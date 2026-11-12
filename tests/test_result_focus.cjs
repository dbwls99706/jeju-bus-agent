const {JSDOM}=require('jsdom'),fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..'),read=n=>JSON.parse(fs.readFileSync(path.join(root,'research',n+'.json')));
const dom=new JSDOM(fs.readFileSync(path.join(root,'static/index.html'),'utf8'),{runScripts:'outside-only',url:'http://localhost'}),w=dom.window,$=id=>w.document.getElementById(id),result=read('repair-example');
let scroll=null;w.HTMLElement.prototype.scrollIntoView=function(o){scroll={id:this.id,...o};};w.matchMedia=()=>({matches:true});
w.fetch=async(url)=>({ok:true,json:async()=>url.includes('catalog')?read('catalog'):url.includes('/plan')?result.plan:result});
w.eval(fs.readFileSync(path.join(root,'static/app.js'),'utf8'));
const tick=()=>new Promise(r=>setTimeout(r,20));
(async()=>{await tick();$('guided-plan').click();await tick();assert.equal(w.document.activeElement.id,'plan-card');$('confirm-plan').click();await tick();assert($('plan-card').hidden);assert(!$('results').hidden);assert.equal(w.document.activeElement.id,'result-title');assert.equal($('result-title').getAttribute('tabindex'),'-1');assert.equal(scroll.id,'result-title');assert.equal(scroll.behavior,'auto');console.log('PASS result focus after confirmed calculation, hidden plan not focused, reduced-motion scroll');})().catch(e=>{console.error(e);process.exitCode=1;});
