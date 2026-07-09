# 第3章 スケジューラとイベントループ

> 本章で読むソース
>
> - [`lib/scheduler.c`](https://github.com/acassen/keepalived/blob/v2.4.1/lib/scheduler.c#L69-L73)
> - [`lib/scheduler.c`](https://github.com/acassen/keepalived/blob/v2.4.1/lib/scheduler.c#L1887-L1929)
> - [`lib/scheduler.c`](https://github.com/acassen/keepalived/blob/v2.4.1/lib/scheduler.c#L1371-L1375)

## この章の狙い

keepalived の非同期処理の中心である `thread_master_t` と epoll 統合を理解する。
VRRP タイマ、ソケット読み書き、子プロセス監視がどの API で登録されるかを押さえる。

## 前提

epoll とタイマファイルディスクリプタの基本を知っていること。

## thread と master

`lib/scheduler.c` は zebra 由来のスレッド（協調的タスク）モデルを実装する。
グローバル `master` が各プロセスのイベントループ本体である。

[`lib/scheduler.c` L69-L73](https://github.com/acassen/keepalived/blob/v2.4.1/lib/scheduler.c#L69-L73)

```c
/* global vars */
thread_master_t *master = NULL;
#ifndef _ONE_PROCESS_DEBUG_
prog_type_t prog_type;		/* Parent/VRRP/Checker process */
```

`thread_add_read`、`thread_add_timer`、`thread_add_child` などが登録 API である。

## ディスパッチ優先順位

`thread_fetch_next_queue` は、イベントキュー、即時実行キューを先に処理し、それ以外は epoll_wait で待つ。

[`lib/scheduler.c` L1887-L1929](https://github.com/acassen/keepalived/blob/v2.4.1/lib/scheduler.c#L1887-L1929)

```c
/* Fetch next ready thread. */
static list_head_t *
thread_fetch_next_queue(thread_master_t *m)
{
	// ... (中略) ...
	/* If there is event process it first. */
	if (!list_empty(&m->event))
		return &m->event;

	/* If there are ready threads process them */
	if (!list_empty(&m->ready))
		return &m->ready;

	do {
		/* Calculate and set wait timer. Take care of timeouted fd.  */
		earliest_timer = thread_set_timer(m);
		// ... (中略) ...
		/* Call epoll function. */
		ret = epoll_wait(m->epoll_fd, m->epoll_events, m->epoll_count, -1);
```

優先順位は「明示イベント」「準備完了」「タイマ/FD」であり、広告期限切れなどの緊急タイマが遅延しにくい。

## タイマ登録

VRRP のアドバタイズ間隔は `thread_add_timer` 系で再スケジュールされる。

[`lib/scheduler.c` L1371-L1375](https://github.com/acassen/keepalived/blob/v2.4.1/lib/scheduler.c#L1371-L1375)

```c
thread_add_timer(thread_master_t *m, thread_func_t func, void *arg, unsigned long timer)
{
	return thread_add_timer_uval(m, func, arg, 0, timer);
}
```

## 高速化・最適化の工夫

単一スレッドで多数の FD と timerfd を epoll に集約し、スレッド切替コストを排除する。
タイマは赤黒木で管理され、次の期限だけを timerfd に反映する（`thread_set_timer`）。

## まとめ

keepalived の「スレッド」は OS スレッドではなく、イベントループ上のコールバックである。

## 関連する章

- [第2章 起動とプロセスモデル](../part00-overview/02-startup-and-process-model.md)
- [第11章 VRRP 状態遷移](../part03-vrrp-base/11-vrrp-state-machine.md)
