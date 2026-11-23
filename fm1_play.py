#!/usr/bin/env python3
"""FM-1 でメロディを鳴らす / .mid に書き出す。

  python3 fm1_play.py rain              … FM-1 で「雨」を鳴らす
  python3 fm1_play.py morning --channel 2
  python3 fm1_play.py --list
  python3 fm1_play.py --export          … melodies/*.mid を作る（PC で試聴用）

メロディは melodies/melodies.json。ポートは名前に Felucca / USB Composite を含むものを自動で使う。
"""
import argparse, json, pathlib, re, sys, time
import mido

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "melodies" / "melodies.json"
NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
PORT_RE = re.compile(r"felucca|usb composite", re.I)


def note_num(name):
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", name)
    if not m:
        raise ValueError(f"音名が読めません: {name}")
    n = NAMES[m[1]] + {"#": 1, "b": -1, "": 0}[m[2]]
    return 12 * (int(m[3]) + 1) + n          # C4 = 60


def events(mel, channel=None):
    """(待ち秒, mido.Message) の列"""
    ch = (channel or mel.get("channel", 1)) - 1
    beat = 60.0 / mel.get("bpm", 120)
    gate = mel.get("gate", 0.8)
    for name, length, vel in mel["notes"]:
        dur = length * beat
        if name == "R":
            yield dur, None
            continue
        ns = [note_num(x) for x in name.split("+")]
        for n in ns:
            yield 0, mido.Message("note_on", channel=ch, note=n, velocity=vel)
        yield dur * gate, None
        for n in ns:
            yield 0, mido.Message("note_off", channel=ch, note=n, velocity=0)
        yield dur * (1 - gate), None


def find_port():
    for n in mido.get_output_names():
        if PORT_RE.search(n):
            return n
    sys.exit("FM-1 の MIDI ポートが見つかりません")


def play(mel, channel=None, port=None):
    with mido.open_output(port or find_port()) as out:
        try:
            for wait, msg in events(mel, channel):
                if msg:
                    out.send(msg)
                if wait:
                    time.sleep(wait)
        finally:
            ch = (channel or mel.get("channel", 1)) - 1
            out.send(mido.Message("control_change", channel=ch, control=123, value=0))  # 全ノートオフ


def export(name, mel):
    mf = mido.MidiFile(ticks_per_beat=480)
    tr = mido.MidiTrack(); mf.tracks.append(tr)
    tempo = mido.bpm2tempo(mel.get("bpm", 120))
    tr.append(mido.MetaMessage("set_tempo", tempo=tempo))
    pending = 0.0
    for wait, msg in events(mel):
        if msg:
            tr.append(msg.copy(time=int(round(mido.second2tick(pending, 480, tempo)))))
            pending = 0.0
        pending += wait
    path = HERE / "melodies" / f"{name}.mid"
    mf.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("melody", nargs="?")
    ap.add_argument("--channel", type=int, help="MIDI チャンネル 1-16（既定は JSON の値）")
    ap.add_argument("--port", help="出力ポート名（既定は自動）")
    ap.add_argument("--gate", type=float, help="音の長さの割合 0-1（既定は JSON の値。大きいほど LED が長く光る）")
    ap.add_argument("--bpm", type=float, help="テンポ（既定は JSON の値）")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--export", action="store_true")
    a = ap.parse_args()
    data = {k: v for k, v in json.loads(DATA.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    if a.list:
        for k, v in data.items():
            print(f"{k}\t{v.get('title', '')}")
        return
    if a.export:
        for k, v in data.items():
            print(export(k, v))
        return
    if a.melody not in data:
        ap.error(f"メロディ名: {', '.join(data)}")
    mel = dict(data[a.melody])
    if a.gate is not None:
        mel["gate"] = a.gate
    if a.bpm is not None:
        mel["bpm"] = a.bpm
    play(mel, a.channel, a.port)


if __name__ == "__main__":
    main()
