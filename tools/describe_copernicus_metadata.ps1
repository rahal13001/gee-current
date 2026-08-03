[CmdletBinding()]
param(
    [ValidateSet('product', 'dataset')]
    [string]$Scope = 'dataset',
    [string]$ProductId = 'GLOBAL_MULTIYEAR_PHY_001_030',
    [string]$DatasetId = 'cmems_mod_glo_phy_my_0.083deg_P1D-m',
    [switch]$Execute
)

$tool = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\.venv\Scripts\copernicusmarine.exe'))
if (-not (Test-Path -LiteralPath $tool -PathType Leaf)) {
    Write-Error 'copernicusmarine executable was not found in the approved local .venv.'
    exit 1
}

$arguments = @('describe')
if ($Scope -eq 'product') {
    $arguments += @('--product-id', $ProductId)
} else {
    $arguments += @('--dataset-id', $DatasetId)
}
$arguments += @(
    '--return-fields', 'all',
    '--disable-progress-bar',
    '--max-concurrent-requests', '0',
    '--log-level', 'ERROR',
    '--raise-on-error'
)

if (-not $Execute) {
    Write-Output 'mode=PLAN_ONLY'
    Write-Output ('command=' + $tool + ' ' + ($arguments -join ' '))
    Write-Output 'network=NOT_PERFORMED'
    Write-Output 'authentication=NOT_PERFORMED'
    exit 0
}

# Network execution is opt-in and intentionally not used by the Foundation/M0
# offline workflow. This wrapper does not perform login or inspect credentials.
& $tool @arguments
exit $LASTEXITCODE
