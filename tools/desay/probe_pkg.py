"""Look inside Desay .pkg app packages and find the boot logo/brand assets.

Findings so far: app-pkg.bin (gzip->tar) holds N gzip-compressed *.pkg (Kanzi apps).
This script decompresses each pkg and reports its inner container + logo/theme assets,
then searches os.bin / u-boot / svp.bin for splash & brand evidence.
"""
import gzip, tarfile, io, os, re, struct, zipfile, lzma, bz2

BIN = r'I:\187B-Firmware-Library\10-Desay-SV-Official\SW0317_2020-03-03\6RD_035_187B_TR7247_SW0317_20200303.bin'
APP = 0x51EC7FB
SVP = 0x200000
OS_ = 0x8464239
OUT = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\composition'
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


f = open(BIN, 'rb')

def inner_kind(b):
    if b[:3] == b'PK\x03\x04':
        return 'zip'
    if b[:2] == b'\x1f\x8b':
        return 'gzip'
    if b[:4] == b'\xfd7zXZ':
        return 'xz'
    if b[:4] == b'ustar' or b[257:262] == b'ustar':
        return 'tar'
    if b[:4] == b'.KZB':
        return 'kanzi-kzb'
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    return 'other:' + b[:8].hex(' ')

print('=' * 78)
print('app .pkg members')
print('=' * 78)
gz = gzip.GzipFile(fileobj=io.BufferedReader(Slice(f, APP), buffer_size=1 << 20), mode='rb')
tf = tarfile.open(fileobj=gz, mode='r|')
stash = {}
for m in tf:
    if not m.isfile() or not m.name.endswith('.pkg'):
        continue
    name = os.path.basename(m.name)
    data = tf.extractfile(m).read()
    try:
        raw = gzip.decompress(data)
    except Exception as e:
        print(f'{name}: gzip fail {e!r}')
        continue
    kind = inner_kind(raw)
    print(f'\n{name}  [{len(data):,} B compressed -> {len(raw):,} B]  inner={kind}')
    if kind == 'zip':
        zf = zipfile.ZipFile(io.BytesIO(raw))
        names = zf.namelist()
        print(f'  zip members={len(names)}; sample: {names[:12]}')
        hits = [n for n in names if re.search(r'(?i)(logo|splash|brand|welcome|vw|skoda|\.png|\.jpg|\.kzb|\.dds|\.ktx|\.ttf)', n)]
        print(f'  logo/theme-ish ({len(hits)}): {hits[:25]}')
        for n in hits[:6]:
            safe = re.sub(r'[^A-Za-z0-9._-]', '_', name + '__' + n)
            open(os.path.join(OUT, safe[-120:]), 'wb').write(zf.read(n))
    elif kind == 'tar':
        ti = tarfile.open(fileobj=io.BytesIO(raw), mode='r:')
        names = [x.name for x in ti.getmembers()]
        print(f'  tar members={len(names)}; sample: {names[:12]}')
        hits = [n for n in names if re.search(r'(?i)(logo|splash|brand|welcome|vw|skoda|\.png|\.jpg|\.kzb)', n)]
        print(f'  logo/theme-ish ({len(hits)}): {hits[:25]}')
    elif kind == 'gzip':
        # nested gzip (e.g. pkg containing another archive)
        try:
            raw2 = gzip.decompress(raw)
            print(f'  nested gzip -> {inner_kind(raw2)}, {len(raw2):,} B')
            if raw2[:2] == b'PK':
                zf = zipfile.ZipFile(io.BytesIO(raw2))
                names = zf.namelist()
                print(f'    zip members={len(names)}; sample: {names[:15]}')
                hits = [n for n in names if re.search(r'(?i)(logo|splash|brand|welcome|vw|skoda|\.png|\.jpg|\.kzb)', n)]
                print(f'    logo/theme-ish ({len(hits)}): {hits[:25]}')
        except Exception as e:
            print(f'  nested gzip fail: {e!r}')
    else:
        ss = re.findall(rb'[\x20-\x7e]{8,}', raw[:200000])
        print('  strings:', [s.decode() for s in ss[:15]])
    stash[name] = raw

print()
print('=' * 78)
print('splash / brand search across components')
print('=' * 78)
pats = [b'logo', b'Logo', b'LOGO', b'splash', b'Splash', b'welcome', b'Welcome', b'bootlogo', b'SKODA', b'Skoda',
        b'Volkswagen', b'VOLKSWAGEN', b'VW_', b'brand', b'Brand']
for label, off, end in (('svp.bin', SVP, 0x51EC7FB), ('os.bin', OS_, os.path.getsize(BIN))):
    f.seek(off)
    blob = f.read(end - off)
    print(f'\n{label} ({len(blob):,} bytes):')
    for p in pats:
        n = blob.count(p)
        if n:
            i = blob.find(p)
            ctx = blob[max(0, i - 40): i + 60]
            asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in ctx)
            print(f'  {p.decode():12s} count={n:5d} first@0x{off+i:x}  "{asc}"')
    # image signatures anywhere
    for sig, nm in ((b'\x89PNG\r\n\x1a\n', 'PNG'), (b'\xff\xd8\xff', 'JPEG'), (b'.KZB', 'KZB'), (b'BM', 'BMP?')):
        c = blob.count(sig)
        if c:
            print(f'  magic {nm} occurrences={c}')

# u-boot splash env
f.seek(OS_)
osblob = f.read()
i = osblob.find(b'splashimage')
print(f"\nu-boot 'splashimage' env: {'found @0x%x' % (OS_+i) if i>=0 else 'not found'}")
for kw in (b'splash', b'bootlogo', b'logo'):
    idx = 0
    cnt = 0
    while True:
        j = osblob.find(kw, idx)
        if j < 0:
            break
        cnt += 1
        idx = j + 1
    print(f'  os.bin contains {kw.decode()}: {cnt} times')
f.close()
