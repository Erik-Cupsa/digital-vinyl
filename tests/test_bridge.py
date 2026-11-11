import http.client
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import struct
import sys
import threading
import unittest
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"bridge"))
import protocol
import server
from PIL import Image


def message(track="a",playing=True):
    return {"trackId":track,"title":"Test track","artist":"Test artist",
            "artUrl":f"https://lh3.googleusercontent.com/{track}","available":True,"playing":playing}


def fake_art(url):
    image=Image.new("RGB",(224,224),(255,0,0)); png=io.BytesIO(); image.save(png,format="PNG")
    return png.getvalue(),protocol.rgb565(image)


class BridgeTests(unittest.TestCase):
    def test_wire_format_and_pixel_order(self):
        raw=protocol.rgb565(Image.new("RGB",(224,224),(255,0,0)))
        self.assertEqual(raw[:2],b"\x00\xf8")
        frame=protocol.packet(protocol.COVER,raw)
        self.assertEqual(struct.unpack("<4sBBII",frame[:14]),
                         (b"DVY1",2,0,100352,zlib.crc32(raw)))
        with self.assertRaises(ValueError): protocol.packet(protocol.COVER,b"short")

    def test_live_pause_and_stale(self):
        now=[100]
        store=server.Store(loader=fake_art,clock=lambda:now[0])
        self.assertEqual(store.snapshot()[0]["mode"],"waiting")
        store.ingest(message())
        state,raw=store.snapshot()
        self.assertEqual(state["mode"],"live"); self.assertTrue(state["playing"])
        self.assertEqual(len(raw),protocol.ART_BYTES)
        version=state["artVersion"]
        store.ingest(message(playing=False))
        state,_=store.snapshot(); self.assertFalse(state["playing"])
        self.assertEqual(version,state["artVersion"])
        now[0]+=11
        state,raw=store.snapshot(); self.assertEqual(state["mode"],"waiting")
        self.assertFalse(state["playing"]); self.assertIsNone(raw)

    def test_failed_new_cover_does_not_reuse_previous_track(self):
        store=server.Store(loader=fake_art)
        store.ingest(message())
        def failure(url): raise ValueError("bad image")
        store.loader=failure; store.ingest(message("b"))
        state,raw=store.snapshot()
        self.assertFalse(state["artReady"]); self.assertIsNone(raw)

    def test_old_slow_download_cannot_replace_new_track(self):
        started=threading.Event(); release=threading.Event()
        def loader(url):
            if url.endswith('/a'): started.set(); release.wait(2)
            return fake_art(url)
        store=server.Store(loader=loader)
        old=threading.Thread(target=store.ingest,args=(message("a"),)); old.start()
        self.assertTrue(started.wait(1)); store.ingest(message("b")); release.set(); old.join()
        self.assertEqual(store.loaded_key[0],"b")

    def test_art_urls_and_metadata_are_bounded(self):
        for url in ["http://lh3.googleusercontent.com/x","https://127.0.0.1/x",
                    "https://lh3.googleusercontent.com.evil.test/x","file:///tmp/x",
                    "https://user:pass@lh3.googleusercontent.com/x"]:
            with self.assertRaises(ValueError): server.allowed_art(url)
        bad=message(); bad['playing']="true"
        with self.assertRaises(ValueError): server.validate(bad)

    def test_http_pairing_and_host_validation(self):
        store=server.Store(loader=fake_art)
        httpd=ThreadingHTTPServer(('127.0.0.1',0),server.handler(store,'test-secret'))
        thread=threading.Thread(target=httpd.serve_forever,daemon=True); thread.start()
        self.addCleanup(httpd.server_close); self.addCleanup(httpd.shutdown)
        def post(secret,host='127.0.0.1:8766'):
            client=http.client.HTTPConnection('127.0.0.1',httpd.server_port)
            client.request('POST','/api/now-playing',json.dumps(message()),
                {'Host':host,'Content-Type':'application/json','Authorization':'Bearer '+secret})
            result=client.getresponse(); status=result.status; result.read(); client.close(); return status
        self.assertEqual(post('wrong'),401)
        self.assertEqual(post('test-secret','evil.test'),404)
        self.assertEqual(post('test-secret'),200)
        self.assertTrue(store.snapshot()[0]['artReady'])


if __name__=='__main__': unittest.main()
