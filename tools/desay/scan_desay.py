import os, re, struct, math, sys, collections

E = r'E:\01 Win Apps\Car Softs\VW Car Radios Firmwares\187B'
TARGETS = {
 'SW0358': E + r'\DessaySv\6RD 035 187B_ SW0358\6RD_035_187B_TR7247_SW0358_20180328.bin',
 'SW0318': E + r'\DessaySv\Desay_0318_Red 2\Desay_0318_Red 2\6RD_035_187B_TR7247_SW0318_20170901.bin',
}

WORDS = [b'Skoda', b'SKODA', b'Volkswagen', b'SEAT', b'AndroidAuto', b'Android Auto', b'androidauto',
         b'aap_', b'AAP', b'CarPlay', b'Carplay', b'carplay', b'CarLife', b'carlife', b'MirrorLink',
         b'Baidu', b'baidu', b'BootLogo', b'bootlogo', b'logo', b'Logo', b'variant', b'Variant',
         b'i.MX', b'imx6', b'IMX6', b'mx6', b'MX6', b'freescale', b'Freescale', b'Desay', b'DESAY',
         b'Telechips', b'tcc8', b'sunplus', b'Sunplus', b'MStar', b'mstar', b'Renesas', b'R-Car',
         b'Tegra', b'QNX', b'WinCE', b'WINCE', b'MIB2', b'mib2', b'uImage', b'squashfs', b'ubifs',
         b'UBI#', b'jffs2', b'cramfs', b'ext4', b'ext3', b'bootloader', b'Bootloader', b'U-Boot', b'uboot',
         b'SHA256', b'RSA', b'PKCS', b'certificate', b'CERT', b'signature', b'verify_image',
         b'PQ', b'PSS', b'GEN2', b'TR7247', b'eMMC', b'NAND', b'spi', b'AVN', b'--red', b'Red']

FS_SIGS = {
 b'\x1f\x8b\x08': 'gzip', b'\xfd7zXZ': 'xz', b'\x42\x5a\x68': 'bzip2', b'\x28\xb5\x2f\xfd': 'zstd',
 b'\x04\x22\x4d\x18': 'lz4', b'\x02\x21\x4c\x18': 'lz4f', b'\x7fELF': 'elf',
 b'\x27\x05\x19\x56': 'uImage', b'hsqs': 'squashfs-le', b'sqsh': 'squashfs-be',
 b'\x45\x3d\xcd\x28': 'cramfs-le', b'\x85\x19\x03\x20': 'jffs2-le', b'\x20\x03\x19\x85': 'jffs2-be',
 b'UBI#': 'ubi', b'UBI!': 'ubifs', b'\x31\x18\x10\x06': 'ubifs-sb',
 b'\x53\xef': 'ext2/3/4-magic', b'ANDROID!': 'android-boot', b'\x89PNG': 'png',
 b'\xff\xd8\xff': 'jpeg', b'BM': 'bmp?', b'PK\x03\x04': 'zip', b'\x1f\x9d': 'compress',
}

def entropy(b):
    if not b: return 0.0
    c = collections.Counter(b)
    n = len(b)
    return -sum((v/n) * math.log2(v/n) for v in c.values())

def scan(path, tag):
    size = os.path.getsize(path)
    print(f'### {tag} size={size}')
    hits = collections.defaultdict(list)
    ent = []
    with open(path, 'rb') as f:
        off = 0
        prev = b''
        while True:
            buf = f.read(4*1024*1024)
            if not buf: break
            data = prev + buf
            base = off - len(prev)
            for w in WORDS:
                s = 0
                while True:
                    i = data.find(w, s)
                    if i < 0: break
                    if len(hits[w]) < 8:
                        hits[w].append(base+i)
                    s = i+1
            for sig, name in FS_SIGS.items():
                s = 0
                while True:
                    i = data.find(sig, s)
                    if i < 0: break
                    # verify plausible alignment for ext magic
                    if name.startswith('ext2') and ((base+i) % 1024) != (0x438 % 1024):
                        s = i+1; continue
                    if len(hits[b'FS:'+name.encode()]) < 12:
                        hits[b'FS:'+name.encode()].append(base+i)
                    s = i+1
            prev = data[-64:]
            off += len(buf)
    # entropy map: reopen and do 1MB
    with open(path, 'rb') as f:
        i = 0
        while True:
            b = f.read(1024*1024)
            if not b: break
            ent.append(round(entropy(b), 2))
            i += 1
    # summarize entropy runs
    print(f'  entropy blocks(MB): n={len(ent)}')
    runs = []
    cur = ent[0]; start = 0
    for idx, v in enumerate(ent[1:], 1):
        if abs(v-cur) > 0.35:
            runs.append((start, idx-1, cur)); start = idx; cur = v
        else:
            cur = (cur*0.75 + v*0.25)
    runs.append((start, len(ent)-1, cur))
    for a,b2,e in runs:
        span = b2-a+1
        if span >= 2:
            print(f'    MB[{a}..{b2}] len={span}MB ent~{e:.2f}')
    print('  word hits:')
    for w in WORDS:
        h = hits.get(w)
        if h:
            print(f'    {w.decode("latin1"):16s} n={len(h)} offs={h[:6]}')
    print('  fs sigs:')
    for k in sorted(hits):
        if k.startswith(b'FS:'):
            print(f'    {k[3:].decode():16s} offs={sorted(hits[k])[:10]}')
    # dump context of top-interest hits
    with open(path,'rb') as f:
        for key in [b'Skoda', b'AndroidAuto', b'CarPlay', b'CarLife', b'MirrorLink', b'aap_', b'logo', b'BootLogo', b'i.MX', b'Desay', b'MIB2']:
            for o in hits.get(key, [])[:3]:
                f.seek(max(0,o-80)); ctx = f.read(200)
                txt = ''.join(chr(c) if 32 <= c < 127 else '.' for c in ctx)
                print(f'    [{key.decode()}] @0x{o:x}: {txt}')
    return hits, ent

for tag, p in TARGETS.items():
    scan(p, tag)
    print()
