"""Dashboard calculations from observed stocks, daily rates and dated prices."""
from collections import defaultdict
from datetime import date
from statistics import mean


def monthly_prices(daily):
    groups = defaultdict(list)
    for row in daily: groups[row['date'][:7]].append(row)
    result = []
    for month, rows in sorted(groups.items()):
        item = {'month': month, 'n': len(rows)}
        for key in ('cwy', 'tet', 'wti'): item[key] = mean(r[key] for r in rows)
        for key in ('cwy', 'tet'):
            ratios = [r[key] * 42 / r['wti'] * 100 for r in rows if r['wti'] > 0]
            item[key + '_ratio'] = mean(ratios) if ratios else None
        result.append(item)
    return result


def reconciliation_flags(rows):
    flags = []
    for before, after in zip(rows, rows[1:]):
        if (date.fromisoformat(after['date']) - date.fromisoformat(before['date'])).days != 7:
            continue
        if any(r.get(k) is None for r,k in ((before,'inv'),(after,'inv'),(after,'build'))): continue
        gap = after['inv'] - before['inv'] - after['build']
        if abs(gap) > .2 + 1e-9:
            flags.append({'date': after['date'], 'row': after['row'], 'prior_inv': before['inv'],
                          'inv': after['inv'], 'build': after['build'], 'gap': gap})
    return flags


def summarize(rows, daily):
    latest = rows[-1]; year, week = latest['season'], latest['week']
    years = list(range(year-5, year))
    by = {(r['season'],r['week']):r for r in rows}
    prior = by[(year-1,week)]
    current = [r for r in rows if r['season']==year]
    def block(y, lo, hi):
        result=[by[(y,w)] for w in range(lo,hi+1)]
        if any((date.fromisoformat(b['date'])-date.fromisoformat(a['date'])).days != 7 for a,b in zip(result,result[1:])):
            raise ValueError('Missing weekly observation in comparison window')
        return result
    def average(rs,key):
        values=[r[key] for r in rs]
        if any(v is None for v in values): raise ValueError('Missing flow in analytical window')
        return mean(values)
    four=block(year,week-3,week); previous=block(year,week-7,week-4)
    prior_four=block(year-1,week-3,week)
    matched=[(by[(year,w)],by[(year-1,w)]) for w in range(1,week+1)]
    prod_delta=sum((a['production']-b['production'])*7 for a,b in matched)
    export_delta=-sum((a['exports']-b['exports'])*7 for a,b in matched)
    build_delta=sum(a['build']-b['build'] for a,b in matched)
    carry=next(r for r in reversed(rows) if r['date']<f'{year}-04-01')['inv']
    prior_carry=next(r for r in reversed(rows) if r['date']<f'{year-1}-04-01')['inv']
    return {'year':year,'week':week,'price':daily[-1],'weekly':latest,'prior':prior,
            'yoy':latest['inv']-prior['inv'], 'yoy_ready':latest['ready']-prior['ready'],
            'cum':latest['cumulative'],'pace5':mean(by[(y,week)]['cumulative'] for y in years),
            'pace4':mean(by[(y,week)]['cumulative'] for y in years[-4:]),
            'inv5':mean(by[(y,week)]['inv'] for y in years),
            'ex4':average(four,'exports'),'ex_prev4':average(previous,'exports'),
            'ex8':average(block(year,week-7,week),'exports'),
            'ex12':average(block(year,week-11,week),'exports'),
            'share4':sum(r['exports'] for r in four)/sum(r['production'] for r in four)*100,
            'build4':sum(r['build'] for r in four),
            'build4ref':mean(sum(r['build'] for r in block(y,week-3,week)) for y in years),
            'carry':carry,'prior_carry':prior_carry,'carry_yoy':carry-prior_carry,
            'cur_level_change':latest['inv']-carry,'prior_level_change':prior['inv']-prior_carry,
            'prod_delta_volume':prod_delta,'export_delta_volume':export_delta,
            'build_delta':build_delta,'residual_delta':build_delta-prod_delta-export_delta,
            'draws':[{'date':r['date'],'build':r['build']} for r in current if r['build']<0],
            'season_high':max(r['inv'] for r in current),'ref_years':years,
            'ex_yoy4':average(four,'exports')/average(prior_four,'exports')-1,
            'prod_yoy4':average(four,'production')/average(prior_four,'production')-1}
