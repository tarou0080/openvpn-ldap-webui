#!/bin/bash
set -e

# Argument check
if [ $# -ne 1 ]; then
    echo "Usage: $0 <cert_serial>"
    echo "Example: $0 johndoe-laptop"
    exit 1
fi

CERT_SERIAL="$1"

# Set default values for environment variables
EASYRSA_VERSION=${EASYRSA_VERSION:-3.2.1}
EASYRSA_CRL_DAYS=${EASYRSA_CRL_DAYS:-180}

echo "=== Starting client certificate revocation ==="
echo "Certificate serial: $CERT_SERIAL"

# Move to working directory
cd /etc/openvpn/easy-rsa/${EASYRSA_VERSION}

# Check if certificate file exists
CLIENT_CERT="/etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/issued/${CERT_SERIAL}.crt"
if [ ! -f "$CLIENT_CERT" ]; then
    echo "ERROR: Certificate file not found: $CLIENT_CERT"
    exit 1
fi

# Set environment variables
export EASYRSA_BATCH="1"
export EASYRSA_CRL_DAYS

echo "Revoking certificate..."

# Revoke certificate
./easyrsa revoke "$CERT_SERIAL"

echo "Updating CRL (Certificate Revocation List)..."

# Generate CRL
./easyrsa gen-crl

echo "Deleting client configuration file..."

# Delete .ovpn file
OVPN_FILE="/etc/openvpn/client-configs/${CERT_SERIAL}.ovpn"
if [ -f "$OVPN_FILE" ]; then
    rm -f "$OVPN_FILE"
    echo "Deleted: $OVPN_FILE"
else
    echo "WARNING: .ovpn file not found: $OVPN_FILE"
fi

# Copy CRL file to a location OpenVPN can read
CRL_SOURCE="/etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/crl.pem"
CRL_DEST="/etc/openvpn/crl.pem"

if [ -f "$CRL_SOURCE" ]; then
    cp "$CRL_SOURCE" "$CRL_DEST"
    chown openvpn:openvpn "$CRL_DEST"
    chmod 644 "$CRL_DEST"
    echo "CRL file updated: $CRL_DEST"
else
    echo "ERROR: CRL file was not generated"
    exit 1
fi

echo "=== Client certificate revocation complete ==="
echo "Revoked certificate: $CERT_SERIAL"
echo "CRL file: $CRL_DEST"
echo "CRL validity: ${EASYRSA_CRL_DAYS} days"

exit 0