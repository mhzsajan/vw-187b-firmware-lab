# Development plan — target: the installed Desay unit

**Target unit:** Desay SV `6RD 035 187B`, HW **036** / SW **0317** (`MIB2-C-V20-20200303`),
currently **installed in the owner's car**. Serial `VWZ6Z2R7343266`, BT `c300`, CarPlay
`CPL24.V1.4.3@C1`.

> **Scope: Desay only.** The NoName/"Tianbao" 187B family is **reference material only** in this
> project — it is used to explain why its community mods exist and how they work, but it is **not**
> a development target, and nothing in this plan produces, tests or flashes NoName firmware.
> All engineering applies solely to the Desay unit described above.

**Hard constraint:** it is the only unit and it is in the car. A bad flash means no radio / no
CarPlay until the unit is physically recovered. Therefore the project rule is:

> **No write to the target unit until a verified recovery path exists.**
> Analysis, unpacking, repacking and validation work happen offline on the firmware image.

---

## 1. What "developing for this unit" realistically means

| Goal | Status | Implication |
|---|---|---|
| Android Auto by firmware | **impossible** — no AA stack, no HU certificate in the image | development target for AA is *not* the firmware; it is a CarPlay→AA adapter (hardware, reversible) |
| Skoda boot logo / brand look | **the real firmware goal** — branding is a per-app Kanzi bundle (`VW_MP2017*.kzb`) | needs (a) a Skoda bundle *or* Kanzi authoring, (b) a flashable package, (c) rollback-safe flashing |
| Other UI/behaviour tweaks (splash, strings, defaults) | possible in principle | same three requirements as above |
| Diagnostics / engineering access | **available now** | zero-risk, already usable |

So: **the development programme is about producing and safely flashing a modified
`svp.bin`/`app-pkg.bin` for this specific unit**, plus non-firmware paths for AA.

## 2. Three workstreams and their gates

### A. Recovery capability (must come first)
Without this, nothing else may be flashed.

- [ ] A1. Locate **UART3 `ttyS2` (115200n8)** test pads on the mainboard; confirm whether the
      console is enabled in production builds.
- [ ] A2. Capture a **read-only boot log** (U-Boot → kernel → SVP). From the log alone we learn:
      the partition table, the eMMC layout, the U-Boot env actually in use, and the `upgrade=`/
      `testing=` boot mode behaviour.
- [ ] A3. Establish a **full eMMC backup** route — via U-Boot (`mmc read` + dump over UART/USB) or
      by pulling the eMMC. Store it, and verify the dump is restorable **in principle**
      (checksums, partition map).
- [ ] A4. Document the **recovery procedure** end-to-end (what to do if a flash fails) and test it
      on paper against the observed boot flow.

**Gate A:** no flashing until A1+A2+A3 are done and A4 is written down.

### B. Validation answer + repacker (offline, no unit risk)
- [ ] B1. Disassemble `svapi_vw_upgrade_package_is_valid` / `svapi_vw_read_pkg_md5(_info)` in
      `libupdate.so.1.0.0` (ARM ELF) and `bin/updateservice`.
      **Outcome:** either "validity = whole-file MD5" (repacking viable) or "signature" (stop).
- [ ] B2. Understand the rollback check (`CheckRollbackValue`, `SaveRollBackNoToMU`,
      `GetSWRollbackNoFromFile`): which numbers, compared how, stored where.
- [ ] B3. Build the **delta repacker** (`tools/desay/repack.py`):
      parse the 5-record table → keep untouched components' compressed bytes verbatim → replace
      only the modified component → rebuild the table offsets/sizes → recompute the whole-file
      MD5 → emit new `.bin` + `.md5` with consistent `VERSION:`/`ROLL_BACK_NO:` lines.
      Acceptance: repacking with *no* change reproduces a **byte-identical** `.bin`.
- [ ] B4. Prove a *content* change (e.g. a text/brand asset) survives unpack→repack→verify.

**Gate B:** a modified `.bin` is only ever produced after B1 says MD5-only. B3's identity
round-trip must pass first.

### C. The actual modification (asset/brand work, offline)
- [ ] C1. Extract `sv.g5.mib2.lockscreen` (and the brand bundles `VW_MP2017*.kzb`) from
      `app-pkg.bin`; determine the `.kzb` container sufficiently to locate a bitmap/texture.
- [ ] C2. Decide the Skoda route:
      (a) obtain a Skoda-branded G5 build (`SK_MP2017*.kzb` or equivalent) — best case;
      (b) author a replacement `.kzb` (Kanzi Studio, matching engine) — heavy;
      (c) narrow-scope edit of the existing bundle (single texture swap) — only if `.kzb` layout
          allows it and the app tolerates it.
- [ ] C3. Produce a **delta package**: one modified component, everything else byte-identical,
      version strings unchanged, rollback numbers unchanged (or documented if they must move).

## 3. Risk classes (apply to every step)

| Class | Examples | Allowed when |
|---|---|---|
| R0 read-only | firmware unpacking, disassembly, engineering-mode screenshots, UART log capture | anytime |
| R1 reversible | same-version reflash, restoring a **verified** backup | after Gate A |
| R2 irreversible | flashing a modified package, MCU (`radio.bin`) write, bootloader/kernel change | after Gate A **and** Gate B, with a restore plan and a charged battery / stable supply |

## 4. Milestones

| # | Milestone | Needs hardware? | Risk |
|---|---|---|---|
| M0 | Documentation baseline (this repo) | no | R0 |
| M1 | `libupdate.so` validation verdict | no | R0 |
| M2 | Delta repacker + identity round-trip | no | R0 |
| M3 | UART console log captured & decoded (partition map, env) | yes — open the unit / reach pads | R0 |
| M4 | Full eMMC backup + recovery procedure | yes | R0/R1 |
| M5 | Modified package built and verified offline | no | R0 |
| M6 | First flash of the modified package | yes | R2 |

M1 → M2 can start immediately; M3 is the critical hardware dependency.

## 5. Explicitly out of scope / do-not-do

- Do **not** flash the NoName `.tar` family onto this unit (different SoC/bootloader/partitions).
- Do **not** write `radio.bin` (MCU) until the Linux side is recovered end-to-end — an MCU brick
  can disable radio/CAN/keys independently of Linux.
- Do **not** rely on "it will just reject a bad package": that is our *hypothesis* (open question),
  not a verified fact.
- Do **not** flash without a backup that has been verified as complete.

## 6. Questions for the owner (needed to schedule M3/M4)

1. Is the mainboard reachable **without removing the unit from the dashboard** (through the
   glovebox / trim), or are you willing to remove it for a bench session?
2. Do you have a **stable 12 V supply** (battery charger / bench PSU) and a USB stick for the
   unit's `Update software` path?
3. Priority if only one firmware goal is achievable now: **Skoda look** (asset/brand) or
   **UI/behaviour tweaks**? (AA stays a dongle.)
4. Are you willing to do a **same-version reflash** as a controlled test of the update path once
   a verified backup exists? That validates "we can restore" before we ever ship a change.
