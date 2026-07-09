# 第12章 VRRP パーサとデータ構造

> 本章で読むソース
>
> - [`keepalived/vrrp/vrrp_parser.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_parser.c)
> - [`keepalived/vrrp/vrrp_data.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_data.c)

## この章の狙い

`vrrp_instance` ブロックが `vrrp_t` 構造体へ落ちる過程を理解する。

## 前提

[第4章](../part01-foundation/04-parser-and-config.md)。

## パーサ

`vrrp_parser.c` は `vrrp_instance` をルートキーワードとして登録し、`virtual_ipaddress` や `track_interface` を子キーワードにぶら下げる。

[`keepalived/vrrp/vrrp_parser.c` L2325-L2337](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_parser.c#L2325-L2337)

```c
	/* VRRP Instance declarations */
	install_keyword_root("vrrp_instance", &vrrp_handler, active, VPP &current_vrrp);
	install_level_end_handler(&vrrp_end_handler);
#ifdef _HAVE_VRRP_VMAC_
	install_keyword("use_vmac", &vrrp_vmac_handler);
	install_keyword("use_vmac_addr", &vrrp_vmac_addr_handler);
	install_keyword("vmac_xmit_base", &vrrp_vmac_xmit_base_handler);
#endif
	install_keyword("unicast_peer", &vrrp_unicast_peer_handler);
```

## データ

`alloc_vrrp` は instance 名を受け取り、VIP リストや track リストを `INIT_LIST_HEAD` で初期化する。

[`keepalived/vrrp/vrrp_data.c` L978-L1000](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_data.c#L978-L1000)

```c
vrrp_t *
alloc_vrrp(const char *iname)
{
	vrrp_t *new;

	/* Allocate new VRRP structure */
	PMALLOC(new);
	INIT_LIST_HEAD(&new->e_list);
	INIT_LIST_HEAD(&new->s_list);
	INIT_LIST_HEAD(&new->track_ifp);
	INIT_LIST_HEAD(&new->track_script);
	INIT_LIST_HEAD(&new->track_file);
	INIT_LIST_HEAD(&new->vip);
	INIT_LIST_HEAD(&new->evip);
	INIT_LIST_HEAD(&new->vroutes);
	INIT_LIST_HEAD(&new->vrules);
```

## 高速化・最適化の工夫

設定構造体はポインタの木で共有を避け、リロード時に `clear_diff_vrrp` で差分のみ netlink 操作する。

## まとめ

実行時状態は `vrrp_data` に集約され、パーサが静的設定を構築する。

## 関連する章

- [第13章 仮想 IP](../part04-vrrp-net/13-vrrp-ipaddress-if.md)
