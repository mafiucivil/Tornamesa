"""Revisión independiente de (a) las 4 orejas de izaje soldadas, (b) el collar de asiento del pivote y
(c) la masa del collar y de las orejas (contenida en m.base) del núcleo TT300-C.

Regla de independencia: NO lee packages/*.js. Los resultados del núcleo salen solo de
`node tools/export_design.js [params.json]` (y de tests/golden/*.json); todo lo demás se deriva aquí desde la norma y la estática:
  - AISC 360-22: D2 (fluencia en sección bruta), D5 (miembros con pasador: rotura a tracción, rotura por corte, límites dimensionales D5.2),
    J7 (aplastamiento), J2.4 (filete: tamaño mínimo/máximo, resistencia), ASD (Ω = 2,00 salvo D2: 1,67).
  - AWS D1.1 (filete: garganta efectiva 0,707·w, método elástico de grupo de soldadura).
  - ASME BTH-1 Cat. B, Nd = 3,0 (esfuerzos admisibles Fy/Nd, 1,25·Fy/Nd en aplastamiento, Fy/(Nd·√3) en corte); ASME B30.26 (grillete), B30.9 (eslinga).
  - Equilibrio del pasador del pivote en un asiento rígido-lineal de Winkler (presión con inversión de signo, integrada numéricamente).

Convenciones: N, mm, MPa (kN para fuerzas de cilindro y de izaje); tf = 9,80665 kN; ρ = 7,85e-6 kg/mm³.

Modelo de las orejas (cada una, ramal a 60° sobre la horizontal, 3 de 4 ramales efectivos):
  T = m·φ·g/(3·sen 60°);  Tv = T·sen 60° (vertical);  Th = T·cos 60° (horizontal, en el plano de la oreja);  d_p = d_ear − 3 (pasador del grillete).
  Oreja: placa de espesor t, ancho 2R, extremo semicircular de radio R centrado en el agujero d, agujero a la altura h_ear sobre la base.
  Soldadura: dos filetes de longitud L = 2R (uno a cada lado), a = 0,707·w, S = 2aL²/6.
Modelo del collar: asiento L = t_base + h_boss (pivote pasante por plancha y collar); H de calado = H_exc + H_asim (+ s·η·F_calado si n impar).

Ejecutar:  python3 -I tests/indep_izaje_collar.py
Termina con «RESULTADO: ...». Sale con 0 si no hay discrepancias numéricas ni hallazgos críticos/mayores; con 1 si los hay; con 2 si no puede
ejecutar el núcleo.
"""
import json, math, pathlib, random, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLD = ROOT / "tests" / "golden"
g0, RHO = 9.80665, 7.85e-6
TOL = 1e-3                      # 0,1 %
S60, C60 = math.sin(math.radians(60)), math.cos(math.radians(60))


# ======================================================================================
# Utilidades
# ======================================================================================
def export(over=None):
    with tempfile.TemporaryDirectory() as td:
        args = ["node", str(ROOT / "tools" / "export_design.js")]
        if over:
            f = pathlib.Path(td) / "p.json"; f.write_text(json.dumps(over)); args.append(str(f))
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


_EXP = {}


def prefetch(lst):
    todo = [o for o in lst if json.dumps(o, sort_keys=True) not in _EXP]
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(export, todo))
    for o, r in zip(todo, res):
        _EXP[json.dumps(o, sort_keys=True)] = r


def get(over):
    k = json.dumps(over, sort_keys=True)
    if k not in _EXP:
        _EXP[k] = export(over)
    return _EXP[k]


def s3(x):
    if x is None:
        return "—"
    if isinstance(x, str):
        return x
    if x == 0 or not math.isfinite(x):
        return f"{x:g}"
    return f"{x:.{max(0, 3 - int(math.floor(math.log10(abs(x)))))}f}" if abs(x) >= 1e-3 else f"{x:.3g}"


def table(title, head, rows):
    print(f"\n### {title}")
    w = [max([len(str(h))] + [len(str(r[i])) for r in rows]) for i, h in enumerate(head)]
    print("| " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(head)) + " |")
    print("|" + "|".join("-" * (x + 2) for x in w) + "|")
    for r in rows:
        print("| " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) + " |")


COMP = []          # (caso, nombre, mío, núcleo, Δ%, estado)
FIND = []          # (id, severidad, texto, referencia, efecto numérico)


def comp(caso, name, mine, core, tol=TOL):
    if core is None or mine is None:
        COMP.append((caso, name, s3(mine), s3(core), "—", "discrepa" if (core is None) != (mine is None) else "coincide")); return
    d = (mine - core) / core * 100 if core else (0.0 if abs(mine) < 1e-9 else 100.0)
    COMP.append((caso, name, s3(mine), s3(core), f"{d:+.4f}", "coincide" if abs(d) <= tol * 100 else "discrepa"))


def comp_est(caso, name, fu, core_estado, banda=True):
    """Estado del núcleo frente a mi FU = demanda/capacidad. El núcleo usa tres estados: ok (FU ≤ 0,9), warn (0,9 < FU ≤ 1) y fail (FU > 1)
    en las verificaciones de esfuerzo; las geométricas son solo ok/fail (banda = False)."""
    eps = 1e-9
    esp = "fail" if fu > 1 + eps else ("warn" if (banda and fu > 0.9 + eps) else "ok")
    COMP.append((caso, name + " (estado)", f"{esp} (FU {fu:.3f})", core_estado, "—", "coincide" if core_estado == esp else "discrepa"))


def finding(i, sev, txt, ref, eff):
    FIND.append((i, sev, txt, ref, eff))


def ver(D, sub):
    r = [v for v in D["verificaciones"] if sub in v["nombre"]]
    return r[0] if r else None


# ======================================================================================
# Modelo propio (todo en función del diccionario de parámetros PP del caso)
# ======================================================================================
def rings_of(PP):
    return sorted(float(x) for x in PP["rings"].replace(";", ",").split(",") if x.strip())


def m_disc(PP):
    """Masa de la mesa [kg] (sin el pivote): planchas, almas, nervios, cubo con rebaje inferior D_boss × h_boss, pasadores de empuje."""
    rings = rings_of(PP); Rt = PP["D_top"] / 2; hw = PP["h_disc"] - PP["t_top"] - PP["t_bot"]
    rpr = max(PP["D_hub"] / 2, PP["R_pin"] - (Rt - PP["R_pin"])); db = PP["D_piv"] + 30
    aring = math.pi * (Rt ** 2 - rpr ** 2) - PP["N_pin"] * math.pi * PP["d_pin"] ** 2 / 4
    m = RHO * ((math.pi * rpr ** 2 - math.pi / 4 * (PP["D_piv"] + 80) ** 2) * PP["t_top"] + aring * max(PP["t_pr"], PP["t_top"]))
    m += RHO * ((math.pi * rpr ** 2 - math.pi / 4 * db ** 2) * PP["t_bot"] + aring * max(PP["t_pr"], PP["t_bot"]))
    m += RHO * sum(2 * math.pi * r * hw * PP["t_web"] for r in rings)
    nin = sum(1 for r in rings if PP["D_hub"] / 2 < r < PP["R_rib"])
    m += RHO * PP["N_rib"] * (PP["R_rib"] - PP["D_hub"] / 2 - nin * PP["t_web"]) * hw * PP["t_rib"]
    m += RHO * math.pi / 4 * (PP["D_hub"] ** 2 - db ** 2) * hw
    if PP["h_boss"] > 0 and PP["D_boss"] > db:
        m -= RHO * math.pi / 4 * (PP["D_boss"] ** 2 - db ** 2) * min(PP["h_boss"], hw)
    m += RHO * PP["N_pin"] * math.pi / 4 * PP["d_pin"] ** 2 * PP["h_disc"]
    return m


def m_pivot(PP):
    return RHO * math.pi / 4 * PP["D_piv"] ** 2 * (PP["t_base"] + PP["h_disc"] - PP["t_top"] + 3)


def ear_area(PP):
    """Área de una oreja [mm²]: rectángulo 2R × h_ear + semicírculo de radio R − agujero d."""
    R, d, h = PP["R_ear"], PP["d_ear"], PP["h_ear"]
    return 2 * R * h + math.pi * R ** 2 / 2 - math.pi * d ** 2 / 4


def m_collar(PP):
    return RHO * math.pi / 4 * (PP["D_boss"] ** 2 - PP["D_piv"] ** 2) * PP["h_boss"] if PP["h_boss"] > 0 else 0.0


def m_ears(PP):
    return RHO * 4 * PP["t_ear"] * ear_area(PP)


def m_base(PP):
    """Plancha B × B × t_base con taladro del pivote Ø D_piv + collar (anillo D_boss–D_piv, altura h_boss) + 4 orejas."""
    plate = RHO * (PP["B"] ** 2 - math.pi / 4 * PP["D_piv"] ** 2) * PP["t_base"]
    return plate + m_collar(PP) + m_ears(PP)


def m_rim(PP):
    return RHO * PP["rim_h"] * PP["rim_t"] * 4 * (PP["B"] - PP["rim_t"])


def kappa(PP):
    Ro, Ri = PP["D_top"] / 2, PP["D_piv"] / 2 + 15
    return 4 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4)


def N_kN(PP):
    return PP["W_tf"] * g0 + (m_disc(PP) + 0.5 * m_pivot(PP)) * g0 / 1e3


# ---- cinemática del accionamiento: F_pas y reacciones de patín por unidad de par (modelo de equilibrio de indep_accionamiento.py) ----
_TAB = {}


def tabla(PP):
    key = tuple(PP[k] for k in ("R_pin", "N_pin", "d_pin", "x_g", "l_p", "f_ext", "d_pp", "mu_g", "mu_s", "eta_c"))
    if key in _TAB:
        return _TAB[key]
    R, Np, dpin, xg, lp, fext, dpp, mug, mus, eta = key
    rp = dpin / 2; ph = math.pi / int(Np)
    front, rear = lp + 20 + fext, 1.25 * dpp
    Lg = 2 / 3 * (front + rear); yr = (front - rear) / 2 - Lg / 2; yc = lp - rp

    def est(th, sg=None):
        a, yp = R * math.cos(th), R * math.sin(th)
        if sg is None:
            sg = 1 if yp > rp else -1
        hh = sg * mus
        F = 1.0 / (a - hh * (yp - rp)); H = hh * F
        Rf = (F * (xg - a) + H * (yc - yr)) / Lg; Rr = H - Rf
        return dict(F=F, sig=(abs(Rf) + abs(Rr)) / F, Fh=(F + mug * (abs(Rf) + abs(Rr))) / eta)

    pts = [est(-ph + 2 * ph * i / 4000) for i in range(4001)]
    th0 = math.asin(rp / R)
    pts += [est(th0, 1), est(th0, -1)]
    _TAB[key] = pts
    return pts


def Fst_kN(PP):
    return math.pi / 4 * PP["D_bore"] ** 2 * PP["p_relief"] / 10 / 1e3


def H_asim(PP):
    """H_asim = F_calado·η·máx_θ |1/(1+(μg−0,05)σ) − 1/(1+(μg+0,05)σ)|,  F_cil = F(1 + μg·σ)/η,  σ = (|R_f|+|R_r|)/F."""
    mg = PP["mu_g"]
    return Fst_kN(PP) * PP["eta_c"] * max(abs(1 / (1 + (mg - 0.05) * e["sig"]) - 1 / (1 + (mg + 0.05) * e["sig"])) for e in tabla(PP))


def H_pivote(PP):
    """(H_diseño, H_calado) [kN] de la reacción horizontal sobre el pivote."""
    N = N_kN(PP); kap = kappa(PP)
    Hec = max(PP["mu_d"] * N * PP["e"] * kap, PP["Ch"] * N); Has = H_asim(PP)
    Hd = Hc = 0.0
    if PP["n_cyl"] % 2 == 1:
        sr = math.sqrt(1 + PP["mu_s"] ** 2)
        T = N * (PP["mu_d"] * PP["r_ef"] + PP["mu_bush"] * PP["mu_d"] * PP["e"] * kap * PP["D_piv"] / 2)      # kN·mm
        e = max(tabla(PP), key=lambda q: q["Fh"])
        Hd = sr * e["F"] * T / PP["n_cyl"]; Hc = sr * PP["eta_c"] * Fst_kN(PP)
    return Hec + Has + Hd, Hec + Has + Hc, Hec, Has


# ---- asiento de Winkler rígido-lineal: p(z) = A + B·z, z desde el centro del asiento; ΣF = H, ΣM = H·(e + L/2) ----
def winkler(H, D, L, e, n=400):
    """Integración numérica (regla del punto medio). Devuelve (A, B, p_sup, p_inf) con p en N/mm² si H en N."""
    dz = L / n; zs = [-L / 2 + (i + 0.5) * dz for i in range(n)]
    s0 = D * dz * n; s2 = D * dz * sum(z * z for z in zs)           # ∫D dz, ∫D z² dz   (∫D z dz = 0)
    A = H / s0; B = H * (e + L / 2) / s2
    return A, B, A + B * L / 2, A - B * L / 2


def sigma_asiento(H_kN, D, L, e):
    return winkler(H_kN * 1e3, D, L, e)[2]


def L_min(H_kN, D, e, cap):
    lo, hi = 1.0, 2000.0
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (lo, m) if sigma_asiento(H_kN, D, m, e) <= cap else (m, hi)
    return hi


def weld_consistente(H_kN, PP, w):
    """Filete perimetral del collar (D_collar, garganta a = 0,707 w) cargado con lo que el collar recibe del pivote según el mismo modelo
    de Winkler: cortante V_c = ∫ p dA en la altura del collar y momento M_c respecto del plano de soldadura (cara superior de la plancha base)."""
    D, L, e, tb, hb = PP["D_piv"], PP["t_base"] + PP["h_boss"], PP["e_piv"], PP["t_base"], PP["h_boss"]
    A, B, _, _ = winkler(H_kN * 1e3, D, L, e)
    n = 2000; z0 = -L / 2 + tb; dz = (L / 2 - z0) / n
    V = M = 0.0
    for i in range(n):
        z = z0 + (i + 0.5) * dz; p = (A + B * z) * D * dz
        V += p; M += p * (z - z0)
    a = 0.707 * w; Dc = PP["D_boss"]
    fb = M / (math.pi * Dc ** 2 / 4 * a); fs = V / (math.pi * Dc * a)
    return math.hypot(fb, fs), V / 1e3, M / 1e6


# ======================================================================================
# Evaluación de un caso: compara lo que el núcleo exporta con el modelo propio
# ======================================================================================
def evaluar(label, D, detalle=False):
    PP = D["P"]; M = D["derivados"]["masas"]
    assert PP["opt_ss"] == 0 and PP["opt_uhmw"] == 0 and PP["opt_bz"] == 0 and PP["opt_wood"] == 0, "el verificador cubre la interfaz acero–acero"
    c = lambda n, mine, core, tol=TOL: comp(label, n, mine, core, tol)
    out = {}
    # ---- (c) masas ----
    mb, md, mp_, mr, mc = m_base(PP), m_disc(PP), m_pivot(PP), m_rim(PP), PP["n_cyl"] * PP["m_cyl"]
    c("m.base (plancha − taladro + collar + 4 orejas)", mb, M["base"])
    c("m.disc (mesa, con rebaje del cubo)", md, M["disc"])
    c("m.pivote", mp_, M["pivot"]); c("m.rim", mr, M["rim"]); c("m.cilindros", mc, M["cyl"])
    resto = M["brackets"] + M["dogs"] + M["shoes"] + M["beds"]                     # componentes fuera del alcance (se toman del núcleo)
    mtot = md + mb + mp_ + mr + mc + resto
    c("m.total (propias + ménsulas/uñas/patines/bancadas del núcleo)", mtot, M["total"])
    suma = sum(M[k] for k in ("disc", "base", "rim", "brackets", "dogs", "shoes", "beds", "pivot", "cyl"))
    c("m.total = Σ componentes del núcleo (identidad interna)", suma, M["total"], 1e-9)
    c("N = W + W_mesa (kN)", N_kN(PP), D["derivados"]["N"])
    # ---- (a) orejas ----
    T = mtot * PP["phi_lift"] * g0 / (3 * S60) / 1e3                                 # kN; se usa la masa total del núcleo para aislar la fórmula
    T_core_m = M["total"] * PP["phi_lift"] * g0 / (3 * S60) / 1e3
    v = ver(D, "Tensión por oreja"); c("T por oreja (kN)", T_core_m, v["dem"])
    w = ver(D, "WLL requerido por cáncamo"); c("WLL por cáncamo (tf) = T/g", T_core_m / g0, w["dem"])
    Tv, Th = T_core_m * S60, T_core_m * C60
    t, R, d, h, we = PP["t_ear"], PP["R_ear"], PP["d_ear"], PP["h_ear"], PP["w_ear"]
    dp = d - 3; Nd, Fy = PP["Nd"], PP["Fy"]
    Tn = T_core_m * 1e3
    cap_ap, cap_t, cap_v = 1.25 * Fy / Nd, Fy / Nd, Fy / (Nd * math.sqrt(3))
    ear = [("Oreja: aplastamiento del agujero", Tn / (dp * t), cap_ap),
           ("Oreja: tracción en la sección neta", Tn / (2 * (R - d / 2) * t), cap_t),
           ("Oreja: desgarro por corte", Tn / (2 * (R - d / 2) * t), cap_v)]
    a_w, L_w = 0.707 * we, 2 * R; S_w = 2 * a_w * L_w ** 2 / 6
    f_w = math.hypot(Tv * 1e3 / (2 * a_w * L_w) + Th * 1e3 * h / S_w, Th * 1e3 / (2 * a_w * L_w))
    ear.append(("Oreja: soldadura a la base", f_w, 0.60 * PP["FEXX"] / (1.2 * Nd)))
    ear.append(("Oreja: relación de bordes (R − d/2 ≥ 0,5 d)", 0.5 * d, R - d / 2))
    for nm, dem, cap in ear:
        k = ver(D, nm.split(" (")[0])
        c(nm + ": dem", dem, k["dem"]); c(nm + ": cap", cap, k["cap"]); comp_est(label, nm, dem / cap, k["estado"], banda=("bordes" not in nm))
    out["FU_weld_ear"] = f_w / (0.60 * PP["FEXX"] / (1.2 * Nd)); out["T"] = T_core_m
    # ---- (b) collar y asiento ----
    Hd, Hc, Hec, Has = H_pivote(PP)
    D_, Lb, e_ = PP["D_piv"], PP["L_bush"], PP["e_piv"]
    c("H_asim (kN)", Has, ver(D, "Empuje neto al pivote")["dem"])
    c("H_exc (kN)", Hec, D["apoyo"]["H_ecc_d"])
    c("Presión en el buje (MPa)", Hd * 1e3 / (D_ * Lb), ver(D, "Presión en el buje")["dem"])
    c("Flexión del pivote (MPa)", Hc * 1e3 * e_ / (math.pi * D_ ** 3 / 32), ver(D, "Flexión del pivote")["dem"])
    Ls = PP["t_base"] + PP["h_boss"]
    k = ver(D, "Aplastamiento del pivote en el asiento")
    c("Aplastamiento del pivote en el asiento (MPa)", Hc * 1e3 / (D_ * Ls), k["dem"]); c("  cap 1,25Fy/Nd (MPa)", cap_ap, k["cap"])
    k = ver(D, "Asiento del pivote con momento")
    sg = sigma_asiento(Hc, D_, Ls, e_)
    c("Asiento con momento: σ (MPa)", sg, k["dem"]); c("  cap 1,25Fy/Nd (MPa)", cap_ap, k["cap"])
    Lm = L_min(Hc, D_, e_, cap_ap)
    lab = re.search(r"mínima ([0-9.,]+) mm", k["nombre"])
    comp(label, "Asiento con momento: profundidad mínima L (mm, rótulo = ⌈L⌉)", float(math.ceil(Lm - 1e-9)), float(lab.group(1).replace(",", ".")) if lab else None, 1e-9)
    comp_est(label, "Asiento con momento", sg / cap_ap, k["estado"])
    k = ver(D, "Aplastamiento del buje en el cubo")
    c("Buje en el cubo (MPa)", Hc * 1e3 / ((D_ + 30) * Lb), k["dem"]); comp_est(label, "Buje en el cubo", Hc * 1e3 / ((D_ + 30) * Lb) / cap_ap, k["estado"])
    out["seat_FU"] = sg / cap_ap
    kw = ver(D, "Soldadura del collar")
    if PP["h_boss"] > 0:
        kc = [ver(D, "Collar del pivote: pared del collar"), ver(D, "Collar del pivote: pared del rebaje"), ver(D, "Buje sobre el collar")]
        geo = [(PP["D_piv"] + 60, PP["D_boss"]), (PP["D_boss"] + 50, PP["D_hub"]), (PP["h_boss"] + 2 + Lb, 0 + PP["h_disc"] - PP["t_top"])]
        for nm, kk, (dem, cap) in zip(("pared del collar ≥ 30", "pared del rebaje ≥ 25", "buje bajo la plancha superior"), kc, geo):
            if kk is None:
                comp(label, "Collar: " + nm, dem, None); continue
            c("Collar: " + nm + ": dem", dem, kk["dem"]); c("Collar: " + nm + ": cap", cap, kk["cap"]); comp_est(label, "Collar: " + nm, dem / cap, kk["estado"], banda=False)
        if kw is None:
            comp(label, "Soldadura del collar", 1.0, None)
        else:
            wd = float(re.search(r"w = ([0-9.,]+) mm", kw["formula"]).group(1).replace(",", "."))
            a_c = 0.707 * wd; Dc = PP["D_boss"]
            fb = Hc * 1e3 * (e_ + Ls / 2) / (math.pi * Dc ** 2 / 4 * a_c); fs = Hc * 1e3 / (math.pi * Dc * a_c)
            f_core = math.hypot(fb, fs); capw = 0.60 * PP["FEXX"] / (1.2 * Nd)
            c("Soldadura del collar (fórmula declarada): f (MPa)", f_core, kw["dem"]); c("  cap 0,60FEXX/(1,2Nd)", capw, kw["cap"])
            comp_est(label, "Soldadura del collar", f_core / capw, kw["estado"], banda=False)     # el núcleo no usa la banda «warn» en este filete
            out["nowarn"] = kw["estado"] == "ok" and f_core / capw > 0.9
            f_con, Vc, Mc = weld_consistente(Hc, PP, wd)
            out.update(wd=wd, f_core=f_core, f_con=f_con, capw=capw, Vc_H=Vc * 1e3 / (Hc * 1e3), Mc=Mc, Hc=Hc)
    else:
        for sub in ("Collar del pivote: pared del collar", "Collar del pivote: pared del rebaje", "Buje sobre el collar", "Soldadura del collar"):
            if ver(D, sub) is not None:
                comp(label, "Sin collar (h_boss = 0): no debe existir «" + sub + "»", 0.0, 1.0)
    return out


# ======================================================================================
# 0. Caso base
# ======================================================================================
D0 = export()
if D0 is None:
    print("No se pudo ejecutar node tools/export_design.js"); sys.exit(2)
P0 = D0["P"]
Pg = json.loads((GOLD / "params_defaults.json").read_text())
Gd = json.loads((GOLD / "tt300c_defaults.json").read_text())
drift = sorted(k for k in Pg if P0.get(k) != Pg.get(k))
print("Parámetros del núcleo = params_defaults.json:", "sí" if not drift else "NO, difieren: " + ", ".join(f"{k} ({Pg[k]} → {P0.get(k)})" for k in drift))
comp("base", "m.disc frente al golden masa_mesa (kg)", m_disc(Pg), Gd["masa_mesa"])
comp("base", "N frente al golden (kN)", N_kN(Pg), Gd["N"])
o0 = evaluar("base", D0)

# ======================================================================================
# 1. Barridos (un parámetro a la vez + combinaciones aleatorias reproducibles)
# ======================================================================================
SW = {
    "W_tf": [100, 200, 400, 500, 600], "t_ear": [8, 10, 14, 25, 32], "w_ear": [5, 6, 10, 12, 16], "h_boss": [0, 30, 45, 100, 150],
    "D_boss": [220, 240, 260, 300, 350], "t_base": [16, 20, 25, 30, 40], "n_cyl": [1, 3, 4],
    "R_ear": [45, 80, 100], "d_ear": [30, 36, 60], "h_ear": [60, 150, 200], "phi_lift": [1.0, 1.5, 2.0],
    "e_piv": [20, 60, 80], "L_bush": [60, 100, 120], "D_piv": [100, 140], "B": [2000, 3000],
}
cases = [("barrido " + k + " = " + str(v), {k: v}) for k, vs in SW.items() for v in vs]
rnd = random.Random(20261106)
RNG = {"W_tf": (50, 500), "t_ear": (10, 30), "w_ear": (6, 12), "h_boss": (0, 120), "D_boss": (200, 300), "t_base": (16, 32), "n_cyl": (1, 4),
       "R_ear": (45, 90), "d_ear": (30, 60), "h_ear": (60, 160), "phi_lift": (1.0, 2.0), "e_piv": (20, 70)}
for i in range(60):
    ov = {}
    for k in rnd.sample(list(RNG), rnd.randint(3, 7)):
        lo, hi = RNG[k]
        ov[k] = rnd.randint(lo, hi) if isinstance(lo, int) and k != "phi_lift" else round(rnd.uniform(lo, hi), 2)
    cases.append((f"combinación {i + 1:02d}", ov))
prefetch([o for _, o in cases])
sw_stats = {}                       # clave del barrido -> [n_cmp, n_disc, worst%]
inval = []
res_cases = []
for nm, ov in cases:
    D = get(ov)
    if D is None:
        inval.append(nm); continue
    n0 = len(COMP)
    o = evaluar(nm, D)
    res_cases.append((nm, ov, D, o))
    grp = nm.split(" = ")[0] if nm.startswith("barrido") else "combinaciones"
    st = sw_stats.setdefault(grp, [0, 0, 0.0, 0])
    st[3] += 1
    for r in COMP[n0:]:
        st[0] += 1
        if r[5] == "discrepa":
            st[1] += 1
        try:
            st[2] = max(st[2], abs(float(r[4])))
        except ValueError:
            pass

# ======================================================================================
# 2. Salida: caso base, resumen de barridos, discrepancias
# ======================================================================================
base_rows = [r[1:] for r in COMP if r[0] == "base"]
table("Caso base (parámetros por defecto): modelo propio frente al núcleo", ["Magnitud", "propio", "núcleo", "Δ %", "estado"], base_rows)
table("Barridos: casos válidos, comparaciones, discrepancias y desvío máximo", ["Barrido", "casos", "comparaciones", "discrepancias", "|Δ| máx %"],
      [[k, v[3], v[0], v[1], f"{v[2]:.4f}"] for k, v in sw_stats.items()])
if inval:
    print(f"\nCasos que el núcleo rechaza por validación (no son discrepancia; {len(inval)}): " + "; ".join(inval))
disc = [r for r in COMP if r[5] == "discrepa"]
if disc:
    table("DISCREPANCIAS NUMÉRICAS", ["Caso", "Magnitud", "propio", "núcleo", "Δ %", "estado"], [list(r) for r in disc[:80]])
    if len(disc) > 80:
        print(f"... y {len(disc) - 80} más")

# ======================================================================================
# 3. Verificaciones normativas propias que el núcleo no calcula (caso base) y hallazgos
# ======================================================================================
PP = P0; Nd, Fy, FEXX = PP["Nd"], PP["Fy"], PP["FEXX"]
t, R, d, h, we, dpin = PP["t_ear"], PP["R_ear"], PP["d_ear"], PP["h_ear"], PP["w_ear"], PP["d_ear"] - 3
T = o0["T"]; Tn = T * 1e3
Fu = 450.0                                 # supuesto: acero Fy = 345 (A572 Gr 50 / S355), Fu mín. 450 MPa; el núcleo no tiene Fu
b_phys = (2 * R - d) / 2; be = min(2 * t + 16, b_phys); a_ext = R - d / 2
rows = []
Rn_tr = Fu * 2 * t * be; rows.append(["D5.1(a) rotura a tracción, área neta efectiva", "Fu·2t·b_e", f"{Rn_tr / 2e3:.1f} kN (Ω=2,00)", f"{T / (Rn_tr / 2e3):.3f}", "ok"])
Asf = 2 * t * (a_ext + d / 2); Rn_sh = 0.6 * Fu * Asf; rows.append(["D5.1(b) rotura por corte, Asf = 2t(a + d/2)", "0,6·Fu·Asf", f"{Rn_sh / 2e3:.1f} kN (Ω=2,00)", f"{T / (Rn_sh / 2e3):.3f}", "ok"])
Rn_br = 1.8 * Fy * dpin * t; rows.append(["J7 aplastamiento (pasador d−3)", "1,8·Fy·d_p·t", f"{Rn_br / 2e3:.1f} kN (Ω=2,00)", f"{T / (Rn_br / 2e3):.3f}", "ok"])
Rn_g = Fy * 2 * R * t; rows.append(["D2 fluencia, sección bruta 2R·t", "Fy·Ag", f"{Rn_g / 1.67e3:.1f} kN (Ω=1,67)", f"{T / (Rn_g / 1.67e3):.3f}", "ok"])
fu_a = a_ext / (1.33 * be); rows.append(["D5.2 extensión a ≥ 1,33·b_e", f"a = {a_ext:.1f}; 1,33·b_e = {1.33 * be:.1f} mm", "—", f"{1 / fu_a:.3f}", "NO CUMPLE" if fu_a < 1 else "ok"])
fu_w = (2 * be + d) / (2 * R); rows.append(["D5.2 ancho 2R ≥ 2·b_e + d", f"2R = {2 * R}; 2b_e + d = {2 * be + d:.1f} mm", "—", f"{fu_w:.3f}", "ok" if fu_w <= 1 + 1e-9 else "NO CUMPLE"])
rows.append(["D5.2 holgura agujero − pasador ≤ 1 mm (si hay movimiento bajo carga)", f"{d - dpin:.1f} mm", "—", f"{(d - dpin) / 1.0:.2f}", "NO CUMPLE" if d - dpin > 1 else "ok"])
# sección de la placa en la base (flexión de Th·h + tracción de Tv sobre 2R × t): no figura entre las verificaciones del núcleo
sig_pl = Tn * C60 * h / (t * (2 * R) ** 2 / 6) + Tn * S60 / (2 * R * t)
rows.append(["Placa de la oreja en la base: Th·h/(t(2R)²/6) + Tv/(2R·t)", "no verificada en el núcleo", f"{sig_pl:.1f} MPa (adm. {Fy / Nd:.1f})", f"{sig_pl / (Fy / Nd):.3f}", "ok" if sig_pl <= Fy / Nd else "NO CUMPLE"])
# soldadura: J2.4 mínimo y capacidad ASD
tmin_joint = min(t, PP["t_base"]); wmin = 3 if tmin_joint <= 6 else 5 if tmin_joint <= 13 else 6 if tmin_joint <= 19 else 8
rows.append(["J2.4 filete de la oreja: w_mín(parte más delgada) ≤ w ≤ t_ear − 2", f"w_mín = {wmin}; w = {we}; máx = {t - 2} mm", "—", f"{wmin / we:.3f}", "ok" if wmin <= we <= t - 2 else "NO CUMPLE"])
rows.append(["J2.4 capacidad ASD del filete: 0,60·FEXX/Ω (Ω = 2,00) frente al 0,60·FEXX/(1,2·Nd) del núcleo", f"{0.6 * FEXX / 2:.1f} vs {0.6 * FEXX / (1.2 * Nd):.1f} MPa", "—", f"{(0.6 * FEXX / (1.2 * Nd)) / (0.6 * FEXX / 2):.3f}", "núcleo más conservador"])
table("Verificaciones normativas propias de la oreja (caso base, T = %.2f kN; Fu = 450 MPa supuesto)" % T, ["Verificación", "expresión / dato", "capacidad", "FU", "estado"], rows)
rows_oreja = rows
span = math.sqrt(PP["x_lug"] ** 2 + (PP["B"] / 2 - PP["c_lug"]) ** 2)
if True:
    print(f"\nÁngulo de ramal: 60° sobre la horizontal exige ramales de longitud ≤ 2·{span:.0f} = {2 * span:.0f} mm (distancia lugar–eje = {span:.0f} mm); ramales más largos aumentan T.")

# --- (b) transferencia al filete del collar
if "f_con" in o0:
    f_core, f_con, capw = o0["f_core"], o0["f_con"], o0["capw"]
    Hc = o0["Hc"]; Nbase = N_kN(PP)
    def Wlim(factor):
        """W [tf] en que el filete llega a su capacidad (f ∝ H; H lineal en N)."""
        sl = PP["mu_d"] * PP["e"] * kappa(PP)
        Hlim = Hc * capw / (f_core * factor)
        return ((Hlim - H_asim(PP) - (H_pivote(PP)[1] - H_pivote(PP)[2] - H_asim(PP))) / sl - (m_disc(PP) + 0.5 * m_pivot(PP)) * g0 / 1e3) / g0
    k_f = f_con / f_core
    rows = [["Núcleo (declarado): V = H, M = H·(e + L/2)", f"{f_core:.2f}", f"{f_core / capw:.3f}", f"{Wlim(1.0):.0f}"],
            ["Propio: lo que el collar toma del pivote (V_c = %.2f·H, M_c = %.1f kN·m respecto de la cara superior de la base)" % (o0["Vc_H"], o0["Mc"]),
             f"{f_con:.2f}", f"{f_con / capw:.3f}", f"{Wlim(k_f):.0f}"]]
    table("Filete perimetral del collar (D = %d mm, w = %g mm): carga transferida" % (PP["D_boss"], o0["wd"]), ["Modelo", "f (MPa)", "FU", "W_lím (tf)"], rows)
    sev = "mayor" if f_con / capw > 0.75 else "menor"
    finding("H1", sev, "Soldadura del collar: el núcleo carga el filete con V = H y M = H·(e + L/2) (momento respecto del centro del asiento). Con el mismo asiento de Winkler que usa para σ, el collar "
            "(solo la parte sobre la cara superior de la base) recibe V_c = %.2f·H y un momento respecto del plano de la soldadura de %.1f kN·m (frente a H·(e+L/2) = %.1f kN·m); la parte de plancha base toma la reacción de signo contrario" % (o0["Vc_H"], o0["Mc"], Hc * (PP["e_piv"] + (PP["t_base"] + PP["h_boss"]) / 2) / 1e3),
            "AWS D1.1 / AISC 360-22 J2.4 (grupo circular, elástico); equilibrio del collar",
            f"f = {f_con:.1f} MPa en vez de {f_core:.1f} (FU {f_con / capw:.2f} frente a {f_core / capw:.2f}); W límite del filete {Wlim(k_f):.0f} tf frente a {Wlim(1.0):.0f} tf")
# --- Geometría constructiva del collar / cubo / buje
db = PP["D_piv"] + 30
dm_rec = RHO * math.pi / 4 * (((PP["D_boss"] + 6) ** 2 - db ** 2) * (PP["h_boss"] + 2) - (PP["D_boss"] ** 2 - db ** 2) * PP["h_boss"])
finding("H2", "menor", "Rebaje del cubo: la masa y la verificación de pared (D_collar + 50 ≤ D_cubo) suponen el rebaje con el mismo diámetro y altura que el collar (D_boss × h_boss): sin holgura de giro, el cubo (que gira) rozaría con el collar (fijo). Con holgura radial 3 mm y axial 2 mm "
        "la pared del cubo queda en %.1f mm (< 25) y la masa del cubo baja %.2f kg" % ((PP["D_hub"] - PP["D_boss"] - 6) / 2, dm_rec),
        "Criterio de fabricación (holgura de giro); consistencia de la geometría", f"pared del cubo {((PP['D_hub'] - PP['D_boss']) / 2):.0f} mm → {(PP['D_hub'] - PP['D_boss'] - 6) / 2:.1f} mm con holgura; masa −{dm_rec:.2f} kg ({dm_rec / D0['derivados']['masas']['total'] * 100:.3f} % del total)")
arm = 2 + PP["L_bush"] / 2
Hc0 = H_pivote(PP)[1]
sg_geo = sigma_asiento(Hc0, PP["D_piv"], PP["t_base"] + PP["h_boss"], arm)
finding("H3", "menor", "Brazo del momento: e_piv (%g mm) es un dato libre; si el buje apoya 2 mm sobre el collar (como supone la verificación de ajuste) y la reacción del buje actúa a media altura, el brazo geométrico desde la cara superior del asiento es 2 + L_buje/2 = %g mm; "
        "el núcleo no liga e_piv a L_buje (con L_buje = 120 el brazo sería 62 mm)" % (PP["e_piv"], arm), "Estática del pivote; ASME BTH-1 3-2.3 (flexión)",
        f"σ asiento {sg_geo:.1f} MPa frente a {o0['seat_FU'] * 1.25 * PP['Fy'] / Nd:.1f} (FU {sg_geo / (1.25 * PP['Fy'] / Nd):.3f} frente a {o0['seat_FU']:.3f}); σ flexión del pivote +{(arm / PP['e_piv'] - 1) * 100:.1f} %")
Rreq = max(d / 2 + 1.33 * (2 * t + 16), (d + 2 * (2 * t + 16)) / 2)
finding("H4", "menor", "Oreja: la verificación «relación de bordes (R − d/2 ≥ 0,5 d)» no es el límite dimensional de AISC 360-22 D5.2 que cita como referencia. Con b_e = mín(2t + 16; (2R − d)/2) = %.1f mm, D5.2 exige "
        "a ≥ 1,33·b_e = %.1f mm y la oreja tiene a = R − d/2 = %.1f mm (con extremo semicircular centrado en el agujero a = (2R − d)/2, así que solo se cumple si (2R − d)/2 ≥ 1,33·(2t + 16)); "
        "además la holgura agujero–pasador es %.0f mm (D5.2 pide ≤ 1 mm si el pasador gira bajo carga)" % (be, 1.33 * be, a_ext, d - dpin),
        "AISC 360-22 D5.2(2) y D5.2(3)", f"FU dimensional {1 / fu_a:.2f} (no cumple); las resistencias de D5.1/J7/D2 tienen FU ≤ {max(float(r[3]) for r in rows_oreja[:4]):.2f}, no gobierna la resistencia; cumpliría con R ≥ {Rreq:.0f} mm (t = {t}, d = {d})")
finding("H5", "menor", "Placa de la oreja en la base (flexión por Th·h + tracción Tv sobre la sección 2R × t) no figura entre las verificaciones del grupo; hoy pasa con holgura, pero con orejas esbeltas gobernaría antes que aplastamiento/desgarro",
        "AISC 360-22 D2; ASME BTH-1 3-2", f"σ = {sig_pl:.1f} MPa, FU {sig_pl / (Fy / Nd):.3f} (adm. Fy/Nd = {Fy / Nd:.1f})")
t8 = [(nm, D) for nm, ov, D, o in res_cases if ov == {"t_ear": 8}]
ex8 = ""
if t8:
    D8 = t8[0][1]
    fallas8 = [v["nombre"] for v in D8["verificaciones"] if v["estado"] == "fail" and ("Oreja" in v["nombre"] or v["grp"] == "Soldaduras")]
    ex8 = f"; con t_ear = 8 y w_ear = {PP['w_ear']} (> t − 2 = 6) el núcleo marca {len(fallas8)} fallas de oreja/soldadura"
finding("H6", "menor", "Soldaduras: no hay verificación de tamaño mínimo/máximo de filete (J2.4) para w_ear ni para el filete del collar, cuyo w = 10 mm está fijo en el rótulo (no es parámetro); "
        "el grupo «Soldaduras» solo cubre almas/nervios y mejillas", "AISC 360-22 J2.4 (Tabla J2.4); AWS D1.1 5.14",
        f"w_mín = {wmin} mm, w_ear = {we}, w_máx = t_ear − 2 = {t - 2} mm (hoy ok){ex8}")
finding("H7", "menor", "El ángulo de 60° es una cota mínima: con lugar–eje de %.0f mm los ramales no deben pasar de 2·%.0f = %.0f mm; ramales más largos (menor ángulo) aumentan T y Th. El núcleo no declara esta restricción" % (span, span, 2 * span),
        "ASME B30.9 (factor de ángulo 1/sen θ); B30.26", f"a 45°: T ×{S60 / math.sin(math.radians(45)):.3f}, Th ×{(1 / math.tan(math.radians(45))) / (1 / math.tan(math.radians(60))):.2f}; Tv no cambia")
nw = [(nm, o["f_core"] / o["capw"]) for nm, ov, D, o in res_cases if o.get("nowarn")]
if nw:
    finding("H8", "menor", "Soldadura del collar: el estado no usa la banda «warn» (0,9 < FU ≤ 1) que sí usan las demás verificaciones de esfuerzo (p. ej. soldadura de la oreja, asiento): con FU entre 0,9 y 1 muestra «ok»",
            "Coherencia interna de estados", f"{len(nw)} casos de barrido con FU entre 0,9 y 1 en «ok» (máx. FU {max(x[1] for x in nw):.3f}); p. ej. " + nw[0][0])
# verificaciones de coherencia con el barrido: ¿hay casos en que mi modelo del filete del collar falla y el núcleo dice ok?
flip = []
for nm, ov, D, o in res_cases:
    if "f_con" in o and o["f_con"] > o["capw"] and o["f_core"] <= o["capw"]:
        flip.append(nm)
if flip:
    print(f"\nCasos en que el modelo propio del filete del collar falla y el núcleo da ok ({len(flip)}): " + "; ".join(flip[:12]) + (" ..." if len(flip) > 12 else ""))

# ======================================================================================
# 4. Resumen
# ======================================================================================
ordsev = {"crítico": 0, "mayor": 1, "menor": 2}
FIND.sort(key=lambda r: (ordsev[r[1]], r[0]))
table("Hallazgos", ["Id", "Severidad", "Descripción", "Referencia", "Efecto numérico"], [list(r) for r in FIND])
nc = len(COMP); nd = len(disc)
ncrit = sum(1 for r in FIND if r[1] == "crítico"); nmay = sum(1 for r in FIND if r[1] == "mayor"); nmen = sum(1 for r in FIND if r[1] == "menor")
print(f"\nRESULTADO: {nc - nd} coincidencias, {nd} discrepancias numéricas (de {nc} comparaciones; {len(res_cases)} casos válidos de barrido, {len(inval)} rechazados por validación); "
      f"hallazgos: {ncrit} críticos, {nmay} mayores, {nmen} menores")
sys.exit(1 if (nd or ncrit or nmay) else 0)
