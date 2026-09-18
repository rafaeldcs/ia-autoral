// Reviewed LocalAuthor tool implementation. No model-generated JS is executed.
const fs = require('node:fs');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const { chromium } = require('/opt/node_modules/playwright');
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const job = JSON.parse(fs.readFileSync('/input/job.json', 'utf8'));

async function main() {
  const browser = await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
  const results = [];
  try {
    for (let i = 0; i < job.urls.length; i++) {
      const target = new URL(job.urls[i]);
      const context = await browser.newContext({viewport:{width:1440,height:960}, locale:'pt-BR',
        acceptDownloads:false, serviceWorkers:'block'});
      const page = await context.newPage();
      const denied = new Set();
      await context.route('**/*', async route => {
        const request = route.request();
        const url = new URL(request.url());
        if (url.protocol !== 'https:' || (url.port && url.port !== '443') || url.username || url.password ||
            !job.allowedHosts.includes(url.hostname) || !['GET','HEAD'].includes(request.method())) {
          denied.add(url.hostname + ':' + request.method()); return route.abort();
        }
        // Targets are DNS-pinned by the host after public-address validation.
        return route.continue();
      });
      const item = {url:target.href, capturedBy:'LocalAuthor isolated browser tool',
                    requestedBy:'user through LocalAuthor CLI', browserControlledByCodex:false,
                    authenticated:false, observedAt:new Date().toISOString()};
      try {
        const response = await page.goto(target.href,{waitUntil:'domcontentloaded',timeout:45000});
        // A bounded browser wait allows hydration without an unbounded networkidle.
        await page.locator('body').waitFor({state:'visible',timeout:15000});
        await page.waitForTimeout(2000);
        const observation = await page.evaluate(({origin,status}) => ({
          url:location.href, authorizedOrigin:origin, status, title:document.title,
          loading:[...document.querySelectorAll('[aria-busy="true"]')].some(e=>e.getClientRects().length>0),
          passwordFilled:[...document.querySelectorAll('input[type="password"]')].some(e=>e.value.length>0)
        }), {origin:target.origin,status:response?.status() || 0});
        // No password values, cookies or form contents leave the browser.
        const decisionRun = cp.spawnSync('python3',['-m','localauthor.capture_decision','/input/policy.npz'],{
          input:JSON.stringify(observation),encoding:'utf8',timeout:15000,
          env:{...process.env,PYTHONPATH:'/runtime/src',OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1'}});
        if (decisionRun.status !== 0) throw new Error('Local model inference failed; no screenshot fallback.');
        item.decision = JSON.parse(decisionRun.stdout);
        item.title = observation.title;
        if (!item.decision.authorized) {
          item.state='not_captured'; item.reason='Local model or guard did not authorize recording.';
        } else {
          // Recheck immediately before the tool: stale navigation or filled
          // password inputs invalidate the decision. This browser never logs in.
          const fresh = await page.evaluate(() => ({url:location.href,
            secret:[...document.querySelectorAll('input[type="password"]')].some(e=>e.value.length>0)}));
          if (fresh.url !== observation.url || fresh.secret) throw new Error('Observation changed before capture.');
          item.file = String(i+1).padStart(3,'0')+'.png';
          const png = await page.screenshot({path:'/output/'+item.file,fullPage:false});
          item.sha256=hash(png); item.bytes=png.length; item.state='captured';
          item.toolReceipt={tool:'browser.screenshot',executed:true,artifactHash:item.sha256};
        }
      } catch (error) {
        item.state='failed'; item.reason=String(error.message).slice(0,350);
      } finally {
        item.deniedRequests=[...denied]; results.push(item); await context.close();
        fs.writeFileSync('/output/captures.json',JSON.stringify(results,null,2));
      }
    }
  } finally { await browser.close(); }
  console.log(JSON.stringify({captured:results.filter(x=>x.state==='captured').length,total:results.length,
    allSitesQualified:false,browserControlledByCodex:false}));
}
main().catch(error=>{console.error(String(error.message));process.exitCode=1;});
