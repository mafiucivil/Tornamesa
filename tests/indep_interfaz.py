"""Revisión independiente de la INTERFAZ DE GIRO TT300-C: opción 0 (acero-acero con grasa), A (dos discos de acero
inoxidable con grasa) y B (dos discos inoxidables con lámina UHMW-PE entre ellos).

Regla de independencia: no lee packages/*.js. Los resultados del núcleo se obtienen solo por su salida JSON
(node tools/export_design.js [params.json]); todo lo demás se deriva aquí desde la mecánica de placas
(Timoshenko y Woinowsky-Krieger), la estática del accionamiento (modelo ya verificado en tests/indep_accionamiento.py),
la elasticidad de láminas confinadas (Lindley / Gent) y AISC 360-22 (ASD, Fy/1,67 = 0,6 Fy).

Ejecutar:  python3 -I tests/indep_interfaz.py
Imprime tablas y termina con «RESULTADO: ...». Sale con 0 si no hay hallazgos críticos ni importantes; con 1 si los hay;
con 2 si no puede ejecutar el núcleo.

Unidades internas: N, mm, MPa (salvo donde se indique kN, kN·m).
"""
import json, math, pathlib, subprocess, sys, tempfile

try:
    import numpy as np
except Exception:          # el modelo de contacto unilateral es opcional
    np = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
g0, RHO = 9.80665, 7.85e-6
RHO_SS, RHO_UH = 7.93e-6, 0.94e-6                  # kg/mm³
AL_UH, AL_S, AL_SS, E_SS = 180e-6, 11.7e-6, 17.3e-6, 193000.0
COM_SS = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
COM_UH = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50]
TOL = 1e-3


def export(over=None):
    with tempfile.TemporaryDirectory() as td:
        args = ["node", str(ROOT / "tools" / "export_design.js")]
        if over:
            f = pathlib.Path(td) / "p.json"; f.write_text(json.dumps(over)); args.append(str(f))
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def s3(x):
    if x is None:
        return "—"
    if isinstance(x, str):
        return x
    if x == 0 or not math.isfinite(x):
        return f"{x:g}"
    return f"{x:.{max(0, 2 - int(math.floor(math.log10(abs(x)))))}f}" if abs(x) >= 1e-3 else f"{x:.3g}"


def table(title, head, rows):
    print(f"\n### {title}")
    w = [max([len(str(h))] + [len(str(r[i])) for r in rows]) for i, h in enumerate(head)]
    print("| " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(head)) + " |")
    print("|" + "|".join("-" * (x + 2) for x in w) + "|")
    for r in rows:
        print("| " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) + " |")


COMP, FIND = [], []


def comp(prueba, name, mine, core, tol=TOL):
    if core is None or mine is None:
        COMP.append((prueba, name, s3(mine), s3(core), "—", "coincide" if core is None and mine is None else "discrepa")); return
    d = (mine - core) / core * 100 if core else (0.0 if abs(mine) < 1e-12 else 100.0)
    COMP.append((prueba, name, s3(mine), s3(core), f"{d:+.3f}", "coincide" if abs(d) <= tol * 100 else "discrepa"))


def com(t, lst):
    """espesor comercial inmediato (≥ t)"""
    if t is None or not math.isfinite(t):
        return math.inf
    for c in lst:
        if c >= t - 1e-9:
            return float(c)
    return math.inf


# ======================================================================================
# 0. Datos
# ======================================================================================
D0 = export()
if D0 is None:
    print("No se pudo ejecutar node tools/export_design.js"); sys.exit(2)
P = D0["P"]
DA, DB = export({"opt_ss": 1}), export({"opt_uhmw": 1})
Pg = json.loads((ROOT / "tests" / "golden" / "params_defaults.json").read_text())
nuevos = sorted(k for k in P if k not in Pg)


def mesa(P):
    """masa de la mesa (kg) sin el pivote, y densidad lineal del pivote (kg/mm)"""
    rings = sorted(float(x) for x in P["rings"].replace(";", ",").split(",") if x.strip())
    Rt = P["D_top"] / 2; hw = P["h_disc"] - P["t_top"] - P["t_bot"]
    rpr = max(P["D_hub"] / 2, P["R_pin"] - (Rt - P["R_pin"])); db = P["D_piv"] + 30
    aring = math.pi * (Rt ** 2 - rpr ** 2) - P["N_pin"] * math.pi * P["d_pin"] ** 2 / 4
    m = RHO * ((math.pi * rpr ** 2 - math.pi / 4 * (P["D_piv"] + 80) ** 2) * P["t_top"] + aring * max(P["t_pr"], P["t_top"]))
    m += RHO * ((math.pi * rpr ** 2 - math.pi / 4 * db ** 2) * P["t_bot"] + aring * max(P["t_pr"], P["t_bot"]))
    m += RHO * sum(2 * math.pi * r * hw * P["t_web"] for r in rings)
    nin = sum(1 for r in rings if P["D_hub"] / 2 < r < P["R_rib"])
    m += RHO * P["N_rib"] * (P["R_rib"] - P["D_hub"] / 2 - nin * P["t_web"]) * hw * P["t_rib"]
    m += RHO * math.pi / 4 * (P["D_hub"] ** 2 - db ** 2) * hw
    m += RHO * P["N_pin"] * math.pi / 4 * P["d_pin"] ** 2 * P["h_disc"]
    return m, RHO * math.pi / 4 * P["D_piv"] ** 2


def geom(P):
    Ro, Ri = P["D_top"] / 2, P["D_piv"] / 2 + 15
    A = math.pi * (Ro ** 2 - Ri ** 2); I = math.pi * (Ro ** 4 - Ri ** 4) / 4
    ru = 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2)
    return Ro, Ri, A, I, ru


def conf_q(q, P, E=None, d=None):
    E = P["E_uhmw"] if E is None else E; d = P["d_flat"] if d is None else d
    return E * d / (P["p_uhmw"] - q) if P["p_uhmw"] > q else math.inf


def iface(P, k):
    """Opción k ∈ {0,1,2}. Devuelve espesores, q_máx (con el peso del disco rotatorio, iterado), N, masa agregada."""
    Ro, Ri, A, I, ru = geom(P)
    m_mesa, rho_piv = mesa(P)
    W = P["W_tf"] * g0
    a = P["ss_void"] / 2
    sad = 0.6 * P["Fy_ss"]
    t_d = com(P["ss_tmin"], COM_SS) if k else 0.0
    t_u = com(P["uh_tmin"], COM_UH) if k == 2 else 0.0
    out = None
    for _ in range(60):
        Delta = 2 * t_d + t_u if k else 0.0
        m_rot = RHO_SS * A * t_d if k else 0.0
        m_piv = rho_piv * (P["t_base"] + P["h_disc"] - P["t_top"] + 3 + Delta)
        Wd = (m_mesa + 0.5 * m_piv + m_rot) * g0 / 1e3
        N = W + Wd; ND = P["phi_d"] * W + Wd
        q = ND * 1e3 / A + ND * 1e3 * P["e"] * Ro / I
        tfl = a * math.sqrt(0.75 * q / sad)
        treq = max(tfl + P["ss_allow"], P["ss_tmin"])
        t_d_new = (P["t_ss"] if P["t_ss"] > 0 else com(treq, COM_SS)) if k else 0.0
        tconf = conf_q(q, P) if k == 2 else None
        tuhreq = max(tconf, P["uh_tmin"]) if k == 2 else 0.0
        t_u_new = (P["t_uhmw"] if P["t_uhmw"] > 0 else com(tuhreq, COM_UH)) if k == 2 else 0.0
        out = dict(k=k, q=q, tflex=tfl if k else None, tssReq=treq if k else 0.0, tss=t_d, tconf=tconf, tuhReq=tuhreq, tuh=t_u,
                   delta=Delta, mTop=m_rot, mUH=RHO_UH * A * t_u, N=N, ND=ND, Wd=Wd, m_piv=m_piv)
        if t_d_new == t_d and t_u_new == t_u:
            break
        t_d, t_u = t_d_new, t_u_new
    out["mAdd"] = 2 * RHO_SS * A * out["tss"] + out["mUH"] if k else 0.0
    return out


# ---------------- accionamiento (modelo verificado en tests/indep_accionamiento.py) ----------------
R_, Np, r_p, n = P["R_pin"], int(P["N_pin"]), P["d_pin"] / 2, P["n_cyl"]
ph = math.pi / Np
x_g, eta, mu_g, mu_s = P["x_g"], P["eta_c"], P["mu_g"], P["mu_s"]
front, rear = P["l_p"] + 20 + P["f_ext"], 1.25 * P["d_pp"]
L_s = front + rear; Lg = 2 / 3 * L_s
y_r = (front - rear) / 2 - Lg / 2
y_c = P["l_p"] - r_p
A_b = math.pi / 4 * P["D_bore"] ** 2; A_ann = A_b - math.pi / 4 * P["d_rod"] ** 2
F_st = A_b * P["p_relief"] / 10                                  # N


def Fh_unit(P):
    """F_cil [N] por 1 N·mm de par por cilindro (máx. en la carrera; lineal en T)."""
    def est(th, sg=None):
        a_, yp = R_ * math.cos(th), R_ * math.sin(th)
        if sg is None:
            sg = 1 if yp > r_p else -1
        hh = sg * mu_s
        F = 1.0 / (a_ - hh * (yp - r_p)); H = hh * F
        Rf = (F * (x_g - a_) + H * (y_c - y_r)) / Lg; Rr = H - Rf
        return (F + mu_g * (abs(Rf) + abs(Rr))) / eta
    th0 = math.asin(r_p / R_)
    c = [est(-ph + 2 * ph * i / 4000) for i in range(4001)] + [est(th0, 1), est(th0, -1)]
    return max(c)


FU_ = Fh_unit(P)                                                   # N/(N·mm)
Ro, Ri, Ac, Ix, ru = geom(P)


def par(P, N_kN, mu, r):
    """T [N·mm] = μ·N·r + μ_buje·H_exc·D_piv/2; H_exc = μ·N·e·(4/3)(Ro³−Ri³)/(Ro⁴−Ri⁴)"""
    Nn = N_kN * 1e3
    H = mu * Nn * P["e"] * 4 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4)
    return mu * Nn * r + P["mu_bush"] * H * P["D_piv"] / 2


def mus(P, k):
    if k == 0:
        return dict(nom=P["mu_nom"], dis=P["mu_d"], borde=P["mu_d"], cont=P["mu_cont"], seco=P["mu_dry"])
    s = "muA_" if k == 1 else "muB_"
    return dict(nom=P[s + "nom"], dis=P[s + "d"], borde=P[s + "d"], cont=P[s + "cont"], seco=P[s + "dry"])


def casos(P, k, N_kN):
    m = mus(P, k)
    rr = dict(nom=ru, dis=P["r_ef"], borde=Ro, cont=P["r_ef"], seco=ru)
    out = {}
    for c in m:
        T = par(P, N_kN, m[c], rr[c])
        F = FU_ * T / n / 1e3                                        # kN
        out[c] = dict(mu=m[c], r=rr[c], T=T / 1e6, F=F, p=F * 1e3 / A_b * 10, FS=F_st / 1e3 / F)
    return out


Tmax = F_st * n / FU_ / 1e6                                         # kN·m: par que vencen los cilindros al alivio (F_cil = F_calado)
IF = [iface(P, k) for k in (0, 1, 2)]
ifc_core = D0["escenarios"]["ifaces"]

print("# Revisión independiente de la interfaz de giro TT300-C: opciones 0 / A / B")
dif = sorted(k for k in set(P) | set(Pg) if P.get(k) != Pg.get(k))
print(f"Parámetros exportados = golden: {'sí' if not dif else 'NO, difieren ' + str(dif)}")
print(f"R_o = {s3(Ro)}, R_i = {s3(Ri)}, A = {s3(Ac)} mm², r_u = {s3(ru)} mm, a = ss_void/2 = {s3(P['ss_void']/2)} mm, "
      f"σ_adm,inox = 0,6·Fy_ss = {s3(0.6*P['Fy_ss'])} MPa, F_calado = {s3(F_st/1e3)} kN, T_max (alivio) = {s3(Tmax)} kN·m")

# ======================================================================================
# 1. Espesores, q_máx, masa agregada: interfazChecks y escenarios.ifaces
# ======================================================================================
tCyc = n * (A_b + A_ann) * P["stroke"] * 1e-6 / P["Q_pump"]          # min por pasada (V_ext + V_ret)/Q
v_edge = Ro / 1000 * (2 * math.pi / P["N_pin"]) / (tCyc * 60)         # m/s


def expected_rows(P, k):
    """Valores propios de cada fila de interfazChecks (nombre-clave → (dem, cap, fu))."""
    r = IF[k]; q = r["q"]; a = P["ss_void"] / 2
    teff = r["tss"] - P["ss_allow"]; sad = 0.6 * P["Fy_ss"]
    sig = 3 * q * a ** 2 / (4 * teff ** 2)
    rows = {
        "flexión sobre un vacío local (placa": (sig, sad, sig / sad),
        "Disco inoxidable: espesor adoptado": (r["tssReq"], r["tss"], r["tssReq"] / r["tss"]),
        "espesor mínimo por flexión": (r["tflex"], None, None),
        "espesor requerido / comercial adoptado (cada": (r["tssReq"], r["tss"], None),
        "Retención de los discos": (Tmax, P["mu_back"] * r["N"] * ru / 1e3, Tmax / (P["mu_back"] * r["N"] * ru / 1e3)),
        "tensión si el disco quedara restringido": (E_SS * (AL_SS - AL_S) * P["dT"], sad, E_SS * (AL_SS - AL_S) * P["dT"] / sad),
        "Dilatación diferencial radial": ((AL_SS - AL_S) * P["dT"] * Ro, None, None),
        "Altura que agrega": (r["delta"], None, None),
        "Masa agregada": (r["mAdd"], None, None),
    }
    if k == 2:
        s = (AL_UH - AL_S) * P["dT"] * 2 * Ro * math.sin(math.pi / P["n_seg"])
        sl = P["life"] * P["turns_yr"] * 2 * math.pi * P["r_ef"] / 1000
        h = P["k_wear"] * 1e-7 * q * sl
        rows.update({
            "presión de contacto máxima frente a la admisible": (q, P["p_uhmw"], q / P["p_uhmw"]),
            "Lámina UHMW: espesor adoptado": (r["tuhReq"], r["tuh"], r["tuhReq"] / r["tuh"]),
            "espesor por conformidad": (r["tconf"], r["tuh"], None),
            "valor PV": (q * v_edge, P["PV_uh"], q * v_edge / P["PV_uh"]),
            "desgaste en la vida": (h, 0.2 * r["tuh"], h / (0.2 * r["tuh"])),
            "junta de dilatación": (s, None, None),
        })
    return rows


tabla1 = []
for k, DD, lab in ((1, DA, "A"), (2, DB, "B")):
    exp = expected_rows(P, k)
    for row in DD["interfazChecks"]["A" if k == 1 else "B"]:
        key = next((kk for kk in exp if kk in row["nombre"]), None)
        if key is None:
            tabla1.append([lab, row["nombre"][:58], "—", "—", "—", "sin fórmula propia"]); continue
        dem, cap, fu = exp[key]
        worst = 0.0; bad = False
        for nm, mine, core in (("dem", dem, row["dem"]), ("cap", cap, row.get("cap")), ("FU", fu, row.get("fu"))):
            if core is None and mine is None:
                continue
            comp("1" + lab, f"{lab} · {row['nombre'][:60]} [{nm}]", mine, core)
            if core is None or mine is None:
                bad = True
            elif core:
                dd = abs((mine - core) / core)
                worst = max(worst, dd * 100); bad = bad or dd > TOL
            elif abs(mine) > 1e-12:
                bad = True
        tabla1.append([lab, row["nombre"][:58], f"{s3(dem)} / {s3(cap)} / {s3(fu)}",
                       f"{s3(row['dem'])} / {s3(row.get('cap'))} / {s3(row.get('fu'))}", f"{worst:.4f}", "DISCREPA" if bad else "coincide"])
table("1a. interfazChecks A y B: dem / cap / FU (propio frente a núcleo; Δ máx en %)", ["Op.", "Fila", "Propio dem / cap / FU", "Núcleo dem / cap / FU", "Δ %", "Veredicto"], tabla1)

tabla2 = []
for k in (0, 1, 2):
    c = ifc_core[k]; r = IF[k]
    for nm, mine, core in (("q_máx (MPa)", r["q"], c["q"]), ("t_flex (mm)", r["tflex"], c.get("tFlex")), ("t_req disco (mm)", r["tssReq"] or None, c.get("tssReq") or None),
                           ("t_disco adoptado (mm)", r["tss"] or None, c["tss"] or None), ("t_conf UHMW (mm)", r["tconf"], c.get("tuhConf")),
                           ("t_UHMW adoptado (mm)", r["tuh"] or None, c["tuh"] or None), ("Δ altura (mm)", r["delta"] or None, c["delta"] or None),
                           ("masa agregada (kg)", r["mAdd"] or None, c["mAdd"] or None)):
        if mine is None and core is None:
            continue
        comp("1i", f"op. {k} · {nm}", mine, core)
        d = (mine - core) / core * 100 if (mine is not None and core) else float("nan")
        tabla2.append([k, nm, s3(mine), s3(core), f"{d:+.4f}", "coincide" if abs(d) <= TOL * 100 else "DISCREPA"])
table("1b. escenarios.ifaces (espesores, q_máx, masa agregada)", ["Op.", "Magnitud", "Propio", "Núcleo", "Δ %", "Veredicto"], tabla2)

# ---------------- barridos ----------------
SW = [("ss_void", [60, 80, 100, 120, 140, 160, 180, 200], "mm"), ("Fy_ss", [170, 185, 205, 225, 250], "MPa"),
      ("E_uhmw", [200, 250, 300, 400, 500], "MPa"), ("d_flat", [0.05, 0.1, 0.15, 0.2, 0.3], "mm"), ("W_tf", [200, 240, 280, 300, 320, 360], "tf")]
sw_bad = 0; sw_n = 0


def cmp_sweep(over):
    """compara propio y núcleo para P+over; devuelve (fila, ok)"""
    global sw_n, sw_bad
    DD = export(over)
    PP = dict(P); PP.update(over)
    ra, rb = iface(PP, 1), iface(PP, 2)
    if DD is None:
        return None, ra, rb, False, []
    ca, cb = DD["escenarios"]["ifaces"][1], DD["escenarios"]["ifaces"][2]
    bad = []
    for lab, r, c, keys in (("A", ra, ca, (("q", "q"), ("tFlex", "tflex"), ("tssReq", "tssReq"), ("tss", "tss"), ("mAdd", "mAdd"), ("delta", "delta"))),
                            ("B", rb, cb, (("q", "q"), ("tuhConf", "tconf"), ("tuhReq", "tuhReq"), ("tuh", "tuh"), ("mAdd", "mAdd"), ("delta", "delta")))):
        for kc, km in keys:
            sw_n += 1
            cv, mv = c.get(kc), r[km]
            if cv is None and (mv is None or not math.isfinite(mv)):
                continue
            if cv is None or mv is None or (not math.isfinite(mv)) or (abs(mv - cv) > TOL * abs(cv) if cv else abs(mv) > 1e-9):
                bad.append(f"{lab}.{kc}")
    # F y FS de diseño de B y A
    for lab, r, c, N_ in (("A", ra, ca, ra["N"]), ("B", rb, cb, rb["N"])):
        PPP = PP
        cs = casos(PPP, 1 if lab == "A" else 2, N_)["dis"]
        for kc, mv in (("F", cs["F"]), ("FS", cs["FS"])):
            sw_n += 1
            if abs(mv - c[kc]) > TOL * abs(c[kc]):
                bad.append(f"{lab}.{kc}")
    sw_bad += len(bad)
    return DD, ra, rb, not bad, bad


for key, vals, u in SW:
    rows = []
    for v in vals:
        res = cmp_sweep({key: v})
        if res[0] is None:
            rows.append([s3(v), "rechazado por el núcleo", "", "", "", "", "", "", ""]); continue
        DD, ra, rb, ok, bad = res
        ca, cb = DD["escenarios"]["ifaces"][1], DD["escenarios"]["ifaces"][2]
        rows.append([s3(v), s3(ra["q"]), f"{s3(ra['tflex'])} / {s3(ca['tFlex'])}", f"{s3(ra['tss'])} / {s3(ca['tss'])}",
                     f"{s3(rb['tconf'])} / {s3(cb['tuhConf'])}", f"{s3(rb['tuh'])} / {s3(cb['tuh'])}", f"{s3(rb['mAdd'])} / {s3(cb['mAdd'])}",
                     f"{s3(casos(dict(P, **{key: v}), 2, rb['N'])['dis']['FS'])} / {s3(cb['FS'])}", "coincide" if ok else "DISCREPA " + ",".join(bad)])
    table(f"1c. Barrido de {key} ({u}); cada celda «propio / núcleo»", [key, "q_máx", "t_flex", "t_disco", "t_conf", "t_UHMW", "mAdd B kg", "FS dis. B", "Veredicto"], rows)
print(f"\nBarridos: {sw_n} comparaciones, {sw_bad} discrepancias (tolerancia 0,1 %)")

# ---------------- umbrales de espesor comercial ----------------


def thick_pair(PP):
    return (iface(PP, 1)["tss"], iface(PP, 2)["tuh"])


def umbrales(key, lo, hi, npts=600):
    xs = [lo + (hi - lo) * i / npts for i in range(npts + 1)]
    out = []
    prev = thick_pair(dict(P, **{key: xs[0]}))
    for i in range(1, len(xs)):
        cur = thick_pair(dict(P, **{key: xs[i]}))
        if cur != prev:
            a_, b_ = xs[i - 1], xs[i]
            for _ in range(60):
                mid = (a_ + b_) / 2
                if thick_pair(dict(P, **{key: mid})) == prev:
                    a_ = mid
                else:
                    b_ = mid
            out.append((b_, prev, cur))
            prev = cur
    return out


rows = []
for key, lo, hi in (("ss_void", 60, 200), ("Fy_ss", 170, 250), ("E_uhmw", 200, 500), ("d_flat", 0.05, 0.3), ("W_tf", 200, 360)):
    for v, p0, p1 in umbrales(key, lo, hi):
        res = []
        for fac in (1 - 2e-4, 1 + 2e-4):
            DD = export({key: v * fac})
            res.append(None if DD is None else (DD["escenarios"]["ifaces"][1]["tss"], DD["escenarios"]["ifaces"][2]["tuh"]))
        ok = res[0] == p0 and res[1] == p1
        comp("1u", f"umbral {key} = {s3(v)}", 1.0 if ok else 0.0, 1.0)
        rows.append([key, s3(v), f"{s3(p0[0])} / {s3(p0[1])}", f"{s3(p1[0])} / {s3(p1[1])}",
                     f"{res[0] and s3(res[0][0])} / {res[0] and s3(res[0][1])}", f"{res[1] and s3(res[1][0])} / {res[1] and s3(res[1][1])}", "coincide" if ok else "DISCREPA"])
DD = export({"p_uhmw": 1.5}); PPd = dict(P, p_uhmw=1.5); rb_ = iface(PPd, 2)
cb_ = DD["escenarios"]["ifaces"][2] if DD else {}
ok_deg = DD is not None and cb_.get("tuh") is None and not math.isfinite(rb_["tuh"]) and cb_.get("tuhConf") is None
comp("1u", "p_uhmw = 1,5 MPa ≤ q_máx: B inviable (sin espesor)", 1.0 if ok_deg else 0.0, 1.0)
rows.append(["p_uhmw", "1.50 (≤ q_máx)", "—", "B inviable", "t_UHMW = " + str(cb_.get("tuh")), "FS = " + str(cb_.get("FS")), "coincide" if ok_deg else "DISCREPA"])
table("1d. Umbrales donde cambian los espesores comerciales (t_disco / t_UHMW en mm): propio y verificación en el núcleo a ±0,02 %",
      ["Parámetro", "Valor umbral", "Debajo (propio)", "Encima (propio)", "Núcleo debajo", "Núcleo encima", "Veredicto"], rows)

# ======================================================================================
# 2. F por cilindro, p y FS de las tres opciones
# ======================================================================================
rows = []
for k, DD, lab in ((0, D0, "0"), (1, DA, "A"), (2, DB, "B")):
    cs = casos(P, k, IF[k]["N"])
    cc = {c["id"]: c for c in DD["derivados"]["casos"]}
    for cid, c in cs.items():
        core = cc[cid]
        comp("2", f"op. {lab} · caso {cid}: F (kN)", c["F"], core["F"]); comp("2", f"op. {lab} · caso {cid}: p (bar)", c["p"], core["p"])
        comp("2", f"op. {lab} · caso {cid}: FS", c["FS"], core["FS"]); comp("2", f"op. {lab} · caso {cid}: T (kN·m)", c["T"], core["T"])
        d = (c["F"] - core["F"]) / core["F"] * 100
        rows.append([lab, cid, s3(c["mu"]), s3(c["r"]), s3(c["T"]), s3(c["F"]), s3(core["F"]), s3(c["p"]), s3(core["p"]), s3(c["FS"]), s3(core["FS"]),
                     f"{d:+.4f}", "gira" if c["F"] <= F_st / 1e3 else "NO gira", "coincide" if abs(d) <= TOL * 100 else "DISCREPA"])
    ci = ifc_core[k]
    comp("2", f"op. {lab} · ifaces F de diseño", cs["dis"]["F"], ci["F"]); comp("2", f"op. {lab} · ifaces p de diseño", cs["dis"]["p"], ci["p"])
    comp("2", f"op. {lab} · ifaces FS de diseño", cs["dis"]["FS"], ci["FS"])
    Tu = par(P, IF[k]["N"], 1.0, P["r_ef"]) / n
    mumax = F_st / (FU_ * Tu)
    comp("2", f"op. {lab} · μ máx que gira (r_ef)", mumax, ci["muMax"])
table("2. Casos de giro por opción (F por cilindro en kN, p en bar; T en kN·m)", ["Op.", "Caso", "μ", "r mm", "T", "F propio", "F núcleo", "p propio", "p núcleo", "FS propio", "FS núcleo", "Δ F %", "Gira", "Veredicto"], rows)
Tmax_core = D0["apoyo"]["Tmax"]
comp("2", "T_max al alivio (kN·m)", Tmax, Tmax_core)

# --- altura nueva del eje: efectos fuera del plano (retención T, ménsulas, soldadura de mejillas)
hd2 = P["h_disc"] / 2
z_t = P["t_base"] + P["t_bed"] - P["h_slot"] / 2
Fpc = eta * F_st


def guia_cal(th):
    a_, yp = R_ * math.cos(th), R_ * math.sin(th)
    Hh = (1 if yp > r_p else -1) * mu_s * Fpc
    Rf = (Fpc * (x_g - a_) + Hh * (y_c - y_r)) / Lg
    return Hh, Rf, Hh - Rf


GC = [guia_cal(-ph + 2 * ph * i / 4000) for i in range(4001)]
SRcal = max(abs(x[1]) + abs(x[2]) for x in GC); Hcal = mu_s * Fpc
ala = (P["w_tee"] - P["w_slot"]) / 2


def retencionT(Delta):
    dz = P["t_base"] + hd2 + Delta - z_t
    V = Hcal * dz / ((P["w_bed"] + P["w_tee"]) / 2) + mu_g * SRcal * dz / L_s
    return V / (ala * L_s)


def soldadura_mejilla(Delta):
    aw = 0.707 * P["w_br"]; hax = hd2 + Delta
    return math.hypot(F_st / (4 * aw * P["L_ch"]), F_st * hax / (4 * aw * P["L_ch"] ** 2 / 6))


def vv(DD, sub):
    return next(v for v in DD["verificaciones"] if sub in v["nombre"])


rows = []
for lab, DD, k in (("0", D0, 0), ("A", DA, 1), ("B", DB, 2)):
    Dl = IF[k]["delta"]
    for nm, sub, mine in (("Retención T: aplastamiento del ala", "aplastamiento en la cabeza T", retencionT(Dl)),
                          ("Soldadura mejillas–base", "Soldadura mejillas–base (4", soldadura_mejilla(Dl)),
                          ("Mejilla: flexión en la base (∝ h_eje)", "Mejilla de la ménsula", vv(D0, "Mejilla de la ménsula")["dem"] * (hd2 + Dl) / hd2)):
        core = vv(DD, sub)
        comp("2z", f"op. {lab} · {nm}", mine, core["dem"])
        d = (mine - core["dem"]) / core["dem"] * 100
        rows.append([lab, f"h_eje = {s3(hd2 + Dl)}", nm, s3(mine), s3(core["dem"]), s3(core["fu"]), f"{d:+.4f}", "coincide" if abs(d) <= TOL * 100 else "DISCREPA"])
table("2z. Altura nueva del eje de los cilindros h_eje = h_disc/2 + Δ: efectos fuera del plano", ["Op.", "h_eje", "Chequeo", "Propio MPa", "Núcleo MPa", "FU núcleo", "Δ %", "Veredicto"], rows)

# ======================================================================================
# 3. HIPÓTESIS FÍSICAS
# ======================================================================================
q = IF[1]["q"]; a = P["ss_void"] / 2; sad = 0.6 * P["Fy_ss"]; nu = 0.3
teff = IF[1]["tss"] - P["ss_allow"]
# ---- (a) placa sobre un vacío local
sig_cl = 3 * q * a ** 2 / (4 * teff ** 2)
sig_ss = 3 * (3 + nu) / 8 * q * a ** 2 / teff ** 2
tfl_cl = a * math.sqrt(0.75 * q / sad); tfl_ss = a * math.sqrt(3 * (3 + nu) / 8 * q / sad)
D_pl = E_SS * teff ** 3 / (12 * (1 - nu ** 2))
wc_cl = q * a ** 4 / (64 * D_pl)
sig_fd = None; wc_fd = None
if np is not None:
    def plate(a, t, q, dv=None, E=E_SS, nu=0.3, h=0.5):
        """Placa axisimétrica de Kirchhoff, empotrada lejos, sobre fundación rígida unilateral con un vacío r<a (profundidad dv o pasante)."""
        Dp = E * t ** 3 / (12 * (1 - nu ** 2)); Lout = a + 12 * t + 100
        N_ = int(round(Lout / h)); r = np.arange(N_ + 1) * h
        L = np.zeros((N_ + 1, N_ + 1)); L[0, 0] = -4 / h ** 2; L[0, 1] = 4 / h ** 2
        for i in range(1, N_):
            L[i, i - 1] = 1 / h ** 2 - 1 / (2 * h * r[i]); L[i, i] = -2 / h ** 2; L[i, i + 1] = 1 / h ** 2 + 1 / (2 * h * r[i])
        L[N_, N_ - 1] = 2 / h ** 2; L[N_, N_] = -2 / h ** 2
        LL = L[:N_, :] @ L[:, :N_]
        kp = 1e1 * Dp / h ** 4
        w = np.zeros(N_); inside = r[:N_] < a
        floor = np.zeros(N_) if dv is None else np.where(inside, dv, 0.0)
        for _ in range(300):
            act = ((~inside) & (w > 0)) if dv is None else (w > floor)
            wn = np.linalg.solve(Dp * LL + np.diag(np.where(act, kp, 0.0)), q * np.ones(N_) + np.where(act, kp * floor, 0.0))
            if np.max(np.abs(wn - w)) < 1e-10:
                w = wn; break
            w = wn
        wf = np.append(w, 0.0); wp = np.gradient(wf, h); wpp = np.zeros_like(wf)
        wpp[1:-1] = (wf[2:] - 2 * wf[1:-1] + wf[:-2]) / h ** 2; wpp[0] = 2 * (wf[1] - wf[0]) / h ** 2; wpp[-1] = 2 * (wf[-2] - wf[-1]) / h ** 2
        rr = np.maximum(r, 1e-9); fr = np.where(r > 0, wp / rr, wpp)
        Mr = -Dp * (wpp + nu * fr); Mt = -Dp * (fr + nu * wpp)
        return r, wf, 6 * np.maximum(np.abs(Mr), np.abs(Mt)) / t ** 2
    r_, w_, s_ = plate(a, teff, q)
    sig_fd, wc_fd = float(s_.max()), float(w_[0])
    # validación del operador contra la solución cerrada (placa empotrada en r = a)
rows = [["Empotrada (modelo del núcleo)", s3(sig_cl), s3(sig_cl / sad), s3(tfl_cl + P["ss_allow"]), s3(com(tfl_cl + P["ss_allow"], COM_SS))],
        ["Simplemente apoyada, ν = 0,3 (3(3+ν)/8·q a²/t² = 1,24·q a²/t²)", s3(sig_ss), s3(sig_ss / sad), s3(tfl_ss + P["ss_allow"]), s3(com(tfl_ss + P["ss_allow"], COM_SS))]]
if sig_fd is not None:
    tfd = tfl_cl * math.sqrt(sig_fd / sig_cl) + P["ss_allow"]
    rows.append(["Disco continuo sobre fundación unilateral con vacío pasante (diferencias finitas)", s3(sig_fd), s3(sig_fd / sad), s3(tfd), s3(com(tfd, COM_SS))])
table(f"3a. Placa circular de radio a = {s3(a)} mm, t_ef = {s3(teff)} mm, q = {s3(q)} MPa, σ_adm = {s3(sad)} MPa", ["Modelo de borde", "σ máx MPa", "FU", "t_req mm", "comercial mm"], rows)
if sig_fd is not None:
    print(f"Razón σ_unilateral/σ_empotrada = {sig_fd/sig_cl:.3f}; razón σ_apoyada/σ_empotrada = {sig_ss/sig_cl:.3f}")
    # profundidad crítica del vacío
    rows = []
    for dv in (0.01, 0.03, 0.05, 0.075, 0.10, 0.30):
        _, _, sd = plate(a, teff, q, dv=dv)
        sdelta = 4 * E_SS * teff * dv / ((1 - nu ** 2) * a ** 2)
        rows.append([s3(dv), s3(float(sd.max())), s3(min(sdelta, sig_cl)), s3(sig_fd), "gobierna el contacto de fondo" if float(sd.max()) < 0.995 * sig_fd else "gobierna la carga uniforme"])
    table("3a'. Vacío de profundidad δ_v: tensión del disco (MPa); cerrada σ_δ = 4·E·t·δ_v/((1−ν²)a²) acotada por la empotrada",
          ["δ_v mm", "σ diferencias finitas", "σ_δ cerrada (acotada)", "σ uniforme (vacío pasante)", "Gobierna"], rows)
    print(f"δ_crit (el disco deja de tocar el fondo): empotrada {s3(wc_cl)} mm = q a⁴/(64 D); modelo unilateral {s3(wc_fd)} mm")
c_ov = teff * math.sqrt(sad / (3 * q))
print(f"Voladizo en el borde del disco (sin respaldo en una franja c): σ = 3 q c²/t² → c_máx = {s3(c_ov)} mm con t_ef = {s3(teff)} mm")

# ---- (b) conformidad de la lámina UHMW
nu_uh = 0.45


def Mcon(E, nu_u=nu_uh):
    return E * (1 - nu_u) / ((1 + nu_u) * (1 - 2 * nu_u))


def Ec(t, Dc, E, mode="inc", nu_u=nu_uh):
    """módulo efectivo de la lámina; S = D_carga/(4t).
    'inc': E + 1/[1/(2S²E) + 1/(M−E)]  → E (S→0), M deformación plana (S→∞), E(1+2S²) si M ≫ E.
    'gent': 1/E_c = 1/[E(1+2S²)] + 1/K  (Gent 1994, compresibilidad por el módulo volumétrico K = E/(3(1−2ν)))."""
    S = Dc / (4 * t)
    if mode == "gent":
        K = E / (3 * (1 - 2 * nu_u)); return 1 / (1 / (E * (1 + 2 * S * S)) + 1 / K), S
    M = Mcon(E, nu_u)
    return E + 1 / (1 / (2 * S * S * E) + 1 / (M - E)), S


def t_conf_S(q, Dc, E, d, p=None, mode="inc", nu_u=nu_uh):
    p = P["p_uhmw"] if p is None else p
    if p <= q:
        return math.inf
    t = 10.0
    for _ in range(400):
        Ee, _ = Ec(t, Dc, E, mode, nu_u); tn = Ee * d / (p - q)
        if abs(tn - t) < 1e-9:
            break
        t = 0.5 * (t + tn)
    return t


qB = IF[2]["q"]; tconf0 = IF[2]["tconf"]; tuh0 = IF[2]["tuh"]
M_c = Mcon(P["E_uhmw"])
rows = []
for Dc in (25, 50, 100, 200):
    for E in (P["E_uhmw"], 700.0):
        tc = t_conf_S(qB, Dc, E, P["d_flat"]); Ee, S = Ec(tc, Dc, E)
        tg = t_conf_S(qB, Dc, E, P["d_flat"], mode="gent")
        rows.append([s3(Dc), s3(E), s3(S), s3(Ee), s3(Ee / E), s3(tc), s3(com(max(tc, P["uh_tmin"]), COM_UH)), s3(tg), f"{(tc/tconf0-1)*100:+.0f}"])
table(f"3b. Módulo confinado de la lámina (S = D_carga/(4t); ν_UHMW = {nu_uh}; d_flat = {P['d_flat']} mm); núcleo: t_conf = {s3(tconf0)} mm → {s3(tuh0)} mm con E uniaxial",
      ["D_carga mm", "E MPa", "S", "E_c MPa", "E_c/E", "t_conf mm", "comercial mm", "t_conf Gent mm", "Δ vs núcleo %"], rows)
print(f"Módulo de deformación plana unidimensional (λ ≫ t, sin rozamiento): M = E(1−ν)/((1+ν)(1−2ν)) = {s3(M_c)} MPa ({s3(M_c/P['E_uhmw'])}×E)")
tc_main = t_conf_S(qB, P["ss_void"], P["E_uhmw"], P["d_flat"]); tc_main_c = com(max(tc_main, P["uh_tmin"]), COM_UH)
# efecto en cascada de un t_UHMW mayor: soldadura de mejillas
DC = export({"opt_uhmw": 1, "t_uhmw": tc_main_c}) if math.isfinite(tc_main_c) else None
if DC is not None:
    w_c = vv(DC, "Soldadura mejillas–base (4"); dl_c = [i for i in DC["escenarios"]["ifaces"] if i["k"] == 2][0]["delta"]
    comp("3b", "Soldadura de mejillas con t_UHMW = %s (Δ = %s): propio" % (s3(tc_main_c), s3(dl_c)), soldadura_mejilla(dl_c), w_c["dem"])
    print(f"Con t_UHMW = {s3(tc_main_c)} mm (Δ = {s3(dl_c)} mm) el núcleo da soldadura de mejillas FU = {s3(w_c['fu'])} (propio {s3(soldadura_mejilla(dl_c)/ (0.6*P['FEXX']/(1.2*P['Nd'])))})")
    fu_weld_conf = w_c["fu"]
else:
    fu_weld_conf = None
# Δ máximo admisible por la soldadura de mejillas
cap_w = 0.6 * P["FEXX"] / (1.2 * P["Nd"])
lo_, hi_ = 0.0, 200.0
for _ in range(60):
    mid = (lo_ + hi_) / 2
    lo_, hi_ = (mid, hi_) if soldadura_mejilla(mid) <= cap_w else (lo_, mid)
Dmax_w = lo_
print(f"Δ máximo que admite la soldadura de mejillas (FU = 1): {s3(Dmax_w)} mm (B adoptada: Δ = {s3(IF[2]['delta'])} mm)")

# ---- (c) valores de partida y fluencia
v_ext = Ro / 1000 * (2 * math.pi / P["N_pin"]) / (n * A_b * P["stroke"] * 1e-6 / P["Q_pump"] * 60)
sl = P["life"] * P["turns_yr"] * 2 * math.pi * P["r_ef"] / 1000
h_w = P["k_wear"] * 1e-7 * qB * sl
rows = [["p_uhmw (sostenida)", s3(P["p_uhmw"]) + " MPa", "5–7 MPa (cargas estáticas continuas; fluencia limita antes que fluencia plástica ~20 MPa)", f"q_máx/p = {s3(qB/P['p_uhmw'])}", "razonable; es un límite de deformación, no de resistencia"],
        ["E_uhmw", s3(P["E_uhmw"]) + " MPa", "600–800 MPa corto plazo; 100–200 MPa tras 1 año bajo carga", "300 es intermedio", "un defecto que se desplaza (disco rotatorio) ve el módulo de corto plazo (≈ 60–100 s por pasada)"],
        ["k_wear", s3(P["k_wear"]) + "e-7 mm³/N·m", "1e-7–1e-6 (limpio); 1e-5 con arena incrustada", f"h = {s3(h_w)} mm en {s3(P['life'])} años", f"con k×100 → h = {s3(h_w*100)} mm ≪ 0,2 t = {s3(0.2*tuh0)} mm"],
        ["PV_uh", s3(P["PV_uh"]) + " MPa·m/s", "0,05–0,10 (seco, UHMW-PE)", f"PV = {s3(qB*v_edge)} (núcleo, v = {s3(v_edge*1e3)} mm/s); con v solo en carrera = {s3(qB*v_ext)}", "no gobierna (v ≈ 1–2 mm/s: el criterio relevante es la presión estática)"],
        ["μ B (nom / dis / cont / seco)", f"{P['muB_nom']} / {P['muB_d']} / {P['muB_cont']} / {P['muB_dry']}", "UHMW sobre inox: 0,05–0,10 con grasa; 0,10–0,22 seco; estático hasta 0,25", "dis < seco; cont = seco", "inconsistente: ver H2"],
        ["μ A (nom / dis / cont / seco)", f"{P['muA_nom']} / {P['muA_d']} / {P['muA_cont']} / {P['muA_dry']}", "inox–inox con grasa 0,10–0,20; seco 0,5–1 (gripado)", "monótono", "razonable"]]
table("3c. Valores de partida frente a la literatura de UHMW-PE (órdenes de magnitud de fichas técnicas; confirmar con el proveedor)",
      ["Parámetro", "Núcleo", "Rango de literatura", "Resultado propio", "Comentario"], rows)
# fluencia: estimación con módulo de fluencia (isócronas típicas)
rows = []
tU = tuh0
qmin = D0["apoyo"]["q_min"]
for lab, Ecr in (("1 mes", 160.0), ("1 año", 120.0), ("25 años", 80.0)):
    s_max = qB / Ecr * tU; s_min = qmin / Ecr * tU
    rows.append([lab, s3(Ecr), s3(s_max), s3(s_max - s_min), s3((s_max - s_min) / (2 * Ro) * 1e3)])
table(f"3c'. Fluencia de la lámina (uniaxial, cota superior; E_fluencia supuesto de isócronas típicas), t = {s3(tU)} mm, q_máx = {s3(qB)}, q_mín = {s3(qmin)} MPa",
      ["Tiempo", "E_fl MPa", "asentamiento en el borde mm", "diferencial q_máx−q_mín mm", "inclinación mm/m"], rows)

# ---- (d) gripado inox-inox
print(f"\n3d. Inox–inox (opción A): presión nominal {s3(q)} MPa; el núcleo no tiene verificación ni requisito de pareja de aleaciones (solo rotula μ_seco «riesgo de gripado»); "
      f"con μ_seco = {P['muA_dry']} el caso seco no gira (FS = {s3(casos(P, 1, IF[1]['N'])['seco']['FS'])})")

# ---- (e) retención de los discos por fricción
rows = []
mb_req_all = []
for k, lab in ((1, "A"), (2, "B")):
    N_ = IF[k]["N"]; cap = P["mu_back"] * N_ * ru / 1e3; cs = casos(P, k, N_)
    for cid in ("nom", "dis", "borde", "cont", "seco"):
        c = cs[cid]
        T_int = c["mu"] * N_ * c["r"] / 1e3                      # par que transmite la interfaz (sin el buje)
        T_real = min(T_int, Tmax)
        mb = T_real / (N_ * ru / 1e3)
        rows.append([lab, cid, s3(c["mu"]), s3(c["T"]), s3(T_int), s3(T_real), s3(T_real / cap), s3(mb), "sí" if c["F"] <= F_st / 1e3 else "NO gira"])
        if cid in ("cont", "seco"):
            mb_req_all.append((lab, cid, mb))
    rows.append([lab, "T_calado", "—", s3(Tmax), s3(Tmax), s3(Tmax), s3(Tmax / cap), s3(Tmax / (N_ * ru / 1e3)), "cota del núcleo"])
table(f"3e. Par que transmiten los discos [kN·m] frente a la capacidad de retención μ_resp·N·r_u (μ_resp = {P['mu_back']}); μ_resp requerido = T/(N·r_u)",
      ["Op.", "Caso", "μ interfaz", "T cilindros (con buje)", "μ·N·r (interfaz)", "T discos = mín(T_int, T_alivio)", "FU retención", "μ_resp requerido", "gira"], rows)
mb_calado = Tmax / (IF[1]["N"] * ru / 1e3)
print(f"μ_resp mínimo con T_calado: {s3(mb_calado)} (A) / {s3(Tmax/(IF[2]['N']*ru/1e3))} (B). "
      f"Con μ_resp = 0,30 (superficie limpia clase A de AISC) FU = {s3(Tmax/(0.30*IF[1]['N']*ru/1e3))}; con 0,20 (película de grasa) FU = {s3(Tmax/(0.20*IF[1]['N']*ru/1e3))}")

# ---- (b') retención de la lámina UHMW contra arrastre
mu_top_max = max(P["muB_cont"], P["muB_dry"], P["muB_d"])
Fdrag = mu_top_max * IF[2]["N"]                                  # kN, fuerza tangencial total que la cara superior transmite a la lámina
db_ = 8.0
n_bolts = Fdrag * 1e3 / (P["p_uhmw"] * db_ * IF[2]["tuh"])
print(f"\n3b'. Arrastre de la lámina UHMW por la cara superior: μ·N = {s3(mu_top_max)}·{s3(IF[2]['N'])} = {s3(Fdrag)} kN; aplastamiento admisible de un bulón M8 en la lámina "
      f"= p_uhmw·d·t = {s3(P['p_uhmw']*db_*IF[2]['tuh']/1e3)} kN → harían falta {s3(n_bolts)} bulones")

# ---- (f) otros
dRad = (AL_UH - AL_S) * P["dT"] * (Ro - Ri)
bolt = {"M6": 3.3, "M8": 4.4, "M10": 5.5}
rows = [[b_, s3(k_), s3(IF[1]["tss"] - P["ss_allow"] - k_), "ok" if IF[1]["tss"] - P["ss_allow"] - k_ >= 1.5 else "queda < 1,5 mm bajo la cabeza"] for b_, k_ in bolt.items()]
table(f"3f. Pernos avellanados (ISO 10642 / DIN 7991, altura de cabeza k) en el disco de {s3(IF[1]['tss'])} mm menos {s3(P['ss_allow'])} mm de relapeado", ["Perno", "k mm", "espesor restante bajo la cabeza mm", "veredicto"], rows)
print(f"Crecimiento radial de un sector UHMW (R_o − R_i) con ΔT = {P['dT']} K: {s3(dRad)} mm (la junta circunferencial {s3(IF[2]['delta'] and (AL_UH-AL_S)*P['dT']*2*Ro*math.sin(math.pi/P['n_seg']))} mm no lo cubre)")
mt = [D0["derivados"]["masas"]["total"], DA["derivados"]["masas"]["total"], DB["derivados"]["masas"]["total"]]
print(f"Masa total del conjunto: {s3(mt[0])} → {s3(mt[1])} (A, +{s3(mt[1]-mt[0])} kg frente a mAdd = {s3(IF[1]['mAdd'])}) → {s3(mt[2])} (B, +{s3(mt[2]-mt[0])} kg frente a mAdd = {s3(IF[2]['mAdd'])}); "
      f"el resto crece por ménsulas, patines y pivote (Δ)")

# ======================================================================================
# Hallazgos
# ======================================================================================
fs_B = {m: casos(dict(P, muB_d=m), 2, IF[2]["N"])["dis"]["FS"] for m in (0.15, 0.20, 0.25, 0.30)}
if np is not None and sig_fd is not None and sig_fd > sig_cl * 1.001:
    FIND.append(("H0", "importante", "El modelo empotrado no acota al de fundación unilateral", f"σ {s3(sig_cl)}", f"σ {s3(sig_fd)}"))
if com(max(tc_main, P["uh_tmin"]), COM_UH) > tuh0:
    FIND.append(("H1", "importante", "Conformidad de la lámina UHMW con módulo uniaxial E: una lámina delgada confinada (S = D/(4t)) es mucho más rígida; la sobrepresión E_c·δ/t sube y el espesor requerido también",
                 f"t_conf {s3(tconf0)} mm → {s3(tuh0)} mm; Δ = {s3(IF[2]['delta'])} mm; soldadura de mejillas FU {s3(vv(DB,'Soldadura mejillas–base (4')['fu'])}",
                 f"t_conf {s3(tc_main)} mm (D_carga = ss_void, ν = 0,45) → {s3(tc_main_c)} mm; Δ = {s3(2*IF[2]['tss']+tc_main_c)} mm; soldadura de mejillas FU {s3(fu_weld_conf)}. Usar E_c(S) iterado (con Gent: {s3(t_conf_S(qB, P['ss_void'], P['E_uhmw'], P['d_flat'], mode='gent'))} mm), o garantizar d_flat ≤ 0,05 mm en 100 mm; revisar la soldadura de mejillas con el Δ nuevo (Δ_máx = {s3(Dmax_w)} mm)"))
if P["muB_d"] < P["muB_dry"] or P["muB_cont"] <= P["muB_dry"]:
    FIND.append(("H2", "importante", "μ de la opción B: el μ de diseño (arranque tras reposo) es menor que el seco, y el contaminado coincide con el seco; la lámina trabaja sin lubricación efectiva a largo plazo (la grasa puede expulsarse bajo 1,7 MPa tras meses de reposo)",
                 f"μ_d {P['muB_d']}: FS {s3(fs_B[0.15])}; ventaja frente a la base {s3((1-ifc_core[2]['F']/ifc_core[0]['F'])*100)} % en F",
                 f"μ_d = 0,20 (seco estático): FS {s3(fs_B[0.20])} (= base); 0,25: FS {s3(fs_B[0.25])} < 1,25; 0,30: FS {s3(fs_B[0.30])} (no gira). Fijar μ_d ≥ 0,20 y μ_cont ≥ 0,25–0,30"))
mb_rq = Tmax / (IF[1]["N"] * ru / 1e3)
Tcont_A = P["muA_cont"] * IF[1]["N"] * P["r_ef"] / 1e3
Tcont_B = P["muB_cont"] * IF[2]["N"] * P["r_ef"] / 1e3
if mb_rq > 0.30:
    FIND.append(("H3", "importante", "Retención de los discos solo por fricción con μ_resp = 0,40 sin respaldo normativo: el valor requerido para T_calado supera 0,30 (superficie limpia clase A de AISC) y no hay redundancia mecánica; el respaldo está junto a la grasa (A) y a la pintura. T_calado es una cota válida, pero conservadora: el par que realmente transmite la interfaz es menor (conclusión: criterio suficiente en demanda, frágil en capacidad)",
                 f"T_calado {s3(Tmax)} kN·m; μ_resp = {P['mu_back']}: FU {s3(Tmax/(P['mu_back']*IF[1]['N']*ru/1e3))}",
                 f"par resistente (contaminado) A {s3(Tcont_A)} / B {s3(Tcont_B)} kN·m → μ_resp requerido {s3(Tcont_A/(IF[1]['N']*ru/1e3))} / {s3(Tcont_B/(IF[2]['N']*ru/1e3))}; con T_calado {s3(mb_rq)}. Con μ_resp = 0,30: FU {s3(Tmax/(0.30*IF[1]['N']*ru/1e3))} (T_calado) / {s3(Tcont_A/(0.30*IF[1]['N']*ru/1e3))} (contaminado A). Prever pasadores radiales o chavetas periféricas (el propio núcleo lo sugiere) o respaldo granallado sin pintura"))
FIND.append(("H4", "importante", "Opción A: inox–inox sin requisito de pareja de aleaciones ni advertencia de gripado en las verificaciones (solo la etiqueta de μ_seco)",
             f"presión {s3(q)} MPa; caso seco sin giro (FS {s3(casos(P,1,IF[1]['N'])['seco']['FS'])})",
             "exigir aleaciones o durezas distintas (diferencia ≥ 50 HB; p. ej. 304 contra 17-4PH o dúplex) o recubrimiento; la presión nominal es ≈ 1/8 de los umbrales de gripado publicados para 304/304 (ASTM G98, del orden de 10–15 MPa; confirmar con el proveedor), pero la grasa puede expulsarse tras reposo largo y el arranque es de baja velocidad con microdeslizamiento"))
FIND.append(("H5", "importante", "Opción B: la retención de la lámina UHMW contra el arrastre de la cara superior no se verifica; la misma pareja UHMW/inox está en ambas caras de la lámina y los bulones avellanados no pueden resistir el arrastre por aplastamiento del UHMW",
             "sin verificación",
             f"fuerza tangencial {s3(Fdrag)} kN frente a {s3(P['p_uhmw']*db_*IF[2]['tuh']/1e3)} kN por bulón M8 ({s3(n_bolts)} bulones); prever alojamiento (rebaje perimetral/cola de milano) o pegado, y verificar el aplastamiento del borde del rebaje con p_uhmw"))
FIND.append(("H6", "menor", "Modelo de la placa: empotrada es adecuada y conservadora (≈ 11 %) para un vacío interior con q > 0 alrededor; la apoyada daría t = 8 mm; no cubre un vacío contiguo al borde del disco",
             f"σ empotrada {s3(sig_cl)} MPa", f"unilateral {s3(sig_fd) if sig_fd else '—'} MPa (−11 %); apoyada {s3(sig_ss)} MPa (t_req {s3(tfl_ss + P['ss_allow'])} → {s3(com(tfl_ss + P['ss_allow'], COM_SS))} mm); la carga uniforme gobierna para δ_v ≥ {s3(wc_fd if wc_fd else wc_cl)} mm (empotrada {s3(wc_cl)}); voladizo máx. c = {s3(c_ov)} mm (cantear el respaldo ≤ 3 mm). σ_δ cerrada subestima ≈ 2× a δ_v = 0,01 mm y 8 % a 0,03 mm: no usarla para reducir t"))
FIND.append(("H7", "menor", "PV con la velocidad media del ciclo completo (carrera + retorno); la mesa solo se mueve en la carrera",
             f"v = {s3(v_edge*1e3)} mm/s, PV = {s3(qB*v_edge)}", f"v = {s3(v_ext*1e3)} mm/s, PV = {s3(qB*v_ext)}; no gobierna (FU {s3(qB*v_ext/P['PV_uh'])})"))
FIND.append(("H8", "menor", "Fluencia de la lámina: asentamiento y diferencia de borde pequeños; sin efecto sobre la verticalidad, pero relaja bulones y desplaza material a las juntas",
             "no evaluada", "≈ 0,1–0,2 mm de asentamiento y ≈ 0,1 mm de diferencia a 1–25 años (≈ 0,05 mm/m); usar arandelas elásticas y rebajes con holgura"))
FIND.append(("H9", "menor", "Dilatación de la lámina UHMW: solo se da la junta circunferencial; el crecimiento radial del sector no se considera",
             f"junta {s3(ifc_core[2].get('F') and (AL_UH-AL_S)*P['dT']*2*Ro*math.sin(math.pi/P['n_seg']))} mm", f"crecimiento radial {s3(dRad)} mm; fijar cada sector en el centro con agujeros ranurados"))
FIND.append(("H10", "menor", "Pernos avellanados en el disco de 6 mm no evaluados: M8 deja ≈ 1,1 mm bajo la cabeza tras el relapeado; hay corrosión galvánica y de resquicio inox/acero al carbono",
             "sin verificación", "usar M6 (k = 3,3 mm) o discos de 8 mm; sellar el perímetro y proteger el respaldo con imprimante de zinc"))
FIND.append(("H11", "menor", "La masa agregada informada excluye el crecimiento por Δ de ménsulas, patines y pivote",
             f"A {s3(IF[1]['mAdd'])} kg; B {s3(IF[2]['mAdd'])} kg", f"A +{s3(mt[1]-mt[0])} kg; B +{s3(mt[2]-mt[0])} kg en el total del conjunto"))

# ======================================================================================
# Resumen
# ======================================================================================
bad = [c for c in COMP if c[5] == "discrepa"]
nco = sum(1 for c in COMP if c[5] == "coincide")
table("Discrepancias numéricas entre el cálculo propio y el núcleo", ["Prueba", "Magnitud", "Propio", "Núcleo", "Δ %", "Veredicto"], bad if bad else [["—", "ninguna", "", "", "", ""]])
table("Hallazgos", ["Id", "Severidad", "Hallazgo", "Núcleo", "Corregido / efecto"], FIND)
sev = {k_: sum(1 for f in FIND if f[1] == k_) for k_ in ("crítica", "importante", "menor")}
print(f"\nRESULTADO: {nco} coincidencias, {len(bad)} discrepancias numéricas; barridos {sw_n} comparaciones, {sw_bad} discrepancias; hallazgos: "
      f"{sev['crítica']} críticos, {sev['importante']} importantes, {sev['menor']} menores")
sys.exit(1 if sev["crítica"] or sev["importante"] else 0)
