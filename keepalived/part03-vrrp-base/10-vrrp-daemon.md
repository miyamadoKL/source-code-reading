# 第10章 VRRP 子プロセスとスケジューラ

> 本章で読むソース
>
> - [`keepalived/vrrp/vrrp_daemon.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_daemon.c#L614-L624)
> - [`keepalived/vrrp/vrrp_scheduler.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_scheduler.c)

## この章の狙い

VRRP 子プロセスの初期化とパケットディスパッチャ起動を追う。

## 前提

[第2章](../part00-overview/02-startup-and-process-model.md)、[第3章](../part01-foundation/03-scheduler.md)。

## ディスパッチャ起動

初期化後、本番モードでは `vrrp_dispatcher_init` をイベントとして登録する。

[`keepalived/vrrp/vrrp_daemon.c` L614-L624](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_daemon.c#L614-L624)

```c
	if (!__test_bit(CONFIG_TEST_BIT, &debug)) {
		/* Init & start the VRRP packet dispatcher */
		thread_add_event(master, vrrp_dispatcher_init, NULL, 0);

		if (!reload) {
			if (global_data->vrrp_startup_delay) {
				vrrp_delayed_start_time = timer_add_long(time_now, global_data->vrrp_startup_delay);
				thread_add_timer(master, delayed_start_clear_thread, NULL, global_data->vrrp_startup_delay);
				log_message(LOG_INFO, "Delaying startup for %g seconds", global_data->vrrp_startup_delay / TIMER_HZ_DOUBLE);
			} else
				vrrp_delayed_start_time.tv_sec = 0;
```

`vrrp_startup_delay` はバックアップの早すぎるマスタ化を防ぐ。

## vrrp_scheduler

`vrrp_scheduler.c` はソケット読み取りスレッドとタイマを束ね、広告送信タイミングを管理する。

## 高速化・最適化の工夫

複数 VRRP instance のソケットを epoll にまとめ、1回の `epoll_wait` で複数読み取りを処理する。

## まとめ

VRRP 子は `vrrp_daemon.c` で初期化し、`vrrp_scheduler.c` で I/O ループに入る。

## 関連する章

- [第11章 状態遷移](11-vrrp-state-machine.md)
