# STATUS / HANDOVER — read this first when resuming

Last updated: **2026-10-24** · Repo: analysis + tooling only (no firmware binaries).

**Goal:** a **ŠKODA start-up screen** on the owner's installed Desay unit (HW 036 / SW 0317),
via a self-made, md5-valid firmware package, flashed only after a verified recovery path exists.
Full checklist: [`docs/desay-action-plan.md`](docs/desay-action-plan.md).

---

## 1. Where we are

| Phase | State |
|---|---|
| Platform identification (both families) | **done** |
| Desay container + component layout (5 records, `os.bin` 14-member table) | **done** |
| Desay rootfs extracted offline (`targetfs.bin` gzip → 227 MB ext4) | **done** |
| Update validation reversed (**plain `md5sum`**, no signature) | **done** |
| Start-screen format decoded (`P6` + 1,152,000 B RGB + 384,000 B pad = 1,536,015 B) | **done** |
| Skoda artwork payload generated + round-trip verified (md5 `079a5ec0…`) | **done** |
| NoName Skoda pack analysed (theme = same "Welcome to …" art in all 24 slots) | **done** |
| **Force-update strategy** (make the unit actually write a same-version component) | **open — top priority** |
| In-place patcher + container rebuilder + verifier | **open — next build** |
| UART console, eMMC backup, rescue SD, restore rehearsal | **open — needs hardware** |

## 2. Confirmed findings

**Platform (Desay, this unit).** TI **DRA72x** (Jacinto 6) · U-Boot **2014.07-00212-gd0650b9**
(2020-03-03, board `mib2_g`, DTB `dra7-mib2-g.dtb`) · **Linux 3.14.57** · `mem=1024M` ·
`console=ttyS2,115200` · eMMC (`mmcblk0`) + SD (`mmcblk1`) · ext4.
Not Windows CE, not i.MX6. Details: `desay-hardware.md`.

**Container.** 5 records at `0x0/0x200/0x400/0x600/0x800` (magic `48 81 48 81`, u32 = absolute
start offset, name @+8, version @+0x4C):

| component | start | size | content |
|---|---|---|---|
| `svp.bin` | `0x200000` | 83.8 MB | gzip→tar userspace: SVP services, Qt5/Wayland, Kanzi, CarPlay/CarLife/MirrorLink, `share/ui/*.kzb` |
| `app-pkg.bin` | `0x51EC7FB` | 52.5 MB | gzip→tar: 17 Kanzi apps (`sv.g5.mib2.*.pkg`) + `install.lst` |
| `radio.bin` | `0x8402309` | 401 KB | raw ARM **MCU** firmware (Lithio tuner + DSP, AKM DSP, CAN coding, EEPROM) |
| `os.bin` | `0x8464239` | 83.9 MB | nested 14-member pack: kernel, 2 DTBs, uramdisk, MLO, u-boot, **`targetfs.bin`** (rootfs), uenv files |

Whole-file MD5 = the shipped `.md5` sidecar value.

**Validation (the gate was here).** `svapi_vw_upgrade_package_is_valid` lives in
`/usr/lib/libsvapi_vw.so.1.4.0` (rootfs, 27 KB). It has **no crypto dependency** and its strings
show the flow: `md5sum %s > /tmp/upgrade.md5` → parse `%s.md5` → `error: %s md5 no match` →
`package unvalid`. Plus version/rollback comparisons (`the os/svp/app/radio version`,
`the size of the rollback`, `%s is match, no upgrade`). **No signature.** Details:
`validation-and-repack.md`.

**Start screen.** Rootfs `/usr/share/rvc/logo/`: 13 × `Startscreen_*.ppm` (1,536,015 B each =
`P6` header + 1,152,000 B RGB + 384,000 B zero pad), `Mazda.ppm` (unpadded, 1,152,015 B),
`opening_ttl.avi`. Displayed via `usr/bin/logo_os`, which reads a **logo index from NOR**
(`Logo_Name_Array`, `load/save_exlap_logo_index`, default fallback). All 13 slots have identical
size → replacing **all 13** is index-proof.

**NoName "Skoda theme" (reference).** The `5606 SKODA` pack has all **24** startscreens replaced by
one identical 800×480 image ("Welcome to ŠKODA"); i.e. the same "Welcome to …" artwork rebranded
into every slot. Desay's `Startscreen_Normal.ppm` decodes to the same design with the VW logo.
Details: `skoda-theme-analysis.md`.

**Not possible.** Android Auto (no stack, no HU certificate) — a CarPlay→AA dongle is the answer.
Full Skoda in-unit UI theme (compiled `VW_MP2017*.kzb` Kanzi bundles).

## 3. Open questions, ordered

1. **Force-update strategy.** The updater skips components whose version matches
   (`"%s is match, no upgrade"`). Our patched `os` component would still declare
   `MIB2-C-V20-20200303`. Decide: bump version string + `ROLL_BACK_NO` (preferred), find a forced
   update/factory mode, or write from a console. **This is the last software blocker.**
2. **Logo index value/default** — irrelevant if all 13 slots are patched; only matters if we keep
   one slot. Low priority.
3. **Per-component md5 verification** — `logo_os`/`updateservice` carry `<component> md5sum error`
   strings; the rebuilder must reproduce whatever the updater checks (internal consistency, not a
   signature).
4. **`CheckRowChecksum`** in `updateservice` — eMMC write verification? Confirm before flashing.
5. Rollback counter storage ("MU") and whether reflashing identical versions is a no-op skip.
6. On-screen checksums `0xc473` / `0xda8c` — unexplained, low priority now.
7. Does any 187B revision really run Windows CE? This one does not (`why-no-custom-firmware.md`).

## 4. Next actions (in order)

1. Build `tools/desay/patch_targetfs.py` — swap the 13 PPMs **in place** in `targetfs.img`
   (locate via ext4 inode extents), write `targetfs.patched.img`.
2. Build `tools/desay/rebuild_bin.py` — re-gzip → `targetfs.bin` → rebuild `os.bin` table →
   rebuild outer container → md5 → sidecar with original `VERSION:`/`ROLL_BACK_NO:` lines.
   **Acceptance: a no-change rebuild is byte-identical to the official `.bin`.**
3. Answer open question #1 (force-update), then verify the patched build with a verifier that
   re-extracts and diffs every member.
4. Hardware phase: UART log → full eMMC dump → rescue SD → written restore rehearsal.
5. First flash, then optional extras (Skoda CarPlay icon, `opening_ttl.avi`).

## 5. Quick commands (resume in 5 minutes)

```powershell
# regenerate the Skoda start-screen payload (all 13 slot names), with visual check
python tools/desay/make_startscreen_ppm.py docs/assets/skoda-startscreen-5606.png `
    -o build --all-slots --verify-png build/verify.png

# extract the rootfs again from the official image (if not already on disk)
python tools/desay/osbin_parse.py        # os.bin table -> kernel/DTB/MLO/u-boot/targetfs.bin
python tools/desay/targetfs_extract.py   # gunzip -> targetfs.img (ext4)
7z x targetfs.img -o rootfs\             # browse it (7-Zip 21+ reads ext4)

# updater internals
python tools/desay/elf_imports.py        # no libcrypto in libsvapi_vw
python tools/desay/libsvapi_probe.py     # validation strings
```

## 6. Where the data lives (not in this repo)

| What | Where |
|---|---|
| Firmware library (3.87 GB, deduped, hashed) | `I:\187B-Firmware-Library\` |
| **Installed-unit reference folder** | `I:\187B-DESAY-SW0317-INSTALLED\` (official `.bin`+`.md5`, extracted boot chain, `targetfs.img`, docs, screenshots, `05-MODS-WORK`, `90-BACKUPS`) |
| NoName dictionary + patches + flash log | `I:\187B-NONAME-CLEAN\` |
| Unit screenshots (source) | `I:\187B-Firmware-Library\Screenshot\` |
| Working extracts | DSH workspace `…\187b\` (`desay\osbin\`, `desay\rootfs\`, `theme\`, `catalog\`) — regenerable |

## 7. Environment notes (gotchas)

- Shell is **Windows PowerShell 5.1**: scripts must be **ASCII-only**; no `-AsByteStream`.
- Python: DSH runtime interpreter (`…\dependencies\python\python.exe`) with numpy + Pillow;
  no capstone installed yet.
- **git push** from the sandbox fails (schannel + credential-helper pipes). Working recipe:
  ```powershell
  $tok=(gh auth token); $b64=[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("x-access-token:$tok"))
  git -c credential.helper= -c http.sslBackend=openssl -c http.version=HTTP/1.1 `
      -c "http.extraheader=AUTHORIZATION: basic $b64" push origin main   # run unrestricted; retry once
  ```
- Some source firmware on `E:` is ACL-locked (Administrators only); readable copies are in `I:\`
  (elevated copy job: `tools/arrange/`).
- 7-Zip 26.02 reads ext4 natively — used to extract the rootfs.

## 8. Commit log

| commit | content |
|---|---|
| `23879cd` | initial: feasibility report, container notes, tools, library manifest |
| `73a361b` | Desay container table decoded; unit identity + engineering mode; screenshots |
| `5a35234` | hardware/software dossier; platform corrected to TI DRA72x |
| `b33219b` | STATUS handover |
| `7720209` | why-no-custom-firmware (WinCE claim corrected) |
| `4ff309b` | scope: installed Desay unit only; dev plan + gates |
| `a15e4f1` | **M1 answered: validation is md5sum**; os.bin table; rootfs extraction; validation doc |
| `1cb5797` | capability analysis + boot-splash discovery (PPM files) |
| `3d701ee` | NoName Skoda pack analysis + verified payload generator |
| `878d453` | end-to-end action plan (phases, owner split, risk register) |
