[CmdletBinding()]
param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'
$excluded = @('graphify-out', '.git', '.venv', 'data', 'runs', 'outputs\security', 'outputs\evidence')
$namePatterns = @('(^|[\\/])\.env($|\.)', 'credentials?', 'private.?key', '(^|[\\/])token([_.-]|$)', '\.(pem|key|p12)$')
$contentPatterns = @(
    '(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----',
    '(?i)(password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*[''\"][^''\"]{8,}[''\"]',
    '(?i)AIza[0-9A-Za-z_-]{20,}',
    '(?i)gh[pousr]_[A-Za-z0-9_]{20,}'
)

function Test-Excluded([string]$Path) {
    $relative = $Path.Substring($Root.Length).TrimStart('\', '/').Replace('\', '/')
    foreach ($part in $excluded) {
        $normalizedPart = $part.Replace('\', '/')
        if ($relative -eq $normalizedPart -or $relative.StartsWith("$normalizedPart/")) { return $true }
    }
    return $false
}

$files = Get-ChildItem -LiteralPath $Root -Recurse -File -Force | Where-Object { -not (Test-Excluded $_.FullName) }
$findings = [System.Collections.Generic.List[string]]::new()
$placeholders = [System.Collections.Generic.List[string]]::new()
foreach ($file in $files) {
    $relative = $file.FullName.Substring($Root.Length).TrimStart('\', '/').Replace('\', '/')
    foreach ($pattern in $namePatterns) {
        if ($relative -match $pattern) { $findings.Add("filename:$relative"); break }
    }
    if ($file.Length -gt 2MB) { continue }
    $lineNumber = 0
    foreach ($line in [IO.File]::ReadLines($file.FullName)) {
        $lineNumber++
        foreach ($pattern in $contentPatterns) {
            if ($line -match $pattern) {
                if ($relative.StartsWith("docs/") -and $line -match 'ISI_DI_TERMINAL|<PASSWORD>|<USERNAME>') {
                    $placeholders.Add("documentation-placeholder:${relative}:${lineNumber}")
                } else {
                    $findings.Add("content:${relative}:${lineNumber}")
                }
                break
            }
        }
    }
}

if ($placeholders.Count -gt 0) {
    Write-Output "Documentation placeholders classified (values suppressed): $($placeholders.Count)"
    $placeholders | Sort-Object -Unique | ForEach-Object { Write-Output $_ }
}
$unique = @($findings | Sort-Object -Unique)
if ($unique.Count -gt 0) {
    Write-Output "Potential secret indicators found (values suppressed): $($unique.Count)"
    $unique | ForEach-Object { Write-Output $_ }
    exit 1
}
Write-Output "No potential secret indicators found; values were not printed."
exit 0
