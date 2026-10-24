import sys, os, struct, json

MAGICS = [
    (b'\x1f\x8b\x08', 'gzip'),
    (b'\xfd7zXZ\x00', 'xz'),
    (b'BZh', 'bzip2'),
    (b'\x28\xb5\x2f\xfd', 'zstd'),
    (b'\x04\x22\x4d\x18', 'lz4-legacy'),
    (b'\x02\x21\x4c\x18', 'lz4'),
    (b'ANDROID!', 'android_bootimg'),
    (b'UBI#', 'ubi'),
    (b'\x27\x05\x19\x56', 'uImage'),
    (b'hsqs', 'squashfs'),
    (b'\x45\x3d\xcd\x28', 'cramfs_le'),
    (b'\x28\xcd\x3d\x45', 'cramfs_be'),
    (b'\x85\x19\x03\x20', 'jffs2'),
    (b'\x7fELF', 'elf'),
    (b'ustar', 'tar'),
    (b'\x55\xaa', 'mbr_sig'),
    (b'EFI PART', 'gpt'),
    (b'\x64\x00\x00\x00', 'sparse?'),
    (b'QNX', 'qnx'),
    (b'Rar!', 'rar'),
    (b'PK\x03\x04', 'zip'),
    (b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 'zeros16'),
]

def scan(path, chunk=8*1024*1024, max_hits=40):
    size = os.path.getsize(path)
    found = {}
    with open(path, 'rb') as f:
        off = 0
        prev_tail = b''
        while off < size:
            buf = f.read(chunk)
            if not buf:
                break
            data = prev_tail + buf
            base = off - len(prev_tail)
            for m, name in MAGICS:
                start = 0
                while True:
                    i = data.find(m, start)
                    if i < 0:
                        break
                    pos = base + i
                    found.setdefault(name, []).append(pos)
                    start = i + 1
                    if len(found[name]) >= max_hits:
                        break
            prev_tail = data[-256:]
            off += len(buf)
    return size, found

def hexdump_preview(path, offs, n=64):
    out = {}
    with open(path, 'rb') as f:
        for o in offs:
            f.seek(o)
            b = f.read(n)
            out[o] = b.hex(' ')
    return out

if __name__ == '__main__':
    for p in sys.argv[1:]:
        try:
            size, found = scan(p)
        except Exception as e:
            print(f'=== {p}\n    ERROR {e}')
            continue
        print(f'=== {p}')
        print(f'    size={size} ({size/1048576:.1f} MB)')
        order = ['gzip','xz','bzip2','zstd','lz4','lz4-legacy','android_bootimg','uImage','ubi','squashfs','cramfs_le','cramfs_be','jffs2','elf','tar','mbr_sig','gpt','sparse?','qnx','rar','zip']
        for name in order:
            if name in found:
                v = found[name]
                print(f'    {name:16s} n={len(v):3d} first={v[:8]}')
        prev = hexdump_preview(p, [0])
        print(f'    @0: {prev[0]}')
