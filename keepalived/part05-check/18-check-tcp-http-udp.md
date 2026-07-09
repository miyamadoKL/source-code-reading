# 第18章 TCP、HTTP、UDP チェック

> 本章で読むソース
>
> - [`keepalived/check/check_tcp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_tcp.c)
> - [`keepalived/check/check_http.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_http.c)
> - [`keepalived/check/check_udp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_udp.c)

## この章の狙い

代表的な L4/L7 ヘルスチェックの実装パターンを理解する。

## 前提

非同期 connect と HTTP ステータスコードを知っていること。

## TCP/UDP

`tcp_connect_thread` は `SOCK_NONBLOCK` で TCP ソケットを開き、`tcp_bind_connect` の結果を `tcp_connection_state` に渡す。
接続待ちはスケジューラの read/write コールバックへ委譲する。

[`keepalived/check/check_tcp.c` L184-L214](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_tcp.c#L184-L214)

```c
static void
tcp_connect_thread(thread_ref_t thread)
{
	checker_t *checker = THREAD_ARG(thread);
	conn_opts_t *co = checker->co;
	int fd;
	int status;

	if (!checker->enabled) {
		thread_add_timer(thread->master, tcp_connect_thread, checker,
				 checker->delay_loop);
		return;
	}

	if ((fd = socket(co->dst.ss_family, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, IPPROTO_TCP)) == -1) {
		// ... (中略) ...
	}

	status = tcp_bind_connect(fd, co);

	if(tcp_connection_state(fd, status, thread, tcp_check_thread,
			co->connection_to, 0)) {
```

## HTTP

`http_read_thread` は応答ストリームを読み切り、digest モードでは `EVP_DigestFinal_ex` で MD5 を確定する。
`EAGAIN` 時は同じ fd で `thread_add_read` を再登録する。

[`keepalived/check/check_http.c` L1546-L1553](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_http.c#L1546-L1553)

```c
	/* Test if data are ready */
	if (r == -1 && (check_EAGAIN(errno) || check_EINTR(errno))) {
		log_message(LOG_INFO, "Read error with server %s: %s"
				    , FMT_CHK(checker)
				    , strerror(errno));
		thread_add_read(thread->master, http_read_thread, checker,
				thread->u.f.fd, timeout, THREAD_DESTROY_CLOSE_FD);
		return;
	}
```

## 高速化・最適化の工夫

チェックごとにソケットを開き直し、完了後は `THREAD_DESTROY_CLOSE_FD` で fd を閉じる。
接続プールは使わず、スケジューラ上の非ブロッキング I/O で待ち時間を他チェックと重ねる。

## まとめ

チェック種別ごとにファイルが分かれ、共通の checker フレームワークに載る。

## 関連する章

- [第17章 check デーモン](17-check-daemon.md)
