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

## P1 — Desay package validation (highest value)

- [ ] Disassemble `svapi_vw_upgrade_package_is_valid` / `svapi_vw_read_pkg_md5(-_info)` in
      `libupdate.so.1.0.0` (ARM ELF, 820 KB) and `bin/updateservice` (844 KB): is validity just
      the whole-file MD5 (feasible repack) or a cryptographic signature (dead end)?
- [ ] Trace `CheckRollbackValue` / `SaveRollBackNoToMU`: where is the rollback counter live
      (MCU EEPROM? eMMC partition?) and does it compare only `ROLL_BACK_NO` from the sidecar?
- [ ] Reproduce the two on-screen checksums (`0xc473` radio SW, `0xda8c` bootloader). Not a
      stored header field; try CRC32-low16, summed words, and hashes over `radio.bin` vs the
      *uncompressed* app data. This tells us what else a hand-made package must satisfy.

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

## P4 — NoName tooling

- [ ] `tools/theme/render_logo.py`: add the reverse direction (PNG → 800×480 BGRA `logo.bin`
      with the 4-byte header) plus an overlay-tar packer, so custom splashes can be produced.
- [ ] Verify the MTD5 backup/restore procedure on hardware before writing anything.

## Non-goals

- Cross-flashing Desay ↔ NoName firmware (different bootloader, kernel, partitions).
- Shipping firmware blobs, vendor UI resources or certificates in this repository.
