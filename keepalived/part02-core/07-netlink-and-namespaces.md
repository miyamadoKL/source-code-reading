# 第7章 netlink とネットワーク名前空間

> 本章で読むソース
>
> - [`keepalived/core/keepalived_netlink.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/keepalived_netlink.c)
> - [`keepalived/core/namespaces.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/namespaces.c)

## この章の狙い

仮想 IP やルートをカーネルに反映する netlink ラッパと、network namespace 切替を理解する。
VRRP がカーネルとどこで境界を引いているかを、共通層のコードから押さえる。

## 前提

rtnetlink（`RTM_NEWADDR` 等）の概念を知っていること。
Linux の network namespace と mount namespace の違いを理解していること。

## netlink チャネル

`keepalived_netlink.c` はコマンド用とカーネル反射用の2系統を持つ。
グローバル `nl_cmd` がアドレスやルートの追加削除に使われる。

[`keepalived/core/keepalived_netlink.c` L92-L99](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/keepalived_netlink.c#L92-L99)

```c
/* Global vars */
nl_handle_t nl_cmd = { .fd = -1 };	/* Command channel */
#ifdef _WITH_VRRP_
int netlink_error_ignore;	/* If we get this error, ignore it */
#endif

/* Static vars */
static nl_handle_t nl_kernel = { .fd = -1 };	/* Kernel reflection channel */
```

VRRP 有効ビルドではリンクやアドレス変化の監視に `nl_kernel` を使う（第13章）。
エラー番号 `netlink_error_ignore` で「既に存在する」系の応答を握りつぶせる。

## ソケット作成

`netlink_socket` は `AF_NETLINK` の `SOCK_RAW` を開き、必要な multicast グループへ join する。
受信バッファサイズは設定で上書きでき、大量のルート反映で溢れないようにする。

[`keepalived/core/keepalived_netlink.c` L551-L592](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/keepalived_netlink.c#L551-L592)

```c
static void
netlink_socket(nl_handle_t *nl, unsigned rcvbuf_size, bool force, int flags, unsigned group, ...)
{
	int ret;
	va_list gp;

	memset(nl, 0, sizeof (*nl));

	socklen_t addr_len;
	struct sockaddr_nl snl;
	int sock_flags = flags;

	nl->fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC | sock_flags, NETLINK_ROUTE);
	if (nl->fd < 0) {
		log_message(LOG_INFO, "Netlink: Cannot open netlink socket : (%s)",
		       strerror(errno));
		return;
	}

	memset(&snl, 0, sizeof (snl));
	snl.nl_family = AF_NETLINK;

	ret = bind(nl->fd, PTR_CAST(struct sockaddr, &snl), sizeof (snl));
	if (ret < 0) {
		log_message(LOG_INFO, "Netlink: Cannot bind netlink socket : (%s)",
		       strerror(errno));
		close(nl->fd);
		nl->fd = -1;
		return;
	}

	/* Join the requested groups */
	va_start(gp, group);
	while (group) {
		ret = setsockopt(nl->fd, SOL_NETLINK, NETLINK_ADD_MEMBERSHIP, &group, sizeof(group));
		if (ret < 0)
			log_message(LOG_INFO, "Netlink: Cannot add group %u membership on netlink socket : (%s)",
			       group, strerror(errno));

		group = va_arg(gp, unsigned);
	}
	va_end(gp);
```

監視用ソケットはスケジューラの read スレッドに載り、カーネルイベントで VRRP のトラッキングが更新される。
終了時は `netlink_close` が pending スレッドをキャンセルして FD を閉じる。

[`keepalived/core/keepalived_netlink.c` L656-L670](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/keepalived_netlink.c#L656-L670)

```c
static void
netlink_close(nl_handle_t *nl)
{
	if (!nl)
		return;

	/* First of all release pending thread. There is no thread
	 * for nl_cmd since it is used synchronously. */
	if (nl->thread) {
		thread_cancel(nl->thread);
		nl->thread = NULL;
	}

	if (nl->fd != -1)
		close(nl->fd);
```

## netlink_talk による往復

設定反映の多くは `netlink_talk` が1メッセージを送り、ACK を待つ。
`NLM_F_ACK` を付与するため、カーネルが拒否した操作は呼び出し元へエラーとして返る。

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
		.msg_control = NULL,
		.msg_controllen = 0,
		.msg_flags = 0
	};

	memset(&snl, 0, sizeof snl);
	snl.nl_family = AF_NETLINK;

	n->nlmsg_seq = ++nl->seq;

	/* Request Netlink acknowledgement */
	n->nlmsg_flags |= NLM_F_ACK;

#ifdef _NETLINK_TIMERS_
	gettimeofday(&start_time, NULL);
#endif

	/* Send message to netlink interface. */
	status = sendmsg(nl->fd, &msg, 0);
	if (status < 0) {
		log_message(LOG_INFO, "Netlink: sendmsg(%d) cmd %d error: %s", nl->fd, n->nlmsg_type,
		       strerror(errno));
		return -1;
	}

	status = netlink_parse_info(netlink_talk_filter, nl, n, false);
```

VIP の追加、ルート、ポリシールール、リンク up/down はいずれもこの経路を通る（第13章、第14章）。
`_NETLINK_TIMERS_` ビルドではコマンド種別ごとの累積時間を計測できる。

## network namespace への入り方

`set_namespaces` は `/var/run/netns/<name>` を開き `setns(fd, CLONE_NEWNET)` で入る。
設定の `net_namespace` キーワードがこれをトリガする（第4章）。

[`keepalived/core/namespaces.c` L263-L292](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/namespaces.c#L263-L292)

```c
bool
set_namespaces(const char* net_namespace)
{
	char *netns_path;
	int fd;

	netns_path = MALLOC(strlen(netns_dir) + strlen(net_namespace) + 1);
	if (!netns_path) {
		log_message(LOG_INFO, "Unable to malloc for set_namespaces()");
		return false;
	}

	strcpy(netns_path, netns_dir);
	strcat(netns_path, net_namespace);

	fd = open(netns_path, O_RDONLY | O_CLOEXEC);
	if (fd == -1) {
		log_message(LOG_INFO, "Failed to open %s", netns_path);
		goto err;
	}

	if (setns(fd, CLONE_NEWNET)) {
		log_message(LOG_INFO, "setns() failed with error %d", errno);
		goto err;
	}

	close(fd);

	if (!__test_bit(CONFIG_TEST_BIT, &debug))
		set_run_mount(net_namespace);
```

namespace 切替は起動時に一度だけ行い、ホットパスでは再 `setns` しない。
以降の netlink 操作はすべてその namespace 内のカーネルへ届く。

## PID ファイル用の mount 回避

PID namespace は作成せず、mount namespace で pid ファイルの衝突を避ける。
`set_run_mount` は `/run/keepalived/<namespace>` を作り、pid ディレクトリへ bind mount する。

[`keepalived/core/namespaces.c` L202-L245](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/namespaces.c#L202-L245)

```c
static void
set_run_mount(const char *net_namespace)
{
	bool error;

	/* /run/keepalived/NAMESPACE */
	mount_dirname = MALLOC(strlen(KEEPALIVED_PID_DIR) + 1 + strlen(net_namespace));
	if (!mount_dirname) {
		log_message(LOG_INFO, "Unable to allocate memory for pid file dirname");
		return;
	}

	strcpy(mount_dirname, KEEPALIVED_PID_DIR);
	strcat(mount_dirname, net_namespace);

	/* We want the directory to have rwxr-xr-x permissions */
	if (umask_val & (S_IRWXU | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH))
		umask(umask_val & ~(S_IRWXU | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH));

	error = mkdir(mount_dirname, S_IRWXU | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH) && errno != EEXIST;

	/* Restore our default umask */
	if (umask_val & (S_IRWXU | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH))
		umask(umask_val);

	if (error) {
		log_message(LOG_INFO, "Unable to create directory %s", mount_dirname);
		free_dirname();
		return;
	}

	if (unshare(CLONE_NEWNS)) {
		log_message(LOG_INFO, "mount unshare failed (%d) '%s'", errno, strerror(errno));
		return;
	}

	/* Make all mounts unshared - systemd makes them shared by default */
	if (mount("", "/", NULL, MS_REC | MS_SLAVE, NULL))
		log_message(LOG_INFO, "Mount slave failed, error (%d) '%s'", errno, strerror(errno));

	if (mount(mount_dirname, pid_directory, NULL, MS_BIND, NULL))
		log_message(LOG_INFO, "Mount failed, error (%d) '%s'", errno, strerror(errno));

	run_mount_set = true;
}
```

複数 namespace で同一ホストに keepalived を並べても、PID ファイルパスが論理的に分離される。

`net_namespace` は `global_parser.c` のルートキーワードとして登録される（第4章）。
`clear_namespaces` は終了時に bind mount を解除する。

[`keepalived/core/namespaces.c` L308-L311](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/namespaces.c#L308-L311)

```c
void
clear_namespaces(void)
{
	unmount_run();
}
```

他の namespace へソケットだけ渡す用途では、現在の net ns FD を保持する。

[`keepalived/core/namespaces.c` L317-L320](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/namespaces.c#L317-L320)

```c
static int
open_current_namespace(void)
{
	return open("/proc/self/ns/net", O_RDONLY | O_CLOEXEC);
}
```

## IPVS 用 namespace

`net_namespace_ipvs` は IPVS ソケットだけ別 namespace で開く用途がある。
`open_ipvs_namespace` が `/var/run/netns/<name>` または init の net ns を選ぶ（同ファイル L324 以降）。

## データフロー

```mermaid
flowchart LR
  CONF[keepalived.conf]
  NS[set_namespaces]
  NL[netlink_talk]
  KERN[カーネル FIB/ARP]
  CONF --> NS
  NS --> NL
  NL --> KERN
```

## 高速化・最適化の工夫

netlink ソケットはプロセスごとに保持し、`netlink_talk` で1メッセージずつ往復する。
ACK 付き送信により失敗を早期検出でき、VRRP の状態機械が不整合なまま進みにくい。
namespace 切替は起動時に固定し、ホットパスでは再 `setns` しない。

受信バッファサイズを設定で拡大できるため、大量ルートがある環境でも netlink 溢れを抑えられる。
監視ソケットとコマンドソケットを分離し、反射イベントが設定反映を詰まらせにくい。

## まとめ

カーネル操作は keepalived 全体で netlink 層に集約される。
network namespace を使う構成では `set_namespaces` と mount 回避で、ネット分離と PID 管理を両立する。

## 関連する章

- [第4章 パーサ](../part01-foundation/04-parser-and-config.md)
- [第13章 仮想 IP](../part04-vrrp-net/13-vrrp-ipaddress-if.md)
- [第14章 ルート](../part04-vrrp-net/14-vrrp-iproute-iprule.md)
