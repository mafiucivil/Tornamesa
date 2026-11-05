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

test("Interfaz alternativa: discos inoxidables (A) y discos con UHMW (B)", () => {
  const base = TT.analyze(TT.defaults(), { noFEA: true }), P0 = TT.defaults();
  assert.equal(base.R.ifc.o, 0); assert.equal(base.R.ifc.delta, 0); assert.equal(base.R.m.ss + base.R.m.uhmw, 0);
  // A: espesor por flexión sobre vacío local de una placa empotrada, σ = 3qa²/(4t²) = 0,6Fy
  const A = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }), I = A.R.ifc;
  const a = P0.ss_void / 2, tf = a * Math.sqrt(0.75 * I.q / (0.6 * P0.Fy_ss));
  near(I.tFlex, tf, 1e-9, "t_flex"); near(I.tssReq, Math.max(tf + P0.ss_allow, P0.ss_tmin), 1e-9, "t_req");
  assert.ok(I.tss >= I.tssReq && [3, 4, 5, 6, 8, 10, 12, 15, 20, 25].includes(I.tss), "espesor comercial ≥ requerido");
  assert.ok(A.checks.filter((c) => c.grp === "Interfaz inox" && c.st !== "info").every((c) => c.st !== "fail"), "A cumple");
  near(A.R.hax, P0.h_disc / 2 + 2 * I.tss, 1e-12, "el eje de los cilindros sube 2·t_disco");
  const Aarea = Math.PI * (A.R.Ro ** 2 - A.R.Ri ** 2);
  near(A.R.m.ss, 2 * 7.93e-6 * Aarea * I.tss, 1e-9, "masa de los discos");
  assert.deepEqual([A.R.mu.nom, A.R.mu.d, A.R.mu.cont, A.R.mu.dry], [P0.muA_nom, P0.muA_d, P0.muA_cont, P0.muA_dry]);
  // B: lámina UHMW t ≥ E·δ/(p_adm − q)
  const B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }), J = B.R.ifc;
  // t_conf = E_c(S)·δ/(p_adm − q), con E_c = E[1 + (M/E − 1)S²/(1+S²)], S = D/(4t) (módulo confinado de lámina delgada)
  const Mf = 0.55 / (1.45 * 0.1), Sx = P0.ss_void / (4 * J.tuhConf);
  near(J.tuhConf, P0.E_uhmw * (1 + (Mf - 1) * Sx * Sx / (1 + Sx * Sx)) * P0.d_flat / (P0.p_uhmw - J.q), 1e-6, "t_conf UHMW (módulo confinado)");
  assert.ok(J.tuhConf > P0.E_uhmw * P0.d_flat / (P0.p_uhmw - J.q), "el confinamiento exige más espesor que el módulo uniaxial");
  assert.ok(J.tuh >= J.tuhReq, "UHMW comercial ≥ requerido");
  near(B.R.hax, P0.h_disc / 2 + 2 * J.tss + J.tuh, 1e-12, "el eje sube 2·t_disco + t_UHMW");
  assert.ok(B.R.cases.find((c) => c.id === "nom").F < A.R.cases.find((c) => c.id === "nom").F, "con UHMW baja la fuerza nominal (μ menor)");
  assert.ok(B.R.mu.d >= B.R.mu.nom && B.R.mu.cont >= B.R.mu.d && B.R.mu.dry >= B.R.mu.d, "μ de B ordenados: nominal ≤ diseño ≤ contaminado, seco");
  // espesor manual: un disco de 3 mm no cumple el mínimo constructivo ni la flexión
  const thin = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, t_ss: 3 }), { noFEA: true });
  assert.ok(thin.checks.some((c) => c.grp === "Interfaz inox" && c.st === "fail"), "3 mm no cumple");
  // las dos opciones a la vez son un error de validación
  assert.ok(AG.validate(Object.assign(TT.defaults(), { opt_ss: 1, opt_uhmw: 1 })).some((v) => v.lvl === "error"), "A y B excluyentes");
});

test("Interfaz alternativa C: placa de bronce con tapones de grafito", () => {
  const P0 = TT.defaults();
  const run = (o) => TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1 }, o), { noFEA: true });
  const C1 = run({}), I = C1.R.ifc;
  // t_flex = a·√(0,75q/(0,6Fy_bz)); t_req = t_flex/√η + sobreespesor, con η = (p − d)/p
  const eta = (P0.bz_plug_p - P0.bz_plug_d) / P0.bz_plug_p, a = P0.ss_void / 2, tf = a * Math.sqrt(0.75 * I.q / (0.6 * P0.Fy_bz));
  near(I.tFlexB, tf, 1e-9, "t_flex del bronce"); near(I.tbzReq, Math.max(tf / Math.sqrt(eta) + P0.bz_allow, P0.bz_tmin), 1e-9, "t_req del bronce");
  assert.ok([4, 5, 6, 8, 10, 12, 15, 20, 25, 30].includes(I.tbz) && I.tbz >= I.tbzReq, "espesor comercial ≥ requerido");
  near(C1.R.hax, P0.h_disc / 2 + I.tbz + I.tss, 1e-12, "el eje sube t_bronce + t_disco");
  assert.deepEqual([C1.R.mu.nom, C1.R.mu.d, C1.R.mu.cont, C1.R.mu.dry], [P0.muC_nom, P0.muC_d, P0.muC_cont, P0.muC_dry]);
  assert.ok(C1.R.mu.nom <= C1.R.mu.d && C1.R.mu.d <= C1.R.mu.cont && C1.R.mu.d <= C1.R.mu.dry, "μ ordenados");
  assert.ok(C1.R.m.bz > 0 && C1.R.m.ss > 0, "masa de bronce y de disco duro");
  // configuraciones 1, 2 y 3 cumplen por defecto y no dejan verificaciones en falla
  [{}, { bz_conf: 2 }, { bz_conf: 3 }].forEach((o) => { const A = run(o); assert.ok(A.verdict.gira && A.verdict.estructura, "C " + JSON.stringify(o) + " cumple"); });
  // configuración 3: la presión local sube con 1/cobertura
  const C3 = run({ bz_conf: 3 }); near(C3.R.ifc.qLoc, C3.R.ifc.q / P0.bz_cover, 1e-9, "q local con pastillas");
  assert.ok(C3.R.m.bz < C1.R.m.bz * 1.05 || C3.R.ifc.tbz > C1.R.ifc.tbz, "pastillas: menos bronce o más espesor");
  // con 40 % de cobertura el pegado no alcanza para el par de calado
  assert.ok(run({ bz_conf: 3, bz_cover: 0.4 }).checks.some((c) => /Retención de la placa de bronce/.test(c.name) && c.st === "fail"), "retención falla con 40 %");
  // espesor manual insuficiente, exclusión con A y B, y tapones mayores que el paso
  assert.ok(run({ t_bz: 4 }).checks.some((c) => c.grp === "Interfaz bronce" && c.st === "fail"), "4 mm no cumple");
  assert.ok(AG.validate(Object.assign(TT.defaults(), { opt_bz: 1, opt_ss: 1 })).some((v) => v.lvl === "error"), "A y C excluyentes");
  assert.ok(AG.validate(Object.assign(TT.defaults(), { opt_bz: 1, bz_plug_d: 40, bz_plug_p: 30 })).some((v) => v.lvl === "error"), "tapón menor que el paso");
  assert.throws(() => TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, opt_uhmw: 1 })), /excluyentes/);
  // las cuatro alternativas con la carga de izaje: ninguna falla la flecha de la base
  [{}, { opt_ss: 1 }, { opt_uhmw: 1 }, { opt_bz: 1 }].forEach((o) => { const A = TT.analyze(Object.assign(TT.defaults(), o)); assert.ok(A.checks.filter((c) => /Izaje/.test(c.name)).every((c) => c.st !== "fail"), "izaje " + JSON.stringify(o)); });
});

test("Un cilindro (n° impar): el pivote reacciona con la fuerza tangencial del pasador", () => {
  const two = TT.analyze(TT.defaults(), { noFEA: true });
  assert.ok(!two.checks.some((c) => /empuje no equilibrado/.test(c.name)), "con 2 cilindros el par es puro");
  const one = TT.analyze(Object.assign(TT.defaults(), { n_cyl: 1, W_tf: 150 }), { noFEA: true });
  const row = one.checks.find((c) => /empuje no equilibrado/.test(c.name));
  assert.ok(row && row.dem > 200, "reacción de diseño ≈ F_pas");
  const bush = one.checks.find((c) => /Presión en el buje/.test(c.name));
  near(bush.dem, (TT.compute(Object.assign(TT.defaults(), { n_cyl: 1, W_tf: 150 })).H_ecc(0.2) + row.dem + 0) * 1e3 / (TT.defaults().D_piv * TT.defaults().L_bush), 0.25, "presión del buje con la reacción");
  assert.equal(bush.st, "fail", "con 1 cilindro y 150 tf el buje no cumple (antes daba 0,33 por omitir la reacción)");
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
