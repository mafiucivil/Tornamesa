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
    Kguide: R.Kguide, Rguide: R.Rguide,
    K: { armMin: K.armMin, armMax: K.armMax, s_req: K.s_req, margin: K.margin, chord: K.chord, gap: K.gap, radial: K.radial, DeltaMax: K.DeltaMax,
         L_s: K.L_s, Lg: K.Lg, front: K.front, rear: K.rear, y_eye: K.y_eye, y_rp0: K.y_rp0, y_rp1: K.y_rp1, L_bed: K.L_bed, Y_bed: K.Y_bed, zc0: K.zc0, lever: K.lever, mouthX: K.mouthX, inset: K.inset },
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
