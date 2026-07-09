# 第14章 ルートとポリシールーティング

> 本章で読むソース
>
> - [`keepalived/vrrp/vrrp_iproute.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_iproute.c)
> - [`keepalived/vrrp/vrrp_iprule.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_iprule.c)

## この章の狙い

`virtual_routes` と `virtual_rules` がカーネル FIB に反映される経路を追う。

## 前提

policy routing（`ip rule`）の基本を知っていること。

## 静的ルート

`netlink_route` は `rtmsg` を組み立て、`RTM_NEWROUTE` または `RTM_DELROUTE` を netlink で送る。

[`keepalived/vrrp/vrrp_iproute.c` L292-L313](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_iproute.c#L292-L313)

```c
static bool
netlink_route(ip_route_t *iproute, int cmd)
{
	struct {
		struct nlmsghdr n;
		struct rtmsg r;
		char buf[RTM_SIZE];
	} req;
	// ... (中略) ...
	if (cmd == IPROUTE_DEL) {
		req.n.nlmsg_flags = NLM_F_REQUEST;
		req.n.nlmsg_type  = RTM_DELROUTE;
	}
```

## ポリシールール

`netlink_rule` は `fib_rule_hdr` を埋め、`RTM_NEWRULE` で fwmark や priority 付きルールを追加する。

[`keepalived/vrrp/vrrp_iprule.c` L144-L163](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_iprule.c#L144-L163)

```c
static int
netlink_rule(ip_rule_t *iprule, int cmd)
{
	int status = 1;
	struct {
		struct nlmsghdr n;
		struct fib_rule_hdr frh;
		char buf[1024];
	} req;

	memset(&req, 0, sizeof (req));

	req.n.nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg));
	req.n.nlmsg_flags = NLM_F_REQUEST;

	if (cmd != IPRULE_DEL) {
		req.n.nlmsg_flags |= NLM_F_CREATE | NLM_F_EXCL;
		req.n.nlmsg_type = RTM_NEWRULE;
```

## 高速化・最適化の工夫

ルート一覧は差分比較で更新し、同一エントリの delete/add を避ける。

## まとめ

L3 冗長は VIP だけでなく、必要に応じて FIB 操作も伴う。

## 関連する章

- [第13章 仮想 IP](13-vrrp-ipaddress-if.md)
