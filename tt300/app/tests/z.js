const { chromium } = require('playwright');
const NM = __dirname + '/node_modules';
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--headless=new'], ignoreDefaultArgs: ['--headless=old'] });
  const page = await (await b.newContext({ acceptDownloads: true })).newPage();
  const errs=[]; page.on('pageerror', e=>errs.push(e.message));
  await page.route('https://cdn.jsdelivr.net/npm/**', (r) => { const u=r.request().url(); const p = u.includes('jszip')? NM+'/jszip/dist/jszip.min.js' : u.includes('autotable')? NM+'/jspdf-autotable/dist/jspdf.plugin.autotable.min.js' : NM+'/jspdf/dist/jspdf.umd.min.js'; r.fulfill({path:p, contentType:'application/javascript'}); });
  await page.route('https://fonts.**', (r) => r.abort());
  await page.goto('http://localhost:8765/index.html#planos'); await page.waitForTimeout(1500);
  const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 30000 }), page.click('#bIssuedZip')]);
  await dl.saveAs('/tmp/claude-0/-home-claude/f880023e-4047-5d94-81d4-3b8b32341d04/scratchpad/issued.zip'); console.log('ok', dl.suggestedFilename(), errs);
  await b.close();
})();
