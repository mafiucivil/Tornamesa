/* Datos de entrada del estudio de la plancha base bajo el soporte del ojal E (docs/qa/plancha_base_soporte_E.md), solo con la API pública del núcleo.
   Uso: node docs/qa/plancha_base_soporte_E/exportar.js '{"opt_uhmw":1}' salida.json   (sin argumentos: valores por defecto) */
const path = require("path"), fs = require("fs");
const TT = require(path.join(__dirname, "..", "..", "..", "packages", "core", "tt300c.js"));
const P = Object.assign(TT.defaults(), JSON.parse(process.argv[2] || "{}"));
const A = TT.analyze(P, { noFEA: true }), R = A.R, sg = R.sup, K = R.K;
if (TT.driveMode(P) !== 2 || !K.ok) throw new Error("el estudio es del modo pivotado con cinemática válida");
const out = {
  P: { B: P.B, t_base: P.t_base, E: P.E, nu: P.nu, Fy: P.Fy, Nd: P.Nd, D_top: P.D_top, rim_h: P.rim_h, rim_t: P.rim_t, n_cyl: P.n_cyl },
  E: K.E, h: (sg.hU + sg.hL) / 2, walls: sg.walls.map((w) => w.rect),
  psiA: sg.sweep.estados.map((q) => q.psi), psiH: sg.sweep.horario.map((q) => q.psi),           // marco local del soporte (= real en el cilindro 1)
  Fstall: R.Fstall * 1e3, Fret: Math.PI / 4 * (P.D_bore ** 2 - P.d_rod ** 2) * P.p_ret / 10,       // N
  Wd: R.Wd * 1e3, mdogs: R.m.dogs, Ri: R.Ri, Ro: R.Ro, m: R.m, msup: sg.m,
};
fs.writeFileSync(process.argv[3] || "entrada.json", JSON.stringify(out));
console.log("h", out.h, "mm; F_calado", (out.Fstall / 1e3).toFixed(1), "kN; F_ret", (out.Fret / 1e3).toFixed(1), "kN; W_mesa", ((out.Wd + out.mdogs * 9.80665) / 1e3).toFixed(2), "kN");
