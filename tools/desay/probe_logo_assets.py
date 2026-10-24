"""Verify the three findings from usr/bin/logo_os:

1. /usr/share/rvc/logo contents (is the boot logo a data file? what format?)
2. any .avi/.bmp/.png assets in the rootfs that could be the splash
3. per-component md5: are component hashes stored in the container records?
"""
import os, gzip, io, hashlib, re

ROOTFS = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\osbin\rootfs'
BIN = r'I:\187B-Firmware-Library\10-Desay-SV-Official\SW0317_2020-03-03\6RD_035_187B_TR7247_SW0317_20200303.bin'

print('=' * 78)
print('1) /usr/share/rvc tree')
print('=' * 78)
rvc = os.path.join(ROOTFS, 'usr', 'share', 'rvc')
if os.path.isdir(rvc):
    for dp, dn, fn in os.walk(rvc):
        rel = os.path.relpath(dp, ROOTFS)
        print(f'  [DIR] {rel}')
        for f in fn:
            p = os.path.join(dp, f)
            try:
                print(f'        {os.path.getsize(p):>10,d}  {f}')
            except OSError:
                print(f'        {"?":>10}  {f}')
else:
    print(f'  not present: {rvc}')
    # look for any 'rvc' or 'logo' directory elsewhere
    for dp, dn, fn in os.walk(ROOTFS):
        for d in list(dn):
            if d.lower() in ('rvc', 'logo', 'logos'):
                print('  found dir:', os.path.relpath(os.path.join(dp, d), ROOTFS))

print()
print('=' * 78)
print('2) media assets in the rootfs (avi/bmp/png/jpg > 10 KB)')
print('=' * 78)
cnt = 0
for dp, dn, fn in os.walk(ROOTFS):
    for f in fn:
        if not f.lower().endswith(('.avi', '.bmp', '.png', '.jpg', '.jpeg', '.gif')):
            continue
        p = os.path.join(dp, f)
        try:
            sz = os.path.getsize(p)
        except OSError:
            continue
        if sz < 10_000:
            continue
        cnt += 1
        if cnt <= 40:
            print(f'  {sz:>10,d}  {os.path.relpath(p, ROOTFS)}')
print(f'  total: {cnt}')

print()
print('=' * 78)
print('3) per-component md5: stored in the container header?')
print('=' * 78)
COMPONENTS = [
    ('svp.bin', 0x00200000, 0x051EC7FB),
    ('app-pkg.bin', 0x051EC7FB, 0x08402309),
    ('radio.bin', 0x08402309, 0x08464239),
]
f = open(BIN, 'rb')
f.seek(0)
header = f.read(0x200000)          # the 2 MB header area
for name, start, end in COMPONENTS:
    h = hashlib.md5()
    f.seek(start)
    remaining = end - start
    while remaining > 0:
        b = f.read(min(1 << 22, remaining))
        if not b:
            break
        h.update(b)
        remaining -= len(b)
    digest = h.hexdigest()
    raw = bytes.fromhex(digest)
    pos_hex = header.find(digest.encode())
    pos_raw = header.find(raw)
    print(f'  {name:12s} md5={digest}  found_as_ascii_in_header={pos_hex}  found_as_binary={pos_raw}'
          + (f' (0x{pos_raw:x})' if pos_raw >= 0 else ''))
f.close()
