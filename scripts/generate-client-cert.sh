#!/bin/bash
set -e

# Argument check
if [ $# -ne 2 ]; then
    echo "Usage: $0 <username> <device_name>"
    echo "Example: $0 johndoe laptop"
    exit 1
fi

USERNAME="$1"
DEVICE_NAME="$2"
CLIENT_NAME="${USERNAME}-${DEVICE_NAME}"

# Set default values for environment variables
EASYRSA_VERSION=${EASYRSA_VERSION:-3.2.1}
EASYRSA_REQ_COUNTRY=${EASYRSA_REQ_COUNTRY:-JP}
EASYRSA_REQ_PROVINCE=${EASYRSA_REQ_PROVINCE:-Tokyo}
EASYRSA_REQ_CITY=${EASYRSA_REQ_CITY:-Tokyo}
EASYRSA_REQ_ORG=${EASYRSA_REQ_ORG:-VPN-Server}
EASYRSA_REQ_OU=${EASYRSA_CLIENT_OU:-VPN-Client}
EASYRSA_CERT_EXPIRE=${EASYRSA_CERT_EXPIRE:-825}
OPENVPN_REMOTE_HOST=${OPENVPN_REMOTE_HOST:-localhost}
OPENVPN_PORT=${OPENVPN_PORT:-1194}

echo "=== Starting client certificate generation ==="
echo "Client Name: $CLIENT_NAME"

# Move to working directory
cd /etc/openvpn/easy-rsa/${EASYRSA_VERSION}

# Set environment variables (export to propagate to child processes)
export EASYRSA_REQ_COUNTRY
export EASYRSA_REQ_PROVINCE
export EASYRSA_REQ_CITY
export EASYRSA_REQ_ORG
export EASYRSA_REQ_EMAIL="${USERNAME}@example.com"
export EASYRSA_REQ_OU
export EASYRSA_REQ_CN="$CLIENT_NAME"
export EASYRSA_BATCH="1"
export EASYRSA_CERT_EXPIRE

echo "Generating client certificate..."

# Generate client certificate
./easyrsa build-client-full "$CLIENT_NAME" nopass

echo "Generating client configuration file..."

# Certificate file paths
CA_CERT="/etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/ca.crt"
CLIENT_CERT="/etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/issued/${CLIENT_NAME}.crt"
CLIENT_KEY="/etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/private/${CLIENT_NAME}.key"
TLS_AUTH="/etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/ta.key"

# Create output directory
mkdir -p "/etc/openvpn/client-configs"

# Generate .ovpn file (add auth-user-pass)
OVPN_FILE="/etc/openvpn/client-configs/${CLIENT_NAME}.ovpn"

# Create base client configuration (set connection destination from environment variables)
cat > "$OVPN_FILE" << OVPNEOF
client
dev tun
proto udp
remote ${OPENVPN_REMOTE_HOST} ${OPENVPN_PORT}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
verb 3

# Encryption settings (enhanced security)
cipher AES-256-GCM
auth SHA256
tls-version-min 1.2

# Enable user authentication (in addition to certificate)
auth-user-pass
OVPNEOF

# Add CA certificate
echo "<ca>" >> "$OVPN_FILE"
cat "$CA_CERT" >> "$OVPN_FILE"
echo "</ca>" >> "$OVPN_FILE"

# Add client certificate
echo "<cert>" >> "$OVPN_FILE"
cat "$CLIENT_CERT" >> "$OVPN_FILE"
echo "</cert>" >> "$OVPN_FILE"

# Add client private key
echo "<key>" >> "$OVPN_FILE"
cat "$CLIENT_KEY" >> "$OVPN_FILE"
echo "</key>" >> "$OVPN_FILE"

# Add TLS auth key
echo "<tls-auth>" >> "$OVPN_FILE"
cat "$TLS_AUTH" >> "$OVPN_FILE"
echo "</tls-auth>" >> "$OVPN_FILE"

# Add key direction
echo "key-direction 1" >> "$OVPN_FILE"

# Set permissions
chown openvpn:openvpn "$OVPN_FILE"
chmod 600 "$OVPN_FILE"

echo "=== Client certificate generation complete ==="
echo "Generated file: $OVPN_FILE"
echo "Client name: $CLIENT_NAME"
echo "File size: $(du -h "$OVPN_FILE" | cut -f1)"
echo "Connect to: ${OPENVPN_REMOTE_HOST}:${OPENVPN_PORT}"
echo "Certificate expiration: ${EASYRSA_CERT_EXPIRE} days"

# Final check
if [ -f "$OVPN_FILE" ]; then
    echo "SUCCESS: .ovpn file generated successfully (enhanced security)"
    exit 0
else
    echo "ERROR: Failed to generate .ovpn file"
    exit 1
fi