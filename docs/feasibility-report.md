# VW 187B — Android Auto & Skoda theme: feasibility report

**Date:** 2026-10-24
**Subject:** `6RD 035 187B` (RCD330-family, PQ platform, 6.5") — two vendor families
**Question:** Can the *Desay* unit get Android Auto and a Skoda theme/logo?

---

## 1. TL;DR

| Goal | Desay SV unit (yours, installed) | NoName / "Tianbao" unit |
|---|---|---|
| Android Auto | **Not by firmware.** No AA stack in the image, updater is version/md5/rollback-checked. **Yes, in practice: add a CarPlay→Android-Auto dongle** (reversible, no flashing). | **Yes, by design** — AA stack ships in firmware; a 17 KB overlay tar re-enables it. |
| Skoda boot logo / "theme" | **No practical route.** Logo lives inside a compiled Kanzi `.kzb` UI bundle, the `.bin` package is validated by `updateservice`, and there are **zero Skoda assets** in the Desay image. | **Yes** — it is one `dd` of a raw 800×480 splash into `/dev/mtdblock5` + a Skoda CarPlay icon PNG. |

So: *possible for the NoName family (which you already do), not achievable for the Desay unit.* The Desay unit is a different product with a closed firmware pipeline, not the same hardware+software with a feature switched off.

---

## 2. What the two families actually are

### 2.1 NoName / "Tianbao" (`std_plus_pss-6.5inch_*.tar`)

- **SoC/OS:** NXP i.MX6, Freescale **LTIB** Linux, **kernel 3.0.35** (`etc/rc.d/rc_mxc.S`, `etc/udev/rules.d/10-imx.rules`).
- **UI:** monolithic ELF `opt/hmi` (9.4 MB, ARM, Qt 4.7.4 from `usr/local/qte4.7.4/`) + `opt/gresfiles/*_ovg.bin` graphic resources. Startscreens are plain PNGs (`opt/gresfiles/Startscreens_ASI/EU/NAR/Startscreen_*.png`).
- **Android Auto:** really present — `opt/AndroidAuto/bin/{aap_service,AAP_Application,ConnectionMgr}` + `libaap_{interface,vdplayer,adplayer,adrecorder}.so` + OpenSSL 1.0.0, plus `/etc/aap_system_attributes.xml` and a dev head-unit certificate/key trio (`aap_dev_root_cert.ca.pem`, `aap_dev_hu_cert.date.sign`, `aap_dev_hu_priv_key.key`) configured for 800×480.
- **Update model:** plain `.tar` overlay + `config.txt` switches (`kernel_update/bootloader_update/vip_update/bt_update/middleware_update` and `[file]:[opt|etc|usr|mirrorlink|lib/firmware]`), executed by `/bin/sh` scripts (`script/before_app_update.sh`, `after_app_update.sh`). **No signing, no encryption.** The updater copies the payload and the scripts run `cp`/`dd` as root.
- **Consequence:** any owner can replace UI resources, boot logo, certs, or add binaries. That is why "custom firmware", AA patch and Skoda theme exist only for this family.

Evidence: `20-NoName-Tianbao/V5314_VW-PQ-GP` and `V5515_170421_VW-PQ-GP` tar memberships; `30-Mods-Patches/*`.

### 2.2 Desay SV (`6RD_035_187B_TR7247_SW03xx_*.bin`)

- **Container:** `48 81 48 81 | 02 00 00 00 | <name> | mib2 | ...` header (only ~336 non-zero bytes, rest zero padding to `0x200000`), then **gzip→tar** component payload. At `0x200000` the stream is a valid gzip tar whose members are the application partition (`./bin`, `./lib`, `./share`, `./etc`); 574 files.
- **Payload is not encrypted** (it decompresses) — so the filesystem is *readable*, but that is not the same as *writable* (see §3.2).
- **Platform:** **Texas Instruments DRA72x "Jacinto 6"** (dual Cortex-A15, SGX544 GPU, IPU2) — U-Boot 2014.07-00212-gd0650b9, board env `board=mib2_g`, "Board: Desay-SV G5 Board", device tree **`dra7-g5-r1.dtb`**, **kernel `Linux-3.14.57`** (TI SDK), `mem=1024M`, console `ttyS2` 115200, eMMC/SD + ext4. **Not i.MX6** (earlier "Freescale i.MX Boot Image" hits were generic uImage type-table strings) and **not Windows CE**. Userspace is Desay's own **SVP** service framework (`exlapservice`, `ilmservice`, `appmgr`, `updateservice`, RCF/IPC) on Qt5/Wayland with a **Kanzi** UI (`libUICore-kanzi.so`, `share/ui/*.kzb`). Full BOM: `docs/desay-hardware.md`.
- **Features (complete list found):** `carplayservice` + `libcarplay`, `carlifeservice` + `libcarlife` + Baidu `bdim/bdsc` blobs, `mirrorlinkservice` + `libmirrorlink`. **No `aap_*` anything, no Android Auto certs, no AA binaries.** The absence is genuine, not a hidden flag.
- **Brand assets present:** `share/CarPlay/VWicon_*.png`, `DesaySVicon_*.png`, `Mazdaicon_*.png`; UI bundles all named `Mazda_G5_*.kzb`. i.e. the G5 platform is sold to several brands and *brand is chosen at build time*. **There is no Skoda asset anywhere in the image.**

### 2.3 The two are NOT interchangeable

Different bootloader versions, different kernel, different init/service framework, different partition layout and different updater. Cross-flashing either direction is a brick, not a theme change. Nothing in this library should be flashed to the other family.

---

## 3. Why the Desay unit cannot simply be "converted"

### 3.1 The Skoda theme on the clone is a one-line `dd` — the Desay has no equivalent path

Decoded `30-Mods-Patches/Skoda-Theme/std_plus_pss-6.5inch_logo_skoda.tar`:

```
script/before_app_update.sh:
    dd if=/sysupdate/system/script/logo.bin of=/dev/mtdblock5     # "Flashing new logo to mtd5..."
script/logo.bin : 1,536,004 bytes
```

`1,536,000 = 800 × 480 × 4` — a raw BGRA framebuffer splash (+4 bytes). Rendered it is exactly the **"Welcome to ŠKODA"** screen (see `skoda_logo_preview.png`). Both `logo_skoda.tar` and `logoSK_VW_PQ_GP.tar` carry the *same* `logo.bin` (SHA256 `C8C800ED93DE2638…`); they differ only in tar timestamps. So the celebrated "VW → Skoda conversion" = **boot splash + Skoda CarPlay OEM icon**; the rest of the UI stays VW.

On the Desay:
- `etc/logo.sh` is an **empty stub** (all three cases `power_up/user_on/user_off` do nothing).
- There is **no splash in the bootloader or kernel** at all (`splash` / `logo` / `bootlogo` absent from `os.bin`; no `splashimage` env in U-Boot).
- The startup/lock screen is drawn by the UI, and **branding is a per-app Kanzi bundle**: every
  app package ships `bin/VW_MP2017*.kzb` + `bin/VW_MP2017*.kzb.cfg`. The shared `svp.bin` carries
  only a generic `share/ui/Mazda_G5_Logo.kzb` fallback from the same G5 code base.
- So "Skoda theme" on this platform = a **build variant** (`SK_MP2017*.kzb` or equivalent Skoda
  project). No Skoda bundle exists in this image and there is no runtime brand switch.

### 3.2 The Desay `.bin` is validated by a closed updater with rollback counters

`bin/updateservice` + `libupdate.so.1.0.0` import/expose:

```
svapi_vw_upgrade_package_is_valid      svapi_vw_read_pkg_md5
svapi_vw_read_pkg_md5_info             svapi_vw_upgrade_copy_to_emmc
svapi_vw_rollback_get / _set           CheckRollbackValue / SaveRollBackNoToMU
CheckRowChecksum                       "ERROR: Rollback checksum, will update all"
                                       "OS / SVP / APP / RADIO rollback num:%d"
```

plus versioning strings `UBOOT_VER`, `UIMAGE_VER`, `VIPAP_VER`, `VIPBL_VER`, `BT_VER`, `CODING`, and the shipped `.md5` sidecars that also list `VERSION:` / `ROLL_BACK_NO:` pairs. So the unit checks package validity (md5-based APIs), enforces anti-downgrade counters stored in MU (MCU EEPROM), and copies to eMMC through a privileged service. Repacking the component tar is *theoretically* conceivable if `package_is_valid` reduces to the plain MD5 we can recompute — but that is unproven, and it would still not give you AA or a Skoda UI, because the code and assets do not exist in the image. Rollback counters also mean a mistake is not easily reversible.

**Verdict: no firmware-level AA and no firmware-level Skoda theme for the Desay unit. Confidence: high for the feature/asset absence (direct image inventory), high that the updater validates (API names + sidecar metadata), medium on whether validation is cryptographic.**

### 3.3 Note on `Desay_0318_Red`

`SW0318` ("0318_RED", 2017-09-01) is a *different build* than `SW0358` (2018-03-28) and `SW0317` (2020-03-03), shipped with a Russian thank-you note — i.e. a Red-themed **Desay build existed**. That proves Desay does produce theme variants as builds, which is the only realistic Skoda route: **obtain a Skoda-branded Desay build**, not modify yours.

---

## 4. What is actually worth doing

1. **Android Auto on the Desay unit — use a CarPlay→AA adapter dongle.** Because the unit already runs full wired/wireless CarPlay, an adapter that presents itself as an iPhone and streams Android Auto gives you AA navigation/media on the existing hardware. Zero flashing, fully reversible, keeps your installed unit safe. This is the answer to "make the Desay support Android Auto" in practice.
2. **Skoda look on the Desay unit — not achievable by firmware.** Options: (a) ask a vendor for a Skoda-branded 0317/0318/0358 build (part-number swap, still risks rollback counters), (b) cosmetic badge on the bezel, (c) use one of your NoName units for the Skoda theme + AA — that platform does both.
3. **Keep the families separate.** Flash Desay `.bin` only to Desay, `std_plus_pss` `.tar` only to the clone. Never cross-flash.
4. **If you want to experiment on the NoName units:** the safe, reversible levers are the overlay tars (`30-Mods-Patches`): AA patch, Skoda logo, variant-conflict bypass. They touch only `opt/usr/etc` files or `mtd5`. A USB dump of `mtd5` before flashing gives you a restore file.

---

## 5. Evidence index (all in this library)

| Claim | Source |
|---|---|
| Clone = i.MX6 + LTIB + kernel 3.0.35 | `20-NoName-Tianbao/*` tar: `etc/rc.d/rc_mxc.S`, `etc/udev/rules.d/10-imx.rules`, `etc/issue`, `etc/ltib-release` |
| Clone has AA stack + dev HU certs | `opt/AndroidAuto/bin/aap_service`, `opt/AndroidAuto/lib/libaap_*.so`, `etc/aap_dev_hu_*`, `etc/aap_system_attributes.xml` |
| Clone UI/theme resources | `opt/hmi` (ELF), `opt/gresfiles/Startscreens_*/*.png`, `opt/data/carplay/{Skoda,VW}_Carplay_oemIcon_V1.png` |
| Skoda theme = raw splash to mtd5 | `30-Mods-Patches/Skoda-Theme/*/script/before_app_update.sh`, `script/logo.bin` (decoded: `skoda_logo_preview.png`) |
| Desay = different platform | `.bin`: U-Boot SPL 2014.07 / "Desay-SV G5 Board" / Linux-3.14.57 uImage / G5 platform |
| Desay feature set | `os.bin` tar (574 files): `bin/{carplay,carlife,mirrorlink}service`, `lib/lib{carplay,carlife,mirrorlink}*`, `share/CarLife/*` — no `aap_*` |
| Desay brand assets | `share/CarPlay/{VW,DesaySV,Mazda}icon_*.png`, `share/ui/Mazda_G5_*.kzb` (no Skoda) |
| Desay logo is Kanzi, not raw | `share/ui/Mazda_G5_Logo.kzb` `.KZB` header + `logo` node; `etc/logo.sh` empty stub; `etc/test.sh` `app-run 19 #logo` |
| Desay updater validation | `bin/updateservice`, `lib/libupdate.so.1.0.0` symbols `svapi_vw_upgrade_package_is_valid`, `svapi_vw_read_pkg_md5`, rollback APIs |
| Desay container layout | header `48 81 48 81`…`mib2`, `0x200000` gzip→tar |

Working notes and scripts: `187b/` in the DSH workspace (`desay/`, `noname/`, `theme/`, `notes/`).
