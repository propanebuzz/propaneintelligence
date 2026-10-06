# Propane Intelligence

Preserve existing Drive file IDs, workbook formulas, charts, macros and history. Never convert the daily-price XLSM to XLSX without explicit authorization.
Keep credentials, source OPIS reports, raw workbooks and private archives out of Git and public dashboard assets. Ignore rules are only a guard: review staged files before committing.
Read docs/SETUP.md and config/sources.json before integration work. Chat connector authorization does not provide OAuth credentials to standalone scripts.
Upsert by report date. Skip empty reports and reject incomplete OPIS price records. Never guess missing values or turn missing data into zero. Preserve report revisions and provenance.
Stocks are barrels, flow rates barrels/day, propane prices dollars/gallon, WTI dollars/barrel. EIA Product Supplied and regional production/imports include Propane/Propylene. Ready-for-Sale stocks exclude propylene and unfractionated propane. PADDs 4 and 5 flows are combined, stocks separate.
Use one validated dataset for dashboard cards, charts and narrative. Maintain separate source observation, publication and refresh dates. Label analytical scenarios and expose their assumptions. Use actual regional observations and true monthly price averages. Flag historical stock/build inconsistencies rather than silently fixing them.
Run `python3 -m unittest discover -s tests` before committing changed pipeline logic. No live schedule or public-data publication until corresponding end-to-end checks pass.
