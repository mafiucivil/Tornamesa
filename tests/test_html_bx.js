/* Prueba rápida (< 120 s) de Tornamesa_BX_v1.0.html con Playwright (Chromium).
   · Carga < 3 s y sin tareas largas > 2 s en el hilo principal.
   · Todas las pestañas en tema claro y oscuro sin errores de consola (salvo ERR_CONNECTION_REFUSED del generador local 127.0.0.1:8765).
   · Valores por defecto = BX.analyze en Node (espesores del disco y del portador, n° de pastillas, estado global y FU de las filas BX).
   · Cambiar un parámetro recalcula (worker) y coincide con Node.
   · El JSON de diseño (descarga directa y POST al generador simulado) trae el bloque «bx» igual al de tools/export_design_bx.js
     (en Node se arma con PLANOS_BX.finish, la misma función que usa ese exportador; el resto del JSON lo arma el worker con
     planos_export.js y tarda: se pide al comienzo y se espera al final).
   Uso: node tests/test_html_bx.js  (requiere haber corrido python3 tools/build_tt300bx.py) */
const path = require("path"), fs = require("fs");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const HTML = path.join(root, "Tornamesa_BX_v1.0.html");
const BX = require("../packages/core/tt300bx.js"), PBX = require("../packages/web/planos_export_bx.js");
const T0 = Date.now();
let nOk = 0, nFail = 0;
const ok = (c, m) => { if (c) { nOk++; console.log("  ok  " + m); } else { nFail++; console.log("  FALLA " + m); } };
const fu3 = (v) => (v == null || !isFinite(v)) ? "—" : v.toLocaleString("es-CL", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
const fmt = (v, sig) => { if (v == null || !isFinite(v)) return "—"; sig = sig || 3; const a = Math.abs(v); const d = a >= 1000 ? 0 : a === 0 ? 0 : Math.max(0, Math.min(3, sig - 1 - Math.floor(Math.log10(a)))); return v.toLocaleString("es-CL", { minimumFractionDigits: d, maximumFractionDigits: d }); };
const TABS = ["resumen", "modelo", "giro", "cinem", "comp", "verif", "fea", "bx", "masa", "planos", "temp", "agentes"];
function diffKeys(a, b, p, out) {
  if (out.length > 10) return out;
  if (typeof a !== typeof b || (a && b && typeof a === "object") !== (a && b && typeof b === "object")) { out.push(p); return out; }
  if (a && typeof a === "object") { for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) diffKeys(a[k], b[k], p + "." + k, out); return out; }
  if (a !== b && !(typeof a === "number" && Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a)))) out.push(p);
  return out;
}

(async () => {
  if (!fs.existsSync(HTML)) { console.log("Falta " + HTML + ": ejecute python3 tools/build_tt300bx.py"); process.exit(2); }
  const P0 = Object.assign(BX.defaults(), { opt_uhmw: 1, opt_ss: 0, opt_bz: 0 });
  const A0 = BX.analyze(P0, { noFEA: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ acceptDownloads: true, colorScheme: "light" });
  const page = await ctx.newPage();
  const errs = [];
  page.on("console", (m) => { if (m.type() === "error" && !/ERR_CONNECTION_REFUSED/.test(m.text())) errs.push(m.text()); });
  page.on("pageerror", (e) => errs.push("pageerror: " + e.message));
  await page.addInitScript(() => { window.__lt = []; try { new PerformanceObserver((l) => l.getEntries().forEach((e) => window.__lt.push(e.duration))).observe({ type: "longtask", buffered: true }); } catch (e) { } });
  // generador local simulado: captura el POST de /api/generar
  let posted = null;
  await page.route("http://127.0.0.1:8765/**", (route) => {
    const u = route.request().url();
    if (/\/api\/ping/.test(u)) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ servidor: "simulado", python: "3.12" }) });
    if (/\/api\/listar/.test(u)) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ salidas: [] }) });
    if (/\/api\/generar/.test(u)) { posted = route.request().postData(); return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "simulado", estado: "listo", progreso: 1, log: [] }) }); }
    if (/\/api\/estado/.test(u)) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "simulado", estado: "listo", progreso: 1, log: [] }) });
    return route.abort();
  });

  console.log("1 · Carga");
  const t0 = Date.now();
  await page.goto("file://" + HTML);
  await page.waitForSelector("#bxBadge", { timeout: 15000 });
  const tLoad = Date.now() - t0;
  ok(tLoad < 3000, `carga hasta badges con resultados: ${tLoad} ms (< 3000)`);
  await page.waitForTimeout(500);
  const lt = await page.evaluate(() => window.__lt.slice());
  ok(Math.max(0, ...lt) < 2000, `tarea larga máxima en la carga: ${Math.round(Math.max(0, ...lt))} ms (< 2000)`);

  console.log("2 · Valores por defecto frente a BX.analyze (Node)");
  const badge = await page.$eval("#bxBadge", (e) => e.textContent);
  ok(badge.includes("disco " + fmt(A0.bx.disco.t) + " mm"), `disco t = ${fmt(A0.bx.disco.t)} mm en el badge («${badge}»)`);
  ok(badge.includes(A0.bx.pastillas.n + " pastillas"), `${A0.bx.pastillas.n} pastillas en el badge`);
  ok(badge.includes("portador " + fmt(A0.bx.portador.t) + " mm"), `portador t = ${fmt(A0.bx.portador.t)} mm en el badge`);
  const eg = await page.$eval("#estadoGlobal", (e) => e.textContent);
  ok(eg.includes(A0.verdict.estado_global), `estado global «${A0.verdict.estado_global}»`);
  await page.click('#tabs button[data-t="verif"]');
  const rowsUI = await page.$$eval("tr.chk-row", (rs) => rs.map((r) => [r.children[1].firstChild.textContent, r.children[5].firstChild.textContent]));
  const bxN = A0.checks.filter((c) => c.bx);
  let mism = 0;
  bxN.forEach((c) => { const r = rowsUI.find((x) => x[0] === c.name); if (!r || r[1] !== fu3(c.fu)) mism++; });
  ok(bxN.length > 0 && mism === 0, `FU de las ${bxN.length} filas BX iguales a Node (${mism} distintas)`);
  const nFull = BX.analyze(P0).checks.length;                            // con FEA, como la página
  ok(rowsUI.length === nFull, `n° de verificaciones ${rowsUI.length} = ${nFull} (BX.analyze con FEA)`);

  // el JSON de diseño se pide ya (el worker lo arma mientras se recorren las pestañas)
  await page.click('#tabs button[data-t="planos"]');
  if (!(await page.$eval("#pkgChk", (e) => e.checked))) await page.click("#pkgChk");
  const pDl = page.waitForEvent("download", { timeout: 600000 });
  await page.click("#bPkgJson");

  console.log("3 · Pestañas en tema claro y oscuro");
  for (const theme of ["light", "dark"]) {
    if (theme === "dark") await page.click("#bTheme");
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    let empty = [];
    for (const t of TABS) {
      await page.click(`#tabs button[data-t="${t}"]`);
      await page.waitForTimeout(150);
      const txt = await page.$eval(`section[data-t="${t}"]`, (e) => e.innerText.trim());
      if (txt.length < 40) empty.push(t);
    }
    ok(empty.length === 0, `tema ${theme} (fondo ${bg}): ${TABS.length} pestañas con contenido${empty.length ? " · vacías: " + empty.join(", ") : ""}`);
  }
  await page.click('#tabs button[data-t="bx"]');
  ok(await page.$$eval("#bxPlan .bxPuck", (e) => e.length) === A0.bx.pastillas.n, "planta BX: una figura por pastilla");
  ok(await page.$$eval("#bxFab tr[data-estado]", (e) => e.length) === A0.bx.fabricacion.length, `fabricación antes → después: ${A0.bx.fabricacion.length} filas`);

  console.log("4 · Exportación del JSON de diseño (bloque «bx»)");
  await page.click('#tabs button[data-t="planos"]');
  const dl = await pDl;
  const J = JSON.parse(fs.readFileSync(await dl.path(), "utf8"));
  await page.waitForSelector("#bGen:not([disabled])", { timeout: 15000 });
  await page.click("#bGen");
  for (let i = 0; i < 100 && !posted; i++) await page.waitForTimeout(200);
  const N = { bx: PBX.finish({}, P0, BX, A0).bx, P: P0 };
  ok(J.proyecto === "TT300-BX" && J.bx && J.bx.disco, "JSON descargado con proyecto TT300-BX y bloque «bx»");
  const dk = diffKeys(J.bx, N.bx, "bx", []);
  ok(dk.length === 0, `bloque «bx» descargado = tools/export_design_bx.js${dk.length ? " · difiere en " + dk.join(", ") : ""}`);
  const Jp = posted ? JSON.parse(posted) : null;
  const dk2 = Jp ? diffKeys(Jp.bx, N.bx, "bx", []) : ["sin POST"];
  ok(dk2.length === 0, `POST a /api/generar con el bloque «bx» igual${dk2.length ? " · " + dk2.join(", ") : ""}`);
  const dkP = diffKeys(J.P, Object.assign(BX.defaults(), P0), "P", []);
  ok(dkP.length === 0, `P del JSON = P de Node${dkP.length ? " · " + dkP.join(", ") : ""}`);

  console.log("5 · Cambiar un parámetro recalcula");
  await page.click('#tabs button[data-t="resumen"]');
  const Pc = Object.assign({}, P0, { bx_tc: 30 });
  const pN = new Promise((res) => setImmediate(() => res(BX.analyze(Pc, { noFEA: true }))));
  await page.fill("#p_bx_tc", "30");
  await page.waitForFunction(() => { const b = document.querySelector("#bxBadge"); return b && /portador 30,0 mm/.test(b.textContent) && !document.querySelector("#calcBadge"); }, null, { timeout: 60000 });
  const A1 = await pN;
  const badge1 = await page.$eval("#bxBadge", (e) => e.textContent);
  ok(badge1.includes(A1.bx.pastillas.n + " pastillas") && badge1.includes("disco " + fmt(A1.bx.disco.t) + " mm"), `recalculado con bx_tc = 30: «${badge1}» (Node: ${A1.bx.pastillas.n} pastillas, disco ${fmt(A1.bx.disco.t)})`);
  const lt2 = await page.evaluate(() => window.__lt.slice());
  ok(Math.max(0, ...lt2) < 2000, `tarea larga máxima en toda la sesión: ${Math.round(Math.max(0, ...lt2))} ms`);
  ok(errs.length === 0, `sin errores de consola${errs.length ? ": " + errs.slice(0, 3).join(" | ") : ""}`);
  await browser.close();
  console.log(`\n${nOk} ok, ${nFail} fallas · ${((Date.now() - T0) / 1000).toFixed(1)} s`);
  process.exit(nFail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
