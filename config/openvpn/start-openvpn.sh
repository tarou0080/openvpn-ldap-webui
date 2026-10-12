#!/bin/bash
set -e
echo "Starting OpenVPN server..."

# Check if OpenVPN is initialized
if [ ! -f "/etc/openvpn/easy-rsa/3.2.1/pki/ca.crt" ]; then
    echo "OpenVPN not initialized. Please run init script first."
    echo "Waiting for initialization..."
    while [ ! -f "/etc/openvpn/easy-rsa/3.2.1/pki/ca.crt" ]; do
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

# Remove old routing/DNS settings if they exist
sed -i '/^# Auto-generated routing and DNS settings/,/^# End of auto-generated settings/d' "$CONFIG_FILE"

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
sed -i '/^# Auto-generated LDAP auth settings/,/^# End of auto-generated LDAP auth settings/d' "$CONFIG_FILE"

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
# End of auto-generated LDAP auth settings
LDAPEOF
    chmod 600 "$CONFIG_FILE"
    echo "LDAP auth settings added to server.conf"
else
    echo "LDAP_SERVER not set; skipping LDAP setenv block"
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
