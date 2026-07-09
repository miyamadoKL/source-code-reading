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

`vrrp_iptables.c` は VRRP マルチキャスト/ユニキャストを ACCEPT するルールを挿入する。

## nftables

`vrrp_nftables.c` と `core/nftables.c` は netlink nft ファミリで同等の穴あけを行う。

## 高速化・最適化の工夫

ルールは instance 起動時に一度だけ追加し、停止時に参照カウントで削除する。

## まとめ

ファイアウォール連携はデフォルト DROP 環境で VRRP を成立させるための補助である。

## 関連する章

- [第10章 VRRP 子](../part03-vrrp-base/10-vrrp-daemon.md)
