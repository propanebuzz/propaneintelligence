# Propane Intelligence

Private data processing and dashboard preview for propane retailers. Setup status and remaining deployment requirements are in [docs/SETUP.md](docs/SETUP.md).

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/run_pipeline.py
```

Google credentials and consent must already be configured privately. The pipeline reads Gmail and the existing Drive workbooks, validates OPIS reports, prepares insert/duplicate/revision plans and builds the six-tab private dashboard. It never writes to Drive. Weekly PDF validation uses `scripts/preview_eia.py`. Source dates, provenance and stale-data warnings accompany the preview.

Live workbook updates, unattended scheduling and public publication remain disabled. This repository contains code only; credentials, original reports, workbooks, normalized snapshots, logs and archives belong outside Git. Public data requires a separate approved export.
