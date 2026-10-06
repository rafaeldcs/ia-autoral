// Trusted acceptance checks. Credentials stay in memory; screenshots are taken after login.
const fs = require('node:fs');
const {chromium, expect} = require(fs.existsSync('/opt/qa/node_modules/@playwright/test') ? '/opt/qa/node_modules/@playwright/test' : '/opt/node_modules/@playwright/test');
(async()=>{
  const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
  const report=[];
  try {
    for(const role of ['admin','manager','member','viewer']) {
      const context=await browser.newContext({viewport:{width:1440,height:1000}});
      const page=await context.newPage(); const errors=[];
      page.on('pageerror',error=>errors.push(error.message));
      await page.goto('http://127.0.0.1:3100');
      await page.getByLabel('E-mail',{exact:true}).fill(role+'@orbit.test');
      await page.getByLabel('Senha',{exact:true}).fill(process.env.ORBIT_QA_PASSWORD);
      await page.getByRole('button',{name:'Entrar',exact:true}).click();
      let releaseInitialGit, firstGitBlocked=false, holdFirstGit=role==='admin';
      const initialGitReady=new Promise(resolve=>{releaseInitialGit=resolve;});
      if(role==='admin')await page.route('**/api/projects/*/git',async route=>{
        if(holdFirstGit&&route.request().method()==='GET'){
          holdFirstGit=false;firstGitBlocked=true;await initialGitReady;
        }
        await route.continue();
      });
      const gitTab=page.getByRole('main').getByRole('button',{name:'Código e entregas',exact:true});
      await expect(gitTab).toBeVisible();
      await gitTab.click();
      await expect(page.getByRole('heading',{name:/Código e entregas/})).toBeVisible();
      if(role==='admin') {
        await expect.poll(()=>firstGitBlocked).toBe(true);
        try {await expect(page.getByRole('button',{name:'Salvar repositório'})).toHaveCount(0);}
        finally {releaseInitialGit();}
        await expect(page.getByRole('button',{name:'Salvar repositório'})).toBeVisible();
        await page.getByLabel('Branch',{exact:true}).fill('invalid branch');
        await page.getByRole('button',{name:'Salvar repositório'}).click();
        await expect(page.getByRole('alert').filter({hasText:/branch|Branch/})).toBeVisible();
        await page.getByLabel('Branch',{exact:true}).fill('codex/local-learning-execution');
        await page.getByRole('button',{name:'Salvar repositório'}).click();
        await expect(page.getByRole('alert').filter({hasText:/branch|Branch/})).toHaveCount(0);
      } else await expect(page.getByRole('button',{name:'Salvar repositório'})).toHaveCount(0);
      const manage=role==='admin'||role==='manager';
      if(manage) {
        await expect(page.getByRole('button',{name:/PULL|Atualizar código/})).toBeVisible();
        await page.getByRole('button',{name:/PUSH|Enviar commits/}).click();
        await expect(page.getByRole('button',{name:'Confirmar',exact:true})).toBeVisible();
        await page.getByRole('button',{name:'Cancelar',exact:true}).click();
        await expect(page.getByRole('button',{name:'Confirmar',exact:true})).toHaveCount(0);
      } else await expect(page.getByRole('button',{name:/PULL|Atualizar código/})).toHaveCount(0);
      await expect(page.getByRole('button',{name:'GQA-1',exact:true}).first()).toBeVisible();
      await page.getByRole('button',{name:'GQA-1',exact:true}).first().click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await expect(page.getByRole('dialog')).toContainText('GQA-1');
      await page.getByRole('button',{name:'Fechar tarefa'}).click();
      await expect(page.getByLabel('URL para clone')).toHaveValue(/\/git\/[a-f0-9-]+\.git$/);
      const hostedPanel=page.getByRole('heading',{name:'Repositório do Orbit',exact:true}).locator('..');
      await expect(hostedPanel.getByRole('button',{name:'GQA-1',exact:true}).first()).toBeVisible();
      await page.getByRole('button',{name:'xss.txt',exact:true}).click();
      await expect(page.locator('pre').filter({hasText:'globalThis.orbitUnsafePreview=true'})).toBeVisible();
      expect(await page.evaluate(()=>globalThis.orbitUnsafePreview)).toBeUndefined();
      const write=page.getByLabel('Permitir push',{exact:true});
      if(role==='viewer')await expect(write).toBeDisabled();else await write.check();
      await page.getByLabel('Nome do token',{exact:true}).fill('Navegador '+role);
      await page.getByRole('button',{name:'Criar token Git',exact:true}).click();
      await expect(page.getByLabel('Token Git gerado',{exact:true})).toHaveAttribute('type','password');
      await expect(page.getByLabel('Token Git gerado',{exact:true})).toHaveValue(/^orb_[a-f0-9]{64}$/);
      await page.getByRole('button',{name:'Ocultar e descartar token',exact:true}).click();
      await expect(page.getByLabel('Token Git gerado',{exact:true})).toHaveCount(0);
      await page.getByRole('button',{name:'Revogar Navegador '+role,exact:true}).click();
      await expect(page.getByRole('button',{name:'Revogar Navegador '+role,exact:true})).toBeDisabled();
      await page.evaluate(()=>scrollTo(0,0));
      await page.screenshot({path:'/tmp/evidence/orbit-'+role+'-desktop.png',fullPage:true,animations:'disabled'});
      if(role==='admin') {
        await page.setViewportSize({width:390,height:844});
        await page.waitForTimeout(300);
        await page.screenshot({path:'/tmp/evidence/orbit-mobile.png',fullPage:true,animations:'disabled'});
        const widths=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth}));
        expect(widths.scroll).toBeLessThanOrEqual(widths.viewport+1);
      }
      expect(errors).toEqual([]);report.push({role,passed:true});await context.close();
    }
    const missing=await browser.newContext();const page=await missing.newPage();
    await page.goto('http://127.0.0.1:3100');
    await page.getByLabel('E-mail',{exact:true}).fill('admin@orbit.test');
    await page.getByLabel('Senha',{exact:true}).fill(process.env.ORBIT_QA_PASSWORD);
    await page.getByRole('button',{name:'Entrar',exact:true}).click();
    await page.getByRole('main').getByRole('button',{name:'Código e entregas',exact:true}).click();
    await page.getByLabel('Remover token salvo').check();
    await page.getByRole('button',{name:'Salvar repositório'}).click();
    await expect(page.getByRole('button',{name:'Enviar commits'})).toBeDisabled();
    await expect(page.getByRole('button',{name:'Publicar homologação'})).toBeDisabled();
    await expect(page.getByRole('status').filter({hasText:'peça ao administrador'})).toBeVisible();
    await missing.close();
    fs.writeFileSync('/tmp/evidence/browser.json',JSON.stringify({roles:report,passed:true},null,2));
  } finally {await browser.close();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
