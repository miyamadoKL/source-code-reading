# Apache Arrow ソースコードリーディング

Apache Arrow（[apache/arrow](https://github.com/apache/arrow)）の仕様と実装を読み解き、言語横断の列指向インメモリフォーマットが「何のために、どういう構造で実現されているか」と「ゼロコピーと高速な解析処理を支える設計上の工夫」を、フォーマット定義と `pyarrow` 実装の両面から引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：25.0.0（コード引用はすべて [`apache-arrow-25.0.0` タグ](https://github.com/apache/arrow/tree/apache-arrow-25.0.0)に固定）
- **想定読者**：列指向フォーマットとデータ解析基盤の基礎がある中級エンジニア
- **読み方**：メモリレイアウトの全体像から型、IPC、メモリと相互運用、計算とデータセット、エコシステムまで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`apache-arrow-25.0.0` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
Apache Arrow はフォーマット仕様（`format/*.fbs` の FlatBuffers 定義と `docs/source/format/*.rst` の仕様書）と、それを各言語で実装したライブラリ群からなる。
本書は仕様に加えて Python バインディング `pyarrow`（`python/pyarrow/`）の実装を引用し、フォーマットがどう構築され読み書きされるかをソースコードから解説する。
C++ コア（`cpp/`）の内部実装や、`pyarrow` 以外の言語バインディングには深入りしない。

## 第0部　全体像

1. [Apache Arrow とは何か](part00-overview/01-what-is-arrow.md)
2. [列指向メモリレイアウトの原則](part00-overview/02-columnar-layout.md)

## 第1部　型とレイアウト

3. [型システムとスキーマ](part01-types/03-type-system.md)
4. [固定長・可変長レイアウト](part01-types/04-fixed-and-variable-layout.md)
5. [ネストレイアウト](part01-types/05-nested-layout.md)
6. [ディクショナリエンコーディング](part01-types/06-dictionary-encoding.md)

## 第2部　IPC とシリアライズ

7. [メッセージとメタデータ](part02-ipc/07-message-format.md)
8. [ストリーミング IPC](part02-ipc/08-streaming-ipc.md)
9. [ファイルフォーマットと Feather](part02-ipc/09-file-format.md)

## 第3部　メモリと相互運用

10. [Buffer とメモリ管理](part03-memory/10-buffer-and-memory.md)
11. [C Data Interface](part03-memory/11-c-data-interface.md)
12. [Flight RPC](part03-memory/12-flight-rpc.md)

## 第4部　計算とデータセット

13. [Compute カーネル](part04-compute/13-compute-kernels.md)
14. [Acero 実行エンジン](part04-compute/14-acero.md)
15. [Dataset API](part04-compute/15-dataset.md)
16. [Parquet 連携](part04-compute/16-parquet-integration.md)

## 第5部　エコシステム

17. [拡張型とエコシステム](part05-ecosystem/17-ecosystem.md)

---

> 本書はフォーマット仕様（`format/`、`docs/source/format/`）と `pyarrow` 実装を対象とし、コード引用は `apache-arrow-25.0.0` タグに固定する。
