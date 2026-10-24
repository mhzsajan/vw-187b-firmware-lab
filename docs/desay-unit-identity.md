# Unit identity — the actual installed Desay unit

Photos supplied by the owner (`docs/assets/screenshots/`): the unit's *Version information*,
*System status*, and the hidden **internal engineering mode**.

## 1. Reported identity (Version information screen)

| Field | Value |
|---|---|
| HW/SW Version | **036 / 0317** |
| Device part number | **6RD035187B** |
| Radio software version (Radio软件版本) | `Std+ MP2017_PQ_07.54_200303__C` |
| Radio software checksum (Radio软件校验值) | **`0xc473`** |
| APP Version | `MP2017_PQ_07.54_200303__C` |
| SVP Version | `SVP30.6@C1` |
| OS Version | `MIB2-C-V20-20200303` |
| CarIf Version | `v2.29.593.132` |
| Exlap Version | `v2.27.609.10 3.5.2` |
| Bluetooth Version | `c300` |
| Bluetooth Address | `74:95:ec:60:78:53` |
| RadioBootloader Version | `BOOT_2016.09.18` |
| RadioBootloader Checksum | **`0xda8c`** |
| Product serial | `VWZ6Z2R7343266` |
| Production date | `20180810` |
| Apple CarPlay | `CPL24.V1.4.3@C1` |

**This is exactly the `SW0317` build in the library** (`6RD_035_187B_TR7247_SW0317_20200303.bin`).
Its `.md5` sidecar carries the same version strings the screen displays:

```
VERSION:SVP30.6@C1              ROLL_BACK_NO:1
VERSION:MP2017_PQ_07.54_200303__C  ROLL_BACK_NO:1
VERSION:07.54_200303__C         ROLL_BACK_NO:1
PROJECT:GEN2_PQ_MP2017
VERSION:MIB2-C-V20-20200303     ROLL_BACK_NO:5
```

So the file ↔ unit mapping is confirmed, and the version triple on screen is generated from the
package metadata, not from a hardcoded string. **Consequence: a package's version strings are
what the unit believes it is running — and what the rollback logic compares against.**

## 2. Container component table (derived from the same image)

Records of `48 81 48 81` sit at `0x000, 0x200, 0x400, 0x600, 0x800`, each with a
`u32 @+4` that is an **absolute start offset**, `name @+8`, `version @+0x4c`:

| record | value (start offset) | name | version |
|---|---|---|---|
| `0x000` | `2` (record count/type) | `6RD_035_187B_TR7247_SW0317_20200303.bin` | — |
| `0x200` | `0x00200000` | **`svp.bin`** | `SVP30.6@C1` |
| `0x400` | `0x051EC7FB` | **`app-pkg.bin`** | `MP2017_PQ_07.54_200303__C` |
| `0x600` | `0x08402309` | **`radio.bin`** | `07.54_200303__C` |
| `0x800` | `0x08464239` | **`os.bin`** | `MIB2-C-V20-20200303` |

The first 2 MB is a header/padding area; `svp.bin` starts right at `0x200000`, which is why the
earlier `carve.py` extraction of "the application partition" actually walked **`svp.bin`** (it
contains `bin/`, `lib/`, `share/`, `etc/` — the SVP service framework, Kanzi UI, CarPlay icons).

Mapping to the UI:
- `SVP Version` = `svp.bin` version
- `APP Version` / `Radio 软件版本` = `app-pkg.bin` / `radio.bin`
- `OS Version` = `os.bin` version

`docs/evidence/desay-container-components.txt` holds the verification run.

## 3. Hidden internal engineering mode (内部工程模式)

The unit exposes an engineering menu (photo `whatsapp-...30.jpeg`) with:

| Left column | Middle column | Right column |
|---|---|---|
| 版本信息 (version info) | 系统状态 (system status) | 电源管理 (power management) |
| 按键测试 (key test) | EOL Off | 煲机模式 (burn-in mode) |
| 初始化 (initialise) | 倒车摄像 (rear camera) | ENGINE ON/OFF |
| 屏幕测试 (screen test) | 按键背光 (key backlight) | BT调试已关 (BT debug: OFF) |
| USB/CarPlay | MirrorLink | 首次连接 (first connection) |

**System status** shows live diagnostics: `Antenna 11084.2mV/42mA`, `tft/pa/core 36/36/38 °C`,
`Key1/Key2 4059/4046` (ADC), `Mic 0.122mA`, `Battery 11.9V`, `USB 4995mV/0mA`.

**System Information** screen has an **`Update software`** button (photo `aaasd.jpeg`). So the
unit's own UI drives the update path — the same `updateservice`/`libupdate.so` we analysed —
i.e. firmware updates come from a user-supplied package (SD/USB), not a dealer tool. That is
the entry point any Desay-side modification would have to pass through.

What the engineering menu does *not* show: any brand/logo/theme item. Branding is not exposed
as a user or engineering setting on this platform.

## 4. Why this matters for the project

1. **The unit is not a mystery box any more**: we know exactly which package it runs, which
   component carries the UI (`svp.bin`, Kanzi), and where the version strings come from.
2. **The version display comes from package metadata**, so any self-made package would have to
   declare versions consistent with the rollback counters (`ROLL_BACK_NO`) or the unit will
   refuse/flag it.
3. **Two visible checksums** (`0xc473` radio SW, `0xda8c` bootloader) give us a testable way to
   find the integrity algorithm: if they are plain CRC16 over `radio.bin` / the bootloader
   region, we can recompute them after editing. `tools/desay/verify_container.py` hunts for
   matching CRC16 variants.
4. **Engineering mode is available on the unit** — a legitimate, non-destructive surface for
   inspection (system status, key test, USB/CarPlay test) before any flashing idea is attempted.
