# 第23章 SNMP、SMTP、D-Bus

> 本章で読むソース
>
> - [`keepalived/core/snmp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/snmp.c)
> - [`keepalived/core/smtp.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/smtp.c)
> - [`keepalived/vrrp/vrrp_dbus.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_dbus.c)

## この章の狙い

監視と通知の周辺機能を理解する。

## 前提

SNMP MIB と SMTP アラートの用途を知っていること。

## SNMP

`snmp_register_mib` は AgentX 経由で VRRP 統計 MIB を登録する。

[`keepalived/core/snmp.c` L447-L453](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/snmp.c#L447-L453)

```c
void snmp_register_mib(oid *myoid, size_t len, const char *name,
		       struct variable *variables, size_t varsize, size_t varlen)
{
	char name_buf[80];

	if (register_mib(name, PTR_CAST(struct variable, variables), varsize,
```

## SMTP

`smtp_alert` は `smtp_t` を確保して `smtp_connect` を呼ぶ。
接続中は `thread_add_write`、サーバ応答は `thread_add_read` で SMTP ダイアログを進める。

[`keepalived/core/smtp.c` L511-L534](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/smtp.c#L511-L534)

```c
static void
smtp_connect(smtp_t *smtp)
{
	enum connect_result status;
	int fd;

	if ((fd = socket(global_data->smtp_server.ss_family, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, IPPROTO_TCP)) == -1) {
		free_smtp_msg_data(smtp);
		return;
	}

	status = tcp_connect(fd, &global_data->smtp_server);

	if (status == connect_in_progress) {
		thread_add_write(master, connection_in_progress, smtp,
				 fd, global_data->smtp_connection_to, THREAD_DESTROY_CLOSE_FD | THREAD_DESTROY_FREE_ARG);
		return;
	}
```

[`keepalived/core/smtp.c` L154-L156](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/smtp.c#L154-L156)

```c
	/* Registering next smtp command processing thread */
	thread_add_read(thread->master, smtp_read_thread, smtp,
			thread->u.f.fd, global_data->smtp_connection_to, THREAD_DESTROY_CLOSE_FD | THREAD_DESTROY_FREE_ARG);
```

## D-Bus

`vrrp_dbus.c` は systemd 連携や外部コントロール用のインタフェースを提供する（ビルド時）。

## 高速化・最適化の工夫

SMTP セッションは専用スレッドではなくスケジューラ上の read/write イベントとして進め、VRRP ループをブロックしない。

## まとめ

運用可観測性はコアと VRRP に分散実装されている。

## 関連する章

- [第11章 状態遷移](../part03-vrrp-base/11-vrrp-state-machine.md)
