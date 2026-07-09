# 第13章 仮想 IP とインタフェース

> 本章で読むソース
>
> - [`keepalived/vrrp/vrrp_ipaddress.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_ipaddress.c)
> - [`keepalived/vrrp/vrrp_if.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_if.c)
> - [`keepalived/vrrp/vrrp_vmac.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_vmac.c)

## この章の狙い

マスタ化時の VIP 追加とインタフェース追跡を理解する。

## 前提

IPv4/IPv6 のセカンダリアドレスを知っていること。

## 仮想 IP

`netlink_iplist` は VIP リストを走査し、未設定のエントリだけ `netlink_ipaddress` でカーネルに反映する。

[`keepalived/vrrp/vrrp_ipaddress.c` L241-L262](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_ipaddress.c#L241-L262)

```c
/* Add/Delete a list of IP addresses */
bool
netlink_iplist(list_head_t *ip_list, int cmd, bool force)
{
	ip_address_t *ip_addr;
	bool changed_entries = false;

	list_for_each_entry(ip_addr, ip_list, e_list) {
		if ((cmd == IPADDRESS_ADD && !ip_addr->set) ||
		    (cmd == IPADDRESS_DEL &&
		     (force || ip_addr->set || __test_bit(DONT_RELEASE_VRRP_BIT, &debug)))) {
			if (netlink_ipaddress(ip_addr, cmd) > 0) {
				ip_addr->set = (cmd == IPADDRESS_ADD);
```

## インタフェース

`vrrp_if.c` はリンク up/down を netlink で監視し、トラックスクリプトと組み合わせる。
`vrrp_vmac.c` は仮想 MAC アドレスを生成し、IPv6 ND を整合させる。

## 高速化・最適化の工夫

GARP/NA はバースト後に間引きタイマで再送し、スイッチの ARP テーブルを更新する。

## まとめ

データプレーンの切替は netlink による VIP 操作が中心である。

## 関連する章

- [第7章 netlink](../part02-core/07-netlink-and-namespaces.md)
- [第11章 状態遷移](../part03-vrrp-base/11-vrrp-state-machine.md)
