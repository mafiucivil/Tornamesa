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
    if (t === "temp" && typeof renderTemp === "function") setTimeout(renderTemp, 0);
    if (t === "tapones" && typeof renderTapones === "function") setTimeout(renderTapones, 0);
    if (t === "planos") setTimeout(() => { if (!GEN.srv && !GEN.pinging) genPing(); }, 0);   // el generador local se busca solo al abrir la pestaña «Planos»
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
    syncAlt();
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
    syncAlt();
    clearTimeout(tmr); $("#busy").textContent = "Calculando…";
    tmr = setTimeout(recalc, 380);
  });
  /* ---------- selector de la alternativa de interfaz (sincronizado con las casillas A, B, C y la configuración de C) ---------- */
  function syncAlt() {
    const v = P.opt_ss ? "A" : P.opt_uhmw ? "B" : P.opt_bz ? "C" + Math.min(3, Math.max(1, Math.round(P.bz_conf || 1))) : "0";
    const sel = $("#altSel"); if (sel) sel.value = v;
  }
  $("#altSel").onchange = (e) => {
    const v = e.target.value;
    P.opt_ss = v === "A" ? 1 : 0; P.opt_uhmw = v === "B" ? 1 : 0; P.opt_bz = v[0] === "C" ? 1 : 0;
    P.bz_conf = v[0] === "C" ? parseInt(v[1], 10) : DEF.bz_conf;   // fuera de C vuelve al valor por defecto (los juegos pre-generados A, B y Base lo usan)
    buildForm(); recalc();
  };
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
    return `<div class="scroll"><table><tr><th>Alternativa</th><th class="n">Disco inox o duro req. → adoptado (mm) (base / mesa con ranuras)</th><th class="n">UHMW req. → adoptado (mm)</th><th class="n">Bronce req. → adoptado (mm)</th><th class="n">Altura agregada (mm)</th><th class="n">Δ masa total (kg)</th><th class="n">Masa total (kg)</th><th class="n">μ diseño</th><th class="n">F/cil diseño (kN)</th><th class="n">p diseño (bar)</th><th class="n">FS diseño</th></tr>
      ${rows.map((r) => `<tr${r.k === act ? ' class="grp"' : ""}><td>${r.k === act ? "● " : ""}${esc(r.name)}</td><td class="n">${r.k ? g(r.tssReq, 3) + " → " + fmt(r.tss, 3) + (r.tss2 !== r.tss || r.tss2Req !== r.tssReq ? " / " + g(r.tss2Req, 3) + " → " + fmt(r.tss2, 3) : "") : "—"}</td><td class="n">${r.k === 2 ? g(r.tuhReq, 3) + " → " + fmt(r.tuh, 3) : "—"}</td><td class="n">${r.k === 3 ? g(r.tbzReq, 3) + " → " + fmt(r.tbz, 3) : "—"}</td><td class="n">${g(r.delta)}</td><td class="n">${r.k ? "+" + fmt(r.dTot, 3) : "—"}</td><td class="n">${fmt(r.mass, 4)}</td><td class="n">${fmt(r.mu_d)}</td><td class="n">${fmt(r.F)}</td><td class="n">${fmt(r.p)}</td><td class="n">${fmt(r.FS)}</td></tr>`).join("")}</table></div>
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
        : [[tb, ifc.tss, "var(--acc)", "disco inox"], ...(ifc.o === 2 ? [[tb + ifc.tss, ifc.tuh, "var(--warn)", "UHMW"]] : []), [tb + ifc.tss + (ifc.o === 2 ? ifc.tuh : 0), ifc.tss2, "var(--acc)", "disco inox"]];
      zs.forEach(([z0, t, c, n], k) => o.push(`<rect x="${X(rI)}" y="${Z(z0 + t)}" width="${X(Rt) - X(rI)}" height="${t}" fill="${c}" opacity="${n === "UHMW" ? 0.85 : 0.75}" stroke="var(--ink)" stroke-width=".6"><title>${n} ${fmt(t, 3)} mm</title></rect>`));
      o.push(`<text x="${X(r0) + 250}" y="${Z(tb) + 14}" font-size="13" fill="var(--ink)">${ifc.o === 3 ? "bronce " + fmt(ifc.tbz, 3) + " + " + (ifc.conf === 2 ? "bronce " : "disco duro ") + fmt(ifc.tss, 3) : ifc.o === 2 ? "inox " + fmt(ifc.tss, 3) + " + UHMW " + fmt(ifc.tuh, 3) + " + inox " + fmt(ifc.tss2, 3) : "inox " + fmt(ifc.tss, 3) + " + inox " + fmt(ifc.tss2, 3) + " (ranurado)"} mm</text>`);
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
      <div class="note">* μ implícito = n·F·a/(N·r_u) con la fuerza de calado y el brazo mínimo: es la fricción que el equipo vence al límite del alivio, sin factor de seguridad. Datos de los equipos comerciales: fichas y planos públicos (Enerpac, KIET); el brazo y el radio de fricción son estimaciones. En Enerpac el brazo igual al radio de la plataforma es una cota superior (el μ implícito baja ≈ 10 % con un brazo 10 % menor); 12,5° por carrera es un valor nominal; KIET declara 400 t en el plano y 500 t en el manual (con 500 t el μ implícito baja de 0,26 a 0,21). La masa por kN no mide eficiencia estructural: los ETT200 y ETT400 pesan casi lo mismo.</div>
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
          <span>Tiempo por ciclo / por vuelta (mínimo teórico, ± 5 %)</span><span>${fmt(R.tCycle)} / ${fmt(R.tRev)} min</span>
          <span>Avance (Q ${fmt(P.Q_pump)} L/min) / retorno (Q ${fmt(R.pump.Qr)} L/min)</span><span>${fmt(R.pump.tExt)} / ${fmt(R.pump.tRet)} min</span>
          <span>Velocidad del vástago: avance / retorno</span><span>${fmt(R.pump.vExt * 1000)} / ${fmt(R.pump.vRet * 1000)} mm/s</span>
          <span>Potencia hidráulica: avance / retorno</span><span>${fmt(R.pump.PhExt)} / ${fmt(R.pump.PhRet)} kW</span>
          <span>Potencia del motor (η ${fmt(P.eta_pump)}): a presión de diseño / de alarma</span><span>${fmt(R.pump.Pmotor)} / ${fmt(R.pump.PmotorAlarm)} kW</span>
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
      ["Discos de acero inoxidable o disco duro (opción A, B o C)", m.ss], ["Lámina UHMW (opción B)", m.uhmw], ["Bronce con grafito (opción C)", m.bz], ["Cubierta de madera dura", m.wood], ["Anillo de acero de la madera", m.ring], ["Barras de los topes soldados", m.stopBars], ["Plancha base", m.base], ["Marco perimetral", m.rim], ["Ménsulas de cilindro", m.brackets], ["Uñas", m.dogs], ["Pivote", m.pivot], ["Cilindros (comerciales)", m.cyl]];
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

  /* ---------- Paquete de dibujo (checkbox «Exportar paquete de dibujo») ---------- */
  const LSK = "tt300c-pkg";
  let pkgSelId = "";
  const SHEET_IDS = (typeof PLANOS !== "undefined") ? PLANOS.SHEETS.map((x) => x.id) : [];
  /* ---------- Temperatura (exposición solar): escenario aparte, geometría de 20 °C congelada ---------- */
  let TH = null, THkey = "";
  const confB = (c) => { const k = c === "A" ? "A" : /C/.test(c || "C") ? "C" : "B"; return `<span class="conf conf-${k}" title="Nivel de confianza del dato (registro): A tabla contrastada · B ficha o dos fuentes · C supuesto o fuente única">${esc(c || "C")}</span>`; };
  const stCell = (st, txt) => `<td class="n c-${st === "info" || st === "pend" ? "ok" : st}">${txt}</td>`;
  const pct = (v) => (v == null || !isFinite(v) ? "—" : (v >= 0 ? "+" : "") + fmt(v, 3) + " %");
  function altId() { return (P.opt_ss ? "A" : P.opt_uhmw ? "B" : P.opt_bz ? "C" + Math.min(3, Math.max(1, Math.round(P.bz_conf || 1))) : "base") + (P.opt_wood > 0.5 ? "+madera" : ""); }
  function setTemp(id, v) {
    P[id] = v; const inp = $("#p_" + id); if (inp) { inp.value = v; inp.closest(".prm").classList.toggle("chg", P[id] !== DEF[id]); }
    store.set(LS, JSON.stringify(P)); renderTemp();
  }
  function renderTemp() {
    const el = document.querySelector('section[data-t="temp"]');
    if (cur !== "temp") return;
    const ctl = `<div class="card"><h3>Escenario térmico · tornamesa expuesta al sol</h3><div class="tmp-ctl">
        <label for="tServ">T del cuerpo (°C)</label><input id="tServ" type="number" min="20" max="120" step="5" value="${esc(P.T_serv)}">
        <label for="dTgrad">Gradiente plancha superior–inferior (K)</label><input id="dTgrad" type="number" min="0" max="40" step="1" value="${esc(P.dT_grad)}">
        <button class="pri" id="bSolar" title="Fija T_serv = 80 °C y dT_grad = 15 K (hipótesis de la sección «Temperatura (exposición solar, 80 °C)» del registro)">Escenario solar 80 °C</button>
        <button id="bFrio" title="Vuelve a T_serv = 20 °C y sin gradiente (el escenario muestra entonces el solar por defecto)">T_serv = 20 °C</button>
        <label for="tAlc">Alcance</label><select id="tAlc" title="term_alcance: 1 = sistema de placas y disco; 2 = además accionamiento mecánico y circuito hidráulico (reproduce el escenario anterior)"><option value="1"${Math.round(P.term_alcance) !== 2 ? " selected" : ""}>Placas y disco</option><option value="2"${Math.round(P.term_alcance) === 2 ? " selected" : ""}>+ accionamiento y circuito hidráulico</option></select></div>
        <div class="msg ok"><b>Alcance:</b> ${Math.round(P.term_alcance) === 2 ? "placas y disco más accionamiento mecánico y circuito hidráulico (cilindros, aceite atrapado, alivio térmico, sellos, viscosidad y bomba)." : "la temperatura se evalúa en el <b>sistema de placas y disco</b>: plancha base, mesa, interfaz (discos, UHMW, bronce y disco duro, pastillas, grasa y ranuras), topes y soldaduras, madera, pivote, buje y collar. Los pistones, el aceite, las válvulas, los sellos, la bomba y el accionamiento mecánico están <b>fuera de alcance</b> (se informan aparte, sin afectar el veredicto)."}</div>
        <div class="note">Escenario aparte: las demás pestañas siguen a 20 °C. La geometría (espesores de discos y lámina, largos de tope, juntas) se dimensiona a 20 °C y se congela: aquí se evalúa esa misma geometría con las capacidades reducidas a la temperatura. Sin T_serv definida (20 °C) se muestra el escenario solar de 80 °C con 15 K. Todos los factores y límites están en el grupo «Temperatura» del panel izquierdo.</div></div>`;
    const bind = () => {
      $("#tServ").onchange = (e) => setTemp("T_serv", Math.min(120, Math.max(20, parseFloat(e.target.value) || 20)));
      $("#dTgrad").onchange = (e) => setTemp("dT_grad", Math.min(40, Math.max(0, parseFloat(e.target.value) || 0)));
      $("#bSolar").onclick = () => { P.T_serv = 80; P.dT_grad = 15; ["T_serv", "dT_grad"].forEach((k) => { const inp = $("#p_" + k); if (inp) { inp.value = P[k]; inp.closest(".prm").classList.toggle("chg", P[k] !== DEF[k]); } }); store.set(LS, JSON.stringify(P)); renderTemp(); };
      $("#tAlc").onchange = (e) => { P.term_alcance = parseInt(e.target.value, 10) === 2 ? 2 : 1; const inp = $("#p_term_alcance"); if (inp) { inp.value = P.term_alcance; inp.closest(".prm").classList.toggle("chg", P.term_alcance !== DEF.term_alcance); } store.set(LS, JSON.stringify(P)); renderTemp(); };
      $("#bFrio").onclick = () => { P.T_serv = 20; P.dT_grad = 0; ["T_serv", "dT_grad"].forEach((k) => { const inp = $("#p_" + k); if (inp) { inp.value = P[k]; inp.closest(".prm").classList.toggle("chg", P[k] !== DEF[k]); } }); store.set(LS, JSON.stringify(P)); renderTemp(); };
    };
    if (!A) { el.innerHTML = ctl + msgs(); bind(); return; }
    const key = JSON.stringify(P);
    if (key !== THkey) {
      el.innerHTML = ctl + `<div class="busy">Calculando el escenario térmico de las 6 alternativas…</div>`; bind();
      setTimeout(() => { try { TH = TT.thermal(P, { wood: "form" }); THkey = key; } catch (err) { TH = null; el.innerHTML = ctl + `<div class="msg error">Error de cálculo térmico: ${esc(err.message)}</div>`; bind(); return; } renderTemp(); }, 30);
      return;
    }
    el.innerHTML = ctl + tempBody(TH); bind();
  }
  function tempBody(r) {
    const at = (a, T) => a.byT.find((b) => Math.abs(b.T - T) < 1e-9), id0 = altId(), act = r.alternativas.find((a) => a.id === id0) || r.alternativas[0], Tn = r.T_scn;
    const bitem = (a) => at(a, Tn), b20 = (a) => at(a, r.T_ref) || a.byT[0];
    const ver = (b) => (b.gira && b.estructura && b.termico ? "ok" : !b.gira || !b.estructura ? "fail" : "warn");
    const tags = (b) => `${b.gira ? "" : '<span class="st st-fail">No gira con FS_mín</span> '}${b.estructura ? "" : '<span class="st st-fail">Estructura/juntas</span> '}${b.termico ? "" : `<span class="st st-fail">Térmica: ${r.alcance === 2 ? "aceite/" : ""}gradiente/juntas</span>`}${b.gira && b.estructura && b.termico ? '<span class="st st-ok">Cumple</span>' : ""}`;
    const gov = (g) => (g ? esc(g.grp + ": " + g.nombre) + ` <span class="ref">(FU ${fu2(g.fu)})</span>` : "—");
    const warns = `<div class="msg warn"><b>Datos supuestos (confianza C):</b> los de UHMW-PE, acero inoxidable y bronce son de ficha de fabricante o supuestos (el UHMW-PE no tiene curva publicada a 80 °C y 80 °C es su límite de servicio continuo): confirmar con el proveedor antes de decidir.</div>
      <div class="msg warn"><b>ASME BTH-1:</b> el rango estándar es −4 a 66 °C; a 80 °C (176 °F) la sección de BTH-1 sobre temperatura no está confirmada y exige decisión de persona calificada (Nd = 3,0 no incluye margen térmico).</div>
      ${r.alcance === 2 ? `<div class="msg error"><b>Aceite atrapado:</b> un tramo aislado (cilindro + válvulas de retención) calentado ${fmt(Tn - r.T_ref, 3)} K sube ≈ ${fmt((r.aceite.find((o) => Math.abs(o.T - Tn) < 1e-9) || { cilindro: { alto: 0 } }).cilindro.alto, 3)} bar si el movimiento está restringido (tope, fin de carrera, calado): instalar válvula de alivio térmico en el tramo aislado; un alivio de sistema aguas arriba de la retención no lo protege.</div>` : `<div class="note"><b>Nota informativa (fuera de alcance):</b> un tramo aislado de aceite (cilindro + válvulas de retención o bloqueo) calentado ${fmt(Tn - r.T_ref, 3)} K subiría ≈ ${fmt((r.aceite.find((o) => Math.abs(o.T - Tn) < 1e-9) || { cilindro: { alto: 0 } }).cilindro.alto, 3)} bar si el movimiento está restringido: exige válvula de alivio térmico en ese tramo. El circuito hidráulico no entra en este escenario (alcance 2 lo reactiva).</div>`}
      ${Tn > 80 ? `<div class="msg warn">T &gt; 80 °C: factores extrapolados linealmente desde el valor tabulado a 80 °C; orden de magnitud.</div>` : ""}`;
    // 1. Tabla por alternativa al escenario
    const t1 = r.alternativas.map((a) => {
      const b = bitem(a), z = b20(a), me = id0 === a.id;
      const dFS = b.FS / z.FS - 1, dFu = z.fuEst > 0 ? b.fuEst / z.fuEst - 1 : null, dMass = b.masa - z.masa;
      return `<tr${me ? ' class="grp"' : ""}><td>${me ? "● " : ""}${esc(a.nombre)}</td>
        <td class="n">${fmt(z.FS)} → ${fmt(b.FS)}<div class="ref">${pct(dFS * 100)}</div></td>
        <td class="n">${fu2(z.fuEst)} → ${fu2(b.fuEst)}<div class="ref">${pct(dFu == null ? null : dFu * 100)}</div></td>
        <td>${gov(b.gobernante)}</td>
        <td class="n">${fu2(z.fuTerm)} → ${fu2(b.fuTerm)}</td><td>${gov(b.gobernanteTerm)}</td>
        <td class="n">${fmt(b.masa, 4)}${dMass ? ` (${pct(dMass / z.masa * 100)})` : ""}</td>
        <td>${tags(b)}</td><td class="n">${b.cambian.filter((c) => c.empeora).length}</td></tr>`;
    }).join("");
    // 2. Matrices de sensibilidad a la temperatura
    const hdr = r.T.map((T) => `<th class="n">${fmt(T, 3)} °C</th>`).join("");
    const mx = (f, cls) => r.alternativas.map((a) => `<tr${id0 === a.id ? ' class="grp"' : ""}><td>${id0 === a.id ? "● " : ""}${esc(a.nombre)}</td>${r.T.map((T) => { const b = at(a, T); return cls(b, f(b)); }).join("")}</tr>`).join("");
    const cell = (kind) => (b, v) => `<td class="n c-${kind === "est" ? (b.estructura ? (b.fuEst > 0.9 ? "warn" : "ok") : "fail") : kind === "term" ? (b.termico ? (b.fuTerm > 0.9 ? "warn" : "ok") : "fail") : b.gira ? "ok" : "fail"}">${v}</td>`;
    const t2 = mx((b) => fu2(b.fuEst), cell("est")), t3 = mx((b) => fu2(b.fuTerm), cell("term")), t4 = mx((b) => fmt(b.FS), cell("giro")), t5 = mx((b) => b.nFail, (b, v) => `<td class="n c-${v ? "fail" : "ok"}">${v}</td>`);
    const kf = r.factores.find((f) => Math.abs(f.T - Tn) < 1e-9) || r.factores[r.factores.length - 1];
    const fk = `Fy acero ${fu2(kf.k.Fy)} · Fy inox ${fu2(kf.k.Fy_ss)} · E inox ${fmt(kf.k.E_ss, 3)} · UHMW k_p ${fu2(kf.k.p_uh)} / k_E ${fu2(kf.k.E_uh)} · bronce ${fu2(kf.k.bz)} · madera C_t ${fu2(kf.k.wood)} · perno ${fu2(kf.k.bolt)}`;
    // 3. Detalle de la alternativa activa
    const a = act, b = bitem(a), z = b20(a);
    const lst = (arr, st) => arr.map((x) => `<tr><td>${esc(x.grp)}: ${esc(x.nombre)}</td><td class="n">${fu2(x.fu20)}</td><td class="n">${fu2(x.fuT)}</td><td class="n">${pct(x.var_pct)}</td><td><span class="st st-${x.st20}">${ST[x.st20]}</span> → <span class="st st-${x.stT}">${ST[x.stT]}</span></td><td>${confB(x.conf)}</td></tr>`).join("") || `<tr><td colspan="6" class="ref">Ninguna</td></tr>`;
    const chg = b.cambian.filter((c) => c.empeora).map((c) => `<tr><td>${esc(c.grp)}: ${esc(c.nombre)}</td><td><span class="st st-${c.de}">${ST[c.de]}</span> → <span class="st st-${c.a}">${ST[c.a]}</span></td><td class="n">${fu2(c.fu20)} → ${fu2(c.fuT)}</td><td>${confB(c.conf)}</td></tr>`).join("") || `<tr><td colspan="4" class="ref">Ninguna verificación empeora de estado</td></tr>`;
    const jun = a.juntas.length ? a.juntas.map((j) => `<tr><td>${esc(j.pieza)}</td><td class="n">${fmt(j.j_req)} mm</td><td class="n">${fmt(j.j_disp)} mm</td><td class="n">${fu2(j.fu)}</td><td><span class="st st-${j.estado}">${j.estado === "fail" ? "Cierra" : ST[j.estado]}</span></td></tr>`).join("") : `<tr><td colspan="5" class="ref">Sin sectores con junta (acero–acero o pegado permanente)</td></tr>`;
    const rowT = (re) => b.filas.find((f) => re.test(f.nombre));
    const hs = [["Buje de bronce en el pivote", rowT(/cierre de la holgura diametral/)], ["Uña–pasador: holgura radial (mesa caliente, base a la sombra)", rowT(/holgura radial de la uña/)], ["Patín fuera de la mesa caliente", rowT(/Patín fuera de la mesa/)]].filter((x) => x[1]).map(([n, f]) => `<tr><td>${esc(n)}</td><td class="n">${fmt(f.dem, 3)} ${esc(f.unidad)}</td><td class="n">${fmt(f.cap, 4)}</td><td><span class="st st-${f.estado}">${ST[f.estado]}</span></td></tr>`).join("");
    const od = r.aceite.map((o) => `<tr${Math.abs(o.T - Tn) < 1e-9 ? ' class="grp"' : ""}><td class="n">${fmt(o.T, 3)}</td><td class="n">${fmt(o.rigido.bajo, 3)} – ${fmt(o.rigido.alto, 3)}</td><td class="n">${fmt(o.cilindro.bajo, 3)} – ${fmt(o.cilindro.alto, 3)}</td><td class="n">${fmt(o.manguera, 3)}</td></tr>`).join("");
    const oilRows = ["carrera de diseño: p_hold", "tras el calado", "cámara anular", "Válvula de alivio térmico del tramo"].map((k) => b.filas.find((f) => f.nombre.indexOf(k) >= 0)).filter(Boolean)
      .map((f) => `<tr><td>${esc(f.nombre)}</td><td class="n">${fmt(f.dem, 4)} bar</td><td class="n">${fmt(f.cap, 4)} bar</td><td class="n">${fu2(f.fu)}</td><td><span class="st st-${f.estado}">${ST[f.estado]}</span></td></tr>`).join("");
    const sm = a.sens, mu = sm.mu.map((m) => `<td class="n c-${m.gira ? "ok" : "fail"}">${fmt(m.FS)}</td>`).join("");
    const uh = sm.uhmw ? `<div class="card" style="margin-top:12px"><h3>Sensibilidad del UHMW-PE (opción B) a k_p y k_E a ${fmt(Tn, 3)} °C</h3><div class="scroll"><table><tr><th>k</th>${sm.uhmw.kp.map((x) => `<th class="n">${fu2(x.k_p)}</th>`).join("")}</tr>
        <tr><td>FU máx. de la lámina según k_p (k_E = ${fu2(P.kT_E_uh)})</td>${sm.uhmw.kp.map((x) => `<td class="n c-${x.cumple ? "ok" : "fail"}">${x.fuUHMW >= 99 ? "&gt; 99" : fu2(x.fuUHMW)}</td>`).join("")}</tr>
        <tr><td>FU máx. de la lámina según k_E (k_p = ${fu2(P.kT_p_uh)})</td>${sm.uhmw.kE.map((x) => `<td class="n c-${x.cumple ? "ok" : "fail"}">${x.fuUHMW >= 99 ? "&gt; 99" : fu2(x.fuUHMW)}</td>`).join("")}</tr></table></div>
        <div class="note">k_p mínimo con el que la lámina cumple a esa temperatura: <b>${sm.uhmw.kp_crit == null ? "ninguno" : fu2(sm.uhmw.kp_crit)}</b>. El factor de 0,40 es supuesto: exigir al proveedor la curva de módulo y de límite elástico entre 20 y 80 °C; el creep (módulo de fluencia 550 → 300 MPa de 1 h a 1 000 h) y el desgaste crecen con la temperatura (sin dato).</div></div>` : "";
    const wd = sm.madera ? `<div class="note">Madera: aplastamiento con C_t 0,70 (seca) FU ${fu2(sm.madera[0].fu)} · con C_t 0,50 (húmeda) FU ${fu2(sm.madera[1].fu)}; el secado al sol agrieta los tablones (nota).</div>` : "";
    const oilCards = `<div class="grid" style="margin-top:12px">
      <div class="card scroll"><h3>Aceite atrapado: Δp térmico por temperatura (bar)</h3><table><tr><th class="n">T (°C)</th><th class="n">Recipiente rígido (K 1,4 – 1,9 GPa)</th><th class="n">Cilindro (Lamé, b/a ${fu2(P.ba_cil)})</th><th class="n">Manguera (K ≈ 0,33 GPa)</th></tr>${od}</table>
        <div class="note">Δp = (α_v − 3α_s)·ΔT/(1/K_aceite + 1/K_c). A mayor K la presión es mayor: gobierna la cota de 1,9 GPa. Con el pistón libre la presión se mantiene y la expansión sale como carrera; la sobrepresión aparece con movimiento restringido.</div></div>
      <div class="card scroll"><h3>Presiones atrapadas a ${fmt(Tn, 3)} °C frente al cilindro (${fmt(P.p_max_cil, 3)} bar, prueba ${fmt(1.5 * P.p_max_cil, 4)} bar)</h3><table><tr><th>Verificación</th><th class="n">Demanda</th><th class="n">Límite</th><th class="n">FU</th><th>Estado</th></tr>${oilRows}</table>
        <div class="note">Tramo aislado = cilindro + retenciones. ${P.alivio_term > 0 ? `Alivio térmico a ${fmt(P.alivio_term, 3)} bar.` : "Sin válvula de alivio térmico (alivio_term = 0): instalar válvula de alivio térmico en el tramo aislado."}</div></div></div>`;
    // Accionamiento mecánico y circuito hidráulico: fuera del alcance del escenario (term_alcance = 1). Se calculan y se informan, sin estado que afecte el veredicto.
    const fa = (b.fuera_alcance || []).slice().sort((x, y) => (isFinite(y.fu) ? y.fu : 99) - (isFinite(x.fu) ? x.fu : 99));
    const faRows = fa.slice(0, 40).map((x) => `<tr><td>${esc(x.grp)}</td><td>${esc(x.nombre)}</td><td class="n">${fu2(x.fu20)}</td><td class="n">${fu2(x.fu)}</td><td><span class="st st-info" title="Estado calculado, informativo: no entra en el veredicto">${x.estado_informativo === "fail" ? "no cumpliría" : x.estado_informativo === "warn" ? "monitoreo" : x.estado_informativo === "ok" ? "cumpliría" : esc(x.estado_informativo)}</span></td></tr>`).join("");
    const outScope = `<div class="card scroll" style="margin-top:12px"><h3>Accionamiento y circuito hidráulico (fuera de alcance) · ${esc(a.nombre)}</h3>
      <div class="msg warn">Solo informativo: ${fa.length} verificaciones (cilindros, aceite atrapado, válvulas de alivio térmico, sellos, viscosidad y bomba, uña–pasador, patín–guía, pasadores de empuje, articulaciones y su fatiga) se calculan a ${fmt(Tn, 3)} °C pero <b>no entran</b> al estado, al FU térmico ni al veredicto. Resumen informativo: ${b.fuera_resumen.fail} no cumplirían, ${b.fuera_resumen.warn} en monitoreo. Alcance 2 las reactiva.</div>
      <table><tr><th>Grupo</th><th>Verificación (mayores FU, hasta 40)</th><th class="n">FU 20 °C</th><th class="n">FU T</th><th>Estado informativo</th></tr>${faRows}</table>
      <div class="note">Aceite atrapado (Δp en bar, cota alta K = 1,9 GPa): ${r.aceite.map((o) => `${fmt(o.T, 3)} °C → ${fmt(o.cilindro.alto, 3)}`).join(" · ")}. Supuestos de confianza C fuera de alcance: ${(r.supuestos_fuera_alcance || []).map(esc).join("; ") || "—"}.</div></div>`;
    return warns + `
    <div class="card" style="margin-top:12px"><h3>Por alternativa a ${fmt(Tn, 3)} °C (20 °C → ${fmt(Tn, 3)} °C) · gradiente ${fmt(r.gradiente_scn, 3)} K</h3><div class="scroll"><table>
      <tr><th>Alternativa</th><th class="n">FS giro</th><th class="n">FU estructura máx.</th><th>Elemento gobernante (estructura)</th><th class="n">FU térmico máx.</th><th>Gobernante térmico (${r.alcance === 2 ? "juntas, gradiente, aceite" : "juntas, gradiente"})</th><th class="n">Masa (kg)</th><th>Estado</th><th class="n">Empeoran de estado</th></tr>${t1}</table></div>
      <div class="note">FU estructura: verificaciones estándar con las capacidades a T (Fy, p_adm, C_t…) sobre la geometría de 20 °C; FU térmico: juntas de dilatación, gradiente sumado a la plancha${r.alcance === 2 ? ", aceite" : ""}. Factores a ${fmt(Tn, 3)} °C: ${fk}. Los FS del giro no cambian con T salvo que se defina k_mu_T (μ de la grasa a T, dato de entrada). ● alternativa activa.</div></div>
    <div class="card" style="margin-top:12px"><h3>Sensibilidad a la temperatura</h3><div class="scroll">
      <table><tr><th>FU estructura máx.</th>${hdr}</tr>${t2}</table><table style="margin-top:8px"><tr><th>FU térmico máx. (juntas + gradiente)</th>${hdr}</tr>${t3}</table>
      <table style="margin-top:8px"><tr><th>FS del giro (μ constante)</th>${hdr}</tr>${t4}</table><table style="margin-top:8px"><tr><th>N.º de verificaciones que no cumplen${r.alcance === 2 ? " (incluye aceite, sellos, viscosidad)" : " (sistema de placas y disco)"}</th>${hdr}</tr>${t5}</table></div></div>
    <div class="card" style="margin-top:12px"><h3>${esc(a.nombre)} · verificaciones que más empeoran a ${fmt(Tn, 3)} °C (aumento de FU, 10 mayores)</h3><div class="scroll"><table><tr><th>Verificación</th><th class="n">FU 20 °C</th><th class="n">FU T</th><th class="n">Variación</th><th>Estado</th><th>Confianza</th></tr>${lst(b.sensibles)}</table></div>
      <div class="note">Solo estructura y giro (sin aceite, sellos ni viscosidad):</div><div class="scroll"><table><tr><th>Verificación</th><th class="n">FU 20 °C</th><th class="n">FU T</th><th class="n">Variación</th><th>Estado</th><th>Confianza</th></tr>${lst(b.sensibles_est)}</table></div></div>
    <div class="card" style="margin-top:12px"><h3>Verificaciones que cambian de estado (cumple → no cumple)</h3><div class="scroll"><table><tr><th>Verificación</th><th>Estado</th><th class="n">FU</th><th>Confianza</th></tr>${chg}</table></div></div>
    <div class="grid" style="margin-top:12px">
      <div class="card scroll"><h3>Juntas de dilatación: requerida frente a disponible</h3><table><tr><th>Pieza</th><th class="n">Requerida</th><th class="n">Disponible en frío</th><th class="n">FU</th><th>Estado</th></tr>${jun}</table>
        <div class="note">Si la junta cierra el sector se comprime y pandea: ampliar la junta en frío (j_sec) al valor requerido. La junta en frío es la del diseño a 20 °C (ΔT de diseño ${fmt(P.dT, 3)} K).</div></div>
      <div class="card scroll"><h3>Holguras de pivote y engrane</h3><table><tr><th>Verificación</th><th class="n">Valor</th><th class="n">Límite</th><th>Estado</th></tr>${hs}</table>
        <div class="note">El buje de bronce (α 18) crece más que el cubo y el pasador de acero (α 12,4): libre, la holgura aumenta; retenido por el cubo, se reduce unas centésimas de mm. Con la mesa caliente y la base a la sombra el círculo de pasadores crece α·ΔT·R_pin respecto de la uña; con ambos calientes el efecto relativo es despreciable.</div></div></div>
    ${r.alcance === 2 ? oilCards : outScope}
    <div class="card" style="margin-top:12px"><h3>Sensibilidad al μ de la grasa (FS del giro a ${fmt(Tn, 3)} °C) · ${esc(a.nombre)}</h3><div class="scroll"><table><tr><th>μ × </th>${sm.mu.map((m) => `<th class="n">${fmt(m.f)}</th>`).join("")}</tr><tr><td>FS del giro (FS_mín ${fu2(P.FS_min)})</td>${mu}</tr></table></div>
      <div class="note">μ máximo (múltiplo del de diseño) con FS ≥ FS_mín: <b>× ${fu2(sm.mu_crit)}</b>. Con Fy del acero × 0,92 (ASME II-D, confianza C): FU estructura máx. ${fu2(sm.kFy092.fuEst)} (${sm.kFy092.fuEst <= 1 ? "≤ 1,0" : "&gt; 1,0"}); FU térmico máx. ${fu2(sm.kFy092.fuTerm)}.${sm.bz090 ? ` Con bronce × 0,90: FU máx. ${fu2(sm.bz090.fuEst)}.` : ""}</div>${wd}</div>${uh}
    <div class="note">Fuente de los datos y niveles de confianza (A tabla contrastada, B ficha o dos fuentes, C supuesto): docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)». Supuestos de confianza C: ${r.supuestos_C.map(esc).join("; ")}.</div>`;
  }

  /* ---------- Tapones de grafito (alternativa C): cantidad real colocable frente a la ideal, barridos y patrón ---------- */
  let TP = null, TPkey = "", tpSel = "C1";
  const f4 = (v) => (v == null || !isFinite(v) ? "—" : v.toLocaleString("es-CL", { minimumFractionDigits: 3, maximumFractionDigits: 3 }));
  const EST_TP = { "cumple": ["ok", "Cumple"], "cumple sin lubricación": ["warn", "Cumple sin lubricación (f_g < mínimo)"], "no cumple": ["fail", "No cumple"], "inalcanzable": ["fail", "Inalcanzable"] };
  function renderTapones() {
    const el = document.querySelector('section[data-t="tapones"]');
    if (cur !== "tapones") return;
    if (!A) { el.innerHTML = msgs(); return; }
    const key = JSON.stringify(P);
    if (key !== TPkey) {
      el.innerHTML = `<div class="busy">Calculando los tapones de C1, C2 y C3 (ideal frente a real, barridos de f_g y de Ø–paso)…</div>`;
      setTimeout(() => { try { TP = TT.tapones(P); TPkey = key; } catch (err) { TP = null; el.innerHTML = `<div class="msg error">Error de cálculo de tapones: ${esc(err.message)}</div>`; return; } renderTapones(); }, 30);
      return;
    }
    const r = TP, a = r.alternativas.find((x) => x.id === tpSel) || r.alternativas[0], ci = a.comparacion, g = a.geom, c = a.conclusion, pm = r.parametros;
    const est = (e) => { const t = EST_TP[e] || ["info", e]; return `<span class="st st-${t[0]}">${esc(t[1])}</span>`; };
    const sel = `<div class="btns">${r.alternativas.map((x) => `<button data-tp="${x.id}"${x.id === a.id ? ' class="pri"' : ""}>${esc(x.nombre)}</button>`).join("")}<button id="bTpJson">Descargar JSON</button><button id="bTpCsv">Descargar CSV (Ø–paso)</button></div>`;
    const altNote = P.opt_bz ? "" : `<div class="note">La alternativa activa no es la C: esta pestaña evalúa C1, C2 y C3 con los parámetros actuales (bz_plug_d, bz_plug_p, bz_edge…) sin cambiar la alternativa seleccionada.</div>`;
    // resumen por alternativa (ideal frente a real)
    const R0 = r.alternativas.map((x) => { const i = x.comparacion.ideal, q = x.comparacion.real, d = x.comparacion.delta_pct; return `<tr${x.id === a.id ? ' class="grp"' : ""}><td>${esc(x.id)}</td><td class="n">${fmt(i.N, 4)} → ${fmt(q.N, 4)}</td><td class="n">${f4(i.fg)} → ${f4(q.fg)}</td><td class="n">${fmt(i.masa_bz, 4)} → ${fmt(q.masa_bz, 4)} (${pct(d.masa_bz)})</td><td class="n">${fu2(i.qNet)} → ${fu2(q.qNet)} (${pct(d.qNet)})</td><td class="n">${fmt(i.tbz, 3)} → ${fmt(q.tbz, 3)}</td><td class="n">${fmt(q.FS, 3)}</td><td>${q.cumple_lub ? '<span class="st st-ok">Cumple</span>' : `<span class="st st-warn">f_g ${f4(q.fg)} &lt; ${fu2(pm.bz_fg_min)}</span>`}</td></tr>`; }).join("");
    // (a) comparación detallada de la alternativa elegida
    const rowsCmp = [["N (tapones)", "N", 4], ["f_g = cobertura de grafito", "fg", 0], ["Masa del bronce (kg)", "masa_bz", 5], ["Masa total (kg)", "masa_total", 5], ["q_neto (MPa)", "qNet", 3], ["FU de q_neto (frente a p_bz)", "fuQ", 3], ["Espesor requerido (mm)", "tbzReq", 3], ["Espesor adoptado (mm)", "tbz", 3], ["PV (MPa·m/s)", "PV", 3], ["FU del PV", "fuPV", 3], ["Desgaste a la vida de diseño (mm)", "desgaste", 3], ["FU del desgaste", "fuDesgaste", 3], ["FS de giro (μ de diseño, dato)", "FS", 4], ["μ de diseño (dato: no cambia)", "mu", 3]]
      .map(([n, k, sg]) => `<tr><td>${esc(n)}</td><td class="n">${sg === 0 ? f4(ci.ideal[k]) : fmt(ci.ideal[k], sg)}</td><td class="n">${sg === 0 ? f4(ci.real[k]) : fmt(ci.real[k], sg)}</td><td class="n">${pct(ci.delta_pct[k])}</td></tr>`).join("");
    const pdr = g.perdidas, perd = [["Malla escalonada dentro de la corona (R_i + borde … R_o − borde)", g.N_malla], ["− franja de borde del bronce (bordes de sector o pastilla)", -pdr.borde], ["− muesca del tope ((b_tope + 2) × " + fmt(g.L_muesca, 3) + " mm)", -pdr.muesca], ["− tornillos de posición (" + g.n_tornillos_sector + " por sector, cabeza Ø" + g.d_cabeza + ")", -pdr.tornillos], ["− ranuras circunferenciales", -pdr.ranCirc], ["− ranuras radiales", -pdr.ranRad], ["= N_real", g.N_real]]
      .map(([n, v]) => `<tr${/N_real/.test(n) ? ' class="grp"' : ""}><td>${esc(n)}</td><td class="n">${v}</td></tr>`).join("");
    // (b) barrido de f_g
    const bf = a.barrido_fg.map((x) => `<tr><td class="n">${fu2(x.fg_obj)}</td><td class="n">${f4(x.fg)}</td><td class="n">Ø${x.d} · ${fmt(x.p, 3)}</td><td class="n">${fmt(x.eta, 3)}</td><td class="n">${x.N}</td><td class="n">${fmt(x.tbzReq, 3)} → ${x.tbz}</td><td class="n">${fmt(x.masa_bz, 4)}</td><td class="n">${fu2(x.qNet)}</td><td>${est(x.estado)}</td></tr>`).join("");
    // (c) barrido (d, p): matriz f_g,real con el estado y tabla de los mejores
    const ds = r.barridos.d, ps = r.barridos.p, cellOf = (d, p) => a.barrido_dp.find((x) => x.d === d && x.p === p);
    const mx = ps.map((p) => `<tr><td class="n"><b>${p}</b></td>${ds.map((d) => { const x = cellOf(d, p); if (!x) return `<td class="n ref">—</td>`; const k = (EST_TP[x.estado] || ["info"])[0]; return `<td class="n c-${k}" title="Ø${d} · paso ${p}: N ${x.N}, η ${fmt(x.eta, 3)}, bronce ${fmt(x.masa_bz, 4)} kg, q_neto ${fu2(x.qNet)} MPa, espesor ${x.tbz} mm. ${esc(x.motivos.join("; ") || x.estado)}">${f4(x.fg)}</td>`; }).join("")}</tr>`).join("");
    const top = a.barrido_dp.filter((x) => x.eta >= pm.bz_eta_min - 1e-12 && x.fab).sort((x, y) => y.fg - x.fg).slice(0, 10)
      .map((x) => `<tr><td class="n">Ø${x.d} · ${x.p}</td><td class="n">${fmt(x.eta, 3)}</td><td class="n">${x.N}</td><td class="n">${f4(x.fg)}</td><td class="n">${fmt(x.tbzReq, 3)} → ${x.tbz}</td><td class="n">${fmt(x.masa_bz, 4)}</td><td class="n">${fu2(x.qNet)}</td><td>${est(x.estado)}</td></tr>`).join("");
    // (d) sensibilidad
    const sb = a.sens_borde.map((x) => `<tr${x.bz_edge === pm.bz_edge ? ' class="grp"' : ""}><td class="n">${x.bz_edge}</td><td class="n">${x.N}</td><td class="n">${f4(x.fg)}</td><td class="n">${fmt(x.masa_bz, 4)}</td><td class="n">${fu2(x.qNet)}</td><td>${x.cumple_lub ? est("cumple") : est("cumple sin lubricación")}</td></tr>`).join("");
    const st = a.sens_tornillos.map((x) => `<tr${x.d_tor === pm.d_tor && x.n_tor === pm.bz_n_tor ? ' class="grp"' : ""}><td class="n">M${x.d_tor}</td><td class="n">${x.n_tor}</td><td class="n">${x.N}</td><td class="n">${f4(x.fg)}</td><td class="n">${fmt(x.masa_bz, 4)}</td><td>${x.n_fallan ? est("no cumple") : (x.cumple_lub ? est("cumple") : est("cumple sin lubricación"))}</td></tr>`).join("");
    // (e) conclusión
    const rec = c.patron_recomendado, best = c.mejor_alcanzable;
    el.innerHTML = `<div class="card"><h3>Tapones de grafito · opción C (cantidad real colocable frente a la ideal)</h3>${altNote}
      <div class="note">Patrón actual: Ø${pm.bz_plug_d} · paso ${pm.bz_plug_p} (escalonado) · franja de borde ${pm.bz_edge} mm · el cálculo usa ${pm.bz_fg_modo > 0.5 ? "<b>f_g real</b> (bz_fg_modo = 1)" : "<b>f_g ideal</b> (bz_fg_modo = 0)"} · f_g mínimo ${fu2(pm.bz_fg_min)} (supuesto C) · η mínimo ${fu2(pm.bz_eta_min)}.</div>
      <div class="scroll"><table><tr><th>Alternativa</th><th class="n">N ideal → real</th><th class="n">f_g ideal → real</th><th class="n">Masa del bronce (kg)</th><th class="n">q_neto (MPa)</th><th class="n">Espesor (mm)</th><th class="n">FS giro</th><th>Lubricación</th></tr>${R0}</table></div>
      ${sel}</div>
    <div class="card" style="margin-top:12px"><h3>${esc(a.nombre)} · conclusión automática</h3>
      <div class="msg ${c.cumple_criterio ? "ok" : "warn"}">${c.cumple_criterio ? `Patrón recomendado: <b>Ø${rec.d} · paso ${rec.p}</b> (η ${fmt(rec.eta, 3)}, ${rec.N} tapones, f_g ${f4(rec.fg)}, bronce ${fmt(rec.masa_bz, 4)} kg).` : `Ningún patrón del barrido cumple f_g,real ≥ ${fu2(c.fg_min_criterio)} con η ≥ ${fu2(pm.bz_eta_min)} y fabricable; el máximo alcanzable es <b>${f4(c.fg_max_alcanzable)}</b>${best ? ` (Ø${best.d} · paso ${best.p}, ${best.N} tapones, η ${fmt(best.eta, 3)})` : ""}. El criterio queda como aviso (supuesto C) y se conserva el patrón actual.`}</div>
      <ul>${c.texto.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>
      ${c.costo_masa ? `<div class="note">Costo del patrón recomendado frente al actual: ${fmt(c.costo_masa.delta_kg, 3)} kg de bronce (${pct(c.costo_masa.delta_pct)}), espesor ${c.costo_masa.delta_espesor >= 0 ? "+" : ""}${c.costo_masa.delta_espesor} mm, ${c.costo_masa.delta_agujeros >= 0 ? "+" : ""}${c.costo_masa.delta_agujeros} agujeros.</div>` : ""}
      <div class="note">f_g mínimo para cumplir (lubricación): <b>${fu2(a.limites_fg.fg_min_lubricacion)}</b>; máximo admisible por q_neto, PV y desgaste: <b>${fu2(a.limites_fg.fg_max)}</b> (q_neto ${fu2(a.limites_fg.q_neto)}, PV ${fu2(a.limites_fg.PV)}, desgaste ${fu2(a.limites_fg.desgaste)}). Más grafito baja la masa del bronce (grafito 1,8 frente a 7,45 g/cm³).</div></div>
    <div class="grid" style="margin-top:12px">
      <div class="card scroll"><h3>(a) Ideal frente a real · ${esc(a.id)}</h3><table><tr><th></th><th class="n">Ideal (π d²/(2√3 p²))</th><th class="n">Real (tapones que caben)</th><th class="n">Variación</th></tr>${rowsCmp}</table>
        <div class="note">El ideal reparte la malla sobre toda la corona; el real descuenta la franja de borde, la muesca del tope, los tornillos y las ranuras. η depende solo de Ø y paso: no cambia. El μ es dato de entrada y no se modifica.</div></div>
      <div class="card scroll"><h3>Cuenta de tapones · ${esc(a.id)}</h3><table><tr><th>Concepto</th><th class="n">Tapones</th></tr>${perd}</table>
        <div class="note">Por ${a.id === "C3" ? "pastilla" : "sector"}: ${g.por_sector_min} a ${g.por_sector_max} tapones; junta ${fmt(g.junta, 2)} mm${a.id === "C3" ? `, cobertura ${fu2(g.cov)}` : ""}; área de contacto ${fmt(g.area_contacto / 1e6, 4)} m². Coincide con el patrón S09 del modelo 3D (cad/modelo3d_tt300c.py).</div></div></div>
    <div class="card scroll" style="margin-top:12px"><h3>(b) Barrido de f_g,real contra espesor, masa, q_neto, η y estado (Ø ${pm.bz_plug_d}, paso variable) · ${esc(a.id)}</h3><table><tr><th class="n">f_g objetivo</th><th class="n">f_g alcanzado</th><th class="n">Patrón</th><th class="n">η</th><th class="n">N</th><th class="n">Espesor requerido → adoptado (mm)</th><th class="n">Masa bronce (kg)</th><th class="n">q_neto (MPa)</th><th>Estado</th></tr>${bf}</table>
      <div class="note">Se elige el mayor paso cuyo f_g,real alcanza el objetivo. El espesor lo fija el tope (${fmt(a.comparacion.real.tbz, 3)} mm) mientras el requerido por flexión sea menor.</div></div>
    <div class="card scroll" style="margin-top:12px"><h3>(c) Barrido de Ø (columnas) y paso (filas): f_g,real y estado · ${esc(a.id)}</h3>
      <table><tr><th class="n">Paso \ Ø</th>${ds.map((d) => `<th class="n">${d}</th>`).join("")}</tr>${mx}</table>
      <div class="note">Verde: cumple; amarillo: cumple sin alcanzar el f_g mínimo; rojo: no cumple (η &lt; ${fu2(pm.bz_eta_min)}, no fabricable u otra verificación). Pase el cursor por una celda para ver N, η, masa y q_neto.</div>
      <table style="margin-top:8px"><tr><th class="n">Patrón</th><th class="n">η</th><th class="n">N</th><th class="n">f_g real</th><th class="n">Espesor req. → adoptado</th><th class="n">Masa bronce (kg)</th><th class="n">q_neto</th><th>Estado</th></tr>${top}</table>
      <div class="note">Los 10 patrones con mayor f_g,real que cumplen η ≥ ${fu2(pm.bz_eta_min)} y son fabricables (ligamento ≥ ${r.barridos.ligamento_min_fab} mm, profundidad ≤ ${r.barridos.prof_max_d}·Ø; sin torno vertical).</div></div>
    <div class="grid" style="margin-top:12px">
      <div class="card scroll"><h3>(d) Sensibilidad a la franja de borde bz_edge · ${esc(a.id)}</h3><table><tr><th class="n">bz_edge (mm)</th><th class="n">N</th><th class="n">f_g real</th><th class="n">Masa bronce (kg)</th><th class="n">q_neto (MPa)</th><th>Lubricación</th></tr>${sb}</table></div>
      <div class="card scroll"><h3>Sensibilidad al número y tamaño de los tornillos · ${esc(a.id)}</h3><table><tr><th class="n">Tornillo</th><th class="n">N.º por sector</th><th class="n">N</th><th class="n">f_g real</th><th class="n">Masa bronce (kg)</th><th>Estado</th></tr>${st}</table>
        <div class="note">Cada tornillo avellanado excluye un círculo de radio (cabeza/2 + borde + Ø/2) centrado en él; 4 por sector es una hipótesis de sensibilidad.</div></div></div>
    <div class="card" style="margin-top:12px"><h3>Notas de confianza y supuestos</h3><ul>${r.notas.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>
      <div class="note"><b>Supuestos:</b> ${r.supuestos.map(esc).join("; ")}.</div></div>`;
    el.querySelectorAll("button[data-tp]").forEach((b) => { b.onclick = () => { tpSel = b.dataset.tp; renderTapones(); }; });
    $("#bTpJson").onclick = () => download(`TT300C_tapones_${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(TP, null, 1), "application/json");
    $("#bTpCsv").onclick = () => {
      const h = ["alternativa", "d", "p", "eta", "N", "fg_real", "tbz_req", "tbz", "masa_bz", "masa_total", "qNet", "estado"], rows = [h.join(";")];
      TP.alternativas.forEach((x) => x.barrido_dp.forEach((y) => rows.push([x.id, y.d, y.p, y.eta, y.N, y.fg, y.tbzReq, y.tbz, y.masa_bz, y.masa_total, y.qNet, y.estado].join(";"))));
      download("TT300C_tapones_barrido_d_p.csv", rows.join("\n"), "text/csv");
    };
  }
  function download(name, data, type) {
    const blob = new Blob([data], { type });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 800);
  }
  function renderPkg() {
    const on = $("#pkgChk").checked, el = $("#pkgPanel");
    el.hidden = !on; $("#pkgRow").classList.toggle("chg", on);
    if (!on) return;
    if (typeof PLANOS === "undefined") { el.innerHTML = `<div class="msg error">Módulo de planos no disponible.</div>`; return; }
    if (!A) { el.innerHTML = `<div class="msg error">Corrija los datos marcados para exportar.</div>`; return; }
    const R = A.R, v = A.verdict, ok = v.gira && v.estructura;
    el.innerHTML = `<div class="kv"><span>Interfaz de giro</span><span>${esc(PLANOS.ifaceName(P, R.ifc))}</span>
        <span>Fijación</span><span>${esc(PLANOS.fixText(P, R.ifc))}</span>
        <span>Cubierta</span><span>${esc(PLANOS.woodText(P))}</span>
        <span>Masa total</span><span>${fmt(R.m.total, 4)} kg</span></div>
      ${ok ? "" : `<div class="msg warn">El diseño actual no cumple (gira o estructura): el generador completo se negará a emitir planos hasta corregirlo.</div>`}
      <ul>${SHEET_IDS.map((id) => `<li>TT300C-${esc(id)}-${PLANOS.REV}</li>`).join("")}<li>Lista de materiales (CSV) · JSON de diseño · láminas SVG</li></ul>
      <div class="btns"><button class="pri" id="bPkgZip">Descargar paquete (.zip)</button><button id="bPkgPrint" title="Abre las láminas en una página de impresión; use Imprimir → Guardar como PDF">Láminas imprimibles (PDF)</button></div>
      <div class="btns"><select id="pkgSel" aria-label="Lámina DXF">${SHEET_IDS.map((id) => `<option value="${esc(id)}"${id === pkgSelId ? " selected" : ""}>${esc(id)}</option>`).join("")}</select><button id="bPkgDxf">DXF</button><button id="bPkgCsv">Lista CSV</button><button id="bPkgJson">JSON de diseño</button></div>
      <div class="adv">${esc(PLANOS.ADVERTENCIA)}</div>
      <div class="note">${PLANOS.NOTAS.map(esc).join(" · ")}. Lo que el núcleo no define se rotula «A DEFINIR». El JSON de diseño alimenta el generador completo (PDF, DXF, STEP y Excel).</div>`;
    const run = (fn) => () => { try { fn(PLANOS.buildPackage(P, A)); } catch (err) { alert("No se pudo generar el paquete: " + err.message); } };
    const find = (pk, kind, id) => pk.files.find((f) => f.kind === kind && (!id || f.sheet === id));
    const stamp = new Date().toISOString().slice(0, 10);
    $("#bPkgZip").onclick = run((pk) => download(`TT300C_paquete_dibujo_Rev${PLANOS.REV}_${stamp}.zip`, pk.zip(), "application/zip"));
    $("#bPkgPrint").onclick = run((pk) => {
      const f = find(pk, "html"), url = URL.createObjectURL(new Blob([f.data], { type: "text/html" })), w = window.open(url, "_blank");
      if (!w) download("TT300C_laminas_impresion.html", f.data, "text/html");
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    });
    $("#pkgSel").onchange = () => { pkgSelId = $("#pkgSel").value; };
    $("#bPkgDxf").onclick = run((pk) => { const f = find(pk, "dxf", $("#pkgSel").value); download(f.name.split("/").pop(), f.data, f.mime); });
    $("#bPkgCsv").onclick = run((pk) => { const f = find(pk, "csv"); download("TT300C_lista_materiales.csv", f.data, "text/csv"); });
    $("#bPkgJson").onclick = run((pk) => { const f = find(pk, "json"); download("TT300-C_design.json", f.data, "application/json"); });
  }
  $("#pkgChk").checked = store.get(LSK) === "1";
  $("#pkgChk").addEventListener("change", () => { store.set(LSK, $("#pkgChk").checked ? "1" : "0"); renderPkg(); });

  /* ---------- Planos: juegos pre-generados (Modo 1) y generador local (Modo 2) ---------- */
  const PIDX = (typeof PLANOS_IDX !== "undefined") ? PLANOS_IDX : { juegos: [], grupos: [["generales", "Generales"], ["fabricacion", "Fabricación"], ["armado", "Armado"]] };
  const GEN_URL = (location.protocol.startsWith("http") && (location.hostname === "127.0.0.1" || location.hostname === "localhost") && location.port === "8765") ? "" : "http://127.0.0.1:8765";
  const PLAB = {}; TT.PARAM_GROUPS.forEach((g) => g.p.forEach((q) => { PLAB[q[0]] = q[1] + (q[2] ? ` [${q[2]}]` : ""); }));
  const GEN = { srv: null, job: null, poll: null, sentP: null, err: "", pinging: false };     // srv: null = comprobando, false = inactivo, objeto = respuesta de /api/ping
  const href = (base, f) => (base ? base + "/" : "") + String(f).split("/").map(encodeURIComponent).join("/");
  const vEq = (a, b) => (typeof a === "number" && typeof b === "number") ? Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b)) : a === b;
  const vTxt = (v) => v === undefined ? "(no existe)" : typeof v === "number" ? v.toLocaleString("es-CL", { maximumFractionDigits: 9 }) : String(v);
  function plDiff(Pa, Pb) {
    const ks = [...new Set([...Object.keys(Pa), ...Object.keys(Pb)])];
    return ks.filter((k) => !vEq(Pa[k], Pb[k])).map((k) => ({ k, a: Pa[k], b: Pb[k] }));
  }
  function plMatch() {
    let best = null;
    PIDX.juegos.forEach((j) => { const d = plDiff(P, j.P); if (!best || d.length < best.d.length) best = { j, d }; });
    return best;
  }
  const jName = (j) => (j.id === "0" ? "Base" : j.id) + " · " + j.interfaz + (j.madera ? " · cubierta de madera" : "");
  /* juego desde indice_planos.json (resultado del generador local) → misma forma compacta del índice incrustado */
  function jFromIndice(ix) {
    const gids = PIDX.grupos.map((g) => g[0]), pdf = {};
    gids.forEach((g) => { pdf[g] = ix.grupos[g] ? ix.grupos[g].pdf : null; });
    const ar = {}; Object.keys(ix.archivos || {}).forEach((k) => { if (ix.archivos[k]) ar[k] = ix.archivos[k]; });
    return { id: "local", carpeta: ix.carpeta, interfaz: ix.interfaz, madera: ix.madera, pdf, archivos: ar,
      laminas: ix.laminas.map((l) => [l.codigo, l.titulo, gids.indexOf(l.grupo), l.pdf ? 1 : 0, l.dxf ? 1 : 0]) };
  }
  function plCards(j) {
    const b = j.carpeta, short = (c) => c.replace(/^TT300C-/, "");
    const cards = PIDX.grupos.map(([gid, gt], gi) => {
      const ls = j.laminas.filter((l) => l[2] === gi);
      const rows = ls.map((l) => `<tr><td>${esc(short(l[0]))}</td><td>${esc(l[1])}</td><td>${l[3] ? `<a href="${esc(href(b, "planos/" + l[0] + ".pdf"))}" target="_blank" rel="noopener">PDF</a>` : "—"}${l[4] ? ` · <a href="${esc(href(b, "planos/" + l[0] + ".dxf"))}" download>DXF</a>` : ""}</td></tr>`).join("");
      return `<div class="card pl-grp" data-g="${gid}"><h3>${esc(gt)}</h3><div class="big">${ls.length} <span class="ref">láminas</span></div>
        <div class="btns">${j.pdf[gid] ? `<a class="btn pri" data-pdf="${gid}" href="${esc(href(b, j.pdf[gid]))}" target="_blank" rel="noopener">PDF ${esc(gt)}</a>` : `<span class="note">PDF del grupo no disponible: ejecute tools/indice_planos.py</span>`}</div>
        <details><summary>Lista de láminas (${ls.length})</summary><div class="scroll"><table><tr><th>Plano</th><th>Título</th><th>Archivo</th></tr>${rows}</table></div></details></div>`;
    }).join("");
    const a = j.archivos, lk = (k, t, dl) => a[k] ? `<a data-f="${k}" href="${esc(href(b, a[k]))}"${dl ? " download" : ' target="_blank" rel="noopener"'}>${t}</a>` : "";
    const dxf = a.dxf_zip ? lk("dxf_zip", "DXF de todas las láminas (.zip)", 1) : `<span class="ref">DXF: no incluido en este juego (solo en el juego Base; el generador local también lo entrega)</span>`;
    return `<div class="grid">${cards}</div>
      <div class="pl-files"><b>Otros archivos:</b>${lk("combinado", "PDF combinado (todas las láminas)")}${lk("despiece_xlsx", "Despiece XLSX", 1)}${lk("step", "Modelo 3D STEP", 1)}${dxf}${lk("informe", "Informe del paquete")}</div>
      <div class="note">Carpeta: <span class="form">${esc(b)}/</span></div>`;
  }
  function renderPlanos() {
    const el = $("#plJuego"); if (!el) return;
    if (!PIDX.juegos.length) { el.innerHTML = `<div class="msg warn">Esta copia de la herramienta no trae el índice de planos pre-generados.</div>`; el.dataset.juego = ""; renderGen(); return; }
    const m = plMatch();
    if (m.d.length === 0) {
      el.dataset.juego = m.j.id; el.dataset.estado = "coincide";
      el.innerHTML = `<div class="msg ok"><b>Planos pre-generados coincidentes</b> con los parámetros actuales: juego <b>${esc(jName(m.j))}</b> (${m.j.laminas.length} láminas, Rev. ${esc(PIDX.rev || "C")}).</div>` + plCards(m.j);
    } else {
      el.dataset.juego = ""; el.dataset.estado = "no-coincide"; el.dataset.cercano = m.j.id;
      el.innerHTML = `<div class="msg warn"><b>Los planos pre-generados no corresponden a los parámetros actuales.</b> El juego más cercano es <b>${esc(jName(m.j))}</b>; difiere en ${m.d.length} parámetro${m.d.length > 1 ? "s" : ""}:</div>
        <div class="card scroll"><table id="plDif"><tr><th>Parámetro</th><th>Nombre</th><th class="n">Valor actual</th><th class="n">Valor del juego</th></tr>
        ${m.d.map((x) => `<tr><td class="form">${esc(x.k)}</td><td>${esc(PLAB[x.k] || "")}</td><td class="n">${esc(vTxt(x.a))}</td><td class="n">${esc(vTxt(x.b))}</td></tr>`).join("")}</table></div>
        <div class="note">Use el <b>generador local</b> (abajo) para obtener los planos de estos parámetros, o vuelva a los del juego con «Valores por defecto» y el selector de alternativa.</div>`;
    }
    renderGen();
  }
  /* ---- Modo 2: servidor local tools/servidor_planos.py ---- */
  function genFetch(path, opt, ms) {
    const ac = new AbortController(), t = setTimeout(() => ac.abort(), ms || 2500);
    return fetch(GEN_URL + path, Object.assign({ cache: "no-store", signal: ac.signal }, opt || {})).then((r) => r.json().then((j) => { clearTimeout(t); if (!r.ok) { const e = new Error(j.error || ("HTTP " + r.status)); e.data = j; throw e; } return j; }));
  }
  function genPing() {
    GEN.pinging = true;
    return genFetch("/api/ping").finally(() => { GEN.pinging = false; }).then((j) => { GEN.srv = j; if (j.trabajo && !GEN.job) { GEN.job = j.trabajo; if (j.trabajo.estado === "en_curso") genPoll(); } }).catch(() => { GEN.srv = false; }).then(renderGen);
  }
  function genPoll() {
    clearInterval(GEN.poll);
    GEN.poll = setInterval(() => {
      if (!GEN.job) { clearInterval(GEN.poll); return; }
      genFetch("/api/estado?id=" + encodeURIComponent(GEN.job.id)).then((j) => { GEN.job = j; if (j.estado !== "en_curso") clearInterval(GEN.poll); renderGen(); })
        .catch(() => { GEN.srv = false; clearInterval(GEN.poll); renderGen(); });
    }, 1500);
  }
  function genStart() {
    GEN.err = "";
    let body;
    try { body = PLANOS.designJSON(PLANOS.buildDesign(P, A)); } catch (err) { GEN.err = "No se pudo armar el JSON de diseño: " + err.message; renderGen(); return; }
    GEN.sentP = JSON.stringify(P);
    genFetch("/api/generar", { method: "POST", headers: { "Content-Type": "application/json" }, body }, 15000)
      .then((j) => { GEN.job = j; genPoll(); renderGen(); })
      .catch((err) => { GEN.err = err.message; if (err.data && err.data.trabajo) { GEN.job = err.data.trabajo; genPoll(); } renderGen(); });
  }
  function renderGen() {
    const el = $("#plGen"); if (!el) return;
    const s = GEN.srv, jb = GEN.job;
    let h = `<h3>Generador local (Modo 2) · planos con los parámetros actuales</h3>`;
    if (s === null) h += `<div class="note" id="genEstado" data-srv="comprobando">Comprobando si el generador local está activo…</div>`;
    else if (s === false) h += `<div class="msg warn" id="genEstado" data-srv="inactivo">Generador local no activo. Ejecuta Generar_planos_Tornamesa.bat (requiere instalar una vez con Instalar_generador_planos.bat)</div>
      <div class="btns"><button id="bGenPing">Volver a comprobar</button></div>`;
    else {
      const busy = jb && jb.estado === "en_curso";
      h += `<div class="msg ok" id="genEstado" data-srv="activo">Generador local activo (${esc(s.servidor || "127.0.0.1:8765")}${s.python ? " · Python " + esc(s.python) : ""}).</div>
        ${A && !(A.verdict.gira && A.verdict.estructura) ? `<div class="msg warn">El diseño actual no cumple (gira o estructura): el generador se negará a emitir planos.</div>` : ""}
        <div class="btns"><button class="pri" id="bGen"${busy || !A ? " disabled" : ""}>Generar planos con los parámetros actuales</button></div>
        <div class="note">Tarda varios minutos (modelo 3D, ${PIDX.juegos.length ? "≈ 45–55" : "todas las"} láminas PDF y DXF, despiece y controles de calidad). El resultado queda en la carpeta <span class="form">salidas/</span> del repositorio.</div>`;
    }
    if (GEN.err) h += `<div class="msg error">No se pudo iniciar la generación: ${esc(GEN.err)}</div>`;
    if (jb) {
      const pc = Math.round(100 * (jb.progreso || 0)), changed = GEN.sentP && GEN.sentP !== JSON.stringify(P);
      h += `<div class="kv" style="margin-top:8px"><span>Trabajo</span><span>${esc(jb.id)}</span><span>Alternativa</span><span>${esc(jb.alternativa || "")}</span><span>Estado</span><span id="genJob" data-estado="${esc(jb.estado)}">${esc({ en_curso: "en curso", listo: "terminado", error: "error" }[jb.estado] || jb.estado)}${jb.duracion_s != null ? ` · ${fmt(jb.duracion_s, 3)} s` : ""}</span></div>`;
      if (jb.estado === "en_curso") h += `<div class="prog"><i style="width:${pc}%"></i></div><div class="busy">${esc(jb.fase || "")} · ${pc} % (estimado)</div>`;
      if (jb.estado === "error") h += `<div class="msg error"><b>El generador terminó con error${jb.codigo != null ? ` (código ${esc(jb.codigo)})` : ""}:</b><pre>${esc(jb.mensaje || "")}</pre></div>`;
      if (changed && jb.estado !== "en_curso") h += `<div class="msg warn">Los parámetros cambiaron después de generar este juego: no corresponde a los parámetros actuales.</div>`;
      if (jb.indice) h += (jb.estado === "error" ? `<div class="msg warn">Se emitieron archivos, pero no pasaron todos los controles: revíselos antes de usarlos.</div>` : `<div class="msg ok">Planos generados en <span class="form">${esc(jb.indice.carpeta)}/</span>.</div>`) + plCards(jFromIndice(jb.indice));
      if (jb.log && jb.log.length) h += `<details${jb.estado === "en_curso" ? " open" : ""}><summary>Registro del generador (${jb.log.length} líneas)</summary><pre class="log" id="genLog">${esc(jb.log.join("\n"))}</pre></details>`;
    }
    const lg = $("#genLog"), atEnd = !lg || lg.scrollTop + lg.clientHeight >= lg.scrollHeight - 4;
    el.innerHTML = h;
    const lg2 = $("#genLog"); if (lg2 && atEnd) lg2.scrollTop = lg2.scrollHeight;
    const bp = $("#bGenPing"); if (bp) bp.onclick = () => { GEN.srv = null; renderGen(); genPing(); };
    const bg = $("#bGen"); if (bg) bg.onclick = genStart;
  }

  function renderAll() {
    renderBadges(); renderResumen(); renderModelo(); renderGiro(); renderVerif(); renderFEA(); renderMasa(); renderAgentes(); renderOpt(); renderPkg(); renderPlanos(); renderTemp(); renderTapones();
  }
  buildForm(); recalc();
})();
