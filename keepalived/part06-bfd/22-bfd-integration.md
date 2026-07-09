# 第22章 BFD と VRRP/check の連携

> 本章で読むソース
>
> - [`keepalived/bfd/bfd_daemon.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/bfd/bfd_daemon.c)
> - [`keepalived/vrrp/vrrp_track.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_track.c)

## この章の狙い

BFD セッション状態が VRRP priority と checker に伝播する経路を追う。

## 前提

[第16章](../part04-vrrp-net/16-vrrp-sync-track.md)、[第20章](../part05-check/20-check-misc.md)。

## パイプ通知

BFD 子は `bfd_vrrp_event_pipe` と `bfd_checker_event_pipe` で Up/Down を送る。
親は fork 前にパイプを開き、子は不要端を閉じる（`start_check_child`）。

## トラック統合

`track_bfd` は `vrrp_track.c` で重み減算に使われる。

## 高速化・最適化の工夫

パイプはバイト列ではなくイベント fd 化され、epoll で一括待受する。

## まとめ

BFD は下位レイヤの障害検知を上位のフェイルオーバー判断へ橋渡しする。

## 関連する章

- [第21章 BFD プロトコル](21-bfd-protocol.md)
