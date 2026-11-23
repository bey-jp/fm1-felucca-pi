#!/usr/bin/env python3
"""melodies.json を簡易 FM 音源（2 オペレーター）で WAV に書き出す。PC で試聴する用。
実機 FM-1 / Felucca の音色とは違うが、FM らしい「ベル・エレピ系」の響きで雰囲気を確認できる。

  python3 render_wav.py          … melodies/<名前>.wav を全部作る
"""
import json, pathlib, sys, wave
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from fm1_play import note_num  # noqa: E402

SR = 44100


def fm_note(freq, dur, vel, ratio=3.5, index=2.2, decay=2.5, tail=1.2):
    """ベル系の FM: 変調器の深さも減衰させて、アタックは明るく、余韻は丸く"""
    t = np.arange(int(SR * (dur + tail))) / SR
    amp = np.exp(-t * decay) * np.minimum(t / 0.004, 1)
    rel = np.where(t > dur, np.exp(-(t - dur) * 8), 1.0)
    mod = index * np.exp(-t * decay * 1.5) * np.sin(2 * np.pi * freq * ratio * t)
    return (vel / 127) * amp * rel * np.sin(2 * np.pi * freq * t + mod)


def render(mel):
    pv = dict(mel.get("preview", {}))            # 試聴用の音色（メロディごと。実機には関係なし）
    peak = pv.pop("peak", 0.8)
    beat = 60.0 / mel.get("bpm", 120)
    gate = mel.get("gate", 0.8)
    total = sum(n[1] for n in mel["notes"]) * beat + 2
    buf = np.zeros(int(SR * total))
    pos = 0.0
    for name, length, vel in mel["notes"]:
        dur = length * beat
        if name != "R":
            for x in name.split("+"):
                f = 440 * 2 ** ((note_num(x) - 69) / 12)
                s = fm_note(f, dur * gate, vel, **pv)
                i = int(pos * SR)
                buf[i:i + len(s)] += s[:len(buf) - i]
        pos += dur
    buf /= max(1e-9, np.abs(buf).max()) / peak
    return (buf * 32767).astype(np.int16)


def main():
    data = json.loads((HERE / "melodies.json").read_text(encoding="utf-8"))
    for k, v in data.items():
        if k.startswith("_"):
            continue
        pcm = render(v)
        path = HERE / f"{k}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        print(path, f"{len(pcm) / SR:.1f}s")


if __name__ == "__main__":
    main()
