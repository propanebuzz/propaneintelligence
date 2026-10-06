"""Merge artifact-authored numeric values into an existing OOXML package.

No source workbook round-trip: untouched ZIP parts and worksheet XML remain exact.
"""
from datetime import date
from io import BytesIO
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from .records import normalize_opis,classify_upsert
from .workbooks import daily_prices

NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def daily_plan(path,records,allow_revisions=False):
    history=daily_prices(path)
    existing=[dict(date=r['date'],conway=r['cwy'],tet=r['tet'],wti=r['wti'],propane_unit='USD/gal',wti_unit='USD/bbl') for r in history]
    with ZipFile(path) as z:
        root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        if root.find('.//s:f',NS) is not None:raise ValueError('Daily input sheet now contains formulas; review required')
        if any('table' in n.lower() or 'signature' in n.lower() for n in z.namelist()):raise ValueError('Tables or digital signatures require a separate preservation workflow')
        next_row=max(int(r.attrib['r']) for r in root.findall('s:sheetData/s:row',NS))+1
    cells={};actions=[];seen=set()
    for raw in sorted(records,key=lambda r:r.get('date','') if r else ''):
        record=normalize_opis(raw)
        if record and record['date'] in seen:raise ValueError('Multiple candidate records for one date')
        if record:seen.add(record['date'])
        action=classify_upsert(existing,record)
        actions.append({'date':record['date'] if record else None,'action':action})
        if action in ('duplicate','skip_empty'):continue
        if action=='revision':
            if not allow_revisions:raise ValueError('Report revision requires explicit review; no candidate written')
            row=next(r['row'] for r in history if r['date']==record['date'])
        else:
            row=next_row;next_row+=1
        serial=(date.fromisoformat(record['date'])-date(1899,12,30)).days
        cells.update({f'A{row}':serial,f'B{row}':record['conway'],f'C{row}':record['tet'],f'D{row}':record['wti']})
    return {'sheet_part':'xl/worksheets/sheet1.xml','cells':cells,'actions':actions}


def merge_numeric(source,authored,plan):
    if not plan['cells']:return source
    part=plan['sheet_part']
    with ZipFile(BytesIO(authored)) as a:
        root=ET.fromstring(a.read('xl/worksheets/sheet1.xml'))
        values={c.attrib['r']:c.find('s:v',NS).text for c in root.findall('s:sheetData/s:row/s:c',NS) if c.find('s:v',NS) is not None}
    if set(values)!=set(plan['cells']):raise ValueError('Authored cell set differs from approved plan')
    for address,value in values.items():
        if float(value)!=float(plan['cells'][address]):raise ValueError('Authored numeric value differs from plan')
    with ZipFile(BytesIO(source)) as z:
        xml=z.read(part).decode('utf-8')
        rows={int(m.group(1)):m for m in re.finditer(r'<row\b[^>]*\br="(\d+)"[^>]*>.*?</row>',xml,re.S)}
        if 2 not in rows:raise ValueError('Input row style template missing')
        template=rows[2].group()
        grouped={}
        for address,value in values.items():grouped.setdefault(int(re.search(r'\d+$',address)[0]),{})[address]=value
        new_rows=[]
        for row,updates in sorted(grouped.items()):
            old=rows.get(row)
            text=old.group() if old else f'<row r="{row}" ht="15.75" customHeight="1"></row>'
            for address,value in sorted(updates.items()):
                column=re.match(r'[A-Z]+',address)[0]
                pattern=rf'<c\b[^>]*\br="{address}"[^>]*(?:/>|>.*?</c>)'
                match=re.search(pattern,text,re.S)
                if match:
                    cell=match.group()
                    if '<f' in cell or 't="s"' in cell or 't="inlineStr"' in cell:raise ValueError('Refusing to overwrite formula/text input')
                    opening=cell.split('>')[0].rstrip('/')+'>'
                    updated=opening+f'<v>{value}</v></c>'
                    text=text[:match.start()]+updated+text[match.end():]
                else:
                    style=re.search(rf'<c\b[^>]*\br="{column}2"[^>]*\bs="(\d+)"',template)
                    if not style:raise ValueError('Source numeric/date style missing')
                    text=text.replace('</row>',f'<c r="{address}" s="{style[1]}"><v>{value}</v></c></row>')
            if old:xml=xml.replace(old.group(),text,1)
            else:new_rows.append(text)
        xml=xml.replace('</sheetData>',''.join(new_rows)+'</sheetData>',1)
        # Explicit dimensions, if present, must include appended observations.
        dimension=re.search(r'<dimension ref="([A-Z]+\d+):([A-Z]+)(\d+)"',xml)
        if dimension and max(grouped)>int(dimension[3]):
            xml=xml[:dimension.start()]+xml[dimension.start():].replace(dimension.group(),f'<dimension ref="{dimension[1]}:{dimension[2]}{max(grouped)}"',1)
        ET.fromstring(xml)
        output=BytesIO()
        with ZipFile(output,'w') as target:
            for info in z.infolist():target.writestr(info,xml.encode('utf-8') if info.filename==part else z.read(info.filename))
        result=output.getvalue()
    verify_package(source,result,part)
    return result


def verify_package(source,candidate,changed_part):
    with ZipFile(BytesIO(source)) as before,ZipFile(BytesIO(candidate)) as after:
        if before.namelist()!=after.namelist() or after.testzip():raise ValueError('Workbook package integrity changed')
        for name in before.namelist():
            if name!=changed_part and before.read(name)!=after.read(name):raise ValueError('Unrelated workbook part changed: '+name)
