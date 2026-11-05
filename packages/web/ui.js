/* TT300-C · Interfaz: formulario, recálculo, dibujos, tablas y optimizador. */
(() => {
  const LS = "tt300c-params-v1", LST = "tt300c-theme";
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { } } };
  const DEF = TT.defaults();
  let P = Object.assign({}, DEF);
  try { const s = JSON.parse(store.get(LS) || "null"); if (s) Object.keys(DEF).forEach((k) => { if (k in s) P[k] = s[k]; }); } catch (e) { }
  let A = null, X = null, AU = null, SC = null, MK = null, CN = null, VAL = [], optRes = null, optRunning = false;
  const $ = (s) => document.querySelector(s);
  const D2R = Math.PI / 180;
  const REF = { KIET: 2158, TT300B: 5354 };

  /* ---------- formato: 2–3 cifras significativas, coma decimal ---------- */
  function fmt(v, sig) {
    if (v == null || !isFinite(v)) return "—";
    sig = sig || 3;
    const a = Math.abs(v);
    let d = a >= 1000 ? 0 : a === 0 ? 0 : Math.max(0, Math.min(3, sig - 1 - Math.floor(Math.log10(a))));
    return v.toLocaleString("es-CL", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  const fu2 = (v) => (v == null || !isFinite(v)) ? "—" : v.toLocaleString("es-CL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const ST = { ok: "Cumple", warn: "Monitoreo", fail: "No cumple", info: "Info", pend: "Pendiente" };

  /* ---------- pestañas ---------- */
  const tabs = [...document.querySelectorAll(".tab")];
  let cur = (location.hash || "#resumen").slice(1);
  if (!tabs.some((t) => t.dataset.t === cur)) cur = "resumen";
  $("#tabs").innerHTML = tabs.map((t) => `<button data-t="${t.dataset.t}">${t.dataset.l}</button>`).join("");
  function showTab(t) {
    cur = t;
    tabs.forEach((s) => s.classList.toggle("on", s.dataset.t === t));
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.t === t));
    try { history.replaceState(null, "", "#" + t); } catch (e) { }
  }
  $("#tabs").addEventListener("click", (e) => { if (e.target.dataset.t) showTab(e.target.dataset.t); });
  showTab(cur);

  /* ---------- tema ---------- */
  const th = store.get(LST); if (th) document.documentElement.dataset.theme = th;
  $("#bTheme").onclick = () => {
    const dark = matchMedia("(prefers-color-scheme: dark)").matches;
    const now = document.documentElement.dataset.theme || (dark ? "dark" : "light");
    const nx = now === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = nx; store.set(LST, nx); renderAll();
  };

  /* ---------- formulario ---------- */
  function buildForm() {
    $("#form").innerHTML = TT.PARAM_GROUPS.map((g, gi) => `<details ${gi < 5 ? "open" : ""}><summary>${esc(g.t)}</summary>${g.p.map(([id, lab, u, def, mn, mx, st]) => {
      const txt = typeof def === "string";
      if (st === "chk") return `<div class="prm chk ${P[id] !== DEF[id] ? "chg" : ""}" data-id="${id}"><label for="p_${id}">${esc(lab)}</label><input id="p_${id}" type="checkbox" ${P[id] > 0.5 ? "checked" : ""}></div>`;
      return `<div class="prm ${P[id] !== DEF[id] ? "chg" : ""}" data-id="${id}"><label for="p_${id}">${esc(lab)}<span class="u">${esc(u)}</span></label>
      <input id="p_${id}" ${txt ? 'class="txt" type="text"' : `type="number" step="${st || "any"}" min="${mn}" max="${mx}"`} value="${esc(P[id])}"></div>`;
    }).join("")}</details>`).join("");
  }
  let tmr = null;
  $("#form").addEventListener("input", (e) => {
    const row = e.target.closest(".prm"); if (!row) return;
    const id = row.dataset.id, txt = typeof DEF[id] === "string";
    if (e.target.type === "checkbox") {
      P[id] = e.target.checked ? 1 : 0;
      const OPTS = ["opt_ss", "opt_uhmw", "opt_bz"];                                    // una sola opción de interfaz a la vez
      if (OPTS.includes(id) && P[id]) OPTS.filter((k) => k !== id).forEach((other) => { P[other] = 0; const ob = $("#p_" + other); if (ob) { ob.checked = false; ob.closest(".prm").classList.remove("chg"); } });
    } else P[id] = txt ? e.target.value : parseFloat(e.target.value);
    row.classList.toggle("chg", P[id] !== DEF[id]);
    clearTimeout(tmr); $("#busy").textContent = "Calculando…";
    tmr = setTimeout(recalc, 380);
  });
  $("#bReset").onclick = () => { P = Object.assign({}, DEF); buildForm(); recalc(); };
  $("#bExp").onclick = () => {
    const blob = new Blob([JSON.stringify(P, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "TT300-C_parametros.json";
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  };
  $("#bImp").onclick = () => $("#fImp").click();
  $("#fImp").onchange = (e) => {
    const f = e.target.files[0]; if (!f) return;
    f.text().then((t) => { const s = JSON.parse(t); Object.keys(DEF).forEach((k) => { if (k in s) P[k] = s[k]; }); buildForm(); recalc(); }).catch(() => alert("Archivo JSON no válido"));
  };
  $("#bOpt").onclick = () => { showTab("opt"); runOpt(); };

  /* ---------- cálculo ---------- */
  function recalc() {
    store.set(LS, JSON.stringify(P));
    VAL = AG.validate(P);
    const t0 = performance.now();
    if (VAL.some((v) => v.lvl === "error")) { A = null; }
    else {
      try { A = TT.analyze(P); X = AG.crossCheck(A); AU = AG.audit(A.checks); SC = AG.scenarios(A); MK = TT.market(P); CN = TT.capacityByCyl(P, [1, 2]); }
      catch (err) { A = null; VAL.push({ lvl: "error", msg: "Error de cálculo: " + err.message }); }
    }
    $("#busy").textContent = A ? `Recalculado en ${fmt(performance.now() - t0, 3)} ms` : "Corrija los datos marcados";
    renderAll();
  }

  /* ---------- encabezado ---------- */
  function renderBadges() {
    if (!A) { $("#badges").innerHTML = `<span class="badge b-fail">Datos inválidos</span>`; return; }
    const v = A.verdict;
    const fuEst = Math.max(0, ...A.checks.filter((c) => c.sys === "est" && c.kind === "fu" && isFinite(c.fu)).map((c) => c.fu));
    const nF = A.checks.filter((c) => c.st === "fail").length;
    $("#badges").innerHTML = [
      `<span class="badge ${v.gira ? "b-ok" : "b-fail"}">${v.gira ? "✓ GIRA" : "✗ NO GIRA"} · FS ${fmt(A.R.cd ? A.R.cd.FS : NaN, 3)}</span>`,
      `<span class="badge ${v.estructura ? (v.warnEst ? "b-warn" : "b-ok") : "b-fail"}">${v.estructura ? "✓ ESTRUCTURA CUMPLE" : `✗ ${nF} NO CUMPLE`} · FU ${fu2(fuEst)}</span>`,
      `<span class="badge b-info">Masa ${fmt(A.R.m.total, 4)} kg</span>`,
      v.pend ? `<span class="badge b-pend">${v.pend} pendiente</span>` : "",
      X && X.every((c) => c.ok) && AU && AU.ok ? `<span class="badge b-ok">Revisión cruzada OK</span>` : `<span class="badge b-warn">Revisar agentes</span>`,
    ].join("");
  }

  /* ---------- Resumen ---------- */
  function msgs() {
    return VAL.map((v) => `<div class="msg ${v.lvl}">${v.lvl === "error" ? "Error" : "Aviso"}: ${esc(v.msg)}</div>`).join("") || `<div class="msg ok">Validador de entradas: sin observaciones.</div>`;
  }
  function renderResumen() {
    const el = document.querySelector('section[data-t="resumen"]');
    if (!A) { el.innerHTML = msgs(); return; }
    const R = A.R, K = R.K, c = (id) => R.cases.find((x) => x.id === id);
    const est = A.checks.filter((x) => x.sys === "est" && x.kind === "fu" && isFinite(x.fu)).sort((a, b) => b.fu - a.fu);
    const notOk = A.checks.filter((x) => x.st === "fail" || x.st === "warn");
    const bar = (v, ref, col) => `<div class="fu" style="height:10px"><i style="width:${Math.min(100, v / ref * 100)}%;background:${col}"></i></div>`;
    const mx = Math.max(R.m.total, REF.TT300B);
    el.innerHTML = msgs() + `
    <div class="grid" style="margin-top:10px">
      <div class="card"><h3>¿Gira?</h3><div class="big" style="color:var(${A.verdict.gira ? "--ok" : "--fail"})">${A.verdict.gira ? "Sí, con margen" : "No asegurado"}</div>
        <div class="kv" style="margin-top:6px">
          <span>FS diseño (μ ${fmt(R.mu.d)}, r ${fmt(P.r_ef)} mm)</span><span>${fmt(c("dis").FS)}</span>
          <span>Presión de diseño / alarma</span><span>${fmt(c("dis").p)} / ${fmt(P.p_alarm)} bar</span>
          <span>FS contaminado (μ ${fmt(R.mu.cont)})</span><span>${fmt(c("cont").FS)}</span>
          <span>FS contacto en el borde</span><span>${fmt(c("borde").FS)}</span>
          <span>Margen de carrera</span><span>${fmt(K.margin)} mm</span>
          <span>μ máx vencible (r_ef, alivio)</span><span>${fmt(R.muMax(P.r_ef))}</span>
          <span>Tiempo por vuelta</span><span>${fmt(R.tRev)} min</span>
        </div></div>
      <div class="card"><h3>Estructura</h3><div class="big" style="color:var(${A.verdict.estructura ? "--ok" : "--fail"})">${A.verdict.estructura ? "Cumple" : "No cumple"}</div>
        <div class="kv" style="margin-top:6px">
          <span>FU máximo</span><span>${est.length ? fu2(est[0].fu) : "—"}</span>
          <span>Gobierna</span><span style="font-family:var(--sans);text-align:right">${est.length ? esc(est[0].grp + ": " + est[0].name) : ""}</span>
          <span>No cumple / monitoreo</span><span>${A.checks.filter((x) => x.st === "fail").length} / ${A.checks.filter((x) => x.st === "warn").length}</span>
          <span>Pendientes</span><span>${A.verdict.pend}</span>
        </div>
        ${notOk.length ? `<div class="note">${notOk.map((x) => `<span class="st st-${x.st}">${ST[x.st]}</span> ${esc(x.grp)} · ${esc(x.name)} (FU ${fu2(x.fu)})`).join("<br>")}</div>` : ""}</div>
      <div class="card"><h3>Masa del equipo</h3><div class="big">${fmt(R.m.total, 4)} kg</div>
        <div class="kv" style="margin-top:6px"><span>Este diseño</span><span>${fmt(R.m.total, 4)} kg</span></div>${bar(R.m.total, mx, "var(--acc)")}
        <div class="kv" style="margin-top:6px"><span>Referencia KIET 400T (fabricante)</span><span>${fmt(REF.KIET, 4)} kg</span></div>${bar(REF.KIET, mx, "var(--steel)")}
        <div class="kv" style="margin-top:6px"><span>TT300-B Rev. 0 (carro guiado)</span><span>${fmt(REF.TT300B, 4)} kg</span></div>${bar(REF.TT300B, mx, "var(--steel)")}
        <div class="note">Mesa ${fmt(R.m.disc, 4)} kg · base ${fmt(R.m.base + R.m.rim, 4)} kg · cilindros ${fmt(R.m.cyl, 3)} kg</div></div>
      <div class="card"><h3>Cargas</h3><div class="kv">
          <span>W (WLL)</span><span>${fmt(R.W, 4)} kN</span>
          <span>N = W + W_mesa</span><span>${fmt(R.N, 4)} kN</span>
          <span>N_D = φd·W + W_mesa</span><span>${fmt(R.ND, 4)} kN</span>
          <span>q medio / q máx interfaz</span><span>${fmt(R.q_avg)} / ${fmt(R.q_max)} MPa</span>
          <span>F calado por cilindro (${fmt(P.p_relief)} bar)</span><span>${fmt(R.Fstall)} kN</span>
          <span>Brazo mínimo de la fuerza</span><span>${fmt(K.armMin, 4)} mm</span>
        </div></div>
    </div>
    <div class="card" style="margin-top:12px"><h3>Casos de accionamiento</h3>${casesTable()}</div>
    <div class="card" style="margin-top:12px"><h3>Interfaz de giro: alternativas (marque A, B o C en «Interfaz alternativa» del panel izquierdo)</h3>${ifaceTable()}</div>
    <div class="card" style="margin-top:12px"><h3>Comparación con equipos comerciales</h3>${marketTable()}</div>`;
  }
  function ifaceTable() {
    const rows = (SC && SC.ifaces) || [], act = A.R.ifc.o;
    const g = (v, d) => (v ? fmt(v, d || 3) : "—");
    return `<div class="scroll"><table><tr><th>Alternativa</th><th class="n">Disco inox o duro req. → adoptado (mm)</th><th class="n">UHMW req. → adoptado (mm)</th><th class="n">Bronce req. → adoptado (mm)</th><th class="n">Altura agregada (mm)</th><th class="n">Δ masa total (kg)</th><th class="n">Masa total (kg)</th><th class="n">μ diseño</th><th class="n">F/cil diseño (kN)</th><th class="n">p diseño (bar)</th><th class="n">FS diseño</th></tr>
      ${rows.map((r) => `<tr${r.k === act ? ' class="grp"' : ""}><td>${r.k === act ? "● " : ""}${esc(r.name)}</td><td class="n">${r.k ? g(r.tssReq, 3) + " → " + fmt(r.tss, 3) : "—"}</td><td class="n">${r.k === 2 ? g(r.tuhReq, 3) + " → " + fmt(r.tuh, 3) : "—"}</td><td class="n">${r.k === 3 ? g(r.tbzReq, 3) + " → " + fmt(r.tbz, 3) : "—"}</td><td class="n">${g(r.delta)}</td><td class="n">${r.k ? "+" + fmt(r.dTot, 3) : "—"}</td><td class="n">${fmt(r.mass, 4)}</td><td class="n">${fmt(r.mu_d)}</td><td class="n">${fmt(r.F)}</td><td class="n">${fmt(r.p)}</td><td class="n">${fmt(r.FS)}</td></tr>`).join("")}</table></div>
      <div class="note">● alternativa activa. Disco inoxidable: placa circular empotrada sobre un vacío local de Ø${fmt(P.ss_void, 3)} mm bajo q = ${fmt(A.R.q_max)} MPa, σ = 3qa²/(4t²) ≤ 0,6·Fy (${fmt(P.Fy_ss, 3)} MPa), más ${fmt(P.ss_allow)} mm de sobreespesor; mínimo constructivo ${fmt(P.ss_tmin)} mm. Lámina UHMW: t ≥ E_c(S)·δ/(p_adm − q), con el módulo E_c aumentado por el factor de forma de la lámina delgada (E = ${fmt(P.E_uhmw, 3)} MPa, δ = ${fmt(P.d_flat)} mm en una ventana de Ø${fmt(P.ss_void, 3)} mm, p_adm = ${fmt(P.p_uhmw)} MPa; mínimo constructivo ${fmt(P.uh_tmin)} mm). La Δ de masa total incluye el crecimiento de ménsulas, patines y pivote por la altura agregada. Bronce (C): t ≥ t_flex/√η + sobreespesor, con la eficiencia de ligamento η = (p − d)/p de los tapones de grafito y el disco duro por el mismo método (Fy ${fmt(P.Fy_cara, 4)} MPa); la configuración 3 (pastillas) concentra la presión en ${fmt(P.bz_cover * 100, 3)} % del área. Los μ de cada alternativa son datos de entrada: confirmarlos con ensayo del proveedor. Al activar A o B el eje de los cilindros sube la altura agregada.</div>`;
  }
  function casesTable() {
    const R = A.R;
    return `<div class="scroll"><table><tr><th>Caso</th><th class="n">μ</th><th class="n">r (mm)</th><th class="n">T (kN·m)</th><th class="n">F/cil (kN)</th><th class="n">p (bar)</th><th class="n">FS</th><th>Resultado</th></tr>
      ${R.cases.map((c) => `<tr><td>${esc(c.name)}</td><td class="n">${fmt(c.mu)}</td><td class="n">${fmt(c.r, 4)}</td><td class="n">${fmt(c.T)}</td><td class="n">${fmt(c.F)}</td><td class="n">${fmt(c.p)}</td><td class="n">${fmt(c.FS)}</td>
      <td><span class="st st-${c.id === "seco" ? (c.turns ? "info" : "info") : c.turns ? (c.p > P.p_alarm ? "warn" : "ok") : "fail"}">${c.turns ? (c.p > P.p_alarm ? "Gira (sobre alarma)" : "Gira") : "No gira"}</span></td></tr>`).join("")}</table></div>
      <div class="note">F/cil = T/(n·brazo_mín·η_c). Fuerza de calado: ${fmt(R.Fstall)} kN a ${fmt(P.p_relief)} bar. El caso de acero seco es referencial: la operación exige lubricación.</div>`;
  }

  /* ---------- Modelo: planta y corte ---------- */
  function planSVG() {
    const R = A.R, K = R.K, B = P.B, S = B / 2 + 160;
    const y = (v) => -v;
    const o = [];
    o.push(`<rect x="${-B / 2}" y="${-B / 2}" width="${B}" height="${B}" fill="var(--soft)" stroke="var(--steel)" stroke-width="4"/>`);
    if (P.rim_t > 0) o.push(`<rect x="${-B / 2 + P.rim_t / 2}" y="${-B / 2 + P.rim_t / 2}" width="${B - P.rim_t}" height="${B - P.rim_t}" fill="none" stroke="var(--steel)" stroke-width="${P.rim_t}" opacity=".6"/>`);
    const Rt = P.D_top / 2;
    o.push(`<circle r="${Rt}" fill="var(--panel)" stroke="var(--ink)" stroke-width="5"/>`);
    o.push(`<circle r="${TT.prIn(P)}" fill="none" stroke="var(--steel)" stroke-width="2" stroke-dasharray="14 10"/>`);
    TT.parseRings(P.rings).forEach((r) => o.push(`<circle r="${r}" fill="none" stroke="var(--steel)" stroke-width="${Math.max(3, P.t_web)}" stroke-dasharray="20 12" opacity=".8"/>`));
    for (let k = 0; k < P.N_rib; k++) { const a = 2 * Math.PI * k / P.N_rib; o.push(`<line x1="${P.D_hub / 2 * Math.cos(a)}" y1="${y(P.D_hub / 2 * Math.sin(a))}" x2="${P.R_rib * Math.cos(a)}" y2="${y(P.R_rib * Math.sin(a))}" stroke="var(--steel)" stroke-width="${Math.max(3, P.t_rib)}" stroke-dasharray="20 12" opacity=".8"/>`); }
    o.push(`<circle r="${P.D_hub / 2}" fill="none" stroke="var(--steel)" stroke-width="4"/><circle r="${P.D_piv / 2}" fill="var(--steel)" opacity=".5"/>`);
    for (let k = 0; k < P.N_pin; k++) { const a = Math.PI / P.N_pin + 2 * Math.PI * k / P.N_pin; o.push(`<circle cx="${P.R_pin * Math.cos(a)}" cy="${y(P.R_pin * Math.sin(a))}" r="${P.d_pin / 2}" fill="var(--ink2)"/>`); }
    // cáncamos
    [[1, 1], [-1, 1], [1, -1], [-1, -1]].forEach(([sx, sy]) => o.push(`<rect x="${sx * P.x_lug - 40}" y="${sy * (B / 2 - P.c_lug) - 40}" width="80" height="80" rx="14" fill="none" stroke="var(--ink2)" stroke-width="4"/>`));
    // accionamiento guiado: bancadas, ménsulas (ambos sentidos), patines, uñas y cilindros (sentido antihorario)
    const g = K, bg = TT.bracketGeo(P);
    for (const sx of [1, -1]) {
      const X = sx * P.x_g;
      o.push(`<rect x="${X - P.w_bed / 2}" y="${-g.Y_bed}" width="${P.w_bed}" height="${2 * g.Y_bed}" fill="var(--soft)" stroke="var(--steel)" stroke-width="3"/>`);
      o.push(`<line x1="${X}" y1="${-g.Y_bed}" x2="${X}" y2="${g.Y_bed}" stroke="var(--steel)" stroke-width="${P.w_slot}" opacity=".35"/>`);
      for (const dy of [1, -1]) {
        const act = sx * dy > 0, op = act ? 1 : 0.35, Ye = dy * g.y_eye;
        o.push(`<g opacity="${op}"><rect x="${X - bg.Wout / 2}" y="${y(Ye + dy * (P.L_ch - bg.rear)) - (dy > 0 ? 0 : 0)}" width="${bg.Wout}" height="${P.L_ch}" transform="translate(0 ${dy > 0 ? 0 : -P.L_ch})" fill="none" stroke="var(--ink)" stroke-width="5"/>
          <circle cx="${X}" cy="${y(Ye)}" r="${P.d_pp / 2}" fill="var(--ink)"/></g>`);
        if (!act) continue;
        const yr = dy * (g.y_rp0 + P.s_free), yb0 = Ye + dy * P.e_body, yb1 = dy * (g.y_rp0 - P.c_rod);
        o.push(`<rect x="${X - P.D_body / 2}" y="${Math.min(y(yb0), y(yb1))}" width="${P.D_body}" height="${Math.abs(yb1 - yb0)}" fill="var(--acc)" opacity=".55"/>`);
        o.push(`<rect x="${X - P.d_rod / 2}" y="${Math.min(y(yb1), y(yr))}" width="${P.d_rod}" height="${Math.abs(yr - yb1)}" fill="var(--acc)"/>`);
        const ys0 = yr - dy * g.rear, ys1 = yr + dy * g.front;
        o.push(`<rect x="${X - P.w_s / 2}" y="${Math.min(y(ys0), y(ys1))}" width="${P.w_s}" height="${g.L_s}" fill="var(--panel)" stroke="var(--ink)" stroke-width="5"/>`);
        o.push(`<circle cx="${X}" cy="${y(yr)}" r="${P.d_pp / 2}" fill="var(--panel)" stroke="var(--ink)" stroke-width="4"/>`);
        const yp = dy * (-P.R_pin * Math.sin(g.pitch / 2)), xm = sx * g.mouthX, xa = sx * g.a_min, xt = sx * g.tipX;
        // uña de cara plana (en contacto con la superficie del pasador), con el chaflán de retorno en la arista punta–cara trasera
        const ch = TT.chamferGeo(P), yf = yp - dy * P.d_pin / 2, ybk = yf - dy * P.dog_b;
        const pts = [[xt, yf], [xm, yf], [xm, ybk], [xt + sx * ch.dx, ybk], [xt, ybk + dy * Math.min(ch.dy, P.dog_b)]].map(([a, b]) => `${a},${y(b)}`).join(" ");
        o.push(`<polygon points="${pts}" fill="var(--load)" opacity=".85"/>`);
        o.push(`<circle cx="${xa}" cy="${y(yp)}" r="${P.d_pin / 2 + 6}" fill="none" stroke="var(--load)" stroke-width="8"/>`);
        if (sx > 0) {
          o.push(`<line x1="0" y1="0" x2="${xa}" y2="0" stroke="var(--load)" stroke-width="3"/><text x="${xa / 2}" y="-14" font-size="44" text-anchor="middle" fill="var(--load)">brazo ${fmt(g.a_min, 3)} mm</text>`);
          o.push(`<line x1="${xa}" y1="${y(yp)}" x2="${X}" y2="${y(yp)}" stroke="var(--load)" stroke-width="3" stroke-dasharray="14 10"/><text x="${(xa + X) / 2}" y="${y(yp) + (dy > 0 ? 60 : -30)}" font-size="40" text-anchor="middle" fill="var(--load)">Δ ${fmt(g.DeltaMax, 3)}</text>`);
        }
      }
    }
    o.push(`<text x="0" y="${-B / 2 - 50}" text-anchor="middle" font-size="52">Base ${fmt(B, 4)} × ${fmt(B, 4)} · mesa Ø${fmt(P.D_top, 4)} · ${P.N_pin} pasadores Ø${fmt(P.d_pin)} en R${fmt(P.R_pin, 4)}</text>`);
    o.push(`<text x="0" y="${B / 2 + 90}" text-anchor="middle" font-size="44" fill="var(--ink2)">Cilindros y patines al tomar el pasador · giro antihorario (ménsulas tenues: giro horario)</text>`);
    return `<svg viewBox="${-S} ${-S} ${2 * S} ${2 * S + 40}" role="img" aria-label="Planta de la tornamesa">${o.join("")}</svg>`;
  }
  function sectionSVG() {
    const R = A.R, tb = P.t_base, hd = P.h_disc, tpr = Math.max(P.t_pr, P.t_top, P.t_bot), ifc = R.ifc, dl = ifc.delta, tm = tb + dl;   // tm: cara inferior de la mesa (sobre los discos de la interfaz)
    const r0 = TT.prIn(P) - 220, r1 = P.B / 2 + 40, W = r1 - r0, Hs = tm + hd + (P.opt_wood > 0.5 ? P.t_wood : 0) + 160;
    const sc = 1, X = (r) => (r - r0) * sc, Z = (z) => (Hs - 40 - z) * sc;
    const o = [];
    o.push(`<rect x="${X(r0)}" y="${Z(tb)}" width="${X(P.B / 2) - X(r0)}" height="${tb}" fill="var(--steel)" opacity=".55"/>`);
    if (P.rim_h > 0) o.push(`<rect x="${X(P.B / 2 - P.rim_t)}" y="${Z(tb + P.rim_h)}" width="${P.rim_t}" height="${P.rim_h}" fill="var(--steel)"/>`);
    const Rt = P.D_top / 2, rpr = TT.prIn(P);
    if (P.opt_wood > 0.5) o.push(`<rect x="${X(r0)}" y="${Z(tm + hd + P.t_wood)}" width="${X(Rt) - X(r0)}" height="${P.t_wood}" fill="#8b5a2b" opacity=".85" stroke="var(--ink)" stroke-width=".6"><title>Madera dura ${fmt(P.t_wood, 3)} mm</title></rect>`);
    if (ifc.o > 0) {                                                  // discos inoxidables (A y B) y lámina UHMW (B) entre la base y la mesa
      const BR = "#b87333", rI = R.Ri;                                 // bronce: color cobre
      const zs = ifc.o === 3 ? [[tb, ifc.tbz, BR, "bronce con grafito"], [tb + ifc.tbz, ifc.tss, ifc.conf === 2 ? BR : "var(--acc)", ifc.conf === 2 ? "2.ª placa de bronce" : "disco duro"]]
        : [[tb, ifc.tss, "var(--acc)", "disco inox"], ...(ifc.o === 2 ? [[tb + ifc.tss, ifc.tuh, "var(--warn)", "UHMW"]] : []), [tb + ifc.tss + (ifc.o === 2 ? ifc.tuh : 0), ifc.tss, "var(--acc)", "disco inox"]];
      zs.forEach(([z0, t, c, n], k) => o.push(`<rect x="${X(rI)}" y="${Z(z0 + t)}" width="${X(Rt) - X(rI)}" height="${t}" fill="${c}" opacity="${n === "UHMW" ? 0.85 : 0.75}" stroke="var(--ink)" stroke-width=".6"><title>${n} ${fmt(t, 3)} mm</title></rect>`));
      o.push(`<text x="${X(r0) + 250}" y="${Z(tb) + 14}" font-size="13" fill="var(--ink)">${ifc.o === 3 ? "bronce " + fmt(ifc.tbz, 3) + " + " + (ifc.conf === 2 ? "bronce " : "disco duro ") + fmt(ifc.tss, 3) : ifc.o === 2 ? "inox " + fmt(ifc.tss, 3) + " + UHMW " + fmt(ifc.tuh, 3) + " + inox " + fmt(ifc.tss, 3) : "2 × inox " + fmt(ifc.tss, 3)} mm</text>`);
    }
    // plancha inferior y superior con anillo
    o.push(`<rect x="${X(r0)}" y="${Z(tm + P.t_bot)}" width="${X(rpr) - X(r0)}" height="${P.t_bot}" fill="var(--ink2)"/>`);
    o.push(`<rect x="${X(rpr)}" y="${Z(tm + tpr)}" width="${X(Rt) - X(rpr)}" height="${tpr}" fill="var(--ink2)"/>`);
    o.push(`<rect x="${X(r0)}" y="${Z(tm + hd)}" width="${X(rpr) - X(r0)}" height="${P.t_top}" fill="var(--ink2)"/>`);
    o.push(`<rect x="${X(rpr)}" y="${Z(tm + hd)}" width="${X(Rt) - X(rpr)}" height="${tpr}" fill="var(--ink2)"/>`);
    TT.parseRings(P.rings).filter((r) => r > r0).forEach((r) => o.push(`<rect x="${X(r - P.t_web / 2)}" y="${Z(tm + hd - P.t_top)}" width="${P.t_web}" height="${hd - P.t_top - P.t_bot}" fill="var(--ink2)" opacity=".75"/>`));
    o.push(`<rect x="${X(P.R_pin - P.d_pin / 2)}" y="${Z(tm + hd)}" width="${P.d_pin}" height="${hd}" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>`);
    const zc = tb + R.hax;
    o.push(`<line x1="${X(r0)}" y1="${Z(zc)}" x2="${X(r1)}" y2="${Z(zc)}" stroke="var(--load)" stroke-width="1.5" stroke-dasharray="10 6"/>`);
    const K = A.R.K, zb = tb + P.t_bed, fh = TT.forkH(P);
    o.push(`<rect x="${X(P.x_g - P.w_bed / 2)}" y="${Z(zb)}" width="${P.w_bed}" height="${P.t_bed}" fill="var(--steel)" opacity=".8"/>`);
    o.push(`<rect x="${X(P.x_g - P.w_slot / 2)}" y="${Z(zb)}" width="${P.w_slot}" height="${P.h_slot}" fill="var(--panel)"/>`);
    if (P.h_tee > 0) o.push(`<rect x="${X(P.x_g - P.w_tee / 2)}" y="${Z(zb - P.h_slot)}" width="${P.w_tee}" height="${P.h_tee}" fill="var(--panel)"/>`);
    o.push(`<rect x="${X(P.x_g - P.w_s / 2)}" y="${Z(zc + fh / 2)}" width="${P.w_s}" height="${zc + fh / 2 - zb}" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>`);
    o.push(`<rect x="${X(P.x_g - P.w_slot / 2 + 1)}" y="${Z(zb)}" width="${P.w_slot - 2}" height="${P.h_slot - 2}" fill="var(--ink2)"/>`);
    if (P.h_tee > 0) o.push(`<rect x="${X(P.x_g - P.w_tee / 2 + 1)}" y="${Z(zb - P.h_slot + 1)}" width="${P.w_tee - 2}" height="${P.h_tee - 2}" fill="var(--ink2)"/>`);
    o.push(`<rect x="${X(K.mouthX)}" y="${Z(zc + P.dog_h / 2 + 10)}" width="${P.x_g - P.w_s / 2 - K.mouthX}" height="${P.dog_h + 20}" fill="none" stroke="var(--ink)" stroke-width="2"/>`);
    o.push(`<rect x="${X(K.tipX)}" y="${Z(zc + P.dog_h / 2)}" width="${K.mouthX + P.L_in - K.tipX}" height="${P.dog_h}" fill="var(--load)" opacity=".75"/>`);
    o.push(`<line x1="${X(P.x_g)}" y1="${Z(tb)}" x2="${X(P.x_g)}" y2="${Z(zc + fh / 2 + 20)}" stroke="var(--ink2)" stroke-dasharray="8 5"/>`);
    const dim = (r, z0, z1, txt, side) => `<line x1="${X(r)}" y1="${Z(z0)}" x2="${X(r)}" y2="${Z(z1)}" stroke="var(--ink)" stroke-width="1"/><text x="${X(r) + (side || 6)}" y="${(Z(z0) + Z(z1)) / 2 + 4}" font-size="13" ${side < 0 ? 'text-anchor="end"' : ""}>${txt}</text>`;
    o.push(dim(r0 + 8, tm, tm + hd, `h ${fmt(hd, 3)}`, 6));
    o.push(dim(r0 + 110, 0, tb, `base ${fmt(tb)}`, 6));
    o.push(dim(P.R_pin, tm + tpr, tm + hd - tpr, `libre ${fmt(TT.pinClear(P))}`, -P.d_pin / 2 - 8));
    o.push(`<text x="${X(Rt) + 8}" y="${Z(tm + hd) + 14}" font-size="13">anillo ${fmt(tpr)}</text>`);
    o.push(`<text x="${X(r0) + 4}" y="${Z(tm + hd) - 8}" font-size="13">sup. ${fmt(P.t_top)} · inf. ${fmt(P.t_bot)} · almas ${fmt(P.t_web)}</text>`);
    o.push(`<text x="${X(r1) - 4}" y="${Z(zc) - 6}" font-size="13" text-anchor="end" fill="var(--load)">eje cilindro +${fmt(R.hax)}</text>`);
    o.push(`<text x="${X(P.R_pin)}" y="${Z(-10) + 22}" font-size="13" text-anchor="middle">R${fmt(P.R_pin, 4)}</text>`);
    return `<svg viewBox="0 0 ${W} ${Hs + 20}" role="img" aria-label="Corte radial en el borde">${o.join("")}</svg>`;
  }
  function renderModelo() {
    const el = document.querySelector('section[data-t="modelo"]');
    if (!A) { el.innerHTML = msgs(); return; }
    el.innerHTML = `<div class="grid" style="grid-template-columns:minmax(300px,1.3fr) minmax(280px,1fr)">
      <div class="card"><h3>Planta</h3>${planSVG()}</div>
      <div class="card"><h3>Corte radial por el patín (escala 1:1 relativa)</h3>${sectionSVG()}
        <div class="kv" style="margin-top:10px">
          <span>Brazo mín (R·cos π/N) / máx</span><span>${fmt(A.R.K.armMin, 4)} / ${fmt(A.R.K.armMax, 4)} mm</span>
          <span>Carrera requerida (libre + cuerda)</span><span>${fmt(A.R.K.s_req, 4)} de ${fmt(P.stroke, 4)} mm</span>
          <span>Δ guía–pasador / Lg / factor K</span><span>${fmt(A.R.K.DeltaMax, 3)} / ${fmt(A.R.K.Lg, 3)} mm / ${fmt(A.R.Kguide)}</span>
          <span>Reacción de guía (calado)</span><span>${fmt(A.R.Rguide)} kN</span>
          <span>Voladizo de la uña / holgura radial</span><span>${fmt(A.R.K.lever, 3)} / ${fmt(A.R.K.radial)} mm</span>
          <span>Cuerda / hueco entre pasadores</span><span>${fmt(A.R.K.chord, 4)} / ${fmt(A.R.K.gap, 4)} mm</span>
          <span>Ciclos por vuelta</span><span>${P.N_pin}</span>
        </div></div></div>`;
  }

  /* ---------- Accionamiento ---------- */
  function lineChart(series, opt) {
    const Wd = 640, Hd = 300, m = { l: 56, r: 16, t: 14, b: 38 };
    const xs = series.flatMap((s) => s.pts.map((p) => p[0])).concat(opt.xs || []);
    const ys = series.flatMap((s) => s.pts.map((p) => p[1])).concat(opt.ys || []);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = 0, y1 = Math.max(...ys) * 1.08;
    const X = (v) => m.l + (v - x0) / (x1 - x0 || 1) * (Wd - m.l - m.r), Y = (v) => Hd - m.b - (v - y0) / (y1 - y0 || 1) * (Hd - m.t - m.b);
    const o = [];
    for (let i = 0; i <= 5; i++) { const v = y0 + (y1 - y0) * i / 5; o.push(`<line x1="${m.l}" x2="${Wd - m.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text x="${m.l - 6}" y="${Y(v) + 4}" font-size="11" text-anchor="end">${fmt(v, 3)}</text>`); }
    for (let i = 0; i <= 5; i++) { const v = x0 + (x1 - x0) * i / 5; o.push(`<text x="${X(v)}" y="${Hd - m.b + 16}" font-size="11" text-anchor="middle">${fmt(v, 3)}</text>`); }
    (opt.hl || []).forEach((h) => o.push(`<line x1="${m.l}" x2="${Wd - m.r}" y1="${Y(h.v)}" y2="${Y(h.v)}" stroke="${h.c}" stroke-dasharray="6 4" stroke-width="1.5"/><text x="${Wd - m.r - 4}" y="${Y(h.v) - 5}" font-size="11" text-anchor="end" fill="${h.c}">${h.t}</text>`));
    (opt.vl || []).forEach((h) => o.push(`<line y1="${m.t}" y2="${Hd - m.b}" x1="${X(h.v)}" x2="${X(h.v)}" stroke="${h.c}" stroke-dasharray="6 4" stroke-width="1.5"/><text x="${X(h.v) - 4}" y="${Hd - m.b - 6}" font-size="11" text-anchor="end" fill="${h.c}">${h.t}</text>`));
    series.forEach((s) => o.push(`<polyline fill="none" stroke="${s.c}" stroke-width="2" points="${s.pts.map((p) => X(p[0]) + "," + Y(p[1])).join(" ")}"/>`));
    o.push(`<text x="${(m.l + Wd - m.r) / 2}" y="${Hd - 6}" font-size="12" text-anchor="middle">${opt.xl}</text><text x="12" y="${(m.t + Hd - m.b) / 2}" font-size="12" text-anchor="middle" transform="rotate(-90 12 ${(m.t + Hd - m.b) / 2})">${opt.yl}</text>`);
    const leg = series.map((s, i) => `<span style="display:inline-flex;align-items:center;gap:5px;margin-right:12px"><i style="width:16px;height:3px;background:${s.c};display:inline-block"></i>${s.n}</span>`).join("");
    return `<svg viewBox="0 0 ${Wd} ${Hd}" role="img" aria-label="${opt.yl} vs ${opt.xl}">${o.join("")}</svg><div class="note">${leg}</div>`;
  }
  function cylCapTable() {
    if (!CN) return "";
    return `<table><tr><th class="n">Cilindros</th><th class="n">W máx. giro (FS ≥ ${fmt(P.FS_min)}, μ diseño)</th><th class="n">W máx. por pivote</th><th class="n">Capacidad adoptada</th><th class="n">W que gira (FS = 1, μ nominal)</th></tr>
      ${CN.map((c) => `<tr${c.n === P.n_cyl ? ' class="grp"' : ""}><td class="n">${c.n}</td><td class="n">${fmt(c.wGiro, 3)} tf</td><td class="n">${fmt(c.wPiv, 3)} tf</td><td class="n"><b>${fmt(c.wCap, 3)} tf</b></td><td class="n">${fmt(c.wNom, 3)} tf</td></tr>`).join("")}</table>
      <div class="note">Con un solo cilindro el empuje no es un par puro: el pivote reacciona con la fuerza tangencial del pasador y limita la capacidad (como en el modo de un cilindro de los equipos comerciales). La capacidad estructural de la cadena de empuje se verifica con la carga indicada en «Carga».</div>`;
  }
  function marketTable() {
    if (!MK) return "";
    const r = (x) => x == null ? "—" : fmt(x, 3), rows = [MK.ours, ...MK.refs];
    return `<div class="scroll"><table><tr><th>Equipo</th><th class="n">Capacidad (kN)</th><th class="n">Masa (kg)</th><th class="n">kg por kN</th><th class="n">Altura (mm)</th><th class="n">Ø plataforma (mm)</th><th class="n">Cilindros</th><th class="n">F por cilindro (kN)</th><th class="n">kN de cilindro por tf</th><th class="n">μ implícito*</th><th class="n">Giro por carrera (°)</th></tr>
      ${rows.map((x, i) => `<tr${i === 0 ? ' class="grp"' : ""}><td>${esc(x.name)}</td><td class="n">${r(x.capKN)}</td><td class="n">${r(x.mass)}</td><td class="n">${x.massPerKN == null ? "—" : fmt(x.massPerKN, 3)}</td><td class="n">${r(x.h)}</td><td class="n">${r(x.D)}</td><td class="n">${x.nCyl == null ? "—" : x.nCyl}</td><td class="n">${r(x.Fcyl)}</td><td class="n">${x.FcylPerTon == null ? "—" : fmt(x.FcylPerTon, 3)}</td><td class="n">${x.muImpl == null ? "—" : fmt(x.muImpl, 3)}</td><td class="n">${r(x.rot)}</td></tr>`).join("")}</table></div>
      <div class="note">* μ implícito = n·F·a/(N·r_u) con la fuerza de calado y el brazo mínimo: es la fricción que el equipo vence al límite del alivio, sin factor de seguridad. Datos de los equipos comerciales: fichas y planos públicos (Enerpac, KIET); el brazo y el radio de fricción son estimaciones.</div>
      <div class="kv" style="margin-top:8px"><span>W máx. que gira, FS ≥ ${fmt(P.FS_min)} (μ de diseño, r_ef) · criterio de este proyecto</span><span>${fmt(MK.capacity.design, 3)} tf</span>
        <span>W máx. que gira con FS = 1 (μ de diseño)</span><span>${fmt(MK.capacity.designFS1, 3)} tf</span>
        <span>W máx. que gira con FS = 1 (μ nominal, r_u) · rotulado comercial</span><span>${fmt(MK.capacity.nominal, 3)} tf</span></div>
      <div class="note">La capacidad de giro es una cota de los cilindros; la capacidad estructural de la mesa se verifica con la carga indicada en «Carga» (${fmt(P.W_tf, 3)} tf).</div>`;
  }
  function renderGiro() {
    const el = document.querySelector('section[data-t="giro"]');
    if (!A) { el.innerHTML = msgs(); return; }
    const R = A.R, K = R.K;
    const ser = [["nom", "Nominal", "var(--ok)"], ["dis", "Diseño", "var(--acc)"], ["cont", "Contaminado (μ·r = " + fmt(R.mu.cont * P.r_ef / 1000) + " m)", "var(--warn)"], ["borde", "Borde (μ·r = " + fmt(R.mu.d * P.D_top / 2000) + " m)", "var(--fail)"]].map(([id, n, c]) => {
      const cs = R.cases.find((x) => x.id === id);
      return { n, c, pts: K.pts.map((q) => [q.s, R.Fcyl(cs.T, q.arm)]) };
    });
    const chart = lineChart(ser, { xl: "Extensión del cilindro desde retraído (mm)", yl: "Fuerza por cilindro (kN)", ys: [R.Fstall], xs: [0, P.stroke],
      hl: [{ v: R.Fstall, c: "var(--fail)", t: `Calado ${fmt(R.Fstall)} kN (${fmt(P.p_relief)} bar)` }, { v: R.Falarm, c: "var(--warn)", t: `Alarma ${fmt(R.Falarm)} kN (${fmt(P.p_alarm)} bar)` }],
      vl: [{ v: P.stroke, c: "var(--ink2)", t: "fin de carrera" }, { v: K.s_req, c: "var(--ok)", t: "suelta el pasador" }] });
    const mm = [["r_u (uniforme)", R.r_u], ["r_ef (diseño)", P.r_ef], ["R (borde)", R.Ro]];
    el.innerHTML = `<div class="card"><h3>Casos</h3>${casesTable()}</div>
      <div class="grid" style="margin-top:12px">
      <div class="card"><h3>Fuerza en cada cilindro a lo largo de la carrera</h3>${chart}</div>
      <div class="card"><h3>Fricción máxima vencible</h3><table><tr><th>Radio</th><th class="n">mm</th><th class="n">μ máx a alivio</th><th class="n">μ máx a alarma</th></tr>
        ${mm.map(([n, r]) => `<tr><td>${n}</td><td class="n">${fmt(r, 4)}</td><td class="n">${fmt(R.muMax(r))}</td><td class="n">${fmt(R.muMax(r) * P.p_alarm / P.p_relief)}</td></tr>`).join("")}</table>
        <div class="note">μ_máx = (n·F_calado·η_c·brazo_mín − T_pivote)/(N·r). Aproximación a alarma: proporcional a la presión.</div>
        <h3 style="margin-top:14px">Capacidad según el número de cilindros</h3>${cylCapTable()}
        <h3 style="margin-top:14px">Hidráulica</h3><div class="kv">
          <span>Área émbolo / anular</span><span>${fmt(R.A, 4)} / ${fmt(R.Aann, 4)} mm²</span>
          <span>F calado / alarma / retorno</span><span>${fmt(R.Fstall)} / ${fmt(R.Falarm)} / ${fmt(R.Fret)} kN</span>
          <span>Volumen por carrera (n cilindros)</span><span>${fmt(R.Vext / 1e6)} L</span>
          <span>Tiempo por ciclo / por vuelta</span><span>${fmt(R.tCycle)} / ${fmt(R.tRev)} min</span>
          <span>Avance (Q ${fmt(P.Q_pump)} L/min) / retorno (Q ${fmt(R.pump.Qr)} L/min)</span><span>${fmt(R.pump.tExt)} / ${fmt(R.pump.tRet)} min</span>
          <span>Velocidad del vástago: avance / retorno</span><span>${fmt(R.pump.vExt * 1000)} / ${fmt(R.pump.vRet * 1000)} mm/s</span>
          <span>Potencia hidráulica: avance / retorno</span><span>${fmt(R.pump.PhExt)} / ${fmt(R.pump.PhRet)} kW</span>
          <span>Potencia del motor (η ${fmt(P.eta_pump)})</span><span>${fmt(R.pump.Pmotor)} kW</span>
          ${R.pump.Qreq ? `<span>Caudal para ${fmt(P.t_vuelta_obj, 3)} min por vuelta</span><span>${fmt(R.pump.Qreq)} L/min</span>` : ""}
        </div>
        <h3 style="margin-top:14px">Control y seguridad: umbrales de presión</h3>
        <table><tr><th>Condición</th><th class="n">p (bar)</th></tr>
          ${[["Gira con μ nominal (esperada en operación)", R.cases.find((c) => c.id === "nom").p], ["Gira con μ de diseño", R.cases.find((c) => c.id === "dis").p], ["Gira contaminado", R.cases.find((c) => c.id === "cont").p], ["Alarma / detención", P.p_alarm], ["Válvula de alivio (calado)", P.p_relief]].map(([n, v]) => `<tr><td>${n}</td><td class="n">${fmt(v)}</td></tr>`).join("")}</table>
        <div class="note">Instalar transductor de presión en el puerto A (lectura y registro por ciclo), detención automática a la presión de alarma, válvulas de bloqueo en ambos cilindros, mando remoto con parada de emergencia y encoder de ángulo (un paso = ${fmt(360 / P.N_pin)}°; resolución recomendada ≤ 0,1°).</div>
        <div class="note">Ensayo de aceptación: con la presión de despegue medida p, μ_real = (n·p·A·η_c·brazo_mín − T_piv)/(N·${fmt(P.r_ef, 4)} mm). Aceptar si μ_real ≤ ${fmt(P.mu_d)}.</div></div></div>`;
  }

  /* ---------- Verificaciones ---------- */
  function fuBar(c) {
    if (c.fu == null || !isFinite(c.fu)) return "";
    const col = { ok: "var(--ok)", warn: "var(--warn)", fail: "var(--fail)" }[c.st] || "var(--steel)";
    return `<div class="fu"><i style="width:${Math.min(100, c.fu * 100)}%;background:${col}"></i></div>`;
  }
  function renderVerif() {
    const el = document.querySelector('section[data-t="verif"]');
    if (!A) { el.innerHTML = msgs(); return; }
    let g = "", rows = "";
    A.checks.forEach((c) => {
      if (c.grp !== g) { g = c.grp; rows += `<tr class="grp"><td colspan="7">${esc(g)}</td></tr>`; }
      rows += `<tr><td><span class="st st-${c.st}">${ST[c.st]}</span></td><td>${esc(c.name)}<div class="form">${esc(c.formula)}</div></td>
        <td class="n">${fmt(c.dem)}</td><td class="n">${c.cap != null ? fmt(c.cap) : ""}</td><td>${esc(c.unit || "")}</td>
        <td class="n">${c.fu != null && isFinite(c.fu) ? fu2(c.fu) : ""}${fuBar(c)}</td><td class="ref">${esc(c.ref)}</td></tr>`;
    });
    el.innerHTML = `<div class="note">Clasificación: FU ≤ 0,90 cumple; 0,90–1,00 monitoreo; &gt; 1,00 no cumple. Los chequeos de giro y geométricos son límites con margen propio: cumplen con FU ≤ 1,00. Cadena de empuje verificada a la fuerza de calado ${fmt(A.R.Fstall)} kN con ASME BTH-1 Nd = ${fmt(P.Nd)}.</div>
      <div class="card scroll"><table><tr><th>Estado</th><th>Verificación</th><th class="n">Demanda</th><th class="n">Capacidad</th><th>Unidad</th><th class="n">FU</th><th>Referencia</th></tr>${rows}</table></div>`;
  }

  /* ---------- FEA ---------- */
  function ramp(t) {   // secuencial claro → oscuro (azul → violeta → rojo)
    const stops = [[0, [236, 242, 250]], [0.35, [120, 170, 230]], [0.65, [70, 80, 190]], [0.85, [170, 40, 120]], [1, [200, 30, 30]]];
    t = Math.max(0, Math.min(1, t));
    for (let i = 1; i < stops.length; i++) if (t <= stops[i][0]) { const [a, ca] = stops[i - 1], [b, cb] = stops[i], f = (t - a) / (b - a); return `rgb(${ca.map((v, k) => Math.round(v + (cb[k] - v) * f)).join(",")})`; }
    return "rgb(200,30,30)";
  }
  function meshSVG(nodes, elems, vals, vmax, label, flipY) {
    const xs = nodes.map((p) => p[0]), ys = nodes.map((p) => p[1]);
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
    const pad = 20, s = 600 / Math.max(x1 - x0, y1 - y0);
    const X = (v) => pad + (v - x0) * s, Y = (v) => pad + (y1 - v) * s;
    let imax = 0; vals.forEach((v, i) => { if (v > vals[imax]) imax = i; });
    const polys = elems.map((e, i) => `<polygon points="${e.map((k) => X(nodes[k][0]) + "," + Y(nodes[k][1])).join(" ")}" fill="${ramp(vals[i] / vmax)}" stroke="${ramp(vals[i] / vmax)}" stroke-width=".4"/>`).join("");
    const em = elems[imax].map((k) => nodes[k]), cx = em.reduce((a, p) => a + p[0], 0) / 4, cy = em.reduce((a, p) => a + p[1], 0) / 4;
    const Wd = pad * 2 + (x1 - x0) * s, Hd = pad * 2 + (y1 - y0) * s;
    return `<svg viewBox="0 0 ${Wd} ${Hd + 56}" role="img" aria-label="${label}">${polys}<circle cx="${X(cx)}" cy="${Y(cy)}" r="7" fill="none" stroke="var(--ink)" stroke-width="2"/>
      <defs><linearGradient id="g${label.length}"><stop offset="0" stop-color="${ramp(0)}"/><stop offset=".35" stop-color="${ramp(.35)}"/><stop offset=".65" stop-color="${ramp(.65)}"/><stop offset=".85" stop-color="${ramp(.85)}"/><stop offset="1" stop-color="${ramp(1)}"/></linearGradient></defs>
      <rect x="${pad}" y="${Hd + 6}" width="260" height="14" fill="url(#g${label.length})"/><text x="${pad}" y="${Hd + 46}" font-size="22">0</text><text x="${pad + 260}" y="${Hd + 46}" font-size="22" text-anchor="end">${fmt(vmax)} MPa</text>
      <text x="${pad + 280}" y="${Hd + 22}" font-size="22">○ máx ${fmt(vals[imax])} MPa</text></svg>`;
  }
  function renderFEA() {
    const el = document.querySelector('section[data-t="fea"]');
    if (!A || !A.fea) { el.innerHTML = msgs(); return; }
    const F = A.fea, k = P.kFEA;
    const card = (t, r, txt) => {
      const vals = r.res.el.map((e) => e.vmGauss);
      return `<div class="card"><h3>${t}</h3>${meshSVG(r.model ? r.model.nodes : r.nodes, r.model ? r.model.elems : r.elems, vals, Math.max(...vals), t)}<div class="kv">${txt}</div></div>`;
    };
    el.innerHTML = `<div class="note">Placa Mindlin MITC4 (validada: Navier 0,05 %, voladizo Q4 1,4 %). Mesa: sector entre nervios con simetría; almas, nervios y pasadores como apoyos rígidos; cubo empotrado. Las tensiones de verificación se multiplican por k_malla = ${fmt(k)} (estudio de convergencia de la revisión independiente).</div>
    <div class="grid">
      ${card("Plancha superior (carga con excentricidad)", F.top, `<span>σvm máx (×k)</span><span>${fmt(F.top.vmMax)} (${fmt(F.top.vmMax * k)}) MPa</span><span>Ubicación r / θ</span><span>${fmt(F.top.maxAt[0], 4)} mm / ${fmt(F.top.maxAt[1])}°</span><span>Flecha máx.</span><span>${fmt(F.top.wMax)} mm</span><span>Carga de línea máx.</span><span>${fmt(F.top.lineMax)} N/mm</span><span>ΣF / ΣR</span><span>${fmt(F.top.Fapp)} / ${fmt(F.top.Rsum)} kN</span><span>Nodos · tiempo</span><span>${F.top.n} · ${fmt(F.top.ms)} ms</span>`)}
      ${card("Plancha inferior (contacto q_máx)", F.bot, `<span>σvm máx (×k)</span><span>${fmt(F.bot.vmMax)} (${fmt(F.bot.vmMax * k)}) MPa</span><span>Ubicación r / θ</span><span>${fmt(F.bot.maxAt[0], 4)} mm / ${fmt(F.bot.maxAt[1])}°</span><span>Flecha máx.</span><span>${fmt(F.bot.wMax)} mm</span><span>Carga de línea máx.</span><span>${fmt(F.bot.lineMax)} N/mm</span><span>ΣF / ΣR</span><span>${fmt(F.bot.Fapp)} / ${fmt(F.bot.Rsum)} kN</span><span>Nodos · tiempo</span><span>${F.bot.n} · ${fmt(F.bot.ms)} ms</span>`)}
      ${card("Izaje del conjunto: plancha base (¼ con simetría)", F.lift, `<span>σvm máx (×k)</span><span>${fmt(F.lift.vmMax)} (${fmt(F.lift.vmMax * k)}) MPa</span><span>Flecha máx.</span><span>${fmt(F.lift.wMax)} mm</span><span>ΣF / ΣR (conjunto)</span><span>${fmt(F.lift.Fapp)} / ${fmt(F.lift.Rsum)} kN</span><span>Factor dinámico</span><span>${fmt(P.phi_lift)}</span>`)}
      <div class="card"><h3>Flexión global del cajón (axisimétrica)</h3><div class="kv">
        <span>|M| máx</span><span>${fmt(F.glob.Mmax / 1e3)} kN·mm/mm a r = ${fmt(F.glob.rM, 3)} mm</span>
        <span>σ membrana sup. / inf.</span><span>${fmt(F.glob.sigTop)} / ${fmt(F.glob.sigBot)} MPa</span>
        <span>Corte total máx en nervios</span><span>${fmt(F.glob.Vmax)} kN a r = ${fmt(F.glob.rV, 3)} mm</span>
        <span>Desequilibrio en el borde</span><span>${fmt(F.glob.imbalance)} kN</span></div>
        <div class="note">Placa sándwich con borde libre: carga φd·W sobre la parrilla y reacción uniforme en la interfaz. La tensión de membrana se suma a la flexión local del FEA.</div></div>
    </div>`;
  }

  /* ---------- Masas ---------- */
  function renderMasa() {
    const el = document.querySelector('section[data-t="masa"]');
    if (!A) { el.innerHTML = msgs(); return; }
    const m = A.R.m;
    const parts = [["Plancha superior (con anillo)", m.top], ["Plancha inferior (con anillo)", m.bot], ["Almas anulares", m.webs], ["Nervios radiales", m.ribs], ["Cubo", m.hub], ["Pasadores de empuje", m.pins],
      ["Discos de acero inoxidable o disco duro (opción A, B o C)", m.ss], ["Lámina UHMW (opción B)", m.uhmw], ["Bronce con grafito (opción C)", m.bz], ["Cubierta de madera dura", m.wood], ["Plancha base", m.base], ["Marco perimetral", m.rim], ["Ménsulas de cilindro", m.brackets], ["Uñas", m.dogs], ["Pivote", m.pivot], ["Cilindros (comerciales)", m.cyl]];
    const mx = Math.max(...parts.map((p) => p[1]));
    el.innerHTML = `<div class="grid"><div class="card scroll"><h3>Desglose</h3><table><tr><th>Pieza</th><th class="n">kg</th><th class="n">%</th><th></th></tr>
      ${parts.map(([n, v]) => `<tr><td>${n}</td><td class="n">${fmt(v, 3)}</td><td class="n">${fmt(v / m.total * 100, 2)}</td><td style="width:40%"><div class="fu"><i style="width:${v / mx * 100}%;background:var(--acc)"></i></div></td></tr>`).join("")}
      <tr class="grp"><td>Total</td><td class="n">${fmt(m.total, 4)}</td><td class="n">100</td><td></td></tr></table>
      <div class="note">Masas de acero con ρ = 7850 kg/m³, sin soldadura ni pintura (agregar ≈ 2 %). No incluye bomba, mangueras ni plancha diamantada.</div></div>
      <div class="card"><h3>Transporte</h3><div class="kv"><span>Masa total</span><span>${fmt(m.total, 4)} kg</span><span>Mesa (izable por separado)</span><span>${fmt(m.disc + m.ssTop + m.pivot, 4)} kg</span><span>Base + ménsulas</span><span>${fmt(m.base + m.rim + m.brackets, 4)} kg</span><span>Dimensiones en planta</span><span>${fmt(P.B, 4)} × ${fmt(P.B, 4)} mm</span><span>Alto total</span><span>${fmt(P.t_base + A.R.ifc.delta + P.h_disc + (P.opt_wood > 0.5 ? P.t_wood : 0), 3)} mm</span><span>Referencia KIET 400T</span><span>${fmt(REF.KIET, 4)} kg</span></div>
      <div class="note">Use el optimizador para reducir la masa manteniendo todas las verificaciones (FU ≤ 0,90 en estructura y giro asegurado).</div></div></div>`;
  }

  /* ---------- Agentes ---------- */
  function renderAgentes() {
    const el = document.querySelector('section[data-t="agentes"]');
    if (!A) { el.innerHTML = `<div class="card"><h3>1 · Validador de entradas</h3>${msgs()}</div>`; return; }
    const xc = X.map((c) => `<tr><td><span class="st st-${c.ok ? "ok" : "fail"}">${c.ok ? "OK" : "Revisar"}</span></td><td>${esc(c.name)}</td><td class="n">${fmt(c.tool, 4)}</td><td class="n">${fmt(c.indep, 4)}</td><td class="n">${fmt(c.d, 2)} %</td><td class="ref">${esc(c.note || "")}${c.tol != null ? " · tol. " + fmt(c.tol) + " %" : ""}</td></tr>`).join("");
    const sg = SC.grid.map((row) => `<tr><td class="n">${fmt(row[0].mu)}</td>${row.map((c) => `<td class="n"><span class="st st-${c.FS >= P.FS_min ? "ok" : c.FS >= 1 ? "warn" : "fail"}">FS ${fmt(c.FS)}</span><div class="form">${fmt(c.p)} bar</div></td>`).join("")}</tr>`).join("");
    el.innerHTML = `<div class="grid">
      <div class="card"><h3>1 · Validador de entradas</h3>${msgs()}</div>
      <div class="card"><h3>2 · Auditor normativo</h3>${AU.ok ? `<div class="msg ok">Las ${A.checks.length} verificaciones declaran fórmula y referencia.</div>` : `<div class="msg error">${AU.missing.length} verificaciones sin referencia: ${AU.missing.map((c) => esc(c.name)).join(", ")}</div>`}
        <table><tr><th>Referencia</th><th class="n">N°</th></tr>${AU.refs.map(([r, n]) => `<tr><td class="ref">${esc(r)}</td><td class="n">${n}</td></tr>`).join("")}</table></div></div>
      <div class="card scroll" style="margin-top:12px"><h3>3 · Revisor cruzado (formulación independiente)</h3><table><tr><th>Estado</th><th>Magnitud</th><th class="n">Herramienta</th><th class="n">Independiente</th><th class="n">Δ</th><th>Nota</th></tr>${xc}</table></div>
      <div class="grid" style="margin-top:12px">
      <div class="card scroll"><h3>4 · Escenarios de fricción (FS al calado)</h3><table><tr><th class="n">μ</th>${SC.rs.map(([n, r]) => `<th class="n">${n} = ${fmt(r, 4)} mm</th>`).join("")}</tr>${sg}</table>
        <div class="note">Verde: FS ≥ FS_min (${fmt(P.FS_min)}); ámbar: gira sin el margen exigido; rojo: no gira.</div></div>
      <div class="card"><h3>4 · Escenarios de carga (caso de diseño)</h3><table><tr><th class="n">W (tf)</th><th class="n">FS</th><th class="n">p (bar)</th><th class="n">μ máx (r_ef)</th></tr>
        ${SC.loads.map((l) => `<tr><td class="n">${fmt(l.W, 3)}</td><td class="n">${fmt(l.FS)}</td><td class="n">${fmt(l.p)}</td><td class="n">${fmt(l.muMax)}</td></tr>`).join("")}</table></div>
      <div class="card"><h3>4 · Clase de presión del cilindro (caso de diseño)</h3><table><tr><th class="n">Clase (psi)</th><th class="n">Alivio / alarma (bar)</th><th class="n">Émbolo mínimo (mm)</th><th class="n">FS con Ø${fmt(P.D_bore, 3)}</th><th class="n">p dis. (bar)</th></tr>
        ${(SC.classes || []).map((c) => `<tr><td class="n">${fmt(c.psi, 5)}</td><td class="n">${fmt(c.pr, 3)} / ${fmt(c.pa, 3)}</td><td class="n">${fmt(c.Dmin, 3)}</td><td class="n">${fmt(c.FScur)}</td><td class="n">${fmt(c.pcur, 3)}</td></tr>`).join("")}</table>
        <div class="note">Émbolo mínimo = máx(FS_min·F_dis/p_alivio; F_dis/p_alarma), con alarma = 0,85·alivio. Al cambiar de clase, ajuste también Ø del cuerpo, masa y cotas del cilindro según catálogo; la herramienta verifica el resto.</div></div></div>`;
  }

  /* ---------- Optimizador ---------- */
  function renderOpt() {
    const el = document.querySelector('section[data-t="opt"]');
    const vars = AG.VARS.map(([k]) => k);
    const lab = (k) => { for (const g of TT.PARAM_GROUPS) for (const p of g.p) if (p[0] === k) return p[1]; return k; };
    let res = "";
    if (optRes) {
      const ch = vars.filter((k) => optRes.P[k] !== optRes.P0[k]);
      res = `<div class="msg ${optRes.ok ? "ok" : "error"}">${optRes.ok ? "Configuración factible encontrada" : esc(optRes.msg || "No se encontró configuración factible")} · ${optRes.evals} evaluaciones · masa ${fmt(optRes.m0, 4)} → ${fmt(optRes.A.R.m.total, 4)} kg (${fmt((optRes.A.R.m.total - optRes.m0) / optRes.m0 * 100, 2)} %)</div>
        <table><tr><th>Variable</th><th class="n">Actual</th><th class="n">Optimizado</th></tr>${ch.map((k) => `<tr><td>${esc(lab(k))}</td><td class="n">${fmt(optRes.P0[k], 4)}</td><td class="n">${fmt(optRes.P[k], 4)}</td></tr>`).join("") || `<tr><td colspan="3">Sin cambios</td></tr>`}</table>
        <div class="btns"><button class="pri" id="bApply" ${optRes.ok ? "" : "disabled"}>Aplicar al modelo</button></div>`;
    }
    el.innerHTML = `<div class="card"><h3>Optimizador de peso</h3>
      <div class="note">Minimiza la masa total con tamaños comerciales (espesores de plancha, diámetros, largos) manteniendo: giro asegurado (todos los chequeos de giro) y FU ≤ objetivo en estructura. Búsqueda por coordenadas con FEA escalada (σ ∝ q/t²); el resultado final se confirma con FEA nueva en malla fina. No cambia la geometría de cinemática, la capacidad ni los materiales.</div>
      <div class="prm" style="max-width:340px;padding:0"><label for="optT">FU objetivo en estructura</label><input id="optT" type="number" step="0.01" min="0.5" max="1" value="0.90"></div>
      <div class="btns"><button class="pri" id="bRun" ${optRunning || !A ? "disabled" : ""}>${optRunning ? "Optimizando…" : "Ejecutar"}</button></div>
      <div class="prog"><i id="optBar"></i></div><div class="busy" id="optMsg"></div>${res}</div>`;
    const b = $("#bRun"); if (b) b.onclick = runOpt;
    const ap = $("#bApply"); if (ap) ap.onclick = () => { P = Object.assign({}, optRes.P); optRes = null; buildForm(); recalc(); showTab("resumen"); };
  }
  function runOpt() {
    if (optRunning || !A) return;
    optRunning = true; renderOpt();
    const target = parseFloat(($("#optT") || {}).value) || 0.9;
    const P0 = Object.assign({}, P), m0 = A.R.m.total;
    const gen = AG.optimizeGen(P0, { target });
    let last = null;
    const step = () => {
      const t0 = performance.now();
      while (performance.now() - t0 < 60) {
        const r = gen.next();
        if (r.done) { optRunning = false; optRes = Object.assign({}, last, { P0, m0 }); renderOpt(); return; }
        last = r.value;
        if (last.phase === "fin") break;
      }
      const bar = $("#optBar"), msg = $("#optMsg");
      if (bar) bar.style.width = Math.min(100, last.evals / 1.2) + "%";
      if (msg) msg.textContent = `Fase: ${last.phase} · evaluaciones ${last.evals} · masa ${fmt(last.A.R.m.total, 4)} kg`;
      setTimeout(step, 0);
    };
    setTimeout(step, 30);
  }

  function renderAll() {
    renderBadges(); renderResumen(); renderModelo(); renderGiro(); renderVerif(); renderFEA(); renderMasa(); renderAgentes(); renderOpt();
  }
  buildForm(); recalc();
})();
