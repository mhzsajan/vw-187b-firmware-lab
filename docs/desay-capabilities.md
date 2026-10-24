# What we can actually do on the Desay unit

Analysis as of 2026-10-24, after: container/rootfs extraction, validation reversal (`md5sum`),
and the boot-splash discovery. Target = the **installed** unit (HW 036 / SW 0317), so every row
also lists whether it needs the car to be touched and what could go wrong.

## 0. What changed with the latest findings

Three facts make the Desay unit far more workable than the literature suggested:

1. **Validation is `md5sum` only** — no signature. A rebuilt package can pass
   (`docs/validation-and-repack.md`).
2. **The root filesystem is inside the update image** (`os.bin` → `targetfs.bin` → ext4 227 MB),
   so everything the OS shows at boot is available offline.
3. **The boot start screens are plain PPM images** — not compiled Kanzi assets:

```
/usr/share/rvc/logo/
  Startscreen_Alltrack.ppm   1,536,015 B   P6 header, 800x480, 4 bytes/pixel
  Startscreen_Normal.ppm     1,536,015 B   ("Normal" is the most likely default)
  Startscreen_GTI/GTD/R/GTE/E_Golf/R_Line/Twin_Drive/Beats_Audio/Blue_Motion/
  Startscreen_Dynaudio/Family.ppm          (13 VW variants, all same size)
  Mazda.ppm                  1,152,015 B   800x480 RGB (P6, 3 bytes/pixel) - other OEM logo
  opening_ttl.avi              154,510 B   the start animation
```

   They are chosen by a **logo index stored in NOR** (`logo_os` strings:
   `get logo path index from nor`, `logo path index invalid`, `Logo_Name_Array`,
   `load/save_exlap_logo_index`), with a default fallback
   (`svapi: load exlap_logo_index, invalid, Using default`).

**Consequence: a Skoda start screen is a data change, not a Kanzi authoring project.** We already
have the exact Skoda artwork (decoded from the NoName pack) and can render it to the required
800×480 format.

## 1. Capability matrix

| # | Capability | Feasible | Touches car? | Risk | Effort |
|---|---|---|---|---|---|
| 1 | Engineering-mode inspection (versions, system status, tests) | **yes, now** | no (buttons) | none | 0 |
| 2 | Read-only UART console (`ttyS2`, 115200) → U-Boot env, partition map, boot logs | **yes**, needs pads | open board | none if read-only | 1 session |
| 3 | Full eMMC backup (U-Boot `mmc read` dump) | **yes**, after #2 | open board | low | 1 session |
| 4 | **Skoda start screen (boot logo)** | **yes** — replace/add a PPM in the rootfs and rebuild `os.bin` | yes (flash) | medium | repack tool + one asset |
| 5 | Start animation change (`opening_ttl.avi`) | **yes** — same mechanism | yes (flash) | medium | same |
| 6 | Skoda CarPlay OEM icon | **yes** — `share/CarPlay/*.png` in `svp.bin` (plain PNG) | yes (flash) | medium | same |
| 7 | UI *theme* (colours/backgrounds inside Kanzi `.kzb`) | **partial** — `.kzb` is a compiled bundle; PNG-like assets inside may be replaceable, full restyle needs Kanzi Studio | yes (flash) | medium | high |
| 8 | Android Auto | **no** — no AA stack, no HU certificate; not portable | — | — | — |
| 9 | Change versions/strings shown in System Info | **yes** (text/config in rootfs) | yes (flash) | medium | low |
| 10 | MCU (`radio.bin`) modifications — tuner/amp/CAN behaviour | technically yes, high risk; MCU has its own bootloader | yes (flash) | **high** | high |
| 11 | Custom kernel / different OS | technically yes (GP-style unsigned uImages), practically huge effort | yes | **very high** | very high |
| 12 | Cross-flash NoName firmware | **never** | — | brick | — |

## 2. The flagship mod: Skoda boot screen

Why this is realistic now:

- the asset is **uncompressed, fixed-size, and already on disk in the image**;
- replacing it does **not** require rebuilding the ext4 filesystem: the ext4 image can be patched
  **in place** (overwrite the same number of data blocks for a file of identical length — the PPM
  files are all exactly 1,536,000 data bytes, so a Skoda image of the same geometry fits exactly);
- then `targetfs.bin` is re-gzipped, `os.bin` rebuilt (14-entry table with offsets/sizes),
  the outer 5-record container rebuilt, whole-file md5 recomputed, and the `.md5` sidecar updated
  with the original `VERSION:`/`ROLL_BACK_NO:` lines.

Pipeline (all offline, each step testable):

```
Skoda artwork (800x480)  ->  Skoda.ppm (P6 / 4-byte pixels, 1,536,000 data bytes)
        ->  patch targetfs.img in place (locate the PPM data, overwrite)
        ->  gzip -> targetfs.bin  ->  rebuild os.bin table
        ->  rebuild outer .bin    ->  md5sum -> update sidecar
        ->  verify: unpack the new .bin again and diff every component
```

**Open question that decides "flash or not":** which index does the unit use? If the configured
index points at `Startscreen_Normal.ppm`, overwriting *that* file is enough (no index change).
Otherwise the NOR index (or `svapi_exlap_logo_set`) must be used — TBD from the `logo_os`
disassembly and the engine's `Logo_Name_Array`.

Risk profile of this mod: if the flash completes, boot splash changes and nothing else. If it
fails mid-flash → the recovery path (#2/#3) is what saves the unit, which is why those come first.

## 3. What is *not* worth doing

- **Android Auto**: no stack, no certificate. A CarPlay→AA adapter is the only real path, and it
  is reversible hardware, not firmware.
- **Full Skoda UI retheme**: every app draws from a compiled `VW_MP2017*.kzb`. Without a Skoda
  bundle or Kanzi Studio, expect "splash + CarPlay icon" level of branding, not a full theme.
- **MCU/radio firmware edits**: the MCU owns tuner, amp, CAN coding and standby. Any mistake
  survives a Linux reflash (the MCU has its own bootloader), so it multiplies brick risk for no
  benefit to the stated goals.
- **Kernel/OS replacement**: technically unblocked by the unsigned uImages, but the payoff (still
  no AA, still Kanzi apps) does not justify it.

## 4. Recommended sequence (respecting "never brick the car unit")

| Phase | Work | Car risk |
|---|---|---|
| 1 | **M2 repacker** — rebuild the container with no change, prove byte-identical round trip | none |
| 2 | **Asset patch tool** — generate `Skoda.ppm`, patch `targetfs.img` in place, rebuild, verify by re-extraction + diff | none |
| 3 | **Recovery** — UART console log, then full eMMC dump, then written restore procedure | none (read-only) |
| 4 | **First flash** — same-version official package (or the asset-patched one) on a stable supply | medium, now recoverable |
| 5 | Only then: iterate on branding (splash variants, CarPlay icon, strings) | medium |

## 5. Still to verify before phase 2/4

- the logo-index mechanism (`Logo_Name_Array`, NOR layout, default value);
- per-component md5: `logo_os`/`updateservice` contain `<component> md5sum error` strings, so the
  update flow may verify each component while staging — the repacker must reproduce whatever the
  updater expects (it is internal-consistency, not a signature);
- `CheckRowChecksum` in `updateservice` (eMMC write verification);
- rollback counter storage location ("MU") and whether reflashing the same versions is skipped
  (`"%s is match, no upgrade"`).

## 6. Bottom line

For the Desay unit the realistic deliverable is:

> **a Skoda-badged start-up experience (splash image + start animation + CarPlay icon) via a
> self-made, md5-valid package, flashed only after a verified backup and recovery path exist.**

That is a genuine, bounded, achievable piece of firmware development — and it needs no Kanzi
Studio, no Android Auto stack, and no MCU work.
