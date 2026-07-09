# 第17章 check デーモン

> 本章で読むソース
>
> - [`keepalived/check/check_daemon.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_daemon.c#L670-L716)

## この章の狙い

Checker 子プロセスの fork と初期化を追う。

## 前提

IPVS の Real Server と Director モデルを知っていること。

## start_check_child

[`keepalived/check/check_daemon.c` L670-L716](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_daemon.c#L670-L716)

```c
int
start_check_child(void)
{
#ifndef _ONE_PROCESS_DEBUG_
	pid_t pid;
	// ... (中略) ...
	pid = fork();

	if (pid < 0) {
		log_message(LOG_INFO, "Healthcheck child process: fork error(%s)"
			       , strerror(errno));
		return -1;
	} else if (pid) {
		checkers_child = pid;
		// ... (中略) ...
		thread_add_child(master, check_respawn_thread, NULL,
				 pid, TIMER_NEVER);

		return 0;
	}
	// ... (中略) ...
	prog_type = PROG_TYPE_CHECKER;
```

親は `check_respawn_thread` で子の死活を監視する。

## 高速化・最適化の工夫

チェックは独立プロセスで走り、HTTP など重いプローブが VRRP を阻害しない。

## まとめ

Checker は `check_daemon.c` が寿命管理し、`start_check` が実チェックを登録する。

## 関連する章

- [第18章 TCP/HTTP/UDP](18-check-tcp-http-udp.md)
- [第19章 IPVS](19-ipvs-wrapper.md)
