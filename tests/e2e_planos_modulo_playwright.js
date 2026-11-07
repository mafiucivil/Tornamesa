/* Verificación de extremo a extremo de la pestaña «Planos» con Playwright (no forma parte de `npm test`).
   Uso: node tests/e2e_planos_modulo_playwright.js [directorio de salida]
   Requiere `playwright` con chromium, python3 y la herramienta construida (python3 tools/build_tt300c.py).
   Levanta tools/servidor_planos.py en 127.0.0.1:8765 (si no está ya activo) y comprueba:
     1. la herramienta abierta a través del servidor;
     2. en cada opción de #altSel (y en W = madera, AF2 = A con discos pegados), el juego pre-generado correcto y que todos los enlaces
        del panel apunten a archivos existentes (y que el servidor los entregue);
     3. que cambiar la carga muestre «no corresponden» y la lista de diferencias;
     4. que el ping del servidor active el botón «Generar planos con los parámetros actuales» (también con la página abierta como file://).
   No pulsa «Generar» (tarda varios minutos). */
const path = require("path"), fs = require("fs"), assert = require("node:assert/strict"), { spawn } = require("child_process");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const out = process.argv[2] || fs.mkdtempSync(path.join(require("os").tmpdir(), "tt300c-e2e-planos-"));
const htmlName = fs.readdirSync(root).filter((n) => /^Tornamesa_v.*\.html$/.test(n))[0];
const BASE = "http://127.0.0.1:8765";
const CARPETA = { 0: "entregables/RevC", A: "entregables/RevC/variantes/A", AF2: "entregables/RevC/variantes/AF2", B: "entregables/RevC/variantes/B",
  C1: "entregables/RevC/variantes/C1", C2: "entregables/RevC/variantes/C2", C3: "entregables/RevC/variantes/C3", W: "entregables/RevC/variantes/W" };
const ping = () => fetch(BASE + "/api/ping").then((r) => r.ok).catch(() => false);

async function servidor() {
  if (await ping()) return null;
  const py = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");
  const p = spawn(py, [path.join(root, "tools", "servidor_planos.py"), "--no-abrir"], { cwd: root, stdio: "ignore" });
  for (let i = 0; i < 120; i++) { if (await ping()) return p; await new Promise((r) => setTimeout(r, 500)); }
  p.kill(); throw new Error("el servidor de planos no respondió en 60 s");
}
const settle = (page) => page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando"), null, { timeout: 60000 }).then(() => page.waitForTimeout(300));

async function enlaces(page, req, juego) {
  const hrefs = await page.$$eval("#plJuego a[href]", (as) => as.map((a) => a.getAttribute("href")));
  assert.ok(hrefs.length > 10, juego + ": pocos enlaces");
  const grupos = await page.$$eval("#plJuego a[data-pdf]", (as) => as.map((a) => a.dataset.pdf));
  assert.deepEqual(grupos, ["generales", "fabricacion", "armado"], juego + ": PDF de los tres grupos");
  for (const h of hrefs) {
    const rel = decodeURIComponent(h);
    assert.ok(rel.startsWith(CARPETA[juego] + "/"), `${juego}: enlace fuera de su carpeta: ${rel}`);
    assert.ok(fs.existsSync(path.join(root, rel)), `${juego}: no existe ${rel}`);
  }
  for (const h of hrefs.filter((x) => /_Planos_(Generales|Fabricacion|Armado)_Rev/.test(x))) {
    const r = await req.head(BASE + "/" + h); assert.equal(r.status(), 200, "el servidor entrega " + h);
  }
  return hrefs.length;
}

(async () => {
  const proc = await servidor();
  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext({ viewport: { width: 1500, height: 1100 } });
    const page = await ctx.newPage(), errs = [];
    page.on("pageerror", (e) => errs.push(String(e))); page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
    // 1. abrir la herramienta vía el servidor
    await page.goto(`${BASE}/${htmlName}#planos`);
    await page.waitForSelector("#plJuego[data-estado]");
    await page.click("#bReset"); await settle(page);
    // 4. el ping activa el botón de generar
    await page.waitForSelector('#genEstado[data-srv="activo"]', { timeout: 15000 });
    assert.equal(await page.isEnabled("#bGen"), true, "botón Generar habilitado con el servidor activo");
    assert.match(await page.textContent("#bGen"), /Generar planos con los parámetros actuales/);
    assert.match(await page.textContent("#plAdv"), /ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO\./);
    // 2. cada opción del selector → su juego
    const opts = await page.$$eval("#altSel option", (os) => os.map((o) => o.value));
    assert.deepEqual(opts, ["0", "A", "B", "C1", "C2", "C3"]);
    for (const v of opts) {
      await page.selectOption("#altSel", v); await settle(page);
      assert.equal(await page.getAttribute("#plJuego", "data-estado"), "coincide", v + ": debe coincidir con un juego pre-generado");
      assert.equal(await page.getAttribute("#plJuego", "data-juego"), v, v + ": juego mostrado");
      const n = await enlaces(page, ctx.request, v);
      console.log(`altSel ${v} → ${CARPETA[v]} · ${n} enlaces OK`);
      if (v === "0" || v === "C2") await page.locator('section[data-t="planos"]').screenshot({ path: path.join(out, `panel_planos_${v === "0" ? "base" : v}.png`) });
    }
    // W (cubierta de madera) y AF2 (A con discos pegados)
    await page.selectOption("#altSel", "0"); await settle(page);
    await page.check("#p_opt_wood"); await settle(page);
    assert.equal(await page.getAttribute("#plJuego", "data-juego"), "W"); console.log(`madera → ${CARPETA.W} · ${await enlaces(page, ctx.request, "W")} enlaces OK`);
    await page.uncheck("#p_opt_wood"); await page.selectOption("#altSel", "A"); await settle(page);
    await page.fill("#p_fix_mode", "2"); await settle(page);
    assert.equal(await page.getAttribute("#plJuego", "data-juego"), "AF2"); console.log(`A + fijación pegada → ${CARPETA.AF2} · ${await enlaces(page, ctx.request, "AF2")} enlaces OK`);
    // 3. cambiar la carga → no corresponden + diferencias
    await page.click("#bReset"); await settle(page);
    assert.equal(await page.getAttribute("#plJuego", "data-juego"), "0");
    await page.fill("#p_W_tf", "250"); await settle(page);
    assert.equal(await page.getAttribute("#plJuego", "data-estado"), "no-coincide");
    const txt = await page.textContent("#plJuego");
    assert.match(txt, /no corresponden a los parámetros actuales/);
    const filas = await page.$$eval("#plDif tr", (trs) => trs.slice(1).map((tr) => [...tr.cells].map((c) => c.textContent.trim())));
    assert.deepEqual(filas.map((f) => f[0]), ["W_tf"], "única diferencia: W_tf");
    assert.equal(filas[0][2], "250"); assert.equal(filas[0][3], "300"); assert.match(filas[0][1], /Capacidad nominal/);
    assert.equal(await page.getAttribute("#plJuego", "data-cercano"), "0");
    await page.screenshot({ path: path.join(out, "panel_planos_no_coincide.png"), fullPage: false });
    console.log("carga 250 tf → «no corresponden», diferencias:", JSON.stringify(filas));
    // las láminas esquemáticas siguen disponibles, rotuladas como esquemas rápidos
    assert.match(await page.textContent('section[data-t="planos"]'), /Esquemas rápidos \(no son planos de fabricación\)/);
    await page.click("#bReset"); await settle(page);
    // 4 bis. página abierta como archivo (origen null): el ping CORS también activa el botón
    const pf = await ctx.newPage();
    pf.on("pageerror", (e) => errs.push(String(e)));
    await pf.goto("file://" + path.join(root, htmlName) + "#planos");
    await pf.waitForSelector('#genEstado[data-srv="activo"]', { timeout: 15000 });
    assert.equal(await pf.isEnabled("#bGen"), true, "file:// → botón Generar habilitado");
    assert.equal(await pf.getAttribute("#plJuego", "data-juego"), "0");
    console.log("file:// → ping CORS OK, botón Generar habilitado");
    // sin servidor → instrucción de una línea
    if (proc) {
      proc.kill(); for (let i = 0; i < 40 && (await ping()); i++) await new Promise((r) => setTimeout(r, 250));
      await pf.reload(); await pf.waitForSelector('#genEstado[data-srv="inactivo"]', { timeout: 15000 });
      assert.match(await pf.textContent("#genEstado"), /Ejecuta Generar_planos_Tornamesa\.bat \(requiere instalar una vez con Instalar_generador_planos\.bat\)/);
      console.log("sin servidor → instrucción del .bat OK");
    }
    assert.deepEqual(errs, [], "errores de consola: " + errs.join(" | "));
    console.log("e2e Planos: OK · capturas en", out);
  } finally {
    await browser.close();
    if (proc) proc.kill();
  }
})().catch((e) => { console.error(e); process.exit(1); });
