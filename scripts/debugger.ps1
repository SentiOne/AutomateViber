$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 (Join-Path $scriptDir "debugger.py") @args
    exit $LASTEXITCODE
}

& python (Join-Path $scriptDir "debugger.py") @args
exit $LASTEXITCODE
