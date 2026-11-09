/* TT300-C · Simulación del movimiento del accionamiento (SVG, sin dependencias externas).
   Anima el ciclo empuje → retorno → reenganche con la API de simulación del núcleo (TT): driveAt (fuerzas en θ para cada caso de
   fricción), guidedAt / camAt / camGeo (modo guiado, con la leva de reenganche si opt_cam = 1), pivotGeo / pivotAt (modo pivotado tipo
   KIET, drive_mode = 2), guideGeo/kinematics/chamferGeo/bracketGeo para las cotas del modo guiado, R.pump para las velocidades del
   vástago (caudal de avance y de retorno) y analyze().checks para marcar en rojo las verificaciones de cinemática que fallan.
   La UI solo compone el dibujo (rotación de la mesa, simetrías entre cilindros); no recalcula fuerzas ni cinemática.
   Arquitectura: un «proveedor» por modo entrega el estado en cada instante y su dibujo; los controles, el gráfico y el GIF son comunes. */
const SIM = (() => {
  const D2R = Math.PI / 180;
  const SPEEDS = [0.25, 0.5, 1, 2, 4, 8];
  const IFC_COL = ["#8a94a3", "#9fb8cf", "#e9ecef", "#b07a32"];          // acero-acero, inox (A), UHMW (B), bronce (C)
  const num = (v, d) => (v == null || !isFinite(v)) ? "—" : v.toLocaleString("es-CL", { minimumFractionDigits: d, maximumFractionDigits: d });
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const sentido = () => S.dir > 0 ? "antihorario" : "horario";

  // verificaciones de cinemática que fallan (estáticas): se muestran en todo el ciclo; las del instante las entrega el núcleo
  function fallas(A, re) { return A.checks.filter((c) => c.st === "fail" && (c.sys === "giro" && c.kind === "geo" || re && re.test(c.grp || ""))).map((c) => c.name); }
  // pico de la salida lateral/radial en el retorno: por debajo de esa carrera la uña vuelve detrás del pasador (reenganche)
  function picoRetorno(sUse, uOf) {
    let sPk = 0, uPk = 0;
    for (let i = 0; i <= 240; i++) { const s = sUse * i / 240, u = uOf(s); if (u > uPk + 1e-9) { uPk = u; sPk = s; } }
    return { sPk, uPk };
  }
  const pF = (R, F) => F * 1e3 / R.A * 10;                               // presión del cilindro (bar) = F/A, como en R.cases

  /* ================= modo guiado (drive_mode 1): bancada con ranura T, patín, uña radial con resorte y, si opt_cam, leva de reenganche ================= */
  function guiado(P, A) {
    const R = A.R, K = R.K, ch = TT.chamferGeo(P), bg = TT.bracketGeo(P), cam = TT.camGeo ? TT.camGeo(P) : null;
    const pitch = K.pitch, h = pitch / 2, sUse = Math.min(P.stroke, K.s_req);
    const vExt = R.pump.vExt * 1000, vRet = R.pump.vRet * 1000, tExt = sUse / vExt, tRet = sUse / vRet;   // mm/s y s
    const at = (s, fase, caseId) => (cam ? TT.camAt(P, s, fase) : TT.guidedAt ? TT.guidedAt(P, s, fase, caseId) : null);
    const dTh = at(sUse, "empuje").th + h;                                // giro por carrera (= paso si la carrera alcanza)
    const pk = picoRetorno(sUse, (s) => at(s, "retorno").u);
    const fijas = fallas(A, /Leva de reenganche/);
    const carrera = fijas.filter((n) => /Carrera requerida/.test(n)), siempre = fijas.filter((n) => !/Carrera requerida/.test(n));
    function state(tau, caseId) {
      const o = { pitch, dTh, sUse };
      if (tau < tExt) {
        const s = Math.min(sUse, vExt * tau), g = at(s, "empuje", caseId), contact = s >= P.s_free, d = contact ? TT.driveAt(P, g.th, caseId) : null;
        Object.assign(o, { fase: contact ? "empuje" : "aproximación (carrera libre)", faseId: "empuje", s, thLoc: g.th, rot: g.th + h, u: 0, contact, g });
        if (d) Object.assign(o, { F: d.F, Fp: d.Fp, H: d.H, Rf: d.Rf, Rr: d.Rr, arm: d.arm, ft: d.ft, fr: d.fr, Fguia: Math.max(Math.abs(d.Rf), Math.abs(d.Rr)) });
        o.alerta = [...siempre, ...(s >= sUse - 2 && sUse < K.s_req ? carrera : [])];
      } else {
        const s = Math.max(0, sUse - vRet * (tau - tExt)), g = at(s, "retorno"), reeng = pk.uPk > 0 && s < pk.sPk;
        Object.assign(o, { fase: reeng ? (cam && g.enRampa ? "reenganche: la rampa de la leva devuelve la uña" : "reenganche: el resorte devuelve la uña") : g.u > 0 ? "retorno: la uña sale sobre el pasador siguiente" : "retorno",
          faseId: reeng ? "reenganche" : "retorno", s, thLoc: h, rot: dTh, u: g.u, contact: false, g });
        const al = g.alertas || { choque: g.holgura < -1e-6 };
        o.alerta = [...siempre, ...(al.sincronia ? ["Sincronía de la leva de reenganche (holgura bajo el margen)"] : []), ...(al.choque ? ["Choque de la uña con el pasador siguiente"] : [])];
      }
      o.L = P.L0 + o.s;
      return o;
    }
    const curve = (caseId) => { const out = []; for (let i = 0; i <= 60; i++) { const s = P.s_free + (sUse - P.s_free) * i / 60, F = TT.driveAt(P, at(s, "empuje", caseId).th, caseId).F; out.push({ s, F, p: pF(R, F) }); } return out; };
    return { id: 1, nombre: "Guiado: bancada con ranura T, patín y uña deslizante radial con resorte" + (cam ? " y leva de reenganche positiva" : ""), P, R, K, bg, ch, cam, pitch, tExt, tRet, vExt, vRet, sUse, dTh, state, curve,
      pinBase: () => 180 / P.N_pin * D2R, plan: planGuiado, detail: detailGuiado,
      leva: cam ? `riel-leva con bolsillo y rampa a ${num(cam.alpha_deg, 0)}°, seguidor de rodillo; sincronía ${num(cam.sincronia, 1)} mm` : "" };
  }

  /* ================= modo pivotado tipo KIET (drive_mode 2): ojal de esquina, bloque-uña sobre Q y placa-leva en media luna ================= */
  function pivotado(P, A) {
    const R = A.R, g = TT.pivotGeo ? TT.pivotGeo(P) : null;
    if (!g) return { id: 2, pendiente: true, nombre: "Pivotado tipo KIET (drive_mode = 2)" };
    const sUse = Math.min(P.stroke, g.s_req), vExt = R.pump.vExt * 1000, vRet = R.pump.vRet * 1000, tExt = sUse / vExt, tRet = sUse / vRet;
    const at = (s, fase) => TT.pivotAt(P, s, fase, sentido());
    const th0 = () => at(0, "empuje").th;
    // soporte del ojal E (abierto hacia la mesa): piezas en planta del núcleo (designDrive().pivotado.fabricacion.soporte_E); sin ellas, el cajón
    const sE = ((TT.designDrive(P, R).pivotado || {}).fabricacion || {}).soporte_E || {}, soporteE = ["cilindro1", "cilindro2"].map((c) => (sE[c] && sE[c].piezas || []).filter((q) => q.poligono && !/tapa_inf/.test(q.id)));
    const dTh = Math.abs(TT.pivotAt(P, sUse, "empuje", "antihorario").th - TT.pivotAt(P, 0, "empuje", "antihorario").th);
    const pk = { antihorario: picoRetorno(sUse, (s) => TT.pivotAt(P, s, "retorno", "antihorario").w), horario: picoRetorno(sUse, (s) => TT.pivotAt(P, s, "retorno", "horario").w) };
    const fijas = fallas(A, /[Pp]ivot|[Ll]eva/), carrera = fijas.filter((n) => /Carrera/.test(n)), siempre = fijas.filter((n) => !/Carrera/.test(n));
    // fases del modo pivotado: toma (aproximación y apertura de la rodilla hasta que Q apoya en el canto) → empuje (Q sobre el canto) → retorno
    // (con la subfase de reenganche cuando la placa-guía conduce el bloque-uña a la toma); todo de TT.pivotAt
    function state(tau, caseId) {
      const o = { pitch: g.paso, dTh, sUse };
      if (tau < tExt) {
        const s = Math.min(sUse, vExt * tau), q = at(s, "empuje"), contact = q.arm != null, d = contact ? TT.driveAt(P, q.th_cil1_antihorario, caseId) : null;
        const fase = contact ? "empuje: Q apoyado en el canto de la placa-guía" : s <= P.s_free ? "toma: aproximación (carrera libre)" : "toma: la rodilla se abre hasta que Q apoya en el canto";
        Object.assign(o, { fase, faseId: contact ? "empuje" : "toma", sub: contact ? "" : s <= P.s_free ? "aproximacion" : "rodilla", s, rot: Math.abs(q.th - th0()), contact, q });
        if (d) Object.assign(o, { F: d.F, Fp: d.Fp, H: d.H, arm: d.arm, armEff: d.armEff, ft: d.ft, fr: d.fr, Fleva: q.contactoLeva.F });
        o.alerta = [...siempre, ...(s >= sUse - 2 && sUse < g.s_req ? carrera : [])];
      } else {
        const s = Math.max(0, sUse - vRet * (tau - tExt)), q = at(s, "retorno"), p = pk[sentido()], reeng = p.uPk > 0 && s < p.sPk;
        Object.assign(o, { fase: reeng ? (q.contactoLeva.enRampa ? "retorno · reenganche: la placa-guía devuelve el bloque-uña a la toma" : "retorno · reenganche: el bloque-uña vuelve detrás del pasador") : q.w > 0.5 ? "retorno: el bloque-uña sale sobre el pasador siguiente" : "retorno",
          faseId: "retorno", sub: reeng ? "reenganche" : "", s, rot: dTh, contact: false, q });
        o.alerta = [...siempre, ...(q.alertas.sincronia ? ["Sincronía de la placa-guía (holgura bajo el margen)"] : []), ...(q.alertas.choque ? ["Choque del bloque-uña con el pasador"] : [])];
      }
      o.L = o.q.L; o.phi = o.q.phi_f;
      return o;
    }
    const curve = (caseId) => { const out = []; for (let i = 0; i <= 60; i++) { const s = P.s_free + (sUse - P.s_free) * i / 60, q = TT.pivotAt(P, s, "empuje", "antihorario"); if (q.arm == null) continue; const F = TT.driveAt(P, q.th_cil1_antihorario, caseId).F; out.push({ s, F, p: pF(R, F) }); } return out; };
    return { id: 2, nombre: "Pivotado tipo KIET: cilindro pivotado en el ojal de esquina, bloque-uña con cara R" + (g.bloque && g.bloque.R_cara ? g.bloque.R_cara : "—") + " sobre el pasador Q y placa-guía curva en media luna", P, R, g, pitch: g.paso, tExt, tRet, vExt, vRet, sUse, dTh, state, curve,
      pinBase: () => th0(), plan: planPivot, detail: detailPivot, soporteE, leva: `4 placas-guía curvas (2 por sentido; las del giro horario son la imagen especular, ACC-024): recta + arcos tangentes (G1) de los segmentos del núcleo; el cilindro usa la del sentido elegido` };
  }

  function proveedor(P, A) {
    const modo = TT.driveMode ? TT.driveMode(P) : (P.drive_mode || 1);
    return modo === 2 ? pivotado(P, A) : guiado(P, A);
  }

  /* ================= dibujo ================= */
  const S = { open: false, prov: null, P: null, A: null, t: 0, run: false, speed: 1, dir: 1, n: 3, caso: "nom", last: 0, raf: 0, curS: 0, label: "" };
  const el = (id) => document.getElementById(id);
  const map = (sx, dy) => (x, y) => [sx * x, dy * y];                    // local de la estación → global (planta, y hacia arriba)

  function pinsSvg(pv, rot, X, Y, r, hi) {
    const P = pv.P, N = P.N_pin, o = [], a0 = pv.pinBase();
    for (let k = 0; k < N; k++) {
      const a = a0 + 2 * Math.PI * k / N + rot, x = P.R_pin * Math.cos(a), y = P.R_pin * Math.sin(a);
      o.push(`<circle cx="${X(x)}" cy="${Y(y)}" r="${r(P.d_pin / 2)}" class="sim-pin${hi && hi(x, y) ? " on" : ""}"/>`);
    }
    return o.join("");
  }
  const polySvg = (pts, X, Y, cls) => `<polygon points="${pts.map(([x, y]) => `${X(x)},${Y(y)}`).join(" ")}" class="${cls}"/>`;
  // estación del modo guiado en coordenadas locales (sx = +1, dy = +1) transformadas por m
  function stationSvg(pv, st, m, X, Y, r, alerta) {
    const P = pv.P, K = pv.K, bg = pv.bg, g = st.g, pt = (x, y) => { const [gx, gy] = m(x, y); return `${X(gx)},${Y(gy)}`; };
    const rect = (x0, y0, x1, y1, cls) => `<polygon points="${pt(x0, y0)} ${pt(x1, y0)} ${pt(x1, y1)} ${pt(x0, y1)}" class="${cls}"/>`;
    const circ = (x, y, d, cls) => { const [gx, gy] = m(x, y); return `<circle cx="${X(gx)}" cy="${Y(gy)}" r="${r(d / 2)}" class="${cls}"/>`; };
    const yrp = g.y_rp, xg = P.x_g, ws = P.w_s;
    const o = [];
    o.push(rect(xg - ws / 2 - 20, -K.Y_bed, xg + ws / 2 + 20, K.Y_bed, "sim-bed"));                       // bancada con ranura T
    o.push(rect(xg - bg.Wout / 2, K.y_eye - bg.rear, xg + bg.Wout / 2, K.y_eye + bg.lugF, "sim-brk"));   // ménsula del ojal
    const yBar = K.y_rp0 - 25;
    o.push(rect(xg - P.D_body / 2, K.y_eye, xg + P.D_body / 2, yBar, "sim-cyl"));                       // cuerpo del cilindro
    o.push(rect(xg - P.d_rod / 2, yBar, xg + P.d_rod / 2, yrp, "sim-rod"));                            // vástago
    o.push(circ(xg, K.y_eye, P.d_pp, "sim-pp"));
    o.push(rect(xg - ws / 2, yrp - K.rear, xg + ws / 2, yrp + K.front, "sim-shoe" + (alerta ? " bad" : "")));   // patín
    // leva de reenganche (opt_cam): riel fijo; su canto es el lugar que limita al seguidor (perfil del núcleo, camGeo)
    const cam = pv.cam;
    if (cam) {
      const pr = cam.perfil_y, xo = Math.max(...pr.map((q) => q.x_canto)) + 30;
      o.push(`<polygon points="${pr.map((q) => pt(q.x_canto, q.y)).join(" ")} ${pt(xo, pr[pr.length - 1].y)} ${pt(xo, pr[0].y)}" class="sim-cam${alerta ? " bad" : ""}"/>`);
    }
    // uña: cara de empuje plana, chaflán de retorno en la arista punta–cara trasera, desplazada u hacia afuera (núcleo: y_cara, x_punta)
    const yf = g.y_cara, yb = yf - P.dog_b, tip = g.x_punta, out = K.mouthX + P.L_in + st.u, dx = Math.min(pv.ch.dx, out - tip), dy = Math.min(pv.ch.dy, P.dog_b);
    o.push(`<polygon points="${pt(tip, yf)} ${pt(tip, yb + dy)} ${pt(tip + dx, yb)} ${pt(out, yb)} ${pt(out, yf)}" class="sim-dog${alerta ? " bad" : st.contact ? " on" : ""}"/>`);
    const ym = (yf + yb) / 2, n = 8, x0 = out, x1 = K.pocketEnd, zz = [];
    for (let i = 0; i <= n; i++) zz.push(pt(x0 + (x1 - x0) * i / n, ym + (i % 2 ? 18 : -18) * (i > 0 && i < n ? 1 : 0)));
    o.push(`<polyline points="${zz.join(" ")}" class="sim-spr"/>`);
    if (cam && g.x_seguidor != null) o.push(circ(g.x_seguidor, g.y_seguidor, 2 * Math.max(5, cam.x_canto_toma - cam.x_perno_toma - cam.holgura_toma), "sim-fol"));   // seguidor de rodillo
    o.push(circ(xg, yrp, P.d_pp, "sim-pp"));
    return o.join("");
  }
  /* ---- placa-guía curva: trayecto SVG desde los segmentos del núcleo ({tipo, p0, p1, centro, radio, sentido}) ----
     Arcos «A» con radio, bandera de arco grande y sentido; el sentido de barrido se deduce de la orientación de la transformación
     (X, Y): con la planta dibujada con y hacia arriba (Y invertida), un arco antihorario del modelo se barre con sweep = 0. */
  function segPath(segs, X, Y, rS, cerrar) {
    if (!segs || !segs.length) return "";
    const det = (X(1) - X(0)) * (Y(1) - Y(0)) > 0 ? 1 : -1, d = [], P_ = (p) => `${(+X(p[0])).toFixed(2)} ${(+Y(p[1])).toFixed(2)}`;
    let cur = null;
    segs.forEach((g) => {
      if (!cur || Math.hypot(g.p0[0] - cur[0], g.p0[1] - cur[1]) > 0.01) d.push("M " + P_(g.p0));
      if (g.tipo === "arco" && g.radio > 0 && g.centro) {
        const a0 = Math.atan2(g.p0[1] - g.centro[1], g.p0[0] - g.centro[0]), a1 = Math.atan2(g.p1[1] - g.centro[1], g.p1[0] - g.centro[0]), ccw = g.sentido !== "horario";
        let sp = ccw ? a1 - a0 : a0 - a1; sp = ((sp % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
        const rr = (+rS(g.radio)).toFixed(2);
        d.push(`A ${rr} ${rr} 0 ${sp > Math.PI ? 1 : 0} ${(ccw ? det < 0 : det > 0) ? 0 : 1} ${P_(g.p1)}`);
      } else d.push("L " + P_(g.p1));
      cur = g.p1;
    });
    if (cerrar) d.push("Z");
    return d.join(" ");
  }
  // cara cilíndrica del bloque-uña (radio R_cara, vértice en el extremo de la cara): polilínea con flecha ≤ 0,1 mm, transformada con la pose
  // que el núcleo da a la envolvente rectangular de la cara (q.una.cara ↔ pivotGeo().bloque.local.cara)
  function caraBloque(g, cara) {
    const lc = g.bloque && g.bloque.local && g.bloque.local.cara, Rc = g.bloque ? g.bloque.R_cara : 0;
    if (!lc || !(Rc > 0) || !cara || cara.length !== 4) return cara;
    const ex = [(cara[1][0] - cara[0][0]) / (lc[1][0] - lc[0][0]), (cara[1][1] - cara[0][1]) / (lc[1][0] - lc[0][0])];
    const ey = [(cara[3][0] - cara[0][0]) / (lc[3][1] - lc[0][1]), (cara[3][1] - cara[0][1]) / (lc[3][1] - lc[0][1])];
    const O = [cara[0][0] - ex[0] * lc[0][0] - ey[0] * lc[0][1], cara[0][1] - ex[1] * lc[0][0] - ey[1] * lc[0][1]];
    const T = ([x, y]) => [O[0] + ex[0] * x + ey[0] * y, O[1] + ex[1] * x + ey[1] * y];
    const x0 = Math.min(...lc.map((p) => p[0])), x1 = Math.max(...lc.map((p) => p[0])), h = Math.max(...lc.map((p) => Math.abs(p[1]))), xc = x1 - Rc;
    const gm = Math.asin(Math.min(1, h / Rc)), n = Math.max(8, Math.ceil(2 * gm / (2 * Math.acos(1 - 0.1 / Rc)))), pts = [[x0, -h]];
    for (let i = 0; i <= n; i++) { const a = -gm + 2 * gm * i / n; pts.push([xc + Rc * Math.cos(a), Rc * Math.sin(a)]); }
    pts.push([x0, h]);
    return pts.map(T);
  }
  // modo pivotado: placas-guía curvas, ojales, cilindros y bloques-uña en coordenadas globales (cilindro 2 = simetría central del 1)
  function pivotSvg(pv, st, X, Y, r, alerta, det) {
    const P = pv.P, g = pv.g, q = st.q, neg = (p) => [-p[0], -p[1]], o = [], sen = sentido(), rS = r;
    Object.entries(g.placas).forEach(([k, pl]) => {
      const act = k.endsWith(sen);
      o.push(`<path d="${segPath(pl.segmentos_contorno, X, Y, rS, true)}" class="sim-cam${act ? (alerta ? " bad" : "") : " off"}" data-placa="${k}"/>`);
      if (act && det) {
        (pl.pernos || []).forEach((b) => o.push(`<circle cx="${X(b[0])}" cy="${Y(b[1])}" r="${r((P.pv_db || 16) / 2)}" class="sim-bolt"/>`));
        (pl.pasadores_posicion || []).forEach((b) => o.push(`<circle cx="${X(b[0])}" cy="${Y(b[1])}" r="${r((P.pv_dd || 16) / 2)}" class="sim-dowel"/>`));
      }
    });
    // canto guía y trayectoria del centro de Q por encima del bloque (la placa está bajo el bloque en z: se dibujan como líneas de referencia)
    const top = [];
    Object.entries(g.placas).forEach(([k, pl]) => {
      if (!k.endsWith(sen)) return;
      top.push(`<path d="${segPath(pl.segmentos_canto, X, Y, rS)}" class="sim-canto"/>`);
      if (det) top.push(`<path d="${segPath(pl.segmentos_centro, X, Y, rS)}" class="sim-traj"/>`);
    });
    g.E.forEach((E, i) => {
      const pz = pv.soporteE && pv.soporteE[i];
      if (pz && pz.length) pz.forEach((q) => o.push(polySvg(q.poligono, X, Y, "sim-brk" + (/tapa/.test(q.id) ? " sim-tapa" : ""))));
      else { const b = g.ojalE.lado_cajon / 2; o.push(polySvg([[E[0] - b, E[1] - b], [E[0] + b, E[1] - b], [E[0] + b, E[1] + b], [E[0] - b, E[1] + b]], X, Y, "sim-brk")); }
    });
    [[q.E, q.Q, (p) => p], [neg(q.E), neg(q.Q), neg]].forEach(([E, Q, f], ci) => {
      const L = Math.hypot(Q[0] - E[0], Q[1] - E[1]), u = [(Q[0] - E[0]) / L, (Q[1] - E[1]) / L], t = [-u[1], u[0]], lb = Math.min(L - 30, P.L0 - 30);
      const bar = (a, b, w) => [[a, -1], [b, -1], [b, 1], [a, 1]].map(([s, k]) => [E[0] + s * u[0] + k * w / 2 * t[0], E[1] + s * u[1] + k * w / 2 * t[1]]);
      o.push(polySvg(bar(0, lb, P.D_body), X, Y, "sim-cyl"), polySvg(bar(lb, L, P.d_rod), X, Y, "sim-rod"));
      o.push(`<circle cx="${X(E[0])}" cy="${Y(E[1])}" r="${r(g.ojalE.d / 2)}" class="sim-pp sim-ojal"/>`);
      const on = st.contact || st.sub === "rodilla";
      o.push(polySvg(q.una.cuerpo.map(f), X, Y, "sim-dog sim-blk" + (alerta ? " bad" : on ? " on" : "")), polySvg(caraBloque(g, q.una.cara).map(f), X, Y, "sim-dog sim-cara" + (on ? " on" : "")), polySvg(q.una.cubo.map(f), X, Y, "sim-pp sim-blk"));
      if (ci === 0) o.push(top.join(""));
      // pasador Q: su extremo inferior es el seguidor que recorre el canto de la placa-guía
      o.push(`<circle cx="${X(Q[0])}" cy="${Y(Q[1])}" r="${r(g.pasadorQ.d / 2)}" class="sim-fol sim-q"/>`);
      if (q.contactoLeva && q.contactoLeva.punto) {
        const c = f(q.contactoLeva.punto), apoyo = q.contactoLeva.enCanto;
        o.push(`<line x1="${X(Q[0])}" y1="${Y(Q[1])}" x2="${X(c[0])}" y2="${Y(c[1])}" class="sim-ctl-l${apoyo ? " on" : ""}"/><circle cx="${X(c[0])}" cy="${Y(c[1])}" r="${apoyo ? 3.2 : 2}" class="sim-ct${apoyo ? "" : " off"}"/>`);
        if (det && ci === 0) o.push(`<text x="${(+X(c[0]) + 7).toFixed(1)}" y="${(+Y(c[1]) + 4).toFixed(1)}" class="sim-t sim-tct">${apoyo ? `contacto Q–canto${q.contactoLeva.F > 0 ? " · " + num(q.contactoLeva.F, 1) + " kN" : ""}` : "Q libre del canto"}</text>`);
      }
    });
    return o.join("");
  }

  function planGuiado(pv, st, rot) {
    const P = pv.P, B = P.B, W = 520, sc = W / (B + 200), X = (x) => (W / 2 + x * sc).toFixed(1), Y = (y) => (W / 2 - y * sc).toFixed(1), r = (d) => (d * sc).toFixed(2);
    const pairs = S.dir > 0 ? [[1, 1], [-1, -1]] : [[1, -1], [-1, 1]];
    const al = st.alerta.length > 0;
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${W}" class="sim-svg" id="simPlan" role="img" aria-label="Planta animada">`;
    s += `<rect x="${X(-B / 2)}" y="${Y(B / 2)}" width="${r(B)}" height="${r(B)}" class="sim-base"/>`;
    pairs.forEach(([sx, dy]) => { s += stationSvg(pv, st, map(sx, dy), X, Y, r, al); });
    s += `<circle cx="${X(0)}" cy="${Y(0)}" r="${r(P.D_top / 2)}" class="sim-table"/>`;
    s += `<circle cx="${X(0)}" cy="${Y(0)}" r="${r(P.D_hub / 2)}" class="sim-hub"/>`;
    const ang = rot;                                                       // giro acumulado de la mesa (rad, con signo)
    s += `<line x1="${X(0)}" y1="${Y(0)}" x2="${X(0.9 * P.D_top / 2 * Math.cos(ang))}" y2="${Y(0.9 * P.D_top / 2 * Math.sin(ang))}" class="sim-mark"/>`;
    const cps = st.contact ? pairs.map(([sx, dy]) => map(sx, dy)(P.R_pin * Math.cos(st.thLoc), P.R_pin * Math.sin(st.thLoc))) : [];   // pasador tomado por cada uña
    s += pinsSvg(pv, ang, X, Y, r, (x, y) => cps.some(([cx, cy]) => Math.hypot(x - cx, y - cy) < P.d_pin / 2));
    s += `<rect x="4" y="3" width="${W - 8}" height="18" rx="3" class="sim-tbg"/><text x="8" y="16" class="sim-t">Planta · ${S.dir > 0 ? "giro antihorario" : "giro horario"} · θ = ${num(rot / D2R * S.dir, 3)}°</text></svg>`;
    return s;
  }

  function detailGuiado(pv, st, rot) {
    const P = pv.P, K = pv.K, x0 = K.a_min - 230, x1 = K.pocketEnd + 70, y0 = K.y_pin0 - 270, y1 = K.y_rp1 + K.front + 50;
    const W = 520, sc = W / (x1 - x0), H = (y1 - y0) * sc, dy = S.dir > 0 ? 1 : -1;
    const X = (x) => ((x - x0) * sc).toFixed(1);
    const Yf = (gy) => (dy > 0 ? (y1 - gy) * sc : (gy + y1) * sc).toFixed(1);   // con giro horario la estación se ve reflejada en y
    const r = (d) => (d * sc).toFixed(2), al = st.alerta.length > 0;
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H.toFixed(0)}" class="sim-svg" id="simDet" role="img" aria-label="Detalle de la estación de un cilindro">`;
    s += `<defs><clipPath id="simClip"><rect x="0" y="0" width="${W}" height="${H.toFixed(0)}"/></clipPath></defs><g clip-path="url(#simClip)">`;
    // capa de interfaz bajo la mesa (corona de contacto), con el color de la alternativa
    const ifc = pv.R.ifc, col = IFC_COL[ifc.o] || IFC_COL[0];
    s += `<circle cx="${X(0)}" cy="${Yf(0)}" r="${r(P.D_top / 2)}" fill="${col}" opacity=".55" stroke="none"/>`;
    if (P.opt_wood > 0.5) s += `<circle cx="${X(0)}" cy="${Yf(0)}" r="${r(P.D_top / 2 - 12)}" fill="#8b5a2b" opacity=".25" stroke="none"/>`;
    s += `<circle cx="${X(0)}" cy="${Yf(0)}" r="${r(P.D_top / 2)}" class="sim-table" fill-opacity="0"/>`;
    s += stationSvg(pv, st, map(1, dy), X, Yf, r, al);
    const cp = map(1, dy)(P.R_pin * Math.cos(st.thLoc), P.R_pin * Math.sin(st.thLoc));
    s += pinsSvg(pv, rot, X, Yf, r, (x, y) => st.contact && Math.hypot(x - cp[0], y - cp[1]) < P.d_pin / 2);
    s += `</g><rect x="4" y="3" width="${W - 8}" height="18" rx="3" class="sim-tbg"/><text x="8" y="16" class="sim-t">Detalle de la estación (cilindro del lado +x) · fase: ${esc(st.fase)}</text>`;
    s += `<rect x="4" y="${(H - 34).toFixed(0)}" width="${W - 8}" height="26" rx="4" class="sim-tbg"/><rect x="8" y="${(H - 28).toFixed(0)}" width="14" height="14" fill="${col}" class="sim-sw"/><text x="28" y="${(H - 17).toFixed(0)}" class="sim-t">Interfaz: ${esc(typeof PLANOS !== "undefined" ? PLANOS.ifaceName(P, ifc) : "")}${P.opt_wood > 0.5 ? " · cubierta de madera" : ""} · μ ${num(pv.R.mu.nom, 2)} / ${num(pv.R.mu.d, 2)}</text></svg>`;
    return s;
  }
  function planSvg(pv, st, rot) { return pv.plan(pv, st, rot); }
  function detailSvg(pv, st, rot) { return pv.detail(pv, st, rot); }
  function planPivot(pv, st, rot) {
    const P = pv.P, B = P.B, W = 520, sc = W / (B + 200), X = (x) => (W / 2 + x * sc).toFixed(1), Y = (y) => (W / 2 - y * sc).toFixed(1), r = (d) => (d * sc).toFixed(2);
    const al = st.alerta.length > 0, q = st.q, hitA = (x, y) => st.contact && [q.pasadores.A, [-q.pasadores.A[0], -q.pasadores.A[1]]].some((c) => Math.hypot(x - c[0], y - c[1]) < P.d_pin / 2);
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${W}" class="sim-svg" id="simPlan" role="img" aria-label="Planta animada">`;
    s += `<rect x="${X(-B / 2)}" y="${Y(B / 2)}" width="${r(B)}" height="${r(B)}" class="sim-base"/>`;
    s += `<circle cx="${X(0)}" cy="${Y(0)}" r="${r(P.D_top / 2)}" class="sim-table"/><circle cx="${X(0)}" cy="${Y(0)}" r="${r(P.D_hub / 2)}" class="sim-hub"/>`;
    const a = pv.pinBase() + rot;
    s += `<line x1="${X(0)}" y1="${Y(0)}" x2="${X(0.9 * P.D_top / 2 * Math.cos(a))}" y2="${Y(0.9 * P.D_top / 2 * Math.sin(a))}" class="sim-mark"/>`;
    s += pinsSvg(pv, rot, X, Y, r, hitA);
    s += pivotSvg(pv, st, X, Y, r, al, false);
    s += `<rect x="4" y="3" width="${W - 8}" height="18" rx="3" class="sim-tbg"/><text x="8" y="16" class="sim-t">Planta · ${S.dir > 0 ? "giro antihorario" : "giro horario"} · θ = ${num(rot / D2R * S.dir, 3)}° · φ cilindro 1 = ${num(st.phi / D2R, 1)}°</text></svg>`;
    return s;
  }
  function detailPivot(pv, st, rot) {
    const P = pv.P, g = pv.g, pl = g.placas["1_" + sentido()].contorno, q = st.q;
    // encuadre fijo: placa-leva activa, Q al inicio y al final del empuje y los pasadores tomado y siguiente
    const ext = [TT.pivotAt(P, 0, "empuje", sentido()), TT.pivotAt(P, pv.sUse, "empuje", sentido())].flatMap((z) => [z.Q, z.pasadores.A, z.pasadores.B]);
    const xs = pl.map((p) => p[0]).concat(ext.map((p) => p[0])), ys = pl.map((p) => p[1]).concat(ext.map((p) => p[1]));
    let x0 = Math.min(...xs) - 90, x1 = Math.max(...xs) + 90, y0 = Math.min(...ys) - 90, y1 = Math.max(...ys) + 90;
    if (x1 - x0 < 0.75 * (y1 - y0)) { const c = (x0 + x1) / 2, hw = 0.375 * (y1 - y0); x0 = c - hw; x1 = c + hw; }
    const W = 520, sc = W / (x1 - x0), Hh = Math.min(700, (y1 - y0) * sc), H = Hh;
    if ((y1 - y0) * sc > Hh) { const c = (y0 + y1) / 2, hh = Hh / sc / 2; y0 = c - hh; y1 = c + hh; }
    const X = (x) => ((x - x0) * sc).toFixed(1), Y = (y) => ((y1 - y) * sc).toFixed(1), r = (d) => (d * sc).toFixed(2), al = st.alerta.length > 0;
    const ifc = pv.R.ifc, col = IFC_COL[ifc.o] || IFC_COL[0];
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H.toFixed(0)}" class="sim-svg" id="simDet" role="img" aria-label="Detalle del bloque-uña y la placa-guía curva">`;
    s += `<defs><clipPath id="simClip"><rect x="0" y="0" width="${W}" height="${H.toFixed(0)}"/></clipPath></defs><g clip-path="url(#simClip)">`;
    s += `<circle cx="${X(0)}" cy="${Y(0)}" r="${r(P.D_top / 2)}" fill="${col}" opacity=".55" stroke="none"/>`;
    if (P.opt_wood > 0.5) s += `<circle cx="${X(0)}" cy="${Y(0)}" r="${r(P.D_top / 2 - 12)}" fill="#8b5a2b" opacity=".25" stroke="none"/>`;
    s += `<circle cx="${X(0)}" cy="${Y(0)}" r="${r(P.D_top / 2)}" class="sim-table" fill-opacity="0"/>`;
    s += pinsSvg(pv, rot, X, Y, r, (x, y) => st.contact && Math.hypot(x - q.pasadores.A[0], y - q.pasadores.A[1]) < P.d_pin / 2);
    s += pivotSvg(pv, st, X, Y, r, al, true);
    s += `</g><rect x="4" y="3" width="${W - 8}" height="18" rx="3" class="sim-tbg"/><text x="8" y="16" class="sim-t">Detalle (cilindro 1) · ${esc(st.fase)}</text>`;
    s += `<rect x="4" y="${(H - 34).toFixed(0)}" width="${W - 8}" height="26" rx="4" class="sim-tbg"/><rect x="8" y="${(H - 28).toFixed(0)}" width="14" height="14" fill="${col}" class="sim-sw"/><text x="28" y="${(H - 17).toFixed(0)}" class="sim-t">Interfaz: ${esc(typeof PLANOS !== "undefined" ? PLANOS.ifaceName(P, ifc) : "")}${P.opt_wood > 0.5 ? " · cubierta de madera" : ""} · μ ${num(pv.R.mu.nom, 2)} / ${num(pv.R.mu.d, 2)}</text></svg>`;
    return s;
  }


  function chartSvg(pv) {
    // p = F_cil/A: una sola curva con dos ejes (kN a la izquierda, bar a la derecha)
    const cur = pv.curve(S.caso), W = 360, H = 160, m = { l: 46, r: 50, t: 12, b: 30 }, kp = cur.length && cur[0].F ? cur[0].p / cur[0].F : 1;
    const sMax = Math.max(pv.P.stroke, pv.sUse, ...cur.map((q) => q.s)), Fm = Math.max(...cur.map((q) => q.F)) * 1.15;
    const X = (s) => (m.l + s / sMax * (W - m.l - m.r)).toFixed(1), YF = (F) => (H - m.b - F / Fm * (H - m.t - m.b)).toFixed(1);
    const tr = cur.filter((q) => q.s <= S.curS + 1e-9);
    let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" class="sim-svg" id="simChart" role="img" aria-label="F_cil y p frente a s">`;
    s += `<line x1="${m.l}" y1="${H - m.b}" x2="${W - m.r}" y2="${H - m.b}" class="sim-ax"/><line x1="${m.l}" y1="${m.t}" x2="${m.l}" y2="${H - m.b}" class="sim-ax"/><line x1="${W - m.r}" y1="${m.t}" x2="${W - m.r}" y2="${H - m.b}" class="sim-ax"/>`;
    for (let i = 1; i <= 3; i++) {
      const F = Fm / 1.15 * i / 3, y = YF(F);
      s += `<line x1="${m.l}" y1="${y}" x2="${W - m.r}" y2="${y}" class="sim-grid-l"/><text x="${m.l - 4}" y="${(+y + 4).toFixed(1)}" class="sim-t sim-tF" text-anchor="end">${num(F, 0)}</text><text x="${W - m.r + 4}" y="${(+y + 4).toFixed(1)}" class="sim-t sim-tp">${num(F * kp, 0)}</text>`;
    }
    s += `<polyline points="${cur.map((q) => `${X(q.s)},${YF(q.F)}`).join(" ")}" class="sim-cF ghost"/>`;
    if (tr.length > 1) s += `<polyline points="${tr.map((q) => `${X(q.s)},${YF(q.F)}`).join(" ")}" class="sim-cF"/>`;
    s += `<line x1="${X(pv.P.stroke)}" y1="${m.t}" x2="${X(pv.P.stroke)}" y2="${H - m.b}" class="sim-lim"/>`;
    s += `<text x="${m.l}" y="${H - 14}" class="sim-t">0</text><text x="${W - m.r}" y="${H - 14}" class="sim-t" text-anchor="end">s = ${num(sMax, 0)} mm</text>`;
    s += `<text x="${m.l - 4}" y="${m.t - 2}" class="sim-t sim-tF" text-anchor="end">kN</text><text x="${W - m.r + 4}" y="${m.t - 2}" class="sim-t sim-tp">bar</text>`;
    s += `<text x="${W / 2}" y="${H - 2}" class="sim-t" text-anchor="middle">F_cil (eje izq., kN) y p = F_cil/A (eje der., bar): una sola curva</text></svg>`;
    return s;
  }

  // interfaz · fijación (solo si hay discos de interfaz: en acero-acero no se rotula) · cubierta
  function etiqueta(P, A) {
    if (typeof PLANOS === "undefined") return "";
    const ifc = A.R.ifc, partes = [PLANOS.ifaceName(P, ifc)];
    if (ifc.o) partes.push(PLANOS.fixText(P, ifc));
    partes.push(PLANOS.woodText(P));
    return partes.join(" · ");
  }
  // nombre corto de la alternativa para archivos: modo_interfaz[F2][_madera]
  function altFile(P) {
    const m = (P.drive_mode || 1) === 2 ? "pivotado" : "guiado";
    const i = P.opt_ss ? "A" + (P.fix_mode === 2 ? "F2" : "") : P.opt_uhmw ? "B" : P.opt_bz ? "C" + Math.min(3, Math.max(1, Math.round(P.bz_conf || 1))) : "base";
    return m + "_" + i + (P.opt_wood > 0.5 ? "_madera" : "");
  }

  /* ================= ciclo y controles ================= */
  const period = () => S.prov.tExt + S.prov.tRet;
  const total = () => S.n * period();
  function snapshot() { return snapshotAt(S.t); }
  function snapshotAt(t) {
    const pv = S.prov, T = period(), tt = Math.min(t, total() - 1e-9), k = Math.max(0, Math.floor(tt / T)), done = t >= total() - 1e-9;
    const st = done ? Object.assign(pv.state(T - 1e-9, S.caso), { fase: "fin de las carreras", faseId: "fin" }) : pv.state(tt - k * T, S.caso);
    const rotLoc = done ? S.n * pv.dTh : k * pv.dTh + st.rot;
    return { st, k: done ? S.n : k, done, rot: S.dir * rotLoc, thetaDeg: rotLoc / D2R };
  }
  function render() {
    if (!S.open) return;
    const pv = S.prov, sn = snapshot(), st = sn.st, P = pv.P, R = pv.R, cs = R.cases.find((c) => c.id === S.caso);
    S.curS = sn.done || st.faseId !== "empuje" ? pv.sUse : st.s;            // el gráfico se traza hasta la carrera actual del empuje (de nuevo en cada carrera)
    el("simPlanBox").innerHTML = planSvg(pv, st, sn.rot);
    el("simDetBox").innerHTML = detailSvg(pv, st, sn.rot);
    el("simChartBox").innerHTML = chartSvg(pv);
    const p = st.F != null ? pF(R, st.F) : null, piv = pv.id === 2;
    const row = (k, v, id) => `<span>${k}</span><span${id ? ` id="${id}"` : ""}>${v}</span>`;
    el("simRead").innerHTML = `<div class="sim-fase">Fase: <b id="simFase">${esc(st.fase)}</b></div><div class="kv sim-read">
      ${row("Carrera", `${Math.min(sn.k + (sn.done ? 0 : 1), S.n)} de ${S.n}`)}
      ${row("θ de la mesa", num(sn.thetaDeg, 3) + "°", "simTheta")}
      ${row("Carrera s / largo del cilindro", `${num(st.s, 1)} / ${num(st.L, 0)} mm`)}
      ${piv ? row("Ángulo del cilindro 1 (en planta)", num(st.phi / D2R, 2) + "°") : ""}
      ${row(piv ? "Brazo a(θ) / efectivo" : "Brazo a(θ)", st.contact ? (piv ? `${num(st.arm, 1)} / ${num(st.armEff, 1)} mm` : num(st.arm, 1) + " mm") : "— (sin contacto)")}
      ${row("Fracción tangencial / radial", st.contact ? `${num(st.ft, 4)} / ${num(st.fr, 4)}` : "—")}
      ${row(`F_cil requerida (${cs ? cs.id === "nom" ? "nominal" : "diseño" : ""}, μ ${num(cs ? cs.mu : NaN, 2)})`, st.contact ? `<span class="${st.F > R.Fstall ? "sim-bad" : ""}">${num(st.F, 1)} kN</span>` : "≈ 0 (sin carga)")}
      ${row("Presión", st.contact ? `${num(p, 0)} bar (alivio ${num(P.p_relief, 0)})` : "—")}
      ${piv ? row("Contacto Q–canto (contactoLeva)", st.q.contactoLeva.enCanto ? "Q apoyado en el canto" + (st.q.contactoLeva.enRampa ? " (flanco de reenganche)" : "") : st.q.contactoLeva.enRampa ? "Q conducido por el flanco" : "Q libre del canto", "simContacto") : ""}
      ${piv ? row("Carga H sobre la placa-guía (caso de diseño)", st.contact ? num(st.Fleva, 1) + " kN" : "—") : ""}
      ${piv && st.faseId === "retorno" ? row("Holgura bloque-uña–pasador siguiente", num(st.q.holgura, 1) + " mm") : ""}
      ${piv ? "" : row("Fuerza en la guía (máx. reacción del patín)", st.Fguia != null ? num(st.Fguia, 1) + " kN" : "—")}
      ${row("Tiempo simulado / total", `${num(Math.min(S.t, total()), 1)} / ${num(total(), 1)} s`)}
    </div>
    ${st.alerta.length ? `<div class="msg error" id="simAlerta"><b>Verificación de cinemática que falla en este instante:</b> ${st.alerta.map(esc).join("; ")}</div>` : ""}`;
    const box = el("simBox");
    box.dataset.theta = sn.thetaDeg.toFixed(6); box.dataset.fase = st.faseId; box.dataset.subfase = st.sub || ""; box.dataset.carrera = String(sn.k); box.dataset.fin = sn.done ? "1" : "0";
    el("bSimPlay").textContent = S.run ? "Pausa" : sn.done ? "Repetir" : "Reproducir";
  }
  function loop(ts) {
    if (!S.open) return;
    if (S.run) {
      const dt = S.last ? Math.min(0.1, (ts - S.last) / 1000) : 0;
      S.t = Math.min(total(), S.t + dt * S.speed);
      if (S.t >= total()) S.run = false;
    }
    S.last = ts;
    render();
    S.raf = requestAnimationFrame(loop);
  }
  function stepNext() {                                                 // paso a paso: hasta el próximo cambio de fase (fin de empuje / fin de retorno)
    const T = period(), k = Math.floor(S.t / T + 1e-9), tau = S.t - k * T;
    S.run = false;
    S.t = Math.min(total(), tau < S.prov.tExt - 1e-9 ? k * T + S.prov.tExt : (k + 1) * T);
    render();
  }
  function reset() { S.t = 0; S.last = 0; render(); }

  function header(pv) {
    const P = pv.P, R = pv.R, mu = R.mu;
    return `<div class="kv sim-kv">
      <span>Accionamiento</span><span>${esc(pv.nombre)}</span>
      <span>Interfaz</span><span>${esc(S.label)}</span>
      <span>μ nominal / diseño</span><span>${num(mu.nom, 2)} / ${num(mu.d, 2)}</span>
      ${P.cam_mat != null && (pv.id === 2 || pv.cam) && TT.camFam ? (() => { const f = TT.camFam(P); return `<span>Material de la leva (cam_mat = ${esc(P.cam_mat)}${f.auto ? ", automático" : ""})</span><span>${esc(f.nombre)} · μ ${num(f.mu, 2)}</span>`; })() : ""}
      <span>Paso de la mesa (360°/${P.N_pin})</span><span>${num(pv.pitch / D2R, 3)}°</span>
      <span>Carrera por paso / del cilindro</span><span>${num(pv.sUse, 1)} / ${num(P.stroke, 0)} mm</span>
      <span>Velocidad del vástago avance / retorno</span><span>${num(pv.vExt, 1)} / ${num(pv.vRet, 1)} mm/s (Q ${num(P.Q_pump, 1)} / ${num(R.pump.Qr, 1)} L/min)</span>
      <span>Tiempo de empuje / retorno por carrera</span><span id="simTiempos">${num(pv.tExt, 1)} / ${num(pv.tRet, 1)} s</span>
      <span>Tiempo por vuelta (núcleo, carrera completa)</span><span>${num(R.tRev, 2)} min</span>
      ${pv.leva ? `<span>Guía de reenganche</span><span>${esc(pv.leva)}</span>` : ""}
    </div>`;
  }

  function open(P, A) {
    const modal = el("simModal"); if (!modal) return;
    S.P = P; S.A = A;
    modal.hidden = false; S.open = true;
    const body = el("simBody");
    if (!A) { body.innerHTML = `<div class="msg error">Corrija los datos marcados para simular.</div>`; return; }
    const pv = proveedor(P, A);
    if (pv.pendiente) {
      body.innerHTML = `<div class="msg warn" id="simPend"><b>${esc(pv.nombre)}:</b> la simulación de este modo espera las funciones de geometría por θ del núcleo (ojal de esquina, bloque-uña y placa-leva). No se dibuja una cinemática que el núcleo no calcula.</div>`;
      el("simBox").dataset.fin = "pendiente"; return;
    }
    S.prov = pv;
    S.label = etiqueta(P, A);
    body.innerHTML = `${header(pv)}
      <div class="sim-ctl">
        <button class="pri" id="bSimPlay">Reproducir</button><button id="bSimStep">Paso a paso</button><button id="bSimReset">Reiniciar</button><button id="bSimGif" title="GIF animado de la planta y el detalle con las carreras, el sentido y la velocidad elegidos">Exportar GIF</button>
        <label>Velocidad <select id="simSpeed">${SPEEDS.map((v) => `<option value="${v}"${v === S.speed ? " selected" : ""}>×${num(v, v < 1 ? 2 : 0)}</option>`).join("")}</select></label>
        <label>Sentido <select id="simDir"><option value="1"${S.dir > 0 ? " selected" : ""}>antihorario</option><option value="-1"${S.dir < 0 ? " selected" : ""}>horario</option></select></label>
        <label>Carreras <input id="simN" type="number" min="1" max="${P.N_pin}" step="1" value="${S.n}"></label>
        <label>Fricción <select id="simCaso"><option value="nom"${S.caso === "nom" ? " selected" : ""}>nominal</option><option value="dis"${S.caso === "dis" ? " selected" : ""}>diseño</option></select></label>
      </div>
      <div class="sim-gif" id="simGif"></div>
      <div class="sim-grid"><div id="simPlanBox"></div><div id="simDetBox"></div></div>
      <div class="sim-grid"><div id="simRead"></div><div id="simChartBox"></div></div>
      <div class="note">Geometría, cinemática y fuerzas del núcleo: ${pv.id === 2 ? "pivotGeo (placas-guía curvas: segmentos_contorno, segmentos_canto y segmentos_centro dibujados como arcos SVG) y pivotAt (ojal E, pasador Q, bloque-uña con cara R" + (pv.g.bloque ? pv.g.bloque.R_cara : "") + ", contactoLeva)" : "guidedAt" + (pv.cam ? ", camGeo y camAt (leva de reenganche)" : "") + ", guideGeo y chamferGeo"}, driveAt (F_cil del caso de fricción elegido) y R.pump (tiempos). Ambos cilindros trabajan en paralelo; el detalle muestra ${pv.id === 2 ? "el cilindro 1" : "el del lado +x"}.</div>`;
    el("bSimPlay").onclick = () => { if (S.t >= total() - 1e-9) reset(); S.run = !S.run; S.last = 0; render(); };
    el("bSimStep").onclick = stepNext;
    el("bSimReset").onclick = () => { S.run = false; reset(); };
    el("bSimGif").onclick = () => { const b = el("bSimGif"); b.disabled = true; exportGif().catch((err) => { el("simGif").innerHTML = `<div class="msg error">No se pudo generar el GIF: ${esc(err.message)}</div>`; }).then(() => { b.disabled = false; }); };
    el("simSpeed").onchange = (e) => { S.speed = parseFloat(e.target.value); };
    el("simDir").onchange = (e) => { S.dir = parseInt(e.target.value, 10); reset(); };
    el("simN").onchange = (e) => { S.n = Math.max(1, Math.min(P.N_pin, Math.round(parseFloat(e.target.value) || 1))); e.target.value = S.n; reset(); };
    el("simCaso").onchange = (e) => { S.caso = e.target.value; render(); };
    S.run = false; reset();
    cancelAnimationFrame(S.raf); S.last = 0; S.raf = requestAnimationFrame(loop);
  }
  function close() { const m = el("simModal"); if (m) m.hidden = true; S.open = false; S.run = false; cancelAnimationFrame(S.raf); }
  function init() {
    const c = el("bSimClose"); if (c) c.onclick = close;
    const m = el("simModal"); if (m) m.addEventListener("click", (e) => { if (e.target === m) close(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && S.open) close(); });
  }
  /* ================= exportación a GIF (GIF89a inline: paleta global por popularidad, LZW, bloque NETSCAPE de bucle) ================= */
  const GIF = (() => {
    // paleta global de 256 colores: los más frecuentes (5 bits por canal) de cuadros de muestra + colores fijos del tema
    function paleta(samples, fijos) {
      const cnt = new Map(), sum = new Map();
      const add = (r, g, b, w) => { const k = (r >> 3) << 10 | (g >> 3) << 5 | (b >> 3); cnt.set(k, (cnt.get(k) || 0) + w); const s = sum.get(k) || [0, 0, 0, 0]; s[0] += r * w; s[1] += g * w; s[2] += b * w; s[3] += w; sum.set(k, s); };
      samples.forEach((d) => { for (let i = 0; i < d.length; i += 4) add(d[i], d[i + 1], d[i + 2], 1); });
      const pal = [], seen = new Set();
      fijos.forEach(([r, g, b]) => { const k = (r >> 3) << 10 | (g >> 3) << 5 | (b >> 3); if (!seen.has(k) && pal.length < 256) { seen.add(k); pal.push([r, g, b]); } });
      [...cnt.entries()].sort((a, b) => b[1] - a[1]).forEach(([k]) => { if (!seen.has(k) && pal.length < 256) { seen.add(k); const s = sum.get(k); pal.push([Math.round(s[0] / s[3]), Math.round(s[1] / s[3]), Math.round(s[2] / s[3])]); } });
      while (pal.length < 256) pal.push([0, 0, 0]);
      const lut = new Uint8Array(32768);                                  // color de 15 bits → índice más cercano
      for (let k = 0; k < 32768; k++) {
        const r = (k >> 10 & 31) * 8 + 4, g = (k >> 5 & 31) * 8 + 4, b = (k & 31) * 8 + 4;
        let best = 0, bd = Infinity;
        for (let j = 0; j < 256; j++) { const p = pal[j], d = 2 * (r - p[0]) ** 2 + 4 * (g - p[1]) ** 2 + 3 * (b - p[2]) ** 2; if (d < bd) { bd = d; best = j; } }
        lut[k] = best;
      }
      return { pal, lut };
    }
    function indices(d, lut) { const n = d.length >> 2, out = new Uint8Array(n); for (let i = 0, j = 0; i < n; i++, j += 4) out[i] = lut[(d[j] >> 3) << 10 | (d[j + 1] >> 3) << 5 | (d[j + 2] >> 3)]; return out; }
    // LZW de GIF (código mínimo 8, tabla de 4096 con código de limpieza al llenarse)
    function lzw(px) {
      const out = [], tab = new Int32Array(4096 * 256), clear = 256, eoi = 257;
      let size = 9, next = 258, cur = 0, shift = 0;
      const emit = (c) => { cur |= c << shift; shift += size; while (shift >= 8) { out.push(cur & 255); cur >>>= 8; shift -= 8; } };
      emit(clear);
      let code = px[0];
      for (let i = 1; i < px.length; i++) {
        const k = px[i], key = code * 256 + k, v = tab[key];
        if (v) { code = v - 1; continue; }
        emit(code);
        if (next === 4096) { emit(clear); tab.fill(0); size = 9; next = 258; }
        else { if (next >= 1 << size) size++; tab[key] = next + 1; next++; }
        code = k;
      }
      emit(code); emit(eoi);
      if (shift > 0) out.push(cur & 255);
      return out;
    }
    function encode(w, h, pal, frames) {                                 // frames: [{x, y, w, h, px, delay (cs)}]
      const b = [], u16 = (v) => b.push(v & 255, v >> 8 & 255), str = (s) => { for (const c of s) b.push(c.charCodeAt(0)); };
      str("GIF89a"); u16(w); u16(h); b.push(0xF7, 0, 0);
      pal.forEach((c) => b.push(c[0], c[1], c[2]));
      b.push(0x21, 0xFF, 11); str("NETSCAPE2.0"); b.push(3, 1, 0, 0, 0);     // bucle infinito
      const parts = [new Uint8Array(b)];
      frames.forEach((f) => {
        const hb = [0x21, 0xF9, 4, 0x04, f.delay & 255, f.delay >> 8 & 255, 0, 0, 0x2C, f.x & 255, f.x >> 8, f.y & 255, f.y >> 8, f.w & 255, f.w >> 8, f.h & 255, f.h >> 8, 0, 8];
        const data = lzw(f.px), blk = new Uint8Array(data.length + Math.ceil(data.length / 255) + 1);
        let o = 0;
        for (let i = 0; i < data.length; i += 255) { const n = Math.min(255, data.length - i); blk[o++] = n; for (let j = 0; j < n; j++) blk[o++] = data[i + j]; }
        blk[o++] = 0;
        parts.push(new Uint8Array(hb), blk.subarray(0, o));
      });
      parts.push(new Uint8Array([0x3B]));
      return parts;
    }
    return { paleta, indices, encode, lzw };
  })();

  // hoja de estilo autónoma para rasterizar los SVG fuera de la página: reglas .sim-* y svg con las variables del tema resueltas
  function estiloSvg() {
    const cs = getComputedStyle(document.documentElement), vars = ["--bg", "--panel", "--ink", "--ink2", "--line", "--soft", "--acc", "--ok", "--okbg", "--warn", "--warnbg", "--fail", "--failbg", "--info", "--infobg", "--pend", "--pendbg", "--steel", "--load", "--sans", "--mono"];
    const decl = vars.map((v) => `${v}:${cs.getPropertyValue(v).trim()}`).join(";");
    let rules = "";
    for (const sh of document.styleSheets) { let rs; try { rs = sh.cssRules; } catch (e) { continue; } for (const r of rs) if (r.selectorText && /sim-|^svg/.test(r.selectorText)) rules += r.cssText + "\n"; }
    return `<style>svg{${decl}}\n${rules}</style>`;
  }
  function rasterSvg(svg, css) {
    const src = svg.replace(/^<svg([^>]*)>/, (m0, a) => `<svg${a}>${css}`);
    return new Promise((res, rej) => { const im = new Image(), url = URL.createObjectURL(new Blob([src], { type: "image/svg+xml" })); im.onload = () => { URL.revokeObjectURL(url); res(im); }; im.onerror = () => { URL.revokeObjectURL(url); rej(new Error("no se pudo rasterizar el SVG")); }; im.src = url; });
  }
  // instantes de los cuadros: más densos en el retorno (rápido) para ver la salida de la uña y el reenganche
  function instantes() {
    const pv = S.prov, T = period(), ts = [], nE = 28, nR = 36;
    for (let k = 0; k < S.n; k++) {
      for (let i = 0; i < nE; i++) ts.push(k * T + pv.tExt * i / nE);
      for (let i = 0; i < nR; i++) ts.push(k * T + pv.tExt + pv.tRet * i / nR);
    }
    ts.push(total());
    return ts;
  }
  async function exportGif(opt) {
    opt = opt || {};
    if (!S.prov || S.prov.pendiente) throw new Error("no hay simulación que exportar");
    const run0 = S.run; S.run = false;
    const prog = (txt, f) => { const g = el("simGif"); if (g) g.innerHTML = `<div class="busy">${esc(txt)}</div><div class="prog"><i style="width:${Math.round(100 * f)}%"></i></div>`; };
    const css = estiloSvg(), W = 900, pad = 6, head = 84, colW = (W - 3 * pad) / 2;
    const ts = instantes(), pv = S.prov, alt = `${pv.nombre.split(":")[0]} · ${S.label}`;
    const cvs = document.createElement("canvas"), cx = cvs.getContext("2d", { willReadFrequently: true });
    const cssv = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim() || "#fff";
    let H = 0;
    const curS0 = S.curS;
    const lineas = (txt, maxW, maxN) => {                                 // parte el rótulo en líneas que caben en el ancho del GIF
      const out = []; let cur = "";
      for (const w of txt.split(" ")) { const tr = cur ? cur + " " + w : w; if (cx.measureText(tr).width <= maxW || !cur) cur = tr; else { out.push(cur); cur = w; } }
      out.push(cur);
      if (out.length > maxN) { out.length = maxN; out[maxN - 1] += " …"; }
      return out;
    };
    async function cuadro(t) {
      const sn = snapshotAt(t), st = sn.st;
      const im1 = await rasterSvg(planSvg(pv, st, sn.rot), css), im2 = await rasterSvg(detailSvg(pv, st, sn.rot), css);
      const h1 = colW * im1.height / im1.width, h2 = colW * im2.height / im2.width;
      if (!H) { H = Math.round(head + Math.max(h1, h2) + pad); cvs.width = W; cvs.height = H; }
      cx.fillStyle = cssv("--bg"); cx.fillRect(0, 0, W, H);
      cx.fillStyle = cssv("--ink"); cx.font = "600 14px " + cssv("--sans"); cx.textBaseline = "top";
      lineas(`TT300-C · ${alt}`, W - 2 * pad - 4, 2).forEach((ln, j) => cx.fillText(ln, pad + 2, 5 + 18 * j));
      cx.font = "13px " + cssv("--sans");
      cx.fillText(`θ = ${num(sn.thetaDeg, 2)}° · carrera ${Math.min(sn.k + (sn.done ? 0 : 1), S.n)} de ${S.n} · ${S.dir > 0 ? "antihorario" : "horario"} · fase: ${st.fase} · t = ${num(Math.min(t, total()), 1)} s de ${num(total(), 1)} s (×${num(S.speed, S.speed < 1 ? 2 : 0)})`, pad + 2, 44);
      if (st.alerta.length) { cx.fillStyle = cssv("--fail"); cx.fillText(lineas("Verificación que falla: " + st.alerta.join("; "), W - 2 * pad - 4, 1)[0], pad + 2, 62); }
      cx.drawImage(im1, pad, head, colW, h1); cx.drawImage(im2, 2 * pad + colW, head, colW, h2);
      return cx.getImageData(0, 0, W, H).data;
    }
    // paleta global: cuadros de muestra (inicio, empuje con contacto, retorno sobre el pasador, fin) + colores fijos del tema y de las interfaces
    prog("Preparando la paleta…", 0.02);
    const hex = (c) => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
    const muestras = [];
    for (const t of [0, buscarFase("toma"), buscarFase("empuje"), buscarFase("retorno"), buscarFase("reenganche"), total()]) if (t != null) muestras.push(await cuadro(t));
    const fij = ["--bg", "--panel", "--ink", "--ink2", "--line", "--soft", "--acc", "--ok", "--fail", "--failbg", "--load", "--steel", "--pend", "--pendbg", "--infobg"]
      .map((v) => { cx.fillStyle = cssv(v); const c = cx.fillStyle; return c.startsWith("#") ? hex(c) : [0, 0, 0]; }).concat(IFC_COL.map(hex));
    const pal = GIF.paleta(muestras, fij);
    const frames = [];
    for (let i = 0; i < ts.length; i++) {
      frames.push({ px: GIF.indices(await cuadro(ts[i]), pal.lut), t: ts[i] });
      prog(`Rasterizando el cuadro ${i + 1} de ${ts.length}…`, 0.05 + 0.7 * (i + 1) / ts.length);
      if (i % 4 === 3) await new Promise((r) => setTimeout(r, 0));
    }
    let prev = null;
    S.curS = curS0;
    // duración de cada cuadro proporcional al tiempo real a la velocidad elegida (centésimas, mínimo 2); el último se mantiene 1,5 s
    const out = [];
    let acc = 0;
    for (let i = 0; i < frames.length; i++) {
      const tEnd = i + 1 < frames.length ? frames[i + 1].t : frames[i].t + 1.5 * S.speed, want = Math.round(tEnd / S.speed * 100);
      let dl = Math.max(2, want - acc); acc += dl;
      // solo el rectángulo que cambia respecto del cuadro anterior (disposición «no descartar»)
      const f = frames[i];
      if (prev) {
        let x0 = W, y0 = H, x1 = -1, y1 = -1;
        for (let y = 0, o = 0; y < H; y++) for (let x = 0; x < W; x++, o++) if (f.px[o] !== prev[o]) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
        if (x1 < 0) { out[out.length - 1].delay += dl; prev = f.px; continue; }
        const w = x1 - x0 + 1, h = y1 - y0 + 1, sub = new Uint8Array(w * h);
        for (let y = 0; y < h; y++) sub.set(f.px.subarray((y0 + y) * W + x0, (y0 + y) * W + x0 + w), y * w);
        out.push({ x: x0, y: y0, w, h, px: sub, delay: dl });
      } else out.push({ x: 0, y: 0, w: W, h: H, px: f.px, delay: dl });
      prev = f.px;
    }
    prog(`Codificando ${out.length} cuadros (LZW)…`, 0.75);
    await new Promise((r) => setTimeout(r, 0));
    const parts = GIF.encode(W, H, pal.pal, out), blob = new Blob(parts, { type: "image/gif" });
    const nombre = `TT300-C_simulacion_${altFile(pv.P)}.gif`;
    if (S.gifUrl) URL.revokeObjectURL(S.gifUrl);
    S.gifUrl = URL.createObjectURL(blob);
    const g = el("simGif");
    if (g) g.innerHTML = `<div class="msg ok" id="simGifOk">GIF listo: ${out.length} cuadros, ${W} × ${H} px, ${num(blob.size / 1048576, 2)} MB · <a href="${S.gifUrl}" download="${esc(nombre)}">${esc(nombre)}</a></div><img id="simGifPrev" src="${S.gifUrl}" alt="Vista previa del GIF de la simulación">`;
    if (opt.descargar !== false) { const a = document.createElement("a"); a.href = S.gifUrl; a.download = nombre; document.body.appendChild(a); a.click(); setTimeout(() => a.remove(), 500); }
    S.run = run0;
    return { blob, nombre, cuadros: out.length, w: W, h: H };
  }

  // para pruebas y capturas: ir a un instante (s simulados) o al centro de la primera ventana de una fase (empuje, retorno, reenganche)
  function seek(t) { S.run = false; S.t = Math.max(0, Math.min(total(), t)); render(); return S.t; }
  function buscarFase(id) {
    // centro de la ventana contigua más larga de la fase (o subfase) en la primera carrera
    const T = period(), n = 2000, runs = []; let cur = null;
    for (let i = 0; i < n; i++) { const t = T * (i + 0.5) / n, z = S.prov.state(t, S.caso); if (z.faseId === id || z.sub === id) { if (!cur) runs.push(cur = []); cur.push(t); } else cur = null; }
    if (!runs.length) return null;
    const w = runs.reduce((a, b) => b.length > a.length ? b : a);
    return w[Math.floor(w.length / 2)];
  }
  // vista estática del detalle del modo pivotado en el centro de una fase (toma, empuje, retorno, reenganche), para la pestaña Modelo
  function vistaFase(P, A, id, caso) {
    const pv = proveedor(P, A); if (pv.id !== 2 || pv.pendiente) return "";
    const d0 = S.dir; S.dir = 1;
    try {
      const T = pv.tExt + pv.tRet, hit = [];
      for (let i = 0; i < 600; i++) { const t = T * (i + 0.5) / 600, z = pv.state(t, caso || "dis"); if (z.faseId === id || z.sub === id) hit.push(t); }
      if (!hit.length) return "";
      const st = pv.state(hit[Math.floor(hit.length / 2)], caso || "dis");
      return detailPivot(pv, st, st.rot).replace('id="simDet"', `id="mdlDet_${id}"`).replace(/simClip/g, "simClip_" + id);
    } finally { S.dir = d0; }
  }
  return { open, close, init, proveedor, seek, buscarFase, exportGif, GIF, segPath, caraBloque, vistaFase, _S: S };
})();
if (typeof module !== "undefined") module.exports = SIM;
