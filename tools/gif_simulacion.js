/* GIF de la simulación del movimiento desde la línea de comando, con el MISMO codificador GIF89a de la herramienta (SIM.exportGif).
   Abre Tornamesa_v<versión>.html con Playwright (chromium sin ventana), aplica la alternativa y los parámetros, y descarga el GIF.

   Uso: node tools/gif_simulacion.js [opciones]
     --alt ID           0 (base, por defecto), A, AF2 (A con discos pegados), B, C1, C2, C3; agregue W para la cubierta de madera (p. ej. --alt B,W)
     --sentido S        antihorario (por defecto) u horario
     --carreras N       número de carreras (por defecto 2)
     --velocidad V      0.25, 0.5, 1 (por defecto), 2, 4 u 8; la duración de cada cuadro es el tiempo real dividido por V
     --friccion F       nom (por defecto) o dis
     --param k=v        cualquier parámetro del formulario (repetible), p. ej. --param W_tf=250
     --salida RUTA      archivo .gif o carpeta (por defecto la carpeta actual, con el nombre TT300-C_simulacion_<alternativa>.gif)
   Requiere: npm install playwright (con chromium) y la herramienta construida (python3 tools/build_tt300c.py). */
const path = require("path"), fs = require("fs");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");

function args(argv) {
  const o = { alt: "0", sentido: "antihorario", carreras: 2, velocidad: 1, friccion: "nom", param: [], salida: process.cwd() };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i], v = argv[i + 1];
    if (a === "--alt") { o.alt = v; i++; } else if (a === "--sentido") { o.sentido = v; i++; } else if (a === "--carreras") { o.carreras = parseInt(v, 10); i++; }
    else if (a === "--velocidad") { o.velocidad = parseFloat(v); i++; } else if (a === "--friccion") { o.friccion = v; i++; } else if (a === "--param") { o.param.push(v); i++; }
    else if (a === "--salida") { o.salida = v; i++; } else if (a === "-h" || a === "--help") { console.log(fs.readFileSync(__filename, "utf8").split("*/")[0]); process.exit(0); }
    else throw new Error("opción desconocida: " + a);
  }
  if (!["antihorario", "horario"].includes(o.sentido)) throw new Error("--sentido debe ser antihorario u horario");
  if (![0.25, 0.5, 1, 2, 4, 8].includes(o.velocidad)) throw new Error("--velocidad debe ser 0.25, 0.5, 1, 2, 4 u 8");
  return o;
}

(async () => {
  const o = args(process.argv.slice(2));
  const html = fs.readdirSync(root).filter((n) => /^Tornamesa_v.*\.html$/.test(n))[0];
  if (!html) throw new Error("no hay Tornamesa_v*.html en la raíz: ejecute python3 tools/build_tt300c.py");
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({ acceptDownloads: true, viewport: { width: 1300, height: 1400 } })).newPage();
    const errs = []; page.on("pageerror", (e) => errs.push(String(e)));
    await page.goto("file://" + path.join(root, html));
    await page.waitForSelector("#bSim");
    const settle = () => page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando"), null, { timeout: 60000 }).then(() => page.waitForTimeout(200));
    const setP = async (id, v) => {
      const ok = await page.evaluate((id) => { const e = document.querySelector("#p_" + id); if (!e) return false; const d = e.closest("details"); if (d) d.open = true; return true; }, id);
      if (!ok) throw new Error("parámetro desconocido: " + id);
      if (await page.getAttribute("#p_" + id, "type") === "checkbox") { if (parseFloat(v) > 0.5) await page.check("#p_" + id); else await page.uncheck("#p_" + id); }
      else await page.fill("#p_" + id, String(v));
      await settle();
    };
    await page.click("#bReset"); await settle();
    const ids = o.alt.split(/[,+]/).map((s) => s.trim().toUpperCase()).filter(Boolean);
    const base = ids.find((x) => x !== "W") || "0";
    await page.selectOption("#altSel", base === "AF2" ? "A" : base); await settle();
    if (base === "AF2") await setP("fix_mode", 2);
    if (ids.includes("W")) await setP("opt_wood", 1);
    for (const kv of o.param) { const [k, v] = kv.split("="); await setP(k, v); }
    await page.click("#bSim"); await page.waitForSelector("#simDet, #simPend");
    if (await page.$("#simPend")) throw new Error((await page.textContent("#simPend")).trim());
    await page.selectOption("#simDir", o.sentido === "horario" ? "-1" : "1");
    await page.selectOption("#simSpeed", String(o.velocidad));
    await page.selectOption("#simCaso", o.friccion);
    await page.fill("#simN", String(o.carreras)); await page.dispatchEvent("#simN", "change");
    const t0 = Date.now();
    const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 600000 }), page.click("#bSimGif")]);
    const dest = fs.existsSync(o.salida) && fs.statSync(o.salida).isDirectory() ? path.join(o.salida, dl.suggestedFilename()) : o.salida;
    await dl.saveAs(dest);
    console.log(`${dest}: ${(await page.textContent("#simGifOk")).replace(/^GIF listo: /, "").split(" · ")[0]} (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
    if (errs.length) console.error("avisos de la página:", errs.join(" | "));
  } finally { await browser.close(); }
})().catch((e) => { console.error("Error:", e.message); process.exit(1); });
