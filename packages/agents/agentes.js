/* TT300-C · Agentes deterministas del producto: validador de entradas, auditor normativo,
   revisor cruzado, escenarios y optimizador de peso. Sin red ni LLM: mismas entradas, mismas salidas. */
const AG = (() => {
  const TT_ = (typeof TT !== "undefined") ? TT : require("../core/tt300c.js");
  const D2R = Math.PI / 180;

  /* ---------- 1. Validador de entradas ---------- */
  function validate(P) {
    const out = [];
    const E = (msg) => out.push({ lvl: "error", msg }), W = (msg) => out.push({ lvl: "warn", msg });
    TT_.PARAM_GROUPS.forEach((g) => g.p.forEach(([id, lab, u, , mn, mx]) => {
      if (mn === undefined) return;
      const v = P[id];
      if (!isFinite(v)) E(lab + ": valor no numérico");
      else if (v < mn || v > mx) E(`${lab} = ${v} ${u} fuera de rango [${mn}; ${mx}]`);
    }));
    const rings = TT_.parseRings(P.rings);
    if (!rings.length) E("Defina al menos un radio de alma anular");
    if (P.D_bore <= P.d_rod) E("El émbolo debe ser mayor que el vástago");
    if (P.p_alarm > P.p_relief) E("La presión de alarma no puede superar la de alivio");
    if (P.opt_ss > 0.5 && P.opt_uhmw > 0.5) E("Elija una sola opción de interfaz: A (discos inoxidables con grasa) o B (discos inoxidables con lámina UHMW)");
    if (P.p_relief > P.p_rated * TT_.PSI_CAT + 1e-6) E(`El alivio (${P.p_relief} bar) supera la presión nominal del cilindro (${P.p_rated} psi ≙ ${Math.round(P.p_rated * TT_.PSI_CAT)} bar)`);
    if (P.s_free >= P.stroke) E("El recorrido libre debe ser menor que la carrera");
    if (P.N_pin % P.N_rib !== 0) {
      const ok = []; for (let n = 4; n <= P.N_pin; n++) if (P.N_pin % n === 0) ok.push(n);
      E(`N° de pasadores (${P.N_pin}) debe ser múltiplo del N° de nervios (${P.N_rib}) para la simetría del modelo FEA. Nervios válidos: ${ok.join(", ")}`);
    }
    if (P.R_pin + P.d_pin / 2 + 15 > P.D_top / 2) E("Los pasadores quedan a menos de 15 mm del borde de la mesa");
    const rpr = TT_.prIn(P);
    rings.forEach((r) => {
      if (r <= P.D_hub / 2) E(`Alma R${r} dentro del cubo`);
      if (r > rpr - 5) W(`Alma R${r} invade el anillo de pasadores (R ≥ ${rpr.toFixed(0)}): revisar holgura con los pasadores`);
    });
    if (rings.length && P.R_rib > Math.max(...rings) + 1) W("Los nervios terminan fuera del alma exterior");
    if (P.D_top + 100 > P.B) E("La base debe sobresalir al menos 50 mm de la mesa por lado");
    const g = TT_.guideGeo(P);
    if (Math.abs(g.y_eye) > P.B / 2 - 60 || P.x_g > P.B / 2 - 60) E("El ojal del cilindro queda fuera de la base (o a menos de 60 mm del borde)");
    if (P.l_p - P.d_pin / 2 - 5 <= 0) E("El pasador del vástago queda delante de la uña: aumentar l_p");
    if (P.D_load > P.D_top) E("El diámetro de apoyo de la carga supera la mesa");
    if (P.n_cyl === 1) W("Un solo cilindro no forma par: el pivote recibe la fuerza completa. Válvula de bloqueo obligatoria");
    if (P.n_cyl % 2 === 1 && P.n_cyl > 1) W("N° impar de cilindros: verificar que el conjunto forme par puro");
    if (P.t_pr < Math.max(P.t_top, P.t_bot)) W("El anillo de pasadores es más delgado que las planchas: se usa el mayor espesor");
    const K = TT_.kinematics(P);
    if (!K.ok) E(K.msg);
    return out;
  }

  /* ---------- 2. Auditor normativo ---------- */
  function audit(checks) {
    const missing = checks.filter((c) => !c.ref || !c.formula || /tbd|pendiente de ref/i.test(c.ref));
    const refs = {};
    checks.forEach((c) => { if (c.ref) refs[c.ref] = (refs[c.ref] || 0) + 1; });
    return { ok: missing.length === 0, missing, refs: Object.entries(refs).sort((a, b) => b[1] - a[1]) };
  }

  /* ---------- 3. Revisor cruzado: recálculo independiente con formulaciones distintas ---------- */
  // Roark, 7.ª ed., Tabla 11.4 caso 8a (placa rectangular empotrada, carga uniforme): σ_borde = β1·q·b²/t²
  const ROARK = [[1.0, 0.3078], [1.2, 0.3834], [1.4, 0.4356], [1.6, 0.4680], [1.8, 0.4872], [2.0, 0.4974], [1e9, 0.5]];
  function beta1(ar) { for (let i = 1; i < ROARK.length; i++) if (ar <= ROARK[i][0]) { const [a0, b0] = ROARK[i - 1], [a1, b1] = ROARK[i]; return a1 > 1e8 ? b1 : b0 + (b1 - b0) * (ar - a0) / (a1 - a0); } return 0.5; }
  function crossCheck(A) {
    const P = A.P, R = A.R, out = [];
    const add = (name, a, b, tol, note) => out.push({ name, tool: a, indep: b, d: (a - b) / (Math.abs(b) || 1) * 100, tol, ok: Math.abs(a - b) <= tol / 100 * Math.abs(b) + 1e-9, note });
    if (!R.K.ok) return out;
    // (a) Fuerza de diseño por potencia virtual con fricción. Para cada θ: equilibrio lineal del patín (3 incógnitas F_pas, R_f, R_r,
    //     resueltas por eliminación de Gauss); el sentido de la fricción de la cara sale de la velocidad numérica del punto
    //     material del pasador en el contacto. Luego F_cil·η·v = (T/n)·ω + μg·Σ|R|·v + μ_s·F_pas·|v_desliz|.
    const pitch = 2 * Math.PI / P.N_pin, yOf = (th) => P.R_pin * Math.sin(th), r = P.d_pin / 2;
    const Ls = R.K.L_s, Lg = 2 / 3 * Ls, front = R.K.front, rear = R.K.rear, Tn = R.cd.T * 1e3 / P.n_cyl;
    const gauss = (M, v) => { const n = v.length, a = M.map((row, i) => [...row, v[i]]);
      for (let c = 0; c < n; c++) { let pv = c; for (let i = c + 1; i < n; i++) if (Math.abs(a[i][c]) > Math.abs(a[pv][c])) pv = i; [a[c], a[pv]] = [a[pv], a[c]];
        for (let i = c + 1; i < n; i++) { const f = a[i][c] / a[c][c]; for (let j = c; j <= n; j++) a[i][j] -= f * a[c][j]; } }
      const x = new Array(n).fill(0); for (let i = n - 1; i >= 0; i--) { let s2 = a[i][n]; for (let j = i + 1; j < n; j++) s2 -= a[i][j] * x[j]; x[i] = s2 / a[i][i]; } return x; };
    let Fmax = 0;
    const evalAt = (th, sgn) => {
      const xc = P.R_pin * Math.cos(th), yc = yOf(th) - r, hh = 1e-7;
      // punto material del pasador en el contacto, rotado dθ con la mesa: velocidad en x
      const vx = ((xc * Math.cos(hh) - yc * Math.sin(hh)) - (xc * Math.cos(-hh) - yc * Math.sin(-hh))) / (2 * hh), vy = xc;
      const sF = sgn !== undefined ? sgn : -Math.sign(vx);             // fricción sobre el pasador opuesta a su deslizamiento en x
      const mu = P.mu_s * sF;
      const yrp = yOf(th) - P.l_p, yr = yrp + (front - rear) / 2 - Lg / 2;
      // incógnitas [Fp, Rf, Rr]: mesa x_c·Fp − y_c·μFp = Tn; patín ΣM(y_r): Fp·(x_g − x_c) + μFp·(y_c − y_r) − Lg·Rf = 0; ΣFx: −μFp + Rf + Rr = 0
      const [Fp, Rf, Rr] = gauss([[xc - yc * mu, 0, 0], [(P.x_g - xc) + mu * (yc - yr), -Lg, 0], [-mu, 1, 1]], [Tn, 0, 0]);
      const Pw = Tn + P.mu_g * (Math.abs(Rf) + Math.abs(Rr)) * vy + P.mu_s * Fp * Math.abs(vx);   // potencia por unidad de ω
      return Pw / (P.eta_c * vy);
    };
    for (let i = 0; i <= 400; i++) { const th = -pitch / 2 + pitch * i / 400; Fmax = Math.max(Fmax, evalAt(th)); }
    const thX = Math.asin(r / P.R_pin); if (thX < pitch / 2) { Fmax = Math.max(Fmax, evalAt(thX, 1), evalAt(thX, -1)); }
    add("Fuerza de diseño por cilindro (potencia virtual con fricción en guía y cara de la uña)", R.cd.F, Fmax, 0.1, "kN");
    // (b) Carrera requerida por coordenadas de los pasadores al inicio y fin del paso
    add("Carrera requerida (coordenadas)", R.K.s_req, P.s_free + yOf(pitch / 2) - yOf(-pitch / 2), 0.1, "mm");
    // (c) Radio de fricción por integración numérica en malla polar
    let num = 0, den = 0; const nr = 400;
    for (let i = 0; i < nr; i++) { const r = R.Ri + (R.Ro - R.Ri) * (i + 0.5) / nr, dA = r * (R.Ro - R.Ri) / nr; num += r * dA; den += dA; }
    add("Radio de fricción con presión uniforme r_u", R.r_u, num / den, 0.05, "mm");
    // (d) Presión máxima por Navier con inercia integrada numéricamente
    let I = 0; for (let i = 0; i < nr; i++) { const r = R.Ri + (R.Ro - R.Ri) * (i + 0.5) / nr; I += Math.PI * r ** 3 * (R.Ro - R.Ri) / nr; }
    const qN = R.ND * 1e3 / R.Ac + R.ND * 1e3 * P.e * R.Ro / I;
    add("Presión de contacto máxima (Navier)", R.q_max, qN, 0.2, "MPa");
    if (A.fea) {
      // (e) Equilibrio de los modelos FEA
      ["top", "bot"].forEach((w) => add(`Equilibrio FEA plancha ${w === "top" ? "superior" : "inferior"} ΣR/ΣF`, A.fea[w].Rsum, A.fea[w].Fapp, 0.5, "kN"));
      add("Equilibrio FEA izaje ΣR/ΣF", A.fea.lift.Rsum, A.fea.lift.Fapp, 0.5, "kN");
      // (f) Plancha inferior: orden de magnitud frente a Roark (paño empotrado)
      const rings = TT_.parseRings(P.rings).filter((r) => r > P.D_hub / 2);
      const radii = [P.D_hub / 2, ...rings];
      let sR = 0;
      for (let i = 0; i < radii.length - 1; i++) {
        const a1 = radii[i + 1] - radii[i], rm = (radii[i + 1] + radii[i]) / 2, b1 = 2 * Math.PI * rm / P.N_rib;
        const bb = Math.min(a1, b1), ar = Math.max(a1, b1) / bb;
        sR = Math.max(sR, beta1(ar) * R.q_max * bb * bb / P.t_bot ** 2);
      }
      const ratio = A.fea.bot.vmMax / sR;
      out.push({ name: "Plancha inferior: FEA / Roark (paño empotrado)", tool: A.fea.bot.vmMax, indep: sR, d: (ratio - 1) * 100, tol: null, ok: ratio > 0.5 && ratio < 2.0, note: "MPa; aceptable si 0,5 < razón < 2,0" });
      // (g) Desequilibrio de la solución axisimétrica global
      out.push({ name: "Flexión global: desequilibrio en el borde", tool: A.fea.glob.imbalance, indep: 0, d: A.fea.glob.imbalance / (R.ND) * 100, tol: 0.1, ok: Math.abs(A.fea.glob.imbalance) <= 1e-3 * R.ND, note: "kN" });
    }
    // (h) Masa de la plancha superior por integración numérica del espesor t(r) en anillos concéntricos
    const Rt = P.D_top / 2, rpr = TT_.prIn(P), hole = P.D_piv + 80, tprx = Math.max(P.t_pr, P.t_top);
    let vTop = 0; const nI = 4000;
    for (let i = 0; i < nI; i++) { const r = hole / 2 + (Rt - hole / 2) * (i + 0.5) / nI; vTop += 2 * Math.PI * r * (Rt - hole / 2) / nI * (r < rpr ? P.t_top : tprx); }
    vTop -= P.N_pin * Math.PI / 4 * P.d_pin ** 2 * tprx;
    const mTop = 7.85e-6 * vTop;
    add("Masa plancha superior", R.m.top, mTop, 0.01, "kg");
    return out;
  }

  /* ---------- 4. Escenarios ---------- */
  function scenarios(A) {
    const P = A.P, R = A.R;
    if (!R.K.ok) return { mu: [], rs: [], grid: [] };
    const mus = [0.10, 0.15, 0.20, 0.25, 0.30], rs = [["r_u", R.r_u], ["r_ef", P.r_ef], ["R", R.Ro]];
    const grid = mus.map((mu) => rs.map(([, r]) => {
      const T = R.torque(mu, r), F = R.Fcyl(T, R.K.armMin);
      return { mu, r, F, p: F * 1e3 / R.A * 10, FS: R.Fstall / F };
    }));
    const loads = [0.8, 1.0, 1.2].map((k) => {
      const Q = Object.assign({}, P, { W_tf: P.W_tf * k });
      const RR = TT_.compute(Q);
      return { W: Q.W_tf, FS: RR.cd ? RR.cd.FS : NaN, p: RR.cd ? RR.cd.p : NaN, muMax: RR.muMax(P.r_ef) };
    });
    // clases de presión de catálogo: alivio = nominal, alarma = 0,85·alivio; émbolo mínimo por FS_min y por alarma
    const classes = [10000, 5000].map((psi) => {
      const pr = Math.floor(psi * TT_.PSI_CAT / 10) * 10, pa = Math.floor(0.85 * pr / 10) * 10, F = R.cd.F;
      const Amin = Math.max(P.FS_min * F * 1e3 / (pr / 10), F * 1e3 / (pa / 10));
      return { psi, pr, pa, Dmin: Math.sqrt(4 * Amin / Math.PI), FScur: R.A * pr / 10 / 1e3 / F, pcur: F * 1e3 / R.A * 10 };
    });
    // alternativas de interfaz de giro: acero–acero (actual), A: discos inoxidables con grasa, B: discos inoxidables con lámina UHMW
    const R0m = TT_.compute(Object.assign({}, P, { opt_ss: 0, opt_uhmw: 0 })).m.total;
    const ifaces = [0, 1, 2].map((k) => {
      const Q = Object.assign({}, P, { opt_ss: k === 1 ? 1 : 0, opt_uhmw: k === 2 ? 1 : 0 }), RR = TT_.compute(Q), I = RR.ifc;
      return { k, name: ["Acero–acero con grasa (base)", "A · Discos inoxidables con grasa", "B · Discos inoxidables con lámina UHMW"][k],
        tss: I.tss, tuh: I.tuh, tssReq: I.tssReq, tuhReq: I.tuhReq, delta: I.delta, mass: RR.m.total, mu_d: RR.mu.d, F: RR.cd.F, p: RR.cd.p, FS: RR.cd.FS,
        muMax: RR.muMax(P.r_ef), q: RR.q_max, mAdd: RR.m.ss + RR.m.uhmw, turns: RR.cd.turns, tFlex: I.tFlex, tuhConf: I.tuhConf, qAvg: I.qAvg, dTot: RR.m.total - R0m };
    });
    return { mus, rs, grid, loads, classes, ifaces };
  }

  /* ---------- 5. Optimizador de peso ---------- */
  const range = (a, b, s) => { const o = []; for (let v = a; v <= b + 1e-9; v += s) o.push(+v.toFixed(3)); return o; };
  const VARS = [
    ["t_top", [10, 12, 15, 16, 20, 22, 25, 30, 32, 35, 40, 45, 50], true],
    ["t_bot", [10, 12, 15, 16, 20, 22, 25, 30, 32, 35, 40, 45, 50], true],
    ["t_base", [6, 8, 10, 12, 15, 16, 20, 22, 25, 30, 32, 35, 40], true],   // el mínimo lo impone el chequeo t_base_mín (planitud)
    ["t_pr", [16, 20, 22, 25, 30, 32, 35, 40, 45, 50, 55, 60], false],
    ["h_disc", range(100, 300, 5), true],
    ["t_web", [8, 10, 12, 15, 16, 20, 25], true],
    ["t_rib", [8, 10, 12, 15, 16, 20, 25], true],
    ["d_pin", range(50, 130, 5), true],
    ["t_ch", [12, 15, 16, 20, 22, 25, 30, 32, 35, 40, 45, 50], false],
    ["L_ch", range(150, 600, 25), false],
    ["d_pp", range(40, 120, 5), false],
    ["dog_b", range(40, 150, 5), false],
    ["dog_h", range(30, 150, 5), false],
    ["L_in", range(100, 400, 25), false],
    ["l_lip", range(30, 150, 10), false],
    ["h_slot", [10, 12, 15, 16, 20, 22, 25, 30], false],
    ["w_bed", range(100, 220, 10), false],
    ["t_bed", [25, 30, 32, 35, 40, 45, 50], false],
    ["w_bed_f", [6, 8, 10, 12, 14], false],
    ["x_lug", range(300, 1000, 50), false],
    ["w_br", [6, 8, 10, 12, 14, 16, 18, 20], false],
    ["w_web", [4, 5, 6, 8, 10, 12], false],
  ];
  function feasible(A, target) {
    return A.checks.every((c) => {
      if (c.st === "info" || c.st === "pend") return true;
      if (c.st === "fail") return false;
      return c.kind === "geo" || c.sys === "giro" ? true : c.fu <= target;
    });
  }
  function* optimizeGen(P0, opts) {
    opts = Object.assign({ target: 0.90, maxEval: 400 }, opts || {});
    let P = Object.assign({}, P0), evals = 0;
    const cache = new Map();
    const run = (Q, fresh) => { evals++; return fresh ? TT_.analyze(Q) : TT_.analyze(Q, { cache }); };
    const tgt = opts.target;
    let A = run(P);
    // fase 1: factibilidad por máximo descenso del déficit (cada variable ±1 tamaño)
    const deficit = (X) => X.checks.reduce((s, c) => {
      if (c.st === "info" || c.st === "pend") return s;
      if (!isFinite(c.fu)) return s + 10;
      const lim = (c.kind === "geo" || c.sys === "giro") ? 1 : tgt;
      return s + Math.max(0, c.fu - lim);
    }, 0);
    let guard = 0, dA = deficit(A);
    while (dA > 0 && guard++ < 80) {
      let best = null;
      for (const [k, list] of VARS) {
        const i = list.findIndex((v) => v >= P[k] - 1e-9);
        for (const j of [i + 1, i - 1]) {
          if (i < 0 || j < 0 || j >= list.length) continue;
          const Q = Object.assign({}, P, { [k]: list[j] }), B = run(Q), dB = deficit(B);
          const score = dA - dB;
          if (score > 1e-9 && (!best || score > best.score + 1e-12 || (Math.abs(score - best.score) <= 1e-12 && B.R.m.total < best.B.R.m.total))) best = { Q, B, dB, score };
        }
      }
      if (!best) break;
      P = best.Q; A = best.B; dA = best.dB;
      yield { phase: "factibilidad", P, A, evals };
    }
    if (!feasible(A, tgt)) { yield { phase: "fin", P, A: run(P, true), evals, ok: false, msg: "No se encontró una configuración factible con las listas de tamaños" }; return; }
    // fase 2: descenso por coordenadas hacia la menor masa
    let improved = true, pass = 0;
    while (improved && pass++ < 6 && evals < opts.maxEval) {
      improved = false;
      for (const [k, list] of VARS) {
        let i = list.findIndex((v) => v >= P[k] - 1e-9);
        while (i > 0 && evals < opts.maxEval) {
          const Q = Object.assign({}, P, { [k]: list[i - 1] });
          if (TT_.masses(Q).total >= TT_.masses(P).total - 1e-6 && k !== "h_disc") { break; }
          const B = run(Q);
          if (feasible(B, tgt) && B.R.m.total <= A.R.m.total + 1e-6) { P = Q; A = B; i--; improved = true; yield { phase: "descenso", P, A, evals, k }; }
          else break;
        }
      }
    }
    // fase 3: confirmación con malla fina; si algo falla, subir la variable asociada
    let F = run(P, true), fix = 0;
    while (!feasible(F, opts.target) && fix++ < 20) {
      const bad = F.checks.filter((c) => c.st === "fail" || (c.kind === "fu" && c.sys === "est" && c.fu > opts.target));
      const map = (c) => /superior/.test(c.name) ? "t_top" : /inferior/.test(c.name) ? "t_bot" : /Izaje/.test(c.name) ? "t_base" : /nervios/.test(c.name) ? "t_rib" : /almas|alma\//.test(c.name) ? "w_web" : null;
      const k = bad.map(map).find(Boolean);
      if (!k) break;
      const list = VARS.find((v) => v[0] === k)[1], i = list.findIndex((v) => v >= P[k] - 1e-9);
      if (i < 0 || i >= list.length - 1) break;
      P = Object.assign({}, P, { [k]: list[i + 1] });
      F = run(P, true);
    }
    yield { phase: "fin", P, A: F, evals, ok: feasible(F, opts.target) };
  }
  function optimize(P0, opts) { let last; for (const s of optimizeGen(P0, opts)) last = s; return last; }

  return { validate, audit, crossCheck, scenarios, optimize, optimizeGen, VARS, feasible };
})();
if (typeof module !== "undefined") module.exports = AG;
