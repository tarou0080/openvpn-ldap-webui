#!/usr/bin/env python3
import sqlite3
import logging
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

def init_db():
    """Initialize database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Certificate request table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cert_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            device_name TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_by TEXT,
            approved_at TIMESTAMP,
            cert_serial TEXT,
            expires_at TIMESTAMP,
            first_downloaded_at TIMESTAMP,
            download_expires_at TIMESTAMP
        )
    ''')
    
    # Audit log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            target_cert_id INTEGER,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # VPN connection history table (skip if already exists)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vpn_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            cert_common_name TEXT NOT NULL,
            client_ip TEXT,
            vpn_ip TEXT,
            connected_at TIMESTAMP NOT NULL,
            disconnected_at TIMESTAMP,
            duration_seconds INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

def log_action(username, action, target_cert_id=None, ip_address=None, user_agent=None):
    """Record audit log"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_logs (username, action, target_cert_id, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?)
    ''', (username, action, target_cert_id, ip_address, user_agent))
    conn.commit()
    conn.close()

def get_cert_request(req_id):
    """Get certificate request"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cert_requests WHERE id = ?', (req_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_cert_by_serial(cert_serial, status='approved'):
    """Get certificate information by serial"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, download_expires_at, first_downloaded_at
        FROM cert_requests 
        WHERE cert_serial = ? AND status = ?
    ''', (cert_serial, status))
    result = cursor.fetchone()
    conn.close()
    return result

def update_cert_status(req_id, status, approved_by=None, cert_serial=None, expires_at=None, download_expires_at=None):
    """Update certificate request status"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if status == 'approved':
        cursor.execute('''
            UPDATE cert_requests 
            SET status = ?, 
                approved_by = ?, 
                approved_at = CURRENT_TIMESTAMP, 
                cert_serial = ?, 
                expires_at = ?,
                download_expires_at = ?
            WHERE id = ?
        ''', (status, approved_by, cert_serial, expires_at, download_expires_at, req_id))
    elif status in ('rejected', 'revoked'):
        cursor.execute('''
            UPDATE cert_requests 
            SET status = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, approved_by, req_id))
    else:
        cursor.execute('UPDATE cert_requests SET status = ? WHERE id = ?', (status, req_id))
    
    conn.commit()
    conn.close()

def update_download_timestamp(cert_id, download_expires_at):
    """Update first download timestamp and download expiry"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cert_requests 
        SET first_downloaded_at = CURRENT_TIMESTAMP,
            download_expires_at = ?
        WHERE id = ?
    ''', (download_expires_at, cert_id))
    conn.commit()
    conn.close()

def reapprove_certificate(cert_id, new_download_expires_at):
    """Reapprove certificate (reset download expiry)"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cert_requests 
        SET first_downloaded_at = NULL,
            download_expires_at = ?
        WHERE id = ?
    ''', (new_download_expires_at, cert_id))
    conn.commit()
    conn.close()

def create_cert_request(username, device_name, reason):
    """Create new certificate request"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cert_requests (username, device_name, reason)
        VALUES (?, ?, ?)
    ''', (username, device_name, reason))
    req_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return req_id

def request_reapproval(cert_id):
    """Request reapproval of certificate"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cert_requests 
        SET reapproval_status = 'pending',
            reapproval_requested_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (cert_id,))
    conn.commit()
    conn.close()

def approve_reapproval(cert_id, approved_by, new_download_expires_at):
    """Approve reapproval request and extend download expiry"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cert_requests 
        SET first_downloaded_at = NULL,
            download_expires_at = ?,
            reapproval_status = NULL,
            reapproval_requested_at = NULL,
            approved_by = ?,
            approved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_download_expires_at, approved_by, cert_id))
    conn.commit()
    conn.close()

def reject_reapproval(cert_id):
    """Reject reapproval request"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cert_requests 
        SET reapproval_status = 'rejected',
            reapproval_requested_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (cert_id,))
    conn.commit()
    conn.close()

def get_reapproval_requests():
    """Get list of certificates with pending reapproval requests"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, device_name, cert_serial, reapproval_requested_at,
               approved_at, download_expires_at
        FROM cert_requests 
        WHERE status = 'approved' AND reapproval_status = 'pending'
        ORDER BY reapproval_requested_at ASC
    ''')
    result = cursor.fetchall()
    conn.close()
    return result
