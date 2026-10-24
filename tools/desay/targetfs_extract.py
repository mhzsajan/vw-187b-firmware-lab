"""Decompress targetfs.bin to a filesystem image, dump the U-Boot upgrade/testing envs, describe FS."""
import gzip, io, os, struct, sys

if hasattr(sys, 'set_int_max_str_digits'):
    sys.set_int_max_str_digits(20000)

OSB = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\osbin'
BIN = r'I:\187B-Firmware-Library\10-Desay-SV-Official\SW0317_2020-03-03\6RD_035_187B_TR7247_SW0317_20200303.bin'

# the two uenv files (absolute offsets from the os.bin table)
for name, abs_off, size in (('upgrade_uenv.txt', 0xD46BE39, 217), ('testing_uenv.txt', 0xD46C039, 217)):
    with open(BIN, 'rb') as f:
        f.seek(abs_off)
        data = f.read(size)
    print('=' * 70)
    print(f'{name}  ({size} B @0x{abs_off:x})')
    print('=' * 70)
    print(data.decode('utf-8', 'replace').replace('\x00', ''))
    print()

img = os.path.join(OSB, 'targetfs.img')
src = os.path.join(OSB, 'targetfs.bin')
if not os.path.exists(img) or os.path.getsize(img) == 0:
    print('decompressing targetfs.bin -> targetfs.img ...')
    with open(src, 'rb') as fi, open(img, 'wb') as fo:
        gz = gzip.GzipFile(fileobj=io.BufferedReader(fi, buffer_size=1 << 20), mode='rb')
        total = 0
        while True:
            chunk = gz.read(1 << 22)
            if not chunk:
                break
            fo.write(chunk)
            total += len(chunk)
    print(f'  wrote {total:,} bytes -> {img}')
else:
    print(f'image already present: {os.path.getsize(img):,} bytes')

with open(img, 'rb') as g:
    head = g.read(4096)
    g.seek(1024)
    sb = g.read(1024)

print('first 32: ' + head[:32].hex(' '))
magic, = struct.unpack('<H', sb[0x38:0x3A])
print(f'ext4 magic at 1024+0x38 = 0x{magic:04x}  (expect 0xef53)')
if magic == 0xEF53:
    inodes, blocks, _r, _fb, _fi, first_data, log_bs = struct.unpack('<IIIIIII', sb[0:28])
    block = 1024 << (log_bs & 7)
    vol = sb[0x78:0x88].split(b'\x00')[0].decode('latin1', 'replace')
    last = sb[0x88:0xC8].split(b'\x00')[0].decode('latin1', 'replace')
    print(f'  EXT4: block={block} blocks={blocks:,} ({blocks*block/1048576:.1f} MB) '
          f'inodes={inodes:,} volume={vol!r} last_mounted={last!r}')
    print(f'  image size {os.path.getsize(img):,} bytes')
else:
    print('  not ext4; first nonzero: ', end='')
    for i, b in enumerate(head):
        if b:
            print(f'offset {i} = {b:02x}')
            break
