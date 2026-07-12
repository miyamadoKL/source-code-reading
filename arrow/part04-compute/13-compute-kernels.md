# 第13章 計算カーネルと FunctionRegistry

> **本章で読むソース**
>
> - [`python/pyarrow/_compute.pyx`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/_compute.pyx)
> - [`python/pyarrow/compute.py`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/compute.py)

## この章の狙い

第1部から第3部で、型、レイアウト、IPC、メモリ共有まで読んだ。
配列に対する加算、比較、集約といった演算は、C++ コアの **compute** モジュールが **Function** と **Kernel** の組で提供する。
本章では `FunctionRegistry` と `call_function` を入口に、関数の種類、カーネル選択、Python 層でのグローバル関数生成まで追う。
第14章の Acero 実行計画と第15章の Dataset スキャンは、いずれもこの compute 関数を下層で呼び出す。

## 前提

`pyarrow.compute` モジュールは、`_compute.pyx` の Cython バインディングと `compute.py` の薄い Python ラッパーからなる。
演算の実体は C++ の `arrow::compute::Function` であり、入力の型組み合わせごとに **Kernel** が実装を提供する。
Python からは関数名でルックアップし、`call_function` またはモジュール直下の `add` や `cast` などで呼び出す。

## Function の種類

`Function` は論理演算を表し、入力シグネチャの範囲ごとに Kernel が割り当てられる。
docstring は関数を次の五種に分類している。

[`python/pyarrow/_compute.pyx` L259-L287](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/_compute.pyx#L259-L287)

```python
cdef class Function(_Weakrefable):
    """
    A compute function.

    A function implements a certain logical computation over a range of
    possible input signatures.  Each signature accepts a range of input
    types and is implemented by a given Kernel.

    Functions can be of different kinds:

    * "scalar" functions apply an item-wise computation over all items
      of their inputs.  Each item in the output only depends on the values
      of the inputs at the same position.  Examples: addition, comparisons,
      string predicates...

    * "vector" functions apply a collection-wise computation, such that
      each item in the output may depend on the values of several items
      in each input.  Examples: dictionary encoding, sorting, extracting
      unique values...

    * "scalar_aggregate" functions reduce the dimensionality of the inputs by
      applying a reduction function.  Examples: sum, min_max, mode...

    * "hash_aggregate" functions apply a reduction function to an input
      subdivided by grouping criteria.  They may not be directly called.
      Examples: hash_sum, hash_min_max...

    * "meta" functions dispatch to other functions.
    """
```

**scalar** は要素ごとの写像である。
**vector** はソートや辞書符号化のように全体を見る。
**scalar_aggregate** は次元を落とす集約である。
**hash_aggregate** はグループ単位の集約で、Acero の `aggregate` ノードから間接的に使われる。
**meta** は他関数への振り分けである。

`kind` プロパティと `num_kernels` で、登録済み実装の規模を確認できる。

## FunctionRegistry と call_function

グローバルな `FunctionRegistry` は起動時に C++ 側のレジストリを包む。
`get_function` で名前検索し、`list_functions` で全名を列挙する。

[`python/pyarrow/_compute.pyx` L529-L611](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/_compute.pyx#L529-L611)

```python
cdef class FunctionRegistry(_Weakrefable):
    cdef CFunctionRegistry* registry

    def __init__(self):
        self.registry = GetFunctionRegistry()

    def list_functions(self):
        """
        Return all function names in the registry.
        """
        cdef vector[c_string] names = self.registry.GetFunctionNames()
        return [frombytes(name) for name in names]

    def get_function(self, name):
        // ... (中略) ...
        with nogil:
            func = GetResultValue(self.registry.GetFunction(c_name))
        return wrap_function(func)
// ... (中略) ...
def call_function(name, args, options=None, memory_pool=None, length=None):
    """
    Call a named function.
    // ... (中略) ...
    """
    func = _global_func_registry.get_function(name)
    return func.call(args, options=options, memory_pool=memory_pool,
                     length=length)
```

`call_function` は名前解決のあと `Function.call` へ委譲する薄い入口である。
`memory_pool` を渡せば、第10章の `MemoryPool` 上で中間バッファを確保できる。

呼び出し経路を Mermaid で示すと次のようになる。

```mermaid
graph LR
    PY["compute.add など"]
    CF["call_function"]
    REG["FunctionRegistry"]
    FN["Function"]
    EXEC["C++ Execute"]
    PY --> CF
    CF --> REG
    REG --> FN
    FN --> EXEC
```

## Function.call とカーネル実行

`Function.call` は引数を `CExecBatch` に詰め、C++ 側の `Execute` へ渡す。
`CExecContext` にメモリプールを渡し、割り当て先を制御する。

[`python/pyarrow/_compute.pyx` L366-L410](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/_compute.pyx#L366-L410)

```python
    def call(self, args, FunctionOptions options=None,
             MemoryPool memory_pool=None, length=None):
        // ... (中略) ...
        cdef:
            const CFunctionOptions* c_options = NULL
            CMemoryPool* pool = maybe_unbox_memory_pool(memory_pool)
            CExecContext c_exec_ctx = CExecContext(pool)
            CExecBatch c_batch
            CDatum result

        _pack_compute_args(args, &c_batch.values)

        if options is not None:
            c_options = options.get_options()

        if length is not None:
            c_batch.length = length
            with nogil:
                result = GetResultValue(
                    self.base_func.Execute(c_batch, c_options, &c_exec_ctx)
                )
        else:
            with nogil:
                result = GetResultValue(
                    self.base_func.Execute(c_batch.values, c_options,
                                           &c_exec_ctx)
                )

        return wrap_datum(result)
```

カーネル選択と実行本体は C++ compute モジュールが担い、Python 層の `_compute.pyx` からは `Execute` 呼び出しまで追える。
`cast` のように Python ラッパーが暗黙キャストや型昇格を行う関数もあり、入力型の扱いは関数ごとに異なる。

`ScalarFunction` には登録済みカーネル列を返す `kernels` プロパティがあり、シグネチャごとの実装がいくつあるかを確認できる。

[`python/pyarrow/_compute.pyx` L420-L426](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/_compute.pyx#L420-L426)

```python
    @property
    def kernels(self):
        """
        The kernels implementing this function.
        """
        cdef vector[const CScalarKernel*] kernels = self.func.kernels()
        return [wrap_scalar_kernel(k) for k in kernels]
```

## compute.py によるグローバル関数の生成

モジュール import 時に `_make_global_functions` がレジストリを走査し、各 `Function` を Python 関数で包む。
`hash_aggregate` と、引数ゼロの `scalar_aggregate` はモジュール直下に露出しない。

[`python/pyarrow/compute.py` L314-L343](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/compute.py#L314-L343)

```python
def _make_global_functions():
    """
    Make global functions wrapping each compute function.

    Note that some of the automatically-generated wrappers may be overridden
    by custom versions below.
    """
    g = globals()
    reg = function_registry()

    # Avoid clashes with Python keywords
    rewrites = {'and': 'and_',
                'or': 'or_'}

    for cpp_name in reg.list_functions():
        name = rewrites.get(cpp_name, cpp_name)
        func = reg.get_function(cpp_name)
        if func.kind == "hash_aggregate":
            # Hash aggregate functions are not callable,
            # so let's not expose them at module level.
            continue
        if func.kind == "scalar_aggregate" and func.arity == 0:
            # Nullary scalar aggregate functions are not callable
            # directly so let's not expose them at module level.
            continue
        assert name not in g, name
        g[cpp_name] = g[name] = _wrap_function(name, func)


_make_global_functions()
```

`_wrap_function` は docstring、シグネチャ、`FunctionOptions` の受け渡しを整える。
その結果、数百の演算が `pc.add(a, b)` のように直接呼べる。

## カスタムラッパーの例：cast

自動生成を上書きする代表例が `cast` である。
`target_type` と `safe` から `CastOptions` を組み立て、底层の `call_function("cast", ...)` を呼ぶ。

[`python/pyarrow/compute.py` L348-L414](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/compute.py#L348-L414)

```python
def cast(arr, target_type=None, safe=None, options=None, memory_pool=None):
    """
    Cast array values to another data type. Can also be invoked as an array
    instance method.
    // ... (中略) ...
    """
    // ... (中略) ...
    if options is None:
        target_type = pa.types.lib.ensure_type(target_type)
        if safe is False:
            options = CastOptions.unsafe(target_type)
        else:
            options = CastOptions.safe(target_type)
    return call_function("cast", [arr], options, memory_pool)
```

`FunctionOptions` サブクラスは演算ごとの追加パラメータを型安全に渡す仕組みである。
`CastOptions` はオーバーフローチェックの有無を制御し、カーネル側の分岐に直結する。

## Expression との関係

`compute.py` は `Expression` も再エクスポートする。
`pc.field("a") > 1` のような式は、第15章の Dataset フィルタや第14章の `FilterNodeOptions` に渡される。
実行時には式が分解され、対応する scalar 関数の組に落ちる。
レジストリに名前のある関数は、バッチ評価と式評価の両方から到達できる。

## まとめ

compute 層は **FunctionRegistry** が全演算名を保持し、**Function** が論理契約を、**Kernel** が型別実装を担う。
`call_function` と `Function.call` は C++ 側 `Execute` へ至る共通入口であり、カーネル選択と実行本体は C++ 実装に委ねられる。
`compute.py` はレジストリを走査してグローバル関数を自動生成し、必要な箇所だけ `cast` のように手書きラッパーで上書きする。
Acero と Dataset はこの関数群を下層で再利用する。

## 関連する章

- 第2章 [カラムレイアウト](../part00-overview/02-columnar-layout.md)：カーネルが前提とするメモリ配置
- 第10章 [Buffer とメモリ管理](../part03-memory/10-buffer-and-memory.md)：`memory_pool` 引数
- 第14章 [Acero 実行計画](14-acero.md)：`FilterNodeOptions` と join
- 第15章 [Dataset と Scanner](15-dataset.md)：フィルタ式のプッシュダウン
