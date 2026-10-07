// Independent functional QA of the reviewed local-model marketing artifacts.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const assert=require('node:assert/strict');
const {chromium}=require('/opt/node_modules/playwright');
const root='/tmp/marketing',out='/tmp/evidence';fs.mkdirSync(out,{recursive:true});
const posts=JSON.parse(fs.readFileSync(root+'/shopair-orbit/posts.json','utf8')).posts;
const server=http.createServer((req,res)=>{
 const file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
 if(!file.startsWith(root+'/')){res.writeHead(403).end();return;}
 try{const raw=fs.readFileSync(file);res.setHeader('Content-Type',file.endsWith('.html')?'text/html; charset=utf-8':file.endsWith('.json')?'application/json':file.endsWith('.svg')?'image/svg+xml':file.endsWith('.png')?'image/png':'text/plain');res.end(raw);}catch{res.writeHead(404).end();}
});
(async()=>{
 await new Promise(resolve=>server.listen(3177,'127.0.0.1',resolve));
 const base='http://127.0.0.1:3177',browser=await chromium.launch({args:['--disable-dev-shm-usage']});
 const cases=[];
 try{
  assert.equal(posts.length,4);
  for(const post of posts){
   assert.ok(post.caption.includes(post.brand));assert.ok(post.caption.length<=280);
   assert.ok(post.headline.length<=65 && post.subheadline.length<=120 && post.cta.length<=40 && post.alt_text.length<=160);
   assert.ok(!/efici|tempo real|\bideal\b|complet|\bgrátis\b|garant|\d+%/i.test(JSON.stringify(post)));
   assert.ok(post.alt_text.startsWith('Proposta:'));
   for(const format of ['feed','story']){
    const page=await browser.newPage({viewport:{width:1080,height:format==='story'?1920:1350}});
    await page.route('**/*',r=>r.request().url().startsWith(base+'/')?r.continue():r.abort());
    await page.goto(base+'/shopair-orbit/'+(post.brand==='Orbit'?'orbit-art.html':'shopair-art.html'));
    await page.evaluate(({post,format})=>{
     const art=document.querySelector('#art');art.style.height=format==='story'?'1920px':'1350px';
     if(post.brand==='Orbit'){
      document.querySelector('#headline').textContent=post.headline;
      document.querySelector('#supporting').textContent=post.subheadline;
      document.querySelector('#cta').textContent=post.cta;
     }else{
      art.querySelectorAll('h1')[1].textContent=post.headline;
      art.querySelector('p').textContent=post.subheadline;
      document.querySelector('#cta').textContent=post.cta;
     }
    },{post,format});
    await page.waitForFunction(()=>[...document.images].every(i=>i.complete&&i.naturalWidth>0));
    const bounds=await page.locator('#art').evaluate(art=>{
     const b=art.getBoundingClientRect();return {width:b.width,height:b.height,overflow:[...art.querySelectorAll('h1,p,#headline,#supporting,#cta,#notice,#origin,#tiles span')].filter(n=>{const r=n.getBoundingClientRect();return r.bottom>b.bottom||r.right>b.right||r.left<b.left||n.scrollHeight>n.clientHeight+1;}).map(n=>n.id||n.tagName)};
    });
    assert.equal(bounds.width,1080);assert.equal(bounds.height,format==='story'?1920:1350);assert.deepEqual(bounds.overflow,[]);
    const file=post.id+(format==='story'?'-story':'')+'.png';
    await page.locator('#art').screenshot({path:out+'/'+file});cases.push({post:post.id,format,...bounds});await page.close();
   }
  }
  // The gallery links use the generated images, not placeholder files.
  fs.mkdirSync(root+'/shopair-orbit/assets',{recursive:true});
  for(const file of fs.readdirSync(out).filter(x=>x.endsWith('.png')))fs.copyFileSync(out+'/'+file,root+'/shopair-orbit/assets/'+file);
  const page=await browser.newPage({viewport:{width:1280,height:950}});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(base+'/shopair-orbit/gestao.html');await page.waitForFunction(()=>document.querySelectorAll('.card').length===4);
  await page.selectOption('#brand','ShopAir');assert.equal(await page.locator('.card').count(),2);
  await page.selectOption('#brand','Orbit');assert.equal(await page.locator('.card').count(),2);
  await page.selectOption('#brand','Todas');
  await page.locator('#date-shopair-01').fill('2026-10-20');await page.locator('#note-shopair-01').fill('Revisão QA sintética; não publicar.');
  await page.locator('.card').first().getByRole('button',{name:'Salvar',exact:true}).click();
  assert.match(await page.locator('#feedback').textContent(),/Salvo/);
  await page.reload();await page.waitForFunction(()=>document.querySelectorAll('.card').length===4);
  assert.equal(await page.locator('#date-shopair-01').inputValue(),'2026-10-20');
  assert.equal(await page.locator('#note-shopair-01').inputValue(),'Revisão QA sintética; não publicar.');
  assert.ok((await page.locator('.status').allTextContents()).every(x=>x==='Rascunho'));
  await page.screenshot({path:out+'/management-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:out+'/management-mobile.png',fullPage:true});
  await page.evaluate(()=>localStorage.setItem('shopair-01','{'));
  await page.reload();await page.waitForFunction(()=>document.querySelectorAll('.card').length===4);
  assert.match(await page.locator('#feedback').textContent(),/Erro ao carregar dados/);
  assert.deepEqual(errors,[]);await page.close();
  const blocked=await browser.newPage();
  await blocked.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new DOMException('QA storage blocked','SecurityError');}}));
  await blocked.goto(base+'/shopair-orbit/gestao.html');await blocked.waitForFunction(()=>document.querySelectorAll('.card').length===4);
  await blocked.locator('.card').first().getByRole('button',{name:'Salvar',exact:true}).click();assert.match(await blocked.locator('#feedback').textContent(),/Erro no armazenamento/);await blocked.close();
  const hostile=await browser.newPage();
  await hostile.route('**/posts.json',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({posts:posts.map(p=>({...p,headline:'<img src=x onerror="window.qaXss=1">',caption:'<script>window.qaXss=2</script>'}))})}));
  await hostile.goto(base+'/shopair-orbit/gestao.html');await hostile.waitForFunction(()=>document.querySelectorAll('.card').length===4);
  assert.equal(await hostile.locator('.card img,.card script').count(),0);assert.equal(await hostile.evaluate(()=>window.qaXss),undefined);await hostile.close();
  const missing=await browser.newPage();await missing.route('**/posts.json',r=>r.fulfill({status:404,body:'Missing'}));
  await missing.goto(base+'/shopair-orbit/gestao.html');await missing.waitForFunction(()=>document.querySelector('#feedback').textContent.includes('Erro ao carregar posts.json'));await missing.close();
  cases.push({management:true,filter:true,persistence:true,mobile:true,malformed_storage:true,blocked_storage:true,missing_source:true,xss_literal:true,publication_simulated:false});
  fs.writeFileSync(out+'/marketing-functional.json',JSON.stringify({passed:true,cases},null,2));console.log('Marketing: 8 real ad exports and management functional checks passed.');
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
