# AI 向け指示書：M-VAVE FM-1 に Felucca を書き込む

> **使う人へ（人間向け）**
> Claude Code・Codex CLI・Gemini CLI など、**パソコンでコマンドを実行できる AI** に、次の1行を送ってください。
>
> ```
> https://github.com/bey-jp/fm1-felucca-pi/blob/main/AI_INSTRUCTIONS.md を読んで、その手順どおりに私の FM-1 に Felucca を入れてください。
> ```
>
> あなたがやることは、FM-1 を USB でつなぐこと、AI に聞かれたことに答えること、書き込み前の最終確認に「はい」と答えることだけです。
> ブラウザのチャット（コマンドを実行できない AI）では使えません。
> ファームウェアの書き換えは自己責任です。Felucca は M-VAVE 公式のものではありません。

---

ここから先は、この指示書を読んでいる AI エージェント向けです。

## あなたの役割

ユーザーは初心者かもしれません。あなたがすべてのコマンドを実行してください。ユーザーに頼むのは次のことだけにします。

- FM-1 を USB ケーブルで抜き差しする・画面を見る・ボタンを押す
- パスワードの入力や管理者権限の承認（sudo、Windows の UAC など）
- **書き込み前の最終確認**（下の「止まって確認する場所」）

あなたの環境が、ダウンロードしたプログラムの実行を許していない場合（安全モードなど）は、無理に回避せず、実行するコマンドを1行ずつユーザーに示して、ユーザーに実行してもらってください。そのときは、出力をすべて貼ってもらいます。

説明はやさしい言葉で、ユーザーの言語で行ってください。専門用語を使うときは一言で説明します。

## 止まって確認する場所（必ず守る）

1. **書き込みの直前**：書き込むファイル名、バージョン、FM-1 の現在の識別名を見せ、「自作の音色は消える可能性があります。書き込んでよいですか？」とはっきり聞きます。「はい」と言われるまで書き込まないでください。
2. **想定と違う出力が出たとき**：推測で先に進まず、出力をそのまま見せて止まります。
3. **書き込み中は何もしない**：書き込み中に FM-1 の USB を抜かせたり、ほかの MIDI ソフトを起動したりしないでください。

## 手順

### 0. 環境を調べる

- OS（Linux / Raspberry Pi、macOS、Windows）と、Python 3 が入っているか（`python3 --version`、Windows は `py -3 --version`）を調べます。
- Python 3.11 以上を推奨します（下で使う `-P` オプションのため）。古い場合は「手順 2 の注意」を見てください。
- Python がない場合は入れます。Windows は `winget install Python.Python.3.12`、macOS は `brew install python` か python.org。Raspberry Pi OS には最初から入っています。

### 1. 作業フォルダとファイル

専用の空フォルダを作り、そこで作業します（例 `~/fm1-felucca`）。

1. Felucca の最新の安定版を調べます。
   `https://api.github.com/repos/hugelton/Felucca/releases/latest` を取得し、`tag_name` と、`assets` の中の `felucca-<版>.fwsc` を確認します。
   プレビュー版・実験版（prerelease）は使いません。
2. `.fwsc` と、インストーラ `https://raw.githubusercontent.com/hugelton/Felucca/main/tools/fm1_install.py` をダウンロードします。
3. `.fwsc` の SHA-256 を計算し、公表値と比べます。公表値は、API の asset の `digest`（`sha256:...`）か、リリースノートに書かれています。
   一致しなければ止まって、ユーザーに伝えます。
   参考：1.8.3 は `49af224db01eb1132b1f80b68788b62d949a8d2dae3b0ce10838c50bd43e34ec`。
4. `fm1_install.py` を開いて、先頭の説明と `main()` に目を通します。
   USB MIDI の SysEx で通信するだけのプログラムであることを確かめてください。

### 2. 必要なライブラリ

```
pip install mido python-rtmidi
```

- Raspberry Pi OS / Debian で `externally-managed-environment` と出たら、作業フォルダに venv を作ってそこに入れます（`python3 -m venv .venv` → `.venv/bin/pip install mido python-rtmidi`）。または `pip install --user --break-system-packages mido` と `sudo apt install python3-rtmidi` を使います。
- 確認：`python3 -P -c "import mido; print(mido.get_input_names())"`
- **注意**：`python3 -I` は使わないでください。`-I` を付けると `~/.local` のライブラリが読み込まれず、mido が見つからずに失敗します。`-P` が使えない古い Python では、`-P` を付けずに、作業フォルダ（`.fwsc` と `fm1_install.py` だけがある場所）で実行します。

### 3. FM-1 をつなぐ

ユーザーに、FM-1 の電源を入れて、**データ通信できる USB ケーブル**でパソコンにつないでもらいます（充電専用ケーブルは不可）。
DAW やシンセのエディタなど、MIDI を使うソフトはすべて閉じてもらいます。

確認：

- Linux：`lsusb` に `4c4a:` で始まる Jieli の機器が出ること。`aconnect -l` に `USB Composite Device`（Felucca 導入後は `Felucca`）が出ること。
- 全 OS 共通：手順 2 の `mido.get_input_names()` に、`USB Composite Device` か `Felucca` を含む名前が出ること。

出てこなければ、ケーブルを替える、別の USB ポートに挿す、FM-1 を再起動する、の順で試してもらいます。

### 4. USB が安定しているか確かめる（Linux、特に Home Assistant の機械では必須）

**Home Assistant OS / Supervised が動いている機械**では、HA の音声コンテナ `hassio_audio` が FM-1 の USB オーディオを開きっぱなしにします。その結果、FM-1 が数分〜25分おきに USB から切断されることが分かっています。

- 確認：`docker ps` に `hassio_audio` があるか。あれば次を実行します。
  ```
  docker exec hassio_audio pactl list cards short
  docker exec hassio_audio pactl set-card-profile <Jieli か Felucca を含むカード名> off
  ```
  このリポジトリの `scripts/fm1_audio_off.sh` でも同じことができます。MIDI はそのまま使えます。FM-1 を挿し直すと元に戻るので、書き込みの直前に行ってください。
- そのあと、10〜20分ほど、切断が起きないか見張ります（`scripts/fm1_watch_usb.sh 20`、または `dmesg` に `USB disconnect` が出ないか）。その間、ユーザーには FM-1 に触らないでもらいます。
- 切断が起きる場合は書き込まないでください。原因を探すか、別のパソコン（Windows / Mac）で書き込むことを提案します。
- **USB ハブごと抜かせない**でください。同じハブに Zigbee ドングルなどがあると、Home Assistant が止まります。

Windows / Mac でも、切断の兆候があれば（デバイスが消えたり出たりする）、書き込まないでください。

### 5. 識別情報を読む（書き込みはしない）

```
python3 -P fm1_install.py --info
```

Windows では `py -3 -P fm1_install.py --info` です。

- 期待する出力：`FM-1_0xx  [running]  port: ...`。公式ファームは `FM-1_014` などと表示されます。
- `[update loader (update not finished)]` と出た場合は、前回の書き込みが途中で止まっています。手順 6 を実行すると完了します。
- 見つからない（終了コード 3）場合は手順 3 に戻ります。
- ポートは自動で探します。FM-1 らしい名前（fm-1 / felucca / composite など）のポートだけを調べ、ほかの機器には触りません。
  うまくいかないときは、`--port "USB Composite"` か `--port Felucca` で指定します。

### 6. 書き込み（ユーザーの「はい」を得てから）

「止まって確認する場所」の 1 の確認をしてから、実行します。

```
python3 -P fm1_install.py felucca-<版>.fwsc
```

- 途中で `Install? ... [y/N]` と聞かれます。あなたが対話入力できない環境では、ユーザーの「はい」を得たうえで `--yes` を付けて実行してください。
- 数分かかります。進み具合が `writing NN%` と表示されます。
- 成功すると、最後に `done: the FM-1 runs FM-1_9xx` と表示され、終了コードは 0 になります。
- **途中で切れた・エラーになった場合**は、同じコマンドをもう一度実行します（書き込みを最後まで終わらせる仕組みがあります）。
- 終了コードの意味：1 キャンセル・その他、2 引数・ファイル不正、3 FM-1 が見つからない、4 接続が切れた、5 タイムアウト、6 機種違い。

### 7. 書き込み後の確認

- `--info` で、識別名が `FM-1_9xx` に変わったことを確認します。
- FM-1 の画面に Felucca が表示され、鍵盤で音が出ることをユーザーに確かめてもらいます。
- Home Assistant の機械では、再接続で音声の設定が元に戻っています。FM-1 をつないだままにするなら、手順 4 の off をもう一度実行します（恒久的な対策は、ユーザーと相談して決めてください）。
- 使い方は Felucca の wiki（https://github.com/hugelton/Felucca/wiki ）を案内します。

## 困ったとき

| 症状 | 対処 |
|---|---|
| 画面が真っ黒で起動しない | パソコンに `WL80UBOOT`（USB ID 4C4A:8057）が出ていれば、チップ内蔵のブートモードです。ケーブルを替え、ほかの MIDI ソフトを閉じて、手順 6 をもう一度実行するか、ブラウザ版インストーラ（Chrome / Edge で https://hugelton.github.io/Felucca ）を使います。それでもだめなら [FM-1-Transporter](https://github.com/kurogedelic/FM-1-transporter) を案内します（XIAO RP2040 と配線が必要） |
| 公式ファームに戻したい | 一番簡単なのは、ブラウザ版インストーラの「Return to official V15」です（作業データを先にバックアップします）。ターミナルで戻す場合は、M-VAVE が配布している無改変の `FM-1.fwsc`（V15 / V16）を用意して `python3 -P fm1_install.py FM-1.fwsc` を実行します（スクリプトが公式ファイルの SHA-256 を照合します）。M-VAVE 公式アップデータでも戻せますが、Felucca のプロジェクトは消えます |
| `No module named 'mido'` | `-I` を付けていないか確認します。手順 2 をやり直します |
| 新しいフラッシュチップ（UC25HQ80）の個体 | Felucca 1.8.2 以降が必要です（最新版を使えば問題ありません） |

## 自作音色について（書き込み前にユーザーへ伝える）

公式ファームの自作音色を USB で書き出す方法は、知られていません（DX7 形式のダンプ要求にも応答しません）。
消えて困る音色は、書き込みの前に、画面の値を写真や動画で残してもらってください。

## 参考

- Felucca：https://github.com/hugelton/Felucca （wiki の Installation / Troubleshooting）
- このリポジトリの README：作業記録と、Home Assistant での USB 切断の詳細
