# Security Policy

## Supported versions

Only the latest release receives fixes. The project is maintained for the author's own deployment (see "Project status" in the README): security fixes and fixes for breakage continue; new features are added only when the author needs them.

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private vulnerability reporting instead:
**Security** tab → **Report a vulnerability** (https://github.com/tarou0080/openvpn-ldap-webui/security/advisories/new).

Include the version, steps to reproduce, and the impact you expect. You will get a reply as soon as possible; there is no fixed SLA because this is a personal project.

## Scope

- **VPN connections** need both a client certificate and the LDAP password of a member of `LDAP_VPN_GROUP`, and revoked certificates are refused. Any way to connect without one of these is in scope.
- **The WebUI has no login of its own.** It trusts the `Remote-User` / `Remote-Groups` headers set by an authenticating reverse proxy (e.g. Authelia) and accepts them only from `TRUSTED_PROXIES`. Reports about exposing the WebUI without such a proxy, or with `TRUSTED_PROXIES` left empty while other hosts can reach it, are out of scope; flaws inside that design are in scope — for example, downloading or acting on another user's certificate, reaching the admin portal without `ADMIN_GROUP`, or script injection into the admin pages.
- **The certificate API** (inside the OpenVPN container) must be reachable only from the WebUI; requests are authenticated with an HMAC of `CERT_API_SECRET`. Ways to issue or revoke certificates without the secret are in scope.
