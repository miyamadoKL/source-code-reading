# 第5章 メモリ、シグナル、プロセス

> 本章で読むソース
>
> - [`lib/memory.c`](https://github.com/acassen/keepalived/blob/v2.4.1/lib/memory.c)
> - [`lib/signals.c`](https://github.com/acassen/keepalived/blob/v2.4.1/lib/signals.c)
> - [`lib/process.c`](https://github.com/acassen/keepalived/blob/v2.4.1/lib/process.c)

## この章の狙い

共通ライブラリが提供するメモリ追跡、シグナル処理、スクリプト実行の枠組みを押さえる。

## 前提

`signalfd`、カスタムアロケータのデバッグ用途を知っていること。

## メモリ管理

`lib/memory.c` は `MALLOC`/`FREE` マクロでラップし、`_MEM_CHECK_` ビルドではリーク検出リストを維持する。
長寿命の設定構造体は起動時に一括確保し、リロード時に差し替える。

## シグナル

`signals.c` は SIGHUP（リロード）、SIGTERM（終了）、SIGCHLD（子監視）を signalfd 経由でスケジューラに渡す。
起動直後は `signals_ignore` で競合を避け、初期化完了後にハンドラを有効化する（`keepalived_main`）。

## プロセスとスクリプト

`process.c` は `notify` スクリプトやチェック用外部コマンドの実行を共通化する。
`script_security` オプションと連動し、危険なパスを拒否する（VRRP/check 双方）。

## 高速化・最適化の工夫

signalfd によりシグナルハンドラ内の非同期安全制約を避け、メインループで一括処理する。
子プロセス終了は `thread_add_child` と組み合わせ、ブロッキング `waitpid` をループ外に閉じ込める。

## まとめ

`lib/` の3モジュールが、全デーモンで共有される実行環境の土台である。

## 関連する章

- [第3章 スケジューラ](03-scheduler.md)
- [第20章 その他チェック](../part05-check/20-check-misc.md)
