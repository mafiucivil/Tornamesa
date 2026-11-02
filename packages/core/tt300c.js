/* TT300-C · Núcleo de cálculo de tornamesa hidráulica (accionamiento por cilindro pivotado y uña).
   Unidades: N, mm, MPa (internas); kN, kN·m, kg y bar en la salida.
   Requiere FEA (fea.js) en el ámbito global o vía require. */
const TT = (() => {
  const FEA_ = (typeof FEA !== "undefined") ? FEA : require("./fea.js");
  const G = 9.80665, RHO = 7.85e-6, D2R = Math.PI / 180;

  /* ---------------- Parámetros ---------------- */
  // [id, etiqueta, unidad, valor por defecto, mín, máx, paso, nota]
  const PARAM_GROUPS = [
    { id: "carga", t: "Carga", p: [
      ["W_tf", "Capacidad nominal (WLL)", "tf", 300, 50, 1000, 10],
      ["e", "Excentricidad máx. del CG", "mm", 150, 0, 400, 10],
      ["phi_d", "Factor de carga para resistencias φd", "–", 1.10, 1, 2, 0.05],
      ["D_load", "Diámetro de apoyo de la carga (parrilla)", "mm", 1600, 600, 2000, 50],
    ] },
    { id: "interfaz", t: "Interfaz de giro (acero-acero, grasa grafitada)", p: [
      ["mu_d", "μ estático de diseño", "–", 0.20, 0.05, 0.6, 0.01],
      ["r_ef", "Radio efectivo de fricción de diseño", "mm", 800, 300, 1000, 10],
      ["mu_nom", "μ nominal (grasa limpia)", "–", 0.15, 0.05, 0.6, 0.01],
      ["mu_cont", "μ contaminado", "–", 0.25, 0.05, 0.6, 0.01],
      ["mu_dry", "μ acero seco (referencial)", "–", 0.50, 0.1, 0.9, 0.01],
      ["q_adm", "Presión de contacto admisible", "MPa", 10, 1, 50, 0.5],
      ["FS_min", "FS mínimo del accionamiento (calado / diseño)", "–", 1.25, 1, 3, 0.05],
    ] },
    { id: "mesa", t: "Mesa giratoria (cajón)", p: [
      ["D_top", "Diámetro de la mesa", "mm", 2000, 1000, 4000, 10],
      ["t_top", "Espesor plancha superior", "mm", 20, 6, 60, 1],
      ["t_bot", "Espesor plancha inferior (contacto)", "mm", 16, 6, 60, 1],
      ["h_disc", "Altura total de la mesa", "mm", 190, 60, 400, 5],
      ["rings", "Radios de almas anulares", "mm", "300, 580, 840"],
      ["t_web", "Espesor almas anulares", "mm", 8, 6, 40, 1],
      ["N_rib", "N° de nervios radiales", "–", 14, 4, 56, 1],
      ["t_rib", "Espesor nervios radiales", "mm", 8, 6, 40, 1],
      ["R_rib", "Radio exterior de nervios", "mm", 840, 300, 1900, 5],
      ["D_hub", "Diámetro exterior del cubo", "mm", 300, 150, 600, 10],
      ["w_web", "Filete almas/nervios–planchas (cada lado)", "mm", 6, 3, 16, 1],
    ] },
    { id: "pasadores", t: "Pasadores de empuje (en la mesa)", p: [
      ["N_pin", "N° de pasadores", "–", 28, 8, 72, 1],
      ["d_pin", "Diámetro del pasador", "mm", 95, 30, 160, 5],
      ["R_pin", "Radio del círculo de pasadores", "mm", 930, 400, 1950, 5],
      ["Fy_pin", "Fy pasador (42CrMo4+QT)", "MPa", 650, 235, 1000, 5],
      ["t_pr", "Espesor del anillo perimetral de pasadores (sup. e inf.)", "mm", 35, 10, 80, 1],
    ] },
    { id: "cilindros", t: "Cilindros hidráulicos", p: [
      ["n_cyl", "N° de cilindros (en par)", "–", 2, 1, 4, 1],
      ["D_bore", "Diámetro del émbolo", "mm", 85, 40, 250, 1],
      ["d_rod", "Diámetro del vástago", "mm", 55, 20, 200, 1],
      ["D_body", "Diámetro exterior del cuerpo", "mm", 115, 50, 300, 1],
      ["p_relief", "Presión de alivio (calado)", "bar", 700, 50, 800, 10],
      ["p_alarm", "Presión de alarma / detención", "bar", 600, 50, 800, 10],
      ["p_ret", "Presión de retorno (puerto B)", "bar", 200, 10, 700, 10],
      ["stroke", "Carrera", "mm", 235, 50, 600, 1],
      ["L0", "Longitud ojal-ojal retraído", "mm", 493, 200, 2000, 1],
      ["e_body", "Distancia del eje del ojal trasero al inicio del cuerpo", "mm", 75, 30, 300, 1],
      ["eta_c", "Rendimiento del cilindro (sellos)", "–", 0.95, 0.8, 1, 0.01],
      ["m_cyl", "Masa por cilindro", "kg", 45, 5, 500, 1],
      ["Q_pump", "Caudal de la bomba", "L/min", 1.8, 0.2, 50, 0.1],
    ] },
    { id: "cinematica", t: "Cinemática", p: [
      ["R_eye", "Radio del ojal en la base", "mm", 1360, 500, 3000, 5],
      ["a_eye", "Ángulo del ojal (planta)", "°", 135, 0, 360, 1],
      ["d_dog", "Uña: pasador del vástago → centro del pasador", "mm", 290, 60, 600, 1],
      ["s_free", "Recorrido libre antes de tomar el pasador", "mm", 10, 0, 100, 1],
      ["s_margin", "Margen mínimo de carrera exigido", "mm", 5, 0, 50, 1],
    ] },
    { id: "una", t: "Uña de empuje", p: [
      ["dog_b", "Ancho de la uña (en planta)", "mm", 65, 20, 200, 1],
      ["dog_h", "Alto de la uña (contacto con el pasador)", "mm", 50, 20, 200, 1],
      ["dog_tip", "Ancho de la punta entre pasadores", "mm", 60, 20, 200, 1],
      ["e_off", "Desplazamiento del cuerpo de la uña (+ afuera, − hacia el centro)", "mm", 0, -300, 300, 1],
      ["l_nose", "Largo de la punta sobre la línea de fuerza", "mm", 80, 20, 300, 1],
      ["e_dog", "Excentricidad accidental de la uña", "mm", 10, 0, 50, 1],
      ["Fy_dog", "Fy uña (34CrNiMo6+QT)", "MPa", 800, 235, 1200, 5],
    ] },
    { id: "articulacion", t: "Articulaciones y ménsulas del cilindro", p: [
      ["d_pp", "Diámetro de pasadores de articulación", "mm", 70, 20, 150, 5],
      ["Fy_pp", "Fy pasadores de articulación", "MPa", 650, 235, 1000, 5],
      ["t_ch", "Espesor de mejillas (horquilla)", "mm", 22, 8, 80, 1],
      ["g_ch", "Holgura mejilla-ojal", "mm", 2, 0, 10, 0.5],
      ["b_eye", "Ancho del ojal del cilindro", "mm", 50, 20, 150, 1],
      ["L_ch", "Largo de mejilla de la ménsula (sobre la base)", "mm", 300, 80, 800, 5],
      ["w_br", "Filete mejilla–base", "mm", 14, 4, 25, 1],
      ["n_br", "N° de ménsulas (2 por sentido de giro)", "–", 4, 2, 8, 1],
    ] },
    { id: "base", t: "Base", p: [
      ["B", "Lado de la base cuadrada", "mm", 2200, 1000, 4500, 10],
      ["t_base", "Espesor plancha base", "mm", 16, 6, 60, 1],
      ["t_base_min", "Espesor mínimo de base por planitud (criterio de fabricación)", "mm", 16, 6, 60, 1],
      ["rim_h", "Alto del marco perimetral", "mm", 45, 0, 200, 1],
      ["rim_t", "Espesor del marco perimetral", "mm", 10, 0, 40, 1],
      ["c_lug", "Punto de izaje (a medio lado): distancia al borde", "mm", 50, 30, 600, 5],
      ["phi_lift", "Factor dinámico de izaje", "–", 1.30, 1, 2, 0.05],
      ["q_floor", "Presión admisible de la losa / mats (referencial)", "MPa", 2.0, 0.1, 20, 0.1],
    ] },
    { id: "pivote", t: "Pivote central", p: [
      ["D_piv", "Diámetro del pivote", "mm", 120, 40, 400, 5],
      ["L_bush", "Largo del buje", "mm", 80, 20, 300, 5],
      ["p_bush", "Presión admisible del buje", "MPa", 30, 5, 100, 1],
      ["mu_bush", "μ del buje", "–", 0.20, 0.02, 0.5, 0.01],
      ["e_piv", "Brazo de flexión del pivote", "mm", 40, 5, 200, 1],
      ["Fy_piv", "Fy pivote", "MPa", 650, 235, 1000, 5],
      ["Ch", "Coeficiente sísmico horizontal (0 = no aplica, decisión del mandante)", "–", 0, 0, 1.5, 0.01],
    ] },
    { id: "material", t: "Materiales y normas", p: [
      ["Fy", "Fy acero estructural (ASTM A572 Gr.50)", "MPa", 345, 235, 690, 5],
      ["FEXX", "Resistencia del electrodo FEXX", "MPa", 490, 410, 830, 10],
      ["E", "Módulo de elasticidad", "MPa", 200000, 190000, 210000, 1000],
      ["nu", "Coeficiente de Poisson", "–", 0.30, 0.25, 0.35, 0.01],
      ["Nd", "ASME BTH-1 factor de diseño (Cat. B = 3,0)", "–", 3.0, 2.0, 4.0, 0.5],
      ["kFEA", "Factor de convergencia de malla FEA", "–", 1.15, 1, 1.5, 0.01],
    ] },
    { id: "fatiga", t: "Ciclo de servicio (fatiga)", p: [
      ["turns_yr", "Vueltas completas por año", "–", 50, 0, 10000, 1],
      ["life", "Vida de diseño", "años", 25, 1, 100, 1],
    ] },
  ];

  function defaults() {
    const P = {};
    PARAM_GROUPS.forEach((g) => g.p.forEach((q) => { P[q[0]] = q[3]; }));
    return P;
  }
  function parseRings(s) {
    return String(s).split(/[,; ]+/).map(Number).filter((v) => isFinite(v) && v > 0).sort((a, b) => a - b);
  }

  /* ---------------- Masas ---------------- */
  function masses(P) {
    const rings = parseRings(P.rings);
    const hw = P.h_disc - P.t_top - P.t_bot;
    const Rt = P.D_top / 2, r_hub = P.D_hub / 2, d_bush = P.D_piv + 2 * 15;
    // planchas: disco central + anillo de pasadores (agujeros de pasadores en todo el espesor del anillo)
    const rpr = prIn(P), aRing = Math.PI * (Rt * Rt - rpr * rpr) - P.N_pin * Math.PI / 4 * P.d_pin ** 2;
    const hole_top = P.D_piv + 80;                                       // alojamiento de la tapa retenedora
    const m = {};
    m.top = RHO * ((Math.PI * rpr * rpr - Math.PI / 4 * hole_top ** 2) * P.t_top + aRing * Math.max(P.t_pr, P.t_top));
    m.bot = RHO * ((Math.PI * rpr * rpr - Math.PI / 4 * d_bush ** 2) * P.t_bot + aRing * Math.max(P.t_pr, P.t_bot));
    m.webs = RHO * rings.reduce((s, r) => s + 2 * Math.PI * r * hw * P.t_web, 0);
    const ringsIn = rings.filter((r) => r > r_hub && r < P.R_rib).length;
    m.ribs = RHO * P.N_rib * Math.max(0, P.R_rib - r_hub - ringsIn * P.t_web) * hw * P.t_rib;
    m.hub = RHO * Math.PI / 4 * (P.D_hub ** 2 - d_bush ** 2) * hw;
    m.pins = RHO * P.N_pin * Math.PI / 4 * P.d_pin ** 2 * P.h_disc;
    m.disc = m.top + m.bot + m.webs + m.ribs + m.hub + m.pins;
    m.base = RHO * (P.B * P.B - Math.PI / 4 * P.D_piv ** 2) * P.t_base;
    m.rim = RHO * (4 * P.B - 4 * P.rim_t) * P.rim_h * P.rim_t;
    const bg = bracketGeo(P, kinematics(P));
    const Llug = bg.Llug, tl = 2 * P.t_ch + bg.spacer;
    m.brackets = RHO * P.n_br * (2 * P.t_ch * P.L_ch * bg.H + (bg.Win * Llug - Math.PI / 4 * P.d_pp ** 2) * tl);
    // uña: horquilla (2 orejas) + cuerpo − asiento cilíndrico
    const fw = 2.4 * P.d_pp, tf = forkH(P) - P.b_eye - 2 * P.g_ch;
    const bodyL = Math.max(0, P.d_dog - fw / 2 - P.l_nose), crank = Math.abs(P.e_off) * Math.max(P.dog_b, P.dog_tip);
    m.dogs = RHO * P.n_cyl * ((fw * fw - Math.PI / 4 * P.d_pp ** 2) * tf + (bodyL * P.dog_b + P.l_nose * P.dog_tip + crank - seatArea(P)) * P.dog_h);
    m.pivot = RHO * Math.PI / 4 * P.D_piv ** 2 * (P.t_base + P.h_disc - P.t_top + 3);
    m.cyl = P.n_cyl * P.m_cyl;
    m.total = m.disc + m.base + m.rim + m.brackets + m.dogs + m.pivot + m.cyl;
    return m;
  }
  function bracketGeo(P, K) {
    const half = Math.sin((K && K.ok ? K.swing : 0.1) / 2);
    const Win = P.D_body + 2 * (P.L_ch * half + 10);                    // luz interior entre mejillas
    const H = hAxis(P) + P.b_eye / 2 + P.g_ch + P.t_ch;                 // alto hasta cara superior de la oreja superior
    const spacer = Math.max(0, hAxis(P) - P.b_eye / 2 - P.g_ch - P.t_ch); // suplemento bajo la oreja inferior
    // saliente trasera: desgarro por corte de la oreja superior (2 planos) con F/2 a calado, BTH-1 Fy/(Nd·√3)
    const Fs = Math.PI / 4 * P.D_bore ** 2 * P.p_relief / 10;           // N
    const aReq = (Fs / 2) / (2 * P.t_ch * P.Fy / (P.Nd * Math.sqrt(3)));
    const rear = Math.ceil((P.d_pp / 2 + aReq / 0.85) / 5) * 5;
    const lugF = P.d_pp / 2 + 25;                                        // saliente delantera (sin carga), libre del cuerpo
    return { Win, H, spacer, rear, lugF, Llug: rear + lugF, aReq, Wout: Win + 2 * P.t_ch };
  }
  function seatArea(P) {   // área del asiento cilíndrico R = d_pas/2 + 1 dentro del ancho de la punta
    const Rn = P.d_pin / 2 + 1, yb = Math.min(P.dog_tip / 2, Rn);
    return 2 * (yb / 2 * Math.sqrt(Rn * Rn - yb * yb) + Rn * Rn / 2 * Math.asin(yb / Rn));
  }
  function TT_lugF(P) { return P.d_pp / 2 + 25; }
  function forkH(P) { return P.b_eye + 2 * P.g_ch + 2 * P.t_ch; }       // alto de la horquilla de la uña
  function hAxis(P) { return P.h_disc / 2; }                         // eje del cilindro sobre la base = mitad de la luz del pasador
  function prIn(P) { return Math.max(P.D_hub / 2, P.R_pin - (P.D_top / 2 - P.R_pin)); }   // radio interior del anillo de pasadores
  function pinClear(P) { return P.h_disc - 2 * Math.max(P.t_pr, P.t_top, P.t_bot); }

  /* ---------------- Cinemática ---------------- */
  function kinematics(P) {
    const Re = P.R_eye, R = P.R_pin, d = P.d_dog, pitch = 2 * Math.PI / P.N_pin;
    const dist = (del) => Math.sqrt(Re * Re + R * R - 2 * Re * R * Math.cos(del));
    const arm = (del) => Re * R * Math.sin(del) / dist(del);
    const Leng = P.L0 + P.s_free + d;
    const c = (Re * Re + R * R - Leng * Leng) / (2 * Re * R);
    if (!(Math.abs(c) <= 1)) return { ok: false, msg: "La uña no alcanza el círculo de pasadores con L0 + libre + uña" };
    const de = Math.acos(c), dend = de + pitch;
    const Lend = dist(dend) - d;
    const s_req = Lend - P.L0;
    const pts = [];
    let armMin = Infinity, armMax = 0;
    for (let i = 0; i <= 60; i++) {
      const del = de + pitch * i / 60, a = arm(del);
      armMin = Math.min(armMin, a); armMax = Math.max(armMax, a);
      pts.push({ del, s: dist(del) - d - P.L0, arm: a });
    }
    const chord = 2 * R * Math.sin(pitch / 2);
    // posición del pasador del vástago y dirección del cilindro desde retraído hasta fin del paso
    const cr = (Re * Re + R * R - (P.L0 + d) ** 2) / (2 * Re * R), dr = Math.abs(cr) <= 1 ? Math.acos(cr) : de;
    let RrodMin = Infinity, RrodMax = 0, phMin = Infinity, phMax = -Infinity;
    for (let i = 0; i <= 60; i++) {
      const del = dr + (dend - dr) * i / 60, Dd = dist(del);
      const Pp = [R * Math.cos(-del), R * Math.sin(-del)], E0 = [Re, 0];   // marco local: ojal sobre el eje x
      const u = [(Pp[0] - E0[0]) / Dd, (Pp[1] - E0[1]) / Dd], Rp = [Pp[0] - d * u[0], Pp[1] - d * u[1]];
      RrodMin = Math.min(RrodMin, Math.hypot(Rp[0], Rp[1])); RrodMax = Math.max(RrodMax, Math.hypot(Rp[0], Rp[1]));
      const ph = Math.atan2(u[1], u[0]); phMin = Math.min(phMin, ph); phMax = Math.max(phMax, ph);
    }
    return { ok: true, Re, R, d, pitch, dist, arm, Leng, de, dend, Lend, s_req, margin: P.stroke - s_req, armMin, armMax, pts, chord, gap: chord - P.d_pin,
      dr, RrodMin, RrodMax, swing: phMax - phMin, phMid: (phMax + phMin) / 2 };
  }

  // distancia mínima, durante el empuje, entre el pasador del vástago y el pasador siguiente (+1),
  // y entre los pasadores vecinos (±1) y el eje de la uña (segmento pasador del vástago → pasador tomado)
  function dogClear(Re, R, d, pitch, de, dend) {
    let fork = Infinity, body = Infinity;
    const E0 = [Re, 0];
    for (let i = 0; i <= 40; i++) {
      const del = de + (dend - de) * i / 40;
      const Pp = [R * Math.cos(-del), R * Math.sin(-del)], L = Math.hypot(Pp[0] - E0[0], Pp[1] - E0[1]);
      const u = [(Pp[0] - E0[0]) / L, (Pp[1] - E0[1]) / L], Rp = [Pp[0] - d * u[0], Pp[1] - d * u[1]];
      for (const k of [1, -1]) {
        const a = -(del - k * pitch), Q = [R * Math.cos(a), R * Math.sin(a)];
        if (k === 1) fork = Math.min(fork, Math.hypot(Q[0] - Rp[0], Q[1] - Rp[1]));
        const t = Math.max(0, Math.min(d, (Q[0] - Rp[0]) * u[0] + (Q[1] - Rp[1]) * u[1]));
        body = Math.min(body, Math.hypot(Q[0] - Rp[0] - t * u[0], Q[1] - Rp[1] - t * u[1]));
      }
    }
    return { clrFork: fork, clrBody: body };
  }
  // uña acodada: cuerpo desplazado e_off hacia afuera (lado opuesto al centro) entre la horquilla y la raíz de la punta;
  // la punta (largo l_nose) queda sobre la línea de fuerza. Distancias mínimas a los pasadores vecinos durante el empuje.
  function dogClear2(P, K) {
    const Re = P.R_eye, R = P.R_pin, d = P.d_dog, pitch = 2 * Math.PI / P.N_pin;
    const segDist = (Q, A, B) => {
      const ab = [B[0] - A[0], B[1] - A[1]], L2 = ab[0] ** 2 + ab[1] ** 2;
      const t = Math.max(0, Math.min(1, ((Q[0] - A[0]) * ab[0] + (Q[1] - A[1]) * ab[1]) / (L2 || 1)));
      return Math.hypot(Q[0] - A[0] - t * ab[0], Q[1] - A[1] - t * ab[1]);
    };
    let fork = Infinity, body = Infinity, nose = Infinity, rmin = Infinity;
    for (let i = 0; i <= 40; i++) {
      const del = K.de + (K.dend - K.de) * i / 40;
      const Pp = [R * Math.cos(-del), R * Math.sin(-del)], E0 = [Re, 0], L = Math.hypot(Pp[0] - E0[0], Pp[1] - E0[1]);
      const u = [(Pp[0] - E0[0]) / L, (Pp[1] - E0[1]) / L];
      let n = [-u[1], u[0]];
      const mid = [Pp[0] - d / 2 * u[0], Pp[1] - d / 2 * u[1]];
      if (n[0] * mid[0] + n[1] * mid[1] < 0) n = [-n[0], -n[1]];          // normal hacia afuera (e_off > 0) ; e_off < 0: hacia el centro
      const Rp = [Pp[0] - d * u[0], Pp[1] - d * u[1]], Nr = [Pp[0] - P.l_nose * u[0], Pp[1] - P.l_nose * u[1]];
      const B0 = [Rp[0] + P.e_off * n[0], Rp[1] + P.e_off * n[1]], B1 = [Nr[0] + P.e_off * n[0], Nr[1] + P.e_off * n[1]];
      for (const [A, B] of [[B0, B1], [Rp, B0], [Nr, B1]]) rmin = Math.min(rmin, segDist([0, 0], A, B));
      for (const k of [1, -1, 2, 3]) {
        const a = -(del - k * pitch), Q = [R * Math.cos(a), R * Math.sin(a)];
        if (k === 1) fork = Math.min(fork, Math.hypot(Q[0] - Rp[0], Q[1] - Rp[1]));
        body = Math.min(body, segDist(Q, B0, B1), segDist(Q, Rp, B0), segDist(Q, Nr, B1));
        nose = Math.min(nose, segDist(Q, Nr, Pp));
      }
    }
    return { clrFork: fork, clrBody: body, clrNose: nose, rBodyMin: rmin };
  }

  /* ---------------- Accionamiento ---------------- */
  function compute(P) {
    const m = masses(P);
    const W = P.W_tf * G;                             // kN
    const Wd = (m.disc + m.pivot * 0.5) * G / 1e3;     // kN (mesa + medio pivote)
    const N = W + Wd, ND = P.phi_d * W + Wd;
    const Ro = P.D_top / 2, Ri = P.D_piv / 2 + 15;
    const Ac = Math.PI * (Ro * Ro - Ri * Ri);
    const r_u = 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2);
    const kq = 4 * P.e * Ro / (Ro * Ro + Ri * Ri);
    const q_avg = ND * 1e3 / Ac, q_max = q_avg * (1 + kq), q_min = q_avg * (1 - kq);
    const H_ecc = (mu) => mu * N * P.e * (4 / 3) * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4);   // kN
    const T_piv = (mu) => P.mu_bush * H_ecc(mu) * (P.D_piv / 2) / 1e3;                        // kN·m
    const K = kinematics(P);
    if (K.ok) Object.assign(K, dogClear2(P, K));
    const A = Math.PI / 4 * P.D_bore ** 2, Aann = A - Math.PI / 4 * P.d_rod ** 2;
    const Fstall = A * P.p_relief / 10 / 1e3, Falarm = A * P.p_alarm / 10 / 1e3, Fret = Aann * P.p_ret / 10 / 1e3;
    const torque = (mu, r) => mu * N * r / 1e3 + T_piv(mu);                                   // kN·m
    const Fcyl = (T, armmm) => T * 1e3 / (P.n_cyl * armmm * P.eta_c);                          // kN
    const caseDef = [
      ["nom", "Nominal: grasa grafitada limpia", P.mu_nom, r_u],
      ["dis", "Diseño: μ límite superior, r efectivo", P.mu_d, P.r_ef],
      ["borde", "Borde: μ de diseño con contacto en el borde (r = R)", P.mu_d, Ro],
      ["cont", "Contaminado: arena / película degradada", P.mu_cont, P.r_ef],
      ["seco", "Acero seco, sin lubricación (referencial)", P.mu_dry, r_u],
    ];
    const cases = K.ok ? caseDef.map(([id, name, mu, r]) => {
      const T = torque(mu, r), F = Fcyl(T, K.armMin);
      return { id, name, mu, r, T, F, p: F * 1e3 / A * 10, FS: Fstall / F, turns: F <= Fstall };
    }) : [];
    const cd = cases.find((c) => c.id === "dis");
    const muMax = (r) => K.ok ? (P.n_cyl * Fstall * P.eta_c * K.armMin / 1e3 - T_piv(P.mu_d)) / (N * r / 1e3) : 0;
    const curve = K.ok ? K.pts.map((q) => ({ s: q.s, arm: q.arm, F: cd ? Fcyl(cd.T, q.arm) : 0 })) : [];
    const Vext = P.n_cyl * A * P.stroke, Vret = P.n_cyl * Aann * P.stroke;
    const tCycle = (Vext + Vret) / 1e6 / P.Q_pump;    // min
    // tierra / losa (base delgada: sin reparto, se toma q_max de la interfaz como presión de apoyo)
    const N_tot = ND + (m.total - m.disc) * G / 1e3;
    const g_rigid = N_tot * 1e3 / (P.B * P.B) * (1 + 6 * P.e * Math.SQRT2 / P.B);
    return { m, W, Wd, N, ND, Ro, Ri, Ac, r_u, q_avg, q_max, q_min, H_ecc, T_piv, K, A, Aann, Fstall, Falarm, Fret,
      cases, cd, muMax, curve, tCycle, tRev: tCycle * P.N_pin, Vext, g_rigid, hax: hAxis(P), torque, Fcyl };
  }

  /* ---------------- FEA de la mesa (sector entre nervios) ---------------- */
  function linspaceKeys(keys, h) {
    const out = [keys[0]];
    for (let i = 1; i < keys.length; i++) {
      const a = keys[i - 1], b = keys[i], n = Math.max(1, Math.ceil((b - a) / h));
      for (let k = 1; k <= n; k++) out.push(a + (b - a) * k / n);
    }
    return out;
  }
  function uniqSorted(arr, tol) {
    const s = arr.slice().sort((a, b) => a - b), o = [];
    for (const v of s) if (!o.length || v - o[o.length - 1] > tol) o.push(v);
    return o;
  }
  function discModel(P, R, which, coarse) {
    const alpha = 2 * Math.PI / P.N_rib, r0 = P.D_hub / 2, Rd = P.D_top / 2;
    const hr = Math.max(coarse ? 30 : 18, (Rd - r0) / (coarse ? 28 : 48));
    const rings = parseRings(P.rings).filter((r) => r > r0 && r < Rd);
    const RL = Math.min(P.D_load / 2, Rd);
    const keyR = uniqSorted([r0, ...rings, Math.min(P.R_rib, Rd), P.R_pin - P.d_pin / 2, P.R_pin, P.R_pin + P.d_pin / 2, Rd, which === "top" ? RL : r0]
      .filter((r) => r >= r0 && r <= Rd), 2);
    const rs = linspaceKeys(keyR, hr);
    const pinAng = [];
    for (let k = 0; k < P.N_pin; k++) {
      const a = Math.PI / P.N_pin + 2 * Math.PI * k / P.N_pin;
      if (a >= -1e-9 && a <= alpha + 1e-9) pinAng.push(a);
    }
    const db = (P.d_pin / 2) / P.R_pin;
    const keyT = uniqSorted([0, alpha, ...pinAng, ...pinAng.map((a) => a - db), ...pinAng.map((a) => a + db)].filter((a) => a >= 0 && a <= alpha), 1e-4);
    const ts = linspaceKeys(keyT, Math.max((coarse ? 2.5 : 1.25) * D2R, alpha / (coarse ? 16 : 30)));
    const nT = ts.length, nodes = [], elems = [], pol = [];
    for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) { nodes.push([rs[i] * Math.cos(ts[j]), rs[i] * Math.sin(ts[j])]); pol.push([rs[i], ts[j]]); }
    const id = (i, j) => i * nT + j;
    const q = [], t = which === "top" ? P.t_top : P.t_bot;
    const q_top = P.phi_d * R.W * 1e3 / (Math.PI * RL * RL) * (1 + 4 * P.e / RL);
    for (let i = 0; i < rs.length - 1; i++) for (let j = 0; j < nT - 1; j++) {
      elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
      const rc = (rs[i] + rs[i + 1]) / 2;
      q.push(which === "top" ? (rc <= RL ? q_top : 0) : R.q_max);
    }
    const wFix = new Set(), clamp = [], betaN = [], groups = { ring: rings.map(() => []), rib: [], pin: pinAng.map(() => []), hub: [] };
    const near = (a, b, tol) => Math.abs(a - b) < tol;
    for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) {
      const k = id(i, j), r = rs[i], th = ts[j];
      if (i === 0) { clamp.push(k); groups.hub.push(k); continue; }
      rings.forEach((rr, ri) => { if (near(r, rr, 0.5)) { wFix.add(k); groups.ring[ri].push(k); } });
      if ((j === 0 || j === nT - 1) && r <= P.R_rib + 0.5) { if (!wFix.has(k)) groups.rib.push(k); wFix.add(k); }
      pinAng.forEach((ba, bi) => {
        const x = r * Math.cos(th) - P.R_pin * Math.cos(ba), y = r * Math.sin(th) - P.R_pin * Math.sin(ba);
        if (Math.hypot(x, y) <= P.d_pin / 2 + 0.5) { if (!wFix.has(k)) groups.pin[bi].push(k); wFix.add(k); }
      });
      if (j === 0) betaN.push([k, 0, 1]);
      if (j === nT - 1) betaN.push([k, -Math.sin(alpha), Math.cos(alpha)]);
    }
    return { nodes, pol, elems, q: Float64Array.from(q), t, E: P.E, nu: P.nu, wFix: [...wFix], clamp, betaN, groups, rings, pinAng, alpha, rs, ts, which, q_top };
  }
  const now = () => (typeof performance !== "undefined" ? performance.now() : Date.now());
  function runDisc(P, R, which, coarse) {
    const m = discModel(P, R, which, coarse);
    const t0 = now();
    const r = FEA_.plate(m);
    const ms = now() - t0;
    let vmMax = 0, imax = 0;
    r.el.forEach((e, i) => { if (e.vmGauss > vmMax) { vmMax = e.vmGauss; imax = i; } });
    let wMax = 0; for (const w of r.w) wMax = Math.max(wMax, Math.abs(w));
    const sumS = (arr) => Math.abs(arr.reduce((s, k) => s + r.reac[k], 0));   // suma con signo (rev. m3)
    const ringLine = m.rings.map((rr, i) => sumS(m.groups.ring[i]) / (rr * m.alpha));   // N/mm
    const ribF = sumS(m.groups.rib), ribLine = ribF / (2 * Math.max(1, P.R_rib - P.D_hub / 2));   // N/mm, 2 bordes del sector = 1 nervio
    const pinF = m.groups.pin.map((g) => sumS(g) / 1e3);
    const ec = m.elems[imax].map((k) => m.nodes[k]);
    const cx = ec.reduce((s, p) => s + p[0], 0) / 4, cy = ec.reduce((s, p) => s + p[1], 0) / 4;
    return { model: m, res: r, ms, vmMax, wMax, ringLine, ribLine, pinF, lineMax: Math.max(0, ribLine, ...ringLine),
      Fapp: r.Fapplied / 1e3, Rsum: Math.abs(r.Rsum) / 1e3, maxAt: [Math.hypot(cx, cy), Math.atan2(cy, cx) / D2R], n: m.nodes.length };
  }

  /* ---------------- Flexión global axisimétrica del cajón (placa sándwich, borde libre) ---------------- */
  function globalBending(P, R) {
    const n = 4000, Rd = P.D_top / 2, RL = Math.min(P.D_load / 2, Rd), Ri = R.Ri;
    const qt = P.phi_d * R.W * 1e3 / (Math.PI * RL * RL), qd = R.Wd * 1e3 / (Math.PI * Rd * Rd);
    const qb = R.ND * 1e3 / (Math.PI * (Rd * Rd - Ri * Ri));
    const r = new Float64Array(n), p = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      r[i] = 1e-6 + Rd * i / (n - 1);
      p[i] = (r[i] >= Ri ? qb : 0) - (r[i] <= RL ? qt : 0) - qd;
    }
    const cum = new Float64Array(n), Q = new Float64Array(n);
    for (let i = 1; i < n; i++) cum[i] = cum[i - 1] + 0.5 * (p[i] * r[i] + p[i - 1] * r[i - 1]) * (r[i] - r[i - 1]);
    for (let i = 0; i < n; i++) Q[i] = cum[i] / r[i];
    const Iq = new Float64Array(n), J = new Float64Array(n);
    for (let i = 1; i < n; i++) Iq[i] = Iq[i - 1] + 0.5 * (Q[i] + Q[i - 1]) * (r[i] - r[i - 1]);
    for (let i = 1; i < n; i++) J[i] = J[i - 1] + 0.5 * (Iq[i] * r[i] + Iq[i - 1] * r[i - 1]) * (r[i] - r[i - 1]);
    const psi = new Float64Array(n), dps = new Float64Array(n);
    for (let i = 0; i < n; i++) psi[i] = J[i] / r[i];
    for (let i = 1; i < n - 1; i++) dps[i] = (psi[i + 1] - psi[i - 1]) / (r[i + 1] - r[i - 1]);
    dps[0] = dps[1]; dps[n - 1] = dps[n - 2];
    const C = -(dps[n - 1] + P.nu * psi[n - 1] / Rd) / (1 + P.nu);
    let Mmax = 0, rM = 0, Vmax = 0, rV = 0;
    for (let i = 5; i < n - 5; i++) {
      const ps = psi[i] + C * r[i], dp = dps[i] + C;
      const Mr = dp + P.nu * ps / r[i], Mt = ps / r[i] + P.nu * dp;
      const M = Math.max(Math.abs(Mr), Math.abs(Mt));
      if (M > Mmax) { Mmax = M; rM = r[i]; }
      if (r[i] >= P.D_hub / 2 && r[i] <= P.R_rib) {
        const V = Math.abs(Q[i]) * 2 * Math.PI * r[i];
        if (V > Vmax) { Vmax = V; rV = r[i]; }
      }
    }
    const hc = P.h_disc - (P.t_top + P.t_bot) / 2;
    const imb = Q[n - 1] * 2 * Math.PI * Rd / 1e3;
    return { Mmax, rM, sigTop: Mmax / (P.t_top * hc), sigBot: Mmax / (P.t_bot * hc), Vmax: Vmax / 1e3, rV, imbalance: imb };
  }

  /* ---------------- FEA de izaje de la base (cuarto de placa con simetría) ---------------- */
  function runLift(P, R, coarse) {
    const a = P.B / 2, n = coarse ? 14 : 24, h = a / n;
    const nodes = [], elems = [];
    for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) nodes.push([i * h, j * h]);
    const id = (i, j) => i * (n + 1) + j;
    const Rd = P.D_top / 2;
    const mOther = R.m.disc + R.m.pivot + R.m.dogs + R.m.cyl;            // apoyado sobre la huella de la mesa
    const qDisc = mOther * G / (Math.PI * Rd * Rd);
    const qOwn = (R.m.base + R.m.rim + R.m.brackets) * G / (P.B * P.B);
    const q = [];
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
      const xc = (i + 0.5) * h, yc = (j + 0.5) * h;
      q.push(P.phi_lift * (qOwn + (Math.hypot(xc, yc) <= Rd ? qDisc : 0)));
    }
    // puntos de izaje a medio lado (las esquinas las ocupan las ménsulas): (xl, 0) y (0, xl)
    const xl = a - P.c_lug, pad = Math.max(75, 1.01 * h);       // placa de apoyo del punto de izaje 150 × 150 (mín. un elemento)
    const wFix = [], betaN = [];
    for (let i = 0; i <= n; i++) for (let j = 0; j <= n; j++) {
      const k = id(i, j), x = i * h, y = j * h;
      if ((Math.abs(x - xl) <= pad + 1e-6 && y <= pad + 1e-6) || (Math.abs(y - xl) <= pad + 1e-6 && x <= pad + 1e-6)) wFix.push(k);
      if (i === 0) betaN.push([k, 1, 0]);
      if (j === 0) betaN.push([k, 0, 1]);
    }
    if (!wFix.length) { let best = 0, bd = 1e9; nodes.forEach((p, k) => { const d = Math.hypot(p[0] - xl, p[1] - xl); if (d < bd) { bd = d; best = k; } }); wFix.push(best); }
    const t0 = now();
    const r = FEA_.plate({ nodes, elems, t: P.t_base, E: P.E, nu: P.nu, q: Float64Array.from(q), wFix, betaN });
    let vmMax = 0, wMax = 0;
    r.el.forEach((e) => { vmMax = Math.max(vmMax, e.vmGauss); });
    for (const w of r.w) wMax = Math.max(wMax, Math.abs(w));
    return { nodes, elems, res: r, vmMax, wMax, ms: now() - t0, Fapp: 4 * r.Fapplied / 1e3, Rsum: 4 * Math.abs(r.Rsum) / 1e3, n };
  }

  /* ---------------- Fatiga: AISC 360-22 Apéndice 3, Tabla A-3.1 (SI) ---------------- */
  // Cf en unidades US (ksi) según la tabla; F_SR[MPa] = 6,895·(Cf/n)^(1/k); F_TH en MPa
  const FAT_CAT = { A: [250e8, 165, 3], B: [120e8, 110, 3], C: [44e8, 69, 3], D: [22e8, 48, 3], E: [11e8, 31, 3], "E'": [3.9e8, 18, 3], F: [150e10, 55, 6] };
  function FSR(cat, nCyc) { const [Cf, Fth, k] = FAT_CAT[cat]; return Math.max(6.895 * Math.pow(Cf / Math.max(nCyc, 1), 1 / k), Fth); }

  /* ---------------- Verificaciones ---------------- */
  // kind: "fu" (FU = dem/cap), "geo" (FU con criterio geométrico), "info" (no afecta el veredicto), "pend" (pendiente de dato)
  function verifs(P, R, fea) {
    const out = [];
    const add = (o) => out.push(Object.assign({ kind: "fu" }, o, { fu: o.kind === "info" || o.kind === "pend" ? null : (o.fu != null ? o.fu : o.dem / o.cap) }));
    const K = R.K, Nd = P.Nd, Fy = P.Fy;
    const Fs = R.Fstall;                                   // fuerza de calado por cilindro, kN
    const cd = R.cd || { F: NaN, p: NaN, FS: NaN };
    const cs = (id) => R.cases.find((c) => c.id === id) || { F: NaN, FS: NaN, p: NaN };
    const Fw = (P.FEXX * 0.60) / (1.20 * Nd);              // BTH-1 soldaduras
    const FwA = 0.60 * P.FEXX / 2.0;                       // AISC J2.4 ASD (Ω 2,00), sin aumento direccional

    /* --- Giro --- */
    add({ grp: "Giro", sys: "giro", name: "FS del accionamiento en el caso de diseño", formula: "FS = F_calado / F_dis ≥ FS_min", dem: P.FS_min, cap: cd.FS, unit: "–", ref: "Criterio del proyecto (μ_d, r_ef)" });
    add({ grp: "Giro", sys: "giro", name: "Presión de diseño frente a la alarma", formula: "p_dis = F_dis / A ≤ p_alarma", dem: cd.p, cap: P.p_alarm, unit: "bar", ref: "Criterio de operación" });
    add({ grp: "Giro", sys: "giro", name: "Gira con grasa contaminada", formula: "F_cont ≤ F_calado", dem: cs("cont").F, cap: Fs, unit: "kN", ref: "Criterio del proyecto" });
    add({ grp: "Giro", sys: "giro", name: "Gira con contacto en el borde (r = R)", formula: "F(μ_d, R) ≤ F_calado", dem: cs("borde").F, cap: Fs, unit: "kN", ref: "Revisión independiente M1" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Carrera requerida con margen", formula: "s_libre + ΔL(paso) + margen ≤ carrera", dem: K.ok ? K.s_req + P.s_margin : NaN, cap: P.stroke, unit: "mm", ref: "Cinemática (rev. C3)" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Holgura de la punta de la uña entre pasadores", formula: "cuerda − d_pas ≥ punta + 2·10", dem: P.dog_tip + 20, cap: K.ok ? K.gap : NaN, unit: "mm", ref: "Cinemática" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Contacto de la uña dentro de la luz libre del pasador", formula: "h_uña + 10 ≤ h − 2·t_anillo", dem: P.dog_h + 10, cap: pinClear(P), unit: "mm", ref: "Geometría" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Horquilla de la uña libre del pasador siguiente", formula: "1,2·d_pp + d_pas/2 + 10 ≤ dist. mín. (empuje)", dem: 1.2 * P.d_pp + P.d_pin / 2 + 10, cap: K.ok ? K.clrFork : NaN, unit: "mm", ref: "Geometría (interferencia en planta)" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Cuerpo de la uña (acodada) libre de los pasadores vecinos", formula: "b_uña/2 + d_pas/2 + 10 ≤ dist. mín. al eje del cuerpo", dem: P.dog_b / 2 + P.d_pin / 2 + 10, cap: K.ok ? K.clrBody : NaN, unit: "mm", ref: "Geometría (interferencia en planta)" });
    const ringsAll = parseRings(P.rings), rWeb = ringsAll.length ? Math.max(...ringsAll) + P.t_web / 2 : 0;
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Cuerpo de la uña libre del alma exterior de la mesa", formula: "R_alma + t/2 + b_uña/2 + 10 ≤ r mín. del eje del cuerpo", dem: rWeb + P.dog_b / 2 + 10, cap: K.ok ? K.rBodyMin : NaN, unit: "mm", ref: "Geometría (interferencia en planta)" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Punta de la uña libre de los pasadores vecinos", formula: "punta/2 + d_pas/2 + 10 ≤ dist. mín. al eje de la punta", dem: P.dog_tip / 2 + P.d_pin / 2 + 10, cap: K.ok ? K.clrNose : NaN, unit: "mm", ref: "Geometría (interferencia en planta)" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Orejas de la ménsula libres del cuerpo del cilindro", formula: "d_pp/2 + 25 + 10 ≤ e_cuerpo", dem: TT_lugF(P) + 10, cap: P.e_body, unit: "mm", ref: "Geometría" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Horquilla de la uña entre anillos de pasadores", formula: "b_ojal + 2g + 2t + 2·10 ≤ h − 2·t_anillo", dem: forkH(P) + 20, cap: pinClear(P), unit: "mm", ref: "Geometría (horquilla sobre el borde de la mesa)" });
    const bgv = bracketGeo(P, K), D2 = Math.PI / 180;
    // esquinas de la caja de la ménsula (local: eje x hacia el cilindro), en coordenadas de planta
    let cmax = 0, rmin = Infinity;
    if (K.ok) {
      const aE = P.a_eye * D2, ph = aE + K.phMid, E0 = [P.R_eye * Math.cos(aE), P.R_eye * Math.sin(aE)];
      for (const [lx, ly] of [[-bgv.rear, -bgv.Wout / 2], [-bgv.rear, bgv.Wout / 2], [P.L_ch - bgv.rear, -bgv.Wout / 2], [P.L_ch - bgv.rear, bgv.Wout / 2]]) {
        const X = E0[0] + lx * Math.cos(ph) - ly * Math.sin(ph), Y = E0[1] + lx * Math.sin(ph) + ly * Math.cos(ph);
        cmax = Math.max(cmax, Math.abs(X), Math.abs(Y)); rmin = Math.min(rmin, Math.hypot(X, Y));
      }
    }
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Ménsula del ojal dentro de la base (esquinas de la caja)", formula: "máx |x|,|y| de la caja ≤ B/2 − t_marco − 5", dem: K.ok ? cmax : NaN, cap: P.B / 2 - P.rim_t - 5, unit: "mm", ref: "Geometría" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Ménsula libre de la mesa", formula: "D/2 + 20 ≤ r mín. de la caja", dem: P.D_top / 2 + 20, cap: K.ok ? rmin : NaN, unit: "mm", ref: "Geometría" });
    add({ grp: "Giro", sys: "giro", kind: "geo", name: "Cuerpo del cilindro libre sobre la base", formula: "D_cuerpo/2 + 5 ≤ h_eje", dem: P.D_body / 2 + 5, cap: R.hax, unit: "mm", ref: "Geometría" });
    const Ir = Math.PI * P.d_rod ** 4 / 64, Lext = P.L0 + P.stroke;
    const Pcr = Math.PI ** 2 * P.E * Ir / (Lext * Lext) / 1e3;
    add({ grp: "Giro", sys: "giro", name: "Pandeo del vástago (biarticulado, longitud extendida)", formula: "F_calado ≤ Pcr / 3; Pcr = π²EI/L²", dem: Fs, cap: Pcr / 3, unit: "kN", ref: "Euler, FS 3 (conservador frente a ISO/TS 13725)" });
    add({ grp: "Giro", sys: "giro", kind: "info", name: "Retorno: fuerza disponible en el puerto B", formula: "F_ret = A_anular · p_ret", dem: R.Fret, unit: "kN", ref: "Hidráulica" });
    add({ grp: "Giro", sys: "giro", kind: "info", name: "Tiempo por vuelta", formula: "N_pas · (V_ext + V_ret) / Q", dem: R.tRev, unit: "min", ref: "Hidráulica" });

    /* --- Interfaz y apoyo --- */
    add({ grp: "Interfaz", sys: "est", name: "Presión de contacto máxima", formula: "q = N_D/A · (1 + 4eR/(R²+r²))", dem: R.q_max, cap: P.q_adm, unit: "MPa", ref: "Criterio acero/acero lubricado" });
    add({ grp: "Interfaz", sys: "est", kind: "geo", name: "Sin despegue de la mesa (q_mín ≥ 0)", formula: "1 − 4eR/(R²+r²) ≥ 0", dem: 4 * P.e * R.Ro / (R.Ro ** 2 + R.Ri ** 2), cap: 1, unit: "–", ref: "Núcleo central" });
    add({ grp: "Interfaz", sys: "est", kind: "info", name: "Presión sobre losa / mats bajo la mesa (base delgada, sin reparto)", formula: "σ ≈ q_max ≤ q_losa (verificar por terceros)", dem: R.q_max, cap: P.q_floor, unit: "MPa", ref: "Referencial (rev. M7)" });

    /* --- Mesa --- */
    const sAll = 0.6 * Fy;
    if (fea) {
      const k = P.kFEA;
      add({ grp: "Mesa (FEA)", sys: "est", name: "Plancha superior: σvm local (carga con e)", formula: "MITC4 × k_malla", dem: fea.top.vmMax * k, cap: sAll, unit: "MPa", ref: "AISC 360-22 F11 (0,6Fy), criterio conservador" });
      add({ grp: "Mesa (FEA)", sys: "est", name: "Plancha inferior: σvm local (contacto q_max)", formula: "MITC4 × k_malla", dem: fea.bot.vmMax * k, cap: sAll, unit: "MPa", ref: "AISC 360-22 F11 (0,6Fy), criterio conservador" });
      const gb = fea.glob;
      add({ grp: "Mesa", sys: "est", name: "Plancha superior: global + local", formula: "σ = M_glob/(t·h_c) + σvm_local", dem: gb.sigTop + fea.top.vmMax * k, cap: sAll, unit: "MPa", ref: "Placa sándwich axisimétrica (rev. M2)" });
      add({ grp: "Mesa", sys: "est", name: "Plancha inferior: global + local", formula: "σ = M_glob/(t·h_c) + σvm_local", dem: gb.sigBot + fea.bot.vmMax * k, cap: sAll, unit: "MPa", ref: "Placa sándwich axisimétrica (rev. M2)" });
      const hw = P.h_disc - P.t_top - P.t_bot;
      const tau = gb.Vmax * 1e3 / (P.N_rib * P.t_rib * hw);
      const lam = hw / P.t_rib, lamLim = 2.24 * Math.sqrt(P.E / Fy);
      add({ grp: "Mesa", sys: "est", name: "Corte en nervios radiales", formula: "τ = V/(N·t·h_w) ≤ 0,6Fy/1,50 (h/t ≤ 2,24√(E/Fy))", dem: tau, cap: 0.6 * Fy / (lam <= lamLim ? 1.50 : 1.67), unit: "MPa", ref: "AISC 360-22 G2.1(a), Ec. G2-1" });
      const qv = Math.max(fea.top.lineMax, fea.bot.lineMax);
      const qh = gb.Vmax * 1e3 / (P.N_rib * hw);
      const fw = Math.hypot(qh, qv) / (2 * 0.707 * P.w_web);
      add({ grp: "Mesa", sys: "est", name: "Soldadura alma/nervio–plancha (2 filetes)", formula: "f = √(q_h² + q_v²)/(2·0,707·w) ≤ 0,6FEXX/2,0", dem: fw, cap: FwA, unit: "MPa", ref: "AISC 360-22 J2.4, Ec. J2-4" });
      add({ grp: "Mesa", sys: "est", name: "Fluencia local de almas por carga de línea", formula: "σ = q_v / t ≤ Fy/1,50", dem: qv / Math.min(P.t_web, P.t_rib), cap: Fy / 1.5, unit: "MPa", ref: "AISC 360-22 J10.2" });
      add({ grp: "Mesa (FEA)", sys: "est", kind: "geo", name: "Equilibrio FEA (ΣF = ΣR)", formula: "|ΣF − ΣR| / ΣF ≤ 0,5 %", dem: Math.abs(fea.bot.Fapp - fea.bot.Rsum) / fea.bot.Fapp * 100 + 0.0001, cap: 0.5, unit: "%", ref: "Control numérico" });
    }

    /* --- Tamaño mínimo de filete según espesor de la parte más gruesa --- */
    const wMin = (T) => T <= 6 ? 3 : T <= 12 ? 5 : T <= 20 ? 6 : 8;
    add({ grp: "Base", sys: "est", kind: "geo", name: "Espesor de la plancha base frente al mínimo por planitud", formula: "t_base_mín ≤ t_base", dem: P.t_base_min, cap: P.t_base, unit: "mm", ref: "Criterio de fabricación (planitud 0,20 de la cara de giro)" });
    const Tw = Math.max(P.t_top, P.t_bot), Tb = Math.max(P.t_base, P.t_ch);
    add({ grp: "Soldaduras", sys: "est", kind: "geo", name: "Filete mínimo almas/nervios–planchas", formula: "w_mín(T = " + Tw + ") ≤ w ≤ t_alma", dem: wMin(Tw), cap: Math.min(P.w_web, Math.min(P.t_web, P.t_rib)), unit: "mm", ref: "AWS D1.1/D1.1M:2020, tamaño mínimo de filete" });
    add({ grp: "Soldaduras", sys: "est", kind: "geo", name: "Filete mínimo mejillas–base", formula: "w_mín(T = " + Tb + ") ≤ w ≤ t_mín", dem: wMin(Tb), cap: Math.min(P.w_br, Math.min(P.t_base, P.t_ch)), unit: "mm", ref: "AWS D1.1/D1.1M:2020, tamaño mínimo de filete" });

    /* --- Pasadores de empuje (cadena de empuje a fuerza de calado) --- */
    const tpr = Math.max(P.t_pr, P.t_top, P.t_bot), Ls = P.h_disc - tpr;
    const Mp = Fs * Ls / 4 / 1e3;                                       // kN·m, carga en el centro (máximo)
    const Sp = Math.PI * P.d_pin ** 3 / 32, Ap = Math.PI * P.d_pin ** 2 / 4;
    add({ grp: "Pasadores de empuje", sys: "est", name: "Flexión (biapoyado entre planchas, carga al centro)", formula: "M = F·L/4; σ = M/S ≤ Fy/Nd", dem: Mp * 1e6 / Sp, cap: P.Fy_pin / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3 (Fy/Nd, conservador)" });
    add({ grp: "Pasadores de empuje", sys: "est", name: "Corte (carga junto a una plancha)", formula: "τ = 4F/(3A) ≤ Fy/(Nd·√3)", dem: 4 * Fs * 1e3 / (3 * Ap), cap: P.Fy_pin / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
    add({ grp: "Pasadores de empuje", sys: "est", name: "Aplastamiento en el agujero de la plancha", formula: "σ = F/(d·t_anillo) ≤ 1,25Fy/Nd", dem: Fs * 1e3 / (P.d_pin * tpr), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 (aplastamiento en pasadores)" });
    add({ grp: "Pasadores de empuje", sys: "est", name: "Aplastamiento pasador–uña", formula: "σ = F/(d·h_uña) ≤ 1,25·Fy_mín/Nd", dem: Fs * 1e3 / (P.d_pin * P.dog_h), cap: 1.25 * Math.min(P.Fy_pin, P.Fy_dog) / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });

    /* --- Uña --- */
    const Adog = P.dog_b * P.dog_h;
    add({ grp: "Uña", sys: "est", name: "Cuerpo: compresión + flexión por acodamiento", formula: "σ = F/A·(1 + 6(e_off + e_acc)/b) ≤ Fy/Nd", dem: Fs * 1e3 / Adog * (1 + 6 * (Math.abs(P.e_off) + P.e_dog) / P.dog_b), cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.4 / 3-2.3" });
    add({ grp: "Uña", sys: "est", name: "Punta: compresión + flexión en la raíz del codo", formula: "σ = F/(t·h)·(1 + 6·e_off/t), t = punta", dem: Fs * 1e3 / (P.dog_tip * P.dog_h) * (1 + 6 * Math.abs(P.e_off) / P.dog_tip), cap: P.Fy_dog / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.4 / 3-2.3" });

    /* --- Articulaciones (ojal en la base y pasador del vástago) --- */
    const App = Math.PI * P.d_pp ** 2 / 4, Spp = Math.PI * P.d_pp ** 3 / 32;
    const Mpp = Fs / 2 * (P.t_ch / 2 + P.g_ch + P.b_eye / 4) / 1e3;
    add({ grp: "Articulaciones", sys: "est", name: "Pasador: flexión (horquilla)", formula: "M = F/2·(t/2 + g + b/4); σ ≤ Fy/Nd", dem: Mpp * 1e6 / Spp, cap: P.Fy_pp / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3 / 3-2.3" });
    add({ grp: "Articulaciones", sys: "est", name: "Pasador: corte doble", formula: "τ = (F/2)/A ≤ Fy/(Nd·√3)", dem: Fs / 2 * 1e3 / App, cap: P.Fy_pp / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-2.2" });
    add({ grp: "Articulaciones", sys: "est", name: "Aplastamiento en mejillas", formula: "σ = (F/2)/(d·t) ≤ 1,25Fy/Nd", dem: Fs / 2 * 1e3 / (P.d_pp * P.t_ch), cap: 1.25 * Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-3.3" });
    const bgx = bracketGeo(P, K), aSh = bgx.rear - P.d_pp / 2;
    add({ grp: "Articulaciones", sys: "est", name: "Oreja superior de la ménsula: desgarro por corte tras el agujero", formula: "τ = (F/2)/(2·t·a) ≤ Fy/(Nd·√3), a = saliente − d/2", dem: Fs / 2 * 1e3 / (2 * P.t_ch * aSh), cap: Fy / (Nd * Math.sqrt(3)), unit: "MPa", ref: "ASME BTH-1 §3-3.3 (simplificado, 2 planos de corte)" });
    add({ grp: "Articulaciones", sys: "est", kind: "info", name: "Ojal comercial del cilindro: admitir pasador y carga", formula: "Ø ojal ≥ d_pp; ancho = b_ojal (confirmar con ficha)", dem: P.d_pp, unit: "mm", ref: "Ficha del fabricante" });
    const hax = R.hax;
    const Mch = Fs / 2 * hax / 1e3;
    add({ grp: "Articulaciones", sys: "est", name: "Mejilla de la ménsula: flexión en la base", formula: "σ = (F/2)·h_eje/(t·L²/6) ≤ Fy/Nd", dem: Mch * 1e6 / (P.t_ch * P.L_ch ** 2 / 6), cap: Fy / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
    const aw = 0.707 * P.w_br;
    const fV = Fs * 1e3 / (4 * aw * P.L_ch), fM = Fs * 1e3 * hax / (4 * aw * P.L_ch ** 2 / 6);
    add({ grp: "Articulaciones", sys: "est", name: "Soldadura mejillas–base (4 filetes)", formula: "f = √(fV² + fM²) ≤ 0,60FEXX/(1,20Nd)", dem: Math.hypot(fV, fM), cap: Fw, unit: "MPa", ref: "ASME BTH-1 §3-3.4" });

    /* --- Pivote --- */
    const H = Math.max(R.H_ecc(P.mu_d), P.Ch * R.N);
    add({ grp: "Pivote", sys: "est", name: "Presión en el buje", formula: "p = H/(D·L), H = máx(fricción excéntrica; Ch·N)", dem: H * 1e3 / (P.D_piv * P.L_bush), cap: P.p_bush, unit: "MPa", ref: "Fabricante del buje" });
    add({ grp: "Pivote", sys: "est", name: "Flexión del pivote", formula: "σ = H·e/(πD³/32) ≤ Fy/Nd", dem: H * 1e3 * P.e_piv / (Math.PI * P.D_piv ** 3 / 32), cap: P.Fy_piv / Nd, unit: "MPa", ref: "ASME BTH-1 §3-2.3" });
    if (!(P.Ch > 0)) add({ grp: "Pivote", sys: "est", kind: "info", name: "Caso sísmico: no aplica", formula: "Sin requerimiento sísmico (decisión del mandante, 31-10-2026); si se instala en forma permanente, ingresar Ch", dem: 0, unit: "–", ref: "Decisión del mandante" });

    /* --- Base --- */
    if (fea && fea.lift) {
      add({ grp: "Base", sys: "est", name: "Izaje del conjunto: σvm en la plancha base", formula: "MITC4 × k_malla, φ_izaje", dem: fea.lift.vmMax * P.kFEA, cap: sAll, unit: "MPa", ref: "AISC 360-22 F11 (0,6Fy)" });
      add({ grp: "Base", sys: "est", kind: "geo", name: "Izaje: flecha de la base", formula: "w ≤ B/300", dem: fea.lift.wMax, cap: P.B / 300, unit: "mm", ref: "Criterio del proyecto" });
    }
    add({ grp: "Base", sys: "est", kind: "geo", name: "Punto de izaje fuera de la mesa", formula: "D/2 + 10 + 35 ≤ B/2 − c (huella Ø70)", dem: P.D_top / 2 + 45, cap: P.B / 2 - P.c_lug, unit: "mm", ref: "Geometría" });
    add({ grp: "Base", sys: "est", kind: "geo", name: "Punto de izaje dentro del marco", formula: "t_marco + 35 ≤ c", dem: P.rim_t + 35, cap: P.c_lug, unit: "mm", ref: "Geometría" });
    const mt = R.m.total;
    add({ grp: "Base", sys: "est", kind: "info", name: "WLL requerido por cáncamo (eslinga 4 ramales, 3 efectivas, 60°)", formula: "m·φ / (3·sin 60°)", dem: mt * P.phi_lift / (3 * Math.sin(60 * D2R)) / 1000, unit: "t", ref: "ASME B30.9 (3 ramales efectivos)" });

    /* --- Fatiga --- */
    const nCyc = P.N_pin * P.turns_yr * P.life, nPin = 2 * P.turns_yr * P.life;
    const Fd = cd.F;                                                  // fuerza de operación (rango de tensiones)
    const fat = (name, sig, cat, N) => {
      if (N <= 20000) add({ grp: "Fatiga", sys: "est", kind: "info", name: name + " (N = " + Math.round(N) + " ≤ 20 000)", formula: "Clase de servicio 0: no requiere verificación", dem: N, unit: "ciclos", ref: "ASME BTH-1 §3-4 / AISC 360-22 A-3.1" });
      else add({ grp: "Fatiga", sys: "est", name: name + " (cat. " + cat + ", N = " + Math.round(N) + ")", formula: (cat === "F" ? "Δτ ≤ F_SR = (Cf/N)^0,167 ≥ F_TH" : "Δσ ≤ F_SR = (Cf/N)^0,333 ≥ F_TH"), dem: sig, cap: FSR(cat, N), unit: "MPa", ref: "AISC 360-22 Apéndice 3, Ec. A-3-1, Tabla A-3.1" });
    };
    fat("Pasadores de empuje", Fd * Ls / 4 * 1e3 / Sp, "A", nPin);
    fat("Uña", Fd * 1e3 / Adog * (1 + 6 * (Math.abs(P.e_off) + P.e_dog) / P.dog_b), "A", nCyc);
    fat("Pasadores de articulación", Fd / 2 * (P.t_ch / 2 + P.g_ch + P.b_eye / 4) * 1e3 / Spp, "A", nCyc);
    fat("Pie de soldadura mejilla–base", Fd / 2 * 1e3 * hax / (P.t_ch * P.L_ch ** 2 / 6), "E", nCyc);
    fat("Garganta soldadura mejilla–base (corte)", Math.hypot(Fd * 1e3 / (4 * aw * P.L_ch), Fd * 1e3 * hax / (4 * aw * P.L_ch ** 2 / 6)), "F", nCyc);

    out.forEach((c) => {
      if (c.kind === "info") c.st = "info";
      else if (c.kind === "pend") c.st = "pend";
      else if (!isFinite(c.fu)) c.st = "fail";
      else if (c.kind === "geo" || c.sys === "giro") c.st = c.fu <= 1 ? "ok" : "fail";   // límites con margen propio
      else c.st = c.fu <= 0.9 ? "ok" : c.fu <= 1 ? "warn" : "fail";
    });
    return out;
  }

  /* FEA de la mesa con caché: con apoyos rígidos la solución es lineal en q y, en flexión, σ ∝ q/t².
     Se usa solo en la búsqueda del optimizador; la confirmación final corre una FEA nueva. */
  function discCached(P, R, which, opts) {
    if (!opts.cache) return runDisc(P, R, which, opts.coarse);
    const RL = Math.min(P.D_load / 2, P.D_top / 2);
    const q = which === "top" ? P.phi_d * R.W * 1e3 / (Math.PI * RL * RL) * (1 + 4 * P.e / RL) : R.q_max;
    const t = which === "top" ? P.t_top : P.t_bot;
    const key = which + JSON.stringify([P.N_rib, P.D_hub, P.D_top, P.rings, P.R_rib, P.R_pin, P.d_pin, P.N_pin, P.D_load, P.E, P.nu, !!opts.coarse]);
    let c = opts.cache.get(key);
    if (!c) { c = { q, t, res: runDisc(P, R, which, opts.coarse) }; opts.cache.set(key, c); }
    const kq = q / c.q, ks = kq * (c.t / t) ** 2;
    return Object.assign({}, c.res, { vmMax: c.res.vmMax * ks, lineMax: c.res.lineMax * kq, ringLine: c.res.ringLine.map((v) => v * kq),
      ribLine: c.res.ribLine * kq, Fapp: c.res.Fapp * kq, Rsum: c.res.Rsum * kq, scaled: c.t !== t || c.q !== q });
  }

  /* ---------------- Análisis completo ---------------- */
  function analyze(P, opts) {
    opts = opts || {};
    const R = compute(P);
    let fea = null;
    if (R.K.ok && !opts.noFEA) {
      fea = { top: discCached(P, R, "top", opts), bot: discCached(P, R, "bot", opts), glob: globalBending(P, R), lift: runLift(P, R, opts.coarse) };
    }
    const checks = verifs(P, R, fea);
    const bad = (sys) => checks.filter((c) => c.sys === sys && c.st === "fail");
    const warn = (sys) => checks.filter((c) => c.sys === sys && c.st === "warn");
    const verdict = {
      gira: R.K.ok && bad("giro").length === 0,
      estructura: bad("est").length === 0,
      warnGiro: warn("giro").length, warnEst: warn("est").length,
      pend: checks.filter((c) => c.st === "pend").length,
      fuMax: Math.max(0, ...checks.filter((c) => c.fu != null && isFinite(c.fu) && c.kind === "fu").map((c) => c.fu)),
    };
    return { P, R, fea, checks, verdict };
  }

  return { prIn, pinClear, bracketGeo, forkH, PARAM_GROUPS, defaults, parseRings, masses, kinematics, compute, discModel, runDisc, globalBending, runLift, verifs, analyze, FSR, FAT_CAT, hAxis, G };
})();
if (typeof module !== "undefined") module.exports = TT;
