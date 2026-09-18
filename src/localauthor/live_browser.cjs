// LocalAuthor's reviewed browser adapter. Site text never becomes executable code.
const fs = require('node:fs');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const readline = require('node:readline');
const { chromium } = require('/opt/node_modules/playwright');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const plain = value => value.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase();
const risky = /(?:excluir|apagar|deletar|salvar|publicar|enviar|pagar|cobrar|reembolsar|comprar|contratar|ativar|desativar|delete|remove|save|submit|send|pay|purchase|checkout|logout|signout|sair|unsubscribe|cancelar|cancel)/i;

function safeLink(href, name, origin) {
  try {
    const url = new URL(href);
    return url.origin === origin && url.protocol === 'https:' && !url.username && !url.password &&
      !risky.test(plain(name+' '+url.pathname)) && ![...url.searchParams.keys()].some(k=>/token|password|secret|code|key/i.test(k));
  } catch { return false; }
}

function allowedRequest(url, method, navigation, job, origin, loginWindow) {
  const allowed = url.protocol==='https:' && (!url.port || url.port==='443') && !url.username && !url.password && job.hosts.includes(url.hostname);
  const read = ['GET','HEAD'].includes(method) && !risky.test(plain(url.pathname));
  const login = loginWindow && ['POST','OPTIONS'].includes(method) &&
    (job.authHosts || [new URL(origin).hostname]).includes(url.hostname) && /\/(login|signin|sign-in|session|token)\/?$/i.test(url.pathname);
  return allowed && (read || login) && (!navigation || url.origin===origin);
}

function safeButton(control) {
  return !control.inForm && !risky.test(plain(control.name)) &&
    (control.navigationContext || control.role==='tab' || /^(painel|dashboard)(\s|$)/i.test(control.name));
}

class LiveBrowser {
  constructor(job, emit = data => console.log(JSON.stringify(data))) {
    this.job = job; this.origin = new URL(job.url).origin; this.emit = emit;
    this.visited = new Set(); this.count = 0; this.history = []; this.loginWindow = false;
    this.blocked = new Set();
  }
  async start() {
    this.browser = await chromium.launch({headless:true, args:['--no-sandbox','--disable-dev-shm-usage']});
    this.context = await this.browser.newContext({viewport:{width:1360,height:900},locale:'pt-BR',
      acceptDownloads:false,serviceWorkers:'block'});
    // WebSockets are not part of this read-only investigation channel.
    await this.context.routeWebSocket('**/*', socket=>socket.close());
    await this.context.route('**/*', route=>{
      const request = route.request();
      let url;
      try { url = new URL(request.url()); } catch { return route.abort(); }
      // Authentication is a separate, explicit operation; its POST window closes
      // before screenshots/exploration. Only the current site's origin may POST.
      if (!allowedRequest(url,request.method(),request.isNavigationRequest(),this.job,this.origin,this.loginWindow)) {
        this.blocked.add(url.hostname+' ('+request.method()+')'); return route.abort();
      }
      return route.continue();
    });
    this.context.on('page', page=>{ if (this.page && page!==this.page) page.close().catch(()=>{}); });
    this.page = await this.context.newPage();
    this.page.setDefaultTimeout(8000);
    this.page.on('dialog', dialog=>dialog.dismiss().catch(()=>{}));
    this.status = 0;
    this.page.on('response', response=>{ if (response.request().isNavigationRequest() && response.frame()===this.page.mainFrame()) this.status=response.status(); });
  }
  async goto(url) {
    if (!safeLink(url,'',this.origin)) throw Error('blocked_navigation');
    await this.page.goto(url,{waitUntil:'domcontentloaded',timeout:30000});
    await this.page.waitForTimeout(700);
  }
  async observe() {
    const location = new URL(this.page.url());
    if (/(token|password|secret|code|key)=/i.test(location.search+' '+location.hash)) throw Error('sensitive_url');
    const raw = await this.page.evaluate(()=>{
      const visible = node => node.getClientRects().length>0 && getComputedStyle(node).visibility!=='hidden';
      const headings = [...document.querySelectorAll('h1,h2,h3,[role="heading"]')].filter(visible).map(n=>n.textContent.trim()).filter(Boolean);
      const links = [...document.querySelectorAll('a[href],button,[role="tab"]')].filter(visible);
      const controls = links.slice(0,80).map((node,index)=>{
        const id='control-'+index; node.setAttribute('data-localauthor-control',id);
        return {id,name:(node.getAttribute('aria-label') || node.textContent || node.title || node.href || '').trim().slice(0,240),
          href:node.tagName==='A'?node.href:null,role:node.getAttribute('role') || (node.tagName==='A'?'link':'button'),
          navigationContext:!!node.closest('nav,aside,[role="navigation"]'),inForm:!!node.closest('form')};
      });
      const passwords = [...document.querySelectorAll('input[type="password"]')].filter(visible);
      const users = [...document.querySelectorAll('input[type="email"],input[autocomplete="username"],input[name="username"],input[name="email"]')].filter(visible);
      const scope = passwords.length===1 ? (passwords[0].form || document) : document;
      const submits = [...scope.querySelectorAll('button:not([type="button"]):not([type="reset"]),input[type="submit"]')].filter(visible).filter(n=>/^(entrar(?: na (?:minha|sua) conta)?|acessar(?: minha conta)?|iniciar sess[aã]o|sign in|log in|login)$/i.test((n.textContent || n.value || '').trim()));
      const loginAvailable = passwords.length===1 && users.length===1 && submits.length===1;
      return {url:location.href,title:(document.title || headings[0] || 'Página sem título').slice(0,600),
        headings:headings.slice(0,60).map(s=>s.slice(0,600)),controls,loginAvailable,
        loading:[...document.querySelectorAll('[aria-busy="true"]')].some(visible) || [...document.querySelectorAll('button:disabled')].some(n=>visible(n)&&/entrando|signing in|carregando|aguarde/i.test(n.textContent)),scrollY:Math.round(scrollY),
        truncated:links.length>80 || headings.length>60};
    });
    if (new URL(raw.url).origin!==this.origin) throw Error('scope_changed');
    raw.controls = raw.controls.filter(c=>c.name).map(c=>{
      const key=c.href || 'button:'+raw.url+':'+c.name+':'+c.id;
      return {...c,key,safe:c.href?safeLink(c.href,c.name,this.origin):safeButton(c),visited:this.visited.has(key)||key===raw.url};
    });
    raw.accessible = this.status>=200 && this.status<400;
    // State-independent hash: visits change as evidence is saved, DOM identity does not.
    const fingerprint = {...raw,controls:raw.controls.map(({visited,...c})=>c)};
    raw.snapshot = hash(JSON.stringify(fingerprint));
    return raw;
  }
  infer(observation) {
    const run = cp.spawnSync('python3',['-m','localauthor.browser_reasoner'], {
      input:JSON.stringify(observation),encoding:'utf8',timeout:20000,
      env:{...process.env,PYTHONPATH:'/runtime/src',OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1'}});
    if (run.status!==0) throw Error('model_unavailable');
    return JSON.parse(run.stdout);
  }
  async record(action) {
    if (this.count>=60) throw Error('budget');
    const observation = await this.observe();
    const model = this.infer(observation);
    const frame = {number:++this.count,at:new Date().toISOString(),url:observation.url,title:observation.title,
      snapshot:observation.snapshot,controls:model.controls,loginAvailable:observation.loginAvailable,
      interpretation:model.interpretation,proposal:{action:model.action,target:model.target},
      captureAction:model.captureAction,capturedBy:'LocalAuthor own browser',trigger:action,
      blockedRequests:[...this.blocked].slice(0,20),
      truncated:observation.truncated,pending:model.controls.filter(c=>c.safe&&!c.visited).length,
      allSitesQualified:false};
    if (model.captureAllowed) {
      const fresh = await this.observe();
      if (fresh.snapshot!==observation.snapshot) throw Error('stale');
      frame.file=String(frame.number).padStart(3,'0')+'.png';
      const png = await this.page.screenshot({path:'/output/'+frame.file,
        mask:[this.page.locator('input,textarea,[contenteditable="true"]')],maskColor:'#e2e5ed',timeout:12000});
      frame.sha256=hash(png);
      this.visited.add(observation.url);
    } else frame.reason='Modelo ou estado da página não autorizou captura. Tente atualizar após o carregamento.';
    this.current = frame;
    this.emit({kind:'frame',frame,action});
    return frame;
  }
  async fresh(expected) {
    const observation = await this.observe();
    if (observation.snapshot!==expected || this.current?.snapshot!==expected) throw Error('stale');
    return observation;
  }
  async link(target, expected) {
    const observation = await this.fresh(expected);
    const control = observation.controls.find(c=>c.id===target && c.safe);
    if (!control) throw Error('blocked_navigation');
    this.history.push(observation.url);
    // Navigate to the exact observed href; no untrusted onclick handler.
    this.visited.add(control.key);
    if(control.href) await this.goto(control.href);
    else {
      await this.page.locator('[data-localauthor-control="'+control.id+'"]').click();
      await this.page.waitForTimeout(700);
    }
  }
  async login(data) {
    const observation = await this.fresh(data.snapshot);
    if (!observation.loginAvailable) throw Error('login_unavailable');
    const password = this.page.locator('input[type="password"]:visible');
    const user = this.page.locator('input[type="email"]:visible,input[autocomplete="username"]:visible,input[name="username"]:visible,input[name="email"]:visible');
    const forms = this.page.locator('form').filter({has:password});
    const scope = await forms.count()===1 ? forms : this.page;
    const submit = scope.getByRole('button',{name:/^(entrar(?: na (?:minha|sua) conta)?|acessar(?: minha conta)?|iniciar sess[aã]o|sign in|log in|login)$/i});
    if (await password.count()!==1 || await user.count()!==1 || await submit.count()!==1) throw Error('login_unavailable');
    this.loginWindow=true;
    try {
      await user.fill(data.username); await password.fill(data.password);
      await submit.click();
      await this.page.waitForLoadState('networkidle',{timeout:20000}).catch(()=>{});
      await this.page.waitForTimeout(500);
      await this.page.waitForFunction(()=>![...document.querySelectorAll('button:disabled')].some(n=>n.getClientRects().length && /entrando|signing in|carregando|aguarde/i.test(n.textContent)),null,{timeout:20000}).catch(()=>{});
      await this.page.waitForTimeout(300);
    } finally {
      this.loginWindow=false;
      data.username=''; data.password='';
      await this.page.locator('input[type="password"]').fill('').catch(()=>{});
    }
  }
  async act(data) {
    if (data.action==='link') await this.link(data.target,data.snapshot);
    else if (data.action==='login') await this.login(data);
    else if (data.action==='back') {
      await this.fresh(data.snapshot);
      if (!this.history.length) throw Error('empty_history');
      await this.goto(this.history.pop());
    } else if (data.action==='scroll') {
      await this.fresh(data.snapshot);
      await this.page.evaluate(()=>scrollBy(0,Math.round(innerHeight*.75)));
    } else if (data.action==='explore') {
      await this.fresh(data.snapshot);
      for (let step=0;step<5;step++) {
        const next = this.current.proposal;
        if (!['OPEN_1','OPEN_2'].includes(next.action) || !next.target) break;
        const control = this.current.controls.find(c=>c.id===next.target && c.safe);
        if (!control || this.visited.has(control.key)) break;
        await this.link(next.target,this.current.snapshot);
        await this.record('model_navigation');
      }
      return;
    } else if (data.action!=='capture') throw Error('unsupported_action');
    await this.record(data.action);
  }
  async close() { if (this.browser) await this.browser.close(); }
}

async function main() {
  const session = new LiveBrowser(JSON.parse(fs.readFileSync('/input/job.json','utf8')));
    const errors = {stale:'A página mudou. Atualize a captura e escolha novamente.',
    blocked_navigation:'Destino fora do escopo de leitura.',login_unavailable:'Formulário de login não compatível. Esta sessão não pode autenticar automaticamente.',
    model_unavailable:'Modelo local indisponível; nenhuma ação automática foi executada.',
    empty_history:'Ainda não existe página anterior.',budget:'Limite de observações atingido. Abra uma nova sessão.'};
  try {
    await session.start(); await session.goto(session.job.url); await session.record('open');
    console.log(JSON.stringify({kind:'ready'}));
    const lines = readline.createInterface({input:process.stdin,crlfDelay:Infinity});
    for await (const line of lines) {
      let data;
      try {
        if (line.length>4000) throw Error('oversized');
        data=JSON.parse(line); await session.act(data);
      } catch(error) {
        console.log(JSON.stringify({kind:'error',message:errors[error.message] || 'A ação não terminou. O site pode exigir outra autenticação, conexão ou tipo de controle. Atualize a captura.'}));
      } finally { if(data) {data.username='';data.password='';} }
      console.log(JSON.stringify({kind:'ready'}));
    }
  } finally { await session.close(); }
}
module.exports={LiveBrowser,safeLink,safeButton,allowedRequest};
if(require.main===module) main().catch(()=>{console.log(JSON.stringify({kind:'error',message:'Não foi possível abrir este site. Confira o endereço, a conexão e os modelos locais.'}));process.exitCode=1;});
