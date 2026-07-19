#!/usr/bin/env python3
import os
import time
import logging
import requests
import sqlite3
from flask import Blueprint, redirect, url_for, flash
from utils import get_current_jst_time, convert_utc_to_jst
from config import CERT_API_ENDPOINT, LOG_ROTATION_TYPE, LOG_BACKUP_COUNT, DATABASE_PATH, ACTION_NAMES
from translations import _
from admin_utils import render_with_context, require_admin

logger = logging.getLogger(__name__)

admin_system_bp = Blueprint('admin_system', __name__, url_prefix='/admin/system')

def get_system_health():
    """Get system health information"""
    health_info = {
        'api_status': 'unknown',
        'api_response_time': None,
        'api_last_check': get_current_jst_time(),
        'api_error': None
    }
    try:
        start_time = time.time()
        response = requests.get(f'{CERT_API_ENDPOINT}/health', timeout=5)
        response_time = time.time() - start_time
        health_info['api_response_time'] = round(response_time * 1000, 2)
        if response.status_code == 200:
            health_info['api_status'] = 'healthy'
        else:
            health_info['api_status'] = 'degraded'
            health_info['api_error'] = f'HTTP {response.status_code}'
    except requests.exceptions.Timeout:
        health_info['api_status'] = 'timeout'
        health_info['api_error'] = _('API response timeout')
    except requests.exceptions.ConnectionError:
        health_info['api_status'] = 'unreachable'
        health_info['api_error'] = _('API connection error')
    except Exception as e:
        health_info['api_status'] = 'error'
        health_info['api_error'] = str(e)
    return health_info

def get_log_info():
    """Get log file information"""
    log_info = {
        'app_log_size': 0,
        'app_log_size_mb': 0,
        'app_log_exists': False,
        'app_log_error': None,
        'rotation_type': LOG_ROTATION_TYPE,
        'backup_count': LOG_BACKUP_COUNT
    }
    try:
        app_log_path = '/app/data/logs/app.log'
        if os.path.exists(app_log_path):
            log_info['app_log_exists'] = True
            size_bytes = os.path.getsize(app_log_path)
            log_info['app_log_size'] = size_bytes
            log_info['app_log_size_mb'] = round(size_bytes / (1024 * 1024), 2)
        else:
            log_info['app_log_error'] = _('Log file not found')
    except Exception as e:
        log_info['app_log_error'] = _('Error retrieving log file information: %(error)s', error=str(e))
    return log_info

def get_recent_activities():
    """Get recent activities"""
    activities = []
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, action, target_cert_id, timestamp
            FROM audit_logs 
            ORDER BY timestamp DESC 
            LIMIT 5
        ''')
        for row in cursor.fetchall():
            username, action, target_cert_id, timestamp = row
            jst_timestamp = convert_utc_to_jst(timestamp)
            activity = {
                'username': username,
                'action': ACTION_NAMES.get(action, action),
                'target_cert_id': target_cert_id,
                'timestamp': jst_timestamp
            }
            activities.append(activity)
        conn.close()
    except Exception as e:
        logger.error(f"Recent activities fetch error: {str(e)}")
        activities = [{'error': _('Error fetching recent activities: %(error)s', error=str(e))}]
    return activities

def get_scheduler_status():
    """Get scheduler status"""
    status_info = {
        'exists': False, 'is_running': False, 'last_run_at': None,
        'last_run_status': 'unknown', 'last_run_duration': None,
        'next_run_at': None, 'last_error': None, 'recent_events': []
    }
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduler_status'")
        if not cursor.fetchone():
            conn.close()
            return status_info
        
        status_info['exists'] = True
        cursor.execute('''
            SELECT is_running, last_run_at, last_run_status, 
                   last_run_duration_seconds, next_run_at, last_error
            FROM scheduler_status WHERE task_name = ?
        ''', ('vpn-log-parser',))
        row = cursor.fetchone()
        if row:
            status_info['is_running'] = row[0] == 1
            status_info['last_run_at'] = row[1]
            status_info['last_run_status'] = row[2] or 'unknown'
            status_info['last_run_duration'] = f"{row[3]:.2f}" if row[3] else None
            status_info['next_run_at'] = row[4]
            status_info['last_error'] = row[5]
        
        cursor.execute('''
            SELECT event_type, status, message, duration_seconds, created_at
            FROM scheduler_events WHERE task_name = ? ORDER BY created_at DESC LIMIT 5
        ''', ('vpn-log-parser',))
        for event_row in cursor.fetchall():
            event = {
                'type': event_row[0], 'status': event_row[1], 'message': event_row[2],
                'duration': f"{event_row[3]:.2f}s" if event_row[3] else None,
                'created_at': convert_utc_to_jst(event_row[4])
            }
            status_info['recent_events'].append(event)
        conn.close()
    except Exception as e:
        logger.error(f"Scheduler status fetch error: {str(e)}")
        status_info['error'] = str(e)
    return status_info

@admin_system_bp.route('/status')
def system_status():
    """Display system status"""
    if error_response := require_admin():
        return error_response
    
    system_health = get_system_health()
    log_info = get_log_info()
    recent_activities = get_recent_activities()
    scheduler_status = get_scheduler_status()
    
    return render_with_context('system_status.html', 
                             system_health=system_health,
                             log_info=log_info,
                             recent_activities=recent_activities,
                             scheduler_status=scheduler_status)
