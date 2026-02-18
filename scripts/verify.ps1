Param(
  [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ArtifactsRoot = Join-Path $Root "artifacts\verify"
$LatestPtr = Join-Path $ArtifactsRoot "latest_proof_path.txt"
$OldProof = $null

if (Test-Path $LatestPtr) {
  $oldDir = (Get-Content $LatestPtr -Raw).Trim()
  if ($oldDir) {
    $oldProofPath = Join-Path $oldDir "proof.json"
    if (Test-Path $oldProofPath) {
      $OldProof = $oldProofPath
    }
  }
}

$cmd = @(
  "python",
  "tools/run_verify.py",
  "--src", "$Root",
  "--build", (Join-Path $Root "build_verify"),
  "--install-prefix", (Join-Path $Root "dist"),
  "--artifacts-root", (Join-Path $Root "artifacts\verify"),
  "--config", $Configuration
)

if ($env:VERIFY_SMOKE_CMD) {
  $cmd += @("--smoke-cmd", $env:VERIFY_SMOKE_CMD)
}
if ($env:VERIFY_SMOKE_PREFIX) {
  $cmd += @("--smoke-prefix", $env:VERIFY_SMOKE_PREFIX)
}
if ($env:VERIFY_CMAKE_ARGS) {
  $items = $env:VERIFY_CMAKE_ARGS -split ';'
  foreach ($i in $items) {
    if ($i.Trim()) { $cmd += @("--cmake-arg", $i.Trim()) }
  }
}
if ($env:VERIFY_CTEST_ARGS) {
  $items = $env:VERIFY_CTEST_ARGS -split ';'
  foreach ($i in $items) {
    if ($i.Trim()) { $cmd += @("--ctest-arg", $i.Trim()) }
  }
}

Write-Host "[verify] run_verify start"
& $cmd[0] $cmd[1..($cmd.Length-1)]
$runRc = $LASTEXITCODE
Write-Host "[verify] run_verify rc=$runRc"

if (-not (Test-Path $LatestPtr)) {
  Write-Error "[verify] latest_proof_path.txt not found: $LatestPtr"
  exit 3
}
$ProofDir = (Get-Content $LatestPtr -Raw).Trim()
if (-not $ProofDir) {
  Write-Error "[verify] empty proof dir pointer"
  exit 4
}
$NewProof = Join-Path $ProofDir "proof.json"

Write-Host "[verify] gate check on $ProofDir"
python tools/adlc_gate.py --proof-dir $ProofDir
$gateRc = $LASTEXITCODE
Write-Host "[verify] adlc_gate rc=$gateRc"

if ($OldProof -and (Test-Path $OldProof) -and (Test-Path $NewProof) -and ($OldProof -ne $NewProof)) {
  $contrastOut = Join-Path $ProofDir "contrast_report.md"
  Write-Host "[verify] writing contrast report: $contrastOut"
  python tools/contrast_proof.py --old $OldProof --new $NewProof --out $contrastOut
}

if ($gateRc -ne 0) {
  exit $gateRc
}
exit 0
