# VW 187B firmware lab (`6RD 035 187B` / RCD330 family)

Reverse-engineering notes, tooling and experiments for the VW PQ-platform 6.5" radio
**`6RD 035 187B`** (the Chinese RCD330-family unit).

Two vendor families exist in the wild and they are **different products**, not one product
with features switched off:

| | Desay SV ("official") | NoName / "Tianbao" (community clone) |
|---|---|---|
| Firmware package | single `.bin` + `.md5` (`6RD_035_187B_TR7247_SW03xx_…`) | `.tar` overlay packs (`std_plus_pss-6.5inch_*`) |
| Platform | **TI DRA72x (Jacinto 6)**, U-Boot 2014.07 board `mib2_g`, Linux **3.14.57**, 1 GB RAM, Wayland/Qt5 + **Kanzi** UI, Desay **SVP** framework | NXP i.MX6, Freescale **LTIB**, Linux **3.0.35**, Qt 4.7.4 HMI (`opt/hmi`) + OVG graphic resources |
| Update model | `updateservice` + `libupdate.so`, package validity / md5 / rollback counters | plain tar + `/bin/sh` hooks, **no signing** |
| CarPlay / CarLife / MirrorLink | yes | yes |
| Android Auto | **absent** (no AA binaries, no certs) | **present** (`opt/AndroidAuto/*`, `/etc/aap_dev_hu_*`) |
| Skoda boot logo / theme | not user-changeable (logo inside Kanzi bundle, no Skoda assets in image) | **trivial** — raw splash `dd`'d to `/dev/mtdblock5` |
| Cross-flash | **never** — different bootloader, kernel, partitions | **never** |

The headline findings, with file/offset evidence, are in
[`docs/feasibility-report.md`](docs/feasibility-report.md).

## What we can and cannot do

- **Desay + Android Auto by firmware:** not achievable — the projection stack and head-unit
  certificates do not exist anywhere in the image. Practical answer: a CarPlay→Android-Auto
  adapter dongle (the unit already runs CarPlay).
- **Desay + Skoda theme:** not by modification. The logo lives in a compiled Kanzi `.kzb` and
  the `.bin` is validated by `svapi_vw_upgrade_package_is_valid` / `svapi_vw_read_pkg_md5`
  with anti-downgrade rollback counters. The only realistic route is a Skoda-branded Desay
  build (Desay already ships branded variants such as `SW0318 "Red"`).
- **NoName + AA / Skoda theme:** both work today via small overlay tars (see `30-Mods-Patches`
  in the local library) — this repo documents how and why.

## Repository map

```
docs/
  feasibility-report.md      main findings, evidence table, confidence levels
  desay-hardware.md          full BOM / boot chain / software stack / capability matrix
  desay-unit-identity.md     the installed unit (SW0317) and its engineering mode
  desay-container.md         .bin container layout, offsets, extraction recipe
  noname-platform.md         tar package anatomy, AA stack, theme mechanism
  library-manifest.md        the local firmware library layout + hashes
  assets/skoda-logo-preview.png   decoded Skoda splash from logoSK tar
  assets/screenshots/        unit screens: version info, system status, engineering mode
  evidence/                  raw outputs the conclusions are based on
tools/
  scan_magics.py             generic container/FS signature scanner
  desay/                     .bin header probe, uImage/ELF probe, rootfs carver, updater symbols
  noname/                    tar package inventory probe
  theme/render_logo.py       logo.bin -> PNG renderer
  arrange/                   PowerShell library organiser (dedupe + hashes + ACL normalisation)
ROADMAP.md                   what to build / verify next
```

## Ground rules

1. **No firmware binaries in this repo.** Everything here is analysis, scripts and derived text.
   Firmware stays on the owner's disk (see `docs/library-manifest.md` for the expected layout).
2. Never flash one family's firmware onto the other. Brick risk is real and unrecoverable
   without a bench setup.
3. Findings must be tied to evidence: file + offset/member + what it proves, and marked
   **observed** vs **inferred** with a confidence level.
4. Only work on hardware you own.

## Quick start

```bash
# inspect any firmware file (works on .bin, .tar, images)
python tools/scan_magics.py /path/to/firmware.bin

# Desay .bin: container header, payload start, kernel/u-boot banners
python tools/desay/container_probe.py
python tools/desay/uimage_probe.py

# Desay .bin: list the gzip->tar application partition
python tools/desay/carve.py

# NoName .tar: package inventory, AA stack, theme assets
python tools/noname/probe.py

# render the community Skoda splash blob to PNG
python tools/theme/render_logo.py logo.bin -o skoda.png --width 800 --height 480 --offset 4
```

Scripts currently carry absolute paths from the machine the analysis was done on; edit the
constants at the top (or the `SRC`/`DESAY` variables) before running.

## Status

Phase 1 (platform identification + feasibility) is complete. See [`ROADMAP.md`](ROADMAP.md)
for the open questions — starting with whether Desay's package validation is plain MD5 or
cryptographic, which decides whether a modified `.bin` could ever be flashed.
