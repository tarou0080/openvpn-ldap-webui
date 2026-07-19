# Configuration Guide

This document provides detailed information about configuration options for the OpenVPN LDAP WebUI system.

English | [日本語](CONFIGURATION.ja.md)

## Environment Variables

All configuration is done through the `.env` file. Copy `.env.example` to `.env` and adjust values according to your environment.

```bash
cp .env.example .env
vi .env
```

## Network Configuration

### Basic Network Settings

```bash
# External bind IP address
BIND_IP=192.0.2.10

# External ports
WEBUI_PORT=80              # WebUI external port
OPENVPN_PORT=1194          # OpenVPN external port (UDP)
CERT_API_PORT=8080         # Certificate API external port

# Internal ports (usually no need to change)
WEBUI_INTERNAL_PORT=5000
OPENVPN_INTERNAL_PORT=1194
CERT_API_INTERNAL_PORT=8080
```

- **BIND_IP**: The IP address where services will bind. This should be an IP address on your host that is accessible to VPN clients.
- **WEBUI_PORT**: Port for accessing the web interface
- **OPENVPN_PORT**: Port for VPN connections. Must match firewalld configuration.
- **CERT_API_PORT**: Internal API port for certificate operations

### VPN Network Configuration

```bash
# VPN client network settings
VPN_NETWORK=10.8.0.0
VPN_NETMASK=255.255.255.0
```

- **VPN_NETWORK**: Network address for VPN clients (default: 10.8.0.0)
- **VPN_NETMASK**: Netmask for VPN client network (default: 255.255.255.0)

This configuration creates a 10.8.0.0/24 network for VPN clients.

## Domain Configuration

```bash
# Domain settings
ADMIN_DOMAIN=vpnadmin.example.com
USER_DOMAIN=vpn.example.com

# OpenVPN connection host (written to .ovpn files)
OPENVPN_REMOTE_HOST=vpn.example.com
```

- **ADMIN_DOMAIN**: Domain for admin interface (informational)
- **USER_DOMAIN**: Domain for user interface (informational)
- **OPENVPN_REMOTE_HOST**: Hostname or IP that clients will connect to. This value is written to the .ovpn configuration files.

## Security Configuration

### Application Secrets

```bash
# Flask SECRET_KEY
SECRET_KEY=your-secret-key-here

# Certificate API authentication secret
CERT_API_SECRET=your-api-secret-here
```

Generate secure random keys:
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

- **SECRET_KEY**: Used by Flask for session management. Must be kept secret.
- **CERT_API_SECRET**: Used for authenticating API requests between WebUI and OpenVPN containers.

### WebUI Admin Group

```bash
# AD/LDAP group whose members are treated as WebUI administrators
ADMIN_GROUP=net-vpn-admins
```

- **ADMIN_GROUP**: The LDAP/AD group name whose members get access to the admin interface.
  Members of this group see the "Admin" link in the navigation bar after logging in through
  the reverse proxy. The value must match the group name exactly as it appears in
  `Remote-Groups` injected by the proxy (typically the `cn` of the AD group).
  Default: `net-vpn-admins`.

## Certificate and CA Configuration

### CA Certificate Information

```bash
# CA certificate details
EASYRSA_REQ_COUNTRY=US
EASYRSA_REQ_PROVINCE=California
EASYRSA_REQ_CITY=San Francisco
EASYRSA_REQ_ORG=MyOrganization
EASYRSA_REQ_EMAIL=admin@example.com
EASYRSA_REQ_OU=IT
EASYRSA_CA_CN=MyVPN-CA
```

These values are embedded in the CA certificate. Adjust to match your organization.

### Client Certificate Information

```bash
# Client certificate organizational unit
EASYRSA_CLIENT_OU=VPN-Client
```

### Certificate Validity Periods

```bash
# Certificate expiration (in days)
EASYRSA_CA_EXPIRE=3650        # CA certificate: 10 years
EASYRSA_CERT_EXPIRE=825       # Client certificates: ~2 years
EASYRSA_CRL_DAYS=180          # Certificate Revocation List: 6 months
```

- **EASYRSA_CA_EXPIRE**: CA certificate validity period (default: 10 years)
- **EASYRSA_CERT_EXPIRE**: Client certificate validity period (default: 825 days ≈ 2 years 3 months)
- **EASYRSA_CRL_DAYS**: How long the CRL is valid before needing regeneration

**Note**: Apple iOS requires certificates to be valid for 825 days or less.

## Internal Network Configuration (Optional)

If you want VPN clients to access your internal network:

```bash
# Internal network settings
HOME_NETWORK=192.168.0.0
HOME_NETMASK=255.255.0.0
HOME_DNS_SERVER=192.168.1.1
HOME_GATEWAY=192.168.1.1
HOME_DOMAIN=internal.example.com
ENABLE_NETBIOS=false
```

- **HOME_NETWORK**: Your internal network address
- **HOME_NETMASK**: Netmask for internal network
- **HOME_DNS_SERVER**: DNS server IP for VPN clients
- **HOME_GATEWAY**: Gateway IP for routing to internal network
- **HOME_DOMAIN**: Internal DNS domain (optional)
- **ENABLE_NETBIOS**: Enable NetBIOS name resolution for Windows networks

These settings are used to:
1. Push routes to VPN clients
2. Configure DNS settings in client .ovpn files
3. Set up server-side routing (requires proper host configuration)

## Application Configuration

### Flask Environment

```bash
FLASK_ENV=production
```

- **production**: Use in production (default)
- **development**: Enable debug mode (not recommended for production)

## Logging Configuration

```bash
# Log rotation type
LOG_ROTATION_TYPE=time        # 'time' or 'size'

# Size-based rotation
LOG_MAX_SIZE_MB=10            # Max log file size in MB
LOG_BACKUP_COUNT=30           # Number of backup files to keep

# Time-based rotation
LOG_ROTATION_WHEN=D           # D=daily, W=weekly, M=monthly
LOG_ROTATION_INTERVAL=1       # Interval count
```

### Log Rotation Types

**Time-based rotation** (recommended):
```bash
LOG_ROTATION_TYPE=time
LOG_ROTATION_WHEN=D           # Rotate daily
LOG_ROTATION_INTERVAL=1       # Every 1 day
LOG_BACKUP_COUNT=30           # Keep 30 days of logs
```

**Size-based rotation**:
```bash
LOG_ROTATION_TYPE=size
LOG_MAX_SIZE_MB=10            # Rotate when file reaches 10MB
LOG_BACKUP_COUNT=10           # Keep 10 backup files
```

## Download Expiration Configuration

```bash
# Certificate download expiration settings
DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS=24        # Hours valid after approval
DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS=0   # Hours valid after first download
```

- **DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS**: How long a certificate can be downloaded after approval (0 = unlimited)
- **DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS**: How long a certificate can be re-downloaded after the first download (0 = disable re-download)

Example configurations:

**Allow downloads for 24 hours after approval, disable re-download**:
```bash
DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS=24
DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS=0
```

**Allow unlimited downloads**:
```bash
DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS=0
DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS=0
```

## VPN Log Parsing Configuration

```bash
# VPN log parsing scheduler settings
VPN_LOG_SCHEDULE_MODE=FIXED          # 'INTERVAL' or 'FIXED'
VPN_LOG_SCHEDULE_INTERVAL=15         # Minutes (for INTERVAL mode)
VPN_LOG_SCHEDULE_TIMES=0,15,30,45    # Minutes (for FIXED mode)
VPN_LOG_PARSER_TIMEOUT=300           # Parser timeout in seconds
```

### Schedule Modes

**FIXED mode** (recommended):
```bash
VPN_LOG_SCHEDULE_MODE=FIXED
VPN_LOG_SCHEDULE_TIMES=0,15,30,45    # Run at :00, :15, :30, :45 every hour
```

**INTERVAL mode**:
```bash
VPN_LOG_SCHEDULE_MODE=INTERVAL
VPN_LOG_SCHEDULE_INTERVAL=15         # Run every 15 minutes
```

- **VPN_LOG_PARSER_TIMEOUT**: Maximum time allowed for log parsing (default: 300 seconds)

## LDAP Authentication Configuration

LDAP authentication is configured through environment variables in the `.env` file:

```bash
# LDAP server settings
LDAP_SERVER=ldap.example.com
LDAP_PORT=389

# LDAP Base DN (starting point for user searches)
LDAP_BASE_DN=dc=example,dc=com

# LDAP Bind User (account for searches)
LDAP_BIND_USER=CN=BindUser,CN=Users,DC=example,DC=com
LDAP_BIND_PASSWORD=your-bind-password

# LDAP search filter ({username} will be replaced with the username)
# Default configuration for Active Directory
LDAP_USER_FILTER=(&(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})))

# VPN access group (only members of this group can connect to VPN)
LDAP_VPN_GROUP=CN=VPN-Users,CN=Users,DC=example,DC=com
```

### LDAP Configuration Details

- **LDAP_SERVER**: LDAP server hostname or IP address
- **LDAP_PORT**: LDAP server port (usually 389, or 636 for LDAPS)
- **LDAP_BASE_DN**: Base DN where user searches start
- **LDAP_BIND_USER**: Full DN of the bind user used for searches
- **LDAP_BIND_PASSWORD**: Password for the bind user
- **LDAP_USER_FILTER**: LDAP filter used for user searches
- **LDAP_VPN_GROUP**: DN of the group that grants VPN access

For detailed configuration instructions, see the [LDAP Setup Guide](LDAP_SETUP.md).

## Advanced Configuration

### Path Configuration

```bash
# EasyRSA version
EASYRSA_VERSION=3.2.1
```

Usually no need to change unless you want to use a different EasyRSA version.

## Configuration Examples

### Minimal Configuration (Testing)

```bash
BIND_IP=192.0.2.10
OPENVPN_PORT=1194
OPENVPN_REMOTE_HOST=192.0.2.10
SECRET_KEY=<generated-secret>
CERT_API_SECRET=<generated-secret>
LDAP_SERVER=ldap.example.com
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_USER=CN=BindUser,CN=Users,DC=example,DC=com
LDAP_BIND_PASSWORD=<bind-user-password>
LDAP_VPN_GROUP=CN=VPN-Users,CN=Users,DC=example,DC=com
```

### Production Configuration

```bash
# Network
BIND_IP=203.0.113.10
OPENVPN_PORT=1194
OPENVPN_REMOTE_HOST=vpn.example.com

# Security
SECRET_KEY=<strong-random-secret>
CERT_API_SECRET=<strong-random-secret>

# LDAP Authentication
LDAP_SERVER=ad.example.com
LDAP_PORT=389
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_USER=CN=BindUser,CN=Users,DC=example,DC=com
LDAP_BIND_PASSWORD=<strong-password>
LDAP_VPN_GROUP=CN=VPN-Users,CN=Users,DC=example,DC=com

# Certificates
EASYRSA_REQ_COUNTRY=US
EASYRSA_REQ_PROVINCE=California
EASYRSA_REQ_CITY=San Francisco
EASYRSA_REQ_ORG=Example Inc
EASYRSA_REQ_EMAIL=vpnadmin@example.com
EASYRSA_CA_CN=Example-VPN-CA

# Internal network access
HOME_NETWORK=192.168.0.0
HOME_NETMASK=255.255.0.0
HOME_DNS_SERVER=192.168.1.1
HOME_GATEWAY=192.168.1.1

# Logging
LOG_ROTATION_TYPE=time
LOG_ROTATION_WHEN=D
LOG_BACKUP_COUNT=90

# Download restrictions
DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS=24
DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS=0
```

## Applying Configuration Changes

After modifying `.env`:

1. **Recreate containers** (for most changes):
   ```bash
   podman-compose down
   podman-compose up -d
   ```

2. **For certificate-related changes**, you may need to reinitialize:
   ```bash
   # Warning: This will regenerate all certificates!
   podman exec -it openvpn-server /scripts/init-openvpn.sh
   ```

## Security Best Practices

1. **Keep secrets secure**: Never commit `.env` to version control
2. **Use strong random keys**: Generate with `python3 -c 'import secrets; print(secrets.token_hex(32))'`
3. **Use HTTPS**: Deploy WebUI behind a reverse proxy with TLS
4. **Limit certificate validity**: Follow Apple's guidelines (825 days max)
5. **Regular backups**: Back up `/srv/openvpn-ldap-webui/data` regularly
6. **Monitor logs**: Check audit logs for suspicious activity
7. **Update regularly**: Keep containers and host system updated

## Troubleshooting Configuration Issues

### WebUI won't start

```bash
# Check for syntax errors in .env
podman logs vpn-webui

# Verify all required variables are set
grep -E "SECRET_KEY|CERT_API_SECRET" .env
```

### OpenVPN won't start

```bash
# Check OpenVPN container logs
podman logs openvpn-server

# Verify network configuration
grep -E "BIND_IP|OPENVPN_PORT|VPN_NETWORK" .env
```

### Clients can't download certificates

```bash
# Check download expiration settings
grep DOWNLOAD_EXPIRE .env

# Verify certificate API is accessible
curl -I http://localhost:8080/health
```

### LDAP authentication fails

```bash
# Check LDAP settings
grep LDAP .env

# Check OpenVPN container logs for LDAP errors
podman logs openvpn-server | grep -i ldap

# Test LDAP connection
podman exec -it openvpn-server python3 /scripts/ldap_auth.py
```
