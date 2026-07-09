# 第24章 genhash、トラッカー、リロード監視

> 本章で読むソース
>
> - [`keepalived/check/check_genhash.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_genhash.c)
> - [`keepalived/trackers/track_file.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/trackers/track_file.c)
> - [`keepalived/core/reload_monitor.c`](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/core/reload_monitor.c)

## この章の狙い

付属ツールとファイルトラッカー、スケジュールリロードを押さえる。

## 前提

LVS の永続セッションとハッシュシードを知っていること。

## genhash

`keepalived_main` は argv[0] が `genhash` のとき `check_genhash` に分岐する（第6章）。
`check_genhash.c` はカーネルと同じハッシュをユーザ空間で計算する。

## track_file

`track_file.c` は inotify でファイル変化を検知し、VRRP/check の重みに反映する。

## reload_monitor

`reload_monitor.c` は時刻ファイルに基づき設定の再読み込みをスケジュールする。

## 高速化・最適化の工夫

genhash はデーモンを起動せず単発計算で終了し、オペレーションコストを最小化する。

## まとめ

周辺モジュールが運用自動化の足りない隙間を埋める。

## 関連する章

- [第8章 リロード](../part02-core/08-reload-notify-track.md)
- [第6章 core main](../part02-core/06-core-main-and-daemon.md)
