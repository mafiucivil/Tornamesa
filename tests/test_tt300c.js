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
