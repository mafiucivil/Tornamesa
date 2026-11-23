/* TT300-BX · Interfaz de Tornamesa_BX (copia adaptada de packages/web/ui.js; ese archivo no cambia).
   Evalúa SOLO la tornamesa con disco inoxidable atornillado + pastillas de UHMW (packages/core/tt300bx.js, agentes agentes_bx.js).
   Rendimiento: el dimensionamiento BX y todo lo caro (análisis, escenarios, mercado, capacidad por cilindros, térmica y el JSON de diseño)
   corre en Web Workers (packages/web_bx/worker_bx.js) y nunca bloquea la página; los valores por defecto vienen precalculados al compilar
   (tools/build_tt300bx.py) con el mismo código del worker. Se mantienen: cálculo diferido de los bloques hasta que son visibles, render de
   badges + pestaña activa, debounce de 600 ms con cancelación por generación (RGEN) y la memoria LRU del núcleo (en el worker). */
(() => {
  const TT = TTF, AG = AGBX;                                          // fachada: cada P recibe la geometría BX del worker (gancho __bx)
  const LS = "tt300bx-params-v1", LST = "tt300bx-theme";
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { } } };
  const forceBX = (Q) => Object.assign(Q, { opt_uhmw: 1, opt_ss: 0, opt_bz: 0 });   // sin selector: siempre la interfaz BX (opción B del núcleo + gancho)
  const DEF = forceBX(TT.defaults());
  let P = Object.assign({}, DEF);
  try { const s = JSON.parse(store.get(LS) || "null"); if (s) Object.keys(DEF).forEach((k) => { if (k in s) P[k] = s[k]; }); } catch (e) { }
  forceBX(P);
  let A = null, X = null, AU = null, VAL = [], calc = false, calcErr = "";
  const $ = (s) => document.querySelector(s);
  const D2R = Math.PI / 180;
  const REF = { KIET: 2158, TT300B: 5354 };
  /* ---------- workers: «main» (análisis y JSON de diseño) y «lazy» (bloques diferidos). Una petición de una generación vieja se cancela
     terminando el worker (se vuelve a crear al pedir). Sin Worker (navegador antiguo) se calcula en el hilo principal con setTimeout. ---------- */
  let WURL = null;
  try { WURL = URL.createObjectURL(new Blob([document.getElementById("libs").textContent], { type: "text/javascript" })); } catch (e) { WURL = null; }
  function mkW(name) {
    const W = { name, w: null, q: new Map(), seq: 0 };
    const failAll = (msg) => { for (const c of W.q.values()) c.rej(new Error(msg)); W.q.clear(); };
    W.spawn = () => {
      try { W.w = new Worker(WURL); } catch (e) { W.w = null; WURL = null; return; }
      W.w.onmessage = (e) => { const c = W.q.get(e.data.id); if (!c) return; W.q.delete(e.data.id); e.data.ok ? c.res(e.data.r) : c.rej(new Error(e.data.err)); };
      W.w.onerror = (e) => { if (e.preventDefault) e.preventDefault(); const w0 = W.w; W.w = null; if (w0) w0.terminate(); failAll("Error en el worker de cálculo: " + (e.message || "desconocido")); };
    };
    W.call = (msg, gen) => new Promise((res, rej) => {
      if (!W.w && WURL) W.spawn();
      if (!W.w) { setTimeout(() => { try { res(BXW.run(JSON.parse(JSON.stringify(msg)))); } catch (err) { rej(err); } }, 0); return; }   // respaldo sin Worker
      const id = ++W.seq; W.q.set(id, { res, rej, gen }); W.w.postMessage(Object.assign({ id }, msg));
    });
    W.kill = () => { if (W.w) { W.w.terminate(); W.w = null; } failAll("cancelado"); };
    W.cancelStale = (gen) => { if (W.w && [...W.q.values()].some((c) => c.gen !== gen)) { W.w.terminate(); W.w = null; failAll("cancelado"); } };
    return W;
  }
  const WK = { main: mkW("main"), lazy: mkW("lazy") };
  /* ---------- cálculo diferido: escenarios (SC), mercado (MK), capacidad por n° de cilindros (CN) y la comparación con drive_mode = 2 (CMP)
     se piden al worker «lazy» la primera vez que un bloque visible los necesita y se guardan hasta el siguiente recalc(). RGEN sube con cada
     edición y con cada recalc() y descarta los llenados de una generación anterior (no pintan resultados viejos). ---------- */
  let RGEN = 0;
  const dirty = new Set();                                            // pestañas por redibujar (render perezoso, ver renderAll)
  const LZ = {}, LZP = {};
  function lzGet(k) {
    if (k in LZ) return Promise.resolve(LZ[k]);
    if (LZP[k]) return LZP[k];
    const g = RGEN, Ps = Object.assign({}, P);
    return (LZP[k] = WK.lazy.call({ op: "lazy", k, P: Ps }, g).then((r) => { if (g === RGEN) { LZ[k] = r; delete LZP[k]; } return r; },
      (err) => { if (g === RGEN) { LZ[k] = null; LZ[k + "_err"] = err.message; delete LZP[k]; } return null; }));
  }
  const lz = (k) => (A && k in LZ ? LZ[k] : null);
  const lzErr = (k) => LZ[k + "_err"] ? `<div class="msg error">Error de cálculo: ${esc(LZ[k + "_err"])}</div>` : "";
  // marcador de un bloque diferido: cuando se vuelve visible (pestaña abierta y bloque en pantalla) se piden sus datos al worker y, al llegar,
  // se reemplaza sin envoltorio (outerHTML) por su contenido; si entretanto llegó otra edición (RGEN cambió), se descarta
  let lzSeq = 0;
  const lzIO = typeof IntersectionObserver === "function" ? new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { lzIO.unobserve(e.target); setTimeout(e.target._lzFill, 0); } }), { rootMargin: "200px" }) : null;
  function lzSlot(html, keys) {
    const id = "lzs" + (++lzSeq), g = RGEN;
    const fill = () => { if (g !== RGEN) return; const el0 = document.getElementById(id); if (el0) el0.textContent = "Calculando en segundo plano…";
      Promise.all((keys || []).map(lzGet)).then(() => { if (g !== RGEN) return; const el = document.getElementById(id); if (el) el.outerHTML = html(); }); };
    setTimeout(() => { const el = document.getElementById(id); if (!el || g !== RGEN) return; if (lzIO) { el._lzFill = fill; lzIO.observe(el); } else fill(); }, 0);
    return `<div class="note" id="${id}" data-lazy="1">Calculando…</div>`;
  }

  /* ---------- formato: 2–3 cifras significativas, coma decimal ---------- */
  function fmt(v, sig) {
    if (v == null || !isFinite(v)) return "—";
    sig = sig || 3;
    const a = Math.abs(v);
    let d = a >= 1000 ? 0 : a === 0 ? 0 : Math.max(0, Math.min(3, sig - 1 - Math.floor(Math.log10(a))));
    return v.toLocaleString("es-CL", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  const fu3 = (v) => (v == null || !isFinite(v)) ? "—" : v.toLocaleString("es-CL", { minimumFractionDigits: 3, maximumFractionDigits: 3 });
  const fu2 = fu3;                                                     // FU con 3 decimales en toda la UI
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const ST = { ok: "Cumple", warn: "Monitoreo", fail: "No cumple", info: "Info", pend: "Pendiente" };
  /* ---------- veredicto global del núcleo (verdict.estado_global, pendientes_criticos, limitaciones_uso) ---------- */
  const egCls = (eg) => (eg === "CUMPLE" ? "ok" : "fail");
  function pendCritHTML(v, id) {
    const pc = (v && v.pendientes_criticos) || [];
    if (!pc.length) return "";
    return `<div class="pcrit"${id ? ` id="${id}"` : ""}><b>Pendientes críticos (FU &gt; 1, a la espera de decisión): ${pc.length} · FU máx. ${fu3(v.fuMaxPend)}</b><ul>${pc.map((q) => `<li class="pcrit-i"><span class="st st-fail">FU ${fu3(q.fu)}</span> ${esc(q.grp)} · ${esc(q.nombre)}${q.fuera_alcance_termico ? ' <span class="ref">(fuera del alcance térmico)</span>' : ""}<div class="ref">${esc(q.ref || "")}</div></li>`).join("")}</ul></div>`;
  }
  // limitaciones de uso del núcleo: verdict.limitaciones_uso y las de los pasadores de empuje soldados (designDrive().pasadores_empuje.limitaciones)
  function limUsoLista(v) {
    const L = ((v && v.limitaciones_uso) || []).slice();
    try { const pe = TT.designDrive(P, A.R).pasadores_empuje; ((pe && pe.limitaciones) || []).forEach((t, k) => L.push({ id: "pasador_no_reemplazable" + (k ? "_" + k : ""), texto: "pasador de empuje no reemplazable. " + t, motivo: pe.union ? "Pasadores Ø" + fmt(pe.d) + " a ras del disco, soldados (" + pe.union.tipo + ")." : "", referencia: pe.referencia })); } catch (e) { /* sin designDrive */ }
    return L;
  }
  function limUsoHTML(v, id) {
    const L = limUsoLista(v);
    if (!L.length) return "";
    return `<div class="limuso"${id ? ` id="${id}"` : ""}>${L.map((l) => `<div class="limuso-i" data-id="${esc(l.id || "")}"><b>Limitación de uso${l.informativa ? " (informativa)" : ""}:</b> ${esc(l.texto || l.condicion || "")}<div class="ref">${esc(l.motivo || l.caso || "")}${l.alcance ? ` Alcance: ${esc(l.alcance)}.` : ""}${l.referencia ? ` Ref.: ${esc(l.referencia)}` : ""}</div></div>`).join("")}</div>`;
  }
  // refuerzo cuadrado soldado sobre la base bajo los soportes del cilindro (núcleo: designDrive().pivotado.fabricacion.soporte_E.refuerzo o levaGuiada.fabricacion.refuerzo)
  const areaC = (pl) => { let A2 = 0, cx = 0, cy = 0; pl.forEach((p, i) => { const q = pl[(i + 1) % pl.length], w = p[0] * q[1] - q[0] * p[1]; A2 += w; cx += (p[0] + q[0]) * w; cy += (p[1] + q[1]) * w; }); return Math.abs(A2) > 1e-9 ? [cx / (3 * A2), cy / (3 * A2)] : pl[0]; };   // centroide de área de un polígono
  function insertoOf(R) {
    try {
      const D = TT.designDrive(P, R), f = D.modo === 2 ? ((D.pivotado || {}).fabricacion || {}).soporte_E : ((D.levaGuiada || {}).fabricacion || {});
      const I = f && (f.refuerzo || f.inserto); return I && I.cuadrado && Array.isArray(I.cuadrado.vertices) && I.cuadrado.vertices.length ? I : null;
    } catch (e) { return null; }
  }

  /* ---------- pestañas ---------- */
  const tabs = [...document.querySelectorAll(".tab")];
  let cur = (location.hash || "#resumen").slice(1);
  if (!tabs.some((t) => t.dataset.t === cur)) cur = "resumen";
  $("#tabs").innerHTML = tabs.map((t) => `<button data-t="${t.dataset.t}">${t.dataset.l}</button>`).join("");
  function showTab(t) {
    cur = t;
    if (t === "temp" && typeof renderTemp === "function") setTimeout(renderTemp, 0);
    if (t === "planos") setTimeout(() => { if (!GEN.srv && !GEN.pinging) genPing(); }, 0);   // el generador local se busca solo al abrir la pestaña «Planos»
    tabs.forEach((s) => s.classList.toggle("on", s.dataset.t === t));
    document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.t === t));
    renderTab(t);                // render perezoso: la pestaña se dibuja al abrirla si quedó «sucia»
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

  /* ---------- formulario: sin selector de interfaz; se ocultan los parámetros de las opciones A/C, del acero sobre acero y de los sectores
     y topes que BX no usa. Del grupo «inox» del núcleo quedan los que lee el módulo BX (lista BX_USED, calculada al compilar desde
     packages/core/tt300bx.js y agentes_bx.js) más los μ de la opción B (los usa el núcleo con el gancho BX). ---------- */
  const HIDE_GRP = { interfaz: ["mu_d", "mu_nom", "mu_cont", "mu_dry"] };
  const KEEP_INOX = new Set((typeof BX_USED !== "undefined" ? BX_USED : []).concat(["muB_nom", "muB_d", "muB_cont", "muB_dry"]));
  const OPT_IDS = ["opt_ss", "opt_uhmw", "opt_bz", "bz_conf"];
  const visP = (g, id) => !OPT_IDS.includes(id) && !(HIDE_GRP[g.id] || []).includes(id) && (g.id !== "inox" || KEEP_INOX.has(id));
  const GRP_T = { interfaz: "Interfaz de giro: radio de fricción y factor de seguridad (los μ son los de la opción B, abajo)", inox: "Interfaz BX: inoxidable, UHMW y μ (parámetros del núcleo que usa el módulo BX)" };
  const FORM_GROUPS = () => { const G = TT.PARAM_GROUPS.map((g) => ({ id: g.id, t: GRP_T[g.id] || g.t, p: g.p.filter((q) => visP(g, q[0])) })).filter((g) => g.p.length), i = G.findIndex((g) => g.id === "bx"); if (i > 0) G.unshift(G.splice(i, 1)[0]); return G; };
  function buildForm() {
    $("#form").innerHTML = FORM_GROUPS().map((g, gi) => `<details ${gi < 4 ? "open" : ""} data-g="${esc(g.id)}"><summary>${esc(g.t)}</summary>${g.p.map(([id, lab, u, def, mn, mx, st]) => {
      const txt = typeof def === "string";
      if (st === "chk") return `<div class="prm chk ${P[id] !== DEF[id] ? "chg" : ""}" data-id="${id}"><label for="p_${id}">${id === "opt_wood" ? `<span class="standby" id="woodStandby">Cubierta de madera W: en stand by (no incluida en la entrega Rev${BX.REV_PLANOS})</span>` : ""}${esc(lab)}</label><input id="p_${id}" type="checkbox" ${P[id] > 0.5 ? "checked" : ""}></div>`;
      return `<div class="prm ${P[id] !== DEF[id] ? "chg" : ""}" data-id="${id}"><label for="p_${id}">${esc(lab)}<span class="u">${esc(u)}</span></label>
      <input id="p_${id}" ${txt ? 'class="txt" type="text"' : `type="number" step="${st || "any"}" min="${mn}" max="${mx}"`} value="${esc(P[id])}"></div>`;
    }).join("")}</details>`).join("");
  }
  let tmr = null;
  $("#form").addEventListener("input", (e) => {
    const row = e.target.closest(".prm"); if (!row) return;
    const id = row.dataset.id, txt = typeof DEF[id] === "string";
    if (e.target.type === "checkbox") P[id] = e.target.checked ? 1 : 0;
    else P[id] = txt ? e.target.value : parseFloat(e.target.value);
    row.classList.toggle("chg", P[id] !== DEF[id]);
    RGEN++; clearTimeout(tmr); $("#busy").textContent = "Calculando…";
    tmr = setTimeout(recalc, 600);
  });
  $("#bReset").onclick = () => { P = Object.assign({}, DEF); buildForm(); recalc(); };
  $("#bExp").onclick = () => {
    const blob = new Blob([JSON.stringify(P, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "TT300-BX_parametros.json";
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  };
  $("#bImp").onclick = () => $("#fImp").click();
  $("#fImp").onchange = (e) => {
    const f = e.target.files[0]; if (!f) return;
    f.text().then((t) => { const s = JSON.parse(t); Object.keys(DEF).forEach((k) => { if (k in s) P[k] = s[k]; }); forceBX(P); buildForm(); recalc(); }).catch(() => alert("Archivo JSON no válido"));
  };
  if (typeof SIM !== "undefined") { SIM.init(); $("#bSim").onclick = () => { if (A) SIM.open(P, A); }; }   // simulación del movimiento con la geometría del núcleo

  /* ---------- cálculo: el worker «main» devuelve VAL, A (sin funciones), X y AU; aquí se rearman las funciones de A.R (TT.compute del
     núcleo sobre A.Pc, que ya trae la geometría BX en __bx: no se vuelve a dimensionar). Con los valores por defecto se usa el resultado
     precalculado al compilar (BX_PRE, mismo código del worker) y el worker se calienta en segundo plano. ---------- */
  function rehydrate(R, Rc, seen) {
    seen = seen || new Set(); if (!R || !Rc || typeof Rc !== "object" || seen.has(Rc)) return; seen.add(Rc);
    for (const k of Object.keys(Rc)) { const v = Rc[k]; if (typeof v === "function") R[k] = v; else if (v && typeof v === "object" && R[k] && typeof R[k] === "object") rehydrate(R[k], v, seen); }
  }
  function apply(res) {
    VAL = res.VAL || []; A = res.A; X = res.X || []; AU = res.AU || null; BXWEB.dd = null; BXWEB.R = null; BXWEB.ver++;
    if (A) {
      try { rehydrate(A.R, TTcore.compute(A.Pc)); } catch (err) { VAL.push({ lvl: "warn", msg: "No se pudieron rearmar las funciones del resultado: " + err.message }); }
      BXWEB.bx = A.Pc.__bx; BXWEB.dd = res.DD || null; BXWEB.R = A.R;
    }
  }
  let preUsed = false;
  // resultado precalculado (tools/build_tt300bx.py → <script type="application/json" id="bxpre">): clave y fecha en atributos, JSON aparte
  function preOf() { const el = document.getElementById("bxpre"); return el ? { key: el.dataset.key ? JSON.parse(el.dataset.key) : "", fecha: el.dataset.fecha || "", txt: el.textContent, memoTxt: (document.getElementById("bxpremem") || {}).textContent || "", lazyTxt: (document.getElementById("bxprelz") || {}).textContent || "" } : null; }
  function recalc() {
    store.set(LS, JSON.stringify(P));
    RGEN++; const g = RGEN; BXWEB.ver++;
    Object.keys(LZ).forEach((k) => delete LZ[k]); Object.keys(LZP).forEach((k) => delete LZP[k]);
    WK.main.cancelStale(g); WK.lazy.cancelStale(g); HELP.forEach((w) => w.terminate()); HELP = [];
    const v0 = AG.validate(P);
    if (v0.some((v) => v.lvl === "error")) { VAL = v0; A = null; calc = false; $("#busy").textContent = "Corrija los datos marcados"; renderAll(); return; }
    const t0 = performance.now(), Ps = Object.assign({}, P), key = JSON.stringify(Ps);
    const pre = preOf();
    if (pre && pre.key === key) {                                     // valores por defecto: resultado precalculado al compilar, en tareas cortas separadas
      calc = true; $("#busy").textContent = "Cargando el resultado precalculado…"; renderBadges();
      setTimeout(() => {
        if (g !== RGEN) return;
        const r = JSON.parse(pre.txt, (k, v) => (v === "__NaN" ? NaN : v === "__Inf" ? Infinity : v === "__-Inf" ? -Infinity : v));
        setTimeout(() => {
          if (g !== RGEN) return;
          apply(r); calc = false; preUsed = true;
          if (pre.lazyTxt) { try { const lzr = JSON.parse(pre.lazyTxt, (k, v) => (v === "__NaN" ? NaN : v === "__Inf" ? Infinity : v === "__-Inf" ? -Infinity : v)); ["SC", "MK", "CN"].forEach((k) => { if (lzr[k]) LZ[k] = lzr[k]; }); if (lzr.TH) { TH = lzr.TH; THkey = key; } } catch (e) { } }
          setTimeout(() => {
            if (g !== RGEN) return;
            $("#busy").textContent = `Valores por defecto: resultado precalculado al compilar (${pre.fecha}) · ${fmt(performance.now() - t0, 3)} ms`;
            renderAll();
            WK.main.call({ op: "analyze", P: Ps }, g).catch(() => { });   // calienta el worker (caché del dimensionamiento BX) para los bloques diferidos
          }, 0);
        }, 0);
      }, 0);
      return;
    }
    calc = true; calcErr = ""; $("#busy").textContent = "Calculando en segundo plano (dimensionamiento BX)…"; renderBadges();
    WK.main.call({ op: "analyze", P: Ps }, g).then((res) => {
      if (g !== RGEN) return;
      apply(res); calc = false;
      $("#busy").textContent = A ? `Recalculado en ${fmt((performance.now() - t0) / 1000, 3)} s (worker)` : "Corrija los datos marcados";
      renderAll();
    }, (err) => { if (g !== RGEN || err.message === "cancelado") return; calc = false; calcErr = err.message; A = null; VAL = [{ lvl: "error", msg: "Error de cálculo: " + err.message }]; $("#busy").textContent = "Error de cálculo"; renderAll(); });
  }

  /* ---------- encabezado ---------- */
  function renderBadges() {
    const pre = calc ? `<span class="badge b-pend" id="calcBadge" title="El worker está recalculando; se muestran los resultados anteriores">Calculando…</span>` : "";
    if (!A) { $("#badges").innerHTML = pre || `<span class="badge b-fail">Datos inválidos</span>`; return; }
    const v = A.verdict;
    const fuEst = Math.max(0, ...A.checks.filter((c) => c.sys === "est" && c.kind === "fu" && isFinite(c.fu)).map((c) => c.fu));
    const nF = A.checks.filter((c) => c.st === "fail").length;
    $("#badges").innerHTML = pre + [
      `<span class="badge b-eg b-${egCls(v.estado_global)}" id="estadoGlobal" title="Estado global del núcleo (verdict.estado_global)">${v.estado_global === "CUMPLE" ? "✓" : "✗"} ESTADO GLOBAL: ${esc(v.estado_global)}${(v.pendientes_criticos || []).length ? ` · FU pend. ${fu2(v.fuMaxPend)}` : ""}</span>`,
      `<span class="badge ${v.gira ? "b-ok" : "b-fail"}">${v.gira ? "✓ GIRA" : "✗ NO GIRA"} · FS ${fmt(A.R.cd ? A.R.cd.FS : NaN, 3)}</span>`,
      `<span class="badge ${v.estructura && !(v.pendientes_criticos || []).length ? (v.warnEst ? "b-warn" : "b-ok") : "b-fail"}">${v.estructura ? ((v.pendientes_criticos || []).length ? "✗ ESTRUCTURA PENDIENTE DE DECISIÓN" : "✓ ESTRUCTURA CUMPLE") : `✗ ${nF} NO CUMPLE`} · FU ${fu2(fuEst)}</span>`,
      `<span class="badge b-info">Masa ${fmt(A.R.m.total, 4)} kg</span>`,
      A.bx ? `<span class="badge b-info" id="bxBadge" title="TT300-BX: disco, pastillas y portador (A.bx)">BX · disco ${fmt(A.bx.disco.t)} mm · ${A.bx.pastillas.n} pastillas ${pkTxt(A.bx.pastillas)} · portador ${fmt(A.bx.portador.t)} mm</span>` : "",
      v.pend ? `<span class="badge b-pend">${v.pend} pendiente</span>` : "",
      X && X.every((c) => c.ok) && AU && AU.ok ? `<span class="badge b-ok">Revisión cruzada OK</span>` : `<span class="badge b-warn">Revisar agentes</span>`,
    ].join("");
  }

  /* ---------- Resumen ---------- */
  function msgs() {
    if (calc && !A) return `<div class="msg ok" id="calcMsg">Calculando en segundo plano (dimensionamiento BX: disco, tornillos, portador y pastillas)… la página sigue respondiendo.</div>`;
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
    const v = A.verdict, eg = v.estado_global, ok = egCls(eg);
    el.innerHTML = msgs() + `
    <div class="card vered vd-${ok}" id="veredicto" style="margin-top:10px"><h3>Veredicto global</h3><div class="big vd-${ok}" id="estadoGlobalRes">${esc(eg)}</div>
      <div class="note">¿Gira? ${v.gira ? "sí" : "NO"} · estructura ${v.estructura ? "cumple" : "NO cumple"} · pendientes críticos ${(v.pendientes_criticos || []).length}${(v.pendientes_criticos || []).length ? ` (FU máx. ${fu2(v.fuMaxPend)})` : ""} · limitaciones de uso ${limUsoLista(v).length}</div>
      ${pendCritHTML(v, "pendCrit")}${limUsoHTML(v, "limUso")}</div>
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
      <div class="card" id="cardEst"><h3>Estructura</h3><div class="big" style="color:var(${A.verdict.estructura && !(v.pendientes_criticos || []).length ? "--ok" : "--fail"})">${A.verdict.estructura ? ((v.pendientes_criticos || []).length ? "Pendiente de decisión" : "Cumple") : "No cumple"}</div>
        <div class="note" style="margin:4px 0 0">Estado global: <b id="estadoGlobalEst" style="color:var(--${ok})">${esc(eg)}</b></div>
        <div class="kv" style="margin-top:6px;grid-template-columns:minmax(120px,auto) 1fr">
          <span>FU máximo</span><span>${est.length ? fu2(est[0].fu) : "—"}</span>
          <span>Gobierna</span><span style="font-family:var(--sans);text-align:right">${est.length ? esc(est[0].grp + ": " + est[0].name) : ""}</span>
          <span>No cumple / monitoreo</span><span>${A.checks.filter((x) => x.st === "fail").length} / ${A.checks.filter((x) => x.st === "warn").length}</span>
          <span>Pendientes / críticos (FU &gt; 1)</span><span>${A.verdict.pend} / ${(v.pendientes_criticos || []).length}</span>
        </div>
        ${pendCritHTML(v, "pendCritEst")}
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
    <div class="card" style="margin-top:12px" id="bxResumen"><h3>Interfaz TT300-BX: disco inoxidable (lámina soldada o disco atornillado según bx_disc_modo) + pastillas de UHMW (detalle en la pestaña «Disco y pastillas»)</h3>${bxSummary()}</div>
    <div class="card" style="margin-top:12px"><h3>Comparación con equipos comerciales</h3>${lzSlot(marketTable, ["MK"])}</div>`;
  }
  // resumen de la interfaz BX: todo sale de A.bx (BX.design del módulo) y de las filas «BX ·» de A.checks
  const bxRowsOf = () => A.checks.filter((c) => c.bx || /^BX ·/.test(c.name));
  // forma de la pastilla según lo que exponga el módulo (bx.pastillas.forma / lado / r_esquina); sin «lado», redonda de Ø d
  const pkSq = (pa) => pa.lado != null && isFinite(pa.lado) && !/redond/i.test(String(pa.forma || "")) && pa.forma !== 0;
  const pkW = (pa) => (pkSq(pa) ? pa.lado : pa.d);
  const pkTxt = (pa, sig) => (pkSq(pa) ? `□${fmt(pa.lado, sig || 3)}${pa.r_esquina ? " R" + fmt(pa.r_esquina, 2) : ""}` : `Ø${fmt(pa.d, sig || 3)}`);
  function bxGov(re) { const r = bxRowsOf().filter((c) => re.test(c.name) && c.fu != null && isFinite(c.fu) && c.kind !== "info"); return r.reduce((m, c) => (!m || c.fu > m.fu ? c : m), null); }
  function bxSummary() {
    const D = A.bx; if (!D) return `<div class="msg warn">El módulo BX no entregó geometría (A.bx vacío).</div>`;
    const d = D.disco, tw = d.tornillos, pa = D.pastillas, po = D.portador, ifc = A.R.ifc;
    const gv = (re) => { const c = bxGov(re); return c ? `<span class="st st-${c.st}">FU ${fu3(c.fu)}</span> <span class="ref">${esc(c.name.replace(/^BX · /, ""))}</span>` : "—"; };
    const rows = bxRowsOf(), nF = rows.filter((c) => c.st === "fail").length, nW = rows.filter((c) => c.st === "warn").length, nPd = rows.filter((c) => c.st === "pend").length;
    return `<div class="scroll"><table id="bxSumTab"><tr><th>Pieza</th><th>Dimensión adoptada (módulo BX)</th><th>Verificación gobernante</th></tr>
      <tr><td>Disco</td><td>${esc(d.material)}, <b>t = ${fmt(d.t)} mm</b> (requerido ${fmt(d.t_req, 3)}), ${d.semidiscos} semidiscos de ${fmt(d.masa_semidisco, 3)} kg (masa ${fmt(d.masa, 4)} kg)</td><td>${gv(/^BX · Disco/)}</td></tr>
      <tr><td>Tornillos del disco</td><td><b>${tw.n} × ${esc(tw.designacion_base)}</b>, malla ${fmt(tw.paso_malla, 3)} mm, ${tw.anillos.length} anillos</td><td>${gv(/^BX · Tornillos del disco/)}</td></tr>
      <tr><td>Pastillas</td><td><b>${pa.n} × ${pkTxt(pa, 4)} × ${fmt(pa.H, 3)} mm</b>${pa.forma != null ? ` (${esc(String(pa.forma))})` : ""}, saliente h_p = ${fmt(pa.h_p, 3)} mm, interferencia ${fmt(pa.interferencia, 3)} mm, ${fmt(pa.masa_total, 3)} kg; cobertura ${fmt(pa.cobertura, 2)}</td><td>${gv(/^BX · Pastillas/)}</td></tr>
      <tr><td>Tornillo de pastilla</td><td>${esc((pa.tornillo || {}).designacion || "—")}</td><td>${gv(/^BX · Pastillas: tornillo|^BX · Tornillo de pastilla/)}</td></tr>
      <tr><td>Portador</td><td>t = <b>${fmt(po.t)} mm</b>, R${fmt(po.R_int, 4)}…R${fmt(po.R_ext, 4)}, paso ${fmt(po.paso, 4)}, ligamento ${fmt(po.ligamento, 3)}, patrón ${esc(po.patron.tipo)}, filetes z${fmt(po.filetes.w)}${po.tapones.n ? `, ${po.tapones.n} agujeros de soldadura` : ""} (${fmt(po.masa, 4)} kg)</td><td>${gv(/^BX · Portador/)}</td></tr>
      <tr><td>Interfaz</td><td>δ = ${fmt(ifc.delta, 3)} mm sobre la base (portador + saliente + disco); eje del cilindro +${fmt(A.R.hax, 4)} mm</td><td>—</td></tr></table></div>
      <div class="note">Filas BX en «Verificaciones»: ${rows.length} (${nF} no cumplen, ${nW} en monitoreo, ${nPd} pendientes). μ de diseño de la opción B (${fmt(A.R.mu.d)}); μ efectivo de las piezas de acero ${fmt(D.diseno.mu_eff, 3)}. Fabricación antes → después y planta del disco en la pestaña «Disco y pastillas».</div>`;
  }
  function casesTable() {
    const R = A.R;
    return `<div class="scroll"><table><tr><th>Caso</th><th class="n">μ</th><th class="n">r (mm)</th><th class="n">T (kN·m)</th><th class="n">F/cil (kN)</th><th class="n">p (bar)</th><th class="n">FS</th><th>Resultado</th></tr>
      ${R.cases.map((c) => `<tr><td>${esc(c.name)}</td><td class="n">${fmt(c.mu)}</td><td class="n">${fmt(c.r, 4)}</td><td class="n">${fmt(c.T)}</td><td class="n">${fmt(c.F)}</td><td class="n">${fmt(c.p)}</td><td class="n">${fmt(c.FS)}</td>
      <td><span class="st st-${c.id === "seco" ? (c.turns ? "info" : "info") : c.turns ? (c.p > P.p_alarm ? "warn" : "ok") : "fail"}">${c.turns ? (c.p > P.p_alarm ? "Gira (sobre alarma)" : "Gira") : "No gira"}</span></td></tr>`).join("")}</table></div>
      <div class="note">F/cil = T/(n·brazo_mín·η_c). Fuerza de calado: ${fmt(R.Fstall)} kN a ${fmt(P.p_relief)} bar. El caso de acero seco es referencial: la operación exige lubricación.</div>`;
  }

  /* ---------- Modelo: planta y corte ---------- */
  const isPiv = () => (TT.driveMode ? TT.driveMode(P) : P.drive_mode) === 2;
  // modo pivotado tipo KIET en planta: lo fijo de TT.pivotGeo (ojales E, placas-leva con pernos) y lo móvil de TT.pivotAt al tomar el pasador
  function pivotPlan(R) {
    const g = TT.pivotGeo(P); if (!g) return "";
    const D = TT.designDrive(P, R).pivotado || {}, pl = D.placa_leva || {}, y = (v) => -v, o = [];
    const pts = (arr) => arr.map(([a, b]) => `${a},${y(b)}`).join(" ");
    // placas-guía curvas: trayecto con arcos SVG desde los segmentos del núcleo (las del giro horario son la imagen especular, ACC-024)
    const sp = (segs, z) => SIM.segPath(segs, (v) => v, y, (v) => v, z);
    Object.entries(g.placas).forEach(([k, pc]) => {
      const act = k.endsWith("_antihorario");
      o.push(`<g opacity="${act ? 1 : 0.35}" class="mdl-placa" data-placa="${k}"><path d="${sp(pc.segmentos_contorno, true)}" fill="#c9b37e" fill-opacity=".5" stroke="#8a6d2f" stroke-width="4"/>${act ? `<path d="${sp(pc.segmentos_canto)}" fill="none" stroke="#b4570b" stroke-width="7"/>` : ""}${pc.pernos.map(([a, b]) => `<circle cx="${a}" cy="${y(b)}" r="${(pl.d_perno || 20) / 2}" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>`).join("")}${(pc.pasadores_posicion || []).map(([a, b]) => `<circle cx="${a}" cy="${y(b)}" r="${(P.pv_dd || 16) / 2}" fill="var(--pendbg)" stroke="var(--pend)" stroke-width="2"/>`).join("")}</g>`);
    });
    const sE = (D.fabricacion || {}).soporte_E || {};               // soporte del ojal E abierto hacia la mesa: piezas en planta del núcleo
    g.E.forEach(([ex, ey], i) => {
      const pz = ((sE["cilindro" + (i + 1)] || {}).piezas || []).filter((q) => q.poligono && !/tapa_inf/.test(q.id));
      if (pz.length) pz.forEach((q) => o.push(`<polygon points="${pts(q.poligono)}" fill="var(--soft)" fill-opacity="${/tapa/.test(q.id) ? 0.6 : 1}" stroke="var(--ink)" stroke-width="4"/>`));
      else { const h = g.ojalE.lado_cajon / 2; o.push(`<rect x="${ex - h}" y="${y(ey) - h}" width="${2 * h}" height="${2 * h}" fill="var(--soft)" stroke="var(--ink)" stroke-width="5"/>`); }
      o.push(`<circle cx="${ex}" cy="${y(ey)}" r="${g.ojalE.d / 2}" fill="var(--ink)"/>`);
    });
    // bloque-uña: garra real con arcos SVG desde pivotGeo().bloque.garra.contorno (SIM.garraSegs) y el contacto del asiento; sin garra, la cara heredada
    const blq = (q, f, sen, ci) => {
      const gs = SIM.garraSegs ? SIM.garraSegs(g, q, f) : null;
      if (!gs) return `<polygon points="${pts(q.una.cuerpo.map(f))}" fill="var(--load)" opacity=".85"/><polygon points="${pts(SIM.caraBloque(g, q.una.cara).map(f))}" fill="var(--load)"/>`;
      const ac = q.asiento.contacto && f(q.asiento.contacto), cA = f(q.asiento.centro);
      return `<path d="${sp(gs, true)}" class="mdl-garra" data-sen="${sen}" data-cil="${ci + 1}" fill="var(--load)" fill-opacity=".85" stroke="var(--ink)" stroke-width="2"/><path d="${sp(gs.filter((c) => c.rol === "asiento"))}" fill="none" stroke="var(--ink)" stroke-width="6"/>`
        + (q.asiento.asentado ? `<circle cx="${cA[0]}" cy="${y(cA[1])}" r="${P.d_pin / 2}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-dasharray="6 4"/>` : "")
        + (ac ? `<circle cx="${ac[0]}" cy="${y(ac[1])}" r="9" fill="var(--fail)"/>` : "");
    };
    ["horario", "antihorario"].forEach((sen) => {
      const q = TT.pivotAt(P, P.s_free, "empuje", sen); if (!q) return;
      const act = sen === "antihorario";
      [[q.E, q.Q, (p) => p], [[-q.E[0], -q.E[1]], [-q.Q[0], -q.Q[1]], (p) => [-p[0], -p[1]]]].forEach(([E, Q, f], ci) => {
        const L = Math.hypot(Q[0] - E[0], Q[1] - E[1]), u = [(Q[0] - E[0]) / L, (Q[1] - E[1]) / L], t = [-u[1], u[0]], lb = Math.min(L - 30, P.L0 - 30);
        const bar = (a, b, w) => [[a, -1], [b, -1], [b, 1], [a, 1]].map(([s_, k]) => [E[0] + s_ * u[0] + k * w / 2 * t[0], E[1] + s_ * u[1] + k * w / 2 * t[1]]);
        o.push(`<g opacity="${act ? 1 : 0.3}"><polygon points="${pts(bar(0, lb, P.D_body))}" fill="var(--acc)" opacity=".55"/><polygon points="${pts(bar(lb, L, P.d_rod))}" fill="var(--acc)"/>
          ${blq(q, f, sen, ci)}<polygon points="${pts(q.una.cubo.map(f))}" fill="var(--panel)" stroke="var(--ink)" stroke-width="3"/>
          <circle cx="${Q[0]}" cy="${y(Q[1])}" r="${g.pasadorQ.d / 2}" fill="none" stroke="var(--ink)" stroke-width="3"/></g>`);
        if (act) { const A_ = f(q.pasadores.A); o.push(`<circle cx="${A_[0]}" cy="${y(A_[1])}" r="${P.d_pin / 2 + 6}" fill="none" stroke="var(--load)" stroke-width="8"/>`); }
      });
      if (act && D.brazo_ef_min != null) { const A_ = q.pasadores.A; o.push(`<text x="${A_[0] / 2}" y="${y(A_[1] / 2) - 14}" font-size="44" text-anchor="middle" fill="var(--load)">brazo ef. mín. ${fmt(D.brazo_ef_min, 3)} mm</text><line x1="0" y1="0" x2="${A_[0]}" y2="${y(A_[1])}" stroke="var(--load)" stroke-width="3"/>`); }
    });
    return o.join("");
  }
  function planSVG() {
    const R = A.R, K = R.K, B = P.B, S = B / 2 + 160;
    const y = (v) => -v;
    const o = [];
    o.push(`<rect x="${-B / 2}" y="${-B / 2}" width="${B}" height="${B}" fill="var(--soft)" stroke="var(--steel)" stroke-width="4"/>`);
    if (P.rim_t > 0) o.push(`<rect x="${-B / 2 + P.rim_t / 2}" y="${-B / 2 + P.rim_t / 2}" width="${B - P.rim_t}" height="${B - P.rim_t}" fill="none" stroke="var(--steel)" stroke-width="${P.rim_t}" opacity=".6"/>`);
    const INS = insertoOf(R);
    if (INS) {                                                        // refuerzos cuadrados (núcleo): cuadrado, tapones y atiesador tangencial si lo hay
      const tp = INS.tapones || {}, at = INS.atiesadores;
      INS.cuadrado.vertices.forEach((pl, k) => {
        const c = areaC(pl), ps = (tp.posiciones || [])[k] || [], ra = at && at.por_esquina && at.por_esquina[k];
        o.push(`<g class="mdl-ins" data-k="${k}"><polygon points="${pl.map(([a, b]) => `${a},${y(b)}`).join(" ")}" fill="var(--ins)" fill-opacity=".35" stroke="var(--insk)" stroke-width="5"/>${ps.map(([a, b]) => `<circle class="mdl-tap" cx="${a}" cy="${y(b)}" r="${(tp.d || 44) / 2}" fill="var(--panel)" stroke="var(--insk)" stroke-width="4"/>`).join("")}${ra ? `<polygon class="mdl-ati" points="${ra.poligono.map(([a, b]) => `${a},${y(b)}`).join(" ")}" fill="var(--insk)" fill-opacity=".8" stroke="var(--insk)" stroke-width="3"/>` : ""}
          <text x="${c[0]}" y="${y(c[1]) + 14}" font-size="40" text-anchor="middle" fill="var(--insk)" font-weight="700" paint-order="stroke" stroke="var(--panel)" stroke-width="8" stroke-linejoin="round" class="mdl-ins-t">refuerzo t ${fmt(INS.t_d, 2)}</text></g>`);
      });
    }
    const Rt = P.D_top / 2;
    o.push(`<circle r="${Rt}" fill="var(--panel)" stroke="var(--ink)" stroke-width="5"/>`);
    o.push(`<circle r="${TT.prIn(P)}" fill="none" stroke="var(--steel)" stroke-width="2" stroke-dasharray="14 10"/>`);
    TT.parseRings(P.rings).forEach((r) => o.push(`<circle r="${r}" fill="none" stroke="var(--steel)" stroke-width="${Math.max(3, P.t_web)}" stroke-dasharray="20 12" opacity=".8"/>`));
    for (let k = 0; k < P.N_rib; k++) { const a = 2 * Math.PI * k / P.N_rib; o.push(`<line x1="${P.D_hub / 2 * Math.cos(a)}" y1="${y(P.D_hub / 2 * Math.sin(a))}" x2="${P.R_rib * Math.cos(a)}" y2="${y(P.R_rib * Math.sin(a))}" stroke="var(--steel)" stroke-width="${Math.max(3, P.t_rib)}" stroke-dasharray="20 12" opacity=".8"/>`); }
    o.push(`<circle r="${P.D_hub / 2}" fill="none" stroke="var(--steel)" stroke-width="4"/><circle r="${P.D_piv / 2}" fill="var(--steel)" opacity=".5"/>`);
    for (let k = 0; k < P.N_pin; k++) { const a = Math.PI / P.N_pin + 2 * Math.PI * k / P.N_pin; o.push(`<circle cx="${P.R_pin * Math.cos(a)}" cy="${y(P.R_pin * Math.sin(a))}" r="${P.d_pin / 2}" fill="var(--ink2)"/>`); }
    // cáncamos
    [[1, 1], [-1, 1], [1, -1], [-1, -1]].forEach(([sx, sy]) => o.push(`<rect x="${sx * P.x_lug - 40}" y="${sy * (B / 2 - P.c_lug) - 40}" width="80" height="80" rx="14" fill="none" stroke="var(--ink2)" stroke-width="4"/>`));
    if (isPiv()) o.push(pivotPlan(R));
    // accionamiento guiado: bancadas, ménsulas (ambos sentidos), patines, uñas y cilindros (sentido antihorario)
    const g = K, bg = isPiv() ? null : TT.bracketGeo(P), cam = !isPiv() && TT.camGeo ? TT.camGeo(P) : null;
    if (!isPiv()) for (const sx of [1, -1]) {
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
        if (cam) {                                                    // leva de reenganche (opt_cam): riel fijo con bolsillo y rampa, y seguidor de rodillo al tomar el pasador (núcleo: camGeo, camAt)
          const L = TT.designDrive(P, R).levaGuiada, xo = L && L.x ? L.x.borde_exterior : Math.max(...cam.perfil_y.map((q) => q.x_canto)) + 40, pr = cam.perfil_y;
          const rail = pr.map((q) => [q.x_canto, q.y]).concat([[xo, pr[pr.length - 1].y], [xo, pr[0].y]]);
          o.push(`<polygon points="${rail.map(([a, b]) => `${sx * a},${y(dy * b)}`).join(" ")}" fill="#c9b37e" fill-opacity=".55" stroke="#8a6d2f" stroke-width="4"/>`);
          const ca = TT.camAt(P, P.s_free, "empuje"), rF = Math.max(5, cam.x_canto_toma - cam.x_perno_toma - cam.holgura_toma);
          o.push(`<circle cx="${sx * ca.x_seguidor}" cy="${y(dy * ca.y_seguidor)}" r="${rF}" fill="#e2c46f" stroke="var(--ink)" stroke-width="3"/>`);
        }
        if (sx > 0) {
          o.push(`<line x1="0" y1="0" x2="${xa}" y2="0" stroke="var(--load)" stroke-width="3"/><text x="${xa / 2}" y="-14" font-size="44" text-anchor="middle" fill="var(--load)">brazo ${fmt(g.a_min, 3)} mm</text>`);
          o.push(`<line x1="${xa}" y1="${y(yp)}" x2="${X}" y2="${y(yp)}" stroke="var(--load)" stroke-width="3" stroke-dasharray="14 10"/><text x="${(xa + X) / 2}" y="${y(yp) + (dy > 0 ? 60 : -30)}" font-size="40" text-anchor="middle" fill="var(--load)">Δ ${fmt(g.DeltaMax, 3)}</text>`);
        }
      }
    }
    o.push(`<text x="0" y="${-B / 2 - 50}" text-anchor="middle" font-size="52">Base ${fmt(B, 4)} × ${fmt(B, 4)} · mesa Ø${fmt(P.D_top, 4)} · ${P.N_pin} pasadores Ø${fmt(P.d_pin)} en R${fmt(P.R_pin, 4)}</text>`);
    const ley = (isPiv() ? ["Cilindros pivotados y bloques-uña al tomar el pasador · giro antihorario (tenue: giro horario)", "Ojales E en diagonal · 4 placas-guía curvas (canto guía en naranja)"] : ["Cilindros y patines al tomar el pasador · giro antihorario (ménsulas tenues: giro horario)" + (cam ? " · leva de reenganche" : "")]).map((t) => [t, "var(--ink2)", ""]);
    if (INS) ley.push([`Base t = ${fmt(INS.t_base, 2)} mm entera · ${INS.n} refuerzos cuadrados ${fmt(INS.lado, 3)} × ${fmt(INS.lado, 3)} × ${fmt(INS.t_d, 2)} mm soldados sobre la base (${fmt(INS.masa, 3)} kg c/u)`, "var(--insk)", ' id="mdlInsRot"']);
    if (INS) ley.push([`bajo ${isPiv() ? "los soportes del ojal E" : "las ménsulas del ojal trasero"} · ${(INS.tapones || {}).n_por_esquina || 0} tapones Ø${fmt((INS.tapones || {}).d || 0)}${INS.atiesadores ? ` · atiesador ${fmt(INS.atiesadores.t)} × ${fmt(INS.atiesadores.h)} × ${fmt(INS.atiesadores.largo)}` : " · sin atiesador"}`, "var(--insk)", ' id="mdlInsRot2"']);
    ley.forEach(([t, c, id], k) => o.push(`<text x="0" y="${B / 2 + 80 + 50 * k}" text-anchor="middle" font-size="40" fill="${c}"${id}>${esc(t)}</text>`));
    return `<svg viewBox="${-S} ${-S} ${2 * S} ${S + B / 2 + 100 + 50 * (ley.length - 1)}" role="img" aria-label="Planta de la tornamesa">${o.join("")}</svg>`;
  }
  // modo pivotado en alzado desarrollado (distancias radiales al eje de giro): placa-leva, bloque-uña con su pasador Q, cilindro y soporte del ojal E
  function pivotSection(R, pv, gP, X, Z, zc, tb) {
    const q = TT.pivotAt(P, P.s_free, "empuje", "antihorario"); if (!q) return "";
    const rr = (pts) => { const v = pts.map(([a, b]) => Math.hypot(a, b)); return [Math.min(...v), Math.max(...v)]; };
    const pl = pv.placa_leva || {}, bl = pv.bloque_una || {}, se = pv.soporte_E || {}, o = [];
    const [p0, p1] = rr(gP.placas["1_antihorario"].contorno), [b0, b1] = rr(q.una.cuerpo.concat(q.una.cubo)), rQ = Math.hypot(...q.Q), rE = Math.hypot(...q.E);
    o.push(`<rect x="${X(p0)}" y="${Z(tb + pl.t)}" width="${p1 - p0}" height="${pl.t}" fill="#c9b37e" stroke="#8a6d2f" stroke-width="1.5"><title>Placa-leva t = ${fmt(pl.t)} mm</title></rect>`);
    o.push(`<rect x="${X(b0)}" y="${Z(bl.z_inf + bl.h)}" width="${b1 - b0}" height="${bl.h}" fill="var(--load)" opacity=".75"><title>Bloque-uña h = ${fmt(bl.h)} mm</title></rect>`);
    o.push(`<rect x="${X(rQ - bl.d_Q / 2)}" y="${Z(R.blk.zCam + bl.l_pasador_Q)}" width="${bl.d_Q}" height="${bl.l_pasador_Q}" fill="none" stroke="var(--ink)" stroke-width="2"><title>Pasador Q Ø${fmt(bl.d_Q)} × ${fmt(bl.l_pasador_Q)}</title></rect>`);
    const zp = (((pv.fabricacion || {}).soporte_E || {}).z_paredes) || [tb, tb + se.alto], zs0 = zp[0], zs1 = zp[1];   // paredes del soporte (núcleo: fabricacion.soporte_E.z_paredes, sobre el refuerzo: z = t)
    // rótulo del soporte del ojal E leído del núcleo (fabricacion.soporte_E: tipo, lado y tapas.lado): cajón abierto hacia la mesa, no un ojal en cajón cerrado
    const fE = (pv.fabricacion || {}).soporte_E || {}, tipoE = String(fE.tipo || "").split(":")[0].trim();
    const sopETxt = tipoE ? `soporte E: ${tipoE} (lado ${fmt(fE.lado != null ? fE.lado : se.lado_cajon)}${fE.tapas && fE.tapas.lado ? ", tapas " + fmt(fE.tapas.lado) : ""})` : `ojal E (cajón ${fmt(se.lado_cajon)})`;
    o.push(`<rect x="${X(rE - se.lado_cajon / 2)}" y="${Z(zs1)}" width="${se.lado_cajon}" height="${zs1 - zs0}" fill="var(--soft)" stroke="var(--ink)" stroke-width="2"><title>${esc(sopETxt)}</title></rect>`);
    [se.z_tapa_inf, se.z_tapa_sup].forEach((zt) => o.push(`<line x1="${X(rE - se.lado_cajon / 2)}" y1="${Z(zt)}" x2="${X(rE + se.lado_cajon / 2)}" y2="${Z(zt)}" stroke="var(--ink)" stroke-width="3"/>`));
    const rm = rE - (P.L0 - 30) * (rE - rQ) / Math.max(1, Math.hypot(q.Q[0] - q.E[0], q.Q[1] - q.E[1]));
    o.push(`<rect x="${X(Math.min(rm, rE))}" y="${Z(zc + P.D_body / 2)}" width="${Math.abs(rE - rm)}" height="${P.D_body}" fill="var(--acc)" opacity=".55"/>`);
    o.push(`<rect x="${X(Math.min(rQ, rm))}" y="${Z(zc + P.d_rod / 2)}" width="${Math.abs(rm - rQ)}" height="${P.d_rod}" fill="var(--acc)"/>`);
    o.push(`<line x1="${X(rE)}" y1="${Z(tb)}" x2="${X(rE)}" y2="${Z(zs1 + 20)}" stroke="var(--ink2)" stroke-dasharray="8 5"/>`);
    o.push(`<text x="${X(p0)}" y="${Z(tb) + 14}" font-size="13">placa-guía ${fmt(pl.t)}</text><text x="${X(b0)}" y="${Z(bl.z_inf + bl.h) - 6}" font-size="13" fill="var(--load)">bloque-uña h ${fmt(bl.h)}</text><text x="${X(rE)}" y="${Z(zs1) - 6}" font-size="13" text-anchor="middle" id="secSopE">${esc(sopETxt)}</text>`);
    o.push(`<text x="${X(rQ)}" y="${Z(0) + 36}" font-size="12" text-anchor="middle" fill="var(--ink2)">alzado desarrollado a lo largo del cilindro 1 (distancias radiales)</text>`);
    return o.join("");
  }
  function sectionSVG() {
    const R = A.R, tb = P.t_base, hd = P.h_disc, tpr = Math.max(P.t_pr, P.t_top, P.t_bot), ifc = R.ifc, dl = ifc.delta, tm = tb + dl;   // tm: cara inferior de la mesa (sobre los discos de la interfaz)
    const pv = isPiv() ? TT.designDrive(P, R).pivotado : null, gP = pv ? TT.pivotGeo(P) : null;
    const r0 = TT.prIn(P) - 220, r1 = Math.max(P.B / 2 + 40, gP ? Math.hypot(...gP.E[0]) + gP.ojalE.lado_cajon / 2 + 60 : 0), W = r1 - r0, Hs = tm + hd + (P.opt_wood > 0.5 ? P.t_wood : 0) + 160;
    const sc = 1, X = (r) => (r - r0) * sc, Z = (z) => (Hs - 40 - z) * sc;
    const o = [];
    o.push(`<rect x="${X(r0)}" y="${Z(tb)}" width="${X(P.B / 2) - X(r0)}" height="${tb}" fill="var(--steel)" opacity=".55"/>`);
    const INS = insertoOf(R);
    if (INS) {                                                        // refuerzo cuadrado cortado por la línea del soporte: E (pivotado, radial) o y = y_ojal (guiado); pila: base 0…t_base, refuerzo t_base…t, soporte encima
      const g0 = gP ? [0, 0] : [0, R.K.y_eye], u = gP ? (() => { const E = gP.E[0], L = Math.hypot(E[0], E[1]); return [E[0] / L, E[1] / L]; })() : [1, 0];
      const pip = (q, pl) => { let c = false; for (let i = 0, j = pl.length - 1; i < pl.length; j = i++) { const [xi, yi] = pl[i], [xj, yj] = pl[j]; if ((yi > q[1]) !== (yj > q[1]) && q[0] < (xj - xi) * (q[1] - yi) / (yj - yi) + xi) c = !c; } return c; };
      const span = (pls) => { let a = null, b = null; for (let r = 0; r <= 2600; r += 2) { const q = [g0[0] + u[0] * r, g0[1] + u[1] * r]; if (pls.some((pl) => pip(q, pl))) { if (a == null) a = r; b = r; } } return [a, b]; };
      const [s0, s1r] = span(INS.cuadrado.vertices), s1 = s1r == null ? null : Math.min(s1r, gP ? r1 - 20 : P.B / 2), zr = INS.z || [INS.t_base, INS.t];
      if (s0 != null && s1 > s0) {
        o.push(`<rect id="secIns" x="${X(s0)}" y="${Z(zr[1])}" width="${s1 - s0}" height="${zr[1] - zr[0]}" fill="var(--ins)" fill-opacity="${gP ? 0.55 : 0.3}" stroke="var(--insk)" stroke-width="1.5"${gP ? "" : ' stroke-dasharray="6 4"'}><title>Refuerzo cuadrado ${fmt(INS.lado)} × ${fmt(INS.lado)} × ${fmt(INS.t_d)} mm soldado sobre la base de ${fmt(INS.t_base)} mm (z ${fmt(zr[0])}…${fmt(zr[1])})</title></rect>`);
        o.push(`<line x1="${X(s1 - 14)}" y1="${Z(0)}" x2="${X(s1 - 14)}" y2="${Z(INS.t)}" stroke="var(--insk)" stroke-width="1"/><text x="${X(s1 - 20)}" y="${Z(INS.t / 2) + 4}" font-size="13" text-anchor="end" fill="var(--insk)" font-weight="700">t ${fmt(INS.t, 2)}</text>`);
        o.push(`<text x="${X(Math.max(s0, r0)) + 4}" y="${Z(0) + 14}" font-size="13" fill="var(--insk)" font-weight="700" id="secInsT">refuerzo t ${fmt(INS.t_d, 2)} sobre la base de ${fmt(INS.t_base, 2)} (z = ${fmt(INS.t, 2)})${gP ? "" : " · proyectado desde y_ojal"}</text>`);
      }
      const at = INS.atiesadores;
      if (at && at.por_esquina) {                                     // atiesador tangencial cortado por la misma línea
        const [a0, a1] = span(at.por_esquina.map((q) => q.poligono)), za = at.z || [INS.t_base, INS.t_base + at.h];
        if (a0 != null) o.push(`<rect id="secAti" x="${X(a0)}" y="${Z(za[1])}" width="${Math.max(2, a1 - a0)}" height="${za[1] - za[0]}" fill="var(--insk)" fill-opacity=".8"><title>Atiesador tangencial ${fmt(at.t)} × ${fmt(at.h)} × ${fmt(at.largo)} mm</title></rect>`);
      }
    }
    if (P.rim_h > 0) o.push(`<rect x="${X(P.B / 2 - P.rim_t)}" y="${Z(tb + P.rim_h)}" width="${P.rim_t}" height="${P.rim_h}" fill="var(--steel)"/>`);
    const Rt = P.D_top / 2, rpr = TT.prIn(P);
    if (P.opt_wood > 0.5) o.push(`<rect x="${X(r0)}" y="${Z(tm + hd + P.t_wood)}" width="${X(Rt) - X(r0)}" height="${P.t_wood}" fill="#8b5a2b" opacity=".85" stroke="var(--ink)" stroke-width=".6"><title>Madera dura ${fmt(P.t_wood, 3)} mm</title></rect>`);
    if (ifc.bx && A.bx) {                                             // TT300-BX: portador soldado a la base, pastillas de UHMW (corte en y = 0, x > 0) y disco inoxidable bajo la mesa
      const D = A.bx, po = D.portador, pa = D.pastillas, tc = po.t, hp = pa.h_p, td = D.disco.t;
      o.push(`<rect id="secBxPort" x="${X(Math.max(r0, po.R_int))}" y="${Z(tb + tc)}" width="${X(po.R_ext) - X(Math.max(r0, po.R_int))}" height="${tc}" fill="var(--steel)" opacity=".85" stroke="var(--ink)" stroke-width=".6"><title>Portador t = ${fmt(tc)} mm soldado a la base (filetes perimetrales z${fmt(po.filetes.w)})</title></rect>`);
      const rr = [...new Set(pa.lista.filter((q) => q.x > 0 && Math.abs(q.y) < pkW(pa) / 2).map((q) => Math.round(q.x * 10) / 10))].filter((x) => x > r0);
      rr.forEach((x) => o.push(`<rect class="secBxPuck" x="${X(x - pkW(pa) / 2)}" y="${Z(tb + tc + hp)}" width="${pkW(pa)}" height="${tc + hp}" fill="var(--warn)" opacity=".85" stroke="var(--ink)" stroke-width=".6"><title>Pastilla UHMW ${pkTxt(pa)} × ${fmt(pa.H)} mm, saliente ${fmt(hp)} mm</title></rect>`));
      o.push(`<rect id="secBxDisco" x="${X(Math.max(r0, D.disco.R_int))}" y="${Z(tb + tc + hp + td)}" width="${X(D.disco.R_ext) - X(Math.max(r0, D.disco.R_int))}" height="${td}" fill="var(--acc)" opacity=".75" stroke="var(--ink)" stroke-width=".6"><title>Disco ${esc(D.disco.material)} t = ${fmt(td)} mm atornillado a la mesa</title></rect>`);
      o.push(`<text x="${X(r0) + 250}" y="${Z(tb) + 14}" font-size="13" fill="var(--ink)" id="secBxTxt">portador ${fmt(tc)} + saliente ${fmt(hp)} + disco ${fmt(td)} = δ ${fmt(ifc.delta, 3)} mm</text>`);
    } else if (ifc.o > 0) {                                           // discos inoxidables (A y B) y lámina UHMW (B) entre la base y la mesa
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
    if (pv && gP) o.push(pivotSection(R, pv, gP, X, Z, zc, tb));
    else {
    o.push(`<rect x="${X(P.x_g - P.w_bed / 2)}" y="${Z(zb)}" width="${P.w_bed}" height="${P.t_bed}" fill="var(--steel)" opacity=".8"/>`);
    o.push(`<rect x="${X(P.x_g - P.w_slot / 2)}" y="${Z(zb)}" width="${P.w_slot}" height="${P.h_slot}" fill="var(--panel)"/>`);
    if (P.h_tee > 0) o.push(`<rect x="${X(P.x_g - P.w_tee / 2)}" y="${Z(zb - P.h_slot)}" width="${P.w_tee}" height="${P.h_tee}" fill="var(--panel)"/>`);
    o.push(`<rect x="${X(P.x_g - P.w_s / 2)}" y="${Z(zc + fh / 2)}" width="${P.w_s}" height="${zc + fh / 2 - zb}" fill="var(--panel)" stroke="var(--ink)" stroke-width="2"/>`);
    o.push(`<rect x="${X(P.x_g - P.w_slot / 2 + 1)}" y="${Z(zb)}" width="${P.w_slot - 2}" height="${P.h_slot - 2}" fill="var(--ink2)"/>`);
    if (P.h_tee > 0) o.push(`<rect x="${X(P.x_g - P.w_tee / 2 + 1)}" y="${Z(zb - P.h_slot + 1)}" width="${P.w_tee - 2}" height="${P.h_tee - 2}" fill="var(--ink2)"/>`);
    o.push(`<rect x="${X(K.mouthX)}" y="${Z(zc + P.dog_h / 2 + 10)}" width="${P.x_g - P.w_s / 2 - K.mouthX}" height="${P.dog_h + 20}" fill="none" stroke="var(--ink)" stroke-width="2"/>`);
    o.push(`<rect x="${X(K.tipX)}" y="${Z(zc + P.dog_h / 2)}" width="${K.mouthX + P.L_in - K.tipX}" height="${P.dog_h}" fill="var(--load)" opacity=".75"/>`);
    o.push(`<line x1="${X(P.x_g)}" y1="${Z(tb)}" x2="${X(P.x_g)}" y2="${Z(zc + fh / 2 + 20)}" stroke="var(--ink2)" stroke-dasharray="8 5"/>`);
    const LG = TT.camGeo && TT.camGeo(P) ? TT.designDrive(P, R).levaGuiada : null;
    if (LG && LG.z && LG.x) {                                         // leva de reenganche en alzado: riel sobre el patín y seguidor de rodillo en su perno (núcleo: designDrive.levaGuiada)
      const z = LG.z, x = LG.x, rF = Math.max(5, x.canto_toma - x.perno_seguidor_toma - (LG.holgura_toma || 0));
      o.push(`<rect x="${X(x.canto_toma)}" y="${Z(z.sup_riel)}" width="${x.borde_exterior - x.canto_toma}" height="${z.sup_riel - z.inf_riel}" fill="#c9b37e" stroke="#8a6d2f" stroke-width="1.5"><title>Riel-leva t = ${fmt(z.sup_riel - z.inf_riel)} mm</title></rect>`);
      o.push(`<line x1="${X(x.perno_seguidor_toma)}" y1="${Z(z.sup_una)}" x2="${X(x.perno_seguidor_toma)}" y2="${Z(z.sup_riel - 4)}" stroke="var(--ink)" stroke-width="3"/>`);
      o.push(`<rect x="${X(x.perno_seguidor_toma - rF)}" y="${Z(z.sup_riel - 4)}" width="${2 * rF}" height="${z.sup_riel - z.inf_riel - 8}" rx="4" fill="#e2c46f" stroke="var(--ink)" stroke-width="1"><title>Seguidor de rodillo</title></rect>`);
      o.push(`<text x="${X(x.borde_exterior)}" y="${Z(z.sup_riel) - 4}" font-size="13" text-anchor="end">leva de reenganche</text>`);
    }
    }
    const dim = (r, z0, z1, txt, side) => `<line x1="${X(r)}" y1="${Z(z0)}" x2="${X(r)}" y2="${Z(z1)}" stroke="var(--ink)" stroke-width="1"/><text x="${X(r) + (side || 6)}" y="${(Z(z0) + Z(z1)) / 2 + 4}" font-size="13" ${side < 0 ? 'text-anchor="end"' : ""}>${txt}</text>`;
    o.push(dim(r0 + 8, tm, tm + hd, `h ${fmt(hd, 3)}`, 6));
    o.push(dim(r0 + 110, 0, tb, `base ${fmt(tb)}`, 6));
    o.push(dim(P.R_pin, tm + tpr, tm + hd - tpr, `libre ${fmt(TT.pinClear(P))}`, -P.d_pin / 2 - 8));
    o.push(`<text x="${X(Rt) + 8}" y="${Z(tm + hd) + 14}" font-size="13">${Math.round(P.bx_mesa_entera == null ? 1 : P.bx_mesa_entera) === 1 ? "plancha entera" : "anillo"} ${fmt(tpr)}</text>`);
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
      <div class="card"><h3>${isPiv() ? "Alzado desarrollado del cilindro pivotado (escala 1:1 relativa)" : "Corte radial por el patín (escala 1:1 relativa)"}</h3>${sectionSVG()}
        ${isPiv() ? (() => { const D = TT.designDrive(P, A.R).pivotado || {}; return `<div class="kv" style="margin-top:10px">
          <span>Ojal E (x, y) / radio R_E / φ_E</span><span>${fmt(D.E ? D.E[0] : NaN, 4)}, ${fmt(D.E ? D.E[1] : NaN, 4)} / ${fmt(D.R_E, 4)} mm / ${fmt(D.phi_E, 3)}°</span>
          <span>Brazo mín / máx / efectivo mín</span><span>${fmt(D.brazo_min, 4)} / ${fmt(D.brazo_max, 4)} / ${fmt(D.brazo_ef_min, 4)} mm</span>
          <span>Carrera requerida</span><span>${fmt(D.carrera_req, 4)} de ${fmt(P.stroke, 4)} mm</span>
          <span>Largo Q–pasador (bloque-uña)</span><span>${fmt(D.L_qp, 4)} mm</span>
          <span>θ del pasador tomado: inicio / fin</span><span>${fmt(D.theta_ini_deg, 4)}° / ${fmt(D.theta_fin_deg, 4)}°</span>
          <span>Holgura al pasador siguiente / cuerpo–mesa</span><span>${fmt(D.holgura_pasador_siguiente, 3)} / ${fmt(D.holgura_cuerpo_mesa, 3)} mm</span>
          <span>Ciclos por vuelta</span><span>${P.N_pin}</span>
        </div>`; })() : `<div class="kv" style="margin-top:10px">
          <span>Brazo mín (R·cos π/N) / máx</span><span>${fmt(A.R.K.armMin, 4)} / ${fmt(A.R.K.armMax, 4)} mm</span>
          <span>Carrera requerida (libre + cuerda)</span><span>${fmt(A.R.K.s_req, 4)} de ${fmt(P.stroke, 4)} mm</span>
          <span>Δ guía–pasador / Lg / factor K</span><span>${fmt(A.R.K.DeltaMax, 3)} / ${fmt(A.R.K.Lg, 3)} mm / ${fmt(A.R.Kguide)}</span>
          <span>Reacción de guía (calado)</span><span>${fmt(A.R.Rguide)} kN</span>
          <span>Voladizo de la uña / holgura radial</span><span>${fmt(A.R.K.lever, 3)} / ${fmt(A.R.K.radial)} mm</span>
          <span>Cuerda / hueco entre pasadores</span><span>${fmt(A.R.K.chord, 4)} / ${fmt(A.R.K.gap, 4)} mm</span>
          <span>Ciclos por vuelta</span><span>${P.N_pin}</span>
        </div>`}</div></div>${isPiv() ? lzSlot(placaGuiaCard) : ""}`;   // la placa-guía (3 vistas con la simulación) se dibuja en una tarea aparte
  }
  // placa-guía curva del modo pivotado: detalle en toma, empuje y retorno (simulación, TT.pivotAt) y tabla de los segmentos del canto (núcleo)
  function placaGuiaCard() {
    const g = TT.pivotGeo(P); if (!g || typeof SIM === "undefined") return "";
    const D = TT.designDrive(P, A.R).pivotado || {}, pl = D.placa_leva || {}, seg = g.placas["1_antihorario"].segmentos_canto || [];
    const fases = [["toma", "Toma: Q en la toma y la " + SIM.garraTxt(g) + " llega al pasador"], ["empuje", "Empuje: Q apoyado en el canto (contacto Q–canto)"], ["retorno", "Retorno: el bloque-uña sale sobre el pasador siguiente y la placa lo conduce a la toma"]];
    return `<div class="card" style="margin-top:12px" id="mdlPlaca"><h3>Placa-guía curva (cilindro 1, giro antihorario) · toma → empuje → retorno</h3>
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">${fases.map(([id, t]) => `<div><div class="note"><b>${esc(t)}</b></div>${SIM.vistaFase(P, A, id)}</div>`).join("")}</div>
      <div class="note">Canto (naranja) y trayectoria del centro de Q (trazos) dibujados con arcos SVG desde <code>pivotGeo().placas[k].segmentos_*</code>; las placas del giro horario son la imagen especular (ACC-024). ${g.bloque.garra ? `Bloque-uña con ${esc(SIM.garraTxt(g))} dibujado con arcos SVG desde <code>pivotGeo().bloque.garra.contorno</code> (labio ${fmt(g.bloque.garra.labio.saliente_sobre_centro)} × ${fmt(g.bloque.garra.labio.espesor)}, nariz R${fmt(g.bloque.garra.nariz.radio)}, rampa ${fmt(g.bloque.garra.rampa.angulo_deg)}°, abrazo ${fmt(g.bloque.garra.asiento.abrazo_total_deg)}°); en el empuje el pasador tomado queda asentado y el punto rojo es el contacto del asiento (<code>pivotAt().asiento</code>)` : `Bloque-uña con cara cilíndrica R${fmt(g.bloque.R_cara)}`}, pasador Q Ø${fmt(g.pasadorQ.d)}, ojal E Ø${fmt(g.ojalE.d)} en su soporte abierto y pasador tomado en naranja.</div>
      <div class="scroll"><table id="mdlSeg"><tr><th>#</th><th>Rol</th><th>Tipo</th><th>Sentido</th><th>Curvatura</th><th class="n">R canto (mm)</th><th class="n">Centro (mm)</th><th class="n">Inicio (mm)</th><th class="n">Fin (mm)</th></tr>
        ${seg.map((q, i) => `<tr><td class="n">${i + 1}</td><td>${esc(q.rol)}</td><td>${q.tipo === "arco" ? "arco" : "recta"}</td><td>${esc(q.sentido || "—")}</td><td>${esc(q.curvatura || "—")}</td><td class="n">${q.radio ? fmt(q.radio, 3) : "—"}</td><td class="n">${q.centro ? fmt(q.centro[0], 5) + "; " + fmt(q.centro[1], 5) : "—"}</td><td class="n">${fmt(q.p0[0], 5)}; ${fmt(q.p0[1], 5)}</td><td class="n">${fmt(q.p1[0], 5)}; ${fmt(q.p1[1], 5)}</td></tr>`).join("")}</table></div>
      <div class="kv" style="margin-top:8px"><span>Radio mínimo del canto convexo / cóncavo</span><span>${fmt((pl.radio_min_canto || {}).convexo, 3)} / ${fmt((pl.radio_min_canto || {}).concavo, 3)} mm</span>
        <span>Continuidad G1 (quiebre máximo de tangente)</span><span>${fmt((pl.g1_max_rad || 0) / D2R, 3)}°</span>
        <span>Largo del canto / área de la placa</span><span>${fmt(pl.largo_canto, 4)} mm / ${fmt(pl.area / 100, 4)} cm²</span>
        <span>Ángulo del flanco de reenganche</span><span>${fmt(pl.alpha_deg, 3)}° (máx. admisible ${fmt(P.pv_alpha, 3)}°)</span></div></div>`;
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
    const CN = lz("CN"); if (!CN) return lzErr("CN");
    return `<table><tr><th class="n">Cilindros</th><th class="n">W máx. giro (FS ≥ ${fmt(P.FS_min)}, μ diseño)</th><th class="n">W máx. por pivote</th><th class="n">Capacidad adoptada</th><th class="n">W que gira (FS = 1, μ nominal)</th></tr>
      ${CN.map((c) => `<tr${c.n === P.n_cyl ? ' class="grp"' : ""}><td class="n">${c.n}</td><td class="n">${fmt(c.wGiro, 3)} tf</td><td class="n">${fmt(c.wPiv, 3)} tf</td><td class="n"><b>${fmt(c.wCap, 3)} tf</b></td><td class="n">${fmt(c.wNom, 3)} tf</td></tr>`).join("")}</table>
      <div class="note">Con un solo cilindro el empuje no es un par puro: el pivote reacciona con la fuerza tangencial del pasador y limita la capacidad (como en el modo de un cilindro de los equipos comerciales). La capacidad estructural de la cadena de empuje se verifica con la carga indicada en «Carga».</div>`;
  }
  function marketTable() {
    const MK = lz("MK"); if (!MK) return lzErr("MK");
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
      if (isPiv()) {                                                  // modo pivotado: F_cil del núcleo (driveAt) en el θ que entrega pivotAt para cada extensión
        const pts = [];
        for (let i = 0; i <= 60; i++) { const s = P.s_free + (K.s_req - P.s_free) * i / 60, q = TT.pivotAt(P, s, "empuje", "antihorario"); if (q && q.arm != null) pts.push([s, TT.driveAt(P, q.th_cil1_antihorario, id).F]); }
        return { n, c, pts };
      }
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
        <h3 style="margin-top:14px">Capacidad según el número de cilindros</h3>${lzSlot(cylCapTable, ["CN"])}
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

  /* ---------- Cinemática del modo pivotado (drive_mode = 2): datos de TT.designDrive().pivotado y del núcleo (sin recalcular) ---------- */
  // gráfico compacto: series [{pts:[[x,y]], c, n, dash}], marcas verticales [{v, t, c}], líneas horizontales [{v, t, c}], eje derecho opcional (k·y)
  function kinChart(o) {
    const Wd = 440, Hd = 230, m = { l: 52, r: o.y2 ? 46 : 14, t: 14, b: 34 };
    const xs = o.series.flatMap((s) => s.pts.map((q) => q[0])), ys = o.series.flatMap((s) => s.pts.map((q) => q[1])).concat((o.hl || []).map((h) => h.v));
    const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(0, ...ys), y1 = Math.max(...ys) * 1.1 || 1;
    const X = (v) => (m.l + (v - x0) / (x1 - x0 || 1) * (Wd - m.l - m.r)).toFixed(1), Y = (v) => (Hd - m.b - (v - y0) / (y1 - y0 || 1) * (Hd - m.t - m.b)).toFixed(1);
    const g = [];
    for (let i = 0; i <= 4; i++) { const v = y0 + (y1 - y0) * i / 4; g.push(`<line x1="${m.l}" x2="${Wd - m.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text x="${m.l - 5}" y="${+Y(v) + 4}" font-size="10.5" text-anchor="end">${fmt(v, 3)}</text>${o.y2 ? `<text x="${Wd - m.r + 5}" y="${+Y(v) + 4}" font-size="10.5" fill="var(--load)">${fmt(v * o.y2.k, 3)}</text>` : ""}`); }
    for (let i = 0; i <= 4; i++) { const v = x0 + (x1 - x0) * i / 4; g.push(`<text x="${X(v)}" y="${Hd - m.b + 14}" font-size="10.5" text-anchor="middle">${fmt(v, 4)}</text>`); }
    (o.hl || []).forEach((h) => g.push(`<line x1="${m.l}" x2="${Wd - m.r}" y1="${Y(h.v)}" y2="${Y(h.v)}" stroke="${h.c}" stroke-dasharray="5 4" stroke-width="1.2"/><text x="${Wd - m.r - 18}" y="${+Y(h.v) - 4}" font-size="10" text-anchor="end" fill="${h.c}">${esc(h.t)}</text>`));
    (o.marks || []).forEach((h) => { const xm = +X(h.v), xt = xm > Wd - m.r - 12 ? xm - 4 : xm + 11; g.push(`<line x1="${xm}" x2="${xm}" y1="${m.t}" y2="${Hd - m.b}" stroke="${h.c}" stroke-dasharray="3 3" stroke-width="1.1" class="kin-mark"/><text x="${xt}" y="${m.t + 3}" font-size="10" fill="${h.c}" text-anchor="end" transform="rotate(-90 ${xt} ${m.t + 3})">${esc(h.t)}</text>`); });
    o.series.forEach((s) => g.push(`<polyline fill="none" stroke="${s.c}" stroke-width="${s.w || 1.8}"${s.dash ? ` stroke-dasharray="${s.dash}"` : ""} points="${s.pts.map((q) => X(q[0]) + "," + Y(q[1])).join(" ")}"/>`));
    g.push(`<line x1="${m.l}" x2="${m.l}" y1="${m.t}" y2="${Hd - m.b}" stroke="var(--ink2)"/><line x1="${m.l}" x2="${Wd - m.r}" y1="${Hd - m.b}" y2="${Hd - m.b}" stroke="var(--ink2)"/>`);
    g.push(`<text x="${(m.l + Wd - m.r) / 2}" y="${Hd - 4}" font-size="11" text-anchor="middle">${esc(o.xl)}</text><text x="11" y="${(m.t + Hd - m.b) / 2}" font-size="11" text-anchor="middle" transform="rotate(-90 11 ${(m.t + Hd - m.b) / 2})">${esc(o.yl)}</text>`);
    if (o.y2) g.push(`<text x="${Wd - 8}" y="${(m.t + Hd - m.b) / 2}" font-size="11" text-anchor="middle" fill="var(--load)" transform="rotate(90 ${Wd - 8} ${(m.t + Hd - m.b) / 2})">${esc(o.y2.lab)}</text>`);
    const leg = o.series.filter((s) => s.n).map((s) => `<span style="display:inline-flex;align-items:center;gap:5px;margin-right:12px"><i style="width:16px;height:0;border-top:2px ${s.dash ? "dashed" : "solid"} ${s.c};display:inline-block"></i>${esc(s.n)}</span>`).join("");
    return `<div class="card kin-card" data-k="${o.id}"><h3>${esc(o.title)}</h3><svg viewBox="0 0 ${Wd} ${Hd}" role="img" aria-label="${esc(o.title)}">${g.join("")}</svg>${leg ? `<div class="note">${leg}</div>` : ""}</div>`;
  }
  function renderCinem() {
    const el = document.querySelector('section[data-t="cinem"]'); if (!el) return;
    if (!A) { el.innerHTML = msgs(); return; }
    if (!isPiv()) { el.innerHTML = `<div class="msg warn" id="kinNo">La cinemática de esta pestaña es la del accionamiento pivotado tipo KIET (drive_mode = 2). Con el modo guiado (drive_mode = 1) la fuerza a lo largo de la carrera está en «Accionamiento».</div>`; return; }
    const D = TT.designDrive(P, A.R).pivotado || {}, cin = D.cinematica || [], pl = D.placa_leva || {}, R = A.R;
    if (!cin.length) { el.innerHTML = `<div class="msg warn">El núcleo no entrega la cinemática del empuje guiado (designDrive().pivotado.cinematica).</div>`; return; }
    const push = (R.camP && R.camP.push || []).filter((q) => q.ok), hb = push.length === cin.length ? push.map((q) => q.clrB) : null;
    const iCal = cin.reduce((b, c, i) => c.F_cil > cin[b].F_cil ? i : b, 0), thHz = pl.hertz && pl.hertz.push ? pl.hertz.push.th / D2R : null;
    const near = (th) => cin.reduce((b, c, i) => Math.abs(((c.th - th) % 360 + 540) % 360 - 180) < Math.abs(((cin[b].th - th) % 360 + 540) % 360 - 180) ? i : b, 0);
    const iHz = thHz != null ? near(thHz) : null, iHb = hb ? hb.reduce((b, v, i) => v < hb[b] ? i : b, 0) : null, iFin = cin.length - 1;
    const tc = cin.map((c) => c.th), mk = [{ v: cin[0].th, t: "toma", c: "var(--ok)" }, { v: cin[iCal].th, t: "calado (F_cil máx.)", c: "var(--fail)" }, { v: cin[iFin].th, t: "fin del empuje", c: "var(--acc)" }];
    const xl = "θ del pasador tomado (°)", ser = (k, c, n, dash) => ({ pts: cin.map((q) => [q.th, q[k]]), c, n, dash });
    const kp = cin[0].F_cil ? cin[0].p / cin[0].F_cil : 0;
    const chP = A.checks.find((c) => /ángulo de presión máximo bajo el de autobloqueo/.test(c.name)), chB = A.checks.find((c) => /Bloque-uña libre de los pasadores en el empuje guiado/.test(c.name));
    const ret = pl.retorno || [], rg = [];                            // tramos contiguos con Q conducido por la placa-guía
    ret.forEach((q, i) => { if (!q.guia) return; if (!i || !ret[i - 1].guia) rg.push([]); rg[rg.length - 1].push([q.L, q.holgura]); });
    const charts = [
      kinChart({ id: "L", title: "Largo del cilindro L = |Q − E|", xl, yl: "L (mm)", series: [ser("L", "var(--acc)", "L del cilindro (Q apoyado en el canto)")], marks: mk, hl: [{ v: P.L0 + P.stroke, t: `L máx. ${fmt(P.L0 + P.stroke, 4)} mm`, c: "var(--ink2)" }] }),
      kinChart({ id: "F", title: "Fuerza del cilindro y presión (caso de diseño)", xl, yl: "F_cil (kN)", y2: { k: kp, lab: "p (bar)" }, series: [ser("F_cil", "var(--acc)", "F_cil, empuje guiado"), ser("F_cil_colineal", "var(--ink2)", "F_cil colineal (referencia)", "5 4")], marks: mk, hl: [{ v: R.Fstall, t: `alivio ${fmt(R.Fstall)} kN (${fmt(P.p_relief)} bar)`, c: "var(--fail)" }] }),
      kinChart({ id: "H", title: "Carga H sobre la placa-guía (caso de diseño)", xl, yl: "H (kN)", series: [ser("F_leva", "var(--load)", "H en el contacto Q–canto")], marks: mk }),
      kinChart({ id: "phi", title: "Ángulo de presión φ en el contacto Q–canto (empuje)", xl, yl: "φ (°)", series: [ser("phi_presion_deg", "#7b3fa0", "φ empuje")], marks: mk, hl: chP ? [{ v: chP.cap, t: `autobloqueo 90° − atan μ = ${fmt(chP.cap, 3)}°`, c: "var(--fail)" }] : [] }),
      hb ? kinChart({ id: "hb", title: "Holgura bloque-uña–pasadores en el empuje guiado", xl, yl: "holgura (mm)", series: [{ pts: cin.map((q, i) => [q.th, hb[i]]), c: "var(--ok)", n: "holgura mínima a los pasadores anterior y siguiente" }], marks: mk, hl: [{ v: P.pv_cB, t: `mínimo ${fmt(P.pv_cB)} mm`, c: "var(--fail)" }] }) : `<div class="card"><div class="msg warn">El núcleo no entrega la holgura bloque–pasadores por posición.</div></div>`,
      ret.length ? kinChart({ id: "sync", title: "Holgura de sincronía en el retorno (mesa detenida en θ_fin)", xl: "L del cilindro en el retorno (mm)", yl: "holgura (mm)", series: [{ pts: ret.map((q) => [q.L, q.holgura]), c: "var(--ink2)", n: "retorno: el pasador siguiente levanta el bloque (0 = deslizamiento previsto)", w: 1.2 }, ...rg.map((pts, k) => ({ pts, c: "var(--ok)", n: k ? "" : "conducción por la placa-guía (sincronía)", w: 2.4 }))], hl: [{ v: pl.margen_diseno, t: `margen con tolerancias ${fmt(pl.margen_diseno, 3)} mm`, c: "var(--fail)" }], marks: [{ v: pl.primer_contacto ? pl.primer_contacto.L : P.L0, t: "primer contacto del retorno", c: "var(--acc)" }] }) : "",
    ];
    // puntos característicos: toma, calado (F_cil máx.), cambios de tramo del canto (push[].tramo ↔ segmentos_canto) y fin del empuje
    const segC = (TT.pivotGeo(P) || { placas: {} }).placas["1_antihorario"], rolT = (i) => push[i] && segC && segC.segmentos_canto[push[i].tramo] ? segC.segmentos_canto[push[i].tramo].rol : null;
    const trans = push.length === cin.length ? push.map((q, i) => i).filter((i) => i > 0 && push[i].tramo !== push[i - 1].tramo && i !== iCal && i !== iFin) : [];
    const sel = [0, iCal, iFin]; trans.forEach((i) => { if (sel.length < 5 && !sel.includes(i)) sel.push(i); });
    const pts5 = [...new Set(sel)].sort((a, b) => a - b).map((i) => { const tg = []; if (i === 0) tg.push("Toma"); if (i === iCal) tg.push("Calado (F_cil máx.)"); if (i === iFin) tg.push("Fin del empuje"); if (i === iHz) tg.push("Hertz crítico del canto"); if (i === iHb) tg.push("holgura bloque–pasadores mín."); if (!tg.length) tg.push("Cambio de tramo del canto"); return [tg.join(" · ") + (rolT(i) ? ` — Q en «${rolT(i)}»` : ""), i]; });
    const tabla = `<table id="kinPts"><tr><th>Punto</th><th class="n">θ (°)</th><th class="n">L (mm)</th><th class="n">s (mm)</th><th class="n">F_cil (kN)</th><th class="n">p (bar)</th><th class="n">H guía (kN)</th><th class="n">φ (°)</th><th class="n">Holgura bloque–pasadores (mm)</th><th class="n">Brazo ef. (mm)</th></tr>
      ${pts5.map(([n, i]) => { const c = i != null ? cin[i] : null; return `<tr data-i="${i == null ? "" : i}"><td>${esc(n)}</td>${c ? `<td class="n">${fmt(c.th, 5)}</td><td class="n">${fmt(c.L, 4)}</td><td class="n">${fmt(c.s, 4)}</td><td class="n">${fmt(c.F_cil, 4)}</td><td class="n">${fmt(c.p, 3)}</td><td class="n">${fmt(c.F_leva, 3)}</td><td class="n">${fmt(c.phi_presion_deg, 3)}</td><td class="n">${hb ? fmt(hb[i], 3) : "—"}</td><td class="n">${fmt(c.a_ef, 4)}</td>` : `<td colspan="9" class="ref">sin dato del núcleo</td>`}</tr>`; }).join("")}</table>`;
    el.innerHTML = `<div class="note">Accionamiento pivotado tipo KIET (drive_mode = 2), cilindro 1, giro antihorario, caso de diseño (μ ${fmt(R.mu.d)}). Datos: <code>TT.designDrive().pivotado.cinematica</code> (${cin.length} posiciones del empuje guiado con Q apoyado en el canto), <code>placa_leva.retorno</code> y la holgura bloque–pasadores de <code>analyze().R.camP.push[].clrB</code>; la UI no recalcula.</div>
      <div class="grid kin-grid" id="kinGrid" style="grid-template-columns:repeat(auto-fit,minmax(360px,1fr))">${charts.join("")}</div>
      <div class="card" style="margin-top:12px"><h3>Puntos característicos del empuje (${pts5.length})</h3><div class="scroll">${tabla}</div>
        <div class="kv" style="margin-top:8px"><span>θ toma / fin del empuje</span><span>${fmt(D.theta_ini_deg, 5)}° / ${fmt(D.theta_fin_deg, 5)}°</span>
          <span>Carrera requerida / del cilindro</span><span>${fmt(D.carrera_req, 4)} / ${fmt(P.stroke, 4)} mm</span>
          <span>Sincronía nominal / peor caso (retorno)</span><span>${fmt(pl.sincronia, 3)} / ${fmt(pl.sincronia_peor, 3)} mm (margen ${fmt(pl.margen_diseno, 3)} mm)</span>
          <span>Primer contacto del retorno: L / φ</span><span>${pl.primer_contacto ? fmt(pl.primer_contacto.L, 4) + " mm / " + fmt(pl.primer_contacto.phi, 3) + "°" : "—"}</span>
          <span>Bolsillo (máx W) / ángulo del flanco</span><span>${fmt(pl.bolsillo_w, 3)} mm / ${fmt(pl.alpha_deg, 3)}°</span>
          ${chB ? `<span>Holgura bloque–pasadores mínima (verificación)</span><span>${fmt(chB.cap, 3)} mm ≥ ${fmt(chB.dem, 3)} mm · FU ${fu3(chB.fu)}</span>` : ""}</div>
        <div class="note">Calado: posición de fuerza máxima del cilindro en el empuje (la primera en calar si la fricción sube). Hertz crítico: peor punto de contacto Q–canto a la fuerza de calado (placa_leva.hertz.push). La holgura de sincronía se grafica frente a L porque en el retorno la mesa queda detenida en θ_fin.</div></div>`;
  }

  /* ---------- Comparación de la guía: original poligonal (b928552, histórico fijo) / curva (núcleo) / concepto KIET (medido en el plano) ---------- */
  const ORIG = { ref: "commit b928552 · docs/qa/guia_curva_KIET/cambios.md §1, §2 y §4 (valores históricos fijos)" };
  function renderComp() {
    const el = document.querySelector('section[data-t="comp"]'); if (!el) return;
    if (!A) { el.innerHTML = msgs(); return; }
    const img = typeof TT_IMG !== "undefined" && TT_IMG.comparacion ? `<img id="compImg" src="${TT_IMG.comparacion}" alt="Comparación de la placa-guía: original poligonal, curva y concepto KIET" style="display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px;background:#fff">` : `<div class="msg warn">Figura no embebida en esta compilación.</div>`;
    const piv = isPiv();
    if (!piv && !("CMP" in LZ)) {                                     // modo guiado: el análisis con drive_mode = 2 (BX completo) corre en el worker
      el.innerHTML = `<div class="note" id="compCalc">Calculando la guía curva con drive_mode = 2 en segundo plano…</div>`;
      const g = RGEN; lzGet("CMP").then(() => { if (g === RGEN && cur === "comp") renderComp(); }); return;
    }
    if (!piv && !LZ.CMP) { el.innerHTML = lzErr("CMP"); return; }
    if (!piv && !LZ.CMP._rh) { try { rehydrate(LZ.CMP.R, TTcore.compute(LZ.CMP.Pc)); } catch (e) { } LZ.CMP._rh = true; }
    const Ap = piv ? A : LZ.CMP, Pp = piv ? P : Ap.Pc;
    const D = TT.designDrive(Pp, Ap.R).pivotado || {}, pl = D.placa_leva || {}, g = TT.pivotGeo(Pp) || {}, dis = Ap.R.cases.find((c) => c.id === "dis") || {};
    const seg = g.placas ? g.placas["1_antihorario"].segmentos_canto : [], nA = seg.filter((q) => q.tipo === "arco").length, nL = seg.filter((q) => q.tipo !== "arco").length;
    const chk = (re) => Ap.checks.find((c) => re.test(c.name)), fab = (D.fabricacion || {}).placas_leva || {}, marco = fab.marco || {};
    const qF = chk(/^BX · Pasador Q: flexión \(horquilla/) || chk(/^Pasador Q: flexión/);   // rev. 9: la fila BX con la H del μ bajo sustituye a la del núcleo
    const rows = [
      ["Perfil del canto", "poligonal: 4 vértices, quiebre de tangente máx. 70,2°", `${nL} rectas + ${nA} arcos tangentes (${seg.filter((q) => q.tipo === "arco" && !/sin contacto/.test(q.rol)).length} de contacto y el cierre del bolsillo), G1: quiebre máx. ${fmt((pl.g1_max_rad || 0) / D2R, 3)}°`, "media luna con arco continuo y gancho en un extremo"],
      ["Radio mínimo del canto convexo / cóncavo", "0 (vértices)", `${fmt((pl.radio_min_canto || {}).convexo, 3)} / ${fmt((pl.radio_min_canto || {}).concavo, 3)} mm`, "no acotado"],
      ["Ángulo de presión del flanco de reenganche", "65° (vértices sin definir)", `${fmt(pl.alpha_deg, 3)}° (máximo, en el pie del flanco)`, "no acotado"],
      ["Canto exportado", "desplazamiento en w (invade el seguidor 27,1 mm)", `envolvente exacta del seguidor (polilínea con flecha ≤ ${fmt(pl.tolerancia_polilinea, 1)} mm)`, "—"],
      ["Sincronía nominal (declarada)", "7,07 mm", `${fmt(pl.sincronia, 3)} mm (margen ${fmt(pl.margen_diseno, 3)} con tolerancias)`, "—"],
      ["Sincronía con el contorno fabricado", "−21,0 mm (choque con B)", `${fmt(pl.sincronia, 3)} mm (peor caso ${fmt(pl.sincronia_peor, 3)})`, "—"],
      ["Bolsillo (máx. W)", "57,9 mm", `${fmt(pl.bolsillo_w, 3)} mm`, "—"],
      ["Carga de diseño de la placa", "71,6 kN (atasco)", `${fmt((pl.fuerzas_N || {}).diseno / 1e3, 4)} kN (empuje a calado)`, "—"],
      ["F del cilindro, caso de diseño", "308,1 kN", `${fmt(dis.F, 4)} kN`, "—"],
      ["Presión de diseño", "484 bar", `${fmt(dis.p, 3)} bar`, "—"],
      ["FS del accionamiento (diseño)", "1,446", fmt(dis.FS, 4), "—"],
      ["Carrera requerida", "220,41 mm", `${fmt(D.carrera_req, 5)} mm`, "—"],
      ["Placa", "labio de 80 mm, 6 pernos M20", `rectángulo ${fmt(marco.largo, 3)} × ${fmt(marco.ancho, 3)} × ${fmt(pl.t)} mm, ${pl.n_pernos} ISO 10642 M${Math.round(pl.d_perno)} 8.8 + 2 pasadores de posición`, "rectangular, ~6 pernos en el perímetro"],
      ["Material", "S355J2 «con canto templado ≥ 55 HRC»", esc(String(fab.material || "—").split(",")[0].replace(/ de respaldo.*$/, "")) + ", canto desnudo y engrasado (buje templado del seguidor; rev. 9)", "no indicado"],
      ["Masa de las 4 placas", "34,4 kg", `${fmt(Ap.R.m.cam, 3)} kg`, "—"],
      ["Pasador Q: FU de flexión", "0,551", qF ? fu3(qF.fu) : "—", "—"],
      ["Disposición", "2 cilindros en esquinas opuestas, 2 placas por cilindro", `ojales a ${fmt(D.phi_E, 3)}° y ${fmt(((D.phi_E || 0) + 180) % 360, 3)}°; 2 placas por cilindro (una por sentido; la del horario es la imagen especular, ACC-024)`, "ojales a 134,9° y 315,1°; 2 placas por cilindro"],
      ["Posición angular de las placas respecto de la diagonal del ojal", "—", "± 20,9°", "−26,0° y +25,1° (cil. 1); +26,3° y −26,1° (cil. 2)"],
      ["Radio del centro de la placa / radio del anillo", "—", "1,18 (sobre R = D/2)", "1,02–1,08"],
    ];
    el.innerHTML = `<div class="note">Valores por defecto, cilindro 1, giro antihorario${piv ? "" : " (calculado con drive_mode = 2: la guía curva es del accionamiento pivotado)"}. Original: ${esc(ORIG.ref)}. Curva: núcleo actual (<code>designDrive().pivotado</code>, <code>pivotGeo()</code>, <code>analyze()</code>). KIET: plano KIET-1024-REF-TT-400T, <b>concepto medido en el plano, no acotado</b> (solo proporciones; sus dimensiones no se trasladan).</div>
      <div class="card scroll"><table id="compTab"><tr><th>Aspecto</th><th>Original poligonal (b928552)</th><th>Curva (este diseño, núcleo)</th><th>Concepto KIET (medido en el plano, no acotado)</th></tr>
        ${rows.map(([a, o, c, k]) => `<tr><td>${esc(a)}</td><td class="ref">${esc(o)}</td><td><b>${c}</b></td><td class="ref">${esc(k)}</td></tr>`).join("")}</table></div>
      <div class="card" style="margin-top:12px"><h3>Figura: original poligonal, curva y concepto KIET</h3>${img}<div class="note">docs/qa/guia_curva_KIET/comparacion.png (tools/fig_guia_curva.py), embebida en la herramienta.</div></div>`;
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
    A.checks.forEach((c, i) => {
      if (c.grp !== g) { g = c.grp; rows += `<tr class="grp"><td colspan="7">${esc(g)}</td></tr>`; }
      rows += `<tr class="chk-row" data-i="${i}" data-st="${c.st}"><td><span class="st st-${c.st}">${ST[c.st]}</span></td><td>${esc(c.name)}<div class="form">${esc(c.formula)}</div></td>
        <td class="n">${fmt(c.dem)}</td><td class="n">${c.cap != null ? fmt(c.cap) : ""}</td><td>${esc(c.unit || "")}</td>
        <td class="n">${fu3(c.fu)}${fuBar(c)}</td><td class="ref">${esc(c.ref)}</td></tr>`;
    });
    el.innerHTML = `<div class="note">Clasificación: FU ≤ 0,90 cumple; 0,90–1,00 monitoreo; &gt; 1,00 no cumple. Los chequeos de giro y geométricos son límites con margen propio: cumplen con FU ≤ 1,00. Cadena de empuje verificada a la fuerza de calado ${fmt(A.R.Fstall)} kN con ASME BTH-1 Nd = ${fmt(P.Nd)}.</div>
      <div class="card scroll"><table><tr><th>Estado</th><th>Verificación</th><th class="n">Demanda</th><th class="n">Capacidad</th><th>Unidad</th><th class="n">FU</th><th>Norma / referencia</th></tr>${rows}</table></div>`;
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

  /* ---------- Disco y pastillas (TT300-BX): todo de A.bx (BX.design) y de las filas «BX ·» ---------- */
  function bxPlanSVG(D) {
    const d = D.disco, po = D.portador, pa = D.pastillas, tw = d.tornillos, Ro = d.R_ext, S = Ro + 60, y = (v) => -v, o = [];
    o.push(`<circle r="${Ro}" fill="var(--soft)" stroke="var(--ink)" stroke-width="4"/><circle r="${d.R_int}" fill="var(--panel)" stroke="var(--ink)" stroke-width="3"/>`);
    o.push(`<circle r="${po.R_ext}" fill="none" stroke="var(--steel)" stroke-width="3" stroke-dasharray="16 10"/><circle r="${po.R_int}" fill="none" stroke="var(--steel)" stroke-width="3" stroke-dasharray="16 10"/>`);
    const sq = pkSq(pa), hw = pkW(pa) / 2, rc = sq ? (pa.r_esquina || 0) : 0;
    pa.lista.forEach((q) => { const st = q.p >= pa.p_max - 1e-9 ? ' stroke="var(--fail)" stroke-width="5"' : ' stroke="var(--insk)" stroke-width="2"';
      const rot = q.ang != null ? q.ang : q.rot != null ? q.rot : Math.atan2(q.y, q.x) / D2R;   // cuadrada: orientación del módulo si la entrega; si no, radial
      o.push(sq ? `<rect class="bxPuck" x="${-hw}" y="${-hw}" width="${2 * hw}" height="${2 * hw}" rx="${rc}" transform="translate(${q.x} ${y(q.y)}) rotate(${-rot})" fill="var(--warnbg)"${st}/>` : `<circle class="bxPuck" cx="${q.x}" cy="${y(q.y)}" r="${hw}" fill="var(--warnbg)"${st}/>`); });
    (po.tapones.posiciones || []).forEach(([a, b]) => o.push(`<circle class="bxPlug" cx="${a}" cy="${y(b)}" r="${po.tapones.d / 2}" fill="var(--steel)" opacity=".6"/>`));
    tw.lista.forEach((b) => o.push(`<circle class="bxBolt" cx="${b.x}" cy="${y(b.y)}" r="${Math.max(6, tw.d_cabeza / 2)}" fill="var(--acc)"/>`));
    ((d.tapones || {}).lista || []).forEach((q) => { const qx = Array.isArray(q) ? q[0] : q.x, qy = Array.isArray(q) ? q[1] : q.y; o.push(`<circle class="bxLamPlug" cx="${qx}" cy="${y(qy)}" r="${Math.max(8, (d.tapones.d || 14) / 2)}" fill="var(--acc)"/>`); });
    o.push(`<line x1="${-Ro}" y1="0" x2="${-d.R_int}" y2="0" stroke="var(--load)" stroke-width="5"/><line x1="${d.R_int}" y1="0" x2="${Ro}" y2="0" stroke="var(--load)" stroke-width="5"/>`);
    o.push(`<text x="0" y="${-Ro - 18}" text-anchor="middle" font-size="44">Disco Ø${fmt(2 * Ro, 4)} × ${fmt(d.t)} · ${pa.n} pastillas ${pkTxt(pa)} · ${d.modo === 1 ? (d.tapones ? d.tapones.n + " tapones Ø" + fmt(d.tapones.d) + " (lámina soldada)" : "lámina soldada") : tw.n + " tornillos M" + fmt(tw.d)}</text>`);
    return `<svg viewBox="${-S} ${-S - 20} ${2 * S} ${2 * S + 40}" role="img" aria-label="Planta del disco BX" id="bxPlan">${o.join("")}</svg>
      <div class="note"><span style="color:var(--warn)">●</span> pastillas (borde rojo: la más cargada) · <span style="color:var(--acc)">●</span> ${d.modo === 1 ? "tapones de soldadura lámina–mesa" : "tornillos avellanados disco–mesa"} · <span style="color:var(--load)">━</span> ${d.modo === 1 ? "junta a tope CJP entre paneles" : "CJP entre semidiscos"} (eje x) · trazos: bordes del portador${po.tapones.n ? " · gris: agujeros de soldadura" : ""}.</div>`;
  }
  function bxLaminaCard(d, kv) {
    const L = d.lamina || {}, T = d.tapones || {}, C = d.costura || {}, J = L.junta || {};
    return `<div class="card" id="bxDisco"><h3>Lámina inoxidable ${fmt(d.t)} mm soldada a la mesa</h3>${kv([["Material", esc(d.material)], ["Espesor adoptado / requerido", `<b>${fmt(d.t)}</b> / ${fmt(d.t_req, 3)} mm`],
      ["Paneles / formato de plancha", `${L.n_paneles} paneles de ${(L.paneles || [])[0] ? fmt(L.paneles[0].ancho, 4) + " × " + fmt(L.paneles[0].largo, 4) : "—"} mm / ${(L.formato || []).join(" × ")} mm`],
      ["R exterior / interior", `${fmt(d.R_ext, 4)} / ${fmt(d.R_int, 4)} mm`], ["Fy / Fu / α", `${fmt(d.Fy, 3)} / ${fmt(d.Fu, 3)} MPa / ${fmt(d.alfa * 1e6, 3)}×10⁻⁶/K`], ["Masa", `${fmt(d.masa, 4)} kg`],
      ["Junta entre paneles", esc(String(J.tipo || "").split(";")[0]) + (J.aporte ? " · " + esc(J.aporte) : "")]])}</div>
      <div class="card" id="bxTorn" style="margin-top:12px"><h3>Tapones y costuras (sin tornillos)</h3>${kv([["Tapones", `<b>${T.n}</b> × Ø${fmt(T.d)} mm, relleno ${fmt(T.relleno)} mm, paso ≈ ${fmt(T.paso, 3)} mm`],
      ["Anillos (R)", (T.anillos || []).map((a) => fmt(a.r, 4) + " (" + a.n + ")").join(" · ") + " mm"], ["Norma", esc(T.norma || "")],
      ["Costura perimetral", esc(C.tipo || "") + (C.exterior ? ` · ext. R${fmt(C.exterior.R, 4)}, int. R${fmt((C.interior || {}).R, 4)}` : "")]])}
      <div class="note">${esc(typeof d.fabricacion === "string" ? d.fabricacion : "")}</div></div></div>`;
  }
  // rev. 7d: cilindro hidráulico fabricado (A.bx.cilindro = bloque bx.cilindro del JSON de diseño): piezas, sellos y filas del grupo «Cilindro»
  function cylCard(Cy) {
    if (!Cy) return "";
    const rows = A.checks.filter((c) => c.grp === "Cilindro"), gv = rows.filter((c) => c.kind === "fu" && isFinite(c.fu)).reduce((m, c) => (!m || c.fu > m.fu ? c : m), null);
    const pz = [["Camisa (ACC-028)", `Ø${fmt(Cy.camisa.D, 3)} ${esc(Cy.camisa.tol_D)} × Ø${fmt(Cy.camisa.d, 2)} ${esc(Cy.camisa.tol_d)} × ${fmt(Cy.camisa.largo, 3)}; rosca ${esc(Cy.camisa.rosca.designacion)}; puertos A y B ${esc(Cy.camisa.puerto_B.rosca)}`, esc(Cy.camisa.material)],
      ["Fondo macizo (ACC-029)", `bloque ${fmt(Cy.fondo.t, 2)} = pestaña ${fmt(Cy.fondo.pestana, 2)} + espiga Ø${fmt(Cy.fondo.espiga.d, 2)} ${esc(Cy.fondo.espiga.tol)} × ${fmt(Cy.fondo.espiga.largo, 2)} mm (tope del retraído); ${esc(Cy.fondo.cjp.tipo)}`, esc(Cy.fondo.material)],
      ["Ojal trasero (ACC-030)", `R${fmt(Cy.fondo.ojal.R, 2)} × ${fmt(Cy.fondo.ojal.ancho, 2)}; rótula ${esc(Cy.fondo.ojal.rotula.designacion)}`, esc(Cy.fondo.ojal.material)],
      ["Tapa delantera (ACC-031)", `espiga Ø${fmt(Cy.tapa.espiga.d, 3)} ${esc(Cy.tapa.espiga.tol)}; ${esc(Cy.tapa.rosca.designacion)}; reborde Ø${fmt(Cy.tapa.reborde.d, 3)}; largo ${fmt(Cy.tapa.largo, 2)}`, esc(Cy.tapa.material)],
      ["Pistón y tuerca (ACC-032/033)", `Ø${fmt(Cy.piston.D, 3)} ${esc(Cy.piston.tol_D)} × ${fmt(Cy.piston.largo, 2)}; ${esc(Cy.piston.tuerca.designacion)}, ${fmt(Cy.piston.tuerca.par_Nm, 4)} N·m`, esc(Cy.piston.material)],
      ["Vástago (ACC-034)", `Ø${fmt(Cy.vastago.d, 2)} ${esc(Cy.vastago.tol)} × ${fmt(Cy.vastago.largo, 3)}; cromo ≥ ${fmt(Cy.vastago.cromo.espesor_min_um, 2)} µm; rosca ${esc(Cy.vastago.rosca.designacion)}`, esc(Cy.vastago.material)],
      ["Ojal del vástago (ACC-035)", `R${fmt(Cy.ojal_vastago.R, 2)} × ${fmt(Cy.ojal_vastago.ancho, 2)}, agujero Ø${fmt(Cy.ojal_vastago.d, 2)} ${esc(Cy.ojal_vastago.tol_d)}; ${esc(Cy.ojal_vastago.rotula)}`, esc(Cy.ojal_vastago.material)]];
    const sl = Cy.sellos.map((q) => `<tr><td>${esc(q.pos)}</td><td>${esc(q.nombre)}</td><td>${esc(q.norma)}</td><td>${esc(q.designacion)}</td><td>Ø${fmt(q.alojamiento.d_fondo, 3)} ${esc(q.alojamiento.tol_fondo)}</td></tr>`).join("");
    return `<div class="card scroll" style="margin-top:12px" id="bxCyl"><h3>Cilindro hidráulico fabricado (rev. 7d): ${fmt(Cy.D_camisa, 2)}/${fmt(Cy.d_vastago, 2)} × ${fmt(Cy.carrera, 3)}, retraído ${fmt(Cy.L0, 3)} / extendido ${fmt(Cy.L_ext, 3)} mm; prueba ${fmt(Cy.p_prueba, 3)} bar</h3>
      <div class="kv"><span>Cuerpo / c vástago</span><span>${fmt(Cy.cuerpo, 3)} / ${fmt(Cy.c_vastago, 2)} mm</span><span>F calado / F anular / F tapa</span><span>${fmt(Cy.F_calado_kN)} / ${fmt(Cy.F_anular_kN)} / ${fmt(Cy.F_tapa_kN)} kN</span><span>Masa por cilindro</span><span>${fmt(Cy.masa_total, 3)} kg</span><span>Filas «Cilindro» / gobernante</span><span>${rows.length} / ${gv ? esc(gv.name.replace(/^BX · Cilindro: /, "")) + " (FU " + fu3(gv.fu) + ")" : "—"}</span></div>
      <table id="bxCylPz"><tr><th>Pieza</th><th>Dimensiones (bx.cilindro)</th><th>Material</th></tr>${pz.map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="ref">${r[2]}</td></tr>`).join("")}</table>
      <table id="bxCylSl" style="margin-top:8px"><tr><th>Pos.</th><th>Sello</th><th>Norma</th><th>Designación</th><th>Alojamiento</th></tr>${sl}</table>
      <div class="note">${Cy.notas.map(esc).join(" ")}</div></div>`;
  }
  function renderBX() {
    const el = document.querySelector('section[data-t="bx"]');
    if (!A) { el.innerHTML = msgs(); return; }
    const D = A.bx; if (!D) { el.innerHTML = `<div class="msg warn">El módulo BX no está activo para estos parámetros.</div>`; return; }
    const d = D.disco, tw = d.tornillos, pa = D.pastillas, po = D.portador, aj = pa.ajuste || {}, tor = pa.tornillo || {}, so = pa.sobrepresion || {};
    const kv = (rows) => `<div class="kv">${rows.map(([a, b]) => `<span>${esc(a)}</span><span>${b}</span>`).join("")}</div>`;
    const rows = bxRowsOf();
    let g = "", vr = "";
    rows.forEach((c) => { const gg = (c.name.replace(/^BX · /, "").split(/[:(]/)[0] || "").trim(); if (gg !== g) { g = gg; vr += `<tr class="grp"><td colspan="7">${esc(g)}</td></tr>`; }
      vr += `<tr class="bx-row" data-st="${c.st}"><td><span class="st st-${c.st}">${ST[c.st]}</span></td><td>${esc(c.name)}<div class="form">${esc(c.formula)}</div></td><td class="n">${fmt(c.dem)}</td><td class="n">${c.cap != null ? fmt(c.cap) : ""}</td><td>${esc(c.unit || "")}</td><td class="n">${fu3(c.fu)}${fuBar(c)}</td><td class="ref">${esc(c.ref)}</td></tr>`; });
    const fab = (D.fabricacion || []).map((f) => `<tr data-estado="${esc(f.estado)}"><td>${esc(f.pieza)}</td><td class="ref">${esc(f.antes)}</td><td>${esc(f.despues)}</td><td><span class="st st-${f.estado === "eliminada" ? "ok" : f.estado === "simplificada" ? "ok" : f.estado === "nueva" ? "pend" : "info"}">${esc(f.estado)}</span></td><td class="ref">${esc(f.motivo || "")}</td><td class="ref">${esc(f.verificacion || "")}</td></tr>`).join("");
    const cnt = (D.fabricacion || []).reduce((m, f) => { m[f.estado] = (m[f.estado] || 0) + 1; return m; }, {});
    el.innerHTML = `<div class="grid" style="grid-template-columns:minmax(300px,1.2fr) minmax(280px,1fr)">
      <div class="card"><h3>Planta: ${d.modo === 1 ? "lámina, tapones" : "disco, tornillos"}, pastillas y portador</h3>${bxPlanSVG(D)}</div>
      <div>${d.modo === 1 ? bxLaminaCard(d, kv) : `<div class="card" id="bxDisco"><h3>Disco inoxidable (2 semidiscos con CJP)</h3>${kv([["Material", esc(d.material)], ["Espesor adoptado / requerido", `<b>${fmt(d.t)}</b> / ${fmt(d.t_req, 3)} mm`], ["Requerido por la cabeza avellanada / por el vacío local", `${fmt(d.t_cabeza, 3)} / ${fmt(d.t_vacio, 3)} mm`], ["R exterior / interior", `${fmt(d.R_ext, 4)} / ${fmt(d.R_int, 4)} mm`], ["Fy / Fu / α", `${fmt(d.Fy, 3)} / ${fmt(d.Fu, 3)} MPa / ${fmt(d.alfa * 1e6, 3)}×10⁻⁶/K`], ["Masa (semidisco)", `${fmt(d.masa, 4)} kg (${fmt(d.masa_semidisco, 3)} kg)`], ["Celda entre pastillas: σ / flecha", `${fmt(d.celda.sigma)} MPa / ${fmt(d.celda.flecha, 3)} mm`], ["CJP", esc(d.cjp.norma) + ", " + fmt(d.cjp.largo, 4) + " mm"]])}<div class="note">${esc(d.acabado)}</div></div>
      <div class="card" id="bxTorn" style="margin-top:12px"><h3>Tornillos del disco</h3>${kv([["Designación", esc(tw.designacion_base)], ["Cantidad / malla / s mín.", `<b>${tw.n}</b> / ${fmt(tw.paso_malla, 3)} / ${fmt(tw.s_min, 3)} mm`], ["Anillos (R)", tw.anillos.map((r) => fmt(r, 4)).join(" · ")], ["Corte combinado / capacidad", `${fmt(tw.V_comb / 1e3)} / ${fmt(tw.capV / 1e3)} kN`], ["Fuerza térmica de borde ext. / int.", `${fmt(tw.Fth_ext / 1e3)} / ${fmt(tw.Fth_int / 1e3)} kN (ΔT ${fmt(tw.dT_diseno, 3)} K)`]])}<div class="note">${esc(tw.nota)}</div></div></div></div>`}<div class="grid" style="margin-top:12px">
      <div class="card" id="bxPast"><h3>Pastillas de UHMW</h3>${kv([["Cantidad / forma y medida" + (pa.d_torneado != null ? " / Ø de fabricación" : ""), `<b>${pa.n}</b> / ${pkTxt(pa, 4)}${pa.d_torneado != null && !pkSq(pa) ? " / " + fmt(pa.d_torneado, 5) : ""} mm`], ["Alto H / saliente h_p", `${fmt(pa.H, 3)} / <b>${fmt(pa.h_p, 3)}</b> mm`], ["Interferencia (rango)", `${fmt(aj.delta, 3)} mm${aj.rango ? ` (${fmt(aj.rango[0], 3)} … ${fmt(aj.rango[1], 3)})` : ""}`], ["p máx. / PV máx.", `${fmt(pa.p_max)} MPa / ${fmt(pa.PV_max)} MPa·m/s`], ["Sobrepresión por planitud (p total)", `${fmt(so.dp)} (${fmt(so.p_total)}) MPa`], ["Σ N sobre las pastillas", `${fmt(pa.suma_N_kN, 4)} kN`], ["Cobertura / masa", `${fmt(pa.cobertura, 2)} / ${fmt(pa.masa_total, 3)} kg (${fmt(pa.masa_unit, 3)} c/u)`], ["Tornillo", esc(tor.designacion)], ["Taladro ciego / engrane", `${fmt(tor.taladro_ciego, 3)} / ${fmt(tor.engrane, 3)} mm`]])}<div class="note">${esc(aj.montaje || "")}${pa.proceso ? " " + esc(pa.proceso) : ""}</div></div>
      <div class="card" id="bxPort"><h3>Portador soldado a la base</h3>${kv([["Material", esc(po.material)], ["Espesor / R int. / R ext.", `<b>${fmt(po.t)}</b> / ${fmt(po.R_int, 4)} / ${fmt(po.R_ext, 4)} mm`], ["Paso / ligamento", `${fmt(po.paso, 4)} / ${fmt(po.ligamento, 3)} mm`], ["Patrón", esc(po.patron.tipo) + ` (saltos máx. ${po.patron.saltos_max}, al borde ${po.patron.pastillas_al_borde})`], ["Agujeros de pastillas / de soldadura", `${po.agujeros.n} × Ø${fmt(po.agujeros.d, 4)} / ${po.tapones.n}`], ["Filetes perimetrales", `z${fmt(po.filetes.w)} en R${fmt(po.filetes.exterior.R, 4)} y R${fmt(po.filetes.interior.R, 4)}`], ["Masa (plancha + filetes)", `${fmt(po.masa, 4)} kg (${fmt(po.masa_plancha, 4)} + ${fmt(po.masa_filetes, 3)})`]])}<div class="note">${esc(po.corte)}. ${esc(po.secuencia)}</div></div>
      <div class="card" id="bxDis"><h3>Búsqueda del diseño</h3>${kv([["Candidatos evaluados / que cumplen", `${D.diseno.candidatos} / ${D.diseno.candidatos_ok}`], ["μ máx. / μ efectivo (acero)", `${fmt(D.diseno.mu_max, 3)} / ${fmt(D.diseno.mu_eff, 3)}`], ["T de calado", `${fmt(D.diseno.T_calado)} kN·m`], ["q medio / q máx.", `${fmt(D.diseno.q_med)} / ${fmt(D.diseno.q_max)} MPa`]])}<div class="note">${esc(D.diseno.nota)}</div></div></div>
    ${cylCard(D.cilindro)}
    <div class="card scroll" style="margin-top:12px" id="bxFab"><h3>Fabricación: antes → después (${Object.entries(cnt).map(([k, n]) => n + " " + k).join(" · ")})</h3><table><tr><th>Pieza</th><th>Antes</th><th>Después</th><th>Estado</th><th>Motivo</th><th>Verificación</th></tr>${fab}</table></div>
    <div class="card scroll" style="margin-top:12px" id="bxVer"><h3>Verificaciones TT300-BX (${rows.length} filas; también en «Verificaciones», grupo «${esc((rows[0] || {}).grp || "")}»)</h3><table><tr><th>Estado</th><th>Verificación</th><th class="n">Demanda</th><th class="n">Capacidad</th><th>Unidad</th><th class="n">FU</th><th>Norma / referencia</th></tr>${vr}</table></div>`;
  }

  /* ---------- Masas ---------- */
  function renderMasa() {
    const el = document.querySelector('section[data-t="masa"]');
    if (!A) { el.innerHTML = msgs(); return; }
    const m = A.R.m;
    const PP = A.P || P, me = Math.round(PP.bx_mesa_entera == null ? 1 : PP.bx_mesa_entera) === 1;   // rev. 7c: plancha entera por nivel
    const parts = [[me ? "Plancha superior entera Ø" + PP.D_top + " (con los agujeros de los pasadores)" : "Plancha superior (con anillo)", m.top], [me ? "Plancha inferior entera Ø" + PP.D_top + " (con los agujeros de los pasadores)" : "Plancha inferior (con anillo)", m.bot], ["Almas anulares", m.webs], ["Nervios radiales", m.ribs], ["Cubo", m.hub], ["Pasadores de empuje", m.pins],
      ["Disco inoxidable BX (2 semidiscos)", m.ss], ["Pastillas de UHMW (BX)", m.uhmw], ["Portador soldado a la base (BX)", m.bxPortador || 0], ["Cubierta de madera dura", m.wood], ["Anillo de acero de la madera", m.ring], ["Plancha base", m.base], ["Marco perimetral", m.rim], ["Ménsulas de cilindro", m.brackets], ["Uñas", m.dogs], ["Pivote", m.pivot], ["Cilindros (comerciales)", m.cyl]].filter((q) => q[1] > 0 || /BX/.test(q[0]));
    const otros = m.total - parts.reduce((s, q) => s + (q[1] || 0), 0);
    if (Math.abs(otros) > 0.05) parts.push(["Otros del núcleo (placas-guía, soportes, refuerzos, patines…)", otros]);
    const mx = Math.max(...parts.map((p) => p[1]));
    el.innerHTML = `<div class="grid"><div class="card scroll"><h3>Desglose</h3><table><tr><th>Pieza</th><th class="n">kg</th><th class="n">%</th><th></th></tr>
      ${parts.map(([n, v]) => `<tr><td>${n}</td><td class="n">${fmt(v, 3)}</td><td class="n">${fmt(v / m.total * 100, 2)}</td><td style="width:40%"><div class="fu"><i style="width:${v / mx * 100}%;background:var(--acc)"></i></div></td></tr>`).join("")}
      <tr class="grp"><td>Total</td><td class="n">${fmt(m.total, 4)}</td><td class="n">100</td><td></td></tr></table>
      <div class="note">Masas de acero con ρ = 7850 kg/m³, sin soldadura ni pintura (agregar ≈ 2 %). No incluye bomba, mangueras ni plancha diamantada.</div></div>
      <div class="card"><h3>Transporte</h3><div class="kv"><span>Masa total</span><span>${fmt(m.total, 4)} kg</span><span>Mesa (izable por separado)</span><span>${fmt(m.disc + m.ssTop + m.pivot, 4)} kg</span><span>Base + ménsulas</span><span>${fmt(m.base + m.rim + m.brackets, 4)} kg</span><span>Dimensiones en planta</span><span>${fmt(P.B, 4)} × ${fmt(P.B, 4)} mm</span><span>Alto total</span><span>${fmt(P.t_base + A.R.ifc.delta + P.h_disc + (P.opt_wood > 0.5 ? P.t_wood : 0), 3)} mm</span><span>Referencia KIET 400T</span><span>${fmt(REF.KIET, 4)} kg</span></div>
      <div class="note">El optimizador de masa del núcleo no evalúa las filas BX (agentes_bx.js: pendiente); la geometría BX la dimensiona el módulo (parámetros bx_ en 0 = automático).</div></div></div>
      ${bxDespiece()}`;
  }
  // despiece de la interfaz BX (A.bx): piezas, cantidades y masas del módulo
  function bxDespiece() {
    const D = A.bx; if (!D) return "";
    const d = D.disco, tw = d.tornillos, pa = D.pastillas, po = D.portador;
    const rows = (d.modo === 1 ? [["Panel de lámina inoxidable (" + d.material + ") " + fmt(d.t) + " mm", (d.lamina || {}).n_paneles, ((d.lamina || {}).paneles || [{}])[0].masa, d.masa],
      ["Tapón de soldadura Ø" + fmt((d.tapones || {}).d) + " en la lámina", (d.tapones || {}).n, null, null]] : [["Semidisco inoxidable (" + d.material + ") Ø" + fmt(2 * d.R_ext, 4) + " × " + fmt(d.t) + " mm, agujero Ø" + fmt(2 * d.R_int, 4), d.semidiscos, d.masa_semidisco, d.masa],
      ["Tornillo " + tw.designacion_base, tw.n, null, null]]).concat([

      ["Portador " + po.material.split(" (")[0] + " t = " + fmt(po.t) + " mm, R" + fmt(po.R_int, 4) + "…R" + fmt(po.R_ext, 4) + ", " + po.agujeros.n + " agujeros Ø" + fmt(po.agujeros.d, 4), 1, po.masa, po.masa],
      ["Pastilla UHMW " + (pkSq(pa) ? pkTxt(pa, 4) : "Ø" + fmt(pa.d_torneado != null ? pa.d_torneado : pa.d, 5)) + " × " + fmt(pa.H, 3) + " mm" + (pa.proceso ? " (" + String(pa.proceso).split(/[;.]/)[0] + ")" : ""), pa.n, pa.masa_unit, pa.masa_total],
      ["Tornillo de pastilla " + ((pa.tornillo || {}).designacion || "—"), (pa.tornillo || {}).n, null, null]]).concat(po.tapones.n ? [["Agujero de soldadura (tapón) Ø" + fmt(po.tapones.d, 4) + ", filete z" + fmt(po.tapones.w), po.tapones.n, null, null]] : []);
    return `<div class="card scroll" style="margin-top:12px" id="bxDesp"><h3>Despiece de la interfaz TT300-BX</h3><table><tr><th>Pieza</th><th class="n">Cantidad</th><th class="n">kg c/u</th><th class="n">kg total</th></tr>
      ${rows.map(([n, q, mu, mt]) => `<tr><td>${esc(n)}</td><td class="n">${q}</td><td class="n">${mu == null ? "—" : fmt(mu, 3)}</td><td class="n">${mt == null ? "—" : fmt(mt, 4)}</td></tr>`).join("")}
      <tr class="grp"><td>Masa de la interfaz BX (disco + pastillas + portador)</td><td></td><td></td><td class="n">${fmt((A.R.m.ss || 0) + (A.R.m.uhmw || 0) + (A.R.m.bxPortador || 0), 4)}</td></tr></table>
      <div class="note">Soldaduras: ${D.soldaduras.map((w) => esc(w.id + " " + w.union + " (" + w.tipo + ")")).join(" · ")}.</div></div>`;
  }

  /* ---------- Agentes ---------- */
  function renderAgentes() {
    const el = document.querySelector('section[data-t="agentes"]');
    if (!A) { el.innerHTML = `<div class="card"><h3>1 · Validador de entradas</h3>${msgs()}</div>`; return; }
    const xc = X.map((c) => `<tr><td><span class="st st-${c.ok ? "ok" : "fail"}">${c.ok ? "OK" : "Revisar"}</span></td><td>${esc(c.name)}</td><td class="n">${fmt(c.tool, 4)}</td><td class="n">${fmt(c.indep, 4)}</td><td class="n">${fmt(c.d, 2)} %</td><td class="ref">${esc(c.note || "")}${c.tol != null ? " · tol. " + fmt(c.tol) + " %" : ""}</td></tr>`).join("");
    const scen = () => { const SC = lz("SC"); if (!SC) return lzErr("SC") || `<div class="msg error">Sin escenarios</div>`;
    const sg = SC.grid.map((row) => `<tr><td class="n">${fmt(row[0].mu)}</td>${row.map((c) => `<td class="n"><span class="st st-${c.FS >= P.FS_min ? "ok" : c.FS >= 1 ? "warn" : "fail"}">FS ${fmt(c.FS)}</span><div class="form">${fmt(c.p)} bar</div></td>`).join("")}</tr>`).join("");
      return `<div class="grid" style="margin-top:12px">
      <div class="card scroll"><h3>4 · Escenarios de fricción (FS al calado)</h3><table><tr><th class="n">μ</th>${SC.rs.map(([n, r]) => `<th class="n">${n} = ${fmt(r, 4)} mm</th>`).join("")}</tr>${sg}</table>
        <div class="note">Verde: FS ≥ FS_min (${fmt(P.FS_min)}); ámbar: gira sin el margen exigido; rojo: no gira.</div></div>
      <div class="card"><h3>4 · Escenarios de carga (caso de diseño)</h3><table><tr><th class="n">W (tf)</th><th class="n">FS</th><th class="n">p (bar)</th><th class="n">μ máx (r_ef)</th></tr>
        ${SC.loads.map((l) => `<tr><td class="n">${fmt(l.W, 3)}</td><td class="n">${fmt(l.FS)}</td><td class="n">${fmt(l.p)}</td><td class="n">${fmt(l.muMax)}</td></tr>`).join("")}</table></div>
      <div class="card"><h3>4 · Clase de presión del cilindro (caso de diseño)</h3><table><tr><th class="n">Clase (psi)</th><th class="n">Alivio / alarma (bar)</th><th class="n">Émbolo mínimo (mm)</th><th class="n">FS con Ø${fmt(P.D_bore, 3)}</th><th class="n">p dis. (bar)</th></tr>
        ${(SC.classes || []).map((c) => `<tr><td class="n">${fmt(c.psi, 5)}</td><td class="n">${fmt(c.pr, 3)} / ${fmt(c.pa, 3)}</td><td class="n">${fmt(c.Dmin, 3)}</td><td class="n">${fmt(c.FScur)}</td><td class="n">${fmt(c.pcur, 3)}</td></tr>`).join("")}</table>
        <div class="note">Émbolo mínimo = máx(FS_min·F_dis/p_alivio; F_dis/p_alarma), con alarma = 0,85·alivio. Al cambiar de clase, ajuste también Ø del cuerpo, masa y cotas del cilindro según catálogo; la herramienta verifica el resto.</div></div></div>`; };
    el.innerHTML = `<div class="grid">
      <div class="card"><h3>1 · Validador de entradas</h3>${msgs()}</div>
      <div class="card"><h3>2 · Auditor normativo</h3>${AU.ok ? `<div class="msg ok">Las ${A.checks.length} verificaciones declaran fórmula y referencia.</div>` : `<div class="msg error">${AU.missing.length} verificaciones sin referencia: ${AU.missing.map((c) => esc(c.name)).join(", ")}</div>`}
        <table><tr><th>Referencia</th><th class="n">N°</th></tr>${AU.refs.map(([r, n]) => `<tr><td class="ref">${esc(r)}</td><td class="n">${n}</td></tr>`).join("")}</table></div></div>
      <div class="card scroll" style="margin-top:12px"><h3>3 · Revisor cruzado (formulación independiente; las filas «BX ·» recalculan lo propio del módulo)</h3><table id="agX"><tr><th>Estado</th><th>Magnitud</th><th class="n">Herramienta</th><th class="n">Independiente</th><th class="n">Δ</th><th>Nota</th></tr>${xc}</table></div>
      ${lzSlot(scen, ["SC"])}
      <div class="card" style="margin-top:12px"><h3>5 · Optimizador de masa</h3><div class="msg warn">${esc(AG.optimize().msg)}</div></div>`;
  }

  /* ---------- Paquete de dibujo (checkbox «Exportar paquete de dibujo») ---------- */
  const LSK = "tt300bx-pkg";
  const BX_IFACE = "TT300-BX · lámina inoxidable soldada a la mesa (modo 1) o disco atornillado (modo 0) + pastillas de UHMW en portador soldado a la base";
  /* ---------- Temperatura (exposición solar): escenario aparte, geometría de 20 °C congelada ---------- */
  let TH = null, THkey = "", THreq = "";
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
      el.innerHTML = ctl + `<div class="busy" id="tempCalc">Calculando el escenario térmico de TT300-BX en segundo plano (BX.thermal)…</div>`; bind();
      if (THreq === key) return;
      THreq = key;
      WK.lazy.call({ op: "lazy", k: "TH", P: Object.assign({}, P) }, RGEN).then((r) => { if (THreq !== key) return; THreq = ""; TH = r; THkey = key; renderTemp(); },
        (err) => { if (THreq !== key) return; THreq = ""; if (err.message === "cancelado") { if (cur === "temp") renderTemp(); return; } TH = null; if (cur === "temp") { el.innerHTML = ctl + `<div class="msg error">Error de cálculo térmico: ${esc(err.message)}</div>`; bind(); } });
      return;
    }
    el.innerHTML = ctl + tempBody(TH); bind();
  }
  function tempBody(r) {
    const at = (a, T) => a.byT.find((b) => Math.abs(b.T - T) < 1e-9), id0 = altId(), act = r.alternativas.find((a) => a.id === id0) || r.alternativas[0], Tn = r.T_scn;
    const bitem = (a) => at(a, Tn), b20 = (a) => at(a, r.T_ref) || a.byT[0];
    const ver = (b) => (b.gira && b.estructura && b.termico ? "ok" : !b.gira || !b.estructura ? "fail" : "warn");
    const npc = (b) => (b.pendientes_criticos || []).length;
    const tags = (b) => `${b.gira ? "" : '<span class="st st-fail">No gira con FS_mín</span> '}${b.estructura ? "" : '<span class="st st-fail">Estructura/juntas</span> '}${b.termico ? "" : `<span class="st st-fail">Térmica: ${r.alcance === 2 ? "aceite/" : ""}gradiente/juntas</span> `}${npc(b) ? `<span class="st st-fail" title="${esc(b.estado_global || "")}">Pendiente de decisión (${npc(b)}, FU ${fu2(b.fuMaxPend)})</span>` : ""}${b.gira && b.estructura && b.termico && !npc(b) ? '<span class="st st-ok">Cumple</span>' : ""}`;
    const gov = (g) => (g ? esc(g.grp + ": " + g.nombre) + ` <span class="ref">(FU ${fu2(g.fu)})</span>` : "—");
    const bxT = (() => { const bb = bitem(act).bx; if (!bb) return ""; return `<div class="card scroll" style="margin-top:12px" id="tempBx"><h3>Filas TT300-BX a ${fmt(Tn, 3)} °C (geometría BX de 20 °C congelada) · ${bb.nFail} no cumplen, ${bb.nWarn} en monitoreo${bb.gobernante ? " · gobierna " + esc(bb.gobernante.nombre.replace(/^BX · /, "")) + " (FU " + fu3(bb.gobernante.fu) + ")" : ""}</h3>
      <table><tr><th>Estado</th><th>Verificación</th><th class="n">Demanda</th><th class="n">Capacidad</th><th>Unidad</th><th class="n">FU</th><th>Referencia</th></tr>${bb.filas.map((f) => `<tr><td><span class="st st-${f.estado}">${ST[f.estado] || esc(f.estado)}</span></td><td>${esc(f.nombre)}<div class="form">${esc(f.formula || "")}</div></td><td class="n">${fmt(f.dem)}</td><td class="n">${f.cap != null ? fmt(f.cap) : ""}</td><td>${esc(f.unidad || "")}</td><td class="n">${fu3(f.fu)}</td><td class="ref">${esc(f.ref || "")}</td></tr>`).join("")}</table>
      <div class="note">Filas propias del módulo BX evaluadas a cada temperatura con las capacidades reducidas (BX.thermal → byT[].bx). Los límites de temperatura de la interfaz BX son parámetros del grupo TT300-BX del panel izquierdo; ver también las limitaciones de uso del Resumen.</div></div>`; })();
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
    return warns + bxT + `
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
      <div class="note">μ máximo (múltiplo del de diseño) con FS ≥ FS_mín: <b>× ${fu2(sm.mu_crit)}</b>. Con Fy del acero × 0,92 (ASME II-D, confianza C): FU estructura máx. ${fu2(sm.kFy092.fuEst)} (${sm.kFy092.fuEst <= 1 ? "≤ 1,0" : "&gt; 1,0"}); FU térmico máx. ${fu2(sm.kFy092.fuTerm)}.${sm.bz090 ? ` Con bronce × 0,90: FU máx. ${fu2(sm.bz090.fuEst)}.` : ""}</div>${wd}</div>
    <div class="note">Fuente de los datos y niveles de confianza (A tabla contrastada, B ficha o dos fuentes, C supuesto): docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)». Supuestos de confianza C: ${r.supuestos_C.map(esc).join("; ")}.</div>`;
  }

  function download(name, data, type) {
    const blob = new Blob([data], { type });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 800);
  }
  /* JSON de diseño de TT300-BX: lo arma el worker con planos_export.js (buildDesign, mismo esquema que tools/export_design.js) sobre la
     fachada BX más el bloque «bx» (packages/web/planos_export_bx.js, fuente única con tools/export_design_bx.js). */
  let DJ = { key: "", json: null, p: null };
  function designJSONAsync() {
    const key = JSON.stringify(P);
    if (DJ.key === key && DJ.json) return Promise.resolve(DJ.json);
    if (DJ.key === key && DJ.p) return DJ.p;
    DJ = { key, json: null, p: null };
    const Ps = Object.assign({}, P), g = RGEN;
    DJ.p = memoFor(Ps, g).then((memo) => WK.main.call({ op: "design", P: Ps, memo }, g)).then((j) => { if (DJ.key === key) { DJ.json = j; DJ.p = null; } return j; }, (err) => { if (DJ.key === key) DJ.p = null; throw err; });
    return DJ.p;
  }
  // resultados que pide el exportador además del análisis (PLANOS_BX.exportCalls): se reparten entre varios workers en paralelo; los que ya
  // están (precalculados al compilar para los valores por defecto, o los bloques diferidos de mercado y capacidad) no se repiten
  let HELP = [];
  function memoFor(Ps, g) {
    const Pf = Object.assign(TT.defaults(), Ps), calls = PLANOS_BX.exportCalls(Pf), memo = {}, pre = preOf();
    if (pre && pre.key === JSON.stringify(Ps) && pre.memoTxt) { try { Object.assign(memo, JSON.parse(pre.memoTxt, (k, v) => (v === "__NaN" ? NaN : v === "__Inf" ? Infinity : v === "__-Inf" ? -Infinity : v))); } catch (e) { } }
    if (g === RGEN && LZ.MK) memo[PLANOS_BX.memoKey("market", [Pf])] = LZ.MK;
    if (g === RGEN && LZ.CN) memo[PLANOS_BX.memoKey("capacityByCyl", [Pf, [1, 2]])] = LZ.CN;
    const todo = calls.filter((c) => !(c.key in memo));
    if (!todo.length || !WURL) return Promise.resolve(memo);
    const n = Math.max(1, Math.min(4, (navigator.hardwareConcurrency || 2) - 1, todo.length));
    HELP.forEach((w) => w.terminate()); HELP = [];
    let i = 0;
    const runOne = (w) => (i >= todo.length ? Promise.resolve() : (() => { const c = todo[i++]; return w.call({ op: "call", fn: c.fn, args: c.args }, g).then((r) => { memo[c.key] = r; }, () => { }).then(() => runOne(w)); })());
    const ws = Array.from({ length: n }, () => mkW("ayuda"));
    HELP = ws.map((w) => ({ terminate: w.kill }));
    return Promise.all(ws.map(runOne)).then(() => { ws.forEach((w) => w.kill()); HELP = []; return memo; });
  }
  function renderPkg() {
    const on = $("#pkgChk").checked, el = $("#pkgPanel");
    el.hidden = !on; $("#pkgRow").classList.toggle("chg", on);
    if (!on) return;
    if (!A) { el.innerHTML = `<div class="msg error">${calc ? "Calculando…" : "Corrija los datos marcados para exportar."}</div>`; return; }
    const R = A.R, v = A.verdict, ok = v.gira && v.estructura;
    const RVp = BX.REVISIONES_PLANOS, RVa = RVp[RVp.length - 1];   // revisión única del juego de planos BX (README_BX §13.8)
    el.innerHTML = `<div class="kv"><span>Interfaz de giro</span><span>${esc(BX_IFACE)}</span>
        <span>Masa total</span><span>${fmt(R.m.total, 4)} kg</span>
        <span>Revisión del juego de planos</span><span id="pkgRev" data-rev="${esc(RVa.letra)}">Rev. ${esc(RVa.letra)} (${esc(RVa.fecha)}, cálculo BX rev. ${esc(RVa.rev_calculo)}; todas las láminas) · anteriores: ${RVp.slice(0, -1).reverse().map((r) => "Rev. " + esc(r.letra)).join(", ") || "—"}</span></div>
      ${ok ? "" : `<div class="msg warn">El diseño actual no cumple (gira o estructura): el generador completo se negará a emitir planos hasta corregirlo.</div>`}
      <div class="btns"><button class="pri" id="bPkgJson">JSON de diseño (con bloque «bx»)</button></div><div class="busy" id="pkgMsg"></div>
      <div class="adv">${esc(PLANOS_W.ADVERTENCIA)}</div>
      <div class="note">${PLANOS_W.NOTAS.map(esc).join(" · ")}. Las láminas esquemáticas del navegador (DXF/SVG) dibujan las interfaces del núcleo y no la BX: en esta herramienta solo se descarga el JSON de diseño, que es la entrada del generador completo (PDF, DXF, STEP y Excel, paquete BX).</div>`;
    $("#bPkgJson").onclick = () => {
      const m = $("#pkgMsg"); if (m) m.textContent = "Armando el JSON de diseño en segundo plano…";
      designJSONAsync().then((j) => { if (m) m.textContent = "JSON listo."; download("TT300-BX_design.json", j, "application/json"); }, (err) => { if (m) m.textContent = ""; alert("No se pudo generar el JSON de diseño: " + err.message); });
    };
  }
  $("#pkgChk").checked = store.get(LSK) === "1";
  $("#pkgChk").addEventListener("change", () => { store.set(LSK, $("#pkgChk").checked ? "1" : "0"); renderPkg(); });

  /* ---------- Planos: generación a pedido con el generador local (tools/servidor_planos.py en 127.0.0.1:8765) ---------- */
  const PL_GRUPOS = [["generales", "Generales"], ["fabricacion", "Fabricación"], ["armado", "Armado"]];
  const GEN_URL = (location.protocol.startsWith("http") && (location.hostname === "127.0.0.1" || location.hostname === "localhost") && location.port === "8765") ? "" : "http://127.0.0.1:8765";
  const PLAB = {}; TT.PARAM_GROUPS.forEach((g) => g.p.forEach((q) => { PLAB[q[0]] = [q[1], q[2]]; }));
  // srv: null = comprobando, false = no responde, objeto = respuesta de /api/ping; job = trabajo en curso o último; ver = juego mostrado (indice); hist = /api/listar
  const GEN = { srv: null, job: null, poll: null, err: "", pinging: false, ver: null, verId: "", hist: null };
  const href = (base, f) => GEN_URL + "/" + (base + "/" + f).split("/").map(encodeURIComponent).join("/");
  const vEq = (a, b) => (typeof a === "number" && typeof b === "number") ? Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b)) : a === b;
  const vTxt = (v) => v === undefined ? "(no existe)" : typeof v === "number" ? v.toLocaleString("es-CL", { maximumFractionDigits: 9 }) : String(v);
  const plDiff = (Pa, Pb) => [...new Set([...Object.keys(Pa), ...Object.keys(Pb)])].filter((k) => !vEq(Pa[k], Pb[k]));
  function plCards(ix) {
    const b = ix.carpeta, short = (c) => c.replace(/^TT300C-/, ""), a = ix.archivos || {};
    const cards = PL_GRUPOS.map(([gid, gt]) => {
      const ls = ix.laminas.filter((l) => l.grupo === gid), g = ix.grupos[gid] || {};
      const rows = ls.map((l) => `<tr><td>${esc(short(l.codigo))}</td><td>${esc(l.titulo)}</td><td>${l.pdf ? `<a href="${esc(href(b, l.pdf))}" target="_blank" rel="noopener">PDF</a>` : "—"}${l.dxf ? ` · <a href="${esc(href(b, l.dxf))}" download>DXF</a>` : ""}</td></tr>`).join("");
      return `<div class="card pl-grp" data-g="${gid}"><h3>${esc(gt)}</h3><div class="big">${ls.length} <span class="ref">láminas</span></div>
        <div class="btns">${g.pdf ? `<a class="btn pri" data-pdf="${gid}" href="${esc(href(b, g.pdf))}" target="_blank" rel="noopener">PDF ${esc(gt)}</a>` : `<span class="note">Sin PDF del grupo</span>`}</div>
        <details><summary>Lista de láminas (${ls.length})</summary><div class="scroll"><table><tr><th>Plano</th><th>Título</th><th>Archivo</th></tr>${rows}</table></div></details></div>`;
    }).join("");
    const lk = (k, t, dl) => a[k] ? `<a data-f="${k}" href="${esc(href(b, a[k]))}"${dl ? " download" : ' target="_blank" rel="noopener"'}>${t}</a>` : "";
    return `<div class="grid">${cards}</div>
      <div class="pl-files"><b>Otros archivos:</b>${lk("combinado", "PDF combinado (todas las láminas)")}${lk("despiece_xlsx", "Despiece XLSX", 1)}${lk("step", "Modelo 3D STEP", 1)}${lk("dxf_zip", "DXF de todas las láminas (.zip)", 1)}${lk("informe", "Informe del paquete")}</div>
      <div class="note">Carpeta: <span class="form">${esc(b)}/</span></div>`;
  }
  function renderPlanos() { renderSrv(); renderResumenPl(); renderGen(); renderHist(); }
  /* estado del generador e instrucciones de instalación */
  function renderSrv() {
    const el = $("#plSrv"); if (!el) return;
    const s = GEN.srv;
    el.innerHTML = `<h3>Generador local de planos</h3>` + (s === null ? `<div class="note" id="genEstado" data-srv="comprobando">Comprobando si el generador local está activo en 127.0.0.1:8765…</div>`
      : s === false ? `<div class="msg warn" id="genEstado" data-srv="inactivo"><b>El generador local no responde.</b> Los planos se generan a pedido en este equipo:</div>
        <ol class="pl-pasos" id="genInstr"><li><b>Una sola vez:</b> ejecute <span class="form">Instalar_generador_planos.bat</span> (carpeta del repositorio). Busca Python 3.12 o 3.11 (si falta, indica cómo instalarlo desde python.org), crea <span class="form">.venv-planos</span> e instala los paquetes; tarda varios minutos.</li>
        <li><b>Cada vez:</b> ejecute <span class="form">Generar_planos_Tornamesa.bat</span> y deje abierta su ventana. Abre esta herramienta desde http://127.0.0.1:8765.</li>
        <li>Vuelva a esta pestaña y pulse «Volver a comprobar».</li></ol>
        <div class="btns"><button id="bGenPing">Volver a comprobar</button></div>`
      : `<div class="msg ok" id="genEstado" data-srv="activo">Generador local activo (${esc(s.servidor || "127.0.0.1:8765")}${s.python ? " · Python " + esc(s.python) : ""}).</div>
        <div class="note">Los juegos generados quedan en la carpeta <span class="form">salidas/</span> del repositorio y se sirven desde el generador local.</div>`);
    const bp = $("#bGenPing"); if (bp) bp.onclick = () => { GEN.srv = null; renderSrv(); renderGen(); genPing(); };
  }
  /* alternativa y parámetros que se enviarán */
  function renderResumenPl() {
    const el = $("#plResumen"); if (!el) return;
    const ch = Object.keys(DEF).filter((k) => !vEq(P[k], DEF[k]));
    let h = `<h3>Lo que se enviará al generador</h3>`;
    if (!A) { el.innerHTML = h + `<div class="msg error" id="plResEstado">Corrija los datos marcados: con datos inválidos no se pueden generar planos.</div>`; return; }
    const R = A.R, v = A.verdict;
    h += `<div class="kv" id="plResKv"><span>Módulo</span><span>TT300-BX</span>
      <span>Interfaz de giro</span><span>${esc(BX_IFACE)}</span><span>Disco / pastillas / portador</span><span>${A.bx ? `t ${fmt(A.bx.disco.t)} mm · ${A.bx.pastillas.n} × ${pkTxt(A.bx.pastillas)} · t ${fmt(A.bx.portador.t)} mm` : "—"}</span><span>Cubierta</span><span>${esc(PLANOS_W.woodText(P))}</span>
      <span>Capacidad / masa total</span><span>${fmt(P.W_tf, 3)} tf / ${fmt(R.m.total, 4)} kg</span>
      <span>¿Gira? / ¿Estructura?</span><span>${v.gira ? "sí" : "NO"} / ${v.estructura ? "cumple" : "NO cumple"}</span>
      <span>Estado global</span><span>${esc(v.estado_global)}</span></div>`;
    if (!(v.gira && v.estructura)) h += `<div class="msg warn">El diseño actual no cumple (gira o estructura): el generador se negará a emitir planos.</div>`;
    h += `<details${ch.length && ch.length <= 8 ? " open" : ""}><summary>Parámetros distintos de los valores por defecto (${ch.length} de ${Object.keys(DEF).length})</summary>${ch.length ? `<div class="scroll"><table id="plParams"><tr><th>Parámetro</th><th>Nombre</th><th class="n">Valor</th><th class="n">Por defecto</th></tr>
      ${ch.map((k) => `<tr><td class="form">${esc(k)}</td><td>${esc(PLAB[k] ? PLAB[k][0] : "")}${PLAB[k] && PLAB[k][1] && PLAB[k][1] !== "–" ? ` <span class="ref">[${esc(PLAB[k][1])}]</span>` : ""}</td><td class="n">${esc(vTxt(P[k]))}</td><td class="n">${esc(vTxt(DEF[k]))}</td></tr>`).join("")}</table></div>` : `<div class="note">Todos los parámetros están en su valor por defecto.</div>`}</details>
      <div class="note">Se envía el JSON de diseño completo (el mismo esquema de <span class="form">node tools/export_design_bx.js</span>, con el bloque «bx»): ${Object.keys(DEF).length} parámetros más los resultados del cálculo. Lo arma el worker (varios segundos).</div>`;
    el.innerHTML = h;
  }
  /* ---- llamadas al servidor ---- */
  function genFetch(path, opt, ms) {
    const ac = new AbortController(), t = setTimeout(() => ac.abort(), ms || 2500);
    return fetch(GEN_URL + path, Object.assign({ cache: "no-store", signal: ac.signal }, opt || {})).then((r) => r.json().then((j) => { clearTimeout(t); if (!r.ok) { const e = new Error(j.error || ("HTTP " + r.status)); e.data = j; throw e; } return j; }));
  }
  function genPing() {
    GEN.pinging = true;
    return genFetch("/api/ping").finally(() => { GEN.pinging = false; }).then((j) => {
      GEN.srv = j;
      if (j.trabajo && !GEN.job) { GEN.job = j.trabajo; if (j.trabajo.estado === "en_curso") genPoll(); }
      genHist();
    }).catch(() => { GEN.srv = false; GEN.hist = null; }).then(() => { renderSrv(); renderGen(); renderHist(); });
  }
  function genHist() {
    return genFetch("/api/listar", null, 5000).then((j) => { GEN.hist = j.salidas || []; }).catch(() => { GEN.hist = null; }).then(renderHist);
  }
  function genPoll() {
    clearInterval(GEN.poll);
    GEN.poll = setInterval(() => {
      if (!GEN.job) { clearInterval(GEN.poll); return; }
      genFetch("/api/estado?id=" + encodeURIComponent(GEN.job.id)).then((j) => {
        GEN.job = j;
        if (j.estado !== "en_curso") { clearInterval(GEN.poll); if (j.indice) { GEN.ver = j.indice; GEN.verId = j.id; } genHist(); }
        renderGen();
      }).catch(() => { GEN.srv = false; clearInterval(GEN.poll); renderSrv(); renderGen(); });
    }, 1500);
  }
  function genStart() {
    GEN.err = "";
    GEN.armando = true; renderGen();
    designJSONAsync().then((body) => { GEN.armando = false; return genFetch("/api/generar", { method: "POST", headers: { "Content-Type": "application/json" }, body }, 15000); },
      (err) => { GEN.armando = false; const e = new Error("No se pudo armar el JSON de diseño: " + err.message); throw e; })
      .then((j) => { GEN.job = j; GEN.ver = null; GEN.verId = ""; genPoll(); renderGen(); })
      .catch((err) => { GEN.err = err.message; if (err.data && err.data.trabajo) { GEN.job = err.data.trabajo; genPoll(); } renderGen(); });
  }
  function genAbrir(id) {
    GEN.err = "";
    genFetch("/api/salida?id=" + encodeURIComponent(id), null, 60000).then((ix) => { GEN.ver = ix; GEN.verId = id; renderGen(); const r = $("#plVer"); if (r && r.scrollIntoView) r.scrollIntoView({ block: "nearest" }); })
      .catch((err) => { GEN.err = "No se pudo abrir la generación " + id + ": " + err.message; renderGen(); });
  }
  /* botón, avance y resultado */
  function renderGen() {
    const el = $("#plGen"); if (!el) return;
    const s = GEN.srv, jb = GEN.job, busy = !!(jb && jb.estado === "en_curso");
    let h = `<h3>Generar planos con los parámetros actuales</h3>
      <div class="btns"><button class="pri" id="bGen"${busy || GEN.armando || !A || !s ? " disabled" : ""}>Generar planos</button></div>${GEN.armando ? `<div class="busy" id="genArm">Armando el JSON de diseño (con el bloque «bx») en segundo plano…</div>` : ""}`;
    if (!s) h += `<div class="note">${s === null ? "Comprobando el generador local…" : "Requiere el generador local activo (vea las instrucciones arriba)."}</div>`;
    else h += `<div class="note">Tarda unos 4 a 6 minutos: modelo 3D, láminas PDF y DXF, despiece y controles de calidad.</div>`;
    if (GEN.err) h += `<div class="msg error">${esc(GEN.err)}</div>`;
    if (jb) {
      const pc = Math.round(100 * (jb.progreso || 0));
      h += `<div class="kv" style="margin-top:8px"><span>Trabajo</span><span>${esc(jb.id)}</span><span>Estado</span><span id="genJob" data-estado="${esc(jb.estado)}">${esc({ en_curso: "en curso", listo: "terminado", error: "error" }[jb.estado] || jb.estado)}${jb.duracion_s != null ? ` · ${fmt(jb.duracion_s, 3)} s` : ""}</span></div>`;
      if (busy) h += `<div class="prog"><i style="width:${pc}%"></i></div><div class="busy" id="genFase">${esc(jb.fase || "")} · ${pc} % (estimado)</div>`;
      if (jb.estado === "error") h += `<div class="msg error"><b>El generador terminó con error${jb.codigo != null ? ` (código ${esc(jb.codigo)})` : ""}:</b><pre>${esc(jb.mensaje || "")}</pre></div>`;
      if (jb.log && jb.log.length) h += `<details${busy ? " open" : ""}><summary>Registro del generador (${jb.log.length} líneas)</summary><pre class="log" id="genLog">${esc(jb.log.join("\n"))}</pre></details>`;
    }
    if (GEN.ver) {
      const ix = GEN.ver, dif = ix.P ? plDiff(P, ix.P) : null, err = jb && jb.id === GEN.verId && jb.estado === "error";
      h += `<div id="plVer" data-id="${esc(GEN.verId)}">` + (err ? `<div class="msg warn">Se emitieron archivos, pero no pasaron todos los controles: revíselos antes de usarlos.</div>` : `<div class="msg ok">Juego <b>${esc(GEN.verId)}</b>: ${ix.laminas.length} láminas${ix.interfaz ? " · " + esc(ix.interfaz) : ""}${ix.madera ? " · cubierta de madera" : ""}.</div>`)
        + (dif && dif.length ? `<div class="msg warn" id="plVerDif">Este juego no corresponde a los parámetros actuales (difiere en ${dif.length}: ${esc(dif.slice(0, 8).join(", "))}${dif.length > 8 ? "…" : ""}).</div>` : "")
        + plCards(ix) + `</div>`;
    }
    const lg = $("#genLog"), atEnd = !lg || lg.scrollTop + lg.clientHeight >= lg.scrollHeight - 4;
    el.innerHTML = h;
    const lg2 = $("#genLog"); if (lg2 && atEnd) lg2.scrollTop = lg2.scrollHeight;
    const bg = $("#bGen"); if (bg) bg.onclick = genStart;
  }
  /* historial de salidas/ */
  function renderHist() {
    const el = $("#plHist"); if (!el) return;
    let h = `<h3>Generaciones anteriores (salidas/)</h3>`;
    if (!GEN.srv) h += `<div class="note">Disponible con el generador local activo.</div>`;
    else if (GEN.hist === null) h += `<div class="note">Leyendo salidas/…</div>`;
    else if (!GEN.hist.length) h += `<div class="note" id="plHistVacio">Todavía no hay planos generados.</div>`;
    else h += `<div class="scroll"><table id="plHistTab"><tr><th>Generación</th><th>Alternativa</th><th class="n">Láminas</th><th>Parámetros</th><th></th></tr>
      ${GEN.hist.map((x) => { const d = x.P ? plDiff(P, x.P).length : -1; return `<tr data-id="${esc(x.id)}"><td class="form">${esc(x.id)}</td><td>${esc(x.interfaz || x.alternativa || "")}${x.madera ? " · madera" : ""}</td><td class="n">${x.laminas != null ? x.laminas : "—"}</td>
        <td>${d === 0 ? `<span class="st st-ok">= actuales</span>` : d > 0 ? `<span class="st st-info">difiere en ${d}</span>` : "—"}</td><td><button data-abrir="${esc(x.id)}"${GEN.verId === x.id ? " class=\"pri\"" : ""}>Abrir</button></td></tr>`; }).join("")}</table></div>
      <div class="btns"><button id="bHist">Actualizar lista</button></div>`;
    el.innerHTML = h;
    el.querySelectorAll("button[data-abrir]").forEach((b) => { b.onclick = () => genAbrir(b.dataset.abrir); });
    const bh = $("#bHist"); if (bh) bh.onclick = genHist;
  }

  /* render perezoso: recalc() dibuja los badges y la pestaña activa; las demás quedan «sucias» y se dibujan al abrirlas (showTab).
     Temperatura y Tapones ya se dibujan solo si están activas y al abrirlas (showTab), con su propio caché. */
  /* GIF del movimiento (valores por defecto) incrustado al construir: se decodifica solo al abrir «Cinemática» */
  let simGifUrl = null;
  function addSimGif() {
    const el = document.querySelector('section[data-t="cinem"]'), src = document.getElementById("TT_SIMGIF");
    if (!el || !src) return;
    if (!simGifUrl) { try { const b = atob(src.textContent.trim()), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); simGifUrl = URL.createObjectURL(new Blob([u], { type: "image/gif" })); } catch (e) { return; } }
    const esDef = Object.keys(DEF).every((k) => P[k] === DEF[k] || (P[k] !== P[k] && DEF[k] !== DEF[k]));
    const card = document.createElement("div"); card.className = "card sim-gif"; card.id = "kinGif"; card.style.marginBottom = "12px";
    card.innerHTML = `<h3>Movimiento cinemático: empuje, retorno y reenganche (2 carreras, giro antihorario, ×2)</h3>
      <div class="note">Cada carrera gira la mesa un paso de pasadores (360°/N_pin); en el retorno el bloque-uña monta el pasador siguiente por la rampa del dorso y cae detrás de él, y la carrera siguiente parte con el cilindro en la misma posición angular que la primera. GIF generado con la simulación de esta herramienta${esDef ? "" : " — <b>con los parámetros por defecto, no con los actuales</b>; para los actuales use «Simulación» → «Exportar GIF»"}.</div>
      <img src="${simGifUrl}" alt="Simulación del movimiento de la tornamesa: empuje, retorno y reenganche" loading="lazy" decoding="async">`;
    el.prepend(card);
  }
  const RENDER = { resumen: renderResumen, modelo: renderModelo, giro: renderGiro, cinem: () => { renderCinem(); addSimGif(); }, comp: renderComp, verif: renderVerif, fea: renderFEA, bx: renderBX, masa: renderMasa, agentes: renderAgentes, planos: () => { renderPkg(); renderPlanos(); } };
  function renderTab(t) { if (!dirty.has(t)) return; dirty.delete(t); RENDER[t](); }
  function renderAll() {
    renderBadges();
    Object.keys(RENDER).forEach((t) => dirty.add(t));
    renderTab(cur); renderTemp();
  }
  buildForm(); recalc();
})();
