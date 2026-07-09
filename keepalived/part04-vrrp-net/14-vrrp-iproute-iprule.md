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

`vrrp_iproute.c` はマスタ時のみ `virtual_routes` を追加し、Backup では削除する。

## ポリシールール

`vrrp_iprule.c` は fwmark や priority 付きルールを netlink で設定する。

## 高速化・最適化の工夫

ルート一覧は差分比較で更新し、同一エントリの delete/add を避ける。

## まとめ

L3 冗長は VIP だけでなく、必要に応じて FIB 操作も伴う。

## 関連する章

- [第13章 仮想 IP](13-vrrp-ipaddress-if.md)
