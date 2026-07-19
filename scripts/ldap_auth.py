#!/usr/bin/env python3

import sys
import os
import logging
from ldap3 import Server, Connection, Tls
import ssl

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# LDAP settings (from environment variables)
LDAP_SERVER = os.environ.get('LDAP_SERVER', 'ldap.example.com')
LDAP_PORT = int(os.environ.get('LDAP_PORT', '389'))
LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN', 'dc=example,dc=com')
LDAP_BIND_USER = os.environ.get('LDAP_BIND_USER', 'CN=BindUser,CN=Users,DC=example,DC=com')
LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD', '')
LDAP_USER_FILTER = os.environ.get('LDAP_USER_FILTER', '(&(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})))')
LDAP_VPN_GROUP = os.environ.get('LDAP_VPN_GROUP', 'CN=VPN-Users,CN=Users,DC=example,DC=com')

def authenticate_user(username, password):
    """Perform LDAP authentication"""
    try:
        # TLS settings (skip certificate validation)
        tls_configuration = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
        
        # Connect to LDAP server
        server = Server(LDAP_SERVER, port=LDAP_PORT, use_ssl=False, tls=tls_configuration)
        
        # Connect with admin account
        admin_conn = Connection(server, user=LDAP_BIND_USER, password=LDAP_BIND_PASSWORD)
        admin_conn.open()
        admin_conn.start_tls()
        
        if not admin_conn.bind():
            logger.error("Admin bind failed")
            return False, "LDAP admin bind failed"
        
        # Search for user
        search_filter = LDAP_USER_FILTER.format(username=username)
        admin_conn.search(LDAP_BASE_DN, search_filter, attributes=['distinguishedName', 'memberOf'])
        
        if not admin_conn.entries:
            logger.warning(f"User not found: {username}")
            admin_conn.unbind()
            return False, "User not found"
        
        # Get user DN
        user_dn = admin_conn.entries[0].distinguishedName.value
        user_groups = admin_conn.entries[0].memberOf.values if hasattr(admin_conn.entries[0], 'memberOf') else []
        
        logger.info(f"Found user: {username}, DN: {user_dn}")
        admin_conn.unbind()
        
        # Check if user is a member of the VPN group
        if LDAP_VPN_GROUP not in user_groups:
            logger.warning(f"User {username} is not in VPN-Users group")
            return False, "Access denied: Not in VPN-Users group"
        
        # Reconnect with user credentials
        user_conn = Connection(server, user=user_dn, password=password)
        user_conn.open()
        user_conn.start_tls()
        
        if user_conn.bind():
            logger.info(f"Authentication successful for user: {username}")
            user_conn.unbind()
            return True, "Authentication successful"
        else:
            logger.warning(f"Authentication failed for user: {username}")
            return False, "Invalid credentials"
            
    except Exception as e:
        logger.error(f"LDAP authentication error: {str(e)}")
        return False, f"Authentication error: {str(e)}"

def main():
    """Process authentication request from OpenVPN"""
    if len(sys.argv) != 2:
        logger.error("Usage: ldap_auth.py <temp_file>")
        sys.exit(1)
    
    temp_file = sys.argv[1]
    
    try:
        # Read authentication information from OpenVPN
        with open(temp_file, 'r') as f:
            lines = f.readlines()
        
        if len(lines) < 2:
            logger.error("Invalid auth file format")
            sys.exit(1)
        
        username = lines[0].strip()
        password = lines[1].strip()
        
        # Perform authentication
        success, message = authenticate_user(username, password)
        
        if success:
            logger.info(f"VPN authentication successful: {username}")
            sys.exit(0)  # Success
        else:
            logger.warning(f"VPN authentication failed: {username} - {message}")
            sys.exit(1)  # Failure
            
    except Exception as e:
        logger.error(f"Authentication script error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()