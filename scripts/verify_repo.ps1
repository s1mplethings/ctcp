Param(
  [string]$Configuration = "Release",
  [switch]$Full
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildDirLite = Join-Path $Root "build_lite"
$RunFull = $Full -or ($env:CTCP_FULL_GATE -eq "1")
$WriteFixtures = ($env:CTCP_WRITE_FIXTURES -eq "1")
$ModeName = "LITE"
if ($RunFull) { $ModeName = "FULL" }

Write-Host "[verify_repo] repo root: $Root"
Write-Host "[verify_repo] mode: $ModeName"
Write-Host "[verify_repo] write_fixtures: $WriteFixtures"
$BuildArtifactsCommittedMessage = -join ([char[]](
  0x6784,0x5efa,0x4ea7,0x7269,0x88ab,0x63d0,0x4ea4,0x4e86,0xff0c,0x8bf7,0x4ece,
  0x20,0x67,0x69,0x74,0x20,0x4e2d,0x79fb,0x9664,0x5e76,0x66f4,0x65b0,0x20,
  0x2e,0x67,0x69,0x74,0x69,0x67,0x6e,0x6f,0x72,0x65
))

function Invoke-ExternalChecked {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Label,
    [Parameter(Mandatory = $true)]
    [scriptblock]$Command
  )
  & $Command
  if ($LASTEXITCODE -ne 0) {
    Write-Error "[verify_repo] FAILED: $Label (exit=$LASTEXITCODE)"
    exit $LASTEXITCODE
  }
}

function Invoke-Step {
  param(
    [Parameter(Mandatory = $true)]
    [string]$Name,
    [Parameter(Mandatory = $true)]
    [scriptblock]$Block
  )
  Write-Host "[verify_repo] $Name"
  & $Block
}

function Get-CmakeExe {
  $cmd = Get-Command cmake -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $cands = @(
    "C:\Program Files\CMake\bin\cmake.exe",
    "C:\Program Files (x86)\CMake\bin\cmake.exe"
  )
  foreach ($c in $cands) {
    if (Test-Path $c) { return $c }
  }
  return $null
}

function Get-CtestExe {
  $cmd = Get-Command ctest -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $cm = Get-CmakeExe
  if ($cm) {
    $cand = Join-Path (Split-Path -Parent $cm) "ctest.exe"
    if (Test-Path $cand) { return $cand }
  }
  return $null
}

function Invoke-BuildPollutionGate {
  param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot
  )

  Write-Host "[verify_repo] anti-pollution gate (build artifacts)"
  $trackedFiles = @(git -C $RepoRoot ls-files)
  if ($LASTEXITCODE -ne 0) {
    Write-Error "[verify_repo] FAILED: anti-pollution gate (git ls-files) (exit=$LASTEXITCODE)"
    exit $LASTEXITCODE
  }

  $trackedBuild = @($trackedFiles | Where-Object { $_ -like "build*/*" })
  if ($trackedBuild.Count -gt 0) {
    Write-Host "[verify_repo] tracked build artifacts detected (showing up to 20):"
    $trackedBuild | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }
    Write-Host "[verify_repo] $BuildArtifactsCommittedMessage"
    Write-Host "[verify_repo] suggested cleanup commands:"
    Write-Host "  git rm -r --cached build_lite build_verify"
    Write-Host '  git commit -m "Stop tracking build outputs"'
    exit 1
  }

  $unignoredBuild = @(git -C $RepoRoot ls-files --others --exclude-standard -- 'build*/**')
  if ($LASTEXITCODE -ne 0) {
    Write-Error "[verify_repo] FAILED: anti-pollution gate (git ls-files --others) (exit=$LASTEXITCODE)"
    exit $LASTEXITCODE
  }
  if ($unignoredBuild.Count -gt 0) {
    Write-Warning "[verify_repo] detected unignored files under build*/ (showing up to 20)."
    $unignoredBuild | Select-Object -First 20 | ForEach-Object { Write-Warning "  $_" }
    Write-Warning "[verify_repo] Please confirm .gitignore covers build outputs."
  }
}

Invoke-BuildPollutionGate -RepoRoot $Root

$CmakeExe = Get-CmakeExe
$CtestExe = Get-CtestExe
if ($CmakeExe) {
  Invoke-Step -Name "cmake configure (headless lite)" -Block {
    Invoke-ExternalChecked -Label "cmake configure (headless lite)" -Command {
      & $CmakeExe -S $Root -B $BuildDirLite -DCMAKE_BUILD_TYPE=$Configuration "-DCTCP_ENABLE_GUI=OFF" "-DBUILD_TESTING=ON"
    }
  }
  Invoke-Step -Name "cmake build (headless lite)" -Block {
    Invoke-ExternalChecked -Label "cmake build (headless lite)" -Command {
      & $CmakeExe --build $BuildDirLite --config $Configuration
    }
  }
  if ((Test-Path (Join-Path $BuildDirLite "CTestTestfile.cmake")) -and $CtestExe) {
    Invoke-Step -Name "ctest lite" -Block {
      Invoke-ExternalChecked -Label "ctest lite" -Command {
        & $CtestExe --test-dir $BuildDirLite --output-on-failure -C $Configuration -R "headless_smoke|verify_tools_selftest"
      }
    }
  } else {
    Write-Host "[verify_repo] no tests detected or ctest missing in lite build (skip ctest)"
  }
} else {
  Write-Host "[verify_repo] cmake not found; skipping headless build"
}

Invoke-Step -Name "workflow gate (workflow checks)" -Block {
  Invoke-ExternalChecked -Label "workflow gate (workflow checks)" -Command { python scripts\workflow_checks.py }
}

Invoke-Step -Name "contract checks" -Block {
  Invoke-ExternalChecked -Label "contract checks" -Command { python scripts\contract_checks.py }
}

Invoke-Step -Name "doc index check (sync doc links --check)" -Block {
  Invoke-ExternalChecked -Label "doc index check (sync doc links --check)" -Command {
    python scripts\sync_doc_links.py --check
  }
}

Invoke-Step -Name "lite scenario replay" -Block {
  $RunsRoot = Join-Path $Root "simlab\_runs_repo_gate"
  $SummaryOut = Join-Path $Root "simlab\_runs_repo_gate\_lite_summary.json"
  if ($WriteFixtures) {
    $RunsRoot = Join-Path $Root "tests\fixtures\adlc_forge_full_bundle\runs\simlab_lite_runs"
    $SummaryOut = Join-Path $Root "tests\fixtures\adlc_forge_full_bundle\runs\_simlab_lite_summary.json"
  }
  Invoke-ExternalChecked -Label "lite scenario replay" -Command {
    python simlab\run.py --suite lite --runs-root $RunsRoot --json-out $SummaryOut
  }
}

if ($RunFull) {
  Write-Host "[verify_repo] FULL mode enabled via --Full / CTCP_FULL_GATE=1"
  $TestAll = Join-Path $Root "scripts\test_all.ps1"
  if (Test-Path $TestAll) {
    Invoke-Step -Name "tests (full)" -Block {
      Invoke-ExternalChecked -Label "tests (full)" -Command { powershell -ExecutionPolicy Bypass -File $TestAll }
    }
  } else {
    Write-Host "[verify_repo] tests (full): scripts/test_all.ps1 not found (skip)"
  }
}

Write-Host "[verify_repo] OK"
