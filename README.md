# Propane Intelligence

Private data processing and dashboard preview for propane retailers. Setup status and remaining deployment requirements are in [docs/SETUP.md](docs/SETUP.md).

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/python -m unittest discover -s tests
.venv/bin/python scripts/run_pipeline.py
```

Google credentials and consent must already be configured privately. The pipeline reads Gmail and the existing Drive workbooks, validates OPIS reports, prepares insert/duplicate/revision plans and builds the six-tab private dashboard. The default pipeline does not write to Drive. A separate manual daily-update command is available after Drive write authorization and preservation checks. Weekly PDF validation uses `scripts/preview_eia.py`. Source dates, provenance and stale-data warnings accompany the preview.

Live workbook updates, unattended scheduling and public publication remain disabled. This repository contains code only; credentials, original reports, workbooks, normalized snapshots, logs and archives belong outside Git. Public data requires a separate approved export.


Daily update preparation: `.venv/bin/python scripts/stage_daily_update.py`. Manual same-ID application: `.venv/bin/python scripts/apply_daily_update.py`. Backups and write journals remain private. Revisions stop for review. Complete weekly-row staging and same-ID updates are available through scripts/stage_weekly_update.py and scripts/apply_weekly_update.py. Daily and weekly new-row staging is verified. Guarded unattended updates use the commands below; original reports, workbooks, credentials and journals remain private.

## Automatic dashboard updates

Daily at 8 PM America/Chicago: `scripts/nightly_update.py --apply` reads OPIS reports, validates complete crude/Conway/TET observations, upserts the existing workbook, reads back saved data and publishes only the dashboard export. Weekly at 9:31 AM Central on Wednesdays: `scripts/weekly_release.py --apply` checks EIA’s official release calendar and release-time CSV tables, updates the existing weekly workbook and publishes the refreshed dashboard. A Thursday 11:01 AM holiday check and nightly calendar check cover delayed releases. All commands use `.venv/bin/python`.

The local Codex schedules require the Mac and app to remain running and online. Start time is not a guarantee of completed GitHub Pages deployment at that minute. Incomplete reports, revisions, uncertain uploads or changed workbook versions stop the affected workflow; prior published data remains available. Publishing uses only validated derived market observations and excludes raw reports and credentials. The no-login site is publicly accessible to anyone who obtains its URL.
