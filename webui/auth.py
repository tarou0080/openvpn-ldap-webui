#!/usr/bin/env python3
from flask import request, abort
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
    """Determine if access is from admin domain"""
    return request.host == ADMIN_DOMAIN

def is_admin_user(user):
    """Determine if user belongs to admin group"""
    return ADMIN_GROUP in user.get('groups', [])

def get_domain_info():
    """Get domain information"""
    return {
        'is_admin': is_admin_domain(),
        'current_host': request.host,
        'admin_url': f'https://{ADMIN_DOMAIN}',
        'user_url': f'https://{USER_DOMAIN}'
    }
