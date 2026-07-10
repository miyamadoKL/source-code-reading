# Linux カーネル 割り込みと時間

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の genirq、softirq、workqueue、タイマー、tick、クロックソースを読み解く分冊である。
ハードウェア割り込みから遅延実行、時刻の維持とユーザー空間への提供までをソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md)、[プロセスとスケジューラ](../sched/README.md)、[同期と RCU](../locking/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  割り込み基盤を押さえてから遅延実行、タイマー、tick、IPI とユーザー空間への時刻提供へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。

## 第0部　割り込み基盤

1. [irq_desc と irq_domain](part00-genirq/01-irq-desc-domain.md)
2. [フローハンドラと irq_chip](part00-genirq/02-flow-handler-chip.md)
3. [request_irq からハンドラ実行まで](part00-genirq/03-request-irq-handler.md)

## 第1部　遅延実行

4. [softirq と tasklet](part01-deferred/04-softirq-tasklet.md)
5. [workqueue の構造](part01-deferred/05-workqueue-structure.md)
6. [workqueue の実行と並行性管理](part01-deferred/06-workqueue-execution.md)

## 第2部　タイマー

7. [タイマーホイール](part02-timer/07-timer-wheel.md)
8. [hrtimer](part02-timer/08-hrtimer.md)
9. [clocksource と clockevents](part02-timer/09-clocksource-clockevents.md)
10. [timekeeping](part02-timer/10-timekeeping.md)

## 第3部　tick と NO_HZ

11. [tick デバイスと周期 tick](part03-tick/11-tick-device.md)
12. [NO_HZ](part03-tick/12-no-hz.md)

## 第4部　連携

13. [IPI と smp_call_function](part04-ipc-time/13-ipi-smp-call.md)
14. [ユーザー空間への時刻提供](part04-ipc-time/14-userspace-time-vdso.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコア分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
