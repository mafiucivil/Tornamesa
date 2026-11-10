/* Verificación de extremo a extremo de la placa-guía curva del modo pivotado tipo KIET (drive_mode = 2) en la herramienta, con Playwright
   (no forma parte de `npm test`).
   Uso: node tests/e2e_guia_curva_playwright.js [directorio de salida]   (requiere `playwright` con chromium y la herramienta construida)
   Comprueba:
     1. las 4 placas-guía se dibujan desde los segmentos del núcleo (pivotGeo().placas[k].segmentos_contorno) con arcos SVG «A»: muestreando el
        trayecto con getPointAtLength, todo punto queda a ≤ 0,1 mm de su recta o arco (radio, sentido y bandera de arco grande correctos);
     2. la simulación recorre toma → empuje → retorno (TT.pivotAt), con el contacto Q–canto en el empuje, el pasador Q, la cara R del bloque-uña,
        el ojal E, el cilindro (cuerpo y vástago) y el pasador tomado; capturas de las 3 fases a deviceScaleFactor 2;
     3. el panel «Cinemática (modo 2)»: 6 gráficos SVG con las marcas de toma, calado y fin del empuje, y la tabla de 5 puntos característicos
        con los valores de designDrive().pivotado.cinematica;
     4. la pestaña «Comparación de la guía»: tabla original / curva / KIET y figura embebida (base64) que el navegador decodifica;
     5. «Verificaciones»: todas las filas de TT.analyze(P).checks aparecen en el DOM con estado, FU con 3 decimales y norma (ninguna falta, ninguna sobra);
     6. 0 «NaN», «undefined» ni «Infinity» en el DOM (texto y atributos) en el modo 2 por defecto, el modo 1 y cada alternativa (base, A, AF2, B, C1, C2, C3),
        con todas las pestañas y la simulación en sus fases;
     7. el control opt_wood funciona y muestra el rótulo «Cubierta de madera W: en stand by (no incluida en la entrega RevC)»;
     8. veredicto global del núcleo (verdict.estado_global) en la insignia, el veredicto del resumen y la tarjeta «Estructura»; pendientes críticos
        (ins_on = 0) con FU de 3 decimales y referencia; limitaciones de uso (verdict.limitaciones_uso) en el resumen y en la simulación;
     9. inserto de esquina (designDrive().pivotado.fabricacion.soporte_E.inserto / levaGuiada.fabricacion.inserto) dibujado en la planta del Modelo
        (polígono con muescas = núcleo, rótulo de espesor), en el corte o alzado (con su espesor) y en la planta de la simulación, en los modos 1 y 2;
        lista de materiales con la plancha base de t_base mm y el inserto (espesor y masa) en la ménsula o el soporte E;
    10. las filas de verificación del núcleo frente al DOM también en el modo 1 (guiado). */
const path = require("path"), fs = require("fs"), assert = require("node:assert/strict");
const { chromium } = require("playwright");
const root = path.resolve(__dirname, "..");
const out = process.argv[2] || fs.mkdtempSync(path.join(require("os").tmpdir(), "tt300c-e2e-guia-"));
fs.mkdirSync(out, { recursive: true });
const html = "file://" + path.join(root, fs.readdirSync(root).filter((n) => /^Tornamesa_v.*\.html$/.test(n))[0]);
const ALTS = [["base", "0", {}], ["A", "A", {}], ["AF2", "A", { fix_mode: 2 }], ["B", "B", {}], ["C1", "C1", {}], ["C2", "C2", {}], ["C3", "C3", {}]];
const ABRIR = "header{position:static!important}.wrap{height:auto!important;display:block!important}aside{display:none!important}main{overflow:visible!important}";

(async () => {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({ viewport: { width: 1360, height: 1500 }, deviceScaleFactor: 2 })).newPage(), errs = [];
    page.on("pageerror", (e) => errs.push(String(e))); page.on("console", (m) => { if (m.type() === "error" && !/ERR_CONNECTION_REFUSED/.test(m.text())) errs.push(m.text()); });
    page.setDefaultTimeout(180000);                                     // pestañas que calculan en el hilo principal (Tapones, Temperatura) en una máquina cargada
    await page.goto(html, { timeout: 240000 });
    await page.waitForSelector("#bSim");
    const settle = () => page.waitForFunction(() => !document.querySelector("#busy").textContent.startsWith("Calculando"), null, { timeout: 120000 }).then(() => page.waitForTimeout(250));
    const setP = async (id, v) => {
      await page.evaluate((id) => { const d = document.querySelector("#p_" + id).closest("details"); if (d) d.open = true; }, id);
      if (await page.getAttribute("#p_" + id, "type") === "checkbox") { if (v) await page.check("#p_" + id); else await page.uncheck("#p_" + id); } else await page.fill("#p_" + id, String(v));
      await settle();
    };
    const tab = async (t) => { await page.click(`#tabs button[data-t="${t}"]`); await page.waitForTimeout(200); };
    await page.click("#bReset"); await settle();
    assert.equal(await page.evaluate(() => TT.driveMode(TT.defaults())), 2, "drive_mode = 2 por defecto");

    // ---- 7. cubierta W en stand by: rótulo visible y el control sigue funcionando
    await page.evaluate(() => { const d = document.querySelector("#p_opt_wood").closest("details"); if (d) d.open = true; });
    assert.ok(await page.isVisible("#woodStandby"), "rótulo de stand by de la cubierta W visible");
    assert.equal((await page.textContent("#woodStandby")).trim(), "Cubierta de madera W: en stand by (no incluida en la entrega RevC)");
    await setP("opt_wood", 1);
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem("tt300c-params-v1")).opt_wood), 1, "opt_wood = 1 aplicado");
    await setP("opt_wood", 0);
    console.log("cubierta W: rótulo «en stand by» visible y el control opt_wood funciona");

    // ---- 8. veredicto global, pendientes críticos y limitaciones de uso
    const fu3 = (v) => v.toLocaleString("es-CL", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
    const veredicto = async (etq) => {
      const r = await page.evaluate(() => {
        const P = JSON.parse(localStorage.getItem("tt300c-params-v1")), v = TT.analyze(P).verdict, tx = (s) => (document.querySelector(s) || { textContent: null }).textContent;
        return { v, badge: tx("#estadoGlobal"), res: tx("#estadoGlobalRes"), est: tx("#estadoGlobalEst"), lim: tx("#limUso"),
          pend: [...document.querySelectorAll("#pendCrit li")].map((li) => li.textContent), pendEst: document.querySelectorAll("#pendCritEst li").length };
      });
      const eg = r.v.estado_global;
      assert.ok(["CUMPLE", "NO CUMPLE", "NO CUMPLE / PENDIENTE DE DECISIÓN"].includes(eg), etq + ": estado_global del núcleo");
      assert.ok(r.badge && r.badge.includes("ESTADO GLOBAL: " + eg), `${etq}: insignia con el estado global (${r.badge})`);
      assert.equal((r.res || "").trim(), eg, etq + ": veredicto del resumen");
      assert.equal((r.est || "").trim(), eg, etq + ": tarjeta «Estructura»");
      assert.equal(r.pend.length, r.v.pendientes_criticos.length, etq + ": pendientes críticos listados");
      assert.equal(r.pendEst, r.v.pendientes_criticos.length, etq + ": pendientes críticos en la tarjeta «Estructura»");
      r.v.pendientes_criticos.forEach((q, i) => { assert.ok(r.pend[i].includes("FU " + fu3(q.fu)), `${etq}: FU con 3 decimales (${q.nombre})`); assert.ok(r.pend[i].includes(q.nombre) && r.pend[i].includes(q.ref), `${etq}: nombre y referencia (${q.nombre})`); });
      if (r.v.pendientes_criticos.length) assert.ok(r.badge.includes("FU pend. " + fu3(r.v.fuMaxPend)), etq + ": FU máximo de los pendientes en la insignia");
      r.v.limitaciones_uso.forEach((l) => assert.ok(r.lim && r.lim.includes("Limitación de uso: " + l.texto), `${etq}: limitación de uso visible (${l.id})`));
      if (!r.v.limitaciones_uso.length) assert.equal(r.lim, null, etq + ": sin limitaciones, sin recuadro");
      if (r.v.limitaciones_uso.length) {
        await page.click("#bSim"); await page.waitForSelector("#simDet");
        const sl = await page.textContent("#simLim");
        r.v.limitaciones_uso.forEach((l) => assert.ok(sl.includes("Limitación de uso: " + l.texto), etq + ": limitación de uso en la simulación"));
        await page.click("#bSimClose");
      }
      return r;
    };
    let vr = await veredicto("pivotado");
    assert.equal(vr.v.estado_global, "CUMPLE"); assert.equal(vr.v.limitaciones_uso.length, 1);
    console.log(`veredicto (pivotado): «${vr.v.estado_global}» en la insignia, el resumen y «Estructura»; limitación de uso «${vr.v.limitaciones_uso[0].texto}» en el resumen y la simulación`);
    await setP("ins_on", 0);
    vr = await veredicto("pivotado sin inserto");
    assert.equal(vr.v.estado_global, "NO CUMPLE / PENDIENTE DE DECISIÓN"); assert.ok(vr.v.pendientes_criticos.length >= 1);
    assert.equal(await page.$$eval(".mdl-ins, #secIns", (e) => e.length), 0, "sin inserto: no se dibuja");
    console.log(`veredicto (ins_on = 0): «${vr.v.estado_global}», ${vr.v.pendientes_criticos.length} pendiente(s) crítico(s): ${vr.v.pendientes_criticos.map((q) => "FU " + fu3(q.fu)).join(", ")}`);
    await setP("ins_on", 1);

    // ---- 9. inserto de esquina: Modelo (planta y corte), simulación y lista de materiales, en los dos modos
    const inserto = async (modo) => {
      await tab("modelo");
      const r = await page.evaluate(() => {
        const P = JSON.parse(localStorage.getItem("tt300c-params-v1")), A = TT.analyze(P, { noFEA: true }), D = TT.designDrive(P, A.R);
        const I = D.modo === 2 ? D.pivotado.fabricacion.soporte_E.inserto : D.levaGuiada.fabricacion.inserto;
        const g = [...document.querySelectorAll('section[data-t="modelo"] g.mdl-ins')];
        const pts = g.map((e) => e.querySelector("polygon").getAttribute("points").trim().split(/\s+/).map((q) => q.split(",").map(Number)));
        const dmax = Math.max(...pts.map((pp, k) => Math.max(...pp.map(([x, y], i) => Math.hypot(x - I.esquinas[k][i][0], -y - I.esquinas[k][i][1])))));
        const bom = PLANOS.buildBOM(P, A).items.filter((it) => it.sub === "BASE").map((it) => it.desc);
        return { modo: D.modo, n: I.n, t: I.t, tb: I.t_base, masa: I.masa, mt: I.masa_total, nv: I.esquinas.map((e) => e.length), ng: g.length, nvDom: pts.map((p) => p.length), dmax,
          rot: g.map((e) => e.querySelector("text").textContent), sec: !!document.querySelector("#secIns"), secT: (document.querySelector("#secInsT") || {}).textContent, ley: (document.querySelector("#mdlInsRot") || {}).textContent, bom };
      });
      const nf = (v) => String(+(+v).toFixed(1)).replace(".", ",");
      const nf1 = (v) => (+v).toFixed(1).replace(".", ",");
      assert.equal(r.modo, modo);
      assert.equal(r.ng, r.n, `modo ${modo}: ${r.n} insertos en la planta`);
      assert.deepEqual(r.nvDom, r.nv, `modo ${modo}: polígono con las muescas del núcleo (vértices)`);
      assert.ok(r.dmax < 1e-6, `modo ${modo}: vértices del inserto = núcleo (${r.dmax})`);
      r.rot.forEach((t) => assert.equal(t, "inserto t " + r.t, `modo ${modo}: rótulo de espesor`));
      assert.ok(r.sec && r.secT.startsWith(`inserto t ${r.t} sobre la base de ${r.tb}`), `modo ${modo}: inserto en el corte con su espesor (${r.secT})`);
      assert.ok(r.ley.includes(`Base t = ${r.tb} mm`) && r.ley.includes(`insertos de esquina t = ${r.t} mm`), `modo ${modo}: leyenda de la planta`);
      assert.ok(r.bom.some((d) => d.startsWith("Plancha base ") && d.includes(` x ${nf(r.tb)} mm `)), `modo ${modo}: plancha base de ${r.tb} mm en la lista de materiales`);
      assert.ok(r.bom.some((d) => /^(Ménsula|Soporte)/.test(d) && d.includes(`t = ${nf(r.t)} mm`) && d.includes(`${r.n} x ${nf1(r.masa)} kg = ${nf1(r.mt)} kg`)), `modo ${modo}: inserto (espesor y masa) en la ménsula o el soporte E: ${r.bom.join(" | ")}`);
      await page.click("#bSim"); await page.waitForSelector("#simDet");
      const ns = await page.$$eval("#simPlan polygon.sim-ins", (e) => e.length), nt = await page.$$eval("#simPlan text.sim-tins", (e) => e.map((t) => t.textContent));
      assert.equal(ns, r.n, `modo ${modo}: insertos en la planta de la simulación`);
      nt.forEach((t) => assert.equal(t, "inserto t " + r.t));
      assert.match(await page.textContent("#simIns"), new RegExp(`t ${r.tb} mm / t ${r.t} mm`));
      await page.click("#bSimClose");
      return r;
    };
    const ins2 = await inserto(2);
    console.log(`inserto (pivotado): ${ins2.n} polígonos con ${ins2.nv.join("/")} vértices = núcleo, t ${ins2.t} sobre base ${ins2.tb}, en la planta, el alzado y la simulación; lista de materiales: «${ins2.bom.find((d) => /^Soporte/.test(d))}»`);

    // ---- 1. arcos de las 4 placas: trayecto SVG frente a la geometría analítica del núcleo
    const geo = await page.evaluate(() => {
      const P = TT.defaults(), g = TT.pivotGeo(P), ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg"), res = {};
      document.body.appendChild(svg);
      const dSeg = (q, p) => {
        if (q.tipo === "arco") {
          const a = Math.atan2(p[1] - q.centro[1], p[0] - q.centro[0]), a0 = Math.atan2(q.p0[1] - q.centro[1], q.p0[0] - q.centro[0]), a1 = Math.atan2(q.p1[1] - q.centro[1], q.p1[0] - q.centro[0]);
          const ccw = q.sentido !== "horario", n = (x) => ((x % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI), sw = ccw ? n(a1 - a0) : n(a0 - a1), u = ccw ? n(a - a0) : n(a0 - a);
          if (u <= sw + 1e-9) return Math.abs(Math.hypot(p[0] - q.centro[0], p[1] - q.centro[1]) - q.radio);
          return Math.min(Math.hypot(p[0] - q.p0[0], p[1] - q.p0[1]), Math.hypot(p[0] - q.p1[0], p[1] - q.p1[1]));
        }
        const vx = q.p1[0] - q.p0[0], vy = q.p1[1] - q.p0[1], L2 = vx * vx + vy * vy, t = Math.max(0, Math.min(1, ((p[0] - q.p0[0]) * vx + (p[1] - q.p0[1]) * vy) / (L2 || 1)));
        return Math.hypot(p[0] - q.p0[0] - t * vx, p[1] - q.p0[1] - t * vy);
      };
      Object.entries(g.placas).forEach(([k, pl]) => {
        const out = {};
        for (const campo of ["segmentos_contorno", "segmentos_canto", "segmentos_centro"]) {
          const segs = pl[campo], d = SIM.segPath(segs, (x) => x, (y) => -y, (r) => r, campo === "segmentos_contorno");
          const p = document.createElementNS(ns, "path"); p.setAttribute("d", d); svg.appendChild(p);
          const L = p.getTotalLength(), n = Math.ceil(L / 0.5); let dmax = 0;
          for (let i = 0; i <= n; i++) { const q = p.getPointAtLength(L * i / n), m = [q.x, -q.y]; dmax = Math.max(dmax, Math.min(...segs.map((s) => dSeg(s, m)))); }
          // y al revés: cada segmento queda cubierto por el trayecto (puntos medios de los arcos)
          const pts = []; for (let i = 0; i <= n; i++) { const q = p.getPointAtLength(L * i / n); pts.push([q.x, -q.y]); }
          let cover = 0; segs.forEach((s) => { const mid = s.tipo === "arco" ? (() => { const a0 = Math.atan2(s.p0[1] - s.centro[1], s.p0[0] - s.centro[0]), a1 = Math.atan2(s.p1[1] - s.centro[1], s.p1[0] - s.centro[0]), ccw = s.sentido !== "horario", nn = (x) => ((x % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI), sw = ccw ? nn(a1 - a0) : nn(a0 - a1), am = a0 + (ccw ? 1 : -1) * sw / 2; return [s.centro[0] + s.radio * Math.cos(am), s.centro[1] + s.radio * Math.sin(am)]; })() : [(s.p0[0] + s.p1[0]) / 2, (s.p0[1] + s.p1[1]) / 2]; cover = Math.max(cover, Math.min(...pts.map((m) => Math.hypot(m[0] - mid[0], m[1] - mid[1])))); });
          out[campo] = { arcos: segs.filter((s) => s.tipo === "arco").length, A: (d.match(/A /g) || []).length, dmax, cover, L };
        }
        res[k] = out;
      });
      svg.remove();
      return res;
    });
    assert.equal(Object.keys(geo).length, 4, "4 placas-guía");
    for (const [k, o] of Object.entries(geo)) for (const [c, v] of Object.entries(o)) {
      assert.equal(v.A, v.arcos, `${k} ${c}: un comando A por arco`);
      assert.ok(v.dmax <= 0.1, `${k} ${c}: desvío del trayecto ${v.dmax} mm > 0,1 mm`);
      assert.ok(v.cover <= 0.6, `${k} ${c}: el trayecto no pasa por el punto medio de algún segmento (${v.cover} mm)`);
    }
    console.log("placas-guía: " + Object.entries(geo).map(([k, o]) => `${k} ${o.segmentos_contorno.A} arcos, desvío máx. ${Math.max(...Object.values(o).map((v) => v.dmax)).toExponential(1)} mm`).join(" · "));

    // ---- 2. simulación: toma → empuje → retorno
    await page.click("#bSim"); await page.waitForSelector("#simDet");
    assert.equal(await page.$$eval("#simPlan path.sim-cam", (ps) => ps.length), 4, "las 4 placas-guía en planta como trayectos");
    assert.ok(await page.$$eval("#simPlan path.sim-cam", (ps) => ps.every((p) => / A [\d.]+ [\d.]+ 0 [01] [01] /.test(p.getAttribute("d")))), "placas con arcos A");
    const fases = {};
    for (const f of ["toma", "empuje", "retorno"]) {
      await page.evaluate((f) => SIM.seek(SIM.buscarFase(f)), f);
      assert.equal(await page.getAttribute("#simBox", "data-fase"), f, "fase " + f);
      const det = await page.evaluate(() => ({
        canto: document.querySelectorAll("#simDet path.sim-canto").length, traj: document.querySelectorAll("#simDet path.sim-traj").length, q: document.querySelectorAll("#simDet circle.sim-q").length,
        cara: document.querySelectorAll("#simDet polygon.sim-cara").length, ojal: document.querySelectorAll("#simDet circle.sim-ojal").length, cyl: document.querySelectorAll("#simDet .sim-cyl").length, rod: document.querySelectorAll("#simDet .sim-rod").length,
        tomado: document.querySelectorAll("#simDet circle.sim-pin.on").length, ct: document.querySelectorAll("#simDet circle.sim-ct:not(.off)").length, contacto: document.querySelector("#simContacto").textContent, fase: document.querySelector("#simFase").textContent,
        caraPts: document.querySelector("#simDet polygon.sim-cara").getAttribute("points").trim().split(/\s+/).length,
      }));
      fases[f] = det;
      assert.ok(det.canto >= 1 && det.traj >= 1 && det.q === 2 && det.cara === 2 && det.ojal === 2 && det.cyl === 2 && det.rod === 2, `${f}: elementos del detalle ${JSON.stringify(det)}`);
      assert.ok(det.caraPts > 8, `${f}: cara cilíndrica del bloque-uña como polilínea (${det.caraPts} puntos)`);
      if (f === "empuje") { assert.ok(det.tomado >= 1, "empuje: pasador tomado resaltado"); assert.ok(det.ct >= 1, "empuje: contacto Q–canto"); assert.match(det.contacto, /Q apoyado en el canto/); }
      if (f === "toma") assert.match(det.fase, /^toma/);
      await page.locator("#simBox").screenshot({ path: path.join(out, `sim_pivotado_${f}.png`) });
    }
    // el movimiento sale de TT.pivotAt: Q del dibujo = Q del núcleo en el instante
    const qOk = await page.evaluate(() => { SIM.seek(SIM.buscarFase("empuje")); const st = SIM._S.prov.state(SIM._S.t, SIM._S.caso), q = TT.pivotAt(SIM._S.P, st.s, "empuje", "antihorario"); return Math.hypot(q.Q[0] - st.q.Q[0], q.Q[1] - st.q.Q[1]) < 1e-9 && q.contactoLeva.enCanto; });
    assert.ok(qOk, "Q de la simulación = TT.pivotAt(...).Q con contacto en el canto");
    await page.click("#bSimClose");
    console.log("simulación: toma → empuje → retorno con contacto Q–canto, pasador Q, cara R120, ojal E, cilindro y pasador tomado; capturas en " + out);

    const abierto = await page.addStyleTag({ content: ABRIR });   // capturas de pestañas completas (sin encabezado fijo ni barra lateral)
    // ---- 3. cinemática del modo 2
    await tab("cinem");
    const kin = await page.evaluate(() => {
      const P = JSON.parse(localStorage.getItem("tt300c-params-v1")), A = TT.analyze(P, { noFEA: true }), cin = TT.designDrive(P, A.R).pivotado.cinematica;
      const cards = [...document.querySelectorAll("#kinGrid .kin-card")];
      const rows = [...document.querySelectorAll("#kinPts tr[data-i]")].map((tr) => ({ i: +tr.dataset.i, td: [...tr.querySelectorAll("td")].map((t) => t.textContent.trim()) }));
      const f = (v, d) => v.toLocaleString("es-CL", { minimumFractionDigits: d, maximumFractionDigits: d });
      return { cards: cards.map((c) => ({ k: c.dataset.k, lines: c.querySelectorAll("polyline").length, marks: c.querySelectorAll(".kin-mark").length })), rows, ok: rows.every((r) => r.td[1] === f(cin[r.i].th, 2) && r.td[4] === f(cin[r.i].F_cil, 1)), n: cin.length };
    });
    assert.deepEqual(kin.cards.map((c) => c.k), ["L", "F", "H", "phi", "hb", "sync"], "6 gráficos de cinemática");
    kin.cards.filter((c) => c.k !== "sync").forEach((c) => assert.equal(c.marks, 3, `${c.k}: marcas de toma, calado y fin`));
    assert.equal(kin.rows.length, 5, "5 puntos característicos");
    assert.ok(kin.ok, "la tabla reproduce designDrive().pivotado.cinematica");
    await page.locator('section[data-t="cinem"]').screenshot({ path: path.join(out, "cinematica_modo2.png") });
    console.log(`cinemática: 6 gráficos (${kin.n} posiciones del núcleo) y 5 puntos característicos: ${kin.rows.map((r) => r.td[0].split(" — ")[0]).join(" | ")}`);

    // ---- 4. comparación de la guía
    await tab("comp");
    const cmp = await page.evaluate(() => ({ filas: document.querySelectorAll("#compTab tr").length - 1, img: document.querySelector("#compImg") ? [document.querySelector("#compImg").naturalWidth, document.querySelector("#compImg").src.slice(0, 22)] : null, txt: document.querySelector("#compTab").textContent }));
    assert.ok(cmp.filas >= 15, "tabla de comparación");
    assert.ok(cmp.img && cmp.img[0] > 1000 && cmp.img[1] === "data:image/png;base64,", "figura embebida en base64 y decodificada");
    assert.match(cmp.txt, /b928552/); assert.match(cmp.txt, /no acotado/);
    await page.locator('section[data-t="comp"]').screenshot({ path: path.join(out, "comparacion_guia.png") });
    await tab("modelo");
    await page.locator('section[data-t="modelo"]').screenshot({ path: path.join(out, "modelo_pivotado.png") });
    console.log(`comparación: ${cmp.filas} filas, figura ${cmp.img[0]} px de ancho embebida`);

    await abierto.evaluate((e) => e.remove());
    // ---- 5. verificaciones: filas del núcleo frente al DOM
    const verifDOM = async () => { await tab("verif"); return page.evaluate(() => {
      const P = JSON.parse(localStorage.getItem("tt300c-params-v1")), A = TT.analyze(P), ST = { ok: "Cumple", warn: "Monitoreo", fail: "No cumple", info: "Info", pend: "Pendiente" };
      const rows = [...document.querySelectorAll('section[data-t="verif"] tr.chk-row')], falt = [], mal = [];
      A.checks.forEach((c, i) => {
        const tr = rows.find((r) => +r.dataset.i === i);
        if (!tr) { falt.push(c.grp + " · " + c.name); return; }
        const td = [...tr.querySelectorAll("td")].map((t) => t.textContent.trim());
        const fu = c.fu != null && isFinite(c.fu) ? c.fu.toLocaleString("es-CL", { minimumFractionDigits: 3, maximumFractionDigits: 3 }) : "—";
        if (td[0] !== ST[c.st] || !td[1].startsWith(c.name) || td[5] !== fu || td[6] !== c.ref) mal.push({ i, n: c.name, td0: td[0], fu: td[5], esperado: fu });
      });
      return { n: A.checks.length, dom: rows.length, falt, mal, grupos: [...new Set(A.checks.map((c) => c.grp))], ins: A.checks.filter((c) => /inserto/.test(c.name)).length };
    }); };
    const ver = await verifDOM();
    assert.deepEqual(ver.falt, [], "filas del núcleo que la UI no muestra");
    assert.deepEqual(ver.mal, [], "filas con estado, FU (3 decimales) o norma distintos");
    assert.equal(ver.dom, ver.n, "la UI no muestra filas que no estén en el núcleo");
    assert.ok(ver.ins >= 10, "filas de la plancha base con inserto en el grupo del soporte E");
    const nuevas = await page.evaluate(() => [/Placa-guía: contacto de Hertz/, /capa templada/, /ligamento/, /Tornillos de la placa-guía: corte \(ISO 10642 M16/, /enganche de la rosca/, /Sincronía/, /Flanco de reenganche/, /autobloqueo/, /Bloque-uña: contacto dentro de la cara/, /Vástago: flexocompresión/, /Pasador Q: flexión/].map((re) => [re.source, [...document.querySelectorAll('section[data-t="verif"] tr.chk-row')].some((tr) => re.test(tr.textContent))]));
    assert.deepEqual(nuevas.filter((x) => !x[1]).map((x) => x[0]), [], "filas nuevas de la placa-guía, bloque-uña, vástago y pasador Q");
    console.log(`verificaciones: ${ver.n} filas del núcleo = ${ver.dom} filas en el DOM (0 faltan, 0 sobran), ${ver.grupos.length} grupos, ${ver.ins} filas del inserto; FU con 3 decimales, norma y estado coinciden`);
    // ---- 10. y 9. en el modo 1 (guiado): filas del núcleo frente al DOM, veredicto e inserto
    await setP("drive_mode", 1);
    const ver1 = await verifDOM();
    assert.deepEqual(ver1.falt, [], "modo 1: filas del núcleo que la UI no muestra");
    assert.deepEqual(ver1.mal, [], "modo 1: filas con estado, FU (3 decimales) o norma distintos");
    assert.equal(ver1.dom, ver1.n, "modo 1: la UI no muestra filas que no estén en el núcleo");
    assert.ok(ver1.ins >= 10, "modo 1: filas de la plancha base con inserto en el grupo de la ménsula");
    await tab("resumen"); vr = await veredicto("guiado");
    const ins1 = await inserto(1);
    console.log(`modo 1 (guiado): ${ver1.n} filas del núcleo = ${ver1.dom} en el DOM (${ver1.ins} del inserto); veredicto «${vr.v.estado_global}»; ${ins1.n} insertos t ${ins1.t} con ${ins1.nv.join("/")} vértices; lista de materiales: «${ins1.bom.find((d) => /^Ménsula/.test(d))}»`);
    await page.click("#bReset"); await settle();

    // ---- 6. 0 NaN / undefined / Infinity en el DOM: modo 2 y modo 1 × alternativas
    const malos = () => page.evaluate(() => {
      const re = /\bNaN\b|undefined|-?Infinity/, hits = [];
      const walk = (n) => {
        if (n.nodeType === 3) { if (re.test(n.nodeValue)) hits.push("texto: " + n.nodeValue.trim().slice(0, 100)); return; }
        if (n.nodeType !== 1 || n.tagName === "SCRIPT" || n.tagName === "STYLE") return;
        for (const a of n.attributes) if (!(n.tagName === "IMG" && a.name === "src") && re.test(a.value)) hits.push(`${n.tagName}[${a.name}]: ${a.value.slice(0, 100)}`);
        n.childNodes.forEach(walk);
      };
      walk(document.body); return hits.slice(0, 5);
    });
    const tabs = await page.$$eval("#tabs button", (bs) => bs.map((b) => b.dataset.t));
    const resumen = [];
    for (const modo of [2, 1]) for (const [nom, sel, extra] of ALTS) {
      await page.click("#bReset"); await settle();
      if (modo === 1) await setP("drive_mode", 1);
      await page.selectOption("#altSel", sel); await settle();
      for (const [k, v] of Object.entries(extra)) await setP(k, v);
      for (const t of tabs) {
        await tab(t);
        if (t === "temp" || t === "tapones") await page.waitForFunction((t) => !/Calculando/.test(document.querySelector(`section[data-t="${t}"]`).textContent), t, { timeout: 180000 });
      }
      let m = await malos();
      assert.deepEqual(m, [], `modo ${modo} · ${nom}: NaN/undefined/Infinity en las pestañas`);
      await page.click("#bSim"); await page.waitForSelector("#simDet");
      for (const f of modo === 2 ? ["toma", "empuje", "retorno", "reenganche"] : ["empuje", "retorno", "reenganche"]) { await page.evaluate((f) => SIM.seek(SIM.buscarFase(f)), f); m = await malos(); assert.deepEqual(m, [], `modo ${modo} · ${nom} · simulación ${f}: NaN/undefined/Infinity`); }
      await page.click("#bSimClose");
      assert.deepEqual(errs, [], `modo ${modo} · ${nom}: errores de consola: ` + errs.slice(0, 3).join(" | "));
      resumen.push(`${modo === 2 ? "pivotado" : "guiado"}·${nom}`);
    }
    console.log(`0 NaN / undefined / Infinity en el DOM (${tabs.length} pestañas + simulación) en: ${resumen.join(", ")}`);
    console.log("e2e guía curva: OK · capturas en", out);
  } finally { await browser.close(); }
})().catch((e) => { console.error(e); process.exit(1); });
