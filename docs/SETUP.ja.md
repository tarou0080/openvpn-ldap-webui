# ホストセットアップガイド

このドキュメントでは、OpenVPN LDAP WebUIシステムを実行するために必要なホスト側の設定について説明します。

[English](SETUP.md) | 日本語

## 前提条件

- Rocky Linux 9（または互換性のあるLinuxディストリビューション）
- PodmanとPodman-composeがインストール済み
- firewalldが有効
- LDAPサーバー（Active DirectoryまたはOpenLDAP）にホストからアクセス可能

## 必須ホスト設定

### 1. Firewalld設定

VPNトラフィックを許可し、マスカレードを有効にするようfirewalldを設定します：

```bash
# 送信元を限定したリッチルールでVPNネットワークのマスカレードを追加する。
# "source address"付きのリッチルールを使うことで、マスカレードをVPNトラフィックのみに限定できる。
# publicゾーン全体でmasqueradeを有効化すると、他のコンテナネットワークのトラフィックまで
# マスカレードされてしまうため推奨しない。
# 10.8.0.0/24はデフォルトのVPNクライアントネットワーク（.envのVPN_NETWORK）
firewall-cmd --permanent --zone=public --add-rich-rule='rule family="ipv4" source address="10.8.0.0/24" masquerade'

# OpenVPNポートを開放（.envのOPENVPN_PORTに合わせて調整）
firewall-cmd --permanent --zone=public --add-port=1194/udp

# ファイアウォール設定を再読み込み
firewall-cmd --reload

# 設定を確認
firewall-cmd --zone=public --list-all
```

**注意**: `1194`は`.env`で設定した`OPENVPN_PORT`に置き換えてください。

### 2. Sysctl設定（rp_filter）

VPNトラフィックを許可するためにリバースパスフィルタリングを設定します：

```bash
# VPN用のsysctl設定を作成
cat > /etc/sysctl.d/99-vpn.conf << 'EOF'
# VPN設定

# IPフォワーディングを有効化（VPNトラフィックのルーティングに必須）
net.ipv4.ip_forward=1

# podmanブリッジインターフェースのrp_filterを無効化
# 'podmanX'を実際のpodmanブリッジインターフェース名に置き換える
net.ipv4.conf.podmanX.rp_filter=0

# ホストの物理インターフェースのrp_filterを無効化
# 'ethX'を実際の物理インターフェース名に置き換える
net.ipv4.conf.ethX.rp_filter=0
EOF

# 設定を適用
sysctl -p /etc/sysctl.d/99-vpn.conf
```

**重要**: 
- `podmanX`を実際のpodmanブリッジインターフェース名に置き換えてください（`ip a | grep podman`で確認）
- `ethX`を実際の物理ネットワークインターフェース名に置き換えてください（`ip a`で確認）
- 一般的な物理インターフェース名: `eth0`, `ens3`, `enp0s3` など

### 3. ルーティング設定

VPNクライアントがVPNサーバー以外のネットワークにアクセスする必要がある場合：

```bash
# 内部ネットワークへのルートを追加
# ネットワークトポロジーに合わせて値を置き換える
nmcli connection modify <インターフェース名> +ipv4.routes "<ネットワーク> <ゲートウェイ>"

# 例: 192.168.0.0/16ネットワークをゲートウェイ192.168.1.1経由でルーティング
# nmcli connection modify eth0 +ipv4.routes "192.168.0.0/16 192.168.1.1"

# 設定を確認
nmcli connection show <インターフェース名> | grep ipv4.routes

# 変更を適用（一時的に接続が中断される可能性があります）
# nmcli connection up <インターフェース名>
```

**注意**: 
- このステップは、VPNクライアントがVPNサーバーのローカルネットワーク以外のネットワークにアクセスする必要がある場合のみ必要です
- ネットワークとゲートウェイは`.env`の`HOME_NETWORK`、`HOME_NETMASK`、`HOME_GATEWAY`と一致させてください
- 環境に合わせてインターフェース名を調整してください

## コンテナのデプロイ

ホストの設定が完了したら、コンテナを起動します：

```bash
cd /srv/openvpn-ldap-webui
podman-compose up -d
```

## 検証

### 1. OpenVPNサーバーの確認

```bash
# OpenVPNが正しいIPとポートでリッスンしているか確認
ss -ulnp | grep <OPENVPN_PORT>
# 期待される結果: BIND_IP:OPENVPN_PORTが表示される

# tunインターフェースが作成されているか確認
ip a | grep tun
# 期待される結果: tun0インターフェースが存在する

# マスカレードルールを確認
iptables -t nat -L POSTROUTING -n -v | grep 10.8.0
# 期待される結果: VPN使用中にパケットカウンターが増加するルールが表示される

# ルーティングテーブルを確認
ip route | grep tun0
# 期待される結果: tun0経由のVPNネットワークへのルートが表示される
```

### 2. VPN接続テスト

クライアント証明書をセットアップした後：

1. VPNクライアント経由で接続
2. VPNクライアントから接続をテスト：
   ```bash
   # VPNサーバーの内部ネットワークへの接続をテスト
   ping <内部ゲートウェイ>
   
   # 名前解決をテスト（DNSが設定されている場合）
   nslookup <ホスト名> <DNSサーバー>
   ```

## トラブルシューティング

### VPNに接続できない

```bash
# OpenVPNログを確認
tail -50 /srv/openvpn-ldap-webui/data/openvpn-logs/openvpn.log

# ファイアウォールポートが開いているか確認
firewall-cmd --zone=public --query-port=<OPENVPN_PORT>/udp

# OpenVPNプロセスが実行中か確認
podman ps | grep openvpn-server

# OpenVPNコンテナのログを確認
podman logs openvpn-server
```

### VPN接続はできるが内部ネットワークにアクセスできない

```bash
# パケットがtun0に到達しているか確認
tcpdump -i tun0 -n icmp

# マスカレードが機能しているか確認
iptables -t nat -L POSTROUTING -n -v | grep 10.8.0
# パケットカウンターが0の場合、マスカレードが機能していない

# ルーティングを確認
ip route get <内部ネットワークIP>

# rp_filter設定を確認
sysctl net.ipv4.conf.all.rp_filter
sysctl net.ipv4.conf.<インターフェース>.rp_filter
```

### WebUIにアクセスできない

```bash
# WebUIコンテナが実行中か確認
podman ps | grep vpn-webui

# WebUIログを確認
podman logs vpn-webui

# WebUIが正しいポートでリッスンしているか確認
ss -tlnp | grep 5000

# ローカル接続をテスト
curl -I http://<BIND_IP>:5000/
```

## 重要な環境変数

`.env`の主要な変数を参照してください：

```bash
# ネットワーク設定
BIND_IP=192.0.2.10              # VPNサーバーのバインドIP
OPENVPN_PORT=1194               # 外部OpenVPNポート
VPN_NETWORK=10.8.0.0            # VPNクライアントネットワーク
VPN_NETMASK=255.255.255.0

# 内部ネットワーク設定（オプション）
HOME_NETWORK=192.168.0.0        # 内部ネットワーク
HOME_NETMASK=255.255.0.0
HOME_DNS_SERVER=192.168.1.1     # 内部DNSサーバー
HOME_GATEWAY=192.168.1.1        # 内部ゲートウェイ
```

## アーキテクチャ概要

```
VPNクライアント（外部）
    ↓ UDP <OPENVPN_PORT>
ホストIP（BIND_IP）
    ↓
OpenVPN Server（hostネットワークモード）
    ↓ tun0（VPN_NETWORK）
    ↓ マスカレード
内部ネットワーク（HOME_NETWORK）
```

## リバースプロキシ（WebUIアクセスに必須）

WebUIは `Remote-User` と `Remote-Groups` HTTPヘッダーでユーザーを認証します。
これらのヘッダーは認証リバースプロキシが注入する必要があります。プロキシを経由しない
直接アクセスは 401 Unauthorized が返ります。

`.env`（および`compose.yml`のデフォルト）で `AUTHELIA_HEADERS=true` を設定することで、
WebUI が独自セッションではなく `Remote-User` / `Remote-Groups` を参照するようになります。

### nginx + Authelia の最小構成例

```nginx
# Authelia認証チェック（URLはAuthelia エンドポイントに合わせて変更）
location /authelia {
    internal;
    proxy_pass http://authelia:9091/api/verify;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header X-Original-URL $scheme://$http_host$request_uri;
}

# WebUIロケーション（1ドメインモードでは両ポータルを配信）
location / {
    auth_request /authelia;
    # Autheliaからユーザー情報ヘッダーを注入
    auth_request_set $user $upstream_http_remote_user;
    auth_request_set $groups $upstream_http_remote_groups;
    proxy_set_header Remote-User $user;
    proxy_set_header Remote-Groups $groups;

    proxy_pass http://<BIND_IP>:<WEBUI_PORT>;
    proxy_set_header Host $host;
}
```

`<BIND_IP>` と `<WEBUI_PORT>` は `.env` の値に置き換えてください。

### Autheliaのアクセス規則（1ドメインモード）

`/admin` は二要素認証を必須にして管理グループに限り、それ以外はVPN利用者向けにします。
規則は上から順に評価されるので、各 `deny` は閉じたい規則の直後に置いてください。
置かないと、グループ外の利用者が後ろのゆるい規則に拾われます。

```yaml
access_control:
  rules:
    - domain: 'vpn.example.com'
      resources: ['^/admin([/?].*)?$']
      policy: 'two_factor'
      subject: 'group:vpn-admins'
    - domain: 'vpn.example.com'
      resources: ['^/admin([/?].*)?$']
      policy: 'deny'
    - domain: 'vpn.example.com'
      policy: 'one_factor'
      subject: ['group:vpn-users', 'group:vpn-admins']
    - domain: 'vpn.example.com'
      policy: 'deny'
```

WebUIも管理ページごとに `ADMIN_GROUP` の所属を確認するので、`/admin` はプロキシの規則と
アプリの確認の両方で守られます。ドメイン分離モードでは、同じ規則をパスではなくドメイン単位で書きます。

## 注意事項

- OpenVPNサーバーは直接ネットワークアクセスのため`network_mode: host`で実行されます
- マスカレードはfirewalldの送信元限定リッチルールで管理されます
- WebUIは独自のコンテナネットワークで実行され、内部API経由でOpenVPNコンテナと通信します
- WebUIには認証リバースプロキシが必須です。直接HTTPアクセスは401を返します
