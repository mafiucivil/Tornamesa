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
    let s = `<svg viewBox="0 0 ${W} ${W}" class="sim-svg" id="simPlan" role="img" aria-label="Planta animada">`;
    s += `<rect x="${X(-B / 2)}" y="${Y(B / 2)}" width="${r(B)}" height="${r(B)}" class="sim-base"/>`;
    pairs.forEach(([sx, dy]) => { s += stationSvg(pv, st, map(sx, dy), X, Y, r, al); });
    s += `<circle cx="${X(0)}" cy="${Y(0)}" r="${r(P.D_top / 2)}" class="sim-table"/>`;
    s += `<circle cx="${X(0)}" cy="${Y(0)}" r="${r(P.D_hub / 2)}" class="sim-hub"/>`;
    const ang = rot;                                                       // giro acumulado de la mesa (rad, con signo)
    s += `<line x1="${X(0)}" y1="${Y(0)}" x2="${X(0.9 * P.D_top / 2 * Math.cos(ang))}" y2="${Y(0.9 * P.D_top / 2 * Math.sin(ang))}" class="sim-mark"/>`;
    const cps = st.contact ? pairs.map(([sx, dy]) => map(sx, dy)(P.R_pin * Math.cos(st.thLoc), P.R_pin * Math.sin(st.thLoc))) : [];   // pasador tomado por cada uña
    s += pinsSvg(pv, ang, X, Y, r, (x, y) => cps.some(([cx, cy]) => Math.hypot(x - cx, y - cy) < P.d_pin / 2));
    s += `<text x="8" y="16" class="sim-t">Planta · ${S.dir > 0 ? "giro antihorario" : "giro horario"} · θ = ${num(rot / D2R * S.dir, 3)}°</text></svg>`;
    return s;
  }

  function detailSvg(pv, st, rot) {
    const P = pv.P, K = pv.K, x0 = K.a_min - 230, x1 = K.pocketEnd + 70, y0 = K.y_pin0 - 270, y1 = K.y_rp1 + K.front + 50;
    const W = 520, sc = W / (x1 - x0), H = (y1 - y0) * sc, dy = S.dir > 0 ? 1 : -1;
    const X = (x) => ((x - x0) * sc).toFixed(1);
    const Yf = (gy) => (dy > 0 ? (y1 - gy) * sc : (gy + y1) * sc).toFixed(1);   // con giro horario la estación se ve reflejada en y
    const r = (d) => (d * sc).toFixed(2), al = st.alerta.length > 0;
    let s = `<svg viewBox="0 0 ${W} ${H.toFixed(0)}" class="sim-svg" id="simDet" role="img" aria-label="Detalle de la estación de un cilindro">`;
    s += `<defs><clipPath id="simClip"><rect x="0" y="0" width="${W}" height="${H.toFixed(0)}"/></clipPath></defs><g clip-path="url(#simClip)">`;
    // capa de interfaz bajo la mesa (corona de contacto), con el color de la alternativa
    const ifc = pv.R.ifc, col = IFC_COL[ifc.o] || IFC_COL[0];
    s += `<circle cx="${X(0)}" cy="${Yf(0)}" r="${r(P.D_top / 2)}" fill="${col}" opacity=".55" stroke="none"/>`;
    if (P.opt_wood > 0.5) s += `<circle cx="${X(0)}" cy="${Yf(0)}" r="${r(P.D_top / 2 - 12)}" fill="#8b5a2b" opacity=".25" stroke="none"/>`;
    s += `<circle cx="${X(0)}" cy="${Yf(0)}" r="${r(P.D_top / 2)}" class="sim-table" fill-opacity="0"/>`;
    s += stationSvg(pv, st, map(1, dy), X, Yf, r, al);
    const cp = map(1, dy)(P.R_pin * Math.cos(st.thLoc), P.R_pin * Math.sin(st.thLoc));
    s += pinsSvg(pv, rot, X, Yf, r, (x, y) => st.contact && Math.hypot(x - cp[0], y - cp[1]) < P.d_pin / 2);
    s += `</g><text x="8" y="16" class="sim-t">Detalle de la estación (cilindro del lado +x) · fase: ${esc(st.fase)}</text>`;
    s += `<rect x="4" y="${(H - 34).toFixed(0)}" width="${W - 8}" height="26" rx="4" fill="var(--panel)" opacity=".9"/><rect x="8" y="${(H - 28).toFixed(0)}" width="14" height="14" fill="${col}" stroke="var(--ink)" stroke-width=".5"/><text x="28" y="${(H - 17).toFixed(0)}" class="sim-t">Interfaz: ${esc(S.label)} · μ ${num(pv.R.mu.nom, 2)} / ${num(pv.R.mu.d, 2)}</text></svg>`;
    return s;
  }

  function chartSvg(pv) {
    const cur = pv.curve(S.caso), W = 360, H = 150, m = { l: 44, r: 44, t: 10, b: 26 };
    const sMax = Math.max(pv.P.stroke, pv.sUse, ...cur.map((q) => q.s)), Fm = Math.max(...cur.map((q) => q.F)) * 1.15, pm = Math.max(...cur.map((q) => q.p)) * 1.15;
    const X = (s) => (m.l + s / sMax * (W - m.l - m.r)).toFixed(1), YF = (F) => (H - m.b - F / Fm * (H - m.t - m.b)).toFixed(1), Yp = (p) => (H - m.b - p / pm * (H - m.t - m.b)).toFixed(1);
    const full = (k, Yk) => cur.map((q) => `${X(q.s)},${Yk(q[k])}`).join(" ");
    const tr = cur.filter((q) => q.s <= S.curS + 1e-9);
    let s = `<svg viewBox="0 0 ${W} ${H}" class="sim-svg" id="simChart" role="img" aria-label="F_cil y p frente a s">`;
    s += `<line x1="${m.l}" y1="${H - m.b}" x2="${W - m.r}" y2="${H - m.b}" class="sim-ax"/><line x1="${m.l}" y1="${m.t}" x2="${m.l}" y2="${H - m.b}" class="sim-ax"/><line x1="${W - m.r}" y1="${m.t}" x2="${W - m.r}" y2="${H - m.b}" class="sim-ax"/>`;
    s += `<polyline points="${full("F", YF)}" class="sim-cF ghost"/><polyline points="${full("p", Yp)}" class="sim-cp ghost"/>`;
    if (tr.length > 1) { s += `<polyline points="${tr.map((q) => `${X(q.s)},${YF(q.F)}`).join(" ")}" class="sim-cF"/><polyline points="${tr.map((q) => `${X(q.s)},${Yp(q.p)}`).join(" ")}" class="sim-cp"/>`; }
    s += `<line x1="${X(pv.P.stroke)}" y1="${m.t}" x2="${X(pv.P.stroke)}" y2="${H - m.b}" class="sim-lim"/>`;
    s += `<text x="${m.l}" y="${H - 6}" class="sim-t">0</text><text x="${W - m.r}" y="${H - 6}" class="sim-t" text-anchor="end">s = ${num(sMax, 0)} mm</text>`;
    s += `<text x="4" y="${m.t + 8}" class="sim-t sim-tF">${num(Fm, 0)} kN</text><text x="${W - 2}" y="${m.t + 8}" class="sim-t sim-tp" text-anchor="end">${num(pm, 0)} bar</text>`;
    s += `<text x="${m.l + 6}" y="${m.t + 22}" class="sim-t sim-tF">F_cil</text><text x="${m.l + 46}" y="${m.t + 22}" class="sim-t sim-tp">p</text></svg>`;
    return s;
  }

  /* ================= ciclo y controles ================= */
  const period = () => S.prov.tExt + S.prov.tRet;
  const total = () => S.n * period();
  function snapshot() {
    const pv = S.prov, T = period(), tt = Math.min(S.t, total() - 1e-9), k = Math.max(0, Math.floor(tt / T)), done = S.t >= total() - 1e-9;
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
    S.label = (typeof PLANOS !== "undefined" ? PLANOS.ifaceName(P, A.R.ifc) + " · " + PLANOS.fixText(P, A.R.ifc) + " · " + PLANOS.woodText(P) : "") ;
    body.innerHTML = `${header(pv)}
      <div class="sim-ctl">
        <button class="pri" id="bSimPlay">Reproducir</button><button id="bSimStep">Paso a paso</button><button id="bSimReset">Reiniciar</button>
        <label>Velocidad <select id="simSpeed">${SPEEDS.map((v) => `<option value="${v}"${v === S.speed ? " selected" : ""}>×${num(v, v < 1 ? 2 : 0)}</option>`).join("")}</select></label>
        <label>Sentido <select id="simDir"><option value="1"${S.dir > 0 ? " selected" : ""}>antihorario</option><option value="-1"${S.dir < 0 ? " selected" : ""}>horario</option></select></label>
        <label>Carreras <input id="simN" type="number" min="1" max="${P.N_pin}" step="1" value="${S.n}"></label>
        <label>Fricción <select id="simCaso"><option value="nom"${S.caso === "nom" ? " selected" : ""}>nominal</option><option value="dis"${S.caso === "dis" ? " selected" : ""}>diseño</option></select></label>
      </div>
      <div class="sim-grid"><div id="simPlanBox"></div><div id="simDetBox"></div></div>
      <div class="sim-grid"><div id="simRead"></div><div id="simChartBox"></div></div>
      <div class="note">Geometría y fuerzas del núcleo (kinematics, guideGeo, chamferGeo, R.stroke del caso de diseño; para el caso nominal, escalado por el par: el núcleo es lineal en T). Ambos cilindros trabajan en paralelo; el detalle muestra el del lado +x.</div>`;
    el("bSimPlay").onclick = () => { if (S.t >= total() - 1e-9) reset(); S.run = !S.run; S.last = 0; render(); };
    el("bSimStep").onclick = stepNext;
    el("bSimReset").onclick = () => { S.run = false; reset(); };
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
  // para pruebas y capturas: ir a un instante (s simulados) o al centro de la primera ventana de una fase (empuje, retorno, reenganche)
  function seek(t) { S.run = false; S.t = Math.max(0, Math.min(total(), t)); render(); return S.t; }
  function buscarFase(id) {
    const T = period(), n = 2000, hit = [];
    for (let i = 0; i < n; i++) { const t = T * (i + 0.5) / n; if (S.prov.state(t, S.caso).faseId === id) hit.push(t); }
    return hit.length ? hit[Math.floor(hit.length / 2)] : null;
  }
  return { open, close, init, proveedor, seek, buscarFase, _S: S };
})();
if (typeof module !== "undefined") module.exports = SIM;
