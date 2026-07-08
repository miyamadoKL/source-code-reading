# etcd ソースコードリーディング

etcd（[etcd-io/etcd](https://github.com/etcd-io/etcd)）のソースコードを読み解き、分散キーバリューストアを支える起動、永続化、MVCC、Raft、API、client、運用機能を日本語で解説するドキュメントである。

- **対象バージョン**：v3.6.12（コード引用はすべて [`v3.6.12` タグ](https://github.com/etcd-io/etcd/tree/v3.6.12)に固定）
- **想定読者**：Go、gRPC、Raft、永続化の基礎があり、etcd の内部構造を実装から確認したい中級エンジニア。
- **読み方**：第0部から順に読むと、起動、保存、合意、API、client、運用機能へ段階的に積み上がる。

コード引用は、ローカルの v3.6.12 ソースで行番号と内容を照合したうえで、GitHub の固定タグへのリンクとして示す。

## 第0部　概観

1. [etcd の全体像](part00-overview/01-etcd-overview.md)
2. [embed と起動処理](part00-overview/02-embed-and-startup.md)

## 第1部　ストレージ

3. [backend と bbolt](part01-storage/03-backend-bbolt.md)
4. [schema と keyspace](part01-storage/04-schema-keyspace.md)
5. [WAL](part01-storage/05-wal.md)
6. [MVCC の revision index](part01-storage/06-mvcc-revision-index.md)

## 第2部　MVCC

7. [MVCC の read と write](part02-mvcc/07-mvcc-read-write.md)
8. [コンパクション](part02-mvcc/08-compaction.md)
9. [スナップショット](part02-mvcc/09-snapshot.md)

## 第3部　Raft

10. [etcdserver の Raft ループ](part03-raft/10-etcdserver-raft.md)
11. [apply pipeline](part03-raft/11-apply-pipeline.md)
12. [cluster bootstrap](part03-raft/12-cluster-bootstrap.md)

## 第4部　トランザクションとリースと watch

13. [transaction](part04-txn-lease-watch/13-transaction.md)
14. [リース](part04-txn-lease-watch/14-lease.md)
15. [watch](part04-txn-lease-watch/15-watch.md)

## 第5部　API と認証

16. [gRPC v3 server](part05-api-auth/16-grpc-v3-server.md)
17. [KV Range](part05-api-auth/17-kv-range.md)
18. [auth と RBAC](part05-api-auth/18-auth-rbac.md)

## 第6部　クライアント

19. [clientv3](part06-client/19-clientv3.md)
20. [etcdctl](part06-client/20-etcdctl.md)
21. [gRPC proxy](part06-client/21-grpcproxy.md)

## 第7部　運用

22. [リニアライザブル read](part07-ops/22-linearizable-read.md)
23. [corruption check](part07-ops/23-corruption-check.md)
24. [feature gate と version](part07-ops/24-feature-version.md)

---

> 全24章を公開済み。
> コード引用は `etcd-io/etcd` の `v3.6.12` タグに固定している。
