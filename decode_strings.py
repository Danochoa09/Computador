import struct

vals = [(21, 7954884599197540417), (22, 5972084), (23, 23389), (24, 2112093), (25, 10)]
for n, v in vals:
    s = struct.pack("<Q", v).rstrip(b"\x00").decode("utf-8", errors="replace")
    print(f"str_{n}: {repr(s)}")
