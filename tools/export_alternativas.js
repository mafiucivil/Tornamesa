/* Exporta, para la memoria de cálculo, el análisis completo de cada alternativa de interfaz (base, A, B, C1, C2, C3 y cubierta de madera)
   más el escenario térmico de la cubierta de madera (TT.thermal con wood = 1). Fuente única: TT.analyze / TT.thermal; la memoria solo redacta.
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
// Medidas recomendadas, cuantificadas con el mismo núcleo (T de escenario = 80 °C): (1) válvula de alivio térmico en el tramo aislado; (2) junta en frío de los sectores j_sec ≥ junta requerida de la lámina UHMW (B)
const Tsc = 80, t80 = (Pp, alt) => TT.thermal(Pp, { alts: [alt], T: [20, Tsc] }).alternativas[0];
const oilRows = (a) => a.byT[1].filas.filter((r) => r.sub === "e").map((r) => ({ nombre: r.nombre, dem: r.dem, cap: r.cap == null ? null : r.cap, unidad: r.unidad, fu: r.fu, estado: r.estado }));
const resumen = (a) => { const b = a.byT[1]; return { FS: b.FS, gira: b.gira, estructura: b.estructura, termico: b.termico, fuEst: b.fuEst, gobernante: b.gobernante, fuTerm: b.fuTerm, gobernanteTerm: b.gobernanteTerm, nFail: b.nFail, nWarn: b.nWarn }; };
const altRelief = [0, P.p_max_cil].map((ar) => { const a = t80(Object.assign({}, P, { alivio_term: ar }), "base"); return { alivio_term: ar, filas: oilRows(a), resumen: resumen(a) }; });
const jB = (t80(P, "B").juntas.find((j) => /UHMW/.test(j.pieza)) || {}).j_req;
const jNew = jB ? Math.ceil(jB * 10 - 1e-9) / 10 : null;
const aJ = jNew ? t80(Object.assign({}, P, { j_sec: jNew }), "B") : null;
const tBots = [P.t_bot, P.t_bot + 2, P.t_bot + 4].map((tb) => { const a = t80(Object.assign({}, P, { t_bot: tb }), "C3"); return Object.assign({ t_bot: tb, masa20: a.geometria.masa20 }, resumen(a)); });
const grads = [0, 5, 10, 15].map((g) => { const a = TT.thermal(P, { alts: ["base", "C3"], gradient: g, T: [20, Tsc] }).alternativas; const o = {}; a.forEach((x) => { o[x.id] = resumen(x); }); return { gradiente: g, alts: o }; });
const vg68 = TT.oilViscosity(Tsc);
out.medidas = { c3_t_bot: tBots, gradiente: grads, viscosidad: vg68, alivio_termico: altRelief, p_max_cil: P.p_max_cil, p_relief: P.p_relief,
  junta_B: aJ ? { j_req: jB, j_sec_actual: P.j_sec, j_sec_nuevo: jNew, juntas: aJ.juntas, masa20: aJ.geometria.masa20, masa20_actual: t80(P, "B").geometria.masa20, resumen: resumen(aJ) } : null };
process.stdout.write(JSON.stringify(out, null, 1));
