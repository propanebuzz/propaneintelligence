// Author only the requested numeric cells; preserve the source package separately.
import fs from 'node:fs/promises';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const [planPath, outputPath] = process.argv.slice(2);
const plan = JSON.parse(await fs.readFile(planPath, 'utf8'));
const workbook = Workbook.create();
const sheet = workbook.worksheets.add('Updates');
for (const [address, value] of Object.entries(plan.cells)) {
  if (!/^[A-Z]+[1-9][0-9]*$/.test(address) || typeof value !== 'number' || !Number.isFinite(value)) throw new Error('Invalid numeric cell');
  sheet.getRange(address).values = [[value]];
}
await workbook.recalculate();
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
