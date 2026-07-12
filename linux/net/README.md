# Linux カーネル ネットワーク

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）のネットワークスタックを読み解く分冊である。
`sk_buff`、ソケット層、TCP/IPv4、受信高速化（NAPI、GRO）、送信と qdisc、netfilter、XDP まで、送信と受信の主要実行経路をソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[メモリ管理](../mm/README.md) と [割り込みと時間](../irq-time/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読み、`sk_buff` とソケット層を押さえてから TCP、IPv4、受信高速化、送信 qdisc、netfilter、XDP へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。
BPF verifier の詳細は BPF 分冊（計画中）の担当とし、本分冊では XDP とソケット BPF の境界のみ触れる。

## 第0部　概観と sk_buff

1. [ネットワークスタックの全体像と net namespace](part00-overview/01-network-stack-overview.md)
2. [sk_buff の構造と割り当て](part00-overview/02-sk_buff-structure-allocation.md)
3. [sk_buff の clone、copy、非線形データ](part00-overview/03-sk_buff-clone-copy-nonlinear.md)
4. [net_device と netdev ライフサイクル](part00-overview/04-netdev-lifecycle.md)

## 第1部　ソケット層

5. [struct sock とソケットオブジェクト](part01-socket/05-struct-sock.md)
6. [socket システムコール](part01-socket/06-socket-syscalls.md)
7. [sendmsg と recvmsg の一般経路](part01-socket/07-sendmsg-recvmsg.md)
8. [PF_INET とプロトコル登録](part01-socket/08-pf-inet-registration.md)

## 第2部　TCP

9. [TCP 接続の確立とソケット状態](part02-tcp/09-tcp-connection-establishment.md)
10. [TCP 送信経路とセグメント化](part02-tcp/10-tcp-output-path.md)
11. [TCP 受信経路と ACK 処理](part02-tcp/11-tcp-input-ack.md)
12. [輻輳制御と再送タイマー](part02-tcp/12-tcp-congestion-retransmit.md)

## 第3部　IPv4 とルーティング

13. [IPv4 出力と ip_local_out](part03-ipv4/13-ipv4-output.md)
14. [FIB とルーティング検索](part03-ipv4/14-fib-routing-lookup.md)
15. [IPv4 入力とローカル配送](part03-ipv4/15-ipv4-input-delivery.md)
16. [neighbour と ARP 解決](part03-ipv4/16-neighbour-arp.md)
17. [UDP と ICMP の概観](part03-ipv4/17-udp-icmp-overview.md)

## 第4部　受信高速化

18. [NAPI と netif_receive_skb](part04-rx-fastpath/18-napi-netif-receive.md)
19. [GRO とソフトウェアオフロード受信](part04-rx-fastpath/19-gro-receive-offload.md)
20. [RPS、RFS と受信ステアリング](part04-rx-fastpath/20-rps-rfs-steering.md)

## 第5部　送信と traffic control

21. [dev_queue_xmit と送信キュー投入](part05-tx-qdisc/21-dev-queue-xmit.md)
22. [qdisc フレームワークと sch_generic](part05-tx-qdisc/22-qdisc-framework.md)
23. [mq、fq、fq_codel](part05-tx-qdisc/23-mq-fq-fq-codel.md)

## 第6部　netfilter

24. [netfilter フックと IPv4 フック点](part06-netfilter/24-netfilter-hooks.md)
25. [nf_conntrack と接続追跡](part06-netfilter/25-nf-conntrack.md)
26. [nf_tables 概観](part06-netfilter/26-nf-tables-overview.md)

## 第7部　XDP と高速データパス

27. [XDP プログラムと早期処理](part07-xdp/27-xdp-program-early.md)
28. [AF_XDP とゼロコピー受信](part07-xdp/28-af-xdp-zero-copy.md)

---

> 本分冊は `net/` の主要実行経路に焦点を当てる。
> IPv6 の詳細、wireless、bluetooth、bridge、ipvs は対象外とする。
