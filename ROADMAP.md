# Roadmap

Phase 1 — platform identification & feasibility — **done** (see `docs/feasibility-report.md`).

## Open questions, ordered by value

### P1 — Decide whether Desay packages are modifiable at all
- [ ] Statically analyse `svapi_vw_upgrade_package_is_valid` / `svapi_vw_read_pkg_md5` in
      `libupdate.so.1.0.0` (ARM ELF, 820 KB) and `bin/updateservice` (844 KB).
      Target: does validity reduce to the plain MD5 that the shipped `.md5` sidecar already
      contains, or is there a signature/HMAC over the payload?
- [ ] Map the container component records fully (all `48 81 48 81` records between `0x000` and
      `0x200000`, their sizes/names/tags) — currently only `os.bin` + header are parsed.
- [ ] Identify the rollback-counter storage ("MU") and the exact check
      (`CheckRollbackValue`, `SaveRollBackNoToMU`) — this determines whether a self-made
      package would be refused purely on version numbers.

**Why:** this is the gate for every Desay-side idea (custom splash, UI cleanup, diagnostics).

### P2 — Desay boot logo path
- [ ] Parse the `.KZB` format enough to locate the `logo` texture inside
      `share/ui/*_G5_Logo.kzb` (embedded PNG at offset 91083 in the analysed file) and check
      whether replacing it with an 800×480 image produces a valid bundle.
- [ ] Verify whether the UI app id 19 (`app-run 19 #logo`) reads only that bundle or also an
      MTD partition (check `strings` in the logo app / `libuifw-kanzi.so` for `/dev/mtd*`).

### P3 — Android Auto research
- [ ] Confirm from `aap_service` strings which AAP protocol version and USB mode are used, and
      whether the stack needs a Google-signed head-unit cert beyond the bundled dev cert
      (this explains why clones can ship AA and Desay does not).
- [ ] Document the CarPlay→AA dongle option (no firmware risk) as the supported path for the
      Desay unit.

### P4 — NoName tooling
- [ ] `tools/theme/render_logo.py`: add `--from-png` direction (PNG → 800×480 BGRA
      `logo.bin` with the 4-byte header) so a custom splash can be round-tripped and re-packed
      into a logo overlay tar.
- [ ] `tools/noname/repack.py`: build a minimal overlay tar (config.txt + `script/*.sh` +
      payload) from a directory, with correct tar padding so the unit's updater accepts it.
- [ ] Verify the MTD5 backup/restore procedure on hardware.

### P5 — Documentation / library
- [ ] Keep `docs/library-manifest.md` in sync with the local library on `I:\187B-Firmware-Library`
      (regenerate with `tools/arrange/arrange_187b.ps1`, which dedupes by SHA-256 and
      normalises ACLs so locked source files become readable copies).

## Non-goals

- Cross-flashing Desay ↔ NoName firmware. Different bootloader, kernel, partitions; not a
  reversible experiment.
- Shipping firmware blobs, vendor UI resources or certificates in this repository.
