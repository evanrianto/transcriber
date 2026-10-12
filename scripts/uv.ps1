# Runs uv with the given arguments, installing uv first if it isn't available yet.
$ErrorActionPreference = "Stop"

$found = Get-Command uv -ErrorAction SilentlyContinue
if ($found) {
    $uv = $found.Source
} else {
    $uv = Join-Path $HOME ".local\bin\uv.exe"
    if (-not (Test-Path $uv)) {
        Write-Host "uv not found; installing it..."
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    }
}

& $uv @args
exit $LASTEXITCODE
