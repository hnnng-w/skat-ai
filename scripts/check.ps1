Write-Host "Running Ruff check..."
python -m ruff check .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Ruff check failed."
    exit $LASTEXITCODE
}

Write-Host "Running JSON schema validation..."
python scripts/validate_examples_schema.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "JSON schema validation failed."
    exit $LASTEXITCODE
}

Write-Host "Running generated output schema validation..."
python scripts/validate_generated_outputs_schema.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Generated output schema validation failed."
    exit $LASTEXITCODE
}

Write-Host "Running tests..."
python -m pytest

if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "All checks passed."