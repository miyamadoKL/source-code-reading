# Linux カーネル プロセスとスケジューラ

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）のプロセス表現、ライフサイクル、EEVDF スケジューラ、RT と deadline クラス、プリエンプション、PSI を読み解く分冊である。
ユーザー空間の「プロセス」がカーネル内部でどう表現され、いつどの CPU で走るかをソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  プロセス表現と fork、exec、exit を押さえてからスケジューラコア、EEVDF、特殊クラス、SMP 可観測性へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。

## 第0部　プロセスの表現とライフサイクル

1. [task_struct の構造](part00-process/01-task-struct.md)
2. [fork とプロセス生成（copy_process）](part00-process/02-fork-copy-process.md)
3. [exec とプログラム実行](part00-process/03-exec-program.md)
4. [exit と wait](part00-process/04-exit-wait.md)

## 第1部　スケジューラコア

5. [ランキューとスケジューリングクラスの階層](part01-core/05-runqueue-sched-class.md)
6. [__schedule とコンテキストスイッチ](part01-core/06-schedule-context-switch.md)
7. [プリエンプションモデル（PREEMPT_NONE から PREEMPT_LAZY まで）](part01-core/07-preemption-model.md)

## 第2部　EEVDF スケジューラ

8. [vruntime と eligibility（CFS から EEVDF への転換）](part02-eevdf/08-vruntime-eligibility.md)
9. [enqueue と dequeue と pick_next_task](part02-eevdf/09-enqueue-dequeue-pick.md)
10. [group scheduling と cgroup 階層](part02-eevdf/10-group-scheduling-cgroup.md)

## 第3部　RT と deadline

11. [RT クラス](part03-classes/11-rt-class.md)
12. [deadline クラス](part03-classes/12-deadline-class.md)

## 第4部　マルチコアと可観測性

13. [ロードバランスと NUMA](part04-smp-obs/13-load-balance-numa.md)
14. [PSI と統計](part04-smp-obs/14-psi-stats.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコア分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
