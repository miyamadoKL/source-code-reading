# Linux カーネル ブロック層と io_uring

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）のブロック層、`blk-mq`、I/O スケジューラ、`io_uring`、NVMe ドライバ概観、device mapper を読み解く分冊である。
ページキャッシュやファイルシステムからの `submit_bio` 入口を押さえ、`bio` と `request`、ハードウェアキュー、完了経路、非同期 I/O インタフェースまで追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[VFS とページキャッシュ](../vfs/README.md) と [メモリ管理](../mm/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読み、`bio` と `gendisk` を押さえてから `blk-mq`、スケジューラ、`io_uring`、ドライバ層へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。
ページキャッシュからのライトバック経路は [VFS 分冊](../vfs/part05-writeback/17-writeback-bdi-kthread.md) を参照する。

## 第0部　概観と基本オブジェクト

1. [ブロック層の全体像と submit_bio 経路](part00-overview/01-block-layer-overview.md)
2. [bio の構造とライフサイクル](part00-overview/02-bio-structure-lifecycle.md)
3. [gendisk、request_queue、request](part00-overview/03-gendisk-request-queue.md)

## 第1部　blk-mq

4. [ソフトウェアキューとハードウェアキュー、hctx と ctx](part01-blk-mq/04-blk-mq-queues-hctx-ctx.md)
5. [blk_mq_submit_bio とタグ割り当て](part01-blk-mq/05-blk-mq-submit-tags.md)
6. [完了処理、IRQ、polling](part01-blk-mq/06-blk-mq-completion-poll.md)

## 第2部　I/O スケジューラ

7. [elevator フレームワークと切り替え](part02-iosched/07-elevator-framework.md)
8. [mq-deadline スケジューラ](part02-iosched/08-mq-deadline.md)
9. [BFQ 概観](part02-iosched/09-bfq-overview.md)
10. [plug と merge](part02-iosched/10-plug-merge.md)

## 第3部　io_uring

11. [SQ/CQ リングと io_ring_ctx](part03-io-uring/11-sq-cq-rings.md)
12. [SQE の発行と io_submit_sqes](part03-io-uring/12-sqe-submission.md)
13. [io-wq による非同期実行](part03-io-uring/13-io-wq-async.md)
14. [登録リソースと polling](part03-io-uring/14-fixed-buffer-poll.md)

## 第4部　ドライバとスタック

15. [NVMe と blk-mq キュー対応](part04-driver-stack/15-nvme-queues.md)
16. [device mapper と dm-table](part04-driver-stack/16-device-mapper.md)
17. [ブロック統計と throttling 概観](part04-driver-stack/17-blk-stats-throttling.md)

## v7.1.3 との差分（監査）

`v6.18.38` と `v7.1.3` の主要ファイルを `diff` と関数本体の逐語比較で確認した（2026-07-12）。
本文のコード引用は `v6.18.38` に固定し、下表は読解に影響する変更の有無を示す。

| 領域 | ファイル | サイズ変化 | 本章で引用する関数 | 判定 |
| --- | --- | --- | --- | --- |
| blk-mq 投入 | `block/blk-mq.c` | +1330 バイト | `blk_mq_attempt_bio_merge`（[L3034-L3044](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-mq.c#L3034-L3044)）、`blk_mq_get_new_requests`（[L3046-L3075](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-mq.c#L3046-L3075)） | 本文と同一 |
| blk-mq 完了 | `block/blk-mq.c` | 同上 | `blk_mq_complete_request_remote`（[L1319-L1343](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-mq.c#L1319-L1343)）、`blk_mq_complete_need_ipi`（[L1272-L1297](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-mq.c#L1272-L1297)） | 本文と同一 |
| スケジューラ merge | `block/blk-mq-sched.c` | 微差 | `blk_mq_sched_bio_merge` | 本文と同一 |
| io_uring 発行 | `io_uring/io_uring.c` | −22623 バイト（リファクタ） | `io_queue_sqe`（[L1646-L1661](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/io_uring.c#L1646-L1661)） | 本文と同一 |
| io_uring 発行 | 同上 | 同上 | `io_submit_sqe`（[L1886-L1939](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/io_uring.c#L1886-L1939)） | `io_init_req` に `left` 引数追加。`ctx->bpf_filters` と `io_uring_run_bpf_filters()` による発行前拒否分岐が増加（inline/io-wq 後段は維持） |
| io_uring io-wq punt | `io_uring/io_uring.c` | 同上 | `io_queue_iowq`（[L407-L433](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/io_uring.c#L407-L433)） | 本体は同一、`io_req_queue_iowq_tw` の引数型が変更 |
| NVMe | `drivers/nvme/host/pci.c` | 微差 | `nvme_queue_rq`（[L1431-L1458](https://github.com/gregkh/linux/blob/v7.1.3/drivers/nvme/host/pci.c#L1431-L1458)） | 本文と同一、行番号のみずれる |
| device mapper | `drivers/md/dm.c` | +654 バイト | `__map_bio`（[L1397-L1452](https://github.com/gregkh/linux/blob/v7.1.3/drivers/md/dm.c#L1397-L1452)）、`__split_and_process_bio`（[L1721-L1762](https://github.com/gregkh/linux/blob/v7.1.3/drivers/md/dm.c#L1721-L1762)） | `__map_bio` は同一、分割処理は周辺コメント等で微差 |

elevator 実装（mq-deadline、BFQ）と `block/blk-core.c` の `submit_bio` 入口は、本章が引用する範囲では実質的な分岐変更は見つからなかった。

---

> 本分冊は Linux カーネル読解ドキュメント群のストレージ系分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
> ページキャッシュや writeback との接続は VFS 分冊を参照する。
