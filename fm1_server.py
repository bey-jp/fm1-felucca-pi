#!/usr/bin/env python3
"""HA から FM-1 のメロディを鳴らすための小さな HTTP サーバー（標準ライブラリ + mido）。

  POST http://127.0.0.1:5002/play   {"melody": "rain"}   → 鳴らし始めて 202 を返す
  GET  http://127.0.0.1:5002/status                      → FM-1 の接続と再生中かどうか

127.0.0.1 だけで待つ（HA コンテナは host ネットワークなので届く）。同時に1曲だけ。再生中の依頼は 409。
"""
import json, threading, sys, pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import mido
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fm1_play  # noqa: E402

HOST, PORT = "127.0.0.1", 5002
busy = threading.Lock()


def melodies():
    d = json.loads(fm1_play.DATA.read_text(encoding="utf-8"))
    return {k: v for k, v in d.items() if not k.startswith("_")}


def port_name():
    for n in mido.get_output_names():
        if fm1_play.PORT_RE.search(n):
            return n
    return None


def run(mel, port):
    try:
        fm1_play.play(mel, port=port)
    except Exception as e:  # FM-1 が途中で抜かれた等
        print("play error:", e, flush=True)
    finally:
        busy.release()


class H(BaseHTTPRequestHandler):
    def reply(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path != "/status":
            return self.reply(404, {"error": "not found"})
        self.reply(200, {"fm1": port_name(), "playing": busy.locked(), "melodies": list(melodies())})

    def do_POST(self):
        if self.path != "/play":
            return self.reply(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self.reply(400, {"error": "bad json"})
        data = melodies()
        name = req.get("melody")
        if name not in data:
            return self.reply(400, {"error": f"melody: {', '.join(data)}"})
        port = port_name()
        if not port:
            return self.reply(503, {"error": "FM-1 not connected"})
        if not busy.acquire(blocking=False):
            return self.reply(409, {"error": "already playing"})
        threading.Thread(target=run, args=(data[name], port), daemon=True).start()
        print("play", name, flush=True)
        self.reply(202, {"playing": name})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"listening {HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
