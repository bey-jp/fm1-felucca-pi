# M-VAVE FM-1 に Felucca（カスタムファームウェア）を Raspberry Pi から書き込む

FM シンセ **M-VAVE FM-1** に、オープンソースのカスタムファームウェア **[Felucca](https://github.com/hugelton/Felucca)** を、
ブラウザを使わず **Raspberry Pi 5（Home Assistant が動いている Pi）からターミナルで**書き込んだ記録です。
途中でハマった「FM-1 が数分おきに USB 切断する」問題の原因（Home Assistant の音声コンテナ）と対策も載せています。

Flashing the open-source **Felucca** firmware onto an **M-VAVE FM-1** from a Raspberry Pi 5 running Home Assistant,
plus the fix for random USB disconnects caused by Home Assistant's audio container. (English summary at the bottom.)

> ⚠️ ファームウェアの書き換えは自己責任です。Felucca は M-VAVE 公式のものではありません。

> 🤖 **AI にやってもらう**: Claude Code などコマンドを実行できる AI に
> 「https://github.com/bey-jp/fm1-felucca-pi/blob/main/AI_INSTRUCTIONS.md を読んで、その手順どおりに私の FM-1 に Felucca を入れてください」
> と頼めば、つなぐ・確認に答える以外は AI がやります → [AI_INSTRUCTIONS.md](AI_INSTRUCTIONS.md)
> ChatGPT・Gemini などのチャットでも、コマンドを1つずつ案内してもらう形で使えます（実行と結果の貼り付けは自分で）。

## FM-1 のカスタムファームウェア（2026-11 時点）

| 名前 | 種類 | 価格 | 内容 |
|---|---|---|---|
| 公式 V15 / V16 | M-VAVE 公式（クローズド） | 無料 | 出荷時のファームの更新版 |
| [FM1 Open](https://github.com/m-vave/fm1_open) | M-VAVE 公式のオープンソース版 | 無料 | 8 トラックシーケンサー、FM＋サンプル＋303/808/PSG など、ブラウザの Workbench |
| **[Felucca](https://github.com/hugelton/Felucca)** | 有志のオープンソース（GPL-3.0） | 無料 | 13 エンジン、4 トラック×64 ステップ、パラメータロック、アルペジエーター、LFO、Web エディタ |
| Baud Girl FM-1+VA | 有志 | 無料 | VA エンジン＋マルチモードフィルタ、303 風シーケンサー |
| Groove OS | 有志（クローズド） | $29 | 8 トラックのグルーヴボックス、Perform モード |
| Hortator / JIANT FM / GR!MM | Felucca 派生など | 無料 | ドラムマシン化など（ベータ） |

Felucca を選んだ理由: 無料・オープンソース・更新が活発、インストーラに「公式 V15 に戻す」ボタンがあり、文鎮化したときの復旧手順も wiki にある。

## ハードウェアのメモ

- SoC: JieLi AC791N / WL82（Dexed 由来の 6 オペレーター FM）
- USB: クラスコンプライアントの USB MIDI 入出力 + USB オーディオ（2ch / 24bit / 44.1kHz）。Linux はドライバ追加不要
- `lsusb`: 公式ファームは `4c4a:c755 Jieli Technology USB Composite Device`、Felucca では `1209:0001`（製品名 `Felucca`、ALSA 名も `Felucca`）。Felucca は USB シリアル（ttyACM）も出す
- Bluetooth は載っているが、Felucca は BLE MIDI 非対応（今後も対応しない方針）
- Wi-Fi なし

## 書き込み手順（Raspberry Pi / Linux）

Felucca にはブラウザ版インストーラ（Chrome / Edge、https://hugelton.github.io/Felucca ）のほかに、
同じ処理を **USB MIDI の SysEx** で行うターミナル版 `tools/fm1_install.py` があります。これなら Pi のターミナルだけで書き込めます。

### 1. 用意

```sh
pip install mido python-rtmidi      # Raspberry Pi OS なら python3-rtmidi は apt でも可
mkdir -p ~/fm1 && cd ~/fm1
curl -LO https://raw.githubusercontent.com/hugelton/Felucca/main/tools/fm1_install.py
curl -LO https://github.com/hugelton/Felucca/releases/download/v1.8.3/felucca-1.8.3.fwsc
sha256sum felucca-1.8.3.fwsc
# 49af224db01eb1132b1f80b68788b62d949a8d2dae3b0ce10838c50bd43e34ec（1.8.3 の公表値）
```

最新版は [Releases](https://github.com/hugelton/Felucca/releases) で確認してください。

### 2. USB 切断が起きないか確認（重要）

書き込み中に USB が切れると危険です。**Home Assistant OS / Supervised の Pi につないだ場合**、
HA の音声コンテナ `hassio_audio`（PulseAudio）が FM-1 の音声を再生・録音とも開きっぱなしにして、
FM-1 が **数分〜25 分おきに USB 切断・再接続**を繰り返しました（ハブ経由でも直挿しでも、ケーブルを替えても発生）。

```sh
sh scripts/fm1_audio_off.sh      # FM-1 の音声プロファイルを off（MIDI はそのまま使える）
sh scripts/fm1_watch_usb.sh 20   # 20 分見張って切断がないことを確認
```

音声を止めたら 20 分間一度も切れなくなりました。この設定は FM-1 を挿し直すと元に戻るので、書き込み直前に実行します。

**自動で毎回オフにする（つなぎっぱなしにする場合）**: FM-1 のサウンドカードが現れたら自動で off にする udev ルールと systemd サービスです。

```sh
sudo cp scripts/fm1_audio_off.sh /usr/local/bin/
sudo cp system/99-fm1-audio-off.rules /etc/udev/rules.d/
sudo cp system/fm1-audio-off.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo udevadm control --reload
```

Felucca を入れると USB ID が `4c4a:c755`（Jieli）から `1209:0001`（製品名 `Felucca`）に変わるので、ルールは両方に対応しています。

### 3. 識別情報の確認（書き込みはしない）

```sh
python3 -P fm1_install.py --info --port "USB Composite"
# FM-1_014  [running]  port: USB Composite Device:USB Composite Device MIDI 1 28:0
```

### 4. 書き込み

```sh
python3 -P fm1_install.py felucca-1.8.3.fwsc --port "USB Composite"
# package: FM-1_918  (felucca-1.8.3.fwsc)
# device:  FM-1_014  (...)
# Install? Do not unplug the FM-1 while writing. [y/N] y
# writing 100%
# restarting
# done: the FM-1 runs FM-1_918
```

数分で終わります。途中で切れた場合は、同じコマンドをもう一度実行すると書き込みを最後まで終わらせます。

### ハマりどころ

- **`python3 -I` は使わない**: `-I` はユーザー領域（`~/.local`）を読まないので、`pip install --user` した mido が見つからずに失敗する。`-P`（スクリプトのフォルダを import パスに入れない）なら OK
- **ターミナルで先頭に `!` を付けない**: bash の `!` は終了コードの反転。`! cd … && python3 …` だと python が実行されずに終わる
- **USB ハブごと抜かない**: 同じハブに Zigbee ドングルなどを挿していると、抜き差しで HA の Zigbee（Zigbee2MQTT）が止まる。戻しても `can't set config #1, error -32` で使えない状態になることがある → `echo 1 | sudo tee /sys/bus/usb/devices/<パス>/bConfigurationValue` で復旧し、Zigbee2MQTT を再起動した

## 公式ファームに戻す

- ブラウザ版インストーラの「Return to official V15」（先に作業データをバックアップしてくれる）
- または M-VAVE 公式アップデータ（Felucca のプロジェクトと FM6 ボイスバンクは消える）
- ターミナル版でも、M-VAVE 配布の無改変 `FM-1.fwsc`（V15 / V16）なら `python3 -P fm1_install.py FM-1.fwsc` で戻せる
- 書き込み失敗で画面が真っ黒: PC に `WL80UBOOT`（4C4A:8057）が出ればチップ内蔵のブートモード。インストーラを再実行。だめなら [FM-1-Transporter](https://github.com/kurogedelic/FM-1-transporter)（XIAO RP2040 で USB 線から直接書く）

### 自作音色のバックアップについて

公式ファームの自作音色を USB から書き出す方法は見つかりませんでした（DX7 形式のダンプ要求 `F0 43 20 09 F7` にも無応答）。
Felucca インストーラのバックアップは Felucca 稼働中のデータ専用です。消えて困る音色は、画面の写真や動画で値を控えておきましょう。

## MIDI 出力の実測（Home Assistant 連携の下調べ）

`aseqdump` で FM-1 から USB MIDI に出てくるものを調べました。

| | 公式 (FM-1_014) | Felucca 1.8.3 |
|---|---|---|
| 鍵盤 | Ch1 のノートオン／オフ（ベロシティ 90 固定） | **選択中トラックのチャンネル**でノートオン／オフ（ベロシティ 100） |
| Knob 1〜4 | 何も出ない | 何も出ない（CC は受信専用） |
| ボタン | 何も出ない | 何も出ない |

Pi → FM-1 の方向（ノートを送って鳴らす）はどちらでも使えます。
FM-1 を HA の操作盤にするなら鍵盤を使い、Felucca なら「トラック（チャンネル）× 鍵盤」で多くのボタンに割り当てられます。

```sh
aconnect -l                                         # FM-1 のポート番号（例 28:0）
stdbuf -oL aseqdump -p 28:0                         # 受信を表示（パイプするときは stdbuf が必要）
amidi -p hw:3,0,0 -S '90 3C 7F'; amidi -p hw:3,0,0 -S '80 3C 00'   # ド を鳴らす
```

## Home Assistant から FM-1 を鳴らす（雨のメロディ）

雨センサーが反応したら、FM-1 で「雨のメロディ」を鳴らしています。鳴っている音に合わせて鍵盤の LED も光ります（Felucca は MIDI IN のノートで LED が光る）。

```
雨センサー ──▶ HA 自動化 ──rest_command──▶ fm1_server.py（127.0.0.1:5002）──USB MIDI──▶ FM-1
```

| ファイル | 内容 |
|---|---|
| `fm1_play.py` | メロディを FM-1 に送る。`python3 fm1_play.py rain`、`--gate` / `--bpm` で長さ・テンポを変更、`--export` で .mid |
| `fm1_server.py` | HA から呼ぶ HTTP サーバー。`POST /play {"melody":"rain"}`（202 開始 / 409 再生中 / 503 FM-1 なし）、`GET /status` |
| `melodies/melodies.json` | メロディ（`[音名, 拍, 強さ]` の列）。rain（雨・サラサラ版）と morning（朝のアラーム） |
| `melodies/*.wav` | 試聴用（簡易 FM 合成。実機とは音色が違う）。`render_wav.py` で作り直せる |
| `system/fm1-server.service` | systemd 用（パスとユーザーは自分の環境に合わせる） |
| `ha/ha_example.yaml` | HA の rest_command と自動化の例 |

```sh
sudo mkdir -p /opt/fm1-felucca-pi && sudo cp -r fm1_play.py fm1_server.py melodies /opt/fm1-felucca-pi/
sudo cp system/fm1-server.service /etc/systemd/system/   # User= と パスを確認
sudo systemctl daemon-reload && sudo systemctl enable --now fm1-server
curl http://127.0.0.1:5002/status
```

- LED: 1音が短すぎる（0.1 秒以下）と LED はちらつく程度にしか見えない。rain は 60bpm・gate 0.95 にした
- 雨のメロディと朝のアラームはオリジナル曲です（このリポジトリの LICENSE に従って使えます）

## English summary

- Felucca ships a terminal installer (`tools/fm1_install.py`) that flashes over USB-MIDI SysEx, so no browser is needed. It worked from a Raspberry Pi 5: `python3 -P fm1_install.py felucca-1.8.3.fwsc --port "USB Composite"`.
- On Home Assistant OS/Supervised, the `hassio_audio` PulseAudio container keeps the FM-1's USB audio streams open, and the FM-1 dropped off USB every few minutes. Setting the card profile to `off` (`scripts/fm1_audio_off.sh`) fixed it; verify with `scripts/fm1_watch_usb.sh` before flashing.
- Don't use `python3 -I` if mido is installed with `pip --user`; use `-P`.
- Neither the stock firmware nor Felucca sends MIDI CC from the knobs; only key notes go out over USB.

## Links

- Felucca: https://github.com/hugelton/Felucca （wiki: Installation / Troubleshooting）
- FM1 Open（M-VAVE）: https://github.com/m-vave/fm1_open
- ブログ: https://bey.jp/

## License

このリポジトリのスクリプトと文書は MIT。Felucca 本体とインストーラは GPL-3.0（このリポジトリには含めていません）。
