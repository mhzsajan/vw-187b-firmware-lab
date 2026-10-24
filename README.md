# VW 187B firmware lab (`6RD 035 187B` / RCD330 family)

Reverse-engineering notes, tooling and experiments for the VW PQ-platform 6.5" radio
**`6RD 035 187B`** (the Chinese RCD330-family unit).

Two vendor families exist in the wild and they are **different products**, not one product
with features switched off:

| | Desay SV ("official") | NoName / "Tianbao" (community clone) |
|---|---|---|
| Firmware package | single `.bin` + `.md5` (`6RD_035_187B_TR7247_SW03xx_â€¦`) | `.tar` overlay packs (`std_plus_pss-6.5inch_*`) |
| Platform | **TI DRA72x (Jacinto 6)**, U-Boot 2014.07 board `mib2_g`, Linux **3.14.57**, 1 GB RAM, Wayland/Qt5 + **Kanzi** UI, Desay **SVP** framework | NXP i.MX6, Freescale **LTIB**, Linux **3.0.35**, Qt 4.7.4 HMI (`opt/hmi`) + OVG graphic resources |
| Update model | `updateservice` + `libupdate.so`, package validity / md5 / rollback counters | plain tar + `/bin/sh` hooks, **no signing** |
| CarPlay / CarLife / MirrorLink | yes | yes |
| Android Auto | **absent** (no AA binaries, no certs) | **present** (`opt/AndroidAuto/*`, `/etc/aap_dev_hu_*`) |
| Skoda boot logo / theme | not user-changeable (logo inside Kanzi bundle, no Skoda assets in image) | **trivial** â€” raw splash `dd`'d to `/dev/mtdblock5` |
| Cross-flash | **never** â€” different bootloader, kernel, partitions | **never** |

The headline findings, with file/offset evidence, are in
[`docs/feasibility-report.md`](docs/feasibility-report.md).

## What we can and cannot do

- **Desay + Android Auto by firmware:** not achievable â€” the projection stack and head-unit
  certificates do not exist anywhere in the image. Practical answer: a CarPlayâ†’Android-Auto
  adapter dongle (the unit already runs CarPlay).
- **Desay + Skoda theme:** not by modification. The logo lives in a compiled Kanzi `.kzb` and
  the `.bin` is validated by `svapi_vw_upgrade_package_is_valid` / `svapi_vw_read_pkg_md5`
  with anti-downgrade rollback counters. The only realistic route is a Skoda-branded Desay
  build (Desay already ships branded variants such as `SW0318 "Red"`).
- **NoName + AA / Skoda theme:** both work today via small overlay tars (see `30-Mods-Patches`
  in the local library) â€” this repo documents how and why.

## Repository map

> **Resuming later? Start with [`STATUS.md`](STATUS.md)** â€” it has the current state, confirmed
> findings, open questions, where the firmware data lives, environment gotchas and next actions.

```
STATUS.md                    cold-start handover: state, findings, open questions, env notes, next steps
ROADMAP.md                   what to build / verify next (P0 hardware, P1 validation, P2 logo)
docs/
  feasibility-report.md      main findings, evidence table, confidence levels
  desay-hardware.md          full BOM / boot chain / software stack / capability matrix
  desay-unit-identity.md     the installed unit (SW0317) and its engineering mode
  desay-container.md         .bin container layout, offsets, extraction recipe
  validation-and-repack.md   PROOF: validation is md5sum (no signature) + repack recipe
  desay-capabilities.md      what is/isn't achievable on this unit (ranked, with risk)
  skoda-theme-analysis.md    NoName Skoda pack decoded + the exact Desay splash format
  desay-action-plan.md       end-to-end checklist to a Skoda splash (phases, owners, risks)
  dev-plan-installed-unit.md target is the installed unit: gates, risk classes, milestones
  why-no-custom-firmware.md  why the Desay scene doesn't exist - and the false "WinCE" explanation
  noname-platform.md         tar package anatomy, AA stack, theme mechanism
  library-manifest.md        the local firmware library layout + hashes
  assets/                    unit screenshots + Skoda/VW start-screen comparisons
  evidence/                  raw outputs the conclusions are based on
tools/
  scan_magics.py             generic container/FS signature scanner
  desay/                     container + os.bin probes, rootfs extractor, ELF import analyser,
                             updater-string probe, start-screen PPM generator
  noname/                    tar package inventory probe
  theme/render_logo.py       logo.bin -> PNG renderer (NoName)
  arrange/                   PowerShell library organiser (dedupe + hashes + ACL normalisation)
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

Platform identification, the container/rootfs reversal and the update-validation question are
**done** (validation is plain `md5sum`, no signature). The achievable firmware goal is a
**Skoda start screen**: the format is decoded (1,536,015-byte padded PPM) and the payload is
generated and verified. Next: in-place patcher + container rebuilder, then the force-update
question, then the hardware recovery path, then the first flash.

See [`STATUS.md`](STATUS.md) for the current state and
[`docs/desay-action-plan.md`](docs/desay-action-plan.md) for the end-to-end checklist.

