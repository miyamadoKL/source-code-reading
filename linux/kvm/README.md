# Linux カーネル 仮想化（KVM）

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の KVM ハイパーバイザを読み解く分冊である。
`/dev/kvm` 経由の VM と vCPU ライフサイクル、`KVM_RUN` 実行ループ、ゲストメモリ管理、x86 の EPT/NPT を含む KVM MMU、Intel VMX と AMD SVM の VM-entry/exit、割り込み注入、MMIO と eventfd/ioeventfd、dirty log、vhost の virtqueue 概観まで、カーネル側のコア機構をソースから追う。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md)、[メモリ管理](../mm/README.md)、[割り込みと時間](../irq-time/README.md) を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  KVM 全体像とデータ構造を押さえてから KVM コア、ゲストメモリ、x86 MMU、x86 共通処理、VMX、SVM、割り込みと I/O、vhost へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。
ホストのページテーブルと TLB の一般論は [メモリ管理](../mm/part03-virtual/16-page-table-walk-missing-fault.md) を参照し、本分冊ではゲスト物理アドレス（GPA）と EPT/NPT へのマッピングに焦点を当てる。
`mmu_notifier` の一般論は mm 分冊を参照し、本分冊では KVM が notifier をどう登録しゲスト MMU と連動するかに焦点を当てる。

本分冊の委譲境界は次のとおりである。

- **ゲスト OS**：ゲストカーネル、ゲストのページフォールト処理、ゲストドライバの内部実装は対象外とする。
  ゲストが見る CPU 機能（cpuid、MSR）は KVM がどうエミュレート・透過するかに限定して扱う。
- **QEMU 等 userspace VMM**：`/dev/kvm` の ioctl 契約とカーネル側の応答に留め、デバイスモデル、マシン定義、マイグレーションの userspace 実装は境界としてのみ触れる。
- **個別デバイスエミュレーション**：`i8254.c`、`i8259.c` 等のレガシーデバイス個別実装の網羅列挙は行わない。
  irqchip と LAPIC が割り込みをどう届けるかの接続点に焦点を当てる。
- **VFIO と IOMMU**：`virt/kvm/vfio.c` はデバイス割り当ての接続点として概観に留め、IOMMU ドライバ（`drivers/iommu/`）と VFIO 本体は本分冊の範囲外とする。
- **機密計算（SEV、TDX）**：`arch/x86/kvm/svm/sev.c`、`arch/x86/kvm/vmx/tdx.c` は将来の専門トピックとして境界に留め、本分冊では通常の VMX/SVM 経路を主題とする。
- **Xen 互換**：`arch/x86/kvm/xen.c` は本分冊の範囲外とする。
- **Hyper-V enlightenment**：`arch/x86/kvm/hyperv.c` と `kvm_onhyperv.c` はタイマー・再同期など主要フックの概観に留め、個別 hypercall の網羅は行わない。
- **vhost の派生実装**：`vhost-scsi.c`、`vsock.c`、`vdpa.c` は virtqueue モデルとの関係を注記する程度に留め、第8部では `vhost.c` と `vhost-net` を主題とする。
- **他アーキテクチャ**：`arch/arm64/kvm/` 等は本分冊の範囲外とする。

## 第0部　仮想化の基盤

1. [KVM の全体像と userspace 境界](part00-foundation/01-kvm-overview-userspace-boundary.md)
2. [`struct kvm` / `kvm_vcpu` とアーキテクチャ ops](part00-foundation/02-kvm-vcpu-arch-ops.md)

## 第1部　KVM コア

3. [VM の生成・破棄と ioctl 面](part01-kvm-core/03-vm-lifecycle-ioctl.md)
4. [vCPU の生成・破棄とリクエスト機構](part01-kvm-core/04-vcpu-lifecycle-requests.md)
5. [`KVM_RUN` と vCPU 実行ループ](part01-kvm-core/05-kvm-run-execution-loop.md)

## 第2部　ゲストメモリ

6. [メモリスロット、`guest_memfd`、ホストバッキング](part02-guest-memory/06-memory-slots-guest-memfd.md)
7. [`mmu_notifier` とリモート TLB flush](part02-guest-memory/07-mmu-notifier-remote-tlb.md)
8. [dirty page tracking（bitmap と dirty ring）](part02-guest-memory/08-dirty-page-tracking.md)

## 第3部　x86 KVM MMU

9. [シャドウページテーブルと TDP（EPT/NPT）のモデル](part03-x86-mmu/09-shadow-tdp-model.md)
10. [SPTE とゲスト page fault 処理](part03-x86-mmu/10-spte-page-fault.md)
11. [TDP MMU fast path と `tdp_mmu`](part03-x86-mmu/11-tdp-mmu-fastpath.md)

## 第4部　x86 共通

12. [レジスタ、MSR、cpuid、例外注入](part04-x86-common/12-regs-msr-cpuid-exceptions.md)
13. [命令エミュレーション（`emulate.c`）](part04-x86-common/13-instruction-emulation.md)

## 第5部　Intel VMX

14. [VMX 有効化と VMCS の構築](part05-vmx/14-vmx-enable-vmcs.md)
15. [`vmx_vcpu_run` と VM-exit 処理](part05-vmx/15-vmx-run-exit.md)
16. [nested VMX と posted interrupt 概観](part05-vmx/16-nested-vmx-posted-intr.md)

## 第6部　AMD SVM

17. [VMCB と `svm_vcpu_run`](part06-svm/17-vmcb-svm-run.md)
18. [nested SVM と AVIC 概観](part06-svm/18-nested-svm-avic.md)

## 第7部　割り込みと I/O

19. [irqchip、LAPIC、割り込み注入](part07-irq-io/19-irqchip-lapic-injection.md)
20. [MMIO bus、`ioeventfd`、`irqfd`](part07-irq-io/20-mmio-ioeventfd-irqfd.md)

## 第8部　vhost

21. [vhost フレームワークと virtqueue](part08-vhost/21-vhost-virtqueue.md)
22. [vhost-net データパス](part08-vhost/22-vhost-net-datapath.md)

---

> 本分冊は Linux カーネル読解ドキュメント群の仮想化分冊である。
> コード引用は `v6.18.38` に固定し、7.x 系の注釈のみ `v7.1.3` を使う。
> vCPU のホスト側スケジューリング（`vcpu_load` と preempt 抑止の関係）は [プロセスとスケジューラ](../sched/README.md) との接点として必要最小限に触れる。
