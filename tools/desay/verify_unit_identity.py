"""Verify the on-screen identity/checksums of the Desay unit against the SW0317 image.

Unit screen reports (photos in I:\\187B-Firmware-Library\\Screenshot):
    HW/SW Version             036/0317
    Radio SW version          Std+ MP2017_PQ_07.54_200303__C
    Radio SW checksum         0xc473
    SVP Version               SVP30.6@C1
    OS Version                MIB2-C-V20-20200303
    RadioBootloader Version   BOOT_2016.09.18
    RadioBootloader Checksum  0xda8c
    Bluetooth                 c300
    Apple CarPlay             CPL24.V1.4.3@C1
    Serial                    VWZ6Z2R7343266
    Production date           20180810
"""
import os, struct, re

P = r'I:\187B-Firmware-Library\10-Desay-SV-Official\SW0317_2020-03-03\6RD_035_187B_TR7247_SW0317_20200303.bin'
size = os.path.getsize(P)
print(f'file   = {os.path.basename(P)}')
print(f'size   = {size:,} bytes')

def dump(off, n, label):
    with open(P, 'rb') as f:
        f.seek(off); b = f.read(n)
    print(f'\n--- {label} @0x{off:x} ({n} B)')
    for i in range(0, len(b), 16):
        row = b[i:i+16]
        print(f'  {off+i:08x}  {" ".join(f"{c:02x}" for c in row):<48}  '
              f'{"".join(chr(c) if 32 <= c < 127 else "." for c in row)}')

dump(0, 0x120, 'header record 0')
# find all pack-entry magics in the header area
with open(P, 'rb') as f:
    head = f.read(0x200000)
recs = [m.start() for m in re.finditer(re.escape(b'\x48\x81\x48\x81'), head)]
print(f'\npack record magics in first 2 MB: {[hex(r) for r in recs]}')
for r in recs[:8]:
    rec = head[r:r+0x100]
    f1 = struct.unpack('<I', rec[4:8])[0]
    names = [x.decode('latin1') for x in re.findall(rb'[\x20-\x7e]{4,}', rec)]
    print(f'  @0x{r:x} u32@+4=0x{f1:08x} ({f1:,})  strings={names[:4]}')

# checksums reported by the unit
targets = {'radio_sw 0xc473': b'\x73\xc4', 'radio_bl 0xda8c': b'\x8c\xda'}
for label, pat in targets.items():
    hits = []
    with open(P, 'rb') as f:
        off = 0
        while True:
            chunk = f.read(1 << 22)
            if not chunk:
                break
            start = 0
            while True:
                i = chunk.find(pat, start)
                if i < 0:
                    break
                hits.append(off + i)
                start = i + 1
                if len(hits) > 40:
                    break
            off += len(chunk)
            if len(hits) > 40:
                break
    near = [h for h in hits if h < 0x200000]
    print(f'\n{label}: total hits={len(hits)}  in header area(<0x200000)={[hex(x) for x in near]}')
    for h in near[:8]:
        with open(P, 'rb') as f:
            f.seek(max(0, h - 24)); ctx = f.read(72)
        print(f'   @0x{h:x} ctx: ' + ' '.join(f'{c:02x}' for c in ctx))
        print(f'              asc: ' + ''.join(chr(c) if 32 <= c < 127 else '.' for c in ctx))

# version strings from the .md5 sidecar must appear in the image
for s in [b'SVP30.6@C1', b'MP2017_PQ_07.54_200303__C', b'MIB2-C-V20-20200303', b'GEN2_PQ_MP2017',
          b'BOOT_2016.09.18', b'CPL24.V1.4.3@C1', b'VWZ6Z2R7343266']:
    with open(P, 'rb') as f:
        data = f.read()
    i = data.find(s)
    print(f'  {s.decode():32s} first_offset={hex(i) if i >= 0 else "NOT FOUND"}')
