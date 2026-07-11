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
3. [queue limits と bio の split/clone](part00-overview/03-queue-limits-bio-split.md)
4. [gendisk、request_queue、request の所有関係](part00-overview/04-gendisk-request-queue.md)

## 第1部　blk-mq

5. [ソフトウェアキューとハードウェアキュー、hctx と ctx](part01-blk-mq/05-blk-mq-queues-hctx-ctx.md)
6. [blk_mq_submit_bio とタグ割り当て](part01-blk-mq/06-blk-mq-submit-tags.md)
7. [dispatch と queue_rq handoff](part01-blk-mq/07-dispatch-queue-rq-handoff.md)
8. [完了処理、IRQ、polling](part01-blk-mq/08-blk-mq-completion-poll.md)

## 第2部　I/O スケジューラ

9. [elevator フレームワークと切り替え](part02-iosched/09-elevator-framework.md)
10. [mq-deadline スケジューラ](part02-iosched/10-mq-deadline.md)
11. [BFQ 概観](part02-iosched/11-bfq-overview.md)
12. [plug と merge](part02-iosched/12-plug-merge.md)

## 第3部　io_uring

13. [SQ/CQ リングと io_ring_ctx](part03-io-uring/13-sq-cq-rings.md)
14. [SQE の発行と io_submit_sqes](part03-io-uring/14-sqe-submission.md)
15. [io-wq による非同期実行](part03-io-uring/15-io-wq-async.md)
16. [read/write と direct I/O 実行](part03-io-uring/16-rw-direct-io.md)
17. [リクエスト完了、CQE 公開、キャンセル](part03-io-uring/17-req-complete-cqe.md)
18. [登録リソースと buffer ring](part03-io-uring/18-fixed-resources-buffer-ring.md)
19. [IOPOLL と CQ 完了](part03-io-uring/19-iopoll-cq-completion.md)

## 第4部　NVMe とゾーンストレージ

20. [NVMe コントローラのライフサイクル](part04-nvme-zoned/20-nvme-controller-lifecycle.md)
21. [NVMe の queue_rq とドアベル](part04-nvme-zoned/21-nvme-queue-rq-doorbell.md)
22. [zoned block device](part04-nvme-zoned/22-blk-zoned.md)

## 第5部　device mapper と制御層

23. [device mapper と dm-table](part05-dm-control/23-device-mapper.md)
24. [dm-crypt と target->map 契約](part05-dm-control/24-dm-crypt.md)
25. [ブロック統計](part05-dm-control/25-blk-stats.md)
26. [blk-cgroup QoS](part05-dm-control/26-blk-cgroup-qos.md)

**v7.1.3 との差分監査**として、`v6.18.38` と `v7.1.3` の主要ファイルを関数本体の比較で確認した。
本文のコード引用は `v6.18.38` に固定し、下表は読解に影響する変更の有無を示す。

| 領域 | ファイル | サイズ変化 | 本章で引用する関数 | 判定 |
| --- | --- | --- | --- | --- |
| queue limits | `block/blk-settings.c` | 微差 | `blk_stack_limits`（[L780-L823](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-settings.c#L780-L823)） | 本文と同一 |
| blk-mq dispatch | `block/blk-mq.c` | +1330 バイト | `blk_mq_dispatch_rq_list`（[L2116-L2188](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-mq.c#L2116-L2188)） | dispatch 再挿入と restart 分岐は同一 |
| blk-mq 投入 | `block/blk-mq.c` | 同上 | `blk_mq_attempt_bio_merge`（[L3034-L3044](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-mq.c#L3034-L3044)）、`blk_mq_get_new_requests`（[L3046-L3075](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-mq.c#L3046-L3075)） | 本文と同一 |
| blk-mq 完了 | `block/blk-mq.c` | 同上 | `blk_mq_complete_request_remote`（[L1319-L1343](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-mq.c#L1319-L1343)）、`blk_mq_complete_need_ipi`（[L1272-L1297](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-mq.c#L1272-L1297)） | 本文と同一 |
| スケジューラ merge | `block/blk-mq-sched.c` | 微差 | `blk_mq_sched_bio_merge` | 本文と同一 |
| io_uring rw | `io_uring/rw.c` | リファクタ | `__io_read`（[L912-L975](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/rw.c#L912-L975)） | `-EIOCBQUEUED`/partial 分岐は同一 |
| io_uring 完了/キャンセル | `io_uring/cancel.c` | 新設（v6 は `io_uring.c`） | `io_uring_try_cancel_requests`（[L515-L592](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/cancel.c#L515-L592)） | defer と io-wq 走査は同一 |
| io_uring 発行 | `io_uring/io_uring.c` | −22623 バイト（リファクタ） | `io_queue_sqe`（[L1646-L1661](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/io_uring.c#L1646-L1661)） | 本文と同一 |
| io_uring 発行 | 同上 | 同上 | `io_submit_sqe`（[L1886-L1939](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/io_uring.c#L1886-L1939)） | `io_init_req` に `left` 引数が追加され、`ctx->bpf_filters` と `io_uring_run_bpf_filters()` による発行前拒否分岐が増加（inline/io-wq 後段は維持） |
| io_uring io-wq punt | `io_uring/io_uring.c` | 同上 | `io_queue_iowq`（[L407-L433](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/io_uring.c#L407-L433)） | 本体は同一、`io_req_queue_iowq_tw` の引数型が変更 |
| buffer ring | `io_uring/kbuf.c` | 微差 | `io_register_pbuf_ring`（[L615-L641](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/kbuf.c#L615-L641)）、`io_buffer_select`（[L226-L244](https://github.com/gregkh/linux/blob/v7.1.3/io_uring/kbuf.c#L226-L244)） | 本文と同一 |
| NVMe reset | `drivers/nvme/host/pci.c` | 微差 | `nvme_reset_work`（[L3379-L3489](https://github.com/gregkh/linux/blob/v7.1.3/drivers/nvme/host/pci.c#L3379-L3489)） | CONNECTING/DELETING/DEAD 分岐は同一 |
| NVMe | `drivers/nvme/host/pci.c` | 同上 | `nvme_queue_rq`（[L1431-L1458](https://github.com/gregkh/linux/blob/v7.1.3/drivers/nvme/host/pci.c#L1431-L1458)） | 本文と同一、行番号のみずれる |
| zoned | `block/blk-zoned.c` | 微差 | `blk_zone_wplug_handle_native_zone_append`（[L1533-L1571](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-zoned.c#L1533-L1571)） | 本文と同一 |
| dm-crypt | `drivers/md/dm-crypt.c` | 微差 | `crypt_map`（[L3417-L3484](https://github.com/gregkh/linux/blob/v7.1.3/drivers/md/dm-crypt.c#L3417-L3484)） | READ/WRITE 分岐は同一、zoned 向け `no_split` 追加 |
| blk-stat | `block/blk-stat.c` | 微差 | `blk_rq_stat_add`（[L42-L48](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-stat.c#L42-L48)） | mean/batch モデルは同一 |
| iocost | `block/blk-iocost.c` | 微差 | `ioc_rqos_throttle`（[L2617-L2653](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-iocost.c#L2617-L2653)）、`ioc_rqos_done_bio`（[L2810-L2816](https://github.com/gregkh/linux/blob/v7.1.3/block/blk-iocost.c#L2810-L2816)） | vtime/waitq 経路は同一 |
| device mapper | `drivers/md/dm.c` | +654 バイト | `__map_bio`（[L1397-L1452](https://github.com/gregkh/linux/blob/v7.1.3/drivers/md/dm.c#L1397-L1452)）、`__split_and_process_bio`（[L1721-L1762](https://github.com/gregkh/linux/blob/v7.1.3/drivers/md/dm.c#L1721-L1762)） | `__map_bio` は同一、分割処理は周辺コメント等で微差 |

elevator 実装（mq-deadline、BFQ）と `block/blk-core.c` の `submit_bio` 入口は、本章が引用する範囲では実質的な分岐変更は見つからなかった。

---

> 本分冊は Linux カーネル読解ドキュメント群のストレージ系分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
> ページキャッシュや writeback との接続は VFS 分冊を参照する。
