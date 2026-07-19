#!/usr/bin/env python3
import os
import sys
from datetime import timezone, timedelta

# Enforce SECRET_KEY setting
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY or SECRET_KEY == 'dev-key-change-in-production':
    print("ERROR: SECRET_KEY environment variable must be set to a secure random value", file=sys.stderr)
    print("Generate a key with: python3 -c 'import secrets; print(secrets.token_hex(32))'", file=sys.stderr)
    sys.exit(1)

# Path settings
DATABASE_PATH = os.environ.get('DATABASE_PATH', '/app/data/db/vpn.db')
CERT_PATH = os.environ.get('CERT_PATH', '/app/data/certs')
OPENVPN_CONFIG = os.environ.get('OPENVPN_CONFIG', '/app/openvpn-config')

# Domain settings
ADMIN_DOMAIN = os.environ.get('ADMIN_DOMAIN', 'vpn-admin.example.com')
USER_DOMAIN = os.environ.get('USER_DOMAIN', 'vpn.example.com')

# Certificate validity (days)
CERT_EXPIRE_DAYS = int(os.environ.get('CERT_EXPIRE_DAYS', '825'))

# Download expiration settings
DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS = int(os.environ.get('DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS', '24'))
DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS = int(os.environ.get('DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS', '0'))

# Timezone settings
JST = timezone(timedelta(hours=9))

# Default language setting
DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'en')

# Log settings
LOG_ROTATION_TYPE = os.environ.get('LOG_ROTATION_TYPE', 'time')  # 'size' or 'time'
LOG_MAX_SIZE_MB = int(os.environ.get('LOG_MAX_SIZE_MB', '10'))
LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '30'))
LOG_ROTATION_WHEN = os.environ.get('LOG_ROTATION_WHEN', 'D')  # D, W, M
LOG_ROTATION_INTERVAL = int(os.environ.get('LOG_ROTATION_INTERVAL', '1'))

# Certificate API settings
CERT_API_SECRET = os.environ.get('CERT_API_SECRET', 'change-this-secret-in-production')
CERT_API_ENDPOINT = os.environ.get('CERT_API_ENDPOINT', 'http://openvpn-server:8080')

# Action name mapping
ACTION_NAMES = {
    'request': 'Certificate Request',
    'approve': 'Certificate Approval',
    'reject': 'Certificate Rejection',
    'revoke': 'Certificate Revocation',
    'download': 'Certificate Download',
    'reapprove': 'Certificate Reapproval',
    'request_reapproval': 'Reapproval Request',
    'approve_reapproval': 'Reapproval Request Approval',
    'reject_reapproval': 'Reapproval Request Rejection'
}
# Admin group setting
ADMIN_GROUP = os.environ.get('ADMIN_GROUP', 'net-vpn-admins')
