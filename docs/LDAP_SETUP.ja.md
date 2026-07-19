# LDAP設定ガイド

このドキュメントでは、OpenVPN LDAP WebUIとLDAPサーバー（Active DirectoryまたはOpenLDAP）の統合設定について詳しく説明します。

[English](LDAP_SETUP.md) | 日本語

## 概要

OpenVPN LDAP WebUIは、VPN接続時にLDAP/Active Directory認証を使用します。証明書とユーザー名/パスワードの両方による二要素認証を実現します。

## LDAP認証フロー

```
VPNクライアント
    ↓ OpenVPN接続試行（証明書 + ユーザー名/パスワード）
OpenVPN Server
    ↓ 証明書検証（成功）
    ↓ ldap_auth.pyスクリプト呼び出し
LDAP Server
    ↓ ユーザー検証
    ↓ グループメンバーシップ確認
    ↓ 認証結果を返す
OpenVPN Server
    ↓ 接続許可/拒否
```

## 前提条件

### Active Directoryの場合

- Active Directoryサーバーが稼働中
- VPNサーバーからADへのネットワーク到達性
- 検索用のバインドユーザー（読み取り権限のみでOK）
- VPNアクセス用のセキュリティグループ

### OpenLDAPの場合

- OpenLDAPサーバーが稼働中
- VPNサーバーからLDAPへのネットワーク到達性
- 検索用のバインドユーザー
- VPNアクセス用のグループ
- **`memberOf` overlayの有効化が必要** — `ldap_auth.py` はグループメンバーシップを `memberOf`
  属性のDN完全一致で確認します。OpenLDAPはデフォルトで `memberOf` を付与しないため、
  `memberof` overlayを有効化する必要があります。有効化しないと、ユーザーが正しくグループに
  追加されていてもグループメンバーシップチェックが常に失敗します。

## 設定手順

### ステップ1: LDAPグループの作成

#### Active Directoryの場合

1. Active Directory Users and Computersを開く
2. 新しいセキュリティグループを作成:
   - 名前: `VPN-Users`
   - グループスコープ: `Global` または `Universal`
   - グループの種類: `Security`
3. VPNアクセスを許可するユーザーをこのグループに追加

#### OpenLDAPの場合

LDIFファイルの例:

```ldif
dn: cn=VPN-Users,ou=Groups,dc=example,dc=com
objectClass: groupOfNames
cn: VPN-Users
description: VPN Access Group
member: uid=user1,ou=Users,dc=example,dc=com
member: uid=user2,ou=Users,dc=example,dc=com
```

適用:
```bash
ldapadd -x -D "cn=admin,dc=example,dc=com" -W -f vpn-group.ldif
```

### ステップ2: バインドユーザーの作成

#### Active Directoryの場合

1. 新しいユーザーを作成（例: `BindUser`）
2. 権限設定:
   - 通常のドメインユーザー権限でOK
   - 特別な権限は不要（読み取りのみ）
3. パスワード設定:
   - 強固なパスワードを設定
   - 「パスワードを無期限にする」を有効化

#### OpenLDAPの場合

LDIFファイルの例:

```ldif
dn: cn=BindUser,dc=example,dc=com
objectClass: simpleSecurityObject
objectClass: organizationalRole
cn: BindUser
description: LDAP Bind User for VPN Authentication
userPassword: {SSHA}your-hashed-password
```

### ステップ3: .env ファイルの設定

`.env.example`をコピーして編集:

```bash
cp .env.example .env
vi .env
```

#### Active Directoryの設定例

```bash
# LDAP認証設定
LDAP_SERVER=ad.example.com
LDAP_PORT=389

# Base DN（組織のドメインに合わせて変更）
LDAP_BASE_DN=dc=example,dc=com

# Bind User（フルDN形式で指定）
LDAP_BIND_USER=CN=BindUser,CN=Users,DC=example,DC=com
LDAP_BIND_PASSWORD=your-strong-password

# Active Directory用の検索フィルター（通常変更不要）
LDAP_USER_FILTER=(&(objectClass=user)(|(sAMAccountName={username})(userPrincipalName={username})))

# VPNグループのDN（作成したグループに合わせて変更）
LDAP_VPN_GROUP=CN=VPN-Users,CN=Users,DC=example,DC=com
```

#### OpenLDAPの設定例

```bash
# LDAP認証設定
LDAP_SERVER=ldap.example.com
LDAP_PORT=389

# Base DN
LDAP_BASE_DN=dc=example,dc=com

# Bind User
LDAP_BIND_USER=cn=BindUser,dc=example,dc=com
LDAP_BIND_PASSWORD=your-strong-password

# OpenLDAP用の検索フィルター
LDAP_USER_FILTER=(&(objectClass=inetOrgPerson)(uid={username}))

# VPNグループのDN
LDAP_VPN_GROUP=cn=VPN-Users,ou=Groups,dc=example,dc=com
```

### ステップ4: LDAP接続のテスト

コンテナを起動する前にLDAP接続をテストすることをお勧めします:

#### ldapsearchコマンドでのテスト

```bash
# Active Directoryの場合
ldapsearch -x -H ldap://ad.example.com:389 \
  -D "CN=BindUser,CN=Users,DC=example,DC=com" \
  -w "your-password" \
  -b "DC=example,DC=com" \
  "(&(objectClass=user)(sAMAccountName=testuser))"

# OpenLDAPの場合
ldapsearch -x -H ldap://ldap.example.com:389 \
  -D "cn=BindUser,dc=example,dc=com" \
  -w "your-password" \
  -b "dc=example,dc=com" \
  "(&(objectClass=inetOrgPerson)(uid=testuser))"
```

成功すれば、ユーザー情報が表示されます。

### ステップ5: コンテナの起動

```bash
podman-compose up -d
```

### ステップ6: LDAP認証のテスト

OpenVPNサーバーコンテナ内で認証スクリプトをテスト:

```bash
# テスト用の認証ファイルを作成
echo "testuser" > /tmp/test_auth.txt
echo "testpassword" >> /tmp/test_auth.txt

# 認証スクリプトを実行
podman exec -it openvpn-server python3 /scripts/ldap_auth.py /tmp/test_auth.txt

# クリーンアップ
rm /tmp/test_auth.txt
```

成功時の出力例:
```
2024-01-01 12:00:00 - INFO - Found user: testuser, DN: CN=Test User,CN=Users,DC=example,DC=com
2024-01-01 12:00:00 - INFO - Authentication successful for user: testuser
2024-01-01 12:00:00 - INFO - VPN authentication successful: testuser
```

## 高度な設定

### SSL/TLS接続の有効化

本番環境では、LDAPS（LDAP over SSL）の使用を推奨します。

#### scripts/ldap_auth.py の編集

```python
# SSL/TLS設定
server = Server(LDAP_SERVER, port=636, use_ssl=True, tls=tls_configuration)
```

#### .env の設定

```bash
LDAP_PORT=636
```

### カスタム検索フィルター

異なるLDAPスキーマに対応するため、検索フィルターをカスタマイズできます。

#### 例1: 複数の属性で検索

```bash
LDAP_USER_FILTER=(&(objectClass=person)(|(uid={username})(mail={username}@example.com)))
```

#### 例2: 組織単位（OU）の制限

```bash
LDAP_USER_FILTER=(&(objectClass=user)(sAMAccountName={username})(memberOf=CN=Employees,OU=Users,DC=example,DC=com))
```

#### 例3: 特定の属性値のチェック

```bash
LDAP_USER_FILTER=(&(objectClass=user)(sAMAccountName={username})(employeeType=FullTime))
```

### 複数のVPNグループ対応

複数のグループメンバーにVPNアクセスを許可する場合、`ldap_auth.py`を編集:

```python
# 複数グループの定義
VPN_GROUPS = [
    'CN=VPN-Users,CN=Users,DC=example,DC=com',
    'CN=Administrators,CN=Users,DC=example,DC=com',
    'CN=RemoteWorkers,CN=Users,DC=example,DC=com'
]

# チェックロジック
if not any(group in user_groups for group in VPN_GROUPS):
    logger.warning(f"User {username} is not in any VPN group")
    return False, "Access denied: Not in VPN groups"
```

### ネストされたグループのサポート

Active Directoryでネストされたグループを使用する場合:

```python
# 検索フィルターで再帰的なグループメンバーシップを使用
search_filter = f'(&(objectClass=user)(sAMAccountName={username})(memberOf:1.2.840.113556.1.4.1941:=CN=VPN-Users,CN=Users,DC=example,DC=com))'
```

`1.2.840.113556.1.4.1941`はADの特殊なOIDで、ネストされたグループメンバーシップを再帰的に検索します。

## トラブルシューティング

### 問題1: バインドに失敗する

**症状**: `Admin bind failed`

**確認事項**:
```bash
# LDAP設定を確認
grep LDAP .env

# LDAPサーバーへの接続確認
podman exec -it openvpn-server nc -zv $LDAP_SERVER $LDAP_PORT

# バインドユーザーのDN形式を確認
# Active Directoryの場合はCN形式
# OpenLDAPの場合はcn形式
```

### 問題2: ユーザーが見つからない

**症状**: `User not found`

**確認事項**:
```bash
# Base DNが正しいか確認
echo $LDAP_BASE_DN

# 検索フィルターをテスト
ldapsearch -x -H ldap://$LDAP_SERVER:$LDAP_PORT \
  -D "$LDAP_BIND_USER" -w "$LDAP_BIND_PASSWORD" \
  -b "$LDAP_BASE_DN" \
  "(&(objectClass=user)(sAMAccountName=testuser))"
```

### 問題3: グループメンバーシップのチェックに失敗

**症状**: `Access denied: Not in VPN-Users group`

**確認事項**:
```bash
# ユーザーのグループメンバーシップを確認
ldapsearch -x -H ldap://$LDAP_SERVER:$LDAP_PORT \
  -D "$LDAP_BIND_USER" -w "$LDAP_BIND_PASSWORD" \
  -b "$LDAP_BASE_DN" \
  "(&(objectClass=user)(sAMAccountName=testuser))" memberOf

# グループのDNが完全一致するか確認（大文字小文字、スペースに注意）
```

### 問題4: TLS/SSL接続エラー

**症状**: `SSL/TLS connection failed`

**解決方法**:

証明書検証を一時的に無効化（テスト目的のみ）:
```python
tls_configuration = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
```

本番環境では適切な証明書を使用:
```python
tls_configuration = Tls(
    ca_certs_file='/path/to/ca-cert.pem',
    validate=ssl.CERT_REQUIRED
)
```

### 問題5: タイムアウト

**症状**: 認証に長時間かかる、またはタイムアウト

**解決方法**:
```python
# ldap_auth.pyにタイムアウト設定を追加
server = Server(
    LDAP_SERVER, 
    port=LDAP_PORT, 
    use_ssl=False, 
    tls=tls_configuration,
    connect_timeout=5  # 5秒でタイムアウト
)
```

## デバッグモード

詳細なログを確認するには、ログレベルをDEBUGに変更:

```python
# scripts/ldap_auth.py
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
```

コンテナを再起動:
```bash
podman-compose restart openvpn-server
```

ログを確認:
```bash
podman logs -f openvpn-server | grep -i ldap
```

## セキュリティのベストプラクティス

1. **最小権限の原則**: バインドユーザーには読み取り権限のみを付与
2. **LDAPS使用**: 本番環境ではSSL/TLS暗号化を使用
3. **強固なパスワード**: バインドユーザーのパスワードは複雑にする
4. **定期的な監査**: LDAP認証ログを定期的に確認
5. **グループベースのアクセス制御**: 個別ユーザーではなくグループで管理
6. **アカウントロックアウト**: ADのロックアウトポリシーを設定
7. **監視**: 認証失敗の異常な増加を監視

## よくある質問

**Q: Active DirectoryとOpenLDAPの両方をサポートできますか？**

A: はい、LDAP_USER_FILTERを適切に設定すれば可能です。ただし、同時に両方は使用できません。

**Q: ユーザー名として何を使用できますか？**

A: デフォルト設定では、sAMAccountName（ADの場合）またはuid（OpenLDAPの場合）を使用します。LDAP_USER_FILTERをカスタマイズすることで、メールアドレスなども使用できます。

**Q: LDAP認証を無効化できますか？**

A: いいえ、このシステムはLDAP認証を前提に設計されています。LDAP認証なしで使用する場合は、別の認証方式を実装する必要があります。

**Q: 証明書だけで認証できますか？**

A: デフォルトでは証明書+LDAP認証の二要素認証です。証明書のみにする場合は、OpenVPN設定から`auth-user-pass`を削除する必要がありますが、セキュリティ上推奨されません。

**Q: LDAP認証のパフォーマンスへの影響は？**

A: LDAP認証は接続確立時のみ実行され、確立後の通信には影響しません。通常、数百ミリ秒程度のオーバーヘッドです。

## 参考資料

- [LDAP3 Documentation](https://ldap3.readthedocs.io/)
- [Active Directory LDAP Syntax Filters](https://social.technet.microsoft.com/wiki/contents/articles/5392.active-directory-ldap-syntax-filters.aspx)
- [OpenLDAP Administrator's Guide](https://www.openldap.org/doc/admin24/)
