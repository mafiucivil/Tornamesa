"""Revisión independiente del ACCIONAMIENTO TT300-C (cilindro – patín guiado – uña – pasador).

Regla de independencia: no lee packages/core ni packages/agents. Los resultados del núcleo se obtienen
solo por su salida JSON (node tools/export_design.js [params.json]); todo lo demás se deriva aquí desde
la estática, la cinemática y ASME BTH-1 Cat. B (Fy/Nd; corte Fy/(Nd·√3); aplastamiento 1,25Fy/Nd;
soldadura 0,60FEXX/(1,20Nd)).

Ejecutar desde la raíz del repositorio:  python3 -I tests/indep_accionamiento.py
Imprime tablas por prueba y termina con una línea «RESULTADO: ...». Código de salida 1 si hay
hallazgos críticos o importantes (el script es un verificador, no un generador de diseño).

Convenciones (giro antihorario, cilindro del lado x = +x_g, empuje +y; el otro cilindro es simétrico
respecto del centro y el giro horario es la imagen especular, con los mismos módulos):
  θ ∈ [−π/N, +π/N]   posición angular del pasador tomado;  a = R cos θ, y_p = R sin θ
  Δ = x_g − a        excentricidad en planta del empuje del pasador respecto del eje del cilindro
  Patín: origen en el pasador del vástago, +y hacia adelante; L_s = l_p + 20 + 1,25 d_pp, Lg = 2/3 L_s
  Uña: origen en el centro del asiento (= centro del pasador; cara de empuje en y = 0, cuerpo y ∈ [−b, 0]).
Unidades: N, mm, MPa (se imprimen kN y kN·m donde corresponde).
"""
import json, math, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLD = ROOT / "tests" / "golden"
g0, RHO = 9.80665, 7.85e-6


def export(over=None):
    """Resultados del núcleo vía JSON (única interfaz permitida)."""
    with tempfile.TemporaryDirectory() as td:
        args = ["node", str(ROOT / "tools" / "export_design.js")]
        if over:
            f = pathlib.Path(td) / "p.json"
            f.write_text(json.dumps(over))
            args.append(str(f))
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def s3(x):
    """3 cifras significativas."""
    if x is None:
        return "—"
    if isinstance(x, str):
        return x
    if x == 0 or not math.isfinite(x):
        return f"{x:g}"
    return f"{x:.{max(0, 2 - int(math.floor(math.log10(abs(x)))))}f}" if abs(x) >= 1e-3 else f"{x:.3g}"


def table(title, head, rows):
    print(f"\n### {title}")
    w = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(head)]
    print("| " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(head)) + " |")
    print("|" + "|".join("-" * (x + 2) for x in w) + "|")
    for r in rows:
        print("| " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) + " |")


COMP = []      # (prueba, magnitud, propio, núcleo, Δ%, veredicto)
FIND = []      # (id, severidad, título, valor núcleo, valor corregido)


def comp(prueba, name, mine, core, tol=1e-3):
    if core is None:
        COMP.append((prueba, name, s3(mine), "—", "—", "el núcleo omite"))
        return
    d = (mine - core) / core * 100 if core else 0.0
    COMP.append((prueba, name, s3(mine), s3(core), f"{d:+.2f}", "coincide" if abs(d) <= tol * 100 else "discrepa"))


# ======================================================================================
# 0. Datos
# ======================================================================================
D0 = export()
if D0 is None:
    print("No se pudo ejecutar node tools/export_design.js"); sys.exit(2)
P = D0["P"]
Pg = json.loads((GOLD / "params_defaults.json").read_text())
dif = sorted(k for k in set(P) | set(Pg) if P.get(k) != Pg.get(k))
DV, KC = D0["derivados"], D0["derivados"]["K"]
VER = {v["nombre"]: v for v in D0["verificaciones"]}
def ver(sub):
    for k, v in VER.items():
        if sub in k:
            return v
    return None

R, Np, r_p, n = P["R_pin"], int(P["N_pin"]), P["d_pin"] / 2, P["n_cyl"]
ph = math.pi / Np
a_min = R * math.cos(ph)
x_g, eta, mu_g = P["x_g"], P["eta_c"], P["mu_g"]
front, rear = P["l_p"] + 20, 1.25 * P["d_pp"]
L_s = front + rear; Lg = 2 / 3 * L_s
y_mid = (front - rear) / 2; y_f, y_r = y_mid + Lg / 2, y_mid - Lg / 2
y_c = P["l_p"]
mouthX = min(x_g - P["w_s"] / 2, R + r_p + 10)
tipX = a_min - P["c_tip"]
b, h_d, L_in = P["dog_b"], P["dog_h"], P["L_in"]
R_seat = r_p + 1                                     # asiento R51 (planos F-03 / D-01)
A_b = math.pi / 4 * P["D_bore"] ** 2
A_ann = A_b - math.pi / 4 * P["d_rod"] ** 2
F_st = A_b * P["p_relief"] / 10                      # N (bar → MPa = /10)
Nd, Fy = P["Nd"], P["Fy"]
Fb = 1.25 * Fy / Nd                                  # aplastamiento BTH-1 (registro del proyecto)
m_shoe = DV["masas"]["shoes"] / n; m_cyl = DV["masas"]["cyl"] / n
W_shoe, W_cyl = m_shoe * g0, m_cyl * g0
F_sp = 300.0                                         # resorte pos 12: 150–300 N (F-03) → cota superior
mu_p = mu_g                                          # μ uña–alojamiento (mismo par acero/grasa que la guía)
mu_s = mu_g                                          # μ pasador–asiento


# --- par resistente desde primeros principios (mismo enunciado que indep_tt300c.py) ---
def masa_mesa(P):
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
    m_piv = RHO * math.pi / 4 * P["D_piv"] ** 2 * (P["t_base"] + P["h_disc"] - P["t_top"] + 3)
    return m + 0.5 * m_piv


def par(P, mu, r):
    """T [N·mm] = μ·N·r + μ_buje·H_exc·D/2 (H_exc = μN·e·(4/3)(Ro³−Ri³)/(Ro⁴−Ri⁴))."""
    Nn = P["W_tf"] * g0 * 1e3 + masa_mesa(P) * g0
    Ro, Ri = P["D_top"] / 2, P["D_piv"] / 2 + 15
    H = mu * Nn * P["e"] * 4 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 4 - Ri ** 4)
    return mu * Nn * r + P["mu_bush"] * H * P["D_piv"] / 2


def casos(P):
    Ro, Ri = P["D_top"] / 2, P["D_piv"] / 2 + 15
    ru = 2 / 3 * (Ro ** 3 - Ri ** 3) / (Ro ** 2 - Ri ** 2)
    return {"nom": (P["mu_nom"], ru), "dis": (P["mu_d"], P["r_ef"]), "borde": (P["mu_d"], Ro),
            "cont": (P["mu_cont"], P["r_ef"]), "seco": (P["mu_dry"], ru)}


# ======================================================================================
# Modelo de equilibrio del conjunto pasador – uña – patín (plano x–y)
# ======================================================================================
def dog_solve(s, mu, xm, Lin, Fsp, known=(), Mk=0.0, unk=((1.0, 0.0), (0.0, 0.0))):
    """Uña rígida en el alojamiento, contactos en la boca (x = xm) y en el extremo (x = xm + Lin).
    Cada contacto puede apoyar en la pared trasera (y = −b, N > 0 empuja +y) o en la delantera (y = 0, N < 0).
    Fricción −s·μ·|N| en x (s = signo de la velocidad radial de la uña, +1 hacia afuera).
    known: cargas conocidas (fx, fy, x, y); Mk: par conocido (antihorario +); resorte (−Fsp, 0) en (xm+Lin, −b/2).
    unk: ((ux, uy), (xq, yq)) dirección y punto de la fuerza incógnita Q.
    Devuelve (Q, N1, N2) consistente con los signos supuestos."""
    (ux, uy), (xq, yq) = unk
    kn = list(known) + [(-Fsp, 0.0, xm + Lin, -b / 2)]
    SFx = sum(k[0] for k in kn); SFy = sum(k[1] for k in kn)
    SM = sum(k[2] * k[1] - k[3] * k[0] for k in kn) + Mk
    xs = (xm, xm + Lin)
    def det(M):
        return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
                + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))
    for sg in ((1, -1), (1, 1), (-1, 1), (-1, -1)):
        ys = [(-b if q > 0 else 0.0) for q in sg]
        A = [[ux, -s * mu * sg[0], -s * mu * sg[1]],
             [uy, 1.0, 1.0],
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
        Q, N1, N2 = sol
        if N1 * sg[0] >= -1e-9 and N2 * sg[1] >= -1e-9:
            return Q, N1, N2
    return None


def uña_fbd(F, _unused, xm, Lin, s, mu, Ms, Fsp):
    """Arrastre radial de la uña por el asiento: carga (Hx, −F) en el centro del asiento + par Ms.
    Devuelve (Hx necesario, N1, N2)."""
    r = dog_solve(s, mu, xm, Lin, Fsp, known=[(0.0, -F, 0.0, 0.0)], Mk=Ms)
    return r


def estado(theta, Tn, modelo="nucleo", mu_pp=None, mu_ss=None, mu_gg=None, Fsp=F_sp, kpinch=None):
    """Equilibrio cuasiestático en la posición θ para un par por cilindro Tn = T/n.
    modelo: 'nucleo' (sin fricción uña–pasador ni uña–alojamiento),
            'asiento' (asiento R51 conforme: la uña sigue al pasador en x y desliza en el alojamiento),
            'plana' (cara plana normal a y: el pasador desliza sobre la cara, la uña no se mueve)."""
    mu_pp = mu_p if mu_pp is None else mu_pp
    mu_ss = mu_s if mu_ss is None else mu_ss
    mu_gg = mu_g if mu_gg is None else mu_gg
    a, yp = R * math.cos(theta), R * math.sin(theta)
    Dl = x_g - a
    s = 1 if yp < 0 else -1                          # ẋ_pasador = −y_p·ω (antihorario, lado +x)
    xm, Lin = mouthX - a, L_in + (a - a_min)
    if modelo == "nucleo":
        F = Tn / a; Ms = 0.0; Hval = 0.0; N1 = F * (xm + Lin) / Lin; N2 = F * xm / Lin
    elif modelo in ("asiento", "borde"):
        # 'asiento': contacto siempre en el arco, línea por el centro del pasador + par de fricción Ms.
        # 'borde'  : en la 2.ª mitad (uña entrando) la resultante se inclina más allá del borde del asiento
        #            (ψ = −asin(c_tip/R51)); el contacto pasa al borde E, sin par adicional.
        Ms_F = mu_ss * 4 / math.pi * r_p
        dE = math.sqrt(R_seat ** 2 - P["c_tip"] ** 2)
        edge = (modelo == "borde" and s < 0)
        xE, yE = ((-P["c_tip"], -dE) if edge else (0.0, 0.0))
        F = Tn / a
        for _ in range(60):                           # punto fijo: momento sobre la mesa = Tn
            Ms = 0.0 if edge else Ms_F * F
            if kpinch is not None:                    # sensibilidad: ΣN = kpinch·F (reparto elástico lineal)
                Hval, N1, N2 = s * mu_pp * kpinch * F + Fsp, None, None
            elif edge:
                Hval, N1, N2 = dog_solve(s, mu_pp, xm, Lin, Fsp, known=[(0.0, -F, xE, yE)], Mk=0.0, unk=((1.0, 0.0), (xE, yE)))
            else:
                Hval, N1, N2 = uña_fbd(F, 0, xm, Lin, s, mu_pp, Ms, Fsp)
            # fuerza sobre el pasador (−Hx, F) en (a + xE, y_p + yE):  (a + xE) F + (y_p + yE) Hx − Ms = Tn
            Fn = (Tn - (yp + yE) * Hval + Ms) / (a + xE)
            if abs(Fn - F) < 1e-9 * Tn / a:
                F = Fn; break
            F = Fn
        Ms = 0.0 if edge else Ms_F * F
    elif modelo == "plana":
        sg = 1 if (r_p - yp) > 0 else -1             # deslizamiento del pasador sobre la cara
        al = mu_ss * sg
        # contacto en (a, y_p − r): a F + (y_p − r) Hx = Tn
        F = Tn / (a + (yp - r_p) * al)
        Hval = al * F; Ms = 0.0
        N1 = F * (xm + L_in) / L_in; N2 = F * xm / L_in
    if modelo not in ("asiento", "borde"):
        xE, yE = 0.0, 0.0
    Rf = (F * (Dl - xE) + Ms - (y_c + yE - y_r) * Hval) / Lg
    Rr = -Hval - Rf
    Frod = F + mu_gg * (abs(Rf) + abs(Rr))
    Fh = Frod / eta
    return dict(th=theta, a=a, yp=yp, Dl=Dl, s=s, F=F, Hx=Hval, Ms=Ms, Rf=Rf, Rr=Rr, Frod=Frod, Fh=Fh,
                N1=N1, N2=N2, xm=xm, Lin=Lin)


def barrido(Tn, modelo, npts=401, **kw):
    out = [estado(-ph + 2 * ph * i / (npts - 1), Tn, modelo, **kw) for i in range(npts)]
    # en θ = 0 se evalúan ambos sentidos de la fricción radial
    return out


def Fmax(Tn, modelo, **kw):
    return max(barrido(Tn, modelo, **kw), key=lambda e: e["Fh"])


MOD = "borde"                                        # modelo principal (contacto en el borde del asiento en la 2.ª mitad)
cs = casos(P)
mu_d, r_ef = cs["dis"]
T_d = par(P, mu_d, r_ef)
Tn_d = T_d / n

print("# Revisión independiente del accionamiento TT300-C (patín – uña – pasador)")
print(f"Parámetros del núcleo = golden salvo: {dif if dif else 'ninguno'} (p_rated falta en params_defaults.json; no interviene aquí)")
print(f"R = {R}, N = {Np}, a_min = {s3(a_min)} mm, x_g = {x_g}, L_s = {s3(L_s)}, Lg = {s3(Lg)}, y_f = {s3(y_f)}, y_r = {s3(y_r)}, "
      f"boca x = {s3(mouthX)}, punta x = {s3(tipX)}, μp = μs = μg = {mu_g}, F_calado = {s3(F_st/1e3)} kN")

# ======================================================================================
# PRUEBA 1 – Equilibrio en el plano en 5 posiciones
# ======================================================================================
pos = [(-ph, "Inicio θ=−π/N"), (-ph / 2, "1/4"), (-1e-9, "Centro (1.ª mitad)"), (1e-9, "Centro (2.ª mitad)"), (ph / 2, "3/4"), (ph, "Final θ=+π/N")]
rows = []
car = {c["pos"]: c for c in D0["carrera"]}
for th, lab in pos:
    e0 = estado(th, Tn_d, "nucleo"); e1 = estado(th, Tn_d, MOD); e3 = estado(th, Tn_d, "asiento"); e2 = estado(th, Tn_d, "plana")
    rows.append([lab, s3(math.degrees(th)), s3(e0["F"] / 1e3), s3(e0["Fh"] / 1e3), s3(e0["Rf"] / 1e3),
                 s3(e1["F"] / 1e3), s3(e1["Hx"] / 1e3), s3(e1["Rf"] / 1e3), s3(e1["Rr"] / 1e3), s3(e1["Fh"] / 1e3),
                 f"{(e1['Fh'] / e0['Fh'] - 1) * 100:+.1f}", s3(e3["Fh"] / 1e3), f"{(e3['Fh'] / e0['Fh'] - 1) * 100:+.1f}",
                 s3(e2["Fh"] / 1e3), f"{(e2['Fh'] / e0['Fh'] - 1) * 100:+.1f}"])
table("Prueba 1 – Equilibrio cuasiestático (caso de diseño μ=0,20, r=0,80 m), kN. A = asiento R51 (planos), contacto en el borde en la 2.ª mitad; "
      "A' = ídem con la resultante por el centro del pasador + par Ms; P = cara plana",
      ["Posición", "θ°", "F_pas núcleo", "F_cil núcleo", "R_f núcleo", "F_pas A", "H_x A", "R_f A", "R_r A",
       "F_cil A", "Δ%", "F_cil A'", "Δ%", "F_cil P", "Δ%"], rows)
for th, key in [(-ph, "Inicio (toma)"), (0.0, "Centro"), (ph, "Final")]:
    e0 = estado(th, Tn_d, "nucleo"); c = car[key]
    comp("1", f"F_cil {key} (modelo del núcleo)", e0["Fh"] / 1e3, c["F"])
    comp("1", f"F_pas {key}", e0["F"] / 1e3, c["Fpin"])
    comp("1", f"R_guía {key} = F_pas·Δ/Lg", e0["Rf"] / 1e3, c["Rg"])
    comp("1", f"F_r = F_pas·sinθ {key} (va al pivote, se anula en el par)", e0["F"] * math.sin(th) / 1e3, c["Fr"])
K0 = (1 + 2 * mu_g * (x_g - a_min) / Lg) / eta
comp("1", "K = (1+2μgΔ/Lg)/η", K0, DV["Kguide"])
eA = Fmax(Tn_d, MOD); eA2 = Fmax(Tn_d, "asiento"); eP = Fmax(Tn_d, "plana"); eN = Fmax(Tn_d, "nucleo")
eK = Fmax(Tn_d, "asiento", kpinch=None)
eE = Fmax(Tn_d, "asiento", kpinch=3.55)
comp("1", "F_cil máx. en la carrera, asiento R51 (A, kN)", eA["Fh"] / 1e3, DV["casos"][1]["F"])
comp("1", "F_cil máx. en la carrera, asiento R51 (A', kN)", eA2["Fh"] / 1e3, DV["casos"][1]["F"])
comp("1", "F_cil máx., cara plana (kN)", eP["Fh"] / 1e3, DV["casos"][1]["F"])
comp("1", "K equivalente con asiento = F_máx·n·a_min/T", eA["Fh"] * a_min / Tn_d, DV["Kguide"])
print(f"\nF_cil máx: núcleo {s3(eN['Fh']/1e3)} kN (θ={s3(math.degrees(eN['th']))}°); A' {s3(eA2['Fh']/1e3)} kN; A {s3(eA['Fh']/1e3)} kN (θ={s3(math.degrees(eA['th']))}°, "
      f"H/F={s3(eA['Hx']/eA['F'])}); asiento con ΣN elástico 3,55F {s3(eE['Fh']/1e3)} kN; cara plana {s3(eP['Fh']/1e3)} kN (θ={s3(math.degrees(eP['th']))}°)")
FS_core = F_st / 1e3 / DV["casos"][1]["F"]
FS_A = F_st / eA["Fh"]; FS_A2 = F_st / eA2["Fh"]; FS_P = F_st / eP["Fh"]
FIND.append(("H1", "crítica", "Fricción radial de la uña en el alojamiento: el asiento R51 obliga a la uña a seguir los 5,85 mm radiales del pasador (ΣN ≈ 3F en el alojamiento); el núcleo la omite",
             f"FS diseño {s3(FS_core)} ≥ 1,25", f"FS diseño {s3(FS_A)}–{s3(FS_A2)} < 1,25 (cara plana: {s3(FS_P)})"))

# signos de las reacciones de guía
e_ini, e_fin = estado(-ph, Tn_d, MOD), estado(ph, Tn_d, MOD)
table("Prueba 1(c) – Signo y punto de aplicación de las reacciones de guía (kN; +x = hacia afuera de la mesa)",
      ["Modelo / posición", "R_f en y=" + s3(y_f), "R_r en y=" + s3(y_r), "Σ|R|", "fricción μgΣ|R|"],
      [["núcleo (extremo de carrera)", s3(estado(ph, Tn_d)["Rf"] / 1e3), s3(estado(ph, Tn_d)["Rr"] / 1e3),
        s3((abs(estado(ph, Tn_d)["Rf"]) + abs(estado(ph, Tn_d)["Rr"])) / 1e3), s3(mu_g * 2 * estado(ph, Tn_d)["Rf"] / 1e3)],
       ["A, inicio (uña sale)", s3(e_ini["Rf"] / 1e3), s3(e_ini["Rr"] / 1e3), s3((abs(e_ini["Rf"]) + abs(e_ini["Rr"])) / 1e3), s3(mu_g * (abs(e_ini["Rf"]) + abs(e_ini["Rr"])) / 1e3)],
       ["A, final (uña entra, contacto en E)", s3(e_fin["Rf"] / 1e3), s3(e_fin["Rr"] / 1e3), s3((abs(e_fin["Rf"]) + abs(e_fin["Rr"])) / 1e3), s3(mu_g * (abs(e_fin["Rf"]) + abs(e_fin["Rr"])) / 1e3)]])

# ======================================================================================
# PRUEBA 3 – Trabajos virtuales: W_hidráulico = W_útil + pérdidas (integración en la carrera)
# ======================================================================================
def energia(modelo, Tn, npts=4001, **kw):
    W = dict(hyd=0, util=0, seal=0, guide=0, pocket=0, seat=0, face=0, spring=0)
    dth = 2 * ph / (npts - 1)
    for i in range(npts - 1):
        th = -ph + (i + 0.5) * dth
        e = estado(th, Tn, modelo, **kw)
        ds = e["a"] * dth
        W["hyd"] += e["Fh"] * ds
        W["util"] += Tn * dth
        W["seal"] += (1 - eta) * e["Fh"] * ds
        W["guide"] += mu_g * (abs(e["Rf"]) + abs(e["Rr"])) * ds
        dx = abs(e["yp"]) * dth
        if modelo == "asiento":
            W["pocket"] += (abs(e["Hx"] - F_sp)) * dx
            W["seat"] += e["Ms"] * dth
            W["spring"] += F_sp * (-e["s"]) * dx * -1      # trabajo neto sobre el resorte (≈ 0)
        if modelo == "plana":
            W["face"] += abs(e["Hx"]) * abs(r_p - e["yp"]) * dth
    return W


rows = []
chord = 2 * R * math.sin(ph)
for mod in ("nucleo", "asiento", "plana"):
    W = energia(mod, Tn_d)
    loss = W["util"] + W["seal"] + W["guide"] + W["pocket"] + W["seat"] + W["face"] + W["spring"]
    rows.append([mod, s3(W["hyd"] / 1e6), s3(W["util"] / 1e6), s3(W["seal"] / 1e6), s3(W["guide"] / 1e6), s3((W["pocket"] + W["seat"] + W["face"]) / 1e6),
                 f"{(W['hyd'] - loss) / W['hyd'] * 100:+.4f}", s3(W["hyd"] / chord / 1e3), s3(W["util"] / W["hyd"])])
    if mod == "nucleo":
        Wn = W
table("Prueba 3 – Balance de trabajo en una carrera de toma (kJ; F media = W/cuerda)",
      ["Modelo", "W hidráulico", "W útil T·2π/(nN)", "sellos", "guía", "uña/asiento/cara", "cierre %", "F media kN", "rendimiento"], rows)
comp("3", "W hidráulico = (T/n)·∫K dθ (modelo núcleo) vs W útil + pérdidas", Wn["hyd"] / 1e6, (Wn["util"] + Wn["seal"] + Wn["guide"]) / 1e6)

# ======================================================================================
# PRUEBA 2 – Equilibrio fuera del plano (y–z y x–z)
# ======================================================================================
tb = P["t_base"]
z_c = tb + P["h_disc"] / 2                           # eje del cilindro = centro de la uña = centro de la luz del pasador
z_dog = tb + P["h_disc"] / 2
h_t = P["h_slot"] - 2                                # lengüeta dibujada con 2 mm de fondo libre (D-01 detalle B)
z_t = tb + P["t_bed"] - h_t / 2
dz = z_c - z_t
comp("2", "Altura del eje del cilindro z_c (mm)", z_c, KC["zc0"])
e_d = estado(ph, Tn_d, "nucleo")
Mx = (e_d["Frod"] - e_d["F"]) * dz                   # cabeceo
Mx_cal = (F_st * eta - F_st * eta / K0 / eta) * dz   # a calado, con F_pas = F_st·η/K·... (fricción de guía viva)
Mx_cal = F_st * eta * (1 - 1 / (K0 * eta)) * dz
rest_p = W_shoe * (front - y_mid) + W_cyl / 2 * front
V_rear = (Mx - rest_p) / L_s
V_rear_cal = (Mx_cal - rest_p) / L_s
eAf = estado(ph, Tn_d, MOD)
My = abs(eAf["Hx"]) * dz                             # balanceo
rest_r = (W_shoe + W_cyl / 2) * P["w_bed"] / 2
H_cal = abs(estado(ph, F_st * a_min, MOD)["Hx"]) * F_st / estado(ph, F_st * a_min, MOD)["F"]
My_cal = H_cal * dz
lev_gib = P["w_bed"] / 2 + P["w_s"] / 2 - 15
sig_key = abs(eAf["Hx"]) / (L_s * h_t) + 6 * (My - rest_r) / (L_s * h_t ** 2)
table("Prueba 2 – Fuera del plano (z: eje cilindro y contacto uña–pasador, lengüeta); kN, kN·m",
      ["Magnitud", "Diseño (final de carrera)", "Calado", "Comentario"],
      [["e_z eje cilindro − contacto uña", s3(z_c - z_dog), s3(z_c - z_dog), "0 por construcción (uña centrada en la luz del pasador)"],
       ["Δz carga – lengüeta (mm)", s3(dz), s3(dz), f"z_c = {s3(z_c)}, z_lengüeta = {s3(z_t)}"],
       ["Cabeceo M_x = fricción de guía · Δz", s3(Mx / 1e6), s3(Mx_cal / 1e6), "levanta la cola del patín"],
       ["Peso estabilizante (patín + ½ cilindro)", s3(rest_p / 1e6), s3(rest_p / 1e6), f"m_patín {s3(m_shoe)} kg"],
       ["Retención vertical necesaria en la cola", s3(V_rear / 1e3), s3(V_rear_cal / 1e3), "no hay regleta ni cola de milano"],
       ["Balanceo M_y = H_x · Δz (modelo A)", s3(My / 1e6), s3(My_cal / 1e6), "H_x radial de la uña"],
       ["Retención en el borde opuesto (regleta a " + s3(lev_gib) + " mm)", s3((My - rest_r) / lev_gib / 1e3), s3((My_cal - rest_r) / lev_gib / 1e3), ""],
       ["σ lengüeta como chaveta a momento (sin regletas), MPa", s3(sig_key), s3(H_cal / (L_s * h_t) + 6 * (My_cal - rest_r) / (L_s * h_t ** 2)), f"adm 1,25Fy/Nd = {s3(Fb)}"]])
busca = [v["nombre"] for v in D0["verificaciones"] if any(k in v["nombre"].lower() for k in ("lengüeta", "ranura", "labio", "volc", "levant", "retenc"))]
print("Verificaciones del núcleo con «lengüeta/ranura/labio/volc/levant/retenc»:", busca)
comp("2", "Retención vertical del patín (cabeceo), kN", V_rear / 1e3, None)
comp("2", "Balanceo del patín por H_x, kN·m", My / 1e6, None)
FIND.append(("H2", "importante", "Patín sin retención vertical: cabeceo por la fricción de guía (Δz = 90 mm) y balanceo por H_x; ninguna verificación del núcleo",
             "no verificado", f"retención ≥ {s3(V_rear_cal/1e3)} kN en la cola (calado) y {s3((My_cal-rest_r)/lev_gib/1e3)} kN en el borde (balanceo)"))

# ======================================================================================
# PRUEBA 4 – Uña (calado: F = F_calado en la uña, como el núcleo)
# ======================================================================================
Fy_d = P["Fy_dog"]; S_d = h_d * b ** 2 / 6; A_d = h_d * b
fa_d, fv_d = Fy_d / Nd, Fy_d / (Nd * 3 ** .5)
lev = mouthX - a_min
dE = math.sqrt(R_seat ** 2 - P["c_tip"] ** 2)
E = (-P["c_tip"], -dE)                               # borde del asiento del lado de la punta (coord. de la uña)
ec = estado(ph, F_st * a_min, MOD)                   # misma razón H/F que en marcha (uña entrando, contacto en E)
cH = abs(ec["Hx"]) / ec["F"]
H_st = cH * F_st; Ms_st = 0.0
def M_sec(F, Hx, pt, xs, yc):
    """Momento (z) en la sección x = xs (centroide y = yc) de la fuerza (Hx, −F) aplicada en pt."""
    rx, ry = pt[0] - xs, pt[1] - yc
    return rx * (-F) - ry * Hx
# (a) flexión en la boca
sig_core = F_st * (lev + P["e_dog"]) / S_d
comp("4", "Uña: σ flexión en la boca (fórmula del núcleo), MPa", sig_core, ver("Flexión en la boca")["dem"])
def bloque(l, L):
    c = -l + math.sqrt(l * l + l * L + L * L / 2)
    return c, 1 / (2 * c - L)                         # σ·h = F/(2c − L)
c_pl, k_pl = bloque(lev, L_in)
x0 = (2 * c_pl - L_in)
M_pl = F_st * (lev + x0 / 2)
comp("4", "Uña: M máx dentro del alojamiento (bloque plástico) / M núcleo", M_pl / (F_st * (lev + P["e_dog"])), 1.0, tol=0.01)
M_E = abs(M_sec(F_st, -H_st, E, lev, -b / 2))        # contacto en el borde E, uña arrastrada hacia adentro
sig_E = M_E / S_d + H_st / A_d
M_E0 = abs(M_sec(F_st, 0.0, E, lev, -b / 2))         # contacto en E sin arrastre (uña trabada)
sig_E0 = M_E0 / S_d
FIND.append(("H3", "menor", "Uña: flexión en la boca con la carga en el borde del asiento (brazo l + c_tip) y H_x axial",
             f"FU {s3(sig_core/fa_d)}", f"FU {s3(max(sig_E, sig_E0)/fa_d)}"))
# (b) sección neta por el asiento R51 (entalla de profundidad R51 en el centro, F-03)
def gancho(F, Hx, pt):
    best = (0.0, 0.0, 0.0)
    xs = pt[0] + 0.25
    while xs <= lev:
        d = math.sqrt(R_seat ** 2 - xs ** 2) if abs(xs) < R_seat else 0.0
        w = b - d; yc = -(b + d) / 2
        sg = 6 * abs(M_sec(F, Hx, pt, xs, yc)) / (h_d * w ** 2) + abs(Hx) / (h_d * w)
        if sg > best[0]:
            best = (sg, xs, w)
        xs += 0.25
    return best
g_c = gancho(F_st, 0.0, (0.0, -R_seat))             # 1.ª mitad: carga en el fondo del asiento
g_E0 = gancho(F_st, 0.0, E)                          # 2.ª mitad: pasador apoyado en el borde, uña trabada
g_EH = gancho(F_st, -H_st, E)                        # 2.ª mitad: borde arrastrando la uña hacia adentro
eDd = estado(ph, Tn_d, MOD)
g_Ed = gancho(eDd["F"], eDd["Hx"], E)                # ídem a carga de diseño
FIND.append(("H4", "crítica", f"Uña: sección neta del «gancho» junto al asiento R51 (entalla {s3(R_seat)} mm de profundidad en uña de {s3(b)}; punta maciza {s3(b - dE)} mm) no verificada",
             "no verificado", f"FU {s3(g_c[0]/fa_d)} (carga en el fondo, calado); {s3(g_E0[0]/fa_d)}–{s3(g_EH[0]/fa_d)} (carga en el borde, calado); {s3(g_Ed[0]/fa_d)} a carga de diseño"))
# (c) corte en la boca
tau = 1.5 * F_st / A_d
comp("4", "Uña: τ corte en la boca, MPa", tau, ver("Corte en la boca")["dem"])
# (d) aplastamiento pasador–uña (proyectado) y Hertz conforme R51/R50
sig_br = F_st / (P["d_pin"] * h_d)
comp("4", "Pasador–uña: aplastamiento proyectado, MPa", sig_br, ver("Aplastamiento pasador–uña")["dem"])
Es = P["E"] / (2 * (1 - P["nu"] ** 2))
Req = r_p * R_seat / (R_seat - r_p)
pH_conf = math.sqrt(F_st / h_d * Es / (math.pi * Req))
pH_flat = math.sqrt(F_st / h_d * Es / (math.pi * r_p))
pH_lim = 1.67 * min(Fy_d, P["Fy_pin"])
# (e) aplastamiento en el alojamiento (labio)
sig_lip_core = F_st * (lev + L_in) / L_in / (P["l_lip"] * h_d)
comp("4", "Labio: σ = F(l+L_in)/L_in/(l_labio·h), MPa", sig_lip_core, ver("labio delantero")["dem"])
sig_lip_pl = F_st * k_pl / h_d
lev_eq = M_E / F_st
c_plH, k_plH = bloque(lev_eq, L_in)
sig_lip_plH = F_st * k_plH / h_d
p_el = F_st / (h_d * L_in) * (4 + 6 * lev / L_in)
FIND.append(("H5", "importante", "Aplastamiento uña–alojamiento: el núcleo pone N2 concentrada en el extremo y reparte N1 en l_labio (incoherente); el bloque rígido-plástico da c ≈ l_labio y N1 ≈ 2,9F",
             f"FU {s3(ver('labio delantero')['fu'])}", f"FU {s3(sig_lip_pl/Fb)} (carga en el borde: {s3(sig_lip_plH/Fb)}); pico elástico {s3(p_el)} MPa"))
# (f) pared de la nariz del alojamiento (25 mm adelantada, paredes 20 mm, F-03)
inset = KC["inset"]; t_w = 20.0
N1_core = F_st * (lev + L_in) / L_in
V_nose = N1_core * min(inset, P["l_lip"]) / P["l_lip"]
sig_nose = V_nose * inset / 2 / ((h_d + 20) * t_w ** 2 / 6)
tau_nose = V_nose / ((h_d + 20) * t_w)
# (g) arrastre de la uña: el borde del asiento está a ψ = −asin(c_tip/R51)
psi_edge = math.degrees(math.asin(P["c_tip"] / R_seat))
eA2d = estado(ph, Tn_d, "asiento")
psi_req = math.degrees(math.atan(abs(eA2d["Hx"]) / eA2d["F"]))
psi_cap = psi_edge + math.degrees(math.atan(mu_s))
jam = 2 * mu_p * (b / 2) / L_in                      # «efecto cajón»: atasca si ≥ 1
table("Prueba 4 – Uña a F_calado = " + s3(F_st / 1e3) + " kN (2.ª mitad: carga en el borde E del asiento, H_x = " + s3(H_st / 1e3) + " kN)",
      ["Chequeo", "Hipótesis", "Propio", "Núcleo", "Adm.", "FU propio", "FU núcleo"],
      [["Flexión en la boca", "F(l+e)/S", s3(sig_core), s3(ver("Flexión en la boca")["dem"]), s3(fa_d), s3(sig_core / fa_d), s3(ver("Flexión en la boca")["fu"])],
       ["Flexión en la boca, carga en E, uña trabada", f"brazo {s3(lev + P['c_tip'])}", s3(sig_E0), "—", s3(fa_d), s3(sig_E0 / fa_d), "—"],
       ["Flexión en la boca, carga en E + H_x", "M + H/A", s3(sig_E), "—", s3(fa_d), s3(sig_E / fa_d), "—"],
       ["Gancho: carga en el fondo del asiento", f"x = {s3(g_c[1])}, ancho neto {s3(g_c[2])}", s3(g_c[0]), "—", s3(fa_d), s3(g_c[0] / fa_d), "—"],
       ["Gancho: carga en el borde E, uña trabada", f"x = {s3(g_E0[1])}, ancho neto {s3(g_E0[2])}", s3(g_E0[0]), "—", s3(fa_d), s3(g_E0[0] / fa_d), "—"],
       ["Gancho: carga en E arrastrando la uña", f"x = {s3(g_EH[1])}, ancho neto {s3(g_EH[2])}", s3(g_EH[0]), "—", s3(fa_d), s3(g_EH[0] / fa_d), "—"],
       ["Gancho: ídem a carga de diseño", f"F = {s3(eDd['F']/1e3)} kN", s3(g_Ed[0]), "—", s3(fa_d), s3(g_Ed[0] / fa_d), "—"],
       ["Corte en la boca", "1,5F/(hb)", s3(tau), s3(ver("Corte en la boca")["dem"]), s3(fv_d), s3(tau / fv_d), s3(ver("Corte en la boca")["fu"])],
       ["Aplast. pasador–uña (proyectado)", "F/(d·h)", s3(sig_br), s3(ver("Aplastamiento pasador–uña")["dem"]), s3(1.25 * min(Fy_d, P["Fy_pin"]) / Nd), s3(sig_br / (1.25 * min(Fy_d, P["Fy_pin"]) / Nd)), s3(ver("Aplastamiento pasador–uña")["fu"])],
       ["Hertz asiento conforme R51/R50", f"R_eq = {s3(Req)}", s3(pH_conf), "—", "1,67Fy = " + s3(pH_lim), s3(pH_conf / pH_lim), "—"],
       ["Hertz si la cara fuera plana", "R = 50", s3(pH_flat), "—", s3(pH_lim), s3(pH_flat / pH_lim), "—"],
       ["Labio: modelo del núcleo", "N1 = F(l+L)/L en l_labio", s3(sig_lip_core), s3(ver("labio delantero")["dem"]), s3(Fb), s3(sig_lip_core / Fb), s3(ver("labio delantero")["fu"])],
       ["Labio: bloque rígido-plástico", f"c = {s3(c_pl)} mm, σ = F/(h(2c−L))", s3(sig_lip_pl), "—", s3(Fb), s3(sig_lip_pl / Fb), "—"],
       ["Labio: bloque plástico, carga en E", f"l_eq = {s3(lev_eq)}", s3(sig_lip_plH), "—", s3(Fb), s3(sig_lip_plH / Fb), "—"],
       ["Labio: pico elástico (Winkler lineal)", "F/(hL)(4+6l/L)", s3(p_el), "—", s3(Fb), s3(p_el / Fb), "—"],
       ["Nariz del alojamiento (25 × pared 20)", f"V = {s3(V_nose/1e3)} kN, flexión", s3(sig_nose), "—", s3(Fy / Nd), s3(sig_nose / (Fy / Nd)), "—"],
       ["Nariz: corte", "V/(t·(h+20))", s3(tau_nose), "—", s3(Fy / (Nd * 3 ** .5)), s3(tau_nose / (Fy / (Nd * 3 ** .5))), "—"],
       ["Arrastre de la uña por el asiento (diseño)", f"ψ req = atan(H/F) vs borde {s3(psi_edge)}° + φ", s3(psi_req), "—", s3(psi_cap), s3(psi_req / psi_cap), "—"],
       ["Efecto cajón de la uña (atasco)", "2μ(b/2)/L_in", s3(jam), "—", "1", s3(jam), "—"]])
rows = []
for mu in (0.10, 0.15, 0.20, 0.25):
    e = estado(ph, Tn_d, "asiento", mu_pp=mu, mu_ss=mu)
    pr = math.degrees(math.atan(abs(e["Hx"]) / e["F"])); pc = psi_edge + math.degrees(math.atan(mu))
    pc_min = psi_edge - math.degrees(math.atan(mu))
    rows.append([s3(mu), s3(abs(e["Hx"]) / e["F"]), s3(pr), f"{s3(pc_min)}–{s3(pc)}", "sí" if pr <= pc_min else ("límite" if pr <= pc else "NO (el pasador monta el borde)")])
table("Prueba 4b – Arrastre de la uña hacia adentro por el flanco del asiento (2.ª mitad, carga de diseño). "
      "El rango disponible depende del sentido del deslizamiento en E (giro del pasador vs traslación radial)",
      ["μ_p = μ_s", "H/F requerido", "ψ requerido °", "ψ disponible ° (borde ∓ φ)", "¿lo transmite?"], rows)
FIND.append(("H6", "importante", "Nariz del alojamiento (adelantada 25 mm, paredes de 20 mm) recibe N1 en la boca y no se verifica",
             "no verificado", f"flexión FU {s3(sig_nose/(Fy/Nd))}, corte FU {s3(tau_nose/(Fy/(Nd*3**.5)))}"))
FIND.append(("H7", "crítica", "Asiento R51 abierto hacia la punta (borde a %s°, c_tip = 15): en la 2.ª mitad de cada carrera la uña debe volver 5,85 mm hacia adentro y solo puede arrastrarla el borde del asiento" % s3(psi_edge),
             "no verificado", f"ψ requerido {s3(psi_req)}° frente a {s3(psi_edge - math.degrees(math.atan(mu_s)))}–{s3(psi_cap)}° disponibles: el pasador apoya en la arista E (contacto de borde)"))

# ======================================================================================
# PRUEBA 5 – Pasador de empuje con la carga a la altura de la uña
# ======================================================================================
tpr = max(P["t_pr"], P["t_top"], P["t_bot"])
Lc = P["h_disc"] - 2 * tpr; Ls_ = P["h_disc"] - tpr
S_p = math.pi * P["d_pin"] ** 3 / 32; A_p = math.pi / 4 * P["d_pin"] ** 2
z0 = (Lc - h_d) / 2                                   # inicio de la carga desde la cara del anillo
Fres = math.hypot(F_st, H_st)
def M_pin(F, L, z1, z2, emp):
    """Viga de luz L con carga uniforme F entre z1 y z2; emp=True biempotrada. Devuelve M máx."""
    w = F / (z2 - z1); m = 2000; best = 0
    if emp:
        # momentos de empotramiento por superposición de cargas puntuales: M_A = Σ P a b²/L²
        MA = sum(w * (z2 - z1) / m * ((z1 + (i + .5) * (z2 - z1) / m) * (L - (z1 + (i + .5) * (z2 - z1) / m)) ** 2) / L ** 2 for i in range(m))
        Mmid = F / 2 * L / 2 - w * ((L / 2 - z1) ** 2) / 2 - MA
        return max(MA, Mmid)
    return F / 2 * L / 2 - w * ((L / 2 - z1) ** 2) / 2
rows = []
sp_core = ver("Flexión (biapoyado entre planchas")["dem"]
for lab, L, z1, emp in [("biapoyado L=h−t (núcleo), carga puntual", Ls_, Ls_ / 2, False),
                        ("biapoyado L=h−t, carga repartida en h_uña", Ls_, (Ls_ - h_d) / 2, False),
                        ("biempotrado L=luz libre, repartida en h_uña", Lc, z0, True)]:
    if z1 == Ls_ / 2:
        M = F_st * L / 4; MH = Fres * L / 4
    else:
        M = M_pin(F_st, L, z1, z1 + h_d, emp); MH = M_pin(Fres, L, z1, z1 + h_d, emp)
    rows.append([lab, s3(L), s3(M / S_p), s3(MH / S_p), s3(sp_core), s3(MH / S_p / (P["Fy_pin"] / Nd))])
comp("5", "Pasador: σ biapoyado carga puntual, MPa", F_st * Ls_ / 4 / S_p, sp_core)
tau_p = 4 * Fres / (3 * A_p)
rows.append(["corte 4F/3A con resultante √(F²+H²)", "—", s3(4 * F_st / (3 * A_p)), s3(tau_p), s3(ver("Corte (carga junto")["dem"]), s3(tau_p / (P["Fy_pin"] / (Nd * 3 ** .5)))])
table("Prueba 5 – Pasador de empuje a F_calado (MPa)", ["Modelo", "L mm", "σ (F)", "σ (√(F²+H²))", "Núcleo", "FU propio"], rows)

# ======================================================================================
# PRUEBA 6 – Giro: casos y barridos (núcleo vía params.json)
# ======================================================================================
rows = []
for c in DV["casos"]:
    mu, r = cs[c["id"]]; T = par(P, mu, r)
    Fn = Fmax(T / n, "nucleo")["Fh"]; Fa = Fmax(T / n, MOD)["Fh"]; Fa2 = Fmax(T / n, "asiento")["Fh"]; Fp = Fmax(T / n, "plana")["Fh"]
    comp("6", f"Caso {c['id']}: F_cil (kN)", Fn / 1e3, c["F"])
    rows.append([c["id"], s3(mu), s3(r), s3(T / 1e6), s3(c["F"]), s3(Fn / 1e3), s3(c["FS"]), "sí" if c["gira"] else "no",
                 s3(Fa / 1e3), s3(F_st / Fa), "sí" if F_st >= Fa else "NO", s3(F_st / Fa2), s3(F_st / Fp)])
table("Prueba 6a – Casos de fricción (F en kN, T en kN·m); A = asiento con borde (principal), A' = resultante por el centro, P = cara plana",
      ["Caso", "μ", "r mm", "T", "F núcleo", "F propio (mod. núcleo)", "FS núcleo", "gira núcleo", "F A", "FS A", "gira A", "FS A'", "FS P"], rows)
for cid in ("cont", "borde"):
    mu, r = cs[cid]; Fa = Fmax(par(P, mu, r) / n, MOD)["Fh"]
    if Fa > F_st:
        FIND.append(("H1-" + cid, "crítica", f"Caso {cid}: con la fricción de la uña no gira (cala al final de la carrera)",
                     f"FS {s3([c for c in DV['casos'] if c['id']==cid][0]['FS'])}", f"FS {s3(F_st/Fa)}"))
# μ máximo que gira (lineal en μ)
Tu = par(P, 1.0, r_ef)
mu_max_n = F_st / (Fmax(Tu / n, "nucleo")["Fh"])
mu_max_a = F_st / (Fmax(Tu / n, MOD)["Fh"])
comp("6", "μ máx que gira con r_ef (modelo núcleo)", mu_max_n, DV["muMax_ref"])
print(f"\nμ máx que gira (r_ef): núcleo {s3(DV['muMax_ref'])}, propio-modelo-núcleo {s3(mu_max_n)}, propio-asiento {s3(mu_max_a)}; "
      f"μ para FS=1,25: núcleo {s3(mu_max_n/1.25)}, asiento {s3(mu_max_a/1.25)}")

def sweep(key, vals, extra=lambda v: {}):
    rows = []
    for v in vals:
        over = {key: v}; over.update(extra(v))
        D = export(over)
        PP = dict(P); PP.update(over)
        if key == "mu_g":
            global mu_g
        mu, r = PP["mu_d"], PP["r_ef"]
        T = par(PP, mu, r)
        kw = dict(mu_gg=PP["mu_g"], mu_pp=PP["mu_g"], mu_ss=PP["mu_g"])
        if key == "mu_g":
            Kv = (1 + 2 * PP["mu_g"] * (x_g - a_min) / Lg) / eta
            Fn = Kv * T / (n * a_min)
        else:
            Fn = Fmax(T / n, "nucleo", mu_gg=PP["mu_g"])["Fh"]
        Fa = Fmax(T / n, MOD, **kw)["Fh"]
        if D is None:
            rows.append([s3(v), "rechazado por el validador", "—", "—", s3(Fn / 1e3), s3(F_st / Fn), s3(Fa / 1e3), s3(F_st / Fa), "—"])
            continue
        cd = [c for c in D["derivados"]["casos"] if c["id"] == "dis"][0]
        comp("6", f"Barrido {key}={v}: F_dis", Fn / 1e3, cd["F"])
        rows.append([s3(v), s3(cd["F"]), s3(cd["FS"]), "sí" if cd["gira"] else "no", s3(Fn / 1e3), s3(F_st / Fn), s3(Fa / 1e3), s3(F_st / Fa),
                     "sí" if Fa <= F_st else "NO"])
    return rows
hdr = ["valor", "F_dis núcleo", "FS núcleo", "gira núcleo", "F propio (mod. núcleo)", "FS propio", "F con uña (A)", "FS A", "gira A"]
table("Prueba 6b – Barrido μ_d (r_ef = 0,80 m)", hdr, sweep("mu_d", [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]))
table("Prueba 6c – Barrido de carga W (μ_d = 0,20)", hdr, sweep("W_tf", [200, 240, 280, 300, 320, 360]))
table("Prueba 6d – Barrido μ_g (μ_p = μ_s = μ_g en el modelo con asiento)", hdr, sweep("mu_g", [0.10, 0.15, 0.20, 0.25]))
# carga límite que gira (W) con μ_d=0,20, ambos modelos
def W_lim(modelo, FS=1.0):
    lo, hi = 50, 2000
    for _ in range(60):
        mid = (lo + hi) / 2; PP = dict(P); PP["W_tf"] = mid
        F = Fmax(par(PP, mu_d, r_ef) / n, modelo)["Fh"]
        lo, hi = (mid, hi) if F_st / F >= FS else (lo, mid)
    return lo
print(f"Carga máxima que gira (μ=0,20, r_ef): modelo núcleo {s3(W_lim('nucleo'))} tf (FS 1,25: {s3(W_lim('nucleo',1.25))} tf); "
      f"con uña (A) {s3(W_lim(MOD))} tf (FS 1,25: {s3(W_lim(MOD,1.25))} tf)")

# ======================================================================================
# PRUEBA 7 – Retorno y reenganche
# ======================================================================================
F_ret = A_ann * P["p_ret"] / 10
comp("7", "F_retorno = A_anular·p_ret (kN)", F_ret / 1e3, DV["Fret"])
def leva(alpha_deg, mu, Fsp=F_sp):
    """Uña empujada hacia afuera por el pasador siguiente al retraer (cara trasera achaflanada).
    alpha = ángulo de la normal de contacto respecto de +x (= ángulo del chaflán respecto de la dirección y del movimiento).
    Fuerza del pasador sobre la uña: N/cosφ·(cos(β+φ), sin(β+φ)) en (r cos β, −b) (origen = centro del asiento en reposo).
    Devuelve (P en y que se opone al retorno, Q radial) o None si autobloquea."""
    beta = math.radians(alpha_deg); phi = math.atan(mu)
    xc = r_p * math.cos(beta)
    xm = mouthX - a_min
    cx, cy = math.cos(beta + phi) / math.cos(phi), math.sin(beta + phi) / math.cos(phi)
    r = dog_solve(+1, mu, xm, L_in, Fsp, known=[], Mk=0.0, unk=((cx, cy), (xc, -b)))
    if r is None or r[0] <= 0:
        return None
    N = r[0]
    return N * cy, N * cx
rows = []
for alpha in (30, 45, 60):
    row = [f"normal a {alpha}° de x (chaflán a {alpha}° del movimiento)"]
    for mu in (0.15, 0.20, 0.25, 0.30):
        rr = leva(alpha, mu)
        row.append("AUTOBLOQUEO" if rr is None else s3(rr[0] / 1e3))
    rows.append(row)
table("Prueba 7a – Fuerza P (kN) que la leva opone al retorno; F_ret disponible = " + s3(F_ret / 1e3) + " kN",
      ["Geometría del contacto", "μ=0,15", "μ=0,20", "μ=0,25", "μ=0,30"], rows)
# extensión del chaflán necesaria para que el contacto caiga en él
rows = []
for alpha in (30, 45, 60):
    cx_need = (a_min + r_p * math.cos(math.radians(alpha))) - tipX
    cy_need = cx_need / math.tan(math.radians(alpha))
    solid_tip = b - math.sqrt(R_seat ** 2 - P["c_tip"] ** 2)
    rows.append([f"{alpha}°", s3(cx_need), s3(cy_need), "cabe (corta la punta maciza de " + s3(solid_tip) + " mm)" if solid_tip < cy_need <= b else ("cabe" if cy_need <= b else "NO cabe en b = " + s3(b))])
table("Prueba 7b – Chaflán necesario desde la punta (mm)", ["normal de contacto", "Δx desde la punta", "Δy en la cara trasera", "¿cabe?"], rows)
def mu_lock(alpha):
    lo, hi = 0.0, 1.0
    if leva(alpha, hi) is not None:
        return float("inf")
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if leva(alpha, mid) is not None else (lo, mid)
    return lo
def beta_max(mu):
    lo, hi = 0.0, 89.0
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if leva(mid, mu) is not None else (lo, mid)
    return lo
solid_tip = b - math.sqrt(R_seat ** 2 - P["c_tip"] ** 2)
# chaflán contenido en la punta maciza (Δy ≤ solid_tip): contacto en el chaflán si cabe, si no en la arista B
def beta_real(alpha_ch):
    """alpha_ch: ángulo del chaflán respecto de y (= normal respecto de x). Devuelve β efectivo de la 1.ª toma."""
    dx_max = solid_tip * math.tan(math.radians(alpha_ch))
    need = (a_min + r_p * math.cos(math.radians(alpha_ch))) - tipX
    if dx_max >= need:
        return alpha_ch
    xB = tipX + dx_max
    return math.degrees(math.acos(max(-1, min(1, (xB - a_min) / r_p))))
rows = []
for lab, al in [("30° respecto de la cara trasera (normal a 60° de x)", 60), ("45°", 45), ("30° respecto del movimiento (normal a 30° de x)", 30)]:
    br = beta_real(al)
    rows.append([lab, s3(br), s3(mu_lock(br)), "sí" if mu_lock(br) > 0.30 else "NO"])
rows.append(["β máximo sin autobloqueo con μ = 0,20 / 0,30", s3(beta_max(0.20)) + " / " + s3(beta_max(0.30)), "—", "—"])
table(f"Prueba 7d – Chaflán limitado a la punta maciza bajo el asiento ({s3(solid_tip)} mm): ángulo real de la 1.ª toma y μ de autobloqueo",
      ["Interpretación del «chaflán 30°»", "β efectivo °", "μ de autobloqueo", "¿seguro hasta μ 0,30?"], rows)
# reenganche
clr_travel = tipX + KC["travel"] - (a_min + r_p)
d_end = P["s_free"]
win_plus = P["s_free"] + (R_seat - r_p)
win_minus = P["stroke"] - DV["K"]["s_req"] - P["s_margin"]
gap_back = (R * math.sin(2 * ph) - R * math.sin(0)) if False else (2 * R * math.sin(ph)) - r_p - b - (0)  # pasador anterior vs cara trasera
# reinserción radial: barrido de la uña desde afuera con la cara 10 mm detrás del centro del pasador
def interf(delta, dy):
    """¿Material de la uña (rectángulo menos entalla) dentro del pasador? uña desplazada delta hacia afuera."""
    xs = a_min + delta                                 # centro del asiento
    xt = xs - P["c_tip"]
    for i in range(0, 361):
        ang = math.radians(i)
        px, py = a_min + r_p * math.cos(ang), dy + r_p * math.sin(ang)   # pasador centrado en (a_min, dy) relativo a la cara (y=0)
        if xt <= px <= xt + (mouthX + L_in - tipX) and -b <= py <= 0:
            if math.hypot(px - xs, py) > R_seat - 1e-9:
                return True
    return False
blocked = [round(dl, 1) for dl in [x * 0.5 for x in range(0, int(KC["travel"] * 2) + 1)] if interf(dl, d_end)]
table("Prueba 7c – Reenganche",
      ["Chequeo", "Propio", "Núcleo", "Veredicto"],
      [["Holgura punta–pasador al retraer (tip + recorrido − (a_min + r))", s3(clr_travel), s3(KC["travel"]), "≥ 10 mm" if clr_travel >= 10 else "< 10 mm"],
       ["Holgura radial en carrera R(1−cos π/N)+2 vs slot", s3(R * (1 - math.cos(ph)) + 2), s3(ver("Holgura radial")["dem"]), "coincide"],
       ["Cara del asiento detrás del pasador al fin del retorno (mm)", s3(d_end), "s_libre", "≥ 0 → el pasador entra en la entalla"],
       ["Ventana de L0 real (cilindro): +mm admisible", s3(win_plus), "—", "si L0 > 520 + %s no reengancha" % s3(win_plus)],
       ["Ventana de L0 real: −mm admisible (carrera)", s3(win_minus), "—", "margen de carrera"],
       ["Posiciones de reinserción radial con interferencia", str(blocked[:6]) if blocked else "ninguna", "—", "OK" if not blocked else "INTERFIERE"],
       ["Retorno: demanda (sellos 5 % + peso + leva β 60°, μ 0,15) vs F_ret", s3(((1 - eta) * F_ret + mu_g * (W_shoe + W_cyl / 2) + leva(60, 0.15)[0]) / 1e3), s3(F_ret / 1e3), "OK si no autobloquea (ver 7d)"]])
if mu_lock(beta_real(60)) < 0.30 or mu_lock(beta_real(45)) < 0.30:
    FIND.append(("H8", "importante", "Chaflán de retorno «30°» sin referencia ni cotas (F-03 no lo dibuja); dentro de la punta maciza (%s mm) la 1.ª toma queda a β ≈ %s° y la uña se autobloquea" % (s3(solid_tip), s3(beta_real(45))),
                 "no verificado", "autobloqueo con μ ≥ %s (β 60°) / %s (β %s°); exigir β ≤ %s° para μ 0,30" % (s3(mu_lock(beta_real(60))), s3(mu_lock(beta_real(45))), s3(beta_real(45)), s3(beta_max(0.30)))))

# ======================================================================================
# PRUEBA 8 – Otros frentes
# ======================================================================================
Lb = P["L0"] + P["stroke"]; I = math.pi * P["d_rod"] ** 4 / 64
Pcr = math.pi ** 2 * P["E"] * I / Lb ** 2
comp("8", "Pandeo vástago: Pcr (kN)", Pcr / 1e3, ver("Pandeo del vástago")["cap"] * 3)
# lengüeta: reacción y presión con H y con distribución lineal
Rg_core = F_st * (x_g - a_min) / Lg
comp("8", "R_guía a calado F_st·Δ/Lg (kN)", Rg_core / 1e3, DV["Rguide"])
sig_t_core = Rg_core / (P["h_slot"] * L_s / 3)
sig_t_lin = 4 * Rg_core / (h_t * L_s)
Rf_H = abs(ec["Rf"]) / ec["F"] * F_st                # misma configuración que en marcha (contacto en E), escalada a F_calado
sig_t_H = 4 * Rf_H / (h_t * L_s)
sig_t_coreH = Rf_H / (P["h_slot"] * L_s / 3)
wall = (P["w_bed"] - P["w_slot"]) / 2
sig_wall_core = Rg_core * P["h_slot"] / 2 / (L_s / 3 * wall ** 2 / 6)
sig_wall_H = Rf_H * P["h_slot"] / 2 / (L_s / 3 * wall ** 2 / 6)
e_dd = estado(ph, Tn_d, MOD)
# soldadura bancada–base
w_f = P["w_bed_f"]
f_core = Rg_core / (2 * 0.707 * w_f * (L_s + 2 * P["w_bed"]))
L_loc = L_s / 2 + 2 * P["t_bed"]
f_1 = Rg_core / (0.707 * w_f * L_loc)
f_1H = Rf_H / (0.707 * w_f * L_loc)
Fw = 0.6 * P["FEXX"] / (1.2 * Nd)
floor = P["t_bed"] - P["h_slot"]
# asimetría entre los dos patines (μg 0,10 / 0,20): fuerza neta al pivote
Kl = 1 + 2 * 0.10 * (x_g - a_min) / Lg; Kh = 1 + 2 * 0.20 * (x_g - a_min) / Lg
Frod = 2 * Tn_d / a_min / (1 / Kl + 1 / Kh)
dF = Frod * (1 / Kl - 1 / Kh)
p_bush = ver("Presión en el buje")
table("Prueba 8 – Otros frentes", ["Frente", "Propio", "Núcleo", "Adm.", "FU propio", "FU núcleo"],
      [["Pandeo del vástago Euler L = L0+carrera (kN)", s3(Pcr / 1e3), s3(ver("Pandeo del vástago")["cap"] * 3), "Pcr/3", s3(F_st / (Pcr / 3)), s3(ver("Pandeo del vástago")["fu"])],
       ["Lengüeta: σ = R/(h_ranura·L_s/3) (núcleo)", s3(sig_t_core), s3(ver("lengüeta")["dem"]), s3(Fb), s3(sig_t_core / Fb), s3(ver("lengüeta")["fu"])],
       [f"R_guía delantera a calado con H_x (kN); a carga de diseño {s3(e_dd['Rf']/1e3)}", s3(Rf_H / 1e3), s3(DV["Rguide"]), "—", "—", "—"],
       ["Lengüeta: fórmula del núcleo con R corregida", s3(sig_t_coreH), s3(ver("lengüeta")["dem"]), s3(Fb), s3(sig_t_coreH / Fb), s3(ver("lengüeta")["fu"])],
       ["Pared de la ranura: fórmula del núcleo con R corregida", s3(sig_wall_H), s3(ver("Pared de la ranura")["dem"]), s3(Fy / Nd), s3(sig_wall_H / (Fy / Nd)), s3(ver("Pared de la ranura")["fu"])],
       ["Lengüeta: pico lineal 4R/(h_t·L_s), h_t = h_ranura−2", s3(sig_t_lin), "—", s3(Fb), s3(sig_t_lin / Fb), "—"],
       ["Lengüeta: pico lineal con H_x (uña entrando)", s3(sig_t_H), "—", s3(Fb), s3(sig_t_H / Fb), "—"],
       ["Soldadura bancada–base: 2 filetes, L_s+2w (núcleo)", s3(f_core), s3(ver("Soldadura bancada")["dem"]), s3(Fw), s3(f_core / Fw), s3(ver("Soldadura bancada")["fu"])],
       [f"Soldadura: 1 filete (fondo de ranura {s3(floor)} mm), L = L_s/2+2t", s3(f_1), "—", s3(Fw), s3(f_1 / Fw), "—"],
       ["Soldadura: ídem con H_x", s3(f_1H), "—", s3(Fw), s3(f_1H / Fw), "—"],
       ["Asimetría μg 0,10/0,20 entre patines: fuerza neta al pivote (kN)", s3(dF / 1e3), "0 (par puro)", "—", "—", "—"],
       ["Buje con esa fuerza adicional (MPa)", s3(p_bush["dem"] + dF / (P["D_piv"] * P["L_bush"])), s3(p_bush["dem"]), s3(p_bush["cap"]),
        s3((p_bush["dem"] + dF / (P["D_piv"] * P["L_bush"])) / p_bush["cap"]), s3(p_bush["fu"])]])
comp("8", "Lengüeta σ (fórmula del núcleo)", sig_t_core, ver("lengüeta")["dem"])
comp("8", "Soldadura bancada f (fórmula del núcleo)", f_core, ver("Soldadura bancada")["dem"])
comp("8", "Pared de la ranura σ (fórmula del núcleo)", sig_wall_core, ver("Pared de la ranura")["dem"])
FIND.append(("H9", "importante", f"Lengüeta/bancada: reacción concentrada; fondo de ranura de {s3(floor)} mm deja un solo filete por reacción",
             f"FU lengüeta {s3(ver('lengüeta')['fu'])}, soldadura {s3(ver('Soldadura bancada')['fu'])}",
             f"FU lengüeta {s3(sig_t_lin/Fb)} ({s3(sig_t_H/Fb)} con H), soldadura {s3(f_1/Fw)} ({s3(f_1H/Fw)} con H)"))
FIND.append(("H11", "menor", "Descripción «cara plana» frente a planos/núcleo: l_p llega al CENTRO del pasador y F-03 dibuja asiento R51 centrado en la cara (entalla de media caña); el chequeo «Uña entre pasadores» supone cara en la superficie del pasador",
             "inconsistente", "unificar: o cara plana (desplazar 50 mm la cinemática) o asiento con c_tip ≥ 35 y gancho verificado"))
FIND.append(("H12", "menor", "Pasador de empuje: la resultante √(F²+H²) no se considera (el modelo puntual del núcleo la cubre)",
             f"FU {s3(ver('Flexión (biapoyado entre planchas')['fu'])}", f"FU {s3(math.hypot(F_st, H_st) * Ls_ / 4 / S_p / (P['Fy_pin'] / Nd))}"))
FIND.append(("H10", "menor", "Asimetría de fricción entre patines: el par deja de ser puro; fuerza neta al pivote",
             f"buje FU {s3(p_bush['fu'])}", f"buje FU {s3((p_bush['dem'] + dF / (P['D_piv'] * P['L_bush'])) / p_bush['cap'])}"))

# ======================================================================================
# Dimensionamiento de las correcciones propuestas (orientativo, a F_calado)
# ======================================================================================
def L_in_req(l, fb):
    lo, hi = 10.0, 1000.0
    for _ in range(80):
        m = (lo + hi) / 2
        c = -l + math.sqrt(l * l + l * m + m * m / 2)
        lo, hi = (m, hi) if F_st / (h_d * (2 * c - m)) > fb else (lo, m)
    return hi
def hook_fu(bb):
    best = 0.0
    x = 0.0
    while x <= R_seat:
        d = math.sqrt(R_seat ** 2 - x * x); w = bb - d
        best = max(best, 6 * F_st * x / (h_d * w * w)); x += 0.25
    return best / fa_d
y_face0 = -R * math.sin(ph) - P["s_free"]
xp3, yp3 = R * math.cos(3 * ph), -R * math.sin(3 * ph)
dxp = tipX - xp3
y_surf3 = yp3 + (math.sqrt(r_p ** 2 - dxp ** 2) if abs(dxp) < r_p else 0.0)
b_max = y_face0 - y_surf3 - 10
b_ok = next(bb for bb in range(int(b), 400) if hook_fu(bb) <= 1.0)
table("Dimensionamiento orientativo de correcciones (F_calado)",
      ["Corrección", "Valor actual", "Necesario", "Comentario"],
      [["L_in para labio FU ≤ 1 (bloque plástico, Fy patín 345)", s3(L_in), s3(L_in_req(lev, Fb)), "alarga alojamiento y patín"],
       ["b_uña para gancho FU ≤ 1 (carga en el fondo)", s3(b), s3(b_ok), f"FU con b = 120: {s3(hook_fu(120))}"],
       ["b_uña máx. geométrico (asiento en el centro del pasador, 10 mm al pasador 3π/N)", s3(b), s3(b_max),
        "el chequeo «Uña entre pasadores» del núcleo (cuerda − d ≥ b + 20) limita b a 88 con un modelo que no es el dibujado"],
       ["Filete bancada (1 filete, L = L_s/2 + 2t) para R_guía de calado", s3(P["w_bed_f"]), s3(Rg_core / (0.707 * Fw * L_loc)), "mejor: bancada más gruesa, fondo ≥ 12 mm, o fijación atornillada/CJP"]])

# ======================================================================================
# Resumen
# ======================================================================================
table("Comparación con el núcleo (tolerancia 0,1 %)", ["Prueba", "Magnitud", "Propio", "Núcleo", "Δ %", "Veredicto"], COMP)
table("Hallazgos", ["Id", "Severidad", "Hallazgo", "Núcleo", "Corregido"], FIND)
nco = sum(1 for c in COMP if c[5] == "coincide"); ndi = sum(1 for c in COMP if c[5] == "discrepa"); nom = sum(1 for c in COMP if c[5] == "el núcleo omite")
sev = {k: sum(1 for f in FIND if f[1] == k) for k in ("crítica", "importante", "menor")}
print(f"\nRESULTADO: {nco} coincidencias, {ndi} discrepancias numéricas, {nom} omisiones; hallazgos: "
      f"{sev['crítica']} críticos, {sev['importante']} importantes, {sev['menor']} menores")
sys.exit(1 if sev["crítica"] or sev["importante"] else 0)
