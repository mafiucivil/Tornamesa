/* Exporta, para la memoria de cálculo, el análisis completo de cada alternativa de interfaz (base, A, B, C1, C2, C3)
   y los tapones de grafito de la opción C (TT.tapones: cantidad real frente a ideal),
   las medidas recomendadas del escenario solar (alcance placas y disco, term_alcance = 1) y la nota informativa del accionamiento fuera de alcance.
   Fuente única: TT.analyze / TT.thermal / TT.tapones; la memoria solo redacta.
   Uso: node tools/export_alternativas.js [parametros.json] > cad/out/TT300-C_alternativas.json */
const fs = require("fs");
const TT = require("../packages/core/tt300c.js");
const P = Object.assign(TT.defaults(), process.argv[2] ? JSON.parse(fs.readFileSync(process.argv[2], "utf8")) : {});
const brief = (c) => (c ? { grp: c.grp, nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref } : null);
// Cubierta de madera W: EN STAND BY por decisión del mandante (09-11-2026; docs/standby/madera_W/LEEME.md). No entra a la entrega RevC; TT_CON_MADERA=1 la vuelve a exportar.
const CON_W = process.env.TT_CON_MADERA === "1";
const ALTS = TT.TH_ALTS.map(([id, nombre, flags]) => ({ id, nombre, flags, wood: 0 })).concat(CON_W ? [{ id: "W", nombre: "Base + cubierta de madera W (plancha rebajada)", flags: {}, wood: 1 }] : []);
const out = { version: 1, madera_W: CON_W ? "incluida" : "stand by (docs/standby/madera_W/LEEME.md)",
  P_ref: { hc_min: P.hc_min, tol_hc: P.tol_hc, m_ri: P.m_ri, R_ear: P.R_ear, d_ear: P.d_ear, t_wood: P.t_wood, j_sec: P.j_sec }, alternativas: [] };
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
    madera: a.wood ? { m_madera: R.m.wood, m_anillo: R.m.ring, t_wood: Pa.t_wood, checks: byGrp(/^Cubierta$/).map(brief) } : null,
  });
});
// escenario térmico de la cubierta de madera (solo con TT_CON_MADERA=1; la clave `termica` de export_design.js la deja sin madera)
out.termica_madera = CON_W ? TT.thermal(P, { alts: ["base"], wood: 1 }).alternativas.filter((x) => x.madera) : [];
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
// Accionamiento (decisiones del mandante del 08-11-2026): pivotado tipo KIET por defecto (drive_mode = 2) y guiado con leva de reenganche positiva como alternativa
// (drive_mode = 1, opt_cam = 1); familias del material del contacto seguidor–placa-leva; base de 2.760 mm como alternativa a las holguras; AF2 (tornillos avellanados disco–mesa).
{
  const casosOf = (R) => R.cases.map((c) => ({ id: c.id, nombre: c.name, mu: c.mu, r: c.r, T: c.T, F: c.F, p: c.p, FS: c.FS, gira: c.turns }));
  const govOf = (A, sysEst) => A.checks.filter((c) => c.kind !== "info" && c.fu != null && isFinite(c.fu) && c.st !== "pend" && (!sysEst || (c.kind === "fu" && c.sys === "est"))).reduce((b, c) => (!b || c.fu > b.fu ? c : b), null);
  const modo = (Pm) => {
    const A = TT.analyze(Pm), R = A.R, K = R.K, DRV = TT.designDrive(Pm, R), dm = TT.driveMode(Pm);
    const row = (re) => brief(A.checks.find((c) => re.test(c.name)));
    let radial = null;
    if (dm === 1) {   // guiado: componente radial por cilindro en el pasador a lo largo de la carrera (caso de diseño); el par simétrico la anula en el pivote
      const fr = R.stroke.map((q) => q.Fp * Math.sin(q.th) + q.H * Math.cos(q.th));
      radial = { por_cilindro_dis: Math.max(...fr.map(Math.abs)), por_cilindro_calado: null, neta: row(/^Empuje neto al pivote/) };
    } else {
      const r = row(/^Pivotado: componente radial/);
      radial = { por_cilindro_dis: r.dem, por_cilindro_calado: r.cap, neta: row(/^Empuje neto al pivote/) };
    }
    const carrera = dm === 1 ? (() => {
      const st = R.stroke, thX = Math.asin(Pm.d_pin / 2 / Pm.R_pin), pick = [["Inicio (toma)", st[0]]];
      const xs = st.filter((q) => Math.abs(q.th - thX) < 1e-12);
      if (xs.length === 2) { pick.push(["Cambio de sentido de la fricción (antes)", xs[0]]); pick.push(["Cambio de sentido de la fricción (después)", xs[1]]); }
      pick.push(["Final", st[st.length - 1]]);
      return pick.map(([pos, q]) => ({ pos, th: q.th * 180 / Math.PI, s: q.s, F: q.F, p: q.F * 1e3 / R.A * 10, Fpin: q.Fp, H: q.H, Ft: q.Fp * Math.cos(q.th) - q.H * Math.sin(q.th), Fr: q.Fp * Math.sin(q.th) + q.H * Math.cos(q.th), Rf: q.Rf, Rr: q.Rr }));
    })() : null;
    const lg = DRV.levaGuiada ? Object.assign({}, DRV.levaGuiada, { fabricacion: undefined }) : null;
    return { drive_mode: dm, modo_nombre: DRV.modo_nombre, masa: R.m.total, masas: R.m, masas_desc: DRV.masas_desc, casos: casosOf(R), cd: { F: R.cd.F, p: R.cd.p, FS: R.cd.FS, T: R.cd.T },
      K: dm === 1 ? { armMin: K.armMin, armMax: K.armMax, s_req: K.s_req, margin: K.margin, chord: K.chord, DeltaMax: K.DeltaMax, L_s: K.L_s, Lg: K.Lg, travel: K.travel } : { armMin: K.armMin, armMax: K.armMax, aEffMin: K.aEffMin, s_req: K.s_req, margin: K.margin, chord: K.chord },
      Kguide: R.Kguide, Rguide: R.Rguide, chaflan: TT.chamferGeo(Pm), familia: { f: R.fam.f, nombre: R.fam.nombre, mu: R.fam.mu, auto: R.fam.auto }, veredicto: A.verdict,
      gobernante: brief(govOf(A, false)), gobernante_resistencia: brief(govOf(A, true)), radial, carrera, levaGuiada: lg,
      verificaciones: A.checks.map(brief), stroke: Pm.stroke,
      P: { s_free: Pm.s_free, c_lug: Pm.c_lug, B: Pm.B, opt_cam: Pm.opt_cam, cam_mat: Pm.cam_mat } };
  };
  const Pp = Object.assign({}, P, { drive_mode: 2 }), Pg = Object.assign({}, P, { drive_mode: 1, opt_cam: 1 });
  const piv = modo(Pp), gui = modo(Pg);
  // familias del contacto seguidor–placa-leva en el modo pivotado (cam_mat = 1…4) y regla automática por interfaz
  const familias = [1, 2, 3, 4].map((cm) => {
    const A = TT.analyze(Object.assign({}, Pp, { cam_mat: cm }), { noFEA: true }), R = A.R;
    return { cam_mat: cm, nombre: R.fam.nombre, corto: R.fam.corto, mu: R.fam.mu, muRef: R.fam.muRef, pRef: R.fam.pRef, tipo: R.fam.tipo, pAdm: R.fam.pAdm, PV: R.fam.PV, masa: R.m.total, FS: R.cd.FS, F: R.cd.F, veredicto: A.verdict,
      filas: A.checks.filter((c) => c.grp === "Placas-leva" || /Rampa de la placa-leva/.test(c.name)).map(brief), fallas: A.checks.filter((c) => c.st === "fail").map(brief) };
  });
  const auto = TT.TH_ALTS.map(([id, nombre, flags]) => { const R = TT.analyze(Object.assign({}, Pp, { opt_ss: 0, opt_uhmw: 0, opt_bz: 0, bz_conf: 1, cam_mat: 0 }, flags), { noFEA: true }).R; return { id, nombre, f: R.fam.f, familia: R.fam.nombre }; });
  // holguras «cajón del ojal E dentro de la base» y «Q fuera de la mesa»: base adoptada (B = 2.560, aceptada por el mandante) frente a B = 2.760 con la sugerencia de E a FU 0,95
  const hol = (Pm) => { const A = TT.analyze(Pm, { noFEA: true }), R = A.R, K = R.K, f = (re) => brief(A.checks.find((c) => re.test(c.name)));
    return { B: Pm.B, R_E: Math.hypot(K.E[0], K.E[1]), L_qp: K.Lqp, fugeo: Pm.pv_fugeo, cajon: f(/^Soporte del ojal E dentro de la base/), Q: f(/^Pasador Q fuera de la mesa/), FS: R.cd.FS, masa: R.m.total, veredicto: A.verdict }; };
  const h0 = hol(Pp), h1 = hol(Object.assign({}, Pp, { B: 2760, pv_fugeo: 0.95, pv_RE: 0, pv_Lqp: 0 }));
  // AF2: opción A pegada (fix_mode = 2) con tornillos avellanados ISO 10642 del disco de la mesa a la plancha inferior
  const Pa = Object.assign({}, Pp, { opt_ss: 1, opt_uhmw: 0, opt_bz: 0, fix_mode: 2 }), Aa = TT.analyze(Pa, { noFEA: true }), Ra = Aa.R, Da = TT.designDrive(Pa, Ra);
  const tor = Object.assign({}, Da.tornillos_interfaz); delete tor.posiciones;
  const af2 = { tornillos: tor, filas: Aa.checks.filter((c) => /^AF2/.test(c.name)).map(brief), tss: Ra.ifc.tss, tss2: Ra.ifc.tss2, tssReq: Ra.ifc.tssReq, tss2Req: Ra.ifc.tss2Req, masa: Ra.m.total, veredicto: Aa.verdict, t_bot: Pa.t_bot,
    ss_allow: Pa.ss_allow, ss_tmin: Pa.ss_tmin, FS: Ra.cd.FS };
  const lab = (id) => { const q = TT.PARAM_GROUPS.reduce((a, g) => a.concat(g.p), []).find((x) => x[0] === id); return q ? q[1] : null; };
  out.accionamiento = { pivotado: piv, guiado: gui, familias, familias_auto: auto, holguras: { adoptada: h0, B2760: h1 }, af2, etiquetas: { s_free: lab("s_free"), c_lug: lab("c_lug"), drive_mode: lab("drive_mode"), cam_mat: lab("cam_mat") } };
}
// Plancha base: base de t_base con inserto de esquina bajo cada soporte del cilindro (decisión del mandante 10-11-2026; registro, «Plancha base: base de 20 mm con inserto de esquina (10-11-2026)»).
// Por modo e interfaz: inserto exportado por el núcleo (TT.designDrive; sin los polígonos del rebaje), filas «Plancha base bajo …», masas y veredicto (TT.analyze completo).
// «antes»: el diseño de la memoria anterior (base de 18 mm sin inserto, ins_on = 0), con el mismo núcleo, para el cambio de masa.
{
  const sinPoligonos = (I) => {
    if (!I) return null;
    const o = Object.assign({}, I); delete o.poligono;   // «esquinas» y «esquinas_espesor_pleno» quedan (figura de 7.10); «poligono» las repite
    if (o.rebaje) { o.rebaje = Object.assign({}, o.rebaje); delete o.rebaje.poligonos; }
    return o;
  };
  const mas = (R) => ({ total: R.m.total, base: R.m.base, rim: R.m.rim, brackets: R.m.brackets, insertos: R.m.insertos, insBrackets: R.m.insBrackets, insRim: R.m.insRim });
  const modelo = (id, nombre, over) => {
    const Pm = Object.assign({}, P, { opt_ss: 0, opt_uhmw: 0, opt_bz: 0, bz_conf: 1 }, over), A = TT.analyze(Pm), R = A.R, DRV = TT.designDrive(Pm, R), dm = TT.driveMode(Pm);
    const I = dm === 2 ? DRV.pivotado.fabricacion.soporte_E.inserto : (DRV.levaGuiada && DRV.levaGuiada.fabricacion ? DRV.levaGuiada.fabricacion.inserto : null);
    // piezas soldadas sobre el inserto (núcleo f2dc2b5): pasador E sobre la cara del inserto (pivotado), mejillas de la ménsula corridas (guiado), pie de las orejas de la diagonal
    const pE = dm === 2 ? Object.assign({}, DRV.pivotado.fabricacion.pasador_E) : null;
    const mens = dm === 1 && DRV.levaGuiada && DRV.levaGuiada.fabricacion && DRV.levaGuiada.fabricacion.mensula ? Object.assign({}, DRV.levaGuiada.fabricacion.mensula) : null;
    if (mens) delete mens.huellas;
    return { id, nombre, drive_mode: dm, over, t_base: Pm.t_base, ins_on: Pm.ins_on, ins_fsv: Pm.ins_fsv, inserto: sinPoligonos(I), pasador_E: pE, mensula: mens,
      filas: A.checks.filter((c) => /^Plancha base bajo/.test(c.name)).map(brief), masas: mas(R), veredicto: A.verdict,
      filas_sobre_inserto: A.checks.filter((c) => /^Pasador vertical E: extremo inferior sobre la cara del inserto|^Oreja: pie sobre el espesor pleno del inserto/.test(c.name)).map(brief),
      izaje: A.checks.filter((c) => c.grp === "Base" && /izaje/i.test(c.name)).map(brief) };
  };
  const PIVM = [["base", "Pivotado, interfaz base (por defecto)", {}], ["A", "Pivotado, interfaz A", { opt_ss: 1 }], ["AF2", "Pivotado, interfaz A pegada (AF2)", { opt_ss: 1, fix_mode: 2 }], ["B", "Pivotado, interfaz B", { opt_uhmw: 1 }],
    ["C1", "Pivotado, interfaz C1", { opt_bz: 1, bz_conf: 1 }], ["C2", "Pivotado, interfaz C2", { opt_bz: 1, bz_conf: 2 }], ["C3", "Pivotado, interfaz C3", { opt_bz: 1, bz_conf: 3 }],
    ["G", "Guiado, interfaz base", { drive_mode: 1, opt_cam: 1 }], ["GA", "Guiado, interfaz A", { drive_mode: 1, opt_cam: 1, opt_ss: 1 }], ["GB", "Guiado, interfaz B", { drive_mode: 1, opt_cam: 1, opt_uhmw: 1 }]];
  const modelos = PIVM.map(([id, nombre, over]) => modelo(id, nombre, Object.assign({ drive_mode: 2 }, over)));
  const A0 = TT.analyze(Object.assign({}, P, { drive_mode: 2, ins_on: 0, t_base: 18 }), { noFEA: true });
  out.plancha_base = { modelos, antes: { descripcion: "base de 18 mm sin inserto (ins_on = 0), diseño de la memoria anterior", t_base: 18, ins_on: 0, masas: mas(A0.R), estado_global: A0.verdict.estado_global } };
}
// Parámetros del accionamiento (v1.5: modo, levas y pivotado), definición del núcleo
{
  const allP = TT.PARAM_GROUPS.reduce((a, g) => a.concat(g.p), []);
  out.parametros_accionamiento = allP.filter((q) => /^(drive_mode|cam_mat|opt_cam|cam_|pv_)/.test(q[0])).map((q) => ({ id: q[0], lab: q[1], u: q[2], def: q[3], min: q[4], max: q[5], valor: P[q[0]] }));
}
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
