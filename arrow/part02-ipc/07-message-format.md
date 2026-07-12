# 第7章 メッセージ形式とレコードバッチ

> **本章で読むソース**
>
> - [`format/Message.fbs`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Message.fbs)
> - [`format/Schema.fbs`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Schema.fbs)
> - [`docs/source/format/Columnar.rst`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst)
> - [`docs/source/format/Metadata.rst`](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Metadata.rst)

## この章の狙い

第1部で型とレイアウト、ディクショナリエンコーディングまで読んだ。
本章では、メモリ上の配列をワイヤ上のバイナリへ写すための**IPC メッセージ**契約を `Message.fbs` と `Columnar.rst` から追う。
`Message` の封入形式、`RecordBatch` のメタデータ、`FieldNode` と `Buffer` の対応付け、オプションの `BodyCompression` を押さえ、第8章のストリームと第9章のファイル形式への土台を置く。

## 前提

列指向フォーマットの直列化単位は**レコードバッチ**である。
レコードバッチは同名フィールドの配列列を同じ長さで束ねたものであり、フィールド名と型の集合がスキーマになる。
IPC ではスキーマ、レコードバッチ、ディクショナリバッチの三種メッセージが一方向ストリームを構成する。

[`docs/source/format/Columnar.rst` L1194-L1209](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1194-L1209)

```text
The primitive unit of serialized data in the columnar format is the
"record batch". Semantically, a record batch is an ordered collection
of arrays, known as its **fields**, each having the same length as one
another but potentially different data types. A record batch's field
names and types collectively form the batch's **schema**.

In this section we define a protocol for serializing record batches
into a stream of binary payloads and reconstructing record batches
from these payloads without need for memory copying.

The columnar IPC protocol utilizes a one-way stream of binary messages
of these types:

* Schema
* RecordBatch
* DictionaryBatch
```

## 封入メッセージ形式

各 IPC メッセージは**封入形式**で運ばれる。
先頭に継続インジケータとメタデータ長、続いて FlatBuffers の `Message`、8 バイト境界へのパディング、最後にメッセージ本体が並ぶ。

[`docs/source/format/Columnar.rst` L1221-L1247](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1221-L1247)

```text
For simple streaming and file-based serialization, we define a
"encapsulated" message format for interprocess communication. Such
messages can be "deserialized" into in-memory Arrow array objects by
examining only the message metadata without any need to copy or move
any of the actual data.

The encapsulated binary message format is as follows:

* A 32-bit continuation indicator. The value ``0xFFFFFFFF`` indicates
  a valid message. This component was introduced in version 0.15.0 in
  part to address the 8-byte alignment requirement of Flatbuffers
* A 32-bit little-endian length prefix indicating the metadata size
* The message metadata as using the ``Message`` type defined in
  `Message.fbs`_
* Padding bytes to an 8-byte boundary
* The message body, whose length must be a multiple of 8 bytes
// ... (中略) ...
The complete serialized message must be a multiple of 8 bytes so that messages
can be relocated between streams.
```

読み手はまずメタデータをパースして `bodyLength` を得てから本体を読む。
メタデータだけで各バッファのオフセットと長さが分かるため、本体バイト列を既存メモリへマップすればポインタ演算で `Array` を再構成でき、コピーを避けられる。

封入形式を Mermaid で示すと次のようになる。

```mermaid
graph LR
    CONT["continuation 0xFFFFFFFF"]
    LEN["metadata_size int32"]
    META["Message flatbuffer"]
    PAD["padding to 8 bytes"]
    BODY["message body"]
    CONT --> LEN --> META --> PAD --> BODY
```

## Message と MessageHeader

`Message.fbs` のルート型 `Message` は、バージョン、ヘッダ union、本体長、任意の `custom_metadata` を持つ。

[`format/Message.fbs` L148-L157](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Message.fbs#L148-L157)

```text
union MessageHeader {
  Schema, DictionaryBatch, RecordBatch, Tensor, SparseTensor
}

table Message {
  version: org.apache.arrow.flatbuf.MetadataVersion;
  header: MessageHeader;
  bodyLength: long;
  custom_metadata: [ KeyValue ];
}
```

`MessageHeader` union により、メッセージ種別ごとに別テーブルを載せつつ共通の封入枠を共有する。
実装はすべての種別を扱う必要はなく、相互運用のためには `RecordBatch` の送受信が中心になる。

## FieldNode：ネストの論理長

`FieldNode` はネスト木の各ノードについて、そのレベルでの配列長と null 個数を記録する。
子を持たないリーフでも、親の `List` ノードと子の `Int16` ノードは別々の `FieldNode` になる。

[`format/Message.fbs` L28-L43](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Message.fbs#L28-L43)

```text
/// Metadata about a field at some level of a nested type tree (but not
/// its children).
///
/// For example, a List<Int16> with values `[[1, 2, 3], null, [4], [5, 6], null]`
/// would have {length: 5, null_count: 2} for its List node, and {length: 6,
/// null_count: 0} for its Int16 node, as separate FieldNode structs
struct FieldNode {
  /// The number of value slots in the Arrow array at this level of a nested
  /// tree
  length: long;

  /// The number of observed nulls. Fields with null_count == 0 may choose not
  /// to write their physical validity bitmap out as a materialized buffer,
  /// instead setting the length of the bitmap buffer to 0.
  null_count: long;
}
```

`null_count == 0` のとき validity ビットマップを省略できる規則は、ストレージと帯域の両方を削る。
デコーダは「バッファ長 0」を「全スロット有効」と解釈する。

## RecordBatch メタデータ

`RecordBatch` テーブルは、行数、前順序走査で平坦化した `FieldNode` 列、`Buffer` 列、任意の圧縮設定を持つ。

[`format/Message.fbs` L86-L120](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Message.fbs#L86-L120)

```text
table RecordBatch {
  /// number of records / rows. The arrays in the batch should all have this
  /// length
  length: long;

  /// Nodes correspond to the pre-ordered flattened logical schema
  nodes: [FieldNode];

  /// Buffers correspond to the pre-ordered flattened buffer tree
  ///
  /// The number of buffers appended to this list depends on the schema. For
  /// example, most primitive arrays will have 2 buffers, 1 for the validity
  /// bitmap and 1 for the values. For struct arrays, there will only be a
  /// single buffer for the validity (nulls) bitmap
  buffers: [Buffer];

  /// Optional compression of the message body
  compression: BodyCompression;
  // ... (中略) variadicBufferCounts ...
}
```

平坦化はスキーマのフィールドを深さ優先の前順序で走査する。
例として `Struct` 内の `List` を含むスキーマでは、親 struct、子 int32、子 list、孫 item、別列 utf8 の順に `FieldNode` が並ぶ。

[`docs/source/format/Columnar.rst` L1318-L1348](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1318-L1348)

```text
Fields and buffers are flattened by a pre-order depth-first traversal
of the fields in the record batch. For example, let's consider the
schema ::

    col1: Struct<a: Int32, b: List<item: Int64>, c: Float64>
    col2: Utf8

The flattened version of this is: ::

    FieldNode 0: Struct name='col1'
    FieldNode 1: Int32 name='a'
    FieldNode 2: List name='b'
    FieldNode 3: Int64 name='item'
    FieldNode 4: Float64 name='c'
    FieldNode 5: Utf8 name='col2'
// ... (中略) buffer 0 .. buffer 11 ...
```

`variadicBufferCounts` は `Utf8View` のように可変本数バッファを持つフィールドごとに、当該バッチで何本のデータバッファがあるかを伝える（フォーマット 1.4）。

[`docs/source/format/Columnar.rst` L1363-L1368](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1363-L1368)

```text
Some types such as Utf8View are represented using a variable number of buffers.
For each such Field in the pre-ordered flattened logical schema, there will be
an entry in ``variadicBufferCounts`` to indicate the number of variadic buffers
which belong to that Field in the current RecordBatch.
```

## Buffer：本体中のオフセット

`Buffer` は `Schema.fbs` で定義され、レコードバッチ本体先頭からの相対オフセットとバイト長を示す。
`length` はパディングを含まない実データ長であり、メモリ上の実サイズをそのまま書くことが推奨される。

[`format/Schema.fbs` L538-L551](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Schema.fbs#L538-L551)

```text
/// A Buffer represents a single contiguous memory segment
struct Buffer {
  /// The relative offset into the shared memory page where the bytes for this
  /// buffer starts
  offset: long;

  /// The absolute length (in bytes) of the memory buffer. The memory is found
  /// from offset (inclusive) to offset + length (non-inclusive). When building
  /// messages using the encapsulated IPC message, padding bytes may be written
  /// after a buffer, but such padding bytes do not need to be accounted for in
  /// the size here.
  length: long;
}
```

[`docs/source/format/Columnar.rst` L1350-L1356](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1350-L1356)

```text
The ``Buffer`` Flatbuffers value describes the location and size of a buffer's
data, relative to the start of the RecordBatch message's body.

The ``size`` field of ``Buffer`` is not required to account for padding
bytes. Since this metadata can be used to communicate in-memory pointer
addresses between libraries, it is recommended to set ``size`` to the actual
memory size rather than the padded size.
```

本体は各バッファを 8 バイトアライメントで連結した平坦列である。
メタデータの `buffers[i].offset` と `length` があれば、デコーダは本体スライスをそのまま `ArrayData` のバッファポインタに載せられる。

## BodyCompression

`BodyCompression` はレコードバッチ本体のバッファ単位圧縮を記述する。
現状の `method` は `BUFFER` のみで、各バッファを個別に圧縮する。

[`format/Message.fbs` L45-L81](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Message.fbs#L45-L81)

```text
enum CompressionType: byte {
  // LZ4 frame format, for portability, as provided by lz4frame.h or wrappers
  // thereof. Not to be confused with "raw" (also called "block") format
  // provided by lz4.h
  LZ4_FRAME,

  // Zstandard
  ZSTD
}
// ... (中略) ...
enum BodyCompressionMethod: byte {
  /// Each constituent buffer is first compressed with the indicated
  /// compressor, and then written with the uncompressed length in the first 8
  /// bytes as a 64-bit little-endian signed integer followed by the compressed
  /// buffer bytes (and then padding as required by the protocol). The
  /// uncompressed length may be set to -1 to indicate that the data that
  /// follows is not compressed, which can be useful for cases where
  /// compression does not yield appreciable savings.
  BUFFER
}
```

圧縮時は各バッファ先頭 8 バイトに非圧縮長を置き、続けて圧縮バイト列を書く。
非圧縮長を `-1` にすれば、そのバッファだけ生のまま送れる。
ランダムアクセスや再マップを想定した列ストレージでは、すでに圧縮済みの転送路（gzip など）と二重圧縮しない方がよい、と仕様は注意する。

[`docs/source/format/Columnar.rst` L1397-L1430](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1397-L1430)

```text
There are three different options for compression of record batch
body buffers: Buffers can be uncompressed, buffers can be
compressed with the ``lz4`` compression codec, or buffers can be
compressed with the ``zstd`` compression codec. Buffers in the
flat sequence of a message body must be compressed separately using
the same codec.
// ... (中略) ...
    little-endian signed integer stored in the first 8 bytes of each
    buffer in the sequence. This uncompressed length can be set to ``-1`` to indicate
    that that specific buffer is left uncompressed.
```

## スキーマメッセージとメタデータ

スキーマメッセージは本体を持たず、フィールド列とエンディアン宣言だけを運ぶ。
各 `Field` は名前、型、nullable、子フィールド、任意の `dictionary` を含む。

[`docs/source/format/Columnar.rst` L1264-L1286](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1264-L1286)

```text
Schema message
--------------

The Flatbuffers definition file `Schema.fbs`_ contains the definitions for all
built-in data types and the ``Schema`` metadata type which represents
the schema of a given record batch. A schema consists of an ordered
sequence of fields, each having a name and type. A serialized ``Schema``
does not contain any body, only metadata.
// ... (中略) ...
* A ``dictionary`` property indicating whether the field is
  dictionary-encoded or not. If it is, a dictionary "id" is assigned
  to allow matching a subsequent dictionary IPC message with the
  appropriate field.
```

`Metadata.rst` は列仕様書へ統合されたが、キーと値の任意メタデータは `KeyValue` テーブルで表現される。
スキーマ、フィールド、メッセージの各レベルに `custom_metadata` を付けられる。

[`format/Schema.fbs` L472-L478](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Schema.fbs#L472-L478)

```text
/// user defined key value pairs to add custom metadata to arrow
/// key namespacing is the responsibility of the user

table KeyValue {
  key: string;
  value: string;
}
```

[`format/Schema.fbs` L556-L565](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Schema.fbs#L556-L565)

```text
table Schema {

  /// endianness of the buffer
  /// it is Little Endian by default
  /// if endianness doesn't match the underlying system then the vectors need to be converted
  endianness: Endianness=Little;

  fields: [Field];
  // User-defined metadata
  custom_metadata: [ KeyValue ];
```

[`docs/source/format/Columnar.rst` L1288-L1290](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/docs/source/format/Columnar.rst#L1288-L1290)

```text
We additionally provide both schema-level and field-level
``custom_metadata`` attributes allowing for systems to insert their
own application-defined metadata to customize behavior.
```

`MetadataVersion` はメッセージごとに記録され、V5 が現行である。
V4 から V5 では Union の validity ビットマップが廃止された、など非互換点がコメントに列挙される。

[`format/Schema.fbs` L31-L51](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/format/Schema.fbs#L31-L51)

```text
enum MetadataVersion:short {
  /// 0.1.0 (October 2016).
  V1,
  // ... (中略) ...
  /// >= 1.0.0 (July 2020). Backwards compatible with V4 (V5 readers can read V4
  /// metadata and IPC messages). Implementations are recommended to provide a
  /// V4 compatibility mode with V5 format changes disabled.
  ///
  /// Incompatible changes between V4 and V5:
  /// - Union buffer layout has changed. In V5, Unions don't have a validity
  ///   bitmap buffer.
  V5,
}
```

## pyarrow の Message ラッパー

`pyarrow` の `Message` クラスは、デシリアライズ済みの IPC メッセージをメタデータバッファと本体バッファに分けて保持する。

[`python/pyarrow/ipc.pxi` L383-L413](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.pxi#L383-L413)

```python
cdef class Message(_Weakrefable):
    """
    Container for an Arrow IPC message with metadata and optional body
    """
    // ... (中略) ...
    @property
    def metadata(self):
        return pyarrow_wrap_buffer(self.message.get().metadata())

    @property
    def metadata_version(self):
        return _wrap_metadata_version(self.message.get().metadata_version())

    @property
    def body(self):
        cdef shared_ptr[CBuffer] body = self.message.get().body()
        if body.get() == NULL:
            return None
        else:
            return pyarrow_wrap_buffer(body)
```

`get_record_batch_size` は、メタデータとパディングを含むシリアライズ後サイズを見積もる API である。

[`python/pyarrow/ipc.pxi` L1312-L1324](https://github.com/apache/arrow/blob/apache-arrow-25.0.0/python/pyarrow/ipc.pxi#L1312-L1324)

```python
def get_record_batch_size(RecordBatch batch):
    """
    Return total size of serialized RecordBatch including metadata and padding.

    Parameters
    ----------
    batch : RecordBatch
        The recordbatch for which we want to know the size.
    """
    cdef int64_t size
    with nogil:
        check_status(GetRecordBatchSize(deref(batch.batch), &size))
    return size
```

## まとめ

IPC の最小単位は封入された `Message` であり、FlatBuffers メタデータと 8 バイト整列された本体からなる。
`RecordBatch` は `FieldNode` と `Buffer` の並列でネスト列を平坦化し、本体スライスへのポインタだけで配列を再構成できる。
`null_count == 0` なら validity バッファを省略でき、圧縮時はバッファごとに非圧縮長ヘッダで選択的圧縮ができる。
スキーマと `KeyValue` メタデータが型契約を運び、第8章ではこのメッセージのストリーム順序を読む。

## 関連する章

- 第3章 [型システムとスキーマ](../part01-types/03-type-system.md)：`Field` と `Schema`
- 第6章 [ディクショナリエンコーディング](../part01-types/06-dictionary-encoding.md)：`DictionaryBatch`
- 第8章 [ストリーミング IPC](08-streaming-ipc.md)：メッセージ列と EOS
- 第9章 [ファイル形式](09-file-format.md)：フッタとランダムアクセス
