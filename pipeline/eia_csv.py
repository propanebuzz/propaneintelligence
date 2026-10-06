"""EIA release-time Tables 1/9 CSV contract; stocks in million barrels, flows in thousand bpd."""
import csv
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import io
import re

VERSION = 'eia-release-csv-v1'


def rows(raw):
    return [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(raw.decode('cp1252')))]


def number(value, scale=1000):
    try:
        value = Decimal(value.replace(',', '')) * scale
    except InvalidOperation:
        raise ValueError('Missing or unsupported EIA CSV value') from None
    if not value.is_finite():
        raise ValueError('Non-finite EIA CSV value')
    return float(value)


def block(table, section, product):
    hits = [i for i, r in enumerate(table) if len(r) >= 2 and r[:2] == [section, product]]
    if len(hits) != 1:
        raise ValueError('Missing or ambiguous EIA CSV section: ' + section + '/' + product)
    index = hits[0]
    national = table[index]
    if len(national) != 8:
        raise ValueError('EIA Table 9 columns changed')
    regions = {}
    for row in table[index + 1:]:
        if len(row) != 8 or row[0] != section or not re.search(r'PADD', row[1]):
            break
        if row[1] in regions:
            raise ValueError('Duplicate EIA regional row')
        regions[row[1]] = row
    return national, regions


def parse_tables(table1, table9, today=None):
    one, nine = rows(table1), rows(table9)
    if not one or not nine or one[0][0] != 'STUB_1' or nine[0][:2] != ['STUB_1', 'STUB_2']:
        raise ValueError('EIA CSV headers changed')
    day = datetime.strptime(one[0][1], '%m/%d/%y').date()
    if day.weekday() != 4 or day > (today or date.today()):
        raise ValueError('Invalid EIA observation date')
    if nine[0][2] != one[0][1] or len(nine[0]) != 8 or nine[0][6] != one[0][1]:
        raise ValueError('EIA tables are from different releases or columns changed')
    supply_headers = [r for r in one if r[:2] == ['STUB_1', 'STUB_2']]
    if len(supply_headers) != 1 or len(supply_headers[0]) != 13 or supply_headers[0][2] != one[0][1] or supply_headers[0][7] != one[0][1]:
        raise ValueError('EIA Table 1 supply headers changed')
    stocks = [r for r in one if r[0] == 'Propane/Propylene']
    demand = [r for r in one if len(r) == 13 and r[0] == 'Products Supplied' and re.fullmatch(r'\(\d+\)\s+Propane/Propylene', r[1])]
    if len(stocks) != 1 or len(stocks[0]) != 8 or len(demand) != 1:
        raise ValueError('EIA Table 1 propane rows changed')
    result = {'date': day.isoformat(), 'inv_bbl': number(stocks[0][1], 1000000),
              'build_bbl': number(stocks[0][3], 1000000),
              'product_supplied_bpd': number(demand[0][2]),
              'product_supplied_4wk_bpd': number(demand[0][7])}
    labels = [('East Coast (PADD 1)', 'padd1'), ('Midwest (PADD 2)', 'padd2'),
              ('Gulf Coast (PADD 3)', 'padd3'), ('PADDs 4 and 5', 'padd45')]
    for section, key in [('Refiner and Blender Net Production', 'production'), ('Imports', 'imports')]:
        national, regions = block(nine, section, 'Propane/Propylene')
        result[key + '_bpd'] = number(national[2])
        result[key + '_4wk_bpd'] = number(national[6])
        for label, region in labels:
            if label not in regions: raise ValueError('Missing EIA regional flow')
            result[region + '_' + key + '_bpd'] = number(regions[label][2])
        if abs(sum(result[r + '_' + key + '_bpd'] for _, r in labels) - result[key + '_bpd']) > 4000:
            raise ValueError('EIA regional flows do not reconcile')
    total, regions = block(nine, 'Stocks (Million Barrels)', 'Propane/Propylene')
    if number(total[2], 1000000) != result['inv_bbl']:
        raise ValueError('EIA national stocks differ between tables')
    for label, key in [('Midwest (PADD 2)', 'midwest_bbl'), ('Gulf Coast (PADD 3)', 'gulf_bbl')]:
        if label not in regions: raise ValueError('Missing EIA regional stock')
        result[key] = number(regions[label][2], 1000000)
    ready, regions = block(nine, 'Stocks (Million Barrels)', 'Propane, fractionated and ready for sale')
    result['ready_bbl'] = number(ready[2], 1000000)
    for label, region in labels[:3] + [('Rocky Mountain (PADD 4)', 'padd4'), ('West Coast (PADD 5)', 'padd5')]:
        if label not in regions: raise ValueError('Missing EIA Ready-for-Sale stock')
        result[region + '_ready_bbl'] = number(regions[label][2], 1000000)
    if abs(sum(result[f'padd{i}_ready_bbl'] for i in range(1, 6)) - result['ready_bbl']) > 5000:
        raise ValueError('EIA Ready-for-Sale stocks do not reconcile')
    exports, _ = block(nine, 'Exports', 'Propane')
    result['exports_bpd'] = number(exports[2])
    if any(v < 0 for k, v in result.items() if k not in ('date', 'build_bbl')):
        raise ValueError('Negative EIA stock or flow')
    return result
