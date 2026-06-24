# RocksDB ソースコードリーディング

RocksDB（[facebook/rocksdb](https://github.com/facebook/rocksdb)）のソースコードを読み解き、各コンポーネントが「何のために、どういう処理を行うか」と「高速化、最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：v11.1.1（コード引用はすべて [`v11.1.1` タグ](https://github.com/facebook/rocksdb/tree/v11.1.1)に固定）
- **想定読者**：C++ と DB の基礎がある中級エンジニア
- **読み方**：基礎から順に積み上がる構成。
  第0部から順に読むことを想定する。

コード引用は、本文中の `[path L開始-L終了](https://github.com/facebook/rocksdb/blob/v11.1.1/...)` 形式のリンクから GitHub 上の該当箇所を直接参照できる。

## 目次

### 第0部　導入と全体像

1. [RocksDB とは何か](part00-introduction/01-what-is-rocksdb.md)
2. [アーキテクチャ全体像](part00-introduction/02-architecture-overview.md)
3. [最小コード例で動かす](part00-introduction/03-hello-rocksdb.md)

### 第1部　基本データモデルと公開 API

4. [Slice とゼロコピー](part01-data-model/04-slice.md)
5. [内部キー形式 InternalKey](part01-data-model/05-internal-key.md)
6. [DB インターフェースと Options](part01-data-model/06-db-and-options.md)
7. [WriteBatch](part01-data-model/07-write-batch.md)

### 第2部　書き込みパス

8. [書き込みパイプライン全体](part02-write-path/08-write-pipeline.md)
9. [WriteThread とグループコミット](part02-write-path/09-write-thread.md)
10. [WAL（ログ）](part02-write-path/10-wal.md)
11. [MemTable と InlineSkipList](part02-write-path/11-memtable-skiplist.md)
12. [WriteBufferManager と Write Stall/Controller](part02-write-path/12-write-buffer-manager.md)
13. [Flush](part02-write-path/13-flush.md)

### 第3部　永続化フォーマット（SST）

14. [テーブルフォーマット概論](part03-sst/14-table-format.md)
15. [BlockBasedTable のビルド](part03-sst/15-block-based-table-builder.md)
16. [BlockBasedTable の読み出し](part03-sst/16-block-based-table-reader.md)
17. [インデックスブロック](part03-sst/17-index-block.md)
18. [フィルタと Bloom フィルタ](part03-sst/18-bloom-filter.md)
19. [Ribbon フィルタ](part03-sst/19-ribbon-filter.md)
20. [圧縮と辞書圧縮](part03-sst/20-compression.md)
21. [チェックサムと整合性](part03-sst/21-checksum.md)
22. [他のテーブル形式](part03-sst/22-other-table-formats.md)

### 第4部　読み出しパス

23. [Get の全体像](part04-read-path/23-get.md)
24. [Version と SuperVersion](part04-read-path/24-version-superversion.md)
25. [TableCache](part04-read-path/25-table-cache.md)
26. [イテレータ階層](part04-read-path/26-iterators.md)
27. [MultiGet](part04-read-path/27-multiget.md)
28. [MultiScan と coalescing iterator](part04-read-path/28-multiscan.md)

### 第5部　コンパクション

29. [コンパクションの理論](part05-compaction/29-compaction-theory.md)
30. [CompactionPicker](part05-compaction/30-compaction-picker.md)
31. [CompactionJob と CompactionIterator](part05-compaction/31-compaction-job.md)
32. [サブコンパクションと並列化](part05-compaction/32-subcompaction.md)
33. [マージ演算子](part05-compaction/33-merge-operator.md)

### 第6部　バージョン管理とメタデータ

34. [MANIFEST と VersionEdit](part06-version/34-manifest-versionedit.md)
35. [カラムファミリー](part06-version/35-column-family.md)
36. [シーケンス番号と Snapshot/MVCC](part06-version/36-snapshot-mvcc.md)
37. [ファイル管理と削除スケジューラ](part06-version/37-file-management.md)

### 第7部　キャッシュとメモリ

38. [Cache 抽象と Sharded Cache](part07-cache/38-cache-sharded.md)
39. [LRUCache](part07-cache/39-lru-cache.md)
40. [HyperClockCache](part07-cache/40-hyperclock-cache.md)
41. [Secondary / Tiered Cache](part07-cache/41-secondary-tiered-cache.md)
42. [メモリ割り当てとアリーナ](part07-cache/42-memory-arena.md)

### 第8部　並行制御と計測

43. [ThreadLocal とスレッドプール](part08-concurrency/43-threadlocal-threadpool.md)
44. [RateLimiter](part08-concurrency/44-rate-limiter.md)
45. [統計と計測](part08-concurrency/45-statistics-perfcontext.md)

### 第9部　環境抽象

46. [Env と FileSystem](part09-env/46-env-filesystem.md)
47. [ファイル I/O と先読み](part09-env/47-file-io-prefetch.md)

### 第10部　高度な機能と拡張

48. [BlobDB（KV 分離）](part10-advanced/48-blob-db.md)
49. [ワイドカラム](part10-advanced/49-wide-columns.md)
50. [トランザクション（楽観/悲観/2PC）](part10-advanced/50-transactions.md)
51. [バックアップ、チェックポイント、セカンダリ](part10-advanced/51-backup-checkpoint-secondary.md)
52. [エラーハンドリング、トレース、言語バインディング](part10-advanced/52-error-handling-trace-bindings.md)

---

> 全52章すべて執筆済み。
> 各章のコード引用は v11.1.1 タグに固定した GitHub リンクから該当行を直接参照できる。
