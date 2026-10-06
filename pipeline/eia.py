"""Strict Table 1/9 extraction for the supplied EIA report layout."""
from datetime import datetime
import re

VERSION='eia-tables-1-9-v1'


def _numbers(line,count):
    parts=re.split(r'\.{2,}',line)
    if len(parts)<2:raise ValueError('EIA row leaders missing; layout needs review')
    tokens=parts[-1].strip().split()
    if len(tokens)!=count:raise ValueError('EIA row column count changed')
    values=[]
    for token in tokens:
        if token in ('–','—','-'):values.append(None)
        elif re.fullmatch(r'-?\d[\d,]*(?:\.\d+)?',token):values.append(float(token.replace(',','')))
        else:raise ValueError('EIA row contains an unsupported value')
    return values


def _block(pages,heading,section=None):
    candidates=[]
    for page in pages:
        if 'Table 9.' not in page or heading not in page:continue
        lines=[line.strip() for line in page.splitlines()]
        for i,line in enumerate(lines):
            if line.startswith(heading) and '..' in line:
                prefix='\n'.join(lines[:i])
                if section and section not in prefix:continue
                if section=='Imports' and 'Product Supplied' in prefix.split(section)[-1]:continue
                candidates.append(lines[i:i+(5 if section else 9)])
    return candidates


def _regions(lines,prefix):
    result={}
    for label,key in [('East Coast (PADD 1)','padd1'),('Midwest (PADD 2)','padd2'),('Gulf Coast (PADD 3)','padd3'),('PADDs 4 and 5','padd45')]:
        matches=[line for line in lines[1:] if line.startswith(label)]
        if len(matches)!=1:raise ValueError('EIA regional flow row missing or ambiguous')
        value=_numbers(matches[0],6)[0]
        if value is None:raise ValueError('EIA regional flow missing')
        result[key+'_'+prefix+'_bpd']=value*1000
    return result


def parse_pages(pages):
    if not pages:raise ValueError('No EIA pages')
    header=re.search(r'Table 1\..*?Week Ending (\d{1,2}/\d{1,2}/\d{4})',pages[0])
    if not header:raise ValueError('EIA week-ending header missing')
    day=datetime.strptime(header[1],'%m/%d/%Y').date()
    result={'date':day.isoformat()}
    products=pages[0].split('Products Supplied',1)
    if len(products)!=2:raise ValueError('EIA Products Supplied section missing')
    matches=[line for line in products[1].splitlines() if re.match(r'^\(\d+\) Propane/Propylene',line)]
    if len(matches)!=1:raise ValueError('EIA product supplied row missing or ambiguous')
    values=_numbers(matches[0],11)
    if values[0] is None or values[5] is None:raise ValueError('EIA product supplied data missing')
    result.update(product_supplied_bpd=values[0]*1000,product_supplied_4wk_bpd=values[5]*1000)
    production=_block(pages,'Propane/Propylene','Refiner and Blender Net Production')
    imports=_block(pages,'Propane/Propylene','Imports')
    for blocks,prefix in [(production,'production'),(imports,'imports')]:
        if len(blocks)!=1:raise ValueError('EIA national flow section missing or ambiguous')
        block=blocks[0];values=_numbers(block[0],6)
        if values[0] is None or values[4] is None:raise ValueError('EIA national flow missing')
        result[prefix+'_bpd']=values[0]*1000
        result[prefix+'_4wk_bpd']=values[4]*1000
        result.update(_regions(block,prefix))
        if abs(sum(result[k+'_'+prefix+'_bpd'] for k in ('padd1','padd2','padd3','padd45'))-result[prefix+'_bpd'])>4000:
            raise ValueError('EIA regional flows do not reconcile within rounding tolerance')
    ready=_block(pages,'Propane, fractionated and ready for sale')
    if len(ready)!=1:raise ValueError('EIA Ready-for-Sale section missing or ambiguous')
    # Table 9 stock rows have four observations followed by four non-applicable columns.
    national=_numbers(ready[0][0],8)[0]
    if national is None:raise ValueError('EIA ready-for-sale stocks missing')
    result['ready_bbl']=national*1e6
    for label,key in [('East Coast (PADD 1)','padd1'),('Midwest (PADD 2)','padd2'),('Gulf Coast (PADD 3)','padd3'),('Rocky Mountain (PADD 4)','padd4'),('West Coast (PADD 5)','padd5')]:
        lines=[line for line in ready[0][1:] if line.startswith(label)]
        if len(lines)!=1:raise ValueError('EIA regional ready-for-sale row missing')
        value=_numbers(lines[0],8)[0]
        if value is None:raise ValueError('EIA regional ready-for-sale value missing')
        result[key+'_ready_bbl']=value*1e6
    if abs(sum(result[f'padd{i}_ready_bbl'] for i in range(1,6))-result['ready_bbl'])>300000:
        raise ValueError('EIA regional ready-for-sale stocks do not reconcile within rounding tolerance')
    if any(v<0 for k,v in result.items() if k!='date'):raise ValueError('Negative EIA field')
    return result
