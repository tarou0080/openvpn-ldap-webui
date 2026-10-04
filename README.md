# OpenVPN LDAP WebUI

LDAP-integrated OpenVPN certificate management WebUI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

English | [日本語](README.ja.md)

## Overview

OpenVPN LDAP WebUI is a web-based certificate management system for OpenVPN that integrates with LDAP authentication. Users can request VPN certificates for their devices through a self-service portal, and administrators can approve or reject requests through an admin interface.

## Key Features

### User Features
- **Certificate Request**: Request certificates by specifying device names
- **Certificate Download**: Download approved certificates as .ovpn files
- **Certificate List**: View status of your certificates
- **Re-approval Request**: Request re-approval for expired certificates

### Administrator Features
- **Certificate Approval/Rejection**: Review and process user requests
- **Certificate Revocation**: Revoke issued certificates
- **VPN Connection History**: View real-time connection status and history
- **Audit Logs**: Review all certificate operations
- **System Status**: Monitor log parser scheduler status

### Integration & Security
- **LDAP Authentication**: Seamless integration with LDAP/Active Directory
- **Automated Log Analysis**: Automatic parsing of OpenVPN logs every 15 minutes
- **Certificate Lifecycle Management**: Complete workflow from request to revocation
- **Audit Trail**: Comprehensive logging of all operations

## Architecture

```
┌─────────────────┐
│  Users/Admins   │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────────┐
│     VPN WebUI (Flask)               │
│  - User Interface                   │
│  - Admin Interface                  │
│  - Certificate Request/Approval     │
│  - VPN Log Analysis & Display       │
└──────┬──────────────────────────────┘
       │ HTTP API (Internal)
       ▼
┌─────────────────────────────────────┐
│   OpenVPN Server Container          │
│  - Certificate API                  │
│  - Certificate Generation/Revocation│
│  - OpenVPN Server                   │
│  - LDAP Authentication              │
└─────────────────────────────────────┘
       │ LDAP
       ▼
┌─────────────────┐
│  LDAP Server    │
│  (AD/OpenLDAP)  │
└─────────────────┘
```

## Components

### 1. VPN WebUI (`vpn-webui`)
- **Language**: Python 3 / Flask
- **Database**: SQLite
- **Features**:
  - Certificate request management
  - Approval workflow
  - VPN connection log analysis
  - Audit logging

### 2. OpenVPN Server (`openvpn-server`)
- **Network Mode**: host mode
- **Features**:
  - OpenVPN Server (UDP)
  - Certificate generation/revocation API (internal port 8080)
  - LDAP authentication
  - EasyRSA 3.2.1 for certificate management

### 3. Automated Log Analysis
- **Scheduler**: vpn_log_scheduler.py
- **Parser**: parse_vpn_logs.py
- **Frequency**: Every 15 minutes (default)
- **Function**: Extract connection/disconnection info from OpenVPN logs

## Quick Start

### Prerequisites

- Linux (Rocky Linux 9 or compatible)
- Podman / podman-compose
- firewalld
- **LDAP server (Active Directory or OpenLDAP) — required, cannot be disabled**
  - VPN client authentication always goes through LDAP; certificate-only mode is not supported
  - See [docs/LDAP_SETUP.md](docs/LDAP_SETUP.md) for setup details
- **Authenticating reverse proxy (e.g., Authelia) — required for WebUI access**
  - The WebUI authenticates users via `Remote-User` / `Remote-Groups` HTTP headers injected by the proxy
  - Direct HTTP access (without the proxy) returns 401 Unauthorized
  - See [docs/SETUP.md](docs/SETUP.md) for a minimal nginx + Authelia configuration example

### Installation

1. **Clone the repository**

```bash
cd /srv
git clone <your-repository-url>
cd openvpn-ldap-webui
```

2. **Configure environment variables**

```bash
cp .env.example .env
vi .env  # Edit according to your environment
```

Key settings:
- `BIND_IP`: VPN server bind IP
- `OPENVPN_PORT`: External port
- `OPENVPN_REMOTE_HOST`: Connection hostname for client config
- `HOME_NETWORK` / `HOME_NETMASK`: Your network settings
- `CERT_API_SECRET`: Certificate API secret key
- **LDAP settings**: `LDAP_SERVER`, `LDAP_BASE_DN`, `LDAP_BIND_USER`, `LDAP_BIND_PASSWORD`, `LDAP_VPN_GROUP`

3. **Host configuration**

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions.

**Required:**
- firewalld configuration (masquerade, port forwarding, rich rules)
- sysctl configuration (rp_filter)
- Routing configuration

4. **Start containers**

```bash
podman-compose up -d
```

> **Note**: The `start-openvpn.sh` entrypoint waits (blocks) until the CA certificate exists.
> The container will not finish starting until you complete the initialization step below.

5. **Initialize PKI (first time only)**

Run the initialization script to generate the CA and server certificates:

```bash
podman exec -it openvpn-server /scripts/init-openvpn.sh
```

This generates:
- CA certificate
- Server certificate
- DH parameters
- TLS-AUTH key

After initialization, restart the containers so the OpenVPN server starts with the new PKI:

```bash
podman-compose restart
```

6. **Access**

The WebUI requires an authenticating reverse proxy (e.g., Authelia with nginx) to inject
`Remote-User` and `Remote-Groups` headers. Direct access without the proxy returns 401.

- **User Portal**: proxied via your reverse proxy (internally `http://<BIND_IP>:<WEBUI_PORT>/`)
- **Admin Portal**: proxied via your reverse proxy (internally `http://<BIND_IP>:<WEBUI_PORT>/admin`). Can optionally be moved to its own domain with `ADMIN_DOMAIN` (see docs/CONFIGURATION.md)

See [docs/SETUP.md](docs/SETUP.md) for the reverse proxy configuration.

## Documentation

- [Setup Guide](docs/SETUP.md) - Detailed host configuration
- [Configuration Guide](docs/CONFIGURATION.md) - Configuration options and customization
- [LDAP Setup Guide](docs/LDAP_SETUP.md) - LDAP integration configuration

### Japanese Documentation

- [セットアップガイド](docs/SETUP.ja.md) - 詳細なホスト設定
- [設定ガイド](docs/CONFIGURATION.ja.md) - 設定オプションとカスタマイズ
- [LDAP設定ガイド](docs/LDAP_SETUP.ja.md) - LDAP統合の詳細設定

## Certificate Lifecycle

1. **Request** (User): Submit certificate request with device name
2. **Approval** (Admin): Review and approve/reject request
3. **Generation** (Automatic): Certificate automatically generated upon approval
4. **Download** (User): Download .ovpn file
5. **Usage**: Connect via VPN
6. **Revocation** (Admin): Revoke certificate if needed

### Certificate Validity

- **CA Certificate**: 3650 days (~10 years)
- **Client Certificate**: 825 days (~2 years 3 months)
- **CRL**: 3650 days (~10 years)

Validity periods can be changed in `.env`.

## Directory Structure

```
openvpn-ldap-webui/
├── compose.yml              # Docker Compose configuration
├── .env                     # Environment variables
├── README.md               # This file
├── LICENSE                 # MIT License
├── docs/                   # Documentation
│   ├── SETUP.md           # Setup guide
│   └── CONFIGURATION.md   # Configuration guide
├── config/                 # Container configuration
│   └── openvpn/           # OpenVPN container
│       ├── Dockerfile
│       └── start-openvpn.sh
├── webui/                  # WebUI container
│   ├── Dockerfile
│   ├── app.py              # Flask application
│   ├── routes_*.py         # Routing
│   ├── templates/          # HTML templates
│   └── translations/       # i18n message files
├── scripts/               # Operational scripts
│   ├── init-openvpn.sh           # Initial setup
│   ├── generate-client-cert.sh   # Certificate generation
│   ├── revoke-client-cert.sh     # Certificate revocation
│   ├── cert_api.py               # Certificate API
│   ├── ldap_auth.py              # LDAP authentication
│   ├── parse_vpn_logs.py         # Log parsing
│   └── vpn_log_scheduler.py      # Log parser scheduler
└── data/                  # Persistent data (.gitignore)
    ├── db/                # SQLite database
    ├── certs/             # Certificate data
    ├── logs/              # WebUI logs
    └── openvpn-logs/      # OpenVPN logs
```

## Logging

### VPN Connection Logs

- **Analysis Frequency**: Every 15 minutes (default)
- **Storage**: SQLite DB (`vpn_connections` table)
- **Display**: Admin Portal > VPN Connection History

### Audit Logs

All certificate operations (request, approval, rejection, revocation, download) are logged.

- **Storage**: SQLite DB (`audit_logs` table)
- **Display**: Admin Portal > Audit Logs

## Troubleshooting

**Q: Cannot connect to VPN**
```bash
# Check OpenVPN logs (replace <clone-dir> with your actual clone directory)
tail -50 <clone-dir>/data/openvpn-logs/openvpn.log

# Check if port is open
ss -ulnp | grep <OPENVPN_PORT>
firewall-cmd --zone=public --query-port=<OPENVPN_PORT>/udp
```

**Q: Cannot access home network**
```bash
# Check masquerade
iptables -t nat -L POSTROUTING -n -v | grep 10.8.0

# Check routing
ip route get <your-network-ip>
```

**Q: LDAP authentication fails**
```bash
# Check LDAP settings
grep LDAP .env

# Check OpenVPN container logs
podman logs openvpn-server | grep -i ldap

# Test LDAP connection
podman exec -it openvpn-server python3 /scripts/ldap_auth.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

your-username

## Acknowledgments

This project was developed with the assistance of Claude (Anthropic's AI assistant).
