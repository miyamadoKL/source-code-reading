# systemd ソースコードリーディング

systemd（[systemd/systemd](https://github.com/systemd/systemd)）のソースコードを読み解き、Linux の init システムとサービス管理が「何のために、どういう処理を行うか」と「高速化・最適化の工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：261.1（コード引用はすべて [`v261.1` タグ](https://github.com/systemd/systemd/tree/v261.1)に固定）
- **ライセンス**：LGPL-2.1-or-later で、udev の一部は GPL-2.0-or-later（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：C と Linux システムプログラミングの基礎がある中級エンジニア
- **読み方**：概観と共通基盤から PID 1 コア、リソース制御、周辺デーモンへと積み上がる構成で、第0部から順に読むことを想定する。

コード引用は、`v261.1` タグに固定した GitHub リンクと、実ソースから取ったコードブロックの2点セットで示す。

## 第0部　概観

1. [systemd の全体像とプロセスツリー](part00-overview/01-systemd-overview.md)
2. [ユニットファイルと依存関係モデル](part00-overview/02-unit-files-and-dependencies.md)

## 第1部　共通基盤

3. [fundamental と basic のメモリ管理とデータ構造](part01-foundation/03-fundamental-and-basic.md)
4. [sd-event イベントループ](part01-foundation/04-sd-event.md)
5. [sd-bus と D-Bus 連携](part01-foundation/05-sd-bus.md)

## 第2部　PID 1 コア

6. [Manager とメインループ](part02-core/06-manager.md)
7. [Unit 抽象化と UnitType](part02-core/07-unit.md)
8. [Job とトランザクション](part02-core/08-job.md)
9. [Service ユニットの起動シーケンス](part02-core/09-service.md)
10. [ソケットアクティベーション](part02-core/10-socket-activation.md)
11. [Timer、Path、Target ユニット](part02-core/11-timer-path-target.md)

## 第3部　リソース制御

12. [cgroup v2 統合](part03-resources/12-cgroup.md)
13. [BPF によるリソース制約](part03-resources/13-bpf-restrictions.md)

## 第4部　journald

14. [ジャーナルファイルフォーマット](part04-journal/14-journal-format.md)
15. [journald の書き込みとローテーション](part04-journal/15-journald.md)

## 第5部　udev

16. [udev デーモンのイベント処理](part05-udev/16-udev-daemon.md)
17. [hwdb とデバイス列挙](part05-udev/17-hwdb-and-enumeration.md)

## 第6部　logind

18. [logind のセッション管理](part06-logind/18-logind.md)
19. [sd-login API と PAM 連携](part06-logind/19-sd-login.md)

## 第7部　ネットワーク

20. [networkd のリンク管理](part07-network/20-networkd.md)
21. [resolved のスタブリゾルバ](part07-network/21-resolved.md)

## 第8部　周辺基盤

22. [ユニットジェネレータ](part08-periphery/22-unit-generators.md)
23. [tmpfiles と sysusers](part08-periphery/23-tmpfiles-and-sysusers.md)
24. [homed と Varlink](part08-periphery/24-homed-and-varlink.md)

---

> 全9部24章を公開済み。
> コード引用はすべて [`v261.1`](https://github.com/systemd/systemd/tree/v261.1) タグに固定している。
> portable、factory-reset、vm 等のニッチ機能と言語バインディングは本書の対象外である。
