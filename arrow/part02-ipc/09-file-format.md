# 第9章 ファイル形式と Feather

> **本章で読むソース**
>
> - [`format/File.fbs`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/File.fbs)
> - [`docs/source/format/IPC.rst`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/IPC.rst)
> - [`docs/source/format/Columnar.rst`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst)
> - [`python/pyarrow/ipc.pxi`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.pxi)
> - [`python/pyarrow/ipc.py`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.py)
> - [`python/pyarrow/feather.py`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/feather.py)
> - [`python/pyarrow/_feather.pyx`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/_feather.pyx)

## この章の狙い

第8章で一方向ストリームとしての IPC を読んだ。
本章では、同じメッセージ列に**フッタ**を付けてランダムアクセスを可能にした**IPC ファイル形式**を `File.fbs` と `Columnar.rst` から追う。
`RecordBatchFileReader` と `RecordBatchFileWriter`、および Feather V2 がこの形式であることを `feather` モジュールから確認する。

## 前提

IPC ファイルはストリーム形式の拡張である。
ファイル先頭と末尾にマジック `ARROW1` があり、中央は第8章と同じ封入メッセージ列である。
末尾フッタにスキーマの写しと各ブロックのオフセットが入り、任意のレコードバッチへシークできる。

## ファイルレイアウト

仕様は次の構成を示す。
マジック、パディング、ストリーム本体（EOS 付き）、フッタ、フッタ長、末尾マジックの順である。

[`docs/source/format/Columnar.rst` L1517-L1533](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1517-L1533)

```text
We define a "file format" supporting random access that is an extension of
the stream format. The file starts and ends with a magic string ``ARROW1``
(plus padding). What follows in the file is identical to the stream format.
At the end of the file, we write a *footer* containing a redundant copy of
the schema (which is a part of the streaming format) plus memory offsets and
sizes for each of the data blocks in the file. This enables random access to
any record batch in the file. See `File.fbs`_ for the precise details of the
file footer.

Schematically we have: ::

    <magic number "ARROW1">
    <empty padding bytes [to 8 byte boundary]>
    <STREAMING FORMAT with EOS>
    <FOOTER>
    <FOOTER SIZE: little-endian int32>
    <magic number "ARROW1">
```

フッタを先に読めば、ストリーム全体を順送りしなくてもバッチ位置が分かる。
ディスク上の列データストアでは、メタデータだけ先に mmap して必要なチャンクだけ読む運用が一般的である。

レイアウトを Mermaid で示すと次のようになる。

```mermaid
graph LR
    MAGIC1["ARROW1 magic"]
    STREAM["IPC stream with EOS"]
    FOOT["Footer flatbuffer"]
    FSIZE["footer size int32"]
    MAGIC2["ARROW1 magic"]
    MAGIC1 --> STREAM --> FOOT --> FSIZE --> MAGIC2
```

## File.fbs の Footer と Block

`Footer` テーブルはメタデータ版、スキーマ、辞書ブロック列、レコードバッチブロック列、任意の `custom_metadata` を持つ。

[`format/File.fbs` L26-L37](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/File.fbs#L26-L37)

```text
table Footer {
  version: org.apache.arrow.flatbuf.MetadataVersion;

  schema: org.apache.arrow.flatbuf.Schema;

  dictionaries: [ Block ];

  recordBatches: [ Block ];

  /// User-defined metadata
  custom_metadata: [ KeyValue ];
}
```

`Block` は各レコードバッチに対応する封入メッセージのファイル内位置を記録する。
C++ のファイルライタは `WriteIpcPayload` を呼ぶ直前のストリーム位置を `FileBlock.offset` に保存する。
リーダはこの値をファイル内の絶対オフセットとして `ReadMessage(block.offset, ...)` に渡す。
したがって `offset` は封入メッセージ（encapsulated message）先頭を指すファイル内の絶対位置である。
封入メッセージは4バイト長プレフィックスで始まる。
現行の非レガシー形式では、その前に4バイトの継続指示子 `0xFFFFFFFF` が付きプレフィックス全体は8バイトになる。
レガシー形式（`write_legacy_ipc_format` が真）では継続指示子がなく、プレフィックスは4バイトである。
FlatBuffers の `Message` ヘッダより後の RecordBatch 本体でも、先頭マジックからの相対位置でもない。
`File.fbs` の `Block` コメントは RecordBatch 開始と読めるが、実装が記録するのは封入メッセージ全体の先頭である。
`metaDataLength` は長さプレフィックス、FlatBuffers メタデータ、パディングを含むメタデータ部の長さである。
`bodyLength` はメッセージ本体の長さである。

[`format/File.fbs` L39-L50](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/File.fbs#L39-L50)

```text
struct Block {

  /// Index to the start of the RecordBatch (note this is past the Message header)
  offset: long;

  /// Length of the metadata
  metaDataLength: int;

  /// Length of the data (this is aligned so there can be a gap between this and
  /// the metadata).
  bodyLength: long;
}
```

`get_batch(i)` はフッタの `recordBatches[i]` から位置を引き、C++ 側の `ReadRecordBatch(i)` で第7章の封入メッセージをデコードする。
インデックス `i` からブロック位置を引く操作は定数時間だが、シーク後の本体読み出しとデコードのコストはバッチサイズに依存する。

## ストリーム形式との等価性と差分

フッタはストリーム内情報の冗長写しである。
準拠ライタは、フッタのスキーマと先頭ストリームのスキーマを一致させ、ブロック順序もストリーム出現順と揃えることが推奨される。

[`docs/source/format/Columnar.rst` L1538-L1551](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1538-L1551)

```text
Since the IPC file footer duplicates information already found in the embedded IPC
stream, there is a theoretical possibility that said information diverges. However,
we request that compliant IPC file writers follow these guidelines:

1. The metadata version, schema and custom metadata serialized in the IPC file
   footer (as part of the ``Footer`` Flatbuffers table) MUST be identical to the
   metadata version, schema and custom metadata serialized at the beginning of
   the embedded IPC stream (as part of the first ``Message`` Flatbuffers table).

2. The dictionaries and record batches serialized in the IPC file footer
   SHOULD be listed in the same order as they appear in the embedded IPC stream,
```

ランダムアクセス可能なファイルでは、辞書の扱いにストリームとの差がある。
初期辞書をすべてのレコードバッチより前に置く要件はファイルにはなく、辞書の置換はサポートされず、デルタはフッタ記載順に適用される。

[`docs/source/format/Columnar.rst` L1556-L1567](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1556-L1567)

```text
The random accessible nature of IPC Files leads to semantic differences when
decoding dictionary-encoded data:

1. While the IPC Streaming format requires that all initial dictionary batches
   are emitted before any record batch, there is no such requirement in the IPC
   File format.

2. The IPC File format does not support dictionary replacement, i.e. only one
   non-delta dictionary batch can be emitted for a given dictionary ID.

3. Delta dictionary batches in an IPC File are applied in the order they appear
   in the file footer.
```

ファイルへ書くときは `IpcWriteOptions.unify_dictionaries` で辞書を統一し、置換を避ける設計が現実的である（第8章）。

拡張子 `.arrow` と MIME 型 `vnd.apache.arrow.file` が推奨される。
歴史的に Feather V2 や `.feather` という名前でも知られる。

[`docs/source/format/Columnar.rst` L1572-L1580](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1572-L1580)

```text
We recommend the ".arrow" extension for IPC Files. The registered MIME type for
IPC Files is `vnd.apache.arrow.file`_.

.. admonition:: Historical note

   Files created with this format were sometimes called "Feather V2" or
   named with the ".feather" extension, stemming from "Feather (V1)", a proof of
   concept early in the Arrow project for fast language-agnostic dataframe storage
   supporting only a small subset of Arrow types.
```

## RecordBatchFileWriter

`_RecordBatchFileWriter` は `MakeFileWriter` でファイルライタを開く。
ストリームライタを継承するため、`write_batch` と `write_table` の API は共通である。
ファイル固有の差分は、クローズ時にフッタを書き込む点にある。

[`python/pyarrow/ipc.pxi` L1106-L1123](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.pxi#L1106-L1123)

```python
cdef class _RecordBatchFileWriter(_RecordBatchStreamWriter):

    def _open(self, sink, Schema schema not None,
              IpcWriteOptions options=IpcWriteOptions(),
              metadata=None):
        cdef:
            shared_ptr[COutputStream] c_sink
            shared_ptr[const CKeyValueMetadata] c_meta

        self.options = options.c_options
        get_writer(sink, &c_sink)

        metadata = ensure_metadata(metadata, allow_none=True)
        c_meta = pyarrow_unwrap_metadata(metadata)

        with nogil:
            self.writer = GetResultValue(
                MakeFileWriter(c_sink, schema.sp_schema, self.options, c_meta))
```

`ipc.new_file` がファクトリであり、`metadata` 引数でフッタに載るファイル全体のキーと値を渡せる。

[`python/pyarrow/ipc.py` L76-L79](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.py#L76-L79)

```python
metadata : dict | pyarrow.KeyValueMetadata, optional
    Key/value pairs (both must be bytes-like) that will be stored
    in the file footer and are retrievable via
    pyarrow.ipc.open_file(...).metadata."""
```

[`python/pyarrow/ipc.py` L191-L192](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.py#L191-L192)

```python
def new_file(sink, schema, *, options=None, metadata=None):
    return RecordBatchFileWriter(sink, schema, options=options, metadata=metadata)
```

## RecordBatchFileReader

`_RecordBatchFileReader` はランダムアクセスファイルを開き、フッタからスキーマとバッチ数を得る。
`get_batch(i)` はインデックス指定で単一バッチを読む。

[`python/pyarrow/ipc.pxi` L1147-L1216](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.pxi#L1147-L1216)

```python
cdef class _RecordBatchFileReader(_Weakrefable):
    // ... (中略) ...
    def _open(self, source, footer_offset=None,
              IpcReadOptions options=IpcReadOptions(),
              MemoryPool memory_pool=None):
        // ... (中略) ...
        with nogil:
            if offset != 0:
                self.reader = GetResultValue(
                    CRecordBatchFileReader.Open2(self.file.get(), offset,
                                                 self.options))

            else:
                self.reader = GetResultValue(
                    CRecordBatchFileReader.Open(self.file.get(),
                                                self.options))

        self.schema = pyarrow_wrap_schema(self.reader.get().schema())

    @property
    def num_record_batches(self):
        """
        The number of record batches in the IPC file.
        """
        return self.reader.get().num_record_batches()

    def get_batch(self, int i):
        // ... (中略) ...
        with nogil:
            batch = GetResultValue(self.reader.get().ReadRecordBatch(i))

        return pyarrow_wrap_batch(batch)
```

`footer_offset` は、Arrow ファイルがより大きなコンテナに埋め込まれているとき、末尾からの絶対位置を渡すための引数である。

`read_all` は全インデックスを順に `ReadRecordBatch` し、`Table.FromRecordBatches` で結合する。

[`python/pyarrow/ipc.pxi` L1249-L1268](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.pxi#L1249-L1268)

```python
    def read_all(self):
        """
        Read all record batches as a pyarrow.Table
        """
        cdef:
            vector[shared_ptr[CRecordBatch]] batches
            shared_ptr[CTable] table
            int i, nbatches

        nbatches = self.num_record_batches

        batches.resize(nbatches)
        with nogil:
            for i in range(nbatches):
                batches[i] = GetResultValue(self.reader.get()
                                            .ReadRecordBatch(i))
            table = GetResultValue(
                CTable.FromRecordBatches(self.schema.sp_schema, move(batches)))

        return pyarrow_wrap_table(table)
```

`metadata` プロパティはフッタの `custom_metadata` を辞書として返す。

[`python/pyarrow/ipc.pxi` L1288-L1294](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.pxi#L1288-L1294)

```python
    @property
    def metadata(self):
        """
        File-level custom metadata as dict, where both keys and values are byte-like.
        This kind of metadata can be written via ``ipc.new_file(..., metadata=...)``.
        """
        wrapped = pyarrow_wrap_metadata(self.reader.get().metadata())
        return wrapped.to_dict() if wrapped is not None else None
```

`ipc.open_file` が公開エントリポイントである。

[`python/pyarrow/ipc.py` L207-L231](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.py#L207-L231)

```python
def open_file(source, footer_offset=None, *, options=None, memory_pool=None):
    """
    Create reader for Arrow file format.
    // ... (中略) ...
    """
    return RecordBatchFileReader(
        source, footer_offset=footer_offset,
        options=options, memory_pool=memory_pool)
```

## Feather V2 と IPC ファイル

`pyarrow.feather` の V2 は Arrow IPC ファイル形式そのものである。
`write_feather` は非推奨だが、内部で `_feather.write_feather` を呼び、C++ の `WriteFeather` へ委譲する。

[`python/pyarrow/feather.py` L125-L158](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/feather.py#L125-L158)

```python
def write_feather(df, dest, compression=None, compression_level=None,
                  chunksize=None, version=2):
    """
    Write a pandas.DataFrame to Feather format.

    .. deprecated:: 24.0.0
       Use :func:`pyarrow.ipc.new_file` /
       :class:`pyarrow.ipc.RecordBatchFileWriter` instead.
       Feather V2 is the Arrow IPC file format.
    // ... (中略) ...
    """
    warnings.warn(
        "pyarrow.feather.write_feather is deprecated as of 24.0.0. "
        "Use pyarrow.ipc.new_file() / RecordBatchFileWriter instead. "
        "Feather V2 is the Arrow IPC file format.",
```

V2 では LZ4 が利用可能ならデフォルト圧縮に使われ、`chunksize` でレコードバッチの最大行数を制御できる。

[`python/pyarrow/feather.py` L199-L210](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/feather.py#L199-L210)

```python
    else:
        if compression is None and Codec.is_available('lz4_frame'):
            compression = 'lz4'
        elif (compression is not None and
              compression not in _FEATHER_SUPPORTED_CODECS):
            raise ValueError(f'compression="{compression}" not supported, must be '
                             f'one of {_FEATHER_SUPPORTED_CODECS}')

    try:
        _feather.write_feather(table, dest, compression=compression,
                               compression_level=compression_level,
                               chunksize=chunksize, version=version)
```

`_feather.pyx` の `write_feather` は `CFeatherProperties` に版、圧縮、チャンクサイズを設定し `WriteFeather` を呼ぶ。

[`python/pyarrow/_feather.pyx` L38-L64](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/_feather.pyx#L38-L64)

```python
def write_feather(Table table, object dest, compression=None,
                  compression_level=None, chunksize=None, version=2):
    cdef shared_ptr[COutputStream] sink
    get_writer(dest, &sink)

    cdef CFeatherProperties properties
    if version == 2:
        properties.version = kFeatherV2Version
    else:
        properties.version = kFeatherV1Version

    if compression == 'zstd':
        properties.compression = CCompressionType_ZSTD
    elif compression == 'lz4':
        properties.compression = CCompressionType_LZ4_FRAME
    else:
        properties.compression = CCompressionType_UNCOMPRESSED
    // ... (中略) ...
    with nogil:
        check_status(WriteFeather(deref(table.table), sink.get(),
                                  properties))
```

`FeatherReader` は `memory_map` フラグを `get_reader` に渡し、ディスク上ファイルのゼロコピー読み出しを選べる。

[`python/pyarrow/_feather.pyx` L67-L79](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/_feather.pyx#L67-L79)

```python
cdef class FeatherReader(_Weakrefable):
    // ... (中略) ...
    def __cinit__(self, source, c_bool use_memory_map, c_bool use_threads):
        cdef:
            shared_ptr[CRandomAccessFile] reader
            CIpcReadOptions options = CIpcReadOptions.Defaults()
        options.use_threads = use_threads

        get_reader(source, use_memory_map, &reader)
        with nogil:
            self.reader = GetResultValue(CFeatherReader.Open(reader, options))
```

`read_table` も `ipc.open_file` への移行が案内されている。

[`python/pyarrow/feather.py` L301-L329](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/feather.py#L301-L329)

```python
def read_table(source, columns=None, memory_map=False, use_threads=True):
    """
    Read a pyarrow.Table from Feather format

    .. deprecated:: 24.0.0
       Use :func:`pyarrow.ipc.open_file` /
       :class:`pyarrow.ipc.RecordBatchFileReader` instead.
       Feather V2 is the Arrow IPC file format.
    // ... (中略) ...
    """
    warnings.warn(
        "pyarrow.feather.read_table is deprecated as of 24.0.0. "
        "Use pyarrow.ipc.open_file() / RecordBatchFileReader instead. "
```

Feather V1 は型の部分集合だけを扱う別形式であり、V2 へ移行後は IPC ファイルと同一の表現力を得る。

## まとめ

IPC ファイルはストリームに `ARROW1` マジックと `Footer` を加えた形式である。
`Block` のオフセット列により任意のレコードバッチへ O(1) でシークでき、フッタだけ mmap する運用が可能になる。
辞書はファイル形式では置換不可であり、ライタ側で辞書統一が現実的である。
`RecordBatchFileWriter` は書き込み中にブロック位置を記録し、クローズ時にフッタを書く。
`RecordBatchFileReader.get_batch` はインデックス指定読み出しの入口である。
Feather V2 は IPC ファイルの別名であり、新規コードは `ipc.new_file` と `open_file` を使う。

## 関連する章

- 第7章 [メッセージ形式とレコードバッチ](07-message-format.md)：`RecordBatch` と `Buffer`
- 第8章 [ストリーミング IPC](08-streaming-ipc.md)：埋め込みストリーム本体
- 第10章 Buffer とメモリ管理：メモリマップと `foreign_buffer`
- 第15章 Dataset：IPC を `format='ipc'` で読む高レベル API
