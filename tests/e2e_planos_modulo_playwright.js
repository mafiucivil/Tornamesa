/* Verificación de extremo a extremo de la pestaña «Planos» (generación a pedido) con Playwright (no forma parte de `npm test`).
   Uso: node tests/e2e_planos_modulo_playwright.js [directorio de salida] [--generar]
   Requiere `playwright` con chromium, python3 y la herramienta construida (python3 tools/build_tt300c.py).
   Comprueba:
     1. servidor caído (página abierta como file://): estado «no responde», instrucciones de Instalar_generador_planos.bat y
        Generar_planos_Tornamesa.bat, botón «Generar planos» deshabilitado (se omite si ya había un servidor en 127.0.0.1:8765);
     2. con tools/servidor_planos.py levantado: herramienta servida por el servidor, generador activo, botón habilitado, resumen de la
        alternativa y de los parámetros que se enviarán (cambia al instante con #altSel y con un parámetro);
     3. historial (/api/listar): «Abrir» una generación anterior muestra Generales, Fabricación y Armado con enlaces que el servidor entrega;
     4. con --generar: genera el caso por defecto completo con el servidor real (unos 6 min), sigue el avance y comprueba el juego final.
   Capturas: panel_planos_caido.png, panel_planos_generando.png, panel_planos_terminado.png (o panel_planos_historial.png sin --generar). */
const path = require("path"), fs = require("fs"), assert = require("node:assert/strict"), { spawn } = require("child_process");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const args = process.argv.slice(2), GENERAR = args.includes("--generar");
const out = args.filter((a) => !a.startsWith("--"))[0] || fs.mkdtempSync(path.join(require("os").tmpdir(), "tt300c-e2e-planos-"));
const htmlName = fs.readdirSync(root).filter((n) => /^Tornamesa_v.*\.html$/.test(n))[0];
const BASE = "http://127.0.0.1:8765";
const ping = () => fetch(BASE + "/api/ping").then((r) => r.ok).catch(() => false);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const settle = (page) => page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando"), null, { timeout: 60000 }).then(() => page.waitForTimeout(300));
const shot = (page, name) => page.locator('section[data-t="planos"]').screenshot({ path: path.join(out, name) });

async function servidor() {
  const py = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
  const p = spawn(py, [path.join(root, "tools", "servidor_planos.py"), "--no-abrir"], { cwd: root, stdio: "ignore" });
  for (let i = 0; i < 120; i++) { if (await ping()) return p; await sleep(500); }
  p.kill(); throw new Error("el servidor de planos no respondió en 60 s");
}
async function juego(page, req, sel) {
  const grupos = await page.$$eval(sel + " a[data-pdf]", (as) => as.map((a) => a.dataset.pdf));
  assert.deepEqual(grupos, ["generales", "fabricacion", "armado"], "PDF de los tres grupos");
  const files = await page.$$eval(sel + " a[data-f]", (as) => as.map((a) => a.dataset.f));
  for (const f of ["combinado", "despiece_xlsx", "step", "dxf_zip"]) assert.ok(files.includes(f), "falta el enlace " + f);
  const hrefs = await page.$$eval(sel + " a[href]", (as) => as.map((a) => a.href));
  for (const h of hrefs) {
    assert.ok(h.startsWith(BASE + "/salidas/"), "enlace servido por el generador local: " + h);
    const r = await req.head(h); assert.equal(r.status(), 200, "el servidor entrega " + h);
  }
  const n = await page.$$eval(sel + " .pl-grp", (cs) => cs.map((c) => parseInt(c.querySelector(".big").textContent, 10)));
  return { enlaces: hrefs.length, laminas: n };
}

(async () => {
  let proc = null;
  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({ viewport: { width: 1500, height: 1200 } });
    const errs = [];
    const watch = (pg) => { pg.on("pageerror", (e) => errs.push(String(e))); pg.on("console", (m) => { if (m.type() === "error" && !/ERR_CONNECTION_REFUSED/.test(m.text())) errs.push(m.text()); }); };
    // 1. servidor caído
    if (!(await ping())) {
      const pf = await ctx.newPage(); watch(pf);
      await pf.goto("file://" + path.join(root, htmlName) + "#planos");
      await pf.waitForSelector('#genEstado[data-srv="inactivo"]', { timeout: 15000 });
      const t = await pf.textContent("#plSrv");
      assert.match(t, /no responde/); assert.match(t, /Instalar_generador_planos\.bat/); assert.match(t, /Generar_planos_Tornamesa\.bat/);
      assert.equal(await pf.isEnabled("#bGen"), false, "sin servidor el botón está deshabilitado");
      assert.match(await pf.textContent("#plHist"), /Disponible con el generador local activo/);
      assert.match(await pf.textContent("#plAdv"), /ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO\./);
      await shot(pf, "panel_planos_caido.png");
      console.log("servidor caído → instrucciones visibles, botón deshabilitado");
      await pf.close();
      proc = await servidor();
    } else console.log("servidor caído: omitido (ya había un generador activo en 127.0.0.1:8765)");
    // 2. servidor activo
    const page = await ctx.newPage(); watch(page);
    await page.goto(`${BASE}/${htmlName}#planos`);
    await page.waitForSelector('#genEstado[data-srv="activo"]', { timeout: 15000 });
    await page.click("#bReset"); await settle(page);
    assert.equal(await page.isEnabled("#bGen"), true, "botón Generar habilitado con el servidor activo");
    assert.match(await page.textContent("#plResKv"), /Base: acero sobre acero/);
    await page.selectOption("#altSel", "B"); await settle(page);
    assert.match(await page.textContent("#plResKv"), /UHMW/, "el resumen sigue a #altSel");
    assert.ok((await page.$$eval("#plParams tr td.form", (td) => td.map((x) => x.textContent))).includes("opt_uhmw"));
    await page.fill("#p_W_tf", "250"); await settle(page);
    assert.ok((await page.$$eval("#plParams tr td.form", (td) => td.map((x) => x.textContent))).includes("W_tf"), "W_tf en los parámetros que se enviarán");
    await page.click("#bReset"); await settle(page);
    assert.match(await page.textContent("#plResumen"), /Todos los parámetros están en su valor por defecto/);
    console.log("servidor activo → botón habilitado; resumen de alternativa y parámetros OK");
    // 3. historial
    await page.waitForFunction(() => !/Leyendo salidas/.test(document.querySelector("#plHist").textContent));
    const hist = await page.$$eval("#plHistTab tr[data-id]", (trs) => trs.map((tr) => tr.dataset.id)).catch(() => []);
    if (hist.length) {
      await page.click(`#plHistTab button[data-abrir="${hist[0]}"]`);
      await page.waitForSelector(`#plVer[data-id="${hist[0]}"]`, { timeout: 60000 });
      const r = await juego(page, ctx.request, "#plVer");
      console.log(`historial: ${hist.length} generación(es); «Abrir» ${hist[0]} → láminas por grupo ${r.laminas.join("/")}, ${r.enlaces} enlaces servidos`);
      if (!GENERAR) await shot(page, "panel_planos_historial.png");
    } else console.log("historial: vacío");
    // 4. generación real del caso por defecto
    if (GENERAR) {
      const t0 = Date.now();
      await page.click("#bGen");
      await page.waitForSelector('#genJob[data-estado="en_curso"]', { timeout: 30000 });
      assert.equal(await page.isEnabled("#bGen"), false, "botón deshabilitado durante la generación");
      await page.waitForFunction(() => /Dibujando/.test((document.querySelector("#genFase") || {}).textContent || ""), null, { timeout: 900000 });
      await page.waitForTimeout(2000);
      await shot(page, "panel_planos_generando.png");
      console.log("generando:", (await page.textContent("#genFase")).trim());
      await page.waitForFunction(() => { const j = document.querySelector("#genJob"); return j && j.dataset.estado !== "en_curso"; }, null, { timeout: 1800000, polling: 2000 });
      const est = await page.getAttribute("#genJob", "data-estado");
      if (est !== "listo") console.error(await page.textContent("#plGen"));
      assert.equal(est, "listo", "la generación termina sin error");
      const id = await page.getAttribute("#plVer", "data-id");
      const r = await juego(page, ctx.request, "#plVer");
      assert.ok(r.laminas.every((n) => n > 0), "los tres grupos tienen láminas");
      await page.waitForSelector(`#plHistTab tr[data-id="${id}"]`, { timeout: 30000 });
      assert.match(await page.textContent(`#plHistTab tr[data-id="${id}"]`), /= actuales/, "la generación nueva figura en el historial con los parámetros actuales");
      assert.equal(await page.$("#plVerDif"), null, "el juego corresponde a los parámetros actuales");
      await shot(page, "panel_planos_terminado.png");
      console.log(`generado ${id} en ${((Date.now() - t0) / 1000).toFixed(0)} s → láminas por grupo ${r.laminas.join("/")}, ${r.enlaces} enlaces servidos`);
    }
    assert.deepEqual(errs, [], "errores de consola: " + errs.join(" | "));
    console.log("e2e Planos: OK · capturas en", out);
  } finally {
    await browser.close();
    if (proc) proc.kill();
  }
})().catch((e) => { console.error(e); process.exit(1); });
