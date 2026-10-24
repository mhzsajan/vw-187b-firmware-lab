# Why is there no custom firmware for the Desay 187B?

A common explanation circulating online says the Desay 187B runs **Windows CE 6.0**, that its OS
is a monolithic `Nk.bin` built from a vendor BSP with Platform Builder, and that this is why no
custom firmware exists. **For the unit in this project that explanation is wrong** — and the real
reasons are more specific and more useful, because several of them are things we could still
change.

---

## 1. The Windows CE claim is false for this unit

The owner's unit (HW 036 / SW 0317 — the image analysed here) is **Linux on a Texas Instruments
DRA72x**. This is not an inference from a datasheet; it is read out of the firmware the unit runs,
which matches its own version screen:

| Evidence | Where |
|---|---|
| `console=ttyS2,115200n8 … mem=1024M … root=/dev/mmcblk0p1 ro rootfstype=ext4` | U-Boot environment inside `os.bin` |
| U-Boot **2014.07-00212-gd0650b9 (Mar 03 2020)**, `board=mib2_g`, "Desay-SV G5 Board" | `os.bin` uImage + strings |
| Device tree **`dra7-g5-r1.dtb`**, kernel **`Linux-3.14.57`** | `os.bin` uImage name + `findfdt` in U-Boot |
| `/svp/etc/*.sh` POSIX shell scripts, `/proc`, `/sys`, `55020000.ipu` (TI IPU2) | `svp.bin` |
| ELF32 ARM binaries, GLIBC/GLIBCXX, Qt5, Wayland/Weston, GStreamer 1.0.204 | `svp.bin`, `app-pkg.bin` |
| gzip→tar component payloads, ext4 rootfs, eMMC/SD | container analysis (`docs/desay-container.md`) |

Windows CE has no U-Boot, no device-tree `dra7-g5-r1.dtb`, no `ttyS2` bootargs, no ext4, no
Wayland/Qt5, no `/sys` power-management nodes, and no `gzip→tar` package format. **There is no
`Nk.bin` anywhere in this firmware, and no Platform Builder BSP is involved.**

Where the confusion plausibly comes from:

- **"Desay" is used loosely.** Desay SV has shipped many WinCE-based head units over the years;
  descriptions written about *other* Desay products get attached to the 187B.
- **187B is a part-number family, not one product.** Several suppliers/revisions exist
  (HW 036/040/…, SW 0317/0318/0357/0358); a WinCE-based 187B revision may exist elsewhere. It is
  **not this one**. Our unit reports `Exlap`/`SVP`/`MIB2-C` versions — Desay's Linux framework
  naming, not WinCE artifacts.
- **The wrong conclusion survives because the practical outcome is the same**: closed firmware,
  validated updates, no community mods. But the *reasons* and the *paths forward* are different.

**Open question for the record:** does any Desay 187B revision actually run WinCE? Unverified —
we have only this family's firmware, and it is Linux.

---

## 2. The real reasons (ranked by how much they matter)

### 2.1 The Desay update path is *closed by design* — it is not an OS property

This is the decisive one, and it has nothing to do with WinCE vs Linux.

| | NoName / Tianbao | Desay SV |
|---|---|---|
| Package | plain `.tar` overlay | single `.bin` + `.md5` sidecar |
| Installer | `/bin/sh` scripts shipped with the pack (`before_app_update.sh`, `after_app_update.sh`) running as root | compiled `updateservice` + `libupdate.so` |
| Validation | none (no signature, no version gate) | `svapi_vw_upgrade_package_is_valid`, `svapi_vw_read_pkg_md5(_info)`, rollback counters (`CheckRollbackValue`, `SaveRollBackNoToMU`) |
| Arbitrary writes allowed? | yes — the theme pack literally does `dd if=… of=/dev/mtdblock5` | no; `copy_to_emmc` through a privileged service, rootfs is `ro` ext4 |
| Overlay mechanism | `config.txt` switches + `[file]:[opt|etc|usr]` | **none** |

The NoName units are moddable because **the vendor shipped a script-driven updater with root hooks
and no signature** — that is an OEM design decision, and Desay made the opposite one. A Linux
device with a locked, validated updater is just as unmoddable as a WinCE device; conversely a
WinCE device with an open update format would be moddable too.

### 2.2 The UI is compiled, so there is no low-effort "mod" to seed a scene

On NoName the entire theming layer is *data*: PNG start screens, a 800×480 raw splash written to
MTD5, a CarPlay icon PNG. A newcomer can change the boot logo in one command — that is how
communities start.

On Desay every app ships its UI as a **Rightware Kanzi `.kzb` bundle**, brand-namespaced
(`VW_MP2017*.kzb`, `VW_MP2017_RADIO.kzb`, …) and built by Kanzi Studio against a specific engine
version. There is no PNG to drop in, no splash partition, no `logo.sh` (it is an empty stub), and
no Skoda/Kanzi asset anywhere in the image. **Even a cosmetic mod needs a Kanzi authoring licence,
the right engine version and a rebuild of every package that carries that bundle.** The effort
curve kills casual modding before validation is even reached.

### 2.3 No Android Auto stack ⇒ no "killer feature" to chase

The RCD330 scene was driven by wanting AA on units that lacked it. On NoName the stack is
already in the firmware (`opt/AndroidAuto/bin/aap_service`, `libaap_*.so`, `/etc/aap_dev_hu_*`
certificates, `aap_system_attributes.xml`) — the "patch" only refreshes the HMI so the feature
becomes reachable.

On Desay the stack, the certs and the AA protocol code **do not exist in the image at all**
(verified by full file inventory: CarPlay, CarLife and MirrorLink only). Google never shipped an
AA head-unit stack for WinCE *or* for this Desay Linux build, so there was nothing to backport —
and a head unit needs a valid HU certificate for the AA protocol, which is not something a modder
can mint. The single biggest motivation therefore never existed.

### 2.4 Hardware entry points are physical and expensive

The device is Linux, so a real "custom OS" route exists in principle — but every entry point is
hardware:

- **UART3 / `ttyS2` @115200** console pads on the mainboard (U-Boot + kernel console).
- **MCU (`radio.bin`)** holds tuner, AKM DSP, **CAN coding**, EEPROM/rollback counter ("MU").
- **eMMC** reflash / recovery if an experiment fails.

Contrast with NoName: the updater itself is the entry point, over USB, with no tools.
Compare also the cost of failure: Desay rollback counters are stored in MU and a bad flash is not
undone by re-flashing an older file — a bench recovery setup is a prerequisite, which is exactly
what casual developers do **not** have.

### 2.5 Community gravity: the clone was cheaper and better

The NoName unit ships with AA *and* CarPlay, costs less, and is trivially patchable. Any developer
choosing a target picks that one. The Desay unit became known as "the CarPlay-only one". Scarcity
of buyers ⇒ scarcity of dumps, pinouts, logs and tooling ⇒ no scene. This is self-reinforcing and
is probably the single largest social factor.

### 2.6 Practical/legal friction

Desay firmware ships as whole signed-format `.bin` + sidecar md5 with rollback numbers; there is
no public vendor toolchain, no Kanzi project files, and no published update specification. Even
the *format* had to be reverse engineered from scratch (this repo).

---

## 3. Claim-by-claim verdict on the circulating text

| Claim | Verdict |
|---|---|
| "Desay 187B runs Windows CE 6.0" | **False for this unit** — Linux 3.14.57 / TI DRA72x, proven above. Possibly true for *some other* 187B revision; unverified. |
| "OS is monolithic `Nk.bin`, closed, needs Platform Builder + BSP" | **False for this unit** — components are `svp.bin`, `app-pkg.bin`, `radio.bin`, `os.bin` (gzip/tar/nested uImage packs). No `Nk.bin`. |
| "WinCE escapes to desktop via a USB script; run CorePlayer/GPS" | **Not applicable** — there is no WinCE desktop on this unit. No such mechanism found in its firmware. |
| "NoName bootloader is forgiving, accepts unverified USB packs" | **True** — overlay tars are unsigned and executed as root scripts. |
| "Desay updates are structured/validated, needs an EEPROM programmer to bypass" | **Half true** — updates are validated (md5 API + rollback counters). The bypass route is **not** an EEPROM programmer; it would be U-Boot/UART (and whether md5 is the only check is still open). |
| "AA can't run because Google never built it for WinCE" | **Wrong reason, right outcome** — AA is absent on this Linux build because the stack and HU certificate were never included. |
| "Community interest went to NoName" | **True** — and reinforced by 2.2/2.4/2.5 above. |
| "Developers took AA binaries from the Visteon 187E and backported them" | **Unverified community lore**; the AA stack in NoName packs is the vendor's own AAP SDK + dev certs, so any backport would at most be an HMI/enablement change on units that already had the stack. |

---

## 4. What would change the picture

1. **If `package_is_valid` is only the whole-file MD5** (open question #1 in `STATUS.md`), a
   repacked Desay `.bin` becomes technically flashable. That would turn "no custom firmware
   possible" into "custom firmware possible but effort-heavy (Kanzi rebuild + rollback counter)".
2. **If a Skoda-branded G5 build exists** (`SK_MP2017*.kzb`), theme conversion becomes a firmware
   swap rather than an authoring project.
3. **A read-only UART console session** would immediately give partition map, U-Boot env and boot
   logs — the raw material for any deeper work.
4. **A bench CAN harness** would let us read the MCU coding block, including whether a
   brand/variant byte exists there.

None of these require accepting the WinCE framing — and none of them are blocked by it either.
