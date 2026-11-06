/* Exporta el diseño completo (parámetros + resultados derivados) para el generador de planos.
   Uso: node tools/export_design.js [parametros.json] > design.json
   El generador de planos solo dibuja; toda magnitud sale de este archivo (fuente única). */
const fs = require("fs");
const TT = require("../packages/core/tt300c.js"), AG = require("../packages/agents/agentes.js");
const P = Object.assign(TT.defaults(), process.argv[2] ? JSON.parse(fs.readFileSync(process.argv[2], "utf8")) : {});
const val = AG.validate(P);
if (val.some((v) => v.lvl === "error")) { console.error(val.filter((v) => v.lvl === "error").map((v) => v.msg).join("\n")); process.exit(2); }
const A = TT.analyze(P), R = A.R, K = R.K, D2R = Math.PI / 180;
const bg = TT.bracketGeo(P);
// posiciones de cilindro (accionamiento guiado): lado sx = ±1 (guía en x = sx·x_g), sentido de empuje dy = ±1 en y.
// sx·dy = +1 → giro antihorario en planta; −1 → horario. Cada par es simétrico respecto del centro (par puro).
function cylPos(sx, dy) {
  const g = TT.guideGeo(P), R = P.R_pin, ph = g.pitch / 2;
  const Y = (y) => dy * y, X = sx * P.x_g;
  const pin = (th) => [sx * R * Math.cos(th), dy * R * Math.sin(th)];
  return {
    side: sx, dir: dy, x: X, eye: [X, Y(g.y_eye)], phiMean: dy > 0 ? 90 : -90,
    rodRetracted: [X, Y(g.y_rp0)], rodEngage: [X, Y(g.y_rp0 + P.s_free)], rodEnd: [X, Y(g.y_rp1)],
    pinStart: pin(-ph), pinEnd: pin(ph), shoeFront: g.front, shoeRear: g.rear, mouthX: sx * g.mouthX,
  };
}
const ccw = [cylPos(1, 1), cylPos(-1, -1)], cw = [cylPos(1, -1), cylPos(-1, 1)];
const out = {
  proyecto: "TT300-C", fecha: new Date().toISOString().slice(0, 10), P,
  verdict: A.verdict, validacion: val,
  derivados: {
    W: R.W, N: R.N, ND: R.ND, q_max: R.q_max, q_avg: R.q_avg, Fstall: R.Fstall, Falarm: R.Falarm, Fret: R.Fret, A: R.A, Aann: R.Aann,
    hax: R.hax, prIn: TT.prIn(P), pinClear: TT.pinClear(P), forkH: TT.forkH(P), bracket: bg, tRev: R.tRev, tCycle: R.tCycle, muMax_ref: R.muMax(P.r_ef),
    Kguide: R.Kguide, Rguide: R.Rguide, stallMax: R.stallMax, chaflan: TT.chamferGeo(P),
    K: { armMin: K.armMin, armMax: K.armMax, s_req: K.s_req, margin: K.margin, chord: K.chord, gap: K.gap, radial: K.radial, DeltaMax: K.DeltaMax,
         L_s: K.L_s, Lg: K.Lg, front: K.front, rear: K.rear, y_eye: K.y_eye, y_rp0: K.y_rp0, y_rp1: K.y_rp1, L_bed: K.L_bed, Y_bed: K.Y_bed, zc0: K.zc0, lever: K.lever, mouthX: K.mouthX, inset: K.inset, tipX: K.tipX, travel: K.travel, pocketEnd: K.pocketEnd, shoeTop: K.shoeTop },
    casos: R.cases.map((c) => ({ id: c.id, nombre: c.name, mu: c.mu, r: c.r, T: c.T, F: c.F, p: c.p, FS: c.FS, gira: c.turns })),
    masas: R.m,
  },
  pasadores: Array.from({ length: P.N_pin }, (_, k) => (180 / P.N_pin + 360 * k / P.N_pin)),
  nervios: Array.from({ length: P.N_rib }, (_, k) => 360 * k / P.N_rib),
  almas: TT.parseRings(P.rings),
  cilindros: { horario: cw, antihorario: ccw },
  grupos: TT.PARAM_GROUPS.map((g) => ({ id: g.id, titulo: g.t, p: g.p.map(([id, lab, u]) => ({ id, lab, u })) })),
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
  escenarios: (() => { const sc = AG.scenarios(A); return { mus: sc.mus, rs: sc.rs, grid: sc.grid, loads: sc.loads, classes: sc.classes, ifaces: sc.ifaces }; })(),
  interfazChecks: (() => { const chk = (k) => TT.analyze(Object.assign({}, P, { opt_ss: k === 1 ? 1 : 0, opt_uhmw: k === 2 ? 1 : 0, opt_bz: k === 3 ? 1 : 0 }), { noFEA: true }).checks.filter((c) => c.grp === (k === 3 ? "Interfaz bronce" : "Interfaz inox"))
    .map((c) => ({ nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref })); return { A: chk(1), B: chk(2), C: chk(3) }; })(),
  bombaBarrido: [[1.8, 0], [5, 0], [10, 0], [10, 20], [20, 0]].map(([q, qr]) => { const RR = TT.compute(Object.assign({}, P, { Q_pump: q, Q_ret: qr })); return { Q: q, Qr: RR.pump.Qr, tRev: RR.tRev, tCycle: RR.tCycle, Pmotor: RR.pump.Pmotor, vRet: RR.pump.vRet }; }),
  cubierta: (() => { const A1 = TT.analyze(Object.assign({}, P, { opt_wood: 1, opt_bz: 0 }), { noFEA: true }), A0 = TT.analyze(Object.assign({}, P, { opt_wood: 0 }), { noFEA: true });
    return { dMasa: A1.R.m.total - A0.R.m.total, mWood: A1.R.m.wood, checks: A1.checks.filter((c) => c.grp === "Cubierta").map((c) => ({ nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref })) }; })(),
  mercado: TT.market(P), capCil: TT.capacityByCyl(P, [1, 2]), bomba: R.pump,
  revisionCruzada: AG.crossCheck(A),
  auditoria: AG.audit(A.checks),
  // Geometría de la interfaz que el núcleo calcula pero no entrega como parámetro (se extrae de sus propias verificaciones, sin recalcular):
  //  - largo de cada tope (L_tope) y canto radial disponible (R_o − R_i − 100), en el orden en que el núcleo los emite
  //  - junta de dilatación calculada, profundidad útil de los tapones de grafito, ancho de cada sector
  //  - constantes del núcleo que fijan la geometría de la mesa (diámetros del alojamiento de la tapa y del buje)
  interfazGeom: (() => {
    const ck = A.checks, byName = (re) => ck.filter((c) => re.test(c.name));
    const topes = byName(/largo del tope frente al canto radial/).map((c) => ({ pieza: c.name.split(":")[0], L: c.dem, Lav: c.cap, n: Number((c.name.match(/\((\d+) (sectores|pastillas)\)/) || [])[1]) || null }));
    const juntas = byName(/(crecimiento por dilatación de la cuerda|junta de dilatación entre sectores)/).map((c) => ({ pieza: c.name.split(":")[0], j: c.dem }));
    const tap = byName(/Tapones de grafito: profundidad restante/)[0];
    const sector = byName(/masa del sector/).map((c) => ({ pieza: c.name.split(":")[0], m: c.dem }));
    const ifc = R.ifc;
    return { topes, juntas, tapon_prof_max: tap ? tap.cap : null, tapon_prof_frac: tap && ifc.tbz ? tap.cap / ifc.tbz : null, sector_masa: sector,
      hole_top: P.D_piv + 80, d_bush: P.D_piv + 30, nota: "hole_top y d_bush reproducen las constantes de massesMesa() del núcleo (D_piv + 80 y D_piv + 30)" };
  })(),
  verificaciones: A.checks.map((c) => ({ grp: c.grp, nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref })),
};
process.stdout.write(JSON.stringify(out, null, 1));
