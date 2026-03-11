<#
.SYNOPSIS
  CTCP smart auto-commit script
  Version format: X.Y.Z
    X = major principle / architecture change
    Y = normal principle modification
    Z = daily fix / refinement

.DESCRIPTION
  - Only commits when there are real changes + user explicitly invokes
  - Auto-classifies change level and bumps the correct version digit
  - Auto-generates concise commit log
  - Privacy files are never committed (.gitignore + secondary filter)
  - Optionally pushes to origin

.PARAMETER Level
  Manually specify: major / minor / patch.  Auto-detected if omitted.

.PARAMETER NoPush
  Skip push to remote

.PARAMETER DryRun
  Preview only, do not actually commit

.PARAMETER Message
  Append a custom note after the auto-generated summary

.EXAMPLE
  .\scripts\auto_commit.ps1
  .\scripts\auto_commit.ps1 -Level patch
  .\scripts\auto_commit.ps1 -Level minor -Message "refactor bridge"
  .\scripts\auto_commit.ps1 -DryRun
#>
param(
    [ValidateSet("major", "minor", "patch")]
    [string]$Level,
    [switch]$NoPush,
    [switch]$DryRun,
    [string]$Message
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$TAG = 'auto_commit'

$RepoRoot = (git rev-parse --show-toplevel 2>&1) | Select-Object -First 1
if (-not $RepoRoot) { Write-Error 'Not inside a git repo'; exit 1 }
Push-Location $RepoRoot

# ---- Privacy guard: ensure sensitive files never get staged ----
$PrivacyPatterns = @(
    '\.key$', '\.pem$', '\.p12$', '\.pfx$', '\.secret$',
    '\.credentials$', '\.token$', '_token\.txt$',
    'api_key', 'id_rsa', '\.netrc$', '\.npmrc$', '\.pypirc$',
    '[\\/]secrets[\\/]', '[\\/]private[\\/]',
    '[\\/]\.agent_private[\\/]', '[\\/]\.env\b'
)

function Test-PrivacyFile([string]$path) {
    foreach ($p in $PrivacyPatterns) {
        if ($path -match $p) { return $true }
    }
    return $false
}

# ---- Any changes? ----
$StatusLines = git status --porcelain 2>&1
if (-not $StatusLines -or ($StatusLines | Measure-Object).Count -eq 0) {
    Write-Host ('  [{0}] No changes, skip.' -f $TAG) -ForegroundColor Yellow
    Pop-Location; exit 0
}

# ---- Collect changed files + filter privacy ----
$ChangedFiles = @()
$BlockedFiles = @()

foreach ($line in $StatusLines) {
    $raw = $line.ToString().Trim()
    if ($raw.Length -lt 3) { continue }
    $fp = $raw.Substring(2).Trim()
    if ($fp -match '->\s*(.+)$') { $fp = $Matches[1].Trim() }
    $fp = $fp.Trim('"')

    if (Test-PrivacyFile $fp) {
        $BlockedFiles += $fp
    } else {
        $ChangedFiles += $fp
    }
}

if ($BlockedFiles.Count -gt 0) {
    Write-Host ('  [{0}] Privacy guard blocked:' -f $TAG) -ForegroundColor Red
    $BlockedFiles | ForEach-Object { Write-Host "    BLOCKED: $_" -ForegroundColor Red }
}

if ($ChangedFiles.Count -eq 0) {
    Write-Host ('  [{0}] No committable files after filtering.' -f $TAG) -ForegroundColor Yellow
    Pop-Location; exit 0
}

# ---- Auto-detect change level ----
# Rules (strict):
#   major: ONLY when CMakeLists.txt root build system is fundamentally restructured
#          (mere edits to docs/AGENTS.md/contracts do NOT count)
#          User must explicitly pass -Level major for true architectural redesign.
#   minor: src/ include/ executor/ frontend/ contracts/ ctcp/ core executable code,
#          OR scripts/*.py runtime logic, OR core doc rewrites (AGENTS.md, 00_CORE.md etc.)
#   patch: docs/ tests/ meta/ config / daily refinement

function Detect-Level([string[]]$files) {
    $hasMinor = $false

    # major is NEVER auto-detected. Use -Level major explicitly.
    # This prevents accidental major bumps from doc edits or large diffs.

    foreach ($f in $files) {
        # Minor: executable code changes
        if ($f -match '^(src|include|executor|frontend|contracts|ctcp)[\\/]' -or
            $f -match '^scripts[\\/].*\.py$' -or
            $f -match '\.cpp$|\.h$') {
            $hasMinor = $true
        }
        # Minor: core architecture doc changes (but not major)
        elseif ($f -match '^CMakeLists\.txt$' -or
                $f -match '^AGENTS\.md$' -or
                $f -match '^docs[\\/]00_CORE\.md$' -or
                $f -match '^docs[\\/]01_north_star\.md$' -or
                $f -match '^ai_context[\\/]00_AI_CONTRACT\.md$') {
            $hasMinor = $true
        }
        # Minor: any .py file change
        elseif ($f -match '\.py$') {
            $hasMinor = $true
        }
    }

    if ($hasMinor) { return 'minor' }
    return 'patch'
}

if (-not $Level) {
    $Level = Detect-Level $ChangedFiles
    Write-Host ('  [{0}] Auto-detected level: {1}' -f $TAG, $Level) -ForegroundColor Cyan
} else {
    Write-Host ('  [{0}] Manual level: {1}' -f $TAG, $Level) -ForegroundColor Cyan
}

# ---- Read + bump version ----
$VersionFile = Join-Path $RepoRoot 'VERSION'
if (Test-Path $VersionFile) {
    $CurrentVersion = (Get-Content $VersionFile -Raw).Trim()
} else {
    $CurrentVersion = '0.0.0'
}

if ($CurrentVersion -match '^(\d+)\.(\d+)\.(\d+)$') {
    $vMajor = [int]$Matches[1]
    $vMinor = [int]$Matches[2]
    $vPatch = [int]$Matches[3]
} else {
    Write-Error "VERSION format error: $CurrentVersion (expected X.Y.Z)"
    Pop-Location; exit 1
}

switch ($Level) {
    'major' { $vMajor++; $vMinor = 0; $vPatch = 0 }
    'minor' { $vMinor++; $vPatch = 0 }
    'patch' { $vPatch++ }
}
$NewVersion = '{0}.{1}.{2}' -f $vMajor, $vMinor, $vPatch

# ---- Generate concise commit log ----
function Generate-CommitSummary([string[]]$files, [string]$lvl) {
    $groups = @{}
    foreach ($f in $files) {
        $dir = if ($f -match '^([^\\/]+)[\\/]') { $Matches[1] } else { 'root' }
        if (-not $groups.ContainsKey($dir)) { $groups[$dir] = 0 }
        $groups[$dir]++
    }

    $topDirs = $groups.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 3
    $dirSummary = ($topDirs | ForEach-Object { '{0}({1})' -f $_.Key, $_.Value }) -join ', '

    $prefix = switch ($lvl) {
        'major' { 'MAJOR' }
        'minor' { 'UPDATE' }
        'patch' { 'FIX' }
    }

    return ('{0}: {1}' -f $prefix, $dirSummary)
}

$AutoSummary = Generate-CommitSummary $ChangedFiles $Level
if ($Message) {
    $CommitMsg = '{0} {1} -- {2}' -f $NewVersion, $AutoSummary, $Message
} else {
    $CommitMsg = '{0} {1}' -f $NewVersion, $AutoSummary
}

# ---- Preview ----
Write-Host ''
Write-Host '  ========================================' -ForegroundColor Green
Write-Host '    CTCP Auto Commit' -ForegroundColor Green
Write-Host '  ========================================' -ForegroundColor Green
Write-Host ('  Version : {0} -> {1}' -f $CurrentVersion, $NewVersion) -ForegroundColor White
Write-Host ('  Level   : {0}' -f $Level) -ForegroundColor White
Write-Host ('  Message : {0}' -f $CommitMsg) -ForegroundColor White
Write-Host ('  Files   : {0}' -f $ChangedFiles.Count) -ForegroundColor White
Write-Host ''
Write-Host '  File list:' -ForegroundColor Gray
$ChangedFiles | ForEach-Object { Write-Host "    + $_" -ForegroundColor DarkGray }
Write-Host ''

if ($DryRun) {
    Write-Host ('  [{0}] DryRun mode, no commit made.' -f $TAG) -ForegroundColor Yellow
    Pop-Location; exit 0
}

# ---- Execute commit ----
Set-Content $VersionFile $NewVersion -NoNewline -Encoding utf8

foreach ($f in $ChangedFiles) {
    git add $f 2>$null
}
git add VERSION 2>$null

# Double-insurance: unstage any privacy file
foreach ($f in $BlockedFiles) {
    git reset HEAD $f 2>$null
}

git commit -m $CommitMsg 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Error ('  [{0}] Commit failed' -f $TAG)
    Pop-Location; exit 1
}

Write-Host ('  [{0}] Committed: {1}' -f $TAG, $CommitMsg) -ForegroundColor Green

# ---- Push (optional) ----
if (-not $NoPush) {
    $branch = git branch --show-current 2>$null
    if ($branch) {
        Write-Host ('  [{0}] Pushing to origin/{1} ...' -f $TAG, $branch) -ForegroundColor Cyan
        $pushOut = git push origin $branch 2>&1 | Out-String
        Write-Host $pushOut -ForegroundColor DarkGray
        if ($LASTEXITCODE -eq 0) {
            Write-Host ('  [{0}] Push OK' -f $TAG) -ForegroundColor Green
        } else {
            Write-Host ('  [{0}] Push failed (commit saved locally)' -f $TAG) -ForegroundColor Yellow
        }
    }
} else {
    Write-Host ('  [{0}] NoPush flag set, skipping.' -f $TAG) -ForegroundColor Yellow
}

Pop-Location
Write-Host ('  [{0}] Done.' -f $TAG) -ForegroundColor Green
