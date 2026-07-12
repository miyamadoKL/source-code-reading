# Apache Parquet ソースコードリーディング

Apache Parquet（[apache/parquet-format](https://github.com/apache/parquet-format)）の仕様を読み解き、列指向ストレージフォーマットが「何のために、どういう構造で実現されているか」と「解析ワークロードを支える設計上の工夫」を、仕様書と Thrift 定義の両面から引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：2.13.0（コード引用はすべて [`apache-parquet-format-2.13.0` タグ](https://github.com/apache/parquet-format/tree/apache-parquet-format-2.13.0)に固定）
- **想定読者**：列指向フォーマットとデータ解析基盤の基礎がある中級エンジニア
- **読み方**：ファイル構造の全体像から型、エンコーディング、ページと圧縮、統計とインデックス、暗号化、拡張型、互換性まで積み上げる構成で、第0部から順に読むことを想定する。

コード引用は、`apache-parquet-format-2.13.0` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。
Apache Parquet は単独で動作するソフトウェアではなく、列指向ストレージフォーマットの仕様である。
仕様の中核は `src/main/thrift/parquet.thrift`（メタデータの Thrift 定義）と、リポジトリ直下の各仕様書（`Encodings.md`、`LogicalTypes.md`、`Encryption.md` 等）が担う。
本書はこの仕様群を対象とし、参照実装（parquet-mr、parquet-cpp 等）の内部には踏み込まない。

## 第0部　全体像

1. [Parquet とは何か](part00-overview/01-what-is-parquet.md)
2. [ファイル構造とメタデータ階層](part00-overview/02-file-structure.md)

## 第1部　型システム

3. [物理型と論理型](part01-types/03-physical-and-logical-types.md)
4. [ネスト構造と定義・繰り返しレベル](part01-types/04-nested-encoding.md)

## 第2部　エンコーディング

5. [基本エンコーディング](part02-encoding/05-basic-encodings.md)
6. [差分・分割エンコーディング](part02-encoding/06-delta-encodings.md)

## 第3部　ページと圧縮

7. [データページとページヘッダ](part03-page/07-data-pages.md)
8. [圧縮](part03-page/08-compression.md)

## 第4部　統計とインデックス

9. [統計情報とカラム順序](part04-index/09-statistics.md)
10. [ページインデックス](part04-index/10-page-index.md)
11. [ブルームフィルタ](part04-index/11-bloom-filter.md)

## 第5部　暗号化

12. [モジュラー暗号化](part05-encryption/12-modular-encryption.md)

## 第6部　拡張型

13. [Variant エンコーディング](part06-extensions/13-variant-encoding.md)
14. [Variant シュレッディング](part06-extensions/14-variant-shredding.md)
15. [地理空間型](part06-extensions/15-geospatial.md)

## 第7部　互換性と運用

16. [スキーマ進化と後方互換](part07-compat/16-schema-evolution.md)
17. [バイナリプロトコル拡張と設定](part07-compat/17-binary-protocol-and-config.md)

---

> 本書は仕様リポジトリ `apache/parquet-format` を対象とし、コード引用は `apache-parquet-format-2.13.0` タグに固定する。
