/* Verificación de extremo a extremo de la «Simulación del movimiento» con Playwright (no forma parte de `npm test`).
   Uso: node tests/e2e_simulacion_playwright.js [directorio de salida]   (requiere `playwright` con chromium y la herramienta construida)
   Comprueba, para el modo guiado y varias interfaces (Base, A, B, C1 y cubierta de madera), que la simulación abre, anima N carreras
   y termina con θ = N·paso (±0,01°), en ambos sentidos de giro; que una carrera insuficiente se marca en rojo al final del empuje;
   y captura las fases de empuje, retorno y reenganche. El modo pivotado (drive_mode = 2) se prueba cuando el núcleo entregue su
   geometría; mientras tanto se comprueba que la simulación lo declara pendiente en vez de dibujar una cinemática inventada.
   «Exportar GIF»: con 2 interfaces y ambos sentidos, el botón descarga un GIF89a válido con más de 1 cuadro que PIL (Python) decodifica,
   y la vista previa queda en el modal (captura sim_gif_vista_previa.png). */
const path = require("path"), fs = require("fs"), assert = require("node:assert/strict"), { execFileSync } = require("child_process");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const out = process.argv[2] || fs.mkdtempSync(path.join(require("os").tmpdir(), "tt300c-e2e-sim-"));
const html = "file://" + path.join(root, fs.readdirSync(root).filter((n) => /^Tornamesa_v.*\.html$/.test(n))[0]);
const N = 2;

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({ acceptDownloads: true, viewport: { width: 1300, height: 1350 } })).newPage(), errs = [];
    page.on("pageerror", (e) => errs.push(String(e))); page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
    await page.goto(html);
    await page.waitForSelector("#bSim");
    const settle = () => page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando"), null, { timeout: 60000 }).then(() => page.waitForTimeout(300));
    const cerrar = () => page.click("#bSimClose");
    const setP = async (id, v) => { await page.evaluate((id) => { const d = document.querySelector("#p_" + id).closest("details"); if (d) d.open = true; }, id); await page.fill("#p_" + id, String(v)); await settle(); };
    async function correr(nombre, dir) {
      await page.click("#bSim"); await page.waitForSelector("#simDet");
      await page.selectOption("#simDir", String(dir || 1));
      await page.selectOption("#simSpeed", "8");
      await page.fill("#simN", String(N)); await page.dispatchEvent("#simN", "change");
      const pasoDeg = await page.evaluate(() => SIM._S.prov.pitch * 180 / Math.PI);
      const t0 = Date.now();
      await page.click("#bSimPlay");
      await page.waitForFunction(() => document.getElementById("simBox").dataset.fin === "1", null, { timeout: 120000 });
      const th = parseFloat(await page.getAttribute("#simBox", "data-theta"));
      assert.ok(Math.abs(th - N * pasoDeg) <= 0.01, `${nombre}: θ final ${th}° ≠ ${N}·${pasoDeg}°`);
      console.log(`${nombre}${dir < 0 ? " (horario)" : ""}: ${N} carreras en ${((Date.now() - t0) / 1000).toFixed(1)} s a ×8 → θ = ${th.toFixed(4)}° (paso ${pasoDeg.toFixed(4)}°)`);
    }
    // modo guiado, varias interfaces
    for (const v of ["0", "A", "B", "C1"]) {
      await page.click("#bReset"); await settle();
      await page.selectOption("#altSel", v); await settle();
      await correr("guiado · " + v);
      if (v === "0") {
        for (const f of ["empuje", "retorno", "reenganche"]) {
          const t = await page.evaluate((f) => SIM.seek(SIM.buscarFase(f)), f);
          assert.equal(await page.getAttribute("#simBox", "data-fase"), f, "fase " + f + " en t = " + t);
          await page.locator("#simBox").screenshot({ path: path.join(out, `sim_guiado_${f}.png`) });
        }
        console.log("capturas: empuje, retorno y reenganche (modo guiado)");
      }
      if (v === "A") { await cerrar(); await correr("guiado · A", -1); }
      await cerrar();
    }
    await page.click("#bReset"); await settle();
    await page.check("#p_opt_wood"); await settle();
    await correr("guiado · madera"); await cerrar();
    // carrera insuficiente: el instante final del empuje se marca en rojo y la mesa no completa el paso
    await page.click("#bReset"); await settle();
    const sReq = await page.evaluate(() => SIM.proveedor(TT.defaults(), TT.analyze(TT.defaults(), { noFEA: true })).K.s_req);
    await setP("stroke", Math.floor(sReq - 30));
    await page.click("#bSim"); await page.waitForSelector("#simDet");
    await page.evaluate(() => SIM.seek(SIM._S.prov.tExt - 1e-6));
    await page.waitForSelector("#simAlerta");
    assert.match(await page.textContent("#simAlerta"), /Carrera requerida/);
    assert.ok(await page.evaluate(() => SIM._S.prov.dTh < SIM._S.prov.pitch - 1e-6), "con carrera insuficiente la mesa no completa el paso");
    await page.locator("#simBox").screenshot({ path: path.join(out, "sim_guiado_carrera_insuficiente.png") });
    console.log("carrera insuficiente → marcada en rojo al final del empuje");
    await cerrar();
    // Exportar GIF: 2 interfaces × 2 sentidos
    for (const [v, dir] of [["0", 1], ["0", -1], ["B", 1], ["B", -1]]) {
      await page.click("#bReset"); await settle();
      await page.selectOption("#altSel", v); await settle();
      await page.click("#bSim"); await page.waitForSelector("#simDet");
      await page.selectOption("#simDir", String(dir));
      await page.fill("#simN", "2"); await page.dispatchEvent("#simN", "change");
      const t0 = Date.now();
      const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 300000 }), page.click("#bSimGif")]);
      const f = path.join(out, `${dir < 0 ? "horario_" : ""}${dl.suggestedFilename()}`); await dl.saveAs(f);
      const buf = fs.readFileSync(f);
      assert.equal(buf.subarray(0, 6).toString("latin1"), "GIF89a", "cabecera GIF89a");
      assert.match(dl.suggestedFilename(), /^TT300-C_simulacion_guiado_(base|B)\.gif$/);
      const py = execFileSync("python3", ["-c", "import sys\nfrom PIL import Image\nim=Image.open(sys.argv[1]); n=im.n_frames; d=0\nfor k in range(n):\n im.seek(k); im.convert('RGB'); d+=im.info.get('duration',0)\nprint(n, im.size[0], im.size[1], d, im.info.get('loop'))", f]).toString().trim().split(" ").map(Number);
      assert.ok(py[0] > 1, "más de 1 cuadro"); assert.equal(py[1], 900); assert.equal(py[4], 0, "bucle infinito (NETSCAPE)");
      assert.ok(buf.length < 6 * 1048576, "menos de 6 MB para 2 carreras");
      assert.ok(await page.isVisible("#simGifPrev"), "vista previa en el modal");
      console.log(`GIF ${v === "0" ? "base" : v}${dir < 0 ? " horario" : ""}: ${py[0]} cuadros (PIL), ${py[1]}×${py[2]} px, ${(buf.length / 1048576).toFixed(2)} MB, ${(py[3] / 1000).toFixed(1)} s de animación; generado en ${((Date.now() - t0) / 1000).toFixed(1)} s`);
      if (v === "B" && dir > 0) { await page.$eval("#simGif", (e) => e.scrollIntoView()); await page.locator("#simBox").screenshot({ path: path.join(out, "sim_gif_vista_previa.png") }); }
      await cerrar();
    }
    assert.deepEqual(errs, [], "errores de consola (modo guiado): " + errs.join(" | "));
    // modo pivotado
    await page.click("#bReset"); await settle();
    if (await page.$("#p_drive_mode")) {
      await setP("drive_mode", 2);
      await page.click("#bSim"); await page.waitForTimeout(300);
      if (await page.$("#simPend")) {
        console.log("modo pivotado (drive_mode = 2): PENDIENTE de la geometría del núcleo (la simulación lo declara y no dibuja)");
        if (errs.length) console.log(`  aviso: ${errs.length} errores de consola con drive_mode = 2 fuera de la simulación (núcleo en desarrollo): ${errs[0]}`);
        errs.length = 0;
      }
      else { await page.waitForSelector("#simDet"); await correr("pivotado · base"); }
      await cerrar();
    } else console.log("modo pivotado: el núcleo aún no tiene drive_mode");
    assert.deepEqual(errs, [], "errores de consola: " + errs.join(" | "));
    console.log("e2e Simulación: OK · capturas en", out);
  } finally { await browser.close(); }
})().catch((e) => { console.error(e); process.exit(1); });
