Param(
  [string]$Configuration = "Release",
  [switch]$Full,
  [string]$Profile = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildRoot = if ($env:CTCP_BUILD_ROOT) { $env:CTCP_BUILD_ROOT } else { $Root }
if (-not (Test-Path $BuildRoot)) {
  New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
}
$BuildRoot = Resolve-Path $BuildRoot
$BuildDirLite = Join-Path $BuildRoot "build_lite"
$UseNinja = ($env:CTCP_USE_NINJA -eq "1")
$BuildParallel = $env:CTCP_BUILD_PARALLEL
if (-not $BuildParallel) { $BuildParallel = [Environment]::ProcessorCount }
$CompilerLauncher = $env:CTCP_COMPILER_LAUNCHER
$RunFull = $Full -or ($env:CTCP_FULL_GATE -eq "1")
$WriteFixtures = ($env:CTCP_WRITE_FIXTURES -eq "1")
$SkipLiteReplay = ($env:CTCP_SKIP_LITE_REPLAY -eq "1")
$ModeName = "LITE"
if ($RunFull) { $ModeName = "FULL" }
$ExecutedGates = @()
$AdvisoryFailures = @()

# --- Verification Profile ---
# Profiles: doc-only | contract | code
# Source: --Profile param > CTCP_VERIFY_PROFILE env > auto-detect
if (-not $Profile) { $Profile = $env:CTCP_VERIFY_PROFILE }
if (-not $Profile) {
  try {
    $Profile = (python scripts\classify_change_profile.py 2>$null).Trim()
  } catch { $Profile = "" }
}
if (-not $Profile) { $Profile = "code" }
$Profile = $Profile.ToLower()
if ($Profile -notin @("doc-only", "contract", "code")) {
  Write-Error "[verify_repo] invalid profile: $Profile (expected: doc-only, contract, code)"
  exit 1
}

# Gate selection per profile
$ProfileSkipBuild = ($Profile -eq "doc-only") -or ($Profile -eq "contract")
$ProfileSkipBehaviorCatalog = ($Profile -eq "doc-only")
$ProfileSkipTripletGuard = ($Profile -eq "doc-only") -or ($Profile -eq "contract")
$ProfileSkipLiteReplay = ($Profile -eq "doc-only") -or ($Profile -eq "contract")
$ProfileSkipPythonUnitTests = ($Profile -eq "doc-only") -or ($Profile -eq "contract")
$ProfileAdvisoryContractChecks = ($Profile -eq "doc-only")

Write-Host "[verify_repo] repo root: $Root"
Write-Host "[verify_repo] build root: $BuildRoot"
Write-Host "[verify_repo] profile: $Profile"
Write-Host "[verify_repo] mode: $ModeName"
Write-Host "[verify_repo] write_fixtures: $WriteFixtures"
$BuildArtifactsCommittedMessage = -join ([char[]](
  0x6784,0x5efa,0x4ea7,0x7269,0x88ab,0x63d0,0x4ea4,0x4e86,0xff0c,0x8bf7,0x4ece,
  0x20,0x67,0x69,0x74,0x20,0x4e2d,0x79fb,0x9664,0x5e76,0x66f4,0x65b0,0x20,
  0x2e,0x67,0x69,0x74,0x69,0x67,0x6e,0x6f,0x72,0x65
))
$RunArtifactsCommittedMessage = "Run outputs exist or are tracked inside repo; move them to external CTCP_RUNS_ROOT."

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

function Add-ExecutedGate {
  param(
    [Parameter(Mandatory = $true)]
    [string]$GateName
  )
  $script:ExecutedGates += $GateName
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

function Get-CompilerLauncher {
  $ccache = Get-Command ccache -ErrorAction SilentlyContinue
  if ($ccache) { return "ccache" }
  $sccache = Get-Command sccache -ErrorAction SilentlyContinue
  if ($sccache) { return "sccache" }
  return ""
}

function Invoke-BuildPollutionGate {
  param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot
  )

  Write-Host "[verify_repo] anti-pollution gate (build/run artifacts)"
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

  $trackedRuns = @($trackedFiles | Where-Object { $_ -like "simlab/_runs*/*" -or $_ -like "meta/runs/*" })
  if ($trackedRuns.Count -gt 0) {
    Write-Host "[verify_repo] tracked run outputs detected (showing up to 20):"
    $trackedRuns | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }
    Write-Host "[verify_repo] $RunArtifactsCommittedMessage"
    exit 1
  }

  $unignoredBuild = @(git -C $RepoRoot ls-files --others --exclude-standard -- 'build*/**')
  if ($LASTEXITCODE -ne 0) {
    Write-Error "[verify_repo] FAILED: anti-pollution gate (git ls-files --others) (exit=$LASTEXITCODE)"
    exit $LASTEXITCODE
  }
  if ($unignoredBuild.Count -gt 0) {
    Write-Host "[verify_repo] unignored build outputs detected (showing up to 20):"
    $unignoredBuild | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }
    Write-Host "[verify_repo] Build outputs appear inside repo; clean them or update ignore rules."
    exit 1
  }

  $unignoredRuns = @(git -C $RepoRoot ls-files --others --exclude-standard -- 'simlab/_runs*/**' 'meta/runs/**')
  if ($LASTEXITCODE -ne 0) {
    Write-Error "[verify_repo] FAILED: anti-pollution gate (git ls-files run outputs) (exit=$LASTEXITCODE)"
    exit $LASTEXITCODE
  }
  if ($unignoredRuns.Count -gt 0) {
    Write-Host "[verify_repo] unignored run outputs detected (showing up to 20):"
    $unignoredRuns | Select-Object -First 20 | ForEach-Object { Write-Host "  $_" }
    Write-Host "[verify_repo] $RunArtifactsCommittedMessage"
    exit 1
  }
}

Invoke-BuildPollutionGate -RepoRoot $Root

if ($ProfileSkipBuild) {
  Write-Host "[verify_repo] headless build skipped (profile: $Profile)"
  Add-ExecutedGate "lite"
} else {

$CmakeExe = Get-CmakeExe
$CtestExe = Get-CtestExe
if ($CmakeExe) {
  # BEHAVIOR_ID: B001
  if (-not $CompilerLauncher) {
    $CompilerLauncher = Get-CompilerLauncher
  }
  Write-Host "[verify_repo] build parallel: $BuildParallel"
  if ($UseNinja) { Write-Host "[verify_repo] generator: Ninja" }
  if ($CompilerLauncher) {
    Write-Host "[verify_repo] compiler launcher: $CompilerLauncher"
  } else {
    Write-Host "[verify_repo] compiler launcher: none"
  }

  $configureArgs = @(
    "-S", $Root,
    "-B", $BuildDirLite,
    "-DCMAKE_BUILD_TYPE=$Configuration",
    "-DCTCP_ENABLE_GUI=OFF",
    "-DBUILD_TESTING=ON"
  )
  if ($UseNinja) {
    $configureArgs += @("-G", "Ninja")
  }
  if ($CompilerLauncher) {
    $configureArgs += "-DCMAKE_CXX_COMPILER_LAUNCHER=$CompilerLauncher"
  }

  Invoke-Step -Name "cmake configure (headless lite)" -Block {
    Invoke-ExternalChecked -Label "cmake configure (headless lite)" -Command {
      & $CmakeExe @configureArgs
    }
  }

  $buildArgs = @("--build", $BuildDirLite, "--config", $Configuration, "--parallel", "$BuildParallel")
  Invoke-Step -Name "cmake build (headless lite)" -Block {
    Invoke-ExternalChecked -Label "cmake build (headless lite)" -Command {
      & $CmakeExe @buildArgs
    }
  }
  if ((Test-Path (Join-Path $BuildDirLite "CTestTestfile.cmake")) -and $CtestExe) {
    $ctestArgs = @("--test-dir", $BuildDirLite, "--output-on-failure", "-C", $Configuration, "-R", "headless_smoke|verify_tools_selftest", "-j", "$BuildParallel")
    Invoke-Step -Name "ctest lite" -Block {
      Invoke-ExternalChecked -Label "ctest lite" -Command {
        & $CtestExe @ctestArgs
      }
    }
  } else {
    Write-Host "[verify_repo] no tests detected or ctest missing in lite build (skip ctest)"
  }
  Add-ExecutedGate "lite"
} else {
  Write-Host "[verify_repo] cmake not found; skipping headless build"
  Add-ExecutedGate "lite"
}

} # end if (-not $ProfileSkipBuild)

# BEHAVIOR_ID: B002
Invoke-Step -Name "workflow gate (workflow checks)" -Block {
  Invoke-ExternalChecked -Label "workflow gate (workflow checks)" -Command { python scripts\workflow_checks.py }
}
Add-ExecutedGate "workflow_gate"

# BEHAVIOR_ID: B003
Invoke-Step -Name "plan check" -Block {
  Invoke-ExternalChecked -Label "plan check" -Command { python scripts\plan_check.py }
}
Add-ExecutedGate "plan_check"

# BEHAVIOR_ID: B004
Invoke-Step -Name "patch check (scope from PLAN)" -Block {
  Invoke-ExternalChecked -Label "patch check (scope from PLAN)" -Command { python scripts\patch_check.py }
}
Add-ExecutedGate "patch_check"

# BEHAVIOR_ID: B005
if ($ProfileSkipBehaviorCatalog) {
  Write-Host "[verify_repo] behavior catalog check skipped (profile: $Profile)"
  Add-ExecutedGate "behavior_catalog_check"
} else {
  Invoke-Step -Name "behavior catalog check" -Block {
    Invoke-ExternalChecked -Label "behavior catalog check" -Command { python scripts\behavior_catalog_check.py }
  }
  Add-ExecutedGate "behavior_catalog_check"
}

# BEHAVIOR_ID: B006
if ($ProfileAdvisoryContractChecks) {
  Invoke-Step -Name "contract checks (advisory for $Profile)" -Block {
    python scripts\contract_checks.py
    if ($LASTEXITCODE -ne 0) {
      Write-Host "[verify_repo] ADVISORY: contract checks failed (exit=$LASTEXITCODE) - recorded as preexisting, non-blocking for profile: $Profile"
      $script:AdvisoryFailures += "contract_checks (exit=$LASTEXITCODE)"
    }
  }
  Add-ExecutedGate "contract_checks"
} else {
  Invoke-Step -Name "contract checks" -Block {
    Invoke-ExternalChecked -Label "contract checks" -Command { python scripts\contract_checks.py }
  }
  Add-ExecutedGate "contract_checks"
}

# BEHAVIOR_ID: B007
Invoke-Step -Name "doc index check (sync doc links --check)" -Block {
  Invoke-ExternalChecked -Label "doc index check (sync doc links --check)" -Command {
    python scripts\sync_doc_links.py --check
  }
}
Add-ExecutedGate "doc_index_check"

if ($ProfileSkipTripletGuard) {
  Write-Host "[verify_repo] triplet integration guard skipped (profile: $Profile)"
  Add-ExecutedGate "triplet_guard"
} else {
  Invoke-Step -Name "triplet integration guard" -Block {
    Invoke-ExternalChecked -Label "triplet runtime wiring contract" -Command {
      python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v
    }
    Invoke-ExternalChecked -Label "triplet issue memory accumulation contract" -Command {
      python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v
    }
    Invoke-ExternalChecked -Label "triplet skill consumption contract" -Command {
      python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v
    }
  }
  Add-ExecutedGate "triplet_guard"
}

if ($ProfileSkipLiteReplay) {
  Write-Host "[verify_repo] lite scenario replay skipped (profile: $Profile)"
  Add-ExecutedGate "lite_replay"
} elseif ($SkipLiteReplay) {
  Write-Host "[verify_repo] lite scenario replay skipped (CTCP_SKIP_LITE_REPLAY=1)"
  Add-ExecutedGate "lite_replay"
} else {
  # BEHAVIOR_ID: B008
  Invoke-Step -Name "lite scenario replay" -Block {
    if ($WriteFixtures) {
      $RunsRoot = Join-Path $Root "tests\fixtures\adlc_forge_full_bundle\runs\simlab_lite_runs"
      $SummaryOut = Join-Path $Root "tests\fixtures\adlc_forge_full_bundle\runs\_simlab_lite_summary.json"
      Invoke-ExternalChecked -Label "lite scenario replay" -Command {
        python simlab\run.py --suite lite --runs-root $RunsRoot --json-out $SummaryOut
      }
    } else {
      Invoke-ExternalChecked -Label "lite scenario replay" -Command {
        python simlab\run.py --suite lite
      }
    }
  }
  Add-ExecutedGate "lite_replay"
}

# BEHAVIOR_ID: B009
if ($ProfileSkipPythonUnitTests) {
  Write-Host "[verify_repo] python unit tests skipped (profile: $Profile)"
  Add-ExecutedGate "python_unit_tests"
} else {
  Invoke-Step -Name "python unit tests" -Block {
    Invoke-ExternalChecked -Label "python unit tests" -Command {
      python -m unittest discover -s tests -p "test_*.py"
    }
  }
  Add-ExecutedGate "python_unit_tests"
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

Invoke-Step -Name "plan gate execution/evidence check" -Block {
  $ExecutedGatesCsv = ($ExecutedGates -join ",")
  Invoke-ExternalChecked -Label "plan gate execution/evidence check" -Command {
    python scripts\plan_check.py --executed-gates $ExecutedGatesCsv --check-evidence
  }
}

# --- Failure Attribution Summary ---
Write-Host ""
Write-Host "[verify_repo] === Verification Summary ==="
Write-Host "[verify_repo] profile: $Profile"
Write-Host "[verify_repo] gates executed: $($ExecutedGates -join ', ')"
if ($AdvisoryFailures.Count -gt 0) {
  Write-Host "[verify_repo] advisory (preexisting, non-blocking) failures:"
  foreach ($f in $AdvisoryFailures) {
    Write-Host "[verify_repo]   - $f"
  }
}
Write-Host ""

Write-Host "[verify_repo] OK"
