const { chromium } = require('playwright');
const NM = __dirname + '/node_modules', OUT = '/tmp/claude-0/-home-claude/f880023e-4047-5d94-81d4-3b8b32341d04/scratchpad';
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--headless=new', '--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'], ignoreDefaultArgs: ['--headless=old'] });
  for (const scheme of ['light', 'dark']) {
  const page = await (await b.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: scheme })).newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await page.route('https://cdn.jsdelivr.net/npm/**', (r) => { const u = r.request().url();
    const p = u.includes('OrbitControls') ? NM + '/three/examples/js/controls/OrbitControls.js' : u.includes('three.min') ? NM + '/three/build/three.min.js' : u.includes('jszip') ? NM + '/jszip/dist/jszip.min.js' : u.includes('autotable') ? NM + '/jspdf-autotable/dist/jspdf.plugin.autotable.min.js' : NM + '/jspdf/dist/jspdf.umd.min.js';
    r.fulfill({ path: p, contentType: 'application/javascript' }); });
  await page.route('https://fonts.**', (r) => r.abort());
  await page.goto('http://localhost:8765/index.html'); await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/g_${scheme}.png` });
  if (scheme === 'light') {
    await page.focus('#p_t_bot'); await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}/g_focus_tbot.png` });
    await page.focus('#p_X_cyl'); await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}/g_focus_xcyl.png` });
    // independent scroll
    const r = await page.evaluate(async () => { const a = document.querySelector('aside.params'), m = document.querySelector('main.res'); a.scrollTop = 600; await new Promise(r => setTimeout(r, 100)); return { aside: a.scrollTop, main: m.scrollTop, win: window.scrollY, ah: a.scrollHeight, ach: a.clientHeight, mh: m.scrollHeight, mch: m.clientHeight }; });
    console.log('scroll', JSON.stringify(r));
    await page.mouse.move(900, 600); await page.mouse.wheel(0, 900); await page.waitForTimeout(300);
    const r2 = await page.evaluate(() => ({ aside: document.querySelector('aside.params').scrollTop, main: document.querySelector('main.res').scrollTop, win: window.scrollY }));
    console.log('after wheel on main', JSON.stringify(r2));
    await page.screenshot({ path: `${OUT}/g_scrolled.png` });
    await page.fill('#p_t_top', '40'); await page.fill('#p_N_rib', '16'); await page.waitForTimeout(1800);
    await page.screenshot({ path: `${OUT}/g_changed.png` });
  }
  console.log(scheme, 'errors', errs.filter(e => !e.includes('TUNNEL') && !e.includes('404')));
  }
  await b.close();
})();
