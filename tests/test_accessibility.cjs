const {JSDOM}=require('jsdom'),fs=require('fs'),assert=require('assert');
const root=require('path').resolve(__dirname,'..')+'/';
const d=new JSDOM(fs.readFileSync(root+'static/index.html','utf8'),{runScripts:'outside-only',url:'http://localhost'}),w=d.window,doc=w.document;
w.fetch=async()=>({ok:true,json:async()=>JSON.parse(fs.readFileSync(root+'research/catalog.json'))});
w.eval(fs.readFileSync(root+'static/app.js','utf8'));
assert.equal(doc.documentElement.lang,'ko');
assert(doc.querySelector('link[rel="icon"]').href.endsWith('/static/favicon.svg'));
assert(!doc.querySelector('#free-question').open);
assert(!doc.body.textContent.includes('▥'));
for(const selector of ['.brand img','.empty-icon img']){const icon=doc.querySelector(selector);assert(icon);assert.equal(icon.getAttribute('src'),'/static/favicon.svg');assert.equal(icon.getAttribute('alt'),'');assert.equal(icon.getAttribute('width'),'48');assert.equal(icon.getAttribute('height'),'48');}
assert(doc.querySelector('.brand').textContent.includes('버스여울'));

assert(doc.querySelector('#chart').compareDocumentPosition(doc.querySelector('#claim-card'))&4);
assert(!doc.querySelector('#warnings').closest('details'));
assert(!doc.querySelector('.result-caution').closest('details'));
for(const e of doc.querySelectorAll('input,select,textarea'))assert(e.id&&doc.querySelector(`label[for="${e.id}"]`),e.id);
const details=[...doc.querySelectorAll('details')];details[0].open=true;const before=details.map(e=>e.open);
w.dispatchEvent(new w.Event('beforeprint'));assert(details.every(e=>e.open));
w.dispatchEvent(new w.Event('afterprint'));assert.deepEqual(details.map(e=>e.open),before);
console.log('PASS: Korean document, icon, advanced disclosure, chart hierarchy, persistent warnings, form labels, print detail restoration');
