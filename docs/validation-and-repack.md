# Desay update validation — it is `md5sum`, not a signature

**Status: M1 answered (2026-10-24). Confidence: high.**

The open gate question ("is `svapi_vw_upgrade_package_is_valid` a plain MD5 or a cryptographic
signature?") resolves to: **plain `md5sum` comparison against the shipped `.md5` sidecar. There is
no signature, no certificate and no crypto dependency in the validation path.**

## 1. Where the code lives

`updateservice` imports the `svapi_vw_*` family from **`libsvapi_vw.so.1`**. That library is *not*
in the `svp.bin` app partition — it is in the root filesystem, which is inside `os.bin` as
`targetfs.bin` (gzip → **ext4**, 227 MB, label `rootfs`):

```
/usr/lib/libsvapi_vw.so.1.4.0    27,282 B   exports the upgrade/rollback API
/usr/lib/libsvapi.so.1.3.0      122,938 B   base svapi (display, i2c, USB, GPS…)
/usr/bin/update_program          12,509 B   small CLI wrapper over the two libraries
```

ELF analysis of `libsvapi_vw.so.1.4.0`:

```
DT_NEEDED: librt.so.1 libdrm.so.2 libdrm_omap.so.1 libc.so.6
imports:   38  (no libcrypto, no OpenSSL, no RSA/EVP/signature calls; only memcmp is "crypto-ish")
exports:   svapi_vw_upgrade_package_is_valid   svapi_vw_read_pkg_md5_info
           svapi_vw_rollback_get / _set        svapi_vw_upgrade_copy_to_emmc
           svapi_vw_upgrade_package_to_file    svapi_vw_upgrade_os_package
           svapi_vw_get_version                svapi_exlap_logo_get / _set
```

## 2. The validation code, reconstructed from its own strings

Filtered strings from `libsvapi_vw.so.1.4.0` (full list in
`docs/evidence/desay-validation-strings.txt`):

```
md5sum %s > /tmp/upgrade.md5
/tmp/upgrade.md5
rm -rf /tmp/upgrade.md5
error: Can not open /tmp/upgrade.md5
error: %s md5 no match
%s.md5
%63s %63s %63s %127s
package unvalid
%d the packages is %d, the valid is %d!
name:%s, size=%x, offset=%x, package=%d
svp%d: %s magic-%x, offset-%8x, len-%d
```

So `svapi_vw_upgrade_package_is_valid()` does, in order:

1. locate the package (`<something>.bin`) and its sidecar (`<something>.bin.md5` → `%s.md5`),
2. **shell out**: `md5sum <package> > /tmp/upgrade.md5` (it imports `system`),
3. parse the result and the sidecar with `sscanf("%63s %63s %63s %127s")`,
4. compare → on mismatch: `error: %s md5 no match` → `package unvalid`,
5. clean up `/tmp/upgrade.md5`.

**That is the whole cryptographic story: the integrity model is "md5sum matches the text file we
shipped next to the firmware".** Recomputable by anyone, no keys involved.

## 3. What else is checked (version / rollback)

The same library carries the version logic, matched against the `VERSION:` / `ROLL_BACK_NO:` lines
of the sidecar:

```
the svp_version %s %d        the app_version %s %d
the radio version %s %d      the os version %s %d
the project version %s       the pak_message.version is %s, and the version is %s
the size of the rollback is %d
%s is match, no upgrade      VERSION:%s
%63s %63s %63s %127s
```

Interpretation:

- each component's version in the package is compared with the running version;
- **`%s is match, no upgrade`** = if the package version equals the installed version, that
  component is skipped (useful safety property: reflashing the same build is a no-op, not a risk);
- rollback numbers (`ROLL_BACK_NO`) are collected ("the size of the rollback is %d") and compared
  against the stored counters (`svapi_vw_rollback_get/_set`, `SaveRollBackNoToMU` in
  `updateservice`) → downgrade protection lives in the MCU ("MU"), not in the signature.

Device/scan strings show how packages are found: `/proc/mounts`, `/media/usbstorage{0,1}`,
`/media/hub_usbstorage{0,1}`, `/dev/sd[a-c][13]`, `/dev/mmcblk{0,1,2}[p13]`, `/dev/mtd{0,3}`.

## 4. Consequence for the project

A modified Desay `.bin` **can** pass validation, provided:

1. the component(s) we change are re-packed correctly into the container,
2. the **whole-file md5** is recomputed,
3. the sidecar `.md5` is regenerated with the new hash **and the original `VERSION:` /
   `ROLL_BACK_NO:` lines kept unchanged** (so the version logic sees the same versions and the
   rollback comparison behaves exactly as for the official package).

This is the first time the Desay side has a plausible, evidence-backed modification path:

```
patch component  →  rebuild container (fix record table offsets/sizes)
                 →  md5sum the new .bin
                 →  rewrite sidecar line 1, keep VERSION/ROLL_BACK_NO lines
                 →  package validates like an official one
```

## 5. Remaining unknowns / risks (do not skip)

| Risk | Status |
|---|---|
| `CheckRowChecksum` in `updateservice` — per-row checksum during the eMMC copy? | **open** — must be inspected before flashing; it may be an eMMC write-verify, not a payload check |
| Rollback counter semantics: does re-flashing the *same* versions always pass? | inferred yes (`"is match, no upgrade"`), unverified on the unit |
| Failure during the eMMC copy (power loss) | the real brick risk — needs stable supply and a recovery path |
| `upgrade=1` / `testing=1` boot modes (`upgrade_uenv.txt`, `testing_uenv.txt`) change the boot rootfs to `/dev/mmcblk1p2` | open — understand before using |
| The MCU (`radio.bin`) has its own update path and bootloader | out of scope until Linux-side work is proven |

## 6. Bonus finding for the theme goal

`libsvapi_vw.so.1.4.0` also exports **`svapi_exlap_logo_get` / `svapi_exlap_logo_set`** and logs
`"svapi: load exlap_logo_index, invalid, Using default"`. So the boot/start logo is loaded through
an **exlap logo index** with a default fallback — i.e. the logo may be selectable by a config/index
file rather than only baked into the Kanzi bundle. This is the most promising lead for the Skoda
logo goal on Desay and is now the top of P2.

## 7. Reproduce

```
python tools/desay/osbin_parse.py     # parse os.bin table, extract targetfs.bin / uImage / DTB / MLO / u-boot
python tools/desay/targetfs2.py       # gunzip targetfs.bin -> targetfs.img (ext4), dump upgrade/testing uenv
7z x targetfs.img -o rootfs/          # extract rootfs (7-Zip 21+ reads ext4)
python tools/desay/elf_imports.py     # dynamic deps: prove no libcrypto in libsvapi_vw
python tools/desay/libsvapi_probe.py  # filtered strings + hash-constant signatures
```
