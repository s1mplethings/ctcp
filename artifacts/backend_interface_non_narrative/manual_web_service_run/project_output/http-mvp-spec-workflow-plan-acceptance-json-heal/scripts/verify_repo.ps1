$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$required = @(
  (Join-Path $root 'README.md'),
  (Join-Path $root 'scripts\run_project_web.py')
)
$missing = @($required | Where-Object { -not (Test-Path $_) })
if ($missing.Count -gt 0) {
  Write-Output ('missing: ' + ($missing -join ', '))
  exit 1
}
Write-Output 'PASS'
