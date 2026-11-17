/* Recorrido de extremo a extremo: las 8 alternativas (Base, A, AF2, B, C1, C2, C3, madera) × los 2 modos de accionamiento
   (guiado, drive_mode = 1; pivotado tipo KIET, drive_mode = 2) con Playwright (no forma parte de `npm test`).
   Uso: node tests/e2e_modos_alternativas_playwright.js [directorio de salida]   (requiere `playwright` con chromium y la herramienta construida)
   En cada combinación abre todas las pestañas, la simulación (empuje, retorno y reenganche) y los esquemas rápidos del navegador
   (PLANOS.buildPackage: SVG, DXF y página de impresión) y exige 0 errores de consola y 0 «NaN» (ni atributos «undefined») en los SVG.
   Guarda capturas de la pestaña Modelo de cada modo (Base). */
const path = require("path"), fs = require("fs"), assert = require("node:assert/strict");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const out = process.argv[2] || fs.mkdtempSync(path.join(require("os").tmpdir(), "tt300c-e2e-modos-"));
const html = "file://" + path.join(root, fs.readdirSync(root).filter((n) => /^Tornamesa_v.*\.html$/.test(n))[0]);
const ALTS = [["Base", "0", {}], ["A", "A", {}], ["AF2", "A", { fix_mode: 2 }], ["B", "B", {}], ["C1", "C1", {}], ["C2", "C2", {}], ["C3", "C3", {}], ["madera", "0", { opt_wood: 1 }]];
const OVER = { "0": {}, A: { opt_ss: 1 }, B: { opt_uhmw: 1 }, C1: { opt_bz: 1, bz_conf: 1 }, C2: { opt_bz: 1, bz_conf: 2 }, C3: { opt_bz: 1, bz_conf: 3 } };
const MALO = /NaN|="undefined"|="Infinity"|="-Infinity"/;

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({ viewport: { width: 1400, height: 1000 } })).newPage(), errs = [];
    page.on("pageerror", (e) => errs.push(String(e))); page.on("console", (m) => { if (m.type() === "error" && !/ERR_CONNECTION_REFUSED/.test(m.text())) errs.push(m.text()); });   // la pestaña Planos busca el generador local en 127.0.0.1:8765 (sin servidor: rechazo esperado)
    await page.goto(html);
    await page.waitForSelector("#bSim");
    const settle = () => page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando"), null, { timeout: 60000 }).then(() => page.waitForTimeout(250));
    const setP = async (id, v) => {
      await page.evaluate((id) => { const d = document.querySelector("#p_" + id).closest("details"); if (d) d.open = true; }, id);
      if (await page.getAttribute("#p_" + id, "type") === "checkbox") { if (v) await page.check("#p_" + id); else await page.uncheck("#p_" + id); } else await page.fill("#p_" + id, String(v));
      await settle();
    };
    const tabs = await page.$$eval("#tabs button", (bs) => bs.map((b) => b.dataset.t));
    const svgMalos = () => page.evaluate((re) => [...document.querySelectorAll("svg")].map((s) => s.outerHTML).filter((h) => new RegExp(re).test(h)).map((h) => h.slice(0, 160)), MALO.source);
    let n = 0;
    for (const modo of [1, 2]) {
      for (const [nom, sel, extra] of ALTS) {
        const t0 = Date.now();
        await page.click("#bReset"); await settle();
        await setP("drive_mode", modo);
        await page.selectOption("#altSel", sel); await settle();
        for (const [k, v] of Object.entries(extra)) await setP(k, v);
        // todas las pestañas (Temperatura y Tapones calculan en diferido)
        for (const t of tabs) {
          await page.click(`#tabs button[data-t="${t}"]`);
          if (t === "temp") await page.waitForFunction(() => !/Calculando/.test(document.querySelector('section[data-t="temp"]').textContent), null, { timeout: 180000 });
          if (t === "tapones") await page.waitForFunction(() => !/Calculando/.test(document.querySelector('section[data-t="tapones"]').textContent), null, { timeout: 180000 });
          await page.waitForTimeout(150);
        }
        if (nom === "Base") { await page.click('#tabs button[data-t="modelo"]'); await page.waitForTimeout(200); await page.locator('section[data-t="modelo"]').screenshot({ path: path.join(out, `modelo_${modo === 2 ? "pivotado" : "guiado"}.png`) }); }
        let malos = await svgMalos();
        assert.deepEqual(malos, [], `${nom} · modo ${modo}: SVG con NaN en las pestañas`);
        // simulación: las tres fases
        await page.click("#bSim"); await page.waitForSelector("#simDet");
        for (const f of ["empuje", "retorno", "reenganche"]) await page.evaluate((f) => SIM.seek(SIM.buscarFase(f)), f);
        malos = await svgMalos();
        assert.deepEqual(malos, [], `${nom} · modo ${modo}: SVG con NaN en la simulación`);
        await page.click("#bSimClose");
        // esquemas rápidos del navegador
        const pk = await page.evaluate(({ o, m }) => {
          const P = Object.assign(TT.defaults(), o, { drive_mode: m }), pk = PLANOS.buildPackage(P, TT.analyze(P, { noFEA: true }), {}), dec = new TextDecoder("latin1");
          return pk.files.filter((f) => /svg|dxf|html/.test(f.kind)).map((f) => [f.name, dec.decode(f.data)]).map(([nm, tx]) => [nm, /NaN|undefined|Infinity/.test(tx)]);
        }, { o: Object.assign({}, OVER[sel], extra), m: modo });
        assert.deepEqual(pk.filter((x) => x[1]).map((x) => x[0]), [], `${nom} · modo ${modo}: esquemas con NaN`);
        assert.deepEqual(errs, [], `${nom} · modo ${modo}: errores de consola: ` + errs.slice(0, 3).join(" | "));
        n++;
        console.log(`${modo === 2 ? "pivotado" : "guiado  "} · ${nom.padEnd(6)}: ${tabs.length} pestañas, simulación y ${pk.length} archivos de esquemas sin NaN ni errores (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
      }
    }
    console.log(`e2e modos × alternativas: OK (${n} combinaciones) · capturas en ${out}`);
  } finally { await browser.close(); }
})().catch((e) => { console.error(e); process.exit(1); });
