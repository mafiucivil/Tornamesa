/* Pruebas del módulo TT300-BX (packages/core/tt300bx.js): disco inoxidable atornillado a la mesa (dos semidiscos con CJP) y pastillas de UHMW
   en un portador de acero soldado a la base. Corre en < 120 s:  node --test tests/test_tt300bx.js
   Incluye la verificación de que el núcleo TT300-C original sigue idéntico: (a) el subconjunto «golden» de tests/test_tt300c.js en un proceso hijo y
   (b) comparación bit a bit (JSON) del núcleo actual contra el de la base a67d98e (git show) en varias configuraciones, sin FEA. */
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path"), os = require("os"), cp = require("child_process");
const TT = require("../packages/core/tt300c.js"), BX = require("../packages/core/tt300bx.js"), AGBX = require("../packages/agents/agentes_bx.js");
const ROOT = path.join(__dirname, "..");
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol * Math.abs(b) + 1e-12, `${msg}: ${a} vs ${b} (tol ${tol * 100} %)`);

const P0 = BX.defaults();
const A0 = BX.analyze(P0, { noFEA: true });   // análisis por defecto sin FEA (rápido); la FEA se prueba aparte una vez
const G0 = A0.bx;

/* ---------- 1. El núcleo original no cambia ---------- */
test("Núcleo: el gancho P.__bx es aditivo; sin él los resultados son bit-idénticos a la base a67d98e (JSON, sin FEA)", () => {
  let src;
  try { src = cp.execFileSync("git", ["show", "a67d98e:packages/core/tt300c.js"], { cwd: ROOT, encoding: "utf8", maxBuffer: 64 << 20 }); }
  catch (e) { return; }   // sin git: la prueba del golden (abajo) cubre el caso
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "tt300c_base_"));
  fs.writeFileSync(path.join(dir, "tt300c.js"), src);
  fs.copyFileSync(path.join(ROOT, "packages/core/fea.js"), path.join(dir, "fea.js"));
  const OLD = require(path.join(dir, "tt300c.js"));
  const ser = (A) => JSON.stringify({ R: A.R, checks: A.checks, verdict: A.verdict }, (k, v) => (typeof v === "function" ? undefined : (typeof v === "number" && !isFinite(v) ? String(v) : v)));
  const cfgs = [{}, { opt_uhmw: 1 }, { opt_ss: 1 }, { opt_ss: 1, fix_mode: 2 }, { opt_bz: 1, bz_conf: 3 }, { opt_uhmw: 1, drive_mode: 1 }, { opt_uhmw: 1, opt_wood: 1 }];
  for (const o of cfgs) {
    const Pn = Object.assign(TT.defaults(), o), Po = Object.assign(OLD.defaults(), o);
    assert.equal(ser(TT.analyze(Pn, { noFEA: true })), ser(OLD.analyze(Po, { noFEA: true })), "configuración " + JSON.stringify(o));
  }
  // izaje (FEA de la base): usa la masa sobre la huella; sin BX no cambia
  const Pn = Object.assign(TT.defaults(), { opt_uhmw: 1 }), Rn = TT.compute(Pn), Ro = OLD.compute(Object.assign(OLD.defaults(), { opt_uhmw: 1 }));
  assert.equal(TT.runLift(Pn, Rn, true).vmMax, OLD.runLift(Object.assign(OLD.defaults(), { opt_uhmw: 1 }), Ro, true).vmMax, "izaje");
  assert.deepEqual(Object.keys(TT).sort(), Object.keys(OLD).sort(), "API del núcleo sin claves nuevas");
});

test("Núcleo: subconjunto golden de tests/test_tt300c.js sin cambios (proceso hijo)", () => {
  const env = Object.assign({}, process.env, { UPDATE_GOLDEN: "" }); delete env.NODE_TEST_CONTEXT; delete env.UPDATE_GOLDEN;   // proceso hijo independiente del ejecutor de pruebas; nunca regenera el golden
  const r = cp.spawnSync(process.execPath, ["--test", "--test-reporter=tap", "--test-name-pattern=[Gg]olden", path.join(ROOT, "tests/test_tt300c.js")], { cwd: ROOT, encoding: "utf8", timeout: 110000, env });
  assert.equal(r.status, 0, (r.stdout || "").slice(-3000) + (r.stderr || ""));
  assert.match(r.stdout, /# pass 6/);
  assert.match(r.stdout, /# fail 0/);
});

/* ---------- 2. Módulo BX: activación, gancho y masas ---------- */
test("BX: valores por defecto activan la opción B con el gancho; A y C pasan al núcleo sin tocar", () => {
  assert.equal(P0.opt_uhmw, 1); assert.equal(P0.opt_ss, 0); assert.equal(P0.opt_bz, 0);
  assert.ok(BX.active(P0));
  const I = A0.R.ifc;
  assert.equal(I.bx, true);
  assert.equal(I.topes.length, 0, "sin topes ni sectores");
  assert.equal(I.cortes.length, 0);
  near(I.delta, G0.portador.t + G0.pastillas.h_p + G0.disco.t, 1e-12, "δ = t_portador + saliente + t_disco");
  near(A0.R.m.ssTop, G0.disco.masa, 1e-12, "masa rotatoria = disco inoxidable");
  near(A0.R.m.uhmw, G0.pastillas.masa_total, 1e-12, "m.uhmw = pastillas");
  near(A0.R.m.bxPortador, G0.portador.masa, 1e-12, "portador en m.total");
  assert.ok(!A0.checks.some((c) => /sectores\)|Lámina UHMW|Disco de la base/.test(c.name)), "sin filas de los sectores de la opción B");
  // A y C: el módulo devuelve el análisis del núcleo
  const Aa = BX.analyze(Object.assign({}, P0, { opt_uhmw: 0, opt_ss: 1 }), { noFEA: true }), Ta = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true });
  assert.equal(Aa.bx, null);
  assert.equal(Aa.R.m.total, Ta.R.m.total);
});

test("BX: dimensiones adoptadas por defecto (disco 304 de 6 u 8 mm, 100–200 tornillos M10/M12) y estado de cada parte", () => {
  const D = G0.disco, U = G0.pastillas, C = G0.portador, T = D.tornillos;
  assert.match(D.material, /304/);
  assert.ok([6, 8].includes(D.t), "disco " + D.t + " mm");
  assert.ok(D.t >= D.t_req - 1e-9);
  assert.ok([10, 12].includes(T.d) && T.n >= 100 && T.n <= 200 && T.paso_malla >= 150, "tornillos " + T.n + " M" + T.d + " a " + T.paso_malla);
  assert.ok(U.n > 50 && U.n < 2000, "n pastillas " + U.n);
  assert.ok([20, 25, 30, 40, 50].includes(U.H), "pastilla cortada de plancha comercial: H = " + U.H);
  near(U.H, C.t + U.h_p, 1e-12, "H = t_portador + saliente");
  assert.ok(C.paso - U.d >= C.ligamento - 1e-9, "ligamento");
  assert.equal(A0.verdict.gira, true);
  const bxRows = A0.checks.filter((c) => c.bx);
  assert.ok(bxRows.length >= 40, "filas BX " + bxRows.length);
  bxRows.forEach((c) => { assert.ok(c.ref && c.formula && c.grp && c.sys, "fila completa: " + c.name); });
  // disco, tornillos y portador cumplen con margen (FU ≤ 0,90 o geométricas ≤ 1)
  bxRows.filter((c) => /Disco|Tornillos del disco|Portador/.test(c.name) && (c.kind === "fu" || c.kind === "geo")).forEach((c) => assert.ok(c.st === "ok", c.name + " FU " + c.fu));
  // lo que no cumple es solo el UHMW (pastillas): documentado en docs/bx/README_BX.md
  A0.checks.filter((c) => c.st === "fail").forEach((c) => assert.match(c.name, /^BX · Pastillas/, "falla no prevista: " + c.name));
  // 80 °C: limitación de uso informativa (no pendiente crítico)
  assert.ok(A0.verdict.limitaciones_uso.some((l) => l.id === "BX-T-SELLO"));
  assert.ok(!A0.verdict.pendientes_criticos.some((c) => /80 °C/.test(c.nombre)));
  assert.ok(A0.checks.some((c) => c.bx && /Pastillas a 50 °C: valor PV/.test(c.name)));
});

/* ---------- 3. Fórmulas ---------- */
test("BX: celda anular (borde interior empotrado, exterior guiado) frente a diferencias finitas", () => {
  const q = 1.7, a = 50, b = 80, D = 200000 * 8 ** 3 / (12 * (1 - 0.09)), nu = 0.3;
  const c = BX.cellPlate(q, a, b, D, nu);
  // Ecuación axisimétrica en la pendiente θ = w' por diferencias finitas centradas (tridiagonal), θ(a) = θ(b) = 0; M_r = −D(θ' + νθ/r); w(b) − w(a) = ∫θ dr.
  const n = 4000, h = (b - a) / n, A = [], B = [], Cc = [], Rhs = [];
  for (let i = 1; i < n; i++) { const r = a + i * h, Q = q * (r * r - b * b) / (2 * r);   // D·d/dr[(1/r)·d(rθ)/dr] = q·(r² − b²)/(2r) (corte nulo en el borde guiado b)
    // θ'' + θ'/r − θ/r² = Q/D
    A.push(1 / (h * h) - 1 / (2 * r * h)); B.push(-2 / (h * h) - 1 / (r * r)); Cc.push(1 / (h * h) + 1 / (2 * r * h)); Rhs.push(Q / D); }
  const m = n - 1, cp_ = new Array(m), dp = new Array(m), th = new Array(m);
  for (let i = 0; i < m; i++) { const den = B[i] - (i ? A[i] * cp_[i - 1] : 0); cp_[i] = Cc[i] / den; dp[i] = (Rhs[i] - (i ? A[i] * dp[i - 1] : 0)) / den; }
  for (let i = m - 1; i >= 0; i--) th[i] = dp[i] - (i < m - 1 ? cp_[i] * th[i + 1] : 0);
  const thAt = (i) => (i <= 0 || i >= n ? 0 : th[i - 1]);
  const Mr = (i) => { const r = a + i * h, d = (i === 0 ? (-3 * thAt(0) + 4 * thAt(1) - thAt(2)) / (2 * h) : i === n ? (3 * thAt(n) - 4 * thAt(n - 1) + thAt(n - 2)) / (2 * h) : (thAt(i + 1) - thAt(i - 1)) / (2 * h)); return -D * (d + nu * thAt(i) / r); };
  let w = 0; for (let i = 0; i < n; i++) w += (thAt(i) + thAt(i + 1)) / 2 * h;
  near(Math.abs(c.Ma), Math.abs(Mr(0)), 0.01, "M_r en el borde empotrado");
  near(Math.abs(c.Mb), Math.abs(Mr(n)), 0.01, "M_r en el borde guiado");
  near(Math.abs(c.w), Math.abs(w), 0.01, "flecha relativa");
});

test("BX: rigidez de Huth y fuerza térmica de borde frente a una cadena discreta de resortes", () => {
  const k = BX.huth(8, 193000, 16, 200000, 10);
  assert.ok(k > 1e5 && k < 4e5, "rigidez " + k);
  // franja radial: barra E·t·s/(1−ν²) sobre resortes k cada s_r; deformación libre ε(1+ν); semi-infinita (n grande): fuerza en el último resorte
  const E = 200000, t = 8, nu = 0.3, s = 150, sr = 150, eps = 1.3e-6 * 60, kb = k;
  const F = BX.edgeForce({ E, t, nu, eps, kb, st: s, sr });
  const EA = E * t * s / (1 - nu * nu), n = 200, kbar = EA / sr, e0 = eps * (1 + nu);
  // equilibrio de nudos: u_i, barra entre i e i+1 con fuerza kbar·(u_{i+1} − u_i − e0·sr); resorte k·u_i; nudo 0 en el centro (u = 0), nudo n en el borde libre
  const a = [], b = [], c = [], r = [];
  for (let i = 1; i <= n; i++) { const last = i === n; a.push(-kbar); b.push((last ? kbar : 2 * kbar) + kb); c.push(last ? 0 : -kbar); r.push(last ? kbar * e0 * sr : 0); }
  const m = n, cp_ = [], dp = [], u = new Array(m);
  for (let i = 0; i < m; i++) { const den = b[i] - (i ? a[i] * cp_[i - 1] : 0); cp_[i] = c[i] / den; dp[i] = (r[i] - (i ? a[i] * dp[i - 1] : 0)) / den; }
  for (let i = m - 1; i >= 0; i--) u[i] = dp[i] - (i < m - 1 ? cp_[i] * u[i + 1] : 0);
  near(F, kb * u[m - 1], 0.01, "fuerza del resorte de borde (fórmula cerrada de la cadena frente a la solución numérica)");
});

test("BX: equilibrio de presiones de las pastillas, presión ≥ q y PV con la velocidad del núcleo", () => {
  const U = G0.pastillas, Rr = A0.R;
  near(U.suma_N_kN, Rr.ND, 0.01, "Σ q·dA sobre las pastillas = N_D");
  assert.ok(U.p_max > Rr.q_max, "p_pastilla > q_máx (cobertura < 1)");
  assert.ok(U.cobertura > 0.4 && U.cobertura < 0.9);
  const vcyl = P0.Q_pump * 1e6 / 60 / (P0.n_cyl * Rr.A), w = vcyl / Rr.K.armMin;
  near(U.PV_max, Math.max(...U.lista.map((q) => q.p * q.r * w / 1000)), 1e-9, "PV");
});

test("BX: patrón radial con transferencia perimetral; la variante con agujeros de soldadura cumple la regla de un salto", () => {
  const C = G0.portador;
  assert.equal(C.patron.tipo, "radial");
  assert.equal(C.tapones.n, 0, "sin agujeros de soldadura por defecto");
  const tq = A0.checks.find((c) => /corte por torsión en la sección neta crítica/.test(c.name));
  assert.ok(tq && tq.fu <= 0.9, "torsión del portador");
  // separación mínima entre centros ≥ paso (ligamento ≥ lig)
  const L = G0.pastillas.lista; let m = Infinity;
  for (let i = 0; i < L.length; i++) for (let j = i + 1; j < L.length; j++) m = Math.min(m, Math.hypot(L[i].x - L[j].x, L[i].y - L[j].y));
  assert.ok(m >= C.paso - 1e-6, "separación " + m + " < paso " + C.paso);
  // variante triangular con agujeros de soldadura √7: un salto como máximo
  const Gt = BX.design(Object.assign({}, P0, { bx_pat: 1, bx_nw: 7 }));
  assert.equal(Gt.portador.patron.tipo, "triangular");
  assert.equal(Gt.portador.patron.saltos_max, 1);
  assert.ok(Gt.portador.tapones.n > 0);
});

test("BX: interferencia en frío, montaje y caliente; tornillo de la pastilla fuera del camino del arrastre", () => {
  const U = G0.pastillas, f = U.ajuste;
  assert.ok(f.delta_min_20 >= -1e-9, "interferencia mínima a 20 °C ≥ 0");
  assert.ok(f.holgura_frio <= P0.bx_c_sp - 0.2 + 1e-9, "holgura en frío ≤ holgura del agujero del tornillo − 0,2");
  assert.ok(f.eps_caliente <= P0.bx_eps_max / 100 + 1e-12);
  near(f.d_dil_caliente, (P0.bx_al_uh * 1e-6 - P0.bx_al_st * 1e-6) * (P0.T_ifc_max - P0.T_ref) * U.d, 1e-9, "Δd caliente con α_UHMW = 190×10⁻⁶");
});

test("BX: tornillos del disco: corte primario por el par (J3.7); térmica secundaria repartida por rigidez; membrana y pandeo del disco", () => {
  const T = G0.disco.tornillos;
  near(T.lista.reduce((s, b) => s + b.VT * b.r, 0) / 1e6, A0.R.TmaxTopes, 1e-9, "Σ V_T·r = T_calado");
  assert.ok(T.V_primario <= 0.9 * T.capV);
  assert.equal(T.dT_diseno, 30, "ΔT de servicio 0–50 °C con montaje a 20 °C");
  assert.equal(T.Vth_anillos.length, T.anillos.length);
  assert.ok(T.Vth_anillos[T.Vth_anillos.length - 1] >= T.Vth_anillos[0], "el anillo exterior toma más");
  const prim = A0.checks.find((c) => /corte de diseño por el par/.test(c.name)), sec = A0.checks.find((c) => /componente térmica secundaria/.test(c.name));
  assert.equal(prim.kind, "fu"); assert.equal(sec.kind, "info");
  const th = G0.disco.termico; near(th.sigma_uniaxial, 193000 * 5.3e-6 * 30, 1e-9, "σ = E·Δα·ΔT ≈ 31 MPa");
  ["rango frente a 2·Fy", "frente a Fy", "pandeo por la compresión térmica"].forEach((k) => { const c = A0.checks.find((x) => x.bx && x.name.includes(k)); assert.ok(c && c.st === "ok", k); });
  T.lista.forEach((b) => { assert.ok(Math.abs(b.y) >= P0.bx_c_cjp - 1e-9); });
});

test("BX: tabla de fabricación (antes → después, motivo y verificación) y JSON puro", () => {
  const F = G0.fabricacion;
  assert.ok(F.length >= 12);
  F.forEach((f) => { assert.ok(f.pieza && f.antes && f.despues && f.motivo && f.verificacion && f.estado, JSON.stringify(f)); });
  assert.ok(F.some((f) => f.estado === "se mantiene") && F.some((f) => f.estado === "simplificada") && F.some((f) => f.estado === "eliminada"));
  JSON.stringify(G0);
});

test("BX: agentes (validador, auditor, revisor cruzado y escenarios) sobre el módulo", () => {
  assert.equal(AGBX.validate(P0).filter((v) => v.lvl === "error").length, 0);
  const au = AGBX.audit(A0.checks); assert.ok(au.ok, JSON.stringify(au.missing.map((c) => c.name)));
  const cc = AGBX.crossCheck(A0); assert.ok(cc.length >= 5); cc.filter((c) => c.bx).forEach((c) => assert.ok(c.ok, c.name + " " + c.tool + " / " + c.indep));
  const sc = AGBX.scenarios(A0); assert.match(sc.ifaces[2].name, /BX/);
  assert.ok(AGBX.validate(Object.assign({}, P0, { bx_pat: 3 })).some((v) => v.lvl === "error"));
});

test("BX: análisis con FEA (mesa, flexión global, izaje con el portador) y escenario térmico a 80 °C", () => {
  const A = BX.analyze(P0);
  assert.ok(A.fea && A.fea.lift.vmMax > 0);
  assert.equal(A.verdict.gira, true);
  A.checks.filter((c) => c.st === "fail").forEach((c) => assert.match(c.name, /^BX · Pastillas/, "con FEA, falla no prevista: " + c.name));   // mesa, base e izaje cumplen
  const th = BX.thermal(P0, { T: [20, 80] });
  const b = th.alternativas[0], b80 = b.byT.find((x) => x.T === 80), b20 = b.byT.find((x) => x.T === 20);
  assert.ok(b80.bx && b80.bx.filas.length > 10);
  assert.ok(b80.bx.fuEst >= b20.bx.fuEst, "a 80 °C empeora");
  const p80 = b80.bx.filas.find((r) => /presión máxima/.test(r.nombre));
  near(p80.cap, P0.p_uhmw * P0.kT_p_uh, 1e-9, "p_adm a 80 °C = k_p·p_adm");
});
