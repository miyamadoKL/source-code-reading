# 第5章 WAL

> 本章で読むソース
>
> - [`server/storage/wal/wal.go`](https://github.com/etcd-io/etcd/blob/v3.6.12/server/storage/wal/wal.go)
> - [`server/storage/wal/encoder.go`](https://github.com/etcd-io/etcd/blob/v3.6.12/server/storage/wal/encoder.go)

## この章の狙い

本章では **WAL** が Raft の HardState、entry、snapshot marker をどの順序で保存するかを読む。
クラッシュ後にどこから再生できるかを、segment、CRC、fsync の観点で整理する。

## 前提

WAL は MVCC の key value ではなく、Raft log と HardState の永続化である。
backend の consistent index と WAL の commit index は、復旧時に突き合わせて使われる。

## 全体の流れ

```mermaid
sequenceDiagram
    participant raft as raftNode Ready
    participant wal as WAL
    participant file as WAL segment
    raft->>wal: Save HardState and entries
    wal->>file: encode records with CRC
    wal->>file: sync when MustSync
    raft->>wal: SaveSnapshot
    wal->>file: snapshot record and sync
```

## WAL の保持状態

`WAL` は現在の HardState、読み取り開始 snapshot、encoder、locked files、file pipeline を持つ。
ファイル名が増加する複数 segment を前提にして、最後に保存した entry index を `enti` として追跡する。

`WAL` は metadata、HardState、decoder、encoder、locked files を持つ。

[server/storage/wal/wal.go L72-L100](https://github.com/etcd-io/etcd/blob/v3.6.12/server/storage/wal/wal.go#L72-L100)

```go
type WAL struct {
	lg *zap.Logger

	dir string // the living directory of the underlay files

	// dirFile is a fd for the wal directory for syncing on Rename
	dirFile *os.File

	metadata []byte           // metadata recorded at the head of each WAL
	state    raftpb.HardState // hardstate recorded at the head of WAL

	start     walpb.Snapshot // snapshot to start reading
	decoder   Decoder        // decoder to Decode records
	readClose func() error   // closer for Decode reader

	unsafeNoSync bool // if set, do not fsync

	mu      sync.Mutex
	enti    uint64   // index of the last entry saved to the wal
	encoder *encoder // encoder to encode records

	locks []*fileutil.LockedFile // the locked files the WAL holds (the name is increasing)
	fp    *filePipeline
}

// Create creates a WAL ready for appending records. The given metadata is
// recorded at the head of each WAL file, and can be retrieved with ReadAll
// after the file is Open.
func Create(lg *zap.Logger, dirpath string, metadata []byte) (*WAL, error) {
```

## entry と HardState をまとめて保存する

`Save` は空の HardState と entry を短絡し、必要な場合だけ `MustSync` の判定に従って fsync する。
segment サイズを超えた場合は `cut` に進み、長い WAL を一定サイズのファイルに分割する。

`Save` は entry、HardState、sync、segment cut を一つの排他区間で扱う。

[server/storage/wal/wal.go L955-L991](https://github.com/etcd-io/etcd/blob/v3.6.12/server/storage/wal/wal.go#L955-L991)

```go
func (w *WAL) Save(st raftpb.HardState, ents []raftpb.Entry) error {
	w.mu.Lock()
	defer w.mu.Unlock()

	// short cut, do not call sync
	if raft.IsEmptyHardState(st) && len(ents) == 0 {
		return nil
	}

	mustSync := raft.MustSync(st, w.state, len(ents))

	// TODO(xiangli): no more reference operator
	for i := range ents {
		if err := w.saveEntry(&ents[i]); err != nil {
			return err
		}
	}
	if err := w.saveState(&st); err != nil {
		return err
	}

	curOff, err := w.tail().Seek(0, io.SeekCurrent)
	if err != nil {
		return err
	}
	if curOff < SegmentSizeBytes {
		if mustSync {
			// gofail: var walBeforeSync struct{}
			err = w.sync()
			// gofail: var walAfterSync struct{}
			return err
		}
		return nil
	}

	return w.cut()
}
```

`encoder` は CRC を更新し、1 MiB buffer を使って record を marshal する。

[server/storage/wal/encoder.go L44-L90](https://github.com/etcd-io/etcd/blob/v3.6.12/server/storage/wal/encoder.go#L44-L90)

```go
func newEncoder(w io.Writer, prevCrc uint32, pageOffset int) *encoder {
	return &encoder{
		bw:  ioutil.NewPageWriter(w, walPageBytes, pageOffset),
		crc: crc.New(prevCrc, crcTable),
		// 1MB buffer
		buf:       make([]byte, 1024*1024),
		uint64buf: make([]byte, 8),
	}
}

// newFileEncoder creates a new encoder with current file offset for the page writer.
func newFileEncoder(f *os.File, prevCrc uint32) (*encoder, error) {
	offset, err := f.Seek(0, io.SeekCurrent)
	if err != nil {
		return nil, err
	}
	return newEncoder(f, prevCrc, int(offset)), nil
}

func (e *encoder) encode(rec *walpb.Record) error {
	e.mu.Lock()
	defer e.mu.Unlock()

	e.crc.Write(rec.Data)
	rec.Crc = e.crc.Sum32()
	var (
		data []byte
		err  error
		n    int
	)

	if rec.Size() > len(e.buf) {
		data, err = rec.Marshal()
		if err != nil {
			return err
		}
	} else {
		n, err = rec.MarshalTo(e.buf)
		if err != nil {
			return err
		}
		data = e.buf[:n]
	}

	data, lenField := prepareDataWithPadding(data)

	return write(e.bw, e.uint64buf, data, lenField)
```

## 最適化の工夫

`Save` は `raft.IsEmptyHardState` かつ entry なしの呼び出しを即時 return し、心拍中心の Ready 処理で不要な sync 判定を避ける。
`encoder` は通常の record を再利用 buffer に marshal し、大きな record のときだけ別 slice を作るため、WAL 書き込み時の割り当てを抑える。

## まとめ

- WAL は Raft の順序と耐久性を支え、backend の key value とは別の復旧軸を持つ。
- CRC と segment cut と必要時 sync が、破損検出と書き込み負荷の釣り合いを取る。

## 関連する章

- [backend と bbolt](03-backend-bbolt.md)
- [スナップショット](../part02-mvcc/09-snapshot.md)
- [etcdserver の Raft ループ](../part03-raft/10-etcdserver-raft.md)
