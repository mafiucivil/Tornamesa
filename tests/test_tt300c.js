/* Pruebas del núcleo TT300-C: benchmarks FEA, cinemática KIET, agentes y golden file.
   Ejecutar: node --test tests/   ·   regenerar golden: UPDATE_GOLDEN=1 node --test tests/ */
const test = require("node:test"), assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");
const FEA = require("../packages/core/fea.js"), TT = require("../packages/core/tt300c.js"), AG = require("../packages/agents/agentes.js");
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol * Math.abs(b), `${msg}: ${a} vs ${b} (tol ${tol * 100} %)`);

test("FEA: placa simplemente apoyada (Navier)", () => {
  const a = 1000, n = 20, nodes = [], elems = [];
  for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) nodes.push([i * a / n, j * a / n]);
  const id = (i, j) => i * (n + 1) + j;
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
  const wFix = [], betaN = [];
  for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) {
    if (i === 0 || i === n) { wFix.push(id(i, j)); betaN.push([id(i, j), 0, 1]); } else if (j === 0 || j === n) { wFix.push(id(i, j)); betaN.push([id(i, j), 1, 0]); }
  }
  const r = FEA.plate({ nodes, elems, t: 10, E: 2e5, nu: 0.3, q: new Float64Array(elems.length).fill(0.01), wFix, betaN });
  const D = 2e5 * 1000 / (12 * 0.91);
  near(r.w[id(n / 2, n / 2)], 0.00406 * 0.01 * 1e12 / D, 0.005, "flecha central");
  near(Math.abs(r.Rsum), r.Fapplied, 1e-6, "equilibrio");
});

test("FEA: voladizo en tensión plana", () => {
  const L = 1000, h = 100, nx = 80, ny = 10, N = [], E = [];
  for (let i = 0; i <= nx; i++) for (let j = 0; j <= ny; j++) N.push([i * L / nx, j * h / ny]);
  const id = (i, j) => i * (ny + 1) + j;
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) E.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
  const fix = []; for (let j = 0; j <= ny; j++) fix.push([id(0, j), 0], [id(0, j), 1]);
  const loads = []; for (let j = 0; j <= ny; j++) loads.push([id(nx, j), 0, -1000 / (ny + 1)]);
  const r = FEA.planeStress({ nodes: N, elems: E, t: 10, E: 2e5, nu: 0.3, fix, loads });
  near(-r.u[2 * id(nx, ny / 2) + 1], 2.026, 0.02, "flecha de punta");
});

test("Accionamiento guiado: reproduce el factor de guía de TT300-B (K = 1,2403)", () => {
  // TT300-B: barras R940, 36, guía en x = 1085, Lg = 250, μg 0,15, η 0,95 → K = 1,24031, brazo 936,42
  const P = Object.assign(TT.defaults(), { R_pin: 940, N_pin: 36, N_rib: 12, x_g: 1085, d_pin: 70, d_pp: 70, l_p: 267.5, mu_g: 0.15, eta_c: 0.95, f_ext: 0, mu_s: 0 });
  const K = TT.kinematics(P), R = TT.compute(P);
  near(K.L_s, 375, 1e-9, "largo del patín para Lg = 250");
  near(K.armMin, 936.42, 1e-4, "brazo mínimo R·cos(π/N)");
  near(R.Kguide, 1.24031, 1e-4, "factor de guía");
  near(K.s_req, P.s_free + 2 * 940 * Math.sin(Math.PI / 36), 1e-9, "carrera = libre + cuerda");
});

test("Cara plana: fricción de la cara cambia de sentido en y_p = r y μ_s = 0 recupera el modelo sin fricción", () => {
  const P = TT.defaults(), R = TT.compute(P), r = P.d_pin / 2;
  const thX = Math.asin(r / P.R_pin), atX = R.stroke.filter((q) => Math.abs(q.th - thX) < 1e-12);
  assert.equal(atX.length, 2, "ambos sentidos evaluados en el cambio");
  assert.ok(R.stroke.filter((q) => P.R_pin * Math.sin(q.th) < r - 1e-9).every((q) => q.H < 0), "antes del cambio la fricción sobre el pasador apunta hacia el centro");
  assert.ok(R.stroke.filter((q) => P.R_pin * Math.sin(q.th) > r + 1e-9).every((q) => q.H > 0), "después del cambio apunta hacia afuera");
  const Q = Object.assign(TT.defaults(), { mu_s: 0 }), RQ = TT.compute(Q), K = TT.kinematics(Q);
  const Fold = RQ.cd.T * 1e3 / (Q.n_cyl * K.armMin) * (1 + 2 * Q.mu_g * (Q.x_g - K.armMin) / K.Lg) / Q.eta_c;
  near(RQ.cd.F, Fold, 1e-9, "μ_s = 0: F = K·T/(n·a_mín)");
  assert.ok(R.cd.F > RQ.cd.F, "la fricción de la cara aumenta la fuerza");
});

test("Detecta fallas de diseño del accionamiento: autobloqueo del chaflán y patín sin retención", () => {
  const lock = TT.analyze(Object.assign(TT.defaults(), { beta_ch: 70, mu_ret: 0.3 }), { coarse: true }).checks.find((c) => /autobloqueo/.test(c.name));
  assert.equal(lock.st, "fail", "β = 70° con μ = 0,3 se autobloquea");
  const noT = TT.analyze(Object.assign(TT.defaults(), { h_tee: 0, t_bed: 34 }), { coarse: true }).checks.find((c) => /sin retención vertical/.test(c.name));
  assert.ok(noT && noT.st === "fail", "sin ranura T el patín vuelca");
});

test("Valores por defecto: sin errores, gira y la estructura cumple", () => {
  const P = TT.defaults();
  assert.equal(AG.validate(P).filter((v) => v.lvl === "error").length, 0);
  const A = TT.analyze(P);
  assert.ok(A.verdict.gira, "gira");
  assert.ok(A.verdict.estructura, "estructura");
  assert.ok(A.checks.filter((c) => c.sys === "est" && c.kind === "fu").every((c) => c.fu <= 0.90), "FU ≤ 0,90 en estructura");
});

test("Agentes: auditor y revisor cruzado sin observaciones", () => {
  const A = TT.analyze(TT.defaults());
  const au = AG.audit(A.checks);
  assert.ok(au.ok, "todas las verificaciones con fórmula y referencia");
  for (const c of AG.crossCheck(A)) assert.ok(c.ok, "revisor cruzado: " + c.name + " Δ " + c.d);
});

test("Validador: detecta incompatibilidades", () => {
  const bad = Object.assign(TT.defaults(), { N_rib: 12, D_bore: 50, d_rod: 55 });
  const v = AG.validate(bad).filter((x) => x.lvl === "error").map((x) => x.msg).join(" | ");
  assert.match(v, /múltiplo/); assert.match(v, /émbolo/);
});

test("Giro: con μ 0,35 la herramienta declara que no gira", () => {
  const A = TT.analyze(Object.assign(TT.defaults(), { mu_d: 0.35 }), { noFEA: true });
  assert.equal(A.verdict.gira, false);
});

test("Optimizador: resultado factible y no más pesado", () => {
  const P = Object.assign(TT.defaults(), { t_top: 30, t_bot: 30, t_base: 30 });
  const m0 = TT.masses(P).total, o = AG.optimize(P);
  assert.ok(o.ok, "factible");
  assert.ok(o.A.R.m.total < m0, "más liviano");
  assert.ok(o.A.verdict.gira && o.A.verdict.estructura);
});

test("Golden file: resultados por defecto sin cambios no justificados", () => {
  const A = TT.analyze(TT.defaults()), R = A.R;
  const snap = {
    masa_total: R.m.total, masa_mesa: R.m.disc, N: R.N, q_max: R.q_max, F_calado: R.Fstall, brazo_min: R.K.armMin, carrera_req: R.K.s_req,
    casos: Object.fromEntries(R.cases.map((c) => [c.id, [c.F, c.p, c.FS]])),
    fea: { top: A.fea.top.vmMax, bot: A.fea.bot.vmMax, lift: A.fea.lift.vmMax, glob: A.fea.glob.Mmax },
    fu: Object.fromEntries(A.checks.filter((c) => c.fu != null).map((c) => [c.grp + " · " + c.name, c.fu])),
  };
  const f = path.join(__dirname, "golden", "tt300c_defaults.json");
  if (process.env.UPDATE_GOLDEN || !fs.existsSync(f)) fs.writeFileSync(f, JSON.stringify(snap, null, 1));
  const g = JSON.parse(fs.readFileSync(f, "utf8"));
  const cmp = (a, b, k) => {
    if (typeof b === "number") near(a, b, 1e-6, k);
    else if (Array.isArray(b)) b.forEach((v, i) => cmp(a[i], v, k + "[" + i + "]"));
    else for (const kk of Object.keys(b)) { assert.ok(kk in a, "falta " + kk); cmp(a[kk], b[kk], k + "." + kk); }
  };
  cmp(snap, g, "golden");
});
