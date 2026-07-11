# Linux カーネル 全体像と横断基盤

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）のソースツリー全体の地図、ビルド基盤、起動シーケンス、システムコール入口、主要データ構造、横断基盤を読み解く分冊である。
他の分冊に入る前に、カーネルがどう組み上がり、ユーザー空間からどう入ってくるかを押さえる。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：C とオペレーティングシステムの基礎があり、カーネル内部をソースから追いたい中級エンジニア
- **読み方**：第0部から順に読む。
  起動とシステムコール入口を先に押さえ、データ構造と sysfs、printk へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。

## 第0部　概観

1. [ソースツリーの地図](part00-overview/01-source-tree-map.md)
2. [Kconfig と Kbuild](part00-overview/02-kconfig-kbuild.md)

## 第1部　起動

3. [x86-64 ブートパス](part01-boot/03-x86-64-boot-path.md)
4. [start_kernel と initcall](part01-boot/04-start-kernel-initcall.md)
5. [kernel_init から init プロセス起動まで](part01-boot/05-kernel-init-to-init.md)

## 第2部　システムコール入口

6. [システムコールテーブルと SYSCALL_DEFINE](part02-syscall/06-syscall-table-syscall-define.md)
7. [entry_64.S の入口と出口](part02-syscall/07-entry-64-syscall-entry-exit.md)
8. [vDSO](part02-syscall/08-vdso.md)

## 第3部　主要データ構造

9. [list_head と hlist](part03-datastructures/09-list-head-hlist.md)
10. [rbtree](part03-datastructures/10-rbtree.md)
11. [XArray](part03-datastructures/11-xarray.md)
12. [Maple Tree](part03-datastructures/12-maple-tree.md)

## 第4部　横断基盤

13. [kobject と sysfs](part04-infra/13-kobject-sysfs.md)
14. [printk](part04-infra/14-printk.md)

## 第5部　ランタイム制御

15. [モジュールローダ](part05-runtime/15-module-loader.md)
16. [sysctl とカーネルパラメータ](part05-runtime/16-sysctl-kernel-parameters.md)
17. [panic と reboot](part05-runtime/17-panic-reboot.md)
18. [livepatch](part05-runtime/18-livepatch.md)

---

> 本分冊は Linux カーネル読解ドキュメント群の入口である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
