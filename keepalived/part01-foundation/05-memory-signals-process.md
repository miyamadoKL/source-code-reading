# 第5章 メモリ、シグナル、プロセス

> 本章で読むソース
>
> - [`lib/memory.c`](https://github.com/acassen/keepalived/blob/v2.4.1/lib/memory.c)
> - [`lib/signals.c`](https://github.com/acassen/keepalived/blob/v2.4.1/lib/signals.c)
> - [`lib/process.c`](https://github.com/acassen/keepalived/blob/v2.4.1/lib/process.c)

## この章の狙い

共通ライブラリが提供するメモリ追跡、シグナル処理、子プロセス制限の枠組みを押さえる。

## 前提

`signalfd`、カスタムアロケータのデバッグ用途を知っていること。

## メモリ管理

`lib/memory.c` は `MALLOC`/`FREE` マクロでラップし、`_MEM_CHECK_` ビルドではリーク検出リストを維持する。
通常ビルドでも `xrealloc` 等は枯渇時に abort し、呼び出し側が NULL チェックを省略できる前提を保つ。

[`lib/memory.c` L116-L128](https://github.com/acassen/keepalived/blob/v2.4.1/lib/memory.c#L116-L128)

```c
#if !defined(_MEM_CHECK_) && !defined(_MALLOC_CHECK_)
/* In the default build STRDUP, STRNDUP and REALLOC otherwise map to raw libc
 * and can return NULL, unlike MALLOC. These wrappers abort on exhaustion so the
 * codebase assumption that allocations succeed holds uniformly. */
void * __attribute__ ((malloc))
xrealloc(void *buffer, unsigned long size)
{
	void *mem = realloc(buffer, size);

	if (size && mem == NULL)
		mem_alloc_error("xrealloc()");

	return mem;
}
```

## シグナル

`signals.c` は SIGHUP（リロード）、SIGTERM（終了）、SIGCHLD（子監視）を signalfd 経由でスケジューラに渡す。
`signal_run_callback` が fd から `signalfd_siginfo` を読み、登録済みハンドラへディスパッチする。

[`lib/signals.c` L233-L240](https://github.com/acassen/keepalived/blob/v2.4.1/lib/signals.c#L233-L240)

```c
static void
signal_run_callback(thread_ref_t thread)
{
	uint32_t sig;
	struct signalfd_siginfo siginfo;

	while (read(signal_fd, &siginfo, sizeof(struct signalfd_siginfo)) == sizeof(struct signalfd_siginfo)) {
		sig = siginfo.ssi_signo;
```

## プロセスとスクリプト

`process.c` は子プロセスの `RLIMIT_NOFILE` 等を親から引き継がせず、チェック用ソケットの暴走を抑える。
外部スクリプト本体は `notify.c` の `system_call_script` が fork し、終了は `thread_add_child` で回収する。

[`lib/process.c` L389-L410](https://github.com/acassen/keepalived/blob/v2.4.1/lib/process.c#L389-L410)

```c
void
set_max_file_limit(unsigned fd_required)
{
	struct rlimit limit = { .rlim_cur = 0 };
	// ... (中略) ...
	if (setrlimit(RLIMIT_NOFILE, &limit) == -1)
		log_message(LOG_INFO, "Failed to set open file limit to %" PRI_rlim_t ":%" PRI_rlim_t " failed - errno %d", limit.rlim_cur, limit.rlim_max, errno);
```

## 高速化・最適化の工夫

signalfd によりシグナルハンドラ内の非同期安全制約を避け、メインループで一括処理する。
子プロセス終了は `thread_add_child` と組み合わせ、ブロッキング `waitpid` をループ外に閉じ込める。

## まとめ

`lib/` の3モジュールが、全デーモンで共有される実行環境の土台である。

## 関連する章

- [第3章 スケジューラ](03-scheduler.md)
- [第20章 その他チェック](../part05-check/20-check-misc.md)
