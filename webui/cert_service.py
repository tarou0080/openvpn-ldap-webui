#!/usr/bin/env python3
import json
import hmac
import hashlib
import requests
import logging
from datetime import datetime, timezone, timedelta
from config import (
    CERT_API_SECRET, CERT_API_ENDPOINT, CERT_EXPIRE_DAYS,
    DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS, DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS
)
from database import update_download_timestamp

logger = logging.getLogger(__name__)

def calculate_cert_expiry_date():
    """Calculate certificate expiry date (UTC)"""
    expiry_date = datetime.now(timezone.utc) + timedelta(days=CERT_EXPIRE_DAYS)
    return expiry_date.isoformat()

def calculate_download_expiry_from_approval():
    """Calculate download expiry from approval time (UTC)"""
    if DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS == 0:
        # If 0, no limit (return NULL)
        return None
    expiry_date = datetime.now(timezone.utc) + timedelta(hours=DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS)
    return expiry_date.isoformat()

def update_download_expiry_after_first_download(cert_id):
    """Update download expiry after first download"""
    if DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS == 0:
        # If 0, immediately invalidate (set past time)
        expiry_date = datetime.now(timezone.utc) - timedelta(seconds=1)
    else:
        expiry_date = datetime.now(timezone.utc) + timedelta(hours=DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS)
    
    update_download_timestamp(cert_id, expiry_date.isoformat())
    return expiry_date

def is_download_expired(download_expires_at):
    """Check if download period has expired"""
    if not download_expires_at:
        # No limit if expiry is not set
        return False
    
    try:
        expiry_dt = datetime.fromisoformat(download_expires_at.replace('Z', '+00:00'))
        if expiry_dt.tzinfo is None:
            expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
        
        now_utc = datetime.now(timezone.utc)
        return now_utc > expiry_dt
    except Exception as e:
        logger.error(f"Download expiry check error: {str(e)}")
        return False

def call_cert_api(username, device_name):
    """Call Certificate API"""
    try:
        # Prepare request data
        data = json.dumps({
            'username': username,
            'device_name': device_name
        })
        
        # Generate HMAC signature
        signature = hmac.new(CERT_API_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
        
        # Call API
        response = requests.post(
            f'{CERT_API_ENDPOINT}/generate-cert',
            data=data,
            headers={
                'Content-Type': 'application/json',
                'X-Signature': f'sha256={signature}'
            },
            timeout=180  # 3 minute timeout
        )
        
        return response
        
    except requests.exceptions.Timeout:
        logger.error("Certificate API timeout")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("Certificate API connection error")
        return None
    except Exception as e:
        logger.error(f"Certificate API error: {str(e)}")
        return None

def call_cert_revoke_api(cert_serial):
    """Call Certificate Revoke API"""
    try:
        # Prepare request data
        data = json.dumps({
            'cert_serial': cert_serial
        })
        
        # Generate HMAC signature
        signature = hmac.new(CERT_API_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
        
        # Call API
        response = requests.post(
            f'{CERT_API_ENDPOINT}/revoke-cert',
            data=data,
            headers={
                'Content-Type': 'application/json',
                'X-Signature': f'sha256={signature}'
            },
            timeout=180  # 3 minute timeout
        )
        
        return response
        
    except requests.exceptions.Timeout:
        logger.error("Certificate Revoke API timeout")
        return None
    except requests.exceptions.ConnectionError:
        logger.error("Certificate Revoke API connection error")
        return None
    except Exception as e:
        logger.error(f"Certificate Revoke API error: {str(e)}")
        return None
