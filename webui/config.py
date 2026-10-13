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
# Empty ADMIN_DOMAIN = single-domain mode (admin portal under /admin on the same host).
# Set ADMIN_DOMAIN (and USER_DOMAIN) to serve the admin portal on its own domain.
ADMIN_DOMAIN = os.environ.get('ADMIN_DOMAIN', '').strip()
USER_DOMAIN = os.environ.get('USER_DOMAIN', '').strip()
if ADMIN_DOMAIN and not USER_DOMAIN:
    print("ERROR: USER_DOMAIN must be set when ADMIN_DOMAIN is set (split-domain mode)", file=sys.stderr)
    sys.exit(1)

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

# Reverse proxies allowed to supply Remote-User / Remote-Groups (comma-separated IPs or CIDRs).
# Empty = headers are accepted from any source (only safe if nothing but the proxy can reach the WebUI).
import ipaddress
TRUSTED_PROXIES = []
for _p in os.environ.get('TRUSTED_PROXIES', '').split(','):
    if _p.strip():
        try:
            TRUSTED_PROXIES.append(ipaddress.ip_network(_p.strip(), strict=False))
        except ValueError:
            print(f"ERROR: invalid TRUSTED_PROXIES entry: {_p.strip()}", file=sys.stderr)
            sys.exit(1)
if not TRUSTED_PROXIES:
    print("WARNING: TRUSTED_PROXIES is empty; Remote-User headers are accepted from any source. "
          "Set it to your reverse proxy's IP unless nothing but the proxy can reach the WebUI.", file=sys.stderr)
