# 第22章 BFD と VRRP/check の連携

> 本章で読むソース
>
> - [`keepalived/bfd/bfd_event.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/bfd/bfd_event.c)
> - [`keepalived/bfd/bfd_daemon.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/bfd/bfd_daemon.c)
> - [`keepalived/vrrp/vrrp_scheduler.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_scheduler.c)

## この章の狙い

BFD セッション状態が VRRP priority と checker に伝播する経路を追う。

## 前提

[第16章](../part04-vrrp-net/16-vrrp-sync-track.md)、[第20章](../part05-check/20-check-misc.md)。

## パイプの作成

`open_bfd_pipes` は `open_pipe` で VRRP 用と checker 用の通常 pipe を作る。
fork 前に親が両端を開き、子は不要端を閉じる。

[`keepalived/bfd/bfd_daemon.c` L119-L136](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/bfd/bfd_daemon.c#L119-L136)

```c
bool
open_bfd_pipes(void)
{
#ifdef _WITH_VRRP_
	if (open_pipe(bfd_vrrp_event_pipe) == -1) {
		log_message(LOG_ERR, "Unable to create BFD vrrp event pipe: %m");
		return false;
	}
#endif

#ifdef _WITH_LVS_
	if (open_pipe(bfd_checker_event_pipe) == -1) {
		log_message(LOG_ERR, "Unable to create BFD checker event pipe: %m");
		return false;
	}
#endif

	return true;
}
```

## イベント送信と受信

BFD 子は `bfd_event_send` で `bfd_event_t` を pipe の write 端へ書き込む。
VRRP 子は `vrrp_bfd_thread` が read fd をスケジューラに登録し、構造体を読んで `vrrp_handle_bfd_event` へ渡す。

[`keepalived/bfd/bfd_event.c` L38-L70](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/bfd/bfd_event.c#L38-L70)

```c
void
bfd_event_send(bfd_t *bfd)
{
	bfd_event_t evt;
	// ... (中略) ...
	strcpy(evt.iname, bfd->iname);
	evt.state = bfd->local_state == BFD_STATE_UP ? BFD_STATE_UP : BFD_STATE_DOWN;
	evt.sent_time = timer_now();

	if (vrrp_running && bfd->vrrp) {
		ret = write(bfd_vrrp_event_pipe[1], &evt, sizeof evt);
```

[`keepalived/vrrp/vrrp_scheduler.c` L865-L887](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_scheduler.c#L865-L887)

```c
static void
vrrp_bfd_thread(thread_ref_t thread)
{
	bfd_event_t evt;
	ssize_t nread;

	bfd_thread = thread_add_read(master, vrrp_bfd_thread, NULL,
				     thread->u.f.fd, TIMER_NEVER, 0);

	while ((nread = read(thread->u.f.fd, &evt, sizeof(bfd_event_t))) != -1) {
		if ((size_t)nread != sizeof(bfd_event_t)) {
			log_message(LOG_INFO, "(BFD) event pipe short read %zd of %zu bytes", nread, sizeof(bfd_event_t));
			break;
		}
		vrrp_handle_bfd_event(&evt);
	}
}
```

## 高速化・最適化の工夫

pipe の read fd を epoll 統合済みスケジューラへ載せ、BFD 通知を他 I/O と同じループで処理する。

## まとめ

BFD は下位レイヤの障害検知を上位のフェイルオーバー判断へ橋渡しする。

## 関連する章

- [第21章 BFD プロトコル](21-bfd-protocol.md)
