#!/bin/sh
# FM-1 の USB 切断を見張る（書き込み前の安定確認用）。
# 使い方: sh fm1_watch_usb.sh [分]   （既定 20 分。dmesg を読める権限が必要）
# FM-1 の USB パス（例 1-2、ハブ経由なら 1-2.3）は自動で探す。
set -eu
MIN=${1:-20}
path=""
for d in /sys/bus/usb/devices/*; do
  [ -f "$d/idVendor" ] || continue
  v=$(cat "$d/idVendor"); pr=$(cat "$d/product" 2>/dev/null || true)
  # 公式ファーム = 4c4a:c755（Jieli）、Felucca = 1209:0001（product "Felucca"）
  if [ "$v" = "4c4a" ] || { [ "$v" = "1209" ] && [ "$pr" = "Felucca" ]; }; then path=$(basename "$d"); break; fi
done
[ -n "$path" ] || { echo "FM-1 (USB ID 4c4a:xxxx / Felucca 1209:0001) が見つかりません" >&2; exit 1; }

start=$(cut -d' ' -f1 /proc/uptime | cut -d. -f1)
end=$((start + MIN * 60))
echo "watching usb $path for $MIN min from $(date +%T)"
while [ "$(cut -d' ' -f1 /proc/uptime | cut -d. -f1)" -lt "$end" ]; do
  if dmesg | awk -v s="$start" -F'[][]' '$2+0>s' | grep -q "usb $path: USB disconnect"; then
    echo "DISCONNECT at $(date +%T)"
    exit 2
  fi
  sleep 10
done
echo "STABLE for $MIN min (until $(date +%T))"
