# 設定ガイド

このドキュメントでは、OpenVPN LDAP WebUIシステムの設定オプションについて詳しく説明します。

[English](CONFIGURATION.md) | 日本語

## 環境変数

すべての設定は`.env`ファイルで行います。`.env.example`をコピーして、環境に合わせて値を調整してください。

```bash
cp .env.example .env
vi .env
```

## ネットワーク設定

### 基本ネットワーク設定

```bash
# 外部バインドIPアドレス
BIND_IP=192.0.2.10

# 外部ポート
WEBUI_PORT=80              # WebUI外部ポート
OPENVPN_PORT=1194          # OpenVPN外部ポート（UDP）
CERT_API_PORT=8080         # 証明書API外部ポート

# 内部ポート（通常変更不要）
WEBUI_INTERNAL_PORT=5000
OPENVPN_INTERNAL_PORT=1194
CERT_API_INTERNAL_PORT=8080
```

- **BIND_IP**: サービスがバインドするIPアドレス。VPNクライアントからアクセス可能なホスト上のIPアドレスを指定してください。
- **WEBUI_PORT**: Webインターフェースへのアクセスポート
- **OPENVPN_PORT**: VPN接続用ポート。firewalld設定と一致させる必要があります。
- **CERT_API_PORT**: 証明書操作用の内部APIポート

### VPNネットワーク設定

```bash
# VPNクライアントネットワーク設定
VPN_NETWORK=10.8.0.0
VPN_NETMASK=255.255.255.0
```

- **VPN_NETWORK**: VPNクライアント用のネットワークアドレス（デフォルト: 10.8.0.0）
- **VPN_NETMASK**: VPNクライアントネットワークのネットマスク（デフォルト: 255.255.255.0）

この設定により、VPNクライアント用に10.8.0.0/24ネットワークが作成されます。

## ドメイン設定

```bash
# ドメイン設定
ADMIN_DOMAIN=vpnadmin.example.com
USER_DOMAIN=vpn.example.com

# OpenVPN接続先ホスト（.ovpnファイルに記載されます）
OPENVPN_REMOTE_HOST=vpn.example.com
```

- **ADMIN_DOMAIN**: 管理インターフェース用ドメイン（情報提供用）
- **USER_DOMAIN**: ユーザーインターフェース用ドメイン（情報提供用）
- **OPENVPN_REMOTE_HOST**: クライアントが接続するホスト名またはIP。この値は.ovpn設定ファイルに記載されます。

## セキュリティ設定

### アプリケーションシークレット

```bash
# Flask SECRET_KEY
SECRET_KEY=your-secret-key-here

# 証明書API認証シークレット
CERT_API_SECRET=your-api-secret-here
```

安全なランダムキーの生成方法:
```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

- **SECRET_KEY**: Flaskのセッション管理に使用されます。秘密を保持する必要があります。
- **CERT_API_SECRET**: WebUIとOpenVPNコンテナ間のAPI認証に使用されます。

### WebUI管理者グループ

```bash
# WebUI管理者として扱うAD/LDAPグループ名
ADMIN_GROUP=net-vpn-admins
```

- **ADMIN_GROUP**: 管理画面へのアクセスを許可するLDAP/ADグループ名。
  このグループのメンバーはリバースプロキシ経由でログイン後、ナビゲーションバーに
  「管理」リンクが表示されます。値はプロキシが注入する `Remote-Groups` ヘッダー内の
  グループ名（通常はADグループの `cn`）と完全一致させる必要があります。
  デフォルト: `net-vpn-admins`。

## LDAP認証設定

```bash
# LDAPサーバー設定
LDAP_SERVER=ldap.example.com
LDAP_PORT=389

# LDAP Base DN（ユーザー検索の基点）
LDAP_BASE_DN=dc=example,dc=com

# LDAP Bind User（検索用アカウント）
LDAP_BIND_USER=CN=BindUser,CN=Users,DC=example,DC=com
LDAP_BIND_PASSWORD=your-bind-password

# LDAP検索フィルター（{username}がユーザー名に置換されます）
# Active Directory用のデフォルト設定
LDAP_USER_FILTER=(&(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})))

# VPNアクセス許可グループ（このグループのメンバーのみVPN接続可能）
LDAP_VPN_GROUP=CN=VPN-Users,CN=Users,DC=example,DC=com
```

### LDAP設定の詳細

- **LDAP_SERVER**: LDAPサーバーのホスト名またはIPアドレス
- **LDAP_PORT**: LDAPサーバーのポート（通常389、LDAPS使用時は636）
- **LDAP_BASE_DN**: ユーザー検索を開始するベースDN
- **LDAP_BIND_USER**: ユーザー検索に使用するバインドユーザーのフルDN
- **LDAP_BIND_PASSWORD**: バインドユーザーのパスワード
- **LDAP_USER_FILTER**: ユーザー検索に使用するLDAPフィルター
- **LDAP_VPN_GROUP**: VPNアクセスを許可するグループのDN

詳細な設定手順については、[LDAP設定ガイド](LDAP_SETUP.ja.md)を参照してください。

## 証明書・CA設定

### CA証明書情報

```bash
# CA証明書詳細
EASYRSA_REQ_COUNTRY=JP
EASYRSA_REQ_PROVINCE=Tokyo
EASYRSA_REQ_CITY=Tokyo
EASYRSA_REQ_ORG=MyOrganization
EASYRSA_REQ_EMAIL=admin@example.com
EASYRSA_REQ_OU=IT
EASYRSA_CA_CN=MyVPN-CA
```

これらの値はCA証明書に埋め込まれます。組織に合わせて調整してください。

### クライアント証明書情報

```bash
# クライアント証明書の組織単位
EASYRSA_CLIENT_OU=VPN-Client
```

### 証明書有効期限

```bash
# 証明書有効期限（日数）
EASYRSA_CA_EXPIRE=3650        # CA証明書: 10年
EASYRSA_CERT_EXPIRE=825       # クライアント証明書: 約2年
EASYRSA_CRL_DAYS=180          # 証明書失効リスト: 6ヶ月
```

- **EASYRSA_CA_EXPIRE**: CA証明書の有効期間（デフォルト: 10年）
- **EASYRSA_CERT_EXPIRE**: クライアント証明書の有効期間（デフォルト: 825日 ≈ 2年3ヶ月）
- **EASYRSA_CRL_DAYS**: CRLが再生成が必要になるまでの有効期間

**注意**: Apple iOSは証明書の有効期間が825日以下である必要があります。

## 内部ネットワーク設定（オプション）

VPNクライアントから内部ネットワークへのアクセスを許可する場合：

```bash
# 内部ネットワーク設定
HOME_NETWORK=192.168.0.0
HOME_NETMASK=255.255.0.0
HOME_DNS_SERVER=192.168.1.1
HOME_GATEWAY=192.168.1.1
HOME_DOMAIN=internal.example.com
ENABLE_NETBIOS=false
```

- **HOME_NETWORK**: 内部ネットワークのアドレス
- **HOME_NETMASK**: 内部ネットワークのネットマスク
- **HOME_DNS_SERVER**: VPNクライアント用DNSサーバーのIP
- **HOME_GATEWAY**: 内部ネットワークへのルーティング用ゲートウェイIP
- **HOME_DOMAIN**: 内部DNS ドメイン（オプション）
- **ENABLE_NETBIOS**: Windowsネットワーク用NetBIOS名前解決を有効化

これらの設定は以下の用途に使用されます:
1. VPNクライアントへのルート配信
2. クライアント.ovpnファイルのDNS設定
3. サーバー側ルーティングのセットアップ（適切なホスト設定が必要）

## アプリケーション設定

### Flask環境

```bash
FLASK_ENV=production
```

- **production**: 本番環境で使用（デフォルト）
- **development**: デバッグモードを有効化（本番環境では非推奨）

## ログ設定

```bash
# ログローテーション方式
LOG_ROTATION_TYPE=time        # 'time'または'size'

# サイズベースローテーション
LOG_MAX_SIZE_MB=10            # 最大ログファイルサイズ（MB）
LOG_BACKUP_COUNT=30           # 保持するバックアップファイル数

# 時間ベースローテーション
LOG_ROTATION_WHEN=D           # D=日次、W=週次、M=月次
LOG_ROTATION_INTERVAL=1       # 間隔数
```

### ログローテーションタイプ

**時間ベースローテーション**（推奨）:
```bash
LOG_ROTATION_TYPE=time
LOG_ROTATION_WHEN=D           # 日次ローテーション
LOG_ROTATION_INTERVAL=1       # 1日ごと
LOG_BACKUP_COUNT=30           # 30日分のログを保持
```

**サイズベースローテーション**:
```bash
LOG_ROTATION_TYPE=size
LOG_MAX_SIZE_MB=10            # ファイルが10MBに達したらローテーション
LOG_BACKUP_COUNT=10           # 10個のバックアップファイルを保持
```

## ダウンロード有効期限設定

```bash
# 証明書ダウンロード有効期限設定
DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS=24        # 承認後の有効時間
DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS=0   # 初回ダウンロード後の有効時間
```

- **DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS**: 承認後、証明書をダウンロード可能な時間（0 = 無制限）
- **DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS**: 初回ダウンロード後、再ダウンロード可能な時間（0 = 再ダウンロード無効）

設定例:

**承認後24時間ダウンロード可能、再ダウンロード無効**:
```bash
DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS=24
DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS=0
```

**無制限ダウンロード**:
```bash
DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS=0
DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS=0
```

## VPNログ解析設定

```bash
# VPNログ解析スケジューラ設定
VPN_LOG_SCHEDULE_MODE=FIXED          # 'INTERVAL'または'FIXED'
VPN_LOG_SCHEDULE_INTERVAL=15         # 分（INTERVALモード用）
VPN_LOG_SCHEDULE_TIMES=0,15,30,45    # 分（FIXEDモード用）
VPN_LOG_PARSER_TIMEOUT=300           # パーサータイムアウト（秒）
```

### スケジュールモード

**FIXEDモード**（推奨）:
```bash
VPN_LOG_SCHEDULE_MODE=FIXED
VPN_LOG_SCHEDULE_TIMES=0,15,30,45    # 毎時00分、15分、30分、45分に実行
```

**INTERVALモード**:
```bash
VPN_LOG_SCHEDULE_MODE=INTERVAL
VPN_LOG_SCHEDULE_INTERVAL=15         # 15分ごとに実行
```

- **VPN_LOG_PARSER_TIMEOUT**: ログ解析の最大許容時間（デフォルト: 300秒）

## 高度な設定

### パス設定

```bash
# EasyRSAバージョン
EASYRSA_VERSION=3.2.1
```

異なるEasyRSAバージョンを使用する場合以外は、通常変更不要です。

## 設定例

### 最小構成（テスト用）

```bash
BIND_IP=192.0.2.10
OPENVPN_PORT=1194
OPENVPN_REMOTE_HOST=192.0.2.10
SECRET_KEY=<生成されたシークレット>
CERT_API_SECRET=<生成されたシークレット>
LDAP_SERVER=ldap.example.com
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_USER=CN=BindUser,CN=Users,DC=example,DC=com
LDAP_BIND_PASSWORD=<バインドユーザーパスワード>
LDAP_VPN_GROUP=CN=VPN-Users,CN=Users,DC=example,DC=com
```

### 本番環境設定

```bash
# ネットワーク
BIND_IP=203.0.113.10
OPENVPN_PORT=1194
OPENVPN_REMOTE_HOST=vpn.example.com

# セキュリティ
SECRET_KEY=<強力なランダムシークレット>
CERT_API_SECRET=<強力なランダムシークレット>

# LDAP認証
LDAP_SERVER=ad.example.com
LDAP_PORT=389
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_USER=CN=BindUser,CN=Users,DC=example,DC=com
LDAP_BIND_PASSWORD=<強力なパスワード>
LDAP_VPN_GROUP=CN=VPN-Users,CN=Users,DC=example,DC=com

# 証明書
EASYRSA_REQ_COUNTRY=JP
EASYRSA_REQ_PROVINCE=Tokyo
EASYRSA_REQ_CITY=Tokyo
EASYRSA_REQ_ORG=Example Inc
EASYRSA_REQ_EMAIL=vpnadmin@example.com
EASYRSA_CA_CN=Example-VPN-CA

# 内部ネットワークアクセス
HOME_NETWORK=192.168.0.0
HOME_NETMASK=255.255.0.0
HOME_DNS_SERVER=192.168.1.1
HOME_GATEWAY=192.168.1.1

# ロギング
LOG_ROTATION_TYPE=time
LOG_ROTATION_WHEN=D
LOG_BACKUP_COUNT=90

# ダウンロード制限
DOWNLOAD_EXPIRE_FROM_APPROVAL_HOURS=24
DOWNLOAD_EXPIRE_FROM_FIRST_DOWNLOAD_HOURS=0
```

## 設定変更の適用

`.env`を変更した後:

1. **コンテナの再作成**（ほとんどの変更に対して）:
   ```bash
   podman-compose down
   podman-compose up -d
   ```

2. **証明書関連の変更の場合**、再初期化が必要な場合があります:
   ```bash
   # 警告: これにより全ての証明書が再生成されます！
   podman exec -it openvpn-server /scripts/init-openvpn.sh
   ```

## セキュリティのベストプラクティス

1. **シークレットを安全に保管**: `.env`をバージョン管理にコミットしない
2. **強力なランダムキーを使用**: `python3 -c 'import secrets; print(secrets.token_hex(32))'`で生成
3. **HTTPSを使用**: WebUIをTLS対応のリバースプロキシの背後にデプロイ
4. **証明書有効期限の制限**: Appleのガイドライン（最大825日）に従う
5. **定期的なバックアップ**: `/srv/openvpn-ldap-webui/data`を定期的にバックアップ
6. **ログの監視**: 監査ログで不審なアクティビティをチェック
7. **定期的な更新**: コンテナとホストシステムを定期的に更新
8. **LDAP認証の保護**: 本番環境ではLDAPS（LDAP over SSL/TLS）を使用
9. **最小権限の原則**: LDAPバインドユーザーには読み取り権限のみを付与

## 設定問題のトラブルシューティング

### WebUIが起動しない

```bash
# .envの構文エラーを確認
podman logs vpn-webui

# 必須変数が設定されているか確認
grep -E \"SECRET_KEY|CERT_API_SECRET\" .env
```

### OpenVPNが起動しない

```bash
# OpenVPNコンテナのログを確認
podman logs openvpn-server

# ネットワーク設定を確認
grep -E \"BIND_IP|OPENVPN_PORT|VPN_NETWORK\" .env
```

### クライアントが証明書をダウンロードできない

```bash
# ダウンロード有効期限設定を確認
grep DOWNLOAD_EXPIRE .env

# 証明書APIにアクセス可能か確認
curl -I http://localhost:8080/health
```

### LDAP認証が失敗する

```bash
# LDAP設定を確認
grep LDAP .env

# OpenVPNコンテナログでLDAPエラーを確認
podman logs openvpn-server | grep -i ldap

# LDAP接続をテスト
podman exec -it openvpn-server python3 /scripts/ldap_auth.py
```

## 参考資料

- [セットアップガイド](SETUP.ja.md) - ホスト設定の詳細
- [LDAP設定ガイド](LDAP_SETUP.ja.md) - LDAP統合の詳細設定
- [OpenVPN公式ドキュメント](https://openvpn.net/community-resources/)
- [EasyRSAドキュメント](https://easy-rsa.readthedocs.io/)
