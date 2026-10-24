import struct, zlib, re, os, collections, math

P = r'E:\01 Win Apps\Car Softs\VW Car Radios Firmwares\187B\DessaySv\6RD 035 187B_ SW0358\6RD_035_187B_TR7247_SW0358_20180328.bin'
size = os.path.getsize(P)
print(f'size={size}')

def dump(off, n, label):
    with open(P,'rb') as f:
        f.seek(off); b = f.read(n)
    print(f'--- {label} @0x{off:x} ({n}B)')
    for i in range(0, len(b), 16):
        row = b[i:i+16]
        hx = ' '.join(f'{c:02x}' for c in row)
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in row)
        print(f'  {off+i:08x}  {hx:<48}  {asc}')

dump(0, 0x120, 'header start')
dump(0x800, 0x100, 'around os.bin ref')
dump(0x200000, 0x100, 'payload start 0x200000')

# gzip stream check at 0x200000
with open(P,'rb') as f:
    f.seek(0x200000); g = f.read(65536)
print('gzip hdr bytes:', g[:10].hex(' '))
if g[:2] == b'\x1f\x8b':
    cm, flg = g[2], g[3]
    mtime = struct.unpack('<I', g[4:8])[0]
    xfl, osb = g[8], g[9]
    print(f'  CM={cm} FLG=0x{flg:02x} MTIME={mtime} XFL={xfl} OS={osb}')
    try:
        z = zlib.decompressobj(16 + zlib.MAX_WBITS)
        out = z.decompress(g[:200000], 4096)
        print(f'  decompressed first 256: {out[:256]!r}')
        print(f'  decompressed total(partial)={len(out)}')
    except Exception as e:
        print(f'  gzip fail: {e}')

def ent(b):
    c = collections.Counter(b); n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

print('--- 64KB entropy profile first 16MB')
with open(P,'rb') as f:
    f.seek(0); i = 0
    out = []
    while i < 16*1024*1024:
        b = f.read(65536)
        if not b: break
        out.append((i, round(ent(b),2), b[:8].hex(' ')))
        i += 65536
for o,e,m in out[:24]:
    print(f'   0x{o:07x} ent={e:5.2f} {m}')
print('   ...')
for o,e,m in out[-8:]:
    print(f'   0x{o:07x} ent={e:5.2f} {m}')

# zlib-compressibility test: sampled 1MB blocks
print('--- sampled compressibility (zlib level 1, 1MB blocks)')
with open(P,'rb') as f:
    for off in [0x200000, 0x400000, 0x1000000, 0x2000000, 0x4000000, 0x6000000, 0x7f00000, 0x8000000, 0x8200000, 0x8300000, 0x8500000, 0x8800000, 0x8d00000]:
        f.seek(off); b = f.read(1024*1024)
        if len(b) < 1024: continue
        c = zlib.compress(b, 1)
        print(f'   0x{off:07x} ratio={len(c)/len(b):.3f} ent={ent(b):.2f}')

# ASCII strings in the 0x82F0000..0x8A00000 plaintext-ish descriptor region
print('--- strings 0x82F0000-0x8A00000 (len>=6)')
with open(P,'rb') as f:
    f.seek(0x82F0000); blob = f.read(0x8A00000-0x82F0000)
pat = re.compile(rb'[\x20-\x7e]{6,}')
strs = [m.group().decode('latin1') for m in pat.finditer(blob)]
print(f'   count={len(strs)} uniq={len(set(strs))}')
kw = re.compile(r'(\.bin|\.img|\.so|uci|imx|mx6|g5|desay|mib2|boot|os\.|app|root|user|data|part|sig|md5|sha|ver|kernel|u-boot|qnx|linux|logo|skoda|vw|seat|carplay|aap|android)', re.I)
sel = [s for s in strs if kw.search(s)]
seen = set(); uniq = []
for s in sel:
    if s not in seen:
        seen.add(s); uniq.append(s)
print(f'   keyword-matching uniq={len(uniq)}; showing up to 250:')
for s in uniq[:250]:
    print('     ', s)

# context around AAP hits
print('--- AAP hit contexts')
with open(P,'rb') as f:
    for off in [12234913, 48509477, 55998620, 60426575, 67270828, 75340856]:
        f.seek(max(0, off-64)); b = f.read(160)
        print(f'   @0x{off:x}: ' + ''.join(chr(c) if 32 <= c < 127 else '.' for c in b))
    f.seek(138038356-128); b = f.read(320)
    print('   [Carplay] @0x83a3254: ' + ''.join(chr(c) if 32 <= c < 127 else '.' for c in b))
    f.seek(137834928-64); b = f.read(200)
    print('   [GEN2] @0x8378d30: ' + ''.join(chr(c) if 32 <= c < 127 else '.' for c in b))
