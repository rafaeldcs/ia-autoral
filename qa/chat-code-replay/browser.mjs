// Frozen browser assertions, independent of the generated component.
import { chromium } from '/opt/node_modules/playwright/index.mjs';
import fs from 'node:fs';

const results = [];
const screenshots = {};
const browser = await chromium.launch({headless:true, args:['--no-sandbox','--disable-dev-shm-usage']});
const page = await browser.newPage({viewport:{width:1280,height:800}});
const errors = [];
page.on('pageerror', error => errors.push(error.message));
const complete = async item => {
  const button=item.getByRole('button');
  return await button.isDisabled() || await button.getAttribute('aria-pressed')==='true' ||
    /conclu[íi]d[ao]/i.test(await item.innerText()) || await item.evaluate(node=>
      [node,...node.querySelectorAll('*')].some(n=>getComputedStyle(n).textDecorationLine.includes('line-through')));
};
async function check(name, test) {
  try { await test(); results.push({name,passed:true}); }
  catch(error) { results.push({name,passed:false,detail:String(error.message).slice(0,1800)}); }
}
function assert(condition, message) { if(!condition)throw new Error(message); }
await page.goto('http://127.0.0.1:3217/',{waitUntil:'networkidle'});
screenshots['browser-before.png']=(await page.screenshot({fullPage:true})).toString('base64');
await check('all_initial_tasks',async()=>{
  assert(await page.locator('li').count()===3,'Expected all three tasks');
  for(const title of ['Revisar código','Escrever testes','Documentar API'])
    assert(await page.getByRole('button',{name:new RegExp(title)}).count()===1,'Accessible action missing: '+title);
});
await check('initial_completed_state_is_observable',async()=>{
  assert(!await complete(page.locator('li').nth(0)),'First task should start pending');
  assert(await complete(page.locator('li').nth(2)),'Completed prop has no visible/accessible state');
});
await check('click_completes_only_selected_and_keeps_list',async()=>{
  await page.locator('li').nth(0).getByRole('button').click();
  await page.waitForTimeout(150);
  assert(await page.locator('li').count()===3,'Completing removed a task');
  assert(await complete(page.locator('li').nth(0)),'Click produced no observable completion');
  assert(!await complete(page.locator('li').nth(1)),'Unselected task changed');
});
screenshots['browser-after.png']=(await page.screenshot({fullPage:true})).toString('base64');
await check('completion_is_idempotent',async()=>{
  const button=page.locator('li').nth(0).getByRole('button');
  if(!await button.isDisabled())await button.click();
  assert(await complete(page.locator('li').nth(0)),'Repeated completion is not observably complete');
});
await check('keyboard_can_complete_task',async()=>{
  await page.locator('li').nth(1).getByRole('button').focus();
  await page.keyboard.press('Enter');await page.waitForTimeout(150);
  assert(await complete(page.locator('li').nth(1)),'Keyboard activation did not complete task');
});
await check('responsive_320px',async()=>{
  await page.setViewportSize({width:320,height:640});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Page overflows horizontally');
});
await check('empty_props_render_no_tasks',async()=>{
  await page.goto('http://127.0.0.1:3217/empty',{waitUntil:'networkidle'});
  assert(await page.locator('li').count()===0,'Empty props produced synthetic tasks');
});
await check('titles_are_inert_text',async()=>{
  await page.goto('http://127.0.0.1:3217/escape',{waitUntil:'networkidle'});
  assert(await page.locator('img').count()===0 && await page.evaluate(()=>window.INJECTED)===undefined,'Title became executable markup');
  assert((await page.locator('li').innerText()).includes('<img'),'Original title text was lost');
});
await check('no_browser_exceptions',async()=>assert(errors.length===0,errors.join('\n')));
await browser.close();
fs.writeFileSync('/tmp/chat-code/browser-results.json',JSON.stringify({results,screenshots,errors}));
