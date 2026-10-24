"""Analyse the two remaining mod paths on the Desay unit.

A) Where does the logo come from?  libsvapi_vw exports svapi_exlap_logo_get/_set and logs
   "load exlap_logo_index, invalid, Using default" -> find the index/asset files in the rootfs
   and in the app packages.
B) What is inside a brand Kanzi bundle?  Extract res/VW_MP2017.kzb from the lockscreen package
   and look for embedded images (PNG/JPEG/DDS/KTX/BMP) that could be replaced without Kanzi Studio.
"""
import gzip, tarfile, io, os, re, struct

BIN = r'I:\187B-Firmware-Library\10-Desay-SV-Official\SW0317_2020-03-03\6RD_035_187B_TR7247_SW0317_20200303.bin'
APP = 0x51EC7FB
ROOTFS = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\osbin\rootfs'
OUT = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\logo_probe'
os.makedirs(OUT, exist_ok=True)


class Slice(io.RawIOBase):
    def __init__(self, f, start):
        self.f, self.start, self.pos = f, start, 0
    def readable(self): return True
    def seekable(self): return True
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off; return self.pos
    def tell(self): return self.pos
    def read(self, n=-1):
        self.f.seek(self.start + self.pos)
        d = self.f.read() if (n is None or n < 0) else self.f.read(n)
        self.pos += len(d); return d
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


# ---------------------------------------------------------------- A: rootfs logo files
print('=' * 78)
print('A) logo-related files in the extracted rootfs')
print('=' * 78)
hits = []
for dirpath, dirnames, filenames in os.walk(ROOTFS):
    for fn in filenames:
        low = fn.lower()
        if any(k in low for k in ('logo', 'splash', 'brand', 'startup')):
            p = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            hits.append((os.path.relpath(p, ROOTFS), sz))
for rel, sz in sorted(hits, key=lambda x: -x[1])[:40]:
    print(f'  {sz:>10,d}  {rel}')
print(f'  total: {len(hits)} files')

# exlap logo index: search binaries for the index filename near the log strings
print('\n  searching binaries for "exlap_logo" and nearby ASCII (index path hints):')
scanned = 0
for dirpath, dirnames, filenames in os.walk(os.path.join(ROOTFS, 'usr')):
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        try:
            if os.path.getsize(p) > 8_000_000:
                continue
            data = open(p, 'rb').read()
        except Exception:
            continue
        if b'exlap_logo' not in data:
            continue
        scanned += 1
        print(f'\n  {os.path.relpath(p, ROOTFS)} ({len(data):,} B)')
        for m in re.finditer(rb'[\x20-\x7e]{4,}', data):
            s = m.group().decode('latin1')
            if re.search(r'(?i)(logo|\.idx|\.bin|index|\.kzb|default)', s):
                print(f'     {s[:140]}')

# ---------------------------------------------------------------- B: brand kzb
print()
print('=' * 78)
print('B) inside a brand Kanzi bundle (lockscreen package)')
print('=' * 78)
f = open(BIN, 'rb')
gz = gzip.GzipFile(fileobj=io.BufferedReader(Slice(f, APP), buffer_size=1 << 20), mode='rb')
tf = tarfile.open(fileobj=gz, mode='r|')
target = None
for m in tf:
    if m.isfile() and m.name.endswith('lockscreen-1.0.0.pkg'):
        data = tf.extractfile(m).read()
        raw = gzip.decompress(data)
        ti = tarfile.open(fileobj=io.BytesIO(raw), mode='r:')
        for mem in ti.getmembers():
            if mem.name.endswith('.kzb'):
                kz = ti.extractfile(mem).read()
                dest = os.path.join(OUT, os.path.basename(mem.name))
                open(dest, 'wb').write(kz)
                print(f'  extracted {mem.name} ({len(kz):,} B) -> {dest}')
                target = kz
        break
f.close()

if target:
    print(f'  header: {target[:32].hex(" ")}')
    print('  ascii: ' + ''.join(chr(c) if 32 <= c < 127 else '.' for c in target[:32]))
    sigs = {b'\x89PNG\r\n\x1a\n': 'PNG', b'\xff\xd8\xff': 'JPEG', b'DDS ': 'DDS',
            b'\xabKTX': 'KTX', b'BM': 'BMP?', b'PVR\x03': 'PVR',
            b'1TXC': 'TXC?', b'GXTL': 'texture'}
    for sig, name in sigs.items():
        idx = 0
        cnt = 0
        firsts = []
        while True:
            i = target.find(sig, idx)
            if i < 0:
                break
            cnt += 1
            if len(firsts) < 5:
                firsts.append(i)
            idx = i + 1
        if cnt:
            print(f'  {name}: {cnt} occurrence(s), first at {[hex(x) for x in firsts]}')
    # PNG dimension dump for the first few
    idx = 0
    shown = 0
    while shown < 6:
        i = target.find(b'\x89PNG\r\n\x1a\n', idx)
        if i < 0:
            break
        if i + 24 <= len(target):
            w, h = struct.unpack('>II', target[i + 16:i + 24])
            print(f'    PNG @0x{i:x}: {w}x{h} px')
        idx = i + 1
        shown += 1
    strs = re.findall(rb'[\x20-\x7e]{5,}', target[:400000])
    print('  ascii sample:', [s.decode() for s in strs[:18]])
