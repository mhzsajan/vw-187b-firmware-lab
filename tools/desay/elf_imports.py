"""Parse ELF32-ARM dynamic symbols to find HOW the Desay updater validates packages.

No disassembler needed: DT_NEEDED + imported (UND) symbols answer most of it.
- imports MD5_* / only memcmp        -> likely plain md5 compare
- imports RSA_/EVP_Verify/EC_VERIFY -> cryptographic signature
"""
import struct, sys, os

KEY = ('svapi', 'md5', 'sha', 'crc', 'rsa', 'evp', 'sign', 'verify', 'crypt', 'aes', 'hmac', 'memcmp', 'rollback')


def parse(path):
    data = open(path, 'rb').read()
    if data[:4] != b'\x7fELF':
        return {'error': 'not elf'}
    ei_class, ei_data = data[4], data[5]
    if ei_class != 1 or ei_data != 1:
        return {'error': f'expected ELF32 LE, got class={ei_class} data={ei_data}'}
    (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
     e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx) = struct.unpack('<HHIIIIIHHHHHH', data[16:52])
    secs = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        nm, typ, flags, addr, offset, size, link, info, align, entsize = struct.unpack('<IIIIIIIIII', data[off:off + 40])
        secs.append(dict(nm=nm, type=typ, offset=offset, size=size, link=link, entsize=entsize))
    shstr = secs[e_shstrndx]
    def sname(nm):
        b = data[shstr['offset'] + nm:]
        return b[:b.index(b'\x00')].decode('latin1')
    for s in secs:
        s['name'] = sname(s['nm'])
    byname = {s['name']: s for s in secs}

    out = {'machine': e_machine, 'type': e_type, 'sections': [s['name'] for s in secs],
           'needed': [], 'imports': [], 'exports': []}
    if '.dynamic' in byname:
        d = byname['.dynamic']
        dstr = secs[d['link']]
        n = d['size'] // 8
        for i in range(n):
            tag, val = struct.unpack('<iI', data[d['offset'] + i * 8: d['offset'] + i * 8 + 8])
            if tag == 0:
                break
            if tag == 1:  # DT_NEEDED
                b = data[dstr['offset'] + val:]
                out['needed'].append(b[:b.index(b'\x00')].decode('latin1'))
    if '.dynsym' in byname:
        ds = byname['.dynsym']
        dstr = secs[ds['link']]
        cnt = ds['size'] // 16
        for i in range(cnt):
            nm, val, size, info, other, shndx = struct.unpack('<IIIBBH', data[ds['offset'] + i * 16: ds['offset'] + i * 16 + 16])
            b = data[dstr['offset'] + nm:]
            name = b[:b.index(b'\x00')].decode('latin1')
            if not name:
                continue
            if shndx == 0:
                out['imports'].append(name)
            else:
                out['exports'].append(name)
    return out


for path in sys.argv[1:]:
    print('=' * 78)
    print(os.path.basename(path), f'({os.path.getsize(path):,} bytes)')
    r = parse(path)
    if 'error' in r:
        print('  ERROR:', r['error'])
        continue
    print(f"  e_machine={r['machine']} (40=ARM)  e_type={r['type']}")
    print(f"  DT_NEEDED: {r['needed']}")
    print(f"  imports={len(r['imports'])} exports={len(r['exports'])}")
    for label, lst in (('IMPORT', r['imports']), ('EXPORT', r['exports'])):
        hits = [s for s in lst if any(k in s.lower() for k in KEY)]
        print(f'  {label} crypto/verify/update-ish ({len(hits)}):')
        for s in hits[:60]:
            print('     ' + s)
