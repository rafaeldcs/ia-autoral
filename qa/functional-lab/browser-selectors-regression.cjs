// Independent DOM regression; inference is intentionally absent from this test.
const assert=require('node:assert/strict');
const {chromium}=require('/opt/node_modules/playwright');
const {LiveBrowser,allowedRequest}=require('/runtime/src/localauthor/live_browser.cjs');
// Policy matrix: a GET preflight never grants a later mutation.
const origin='https://example.test',job={hosts:['example.test','api.example.test'],authHosts:['api.example.test']};
const permitted=(url,method,requested='',login=false,navigation=false)=>allowedRequest(new URL(url),method,navigation,job,origin,login,requested);
for(const method of ['GET','HEAD']){
 assert.equal(permitted('https://api.example.test/catalog','OPTIONS',method),true);
 assert.equal(permitted('https://api.example.test/catalog',method),true);
 assert.equal(permitted('https://api.example.test/delete','OPTIONS',method),false);
 assert.equal(permitted('https://api.example.test/catalog','OPTIONS',method,false,true),false);
}
for(const requested of ['', 'POST','PUT','PATCH','DELETE','TRACE','get','GET, POST'])assert.equal(permitted('https://api.example.test/catalog','OPTIONS',requested),false);
for(const method of ['POST','PUT','PATCH','DELETE'])assert.equal(permitted('https://api.example.test/catalog',method),false);
for(const url of ['http://api.example.test/catalog','https://api.example.test:8443/catalog','https://unknown.test/catalog','https://user:pass@api.example.test/catalog'])assert.equal(permitted(url,'OPTIONS','GET'),false);
assert.equal(permitted('https://api.example.test/login','POST','',true),true);
assert.equal(permitted('https://api.example.test/login','POST'),false);
assert.equal(permitted('https://api.example.test/login','OPTIONS','POST',true),true);
assert.equal(permitted('https://example.test/login','POST','',true),false);
assert.equal(permitted('https://api.example.test/catalog','OPTIONS','POST',true),false);

(async()=>{
 const browser=await chromium.launch({args:['--disable-dev-shm-usage']});
 try{
  const page=await browser.newPage();
  const session=new LiveBrowser({url:'https://example.test/',hosts:['example.test']});
  session.page=page;session.origin='https://example.test';session.status=200;
  await page.route('**/*',route=>route.fulfill({contentType:'text/html; charset=utf-8',body:'<meta charset="utf-8"><h1>QA sintética</h1><nav><button id="old">Anterior</button><button id="next">Próxima</button><button>Salvar</button></nav>'}));
  await page.goto('https://example.test/');
  const first=await session.observe();session.current=first;
  assert.equal(first.controls[2].safe,false);
  await page.locator('#old').evaluate(node=>node.style.display='none');
  const second=await session.observe();session.current=second;
  assert.equal(await page.locator('[data-localauthor-control="control-0"]').count(),1);
  assert.equal(await page.locator('#old').getAttribute('data-localauthor-control'),null);
  assert.equal(second.controls[0].name,'Próxima');
  await assert.rejects(session.fresh(first.snapshot),/stale/);
  await session.fresh(second.snapshot);
  await page.locator('#old').evaluate(node=>node.style.display='');
  const third=await session.observe();session.current=third;
  assert.equal(third.controls[0].name,'Anterior');
  assert.equal(await page.locator('[data-localauthor-control="control-0"]').count(),1);
  assert.equal(third.controls.find(c=>c.name==='Salvar').safe,false);
  await assert.rejects(session.fresh(second.snapshot),/stale/);
  await page.evaluate(()=>{
   const nav=document.querySelector('nav');
   const group=document.createElement('div');group.id='collapsed';group.style.cssText='max-height:0;opacity:0;overflow:hidden';
   const button=document.createElement('button');button.textContent='Central de Marketing';group.append(button);nav.append(group);
  });
  const closed=await session.observe();session.current=closed;
  assert.ok(!closed.controls.some(c=>c.name==='Central de Marketing'));
  await page.locator('#collapsed').evaluate(n=>n.style.cssText='max-height:1200px;opacity:1;overflow:hidden');
  const opened=await session.observe();session.current=opened;
  assert.ok(opened.controls.some(c=>c.name==='Central de Marketing'));
  await assert.rejects(session.fresh(closed.snapshot),/stale/);
  await page.evaluate(()=>{
   const clip=document.createElement('div');clip.id='clip';clip.style.cssText='position:absolute;left:10px;top:10px;width:100px;height:20px;overflow:hidden';
   const b=document.createElement('button');b.textContent='Parcial';b.style.cssText='position:absolute;top:10px;height:30px';clip.append(b);document.querySelector('nav').append(clip);
  });
  const partial=await session.observe();session.current=partial;
  assert.ok(partial.controls.some(c=>c.name==='Parcial'));
  await page.locator('#clip button').evaluate(n=>n.style.top='50px');
  const outside=await session.observe();session.current=outside;
  assert.ok(!outside.controls.some(c=>c.name==='Parcial'));
  assert.equal(outside.controls.find(c=>c.name==='Salvar').safe,false);
  console.log(JSON.stringify({passed:true,selector_uniqueness:true,hidden_marker_removed:true,stale_rejected:true,mutation_blocked:true,readonly_preflight:true,model_qualification:false}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
