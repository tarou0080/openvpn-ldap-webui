# OpenVPN LDAP WebUI

LDAP認証統合OpenVPN証明書管理WebUI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | 日本語

## 概要

OpenVPN LDAP WebUIは、LDAP認証と統合されたOpenVPN用のWeb ベース証明書管理システムです。ユーザーはセルフサービスポータルを通じてデバイス用のVPN証明書を申請でき、管理者は管理インターフェースを通じて申請の承認または拒否を行えます。

## 主な機能

### ユーザー機能
- **証明書申請**: デバイス名を指定して証明書を申請
- **証明書ダウンロード**: 承認された証明書を.ovpnファイルとしてダウンロード
- **証明書一覧**: 自分の証明書のステータスを確認
- **再承認申請**: 期限切れ証明書の再承認を申請

### 管理者機能
- **証明書の承認/拒否**: ユーザー申請のレビューと処理
- **証明書の失効**: 発行済み証明書の失効
- **VPN接続履歴**: リアルタイム接続状況と履歴の確認
- **監査ログ**: 全ての証明書操作の確認
- **システムステータス**: ログパーサースケジューラの状態監視

### 統合とセキュリティ
- **LDAP認証**: LDAP/Active Directoryとシームレスに統合
- **自動ログ解析**: 15分ごとのOpenVPNログの自動解析
- **証明書ライフサイクル管理**: 申請から失効までの完全なワークフロー
- **監査証跡**: 全ての操作の包括的なロギング

## アーキテクチャ

```
┌─────────────────┐
│ ユーザー/管理者  │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────────────────────────┐
│     VPN WebUI (Flask)               │
│  - ユーザーインターフェース          │
│  - 管理インターフェース              │
│  - 証明書申請/承認                   │
│  - VPNログ解析・表示                 │
└──────┬──────────────────────────────┘
       │ HTTP API (内部)
       ▼
┌─────────────────────────────────────┐
│   OpenVPN Server Container          │
│  - 証明書API                         │
│  - 証明書生成/失効                   │
│  - OpenVPN Server                   │
│  - LDAP認証                          │
└─────────┬───────────────────────────┘
          │ LDAP
          ▼
┌─────────────────┐
│  LDAPサーバー    │
│  (AD/OpenLDAP)  │
└─────────────────┘
```

## コンポーネント

### 1. VPN WebUI (`vpn-webui`)
- **言語**: Python 3 / Flask
- **データベース**: SQLite
- **機能**:
  - 証明書申請管理
  - 承認ワークフロー
  - VPN接続ログ解析
  - 監査ログ

### 2. OpenVPN Server (`openvpn-server`)
- **ネットワークモード**: host mode
- **機能**:
  - OpenVPN Server (UDP)
  - 証明書生成/失効API (内部ポート8080)
  - LDAP認証
  - EasyRSA 3.2.1による証明書管理

### 3. 自動ログ解析
- **スケジューラ**: vpn_log_scheduler.py
- **パーサー**: parse_vpn_logs.py
- **実行頻度**: 15分ごと（デフォルト）
- **機能**: OpenVPNログから接続/切断情報を抽出

## クイックスタート

### 前提条件

- Linux (Rocky Linux 9 または互換OS)
- Podman / podman-compose
- firewalld
- **LDAPサーバー (Active Directory または OpenLDAP) — 必須、無効化不可**
  - VPNクライアントの認証は常にLDAPを経由します。証明書のみの認証モードはサポートしていません
  - 設定の詳細は [docs/LDAP_SETUP.ja.md](docs/LDAP_SETUP.ja.md) を参照してください
- **認証リバースプロキシ（例: Authelia）— WebUIアクセスに必須**
  - WebUIはプロキシが注入する `Remote-User` / `Remote-Groups` HTTPヘッダーでユーザーを認証します
  - プロキシを経由せずに直接HTTPアクセスした場合は 401 Unauthorized が返ります
  - 設定例は [docs/SETUP.ja.md](docs/SETUP.ja.md) を参照してください

### インストール

1. **リポジトリのクローン**

```bash
cd /srv
git clone <your-repository-url>
cd openvpn-ldap-webui
```

2. **環境変数の設定**

```bash
cp .env.example .env
vi .env  # 環境に合わせて編集
```

重要な設定項目:
- `BIND_IP`: VPNサーバーのバインドIP
- `OPENVPN_PORT`: 外部公開ポート
- `OPENVPN_REMOTE_HOST`: クライアント設定に記載される接続先ホスト名
- `HOME_NETWORK` / `HOME_NETMASK`: ネットワーク設定
- `FULL_TUNNEL`: `true` でクライアントの全通信をVPN経由にし、インターネットの出口をこのサーバーにする（`block-ipv6` も送る）。既定 `false` は `HOME_NETWORK` 宛てだけ。ホスト側でVPNの通信を上流へ転送・マスカレードできる必要がある
- `CERT_API_SECRET`: 証明書API秘密鍵
- **LDAP設定**: `LDAP_SERVER`, `LDAP_BASE_DN`, `LDAP_BIND_USER`, `LDAP_BIND_PASSWORD`, `LDAP_VPN_GROUP`

3. **ホストの設定**

詳細なセットアップ手順は [docs/SETUP.ja.md](docs/SETUP.ja.md) を参照してください。

**必須項目:**
- firewalld設定 (masquerade, ポート転送, rich rules)
- sysctl設定 (rp_filter)
- ルーティング設定

4. **コンテナの起動**

```bash
podman-compose up -d
```

> **注意**: `start-openvpn.sh` エントリポイントはCA証明書が存在するまで待機（ブロック）します。
> 次のPKI初期化を完了するまでコンテナは起動完了しません。

5. **PKIの初期化（初回のみ）**

初期化スクリプトを実行してCAとサーバー証明書を生成します:

```bash
podman exec -it openvpn-server /scripts/init-openvpn.sh
```

これにより以下が生成されます:
- CA証明書
- サーバー証明書
- DHパラメータ
- TLS-AUTHキー

初期化後、OpenVPNサーバーが新しいPKIで起動するようコンテナを再起動します:

```bash
podman-compose restart
```

6. **アクセス**

WebUIにアクセスするには `Remote-User` / `Remote-Groups` ヘッダーを注入する認証リバースプロキシ（例: Authelia + nginx）が必要です。プロキシを経由しない直接アクセスは401になります。

- **ユーザーポータル**: リバースプロキシ経由（内部: `http://<BIND_IP>:<WEBUI_PORT>/`）
- **管理ポータル**: リバースプロキシ経由（内部: `http://<BIND_IP>:<WEBUI_PORT>/admin`）。`ADMIN_DOMAIN` で別ドメインに分離することもできます（docs/CONFIGURATION.ja.md 参照）

設定例は [docs/SETUP.ja.md](docs/SETUP.ja.md) を参照してください。

## ドキュメント

- [セットアップガイド](docs/SETUP.ja.md) - 詳細なホスト設定
- [設定ガイド](docs/CONFIGURATION.ja.md) - 設定オプションとカスタマイズ
- [LDAP設定ガイド](docs/LDAP_SETUP.ja.md) - LDAP統合の詳細設定

## 証明書ライフサイクル

1. **申請** (ユーザー): デバイス名を指定して証明書を申請
2. **承認** (管理者): 申請をレビューして承認/拒否
3. **生成** (自動): 承認時に証明書が自動生成
4. **ダウンロード** (ユーザー): .ovpnファイルをダウンロード
5. **使用**: VPN経由で接続
6. **失効** (管理者): 必要に応じて証明書を失効

### 証明書有効期限

- **CA証明書**: 3650日 (~10年)
- **クライアント証明書**: 825日 (~2年3ヶ月)
- **CRL**: 3650日 (~10年)

有効期限は`.env`で変更可能です。

## ディレクトリ構造

```
openvpn-ldap-webui/
├── compose.yml              # Docker Compose設定
├── .env                     # 環境変数
├── README.md               # このファイル（英語版）
├── README.ja.md            # このファイル（日本語版）
├── LICENSE                 # MITライセンス
├── docs/                   # ドキュメント
│   ├── SETUP.md           # セットアップガイド（英語）
│   ├── SETUP.ja.md        # セットアップガイド（日本語）
│   ├── CONFIGURATION.md   # 設定ガイド（英語）
│   ├── CONFIGURATION.ja.md # 設定ガイド（日本語）
│   ├── LDAP_SETUP.md      # LDAP設定ガイド（英語）
│   └── LDAP_SETUP.ja.md   # LDAP設定ガイド（日本語）
├── config/                 # コンテナ設定
│   └── openvpn/           # OpenVPNコンテナ
│       ├── Dockerfile
│       └── start-openvpn.sh
├── webui/                  # WebUIコンテナ
│   ├── Dockerfile
│   ├── app.py              # Flaskアプリケーション
│   ├── routes_*.py         # ルーティング
│   ├── templates/          # HTMLテンプレート
│   └── translations/       # i18nメッセージファイル
├── scripts/               # 運用スクリプト
│   ├── init-openvpn.sh           # 初期セットアップ
│   ├── generate-client-cert.sh   # 証明書生成
│   ├── revoke-client-cert.sh     # 証明書失効
│   ├── cert_api.py               # 証明書API
│   ├── ldap_auth.py              # LDAP認証
│   ├── parse_vpn_logs.py         # ログ解析
│   └── vpn_log_scheduler.py      # ログパーサースケジューラ
└── data/                  # 永続化データ (.gitignore)
    ├── db/                # SQLiteデータベース
    ├── certs/             # 証明書データ
    ├── logs/              # WebUIログ
    └── openvpn-logs/      # OpenVPNログ
```

## ロギング

### VPN接続ログ

- **解析頻度**: 15分ごと（デフォルト）
- **保存先**: SQLite DB (`vpn_connections`テーブル)
- **表示**: 管理ポータル > VPN接続履歴

### 監査ログ

全ての証明書操作（申請、承認、拒否、失効、ダウンロード）がログに記録されます。

- **保存先**: SQLite DB (`audit_logs`テーブル)
- **表示**: 管理ポータル > 監査ログ

## トラブルシューティング

**Q: VPNに接続できない**
```bash
# OpenVPNログを確認（<clone-dir>は実際のクローン先ディレクトリに置き換える）
tail -50 <clone-dir>/data/openvpn-logs/openvpn.log

# ポートが開いているか確認
ss -ulnp | grep <OPENVPN_PORT>
firewall-cmd --zone=public --query-port=<OPENVPN_PORT>/udp
```

**Q: ホームネットワークにアクセスできない**
```bash
# マスカレードを確認
iptables -t nat -L POSTROUTING -n -v | grep 10.8.0

# ルーティングを確認
ip route get <your-network-ip>
```

**Q: LDAP認証が失敗する**
```bash
# LDAP設定を確認
grep LDAP .env

# OpenVPNコンテナのログを確認
podman logs openvpn-server | grep -i ldap

# LDAP接続をテスト
podman exec -it openvpn-server python3 /scripts/ldap_auth.py
```

## コントリビューション

貢献を歓迎します！Pull Requestをお気軽に送信してください。

## ライセンス

このプロジェクトはMITライセンスの下でライセンスされています - 詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 作成者

your-username

## 謝辞

このプロジェクトはClaude（AnthropicのAIアシスタント）の支援を受けて開発されました。
