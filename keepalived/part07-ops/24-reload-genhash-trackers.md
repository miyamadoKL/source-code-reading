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

`check_genhash.c` の先頭コメントは、生成する MD5 が `wget` や `curl` の出力を `md5sum` した値と同じであると説明する。
`check_genhash` はダミー checker を組み立て、HTTP/SSL 応答本文の digest を計算して終了する。

[`keepalived/check/check_genhash.c` L24-L29](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/check/check_genhash.c#L24-L29)

```c
/*
 * The hash generated is the same as the one you can get from
 * wget or curl:
 *  wget http://[url]/[path] -O - | md5sum
 *  curl http://[url]/[path] | md5sum
 */
```

## track_file

`process_inotify` は inotify fd を `thread_add_read` で待ち、イベントごとに tracked file の重みを更新する。

[`keepalived/trackers/track_file.c` L844-L855](https://github.com/acassen/keepalived/blob/v2.4.1/keepalived/trackers/track_file.c#L844-L855)

```c
static void
process_inotify(thread_ref_t thread)
{
	char buf[sizeof(struct inotify_event) + NAME_MAX + 1] __attribute__((aligned(__alignof__(struct inotify_event))));
	// ... (中略) ...
	inotify_thread = thread_add_read(master, process_inotify, track_files, fd, TIMER_NEVER, 0);
```

## reload_monitor

[第8章](../part02-core/08-reload-notify-track.md) の `start_reload_monitor` が時刻ファイル変更を検知する。

## 高速化・最適化の工夫

genhash はデーモンを起動せず単発計算で終了し、オペレーションコストを最小化する。

## まとめ

周辺モジュールが運用自動化の足りない隙間を埋める。

## 関連する章

- [第8章 リロード](../part02-core/08-reload-notify-track.md)
- [第6章 core main](../part02-core/06-core-main-and-daemon.md)
