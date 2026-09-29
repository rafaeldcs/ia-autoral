"""Browser-to-chat-to-neural-weights check in an isolated ephemeral LocalAuthor."""
import argparse,json,os,shutil,subprocess,sys,tempfile,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src')]
from localauthor.config import Settings
from localauthor.application import Application
from localauthor.server import create_server
p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
if not Path('/.dockerenv').exists():raise RuntimeError('Sandbox required')
with tempfile.TemporaryDirectory() as tmp:
    home=Path(tmp)/'home';settings=Settings.load(home);settings.port=18765
    destination=home/'models'/args.model.name;destination.mkdir()
    for name in ('best-validation.npz','best-validation.npz.sha256'):shutil.copyfile(args.model/name,destination/name)
    shutil.copyfile(args.model/'qualification.json',home/'exports/code-repair-qualification.json')
    project_root=Path(tmp)/'project';project_root.mkdir()
    app=Application(settings);app.store.add_project('Laboratório de correções',str(project_root))
    server=create_server(app,ROOT/'ui');app.start();thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    args.output.mkdir(parents=True,exist_ok=True)
    script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict');
const {chromium}=require('/opt/node_modules/playwright');
(async()=>{
 const token=fs.readFileSync(process.env.QA_TOKEN_PATH,'utf8').trim();
 const browser=await chromium.launch({args:['--no-sandbox','--disable-dev-shm-usage']});
 const report={checks:[],success:false};const check=(name,ok)=>{report.checks.push({name,passed:!!ok});assert(ok,name);};
 try{
  const context=await browser.newContext({viewport:{width:1280,height:960},serviceWorkers:'block'});
  await context.route('**/*',r=>new URL(r.request().url()).origin==='http://127.0.0.1:18765'?r.continue():r.abort());
  const page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto('http://127.0.0.1:18765');await page.locator('#local-token').fill(token);await page.locator('#connect-form button').click();await page.locator('#studio').waitFor();
  await page.locator('#repair-examples summary').click();await page.getByRole('button',{name:'Testar configuração do servidor',exact:true}).click();
  check('Example selects neural generation and preserves code',await page.locator('#response-mode').inputValue()==='model'&&await page.locator('#input-format').inputValue()==='code');
  check('Prefilled source is broken input, not a supplied answer',(await page.locator('#message-input').inputValue()).includes('{ reverse_proxy api:8080 }'));
  await page.locator('#send').click();await page.locator('.message.assistant pre').waitFor();
  check('Chat produces the Caddy correction from weights',await page.locator('.message.assistant pre').innerText()==='handle @api {\n    reverse_proxy api:8080\n}');
  check('Qualification limits are visible',(await page.locator('.message.assistant small').innerText()).includes('duas famílias'));
  await page.screenshot({path:process.env.QA_OUTPUT+'/caddy-chat.png',fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'Testar validação C#',exact:true}).click();await page.locator('#send').click();await page.waitForFunction(()=>document.querySelectorAll('.message.assistant pre').length===2);
  check('Chat produces the C# condition from weights',await page.locator('.message.assistant pre').last().innerText()==='input.Endpoint != null && Rules.ValidPushEndpoint(input.Endpoint)');
  await page.setViewportSize({width:390,height:844});check('Mobile page has no horizontal overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.waitForTimeout(300);await page.locator('.message.assistant').last().scrollIntoViewIfNeeded();
  await page.screenshot({path:process.env.QA_OUTPUT+'/csharp-chat-mobile.png',fullPage:true,animations:'disabled'});
  report.success=true;
 }catch(error){report.failure=error.message;process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync(process.env.QA_OUTPUT+'/chat-smoke.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));}
})();
'''
    # The raw JS string contains escaped newlines in expected JS string literals.
    script=script.replace('\\\\n','\\n')
    try:
        result=subprocess.run(['node','-e',script],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90,
            env={**os.environ,'QA_TOKEN_PATH':str(home/'api.token'),'QA_OUTPUT':str(args.output)})
        print(result.stdout);code=result.returncode
    finally:server.shutdown();server.server_close();app.close()
raise SystemExit(code)
