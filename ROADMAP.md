# Roadmap

Phase 1 — platform identification & feasibility — **done** (`docs/feasibility-report.md`).
Phase 2 — Desay package internals — **in progress**, container table decoded and verified.

## Done

- [x] Identify both platforms (Desay: U-Boot SPL 2014.07 / "Desay-SV G5 Board" / Linux 3.14.57;
      NoName: i.MX6 / LTIB / Linux 3.0.35).
- [x] Prove Android Auto absence in the Desay image and presence in the NoName image.
- [x] Decode the NoName "Skoda theme" mechanism (raw 800×480 splash `dd` to `/dev/mtdblock5`).
- [x] Identify the owner's installed unit from its screens — **SW0317 / HW 036 / OS
      MIB2-C-V20-20200303** — and match it to the library image (`docs/desay-unit-identity.md`).
- [x] Decode the Desay container record table: `svp.bin`, `app-pkg.bin`, `radio.bin`, `os.bin`
      with absolute start offsets, all boundaries validated (`docs/desay-container.md`).
- [x] Confirm the shipped `.md5` sidecar is the **whole-file** MD5 and that it matches.

## P1 — Desay package validation — **ANSWERED (md5sum, no signature)**

- [x] `svapi_vw_upgrade_package_is_valid` lives in `/usr/lib/libsvapi_vw.so.1.4.0` (rootfs inside
      `os.bin` → `targetfs.bin` → ext4). It shells out `md5sum <pkg> > /tmp/upgrade.md5`, parses
      the `.md5` sidecar and compares; mismatch → `package unvalid`. **No crypto dependency**
      (DT_NEEDED: only libc/libdrm/librt). Full evidence: `docs/validation-and-repack.md`.
- [x] Version/rollback logic is in the same library: `the svp/app/radio/os version`, `the size of
      the rollback`, `%s is match, no upgrade`.
- [ ] Follow-up: what does `CheckRowChecksum` (in `updateservice`) verify — eMMC write-verify or
      payload integrity?
- [ ] Follow-up: confirm that reflashing identical versions is skipped (`"is match, no upgrade"`)
      and that rollback counters only block downgrades.
- [ ] On-screen checksums `0xc473` / `0xda8c` — still unexplained; low priority now.

## P1.2 — Build the repacker (M2)

- [ ] `tools/desay/repack.py`: parse the 5-record table → replace only the modified component →
      fix offsets/sizes → recompute whole-file md5 → regenerate sidecar with the original
      `VERSION:`/`ROLL_BACK_NO:` lines.
- [ ] Acceptance test: repack **without** modification reproduces a byte-identical `.bin`.
- [ ] Then a single-asset delta (e.g. one `.png` inside `app-pkg.bin`) and verify content.

## P2 — Desay logo path — **format cracked, payload built**

- [x] Rootfs `/usr/share/rvc/logo/`: 13 × `Startscreen_*.ppm`, format = `P6` + 1,152,000 B RGB +
      384,000 B pad = 1,536,015 B; selection by a **NOR logo index** (`logo_os`, `Logo_Name_Array`).
- [x] `tools/desay/make_startscreen_ppm.py` generates the padded payload (all 13 slots),
      round-trip verified (md5 `079a5ec0a7d8af3493a5a969defe8aaf`).
- [x] NoName comparison: the `5606 SKODA` pack replaces all 24 slots with one Skoda image —
      the same trick works here (all 13 slots, index-proof).
- [ ] Patch `targetfs.img` in place with the 13 payloads (`tools/desay/patch_targetfs.py`).
- [ ] Optional extras: Skoda CarPlay icon in `svp.bin`, `opening_ttl.avi` animation.

## P2.5 — Force-update strategy (**last software blocker**)

- [ ] The updater skips components whose version matches (`"%s is match, no upgrade"`). Decide how
      a same-version patched `os` component gets written: bump version string + `ROLL_BACK_NO`
      (preferred), forced/factory mode, or console write. Needed before any flash.

## P1.5 — Extract the remaining Desay components — **done**

- [x] `app-pkg.bin`: 17 Kanzi app packages (`sv.g5.mib2.*.pkg`, each gzip→tar) + `install.lst`.
      **Brand = per-app Kanzi bundle name `VW_MP2017*.kzb`** — this is the theme/branding switch.
- [x] `os.bin`: nested pack, record `G5-R1`; kernel `Linux-3.14.57` at +0xA00, U-Boot
      2014.07-00212-gd0650b9 at +0x51FE00. **No splash/logo in U-Boot or kernel.**
- [x] `radio.bin`: plaintext ARM **MCU firmware** (tuner Lithio/TEF668x + DSP patches, AKM audio
      DSP, CAN coding, keys/LED/EEPROM). This is what VCDS talks to.

## P0 — Hardware access paths (new, highest leverage)

- [ ] Confirm the SoC is a **GP (general-purpose, unsigned boot)** device: the kernel/U-Boot
      uImages carry no signature, but check the DRA7 boot config / eFuse state.
- [ ] Locate the **UART3 (`ttyS2`) pads** on the mainboard; a read-only console session would give
      U-Boot env, partition map, kernel logs — the foundation for any custom-OS work.
- [ ] Document the U-Boot `upgrade=1` / `testing=1` boot modes and what userspace does with them.
- [ ] Bench-harness the **MCU CAN** interface (VCDS without the car's gateway) to read the
      diagnostic coding values and check for a brand/variant byte.

## P2 — Desay boot logo path

- [ ] Determine whether the logo texture inside `<Brand>_G5_Logo.kzb` can be replaced while
      keeping the bundle valid (locate the `logo` node; the PNG at offset 91083 is a candidate).
- [ ] Confirm the UI reads the logo only from the bundle (not from an MTD partition): grep the
      logo app / `libuifw-kanzi.so` for `/dev/mtd*` and for `Logo.kzb` paths.

## P3 — Engineering mode

- [ ] Document how the engineering menu is entered (owner knows; add the exact key sequence).
- [ ] Inventory what each entry does, especially `初始化` (initialise), `EOL Off`, `USB/CarPlay`
      test, `BT调试` (BT debug), `首次连接` — any of these may expose useful logs or state.
- [ ] Check whether any entry can trigger an update from USB/SD (the System Information screen
      already has an `Update software` button).

## P4 — NoName tooling — **reference only, not a development target**

The project target is the **Desay** unit installed in the car (`docs/dev-plan-installed-unit.md`).
NoName packs are kept in the library purely to explain the ecosystem and to document the
contrast (unsigned tar overlays, raw MTD5 splash, AA stack). No NoName tooling is planned unless
the target changes; the items below are parked.

- [ ] (parked) `tools/theme/render_logo.py`: reverse direction (PNG → 800×480 BGRA `logo.bin`)
      plus an overlay-tar packer.
- [ ] (parked) Verify the MTD5 backup/restore procedure on hardware.

## Non-goals

- Cross-flashing Desay ↔ NoName firmware (different bootloader, kernel, partitions).
- Shipping firmware blobs, vendor UI resources or certificates in this repository.
