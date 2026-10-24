# tools

All scripts were written during the initial analysis on Windows (Python 3.12 from the DSH
runtime, plus PowerShell 5.1 for the organiser). Paths are currently absolute — edit the
constants at the top of each script (`SRC`, `E`, `DESAY`, `PACKS`, `OUT`) to match your machine.

| Script | Purpose |
|---|---|
| `scan_magics.py` | Scan any blob for container/filesystem signatures (gzip, xz, squashfs, cramfs, UBI, uImage, ELF, ext, GPT, zip…) plus ASCII preview. Works on 200 MB+ files in chunks. |
| `desay/container_probe.py` | Dump the Desay `.bin` header, verify the gzip stream at `0x200000`, entropy/compressibility profile, ASCII strings around the component table, AAP/CarPlay hits. |
| `desay/uimage_probe.py` | Find and parse U-Boot uImage headers (OS/arch/kernel name) and ELF headers inside a Desay image. This is what identified `Linux-3.14.57` and `U-Boot 2014.07-00209-g36d39ae`. |
| `desay/carve.py` | Stream `gzip` → `tar` from `0x200000` and list/extract the application partition (574 members). |
| `desay/get_scripts.py` | Extract `etc/*.sh`, `etc/app.conf`, `share/AccountInfo.txt` from the Desay partition as text. |
| `desay/probe_update.py` | Extract `updateservice`, `libupdate.so`, `<Brand>_G5_Logo.kzb`, a CarPlay icon and dump verification-related symbols/strings. |
| `desay/scan_desay.py` | Bulk keyword + filesystem-signature scan across both readable Desay builds. |
| `noname/probe.py` | NoName `.tar` package inventory: member counts, biggest files, `opt/AndroidAuto`, `gresfiles` startscreens, `opt/data/carplay`, dumps `config.txt` / `aap_system_attributes.xml` / rc scripts. |
| `theme/render_logo.py` | Convert a NoName `logo.bin` (800×480 BGRA + 4 header bytes) to PNG. |
| `arrange/arrange_187b.ps1` | Build the organised firmware library: copies the source tree into a new folder, dedupes by SHA-256, normalises ACLs on the copies, writes `00-INVENTORY.csv` + `00-MANIFEST.md`. Run elevated (`arrange/run_elevated.ps1`). |

## Notes

- `render_logo.py` needs Pillow (`pip install pillow`).
- The organiser exists because the original files were owned by `Administrators` only — a
  standard user cannot even read them, so an elevated copy that inherits the destination ACL is
  the way to get readable, verifiable copies.
- Extraction scripts use a seekable `Slice` wrapper around a 200 MB+ file instead of reading it
  fully into memory; keep that pattern for large images.
