const { chromium } = require('playwright');
const path = require('path');
const NM = path.join(__dirname, 'node_modules');
const map = {
  'jspdf@2.5.1/dist/jspdf.umd.min.js': NM + '/jspdf/dist/jspdf.umd.min.js',
  'jspdf-autotable@3.8.2/dist/jspdf.plugin.autotable.min.js': NM + '/jspdf-autotable/dist/jspdf.plugin.autotable.min.js',
  'jszip@3.10.1/dist/jszip.min.js': NM + '/jszip/dist/jszip.min.js',
};
const OUT = process.argv[2] || '/tmp/claude-0/-home-claude/f880023e-4047-5d94-81d4-3b8b32341d04/scratchpad';
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--headless=new'], ignoreDefaultArgs: ['--headless=old'] });
  for (const scheme of ['light', 'dark']) {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: scheme, acceptDownloads: true });
    const page = await ctx.newPage();
    const errs = [];
    page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
    page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
    await page.route('https://cdn.jsdelivr.net/npm/**', (r) => { const k = Object.keys(map).find((k) => r.request().url().endsWith(k)); k ? r.fulfill({ path: map[k], contentType: 'application/javascript' }) : r.abort(); });
    await page.route('https://fonts.**', (r) => r.abort());
    await page.goto('http://localhost:8765/index.html');
    await page.waitForTimeout(1500);
    const tabs = scheme === 'light' ? ['resumen', 'actuador', 'diagramas', 'verificaciones', 'fea', 'planos'] : ['resumen', 'fea'];
    for (const t of tabs) {
      await page.click(`.tab[data-t="${t}"]`); await page.waitForTimeout(300);
      await page.screenshot({ path: `${OUT}/s_${scheme}_${t}.png`, fullPage: true });
    }
    if (scheme === 'light') {
      // downloads
      for (const id of ['bSheetPdf', 'bSheetDxf', 'bMemo']) {
        const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 30000 }), page.click('#' + id)]);
        const p = `${OUT}/dl_${dl.suggestedFilename()}`; await dl.saveAs(p); console.log('downloaded', p);
      }
      const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 30000 }), page.click('[data-file$="Diseno.pdf"]')]);
      console.log('issued', dl.suggestedFilename());
      // change a parameter
      await page.click('.tab[data-t="resumen"]');
      await page.fill('#p_mu', '0.35'); await page.waitForTimeout(1500);
      console.log('verdict mu=0.35:', await page.textContent('#verdict'));
      await page.screenshot({ path: `${OUT}/s_mu035.png` });
      await page.fill('#p_mu', '0.20'); await page.fill('#p_t_bot', '20'); await page.waitForTimeout(1500);
      console.log('chips t_bot=20:', await page.textContent('#chips'));
    }
    // mobile
    if (scheme === 'light') {
      await page.setViewportSize({ width: 400, height: 900 });
      await page.waitForTimeout(400);
      const sw = await page.evaluate(() => document.documentElement.scrollWidth);
      console.log('mobile scrollWidth', sw);
      await page.screenshot({ path: `${OUT}/s_mobile.png` });
    }
    console.log(scheme, 'errors:', errs.slice(0, 10));
    await ctx.close();
  }
  await b.close();
})();
