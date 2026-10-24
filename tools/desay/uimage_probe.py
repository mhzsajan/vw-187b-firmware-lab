import struct, sys, os

E = r'E:\01 Win Apps\Car Softs\VW Car Radios Firmwares\187B'
FILES = {
 'SW0358': E + r'\DessaySv\6RD 035 187B_ SW0358\6RD_035_187B_TR7247_SW0358_20180328.bin',
 'SW0318': E + r'\DessaySv\Desay_0318_Red 2\Desay_0318_Red 2\6RD_035_187B_TR7247_SW0318_20170901.bin',
}

IH_OS = {0:'invalid',1:'OpenBSD',2:'NetBSD',3:'FreeBSD',4:'4.4BSD',5:'Linux',6:'SVR4',7:'Esix',8:'Solaris',9:'Irix',10:'SCO',11:'Dell',12:'NCR',13:'LynxOS',14:'VxWorks',15:'pSOS',16:'QNX',17:'Firmware',18:'RTEMS',19:'ARTOS',20:'Unity',21:'INTEGRITY'}
IH_ARCH = {0:'invalid',1:'alpha',2:'ARM',3:'x86',4:'IA64',5:'MIPS',6:'MIPS64',7:'PowerPC',8:'PowerPC64',9:'SPARC',10:'SPARC64',11:'SuperH',12:'m68k',13:'MicroBlaze',14:'Nios2',15:'Blackfin',16:'AVR32',17:'ST200',18:'Sandbox',19:'NDS32',20:'OpenRISC',21:'ARM64',22:'ARC',23:'x86_64',24:'Xtensa'}
IH_COMP = {0:'none',1:'gzip',2:'bzip2',3:'lzma',4:'lzo',5:'lz4',6:'zstd'}
IH_TYPE = {1:'standalone',2:'kernel',3:'RAMDisk',4:'Multi-File',5:'Firmware',6:'Script',7:'Filesystem',8:'FlatDevTree',9:'Kernel NOLOAD',10:'RAMDiskX',11:'Kernel xip',14:'Kernel FIT',15:'Script FIT'}

def uimage(path, off):
    with open(path,'rb') as f:
        f.seek(off)
        h = f.read(64)
    if len(h) < 64: return None
    magic, hcrc, ts, size, load, ep, dcrc, os_, arch, typ, comp = struct.unpack('>IIIIIIIBBBB', h[:32])
    if magic != 0x27051956: return {'bad':'no magic', 'raw':h[:16].hex(' ')}
    name = h[32:64].split(b'\x00')[0].decode('latin1', 'replace')
    return dict(size=size, load=hex(load), ep=hex(ep), os=IH_OS.get(os_,os_), arch=IH_ARCH.get(arch,arch),
                type=IH_TYPE.get(typ,typ), comp=IH_COMP.get(comp,comp), name=name,
                data_off=off+64, data_end=off+64+size)

ELF_MACH = {3:'x86',8:'MIPS',20:'PowerPC',40:'ARM',62:'x86-64',183:'ARM64',243:'RISC-V'}
ELF_DATA = {1:'LE',2:'BE'}

def elf(path, off):
    with open(path,'rb') as f:
        f.seek(off); h = f.read(64)
    if h[:4] != b'\x7fELF': return {'bad':'no elf'}
    cls, data = h[4], h[5]
    if data == 1:
        etype, mach, ver, entry, phoff = struct.unpack('<HHIIII', h[16:32])
    else:
        etype, mach, ver, entry, phoff = struct.unpack('>HHIIII', h[16:32])
    return dict(cls={1:'32',2:'64'}.get(cls), endian=ELF_DATA.get(data), type=etype,
                machine=ELF_MACH.get(mach, mach), entry=hex(entry), phoff=hex(phoff))

for tag, p in FILES.items():
    print(f'### {tag}: {os.path.basename(p)}')
    offs = []
    with open(p,'rb') as f:
        # find all uImage magics properly
        f.seek(0); data = f.read()
    start = 0
    while True:
        i = data.find(b'\x27\x05\x19\x56', start)
        if i < 0: break
        offs.append(i); start = i+1
    print(f'  uImage magic candidates: {offs}')
    for o in offs:
        r = uimage(p, o)
        print(f'  uImage @{o} (0x{o:x}): {r}')
        if r and 'bad' not in r:
            # verify header CRC and check a decompress window
            import zlib
            with open(p,'rb') as f:
                f.seek(r['data_off']); d0 = f.read(4096)
            if d0[:2] == b'\x1f\x8b':
                try:
                    z = zlib.decompressobj(16+zlib.MAX_WBITS)
                    out = z.decompress(d0, 2048)
                    print(f'     -> gzip payload OK, first bytes: {out[:80]!r}')
                except Exception as e:
                    print(f'     -> gzip decompress fail: {e}')
            else:
                print(f'     -> payload first 32: {d0[:32].hex(" ")}')
    for o in [i for i in range(0, len(data)-4) if False]:
        pass
    # ELF candidates
    eoff = []
    start = 0
    while True:
        i = data.find(b'\x7fELF', start)
        if i < 0: break
        eoff.append(i); start = i+1
    print(f'  ELF candidates: {eoff}')
    for o in eoff:
        print(f'  ELF @{o}: {elf(p,o)}')
    del data
