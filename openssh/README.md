# OpenSSH ソースコードリーディング

OpenSSH（[openssh/openssh-portable](https://github.com/openssh/openssh-portable)）のソースコードを読み解き、SSH プロトコルの実装が「何のために、どういう処理を行うか」と「高速化、セキュリティの工夫」を、ソースコードを引用しながら日本語で解説するドキュメントである。

- **対象バージョン**：V_10_3_P1（コード引用はすべて [`V_10_3_P1` タグ](https://github.com/openssh/openssh-portable/tree/V_10_3_P1)に固定）
- **ライセンス**：BSD 系（引用の方針はリポジトリルートの[引用とライセンス](../README.md#引用とライセンス)を参照）。
- **想定読者**：C 言語とネットワークプロトコルの基礎がある中級エンジニア
- **読み方**：トランスポート層から認証、セッション、セキュリティ基盤へと積み上がる構成で、第0部から順に読むことを想定する。

コード引用は、本文中の `[path L開始-L終了](https://github.com/openssh/openssh-portable/blob/V_10_3_P1/...)` 形式のリンクから GitHub 上の該当箇所を直接参照できる。

## 第0部　概観

1. [OpenSSH の全体像](part00-overview/01-openssh-overview.md)

## 第1部　トランスポート層

2. [パケットプロトコル](part01-transport/02-packet-protocol.md)
3. [鍵交換](part01-transport/03-key-exchange.md)
4. [暗号と MAC の抽象化](part01-transport/04-cipher-and-mac.md)

## 第2部　認証

5. [認証フレームワーク](part02-auth/05-auth-framework.md)
6. [公開鍵認証](part02-auth/06-public-key-auth.md)
7. [パスワード・KBDINT・GSSAPI 認証](part02-auth/07-password-kbdint-gssapi.md)

## 第3部　セッションとチャネル

8. [チャネルの多重化](part03-session/08-channels.md)
9. [クライアント接続](part03-session/09-client-connection.md)
10. [サーバーセッション](part03-session/10-server-session.md)

## 第4部　セキュリティ基盤

11. [権限分離](part04-security/11-privilege-separation.md)
12. [鍵管理](part04-security/12-key-management.md)

---

> 全12章を公開済み。
> コード引用はすべて [`V_10_3_P1`](https://github.com/openssh/openssh-portable/tree/V_10_3_P1) タグに固定している。
