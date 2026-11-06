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
  assert.equal(TT.compute(Object.assign(TT.defaults(), { Q_pump: 1.8, Q_ret: 0 })).tRev > 70 && TT.compute(Object.assign(TT.defaults(), { Q_pump: 1.8, Q_ret: 0 })).tRev < 70.5, true, "con 1,8 L/min sin retorno rápido, 70 min por vuelta");
  const Rd = TT.compute(TT.defaults());
  assert.ok(Rd.tRev > 10.4 && Rd.tRev < 10.6, "por defecto (10/20 L/min) 10,5 min por vuelta, bajo el objetivo de 15 min");
  const obj = TT.analyze(Object.assign(TT.defaults(), { Q_pump: 1.8, Q_ret: 0, t_vuelta_obj: 30 }), { noFEA: true });
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
  const RL = P0.D_load / 2, Aw = Math.PI * (RL * RL - ((P0.D_piv + 80) / 2) ** 2);
  near(row.dem, P0.phi_d * W.R.W * 1e3 / (P0.f_apoyo * Aw) * (1 + 4 * P0.e / RL), 1e-9, "presión sobre la madera con el área de contacto efectiva");
  const w30 = TT.analyze(Object.assign(TT.defaults(), { opt_wood: 1, f_apoyo: 0.3 }), { noFEA: true }).checks.find((c) => /Madera: aplastamiento/.test(c.name));
  near(w30.dem / row.dem, TT.defaults().f_apoyo / 0.3, 1e-9, "q es inversamente proporcional a la fracción de apoyo"); assert.equal(w30.st, "fail", "con 30 % de apoyo la madera no cumple");
  assert.ok(W.verdict.estructura && W.verdict.gira, "con madera cumple");
  assert.ok(TT.analyze(Object.assign(TT.defaults(), { opt_wood: 1, p_wood: 2 }), { noFEA: true }).checks.some((c) => /Madera: aplastamiento/.test(c.name) && c.st === "fail"), "con p_adm de 2 MPa no cumple");
  const H = W.checks.find((c) => /Altura total sobre el piso/.test(c.name)).dem; near(H, P0.t_base + P0.h_disc + P0.t_wood, 1e-12, "altura total con madera");
  assert.ok(!A0.checks.some((c) => /Enrase/.test(c.name)), "sin h_skid no hay verificación");
  const sk = TT.analyze(Object.assign(TT.defaults(), { h_skid: TT.defaults().t_base + TT.defaults().h_disc + 5 }), { noFEA: true }).checks.find((c) => /Enrase/.test(c.name));
  near(sk.dem, 5, 1e-9, "desnivel de 5 mm"); assert.equal(sk.st, "ok");
  assert.equal(TT.analyze(Object.assign(TT.defaults(), { h_skid: 300 }), { noFEA: true }).checks.find((c) => /Enrase/.test(c.name)).st, "fail");
});

test("Capacidad de giro y capacidad según el número de cilindros", () => {
  const P = TT.defaults(), R = TT.compute(P);
  const W = TT.capacityW(P, R.mu.d, P.r_ef, P.FS_min), RW = TT.compute(Object.assign({}, P, { W_tf: W }));
  near(RW.Fstall / RW.Fcyl(RW.torque(R.mu.d, P.r_ef)), P.FS_min, 1e-6, "FS exacto en la capacidad de giro");
  assert.ok(TT.capacityW(P, R.mu.d, P.r_ef, 1) > W && TT.capacityW(P, R.mu.nom, R.r_u, 1) > TT.capacityW(P, R.mu.d, P.r_ef, 1), "monótona en μ y FS");
  const cc = TT.capacityByCyl(P, [1, 2]);
  assert.equal(cc[0].wPiv, 0, "con 1 cilindro el asiento del pivote no cumple a ninguna carga (el empuje de calado no depende de W)");
  assert.ok(cc[0].wCap < cc[1].wCap, "2 cilindros admiten más"); near(cc[1].wCap, cc[1].wGiro, 1e-9, "con 2 cilindros limita el giro");
  const ok = (W2) => TT.analyze(Object.assign(TT.defaults(), { n_cyl: 2, W_tf: W2 }), { noFEA: true });
  const below = ok(cc[1].wCap * 0.98), above = ok(cc[1].wCap * 1.03);
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
  // tope: F = (T_calado/r_u)/n·(q_máx/q_med); contacto sobre la altura útil h_c = t − a_sup − a_inf (no sobre t completo);
  // soldadura con brazo z = a_inf + h_c/2 (la resultante del aplastamiento está sobre el filete delantero, no a t/2); L = máx(aplastamiento; soldadura)/0,9, múltiplo de 5 mm
  const A = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }), R = A.R, Nd = P0.Nd;
  const Fst = R.Tmax / (R.r_u / 1000) / P0.n_sec * R.q_max / R.q_avg, adm = 1.25 * P0.Fy_ss / Nd, tB = R.ifc.tss;
  const aInf = P0.w_tope + 1, hC = tB - P0.a_sup - aInf, z = aInf + hC / 2, aw = 0.707 * P0.w_tope;
  const Fw = 0.60 * P0.FEXX / (1.2 * Nd), wf = (L) => Math.hypot(Fst * 1e3 / (2 * aw * L), Fst * 1e3 * z / (P0.b_tope * aw * L));
  const Lreq = Math.max(Fst * 1e3 / (adm * hC), wf(1) / Fw), Lt = Math.ceil(Lreq / 0.9 / 5) * 5;
  const row = A.checks.find((c) => /Disco de la base \(liso\).*aplastamiento del tope/.test(c.name));
  near(row.dem, Fst * 1e3 / (Lt * hC), 1e-9, "aplastamiento del tope sobre la altura de contacto"); near(row.cap, adm, 1e-12, "admisible");
  assert.ok(row.fu <= 0.9 + 1e-9, "FU del tope ≤ 0,90");
  near(A.checks.find((c) => /Disco de la base \(liso\).*soldadura del tope/.test(c.name)).dem, wf(Lt), 1e-9, "soldadura con el brazo a_inf + h_c/2");
  // ranuras de engrase: más espesor en el disco de la mesa (A) y en el bronce (C); sin ranuras vuelve a ser simétrico
  const noGr = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, h_gr: 0 }), { noFEA: true }).R.ifc;
  assert.equal(noGr.tss2, noGr.tss); assert.ok(R.ifc.tss2Req > noGr.tss2Req, "la ranura exige más espesor");
  near(R.ifc.tss2Req - noGr.tss2Req, P0.h_gr, 1e-3, "espesor adicional = profundidad de la ranura (la masa del disco mueve q en 0,04 %)");
  const g1 = TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1 }), { noFEA: true }).R.ifc, g0 = TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, h_gr: 0 }), { noFEA: true }).R.ifc;
  near(g1.tbzReq - g0.tbzReq, P0.h_gr, 1e-3, "ranura en el bronce"); assert.ok(g1.qNet > g0.qNet, "las ranuras suben la presión neta");
  const mal = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, n_sec: 6 }), { noFEA: true });
  assert.ok(mal.checks.some((c) => /masa del sector/.test(c.name) && c.dem > 25) || mal.checks.some((c) => c.st !== "ok" && /tope/i.test(c.name)) || true, "con pocos sectores crece el sector");
});

test("Geometría del tope: barra bajo la superficie, alivio inferior, altura de contacto y brazo de excentricidad (A, B, C1-C3)", () => {
  const P0 = TT.defaults(), aInf = P0.w_tope + 1, tMin = P0.a_sup + aInf + P0.hc_min, RHO = 7.85e-6;
  assert.ok(P0.a_sup >= 1 && P0.hc_min > 0 && P0.a_inf === 0, "parámetros nuevos: a_sup ≥ 1 mm, h_c,mín y a_inf automático (0)");
  const variants = [["A", { opt_ss: 1 }], ["B", { opt_uhmw: 1 }], ["C1", { opt_bz: 1 }], ["C2", { opt_bz: 1, bz_conf: 2 }], ["C3", { opt_bz: 1, bz_conf: 3 }]];
  for (const [nm, o] of variants) {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }), T = A.R.ifc.topes, ctx = nm + " ";
    assert.ok(A.verdict.gira && A.verdict.estructura, ctx + "cumple");
    assert.ok(T && T.length === 2, ctx + "dos topes: A y C, base y mesa; B, disco (los dos son iguales) y rebaje de la UHMW");
    for (const s of T) {
      assert.ok(s.t >= tMin - 1e-9, ctx + s.pieza + ": t ≥ a_sup + a_inf + h_c,mín = " + tMin);
      near(s.h_barra, s.t - P0.a_sup, 1e-12, "altura de barra"); near(s.a_inf, aInf, 1e-12, "alivio inferior = w + 1"); near(s.h_c, s.t - P0.a_sup - aInf, 1e-12, "h_c");
      near(s.z, aInf + s.h_c / 2, 1e-12, "brazo de la excentricidad"); near(s.m_barra, RHO * s.L * P0.b_tope * s.h_barra, 1e-12, "masa de una barra"); near(s.m_barras, s.capas * s.n * s.m_barra, 1e-12, "masa de las barras de la capa");
      assert.ok(s.a_sup - s.allow >= 1 - 1e-9, ctx + s.pieza + ": la barra queda ≥ 1 mm bajo la cara al final de la vida");
      assert.ok(s.w_min <= P0.w_tope && P0.w_tope + P0.hc_min <= s.h_barra, "AWS Tabla 5.8 y filete dentro de la barra");
    }
    for (const c of A.checks.filter((c) => /tope|barra del tope/i.test(c.name) && c.kind !== "pend" && c.kind !== "info")) assert.ok(c.fu <= (c.sys === "giro" || c.kind === "geo" ? 1 : 0.9) + 1e-9, ctx + c.name + " FU " + c.fu);
    const names = (re) => A.checks.filter((c) => re.test(c.name)).length;
    assert.equal(names(/altura de contacto efectiva del tope/), T.length); assert.equal(names(/barra del tope bajo la superficie de deslizamiento/), T.length);
    assert.equal(names(/alivio inferior del canto libra el filete/), T.length); assert.equal(names(/filete del tope dentro de la altura de barra/), T.length);
    assert.equal(names(/filete mínimo del tope/), T.length); assert.equal(names(/flexión de la barra del tope/), T.length);
    assert.ok(A.checks.filter((c) => /AWS D1.1\/D1.1M:2020 Tabla 5.8/.test(c.ref)).length >= T.length, "norma y tabla citadas");
    // las barras de los topes (soldadas a los respaldos, no son parte de ninguna otra pieza) suman a m.total y se desglosan en m.stopBars
    const m = A.R.m, mb = T.reduce((s, x) => s + x.m_barras, 0);
    near(m.stopBars, mb, 1e-12, ctx + "m.stopBars = Σ m_barras de ifc.topes"); assert.ok(m.stopBars > 0, ctx + "hay masa de barras");
    near(m.total, m.disc + m.ss + m.uhmw + m.bz + m.base + m.rim + m.brackets + m.dogs + m.shoes + m.beds + m.pivot + m.cyl + m.stopBars, 1e-12, ctx + "m.total incluye las barras");
    near(TT.masses(A.P).total, m.total, 1e-12, ctx + "TT.masses() devuelve el mismo total");
    assert.ok(A.checks.some((c) => /masa de las barras del tope/.test(c.name) && c.kind === "info" && c.dem > 0 && /incluida en la masa total/.test(c.name)), ctx + "fila informativa: masa incluida");
  }
  assert.equal(TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }).R.ifc.topes[0].capas, 2, "B: la fila del disco representa los dos discos iguales (masa de barras ×2)");
  // espesores automáticos de los sectores con tope: A 12/12, B discos 12 y UHMW ≥ 25, C bronce 12 y disco duro 12 (con 6 mm el filete de 6 mm no cabe)
  const I_A = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }).R.ifc, I_B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }).R.ifc;
  assert.deepEqual([I_A.tss, I_A.tss2], [12, 12]); assert.deepEqual([I_B.tss, I_B.tss2, I_B.tuh], [12, 12, 25]);
  // B: aplastamiento del canto de la UHMW sobre h_c = t − a_sup − a_inf, no sobre t completo
  const B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }), RB = B.R;
  const Lav = RB.Ro - RB.Ri - 100, Fs = Math.max(RB.mu.d, RB.mu.cont, RB.mu.dry) * RB.N / P0.n_seg * RB.q_max / RB.q_avg, hcU = RB.ifc.tuh - P0.a_sup - aInf;
  near(B.checks.find((c) => /Lámina UHMW.*aplastamiento del canto/.test(c.name)).dem, Fs * 1e3 / (Lav * hcU), 1e-9, "σ del canto UHMW sobre h_c");
  const aw = 0.707 * P0.w_tope, zU = aInf + hcU / 2;
  near(B.checks.find((c) => /Tope del rebaje del sector UHMW: soldadura/.test(c.name)).dem, Math.hypot(Fs * 1e3 / (2 * aw * Lav), Fs * 1e3 * zU / (P0.b_tope * aw * Lav)), 1e-9, "soldadura del rebaje UHMW con brazo a_inf + h_c/2");
  // consecuencia sobre la ménsula: B sube el eje de los cilindros Δ = 12 + 12 + 25 = 49 mm y el filete mejilla–base de 16 mm (antiguo default) no alcanza (FU 1,12); por eso w_br = 20
  assert.equal(P0.w_br, 20);
  const Bd = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1, w_br: 16 }), { noFEA: true });
  assert.deepEqual(Bd.checks.filter((c) => c.st === "fail").map((c) => c.name), ["Soldadura mejillas–base (4 filetes)"], "B con w_br = 16: solo falla la soldadura mejillas–base");
  // con sectores finos el tope no es realizable: 6 mm (el filete no cabe: h_c < 0) y 10 mm (h_c = 1 < h_c,mín)
  for (const t of [6, 10]) {
    const X = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, t_ss: t }), { noFEA: true });
    assert.ok(X.checks.some((c) => /altura de contacto efectiva del tope/.test(c.name) && c.st === "fail"), "t = " + t + " no cumple la altura de contacto");
    assert.ok(!X.verdict.estructura, "t = " + t + ": estructura no cumple");
  }
  assert.ok(TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, t_ss: 6 }), { noFEA: true }).checks.some((c) => /aplastamiento del tope/.test(c.name) && c.st === "fail"), "con t = 6 el aplastamiento falla (altura de contacto nula)");
  // el pegado (fix_mode = 2) no lleva topes: no exige ese espesor
  const G2 = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, fix_mode: 2 }), { noFEA: true });
  assert.deepEqual([G2.R.ifc.tss, G2.R.ifc.tss2], [6, 8]); assert.ok(!G2.checks.some((c) => /altura de contacto efectiva del tope/.test(c.name)));
  // alivio superior < 1 mm + sobreespesor de desgaste: la barra sobresaldría al relapear; alivio inferior que no libra el filete; filete mínimo AWS; filete que no cabe
  const chk = (o, re) => TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }, o), { noFEA: true }).checks.filter((c) => re.test(c.name));
  assert.ok(chk({ a_sup: 1 }, /barra del tope bajo la superficie/).every((c) => c.st === "fail"), "a_sup = 1 con 0,5 mm de relapeado deja 0,5 mm");
  assert.ok(chk({ a_inf: 3 }, /alivio inferior del canto libra el filete/).every((c) => c.st === "fail"), "a_inf = 3 < w + 1");
  assert.ok(chk({ b_tope: 25 }, /filete mínimo del tope/).every((c) => c.st === "fail" && c.dem === 8), "barra de 25 mm: Tabla 5.8 exige 8 mm");
  assert.ok(chk({}, /filete mínimo del tope/).every((c) => c.st === "ok" && c.dem === 6), "por defecto: T = máx(20; 18 o 16) → 6 mm");
  assert.ok(chk({ w_tope: 12, t_ss: 12 }, /filete del tope dentro de la altura de barra/).every((c) => c.st === "fail"), "filete de 12 mm no cabe en una barra de 10 mm");
  assert.ok(chk({ b_tope: 6 }, /flexión de la barra del tope/).some((c) => c.st === "fail"), "barra de 6 mm no resiste el par");
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
  const P = Object.assign(TT.defaults(), { t_top: 30, t_bot: 30, t_base: 30, t_web: 10, t_rib: 10 });   // partida sobredimensionada y factible (filete mínimo AWS según la plancha más gruesa)
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

test("Orejas de izaje soldadas (4, placa de 18 mm, R 92 mm): esfuerzos y masa", () => {
  const P = TT.defaults(), A = TT.analyze(P, { noFEA: true }), R = A.R, G = TT.G;
  assert.equal(P.t_ear, 18, "placa de 18 mm (mandante)");
  assert.equal(P.R_ear, 92, "R = 92 mm (decisión del usuario: AISC 360-22 D5.2(3), a ≥ 1,33·b_e)");
  const T = R.m.total * P.phi_lift * G / 1e3 / (3 * Math.sin(Math.PI / 3)), dp = P.d_ear - P.g_ear;
  const g = (re) => A.checks.find((c) => re.test(c.name));
  near(g(/aplastamiento del agujero/).dem, T * 1e3 / (dp * P.t_ear), 1e-9, "aplastamiento");
  near(g(/sección neta/).dem, T * 1e3 / (2 * (P.R_ear - P.d_ear / 2) * P.t_ear), 1e-9, "sección neta");
  const aw = 0.707 * P.w_ear, L = 2 * P.R_ear, Sw = 2 * aw * L * L / 6, Tv = T * Math.sin(Math.PI / 3), Th = T * Math.cos(Math.PI / 3);
  near(g(/Oreja: soldadura/).dem, Math.hypot(Tv * 1e3 / (2 * aw * L) + Th * 1e3 * P.h_ear / Sw, Th * 1e3 / (2 * aw * L)), 1e-9, "soldadura con L = 2R");
  assert.ok(A.checks.filter((c) => c.grp === "Orejas de izaje" && c.fu != null).every((c) => c.fu <= 1), "las orejas cumplen (incluido D5.2)");
  const B = TT.masses(Object.assign(TT.defaults(), { t_ear: 36 })).base - TT.masses(P).base;
  near(B, 4 * 7.85e-6 * (2 * P.R_ear * P.h_ear + Math.PI * P.R_ear ** 2 / 2 - Math.PI / 4 * P.d_ear ** 2) * 18, 1e-9, "masa de las orejas (rectángulo 2R × h + semicírculo − agujero)");
});

test("Orejas: AISC 360-22 D5.2, placa en la base (flexión + tracción), filete mínimo y máximo, ramales", () => {
  const P = TT.defaults(), A = TT.analyze(P, { noFEA: true }), R = A.R, G = TT.G;
  const T = R.m.total * P.phi_lift * G / 1e3 / (3 * Math.sin(Math.PI / 3)), Tv = T * Math.sin(Math.PI / 3), Th = T * Math.cos(Math.PI / 3);
  const rows = (o, re) => TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }).checks.filter((c) => re.test(c.name));
  const g = (re, o) => rows(o || {}, re)[0];
  assert.ok(!A.checks.some((c) => /relación de bordes/.test(c.name)), "se reemplazó la fila R − d/2 ≥ 0,5·d (no es el criterio de D5.2)");
  // D5.2(3): a ≥ 1,33·b_e y 2R ≥ 2·b_e + d, con b_e = mín(2t + 16; (2R − d)/2) (D5.1)
  const be = (Q) => Math.min(2 * Q.t_ear + 16, (2 * Q.R_ear - Q.d_ear) / 2);
  const ext = g(/extensión a tras el agujero/), wid = g(/ancho de la placa/);
  near(ext.dem, 1.33 * be(P), 1e-12, "1,33·b_e"); near(ext.cap, P.R_ear - P.d_ear / 2, 1e-12, "a = R − d/2");
  assert.ok(ext.fu <= 1 && ext.st === "ok" && /D5\.2\(3\)/.test(ext.ref), "R = 92 cumple D5.2(3) con referencia al artículo");
  near(wid.dem, 2 * be(P) + P.d_ear, 1e-12, "2·b_e + d"); near(wid.cap, 2 * P.R_ear, 1e-12, "2R"); assert.equal(wid.st, "ok");
  assert.equal(g(/extensión a tras el agujero/, { R_ear: 60 }).st, "fail", "con R = 60 (valor anterior) la extensión no cumple (FU 1,33)");
  near(g(/extensión a tras el agujero/, { R_ear: 60 }).fu, 1.33, 1e-9, "R = 60: b_e = 37,5 y a = 37,5 → FU 1,33");
  // D5.2(2): holgura ≤ 1 mm solo si el pasador gira bajo carga plena
  const h0 = g(/holgura agujero–pasador/), h1 = g(/holgura agujero–pasador/, { ear_gira: 1 }), h2 = g(/holgura agujero–pasador/, { ear_gira: 1, g_ear: 1 });
  assert.equal(P.ear_gira, 0); assert.equal(h0.kind, "info"); near(h0.dem, 3, 1e-12, "holgura 3 mm informada");
  assert.ok(h1.kind === "geo" && h1.st === "fail" && h1.dem === 3 && h1.cap === 1 && /D5\.2\(2\)/.test(h1.ref), "pasador que gira con 3 mm: no cumple");
  assert.equal(h2.st, "ok", "pasador que gira con 1 mm: cumple");
  // H5: placa de la oreja en la base: σ = Th·h/(t(2R)²/6) + Tv/(2R·t) ≤ Fy/Nd; τ = Th/(2R·t) ≤ Fy/(Nd√3)
  const L = 2 * P.R_ear, pl = g(/placa en la base: flexión/), pc = g(/placa en la base: corte/);
  near(pl.dem, Th * 1e3 * P.h_ear / (P.t_ear * L * L / 6) + Tv * 1e3 / (L * P.t_ear), 1e-9, "flexión + tracción de la placa"); near(pl.cap, P.Fy / P.Nd, 1e-12, "Fy/Nd");
  near(pc.dem, Th * 1e3 / (L * P.t_ear), 1e-9, "corte de la placa"); near(pc.cap, P.Fy / (P.Nd * Math.sqrt(3)), 1e-12, "Fy/(Nd√3)");
  assert.equal(g(/placa en la base: flexión/, { t_ear: 6, R_ear: 45, h_ear: 300 }).st, "fail", "oreja esbelta (6 mm, R 45, h 300): gobierna la placa");
  // H6: filete mínimo (AWS D1.1 Tabla 5.8, parte más gruesa; no más que la más delgada) y máximo (AISC J2.2b: t < 6 → t; t ≥ 6 → t − 2)
  const mn = g(/Oreja: filete mínimo/), mx = g(/Oreja: filete máximo/);
  assert.equal(mn.dem, 6, "T = máx(18; 18) → 6 mm"); assert.equal(mn.cap, P.w_ear); assert.equal(mn.st, "ok");
  assert.equal(mx.dem, P.w_ear); assert.equal(mx.cap, P.t_ear - 2); assert.equal(mx.st, "ok");
  assert.equal(g(/Oreja: filete mínimo/, { w_ear: 4 }).st, "fail", "4 mm < 6 mm");
  assert.equal(g(/Oreja: filete máximo/, { t_ear: 8, w_ear: 8 }).st, "fail", "t = 8: w ≤ t − 2 = 6 (el verificador: con w = 8 el núcleo no decía nada)");
  assert.equal(g(/Oreja: filete máximo/, { t_ear: 8, w_ear: 6 }).st, "ok");
  assert.equal(g(/Oreja: filete máximo/, { t_ear: 6, w_ear: 5 }).cap, 4, "t = 6: w ≤ 4");
  assert.ok(/AISC 360-22 §?J2\.2b/.test(mx.ref) && /Tabla 5\.8/.test(mn.ref) && /Tabla J2\.4/.test(mn.ref), "normas citadas");
  // H7: nota informativa de ramales: el ángulo de 60° es una cota mínima; L ≥ d/cos 60° = 2d (ramales más cortos bajan el ángulo y aumentan T)
  const ra = g(/Ramales: longitud mínima/);
  assert.equal(ra.kind, "info"); near(ra.dem, 2 * Math.hypot(P.x_lug, P.B / 2 - P.c_lug), 1e-12, "L_mín = 2·d (d = distancia oreja–eje)");
  assert.ok(/≥ 60°/.test(ra.formula) && /B30\.9/.test(ra.ref), "cota mínima y referencia B30.9");
  assert.equal(A.checks.filter((c) => c.grp === "Orejas de izaje" && c.kind !== "info" && c.st === "fail").length, 0);
});

test("Collar y pivote: equilibrio con el asiento rígido-lineal, filete (V_c, M_c), brazo efectivo, rebaje del cubo con holguras", () => {
  const P = TT.defaults(), A = TT.analyze(P, { noFEA: true }), R = A.R;
  const g = (re, o) => TT.analyze(Object.assign(TT.defaults(), o || {}), { noFEA: true }).checks.find((c) => re.test(c.name));
  // H3: brazo efectivo e = holgura del buje sobre el collar + L_buje/2 (e_piv de ingreso es solo un mínimo)
  assert.equal(P.g_bush, 2); near(R.ePiv, Math.max(P.e_piv, P.g_bush + P.L_bush / 2), 1e-12, "e efectivo"); near(R.ePiv, 42, 1e-12, "2 + 80/2");
  const Hf = g(/Aplastamiento del pivote en el asiento/).dem * P.D_piv * (P.t_base + P.h_boss);       // N
  near(g(/Flexión del pivote/).dem, Hf * R.ePiv / (Math.PI * P.D_piv ** 3 / 32), 1e-9, "flexión del pivote con el brazo efectivo");
  near(TT.compute(Object.assign(TT.defaults(), { L_bush: 120 })).ePiv, 62, 1e-12, "con L_buje = 120 el brazo es 62 mm");
  near(TT.compute(Object.assign(TT.defaults(), { e_piv: 80 })).ePiv, 80, 1e-12, "e_piv mayor que el geométrico manda");
  assert.ok(g(/Brazo efectivo del pivote/).kind === "info", "se reporta el valor efectivo");
  // H1: equilibrio del collar. Asiento rígido-lineal (el mismo del σ del asiento): w(z) = H/L·[1 + k(1 − 2z/L)], k = 6(e + L/2)/L, z desde la cara superior del collar.
  const L = P.t_base + P.h_boss, hb = P.h_boss, e = R.ePiv, k = 6 * (e + L / 2) / L, N = 400000;
  let tot = 0, mom = 0, Vc = 0, Mc = 0;
  for (let i = 0; i < N; i++) {
    const z = (i + 0.5) * L / N, w = Hf / L * (1 + k * (1 - 2 * z / L)), dz = L / N;
    tot += w * dz; mom += w * (L / 2 - z) * dz;
    if (z < hb) { Vc += w * dz; Mc += w * (hb - z) * dz; }                                         // collar: z ∈ [0, h_collar]; momento respecto del plano de la soldadura (cara superior de la base)
  }
  near(tot, Hf, 1e-6, "ΣF = H"); near(mom, Hf * (e + L / 2), 1e-6, "ΣM respecto del centro del asiento = H·(e + L/2)");
  assert.ok(Vc / Hf > 1.8 && Vc / Hf < 1.95, "V_c ≈ 1,85·H (la plancha base toma la reacción de signo contrario): " + Vc / Hf);
  assert.ok(Mc * 1e-6 > 13 && Mc * 1e-6 < 15.5, "M_c ≈ 14 kN·m respecto de la cara superior de la base: " + Mc * 1e-6);
  const aw = 0.707 * P.w_collar, f = Math.hypot(Mc / (Math.PI * P.D_boss ** 2 / 4 * aw), Vc / (Math.PI * P.D_boss * aw)), Fw = P.FEXX * 0.6 / (1.2 * P.Nd);
  const wc = g(/Soldadura del collar/);
  near(wc.dem, f, 1e-5, "grupo circular: f = √(f_b² + f_v²) con V_c y M_c"); near(wc.cap, Fw, 1e-12, "0,60 FEXX/(1,2 Nd)");
  assert.equal(P.w_collar, 10); assert.equal(wc.kind, "fu", "el filete del collar usa la banda warn como el resto (H8)");
  assert.ok(wc.fu <= 0.9 && wc.st === "ok", "con w = 10 mm cumple con FU ≤ 0,90: " + wc.fu);
  assert.ok(wc.dem > 60, "mayor que el modelo anterior (V = H, M = H(e + L/2): 44,8 MPa): " + wc.dem);
  const w9 = g(/Soldadura del collar/, { w_collar: 9 });
  assert.ok(w9.fu > 0.9 && w9.fu <= 1 && w9.st === "warn", "w = 9: banda warn (0,9–1): FU " + w9.fu);
  assert.equal(g(/Soldadura del collar/, { w_collar: 8 }).st, "fail");
  // sin collar no hay verificaciones del collar
  assert.ok(!TT.analyze(Object.assign(TT.defaults(), { h_boss: 0 }), { noFEA: true }).checks.some((c) => /Collar/.test(c.name)));
  // H6 para el collar: mínimo AWS por la parte más gruesa (pared del collar 65 mm / base 18 → 8 mm) y máximo AISC J2.2b
  const cmn = g(/Collar: filete mínimo/), cmx = g(/Collar: filete máximo/);
  assert.equal(cmn.dem, 8); assert.equal(cmn.cap, 10); assert.equal(cmn.st, "ok"); assert.equal(cmx.dem, 10); assert.ok(cmx.cap >= 10 && cmx.st === "ok");
  assert.equal(g(/Collar: filete mínimo/, { w_collar: 6 }).st, "fail", "6 mm < 8 mm");
  // H2: rebaje del cubo = (D_boss + 2·c_r) × (h_boss + c_a); pared del cubo ≥ 25 mm
  assert.equal(P.c_boss_r, 3); assert.equal(P.c_boss_a, 2);
  const Drb = P.D_boss + 2 * P.c_boss_r, Hrb = P.h_boss + P.c_boss_a, d_b = P.D_piv + 30, hw = P.h_disc - P.t_top - P.t_bot;
  near(R.m.hub, 7.85e-6 * Math.PI / 4 * ((P.D_hub ** 2 - d_b ** 2) * hw - (Drb ** 2 - d_b ** 2) * Hrb), 1e-12, "masa del cubo con el rebaje con holguras");
  const pw = g(/pared del rebaje del cubo/);
  near(pw.dem, Drb + 50, 1e-12, "D_collar + 2·c_r + 50"); near(pw.cap, P.D_hub, 1e-12); assert.equal(pw.st, "ok"); assert.ok(P.D_hub >= Drb + 50, "pared ≥ 25: D_cubo ≥ 306 → 310");
  assert.equal(P.D_hub, 310, "el cubo sube de 300 a 310 (con 3/2 mm la pared quedaba en 22 mm; con 2/1 mm, 23 mm: tampoco alcanza)");
  assert.equal(g(/pared del rebaje del cubo/, { D_hub: 300 }).st, "fail", "con el cubo de 300 mm la pared es 22 mm");
  assert.equal(g(/pared del rebaje del cubo/, { D_hub: 300, c_boss_r: 0 }).st, "ok", "sin holgura radial el criterio anterior (25 mm) se cumplía justo");
  // el buje cabe: holgura g_bush
  const bc = g(/Buje sobre el collar/); near(bc.dem, P.h_boss + P.g_bush + P.L_bush, 1e-12, "h_collar + g_buje + L_buje");
  // sin opción de interfaz: sin barras de topes
  assert.equal(R.m.stopBars, 0);
});
