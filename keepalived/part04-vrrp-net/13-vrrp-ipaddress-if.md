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

`vrrp_ipaddress.c` は `netlink_iplist` で VIP を追加削除する。
`no_prefix` や `peer` オプションはラベル付きアドレスとして扱う。

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
