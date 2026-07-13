# SQLite ソースコードリーディング

SQLite（[sqlite/sqlite](https://github.com/sqlite/sqlite)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「高速化、最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：3.53.3（コード引用はすべて [`version-3.53.3` タグ](https://github.com/sqlite/sqlite/tree/version-3.53.3)に固定）
- **ライセンス**：Public Domain（パブリックドメイン）
- **想定読者**：C 言語とリレーショナルデータベースの基礎がある中級エンジニア
- **読み方**：基礎から順に積み上がる構成で、第0部から順に読むことを想定する。
- **対象ビルド**：OS 依存部は Unix ビルド（`os_unix.c`）を主対象とし、Windows 実装（`os_win.c`）は必要箇所で注記する。

コード引用は、本文中の `[path L開始-L終了](https://github.com/sqlite/sqlite/blob/version-3.53.3/...)` 形式のリンクから GitHub 上の該当箇所を直接参照できる。
`opcodes.h` や `keywordhash.h` などビルド時に生成されるファイルは、引用ではなく生成元ツールと生成規則を示して扱う。

## 第0部　全体像

1. [SQLite のアーキテクチャ全体像](part00-overview/01-architecture.md)

## 第1部　フロントエンド：SQL からバイトコードへ

2. [公開 API と文のライフサイクル](part01-frontend/02-api-lifecycle.md)
3. [トークナイザ](part01-frontend/03-tokenizer.md)
4. [パーサ：Lemon と構文木](part01-frontend/04-parser.md)
5. [スキーマ構築と名前解決](part01-frontend/05-schema-resolve.md)

## 第2部　クエリコンパイラ（コード生成）

6. [式のコード生成と定数式因数分解](part02-compiler/06-expr-codegen.md)
7. [SELECT の処理](part02-compiler/07-select.md)
8. [クエリプランナ（1）WHERE 解析](part02-compiler/08-planner-where-analysis.md)
9. [クエリプランナ（2）ループ候補とコード生成](part02-compiler/09-planner-loops-codegen.md)
10. [INSERT / DELETE / UPDATE / UPSERT](part02-compiler/10-insert-delete-update.md)
11. [トリガと外部キー制約](part02-compiler/11-trigger-fkey.md)
12. [集約とウィンドウ関数](part02-compiler/12-aggregate-window.md)

## 第3部　仮想マシン VDBE

13. [VDBE バイトコードエンジン](part03-vdbe/13-vdbe-engine.md)
14. [VDBE プログラムの構築](part03-vdbe/14-vdbe-build.md)
15. [Mem 値の表現と型アフィニティ](part03-vdbe/15-mem-affinity.md)
16. [外部マージソート](part03-vdbe/16-external-sort.md)

## 第4部　ストレージエンジン

17. [B-tree（1）ファイルフォーマットとページ](part04-storage/17-btree-format.md)
18. [B-tree（2）カーソルと探索](part04-storage/18-btree-cursor.md)
19. [B-tree（3）挿入、削除、バランス](part04-storage/19-btree-balance.md)
20. [Pager とトランザクション](part04-storage/20-pager.md)
21. [WAL モード](part04-storage/21-wal.md)

## 第5部　OS 抽象と実行基盤

22. [VFS とロック、共有メモリ](part05-os/22-vfs-locking.md)
23. [メモリ確保とページキャッシュ](part05-os/23-memory-pcache.md)
24. [Mutex とワーカースレッド](part05-os/24-mutex-threads.md)

## 第6部　拡張機構

25. [仮想テーブルと JSON](part06-ext/25-vtab-json.md)
26. [FTS5 全文検索](part06-ext/26-fts5.md)

---

> 全26章。
> コード引用はすべて `version-3.53.3` タグに固定している。
