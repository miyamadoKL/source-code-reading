# keepalived ソースコードリーディング

keepalived（[acassen/keepalived](https://github.com/acassen/keepalived)）のソースコードを読み解き、VRRP、ヘルスチェック、IPVS、BFD を支えるプロセスモデルとイベント駆動基盤を日本語で解説するドキュメントである。

- **対象バージョン**：v2.4.1（コード引用はすべて [`v2.4.1` タグ](https://github.com/acassen/keepalived/tree/v2.4.1)に固定）
- **ライセンス**：GPL-2.0-or-later（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：Linux ネットワーク、C、epoll の基礎があり、高可用性構成の実装をソースから追いたい中級エンジニア。
- **読み方**：第0部から順に読むと、起動、スケジューラ、VRRP、チェッカー、BFD、運用機能へ段階的に積み上がる。

コード引用は GitHub の固定タグ URL とコードブロックの2点セットで示す。

## 第0部　概観

1. [keepalived の全体像](part00-overview/01-keepalived-overview.md)
2. [起動とプロセスモデル](part00-overview/02-startup-and-process-model.md)

## 第1部　基盤ライブラリ

3. [スケジューラとイベントループ](part01-foundation/03-scheduler.md)
4. [パーサと設定](part01-foundation/04-parser-and-config.md)
5. [メモリ、シグナル、プロセス](part01-foundation/05-memory-signals-process.md)

## 第2部　コア

6. [core main とデーモン起動](part02-core/06-core-main-and-daemon.md)
7. [netlink とネットワーク名前空間](part02-core/07-netlink-and-namespaces.md)
8. [リロード、通知、プロセス追跡](part02-core/08-reload-notify-track.md)

## 第3部　VRRP 基礎

9. [VRRP の概要と vrrp.c](part03-vrrp-base/09-vrrp-overview.md)
10. [VRRP 子プロセスとスケジューラ](part03-vrrp-base/10-vrrp-daemon.md)
11. [VRRP 状態遷移](part03-vrrp-base/11-vrrp-state-machine.md)
12. [VRRP パーサとデータ構造](part03-vrrp-base/12-vrrp-parser-data.md)

## 第4部　VRRP ネットワーク

13. [仮想 IP とインタフェース](part04-vrrp-net/13-vrrp-ipaddress-if.md)
14. [ルートとポリシールーティング](part04-vrrp-net/14-vrrp-iproute-iprule.md)
15. [ファイアウォールと nftables](part04-vrrp-net/15-vrrp-firewall-nftables.md)
16. [同期グループとトラッキング](part04-vrrp-net/16-vrrp-sync-track.md)

## 第5部　ヘルスチェックと IPVS

17. [check デーモン](part05-check/17-check-daemon.md)
18. [TCP、HTTP、UDP チェック](part05-check/18-check-tcp-http-udp.md)
19. [IPVS ラッパー](part05-check/19-ipvs-wrapper.md)
20. [その他チェックと BFD 連携](part05-check/20-check-misc.md)

## 第6部　BFD

21. [BFD プロトコル実装](part06-bfd/21-bfd-protocol.md)
22. [BFD と VRRP/check の連携](part06-bfd/22-bfd-integration.md)

## 第7部　運用

23. [SNMP、SMTP、D-Bus](part07-ops/23-snmp-smtp-dbus.md)
24. [genhash、トラッカー、リロード監視](part07-ops/24-reload-genhash-trackers.md)

---

> 全24章を執筆済み。
> コード引用は `acassen/keepalived` の `v2.4.1` タグに固定している。
