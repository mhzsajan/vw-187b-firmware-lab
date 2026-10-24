"""Desay container: component table + boundary checksums (SW0317), fast paths.

Records at 0x000/0x200/0x400/0x600/0x800, u32@+4 = absolute start offset.
Checksum targets displayed by the unit:
    Radio SW checksum          0xc473
    RadioBootloader checksum   0xda8c
Only small windows are hashed (table-driven CRC16 + numpy where useful).
"""
import os, struct, hashlib, zlib

P = r'I:\187B-Firmware-Library\10-Desay-SV-Official\SW0317_2020-03-03\6RD_035_187B_TR7247_SW0317_20200303.bin'
SIZE = os.path.getsize(P)
f = open(P, 'rb')

recs = []
for off in range(0, 0x1000, 0x200):
    f.seek(off)
    rec = f.read(0x200)
    if rec[:4] != b'\x48\x81\x48\x81':
        continue
    val = struct.unpack('<I', rec[4:8])[0]
    name = rec[8:0x28].split(b'\x00')[0].decode('latin1', 'replace')
    ver = rec[0x4c:0x80].split(b'\x00')[0].decode('latin1', 'replace')
    recs.append((off, val, name, ver))

print(f'file = {os.path.basename(P)}\nsize = {SIZE:,} (0x{SIZE:X})\n')
print(f"{'rec':>6} {'value':>12} {'hex':>12}  {'name':<16} version")
for off, val, name, ver in recs:
    print(f'0x{off:04x} {val:>12,} 0x{val:08x}  {name:<16} {ver}')

bounds = sorted({v for _, v, _, _ in recs if 0 < v < SIZE})
print(f'\nboundaries: {[hex(b) for b in bounds]}')
segments = []
for i, b in enumerate(bounds):
    end = bounds[i + 1] if i + 1 < len(bounds) else SIZE
    segments.append((b, end))
print('\nsegments (start..end, size):')
for s, e in segments:
    f.seek(s); head = f.read(16)
    kind = ('gzip' if head[:2] == b'\x1f\x8b' else
            'uImage' if head[:4] == b'\x27\x05\x19\x56' else
            'zeros' if head == b'\x00' * 16 else 'other')
    print(f'  0x{s:08x}..0x{e:08x}  {e-s:>10,}  {head[:8].hex(" ")}  {kind}')

# ---- uImage components anywhere (plain header scan, 4-byte pattern) -------
print('\nuImage headers found:')
f.seek(0)
data_off = 0
pat = b'\x27\x05\x19\x56'
CH = 1 << 22
prev = b''
while True:
    chunk = f.read(CH)
    if not chunk:
        break
    blob = prev + chunk
    base = data_off - len(prev)
    start = 0
    while True:
        i = blob.find(pat, start)
        if i < 0:
            break
        abs_off = base + i
        if abs_off >= 0:
            f.seek(abs_off); h = f.read(64)
            if len(h) == 64:
                magic, hcrc, ts, size, load, ep, dcrc, os_, arch, typ, comp = struct.unpack('>IIIIIIIBBBB', h[:32])
                nm = h[32:64].split(b'\x00')[0].decode('latin1', 'replace')
                print(f'  0x{abs_off:08x} size={size:>10,} load=0x{load:08x} os={os_} arch={arch} type={typ} name={nm!r}')
        start = i + 4
    prev = blob[-3:]
    data_off += len(chunk)

# ---- CRC16 table-driven ---------------------------------------------------
def make_table(poly, refin):
    tbl = []
    for i in range(256):
        c = i
        if refin:
            c = int(f'{c:08b}'[::-1], 2)
        for _ in range(8):
            c = ((c << 1) ^ poly) & 0xFFFF if (c & 0x8000) else (c << 1) & 0xFFFF
        if refin:
            c = int(f'{c:016b}'[::-1], 2)
        tbl.append(c)
    return tbl

def crc16(data, poly, init, refin=False, xorout=0):
    tbl = make_table(poly, refin)
    crc = init
    if refin:
        for b in data:
            crc = (crc >> 8) ^ tbl[(crc ^ b) & 0xFF]
    else:
        for b in data:
            crc = ((crc << 8) & 0xFFFF) ^ tbl[((crc >> 8) ^ b) & 0xFF]
    return (crc ^ xorout) & 0xFFFF

VARIANTS = {
    'ccitt-false': dict(poly=0x1021, init=0xFFFF),
    'xmodem':      dict(poly=0x1021, init=0x0000),
    'arc':         dict(poly=0xA001, init=0x0000, refin=True),
    'modbus':      dict(poly=0xA001, init=0xFFFF, refin=True),
    'x25':         dict(poly=0x8408, init=0xFFFF, refin=True, xorout=0xFFFF),
    'kermit':      dict(poly=0x8408, init=0x0000, refin=True),
}

def show(label, s, e):
    f.seek(s); data = f.read(e - s)
    out = [f'{label} (0x{s:x}..0x{e:x}, {len(data):,} B)']
    for name, kw in VARIANTS.items():
        out.append(f'{name}={crc16(data, **kw):04x}')
    out.append(f'crc32={zlib.crc32(data) & 0xFFFFFFFF:08x}')
    print('  ' + '  '.join(out))

print('\nchecksum hunt on small windows (Radio SW 0xc473 / Bootloader 0xda8c):')
radio = None
for s, e in segments:
    if e - s < 8_000_000:
        show(f'seg 0x{s:x}', s, e)
# windows around the bootloader banner string
for anchor in (0x8402b09,):
    show('bl-64K', max(0, anchor - 0x8000), anchor + 0x8000)
    show('bl-256K', max(0, anchor - 0x20000), anchor + 0x20000)

# ---- is 0xc473 / 0xda8c stored verbatim anywhere? -------------------------
print('\nverbatim search for c4 73 / 8c da inside the file (first 6 hits each):')
for label, needle in (('0xc473', b'\x73\xc4'), ('0xda8c', b'\x8c\xda')):
    f.seek(0)
    hits = []
    base = 0
    prev = b''
    while True:
        chunk = f.read(CH)
        if not chunk:
            break
        blob = prev + chunk
        b0 = base - len(prev)
        start = 0
        while True:
            i = blob.find(needle, start)
            if i < 0:
                break
            hits.append(b0 + i)
            start = i + 1
        prev = blob[-1:]
        base += len(chunk)
        if len(hits) > 200:
            break
    print(f'  {label}: {len(hits)} hits, first: {[hex(h) for h in hits[:6]]}')

h = hashlib.md5()
f.seek(0)
while True:
    c = f.read(1 << 22)
    if not c:
        break
    h.update(c)
print(f'\nmd5(whole) = {h.hexdigest()}   sidecar = c7d9bd20d4eaa929d91e4dcbe75bfba3')
f.close()
