/* Tutor-authored functional checks. LocalAuthor executes them, not neural authorship.
 * Real login/Next/API, plus a declared response fixture for a missing date.
 * Never changes database records or captures the credential form.
 */
const fs = require('node:fs');
const assert = require('node:assert/strict');
const {chromium} = require('/opt/node_modules/playwright');
assert(fs.existsSync('/.dockerenv'), 'Reviewed sandbox required');
const origin = 'http://localhost:3180';
const users = JSON.parse(fs.readFileSync('/input/access.json', 'utf8'));
const output = '/output';
fs.mkdirSync(output, {recursive: true});
const report = {author: 'Codex', executor: 'LocalAuthor browser worker',
  scope: 'Real simulation login and cleaning list; null date injected into one browser response only',
  checks: [], success: false};
function check(name, passed) {
  report.checks.push({name, passed: !!passed});
  assert(passed, name);
}
(async () => {
  const browser = await chromium.launch({args: ['--no-sandbox', '--disable-dev-shm-usage']});
  try {
    const context = await browser.newContext({viewport: {width: 1366, height: 900}, serviceWorkers: 'block'});
    let injectNull = false, substituted = false;
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.origin !== origin) return route.abort();
      if (url.pathname === '/api/cleanings' && injectNull && route.request().method() === 'GET') {
        const response = await route.fetch();
        assert.equal(response.status(), 200);
        const data = await response.json();
        assert(Array.isArray(data) && data.length > 0, 'Positive control requires actual seeded cleaning');
        data[0].startsAt = null;
        substituted = true;
        return route.fulfill({response, json: data});
      }
      return route.continue();
    });
    await page.goto(origin + '/entrar');
    await page.locator('[name=login]').fill(users.Coordinator.login);
    await page.locator('[name=password]').fill(users.Coordinator.password);
    await page.getByRole('button', {name: 'Entrar no aplicativo', exact: true}).click();
    await page.locator('#main-content').waitFor();
    check('Real coordinator authenticates', !page.url().includes('/entrar'));
    await page.goto(origin + '/limpezas');
    await page.waitForLoadState('networkidle');
    check('Actual API supplies visible cleaning cards', await page.locator('a[href^="/limpezas/"]').count() > 0);
    check('Original response has no missing-date label', !(await page.locator('#main-content').innerText()).includes('Data indisponível'));
    injectNull = true;
    await page.reload();
    await page.getByText('Data indisponível', {exact: false}).first().waitFor();
    check('Missing date fixture was exercised', substituted);
    check('Actual React card renders absence, not 1969', !(await page.locator('#main-content').innerText()).includes('1969'));
    check('No error notice for missing date', await page.locator('#main-content [role=alert]').count() === 0);
    await page.screenshot({path: output + '/date-missing-desktop.png', fullPage: true, animations: 'disabled'});
    await page.setViewportSize({width: 390, height: 844});
    check('Mobile has no horizontal overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.screenshot({path: output + '/date-missing-mobile.png', fullPage: true, animations: 'disabled'});
    injectNull = false;
    await page.reload();
    await page.waitForLoadState('networkidle');
    check('Removing fixture restores actual API dates', !(await page.locator('#main-content').innerText()).includes('Data indisponível'));
    check('No unhandled browser errors', errors.length === 0);
    report.success = true;
    await context.close();
  } catch (error) {
    report.failure = error.message;
    process.exitCode = 1;
  } finally {
    await browser.close();
    fs.writeFileSync(output + '/functional-report.json', JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  }
})();
