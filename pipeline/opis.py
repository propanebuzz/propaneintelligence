"""Strict parser for the observed OPIS North America LPG layout.

Layout changes and incomplete reports require review; source text stays private.
"""
from datetime import datetime
import re
from .records import normalize_opis

VERSION = 'opis-north-america-v1'
DATE_PATTERN = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}'
NUMBER = r'\d+(?:\.\d+)?'


def _table_average(pages, heading, product):
    matches = []
    for page in pages:
        if heading not in page:
            continue
        block = page.split(heading, 1)[1].split('\nOPIS ', 1)[0]
        if not re.search(r'Any Current Month\s+Prompt Current Month\s+Out Month', block):
            raise ValueError('Unrecognized OPIS price-column layout')
        if not re.search(r'Product Low High Avg MTD', block):
            raise ValueError('Unrecognized OPIS price-column labels')
        rows = re.findall(r'^' + re.escape(product) + r'\s+(.+)$', block, re.M)
        for row in rows:
            values = row.split()
            if len(values) != 12 or any(not re.fullmatch(NUMBER, v) for v in values):
                raise ValueError('Incomplete or changed OPIS price row')
            numbers = list(map(float, values))
            if not numbers[0] <= numbers[2] <= numbers[1]:
                raise ValueError('OPIS average falls outside low/high assessment')
            matches.append(numbers[2])
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous OPIS table/product')
    return matches[0]


def parse_pages(pages):
    if not pages or not pages[0].strip():
        raise ValueError('No readable OPIS report text')
    first_date = re.search(DATE_PATTERN, pages[0][:1000])
    if not first_date:
        raise ValueError('Report header date missing')
    report_date = datetime.strptime(first_date[0], '%B %d, %Y').date().isoformat()
    for page in pages[1:]:
        header = re.search(r'OPIS North America LPG Report\s+(' + DATE_PATTERN + ')', page[:1000])
        if header and datetime.strptime(header[1], '%B %d, %Y').date().isoformat() != report_date:
            raise ValueError('Conflicting OPIS report dates')
    text = '\n'.join(pages)
    # A missing table alone is not proof of a holiday: require an explicit notice.
    no_market = re.search(r'(?:no (?:price )?assessments|not published|no market data)', text, re.I)
    price_rows = re.search(r'^(?:TET Propane|Propane)\s+' + NUMBER, text, re.M)
    if no_market and not price_rows:
        return None
    conway = _table_average(pages, 'OPIS Conway In-Well Spot Gas Liquids Prices (cts/gal)', 'Propane')
    tet = _table_average(pages, 'OPIS Mont Belvieu Spot Gas Liquids Prices (cts/gal)', 'TET Propane')
    first = pages[0]
    if 'WTI Crude Oil ($/bbl)' not in first or 'Brent Crude Oil ($/bbl)' not in first:
        raise ValueError('WTI futures section missing')
    futures = first.split('WTI Crude Oil ($/bbl)', 1)[1].split('Brent Crude Oil ($/bbl)', 1)[0]
    contracts = re.findall(r'^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(' + NUMBER + r')\s+', futures, re.M)
    if len(contracts) != 2:
        raise ValueError('Unrecognized WTI front-month futures table')
    return normalize_opis({'date': report_date, 'conway': conway, 'tet': tet,
                           'wti': float(contracts[0][1]), 'propane_unit': 'cents/gal', 'wti_unit': 'USD/bbl'})
