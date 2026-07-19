# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2026-07-20

### Fixed

- **Connection history summary cards were blank**: the connection-history view passed an empty statistics context, so the "total connections", "currently connected" and "unique users" cards showed no values. The view now computes these aggregates and the cards display real numbers.
- **Mobile layout of the connection history page**: summary cards and the filter fields now stack in a single column on small screens instead of being squeezed into narrow half-width columns; the pagination bar wraps onto multiple rows so the previous/next controls are no longer clipped off-screen; and filter/export buttons wrap instead of breaking their labels across lines.

## [1.1.1] - 2026-07-19

### Fixed

- **VPN connection history page no longer redirects away**: the admin connection-history view raised a template error and bounced back to the home page because its pagination context was incomplete (missing `per_page`/`has_prev`/`has_next`/`prev_page`/`next_page`) and the filter context was empty. The page now renders the history table with working pagination.
- **Mobile table readability**: table cells in scrollable tables no longer wrap onto multiple lines on small screens; each row stays on one line and the table scrolls horizontally.

### Changed

- Removed the redundant "Admin Home" / "Back to admin" buttons from admin content pages (certificate list, revoked list, audit logs, system status, connection history); navigation is consolidated into the header, which already provides this link. Contextual links (e.g. "Revoked List") are kept.

## [1.1.0] - 2026-07-19

### Added

- **Responsive WebUI layout for mobile devices**: navigation collapses to a stacked layout, dashboard cards reflow into fewer columns, and wide tables scroll horizontally within their own container instead of overflowing the page. Desktop rendering is unchanged.

### Fixed

- Approved certificates heading rendered a literal `{count}` placeholder (e.g. `(3 {count} certificates)`) because the count-aware translation string was invoked without its `count` argument. It now reads `(3 certificates)` / `(3 件)`.

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
