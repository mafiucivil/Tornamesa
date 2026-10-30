/* TT300 – motor de cálculo y FEA (N, mm, MPa salvo indicación). */
(function (root) {
  "use strict";
  const G = 9.80665, RHO = 7.85e-6; // kg/mm3

  const DEFAULTS = {
    // carga
    W_tf: 300, e: 150, phi_d: 1.10, D_load: 1600, H_frac: 0.055,
    // fricción
    mu_d: 0.20, mu_nom: 0.15, mu_cont: 0.25, mu_dry: 0.50, r_eff: 0.80, mu_g: 0.15, eta: 0.95, mu_piv: 0.20,
    // disco
    D_disc: 2000, t_top: 30, t_bot: 30, gap: 100, D_hub: 300, D_bore: 190, rings: "300, 550, 735", t_ring: 25,
    n_rib: 12, t_rib: 20, R_rib: 880, R_bar: 940, D_bar: 70, n_bar: 36, D_hole: 71, E_w: 12,
    // base
    BX: 2400, BY: 2000, TB: 80,
    // accionamiento
    D_cyl: 90, D_rod: 63, p_relief: 700, p_alarm: 600, stroke: 200, free: 36, L0: 450,
    X_cyl: 1085, Lg: 250, shoe_X0: 1020, pawl_L: 245, pawl_W: 85, pawl_H: 90, seat_R: 36, tip_off: 31.4, ch_x: 61, ch_y: 36,
    D_pin: 70, t_cheek: 40, cheek_gap: 80, eye_W: 70, L_cheek: 280, h_axis: 80,
    g_w: 40, g_h: 30, g_emb: 10, g_Lc: 150, D_piv: 150, L_bush: 100,
    // materiales
    Fy: 345, FEXX: 490, Fy_pawl: 800, Fy_pin: 650, Nd: 2.0, Es: 200000, nu: 0.3, q_allow: 10, p_bush: 30, q_ground: 1.0,
  };

  function ringsOf(p) {
    return String(p.rings).split(/[,;\s]+/).map(Number).filter((x) => x > 0).sort((a, b) => a - b);
  }

  function masses(p) {
    const R = p.D_disc / 2, TD = p.t_top + p.gap + p.t_bot, rings = ringsOf(p);
    const plate = (t) => (Math.PI * R * R - Math.PI * (p.D_hub / 2) ** 2 - p.n_bar * Math.PI * (p.D_hole / 2) ** 2) * t * RHO;
    const hub = Math.PI / 4 * (p.D_hub ** 2 - p.D_bore ** 2) * TD * RHO;
    const ring = rings.reduce((s, r) => s + 2 * Math.PI * r * p.t_ring * p.gap * RHO, 0);
    let ribL = p.R_rib - p.D_hub / 2;
    rings.forEach((r) => { if (r > p.D_hub / 2 && r < p.R_rib) ribL -= p.t_ring; });
    const rib = p.n_rib * p.t_rib * p.gap * ribL * RHO;
    const bars = p.n_bar * Math.PI / 4 * p.D_bar ** 2 * TD * RHO;
    const disc = plate(p.t_top) + plate(p.t_bot) + hub + ring + rib + bars;
    const base = p.BX * p.BY * p.TB * RHO;
    return { top: plate(p.t_top), bot: plate(p.t_bot), hub, ring, rib, ribL, bars, disc, base, total: disc + base + 420 };
  }

  // Coeficientes de Roark (Tabla 11.4 caso 8: 4 bordes empotrados, carga uniforme). a/b -> [beta1 (borde), alpha]
  const ROARK = [[1.0, 0.3078, 0.0138], [1.2, 0.3834, 0.0188], [1.4, 0.4356, 0.0226], [1.6, 0.4680, 0.0251],
                 [1.8, 0.4872, 0.0267], [2.0, 0.4974, 0.0277], [1e9, 0.5, 0.0284]];
  function roark(a, b) {
    const L = Math.max(a, b), S = Math.min(a, b), r = L / S;
    for (let i = 1; i < ROARK.length; i++) {
      if (r <= ROARK[i][0]) {
        const [r0, b0, a0] = ROARK[i - 1], [r1, b1, a1] = ROARK[i];
        const k = r1 > 1e8 ? Math.min(1, (r - r0) / 2) : (r - r0) / (r1 - r0);
        return { beta: b0 + k * (b1 - b0), alpha: a0 + k * (a1 - a0), b: S, a: L, ratio: r };
      }
    }
  }

  function panels(p) {
    const rings = ringsOf(p), out = [];
    const edges = [p.D_hub / 2].concat(rings);
    for (let i = 0; i < edges.length - 1; i++) {
      const r0 = edges[i] + (i === 0 ? 0 : p.t_ring / 2), r1 = edges[i + 1] - p.t_ring / 2;
      const rm = (r0 + r1) / 2, radial = r1 - r0;
      const circ = 2 * Math.PI * rm / p.n_rib - p.t_rib;
      out.push({ name: `R${edges[i]}–R${edges[i + 1]}`, radial, circ, rm });
    }
    return out;
  }

  function compute(pin) {
    const p = Object.assign({}, DEFAULTS, pin);
    const m = masses(p);
    const W = p.W_tf * G;                 // kN
    const Wd = m.disc * G / 1000;         // kN
    const N = W + Wd;                     // kN
    const Rc = p.D_disc / 2, ri = p.D_bore / 2;
    const r_unif = 2 / 3 * (Rc ** 3 - ri ** 3) / (Rc ** 2 - ri ** 2) / 1000; // m
    const step = 360 / p.n_bar, half = step / 2 * Math.PI / 180;
    const arm = p.R_bar * Math.cos(half) / 1000;          // m
    const Delta = (p.X_cyl - p.R_bar * Math.cos(half)) / 1000;
    const A = Math.PI / 4 * p.D_cyl ** 2;                 // mm2
    const F_relief = A * p.p_relief / 1e4;               // kN
    const F_alarm = A * p.p_alarm / 1e4;
    const K = (1 + 2 * p.mu_g * Delta / (p.Lg / 1000)) / p.eta;
    const T_piv = p.mu_piv * (0.05 * W) * (p.D_piv / 2000);
    const cas = (mu, r) => {
      const Tf = mu * N * r, T = Tf + T_piv, Fb = T / (2 * arm), Fc = K * Fb, pb = Fc * 1e4 / A;
      return { mu, r, Tf, T, Fb, Fc, p: pb, FS: F_relief / Fc };
    };
    const cases = [
      { key: "nom", name: "Nominal – grasa limpia", ...cas(p.mu_nom, r_unif) },
      { key: "des", name: "DISEÑO", ...cas(p.mu_d, p.r_eff) },
      { key: "cont", name: "Contaminado", ...cas(p.mu_cont, p.r_eff) },
      { key: "dry", name: "Acero seco (prohibido)", ...cas(p.mu_dry, r_unif) },
    ];
    const muMax = (r, pbar) => ((A * pbar / 1e4) / K * 2 * arm - T_piv) / (N * r);
    const des = cases[1];

    // presiones
    const ND = p.phi_d * W + Wd;
    const Ac = Math.PI * (Rc ** 2 - ri ** 2);
    const q_avg = ND * 1000 / Ac;
    const kq = 4 * p.e * Rc / (Rc ** 2 + ri ** 2);
    const q_max = q_avg * (1 + kq), q_min = q_avg * (1 - kq);
    const q_load = p.phi_d * W * 1000 / (Math.PI * (p.D_load / 2) ** 2);
    const Ng = (W + m.total * G / 1000);
    const qg = Ng * 1000 / (p.BX * p.BY), qg_max = qg * (1 + 6 * p.e / p.BY), qg_min = qg * (1 - 6 * p.e / p.BY);

    // cinemática
    const chord = 2 * p.R_bar * Math.sin(half);
    const useful = p.stroke - p.free;

    // ---------- verificaciones ----------
    const Fs = F_relief;                  // kN, fuerza de calado
    const V = [];
    const add = (grp, el, dem, cap, unit, ref, note) => V.push({ grp, el, dem, cap, unit, FU: dem / cap, ref, note });
    add("Interfaz", "Presión de contacto máx. (e)", q_max, p.q_allow, "MPa", "Criterio acero/acero lubricado");
    // placas por paneles (Roark)
    const pans = panels(p);
    let worstTop = null, worstBot = null;
    pans.forEach((pn) => {
      const rk = roark(pn.radial, pn.circ);
      const sT = rk.beta * q_load * rk.b ** 2 / p.t_top ** 2;
      const sB = rk.beta * q_max * rk.b ** 2 / p.t_bot ** 2;
      pn.rk = rk; pn.sT = sT; pn.sB = sB;
      pn.wT = rk.alpha * q_load * rk.b ** 4 / (p.Es * p.t_top ** 3);
      if (!worstTop || sT > worstTop.sT) worstTop = pn;
      if (!worstBot || sB > worstBot.sB) worstBot = pn;
    });
    add("Disco", `Plancha sup. 4a – panel ${worstTop.name} (${worstTop.rk.b.toFixed(0)}×${worstTop.rk.a.toFixed(0)})`, worstTop.sT, 0.6 * p.Fy, "MPa", "Roark T11.4 c.8; 0,6·Fy (AISC F11)");
    add("Disco", `Plancha inf. 4b – panel ${worstBot.name}`, worstBot.sB, 0.6 * p.Fy, "MPa", "Roark T11.4 c.8; 0,6·Fy");
    // voladizo anular exterior, sección compuesta 4a+4b unidas por barras
    const rings = ringsOf(p), rOut = rings[rings.length - 1] + p.t_ring / 2;
    const Lc = Rc - rOut;
    const hc = p.gap + (p.t_top + p.t_bot) / 2;
    const Icomp = p.t_top * (p.t_bot * hc / (p.t_top + p.t_bot)) ** 2 + p.t_bot * (p.t_top * hc / (p.t_top + p.t_bot)) ** 2 + (p.t_top ** 3 + p.t_bot ** 3) / 12;
    const yext = p.t_bot * hc / (p.t_top + p.t_bot) + p.t_top / 2;
    const Mc = q_avg * Lc ** 2 / 2;
    add("Disco", `Voladizo anular R${rOut.toFixed(0)}–R${Rc} (4a+4b compuesto)`, Mc * Math.max(yext, hc - yext + (p.t_top + p.t_bot) / 2) / Icomp, 0.6 * p.Fy, "MPa", "Viga compuesta por barras 4f; q media");
    // almas
    let wmax = 0;
    const edges = [p.D_hub / 2].concat(rings, [Rc]);
    for (let i = 1; i < edges.length - 1; i++) { const trib = (edges[i + 1] - edges[i - 1]) / 2; wmax = Math.max(wmax, Math.max(q_load, q_max) * trib); }
    add("Disco", "Almas 4d – compresión (q·ancho trib./t)", wmax / p.t_ring, 0.6 * p.Fy, "MPa", "AISC J10.2 (fluencia local)");
    // barra
    const L = p.gap, c = Math.min(p.pawl_H, L), d = p.D_bar;
    const Mss = Fs / 4 * (L - c / 2) / 1000;                       // kN·m
    const Mfe = Fs * (3 * L * L - c * c) / (24 * L) / 1000;
    const Mn = p.Fy * d ** 3 / 6 / 1.67 / 1e6;
    add("Barra 4f", `Flexión (rotulada) – F calado ${Fs.toFixed(0)} kN`, Mss, Mn, "kN·m", "AISC F11.1, Ω = 1,67");
    const tau = 4 * (Fs / 2) * 1000 / (3 * Math.PI * d * d / 4);
    add("Barra 4f", "Corte", tau, 0.6 * p.Fy / 1.5, "MPa", "AISC G1, Ω = 1,50");
    const tV = Fs / 2 * 1000 / (Math.PI * d * p.E_w), tM = Mfe * 1e6 / (Math.PI * (d / 2) ** 2 * p.E_w);
    add("Barra 4f", `Soldadura PJP (E = ${p.E_w}) – V + M empotrado`, Math.hypot(tV, tM), 0.6 * p.FEXX / 2, "MPa", "AISC J2.5, Ω = 2,0; AWS D1.1");
    add("Barra 4f", `Aplastamiento en agujero Ø${p.D_hole}`, Fs / 2 * 1000 / (Math.min(p.t_top, p.t_bot) * d), 0.9 * p.Fy, "MPa", "AISC J7, Ω = 2,0");
    // trinquete
    const lev = p.shoe_X0 - p.R_bar * Math.cos(half);
    const sp = Fs * 1000 * lev / (p.pawl_H * p.pawl_W ** 2 / 6);
    add("Empuje", `Trinquete – flexión en boca (brazo ${lev.toFixed(1)} mm)`, sp, p.Fy_pawl / p.Nd, "MPa", "Fy/Nd (ASME BTH-1, Nd)");
    // guía
    const Rg = Fs * Delta / (p.Lg / 1000);
    add("Empuje", `Guía – aplastamiento en ranura (R = ${Rg.toFixed(0)} kN)`, Rg * 1000 / (p.g_emb * p.g_Lc), 0.9 * p.Fy, "MPa", "AISC J7, Ω = 2,0");
    add("Empuje", "Guía – flexión en raíz", Rg * p.g_h / 2 / 1000, p.Fy * p.g_Lc * p.g_w ** 2 / 4 / 1.67 / 1e6, "kN·m", "AISC F11.1, Ω = 1,67");
    // ménsula y pasador
    const sc = Fs * 1000 * p.h_axis / (2 * p.t_cheek * p.L_cheek ** 2 / 6);
    add("Ménsula", "Mejillas – flexión en la base", sc, 0.6 * p.Fy, "MPa", "AISC F11; CJP AISC J2");
    const cl = Math.max(0, (p.cheek_gap - p.eye_W) / 2);
    const Mp = Fs / 2 * (p.t_cheek / 2 + cl + p.eye_W / 4) / 1000;
    add("Ménsula", `Pasador Ø${p.D_pin} – flexión (horquilla)`, Mp * 1e6 / (Math.PI * p.D_pin ** 3 / 32), p.Fy_pin / p.Nd, "MPa", "Fy/Nd (ASME BTH-1)");
    add("Ménsula", "Pasador – corte doble", Fs / 2 * 1000 / (Math.PI * p.D_pin ** 2 / 4), p.Fy_pin / (p.Nd * Math.sqrt(3)), "MPa", "ASME BTH-1 3-2.2");
    add("Ménsula", "Agujero mejilla – aplastamiento", Fs / 2 * 1000 / (p.t_cheek * p.D_pin), 0.9 * p.Fy, "MPa", "AISC J7, Ω = 2,0");
    // pivote
    const H = p.H_frac * W;
    add("Pivote", `Buje – presión (H = ${(p.H_frac * 100).toFixed(1)} % W)`, H * 1000 / (p.D_piv * p.L_bush), p.p_bush, "MPa", "Fabricante bronce-grafito");
    add("Pivote", "Pivote – flexión", H * 50 / (Math.PI * p.D_piv ** 3 / 32) * 1000, p.Fy_pin / p.Nd, "MPa", "Fy/Nd");
    // cilindro
    const Lb = p.L0 + p.stroke, I = Math.PI * p.D_rod ** 4 / 64, Pcr = Math.PI ** 2 * p.Es * I / Lb ** 2 / 1000;
    add("Cilindro", `Vástago Ø${p.D_rod} – pandeo (L = ${Lb})`, Fs, Pcr / 3, "kN", "Euler, FS = 3,0");
    add("Cilindro", "Fuerza de diseño vs disponible a alivio", des.Fc, F_relief, "kN", "Ec. (5)–(7)");
    add("Cilindro", `Carrera útil vs cuerda de ${step.toFixed(1)}°`, chord, useful, "mm", "Cinemática del trinquete");
    add("Apoyo", "Presión bajo placa base (máx.)", qg_max, p.q_ground, "MPa", "Admisible losa/mats (dato)");

    const FUmax = V.reduce((a, v) => Math.max(a, v.FU), 0);
    return {
      p, m, W, Wd, N, Rc, ri, r_unif, step, arm, Delta, A, F_relief, F_alarm, K, T_piv, cases, des,
      muMax, ND, q_avg, q_max, q_min, q_load, qg, qg_max, qg_min, chord, useful, Fs, V, FUmax, lev, Rg, H, pans,
      Mss, Mfe, tV, tM, Pcr, Lb,
    };
  }

  // fuerza vs posición de carrera (lado derecho, empuje +Y)
  function strokeCurve(R, mu, r, npts) {
    const p = R.p, out = [];
    const half = R.step / 2 * Math.PI / 180;
    const T = mu * R.N * r + R.T_piv;
    const s0 = p.free;
    for (let i = 0; i <= npts; i++) {
      const s = p.stroke * i / npts;
      if (s < s0) { out.push({ s, F: 0.02 * R.des.Fc, p: 0.02 * R.des.p, th: null }); continue; }
      // y de la barra: R sin(th) = R sin(-half) + (s - s0)
      const y = p.R_bar * Math.sin(-half) + (s - s0);
      if (Math.abs(y) > p.R_bar) break;
      const th = Math.asin(y / p.R_bar);
      const armx = p.R_bar * Math.cos(th);
      const Dl = (p.X_cyl - armx) / 1000;
      const K = (1 + 2 * p.mu_g * Dl / (p.Lg / 1000)) / p.eta;
      const Fb = T / (2 * armx / 1000);
      const F = K * Fb;
      out.push({ s, F, p: F * 1e4 / R.A, th: th * 180 / Math.PI, Fb, arm: armx });
    }
    return out;
  }

  // ======================== FEA ========================
  // Matriz banda simétrica (almacena j>=i, j-i<=bw)
  function Band(n, bw) { this.n = n; this.bw = bw; this.a = new Float64Array(n * (bw + 1)); }
  Band.prototype.add = function (i, j, v) { if (j < i) { const t = i; i = j; j = t; } const k = j - i; if (k > this.bw) throw new Error("bw"); this.a[i * (this.bw + 1) + k] += v; };
  Band.prototype.fix = function (i) {
    const bw = this.bw, w = bw + 1;
    for (let k = 0; k <= bw; k++) if (i + k < this.n) this.a[i * w + k] = 0;
    for (let k = 1; k <= bw; k++) if (i - k >= 0) this.a[(i - k) * w + k] = 0;
    this.a[i * w] = 1;
  };
  Band.prototype.solve = function (f) {
    const n = this.n, bw = this.bw, w = bw + 1, a = this.a;
    for (let i = 0; i < n; i++) { // Cholesky banda
      let s = a[i * w];
      for (let k = Math.max(0, i - bw); k < i; k++) { const l = a[k * w + (i - k)]; s -= l * l; }
      if (s <= 0) throw new Error("Matriz no definida positiva en dof " + i);
      const d = Math.sqrt(s); a[i * w] = d;
      const jm = Math.min(n - 1, i + bw);
      for (let j = i + 1; j <= jm; j++) {
        let t = a[i * w + (j - i)];
        for (let k = Math.max(0, j - bw); k < i; k++) t -= a[k * w + (i - k)] * a[k * w + (j - k)];
        a[i * w + (j - i)] = t / d;
      }
    }
    const y = Float64Array.from(f);
    for (let i = 0; i < n; i++) { let s = y[i]; for (let k = Math.max(0, i - bw); k < i; k++) s -= a[k * w + (i - k)] * y[k]; y[i] = s / a[i * w]; }
    for (let i = n - 1; i >= 0; i--) { let s = y[i]; const jm = Math.min(n - 1, i + bw); for (let j = i + 1; j <= jm; j++) s -= a[i * w + (j - i)] * y[j]; y[i] = s / a[i * w]; }
    return y;
  };

  const GP = [-1 / Math.sqrt(3), 1 / Math.sqrt(3)];
  const XI = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
  function dN(xi, eta) { return XI.map(([a, b]) => [a * (1 + b * eta) / 4, b * (1 + a * xi) / 4]); }
  function Nf(xi, eta) { return XI.map(([a, b]) => (1 + a * xi) * (1 + b * eta) / 4); }

  /* Placa Mindlin Q4 (integración selectiva), panel rectangular a×b empotrado, presión q. */
  function plateFEA(a, b, t, q, E, nu, nx, ny) {
    const hx = a / nx, hy = b / ny, nnx = nx + 1, nny = ny + 1, nn = nnx * nny, ndof = 3 * nn;
    // numeración por columnas en la dirección corta
    const id = (i, j) => i * nny + j;      // i en x, j en y (y corta si b<=a)
    const bw = 3 * (nny + 2);
    const K = new Band(ndof, bw), F = new Float64Array(ndof);
    const D = E * t ** 3 / (12 * (1 - nu * nu)), Gs = E / (2 * (1 + nu)) * t * 5 / 6;
    const Db = [[D, nu * D, 0], [nu * D, D, 0], [0, 0, D * (1 - nu) / 2]];
    const ke = new Float64Array(144);
    // matriz elemental (idéntica para todos)
    const jx = 2 / hx, jy = 2 / hy, detJ = hx * hy / 4;
    const addBtDB = (Bm, Dm, wgt) => {
      const r = Bm.length;
      for (let i = 0; i < 12; i++) for (let j = 0; j < 12; j++) {
        let s = 0;
        for (let k = 0; k < r; k++) for (let l = 0; l < r; l++) s += Bm[k][i] * Dm[k][l] * Bm[l][j];
        ke[i * 12 + j] += s * wgt;
      }
    };
    for (const xi of GP) for (const et of GP) {
      const d = dN(xi, et), Bb = [new Array(12).fill(0), new Array(12).fill(0), new Array(12).fill(0)];
      for (let n = 0; n < 4; n++) { const dx = d[n][0] * jx, dy = d[n][1] * jy; Bb[0][3 * n + 1] = dx; Bb[1][3 * n + 2] = dy; Bb[2][3 * n + 1] = dy; Bb[2][3 * n + 2] = dx; }
      addBtDB(Bb, Db, detJ);
    }
    { const d = dN(0, 0), Nn = Nf(0, 0), Bs = [new Array(12).fill(0), new Array(12).fill(0)];
      for (let n = 0; n < 4; n++) { Bs[0][3 * n] = d[n][0] * jx; Bs[0][3 * n + 1] = -Nn[n]; Bs[1][3 * n] = d[n][1] * jy; Bs[1][3 * n + 2] = -Nn[n]; }
      addBtDB(Bs, [[Gs, 0], [0, Gs]], 4 * detJ); }
    const elems = [];
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
      const nodes = [id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)];
      elems.push(nodes);
      const dofs = []; nodes.forEach((n) => dofs.push(3 * n, 3 * n + 1, 3 * n + 2));
      for (let r = 0; r < 12; r++) for (let c = r; c < 12; c++) K.add(dofs[r], dofs[c], ke[r * 12 + c]);
      nodes.forEach((n) => (F[3 * n] += q * hx * hy / 4));
    }
    for (let i = 0; i < nnx; i++) for (let j = 0; j < nny; j++) if (i === 0 || j === 0 || i === nx || j === ny) {
      const n = id(i, j); for (let k = 0; k < 3; k++) { K.fix(3 * n + k); F[3 * n + k] = 0; }
    }
    const u = K.solve(F);
    // momentos en puntos de Gauss -> tensión de flexión σ = 6M/t²
    const sig = new Float64Array(elems.length);
    let smax = 0, wmax = 0;
    for (let n = 0; n < nn; n++) wmax = Math.max(wmax, u[3 * n]);
    elems.forEach((nodes, e) => {
      let emax = 0;
      for (const xi of GP) for (const et of GP) {
        const d = dN(xi, et); let kx = 0, ky = 0, kxy = 0;
        for (let n = 0; n < 4; n++) { const dx = d[n][0] * jx, dy = d[n][1] * jy, bx = u[3 * nodes[n] + 1], by = u[3 * nodes[n] + 2]; kx += dx * bx; ky += dy * by; kxy += dy * bx + dx * by; }
        const Mx = D * (kx + nu * ky), My = D * (ky + nu * kx), Mxy = D * (1 - nu) / 2 * kxy;
        const sx = 6 * Mx / t ** 2, sy = 6 * My / t ** 2, txy = 6 * Mxy / t ** 2;
        const vm = Math.sqrt(sx * sx - sx * sy + sy * sy + 3 * txy * txy);
        emax = Math.max(emax, Math.max(Math.abs(sx), Math.abs(sy)));
        sig[e] = Math.max(sig[e], vm);
      }
      smax = Math.max(smax, emax);
    });
    const wn = new Float64Array(nn); for (let n = 0; n < nn; n++) wn[n] = u[3 * n];
    return { nx, ny, hx, hy, a, b, elems, sig, w: wn, wmax, smax, ndof, id };
  }

  /* Trinquete en tensión plana Q4. Coordenadas locales: x desde la punta, y desde la cara opuesta a la barra. */
  function pawlFEA(R, h) {
    const p = R.p, Lp = p.pawl_L, Wp = p.pawl_W, th = p.pawl_H;
    h = h || 2.0;
    const nx = Math.round(Lp / h), ny = Math.round(Wp / h), hx = Lp / nx, hy = Wp / ny;
    const nny = ny + 1, nn = (nx + 1) * nny, ndof = 2 * nn;
    const id = (i, j) => i * nny + j;
    const half = R.step / 2 * Math.PI / 180;
    const xTip = p.R_bar * Math.cos(half) - p.tip_off;            // x global de la punta
    const cxl = p.tip_off, cyl = Wp, Rs = p.seat_R;              // centro del asiento (cara y = Wp)
    const xMouth = p.shoe_X0 - xTip;                            // inicio del alojamiento
    const chx = p.ch_x, chy = p.ch_y;
    const inside = (x, y) => !((x - cxl) ** 2 + (y - cyl) ** 2 < Rs * Rs) && !(chx > 0 && x < chx && y < chy * (1 - x / chx));
    const X = new Float64Array(nn), Y = new Float64Array(nn);
    for (let i = 0; i <= nx; i++) for (let j = 0; j <= ny; j++) { X[id(i, j)] = i * hx; Y[id(i, j)] = j * hy; }
    const elems = [];
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
      const xc = (i + 0.5) * hx, yc = (j + 0.5) * hy;
      if (inside(xc, yc)) elems.push({ n: [id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)], i, j });
    }
    // eliminar elementos unidos sólo por un vértice (mecanismos)
    for (let it = 0; it < 3; it++) {
      const cnt = new Map();
      elems.forEach((e) => { for (let k = 0; k < 4; k++) { const a = e.n[k], b = e.n[(k + 1) % 4], key = Math.min(a, b) + "_" + Math.max(a, b); cnt.set(key, (cnt.get(key) || 0) + 1); } });
      const keepE = elems.filter((e) => { let sh = 0; for (let k = 0; k < 4; k++) { const a = e.n[k], b = e.n[(k + 1) % 4]; if (cnt.get(Math.min(a, b) + "_" + Math.max(a, b)) > 1) sh++; } return sh >= 2; });
      if (keepE.length === elems.length) break; elems.length = 0; keepE.forEach((e) => elems.push(e));
    }
    const used = new Uint8Array(nn);
    elems.forEach((e) => e.n.forEach((n) => (used[n] = 1)));
    // nodos de borde irregular: proyectar sobre la geometría real (asiento o chaflán)
    const segP = (x, y) => { const ax = 0, ay = chy, bx = chx, by = 0, vx = bx - ax, vy = by - ay; let t = ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy); t = Math.max(0, Math.min(1, t)); return [ax + t * vx, ay + t * vy]; };
    const hm = Math.max(hx, hy), snapped = new Uint8Array(nn);
    const adj = []; elems.forEach((e) => e.n.forEach((n) => { (adj[n] = adj[n] || []).push(e); }));
    const detAt = (e, xi, et) => { const d = dN(xi, et); let J11 = 0, J12 = 0, J21 = 0, J22 = 0; for (let k = 0; k < 4; k++) { const n = e.n[k]; J11 += d[k][0] * X[n]; J12 += d[k][0] * Y[n]; J21 += d[k][1] * X[n]; J22 += d[k][1] * Y[n]; } return J11 * J22 - J12 * J21; };
    for (let n = 0; n < nn; n++) {
      if (!used[n]) continue;
      const x = X[n], y = Y[n];
      const r = Math.hypot(x - cxl, y - cyl);
      let best = null, d = 1e9;
      if (Math.abs(r - Rs) < 0.6 * hm && y < Wp - 1e-9) { d = Math.abs(r - Rs); best = [cxl + Rs * (x - cxl) / r, cyl + Rs * (y - cyl) / r]; }
      if (chx > 0) { const q = segP(x, y), dd = Math.hypot(q[0] - x, q[1] - y); if (dd < 0.6 * hm && dd < d && x < chx + 1e-9 && y > 1e-9 && x > 1e-9) { d = dd; best = q; } }
      if (best && d > 1e-9) {
        const ox = X[n], oy = Y[n]; X[n] = best[0]; Y[n] = best[1];
        const ok = (adj[n] || []).every((e) => GP.every((xi) => GP.every((et) => detAt(e, xi, et) > 0.15 * hx * hy / 4)));
        if (ok) snapped[n] = 1; else { X[n] = ox; Y[n] = oy; }
      }
    }
    const E = p.Es, nu = p.nu, c = E / (1 - nu * nu);
    const Dm = [[c, c * nu, 0], [c * nu, c, 0], [0, 0, c * (1 - nu) / 2]];
    const bw = 2 * (nny + 2);
    const K = new Band(ndof, bw), F = new Float64Array(ndof);
    const Bfor = (e, xi, et) => {
      const d = dN(xi, et); let J11 = 0, J12 = 0, J21 = 0, J22 = 0;
      for (let k = 0; k < 4; k++) { const n = e.n[k]; J11 += d[k][0] * X[n]; J12 += d[k][0] * Y[n]; J21 += d[k][1] * X[n]; J22 += d[k][1] * Y[n]; }
      const dj = J11 * J22 - J12 * J21;
      const B = [new Array(8).fill(0), new Array(8).fill(0), new Array(8).fill(0)];
      for (let k = 0; k < 4; k++) {
        const dx = (J22 * d[k][0] - J12 * d[k][1]) / dj, dy = (-J21 * d[k][0] + J11 * d[k][1]) / dj;
        B[0][2 * k] = dx; B[1][2 * k + 1] = dy; B[2][2 * k] = dy; B[2][2 * k + 1] = dx;
      }
      return { B, dj };
    };
    let badJ = 0;
    elems.forEach((e) => {
      const ke = new Float64Array(64);
      let xc = 0, yc = 0; e.n.forEach((n) => { xc += X[n] / 4; yc += Y[n] / 4; }); e.xc = xc; e.yc = yc;
      for (const xi of GP) for (const et of GP) {
        const { B, dj } = Bfor(e, xi, et); if (dj <= 0) badJ++;
        for (let i = 0; i < 8; i++) for (let j = i; j < 8; j++) { let s = 0; for (let k = 0; k < 3; k++) for (let l = 0; l < 3; l++) s += B[k][i] * Dm[k][l] * B[l][j]; ke[i * 8 + j] += s * Math.abs(dj) * th; }
      }
      const dofs = []; e.n.forEach((n) => dofs.push(2 * n, 2 * n + 1));
      for (let r = 0; r < 8; r++) for (let q = r; q < 8; q++) K.add(dofs[r], dofs[q], ke[r * 8 + q]);
    });
    // carga: presión de contacto radial en el asiento, distribución coseno (resultante = F calado, en -y)
    const bnodes = [];
    for (let n = 0; n < nn; n++) {
      if (!used[n]) continue;
      const r = Math.hypot(X[n] - cxl, Y[n] - cyl);
      if (Math.abs(r - Rs) < 0.3 * hm) { const ny_ = (Y[n] - cyl) / r; if (ny_ < -0.17) bnodes.push({ n, w: -ny_, nx: (X[n] - cxl) / r, ny: ny_ }); }
    }
    const Ftot = R.Fs * 1000; let sw = 0; bnodes.forEach((b) => (sw += b.w * b.w));
    bnodes.forEach((b) => { const f = Ftot * b.w / sw; F[2 * b.n] += f * b.nx; F[2 * b.n + 1] += f * b.ny; });
    // apoyos: alojamiento del carro (x >= boca) en caras y = 0 / y = W (uy); extremo posterior (ux)
    for (let i = 0; i <= nx; i++) for (let j = 0; j <= ny; j++) {
      const n = id(i, j), x = i * hx;
      if (!used[n]) { K.fix(2 * n); K.fix(2 * n + 1); F[2 * n] = F[2 * n + 1] = 0; continue; }
      if (x >= xMouth - 1e-6 && (j === 0 || j === ny)) { K.fix(2 * n + 1); F[2 * n + 1] = 0; }
      if (i === nx) { K.fix(2 * n); F[2 * n] = 0; }
    }
    const u = K.solve(F);
    const sig = new Float64Array(elems.length); let smax = 0, sNotch = 0, sMouth = 0, sCont = 0, at = null;
    elems.forEach((e, k) => {
      let vm = 0;
      const ue = []; e.n.forEach((n) => ue.push(u[2 * n], u[2 * n + 1]));
      for (const xi of GP) for (const et of GP) {
        const { B } = Bfor(e, xi, et);
        const eps = [0, 0, 0]; for (let r = 0; r < 3; r++) for (let q = 0; q < 8; q++) eps[r] += B[r][q] * ue[q];
        const s = [0, 0, 0]; for (let r = 0; r < 3; r++) for (let q = 0; q < 3; q++) s[r] += Dm[r][q] * eps[q];
        vm = Math.max(vm, Math.sqrt(s[0] * s[0] - s[0] * s[1] + s[1] * s[1] + 3 * s[2] * s[2]));
      }
      sig[k] = vm;
      { const { B } = Bfor(e, 0, 0); const eps = [0, 0, 0]; for (let r = 0; r < 3; r++) for (let q = 0; q < 8; q++) eps[r] += B[r][q] * ue[q];
        e.sx = Dm[0][0] * eps[0] + Dm[0][1] * eps[1]; e.txy = Dm[2][2] * eps[2]; }
      const dc = Math.hypot(e.xc - cxl, e.yc - cyl);
      const nearSupport = e.xc > xMouth - 2 * hx, contact = dc < Rs + 1.6 * hm && e.yc > cyl - Rs - 2 * hm;
      e.flag = contact ? 1 : nearSupport ? 2 : 0;
      if (!nearSupport && !contact && vm > smax) { smax = vm; at = [e.xc, e.yc]; }
      if (contact) sCont = Math.max(sCont, vm);
      if (Math.abs(e.xc - (xMouth - 3 * hx)) < hx / 2 + 1e-9) sMouth = Math.max(sMouth, vm);
    });
    let umax = 0; for (let n = 0; n < nn; n++) umax = Math.max(umax, Math.hypot(u[2 * n], u[2 * n + 1]));
    // linealización por secciones verticales (ASME VIII-2 5.A): σm + σb y τ media
    const cols = new Map();
    elems.forEach((e) => { if (!cols.has(e.i)) cols.set(e.i, []); cols.get(e.i).push(e); });
    const sections = [];
    cols.forEach((list, i) => {
      const x = (i + 0.5) * hx; if (x > xMouth - 0.5 * hx) return;
      let y0 = 1e9, y1 = -1e9; list.forEach((e) => { e.n.forEach((n) => { y0 = Math.min(y0, Y[n]); y1 = Math.max(y1, Y[n]); }); });
      const d = y1 - y0, ym = (y0 + y1) / 2; let Nn = 0, M = 0, V = 0;
      list.forEach((e) => { let a = 1e9, b = -1e9; e.n.forEach((n) => { a = Math.min(a, Y[n]); b = Math.max(b, Y[n]); }); const dy = b - a; Nn += e.sx * dy; M += e.sx * dy * ((a + b) / 2 - ym); V += e.txy * dy; });
      const sm = Nn / d, sb = 6 * M / (d * d), ta = V / d;
      sections.push({ x, d, sm, sb, ta, slin: Math.abs(sm) + Math.abs(sb), seq: Math.sqrt((Math.abs(sm) + Math.abs(sb)) ** 2 + 3 * (1.5 * ta) ** 2 * 0) , tmax: 1.5 * Math.abs(ta) });
    });
    sections.sort((a, b) => a.x - b.x);
    let crit = sections[0]; sections.forEach((s) => { if (s.slin > crit.slin) crit = s; });
    let crT = sections[0]; sections.forEach((s) => { if (s.tmax > crT.tmax) crT = s; });
    const beam = R.Fs * 1000 * (xMouth - cxl) / (th * Wp * Wp / 6);
    return { sections, crit, crT, nx, ny, hx, hy, Lp, Wp, X, Y, elems, sig, smax, at, sMouth, sCont, umax, xMouth, cx: cxl, cy: cyl, Rs, chx, chy, beam, ndof, nb: bnodes.length, badJ };
  }

  const api = { DEFAULTS, compute, strokeCurve, plateFEA, pawlFEA, roark, panels, masses, ringsOf, G };
  if (typeof module !== "undefined") module.exports = api; else root.TT = api;
})(this);
