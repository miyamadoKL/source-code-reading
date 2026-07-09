# 第8章 リロード、通知、プロセス追跡

> 本章で読むソース
>
> - [`keepalived/core/reload_monitor.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/reload_monitor.c)
> - [`keepalived/core/config_notify.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/config_notify.c)
> - [`keepalived/core/track_process.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/track_process.c)

## この章の狙い

SIGHUP リロード以外の設定更新経路と、外部プロセス状態の追跡を押さえる。

## 前提

systemd の `Reload=` や inotify の用途を知っていること。

## リロード監視

`start_reload_monitor` は `reload_time_file` の親ディレクトリを inotify で監視し、変更を検知するとリロードを起動する。

[`keepalived/core/reload_monitor.c` L406-L428](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/reload_monitor.c#L406-L428)

```c
void
start_reload_monitor(void)
{
	int inotify_fd;
	char *dir;
	// ... (中略) ...
	inotify_fd = inotify_init1(IN_CLOEXEC | IN_NONBLOCK);

	file_name = strrchr(global_data->reload_time_file, '/');
```

## 設定通知

`open_config_read_fd` は eventfd を作り、子の `notify_config_read` が書き込んだ完了通知を `child_reloaded_thread` が読む。
全子の再読み込みが終わると `reload_queued` があれば `start_reload` を再投入する。

[`keepalived/core/config_notify.c` L54-L80](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/config_notify.c#L54-L80)

```c
static void
child_reloaded_thread(__attribute__((unused)) thread_ref_t thread)
{
	uint64_t event_count;
	int ret;

	ret = read(thread->u.f.fd, &event_count, sizeof(event_count));
	// ... (中略) ...
		if (!num_reloading) {
			log_message(LOG_INFO, "%s complete", loaded ? "Reload" : "Startup");
			loaded = true;
			if (reload_queued) {
				reload_queued = false;
				thread_add_event(master, start_reload, NULL, 0);
			}
		}
```

[`keepalived/core/config_notify.c` L88-L102](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/config_notify.c#L88-L102)

```c
void
open_config_read_fd(void)
{
	child_reloaded_event = eventfd(0, EFD_CLOEXEC | EFD_NONBLOCK);
	thread_add_read(master, child_reloaded_thread, NULL, child_reloaded_event, TIMER_NEVER, 0);
}

void
notify_config_read(void)
{
	uint64_t one = 1;

	if (write(child_reloaded_event, &one, sizeof(one)) <= 0)
		log_message(LOG_INFO, "Write child_reloaded_event errno %d - %m", errno);
}
```

## プロセス追跡

`reload_track_processes` は `/proc` ベースの追跡木を作り直し、netlink ソケットの read イベントで PID の生死を更新する。

[`keepalived/core/track_process.c` L1236-L1246](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/track_process.c#L1236-L1246)

```c
void
reload_track_processes(void)
{
	/* Remove the existing process tree */
	free_process_tree();

	/* Re read processes */
	read_procs(&vrrp_data->vrrp_track_processes);

	/* Add read thread */
	read_thread = thread_add_read(master, read_process_update, NULL, nl_sock, TIMER_NEVER, 0);
```

## 高速化・最適化の工夫

リロードは子ごとに差分適用（`clear_diff_*`）を行い、全インスタンス再起動を避ける。

## まとめ

運用時の動的変更は core 層の監視モジュールが受け、各子が差分処理する。

## 関連する章

- [第24章 genhash とトラッカー](../part07-ops/24-reload-genhash-trackers.md)
- [第16章 同期とトラック](../part04-vrrp-net/16-vrrp-sync-track.md)
