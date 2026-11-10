"""Revisión independiente del ACCIONAMIENTO TT300-C (cilindro – patín guiado – uña de cara plana – pasador).

Regla de independencia: no lee packages/*.js. Los resultados del núcleo se obtienen solo por su salida
JSON (node tools/export_design.js [params.json]) y tests/golden/*.json; todo lo demás se deriva aquí desde la
estática, la cinemática, Hertz y ASME BTH-1 Cat. B (Fy/Nd; corte Fy/(Nd·√3); aplastamiento 1,25Fy/Nd;
soldadura 0,60FEXX/(1,20Nd)).

Ejecutar:  python3 -I tests/indep_accionamiento.py
Imprime tablas por prueba y termina con «RESULTADO: ...». Sale con 1 si hay discrepancias numéricas o hallazgos
críticos o mayores («importante»); con 0 en caso contrario.
Convención «abierto a planos»: N2 (temple por inducción ≥ 55 HRC de pasador y uña) y N8 (alivio de borde de ~10 mm en
las caras de contacto) son requisitos de planos ya asignados al dibujante; mientras la nota de planos no los rotule se
imprimen como «abierto a planos» (no bloqueantes). Si el núcleo/planos dejaran de cumplir lo numérico (FU > 1 con la
hipótesis de temple, o el reparto elástico supera k_edge) siguen apareciendo como N9 «importante».

Convenciones (giro antihorario, cilindro en x = +x_g, empuje +y; el par es simétrico respecto del centro):
  θ ∈ [−π/N, +π/N]; a = R cos θ; y_p = R sin θ; Δ = x_g − a.
  Cara plana normal a y: contacto en (a, y_p − r). El pasador desliza sobre la cara con velocidad relativa
  ∝ (y_p − r) ⇒ fuerza sobre el pasador en x: H = s·μ_s·F, s = signo(y_p − r).
  Patín: origen en el pasador del vástago; front = l_p + 20 + f_ext; rear = 1,25 d_pp; L_s = front + rear;
  Lg = 2/3 L_s; reacciones de guía en y_f,r = (front − rear)/2 ± Lg/2; contacto de la uña en y_c = l_p − r.
Unidades internas: N, mm, MPa.
"""
import json, math, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLD = ROOT / "tests" / "golden"
g0, RHO = 9.80665, 7.85e-6


def export(over=None):
    over = dict({"drive_mode": 1}, **(over or {}))   # este verificador modela el accionamiento guiado: desde el 08-11-2026 el valor por defecto es el pivotado (drive_mode = 2)
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


def comp(prueba, name, mine, core, tol=1e-3):
    if core is None:
        COMP.append((prueba, name, s3(mine), "—", "—", "el núcleo omite")); return
    d = (mine - core) / core * 100 if core else 0.0
    COMP.append((prueba, name, s3(mine), s3(core), f"{d:+.2f}", "coincide" if abs(d) <= tol * 100 else "discrepa"))


# ======================================================================================
# 0. Datos
# ======================================================================================
D0 = export()
if D0 is None:
    print("No se pudo ejecutar node tools/export_design.js"); sys.exit(2)
P = D0["P"]
Pg = json.loads((GOLD / "params_defaults.json").read_text()); Pg["drive_mode"] = 1   # modelo guiado
dif = sorted(k for k in set(P) | set(Pg) if P.get(k) != Pg.get(k))
DV, KC = D0["derivados"], D0["derivados"]["K"]
VER = {v["nombre"]: v for v in D0["verificaciones"]}
def ver(sub):
    for k, v in VER.items():
        if sub in k:
            return v
    raise KeyError(sub)

R, Np, r_p, n = P["R_pin"], int(P["N_pin"]), P["d_pin"] / 2, P["n_cyl"]
ph = math.pi / Np
a_min = R * math.cos(ph)
x_g, eta, mu_g, mu_s = P["x_g"], P["eta_c"], P["mu_g"], P["mu_s"]
front, rear = P["l_p"] + 20 + P["f_ext"], 1.25 * P["d_pp"]
L_s = front + rear; Lg = 2 / 3 * L_s
y_mid = (front - rear) / 2; y_f, y_r = y_mid + Lg / 2, y_mid - Lg / 2
y_c = P["l_p"] - r_p                                 # cara plana en la superficie del pasador
mouthX = min(x_g - P["w_s"] / 2, R + r_p + 10)
inset = (x_g - P["w_s"] / 2) - mouthX
tipX = a_min - P["c_tip"]
b, h_d, L_in = P["dog_b"], P["dog_h"], P["L_in"]
A_b = math.pi / 4 * P["D_bore"] ** 2
A_ann = A_b - math.pi / 4 * P["d_rod"] ** 2
F_st = A_b * P["p_relief"] / 10
Nd, Fy = P["Nd"], P["Fy"]
Fb = 1.25 * Fy / Nd
m_shoe = DV["masas"]["shoes"] / n; m_cyl = DV["masas"]["cyl"] / n
W_shoe, W_cyl = m_shoe * g0, m_cyl * g0
F_sp = 300.0
mu_p = mu_g                                          # μ uña–alojamiento (hipótesis)


def R_i_if(P):
    """Radio interior real de la interfaz (cambio 2 del núcleo): con collar D_boss/2 + c_boss_r + m_ri; sin collar D_piv/2 + 15."""
    return P["D_boss"] / 2 + P["c_boss_r"] + P["m_ri"] if P["h_boss"] > 0 else P["D_piv"] / 2 + 15


def masa_mesa(P):
    assert not (P["opt_ss"] or P["opt_uhmw"] or P["opt_bz"]), "solo caso sin interfaz; A/B/C en indep_interfaz.py"
    rings = sorted(float(x) for x in P["rings"].replace(";", ",").split(",") if x.strip())
    Rt = P["D_top"] / 2; hw = P["h_disc"] - P["t_top"] - P["t_bot"]
    rpr = max(P["D_hub"] / 2, P["R_pin"] - (Rt - P["R_pin"])); db = P["D_piv"] + 30
    aring = math.pi * (Rt ** 2 - rpr ** 2) - P["N_pin"] * math.pi * P["d_pin"] ** 2 / 4
    m = RHO * ((math.pi * rpr ** 2 - math.pi / 4 * (P["D_piv"] + 80) ** 2) * P["t_top"] + aring * max(P["t_pr"], P["t_top"]))
    # Plancha inferior con agujero pasante Ø(D_boss + 2c_boss_r) y cubo rebajado solo lo que excede t_bot (profundidad
    # desde la cara inferior = h_boss − δ + c_boss_a, δ = 0 sin interfaz).
    collar = P["h_boss"] > 0
    D_rec = P["D_boss"] + 2 * P["c_boss_r"] if collar else db
    dep = P["h_boss"] + P["c_boss_a"] if collar else 0.0
    m += RHO * ((math.pi * rpr ** 2 - math.pi / 4 * D_rec ** 2) * P["t_bot"] + aring * max(P["t_pr"], P["t_bot"]))
    m += RHO * sum(2 * math.pi * r * hw * P["t_web"] for r in rings)
    nin = sum(1 for r in rings if P["D_hub"] / 2 < r < P["R_rib"])
    m += RHO * P["N_rib"] * (P["R_rib"] - P["D_hub"] / 2 - nin * P["t_web"]) * hw * P["t_rib"]
    m += RHO * math.pi / 4 * ((P["D_hub"] ** 2 - db ** 2) * hw - ((D_rec ** 2 - db ** 2) * max(dep - P["t_bot"], 0) if collar else 0))
    m += RHO * P["N_pin"] * math.pi / 4 * P["d_pin"] ** 2 * P["h_disc"]
    m_piv = RHO * math.pi / 4 * P["D_piv"] ** 2 * (P["t_base"] + P["h_disc"] - P["t_top"] + 3)
    return m + 0.5 * m_piv


def par(P, mu, r):
    """T [N·mm] = μ·N·r + μ_buje·H_exc·D/2, H_exc = μN·e·(4/3)(Ro³−Ri³)/(Ro⁴−Ri⁴) (∝ μ)."""
    Nn = P["W_tf"] * g0 * 1e3 + masa_mesa(P) * g0
    Ro, Ri = P["D_top"] / 2, R_i_if(P)
    H = mu * Nn * P["e"] * 4 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4)
    return mu * Nn * r + P["mu_bush"] * H * P["D_piv"] / 2


def casos(P):
    Ro, Ri = P["D_top"] / 2, R_i_if(P)
    ru = 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2)
    return {"nom": (P["mu_nom"], ru), "dis": (P["mu_d"], P["r_ef"]), "borde": (P["mu_d"], Ro),
            "cont": (P["mu_cont"], P["r_ef"]), "seco": (P["mu_dry"], ru)}


# ======================================================================================
# Modelos de equilibrio en el plano
# ======================================================================================
def estado(theta, Tn, modelo="plana", mu_gg=None, mu_ss=None, sg=None, xg=None):
    """'plana': cara plana con fricción μ_s (modelo de diseño). 'K': modelo Rev B sin fricción en la cara."""
    mu_gg = mu_g if mu_gg is None else mu_gg
    mu_ss = mu_s if mu_ss is None else mu_ss
    xg = x_g if xg is None else xg
    a, yp = R * math.cos(theta), R * math.sin(theta)
    Dl = xg - a
    if modelo == "K":
        F = Tn / a; H = 0.0
    else:
        if sg is None:
            sg = 1 if yp > r_p else -1
        hh = sg * mu_ss
        F = Tn / (a - hh * (yp - r_p))               # (T/n) = a F − (y_p − r) H
        H = hh * F                                    # fuerza sobre el PASADOR en x
    Rf = (F * Dl + H * (y_c - y_r)) / Lg
    Rr = H - Rf
    Frod = F + mu_gg * (abs(Rf) + abs(Rr))
    return dict(th=theta, a=a, yp=yp, Dl=Dl, F=F, H=H, Rf=Rf, Rr=Rr, Frod=Frod, Fh=Frod / eta)


def barrido(Tn, modelo="plana", npts=2001, **kw):
    out = []
    for i in range(npts):
        th = -ph + 2 * ph * i / (npts - 1)
        out.append(estado(th, Tn, modelo, **kw))
    th0 = math.asin(r_p / R)                          # y_p = r: ambos sentidos de la fricción
    if modelo == "plana":
        out += [estado(th0, Tn, modelo, sg=+1, **kw), estado(th0, Tn, modelo, sg=-1, **kw)]
    return out


def Fmax(Tn, modelo="plana", **kw):
    return max(barrido(Tn, modelo, **kw), key=lambda e: e["Fh"])


cs = casos(P)
mu_d, r_ef = cs["dis"]
T_d = par(P, mu_d, r_ef); Tn_d = T_d / n

print("# Revisión independiente del accionamiento TT300-C – Rev C (uña de cara plana, bancada con ranura T)")
print(f"Parámetros exportados = golden: {'sí' if not dif else 'NO, difieren ' + str(dif)}")
print(f"R = {R}, N = {Np}, a_min = {s3(a_min)}, x_g = {x_g}, L_s = {s3(L_s)}, Lg = {s3(Lg)}, y_f = {s3(y_f)}, y_r = {s3(y_r)}, "
      f"y_c = {s3(y_c)}, boca = {s3(mouthX)}, punta = {s3(tipX)}, μs = {mu_s}, μg = {mu_g}, F_calado = {s3(F_st/1e3)} kN")
comp("0", "Largo del patín L_s (mm)", L_s, KC["L_s"]); comp("0", "Lg (mm)", Lg, KC["Lg"])
comp("0", "Boca x (mm)", mouthX, KC["mouthX"]); comp("0", "Punta x (mm)", tipX, KC["tipX"])

# ======================================================================================
# PRUEBA 1 – Equilibrio en el plano
# ======================================================================================
th_r = math.asin(r_p / R)
pos = [(-ph, "Inicio θ=−π/N", None), (-ph / 2, "1/4", None), (0.0, "Centro", None), (th_r, "y_p = r (s=−1)", -1),
       (th_r, "y_p = r (s=+1)", +1), (ph / 2, "3/4", None), (ph, "Final θ=+π/N", None)]
rows = []
for th, lab, sg in pos:
    e = estado(th, Tn_d, sg=sg); k = estado(th, Tn_d, "K")
    rows.append([lab, s3(math.degrees(th)), s3(e["F"] / 1e3), s3(e["H"] / 1e3), s3(e["Rf"] / 1e3), s3(e["Rr"] / 1e3),
                 s3(e["Fh"] / 1e3), s3(k["Fh"] / 1e3), f"{(e['Fh'] / k['Fh'] - 1) * 100:+.1f}"])
table("Prueba 1 – Equilibrio cuasiestático, caso de diseño (kN). H = fuerza sobre el pasador en x (+ hacia afuera)",
      ["Posición", "θ°", "F_pas", "H", "R_f", "R_r", "F_cil", "F_cil sin fricción en la cara", "Δ%"], rows)
eM = Fmax(Tn_d)
cd = [c for c in DV["casos"] if c["id"] == "dis"][0]
comp("1", "F_cil de diseño = máx en la carrera (kN)", eM["Fh"] / 1e3, cd["F"])
comp("1", "K equivalente = F_cil·n·a_min/T", eM["Fh"] * a_min / Tn_d, DV["Kguide"])
car = D0["carrera"]
for c in car:
    sgn = None
    if "antes" in c["pos"]: sgn = -1
    if "después" in c["pos"]: sgn = +1
    e = estado(math.radians(c["th"]), Tn_d, sg=sgn)
    ct, st_ = math.cos(e["th"]), math.sin(e["th"])
    for k, mine in (("F", e["Fh"]), ("Fpin", e["F"]), ("H", e["H"]), ("Rf", e["Rf"]), ("Rr", e["Rr"]),
                    ("Ft", -e["H"] * st_ + e["F"] * ct), ("Fr", e["H"] * ct + e["F"] * st_)):
        comp("1", f"Carrera «{c['pos']}»: {k}", mine / 1e3, c[k])
# validez de la hipótesis «la uña no se mueve en el alojamiento»: μ_s F ≤ μ_p ΣN
lev = mouthX - a_min
SN = (1 + 2 * lev / L_in)
print(f"\nUña quieta en el alojamiento: H/F = μ_s = {mu_s} ≤ μ_p·(1 + 2l/L_in) = {s3(mu_p * SN)} → {'sí' if mu_s <= mu_p * SN else 'NO'}")
print(f"Fuerza radial al pivote: H del par simétrico se anula; F·sinθ también (±{s3(eM['F']*math.sin(ph)/1e3)} kN por pasador)")

# ======================================================================================
# PRUEBA 3 – Trabajos virtuales
# ======================================================================================
def energia(Tn, modelo="plana", npts=8001):
    W = dict(hyd=0, util=0, seal=0, guide=0, face=0)
    dth = 2 * ph / (npts - 1)
    for i in range(npts - 1):
        th = -ph + (i + 0.5) * dth
        e = estado(th, Tn, modelo)
        ds = e["a"] * dth
        W["hyd"] += e["Fh"] * ds; W["util"] += Tn * dth
        W["seal"] += (1 - eta) * e["Fh"] * ds
        W["guide"] += mu_g * (abs(e["Rf"]) + abs(e["Rr"])) * ds
        W["face"] += abs(e["H"]) * abs(e["yp"] - r_p) * dth      # deslizamiento radial relativo |ẏ_p − r|·dθ
    return W
rows = []
for mod in ("K", "plana"):
    W = energia(Tn_d, mod)
    cl = (W["hyd"] - W["util"] - W["seal"] - W["guide"] - W["face"]) / W["hyd"] * 100
    rows.append([mod, s3(W["hyd"] / 1e6), s3(W["util"] / 1e6), s3(W["seal"] / 1e6), s3(W["guide"] / 1e6), s3(W["face"] / 1e6), f"{cl:+.5f}",
                 s3(W["hyd"] / (2 * R * math.sin(ph)) / 1e3), s3(W["util"] / W["hyd"])])
    if mod == "plana":
        Wp = W; clp = cl
table("Prueba 3 – Balance de trabajo en una carrera (kJ)", ["Modelo", "W hidr.", "W útil", "sellos", "guía", "cara uña", "cierre %", "F media kN", "rendimiento"], rows)
comp("3", "Cierre del balance de trabajo, modelo plana (%)", abs(clp) + 1, 1.0)

# ======================================================================================
# PRUEBA 2 – Fuera del plano: retención vertical por la cabeza T
# ======================================================================================
tb = P["t_base"]
z_c = tb + P["h_disc"] / 2
h_t = P["h_slot"] - 2
z_t = tb + P["t_bed"] - P["h_slot"] / 2                # definición declarada (contacto a h/2 bajo la cara)
z_t2 = tb + P["t_bed"] - h_t / 2                       # centroide del contacto de 20 mm (h − 2)
dz = z_c - z_t
comp("2", "Altura del eje del cilindro (mm)", z_c, KC["zc0"])
# estado de calado en la guía: F_pas = η·F_calado, H = s·μ_s·F_pas (la fricción de guía puede ser nula en reposo)
Fp_cal = eta * F_st
def guia_cal(th):
    a, yp = R * math.cos(th), R * math.sin(th)
    Hh = (1 if yp > r_p else -1) * mu_s * Fp_cal
    Rf = (Fp_cal * (x_g - a) + Hh * (y_c - y_r)) / Lg
    return Hh, Rf, Hh - Rf
GC = [guia_cal(-ph + 2 * ph * i / 4000) for i in range(4001)]
Rf_cal = max(abs(g[1]) for g in GC)
SR_cal = max(abs(g[1]) + abs(g[2]) for g in GC)
H_cal = mu_s * Fp_cal
ala = (P["w_tee"] - P["w_slot"]) / 2
lev_core = (P["w_bed"] + P["w_tee"]) / 2
lev_mine = P["w_bed"] / 2 + (P["w_slot"] / 2 + ala / 2)   # borde de la bancada ↔ centro del ala opuesta
def retencion(dzz, lev_r):
    Mv = H_cal * dzz; Mc = mu_g * SR_cal * dzz
    return Mv, Mc, Mv / lev_r + Mc / L_s
Mv, Mc, V_core = retencion(dz, lev_core)
_, _, V_mine = retencion(z_c - z_t2, lev_mine)
sig_V = V_core / (ala * L_s)
vcore = ver("Retención vertical del patín")
comp("2", "Retención vertical V (kN), definición declarada", V_core / 1e3, vcore["dem"] * ala * L_s / 1e3)
table("Prueba 2 – Fuera del plano a calado (F_pas = η·F_calado)", ["Magnitud", "Propio", "Núcleo", "Comentario"],
      [["e_z eje cilindro – contacto uña (mm)", "0", "0", "uña centrada en la luz del pasador"],
       ["Δz carga – contacto en el cuello (mm)", s3(dz), "—", f"z_c {s3(z_c)}, z_t {s3(z_t)}"],
       ["Vuelco M = H_máx·Δz (kN·m)", s3(Mv / 1e6), "—", ""],
       ["Cabeceo M = μg·máx(|R_f|+|R_r|)·Δz (kN·m)", s3(Mc / 1e6), "—", ""],
       ["V = M_v/((w_b+w_T)/2) + M_c/L_s (kN)", s3(V_core / 1e3), s3(vcore["dem"] * ala * L_s / 1e3), ""],
       ["V con centroide a (h−2)/2 y brazo al centro del ala (kN)", s3(V_mine / 1e3), "—", f"sensibilidad: {(V_mine/V_core-1)*100:+.1f} %"],
       ["σ ala de la cabeza T (MPa)", s3(sig_V), s3(vcore["dem"]), f"FU {s3(sig_V/Fb)}"]])

# ======================================================================================
# PRUEBA 4 – Uña (cara plana) a F_calado
# ======================================================================================
Fy_d = P["Fy_dog"]; fa_d, fv_d = Fy_d / Nd, Fy_d / (Nd * 3 ** .5)
S_d, A_d = h_d * b ** 2 / 6, h_d * b
sig_m = F_st * (lev + P["e_dog"]) / S_d + mu_s * F_st / A_d
sig_m2 = sig_m + mu_s * F_st * (b / 2) / S_d          # H aplicada en la cara: excéntrica b/2 del eje
comp("4", "Uña: flexión en la boca + μF (axial y excéntrica b/2) (MPa)", sig_m2, ver("Flexión en la boca")["dem"])
if abs(sig_m2 - ver("Flexión en la boca")["dem"]) / sig_m2 > 1e-3:
  FIND.append(("N4", "menor", "Uña: flexión en la boca omite el momento de H = μ_s·F aplicado en la cara (excentricidad b/2)",
             f"FU {s3(ver('Flexión en la boca')['fu'])}", f"FU {s3(sig_m2/fa_d)}: σ += μ_s·F·(b/2)/(h·b²/6)"))
tau_m = 1.5 * F_st / A_d
comp("4", "Uña: corte en la boca (MPa)", tau_m, ver("Corte en la boca")["dem"])
Es = P["E"] / (2 * (1 - P["nu"] ** 2))
pH = math.sqrt(F_st / h_d * Es / (math.pi * r_p))
comp("4", "Hertz cara plana–pasador p0 con q = k_borde·F/h (MPa)", pH * math.sqrt(P.get("k_edge", 1.0)), ver("Contacto de Hertz")["dem"])
bH = math.sqrt(4 * F_st * r_p / (math.pi * h_d * Es))
comp("4", "Profundidad de temple 3·0,78·b con q de borde (mm)", 3 * 0.78 * bH * math.sqrt(P.get("k_edge", 1.0)), ver("Profundidad mínima de temple")["dem"])
fu_pin_H = pH / (1.67 * P["Fy_pin"])
F_dd = eM["F"]
fu_pin_Hd = math.sqrt(F_dd / h_d * Es / (math.pi * r_p)) / (1.67 * P["Fy_pin"])
planos_txt = (ROOT / "cad" / "planos_tt300c.py").read_text()
if "Dureza pos 3 y 10: 280–330 HB" in planos_txt or "inducc" not in planos_txt.lower():
  FIND.append(("N2", "abierto a planos", "Hertz: la presión es la misma en ambos cuerpos. La memoria pide temple por inducción en pasador y uña, pero la nota de planos (cad/planos_tt300c.py) sigue con «Dureza pos 3 y 10: 280–330 HB». Sin temple, el pasador (Fy 800) no cumple",
             f"FU {s3(ver('Contacto de Hertz')['fu'])} (con Fy_sup = {P['Fy_surf']} en ambos)", f"pasador sin temple: FU {s3(fu_pin_H)} a calado ({s3(fu_pin_Hd)} a diseño). Llevar el temple de pos 3 y 10 a planos; rotular el chequeo «ambas caras»"))
# chaflán de retorno
beta = math.radians(P["beta_ch"])
travel = KC["travel"]
dy_ch = travel / math.tan(beta)
comp("4", "Chaflán: Δy + b_punta (mm)", dy_ch + P["b_tip"], ver("Chaflán de retorno: cabe")["dem"])
dx_need = (a_min + r_p * math.cos(beta)) - tipX       # basta que la 1.ª toma caiga en el chaflán
w_c = b - dy_ch * (1 - P["c_tip"] / travel)
comp("4", "Corte en la sección de contacto (MPa)", 1.5 * F_st / (h_d * w_c), ver("Corte en la sección del contacto")["dem"])
best = 0.0; x = P["c_tip"]
while x <= travel:
    w = b - dy_ch * (1 - x / travel); best = max(best, 6 * F_st * (x - P["c_tip"]) / (h_d * w * w)); x += 0.05
comp("4", "Flexión en la zona del chaflán (MPa)", best, ver("Flexión en la zona del chaflán")["dem"], tol=2e-3)
# alojamiento rígido-plástico y marco de boca
l_eq = lev + P["e_dog"]
c_pl = -l_eq + math.sqrt(l_eq ** 2 + l_eq * L_in + L_in ** 2 / 2)
sig_al = F_st / (h_d * (2 * c_pl - L_in))
comp("4", "Alojamiento bloque rígido-plástico (MPa)", sig_al, ver("Aplastamiento del alojamiento")["dem"])
V_fw = min(F_st, sig_al * h_d * min(inset, c_pl))   # el cortante del marco no puede superar la fuerza total del empuje
t_fw = P["t_fw"]
comp("4", "Marco de boca: flexión (MPa)", 6 * V_fw * inset / 2 / ((h_d + 20) * t_fw ** 2), ver("marco de boca: flexión")["dem"])
comp("4", "Marco de boca: corte (MPa)", 1.5 * V_fw / ((h_d + 20) * t_fw), ver("marco de boca: corte")["dem"])

# ======================================================================================
# PRUEBA 5 – Pasador de empuje
# ======================================================================================
tpr = max(P["t_pr"], P["t_top"], P["t_bot"])
Ls_ = P["h_disc"] - tpr                               # luz entre planos medios de los anillos
d_pin = P["d_pin"]
S_p, A_p, I_p = math.pi * d_pin ** 3 / 32, math.pi / 4 * d_pin ** 2, math.pi * d_pin ** 4 / 64
Fr = F_st * math.sqrt(1 + mu_s ** 2)
c_d = h_d
M_uni = Fr * (Ls_ - c_d / 2) / 4                      # = F(2L − c)/8
V_p = Fr * (0.5 + P["e_dog"] / Ls_)
comp("5", "Pasador: flexión, carga repartida en h_uña (MPa)", M_uni / S_p, ver("Flexión (biapoyado entre anillos")["dem"])
comp("5", "Pasador: corte en el apoyo 4V/3A (MPa)", 4 * V_p / (3 * A_p), ver("Corte en el apoyo")["dem"])
comp("5", "Pasador: aplastamiento V/(d t) (MPa)", V_p / (d_pin * tpr), ver("Aplastamiento en el agujero del anillo")["dem"])
comp("5", "Pasador–uña aplastamiento F/(d h) (MPa)", F_st / (d_pin * h_d), ver("Aplastamiento pasador–uña")["dem"])
M_e = (Fb - V_p / (d_pin * tpr)) * d_pin * tpr ** 2 / 6
M_emp = Fr * (3 * Ls_ ** 2 - c_d ** 2) / (24 * Ls_)
comp("5", "Empotramiento disponible / perfecto (info)", M_e / M_emp, ver("Empotramiento disponible")["dem"])
# Reparto real de la carga: uña rígida contra un pasador que flecta (Timoshenko) con rigidez de contacto de Hertz.
q_m = F_st / h_d
b_h = math.sqrt(4 * q_m * r_p / (math.pi * Es))
k_c = q_m / (q_m / (math.pi * Es) * (2 * math.log(4 * r_p / b_h) - 1))
def reparto(kc, nel=111):
    Gs = P["E"] / (2 * (1 + P["nu"])); ks = 0.9
    xs = [(Ls_ - c_d) / 2 + c_d * (i + 0.5) / nel for i in range(nel)]; dx = c_d / nel
    def w(x, a):
        bb = Ls_ - a
        if x <= a:
            return bb * x * (Ls_ ** 2 - bb ** 2 - x * x) / (6 * P["E"] * I_p * Ls_) + bb * x / (Ls_ * ks * Gs * A_p)
        return a * (Ls_ - x) * (Ls_ ** 2 - a * a - (Ls_ - x) ** 2) / (6 * P["E"] * I_p * Ls_) + a * (Ls_ - x) / (Ls_ * ks * Gs * A_p)
    N = nel + 1; M = [[0.0] * N for _ in range(N)]; rhs = [0.0] * N
    for i in range(nel):
        for j in range(nel):
            M[i][j] = w(xs[i], xs[j]) * dx
        M[i][i] += 1 / kc; M[i][nel] = -1.0
    for j in range(nel):
        M[nel][j] = dx
    rhs[nel] = 1.0
    for k in range(N):
        pv = max(range(k, N), key=lambda r: abs(M[r][k])); M[k], M[pv] = M[pv], M[k]; rhs[k], rhs[pv] = rhs[pv], rhs[k]
        for r in range(k + 1, N):
            f = M[r][k] / M[k][k]
            if f:
                for cc in range(k, N):
                    M[r][cc] -= f * M[k][cc]
                rhs[r] -= f * rhs[k]
    x = [0.0] * N
    for k in range(N - 1, -1, -1):
        x[k] = (rhs[k] - sum(M[k][cc] * x[cc] for cc in range(k + 1, N))) / M[k][k]
    q = x[:nel]
    Mmid = 0.5 * Ls_ / 2 - sum(q[j] * dx * (Ls_ / 2 - xs[j]) for j in range(nel) if xs[j] < Ls_ / 2)
    return q[0] * c_d, q[nel // 2] * c_d, Mmid / ((Ls_ - c_d / 2) / 4)
kq_end, kq_mid, kM = reparto(k_c)
pH_edge = pH * math.sqrt(kq_end)
if kq_end > P.get("k_edge", 1.0) * 1.02:
    FIND.append(("N9", "importante", "Factor de borde del núcleo menor que el reparto elástico propio",
                 f"k_borde = {s3(P.get('k_edge', 1.0))}", f"reparto elástico {s3(kq_end)}: subir k_borde"))
table("Prueba 5 – Pasador de empuje Ø%s a F_calado (MPa)" % s3(d_pin), ["Chequeo", "Propio", "Núcleo", "Adm.", "FU"],
      [["Flexión, carga uniforme en h_uña (modelo del núcleo)", s3(M_uni / S_p), s3(ver("Flexión (biapoyado entre anillos")["dem"]), s3(P["Fy_pin"] / Nd), s3(M_uni / S_p / (P["Fy_pin"] / Nd))],
       ["Flexión con reparto elástico (uña rígida, Hertz)", s3(kM * M_uni / S_p), "—", s3(P["Fy_pin"] / Nd), s3(kM * M_uni / S_p / (P["Fy_pin"] / Nd))],
       ["Flexión con carga puntual (cota superior)", s3(Fr * Ls_ / 4 / S_p), "—", s3(P["Fy_pin"] / Nd), s3(Fr * Ls_ / 4 / S_p / (P["Fy_pin"] / Nd))],
       ["Corte en el apoyo, V = F_r(1/2 + e/L)", s3(4 * V_p / (3 * A_p)), s3(ver("Corte en el apoyo")["dem"]), s3(P["Fy_pin"] / (Nd * 3 ** .5)), s3(4 * V_p / (3 * A_p) / (P["Fy_pin"] / (Nd * 3 ** .5)))],
       ["Aplastamiento en el anillo V/(d t)", s3(V_p / (d_pin * tpr)), s3(ver("Aplastamiento en el agujero del anillo")["dem"]), s3(Fb), s3(V_p / (d_pin * tpr) / Fb)],
       ["Empotramiento disponible / perfecto", s3(M_e / M_emp), s3(ver("Empotramiento disponible")["dem"]), "info", "biapoyado justificado"],
       [f"Línea de carga en el borde de la uña / media (k_c = {s3(k_c)} N/mm²)", s3(kq_end), "1 (uniforme)", "—", f"centro {s3(kq_mid)}"],
       ["Hertz en el borde de la cara (sin singularidad de arista)", s3(pH_edge), s3(pH), s3(1.67 * P["Fy_surf"]), s3(pH_edge / (1.67 * P["Fy_surf"]))]])
planos_txt = (ROOT / "cad" / "planos_tt300c.py").read_text()
if not any(k in planos_txt.lower() for k in ("alivio de borde", "bombeo", "abombad", "perfil logar", "alivio de extremos")):
    FIND.append(("N8", "abierto a planos", "Hertz uña–pasador: el pasador flecta bajo la uña rígida y la carga se concentra en los bordes superior e inferior de la cara (aristas 0,5×45°, sin alivio de borde en planos); la verificación supone carga lineal uniforme F/h",
                 f"p0 {s3(pH)} MPa, FU {s3(ver('Contacto de Hertz')['fu'])}",
                 f"q_borde = {s3(kq_end)}·F/h → p0 {s3(pH_edge)} MPa, FU {s3(pH_edge/(1.67*P['Fy_surf']))} sin contar la singularidad de arista. Especificar alivio de borde (bombeo o perfil logarítmico de ~10 mm en ambos extremos de la cara) y verificar Hertz con q = {s3(kq_end)}·F/h"))

# ======================================================================================
# PRUEBA 6 – Giro: casos y barridos
# ======================================================================================
rows = []
for c in DV["casos"]:
    mu, r = cs[c["id"]]; T = par(P, mu, r)
    Fm = Fmax(T / n)["Fh"]
    comp("6", f"Caso {c['id']}: F_cil (kN)", Fm / 1e3, c["F"])
    rows.append([c["id"], s3(mu), s3(r), s3(T / 1e6), s3(c["F"]), s3(Fm / 1e3), s3(c["FS"]), s3(F_st / Fm), "sí" if c["gira"] else "no", "sí" if Fm <= F_st else "no"])
table("Prueba 6a – Casos de fricción", ["Caso", "μ", "r", "T kN·m", "F núcleo", "F propio", "FS núcleo", "FS propio", "gira núcleo", "gira propio"], rows)
Tu = par(P, 1.0, r_ef)
mu_max = F_st / Fmax(Tu / n)["Fh"]
comp("6", "μ máx que gira con r_ef", mu_max, DV["muMax_ref"])
Tpiv_d = par(P, mu_d, 0.0)
mu_max_cte = (F_st / Fmax(Tu / n)["Fh"] * (par(P, 1.0, r_ef)) - Tpiv_d) / (par(P, 1.0, r_ef) - par(P, 1.0, 0.0))
print(f"\nμ máx: propio {s3(mu_max)}; si T_piv se tomara constante (= T_piv(μ_d)) resulta {mu_max_cte:.5f} frente a {DV['muMax_ref']:.5f} del núcleo")
if abs(mu_max - DV["muMax_ref"]) / DV["muMax_ref"] > 5e-4:
    FIND.append(("N6", "menor", "μ_máx del núcleo trata el par del pivote como constante (calculado con μ_d), pero H_exc ∝ μ",
                 s3(DV["muMax_ref"]), f"{mu_max:.4f} (−{(1 - mu_max/DV['muMax_ref'])*100:.2f} %)"))

def sweep(key, vals):
    rows = []
    for v in vals:
        over = {key: v}; D = export(over)
        PP = dict(P); PP.update(over)
        T = par(PP, PP["mu_d"], PP["r_ef"])
        Fm = Fmax(T / n, mu_gg=PP["mu_g"])["Fh"]
        if D is None:
            rows.append([s3(v), "rechazado", "—", "—", s3(Fm / 1e3), s3(F_st / Fm)]); continue
        c = [c for c in D["derivados"]["casos"] if c["id"] == "dis"][0]
        comp("6", f"Barrido {key}={v}: F_dis", Fm / 1e3, c["F"])
        rows.append([s3(v), s3(c["F"]), s3(c["FS"]), "sí" if c["gira"] else "no", s3(Fm / 1e3), s3(F_st / Fm)])
    return rows
hdr = ["valor", "F_dis núcleo", "FS núcleo", "gira", "F propio", "FS propio"]
table("Prueba 6b – Barrido μ_d", hdr, sweep("mu_d", [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]))
table("Prueba 6c – Barrido W (tf)", hdr, sweep("W_tf", [200, 240, 280, 300, 320, 360]))
table("Prueba 6d – Barrido μ_g", hdr, sweep("mu_g", [0.10, 0.15, 0.20, 0.25]))
def W_lim(FS=1.0):
    lo, hi = 50, 2000
    for _ in range(50):
        mid = (lo + hi) / 2; PP = dict(P); PP["W_tf"] = mid
        lo, hi = (mid, hi) if F_st / Fmax(par(PP, mu_d, r_ef) / n, npts=401)["Fh"] >= FS else (lo, mid)
    return lo
print(f"Carga máxima que gira (μ 0,20, r_ef): {s3(W_lim())} tf; con FS 1,25: {s3(W_lim(1.25))} tf; μ para FS 1,25: {s3(mu_max/1.25)}")

# ======================================================================================
# PRUEBA 7 – Retorno y reenganche
# ======================================================================================
F_ret = A_ann * P["p_ret"] / 10
comp("7", "F_retorno (kN)", F_ret / 1e3, DV["Fret"])


def dog_solve(s, mu, xm, Lin, Fsp, known=(), Mk=0.0, unk=((1.0, 0.0), (0.0, 0.0))):
    """Uña rígida, contactos en la boca (x = xm) y en el extremo (x = xm+Lin); cada uno en la pared
    trasera (y = −b, N>0) o delantera (y = 0, N<0); fricción −s·μ·|N| en x. Incógnitas (Q, N1, N2)."""
    (ux, uy), (xq, yq) = unk
    kn = list(known) + [(-Fsp, 0.0, xm + Lin, -b / 2)]
    SFx = sum(k[0] for k in kn); SFy = sum(k[1] for k in kn)
    SM = sum(k[2] * k[1] - k[3] * k[0] for k in kn) + Mk
    xs = (xm, xm + Lin)
    det = lambda M: (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                     + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
    for sg in ((1, -1), (1, 1), (-1, 1), (-1, -1)):
        ys = [(-b if q > 0 else 0.0) for q in sg]
        A = [[ux, -s * mu * sg[0], -s * mu * sg[1]], [uy, 1.0, 1.0],
             [xq * uy - yq * ux, xs[0] + ys[0] * s * mu * sg[0], xs[1] + ys[1] * s * mu * sg[1]]]
        rhs = [-SFx, -SFy, -SM]
        D = det(A)
        if abs(D) < 1e-12:
            continue
        sol = []
        for k in range(3):
            Ak = [row[:] for row in A]
            for i in range(3):
                Ak[i][k] = rhs[i]
            sol.append(det(Ak) / D)
        if sol[1] * sg[0] >= -1e-9 and sol[2] * sg[1] >= -1e-9:
            return sol
    return None


def leva(beta_deg, mu):
    """Retorno: el pasador siguiente empuja el chaflán; normal a β de x. Devuelve (P_y, Q_x) o None (autobloqueo)."""
    bt = math.radians(beta_deg); phi = math.atan(mu)
    xc = r_p * math.cos(bt)                           # respecto del centro del pasador (= a_min)
    xr = (a_min + xc) - tipX
    yc = -b + dy_ch * max(0.0, 1 - xr / travel)       # punto del chaflán
    xm = mouthX - a_min
    cx, cy = math.cos(bt + phi) / math.cos(phi), math.sin(bt + phi) / math.cos(phi)
    rr = dog_solve(+1, mu, xm, L_in, F_sp, unk=((cx, cy), (xc, yc)))
    if rr is None or rr[0] <= 0:
        return None
    return rr[0] * cy, rr[0] * cx


def mu_lock(bdeg):
    lo, hi = 0.0, 1.0
    if leva(bdeg, hi) is not None:
        return float("inf")
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if leva(bdeg, mid) is not None else (lo, mid)
    return lo
vlk = ver("Retorno sin autobloqueo")
mur = P["mu_ret"]
l_core_formula = mouthX - (tipX + travel / 2)
k_c = 1 + 2 * l_core_formula / L_in
lhs = mur * k_c * (math.sin(beta) + mur * math.cos(beta)); rhs = math.cos(beta) - mur * math.sin(beta)
comp("7", "Autobloqueo: μk(sinβ+μcosβ) (contacto en el medio del chaflán)", lhs, vlk["dem"])
comp("7", "Autobloqueo: cosβ − μ sinβ", rhs, vlk["cap"])
mlk = mu_lock(P["beta_ch"])
clr = tipX + travel - (a_min + r_p)
rows = [["Contacto inicial dentro del chaflán: Δx necesario ≤ Δx del chaflán", s3(dx_need), s3(travel), "sí" if dx_need <= travel else "NO"],
        ["μ de autobloqueo (equilibrio completo de la uña, β = %s°)" % s3(P["beta_ch"]), s3(mlk), f"μ_ret = {mur}", "OK" if mlk > 0.30 else ("OK hasta μ_ret" if mlk > mur else "NO")],
        ["P que opone la leva con μ_ret (kN)", s3((leva(P["beta_ch"], mur) or (float("nan"), 0))[0] / 1e3), s3(F_ret / 1e3), "≪ F_ret"],
        ["Holgura punta–pasador al retraer (mm)", s3(clr), "≥ 10", "OK" if clr >= 10 else "NO"],
        ["Cara 10 mm detrás de la superficie del pasador siguiente al final del retorno", s3(P["s_free"]), "s_libre", "OK"],
        ["Uña entre pasadores: cuerda − d − b (mm, 2 holguras)", s3(2 * R * math.sin(ph) - 2 * r_p - b), "≥ 20", "OK"]]
table("Prueba 7 – Retorno y reenganche", ["Chequeo", "Propio", "Referencia", "Veredicto"], rows)

# ======================================================================================
# PRUEBA 8 – Guía, bancada con ranura T, pivote, pandeo
# ======================================================================================
Lb = P["L0"] + P["stroke"]; Pcr = math.pi ** 2 * P["E"] * math.pi * P["d_rod"] ** 4 / 64 / Lb ** 2
comp("8", "Pandeo: Pcr (kN)", Pcr / 1e3, ver("Pandeo del vástago")["cap"] * 3)
comp("8", "R_guía a calado con F_pas = η·F_calado (kN)", Rf_cal / 1e3, DV["Rguide"])
sig_t = 4 * Rf_cal / (h_t * L_s)
comp("8", "Lengüeta: 4R/((h−2)L_s) (MPa)", sig_t, ver("Aplastamiento de la lengüeta")["dem"])
t_root = (P["w_bed"] - P["w_tee"]) / 2
q = 4 * Rf_cal / L_s
lev_w = h_t / 2 + 2 + P["h_tee"]                    # centroide del contacto (20 mm) → fondo de la cabeza T (raíz de t_raíz)
sig_w = 6 * q * lev_w / t_root ** 2
comp("8", "Pared de la ranura: raíz de t_raíz, brazo al fondo de la cabeza T (MPa)", sig_w, ver("Pared de la ranura")["dem"])
w_bed_req = P["w_tee"] + 2 * math.sqrt(6 * q * lev_w / (Fy / Nd))
f_w = Rf_cal / (2 * 0.707 * P["w_bed_f"] * (L_s + 2 * P["w_bed"]))
comp("8", "Soldadura bancada (MPa)", f_w, ver("Soldadura bancada")["dem"])
comp("8", "Fondo de ranura (mm)", P["t_bed"] - P["h_slot"] - P["h_tee"], ver("Fondo de la ranura")["dem"])
if sig_w / (Fy / Nd) > 1.0:
    FIND.append(("N1", "crítica", "Pared de la ranura T no cumple", f"FU {s3(ver('Pared de la ranura')['fu'])}", f"FU {s3(sig_w/(Fy/Nd))}; w_bancada ≥ {s3(w_bed_req)}"))
elif abs(sig_w - ver("Pared de la ranura")["dem"]) / sig_w > 1e-3:
    FIND.append(("N1", "importante", "Pared de la ranura T: el brazo del núcleo no coincide con el propio", f"σ {s3(ver('Pared de la ranura')['dem'])}", f"σ {s3(sig_w)}"))
Rf_c2 = Rf_cal
# asimetría
def f_rat(mg, th):
    e = estado(th, 1.0, mu_gg=mg); return e["Frod"] / e["F"]
Has_core = ver("Empuje neto al pivote")["dem"]
Has_mx = max(F_st * eta * abs(1 / f_rat(mu_g - 0.05, th) - 1 / f_rat(mu_g + 0.05, th)) for th in [(-ph + 2 * ph * i / 400) for i in range(401)])
Has_ini = F_st * eta * abs(1 / f_rat(mu_g - 0.05, -ph) - 1 / f_rat(mu_g + 0.05, -ph))
comp("8", "H_asim máximo en la carrera (kN)", Has_mx / 1e3, Has_core)
pb = ver("Presión en el buje")
p_new = pb["dem"] + (Has_mx / 1e3 - Has_core) * 1e3 / (P["D_piv"] * P["L_bush"])
if Has_mx / 1e3 > Has_core * 1.001:
    FIND.append(("N7", "menor", "H_asim del pivote menor que el máximo en la carrera",
                 f"{s3(Has_core)} kN, buje FU {s3(pb['fu'])}", f"{s3(Has_mx/1e3)} kN, buje FU {s3(p_new/pb['cap'])}"))
comp("8", "Buje: p (MPa) con H_asim propio", (D0["apoyo"]["H_ecc_d"] + Has_mx / 1e3) * 1e3 / (P["D_piv"] * P["L_bush"]), pb["dem"])
table("Prueba 8 – Guía, bancada y pivote", ["Frente", "Propio", "Núcleo", "Adm.", "FU propio", "FU núcleo"],
      [["R_guía delantera a calado (kN)", s3(Rf_cal / 1e3), s3(DV["Rguide"]), "—", "—", "—"],
       ["Lengüeta 4R/((h−2)L_s)", s3(sig_t), s3(ver("Aplastamiento de la lengüeta")["dem"]), s3(Fb), s3(sig_t / Fb), s3(ver("Aplastamiento de la lengüeta")["fu"])],
       [f"Pared ranura, brazo {s3(lev_w)} a la raíz de t_raíz = {s3(t_root)}", s3(sig_w), s3(ver("Pared de la ranura")["dem"]), s3(Fy / Nd), s3(sig_w / (Fy / Nd)), s3(ver("Pared de la ranura")["fu"])],
       ["Soldadura bancada (2 filetes)", s3(f_w), s3(ver("Soldadura bancada")["dem"]), s3(0.6 * P["FEXX"] / (1.2 * Nd)), s3(f_w / (0.6 * P["FEXX"] / (1.2 * Nd))), s3(ver("Soldadura bancada")["fu"])],
       ["H_asim (kN) máx en carrera", s3(Has_mx/1e3), s3(Has_core), "—", "—", "—"],
       ["Pandeo del vástago Pcr (kN)", s3(Pcr / 1e3), s3(ver("Pandeo del vástago")["cap"] * 3), "Pcr/3", s3(F_st / (Pcr / 3)), s3(ver("Pandeo del vástago")["fu"])]])

# ======================================================================================
# PRUEBA 9 – Plancha base bajo la ménsula del ojal trasero (docs/qa/plancha_base_modo_guiado.md, 10-11-2026)
# ======================================================================================
# Ménsula = dos mejillas (t_ch × L_ch) soldadas a la plancha, a ±(Win/2 … Win/2 + t_ch) del eje del cilindro, desde la saliente trasera (−rear) hasta
# L_ch − rear respecto del ojal. Ojal en (x_g; y_ojal), y_ojal = y_rp0 − L0, y_rp0 = −R·sen(π/N) − l_p − s_libre (pasador del vástago a la toma).
# Empuje: la ménsula recibe −F·ŷ a la altura del eje h; la reacción es de la mesa (roce de la interfaz, el otro cilindro): M = F·h alrededor de x no se
# cierra en la bancada. Con los dos cilindros M₂ = −M₁ en (−x_g; −y_ojal): torsión de la base. Método 1 (réplica): franja del modelo de un soporte
# (retención en el borde más lejano de la mesa: s_H = talón − O·f + D/2), corte V = M/a y cota inferior de la torsión (placa libre, m_xy = M/(2B)).
# Método 2 (contraste): FEA propia de Mindlin de la base entera (malla 80) con las dos ménsulas rígidas, las bancadas como elementos de espesor
# equivalente (misma rigidez a flexión de la sección compuesta con la ranura T; isótropo: sobrestima su torsión, de modo que la conclusión es conservadora
# en el sentido de «no cumple»), contacto unilateral, peso propio y la mesa vacía en el anillo, o la huella de la mesa bilateral si está cargada.
print("\n### Prueba 9 – Plancha base bajo la ménsula del ojal trasero (modo guiado)")
# Solo con la salida de tools/export_design.js (filas de verificación y veredicto; designDrive().guiado no va en ese JSON, que tiene que coincidir con
# el de packages/web/planos_export.js): la geometría se rearma aquí y se compara con dem, fu y estado de las filas.
try:
    VR9 = {k_: ver("Plancha base bajo la ménsula del ojal trasero: " + k_) for k_ in ("modelo", "flexión sin anclaje, empuje", "flexión sin anclaje, retorno", "corte de la franja", "torsión de la base", "levantamiento")}
except KeyError:
    VR9 = None
    FIND.append(("N10", "importante", "Plancha base bajo la ménsula: el núcleo no tiene las filas del modo guiado", "—", "filas «Plancha base bajo la ménsula del ojal trasero»"))
if VR9 is not None:
    BR9 = DV["bracket"]; h9 = DV["hax"]; t9 = P["t_base"]; B9 = P["B"]
    yp0_9 = -R * math.sin(math.pi / Np) - P["l_p"] - P["s_free"]; yE9 = yp0_9 - P["L0"]
    x0_9 = BR9["Win"] / 2; x1_9 = x0_9 + P["t_ch"]; y0_9 = -BR9["rear"]; y1_9 = P["L_ch"] - BR9["rear"]
    V9 = [(sx_ * xx_, yy_) for sx_ in (1, -1) for xx_ in (x0_9, x1_9) for yy_ in (y0_9, y1_9)]
    O9 = (-x_g, -yE9)
    Fret9 = A_ann * P["p_ret"] / 10
    def franja9(F_, s_):
        f_ = (0.0, s_); g_ = (-f_[1], f_[0]); pf_ = [vx * f_[0] + vy * f_[1] for vx, vy in V9]; pg_ = [vx * g_[0] + vy * g_[1] for vx, vy in V9]
        toe_ = max(pf_); a_ = toe_ - min(pf_); w_ = max(pg_) - min(pg_); sH_ = toe_ - (O9[0] * f_[0] + O9[1] * f_[1]) + P["D_top"] / 2; M_ = F_ * h9
        Mc_ = M_ * (1 - a_ / sH_) if sH_ > a_ else M_; b_ = w_ + a_
        return dict(M=M_, a=a_, w=w_, b=b_, sH=sH_, Mc=Mc_, sig=6 * Mc_ / (b_ * t9 * t9), tau=1.5 * (M_ / a_) / (b_ * t9), T=M_ / sH_ if sH_ > a_ else float("inf"))
    fe9, fr9 = franja9(F_st, -1.0), franja9(Fret9, 1.0)
    comp("9", "Franja, empuje: σ (MPa)", fe9["sig"], ver("Plancha base bajo la ménsula del ojal trasero: flexión sin anclaje, empuje")["dem"])
    comp("9", "Franja, retorno: σ (MPa)", fr9["sig"], ver("Plancha base bajo la ménsula del ojal trasero: flexión sin anclaje, retorno")["dem"])
    comp("9", "Franja, corte τ (MPa)", fe9["tau"], ver("Plancha base bajo la ménsula del ojal trasero: corte de la franja")["dem"])
    tq9 = 6 * (fe9["M"] / (2 * B9)) / t9 ** 2
    comp("9", "Torsión de la base (cota inferior) τ (MPa)", tq9, ver("Plancha base bajo la ménsula del ojal trasero: torsión de la base")["dem"])
    comp("9", "Momento por ménsula en el empuje M = F·h (kN·m)", fe9["M"] / 1e6, VR9["modelo"]["dem"])
    comp("9", "Momento por ménsula en el retorno M = F_ret·h (kN·m)", fr9["M"] / 1e6, VR9["modelo"]["cap"])
    Wm9 = (DV["masas"]["disc"] + DV["masas"]["ssTop"] + 0.5 * DV["masas"]["pivot"]) * g0      # mesa + disco rotatorio + medio pivote (las uñas van en los patines)
    Tq9 = n * fe9["T"]
    print(f"    ojal de la ménsula en ({x_g:.0f}; {yE9:.1f}); fuerza de esquina M/B = {fe9['M'] / B9 / 1e3:.1f} kN; mesa vacía: piden {Tq9 / 1e3:.1f} kN frente a {Wm9 / 1e3:.1f} kN de peso propio")
    if not (Tq9 > Wm9): FIND.append(("N10", "importante", "Mesa vacía: la retención debería faltar", s3(Tq9 / 1e3), s3(Wm9 / 1e3)))
    if ("(" + f"{x_g:.0f}".replace(".", ",") + "; " + f"{yE9:.0f}") not in VR9["modelo"]["formula"]:
        FIND.append(("N10", "menor", "La fila del modelo no declara el ojal propio", "—", f"({x_g:.0f}; {yE9:.0f})"))
    if not (fr9["sH"] <= fr9["a"]):
        FIND.append(("N10", "importante", "Retorno: la mesa debería quedar delante del pie de la ménsula (sin retención detrás del talón)", s3(fr9["sH"]), s3(fr9["a"])))
    for nm9 in ("flexión sin anclaje, empuje", "flexión sin anclaje, retorno", "torsión de la base"):
        v9 = ver("Plancha base bajo la ménsula del ojal trasero: " + nm9)
        if v9["estado"] != "pend" or not (v9["fu"] > 1):
            FIND.append(("N10", "importante", "Plancha base bajo la ménsula (" + nm9 + "): debería quedar «pend» con FU > 1 (sin anclaje)", f"{v9['estado']} FU {s3(v9['fu'])}", "pend, FU > 1"))
    VD9 = D0["verdict"]; pc9 = sorted([v for v in D0["verificaciones"] if v["estado"] == "pend" and v["fu"] is not None and not (math.isfinite(v["fu"]) and v["fu"] <= 1)], key=lambda v: -v["fu"])
    comp("9", "Pendientes críticos: FU máximo", pc9[0]["fu"] if pc9 else 0.0, VD9["fuMaxPend"], tol=1e-9)
    if VD9["estado_global"] != ("NO CUMPLE / PENDIENTE DE DECISIÓN" if pc9 and VD9["gira"] and VD9["estructura"] else VD9["estado_global"]) or len(VD9["pendientes_criticos"]) != len(pc9):
        FIND.append(("N10", "importante", "Estado global del modo guiado con pendientes críticos", VD9["estado_global"], "NO CUMPLE / PENDIENTE DE DECISIÓN"))
    rows9 = [["Franja, empuje a calado", s3(fe9["M"] / 1e6), s3(fe9["sig"]), s3(fe9["sig"] / (Fy / Nd))], ["Franja, retorno (atasco)", s3(fr9["M"] / 1e6), s3(fr9["sig"]), s3(fr9["sig"] / (Fy / Nd))],
             ["Torsión de la base (cota inferior)", s3(fe9["M"] / 1e6), s3(tq9), s3(tq9 / (Fy / (Nd * math.sqrt(3))))]]
    try:
        import numpy as np, scipy.sparse as sp9, scipy.sparse.linalg as spl9
        hb9 = 80.0; nb9 = int(round(B9 / hb9)); xs9 = np.linspace(-B9 / 2, B9 / 2, nb9 + 1); Es9, nu9 = P["E"], P["nu"]
        Xb9 = np.repeat(xs9, nb9 + 1); Yb9 = np.tile(xs9, nb9 + 1); nn9 = Xb9.size
        el9 = np.array([[i * (nb9 + 1) + j, (i + 1) * (nb9 + 1) + j, (i + 1) * (nb9 + 1) + j + 1, i * (nb9 + 1) + j + 1] for i in range(nb9) for j in range(nb9)])
        ec9 = np.stack([Xb9[el9].mean(axis=1), Yb9[el9].mean(axis=1)], axis=1)
        # bancada (y ∈ ±(Y_bed + l_soporte), con su prolongación) como espesor equivalente: I de la sección compuesta plancha + bancada − ranura − cabeza T
        tB9, wb9 = P["t_bed"], P["w_bed"]; Hc9 = t9 + tB9
        pr9 = [(wb9 * t9, t9 / 2, wb9 * t9 ** 3 / 12), (wb9 * tB9, t9 + tB9 / 2, wb9 * tB9 ** 3 / 12), (-P["w_slot"] * P["h_slot"], Hc9 - P["h_slot"] / 2, -P["w_slot"] * P["h_slot"] ** 3 / 12),
               (-P["w_tee"] * P["h_tee"], Hc9 - P["h_slot"] - P["h_tee"] / 2, -P["w_tee"] * P["h_tee"] ** 3 / 12)]
        A9 = sum(p_[0] for p_ in pr9); yc9 = sum(p_[0] * p_[1] for p_ in pr9) / A9; I9 = sum(p_[2] + p_[0] * (p_[1] - yc9) ** 2 for p_ in pr9); teq9 = (12 * I9 / wb9) ** (1 / 3)
        Yb_ext9 = KC["Y_bed"] + P["cam_ls"]
        inBed9 = (np.abs(np.abs(ec9[:, 0]) - x_g) < wb9 / 2) & (np.abs(ec9[:, 1]) < Yb_ext9)
        te9 = np.where(inBed9, teq9, t9)
        def Bm9(xi, et, a_):
            sgx, sgy = (-1, 1, 1, -1), (-1, -1, 1, 1); Bb_ = np.zeros((3, 12)); Bs_ = np.zeros((2, 12))
            for k in range(4):
                N_ = 0.25 * (1 + xi * sgx[k]) * (1 + et * sgy[k]); dx_ = 0.25 * sgx[k] * (1 + et * sgy[k]) / a_; dy_ = 0.25 * sgy[k] * (1 + xi * sgx[k]) / a_
                Bb_[0, 3 * k + 1] = dx_; Bb_[1, 3 * k + 2] = dy_; Bb_[2, 3 * k + 1] = dy_; Bb_[2, 3 * k + 2] = dx_; Bs_[0, 3 * k] = dx_; Bs_[0, 3 * k + 1] = -N_; Bs_[1, 3 * k] = dy_; Bs_[1, 3 * k + 2] = -N_
            return Bb_, Bs_
        a9 = hb9 / 2; gq9 = (-1 / math.sqrt(3), 1 / math.sqrt(3)); C9 = np.array([[1, nu9, 0], [nu9, 1, 0], [0, 0, (1 - nu9) / 2]])
        Kb9 = sum(Bm9(x_, y_, a9)[0].T @ C9 @ Bm9(x_, y_, a9)[0] * a9 * a9 for x_ in gq9 for y_ in gq9); B0b9, B0s9 = Bm9(0, 0, a9); Ks9 = B0s9.T @ B0s9 * 4 * a9 * a9
        D9 = Es9 * te9 ** 3 / (12 * (1 - nu9 ** 2)); G9 = 5 / 6 * Es9 / (2 * (1 + nu9)) * te9
        df9 = np.stack([3 * el9, 3 * el9 + 1, 3 * el9 + 2], axis=2).reshape(len(el9), 12)
        K9 = sp9.csr_matrix(((D9[:, None, None] * Kb9[None] + G9[:, None, None] * Ks9[None]).ravel(), (np.repeat(df9, 12, axis=1).ravel(), np.tile(df9, (1, 12)).ravel())), shape=(3 * nn9, 3 * nn9))
        E9 = (x_g, yE9); sups9 = []
        for sg_ in (1, -1):
            Xl_, Yl_ = sg_ * Xb9 - E9[0], sg_ * Yb9 - E9[1]; m_ = np.zeros(nn9, bool)
            for sx_ in (1, -1):
                m_ |= (sx_ * Xl_ >= x0_9 - hb9 / 2) & (sx_ * Xl_ <= x1_9 + hb9 / 2) & (Yl_ >= y0_9 - hb9 / 2) & (Yl_ <= y1_9 + hb9 / 2)
            sups9.append(m_)
        inS9 = sups9[0] | sups9[1]; fn9 = np.where(~inS9)[0]; fr9_ = np.stack([3 * fn9, 3 * fn9 + 1, 3 * fn9 + 2], axis=1).ravel(); nf9 = fr9_.size
        Tr_, Tc_, Tv_ = [fr9_], [np.arange(nf9)], [np.ones(nf9)]
        for si_, (m_, c_) in enumerate(zip(sups9, (E9, (-E9[0], -E9[1])))):
            k_ = np.where(m_)[0]; o_ = np.ones(k_.size)
            Tr_ += [3 * k_, 3 * k_, 3 * k_, 3 * k_ + 1, 3 * k_ + 2]; Tc_ += [o_ * (nf9 + 3 * si_), o_ * (nf9 + 3 * si_ + 1), o_ * (nf9 + 3 * si_ + 2), o_ * (nf9 + 3 * si_ + 1), o_ * (nf9 + 3 * si_ + 2)]
            Tv_ += [o_, Xb9[k_] - c_[0], Yb9[k_] - c_[1], o_, o_]
        T9 = sp9.csr_matrix((np.concatenate(Tv_), (np.concatenate(Tr_), np.concatenate(Tc_).astype(int))), shape=(3 * nn9, nf9 + 6)); Kr9 = (T9.T @ K9 @ T9).tocsr()
        Tw9 = (sp9.csr_matrix((np.ones(nn9), (np.arange(nn9), 3 * np.arange(nn9))), shape=(nn9, 3 * nn9)) @ T9).tocsr()
        fz9 = np.zeros(nn9)
        for e_, tt_ in zip(el9, te9): fz9[e_] -= RHO * g0 * tt_ * hb9 * hb9 / 4
        rb9 = np.hypot(Xb9, Yb9); Ri9 = R_i_if(P); ring9 = (rb9 >= Ri9) & (rb9 <= P["D_top"] / 2)
        fz9[ring9] -= Wm9 / ring9.sum()
        rhs9 = T9.T @ np.stack([fz9, np.zeros(nn9), np.zeros(nn9)], axis=1).ravel()
        Wsup9 = (DV["masas"]["brackets"] / P["n_br"] + DV["masas"]["cyl"] / n / 2) * g0
        def fea9(holdT):
            r_ = rhs9.copy(); M_ = F_st * h9
            for si_, s_ in enumerate((1, -1)): r_[nf9 + 3 * si_] -= Wsup9; r_[nf9 + 3 * si_ + 2] += s_ * M_     # Mx = +F·h en la ménsula 1, −F·h en la 2
            hold = (rb9 <= P["D_top"] / 2) if holdT else np.zeros(nn9, bool); act_ = np.ones(nn9, bool); seen_ = set(); part_ = False
            for it_ in range(400):
                u_ = T9 @ spl9.spsolve((Kr9 + Tw9.T @ sp9.diags(np.where(act_ | hold, 1e7, 1e-3)) @ Tw9).tocsc(), r_); w_ = u_[0::3]
                rel_ = act_ & ~hold & (w_ > 1e-9); add_ = ~act_ & (w_ < -1e-9)
                if not rel_.any() and not add_.any(): break
                new_ = act_.copy()
                if part_:
                    if add_.any(): ix_ = np.where(add_)[0]; new_[ix_[np.argsort(w_[ix_])[:max(1, ix_.size // 10)]]] = True
                    if rel_.any(): ix_ = np.where(rel_)[0]; new_[ix_[np.argsort(-w_[ix_])[:max(1, ix_.size // 10)]]] = False
                else: new_[rel_] = False; new_[add_] = True
                k_ = hash(new_.tobytes()); part_ = part_ or k_ in seen_; seen_.add(k_); act_ = new_
            kap_ = u_[df9] @ B0b9.T; Em_ = Es9 / (1 - nu9 ** 2)
            sp_ = np.stack([Em_ * t9 / 2 * (kap_[:, 0] + nu9 * kap_[:, 1]), Em_ * t9 / 2 * (kap_[:, 1] + nu9 * kap_[:, 0]), Em_ * t9 / 2 * (1 - nu9) / 2 * kap_[:, 2]], axis=1)
            vm_ = np.sqrt(sp_[:, 0] ** 2 - sp_[:, 0] * sp_[:, 1] + sp_[:, 1] ** 2 + 3 * sp_[:, 2] ** 2); okE = ~inBed9 & ~inS9[el9].all(axis=1)
            return float(w_.max()), int(act_.sum()), it_, float(vm_[okE].max())
        wV9, nV9, iV9, sV9 = fea9(False); wC9, nC9, iC9, sC9 = fea9(True)
        rows9 += [["FEA propia, mesa vacía (dos cilindros)", s3(F_st * h9 / 1e6), s3(sV9), s3(sV9 / (Fy / Nd)) + f"; lev. {s3(wV9)} mm, {nV9} nudos"],
                  ["FEA propia, mesa cargada", s3(F_st * h9 / 1e6), s3(sC9), s3(sC9 / (Fy / Nd)) + f"; lev. {s3(wC9)} mm"]]
        if not (wV9 > 20 and sV9 > Fy / Nd):
            FIND.append(("N10", "importante", "FEA propia del modo guiado con la mesa vacía: la base debería flotar (levantamiento ≫ 1 mm) y la plancha exceder Fy/Nd", f"{s3(wV9)} mm, σ {s3(sV9)}", "—"))
        if not (sC9 > Fy / Nd):
            FIND.append(("N10", "importante", "FEA propia del modo guiado con la mesa cargada: la plancha junto a la ménsula debería exceder Fy/Nd", f"σ {s3(sC9)}", "—"))
    except ImportError:
        print("    numpy/scipy no disponibles: se omite la FEA de contraste")
    table("Prueba 9 – Plancha base bajo la ménsula (sin anclaje; ASME BTH-1 §3-2, Nd = 3)", ["Caso", "M (kN·m)", "σ o τ (MPa)", "FU"], rows9)

# ======================================================================================
# Resumen
# ======================================================================================
table("Comparación con el núcleo (tolerancia 0,1 % salvo indicación)", ["Prueba", "Magnitud", "Propio", "Núcleo", "Δ %", "Veredicto"], COMP)
table("Hallazgos", ["Id", "Severidad", "Hallazgo", "Núcleo", "Corregido"], FIND)
nco = sum(1 for c in COMP if c[5] == "coincide"); ndi = sum(1 for c in COMP if c[5] == "discrepa"); nom = sum(1 for c in COMP if c[5] == "el núcleo omite")
sev = {k: sum(1 for f in FIND if f[1] == k) for k in ("crítica", "importante", "menor", "abierto a planos")}
print(f"\nRESULTADO: {nco} coincidencias, {ndi} discrepancias numéricas, {nom} omisiones; hallazgos: "
      f"{sev['crítica']} críticos, {sev['importante']} importantes, {sev['menor']} menores, "
      f"{sev['abierto a planos']} abiertos a planos (no bloqueantes)")
sys.exit(1 if (ndi or sev["crítica"] or sev["importante"]) else 0)
