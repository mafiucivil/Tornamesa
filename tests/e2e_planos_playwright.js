/* Verificación de extremo a extremo del checkbox «Exportar paquete de dibujo» con Playwright (no forma parte de `npm test`).
   Uso: node tests/e2e_planos_playwright.js [directorio de salida]  (requiere `playwright` con chromium instalado y dist/ construido: npm run build) */
const path = require("path"), fs = require("fs"), assert = require("node:assert/strict");
const { chromium } = require("playwright");
const out = process.argv[2] || fs.mkdtempSync(path.join(require("os").tmpdir(), "tt300c-e2e-"));
const html = "file://" + path.resolve(__dirname, "..", require("fs").readdirSync(path.resolve(__dirname, "..")).filter((n) => /^Tornamesa_v.*\.html$/.test(n))[0]);
const ALTS = [["acero-acero", null], ["A", "opt_ss"], ["B", "opt_uhmw"], ["C", "opt_bz"]];
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 1500, height: 1000 } });
  const page = await ctx.newPage(), errs = [];
  page.on("pageerror", (e) => errs.push(String(e))); page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
  await page.goto(html);
  await page.waitForSelector("#pkgChk");
  assert.equal(await page.isVisible("#pkgPanel"), false, "el panel debe estar oculto al inicio");
  await page.check("#pkgChk");
  assert.equal(await page.isVisible("#pkgPanel"), true);
  for (const [name, id] of ALTS) {
    for (const o of ["opt_ss", "opt_uhmw", "opt_bz"]) if (await page.isChecked("#p_" + o) && o !== id) await page.uncheck("#p_" + o);
    if (id) await page.check("#p_" + id);
    await page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando"));
    await page.waitForTimeout(700);
    const txt = await page.textContent("#pkgPanel");
    const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#bPkgZip")]);
    const zipPath = path.join(out, `paquete_${name}.zip`); await dl.saveAs(zipPath);
    const sz = fs.statSync(zipPath).size; assert.ok(sz > 20000, "ZIP vacío");
    const [dd] = await Promise.all([page.waitForEvent("download"), page.click("#bPkgDxf")]); await dd.saveAs(path.join(out, `${name}_` + dd.suggestedFilename()));
    const [dc] = await Promise.all([page.waitForEvent("download"), page.click("#bPkgCsv")]); await dc.saveAs(path.join(out, `${name}_lista.csv`));
    const [dj] = await Promise.all([page.waitForEvent("download"), page.click("#bPkgJson")]); await dj.saveAs(path.join(out, `${name}_design.json`));
    const [pop] = await Promise.all([page.waitForEvent("popup"), page.click("#bPkgPrint")]);
    await pop.waitForLoadState();
    assert.equal(await pop.locator("svg").count(), 5, "5 láminas en la página de impresión");
    await pop.screenshot({ path: path.join(out, `impresion_${name}.png`), fullPage: false });
    await pop.pdf({ path: path.join(out, `impresion_${name}.pdf`), preferCSSPageSize: true, printBackground: true });
    await pop.close();
    console.log(name, "OK", sz, "bytes ·", txt.replace(/\s+/g, " ").slice(0, 110));
  }
  assert.deepEqual(errs, [], "errores de consola: " + errs.join("|"));
  await page.screenshot({ path: path.join(out, "herramienta.png") });
  await browser.close();
  console.log("salida en", out);
})().catch((e) => { console.error(e); process.exit(1); });
