/* TT300-BX · Adaptador de los agentes deterministas (packages/agents/agentes.js) al módulo TT300-BX (packages/core/tt300bx.js).
   validate: el del núcleo sobre los parámetros comunes + rangos y coherencia de los parámetros bx_; audit: el del núcleo (puro sobre las filas);
   crossCheck: el del núcleo sobre el análisis BX (P con el gancho __bx) + recálculos independientes de lo propio de BX (equilibrio de las pastillas,
   celda anular por diferencias finitas, par de los tornillos, fuerza térmica de borde con una cadena discreta, masa del portador por muestreo);
   scenarios: el del núcleo con la alternativa B rotulada como BX (la geometría BX queda fija; cambia solo la carga). El optimizador de masa del núcleo
   no conoce las filas BX: no se ofrece (pendiente). */
const AGBX = (() => {
  const BX_ = (typeof BX !== "undefined") ? BX : require("../core/tt300bx.js");
  const AG_ = (typeof AG !== "undefined") ? AG : require("./agentes.js");
  const TT_prIn = (P) => BX_.TT.prIn(P);

  function validate(P) {
    const out = AG_.validate(P), E = (msg) => out.push({ lvl: "error", msg }), W = (msg) => out.push({ lvl: "warn", msg });
    BX_.BX_GROUP.p.forEach(([id, lab, u, def, mn, mx]) => {
      if (mn === undefined) return;
      const v = P[id] === undefined ? def : P[id];
      if (!isFinite(v)) E(lab + ": valor no numérico");
      else if (v < mn || v > mx) E(`${lab} = ${v} ${u} fuera de rango [${mn}; ${mx}]`);
    });
    const g = (k) => (P[k] === undefined ? BX_.BX_GROUP.p.find((q) => q[0] === k)[3] : P[k]);
    if (![1, 2].includes(Math.round(g("bx_pat")))) E("TT300-BX: el patrón de pastillas debe ser 1 (triangular) o 2 (radial)");
    if (![1, 2].includes(Math.round(g("bx_ss_mat")))) E("TT300-BX: el material del disco debe ser 1 (austenítico) o 2 (dúplex 2205)");
    if (!(g("bx_Tmin") < P.T_ref && P.T_ref < g("bx_Tmax"))) E("TT300-BX: debe cumplirse T_mín < T_ref < T_máx");
    if (g("bx_dp") > 0 && g("bx_lig") > 0 && g("bx_lig") < 5) W("TT300-BX: ligamento menor que 5 mm entre agujeros cortados con plasma");
    if (!BX_.active(P)) W("TT300-BX inactivo: la interfaz no es la opción B (opt_uhmw = 1); el módulo devuelve el cálculo del núcleo sin cambios");
    return out;
  }
  const audit = (checks) => AG_.audit(checks);

  function crossCheck(A) {
    const base = AG_.crossCheck(Object.assign({}, A, { P: A.Pc || A.P }));
    if (!A.bx) return base;
    const out = base.slice(), P = A.Pc, D = A.bx, R = A.R;
    const add = (name, a, b, tol, note) => out.push({ name, tool: a, indep: b, d: (a - b) / (Math.abs(b) || 1) * 100, tol, ok: Math.abs(a - b) <= tol / 100 * Math.abs(b) + 1e-9, note, bx: true });
    // (a) Equilibrio: la suma de q·dA asignada a las pastillas = N_D (sin excentricidad: la integral del término lineal es nula)
    add("BX · Σ carga sobre las pastillas (muestreo) = N_D", D.pastillas.suma_N_kN, R.ND, 0.5, "kN");
    // (b) Celda anular: diferencias finitas sobre la ecuación de la pendiente (independiente de la solución cerrada)
    const c = D.disco.celda, M = BX_.matOf(P), te = D.disco.t - P.ss_allow, Dp = M.E * te ** 3 / (12 * (1 - M.nu ** 2)), q = D.diseno.q_max;
    const a = c.a, b = c.b, n = 2000, h = (b - a) / n, A_ = [], B_ = [], C_ = [], Rh = [];
    for (let i = 1; i < n; i++) { const r = a + i * h; A_.push(1 / (h * h) - 1 / (2 * r * h)); B_.push(-2 / (h * h) - 1 / (r * r)); C_.push(1 / (h * h) + 1 / (2 * r * h)); Rh.push(q * (r * r - b * b) / (2 * r) / Dp); }
    const m = n - 1, cp = new Array(m), dp = new Array(m), th = new Array(m);
    for (let i = 0; i < m; i++) { const den = B_[i] - (i ? A_[i] * cp[i - 1] : 0); cp[i] = C_[i] / den; dp[i] = (Rh[i] - (i ? A_[i] * dp[i - 1] : 0)) / den; }
    for (let i = m - 1; i >= 0; i--) th[i] = dp[i] - (i < m - 1 ? cp[i] * th[i + 1] : 0);
    const Ma = -Dp * ((-3 * 0 + 4 * th[0] - th[1]) / (2 * h));
    add("BX · Disco: momento de la celda en el borde de la pastilla (diferencias finitas)", Math.abs(c.M_a), Math.abs(Ma), 1.0, "N·mm/mm");
    // (c) Par de los tornillos: Σ V_T·r = T_calado
    const T = D.disco.tornillos.lista.reduce((s, x) => s + x.VT * x.r, 0) / 1e6;
    add("BX · Tornillos del disco: Σ V_T·r = T_calado", T, R.TmaxTopes || R.Tmax, 0.01, "kN·m");
    // (d) Componente térmica de los tornillos: misma franja radial con resortes en los anillos, resuelta por Gauss–Seidel (otro método que el núcleo BX)
    const tw = D.disco.tornillos, Pc = A.Pc, eps = Math.abs(M.al - Pc.bx_al_st * 1e-6) * tw.dT_diseno, rr = tw.anillos, nOf = (r) => tw.lista.filter((x) => Math.abs(x.r - r) < 1e-6).length;
    const st = rr.map((r) => 2 * Math.PI * r / Math.max(1, nOf(r))), w = st[st.length - 1], EA = M.E * D.disco.t * w / (1 - M.nu ** 2), e0 = (1 + M.nu) * eps;
    const kb = rr.map((r) => BX_.huth(D.disco.t, M.E, r - tw.d / 2 > TT_prIn(Pc) ? Pc.t_pr : Pc.t_bot, Pc.E, tw.d)), K = rr.map((r, i) => kb[i] * w / st[i]), u = rr.map(() => 0);
    for (let it = 0; it < 20000; it++) { let dmax = 0;
      for (let i = 0; i < rr.length; i++) { const Lm = rr[i] - (i ? rr[i - 1] : 0), kL = EA / Lm, Lp = i < rr.length - 1 ? rr[i + 1] - rr[i] : 0, kR = Lp ? EA / Lp : 0;
        const un = (kL * ((i ? u[i - 1] : 0) + e0 * Lm) + (kR ? kR * (u[i + 1] - e0 * Lp) : 0)) / (kL + kR + K[i]); dmax = Math.max(dmax, Math.abs(un - u[i])); u[i] = un; }
      if (dmax < 1e-13) break; }
    add("BX · Tornillos del disco: componente térmica del anillo exterior (franja con resortes, Gauss–Seidel)", tw.Fth_ext, Math.abs(kb[rr.length - 1] * u[rr.length - 1]), 0.5, "N");
    // (e) Masa de la plancha del portador por muestreo en malla de 2 mm
    const C = D.portador, holes = C.agujeros.posiciones.concat(C.tapones.posiciones), H = new Map(), cs = C.paso;
    holes.forEach((p) => { const k = Math.floor(p[0] / cs) + "," + Math.floor(p[1] / cs); if (!H.has(k)) H.set(k, []); H.get(k).push(p); });
    let Ast = 0; const hs = 2;
    for (let x = -C.R_ext; x <= C.R_ext; x += hs) for (let y = -C.R_ext; y <= C.R_ext; y += hs) {
      const xc = x + hs / 2, yc = y + hs / 2, r = Math.hypot(xc, yc); if (r < C.R_int || r > C.R_ext) continue;
      const cx = Math.floor(xc / cs), cy = Math.floor(yc / cs); let inHole = false;
      for (let i = -1; i <= 1 && !inHole; i++) for (let j = -1; j <= 1 && !inHole; j++) { const L = H.get((cx + i) + "," + (cy + j)); if (L) for (const p of L) if (Math.hypot(p[0] - xc, p[1] - yc) < (C.agujeros.d) / 2) { inHole = true; break; } }
      if (!inHole) Ast += hs * hs;
    }
    add("BX · Portador: masa de la plancha (muestreo de 2 mm)", C.masa_plancha, 7.85e-6 * C.t * Ast, 1.0, "kg");
    return out;
  }

  function scenarios(A) {
    const sc = AG_.scenarios(Object.assign({}, A, { P: A.Pc || A.P }));
    if (A.bx && sc.ifaces && sc.ifaces[2]) sc.ifaces[2].name = "BX · Disco inoxidable atornillado + pastillas de UHMW en portador soldado";
    return sc;
  }
  function optimize() { return { ok: false, msg: "TT300-BX: el optimizador de masa del núcleo no evalúa las filas BX (pendiente); use BX.design con los parámetros bx_ manuales o automáticos" }; }

  return { validate, audit, crossCheck, scenarios, optimize, VARS: AG_.VARS, feasible: AG_.feasible };
})();
if (typeof module !== "undefined") module.exports = AGBX;
