/* Pruebas del paquete de dibujo (packages/web/planos_export.js): DXF parseable, láminas con advertencia y notas,
   lista de materiales contra la masa del núcleo, JSON de diseño igual al de tools/export_design.js, ZIP y página de impresión.
   Ejecutar: node --test tests/test_planos_export.js */
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), os = require("os"), path = require("path"), zlib = require("zlib");
const { execFileSync } = require("child_process");
const TT = require("../packages/core/tt300c.js"), AG = require("../packages/agents/agentes.js"), PL = require("../packages/web/planos_export.js");

const VARIANTS = [
  ["acero-acero", {}],
  ["A discos inoxidables", { opt_ss: 1 }],
  ["B discos + UHMW", { opt_uhmw: 1 }],
  ["C bronce con grafito", { opt_bz: 1 }],
  ["C2 dos placas de bronce, con madera", { opt_bz: 1, bz_conf: 2, opt_wood: 1 }],
  ["C3 pastillas, pegado permanente", { opt_bz: 1, bz_conf: 3, fix_mode: 2 }],
  ["B con cubierta de madera", { opt_uhmw: 1, opt_wood: 1 }],
];
const cache = new Map();
function pack(over) {
  const key = JSON.stringify(over);
  if (!cache.has(key)) {
    const P = Object.assign(TT.defaults(), over), A = TT.analyze(P, { noFEA: true });
    cache.set(key, { P, A, pk: PL.buildPackage(P, A, { noDesign: true, fecha: "2026-11-05" }) });
  }
  return cache.get(key);
}

/* ---- lector DXF mínimo: pares (código, valor) → secciones y entidades ---- */
function parseDXF(buf) {
  const lines = Buffer.from(buf).toString("latin1").split(/\r?\n/);
  assert.equal(lines.length % 2, 1, "número par de líneas de datos (el último elemento es la cadena vacía final)");
  const pairs = [];
  for (let i = 0; i + 1 < lines.length; i += 2) { const c = lines[i].trim(); assert.match(c, /^-?\d+$/, `código de grupo inválido en la línea ${i + 1}: "${lines[i]}"`); pairs.push([+c, lines[i + 1]]); }
  const secs = {}, order = []; let cur = null, tables = {}, tab = null, ents = [], e = null;
  for (let i = 0; i < pairs.length; i++) {
    const [c, v] = pairs[i];
    if (c === 0 && v === "SECTION") { const nm = pairs[++i][1]; cur = nm; secs[nm] = []; order.push(nm); continue; }
    if (c === 0 && v === "ENDSEC") { cur = null; continue; }
    if (c === 0 && v === "EOF") { order.push("EOF"); break; }
    assert.ok(cur, `grupo fuera de sección: ${c}/${v}`);
    secs[cur].push([c, v]);
    if (cur === "ENTITIES") { if (c === 0) { e = { type: v, g: [] }; ents.push(e); } else e.g.push([c, v]); }
  }
  const get = (en, code) => { const f = en.g.find((x) => x[0] === code); return f ? f[1] : undefined; };
  const num = (en, code) => { const f = get(en, code); return f === undefined ? NaN : +f; };
  return { order, secs, ents, get, num, header: Object.fromEntries(secs.HEADER.reduce((a, p, i, arr) => (p[0] === 9 ? a.concat([[p[1], arr[i + 1] && arr[i + 1][1]]]) : a), [])) };
}
const layersOf = (d) => { const L = []; let inLayer = false; d.secs.TABLES.forEach(([c, v], i, arr) => { if (c === 0 && v === "LAYER") L.push(arr[i + 1][1]); }); return L; };
const counts = (d) => d.ents.reduce((o, e) => (o[e.type] = (o[e.type] || 0) + 1, o), {});
const texts = (d) => d.ents.filter((e) => e.type === "TEXT").map((e) => ({ s: d.get(e, 1), layer: d.get(e, 8), h: d.num(e, 40) }));
const dxfOf = (pk, id) => pk.files.find((f) => f.kind === "dxf" && f.sheet === id);

test("DXF: estructura R12, secciones, capas y entidades válidas en las 4 alternativas de interfaz", () => {
  for (const [nombre, over] of VARIANTS) {
    const { pk } = pack(over);
    assert.equal(pk.sheets.length, 5, nombre);
    for (const sh of pk.sheets) {
      const f = dxfOf(pk, sh.id), d = parseDXF(f.data), ctx = `${nombre} · ${sh.code}`;
      assert.deepEqual(d.order, ["HEADER", "TABLES", "BLOCKS", "ENTITIES", "EOF"], ctx);
      assert.equal(d.header.$ACADVER, "AC1009", ctx + " (R12)");
      assert.equal(d.header.$DWGCODEPAGE, "ANSI_1252", ctx);
      const lay = layersOf(d);
      for (const l of ["CONTORNO", "COTAS", "EJES", "TEXTO"]) assert.ok(lay.includes(l), `${ctx}: falta la capa ${l}`);
      const c = counts(d);
      for (const t of ["LINE", "POLYLINE", "TEXT", "CIRCLE"]) assert.ok((c[t] || 0) > 0, `${ctx}: sin entidades ${t}`);
      assert.ok(c.TEXT > 15 && c.LINE > 40, ctx + " contenido mínimo");
      assert.equal(c.POLYLINE, c.SEQEND, ctx + ": POLYLINE y SEQEND balanceados");
      // los VERTEX van dentro de POLYLINE…SEQEND
      let open = false, nv = 0;
      for (const e of d.ents) { if (e.type === "POLYLINE") { assert.ok(!open); open = true; nv = 0; } else if (e.type === "VERTEX") { assert.ok(open, ctx + ": VERTEX fuera de POLYLINE"); nv++; } else if (e.type === "SEQEND") { assert.ok(open && nv >= 2, ctx + ": POLYLINE con menos de 2 vértices"); open = false; } else assert.ok(!open, ctx + ": entidad dentro de POLYLINE"); }
      // capas usadas definidas y coordenadas finitas dentro de la hoja
      for (const e of d.ents) {
        if (e.type === "SEQEND") continue;
        assert.ok(lay.includes(d.get(e, 8)), `${ctx}: capa no definida ${d.get(e, 8)}`);
        for (const k of [10, 20, 11, 21, 40]) { const v = d.num(e, k); if (!Number.isNaN(v)) assert.ok(Number.isFinite(v), `${ctx}: valor no finito`); }
        if (e.type !== "TEXT" && e.type !== "VERTEX") { const x = d.num(e, 10), y = d.num(e, 20); if (!Number.isNaN(x)) assert.ok(x >= -1 && x <= sh.W + 1 && y >= -1 && y <= sh.H + 1, `${ctx}: ${e.type} fuera de la hoja (${x}, ${y})`); }
      }
      // sólo caracteres Latin-1 imprimibles (ANSI_1252)
      assert.ok(!/[^\x09\x0a\x0d\x20-\x7e\xa0-\xff]/.test(Buffer.from(f.data).toString("latin1")), ctx + ": caracteres fuera de ANSI_1252");
      // entidades según lámina
      if (sh.id === "IZAJE-00") assert.ok(c.ARC >= 1, ctx + ": la oreja lleva un ARC");
      if (sh.id === "MESA-00") assert.ok(c.CIRCLE >= TT.defaults().N_pin, ctx + ": un CIRCLE por pasador");
      if (sh.id === "BASE-00") assert.ok(c.CIRCLE >= 6 && c.POLYLINE >= 10, ctx);
    }
  }
});

test("Láminas: advertencia, notas, cajetín y código en el DXF, el SVG y la página de impresión de cada variante", () => {
  for (const [nombre, over] of VARIANTS) {
    const { pk, P, A } = pack(over), ifn = PL.ifaceName(P, A.R.ifc);
    const html = Buffer.from(pk.files.find((f) => f.kind === "html").data).toString("utf8");
    for (const sh of pk.sheets) {
      const ctx = `${nombre} · ${sh.code}`, d = parseDXF(dxfOf(pk, sh.id).data), T = texts(d), all = T.map((t) => t.s);
      assert.match(sh.code, /^TT300C-[A-Z]+-\d{2}-B$/, ctx);
      assert.ok(all.includes(PL.ADVERTENCIA), ctx + ": falta la advertencia");
      assert.equal(PL.ADVERTENCIA, "ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO.");
      for (const n of ["En caso de vientos fuertes no se recomienda realizar la operación.", "Equipo sin anclaje"]) assert.ok(all.includes(n), `${ctx}: falta la nota «${n}»`);
      assert.ok(all.some((s) => s === `CÓDIGO: ${sh.code}`), ctx + ": código en el cajetín");
      assert.ok(all.some((s) => /^ESC\. 1:\d/.test(s)), ctx + ": escala");
      assert.ok(all.some((s) => /^MASA DE ESTA LÁMINA: [\d,]+ kg$/.test(s)), ctx + ": masa de la lámina");
      assert.ok(all.some((s) => s.startsWith(`MASA TOTAL DEL EQUIPO: ${PL.nf(A.R.m.total)} kg`)), ctx + ": masa total = núcleo");
      assert.ok(all.some((s) => s.startsWith("INTERFAZ: " + ifn)), ctx + ": alternativa de interfaz en el cajetín");
      assert.ok(all.some((s) => s.startsWith("FIJACIÓN: " + PL.fixText(P, A.R.ifc))), ctx + ": fijación");
      assert.ok(all.some((s) => /Formato A[123]/.test(s)), ctx + ": formato");
      // el cajetín está en capas de texto negro sobre blanco (ACI 7 en TEXTO y CAJETIN)
      const lt = d.secs.TABLES, colorOf = (n) => { const i = lt.findIndex(([c, v], k) => c === 2 && v === n && lt[k - 1] && lt[k - 1][1] === "LAYER"); return +lt.slice(i).find(([c]) => c === 62)[1]; };
      assert.equal(colorOf("TEXTO"), 7); assert.equal(colorOf("CAJETIN"), 7);
      // SVG
      const svg = Buffer.from(pk.files.find((f) => f.kind === "svg" && f.sheet === sh.id).data).toString("utf8");
      assert.match(svg, /<svg [^>]*viewBox="0 0 [\d.]+ [\d.]+"/); assert.ok(svg.includes(PL.ADVERTENCIA) && svg.includes("Equipo sin anclaje") && svg.includes("En caso de vientos fuertes no se recomienda realizar la operación."), ctx + " SVG");
      assert.ok(svg.includes("fill=\"#fff\"") && svg.includes("fill=\"#000\""), ctx + ": SVG negro sobre blanco");
      assert.ok(html.includes(sh.code), ctx + " en la página de impresión");
    }
    // interfaz elegida visible en la sección y marcas «A DEFINIR» donde el núcleo no define la geometría
    const conj = texts(parseDXF(dxfOf(pk, "CONJ-00").data)).map((t) => t.s).join("\n");
    assert.ok(conj.includes("Interfaz elegida: " + ifn), nombre + ": sección con la interfaz elegida");
    if (over.opt_wood) assert.match(conj, /TABLONES A DEFINIR/);
    if (over.bz_conf === 3) assert.match(conj, /PASTILLAS DE BRONCE.*A DEFINIR/);
    const piv = texts(parseDXF(dxfOf(pk, "PIVOTE-00").data)).map((t) => t.s).join("\n");
    assert.match(piv, /A DEFINIR/);
  }
  const { pk } = pack({});
  const html = Buffer.from(pk.files.find((f) => f.kind === "html").data).toString("utf8");
  assert.ok(html.startsWith("<!doctype html>") && html.includes("@media print") && html.includes("@page"), "HTML de impresión autocontenido");
  assert.equal((html.match(/<section class="sheet/g) || []).length, 5);
  assert.ok(!/(src|href)=["']https?:/i.test(html), "sin recursos externos");
});

test("Interfaz: cada alternativa dibuja sus capas y respeta la exclusión mutua A/B/C", () => {
  const nPoly = (over, id) => counts(parseDXF(dxfOf(pack(over).pk, id).data)).POLYLINE;
  const base = nPoly({}, "CONJ-00"), a = nPoly({ opt_ss: 1 }, "CONJ-00"), b = nPoly({ opt_uhmw: 1 }, "CONJ-00");
  assert.ok(a === base + 2, `A agrega 2 discos (${a} vs ${base})`);
  assert.ok(b === base + 3, `B agrega 2 discos y la lámina UHMW (${b} vs ${base})`);
  assert.ok(nPoly({ opt_bz: 1 }, "CONJ-00") === base + 2, "C agrega bronce y disco duro");
  // sectores desmontables: más líneas en la base con interfaz que sin ella
  const nl = (over, id) => counts(parseDXF(dxfOf(pack(over).pk, id).data)).LINE;
  assert.ok(nl({ opt_ss: 1 }, "BASE-00") >= nl({}, "BASE-00") + TT.defaults().n_sec, "n_sec juntas de sector en la planta de la base");
  assert.ok(nl({ opt_ss: 1, fix_mode: 2 }, "BASE-00") < nl({ opt_ss: 1 }, "BASE-00"), "pegado permanente: sin juntas");
  // exclusión mutua: el núcleo y el generador rechazan dos alternativas a la vez
  assert.throws(() => TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, opt_bz: 1 }), { noFEA: true }));
  assert.throws(() => PL.buildDesign(Object.assign(TT.defaults(), { opt_uhmw: 1, opt_bz: 1 })), /una sola opción de interfaz/);
  // la interfaz de los parámetros define el nombre
  assert.match(PL.ifaceName(pack({ opt_ss: 1 }).P, pack({ opt_ss: 1 }).A.R.ifc), /^A:/);
  assert.match(PL.ifaceName(pack({ opt_uhmw: 1 }).P, pack({ opt_uhmw: 1 }).A.R.ifc), /^B:/);
  assert.match(PL.ifaceName(pack({ opt_bz: 1 }).P, pack({ opt_bz: 1 }).A.R.ifc), /^C:/);
});

/* ---- CSV ---- */
function parseCSV(buf) {
  const txt = Buffer.from(buf).toString("utf8"); assert.equal(txt.charCodeAt(0), 0xfeff, "UTF-8 con BOM");
  return txt.slice(1).split(/\r\n/).filter(Boolean).map((l) => { const out = []; let cur = "", q = false; for (let i = 0; i < l.length; i++) { const ch = l[i]; if (q) { if (ch === '"' && l[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') q = false; else cur += ch; } else if (ch === '"') q = true; else if (ch === ";") { out.push(cur); cur = ""; } else cur += ch; } out.push(cur); return out; });
}
const dec = (s) => parseFloat(String(s).replace(",", "."));

test("Lista de materiales (CSV): la masa total coincide con R.m.total del núcleo (±0,5 %) y con cada subconjunto", () => {
  for (const [nombre, over] of VARIANTS) {
    const { pk, A } = pack(over), rows = parseCSV(pk.files.find((f) => f.kind === "csv").data);
    const head = rows.findIndex((r) => r[0] === "Código");
    assert.deepEqual(rows[head], ["Código", "Subconjunto", "Pos.", "Descripción", "Material", "Cantidad", "Masa unitaria [kg]", "Masa total [kg]", "Observación"]);
    const items = rows.filter((r) => /^TT300C-[A-Z]+-\d{2}-B$/.test(r[0]));
    assert.ok(items.length >= 14, nombre + ": partidas");
    const total = items.reduce((s, r) => s + dec(r[7]), 0), tot = rows.find((r) => r[3] === "MASA TOTAL");
    assert.ok(tot, "fila MASA TOTAL");
    assert.ok(Math.abs(total - A.R.m.total) <= 0.005 * A.R.m.total, `${nombre}: ${total} vs núcleo ${A.R.m.total}`);
    assert.ok(Math.abs(dec(tot[7]) - A.R.m.total) <= 0.005 * A.R.m.total, nombre + ": MASA TOTAL");
    items.forEach((r) => assert.ok(Math.abs(dec(r[5]) * dec(r[6]) - dec(r[7])) <= 0.002 * Math.max(1, dec(r[7])) + 0.002, `${nombre}: ${r[0]} cantidad × unitaria = total`));
    // masas por componente del núcleo
    const m = A.R.m, sum = (sub) => items.filter((r) => r[0].startsWith("TT300C-" + sub + "-")).reduce((s, r) => s + dec(r[7]), 0);
    const near = (a, b, msg) => assert.ok(Math.abs(a - b) <= 0.0005 * Math.max(1, b), `${nombre} ${msg}: ${a} vs ${b}`);
    near(sum("MESA"), m.disc, "MESA"); near(sum("INTER"), m.ss + m.uhmw + m.bz + m.stopBars, "INTER (discos, UHMW, bronce y barras de los topes)"); near(sum("CIL"), m.cyl, "cilindros");
    near(sum("PIVOTE") + sum("IZAJE") + sum("BASE"), m.pivot + m.base + m.rim + m.brackets + m.dogs + m.shoes + m.beds, "base + collar + orejas + pivote");
    assert.ok(rows.some((r) => r[0].includes("ESTOS PLANOS NO SON VÁLIDOS")), "advertencia en el CSV");
    if (over.opt_wood) assert.ok(items.some((r) => /^TT300C-MESA-07-/.test(r[0])), "cubierta de madera en la lista");
    else assert.ok(!items.some((r) => /^TT300C-MESA-07-/.test(r[0])));
    // sector: cantidad = n_sec cuando la fijación es desmontable
    const inter = items.filter((r) => r[0].startsWith("TT300C-INTER-"));
    if (over.opt_ss || over.opt_uhmw) assert.equal(+inter[0][5], over.fix_mode === 2 ? 1 : TT.defaults().n_sec);
  }
});

test("Cada lámina reporta la masa de su subconjunto y la masa total del núcleo", () => {
  const { pk, A } = pack({ opt_uhmw: 1 }), m = A.R.m;
  const by = Object.fromEntries(pk.sheets.map((s) => [s.id, s.masa]));
  assert.ok(Math.abs(by["CONJ-00"] - m.total) < 1e-6);
  assert.ok(Math.abs(by["MESA-00"] - m.disc) < 1e-6);
  assert.ok(Math.abs(by["PIVOTE-00"] - m.pivot - (TT.defaults().h_boss > 0 ? RHO_COLLAR(TT.defaults()) : 0)) < 1e-6);
  assert.ok(by["IZAJE-00"] > 0 && by["BASE-00"] > 0);
});
function RHO_COLLAR(P) { return 7.85e-6 * Math.PI / 4 * (P.D_boss ** 2 - P.D_piv ** 2) * P.h_boss; }

/* ---- JSON de diseño = tools/export_design.js ---- */
test("JSON de diseño: mismo contenido que tools/export_design.js (parámetros por defecto y alternativa B)", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "tt300c-")), script = path.join(__dirname, "..", "tools", "export_design.js");
  for (const over of [{}, { opt_uhmw: 1, opt_wood: 1 }]) {
    const P = Object.assign(TT.defaults(), over), pf = path.join(tmp, "p.json"); fs.writeFileSync(pf, JSON.stringify(P));
    const ref = JSON.parse(execFileSync(process.execPath, [script, pf], { maxBuffer: 1 << 28 }).toString());
    const got = JSON.parse(PL.designJSON(PL.buildDesign(P)));
    delete ref.fecha; delete got.fecha;
    assert.deepEqual(Object.keys(got).sort(), Object.keys(ref).sort(), "mismas claves de primer nivel");
    assert.deepEqual(got, ref);
  }
  // el paquete lo incluye
  const P = TT.defaults(), A = TT.analyze(P, { noFEA: true }), pk = PL.buildPackage(P, A, {});
  const j = JSON.parse(Buffer.from(pk.files.find((f) => f.kind === "json").data).toString("utf8"));
  assert.equal(j.proyecto, "TT300-C"); assert.ok(j.derivados && j.verificaciones && j.pasadores.length === P.N_pin);
});

/* ---- geometría resuelta de los topes (interfazGeom.topes) y barras en la lista de materiales ---- */
test("interfazGeom.topes: geometría resuelta de cada tope (R.ifc.topes), idéntica en tools/export_design.js; las barras suman a la lista de materiales", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "tt300c-")), script = path.join(__dirname, "..", "tools", "export_design.js");
  for (const [nombre, over] of VARIANTS) {
    const { P, A, pk } = pack(over), T = A.R.ifc.topes, got = JSON.parse(PL.designJSON(PL.buildDesign(P, A))).interfazGeom.topes;
    assert.equal(got.length, T.length, nombre + ": un elemento por tope");
    got.forEach((g, i) => {
      for (const k of ["pieza", "n", "t", "L", "Lav", "F", "a_sup", "a_inf", "h_barra", "h_c", "z", "w_tope", "b_tope", "w_min", "capas", "m_barra", "m_barras"]) assert.ok(k in g, `${nombre}: falta ${k}`);
      assert.deepEqual(g, JSON.parse(JSON.stringify(T[i])), nombre + ": " + g.pieza);
    });
    const pf = path.join(tmp, "p.json"); fs.writeFileSync(pf, JSON.stringify(P));
    assert.deepEqual(JSON.parse(execFileSync(process.execPath, [script, pf], { maxBuffer: 1 << 28 }).toString()).interfazGeom.topes, got, nombre + ": ambos exportadores iguales");
    // 3.ª pasada: R_i efectivo de la interfaz y rebaje del collar en la plancha inferior (claves nuevas de interfazGeom, iguales en los dos exportadores)
    const IG = JSON.parse(PL.designJSON(PL.buildDesign(P, A))).interfazGeom, IG2 = JSON.parse(execFileSync(process.execPath, [script, pf], { maxBuffer: 1 << 28 }).toString()).interfazGeom, Rr = A.R, hg = Rr.hubG;
    for (const k of ["Ri", "D_rebaje_bot", "h_rebaje", "h_rebaje_plancha", "h_rebaje_cubo", "m_ri"]) assert.ok(k in IG, `${nombre}: falta interfazGeom.${k}`);
    assert.equal(IG.Ri, Rr.Ri); assert.equal(IG.Ri, P.D_boss / 2 + P.c_boss_r + P.m_ri, nombre + ": R_i = D_collar/2 + c_boss_r + m_ri");
    assert.equal(IG.D_rebaje_bot, P.D_boss + 2 * P.c_boss_r, nombre + ": Ø del rebaje en la plancha inferior"); assert.equal(IG.D_rebaje_bot, hg.Drb);
    assert.equal(IG.h_rebaje, P.h_boss - Rr.ifc.delta + P.c_boss_a, nombre + ": profundidad h_collar − δ + c_boss_a"); assert.equal(IG.h_rebaje_plancha, IG.h_rebaje > 0 ? P.t_bot : 0, nombre + ": agujero pasante en la plancha inferior"); assert.equal(IG.h_rebaje_cubo, Math.min(Math.max(0, IG.h_rebaje - P.t_bot), P.h_disc - P.t_top - P.t_bot)); assert.equal(IG.m_ri, P.m_ri);
    for (const k of ["Ri", "D_rebaje_bot", "h_rebaje", "h_rebaje_plancha", "h_rebaje_cubo", "m_ri", "d_bush", "hole_top"]) assert.equal(IG2[k], IG[k], `${nombre}: ${k} igual en tools/export_design.js`);
    assert.equal(IG.d_bush, P.D_piv + 30);
    // 4.ª pasada: descuentos de masa de las coronas (cortes), juntas efectivas, tolerancia h_c y anillo de acero de la madera: claves nuevas, iguales en los dos exportadores
    for (const k of ["cortes", "junta_sector", "junta_uhmw", "j_sec", "tol_hc", "t_ring", "anillo_madera"]) { assert.ok(k in IG, `${nombre}: falta interfazGeom.${k}`); assert.deepEqual(IG2[k], IG[k], `${nombre}: ${k} igual en tools/export_design.js`); }
    assert.deepEqual(IG.cortes, JSON.parse(JSON.stringify(A.R.ifc.cortes || [])), nombre + ": cortes = R.ifc.cortes");
    assert.equal(IG.j_sec, P.j_sec); assert.equal(IG.tol_hc, P.tol_hc); assert.equal(IG.t_ring, P.t_ring);
    if (A.R.ifc.o > 0 && P.fix_mode < 1.5) { assert.ok(IG.cortes.length >= 2 && IG.cortes.every((c) => c.m_desc > 0 && Math.abs(c.m_neta - (c.m_bruta - c.m_desc)) < 1e-9), nombre + ": cortes con masa bruta, descontada y neta"); assert.ok(IG.junta_sector >= 1 || A.R.ifc.o === 2 && IG.junta_sector == null, nombre + ": junta en frío ≥ 1 mm"); }
    if (A.R.ifc.o === 2) assert.ok(IG.junta_uhmw >= 1, nombre + ": junta de la lámina UHMW ≥ 1 mm");
    if (A.R.m.ring > 0) { assert.ok(IG.anillo_madera && IG.anillo_madera.m === A.R.m.ring && IG.anillo_madera.h_ring === P.t_wood, nombre + ": anillo de la madera"); const rg = pk.bom.items.find((i) => /Anillo de acero de contención/.test(i.desc)); assert.ok(rg && Math.abs(rg.mTot - A.R.m.ring) < 1e-9, nombre + ": anillo en la lista de materiales"); } else assert.equal(IG.anillo_madera, null);
    // lista de materiales: las barras de los topes son una línea más y la lista cierra con m.total
    const bars = pk.bom.items.find((i) => /Barras de los topes/.test(i.desc));
    const mb = A.R.m.stopBars;
    if (mb > 0) { assert.ok(bars, nombre + ": línea de barras en la lista"); assert.ok(Math.abs(bars.mTot - mb) < 1e-9); } else assert.ok(!bars);
    assert.ok(Math.abs(pk.bom.total - A.R.m.total) < 1e-6, nombre + `: lista = núcleo (${pk.bom.total} vs ${A.R.m.total})`);
  }
  assert.deepEqual(JSON.parse(PL.designJSON(PL.buildDesign(TT.defaults()))).interfazGeom.topes, [], "sin interfaz: sin topes");
});

/* ---- ZIP ---- */
function readZip(u8) {
  const dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength); let e = u8.length - 22; assert.equal(dv.getUint32(e, true), 0x06054b50, "fin de directorio central");
  const n = dv.getUint16(e + 10, true); let p = dv.getUint32(e + 16, true); const out = {};
  for (let i = 0; i < n; i++) {
    assert.equal(dv.getUint32(p, true), 0x02014b50);
    const crc = dv.getUint32(p + 16, true), csz = dv.getUint32(p + 20, true), nl = dv.getUint16(p + 28, true), xl = dv.getUint16(p + 30, true), cl = dv.getUint16(p + 32, true), off = dv.getUint32(p + 42, true);
    const name = Buffer.from(u8.subarray(p + 46, p + 46 + nl)).toString("utf8"), lnl = dv.getUint16(off + 26, true), lxl = dv.getUint16(off + 28, true), start = off + 30 + lnl + lxl;
    out[name] = { data: u8.subarray(start, start + csz), crc }; p += 46 + nl + xl + cl;
  }
  return out;
}
test("ZIP del paquete: directorio central válido, CRC-32 correcto y contenido completo", () => {
  const { pk } = pack({ opt_ss: 1 }), z = readZip(pk.zip()), names = Object.keys(z);
  for (const sh of pk.sheets) { assert.ok(names.includes(`TT300C_paquete_dibujo/DXF/${sh.code}.dxf`)); assert.ok(names.includes(`TT300C_paquete_dibujo/SVG/${sh.code}.svg`)); }
  for (const f of ["TT300C_lista_materiales.csv", "TT300C_laminas_impresion.html", "LEEME.txt"]) assert.ok(names.includes("TT300C_paquete_dibujo/" + f), f);
  for (const [nm, e] of Object.entries(z)) { assert.equal(PL.crc32(e.data), e.crc, "CRC " + nm); if (zlib.crc32) assert.equal(zlib.crc32(e.data) >>> 0, e.crc); }
  const leeme = Buffer.from(z["TT300C_paquete_dibujo/LEEME.txt"].data).toString("utf8");
  assert.ok(leeme.includes(PL.ADVERTENCIA) && leeme.includes("Equipo sin anclaje"));
  // con el JSON de diseño cuando se pide
  const P = TT.defaults(), A = TT.analyze(P, { noFEA: true }), full = readZip(PL.buildPackage(P, A, {}).zip());
  assert.ok(Object.keys(full).includes("TT300C_paquete_dibujo/TT300-C_design.json"));
});

/* ---- DXF con ezdxf (si está instalado) ---- */
test("DXF: lectura y auditoría con ezdxf (se omite si no está instalado)", (t) => {
  try { execFileSync("python3", ["-I", "-c", "import ezdxf"], { stdio: "ignore" }); } catch (e) { return t.skip("ezdxf no disponible"); }
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "tt300c-dxf-"));
  for (const [nombre, over] of [VARIANTS[0], VARIANTS[2], VARIANTS[3]]) {
    for (const f of pack(over).pk.files.filter((x) => x.kind === "dxf")) fs.writeFileSync(path.join(tmp, nombre.split(" ")[0] + "_" + path.basename(f.name)), f.data);
  }
  const py = `import ezdxf,glob,sys\nfor f in sorted(glob.glob(sys.argv[1]+'/*.dxf')):\n    d=ezdxf.readfile(f); a=d.audit()\n    assert not a.errors, (f,a.errors)\n    assert d.dxfversion=='AC1009', d.dxfversion\n    t=[e.dxf.text for e in d.modelspace() if e.dxftype()=='TEXT']\n    assert any('NO SON V\\u00c1LIDOS' in s for s in t), f\nprint('ok')`;
  assert.equal(execFileSync("python3", ["-I", "-c", py, tmp]).toString().trim(), "ok");
});

/* ---- Escenario térmico (exposición solar, 80 °C): clave `termica` idéntica en los dos exportadores ---- */
test("JSON de diseño: `termica` (escenario solar 80 °C, por alternativa y temperatura) igual en tools/export_design.js y packages/web/planos_export.js", () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "tt300c-")), script = path.join(__dirname, "..", "tools", "export_design.js");
  for (const over of [{}, { opt_uhmw: 1, opt_wood: 1, T_serv: 70, dT_grad: 12 }]) {
    const P = Object.assign(TT.defaults(), over), pf = path.join(tmp, "p.json"); fs.writeFileSync(pf, JSON.stringify(P));
    const ref = JSON.parse(execFileSync(process.execPath, [script, pf], { maxBuffer: 1 << 28 }).toString()).termica;
    const got = JSON.parse(PL.designJSON(PL.buildDesign(P))).termica;
    assert.ok(got && Array.isArray(got.alternativas) && got.alternativas.length === 6, "una entrada por alternativa");
    assert.deepEqual(got, ref, "ambos exportadores iguales");
    assert.deepEqual(got, JSON.parse(JSON.stringify(TT.thermal(P))), "igual a TT.thermal(P)");
    assert.equal(got.T_scn, over.T_serv || 80); assert.equal(got.gradiente_scn, over.dT_grad || 15);
    for (const a of got.alternativas) { assert.ok(a.byT.length >= 5 && a.byT.every((b) => b.FS > 0 && "fuEst" in b && Array.isArray(b.sensibles) && Array.isArray(b.cambian)), a.id); assert.equal(a.madera, !!over.opt_wood, "la madera sigue la casilla del formulario"); }
    assert.ok(got.avisos.length >= 3 && got.aceite.length === got.T.length);
  }
});
