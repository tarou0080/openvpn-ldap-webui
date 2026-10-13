#!/bin/bash
set -e

echo "=== Starting OpenVPN Server initialization ==="

# Set default values for environment variables
EASYRSA_VERSION=${EASYRSA_VERSION:-3.2.1}
EASYRSA_REQ_COUNTRY=${EASYRSA_REQ_COUNTRY:-JP}
EASYRSA_REQ_PROVINCE=${EASYRSA_REQ_PROVINCE:-Tokyo}
EASYRSA_REQ_CITY=${EASYRSA_REQ_CITY:-Tokyo}
EASYRSA_REQ_ORG=${EASYRSA_REQ_ORG:-VPN-Server}
EASYRSA_REQ_EMAIL=${EASYRSA_REQ_EMAIL:-admin@example.com}
EASYRSA_REQ_OU=${EASYRSA_REQ_OU:-VPN}
EASYRSA_CA_CN=${EASYRSA_CA_CN:-VPN-CA}
EASYRSA_CA_EXPIRE=${EASYRSA_CA_EXPIRE:-3650}
EASYRSA_CERT_EXPIRE=${EASYRSA_CERT_EXPIRE:-825}
VPN_NETWORK=${VPN_NETWORK:-10.8.0.0}
VPN_NETMASK=${VPN_NETMASK:-255.255.255.0}

# Move to working directory
cd /etc/openvpn/easy-rsa/${EASYRSA_VERSION}

echo "Initializing easy-rsa..."
# Force initialize the PKI environment (automate the two-step confirmation)
echo -e "yes\nyes" | ./easyrsa init-pki

echo "Generating CA certificate..."
# Set environment variables for non-interactive mode (export to propagate to child processes)
export EASYRSA_REQ_COUNTRY
export EASYRSA_REQ_PROVINCE
export EASYRSA_REQ_CITY
export EASYRSA_REQ_ORG
export EASYRSA_REQ_EMAIL
export EASYRSA_REQ_OU
export EASYRSA_REQ_CN="${EASYRSA_CA_CN}"
export EASYRSA_BATCH="1"
export EASYRSA_CA_EXPIRE
export EASYRSA_CERT_EXPIRE

# Generate CA certificate (no password)
./easyrsa build-ca nopass

echo "Generating server certificate..."
# Generate server certificate
./easyrsa build-server-full server nopass

echo "Generating DH parameters..."
# Generate DH parameters (may take some time)
./easyrsa gen-dh

echo "Generating TLS-AUTH key..."
# Generate private key for TLS-AUTH
openvpn --genkey secret pki/ta.key

echo "Creating server configuration file..."
# Create server configuration file
cat > /etc/openvpn/server/server.conf << EOF
port 1194
proto udp
dev tun
ca /etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/ca.crt
cert /etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/issued/server.crt
key /etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/private/server.key
dh /etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/dh.pem
tls-auth /etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/ta.key 0

server ${VPN_NETWORK} ${VPN_NETMASK}
ifconfig-pool-persist ipp.txt

keepalive 10 120
user openvpn
group openvpn
persist-key
persist-tun

status /var/log/openvpn/openvpn-status.log
log-append /var/log/openvpn/openvpn.log
verb 3

# Client configuration directory
client-config-dir /etc/openvpn/ccd

# Cipher, LDAP authentication and CRL settings are (re)written by
# start-openvpn.sh on every start, so they cannot go missing.
EOF

echo "Setting permissions..."
# Set permissions
chown -R openvpn:openvpn /etc/openvpn
chown -R openvpn:openvpn /var/log/openvpn

echo "=== OpenVPN Server initialization complete ==="
echo "CA certificate: /etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/ca.crt"
echo "Server certificate: /etc/openvpn/easy-rsa/${EASYRSA_VERSION}/pki/issued/server.crt"
echo "Server configuration: /etc/openvpn/server/server.conf"
echo "CA expiration: ${EASYRSA_CA_EXPIRE} days"
echo "Certificate expiration: ${EASYRSA_CERT_EXPIRE} days"
echo "VPN network: ${VPN_NETWORK} ${VPN_NETMASK}"