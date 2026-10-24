import gzip, tarfile, io, os, re, zlib

DESAY = 'I:\\187B-Firmware-Library\\10-Desay-SV-Official\\SW0358_2018-03-28\\6RD_035_187B_TR7247_SW0358_20180328.bin'
OUT = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\rootfs'
os.makedirs(OUT, exist_ok=True)

class Slice(io.RawIOBase):
    def __init__(self, f, start):
        self.f = f; self.start = start; self.pos = 0
    def readable(self): return True
    def seekable(self): return True
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off
        return self.pos
    def tell(self): return self.pos
    def read(self, n=-1):
        self.f.seek(self.start + self.pos)
        d = self.f.read() if (n is None or n < 0) else self.f.read(n)
        self.pos += len(d); return d
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

WANT = {'./share/ui/Mazda_G5_Logo.kzb': 'logo.kzb',
        './lib/libupdate.so.1.0.0': 'libupdate.so',
        './bin/updateservice': 'updateservice',
        './share/CarPlay/VWicon_256X256.png': 'vwicon.png'}
f = open(DESAY, 'rb')
gz = gzip.GzipFile(fileobj=io.BufferedReader(Slice(f, 0x200000), buffer_size=1 << 20), mode='rb')
tf = tarfile.open(fileobj=gz, mode='r|')
got = {}
for m in tf:
    if m.name in WANT and m.isfile():
        got[WANT[m.name]] = tf.extractfile(m).read()
for k, v in got.items():
    open(os.path.join(OUT, k), 'wb').write(v)
    print(f'{k}: {len(v)} bytes')

kz = got['logo.kzb']
print('\n=== logo.kzb header')
print(kz[:96].hex(' '))
print(repr(kz[:96]))
# look for embedded PNG / raw image / known container magics
for magic, name in [(b'\x89PNG', 'png'), (b'\x00\x00\x00\x00\x01\x01', 'raw?'), (b'KZB', 'kzb'), (b'\x1f\x8b', 'gzip'), (b'PK\x03\x04', 'zip')]:
    i = kz.find(magic)
    print(f'  find {name}: {i}')
# count unique byte values in a middle window to guess raw vs compressed
win = kz[len(kz)//2: len(kz)//2 + 65536]
print('  mid entropy approx unique bytes:', len(set(win)))
# does the kzb contain a bitmap header? search for common Kanzi 'kzb' strings
strs = re.findall(rb'[ -~]{5,}', kz[:200000])
print('  ascii in first 200KB:', [s.decode() for s in strs[:20]])

for name in ['libupdate.so', 'updateservice']:
    data = got[name]
    pat = re.compile(rb'(?i)(md5|sha1|sha256|crc32|crc|signature|sign_|verify|invalid package|package|version|rollback|magic|decrypt|aes)')
    hits = {}
    for m in pat.finditer(data):
        s = m.group().lower()
        hits.setdefault(s, 0)
        hits[s] += 1
    print(f'\n=== {name}: keyword counts', hits)
    ctx = []
    for m in re.finditer(rb'(?i)(md5|signature|verify|invalid|crc|decrypt|encrypt|aes|rollback)', data):
        a = max(0, m.start()-60); b = min(len(data), m.end()+60)
        s = ''.join(chr(c) if 32 <= c < 127 else '.' for c in data[a:b])
        ctx.append(s)
    seen = set()
    for s in ctx:
        if s not in seen:
            seen.add(s); print('   ', s)
        if len(seen) > 25: break
