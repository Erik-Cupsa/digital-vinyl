"""Exercise the real USB worker against a protocol peer, without opening hardware."""
from pathlib import Path
import struct
import sys
import threading
import unittest
from unittest.mock import patch
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bridge'))
import server
from test_bridge import fake_art, message


class USBTests(unittest.TestCase):
    def test_handshake_complete_cover_ack_and_state(self):
        stop=threading.Event(); received=[]; buffer=bytearray(); replies=[]
        class Peer:
            dtr=True; rts=True; port=None
            def __init__(self, **kwargs): pass
            def open(self):
                assert self.port=='test-only' and not self.dtr and not self.rts
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def write(self,data):
                if data==b'?' and not buffer:
                    replies.append(b'DVY1 READY\n'); return len(data)
                buffer.extend(data)
                if len(buffer)>=14:
                    magic,kind,reserved,size,crc=struct.unpack('<4sBBII',buffer[:14])
                    assert magic==b'DVY1' and reserved==0
                    if len(buffer)==14+size:
                        payload=bytes(buffer[14:]); assert zlib.crc32(payload)==crc
                        received.append((kind,payload)); buffer.clear()
                        replies.append(f'ACK {kind} {crc:08x}\n'.encode())
                        if kind==1: stop.set()
                return len(data)
            def readline(self): return replies.pop(0) if replies else b''
        store=server.Store(loader=fake_art); store.ingest(message())
        with patch('serial.Serial',Peer): server.usb_worker(store,'test-only',False,stop)
        self.assertEqual([kind for kind,_ in received],[3,2,1])
        self.assertEqual(received[0][1],b'\x00')
        self.assertEqual(len(received[1][1]),100352)
        self.assertEqual(received[2][1],b'\x01\x01')
        self.assertIn('handshake verified',store.device)

    def test_foreign_firmware_gets_no_binary_data(self):
        writes=[]
        class Stop:
            done=False
            def is_set(self): return self.done
            def wait(self,seconds):
                if seconds==2: self.done=True
                return self.done
        class Peer:
            def __init__(self,**kwargs): pass
            def open(self): pass
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def write(self,data): writes.append(data)
            def readline(self): return b'Pocket Eyes\n'
        store=server.Store()
        with patch('serial.Serial',Peer): server.usb_worker(store,'test-only',False,Stop())
        self.assertEqual(writes,[b'?']*6)
        self.assertIn('no artwork sent',store.device)
