# Linux カーネル VFS とページキャッシュ

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の仮想ファイルシステム層（VFS）とページキャッシュを読み解く分冊である。
パス解決、inode と dentry キャッシュ、マウント、open と read/write、address_space、ライトバックまで、fs/ コアと mm/filemap.c の主要経路をソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md) と [同期と RCU](../locking/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読み、VFS の4大オブジェクトを押さえてからパス解決、マウント、ファイル操作、ページキャッシュ、ライトバックへ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。
XArray の一般論は [全体像と横断基盤](../foundation/part03-datastructures/11-xarray.md) を参照し、本分冊では address_space への適用に焦点を当てる。
folio の一般論は [メモリ管理](../mm/part00-foundation/02-folio-page-unit.md) を参照する。
RCU の一般論は [同期と RCU](../locking/part04-rcu/12-rcu-basics.md) を参照し、本分冊では RCU-walk に焦点を当てる。
`balance_dirty_pages` の詳細は [メモリ管理](../mm/part04-reclaim/24-folio-reclaim-decision.md) と境界を分ける。

## 第0部　VFS の全体像

1. [VFS 層の位置づけとシステムコール入口](part00-overview/01-vfs-layer-overview.md)
2. [super_block、inode、dentry、file の関係](part00-overview/02-vfs-core-objects.md)
3. [file_operations とファイルシステム抽象化](part00-overview/03-file-operations.md)

## 第1部　パス解決

4. [dcache のハッシュと名前検索](part01-path-lookup/04-dcache-hash-lookup.md)
5. [dentry の LRU と縮小](part01-path-lookup/05-dentry-lru-shrink.md)
6. [path lookup と link_path_walk](part01-path-lookup/06-path-lookup-walk.md)
7. [RCU-walk と ref-walk の切り替え](part01-path-lookup/07-rcu-walk-ref-walk.md)

## 第2部　マウントと inode

8. [vfsmount と mount namespace](part02-mount-inode/08-mount-namespace.md)
9. [inode のライフサイクルと icache](part02-mount-inode/09-inode-lifecycle.md)

## 第3部　ファイル操作

10. [open 経路と do_filp_open](part03-file-io/10-open-path.md)
11. [read 経路と iov_iter](part03-file-io/11-read-path.md)
12. [write 経路と generic_file_write_iter](part03-file-io/12-write-path.md)

## 第4部　ページキャッシュ

13. [address_space と XArray](part04-page-cache/13-address-space-xarray.md)
14. [filemap_read とページ取得](part04-page-cache/14-filemap-read.md)
15. [readahead と file_ra_state](part04-page-cache/15-readahead.md)
16. [書き込みと dirty ページ](part04-page-cache/16-write-dirty.md)

## 第5部　ライトバックと同期

17. [bdi、writeback kthread、wb_writeback](part05-writeback/17-writeback-bdi-kthread.md)
18. [fsync、sync、vfs_fsync](part05-writeback/18-fsync-sync.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコア分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
> 個別ファイルシステム（ext4 等）の on-disk 形式は [個別ファイルシステム](../README.md) 計画分冊の対象とする。
