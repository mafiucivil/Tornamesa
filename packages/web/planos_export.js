/* TT300-C · Exportación del paquete de dibujo (navegador y Node, sin dependencias).
   Genera, desde los parámetros P y los resultados del núcleo (TT, AG):
     · láminas DXF (R12, ASCII/ANSI_1252) con capas CONTORNO, OCULTO, EJES, COTAS, TEXTO, CAJETIN y ACHURADO;
     · las mismas láminas en SVG y una página HTML de impresión (@media print → PDF desde el navegador);
     · lista de materiales en CSV (masas del núcleo);
     · el JSON de diseño con el mismo esquema que tools/export_design.js (entrada del generador Python completo);
     · un ZIP (sin compresión) que reúne todo.
   Toda cota sale de P o de las funciones del núcleo; lo que el núcleo no define se dibuja como contorno y se rotula «A DEFINIR». */
const PLANOS = (() => {
  const TT_ = (typeof TT !== "undefined") ? TT : require("../core/tt300c.js");
  const AG_ = (typeof AG !== "undefined") ? AG : require("../agents/agentes.js");
  const RHO = 7.85e-6, D2R = Math.PI / 180;
  const ADVERTENCIA = "ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO.";
  const NOTAS = ["En caso de vientos fuertes no se recomienda realizar la operación.", "Equipo sin anclaje"];
  const REV = "B";

  /* ====================================================================== */
  /* 1. JSON de diseño (mismo esquema que tools/export_design.js)            */
  /* ====================================================================== */
  function buildDesign(Pin, Apre) {
    const P = Object.assign(TT_.defaults(), Pin || {});
    const val = AG_.validate(P);
    if (val.some((v) => v.lvl === "error")) { const e = new Error(val.filter((v) => v.lvl === "error").map((v) => v.msg).join("\n")); e.validation = val; throw e; }
    const A = Apre || TT_.analyze(P), R = A.R, K = R.K;
    const bg = TT_.bracketGeo(P);
    function cylPos(sx, dy) {
      const g = TT_.guideGeo(P), Rp = P.R_pin, ph = g.pitch / 2;
      const Y = (y) => dy * y, X = sx * P.x_g;
      const pin = (th) => [sx * Rp * Math.cos(th), dy * Rp * Math.sin(th)];
      return {
        side: sx, dir: dy, x: X, eye: [X, Y(g.y_eye)], phiMean: dy > 0 ? 90 : -90,
        rodRetracted: [X, Y(g.y_rp0)], rodEngage: [X, Y(g.y_rp0 + P.s_free)], rodEnd: [X, Y(g.y_rp1)],
        pinStart: pin(-ph), pinEnd: pin(ph), shoeFront: g.front, shoeRear: g.rear, mouthX: sx * g.mouthX,
      };
    }
    const ccw = [cylPos(1, 1), cylPos(-1, -1)], cw = [cylPos(1, -1), cylPos(-1, 1)];
    const DRV = TT_.designDrive(P, R);                                  // datos de dibujo del accionamiento (leva guiada, modo pivotado), como tools/export_design.js
    const out = {
      proyecto: "TT300-C", fecha: new Date().toISOString().slice(0, 10), P, modo: DRV.modo, modo_nombre: DRV.modo_nombre, levaGuiada: DRV.levaGuiada, pivotado: DRV.pivotado,
      verdict: A.verdict, validacion: val,
      derivados: {
        W: R.W, N: R.N, ND: R.ND, q_max: R.q_max, q_avg: R.q_avg, Fstall: R.Fstall, Falarm: R.Falarm, Fret: R.Fret, A: R.A, Aann: R.Aann,
        hax: R.hax, prIn: TT_.prIn(P), pinClear: TT_.pinClear(P), forkH: TT_.forkH(P), bracket: bg, tRev: R.tRev, tCycle: R.tCycle, muMax_ref: R.muMax(P.r_ef),
        Kguide: R.Kguide, Rguide: R.Rguide, stallMax: R.stallMax, chaflan: TT_.chamferGeo(P),
        K: { armMin: K.armMin, armMax: K.armMax, s_req: K.s_req, margin: K.margin, chord: K.chord, gap: K.gap, radial: K.radial, DeltaMax: K.DeltaMax,
             L_s: K.L_s, Lg: K.Lg, front: K.front, rear: K.rear, y_eye: K.y_eye, y_rp0: K.y_rp0, y_rp1: K.y_rp1, L_bed: K.L_bed, Y_bed: K.Y_bed, zc0: K.zc0, lever: K.lever, mouthX: K.mouthX, inset: K.inset, tipX: K.tipX, travel: K.travel, pocketEnd: K.pocketEnd, shoeTop: K.shoeTop },
        casos: R.cases.map((c) => ({ id: c.id, nombre: c.name, mu: c.mu, r: c.r, T: c.T, F: c.F, p: c.p, FS: c.FS, gira: c.turns })),
        masas: R.m, masas_desc: DRV.masas_desc,
      },
      pasadores: Array.from({ length: P.N_pin }, (_, k) => (180 / P.N_pin + 360 * k / P.N_pin)),
      nervios: Array.from({ length: P.N_rib }, (_, k) => 360 * k / P.N_rib),
      almas: TT_.parseRings(P.rings),
      cilindros: { horario: cw, antihorario: ccw },
      grupos: TT_.PARAM_GROUPS.map((g) => ({ id: g.id, titulo: g.t, p: g.p.map(([id, lab, u]) => ({ id, lab, u })) })),
      apoyo: { r_u: R.r_u, Ro: R.Ro, Ri: R.Ri, Ac: R.Ac, T_piv_d: R.T_piv(R.mu.d), H_ecc_d: R.H_ecc(R.mu.d), mu: R.mu, interfaz: R.ifc, Tmax: R.Tmax, q_min: R.q_min, Wd: R.Wd },
      carrera: (() => {
        const st = R.stroke, thX = Math.asin(P.d_pin / 2 / P.R_pin), pick = [];
        pick.push(["Inicio (toma)", st[0]]);
        const xs = st.filter((q) => Math.abs(q.th - thX) < 1e-12);
        if (xs.length === 2) { pick.push(["Cambio de sentido de la fricción (antes)", xs[0]]); pick.push(["Cambio de sentido de la fricción (después)", xs[1]]); }
        pick.push(["Final", st[st.length - 1]]);
        return pick.map(([pos, q]) => ({ pos, th: q.th / D2R, s: q.s, arm: P.R_pin * Math.cos(q.th), Delta: P.x_g - P.R_pin * Math.cos(q.th), F: q.F, p: q.F * 1e3 / R.A * 10,
          Fpin: q.Fp, H: q.H, Ft: q.Fp * Math.cos(q.th) - q.H * Math.sin(q.th), Fr: q.Fp * Math.sin(q.th) + q.H * Math.cos(q.th), Rf: q.Rf, Rr: q.Rr }));
      })(),
      escenarios: (() => { const sc = AG_.scenarios(A); return { mus: sc.mus, rs: sc.rs, grid: sc.grid, loads: sc.loads, classes: sc.classes, ifaces: sc.ifaces }; })(),
      interfazChecks: (() => { const chk = (k) => TT_.analyze(Object.assign({}, P, { opt_ss: k === 1 ? 1 : 0, opt_uhmw: k === 2 ? 1 : 0, opt_bz: k === 3 ? 1 : 0 }), { noFEA: true }).checks.filter((c) => c.grp === (k === 3 ? "Interfaz bronce" : "Interfaz inox"))
        .map((c) => ({ nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref })); return { A: chk(1), B: chk(2), C: chk(3) }; })(),
      bombaBarrido: [[1.8, 0], [5, 0], [10, 0], [10, 20], [20, 0]].map(([q, qr]) => { const RR = TT_.compute(Object.assign({}, P, { Q_pump: q, Q_ret: qr })); return { Q: q, Qr: RR.pump.Qr, tRev: RR.tRev, tCycle: RR.tCycle, Pmotor: RR.pump.Pmotor, vRet: RR.pump.vRet }; }),
      cubierta: (() => { const A1 = TT_.analyze(Object.assign({}, P, { opt_wood: 1, opt_bz: 0 }), { noFEA: true }), A0 = TT_.analyze(Object.assign({}, P, { opt_wood: 0 }), { noFEA: true });
        return { dMasa: A1.R.m.total - A0.R.m.total, mWood: A1.R.m.wood, checks: A1.checks.filter((c) => c.grp === "Cubierta").map((c) => ({ nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref })) }; })(),
      mercado: TT_.market(P), capCil: TT_.capacityByCyl(P, [1, 2]), bomba: R.pump,
      revisionCruzada: AG_.crossCheck(A),
      auditoria: AG_.audit(A.checks),
      // Geometría de la interfaz que el núcleo calcula pero no entrega como parámetro (la geometría de los topes sale de R.ifc.topes; el resto, de sus propias verificaciones, sin recalcular)
      interfazGeom: (() => {
        const ck = A.checks, byName = (re) => ck.filter((c) => re.test(c.name));
        const topes = (R.ifc.topes || []).map((s) => Object.assign({}, s));   // geometría resuelta de cada tope (núcleo: stopsOf), también la lámina UHMW en B: pieza, n, t, L, Lav, F, a_sup, a_inf, h_barra, h_c, z, w_tope, b_tope, w_min, capas, m_barra, m_barras
        const juntas = byName(/(crecimiento por dilatación de la cuerda|junta de dilatación entre sectores)/).map((c) => ({ pieza: c.name.split(":")[0], j: c.dem }));
        const tap = byName(/Tapones de grafito: profundidad restante/)[0];
        const sector = byName(/masa del sector/).map((c) => ({ pieza: c.name.split(":")[0], m: c.dem }));
        const ifc = R.ifc;
        // 4.ª pasada: material descontado de las coronas (R.ifc.cortes: junta, muesca y chaflán por sector, masa bruta/descontada/neta), juntas efectivas y anillo de acero de la madera
    const cortes = (R.ifc.cortes || []).map((c) => Object.assign({}, c)), jS = cortes.filter((c) => !c.strip).map((c) => c.j), jU = cortes.filter((c) => c.strip).map((c) => c.j);
    const anillo = null;   // cubierta W (08-11-2026): sin anillo de contención 10×50; la geometría del rebaje va en la clave «madera»
    // Tapones de grafito (opción C): cantidad real colocable y fracciones real/ideal (R.ifc.tap; conciliado con el patrón S09 del dibujante), null sin la opción C
    const tapones = ifc.tap ? { conf: ifc.conf, N_real: ifc.Nreal, N_ideal: ifc.Nideal, fg_real: ifc.fgReal, fg_ideal: ifc.fgIdeal, fg_usado: ifc.fgUsed, modo: P.bz_fg_modo, cobertura: ifc.cobGrafito, cobertura_ideal: ifc.cobGrafitoIdeal, cov: ifc.cov,
      d: ifc.tap.d, p: ifc.tap.p, eta: ifc.eta, bz_edge: ifc.tap.edge, n_sectores: ifc.tap.n, junta: ifc.tap.junta, L_muesca: ifc.tap.L, radios_tornillos: ifc.tap.radios, n_tornillos_sector: ifc.tap.radios.length ? (ifc.tap.nTor >= 4 ? 4 : 2) : 0, d_cabeza: ifc.tap.dk,
      N_malla: ifc.tap.N_malla, perdidas: ifc.tap.perdidas, por_sector: ifc.tap.porSector, fg_min: P.bz_fg_min, cumple_lubricacion: ifc.fgUsed >= P.bz_fg_min - 1e-12 } : null;
    return { topes, juntas, tapon_prof_max: tap ? tap.cap : null, tapon_prof_frac: tap && ifc.tbz ? tap.cap / ifc.tbz : null, sector_masa: sector,
      cortes, junta_sector: jS.length ? Math.max(...jS) : null, junta_uhmw: jU.length ? Math.max(...jU) : null, j_sec: P.j_sec, tol_hc: P.tol_hc, anillo_madera: anillo, tapones,
          hole_top: P.D_piv + 80, d_bush: P.D_piv + 30,
          Ri: R.Ri, m_ri: P.m_ri, D_rebaje_bot: R.hubG.Drb, h_rebaje: R.hubG.hRaw, h_rebaje_plancha: R.hubG.hPl, h_rebaje_cubo: R.hubG.hHub,
          nota: "hole_top y d_bush reproducen las constantes de massesMesa() del núcleo (D_piv + 80 y D_piv + 30); Ri = radio interior efectivo del anillo de contacto (D_collar/2 + c_boss_r + m_ri con collar); D_rebaje_bot = Ø del agujero/rebaje del collar en la plancha inferior (D_collar + 2·c_boss_r); h_rebaje = h_collar − δ + c_boss_a desde la cara inferior de la mesa (negativo: sin rebaje), repartida en h_rebaje_plancha (t_bot) y h_rebaje_cubo; cortes = por pieza de la interfaz, volumen por sector de junta (o franja libre en la lámina UHMW), muesca (b_tope + 2)·L·t y chaflán a_inf²·L, y masa bruta/descontada/neta (m_neta es la que suma a la masa total); junta_sector y junta_uhmw = junta en frío efectiva en mm (mayor entre j_sec y la dilatación, a 0,1 mm); anillo_madera = null (la cubierta W no tiene anillo de contención; ver la clave «madera»)" };
      })(),
      // Cubierta de madera W (rebaje): geometría de fabricación (anillo, pared, plancha rebajada, almas recortadas, tablones, abertura, fijación, soldaduras) y FEA escalonado; null sin cubierta
      madera: TT_.designWood(P, A),
      verificaciones: A.checks.map((c) => ({ grp: c.grp, nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref })),
      // Escenario térmico (exposición solar, registro.md «Temperatura (exposición solar, 80 °C)»): por alternativa y temperatura; geometría de 20 °C congelada; solo informativo (no entra en el veredicto)
      termica: TT_.thermal(P),
    };
    return out;
  }
  const designJSON = (D) => JSON.stringify(D, null, 1);

  /* ====================================================================== */
  /* 2. Contexto de cálculo: magnitudes derivadas del núcleo                  */
  /* ====================================================================== */
  const nf = (v, d) => { const s = (d == null ? String(+(+v).toFixed(1)) : (+v).toFixed(d)); return s.replace(".", ","); };
  const fmtDate = (iso) => { const [y, m, d] = iso.split("-"); return `${d}-${m}-${y}`; };
  function ifaceName(P, ifc) {
    if (ifc.o === 1) return "A: discos inoxidables con grasa";
    if (ifc.o === 2) return "B: discos inoxidables + lámina UHMW";
    if (ifc.o === 3) return "C: bronce con grafito" + (ifc.conf === 2 ? " (2 placas de bronce)" : ifc.conf === 3 ? " (pastillas)" : " + disco duro");
    return "Acero-acero con grasa grafitada";
  }
  function fixText(P, ifc) {
    if (!ifc.o) return "No aplica (sin discos de interfaz)";
    return P.fix_mode < 1.5 ? `Sectores desmontables con topes soldados (${P.n_sec} sectores)` : "Pegado permanente (no desmontable)";
  }
  const woodText = (P) => P.opt_wood > 0.5 ? `Madera dura t = ${nf(P.t_wood)} mm` : "Sin cubierta de madera";

  function ctxOf(P, A, fecha) {
    const R = A.R, ifc = R.ifc, tb = P.t_base, delta = ifc.delta;
    return {
      P, A, R, K: R.K, ifc, g: TT_.guideGeo(P), bg: TT_.bracketGeo(P), ch: TT_.chamferGeo(P), prIn: TT_.prIn(P), rings: TT_.parseRings(P.rings),
      // accionamiento: modo pivotado (pivotGeo/pivotAt al tomar el pasador, giro antihorario) o leva de reenganche del modo guiado (camGeo/camAt)
      piv: (TT_.driveMode ? TT_.driveMode(P) : P.drive_mode) === 2 && TT_.pivotGeo ? { g: TT_.pivotGeo(P), q: TT_.pivotAt(P, P.s_free, "empuje", "antihorario"), D: TT_.designDrive(P, R).pivotado } : null,
      cam: TT_.camGeo && TT_.camGeo(P) ? { g: TT_.camGeo(P), a: TT_.camAt(P, P.s_free, "empuje"), L: TT_.designDrive(P, R).levaGuiada } : null,
      tb, delta, tm: tb + delta, hw: P.h_disc - P.t_top - P.t_bot, tpr: Math.max(P.t_pr, P.t_top, P.t_bot), d_bush: P.D_piv + 30, hole_top: P.D_piv + 80,
      fecha: fecha || new Date().toISOString().slice(0, 10),
      stops: (A.checks || []).filter((c) => /largo del tope frente al canto/.test(c.name)).map((c) => ({ nombre: c.name.replace(/: largo del tope.*$/, ""), L: c.dem })),
    };
  }

  /* ====================================================================== */
  /* 3. Lista de materiales con las masas del núcleo                         */
  /* ====================================================================== */
  const SUBS = [["BASE", "Base"], ["MESA", "Mesa giratoria"], ["INTER", "Interfaz de giro"], ["PIVOTE", "Pivote y collar"], ["IZAJE", "Orejas de izaje"], ["CIL", "Cilindros hidráulicos"]];
  function buildBOM(P, A) {
    const R = A.R, m = R.m, ifc = R.ifc, items = [], steel = `Acero ASTM A572 Gr.50 (Fy ${nf(P.Fy)} MPa)`;
    const cz = (id) => (ifc.cortes || []).find((c) => c.id === id);
    const add = (sub, pos, desc, mat, qty, mTot, nota) => items.push({ sub, pos, code: `TT300C-${sub}-${String(pos).padStart(2, "0")}-${REV}`, desc, mat, qty, mUnit: mTot / qty, mTot, nota: nota || "" });
    // Base
    const plate = RHO * (P.B * P.B - Math.PI / 4 * P.D_piv ** 2) * P.t_base;
    const collar = P.h_boss > 0 ? RHO * Math.PI / 4 * (P.D_boss ** 2 - P.D_piv ** 2) * P.h_boss : 0;
    const ears = 4 * RHO * (2 * P.R_ear * P.h_ear + Math.PI * P.R_ear ** 2 / 2 - Math.PI / 4 * P.d_ear ** 2) * P.t_ear;
    // accionamiento: guiado (bancada, ménsula, patín, uña y leva de reenganche) o pivotado tipo KIET (soporte del ojal E, bloque-uña, placas-leva); descripciones del núcleo (designDrive)
    const DRV = TT_.designDrive ? TT_.designDrive(P, R) : null, md = (DRV && DRV.masas_desc) || {}, piv = !!(DRV && DRV.modo === 2);
    // refuerzo cuadrado soldado sobre la base bajo cada soporte del cilindro (núcleo: pivotado.fabricacion.soporte_E.refuerzo / levaGuiada.fabricacion.refuerzo);
    // el núcleo lo suma a m.brackets: aquí va en su propia partida (BASE-08) y se descuenta del soporte, así la suma por subconjunto no cambia
    const INSf = DRV ? (piv ? ((DRV.pivotado || {}).fabricacion || {}).soporte_E : ((DRV.levaGuiada || {}).fabricacion || {})) : null, INSq = INSf && (INSf.refuerzo || INSf.inserto);
    const INS = INSq && INSq.cuadrado && Array.isArray(INSq.cuadrado.vertices) ? INSq : null, tB = INS ? INS.t_base : P.t_base, mIns = INS ? INS.masa_total : 0;
    const insTxt = INS ? " (el refuerzo cuadrado de la base va aparte: BASE-08)" : "";
    add("BASE", 1, `Plancha base ${nf(P.B)} x ${nf(P.B)} x ${nf(tB)} mm entera con agujero Ø${nf(P.D_piv)}`, steel, 1, plate);
    add("BASE", 2, `Marco perimetral ${nf(P.rim_t)} x ${nf(P.rim_h)} mm`, steel, 1, m.rim);
    if (INS) {
      const tp = INS.tapones || {}, at = INS.atiesadores;
      add("BASE", 8, `Refuerzo cuadrado soldado sobre la base ${nf(INS.lado)} x ${nf(INS.lado)} x t_d = ${nf(INS.t_d)} mm (cara superior a z = ${nf(INS.t)} mm), ${nf(tp.n_por_esquina || 0)} tapones Ø${nf(tp.d || 0)} por refuerzo`
        + (at ? `, atiesador tangencial ${nf(at.t)} x ${nf(at.h)} x ${nf(at.largo)} mm (${nf(at.masa, 1)} kg c/u)` : ", sin atiesador") + ` (${INS.n} x ${nf(INS.masa, 1)} kg = ${nf(INS.masa_total, 1)} kg)`,
        INS.material || steel, INS.n, mIns, "Tapones, filete en los bordes interiores y PJP en bisel en los exteriores (núcleo); masa del núcleo");
    }
    if (!piv) {
      add("BASE", 3, `Bancada ${nf(P.w_bed)} x ${nf(P.t_bed)} x ${nf(R.K.L_bed)} con ranura T de guía`, steel, P.n_cyl, m.beds);
      add("BASE", 4, "Ménsula de cilindro (2 mejillas + suplemento)" + insTxt, steel, P.n_br, m.brackets - mIns);
      add("BASE", 5, "Patín guiado con alojamiento de la uña", `Acero Fy ${nf(P.Fy_shoe)} MPa`, P.n_cyl, m.shoes);
      add("BASE", 6, `Uña de empuje ${nf(P.dog_b)} x ${nf(P.dog_h)} (cara plana con chaflán de retorno)`, `34CrNiMo6+QT (Fy ${nf(P.Fy_dog)} MPa)`, P.n_cyl, m.dogs);
    } else {
      add("BASE", 4, (md.brackets ? md.brackets.charAt(0).toUpperCase() + md.brackets.slice(1).replace(/, con su refuerzo de esquina soldado sobre la base/, "") : "Soporte del ojal E") + insTxt, steel, P.n_cyl, m.brackets - mIns);
      add("BASE", 6, md.dogs ? md.dogs.charAt(0).toUpperCase() + md.dogs.slice(1) : "Bloque-uña con pasador Q", `Acero Fy ${nf(P.Fy_dog)} MPa`, P.n_cyl, m.dogs);
    }
    if (m.cam > 0) add("BASE", 7, (md.cam ? md.cam.charAt(0).toUpperCase() + md.cam.slice(1) : "Leva de reenganche") + " (masa del núcleo)", steel, piv ? 4 : P.n_cyl, m.cam);
    // Mesa
    const rings = TT_.parseRings(P.rings);
    add("MESA", 1, `Plancha superior t = ${nf(P.t_top)} (anillo de pasadores t = ${nf(Math.max(P.t_pr, P.t_top))})`, steel, 1, m.top);
    add("MESA", 2, `Plancha inferior t = ${nf(P.t_bot)} (anillo de pasadores t = ${nf(Math.max(P.t_pr, P.t_bot))})`, steel, 1, m.bot);
    add("MESA", 3, `Almas anulares t = ${nf(P.t_web)} (radios ${rings.map((r) => nf(r)).join(", ")} mm)`, steel, 1, m.webs);
    add("MESA", 4, `Nervios radiales t = ${nf(P.t_rib)}`, steel, P.N_rib, m.ribs);
    add("MESA", 5, `Cubo Ø${nf(P.D_hub)}`, steel, 1, m.hub);
    const PE = DRV && DRV.pasadores_empuje, PEu = (PE && PE.union) || null;   // pasadores a ras del disco y soldados (núcleo: designDrive().pasadores_empuje); sin perno ni arandela
    add("MESA", 6, `Pasador de empuje Ø${nf(P.d_pin)} x ${nf(P.h_disc)}${PE ? `, a ras del disco y de la cara inferior, soldado a ambos anillos${PEu ? ` (PJP en bisel 45° S${nf(PEu.S)}/E${nf(PEu.E)}, esmerilada a ras)` : ""}` : ""}`, `34CrNiMo6+QT (Fy ${nf(P.Fy_pin)} MPa)`, P.N_pin, m.pins, PE ? "No reemplazable (soldado); sin perno ni arandela" : "");
    if (m.wood > 0) add("MESA", 7, `Cubierta de madera dura t = ${nf(P.t_wood)} (tablones: disposición A DEFINIR)`, `Madera dura ${nf(P.rho_wood)} kg/m3`, 1, m.wood, "Opcional");
    if (m.ring > 0) add("MESA", 8, `Anillo de acero de contención de la madera: pletina ${nf(P.t_ring)} x ${nf(P.t_wood)} rolada a Ø${nf(P.D_top)}`, steel, 1, m.ring, "Opcional; soldada a la plancha superior; en la masa total");
    // Interfaz
    const nS = P.fix_mode < 1.5 ? P.n_sec : 1, sect = P.fix_mode < 1.5 ? "sector" : "disco completo";
    if (ifc.o === 1 || ifc.o === 2) {
      const t1 = ifc.tss, t2 = ifc.tss2, c0 = cz("disc0"), c1 = cz("disc1");   // masa neta de cada disco (sin muescas, chaflanes ni juntas); con pegado, la corona entera repartida por espesor
      const mA = c0 ? c0.m_neta / c0.capas : m.ss * t1 / (t1 + t2), mB = c1 ? c1.m_neta : (c0 ? c0.m_neta / c0.capas : m.ss * t2 / (t1 + t2));
      add("INTER", 1, `Disco inoxidable de la base (liso) t = ${nf(t1)} (${sect})`, `Inox (Fy ${nf(P.Fy_ss)} MPa)`, nS, mA);
      add("INTER", 2, `Disco inoxidable de la mesa t = ${nf(t2)}${ifc.o === 1 ? " con ranuras de engrase" : ""} (${sect})`, `Inox (Fy ${nf(P.Fy_ss)} MPa)`, nS, mB);
      if (ifc.o === 2) add("INTER", 3, `Lámina UHMW t = ${nf(ifc.tuh)} (${P.n_seg} sectores)`, "UHMW-PE", P.fix_mode < 1.5 ? P.n_seg : 1, m.uhmw);
    } else if (ifc.o === 3) {
      const nB = ifc.conf === 3 ? P.bz_npad : nS, solid = ifc.conf === 2 ? (cz("bz1") ? cz("bz1").m_neta : ifc.A_ss * ifc.tss * P.rho_bz * 1e-6) : 0;
      add("INTER", 1, `${ifc.conf === 3 ? "Pastillas de bronce con tapones de grafito" : "Placa de bronce con tapones de grafito"} t = ${nf(ifc.tbz)}${P.h_gr > 0 ? " (ranuras de engrase)" : ""}`, `Bronce Fy ${nf(P.Fy_bz)} MPa + grafito`, P.fix_mode < 1.5 || ifc.conf === 3 ? nB : 1, m.bz - solid);
      if (ifc.conf === 2) add("INTER", 2, `2.ª placa de bronce t = ${nf(ifc.tss)} (${sect})`, `Bronce Fy ${nf(P.Fy_bz2)} MPa`, nS, solid);
      else add("INTER", 2, `Disco duro t = ${nf(ifc.tss)} (${sect})`, `17-4PH o inox nitrurado (Fy ${nf(P.Fy_cara)} MPa)`, nS, m.ss);
    }
    if (m.stopBars > 0) add("INTER", 4, `Barras de los topes soldados (${(ifc.topes || []).map((s) => `${nf(s.capas * s.n)} x ${nf(s.L)} x ${nf(s.b_tope)} x ${nf(s.h_barra)}`).join("; ")})`, (ifc.topes || []).some((s) => s.uh) ? `${steel}; barras del rebaje de la lámina UHMW en acero inoxidable (ρ 7,93)` : steel, ifc.topes.reduce((q, s) => q + s.capas * s.n, 0), m.stopBars, "Soldadas al respaldo (filete w_tope); suman a la masa total");
    // Pivote, orejas, cilindros
    add("PIVOTE", 1, `Pivote Ø${nf(P.D_piv)} x ${nf(P.t_base + ifc.delta + P.h_disc - P.t_top + 3)}`, `Acero Fy ${nf(P.Fy_piv)} MPa`, 1, m.pivot);
    if (collar > 0) add("PIVOTE", 2, `Collar de asiento Ø${nf(P.D_boss)}/Ø${nf(P.D_piv)} x ${nf(P.h_boss)} soldado a la base`, steel, 1, collar);
    add("IZAJE", 1, `Oreja de izaje, placa t = ${nf(P.t_ear)}, R${nf(P.R_ear)}, agujero Ø${nf(P.d_ear)}`, steel, 4, ears);
    add("CIL", 1, `Cilindro hidráulico Ø${nf(P.D_bore)}/Ø${nf(P.d_rod)}, carrera ${nf(P.stroke)} (comercial)`, "Comercial (catálogo)", P.n_cyl, m.cyl);
    const order = SUBS.map((s) => s[0]);
    items.sort((a, b) => order.indexOf(a.sub) - order.indexOf(b.sub) || a.pos - b.pos);
    const total = items.reduce((s, i) => s + i.mTot, 0);
    const bySub = {}; items.forEach((i) => { bySub[i.sub] = (bySub[i.sub] || 0) + i.mTot; });
    return { items, total, bySub, core: m.total, diffPct: (total - m.total) / m.total * 100 };
  }
  function bomCSV(B, P, A, fecha) {
    const q = (s) => /[;"\n]/.test(s) ? '"' + String(s).replace(/"/g, '""') + '"' : String(s), n3 = (v) => (+v).toFixed(3).replace(".", ",");
    const L = [["TT300-C · Lista de materiales · Rev. " + REV + " · " + fmtDate(fecha)].join(";"), ["Interfaz: " + ifaceName(P, A.R.ifc) + " · Fijación: " + fixText(P, A.R.ifc) + " · " + woodText(P)].join(";"),
      ["Código", "Subconjunto", "Pos.", "Descripción", "Material", "Cantidad", "Masa unitaria [kg]", "Masa total [kg]", "Observación"].join(";")];
    SUBS.forEach(([sub, nombre]) => {
      const it = B.items.filter((i) => i.sub === sub); if (!it.length) return;
      it.forEach((i) => L.push([i.code, nombre, i.pos, q(i.desc), q(i.mat), i.qty, n3(i.mUnit), n3(i.mTot), q(i.nota)].join(";")));
      L.push(["", nombre, "", "Subtotal", "", "", "", n3(B.bySub[sub]), ""].join(";"));
    });
    L.push(["", "", "", "MASA TOTAL", "", "", "", n3(B.total), ""].join(";"));
    L.push(["", "", "", "Masa total del núcleo de cálculo (R.m.total)", "", "", "", n3(B.core), "Diferencia: " + B.diffPct.toFixed(4).replace(".", ",") + " %"].join(";"));
    L.push(["Masas de acero con densidad 7850 kg/m3, sin soldadura ni pintura (agregar ≈ 2 %). No incluye bomba, mangueras ni plancha diamantada."].join(";"));
    L.push([ADVERTENCIA].join(";"));
    return "﻿" + L.join("\r\n") + "\r\n";
  }

  /* ====================================================================== */
  /* 4. Modelo de dibujo (entidades en mm de papel) y vistas                 */
  /* ====================================================================== */
  const LAYERS = [["CONTORNO", 7, "CONTINUOUS"], ["OCULTO", 7, "DASHED"], ["EJES", 1, "CENTER"], ["COTAS", 3, "CONTINUOUS"], ["TEXTO", 7, "CONTINUOUS"], ["CAJETIN", 7, "CONTINUOUS"], ["ACHURADO", 8, "CONTINUOUS"]];
  const TXTW = 0.62;                                              // ancho medio de carácter / altura (estimación para el ajuste a la hoja)
  function Dwg() { this.e = []; }
  Dwg.prototype = {
    line(x1, y1, x2, y2, l) { if (Math.hypot(x2 - x1, y2 - y1) > 1e-6) this.e.push({ t: "LINE", l: l || "CONTORNO", x1, y1, x2, y2 }); },
    poly(pts, closed, l) { if (pts.length > 1) this.e.push({ t: "POLY", l: l || "CONTORNO", pts, closed: !!closed }); },
    circle(cx, cy, r, l) { if (r > 1e-6) this.e.push({ t: "CIRCLE", l: l || "CONTORNO", cx, cy, r }); },
    arc(cx, cy, r, a0, a1, l) { if (r > 1e-6) this.e.push({ t: "ARC", l: l || "CONTORNO", cx, cy, r, a0, a1 }); },
    text(x, y, s, h, l, al, rot) { this.e.push({ t: "TEXT", l: l || "TEXTO", x, y, h: h || 2.5, s: String(s), al: al || "l", rot: rot || 0 }); },
    translate(dx, dy) {
      this.e.forEach((e) => {
        if (e.t === "LINE") { e.x1 += dx; e.x2 += dx; e.y1 += dy; e.y2 += dy; }
        else if (e.t === "POLY") e.pts = e.pts.map(([x, y]) => [x + dx, y + dy]);
        else { if (e.t === "TEXT") { e.x += dx; e.y += dy; } else { e.cx += dx; e.cy += dy; } }
      });
    },
    bbox() {
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      const pt = (x, y) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); };
      this.e.forEach((e) => {
        if (e.t === "LINE") { pt(e.x1, e.y1); pt(e.x2, e.y2); }
        else if (e.t === "POLY") e.pts.forEach(([x, y]) => pt(x, y));
        else if (e.t === "CIRCLE") { pt(e.cx - e.r, e.cy - e.r); pt(e.cx + e.r, e.cy + e.r); }
        else if (e.t === "ARC") { const n = 24; for (let i = 0; i <= n; i++) { const a = (e.a0 + (((e.a1 - e.a0) % 360) + 360) % 360 * i / n) * D2R; pt(e.cx + e.r * Math.cos(a), e.cy + e.r * Math.sin(a)); } }
        else { const w = e.s.length * TXTW * e.h, v = e.rot % 180 !== 0; const ax = e.al === "c" ? -w / 2 : e.al === "r" ? -w : 0; if (!v) { pt(e.x + ax, e.y); pt(e.x + ax + w, e.y + e.h); } else { pt(e.x - e.h, e.y + ax); pt(e.x, e.y + ax + w); } }
      });
      return [x0, y0, x1, y1];
    },
  };
  // Vista: coordenadas de modelo (mm reales) → papel (mm) con escala sc y origen (ox, oy)
  function View(d, ox, oy, sc) { this.d = d; this.ox = ox; this.oy = oy; this.sc = sc; }
  View.prototype = {
    X(x) { return this.ox + x * this.sc; }, Y(y) { return this.oy + y * this.sc; },
    line(x1, y1, x2, y2, l) { this.d.line(this.X(x1), this.Y(y1), this.X(x2), this.Y(y2), l); },
    poly(pts, closed, l) { this.d.poly(pts.map((p) => [this.X(p[0]), this.Y(p[1])]), closed, l); },
    rect(x0, y0, x1, y1, l) { this.poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], true, l); },
    circ(cx, cy, r, l) { this.d.circle(this.X(cx), this.Y(cy), r * this.sc, l); },
    arc(cx, cy, r, a0, a1, l) { this.d.arc(this.X(cx), this.Y(cy), r * this.sc, a0, a1, l); },
    text(x, y, s, h, l, al, rot) { this.d.text(this.X(x), this.Y(y), s, h, l, al, rot); },
    axes(x0, y0, x1, y1) { this.line(x0, y0, x1, y1, "EJES"); },
    cross(cx, cy, r) { this.line(cx - r, cy, cx + r, cy, "EJES"); this.line(cx, cy - r, cx, cy + r, "EJES"); },
    hatch(x0, y0, x1, y1, gap) {                                  // achurado a 45° de un rectángulo (en papel)
      const a = this.X(x0), b = this.Y(y0), c = this.X(x1), e = this.Y(y1), g = gap || 1.4;
      const xa = Math.min(a, c), xb = Math.max(a, c), ya = Math.min(b, e), yb = Math.max(b, e);
      if ((xb - xa) < 0.3 || (yb - ya) < 0.3) return;
      for (let k = xa - yb; k <= xb - ya; k += g * Math.SQRT2) {
        const xs = Math.max(xa, k + ya), xe = Math.min(xb, k + yb);
        if (xe - xs > 0.05) this.d.line(xs, xs - k, xe, xe - k, "ACHURADO");
      }
    },
    // cota alineada entre dos puntos del modelo; off = distancia de la línea de cota en mm de papel (signo = lado)
    dim(x1, y1, x2, y2, off, label) {
      const a = [this.X(x1), this.Y(y1)], b = [this.X(x2), this.Y(y2)], L = Math.hypot(b[0] - a[0], b[1] - a[1]); if (L < 1e-6) return;
      const ux = (b[0] - a[0]) / L, uy = (b[1] - a[1]) / L, nx = -uy, ny = ux, sg = off < 0 ? -1 : 1;
      const a2 = [a[0] + nx * off, a[1] + ny * off], b2 = [b[0] + nx * off, b[1] + ny * off], d = this.d;
      d.line(a[0] + nx * 1 * sg, a[1] + ny * 1 * sg, a2[0] + nx * 1.5 * sg, a2[1] + ny * 1.5 * sg, "COTAS");
      d.line(b[0] + nx * 1 * sg, b[1] + ny * 1 * sg, b2[0] + nx * 1.5 * sg, b2[1] + ny * 1.5 * sg, "COTAS");
      d.line(a2[0], a2[1], b2[0], b2[1], "COTAS");
      const ar = (p, s) => { const dx = ux * s * 2.6, dy = uy * s * 2.6; d.line(p[0], p[1], p[0] + dx + nx * 0.8, p[1] + dy + ny * 0.8, "COTAS"); d.line(p[0], p[1], p[0] + dx - nx * 0.8, p[1] + dy - ny * 0.8, "COTAS"); };
      ar(a2, 1); ar(b2, -1);
      let ang = Math.atan2(uy, ux) / D2R; if (ang > 90.001 || ang <= -89.999) ang += ang > 0 ? -180 : 180;
      const rr = ang * D2R, upx = -Math.sin(rr), upy = Math.cos(rr);
      d.text((a2[0] + b2[0]) / 2 + upx * 0.9, (a2[1] + b2[1]) / 2 + upy * 0.9, label != null ? label : nf(Math.hypot(x2 - x1, y2 - y1) ), 2.5, "COTAS", "c", Math.abs(ang) < 0.001 ? 0 : ang);
    },
    // cota horizontal / vertical entre coordenadas del modelo
    dimH(x1, x2, y, off, label) { this.dim(x1, y, x2, y, off, label); },
    dimV(y1, y2, x, off, label) { this.dim(x, y1, x, y2, off, label); },
    leader(x, y, dx, dy, s, h) {                                  // directriz con texto; (dx, dy) en mm de papel
      const p = [this.X(x), this.Y(y)], e = [p[0] + dx, p[1] + dy], sg = dx < 0 ? -1 : 1, hh = h || 2.5, len = s.length * TXTW * hh + 2;
      this.d.line(p[0], p[1], e[0], e[1], "COTAS"); this.d.line(e[0], e[1], e[0] + sg * len, e[1], "COTAS");
      this.d.circle(p[0], p[1], 0.5, "COTAS");
      this.d.text(e[0] + sg * 1, e[1] + 0.8, s, hh, "TEXTO", sg > 0 ? "l" : "r");
      if (sg < 0) { /* texto a la izquierda: se alinea al final de la repisa */ this.d.e[this.d.e.length - 1].x = e[0] - 1; }
    },
    note(x, y, s, h) { this.text(x, y, s, h || 2.5, "TEXTO", "l"); },
  };
  function sectorJoints(v, ri, ro, n, ph, layer) { for (let k = 0; k < n; k++) { const a = (ph || 0) * D2R + 2 * Math.PI * k / n; v.line(ri * Math.cos(a), ri * Math.sin(a), ro * Math.cos(a), ro * Math.sin(a), layer); } }

  /* ====================================================================== */
  /* 5. Láminas                                                              */
  /* ====================================================================== */
  const TOPE_TXT = (c) => c.stops.length ? c.stops.map((s) => `${s.nombre.replace(/\s*\(\d+ (sectores|pastillas)\)/, "")}: tope L = ${nf(s.L)} mm`).join(" · ") : "";
  function fixNotes(c) {                                          // rotulado de la fijación desmontable por sectores
    const P = c.P, o = c.ifc.o, out = [];
    if (!o) return out;
    if (P.fix_mode < 1.5) {
      out.push(`FIJACIÓN DESMONTABLE POR SECTORES: ${P.n_sec} sectores por disco o placa; topes soldados al respaldo (filete ${nf(P.w_tope)} mm, barra ${nf(P.b_tope)} mm); tornillos avellanados de posición M${nf(P.d_tor)}.`);
      if (c.stops.length) out.push(TOPE_TXT(c) + " · POSICIÓN RADIAL DE LOS TOPES: A DEFINIR");
    } else out.push("FIJACIÓN PERMANENTE (PEGADO): los discos o placas no son desmontables sin destruir la unión.");
    return out;
  }

  // ----- BASE: planta de la base -----
  function sheetBase(d, s, c) {
    const P = c.P, R = c.R, K = c.K, g = c.g, bg = c.bg, ch = c.ch, ifc = c.ifc, B = P.B, v = new View(d, 0, 0, s);
    v.rect(-B / 2, -B / 2, B / 2, B / 2);
    if (P.rim_t > 0) v.rect(-B / 2 + P.rim_t, -B / 2 + P.rim_t, B / 2 - P.rim_t, B / 2 - P.rim_t);
    v.circ(0, 0, P.D_piv / 2);
    if (P.h_boss > 0) v.circ(0, 0, P.D_boss / 2);
    v.circ(0, 0, P.D_top / 2, "OCULTO");
    v.axes(-B / 2 - 25 / s, 0, B / 2 + 25 / s, 0); v.axes(0, -B / 2 - 25 / s, 0, B / 2 + 25 / s);
    // interfaz fija a la base
    if (ifc.o > 0) {
      const ri = R.Ri, ro = R.Ro, rj = Math.max(ri, P.h_boss > 0 ? P.D_boss / 2 : 0);
      v.circ(0, 0, ri); v.circ(0, 0, ro);
      if (P.fix_mode < 1.5) {
        const nb = ifc.o === 3 ? (ifc.conf === 3 ? P.bz_npad : P.n_sec) : P.n_sec;
        sectorJoints(v, rj, ro, nb, 0, "CONTORNO");
        if (ifc.o === 2 && P.n_seg !== P.n_sec) sectorJoints(v, rj, ro, P.n_seg, 360 / P.n_seg / 2, "OCULTO");
      }
      if (ifc.o === 3 && P.h_gr > 0) {                            // ranuras de engrase en el bronce (opción C)
        for (let k = 0; k < P.n_gr_rad; k++) { const a = (k + 0.5) * 2 * Math.PI / P.n_gr_rad; v.line(rj * Math.cos(a), rj * Math.sin(a), ro * Math.cos(a), ro * Math.sin(a), "OCULTO"); }
        for (let k = 1; k <= P.n_gr_circ; k++) v.circ(0, 0, ri + (ro - ri) * k / (P.n_gr_circ + 1), "OCULTO");
      }
    }
    if (c.piv && c.piv.g) pivotPlanta(v, c);
    // bancadas, ménsulas, cilindros activos (giro antihorario) y patines
    if (!c.piv) for (const sx of [1, -1]) {
      const X = sx * P.x_g;
      v.rect(X - P.w_bed / 2, -g.Y_bed, X + P.w_bed / 2, g.Y_bed);
      v.line(X - P.w_slot / 2, -g.Y_bed, X - P.w_slot / 2, g.Y_bed, "OCULTO"); v.line(X + P.w_slot / 2, -g.Y_bed, X + P.w_slot / 2, g.Y_bed, "OCULTO");
      for (const dy of [1, -1]) {
        const act = sx * dy > 0, Ye = dy * g.y_eye;
        const y0 = dy > 0 ? Ye - bg.rear : Ye + bg.rear - P.L_ch;
        v.rect(X - bg.Wout / 2, y0, X + bg.Wout / 2, y0 + P.L_ch, act ? "CONTORNO" : "OCULTO");
        v.circ(X, Ye, P.d_pp / 2, act ? "CONTORNO" : "OCULTO");
        if (!act) continue;
        const yr = dy * (g.y_rp0 + P.s_free), yb0 = Ye + dy * P.e_body, yb1 = dy * (g.y_rp0 - P.c_rod);
        v.rect(X - P.D_body / 2, Math.min(yb0, yb1), X + P.D_body / 2, Math.max(yb0, yb1));
        v.rect(X - P.d_rod / 2, Math.min(yb1, yr), X + P.d_rod / 2, Math.max(yb1, yr));
        const ys0 = yr - dy * g.rear, ys1 = yr + dy * g.front;
        v.rect(X - P.w_s / 2, Math.min(ys0, ys1), X + P.w_s / 2, Math.max(ys0, ys1));
        v.circ(X, yr, P.d_pp / 2);
        const yp = dy * (-P.R_pin * Math.sin(g.pitch / 2)), xm = sx * g.mouthX, xa = sx * g.a_min, xt = sx * g.tipX, yf = yp - dy * P.d_pin / 2, ybk = yf - dy * P.dog_b;
        v.poly([[xt, yf], [xm, yf], [xm, ybk], [xt + sx * ch.dx, ybk], [xt, ybk + dy * Math.min(ch.dy, P.dog_b)]], true);
        v.circ(xa, yp, P.d_pin / 2, "OCULTO");
        if (c.cam) {                                                  // leva de reenganche: riel fijo (canto con bolsillo y rampa) y seguidor de rodillo al tomar el pasador
          const pr = c.cam.g.perfil_y, xo = c.cam.L && c.cam.L.x ? c.cam.L.x.borde_exterior : Math.max(...pr.map((q) => q.x_canto)) + 40;
          v.poly(pr.map((q) => [sx * q.x_canto, dy * q.y]).concat([[sx * xo, dy * pr[pr.length - 1].y], [sx * xo, dy * pr[0].y]]), true);
          v.circ(sx * c.cam.a.x_seguidor, dy * c.cam.a.y_seguidor, Math.max(5, c.cam.g.x_canto_toma - c.cam.g.x_perno_toma - c.cam.g.holgura_toma));
        }
      }
    }
    // orejas de izaje (huella de la placa t_ear × 2R, orientación A DEFINIR)
    const xl = P.x_lug, yl = B / 2 - P.c_lug;
    [[1, 1], [-1, 1], [1, -1], [-1, -1]].forEach(([sx, sy]) => v.rect(sx * xl - P.R_ear, sy * yl - P.t_ear / 2, sx * xl + P.R_ear, sy * yl + P.t_ear / 2));
    // cotas
    v.dimH(-B / 2, B / 2, -B / 2, -16, nf(B)); v.dimV(-B / 2, B / 2, -B / 2, 16, nf(B));
    v.dimH(0, P.x_g, B / 2, 12, `x_g ${nf(P.x_g)}`);
    v.dimH(0, P.x_lug, yl, 8, `x_izaje ${nf(P.x_lug)}`);
    v.dimV(yl, B / 2, P.x_lug, -14, `c ${nf(P.c_lug)}`);
    if (!c.piv) {
    v.dimV(-g.Y_bed, g.Y_bed, P.x_g + P.w_bed / 2, -14, `bancada ${nf(2 * g.Y_bed)}`);
    v.dimH(P.x_g - P.w_bed / 2, P.x_g + P.w_bed / 2, -g.Y_bed, -8, `${nf(P.w_bed)}`);
    }
    v.leader(P.D_piv / 2 * Math.cos(Math.PI / 4), P.D_piv / 2 * Math.sin(Math.PI / 4), -22, 18, `PIVOTE Ø${nf(P.D_piv)} (PIVOTE-01)`);
    if (P.h_boss > 0) v.leader(P.D_boss / 2 * Math.cos(-Math.PI / 4), P.D_boss / 2 * Math.sin(-Math.PI / 4), 22, -18, `COLLAR Ø${nf(P.D_boss)} x ${nf(P.h_boss)} (PIVOTE-02)`);
    v.leader(0, -P.D_top / 2, -26, -16, `MESA Ø${nf(P.D_top)} (oculta)`);
    v.leader(-xl, -yl - P.t_ear / 2, -18, -9, `OREJA DE IZAJE x4 (IZAJE-01)`);
    if (!c.piv) {
    v.leader(-P.x_g, -g.Y_bed + 120, -20, -14, "BANCADA (BASE-03)"); v.leader(P.x_g + bg.Wout / 2, -g.y_eye + 60, 20, 12, "MÉNSULA (BASE-04)");
    v.leader(P.x_g + P.w_s / 2, g.y_rp0 + P.s_free + g.front, 20, 12, "PATÍN (BASE-05)");
    v.leader(P.x_g + P.D_body / 2, g.y_eye + P.e_body + 120, 20, -10, `CILINDRO Ø${nf(P.D_bore)} (CIL-01)`);
    if (c.cam) v.leader(P.x_g + P.w_s / 2, g.y_rp0 + P.s_free + 40, 22, -14, "LEVA DE REENGANCHE (BASE-07)");
    }
    // textos
    const lines = [`BASE ${nf(B)} x ${nf(B)} x ${nf(P.t_base)} · marco ${nf(P.rim_t)} x ${nf(P.rim_h)} · N.º de cilindros ${P.n_cyl} (se muestra el giro antihorario; ménsulas a trazos: giro horario)`,
      `Interfaz elegida: ${ifaceName(P, ifc)}${ifc.o ? ` · Ri ${nf(R.Ri)} · Ro ${nf(R.Ro)} mm` : ""}`, ...fixNotes(c)];
    if (ifc.o && P.h_boss > 0) lines.push(`DIÁMETRO INTERIOR DE DISCOS O PLACAS ALREDEDOR DEL COLLAR: Ø${nf(2 * R.Ri)} (R_i = D_collar/2 + c_boss_r + m_ri = ${nf(P.D_boss / 2)} + ${nf(P.c_boss_r)} + ${nf(P.m_ri)}; igual al del núcleo). REBAJE DEL COLLAR EN LA PLANCHA INFERIOR Ø${nf(R.hubG.Drb)}, PROFUNDIDAD ${nf(R.hubG.hRaw)} DESDE LA CARA INFERIOR DE LA MESA.`);
    if (ifc.o === 3 && P.h_gr > 0) lines.push("RANURAS DE ENGRASE EN EL BRONCE (a trazos): POSICIÓN INDICATIVA, A DEFINIR.");
    lines.push("OREJAS DE IZAJE: ORIENTACIÓN DE LA PLACA EN PLANTA A DEFINIR (se dibuja su huella t x 2R).");
    d.notes = lines;
  }

  // ----- MESA: planta de la mesa -----
  function sheetMesa(d, s, c) {
    const P = c.P, R = c.R, ifc = c.ifc, Rt = P.D_top / 2, v = new View(d, 0, 0, s);
    v.circ(0, 0, Rt); v.circ(0, 0, c.prIn, "OCULTO");
    c.rings.forEach((r) => v.circ(0, 0, r));
    for (let k = 0; k < P.N_rib; k++) { const a = 2 * Math.PI * k / P.N_rib; v.line(P.D_hub / 2 * Math.cos(a), P.D_hub / 2 * Math.sin(a), P.R_rib * Math.cos(a), P.R_rib * Math.sin(a)); }
    v.circ(0, 0, P.D_hub / 2); v.circ(0, 0, c.d_bush / 2); v.circ(0, 0, c.hole_top / 2, "OCULTO");
    for (let k = 0; k < P.N_pin; k++) { const a = Math.PI / P.N_pin + 2 * Math.PI * k / P.N_pin; v.circ(P.R_pin * Math.cos(a), P.R_pin * Math.sin(a), P.d_pin / 2); }
    v.circ(0, 0, P.R_pin, "EJES");
    v.axes(-Rt - 25 / s, 0, Rt + 25 / s, 0); v.axes(0, -Rt - 25 / s, 0, Rt + 25 / s);
    // interfaz fija a la mesa (cara inferior, vista oculta)
    if (ifc.o > 0) {
      const ri = R.Ri, ro = R.Ro, rj = Math.max(ri, P.h_boss > 0 ? P.D_boss / 2 : 0);
      v.circ(0, 0, ri, "OCULTO"); v.circ(0, 0, ro, "OCULTO");
      if (P.fix_mode < 1.5) sectorJoints(v, rj, ro, P.n_sec, 360 / P.n_sec / 2, "OCULTO");
      if (ifc.o === 1 && P.h_gr > 0) {
        for (let k = 0; k < P.n_gr_rad; k++) { const a = k * 2 * Math.PI / P.n_gr_rad; v.line(rj * Math.cos(a), rj * Math.sin(a), ro * Math.cos(a), ro * Math.sin(a), "OCULTO"); }
        for (let k = 1; k <= P.n_gr_circ; k++) v.circ(0, 0, ri + (ro - ri) * k / (P.n_gr_circ + 1), "OCULTO");
      }
    }
    // cotas
    v.dimH(-Rt, Rt, -Rt, -16, `Ø${nf(P.D_top)}`);
    v.dim(0, 0, P.R_pin * Math.cos(Math.PI / 4), P.R_pin * Math.sin(Math.PI / 4), 0, `R${nf(P.R_pin)}`);
    v.leader(P.R_pin * Math.cos(Math.PI * 0.25 + Math.PI / P.N_pin), P.R_pin * Math.sin(Math.PI * 0.25 + Math.PI / P.N_pin) + 0, 22, 18, `${P.N_pin} PASADORES Ø${nf(P.d_pin)} (MESA-06) cada ${nf(360 / P.N_pin, 2)}°`);
    v.leader(P.D_hub / 2 * Math.cos(Math.PI * 1.25), P.D_hub / 2 * Math.sin(Math.PI * 1.25), -24, -16, `CUBO Ø${nf(P.D_hub)} (MESA-05)`);
    v.leader(P.R_rib, 0, 22, 14, `${P.N_rib} NERVIOS t = ${nf(P.t_rib)}, R${nf(P.R_rib)} (MESA-04)`);
    if (c.rings.length) v.leader(c.rings[c.rings.length - 1] * Math.cos(Math.PI * 0.75), c.rings[c.rings.length - 1] * Math.sin(Math.PI * 0.75), -26, 22, `ALMAS ANULARES t = ${nf(P.t_web)}, R${c.rings.map((r) => nf(r)).join(" / R")} (MESA-03)`);
    v.leader(c.prIn * Math.cos(-Math.PI * 0.3), c.prIn * Math.sin(-Math.PI * 0.3), 22, -16, `ANILLO DE PASADORES: r int. ${nf(c.prIn)} · t = ${nf(c.tpr)}`);
    const lines = [`MESA Ø${nf(P.D_top)} x ${nf(P.h_disc)} · plancha superior ${nf(P.t_top)} (no mostrada) · plancha inferior ${nf(P.t_bot)} · luz libre del pasador ${nf(TT_.pinClear(P))} mm`,
      `Interfaz elegida: ${ifaceName(P, ifc)} (elementos de la mesa a trazos, cara inferior)`, ...fixNotes(c)];
    if (ifc.o === 1 && P.h_gr > 0) lines.push(`RANURAS DE ENGRASE EN EL DISCO DE LA MESA: ${P.n_gr_rad} radiales y ${P.n_gr_circ} circunferenciales, ancho ${nf(P.w_gr)}, prof. ${nf(P.h_gr)}; POSICIÓN INDICATIVA, A DEFINIR. ${P.n_greaser} graseras M10x1 en el borde.`);
    if (ifc.o && P.fix_mode < 1.5) lines.push("DESFASE ANGULAR ENTRE JUNTAS DE LA BASE Y DE LA MESA: A DEFINIR.");
    if (P.opt_wood > 0.5) lines.push(`CUBIERTA DE MADERA DURA t = ${nf(P.t_wood)} mm sobre la plancha superior (Ø${nf(P.D_top)} con agujero Ø${nf(c.hole_top)}): DISPOSICIÓN DE LOS TABLONES A DEFINIR.`);
    d.notes = lines;
  }

  function segsView(v, segs, l) {
    segs.forEach((q) => {
      if (q.tipo === "arco" && q.radio > 0 && q.centro) {
        const ang = (p) => Math.atan2(p[1] - q.centro[1], p[0] - q.centro[0]) / D2R, a0 = ang(q.p0), a1 = ang(q.p1);
        if (q.sentido === "horario") v.arc(q.centro[0], q.centro[1], q.radio, a1, a0, l); else v.arc(q.centro[0], q.centro[1], q.radio, a0, a1, l);
      } else v.line(q.p0[0], q.p0[1], q.p1[0], q.p1[1], l);
    });
  }
  // modo pivotado en planta: ojales E en diagonal (cajón), 4 placas-leva con pernos (activas las del giro antihorario), cilindros y bloques-uña al tomar el pasador
  function pivotPlanta(v, c) {
    const P = c.P, g = c.piv.g, q = c.piv.q, D = c.piv.D || {}, pl = D.placa_leva || {};
    // placas-guía curvas: rectas y arcos de los segmentos del núcleo (ARC de DXF, antihorario de a0 a a1); el giro horario es la imagen especular (ACC-024)
    Object.entries(g.placas).forEach(([k, pc]) => { const act = k.endsWith("_antihorario"); segsView(v, pc.segmentos_contorno || [], act ? "CONTORNO" : "OCULTO"); if (act) { pc.pernos.forEach(([a, b]) => v.circ(a, b, (pl.d_perno || 20) / 2)); (pc.pasadores_posicion || []).forEach(([a, b]) => v.circ(a, b, (P.pv_dd || 16) / 2, "OCULTO")); } });
    g.E.forEach(([ex, ey]) => { const h = g.ojalE.lado_cajon / 2; v.rect(ex - h, ey - h, ex + h, ey + h); v.circ(ex, ey, g.ojalE.d / 2); v.cross(ex, ey, h + 10); });
    if (!q) return;
    [[q.E, q.Q, (p) => p], [[-q.E[0], -q.E[1]], [-q.Q[0], -q.Q[1]], (p) => [-p[0], -p[1]]]].forEach(([E, Q, f]) => {
      const L = Math.hypot(Q[0] - E[0], Q[1] - E[1]), u = [(Q[0] - E[0]) / L, (Q[1] - E[1]) / L], t = [-u[1], u[0]], lb = Math.min(L - 30, P.L0 - 30);
      const bar = (a, b, w) => [[a, -1], [b, -1], [b, 1], [a, 1]].map(([s_, k]) => [E[0] + s_ * u[0] + k * w / 2 * t[0], E[1] + s_ * u[1] + k * w / 2 * t[1]]);
      v.poly(bar(0, lb, P.D_body), true); v.poly(bar(lb, L, P.d_rod), true);
      v.poly(q.una.cuerpo.map(f), true); v.poly(q.una.cara.map(f), true); v.poly(q.una.cubo.map(f), true); v.circ(Q[0], Q[1], g.pasadorQ.d / 2);
      const A_ = f(q.pasadores.A); v.circ(A_[0], A_[1], P.d_pin / 2, "OCULTO");
    });
    const E = g.E[0], pc = g.placas["1_antihorario"].contorno[0];
    v.dimH(0, E[0], E[1], -10, `E x ${nf(E[0])}`); v.dimV(0, E[1], E[0], 12, `E y ${nf(E[1])}`);
    v.leader(E[0], E[1], 18, -10, `OJAL E (BASE-04) · cajón ${nf(g.ojalE.lado_cajon)}`);
    v.leader(pc[0], pc[1], 20, 12, `PLACA-LEVA t = ${nf(pl.t || P.pv_tcam)} (BASE-07)`);
    v.leader(q.Q[0], q.Q[1], 22, 14, `BLOQUE-UÑA + PASADOR Q Ø${nf(g.pasadorQ.d)} (BASE-06)`);
    v.leader((q.E[0] + q.Q[0]) / 2, (q.E[1] + q.Q[1]) / 2, 22, -16, `CILINDRO PIVOTADO Ø${nf(P.D_bore)} (CIL-01)`);
  }
  // modo pivotado en alzado desarrollado (distancias radiales): placa-leva, bloque-uña con pasador Q, cilindro y soporte del ojal E
  function pivotAlzado(v, c, zc, R_) {
    const P = c.P, g = c.piv.g, q = c.piv.q, D = c.piv.D || {}, pl = D.placa_leva || {}, bl = D.bloque_una || {}, se = D.soporte_E || {}, tb = c.tb;
    if (!q) return;
    const rr = (pts) => { const a = pts.map(([x, y]) => Math.hypot(x, y)); return [Math.min(...a), Math.max(...a)]; };
    const [p0, p1] = rr(g.placas["1_antihorario"].contorno), [b0, b1] = rr(q.una.cuerpo.concat(q.una.cara, q.una.cubo)), rQ = Math.hypot(...q.Q), rE = Math.hypot(...q.E);
    R_(p0, tb, p1, tb + pl.t);
    v.rect(b0, bl.z_inf, b1, bl.z_inf + bl.h, "CONTORNO");
    v.rect(rQ - bl.d_Q / 2, c.R.blk.zCam, rQ + bl.d_Q / 2, c.R.blk.zCam + bl.l_pasador_Q, "OCULTO");
    v.rect(rE - se.lado_cajon / 2, tb, rE + se.lado_cajon / 2, tb + se.alto, "CONTORNO");
    [se.z_tapa_inf, se.z_tapa_sup].forEach((zt) => v.line(rE - se.lado_cajon / 2, zt, rE + se.lado_cajon / 2, zt));
    const rm = rE - (P.L0 - 30) * (rE - rQ) / Math.max(1, Math.hypot(q.Q[0] - q.E[0], q.Q[1] - q.E[1]));
    v.rect(Math.min(rm, rE), zc - P.D_body / 2, Math.max(rm, rE), zc + P.D_body / 2); v.rect(Math.min(rQ, rm), zc - P.d_rod / 2, Math.max(rQ, rm), zc + P.d_rod / 2);
    v.line(rE, tb, rE, tb + se.alto + 20, "EJES"); v.line(rQ, c.R.blk.zCam - 10, rQ, c.R.blk.zCam + bl.l_pasador_Q + 10, "EJES");
    v.dimV(tb, tb + pl.t, p1, -10, `${nf(pl.t)}`); v.dimV(bl.z_inf, bl.z_inf + bl.h, b0, 10, `h ${nf(bl.h)}`);
    v.leader((p0 + p1) / 2, tb + pl.t, -10, -18, "PLACA-LEVA (BASE-07)"); v.leader(b1, bl.z_inf + bl.h, 12, 20, "BLOQUE-UÑA + PASADOR Q (BASE-06)"); v.leader(rE, tb + se.alto, 14, 22, "SOPORTE DEL OJAL E (BASE-04)");
  }

  // ----- CONJ: sección radial del conjunto con la interfaz elegida -----
  function sheetConj(d, s, c) {
    const P = c.P, R = c.R, K = c.K, ifc = c.ifc, tb = c.tb, tm = c.tm, hd = P.h_disc, tpr = c.tpr, Rt = P.D_top / 2, rpr = c.prIn;
    const r0 = rpr - 220, rB = P.B / 2, v = new View(d, 0, 0, s), woodT = P.opt_wood > 0.5 ? P.t_wood : 0;
    const R_ = (x0, z0, x1, z1, hat, l) => { v.rect(x0, z0, x1, z1, l); if (hat !== false) v.hatch(x0, z0, x1, z1); };
    R_(r0, 0, rB, tb);                                                       // plancha base
    if (P.rim_h > 0) R_(rB - P.rim_t, tb, rB, tb + P.rim_h);
    // interfaz entre la base y la mesa
    const layers = [];
    if (ifc.o === 3) { layers.push([tb, ifc.tbz, "BRONCE CON GRAFITO", true]); layers.push([tb + ifc.tbz, ifc.tss, ifc.conf === 2 ? "2.ª PLACA DE BRONCE" : "DISCO DURO", true]); }
    else if (ifc.o > 0) { layers.push([tb, ifc.tss, "DISCO INOX BASE", true]); let z = tb + ifc.tss; if (ifc.o === 2) { layers.push([z, ifc.tuh, "UHMW", true]); z += ifc.tuh; } layers.push([z, ifc.tss2, "DISCO INOX MESA", true]); }
    layers.forEach(([z0, t, n]) => { R_(R.Ri > r0 ? R.Ri : r0, z0, Rt, z0 + t); });
    // mesa
    R_(r0, tm, rpr, tm + P.t_bot);                                           // plancha inferior
    R_(rpr, tm, Rt, tm + tpr);                                               // anillo de pasadores (inferior)
    R_(r0, tm + hd - P.t_top, rpr, tm + hd);                                 // plancha superior
    R_(rpr, tm + hd - tpr, Rt, tm + hd);
    c.rings.filter((r) => r > r0).forEach((r) => R_(r - P.t_web / 2, tm + P.t_bot, r + P.t_web / 2, tm + hd - P.t_top));
    v.rect(P.R_pin - P.d_pin / 2, tm, P.R_pin + P.d_pin / 2, tm + hd, "OCULTO");   // pasador (eje vertical)
    if (woodT) { R_(r0, tm + hd, Rt - 0, tm + hd + woodT, true); }
    // bancada, patín y uña (sección por el eje del cilindro)
    const zc = tb + R.hax, zb = tb + P.t_bed, fh = TT_.forkH(P);
    if (c.piv && c.piv.g) { pivotAlzado(v, c, zc, R_); v.line(r0 - 20, zc, Math.max(rB, Math.hypot(...c.piv.g.E[0])) + 40, zc, "EJES"); }
    else {
    R_(P.x_g - P.w_bed / 2, tb, P.x_g + P.w_bed / 2, zb);
    v.rect(P.x_g - P.w_slot / 2, zb - P.h_slot, P.x_g + P.w_slot / 2, zb, "OCULTO");
    R_(P.x_g - P.w_s / 2, zb, P.x_g + P.w_s / 2, zc + fh / 2, false);
    v.rect(K.tipX, zc - P.dog_h / 2, K.mouthX + P.L_in, zc + P.dog_h / 2, "CONTORNO");
    v.line(P.x_g, tb, P.x_g, zc + fh / 2 + 20, "EJES"); v.line(r0 - 20, zc, rB + 40, zc, "EJES");
    if (c.cam && c.cam.L && c.cam.L.z && c.cam.L.x) {               // leva de reenganche: riel sobre el patín y seguidor de rodillo en su perno
      const z = c.cam.L.z, x = c.cam.L.x, rF = Math.max(5, x.canto_toma - x.perno_seguidor_toma - (c.cam.L.holgura_toma || 0));
      R_(x.canto_toma, z.inf_riel, x.borde_exterior, z.sup_riel);
      v.rect(x.perno_seguidor_toma - rF, z.inf_riel + 4, x.perno_seguidor_toma + rF, z.sup_riel - 4, "CONTORNO");
      v.line(x.perno_seguidor_toma, z.sup_una, x.perno_seguidor_toma, z.sup_riel - 4, "EJES");
      v.leader(x.borde_exterior, z.sup_riel, 16, 14, "LEVA DE REENGANCHE (BASE-07)");
    }
    }
    // cotas: pila de espesores a la izquierda (desfasadas alternadamente para que no se pisen)
    const st = [[0, tb, tb]].concat(layers.map(([z0, t]) => [z0, z0 + t, t]), [[tm, tm + P.t_bot, P.t_bot]]);
    st.forEach(([z0, z1, t], i) => v.dimV(z0, z1, r0, 12 + 10 * (i % 2), nf(t)));
    v.dimV(tm, tm + hd, r0, 36, `h ${nf(hd)}`);
    v.dimV(tm + hd - P.t_top, tm + hd, r0, 12, nf(P.t_top));
    v.dimV(tm + hd - tpr, tm + hd, Rt, -12, `anillo ${nf(tpr)}`);
    v.dimV(tm + tpr, tm + hd - tpr, P.R_pin + P.d_pin / 2, -12, `libre ${nf(TT_.pinClear(P))}`);
    v.dimH(P.R_pin, rB, 0, -14, `${nf(rB - P.R_pin)}`);
    v.dimV(0, zc, rB + 40, -14, `eje cil. ${nf(zc)}`);
    v.dimV(0, tm + hd + woodT, rB + 40, -28, `alto ${nf(tm + hd + woodT)}`);
    if (woodT) v.dimV(tm + hd, tm + hd + woodT, Rt, -12, `madera ${nf(woodT)}`);
    if (!c.piv) { v.leader(P.x_g, zb + 20, 24, 22, "BANCADA + PATÍN (BASE-03 / BASE-05)"); v.leader(K.tipX + 30, zc, -30, 24, "UÑA (BASE-06)"); }
    v.leader(P.R_pin, tm + hd, 14, 22 + (woodT ? 6 : 0), `PASADOR Ø${nf(P.d_pin)} en R${nf(P.R_pin)} (MESA-06)`);
    if (layers.length) v.leader((R.Ri > r0 ? R.Ri : r0) + 80, tb + layers[0][1] / 2, -2, -26, "INTERFAZ DE GIRO (INTER)");
    if (woodT) v.leader(r0 + 120, tm + hd + woodT, 0, 20, "CUBIERTA DE MADERA (MESA-07)");
    const lines = [`SECCIÓN RADIAL POR EL EJE DEL CILINDRO · base ${nf(tb)} · interfaz δ = ${nf(c.delta)} · mesa h = ${nf(hd)} · eje del cilindro +${nf(R.hax)} sobre la base`,
      `Interfaz elegida: ${ifaceName(P, ifc)}${layers.length ? " · capas: " + layers.map((l) => `${l[2]} ${nf(l[1])}`).join(" + ") : ""}`, ...fixNotes(c)];
    if (ifc.o === 3 && ifc.conf === 3) lines.push(`PASTILLAS DE BRONCE (cobertura ${nf(P.bz_cover * 100)} %, ${P.bz_npad} por vuelta): GEOMETRÍA DE LAS PASTILLAS A DEFINIR (se dibuja el espesor de la placa).`);
    if (woodT) lines.push("CUBIERTA DE MADERA: DISPOSICIÓN Y FIJACIÓN DE LOS TABLONES A DEFINIR (se dibuja el espesor).");
    lines.push(`Cotas radiales medidas desde el eje de giro: pasador R${nf(P.R_pin)}, eje de la guía x_g = ${nf(P.x_g)}, borde de la base ${nf(rB)}. La sección se corta en r = ${nf(r0)} mm; el pivote y el collar están en la lámina PIVOTE.`);
    d.notes = lines;
  }

  // ----- PIVOTE: collar de asiento y pivote -----
  function sheetPivote(d, s, c) {
    const P = c.P, tb = c.tb, tm = c.tm, hd = P.h_disc, Dp = P.D_piv, Db = P.D_boss, hb = P.h_boss, zTop = tm + hd - P.t_top, Lp = zTop + 3, dbu = c.d_bush;
    const xw = Math.max(P.D_hub / 2, Db / 2) + 70;
    const sp = new View(d, 0, 0, s);                                         // planta (centrada en 0,0)
    const ox2 = xw * s * 2 + 60;                                              // sección a la derecha
    const v = new View(d, ox2 + xw * s, 0, s);
    sp.circ(0, 0, Dp / 2); sp.circ(0, 0, dbu / 2, "OCULTO"); if (hb > 0) sp.circ(0, 0, Db / 2); sp.circ(0, 0, P.D_hub / 2, "OCULTO"); sp.circ(0, 0, c.hole_top / 2, "OCULTO");
    sp.cross(0, 0, xw);
    const pa = (r, deg) => [r * Math.cos(deg * D2R), r * Math.sin(deg * D2R)];
    sp.leader(...pa(Dp / 2, 60), 24, 20, `PIVOTE Ø${nf(Dp)}`);
    if (hb > 0) sp.leader(...pa(Db / 2, 20), 30, 8, `COLLAR Ø${nf(Db)}`);
    sp.leader(...pa(dbu / 2, -30), 30, -10, `BUJE Ø${nf(dbu)}`);
    sp.leader(...pa(P.D_hub / 2, -60), 24, -22, `CUBO Ø${nf(P.D_hub)} (a trazos)`);
    sp.leader(...pa(c.hole_top / 2, 150), -24, 16, `AGUJERO SUP. Ø${nf(c.hole_top)}`);
    sp.text(0, xw + 24, "PLANTA", 3.5, "TEXTO", "c");
    v.text(0, Math.max(Lp, tm + hd) + 22 + 0, "SECCIÓN POR EL EJE", 3.5, "TEXTO", "c");
    const Rx = (x0, z0, x1, z1, hat) => { [1, -1].forEach((sg) => { v.rect(sg * x0, z0, sg * x1, z1); if (hat !== false) v.hatch(sg * x0, z0, sg * x1, z1, 1.2); }); };
    const hubTopZ = zTop;
    Rx(Dp / 2, 0, xw, tb);                                                   // plancha base (sin agujero del pivote)
    if (hb > 0) { Rx(Dp / 2, tb, Db / 2, tb + hb); [1, -1].forEach((sg) => v.poly([[sg * Db / 2, tb], [sg * (Db / 2 + 10), tb], [sg * Db / 2, tb + 10]], true)); }
    v.rect(-Dp / 2, 0, Dp / 2, Lp); v.hatch(-Dp / 2, 0, Dp / 2, Lp, 1.8);                  // pivote
    // interfaz alrededor del collar
    const layers = []; const ifc = c.ifc;
    if (ifc.o === 3) { layers.push([tb, ifc.tbz]); layers.push([tb + ifc.tbz, ifc.tss]); } else if (ifc.o > 0) { layers.push([tb, ifc.tss]); let z = tb + ifc.tss; if (ifc.o === 2) { layers.push([z, ifc.tuh]); z += ifc.tuh; } layers.push([z, ifc.tss2]); }
    const xi = Math.max(c.R.Ri, hb > 0 ? Db / 2 : 0);
    layers.forEach(([z0, t]) => Rx(xi, z0, xw, z0 + t));
    // buje sobre el collar
    const zbu = tb + hb + 2; Rx(Dp / 2, zbu, dbu / 2, zbu + P.L_bush);
    // mesa: plancha inferior con agujero Ø(D_boss) sobre el collar (A DEFINIR), cubo y plancha superior
    const xin = hb > 0 ? Db / 2 : dbu / 2;
    Rx(xin, tm, xw, tm + P.t_bot);
    const zr = Math.max(zbu, tm + P.t_bot);
    [1, -1].forEach((sg) => { v.poly([[sg * xin, tm + P.t_bot], [sg * P.D_hub / 2, tm + P.t_bot], [sg * P.D_hub / 2, hubTopZ], [sg * dbu / 2, hubTopZ], [sg * dbu / 2, zr], [sg * xin, zr]], true); });
    [1, -1].forEach((sg) => v.hatch(sg * dbu / 2, zr, sg * P.D_hub / 2, hubTopZ, 1.2));
    Rx(c.hole_top / 2, hubTopZ, xw, tm + hd);
    // cotas
    v.dimV(0, tb, xw, -12, `${nf(tb)}`);
    if (hb > 0) v.dimV(tb, tb + hb, -Db / 2, -10, `h ${nf(hb)}`);
    v.dimV(0, Lp, -xw, 14, `L ${nf(Lp)}`);
    v.dimH(-Dp / 2, Dp / 2, 0, -10, `Ø${nf(Dp)}`);
    v.dimV(zbu, zbu + P.L_bush, -dbu / 2, 12, `buje ${nf(P.L_bush)}`);
    v.dimV(tm, tm + hd, xw, -12, `h ${nf(hd)}`);
    v.leader(Dp / 2, Lp, 30, 14, `PIVOTE Ø${nf(Dp)} x ${nf(Lp)} (PIVOTE-01)`);
    if (hb > 0) v.leader(Db / 2, tb + hb / 2, 30, -30, `COLLAR (PIVOTE-02), filete 10 mm`);
    const lines = [`COLLAR DE ASIENTO Ø${nf(Db)} x ${nf(hb)} SOLDADO A LA BASE (t = ${nf(tb)}) · PIVOTE Ø${nf(Dp)} (H7/p6) · asiento = plancha base + collar = ${nf(tb + hb)} mm`,
      "REBAJE DEL CUBO SOBRE EL COLLAR (Ø y profundidad) Y AGUJERO DE LA PLANCHA INFERIOR: A DEFINIR (se dibuja el contorno hasta la cara superior del collar + 2 mm).",
      "TAPA RETENEDORA Y TAPA DE INSPECCIÓN DEL PIVOTE: A DEFINIR (no definidas en el núcleo; las incluye el generador completo).",
      `Interfaz elegida: ${ifaceName(P, ifc)}${ifc.o ? ": DIÁMETRO INTERIOR DE DISCOS O PLACAS ALREDEDOR DEL COLLAR A DEFINIR (se dibujan desde el collar)." : ""}`];
    d.notes = lines;
  }

  // ----- IZAJE: orejas de izaje -----
  function sheetIzaje(d, s, c) {
    const P = c.P, R = P.R_ear, h = P.h_ear, t = P.t_ear, B = P.B, ife = c.A.checks.filter((k) => k.grp === "Orejas de izaje");
    const gap = 40, wEl = 2 * R * s, wSd = (t + 2 * P.w_ear) * s + 20;
    const v1 = new View(d, 0, 0, s);                                         // elevación
    const v2 = new View(d, wEl / 2 + gap + 20 + wSd / 2, 0, s);              // vista lateral
    const sl = Math.min(s, 1 / 20), v3 = new View(d, wEl / 2 + gap + 20 + wSd + gap + (B / 2) * sl + 20, (h + R) * s / 2, sl);   // ubicación en la base
    v1.poly([[-R, 0], [R, 0], [R, h]], false); v1.arc(0, h, R, 0, 180); v1.poly([[-R, h], [-R, 0]], false); v1.line(-R, 0, R, 0);
    v1.circ(0, h, P.d_ear / 2); v1.cross(0, h, R + 10);
    v1.line(-R - 14 / s, 0, R + 14 / s, 0, "CONTORNO");
    v1.dimH(-R, R, 0, -12, `${nf(2 * R)}`); v1.dimV(0, h, R, -14, `${nf(h)}`);
    v1.leader(R * Math.cos(Math.PI / 4), h + R * Math.sin(Math.PI / 4), 18, 12, `R${nf(R)}`);
    v1.leader(P.d_ear / 2 * Math.cos(-Math.PI / 4), h + P.d_ear / 2 * Math.sin(-Math.PI / 4), 18, -14, `Ø${nf(P.d_ear)}`);
    v1.text(0, h + R + 18 / s, "ELEVACIÓN DE LA OREJA", 3.5, "TEXTO", "c");
    // vista lateral: placa t × (h + R) sobre la base, filetes w_ear a ambos lados
    v2.rect(-t / 2, 0, t / 2, h + R); v2.hatch(-t / 2, 0, t / 2, h + R, 1.2);
    v2.rect(-t / 2 - 2 * P.w_ear - 40, -P.t_base, t / 2 + 2 * P.w_ear + 40, 0); v2.hatch(-t / 2 - 2 * P.w_ear - 40, -P.t_base, t / 2 + 2 * P.w_ear + 40, 0, 1.2);
    [1, -1].forEach((sg) => v2.poly([[sg * t / 2, 0], [sg * (t / 2 + P.w_ear), 0], [sg * t / 2, P.w_ear]], true));
    v2.line(0, -P.t_base - 8, 0, h + R + 8, "EJES");
    v2.dimH(-t / 2, t / 2, h + R, 10, `t ${nf(t)}`); v2.dimV(0, h + R, t / 2 + 2 * P.w_ear + 40, -12, `${nf(h + R)}`);
    v2.dimV(-P.t_base, 0, -t / 2 - 2 * P.w_ear - 40, 10, `${nf(P.t_base)}`);
    v2.leader(t / 2 + P.w_ear, P.w_ear * 0.4, 20, -14, `FILETE ${nf(P.w_ear)} mm (ambos lados, L = ${nf(2 * R)})`);
    v2.text(0, h + R + 18 / s, "VISTA LATERAL", 3.5, "TEXTO", "c");
    // ubicación en planta (esquema)
    v3.rect(-B / 2, -B / 2, B / 2, B / 2); v3.circ(0, 0, P.D_top / 2, "OCULTO"); v3.cross(0, 0, B / 2 + 8 / sl * 0 + 120);
    [[1, 1], [-1, 1], [1, -1], [-1, -1]].forEach(([sx, sy]) => { v3.circ(sx * P.x_lug, sy * (B / 2 - P.c_lug), 35, "CONTORNO"); });
    v3.dimH(0, P.x_lug, B / 2 - P.c_lug, 0 + 6, `${nf(P.x_lug)}`); v3.dimV(B / 2 - P.c_lug, B / 2, -P.x_lug, 8, `${nf(P.c_lug)}`);
    v3.dimH(-B / 2, B / 2, -B / 2, -10, nf(B));
    v3.text(0, B / 2 + 14 / sl * 0 + 380, "UBICACIÓN EN LA BASE (4 OREJAS)", 3.5, "TEXTO", "c");
    const lines = [`OREJA DE IZAJE x4, placa t = ${nf(t)}, R${nf(R)}, agujero Ø${nf(P.d_ear)} (pasador del grillete ≤ Ø${nf(P.d_ear - 3)}), centro a ${nf(h)} mm sobre la base, filete ${nf(P.w_ear)} mm`,
      `Ubicación: x = ±${nf(P.x_lug)} · y = ±${nf(B / 2 - P.c_lug)} (c = ${nf(P.c_lug)} al borde) · factor dinámico de izaje ${nf(P.phi_lift, 2)}`,
      "ORIENTACIÓN DE LA PLACA EN PLANTA (PLANO DE LA OREJA) Y ÁNGULO DE LA ESLINGA: A DEFINIR.",
      ife.length ? `Verificaciones de las orejas en la herramienta: ${ife.filter((k) => k.st === "ok" || k.st === "info").length} cumplen, ${ife.filter((k) => k.st === "warn").length} en monitoreo, ${ife.filter((k) => k.st === "fail").length} no cumplen (huella de la oreja en planta: Ø70 del núcleo).` : ""].filter(Boolean);
    d.notes = lines;
  }

  const SHEETS = [
    { id: "BASE-00", sub: "BASE", titulo: "PLANTA DE LA BASE: CILINDROS, BANCADAS, OREJAS Y COLLAR", fn: sheetBase, maxDen: 10, subs: ["BASE"] },
    { id: "MESA-00", sub: "MESA", titulo: "PLANTA DE LA MESA: ANILLO DE PASADORES, NERVIOS Y ALMAS", fn: sheetMesa, maxDen: 10, subs: ["MESA"] },
    { id: "CONJ-00", sub: "CONJ", titulo: "SECCIÓN RADIAL DEL CONJUNTO CON LA INTERFAZ DE GIRO ELEGIDA", fn: sheetConj, maxDen: 5, subs: null },
    { id: "PIVOTE-00", sub: "PIVOTE", titulo: "COLLAR DE ASIENTO Y PIVOTE CENTRAL", fn: sheetPivote, maxDen: 5, subs: ["PIVOTE"] },
    { id: "IZAJE-00", sub: "IZAJE", titulo: "OREJAS DE IZAJE SOLDADAS A LA BASE", fn: sheetIzaje, maxDen: 2, subs: ["IZAJE"] },
  ];
  const sheetCode = (sh) => `TT300C-${sh.id}-${REV}`;

  /* ----- marco, cajetín y ajuste de formato/escala ----- */
  const FORMATS = [["A3", 420, 297], ["A2", 594, 420], ["A1", 841, 594]];
  const DENS = [1, 2, 2.5, 5, 10, 20, 25, 50, 100];
  const CAJ = { w: 196, h: 66 }, STRIP = 10;
  function frame(d, W, H, ctx, info) {
    const x0 = 20, y0 = 10, x1 = W - 10, y1 = H - 10, C = (a, b, c2, e) => d.line(a, b, c2, e, "CAJETIN"), T = (x, y, s2, h, al) => d.text(x, y, s2, h, "TEXTO", al || "l");
    d.poly([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], true, "CAJETIN");
    C(x0, y0 + STRIP, x1, y0 + STRIP);                                            // franja de advertencia (texto negro sobre blanco)
    T((x0 + x1) / 2, y0 + 3.2, ADVERTENCIA, 3.4, "c");
    const cx = x1 - CAJ.w, cy = y0 + STRIP, pad = 2;
    d.poly([[cx, cy], [x1, cy], [x1, cy + CAJ.h], [cx, cy + CAJ.h]], true, "CAJETIN");
    [12, 24, 34, 44, 54].forEach((dy) => C(cx, cy + dy, x1, cy + dy));
    T(cx + pad, cy + 58.5, "TT300-C · TORNAMESA HIDRÁULICA 300 tf", 4.2);
    T(cx + pad, cy + 47.5, info.titulo, 3.4);
    [70, 125, 148, 166].forEach((dx) => C(cx + dx, cy + 34, cx + dx, cy + 44));
    T(cx + pad, cy + 37.5, `CÓDIGO: ${info.codigo}`, 3.2); T(cx + 72, cy + 37.5, `ESC. ${info.escala}`, 3.2); T(cx + 127, cy + 37.5, `HOJA ${info.hoja}`, 3.2);
    T(cx + 150, cy + 37.5, `REV. ${REV}`, 3.2); T(cx + 168, cy + 37.5, fmtDate(ctx.fecha), 3.2);
    C(cx + 98, cy + 24, cx + 98, cy + 34);
    T(cx + pad, cy + 27.5, `MASA DE ESTA LÁMINA: ${nf(info.masa)} kg`, 3.2); T(cx + 100, cy + 27.5, `MASA TOTAL DEL EQUIPO: ${nf(info.masaTotal)} kg`, 3.2);
    T(cx + pad, cy + 18.6, `INTERFAZ: ${ifaceName(ctx.P, ctx.ifc)} · ${woodText(ctx.P)}`, 2.6);
    T(cx + pad, cy + 14.2, `FIJACIÓN: ${fixText(ctx.P, ctx.ifc)}`, 2.6);
    T(cx + pad, cy + 8.4, "NOTAS:", 2.6); T(cx + 16, cy + 8.4, NOTAS[0], 2.6); T(cx + 16, cy + 4.8, NOTAS[1], 2.6);
    T(cx + pad, cy + 1.3, `REVISÓ / APROBÓ: ______________ (ingeniero calculista habilitado) · Formato ${info.formato}`, 2.2);
    // notas propias de la lámina, a la izquierda del cajetín
    const nx = x0 + 4, hh = 2.3, maxC = Math.floor((cx - nx - 4) / (TXTW * hh)), wrapped = [];
    (d.notes || []).forEach((t) => { let rest = t; while (rest.length > maxC) { let k = rest.lastIndexOf(" ", maxC); if (k < 10) k = maxC; wrapped.push(rest.slice(0, k)); rest = rest.slice(k + 1); } wrapped.push(rest); });
    const nmax = Math.floor((CAJ.h - 2) / (hh * 1.55)), nl = wrapped.slice(0, nmax);
    nl.forEach((t, i) => T(nx, cy + 2 + (nl.length - 1 - i) * hh * 1.55, t, hh));
  }
  function buildSheet(sh, ctx, idx, nSheets, bom) {
    const reg = (W, H) => ({ x0: 25, y0: 10 + STRIP + CAJ.h + 5, x1: W - 15, y1: H - 15 });
    let best = null, lastFit = null;
    outer: for (const [fn, W, H] of FORMATS) {
      const r = reg(W, H);
      for (const den of DENS) {
        const d = new Dwg(); sh.fn(d, 1 / den, ctx);
        const bb = d.bbox();
        if (bb[2] - bb[0] <= r.x1 - r.x0 && bb[3] - bb[1] <= r.y1 - r.y0) {          // primera escala (la más fina) que cabe en este formato
          lastFit = { fn, W, H, den, d, r, bb };
          if (den <= sh.maxDen) { best = lastFit; break outer; }
          break;
        }
      }
    }
    best = best || lastFit;
    if (!best) { const [fn, W, H] = FORMATS[2], d = new Dwg(); sh.fn(d, 1 / 200, ctx); best = { fn, W, H, den: 200, d, r: reg(W, H), bb: d.bbox() }; }
    const { d, W, H, r, bb } = best;
    d.translate((r.x0 + r.x1) / 2 - (bb[0] + bb[2]) / 2, (r.y0 + r.y1) / 2 - (bb[1] + bb[3]) / 2);
    const masa = sh.subs ? sh.subs.reduce((s, k) => s + (bom.bySub[k] || 0), 0) : bom.total;
    frame(d, W, H, ctx, { titulo: sh.titulo, codigo: sheetCode(sh), escala: sh.id === "IZAJE-00" ? `1:${nf(best.den)} (ubicación 1:20)` : `1:${nf(best.den)}`, hoja: `${idx + 1}/${nSheets}`, masa, masaTotal: bom.total, formato: best.fn });
    return { id: sh.id, code: sheetCode(sh), titulo: sh.titulo, dwg: d, W, H, formato: best.fn, den: best.den, masa };
  }
  function buildSheets(P, A, opt) {
    const ctx = ctxOf(P, A, opt && opt.fecha), bom = buildBOM(P, A);
    return { ctx, bom, sheets: SHEETS.map((sh, i) => buildSheet(sh, ctx, i, SHEETS.length, bom)) };
  }

  /* ====================================================================== */
  /* 6. Escritura DXF R12                                                    */
  /* ====================================================================== */
  const SUBST = { "≥": ">=", "≤": "<=", "→": "->", "–": "-", "—": "-", "−": "-", "Δ": "Delta", "μ": "µ", "φ": "phi", "σ": "sigma", "≈": "~", "’": "'", "“": '"', "”": '"', "τ": "tau", "η": "eta", "π": "pi", "√": "raiz", "…": "..." };
  const dxfStr = (s) => String(s).replace(/[^\x20-\x7e -ÿ]/g, (ch) => SUBST[ch] || "?");
  const ff = (v) => { const s = (+v).toFixed(4); return s.indexOf(".") < 0 ? s : s.replace(/0+$/, "").replace(/\.$/, ".0"); };
  function toDXF(d, W, H) {
    const o = [], g = (c, v) => o.push(String(c), String(v));
    g(0, "SECTION"); g(2, "HEADER");
    g(9, "$ACADVER"); g(1, "AC1009"); g(9, "$DWGCODEPAGE"); g(3, "ANSI_1252"); g(9, "$INSBASE"); g(10, "0.0"); g(20, "0.0"); g(30, "0.0");
    g(9, "$EXTMIN"); g(10, "0.0"); g(20, "0.0"); g(30, "0.0"); g(9, "$EXTMAX"); g(10, ff(W)); g(20, ff(H)); g(30, "0.0");
    g(9, "$LIMMIN"); g(10, "0.0"); g(20, "0.0"); g(9, "$LIMMAX"); g(10, ff(W)); g(20, ff(H)); g(9, "$LTSCALE"); g(40, "1.0");
    g(0, "ENDSEC");
    g(0, "SECTION"); g(2, "TABLES");
    g(0, "TABLE"); g(2, "LTYPE"); g(70, 3);
    g(0, "LTYPE"); g(2, "CONTINUOUS"); g(70, 0); g(3, "Solid line"); g(72, 65); g(73, 0); g(40, "0.0");
    g(0, "LTYPE"); g(2, "DASHED"); g(70, 0); g(3, "Dashed"); g(72, 65); g(73, 2); g(40, "6.0"); g(49, "4.0"); g(49, "-2.0");
    g(0, "LTYPE"); g(2, "CENTER"); g(70, 0); g(3, "Center"); g(72, 65); g(73, 4); g(40, "18.0"); g(49, "12.0"); g(49, "-2.0"); g(49, "2.0"); g(49, "-2.0");
    g(0, "ENDTAB");
    g(0, "TABLE"); g(2, "LAYER"); g(70, LAYERS.length);
    LAYERS.forEach(([n, col, lt]) => { g(0, "LAYER"); g(2, n); g(70, 0); g(62, col); g(6, lt); });
    g(0, "ENDTAB");
    g(0, "TABLE"); g(2, "STYLE"); g(70, 1); g(0, "STYLE"); g(2, "STANDARD"); g(70, 0); g(40, "0.0"); g(41, "1.0"); g(50, "0.0"); g(71, 0); g(42, "2.5"); g(3, "txt"); g(4, ""); g(0, "ENDTAB");
    g(0, "ENDSEC");
    g(0, "SECTION"); g(2, "BLOCKS"); g(0, "ENDSEC");
    g(0, "SECTION"); g(2, "ENTITIES");
    d.e.forEach((e) => {
      if (e.t === "LINE") { g(0, "LINE"); g(8, e.l); g(10, ff(e.x1)); g(20, ff(e.y1)); g(30, "0.0"); g(11, ff(e.x2)); g(21, ff(e.y2)); g(31, "0.0"); }
      else if (e.t === "CIRCLE") { g(0, "CIRCLE"); g(8, e.l); g(10, ff(e.cx)); g(20, ff(e.cy)); g(30, "0.0"); g(40, ff(e.r)); }
      else if (e.t === "ARC") { g(0, "ARC"); g(8, e.l); g(10, ff(e.cx)); g(20, ff(e.cy)); g(30, "0.0"); g(40, ff(e.r)); g(50, ff(((e.a0 % 360) + 360) % 360)); g(51, ff(((e.a1 % 360) + 360) % 360)); }
      else if (e.t === "POLY") {
        g(0, "POLYLINE"); g(8, e.l); g(66, 1); g(10, "0.0"); g(20, "0.0"); g(30, "0.0"); g(70, e.closed ? 1 : 0);
        e.pts.forEach(([x, y]) => { g(0, "VERTEX"); g(8, e.l); g(10, ff(x)); g(20, ff(y)); g(30, "0.0"); });
        g(0, "SEQEND"); g(8, e.l);
      } else if (e.t === "TEXT") {
        const j = e.al === "c" ? 1 : e.al === "r" ? 2 : 0;
        g(0, "TEXT"); g(8, e.l); g(10, ff(e.x)); g(20, ff(e.y)); g(30, "0.0"); g(40, ff(e.h)); g(1, dxfStr(e.s));
        if (e.rot) g(50, ff(((e.rot % 360) + 360) % 360));
        if (j) { g(72, j); g(11, ff(e.x)); g(21, ff(e.y)); g(31, "0.0"); }
      }
    });
    g(0, "ENDSEC"); g(0, "EOF");
    return o.join("\r\n") + "\r\n";
  }
  const latin1Bytes = (s) => { const u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i) & 255; return u; };
  const utf8Bytes = (s) => (typeof TextEncoder !== "undefined" ? new TextEncoder().encode(s) : Uint8Array.from(Buffer.from(s, "utf8")));

  /* ====================================================================== */
  /* 7. SVG y página HTML de impresión                                       */
  /* ====================================================================== */
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const STYLE = { CONTORNO: ["#000", 0.35, ""], OCULTO: ["#444", 0.22, "4 2"], EJES: ["#c00000", 0.18, "12 2 2 2"], COTAS: ["#006400", 0.18, ""], TEXTO: ["#000", 0, ""], CAJETIN: ["#000", 0.35, ""], ACHURADO: ["#7a7a7a", 0.1, ""] };
  function toSVG(sheet, standalone) {
    const { dwg, W, H } = sheet, f2 = (v) => (+v).toFixed(3).replace(/\.?0+$/, "") || "0", Y = (y) => H - y, o = [];
    const st = (l) => { const [c, w, da] = STYLE[l] || STYLE.CONTORNO; return `stroke="${c}" stroke-width="${w}" fill="none"${da ? ` stroke-dasharray="${da}"` : ""}`; };
    dwg.e.forEach((e) => {
      if (e.t === "LINE") o.push(`<line x1="${f2(e.x1)}" y1="${f2(Y(e.y1))}" x2="${f2(e.x2)}" y2="${f2(Y(e.y2))}" ${st(e.l)}/>`);
      else if (e.t === "POLY") o.push(`<${e.closed ? "polygon" : "polyline"} points="${e.pts.map(([x, y]) => f2(x) + "," + f2(Y(y))).join(" ")}" ${st(e.l)} stroke-linejoin="round"/>`);
      else if (e.t === "CIRCLE") o.push(`<circle cx="${f2(e.cx)}" cy="${f2(Y(e.cy))}" r="${f2(e.r)}" ${st(e.l)}/>`);
      else if (e.t === "ARC") {
        const a0 = e.a0 * D2R, sw = (((e.a1 - e.a0) % 360) + 360) % 360, a1 = (e.a0 + sw) * D2R;
        o.push(`<path d="M${f2(e.cx + e.r * Math.cos(a0))} ${f2(Y(e.cy + e.r * Math.sin(a0)))}A${f2(e.r)} ${f2(e.r)} 0 ${sw > 180 ? 1 : 0} 0 ${f2(e.cx + e.r * Math.cos(a1))} ${f2(Y(e.cy + e.r * Math.sin(a1)))}" ${st(e.l)}/>`);
      } else if (e.t === "TEXT") {
        const anchor = e.al === "c" ? "middle" : e.al === "r" ? "end" : "start";
        o.push(`<text x="${f2(e.x)}" y="${f2(Y(e.y))}" font-size="${f2(e.h)}" text-anchor="${anchor}" fill="#000"${e.rot ? ` transform="rotate(${f2(-e.rot)} ${f2(e.x)} ${f2(Y(e.y))})"` : ""}>${esc(e.s)}</text>`);
      }
    });
    return `<svg ${standalone ? 'xmlns="http://www.w3.org/2000/svg" ' : ""}viewBox="0 0 ${W} ${H}" width="${W}mm" height="${H}mm" font-family="Arial, Helvetica, sans-serif" role="img" aria-label="${esc(sheet.code + " " + sheet.titulo)}"><rect width="${W}" height="${H}" fill="#fff"/>${o.join("")}</svg>`;
  }
  function printHTML(pkg, subtitle) {
    const pages = pkg.sheets.map((s) => `<section class="sheet ${s.formato.toLowerCase()}" aria-label="${esc(s.code)}">${toSVG(s, false)}</section>`).join("\n");
    return `<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TT300-C · Láminas de dibujo Rev. ${REV}</title>
<style>
:root{color-scheme:light}
html,body{margin:0;background:#e9ecef;color:#000;font:14px/1.4 system-ui,Arial,sans-serif}
.bar{position:sticky;top:0;z-index:2;background:#fff;border-bottom:1px solid #bbb;padding:8px 14px;display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center}
.bar b{font-size:15px}.bar span{color:#333;font-size:12.5px}
.bar button{font:600 13px system-ui,Arial,sans-serif;padding:6px 12px;border:1px solid #1f5fbf;border-radius:7px;background:#1f5fbf;color:#fff;cursor:pointer}
.warn{background:#fff;color:#000;border:2px solid #000;margin:12px auto;max-width:1100px;padding:8px 12px;font-weight:700;font-size:13px}
.sheet{background:#fff;margin:14px auto;box-shadow:0 1px 6px rgba(0,0,0,.25);max-width:100%;overflow:auto}
.sheet svg{display:block;width:100%;height:auto;background:#fff}
.a3{width:min(1400px,98vw)}.a2{width:min(1400px,98vw)}.a1{width:min(1400px,98vw)}
@page a3{size:420mm 297mm;margin:0}@page a2{size:594mm 420mm;margin:0}@page a1{size:841mm 594mm;margin:0}
@media print{
  html,body{background:#fff}.bar,.warn{display:none}
  .sheet{margin:0;box-shadow:none;max-width:none;overflow:visible;break-after:page;page-break-after:always}
  .a3{page:a3;width:420mm;height:297mm}.a2{page:a2;width:594mm;height:420mm}.a1{page:a1;width:841mm;height:594mm}
  .sheet svg{width:100%;height:100%}
}
</style></head><body>
<div class="bar"><b>TT300-C · Láminas de dibujo Rev. ${REV}</b><span>${esc(subtitle)}</span><button onclick="window.print()">Imprimir / guardar como PDF</button></div>
<div class="warn">${esc(ADVERTENCIA)}</div>
${pages}
</body></html>`;
  }

  /* ====================================================================== */
  /* 8. ZIP (sin compresión)                                                 */
  /* ====================================================================== */
  let CRC = null;
  function crc32(u8) {
    if (!CRC) { CRC = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; CRC[n] = c >>> 0; } }
    let c = 0xffffffff; for (let i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0;
  }
  function zipStore(files) {                                       // files: [{name, data: Uint8Array}] → Uint8Array
    const now = new Date(), dt = ((now.getFullYear() - 1980) << 9 | (now.getMonth() + 1) << 5 | now.getDate()) & 0xffff, tm = (now.getHours() << 11 | now.getMinutes() << 5 | (now.getSeconds() >> 1)) & 0xffff;
    const parts = [], cen = []; let off = 0;
    const u16 = (v) => [v & 255, (v >>> 8) & 255], u32 = (v) => [v & 255, (v >>> 8) & 255, (v >>> 16) & 255, (v >>> 24) & 255];
    files.forEach((f) => {
      const nm = utf8Bytes(f.name), crc = crc32(f.data), n = f.data.length;
      const lh = Uint8Array.from([0x50, 0x4b, 3, 4, ...u16(20), ...u16(0x0800), ...u16(0), ...u16(tm), ...u16(dt), ...u32(crc), ...u32(n), ...u32(n), ...u16(nm.length), ...u16(0)]);
      parts.push(lh, nm, f.data);
      cen.push(Uint8Array.from([0x50, 0x4b, 1, 2, ...u16(20), ...u16(20), ...u16(0x0800), ...u16(0), ...u16(tm), ...u16(dt), ...u32(crc), ...u32(n), ...u32(n), ...u16(nm.length), ...u16(0), ...u16(0), ...u16(0), ...u16(0), ...u32(0), ...u32(off)]), nm);
      off += lh.length + nm.length + n;
    });
    const cdLen = cen.reduce((s, a) => s + a.length, 0);
    const end = Uint8Array.from([0x50, 0x4b, 5, 6, ...u16(0), ...u16(0), ...u16(files.length), ...u16(files.length), ...u32(cdLen), ...u32(off), ...u16(0)]);
    const all = parts.concat(cen, [end]), out = new Uint8Array(all.reduce((s, a) => s + a.length, 0)); let p = 0; all.forEach((a) => { out.set(a, p); p += a.length; });
    return out;
  }

  /* ====================================================================== */
  /* 9. Paquete completo                                                     */
  /* ====================================================================== */
  function buildPackage(P, A, opt) {
    opt = opt || {};
    const pkg = buildSheets(P, A, opt), ifc = A.R.ifc, fecha = pkg.ctx.fecha;
    const files = [];
    pkg.sheets.forEach((s) => {
      files.push({ name: `DXF/${s.code}.dxf`, data: latin1Bytes(toDXF(s.dwg, s.W, s.H)), mime: "application/dxf", kind: "dxf", sheet: s.id });
      files.push({ name: `SVG/${s.code}.svg`, data: utf8Bytes('<?xml version="1.0" encoding="UTF-8"?>\n' + toSVG(s, true)), mime: "image/svg+xml", kind: "svg", sheet: s.id });
    });
    const html = printHTML(pkg, ifaceName(P, ifc) + " · " + woodText(P) + " · " + fmtDate(fecha));
    files.push({ name: "TT300C_laminas_impresion.html", data: utf8Bytes(html), mime: "text/html", kind: "html" });
    files.push({ name: "TT300C_lista_materiales.csv", data: utf8Bytes(bomCSV(pkg.bom, P, A, fecha)), mime: "text/csv", kind: "csv" });
    if (!opt.noDesign) files.push({ name: "TT300-C_design.json", data: utf8Bytes(designJSON(buildDesign(P, A))), mime: "application/json", kind: "json" });
    const leeme = [`TT300-C · Paquete de dibujo Rev. ${REV} · ${fmtDate(fecha)}`, "",
      ADVERTENCIA, ...NOTAS, "",
      `Alternativa de interfaz: ${ifaceName(P, ifc)}`, `Fijación: ${fixText(P, ifc)}`, `Cubierta: ${woodText(P)}`, `Masa total (lista de materiales): ${nf(pkg.bom.total)} kg (núcleo: ${nf(pkg.bom.core)} kg)`, "",
      "Contenido:", "  DXF/   una lámina DXF (R12, capas CONTORNO, OCULTO, EJES, COTAS, TEXTO, CAJETIN, ACHURADO; unidades de papel en mm; codificación ANSI_1252)",
      "  SVG/   las mismas láminas en SVG", "  TT300C_laminas_impresion.html   páginas de impresión (Ctrl+P → Guardar como PDF)", "  TT300C_lista_materiales.csv   lista de materiales (separador ;, coma decimal, UTF-8 con BOM)",
      "  TT300-C_design.json   diseño completo (mismo esquema que tools/export_design.js) para el generador completo (PDF, DXF, STEP, Excel)", "",
      "Lo que el núcleo de cálculo no define se dibuja como contorno y se rotula «A DEFINIR».", ""].join("\r\n");
    files.push({ name: "LEEME.txt", data: utf8Bytes(leeme), mime: "text/plain", kind: "txt" });
    return { files, sheets: pkg.sheets, bom: pkg.bom, ctx: pkg.ctx, zip: () => zipStore(files.map((f) => ({ name: "TT300C_paquete_dibujo/" + f.name, data: f.data }))) };
  }

  const api = { ADVERTENCIA, NOTAS, REV, SHEETS, buildDesign, designJSON, buildBOM, bomCSV, buildSheets, buildPackage, toDXF, toSVG, printHTML, zipStore, crc32, ifaceName, fixText, woodText, nf, latin1Bytes };
  return api;
})();
if (typeof module !== "undefined") module.exports = PLANOS;
