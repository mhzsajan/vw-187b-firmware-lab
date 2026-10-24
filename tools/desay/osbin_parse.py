"""Parse the os.bin record table (SW0317) and extract its members.

os.bin layout (observed):
    0x000  header: magic 48 81 48 81 | u32 3 | "G5-R1" | "G5-R1_MIB2-C-V20-20200303" | "G5 platform"
    0x100  record table, 0x80 bytes per record: name(0x20) | u32 offset | u32 size | zeros
           offsets are relative to the start of os.bin
    0x800  first payload byte (mbr.bin)
Members seen: mbr.bin, uImage, dra7-mib2-g-upgrade.dtb, uramdisk.img, MLO, u-boot.img,
dra7-mib2-g.dtb, targetfs.bin, upgrade_uenv.txt, testing_uenv.txt
"""
import os, struct, sys

BIN = r'I:\187B-Firmware-Library\10-Desay-SV-Official\SW0317_2020-03-03\6RD_035_187B_TR7247_SW0317_20200303.bin'
OS_ = 0x8464239
OUT = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\osbin'
os.makedirs(OUT, exist_ok=True)
SIZE = os.path.getsize(BIN)
f = open(BIN, 'rb')

hdr = f.seek(OS_)
f.seek(0)
f.seek(OS_)
head = f.read(0x100)
magic, count = struct.unpack('<II', head[:8])
name = head[8:0x28].split(b'\x00')[0].decode('latin1')
ver = head[0x28:0x60].split(b'\x00')[0].decode('latin1')
print(f'os.bin header: magic=0x{magic:08x} count={count} name={name!r} version={ver!r}')

recs = []
for i in range(0, 40):
    base = OS_ + 0x100 + i * 0x80
    f.seek(base)
    rec = f.read(0x80)
    nm = rec[0:0x20].split(b'\x00')[0].decode('latin1', 'replace')
    if not nm or not nm.isprintable() or rec == b'\x00' * 0x80:
        break
    off, size = struct.unpack('<II', rec[0x20:0x28])
    recs.append((nm, off, size))

print(f'\n{"name":<26} {"offset":>10} {"size":>12}  abs_offset   first bytes / kind')
for nm, off, size in recs:
    abs_off = OS_ + off
    f.seek(abs_off)
    b = f.read(16)
    kind = ('ext4' if b[0x438 - 0x438:2] == b'' else '')
    # identify by magic at the payload start
    sigs = {b'\x53\xef': 'ext-sl?', b'hsqs': 'squashfs', b'\x1f\x8b': 'gzip', b'BZh': 'bzip2',
            b'\xfd7zXZ': 'xz', b'\x27\x05\x19\x56': 'uImage', b'\x7fELF': 'elf',
            b'ustar': 'tar', b'MLO': 'x-loader?', b'\x89PNG': 'png'}
    kind = next((v for k, v in sigs.items() if b.startswith(k)), '')
    if kind == '' and b[:2] in (b'\x00\x00',):
        # possible ext4: superblock 1024 in
        f.seek(abs_off + 1024 + 0x38)
        m = f.read(2)
        if m == b'\x53\xef':
            kind = 'ext4(rootfs?)'
    print(f'{nm:<26} {off:>10,} {size:>12,}  0x{abs_off:x}  {b[:8].hex(" ")}  {kind}')

# extract the interesting members
want = ('targetfs.bin', 'uramdisk.img', 'uImage', 'u-boot.img', 'MLO',
        'dra7-mib2-g.dtb', 'dra7-mib2-g-upgrade.dtb', 'mbr.bin')
for nm, off, size in recs:
    if nm not in want or size <= 0:
        continue
    abs_off = OS_ + off
    if abs_off + size > SIZE:
        print(f'!! {nm}: size overruns EOF, skipping')
        continue
    dest = os.path.join(OUT, os.path.basename(nm))
    f.seek(abs_off)
    remaining = size
    with open(dest, 'wb') as g:
        while remaining > 0:
            chunk = f.read(min(1 << 20, remaining))
            if not chunk:
                break
            g.write(chunk)
            remaining -= len(chunk)
    print(f'extracted {nm} -> {dest} ({os.path.getsize(dest):,} bytes)')

# identify targetfs filesystem type
tf = os.path.join(OUT, 'targetfs.bin')
if os.path.exists(tf):
    print('\ntargetfs.bin identification:')
    with open(tf, 'rb') as g:
        first = g.read(4096)
        g.seek(1024)
        sb = g.read(1024)
    print('  first 32 bytes: ' + first[:32].hex(' '))
    print('  ascii: ' + ''.join(chr(c) if 32 <= c < 127 else '.' for c in first[:32]))
    magic, = struct.unpack('<H', sb[0x38:0x3A])
    if magic == 0xEF53:
        inodes, blocks, _r, _fb, _fi, first_data, log_bs = struct.unpack('<IIIIIII', sb[0:28])
        block = 1024 << (log_bs & 7)
        vol = sb[0x78:0x88].split(b'\x00')[0].decode('latin1', 'replace')
        print(f'  EXT4 superblock OK: block={block} blocks={blocks:,} '
              f'({blocks*block/1048576:.1f} MB) inodes={inodes:,} volume={vol!r}')
    else:
        print(f'  no ext4 superblock at 1024+0x38 (magic 0x{magic:04x})')
f.close()
