# Desay Skoda splash — complete action plan to "done"

**Goal (definition of done):** the installed Desay unit (HW 036 / SW 0317) boots showing
**"Welcome to ŠKODA"** instead of "WELCOME TO VOLKSWAGEN", with the unit still fully functional
(CarPlay, radio, Bluetooth, CAN), and a proven way back to the official firmware.

**Scope:** start screen only (optionally the CarPlay OEM icon and the start animation). Not the
in-unit UI theme, not Android Auto.

---

## Phase 0 — already done (no action needed)

| Done | Evidence |
|---|---|
| Platform identified: TI DRA72x, Linux 3.14.57, U-Boot 2014.07, rootfs ext4 | `desay-hardware.md` |
| Container decoded: 5 records → `svp.bin`, `app-pkg.bin`, `radio.bin`, `os.bin` (14-member table) | `desay-container.md` |
| Update validation reversed: **plain `md5sum` vs sidecar**, no signature | `validation-and-repack.md` |
| Rootfs extracted offline (227 MB ext4) | `tools/desay/*` |
| Start-screen format decoded: `P6` + 1,152,000 B RGB + 384,000 B padding = **1,536,015 B** | `skoda-theme-analysis.md` |
| Skoda payload generated and round-trip verified (md5 `079a5ec0…`) | `tools/desay/make_startscreen_ppm.py` |
| Start screens are selected by a NOR logo index; **all 13 slots are the same size** → replace all 13, index-proof | `desay-capabilities.md` |

---

## Phase 1 — Software (mine; offline, zero risk to the car)

### 1.1 `tools/desay/patch_targetfs.py` — in-place asset patcher
- locate the 13 `Startscreen_*.ppm` files inside `targetfs.img` (search exact byte content, or
  parse ext4 inode extents for correctness rather than guessing);
- overwrite each with the Skoda payload (same length → no filesystem rebuild, no size change);
- write `targetfs.patched.img`; nothing else in the image changes.

**Acceptance:** extracting all 13 files from the patched image yields exactly the Skoda payload;
`7z` still reads the filesystem cleanly; no other file differs.

### 1.2 `tools/desay/rebuild_bin.py` — container rebuilder
- gzip `targetfs.patched.img` → new `targetfs.bin` (same uncompressed content except the 13 assets);
- rebuild `os.bin`: same 14-member table, updated `targetfs.bin` offset/size, all other members
  byte-identical;
- rebuild the outer 5-record container with corrected record fields;
- recompute `md5sum` → new `.md5` sidecar with the **original** `VERSION:`/`ROLL_BACK_NO:` lines.

**Acceptance (must pass before anything else):**
1. rebuild with **no** change → byte-identical `.bin` to the official file;
2. rebuild with the patch → every component identical except the 13 PPMs;
3. our own re-implementation of the unit's checks passes: `md5sum` matches the sidecar, version
   strings parse identically, rollback values unchanged.

### 1.3 Force-update strategy — **the one open technical question**
The updater skips components whose version already matches (`"%s is match, no upgrade"`).
Our patched `os` component still declares `MIB2-C-V20-20200303`, so the unit may simply skip it.

Options, to be decided from the actual comparison code (`libsvapi_vw.so.1.4.0`, strings
`the os version %s %d`, `the pak_message.version is %s, and the version is %s`):
- **A.** bump the os/app version string + its `ROLL_BACK_NO` by 1 in the sidecar and in the
  component header → unit sees "newer", flashes normally (preferred, needs the comparison
  semantics confirmed);
- **B.** find a factory/`testing=1` boot mode that forces a full write;
- C. (last resort) write the patched components directly from a shell — requires console access.

**Deliverable:** a one-page note stating which option works and the exact numbers used.

### 1.4 Verifier
- re-extract everything from the produced `.bin` and diff against the official one, file by file,
  including inside `targetfs.img`;
- produce a short report: what changed / what didn't / md5s / sidecar comparison.

---

## Phase 2 — Hardware (yours; read-only, no flashing)

| Step | What | Why |
|---|---|---|
| 2.1 | Reach the mainboard: open the unit or access it behind the dashboard | need UART pads and later a backup |
| 2.2 | Find **UART3 / `ttyS2`** pads (3.3 V TTL, 115200 8N1) | the only window into U-Boot/kernel when something goes wrong |
| 2.3 | Capture a **complete boot log** (power-on → U-Boot → kernel → UI) | gives the real partition map, U-Boot env, boot device order |
| 2.4 | **Full eMMC backup** (via U-Boot `mmc read` dump, or a shell `dd` if we get one) | the restore source |
| 2.5 | Prepare a **rescue SD card** (FAT + a valid rootfs, since U-Boot can boot `mmc1p2`) | second line of recovery if eMMC gets damaged |
| 2.6 | Stable supply: battery charger or bench PSU (never a flash on a weak battery) | power loss during eMMC write is the real brick risk |
| 2.7 | Write the restore procedure and **rehearse it on paper** against the captured boot log | no improvisation on the day |

**Gate:** no modified package goes near the car until 2.1–2.7 are done.

---

## Phase 3 — First flash (the risky step, but bounded)

1. Put the official `.bin` + `.md5` on the USB stick as a safety net.
2. Put the modified `.bin` + `.md5` on the same stick.
3. Ignition on, stable supply, **do not** switch off; System Information → Update software.
4. Watch the UART log during the write (this is what the console was for).
5. After reboot: verify splash = ŠKODA, then check CarPlay, radio, Bluetooth, CAN/steering keys,
   reverse camera, engineering mode versions.
6. If anything is wrong: reflash the official package from the same stick.

**Success criteria:** ŠKODA splash on every boot, all functions working, official package
re-flashable afterwards.

---

## Phase 4 — Optional extras (after Phase 3 succeeds)

- Skoda **CarPlay OEM icon**: replace `share/CarPlay/VWicon_*.png` inside `svp.bin` with a Skoda
  icon (same mechanism, same repack pipeline).
- **Start animation**: replace `opening_ttl.avi` in `targetfs.img` (needs the same codec/duration).
- Other start-screen variants (e.g. Skoda-only artwork variations) — regenerate the PPM.

---

## What I need from you (to schedule the work)

1. **Can you open/reach the unit** for UART + backup? (If not, Phase 3 cannot be justified.)
2. **Battery charger / bench supply** available?
3. **Which extras** do you want in the first package: splash only, or splash + CarPlay icon?
4. A **photo of the UART area** once opened — I can map the pads from the photo.
5. Confirm you accept that Phase 3 carries a non-zero brick risk and that the unit is the only one.

## Effort estimate

| Phase | Owner | Time |
|---|---|---|
| 1.1–1.2 patcher + rebuilder + verifier | me | one working session |
| 1.3 force-update strategy | me | needs a focused look at the version comparison + a decision |
| 2.x hardware, UART log, backup | you (I guide) | 1–2 hours on the bench |
| 3 first flash | both (I watch the log) | ~30 minutes |
| 4 extras | me | short, reuses the same pipeline |

## Risk register

| Risk | Mitigation |
|---|---|
| Corrupt/partial flash → no boot | full eMMC backup + rescue SD + UART console |
| Updater rejects package (md5/version) | verifier + force-update strategy; a rejected package writes nothing |
| Updater *skips* the component (version match) | Phase 1.3 |
| Wrong PPM geometry → black screen but unit boots | we keep the official `.bin` on the stick; reflash restores it |
| Power loss mid-write | charger/PSU, no ignition cycling |
| eMMC write protection/checksums (`CheckRowChecksum`) | verify from `updateservice` before Phase 3 |
