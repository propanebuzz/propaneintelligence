const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const api=require('../dashboard/stories.js'),ctx={window:{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync('docs/snapshot.js','utf8'),ctx);
const data=ctx.window.PROPANE_SNAPSHOT,stories=api.create(data);
assert.equal(stories.length,6);
const regional=stories.find(s=>s.id==='regional-divide');
assert(Math.abs(regional.values.reduce((a,b)=>a+b,0)-2*data.summary.yoy)<1e-9);
const price=stories.find(s=>s.id==='price-momentum');
assert(price.series.every(s=>s.values[0]===100));
assert.equal(price.labels.length,61);
for(const story of stories){const svg=api.render(story);assert(svg.includes('width="1600" height="1000"'));assert(svg.includes('<title'));assert(svg.includes(story.source.replaceAll('&','&amp;')));assert(!/NaN|Infinity|undefined|<script|href=/.test(svg));assert(!svg.includes('/Users/'));
 if(process.argv[2]){fs.mkdirSync(process.argv[2],{recursive:true});fs.writeFileSync(process.argv[2]+'/'+story.id+'.svg',svg)}
}
// Missing values must interrupt lines rather than be plotted as zero; markup must be escaped.
const missing=api.render({title:'<unsafe>',takeaway:'A & B',source:'Source',note:'Note',kind:'line',labels:['a','b','c'],series:[{name:'Series',values:[1,null,3],color:'#087f82'}],unit:'Units'});
assert(missing.includes('&lt;unsafe&gt;'));assert(!missing.includes('NaN'));assert(missing.includes(' M'));
console.log('Six shareable graphics pass source/date, dimensions, arithmetic, missing-value and SVG safety checks.');
