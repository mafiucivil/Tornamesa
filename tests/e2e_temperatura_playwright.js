/* Verificación de extremo a extremo de la pestaña «Temperatura» con Playwright (no forma parte de `npm test`).
   Uso: node tests/e2e_temperatura_playwright.js [directorio de salida]  (requiere `playwright` con chromium y la herramienta construida: npm run build) */
const path = require("path"), fs = require("fs"), assert = require("node:assert/strict");
const { chromium } = require("playwright");
const out = process.argv[2] || fs.mkdtempSync(path.join(require("os").tmpdir(), "tt300c-temp-"));
const root = path.resolve(__dirname, "..");
const html = "file://" + path.join(root, fs.readdirSync(root).filter((n) => /^Tornamesa_v.*\.html$/.test(n))[0]);
const ready = (page) => page.waitForFunction(() => { const t = document.querySelector('section[data-t="temp"]').textContent; return t.includes("Por alternativa") && !t.includes("Calculando el escenario"); }, null, { timeout: 90000 });
(async () => {
  const browser = await chromium.launch(), ctx = await browser.newContext({ viewport: { width: 1500, height: 1000 } });
  const page = await ctx.newPage(), errs = [];
  page.on("pageerror", (e) => errs.push(String(e))); page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
  await page.goto(html); await page.waitForSelector("#altSel");
  await page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando"));
  await page.click('#tabs button[data-t="temp"]'); await page.waitForSelector("#bSolar"); await ready(page);
  await page.click("#bSolar"); await ready(page);
  assert.equal(await page.inputValue("#tServ"), "80"); assert.equal(await page.inputValue("#dTgrad"), "15"); assert.equal(await page.inputValue("#p_T_serv"), "80");
  for (const v of ["0", "A", "B", "C1", "C2", "C3"]) {
    await page.selectOption("#altSel", v);
    await page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando")); await ready(page);
    const t = await page.textContent('section[data-t="temp"]');
    for (const k of ["Datos supuestos", "ASME BTH-1", "Aceite atrapado", "Sensibilidad a la temperatura", "verificaciones que más empeoran", "Juntas de dilatación"]) assert.ok(t.includes(k), v + ": falta «" + k + "»");
    console.log(v, "OK", t.length);
  }
  await page.selectOption("#altSel", "B"); await ready(page);
  await page.screenshot({ path: path.join(out, "temperatura_B.png") });
  for (const t of ["resumen", "verif", "masa", "temp"]) await page.click(`#tabs button[data-t="${t}"]`);
  assert.deepEqual(errs, [], "errores de consola: " + errs.join("|"));
  await browser.close(); console.log("salida en", out);
})().catch((e) => { console.error(e); process.exit(1); });
