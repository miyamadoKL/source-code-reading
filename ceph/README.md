# Ceph ソースコードリーディング

Ceph（[ceph/ceph](https://github.com/ceph/ceph)）のソースコードを読み解き、統合分散ストレージ RADOS の実装と高速化の工夫を日本語で解説するドキュメントである。

- **対象バージョン**：20.2.2（コード引用はすべて [`v20.2.2` タグ](https://github.com/ceph/ceph/tree/v20.2.2)に固定）
- **想定読者**：C++ と分散システムまたはストレージの基礎がある中級エンジニア
- **読み方**：共通基盤とネットワーク層から始め、CRUSH、Monitor、OSD、BlueStore、クライアントアクセス層と下から積み上げて読む

コード引用は「バージョン固定の GitHub リンク」＋「コードブロック」の2点セットで示す。
本書は RADOS を中核に据え、その上に載る RBD・CephFS・RGW を上位層として扱う。

## 第0部　全体像

1. [Ceph/RADOS のアーキテクチャとデーモン起動](part00-overview/01-architecture.md)

## 第1部　共通基盤

2. [オブジェクトモデルとシリアライズ（bufferlist・encode/decode・CephContext）](part01-foundation/02-object-model.md)
3. [スレッド基盤（ShardedThreadPool・WorkQueue・Finisher・Throttle）](part01-foundation/03-threading.md)

## 第2部　ネットワークと認証

4. [Messenger と AsyncConnection のイベント駆動 I/O](part02-network/04-messenger.md)
5. [ProtocolV2 とワイヤーフォーマット](part02-network/05-protocol-v2.md)
6. [cephx 認証](part02-network/06-cephx.md)

## 第3部　データ配置

7. [CRUSH アルゴリズムによる決定的なデータ配置](part03-crush/07-crush.md)
8. [OSDMap・PG マッピング・プール](part03-crush/08-osdmap-pg.md)

## 第4部　Monitor とクラスタ合意

9. [Monitor と Paxos によるマップの合意](part04-monitor/09-monitor-paxos.md)
10. [Elector と PaxosService（OSDMonitor ほか）](part04-monitor/10-elector-paxosservice.md)

## 第5部　OSD と PG

11. [OSD デーモンの構造と op スケジューリング](part05-osd/11-osd-daemon.md)
12. [PG と PeeringState](part05-osd/12-pg-peering.md)
13. [PrimaryLogPG の I/O パイプライン](part05-osd/13-primarylogpg.md)
14. [ReplicatedBackend とレプリケーション書き込み](part05-osd/14-replicated-backend.md)
15. [Erasure Code バックエンド](part05-osd/15-erasure-code.md)
16. [PGLog・recovery・backfill](part05-osd/16-recovery.md)
17. [スクラブと SnapMapper](part05-osd/17-scrub-snapmapper.md)

## 第6部　ローカルストレージ BlueStore

18. [ObjectStore インターフェースと Transaction](part06-bluestore/18-objectstore.md)
19. [BlueStore のメタデータとオンディスク構造](part06-bluestore/19-bluestore-metadata.md)
20. [BlueFS と RocksDB 統合](part06-bluestore/20-bluefs.md)
21. [Allocator と書き込みパス（deferred write・checksum・compression）](part06-bluestore/21-allocator-writepath.md)

## 第7部　クライアントアクセス層

22. [Objecter と librados](part07-clients/22-objecter-librados.md)
23. [librbd（RBD）の I/O ディスパッチ](part07-clients/23-librbd.md)
24. [CephFS：MDS と MDCache](part07-clients/24-cephfs-mds.md)
25. [CephFS クライアントと Capability](part07-clients/25-cephfs-client.md)
26. [RADOS Gateway（RGW）](part07-clients/26-rgw.md)

---

> 各章のコード引用は `v20.2.2` タグに固定している。
> 本書は執筆順に部単位で追加していく。
