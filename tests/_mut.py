"""Verificación independiente del escenario térmico TT300-C (revisor independiente).

No lee packages/core ni packages/agents. Entradas: tests/golden/params_defaults.json, tests/golden/tt300c_defaults.json y la salida
JSON de `node tools/export_design.js [overrides.json]` (clave `termica`, `verificaciones`, `interfazChecks`, `derivados`), tratada como
caja negra. Las fórmulas se derivan de docs/normas/registro.md (sección «Temperatura (exposición solar, 80 °C)») y de las normas citadas:
  - dilatación del acero: EN 1993-1-2 §3.4.1.1  Δl/l = 1,2e-5·θ + 0,4e-8·θ² − 2,416e-4  (α medio entre T_ref y T)
  - Lamé (cilindro de pared gruesa, tensión plana) para buje y cilindro hidráulico; Timoshenko para la placa restringida
  - ASTM D341 (Walther) para la viscosidad; Lindley/Gent para el módulo confinado de la lámina UHMW (como indep_interfaz.py)
Compara contra el núcleo con tolerancia 0,1 %. Salida: exit 0 si todas las réplicas coinciden; 1 si hay diferencias (errores de réplica o
hallazgos reales); 2 si no hay node. Los hallazgos de revisión que no son diferencias numéricas se imprimen al final (HALLAZGO ...).
Ejecutar: python3 -I tests/indep_termica.py"""
import json, math, os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
GD = ROOT / "tests" / "golden"
P0 = json.loads((GD / "params_defaults.json").read_text())
G = json.loads((GD / "tt300c_defaults.json").read_text())
TOL = 1e-3
fails = []
nchk = [0]
LOG = "-v" in sys.argv


def chk(name, mine, tool, tol=TOL, absn=1e-9):
    nchk[0] += 1
    if mine is None or tool is None:
        ok = mine is None and tool is None
        if not ok:
            fails.append(name); print(f"XX  {name:78s} indep {mine}  núcleo {tool}")
        elif LOG:
            print(f"OK  {name:78s} (ambos None)")
        return
    ok = abs(mine - tool) <= tol * abs(tool) + absn
    if not ok:
        fails.append(name)
        print(f"XX  {name:78s} indep {mine:14.6f}  núcleo {tool:14.6f}  Δ {(mine - tool) / (tool if tool else 1) * 100:+.4f} %")
    elif LOG:
        print(f"OK  {name:78s} indep {mine:14.6f}  núcleo {tool:14.6f}")


def chk_eq(name, mine, tool):
    nchk[0] += 1
    if mine != tool:
        fails.append(name); print(f"XX  {name:78s} indep {mine!r}  núcleo {tool!r}")
    elif LOG:
        print(f"OK  {name:78s} {mine!r}")


# ------------------------------------------------------------------ ejecución del núcleo como caja negra
_cache = {}


def export(over=None):
    over = over or {}
    key = json.dumps(over, sort_keys=True)
    if key in _cache:
        return _cache[key]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(over, f)
        fn = f.name
    try:
        r = subprocess.run(["node", str(ROOT / "tools" / "export_design.js"), fn], capture_output=True, text=True, cwd=str(ROOT))
    except FileNotFoundError:
        print("node no está disponible"); sys.exit(2)
    finally:
        os.unlink(fn)
    if r.returncode:
        raise RuntimeError(f"export_design.js {over}: {r.stderr.strip()[:300]}")
    _cache[key] = json.loads(r.stdout)
    return _cache[key]


ALTS = [("base", {}), ("A", {"opt_ss": 1}), ("B", {"opt_uhmw": 1}), ("C1", {"opt_bz": 1, "bz_conf": 1}), ("C2", {"opt_bz": 1, "bz_conf": 2}), ("C3", {"opt_bz": 1, "bz_conf": 3})]
ALT_OVER = dict(ALTS)


def alt_export(aid, wood=False, extra=None):
    o = dict(ALT_OVER[aid])
    if wood:
        o["opt_wood"] = 1
    if extra:
        o.update(extra)
    return export(o)


# ------------------------------------------------------------------ constantes independientes (registro.md y normas)
g_ = 9.80665
ALPHA_SS, ALPHA_UH, ALPHA_BZ = 17.0e-6, 190.0e-6, 18.0e-6      # registro: inox 16,0 a 17,2; UHMW 180 a 200; bronce C93200 18
ALPHA_UH_DESIGN, ALPHA_ST_DESIGN = 180.0e-6, 12.0e-6           # registro (opción B, ISO 11359; EN 1993-1-1): junta en frío a 20 °C con dT = 40
AV = 7.5e-4                                                    # α_v del aceite mineral, registro
K_HOSE = 327.0                                                 # MPa, K combinado aceite + manguera, registro
E_BZ, NU_BZ = 110000.0, 0.33                                   # C95400 (CDA/ASM): el registro no los da; ver HALLAZGO
NU_UH = 0.45                                                   # Poisson del UHMW-PE (igual que indep_interfaz.py)
KEYS = {"Fy": "kT_Fy", "E": "kT_E", "Fy_ss": "kT_Fy_ss", "E_ss": "kT_E_ss", "p_uh": "kT_p_uh", "E_uh": "kT_E_uh", "bz": "kT_bz",
        "wood": "kT_wood", "bolt": "kT_bolt", "weld": "kT_weld", "hertz": "kT_hertz", "mu": "k_mu_T"}
K_FLOOR = 0.05                                                 # observado en el núcleo (p_uh a 120 °C); ver HALLAZGO


def eps_en(th):
    return 1.2e-5 * th + 0.4e-8 * th * th - 2.416e-4


def a_st(T, Tref):
    dT = T - Tref
    return (eps_en(T) - eps_en(Tref)) / dT if dT > 0 else 1.2e-5


def kfac(P, T):
    Tr = P["T_ref"]
    s = (T - Tr) / (80.0 - Tr) if T > Tr else 0.0
    return {k: max(K_FLOOR, 1 + (P[p] - 1) * s) for k, p in KEYS.items()}


def scenario(P):
    """T del escenario, gradiente a esa T y lista de T. T_serv = 20 (por defecto) → escenario solar 80 °C; dT_grad = 0 con T_serv = 20 → 15 K."""
    Tscn = P["T_serv"] if P["T_serv"] != 20 else 80.0
    gs = P["dT_grad"] if (P["dT_grad"] != 0 or P["T_serv"] != 20) else 15.0
    Ts = sorted(set([20, 40, 60, 80, 100, Tscn]))
    return Tscn, gs, Ts


def grad_T(P, T, Tscn, gs):
    return gs * (T - P["T_ref"]) / (Tscn - P["T_ref"]) if T > P["T_ref"] else 0.0


def state_res(fu):
    return "fail" if fu > 1 else ("warn" if fu > 0.9 else "ok")


def state_geo(fu):
    return "fail" if fu > 1 else "ok"


def state_row(r, fu=None):
    """Estado de una fila térmica. Reglas del núcleo inferidas y comprobadas: filas «giro» (geométricas) y la fila de la válvula de alivio térmico
    ok ≤ 1; sellos NBR: monitoreo entre 80 y 120 °C (warn), fail sobre 120 °C; el resto, resistencia (warn > 0,9)."""
    fu = r["fu"] if fu is None else fu
    if r["key"].startswith("Sellos NBR"):
        return "ok" if fu <= 0.9 else ("warn" if r["dem"] <= 120 else "fail")
    if r["kind"] == "geo" or r["key"].startswith("Válvula de alivio térmico del tramo aislado"):
        return state_geo(fu)
    return state_res(fu)


def walther(T40, v40, T100, v100, T):
    Z = lambda v: math.log10(math.log10(v + 0.7))
    x = lambda t: math.log10(t + 273.15)
    B = (Z(v40) - Z(v100)) / (x(100) - x(40))
    A = Z(v40) + B * x(40)
    return 10 ** (10 ** (A - B * x(T))) - 0.7


# ------------------------------------------------------------------ módulo confinado de la lámina UHMW (Lindley/Gent, como indep_interfaz.py)
def Mcon(E, nu=NU_UH):
    return E * (1 - nu) / ((1 + nu) * (1 - 2 * nu))


def Ec(t, Dc, E):
    S = Dc / (4 * t)
    return E * (1 + (Mcon(E) / E - 1) * S * S / (1 + S * S)), S


def t_conf(q, Dc, E, d, p):
    if not (p > q):
        return math.inf
    lo, hi = 1e-3, 1e5
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if Ec(mid, Dc, E)[0] * d / (p - q) > mid:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ======================================================================================================================
# 0. Regresión: con T_serv = 20 el cálculo estándar es el del golden; y el escenario térmico no toca el cálculo estándar
# ======================================================================================================================
print("== 0. Regresión con T_serv = 20 y aislamiento del escenario ==")
D0 = export()
DT = export({"T_serv": 80, "dT_grad": 15})
byname = {}
for c in D0["verificaciones"]:
    byname[f'{c["grp"]} · {c["nombre"]}'] = c
nmiss = 0
for k, v in G["fu"].items():
    m = [c for kk, c in byname.items() if kk == k] or [c for kk, c in byname.items() if kk.startswith(k.split(" (")[0])]
    if len(m) != 1:
        nmiss += 1; print("XX  golden sin correspondencia única:", k[:80]); fails.append("golden:" + k); continue
    chk("golden FU " + k[:60], m[0]["fu"], v, tol=1e-9, absn=1e-12)
chk("golden masa total", D0["derivados"]["masas"]["total"], G["masa_total"], tol=1e-9)
chk("golden N", D0["derivados"]["N"], G["N"], tol=1e-9)
chk("golden q_max", D0["derivados"]["q_max"], G["q_max"], tol=1e-9)
chk("golden F_calado", D0["derivados"]["Fstall"], G["F_calado"], tol=1e-9)
cs = {c["id"]: c for c in D0["derivados"]["casos"]}
for k, v in G["casos"].items():
    chk(f"golden caso {k} FS", cs[k]["FS"], v[2], tol=1e-9)
# el escenario térmico (T_serv = 80, gradiente 15) no cambia ningún resultado estándar
same = 0
for a, b in zip(D0["verificaciones"], DT["verificaciones"]):
    for kk in ("grp", "nombre", "dem", "cap", "fu", "estado"):
        if a.get(kk) != b.get(kk):
            fails.append("aislamiento " + a["nombre"][:40]); print("XX  aislamiento: cambia", a["nombre"][:60], kk, a.get(kk), b.get(kk)); break
    else:
        same += 1
chk_eq("T_serv=80 no altera verificaciones estándar (n coincidentes)", same, len(D0["verificaciones"]))
chk_eq("T_serv=80 no altera derivados", json.dumps(D0["derivados"], sort_keys=True), json.dumps(DT["derivados"], sort_keys=True))
chk_eq("T_serv=80 no altera interfazChecks", json.dumps(D0["interfazChecks"], sort_keys=True), json.dumps(DT["interfazChecks"], sort_keys=True))
chk_eq("T_serv=80 no altera veredicto", json.dumps(D0["verdict"], sort_keys=True), json.dumps(DT["verdict"], sort_keys=True))
chk_eq("TT.thermal no depende de los opt_* de P (6 alternativas iguales)",
       all(json.dumps(alt_export(a)["termica"]["alternativas"][[x["id"] for x in alt_export(a)["termica"]["alternativas"]].index(a)], sort_keys=True)
           == json.dumps(D0["termica"]["alternativas"][[x["id"] for x in D0["termica"]["alternativas"]].index(a)], sort_keys=True) for a, _ in ALTS), True)

# ======================================================================================================================
# 1. Factores de reducción (interpolación T_ref→80 °C, extrapolación) y α del acero (EN 1993-1-2)
# ======================================================================================================================
print("== 1. Factores de reducción y α ==")
CONFIGS = [{}, {"T_serv": 120, "dT_grad": 15}, {"T_serv": 58}, {"T_serv": 80, "dT_grad": 15, "T_ref": 30}, {"k_mu_T": 1.2, "kT_Fy": 0.92, "kT_wood": 0.5}]
for over in CONFIGS:
    P = dict(P0); P.update(over)
    D = export(over); th = D["termica"]
    Tscn, gs, Ts = scenario(P)
    chk_eq(f"{over}: lista de T", th["T"], Ts)
    chk(f"{over}: T_scn", th["T_scn"], Tscn)
    chk(f"{over}: gradiente_scn", th["gradiente_scn"], gs)
    for f in th["factores"]:
        T = f["T"]
        kk = kfac(P, T)
        for k, v in kk.items():
            chk(f"{over} k_{k}({T})", v, f["k"][k], absn=1e-12)
        chk_eq(f"{over} extrapolado({T})", f["extrapolado"], T > 80)
        if T > P["T_ref"]:
            chk(f"{over} α_acero medio ({T})", a_st(T, P["T_ref"]), f["alpha"]["st"])
        chk(f"{over} α_inox({T})", ALPHA_SS, f["alpha"]["ss"]); chk(f"{over} α_UHMW({T})", ALPHA_UH, f["alpha"]["uh"]); chk(f"{over} α_bronce({T})", ALPHA_BZ, f["alpha"]["bz"])
# ancla del 80 °C declarada en el registro: α medio 20→80 = 12,4e-6 y Δl/l = 7,44e-4
chk("registro: Δl/l(80 °C) = 7,44e-4", eps_en(80), 7.44e-4)
chk("registro: α medio 20→80 = 12,4e-6", a_st(80, 20), 12.4e-6)

# ======================================================================================================================
# Datos por alternativa (cálculo estándar a 20 °C del núcleo) y construcción independiente de las filas térmicas
# ======================================================================================================================
Ro = P0["D_top"] / 2
Ri = P0["D_boss"] / 2 + P0["c_boss_r"] + P0["m_ri"]
chord = 2 * Ro * math.sin(math.pi / P0["n_sec"])
Ab = math.pi / 4 * P0["D_bore"] ** 2
pitch = 2 * math.pi / P0["N_pin"]
chord_pin = 2 * P0["R_pin"] * math.sin(pitch / 2)
a_min = P0["R_pin"] * math.cos(pitch / 2)
a_b, b_b = P0["D_piv"] / 2, (P0["D_piv"] + 30) / 2           # buje: Ø interior D_piv, exterior D_piv + 30 (registro de interfaz del pivote)
Kc_lame = P0["E"] / (2 * (((P0["ba_cil"] ** 2 + 1) / (P0["ba_cil"] ** 2 - 1)) + P0["nu"]))   # K = p/(ΔV/V), ΔV/V = 2u_a/a, tensión plana


def find(lst, pre):
    m = [x for x in lst if x["nombre"].startswith(pre)]
    return m[0] if len(m) == 1 else (None if not m else m)


def std_list(aid, wood=False):
    return alt_export(aid, wood)["verificaciones"]


def alt_pieces(aid):
    return {"base": [], "A": [("Disco de la base (liso) (24 sectores)", "ss"), ("Disco de la mesa (con ranuras de engrase) (24 sectores)", "ss")],
            "B": [("Disco de la base (liso) (24 sectores)", "ss"), ("Lámina UHMW (24 sectores)", "uh")],
            "C1": [("Placa de bronce (24 sectores)", "bz"), ("Disco duro (24 sectores)", "ss")],
            "C2": [("Placa de bronce (24 sectores)", "bz"), ("2.ª placa de bronce (24 sectores)", "bz")],
            "C3": [("Pastillas de bronce (24 pastillas)", "bzpad"), ("Disco duro (24 sectores)", "ss")]}[aid]


def thermal_rows(aid, wood, T, P, Tscn, gs, k_over=None):
    """Filas del escenario (réplica independiente). Devuelve lista de dicts: key (prefijo del nombre en el núcleo), sys, fu, dem, cap, kind."""
    D = alt_export(aid, wood)
    std = D["verificaciones"] + [c for c in D.get("interfazChecks", {}).get({"base": "", "A": "A", "B": "B"}.get(aid, "C"), [])]
    dT = T - P["T_ref"] if T > P["T_ref"] else 0.0
    al = a_st(T, P["T_ref"]); eps = al * dT
    gT = grad_T(P, T, Tscn, gs)
    k = kfac(P, T)
    if k_over:
        k.update(k_over)
    R = []

    def add(key, sys_, fu, dem=None, cap=None, kind="res", exact=None):
        R.append(dict(key=key, sys=sys_, fu=fu, dem=dem, cap=cap, kind=kind))

    # --- (2) juntas de dilatación y crecimiento radial
    for pref, mat in alt_pieces(aid):
        a_x = {"ss": ALPHA_SS, "uh": ALPHA_UH, "bz": ALPHA_BZ, "bzpad": ALPHA_BZ}[mat]
        jreq = (a_x - al) * dT * chord
        if mat == "bzpad":
            jdisp = (1 - P["bz_cover"]) * chord
        else:
            jdesign = (ALPHA_UH_DESIGN - ALPHA_ST_DESIGN) * P["dT"] * chord if mat == "uh" else 0.0
            jdisp = max(P["j_sec"], round(jdesign * 10) / 10)
        add(pref + ": junta de dilatación requerida", "est", jreq / jdisp, jreq, jdisp)
        add(pref + ": crecimiento radial relativo", "est", None, (a_x - al) * dT * Ro, None, kind="info")
    # --- (3) buje–pivote (Lamé) y holguras
    rho = 2 * a_b * b_b / ((b_b ** 2 + a_b ** 2) - NU_BZ * (b_b ** 2 - a_b ** 2))
    d_a = (ALPHA_BZ - al) * dT                                  # diferencia de deformación libre bronce–acero
    bore_growth = a_b * ALPHA_BZ * dT - rho * d_a * b_b         # crecimiento radial del Ø interior del buje retenido por el cubo
    cierre = 2 * (a_b * al * dT - bore_growth)                  # cierre diametral de la holgura (>0 = aprieta)
    add("Buje de bronce–pivote: cierre de la holgura", "est", max(cierre, 0) / P["c_bush_d"], max(cierre, 0), P["c_bush_d"])
    add("Buje de bronce–pivote: holgura con el buje libre", "est", None, d_a * 2 * a_b, d_a * 2 * b_b, kind="info")
    p_i = E_BZ * d_a / ((b_b ** 2 + a_b ** 2) / (b_b ** 2 - a_b ** 2) - NU_BZ)
    add("Buje de bronce retenido: tensión circunferencial", "est", None, 2 * p_i * b_b ** 2 / (b_b ** 2 - a_b ** 2), P["Fy_bz2"], kind="info")
    # --- uña–pasador y patín
    R_ = P["R_pin"]
    dem20 = R_ * (1 - math.cos(pitch / 2)) + 2.0
    hol = R_ * (1 - math.cos(pitch / 2)) * (1 + eps) + 2.0 + al * dT * R_
    add("Uña–pasador (mesa caliente, base a la sombra): holgura radial", "giro", hol / P["slot"], hol, P["slot"], kind="geo")
    luz = (chord_pin - P["d_pin"]) * (1 + eps)
    add("Uña–pasador (mesa caliente): luz de la uña entre pasadores", "giro", (P["dog_b"] + 20) / luz, P["dog_b"] + 20, luz, kind="geo")
    car = P["s_free"] + chord_pin * (1 + eps) + P["s_margin"]
    add("Uña–pasador (mesa caliente): carrera requerida", "giro", car / P["stroke"], car, P["stroke"], kind="geo")
    add("Uña–pasador, caso uniforme", "est", None, (P["x_g"] - a_min) * al * dT, None, kind="info")
    pat = (P["D_top"] / 2) * (1 + eps) + 15
    add("Patín fuera de la mesa con la mesa caliente", "giro", pat / (P["x_g"] - P["w_s"] / 2), pat, P["x_g"] - P["w_s"] / 2, kind="geo")
    ban = (P["D_top"] / 2) * (1 + eps) + 10
    add("Bancada de guía fuera de la mesa con la mesa caliente", "giro", ban / (P["x_g"] - P["w_bed"] / 2), ban, P["x_g"] - P["w_bed"] / 2, kind="geo")
    add("Dilatación global: crecimiento del diámetro", "est", None, al * dT * P["D_top"], al * dT * P["B"], kind="info")
    # --- (4) gradiente
    kappa = al * gT / P["D_top"] * 0 + al * gT / 230 * 1000     # 1/m con h = h_mesa (mm → m)
    sth = P["E"] * k["E"] * al * gT / (2 * (1 - P["nu"]))
    add("Gradiente: curvatura térmica", "est", None, kappa, None, kind="info")
    add("Gradiente: flecha en el diámetro", "est", None, kappa * (P["D_top"] / 2 / 1000) ** 2 / 2 * 1000, None, kind="info")
    add("Gradiente: tensión de flexión térmica", "est", None, sth, 0.6 * P["Fy"] * k["Fy"], kind="info")
    capf = 0.6 * P["Fy"] * k["Fy"]
    for pre, nm in (("Gradiente: plancha superior", "Plancha superior: global + local"), ("Gradiente: plancha inferior", "Plancha inferior: global + local")):
        c = [x for x in D["verificaciones"] if x["grp"] == "Mesa" and x["nombre"] == nm][0]
        # dem20 = FU20 × (0,6·Fy) (el golden trae el FU; la capacidad es 0,6·Fy, AISC 360-22 F11)
        d20 = c["fu"] * 0.6 * P["Fy"]
        add(pre, "est", (d20 + sth) / capf, d20 + sth, capf)
    cub = [x for x in D["verificaciones"] if x["grp"] == "Pivote" and x["nombre"].startswith("Plancha inferior y pared del cubo")][0]
    add("Gradiente: pared del cubo junto al rebaje", "est", (cub["fu"] * (P["Fy"] / P["Nd"]) + sth) / (P["Fy"] / P["Nd"] * k["Fy"]), None, None)
    add("Gradiente: desnivel de la cara de contacto", "est", None, kappa / 1000 * (Ro ** 2 - Ri ** 2) / 2, P["d_flat"], kind="info")
    add("Gradiente: variación del hueco de contacto", "est", (kappa / 1000 * (P["ss_void"] / 2) ** 2 / 2) / P["d_flat"], kappa / 1000 * (P["ss_void"] / 2) ** 2 / 2, P["d_flat"])
    # --- (5) aceite atrapado
    ph = [c for c in D["derivados"]["casos"] if c["id"] == "dis"][0]
    p_hold = ph["F"] * 1e3 / Ab * 10                       # bar
    dv = (AV - 3 * al) * dT
    Kc = Kc_lame * k["E"]
    dp = lambda K, Kc_=None: dv / (1 / K + (1 / Kc_ if Kc_ else 0)) * 10   # bar (K, Kc en MPa)
    dp_hi, dp_lo = dp(P["K_oil_hi"], Kc), dp(P["K_oil"], Kc)
    sel = {1: dp(P["K_oil_hi"]), 2: dp_hi, 3: dv * K_HOSE * 10}[int(P["oil_cont"])]
    pm, al_t = P["p_max_cil"], P["alivio_term"]
    cap_ = (lambda x: min(x, al_t)) if al_t > 0 else (lambda x: x)
    add("Aceite atrapado: sobrepresión térmica", "term", None, sel if P["oil_cont"] != 2 else dp_hi, dp_lo, kind="info")
    r1 = cap_(p_hold + sel); r2 = cap_(P["p_relief"] + sel); r3 = cap_(P["p_ret"] + sel)
    add("Aceite atrapado en la carrera de diseño", "term", r1 / pm, r1, pm)
    add("Aceite atrapado tras el calado", "term", r2 / (1.5 * pm), r2, 1.5 * pm)
    add("Aceite atrapado en la cámara anular", "term", r3 / pm, r3, pm)
    if al_t > 0:
        add("Válvula de alivio térmico: apertura bajo la presión máxima", "term", al_t / pm, al_t, pm)
        add("Válvula de alivio térmico: apertura sobre el alivio del sistema", "term", P["p_relief"] / al_t, P["p_relief"], al_t)
    else:
        add("Válvula de alivio térmico del tramo aislado", "term", r1 / pm, r1, pm)
    add("Aceite: dilatación libre", "term", None, dv * 100, dv * 1000 * 1000 / 10 * 1.0, kind="info")
    # --- (6) viscosidad y límites de servicio
    nu_lo = walther(40, 46.0, 100, 6.8, T)
    add("Aceite VG 46: viscosidad", "term", P["nu_min"] / nu_lo, P["nu_min"], nu_lo)
    add("Sellos NBR", "term", T / P["T_seal"], T, P["T_seal"])
    add("Grasa grafitada", "term", T / P["T_drop"], T, P["T_drop"])
    if aid == "B":
        add("Lámina UHMW: temperatura frente al límite", "est", T / 80.0, T, 80.0)
    return R, dict(al=al, eps=eps, gT=gT, k=k, p_hold=p_hold, dp_hi=dp_hi, dp_lo=dp_lo, nu_lo=nu_lo, sth=sth)


def row_by_prefix(filas, pre):
    m = [f for f in filas if f["nombre"].startswith(pre)]
    return m


# ======================================================================================================================
# 2-6. Comparación de las filas térmicas por alternativa y T
# ======================================================================================================================
print("== 2-6. Filas térmicas (juntas, buje, uña, gradiente, aceite, viscosidad) ==")
def core_alts(wood=False):
    return {a["id"]: a for a in export()["termica"]["alternativas"]} if not wood else {a["id"]: a for a in export({"opt_wood": 1})["termica"]["alternativas"]}


TH0 = export()["termica"]
Tscn0, gs0, Ts0 = scenario(P0)
for wood in (False, True):
    CA = core_alts(wood)
    for aid, _ in ALTS:
        cid = aid + ("+madera" if wood else "")
        a = CA[cid]
        for rT in a["byT"]:
            T = rT["T"]
            rows, aux = thermal_rows(aid, wood, T, P0, Tscn0, gs0)
            for r in rows:
                m = row_by_prefix(rT["filas"], r["key"])
                if len(m) != 1:
                    chk_eq(f"{cid} T={T}: fila '{r['key'][:50]}' existe una vez", len(m), 1); continue
                f = m[0]
                tag = f"{cid} T={T} {r['key'][:44]}"
                if r["dem"] is not None and f["dem"] is not None:
                    if r["key"].startswith("Aceite: dilatación libre"):
                        chk(tag + " dem", r["dem"], f["dem"]); chk(tag + " cap", r["dem"] * 10, f["cap"])
                    else:
                        chk(tag + " dem", r["dem"], f["dem"])
                elif r["dem"] is not None:
                    chk_eq(tag + " dem", r["dem"], f["dem"])
                if r["cap"] is not None and f.get("cap") is not None and not r["key"].startswith("Aceite: dilatación libre"):
                    chk(tag + " cap", r["cap"], f["cap"])
                if r["kind"] != "info" and r["fu"] is not None:
                    chk(tag + " fu", r["fu"], f["fu"], absn=1e-12)
                    chk_eq(tag + " estado", state_row(r), f["estado"])
                if r["kind"] == "info" and r["fu"] is None:
                    chk_eq(tag + " fu None", f["fu"], None)
                chk_eq(tag + " sys", r["sys"], f["sys"])
            # ausencia de filas térmicas que yo no replico (excepto las declaradas más abajo)
            known = [r["key"] for r in rows]
            extra = [f for f in rT["filas"] if not any(f["nombre"].startswith(k) for k in known)]
            ALLOWED = ("Gradiente: pared del cubo", "Lámina UHMW: factores", "Lámina UHMW: acortamiento", "Lámina UHMW: PV admisible", "UHMW-PE a T_serv", "Bronce con grafito", "Acero estructural y cadena",
                       "Pernos 10.9", "ASME BTH-1", "Bomba con viscosidad baja", "Sensibilidad al μ", "Madera:", "Aceite VG", "Gradiente: variación")
            extra = [f for f in extra if not any(f["nombre"].startswith(x) for x in ALLOWED)]
            if extra:
                for f in extra:
                    print("XX  fila del núcleo sin réplica:", cid, T, f["nombre"][:90]); fails.append("extra " + f["nombre"][:50])
            # masa congelada
            chk(f"{cid} T={T} masa (geometría congelada de 20 °C)", rT["masa"], alt_export(aid, wood)["derivados"]["masas"]["total"], tol=1e-9)
            # aceite: tabla `aceite`
        # geometría 20 °C adoptada vs espesores del cálculo estándar
        ge = a["geometria"]; st = std_list(aid, wood)
        if aid != "base":
            if aid in ("A", "B"):
                c = [x for x in st if x["nombre"].startswith("Disco de la base") and "espesor adoptado" in x["nombre"]][0]
                chk(f"{cid} geometría tss = espesor adoptado de la base", ge["tss"], c["cap"], tol=1e-9)
            if aid == "B":
                c = [x for x in st if x["nombre"].startswith("Lámina UHMW: espesor adoptado")][0]
                chk(f"{cid} geometría tuh = espesor adoptado", ge["tuh"], c["cap"], tol=1e-9)
            if aid.startswith("C"):
                c = [x for x in st if x["nombre"].startswith("Placa de bronce: espesor adoptado")][0]
                chk(f"{cid} geometría tbz = espesor adoptado", ge["tbz"], c["cap"], tol=1e-9)

# tabla `aceite`, `viscosidad`
print("   (aceite y viscosidad: tablas del núcleo)")
for e in TH0["aceite"]:
    T = e["T"]; dT = T - P0["T_ref"]; al = a_st(T, P0["T_ref"]); dv = (AV - 3 * al) * dT
    chk(f"aceite T={T} rígido bajo", dv * P0["K_oil"] * 10, e["rigido"]["bajo"], absn=1e-9)
    chk(f"aceite T={T} rígido alto", dv * P0["K_oil_hi"] * 10, e["rigido"]["alto"], absn=1e-9)
    chk(f"aceite T={T} cilindro bajo", dv / (1 / P0["K_oil"] + 1 / Kc_lame) * 10, e["cilindro"]["bajo"], absn=1e-9)
    chk(f"aceite T={T} cilindro alto", dv / (1 / P0["K_oil_hi"] + 1 / Kc_lame) * 10, e["cilindro"]["alto"], absn=1e-9)
    chk(f"aceite T={T} manguera", dv * K_HOSE * 10, e["manguera"], absn=1e-9)
    chk(f"aceite T={T} K_c Lamé", Kc_lame, e["Kc_lame_MPa"])
    chk(f"aceite T={T} selección (oil_cont=2)", dv / (1 / P0["K_oil_hi"] + 1 / Kc_lame) * 10, e["seleccion_bar"], absn=1e-9)
for v in TH0["viscosidad"]:
    chk(f"viscosidad VG46 IV100 T={v['T']}", walther(40, 46.0, 100, 6.8, v["T"]), v["lo"])
    chk(f"viscosidad VG46 IV185 (Eurol 47,4/9,5) T={v['T']}", walther(40, 47.4, 100, 9.5, v["T"]), v["hi"])
chk("registro: ν(80 °C) VG46 = 11,1 mm²/s", walther(40, 46.0, 100, 6.8, 80), 11.1, tol=1e-2)
chk("registro: ν(80 °C) VG46 IV185 = 14,6 mm²/s", walther(40, 47.4, 100, 9.5, 80), 14.6, tol=1e-2)
# variantes de P: contenedor, alivio térmico, K, c_bush_d
for over in ({"oil_cont": 1}, {"oil_cont": 3}, {"alivio_term": 800}, {"c_bush_d": 0.05}, {"K_oil_hi": 2300}, {"ba_cil": 1.8}, {"p_max_cil": 600, "nu_min": 12}, {"dT_grad": 7}):
    P = dict(P0); P.update(over)
    Tscn, gs, Ts = scenario(P)
    D = export(over); a = {x["id"]: x for x in D["termica"]["alternativas"]}["base"]
    Kc_save = Kc_lame
    Kc_lame = P["E"] / (2 * (((P["ba_cil"] ** 2 + 1) / (P["ba_cil"] ** 2 - 1)) + P["nu"]))
    for rT in a["byT"]:
        rows, aux = thermal_rows("base", False, rT["T"], P, Tscn, gs)
        for r in rows:
            m = row_by_prefix(rT["filas"], r["key"])
            if len(m) != 1:
                chk_eq(f"{over} T={rT['T']}: fila '{r['key'][:40]}' existe", len(m), 1); continue
            f = m[0]; tag = f"{over} T={rT['T']} {r['key'][:40]}"
            if r["fu"] is not None:
                chk(tag + " fu", r["fu"], f["fu"], absn=1e-12); chk_eq(tag + " estado", state_row(r), f["estado"])
            if r["dem"] is not None and f["dem"] is not None and not r["key"].startswith("Aceite: dilatación"):
                chk(tag + " dem", r["dem"], f["dem"])
    Kc_lame = Kc_save

# ======================================================================================================================
# 7. Estado de cada alternativa por T: FS giro, FU estructura, FU térmico, gobernantes, flags, cambios de estado
# ======================================================================================================================
print("== 7. Estado por alternativa y temperatura ==")


def std_classify(c, aid):
    """Familia de la verificación estándar frente a la temperatura (regla propia por material y por tipo de capacidad)."""
    n, g = c["nombre"], c["grp"]
    if g == "Interfaz inox":
        if n.startswith("Disco de"):
            if "flexión sobre un vacío local" in n: return "ss_flex"
            if "espesor adoptado frente al requerido" in n: return "ss_esp"
            if "aplastamiento del tope sobre el canto" in n: return "ss_tope"
            if "aplastamiento del tope con la altura de contacto reducida" in n: return "ss_red"
        if n.startswith("Lámina UHMW"):
            if "presión de contacto máxima" in n: return "uh_q"
            if "espesor adoptado" in n: return "uh_esp"
            if "aplastamiento del canto contra el tope" in n: return "uh_canto"
            if "aplastamiento del tope con la altura de contacto reducida" in n: return "uh_red"
            if "valor PV" in n: return "uh_pv"
    if g == "Interfaz bronce":
        if n.startswith(("Placa de bronce", "2.ª placa", "Pastillas")):
            if "flexión sobre un vacío local" in n: return "bz_flex"
            if "aplastamiento del tope sobre el canto" in n: return "bz_tope"
            if "aplastamiento del tope con la altura de contacto reducida" in n: return "bz_red"
        if n.startswith("Presión de contacto sobre el bronce neto") or n.startswith("Bronce con grafito: valor PV"): return "bz_p"
    if g == "Cubierta" and n.startswith("Madera: aplastamiento"): return "wood"
    return None


GIRO_FAM = {"ss_tope", "ss_red", "uh_red", "bz_tope", "bz_red"}


def std_at(aid, wood, k, P, q_uh=None, kfy_extra=1.0):
    """FU de cada verificación estándar a la T con factores k. Devuelve lista de dicts (grp, nombre, fu20, fuT, sys, unidad, fam, st20)."""
    D = alt_export(aid, wood)
    chks = D["verificaciones"]
    out = []
    tflex = {}
    for c in chks:
        if c["grp"] == "Interfaz inox" and c["nombre"].startswith("Disco inoxidable: espesor mínimo por flexión"):
            tflex["ss"] = c["dem"]
    qd = [c for c in chks if c["nombre"].startswith("Lámina UHMW: presión de contacto máxima")]
    q = qd[0]["dem"] if qd else None
    for c in chks:
        if c["fu"] is None:
            continue
        fam = std_classify(c, aid)
        fu = c["fu"]
        sys_ = "giro" if (c["grp"] in ("Giro", "Geometría") or fam in GIRO_FAM) else "est"
        if fam in ("ss_flex", "ss_tope", "ss_red"):
            fu = c["fu"] / k["Fy_ss"]
        elif fam == "ss_esp":
            off = c["dem"] - tflex["ss"]
            fu = (tflex["ss"] / math.sqrt(k["Fy_ss"]) + off) / c["cap"]
        elif fam in ("uh_q", "uh_canto", "uh_red", "uh_pv"):
            fu = c["fu"] / k["p_uh"]
        elif fam == "uh_esp":
            padm = P["p_uhmw"] * k["p_uh"]
            t = t_conf(q, P["ss_void"], P["E_uhmw"] * k["E_uh"], P["d_flat"], padm)
            fu = None if math.isinf(t) else max(t, P["uh_tmin"]) / c["cap"]
        elif fam in ("bz_flex", "bz_tope", "bz_red", "bz_p"):
            fu = c["fu"] / k["bz"]
        elif fam == "wood":
            fu = c["fu"] / k["wood"]
        elif c["unidad"] == "MPa" and kfy_extra != 1.0 and not any(s in c["nombre"] for s in ("Soldadura", "soldadura", "Hertz")) and c["grp"] not in ("Soldaduras", "Fatiga"):
            fu = c["fu"] / kfy_extra
        out.append(dict(grp=c["grp"], nombre=c["nombre"], fu20=c["fu"], fuT=fu, sys=sys_, unidad=c["unidad"], fam=fam, st20=c["estado"]))
    return out


def classify_state(item, fu):
    if fu is None:
        return "fail"                       # capacidad nula (p_adm·k ≤ q): sin solución
    if item.get("unidad") in ("mm", "bar", "–", "kN", "mm / mm") or item.get("kind") == "geo":
        return state_geo(fu) if item.get("sys") == "giro" else state_res(fu)
    return state_res(fu)


def state_std(it, fu):
    """estado de una verificación estándar: las de la familia 'resistencia' (MPa, MPa·m/s) y las 'est' en mm usan 0,9/1,0; las 'giro' en mm usan ≤ 1."""
    if fu is None:
        return "fail"
    if it["sys"] == "giro":
        return state_geo(fu)
    if it["unidad"] in ("MPa", "MPa·m/s") or it["fam"] in ("uh_esp", "ss_esp"):
        return state_res(fu)
    return state_geo(fu)


def alt_state(aid, wood, T, P, Tscn, gs, k_over=None, kfy_extra=1.0, FSfac=1.0):
    k = kfac(P, T)
    if k_over: k.update(k_over)
    D = alt_export(aid, wood)
    rows, aux = thermal_rows(aid, wood, T, P, Tscn, gs, k_over)
    if kfy_extra != 1.0:   # sensibilidad Fy×0,92: sólo cambia la capacidad 0,6·Fy de las filas de gradiente
        rows, aux = thermal_rows(aid, wood, T, P, Tscn, gs, dict(k_over or {}, Fy=kfy_extra * k["Fy"]))
        k["Fy"] = kfy_extra * k["Fy"]
    stds = std_at(aid, wood, k, P, kfy_extra=kfy_extra)
    fs20 = [c for c in D["derivados"]["casos"] if c["id"] == "dis"][0]["FS"]
    FS = fs20 / k["mu"] / FSfac
    est_items = [s for s in stds if s["sys"] == "est" and s["unidad"] == "MPa" and s["fuT"] is not None and not s["nombre"].startswith("Lámina UHMW: espesor")]
    # fuEst: máx. FU de las verificaciones estándar de resistencia (MPa), sin las de «giro»
    fuEst = max(est_items, key=lambda s: s["fuT"]) if est_items else None
    th_est = [r for r in rows if r["sys"] == "est" and r["fu"] is not None]
    fuTerm = max(th_est, key=lambda r: r["fu"])
    # estados
    fail = warn = 0
    giro_fail = est_fail = term_bad = False
    for s in stds:
        stt = state_std(s, s["fuT"])
        if stt == "fail": fail += 1
        if stt == "warn": warn += 1
        if stt == "fail":
            if s["sys"] == "giro": giro_fail = True
            else: est_fail = True
    for r in rows:
        if r["fu"] is None: continue
        stt = state_row(r)
        if stt == "fail": fail += 1
        if stt == "warn": warn += 1
        if stt == "fail":
            if r["sys"] == "giro": giro_fail = True
            elif r["sys"] == "est": est_fail = True
        if r["sys"] == "term" and stt == "fail": term_bad = True
    return dict(FS=FS, fuEst=fuEst, fuTerm=fuTerm, gira=(FS >= P["FS_min"] and not giro_fail), estructura=not est_fail, termico=not term_bad,
                nFail=fail, nWarn=warn, stds=stds, rows=rows, k=k, aux=aux, fs20=fs20)


def cmp_state(tag, S, rT):
    chk(tag + " FS", S["FS"], rT["FS"])
    chk(tag + " fuEst", S["fuEst"]["fuT"], rT["fuEst"], absn=1e-12)
    chk_eq(tag + " gobernante (estructura)", S["fuEst"]["nombre"][:60], rT["gobernante"]["nombre"][:60])
    chk(tag + " fuTerm", S["fuTerm"]["fu"], rT["fuTerm"], absn=1e-12)
    chk_eq(tag + " gobernante térmico", rT["gobernanteTerm"]["nombre"].startswith(S["fuTerm"]["key"]), True)
    chk_eq(tag + " gira", S["gira"], rT["gira"])
    chk_eq(tag + " estructura", S["estructura"], rT["estructura"])
    chk_eq(tag + " termico", S["termico"], rT["termico"])
    chk_eq(tag + " nFail", S["nFail"], rT["nFail"])
    chk_eq(tag + " nWarn", S["nWarn"], rT["nWarn"])


def cambios(S, aid, wood, P, T):
    """Verificaciones que cambian de estado entre 20 °C y T (réplica)."""
    S20 = alt_state(aid, wood, 20, P, *scenario(P)[:1], scenario(P)[1])
    out = {}
    for s in S["stds"]:
        a = s["st20"]; b = state_std(s, s["fuT"])
        if a in ("ok", "warn", "fail") and b != a:
            out[(s["grp"], s["nombre"][:70])] = (a, b, s["fu20"], s["fuT"])
    r20 = {r["key"]: r for r in S20["rows"]}
    for r in S["rows"]:
        if r["fu"] is None: continue
        o = r20[r["key"]]
        a = state_row(o); b = state_row(r)
        if a != b:
            out[("Temperatura", r["key"][:70])] = (a, b, o["fu"], r["fu"])
    return out


CA = core_alts(False)
CAw = core_alts(True)
for wood in (False, True):
    CAx = CAw if wood else CA
    for aid, _ in ALTS:
        cid = aid + ("+madera" if wood else "")
        a = CAx[cid]
        chk(f"{cid} FS20", [c for c in alt_export(aid, wood)["derivados"]["casos"] if c["id"] == "dis"][0]["FS"], a["FS20"], tol=1e-9)
        for rT in a["byT"]:
            S = alt_state(aid, wood, rT["T"], P0, Tscn0, gs0)
            for r in S["rows"]:
                r.setdefault("nombre", r["key"])
            S["fuTerm"] = dict(S["fuTerm"])
            cmp_state(f"{cid} T={rT['T']}", S, rT)
            # cambios de estado
            ch = cambios(S, aid, wood, P0, rT["T"])
            def canon(c):
                for kk in ch:
                    if kk[0] == c["grp"] and c["nombre"].startswith(kk[1]): return kk
                return (c["grp"], c["nombre"][:70])
            core_ch = {canon(c): (c["de"], c["a"], c["fu20"], c["fuT"]) for c in rT["cambian"]}
            chk_eq(f"{cid} T={rT['T']} cambios de estado: mismas verificaciones", sorted(ch.keys()), sorted(core_ch.keys()))
            for kk, v in ch.items():
                if kk in core_ch:
                    chk_eq(f"{cid} T={rT['T']} cambio {kk[1][:40]}", (v[0], v[1]), core_ch[kk][:2])
                    chk(f"{cid} T={rT['T']} cambio fuT {kk[1][:30]}", v[3], core_ch[kk][3], absn=1e-12)

# ======================================================================================================================
# 8. Sensibilidades: μ, Fy×0,92, bronce 0,90, UHMW (k_p, k_E, umbral), madera Ct
# ======================================================================================================================
print("== 8. Sensibilidades ==")
for wood in (False, True):
    CAx = CAw if wood else CA
    for aid, _ in ALTS:
        cid = aid + ("+madera" if wood else "")
        a = CAx[cid]; sn = a["sens"]
        fs20 = a["FS20"]
        chk(f"{cid} sens.T", sn["T"], Tscn0)
        for e, f in zip(sn["mu"], (0.8, 1.0, 1.2, 1.5)):
            chk(f"{cid} sens μ×{f} FS", fs20 / f, e["FS"]); chk_eq(f"{cid} sens μ×{f} gira", fs20 / f >= P0["FS_min"], e["gira"])
        chk(f"{cid} margen de μ hasta FS_min (mu_crit)", fs20 / P0["FS_min"], sn["mu_crit"])
        # Fy × 0,92 (ASME II-D Tabla Y-1)
        S = alt_state(aid, wood, 80, P0, Tscn0, gs0, kfy_extra=0.92)
        k92 = sn["kFy092"]
        chk(f"{cid} Fy×0,92 fuEst", S["fuEst"]["fuT"], k92["fuEst"], absn=1e-12)
        chk(f"{cid} Fy×0,92 fuTerm", S["fuTerm"]["fu"], k92["fuTerm"], absn=1e-12)
        chk_eq(f"{cid} Fy×0,92 gobernante", S["fuEst"]["nombre"][:50], k92["gobernante"]["nombre"][:50])
        chk_eq(f"{cid} Fy×0,92 estructura", S["estructura"], k92["estructura"]); chk_eq(f"{cid} Fy×0,92 gira", S["gira"], k92["gira"])
        S80 = alt_state(aid, wood, 80, P0, Tscn0, gs0)
        chk(f"{cid} Fy×0,92 dFu", S["fuEst"]["fuT"] - S80["fuEst"]["fuT"], k92["dFu"], absn=1e-9)
        # empeoran: verificaciones que pasan de ok a warn/fail al bajar Fy a 0,92 (respecto del 80 °C con k = 1)
        emp = {}
        for s0, s1 in zip(S80["stds"], S["stds"]):
            a0, b0 = state_std(s0, s0["fuT"]), state_std(s1, s1["fuT"])
            if b0 != a0 and s1["unidad"] == "MPa": emp[(s1["grp"], s1["nombre"][:50])] = (a0, b0)
        for r0, r1 in zip(S80["rows"], S["rows"]):
            if r0["fu"] is None or r0["sys"] != "est": continue
            a0, b0 = state_res(r0["fu"]), state_res(r1["fu"])
            if a0 != b0 and r0["key"].startswith("Gradiente"): emp[("Temperatura", r0["key"][:50])] = (a0, b0)
        def canon92(e):
            for kk in emp:
                if kk[0] == e["grp"] and e["nombre"].startswith(kk[1]): return kk
            return (e["grp"], e["nombre"][:50])
        coreemp = {canon92(e): (e["de"], e["a"]) for e in k92["empeoran"]}
        # el núcleo lista las que empeoran respecto del estado a 20 °C (de = estado a 80 °C con k = 1)
        if len(coreemp) >= 10:
            miss = set(coreemp) - set(emp)
            chk_eq(f"{cid} Fy×0,92 empeoran (lista del núcleo ⊆ réplica; lista cortada a 10)", sorted(miss), [])
        else:
            chk_eq(f"{cid} Fy×0,92 empeoran (mismas verificaciones)", sorted(emp), sorted(coreemp))
        # madera
        if wood:
            qw = [c for c in alt_export(aid, wood)["verificaciones"] if c["nombre"].startswith("Madera: aplastamiento")][0]
            for e, Ct in zip(sn["madera"], (0.70, 0.50)):
                chk(f"{cid} madera Ct {Ct} FU", qw["dem"] / (P0["p_wood"] * Ct), e["fu"]); chk_eq(f"{cid} madera Ct {Ct} estado", state_res(qw["dem"] / (P0["p_wood"] * Ct)), e["estado"])
        # bronce 0,90
        if aid.startswith("C"):
            S9 = alt_state(aid, wood, 80, P0, Tscn0, gs0, k_over={"bz": 0.9})
            b9 = sn["bz090"]
            chk(f"{cid} bronce×0,90 fuEst", S9["fuEst"]["fuT"], b9["fuEst"], absn=1e-12); chk(f"{cid} bronce×0,90 fuTerm", S9["fuTerm"]["fu"], b9["fuTerm"], absn=1e-12)
            chk_eq(f"{cid} bronce×0,90 estructura", S9["estructura"], b9["estructura"])
        # juntas del escenario
        if aid != "base":
            for j in a["juntas"]:
                rows, aux = thermal_rows(aid, wood, Tscn0, P0, Tscn0, gs0)
                r = [x for x in rows if x["key"].startswith(j["pieza"] + ": junta")][0]
                chk(f"{cid} juntas[{j['pieza'][:25]}] j_req", r["dem"], j["j_req"]); chk(f"{cid} juntas[{j['pieza'][:25]}] j_disp", r["cap"], j["j_disp"]); chk_eq(f"{cid} juntas estado", state_res(r["fu"]), j["estado"])

# UHMW: k_p, k_E y umbral k_p ≥ 0,85
B = CA["B"]["sens"]["uhmw"]
SB = alt_state("B", False, 80, P0, Tscn0, gs0)


def fu_uhmw(kp, kE):
    kk = dict(kfac(P0, 80)); kk["p_uh"] = kp; kk["E_uh"] = kE
    its = [s for s in std_at("B", False, kk, P0) if s["fam"] and s["fam"].startswith("uh_")]
    # filas geométricas de la lámina que no cambian (FU = 1: alivio inferior, filete mínimo) también cuentan en el máximo del núcleo
    Dd = alt_export("B")["verificaciones"]
    geo = [c for c in Dd if c["nombre"].startswith("Lámina UHMW (24 sectores):") and c["fu"] is not None and std_classify(c, "B") is None]
    mx, nm = 0.0, None
    for s in its:
        v = 99.0 if s["fuT"] is None else s["fuT"]
        if v > mx: mx, nm = v, s["nombre"]
    for c in geo:
        if c["fu"] > mx: mx, nm = c["fu"], c["nombre"]
    return mx, nm


for lst, key in ((B["kp"], "k_p"), (B["kE"], "k_E")):
    for e in lst:
        mx, nm = fu_uhmw(e["k_p"], e["k_E"])
        chk(f"UHMW k_p={e['k_p']} k_E={e['k_E']} FU máx. de la lámina", mx, e["fuUHMW"])
        chk_eq(f"UHMW k_p={e['k_p']} k_E={e['k_E']} cumple", mx <= 1.0 + 1e-12, e["cumple"])
        chk_eq(f"UHMW k_p={e['k_p']} k_E={e['k_E']} gobernante", nm[:55], e["gobernante"][:55])
# umbral: k_p donde el FU máximo (con k_E = 0,4) llega a 1; bisección propia
lo, hi = 0.3, 1.0
for _ in range(60):
    mid = 0.5 * (lo + hi)
    if fu_uhmw(mid, 0.4)[0] > 1 + 1e-12 and mid < 0.999: lo = mid
    else: hi = mid
chk("UHMW umbral k_p crítico (k_E = 0,4)", hi, B["kp_crit"], tol=2e-3)
chk("UHMW umbral k_p crítico ≈ 0,85", B["kp_crit"], 0.85, tol=2e-3)
# acortamiento elástico con módulo reducido y PV por balance térmico (filas info de B)
qB = [c for c in alt_export("B")["verificaciones"] if c["nombre"].startswith("Lámina UHMW: presión de contacto máxima")][0]["dem"]
tB = CA["B"]["geometria"]["tuh"]
for rT in CA["B"]["byT"]:
    T = rT["T"]; k = kfac(P0, T)
    Ecv, S_ = Ec(tB, P0["ss_void"], P0["E_uhmw"] * k["E_uh"])
    m = row_by_prefix(rT["filas"], "Lámina UHMW: acortamiento elástico")[0]
    chk(f"B T={T} UHMW acortamiento elástico q·t/E_c", qB * tB / Ecv, m["dem"]); chk(f"B T={T} UHMW cap d_flat", P0["d_flat"], m["cap"])
    m = row_by_prefix(rT["filas"], "Lámina UHMW: PV admisible por balance")[0]
    pv20 = [c for c in alt_export("B")["verificaciones"] if c["nombre"].startswith("Lámina UHMW: valor PV")][0]
    chk(f"B T={T} UHMW PV demanda", pv20["dem"], m["dem"]); chk(f"B T={T} UHMW PV(T) = PV20·(80−T)/(80−T_ref)", P0["PV_uh"] * max(80 - T, 0) / (80 - P0["T_ref"]), m["cap"], absn=1e-12)
    m = row_by_prefix(rT["filas"], "Lámina UHMW: factores aplicados")[0]
    chk(f"B T={T} UHMW k_p", k["p_uh"], m["dem"]); chk(f"B T={T} UHMW k_E", k["E_uh"], m["cap"])

# ======================================================================================================================
# 9. Hallazgos de revisión (no son diferencias numéricas)
# ======================================================================================================================
print("== 9. Cifras de apoyo a los hallazgos ==")
al80 = a_st(80, 20); dv80 = (AV - 3 * al80) * 60
dp = lambda K: dv80 / (1 / K + 1 / Kc_lame) * 10
ph = [c for c in D0["derivados"]["casos"] if c["id"] == "dis"][0]
p_hold = ph["F"] * 1e3 / Ab * 10
print(f"   Δp(K=1,4) {dp(1400):.1f} bar | Δp(K=1,9) {dp(1900):.1f} bar | Δp(K=2,3 cota alta del registro) {dp(2300):.1f} bar (+{(dp(2300) / dp(1900) - 1) * 100:.1f} % sobre 1,9)")
print(f"   p_hold = F_dis/A = {p_hold:.1f} bar; con K=2,3: p_hold+Δp = {p_hold + dp(2300):.1f} bar; calado 700+Δp = {700 + dp(2300):.1f} bar")
print(f"   κ con h = 210 mm: {al80 * 15 / 0.210:.3e} 1/m; con h = 230 mm (registro): {al80 * 15 / 0.230:.3e} 1/m ({(210 / 230 - 1) * 100:+.1f} %)")
print(f"   buje: cierre {2 * (a_b * al80 * 60 - (a_b * ALPHA_BZ * 60 - (2 * a_b * b_b / ((b_b ** 2 + a_b ** 2) - NU_BZ * (b_b ** 2 - a_b ** 2))) * (ALPHA_BZ - al80) * 60 * b_b)):.4f} mm frente a c = 0,10 mm; mínimo del ajuste H7/e8 Ø120 = 0,072 mm")
jd20 = (ALPHA_UH - ALPHA_ST_DESIGN) * 0  # sólo para mantener las constantes a la vista
print(f"   junta UHMW: j_disp 20 °C = {max(1, round((ALPHA_UH_DESIGN - ALPHA_ST_DESIGN) * 40 * chord, 1)):.1f} mm (α 180e-6, dT 40); j_req 80 °C = {(ALPHA_UH - al80) * 60 * chord:.2f} mm (α 190e-6); con α 180e-6: {(ALPHA_UH_DESIGN - al80) * 60 * chord:.2f} mm")
print(f"   UHMW: crecimiento radial absoluto del borde a 80 °C = {ALPHA_UH * 60 * Ro:.2f} mm; holgura a patín = {P0['x_g'] - P0['w_s'] / 2 - Ro:.1f} mm (el acero ocupa {al80 * 60 * Ro:.2f} mm)")
print("   hallazgos (clasificación y efecto) en el informe del revisor; este script sólo verifica numéricamente.")

print()
print(f"{nchk[0]} comparaciones; diferencias: {len(fails)}")
print("RESULTADO:", "sin diferencias" if not fails else "DIFERENCIAS en " + "; ".join(sorted(set(fails))[:40]))
sys.exit(1 if fails else 0)
