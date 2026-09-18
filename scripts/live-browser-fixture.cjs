// Browser integration tests with fictional pages in an offline Docker container.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {LiveBrowser,safeLink,safeButton,allowedRequest}=require('/runtime/src/localauthor/live_browser.cjs');
async function main(){
  const job={url:'https://qa.example.test/',hosts:['qa.example.test']},frames=[],checks=[];
  const session=new LiveBrowser(job,event=>{if(event.kind==='frame')frames.push(event.frame)});
  const check=(name,condition)=>{assert.ok(condition,name);checks.push(name)};
  check('external navigation refused',!safeLink('https://other.example/','Produtos','https://qa.example.test'));
  check('destructive links refused',!safeLink('https://qa.example.test/delete','Excluir','https://qa.example.test'));
  check('POST refused without login',!allowedRequest(new URL(job.url+'auth/login'),'POST',false,job,'https://qa.example.test',false));
  check('auth POST explicitly scoped',allowedRequest(new URL(job.url+'auth/login'),'POST',false,job,'https://qa.example.test',true));
  check('payment POST refused during login',!allowedRequest(new URL(job.url+'payment'),'POST',false,job,'https://qa.example.test',true));
  check('form buttons refused',!safeButton({name:'Produtos',inForm:true,navigationContext:true}));
  check('delete tab refused',!safeButton({name:'Excluir',role:'tab',inForm:false}));
  check('navigation button supported',safeButton({name:'Produtos',inForm:false,navigationContext:true}));
  try{
    await session.start();
    await session.context.route('https://qa.example.test/**',async route=>{
      const path=new URL(route.request().url()).pathname;
      if(path==='/auth/login') return route.fulfill({contentType:'application/json',body:'{"ok":true}'});
      const content=path==='/auth'?`<h1>Autenticação</h1><form id="login"><label>E-mail<input type="email"></label><label>Senha<input type="password"></label><button>Entrar</button></form><script>document.querySelector('form').onsubmit=async e=>{e.preventDefault();await fetch('/auth/login',{method:'POST'});location.href='/products'}</script>`:
        path==='/products'?'<h1>Produtos</h1><a href="/">Página inicial</a>':
        '<h1>Visão geral</h1><a href="/products">Produtos</a><a href="/auth">Entrar</a><a href="/delete">Excluir</a><nav><button onclick="location.href=\'/products\'">Estoque</button></nav><div style="height:2000px"></div>';
      await route.fulfill({contentType:'text/html',body:'<!doctype html><html><head><title>'+ (path==='/products'?'Produtos':path==='/auth'?'Autenticação':'Visão geral')+'</title></head><body>'+content+'</body></html>'});
    });
    await session.goto(job.url);await session.record('open');
    check('own model produced screenshot',Boolean(frames.at(-1).file)&&frames.at(-1).captureAction==='RECORD');
    const first=frames.at(-1);
    await assert.rejects(()=>session.link(first.controls[0].id,'stale'),/stale/);checks.push('stale snapshot rejected');
    await session.act({action:'link',target:first.controls[0].id,snapshot:first.snapshot});
    check('observed navigation executed',frames.at(-1).url.endsWith('/products'));
    await session.act({action:'back',snapshot:frames.at(-1).snapshot});
    check('back executed',frames.at(-1).url===job.url);
    const button=frames.at(-1).controls.find(c=>c.name==='Estoque');
    await session.act({action:'link',target:button.id,snapshot:frames.at(-1).snapshot});
    check('observed navigation button executed',frames.at(-1).url.endsWith('/products'));
    await session.act({action:'back',snapshot:frames.at(-1).snapshot});
    await session.act({action:'scroll',snapshot:frames.at(-1).snapshot});
    check('scroll observed',await session.page.evaluate(()=>scrollY)>0);
    await session.goto(job.url+'auth');await session.record('open');
    check('login form detected',frames.at(-1).loginAvailable);
    const credentials={action:'login',snapshot:frames.at(-1).snapshot,username:'fictional@example.test',password:'fixture-only-29'};
    await session.act(credentials);
    check('login executed',frames.at(-1).url.endsWith('/products'));
    check('credential object cleared',!credentials.password&&!credentials.username);
    check('credentials excluded from evidence',!JSON.stringify(frames).includes('fixture-only-29')&&!JSON.stringify(frames).includes('fictional@example.test'));
    await session.goto(job.url);await session.record('open');
    session.visited.clear();
    await session.act({action:'capture',snapshot:frames.at(-1).snapshot});
    await session.act({action:'explore',snapshot:frames.at(-1).snapshot});
    check('model navigated with a receipt',frames.some(f=>f.trigger==='model_navigation'));
    fs.writeFileSync('/output/fixture-report.json',JSON.stringify({passed:checks.length,checks,frames:frames.length,source:'fictional offline fixtures; not real-site certification'},null,2));
    console.log(JSON.stringify({passed:checks.length,frames:frames.length}));
  }finally{await session.close()}
}
main().catch(error=>{console.error(error.message);process.exitCode=1});
