# LDAP Setup Guide

This document provides detailed instructions for integrating OpenVPN LDAP WebUI with LDAP servers (Active Directory or OpenLDAP).

English | [日本語](LDAP_SETUP.ja.md)

## Overview

OpenVPN LDAP WebUI uses LDAP/Active Directory authentication for VPN connections. This provides two-factor authentication combining certificates and username/password credentials.

## LDAP Authentication Flow

```
VPN Client
    ↓ OpenVPN connection attempt (certificate + username/password)
OpenVPN Server
    ↓ Certificate validation (success)
    ↓ Call ldap_auth.py script
LDAP Server
    ↓ User validation
    ↓ Group membership check
    ↓ Return authentication result
OpenVPN Server
    ↓ Allow/Deny connection
```

## Prerequisites

### For Active Directory

- Active Directory server running
- Network connectivity from VPN server to AD
- Bind user for searches (read-only permissions sufficient)
- Security group for VPN access

### For OpenLDAP

- OpenLDAP server running
- Network connectivity from VPN server to LDAP
- Bind user for searches
- Group for VPN access
- **`memberOf` overlay enabled** — `ldap_auth.py` checks group membership via the `memberOf`
  attribute using an exact DN match. OpenLDAP does not populate `memberOf` by default;
  you must enable the `memberof` overlay. Without it, group membership checks will always
  fail even when the user is correctly added to the group.

## Configuration Steps

### Step 1: Create LDAP Group

#### For Active Directory

1. Open Active Directory Users and Computers
2. Create a new security group:
   - Name: `VPN-Users`
   - Group scope: `Global` or `Universal`
   - Group type: `Security`
3. Add users who should have VPN access to this group

#### For OpenLDAP

Example LDIF file:

```ldif
dn: cn=VPN-Users,ou=Groups,dc=example,dc=com
objectClass: groupOfNames
cn: VPN-Users
description: VPN Access Group
member: uid=user1,ou=Users,dc=example,dc=com
member: uid=user2,ou=Users,dc=example,dc=com
```

Apply:
```bash
ldapadd -x -D "cn=admin,dc=example,dc=com" -W -f vpn-group.ldif
```

### Step 2: Create Bind User

#### For Active Directory

1. Create a new user (e.g., `BindUser`)
2. Permissions:
   - Regular domain user permissions sufficient
   - No special privileges required (read-only)
3. Password settings:
   - Set a strong password
   - Enable "Password never expires"

#### For OpenLDAP

Example LDIF file:

```ldif
dn: cn=BindUser,dc=example,dc=com
objectClass: simpleSecurityObject
objectClass: organizationalRole
cn: BindUser
description: LDAP Bind User for VPN Authentication
userPassword: {SSHA}your-hashed-password
```

### Step 3: Configure .env File

Copy and edit `.env.example`:

```bash
cp .env.example .env
vi .env
```

#### Active Directory Configuration Example

```bash
# LDAP Authentication Settings
LDAP_SERVER=ad.example.com
LDAP_PORT=389

# Base DN (adjust to your organization's domain)
LDAP_BASE_DN=dc=example,dc=com

# Bind User (specify in full DN format)
LDAP_BIND_USER=CN=BindUser,CN=Users,DC=example,DC=com
LDAP_BIND_PASSWORD=your-strong-password

# Search filter for Active Directory (usually no need to change)
LDAP_USER_FILTER=(&(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})))

# VPN group DN (adjust to match your created group)
LDAP_VPN_GROUP=CN=VPN-Users,CN=Users,DC=example,DC=com
```

#### OpenLDAP Configuration Example

```bash
# LDAP Authentication Settings
LDAP_SERVER=ldap.example.com
LDAP_PORT=389

# Base DN
LDAP_BASE_DN=dc=example,dc=com

# Bind User
LDAP_BIND_USER=cn=BindUser,dc=example,dc=com
LDAP_BIND_PASSWORD=your-strong-password

# Search filter for OpenLDAP
LDAP_USER_FILTER=(&(objectClass=inetOrgPerson)(uid={username}))

# VPN group DN
LDAP_VPN_GROUP=cn=VPN-Users,ou=Groups,dc=example,dc=com
```

### Step 4: Test LDAP Connection

It's recommended to test the LDAP connection before starting containers:

#### Testing with ldapsearch Command

```bash
# For Active Directory
ldapsearch -x -H ldap://ad.example.com:389 \
  -D "CN=BindUser,CN=Users,DC=example,DC=com" \
  -w "your-password" \
  -b "DC=example,DC=com" \
  "(&(objectClass=user)(sAMAccountName=testuser))"

# For OpenLDAP
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "cn=BindUser,dc=example,dc=com" \
  -w "your-password" \
  -b "dc=example,dc=com" \
  "(&(objectClass=inetOrgPerson)(uid=testuser))"
```

If successful, user information will be displayed.

### Step 5: Start Containers

```bash
podman-compose up -d
```

### Step 6: Test LDAP Authentication

Test the authentication script inside the OpenVPN server container:

```bash
# Create a test authentication file
echo "testuser" > /tmp/test_auth.txt
echo "testpassword" >> /tmp/test_auth.txt

# Run authentication script
podman exec -it openvpn-server python3 /scripts/ldap_auth.py /tmp/test_auth.txt

# Cleanup
rm /tmp/test_auth.txt
```

Expected output on success:
```
2024-01-01 12:00:00 - INFO - Found user: testuser, DN: CN=Test User,CN=Users,DC=example,DC=com
2024-01-01 12:00:00 - INFO - Authentication successful for user: testuser
2024-01-01 12:00:00 - INFO - VPN authentication successful: testuser
```

## Advanced Configuration

### Enable SSL/TLS Connection

For production environments, using LDAPS (LDAP over SSL) is recommended.

#### Edit scripts/ldap_auth.py

```python
# SSL/TLS configuration
server = Server(LDAP_SERVER, port=636, use_ssl=True, tls=tls_configuration)
```

#### Configure .env

```bash
LDAP_PORT=636
```

### Custom Search Filters

You can customize the search filter to support different LDAP schemas.

#### Example 1: Search by Multiple Attributes

```bash
LDAP_USER_FILTER=(&(objectClass=person)(|(uid={username})(mail={username}@example.com)))
```

#### Example 2: Restrict by Organizational Unit (OU)

```bash
LDAP_USER_FILTER=(&(objectClass=user)(sAMAccountName={username})(memberOf=CN=Employees,OU=Users,DC=example,DC=com))
```

#### Example 3: Check Specific Attribute Values

```bash
LDAP_USER_FILTER=(&(objectClass=user)(sAMAccountName={username})(employeeType=FullTime))
```

### Supporting Multiple VPN Groups

To allow VPN access to members of multiple groups, edit `ldap_auth.py`:

```python
# Define multiple groups
VPN_GROUPS = [
    'CN=VPN-Users,CN=Users,DC=example,DC=com',
    'CN=Administrators,CN=Users,DC=example,DC=com',
    'CN=RemoteWorkers,CN=Users,DC=example,DC=com'
]

# Check logic
if not any(group in user_groups for group in VPN_GROUPS):
    logger.warning(f"User {username} is not in any VPN group")
    return False, "Access denied: Not in VPN groups"
```

### Nested Group Support

For using nested groups in Active Directory:

```python
# Use recursive group membership in search filter
search_filter = f'(&(objectClass=user)(sAMAccountName={username})(memberOf:1.2.840.113556.1.4.1941:=CN=VPN-Users,CN=Users,DC=example,DC=com))'
```

`1.2.840.113556.1.4.1941` is a special AD OID that performs recursive group membership searches.

## Troubleshooting

### Issue 1: Bind Failure

**Symptom**: `Admin bind failed`

**Check**:
```bash
# Verify LDAP settings
grep LDAP .env

# Test connectivity to LDAP server
podman exec -it openvpn-server nc -zv $LDAP_SERVER $LDAP_PORT

# Verify bind user DN format
# For Active Directory: CN format
# For OpenLDAP: cn format
```

### Issue 2: User Not Found

**Symptom**: `User not found`

**Check**:
```bash
# Verify Base DN
echo $LDAP_BASE_DN

# Test search filter
ldapsearch -x -H ldap://$LDAP_SERVER:$LDAP_PORT \
  -D "$LDAP_BIND_USER" -w "$LDAP_BIND_PASSWORD" \
  -b "$LDAP_BASE_DN" \
  "(&(objectClass=user)(sAMAccountName=testuser))"
```

### Issue 3: Group Membership Check Failure

**Symptom**: `Access denied: Not in VPN-Users group`

**Check**:
```bash
# Verify user's group membership
ldapsearch -x -H ldap://$LDAP_SERVER:$LDAP_PORT \
  -D "$LDAP_BIND_USER" -w "$LDAP_BIND_PASSWORD" \
  -b "$LDAP_BASE_DN" \
  "(&(objectClass=user)(sAMAccountName=testuser))" memberOf

# Verify group DN matches exactly (case-sensitive, watch for spaces)
```

### Issue 4: TLS/SSL Connection Error

**Symptom**: `SSL/TLS connection failed`

**Solution**:

Temporarily disable certificate validation (testing only):
```python
tls_configuration = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
```

For production, use proper certificates:
```python
tls_configuration = Tls(
    ca_certs_file='/path/to/ca-cert.pem',
    validate=ssl.CERT_REQUIRED
)
```

### Issue 5: Timeout

**Symptom**: Authentication takes too long or times out

**Solution**:
```python
# Add timeout configuration to ldap_auth.py
server = Server(
    LDAP_SERVER, 
    port=LDAP_PORT, 
    use_ssl=False, 
    tls=tls_configuration,
    connect_timeout=5  # 5 second timeout
)
```

## Debug Mode

To see detailed logs, change the log level to DEBUG:

```python
# scripts/ldap_auth.py
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
```

Restart container:
```bash
podman-compose restart openvpn-server
```

View logs:
```bash
podman logs -f openvpn-server | grep -i ldap
```

## Security Best Practices

1. **Principle of Least Privilege**: Grant bind user read-only permissions only
2. **Use LDAPS**: Use SSL/TLS encryption in production environments
3. **Strong Passwords**: Use complex passwords for bind users
4. **Regular Audits**: Regularly review LDAP authentication logs
5. **Group-Based Access Control**: Manage access via groups, not individual users
6. **Account Lockout**: Configure AD lockout policies
7. **Monitor**: Watch for unusual increases in authentication failures

## Frequently Asked Questions

**Q: Can I support both Active Directory and OpenLDAP?**

A: Yes, by properly configuring LDAP_USER_FILTER. However, you cannot use both simultaneously.

**Q: What can be used as username?**

A: By default, sAMAccountName (for AD) or uid (for OpenLDAP). You can customize LDAP_USER_FILTER to also accept email addresses.

**Q: Can I disable LDAP authentication?**

A: No, this system is designed with LDAP authentication as a requirement. Using it without LDAP would require implementing an alternative authentication method.

**Q: Can I authenticate with certificate only?**

A: No. The server always requires both the certificate and the LDAP password (enforced since 2.0.0); `start-openvpn.sh` writes the LDAP check into `server.conf` on every start.

**Q: What's the performance impact of LDAP authentication?**

A: LDAP authentication only occurs during connection establishment and doesn't affect traffic after connection. Typical overhead is a few hundred milliseconds.

## References

- [LDAP3 Documentation](https://ldap3.readthedocs.io/)
- [Active Directory LDAP Syntax Filters](https://social.technet.microsoft.com/wiki/contents/articles/5392.active-directory-ldap-syntax-filters.aspx)
- [OpenLDAP Administrator's Guide](https://www.openldap.org/doc/admin24/)
