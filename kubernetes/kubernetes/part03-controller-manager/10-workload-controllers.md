# 第10章 主要コントローラ（ReplicaSet, Deployment, StatefulSet）

> 本章で読むソース
>
> - [pkg/controller/replicaset/replica_set.go L1-L996](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/replicaset/replica_set.go#L1-L996)
> - [pkg/controller/deployment/deployment_controller.go L1-L679](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/deployment/deployment_controller.go#L1-L679)
> - [pkg/controller/deployment/sync.go L1-L568](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/deployment/sync.go#L1-L568)
> - [pkg/controller/statefulset/stateful_set_control.go L1-L846](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/statefulset/stateful_set_control.go#L1-L846)

## この章の狙い

Kubernetes のワークロードコントローラの中核である ReplicaSet、Deployment、StatefulSet の調停ロジックを読む。
ReplicaSet は期待 Pod 数と実 Pod 数の差分を埋める基本機構、Deployment は ReplicaSet を経由してローリングアップデートを実現する上位層、StatefulSet は Ordinal 管理と安定したネットワーク識別子を提供する。
それぞれのコントローラが informer と workqueue の共通パターンをどのように拡張しているかを追う。

## 前提

- 第9章で kube-controller-manager の起動フローと expectations 機構を理解している。
- Pod、ReplicaSet、Deployment、StatefulSet の API 仕様を知っている。

## ReplicaSet コントローラ

### 構造体

`ReplicaSetController` は `GroupVersionKind` を埋め込み、ReplicaSet と ReplicationController の両方を扱えるようにしている。

[pkg/controller/replicaset/replica_set.go L95-L140](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/replicaset/replica_set.go#L95-L140)

```go
// ReplicaSetController is responsible for synchronizing ReplicaSet objects stored
// in the system with actual running pods.
type ReplicaSetController struct {
    schema.GroupVersionKind
    kubeClient clientset.Interface
    podControl controller.PodControlInterface
    podIndexer       cache.Indexer
    eventBroadcaster record.EventBroadcaster
    burstReplicas int
    syncHandler func(ctx context.Context, rsKey string) error
    expectations *controller.UIDTrackingControllerExpectations
    rsLister appslisters.ReplicaSetLister
    rsListerSynced cache.InformerSynced
    rsIndexer      cache.Indexer
    podLister corelisters.PodLister
    podListerSynced cache.InformerSynced
    queue workqueue.TypedRateLimitingInterface[string]
    // ...
}
```

`expectations` は `UIDTrackingControllerExpectations` 型で、作成・削除の期待値を UID 単位で追跡する。
`burstReplicas` は1回の sync で作成・削除できる Pod 数の上限（デフォルト500）である。

### イベントハンドラ

ReplicaSet と Pod の informer にイベントハンドラを登録する。

[pkg/controller/replicaset/replica_set.go L223-L268](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/replicaset/replica_set.go#L223-L268)

```go
rsInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
    AddFunc: func(obj interface{}) {
        rsc.addRS(logger, obj)
    },
    UpdateFunc: func(oldObj, newObj interface{}) {
        rsc.updateRS(logger, oldObj, newObj)
    },
    DeleteFunc: func(obj interface{}) {
        rsc.deleteRS(logger, obj)
    },
})
// ...
podInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
    AddFunc: func(obj interface{}) {
        rsc.addPod(logger, obj)
    },
    UpdateFunc: func(oldObj, newObj interface{}) {
        rsc.updatePod(logger, oldObj, newObj)
    },
    DeleteFunc: func(obj interface{}) {
        rsc.deletePod(logger, obj)
    },
})
```

Pod の作成イベントでは `CreationObserved` を呼び、削除イベントでは `DeletionObserved` を呼ぶ。
これにより expectations のカウンタが更新される。

### syncReplicaSet

調停の本体。

[pkg/controller/replicaset/replica_set.go L752-L857](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/replicaset/replica_set.go#L752-L857)

```go
func (rsc *ReplicaSetController) syncReplicaSet(ctx context.Context, key string) error {
    // ...
    rs, err := rsc.rsLister.ReplicaSets(namespace).Get(name)
    // ...
    rsNeedsSync := rsc.expectations.SatisfiedExpectations(logger, key)
    selector, err := metav1.LabelSelectorAsSelector(rs.Spec.Selector)
    // ...
    allRSPods, err := controller.FilterPodsByOwner(rsc.podIndexer, &rs.ObjectMeta, rsc.Kind, true)
    // ...
    allActivePods := controller.FilterActivePods(logger, allRSPods)
    activePods, err := rsc.claimPods(ctx, rs, selector, allActivePods)
    // ...
    if rsNeedsSync && rs.DeletionTimestamp == nil {
        manageReplicasErr = rsc.manageReplicas(ctx, activePods, rs)
    }
    // ...
    newStatus := calculateStatus(rs, activePods, terminatingPods, manageReplicasErr, ...)
    updatedRS, err := updateReplicaSetStatus(...)
    // ...
}
```

`expectations.SatisfiedExpectations` が false を返すと、`manageReplicas` をスキップする。
これにより watch イベントの遅延中に過剰な Pod を作成しない。

### manageReplicas

期待数と実数の差分を計算し、Pod の作成または削除を行う。

[pkg/controller/replicaset/replica_set.go L646-L749](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/replicaset/replica_set.go#L646-L749)

```go
func (rsc *ReplicaSetController) manageReplicas(ctx context.Context, activePods []*v1.Pod, rs *apps.ReplicaSet) error {
    diff := len(activePods) - int(*(rs.Spec.Replicas))
    // ...
    if diff < 0 {
        diff *= -1
        if diff > rsc.burstReplicas {
            diff = rsc.burstReplicas
        }
        rsc.expectations.ExpectCreations(logger, rsKey, diff)
        // ...
        successfulCreations, err := slowStartBatch(diff, controller.SlowStartInitialBatchSize, func() error {
            err := rsc.podControl.CreatePods(ctx, rs.Namespace, &rs.Spec.Template, rs, ...)
            // ...
        })
        // ...
    } else if diff > 0 {
        if diff > rsc.burstReplicas {
            diff = rsc.burstReplicas
        }
        // ...
        podsToDelete := getPodsToDelete(activePods, relatedPods, diff)
        rsc.expectations.ExpectDeletions(logger, rsKey, getPodKeys(podsToDelete))
        // ...並列削除...
    }
    return nil
}
```

不足分は `slowStartBatch` で段階的に作成し、余剰分は並列に削除する。
削除する Pod の選択は `getPodsToDelete` で、同じノード上の Pod が多いものを優先的に残すヒューリスティックが働く。

## Deployment コントローラ

### 構造体

`DeploymentController` は ReplicaSet を介在させて Pod を管理する。

[pkg/controller/deployment/deployment_controller.go L65-L101](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/deployment/deployment_controller.go#L65-L101)

```go
type DeploymentController struct {
    rsControl controller.RSControlInterface
    client    clientset.Interface
    eventBroadcaster record.EventBroadcaster
    eventRecorder    record.EventRecorder
    syncHandler func(ctx context.Context, dKey string) error
    enqueueDeployment func(deployment *apps.Deployment)
    dLister appslisters.DeploymentLister
    rsLister appslisters.ReplicaSetLister
    podLister corelisters.PodLister
    podIndexer cache.Indexer
    dListerSynced cache.InformerSynced
    rsListerSynced cache.InformerSynced
    podListerSynced cache.InformerSynced
    queue workqueue.TypedRateLimitingInterface[string]
}
```

Deployment 自体は Pod を直接管理しない。
新しい ReplicaSet を作成し、古い ReplicaSet のレプリカ数を減らすことでローリングアップデートを実現する。

### syncDeployment

[pkg/controller/deployment/deployment_controller.go L587-L679](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/deployment/deployment_controller.go#L587-L679)

```go
func (dc *DeploymentController) syncDeployment(ctx context.Context, key string) error {
    // ...
    d := deployment.DeepCopy()
    // ...
    rsList, err := dc.getReplicaSetsForDeployment(ctx, d)
    // ...
    podMap, err := dc.getPodMapForDeployment(d, rsList)
    // ...
    if d.Spec.Paused {
        return dc.sync(ctx, d, rsList)
    }
    if getRollbackTo(d) != nil {
        return dc.rollback(ctx, d, rsList)
    }
    scalingEvent, err := dc.isScalingEvent(ctx, d, rsList)
    // ...
    if scalingEvent {
        return dc.sync(ctx, d, rsList)
    }
    switch d.Spec.Strategy.Type {
    case apps.RecreateDeploymentStrategyType:
        return dc.rolloutRecreate(ctx, d, rsList, podMap)
    case apps.RollingUpdateDeploymentStrategyType:
        return dc.rolloutRolling(ctx, d, rsList)
    }
    return fmt.Errorf("unexpected deployment strategy type: %s", d.Spec.Strategy.Type)
}
```

Deployment の sync は以下の分岐を持つ。

1. **Paused**: 一時停止中はスケールのみ処理する。
2. **Rollback**: ロールバック指定があれば古い ReplicaSet に戻す。
3. **ScalingEvent**: レプリカ数変更は比例スケーリングで処理する。
4. **Recreate**: 全 Pod を削除してから新しい ReplicaSet を作成する。
5. **RollingUpdate**: 新しい ReplicaSet を徐々にスケールアップし、古い ReplicaSet を徐々にスケールダウンする。

### ローリングアップデートの比例スケーリング

`scale` 関数は新しい ReplicaSet と古い ReplicaSet のレプリカ数を比例配分する。

[pkg/controller/deployment/sync.go L302-L349](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/deployment/sync.go#L302-L349)

```go
func (dc *DeploymentController) scale(ctx context.Context, deployment *apps.Deployment, newRS *apps.ReplicaSet, oldRSs []*apps.ReplicaSet) error {
    // ...
    if deploymentutil.IsRollingUpdate(deployment) {
        allRSs := controller.FilterActiveReplicaSets(append(oldRSs, newRS))
        allRSsReplicas := deploymentutil.GetReplicaCountForReplicaSets(allRSs)
        allowedSize := int32(0)
        if *(deployment.Spec.Replicas) > 0 {
            allowedSize = *(deployment.Spec.Replicas) + deploymentutil.MaxSurge(*deployment)
        }
        deploymentReplicasToAdd := allowedSize - allRSsReplicas
        // ...比例配分...
    }
    // ...
}
```

`maxSurge` と `maxUnavailable` の制約内で、新しい ReplicaSet に追加できるレプリカ数を計算する。
各 ReplicaSet の現在のサイズに応じて比例配分することで、特定の ReplicaSet に偏らず安全にスケールする。

### 新しい ReplicaSet の作成

`getNewReplicaSet` は Pod テンプレートのハッシュから決定論的な名前を生成する。

[pkg/controller/deployment/sync.go L146-L300](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/deployment/sync.go#L146-L300)

```go
func (dc *DeploymentController) getNewReplicaSet(ctx context.Context, d *apps.Deployment, rsList, oldRSs []*apps.ReplicaSet, createIfNotExisted bool) (*apps.ReplicaSet, error) {
    // ...
    newRSTemplate := *d.Spec.Template.DeepCopy()
    podTemplateSpecHash := controller.ComputeHash(&newRSTemplate, d.Status.CollisionCount)
    newRSTemplate.Labels = labelsutil.CloneAndAddLabel(d.Spec.Template.Labels, apps.DefaultDeploymentUniqueLabelKey, podTemplateSpecHash)
    newRSSelector := labelsutil.CloneSelectorAndAddLabel(d.Spec.Selector, apps.DefaultDeploymentUniqueLabelKey, podTemplateSpecHash)
    newRS := apps.ReplicaSet{
        ObjectMeta: metav1.ObjectMeta{
            Name:            generateReplicaSetName(d.Name, podTemplateSpecHash),
            // ...
        },
        // ...
    }
    // ...
}
```

ハッシュ衝突が起きた場合は `CollisionCount` をインクリメントして再試行する。

## StatefulSet コントローラ

### 構造体

StatefulSet の制御ロジックは `defaultStatefulSetControl` が担う。

[pkg/controller/statefulset/stateful_set_control.go L43-L78](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/statefulset/stateful_set_control.go#L43-L78)

```go
type StatefulSetControlInterface interface {
    UpdateStatefulSet(ctx context.Context, set *apps.StatefulSet, pods []*v1.Pod, now time.Time) (*apps.StatefulSetStatus, error)
    ListRevisions(set *apps.StatefulSet) ([]*apps.ControllerRevision, error)
    AdoptOrphanRevisions(set *apps.StatefulSet, revisions []*apps.ControllerRevision) error
}

type defaultStatefulSetControl struct {
    podControl        *StatefulPodControl
    statusUpdater     StatefulSetStatusUpdaterInterface
    controllerHistory history.Interface
    revisionEqualityCache *lru.Cache
}
```

`revisionEqualityCache` は LRU キャッシュで、リビジョンの等価判定を高速化する。

### UpdateStatefulSet の流れ

[pkg/controller/statefulset/stateful_set_control.go L80-L107](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/statefulset/stateful_set_control.go#L80-L107)

```go
func (ssc *defaultStatefulSetControl) UpdateStatefulSet(ctx context.Context, set *apps.StatefulSet, pods []*v1.Pod, now time.Time) (*apps.StatefulSetStatus, error) {
    set = set.DeepCopy()
    revisions, err := ssc.ListRevisions(set)
    // ...
    history.SortControllerRevisions(revisions)
    currentRevision, updateRevision, status, err := ssc.performUpdate(ctx, set, pods, revisions, now)
    // ...
    return status, ssc.truncateHistory(set, pods, revisions, currentRevision, updateRevision)
}
```

1. ControllerRevision の一覧を取得し、世代順にソートする。
2. `performUpdate` で現在のリビジョンと更新リビジョンを決定し、Pod の作成・更新・削除を行う。
3. `truncateHistory` で履歴を制限数以内に切り詰める。

### updateStatefulSet の本体

Pod を2つのリストに分割する。

[pkg/controller/statefulset/stateful_set_control.go L560-L614](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/statefulset/stateful_set_control.go#L560-L614)

```go
func (ssc *defaultStatefulSetControl) updateStatefulSet(ctx context.Context, set *apps.StatefulSet, ...) (*apps.StatefulSetStatus, error) {
    // ...
    replicaCount := int(*set.Spec.Replicas)
    replicas := make([]*v1.Pod, replicaCount)
    condemned := make([]*v1.Pod, 0, len(pods))
    // ...
    for _, pod := range pods {
        if podInOrdinalRange(pod, set) {
            replicas[getOrdinal(pod)-getStartOrdinal(set)] = pod
        } else if getOrdinal(pod) >= 0 {
            condemned = append(condemned, pod)
        }
    }
    // ...
    start, end := getStartOrdinal(set), getEndOrdinal(set)
    for ord := start; ord <= end; ord++ {
        replicaIdx := ord - start
        if replicas[replicaIdx] == nil {
            replicas[replicaIdx] = newVersionedStatefulSetPod(
                currentSet, updateSet,
                currentRevision.Name, updateRevision.Name, ord)
        }
    }
    // ...
}
```

`replicas` は Ordinal の範囲内にある Pod を Ordinal 順に配置する。
空のスロットにはまだ作成されていない Pod のプレースホルダを入れる。
`condemned` は範囲外の Pod で、削除対象になる。

### Monotonic と Burst

`monotonic` フラグは PodManagementPolicy で決まる。

[pkg/controller/statefulset/stateful_set_control.go L649-L658](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/statefulset/stateful_set_control.go#L649-L658)

```go
monotonic := !allowsBurst(set)
// ...
processReplicaFn := func(i int) (bool, error) {
    return ssc.processReplica(ctx, set, updateSet, monotonic, replicas, i, now)
}
if shouldExit, err := runForAll(replicas, processReplicaFn, monotonic); shouldExit || err != nil {
    updateStatus(&status, ...)
    return &status, err
}
```

Monotonic モード（OrderedReady）では Pod を1つずつ順番に処理する。
Burst モード（Parallel）では `slowStartBatch` で並行処理する。

### processReplica

各 Pod の状態に応じた処理を行う。

[pkg/controller/statefulset/stateful_set_control.go L417-L505](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/statefulset/stateful_set_control.go#L417-L505)

```go
func (ssc *defaultStatefulSetControl) processReplica(ctx context.Context, set *apps.StatefulSet, ...) (bool, error) {
    if isFailed(replicas[i]) || isSucceeded(replicas[i]) {
        if replicas[i].DeletionTimestamp == nil {
            if err := ssc.podControl.DeleteStatefulPod(set, replicas[i]); err != nil {
                return true, err
            }
        }
        return true, nil
    }
    if !isCreated(replicas[i]) {
        // ...
        if err := ssc.podControl.CreateStatefulPod(ctx, set, replicas[i]); err != nil {
            return true, err
        }
        if monotonic {
            return true, nil
        }
    }
    // ...
    if !isRunningAndReady(replicas[i]) && monotonic {
        logger.V(4).Info("StatefulSet is waiting for Pod to be Running and Ready", ...)
        return true, nil
    }
    // ...
}
```

Monotonic モードでは Pod を1つ作成したら即座に return し、次の sync で次の Pod を処理する。
これにより Ordinal の小さい順に確実に起動していく。

### MaxUnavailable による並行更新

`MaxUnavailableStatefulSet` フィーチャゲートが有効な場合、`updateStatefulSetAfterInvariantEstablished` で複数 Pod の並行更新を許可する。

[pkg/controller/statefulset/stateful_set_control.go L738-L805](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/statefulset/stateful_set_control.go#L738-L805)

```go
func updateStatefulSetAfterInvariantEstablished(ctx context.Context, ssc *defaultStatefulSetControl, ...) (*apps.StatefulSetStatus, error) {
    // ...
    maxUnavailable, err = getStatefulSetMaxUnavailable(set.Spec.UpdateStrategy.RollingUpdate.MaxUnavailable, replicaCount)
    // ...
    unavailablePods := 0
    for target := len(replicas) - 1; target >= 0; target-- {
        if isUnavailable(replicas[target], set.Spec.MinReadySeconds, now) {
            unavailablePods++
        }
    }
    if unavailablePods >= maxUnavailable {
        return &status, nil
    }
    podsToDelete := maxUnavailable - unavailablePods
    deletedPods := 0
    for target := len(replicas) - 1; target >= updateMin && deletedPods < podsToDelete; target-- {
        if getPodRevision(replicas[target]) != updateRevision.Name && !isTerminating(replicas[target]) {
            if err := ssc.podControl.DeleteStatefulPod(set, replicas[target]); err != nil {
                return &status, err
            }
            deletedPods++
        }
    }
    return &status, nil
}
```

既に利用できない Pod 数を差し引いた分だけ、追加で Pod を削除できる。
これにより `maxUnavailable` の制約内で並行更新が進む。

## 最適化: Revision Equality Cache

StatefulSet の `setMatchesLatestExistingRevision` は LRU キャッシュでリビジョンの等価判定をスキップする。

[pkg/controller/statefulset/stateful_set_control.go L217-L258](https://github.com/kubernetes/kubernetes/blob/v1.36.2/pkg/controller/statefulset/stateful_set_control.go#L217-L258)

```go
const maxRevisionEqualityCacheEntries = 10_000

type revisionEqualityKey struct {
    setUID                  types.UID
    setGeneration           int64
    revisionResourceVersion string
}

func setMatchesLatestExistingRevision(set *apps.StatefulSet, proposedRevision *apps.ControllerRevision, latestExistingRevision *apps.ControllerRevision, memory *lru.Cache) bool {
    // ...
    equalityCacheKey := revisionEqualityKey{setUID: set.UID, setGeneration: set.Generation, revisionResourceVersion: latestExistingRevision.ResourceVersion}
    if _, ok := memory.Get(equalityCacheKey); ok {
        return true
    }
    // ... expensive comparison ...
    if history.EqualRevision(proposedRevision, reconstructedLatestRevision) {
        memory.Add(equalityCacheKey, struct{}{})
        return true
    }
    return false
}
```

StatefulSet の spec が変更されていない場合、毎回 ControllerRevision を再構築して比較するのは無駄である。
(setUID, setGeneration, revisionResourceVersion) の組み合わせをキャッシュキーとして、以前に等価と判定した組み合わせを記憶する。
キャッシュヒット時は高コストな比較をスキップできる。

## まとめ

ReplicaSet は Pod の期待数と実数の差分を埋める基本機構である。
Deployment は ReplicaSet を介在させてローリングアップデートとロールバックを実現する。
StatefulSet は Ordinal 管理と安定した識別子を提供し、monotonic な起動順序を保証する。
3つとも informer と workqueue の共通パターンに従い、expectations で watch 遅延に対策する。

## 関連する章

- [第9章 kube-controller-manager のアーキテクチャ](09-controller-manager-architecture.md)
- [第11章 主要コントローラ（Job, CronJob, DaemonSet）](11-batch-and-daemon-controllers.md)
