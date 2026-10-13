#!/bin/bash
set -e
echo "Starting OpenVPN server..."

# Check if OpenVPN is initialized
EASYRSA_VERSION=${EASYRSA_VERSION:-3.2.1}
PKI_DIR="/etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki"

if [ ! -f "${PKI_DIR}/ca.crt" ]; then
    echo "OpenVPN not initialized. Please run init script first."
    echo "Waiting for initialization..."
    while [ ! -f "${PKI_DIR}/ca.crt" ]; do
        sleep 5
    done
fi

# Check if server configuration exists
if [ ! -f "/etc/openvpn/server/server.conf" ]; then
    echo "Server configuration not found. Please run init script first."
    exit 1
fi

# Add routing and DNS configuration to server.conf if not already present
echo "Configuring OpenVPN routing and DNS settings..."

CONFIG_FILE="/etc/openvpn/server/server.conf"

# Update port number to match OPENVPN_PORT
sed -i "s/^port .*/port ${OPENVPN_PORT}/" "$CONFIG_FILE"

# Add or update local directive to bind to specific IP
if grep -q "^local " "$CONFIG_FILE"; then
    sed -i "s/^local .*/local ${BIND_IP}/" "$CONFIG_FILE"
else
    sed -i "/^port /a local ${BIND_IP}" "$CONFIG_FILE"
fi

# Remove every auto-generated block; they are all re-added below from the environment
sed -i '/^# Auto-generated security settings/,/^# End of auto-generated security settings/d' "$CONFIG_FILE"
sed -i '/^# Auto-generated routing and DNS settings/,/^# End of auto-generated settings/d' "$CONFIG_FILE"
sed -i '/^# Auto-generated LDAP auth settings/,/^# End of auto-generated LDAP auth settings/d' "$CONFIG_FILE"

# Drop hand-written copies of the directives the security block owns (older
# server.conf files carried them, or lacked them: init before 2.0.0 wrote no
# LDAP check and no CRL check). Compression is removed for good (VORACLE).
sed -i -E '/^[[:space:]]*(cipher|auth|tls-version-min|auth-user-pass-verify|script-security|username-as-common-name|tmp-dir|crl-verify|comp-lzo|compress)([[:space:]]|$)/d' "$CONFIG_FILE"

# Trim trailing blank lines so restarts do not pile them up
CONTENT=$(cat "$CONFIG_FILE")
printf '%s\n' "$CONTENT" > "$CONFIG_FILE"

# Security settings: certificate AND LDAP password are both required, and
# revoked certificates are refused. Written on every start so a regenerated
# or hand-edited server.conf cannot silently lose them.
cat >> "$CONFIG_FILE" << EOF

# Auto-generated security settings
cipher AES-256-GCM
auth SHA256
tls-version-min 1.2
auth-user-pass-verify /scripts/ldap_auth.py via-file
script-security 2
username-as-common-name
tmp-dir /tmp
crl-verify /etc/openvpn/crl.pem
# End of auto-generated security settings
EOF

# Add new settings at the end of the file
cat >> "$CONFIG_FILE" << EOF

# Auto-generated routing and DNS settings
# Push route to home network
push "route ${HOME_NETWORK} ${HOME_NETMASK}"

# Push DNS server
push "dhcp-option DNS ${HOME_DNS_SERVER}"
EOF

# Add DNS domain if specified
if [ -n "${HOME_DOMAIN}" ]; then
    cat >> "$CONFIG_FILE" << EOF
push "dhcp-option DOMAIN ${HOME_DOMAIN}"
EOF
fi

cat >> "$CONFIG_FILE" << EOF

# NetBIOS settings for Windows name resolution
EOF

if [ "${ENABLE_NETBIOS}" = "true" ]; then
    cat >> "$CONFIG_FILE" << EOF
push "dhcp-option WINS ${HOME_DNS_SERVER}"
push "dhcp-option NBT 1"
EOF
fi

if [ "${FULL_TUNNEL}" = "true" ]; then
    cat >> "$CONFIG_FILE" << EOF

# Full tunnel: send all client traffic through the VPN (exit = this server's default route)
push "redirect-gateway def1 bypass-dhcp"
# This server tunnels IPv4 only; stop clients from leaking IPv6 around the tunnel
push "block-ipv6"
EOF
fi

cat >> "$CONFIG_FILE" << EOF
# End of auto-generated settings
EOF

echo "Routing and DNS configuration added to server.conf"

# Pass LDAP auth settings to the auth script via setenv.
# OpenVPN does NOT propagate the daemon's process environment to
# --auth-user-pass-verify scripts (only its own connection variables),
# so env vars from compose never reach ldap_auth.py without this.
if [ -n "${LDAP_SERVER}" ]; then
    cat >> "$CONFIG_FILE" << LDAPEOF

# Auto-generated LDAP auth settings
setenv LDAP_SERVER "${LDAP_SERVER}"
setenv LDAP_PORT "${LDAP_PORT:-389}"
setenv LDAP_BASE_DN "${LDAP_BASE_DN}"
setenv LDAP_BIND_USER "${LDAP_BIND_USER}"
setenv LDAP_BIND_PASSWORD "${LDAP_BIND_PASSWORD}"
setenv LDAP_USER_FILTER "${LDAP_USER_FILTER}"
setenv LDAP_VPN_GROUP "${LDAP_VPN_GROUP}"
setenv LDAP_TLS_CA_FILE "${LDAP_TLS_CA_FILE}"
# End of auto-generated LDAP auth settings
LDAPEOF
    chmod 600 "$CONFIG_FILE"
    echo "LDAP auth settings added to server.conf"
else
    echo "WARNING: LDAP_SERVER is not set; every VPN login will be rejected until it is"
fi

# CRL: regenerate on every start so it always exists (crl-verify refuses to
# start without it) and its expiry is pushed forward. A CRL that expires blocks
# every client with "VERIFY ERROR: CRL has expired".
echo "Regenerating CRL..."
if (cd "${PKI_DIR}/.." && EASYRSA_BATCH=1 EASYRSA_CRL_DAYS="${EASYRSA_CRL_DAYS:-3650}" ./easyrsa gen-crl >/dev/null); then
    cp "${PKI_DIR}/crl.pem" /etc/openvpn/crl.pem
    chown openvpn:openvpn /etc/openvpn/crl.pem
    chmod 644 /etc/openvpn/crl.pem
elif [ -f /etc/openvpn/crl.pem ]; then
    echo "WARNING: CRL regeneration failed; keeping the existing /etc/openvpn/crl.pem"
else
    echo "ERROR: CRL regeneration failed and no CRL exists; refusing to start without revocation checks"
    exit 1
fi

# Start Certificate API server
echo "Starting Certificate API server..."
python3 /scripts/cert_api.py &
API_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $API_PID 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait a moment for API server to start
sleep 2

# Check if API server started successfully
if kill -0 $API_PID 2>/dev/null; then
    echo "Certificate API server started successfully (PID: $API_PID)"
else
    echo "Failed to start Certificate API server"
    exit 1
fi

echo "Starting OpenVPN server..."
echo "Note: iptables masquerade should be configured on the host system"
# Start OpenVPN server (this will block)
exec openvpn --config /etc/openvpn/server/server.conf
