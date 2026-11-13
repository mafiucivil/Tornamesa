/* Datos de entrada del estudio de la plancha base en el modo guiado (drive_mode = 1; docs/qa/plancha_base_modo_guiado.md), solo con la API pública del núcleo.
   Uso: node docs/qa/plancha_base_modo_guiado/exportar.js '{"opt_uhmw":1}' salida.json   (sin argumentos: valores por defecto con drive_mode = 1)
   Marco: planta x, y (mm) con O en el centro; cilindro 1 = lado +x, empuje +y (giro antihorario); el cilindro 2 por rotación de 180°. */
const path = require("path"), fs = require("fs");
const TT = require(path.join(__dirname, "..", "..", "..", "packages", "core", "tt300c.js"));
const P = Object.assign(TT.defaults(), { drive_mode: 1 }, JSON.parse(process.argv[2] || "{}"));
const A = TT.analyze(P, { noFEA: true }), R = A.R, K = R.K, c = R.camG, bg = TT.bracketGeo(P);
if (TT.driveMode(P) !== 1 || !K.ok || !c) throw new Error("el estudio es del modo guiado con la leva de reenganche y cinemática válida");
const fab = TT.designDrive(P, R).levaGuiada.fabricacion;
const r = P.d_pin / 2, yMid = (K.front - K.rear) / 2;
// estados del empuje: pasador tomado en θ (toma, medio y final de la carrera); reacciones de guía por unidad de F_pas (driveAt: mismo modelo que compute)
const ths = [-K.pitch / 2, 0, K.pitch / 2];
const shoe = ths.map((th) => { const d = TT.driveAt(P, th, "nom"), yp = P.R_pin * Math.sin(th), yrp = yp - P.l_p, yr = yrp + yMid - K.Lg / 2;
  return { th, xc: P.R_pin * Math.cos(th), yc: yp - r, y_rp: yrp, y_r: yr, y_f: yr + K.Lg, y_ini: yrp - K.rear, y_fin: yrp + K.front, rf: d.Rf / d.Fp, rr: d.Rr / d.Fp, h: d.H / d.Fp }; });
const out = {
  P: { B: P.B, t_base: P.t_base, E: P.E, nu: P.nu, Fy: P.Fy, Nd: P.Nd, D_top: P.D_top, n_cyl: P.n_cyl, x_g: P.x_g, R_pin: P.R_pin, d_pin: P.d_pin, l_p: P.l_p, dog_b: P.dog_b, eta_c: P.eta_c, mu_s: P.mu_s,
    t_bed: P.t_bed, w_bed: P.w_bed, w_slot: P.w_slot, h_slot: P.h_slot, w_tee: P.w_tee, h_tee: P.h_tee, n_br: P.n_br, t_ch: P.t_ch, L_ch: P.L_ch, cam_ls: P.cam_ls, beta_ch: P.beta_ch, cam_alpha: P.cam_alpha },
  // soporte del cilindro = ménsula del ojal trasero: dos mejillas soldadas a la base (marco local con origen en el ojal E, igual que el soporte del modo 2)
  E: [P.x_g, K.y_eye], h: R.hax,
  walls: [[bg.Win / 2, bg.Win / 2 + P.t_ch, -bg.rear, P.L_ch - bg.rear], [-bg.Win / 2 - P.t_ch, -bg.Win / 2, -bg.rear, P.L_ch - bg.rear]],
  mensula: bg,
  // bancada (y ∈ ±Y_bed) y su prolongación ensanchada bajo los pórticos del riel-leva (y ∈ ±(Y_bed … Y_bed + l_soporte))
  bancada: { x: [P.x_g - P.w_bed / 2, P.x_g + P.w_bed / 2], y: [-K.Y_bed, K.Y_bed] }, prolongacion: fab.prolongacion_bancada_local.map((q) => ({ x: q.x, y: q.y })),
  patas: fab.porticos.patas_local.map((q) => ({ x: q.x, y: q.y })), y_soportes_riel: [-c.Lsp / 2, c.Lsp / 2], Lsp: c.Lsp,
  zT: P.t_bed - P.h_slot / 2,                // reacción lateral de la guía (lengüeta en la ranura) sobre la cara superior de la plancha
  zF: c.zF - P.t_base,                       // seguidor del riel-leva sobre la cara superior de la plancha
  K: { front: K.front, rear: K.rear, L_s: K.L_s, Lg: K.Lg, pitch: K.pitch, y_rp0: K.y_rp0, y_rp1: K.y_rp1, y_eye: K.y_eye, Y_bed: K.Y_bed },
  shoe,
  Fstall: R.Fstall * 1e3, Fret: c.Fret, NT: c.NT, NRx: c.NRx, NR: c.NR, kR: c.kR,
  Wd: R.Wd * 1e3, mdogs: R.m.dogs, Ri: R.Ri, Ro: R.Ro, m: R.m, msup: R.m.brackets / P.n_br, mshoe: R.m.shoes / P.n_cyl, mcam: R.m.cam / P.n_cyl,
  verdict: A.verdict.estado_global,
};
fs.writeFileSync(process.argv[3] || "entrada.json", JSON.stringify(out));
console.log("h", out.h, "mm; F_calado", (out.Fstall / 1e3).toFixed(1), "kN; M = F·h", (out.Fstall * out.h / 1e6).toFixed(2), "kN·m; F_ret", (out.Fret / 1e3).toFixed(1), "kN; N_toma", (out.NT / 1e3).toFixed(1),
  "kN; z_seguidor", out.zF, "mm; ojal E", out.E.map((v) => v.toFixed(1)).join("; "), "; W_mesa", ((out.Wd + out.mdogs * 9.80665) / 1e3).toFixed(2), "kN");
