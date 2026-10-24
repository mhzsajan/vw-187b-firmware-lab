import tarfile, os, sys, re, collections

E = r'E:\01 Win Apps\Car Softs\VW Car Radios Firmwares\187B'
PACKS = {
 '5314': E + r'\NoName\Skoda\AIO\std_plus_pss-6.5inch_1014 5314  _VW_PQ_GP.tar',
 '5515': E + r'\NoName\Skoda\AIO\std_plus_pss-6.5inch_170421 5515  _VW_PQ_GP.tar',
}
OUT = r'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\noname'
os.makedirs(OUT, exist_ok=True)

def dump(name, data, limit=6000):
    txt = data[:limit].decode('utf-8', 'replace')
    print(f'----- {name} ({len(data)} bytes) -----')
    print(txt)
    print('----- end -----')

for tag, path in PACKS.items():
    print(f'########## PACK {tag}')
    tf = tarfile.open(path, 'r:')
    members = tf.getmembers()
    print(f'members={len(members)} total_bytes={sum(m.size for m in members)/1048576:.1f}MB')
    tops = collections.Counter()
    for m in members:
        tops[m.name.split('/')[0]] += 1
    print('top-level entries:', dict(sorted(tops.items(), key=lambda x: -x[1])))
    big = sorted((m for m in members if m.isfile()), key=lambda m: -m.size)[:25]
    print('biggest files:')
    for m in big:
        print(f'   {m.size:>12,d}  {m.name}')
    # interesting names
    pat = re.compile(r'(hmi|logo|bootlogo|startup|aap|skoda|vw|seat|theme|variant|coding|anim)', re.I)
    inter = [m.name for m in members if pat.search(m.name)]
    print(f'name-pattern matches ({len(inter)}):')
    for n in inter[:120]:
        print('   ', n)
    # media assets
    media = [m for m in members if m.name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.qml', '.qm', '.rcc'))]
    print(f'media members: {len(media)}')
    for m in media[:40]:
        print(f'   {m.size:>10,d}  {m.name}')
    if tag == '5314':
        want = ['config.txt', 'etc/aap_system_attributes.xml', 'etc/rc.d/rc.local', 'etc/rc.d/rcS',
                'etc/fstab', 'etc/inittab', 'etc/profile', 'opt/stdplus.ini',
                'system/script/hmi', 'opt/hmi']
        for w in want:
            try:
                m = tf.getmember(w)
            except KeyError:
                print(f'!! member not found: {w}')
                continue
            data = tf.extractfile(m).read()
            dest = os.path.join(OUT, w.replace('/', '__'))
            with open(dest, 'wb') as f:
                f.write(data)
            if m.size < 24000:
                dump(w, data)
            else:
                print(f'--- {w} is {m.size} bytes; first 200 hex: {data[:200].hex(" ")}')
        # list system/ tree
        sysmem = [m.name for m in members if m.name.startswith('system/')]
        print(f'system/ members: {len(sysmem)}')
        for n in sysmem[:80]:
            print('   ', n)
        optmem = [m for m in members if m.name.startswith('opt/')]
        print(f'opt/ members: {len(optmem)}')
        for m in optmem[:80]:
            print(f'   {m.size:>10,d}  {m.name}')
    tf.close()
    print()
