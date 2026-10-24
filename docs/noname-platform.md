# NoName / "Tianbao" platform — package anatomy

Packs: `std_plus_pss-6.5inch_<version>_<variant>.tar` (~200–250 MB each).
Analysed: `…_1014 5314  _VW_PQ_GP.tar` (6,477 members) and `…_170421 5515  _VW_PQ_GP.tar`.

## 1. Platform

- **NXP i.MX6**, Freescale **LTIB** rootfs, **kernel 3.0.35**
  (`etc/rc.d/rc_mxc.S`, `etc/udev/rules.d/10-imx.rules`, `etc/issue`, `etc/ltib-release`).
- UI: monolithic ARM ELF `opt/hmi` (9.4 MB) built against **Qt 4.7.4**
  (`usr/local/qte4.7.4/lib/libQtGui.so.4.7.4`), with graphic resources in
  `opt/gresfiles/*_ovg.bin` (OpenVG) and tables in `opt/gresfiles/*.dat`.
- Persistent config partition `/pss1`: `etc/rc.d/rcS` copies `/opt/stdplus.ini`,
  `/opt/config`, `/opt/hmi_autotest.ini` there when missing.

## 2. Package layout

Top-level members of a full pack:

```
bt_ac_firm/          Bluetooth module firmware (e.g. UGZZC-X501A_C180)
config.txt           update switches (see below)
etc/                 rootfs overlay: services, aap_* certs, rc scripts
usr/                 rootfs overlay: libs, qte4.7.4, GStreamer 0.10
opt/                 the application: hmi, gresfiles, data, AndroidAuto, lib
lib/, mirrorlink/, script/, var/
kernelImage          uImage payload
u-boot.bin           bootloader image
vipImage.bin         BT/VIP application image
```

`config.txt` (from the 5314 pack) is the whole update policy:

```
kernel_update:1
bootloader_update:1
vip_update:1
bt_update:1
middleware_update:1
[file]:[opt]
[file]:[etc]
[file]:[usr]
[file]:[mirrorlink]
[file]:[lib/firmware]
```

Small overlay packs (AA patch, Skoda logo) reuse the same format with every `*_update:0` and a
single `[file]:[usr]` (or `[opt]`) section, plus `script/before_app_update.sh` /
`script/after_app_update.sh` hooks that run as root during installation.

**No signing, no encryption, no version enforcement in the overlay path.** That is the whole
reason community firmware exists for this family.

## 3. Android Auto

Implemented in `opt/AndroidAuto/`:

```
bin/aap_service            1.7 MB   the projection service
bin/AAP_Application        100 KB   app shell
bin/ConnectionMgr          68 KB    USB/AOA connection manager
bin/aapsdk_interface_test, AAP_TestApp
lib/libaap_interface.so    174 KB
lib/libaap_vdplayer.so, libaap_adplayer.so, libaap_adrecorder.so
lib/libcrypto.so.1.0.0, libssl.so.1.0.0
```

plus `/etc/aap_system_attributes.xml` (head-unit description for the AAP stack: make/model
`Generic`, display **800×480**, PAR 10000) and the certificate trio

```
/etc/aap_dev_root_cert.ca.pem
/etc/aap_dev_hu_cert.date.sign
/etc/aap_dev_hu_priv_key.key
```

The AAP patch (`std_plus_pss-6.5inch_AAP_patch.tar`, 17,920 B) does **not** add the stack; the
stack is already in the base firmware. It:

- ships `script/aap_system_attributes.xml` into the image and
- in `script/before_app_update.sh` does `cp /sysupdate/system/script/hmi /opt`,
  i.e. refreshes the HMI binary from the update staging directory.

Interpretation: AA on this platform is gated by the HMI build + AAP attributes, which is why a
tiny overlay can flip behaviour on units where the projection stack is present but the HMI does
not expose it.

## 4. Brand / theme

Two independent pieces, both plain data:

1. **Boot splash** — a raw framebuffer blob written into an MTD partition by a script:

```sh
# script/before_app_update.sh inside std_plus_pss-6.5inch_logo_skoda.tar
#created by mengxp
echo "Flashing new logo to mtd5..."
dd if=/sysupdate/system/script/logo.bin of=/dev/mtdblock5
```

`script/logo.bin` is **1,536,004 bytes** = `800 × 480 × 4` BGRA + 4 header bytes. Rendered
(`tools/theme/render_logo.py`) it is the *"Welcome to ŠKODA"* screen —
`docs/assets/skoda-logo-preview.png`. Both `logo_skoda.tar` and `logoSK_VW_PQ_GP.tar` carry the
**same** logo blob (SHA-256 `C8C800ED93DE2638…`); they differ only in tar timestamps.

`opt/gresfiles/Startscreens_{ASIA,EU,NAR}/Startscreen_*.png` (Alltrack, Beats_Audio,
Blue_Motion, Dynaudio, E_Golf, GTD, GTE, GTI, Normal, R, R_Line, Twin_Drive) are the *runtime*
start screens — all VW variants in the analysed packs; the Skoda splash comes only from the
overlay tar.

2. **CarPlay OEM icon** — `opt/data/carplay/{VW,Skoda}_Carplay_oemIcon_V1.png`; the Skoda icon
   already ships in the base firmware, so brand theming is a data selection, not code.

## 5. Variant conflict bypass

`std_plus_pss-6.5inch_VariantConflictByPass.tar` replaces `/opt/stdplus.ini` with:

```
[Version] AP_VER=5.5.9.9
CUSTM_PQ=VCPass
CUSTM_MQB=5314
UBOOT_VER=uboot_1.4.0  UIMAGE_VER=uImage_5.1.6  KERNL_VER=3.0.35
BT_VER = C150  VIPAP_VER=5.4.6.6  VIPBL_VER=2.0.3
[Upgrade] PACK_TYPE=VW_PQ_PSS
[CODING] BT=0 CODINGS=0
```

i.e. the "variant conflict" that blocks cross-variant flashing is a version/variant mismatch
recorded in `/opt/stdplus.ini` (and `/pss1/stdplus.ini`); the bypass simply overwrites the
version record so the updater accepts packs meant for another variant.

## 6. Safety notes

- `dd … of=/dev/mtdblock5` is a blind raw write; take a backup of `mtd5` first
  (`dd if=/dev/mtdblock5 of=/usb/logo_backup.bin`) so you can restore the original splash.
- Keep `config.txt` flags consistent: a logo-only or AA-only pack must have every `*_update:0`
  except `middleware_update:1`, otherwise it will try to reflash kernel/bootloader/BT.
