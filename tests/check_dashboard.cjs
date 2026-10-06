// Offline DOM contract check; this is not a browser rendering test.
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const html=fs.readFileSync('dashboard/index.html','utf8');
class Element {
 constructor(id=''){this.id=id;this.innerHTML='';this.textContent='';this.clientWidth=700;this.children={};this.dataset={};this.value='4'}
 querySelector(s){return this.children[s]??=new Element(s)}
 querySelectorAll(){return []}
 setAttribute(k,v){this[k]=v}
 addEventListener(){}
 getBoundingClientRect(){return {left:0,width:700}}
}
const elements={};for(const m of html.matchAll(/\bid="([^"]+)"/g))elements[m[1]]=new Element(m[1]);
const tabs=['brief','regions','prices','supply','scenarios','audit'].map(t=>{const e=new Element();e.dataset.tab=t;return e});
const status=new Element(),edition=new Element();
const doc={getElementById(id){assert(elements[id],`Missing DOM id ${id}`);return elements[id]},
 querySelectorAll(s){return s==='[data-tab]'?tabs:s==='.panel'?tabs:s==='.status'?[status]:s==='.edition strong'?[edition]:[]}};
const context={document:doc,window:{addEventListener(){},scrollTo(){}},location:{hash:''},history:{replaceState(){}},console,setTimeout,clearTimeout,Blob,URL};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2],'utf8'),context);
for(const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g))if(match[1].trim())vm.runInContext(match[1],context);
for(const tab of ['brief','regions','prices','supply','scenarios','audit'])context.window.FEP_REVIEW.switchTab(tab);
for(const [id,e] of Object.entries(elements))assert(!/NaN|undefined|Infinity/.test(e.innerHTML+e.textContent),`Invalid display value in ${id}`);
assert(elements.mainKpis.innerHTML.includes('Ready-for-sale, US'));
const data=context.window.FEP_REVIEW.data, latest=data.weekly.at(-1);
assert(elements.readySnapshot.innerHTML.includes('Ready-for-sale, M bbl'));
assert(elements.supplyRead.innerHTML.includes('Regional production and import support'));
assert(status.textContent.includes(latest.date.slice(0,4)));
console.log('All six tabs execute; no invalid display values; Ready-for-Sale and regional fields present. Browser visual verification remains pending.');
