# 第20章 その他チェックと BFD 連携

> 本章で読むソース
>
> - [`keepalived/check/check_misc.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_misc.c)
> - [`keepalived/check/check_bfd.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_bfd.c)
> - [`keepalived/check/check_file.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_file.c)

## この章の狙い

スクリプト、ファイル、BFD ベースのチェックを理解する。

## 前提

[第5章](../part01-foundation/05-memory-signals-process.md) の `process.c`。

## misc と file

`misc_check_thread` は無効時はタイマだけ再登録し、有効時は `system_call_script` で子プロセスを起動する。
親はすぐ戻り、終了コードは `misc_check_child_thread` が受け取る。

[`keepalived/check/check_misc.c` L266-L288](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_misc.c#L266-L288)

```c
static void
misc_check_thread(thread_ref_t thread)
{
	checker_t *checker = THREAD_ARG(thread);
	misc_checker_t *misck_checker;
	int ret;

	misck_checker = CHECKER_ARG(checker);

	if (!checker->enabled) {
		thread_add_timer(thread->master, misc_check_thread, checker,
				 checker->delay_loop);
		return;
	}

	/* Execute the script in a child process. Parent returns, child doesn't */
	ret = system_call_script(thread->master, misc_check_child_thread,
				  checker, (misck_checker->timeout) ? misck_checker->timeout : checker->vs->delay_loop,
				  &misck_checker->script);
```

## BFD

`bfd_check_thread` は checker 子が `bfd_checker_event_pipe` の read fd を `thread_add_read` で待ち、`bfd_event_t` を読む。

[`keepalived/check/check_bfd.c` L315-L332](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_bfd.c#L315-L332)

```c
static void
bfd_check_thread(thread_ref_t thread)
{
	bfd_event_t evt;

	if (thread->type == THREAD_READ_ERROR) {
		thread_close_fd(thread);
		return;
	}

	bfd_thread = thread_add_read(master, bfd_check_thread, NULL,
				     thread->u.f.fd, TIMER_NEVER, 0);

	while (read(thread->u.f.fd, &evt, sizeof(bfd_event_t)) != -1)
		bfd_check_handle_event(&evt);
}
```

## 高速化・最適化の工夫

スクリプト実行は子プロセスに閉じ込め、親のイベントループは `thread_add_child` で終了を非同期回収する。

## まとめ

柔軟な運用要件は misc/file/bfd チェックで吸収される。

## 関連する章

- [第22章 BFD 連携](../part06-bfd/22-bfd-integration.md)
