# Desay `6RD 035 187B` — what the unit is made of

Full composition dossier for the **Desay SV** variant of the 187B, derived from the firmware the
unit actually runs (`SW0317` / `MIB2-C-V20-20200303`) plus the owner's engineering-mode photos.
Every claim below is tied to a file/offset or a tool in this repo.

> **Correction to a common claim.** The Desay 187B does **not** run Windows CE. It runs
> **Linux 3.14.57 (TI SDK) on a Texas Instruments DRA72x "Jacinto 6" SoC**, with U-Boot,
> ext4, Wayland/Weston + Qt5 and Rightware Kanzi. Details and proof in §1–§3. The structural
> conclusion for development is the same as WinCE would have implied — the OS is closed and
> image-validated — but the tooling, the attack surface and the modding path are completely
> different (Linux shell, UART console, gzip/tar components, ELF ARM binaries, `.kzb` UI bundles).

---

## 1. Hardware

| Block | What it is | Evidence |
|---|---|---|
| SoC | **TI DRA72x (Jacinto 6)**, dual Cortex-A15 + SGX544 GPU + IPU2 | U-Boot strings `dra72x`, `dra7`; device tree name **`dra7-g5-r1.dtb`**; kernel strings `dra7`, `omapdrm`, `SGX`; `env_setup.sh`: `echo on > /sys/bus/platform/devices/55020000.ipu/power/control` (TI IPU2 address) |
| Board | **`mib2_g`** / "Board: Desay-SV G5 Board", project **G5**, board rev **R1** | U-Boot env `board=mib2_g`, `board_name=mib2_g`; U-Boot banner "Board: Desay-SV G5 Board" |
| RAM | **1024 MB** (`mem=1024M` in the bootargs) | U-Boot env `mem=1024M`; `mmcargs=… mem=1024M …` |
| Boot medium | eMMC (`mmcblk0`) or SD (`mmcblk1`); U-Boot also supports QSPI (`qspiroot=/dev/mmcblk0p1`) and USB (`usbroot=/dev/sda2`) root | U-Boot env `bootcmd`, `mmcroot`, `qspiroot`, `usbroot` |
| Console | **UART3 / `ttyS2` @ 115200n8** | U-Boot env `console=ttyS2,115200n8`; kernel cmdline string |
| Display | 800×480 (Kanzi/Qt UI, DRM/KMS `omapdrm`), `vram=` env var | `omapdrm.num_crtc=1`; UI assets at 800×480 |
| GPU | PowerVR **SGX544** (TI) | kernel string `SGX` |
| Radio MCU | separate ARM Cortex-M class MCU, firmware = **`radio.bin`** (401,200 B) | see §6 |
| Tuner | NXP **"Lithio"** family (TEF668x), I²C, DSP patches `V102` / `V205` | `radio.bin` strings: `Tuner_IIC`, `Tuner_Lithio_InitProcessing`, `Tuner_Lithio_LoadPatch V102/V205`, `load dsp1/dsp2 pram/cram/OFREG` |
| Audio DSP | **AKM** (e.g. AK7738 family) | `radio.bin`: `akmDSP_set_fader` |
| Bluetooth module | **c300** (reported by the unit) | unit screen; `libbt.so`, `libanwbtstack.so` in `svp.bin` |
| CarPlay co-proc / stack | `carplayservice` + `libcarplay.so`; report `CPL24.V1.4.3@C1` | `svp.bin`; unit screen |

The **256 MB / 1 GB** claim: this board/firmware is unambiguously `mem=1024M` = **1 GB**. No
256 MB configuration appears anywhere in this firmware set; if a 256 MB sub-revision exists it
would be a different board variant with different memory config and is **not verified**.

---

## 2. Storage, partitions, boot chain

| Element | Value | Source |
|---|---|---|
| Rootfs | ext4, mounted `ro` at `/` (`root=/dev/mmcblk0p1 ro` or `/dev/mmcblk1p2 rw`) | U-Boot cmdline strings |
| Data partition | **`/dev/mmcblk0p4`** (ext4, rw, re-created by `factory_reset` via `mkfs.ext4`) | `env_setup.sh`: `SVP_DATA_PARTITION=/dev/mmcblk0p4`; `update.sh factory_reset` |
| Update staging | **`/storage/update/`** with `app-pkg/`, `radio.bin`, `dsp.bin`, `gps-boot.bin`, `gps-upgrade.bin` | `env_setup.sh` (`SVP_APP_PKG_PATH`, `SVP_RMT_PKG_FILE`, …) |
| User data | `/storage/data` (`persistservice` keeps state; `SVP_USER_ROOT_PATH`) | `env_setup.sh` |
| Bootloader | **U-Boot 2014.07-00212-gd0650b9 (Mar 03 2020)** — build date matches `SW0317` exactly | U-Boot banner inside `os.bin` |
| Kernel | **Linux 3.14.57**, uImage, load `0x80008000` | uImage header in `os.bin` at `+0x0A00` |
| Recovery paths in U-Boot | `emmc_test`, `update_image dtb`, boot from mmc/qspi/usb/net, `upgrade=1` / `testing=1` bootargs | U-Boot command strings |

The `upgrade=1` / `testing=1` strings in the boot environment are **service/factory boot modes**
selected by U-Boot — worth exploring later (they may change what the userspace updater does).

---

## 3. Software stack (`svp.bin`, 83.8 MB gzip→tar, 574 files)

- **Framework:** Desay **SVP** — `exlapservice` (RCF/IPC "EXLAP"), `ilmservice` (iLM layer),
  `appmgr`, `devicemgr`, `powerctrl`/`powermgr`, `persistservice`, `procguard`, `sourcemgr`,
  `audiomgr` (+ `librace_iface`), `tunerservice`, `btservice`, `mediaservice`, `cameraservice`,
  `carlifeservice`, `carplayservice`, `mirrorlinkservice`, `locationservice`, `updateservice`.
- **UI runtime:** **Qt 5** (`QT_QPA_FONTDIR`, `QT_WAYLAND_SHELL_INTEGRATION=ivi-shell`) on
  **Wayland/Weston** (`. /home/root/.profile`, "weston Environment"), plus **Rightware Kanzi**
  (`libUICore-kanzi.so`, `libuifw-kanzi.so`, `libGeneralCtrls-kanzi.so`) for the 3D/HMI app UI.
- **Multimedia:** GStreamer 1.0.204 with **Cidana** codecs (`libciaudec`, `libcividec`,
  `libcidana_sdk`), ALSA, `avplayer.cfg`.
- **Projection:** CarPlay, Baidu CarLife, MirrorLink — **and nothing for Android Auto**
  (no `aap_*`, no AA certs anywhere). This is a genuine absence, not a disabled flag.
- **Bluetooth:** BlueZ (`run_bluez.sh`, `bluetooth/version`) + `libbt.so`, `libanwbtstack.so`.
- **Boot scripts:** `/svp/etc/{init,test,update,env_setup,appstart,appstop}.sh`, executed by
  `/bin/sh`; `logo.sh` is an **empty hook**.

---

## 4. Application layer (`app-pkg.bin`, 52.5 MB gzip→tar, 17 members)

Each `.pkg` is itself a **gzip→tar** Kanzi application. `install.lst` defines order:

| Package | Role | Brand resource inside |
|---|---|---|
| `vpanel` | vehicle panel / climate overlay | `VW_MP2017_Vpanel.kzb` |
| `update` | SW update UI (must be first) | `VW_MP2017.kzb` |
| `launcher`, `statusbar` | home UI, status bar | `VW_MP2017.kzb` |
| `camera`, `toptip`, `radio` (AM/FM), `bluetooth`, `mediaplayer`, `setting`, `carmenu`, `climate`, `lockscreen`, `engineering`, `production` | per-app Kanzi UIs | `VW_MP2017.kzb` (media: `VW_MP2017_MEDIA.kzb`, radio: `VW_MP2017_RADIO.kzb`) |
| `appconnect` | CarPlay/CarLife/MirrorLink shell | `VW_MP2017.kzb`, `VW_QR_code.png`, `QR_Code_FAW_VW.png` |

Each package: `manifest.xml`, `bin/<app>`, `bin/*.kzb.cfg`, `res/*.kzb`, optional `res/*.png`.
`carplay`, `carlife`, `mirrorlink` packages are **commented out** in `install.lst` — their UI is
provided through `appconnect`.

### 🔑 Brand = the Kanzi bundle name

Every application resolves its UI from a **brand+project namespaced Kanzi bundle**:
**`VW_MP2017*.kzb`** (+ `VW_MP2017.kzb.cfg`). The shared `svp.bin` carries a generic
`share/ui/Mazda_G5_Logo.kzb` fallback from the same G5 code base (Desay sells G5 to other OEMs).

**Therefore: a "Skoda theme" on this platform is a build variant** — Desay would ship
`SK_MP2017*.kzb` in each package (or a Skoda project equivalent). Nothing in this image can be
switched to Skoda at runtime, and no Skoda asset exists anywhere in it. That is the precise,
final answer to the theme question — and it also tells us exactly what a Skoda build would look
like if one exists on the aftermarket.

There is **no boot splash in U-Boot or the kernel** (`splash`/`logo`/`bootlogo` strings absent
from `os.bin`, no `splashimage` env). The splash/lock screen is drawn by the UI from the
`lockscreen` package's `VW_MP2017.kzb` — i.e. a *data* asset, but inside a compiled Kanzi bundle.

---

## 5. Firmware container (recap)

```
0x000000 … 0x001FFF   record table (5 × 0x200): header + svp.bin/app-pkg.bin/radio.bin/os.bin
0x002000  svp.bin       83.8 MB  gzip→tar   userspace (§3)
0x51EC7FB app-pkg.bin   52.5 MB  gzip→tar   Kanzi apps (§4)
0x8402309 radio.bin    401 KB    raw ARM    MCU firmware (§6)
0x8464239 os.bin        83.9 MB  nested pack: kernel 3.14.57 + U-Boot 2014.07 + OS image
EOF       md5(whole file) = the shipped `.md5` sidecar value
```

## 6. `radio.bin` — the MCU firmware (401,200 bytes, plaintext)

Not encrypted (all byte values present but the code/strings are plain ARM Thumb). Strings show
what it does:

```
BOOT_2016.09.18                     ← the "RadioBootloader Version" the unit displays
GEN2_PQ_MP2017 / 07.54_200303__C    ← the "Radio software version" the unit displays
Tuner_IIC / Tuner_Lithio_InitProcessing / CheckVersionValid / LoadPatch V102 / V205
load dsp1|dsp2 pram|cram|OFREG fail  ← NXP Lithio tuner DSP patch loading
akmDSP_set_fader = %d                ← AKM audio DSP control
CAN_DESC_EEP / "Diagnostic Coding Value are : %x %x %x %x %x %x %x"
RK_TUNE / RK_VOLUME lever read from gpio / LED Driver / key click
EEP_VER_170110 / EEP DONE / recover keyboard_backup_error
Radio standby by hour mode / Wakeup by on reboot / Tuner thread / Turer mbx
```

So the MCU owns: tuner + DSP patch loading, AKM audio processing, **CAN diagnostics/coding**,
rotary knobs/keys/LEDs, EEPROM config and standby/wake logic. **VCDS talks to this MCU**, which
is why the unit's diagnostics work while the Linux side is closed — and why a bench setup could
still code the unit even with a CAN gateway in the car.

## 7. Update path & validation (unchanged conclusions)

- User-triggered from the unit's own **System Information → "Update software"**.
- `updateservice` + `libupdate.so`: `svapi_vw_upgrade_package_is_valid`,
  `svapi_vw_read_pkg_md5(_info)`, `svapi_vw_upgrade_copy_to_emmc`, rollback counters in MU.
- Components are staged to `/storage/update/`; `init.sh` picks the mode
  (`apps_only`, `rmt_only`, `apps_and_rmt`, `gps_only`, `factory_reset`).
- **Open gate:** is `package_is_valid` the plain whole-file MD5 (we can recompute it) or a
  signature? Everything else about the format is now known, so this is the single remaining
  question for Desay-side modification.

---

## 8. What can be done — capability matrix

| Tier | Capability | Feasible? | Notes |
|---|---|---|---|
| A | Read versions/diagnostics via **engineering mode** | **yes** | already on the unit; screenshots in `docs/assets/screenshots/` |
| A | **UART console** `ttyS2` 115200 (U-Boot + kernel console) | **likely** — needs board access to pads | biggest lever for "custom OS development": U-Boot prompt gives full partition/boot control; confirm whether the unit is a GP (unsigned boot) device — the kernel/u-boot uImages carry **no signature**, which suggests a GP device |
| A | Bench **CAN + VCDS** coding of the MCU (brand byte? tuning) | **likely** | MCU handles coding (`CAN_DESC_EEP`, diagnostic coding values); needs direct CAN access, not the car's gateway |
| B | Repack **`app-pkg.bin`/`svp.bin`** and rebuild the `.bin` with a new whole-file MD5 | **blocked on P1** (validation type) | format fully understood: gzip→tar, plain assets inside `*.kzb` packages |
| B | Replace **brand/splash assets** with a Skoda set | **blocked** — no Skoda `.kzb` exists; would have to be authored in Kanzi Studio against the same version | asset is data but compiled |
| B | Add **Android Auto** | **no** — stack + certs absent; porting is out of scope | use a CarPlay→AA dongle |
| C | Flash a modified **`radio.bin`** (MCU) | **possible in principle**, high risk | separate MCU with its own bootloader; bricking = radio brick; `rmt_only` path exists |
| C | Build a **custom Linux/OS image** (kernel + userspace) and boot via U-Boot | **only plausible route to a truly modified unit** | requires UART + recovery + rollback-counter bypass; GP-device boot allows it technically |
| D | Cross-flash NoName `.tar` firmware | **never** | different SoC (i.MX6 vs DRA72x), bootloader, partition scheme |

---

## 9. Open questions

1. Is `svapi_vw_upgrade_package_is_valid` a plain MD5 check or cryptographic? (decompilation)
2. Where is the rollback counter stored (MU = MCU EEPROM? a dedicated eMMC partition?), and can
   it be read/written from the Linux side (`persistservice`?).
3. Are the `MIB2-C-*`/`MP2017` names a VW-internal platform tag echoed by the unit, or Desay's own?
4. Is the DRA72x a **GP** (general-purpose, unsigned boot) device? If yes, the U-Boot console
   route becomes a genuine custom-firmware path.
5. Does a **Skoda-branded G5** firmware exist on the aftermarket (would be `SK_MP2017` bundles)?
6. What exactly do the U-Boot `upgrade=1` / `testing=1` boot modes change in userspace?

## 10. Evidence files

`docs/evidence/` — `desay-container-components.txt`, `desay-composition-report.txt`,
`desay-app-packages.txt`, `desay-app-pkg-filelist.txt`, `desay-boot-and-update-scripts.txt`,
`desay-updater-symbols.txt`, `desay-app-partition-filelist.txt`.
Tools: `tools/desay/{container_probe,uimage_probe,carve,get_scripts,probe_update,verify_container,composition_dump,probe_pkg}.py`.
