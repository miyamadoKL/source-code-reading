# Linux カーネル デバイスモデルとドライバ基盤

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）のデバイスモデルとドライバ基盤を読み解く分冊である。
`struct device` と `device_driver` と `bus_type` を軸に、デバイスの登録、ファームウェア記述（Device Tree と ACPI）からの列挙、ドライバとのマッチと probe、device links による依存解決、unbind と削除の解除経路までを追う。
後半では PCI を題材に、host bridge 登録、コンフィグ空間アクセス、バススキャンとリソース割り当て、ドライバのバインドと利用準備、MSI/MSI-X、ホットプラグ、SR-IOV、AER によるエラー回復をソースから読む。

- **対象バージョン**：6.18.38（コード引用はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（大きな変更は [`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)への固定リンク付き注釈）
- **想定読者**：[全体像と横断基盤](../foundation/README.md) の kobject と sysfs を読み、C とオペレーティングシステムの基礎がある中級エンジニア
- **読み方**：第0部から順に読む。
  デバイスモデルの全体像とデータ構造を押さえてから、登録、列挙、マッチと probe、依存と解除へ進み、後半で PCI のデータ構造、列挙、ドライバ、動的な生成と削除を読む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
アーキテクチャ依存の記述は x86-64 を既定とする。

本分冊の委譲境界は次のとおりである。

- **kobject と sysfs の内部機構**：参照カウント、kset、kernfs、sysfs の実装は [全体像と横断基盤](../foundation/part04-infra/13-kobject-sysfs.md) に委譲する。
  本分冊では `struct device` が kobject をどう埋め込み、属性グループとリンクをいつ生成するかに焦点を当てる。
- **MSI 割り込みドメイン**：`irq_domain` の階層と Linux IRQ 番号の割り当ては [割り込みと時間](../irq-time/part00-genirq/04-msi-domain.md) に委譲する。
  本分冊では PCI capability の設定と `pci_alloc_irq_vectors` の PCI 側に焦点を当てる。
- **電源管理の状態遷移**：suspend と resume のフェーズ順序、runtime PM の状態機械、PCI の D-state 詳細は [電源管理と CPU ライフサイクル](../power-cpu/README.md) に委譲する。
  本分冊では `device_add` と `device_del` が PM の対象集合をいつ構築するかに焦点を当てる。
- **範囲外**：firmware loader（`request_firmware`）、regmap、DMA mapping と IOMMU の内部は本分冊の範囲外とし、driver core の主要経路が触れる接続点（`really_probe` の `dma_configure`、PCI の DMA mask と `pci_set_master`）のみ扱う。

## 第0部　デバイスモデルの全体像

1. [分冊の全体像とデバイスモデルが解く問題](part00-overview/01-device-model-overview.md)
2. [中核データ構造と所有構造](part00-overview/02-core-data-structures-ownership.md)

## 第1部　登録とユーザー空間への公開

3. [bus_type の登録とバスへの追加](part01-registration/03-bus-register.md)
4. [device の登録操作と削除規約](part01-registration/04-device-add-del.md)
5. [class とデバイスの提示、devtmpfs](part01-registration/05-class-devtmpfs.md)
6. [uevent と modalias によるモジュール自動ロード](part01-registration/06-uevent-modalias.md)

## 第2部　ファームウェア記述とデバイス列挙

7. [デバイスプロパティと fwnode / software node](part02-enumeration/07-device-property-fwnode.md)
8. [Device Tree からの platform device 列挙](part02-enumeration/08-device-tree-platform.md)
9. [ACPI デバイス列挙の概観](part02-enumeration/09-acpi-scan.md)

## 第3部　マッチングと probe

10. [ドライバ登録と二方向マッチと async probe](part03-probe/10-driver-match-async-probe.md)
11. [really_probe とバインドの中核](part03-probe/11-really-probe.md)
12. [deferred probe](part03-probe/12-deferred-probe.md)
13. [platform バスによるマッチと probe の実例](part03-probe/13-platform-bus.md)

## 第4部　依存関係とリソースと解除

14. [device links と fw_devlink](part04-links-devres-unbind/14-device-links-fw-devlink.md)
15. [devres によるマネージドリソース](part04-links-devres-unbind/15-devres.md)
16. [unbind と remove とデバイス削除](part04-links-devres-unbind/16-unbind-remove-del.md)

## 第5部　PCI のデータ構造と列挙

17. [PCI サブシステムの全体像と host bridge 登録](part05-pci-enumeration/17-pci-overview-host-bridge.md)
18. [コンフィグ空間アクセスと capability 探索](part05-pci-enumeration/18-pci-config-capability.md)
19. [PCI バススキャンとデバイス生成](part05-pci-enumeration/19-pci-bus-scan.md)
20. [BAR 調査とリソース割り当てと二段階追加](part05-pci-enumeration/20-pci-bar-resource-assign.md)

## 第6部　PCI のドライバと割り込み

21. [PCI ドライバのバインド](part06-pci-driver/21-pci-driver-bind.md)
22. [PCI ドライバの利用準備](part06-pci-driver/22-pci-enable-device.md)
23. [MSI/MSI-X の PCI 側プログラミング](part06-pci-driver/23-pci-msi.md)

## 第7部　PCI のホットプラグと発展機能

24. [PCIe ホットプラグと再帰的削除](part07-pci-dynamic/24-pcie-hotplug.md)
25. [SR-IOV による VF 生成](part07-pci-dynamic/25-sriov.md)
26. [PCIe AER とエラー回復](part07-pci-dynamic/26-pcie-aer.md)

---

> 本分冊は執筆中である。
> コード引用は `gregkh/linux` の `v6.18.38` タグに固定し、7.x 系の大きな変化は `v7.1.3` タグへの固定リンク付きで注記する。
