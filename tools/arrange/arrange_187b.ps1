# 187B firmware library arranger - runs ELEVATED (admin).
# Copies E: source tree into a new organised folder on I:, normalises permissions on the copies,
# dedupes byte-identical firmware packs, writes CSV + Markdown manifest.
$ErrorActionPreference = 'Continue'
$SRC = 'E:\01 Win Apps\Car Softs\VW Car Radios Firmwares\187B'
$DST = 'I:\187B-Firmware-Library'
$LOG = 'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\arrange\arrange.log'
$CSV = Join-Path $DST '00-INVENTORY.csv'
$MD  = Join-Path $DST '00-MANIFEST.md'

function Log($m) {
  $ts = (Get-Date).ToString('HH:mm:ss')
  $line = "$ts  $m"
  Write-Host $line
  Add-Content -LiteralPath $LOG -Value $line -Encoding UTF8
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Log "=== start elevated=$isAdmin user=$([Security.Principal.WindowsIdentity]::GetCurrent().Name)"

# source relative path -> destination relative folder
$map = @(
  @{ r='DessaySv\Official 20200303\6RD_035_187B_TR7247_SW0317_20200303.bin';     d='10-Desay-SV-Official\SW0317_2020-03-03'; f='Desay' },
  @{ r='DessaySv\Official 20200303\6RD_035_187B_TR7247_SW0317_20200303.bin.md5'; d='10-Desay-SV-Official\SW0317_2020-03-03'; f='Desay' },
  @{ r='DessaySv\Desay_0318_Red 2\Desay_0318_Red 2\6RD_035_187B_TR7247_SW0318_20170901.bin';     d='10-Desay-SV-Official\SW0318-Red_2017-09-01'; f='Desay' },
  @{ r='DessaySv\Desay_0318_Red 2\Desay_0318_Red 2\6RD_035_187B_TR7247_SW0318_20170901.bin.md5'; d='10-Desay-SV-Official\SW0318-Red_2017-09-01'; f='Desay' },
  @{ r='DessaySv\6RD 035 187B_ SW0358\6RD_035_187B_TR7247_SW0358_20180328.bin';      d='10-Desay-SV-Official\SW0358_2018-03-28'; f='Desay' },
  @{ r='DessaySv\6RD 035 187B_ SW0358\6RD_035_187B_TR7247_SW0358_20180328.bin.md5';  d='10-Desay-SV-Official\SW0358_2018-03-28'; f='Desay' },
  @{ r='NoName\Skoda\Skoda Y510\std_plus_pss-6.5inch_auto210_VW_PQ_GP.tar';         d='20-NoName-Tianbao\V510_auto210_VW-PQ-GP'; f='NoName' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_1014 5314  _VW_PQ_GP.tar';            d='20-NoName-Tianbao\V5314_VW-PQ-GP'; f='NoName' },
  @{ r='NoName\Skoda\Skoda 541 FW5314\std_plus_pss-6.5inch_1014_5314_VW_PQ_GP.tar'; d='20-NoName-Tianbao\V5314_Skoda541_FW5314'; f='NoName' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_170421 5515  _VW_PQ_GP.tar';          d='20-NoName-Tianbao\V5515_170421_VW-PQ-GP'; f='NoName' },
  @{ r='NoName\V5522 Standard\std_plus_pss-6.5inch_5522.tar';                        d='20-NoName-Tianbao\V5522_Standard'; f='NoName' },
  @{ r='NoName\V 5532 Best Sound\std_plus_pss-6.5inch_5532_VW_PQ_ROW.tar';           d='20-NoName-Tianbao\V5532_Best-Sound'; f='NoName' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_5606_166108-7.1.1.2_SKODA_PQ_CN+EN.tar'; d='20-NoName-Tianbao\V5606_Skoda\CN+EN'; f='NoName' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_5606_SKODA_DE_CV.tar';                  d='20-NoName-Tianbao\V5606_Skoda\DE'; f='NoName' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_5606_SKODA_RU+EN.tar';                  d='20-NoName-Tianbao\V5606_Skoda\RU+EN'; f='NoName' },
  @{ r='NoName\Skoda\5606 BT\std_plus_pss-6.5inch_166108-7.1.1.2_SKODA_PQ.tar';       d='20-NoName-Tianbao\V5606_Skoda\166108-BT-variant'; f='NoName' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_SKODA_Y603.tar';                         d='20-NoName-Tianbao\V603_SKODA_Y603'; f='NoName' },
  @{ r='NoName\Skoda\Bluetooth C210 Skoda PQ CR240\std_plus_pss-6.5inch_161108-6.5.5.1_SKODA_PQ_CR240.tar'; d='20-NoName-Tianbao\V6.5.5.1_Y802_SKODA_CR240'; f='NoName' },
  @{ r='NoName\Skoda\Y802\std_plus_pss-6.5inch_161108-6.5.5.1_SKODA_PQ_CR240.tar';    d='20-NoName-Tianbao\_duplicates\Y802'; f='NoName' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_Y802-6.5.5.1_SKODA_PQ_CR240.tar';        d='20-NoName-Tianbao\_duplicates\AIO_Y802'; f='NoName' },
  @{ r='NoName\Skoda\variantconflict_Eror\variantconflict_Eror\std_plus_pss-6.5inch_1014 5314  _VW_PQ_GP.tar'; d='20-NoName-Tianbao\_duplicates\VariantConflict_5314'; f='NoName' },
  @{ r='NoName\Skoda\variantconflict_Eror\variantconflict_Eror\std_plus_pss-6.5inch_170421 5515  _VW_PQ_GP.tar'; d='20-NoName-Tianbao\_duplicates\VariantConflict_5515'; f='NoName' },
  @{ r='NoName\Latest v5624\std_plus_pss-6.5inch_5624_VW_PQ_ROW.tar';                 d='20-NoName-Tianbao\V5624_VW-PQ-ROW'; f='NoName' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_AAP_patch.tar';                          d='30-Mods-Patches\Android-Auto-Patch'; f='Mod' },
  @{ r='NoName\Skoda\Android Auto Recolution Fix\std_plus_pss-6.5inch_AAP_patch.tar'; d='30-Mods-Patches\Android-Auto-Patch\_duplicate'; f='Mod' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_logo_skoda.tar';                         d='30-Mods-Patches\Skoda-Theme'; f='Mod' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_logoSK_VW_PQ_GP.tar';                    d='30-Mods-Patches\Skoda-Theme'; f='Mod' },
  @{ r='NoName\Skoda\AIO\std_plus_pss-6.5inch_VariantConflictByPass.tar';              d='30-Mods-Patches\VariantConflict-Fix'; f='Mod' },
  @{ r='NoName\Skoda\Variant Conflixt Error Fix\std_plus_pss-6.5inch_VariantConflictByPass.tar'; d='30-Mods-Patches\VariantConflict-Fix\_duplicate'; f='Mod' },
  @{ r='NoName\Skoda\variantconflict_Eror\variantconflict_Eror\usb.jpg';               d='30-Mods-Patches\VariantConflict-Fix'; f='Mod' },
  @{ r='DessaySv\6RD 035 187B_ SW0358.zip';                                            d='40-Original-Archives'; f='Archive' },
  @{ r='DessaySv\Desay_0318_Red 2.zip';                                                d='40-Original-Archives'; f='Archive' },
  @{ r='NoName\Skoda\variantconflict_Eror.rar';                                        d='40-Original-Archives'; f='Archive' }
)

if (-not (Test-Path -LiteralPath $DST)) { New-Item -ItemType Directory -Path $DST -Force | Out-Null; Log "created $DST" }

$seen = @{}
$rows = New-Object System.Collections.ArrayList

function Copy-One($srcPath, $dstDirRel, $fam) {
  if (-not (Test-Path -LiteralPath $srcPath)) { Log "MISSING SOURCE: $srcPath"; return }
  $dstDir = Join-Path $DST $dstDirRel
  if (-not (Test-Path -LiteralPath $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
  $leaf = Split-Path -Leaf $srcPath
  $dstPath = Join-Path $dstDir $leaf
  $item = Get-Item -LiteralPath $srcPath
  $hash = ''
  try { $hash = (Get-FileHash -LiteralPath $srcPath -Algorithm SHA256 -ErrorAction Stop).Hash } catch { Log "HASH FAIL: $srcPath : $($_.Exception.Message)" }
  $dupOf = ''
  if ($hash -ne '' -and $seen.ContainsKey($hash)) {
    $dupOf = $seen[$hash]
    Log ("DUP skip: {0}  == {1}" -f $srcPath, $dupOf)
    [void]$rows.Add([pscustomobject]@{ Family=$fam; Folder=$dstDirRel; File=$leaf; SizeMB=[math]::Round($item.Length/1MB,2); SHA256=$hash; DuplicateOf=$dupOf; Source=$srcPath })
    return
  }
  try {
    Copy-Item -LiteralPath $srcPath -Destination $dstPath -Force -ErrorAction Stop
    Log ("COPIED {0,8:N1} MB  {1}" -f ($item.Length/1MB), $srcPath)
  } catch {
    Log "COPY FAILED: $srcPath : $($_.Exception.Message)"
    [void]$rows.Add([pscustomobject]@{ Family=$fam; Folder=$dstDirRel; File=$leaf; SizeMB=[math]::Round($item.Length/1MB,2); SHA256=$hash; DuplicateOf='COPY-FAILED'; Source=$srcPath })
    return
  }
  if ($hash -ne '' -and -not $seen.ContainsKey($hash)) { $seen[$hash] = ($dstDirRel + '\' + $leaf) }
  [void]$rows.Add([pscustomobject]@{ Family=$fam; Folder=$dstDirRel; File=$leaf; SizeMB=[math]::Round($item.Length/1MB,2); SHA256=$hash; DuplicateOf=$dupOf; Source=$srcPath })
}

foreach ($e in $map) { Copy-One (Join-Path $SRC $e.r) $e.d $e.f }

# any additional .rtf notes sitting in the Desay source folders (avoid non-ASCII literals)
Get-ChildItem -LiteralPath (Join-Path $SRC 'DessaySv') -Recurse -Filter '*.rtf' -File -ErrorAction SilentlyContinue | ForEach-Object {
  Copy-One $_.FullName '10-Desay-SV-Official\_notes' 'Desay'
}

Log "granting ACLs on $DST"
$ic1 = & icacls $DST /grant '*S-1-5-32-545:(OI)(CI)M' /T /C /Q 2>&1
Log ("icacls Users: " + (($ic1 | Select-Object -Last 2) -join ' | '))
$ic2 = & icacls $DST /grant 'DESKTOP-00S7DOD\o0o:(OI)(CI)F' /T /C /Q 2>&1
Log ("icacls o0o  : " + (($ic2 | Select-Object -Last 2) -join ' | '))

$rows | Sort-Object Family, Folder, File | Export-Csv -LiteralPath $CSV -NoTypeInformation -Encoding UTF8
Log "wrote $CSV"

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('# VW 187B Firmware Library')
[void]$sb.AppendLine('')
[void]$sb.AppendLine(('Created: ' + (Get-Date).ToString('yyyy-MM-dd HH:mm')))
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## Layout')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('| Folder | What it is |')
[void]$sb.AppendLine('|---|---|')
[void]$sb.AppendLine('| 10-Desay-SV-Official | Genuine Desay SV firmware (.bin + .md5). Official VW build, VW theme only, no Android Auto stack. |')
[void]$sb.AppendLine('| 20-NoName-Tianbao | Community / noname clone firmware (.tar). VW and Skoda packs, Android Auto stack present, moddable by overlay tars. |')
[void]$sb.AppendLine('| 30-Mods-Patches | Small overlay tars: Android Auto patch, Skoda theme/logo, variant-conflict bypass. _duplicate folders hold byte-identical copies from the source tree. |')
[void]$sb.AppendLine('| 40-Original-Archives | Original ZIP/RAR downloads, untouched. |')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('## Files')
[void]$sb.AppendLine('')
[void]$sb.AppendLine('| Family | Folder | File | MB | SHA256 (16) | Duplicate of |')
[void]$sb.AppendLine('|---|---|---|---:|---|---|')
foreach ($r in ($rows | Sort-Object Family, Folder, File)) {
  $h16 = ''
  if ($r.SHA256 -ne '') { $h16 = $r.SHA256.Substring(0,16) }
  [void]$sb.AppendLine(('| ' + $r.Family + ' | ' + $r.Folder + ' | ' + $r.File + ' | ' + $r.SizeMB + ' | ' + $h16 + ' | ' + $r.DuplicateOf + ' |'))
}
Set-Content -LiteralPath $MD -Value $sb.ToString() -Encoding UTF8
Log "wrote $MD"
$uniqueMB = 0
foreach ($k in $seen.Keys) { }
Log '=== done'
