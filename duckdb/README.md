# DuckDB ソースコードリーディング

DuckDB（[duckdb/duckdb](https://github.com/duckdb/duckdb)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「高速化、最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：1.5.4（コード引用はすべて [`v1.5.4` タグ](https://github.com/duckdb/duckdb/tree/v1.5.4)に固定）
- **ライセンス**：MIT
- **想定読者**：C++ と分析系データベースの基礎がある中級エンジニア
- **読み方**：基礎から順に積み上がる構成で、第0部から順に読むことを想定する。

コード引用は、本文中の `[path L開始-L終了](https://github.com/duckdb/duckdb/blob/v1.5.4/...)` 形式のリンクから GitHub 上の該当箇所を直接参照できる。
DuckDB はベクトル化実行と列指向ストレージを軸とする分析データベースであり、本書はパーサから実行エンジン、ストレージ、トランザクションまでの主要実行経路を追う。

## 第0部　全体像

1. [アーキテクチャ全体像](part00-overview/01-architecture.md)

## 第1部　型システムとベクトル化データ表現

2. [LogicalType と Value](part01-types/02-logical-type-value.md)
3. [Vector とベクトル化](part01-types/03-vector.md)
4. [DataChunk と ColumnDataCollection](part01-types/04-datachunk.md)
5. [文字列とネスト型](part01-types/05-string-nested.md)

## 第2部　パーサとバインダ

6. [パーサとトランスフォーマ](part02-frontend/06-parser-transformer.md)
7. [バインダと名前解決](part02-frontend/07-binder.md)
8. [式のバインド](part02-frontend/08-expression-binding.md)
9. [論理演算子とプラン生成](part02-frontend/09-logical-plan.md)

## 第3部　オプティマイザ

10. [オプティマイザ全体像](part03-optimizer/10-optimizer-overview.md)
11. [フィルタプッシュダウンと統計伝播](part03-optimizer/11-filter-pushdown-statistics.md)
12. [結合順序最適化](part03-optimizer/12-join-order.md)
13. [式の書き換え](part03-optimizer/13-expression-rewrite.md)

## 第4部　物理実行エンジン

14. [物理プラン生成](part04-execution/14-physical-plan.md)
15. [パイプライン実行](part04-execution/15-pipeline-executor.md)
16. [パイプライン構築とスケジューリング](part04-execution/16-pipeline-build-scheduler.md)
17. [式実行](part04-execution/17-expression-executor.md)
18. [テーブル走査と table function](part04-execution/18-table-scan.md)
19. [CSV スキャナ](part04-execution/19-csv-scanner.md)
20. [ハッシュ結合](part04-execution/20-hash-join.md)
21. [集約](part04-execution/21-aggregation.md)
22. [ソート](part04-execution/22-sort.md)
23. [ウィンドウ関数](part04-execution/23-window.md)

## 第5部　列指向ストレージ

24. [ストレージ全体像とブロック管理](part05-storage/24-storage-block-manager.md)
25. [バッファマネージャ](part05-storage/25-buffer-manager.md)
26. [row group と列データ](part05-storage/26-row-group-column.md)
27. [圧縮](part05-storage/27-compression.md)
28. [WAL とチェックポイント](part05-storage/28-wal-checkpoint.md)
29. [ART インデックス](part05-storage/29-art-index.md)

## 第6部　トランザクション、カタログ、関数

30. [MVCC トランザクション](part06-transaction-catalog/30-mvcc.md)
31. [カタログと依存関係](part06-transaction-catalog/31-catalog.md)
32. [関数バインドと拡張登録](part06-transaction-catalog/32-function-extension.md)

---

> 全32章。
> コード引用はすべて `v1.5.4` タグに固定している。
