# Desay SV `6RD 035 187B` — `.bin` container notes

Build analysed: `6RD_035_187B_TR7247_SW0317_20200303.bin` (222,740,754 bytes) — **this is the
build the owner's unit is actually running** (see `docs/desay-unit-identity.md`), plus
`…_SW0358_20180328.bin` and `…_SW0318_20170901.bin` ("0318_RED").

## 1. Verified container structure

The first 2 MB is a header area containing a **record table**, 0x200 bytes per record:

```
0x000000  record 0 : magic 48 81 48 81 | u32 = 2 (record count) | name = <file>.bin | "mib2"
0x000200  record 1 : svp.bin      | u32 = 0x00200000 =     2,097,152  (start offset) | SVP30.6@C1
0x000400  record 2 : app-pkg.bin  | u32 = 0x051EC7FB =    85,903,355                 | MP2017_PQ_07.54_200303__C
0x000600  record 3 : radio.bin    | u32 = 0x08402309 =   138,421,001                 | 07.54_200303__C
0x000800  record 4 : os.bin       | u32 = 0x08464239 =   138,822,201                 | MIB2-C-V20-20200303
0x000A00 … 0x1FFFFF  zero padding
```

Each record: `magic(4) | u32 absolute start offset(4) | name(0x20, NUL padded) | … | version @+0x4C`.

The start offsets are **cumulative boundaries**, and every one was validated against the data
(`tools/desay/verify_container.py`, output in
`docs/evidence/desay-container-components.txt`):

| component | span | size | first bytes | interpretation |
|---|---|---|---|---|
| `svp.bin` | `0x200000` – `0x51EC7FB` | 83.8 MB | `1f 8b 08 00` | **gzip → tar**: SVP service framework, Kanzi UI, CarPlay/CarLife/MirrorLink libs, `share/ui/*.kzb` |
| `app-pkg.bin` | `0x51EC7FB` – `0x8402309` | 52.5 MB | `1f 8b 08 00` | **gzip → tar**: application package (not yet extracted) |
| `radio.bin` | `0x8402309` – `0x8464239` | 401,200 | `d0 65 42 20 51 07 40 00` | raw **radio/MCU firmware** (not gzip) |
| `os.bin` | `0x8464239` – EOF | 83.9 MB | `48 81 48 81 03 00 00 00` | **nested pack with its own record table** (count 3): kernel / U-Boot / OS image |

Notes:

- `os.bin` starts with the same magic + a count of `3`, so the format is recursive. The kernel
  uImage appears at `0x08464C39` (`+0xA00` into `os.bin`):
  `Linux-3.14.57`, load `0x80008000`, ARM, type 2 (kernel).
- `svp.bin` is what earlier notes called "the application partition" — the `carve.py` extraction
  of `0x200000` walked **svp.bin**, not `os.bin`. It is the userspace filesystem
  (`bin/`, `lib/`, `share/`, `etc/`).
- **Whole-file MD5**: `c7d9bd20d4eaa929d91e4dcbe75bfba3` = exactly the value in the shipped
  `.md5` sidecar. So the sidecar hash covers the **entire `.bin`**, not a component.
- The `.md5` sidecar additionally lists `VERSION:` / `ROLL_BACK_NO:` pairs per component —
  the same strings the unit shows on its Version information screen.

## 2. Component extraction recipes

All components are plain gzip (except `radio.bin` and `os.bin`), so no decryption is involved.

```python
# svp.bin (userspace) — what tools/desay/carve.py does
start = 0x00200000
# app-pkg.bin
start = 0x051EC7FB
# wrap the file in a seekable slice, gzip.GzipFile(fileobj=slice), tarfile.open(mode='r|')
```

`radio.bin` is a flat firmware image (401,200 bytes, non-gzip) and `os.bin` needs its own record
table parsed before extracting its three sub-components.

## 3. What `svp.bin` contains (574 members)

- **Services (Desay "SVP" framework):** `exlapservice`, `ilmservice`, `appmgr`, `devicemgr`,
  `btservice`, `tunerservice`, `mediaservice`, `cameraservice`, `powerctrl`, `procguard`,
  `updateservice`, plus test clients (`test.*`).
- **Projection:** `carplayservice` + `libcarplay.so`, `carlifeservice` + `libcarlife*.so` +
  Baidu `share/CarLife/{bdim,bdsc}`, `mirrorlinkservice` + `libmirrorlink.so`.
- **NOT present:** any `aap_*` symbol, Android Auto binary, or head-unit certificate.
  Confirmed by full member inventory — `docs/evidence/desay-app-partition-filelist.txt`.
- **UI:** Kanzi (`libUICore-kanzi.so`, `libuifw-kanzi.so`, `libGeneralCtrls-kanzi.so`) with
  resource bundles `share/ui/<Brand>_G5_*.kzb` (24 files: Statusbar, Home, Vpanel, Btphone,
  KeyBoard, Setting, Media list, Logo, …). In this build every bundle is `Mazda_G5_*`.
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

plus component version strings (`UBOOT_VER`, `UIMAGE_VER`, `VIPAP_VER`, `VIPBL_VER`, `BT_VER`).
Interpretation: the unit validates the package (md5-based APIs, and the whole-file MD5 is known
to us), enforces anti-downgrade counters stored in MCU EEPROM ("MU"), and copies to eMMC from a
privileged service. The update is user-triggered from the unit's own System Information screen
("Update software").

**Open questions**
- Is `svapi_vw_upgrade_package_is_valid` merely `md5(file) == sidecar` (then a repack is
  feasible with a recomputed md5 + untouched rollback numbers), or is there a signature?
- Where exactly is the rollback counter stored, and does `CheckRollbackValue` compare only
  `ROLL_BACK_NO` values from the sidecar?
- What are the on-screen checksums `0xc473` (radio SW) and `0xda8c` (bootloader)? Verified as
  *not* a stored header field; common CRC16 variants over the obvious windows did not match yet.
  Reproducing them would tell us what else a modified package must satisfy.

## 5. Rollback safety notes

Rollback counters mean a downgrade or a failed flash is not simply recoverable by flashing an
older file. Any experiment should assume a bench recovery path (U-Boot serial, or the unit's
recovery mode) must be established first.
