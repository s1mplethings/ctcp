$ErrorActionPreference='Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
Push-Location $Root
try {
  python -m pytest -q tests/test_smoke.py tests/test_pipeline_synth.py tests/test_clean_project.py
} finally {
  Pop-Location
}
