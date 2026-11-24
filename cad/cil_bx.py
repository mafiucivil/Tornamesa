"""Cilindro hidráulico FABRICADO del juego TT300-BX (rev. 7d, decisión del mandante 19-11-2026).

Reemplaza, solo cuando el JSON trae el bloque bx.cilindro, la pieza comercial «cilindro_pv» (ACC-013, especificación de compra) por las piezas
fabricadas y los elementos comerciales del cilindro: camisa, fondo macizo, ojal trasero (orejeta), tapa delantera, pistón, tuerca ranurada,
vástago, ojal del vástago, rótula GE70ES y sellos (S1…S8). Todas las cotas, tolerancias, rugosidades y alojamientos salen de bx.cilindro
(fuente única: packages/core/tt300bx.js, cylExport). ACC-013 pasa a ser el SUBCONJUNTO del cilindro (corte longitudinal con globos, tabla de
sellos, pares, prueba y secuencia) y cada pieza fabricada tiene su lámina (ACC-028…035).

Ejes locales de construcción: x sobre el eje del cilindro desde el eje del ojal trasero E, z vertical (eje del cilindro en z = 0), y horizontal;
las piezas móviles (pistón, tuerca, sellos del pistón, vástago y ojal del vástago) se desplazan e = L − L0 (posición dibujada del núcleo).
Sin bloque bx.cilindro el juego no cambia (el núcleo y el juego TT300-C no pasan por este módulo)."""
import math
import propuestas
import cadquery as cq
from geom import *

T30 = math.tan(math.radians(30.0))
T15 = math.tan(math.radians(15.0))
T20 = math.tan(math.radians(20.0))

# números de pieza FIJOS (acc3d.ACC_NUM sigue hasta 27): el subconjunto conserva ACC-013; ACC-036 es la lámina del esquema retraído/extendido (rev. 7e)
NUM = {"cil_camisa": 28, "cil_fondo": 29, "cil_ojal_E": 30, "cil_tapa": 31, "cil_piston": 32, "cil_tuerca": 33, "cil_vastago": 34, "cil_ojal_Q": 35,
       "cil_rotula": 45, "cil_S1": 37, "cil_S2": 38, "cil_S3": 39, "cil_S4": 40, "cil_S5": 41, "cil_S6": 42, "cil_S7": 43, "cil_S8": 44}
FAB = ["cil_camisa", "cil_fondo", "cil_ojal_E", "cil_tapa", "cil_piston", "cil_tuerca", "cil_vastago", "cil_ojal_Q"]
SELLOS = ["cil_S1", "cil_S2", "cil_S3", "cil_S4", "cil_S5", "cil_S6", "cil_S7", "cil_S8"]
KEYS = FAB + ["cil_rotula"] + SELLOS
MOVIL = {"cil_piston", "cil_tuerca", "cil_vastago", "cil_ojal_Q", "cil_S1", "cil_S2", "cil_S3"}


def C_(g):
    return ((getattr(g, "bx", None) or {}).get("cilindro")) or None


def activo(g):
    return C_(g) is not None


# ---------------------------------------------------------------------------------------------- primitivas
def rev(pts):
    """Sólido de revolución alrededor del eje x a partir del contorno (x, r) cerrado (r ≥ 0)."""
    return cq.Workplane("XY").polyline(pts).close().revolve(360.0, (0, 0, 0), (1, 0, 0)).val()


def ring_x(x0, x1, r0, r1):
    return rev([(x0, r0), (x1, r0), (x1, r1), (x0, r1)])


def cyl_z(r, z0, z1, x=0.0, y=0.0):
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))


def cyl_x(r, x0, x1, y=0.0, z=0.0):
    return cq.Solid.makeCylinder(r, x1 - x0, cq.Vector(x0, y, z), cq.Vector(1, 0, 0))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def puerto(sol, x, d_paso, C_p):
    """Puerto radial hacia +z: refrentado plano Ø sf, rosca G (Ø de núcleo) de prof. p y paso al Ø interior."""
    sf, p = float(C_p["refrentado"]), float(C_p["prof_rosca"])
    zs = math.sqrt(65.0 ** 2 - (sf / 2) ** 2)
    sol = sol.cut(cyl_z(sf / 2, zs, 70.0, x))
    sol = sol.cut(cyl_z(G38_MENOR / 2, zs - p, zs + 0.5, x))
    sol = sol.cut(cyl_z(d_paso / 2, 30.0, zs - p + 0.5, x))
    return sol


G38_MENOR = 18.631         # G 1/2 (ISO 228-1): Ø menor de la rosca interior (taladro de núcleo); rev. 8


def geo(C):
    """Posiciones (x local desde E) y medidas que usan el modelo y las láminas."""
    s = C["s"]
    T, CA, F, TP, PI, V, OQ = C["tapa"], C["camisa"], C["fondo"], C["tapa"], C["piston"], C["vastago"], C["ojal_vastago"]
    o = dict(s0=s["fondo_ext"], si=s["fondo_int"], sk=s["cjp"], sp=s["espiga"], st=s["rosca_ini"], se=s["camisa_fin"], sb=s["cuerpo_fin"])
    o.update(a=C["D_camisa"] / 2.0, b=CA["D"] / 2.0, dr=float(C["d_vastago"]), L0=float(C["L0"]), hn=float(PI["tuerca"]["alto"]), Lpc=float(PI["largo"]))
    o["tb"] = (o["b"] - o["a"] - float(CA["bisel_trasero"]["talon"])) * T30          # largo axial del bisel V 30°
    return o


# ---------------------------------------------------------------------------------------------- piezas en ejes locales
def piezas_locales(C, e=0.0):
    """{clave: sólido} del cilindro en ejes locales (x desde E, eje en z = 0); e = extensión del vástago (L − L0)."""
    o = geo(C)
    s0, si, sk, sp, st, se, sb, a, b = o["s0"], o["si"], o["sk"], o["sp"], o["st"], o["se"], o["sb"], o["a"], o["b"]
    F, CA, T, PI, V, OQ = C["fondo"], C["camisa"], C["tapa"], C["piston"], C["vastago"], C["ojal_vastago"]
    tal = float(CA["bisel_trasero"]["talon"]); tb_ = o["tb"]; gap = float(CA["bisel_trasero"]["separacion"])   # rev. 8: separación de raíz camisa–hombro
    out = {}
    # ---- fondo (rev. 8): bloque macizo Ø cuerpo (pestaña) + espiga Ø camisa dentro de la camisa; la cara de la espiga es el tope del retraído
    Lesp = float(F["espiga"]["largo"])
    fo = rev([(s0, 0), (s0, b - 1.0), (s0 + 1.0, b), (sk, b), (sk, a), (si - 1.0, a), (si, a - 1.0), (si, 0)])
    out["cil_fondo"] = fo
    # ---- camisa: J (bisel 10° + radio) atrás sobre la espiga; rosca interior M110 (al Ø nominal) adelante; entrada de sellos 15°; puertos A y B G 1/2; prisionero M8 abajo
    xc0 = sk + gap
    Jw = float(CA["bisel_trasero"]["largo_bisel"])
    Lt = float(T["rosca"]["w"][1] - T["rosca"]["w"][0]) + 4.0                       # largo de la rosca en la camisa (= L_t)
    dR = float(CA["chaflan_sellos"]["largo"]) * math.tan(math.radians(float(CA["chaflan_sellos"]["ang"])))
    rT = float(C["tapa"]["rosca"]["designacion"].split("×")[0].strip()[1:]) / 2.0
    xs = se - Lt
    ca = rev([(xc0, a), (xc0, a + tal), (xc0 + Jw, b), (se, b), (se, rT), (xs, rT), (xs, a + dR), (xs - float(CA["chaflan_sellos"]["largo"]), a)])
    for kp, dpk in (("puerto_A", CA["puerto_A"]["paso"]), ("puerto_B", CA["puerto_B"]["paso"])):
        ca = puerto(ca, xc0 + float(CA[kp]["x_desde_extremo_trasero"]), float(dpk), CA[kp])
    ca = ca.cut(cyl_z(3.4, -66.0, -(rT) + 0.5, se - float(CA["prisionero_tapa"]["x_desde_extremo"])))
    out["cil_camisa"] = ca
    # ---- tapa delantera (w desde la cara de la espiga)
    E_ = T["espiga"]
    re_ = float(E_["d"]) / 2
    ro = T["espiga"]["ranura_oring"]["w"]
    S4 = next(q for q in C["sellos"] if q["pos"] == "S4")["alojamiento"]
    rg4 = float(S4["d_fondo"]) / 2
    G = T["rosca"]["garganta"]
    rgT = float(G["d"]) / 2
    ext = [(sp, re_ - 1.5 * T15), (sp + 1.5, re_), (sp + ro[0], re_), (sp + ro[0], rg4), (sp + ro[1], rg4), (sp + ro[1], re_), (st, re_), (st, rT - 1.0), (st + 1.0, rT),
           (sp + G["w"][0], rT), (sp + G["w"][0], rgT), (sp + G["w"][1], rgT), (sp + G["w"][1], b), (sb, b)]
    rv = o["dr"] / 2
    inn = [(sp, rv)]
    for h in T["alojamientos_vastago"]:
        w0, w1, rh = float(h["w"][0]), float(h["w"][1]), float(h["d"]) / 2
        inn += [(sp + w0, rv), (sp + w0, rh), (sp + w1, rh), (sp + w1, rv)]
        if h.get("labio"):
            inn[-1] = (sp + w1, float(h["labio"]["d"]) / 2)
            inn += [(sp + float(h["labio"]["w"][1]), float(h["labio"]["d"]) / 2)]
    inn = inn[:-1] + [(sb, inn[-1][1])] if abs(inn[-1][0] - sb) > 1e-6 else inn
    pts = ext + list(reversed(inn))
    ta = rev(pts)
    LL = T["reborde"]["agujeros_llave"]
    for k in range(int(LL["n"])):
        th = math.radians(45.0 + 90.0 * k)
        ta = ta.cut(cyl_x(float(LL["d"]) / 2, sb - float(LL["prof"]), sb + 1.0, float(LL["pcd"]) / 2 * math.cos(th), float(LL["pcd"]) / 2 * math.sin(th)))
    out["cil_tapa"] = ta
    # ---- tuerca ranurada (cara contra el fondo en x = si + e)
    hn, Lpc = o["hn"], o["Lpc"]
    TU = PI["tuerca"]
    rN, dth = float(TU["D"]) / 2, float(V["rosca"]["designacion"].split("×")[0].strip()[1:])
    n0 = si + e
    av = TU["avellanado"]
    tu = rev([(n0, dth / 2), (n0, rN - 1.0), (n0 + 1.0, rN), (n0 + hn, rN), (n0 + hn, float(av["d"]) / 2), (n0 + hn - float(av["prof"]), float(av["d"]) / 2), (n0 + hn - float(av["prof"]), dth / 2)])
    for k in range(int(TU["ranuras"]["n"])):
        th = math.radians(90.0 * k)
        bw, bd = float(TU["ranuras"]["ancho"]), float(TU["ranuras"]["prof"])
        sl = box(n0 - 1, n0 + hn + 1, -bw / 2, bw / 2, rN - bd, rN + 2).rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 45.0 + math.degrees(th))
        tu = tu.cut(sl)
    for th in (0.0, 180.0):
        hole = cyl_z(2.5, dth / 2 - 1.0, rN + 1.0, n0 + (hn - float(av["prof"])) / 2).rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), th)
        tu = tu.cut(hole)
    out["cil_tuerca"] = tu
    # ---- pistón (u desde la cara contra la tuerca)
    p0 = si + e + hn
    u = PI["u"]
    rP, rgu = float(PI["D"]) / 2, float(C["sellos"][1]["alojamiento"]["d_fondo"]) / 2
    rS1 = float(C["sellos"][0]["alojamiento"]["d_fondo"]) / 2
    rAl = float(u["d_alivio"]) / 2
    rB = float(PI["d"]) / 2
    rO3 = float(C["sellos"][2]["alojamiento"]["d_fondo"]) / 2
    ch = float(u["chaflan"][1])
    pi_ = rev([(p0, rB), (p0, rP - ch), (p0 + ch, rP), (p0 + u["guia1"][0], rgu), (p0 + u["guia1"][1], rgu), (p0 + u["guia1"][1], rP), (p0 + u["sello"][0], rP), (p0 + u["sello"][0], rS1),
               (p0 + u["sello"][1], rS1), (p0 + u["sello"][1], rP), (p0 + u["guia2"][0], rP), (p0 + u["guia2"][0], rgu), (p0 + u["guia2"][1], rgu), (p0 + u["guia2"][1], rP),
               (p0 + u["alivio"][0], rP), (p0 + u["alivio"][0], rAl), (p0 + Lpc, rAl), (p0 + Lpc, rB), (p0 + u["ranura_oring"][1], rB), (p0 + u["ranura_oring"][1], rO3),
               (p0 + u["ranura_oring"][0], rO3), (p0 + u["ranura_oring"][0], rB)])
    # el primer tramo (chaflán → ranura de guía) sin resalte: la ranura de la guía abre en el chaflán (u = 1)
    out["cil_piston"] = pi_
    # ---- vástago: rosca (al Ø nominal) con chaflán, garganta, asiento, resalte con chaflán de entrada 20°, Ø vástago hasta la soldadura del ojal
    r0 = si + e
    LQ = o["L0"] + e                                                                  # eje del ojal del vástago
    xw = LQ - float(V["extremo_ojal"]["x_desde_eje_ojal"])
    Lr = float(V["rosca"]["largo"])
    rgV = float(V["garganta"]["d"]) / 2
    ga = float(V["garganta"]["ancho"])
    ra = float(V["asiento"]["d"]) / 2
    chR = 3.0 * T20
    va = rev([(r0, 0), (r0, dth / 2 - 1.5), (r0 + 1.5, dth / 2), (r0 + Lr, dth / 2), (r0 + Lr, rgV), (r0 + Lr + ga, rgV), (r0 + Lr + ga, ra), (r0 + hn + Lpc, ra),
              (r0 + hn + Lpc, rv - chR), (r0 + hn + Lpc + 3.0, rv), (xw, rv), (xw, 0)])
    out["cil_vastago"] = va
    # ---- ojal del vástago: anillo R × ancho (eje z) con agujero; cuello de ancho Ø_vástago y espesor = ancho hasta R_cubo + 10; espiga Ø_vástago hasta la soldadura
    RQ, bQ, dQ = float(OQ["R"]), float(OQ["ancho"]), float(OQ["d"])
    xn1 = float(OQ["cuello"]["x1"])
    ringQ = cq.Solid.makeCylinder(RQ, bQ, cq.Vector(0, 0, -bQ / 2), cq.Vector(0, 0, 1), 180).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 90).fuse(
        cq.Solid.makeCylinder(RQ, bQ, cq.Vector(0, 0, -bQ / 2), cq.Vector(0, 0, 1), 180).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 270)).translate(cq.Vector(LQ, 0, 0))   # aristas en ±y (extremos del ojal)
    oq = ringQ.fuse(box(LQ - xn1, LQ - float(OQ["cuello"]["x0"]) + 2.0, -rv, rv, -bQ / 2, bQ / 2)).fuse(cyl_x(rv, xw, LQ - xn1 + 0.01))
    oq = oq.cut(cyl_z(dQ / 2, -bQ, bQ, LQ))
    oq = oq.cut(cyl_x(3.4, LQ + dQ / 2 - 1.0, LQ + RQ + 1.0))                         # grasera M8 × 1 radial (taladro de núcleo Ø6,8)
    out["cil_ojal_Q"] = oq
    # ---- ojal trasero (orejeta): R alrededor de E, cuello hasta el fondo; alojamiento de la rótula con resalte y ranura del anillo elástico
    OE = F["ojal"]
    RE, bE, wE = float(OE["R"]), float(OE["ancho"]), float(OE["cuello"]) / 2
    AL = OE["alojamiento"]
    half = cq.Solid.makeCylinder(RE, bE, cq.Vector(0, 0, -bE / 2), cq.Vector(0, 0, 1), 180).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 90)   # semicírculo trasero (x ≤ 0)
    front = cyl_z(RE, -bE / 2, bE / 2).intersect(box(0.0, s0, -RE - 1, RE + 1, -bE, bE))
    trap = box(0.0, s0, -wE, wE, -bE / 2, bE / 2)                                      # cuello recto de ancho 2w hasta el fondo
    lug = half.fuse(front).fuse(trap)
    z0 = -bE / 2
    rs_ = AL["resalte"]
    lug = lug.cut(cyl_z(float(rs_["d"]) / 2, z0 - 1, z0 + float(rs_["ancho"])))
    lug = lug.cut(cyl_z(float(AL["d"]) / 2, z0 + float(rs_["ancho"]), bE / 2 + 1))
    rn = AL["ranura"]
    lug = lug.cut(cyl_z(float(rn["d"]) / 2, z0 + float(rn["w"][0]), z0 + float(rn["w"][1])))
    out["cil_ojal_E"] = lug
    # ---- rótula GE70ES (comercial): anillo interior B y exterior C, asentada contra el resalte
    RT_ = OE["rotula"]
    zc_o = z0 + float(rs_["ancho"]) + float(RT_["C"]) / 2
    rk = (float(RT_["d"]) + float(RT_["D"])) / 4 + 2.0
    ro_ = cyl_z(float(RT_["D"]) / 2, zc_o - float(RT_["C"]) / 2, zc_o + float(RT_["C"]) / 2).cut(cyl_z(rk, -60, 60))
    ri_ = cyl_z(rk, zc_o - float(RT_["B"]) / 2, zc_o + float(RT_["B"]) / 2).cut(cyl_z(float(RT_["d"]) / 2, -60, 60))
    out["cil_rotula"] = ro_.fuse(ri_).clean()
    # ---- sellos (anillos de sección rectangular dentro de su alojamiento, 0,1 mm de holgura axial)
    hz = 0.1
    S = {q["pos"]: q for q in C["sellos"]}
    out["cil_S1"] = ring_x(p0 + u["sello"][0] + hz, p0 + u["sello"][1] - hz, rS1 + 0.05, rP)
    out["cil_S2"] = cq.Compound.makeCompound([ring_x(p0 + u["guia1"][0] + hz, p0 + u["guia1"][1] - hz, rgu + 0.05, rP), ring_x(p0 + u["guia2"][0] + hz, p0 + u["guia2"][1] - hz, rgu + 0.05, rP)])
    out["cil_S3"] = ring_x(p0 + u["ranura_oring"][0] + hz, p0 + u["ranura_oring"][1] - hz, rB, rO3 - 0.05)
    out["cil_S4"] = ring_x(sp + ro[0] + hz, sp + ro[1] - hz, rg4 + 0.05, a)
    hv = {h["ref"] + ("b" if h["ref"] == "S7" and i > 2 else ""): h for i, h in enumerate(T["alojamientos_vastago"])}
    def rr(h):
        return ring_x(sp + float(h["w"][0]) + hz, sp + float(h["w"][1]) - hz, rv, float(h["d"]) / 2 - 0.05)
    out["cil_S5"] = rr(hv["S5"])
    out["cil_S6"] = rr(hv["S6"])
    out["cil_S7"] = cq.Compound.makeCompound([rr(hv["S7"]), rr(hv["S7b"])])
    out["cil_S8"] = rr(hv["S8"])
    return out


def colocar(sol, E, a_deg, zc):
    return sol.translate(cq.Vector(0, 0, zc)).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), a_deg).translate(cq.Vector(E[0], E[1], 0))


# ---------------------------------------------------------------------------------------------- modelo 3D
DESC = {
    "cil_camisa": "Camisa del cilindro", "cil_fondo": "Fondo macizo del cilindro (bloque con espiga)", "cil_ojal_E": "Ojal trasero del cilindro (orejeta soldada al fondo)",
    "cil_tapa": "Tapa delantera roscada del cilindro (prensaestopas)", "cil_piston": "Pistón del cilindro", "cil_tuerca": "Tuerca ranurada del pistón",
    "cil_vastago": "Vástago cromado del cilindro", "cil_ojal_Q": "Ojal del vástago (soldado por fricción)", "cil_rotula": "Rótula radial GE70ES del ojal trasero",
}


def build(m, g, D, log=print):
    """Reemplaza la pieza comercial «cilindro_pv» por las piezas del cilindro fabricado (2 cilindros, posición dibujada del núcleo)."""
    C = C_(g)
    if C is None:
        return
    from modelo3d_tt300c import Part
    fr = m.info["pivotado"]["frames"]
    zc, L0 = g.zc, float(C["L0"])
    sols = {k: [] for k in KEYS}
    for k_ in ("1_antihorario", "2_antihorario"):
        F = fr[k_]
        loc = piezas_locales(C, F["L"] - L0)
        for k, so in loc.items():
            sols[k].append(colocar(so, F["E"], F["a_cil"], zc))
    m.info["cilindro_bx"] = dict(e={k_: fr[k_]["L"] - L0 for k_ in fr})
    old = m.get("cilindro_pv")
    idx = m.parts.index(old) if old else len(m.parts)
    if old:
        m.parts.remove(old)
    n = len(sols["cil_camisa"])
    M = {"cil_camisa": C["camisa"]["material"], "cil_fondo": C["fondo"]["material"], "cil_ojal_E": C["fondo"]["ojal"]["material"], "cil_tapa": C["tapa"]["material"],
         "cil_piston": C["piston"]["material"], "cil_tuerca": C["piston"]["tuerca"]["material"] + "+QT (EN 10083-3)", "cil_vastago": C["vastago"]["material"], "cil_ojal_Q": C["ojal_vastago"]["material"]}
    PR = {"cil_camisa": "Barra hueca 132 × 80: corte, torneado exterior e interior; soldadura al fondo; alivio; bruñido Ø" + f(C["camisa"]["d"]) + " " + C["camisa"]["tol_d"] + "; rosca interior; puerto B",
          "cil_fondo": "Torneado del bloque macizo desde plancha de 40 (pestaña y espiga g6); soldadura de la orejeta y a la camisa (CJP en J)",
          "cil_ojal_E": "Oxicorte de plancha de 50 con sobremetal; contorno fresado; biseles en K; alojamiento mecanizado en línea después de soldar",
          "cil_tapa": "Torneado CNC de plancha de 63: espiga, rosca exterior, alojamientos de sellos y agujeros de llave", "cil_piston": "Torneado CNC de barra bonificada; alojamientos de sellos y guías",
          "cil_tuerca": "Torneado CNC; rosca interior; ranuras de llave fresadas; agujeros de los prisioneros", "cil_vastago": "Barra cromada: corte, torneado del extremo, rosca; soldadura por fricción del ojal; rectificado y cromado",
          "cil_ojal_Q": "Oxicorte de plancha de 80; fresado del ojal y el cuello a 50; torneado de la espiga; soldadura por fricción; agujero H9 mecanizado al final"}
    TR = {"cil_camisa": "Alivio de tensiones con el fondo 580–620 °C (WPS-CIL-01)", "cil_fondo": "Alivio de tensiones con la camisa", "cil_ojal_E": "Alivio de tensiones con la camisa",
          "cil_piston": "Bonificado (QT)", "cil_tuerca": "Bonificado (QT)", "cil_vastago": "Cromo duro ≥ " + f(C["vastago"]["cromo"]["espesor_min_um"]) + " µm, " + C["vastago"]["cromo"]["dureza"], "cil_ojal_Q": "—", "cil_tapa": "—"}
    nuevos = []
    for k in FAB:
        p = Part(k, "ACC", DESC[k], _desc(C, k), cq.Workplane("XY").newObject([cq.Compound.makeCompound(sols[k])]), n, M[k], PR[k], core="cyl", color=(0.95, 0.78, 0.1) if k not in ("cil_vastago",) else (0.8, 0.8, 0.85),
                 tratamiento=TR.get(k, "—"), num_fijo=NUM[k])
        nuevos.append(p)
    RT_ = C["fondo"]["ojal"]["rotula"]
    nuevos.append(Part("cil_rotula", "ACC", DESC["cil_rotula"], f"{RT_['designacion']}: d {f(RT_['d'])}, D {f(RT_['D'])}, B {f(RT_['B'])}, C {f(RT_['C'])}; C₀ = {f(RT_['C0_kN'])} kN (dato confirmado por el mandante 19-11-2026)",
                       cq.Workplane("XY").newObject([cq.Compound.makeCompound(sols["cil_rotula"])]), n, "Acero de rodamientos / acero templado (comercial)", "Comercial", core="cyl", comercial=True,
                       catalogo=RT_["designacion"], color=(0.3, 0.3, 0.32), num_fijo=NUM["cil_rotula"]))
    for q in C["sellos"]:
        k = "cil_" + q["pos"]
        nuevos.append(Part(k, "ACC", f"Sello {q['pos']}: {q['nombre']}", f"{q['designacion']} ({q['norma']}); {int(q['cantidad'])} por cilindro", cq.Workplane("XY").newObject([cq.Compound.makeCompound(sols[k])]),
                           n, q["material"], "Comercial", rho=1.5e-6, core=None, comercial=True, catalogo=f"{q['designacion']} — {q['norma']} (código del proveedor A DEFINIR)", color=(0.1, 0.1, 0.1),
                           in_core=False, num_fijo=NUM[k]))
    for i, p in enumerate(nuevos):
        m.parts.insert(idx + i, p)
        m.sub_count["ACC"] = m.sub_count.get("ACC", 0) + 1
        p.num = p.num_fijo
    m.renumerar()
    log(f"  cilindro fabricado (bx.cilindro): {len(nuevos)} ítems en lugar de la pieza comercial ACC-013")


def _desc(C, k):
    T, CA, F, PI, V, OQ = C["tapa"], C["camisa"], C["fondo"], C["piston"], C["vastago"], C["ojal_vastago"]
    if k == "cil_camisa":
        return f"Ø{f(CA['D'])} {CA['tol_D']} × Ø{f(CA['d'])} {CA['tol_d']} (Ra {fm(CA['Ra_d'], 1)}) × {fm(CA['largo'], 1)}; rosca {CA['rosca']['designacion']}; puertos A y B {CA['puerto_B']['rosca']}"
    if k == "cil_fondo":
        return f"Bloque macizo {f(F['t'])}: pestaña Ø{f(F['D'])} × {f(F['pestana'])} + espiga Ø{f(F['espiga']['d'])} {F['espiga']['tol']} × {f(F['espiga']['largo'])} (tope del retraído)"
    if k == "cil_ojal_E":
        return f"Orejeta R{fm(F['ojal']['R'], 1)} × {f(F['ojal']['ancho'])}, cuello {f(F['ojal']['cuello'])}; alojamiento Ø{f(F['ojal']['alojamiento']['d'])} {F['ojal']['alojamiento']['tol']} para la rótula"
    if k == "cil_tapa":
        return f"Espiga Ø{fm(T['espiga']['d'], 1)} {T['espiga']['tol']}, rosca {T['rosca']['designacion']}, reborde Ø{f(T['reborde']['d'])} × {fm(T['reborde']['w'][1] - T['reborde']['w'][0], 0)}; agujero Ø{f(T['agujero']['d'])} {T['agujero']['tol']}; largo {f(T['largo'])}"
    if k == "cil_piston":
        return f"Ø{fm(PI['D'], 1)} {PI['tol_D']} × {f(PI['largo'])}; agujero Ø{f(PI['d'])} {PI['tol_d']}"
    if k == "cil_tuerca":
        return f"{PI['tuerca']['designacion']}, Ø{f(PI['tuerca']['D'])} × {f(PI['tuerca']['alto'])}"
    if k == "cil_vastago":
        return f"Ø{f(V['d'])} {V['tol']} × {fm(V['largo'], 1)} (hasta la soldadura del ojal); rosca {V['rosca']['designacion']}; cromo ≥ {f(V['cromo']['espesor_min_um'])} µm"
    if k == "cil_ojal_Q":
        return f"R{fm(OQ['R'], 1)} × {f(OQ['ancho'])}, agujero Ø{f(OQ['d'])} {OQ['tol_d']} (sin rótula), espiga Ø{f(OQ['espiga']['d'])}"
    return ""


# ---------------------------------------------------------------------------------------------- soldaduras del cilindro (registro único)
def welds(ctx, add_n):
    """J37 CJP en J fondo macizo–camisa, J38 CJP en K del ojal trasero al fondo, J39 soldadura por fricción vástago–ojal (bx.cilindro)."""
    g = ctx.g
    C = C_(g)
    if C is None or not ctx.m.get("cil_camisa"):
        return
    sc = lambda k: ctx.code(k).replace(CODE + "-", "").replace("-" + REV, "")
    n = int(C["n"])
    F, OE, CA = C["fondo"], C["fondo"]["ojal"], C["camisa"]
    tw_ = (float(CA["D"]) - float(CA["d"])) / 2
    A5 = "E7018 (AWS A5.1) / ER70S-6 (AWS A5.18)"
    j = add_n(37, "Fondo macizo – camisa del cilindro (CJP en J en el hombro sobre la espiga integral, detrás del tope)", f"{sc('cil_fondo')} / {sc('cil_camisa')}",
              F["cjp"]["tipo"], "J", t=tw_, groove=True,
              prep=f"J (bisel 10°, radio {fm(CA['bisel_trasero']['radio_J'], 0)}) en el extremo de la camisa, talón {fm(CA['bisel_trasero']['talon'], 0)} mm, separación de raíz {fm(CA['bisel_trasero']['separacion'], 0)} mm contra el hombro a escuadra; respaldo permanente = espiga integral del fondo; filete de refuerzo z6 en el pie",
              prep_txt="10°", nivel="ISO 5817-B", end="UT 100 % · MT 100 %", wps=19, len_total=n * math.pi * float(CA["D"]), aporte=A5, proc="141 + 111 (PROPUESTA)",
              nota=F["cjp"]["proceso"], t_pre=tw_)
    # rev. 9c: precalentamiento único del cilindro (núcleo bx.cilindro.fondo.cjp.precalentamiento_C, más exigente que la Tabla 5.8 por la parte más gruesa)
    pre_c = F["cjp"].get("precalentamiento_C")
    t37 = max(tw_, float(F["t"]))                 # parte más gruesa de la junta: el bloque del fondo (no la pared de la camisa)
    j.update(t_pre=t37)
    if pre_c is not None:
        j.update(pre_c=float(pre_c), pre_txt=f"{fm(pre_c, 0)} °C mín. ({F['cjp']['wps']} del núcleo; AWS D1.1:2020 Tabla 5.8 pediría {propuestas.precalentamiento(t37)} °C por la parte más gruesa, el fondo de {fm(t37, 0)} mm)")
    j.update(backing="M", backing_txt="M: respaldo permanente = espiga integral del fondo", fam_txt=f"CJP en J circunferencial de la camisa S355J2 (pared {fm(tw_, 0)}) sobre la espiga integral del fondo S355J2; {F['cjp']['proceso']}; {F['cjp']['wps']}")
    j = add_n(38, "Ojal trasero (orejeta) – fondo del cilindro (CJP en K todo alrededor + filete de refuerzo z6)", f"{sc('cil_ojal_E')} / {sc('cil_fondo')}",
              OE["soldadura"]["tipo"], "bevel", t=float(OE["ancho"]), groove=True,
              prep="Doble bisel 45° (K) en la orejeta, talón 2 mm, separación 2 mm, resanado de raíz por el otro lado; filete de refuerzo z6", prep_txt="45°", nivel="ISO 5817-B",
              end="UT 100 % · MT 100 %", wps=20, len_total=n * 2 * (float(OE["cuello"]) + float(OE["ancho"])), aporte=A5, proc="135 / 111 (PROPUESTA)", contorno=True, t_pre=float(OE["ancho"]))
    mf_ = str(F.get("material") or "S355J2+N").split(" (")[0]
    pre_e = OE["soldadura"].get("precalentamiento_C", pre_c)
    t38 = max(float(OE["ancho"]), float(F["t"]))
    if pre_e is not None:
        j.update(pre_c=float(pre_e), pre_txt=f"{fm(pre_e, 0)} °C mín. ({OE['soldadura']['wps']} del núcleo; AWS D1.1:2020 Tabla 5.8 pediría {propuestas.precalentamiento(t38)} °C por la parte más gruesa, la orejeta de {fm(t38, 0)} mm)")
    j.update(pasadas_txt=f"{j['pasadas']} (raíz + relleno + tapa por un lado; resanado de raíz y pasadas por el otro lado; sin respaldo)")
    j.update(en_T=True, fam_txt=f"CJP en K (T) de la orejeta S355J2+N de {f(OE['ancho'])} sobre el fondo {mf_} con filete de refuerzo z6; {OE['soldadura']['wps']}")
    V = C["vastago"]
    j = add_n(39, "Vástago – ojal del vástago: soldadura por fricción rotativa a tope Ø" + f(C["d_vastago"]), f"{sc('cil_vastago')} / {sc('cil_ojal_Q')}",
              C["ojal_vastago"]["soldadura"]["tipo"], "square", t=float(C["d_vastago"]), groove=True,
              prep=f"Caras planas a tope Ø{f(C['d_vastago'])}, perpendicularidad 0,05; rebaba (flash) eliminada; {V['extremo_ojal']['nota']}", prep_txt="", nivel="ISO 15620",
              end=C["ojal_vastago"]["soldadura"]["end"].replace(" + ", " · "), wps=21, len_total=n * math.pi * float(C["d_vastago"]), aporte="sin aporte (fricción)", proc="42 (fricción, ISO 4063)", t_pre=0.0)
    na_ = "No aplica (proceso 42 sin arco ni aporte)"
    j.update(fam_txt="Soldadura por fricción rotativa a tope (ISO 4063 proceso 42), procedimiento calificado según ISO 15620 con ensayos de tracción y doblado; sin aporte",
             corr_gmaw=na_, corr_smaw=na_, corr_fcaw=na_, pre_txt="No aplica (parámetros de fricción del procedimiento calificado ISO 15620)", interpase_txt="No aplica",
             pasadas_txt="No aplica (una operación de fricción)", pasadas="—", garganta=f"a tope en toda la sección Ø{f(C['d_vastago'])} (fricción)", origen="núcleo BX (bx.cilindro.ojal_vastago.soldadura; ISO 15620)")
