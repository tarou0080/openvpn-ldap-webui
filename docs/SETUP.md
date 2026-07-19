# Host Setup Guide

This document describes the required host-side configuration for running the OpenVPN LDAP WebUI system.

English | [日本語](SETUP.ja.md)

## Prerequisites

- Rocky Linux 9 (or compatible Linux distribution)
- Podman and podman-compose installed
- firewalld enabled
- LDAP server (Active Directory or OpenLDAP) accessible from the host

**Note**: LDAP authentication is required for VPN connections. See the [LDAP Setup Guide](LDAP_SETUP.md) for detailed LDAP configuration.

## Required Host Configuration

### 1. Firewalld Configuration

Configure firewalld to allow VPN traffic and enable masquerading:

```bash
# Add a source-restricted rich rule for VPN network masquerading.
# Using a rich rule with "source address" limits masquerade to VPN traffic only.
# Enabling masquerade globally on the public zone would also masquerade traffic
# from other container networks and is NOT recommended.
# 10.8.0.0/24 is the default VPN client network (VPN_NETWORK in .env)
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="10.8.0.0/24" masquerade'

# Open the OpenVPN port (adjust to match OPENVPN_PORT in .env)
firewall-cmd --permanent --zone=public --add-port=1194/udp

# Reload firewall configuration
firewall-cmd --reload

# Verify configuration
firewall-cmd --zone=public --list-all
```

**Note**: Replace `1194` with your configured `OPENVPN_PORT` from `.env`.

### 2. Sysctl Configuration (rp_filter)

Configure reverse path filtering to allow VPN traffic:

```bash
# Create sysctl configuration for VPN
cat > /etc/sysctl.d/99-vpn.conf << 'EOF'
# VPN Configuration

# Enable IP forwarding (required for VPN traffic routing)
net.ipv4.ip_forward=1

# Disable rp_filter on the podman bridge interface
# Replace 'podmanX' with your actual podman bridge interface name
net.ipv4.conf.podmanX.rp_filter=0

# Disable rp_filter on the host's physical interface
# Replace 'ethX' with your actual physical interface name
net.ipv4.conf.ethX.rp_filter=0
EOF

# Apply the configuration
sysctl -p /etc/sysctl.d/99-vpn.conf
```

**Important**: 
- Replace `podmanX` with your actual podman bridge interface name (check with `ip a | grep podman`)
- Replace `ethX` with your actual physical network interface name (check with `ip a`)
- Common physical interface names: `eth0`, `ens3`, `enp0s3`, etc.

### 3. Routing Configuration

If you need VPN clients to access networks beyond the VPN server:

```bash
# Add route to your internal network
# Replace values according to your network topology
nmcli connection modify <interface-name> +ipv4.routes "<network> <gateway>"

# Example: Route 192.168.0.0/16 network via gateway 192.168.1.1
# nmcli connection modify eth0 +ipv4.routes "192.168.0.0/16 192.168.1.1"

# Verify the configuration
nmcli connection show <interface-name> | grep ipv4.routes

# Apply changes (this may briefly interrupt connectivity)
# nmcli connection up <interface-name>
```

**Note**: 
- This step is only required if VPN clients need to access networks other than the VPN server's local network
- The network and gateway should match `HOME_NETWORK`, `HOME_NETMASK`, and `HOME_GATEWAY` in `.env`
- Adjust the interface name to match your environment

## Container Deployment

Once the host is configured, start the containers:

```bash
cd /srv/openvpn-ldap-webui
podman-compose up -d
```

## Verification

### 1. Verify OpenVPN Server

```bash
# Check if OpenVPN is listening on the correct IP and port
ss -ulnp | grep <OPENVPN_PORT>
# Expected: Should show the BIND_IP:OPENVPN_PORT

# Verify tun interface is created
ip a | grep tun
# Expected: tun0 interface should exist

# Check masquerade rules
iptables -t nat -L POSTROUTING -n -v | grep 10.8.0
# Expected: Should show rules with packet counters increasing during VPN usage

# Verify routing table
ip route | grep tun0
# Expected: Should show routes to VPN network via tun0
```

### 2. VPN Connection Test

After setting up a client certificate:

1. Connect via VPN client
2. From the VPN client, test connectivity:
   ```bash
   # Test connectivity to VPN server's internal network
   ping <your-internal-gateway>
   
   # Test name resolution (if DNS is configured)
   nslookup <hostname> <your-dns-server>
   ```

## Troubleshooting

### Cannot Connect to VPN

```bash
# Check OpenVPN logs
tail -50 /srv/openvpn-ldap-webui/data/openvpn-logs/openvpn.log

# Verify firewall port is open
firewall-cmd --zone=public --query-port=<OPENVPN_PORT>/udp

# Check if OpenVPN process is running
podman ps | grep openvpn-server

# Inspect OpenVPN container logs
podman logs openvpn-server
```

### VPN Connects but Cannot Access Internal Network

```bash
# Check if packets are reaching tun0
tcpdump -i tun0 -n icmp

# Verify masquerade is working
iptables -t nat -L POSTROUTING -n -v | grep 10.8.0
# If packet counters are 0, masquerade is not working

# Verify routing
ip route get <internal-network-ip>

# Check rp_filter settings
sysctl net.ipv4.conf.all.rp_filter
sysctl net.ipv4.conf.<interface>.rp_filter
```

### WebUI Not Accessible

```bash
# Check if WebUI container is running
podman ps | grep vpn-webui

# Check WebUI logs
podman logs vpn-webui

# Verify WebUI is listening on the correct port
ss -tlnp | grep 5000

# Test local connectivity
curl -I http://<BIND_IP>:5000/
```

## Important Environment Variables

Reference the following key variables in `.env`:

```bash
# Network Configuration
BIND_IP=192.0.2.10              # VPN server bind IP
OPENVPN_PORT=1194               # External OpenVPN port
VPN_NETWORK=10.8.0.0            # VPN client network
VPN_NETMASK=255.255.255.0

# LDAP Authentication (required)
LDAP_SERVER=ldap.example.com    # LDAP server
LDAP_BASE_DN=dc=example,dc=com  # LDAP base DN
LDAP_BIND_USER=CN=BindUser,...  # LDAP bind user
LDAP_VPN_GROUP=CN=VPN-Users,... # VPN access group

# Internal Network Settings (optional)
HOME_NETWORK=192.168.0.0        # Your internal network
HOME_NETMASK=255.255.0.0
HOME_DNS_SERVER=192.168.1.1     # Internal DNS server
HOME_GATEWAY=192.168.1.1        # Internal gateway
```

For detailed LDAP configuration, see the [LDAP Setup Guide](LDAP_SETUP.md).

## Architecture Overview

```
VPN Clients (External)
    ↓ UDP <OPENVPN_PORT>
Host IP (BIND_IP)
    ↓
OpenVPN Server (host network mode)
    ↓ tun0 (VPN_NETWORK)
    ↓ Masquerade
Internal Network (HOME_NETWORK)
```

## Reverse Proxy (required for WebUI)

The WebUI authenticates users via `Remote-User` and `Remote-Groups` HTTP headers.
These headers must be injected by an authenticating reverse proxy. Direct access without
the proxy returns 401 Unauthorized.

Set `AUTHELIA_HEADERS=true` in `.env` (already the default in `compose.yml`) so the WebUI
reads `Remote-User` / `Remote-Groups` instead of its own session.

### Minimal nginx + Authelia example

```nginx
# Authelia authentication check (adjust URL to your Authelia endpoint)
location /authelia {
    internal;
    proxy_pass http://authelia:9091/api/verify;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header X-Original-URL $scheme://$http_host$request_uri;
}

# WebUI location (example for user portal)
location / {
    auth_request /authelia;
    # Inject user identity headers from Authelia
    auth_request_set $user $upstream_http_remote_user;
    auth_request_set $groups $upstream_http_remote_groups;
    proxy_set_header Remote-User $user;
    proxy_set_header Remote-Groups $groups;

    proxy_pass http://<BIND_IP>:<WEBUI_PORT>;
    proxy_set_header Host $host;
}
```

Replace `<BIND_IP>` and `<WEBUI_PORT>` with the values from your `.env`.
The admin portal should be protected with stricter Authelia policy (e.g., two_factor)
and access limited to the admin group.

## Notes

- OpenVPN server runs with `network_mode: host` for direct network access
- Masquerading is managed through firewalld via source-restricted rich rules
- WebUI runs in its own container network and communicates with the OpenVPN container via internal API
- WebUI requires an authenticating reverse proxy; direct HTTP access returns 401
