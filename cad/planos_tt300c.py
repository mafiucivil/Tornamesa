"""Planos de diseño y fabricación TT300-C (A1), generados desde cad/out/TT300-C_design.json.
Uso: python3 cad/planos_tt300c.py [design.json]
Toda magnitud sale del JSON exportado por el núcleo de cálculo (tools/export_design.js): fuente única."""
import json, math, sys, pathlib, zipfile, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import draw
from draw import Sheet, W, H

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "cad" / "out"
D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else OUT / "TT300-C_design.json", encoding="utf-8"))
P, DV = D["P"], D["derivados"]
if not (D["verdict"]["gira"] and D["verdict"]["estructura"]):
    sys.exit("El diseño no cumple (gira/estructura): no se emiten planos. Corrija en la herramienta TT300-C.")

FECHA = datetime.date.fromisoformat(D["fecha"]).strftime("%d-%m-%Y")
M = DV["masas"]
V = {"proj": "TT300-C · TORNAMESA HIDRÁULICA 300 tf", "title": "Cilindro con patín guiado y uña · acero-acero con grasa grafitada", "code": "TT300-C", "fecha": FECHA,
     "rev_txt": f"Rev. B ({FECHA}): uña guiada de cara de empuje plana templada con chaflán de retorno {P['beta_ch']:.0f}°, patín con lengüeta T en bancada con ranura T, cilindros Ø{P['D_bore']:.0f}; reemplaza Rev. A. Generado desde TT300-C_design.json · FS diseño {DV['casos'][1]['FS']:.2f} · masa {M['total']:.0f} kg."}
SHEETS = ["D-01", "D-02", "F-01", "F-02", "F-03", "F-04"]
NS = len(SHEETS)

# ---------------- magnitudes derivadas ----------------
tb, hd, tt, tbo = P["t_base"], P["h_disc"], P["t_top"], P["t_bot"]
tpr = max(P["t_pr"], tt, tbo)
Rt, prIn = P["D_top"] / 2, DV["prIn"]
hw = hd - tt - tbo
hax = DV["hax"]
zc = tb + hax                                   # eje del cilindro (absoluto)
d_pin, R_pin, N_pin = P["d_pin"], P["R_pin"], int(P["N_pin"])
d_bush = P["D_piv"] + 30
z_hubtop = tb + hd - tt
L_piv = z_hubtop + 3
cb_t = 8                                        # tapa de inspección pos 8 (rebaje en la plancha superior)
cap_D = P["D_piv"] + 60
cap_t = tt - 3 - cb_t - 1                       # tapa retenedora pos 7: entre el pivote (+3 sobre el cubo) y la tapa pos 8, 1 de juego
hole_top, cb_D = cap_D + 20, cap_D + 60
BR = DV["bracket"]
Llug = BR["Llug"]
KG = DV["K"]
zb = tb + P["t_bed"]                                   # cara superior de la bancada
paw_L = KG["mouthX"] + P["L_in"] - KG["tipX"]          # largo de la uña
forkH = DV["forkH"]
washer_D = d_pin + 30
zT1 = zb - P["h_slot"]                                 # cabeza de la ranura T de la bancada: z ∈ [zT0, zT1]
zT0 = zT1 - P["h_tee"]
fondo = P["t_bed"] - P["h_slot"] - P["h_tee"]          # fondo de la ranura
neck_w, head_w, head_h = P["w_slot"] - 2, P["w_tee"] - 2, P["h_tee"] - 2   # lengüeta T del patín (1 de juego por lado)
neck_h = P["h_slot"] + 1                               # cuello: de la cabeza T (1 de juego bajo el labio) a la caja del patín
z_shoe = zc + forkH / 2                                # cara superior de la caja del patín
Hs = z_shoe - zb
ch_dx = KG["travel"]                                   # chaflán de retorno de la uña (chamferGeo del núcleo): Δx = recorrido
ch_dy = ch_dx / math.tan(math.radians(P["beta_ch"]))   # Δy = Δx / tan β
b_tipr = P["dog_b"] - ch_dy                            # ancho que queda en la punta
VER = {v["nombre"]: v for v in D["verificaciones"]}
z_hard = next(v["dem"] for v in D["verificaciones"] if v["nombre"].startswith("Profundidad mínima de temple"))
z_hard = math.ceil(z_hard * 10) / 10                   # profundidad efectiva de temple exigida (redondeo hacia arriba)
pk_top, pk_bot = zc + P["dog_h"] / 2 + 1, zc - P["dog_h"] / 2 - 1   # alojamiento de la uña en el patín (alto h_uña + 2)
HRC = "≥ 50 HRC"
def f(v, n=0):
    s = f"{v:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s
def f1(v): return f(v, 1)

def circ(c, r, n=96, a0=0.0, a1=360.0):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
def tr(ox, oy, s):
    return lambda p: (ox + p[0] * s, oy + p[1] * s)
def rot(p, a, c=(0, 0)):
    ca, sa = math.cos(a), math.sin(a)
    return (c[0] + p[0] * ca - p[1] * sa, c[1] + p[0] * sa + p[1] * ca)
def box_local(E, phi, x0, x1, y0, y1):
    return [(E[0] + q[0], E[1] + q[1]) for q in (rot(p, math.radians(phi)) for p in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])]
def section(s, T, adds, cuts=(), hatch=True, scale=0.5, angle=0.0, lay="VIS"):
    """Sección de una unión de rectángulos (x0, x1, z0, z1) menos otros: achurado por celdas y contorno real (sin líneas internas)."""
    xs = sorted({v for r in list(adds) + list(cuts) for v in r[:2]}); zs = sorted({v for r in list(adds) + list(cuts) for v in r[2:]})
    inside = lambda r, x, z: r[0] < x < r[1] and r[2] < z < r[3]
    fill = [[any(inside(r, (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2) for r in adds) and not any(inside(r, (xs[i] + xs[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2) for r in cuts)
             for j in range(len(zs) - 1)] for i in range(len(xs) - 1)]
    F = lambda i, j: 0 <= i < len(xs) - 1 and 0 <= j < len(zs) - 1 and fill[i][j]
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            if not fill[i][j]:
                continue
            if hatch:
                s.hatch_poly([T((xs[i], zs[j])), T((xs[i + 1], zs[j])), T((xs[i + 1], zs[j + 1])), T((xs[i], zs[j + 1]))], scale=scale, angle=angle)
            if not F(i - 1, j): s.line(T((xs[i], zs[j])), T((xs[i], zs[j + 1])), lay)
            if not F(i + 1, j): s.line(T((xs[i + 1], zs[j])), T((xs[i + 1], zs[j + 1])), lay)
            if not F(i, j - 1): s.line(T((xs[i], zs[j])), T((xs[i + 1], zs[j])), lay)
            if not F(i, j + 1): s.line(T((xs[i], zs[j + 1])), T((xs[i + 1], zs[j + 1])), lay)
def bed_xz(X):
    """Sección transversal de la bancada 1e (ranura T) en el plano x–z; X: eje de la guía."""
    adds = [(X - P["w_bed"] / 2, X + P["w_bed"] / 2, tb, zb)]
    cuts = [(X - P["w_slot"] / 2, X + P["w_slot"] / 2, zT1, zb + 1)] + ([(X - P["w_tee"] / 2, X + P["w_tee"] / 2, zT0, zT1)] if P["h_tee"] > 0 else [])
    return adds, cuts
def shoe_xz(X, mouth):
    """Sección del patín 16 por el alojamiento de la uña (plano x–z); mouth: x de la boca (mismo lado que X > 0)."""
    adds = [(X - P["w_s"] / 2, X + P["w_s"] / 2, zb, z_shoe), (X - neck_w / 2, X + neck_w / 2, zT1 - 1, zb), (X - head_w / 2, X + head_w / 2, zT0 + 1, zT1 - 1),
            (mouth, X - P["w_s"] / 2, zc - P["dog_h"] / 2 - 10, zc + P["dog_h"] / 2 + 10)]
    cuts = [(mouth - 1, X - P["x_g"] + KG["pocketEnd"] + 1, pk_bot, pk_top)]
    return adds, cuts
def dog_plan(sx, dy, yps):
    """Contorno en planta de la uña tomando el pasador (cara plana en y = y_pas − dy·d/2, chaflán en la punta–cara trasera)."""
    yF = yps - dy * d_pin / 2; yB = yF - dy * P["dog_b"]
    xT, xE = sx * KG["tipX"], sx * (KG["mouthX"] + P["L_in"])
    return [(xT, yF), (xE, yF), (xE, yB), (xT + sx * ch_dx, yB), (xT, yB + dy * min(ch_dy, P["dog_b"]))], yF, yB

# ---------------- lista de materiales ----------------
cut = lambda a, b: f"{a:.0f}×{b:.0f}"
BOM = [
    ("1", "Base (conj. soldado 1a–1e)", "1", "ASTM A572 Gr.50", M["base"] + M["rim"] + M["brackets"] + M["beds"]),
    ("1a", f"Plancha base {f(P['B'])}×{f(P['B'])}×{f(tb)} (cara de giro planitud 0,20)", "1", "ASTM A572 Gr.50", M["base"]),
    ("1b", f"Marco perimetral {f(P['rim_t'])}×{f(P['rim_h'])}", "4", "ASTM A572 Gr.50", M["rim"] / 4),
    ("1c", f"Ménsula de cilindro en caja (mejillas {f(P['t_ch'])}, orejas Ø{f(P['d_pp'])} H9)", f"{P['n_br']:.0f}", "ASTM A572 Gr.50", M["brackets"] / P["n_br"]),
    ("1d", "Punto de izaje soldable, giratorio (ver nota 9)", "4", "Comercial certificado", 3.0),
    ("1e", f"Bancada de guía {f(P['w_bed'])}×{f(P['t_bed'])}×{f(KG['L_bed'])}, ranura T: cuello {f(P['w_slot'])} H8×{f(P['h_slot'])}, cabeza {f(P['w_tee'])}×{f(P['h_tee'])}", f"{P['n_cyl']:.0f}", "ASTM A572 Gr.50", M["beds"] / P["n_cyl"]),
    ("2", "Mesa giratoria (conj. soldado 2a–2g + 3)", "1", "ASTM A572 Gr.50 – Z35", M["disc"]),
    ("3", f"Pasador de empuje Ø{f(d_pin)} m6 × {f(hd)}", f"{N_pin}", f"34CrNiMo6+QT Fy ≥ {f(P['Fy_pin'])} (3.1); contacto ind. {HRC}", M["pins"] / N_pin),
    ("4", f"Perno ISO 4762 M20×45 10.9 + arandela Ø{f(washer_D)}×10", f"{N_pin}", "10.9 / S355J2", 0.9),
    ("5", f"Pivote Ø{f(P['D_piv'])} × {f(L_piv)}", "1", "42CrMo4+QT", M["pivot"]),
    ("6", f"Buje Ø{f(d_bush)}/Ø{f(P['D_piv'])} × {f(P['L_bush'])} autolubricado", "1", "CuAl10Ni5Fe4 + grafito", 7.85e-6 * 1.07 * math.pi / 4 * (d_bush**2 - P['D_piv']**2) * P['L_bush']),
    ("7", f"Tapa retenedora Ø{f(cap_D)}×{f(cap_t)} + 4 × M10×25 ISO 10642 10.9 (avellanados)", "1", "S355J2", 7.85e-6 * math.pi / 4 * cap_D**2 * cap_t),
    ("8", f"Tapa de inspección Ø{f(cb_D - 2)}×{f(cb_t)} + 6 × M10 avellanado", "1", "S355J2", 7.85e-6 * math.pi / 4 * (cb_D - 2)**2 * cb_t),
    ("9", f"Cilindro hidr. doble efecto Ø{f(P['D_bore'])}/Ø{f(P['d_rod'])}, carrera {f(P['stroke'])}, {f(P['p_rated'])} psi", f"{P['n_cyl']:.0f}", "Comercial (ver F-03)", P["m_cyl"]),
    ("10", f"Uña deslizante {f(paw_L)}×{f(P['dog_b'])}×{f(P['dog_h'])}, cara de empuje plana templada, chaflán de retorno {P['beta_ch']:.0f}° ({f1(ch_dx)}×{f1(ch_dy)})", f"{P['n_cyl']:.0f}",
     f"34CrNiMo6+QT Re ≥ {f(P['Fy_dog'])} (3.1); cara ind. {HRC}", M["dogs"] / P["n_cyl"]),
    ("11", f"Pasador de articulación Ø{f(P['d_pp'])} f8 + placa de retención", f"{2 * P['n_cyl']:.0f}", "42CrMo4+QT", 7.85e-6 * math.pi / 4 * P['d_pp']**2 * (forkH + 20)),
    ("12", f"Resorte de retorno de la uña (compresión, carrera ≥ {f(KG['travel'] + 5)}) + tapa", f"{P['n_cyl']:.0f}", "Comercial", 0.8),
    ("13", "Faldón de sello NBR e=5 + fleje 25×4 + 36 × M8×20 A2-70", "1", "NBR 70 / S235 galv.", 6.0),
    ("14", "Grasa grafitada NLGI 2 (≥10 % grafito) + 4 graseras DIN 71412 M10×1", "≈2,5 kg", "Ver F-04", 0.2),
    ("15", "Cáncamo giratorio M30 WLL ≥ 2,5 t (izaje de la mesa, suelto) + tapón M30", "4", "Comercial", 2.2),
    ("16", f"Patín guiado {f(KG['L_s'])}×{f(P['w_s'])}, lengüeta T (cuello {f(neck_w)}, cabeza {f(head_w)}×{f(head_h)}), marco de boca e={f(P['t_fw'])}", f"{P['n_cyl']:.0f}",
     f"S460 o 34CrNiMo6+QT, Fy ≥ {f(P['Fy_shoe'])} (3.1)", M["shoes"] / P["n_cyl"]),
]

# =====================================================================
def sheet_frame(s, no, title, scale):
    s.frame(V, no, NS, title, scale, rev="B", plano=f"TT300-C-{SHEETS[no - 1]}")

def plan_base(s, T, sc, detail_cyl=True, show_hidden=True, ccw_phantom=True, balloons=True):
    """Planta del conjunto (coordenadas de modelo en mm, T: modelo → papel)."""
    B = P["B"]
    s.pline([T(p) for p in [(-B / 2, -B / 2), (B / 2, -B / 2), (B / 2, B / 2), (-B / 2, B / 2)]], "VIS", True)
    r = P["rim_t"]
    s.pline([T(p) for p in [(-B / 2 + r, -B / 2 + r), (B / 2 - r, -B / 2 + r), (B / 2 - r, B / 2 - r), (-B / 2 + r, B / 2 - r)]], "VIS", True)
    s.pline([T(p) for p in circ((0, 0), Rt)], "VIS")
    if show_hidden:
        s.pline([T(p) for p in circ((0, 0), prIn)], "OCU")
        for rr in D["almas"]:
            s.pline([T(p) for p in circ((0, 0), rr)], "OCU")
        for a in D["nervios"]:
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            s.line(T((P["D_hub"] / 2 * ca, P["D_hub"] / 2 * sa)), T((P["R_rib"] * ca, P["R_rib"] * sa)), "OCU")
        s.pline([T(p) for p in circ((0, 0), P["D_hub"] / 2)], "OCU")
    for a in D["pasadores"]:
        c = (R_pin * math.cos(math.radians(a)), R_pin * math.sin(math.radians(a)))
        s.pline([T(p) for p in circ(c, washer_D / 2, 40)], "VIS")
        s.pline([T(p) for p in circ(c, 17, 24)], "FINA")
    s.pline([T(p) for p in circ((0, 0), cb_D / 2)], "VIS")
    for k in range(6):
        a = math.radians(30 + 60 * k); s.pline([T(p) for p in circ((cb_D / 2 - 10) * 1 and ((cb_D / 2 - 10) * math.cos(a), (cb_D / 2 - 10) * math.sin(a)), 5.5, 16)], "FINA")
    s.line(T((-Rt - 60, 0)), T((Rt + 60, 0)), "EJE"); s.line(T((0, -Rt - 60)), T((0, Rt + 60)), "EJE")
    # izaje a medio lado
    cl = P["B"] / 2 - P["c_lug"]
    for (x, y) in [(P["x_lug"], cl), (-P["x_lug"], cl), (P["x_lug"], -cl), (-P["x_lug"], -cl)]:
        s.pline([T(p) for p in circ((x, y), 35, 32)], "VIS"); s.pline([T(p) for p in circ((x, y), 20, 24)], "FINA")
    for sx in (1, -1):
        X = sx * P["x_g"]
        s.pline([T(p) for p in [(X - P["w_bed"] / 2, -KG["Y_bed"]), (X + P["w_bed"] / 2, -KG["Y_bed"]), (X + P["w_bed"] / 2, KG["Y_bed"]), (X - P["w_bed"] / 2, KG["Y_bed"])]], "VIS", True)
        for wq in (P["w_slot"], P["w_tee"]):
            s.line(T((X - wq / 2, -KG["Y_bed"])), T((X - wq / 2, KG["Y_bed"])), "OCU"); s.line(T((X + wq / 2, -KG["Y_bed"])), T((X + wq / 2, KG["Y_bed"])), "OCU")
    # ménsulas
    for grp, lay in (("antihorario", "VIS"), ("horario", "FANT" if ccw_phantom else "VIS")):
        for c in D["cilindros"][grp]:
            E, ph = c["eye"], c["phiMean"]
            s.pline([T(p) for p in box_local(E, ph, -BR["rear"], P["L_ch"] - BR["rear"], -BR["Wout"] / 2, BR["Wout"] / 2)], lay, True)
            s.pline([T(p) for p in box_local(E, ph, -BR["rear"], P["L_ch"] - BR["rear"], -BR["Win"] / 2, BR["Win"] / 2)], "FINA" if lay == "VIS" else lay, True)
            s.pline([T(p) for p in circ(E, P["d_pp"] / 2, 32)], lay)
    if detail_cyl:
        for c in D["cilindros"]["antihorario"]:
            sx, dy, X, ye, yr, yps = c["side"], c["dir"], c["x"], c["eye"][1], c["rodEngage"][1], c["pinStart"][1]
            rect = lambda x0, x1, y0, y1, lay="VIS": s.pline([T(p) for p in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]], lay, True)
            yb0, yb1 = sorted([ye + dy * P["e_body"], c["rodRetracted"][1] - dy * P["c_rod"]])
            rect(X - P["D_body"] / 2, X + P["D_body"] / 2, yb0, yb1)
            yr0, yr1 = sorted([c["rodRetracted"][1] - dy * P["c_rod"], yr])
            rect(X - P["d_rod"] / 2, X + P["d_rod"] / 2, yr0, yr1)
            ys0, ys1 = sorted([yr - dy * KG["rear"], yr + dy * KG["front"]])
            rect(X - P["w_s"] / 2, X + P["w_s"] / 2, ys0, ys1)
            s.pline([T(p) for p in circ((X, yr), P["d_pp"] / 2, 30)], "VIS")
            dpts, yF, yB = dog_plan(sx, dy, yps)
            s.pline([T(p) for p in dpts], "VIS", True)
            yd0, yd1 = sorted([yF, yB])
            mx0, mx1 = sorted([sx * KG["mouthX"], sx * (P["x_g"] - P["w_s"] / 2)])
            rect(mx0, mx1, yd0 - P["t_fw"], yd1 + P["t_fw"])                       # marco de boca
            s.pline([T(p) for p in circ(c["pinStart"], d_pin / 2 + 4, 40)], "FINA")

# =====================================================================
def sheet_d01():
    s = Sheet(); sheet_frame(s, 1, "CONJUNTO GENERAL", "1:10 / 1:5 / 1:2,5")
    sc = 0.1; T = tr(178, 408, sc)
    plan_base(s, T, sc)
    s.view_title((178, 266), "PLANTA", "ESC 1:10")
    Bh = P["B"] / 2
    s.dim(T((-Bh, -Bh)), T((Bh, -Bh)), -9, f"{f(P['B'])}", "h")
    s.dim(T((Bh, -Bh)), T((Bh, Bh)), 14, f"{f(P['B'])}", "v")
    s.dim_dia(T((0, 0)), Rt * sc, 235, f"Ø{f(P['D_top'])}")
    s.dim_rad(T((0, 0)), R_pin * sc, 62, f"R{f(R_pin)} ({N_pin} pasadores Ø{f(d_pin)})")
    s.section_mark(T((-Bh - 40, 0)), 90, "A"); s.section_mark(T((Bh + 40, 0)), 90, "A")
    ca = D["cilindros"]["antihorario"][0]
    s.detail_circle(T((KG["mouthX"], ca["pinStart"][1])), 24, "B")
    yb = (ca["eye"][1] + ca["rodRetracted"][1]) / 2
    for n, p, q in [("1", (-Bh + 60, -Bh + 60), (-Bh - 120, -Bh - 100)), ("2", (-500, -500), (-1500, -1260)), ("9", (P["x_g"], yb), (1600, -900)),
                    ("16", (P["x_g"], ca["rodEngage"][1]), (1600, -300)), ("10", (KG["mouthX"] + 40, ca["pinStart"][1] - 40), (1600, 250)),
                    ("1e", (-P["x_g"], 0), (-1600, 300)), ("1c", D["cilindros"]["horario"][0]["eye"], (1600, 1300)), ("1d", (P["x_lug"], Bh - P["c_lug"]), (700, 1380))]:
        s.balloon(T(p), T(q), n)
    s.text("Cilindros y patines dibujados para giro antihorario; ménsulas en trazo fantasma: giro horario (trasladar cilindros, patines y uñas).", (40, 254), 2.3)
    # ---- corte A-A 1:5 (media sección) ----
    sc2 = 0.2; ox, oy = 40, 165
    T2 = tr(ox, oy, sc2)
    def rectz(x0, x1, z0, z1, hatch=True, lay="VIS"):
        pts = [T2((x0, z0)), T2((x1, z0)), T2((x1, z1)), T2((x0, z1))]
        s.pline(pts, lay, True)
        if hatch: s.hatch_poly(pts, scale=0.5)
    rectz(P["D_piv"] / 2, Bh, 0, tb)                            # base
    rectz(Bh - P["rim_t"], Bh, tb, tb + P["rim_h"])             # marco
    rectz(d_bush / 2, prIn, tb, tb + tbo)                       # disco inf
    rectz(prIn, Rt, tb, tb + tpr)                               # anillo inf
    rectz(hole_top / 2, prIn, tb + hd - tt, tb + hd)            # disco sup
    rectz(prIn, Rt, tb + hd - tpr, tb + hd)                     # anillo sup
    rectz(d_bush / 2, P["D_hub"] / 2, tb + tbo, z_hubtop)       # cubo
    for rr in D["almas"]:
        rectz(rr - P["t_web"] / 2, rr + P["t_web"] / 2, tb + tbo, z_hubtop)
    rectz(P["D_hub"] / 2, P["R_rib"], tb + tbo, z_hubtop, hatch=False, lay="FINA")   # nervio a 0° (no se achura)
    rectz(R_pin - d_pin / 2, R_pin + d_pin / 2, tb, tb + hd, hatch=False, lay="OCU")  # pasador detrás del plano
    rectz(0, P["D_piv"] / 2, 0, L_piv, hatch=False)               # pivote
    rectz(P["D_piv"] / 2, d_bush / 2, tb + 2, tb + 2 + P["L_bush"])   # buje
    rectz(0, cap_D / 2, L_piv, L_piv + cap_t)                     # tapa retenedora
    rectz(hole_top / 2 - 1, cb_D / 2 - 1, tb + hd - cb_t, tb + hd, hatch=True)   # tapa inspección
    s.line(T2((-10, 0)), T2((0, 0)), "VIS"); s.line(T2((0, -15)), T2((0, tb + hd + 25)), "EJE")
    s.dim(T2((Bh, 0)), T2((Bh, tb + hd)), 14, f"{f(tb + hd)}", "v")
    s.dim(T2((Rt, tb)), T2((Rt, tb + hd)), 6, f"{f(hd)}", "v")
    s.dim(T2((0, tb + hd)), T2((Rt, tb + hd)), 9, f"{f(Rt)}", "h")
    s.dim(T2((0, 0)), T2((R_pin, 0)), -8, f"R{f(R_pin)}", "h")
    s.leader(T2((Rt - 40, tb + hd)), T2((Rt + 60, tb + hd + 80)), f"Anillo de pasadores e={f(tpr)}")
    s.leader(T2((400, tb + hd)), T2((450, tb + hd + 80)), f"Plancha sup. e={f(tt)}")
    s.leader(T2((450, tb)), T2((500, -110)), f"Plancha inf. e={f(tbo)} (cara de giro)")
    s.leader(T2((650, tb / 2)), T2((700, -170)), f"Plancha base e={f(tb)}")
    s.view_title((150, 108), "CORTE A-A (media sección)", "ESC 1:5")
    # ---- detalle B: corte radial por la cara de empuje de la uña y el patín (x absoluto desde el centro), 1:2,5 ----
    sc3 = 0.4; x0d = R_pin - 140; T3 = tr(335 - x0d * sc3, 425, sc3)
    xE = P["B"] / 2; X = P["x_g"]
    section(s, T3, [(x0d, xE, 0, tb), (xE - P["rim_t"], xE, tb, tb + P["rim_h"])])
    section(s, T3, [(x0d, Rt, tb, tb + tpr)]); section(s, T3, [(x0d, Rt, tb + hd - tpr, tb + hd)])
    s.pline([T3(p) for p in [(R_pin - d_pin / 2, tb + tpr), (R_pin + d_pin / 2, tb + tpr), (R_pin + d_pin / 2, tb + hd - tpr), (R_pin - d_pin / 2, tb + hd - tpr)]], "VIS", True)
    section(s, T3, *bed_xz(X), scale=0.35, angle=90)
    section(s, T3, *shoe_xz(X, KG["mouthX"]), scale=0.5)
    section(s, T3, [(KG["tipX"], KG["mouthX"] + P["L_in"], zc - P["dog_h"] / 2, zc + P["dog_h"] / 2)], scale=0.3, angle=90)
    sp0 = KG["mouthX"] + P["L_in"]
    for k in range(6):
        xa, xb = sp0 + (KG["pocketEnd"] - sp0) * k / 6, sp0 + (KG["pocketEnd"] - sp0) * (k + 1) / 6
        s.line(T3((xa, zc - 25 if k % 2 else zc + 25)), T3((xb, zc + 25 if k % 2 else zc - 25)), "FINA")
    s.line(T3((x0d, zc)), T3((xE + 30, zc)), "EJE"); s.line(T3((R_pin, tb - 15)), T3((R_pin, tb + hd + 25)), "EJE"); s.line(T3((X, tb - 15)), T3((X, z_shoe + 20)), "EJE")
    s.dim(T3((R_pin, tb + hd + 12)), T3((KG["mouthX"], tb + hd + 12)), 10, f"{f1(KG['mouthX'] - R_pin)}", "h")
    s.dim(T3((Rt, tb + hd + 12)), T3((X, tb + hd + 12)), 22, f"{f(X - Rt)}", "h")
    s.dim(T3((x0d, 0)), T3((x0d, zc)), -10, f"eje {f(zc)}", "v")
    s.dim(T3((X + P["w_s"] / 2, zb)), T3((X + P["w_s"] / 2, z_shoe)), 8, f"{f(Hs)}", "v")
    s.dim(T3((xE, 0)), T3((xE, zb)), 8, f"{f(zb)}", "v")
    s.dim(T3((KG["tipX"], tb + tpr - 2)), T3((KG["mouthX"] + P["L_in"], tb + tpr - 2)), -8, f"uña {f(paw_L)}", "h")
    s.leader(T3((KG["tipX"] + 30, zc + P["dog_h"] / 2)), T3((KG["tipX"] - 40, tb + hd + 70)), f"Uña pos 10 ({f(P['dog_b'])}×{f(P['dog_h'])}), cara de empuje plana {HRC}")
    s.leader(T3((X + 40, z_shoe)), T3((X + 60, tb + hd + 70)), f"Patín pos 16 (marco e={f(P['t_fw'])})")
    s.leader(T3((X - P["w_tee"] / 2 + 4, zT0 + 4)), T3((X - 140, -45)), f"Ranura T bancada 1e: {f(P['w_slot'])} H8×{f(P['h_slot'])} + {f(P['w_tee'])}×{f(P['h_tee'])}, fondo {f(fondo)}")
    s.leader(T3((X + head_w / 2 - 3, zT0 + 6)), T3((X + 60, -75)), f"Lengüeta T: cuello {f(neck_w)}, cabeza {f(head_w)}×{f(head_h)}")
    s.leader(T3(((sp0 + KG["pocketEnd"]) / 2, zc + 25)), T3((sp0 + 60, tb + hd + 110)), f"Resorte pos 12 (retorno {f(KG['travel'])})")
    s.text(f"Al retraer, el chaflán de retorno ({P['beta_ch']:.0f}°) toca el pasador siguiente: la uña se retrae {f(KG['travel'])} mm hacia afuera y el resorte la devuelve.", (330, 416), 2.2)
    s.view_title((452, 404), "DETALLE B (corte radial por la uña y el patín)", "ESC 1:2,5")
    # ---- datos técnicos ----
    c = {x["id"]: x for x in DV["casos"]}
    rows = [["Capacidad nominal (WLL)", f"{f(P['W_tf'])} tf ({f(DV['W'])} kN)"], ["Excentricidad máx. del CG", f"{f(P['e'])} mm"],
            ["Diámetro de mesa / apoyo de carga", f"Ø{f(P['D_top'])} / Ø{f(P['D_load'])}"], ["Dimensiones en planta / alto", f"{f(P['B'])} × {f(P['B'])} / {f(tb + hd)} mm"],
            ["Masa total (sin carga)", f"{f(M['total'])} kg (mesa {f(M['disc'] + M['pivot'])} kg)"],
            ["Accionamiento", f"{P['n_cyl']:.0f} cil. Ø{f(P['D_bore'])}/Ø{f(P['d_rod'])}, carrera {f(P['stroke'])}, patín guiado (K = {DV['Kguide']:.2f})".replace(".", ",")],
            ["Giro por carrera / ciclos por vuelta", f"{360 / N_pin:.2f}° / {N_pin}".replace(".", ",")],
            ["F de diseño por cilindro (μ 0,20)", f"{f1(c['dis']['F'])} kN · {f(c['dis']['p'])} bar"],
            ["F de calado (alivio {0} bar)".format(f(P['p_relief'])), f"{f1(DV['Fstall'])} kN · FS {c['dis']['FS']:.2f}".replace(".", ",")],
            ["Presión nominal esperada (μ 0,15)", f"{f(c['nom']['p'])} bar"], ["Alarma / detención", f"{f(P['p_alarm'])} bar"],
            ["Presión de contacto máx. interfaz", f"{DV['q_max']:.2f} MPa".replace(".", ",")], ["Tiempo por vuelta (bomba {0} L/min)".format(f1(P['Q_pump'])), f"{f(DV['tRev'])} min"]]
    s.text("DATOS TÉCNICOS", (312, 228), 3.5, bold=True)
    yt = s.table(312, 224, [("Ítem", 78, "L"), ("Valor", 72, "L")], rows, rh=5.0, h=2.2)
    # ---- notas generales ----
    notas = [
        "NOTAS GENERALES",
        f"1. Capacidad nominal {f(P['W_tf'])} tf; excentricidad del CG ≤ {f(P['e'])} mm; carga solo sobre parrilla de reparto Ø{f(P['D_load'])} o ≥ 8 apoyos simétricos.",
        "2. Normas: AISC 360-22 (ASD); ASME BTH-1 Cat. de diseño B (Nd = 3,0) para la cadena de empuje; AWS D1.1/D1.1M:2020; ISO 2768-mK; ISO 1101.",
        f"3. Materiales con certificado EN 10204 3.1; planchas de la mesa UT ASTM A578 nivel B, Z35. Uñas 10 y pasadores 3: contacto templado {HRC}, prof. ≥ {f1(z_hard)} mm.",
        "4. Soldadura con WPS/PQR calificados AWS D1.1, E7018 / ER70S-6. Programa de soldaduras, END y precalentamiento en F-04.",
        "5. Interfaz de giro acero-acero con grasa grafitada (pos 14) en ambas caras; lubricar antes de cada operación. Acero seco no gira.",
        f"6. Cadena de empuje verificada a la fuerza de calado {f1(DV['Fstall'])} kN (alivio {f(P['p_relief'])} bar). Prohibido subir el alivio.",
        "7. Operar siempre con ambos cilindros en par (circuito en paralelo, válvula de bloqueo). Prohibido empujar con un solo cilindro.",
        f"8. Detener y relubricar si la presión supera {f(P['p_alarm'])} bar. Ensayo de aceptación y operación en F-04.",
        f"9. Puntos de izaje pos 1d: comerciales soldables certificados, WLL ≥ {M['total'] * P['phi_lift'] / (3 * math.sin(math.radians(60))) / 1000:.1f} t c/u (eslinga 4 ramales, 60°).".replace(".", ",", 1),
        "10. Sin requerimiento sísmico (decisión del mandante). Para instalación permanente, verificar con NCh2369 en la herramienta (Ch).",
        "11. Verificaciones completas en D-02 y en la herramienta TT300-C_Verificacion.html (misma fuente de datos).",
    ]
    s.mtext(notas, (312, yt - 6), 2.15, 1.55, bold_first=True)
    # ---- lista de materiales ----
    s.text("LISTA DE MATERIALES", (560, 584 - 6), 3.5, bold=True)
    rows = [[n, d, q, m, f1(kg)] for (n, d, q, m, kg) in BOM]
    y = s.table(560, 584 - 9, [("Pos", 10, "C"), ("Descripción", 140, "L"), ("Cant.", 14, "C"), ("Material", 72, "L"), ("kg/u", 30, "R")], rows, rh=5.2, h=2.1)
    s.text(f"Masa total del conjunto ≈ {f(M['total'])} kg (acero, sin soldadura ni pintura: agregar ≈ 2 %).", (560, y - 4), 2.2)
    return s

# =====================================================================
def sheet_d02():
    s = Sheet(); sheet_frame(s, 2, "BASES DE CÁLCULO Y VERIFICACIONES", "S/E")
    s.text("HIPÓTESIS", (30, 576), 3.5, bold=True)
    hip = [["H1", f"W = {f(P['W_tf'])} tf = {f(DV['W'])} kN; N = W + W_mesa = {f(DV['N'])} kN; φd = {P['phi_d']:.2f} solo en resistencias".replace(".", ",", 1)],
           ["H2", f"Interfaz plana anular acero/acero con grasa grafitada; μ diseño {P['mu_d']:.2f}, nominal {P['mu_nom']:.2f}, contaminado {P['mu_cont']:.2f}".replace(".", ",")],
           ["H3", f"Radio efectivo de diseño r_ef = {f(P['r_ef'])} mm; se verifica además contacto en el borde r = {f(Rt)} mm"],
           ["H4", f"Uña de cara plana en patín guiado (ranura T); empuje paralelo a la guía; brazo mín. {f1(DV['K']['armMin'])} mm; μg = {P['mu_g']:.2f}, μ cara = {P['mu_s']:.2f}".replace("0.", "0,")],
           ["H5", f"Cadena de empuje a fuerza de calado {f1(DV['Fstall'])} kN; ASME BTH-1 Cat. B, Nd = {P['Nd']:.1f}".replace(".", ",")],
           ["H6", f"Estructura AISC 360-22 ASD; FEA MITC4 de la mesa × k_malla {P['kFEA']:.2f}; flexión global axisimétrica sumada".replace(".", ",")],
           ["H7", "Base delgada apoyada en losa o mats rígidos: la presión en la losa ≈ presión de contacto (verificar por terceros)"],
           ["H8", "Sin requerimiento sísmico (decisión del mandante, 31-10-2026); base t ≥ {0} mm por planitud".format(f(P.get("t_base_min", 16)))]]
    y = s.table(30, 572, [("Id", 10, "C"), ("Hipótesis", 250, "L")], hip, rh=5.0, h=2.2)
    s.text("CASOS DE ACCIONAMIENTO", (30, y - 6), 3.5, bold=True)
    rows = [[x["nombre"], f"{x['mu']:.2f}", f(x['r']), f1(x['T']), f1(x['F']), f(x['p']), f"{x['FS']:.2f}", "Gira" if x['gira'] else "No gira"] for x in DV["casos"]]
    rows = [[r[0]] + [v.replace(".", ",") for v in r[1:]] for r in rows]
    y = s.table(30, y - 10, [("Caso", 112, "L"), ("μ", 14, "R"), ("r mm", 18, "R"), ("T kN·m", 20, "R"), ("F/cil kN", 20, "R"), ("p bar", 18, "R"), ("FS", 14, "R"), ("", 22, "C")], rows, rh=5.0, h=2.1)
    K = DV["K"]
    s.text("CINEMÁTICA", (30, y - 6), 3.5, bold=True)
    kin = [["Brazo mín. (R·cos π/N) / máx.", f"{f1(K['armMin'])} / {f1(K['armMax'])} mm"],
           ["Carrera requerida / disponible / margen", f"{f1(K['s_req'])} / {f(P['stroke'])} / {f1(K['margin'])} mm"], ["Cuerda / hueco entre pasadores", f"{f1(K['chord'])} / {f1(K['gap'])} mm"],
           ["Δ guía–pasador / Lg / K", f"{f1(K['DeltaMax'])} / {f1(K['Lg'])} mm / {DV['Kguide']:.3f}"], ["Reacción de guía a calado", f"{f1(DV['Rguide'])} kN"],
           ["Voladizo de la uña / retorno radial", f"{f1(K['lever'])} / {f1(K['travel'])} mm"]]
    kin = [[a, b.replace(".", ",")] for a, b in kin]
    s.table(30, y - 10, [("Magnitud", 80, "L"), ("Valor", 60, "L")], kin, rh=5.0, h=2.1)
    s.text("FÓRMULAS", (190, y - 6), 3.5, bold=True)
    s.mtext(["(1) T = μ·N·r + T_piv;  T_piv = μ_buje·H·D_piv/2;  H = μ·N·e·(4/3)(R³−r³)/(R⁴−r⁴)",
             "(2) brazo(θ) = R_pas·cos θ, θ ∈ [−π/N, +π/N];  F_cil·η = F_pas(1 + μg(|r_f| + |r_r|)), fricción μ_s·F_pas en la cara plana;  Lg = 2/3·L_patín",
             "(3) F_cil = K·T / (n·brazo_mín);  p = F_cil / A;  FS = A·p_alivio / F_cil",
             "(4) carrera = libre + 2·R_pas·sen(π/N);  reacción de guía R = [F·Δ + H·(y_c − y_r)]/Lg",
             "(5) q_máx = N_D/A·(1 + 4eR/(R²+r²))",
             "(6) μ_real (ensayo) = (n·p·A·brazo_mín/K − T_piv)/(N·r_ef)"], (190, y - 10), 2.2, 1.7)
    # verificaciones en dos columnas
    ver = [v for v in D["verificaciones"]]
    est = {"ok": "Cumple", "warn": "Monit.", "fail": "NO", "info": "Info", "pend": "Pend."}
    rows = []
    for v in ver:
        dem = "—" if v.get("dem") is None else (f"{v['dem']:.3g}" if abs(v['dem']) < 1e3 else f"{v['dem']:.0f}")
        cap = "" if v.get("cap") is None else (f"{v['cap']:.3g}" if abs(v['cap']) < 1e3 else f"{v['cap']:.0f}")
        fu = "" if v.get("fu") is None else f"{v['fu']:.2f}"
        rows.append([v["grp"][:18], v["nombre"][:52], dem.replace(".", ","), cap.replace(".", ","), (v.get("unidad") or "")[:5], fu.replace(".", ","), est[v["estado"]], v["ref"][:44]])
    s.text("VERIFICACIONES (exportadas por el núcleo de cálculo)", (330, 576), 3.5, bold=True)
    cols = [("Grupo", 34, "L"), ("Verificación", 92, "L"), ("Dem.", 16, "R"), ("Cap.", 16, "R"), ("Ud.", 10, "C"), ("FU", 12, "R"), ("Est.", 14, "C"), ("Referencia", 70, "L")]
    half = len(rows)
    y = s.table(330, 572, cols, rows[:half], rh=4.4, h=1.85)
    if len(rows) > half:
        s.text("(continúa en la columna inferior)", (330, y - 3), 2.0)
        s.table(30, 200 if len(rows) - half < 30 else 230, cols, rows[half:], rh=4.4, h=1.85)
    s.text(f"Veredicto: GIRA = {'SÍ' if D['verdict']['gira'] else 'NO'} · ESTRUCTURA = {'CUMPLE' if D['verdict']['estructura'] else 'NO CUMPLE'} · FU máx {D['verdict']['fuMax']:.2f} · pendientes {D['verdict']['pend']}".replace(".", ","), (330, 80), 3.0, bold=True)
    s.text("FU ≤ 0,90 cumple; 0,90–1,00 monitoreo; > 1,00 no cumple. Chequeos de giro y geométricos: límites con margen propio (FU ≤ 1,00).", (330, 75), 2.2)
    return s

# =====================================================================
def sheet_f01():
    s = Sheet(); sheet_frame(s, 3, "MESA GIRATORIA (POS 2) – CONJUNTO SOLDADO", "1:10 / 1:4 / 1:2")
    sc = 0.1; T = tr(160, 420, sc)
    s.pline([T(p) for p in circ((0, 0), Rt)], "VIS"); s.pline([T(p) for p in circ((0, 0), prIn)], "VIS")
    for rr in D["almas"]:
        s.pline([T(p) for p in circ((0, 0), rr - P["t_web"] / 2)], "VIS"); s.pline([T(p) for p in circ((0, 0), rr + P["t_web"] / 2)], "VIS")
    for a in D["nervios"]:
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a)); na, nb = -sa * P["t_rib"] / 2, ca * P["t_rib"] / 2
        for sg in (-1, 1):
            s.line(T((P["D_hub"] / 2 * ca + sg * na, P["D_hub"] / 2 * sa + sg * nb)), T((P["R_rib"] * ca + sg * na, P["R_rib"] * sa + sg * nb)), "VIS")
    s.pline([T(p) for p in circ((0, 0), P["D_hub"] / 2)], "VIS"); s.pline([T(p) for p in circ((0, 0), d_bush / 2)], "VIS")
    for a in D["pasadores"]:
        c = (R_pin * math.cos(math.radians(a)), R_pin * math.sin(math.radians(a)))
        s.pline([T(p) for p in circ(c, d_pin / 2, 40)], "VIS")
    for k in range(4):
        a = math.radians(45 + 90 * k); c = ((prIn + Rt) / 2 * math.cos(a) * 0 + (R_pin - 120) * math.cos(a), (R_pin - 120) * math.sin(a))
    s.line(T((-Rt - 50, 0)), T((Rt + 50, 0)), "EJE"); s.line(T((0, -Rt - 50)), T((0, Rt + 50)), "EJE")
    s.view_title((160, 304), "PLANTA SIN PLANCHA SUPERIOR", "ESC 1:10")
    s.dim_dia(T((0, 0)), Rt * sc, 130, f"Ø{f(P['D_top'])}")
    s.dim_dia(T((0, 0)), prIn * sc, 200, f"Ø{f(2 * prIn)} (anillos)")
    for i, rr in enumerate(D["almas"]):
        s.dim_rad(T((0, 0)), rr * sc, -20 - 18 * i, f"R{f(rr)} (alma e={f(P['t_web'])})")
    s.text(f"{int(P['N_rib'])} nervios e={f(P['t_rib'])} a {360 / P['N_rib']:.2f}°, de R{f(P['D_hub'] / 2)} a R{f(P['R_rib'])}".replace(".", ","), (70, 292), 2.4)
    s.text(f"{N_pin} pasadores Ø{f(d_pin)} H7/m6 en R{f(R_pin)}, el primero a {180 / N_pin:.3f}° del eje X, paso {360 / N_pin:.3f}°".replace(".", ","), (70, 288), 2.4)
    # corte radial 1:4
    sc2 = 0.25; T2 = tr(40, 190, sc2)
    def rz(x0, x1, z0, z1, hatch=True, lay="VIS"):
        pts = [T2((x0, z0)), T2((x1, z0)), T2((x1, z1)), T2((x0, z1))]
        s.pline(pts, lay, True)
        if hatch: s.hatch_poly(pts, scale=0.5)
    z0 = 0
    rz(d_bush / 2, prIn, z0, tbo); rz(prIn, Rt, z0, tpr); rz(hole_top / 2, prIn, hd - tt, hd); rz(prIn, Rt, hd - tpr, hd)
    rz(d_bush / 2, P["D_hub"] / 2, tbo, hd - tt)
    for rr in D["almas"]:
        rz(rr - P["t_web"] / 2, rr + P["t_web"] / 2, tbo, hd - tt)
    rz(P["D_hub"] / 2, P["R_rib"], tbo, hd - tt, hatch=False, lay="FINA")
    rz(R_pin - d_pin / 2, R_pin + d_pin / 2, 0, hd, hatch=False, lay="OCU")
    s.line(T2((0, -10)), T2((0, hd + 20)), "EJE")
    s.dim(T2((Rt, 0)), T2((Rt, hd)), 8, f"{f(hd)}", "v")
    s.dim(T2((prIn, hd)), T2((Rt, hd)), 8, f"{f(Rt - prIn)}", "h")
    s.dim(T2((0, 0)), T2((prIn, 0)), -8, f"R{f(prIn)}", "h")
    s.dim(T2((prIn + 20, 0)), T2((prIn + 20, tpr)), -4, f"{f(tpr)}", "v", outside=True)
    s.dim(T2((hole_top / 2, hd - tt)), T2((hole_top / 2, hd)), -4, f"{f(tt)}", "v", outside=True)
    s.dim(T2((d_bush / 2 + 8, 0)), T2((d_bush / 2 + 8, tbo)), 4, f"{f(tbo)}", "v", outside=True)
    s.weld(T2((D["almas"][1] - P["t_web"] / 2, tbo)), T2((D["almas"][1] - 120, -90)), "fillet", f"{f(P['w_web'])}", other=True, note="W7 típ.")
    s.weld(T2((prIn, tbo)), T2((prIn - 60, -140)), "cjp", f"t={f(tbo)}", note="W5 UT")
    s.weld(T2((prIn, hd - tt)), T2((prIn - 80, hd + 110)), "cjp", f"t={f(tt)}", note="W5 UT")
    s.view_title((170, 130), "CORTE RADIAL (por un nervio)", "ESC 1:4")
    # detalle C: pasador 1:2
    sc3 = 0.5; T3 = tr(420, 380, sc3)
    def rz3(x0, x1, z0, z1, hatch=True, lay="VIS"):
        pts = [T3((x0, z0)), T3((x1, z0)), T3((x1, z1)), T3((x0, z1))]
        s.pline(pts, lay, True)
        if hatch: s.hatch_poly(pts, scale=0.4)
    rz3(-130, -d_pin / 2, 0, tpr); rz3(d_pin / 2, Rt - R_pin, 0, tpr); rz3(-130, -d_pin / 2, hd - tpr, hd); rz3(d_pin / 2, Rt - R_pin, hd - tpr, hd)
    rz3(-d_pin / 2, d_pin / 2, 0, hd, hatch=False)
    rz3(-11, 11, hd - 40, hd, hatch=False, lay="OCU")
    rz3(-washer_D / 2, washer_D / 2, hd, hd + 10, hatch=False)
    rz3(-15, 15, hd + 10, hd + 30, hatch=False)
    s.line(T3((0, -15)), T3((0, hd + 45)), "EJE")
    s.dim(T3((-d_pin / 2, -5)), T3((d_pin / 2, -5)), -6, f"Ø{f(d_pin)} H7/m6", "h")
    s.dim(T3((Rt - R_pin, 0)), T3((Rt - R_pin, hd)), 8, f"{f(hd)}", "v")
    s.dim(T3((-washer_D / 2, hd + 10)), T3((washer_D / 2, hd + 10)), 22, f"Ø{f(washer_D)}", "h")
    s.leader(T3((0, hd + 30)), T3((70, hd + 70)), "Perno ISO 4762 M20×45 10.9 (pos 4)")
    s.leader(T3((-50, hd + 5)), T3((-150, hd + 50)), "Arandela Ø{0}×10 S355 (pos 4)".format(f(washer_D)))
    s.leader(T3((0, hd - 25)), T3((-160, hd - 60)), "Rosca M20 prof. 40 en pasador")
    zh0, zh1 = max(tpr, zc - tb - P["dog_h"] / 2 - 5), min(hd - tpr, zc - tb + P["dog_h"] / 2 + 5)   # franja de contacto con la uña
    for sg in (-1, 1):
        s.line(T3((sg * (d_pin / 2 + 3), zh0)), T3((sg * (d_pin / 2 + 3), zh1)), "EJE")
    s.dim(T3((-d_pin / 2 - 3, zh0)), T3((-d_pin / 2 - 3, zh1)), -6, f"{f(zh1 - zh0)}", "v")
    s.dim(T3((-d_pin / 2 - 3, 0)), T3((-d_pin / 2 - 3, zh0)), -18, f"{f(zh0)}", "v")
    s.leader(T3((d_pin / 2 + 3, hd / 2)), T3((140, hd / 2 + 40)), f"Contacto de la uña: cara plana templada (sin asiento)")
    s.text(f"Franja de contacto: temple por inducción {HRC}, prof. efectiva ≥ {f1(z_hard)} mm, toda la circunferencia", T3((70 + 0, hd / 2 + 26)), 2.2)
    s.finish(T3((-100, tpr)), "Ra 1,6")
    s.text("Agujeros Ø{0} H7 escariados en línea en ambos anillos después del alivio de tensiones; coaxialidad 0,05.".format(f(d_pin)), (360, 300), 2.2)
    s.text("Pasador a ras con la cara inferior (cara de giro): −0,5/0 mm. Sin soldadura: reemplazable.", (360, 296), 2.2)
    s.view_title((430, 310), "DETALLE C – PASADOR DE EMPUJE", "ESC 1:2")
    # detalle L: ranuras de lubricación (vista inferior de 2c/2d), 1:20
    sc5 = 0.05; T5 = tr(470, 165, sc5)
    s.pline([T5(p) for p in circ((0, 0), Rt)], "VIS"); s.pline([T5(p) for p in circ((0, 0), d_bush / 2)], "VIS")
    for a in D["pasadores"]:
        c = (R_pin * math.cos(math.radians(a)), R_pin * math.sin(math.radians(a)))
        s.pline([T5(p) for p in circ(c, d_pin / 2, 16)], "FINA")
    r_g0, r_g1 = d_bush / 2 + 50, R_pin - d_pin / 2 - 40
    for k in range(12):
        a = math.radians(15 + 30 * k)
        s.line(T5((r_g0 * math.cos(a), r_g0 * math.sin(a))), T5((r_g1 * math.cos(a), r_g1 * math.sin(a))), "VIS")
    gr = [round(r_g0 + 0.25 * (r_g1 - r_g0)), round(r_g0 + 0.6 * (r_g1 - r_g0)), round(r_g1)]
    for r in gr:
        s.pline([T5(p) for p in circ((0, 0), r)], "VIS")
    for k in range(4):
        a = math.radians(45 + 90 * k)
        s.line(T5((r_g1 * math.cos(a), r_g1 * math.sin(a))), T5((Rt * math.cos(a), Rt * math.sin(a))), "OCU")
    s.view_title((470, 105), "DETALLE L – RANURAS DE LUBRICACIÓN (vista inferior)", "ESC 1:20")
    s.text(f"12 radiales a 15° + 30°k de R{f(r_g0)} a R{f(r_g1)}; circunferenciales R" + " / R".join(f(r) for r in gr) + "; sección R3 × 2 prof.;", (420, 95), 2.2)
    s.text("4 graseras M10×1 en el canto (45° + 90°k), taladro Ø6 a la ranura exterior (oculto). Ranuras entre nervios: no cruzar soldaduras.", (420, 91), 2.2)
    # despiece
    rings = D["almas"]
    hub_m = 7.85e-6 * math.pi / 4 * (P["D_hub"]**2 - d_bush**2) * hw
    dsp = [["2a", f"Disco central superior Ø{f(2 * prIn)}×{f(tt)}; Ø{f(hole_top)} + rebaje Ø{f(cb_D)}×{f(cb_t)}; 4 × M30", "1", f1(7.85e-6 * math.pi / 4 * ((2 * prIn)**2 - hole_top**2) * tt)],
           ["2b", f"Anillo superior Ø{f(P['D_top'])}/Ø{f(2 * prIn)}×{f(tpr)} (4 segm. CJP); {N_pin} × Ø{f(d_pin)} H7", "1", f1(7.85e-6 * (math.pi / 4 * (P['D_top']**2 - (2 * prIn)**2) - N_pin * math.pi / 4 * d_pin**2) * tpr)],
           ["2c", f"Disco central inferior Ø{f(2 * prIn)}×{f(tbo)}; Ø{f(d_bush)}; ranuras de lubricación", "1", f1(7.85e-6 * math.pi / 4 * ((2 * prIn)**2 - d_bush**2) * tbo)],
           ["2d", f"Anillo inferior Ø{f(P['D_top'])}/Ø{f(2 * prIn)}×{f(tpr)} (4 segm. CJP); {N_pin} × Ø{f(d_pin)} H7", "1", f1(7.85e-6 * (math.pi / 4 * (P['D_top']**2 - (2 * prIn)**2) - N_pin * math.pi / 4 * d_pin**2) * tpr)],
           ["2e", f"Almas anulares e={f(P['t_web'])} h={f(hw)} roladas, R " + " / ".join(f(r) for r in rings), f"{len(rings)}", f1(M["webs"])],
           ["2f", f"Nervios radiales e={f(P['t_rib'])} h={f(hw)} (tramos entre almas)", f"{int(P['N_rib'])}×{len([r for r in rings if r < P['R_rib']]) + 0}", f1(M["ribs"])],
           ["2g", f"Cubo Ø{f(P['D_hub'])}/Ø{f(d_bush)} H7 × {f(hw)} (forja S355J2+N)", "1", f1(hub_m)]]
    s.text("DESPIECE POS 2", (560, 584 - 6), 3.5, bold=True)
    y = s.table(560, 584 - 9, [("Sub", 10, "C"), ("Descripción", 196, "L"), ("Cant.", 18, "C"), ("kg", 18, "R")], dsp, rh=5.4, h=2.1)
    nf = ["NOTAS DE FABRICACIÓN – MESA",
          "1. Secuencia: almas y nervios sobre disco inferior 2c (W7, W8) → cubo 2g (W6) → anillo 2d (W5) →",
          "   disco superior 2a por cuadrantes opuestos (W9 en ranura, W6) → anillo 2b (W5).",
          "2. Alivio de tensiones 590–620 °C antes del mecanizado final.",
          f"3. Mecanizar cara inferior completa (2c + 2d): planitud 0,20 en Ø{f(P['D_top'])}, Ra 1,6–3,2; refrentar cara superior: paralelismo 0,30.",
          f"4. Escariar Ø{f(d_bush)} H7 del cubo perpendicular a la cara inferior 0,05; prensar buje pos 6 (H7/s6).",
          f"5. Escariar {N_pin} agujeros Ø{f(d_pin)} H7 en ambos anillos en un mismo montaje; PCD {f(2 * R_pin)} ±0,3, paso ±0,05°.",
          "6. Ranuras de lubricación en cara inferior (12 radiales c/30° + 3 circunferenciales), sección R3×2, Ra 1,6, después del refrentado;",
          "   4 graseras M10×1 en el canto del anillo inferior a 45° + 90°k con taladro Ø6 a la ranura exterior.",
          "7. 4 × M30 prof. 45 en 2a a R{0} (45°+90°k) para cáncamos pos 15; tapones a ras en operación.".format(f(prIn - 120)),
          "8. Placa de la carga: superficie superior granallada; sin pintura en cara inferior, agujeros y alojamientos."]
    s.mtext(nf, (560, y - 8), 2.15, 1.55, bold_first=True)
    return s

# =====================================================================
def sheet_f02():
    s = Sheet(); sheet_frame(s, 4, "BASE (POS 1) Y MÉNSULAS DE CILINDRO", "1:10 / 1:4")
    sc = 0.1; T = tr(170, 422, sc)
    B = P["B"]; Bh = B / 2
    s.pline([T(p) for p in [(-Bh, -Bh), (Bh, -Bh), (Bh, Bh), (-Bh, Bh)]], "VIS", True)
    s.pline([T(p) for p in [(-Bh + P['rim_t'], -Bh + P['rim_t']), (Bh - P['rim_t'], -Bh + P['rim_t']), (Bh - P['rim_t'], Bh - P['rim_t']), (-Bh + P['rim_t'], Bh - P['rim_t'])]], "VIS", True)
    s.pline([T(p) for p in circ((0, 0), Rt)], "FANT")
    s.pline([T(p) for p in circ((0, 0), P["D_piv"] / 2)], "VIS")
    for grp in ("horario", "antihorario"):
        for c in D["cilindros"][grp]:
            E, ph = c["eye"], c["phiMean"]
            s.pline([T(p) for p in box_local(E, ph, -BR["rear"], P["L_ch"] - BR["rear"], -BR["Wout"] / 2, BR["Wout"] / 2)], "VIS", True)
            s.pline([T(p) for p in box_local(E, ph, -BR["rear"], P["L_ch"] - BR["rear"], -BR["Win"] / 2, BR["Win"] / 2)], "VIS", True)
            s.pline([T(p) for p in box_local(E, ph, -BR["rear"], Llug - BR["rear"], -BR["Wout"] / 2, BR["Wout"] / 2)], "FINA", True)
            s.pline([T(p) for p in circ(E, P["d_pp"] / 2, 32)], "VIS"); s.centerlines(T(E), P["d_pp"] / 2 * sc, 2)
            s.text(f"{'H' if grp == 'horario' else 'AH'}", T((E[0] - (230 if E[0] > 0 else -230), E[1])), 2.6, "MIDDLE_CENTER", bold=True)
    cl = Bh - P["c_lug"]
    for (x, y) in [(P["x_lug"], cl), (-P["x_lug"], cl), (P["x_lug"], -cl), (-P["x_lug"], -cl)]:
        s.pline([T(p) for p in circ((x, y), 35, 32)], "VIS")
    for sx in (1, -1):
        X = sx * P["x_g"]
        s.pline([T(p) for p in [(X - P["w_bed"] / 2, -KG["Y_bed"]), (X + P["w_bed"] / 2, -KG["Y_bed"]), (X + P["w_bed"] / 2, KG["Y_bed"]), (X - P["w_bed"] / 2, KG["Y_bed"])]], "VIS", True)
        s.line(T((X - P["w_slot"] / 2, -KG["Y_bed"])), T((X - P["w_slot"] / 2, KG["Y_bed"])), "VIS"); s.line(T((X + P["w_slot"] / 2, -KG["Y_bed"])), T((X + P["w_slot"] / 2, KG["Y_bed"])), "VIS")
        s.line(T((X - P["w_tee"] / 2, -KG["Y_bed"])), T((X - P["w_tee"] / 2, KG["Y_bed"])), "OCU"); s.line(T((X + P["w_tee"] / 2, -KG["Y_bed"])), T((X + P["w_tee"] / 2, KG["Y_bed"])), "OCU")
        s.line(T((X, -Bh - 30)), T((X, Bh + 30)), "EJE")
    s.section_mark(T((P["x_g"] - 150, 300)), 90, "E"); s.section_mark(T((P["x_g"] + 150, 300)), 90, "E")
    s.line(T((-Bh - 40, 0)), T((Bh + 40, 0)), "EJE"); s.line(T((0, -Bh - 40)), T((0, Bh + 40)), "EJE")
    s.dim(T((-Bh, -Bh)), T((Bh, -Bh)), -9, f"{f(B)}", "h"); s.dim(T((Bh, -Bh)), T((Bh, Bh)), 9, f"{f(B)}", "v")
    s.dim(T((0, Bh)), T((P["x_g"], Bh)), 8, f"{f(P['x_g'])}", "h")
    s.dim(T((Bh, 0)), T((Bh, -abs(KG["y_eye"]))), 18, f"{f(abs(KG['y_eye']))}", "v")
    s.dim(T((P["x_g"] + P["w_bed"] / 2, -KG["Y_bed"])), T((P["x_g"] + P["w_bed"] / 2, KG["Y_bed"])), 6, f"{f(KG['L_bed'])}", "v")
    s.dim(T((0, Bh)), T((P["x_lug"], Bh)), 9, f"{f(P['x_lug'])}", "h")
    s.text("H: ménsulas para giro horario · AH: giro antihorario (ejes de ménsula paralelos a Y, coaxiales con la guía).", (40, 270), 2.2)
    s.text(f"Guías y ojales en x = ±{f(P['x_g'])}; ojales en y = ±{f(abs(KG['y_eye']))}; pivote Ø{f(P['D_piv'])} H7/p6 al centro; puntos de izaje 1d en x = ±{f(P['x_lug'])}, a {f(P['c_lug'])} del borde.", (40, 266), 2.2)
    s.view_title((170, 282), "PLANTA BASE", "ESC 1:10")
    # detalle ménsula 1:4 (local: x hacia el cilindro)
    sc2 = 0.25
    Tp = tr(470, 470, sc2)
    x0, x1 = -BR["rear"], P["L_ch"] - BR["rear"]
    for yy in (-BR["Wout"] / 2, -BR["Win"] / 2, BR["Win"] / 2, BR["Wout"] / 2):
        s.line(Tp((x0, yy)), Tp((x1, yy)), "VIS")
    s.line(Tp((x0, -BR["Wout"] / 2)), Tp((x0, BR["Wout"] / 2)), "VIS"); s.line(Tp((x1, -BR["Wout"] / 2)), Tp((x1, -BR["Win"] / 2)), "VIS"); s.line(Tp((x1, BR["Win"] / 2)), Tp((x1, BR["Wout"] / 2)), "VIS")
    s.pline([Tp(p) for p in [(x0, -BR["Win"] / 2), (Llug - BR["rear"], -BR["Win"] / 2), (Llug - BR["rear"], BR["Win"] / 2), (x0, BR["Win"] / 2)]], "VIS", True)
    s.pline([Tp(p) for p in circ((0, 0), P["d_pp"] / 2, 40)], "VIS"); s.centerlines(Tp((0, 0)), P["d_pp"] / 2 * sc2, 3)
    s.line(Tp((x0 - 20, 0)), Tp((x1 + 30, 0)), "EJE")
    s.dim(Tp((x0, BR["Wout"] / 2)), Tp((x1, BR["Wout"] / 2)), 8, f"{f(P['L_ch'])}", "h")
    s.dim(Tp((x0, BR["Wout"] / 2)), Tp((0, BR["Wout"] / 2)), 14, f"{f(BR['rear'])}", "h")
    s.dim(Tp((x1, -BR["Win"] / 2)), Tp((x1, BR["Win"] / 2)), 8, f"{f(BR['Win'])}", "v")
    s.dim(Tp((x1, -BR["Wout"] / 2)), Tp((x1, BR["Wout"] / 2)), 18, f"{f(BR['Wout'])}", "v")
    s.dim(Tp((x0, -BR["Wout"] / 2)), Tp((Llug - BR["rear"], -BR["Wout"] / 2)), -8, f"{f(Llug)}", "h")
    s.leader(Tp((0, P["d_pp"] / 2)), Tp((-90, 150)), f"Ø{f(P['d_pp'])} H9 (en orejas sup. e inf.)")
    s.view_title((500, 418), "MÉNSULA 1c – PLANTA", "ESC 1:4")
    Te = tr(470, 330, sc2)
    rect = lambda a, b, c, d, h=True: (s.pline([Te((a, c)), Te((b, c)), Te((b, d)), Te((a, d))], "VIS", True), h and s.hatch_poly([Te((a, c)), Te((b, c)), Te((b, d)), Te((a, d))], scale=0.4))
    rect(x0 - 60, x1 + 60, -tb, 0)
    s.pline([Te((x0, 0)), Te((x1, 0)), Te((x1, BR["H"])), Te((x0, BR["H"]))], "VIS", True)
    s.pline([Te((x0, BR["spacer"] + P["t_ch"])), Te((Llug - BR["rear"], BR["spacer"] + P["t_ch"]))], "OCU")
    s.pline([Te((x0, BR["H"] - P["t_ch"])), Te((Llug - BR["rear"], BR["H"] - P["t_ch"]))], "OCU")
    s.pline([Te((Llug - BR["rear"], 0)), Te((Llug - BR["rear"], BR["H"]))], "OCU")
    s.line(Te((0, -tb - 15)), Te((0, BR["H"] + 20)), "EJE"); s.line(Te((x0 - 30, hax)), Te((x1 + 40, hax)), "EJE")
    s.dim(Te((x1, 0)), Te((x1, BR["H"])), 8, f"{f(BR['H'])}", "v")
    s.dim(Te((x1, 0)), Te((x1, hax)), 18, f"eje {f(hax)}", "v")
    s.dim(Te((x0, 0)), Te((x0, BR["spacer"])), -6, f"{f(BR['spacer'])}", "v", outside=True)
    s.weld(Te((x1 - 40, 0)), Te((x1 + 40, -60)), "fillet", f"{f(P['w_br'])}", other=True, note="W3 (4 líneas)")
    s.weld(Te((x0, BR["H"] - P["t_ch"] / 2)), Te((x0 - 80, BR["H"] + 40)), "fillet", "8", other=True, note="W4")
    s.leader(Te((x0 + 30, BR["spacer"] / 2)), Te((x0 - 70, -55)), f"Oreja inf. bloque e={f(BR['spacer'] + P['t_ch'])} (mec.)")
    s.text(f"Mejillas e={f(P['t_ch'])} · orejas e={f(P['t_ch'])}", Te((x0, BR["H"] + 12)), 2.3)
    s.view_title((500, 286), "MÉNSULA 1c – ELEVACIÓN LATERAL", "ESC 1:4")
    # corte E-E: bancada 1e con ranura T (1:1), lengüeta del patín en fantasma
    X = P["x_g"]; Tb_ = tr(430 - X, 150, 1.0)
    section(s, Tb_, [(X - P["w_bed"] / 2 - 30, X + P["w_bed"] / 2 + 30, 0, tb)], scale=0.6)
    section(s, Tb_, *bed_xz(X), scale=0.6, angle=90)
    s.pline([Tb_(p) for p in [(X - neck_w / 2, zb + 12), (X - neck_w / 2, zT1 - 1), (X - head_w / 2, zT1 - 1), (X - head_w / 2, zT0 + 1), (X + head_w / 2, zT0 + 1),
                              (X + head_w / 2, zT1 - 1), (X + neck_w / 2, zT1 - 1), (X + neck_w / 2, zb + 12)]], "FANT")
    s.line(Tb_((X, -8)), Tb_((X, zb + 18)), "EJE")
    s.dim(Tb_((X - P["w_bed"] / 2, zb)), Tb_((X + P["w_bed"] / 2, zb)), 22, f"{f(P['w_bed'])}", "h")
    s.dim(Tb_((X - P["w_slot"] / 2, zb)), Tb_((X + P["w_slot"] / 2, zb)), 12, f"{f(P['w_slot'])} H8", "h")
    s.dim(Tb_((X - P["w_tee"] / 2, zT0)), Tb_((X + P["w_tee"] / 2, zT0)), -(zT0 - tb) - 10, f"{f(P['w_tee'])} +0,2/0", "h")
    s.dim(Tb_((X + P["w_bed"] / 2, tb)), Tb_((X + P["w_bed"] / 2, zb)), 22, f"{f(P['t_bed'])}", "v")
    s.dim(Tb_((X + P["w_slot"] / 2, zT1)), Tb_((X + P["w_slot"] / 2, zb)), 32 + (P["w_bed"] - P["w_slot"]) / 2, f"{f(P['h_slot'])} +0,1/0", "v")
    s.dim(Tb_((X + P["w_tee"] / 2, zT0)), Tb_((X + P["w_tee"] / 2, zT1)), 12 + (P["w_bed"] - P["w_tee"]) / 2, f"{f(P['h_tee'])} +0,2/0", "v")
    s.dim(Tb_((X - P["w_tee"] / 2, tb)), Tb_((X - P["w_tee"] / 2, zT0)), -12 - (P["w_bed"] - P["w_tee"]) / 2, f"fondo {f(fondo)}", "v")
    s.weld(Tb_((X - P["w_bed"] / 2, tb + 2)), Tb_((X - P["w_bed"] / 2 - 45, zb + 30)), "fillet", f"{f(P['w_bed_f'])}", other=True, note="W12")
    s.finish(Tb_((X - P["w_slot"] / 2 + 3, zb)), "Ra 1,6")
    s.text(f"Lengüeta T del patín pos 16 (fantasma): cuello {f(neck_w)}, cabeza {f(head_w)}×{f(head_h)}; juego 1 por lado.", (345, 132), 2.2)
    s.text("Ranura T pasante en todo el largo: el patín entra por el extremo de la bancada.", (345, 128), 2.2)
    s.view_title((430, 110), "CORTE E-E – BANCADA 1e (RANURA T)", "ESC 1:1")
    # despiece base
    dsp = [["1a", f"Plancha base {f(B)}×{f(B)}×{f(tb)}; Ø{f(P['D_piv'])} H7 central", "1", f1(M["base"])],
           ["1b", f"Marco perimetral pletina {f(P['rim_t'])}×{f(P['rim_h'])} (2 × {f(B)} + 2 × {f(B - 2 * P['rim_t'])})", "4", f1(M["rim"])],
           ["1c1", f"Mejilla {f(P['L_ch'])}×{f(BR['H'])}×{f(P['t_ch'])}", f"{2 * P['n_br']:.0f}", f1(7.85e-6 * P['L_ch'] * BR['H'] * P['t_ch'])],
           ["1c2", f"Oreja superior {f(BR['Win'])}×{f(Llug)}×{f(P['t_ch'])}, Ø{f(P['d_pp'])} H9", f"{P['n_br']:.0f}", f1(7.85e-6 * BR['Win'] * Llug * P['t_ch'])],
           ["1c3", f"Oreja inferior (bloque) {f(BR['Win'])}×{f(Llug)}×{f(BR['spacer'] + P['t_ch'])}, Ø{f(P['d_pp'])} H9", f"{P['n_br']:.0f}", f1(7.85e-6 * BR['Win'] * Llug * (BR['spacer'] + P['t_ch']))],
           ["1d", "Punto de izaje soldable comercial (ver D-01 nota 9)", "4", "—"],
           ["1e", f"Bancada {f(P['w_bed'])}×{f(P['t_bed'])}×{f(KG['L_bed'])}, ranura T {f(P['w_slot'])} H8×{f(P['h_slot'])} + cabeza {f(P['w_tee'])}×{f(P['h_tee'])}, fondo {f(fondo)} (mec. tras soldar)", f"{P['n_cyl']:.0f}", f1(M["beds"] / P["n_cyl"])]]
    s.text("DESPIECE POS 1", (560, 584 - 6), 3.5, bold=True)
    y = s.table(560, 584 - 9, [("Sub", 12, "C"), ("Descripción", 194, "L"), ("Cant.", 18, "C"), ("kg/u", 18, "R")], dsp, rh=5.4, h=2.1)
    nb = ["NOTAS DE FABRICACIÓN – BASE",
          "1. Soldar marco 1b, ménsulas 1c y puntos de izaje 1d; alivio de tensiones; luego mecanizar.",
          f"2. Cara de giro (zona Ø{f(P['D_top'] + 20)}): planitud 0,20, Ra 1,6–3,2; sin pintura.",
          f"3. Orejas 1c2/1c3: escariar Ø{f(P['d_pp'])} H9 en línea en un mismo montaje después de soldar; coaxialidad 0,10;",
          f"   altura del eje {f(hax)} ±0,5 sobre la cara de giro; posición del eje ±0,5 respecto del centro del pivote.",
          f"4. Pivote pos 5: calado en caliente Ø{f(P['D_piv'])} H7/p6 (base local ≤ 200 °C o pivote enfriado) + filete de sello 8 superior;",
          "   perpendicularidad 0,05 respecto de la cara de giro.",
          "5. Los puntos de izaje 1d se sueldan según instrucciones del fabricante (WPS del proveedor, MT 100 %).",
          f"6. Bancadas 1e (e={f(P['t_bed'])}): filete {f(P['w_bed_f'])} continuo a ambos lados (W12, precalentar 65 °C); ranura T (cuello {f(P['w_slot'])} H8 × {f(P['h_slot'])},",
          f"   cabeza {f(P['w_tee'])} × {f(P['h_tee'])}, fondo {f(fondo)}) mecanizada después de soldar y relevar, pasante (corte E-E);",
          "   paralela a Y ±0,10 en todo el largo y coaxial con el ojal de la ménsula ±0,2; flancos Ra 1,6; lubricar con grasa grafitada.",
          "7. Protección: Sa 2½ + epóxico rico en zinc 75 µm + epóxico 125 µm + PU 50 µm (ISO 12944 C4) salvo caras de giro y orejas."]
    s.mtext(nb, (560, y - 8), 2.15, 1.55, bold_first=True)
    return s

# =====================================================================
def sheet_f03():
    s = Sheet(); sheet_frame(s, 5, "PIEZAS MECÁNICAS Y ESPECIFICACIÓN HIDRÁULICA", "1:2,5 / 1:2 / 1:4")
    # uña deslizante 1:2,5 — planta (x radial desde la punta; cara de empuje plana arriba) y elevación
    sc = 0.4; T = tr(50, 478, sc)
    L = paw_L; b = P["dog_b"]; hdg = P["dog_h"]; ct = P["c_tip"]
    s.pline([T(p) for p in [(0, b / 2), (L, b / 2), (L, -b / 2), (ch_dx, -b / 2), (0, -b / 2 + ch_dy)]], "VIS", True)
    s.pline([T(p) for p in circ((ct, b / 2 + d_pin / 2), d_pin / 2, 60)], "FANT")
    s.line(T((ct, b / 2 - 8)), T((ct, b / 2 + d_pin + 8)), "EJE")
    s.line(T((-15, 0)), T((L + 15, 0)), "EJE")
    s.line(T((0, b / 2 + 4)), T((L, b / 2 + 4)), "EJE")                              # zona templada (cara de empuje completa)
    s.dim(T((0, -b / 2)), T((L, -b / 2)), -16, f"{f(L)}", "h")
    s.dim(T((0, -b / 2)), T((ch_dx, -b / 2)), -6, f"Δx {f1(ch_dx)}", "h")
    s.dim(T((L, -b / 2)), T((L, b / 2)), 10, f"{f(b)} f8", "v")
    s.dim(T((0, -b / 2)), T((0, -b / 2 + ch_dy)), -8, f"Δy {f1(ch_dy)}", "v")
    s.dim(T((0, -b / 2 + ch_dy)), T((0, b / 2)), -8, f"{f1(b_tipr)}", "v")
    s.dim(T((0, b / 2 + 4)), T((ct, b / 2 + 4)), 70, f"{f(ct)}", "h", outside=True)
    Mc = (ch_dx / 2, -b / 2 + ch_dy / 2); nb = math.radians(P["beta_ch"])
    nrm = (-math.cos(nb), -math.sin(nb))                                               # normal exterior del chaflán (β respecto del eje x)
    s.line(T(Mc), T((Mc[0] + 70 * nrm[0], Mc[1] + 70 * nrm[1])), "COTA")
    s.line(T(Mc), T((Mc[0] - 70, Mc[1])), "COTA")
    s.arc(T(Mc), 50 * sc, 180, 180 + P["beta_ch"], "COTA")
    s.text(f"β = {P['beta_ch']:.0f}°", T((Mc[0] - 80, Mc[1] - 32)), 2.5, "MIDDLE_RIGHT")
    s.leader(T((L * 0.55, b / 2 + 4)), T((L + 25, b / 2 + 55)), f"Cara de empuje plana: temple ind. {HRC}, prof. ≥ {f1(z_hard)} mm; Ra 0,8; planitud 0,05")
    s.leader(T((ch_dx * 0.7, -b / 2 + ch_dy * 0.3)), T((ch_dx + 60, -b / 2 - 45)), f"Chaflán de retorno {P['beta_ch']:.0f}° (normal/eje radial), Ra 1,6")
    s.text(f"Pasador Ø{f(d_pin)} (fantasma) en la toma: contacto a {f(ct)} de la punta. El resorte actúa en la cara extrema (x = {f(L)}).", (40, 397), 2.2)
    s.view_title((150, 405), "UÑA POS 10 – PLANTA", "ESC 1:2,5")
    Te = tr(50, 345, sc)
    s.pline([Te(p) for p in [(0, -hdg / 2), (L, -hdg / 2), (L, hdg / 2), (0, hdg / 2)]], "VIS", True)
    s.line(Te((ch_dx, -hdg / 2)), Te((ch_dx, hdg / 2)), "OCU")
    s.line(Te((-15, 0)), Te((L + 15, 0)), "EJE")
    s.dim(Te((L, -hdg / 2)), Te((L, hdg / 2)), 8, f"{f(hdg)} f8", "v")
    s.view_title((150, 300), "UÑA POS 10 – ELEVACIÓN (vista de la cara de empuje)", "ESC 1:2,5")
    s.mtext([f"Material 34CrNiMo6+QT (forja), Re ≥ {f(P['Fy_dog'])} MPa medido en probeta de la propia forja, certificado EN 10204 3.1;",
             "  dureza del núcleo QT 280–330 HB. UT EN 10228-3 clase 3.",
             f"Cara de empuje: temple por inducción {HRC} (Fy sup. ≥ {f(P['Fy_surf'])} MPa), profundidad efectiva ≥ {f1(z_hard)} mm (550 HV);",
             "  revenido 180 °C; MT de la cara templada (sin grietas). Rectificar después del temple.",
             f"Ajuste en el alojamiento del patín: {f(b)} H9/f8 × {f(hdg)} H9/f8; retorno radial {f1(KG['travel'])} mm.",
             f"Resorte pos 12: compresión, carrera ≥ {f(KG['travel'] + 5)} mm, fuerza 150–300 N (vence grasa y peso).",
             "Aristas 1×45° salvo la cara de empuje (0,5×45°). Tolerancias ISO 2768-mK."], (40, 288), 2.2, 1.6)
    # patín guiado 1:4 — planta y corte F-F por el alojamiento
    sc5 = 0.25; T5 = tr(560, 250, sc5)
    Ls, ws = KG["L_s"], P["w_s"]
    y0p, y1p = -KG["rear"], KG["front"]
    s.pline([T5(p) for p in [(-ws / 2, y0p), (ws / 2, y0p), (ws / 2, y1p), (-ws / 2, y1p)]], "VIS", True)
    s.pline([T5(p) for p in circ((0, 0), P["d_pp"] / 2, 30)], "VIS"); s.centerlines(T5((0, 0)), P["d_pp"] / 2 * sc5, 3)
    s.pline([T5(p) for p in [(-57.5, y0p), (57.5, y0p), (57.5, 57.5), (-57.5, 57.5)]], "OCU", True)
    yd = P["l_p"] - d_pin / 2; xm = KG["mouthX"] - P["x_g"]; xp = KG["pocketEnd"] - P["x_g"]      # yd: cara de empuje de la uña
    s.pline([T5(p) for p in [(xm, yd - b - 1), (xp + 1, yd - b - 1), (xp + 1, yd + 1), (xm, yd + 1)]], "OCU", True)
    s.pline([T5(p) for p in [(-ws / 2, yd - b - P["t_fw"]), (xm, yd - b - P["t_fw"]), (xm, yd + P["t_fw"]), (-ws / 2, yd + P["t_fw"])]], "VIS")
    for wq in (neck_w, head_w):
        s.line(T5((-wq / 2, y0p)), T5((-wq / 2, y1p)), "OCU"); s.line(T5((wq / 2, y0p)), T5((wq / 2, y1p)), "OCU")
    s.line(T5((0, y0p - 20)), T5((0, y1p + 20)), "EJE")
    s.dim(T5((ws / 2, y0p)), T5((ws / 2, y1p)), 10, f"{f(Ls)}", "v")
    s.dim(T5((ws / 2, y0p)), T5((ws / 2, 0)), 22, f"{f1(KG['rear'])}", "v")
    s.dim(T5((ws / 2, 0)), T5((ws / 2, yd)), 22, f"{f(yd)}", "v")
    s.dim(T5((-ws / 2, y0p)), T5((ws / 2, y0p)), -8, f"{f(ws)}", "h")
    s.dim(T5((xm, yd + P["t_fw"])), T5((xm, yd)), -6, f"{f(P['t_fw'])}", "v")
    s.dim(T5((xm, yd - b)), T5((xm, yd - b - P["t_fw"])), -6, f"{f(P['t_fw'])}", "v")
    s.dim(T5((xm, yd + P["t_fw"])), T5((-ws / 2, yd + P["t_fw"])), 8, f"{f(-ws / 2 - xm)}", "h", outside=True)
    s.leader(T5((0, P["d_pp"] / 2)), T5((-ws / 2 - 90, 60)), f"Ø{f(P['d_pp'])} H9 (pasador del vástago)")
    s.leader(T5((xm, yd - b / 2)), T5((xm - 90, yd + 130)), f"Marco de boca e={f(P['t_fw'])}, alojamiento {f(b)} H9 × {f(hdg)} H9")
    s.section_mark(T5((xm - 30, yd - b / 2)), 0, "F"); s.section_mark(T5((ws / 2 + 30, yd - b / 2)), 180, "F")
    s.text("Hacia el centro de la mesa: −x (izquierda en esta vista).", (520, 120), 2.2)
    s.view_title((560, 130), "PATÍN POS 16 – PLANTA", "ESC 1:4")
    sc6 = 0.4; T6 = lambda p: (735 + p[0] * sc6, 190 + (p[1] - zb) * sc6)
    section(s, T6, *shoe_xz(0, xm), scale=0.4)
    s.line(T6((0, zT0 - 6)), T6((0, z_shoe + 12)), "EJE")
    s.dim(T6((ws / 2, zb)), T6((ws / 2, z_shoe)), 8, f"{f(Hs)}", "v")
    s.dim(T6((-ws / 2, zb)), T6((ws / 2, zb)), -(zb - zT0) - 9, f"{f(ws)}", "h")
    s.dim(T6((-neck_w / 2, zb)), T6((neck_w / 2, zb)), 8, f"{f(neck_w)} f7", "h", outside=True)
    s.dim(T6((-head_w / 2, zT0 + 1)), T6((head_w / 2, zT0 + 1)), -4, f"{f(head_w)} h11", "h", outside=True)
    s.dim(T6((head_w / 2, zT0 + 1)), T6((head_w / 2, zT1 - 1)), 10, f"{f(head_h)}", "v", outside=True)
    s.dim(T6((neck_w / 2, zT1 - 1)), T6((neck_w / 2, zb)), 24, f"{f(neck_h)}", "v", outside=True)
    s.dim(T6((xm, zc - hdg / 2 - 10)), T6((xm, zc + hdg / 2 + 10)), -6, f"{f(hdg + 20)}", "v")
    s.dim(T6((xm, zc + hdg / 2 + 10)), T6((-ws / 2, zc + hdg / 2 + 10)), 6, f"{f1(KG['inset'])}", "h", outside=True)
    s.dim(T6((xp + 1, pk_bot)), T6((xp + 1, pk_top)), 22, f"{f(hdg + 2)}", "v")
    s.view_title((750, 140), "CORTE F-F – PATÍN (lengüeta T)", "ESC 1:2,5")
    s.mtext([f"Patín: S460 (EN 10025) o 34CrNiMo6+QT, Fy ≥ {f(P['Fy_shoe'])} MPa, certificado 3.1; una pieza, sin soldadura.",
             f"Lengüeta T: cuello {f(neck_w)} f7 en ranura {f(P['w_slot'])} H8; cabeza {f(head_w)}×{f(head_h)} en {f(P['w_tee'])}×{f(P['h_tee'])} (juego 1 por lado).",
             f"P1 (revisión): el alojamiento ({f(hdg + 2)}) es más alto que la caja ({f(Hs)}): queda abierto {f(pk_top - z_shoe)} mm arriba",
             f"   y con fondo de {f(pk_bot - zb)} mm sobre la bancada. Confirmar alto de la caja o tapa superior antes de fabricar."], (655, 128), 2.1, 1.6)
    # pasador de empuje 1:2
    sc2 = 0.5; T2 = tr(300, 430, sc2)
    s.pline([T2(p) for p in [(-d_pin / 2, 0), (d_pin / 2, 0), (d_pin / 2, hd), (-d_pin / 2, hd)]], "VIS", True)
    s.pline([T2(p) for p in [(-10, hd - 40), (10, hd - 40), (10, hd), (-10, hd)]], "OCU", True)
    s.line(T2((0, -10)), T2((0, hd + 10)), "EJE")
    s.dim(T2((-d_pin / 2, 0)), T2((d_pin / 2, 0)), -8, f"Ø{f(d_pin)} m6", "h")
    s.dim(T2((d_pin / 2, 0)), T2((d_pin / 2, hd)), 8, f"{f(hd)} −0,5/0", "v")
    s.leader(T2((0, hd - 20)), T2((-70, hd + 35)), "M20 prof. 40")
    s.text(f"34CrNiMo6+QT, Fy ≥ {f(P['Fy_pin'])} MPa (cert. 3.1), núcleo 280–330 HB; Ra 0,8 en Ø; chaflanes 2×45°.", (262, 393), 2.2)
    s.text(f"Franja de contacto con la uña: temple ind. {HRC}, prof. ≥ {f1(z_hard)} mm (ver F-01 det. C).", (262, 389), 2.2)
    s.view_title((300, 405), "PASADOR DE EMPUJE POS 3", "ESC 1:2")
    # pasador de articulación 1:2
    Lpp = forkH + 5                                                     # caña; cabeza 15 → largo total h_horquilla + 20
    T3 = tr(410, 430, sc2)
    s.pline([T3(p) for p in [(-P['d_pp'] / 2, 0), (P['d_pp'] / 2, 0), (P['d_pp'] / 2, Lpp), (-P['d_pp'] / 2, Lpp)]], "VIS", True)
    s.pline([T3(p) for p in [(-P['d_pp'] / 2 - 12, Lpp), (P['d_pp'] / 2 + 12, Lpp), (P['d_pp'] / 2 + 12, Lpp + 15), (-P['d_pp'] / 2 - 12, Lpp + 15)]], "VIS", True)
    s.line(T3((0, -10)), T3((0, Lpp + 25)), "EJE")
    s.dim(T3((-P['d_pp'] / 2, 0)), T3((P['d_pp'] / 2, 0)), -8, f"Ø{f(P['d_pp'])} f8", "h")
    s.dim(T3((P['d_pp'] / 2 + 12, 0)), T3((P['d_pp'] / 2 + 12, Lpp + 15)), 8, f"{f(Lpp + 15)}", "v")
    s.text("42CrMo4+QT 28–34 HRC; cabeza Ø{0}×15; placa de retención".format(f(P['d_pp'] + 24)), (385, 393), 2.2)
    s.view_title((420, 405), "PASADOR DE ARTICULACIÓN POS 11", "ESC 1:2")
    # pivote, buje y tapa 1:4
    sc4 = 0.25; T4 = tr(330, 200, sc4)
    s.pline([T4(p) for p in [(-P['D_piv'] / 2, 0), (P['D_piv'] / 2, 0), (P['D_piv'] / 2, L_piv), (-P['D_piv'] / 2, L_piv)]], "VIS", True)
    s.pline([T4(p) for p in [(P['D_piv'] / 2, tb + 2), (d_bush / 2, tb + 2), (d_bush / 2, tb + 2 + P['L_bush']), (P['D_piv'] / 2, tb + 2 + P['L_bush'])]], "VIS", True)
    s.hatch_poly([T4(p) for p in [(P['D_piv'] / 2, tb + 2), (d_bush / 2, tb + 2), (d_bush / 2, tb + 2 + P['L_bush']), (P['D_piv'] / 2, tb + 2 + P['L_bush'])]], scale=0.3)
    s.pline([T4(p) for p in [(-cap_D / 2, L_piv), (cap_D / 2, L_piv), (cap_D / 2, L_piv + cap_t), (-cap_D / 2, L_piv + cap_t)]], "VIS", True)
    s.line(T4((0, -10)), T4((0, L_piv + cap_t + 15)), "EJE")
    s.dim(T4((-P['D_piv'] / 2, 0)), T4((P['D_piv'] / 2, 0)), -8, f"Ø{f(P['D_piv'])} p6 / f7", "h")
    s.dim(T4((P['D_piv'] / 2, 0)), T4((P['D_piv'] / 2, L_piv)), 30, f"{f(L_piv)}", "v")
    s.dim(T4((-cap_D / 2, L_piv + cap_t)), T4((cap_D / 2, L_piv + cap_t)), 8, f"Ø{f(cap_D)}×{f(cap_t)}", "h")
    s.leader(T4((d_bush / 2, tb + 40)), T4((d_bush / 2 + 80, tb + 120)), f"Buje pos 6 Ø{f(d_bush)}/Ø{f(P['D_piv'])}×{f(P['L_bush'])}")
    s.text(f"Pivote 42CrMo4+QT; tapa S355J2 e={f(cap_t)} con 4 × M10×25 ISO 10642 10.9 avellanados; juego vertical 3 mm.", T4((-cap_D / 2 - 20, -45)), 2.2)
    s.view_title((340, 140), "PIVOTE POS 5, BUJE POS 6, TAPA POS 7", "ESC 1:4")
    # especificación hidráulica
    c = {x["id"]: x for x in DV["casos"]}
    spec = [["Cilindros pos 9", f"{P['n_cyl']:.0f} × doble efecto, Ø{f(P['D_bore'])}/Ø{f(P['d_rod'])}, carrera {f(P['stroke'])}, clase {f(P['p_rated'])} psi ({f(P['p_rated'] * 0.07)} bar)"],
            ["Largo ojal–ojal retraído", f"{f(P['L0'])} mm (confirmar con proveedor; ajustar ménsula si difiere)"],
            ["Geometría de extremos", f"ojal trasero → cuerpo ≥ {f(P['e_body'])}; retraído: ojal del vástago → cuerpo ≥ {f(P['c_rod'])}"],
            ["Ojales", f"Rótula esférica en ambos extremos, pasador Ø{f(P['d_pp'])}, ancho {f(P['b_eye'])}"],
            ["Cuerpo", f"Ø exterior ≤ {f(P['D_body'])} mm; masa ≈ {f(P['m_cyl'])} kg"],
            [f"Fuerza a {f(P['p_relief'])} bar / área", f"{f1(DV['Fstall'])} kN / {f(DV['A'])} mm²"],
            ["Retorno (puerto B {0} bar)".format(f(P['p_ret'])), f"{f1(DV['Fret'])} kN"],
            ["Bomba", f"Eléctrica 70 MPa, ≥ {f1(P['Q_pump'])} L/min, 2 salidas, válvula J con bloqueo"],
            ["Circuito", "Paralelo con colector común; bloqueo de operación con un solo cilindro"],
            ["Alivio / alarma", f"{f(P['p_relief'])} / {f(P['p_alarm'])} bar; manómetro 0–1000 bar clase 1,0"],
            ["Presión esperada", f"nominal ≈ {f(c['nom']['p'])} bar; despegue de diseño ≤ {f(c['dis']['p'])} bar"],
            ["Mangueras", f"{f(P['p_rated'])} psi mín., acoples rápidos con protección, radio de curvatura del fabricante"],
            ["Patín y guía", f"μg ≤ {P['mu_g']:.2f} con grasa grafitada; reacción de guía a calado {f1(DV['Rguide'])} kN".replace(".", ",", 1)]]
    s.text("ESPECIFICACIÓN HIDRÁULICA", (560, 584 - 6), 3.5, bold=True)
    s.table(560, 584 - 9, [("Ítem", 64, "L"), ("Valor", 178, "L")], spec, rh=5.4, h=2.1)
    return s

# =====================================================================
def sheet_f04():
    s = Sheet(); sheet_frame(s, 6, "CORTE, SOLDADURA, MONTAJE Y OPERACIÓN", "S/E")
    rings = D["almas"]
    seg = lambda r: 2 * math.pi * r + 20
    corte = [["1a", "Plancha", f"{f(P['B'] + 10)}×{f(P['B'] + 10)}×{f(tb + 5)}", "1", "A572-50", "Sobremetal 5 por cara funcional"],
             ["1b", "Pletina", f"{f(P['rim_t'])}×{f(P['rim_h'])}×{f(P['B'])}", "4", "A572-50", ""],
             ["1c1", "Plancha", f"{f(P['L_ch'])}×{f(BR['H'] + 5)}×{f(P['t_ch'])}", f"{2 * P['n_br']:.0f}", "A572-50", ""],
             ["1c2", "Plancha", f"{f(BR['Win'] - 1)}×{f(Llug + 5)}×{f(P['t_ch'])}", f"{P['n_br']:.0f}", "A572-50", "Agujero mecanizado tras soldar"],
             ["1c3", "Plancha", f"{f(BR['Win'] - 1)}×{f(Llug + 5)}×{f(BR['spacer'] + P['t_ch'] + 2)}", f"{P['n_br']:.0f}", "A572-50", ""],
             ["2a", "Disco", f"Ø{f(2 * prIn + 5)}×{f(tt)}", "1", "A572-50 Z35", "Oxicorte + mecanizado"],
             ["2b", "Segm. anillo", f"Ø{f(P['D_top'] + 10)}/Ø{f(2 * prIn - 10)}×{f(tpr + 3)}, 90°", "4", "A572-50 Z35", "Empalmes CJP"],
             ["2c", "Disco", f"Ø{f(2 * prIn + 5)}×{f(tbo + 3)}", "1", "A572-50 Z35", "Cara de giro mecanizada"],
             ["2d", "Segm. anillo", f"Ø{f(P['D_top'] + 10)}/Ø{f(2 * prIn - 10)}×{f(tpr + 3)}, 90°", "4", "A572-50 Z35", "Empalmes CJP"]]
    for i, r in enumerate(rings):
        corte.append([f"2e{i + 1}", "Pletina rolada", f"{f(hw)}×{f(P['t_web'])}×{f(seg(r))}", "1", "A572-50", f"Eje R{f(r)}; 1 empalme CJP"])
    rr = [P["D_hub"] / 2] + [r for r in rings if r < P["R_rib"]] + [P["R_rib"]]
    for i in range(len(rr) - 1):
        Lr = rr[i + 1] - rr[i] - P["t_web"] / 2 * (1 if i > 0 else 0) - P["t_web"] / 2 * (1 if i < len(rr) - 2 or rr[-1] in rings else 0)
        corte.append([f"2f{i + 1}", "Pletina", f"{f(hw)}×{f(P['t_rib'])}×{f(Lr)}", f"{int(P['N_rib'])}", "A572-50", f"R{f(rr[i])}–R{f(rr[i + 1])}"])
    corte += [["2g", "Forja", f"Ø{f(P['D_hub'] + 10)}/Ø{f(d_bush - 10)}×{f(hw + 5)}", "1", "S355J2+N", ""],
              ["3", "Barra", f"Ø{f(d_pin + 5)}×{f(hd + 6)}", f"{N_pin}", "34CrNiMo6+QT", f"Fy ≥ {f(P['Fy_pin'])}"],
              ["5", "Barra", f"Ø{f(P['D_piv'] + 5)}×{f(L_piv + 6)}", "1", "42CrMo4+QT", ""],
              ["10", "Forja", f"{f(paw_L + 10)}×{f(P['dog_b'] + 10)}×{f(P['dog_h'] + 10)}", f"{P['n_cyl']:.0f}", "34CrNiMo6+QT", f"Uña; Re ≥ {f(P['Fy_dog'])} (3.1); cara ind."],
              ["16", "Forja / plancha", f"{f(KG['L_s'] + 10)}×{f(P['w_s'] + KG['inset'] + 10)}×{f(max(z_shoe, zc + P['dog_h'] / 2 + 10) - (zT0 + 1) + 10)}", f"{P['n_cyl']:.0f}", "S460 / 34CrNiMo6", f"Patín y lengüeta T de una pieza; Fy ≥ {f(P['Fy_shoe'])}"],
              ["1e", "Plancha", f"{f(P['w_bed'] + 10)}×{f(P['t_bed'] + 5)}×{f(KG['L_bed'] + 10)}", f"{P['n_cyl']:.0f}", "A572-50", "Bancada; ranura T tras soldar"],
              ["11", "Barra", f"Ø{f(P['d_pp'] + 30)}×{f(forkH + 2 * 15 + 20 + 25)}", f"{2 * P['n_cyl']:.0f}", "42CrMo4+QT", ""]]
    s.text("LISTA DE CORTE", (30, 576), 3.5, bold=True)
    y = s.table(30, 572, [("Pos", 12, "C"), ("Forma", 24, "L"), ("Dimensión bruta (mm)", 70, "L"), ("Cant.", 12, "C"), ("Material", 26, "L"), ("Obs.", 56, "L")], corte, rh=4.8, h=2.0)
    sold = [["W1", "1b – 1a", "Filete ambos lados", "6", "MT 100 %"],
            ["W2", "1c1 – 1a", "Filete ambos lados (4 líneas por ménsula)", f"{f(P['w_br'])}", "MT 100 %"],
            ["W3", "1c2/1c3 – 1c1", "Filete ambos lados", "8", "MT 100 %"],
            ["W4", "1c3 – 1a", "Filete todo alrededor", "8", "MT 100 %"],
            ["W5", "2a/2c – 2b/2d; empalmes 2b, 2d", "CJP a tope en V 60°, raíz 3, respaldo", f"t={f(tbo)}–{f(tpr)}", "UT 100 %"],
            ["W6", "2g – 2a / 2c", "CJP bisel 45° con respaldo", f"t={f(tt)}", "UT 100 %"],
            ["W7", "2e – 2c / 2a", "Filete ambos lados continuo", f"{f(P['w_web'])}", "MT 100 %"],
            ["W8", "2f – 2c / 2e / 2g / 2a", "Filete ambos lados continuo", f"{f(P['w_web'])}", "MT 100 %"],
            ["W9", "2a – 2e / 2f (cierre)", "Soldadura en ranura 22×80 c/250, relleno completo", "c/250", "MT 100 %"],
            ["W10", "Empalmes 2e", "CJP a tope en V 60°", f"t={f(P['t_web'])}", "UT 100 %"],
            ["W11", "5 – 1a", "Filete de sello superior", "8", "MT 100 %"],
            ["W12", "1e – 1a", "Filete ambos lados continuo", f"{f(P['w_bed_f'])}", "MT 100 %"]]
    s.text("PROGRAMA DE SOLDADURAS", (240, 576), 3.5, bold=True)
    y2 = s.table(240, 572, [("Junta", 12, "C"), ("Elementos", 52, "L"), ("Tipo y preparación", 74, "L"), ("Tamaño", 22, "C"), ("END", 20, "C")], sold, rh=4.8, h=2.0)
    ctrl = ["PRECALENTAMIENTO Y CONTROL",
            "Precalentamiento AWS D1.1 (Cat. B): t ≤ 20: 10 °C (se exige 50 °C mín.); 20 < t ≤ 38: 10 °C → 50 °C; 38 < t ≤ 65: 65 °C; interpase ≤ 250 °C.",
            "42CrMo4 y 34CrNiMo6: no se sueldan. Planchas de la mesa UT ASTM A578 nivel B antes de cortar.",
            "Tolerancias: ISO 2768-mK; ISO 1101 según planos F-01 a F-03. Dureza del núcleo QT pos 3 y 10: 280–330 HB; pos 11: 28–34 HRC.",
            f"Temple por inducción {HRC}, prof. efectiva ≥ {f1(z_hard)} mm: cara de empuje de cada uña pos 10 y franja de contacto de cada pasador pos 3;",
            "  control: dureza superficial en el 100 % de uñas y 10 % de pasadores, profundidad en probeta testigo por lote, MT de caras templadas.",
            "Control dimensional final: planitud de caras de giro, PCD y paso de pasadores, alturas y coaxialidad de orejas, perpendicularidad del pivote.",
            "Registro: certificados 3.1, WPS/PQR, calificación de soldadores, informes END, dimensional y prueba de carga."]
    s.mtext(ctrl, (240, y2 - 8), 2.15, 1.55, bold_first=True)
    c = {x["id"]: x for x in DV["casos"]}
    mont = ["MONTAJE",
            "1. Apoyar la base en losa o mats nivelados (pendiente ≤ 0,5 %). Verificar presión admisible de la losa ≥ {0} MPa (por terceros).".format(f"{DV['q_max']:.2f}".replace(".", ",")),
            "2. Limpiar caras de giro de 1a y 2c/2d; aplicar grasa grafitada pos 14 de 0,3–0,5 mm por cara y llenar las ranuras.",
            "3. Izar la mesa con 4 cáncamos pos 15 (M30) y bajarla centrada en el pivote; colocar tapa pos 7 (juego vertical 3 mm).",
            "4. Retirar cáncamos y colocar tapones; cerrar tapa de inspección pos 8. Montar faldón pos 13.",
            "5. Insertar los patines pos 16 por el extremo de la ranura T de cada bancada; montar uñas pos 10 (cara plana templada hacia el pasador)",
            "   con resorte pos 12, y cilindros pos 9 entre ménsula y patín (pasadores pos 11).",
            "6. Conectar mangueras (A: avance, B: retorno) al colector común. Prueba en vacío: 2 ciclos completos.",
            "OPERACIÓN (POR CICLO)",
            f"a) Extender ambos cilindros a la vez: {f(P['s_free'])} mm libres, la uña toma el pasador y la mesa gira {360 / N_pin:.2f}°.".replace(".", ",", 1),
            f"b) Retraer a fondo: el chaflán ({P['beta_ch']:.0f}°) toca el pasador siguiente, la uña se retrae {f(KG['travel'])} mm y el resorte la reengancha; verificar ambas uñas.",
            f"c) Registrar presión: esperada ≈ {f(c['nom']['p'])} bar; detener, retraer y relubricar si supera {f(P['p_alarm'])} bar.",
            "d) Para invertir el giro: trasladar cilindros a las ménsulas del otro extremo de la guía y girar patines y uñas 180°.",
            "e) No operar con viento > 50 km/h ni con la carga sin arriostrar. Prohibido operar con un solo cilindro.",
            "ENSAYO DE ACEPTACIÓN",
            f"Giro 360° con 1,0 WLL registrando la presión de despegue p de cada ciclo. μ_real = (n·p·A·brazo_mín/K − T_piv)/(N·{f(P['r_ef'])} mm), K = {DV['Kguide']:.3f}.",
            f"Aceptación: μ_real ≤ {P['mu_d']:.2f} (p ≤ {f(c['dis']['p'])} bar). MT de soldaduras W2–W4 después del ensayo.".replace(".", ",", 1),
            "MANTENIMIENTO",
            "≈ 60 g por grasera (4) antes de cada operación y cada 90° de giro con carga. Inspeccionar uñas, caras y pasadores cada 10 vueltas.",
            "Reemplazar pasadores pos 3 con desgaste > 1 mm en el diámetro o marcas de contacto de borde (sin soldadura: desmontables)."]
    s.mtext(mont, (450, 572), 2.15, 1.55, bold_first=True)
    for t in ("OPERACIÓN (POR CICLO)", "ENSAYO DE ACEPTACIÓN", "MANTENIMIENTO"):
        pass
    lub = ["LUBRICACIÓN (POS 14)",
           "Grasa grafitada NLGI 2, base complejo de litio o calcio, grafito ≥ 10 % en peso, EP (4 bolas ≥ 2500 N), −20/+150 °C.",
           "No usar grasas sin sólidos ni aceites: a la presión de contacto la película fluida se expulsa.",
           "El grafito es conductor: aislar equipos energizados."]
    s.mtext(lub, (30, y - 8), 2.15, 1.55, bold_first=True)
    return s

# =====================================================================
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    builders = [sheet_d01, sheet_d02, sheet_f01, sheet_f02, sheet_f03, sheet_f04]
    pdfs, dxfs = [], []
    for code, fn in zip(SHEETS, builders):
        s = fn()
        base = OUT / f"TT300-C-{code}"
        s.save(str(base) + ".dxf", str(base) + ".pdf")
        pdfs.append(str(base) + ".pdf"); dxfs.append(str(base) + ".dxf")
        print("ok", code)
    import pymupdf
    doc = pymupdf.open()
    for p in pdfs:
        doc.insert_pdf(pymupdf.open(p))
    doc.save(str(OUT / "TT300-C_Planos_RevB.pdf"))
    with zipfile.ZipFile(OUT / "TT300-C_DXF_RevB.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for d in dxfs:
            z.write(d, pathlib.Path(d).name)
        z.write(OUT / "TT300-C_design.json", "TT300-C_design.json")
    for p in pdfs:
        pg = pymupdf.open(p)[0]
        pg.get_pixmap(dpi=60).save(p.replace(".pdf", ".png"))
    print("PDF combinado y ZIP DXF listos en", OUT)

if __name__ == "__main__":
    main()
