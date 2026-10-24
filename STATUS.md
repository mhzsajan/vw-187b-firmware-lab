# STATUS / HANDOVER — read this first when resuming

Last updated: **2026-10-24** · Repo state: 3 commits, analysis-only (no firmware binaries).

This file is the cold-start entry point. Everything below is either **confirmed** (with the doc
that carries the evidence) or explicitly marked as an **open question**.

---

## 1. Where we are

| Phase | State |
|---|---|
| Platform identification (both vendor families) | **done** |
| Desay: container format, component layout, software stack, hardware BOM | **done** (`docs/desay-hardware.md`) |
| Desay: unit identity + engineering mode | **done** (`docs/desay-unit-identity.md`) |
| NoName: package format, Android Auto stack, Skoda-theme mechanism | **done** (`docs/noname-platform.md`) |
| Feasibility answer (AA / Skoda theme per family) | **done** (`docs/feasibility-report.md`) |
| Desay: package validation (MD5 vs signature) | **done — it is plain `md5sum` vs the sidecar** (`docs/validation-and-repack.md`) |
| Desay: UART/console access, GP-device check, MCU coding | **open — needs hardware** |

## 2. Confirmed findings (one line each, with the source doc)

**Two different products, not one product with features disabled.**

| | Desay SV (owner's installed unit) | NoName / "Tianbao" |
|---|---|---|
| SoC | **TI DRA72x "Jacinto 6"** (Cortex-A15, SGX544, IPU2) | NXP i.MX6 |
| Boot | U-Boot 2014.07-00212-gd0650b9, DTB `dra7-g5-r1.dtb`, board `mib2_g` | U-Boot, kernel 3.0.35, Freescale LTIB |
| OS | **Linux 3.14.57**, `mem=1024M`, `console=ttyS2`, eMMC/SD + ext4 | Linux 3.0.35 LTIB, squashfs/cramfs payloads |
| UI | Qt5 on **Wayland/Weston** + **Kanzi** `.kzb`, per-app `.pkg` (gzip→tar) | monolithic Qt 4.7.4 ELF `opt/hmi` + OVG resources |
| Brand/theme | **per-app Kanzi bundle `VW_MP2017*.kzb`** → theme is a *build variant*, no Skoda asset exists | raw 800×480 splash `dd`'d to `/dev/mtdblock5` (that's the "Skoda theme") |
| Android Auto | **absent**: no `aap_*` stack, no certs, no AA code | **present**: `opt/AndroidAuto/*`, `/etc/aap_dev_hu_*`, `aap_system_attributes.xml` |
| Firmware | single `.bin` (record table + gzip components) + `.md5` sidecar | `.tar` overlay packs, unsigned, shell hooks |
| Update | `updateservice` + `libupdate.so`: md5 API + rollback counters; user-triggered from the unit | copy + `dd`/`cp` scripts, no signing |
| MCU | separate ARM MCU `radio.bin`: Lithio tuner + DSP patches, AKM DSP, **CAN coding**, keys/LED/EEPROM | BT module only (C150/C180/C210/C240 families) |

**Desay container (verified, offsets)**
```
0x000000  5-record table, 0x200 stride: header | svp.bin | app-pkg.bin | radio.bin | os.bin
0x002000  svp.bin        83.8 MB  gzip→tar   userspace (SVP services, Qt5/Wayland, Kanzi, CarPlay/CarLife/MirrorLink)
0x51EC7FB app-pkg.bin    52.5 MB  gzip→tar   17 Kanzi app packages + install.lst
0x8402309 radio.bin       401 KB  raw ARM    MCU firmware (plaintext)
0x8464239 os.bin         83.9 MB  nested     kernel Linux-3.14.57 @+0xA00, U-Boot @+0x51FE00
EOF       md5(whole file) == shipped .md5 sidecar value
```

**Owner's unit:** HW 036 / SW 0317, OS `MIB2-C-V20-20200303`, SVP `SVP30.6@C1`, BT `c300`,
CarPlay `CPL24.V1.4.3@C1`, serial `VWZ6Z2R7343266`, built `20180810` — matches the
`SW0317` image in the library exactly.
**Engineering mode** exists (版本信息 / 系统状态 / keys / EOL Off / 初始化 / screen test / USB-CarPlay /
BT debug…), and System Information has an **`Update software`** button.

**Not Windows CE.** Windows CE does not boot with U-Boot + `dra7-g5-r1.dtb`, ext4/eMMC, `ttyS2`
bootargs, Qt5/Wayland and ELF ARM libraries. The "256 MB / WinCE" description belongs to some
other 187B revision, not this one (this unit is 1 GB).

## 3. Open questions (ordered)

1. ~~Is `svapi_vw_upgrade_package_is_valid` a plain whole-file MD5 or a signature?~~
   **ANSWERED: plain `md5sum`.** It shells out `md5sum <pkg> > /tmp/upgrade.md5`, parses the
   sidecar (`%s.md5`) and compares (`error: %s md5 no match` → `package unvalid`). No libcrypto,
   no certificates, no signature. Evidence: `docs/validation-and-repack.md`.
   Follow-ups now: (a) what does `CheckRowChecksum` in `updateservice` actually verify?
   (b) do the `VERSION:`/`ROLL_BACK_NO:` comparisons allow reflashing the same versions
   (`"%s is match, no upgrade"` suggests it is a no-op skip)?
2. Where is the **rollback counter** live (`CheckRollbackValue` / `SaveRollBackNoToMU`) and can it
   be read/written from Linux (`persistservice`)?
3. Is the DRA72x a **GP (unsigned boot) device**? (uImages carry no signature → likely yes.)
4. **UART `ttyS2` pads** — where are they on the mainboard, and is the console enabled?
5. What do U-Boot bootargs `upgrade=1` / `testing=1` change in userspace?
6. Does a **Skoda-branded G5 build** (`SK_MP2017*.kzb`) exist on the aftermarket to obtain?
7. On-screen checksums `0xc473` (radio SW) / `0xda8c` (bootloader) — algorithm unknown; they are
   not raw header fields and not CRC16 of the obvious windows.
8. Does **any** Desay 187B revision actually run Windows CE? The common online explanation says
   so; this unit is Linux (proof in `docs/why-no-custom-firmware.md`). Unverified whether a WinCE
   revision exists under a different HW/SW number.

## 4. Where the data lives (not in this repo)

| What | Where | Notes |
|---|---|---|
| Firmware library (3.87 GB, 36 files) | `I:\187B-Firmware-Library\` | `10-Desay-SV-Official`, `20-NoName-Tianbao`, `30-Mods-Patches`, `40-Original-Archives`, `50-Analysis`; index in `00-MANIFEST.md` / `00-INVENTORY.csv` |
| Unit screenshots (source) | `I:\187B-Firmware-Library\Screenshot\` | copies committed under `docs/assets/screenshots/` |
| Working extracts / probe logs | DSH workspace `…\187b\` (`desay/`, `noname/`, `theme/`, `notes/`, `composition/`) | **not** versioned; regenerate with the tools in this repo |
| Firmware binaries | **never in git**; `.gitignore` enforces it | keep them on local disks only |

Recreating a component from the library:
```python
# svp.bin / app-pkg.bin: seek to the component offset, wrap in a seekable slice,
# gzip.GzipFile(...) -> tarfile.open(mode='r|')    (see tools/desay/carve.py)
# radio.bin: raw read 0x8402309..0x8464239
# os.bin:   nested record table, then uImage parse (see tools/desay/composition_dump.py)
```
Offsets are build-specific — re-derive from the record table with
`tools/desay/verify_container.py` for any other `.bin`.

## 5. Environment notes (gotchas)

- Shell here is **Windows PowerShell 5.1**, not pwsh 7. Scripts must be **ASCII-only** (no
  Cyrillic/UTF-8 literals) or the parser mangles them; `-AsByteStream` is unavailable.
- Python: use the DSH runtime interpreter (`…\dependencies\python\python.exe`); Pillow and numpy
  are available. Capstone is **not** installed — needed for the `libupdate.so` disassembly task.
- **git push** from the sandboxed shell fails: schannel cannot acquire credentials and the `gh`
  credential helper needs named pipes. Working recipe:
  ```powershell
  $tok = (gh auth token); $b64 = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("x-access-token:$tok"))
  git -c credential.helper= -c http.sslBackend=openssl -c http.version=HTTP/1.1 `
      -c "http.extraheader=AUTHORIZATION: basic $b64" push origin main
  ```
  (run with unrestricted sandbox mode; may need one retry on transient GitHub connect errors).
- Some source firmware files on `E:` are ACL-locked (Administrators only). Solace: the elevated
  copy in `tools/arrange/` produces readable, hash-verified copies; library on `I:` is readable.
- Repository conventions: evidence-first (file + offset → claim), mark **observed** vs
  **inferred**, keep both vendor families strictly separate, never ship firmware/vendor assets.

## 6. Suggested next actions

1. Install Capstone, disassemble `svapi_vw_upgrade_package_is_valid` → answer open question #1.
   (`pip install capstone` in the DSH Python runtime.)
2. Photo/inspect the mainboard for `ttyS2` pads → capture a read-only U-Boot boot log.
3. Bench CAN harness (radio + 12 V + CAN H/L + VCDS/OBDeleven) → dump MCU coding values.
4. If a Skoda G5 build appears, verify it with the same toolchain before any flashing.
5. Optional: `tools/theme/render_logo.py` reverse direction (PNG → `logo.bin`) + overlay-tar
   packer for the NoName family.

## 7. Commit log

| commit | content |
|---|---|
| `23879cd` | initial: feasibility report, container notes, tools, library manifest |
| `73a361b` | Desay container table decoded; unit identity + engineering mode; screenshots |
| `5a35234` | full hardware/software dossier; platform corrected to TI DRA72x |
