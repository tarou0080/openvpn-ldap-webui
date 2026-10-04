#!/usr/bin/env python3
from flask import request, abort, url_for
from config import ADMIN_DOMAIN, USER_DOMAIN, ADMIN_GROUP, TRUSTED_PROXIES
import ipaddress
import logging

logger = logging.getLogger(__name__)

def from_trusted_proxy():
    """True if the request comes from a reverse proxy listed in TRUSTED_PROXIES (always True when unset)"""
    if not TRUSTED_PROXIES:
        return True
    try:
        addr = ipaddress.ip_address(request.remote_addr)
    except ValueError:
        return False
    return any(addr in net for net in TRUSTED_PROXIES)


def get_user_from_headers():
    """Get header information from Authelia
    
    Returns 401 error if Remote-User header does not exist
    """
    # Identity headers from anything but the trusted proxy could be forged
    if not from_trusted_proxy():
        if request.headers.get("Remote-User"):
            logger.warning(f"Ignoring identity headers from untrusted source {request.remote_addr}")
        abort(401, description="Authentication required. Please access via Authelia.")

    username = request.headers.get('Remote-User')
    
    # Security: Remote-User header is required
    if not username:
        logger.warning(f"Missing Remote-User header from {request.remote_addr}")
        abort(401, description="Authentication required. Please access via Authelia.")
    
    return {
        'username': username,
        'groups': request.headers.get('Remote-Groups', '').split(','),
        'name': request.headers.get('Remote-Name', ''),
        'email': request.headers.get('Remote-Email', '')
    }

def is_admin_domain():
    """True if the request came to the dedicated admin domain (split-domain mode only)"""
    return bool(ADMIN_DOMAIN) and request.host == ADMIN_DOMAIN

def is_admin_area():
    """True if the request targets the admin portal.

    Split-domain mode (ADMIN_DOMAIN set): the admin domain is the admin portal.
    Single-domain mode (ADMIN_DOMAIN empty): /admin paths are the admin portal.
    """
    if ADMIN_DOMAIN:
        return is_admin_domain()
    return request.path == '/admin' or request.path.startswith('/admin/')

def is_admin_user(user):
    """Determine if user belongs to admin group"""
    return ADMIN_GROUP in user.get('groups', [])

def get_domain_info():
    """Get domain information"""
    if ADMIN_DOMAIN:
        admin_url, user_url = f'https://{ADMIN_DOMAIN}', f'https://{USER_DOMAIN}'
    else:
        admin_url, user_url = url_for('admin_certs.dashboard'), url_for('user.index')
    return {
        'is_admin': is_admin_area(),
        'current_host': request.host,
        'admin_url': admin_url,
        'user_url': user_url
    }
