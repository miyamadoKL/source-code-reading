# 第21章 BFD プロトコル実装

> 本章で読むソース
>
> - [`keepalived/bfd/bfd.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/bfd/bfd.c#L88-L103)
> - [`keepalived/bfd/bfd_scheduler.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/bfd/bfd_scheduler.c)

## この章の狙い

RFC 5880 に沿った BFD 状態変数とスケジューリングを理解する。

## 前提

BFD の Down/Init/Up を知っていること。

## Poll シーケンス

[`keepalived/bfd/bfd.c` L88-L103](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/bfd/bfd.c#L88-L103)

```c
void
bfd_set_poll(bfd_t *bfd)
{
	if (__test_bit(LOG_DETAIL_BIT, &debug))
		log_message(LOG_INFO, "(%s) Starting poll sequence",
			    bfd->iname);
	/*
	 * RFC5880:
	 * ... If the timing is such that a system receiving a Poll Sequence
	 * wishes to change the parameters described in this paragraph, the
	 * new parameter values MAY be carried in packets with the Final (F)
	 * bit set, even if the Poll Sequence has not yet been sent.
	 */
	if (bfd->final != 1)
		bfd->poll = 1;
}
```

## スケジューラ

`bfd_scheduler.c` はセッションごとの送信タイマを管理する。

## 高速化・最適化の工夫

マイクロ秒級の検知のため、送信間隔は `timerfd` と一体の epoll ループで扱う。

## まとめ

BFD 子は独立してセッションを維持し、状態変化をパイプで VRRP/check に通知する。

## 関連する章

- [第22章 BFD 連携](22-bfd-integration.md)
