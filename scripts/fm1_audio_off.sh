#!/bin/sh
# FM-1（公式 / Felucca）の USB オーディオを PulseAudio で「オフ」にする。
# Home Assistant OS / Supervised の音声コンテナ (hassio_audio) が FM-1 の音声を
# 常時開いたままにすると、FM-1 が数分〜25分おきに USB 切断・再接続を繰り返した。
# MIDI はそのまま使える。FM-1 を挿し直す・HA を再起動すると元に戻るので、そのたびに実行する。
#
# 使い方:  sh fm1_audio_off.sh          … HA の hassio_audio を対象
#          PACTL=pactl sh fm1_audio_off.sh … 普通の Linux（PulseAudio / PipeWire-pulse）
# 戻す:    pactl set-card-profile <カード名> output:analog-stereo+input:analog-stereo
set -eu
PACTL=${PACTL:-"docker exec hassio_audio pactl"}

cards=$($PACTL list cards short | awk '{print $2}' | grep -E 'Jieli_Technology_USB_Composite_Device|Felucca' || true)
if [ -z "$cards" ]; then
  echo "FM-1 のオーディオカードが見つかりません" >&2
  exit 1
fi
for c in $cards; do
  $PACTL set-card-profile "$c" off
  echo "off: $c"
done
