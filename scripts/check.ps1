Write-Host "Running Ruff check..."
python -m ruff check .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Ruff check failed."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Running tests..."
python -m pytest

if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "All checks passed."