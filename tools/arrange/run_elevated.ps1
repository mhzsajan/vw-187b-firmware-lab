# Launches the arranger in an elevated PowerShell (UAC prompt will appear - click Yes).
$script = 'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\arrange\arrange_187b.ps1'
$log = 'C:\Users\o0o\Documents\deepseek-harness\default-workspace\187b\arrange\arrange.log'
Remove-Item -LiteralPath $log -ErrorAction SilentlyContinue
$p = Start-Process -FilePath 'powershell.exe' -Verb RunAs -PassThru -Wait -ArgumentList @(
  '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$script`""
)
"elevated process exit code: $($p.ExitCode)"
if (Test-Path -LiteralPath $log) { "--- log tail ---"; Get-Content -LiteralPath $log -Tail 40 }
