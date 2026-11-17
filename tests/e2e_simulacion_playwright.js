/* Verificación de extremo a extremo de la «Simulación del movimiento» con Playwright (no forma parte de `npm test`).
   Uso: node tests/e2e_simulacion_playwright.js [directorio de salida]   (requiere `playwright` con chromium, python3 con Pillow y la herramienta construida)
   Para cada modo de accionamiento (guiado, drive_mode = 1, con la leva de reenganche por defecto; pivotado tipo KIET, drive_mode = 2) y varias
   interfaces, la simulación abre, anima N carreras y termina con θ = N·paso (±0,01°), también en sentido horario; captura empuje, retorno y
   reenganche de ambos modos; una carrera insuficiente se marca en rojo al final del empuje; «Exportar GIF» descarga un GIF89a válido
   (cabecera, más de 1 cuadro, PIL lo decodifica, bucle infinito, < 6 MB) con 2 interfaces y ambos sentidos, y la vista previa queda en el modal. */
const path = require("path"), fs = require("fs"), assert = require("node:assert/strict"), { execFileSync } = require("child_process");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const out = process.argv[2] || fs.mkdtempSync(path.join(require("os").tmpdir(), "tt300c-e2e-sim-"));
const html = "file://" + path.join(root, fs.readdirSync(root).filter((n) => /^Tornamesa_v.*\.html$/.test(n))[0]);
const N = 2;
const PYGIF = "import sys\nfrom PIL import Image\nim=Image.open(sys.argv[1]); n=im.n_frames; d=0\nfor k in range(n):\n im.seek(k); im.convert('RGB'); d+=im.info.get('duration',0)\nprint(n, im.size[0], im.size[1], d, im.info.get('loop'))";

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({ acceptDownloads: true, viewport: { width: 1300, height: 1400 } })).newPage(), errs = [];
    page.on("pageerror", (e) => errs.push(String(e))); page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
    await page.goto(html);
    await page.waitForSelector("#bSim");
    const settle = () => page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando"), null, { timeout: 60000 }).then(() => page.waitForTimeout(300));
    const cerrar = () => page.click("#bSimClose");
    const setP = async (id, v) => { await page.evaluate((id) => { const d = document.querySelector("#p_" + id).closest("details"); if (d) d.open = true; }, id); await page.fill("#p_" + id, String(v)); await settle(); };
    const hayModo2 = !!(await page.$("#p_drive_mode"));
    async function preparar(modo, v, madera) {
      await page.click("#bReset"); await settle();
      if (hayModo2) await setP("drive_mode", modo);                       // el modo por defecto es el pivotado (2): el guiado se fija explícitamente
      await page.selectOption("#altSel", v); await settle();
      if (madera) { await page.check("#p_opt_wood"); await settle(); }
      if (modo === 2 && errs.length) { console.log(`  aviso: ${errs.length} errores de consola al pasar a drive_mode = 2 FUERA de la simulación (pestañas de la herramienta): ${errs[0]}`); errs.length = 0; }
    }
    async function abrir(dir) {
      await page.click("#bSim"); await page.waitForSelector("#simDet");
      await page.selectOption("#simDir", String(dir || 1));
      await page.fill("#simN", String(N)); await page.dispatchEvent("#simN", "change");
    }
    async function correr(nombre, dir) {
      await abrir(dir); await page.selectOption("#simSpeed", "8");
      const pasoDeg = await page.evaluate(() => SIM._S.prov.pitch * 180 / Math.PI), t0 = Date.now();
      await page.click("#bSimPlay");
      await page.waitForFunction(() => document.getElementById("simBox").dataset.fin === "1", null, { timeout: 120000 });
      const th = parseFloat(await page.getAttribute("#simBox", "data-theta"));
      assert.ok(Math.abs(th - N * pasoDeg) <= 0.01, `${nombre}: θ final ${th}° ≠ ${N}·${pasoDeg}°`);
      console.log(`${nombre}${dir < 0 ? " (horario)" : ""}: ${N} carreras en ${((Date.now() - t0) / 1000).toFixed(1)} s a ×8 → θ = ${th.toFixed(4)}° (paso ${pasoDeg.toFixed(4)}°)`);
    }
    async function fases(modo) {
      for (const f of modo === 2 ? ["toma", "empuje", "retorno"] : ["empuje", "retorno", "reenganche"]) {   // modo 2: toma → empuje → retorno (reenganche como subfase del retorno)
        const t = await page.evaluate((f) => SIM.seek(SIM.buscarFase(f)), f);
        assert.equal(await page.getAttribute("#simBox", "data-fase"), f, "fase " + f + " en t = " + t);
        await page.locator("#simBox").screenshot({ path: path.join(out, `sim_${modo === 2 ? "pivotado" : "guiado"}_${f}.png`) });
      }
      console.log(`capturas: ${modo === 2 ? "toma, empuje y retorno (pivotado)" : "empuje, retorno y reenganche (guiado)"}`);
    }
    async function gif(etq, dir) {
      await abrir(dir);
      const t0 = Date.now();
      const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 300000 }), page.click("#bSimGif")]);
      const f = path.join(out, `${dir < 0 ? "horario_" : ""}${dl.suggestedFilename()}`); await dl.saveAs(f);
      const buf = fs.readFileSync(f);
      assert.equal(buf.subarray(0, 6).toString("latin1"), "GIF89a", "cabecera GIF89a");
      assert.match(dl.suggestedFilename(), /^TT300-C_simulacion_(guiado|pivotado)_[A-Za-z0-9_]+\.gif$/);
      const py = execFileSync("python3", ["-c", PYGIF, f]).toString().trim().split(" ").map(Number);
      assert.ok(py[0] > 1, "más de 1 cuadro"); assert.equal(py[1], 900); assert.equal(py[4], 0, "bucle infinito (NETSCAPE)");
      assert.ok(buf.length < 6 * 1048576, "menos de 6 MB para 2 carreras");
      assert.ok(await page.isVisible("#simGifPrev"), "vista previa en el modal");
      console.log(`GIF ${etq}${dir < 0 ? " horario" : ""}: ${dl.suggestedFilename()} · ${py[0]} cuadros (PIL), ${py[1]}×${py[2]} px, ${(buf.length / 1048576).toFixed(2)} MB, ${(py[3] / 1000).toFixed(1)} s de animación; generado en ${((Date.now() - t0) / 1000).toFixed(1)} s`);
    }

    // ---- modo guiado: 4 interfaces + madera, ambos sentidos, fases, carrera insuficiente
    for (const v of ["0", "A", "B", "C1"]) {
      await preparar(1, v);
      await correr("guiado · " + v);
      if (v === "0") await fases(1);
      if (v === "A") { await cerrar(); await correr("guiado · A", -1); }
      await cerrar();
    }
    await preparar(1, "0", true); await correr("guiado · madera"); await cerrar();
    await page.click("#bReset"); await settle();
    if (hayModo2) await setP("drive_mode", 1);
    const sReq = await page.evaluate(() => { const P = Object.assign(TT.defaults(), { drive_mode: 1 }); return SIM.proveedor(P, TT.analyze(P, { noFEA: true })).sUse; });
    await setP("stroke", Math.floor(sReq - 30));
    await page.click("#bSim"); await page.waitForSelector("#simDet");
    await page.evaluate(() => SIM.seek(SIM._S.prov.tExt - 1e-6));
    await page.waitForSelector("#simAlerta");
    assert.match(await page.textContent("#simAlerta"), /Carrera requerida/);
    assert.ok(await page.evaluate(() => SIM._S.prov.dTh < SIM._S.prov.pitch - 1e-6), "con carrera insuficiente la mesa no completa el paso");
    await page.locator("#simBox").screenshot({ path: path.join(out, "sim_guiado_carrera_insuficiente.png") });
    console.log("carrera insuficiente → marcada en rojo al final del empuje");
    await cerrar();
    // GIF del modo guiado: 2 interfaces × 2 sentidos
    for (const [v, dir] of [["0", 1], ["0", -1], ["B", 1], ["B", -1]]) {
      await preparar(1, v); await gif("guiado " + (v === "0" ? "base" : v), dir);
      if (v === "B" && dir > 0) { await page.$eval("#simGif", (e) => e.scrollIntoView()); await page.locator("#simBox").screenshot({ path: path.join(out, "sim_gif_vista_previa.png") }); }
      await cerrar();
    }
    assert.deepEqual(errs, [], "errores de consola (modo guiado): " + errs.join(" | "));

    // ---- modo pivotado tipo KIET (drive_mode = 2)
    if (hayModo2) {
      for (const v of ["0", "A", "C1"]) {
        await preparar(2, v);
        await correr("pivotado · " + v);
        if (v === "0") {
          await fases(2);
          const placas = await page.$$eval("#simPlan path.sim-cam", (ps) => ps.length);
          assert.equal(placas, 4, "las 4 placas-guía curvas en planta (trayectos con arcos)");
          await cerrar(); await correr("pivotado · base", -1);
        }
        await cerrar();
      }
      await preparar(2, "0", true); await correr("pivotado · madera"); await cerrar();
      await preparar(2, "0"); await gif("pivotado base", 1); await cerrar();
      await preparar(2, "A"); await gif("pivotado A", -1); await cerrar();
      assert.deepEqual(errs, [], "errores de consola (simulación del modo pivotado): " + errs.join(" | "));
    } else console.log("modo pivotado: el núcleo aún no tiene drive_mode");
    console.log("e2e Simulación: OK · capturas en", out);
  } finally { await browser.close(); }
})().catch((e) => { console.error(e); process.exit(1); });
