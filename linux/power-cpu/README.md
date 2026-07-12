# Linux カーネル 電源管理と CPU ライフサイクル

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）のシステムサスペンド、ハイバネート、freezer、PM QoS、cpufreq、cpuidle、CPU hotplug を読み解く分冊である。
システム全体の電源遷移から CPU 周波数・idle 状態の制御、CPU のオンライン・オフラインまで、コア機構をソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md)、[プロセスとスケジューラ](../sched/README.md)、[割り込みと時間](../irq-time/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  全体像と PM コアを押さえてからシステムサスペンド、cpufreq、cpuidle、CPU hotplug へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。
`schedutil` のスケジューラ側（PELT、`update_util`、`cpufreq_update_util` の呼び出し元）は [プロセスとスケジューラ](../sched/README.md) に委譲し、本分冊では `cpufreq_schedutil.c` と cpufreq ガバナ基盤の連携に焦点を当てる。
CPU hotplug 時のタスク migration と load balance は sched 分冊へ委譲し、本分冊では `cpuhp` 状態機械と `cpus_read_lock` を中心に読む。
idle 中の tick 停止と NO_HZ は [割り込みと時間](../irq-time/part03-tick/18-no-hz.md) を参照し、本分冊では `cpuidle_idle_call` から cpuidle フレームワークへの入口に焦点を当てる。
cgroup freezer は [namespace と cgroup](../ns-cgroup/README.md) へ委譲し、システム全体の `pm_freezing` は `kernel/freezer.c` と `kernel/power/process.c` に限定して扱う。
個別 SoC 向け cpufreq/cpuidle プラットフォームドライバの列挙は行わない。

## 第0部　基盤

1. [電源管理と CPU ライフサイクルの全体像](part00-foundation/01-power-cpu-overview.md)
2. [PM サブシステムコアと遷移ロック](part00-foundation/02-pm-core-transition.md)

## 第1部　システム電源管理

3. [Freezer とタスク停止](part01-system-pm/03-freezer-task-freeze.md)
4. [Suspend to RAM と s2idle](part01-system-pm/04-suspend-s2idle.md)
5. [Hibernate の遷移とユーザー空間 IF](part01-system-pm/05-hibernate-transition.md)
6. [Snapshot とスワップイメージ](part01-system-pm/06-snapshot-swap-image.md)
7. [PM QoS と制約の集約](part01-system-pm/07-pm-qos.md)
8. [Energy Model と性能ドメイン](part01-system-pm/08-energy-model.md)

## 第2部　cpufreq

9. [cpufreq フレームワークと policy](part02-cpufreq/09-cpufreq-framework-policy.md)
10. [cpufreq ドライバ層（x86 代表）](part02-cpufreq/10-cpufreq-drivers-x86.md)
11. [cpufreq ガバナ基盤と schedutil 連携](part02-cpufreq/11-cpufreq-governor-schedutil.md)
12. [ondemand と conservative ガバナ](part02-cpufreq/12-ondemand-conservative.md)

## 第3部　cpuidle

13. [cpuidle フレームワークとドライバ登録](part03-cpuidle/13-cpuidle-framework-driver.md)
14. [cpuidle ガバナと状態選択](part03-cpuidle/14-cpuidle-governors.md)
15. [sched idle 入口と cpuidle 連携](part03-cpuidle/15-sched-idle-cpuidle.md)

## 第4部　CPU hotplug

16. [CPU hotplug 状態機械](part04-hotplug/16-cpuhp-state-machine.md)
17. [cpu maps、hotplug ロック、サブシステム連携](part04-hotplug/17-cpu-maps-hotplug-integration.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコア分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
> `pm_runtime` とデバイスドライバ個別のランタイム PM は本分冊の範囲外とし、デバイスモデル分冊執筆時に扱う。
