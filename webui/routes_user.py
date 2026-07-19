#!/usr/bin/env python3
import os
import sqlite3
import logging
from flask import Blueprint, request, redirect, url_for, flash, send_file
from auth import get_user_from_headers, is_admin_domain
from database import log_action, get_cert_by_serial, create_cert_request, request_reapproval
from cert_service import is_download_expired, update_download_expiry_after_first_download
from utils import convert_db_row_timestamps, validate_cert_serial
from config import DATABASE_PATH, CERT_PATH
from translations import _

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

def render_with_context(template_name, **kwargs):
    """Render template with common context variables"""
    from flask import render_template
    from flask_wtf.csrf import generate_csrf
    from auth import get_domain_info
    from config import CERT_EXPIRE_DAYS, DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS, DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS, ADMIN_GROUP
    
    context = {
        'user': get_user_from_headers(),
        'domain': get_domain_info(),
        'csrf_token': generate_csrf,
        'cert_expire_days': CERT_EXPIRE_DAYS,
        "admin_group": ADMIN_GROUP,
        'download_expire_from_approval_hours': DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS,
        'download_expire_from_first_download_hours': DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS
    }
    context.update(kwargs)
    return render_template(template_name, **context)

@user_bp.route('/')
def index():
    """User top page"""
    if is_admin_domain():
        # Redirect to admin dashboard if admin domain
        return redirect(url_for('admin_certs.dashboard'))
    
    user = get_user_from_headers()
    
    # Get user's certificate request history (including download expiry info and reapproval status)
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, device_name, status, requested_at, approved_at, cert_serial, expires_at, 
               first_downloaded_at, download_expires_at, reapproval_status
        FROM cert_requests 
        WHERE username = ?
        ORDER BY requested_at DESC
    ''', (user['username'],))
    user_requests_raw = cursor.fetchall()
    conn.close()
    
    # Convert timestamps to JST and determine download availability
    user_requests = []
    for row in user_requests_raw:
        converted_row = list(convert_db_row_timestamps(row, [3, 4, 6, 7, 8]))  # Timestamp columns
        
        # Add download availability check
        if converted_row[2] == 'approved':  # If status is approved
            download_expires_at = row[8]  # Keep in UTC
            is_expired = is_download_expired(download_expires_at)
            converted_row.append(not is_expired)  # Whether downloadable
        else:
            converted_row.append(False)
        
        # Add reapproval_status
        converted_row.append(row[9])  # reapproval_status
        
        user_requests.append(tuple(converted_row))
    
    return render_with_context('index.html', requests=user_requests)

@user_bp.route('/request', methods=['GET', 'POST'])
def request_cert():
    """Certificate request"""
    # Certificate request is disabled on admin domain
    if is_admin_domain():
        flash(_('msg_cert_request_from_user_site'), 'error')
        return redirect(url_for('user.index'))
        
    user = get_user_from_headers()
    
    if request.method == 'POST':
        device_name = request.form.get('device_name')
        reason = request.form.get('reason')
        
        if not device_name:
            flash(_('msg_device_name_required'), 'error')
            return redirect(url_for('user.request_cert'))
        
        # Save certificate request to DB
        req_id = create_cert_request(user['username'], device_name, reason)
        
        # Audit log
        log_action(user['username'], 'request', req_id, request.remote_addr, request.user_agent.string)
        
        flash(_('msg_cert_request_sent'), 'success')
        return redirect(url_for('user.index'))
    
    return render_with_context('request.html')

@user_bp.route('/download/<cert_serial>')
def download_cert(cert_serial):
    """Certificate download"""
    user = get_user_from_headers()
    
    # Security: Check for dangerous characters
    if not validate_cert_serial(cert_serial):
        flash(_('msg_invalid_cert_id'), 'error')
        logger.warning(f"Suspicious cert_serial from {user['username']}: {repr(cert_serial)}")
        return redirect(url_for('user.index'))
    
    # Check user's certificate + download expiry check
    result = get_cert_by_serial(cert_serial)
    
    if not result:
        flash(_('msg_cert_not_found_or_no_permission'), 'error')
        return redirect(url_for('user.index'))
    
    cert_id, cert_username, download_expires_at, first_downloaded_at = result
    
    # Owner check
    if cert_username != user['username']:
        flash(_('msg_cert_not_found_or_no_permission'), 'error')
        return redirect(url_for('user.index'))
    
    # Download expiry check
    if is_download_expired(download_expires_at):
        flash(_('msg_download_expired_request_reapproval'), 'error')
        logger.warning(f"Download expired for {cert_serial} by {user['username']}")
        return redirect(url_for('user.index'))
    
    # Build .ovpn file path
    ovpn_file_path = os.path.join(CERT_PATH, 'client-configs', f'{cert_serial}.ovpn')
    
    # Security: Path normalization and directory check
    try:
        ovpn_file_path = os.path.realpath(ovpn_file_path)
        allowed_dir = os.path.realpath(os.path.join(CERT_PATH, 'client-configs'))
        
        if not ovpn_file_path.startswith(allowed_dir + os.sep):
            flash(_('msg_invalid_file_path'), 'error')
            logger.error(f"Path traversal attempt from {user['username']}: {repr(cert_serial)}")
            return redirect(url_for('user.index'))
    except Exception as e:
        flash(_('msg_file_path_validation_error'), 'error')
        logger.error(f"Path validation error: {str(e)}")
        return redirect(url_for('user.index'))
    
    # Check file existence
    if not os.path.exists(ovpn_file_path):
        flash(_('msg_cert_file_not_found'), 'error')
        logger.error(f"Certificate file not found: {ovpn_file_path}")
        return redirect(url_for('user.index'))
    
    try:
        # Record first download and update download expiry
        if not first_downloaded_at:
            # For first download, update download expiry
            update_download_expiry_after_first_download(cert_id)
            logger.info(f"First download recorded for {cert_serial}, download expiry updated")
        
        # Audit log
        log_action(user['username'], 'download', cert_id, request.remote_addr, request.user_agent.string)
        
        # File download
        return send_file(
            ovpn_file_path,
            as_attachment=True,
            download_name=f'{cert_serial}.ovpn',
            mimetype='application/x-openvpn-profile'
        )
    except Exception as e:
        flash(_('msg_download_error', error=str(e)), 'error')
        logger.error(f"Download error for {cert_serial}: {str(e)}")
        return redirect(url_for('user.index'))

@user_bp.route('/request-reapproval/<int:cert_id>', methods=['POST'])
def request_reapproval_route(cert_id):
    """Request reapproval of certificate"""
    # Reapproval request disabled on admin domain
    if is_admin_domain():
        flash(_('msg_reapproval_request_from_user_site'), 'error')
        return redirect(url_for('user.index'))
    
    user = get_user_from_headers()
    
    # Check if certificate belongs to user and is approved with expired download period
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, device_name, cert_serial, download_expires_at, reapproval_status
        FROM cert_requests 
        WHERE id = ? AND status = 'approved'
    ''', (cert_id,))
    cert_info = cursor.fetchone()
    conn.close()
    
    if not cert_info:
        flash(_('msg_cert_not_found_or_not_approved'), 'error')
        return redirect(url_for('user.index'))
    
    cert_username, device_name, cert_serial, download_expires_at, reapproval_status = cert_info
    
    # Owner check
    if cert_username != user['username']:
        flash(_('msg_no_reapproval_permission'), 'error')
        return redirect(url_for('user.index'))
    
    # Check if already pending reapproval
    if reapproval_status == 'pending':
        flash(_('msg_reapproval_already_pending'), 'info')
        return redirect(url_for('user.index'))
    
    # Download expiry check
    if not is_download_expired(download_expires_at):
        flash(_('msg_cannot_request_reapproval_not_expired'), 'error')
        return redirect(url_for('user.index'))
    
    # Register reapproval request
    request_reapproval(cert_id)
    
    # Audit log
    log_action(user['username'], 'request_reapproval', cert_id, request.remote_addr, request.user_agent.string)
    
    flash(_('msg_reapproval_request_sent', cert_serial=cert_serial), 'success')
    logger.info(f"Reapproval requested for cert_id={cert_id} by {user['username']}")
    
    return redirect(url_for('user.index'))
