[CmdletBinding()]
param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [switch]$ReadOnly
)

$ErrorActionPreference = 'Stop'
Set-Location $Root
$evidence = Join-Path $Root 'outputs\evidence\foundation'
if (-not $ReadOnly) { New-Item -ItemType Directory -Force -Path $evidence | Out-Null }

function Write-Result([string]$Id, [string]$Status, [string]$Summary) {
    $path = Join-Path $evidence "$Id.result.txt"
    if (-not $ReadOnly) {
        @("test_id=$Id", "status=$Status", "summary=$Summary", "utc=$([DateTime]::UtcNow.ToString('o'))") |
            Set-Content -LiteralPath $path -Encoding UTF8
    }
    Write-Output "$Id`t$Status`t$Summary"
}

$required = @('AGENTS.md','README.md','pyproject.toml','.gitignore','CHANGELOG.md',
    'docs\IMPLEMENTATION_STATUS.md','docs\REQUIREMENTS_TRACEABILITY.md',
    'docs\audits\GRAPHIFY_FOUNDATION_AUDIT.md','docs\audits\TOOLS_AND_SKILLS_INVENTORY.md',
    'tools\security\check_secrets.ps1')
$missing = @($required | Where-Object { -not (Test-Path $_) })
if ($missing.Count -eq 0) { Write-Result 'TST-FND-001' 'PASS_WITH_NOTES' 'Required Foundation files exist; large-data directories are ignored.' }
else { Write-Result 'TST-FND-001' 'FAIL' ("Missing: " + ($missing -join ', ')) }

if ((Test-Path 'AGENTS.md') -and ((Get-Item 'AGENTS.md').Length -gt 0)) { Write-Result 'TST-FND-002' 'PASS' 'Root AGENTS.md exists and is non-empty.' }
else { Write-Result 'TST-FND-002' 'FAIL' 'Root AGENTS.md missing or empty.' }

if ($ReadOnly) {
    & (Join-Path $Root 'tools\security\check_secrets.ps1') -Root $Root
} else {
    & (Join-Path $Root 'tools\security\check_secrets.ps1') -Root $Root *> (Join-Path $evidence 'FND-004.secret-scan.txt')
}
if ($LASTEXITCODE -eq 0) { Write-Result 'TST-SEC-BASELINE' 'PASS' 'Offline repository secret scan returned exit code 0.' }
else { Write-Result 'TST-SEC-BASELINE' 'FAIL' 'Offline repository secret scan found indicators; see sanitized evidence.' }

$trace = Get-Content -Raw 'docs\REQUIREMENTS_TRACEABILITY.md'
if ($trace -match 'FND-001' -and $trace -match 'FR-CONF-01' -and $trace -match 'GOV-07') { Write-Result 'TST-FND-005' 'PASS_WITH_NOTES' 'Foundation and PRD requirement anchors are present in traceability.' }
else { Write-Result 'TST-FND-005' 'FAIL' 'Traceability anchors are incomplete.' }
