Param(
  [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildDir = Join-Path $Root "build"

Write-Host "[verify_repo] repo root: $Root"

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

function Get-Qt6ConfigDir {
  if ($env:Qt6_DIR) {
    $direct = Join-Path $env:Qt6_DIR "Qt6Config.cmake"
    if (Test-Path $direct) { return $env:Qt6_DIR }
  }

  if ($env:CMAKE_PREFIX_PATH) {
    $prefixes = $env:CMAKE_PREFIX_PATH -split ';'
    foreach ($p in $prefixes) {
      if (-not [string]::IsNullOrWhiteSpace($p)) {
        $cands = @(
          $p,
          (Join-Path $p "lib/cmake/Qt6"),
          (Join-Path $p "cmake/Qt6")
        )
        foreach ($c in $cands) {
          if (Test-Path (Join-Path $c "Qt6Config.cmake")) { return $c }
        }
      }
    }
  }

  if (Get-Command qmake -ErrorAction SilentlyContinue) {
    $qtPrefix = (& qmake -query QT_INSTALL_PREFIX 2>$null).Trim()
    if ($qtPrefix) {
      $cands = @(
        (Join-Path $qtPrefix "lib/cmake/Qt6"),
        (Join-Path $qtPrefix "cmake/Qt6")
      )
      foreach ($c in $cands) {
        if (Test-Path (Join-Path $c "Qt6Config.cmake")) { return $c }
      }
    }
  }

  return $null
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

# 1) Build (best-effort)
$CmakeExe = Get-CmakeExe
if ($CmakeExe) {
  $Qt6ConfigDir = Get-Qt6ConfigDir
  if ($Qt6ConfigDir) {
    Write-Host "[verify_repo] Qt6 config detected: $Qt6ConfigDir"
    Invoke-Step -Name "cmake configure" -Block {
      Invoke-ExternalChecked -Label "cmake configure" -Command {
        & $CmakeExe -S $Root -B $BuildDir -DCMAKE_BUILD_TYPE=$Configuration "-DCMAKE_PREFIX_PATH=$Qt6ConfigDir"
      }
    }
    Invoke-Step -Name "cmake build" -Block {
      Invoke-ExternalChecked -Label "cmake build" -Command {
        & $CmakeExe --build $BuildDir --config $Configuration
      }
    }

    $CTestFile = Join-Path $BuildDir "CTestTestfile.cmake"
    if ((Test-Path $CTestFile) -and (Get-Command ctest -ErrorAction SilentlyContinue)) {
      Invoke-Step -Name "ctest" -Block {
        Invoke-ExternalChecked -Label "ctest" -Command {
          ctest --test-dir $BuildDir --output-on-failure
        }
      }
    } else {
      Write-Host "[verify_repo] no tests detected (skipping ctest)"
    }
  } else {
    Write-Host "[verify_repo] Qt6 SDK not found; skipping C++ build"
  }
} else {
  Write-Host "[verify_repo] cmake not found; skipping C++ build"
}

# 2) Web build (best-effort)
$WebPkg = Join-Path $Root "web\package.json"
if (Test-Path $WebPkg) {
  Write-Host "[verify_repo] web/package.json detected"
  if (Get-Command npm -ErrorAction SilentlyContinue) {
    Push-Location (Join-Path $Root "web")
    if (Test-Path "package-lock.json") {
      Invoke-ExternalChecked -Label "npm ci" -Command { npm ci }
    } else {
      Invoke-ExternalChecked -Label "npm install" -Command { npm install }
    }
    node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts.build ? 0 : 1)"
    if ($LASTEXITCODE -eq 0) {
      Invoke-ExternalChecked -Label "npm run build" -Command { npm run build }
    } else {
      Write-Host "[verify_repo] no npm build script (skipping)"
    }
    Pop-Location
  } else {
    Write-Host "[verify_repo] npm not found; skipping web build"
  }
} else {
  Write-Host "[verify_repo] no web frontend detected (web/package.json missing)"
}

# 3) Workflow checks (hard)
Invoke-Step -Name "workflow gate (workflow checks)" -Block {
  Invoke-ExternalChecked -Label "workflow gate (workflow checks)" -Command { python scripts\workflow_checks.py }
}

# 4) Contract checks (hard)
Invoke-Step -Name "contract checks" -Block {
  Invoke-ExternalChecked -Label "contract checks" -Command { python scripts\contract_checks.py }
}

# 5) Sync doc links (hard)
Invoke-Step -Name "doc index check (sync doc links --check)" -Block {
  Invoke-ExternalChecked -Label "doc index check (sync doc links --check)" -Command {
    python scripts\sync_doc_links.py --check
  }
}

# 6) Tests (optional)
$TestAll = Join-Path $Root "scripts\test_all.ps1"
if (Test-Path $TestAll) {
  Invoke-Step -Name "tests" -Block {
    Invoke-ExternalChecked -Label "tests" -Command { powershell -ExecutionPolicy Bypass -File $TestAll }
  }
} else {
  Write-Host "[verify_repo] tests: scripts/test_all.ps1 not found (skip)"
}

Write-Host "[verify_repo] OK"
