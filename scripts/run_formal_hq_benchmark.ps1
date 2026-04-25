param(
  [string]$BenchmarkZip = "plane_lite_team_pm_test_pack.zip",
  [string]$RunsRoot = "",
  [string]$RunDir = "",
  [ValidateSet("run", "summarize", "archive-golden")]
  [string]$Mode = "run",
  [string]$SummaryOut = "",
  [string]$ChatId = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$env:CTCP_FORCE_PROVIDER = "api_agent"
if (-not $RunsRoot -and $Mode -eq "run") {
  $RunsRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ctcp_formal_hq_benchmark_" + (Get-Date -Format "yyyyMMdd-HHmmss") + "\runs")
}
if ($RunsRoot) {
  $env:CTCP_RUNS_ROOT = $RunsRoot
}

$argsList = @("scripts/formal_benchmark_runner.py", "--profile", "hq", "--mode", $Mode, "--benchmark-zip", $BenchmarkZip)
if ($RunsRoot) { $argsList += @("--runs-root", $RunsRoot) }
if ($RunDir) { $argsList += @("--run-dir", $RunDir) }
if ($SummaryOut) { $argsList += @("--summary-out", $SummaryOut) }
if ($ChatId) { $argsList += @("--chat-id", $ChatId) }

python @argsList
exit $LASTEXITCODE
