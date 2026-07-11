# Linux カーネル プロセスとスケジューラ

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）のプロセス表現、ライフサイクル、EEVDF スケジューラ、sched_ext、RT と deadline クラス、プリエンプション、PSI を読み解く分冊である。
ユーザー空間の「プロセス」がカーネル内部でどう表現され、いつどの CPU で走るかをソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  プロセス表現と fork、exec、exit を押さえてからスケジューラコア、EEVDF、sched_ext、特殊クラス、SMP 可観測性へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。

## 第0部　プロセスの表現とライフサイクル

1. [task_struct の構造](part00-process/01-task-struct.md)
2. [fork とプロセス生成（copy_process）](part00-process/02-fork-copy-process.md)
3. [exec とプログラム実行](part00-process/03-exec-program.md)
4. [exit と wait](part00-process/04-exit-wait.md)
5. [シグナル配送](part00-process/05-signal-delivery.md)
6. [カーネルスレッド（kthread）](part00-process/06-kthread.md)
7. [ptrace](part00-process/07-ptrace.md)

## 第1部　スケジューラコア

8. [ランキューとスケジューリングクラスの階層](part01-core/08-runqueue-sched-class.md)
9. [__schedule とコンテキストスイッチ](part01-core/09-schedule-context-switch.md)
10. [try_to_wake_up と wakeup の中核](part01-core/10-try-to-wake-up.md)
11. [プリエンプションモデル（PREEMPT_NONE から PREEMPT_LAZY まで）](part01-core/11-preemption-model.md)

## 第2部　EEVDF スケジューラ

12. [vruntime と eligibility（CFS から EEVDF への転換）](part02-eevdf/12-vruntime-eligibility.md)
13. [enqueue と dequeue と pick_next_task](part02-eevdf/13-enqueue-dequeue-pick.md)
14. [group scheduling と cgroup 階層](part02-eevdf/14-group-scheduling-cgroup.md)

## 第3部　sched_ext

15. [ext_sched_class と sched_ext_ops](part03-sched-ext/15-ext-sched-class-ops.md)
16. [DSQ とディスパッチ実行の流れ](part03-sched-ext/16-dsq-dispatch-flow.md)
17. [有効化と bypass、ext_idle](part03-sched-ext/17-enable-bypass-idle.md)

## 第4部　RT と deadline

18. [RT クラス](part04-classes/18-rt-class.md)
19. [deadline クラス](part04-classes/19-deadline-class.md)

## 第5部　マルチコアと可観測性

20. [sched domain とトポロジ構築](part05-smp-obs/20-topology-sched-domains.md)
21. [PELT による負荷追跡](part05-smp-obs/21-pelt-load-tracking.md)
22. [ロードバランスと NUMA](part05-smp-obs/22-load-balance-numa.md)
23. [PSI と統計](part05-smp-obs/23-psi-stats.md)
24. [スケジューラ操作 API（sched_setaffinity と uclamp）](part05-smp-obs/24-scheduler-syscalls-api.md)
25. [cputime、loadavg、schedstats](part05-smp-obs/25-cputime-loadavg-schedstats.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコア分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
