# Linux カーネル 個別ファイルシステム

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の個別ファイルシステム実装を読み解く分冊である。
ext4、btrfs、XFS 概観、overlayfs、tmpfs、procfs と sysfs の on-disk 形式と主要経路をソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[VFS とページキャッシュ](../vfs/README.md) と [メモリ管理](../mm/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部でファイルシステム登録とマウント接続を押さえ、ext4 と btrfs を厚く読み、XFS は概観に留めてから overlayfs、tmpfs、procfs と sysfs へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。
VFS の4大オブジェクトとパス解決は [VFS とページキャッシュ](../vfs/README.md) を参照し、本分冊では on-disk 形式と個別実装に焦点を当てる。
shmem のページ取得一般論は [メモリ管理](../mm/README.md) と境界を分ける。

## 第0部　概観

1. [file_system_type とファイルシステム登録](part00-overview/01-file-system-type-registration.md)
2. [fill_super とマウント接続の流れ](part00-overview/02-fill-super-mount-flow.md)
3. [ディスクレイアウトの読み方](part00-overview/03-on-disk-layout-reading.md)

## 第1部　ext4

4. [ext4 の super block と block group](part01-ext4/04-ext4-super-block-group.md)
5. [ext4 の inode と inode table](part01-ext4/05-ext4-inode-table.md)
6. [ext4 の extent ツリー](part01-ext4/06-ext4-extent-tree.md)
7. [jbd2 のジャーナリング](part01-ext4/07-jbd2-journaling.md)
8. [ext4 の delayed allocation](part01-ext4/08-ext4-delayed-allocation.md)

## 第2部　btrfs

9. [btrfs の B-tree とキー](part02-btrfs/09-btrfs-btree-key.md)
10. [btrfs の CoW と extent 管理](part02-btrfs/10-btrfs-cow-extent.md)
11. [btrfs のスナップショットと subvolume](part02-btrfs/11-btrfs-snapshot-subvolume.md)
12. [btrfs のチェックサムと RAID 概観](part02-btrfs/12-btrfs-checksum-raid.md)

## 第3部　XFS 概観

13. [XFS のアロケーショングループ](part03-xfs/13-xfs-allocation-groups.md)
14. [XFS ログの概観](part03-xfs/14-xfs-log-overview.md)

## 第4部　スタッキングと仮想

15. [overlayfs の upper/lower とコピーアップ](part04-stacking/15-overlayfs-copy-up.md)
16. [tmpfs と shmem](part04-stacking/16-tmpfs-shmem.md)
17. [procfs、sysfs と kernfs](part04-stacking/17-procfs-sysfs-kernfs.md)

**v7.1.3 との差分監査**として、本分冊の主要経路について `v6.18.38` と `v7.1.3` の関数本体を突き合わせた。
監査対象は第6章 extent 分割、第7章 jbd2 recovery と checkpoint、第8章 delayed allocation 予約、第10章 btrfs CoW、第11章 snapshot、第15章 overlayfs copy-up、第16章 shmem、第17章 kernfs open である。
v7.1.3 リンクの行範囲は、本章が説明する分岐を含むよう関数開始行から個別に指定した。

| 経路 | 結果 |
|---|---|
| `ext4_ext_create_new_leaf` | 本章の split と grow 分岐に実質差分なし（[`extents.c` L1400-L1434](https://github.com/gregkh/linux/blob/v7.1.3/fs/ext4/extents.c#L1400-L1434)） |
| `ext4_ext_grow_indepth` | 本章の深さ増加処理に実質差分なし（[`extents.c` L1312-L1354](https://github.com/gregkh/linux/blob/v7.1.3/fs/ext4/extents.c#L1312-L1354)） |
| `jbd2_journal_recover` | 3パス replay の意味論に実質差分なし（[`recovery.c` L271-L310](https://github.com/gregkh/linux/blob/v7.1.3/fs/jbd2/recovery.c#L271-L310)） |
| `jbd2_log_do_checkpoint` | tail 整理と checkpoint list 走査に実質差分なし（[`checkpoint.c` L154-L199](https://github.com/gregkh/linux/blob/v7.1.3/fs/jbd2/checkpoint.c#L154-L199)） |
| `jbd2_cleanup_journal_tail` | tail 更新とバリアに実質差分なし（[`checkpoint.c` L326-L352](https://github.com/gregkh/linux/blob/v7.1.3/fs/jbd2/checkpoint.c#L326-L352)） |
| `ext4_insert_delayed_blocks` | 予約呼び出し前の分岐に実質差分なし（[`inode.c` L1848-L1872](https://github.com/gregkh/linux/blob/v7.1.3/fs/ext4/inode.c#L1848-L1872)） |
| `ext4_da_reserve_space` | `i_reserved_data_blocks` 更新に実質差分なし（[`inode.c` L1624-L1650](https://github.com/gregkh/linux/blob/v7.1.3/fs/ext4/inode.c#L1624-L1650)） |
| `btrfs_cow_block` | メタデータ CoW 判定に実質差分なし（[`ctree.c` L651-L688](https://github.com/gregkh/linux/blob/v7.1.3/fs/btrfs/ctree.c#L651-L688)） |
| `create_pending_snapshot` / `btrfs_copy_root` | ルート複製経路が変更、v6 は lock 後に `btrfs_cow_block` を挟むが v7 は lock 後に `btrfs_copy_root` を直呼び（[`transaction.c` L1819-L1826](https://github.com/gregkh/linux/blob/v7.1.3/fs/btrfs/transaction.c#L1819-L1826)） |
| `create_pending_snapshot` / `btrfs_add_root_ref` | スナップショット登録後の親参照挿入は v6 と同様に継続（[`transaction.c` L1847-L1850](https://github.com/gregkh/linux/blob/v7.1.3/fs/btrfs/transaction.c#L1847-L1850)） |
| `ovl_copy_up_one` | workdir 作成から link 公開までの分岐に実質差分なし（[`copy_up.c` L1123-L1198](https://github.com/gregkh/linux/blob/v7.1.3/fs/overlayfs/copy_up.c#L1123-L1198)） |
| `shmem_get_folio_gfp` | キャッシュ検索と swapin 分岐に実質差分なし（[`shmem.c` L2464-L2504](https://github.com/gregkh/linux/blob/v7.1.3/mm/shmem.c#L2464-L2504)） |
| `kernfs_fop_open` | `seq_open` 接続に実質差分なし（[`file.c` L698-L711](https://github.com/gregkh/linux/blob/v7.1.3/fs/kernfs/file.c#L698-L711)） |
| `kernfs_seq_show` | `ops->seq_show` 委譲に実質差分なし（[`file.c` L217-L224](https://github.com/gregkh/linux/blob/v7.1.3/fs/kernfs/file.c#L217-L224)） |
| `kernfs_fop_read_iter` | `seq_read_iter` 分岐に実質差分なし（[`file.c` L294-L298](https://github.com/gregkh/linux/blob/v7.1.3/fs/kernfs/file.c#L294-L298)） |

上記以外の章（第0部概観、第3部 XFS、第16章 tmpfs 初期化など）も入口関数単位で確認し、本分冊が追う主要経路に実質差分は見つからなかった。

---

> 本分冊は Linux カーネル読解ドキュメント群のストレージ系分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
> ブロック層と io_uring は [ブロック層と io_uring](../block/README.md) 分冊の対象とする。
