# Setup status

Access checked October 6, 2026. Local clone points to propanebuzz/propaneintelligence. The Propane Intelligence local project is registered. This setup was prepared from the existing workbook-update chat and the earlier Review Dashboard Data Analysis chat.

- GitHub connector: authenticated as jonmillerc3; repository read access yes, push access no. Local Git uses repository-specific propanebuzz credentials through macOS Keychain. The user completed `git push --dry-run origin HEAD:main` successfully. A subsequent authenticated GitHub API check confirmed login propanebuzz and repository push permission. The connector still selects jonmillerc3 and must not be used for propane writes.
- Gmail connector: propanebuzz@gmail.com confirmed. Search returned forwarded OPIS LP Gas Report with 20261005_opislp.pdf. Standalone read-only Google login verified as propanebuzz@gmail.com; refresh-token exchange succeeded. Downloaded 20261005_opislp.pdf privately (473885 bytes). PDF extraction verified visually against pages 1 and 2 and independently compared with Sheet1 row 2: all three report prices and units. Plan: duplicate/no write.
- Drive: Propane_Analytics.xlsx found, same ID and saved version as prior edit. Daily price file retrieved at its existing ID and currently named Daily Prices.xlsm, not XLSX. Preserve its format and workbook package features. Standalone Drive downloads succeeded for both existing IDs; ZIP integrity checked. No Drive files or emails changed during verification. Do not alter either workbook during setup.
- Local Python validation primitives implemented and tested. Read-only Google integration scripts and strict OPIS extraction/preview implemented; a private dashboard preview is built; no write adapter, live scheduler or public dashboard is deployed.

## GitHub access

Keep the jonmillerc3 connector available for StatPig. Do not invite that account as a workaround. Use local Git for this repository with the propanebuzz token stored privately in macOS Keychain. Repository-local credential settings specify username propanebuzz and useHttpPath=true to separate this repository's credential lookup. Token expiration must be tracked and renewed. Never put tokens in source files, remote URLs, chat, or logs.

## Implementation sequence

1. Recover the approved six-tab redesigned dashboard (fep_dashboard_review.html), not Claude's original dashboard. Prior chat titles: Review Dashboard Data Analysis and Update propane analytics workbook. Verify artifact identity before reusing code. Existing analog scenarios are assumptions to audit, not certified forecasts.
2. Implement read-only Gmail and Drive adapters. For standalone Mac scripts, configure Google OAuth separately with refresh-token storage outside the repository. Do not copy connector credentials or log bearer tokens.
3. Archive original reports outside this public repository. Extract report dates from the report itself; email arrival date may differ. Store source hashes, extraction versions and revision records privately.
4. Dry-run against normal, holiday, partial, revised and duplicate reports. Require all three OPIS prices. The earlier chat mentioned a duplicate 10/5 test row; the current Drive daily workbook has 190 valid dated rows and 190 unique dates. No duplicate was found and no reconciliation edit is needed on this snapshot. No guessing or incomplete writes.
5. Implement same-ID Drive updates with before-write backups, concurrency checks, formula/chart/macro preservation and after-write readback. For XLSM, inspect and retain all package parts, including VBA if present.
6. Build one normalized private dataset, then an explicitly approved public export. Recalculate dependent charts, cards and commentary together. OPIS source reports are never public assets.
7. Only after end-to-end success, configure a single owner of the 8 PM America/Chicago job. Audit the earlier schedule before creating another one. Use retries, catch-up, run locks, retained last-good data and failure alerts. Do not enable live updates merely by changing the configuration flag.

## Dashboard requirements from the prior audit

Prioritize Ready-for-Sale propane. Official demand and imports retain the Propane/Propylene definition. Preserve actual regional series and PADD 4/5 combined flows. Separate daily price as-of dates and weekly EIA dates. Compute monthly averages from every supplied observation and identify month-to-date. Compute export-to-production ratios from matching sums. Label the actual count of baseline seasons. Flag stock-change discrepancies without changing history. Scenarios must expose their assumptions and historical periods, not imply a fixed future week is the true peak. Never infer a bullish signal solely from propane/crude ratios.

Later modules: regional HDD forecasts and observed demand, grain drying with dated moisture evidence and harvest progress, and a Natrium/eastern Ohio regional view. Distinguish measurements from estimates.

## Google authorization status

Cloud project propane-intelligence has Gmail and Drive APIs enabled. Desktop client is configured External/In production. Website information and policy pages were published, and the user completed fresh consent as propanebuzz@gmail.com. scripts/google_login.py defaults to read-only authorization; --drive-write requests Drive write consent while Gmail remains read-only. The saved write scope and canEdit on both configured files have been verified; scripts/check_google_access.py verifies refresh, Gmail profile, workbook downloads, and OPIS PDF download. Client JSON and tokens are stored outside the repository in the private credentials folder. Downloaded reports and workbooks are private. Before unattended deployment, replace the client secret exposed in a screenshot and keep production status and replace Testing-era tokens with fresh authorization (completed). Current scopes permit Drive updates. Scheduled processing remains disabled.

## OPIS parser verification

The parser selects Any Current Month Avg for Conway In-Well and Mont Belvieu TET propane; WTI uses the first contract in the settlement table. Conflicting header dates, changed columns, missing/ambiguous rows and incomplete values stop processing. Explicit no-assessment notices with no price rows skip; other unreadable/empty reports require review. Synthetic fixtures test column/product selection, front-month choice, holiday behavior and date/layout errors. Seventeen tests pass across extraction, analytics and recovery safeguards. Current history contains no missing price cells on dated rows. scripts/preview_opis.py stores source/workbook hashes, private normalized history and a no-write plan outside Git. Real holiday and revised-report examples still need end-to-end validation.


## Work completed while website access is pending

The recovered six-tab design now loads a separately generated private snapshot. It prioritizes Ready-for-Sale stocks, removes the propylene residual from displayed analytics, and includes official Product Supplied, its four-week average, imports and their four-week average, PADD production/imports and five separate PADD Ready-for-Sale stocks. The latest attached EIA sample matches the workbook's corresponding fields. Historical values and formulas are preserved; no workbook writes occurred.

Read-only runs archive source files by SHA-256, check Drive versions before/after downloading, search recent OPIS messages for catch-up, reject conflicting same-date candidates, retry transient requests, prevent overlapping runs and retain last-good data on failure. Monthly averages use complete supplied daily history. Historical stock/build differences remain visible as flags. Observation dates and refresh dates stay separate; stale sources trigger warnings.

Run `.venv/bin/python scripts/run_pipeline.py` to refresh the private preview from existing Drive files and prepare an OPIS update plan. Run `.venv/bin/python scripts/preview_eia.py /path/to/report.pdf` to validate a weekly report against the workbook. The report extractor targets the supplied Tables 1/9 layout and requires review when columns change. Its production/import fields retain EIA's Propane/Propylene definition. PADDs 4/5 flows are combined because the report combines them.

Private run reports are in `../propane-private/state/`; dashboard files are in `../propane-private/dashboard-preview/`. Original reports, source workbooks and credentials stay outside Git. Seventeen Python tests and a mocked-DOM execution check cover the six dashboard tabs. Browser visual verification is still pending.

Before unattended operation: finish Google production authorization, obtain fresh consent with the required write scope, implement and validate same-ID workbook updates with preservation/readback checks, validate real holiday and revised reports, audit existing daily scheduling, configure a failure notification destination, and approve any public data export. The current configuration cannot enable Drive writes by itself. Webflow Designer access is needed for website pages and eventual dashboard embedding, but does not block these local processing checks.


## Daily workbook update adapter

` .venv/bin/python scripts/stage_daily_update.py ` prepares a private candidate from the latest validated read-only run. Duplicate and empty reports produce byte-identical candidates. Inserts append complete date/Conway/TET/WTI observations after existing XML rows, leaving the source order and historical row references unchanged; the dashboard sorts observations by date. Changed reports stop for explicit revision review by default. Existing source formulas on the input sheet, Excel tables, or signed packages stop processing rather than being modified blindly.

Cell values are authored through the bundled artifact-tool runtime, then merged into the original package with source numeric/date styles. Every other ZIP part is verified byte-identical, preserving secondary sheets, drawings, relationships, metadata, format and VBA if present. The current daily file contains no formula cells. A synthetic insert on a private copy passed preservation/readback checks; a synthetic VBA part passed unit checks. Native Excel visual verification remains pending.

` .venv/bin/python scripts/apply_daily_update.py ` applies the latest plan only to the configured daily file ID. It checks source version and hash, uses Drive's ETag conditional update, archives a private backup, journals the upload and verifies an exact downloaded-byte match. Uncertain uploads are not automatically retried; unresolved journals block further writes until reviewed. This command is manual and does not enable the recurring schedule. The current real report is a duplicate, so running this command made no changes. A real non-duplicate upload remains untested; mocked upload/readback and conflict tests pass. Twenty-seven Python tests pass in total.

Weekly EIA PDF extraction is available, but same-ID weekly row insertion is not yet implemented. Do not route a partial EIA record through the daily adapter or append an incomplete MasterData row. Automatic revised-report selection, real holiday end-to-end examples, unattended scheduling and notifications remain deployment work. Website permission descriptions should be updated to reflect Drive write authorization before enabling scheduled writes.
