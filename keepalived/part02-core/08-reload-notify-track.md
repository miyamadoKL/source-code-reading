# 第8章 リロード、通知、プロセス追跡

> 本章で読むソース
>
> - [`keepalived/core/reload_monitor.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/reload_monitor.c)
> - [`keepalived/core/config_notify.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/config_notify.c)
> - [`keepalived/core/track_process.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/track_process.c)

## この章の狙い

SIGHUP リロード以外の設定更新経路と、外部プロセス状態の追跡を押さえる。

## 前提

systemd の `Reload=` や inotify の用途を知っていること。

## リロード監視

`reload_monitor.c` は `reload_time_file` などのトリガで親に再読み込みを促す。

## 設定通知

`config_notify.c` は D-Bus やファイルベースで設定変更を伝える（ビルドフラグ依存）。

## プロセス追跡

`track_process.c` は指定 PID の生死を監視し、VRRP の重み付けに反映する。

## 高速化・最適化の工夫

リロードは子ごとに差分適用（`clear_diff_*`）を行い、全インスタンス再起動を避ける。

## まとめ

運用時の動的変更は core 層の監視モジュールが受け、各子が差分処理する。

## 関連する章

- [第24章 genhash とトラッカー](../part07-ops/24-reload-genhash-trackers.md)
- [第16章 同期とトラック](../part04-vrrp-net/16-vrrp-sync-track.md)
