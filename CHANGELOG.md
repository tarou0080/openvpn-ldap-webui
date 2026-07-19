# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-19

### Added

- **LDAP-integrated OpenVPN certificate management system** — initial public release
- **Self-service user portal**: certificate request, download, and re-approval request workflow
- **Admin portal**: certificate approval/rejection, revocation, VPN connection history, audit logs, system status
- **LDAP/Active Directory authentication** for VPN connections (certificate + username/password dual authentication)
- **Automated OpenVPN log analysis**: connection/disconnection events parsed every 15 minutes into SQLite
- **Certificate lifecycle management** via EasyRSA 3.x: CA generation, client cert issuance, revocation and CRL management
- **Internal Certificate API** between WebUI and OpenVPN server containers for secure certificate operations
- **Reverse proxy integration**: `Remote-User` / `Remote-Groups` header-based authentication (Authelia-compatible)
- **Multi-language support** (English / Japanese) for WebUI and documentation
- **Configurable admin group** via `ADMIN_GROUP` environment variable
- English and Japanese documentation: SETUP, CONFIGURATION, LDAP_SETUP, TESTING guides
- `.env.example` / `.env.example.ja` with annotated configuration templates

### Security

- CRL validity set to 3650 days by default to prevent silent expiry blocking all VPN clients
- LDAP bind credentials isolated per service (dedicated bind account)
- LDAP settings injected into OpenVPN server config via `setenv` at startup to avoid environment variable leakage
