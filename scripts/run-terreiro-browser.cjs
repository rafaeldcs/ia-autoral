/* Reviewed LocalAuthor QA executor. Run only inside the disposable Docker lab.
 * Neural policy proposes this stage; this authored worker performs the checks.
 * No external navigation, HAR, trace, login screenshot, or credential logging.
 */
const {chromium}=require('/opt/node_modules/playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const origin='http://localhost:3180';
const users=JSON.parse(fs.readFileSync('/input/access.json','utf8'));
const plan=JSON.parse(fs.readFileSync('/input/plan.json','utf8'));
assert(plan.actions.includes('CHECK_BROWSER'));
const out='/output';fs.mkdirSync(out+'/screenshots',{recursive:true});
const report={executor:'LocalAuthor Docker browser worker',author:'Codex',modelRole:'Select QA stage, not write tests or interpret pixels',origin,startedAt:new Date().toISOString(),checks:[],screens:[],errors:[]};
function save(){fs.writeFileSync(out+'/browser-report.json',JSON.stringify(report,null,2));}
function check(name,ok,details={}){report.checks.push({name,passed:!!ok,...details});save();assert(ok,name);}
async function shot(page,role,path,viewport){
 const file=`${role}-${viewport}-${path==='/'?'inicio':path.replace(/\W+/g,'-')}.png`;
 await page.screenshot({path:out+'/screenshots/'+file,fullPage:true,animations:'disabled'});
 report.screens.push({role,path,viewport,file});save();
}
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  for(const role of ['Member','Coordinator','Secretary','Stock','Treasury','Reviewer','Admin']){
   const context=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block'});
   await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
   const page=await context.newPage();page.setDefaultTimeout(15000);
   page.on('pageerror',err=>{report.errors.push({role,kind:'javascript',message:err.message});save();});
   await page.goto(origin+'/entrar');await page.locator('[name=login]').fill(users[role].login);await page.locator('[name=password]').fill(users[role].password);
   await page.getByRole('button',{name:'Entrar no aplicativo',exact:true}).click();
   await page.locator('#main-content').waitFor();check(role+' authenticates through the real form',!page.url().includes('/entrar'));
   const links=[...new Set(await page.locator('nav[aria-label="Menu principal"] a').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href'))))];
   check(role+' has usable navigation',links.length>=10);
   const failures=[];const collect=res=>{if(res.url().includes('/api/')&&res.status()>=400)failures.push({path:new URL(res.url()).pathname,status:res.status()});};page.on('response',collect);
   for(const path of links){
    const started=Date.now();await page.goto(origin+path);await page.locator('#main-content').waitFor();await page.waitForLoadState('networkidle');
    const main=page.locator('#main-content');
    check(role+' renders '+path,(await main.innerText()).trim().length>10,{milliseconds:Date.now()-started});
    check(role+' no error notice '+path,await main.locator('[role=alert]').count()===0);
    await shot(page,role,path,'desktop');
    await page.setViewportSize({width:390,height:844});
    check(role+' mobile width '+path,await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1));
    await shot(page,role,path,'mobile');await page.setViewportSize({width:1440,height:1000});
   }
   check(role+' allowed pages have no HTTP errors',failures.length===0,{failures});page.off('response',collect);
   await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Mais',exact:true}).click();
   await page.getByRole('dialog',{name:'Todas as áreas'}).waitFor();check(role+' mobile drawer opens',true);
   await page.keyboard.press('Escape');check(role+' mobile drawer closes with Escape',await page.getByRole('dialog',{name:'Todas as áreas'}).count()===0);
   await page.getByRole('button',{name:'Sair da conta',exact:true}).last().click();
   await page.locator('[name=login]').waitFor();check(role+' logout returns to login',true);
   await context.close();
  }
  check('No unhandled browser exceptions',report.errors.length===0);
  report.success=true;
 }catch(error){report.success=false;report.failure=error.message;process.exitCode=1;}
 finally{await browser.close();save();console.log(JSON.stringify({success:report.success,checks:report.checks.length,screenshots:report.screens.length,failure:report.failure}));}
})();
