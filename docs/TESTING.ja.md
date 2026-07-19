# ローカルテスト環境の構築

このドキュメントは、Docker Compose を使用して、ローカルで完結したテスト環境をセットアップして実行する方法について説明します。

この環境には、VPN Web UI、OpenVPNサーバー、およびOpenLDAPとリバースプロキシ（Nginx）のモックサービスが含まれています。

## 前提条件

- Docker と Docker Compose
- または、Podman と Podman Compose

## セットアップ

1.  **環境ファイルのコピー:**

    ```bash
    cp .env.example.jp .env
    ```

2.  **`.env` ファイルをテスト環境用に編集:**

    `.env` ファイルを開き、テスト用のLDAPサーバーで動作するように次の変数を設定します:

    ```dotenv
    # ループバックIPまたは非公開IPを使用します
    BIND_IP=127.0.0.1

    # テストLDAPサーバー設定
    LDAP_SERVER=127.0.0.1
    LDAP_BASE_DN=dc=test,dc=example,dc=com
    LDAP_BIND_USER=cn=admin,dc=test,dc=example,dc=com
    LDAP_BIND_PASSWORD=admin
    LDAP_VPN_GROUP=cn=VPN-Users,ou=groups,dc=test,dc=example,dc=com
    ```

## 実行方法

環境に応じて、以下のいずれかのコマンドを実行してください。

### Docker Compose

```bash
docker compose -f compose.yml -f compose.test.yml up -d --build
```

### Podman Compose

```bash
podman-compose -f compose.yml -f compose.test.yml up -d --build
```

## Web UIへのアクセス

テスト環境では、異なるURLパスを使用することでユーザー認証をシミュレートします。実際のログインは不要です。

-   **一般ユーザーとしてアクセスする場合:**
    ブラウザを開き、 `http://localhost/` にアクセスします。
    (シミュレートされるユーザー: `testuser`)

-   **管理者としてアクセスする場合:**
    ブラウザを開き、 `http://localhost/admin/` にアクセスします。
    (シミュレートされるユーザー: `testadmin`)

## テスト用アカウント

OpenLDAPサービスには、次のユーザーが事前に登録されています:

-   **一般ユーザー:**
    -   **ユーザー名:** `testuser`
    -   **パスワード:** `password`
    -   **グループ:** `VPN-Users`
-   **管理者ユーザー:**
    -   **ユーザー名:** `testadmin`
    -   **パスワード:** `password`
    -   **グループ:** `VPN-Users`, `VPN-Admins`

## 停止方法

環境に応じて、以下のいずれかのコマンドを実行してください。

### Docker Compose

```bash
docker compose -f compose.yml -f compose.test.yml down
```

### Podman Compose

```bash
podman-compose -f compose.yml -f compose.test.yml down
```

## 環境の完全なクリーンアップ

テスト環境を完全に削除し、ディスクスペースを解放するには、コンテナ、ネットワーク、および **ボリューム** を削除する必要があります。`-v` オプションを使用してください。

**注意:** この操作により、生成された証明書や設定など、すべてのデータが失われます。

### Docker Compose

```bash
docker compose -f compose.yml -f compose.test.yml down -v
```

### Podman Compose

```bash
podman-compose -f compose.yml -f compose.test.yml down -v
```
