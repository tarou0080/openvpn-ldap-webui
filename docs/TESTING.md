# Local Test Environment Setup

This document describes how to set up and run a local, self-contained test environment using Docker Compose.

This environment includes the VPN Web UI, OpenVPN server, and mock services for OpenLDAP and a reverse proxy (Nginx).

## Prerequisites

- Docker and Docker Compose
- Or, Podman and Podman Compose

## Setup

1.  **Copy the environment file:**

    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file for the test environment:**

    Open the `.env` file and set the following variables to work with the test LDAP server:

    ```dotenv
    # Use a loopback or non-public IP
    BIND_IP=127.0.0.1

    # Test LDAP Server Settings
    LDAP_SERVER=127.0.0.1
    LDAP_BASE_DN=dc=test,dc=example,dc=com
    LDAP_BIND_USER=cn=admin,dc=test,dc=example,dc=com
    LDAP_BIND_PASSWORD=admin
    LDAP_VPN_GROUP=cn=VPN-Users,ou=groups,dc=test,dc=example,dc=com
    ```

## How to Run

Please run one of the following commands, depending on your environment.

### Docker Compose

```bash
docker compose -f compose.yml -f compose.test.yml up -d --build
```

### Podman Compose

```bash
podman-compose -f compose.yml -f compose.test.yml up -d --build
```

## Access the Web UI

The test environment simulates user authentication by using different URL paths. No actual login is required.

-   **To access as a normal user:**
    Open your browser and go to `http://localhost/`
    (Simulated user: `testuser`)

-   **To access as an administrator:**
    Open your browser and go to `http://localhost/admin/`
    (Simulated user: `testadmin`)

## Test Accounts

The OpenLDAP service is pre-populated with the following users:

-   **Normal User:**
    -   **Username:** `testuser`
    -   **Password:** `password`
    -   **Groups:** `VPN-Users`
-   **Admin User:**
    -   **Username:** `testadmin`
    -   **Password:** `password`
    -   **Groups:** `VPN-Users`, `VPN-Admins`

## How to Stop

Please run one of the following commands, depending on your environment.

### Docker Compose

```bash
docker compose -f compose.yml -f compose.test.yml down
```

### Podman Compose

```bash
podman-compose -f compose.yml -f compose.test.yml down
```

## Full Environment Cleanup

To completely remove the test environment and free up disk space, you need to remove containers, networks, and **volumes**. Use the `-v` option.

**Note:** This action will destroy all data, including generated certificates and configurations.

### Docker Compose

```bash
docker compose -f compose.yml -f compose.test.yml down -v
```

### Podman Compose

```bash
podman-compose -f compose.yml -f compose.test.yml down -v
```
