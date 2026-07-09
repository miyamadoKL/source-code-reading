# 第15章 ファイアウォールと nftables

> 本章で読むソース
>
> - [`keepalived/vrrp/vrrp_iptables.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_iptables.c)
> - [`keepalived/vrrp/vrrp_nftables.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_nftables.c)
> - [`keepalived/core/nftables.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/nftables.c)

## この章の狙い

VRRP パケット受理のための iptables/nftables 連携を理解する。

## 前提

INPUT チェーンと nftables table の違いを知っていること。

## iptables 時代

`handle_iptable_rule_to_vip` は VIP 向けの ACCEPT ルールを iptables チェーンへ挿入する。
ipset 有効時は `ipset_entry` で集合メンバとして登録する。

[`keepalived/vrrp/vrrp_iptables.c` L323-L340](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_iptables.c#L323-L340)

```c
static void
handle_iptable_rule_to_vip(ip_address_t *ipaddress, int cmd, struct ipt_handle *h, bool force)
{
	char *ifname = NULL;
	uint8_t family = ipaddress->ifa.ifa_family;

#ifdef _HAVE_LIBIPSET_
	if (global_data->using_ipsets)
	{
		if (!h->session)
			h->session = ipset_session_start();

		ipset_entry(h->session, cmd, ipaddress);
		ipaddress->iptable_rule_set = (cmd != IPADDRESS_DEL);
```

## nftables

`nft_setup_ipv4` は `NFT_MSG_NEWTABLE` で keepalived 用テーブルを作り、続けて chain と rule をバッチ送信する。

[`keepalived/vrrp/vrrp_nftables.c` L756-L772](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_nftables.c#L756-L772)

```c
static void
nft_setup_ipv4(struct mnl_nlmsg_batch *batch)
{
	struct nlmsghdr *nlh;
	struct nftnl_table *ta;
	struct nftnl_chain *t;

	/* nft add table ip keepalived */
	ta = table_add_parse(NFPROTO_IPV4, global_data->vrrp_nf_table_name);
	nlh = nftnl_table_nlmsg_build_hdr(mnl_nlmsg_batch_current(batch),
					NFT_MSG_NEWTABLE, NFPROTO_IPV4,
					NLM_F_CREATE|NLM_F_ACK, seq++);
```

## 高速化・最適化の工夫

nftables 側は `mnl_nlmsg_batch` で複数メッセージをまとめ、netlink 往復を減らす。

## まとめ

ファイアウォール連携はデフォルト DROP 環境で VRRP を成立させるための補助である。

## 関連する章

- [第10章 VRRP 子](../part03-vrrp-base/10-vrrp-daemon.md)
