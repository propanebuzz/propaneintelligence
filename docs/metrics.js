/* Shared, dependency-free analytical rules. Missing observations never become zero. */
(function(root){
'use strict';
const finite=Number.isFinite;
const avg=xs=>xs.length&&xs.every(finite)?xs.reduce((a,b)=>a+b,0)/xs.length:null;
function rank(xs,v){xs=xs.filter(finite);return !xs.length||!finite(v)?null:100*(xs.filter(x=>x<v).length+.5*xs.filter(x=>x===v).length)/xs.length}
function previous(rows,date,days=7){const t=Date.parse(date+'T00:00:00Z')-days*86400000;return rows.find(r=>Date.parse(r.date+'T00:00:00Z')===t)||null}
function windowMean(rows,key,n,end=rows.length){const part=rows.slice(Math.max(0,end-n),end);if(part.length!==n)return null;for(let i=1;i<part.length;i++)if(Date.parse(part[i].date)-Date.parse(part[i-1].date)!==7*86400000)return null;return avg(part.map(r=>r[key]))}
function value(r,key){if(key==='spread')return finite(r.tet)&&finite(r.cwy)?(r.tet-r.cwy)*100:null;if(key==='cwyRatio')return finite(r.cwy)&&finite(r.wti)&&r.wti>0?r.cwy*4200/r.wti:null;return finite(r[key])?r[key]*100:null}
function exposure(weights,departures){if(weights.length!==departures.length||!weights.length||!weights.every(x=>finite(x)&&x>=0)||!departures.every(x=>finite(x)&&x>=-100))return null;const total=weights.reduce((a,b)=>a+b,0);return total>0?weights.reduce((s,w,i)=>s+w*departures[i],0)/total:null}
function shock(production,exports,imports,demand,weeks){return [production,exports,imports,demand,weeks].every(finite)&&weeks>0?(production-exports+imports-demand)*7*weeks/1000:null}
const api={avg,rank,previous,windowMean,value,exposure,shock};
root.FEP_METRICS=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
