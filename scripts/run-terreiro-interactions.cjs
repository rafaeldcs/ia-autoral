/* Real UI operations in the isolated five-member laboratory. */
const {chromium}=require('/opt/node_modules/playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const users=JSON.parse(fs.readFileSync('/input/access.json','utf8')),origin='http://localhost:3180';
const report={checks:[],screenshots:[],author:'Codex',executor:'LocalAuthor Docker worker'};
function check(name,ok){report.checks.push({name,passed:!!ok});assert(ok,name);}
(async()=>{
 const browser=await chromium.launch({args:['--no-sandbox','--disable-dev-shm-usage']});
 async function session(role){const context=await browser.newContext({viewport:{width:390,height:844},serviceWorkers:'block'});await context.route('**/*',r=>new URL(r.request().url()).origin===origin?r.continue():r.abort());const p=await context.newPage();p.setDefaultTimeout(15000);await p.goto(origin+'/entrar');await p.locator('[name=login]').fill(users[role].login);await p.locator('[name=password]').fill(users[role].password);await p.getByRole('button',{name:'Entrar no aplicativo'}).click();await p.locator('#main-content').waitFor();return{context,p};}
 async function shot(p,name){await p.screenshot({path:'/output/screenshots/'+name+'.png',fullPage:true});report.screenshots.push(name+'.png');}
 try{
  const title='Tarefa UI sintética '+Date.now(),day=new Date().toISOString().slice(0,10);
  let {context,p}=await session('Secretary');await p.goto(origin+'/tarefas');await p.getByRole('button',{name:'Criar tarefa',exact:true}).click();
  let dialog=p.getByRole('dialog');await dialog.getByLabel('Tarefa *',{exact:true}).fill(title);await dialog.getByLabel('Orientações').fill('Registrar conclusão pelo próprio médium no teste funcional.');await dialog.getByLabel('Prazo').fill(day);await dialog.getByLabel('Responsável').selectOption(users.Member.id);
  await dialog.getByRole('button',{name:'Confirmar operação',exact:true}).click();await dialog.waitFor({state:'hidden'});
  await p.getByText(title,{exact:true}).waitFor();check('Secretary creates an assigned task through the mobile form',true);await shot(p,'interaction-secretary-created-task');await context.close();
  ({context,p}=await session('Member'));await p.goto(origin+'/tarefas');const row=p.getByRole('row').filter({hasText:title});await row.getByRole('button',{name:'Marcar como concluída'}).click();dialog=p.getByRole('dialog');await dialog.getByRole('button',{name:'Confirmar operação'}).click();await dialog.waitFor({state:'hidden'});await p.waitForLoadState('networkidle');
  check('Assigned member completes the task and action disappears',await row.getByRole('button',{name:'Marcar como concluída'}).count()===0);await shot(p,'interaction-member-completed-task');
  await p.goto(origin+'/mensalidades');await p.getByRole('button',{name:'Ver detalhes',exact:true}).first().click();dialog=p.getByRole('dialog',{name:'Detalhes da mensalidade'});await dialog.getByText('Saldo a pagar',{exact:true}).waitFor();check('Member sees payment details in an actual dialog',await dialog.locator('[role=alert]').count()===0);await shot(p,'interaction-member-due-detail');await p.keyboard.press('Escape');
  await p.goto(origin+'/financeiro');await p.getByRole('alert').first().waitFor();check('Direct treasury URL is denied to ordinary member',true);await shot(p,'interaction-member-finance-denied');await context.close();
  ({context,p}=await session('Treasury'));await p.goto(origin+'/mensalidades');await p.locator('#dues-state').selectOption('exempt');await p.waitForLoadState('networkidle');check('Exempt filter returns precisely one medium',await p.locator('tbody tr').count()===1);await p.getByRole('button',{name:'Ver detalhes',exact:true}).click();dialog=p.getByRole('dialog');await dialog.getByRole('region',{name:'Motivo da isenção'}).waitFor();check('Exemption reason is readable and distinct from payment',await dialog.getByText('Nenhum pagamento: mensalidade regularizada por isenção.',{exact:true}).count()===1);await shot(p,'interaction-treasury-exemption');await context.close();
  report.success=true;
 }catch(error){report.success=false;report.failure=error.message;process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync('/output/interaction-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));}
})();
