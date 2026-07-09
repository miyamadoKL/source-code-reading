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

`vrrp_parser.c` は `virtual_ipaddress`、`track_interface`、`unicast_peer` 等のキーワードを登録する。

## データ

`vrrp_data.c` はリスト `vrrp_data->vrrp` を保持し、起動時にソケットとトラックをバインドする。
`alloc_vrrp` で instance を生成し、名前と VRID で一意性を検証する。

## 高速化・最適化の工夫

設定構造体はポインタの木で共有を避け、リロード時に `clear_diff_vrrp` で差分のみ netlink 操作する。

## まとめ

実行時状態は `vrrp_data` に集約され、パーサが静的設定を構築する。

## 関連する章

- [第13章 仮想 IP](../part04-vrrp-net/13-vrrp-ipaddress-if.md)
