#requires -Version 5.1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
& py -3.11 (Join-Path $root "scripts\validate_publication_repository.py")
if ($LASTEXITCODE -ne 0) {
    throw "Publication repository validation failed."
}
