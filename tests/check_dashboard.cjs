// Offline DOM contract check; this is not a browser rendering test.
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const html=fs.readFileSync('dashboard/index.html','utf8');
class Element {
 constructor(id=''){this.id=id;this._html='';this.textContent='';this.clientWidth=700;this.children={};this.dataset={};this.value='4';this.parentElement=this}
 set value(v){this._value=String(v)}
 get value(){return this._value}
 set innerHTML(v){this._html=v;for(const m of v.matchAll(/\bid="([^"]+)"/g))elements[m[1]]??=new Element(m[1])}
 get innerHTML(){return this._html||''}
 appendChild(){}
 insertBefore(){}
 checkValidity(){return true}
 querySelector(s){return this.children[s]??=new Element(s)}
 querySelectorAll(){return []}
 setAttribute(k,v){this[k]=v}
 addEventListener(){}
 getBoundingClientRect(){return {left:0,width:700}}
}
const elements={};for(const m of html.matchAll(/\bid="([^"]+)"/g))elements[m[1]]=new Element(m[1]);
const tabNames=[...html.matchAll(/data-tab="([^"]+)"/g)].map(m=>m[1]);
const tabs=tabNames.map(t=>{const e=new Element();e.dataset.tab=t;return e});
const status=new Element(),edition=new Element();
const doc={createElement:()=>new Element(),getElementById(id){assert(elements[id],`Missing DOM id ${id}`);return elements[id]},
 querySelectorAll(s){return s==='[data-tab]'?tabs:s==='.panel'?tabs:s==='.status'?[status]:s==='.edition strong'?[edition]:[]}};
const context={document:doc,window:{addEventListener(){},scrollTo(){}},location:{hash:''},history:{replaceState(){}},console,localStorage:{getItem(){return null},setItem(){}},setTimeout,clearTimeout,Blob,URL};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))if(match[1].trim())vm.runInContext(match[1],context);
for(const name of ['metrics.js','enhancements.js'])vm.runInContext(fs.readFileSync('dashboard/'+name,'utf8'),context);
for(const tab of tabNames)context.window.FEP_REVIEW.switchTab(tab);
for(const [id,e] of Object.entries(elements))assert(!/NaN|undefined|Infinity/.test(e.innerHTML+e.textContent),`Invalid display value in ${id}`);
assert(elements.mainKpis.innerHTML.includes('Ready-for-sale, US'));
const data=context.window.FEP_REVIEW.data, latest=data.weekly.at(-1);
assert(elements.readySnapshot.innerHTML.includes('Ready-for-sale, M bbl'));
assert(elements.supplyRead.innerHTML.includes('Regional production and import support'));
assert(status.textContent.includes(latest.date.slice(0,4)));
console.log('All ten tabs execute; no invalid display values; Ready-for-Sale and regional fields present. Browser visual verification remains pending.');
// Exercise selectable metrics, source gaps, all archive seasons and assumption errors.
for(const k of ['inv','midwest','gulf','ready']){elements.seasonMetric.value=k;elements.seasonMetric.onchange()}
for(const k of ['cwy','tet','spread','cwyRatio']){elements.overlayMetric.value=k;elements.overlayMetric.onchange()}
for(const k of ['all','20','60','120']){elements.priceWindow.value=k;elements.priceWindow.onchange()}
elements.heatSeasons.value='all';elements.heatSeasons.onchange();assert(elements.heatReading.textContent.includes('seasons'));
for(let i=0;i<4;i++){elements['weight'+i].value='25';elements['hdd'+i].value='10'}
elements.hdd0.oninput();assert(elements.weatherResult.textContent.includes('+10.0%'));
for(let i=0;i<4;i++)elements['weight'+i].value='0';elements.hdd0.oninput();assert(elements.weatherResult.textContent.includes('valid assumptions'));
elements.weatherReset.onclick();
for(const [id,v] of Object.entries({balanceProd:'100',balanceExport:'50',balanceImport:'20',balanceDemand:'30',balanceWeeks:'4'}))elements[id].value=v;
elements.balanceProd.oninput();assert(elements.balanceResult.textContent==='+1.12M bbl');
elements.eventDate.value='2026-11-19';elements.eventText.value='<img src=x onerror=alert(1)>';elements.eventCategory.value='Infrastructure';elements.eventUrl.value='javascript:alert(1)';
elements.eventForm.onsubmit({preventDefault(){}});assert(elements.eventLog.innerHTML.includes('&lt;img'));assert(!elements.eventLog.innerHTML.includes('href="javascript:'));
assert(elements.freshnessTable.innerHTML.includes('2026-10-02'));
assert(elements.correctionHistory.innerHTML.includes('24.6M'));
console.log('Enhanced controls, null coverage, local note escaping and scenario outputs pass.');

for(const weight of ['1','2']){elements.analogWeight.value=weight;elements.analogWeight.onchange();assert(elements.projectionMethod.innerHTML.includes(weight+'× weight'))}
