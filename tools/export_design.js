/* Exporta el diseño completo (parámetros + resultados derivados) para el generador de planos.
   Uso: node tools/export_design.js [parametros.json] > design.json
   El generador de planos solo dibuja; toda magnitud sale de este archivo (fuente única). */
const fs = require("fs");
const TT = require("../packages/core/tt300c.js"), AG = require("../packages/agents/agentes.js");
const P = Object.assign(TT.defaults(), process.argv[2] ? JSON.parse(fs.readFileSync(process.argv[2], "utf8")) : {});
const val = AG.validate(P);
if (val.some((v) => v.lvl === "error")) { console.error(val.filter((v) => v.lvl === "error").map((v) => v.msg).join("\n")); process.exit(2); }
const A = TT.analyze(P), R = A.R, K = R.K, D2R = Math.PI / 180;
const bg = TT.bracketGeo(P, K);
// posiciones de cilindro: giro horario (a_eye + k·360/n) y antihorario (espejo respecto del eje y)
function cylPos(aEdeg, mirror) {
  const aE = aEdeg * D2R, E = [P.R_eye * Math.cos(aE), P.R_eye * Math.sin(aE)];
  const at = (del) => {
    const th = mirror ? aE + del : aE - del, Pp = [P.R_pin * Math.cos(th), P.R_pin * Math.sin(th)];
    const L = Math.hypot(Pp[0] - E[0], Pp[1] - E[1]), u = [(Pp[0] - E[0]) / L, (Pp[1] - E[1]) / L];
    return { pin: Pp, rod: [Pp[0] - P.d_dog * u[0], Pp[1] - P.d_dog * u[1]], u, phi: Math.atan2(u[1], u[0]) / D2R };
  };
  const a0 = at(K.dr), a1 = at(K.dend), ae = at(K.de);
  let dphi = a1.phi - a0.phi; if (dphi > 180) dphi -= 360; if (dphi < -180) dphi += 360;
  return { eye: E, aE: aEdeg, retracted: a0, engage: ae, end: a1, phiMean: a0.phi + dphi / 2 };
}
const cw = [], ccw = [];
for (let k = 0; k < P.n_cyl; k++) { const a = P.a_eye + 360 * k / P.n_cyl; cw.push(cylPos(a, false)); ccw.push(cylPos(180 - a, true)); }
const out = {
  proyecto: "TT300-C", fecha: new Date().toISOString().slice(0, 10), P,
  verdict: A.verdict, validacion: val,
  derivados: {
    W: R.W, N: R.N, ND: R.ND, q_max: R.q_max, q_avg: R.q_avg, Fstall: R.Fstall, Falarm: R.Falarm, Fret: R.Fret, A: R.A, Aann: R.Aann,
    hax: R.hax, prIn: TT.prIn(P), pinClear: TT.pinClear(P), forkH: TT.forkH(P), bracket: bg, tRev: R.tRev, tCycle: R.tCycle, muMax_ref: R.muMax(P.r_ef),
    K: { de: K.de / D2R, dend: K.dend / D2R, dr: K.dr / D2R, armMin: K.armMin, armMax: K.armMax, s_req: K.s_req, margin: K.margin, chord: K.chord, gap: K.gap, swing: K.swing / D2R, RrodMin: K.RrodMin, RrodMax: K.RrodMax },
    casos: R.cases.map((c) => ({ id: c.id, nombre: c.name, mu: c.mu, r: c.r, T: c.T, F: c.F, p: c.p, FS: c.FS, gira: c.turns })),
    masas: R.m,
  },
  pasadores: Array.from({ length: P.N_pin }, (_, k) => (180 / P.N_pin + 360 * k / P.N_pin)),
  nervios: Array.from({ length: P.N_rib }, (_, k) => 360 * k / P.N_rib),
  almas: TT.parseRings(P.rings),
  cilindros: { horario: cw, antihorario: ccw },
  verificaciones: A.checks.map((c) => ({ grp: c.grp, nombre: c.name, formula: c.formula, dem: c.dem, cap: c.cap, unidad: c.unit, fu: c.fu, estado: c.st, ref: c.ref })),
};
process.stdout.write(JSON.stringify(out, null, 1));
