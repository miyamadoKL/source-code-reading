# Linux カーネル メモリ管理

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の物理メモリ割り当て、スラブ、仮想アドレス空間、ページフォールト、回収、THP、memcg、swap、NUMA fault 側を読み解く分冊である。
起動直後の memblock からバディアロケータ、SLUB、VMA、rmap、LRU と MGLRU、vmscan まで、mm/ の主要経路をソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md) と [プロセスとスケジューラ](../sched/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  memblock と folio、ゾーンを押さえてから物理割り当て、SLUB、仮想メモリ、回収、大きな機能へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。
Maple Tree の汎用 API は [全体像と横断基盤](../foundation/part03-datastructures/12-maple-tree.md) を参照し、本分冊では VMA への適用に焦点を当てる。
per-CPU 変数の一般論は [同期と RCU](../locking/part00-foundation/02-percpu.md) を参照し、pageset など mm 固有の利用に焦点を当てる。

## 第0部　メモリ管理の基礎

1. [memblock と起動直後の物理メモリ](part00-foundation/01-memblock-early-memory.md)
2. [folio とページ管理単位](part00-foundation/02-folio-page-unit.md)
3. [ゾーン、ノード、PFN](part00-foundation/03-zones-nodes-pfn.md)

## 第1部　物理ページ割り当て

4. [`__alloc_pages` の fast path と slow path](part01-physical/04-alloc-pages-path.md)
5. [watermark とゾーン fallback](part01-physical/05-watermark-zone-fallback.md)
6. [per-CPU pageset と compaction](part01-physical/06-percpu-pageset-compaction.md)

## 第2部　スラブ

7. [SLUB と kmem_cache、kmalloc](part02-slub/07-slub-kmalloc-cache.md)
8. [per-CPU slab と freelist](part02-slub/08-slub-percpu-freelist.md)

## 第3部　仮想メモリ

9. [VMA と Maple Tree](part03-virtual/09-vma-maple-tree.md)
10. [mmap と munmap](part03-virtual/10-mmap-munmap.md)
11. [ページフォールトと `handle_mm_fault`](part03-virtual/11-page-fault.md)
12. [vmalloc](part03-virtual/12-vmalloc.md)

## 第4部　逆引きと回収

13. [rmap と逆引き](part04-reclaim/13-rmap.md)
14. [LRU と MGLRU](part04-reclaim/14-lru-mglru.md)
15. [vmscan と回収経路](part04-reclaim/15-vmscan-reclaim.md)
16. [writeback とページキャッシュ回収](part04-reclaim/16-writeback-reclaim.md)

## 第5部　大きな機能

17. [Transparent Huge Pages](part05-advanced/17-thp.md)
18. [memcg とメモリ cgroup](part05-advanced/18-memcg.md)
19. [swap とスワップアウト](part05-advanced/19-swap.md)
20. [NUMA バランシングの fault 側](part05-advanced/20-numa-fault-balancing.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコア分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
> NUMA のスケジューラ側（`task_numa_fault` 等）は [プロセスとスケジューラ](../sched/part05-smp-obs/22-load-balance-numa.md) と境界を分ける。
