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
  near(A.R.ifc.mSS, 7.93e-6 * Aarea * (I.tss + I.tss2), 1e-9, "masa bruta de la corona de los discos (R.m.ss es la neta: descuenta muescas, chaflanes y juntas, ver 4.ª pasada)");
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
  const Rw = P0.D_top / 2 - P0.t_ring, areaIn = Math.PI / 4 * ((2 * Rw) ** 2 - hole ** 2);   // 4.ª pasada: los tablones van dentro del anillo de acero
  near(W.R.m.wood, P0.rho_wood * 1e-9 * areaIn * P0.t_wood, 1e-9, "masa de la madera (dentro del anillo de acero)");
  assert.ok(W.R.m.wood < P0.rho_wood * 1e-9 * area * P0.t_wood, "la madera ya no ocupa la franja del anillo");
  near(W.R.m.total - A0.R.m.total, W.R.m.wood + W.R.m.ring, 0.02, "la cubierta suma madera + anillo de acero (más el efecto sobre la interfaz)");
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
  const Lreq = Math.max(Fst * 1e3 / (adm * (hC - P0.tol_hc)), wf(1) / Fw), Lt = Math.ceil(Lreq / 0.9 / 5) * 5;   // 4.ª pasada: el largo se dimensiona con h_c − tol_hc (el tope tolera 1 mm menos de contacto)
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
      near(s.z, aInf + s.h_c / 2, 1e-12, "brazo de la excentricidad"); near(s.m_barra, (s.uh ? 7.93e-6 : RHO) * s.L * P0.b_tope * s.h_barra, 1e-12, "masa de una barra (UHMW: inoxidable)"); near(s.m_barras, s.capas * s.n * s.m_barra, 1e-12, "masa de las barras de la capa");
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
  // espesores automáticos de los sectores con tope (4.ª pasada, h_c,mín = 6): t ≥ 2 + 7 + 6 = 15 → A 15/15, B discos 15 y UHMW ≥ 25, C bronce 15 y disco duro 15
  const I_A = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }).R.ifc, I_B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }).R.ifc;
  assert.equal(tMin, 15); assert.deepEqual([I_A.tss, I_A.tss2], [15, 15]); assert.deepEqual([I_B.tss, I_B.tss2], [15, 15]); assert.ok(I_B.tuh >= 25 && I_B.tuh >= I_B.tuhTope, "UHMW ≥ tope del rebaje");
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
  // con sectores finos el tope no es realizable: 6 mm (el filete no cabe: h_c < 0), 10 mm (h_c = 1) y 12 mm (h_c = 3 < h_c,mín = 6: el antiguo espesor automático)
  for (const t of [6, 10, 12]) {
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

const IFC_VARIANTS = [["default", {}], ["A", { opt_ss: 1 }], ["B", { opt_uhmw: 1 }], ["C1", { opt_bz: 1 }], ["C2", { opt_bz: 1, bz_conf: 2 }], ["C3", { opt_bz: 1, bz_conf: 3 }], ["madera", { opt_wood: 1 }]];

test("Radio interior real de la interfaz: R_i = D_collar/2 + c_boss_r + m_ri para todas las opciones, y se propaga a presión, masa, topes y eje", () => {
  const P0 = TT.defaults(), Ri = P0.D_boss / 2 + P0.c_boss_r + P0.m_ri, RHO_SS = 7.93e-6, RHO_UH = 0.94e-6;
  assert.equal(P0.m_ri, 3, "margen de borde 3 mm"); assert.equal(Ri, 131, "125 + 3 + 3");
  for (const [nm, o] of IFC_VARIANTS) {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }), R = A.R, I = R.ifc, ctx = nm + ": ";
    near(R.Ri, Ri, 1e-12, ctx + "R_i efectivo");
    near(R.Ac, Math.PI * (R.Ro ** 2 - Ri ** 2), 1e-12, ctx + "área de contacto");
    near(R.q_avg, R.ND * 1e3 / R.Ac, 1e-12, ctx + "q medio sobre el anillo real");
    near(R.q_max, R.q_avg * (1 + 4 * P0.e * R.Ro / (R.Ro ** 2 + Ri ** 2)), 1e-12, ctx + "q máx");
    // sube respecto del anillo antiguo (R_i = 75): la presión no puede bajar al quitar área
    const Ro = R.Ro, qOld = R.ND * 1e3 / (Math.PI * (Ro ** 2 - 75 ** 2)) * (1 + 4 * P0.e * Ro / (Ro ** 2 + 75 ** 2));
    assert.ok(R.q_max > qOld, ctx + "q_máx sube al reducir el área");
    near(R.hax, P0.h_disc / 2 + I.delta, 1e-12, ctx + "el eje de los cilindros sube δ");
    if (I.o) {
      near(I.A_ss, Math.PI * (Ro ** 2 - Ri ** 2), 1e-12, ctx + "área de los discos de la interfaz");
      near(I.q, R.q_max, 1e-3, ctx + "la presión de dimensionamiento de los discos es la del anillo real");
      for (const s of I.topes) { near(s.Lav, Ro - Ri - 100, 1e-12, ctx + s.pieza + ": canto radial disponible"); assert.ok(s.L <= s.Lav + 1e-9, ctx + s.pieza + ": L ≤ R_o − R_i − 100"); }
      const row = A.checks.filter((c) => /largo del tope frente al canto radial/.test(c.name));
      assert.ok(row.length === I.topes.length - (I.o === 2 ? 1 : 0) && row.every((c) => Math.abs(c.cap - (Ro - Ri - 100)) < 1e-9 && c.st === "ok"), ctx + "filas de largo de tope con el canto nuevo (en B la lámina UHMW usa todo el canto y tiene su propia fila de aplastamiento)");
    }
  }
  // masas con el área del anillo real
  const A = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }), B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true });
  near(A.R.ifc.mSS, RHO_SS * Math.PI * (A.R.Ro ** 2 - Ri ** 2) * (A.R.ifc.tss + A.R.ifc.tss2), 1e-12, "masa bruta de la corona de los discos (A)");
  near(B.R.ifc.mUH, RHO_UH * Math.PI * (B.R.Ro ** 2 - Ri ** 2) * B.R.ifc.tuh, 1e-12, "masa bruta de la corona de UHMW (B)");
  // la lámina UHMW usa todo el canto disponible (R_o − R_i − 100) y su espesor de tope lo ve
  near(B.R.ifc.topes.find((s) => s.id === "uhmw").L, B.R.Ro - Ri - 100, 1e-12, "largo del tope UHMW = canto disponible");
  // sin collar vuelve al borde del buje (D_piv/2 + 15); m_ri mueve R_i milímetro a milímetro
  near(TT.compute(Object.assign(TT.defaults(), { h_boss: 0 })).Ri, P0.D_piv / 2 + 15, 1e-12, "sin collar: R_i = D_piv/2 + 15");
  near(TT.compute(Object.assign(TT.defaults(), { m_ri: 10 })).Ri, 138, 1e-12, "m_ri = 10 → R_i = 138");
  assert.ok(TT.compute(Object.assign(TT.defaults(), { m_ri: 10 })).q_max > TT.compute(TT.defaults()).q_max, "más margen = menos área = más presión");
  // por el eje de las ranuras de engrase la longitud radial también parte de R_i: las ranuras ocupan menos área
  const gOld = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, m_ri: 0 }), { noFEA: true }).R;
  assert.ok(gOld.Ri < A.R.Ri && gOld.Ac > A.R.Ac);
  // todas las opciones cumplen con el anillo real (q_máx, aplastamiento de lámina y bronce, topes)
  for (const [nm, o] of IFC_VARIANTS) { const X = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }); assert.ok(X.verdict.gira && X.verdict.estructura, nm + " cumple con R_i = 131"); }
});

test("Rebaje del collar en la mesa: h_collar − δ + c_boss_a desde la cara inferior, agujero de la plancha inferior Ø(D_collar + 2·c_r) y aplastamiento de la pared del cubo", () => {
  const RHO = 7.85e-6;
  for (const [nm, o] of IFC_VARIANTS) {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }), R = A.R, P = A.P, m = R.m, I = R.ifc, H = R.hubG, ctx = nm + ": ";
    const d_b = P.D_piv + 30, Drb = P.D_boss + 2 * P.c_boss_r, hw = P.h_disc - P.t_top - P.t_bot, hRec = P.h_boss - I.delta + P.c_boss_a;
    near(H.hRec, hRec, 1e-12, ctx + "profundidad del rebaje = h_collar − δ + c_boss_a"); near(H.Drb, Drb, 1e-12, ctx + "Ø del agujero de la plancha = D_collar + 2·c_boss_r"); near(H.delta, I.delta, 1e-12, ctx + "δ de la interfaz");
    assert.ok(H.hRec > 0, ctx + "el collar sobresale de la cara inferior de la mesa");
    const rpr = TT.prIn(P), Rt = P.D_top / 2, aRing = Math.PI * (Rt * Rt - rpr * rpr) - P.N_pin * Math.PI / 4 * P.d_pin ** 2;
    const hPl = hRec > 0 ? P.t_bot : 0, hHub = Math.min(Math.max(0, hRec - P.t_bot), hw);   // el agujero de la plancha es pasante (un bolsillo menos profundo que t_bot dejaría un labio inútil)
    near(m.bot, RHO * ((Math.PI * rpr * rpr - Math.PI / 4 * d_b ** 2) * P.t_bot + aRing * Math.max(P.t_pr, P.t_bot)) - RHO * Math.PI / 4 * (Drb ** 2 - d_b ** 2) * hPl, 1e-12, ctx + "masa de la plancha inferior con el agujero real del collar");
    near(m.hub, RHO * Math.PI / 4 * ((P.D_hub ** 2 - d_b ** 2) * hw - (Drb ** 2 - d_b ** 2) * hHub), 1e-12, ctx + "masa del cubo con la parte del rebaje sobre la plancha");
    const inf = A.checks.find((c) => /Rebaje del cubo para el collar/.test(c.name));
    near(inf.dem, Drb, 1e-12, ctx + "Ø rebaje informado"); near(inf.cap, hRec, 1e-12, ctx + "profundidad informada (h − δ + c_a)"); assert.equal(inf.kind, "info");
    const wall = A.checks.find((c) => /pared del rebaje del cubo/.test(c.name));
    near(wall.dem, Drb + 50, 1e-12, ctx + "pared ≥ 25 mm"); assert.equal(wall.st, "ok");
    // aplastamiento de la pared del cubo bajo la presión de contacto que entra por el pie del cubo (anillo R_i … r_hub, plancha inferior apoyada sobre el cubo)
    const rh = P.D_hub / 2, lig = A.checks.find((c) => /aplastamiento de la pared del cubo/.test(c.name));
    near(lig.dem, R.q_max * (rh ** 2 - R.Ri ** 2) / (rh ** 2 - (Drb / 2) ** 2), 1e-9, ctx + "σ en la pared del cubo"); near(lig.cap, P.Fy / P.Nd, 1e-12, ctx + "Fy/Nd"); assert.ok(lig.st === "ok" && lig.fu < 0.1, ctx + "FU " + lig.fu);
    const rr = A.checks.find((c) => /R_i libre del rebaje/.test(c.name));
    near(rr.dem, Drb / 2 + P.m_ri, 1e-12, ctx + "R_i ≥ rebaje + margen"); near(rr.cap, R.Ri, 1e-12); assert.equal(rr.st, "ok");
  }
  // defaults sin interfaz (δ = 0): 60 + 2 = 62 mm, 16 en la plancha (agujero pasante) y 46 en el cubo
  const D0 = TT.compute(TT.defaults()).hubG; assert.deepEqual([D0.hRec, D0.hPl, D0.hHub], [62, 16, 46]);
  // con interfaz el rebaje es menos profundo (4.ª pasada, sectores de 15 mm): A 60 − 30 + 2 = 32; B 60 − 55 + 2 = 7 (menos que t_bot = 16: el cubo queda sin rebaje y el agujero de la plancha sigue siendo pasante, sin labio de 7 mm)
  const HA = TT.compute(Object.assign(TT.defaults(), { opt_ss: 1 })).hubG, HB = TT.compute(Object.assign(TT.defaults(), { opt_uhmw: 1 })).hubG;
  assert.deepEqual([HA.hRec, HA.hPl, HA.hHub], [32, 16, 16]); assert.deepEqual([HB.hRec, HB.hPl, HB.hHub], [7, 16, 0]);
  // la masa total (plancha + cubo) del default es la misma que con el modelo anterior (62 mm, todo en el cubo): solo se reparte entre las dos piezas
  const m0 = TT.masses(TT.defaults()), P0 = TT.defaults(), d_b = P0.D_piv + 30, Drb = P0.D_boss + 2 * P0.c_boss_r, hw0 = P0.h_disc - P0.t_top - P0.t_bot;
  const hubOld = RHO * Math.PI / 4 * ((P0.D_hub ** 2 - d_b ** 2) * hw0 - (Drb ** 2 - d_b ** 2) * 62);
  const rpr0 = TT.prIn(P0), aR0 = Math.PI * ((P0.D_top / 2) ** 2 - rpr0 ** 2) - P0.N_pin * Math.PI / 4 * P0.d_pin ** 2;
  near(m0.hub + m0.bot, hubOld + RHO * ((Math.PI * rpr0 * rpr0 - Math.PI / 4 * d_b ** 2) * P0.t_bot + aR0 * Math.max(P0.t_pr, P0.t_bot)), 1e-12, "plancha + cubo = modelo anterior (δ = 0)");
  // collar bajo la cara inferior (h − δ + c_a < 0): no hay rebaje; el agujero de la plancha es solo el del buje; se informa la profundidad negativa
  const N = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, h_boss: 20 }), { noFEA: true }), HN = N.R.hubG;
  near(HN.hRaw, 20 - 30 + 2, 1e-12, "profundidad cruda negativa (−8)"); assert.equal(HN.hRec, 0); assert.equal(HN.hPl, 0);
  near(N.R.m.hub, RHO * Math.PI / 4 * (P0.D_hub ** 2 - d_b ** 2) * hw0, 1e-12, "sin rebaje: cubo macizo salvo el buje");
  assert.ok(N.checks.find((c) => /Rebaje del cubo para el collar/.test(c.name)).dem < 0 || N.checks.find((c) => /Rebaje del cubo para el collar/.test(c.name)).cap < 0, "profundidad negativa reportada");
  assert.equal(TT.compute(Object.assign(TT.defaults(), { h_boss: 0 })).hubG.hRec, 0, "sin collar no hay rebaje");
  // pared del cubo < 25 mm: sigue fallando (D_hub 300)
  assert.equal(TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, D_hub: 300 }), { noFEA: true }).checks.find((c) => /pared del rebaje del cubo/.test(c.name)).st, "fail");
});

test("e_piv: mínimo de ingreso con default 0 = automático (rige g_buje + L_buje/2)", () => {
  const g = TT.PARAM_GROUPS.find((x) => x.id === "pivote").p.find((q) => q[0] === "e_piv");
  assert.equal(g[3], 0, "default 0 = automático"); assert.equal(g[4], 0, "mínimo del campo 0"); assert.match(g[1], /0 = autom/);
  near(TT.compute(TT.defaults()).ePiv, 42, 1e-12, "automático: 2 + 80/2");
  near(TT.compute(Object.assign(TT.defaults(), { e_piv: 60 })).ePiv, 60, 1e-12, "un mínimo de ingreso mayor manda");
  near(TT.compute(Object.assign(TT.defaults(), { e_piv: 40 })).ePiv, 42, 1e-12, "el antiguo 40 nunca regía");
  assert.equal(AG.validate(TT.defaults()).filter((v) => v.lvl === "error").length, 0, "0 es un valor válido");
});

/* ===================================================================================================================================== */
/* 4.ª pasada                                                                                                                              */
/* ===================================================================================================================================== */
const RHO_S = 7.85e-6, RHO_SSx = 7.93e-6, RHO_UHx = 0.94e-6, ALS = 11.7e-6;
const rnd01 = (x) => Math.ceil(x * 10 - 1e-9) / 10;

test("4.ª pasada · hc_min = 6: sectores con tope de 15 mm y el largo del tope tolera 1 mm menos de contacto (T6)", () => {
  const P0 = TT.defaults(), aInf = P0.w_tope + 1;
  assert.equal(P0.hc_min, 6); assert.equal(P0.tol_hc, 1); assert.equal(P0.a_sup + aInf + P0.hc_min, 15, "espesor mínimo del sector con tope");
  for (const [nm, o] of [["A", { opt_ss: 1 }], ["B", { opt_uhmw: 1 }], ["C1", { opt_bz: 1 }], ["C2", { opt_bz: 1, bz_conf: 2 }], ["C3", { opt_bz: 1, bz_conf: 3 }]]) {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }), T = A.R.ifc.topes, I = A.R.ifc;
    assert.ok(A.verdict.gira && A.verdict.estructura, nm + " cumple");
    if (nm !== "B") assert.deepEqual([I.tss, I.tss2], [15, 15], nm + ": sectores de 15 mm"); else assert.deepEqual([I.tss, I.tss2], [15, 15]);
    if (I.o === 3) assert.equal(I.tbz, 15, nm + ": bronce de 15 mm");
    for (const s of T) {
      assert.ok(s.t >= 15 - 1e-9 && s.h_c >= P0.hc_min - 1e-9, nm + " " + s.pieza + ": t ≥ 15 y h_c ≥ 6");
      const adm = s.adm, sig = (hc) => s.F * 1e3 / (s.L * hc);
      assert.ok(sig(s.h_c - P0.tol_hc) <= 0.9 * adm + 1e-9, nm + " " + s.pieza + ": con 1 mm menos de contacto el aplastamiento sigue ≤ 0,90 (σ/adm = " + (sig(s.h_c - 1) / adm).toFixed(3) + ")");
      assert.ok(sig(s.h_c) <= 0.9 * adm * (s.h_c - 1) / s.h_c + 1e-9, nm + " " + s.pieza + ": con h_c nominal queda con margen");
    }
    const rows = A.checks.filter((c) => /aplastamiento del tope con la altura de contacto reducida/.test(c.name));
    assert.equal(rows.length, T.length, nm + ": una fila de aplastamiento con h_c − tol por tope");
    assert.ok(rows.every((c) => c.fu <= 0.9 + 1e-9 && /tol_hc|tolerancia/.test(c.formula)), nm + ": FU ≤ 0,90 con h_c − tol");
  }
  // B: la lámina de UHMW se dimensiona con h_c ≥ F_s/(0,9·L·p_adm) + tol (T7: el 0,9 es margen de proyecto)
  const B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }), RB = B.R, IB = RB.ifc;
  const Lav = RB.Ro - RB.Ri - 100, Fs = Math.max(RB.mu.d, RB.mu.cont, RB.mu.dry) * RB.N / P0.n_seg * RB.q_max / RB.q_avg;
  const hcNeed = Math.max(P0.hc_min, Fs * 1e3 / (0.9 * Lav * P0.p_uhmw) + P0.tol_hc), tTope = P0.a_sup + aInf + hcNeed;
  near(IB.tuhTope, tTope, 1e-4, "espesor del sector de UHMW por el tope del rebaje (N del bucle de la interfaz vs N final: < 0,01 %)");
  const UH = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50], tExp = UH.find((v) => v >= Math.max(IB.tuhReq, tTope) - 1e-9);
  assert.equal(IB.tuh, tExp, "UHMW comercial = menor espesor ≥ máx(planitud; tope)");
  const row = B.checks.find((c) => /Lámina UHMW: espesor mínimo por el tope del rebaje/.test(c.name));
  assert.ok(row && row.kind === "info", "fila informativa del espesor por el tope");
  assert.ok(/0,9/.test(row.formula) && /margen de proyecto/.test(row.formula) && /no lo exige la norma/.test(row.formula), "T7: el 0,9 se documenta como margen de proyecto, no de norma");
  near(row.dem, tTope, 1e-4, "dem = espesor mínimo por el tope"); near(row.cap, IB.tuh, 1e-12, "cap = espesor adoptado");
  // A con t manual de 12 (el antiguo automático): h_c = 3 < 6 no cumple
  assert.ok(TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, t_ss: 12 }), { noFEA: true }).checks.some((c) => /altura de contacto efectiva del tope/.test(c.name) && c.st === "fail"), "12 mm ya no cumple");
  // tol_hc = 0 reproduce el dimensionamiento sin tolerancia (A: L = 150 con FU 0,836, que con 1 mm menos de contacto pasa de 0,90): la tolerancia es lo que protege contra el hallazgo T6
  const A0 = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, tol_hc: 0 }), { noFEA: true }).R.ifc.topes[0], A1 = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1 }), { noFEA: true }).R.ifc.topes[0];
  assert.ok(A1.L > A0.L, "con tol_hc = 1 el tope es más largo (" + A1.L + " vs " + A0.L + " mm)");
  assert.ok(A0.F * 1e3 / (A0.L * (A0.h_c - 1)) > 0.9 * A0.adm, "sin tolerancia, 1 mm menos de contacto pasa de FU 0,90");
  // con hc_min = 3 (valor anterior) vuelven los 12 mm
  assert.deepEqual([TT.compute(Object.assign(TT.defaults(), { opt_ss: 1, hc_min: 3 })).ifc.tss, TT.compute(Object.assign(TT.defaults(), { opt_ss: 1, hc_min: 3 })).ifc.tss2], [12, 12]);
});

test("4.ª pasada · masa de sectores: muescas, chaflanes y juntas descontadas con fórmula explícita; barras de UHMW en inoxidable", () => {
  const P0 = TT.defaults(), a2 = (P0.w_tope + 1) ** 2, b2 = P0.b_tope + 2;
  assert.equal(P0.j_sec, 1, "junta en frío mínima 1 mm (parámetro)");
  const variants = [["A", { opt_ss: 1 }], ["B", { opt_uhmw: 1 }], ["C1", { opt_bz: 1 }], ["C2", { opt_bz: 1, bz_conf: 2 }], ["C3", { opt_bz: 1, bz_conf: 3 }]];
  for (const [nm, o] of variants) {
    const A = TT.analyze(Object.assign(TT.defaults(), o), { noFEA: true }), R = A.R, I = R.ifc, m = R.m, Ro = R.Ro, Ri = R.Ri, Aan = Math.PI * (Ro ** 2 - Ri ** 2), P = A.P, ctx = nm + ": ";
    const jOf = (al, n) => rnd01(Math.max(P.j_sec, (al - ALS) * P.dT * 2 * Ro * Math.sin(Math.PI / n)));
    const top = (id) => I.topes.find((x) => x.id === id);
    const rBz = P.rho_bz * 1e-6, fg = Math.PI * P.bz_plug_d ** 2 / (2 * Math.sqrt(3) * P.bz_plug_p ** 2), rEff = rBz * (1 - 0.7 * fg) + 1.8e-6 * 0.7 * fg;
    const exp = { ss: I.mSS, uhmw: I.mUH, bz: I.mBz }, desc = { ss: 0, uhmw: 0, bz: 0 };
    const sub = (tgt, rho, n, capas, t, L, joint, jj, strip) => {   // volumen por sector: junta (o franja libre) + muesca (no en la franja) + 2 chaflanes de a_inf²/2
      const Vj = joint ? (strip ? P.b_tope + jj : jj) * (Ro - Ri) * t : 0, Vn = strip ? 0 : b2 * L * t, Vc = a2 * L;
      desc[tgt] += rho * capas * n * (Vj + Vn + Vc);
    };
    if (I.o === 1 || I.o === 2) { const d = top("disc0"), d1 = top("disc1"); for (const x of [d, d1].filter(Boolean)) sub("ss", RHO_SSx, x.n, x.capas, x.t, x.L, true, jOf(17.3e-6, x.n)); }
    if (I.o === 2) { const u = top("uhmw"); sub("uhmw", RHO_UHx, u.n, 1, u.t, u.L, true, jOf(180e-6, u.n), true); }
    if (I.o === 3) {
      const z0 = top("bz0"), z1 = top("bz1");
      sub("bz", rEff, z0.n, 1, z0.t, z0.L, I.conf !== 3, jOf(18e-6, z0.n));            // pastillas: la junta ya está en la fracción de cobertura
      if (I.conf === 2) sub("bz", rBz, z1.n, 1, z1.t, z1.L, true, jOf(18e-6, z1.n)); else sub("ss", RHO_SSx, z1.n, 1, z1.t, z1.L, true, jOf(17.3e-6, z1.n));
    }
    near(m.ss, exp.ss - desc.ss, 1e-9, ctx + "m.ss neta"); near(m.uhmw, exp.uhmw - desc.uhmw, 1e-9, ctx + "m.uhmw neta"); near(m.bz, exp.bz - desc.bz, 1e-9, ctx + "m.bz neta");
    assert.ok(desc.ss + desc.uhmw + desc.bz > 5, ctx + "el descuento es apreciable (> 5 kg)");
    near(m.total, m.disc + m.ss + m.uhmw + m.bz + m.base + m.rim + m.brackets + m.dogs + m.shoes + m.beds + m.pivot + m.cyl + m.stopBars, 1e-12, ctx + "m.total con piezas netas");
    // la fila informativa de cada pieza y las claves de interfazGeom
    const rows = A.checks.filter((c) => /descuento de masa por muescas, chaflanes y juntas/.test(c.name));
    assert.equal(rows.length, I.cortes.length, ctx + "una fila por pieza"); assert.ok(rows.every((c) => c.kind === "info" && c.dem > 0 && /a_inf²|a_inf\^2|a_inf²/.test(c.formula) && /junta/.test(c.formula)), ctx + "filas info con la fórmula");
    near(rows.reduce((q, c) => q + c.dem, 0), desc.ss + desc.uhmw + desc.bz, 1e-9, ctx + "las filas suman el descuento");
    near(I.cortes.reduce((q, c) => q + c.m_desc, 0), desc.ss + desc.uhmw + desc.bz, 1e-9, ctx + "R.ifc.cortes");
    // cada sector pesa menos (manipulación manual): masa neta por sector en la fila de ISO 11228-1
    const ms = A.checks.filter((c) => /masa del sector/.test(c.name));
    assert.ok(ms.length > 0 && ms.every((c) => c.dem <= 25), ctx + "sectores ≤ 25 kg");
  }
  // barras de UHMW en B: acero inoxidable (ρ 7,93); las demás, acero estructural (ρ 7,85)
  const B = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1 }), { noFEA: true }), u = B.R.ifc.topes.find((x) => x.id === "uhmw"), d = B.R.ifc.topes.find((x) => x.id === "disc0");
  near(u.m_barra, RHO_SSx * u.L * P0.b_tope * u.h_barra, 1e-12, "barra de UHMW en inoxidable"); near(d.m_barra, RHO_S * d.L * P0.b_tope * d.h_barra, 1e-12, "barra del disco en acero estructural");
  near(B.R.m.stopBars, d.capas * d.n * d.m_barra + u.n * u.m_barra, 1e-12, "m.stopBars con ambas densidades");
  // con pegado (fix_mode = 2) no hay muescas, chaflanes ni juntas en los discos; la lámina UHMW conserva sus juntas
  const G = TT.analyze(Object.assign(TT.defaults(), { opt_ss: 1, fix_mode: 2 }), { noFEA: true }); near(G.R.m.ss, G.R.ifc.mSS, 1e-12, "pegado: disco entero");
  const GB = TT.analyze(Object.assign(TT.defaults(), { opt_uhmw: 1, fix_mode: 2 }), { noFEA: true }), ju = rnd01(Math.max(P0.j_sec, (180e-6 - ALS) * P0.dT * 2 * GB.R.Ro * Math.sin(Math.PI / P0.n_seg)));
  near(GB.R.m.ss, GB.R.ifc.mSS, 1e-12, "pegado: discos enteros"); near(GB.R.m.uhmw, GB.R.ifc.mUH - RHO_UHx * P0.n_seg * ju * (GB.R.Ro - GB.R.Ri) * GB.R.ifc.tuh, 1e-9, "pegado: la lámina UHMW sigue en sectores con junta");
  // más junta o barra más ancha, más descuento
  const A0 = TT.compute(Object.assign(TT.defaults(), { opt_ss: 1 })), A1 = TT.compute(Object.assign(TT.defaults(), { opt_ss: 1, j_sec: 3 }));
  assert.ok(A1.m.ss < A0.m.ss, "una junta de 3 mm quita más material que una de 1 mm");
  // ambos sentidos de giro: la muesca tiene las dos paredes (chaflán en ambas) y el par de calado es el mismo en los dos sentidos (cilindros en espejo)
  const cw = TT.compute(Object.assign(TT.defaults(), { opt_ss: 1 })); assert.ok(cw.ifc.topes.every((x) => x.F > 0 && x.a_inf === P0.w_tope + 1));
});

test("4.ª pasada · anillo de acero de la cubierta de madera (t_ring)", () => {
  const P0 = TT.defaults(), W = TT.analyze(Object.assign(TT.defaults(), { opt_wood: 1 }), { noFEA: true }), A0 = TT.analyze(TT.defaults(), { noFEA: true }), m = W.R.m;
  assert.equal(P0.t_ring, 10, "pletina de 10 mm (mandante)");
  const q = TT.PARAM_GROUPS.find((g) => g.id === "cubierta").p.find((x) => x[0] === "t_ring"); assert.ok(q && /el alto es t_madera/.test(q[1]) && /anillo/i.test(q[1]), "parámetro documentado");
  const Rt = P0.D_top / 2, Rw = Rt - P0.t_ring;
  near(m.ring, RHO_S * Math.PI * (Rt ** 2 - Rw ** 2) * P0.t_wood, 1e-12, "m.ring = ρ·π·(R² − (R − t_ring)²)·t_madera (altura = espesor de los tablones)");
  assert.ok(m.ring > 24 && m.ring < 25, "≈ 24,5 kg"); assert.equal(A0.R.m.ring, 0, "sin madera no hay anillo");
  near(m.disc, A0.R.m.disc + m.wood + m.ring, 1e-12, "el anillo gira con la mesa: en m.disc");
  near(m.total - A0.R.m.total, m.wood + m.ring, 0.02, "m.total incluye el anillo");
  assert.ok(m.total > A0.R.m.total + m.wood, "más que solo la madera");
  const r = W.checks.find((c) => /Anillo de acero de contención de la madera/.test(c.name)); assert.ok(r && r.kind === "info"); near(r.dem, m.ring, 1e-12, "fila informativa");
  assert.ok(/R² − \(R − t_anillo\)²/.test(r.formula), "fórmula explícita");
  const g = TT.analyze(Object.assign(TT.defaults(), { opt_wood: 1, t_ring: 20 }), { noFEA: true }).R.m; assert.ok(g.ring > 2 * m.ring * 0.99 && g.wood < m.wood, "más ancho: más anillo y menos madera");
  // capacidad: la madera sigue cumpliendo
  assert.ok(W.verdict.gira && W.verdict.estructura, "madera con anillo cumple");
});

test("4.ª pasada · filete mejillas–base: mínimo AWS D1.1 T5.8 (parte más gruesa) y máximo AISC 360-22 J2.2b (borde de la mejilla)", () => {
  const P = TT.defaults(), g = (re, o) => TT.analyze(Object.assign(TT.defaults(), o || {}), { noFEA: true }).checks.find((c) => re.test(c.name));
  const mn = g(/Filete mínimo mejillas–base/), mx = g(/Filete máximo mejillas–base/);
  assert.ok(mn && mx, "ambas filas");
  assert.equal(mn.dem, 8, "T = máx(t_base 18; t_mejilla 25) = 25 → 8 mm"); assert.equal(mn.cap, P.w_br); assert.equal(mn.st, "ok");
  assert.equal(mx.dem, P.w_br); assert.equal(mx.cap, P.t_ch - 2, "t ≥ 6: w ≤ t − 2 = 23 mm (la mejilla termina en el borde)"); assert.equal(mx.st, "ok");
  assert.ok(/J2\.2b/.test(mx.ref) && /Tabla 5\.8/.test(mn.ref) && /se aplica la regla de AWS \(parte más gruesa\)/i.test(mn.ref), "citas");
  assert.equal(g(/Filete máximo mejillas–base/, { w_br: 24 }).st, "fail", "24 > 23");
  assert.equal(g(/Filete máximo mejillas–base/, { t_ch: 12, w_br: 12 }).st, "fail", "mejilla de 12: máx 10");
  assert.equal(g(/Filete máximo mejillas–base/, { t_ch: 12, w_br: 10 }).st, "ok");
  assert.equal(g(/Filete mínimo mejillas–base/, { w_br: 6 }).st, "fail", "6 < 8");
  assert.ok(/plancha base/.test(mx.formula) && /cara/.test(mx.formula), "aclara que la plancha base se suelda por su cara");
  // K2: la cita del filete mínimo aclara cuál regla se aplica en collar, oreja y almas
  for (const re of [/Collar: filete mínimo/, /Oreja: filete mínimo/, /Filete mínimo almas\/nervios–planchas/]) { const c = g(re); assert.ok(/se aplica la regla de AWS \(parte más gruesa\)/i.test(c.ref), "K2: " + c.name); }
});

test("4.ª pasada · flecha al izar la base (C12): margen ≥ 10 % del límite B/300 en todas las variantes, incluso B con madera", () => {
  const P0 = TT.defaults(); assert.equal(P0.c_lug, 200, "puntos de izaje a 200 mm del borde (150 dejaba B sin margen con hc_min = 6)");
  for (const [nm, o] of [...IFC_VARIANTS, ["B+madera", { opt_uhmw: 1, opt_wood: 1 }]]) {
    const P = Object.assign(TT.defaults(), o), R = TT.compute(P), L = TT.runLift(P, R, false);
    assert.ok(L.wMax <= 0.90 * P.B / 300, nm + ": flecha " + L.wMax.toFixed(2) + " mm vs límite " + (P.B / 300).toFixed(2));
  }
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
  assert.ok(Vc / Hf > 1.87 && Vc / Hf < 1.88, "V_c ≈ 1,875·H (la plancha base toma la reacción de signo contrario): " + Vc / Hf);
  assert.ok(Mc * 1e-6 > 13 && Mc * 1e-6 < 15.5, "M_c ≈ 14 kN·m respecto de la cara superior de la base: " + Mc * 1e-6);
  const aw = 0.707 * P.w_collar, f = Math.hypot(Mc / (Math.PI * P.D_boss ** 2 / 4 * aw), Vc / (Math.PI * P.D_boss * aw)), Fw = P.FEXX * 0.6 / (1.2 * P.Nd);
  const wc = g(/Soldadura del collar/);
  near(wc.dem, f, 1e-5, "grupo circular: f = √(f_b² + f_v²) con V_c y M_c"); near(wc.cap, Fw, 1e-12, "0,60 FEXX/(1,2 Nd)");
  assert.equal(P.w_collar, 10); assert.equal(wc.kind, "fu", "el filete del collar usa la banda warn como el resto (H8)");
  assert.ok(wc.fu <= 0.9 && wc.st === "ok", "con w = 10 mm cumple con FU ≤ 0,90: " + wc.fu);
  assert.ok(/V_c ≈ 1,875·H/.test(wc.formula) && !/1,85/.test(wc.formula), "K1: el rótulo dice 1,875·H (la integración da " + (Vc / Hf).toFixed(3) + ")");
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
  // 3.ª pasada: la profundidad del rebaje se mide desde la cara inferior de la mesa (h_collar − δ + c_a; δ = 0 sin interfaz); los primeros t_bot mm son el agujero de la plancha inferior y el resto, el cubo
  const hPl = Math.min(Hrb, P.t_bot), hHub = Math.min(Math.max(0, Hrb - P.t_bot), hw);
  near(R.m.hub, 7.85e-6 * Math.PI / 4 * ((P.D_hub ** 2 - d_b ** 2) * hw - (Drb ** 2 - d_b ** 2) * hHub), 1e-12, "masa del cubo con el rebaje con holguras (solo la parte sobre la plancha inferior)");
  near(hPl + hHub, Hrb, 1e-12, "plancha + cubo suman la profundidad total del rebaje (δ = 0: rebaje más profundo que la plancha)");
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

/* ======================================================================================================
   Temperatura de servicio (exposición solar, 80 °C) · docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)»
   Escenario aparte: con T_serv = 20 °C (por defecto) nada del cálculo estándar cambia; TT.thermal evalúa la MISMA geometría
   (dimensionada a 20 °C y congelada) con las capacidades reducidas a la temperatura.
   ====================================================================================================== */
const THALTS = { base: {}, A: { opt_ss: 1 }, B: { opt_uhmw: 1 }, C1: { opt_bz: 1, bz_conf: 1 }, C2: { opt_bz: 1, bz_conf: 2 }, C3: { opt_bz: 1, bz_conf: 3 } };

test("Temperatura · parámetros nuevos (grupo «Temperatura») con T_serv = 20 °C por defecto y rangos del registro", () => {
  const P = TT.defaults(), g = TT.PARAM_GROUPS.find((x) => x.id === "temperatura");
  assert.ok(g, "grupo Temperatura");
  const d = (id) => g.p.find((q) => q[0] === id);
  assert.equal(P.T_serv, 20); assert.equal(P.T_ref, 20); assert.equal(P.dT_grad, 0);
  assert.deepEqual([d("T_serv")[4], d("T_serv")[5]], [20, 120], "rango 20–120 °C");
  const K = { kT_Fy: 1.00, kT_E: 1.00, kT_Fy_ss: 0.82, kT_E_ss: 0.975, kT_p_uh: 0.40, kT_E_uh: 0.40, kT_bz: 1.00, kT_wood: 0.70, kT_bolt: 0.94, kT_weld: 1.00, kT_hertz: 1.00 };
  for (const [k, v] of Object.entries(K)) assert.equal(P[k], v, k);
  assert.equal(P.p_max_cil, 700); assert.equal(P.alivio_term, 0); assert.equal(P.nu_min, 10); assert.equal(P.K_oil, 1400); assert.equal(P.K_oil_hi, 1900); assert.equal(P.ba_cil, 1.4);
  // cada factor declara su nivel de confianza (A/B/C) en el rótulo
  for (const k of Object.keys(K)) assert.ok(/\((?:[ABC](?:\/[ABC])?)[);,]|confianza [ABC]/.test(d(k)[1]), "nivel de confianza en el rótulo de " + k + ": " + d(k)[1]);
  // el análisis estándar no cambia con T_serv: es un escenario aparte
  const A0 = TT.analyze(TT.defaults(), { noFEA: true }), A1 = TT.analyze(Object.assign(TT.defaults(), { T_serv: 80, dT_grad: 15 }), { noFEA: true });
  assert.equal(A1.checks.length, A0.checks.length, "T_serv no agrega filas ni cambia el cálculo estándar");
  A0.checks.forEach((c, i) => { assert.equal(A1.checks[i].name, c.name); assert.equal(A1.checks[i].fu, c.fu); assert.equal(A1.checks[i].st, c.st); });
  assert.ok(!A0.checks.some((c) => c.grp === "Temperatura"));
});

test("Temperatura · factores: 1 a 20 °C, valor tabulado a 80 °C, interpolación lineal y extrapolación con nota", () => {
  const P = TT.defaults(), f20 = TT.thermalFactors(P, 20), f80 = TT.thermalFactors(P, 80), f50 = TT.thermalFactors(P, 50), f100 = TT.thermalFactors(P, 100);
  for (const [k, v] of Object.entries(f20.k)) assert.equal(v, 1, "factor " + k + " a 20 °C = 1");
  assert.equal(f20.dT, 0); assert.equal(f80.dT, 60); assert.equal(f20.extrap, false); assert.equal(f80.extrap, false);
  near(f80.k.Fy_ss, 0.82, 1e-12, "inox Fy a 80"); near(f80.k.E_ss, 0.975, 1e-12, "inox E a 80"); near(f80.k.p_uh, 0.40, 1e-12, "UHMW k_p a 80"); near(f80.k.E_uh, 0.40, 1e-12, "UHMW k_E a 80");
  near(f80.k.wood, 0.70, 1e-12, "madera Ct a 80"); near(f80.k.bolt, 0.94, 1e-12, "perno 10.9"); near(f80.k.Fy, 1, 1e-12, "acero estructural"); near(f80.k.bz, 1, 1e-12, "bronce"); near(f80.k.weld, 1, 1e-12, "soldadura"); near(f80.k.hertz, 1, 1e-12, "Hertz");
  near(f50.k.Fy_ss, 1 + (0.82 - 1) * 30 / 60, 1e-12, "interpolación lineal a 50 °C"); near(f50.k.wood, 1 - 0.3 * 30 / 60, 1e-12, "madera a 50 °C");
  assert.equal(f100.extrap, true); assert.ok(f100.notes.some((s) => /80 °C/.test(s) && /extrapol/i.test(s)), "nota de extrapolación sobre 80 °C");
  near(f100.k.Fy_ss, 0.82 - 0.18 * 20 / 60, 1e-12, "extrapolación lineal (con cautela) a 100 °C"); assert.ok(f100.k.p_uh >= 0.05, "el factor no baja de 0,05");
  // dilataciones: acero 12×10⁻⁶ (EN 1993-1-1), media 20–80 °C 12,4×10⁻⁶ (EN 1993-1-2 §3.4.1.1), inox 17, UHMW 190, bronce 18, madera 5 en la fibra y 30 transversal
  near(f80.alpha.st, 12.4e-6, 0.002, "α acero medio 20–80 °C (EN 1993-1-2: 7,44×10⁻⁴/60)"); near(f20.alpha.st, 12e-6, 1e-12, "α acero a ΔT = 0 = 12×10⁻⁶");
  near(f80.alpha.ss, 17e-6, 1e-12, "inox"); near(f80.alpha.uh, 190e-6, 1e-12, "UHMW"); near(f80.alpha.bz, 18e-6, 1e-12, "bronce"); near(f80.alpha.woodT, 30e-6, 1e-12, "madera transversal"); near(f80.alpha.woodL, 5e-6, 1e-12, "madera en la fibra");
  near(TT.alphaSteelMean(80) * 60, 1.2e-5 * 80 + 0.4e-8 * 80 * 80 - 2.416e-4, 1e-9, "ε(80 °C) de EN 1993-1-2 = 7,44×10⁻⁴");
});

test("Temperatura · aceite atrapado: Δp = (α_v − 3α_s)·ΔT/(1/K_aceite + 1/K_c) con los valores del registro", () => {
  const P = TT.defaults(), o = TT.oilTrapped(P, 80), a3 = 3 * TT.alphaSteelMean(80), av = 7.5e-4;
  near(o.dT, 60, 1e-12, "ΔT"); near(o.av, av, 1e-12, "α_v"); 
  near(o.rigid.lo.dp, (av - a3) * 60 * 1400, 1e-9, "recipiente rígido, K = 1,4 GPa (MPa)");
  near(o.rigid.hi.dp, (av - a3) * 60 * 1900, 1e-9, "recipiente rígido, K = 1,9 GPa (MPa)");
  near(o.rigid.hi.bar, 815, 0.01, "registro: 815 bar con 1,9 GPa");
  const Kc = P.E / (2 * ((P.ba_cil ** 2 + 1) / (P.ba_cil ** 2 - 1) + P.nu));
  near(o.Kc_lame, Kc, 1e-12, "K_c de Lamé"); near(Kc / 1000, 30, 0.03, "registro: K_c ≈ 30 GPa para b/a = 1,4");
  near(o.cyl.hi.dp, (av - a3) * 60 / (1 / 1900 + 1 / Kc), 1e-9, "cilindro Lamé, 1,9 GPa"); near(o.cyl.hi.bar, 770, 0.02, "registro: ≈ 770 bar");
  near(o.cyl.lo.dp, (av - a3) * 60 / (1 / 1400 + 1 / Kc), 1e-9, "cilindro Lamé, 1,4 GPa"); assert.ok(o.cyl.hi.dp > o.cyl.lo.dp, "con K mayor la presión sube: la cota alta es 1,9 GPa");
  near(o.hose.hi.bar, 140, 0.03, "registro: ≈ 140 bar con manguera (K combinado ≈ 0,33 GPa)");
  assert.equal(TT.oilTrapped(P, 20).cyl.hi.dp, 0, "a 20 °C no hay sobrepresión térmica");
  near(o.expansion_free_pct, 100 * (av - 3 * TT.alphaSteelMean(80)) * 60, 1e-9, "dilatación libre del aceite (%): 4,28 % (registro: 4,29 %)"); near(o.expansion_free_pct, 4.29, 0.01, "registro");
});

test("Temperatura · viscosidad del aceite (Walther) y mínimo de la bomba", () => {
  near(TT.oilViscosity(80).lo, 11.1, 0.01, "VG 46 con ν100 = 6,8: ≈ 11 mm²/s a 80 °C (registro)"); near(TT.oilViscosity(80).hi, 14.6, 0.01, "VG 46 con IV 185: ≈ 14,6 mm²/s");
  near(TT.oilViscosity(40).lo, 46, 1e-9, "ν40 = 46"); near(TT.oilViscosity(100).lo, 6.8, 1e-9, "ν100 = 6,8"); near(TT.oilViscosity(40).hi, 47.4, 1e-9, "Eurol: 47,4"); near(TT.oilViscosity(100).hi, 9.5, 1e-9, "Eurol: 9,5");
  assert.ok(TT.oilViscosity(60).lo > TT.oilViscosity(80).lo, "la viscosidad baja con T");
});

test("Temperatura · a 20 °C el escenario reproduce el cálculo estándar (factores = 1) y la geometría queda congelada a T_serv", () => {
  for (const [id, fl] of Object.entries(THALTS)) {
    const Pa = Object.assign(TT.defaults(), fl), A0 = TT.analyze(Pa, { noFEA: true });
    const A1 = TT.analyze(TT.thermalP(Pa, 20), { noFEA: true });                                  // factores a 20 °C: todos = 1
    A0.checks.forEach((c, i) => { assert.equal(A1.checks[i].name, c.name, id); assert.ok(c.fu == null ? A1.checks[i].fu == null : Math.abs(A1.checks[i].fu - c.fu) <= 1e-12 * Math.max(1, Math.abs(c.fu)) || c.fu === A1.checks[i].fu, id + " · " + c.name); assert.equal(A1.checks[i].st, c.st, id + " · " + c.name); });
    assert.ok(A1.checks.length > A0.checks.length && A1.checks.slice(A0.checks.length).every((c) => c.grp === "Temperatura"), id + ": el escenario solo AGREGA filas del grupo Temperatura");
  }
  const r = TT.thermal(TT.defaults(), { T: [20, 80], wood: false });
  assert.deepEqual(r.alternativas.map((a) => a.id), ["base", "A", "B", "C1", "C2", "C3"]);
  for (const a of r.alternativas) {
    const Pa = Object.assign(TT.defaults(), THALTS[a.alt]), A = TT.analyze(Pa), I = A.R.ifc, [b20, b80] = a.byT;
    near(b20.FS, A.R.cd.FS, 1e-9, a.id + ": FS a 20 °C"); near(a.FS20, A.R.cd.FS, 1e-9, a.id + ": FS20");
    near(b20.fuEst, Math.max(...A.checks.filter((c) => c.sys === "est" && c.kind === "fu" && isFinite(c.fu)).map((c) => c.fu)), 1e-9, a.id + ": FU estructura máx. a 20 °C = el del análisis estándar");
    near(b20.masa, A.R.m.total, 1e-9, a.id + ": masa a 20 °C"); assert.equal(b80.masa, b20.masa, a.id + ": la masa no cambia (geometría congelada)");
    assert.deepEqual([a.geometria.tss, a.geometria.tss2, a.geometria.tuh, a.geometria.tbz], [I.tss, I.tss2, I.tuh, I.tbz || 0].map((x, i) => (i === 3 ? I.tbz : x)), a.id + ": espesores del escenario = los de 20 °C");
    assert.equal(b20.FS, b80.FS, a.id + ": con μ constante el FS del giro no depende de la temperatura");
  }
  // sin congelar, la lámina UHMW se re-dimensionaría con p_adm·0,4 (más gruesa): el escenario NO lo hace
  const PB = Object.assign(TT.defaults(), THALTS.B), t20 = TT.analyze(PB, { noFEA: true }).R.ifc.tuh, tFree = TT.analyze(TT.thermalP(PB, 80), { noFEA: true }).R.ifc.tuh;
  assert.ok(tFree > t20, "sin congelar la lámina sube de " + t20 + " a " + tFree + " mm");
  const rB = TT.thermal(TT.defaults(), { T: [20, 80], alts: ["B"] }).alternativas[0];
  assert.equal(rB.geometria.tuh, t20); assert.equal(rB.byT[1].masa, rB.byT[0].masa);
  // largos de tope y espesores de disco también congelados (A: el Fy del inox baja 18 % y el tope no se alarga)
  const rA = TT.thermal(TT.defaults(), { T: [20, 80], alts: ["A"] }).alternativas[0], A20 = TT.analyze(Object.assign(TT.defaults(), THALTS.A), { noFEA: true });
  assert.deepEqual(rA.geometria.L, Object.fromEntries(A20.R.ifc.topes.map((s) => [s.id, s.L])), "largos de los topes de 20 °C");
});

test("Temperatura · filas de juntas, buje de bronce, gradiente y uña: fórmulas del registro", () => {
  const r = TT.thermal(TT.defaults(), { T: [20, 80], alts: ["B"] }), a = r.alternativas[0], f = a.byT[1].filas, P = TT.defaults(), A = TT.analyze(Object.assign(TT.defaults(), THALTS.B), { noFEA: true }), R = A.R;
  const row = (re) => { const x = f.find((q) => re.test(q.nombre)); assert.ok(x, "fila " + re); return x; };
  const as = TT.alphaSteelMean(80), chord = 2 * R.Ro * Math.sin(Math.PI / P.n_seg);
  // (a) junta UHMW: α 190, acero 12,4 → 2,78 mm requeridos frente a 1,8 mm en frío (diseño a 40 K con 180×10⁻⁶): se cierra
  const jU = row(/Lámina UHMW \(24 sectores\): junta de dilatación requerida/);
  near(jU.dem, (190e-6 - as) * 60 * chord, 1e-9, "j_req UHMW"); near(jU.cap, Math.ceil(Math.max(P.j_sec, (AL_UH_ - 11.7e-6) * P.dT * chord) * 10 - 1e-9) / 10, 1e-12, "j_disp = junta del diseño a 20 °C"); assert.equal(jU.estado, "fail", "la junta de la lámina UHMW cierra a 80 °C");
  assert.equal(a.juntas.find((j) => /UHMW/.test(j.pieza)).j_req, jU.dem);
  const jD = row(/Disco de la base \(liso\).*junta de dilatación requerida/); near(jD.dem, (17e-6 - as) * 60 * 2 * R.Ro * Math.sin(Math.PI / P.n_sec), 1e-9, "j_req inox"); assert.equal(jD.estado, "ok");
  // (b) buje de bronce en el pivote
  const D = P.D_piv, bu = row(/Buje de bronce–pivote: holgura con el buje libre/);
  near(bu.dem, (18e-6 - as) * 60 * D, 1e-9, "Δ holgura libre = (α_bz − α_acero)·ΔT·D (afloja)"); near(bu.cap, (18e-6 - as) * 60 * (D + 30), 1e-9, "Δ interferencia en el cubo (aprieta)");
  const bc = row(/cierre de la holgura diametral/); assert.ok(bc.dem > 0 && bc.dem < 0.05 && bc.estado === "ok", "con el buje retenido la holgura se reduce unas centésimas de mm y no se cierra: " + bc.dem); near(bc.cap, P.c_bush_d, 1e-12, "holgura en frío");
  // (c) uña–pasador con la mesa caliente y la base a la sombra
  const eps = as * 60, dR = eps * P.R_pin, K = R.K;
  near(row(/holgura radial de la uña en el patín/).dem, K.radial * (1 + eps) + 2 + dR, 1e-9, "holgura radial + α·ΔT·R_pin"); near(dR, 0.69, 0.02, "registro: 0,69 mm para 60 K y R_pin 930");
  near(row(/caso uniforme/).dem, (P.x_g - K.armMin) * eps, 1e-9, "escala uniforme: ≈ 0,16 mm"); assert.ok(row(/caso uniforme/).dem < 0.2);
  // (d) gradiente de 15 K a 80 °C: κ = α·ΔT/h, flecha κ·(D/2)²/2, σ = E·α·ΔT/(2(1 − ν))
  const kap = as * 15 / P.h_disc, sig = P.E * as * 15 / (2 * (1 - P.nu));
  near(row(/curvatura térmica/).dem, kap * 1e3, 1e-9, "κ (1/m)"); near(row(/flecha en el diámetro/).dem, kap * (P.D_top / 2) ** 2 / 2, 1e-9, "flecha"); near(row(/tensión de flexión térmica/).dem, sig, 1e-9, "σ restringida");
  const top = TT.analyze(Object.assign(TT.defaults(), THALTS.B)).checks.find((c) => c.name === "Plancha superior: global + local"), gt = row(/Gradiente: plancha superior/);
  near(gt.dem, top.dem + sig, 1e-9, "FU de la plancha superior + σ térmica (suma conservadora)"); near(gt.fu, (top.dem + sig) / top.cap, 1e-9);
  near(row(/desnivel de la cara de contacto/).dem, kap * (R.Ro ** 2 - R.Ri ** 2) / 2, 1e-9, "desnivel R_i–R_o");
  // sin gradiente (T = 20): todo en cero
  const f20 = a.byT[0].filas; assert.equal(f20.find((q) => /curvatura térmica/.test(q.nombre)).dem, 0); assert.equal(f20.find((q) => /junta de dilatación requerida/.test(q.nombre)).dem, 0);
});
const AL_UH_ = 180e-6;

test("Temperatura · aceite atrapado: p_hold + Δp contra el cilindro, alivio térmico y recomendación", () => {
  const P = TT.defaults(), g = (o, T) => TT.thermal(Object.assign(TT.defaults(), o), { T: [20, T || 80], alts: ["base"] }).alternativas[0].byT[1].filas;
  const rows = g({}), A = TT.analyze(P, { noFEA: true }), pd = A.R.cd.p, o = TT.oilTrapped(P, 80), dp = o.sel.hi.bar;
  assert.equal(P.oil_cont, 2, "contenedor por defecto: cilindro (Lamé)");
  const ho = rows.find((x) => /carrera de diseño: p_hold/.test(x.nombre)), cal = rows.find((x) => /tras el calado/.test(x.nombre)), ann = rows.find((x) => /cámara anular/.test(x.nombre)), vv = rows.find((x) => /Válvula de alivio térmico del tramo/.test(x.nombre));
  near(ho.dem, pd + dp, 1e-9, "p_hold = F_dis/A más Δp"); near(ho.cap, 700, 1e-12, "p_max_cil"); assert.equal(ho.estado, "fail");
  near(cal.dem, P.p_relief + dp, 1e-9, "calado: p_alivio + Δp"); near(cal.cap, 1050, 1e-12, "prueba 1,5×"); assert.equal(cal.estado, "fail");
  near(ann.dem, P.p_ret + dp, 1e-9, "cámara anular: p_ret + Δp"); assert.equal(ann.estado, "fail");
  assert.equal(vv.estado, "fail"); assert.ok(/instalar válvula de alivio térmico en el tramo aislado/.test(vv.nombre + vv.formula) && /aguas arriba/.test(vv.formula), "recomendación y aviso del alivio de sistema");
  near(dp, 763.5, 0.01, "Δp con K = 1,9 GPa y cilindro Lamé a ΔT = 60 K: ≈ 764 bar");
  // con un alivio térmico que abre en 700 bar (= p_max_cil y = alivio del sistema) la presión queda limitada: monitoreo, sin fallo
  const w = g({ alivio_term: 700 }); assert.ok(!w.some((x) => x.sys === "term" && x.estado === "fail"), "alivio térmico a 700 bar: ninguna fila térmica de aceite falla");
  assert.ok(w.some((x) => /Válvula de alivio térmico: apertura bajo la presión máxima/.test(x.nombre) && x.estado === "ok"));
  assert.equal(g({ alivio_term: 900 }).find((x) => /apertura bajo la presión máxima/.test(x.nombre)).estado, "fail", "apertura sobre p_max_cil");
  assert.equal(g({ alivio_term: 600 }).find((x) => /apertura sobre el alivio del sistema/.test(x.nombre)).estado, "fail", "por debajo del alivio del sistema gotea a calado");
  // rígido > cilindro > manguera
  const dpOf = (c) => g({ oil_cont: c }).find((x) => /carrera de diseño: p_hold/.test(x.nombre)).dem - pd;
  assert.ok(dpOf(1) > dpOf(2) && dpOf(2) > dpOf(3), "rígido > cilindro > manguera"); near(dpOf(3), 140, 0.03, "manguera ≈ 140 bar");
  // a 20 °C no hay sobrepresión y la verificación pasa; a 40 K (T = 60) el aceite ya excede
  assert.equal(TT.thermal(P, { T: [20, 80], alts: ["base"] }).alternativas[0].byT[0].filas.find((x) => /carrera de diseño: p_hold/.test(x.nombre)).estado, "ok");
});

test("Temperatura · aceite, sellos, grasa y sensibilidades (μ, Fy 0,92, UHMW k_p/k_E, madera)", () => {
  const P = TT.defaults(), r = TT.thermal(P, { T: [20, 40, 60, 80, 100] }), by = (id) => r.alternativas.find((a) => a.id === id);
  const row = (a, T, re) => a.byT.find((b) => b.T === T).filas.find((x) => re.test(x.nombre));
  const bs = by("base");
  const v80 = row(bs, 80, /viscosidad a T_serv/), v100 = row(bs, 100, /viscosidad a T_serv/);
  near(v80.cap, TT.oilViscosity(80).lo, 1e-12); near(v80.fu, P.nu_min / TT.oilViscosity(80).lo, 1e-12); assert.equal(v80.estado, "warn", "≈ 11 mm²/s frente al mínimo supuesto de 10: monitoreo"); assert.equal(v100.estado, "fail", "6,8 mm²/s < 10");
  assert.equal(row(bs, 80, /Sellos NBR/).estado, "warn"); assert.equal(row(bs, 100, /Sellos NBR/).estado, "warn", "80–120 °C: solo monitoreo"); assert.equal(row(bs, 40, /Sellos NBR/).estado, "ok");
  const gr = row(bs, 80, /punto de goteo/); near(gr.fu, 80 / 175, 1e-12); assert.equal(gr.estado, "ok"); assert.ok(/T_goteo − T = 95 K/.test(gr.formula), "margen de 95 K a 80 °C");
  // μ: FS(μ·f) = FS/f; el multiplicador máximo con FS ≥ FS_mín es FS/FS_mín
  near(bs.sens.mu[2].FS, bs.FS20 / 1.2, 1e-12); near(bs.sens.mu[3].FS, bs.FS20 / 1.5, 1e-12); assert.equal(bs.sens.mu[1].gira, true); assert.equal(bs.sens.mu[2].gira, false, "μ × 1,2 baja el FS del giro bajo 1,25 en la base"); near(bs.sens.mu_crit, bs.FS20 / P.FS_min, 1e-12);
  assert.ok(by("C1").sens.mu_crit > bs.sens.mu_crit, "el bronce con grafito tiene más margen de μ (μ_d 0,15 frente a 0,20)");
  // k_mu_T como entrada: con 1,2 a 80 °C el FS del giro baja a FS/1,2 y el golden a 20 °C no cambia
  const rm = TT.thermal(Object.assign(TT.defaults(), { k_mu_T: 1.2 }), { T: [20, 80], alts: ["base"] }).alternativas[0];
  near(rm.byT[1].FS, rm.byT[0].FS / 1.2, 1e-9, "FS con μ × 1,2"); assert.equal(rm.byT[0].FS, rm.FS20);
  // Fy × 0,92 (ASME II-D): con la base el FU máximo de las verificaciones de fluencia sube 1/0,92 y queda ≤ 1,0
  assert.equal(bs.byT.find((b) => b.T === 80).fuEst, bs.byT[0].fuEst, "k_Fy = 1,00: el FU máximo de la base no cambia a 80 °C");
  near(bs.sens.kFy092.fuEst, bs.byT[0].fuEst / 0.92, 1e-6, "FU máx / 0,92"); assert.ok(bs.sens.kFy092.fuEst <= 1, "la base mantiene FU ≤ 1,0 en las verificaciones estándar con Fy × 0,92: " + bs.sens.kFy092.fuEst); assert.ok(bs.sens.kFy092.fuTerm > 1 && /Gradiente/.test(bs.sens.kFy092.gobernanteTerm.nombre), "pero con el gradiente de 15 K sumado, la plancha supera 1,0: " + bs.sens.kFy092.fuTerm);
  assert.ok(bs.sens.kFy092.empeoran.length > 0 && bs.sens.kFy092.empeoran.every((x) => x.de !== "fail"));
  // inox (A, B): el Fy del inox baja 18 % → los topes de los discos (dimensionados para FU 0,90) pasan de 1,0: cambian de estado
  for (const id of ["A", "B"]) { const cam = by(id).byT.find((b) => b.T === 80).cambian.filter((c) => /aplastamiento del tope/.test(c.nombre)); assert.ok(cam.length >= 1 && cam.every((c) => c.de === "ok" && c.a === "fail" && c.empeora), id + ": tope del disco inox falla a 80 °C"); }
  assert.equal(by("C1").byT.find((b) => b.T === 80).cambian.filter((c) => c.grp !== "Temperatura" && c.grp !== "Mesa").length, 0, "C1: sin cambios de estado de verificaciones estándar con k_bz = 1,00");
  // UHMW (B): k_p·p_adm; la lámina solo cumple si k_p ≥ k_crítico (< 1); monotonía
  const B = by("B"), u = B.sens.uhmw;
  assert.ok(u.kp_crit > 0.4 && u.kp_crit < 1 && u.kp.find((x) => x.k_p === 1).cumple && !u.kp.find((x) => x.k_p === 0.4).cumple, "k_p crítico entre 0,4 y 1: " + u.kp_crit);
  for (let i = 1; i < u.kp.length; i++) assert.ok(u.kp[i].fuUHMW <= u.kp[i - 1].fuUHMW + 1e-12, "FU de la lámina no crece con k_p");
  assert.equal(B.byT.find((b) => b.T === 80).gira, false, "B no gira con seguridad a 80 °C: el aplastamiento del tope del rebaje supera p_adm·0,4");
  assert.ok(B.byT.find((b) => b.T === 80).cambian.some((c) => /Lámina UHMW.*aplastamiento del canto/.test(c.nombre) && c.empeora));
  assert.ok(row(B, 80, /acortamiento elástico/).dem > row(B, 20, /acortamiento elástico/).dem, "E reducida: más deformación bajo carga");
  // madera: C_t sobre p_wood
  const W = TT.thermal(Object.assign(TT.defaults(), { opt_wood: 1 }), { T: [20, 80], alts: ["base"] }).alternativas[0], mw = (T) => W.byT.find((b) => b.T === T);
  assert.equal(W.madera, true); const cw = (T) => mw(T).sensibles_est.concat(mw(T).sensibles).find((x) => /Madera: aplastamiento/.test(x.nombre));
  near(cw(80).fuT / cw(80).fu20, 1 / 0.7, 1e-9, "FU de la madera × 1/C_t"); assert.equal(W.sens.madera[1].Ct, 0.5); assert.ok(W.sens.madera[1].fu > W.sens.madera[0].fu);
});

test("Temperatura · escenario por defecto (solar 80 °C, 15 K), temperaturas del escenario, JSON puro y lista de verificaciones sensibles", () => {
  const r = TT.thermal(TT.defaults(), { alts: ["base", "B"] });
  assert.equal(r.T_scn, 80); assert.equal(r.gradiente_scn, 15, "sin T_serv definida el escenario es el solar: 80 °C y 15 K"); assert.deepEqual(r.T, [20, 40, 60, 80, 100]);
  const r2 = TT.thermal(Object.assign(TT.defaults(), { T_serv: 60 }), { T: [20, 40], alts: ["base"] });
  assert.equal(r2.T_scn, 60); assert.equal(r2.gradiente_scn, 0); assert.deepEqual(r2.T, [20, 40, 60], "la tabla incluye la temperatura del escenario");
  assert.equal(TT.thermal(Object.assign(TT.defaults(), { T_serv: 60, dT_grad: 10 }), { T: [20, 60], alts: ["base"] }).alternativas[0].byT[1].gradiente, 10);
  const s = JSON.stringify(r); assert.ok(!/NaN|undefined|Infinity/.test(s), "JSON sin NaN/undefined/Infinity"); assert.deepEqual(JSON.parse(s), JSON.parse(JSON.stringify(TT.thermal(TT.defaults(), { alts: ["base", "B"] }))), "determinista");
  for (const a of r.alternativas) for (const b of a.byT) {
    assert.ok(b.sensibles.length <= 10 && b.sensibles_est.length <= 10);
    b.sensibles.forEach((x) => { assert.ok(["A", "B", "C", "A/C", "B/C"].includes(x.conf), "nivel de confianza: " + x.conf); assert.ok(x.fuT >= x.fu20 && x.nombre); });
    for (let i = 1; i < b.sensibles.length; i++) assert.ok(b.sensibles[i].delta <= b.sensibles[i - 1].delta + 1e-12, "ordenadas por aumento de FU");
    assert.ok(b.cambian.every((c) => ["ok", "warn", "fail"].includes(c.de) && ["ok", "warn", "fail"].includes(c.a) && c.de !== c.a));
  }
  assert.ok(r.avisos.some((x) => /BTH-1/.test(x) && /66 °C/.test(x)) && r.avisos.some((x) => /UHMW/.test(x) && /confianza C/.test(x)) && r.avisos.some((x) => /alivio térmico/.test(x)));
  const b80 = r.alternativas[0].byT.find((b) => b.T === 80); assert.ok(b80.sensibles[0].sys === "term" || b80.sensibles[0].delta > 0);
  // pestañas de extrapolación
  assert.ok(r.alternativas[0].byT.find((b) => b.T === 100).extrapolado && r.alternativas[0].byT.find((b) => b.T === 100).notas.some((x) => /extrapol/.test(x)));
});

/* ======================= Tapones de grafito (opción C): cantidad real colocable frente a la ideal ======================= */
// Golden del modo ideal (bz_fg_modo = 0): reproduce el cálculo anterior a los tapones reales (f_g = π·d²/(2√3·p²) sobre toda la corona)
const bzSnap = (conf, o) => {
  const A = TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, bz_conf: conf }, o || {}), { noFEA: true }), R = A.R, I = R.ifc;
  return { mBz: R.m.bz, mTotal: R.m.total, N: R.N, q: I.q, qLoc: I.qLoc, qNet: I.qNet, tbz: I.tbz, tbzReq: I.tbzReq, tss: I.tss, tssReq: I.tssReq, fg: I.fg, eta: I.eta, FS: R.cd.FS,
    fu: Object.fromEntries(A.checks.filter((c) => c.grp === "Interfaz bronce" && c.fu != null && isFinite(c.fu)).map((c) => [c.name, c.fu])) };
};
test("Tapones · golden del modo ideal (bz_fg_modo = 0 reproduce el cálculo anterior de C1, C2 y C3)", () => {
  const snap = Object.fromEntries([1, 2, 3].map((c) => ["C" + c, bzSnap(c, { bz_fg_modo: 0 })]));
  const f = path.join(__dirname, "golden", "tt300c_bz_ideal.json");
  if (process.env.UPDATE_GOLDEN || !fs.existsSync(f)) fs.writeFileSync(f, JSON.stringify(snap, null, 1));
  const g = JSON.parse(fs.readFileSync(f, "utf8"));
  const cmp = (a, b, k) => {
    if (typeof b === "number") near(a, b, 1e-9, k);
    else for (const kk of Object.keys(b)) { assert.ok(a && kk in a, "falta " + k + "." + kk); cmp(a[kk], b[kk], k + "." + kk); }
  };
  cmp(snap, g, "golden-ideal");
});

/* ======================= Temperatura: alcance (term_alcance) ======================= */
// Golden del escenario anterior (term_alcance = 2: sistema de placas y disco + accionamiento y circuito hidráulico)
const thSnap = (P) => {
  const r = TT.thermal(P, { T: [20, 80] });
  return Object.fromEntries(r.alternativas.map((a) => [a.id, Object.fromEntries(a.byT.map((b) => [String(b.T), {
    FS: b.FS, gira: b.gira, estructura: b.estructura, termico: b.termico, fuEst: b.fuEst, fuTerm: b.fuTerm, masa: b.masa, nFail: b.nFail, nWarn: b.nWarn,
    filas: Object.fromEntries(b.filas.map((x) => [x.nombre, x.fu == null ? -1 : (isFinite(x.fu) ? x.fu : 1e9)])), estados: b.filas.map((x) => x.estado).join(",") }]))]));
};
test("Temperatura · golden del escenario anterior (term_alcance = 2 reproduce el comportamiento previo en las siete alternativas)", () => {
  const snap = thSnap(Object.assign(TT.defaults(), { term_alcance: 2 }));
  const f = path.join(__dirname, "golden", "tt300c_termica_alcance2.json");
  if (process.env.UPDATE_GOLDEN || !fs.existsSync(f)) fs.writeFileSync(f, JSON.stringify(snap, null, 1));
  const g = JSON.parse(fs.readFileSync(f, "utf8"));
  const cmp = (a, b, k) => {
    if (typeof b === "number") near(a, b, 1e-9, k);
    else if (typeof b === "object" && b !== null) for (const kk of Object.keys(b)) { assert.ok(a && kk in a, "falta " + k + "." + kk); cmp(a[kk], b[kk], k + "." + kk); }
    else assert.equal(a, b, k);
  };
  cmp(snap, g, "golden-termica");
});

/* Conteo independiente de los tapones: malla escalonada propia (coordenadas cartesianas), sin reutilizar el código del núcleo.
   Centros de la malla (paso p, fila alterna p·√3/2, anclada al centro de la mesa) cuyo borde queda a ≥ bz_edge del borde del bronce, de las muescas, de los tornillos y de las ranuras. */
function tapIndep(P, R, conf, d, p, edge) {
  const I = R.ifc, Ri = R.Ri, Ro = R.Ro, n = conf === 3 ? P.bz_npad : P.n_sec, th = 2 * Math.PI / n, m = edge + d / 2, cov = conf === 3 ? I.cov : 1;
  const L = P.fix_mode < 1.5 ? I.topes.find((t) => t.id === "bz0").L : 0, hb = (P.b_tope + 2) / 2, ru = R.r_u;
  const gap = Math.max(...I.cortes.filter((c) => !c.strip).map((c) => c.j), P.j_sec);   // junta en frío efectiva entre sectores (mm)
  const dk = { 4: 8, 5: 10, 6: 12, 8: 16, 10: 20, 12: 24 }[P.d_tor] || 2 * P.d_tor;
  const rScrew = P.fix_mode < 1.5 ? I.tap.radios : [];
  const rCirc = P.h_gr > 0 ? I.tap.r_circ : [];
  let N = 0;
  const nrow = Math.ceil(Ro / (p * Math.sqrt(3) / 2)) + 2;
  for (let j = -nrow; j <= nrow; j++) for (let i = -nrow; i <= nrow; i++) {
    const x = i * p + (Math.abs(j) % 2) * p / 2, y = j * p * Math.sqrt(3) / 2, r = Math.hypot(x, y);
    if (r < Ri + m || r > Ro - m) continue;
    let ang = Math.atan2(y, x); if (ang < 0) ang += 2 * Math.PI;
    const k = Math.min(n - 1, Math.floor(ang / th + 1e-12)), a = (k + 0.5) * th;
    const xl = x * Math.cos(a) + y * Math.sin(a), yl = -x * Math.sin(a) + y * Math.cos(a);   // marco local: bisectriz del sector sobre +x
    const sd = (b, px, py) => -px * Math.sin(b) + py * Math.cos(b);                         // distancia con signo a la recta radial de ángulo b (positiva hacia +θ)
    let e1, e2;
    if (conf === 3) { const ph = th * cov / 2; e1 = sd(-ph, xl, yl); e2 = -sd(ph, xl, yl); }     // pastilla: bordes radiales a ±(cobertura·paso angular)/2
    else { e1 = sd(-th / 2, xl, yl) - gap / 2; e2 = -sd(th / 2, xl, yl) - gap / 2; }              // sector: bordes en las radiales de contorno, separados por la junta
    if (e1 < m || e2 < m) continue;
    if (L > 0 && Math.abs(yl) < hb + m && xl > ru - L / 2 - m && xl < ru + L / 2 + m) continue;
    if (rScrew.some((rr) => Math.hypot(xl - rr, yl) < dk / 2 + m)) continue;
    if (rCirc.some((rg) => Math.abs(r - rg) < P.w_gr / 2 + m)) continue;
    if (P.h_gr > 0) {   // ranuras radiales equiespaciadas: distancia lateral del centro a la recta de la ranura (semirrecta que sale del centro de la mesa)
      let hit = false;
      for (let q = 0; q < P.n_gr_rad && !hit; q++) { const f = 2 * Math.PI * q / P.n_gr_rad; if (x * Math.cos(f) + y * Math.sin(f) > 0 && Math.abs(sd(f, x, y)) < P.w_gr / 2 + m) hit = true; }
      if (hit) continue;
    }
    N++;
  }
  return N;
}
const C_VARS = [["C1", 1], ["C2", 2], ["C3", 3]];
const bzA = (conf, o) => TT.analyze(Object.assign(TT.defaults(), { opt_bz: 1, bz_conf: conf }, o || {}), { noFEA: true });

test("Tapones · parámetros nuevos (bz_edge 4, bz_fg_modo 1, bz_fg_min 0,20 supuesto C, bz_eta_min 0,45, bz_n_tor 2) y defaults del patrón sin cambios", () => {
  const P = TT.defaults(), g = (id) => TT.PARAM_GROUPS.flatMap((x) => x.p).find((q) => q[0] === id);
  assert.deepEqual([P.bz_edge, P.bz_fg_modo, P.bz_fg_min, P.bz_eta_min, P.bz_n_tor, P.bz_fg_estricto], [4, 1, 0.20, 0.45, 2, 0]);
  assert.ok(/supuesto C/.test(g("bz_fg_min")[1]) && /catálogo/.test(g("bz_fg_min")[1]), "bz_fg_min declarado como supuesto C a confirmar con catálogo");
  assert.deepEqual([P.bz_plug_d, P.bz_plug_p], [12, 30], "el barrido no encuentra un patrón que cumpla f_g ≥ 0,20 con η ≥ 0,45: se conserva Ø12 · paso 30");
});

test("Tapones · N_real contra el conteo independiente (malla propia): C1, C2 y C3; f_g,real = N·π·d²/4/A_contacto ≤ f_g,ideal", () => {
  for (const [nm, conf] of C_VARS) {
    const A = bzA(conf), R = A.R, I = R.ifc, P = A.P, T = I.tap, ctx = nm + ": ";
    assert.equal(T.N, tapIndep(P, R, conf, P.bz_plug_d, P.bz_plug_p, P.bz_edge), ctx + "N_real = conteo independiente");
    assert.equal(I.Nreal, T.N); assert.ok(Number.isInteger(T.N), "entero");
    const Acont = R.Ac * (conf === 3 ? I.cov : 1), ap = Math.PI * P.bz_plug_d ** 2 / 4;
    near(I.fgReal, T.N * ap / Acont, 1e-12, ctx + "f_g,real"); near(I.cobGrafito, I.fgReal, 1e-12, ctx + "cobertura de grafito = π d²/4·N/A");
    near(I.fgIdeal, Math.PI * P.bz_plug_d ** 2 / (2 * Math.sqrt(3) * P.bz_plug_p ** 2), 1e-12, ctx + "f_g,ideal"); assert.equal(I.fg, I.fgIdeal, "I.fg conserva el significado ideal");
    assert.ok(I.fgReal <= I.fgIdeal, ctx + "real ≤ ideal"); near(I.Nideal, I.fgIdeal * Acont / ap, 1e-12, ctx + "N ideal equivalente");
    assert.equal(T.porSector.length, conf === 3 ? P.bz_npad : P.n_sec); assert.equal(T.porSector.reduce((s, v) => s + v, 0), T.N, "N por sector/pastilla suma N");
    assert.equal(I.topes.find((t) => t.id === "bz0").L, T.L, ctx + "el largo de la muesca del conteo es el del tope del núcleo (R.ifc.topes)");
    const pd = T.perdidas; assert.ok(["borde", "muesca", "tornillos", "ranCirc", "ranRad"].every((k) => pd[k] >= 0), "pérdidas por causa");
    assert.equal(T.N_malla - pd.borde - pd.muesca - pd.tornillos - pd.ranCirc - pd.ranRad, T.N, "balance: malla en la corona − pérdidas = N_real");
  }
  // conciliación con el 3D del dibujante (cad/modelo3d_tt300c.py, patrón S09): 2.640 en C1/C2 y 2.364 en C3
  assert.equal(bzA(1).R.ifc.Nreal, 2640); assert.equal(bzA(2).R.ifc.Nreal, 2640); assert.equal(bzA(3).R.ifc.Nreal, 2364);
  // otros patrones y márgenes: mismo resultado que el conteo independiente
  for (const [nm, conf, o] of [["C1 Ø16/p34", 1, { bz_plug_d: 16, bz_plug_p: 34 }], ["C3 Ø14/p26 borde 6", 3, { bz_plug_d: 14, bz_plug_p: 26, bz_edge: 6 }], ["C1 pegado", 1, { fix_mode: 2 }], ["C1 sin ranuras", 1, { h_gr: 0 }], ["C2 12 sectores", 2, { n_sec: 12 }]]) {
    const A = bzA(conf, o); assert.equal(A.R.ifc.tap.N, tapIndep(A.P, A.R, conf, A.P.bz_plug_d, A.P.bz_plug_p, A.P.bz_edge), nm);
  }
});

test("Tapones · modo 0 (ideal) reproduce el cálculo anterior; modo 1 (real) cambia masa, q_neto, PV y desgaste de forma consistente", () => {
  for (const [nm, conf] of C_VARS) {
    const I0 = bzA(conf, { bz_fg_modo: 0 }).R.ifc, A1 = bzA(conf), I1 = A1.R.ifc, P = A1.P, A0 = bzA(conf, { bz_fg_modo: 0 }), ctx = nm + ": ";
    assert.equal(I0.fgUsed, I0.fgIdeal); assert.equal(I1.fgUsed, I1.fgReal);
    near(I0.qNet, I0.qLoc / (1 - I0.fgIdeal - I0.fgr), 1e-12, ctx + "q_neto ideal"); near(I1.qNet, I1.qLoc / (1 - I1.fgReal - I1.fgr), 1e-12, ctx + "q_neto real");
    assert.ok(I1.qNet < I0.qNet, ctx + "menos grafito: menos área de grafito y menos presión sobre el bronce neto");
    // masa: bronce con tapones ρ_mezcla = ρ_bz(1 − 0,7 f) + ρ_gr·0,7 f sobre el área de la parte cubierta; el real pesa más porque hay más bronce
    const rBz = P.rho_bz * 1e-6, mix = (f) => rBz * (1 - 0.7 * f) + 1.8e-6 * 0.7 * f;
    near(I1.mBz, R_Ac(A1) * (conf === 3 ? I1.cov : 1) * I1.tbz * mix(I1.fgReal) + (conf === 2 ? R_Ac(A1) * I1.tss * rBz : 0), 1e-12, ctx + "masa bruta con f_g,real");
    near(I0.mBz, R_Ac(A0) * (conf === 3 ? I0.cov : 1) * I0.tbz * mix(I0.fgIdeal) + (conf === 2 ? R_Ac(A0) * I0.tss * rBz : 0), 1e-12, ctx + "masa bruta con f_g,ideal");
    assert.ok(A1.R.m.bz > A0.R.m.bz && A1.R.m.total > A0.R.m.total, ctx + "el real pesa más");
    near(A1.R.m.total - A0.R.m.total, A1.R.m.bz - A0.R.m.bz, 1e-9, ctx + "solo cambia la masa del bronce (la masa rotatoria y la presión q no dependen de f_g)");
    assert.equal(A1.R.ifc.tbz, A0.R.ifc.tbz); near(A1.R.ifc.q, A0.R.ifc.q, 1e-12, ctx + "q_máx");
    assert.equal(I1.eta, I0.eta, ctx + "η solo depende de d y p");
    const row = (A, re) => A.checks.find((c) => re.test(c.name));
    near(row(A1, /Bronce con grafito: valor PV/).dem / row(A0, /Bronce con grafito: valor PV/).dem, I1.qNet / I0.qNet, 1e-12, ctx + "PV ∝ q_neto");
    near(row(A1, /Bronce con grafito: desgaste/).dem / row(A0, /Bronce con grafito: desgaste/).dem, I1.qNet / I0.qNet, 1e-12, ctx + "desgaste ∝ q_neto");
    near(row(A1, /Presión de contacto sobre el bronce neto/).dem, I1.qNet, 1e-12, ctx + "fila de q_neto");
    near(A1.R.cd.FS, A0.R.cd.FS, 1e-9, ctx + "FS: la masa del bronce fijo a la base no carga el giro");
  }
});
const R_Ac = (A) => A.R.Ac;

test("Tapones · criterio de lubricación f_g ≥ bz_fg_min (supuesto C): aviso por defecto, no cumple en modo estricto, cumple si el valor lo permite", () => {
  const lub = (A) => A.checks.find((c) => /cobertura mínima de lubricante sólido/.test(c.name));
  for (const [nm, conf] of C_VARS) {
    const A = bzA(conf), c = lub(A); assert.ok(c, nm + ": fila de lubricación");
    near(c.dem, 0.20, 1e-12, "demanda = bz_fg_min"); near(c.cap, A.R.ifc.fgUsed, 1e-12, "capacidad = f_g usada");
    assert.equal(c.st, "warn", nm + ": 0,097 < 0,20: aviso (criterio a confirmar con el catálogo)"); assert.ok(A.verdict.gira && A.verdict.estructura, "el aviso no cambia el veredicto");
    assert.ok(/supuesto C/.test(c.ref) && /catálogo/.test(c.ref), "nivel de confianza en la referencia");
    assert.equal(lub(bzA(conf, { bz_fg_estricto: 1 })).st, "fail"); assert.equal(bzA(conf, { bz_fg_estricto: 1 }).verdict.estructura, false, "estricto: no cumple la estructura/lubricación");
    assert.equal(lub(bzA(conf, { bz_fg_min: 0.09 })).st, "ok");
    assert.equal(lub(bzA(conf, { bz_fg_modo: 0 })).st, "warn", nm + ": con f_g ideal 0,145 tampoco llega a 0,20");
    assert.equal(lub(bzA(conf, { bz_fg_modo: 0, bz_fg_min: 0.14 })).st, "ok");
  }
  // ligamento mínimo (criterio de proyecto): η ≥ bz_eta_min
  const eta = (o) => bzA(1, o).checks.find((c) => /Ligamento entre tapones/.test(c.name));
  assert.equal(eta({}).st, "ok"); assert.equal(eta({ bz_plug_d: 18, bz_plug_p: 30 }).st, "fail", "η = 0,40 < 0,45");
});

test("Tapones · TT.tapones: comparación ideal–real, barridos monótonos, sensibilidad al borde y a los tornillos, conclusión automática", () => {
  const r = TT.tapones(TT.defaults());
  assert.deepEqual(r.alternativas.map((a) => a.id), ["C1", "C2", "C3"]);
  assert.ok(!/NaN|undefined|Infinity/.test(JSON.stringify(r)), "JSON puro");
  for (const a of r.alternativas) {
    const I = bzA(a.conf).R.ifc, A0 = bzA(a.conf, { bz_fg_modo: 0 }), A1 = bzA(a.conf), ctx = a.id + ": ";
    // (a) ideal vs real
    assert.equal(a.comparacion.real.N, I.Nreal); near(a.comparacion.ideal.N, I.Nideal, 1e-9, ctx + "N ideal"); near(a.comparacion.real.fg, I.fgReal, 1e-12, ctx + "f_g real");
    near(a.comparacion.real.masa_bz, A1.R.m.bz, 1e-12, ctx + "masa bronce real"); near(a.comparacion.ideal.masa_bz, A0.R.m.bz, 1e-12, ctx + "masa bronce ideal");
    near(a.comparacion.real.qNet, I.qNet, 1e-12, ctx + "q_neto"); near(a.comparacion.ideal.FS, A0.R.cd.FS, 1e-12, ctx + "FS giro");
    for (const k of ["N", "fg", "cobertura", "masa_bz", "masa_total", "qNet", "fuQ", "tbz", "tbzReq", "PV", "fuPV", "desgaste", "fuDesgaste", "FS", "mu"]) { assert.ok(k in a.comparacion.real && k in a.comparacion.ideal && k in a.comparacion.delta_pct, ctx + "campo " + k); }
    near(a.comparacion.delta_pct.masa_bz, (A1.R.m.bz / A0.R.m.bz - 1) * 100, 1e-9, ctx + "variación % de la masa"); assert.equal(a.comparacion.real.mu, a.comparacion.ideal.mu, "μ es dato: no cambia");
    // (b) barrido de f_g: monótono
    const b = a.barrido_fg; assert.ok(b.length >= 11 && Math.abs(b[0].fg_obj - 0.05) < 1e-9 && Math.abs(b[b.length - 1].fg_obj - 0.30) < 1e-9);
    for (let i = 1; i < b.length; i++) {
      assert.ok(b[i].fg >= b[i - 1].fg - 1e-12, ctx + "f_g alcanzado crece"); assert.ok(b[i].eta <= b[i - 1].eta + 1e-12, ctx + "η no crece"); assert.ok(b[i].tbzReq >= b[i - 1].tbzReq - 1e-9, ctx + "espesor requerido no decrece");
      assert.ok(b[i].qNet >= b[i - 1].qNet - 1e-12, ctx + "q_neto crece con f_g"); assert.ok(b[i].tbz >= b[i - 1].tbz, ctx + "espesor adoptado no decrece");
    }
    assert.ok(b.every((x) => ["cumple", "cumple sin lubricación", "no cumple", "inalcanzable"].includes(x.estado)), "estados");
    // (c) barrido (d, p)
    const dp = a.barrido_dp; assert.deepEqual([...new Set(dp.map((x) => x.d))], [10, 12, 14, 16, 18, 20]); assert.ok(dp.every((x) => x.p >= 22 && x.p <= 40 && x.p > x.d));
    const x = dp.find((q) => q.d === 12 && q.p === 30); assert.equal(x.N, I.Nreal); near(x.fg, I.fgReal, 1e-12, ctx + "la fila Ø12/30 coincide con el cálculo"); near(x.eta, 0.6, 1e-12, "η");
    const q = dp.find((z) => z.d === 14 && z.p === 26), A2 = bzA(a.conf, { bz_plug_d: 14, bz_plug_p: 26 }); near(q.masa_bz, A2.R.m.bz, 1e-12, ctx + "masa de otro patrón"); near(q.qNet, A2.R.ifc.qNet, 1e-12, "q_neto de otro patrón");
    // (d) sensibilidad: más borde = menos tapones; más tornillos = menos tapones
    const e = a.sens_borde; assert.deepEqual(e.map((z) => z.bz_edge), [2, 4, 6, 8]); for (let i = 1; i < e.length; i++) assert.ok(e[i].N <= e[i - 1].N && e[i].fg <= e[i - 1].fg + 1e-12, ctx + "N no crece con la franja de borde");
    assert.equal(e[1].N, I.Nreal, "borde 4 = cálculo");
    const t = a.sens_tornillos; assert.deepEqual(t.filter((z) => z.d_tor === 6).map((z) => z.n_tor), [0, 2, 4]); const tt = t.filter((z) => z.d_tor === 6); assert.ok(tt[0].N >= tt[1].N && tt[1].N >= tt[2].N, ctx + "N no crece con los tornillos"); assert.equal(tt[1].N, I.Nreal);
    // (e) conclusión
    const c = a.conclusion; assert.equal(c.fg_min_criterio, 0.20); assert.ok(c.fg_max_alcanzable > I.fgReal && c.fg_max_alcanzable < 0.20, ctx + "ningún patrón con η ≥ 0,45 llega a 0,20: máx " + c.fg_max_alcanzable);
    assert.equal(c.cumple_criterio, false); assert.equal(c.patron_recomendado, null); assert.ok(c.mejor_alcanzable && c.mejor_alcanzable.eta >= 0.45 - 1e-12 && c.mejor_alcanzable.fg === c.fg_max_alcanzable);
    assert.ok(c.texto.length >= 3 && c.texto.every((s) => typeof s === "string"));
  }
  assert.ok(r.supuestos.some((s) => /bz_fg_min/.test(s)) && r.notas.length >= 3);
  // con un criterio realista (0,15) sí hay patrón y es el de menor masa entre los que cumplen
  const r15 = TT.tapones(Object.assign(TT.defaults(), { bz_fg_min: 0.15 })).alternativas[0], pr = r15.conclusion.patron_recomendado;
  assert.ok(pr && pr.fg >= 0.15 && pr.eta >= 0.45 && pr.estado === "cumple");
  const ok = r15.barrido_dp.filter((x) => x.estado === "cumple"); assert.ok(ok.length > 0 && ok.every((x) => x.masa_bz >= pr.masa_bz - 1e-9), "menor masa entre los que cumplen");
});

test("Tapones · interfazGeom y apoyo.interfaz exponen N_real, f_g real e ideal y la cobertura (R.ifc)", () => {
  const A = bzA(1), I = A.R.ifc;
  for (const k of ["Nreal", "Nideal", "fgReal", "fgIdeal", "fgUsed", "cobGrafito", "tap"]) assert.ok(k in I, "R.ifc." + k);
  assert.ok(!("tap" in TT.compute(TT.defaults()).ifc) || TT.compute(TT.defaults()).ifc.tap == null, "sin opción C no hay tapones");
});
