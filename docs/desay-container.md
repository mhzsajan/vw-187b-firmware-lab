# Desay SV `6RD 035 187B` — `.bin` container notes

Build analysed: `6RD_035_187B_TR7247_SW0358_20180328.bin` (222,167,385 bytes) and
`6RD_035_187B_TR7247_SW0318_20170901.bin` (226,262,078 bytes, "0318_RED").
Both from the owner's firmware set; hashes in `docs/library-manifest.md`.

## 1. Top-level layout

```
0x000000  header record (magic 48 81 48 81, "…SW0358", "mib2", build tag)
0x000800  component record  (magic 48 81 48 81, size 0x083d3a80, name "os.bin",
                             version "MIB2-C-V18-20171207")
0x000fff … 0x1fffff  zero padding (header area is ~336 non-zero bytes in total)
0x200000  payload: valid gzip stream -> tar archive  (the application partition)
   …      further components / kernel / U-Boot image later in the file
0x83d4480 (approx)  U-Boot uImage  "Linux-3.14.57", load 0x80008000, ARM
0x88f5280 (approx)  U-Boot uImage  type Firmware, "U-Boot 2014.07-00209-g36d39ae"
```

Header fields observed (little-endian), from `tools/desay/container_probe.py` output:

| offset | bytes | reading |
|---|---|---|
| `0x00` | `48 81 48 81` | record magic |
| `0x04` | `02 00 00 00` | record type / count |
| `0x08` | `36 52 44 5f …` | ASCII model `6RD_035_187B_TR7247_SW0358` |
| `0x2b` | `6d 69 62 32` | ASCII `mib2` |
| `0x800` | `48 81 48 81` | second record magic |
| `0x804` | `80 3a 3d 08` | `0x083d3a80` = 138,266,240 (component length, matches payload span) |
| `0x808` | `6f 73 2e 62 69 6e` | ASCII `os.bin` component name |
| `0x84c` | `4d 49 42 32 …` | ASCII `MIB2-C-V18-20171207` component version |

The `.md5` sidecars are **not just a hash**: they list component versions and rollback
counters, e.g.

```
deffdeb0c04848354ba65b0e57a68b79  .//6RD_035_187B_TR7247_SW0358_20180328.bin
VERSION:SVP30.6@C1                    ROLL_BACK_NO:1
VERSION:MP2017_PQ_07.30_180328__C     ROLL_BACK_NO:1
VERSION:07.30_180328__C               ROLL_BACK_NO:1
PROJECT:GEN2_PQ_MP2017                ROLL_BACK_NO:1
VERSION:MIB2-C-V18-20171207           ROLL_BACK_NO:5
```

## 2. Payload extraction

The payload at `0x200000` is a plain **gzip** stream (header `1f 8b 08 00 …`, mtime
`1522234714`, OS=3) that decompresses to a **tar** archive whose first member is `./bin/`.

Recipe (see `tools/desay/carve.py`): wrap the file in a seekable slice starting at
`0x200000`, feed it to `gzip.GzipFile`, then `tarfile.open(mode='r|')` and stream members.
No decryption is involved — the application partition is readable.

574 members, ~185 MB of content: `./bin`, `./lib`, `./share`, `./etc`.

## 3. What the application partition contains

- **Services (Desay "SVP" framework):** `exlapservice`, `ilmservice`, `appmgr`, `devicemgr`,
  `btservice`, `tunerservice`, `mediaservice`, `cameraservice`, `powerctrl`, `procguard`,
  `updateservice`, plus test clients (`test.*`).
- **Projection:** `carplayservice` + `libcarplay.so`, `carlifeservice` + `libcarlife*.so` +
  Baidu `share/CarLife/{bdim,bdsc}`, `mirrorlinkservice` + `libmirrorlink.so`.
- **NOT present:** any `aap_*` symbol, Android Auto binary, or head-unit certificate.
  Confirmed by full member inventory — see `docs/evidence/desay-app-partition-filelist.txt`.
- **UI:** Kanzi (`libUICore-kanzi.so`, `libuifw-kanzi.so`, `libGeneralCtrls-kanzi.so`) with
  resource bundles `share/ui/<Brand>_G5_*.kzb` (24 files: Statusbar, Home, Vpanel, Btphone,
  KeyBoard, Setting, Media list, Logo, …). In the analysed build every bundle is `Mazda_G5_*`.
- **Brand assets:** `share/CarPlay/{VW,DesaySV,Mazda}icon_{104,120,180,256}.png`.
  No Skoda asset anywhere.
- **Fonts:** `share/fonts/FZHT_GB18030-{Regular,Light}.ttf` (12 MB each).

### The boot logo

`etc/logo.sh` is an empty hook (all three cases do nothing). `etc/test.sh` starts the UI with
`app-run 19  normal 1   #logo` — the logo is drawn by a UI app from
`share/ui/<Brand>_G5_Logo.kzb`, a compiled Kanzi bundle:

```
2e 4b 5a 42            ".KZB" magic
… "logo" node, embedded PNG at offset 91083, strings: PropertyTypeLibrary, Screens,
  Image Layer, TextureCube, FontDefault, Phong…
```

So unlike the clone, the splash is **not** a raw blob in an MTD partition — it is inside a
compiled UI bundle. Contrast with `tools/theme/render_logo.py` + `docs/noname-platform.md`.

## 4. Update path and validation (why repacking is hard)

`etc/update.sh` dispatches to the compiled `updateservice` with a mode selector:

```
/svp/etc/update.sh apps_only | rmt_only | apps_and_rmt | factory_reset
                     dsp_only | gps_only
```

Symbols observed in `bin/updateservice` and `lib/libupdate.so.1.0.0`
(`docs/evidence/desay-updater-symbols.txt`):

```
svapi_vw_upgrade_package_is_valid    svapi_vw_read_pkg_md5
svapi_vw_read_pkg_md5_info           svapi_vw_upgrade_copy_to_emmc
svapi_vw_rollback_get / _set         CheckRollbackValue / SaveRollBackNoToMU
CheckRowChecksum                     "ERROR: Rollback checksum, will update all"
"OS / SVP / APP / RADIO rollback num:%d"
```

plus component version strings (`UBOOT_VER`, `UIMAGE_VER`, `VIPAP_VER`, `VIPBL_VER`,
`BT_VER`). Interpretation: the unit validates the package (md5-based APIs), enforces
anti-downgrade counters stored in MCU EEPROM ("MU"), and copies to eMMC from a privileged
service.

**Open question:** whether `package_is_valid` is a plain MD5 compare (which we could
recompute, exactly like the shipped `.md5` sidecar) or a cryptographic signature. Answering it
decides whether a modified `.bin` could ever be flashed. See `ROADMAP.md`.

## 5. Rollback safety notes

Rollback counters mean a downgrade or a failed flash is not simply recoverable by flashing an
older file. Any experiment should assume a bench recovery path (U-Boot serial, or the unit's
recovery mode) must be established first.
