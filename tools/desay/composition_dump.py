"""Desay 187B (SW0317) full composition dump.

1) app-pkg.bin  (0x51EC7FB, gzip->tar)  : inventory + biggest members + interesting names
2) os.bin       (0x8464239, nested pack): parse its record table, extract uImage kernel/u-boot,
                                          dump platform strings (SoC, RAM, bootargs, drivers)
3) radio.bin    (0x8402309, raw 401200) : header + strings (MCU/DSP identification)
Everything written to desay/composition/ plus a text report.
"""
import gzip, tarfile, io, os, struct, re, hashlib

BIN = r'I:\187B-Firmware-Library\10-Desay-SV-Official\SW0317_2020-03-03\6RD_035_187B_TR7247_SW0317_20200303.bin'
OUT = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\composition'
os.makedirs(OUT, exist_ok=True)
R = []  # report lines


def p(s=''):
    print(s)
    R.append(str(s))


class Slice(io.RawIOBase):
    def __init__(self, f, start, length=None):
        self.f, self.start, self.pos, self.length = f, start, 0, length
    def readable(self): return True
    def seekable(self): return True
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off
        return self.pos
    def tell(self): return self.pos
    def read(self, n=-1):
        self.f.seek(self.start + self.pos)
        d = self.f.read() if (n is None or n < 0) else self.f.read(n)
        self.pos += len(d)
        return d
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


f = open(BIN, 'rb')
SIZE = os.path.getsize(BIN)
p(f'# Desay SW0317 composition dump  ({SIZE:,} bytes)')
p()

# ---------------------------------------------------------------- app-pkg.bin
APP = 0x51EC7FB
APP_END = 0x8402309
p('=' * 76)
p(f'## app-pkg.bin  @0x{APP:x} .. 0x{APP_END:x}  ({(APP_END-APP):,} bytes)')
p('=' * 76)
names = []
tops = {}
exts = {}
count = 0
big = []
try:
    gz = gzip.GzipFile(fileobj=io.BufferedReader(Slice(f, APP), buffer_size=1 << 20), mode='rb')
    tf = tarfile.open(fileobj=gz, mode='r|')
    for m in tf:
        count += 1
        names.append((m.name, m.size))
        tops[m.name.split('/')[0]] = tops.get(m.name.split('/')[0], 0) + 1
        if m.isfile():
            e = os.path.splitext(m.name)[1].lower()
            exts[e] = exts.get(e, 0) + 1
            big.append((m.size, m.name))
except Exception as ex:
    p(f'STREAM ERROR after {count} members: {ex!r}')
p(f'members={count}')
p('top-level: ' + str(sorted(tops.items(), key=lambda x: -x[1])))
p('ext hist: ' + str(sorted(exts.items(), key=lambda x: -x[1])[:25]))
big.sort(reverse=True)
p('biggest 30:')
for s, n in big[:30]:
    p(f'  {s:>12,d}  {n}')
open(os.path.join(OUT, 'app-pkg-filelist.txt'), 'w', encoding='utf-8', errors='replace').write(
    ''.join(f'{s}\t{n}\n' for n, s in names))
kw = re.compile(r'(vpanel|logo|kzb|kanzi|theme|skoda|vw|carplay|carlife|mirrorlink|aap|android|font|gres|startscreen|boot|splash|\.png|\.jpg)', re.I)
p('keyword-matching names (up to 120):')
hits = [n for n, s in names if kw.search(n)]
for n in hits[:120]:
    p('  ' + n)
p(f'(total keyword matches: {len(hits)})')
p()

# ---------------------------------------------------------------- os.bin
OS_OFF = 0x8464239
p('=' * 76)
p(f'## os.bin nested pack @0x{OS_OFF:x}')
p('=' * 76)
f.seek(OS_OFF)
hdr = f.read(0x1000)
sub = []
for off in range(0, 0x1000, 0x200):
    rec = hdr[off:off + 0x200]
    if rec[:4] != b'\x48\x81\x48\x81':
        continue
    val = struct.unpack('<I', rec[4:8])[0]
    name = rec[8:0x28].split(b'\x00')[0].decode('latin1', 'replace')
    ver = rec[0x4c:0x80].split(b'\x00')[0].decode('latin1', 'replace')
    sub.append((off, val, name, ver))
p(f"{'rec':>6} {'value':>14} {'hex':>12}  {'name':<14} version")
for off, val, name, ver in sub:
    p(f'0x{off:04x} {val:>14,} 0x{val:08x}  {name:<14} {ver}')

# dump beginnings of each declared sub-object, resolve absolute offsets
p('\nsub-object data:')
abs_list = []
for off, val, name, ver in sub:
    cand = [off + 0x1000 + val, val]  # relative-to-os.bin or absolute
    for c in cand:
        if 0 < c < SIZE:
            f.seek(c)
            b = f.read(16)
            kind = ('uImage' if b[:4] == b'\x27\x05\x19\x56' else
                    'gzip' if b[:2] == b'\x1f\x8b' else
                    'zeros' if b[:16] == b'\x00' * 16 else b[:8].hex(' '))
            p(f'  {name:<14} val=0x{val:08x} -> try 0x{c:08x}: {kind}')
            abs_list.append((name, c, kind))

# find all uImage headers in os.bin region and dump strings from them
p('\nuImage objects inside os.bin:')
uimgs = []
f.seek(OS_OFF)
blob = f.read()  # os.bin .. EOF (~84 MB) - acceptable
for m in re.finditer(re.escape(b'\x27\x05\x19\x56'), blob):
    i = m.start()
    h = blob[i:i + 64]
    if len(h) < 64:
        continue
    magic, hcrc, ts, size, load, ep, dcrc, os_, arch, typ, comp = struct.unpack('>IIIIIIIBBBB', h[:32])
    if size <= 0 or size > 40_000_000:
        continue
    nm = h[32:64].split(b'\x00')[0].decode('latin1', 'replace')
    if nm and all(32 <= ord(c) < 127 for c in nm):
        uimgs.append((i, size, load, os_, arch, typ, nm))
        p(f'  rel=0x{i:08x} abs=0x{OS_OFF+i:08x} size={size:,} load=0x{load:08x} '
          f'os={os_} arch={arch} type={typ} name={nm!r}')

def strings(data, minlen=6, limit=None, filt=None):
    out = []
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % minlen, data):
        s = m.group().decode('latin1')
        if filt and not filt.search(s):
            continue
        out.append(s)
        if limit and len(out) >= limit:
            break
    return out

# kernel strings -> platform identity
for rel, size, load, os_, arch, typ, nm in uimgs:
    body = blob[rel + 64: rel + 64 + size]
    fn = os.path.join(OUT, re.sub(r'[^A-Za-z0-9._-]', '_', nm)[:60] + '.bin')
    open(fn, 'wb').write(body)
    p(f'\n--- strings from {nm!r} ({size:,} bytes) saved to {os.path.basename(fn)}')
    ints = re.compile(r'(?i)(i\.MX|mx6|imx6|imx-?6q|imx-?6dl|freescale|linux version|gcc version|'
                      r'console=|root=|mtdparts|mem=|ddr|256MB|512MB|1GB|ttymxc|mmcblk|nand|'
                      r'galcore|vivante|tuner|tef|tda|si4|rda|sta|bd3|bluetooth|c300|anw|'
                      r'desay|svp|g5|board|panel|lvds|mipi)', re.I)
    ss = strings(body, 8, None, ints)
    seen = set()
    for s in ss:
        if s in seen:
            continue
        seen.add(s)
        p('   ' + s[:200])
        if len(seen) > 90:
            break

# bootargs / board strings anywhere in os.bin
p('\n--- boot/board related strings across os.bin:')
ss = strings(blob, 10, None, re.compile(r'(?i)(bootargs|bootcmd|mtdparts|mmcblk|/dev/mtd|androidboot|'
                                        r'console=tty|root=/dev|rootfstype|ubi|splash|bootlogo|'
                                        r'c300|c180|c150|desay|g5.*board|mx6|imx6)'))
seen = set()
for s in ss:
    if s in seen:
        continue
    seen.add(s)
    p('   ' + s[:220])
    if len(seen) > 120:
        break

# ---------------------------------------------------------------- radio.bin
RAD = 0x8402309
RAD_END = 0x8464239
p()
p('=' * 76)
p(f'## radio.bin @0x{RAD:x} ({(RAD_END-RAD):,} bytes)')
p('=' * 76)
f.seek(RAD)
radio = f.read(RAD_END - RAD)
open(os.path.join(OUT, 'radio.bin'), 'wb').write(radio)
p('first 64 bytes: ' + radio[:64].hex(' '))
p('ascii: ' + ''.join(chr(c) if 32 <= c < 127 else '.' for c in radio[:64]))
p(f'md5: {hashlib.md5(radio).hexdigest()}  entropy_uniq_bytes={len(set(radio))}')
p('interesting strings:')
ss = strings(radio, 6, None, re.compile(r'(?i)(ver|boot|mcu|dsp|radio|tuner|stm|nxp|renesas|ti |'
                                        r'atmel|checksum|crc|desay|sv|v\d+\.\d+|201[0-9])'))
seen = set()
for s in ss:
    if s in seen:
        continue
    seen.add(s)
    p('   ' + s[:160])
    if len(seen) > 60:
        break
p('\nall printable strings (first 80, len>=8):')
for s in strings(radio, 8, 80):
    p('   ' + s[:160])

open(os.path.join(OUT, 'composition-report.txt'), 'w', encoding='utf-8', errors='replace').write('\n'.join(R))
p('\n[report saved]')
f.close()
