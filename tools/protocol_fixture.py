from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"bridge"))
from protocol import COVER,ART_BYTES,packet
Path('build').mkdir(exist_ok=True)
Path('build/protocol.bin').write_bytes(packet(COVER,b'\x34\x12'*(ART_BYTES//2)))
