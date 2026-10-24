import gzip, tarfile, io, os

P = r'C:\Users\o0o\AppData\Local\Temp\..\..\..\..\..\E'  # placeholder, unused
DESAY = r'E:\01 Win Apps\Car Softs\VW Car Radios Firmwares\187B\DessaySv\6RD 035 187B_ SW0358\6RD_035_187B_TR7247_SW0358_20180328.bin'
DESAY = 'I:\\187B-Firmware-Library\\10-Desay-SV-Official\\SW0358_2018-03-28\\6RD_035_187B_TR7247_SW0358_20180328.bin'
OUT = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\desay\rootfs'
os.makedirs(OUT, exist_ok=True)

class Slice(io.RawIOBase):
    def __init__(self, f, start):
        self.f = f; self.start = start; self.pos = 0
    def readable(self): return True
    def seekable(self): return True
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off
        return self.pos
    def tell(self): return self.pos
    def read(self, n=-1):
        self.f.seek(self.start + self.pos)
        d = self.f.read() if (n is None or n < 0) else self.f.read(n)
        self.pos += len(d); return d
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

WANT = {
 './etc/logo.sh', './etc/update.sh', './etc/init.sh', './etc/env_setup.sh', './etc/servicestart.sh',
 './etc/app.conf', './etc/appstart.sh', './etc/run-arm.sh', './etc/source.conf', './etc/ilm.conf',
 './etc/test.sh', './etc/func_env.sh', './share/AccountInfo.txt', './etc/hardkey.conf',
}
f = open(DESAY, 'rb')
gz = gzip.GzipFile(fileobj=io.BufferedReader(Slice(f, 0x200000), buffer_size=1 << 20), mode='rb')
tf = tarfile.open(fileobj=gz, mode='r|')
found = {}
for m in tf:
    if m.name in WANT and m.isfile():
        found[m.name] = tf.extractfile(m).read()
for n, d in found.items():
    fn = os.path.join(OUT, n.replace('./', '').replace('/', '__'))
    open(fn, 'wb').write(d)
    print(f'\n########## {n}  ({len(d)} bytes)')
    try:
        print(d.decode('utf-8'))
    except UnicodeDecodeError:
        print(d.decode('latin1'))
