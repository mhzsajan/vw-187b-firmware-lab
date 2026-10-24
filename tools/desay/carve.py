import gzip, tarfile, io, os, re, sys

P = r'E:\01 Win Apps\Car Softs\VW Car Radios Firmwares\187B\DessaySv\6RD 035 187B_ SW0358\6RD_035_187B_TR7247_SW0358_20180328.bin'
OUT = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay'
START = 0x200000

class Slice(io.RawIOBase):
    def __init__(self, f, start, length=None):
        self.f = f; self.start = start; self.pos = 0; self.length = length
    def readable(self): return True
    def seekable(self): return True
    def seek(self, off, whence=0):
        if whence == 0: self.pos = off
        elif whence == 1: self.pos += off
        elif whence == 2: raise io.UnsupportedOperation
        return self.pos
    def tell(self): return self.pos
    def read(self, n=-1):
        self.f.seek(self.start + self.pos)
        if n is None or n < 0:
            data = self.f.read()
        else:
            data = self.f.read(n)
        self.pos += len(data)
        return data
    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)

f = open(P, 'rb')
sliceio = io.BufferedReader(Slice(f, START), buffer_size=1 << 20)
gz = gzip.GzipFile(fileobj=sliceio, mode='rb')
tf = tarfile.open(fileobj=gz, mode='r|')

names = []
exts = {}
kw = re.compile(rb'(skoda|logo|startscreen|startup|carplay|carlife|mirrorlink|aap|android|hmi|theme|variant|coding|boot|sign|cert|\.ttf|gres|res)', re.I)
interesting = []
count = 0
dirs = set()
try:
    for m in tf:
        count += 1
        n = m.name
        names.append((n, m.size, m.type))
        top = n.split('/')[0]
        dirs.add(top)
        if m.isfile():
            e = os.path.splitext(n)[1].lower()
            exts[e] = exts.get(e, 0) + 1
            if kw.search(n.encode('utf-8', 'surrogateescape')):
                interesting.append((n, m.size))
        if count % 2000 == 0:
            print(f'  ...{count} members, last={n}', flush=True)
except Exception as ex:
    print(f'STREAM ERROR after {count} members: {ex!r}')
print(f'TOTAL members={count}')
print(f'top-level: {sorted(dirs)[:60]}')
print('ext histogram top 40:', sorted(exts.items(), key=lambda x: -x[1])[:40])
with open(os.path.join(OUT, 'tar_names.txt'), 'w', encoding='utf-8', errors='replace') as fh:
    for n, s, t in names:
        fh.write(f'{s}\t{t}\t{n}\n')
print(f'--- interesting names ({len(interesting)}):')
for n, s in interesting[:400]:
    print(f'  {s:>10,d}  {n}')
