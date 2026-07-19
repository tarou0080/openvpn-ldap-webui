#!/usr/bin/env python3
import sqlite3
import logging
from flask import Blueprint, request, redirect, url_for, flash
from auth import get_user_from_headers
from database import (
    log_action, update_cert_status, reapprove_certificate, get_cert_request, 
    get_reapproval_requests, approve_reapproval, reject_reapproval
)
from cert_service import (
    call_cert_api, call_cert_revoke_api, calculate_cert_expiry_date, 
    calculate_download_expiry_from_approval, is_download_expired
)
from utils import convert_db_row_timestamps
from config import DATABASE_PATH
from translations import _
from admin_utils import render_with_context, require_admin

logger = logging.getLogger(__name__)

admin_certs_bp = Blueprint('admin_certs', __name__, url_prefix='/admin')

@admin_certs_bp.route('/')
def dashboard():
    """Admin dashboard"""
    if error_response := require_admin():
        return error_response
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, device_name, reason, requested_at
        FROM cert_requests 
        WHERE status = 'pending'
        ORDER BY requested_at ASC
    ''')
    pending_requests_raw = cursor.fetchall()
    conn.close()
    
    pending_requests = [convert_db_row_timestamps(row, [4]) for row in pending_requests_raw]
    
    reapproval_requests_raw = get_reapproval_requests()
    reapproval_requests = [convert_db_row_timestamps(row, [4, 5, 6]) for row in reapproval_requests_raw]

    return render_with_context("admin.html",
                             pending_requests=pending_requests,
                             reapproval_requests=reapproval_requests)
@admin_certs_bp.route('/certificates')
def certificates():
    """Display certificate list"""
    if error_response := require_admin():
        return error_response
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, device_name, cert_serial, approved_by, approved_at, expires_at,
               first_downloaded_at, download_expires_at
        FROM cert_requests 
        WHERE status = 'approved'
        ORDER BY approved_at DESC
    ''')
    approved_certs_raw = cursor.fetchall()
    conn.close()
    
    approved_certs = []
    for row in approved_certs_raw:
        converted_row = list(convert_db_row_timestamps(row, [5, 6, 7, 8]))
        is_expired = is_download_expired(row[8])
        converted_row.append(is_expired)
        approved_certs.append(tuple(converted_row))
    
    return render_with_context('admin_certificates.html', certificates=approved_certs)

@admin_certs_bp.route('/approve/<int:req_id>', methods=['POST'])
def approve_cert(req_id):
    """Certificate approval"""
    if error_response := require_admin():
        return error_response
    
    user = get_user_from_headers()
    request_info = get_cert_request(req_id)
    
    if request_info and request_info[4] == 'pending':
        username, device_name = request_info[1], request_info[2]
        try:
            logger.info(f"Calling Certificate API for {username}-{device_name}")
            response = call_cert_api(username, device_name)
            
            if response is None:
                flash(_('Could not connect to the certificate generation API.'), 'error')
            elif response.status_code == 200:
                api_result = response.json()
                cert_serial = api_result.get('cert_serial', f"{username}-{device_name}")
                expires_at = calculate_cert_expiry_date()
                download_expires_at = calculate_download_expiry_from_approval()
                
                update_cert_status(req_id, 'approved', user['username'], cert_serial, expires_at, download_expires_at)
                log_action(user['username'], 'approve', req_id, request.remote_addr, request.user_agent.string)
                
                flash(_('Approved the certificate request for %(username)s and generated the certificate.', username=username), 'success')
                logger.info(f"Certificate generated successfully for {username}-{device_name}")
            elif response.status_code == 403:
                flash(_('Certificate generation API authentication error. Please contact the system administrator.'), 'error')
                logger.error("Certificate API authentication failed")
            else:
                error_msg = response.json().get('error', 'Unknown error')
                flash(_('Failed to generate certificate: %(error_msg)s', error_msg=error_msg), 'error')
                logger.error(f"Certificate generation failed: {error_msg}")
        except Exception as e:
            flash(_('An error occurred while generating the certificate: %(error)s', error=str(e)), 'error')
            logger.error(f"Certificate generation error: {str(e)}")
    else:
        flash(_('Request not found or already processed.'), 'error')
    
    return redirect(url_for('admin_certs.dashboard'))

@admin_certs_bp.route('/reject/<int:req_id>', methods=['POST'])
def reject_cert(req_id):
    """Certificate rejection"""
    if error_response := require_admin():
        return error_response
    
    user = get_user_from_headers()
    update_cert_status(req_id, 'rejected', user['username'])
    log_action(user['username'], 'reject', req_id, request.remote_addr, request.user_agent.string)
    flash(_('Certificate request rejected.'), 'success')
    return redirect(url_for('admin_certs.dashboard'))

@admin_certs_bp.route('/revoke/<int:cert_id>', methods=['POST'])
def revoke_cert(cert_id):
    """Certificate revocation/invalidation"""
    if error_response := require_admin():
        return error_response
    
    user = get_user_from_headers()
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT cert_serial, username FROM cert_requests WHERE id = ? AND status = \'approved\'', (cert_id,))
    cert_info = cursor.fetchone()
    conn.close()
    
    if cert_info:
        cert_serial, username = cert_info
        try:
            logger.info(f"Calling Certificate Revoke API for {cert_serial}")
            response = call_cert_revoke_api(cert_serial)
            
            if response is None:
                flash(_('Could not connect to the certificate revocation API.'), 'error')
            elif response.status_code == 200:
                update_cert_status(cert_id, 'revoked', user['username'])
                log_action(user['username'], 'revoke', cert_id, request.remote_addr, request.user_agent.string)
                flash(_('Revoked certificate %(cert_serial)s for %(username)s.', cert_serial=cert_serial, username=username), 'success')
                logger.info(f"Certificate revoked successfully: {cert_serial}")
            elif response.status_code == 403:
                flash(_('Certificate revocation API authentication error. Please contact the system administrator.'), 'error')
                logger.error("Certificate Revoke API authentication failed")
            else:
                error_msg = response.json().get('error', 'Unknown error')
                flash(_('Failed to revoke certificate: %(error_msg)s', error_msg=error_msg), 'error')
                logger.error(f"Certificate revocation failed: {error_msg}")
        except Exception as e:
            flash(_('An error occurred while revoking the certificate: %(error)s', error=str(e)), 'error')
            logger.error(f"Certificate revocation error: {str(e)}")
    else:
        flash(_('Certificate not found or already processed.'), 'error')
    
    return redirect(url_for('admin_certs.certificates'))

@admin_certs_bp.route('/reapprove/<int:cert_id>', methods=['POST'])
def reapprove_cert(cert_id):
    """Extend certificate download expiry (reapproval)"""
    if error_response := require_admin():
        return error_response
    
    user = get_user_from_headers()
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT cert_serial, username FROM cert_requests WHERE id = ? AND status = \'approved\'', (cert_id,))
    cert_info = cursor.fetchone()
    conn.close()
    
    if cert_info:
        cert_serial, username = cert_info
        new_download_expires_at = calculate_download_expiry_from_approval()
        reapprove_certificate(cert_id, new_download_expires_at)
        log_action(user['username'], 'reapprove', cert_id, request.remote_addr, request.user_agent.string)
        flash(_('Extended the download expiration for certificate %(cert_serial)s of %(username)s.', cert_serial=cert_serial, username=username), 'success')
        logger.info(f"Certificate reapproved: {cert_serial}")
    else:
        flash(_('Certificate not found or not approved.'), 'error')
    
    return redirect(url_for('admin_certs.certificates'))

@admin_certs_bp.route('/approve-reapproval/<int:cert_id>', methods=['POST'])
def approve_reapproval_request(cert_id):
    """Approve reapproval request"""
    if error_response := require_admin():
        return error_response
    
    user = get_user_from_headers()
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT cert_serial, username, reapproval_status FROM cert_requests WHERE id = ? AND status = \'approved\'', (cert_id,))
    cert_info = cursor.fetchone()
    conn.close()
    
    if cert_info and cert_info[2] == 'pending':
        cert_serial, username = cert_info[0], cert_info[1]
        new_download_expires_at = calculate_download_expiry_from_approval()
        approve_reapproval(cert_id, user['username'], new_download_expires_at)
        log_action(user['username'], 'approve_reapproval', cert_id, request.remote_addr, request.user_agent.string)
        flash(_('Approved the re-approval request for certificate %(cert_serial)s of %(username)s.', cert_serial=cert_serial, username=username), 'success')
        logger.info(f"Reapproval approved for cert_id={cert_id} by {user['username']}")
    else:
        flash(_('This certificate is not pending re-approval.'), 'error')
    
    return redirect(url_for('admin_certs.dashboard'))

@admin_certs_bp.route('/reject-reapproval/<int:cert_id>', methods=['POST'])
def reject_reapproval_request(cert_id):
    """Reject reapproval request"""
    if error_response := require_admin():
        return error_response
    
    user = get_user_from_headers()
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT cert_serial, username, reapproval_status FROM cert_requests WHERE id = ? AND status = \'approved\'', (cert_id,))
    cert_info = cursor.fetchone()
    conn.close()
    
    if cert_info and cert_info[2] == 'pending':
        cert_serial, username = cert_info[0], cert_info[1]
        reject_reapproval(cert_id)
        log_action(user['username'], 'reject_reapproval', cert_id, request.remote_addr, request.user_agent.string)
        flash(_('Rejected the re-approval request for certificate %(cert_serial)s of %(username)s.', cert_serial=cert_serial, username=username), 'info')
        logger.info(f"Reapproval rejected for cert_id={cert_id} by {user['username']}")
    else:
        flash(_('This certificate is not pending re-approval.'), 'error')
        
    return redirect(url_for('admin_certs.dashboard'))
