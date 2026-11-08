/* Exporta, para la memoria de cálculo, el análisis completo de cada alternativa de interfaz (base, A, B, C1, C2, C3 y cubierta de madera)
   más el escenario térmico de la cubierta de madera (TT.thermal con wood = 1), los tapones de grafito de la opción C (TT.tapones: cantidad real frente a ideal),
   las medidas recomendadas del escenario solar (alcance placas y disco, term_alcance = 1) y la nota informativa del accionamiento fuera de alcance.
   Fuente única: TT.analyze / TT.thermal / TT.tapones; la memoria solo redacta.
   Uso: node tools/export_alternativas.js [parametros.json] > cad/out/TT300-C_alternativas.json */
const fs = require("fs");
const TT = require("../packages/core/tt300c.js");
const P = Object.assign(TT.defaults(), process.argv[2] ? JSON.parse(fs.readFileSync(process.argv[2], "utf8")) : {});
const brief = (c) => (c ? { grp: c.grp, nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref } : null);
const ALTS = TT.TH_ALTS.map(([id, nombre, flags]) => ({ id, nombre, flags, wood: 0 })).concat([{ id: "W", nombre: "Base + cubierta de madera dura con anillo de acero", flags: {}, wood: 1 }]);
const out = { version: 1, P_ref: { hc_min: P.hc_min, tol_hc: P.tol_hc, m_ri: P.m_ri, R_ear: P.R_ear, d_ear: P.d_ear, t_ring: P.t_ring, t_wood: P.t_wood, j_sec: P.j_sec }, alternativas: [] };
let m0 = null;
ALTS.forEach((a) => {
  const Pa = Object.assign({}, P, { opt_ss: 0, opt_uhmw: 0, opt_bz: 0, bz_conf: 1 }, a.flags, { opt_wood: a.wood });
  const A = TT.analyze(Pa), R = A.R, I = R.ifc, ck = A.checks;
  if (a.id === "base") m0 = R.m.total;
  const fuOk = ck.filter((c) => c.kind !== "info" && c.fu != null && isFinite(c.fu) && c.st !== "pend");
  const gov = fuOk.reduce((b, c) => (!b || c.fu > b.fu ? c : b), null);
  const govRes = ck.filter((c) => c.kind === "fu" && c.sys === "est" && c.grp !== "Temperatura" && c.fu != null && isFinite(c.fu)).reduce((b, c) => (!b || c.fu > b.fu ? c : b), null);   // misma definición que fuEstOf de TT.thermal: verificaciones de resistencia del sistema estructural (excluye giro, mínimos constructivos «geo» e informativos)
  const top5 = fuOk.slice().sort((x, y) => y.fu - x.fu).slice(0, 5).map(brief);
  const byGrp = (re) => ck.filter((c) => re.test(c.grp));
  out.alternativas.push({
    id: a.id, nombre: a.nombre, flags: a.flags, madera: !!a.wood,
    masa: R.m.total, dMasa: R.m.total - (m0 == null ? R.m.total : m0), masas: { ss: R.m.ss, uhmw: R.m.uhmw, bz: R.m.bz, wood: R.m.wood, ring: R.m.ring, stopBars: R.m.stopBars, disc: R.m.disc },
    interfaz: { o: I.o, conf: I.conf || null, tss: I.tss, tss2: I.tss2, tssReq: I.tssReq, tss2Req: I.tss2Req, tuh: I.tuh, tuhReq: I.tuhReq, tbz: I.tbz, tbzReq: I.tbzReq, tFlex: I.tFlex, tFlexB: I.tFlexB, mSS: I.mSS, mUH: I.mUH, mBz: I.mBz, delta: I.delta, q: I.q, qAvg: I.qAvg },
    q_max: R.q_max, q_avg: R.q_avg, Ri: R.Ri, Ro: R.Ro,
    giro: R.cd ? { FS: R.cd.FS, p: R.cd.p, F: R.cd.F, mu: R.cd.mu } : null,
    veredicto: A.verdict, gobernante: brief(gov), gobernante_resistencia: brief(govRes), top5,
    conteo: { ok: ck.filter((c) => c.st === "ok").length, warn: ck.filter((c) => c.st === "warn").length, fail: ck.filter((c) => c.st === "fail").length, pend: ck.filter((c) => c.st === "pend").length, info: ck.filter((c) => c.st === "info").length, total: ck.length },
    avisos: ck.filter((c) => c.st === "warn" || c.st === "pend" || c.st === "fail").map(brief),
    topes: (I.topes || []).map((s) => ({ id: s.id, pieza: s.pieza, n: s.n, t: s.t, tResp: s.tResp, L: s.L, Lreq: s.Lreq, F: s.F, adm: s.adm, h_barra: s.h_barra, h_c: s.h_c, h_c_min: s.h_c_min, tol_hc: s.tol_hc, z: s.z, w_tope: s.w_tope, b_tope: s.b_tope, uh: s.uh, m_barras: s.m_barras })),
    topes_checks: ck.filter((c) => /^Interfaz (inox|bronce)$/.test(c.grp) && /tope/i.test(c.name) && c.kind !== "info" && c.st !== "pend").map(brief),
    cortes: (I.cortes || []).map((c) => ({ id: c.id, pieza: c.pieza, j: c.j, strip: !!c.strip, n: c.n })),
    hub: R.hubG, collar: byGrp(/^Pivote$/).filter((c) => /ollar|Rebaje|R_i|buje/.test(c.name)).map(brief),
    orejas: byGrp(/^Orejas de izaje$/).map(brief),
    filetes: ck.filter((c) => /filete (m[ií]nimo|m[aá]ximo)/i.test(c.name)).map(brief),
    madera: a.wood ? { m_madera: R.m.wood, m_anillo: R.m.ring, t_ring: Pa.t_ring, t_wood: Pa.t_wood, checks: byGrp(/^Cubierta$/).map(brief) } : null,
  });
});
// escenario térmico de la cubierta de madera (la clave `termica` de export_design.js la deja sin madera)
out.termica_madera = TT.thermal(P, { alts: ["base"], wood: 1 }).alternativas.filter((x) => x.madera);
// Tapones de grafito (opción C): ideal frente a real, barridos de f_g, de (Ø, paso), de la franja de borde y de los tornillos, y patrón recomendado (TT.tapones)
out.tapones = TT.tapones(P);
// Cota de viabilidad de bz_fg_min: patrón de perforaciones minúsculas (Ø5,5 · paso 10) que llegaría al f_g mínimo con η = bz_eta_min; mismo núcleo (TT.analyze, cuenta real)
out.tapones.patron_minusculo = [[1, "C1"], [3, "C3"]].map(([conf, id]) => {
  const Pm = Object.assign({}, P, { opt_ss: 0, opt_uhmw: 0, opt_bz: 1, bz_conf: conf, bz_plug_d: 5.5, bz_plug_p: 10 }), A = TT.analyze(Pm, { noFEA: true }), I = A.R.ifc;
  return { id, d: Pm.bz_plug_d, p: Pm.bz_plug_p, eta: I.eta, N: I.Nreal, fg: I.fgReal, cumple_fg: I.fgReal >= P.bz_fg_min - 1e-12, estructura: A.verdict.estructura, gira: A.verdict.gira };
});
// Empates geométricos del conteo (hallazgo G2 de la réplica): un tapón con su borde a exactamente bz_edge cumple «≥ bz_edge»; si N cambia con ±1e-6 mm, el conteo depende de la coma flotante
{
  const Nat = (conf, d, p, e) => TT.analyze(Object.assign({}, P, { opt_ss: 0, opt_uhmw: 0, opt_bz: 1, bz_conf: conf, bz_plug_d: d, bz_plug_p: p, bz_edge: e }), { noFEA: true }).R.ifc.Nreal;
  const eps = 1e-6, ej = [];
  let tot = 0;
  [1, 3].forEach((conf) => out.tapones.barridos.d.forEach((d) => out.tapones.barridos.p.forEach((p) => {
    tot++; const a = Nat(conf, d, p, P.bz_edge - eps), b = Nat(conf, d, p, P.bz_edge + eps);
    if (a !== b) ej.push({ conf, d, p, N_con_empate: a, N_sin_empate: b, dif_pct: (a / b - 1) * 100 });
  })));
  const act = [1, 3].map((conf) => ({ conf, N_menos: Nat(conf, P.bz_plug_d, P.bz_plug_p, P.bz_edge - eps), N_mas: Nat(conf, P.bz_plug_d, P.bz_plug_p, P.bz_edge + eps) }));
  out.tapones.empates = { eps, n_patrones: tot, n_con_empate: ej.length, max_dif_pct: ej.reduce((m, x) => Math.max(m, Math.abs(x.dif_pct)), 0), ejemplos: ej.slice(0, 6), patron_actual: act };
}
// Modos de accionamiento (Tarea 1: leva de reenganche del modo guiado; Tarea 2: pivotado tipo KIET) para cada alternativa de interfaz: mismo núcleo (TT.analyze)
out.modos_accionamiento = ALTS.map((a) => ({ id: a.id, nombre: a.nombre, modos: [1, 2].map((dm) => {
  const Pa = Object.assign({}, P, { opt_ss: 0, opt_uhmw: 0, opt_bz: 0, bz_conf: 1 }, a.flags, { opt_wood: a.wood, drive_mode: dm }), A = TT.analyze(Pa, { noFEA: true }), R = A.R, K = R.K;
  const est = A.checks.filter((c) => c.kind === "fu" && c.sys === "est" && isFinite(c.fu)), gov = est.reduce((b, c) => (!b || c.fu > b.fu ? c : b), null);
  return { drive_mode: dm, familia_leva: R.fam.f, masa: R.m.total, masas: { brackets: R.m.brackets, dogs: R.m.dogs, shoes: R.m.shoes, beds: R.m.beds, cam: R.m.cam }, F_dis: R.cd ? R.cd.F : null, p_dis: R.cd ? R.cd.p : null, FS: R.cd ? R.cd.FS : null,
    brazo_min: K.armMin, brazo_ef_min: dm === 2 ? K.aEffMin : null, carrera_req: K.s_req, sincronia: dm === 1 ? (R.camG ? R.camG.sync : null) : (R.camP ? R.camP.sync : null), veredicto: A.verdict, gobernante: brief(gov),
    fallas: A.checks.filter((c) => c.st === "fail").map(brief) };
}) }));
// Parámetros añadidos en la v1.2 (definición del núcleo: etiqueta, unidad, valor por defecto, mínimo, máximo)
const NEW_IDS = ["term_alcance", "bz_fg_modo", "bz_edge", "bz_fg_min", "bz_fg_estricto", "bz_eta_min", "bz_n_tor", "d_tor"];
const allP = TT.PARAM_GROUPS.reduce((a, g) => a.concat(g.p), []);
out.parametros_v12 = NEW_IDS.map((id) => { const q = allP.find((x) => x[0] === id); return { id, lab: q[1], u: q[2], def: q[3], min: q[4], max: q[5], valor: P[id] }; });
// Medidas recomendadas del alcance 1 (placas y disco), cuantificadas con el mismo núcleo (T de escenario = 80 °C): junta en frío de los sectores j_sec ≥ junta requerida de la lámina UHMW (B),
// plancha inferior y gradiente de C3. El circuito hidráulico y el accionamiento quedan fuera del alcance (term_alcance = 1): sus filas se informan aparte en `fuera_alcance`, sin medida asociada.
const Tsc = 80, t80 = (Pp, alt) => TT.thermal(Pp, { alts: [alt], T: [20, Tsc] }).alternativas[0];
const resumen = (a) => { const b = a.byT[1]; return { FS: b.FS, gira: b.gira, estructura: b.estructura, termico: b.termico, fuEst: b.fuEst, gobernante: b.gobernante, fuTerm: b.fuTerm, gobernanteTerm: b.gobernanteTerm, nFail: b.nFail, nWarn: b.nWarn }; };
const fb = t80(P, "base").byT[1].fuera_alcance;
const porGrupo = []; fb.forEach((f) => { let g = porGrupo.find((x) => x.grp === f.grp); if (!g) porGrupo.push(g = { grp: f.grp, n: 0, fail: 0, warn: 0 }); g.n++; if (f.estado_informativo === "fail") g.fail++; if (f.estado_informativo === "warn") g.warn++; });
const fueraAlcance = { alcance: P.term_alcance, n: fb.length, fail: fb.filter((f) => f.estado_informativo === "fail").length, warn: fb.filter((f) => f.estado_informativo === "warn").length, por_grupo: porGrupo,
  filas_aviso: fb.filter((f) => f.estado_informativo === "fail" || f.estado_informativo === "warn").map((f) => ({ grp: f.grp, nombre: f.nombre, dem: f.dem, cap: f.cap, unidad: f.unidad, fu: f.fu, estado_informativo: f.estado_informativo, ref: f.ref })) };
const jB = (t80(P, "B").juntas.find((j) => /UHMW/.test(j.pieza)) || {}).j_req;
const jNew = jB ? Math.ceil(jB * 10 - 1e-9) / 10 : null;
const aJ = jNew ? t80(Object.assign({}, P, { j_sec: jNew }), "B") : null;
const tBots = [P.t_bot, P.t_bot + 2, P.t_bot + 4].map((tb) => { const a = t80(Object.assign({}, P, { t_bot: tb }), "C3"); return Object.assign({ t_bot: tb, masa20: a.geometria.masa20 }, resumen(a)); });
const grads = [0, 5, 10, 15].map((g) => { const a = TT.thermal(P, { alts: ["base", "C3"], gradient: g, T: [20, Tsc] }).alternativas; const o = {}; a.forEach((x) => { o[x.id] = resumen(x); }); return { gradiente: g, alts: o }; });
const vg68 = TT.oilViscosity(Tsc);
out.medidas = { c3_t_bot: tBots, gradiente: grads, viscosidad: vg68, fuera_alcance: fueraAlcance, p_max_cil: P.p_max_cil, p_relief: P.p_relief,
  junta_B: aJ ? { j_req: jB, j_sec_actual: P.j_sec, j_sec_nuevo: jNew, juntas: aJ.juntas, masa20: aJ.geometria.masa20, masa20_actual: t80(P, "B").geometria.masa20, resumen: resumen(aJ) } : null };
process.stdout.write(JSON.stringify(out, null, 1));
