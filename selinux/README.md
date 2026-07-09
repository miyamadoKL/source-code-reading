# SELinux userspace ソースコードリーディング

SELinux userspace（[SELinuxProject/selinux](https://github.com/SELinuxProject/selinux)）のソースコードを読み解き、libsepol、libselinux、libsemanage、checkpolicy、policycoreutils を日本語で解説するドキュメントである。

- **対象バージョン**：3.10（コード引用はすべて [`3.10` タグ](https://github.com/SELinuxProject/selinux/tree/3.10)に固定）
- **ライセンス**：コンポーネント別で、libsepol と libsemanage は LGPL-2.1、checkpolicy と policycoreutils は GPL-2.0、libselinux は Public Domain、secilc は FreeBSD License（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：Linux セキュリティ、MAC、FLASK の基礎があり、userspace ツールチェーンの内部をソースから追いたい中級エンジニア。
- **読み方**：第0部から順に読むと、概観、libsepol、ポリシー変換、コンパイル、libselinux、libsemanage、ユーティリティ、周辺ツールへ段階的に積み上がる。

コード引用は GitHub の固定タグ URL とコードブロックの2点セットで示す。
本書はカーネル SELinux 実装（security server）ではなく userspace ライブラリとコマンドを対象とする。

## 第0部　概観

1. [SELinux userspace の全体像](part00-overview/01-selinux-userspace-overview.md)
2. [ビルド構成とコンポーネント](part00-overview/02-build-components.md)

## 第1部　libsepol 基盤

3. [policydb とポリシーデータ構造](part01-libsepol/03-policydb-overview.md)
4. [avtab と sidtab](part01-libsepol/04-avtab-sidtab.md)
5. [symtab と ebitmap](part01-libsepol/05-symtab-ebitmap.md)

## 第2部　ポリシー変換

6. [policydb の読み書き](part02-policy/06-policydb-read-write.md)
7. [link_modules によるモジュール統合](part02-policy/07-module-link.md)
8. [expand と optimize](part02-policy/08-expand-optimize.md)

## 第3部　checkpolicy

9. [checkpolicy のコンパイル入口](part03-checkpolicy/09-checkpolicy-main.md)
10. [checkmodule とモジュール生成](part03-checkpolicy/10-checkmodule-pipeline.md)
11. [CIL と secilc](part03-checkpolicy/11-secilc-cil.md)

## 第4部　libselinux ランタイム

12. [libselinux 初期化と selinuxfs](part04-libselinux/12-libselinux-init.md)
13. [AVC と compute_av](part04-libselinux/13-avc-compute-av.md)
14. [コンテキストとラベリング](part04-libselinux/14-context-labeling.md)

## 第5部　libsemanage

15. [semanage_handle と接続](part05-libsemanage/15-semanage-handle.md)
16. [モジュールストアと semodule](part05-libsemanage/16-module-store.md)
17. [ポリシー commit と reload](part05-libsemanage/17-policy-reload.md)

## 第6部　policycoreutils

18. [restorecon と setfiles](part06-utils/18-restorecon-setfiles.md)
19. [setenforce と getenforce](part06-utils/19-setenforce-getenforce.md)
20. [semodule コマンド](part06-utils/20-semodule-command.md)

## 第7部　周辺ツール

21. [audit2allow と sepolicy](part07-tools/21-audit2allow-sepolicy.md)
22. [mcstrans と setrans](part07-tools/22-mcstrans-setrans.md)
23. [restorecond](part07-tools/23-restorecond.md)

## 第8部　拡張

24. [python バインディングと sandbox](part08-extensions/24-python-sandbox.md)

---

> 対象は SELinuxProject/selinux の userspace リポジトリである。
> refpolicy 本体とカーネル `security/selinux/` は本書の範囲外とする。
> 引用タグは GitHub 上の `3.10` を用いる。
