# Linux カーネル 同期と RCU

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）のアトミック操作、スピンロック、スリープ系ロック、lockdep、RCU、per-CPU 変数を読み解く分冊である。
マルチプロセッサ上でデータ競合を防ぎつつ、読み取りのスケーラビリティを保つ同期機構をソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md) と [プロセスとスケジューラ](../sched/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  アトミックと per-CPU を押さえてからスピン系、スリープ系、正しさ検証、RCU へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。

## 第0部　同期の基礎

1. [アトミック操作とメモリバリア](part00-foundation/01-atomic-barrier.md)
2. [per-CPU 変数](part00-foundation/02-percpu.md)

## 第1部　スピン系ロック

3. [spinlock と qspinlock](part01-spinning/03-spinlock-qspinlock.md)
4. [rwlock と seqlock](part01-spinning/04-rwlock-seqlock.md)

## 第2部　スリープ系ロック

5. [mutex と optimistic spinning](part02-sleeping/05-mutex-osq.md)
6. [rwsem](part02-sleeping/06-rwsem.md)
7. [ww_mutex と percpu-rwsem](part02-sleeping/07-ww-mutex-percpu-rwsem.md)
8. [waitqueue](part02-sleeping/08-waitqueue.md)
9. [semaphore と completion](part02-sleeping/09-semaphore-completion.md)

## 第3部　正しさの検証と RT

10. [lockdep](part03-correctness/10-lockdep.md)
11. [rt_mutex と priority inheritance](part03-correctness/11-rt-mutex-pi.md)

## 第4部　RCU

12. [RCU の基本概念と API](part04-rcu/12-rcu-basics.md)
13. [Tree RCU と grace period](part04-rcu/13-tree-rcu-gp.md)
14. [RCU CPU stall 警告の診断](part04-rcu/14-rcu-stall-diagnosis.md)
15. [SRCU](part04-rcu/15-srcu.md)
16. [Tasks RCU](part04-rcu/16-tasks-rcu.md)
17. [call_rcu と callback 処理](part04-rcu/17-call-rcu-callback.md)
18. [expedited と nocb などの発展](part04-rcu/18-expedited-nocb.md)

## 第5部　futex

19. [futex の基礎と wait/wake](part05-futex/19-futex-hash-wait-wake.md)
20. [requeue と PI futex](part05-futex/20-futex-requeue-pi.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコア分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
