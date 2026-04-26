Write-Host "Running Ruff auto-fix..."
python -m ruff check . --fix

if ($LASTEXITCODE -ne 0) {
    Write-Host "Ruff auto-fix failed."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Running Ruff formatter..."
python -m ruff format .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Ruff format failed."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Formatting completed."