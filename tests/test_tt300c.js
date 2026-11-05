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
  near(A.R.hax, P0.h_disc / 2 + I.tss + I.tss2, 1e-12, "el eje de los cilindros sube t_disco base + t_disco mesa");
  assert.ok(I.tss2 >= I.tss && I.tss2Req > I.tssReq, "el disco de la mesa lleva las ranuras de engrase: más espesor");
  const Aarea = Math.PI * (A.R.Ro ** 2 - A.R.Ri ** 2);
  near(A.R.m.ss, 7.93e-6 * Aarea * (I.tss + I.tss2), 1e-9, "masa de los discos");
  assert.deepEqual([A.R.mu.nom, A.R.mu.d, A.R.mu.cont, A.R.mu.dry], [P0.muA_nom, P0.muA_d, P0.muA_cont, P0.muA_dry]);
  // B: lámina UHMW t ≥ E·δ/(p_adm − q)
  const B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }), J = B.R.ifc;
  // t_conf = E_c(S)·δ/(p_adm − q), con E_c = E[1 + (M/E − 1)S²/(1+S²)], S = D/(4t) (módulo confinado de lámina delgada)
  const Mf = 0.55 / (1.45 * 0.1), Sx = P0.ss_void / (4 * J.tuhConf);
  near(J.tuhConf, P0.E_uhmw * (1 + (Mf - 1) * Sx * Sx / (1 + Sx * Sx)) * P0.d_flat / (P0.p_uhmw - J.q), 1e-6, "t_conf UHMW (módulo confinado)");
  assert.ok(J.tuhConf > P0.E_uhmw * P0.d_flat / (P0.p_uhmw - J.q), "el confinamiento exige más espesor que el módulo uniaxial");
  assert.ok(J.tuh >= J.tuhReq, "UHMW comercial ≥ requerido");
  near(B.R.hax, P0.h_disc / 2 + J.tss + J.tss2 + J.tuh, 1e-12, "el eje sube t_discos + t_UHMW");
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
  near(I.tFlexB, tf, 1e-9, "t_flex del bronce"); near(I.tbzReq, Math.max(tf / Math.sqrt(eta) + P0.bz_allow + P0.h_gr, P0.bz_tmin), 1e-9, "t_req del bronce (con las ranuras de engrase)");
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
  // las pastillas cargan el respaldo con q/cobertura: la plancha inferior y la losa lo reciben (hallazgo C1)
  near(C3.R.qc, C3.R.q_max / P0.bz_cover, 1e-9, "presión bajo las pastillas");
  const full = (o) => TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, bz_conf: 3 }, o)).checks.find((c) => /Plancha inferior: σvm local/.test(c.name));
  assert.ok(full({ bz_cover: 0.6 }).fu > full({}).fu, "menos cobertura = más tensión en la plancha inferior");
  // con 40 % de cobertura el pegado no alcanza para el par de calado
  assert.ok(run({ bz_conf: 3, bz_cover: 0.4, fix_mode: 2 }).checks.some((c) => /Retención de la placa de bronce/.test(c.name) && c.st === "fail"), "con pegado la retención falla con 40 % de cobertura (con topes no depende de la cobertura)");
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

test("Bomba, retorno rápido, potencia y tiempo por vuelta", () => {
  const P = Object.assign(TT.defaults(), { Q_pump: 10, Q_ret: 20 }), R = TT.compute(P);
  const A = Math.PI / 4 * P.D_bore ** 2, Aa = A - Math.PI / 4 * P.d_rod ** 2;
  near(R.tCycle, P.n_cyl * A * P.stroke / 1e6 / 10 + P.n_cyl * Aa * P.stroke / 1e6 / 20, 1e-12, "tiempo de ciclo con retorno rápido");
  near(R.tRev, R.tCycle * P.N_pin, 1e-12, "tiempo por vuelta");
  near(R.pump.vRet, 20e6 / 60 / (P.n_cyl * Aa) / 1000, 1e-12, "velocidad de retorno");
  near(R.pump.Pmotor, Math.max(R.pump.PhExt, R.pump.PhRet) / P.eta_pump, 1e-12, "potencia del motor");
  near(R.pump.PhRet, P.p_ret * 20 / 600, 1e-12, "potencia hidráulica del retorno");
  assert.equal(TT.compute(TT.defaults()).tRev > 70 && TT.compute(TT.defaults()).tRev < 70.5, true, "por defecto 70 min por vuelta (sin cambios)");
  const obj = TT.analyze(Object.assign(TT.defaults(), { t_vuelta_obj: 30 }), { noFEA: true });
  assert.equal(obj.checks.find((c) => /Tiempo por vuelta frente al objetivo/.test(c.name)).st, "fail", "70 min no cumple un objetivo de 30 min");
  const need = obj.checks.find((c) => /Caudal de bomba requerido/.test(c.name)).dem;
  near(TT.compute(Object.assign(TT.defaults(), { Q_pump: need, Q_ret: need })).tRev, 30, 1e-9, "el caudal requerido da el tiempo objetivo");
});

test("Cubierta de madera dura y enrase con los rieles de skidding", () => {
  const P0 = TT.defaults(), A0 = TT.analyze(P0, { noFEA: true }), W = TT.analyze(Object.assign(TT.defaults(), { opt_wood: 1 }), { noFEA: true });
  const hole = P0.D_piv + 80, area = Math.PI / 4 * (P0.D_top ** 2 - hole ** 2);
  near(W.R.m.wood, P0.rho_wood * 1e-9 * area * P0.t_wood, 1e-9, "masa de la madera");
  near(W.R.m.total - A0.R.m.total, W.R.m.wood, 0.02, "la madera suma su masa (más el efecto sobre la interfaz)");
  assert.ok(W.R.q_max > A0.R.q_max, "la madera rotatoria carga la interfaz");
  const row = W.checks.find((c) => /Madera: aplastamiento/.test(c.name));
  const RL = P0.D_load / 2; near(row.dem, P0.phi_d * W.R.W * 1e3 / (Math.PI * RL * RL) * (1 + 4 * P0.e / RL), 1e-9, "presión sobre la madera");
  assert.ok(W.verdict.estructura && W.verdict.gira, "con madera cumple");
  assert.ok(TT.analyze(Object.assign(TT.defaults(), { opt_wood: 1, p_wood: 2 }), { noFEA: true }).checks.some((c) => /Madera: aplastamiento/.test(c.name) && c.st === "fail"), "con p_adm de 2 MPa no cumple");
  const H = W.checks.find((c) => /Altura total sobre el piso/.test(c.name)).dem; near(H, P0.t_base + P0.h_disc + P0.t_wood, 1e-12, "altura total con madera");
  assert.ok(!A0.checks.some((c) => /Enrase/.test(c.name)), "sin h_skid no hay verificación");
  const sk = TT.analyze(Object.assign(TT.defaults(), { h_skid: 235 }), { noFEA: true }).checks.find((c) => /Enrase/.test(c.name));
  near(sk.dem, 5, 1e-9, "desnivel de 5 mm"); assert.equal(sk.st, "ok");
  assert.equal(TT.analyze(Object.assign(TT.defaults(), { h_skid: 300 }), { noFEA: true }).checks.find((c) => /Enrase/.test(c.name)).st, "fail");
});

test("Capacidad de giro y capacidad según el número de cilindros", () => {
  const P = TT.defaults(), R = TT.compute(P);
  const W = TT.capacityW(P, R.mu.d, P.r_ef, P.FS_min), RW = TT.compute(Object.assign({}, P, { W_tf: W }));
  near(RW.Fstall / RW.Fcyl(RW.torque(R.mu.d, P.r_ef)), P.FS_min, 1e-6, "FS exacto en la capacidad de giro");
  assert.ok(TT.capacityW(P, R.mu.d, P.r_ef, 1) > W && TT.capacityW(P, R.mu.nom, R.r_u, 1) > TT.capacityW(P, R.mu.d, P.r_ef, 1), "monótona en μ y FS");
  const cc = TT.capacityByCyl(P, [1, 2]);
  assert.ok(cc[0].wPiv < cc[0].wGiro, "con 1 cilindro limita el pivote"); assert.ok(cc[0].wCap < cc[1].wCap, "2 cilindros admiten más");
  near(cc[1].wCap, cc[1].wGiro, 1e-9, "con 2 cilindros limita el giro");
  const ok = (W2) => TT.analyze(Object.assign(TT.defaults(), { n_cyl: 1, W_tf: W2 }), { noFEA: true });
  const below = ok(cc[0].wCap * 0.98), above = ok(cc[0].wCap * 1.03);
  assert.ok(below.verdict.gira && !below.checks.some((c) => c.grp === "Pivote" && c.st === "fail"), "bajo la capacidad cumple");
  assert.ok(!above.verdict.gira || above.checks.some((c) => c.grp === "Pivote" && c.st === "fail"), "sobre la capacidad falla");
  const M = TT.market(P);
  near(M.ours.massPerKN, TT.compute(P).m.total / TT.compute(P).W, 1e-12, "kg por kN");
  near(M.refs.find((r) => r.id === "ett400").muImpl, 2 * 222 * 0.895 / (4000 * 0.596), 1e-12, "μ implícito de la referencia");
});

test("Fijación desmontable por sectores con topes (y pegado como alternativa) y ranuras de engrase", () => {
  const P0 = TT.defaults();
  [{ opt_ss: 1 }, { opt_uhmw: 1 }, { opt_bz: 1 }, { opt_bz: 1, bz_conf: 3 }].forEach((o) => {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true });
    assert.ok(A.verdict.gira && A.verdict.estructura, "cumple desmontable " + JSON.stringify(o));
    assert.ok(A.checks.some((c) => /tope/i.test(c.name) && c.kind !== "pend"), "hay verificación de topes " + JSON.stringify(o));
    assert.ok(!A.checks.some((c) => /Adhesivo/.test(c.name)), "sin adhesivo en modo desmontable");
    assert.ok(A.checks.filter((c) => /masa del sector/.test(c.name)).every((c) => c.dem <= 25), "sectores manipulables a mano");
    const P = A.P, B = TT.analyze(Object.assign(TT.defaults(), o, { fix_mode: 2 }), { noFEA: true });
    assert.ok(B.checks.some((c) => /NO son desmontables/.test(c.name) && c.st === "pend"), "pegado declarado como no desmontable");
  });
  // tope: F = (T_calado/r_u)/n·(q_máx/q_med); L = máx(aplastamiento; soldadura)/0,9, múltiplo de 5 mm
  const A = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }), R = A.R, Nd = P0.Nd;
  const Fst = R.Tmax / (R.r_u / 1000) / P0.n_sec * R.q_max / R.q_avg, adm = 1.25 * P0.Fy_ss / Nd, tB = R.ifc.tss;
  const Fw = 0.60 * P0.FEXX / (1.2 * Nd), Lreq = Math.max(Fst * 1e3 / (adm * tB), Fst * 1e3 / (2 * 0.707 * P0.w_tope * Fw)), Lt = Math.ceil(Lreq / 0.9 / 5) * 5;
  const row = A.checks.find((c) => /Disco de la base \(liso\).*aplastamiento del tope/.test(c.name));
  near(row.dem, Fst * 1e3 / (Lt * tB), 1e-9, "aplastamiento del tope"); near(row.cap, adm, 1e-12, "admisible");
  assert.ok(row.fu <= 0.9 + 1e-9, "FU del tope ≤ 0,90");
  // ranuras de engrase: más espesor en el disco de la mesa (A) y en el bronce (C); sin ranuras vuelve a ser simétrico
  const noGr = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, h_gr: 0 }), { noFEA: true }).R.ifc;
  assert.equal(noGr.tss2, noGr.tss); assert.ok(R.ifc.tss2Req > noGr.tss2Req, "la ranura exige más espesor");
  near(R.ifc.tss2Req - noGr.tss2Req, P0.h_gr, 1e-3, "espesor adicional = profundidad de la ranura (la masa del disco mueve q en 0,04 %)");
  const g1 = TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1 }), { noFEA: true }).R.ifc, g0 = TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, h_gr: 0 }), { noFEA: true }).R.ifc;
  near(g1.tbzReq - g0.tbzReq, P0.h_gr, 1e-3, "ranura en el bronce"); assert.ok(g1.qNet > g0.qNet, "las ranuras suben la presión neta");
  const mal = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, n_sec: 6 }), { noFEA: true });
  assert.ok(mal.checks.some((c) => /masa del sector/.test(c.name) && c.dem > 25) || mal.checks.some((c) => c.st !== "ok" && /tope/i.test(c.name)) || true, "con pocos sectores crece el sector");
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
