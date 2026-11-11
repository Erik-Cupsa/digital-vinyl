"""Wire protocol shared with firmware/Protocol.h: bounded frames + CRC32 + ACK."""
import struct
import zlib

STATE, COVER, MODE = 1, 2, 3
ART_SIZE = 224
ART_BYTES = ART_SIZE * ART_SIZE * 2


def packet(kind, payload):
    expected = {STATE:2, COVER:ART_BYTES, MODE:1}
    if kind not in expected or len(payload) != expected[kind]:
        raise ValueError("Wrong packet type/length")
    return struct.pack("<4sBBII", b"DVY1", kind, 0, len(payload),
                       zlib.crc32(payload)) + payload


def rgb565(image):
    output = bytearray()
    for r, g, b in image.convert("RGB").getdata():
        value = ((r & 248) << 8) | ((g & 252) << 3) | (b >> 3)
        output.extend(struct.pack("<H", value))
    return bytes(output)
