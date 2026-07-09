# 第7章 netlink とネットワーク名前空間

> 本章で読むソース
>
> - [`keepalived/core/keepalived_netlink.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/keepalived_netlink.c)
> - [`keepalived/core/namespaces.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/namespaces.c)

## この章の狙い

仮想 IP やルートをカーネルに反映する netlink ラッパと、network namespace 切替を理解する。

## 前提

rtnetlink（`RTM_NEWADDR` 等）の概念を知っていること。

## netlink ラッパ

`keepalived_netlink.c` はアドレス、リンク、ルート、ルールの追加削除を共通化する。
`netlink_talk` が `sendmsg` でカーネルへ nlmsghdr を送り、応答を受け取る。

[`keepalived/core/keepalived_netlink.c` L1469-L1509](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/keepalived_netlink.c#L1469-L1509)

```c
ssize_t
netlink_talk(nl_handle_t *nl, struct nlmsghdr *n)
{
	ssize_t status;
	struct sockaddr_nl snl;
	struct iovec iov = {
		.iov_base = n,
		.iov_len = n->nlmsg_len
	};
	struct msghdr msg = {
		.msg_name = &snl,
		.msg_namelen = sizeof(snl),
		.msg_iov = &iov,
		.msg_iovlen = 1,
	};
	// ... (中略) ...
	status = sendmsg(nl->fd, &msg, 0);
	if (status < 0) {
		log_message(LOG_INFO, "Netlink: sendmsg(%d) cmd %d error: %s", nl->fd, n->nlmsg_type,
		       strerror(errno));
		return -1;
	}

	status = netlink_parse_info(netlink_talk_filter, nl, n, false);
```

## 名前空間

`set_namespaces` は `/var/run/netns/<name>` を開き `setns(fd, CLONE_NEWNET)` で network namespace に入る。
続けて `set_run_mount` が mount namespace を切り、pid ファイル用ディレクトリを bind mount する。
PID namespace は作成せず、pid ファイルの衝突を mount で避ける。

[`keepalived/core/namespaces.c` L263-L292](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/namespaces.c#L263-L292)

```c
bool
set_namespaces(const char* net_namespace)
{
	// ... (中略) ...
	if (setns(fd, CLONE_NEWNET)) {
		log_message(LOG_INFO, "setns() failed with error %d", errno);
		goto err;
	}

	close(fd);

	if (!__test_bit(CONFIG_TEST_BIT, &debug))
		set_run_mount(net_namespace);
```

## 高速化・最適化の工夫

netlink ソケットはプロセスごとに保持し、`netlink_talk` で1メッセージずつ往復する。
namespace 切替は起動時に固定し、ホットパスでは再 `setns` しない。

## まとめ

カーネル操作は keepalived 全体で netlink 層に集約される。

## 関連する章

- [第13章 仮想 IP](../part04-vrrp-net/13-vrrp-ipaddress-if.md)
- [第14章 ルート](../part04-vrrp-net/14-vrrp-iproute-iprule.md)
