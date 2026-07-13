# Linux カーネル 電源管理と CPU ライフサイクル

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）のシステムサスペンド、ハイバネート、freezer、PM QoS、デバイス runtime PM、wakeup source、generic power domain、cpufreq、cpuidle、CPU hotplug を読み解く分冊である。
システム全体の電源遷移から CPU 周波数・idle 状態の制御、CPU のオンライン・オフラインまで、コア機構をソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md)、[プロセスとスケジューラ](../sched/README.md)、[割り込みと時間](../irq-time/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  全体像と PM コアを押さえてからシステムサスペンド、device PM（runtime PM・wakeup・genpd）、cpufreq、cpuidle、CPU hotplug へ進む。

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

## 第2部　device PM

9. [device PM callback と DPM 順序](part02-device-pm/09-dpm-callback-order.md)
10. [runtime PM 状態機械](part02-device-pm/10-runtime-pm-state-machine.md)
11. [wakeup source と wake IRQ](part02-device-pm/11-wakeup-source-wake-irq.md)
12. [generic power domain](part02-device-pm/12-generic-power-domain.md)

## 第3部　cpufreq

13. [cpufreq フレームワークと policy](part03-cpufreq/13-cpufreq-framework-policy.md)
14. [cpufreq ドライバ層（x86 代表）](part03-cpufreq/14-cpufreq-drivers-x86.md)
15. [cpufreq ガバナ基盤と schedutil 連携](part03-cpufreq/15-cpufreq-governor-schedutil.md)
16. [ondemand と conservative ガバナ](part03-cpufreq/16-ondemand-conservative.md)

## 第4部　cpuidle

17. [cpuidle フレームワークとドライバ登録](part04-cpuidle/17-cpuidle-framework-driver.md)
18. [cpuidle ガバナと状態選択](part04-cpuidle/18-cpuidle-governors.md)
19. [sched idle 入口と cpuidle 連携](part04-cpuidle/19-sched-idle-cpuidle.md)

## 第5部　CPU hotplug

20. [CPU hotplug 状態機械](part05-hotplug/20-cpuhp-state-machine.md)
21. [cpu maps、hotplug ロック、サブシステム連携](part05-hotplug/21-cpu-maps-hotplug-integration.md)

---

> 本分冊は Linux カーネル読解ドキュメント群のコア分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
> デバイス runtime PM の状態機械・DPM callback 順序・wakeup source・generic power domain は第2部で本分冊が扱う。
> 個別デバイスドライバの PM callback 実装やデバイスモデルのライフサイクルは [デバイスモデルとドライバ基盤](../driver-model/README.md) を参照する。
