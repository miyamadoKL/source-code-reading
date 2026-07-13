# Linux カーネル Rust for Linux

Linux カーネル（[gregkh/linux](https://github.com/gregkh/linux)）の Rust サポート層 `rust/` を読み解く分冊である。
`kernel` クレートと `pin-init` クレート、手続きマクロ、そして C カーネルとの FFI 層を対象に、**安全な Rust 抽象が `unsafe` な C の API をどう安全境界で包むか**を、ビルド統合から実ドライバの登録経路まで一貫して追う。

- **対象バージョン**：6.18.38（コード引用の既定はすべて [`v6.18.38` タグ](https://github.com/gregkh/linux/tree/v6.18.38)に固定）
- **対比バージョン**：7.1.3（[`v7.1.3` タグ](https://github.com/gregkh/linux/tree/v7.1.3)）を基準に、6.18→7.1 で約2.4倍（48k→116k 行）に拡大した Rust for Linux の変化を**各章で対比的に注記し、部末に差分表を置く**
- **想定読者**：Rust の所有権とトレイトの基礎があり、[デバイスモデルとドライバ基盤](../driver-model/README.md) と [同期と RCU](../locking/README.md) の C 側実装を把握している中級エンジニア
- **読み方**：第0部から順に読む。
  ビルドと FFI の土台、言語基盤、メモリ確保、同期、データ構造を押さえ、IO と DMA を導入してからユーザー空間 I/O 境界、デバイスモデルと割り込み、バス抽象へ進む。

コード引用は `[path L開始-L終了](https://github.com/gregkh/linux/blob/v6.18.38/...)` 形式のリンクとコードブロックの2点セットで示す。
7.1.3 との対比引用は `v7.1.3` タグへの固定リンクを使い、本文で基準版か比較版かを明示する。

本分冊の委譲境界は次のとおりである。

- **C 側のドライバコア**：`struct device`、bus と probe、sysfs、devres の C 実装は [デバイスモデルとドライバ基盤](../driver-model/README.md) に委譲する。
  本分冊は Rust 側の `Device`、`Driver`、`Registration`、`Devres` 抽象が C 側をどう包むかを扱い、safe wrapper が依存する C 側契約だけは各章に残す。
- **C 側の同期プリミティブ**：`mutex`、`spinlock`、RCU、`refcount_t` の C 実装は [同期と RCU](../locking/README.md) に委譲する。
  本分冊は Rust 側の `Lock`／`Guard` 抽象、`Arc`、`CondVar`、`rcu::Guard`、`Atomic` が保証する安全性を扱う。
- **C 側のメモリ確保とバスと割り込み**：slab／vmalloc、PCI コア、DMA API、genirq、hrtimer の C 実装は [メモリ管理](../mm/README.md)、[デバイスモデルとドライバ基盤](../driver-model/README.md)、[割り込みと時間](../irq-time/README.md) に委譲する。
  本分冊は Rust 側の `Allocator`、`KBox`／`KVec`、`pci::Driver`、`CoherentAllocation`、`irq::Registration`、`HrTimer` を扱う。
- **範囲外**：個別の実デバイスドライバの網羅、block（`kernel/block/`）の詳細、非同期 Rust（`async`）の一般論、コンパイラ内部。
  7.1.3 で新規追加された `gpu`／`iommu`／`i2c`／`pwm`／`soc` は最終章で代表系統を深掘りし、残りは索引表で扱う。

## 第0部　全体像とビルド統合

1. [Rust for Linux の全体像と kernel クレート](part00-overview-build/01-overview-kernel-crate.md)
2. [ビルド統合とツールチェイン](part00-overview-build/02-build-integration-toolchain.md)
3. [FFI とバインディング生成と helper](part00-overview-build/03-ffi-bindings-helpers.md)

## 第1部　言語基盤と safe/unsafe の橋渡し

4. [module! マクロとモジュール登録](part01-language-foundation/04-module-macro.md)
5. [エラー処理と Result と errno](part01-language-foundation/05-error-result.md)
6. [型の基盤 Opaque と ARef と ForeignOwnable](part01-language-foundation/06-types-opaque-aref.md)
7. [pin-init によるピン留め初期化](part01-language-foundation/07-pin-init.md)

## 第2部　メモリ確保と所有権

8. [アロケータと GFP フラグ](part02-memory-ownership/08-allocator-gfp.md)
9. [KBox と KVec と確保失敗の伝播](part02-memory-ownership/09-kbox-kvec.md)

## 第3部　同期プリミティブ

10. [Arc とアトミック参照カウント](part03-synchronization/10-arc-refcount.md)
11. [Lock 抽象と Mutex と SpinLock と locked_by](part03-synchronization/11-lock-mutex-spinlock.md)
12. [CondVar と Completion と待機](part03-synchronization/12-condvar-completion.md)
13. [RCU とアトミックとメモリオーダリング](part03-synchronization/13-rcu-atomic.md)

## 第4部　データ構造と文字列

14. [侵入型リストと ListArc](part04-data-structures/14-intrusive-list.md)
15. [RBTree と木の所有権モデル](part04-data-structures/15-rbtree.md)
16. [XArray と Maple Tree による索引](part04-data-structures/16-xarray-maple-tree.md)
17. [文字列と CStr と数値解析と表示](part04-data-structures/17-str-cstr-fmt.md)

## 第5部　IO と DMA と非同期実行とタイマー

18. [MMIO と IO 抽象](part05-io-dma-async/18-mmio-io.md)
19. [DMA コヒーレント確保](part05-io-dma-async/19-dma-coherent.md)
20. [workqueue と非同期実行](part05-io-dma-async/20-workqueue.md)
21. [hrtimer と高分解能タイマー抽象](part05-io-dma-async/21-hrtimer.md)

## 第6部　ユーザー空間 I/O 境界

22. [ファイルと uaccess と IovIter](part06-userspace-io/22-file-uaccess-iov.md)
23. [miscdevice と ioctl と poll と seq_file](part06-userspace-io/23-miscdevice-ioctl-poll.md)

## 第7部　デバイスモデルと割り込み

24. [Device と参照カウントと状態型](part07-device-model-irq/24-device-refcount.md)
25. [Driver と登録と probe](part07-device-model-irq/25-driver-registration-probe.md)
26. [devres と Revocable によるリソース管理](part07-device-model-irq/26-devres-revocable.md)
27. [IRQ 要求とスレッド化ハンドラ](part07-device-model-irq/27-irq-request.md)

## 第8部　バス抽象と 7.x への展望

28. [platform デバイスと OF マッチング](part08-bus-future/28-platform-of.md)
29. [PCI ドライバ抽象と BAR と IRQ](part08-bus-future/29-pci-driver.md)
30. [7.x での拡大と新規サブシステムの設計傾向](part08-bus-future/30-7x-expansion.md)

---

> 本分冊は執筆中である。
> コード引用は `gregkh/linux` の `v6.18.38` タグに固定し、7.x 系の変化は `v7.1.3` タグへの固定リンク付きで対比注記する。
