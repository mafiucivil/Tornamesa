/* TT300-C · Simulación del movimiento del accionamiento (SVG, sin dependencias externas).
   Anima el ciclo empuje → retorno → reenganche con la geometría y los resultados del núcleo (TT): kinematics()/guideGeo() para las cotas
   del accionamiento guiado, R.stroke para la fuerza del cilindro y las reacciones de guía a lo largo del empuje, R.pump para las
   velocidades del vástago (caudal de avance y de retorno), chamferGeo() para el chaflán de retorno de la uña y analyze().checks para
   marcar en rojo las verificaciones de cinemática que fallan.
   La UI solo compone posiciones (rotación de la mesa, traslación del vástago); no recalcula fuerzas ni cinemática.
   Arquitectura: un «proveedor» por modo de accionamiento (drive_mode 1 = guiado; drive_mode 2 = pivotado tipo KIET, pendiente de las
   funciones de geometría del núcleo) entrega el estado en cada instante; el dibujo y los controles son comunes. */
const SIM = (() => {
  const D2R = Math.PI / 180;
  const SPEEDS = [0.25, 0.5, 1, 2, 4, 8];
  const IFC_COL = ["#8a94a3", "#9fb8cf", "#e9ecef", "#b07a32"];          // acero-acero, inox (A), UHMW (B), bronce (C)
  const num = (v, d) => (v == null || !isFinite(v)) ? "—" : v.toLocaleString("es-CL", { minimumFractionDigits: d, maximumFractionDigits: d });
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const interp = (xs, ys, x) => {
    if (x <= xs[0]) return ys[0];
    for (let i = 1; i < xs.length; i++) if (x <= xs[i]) { const t = xs[i] === xs[i - 1] ? 1 : (x - xs[i - 1]) / (xs[i] - xs[i - 1]); return ys[i - 1] + t * (ys[i] - ys[i - 1]); }
    return ys[ys.length - 1];
  };

  /* ================= proveedor del modo guiado (drive_mode 1) ================= */
  function guiado(P, A) {
    const R = A.R, K = R.K, ch = TT.chamferGeo(P), bg = TT.bracketGeo(P);
    const pitch = K.pitch, h = pitch / 2;
    const sUse = Math.min(P.stroke, K.s_req);                           // carrera por paso: hasta θ = +π/N (o el tope del cilindro si no alcanza)
    const vExt = R.pump.vExt * 1000, vRet = R.pump.vRet * 1000;         // mm/s (núcleo: Q/(n·A) y Q_ret/(n·A_anular))
    const tExt = sUse / vExt, tRet = sUse / vRet;
    const kS = K.pts.map((q) => q.s), kTh = K.pts.map((q) => q.th), kArm = K.pts.map((q) => q.arm);
    const thOf = (s) => s <= P.s_free ? -h : interp(kS, kTh, s);       // inversa de s(θ) tabulada por el núcleo
    const dTh = thOf(sUse) + h;                                           // giro de la mesa por carrera (= paso si la carrera alcanza)
    const sTh = R.stroke.map((q) => q.th);
    const caseOf = (id) => R.cases.find((c) => c.id === id) || R.cd;
    // fuerzas del núcleo a lo largo del empuje (caso de diseño, R.stroke); para otro caso se escala por T (el núcleo es lineal en T: Tmax = F_calado/F_cil(T = 1))
    const forces = (th, caseId) => {
      const k = caseOf(caseId).T / R.cd.T, f = (key) => interp(sTh, R.stroke.map((q) => q[key]), th) * k;
      return { F: f("F"), Fp: f("Fp"), H: f("H"), Rf: f("Rf"), Rr: f("Rr") };
    };
    const curve = (caseId) => R.stroke.map((q) => { const k = caseOf(caseId).T / R.cd.T; return { s: q.s, F: q.F * k, p: q.F * k * 1e3 / R.A * 10 }; });
    // geometría local de la estación (lado +x, empuje en +y; el dibujo la refleja para cada cilindro y sentido)
    const yFace = (s) => K.y_rp0 + s + P.l_p - P.d_pin / 2;              // cara de empuje de la uña (contacta el pasador en y_p − d/2 a s = s_libre)
    const pinNext = { top: K.y_pin0 + P.d_pin / 2, bot: K.y_pin0 - P.d_pin / 2 };   // pasador siguiente (en −π/N tras el paso)
    const dyCh = Math.min(ch.dy, P.dog_b);
    // salida radial de la uña al retraer: el chaflán de la arista trasera monta sobre el pasador siguiente; el resorte la devuelve al pasarlo
    const uRet = (s) => {
      const yf = yFace(s), yb = yf - P.dog_b, pen = pinNext.top - yb;
      if (pen <= 0 || yf <= pinNext.bot) return 0;
      return Math.min(ch.dx, pen * ch.dx / dyCh);
    };
    // instante del reenganche: la cara de la uña pasa bajo el pasador siguiente
    const sSnap = pinNext.bot - (K.y_rp0 + P.l_p - P.d_pin / 2);
    const fails = A.checks.filter((c) => c.sys === "giro" && c.kind === "geo" && c.st === "fail");
    const failAt = (re) => fails.filter((c) => re.test(c.name)).map((c) => c.name);
    const flags = { carrera: failAt(/Carrera requerida/), toma: failAt(/^Uña/), retorno: failAt(/Alojamiento|Holgura radial/), siempre: fails.filter((c) => !/Carrera requerida|^Uña|Alojamiento|Holgura radial/.test(c.name)).map((c) => c.name) };
    function state(tau, caseId) {                                         // tau: s dentro de la carrera (0 … tExt + tRet)
      const o = { pitch, dTh, sUse };
      if (tau < tExt) {
        const s = Math.min(sUse, vExt * tau), th = thOf(s), contact = s >= P.s_free;
        Object.assign(o, { fase: contact ? "empuje" : "aproximación (carrera libre)", faseId: "empuje", s, thLoc: th, rot: th + h, u: 0, contact });
        if (contact) Object.assign(o, forces(th, caseId), { arm: interp(kTh, kArm, th) });
        o.alerta = [...flags.siempre, ...(contact && s - P.s_free < 15 ? flags.toma : []), ...(s >= sUse - 2 && sUse < K.s_req ? flags.carrera : [])];
      } else {
        const s = Math.max(0, sUse - vRet * (tau - tExt)), u = uRet(s), snapped = s <= sSnap;
        Object.assign(o, { fase: u > 0 ? "retorno: la uña sale sobre el pasador siguiente" : snapped ? "reenganche (el resorte devuelve la uña)" : "retorno", faseId: u > 0 || !snapped ? "retorno" : "reenganche",
          s, thLoc: h, rot: dTh, u, contact: false });
        o.alerta = [...flags.siempre, ...(u > 0 ? flags.retorno : [])];
      }
      o.L = P.L0 + o.s;
      return o;
    }
    return { id: 1, nombre: "Guiado: bancada con ranura T, patín y uña deslizante radial con resorte", P, R, K, bg, ch, pitch, tExt, tRet, vExt, vRet, sUse, dTh, state, curve, yFace, pinNext, flags,
      nota: P.opt_cam ? "Guía de reenganche (opt_cam): pendiente de la geometría del núcleo" : "" };
  }

  /* modo pivotado (drive_mode 2): requiere las funciones de geometría por θ del núcleo; no se inventa la cinemática en la UI */
  function proveedor(P, A) {
    const modo = P.drive_mode || 1;
    if (modo === 1) return guiado(P, A);
    return { id: modo, pendiente: true, nombre: "Pivotado tipo KIET (drive_mode = 2)" };
  }

  /* ================= dibujo ================= */
  const S = { open: false, prov: null, P: null, A: null, t: 0, run: false, speed: 1, dir: 1, n: 3, caso: "nom", last: 0, raf: 0, curS: 0, label: "" };
  const el = (id) => document.getElementById(id);
  const map = (sx, dy) => (x, y) => [sx * x, dy * y];                    // local de la estación → global (planta, y hacia arriba)

  function pinsSvg(pv, rot, X, Y, r, hi) {
    const P = pv.P, N = P.N_pin, o = [];
    for (let k = 0; k < N; k++) {
      const a = (180 / N + 360 * k / N) * D2R + rot, x = P.R_pin * Math.cos(a), y = P.R_pin * Math.sin(a);
      o.push(`<circle cx="${X(x)}" cy="${Y(y)}" r="${r(P.d_pin / 2)}" class="sim-pin${hi && hi(x, y) ? " on" : ""}"/>`);
    }
    return o.join("");
  }
  // estación de un cilindro en coordenadas locales (sx = +1, dy = +1) transformadas por m
  function stationSvg(pv, st, m, X, Y, r, alerta) {
    const P = pv.P, K = pv.K, bg = pv.bg, pt = (x, y) => { const [gx, gy] = m(x, y); return `${X(gx)},${Y(gy)}`; };
    const rect = (x0, y0, x1, y1, cls) => `<polygon points="${pt(x0, y0)} ${pt(x1, y0)} ${pt(x1, y1)} ${pt(x0, y1)}" class="${cls}"/>`;
    const circ = (x, y, d, cls) => { const [gx, gy] = m(x, y); return `<circle cx="${X(gx)}" cy="${Y(gy)}" r="${r(d / 2)}" class="${cls}"/>`; };
    const yrp = K.y_rp0 + st.s, xg = P.x_g, ws = P.w_s;
    const o = [];
    o.push(rect(xg - ws / 2 - 20, -K.Y_bed, xg + ws / 2 + 20, K.Y_bed, "sim-bed"));                       // bancada con ranura T
    o.push(rect(xg - bg.Wout / 2, K.y_eye - bg.rear, xg + bg.Wout / 2, K.y_eye + bg.lugF, "sim-brk"));   // ménsula del ojal
    const yBar = K.y_rp0 - 25;
    o.push(rect(xg - P.D_body / 2, K.y_eye, xg + P.D_body / 2, yBar, "sim-cyl"));                       // cuerpo del cilindro
    o.push(rect(xg - P.d_rod / 2, yBar, xg + P.d_rod / 2, yrp, "sim-rod"));                            // vástago
    o.push(circ(xg, K.y_eye, P.d_pp, "sim-pp"));
    o.push(rect(xg - ws / 2, yrp - K.rear, xg + ws / 2, yrp + K.front, "sim-shoe" + (alerta ? " bad" : "")));   // patín
    // uña: cara de empuje plana, chaflán de retorno en la arista punta–cara trasera, desplazada u hacia afuera
    const yf = pv.yFace(st.s), yb = yf - P.dog_b, tip = K.tipX + st.u, out = K.mouthX + P.L_in + st.u, dx = Math.min(pv.ch.dx, out - tip), dy = Math.min(pv.ch.dy, P.dog_b);
    o.push(`<polygon points="${pt(tip, yf)} ${pt(tip, yb + dy)} ${pt(tip + dx, yb)} ${pt(out, yb)} ${pt(out, yf)}" class="sim-dog${alerta ? " bad" : st.contact ? " on" : ""}"/>`);
    // resorte entre la uña y el fondo del alojamiento
    const ym = (yf + yb) / 2, n = 8, x0 = out, x1 = K.pocketEnd, zz = [];
    for (let i = 0; i <= n; i++) zz.push(pt(x0 + (x1 - x0) * i / n, ym + (i % 2 ? 18 : -18) * (i > 0 && i < n ? 1 : 0)));
    o.push(`<polyline points="${zz.join(" ")}" class="sim-spr"/>`);
    o.push(circ(xg, yrp, P.d_pp, "sim-pp"));
    return o.join("");
  }

  function planSvg(pv, st, rot) {
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

  function detailSvg(pv, st, rot) {
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
    const p = st.F != null ? st.F * 1e3 / R.A * 10 : null, gF = st.Rf != null ? Math.max(Math.abs(st.Rf), Math.abs(st.Rr)) : null;
    const row = (k, v, id) => `<span>${k}</span><span${id ? ` id="${id}"` : ""}>${v}</span>`;
    el("simRead").innerHTML = `<div class="kv">
      ${row("Fase", `<b>${esc(st.fase)}</b>`, "simFase")}
      ${row("Carrera", `${Math.min(sn.k + (sn.done ? 0 : 1), S.n)} de ${S.n}`)}
      ${row("θ de la mesa", num(sn.thetaDeg, 3) + "°", "simTheta")}
      ${row("Carrera s / largo del cilindro", `${num(st.s, 1)} / ${num(st.L, 0)} mm`)}
      ${row("Brazo a(θ)", st.contact ? num(st.arm, 1) + " mm" : "— (sin contacto)")}
      ${row("Fracción tangencial / radial", st.contact ? `${num(Math.cos(st.thLoc), 4)} / ${num(Math.sin(st.thLoc), 4)}` : "—")}
      ${row(`F_cil requerida (${cs ? cs.id === "nom" ? "nominal" : "diseño" : ""}, μ ${num(cs ? cs.mu : NaN, 2)})`, st.contact ? `<span class="${st.F > R.Fstall ? "sim-bad" : ""}">${num(st.F, 1)} kN</span>` : "≈ 0 (sin carga)")}
      ${row("Presión", st.contact ? `${num(p, 0)} bar (alivio ${num(P.p_relief, 0)})` : "—")}
      ${row("Fuerza en la guía (máx. reacción del patín)", gF != null ? num(gF, 1) + " kN" : "—")}
      ${row("Tiempo simulado / total", `${num(Math.min(S.t, total()), 1)} / ${num(total(), 1)} s`)}
    </div>
    ${st.alerta.length ? `<div class="msg error" id="simAlerta"><b>Verificación de cinemática que falla en este instante:</b> ${st.alerta.map(esc).join("; ")}</div>` : ""}`;
    const box = el("simBox");
    box.dataset.theta = sn.thetaDeg.toFixed(6); box.dataset.fase = st.faseId; box.dataset.carrera = String(sn.k); box.dataset.fin = sn.done ? "1" : "0";
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
      ${P.cam_mat != null ? `<span>Material de la leva (cam_mat)</span><span>${P.cam_mat === 0 ? "0 · automático (según el modo y la interfaz)" : esc(P.cam_mat)}</span>` : ""}
      <span>Paso de la mesa (360°/${P.N_pin})</span><span>${num(pv.pitch / D2R, 3)}°</span>
      <span>Carrera por paso / del cilindro</span><span>${num(pv.sUse, 1)} / ${num(P.stroke, 0)} mm</span>
      <span>Velocidad del vástago avance / retorno</span><span>${num(pv.vExt, 1)} / ${num(pv.vRet, 1)} mm/s (Q ${num(P.Q_pump, 1)} / ${num(R.pump.Qr, 1)} L/min)</span>
      <span>Tiempo de empuje / retorno por carrera</span><span id="simTiempos">${num(pv.tExt, 1)} / ${num(pv.tRet, 1)} s</span>
      <span>Tiempo por vuelta (núcleo, carrera completa)</span><span>${num(R.tRev, 2)} min</span>
    </div>${pv.nota ? `<div class="note">${esc(pv.nota)}</div>` : ""}`;
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
      <div class="note">Geometría y fuerzas del núcleo (kinematics, guideGeo, chamferGeo, R.stroke del caso de diseño; para el caso nominal, escalado por el par: el núcleo es lineal en T). Ambos cilindros trabajan en paralelo; el detalle muestra el del lado +x.</div>`;
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
    for (const t of [0, buscarFase("empuje"), buscarFase("retorno"), buscarFase("reenganche"), total()]) if (t != null) muestras.push(await cuadro(t));
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
    const T = period(), n = 2000, hit = [];
    for (let i = 0; i < n; i++) { const t = T * (i + 0.5) / n; if (S.prov.state(t, S.caso).faseId === id) hit.push(t); }
    return hit.length ? hit[Math.floor(hit.length / 2)] : null;
  }
  return { open, close, init, proveedor, seek, buscarFase, exportGif, GIF, _S: S };
})();
if (typeof module !== "undefined") module.exports = SIM;
