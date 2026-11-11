#!/usr/bin/env python3
"""Local now-playing receiver, artwork converter and optional USB bridge."""
import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import re
import secrets
import threading
import time
import urllib.parse
import urllib.request
import warnings
import zlib

from PIL import Image, ImageOps
from protocol import ART_SIZE, ART_BYTES, STATE, COVER, MODE, packet, rgb565

ROOT = Path(__file__).resolve().parents[1]
HTTP_PORT = 8766
MAX_IMAGE = 5 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 16000000


def token():
    path = ROOT / "local/bridge-token"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("x") as output:
            path.chmod(0o600)
            output.write(secrets.token_hex(32))
    result = path.read_text().strip()
    if not re.fullmatch(r"[a-f0-9]{64}", result):
        raise ValueError("Invalid local bridge token; move it aside and run setup again.")
    return result


def allowed_art(url):
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port not in (None,443)
            or not (host.endswith(".googleusercontent.com") or host.endswith(".ytimg.com"))):
        raise ValueError("Artwork must use the music service's HTTPS image CDN.")
    return url


class ImageRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        allowed_art(newurl)
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def fetch_art(url):
    request = urllib.request.Request(allowed_art(url), headers={"User-Agent":"DigitalVinyl/1.0"})
    with urllib.request.build_opener(ImageRedirects()).open(request, timeout=6) as response:
        data = response.read(MAX_IMAGE + 1)
    if len(data)>MAX_IMAGE:
        raise ValueError("Artwork exceeds 5 MiB")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data)) as original:
            image = ImageOps.fit(original.convert("RGB"), (ART_SIZE,ART_SIZE),
                                 method=Image.Resampling.LANCZOS)
    png = io.BytesIO(); image.save(png,format="PNG")
    return png.getvalue(), rgb565(image)


def validate(message):
    if not isinstance(message,dict):
        raise ValueError("Expected a JSON object")
    result = {}
    for field,limit in [("title",200),("artist",200),("trackId",200),("artUrl",2048)]:
        value = message.get(field,"")
        if not isinstance(value,str) or len(value)>limit:
            raise ValueError(f"Invalid {field}")
        result[field] = value
    for field in ("available","playing"):
        if type(message.get(field)) is not bool:
            raise ValueError(f"Invalid {field}")
        result[field] = message[field]
    if result["artUrl"]:
        allowed_art(result["artUrl"])
    return result


class Store:
    def __init__(self, loader=fetch_art, clock=time.monotonic):
        self.lock=threading.Lock(); self.loader=loader; self.clock=clock
        self.updated=0; self.version=0; self.key=None; self.loaded_key=None
        self.png=None; self.rgb=None; self.error=""; self.loading=set()
        self.failed_key=None; self.retry_after=0
        self.data={"title":"", "artist":"", "trackId":"", "artUrl":"", "available":False, "playing":False}
        self.device="Preview only — no USB device opened"

    def ingest(self, message):
        data=validate(message)
        key=(data["trackId"],data["artUrl"])
        with self.lock:
            self.data=data; self.updated=self.clock(); self.key=key
            if (self.loaded_key==key or key in self.loading or not data["available"]
                    or (self.failed_key==key and self.clock()<self.retry_after)):
                return
            self.loading.add(key); self.error="Loading artwork"
        try:
            if not data["artUrl"]:
                raise ValueError("No album artwork found in the player")
            png, raw = self.loader(data["artUrl"])
            with self.lock:
                if self.key==key:
                    self.png=png; self.rgb=raw; self.loaded_key=key; self.version+=1; self.error=""
        except (OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning) as error:
            with self.lock:
                if self.key==key:
                    self.error=f"Artwork unavailable: {type(error).__name__}"
                    self.failed_key=key; self.retry_after=self.clock()+15
        finally:
            with self.lock: self.loading.discard(key)

    def snapshot(self):
        with self.lock:
            fresh=self.data["available"] and self.clock()-self.updated<10
            art_ready=fresh and self.loaded_key==self.key and self.rgb is not None
            public={"title":self.data["title"],"artist":self.data["artist"],
                    "mode":"live" if fresh else "waiting", "playing":fresh and self.data["playing"],
                    "artReady":art_ready,"artVersion":self.version,"error":self.error if fresh else "",
                    "device":self.device}
            return public, self.rgb if art_ready else None


def usb_worker(store, port, demo, stop):
    import serial
    while not stop.is_set():
        try:
            link=serial.Serial(port=None,baudrate=115200,timeout=0.2,write_timeout=10)
            link.dtr=False; link.rts=False; link.port=port; link.open()
            with link:
                verified=False
                for _ in range(6):
                    link.write(b"?")
                    if b"DVY1 READY" in link.readline(): verified=True; break
                    if stop.wait(0.3): return
                if not verified:
                    raise RuntimeError("Digital Vinyl firmware did not answer; no artwork sent")
                with store.lock: store.device="USB connected — firmware handshake verified"

                def send(kind,payload):
                    frame=packet(kind,payload)
                    for offset in range(0,len(frame),2048):
                        link.write(frame[offset:offset+2048])
                    expected=f"ACK {kind} {zlib.crc32(payload):08x}".encode()
                    deadline=time.monotonic()+5
                    while time.monotonic()<deadline:
                        if link.readline().strip()==expected: return
                    raise RuntimeError("Board did not acknowledge a complete frame")

                send(MODE,bytes([1 if demo else 0]))
                delivered=-1
                while not stop.is_set():
                    state,art=store.snapshot()
                    if art is not None and state["artVersion"]!=delivered:
                        send(COVER,art); delivered=state["artVersion"]
                    send(STATE,bytes([int(state["artReady"]),int(state["playing"])]))
                    stop.wait(0.5)
        except (OSError,RuntimeError,serial.SerialException) as error:
            with store.lock: store.device=f"USB waiting: {error}"
            stop.wait(2)


def handler(store, secret):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass # No listening history, tokens or URLs in logs.

        def valid_host(self):
            return self.headers.get("Host")==f"127.0.0.1:{HTTP_PORT}"

        def respond(self,code,body,mime="application/json"):
            self.send_response(code)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(body)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers()
            try: self.wfile.write(body)
            except (BrokenPipeError,ConnectionResetError): pass

        def do_GET(self):
            if not self.valid_host(): return self.respond(403,b'{}')
            route=urllib.parse.urlsplit(self.path).path
            if route=="/api/state":
                return self.respond(200,json.dumps(store.snapshot()[0]).encode())
            if route=="/api/art.png":
                with store.lock: png=store.png
                return self.respond(200,png,"image/png") if png else self.respond(404,b'{}')
            pages={"/":("index.html","text/html; charset=utf-8"),
                   "/app.js":("app.js","text/javascript; charset=utf-8"),
                   "/style.css":("style.css","text/css; charset=utf-8")}
            if route not in pages: return self.respond(404,b'{}')
            name,mime=pages[route]
            self.respond(200,(ROOT/"preview"/name).read_bytes(),mime)

        def do_POST(self):
            if not self.valid_host() or self.path!="/api/now-playing":
                return self.respond(404,b'{}')
            supplied=self.headers.get("Authorization","")
            if not hmac.compare_digest(supplied,"Bearer "+secret):
                return self.respond(401,b'{}')
            if self.headers.get("Content-Type","").split(";")[0]!="application/json":
                return self.respond(415,b'{}')
            try:
                size=int(self.headers.get("Content-Length","0"))
                if size<2 or size>8192: raise ValueError("Invalid size")
                message=json.loads(self.rfile.read(size))
                store.ingest(message)
                self.respond(200,b'{"ok":true}')
            except (ValueError,TypeError): self.respond(400,b'{}')
    return Handler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port",help="Explicit board serial port; omit for preview only")
    parser.add_argument("--demo",action="store_true",help="Explicitly put the board in labeled rehearsal mode")
    args=parser.parse_args()
    state=Store(); stop=threading.Event()
    server=ThreadingHTTPServer(("127.0.0.1",HTTP_PORT),handler(state,token()))
    if args.port:
        threading.Thread(target=usb_worker,args=(state,args.port,args.demo,stop),daemon=True).start()
    print(f"Digital Vinyl: http://127.0.0.1:{HTTP_PORT} (local only)",flush=True)
    print("Live source waiting. Demo mode is labeled and separate.",flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: stop.set(); server.server_close()


if __name__=="__main__": main()
