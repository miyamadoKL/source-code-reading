# 第16章 同期グループとトラッキング

> 本章で読むソース
>
> - [`keepalived/vrrp/vrrp_sync.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_sync.c)
> - [`keepalived/vrrp/vrrp_track.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/vrrp/vrrp_track.c)

## この章の狙い

複数 instance を同一マスタ状態に揃える同期と、interface/script トラックを理解する。

## 前提

[第11章](../part03-vrrp-base/11-vrrp-state-machine.md) の `vrrp_sync_can_goto_master`。

## 同期グループ

`vrrp_sync.c` はグループ内でマスタ数を数え、スプリットブレインを抑える。

## トラック

`vrrp_track.c` は `track_interface`、`track_script`、`track_bfd` の重みを合算し、effective priority を下げる。

## 高速化・最適化の工夫

トラック結果はイベント駆動で再計算し、ポーリング間隔を最小化する。

## まとめ

同期とトラックは運用要件をコードで表現する層である。

## 関連する章

- [第22章 BFD 連携](../part06-bfd/22-bfd-integration.md)
