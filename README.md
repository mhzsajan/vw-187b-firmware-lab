# VW 187B firmware lab (`6RD 035 187B`, RCD330 family)

Reverse-engineering notes and tooling for the VW PQ-platform 6.5" radio **6RD 035 187B**,
with one concrete development goal:

> **Put a "Welcome to SKODA" start-up screen on the Desay unit installed in the owner's car,
> using a self-made, md5-valid firmware package, flashed only after a verified backup and
> recovery path exists.**

This repository contains the analysis, the evidence and the tooling. It does **not** contain
firmware binaries (see Ground rules).

Start here when resuming: **[`STATUS.md`](STATUS.md)** (state, open questions, next actions)
and **[`docs/desay-action-plan.md`](docs/desay-action-plan.md)** (the plan).

---

## 1. Two different radios - do not confuse them

Both are sold as "187B", but they are different products, not one product with features switched off:

| | **Desay SV** (this project's target) | **NoName / "Tianbao"** (reference only) |
|---|---|---|
| Firmware | single `.bin` + `.md5` sidecar (`6RD_035_187B_TR7247_SW03xx...`) | `.tar` overlay packs (`std_plus_pss-6.5inch_*`) |
| SoC / OS | **TI DRA72x "Jacinto 6"**, Linux **3.14.57**, 1 GB RAM | NXP i.MX6, Freescale LTIB, Linux **3.0.35** |
| Boot | U-Boot 2014.07, board `mib2_g`, DTB `dra7-mib2-g.dtb`, `console=ttyS2` | U-Boot, kernel 3.0.35, squashfs/cramfs payloads |
| UI | Qt5 + Wayland/Weston + **Kanzi** (`VW_MP2017*.kzb`), apps as `.pkg` | monolithic Qt 4.7.4 `opt/hmi` + OVG graphic resources |
| Update | compiled `updateservice` + `libsvapi_vw`: **`md5sum` check**, no signature, rollback counters | plain tar + `/bin/sh` hooks, unsigned, no version gate |
| Android Auto | **absent** (no stack, no head-unit certificate) | **present** (`opt/AndroidAuto/*`, `/etc/aap_dev_hu_*`) |
| Start screen | **plain PPM files in the rootfs** (data - modifiable, see below) | plain PNGs + raw splash `dd`'d to `/dev/mtdblock5` |
| Cross-flash | **never** - different bootloader, kernel, partitions | **never** |

---

## 2. What is settled (verified from the firmware itself)

- **Container**: 5 records -> `svp.bin` (userspace), `app-pkg.bin` (17 Kanzi apps), `radio.bin`
  (MCU firmware), `os.bin` (nested 14-member pack with kernel, DTBs, MLO, U-Boot, `targetfs.bin`).
  Whole-file MD5 equals the shipped `.md5`. See [`docs/desay-container.md`](docs/desay-container.md).
- **Update validation**: `svapi_vw_upgrade_package_is_valid` shells out
  `md5sum <pkg> > /tmp/upgrade.md5`, compares with the sidecar and rejects mismatches.
  **No signature, no certificates, no crypto dependency.** See
  [`docs/validation-and-repack.md`](docs/validation-and-repack.md).
- **Root filesystem**: `os.bin` -> `targetfs.bin` -> gzip -> 227 MB ext4, extractable offline.
  It contains `/usr/lib/libsvapi_vw.so.1.4.0` (the validator) and the boot assets.
- **Start screen**: `/usr/share/rvc/logo/Startscreen_*.ppm`, 13 files, each
  **1,536,015 bytes** = `P6\n800 480\n255\n` + 1,152,000 B RGB + 384,000 B zero padding.
  Selected by a logo index in NOR; replacing **all 13** makes the change index-proof.
- **Skoda payload**: generated and round-trip verified
  (`tools/desay/make_startscreen_ppm.py`, payload md5 `079a5ec0a7d8af3493a5a969defe8aaf`).
- **Reference**: the NoName "Skoda theme" pack is the same "Welcome to ..." 800x480 artwork
  rebranded into every slot - see [`docs/skoda-theme-analysis.md`](docs/skoda-theme-analysis.md).

## 3. What is achievable on the target unit

| Capability | Verdict |
|---|---|
| Skoda start-up screen (the visible splash) | **yes** - data swap inside `targetfs.img`, then rebuild the package |
| Skoda CarPlay OEM icon / start animation | **yes** - plain PNG (`svp.bin`) and `opening_ttl.avi` (`targetfs.img`) |
| Diagnostics, engineering mode, UART console | yes (UART needs board access) |
| Skoda in-unit UI theme (menus, colours) | **no** - compiled Kanzi bundles, would need Kanzi Studio |
| Android Auto | **no** - no AA stack and no HU certificate; use a CarPlay-to-AA adapter |
| MCU/radio behaviour changes, custom OS | technically possible, **high risk**, out of scope |

Full ranking and risk: [`docs/desay-capabilities.md`](docs/desay-capabilities.md).

---

## 4. Repository map

```
STATUS.md                       cold-start handover: state, findings, open questions, next actions
ROADMAP.md                      what to build / verify next
docs/
  feasibility-report.md         main findings with evidence table and confidence levels
  desay-hardware.md             BOM, boot chain, partitions, software stack, MCU
  desay-unit-identity.md        the installed unit (HW 036 / SW 0317) and its engineering mode
  desay-container.md            .bin layout, component offsets, extraction recipes
  validation-and-repack.md      proof that validation is md5sum + repack conditions
  desay-capabilities.md         what is / is not achievable, ranked, with risk
  skoda-theme-analysis.md       NoName Skoda pack decoded + exact Desay splash format
  desay-action-plan.md          end-to-end checklist (phases, owners, acceptance, risks)
  dev-plan-installed-unit.md    development constraints and gates for the installed unit
  why-no-custom-firmware.md     why no Desay custom firmware exists (and the false "WinCE" claim)
  noname-platform.md            NoName package anatomy, AA stack, theme mechanism
  library-manifest.md           local firmware library layout and hashes
  assets/                       unit screenshots, Skoda vs VW start-screen comparisons
  evidence/                     raw probe outputs the conclusions are based on
tools/
  scan_magics.py                container / filesystem signature scanner
  desay/container_probe.py      .bin header, payload start, entropy, strings
  desay/uimage_probe.py         uImage / ELF headers (kernel, U-Boot, arch)
  desay/carve.py                gzip -> tar extraction of the svp.bin userspace
  desay/osbin_parse.py          os.bin 14-member table -> kernel, DTBs, MLO, u-boot, targetfs.bin
  desay/targetfs_extract.py     gunzip targetfs.bin -> ext4 image (+ upgrade/testing uenv)
  desay/elf_imports.py          dynamic dependencies (proves libsvapi_vw has no crypto)
  desay/libsvapi_probe.py       validation strings (md5sum flow)
  desay/make_startscreen_ppm.py PNG -> 1,536,015-byte Desay PPM, --all-slots, round-trip check
  noname/probe.py               NoName tar inventory (AA stack, theme assets)
  theme/render_logo.py          NoName logo.bin -> PNG
  arrange/                      PowerShell library organiser (dedupe, hashes, ACL normalisation)
```

---

## 5. Quick start

```bash
# regenerate the Skoda start-screen payload for all 13 slots (with a visual verification PNG)
python tools/desay/make_startscreen_ppm.py docs/assets/skoda-startscreen-5606.png \
    -o build --all-slots --verify-png build/verify.png

# rebuild the rootfs from the official image (if not already extracted)
python tools/desay/osbin_parse.py          # os.bin table -> kernel/DTB/MLO/u-boot/targetfs.bin
python tools/desay/targetfs_extract.py     # gunzip -> targetfs.img (ext4)
7z x targetfs.img -o rootfs\               # browse it (7-Zip 21+ reads ext4)

# updater internals
python tools/desay/elf_imports.py          # no libcrypto in libsvapi_vw
python tools/desay/libsvapi_probe.py       # md5sum validation flow

# inspect any firmware blob for container/filesystem signatures
python tools/scan_magics.py /path/to/firmware.bin
```

Scripts carry absolute paths from the analysis machine; edit the constants at the top before
running. Requirements: Python 3 with numpy + Pillow, 7-Zip 21+ for ext4.

---

## 6. Where the firmware lives (deliberately not in git)

| Content | Location |
|---|---|
| Firmware library, deduplicated and hashed | `I:\187B-Firmware-Library\` |
| Installed-unit reference (official `.bin`, extracted boot chain, rootfs, docs) | `I:\187B-DESAY-SW0317-INSTALLED\` |
| NoName dictionary, patches and flash log | `I:\187B-NONAME-CLEAN\` |

`docs/library-manifest.md` and `STATUS.md` describe the layout and how to re-derive any component.

---

## 7. Status

| Phase | State |
|---|---|
| Platform identification, container/rootfs reversal, validation question | **done** |
| Start-screen format + Skoda payload | **done** (generated, verified) |
| In-place patcher + container rebuilder | next (offline, zero risk) |
| Force-update strategy (avoid the updater skipping a same-version component) | open - last software blocker |
| UART console, eMMC backup, rescue SD, restore rehearsal | open - needs hardware |
| First flash of the modified package | after the two gates above |

---

## 8. Ground rules

1. **No firmware binaries here.** Analysis, scripts and derived text only; firmware stays on the
   owner's disks.
2. **Never cross-flash** the two families. Different bootloader, kernel and partition layout; the
   result is a brick, not a theme change.
3. **Evidence first.** Every claim ties to a file/offset/member and is marked *observed* or
   *inferred*, with a confidence level.
4. **No flashing the target unit** until a full eMMC backup and a rehearsed restore procedure
   exist (`docs/desay-action-plan.md`, Phase 2).
5. Only work on hardware you own.
