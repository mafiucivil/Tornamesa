(function () {
  const DEF = defaults();
  const KEY = "tt300b-params-v1";
  let P = Object.assign({}, DEF);
  try { const s = JSON.parse(localStorage.getItem(KEY) || "null"); if (s) for (const k in s) if (k in DEF && typeof s[k] === typeof DEF[k]) P[k] = s[k]; } catch (e) { /* sin almacenamiento */ }
  let R = null, V = [], F = {}, plate = "bot", field = "vm", deformed = 0, timer = null, hl = [], g3 = null;
  const $ = (id) => document.getElementById(id);
  const dlP = window.claude && window.claude.use ? window.claude.use("downloads").catch(() => null) : Promise.resolve(null);

  function pal(print) {
    if (print) return { ink: "#000000", mute: "#444444", line: "#8a8a8a", grid: "#dddddd", bg: "#ffffff", accent: "#1f4fbf", force: "#b3361f", react: "#0d776a", good: "#2e7a33", warn: "#a8700f", bad: "#c22a2a", fill: "#eef0ee", fill2: "#dcdfdc", cyl: "#d6dceb", shoe: "#efe2cc", pawl: "#f3d49b", band: "rgba(36,83,196,0.08)", paper: "#ffffff", font: "Helvetica, Arial, sans-serif" };
    const cs = getComputedStyle(document.documentElement), g = (n) => cs.getPropertyValue("--" + n).trim();
    return { ink: g("ink"), mute: g("mute"), line: g("line"), grid: g("grid"), bg: g("panel"), accent: g("accent"), force: g("force"), react: g("react"), good: g("good"), warn: g("warn"), bad: g("bad"), fill: g("fill"), fill2: g("fill2"), cyl: g("cyl"), shoe: g("shoe"), pawl: g("pawl"), band: g("band"), paper: "#ffffff", font: "IBM Plex Sans, Segoe UI, sans-serif" };
  }
  const stOf = (v) => (v.kind === "pass" ? (v.fu <= 1 ? "ok" : "no") : v.fu <= 0.9 ? "ok" : v.fu <= 1 ? "wa" : "no");
  const stTxt = { ok: "OK", wa: "Monitoreo", no: "No cumple" };
  function toast(msg) { const t = $("toast"); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), 3200); }

  /* ---------------- formulario ---------------- */
  function buildForm() {
    const f = $("pform"); let html = "";
    PARAM_GROUPS.forEach((g, gi) => {
      html += `<details class="grp" ${gi < 4 && window.innerWidth > 980 ? "open" : ""}><summary>${g.t}</summary><div class="grp-body">`;
      for (const [id, lab, unit, dv, step] of g.items) {
        const isTxt = typeof dv === "string";
        html += `<div class="prow" data-row="${id}"><label for="p_${id}">${lab}<small>${unit} · Rev.0: ${isTxt ? dv : nf(dv, step && step < 1 ? (step < 0.01 ? 3 : 2) : 0)}</small></label>` +
          `<input id="p_${id}" name="${id}" ${isTxt ? 'type="text" class="txt"' : `type="number" step="${step}" inputmode="decimal"`} value="${P[id]}"></div>`;
      }
      html += "</div></details>";
    });
    f.innerHTML = html;
    f.addEventListener("input", (ev) => {
      const el = ev.target; if (!el.name) return;
      const dv = DEF[el.name];
      if (typeof dv === "string") P[el.name] = el.value;
      else { const v = parseFloat(String(el.value).replace(",", ".")); if (!isFinite(v)) return; P[el.name] = v; }
      markChanged(); schedule();
    });
    f.addEventListener("submit", (e) => e.preventDefault());
    f.addEventListener("focusin", (ev) => { if (ev.target.name) focusParam(ev.target.name); });
    markChanged();
  }
  function markChanged() {
    let n = 0;
    for (const k in DEF) { const row = document.querySelector(`[data-row="${k}"]`); const ch = String(P[k]).replace(/\s/g, "") !== String(DEF[k]).replace(/\s/g, ""); if (ch) n++; if (row) row.classList.toggle("chg", ch); }
    const w = $("issuedWarn"); w.hidden = n === 0; w.textContent = `Hay ${n} parámetro(s) distinto(s) del diseño emitido: los planos Rev. 0 no los reflejan. Use el plano paramétrico para documentar esta variante.`;
    try { localStorage.setItem(KEY, JSON.stringify(P)); } catch (e) { /* sin almacenamiento */ }
  }
  $("reset").addEventListener("click", () => { P = Object.assign({}, DEF); for (const k in DEF) { const el = $("p_" + k); if (el) el.value = DEF[k]; } markChanged(); recompute(); toast("Valores de diseño Rev. 0 restablecidos"); });

  function validate() {
    const errs = [];
    if (P.N_rib < 3 || P.N_rib > 36) errs.push("N° de nervios entre 3 y 36");
    if (P.N_bar < 8 || P.N_bar > 120) errs.push("N° de barras entre 8 y 120");
    if (P.R_bar + P.D_bar / 2 >= P.D_disc / 2) errs.push("Las barras deben quedar dentro del disco");
    if (P.D_hub >= P.D_disc) errs.push("Cubo mayor que el disco");
    if (P.D_bore >= P.D_hub) errs.push("Buje mayor que el cubo");
    if (P.weld_S <= 3) errs.push("Bisel de soldadura > 3 mm");
    for (const k in DEF) if (typeof DEF[k] === "number" && !(P[k] > 0) && k !== "e") errs.push(`${k} debe ser positivo`);
    return errs;
  }
  function schedule() { document.querySelector("main").classList.add("busy"); clearTimeout(timer); timer = setTimeout(recompute, 380); }

  function recompute() {
    document.querySelector("main").classList.remove("busy");
    const errs = validate();
    if (errs.length) { $("verdict").className = "verdict no"; $("verdict").innerHTML = `<strong>Parámetros inválidos</strong><span>${errs.join(" · ")}</span>`; return; }
    R = compute(P); F = {};
    try { F.bot = runDisc(P, "bot"); F.top = runDisc(P, "top"); } catch (e) { F.discErr = e.message; }
    try { F.pawl = runPawl(P, R); } catch (e) { F.pawlErr = e.message; }
    V = verifs(R, F);
    render();
  }

  /* ---------------- render ---------------- */
  function render() {
    const C = pal(false), d = R.d, worst = V.filter((v) => v.kind !== "pass").reduce((a, b) => (b.fu > a.fu ? b : a));
    const fails = V.filter((v) => stOf(v) === "no"), mons = V.filter((v) => stOf(v) === "wa"), dry = R.cases[3];
    // veredicto
    let cls = "ok", head = "Gira con certeza en el rango acero/acero engrasado", body = `Cada cilindro necesita ${nf(d.Fc)} kN (${nf(d.p)} bar) con μ = ${nf(P.mu, 2)} y r = ${nf(P.r_eff, 2)} m; dispone de ${nf(R.Fmax)} kN a ${nf(P.p_relief)} bar → FS = ${nf(d.FS, 2)}. Elementos: FU máx ${nf(worst.fu, 2)} (${worst.grp}).`;
    if (d.FS < 1) { cls = "no"; head = "El accionamiento NO vence la fricción de diseño"; body = `Se requieren ${nf(d.Fc)} kN por cilindro (${nf(d.p)} bar) y el alivio entrega ${nf(R.Fmax)} kN.`; }
    else if (fails.length) { cls = "no"; head = `${fails.length} verificación(es) no cumplen`; body = fails.map((v) => `${v.grp}: ${v.el} (FU ${nf(v.fu, 2)})`).join(" · "); }
    else if (d.FS < 1.25 || mons.length) { cls = "wa"; head = "Cumple con margen reducido"; body = (d.FS < 1.25 ? `FS del accionamiento ${nf(d.FS, 2)} < 1,25. ` : "") + mons.map((v) => `${v.grp}: ${v.el} (FU ${nf(v.fu, 2)})`).join(" · "); }
    $("verdict").className = "verdict " + cls;
    $("verdict").innerHTML = `<strong>${head}</strong><span>${body}</span><span class="note">Acero seco (μ ${nf(P.mu_dry, 2)}): ${dry.FS < 1 ? `no gira, requiere ${nf(dry.p)} bar &gt; ${nf(P.p_relief)} bar. Lubricación obligatoria.` : `gira con FS ${nf(dry.FS, 2)}.`}</span>`;
    // chips
    const chip = (c, t, v) => `<span class="chip ${c}"><span class="dot"></span>${t} <b>${v}</b></span>`;
    $("chips").innerHTML = chip(d.FS >= 1.25 ? "ok" : d.FS >= 1 ? "wa" : "no", "FS accionamiento", nf(d.FS, 2)) + chip(worst.fu <= 0.9 ? "ok" : worst.fu <= 1 ? "wa" : "no", "FU máx", nf(worst.fu, 2)) +
      chip(dry.FS < 1 ? "wa" : "ok", "Acero seco", dry.FS < 1 ? "no gira" : "gira") + (F.bot ? chip(Math.abs(F.bot.Fapp - F.bot.Rsum) / F.bot.Fapp < 1e-3 ? "ok" : "no", "FEA equilibrio", "Σ OK") : chip("no", "FEA", "error"));
    // KPIs
    const k = (c, l, v, s) => `<div class="kpi ${c}"><span class="l">${l}</span><span class="v">${v}</span><span class="s">${s}</span></div>`;
    const plMax = F.bot ? Math.max(F.bot.vmMax, F.top.vmMax) : NaN;
    $("kpis").innerHTML =
      k(d.FS >= 1.25 ? "ok" : d.FS >= 1 ? "wa" : "no", "Fuerza por cilindro", `${nf(d.Fc)} kN`, `${nf(d.tf, 1)} tf · ${nf(d.p)} bar (diseño)`) +
      k("", "Capacidad por cilindro", `${nf(R.Fmax)} kN`, `Ø${nf(P.D_piston)} a ${nf(P.p_relief)} bar · FS ${nf(d.FS, 2)}`) +
      k("", "Fricción máx. vencible <span class=\"nt\">μ</span>", nf(R.muMax(R.r_eff, P.p_relief), 3), `r ${nf(R.r_eff, 2)} m · ${nf(R.muMax(R.r_max, P.p_relief), 3)} con r ${nf(R.r_max, 2)}`) +
      k("", "Par resistente", `${nf(d.T)} kN·m`, `N = ${nf(R.N)} kN · 2 × ${nf(d.Fb)} kN × ${nf(R.a / 1000, 3)} m`) +
      k(worst.fu <= 0.9 ? "ok" : worst.fu <= 1 ? "wa" : "no", "FU máximo", nf(worst.fu, 2), `${worst.grp}: ${worst.el}`) +
      k(plMax <= 0.6 * P.Fy ? "ok" : "no", "Placas 4a/4b (FEA)", `${nf(plMax, 1)} MPa`, `σvm máx · admisible ${nf(0.6 * P.Fy)} MPa`);
    // casos
    $("casesT").innerHTML = `<table class="t"><thead><tr><th>Caso</th><th class="n"><span class="nt">μ</span></th><th class="n"><span class="nt">r m</span></th><th class="n">T kN·m</th><th class="n">F barra</th><th class="n">F cil kN</th><th class="n">p bar</th><th class="n">FS</th><th></th></tr></thead><tbody>` +
      R.cases.map((c) => { const s = c.FS >= 1.25 ? "ok" : c.FS >= 1 ? "wa" : "no"; return `<tr class="${c.key === "dis" ? "hl" : ""}"><td>${c.name}</td><td class="n">${nf(c.mu, 2)}</td><td class="n">${nf(c.r, 3)}</td><td class="n">${nf(c.T)}</td><td class="n">${nf(c.Fb)}</td><td class="n">${nf(c.Fc)}</td><td class="n">${nf(c.p)}</td><td class="n">${nf(c.FS, 2)}</td><td><span class="st ${s}">${c.FS >= 1.25 ? "Gira" : c.FS >= 1 ? "Al límite" : "No gira"}</span></td></tr>`; }).join("") + "</tbody></table>";
    $("mumaxT").textContent = `μ máximo que vencen los cilindros: ${nf(R.muMax(R.r_u, P.p_relief), 3)} (r ${nf(R.r_u, 3)}) · ${nf(R.muMax(R.r_eff, P.p_relief), 3)} (r ${nf(R.r_eff, 2)}) · ${nf(R.muMax(R.r_max, P.p_relief), 3)} (r ${nf(R.r_max, 2)}) a ${nf(P.p_relief)} bar; a ${nf(P.p_alarm)} bar: ${nf(R.muMax(R.r_eff, P.p_alarm), 3)} (r ${nf(R.r_eff, 2)}).`;
    const Tf = P.mu * R.N * P.r_eff;
    $("eqs").innerHTML = [
      `N = W + W_disco = ${nf(R.W, 1)} + ${nf(R.Wd, 2)} = ${nf(R.N, 1)} kN`,
      `T_f = μ·N·r = ${nf(P.mu, 2)} × ${nf(R.N, 1)} × ${nf(P.r_eff, 3)} = ${nf(Tf, 1)} kN·m`,
      `T_piv = μb·H·r = ${nf(P.mu_piv, 2)} × ${nf(P.H_frac * R.W, 1)} × ${nf(P.D_piv / 2000, 3)} = ${nf(R.Tpiv, 2)} kN·m`,
      `a = R_b·cos(180°/N_b) = ${nf(P.R_bar)} × cos ${nf(180 / P.N_bar, 2)}° = ${nf(R.a, 1)} mm`,
      `F_barra = T/(2a) = ${nf(d.T, 1)} / (2 × ${nf(R.a / 1000, 4)}) = ${nf(d.Fb, 1)} kN`,
      `K = (1 + 2·μg·Δ/Lg)/ηc = (1 + 2 × ${nf(P.mu_g, 2)} × ${nf(R.Delta, 1)}/${nf(P.Lg)}) / ${nf(P.eta_c, 2)} = ${nf(R.K, 3)}`,
      `F_cil = K·F_barra = ${nf(R.K, 3)} × ${nf(d.Fb, 1)} = ${nf(d.Fc, 1)} kN (${nf(d.tf, 1)} tf)`,
      `p = F_cil/A = ${nf(d.Fc * 1e3)} N / ${nf(R.A)} mm² = ${nf(d.p)} bar`,
      `FS = A·p_alivio / F_cil = ${nf(R.Fmax, 1)} / ${nf(d.Fc, 1)} = ${nf(d.FS, 2)}`,
    ].map((t) => `<span>${t}</span>`).join("");
    $("hyps").innerHTML = [
      `Carga WLL ${nf(P.W_tf)} tf con CG a e ≤ ${nf(P.e)} mm del pivote; carga solo sobre parrilla de Ø${nf(P.D_load)}.`,
      `Interfaz plana anular acero/acero R ${nf(P.D_disc / 2)} / r ${nf(P.D_bore / 2)} mm con grasa grafitada NLGI 2 (≥10 % grafito). μ estático de diseño ${nf(P.mu, 2)}: límite superior de 0,10–0,20 para acero engrasado.`,
      `Radio efectivo: uniforme ${nf(R.r_u, 3)} m. La distribución lineal por excentricidad no cambia el par (∫x·r dA = 0); el diseño usa ${nf(P.r_eff, 2)} m para cubrir la concentración de presión hacia el borde por flexión del disco.`,
      `Dos cilindros simultáneos (válvula de bloqueo): las fuerzas sobre las barras forman un par puro; el pivote no recibe resultante en operación normal.`,
      `Pérdidas por fricción carro/guía (μg ${nf(P.mu_g, 2)}) debidas a la excentricidad Δ entre eje del cilindro y barra, y rendimiento de sellos ηc ${nf(P.eta_c, 2)}.`,
      `La cadena de empuje (barra, soldadura, trinquete, guía, ménsula, pasador, vástago) se verifica a la fuerza de calado ${nf(R.Fmax)} kN: si el disco se traba, abre la válvula antes de que falle un elemento.`,
      `Placas del disco por FEA (Mindlin MITC4): almas, nervios y barras como apoyos rígidos; plancha inferior con q_max ${nf(R.q_max, 2)} MPa uniforme (conservador).`,
    ].map((t) => `<li>${t}</li>`).join("");
    // cilindros
    $("dgPlan").innerHTML = dgPlan(R, C);
    $("dgStroke").innerHTML = dgStroke(R, C);
    $("dgMu").innerHTML = dgMu(R, C);
    $("dgBreak").innerHTML = dgBreak(R, C);
    const at = (c, t) => { const a = P.R_bar * Math.cos(t), Kt = (1 + 2 * P.mu_g * (P.X_cyl - a) / P.Lg) / P.eta_c; return Kt * c.T / (2 * a / 1000); };
    const posn = [["Recorrido libre (0–" + nf(P.free) + " mm)", null], [`Toma la barra (θ = −${nf(180 / P.N_bar, 1)}°)`, -R.th], ["Centro (θ = 0°)", 0], [`Suelta la barra (θ = +${nf(180 / P.N_bar, 1)}°)`, R.th]];
    const cs3 = R.cases.slice(0, 3);
    $("pistonT").innerHTML = `<table class="t"><thead><tr><th>Posición en la carrera</th>${cs3.map((c) => `<th class="n">${c.name.split(" – ")[0]}<br>kN / bar</th>`).join("")}</tr></thead><tbody>` +
      posn.map(([n, t]) => `<tr class="${t === -R.th ? "hl" : ""}"><td>${n}</td>${cs3.map((c) => { if (t === null) return `<td class="n">≈ 0 / –</td>`; const f = at(c, t); return `<td class="n">${nf(f)} / ${nf(f * 1e3 / R.A * 10)}</td>`; }).join("")}</tr>`).join("") +
      `<tr><td>Alarma (detener y relubricar)</td><td class="n" colspan="3">${nf(R.Falarm)} kN / ${nf(P.p_alarm)} bar</td></tr>` +
      `<tr><td>Alivio = fuerza de calado</td><td class="n" colspan="3">${nf(R.Fmax)} kN / ${nf(P.p_relief)} bar</td></tr></tbody></table>` +
      `<h4>Reacciones por cilindro</h4><table class="t"><thead><tr><th>Elemento</th><th class="n">Diseño kN</th><th class="n">Calado kN</th></tr></thead><tbody>` +
      [["Ménsula pos 2 (pasador Ø" + P.D_pin + ")", d.Fc, R.Fmax], ["Pasador: cada plano de corte", d.Fc / 2, R.Fmax / 2], ["Barra 4f (trinquete)", d.Fb, R.Fmax / R.K], ["Guía pos 22, cada reacción R", d.Fb * R.Delta / P.Lg, R.Fmax * R.Delta / P.Lg], ["Pivote (2 cilindros en par)", 0, 0], ["Pivote (accidental, 1 cilindro – bloqueado por válvula)", d.Fc, R.Fmax]]
        .map(([n, a, b]) => `<tr><td>${n}</td><td class="n">${nf(a)}</td><td class="n">${nf(b)}</td></tr>`).join("") + "</tbody></table>";
    // diagramas
    $("dgShoe").innerHTML = dgShoe(R, C);
    $("dgBar").innerHTML = dgBar(R, C);
    $("dgPin").innerHTML = dgPin(R, C);
    $("pathT").innerHTML = `<table class="t"><thead><tr><th>Tramo del camino de carga</th><th class="n">Diseño</th><th class="n">Calado</th></tr></thead><tbody>` +
      [["Presión en cilindro", `${nf(d.p)} bar`, `${nf(P.p_relief)} bar`], ["Vástago → pasador del carro", `${nf(d.Fc)} kN`, `${nf(R.Fmax)} kN`], ["Carro → guía (2 reacciones)", `${nf(d.Fb * R.Delta / P.Lg)} kN c/u`, `${nf(R.Fmax * R.Delta / P.Lg)} kN c/u`],
        ["Trinquete → barra 4f", `${nf(d.Fb)} kN`, `${nf(R.Fmax / R.K)} kN`], ["Barra → planchas 4a/4b (aplast.)", `${nf(d.Fb / 2)} kN c/u`, `${nf(R.Fmax / 2)} kN c/u`], ["Par motor sobre el disco", `${nf(d.T)} kN·m`, `${nf(R.Fmax / R.K * 2 * R.a / 1000)} kN·m`],
        ["Cuerpo cilindro → ménsula → placa base", `${nf(d.Fc)} kN`, `${nf(R.Fmax)} kN`], ["Interfaz de giro (fricción a vencer)", `${nf(d.Tf)} kN·m`, "–"]]
        .map(([a, b, c]) => `<tr><td>${a}</td><td class="n">${b}</td><td class="n">${c}</td></tr>`).join("") + "</tbody></table>" +
      `<p class="note">En el calado el pistón no vence la fricción: el disco no gira y toda la fuerza del alivio queda en la cadena de empuje. Por eso los elementos se verifican a ese valor.</p>`;
    // verificaciones
    $("verT").innerHTML = `<table class="t"><thead><tr><th>Grupo</th><th>Elemento</th><th>Fórmula</th><th class="n">Demanda</th><th class="n">Capacidad</th><th>FU</th><th>Estado</th><th>Referencia</th></tr></thead><tbody>` +
      V.map((v) => { const s = stOf(v), c = s === "ok" ? "var(--good)" : s === "wa" ? "var(--warn)" : "var(--bad)"; const dd = Math.abs(v.dem) < 20 ? 2 : 1;
        return `<tr><td>${v.grp}</td><td>${v.el}</td><td class="f">${v.formula}</td><td class="n">${nf(v.dem, dd)} ${v.unit}</td><td class="n">${nf(v.cap, Math.abs(v.cap) < 20 ? 2 : 0)} ${v.unit}</td><td><div class="fu"><span class="bar"><i style="width:${Math.min(100, v.fu * 100).toFixed(1)}%;background:${c}"></i></span><b class="n" style="font-family:var(--f-mono)">${nf(v.fu, 2)}</b></div></td><td><span class="st ${s}">${v.kind === "pass" ? (s === "ok" ? "Cumple" : "No cumple") : stTxt[s]}</span></td><td class="note">${v.ref}</td></tr>`; }).join("") + "</tbody></table>";
    renderFEA();
    renderSheet();
    renderGeo(true);
  }

  /* ---------------- geometría ---------------- */
  const LABEL = {}; for (const g of PARAM_GROUPS) for (const it of g.items) LABEL[it[0]] = it[1];
  function focusParam(name) {
    hl = PART_OF[name] || [];
    $("editing").innerHTML = hl.length ? `Editando <b>${LABEL[name]}</b> → resaltado: ${hl.map((p) => PART_NAME[p]).join(", ")}` : `Editando <b>${LABEL[name]}</b> (parámetro de material o de cálculo, sin elemento asociado)`;
    renderGeo(false);
  }
  function renderGeo(rebuild) {
    if (!R) return;
    const C = pal(false);
    $("gPlan").innerHTML = geoPlan(R, C, hl);
    $("gElev").innerHTML = geoElev(R, C, hl);
    $("gEdge").innerHTML = geoEdge(R, C, hl);
    if (!g3) { g3 = new Geo3D($("g3d")); if (!g3.ok) $("g3note").textContent = "Este navegador no permite WebGL: se muestran solo las vistas 2D."; }
    if (g3.ok) { if (rebuild) g3.build(R, C); g3.highlight(hl); }
  }
  document.querySelectorAll("[data-v3]").forEach((b) => b.addEventListener("click", () => { document.querySelectorAll("[data-v3]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); g3 && g3.ok && g3.view(b.dataset.v3); }));
  document.querySelectorAll("[data-top]").forEach((b) => b.addEventListener("click", () => { document.querySelectorAll("[data-top]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); g3 && g3.ok && g3.setTop(b.dataset.top); }));

  /* ---------------- FEA ---------------- */
  const STOPS = [[0, [29, 63, 143]], [0.2, [44, 127, 184]], [0.4, [65, 182, 164]], [0.6, [166, 217, 106]], [0.75, [253, 211, 77]], [0.88, [240, 138, 53]], [1, [198, 40, 40]]];
  function cmap(t) {
    t = Math.max(0, Math.min(1, t));
    for (let i = 1; i < STOPS.length; i++) if (t <= STOPS[i][0]) { const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i], u = (t - a) / (b - a); return `rgb(${ca.map((v, k) => Math.round(v + (cb[k] - v) * u)).join(",")})`; }
    return "rgb(198,40,40)";
  }
  const rampCSS = "linear-gradient(90deg," + STOPS.map(([t, c]) => `rgb(${c.join(",")}) ${t * 100}%`).join(",") + ")";
  function elemVal(f, e, fld) { if (fld === "vm") return f.res.el[e].vm; const en = f.model.elems[e]; return en.reduce((s, k) => s + Math.abs(f.res.w[k]), 0) / 4; }
  function drawDisc(cv, f, fld, C) {
    const ctx = cv.getContext("2d"), W = cv.width, H = cv.height, m = f.model, Pp = P, Rd = Pp.D_disc / 2, sc = (Math.min(W, H) / 2 - 40) / Rd, cx = W / 2, cy = H / 2 + 10;
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    let vmax = 0; const vals = new Float64Array(m.elems.length);
    for (let e = 0; e < m.elems.length; e++) { vals[e] = elemVal(f, e, fld); vmax = Math.max(vmax, vals[e]); }
    vmax = vmax || 1;
    for (let s = 0; s < Pp.N_rib; s++) {
      const ca = Math.cos(s * m.alpha), sa = Math.sin(s * m.alpha);
      for (let e = 0; e < m.elems.length; e++) {
        ctx.beginPath();
        m.elems[e].forEach((k, i) => { const [x, y] = m.nodes[k], X = cx + (x * ca - y * sa) * sc, Y = cy - (x * sa + y * ca) * sc; i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); });
        ctx.closePath(); ctx.fillStyle = cmap(vals[e] / vmax); ctx.fill(); ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = 0.6; ctx.stroke();
      }
    }
    ctx.strokeStyle = C.ink; ctx.lineWidth = 1.4; ctx.globalAlpha = 0.85;
    const circ = (r, w, dash) => { ctx.setLineDash(dash || []); ctx.lineWidth = w; ctx.beginPath(); ctx.arc(cx, cy, r * sc, 0, 2 * Math.PI); ctx.stroke(); };
    circ(Rd, 2); circ(Pp.D_hub / 2, 1.4); m.rings.forEach((r) => circ(r, 1.2, [6, 4]));
    if (m.which === "top") circ(Pp.D_load / 2, 1, [2, 4]);
    ctx.setLineDash([6, 4]);
    for (let s = 0; s < Pp.N_rib; s++) { const a = s * m.alpha; ctx.beginPath(); ctx.moveTo(cx + Pp.D_hub / 2 * Math.cos(a) * sc, cy - Pp.D_hub / 2 * Math.sin(a) * sc); ctx.lineTo(cx + Pp.R_rib * Math.cos(a) * sc, cy - Pp.R_rib * Math.sin(a) * sc); ctx.stroke(); }
    ctx.setLineDash([]);
    for (let i = 0; i < Pp.N_bar; i++) { const a = Math.PI / Pp.N_bar + 2 * Math.PI * i / Pp.N_bar; ctx.beginPath(); ctx.arc(cx + Pp.R_bar * Math.cos(a) * sc, cy - Pp.R_bar * Math.sin(a) * sc, Pp.D_bar / 2 * sc, 0, 2 * Math.PI); ctx.stroke(); }
    ctx.globalAlpha = 1;
    if (fld === "vm") { const [r, t] = f.maxAt, a = t * Math.PI / 180, X = cx + r * Math.cos(a) * sc, Y = cy - r * Math.sin(a) * sc; ctx.strokeStyle = C.ink; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(X, Y, 9, 0, 2 * Math.PI); ctx.stroke(); ctx.fillStyle = C.ink; ctx.font = `600 18px ${C.font}`; ctx.fillText(`máx ${nf(f.vmMax, 1)} MPa`, X + 12, Y - 10); }
    ctx.fillStyle = C.ink; ctx.font = `600 20px ${C.font}`; ctx.textAlign = "left";
    ctx.fillText(`${m.which === "bot" ? "Plancha inferior 4b" : "Plancha superior 4a"} · ${fld === "vm" ? "σ von Mises (MPa)" : "flecha relativa |w| (mm)"}`, 14, 26);
    ctx.font = `15px ${C.font}`; ctx.fillStyle = C.mute;
    ctx.fillText(`q = ${nf(m.which === "bot" ? R.q_max : R.q_top, 2)} MPa ${m.which === "bot" ? "(contacto máx., uniforme)" : `en Ø${nf(Pp.D_load)}`} · t = ${nf(m.t)} mm`, 14, 48);
    cv._map = { cx, cy, sc, f, fld, vmax };
    return vmax;
  }
  function drawPawl(cv, f, C, defm) {
    const ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    const sc = Math.min((W - 140) / (f.L + 70), (H - 150) / (f.b + 60)), ox = 70 + 45 * sc, oy = H - 70 - 25 * sc;
    const X = (x) => ox + x * sc, Y = (y) => oy - y * sc;
    const ds = defm ? 0.06 * f.L / Math.max(f.dmax, 1e-9) : 0;
    ctx.fillStyle = C.fill2; ctx.fillRect(X(f.Xm), Y(f.b + 20), (f.L + 30 - f.Xm) * sc, (f.b + 40) * sc);
    ctx.fillStyle = C.bg; ctx.fillRect(X(f.Xm), Y(f.b + 0.5), (f.L + 31 - f.Xm) * sc, (f.b + 1) * sc);
    ctx.fillStyle = C.mute; ctx.font = `14px ${C.font}`; ctx.fillText("carro pos 10 (alojamiento)", X(f.Xm) + 6, Y(f.b + 20) + 16);
    let vmax = 0; for (const e of f.res.el) vmax = Math.max(vmax, e.vm);
    const vcap = Math.min(vmax, (P.Fy_pawl / P.Nd) * 1.25);
    f.elems.forEach((en, i) => {
      ctx.beginPath();
      en.forEach((k, j) => { const x = f.nodes[k][0] + ds * f.res.u[2 * k], y = f.nodes[k][1] + ds * f.res.u[2 * k + 1]; j ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y)); });
      ctx.closePath(); ctx.fillStyle = cmap(f.res.el[i].vm / vcap); ctx.fill(); ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = 0.5; ctx.stroke();
    });
    ctx.strokeStyle = C.ink; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.arc(X(f.Xs), Y(f.Ys), (P.D_bar / 2) * sc, 0, 2 * Math.PI); ctx.stroke();
    ctx.fillStyle = C.mute; ctx.fillText(`barra 4f Ø${P.D_bar}`, X(f.Xs) - 30, Y(f.Ys) - (P.D_bar / 2) * sc - 8);
    ctx.setLineDash([6, 4]); ctx.beginPath(); ctx.moveTo(X(f.Xm), Y(-25)); ctx.lineTo(X(f.Xm), Y(f.b + 30)); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.ink; ctx.fillText("boca del carro", X(f.Xm) + 4, Y(-18));
    ctx.fillStyle = C.react;
    for (const k of f.sup) { const [x, y] = f.nodes[k], up = y < 1; ctx.beginPath(); ctx.moveTo(X(x), Y(y)); ctx.lineTo(X(x) - 4, Y(y) + (up ? 8 : -8)); ctx.lineTo(X(x) + 4, Y(y) + (up ? 8 : -8)); ctx.fill(); }
    ctx.strokeStyle = C.force; ctx.fillStyle = C.force; ctx.lineWidth = 2;
    const step = Math.max(1, Math.floor(f.loads.length / 7));
    f.loads.forEach(([k], i) => { if (i % step) return; const [x, y] = f.nodes[k]; ctx.beginPath(); ctx.moveTo(X(x), Y(y) - 30); ctx.lineTo(X(x), Y(y) - 4); ctx.stroke(); ctx.beginPath(); ctx.moveTo(X(x), Y(y)); ctx.lineTo(X(x) - 4, Y(y) - 9); ctx.lineTo(X(x) + 4, Y(y) - 9); ctx.fill(); });
    ctx.fillStyle = C.ink; ctx.font = `600 20px ${C.font}`;
    ctx.fillText(`σ von Mises (MPa) · F = ${nf(R.Fmax)} kN en el asiento R${P.seat_R}${defm ? ` · deformada ×${nf(ds, 0)}` : ""}`, 14, 26);
    ctx.font = `14px ${C.font}`; ctx.fillStyle = C.mute; ctx.fillText(`escala de color saturada en ${nf(vcap)} MPa (1,25 × admisible); picos locales de contacto hasta ${nf(vmax)} MPa`, 14, 46);
    cv._map = { X, Y, sc, ox, oy, f };
    return vcap;
  }
  function renderFEA() {
    const C = pal(false);
    document.querySelectorAll("[data-plate]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.plate === plate)));
    document.querySelectorAll("[data-field]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.field === field)));
    document.querySelectorAll("[data-def]").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.def === deformed)));
    $("ramp1").style.background = rampCSS; $("ramp2").style.background = rampCSS;
    if (F.discErr) { $("feaDiscN").textContent = "Error en el modelo del disco: " + F.discErr; }
    else {
      const f = F[plate], vmax = drawDisc($("cvDisc"), f, field, C);
      $("lgMin").textContent = "0"; $("lgMax").textContent = field === "vm" ? `${nf(vmax, 1)} MPa` : `${nf(vmax, 4)} mm`;
      const row = (n, b, t) => `<tr><td>${n}</td><td class="n">${b}</td><td class="n">${t}</td></tr>`;
      $("feaDiscT").innerHTML = `<table class="t"><thead><tr><th>Resultado</th><th class="n">4b inferior</th><th class="n">4a superior</th></tr></thead><tbody>` +
        row("Presión aplicada", `${nf(R.q_max, 2)} MPa`, `${nf(R.q_top, 2)} MPa`) + row("σvm máx.", `${nf(F.bot.vmMax, 1)} MPa`, `${nf(F.top.vmMax, 1)} MPa`) +
        row("Ubicación (r, θ)", `${nf(F.bot.maxAt[0])} mm, ${nf(F.bot.maxAt[1], 1)}°`, `${nf(F.top.maxAt[0])} mm, ${nf(F.top.maxAt[1], 1)}°`) +
        row("Flecha máx.", `${nf(F.bot.wMax, 3)} mm`, `${nf(F.top.wMax, 3)} mm`) +
        row("Almas 4d", F.bot.ringLine.map((v) => nf(v)).join(" / ") + " N/mm", F.top.ringLine.map((v) => nf(v)).join(" / ") + " N/mm") +
        row("Barras 4f", F.bot.barF.map((v) => nf(v, 1)).join(" / ") + " kN", F.top.barF.map((v) => nf(v, 1)).join(" / ") + " kN") +
        row("Σ carga / Σ reac.", `${nf(F.bot.Fapp, 1)} / ${nf(F.bot.Rsum, 1)} kN`, `${nf(F.top.Fapp, 1)} / ${nf(F.top.Rsum, 1)} kN`) +
        row("Admisible 0,6 Fy", `${nf(0.6 * P.Fy)} MPa`, `${nf(0.6 * P.Fy)} MPa`) + "</tbody></table>";
      $("feaDiscN").textContent = `Modelo: sector de ${nf(360 / P.N_rib, 1)}° entre nervios, ${F.bot.model.elems.length} elementos placa Mindlin MITC4 (${F.bot.res.ndof} GDL, resuelto en ${nf(F.bot.ms + F.top.ms)} ms). Cubo empotrado; almas, nervios y barras como apoyos verticales rígidos; simetría en los bordes del sector; la imagen repite el sector ${P.N_rib} veces. Al tratar almas y barras como apoyos rígidos se obtiene la flexión local de cada paño, que es la que gobierna el espesor; la flexión global del cajón se verifica aparte (FU en la pestaña Verificaciones).`;
    }
    if (F.pawlErr) $("feaPawlN").textContent = "Error en el modelo del trinquete: " + F.pawlErr;
    else {
      const f = F.pawl, vcap = drawPawl($("cvPawl"), f, C, deformed);
      $("lgMin2").textContent = "0"; $("lgMax2").textContent = `≥ ${nf(vcap)} MPa`;
      const adm = P.Fy_pawl / P.Nd;
      $("feaPawlT").innerHTML = `<table class="t"><thead><tr><th>Resultado</th><th class="n">Valor</th><th class="n">FU</th></tr></thead><tbody>` +
        `<tr><td>σ en la boca, fibra traccionada (FEA)</td><td class="n">${nf(f.vmMouth)} MPa</td><td class="n">${nf(f.vmMouth / adm, 2)}</td></tr>` +
        `<tr><td>σ en la boca, teoría de vigas M/S</td><td class="n">${nf(f.beam)} MPa</td><td class="n">${nf(f.beam / adm, 2)}</td></tr>` +
        `<tr><td>σvm máx. fuera de zonas de contacto (≥ 10 mm)</td><td class="n">${nf(f.vmFar)} MPa</td><td class="n">${nf(f.vmFar / adm, 2)}</td></tr>` +
        `<tr><td>Pico local en contacto/apoyo (singularidad)</td><td class="n">${nf(f.vmMax)} MPa</td><td class="n">–</td></tr>` +
        `<tr><td>Desplazamiento máximo</td><td class="n">${nf(f.dmax, 3)} mm</td><td class="n">–</td></tr>` +
        `<tr><td>Admisible Fy/Nd</td><td class="n">${nf(adm)} MPa</td><td class="n"></td></tr></tbody></table>`;
      $("feaPawlN").textContent = `Tensión plana Q4, malla 2,5 mm (${f.elems.length} elementos, ${f.res.ndof} GDL, ${nf(f.ms)} ms), espesor ${P.pawl_h} mm. Carga del calado repartida en el asiento con distribución cosenoidal. Apoyos: 25 mm inferiores en la boca del carro y labio posterior superior. Los picos en el borde de contacto son singularidades del modelo de apoyo puntual; en la pieza real el contacto se reparte y el chaflán de aristas los elimina. La verificación usa el mayor entre teoría de vigas y FEA en la sección de la boca.`;
    }
  }
  $("cvDisc").addEventListener("mousemove", (ev) => {
    const cv = ev.currentTarget, mp = cv._map; if (!mp) return;
    const r0 = cv.getBoundingClientRect(), x = (ev.clientX - r0.left) * cv.width / r0.width, y = (ev.clientY - r0.top) * cv.height / r0.height;
    const mx = (x - mp.cx) / mp.sc, my = -(y - mp.cy) / mp.sc, r = Math.hypot(mx, my); let th = Math.atan2(my, mx); if (th < 0) th += 2 * Math.PI;
    const m = mp.f.model, tl = th % m.alpha;
    if (r < m.rs[0] || r > m.rs[m.rs.length - 1]) { $("roDisc").textContent = `r = ${nf(r)} mm – fuera de la placa`; return; }
    let i = m.rs.findIndex((v) => v > r) - 1; if (i < 0) i = m.rs.length - 2;
    let j = m.ts.findIndex((v) => v > tl) - 1; if (j < 0) j = m.ts.length - 2;
    const e = i * (m.ts.length - 1) + j, el = mp.f.res.el[e];
    $("roDisc").textContent = `r = ${nf(r)} mm · θ = ${nf(th * 180 / Math.PI, 1)}° · σvm = ${nf(el.vm, 1)} MPa · Mx/My/Mxy = ${nf(el.M[0])}/${nf(el.M[1])}/${nf(el.M[2])} N·mm/mm`;
  });
  $("cvPawl").addEventListener("mousemove", (ev) => {
    const cv = ev.currentTarget, mp = cv._map; if (!mp) return;
    const r0 = cv.getBoundingClientRect(), x = (ev.clientX - r0.left) * cv.width / r0.width, y = (ev.clientY - r0.top) * cv.height / r0.height;
    const mx = (x - mp.ox) / mp.sc, my = (mp.oy - y) / mp.sc, f = mp.f;
    let best = -1, bd = 1e9; f.cent.forEach(([cx, cy], i) => { const d = Math.abs(cx - mx) + Math.abs(cy - my); if (d < bd) { bd = d; best = i; } });
    if (best < 0 || bd > 6) { $("roPawl").textContent = ""; return; }
    const e = f.res.el[best];
    $("roPawl").textContent = `x = ${nf(mx, 1)} · y = ${nf(my, 1)} mm · σx = ${nf(e.sx)} · σy = ${nf(e.sy)} · τxy = ${nf(e.txy)} · σvm = ${nf(e.vm)} MPa`;
  });
  document.querySelectorAll("[data-plate]").forEach((b) => b.addEventListener("click", () => { plate = b.dataset.plate; renderFEA(); }));
  document.querySelectorAll("[data-field]").forEach((b) => b.addEventListener("click", () => { field = b.dataset.field; renderFEA(); }));
  document.querySelectorAll("[data-def]").forEach((b) => b.addEventListener("click", () => { deformed = +b.dataset.def; renderFEA(); }));

  /* ---------------- planos ---------------- */
  function renderSheet() { $("sheetPrev").innerHTML = sheetSVG(buildSheet(R, V, F), { ink: "#000000", paper: "#ffffff", force: "#b3361f" }); }
  async function save(name, blob) {
    let d = null; try { d = await dlP; } catch (e) { d = null; }
    if (d) {
      try { await d.save({ filename: name, data: blob }); toast("Archivo entregado: " + name); }
      catch (e) { toast(e && e.code === "declined" ? "Descarga cancelada" : `No se pudo guardar (${(e && (e.code || e.message)) || "error"})`); }
      return;
    }
    const url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url; a.download = name; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 4000);
    toast("Descargando " + name);
  }
  async function busy(btn, fn) { const t = btn.textContent; btn.disabled = true; btn.textContent = "Generando…"; try { await fn(); } catch (e) { console.error(e); toast("Error: " + e.message); } finally { btn.disabled = false; btn.textContent = t; } }
  const stamp = () => new Date().toISOString().slice(0, 10);
  document.querySelectorAll("[data-file]").forEach((b) => b.addEventListener("click", () => busy(b, async () => {
    const r = await fetch(b.dataset.file); if (!r.ok) throw new Error("archivo no disponible en esta copia");
    await save(b.dataset.file.split("/").pop(), await r.blob());
  })));
  $("bIssuedZip").addEventListener("click", (ev) => busy(ev.currentTarget, async () => {
    if (!window.JSZip) throw new Error("no se cargó la librería ZIP");
    const names = ["TT300-B-D-01.dxf", "TT300-B-D-02.dxf", "TT300-B-D-03.dxf", "TT300-B-F-01.dxf", "TT300-B-F-02.dxf", "TT300-B-F-03.dxf", "TT300-B.step"], z = new JSZip();
    for (const n of names) { const r = await fetch("planos/src/" + n + ".txt"); if (!r.ok) throw new Error("archivo no disponible en esta copia"); z.file(n === "TT300-B.step" ? "TT300-B_conjunto.step" : n, await r.arrayBuffer()); }
    await save("TT300-B_Tornamesa300_DXF_STEP.zip", await z.generateAsync({ type: "blob", compression: "DEFLATE" }));
  }));
  $("bSheetPdf").addEventListener("click", (ev) => busy(ev.currentTarget, async () => {
    if (!window.jspdf) throw new Error("no se cargó la librería PDF");
    await save(`TT300-B-P-01_plano_parametrico_${stamp()}.pdf`, sheetPDF(buildSheet(R, V, F)));
  }));
  $("bSheetDxf").addEventListener("click", (ev) => busy(ev.currentTarget, async () => {
    if (!window.JSZip) throw new Error("no se cargó la librería ZIP");
    const z = new JSZip(); z.file("TT300-B-P-01_plano_parametrico.dxf", sheetDXF(buildSheet(R, V, F)));
    z.file("LEEME.txt", "Plano de verificación paramétrico TT300-B-P-01 en DXF R12 (AC1009), unidades mm, escala de papel 1:1 (formato A1 841x594).\r\nCapas: VIS, FINA, EJE, OCU, COTA, TXT, MARCO, FUERZA.\r\n");
    await save(`TT300-B-P-01_DXF_${stamp()}.zip`, await z.generateAsync({ type: "blob", compression: "DEFLATE" }));
  }));
  $("bMemo").addEventListener("click", (ev) => busy(ev.currentTarget, async () => {
    if (!window.jspdf || !window.jspdf.jsPDF.API.autoTable) throw new Error("no se cargó la librería PDF");
    const Cp = pal(true), im = {};
    im.plan = await svgToPng(dgPlan(R, Cp)); im.mu = await svgToPng(dgMu(R, Cp)); im.stroke = await svgToPng(dgStroke(R, Cp)); im.breakdown = await svgToPng(dgBreak(R, Cp));
    im.shoe = await svgToPng(dgShoe(R, Cp)); im.bar = await svgToPng(dgBar(R, Cp)); im.pin = await svgToPng(dgPin(R, Cp));
    const off = (w, h, fn) => { const c = document.createElement("canvas"); c.width = w; c.height = h; fn(c); return { data: c.toDataURL("image/png"), w, h }; };
    if (F.bot) { im.feaBot = off(900, 900, (c) => drawDisc(c, F.bot, "vm", Cp)); im.feaTop = off(900, 900, (c) => drawDisc(c, F.top, "vm", Cp)); }
    if (F.pawl) im.feaPawl = off(1000, 560, (c) => drawPawl(c, F.pawl, Cp, 0));
    renderFEA();
    await save(`TT300-B_memoria_verificacion_${stamp()}.pdf`, await memoriaPDF(R, V, F, Cp, im));
  }));
  (async () => {
    try { const r = await fetch("planos/TT300-B_Tornamesa300_Planos_Diseno.pdf", { method: "HEAD" }); if (!r.ok) throw 0; }
    catch (e) { document.querySelectorAll("[data-file], #bIssuedZip").forEach((b) => { b.disabled = true; b.title = "Disponible en la versión publicada"; }); }
  })();

  /* ---------------- pestañas ---------------- */
  const TABS = ["modelo", "resumen", "actuador", "diagramas", "verificaciones", "fea", "planos"];
  function show(t) {
    if (!TABS.includes(t)) t = "modelo";
    document.querySelectorAll(".tab").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.t === t)));
    document.querySelectorAll("[data-p]").forEach((p) => (p.hidden = p.dataset.p !== t));
  }
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => { show(b.dataset.t); try { history.replaceState(null, "", "#" + b.dataset.t); } catch (e) { location.hash = b.dataset.t; } }));
  window.addEventListener("hashchange", () => show(location.hash.slice(1)));
  try { window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => R && render()); } catch (e) { /* */ }
  new MutationObserver(() => R && render()).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  buildForm();
  show(location.hash.slice(1));
  recompute();
})();
