# zstd ソースコードリーディング

zstd（[facebook/zstd](https://github.com/facebook/zstd)）のソースコードを読み解き、高速可逆圧縮ライブラリの内部構造を日本語で解説するドキュメントである。

- **対象バージョン**：1.5.7（コード引用はすべて [`v1.5.7` タグ](https://github.com/facebook/zstd/tree/v1.5.7)に固定）
- **想定読者**：C とデータ構造の基礎があり、圧縮アルゴリズムの内部実装を読み解きたい中級エンジニア
- **読み方**：第0部で全体像とフレームフォーマットを押さえ、共通基盤（第1部）とエントロピー符号化（第2部）を土台に、圧縮の中核（第3部）とマッチファインダー（第4部）へ進む。

コード引用は「GitHub リンク行＋コードブロック」の2点セットで示し、行番号は `v1.5.7` の実ソースに固定している。

## 第0部　全体像とフレームフォーマット

1. [zstd とは何か：ライブラリ構成と圧縮の全体像](part00-overview/01-what-is-zstd.md)
2. [フレームフォーマット：frame、block、エントロピーテーブルの配置](part00-overview/02-frame-format.md)
3. [公開 API とストリーミングの流れ](part00-overview/03-public-api-flow.md)

## 第1部　共通基盤

4. [ワークスペース管理：ZSTD_cwksp による単一アロケーション](part01-common/04-cwksp-memory.md)
5. [ビットストリーム：BIT_ 読み書きとビットコンテナ](part01-common/05-bitstream.md)
6. [メモリアクセス、エラー表現、XXH64 チェックサム](part01-common/06-mem-error-xxhash.md)

## 第2部　エントロピー符号化

7. [FSE 符号化：正規化カウントと状態遷移テーブル](part02-entropy/07-fse-compress.md)
8. [FSE 復号：デコードテーブルの構築と展開](part02-entropy/08-fse-decompress.md)
9. [Huffman 符号化：木の構築とビット詰め](part02-entropy/09-huffman-compress.md)
10. [Huffman 復号：テーブル駆動と x64 アセンブラ](part02-entropy/10-huffman-decompress.md)

## 第3部　圧縮の中核

11. [圧縮コンテキストとパラメータ：CCtx と cparams](part03-compress-core/11-cctx-params.md)
12. [seqStore とブロック圧縮の流れ](part03-compress-core/12-seqstore-blockflow.md)
13. [リテラルの符号化](part03-compress-core/13-literals-encoding.md)
14. [シーケンスの符号化](part03-compress-core/14-sequences-encoding.md)
15. [Super Block：小ブロック分割と最小サイズ保証](part03-compress-core/15-superblock.md)

## 第4部　マッチファインダー

16. [fast と double_fast：ハッシュテーブル探索](part04-matchfinder/16-fast-doublefast.md)
17. [lazy と row-based マッチファインダー](part04-matchfinder/17-lazy-row.md)
18. [optimal parser：コストモデルに基づく最適解探索](part04-matchfinder/18-optimal-parser.md)
19. [LDM：Long Distance Matching](part04-matchfinder/19-ldm.md)
20. [ブロック分割：preSplitter](part04-matchfinder/20-block-splitting.md)

## 第5部　マルチスレッド圧縮

21. [ZSTDMT：ジョブ分割、スレッドプール、LDM 連携](part05-mt/21-zstdmt.md)

## 第6部　復号

22. [復号コンテキストとフレーム復号](part06-decompress/22-decompress-frame.md)
23. [ブロック復号とシーケンス実行](part06-decompress/23-decompress-block.md)
24. [辞書復号：ZSTD_DDict](part06-decompress/24-ddict.md)

## 第7部　辞書生成

25. [辞書ビルダー：COVER と fastCover](part07-dict/25-dictionary-builder.md)

---

> 本書は zstd 1.5.7（タグ `v1.5.7`）を対象に、全8部25章で構成する。
