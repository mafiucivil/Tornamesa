"""Láminas del cilindro hidráulico FABRICADO del juego TT300-BX (rev. 7d): subconjunto ACC-013 (corte longitudinal con globos a cada pieza y a
cada sello, retraído y extendido, puertos, tabla de sellos, pares, prueba, aceite y secuencia) y una lámina por pieza fabricada:
ACC-028 camisa, ACC-029 fondo macizo con espiga y el ojal trasero soldado (ACC-030), ACC-031 tapa delantera, ACC-032 pistón y tuerca (ACC-033),
ACC-034 vástago y ACC-035 ojal del vástago. Fuente única: bloque bx.cilindro del JSON (cotas, tolerancias, rugosidades, alojamientos).
Se registran desde hojas_bx.activar() solo si el JSON trae bx.cilindro."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cadquery as cq
from pie_common import *
import cil_bx
import iso286

SUB = "ACC-013"


def _C(ctx):
    return cil_bx.C_(ctx.g)


def _loc(ctx, key, nk, e=0.0, dx=0.0, rot=None):
    """Copia local de la pieza key del cilindro 1 en ejes del cilindro (x desde E, eje en z = 0), desplazada −dx."""
    C = _C(ctx)
    so = cil_bx.piezas_locales(C, e)[key]
    so = so.translate(cq.Vector(-dx, 0, 0))
    if rot:
        so = so.rotate(cq.Vector(0, 0, 0), cq.Vector(*rot[0]), rot[1])
    ctx.shapes[nk] = cq.Compound.makeCompound(so.Solids() if hasattr(so, "Solids") else [so])
    ctx.mat[nk] = ctx.mat.get(key, "acero")
    return nk


def _fit(d, code):
    try:
        return f"Ø{fm(d, 1 if abs(d - round(d)) > 1e-6 else 0)} {code} ({iso286.fmt_dev(d, code)})"
    except Exception:
        return f"Ø{fm(d, 1 if abs(d - round(d)) > 1e-6 else 0)} {code}"


def _seal(C, pos):
    return next(q for q in C["sellos"] if q["pos"] == pos)


def _aloj_txt(q):
    a = q["alojamiento"]
    an = a["ancho"]
    an_t = " y ".join(fm(x, 1) for x in an) if isinstance(an, list) else fm(an, 1)
    return f"Ø{fm(a['d_fondo'], 1)} {a['tol_fondo']} × {an_t} {a.get('tol_ancho', '')}".strip()


def _rows_sellos(C, piezas=None):
    rows = []
    for q in C["sellos"]:
        if piezas and q["pieza"] not in piezas:
            continue
        a = q["alojamiento"]
        extra = []
        if a.get("radio_fondo"):
            extra.append(f"r fondo {fm(a['radio_fondo'], 1)}")
        if a.get("radio_borde"):
            extra.append(f"r borde {fm(a['radio_borde'], 1)}")
        if a.get("Ra_fondo"):
            extra.append(f"Ra fondo {fm(a['Ra_fondo'], 1)}")
        if a.get("Ra_contacto"):
            extra.append(f"Ra contacto {fm(a['Ra_contacto'], 1)}")
        if a.get("d_labio"):
            extra.append(f"labio Ø{fm(a['d_labio'], 0)}")
        rows.append([q["pos"], q["nombre"], q["norma"], q["designacion"], _aloj_txt(q) + ("; " + ", ".join(extra) if extra else ""), q["material"], str(int(q["cantidad"]))])
    return rows


SEAL_COLS = [("Pos.", 9, "C"), ("Elemento", 50, "L"), ("Norma", 22, "L"), ("Designación / código", 50, "L"), ("Alojamiento (Ø fondo tol. × ancho; radios; Ra)", 66, "L"), ("Material", 30, "L"), ("Cant./cil.", 11, "C")]


# =========================================================================================================== ACC-013: subconjunto
def sheet_cil_conjunto(ctx):
    g, P = ctx.g, ctx.P
    C = _C(ctx)
    o = cil_bx.geo(C)
    from hojas_con import Conj, alias, balloons_auto
    if not hasattr(ctx, "subconjuntos"):
        ctx.subconjuntos = set()
    keys = [k for k in cil_bx.KEYS if ctx.m.get(k)]
    c = Conj.__new__(Conj)
    c.keys = keys
    c.p0 = ctx.m.get(keys[0])
    h = Hoja(ctx, SUB, "CILINDRO HIDRÁULICO FABRICADO (DOBLE EFECTO, MODO PIVOTADO): SUBCONJUNTO — CORTE LONGITUDINAL, SELLOS, PUERTOS, PRUEBA Y MONTAJE", "", fmt="A1",
             material="Ver despiece y láminas ACC-028 a ACC-035", masa=f"{fm(C['masa_total'], 1)} kg c/u (con aceite)", trat="Ver notas", serie="CON", items=[ctx.code(k) for k in keys])
    c.init_plano(ctx, h)
    c.iso_keys = []
    c.fmt_try = None
    ctx.subconjuntos.add(h.plano)
    s = c.s
    loc = {k: _loc(ctx, k, k + "_R", 0.0) for k in keys}
    lk = list(loc.values())
    L0, Lx = float(C["L0"]), float(C["L_ext"])
    s0, sb = o["s0"], o["sb"]

    def corte(V, c_):
        s.line(V.P(-95, 0, 0), V.P(L0 + 80, 0, 0), "EJE")
        V.dimh((0, 0, 0), (L0, 0, 0), "top", 2, on=lk, virt_a=35.0, virt_b=float(C["ojal_vastago"]["d"]) / 2, text=f"{f(L0)} (retraído)")
        V.dimh((0, 0, 0), (s0, 0, 40), "top", 0, on=lk, virt_a=35.0, text=f"{f(C['e_cuerpo'])}")
        V.dimh((s0, 0, 60), (sb, 0, 60), "top", 0, on=lk, text=f"{f(C['cuerpo'])} (cuerpo)")
        V.dimh((sb, 0, 40), (L0, 0, 0), "top", 0, on=lk, virt_b=float(C["ojal_vastago"]["d"]) / 2, text=f"({f(C['c_vastago'])})")
        V.dim((sb - 7, 0, -65), (sb - 7, 0, 65), -14, orient="v", on=lk, text=f"Ø{f(C['camisa']['D'])}")
        V.dim((o['si'] + 60, 0, -45), (o['si'] + 60, 0, 45), 0, orient="v", on=lk, text=f"Ø{f(C['D_camisa'])} H8")
        with alias(ctx, "_R"):
            balloons_auto(c_, V, lk, gap=11.0, off=24.0, sides="lr")
        x0_, y0_, x1_, y1_ = V.ext
        # símbolos bajo la vista: J38 y J39 en la primera fila (a ambos lados de la escala del título), J37 en la segunda fila al centro
        for jid, p3, qx, dy in (("J38", (s0, 0, -float(C["fondo"]["ojal"]["ancho"]) / 2 - 1), 12.0, 24), ("J37", (o["sk"], 0, -65.0), 110.0, 38),
                                ("J39", (L0 - float(C["vastago"]["extremo_ojal"]["x_desde_eje_ojal"]), 0, -o["dr"] / 2), 215.0, 24)):
            a_ = V.P(p3)
            c_.h.weld(jid, a_, (x0_ + qx, y0_ - dy), sh=1)
    c.vs("corte", lk, "front", cut=CUT_Y, lv=(1, 5, 1, 3), extra=(10, 8, 10, 8), draw=corte, hs=0.6, w=3.0, mat={k: ctx.mat.get(k, "acero") for k in lk}, auto=False, mins=0.4,
         title=f"CORTE LONGITUDINAL A-A, RETRAÍDO ({f(L0)} ENTRE EJES): CAMISA, FONDO, TAPA, PISTÓN, VÁSTAGO, OJALES Y SELLOS")
    lx = [_loc(ctx, k, k + "_X", float(C["carrera"])) for k in keys if k in ("cil_camisa", "cil_fondo", "cil_ojal_E", "cil_tapa", "cil_vastago", "cil_ojal_Q", "cil_rotula")]

    def ext(V, c_):
        s.line(V.P(-95, 0, 0), V.P(Lx + 80, 0, 0), "EJE")
        V.dimh((0, 0, 0), (Lx, 0, 0), "bottom", 0, on=lx, virt_a=35.0, virt_b=float(C["ojal_vastago"]["d"]) / 2, text=f"{f(Lx)} (extendido)")
        zsf = math.sqrt(65.0 ** 2 - (float(C["camisa"]["puerto_A"]["refrentado"]) / 2) ** 2)
        xa = o["sk"] + float(C["camisa"]["separacion_raiz"]) + float(C["camisa"]["puerto_A"]["x_desde_extremo_trasero"])
        V.note_pt((xa + 12, 0, zsf), (-20, 18), "PUERTO A (avance)", on=lx)
        V.note_pt((sb - 25, 0, 65), (-40, 18), "PUERTO B (retorno)", on=lx)
    c.vs("ext", lx, "front", lv=(1, 2, 1, 2), extra=(10, 0, 10, 26), draw=ext, hatch=False, w=1.0, auto=False, title=f"ELEVACIÓN, EXTENDIDO ({f(Lx)} = RETRAÍDO + CARRERA {f(C['carrera'])}); PUERTOS G 1/2 ARRIBA")
    c.table_block("SELLOS COMERCIALES (bx.cilindro.sellos; presiones: trabajo " + f(C["p_alivio"]) + " bar, prueba " + f(C["p_prueba"]) + " bar)", SEAL_COLS, _rows_sellos(C), wide=True)
    cap_ = [list(r) for r in C["capacidad"]["filas"]] + [["Cuerpo / e cuerpo / c vástago", f"{f(C['cuerpo'])} / {f(C['e_cuerpo'])} / {f(C['c_vastago'])} mm (interior {f(C['interior'])} = pistón {f(C['piston']['largo'])} + tuerca {f(C['piston']['tuerca']['alto'])} + carrera)"],
                                                          ["Aceite / masa por cilindro", f"{C['aceite']}; {fm(C['masa_total'], 1)} kg"]]
    n3_ = (len(cap_) + 2) // 3
    c.table_block("DATOS TÉCNICOS Y CAPACIDAD DEL CILINDRO (bx.cilindro.capacidad)", [("Dato", 52, "L"), ("Valor", 152, "L")] * 3,
                  [sum((cap_[i + k * n3_] if i + k * n3_ < len(cap_) else ["", ""] for k in range(3)), []) for i in range(n3_)], wide=True)
    c.table_block("PARES DE APRIETE", [("Unión", 70, "L"), ("Par", 60, "L")], [list(r) for r in C["pares"]])
    c.compact_table(keys, title="DESPIECE DEL SUBCONJUNTO (por cilindro × 2)")
    c.note_block("NOTAS DEL SUBCONJUNTO", list(C["notas"]), numbered=True)
    c.note_block("SECUENCIA DE MONTAJE Y PRUEBA", list(C["secuencia"]), numbered=True)
    c.note_block(REF_GEN_TIT, [REF_GEN])
    c.weld_block(["J37", "J38", "J39"], title="SOLDADURAS DEL SUBCONJUNTO")
    c.build()
    return c.h


# =========================================================================================================== ACC-028: camisa
def sheet_cil_camisa(ctx):
    C = _C(ctx)
    o = cil_bx.geo(C)
    CA = C["camisa"]
    gap = float(CA["separacion_raiz"])
    x0 = o["sk"] + gap
    nk = _loc(ctx, "cil_camisa", "cil_camisa_L", 0.0, dx=x0)
    xA = float(CA["puerto_A"]["x_desde_extremo_trasero"])
    Lc = o["se"] - x0
    a, b = o["a"], o["b"]
    Lt = float(CA["rosca"]["prof"]) + float(CA["rosca"]["salida"])
    xB = float(CA["puerto_B"]["x_desde_extremo_trasero"])
    xP = Lc - float(CA["prisionero_tapa"]["x_desde_extremo"])
    p = Pieza(ctx, ["cil_camisa"], "CILINDRO: CAMISA Ø" + f(CA["D"]) + " × Ø" + f(CA["d"]) + " (BARRA HUECA ST-52 132 × 80 MAQUINADA), ROSCA M110 × 2, PUERTOS A Y B G 1/2", fmt="A1")
    s = p.s
    on = [nk]
    p.iso_keys = [nk]
    tb_ = float(CA["bisel_trasero"]["largo_bisel"])
    zs = math.sqrt(b ** 2 - (float(CA["puerto_B"]["refrentado"]) / 2) ** 2)
    rsf = float(CA["puerto_B"]["refrentado"]) / 2

    def corte(V, p_):
        s.line(V.P(-8, 0, 0), V.P(Lc + 8, 0, 0), "EJE")
        V.dimh((0, 0, a + 1), (xA, 0, zs), "top", 0, on=on, virt_b=rsf, text=f"{fm(xA, 1)} (puerto A)")
        V.dimh((0, 0, a + 1), (Lc, 0, 60), "bottom", 2, on=on, text=f"{fm(CA['largo'], 0)} ±0,2 (corte {fm(CA['largo_corte'], 0)})")
        V.dimh((0, 0, a + 1), (xB, 0, zs), "top", 1, on=on, virt_b=rsf, text=f"{fm(xB, 1)} (puerto B)")
        V.dimh((xB, 0, zs), (Lc, 0, 60), "top", 0, on=on, virt_a=rsf, text=f"({fm(Lc - xB, 1)})")
        V.dimh((Lc - Lt, 0, 50), (Lc, 0, 60), "bottom", 0, on=on, text=f"{fm(Lt, 0)} (rosca {fm(CA['rosca']['prof'], 0)} + salida {fm(CA['rosca']['salida'], 0)})")
        V.dimh((xP, 0, -63), (Lc, 0, -60), "bottom", 1, on=on, virt_a=3.4, text=f"{fm(CA['prisionero_tapa']['x_desde_extremo'], 0)} (M8)")
        V.dim((Lc * 0.45, 0, -b), (Lc * 0.45, 0, b), 14, orient="v", on=on, text=_fit(CA["D"], CA["tol_D"]))
        V.dim((Lc * 0.62, 0, -a), (Lc * 0.62, 0, a), 0, orient="v", on=on, text=_fit(CA["d"], CA["tol_d"]) + f" Ra {fm(CA['Ra_d'], 1)}")
        V.dim((Lc - 4, 0, -55), (Lc - 4, 0, 55), 22, orient="v", on=on, text=f"{CA['rosca']['designacion']}")
        V.note_pt((tb_ / 2, 0, a + 2 + (b - a - 2) / 2), (30, 40), f"Bisel J {fm(CA['bisel_trasero']['ang'], 0)}° R{fm(CA['bisel_trasero']['radio_J'], 0)}, talón {fm(CA['bisel_trasero']['talon'], 0)} (J37)", on=on)
        xs = Lc - Lt
        V.note_pt((xs - 1.25, 0, a + 0.33), (-50, -30), f"Entrada de sellos {fm(CA['chaflan_sellos']['ang'], 0)}° × {fm(CA['chaflan_sellos']['largo'], 1)}", on=on)
        V.note_pt((xB + rsf - 3, 0, zs), (-60, 30), "Puerto B G 1/2 (ver tabla)", on=on)
        V.note_pt((xA + rsf - 3, 0, zs), (30, 30), "Puerto A G 1/2 (ver tabla)", on=on)
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 3, 2, 3), extra=(30, 10, 30, 30), draw=corte, hs=0.6, w=1.8, auto=False, mins=1.0, title="CORTE A-A (PLANO DE LOS PUERTOS)")
    p.detail("detR", "corte", (Lc - Lt / 2, 0, (a + b) / 2), 24, "B", lv=(1, 1, 1, 1), title="DETALLE B: ROSCA M110 × 2-6H Y ENTRADA DE SELLOS", maxs=4.0)
    rows = [["Ø exterior", _fit(CA["D"], CA["tol_D"])], ["Ø interior (bruñido)", _fit(CA["d"], CA["tol_d"]) + f", Ra ≤ {fm(CA['Ra_d'], 1)}, Rz ≤ 2,5; cilindricidad {fm(CA['cilindricidad'], 2)}; rectitud {CA['rectitud']}"],
            ["Largo / largo de corte", f"{fm(CA['largo'], 0)} / {fm(CA['largo_corte'], 0)} mm"], ["Rosca interior", f"{CA['rosca']['designacion']}, profundidad {fm(CA['rosca']['prof'], 0)} + salida {fm(CA['rosca']['salida'], 0)}, Ø menor {fm(CA['rosca']['D1'], 3)}; {CA['rosca']['chaflan_entrada']}"],
            ["Entrada de sellos", f"{fm(CA['chaflan_sellos']['ang'], 0)}° × {fm(CA['chaflan_sellos']['largo'], 1)} a {fm(CA['chaflan_sellos']['x_desde_extremo'], 0)} del extremo delantero"],
            ["Bisel trasero (J37)", f"{CA['bisel_trasero']['tipo']}; talón {fm(CA['bisel_trasero']['talon'], 0)}; separación {fm(CA['bisel_trasero']['separacion'], 0)}; {CA['bisel_trasero']['respaldo']}"],
            ["Puerto B", f"{CA['puerto_B']['rosca']} {CA['puerto_B']['norma']}, a {fm(xB, 1)} del extremo trasero y {fm(CA['puerto_B']['x_desde_extremo_delantero'], 1)} del delantero; prof. {fm(CA['puerto_B']['prof_rosca'], 0)}; refrentado Ø{fm(CA['puerto_B']['refrentado'], 0)}; paso Ø{fm(CA['puerto_B']['paso'], 0)}; {CA['puerto_B']['orientacion']}"],
            ["Puerto A", f"{CA['puerto_A']['rosca']} {CA['puerto_A']['norma']}, a {fm(xA, 1)} del extremo trasero; prof. {fm(CA['puerto_A']['prof_rosca'], 0)} (núcleo Ø18,6); refrentado Ø{fm(CA['puerto_A']['refrentado'], 0)}; paso Ø{fm(CA['puerto_A']['paso'], 0)}; {CA['puerto_A']['orientacion']}; {CA['puerto_A']['nota']}"],
            ["Prisionero antigiro de la tapa", f"M8 radial abajo (−z) a {fm(CA['prisionero_tapa']['x_desde_extremo'], 0)} del extremo delantero (taladro Ø6,8)"]]
    p.table_block("COTAS Y REQUISITOS (bx.cilindro.camisa)", [("Elemento", 40, "L"), ("Valor", 130, "L")], rows)
    p.tables(["J37"])
    p.notes([f"Material: {CA['material']}; certificado 3.1.", f"Mecanizado del Ø{f(CA['d'])} {CA['tol_d']} y de la rosca DESPUÉS de soldar el fondo (J37) y del alivio de tensiones: {CA['acabado']}.",
             "Aristas interiores sin rebabas; limpieza interior ISO 4406 18/16/13 antes del montaje.", "Tapón de protección en los puertos hasta el montaje.", "Tolerancias geométricas (ISO 1101): " + "; ".join(t[3] + " " + t[1] + ((" respecto de " + t[2]) if t[2] else "") for t in [("cyl", fm(CA["cilindricidad"], 2), None, f"Cilindricidad del Ø{f(CA['d'])} {CA['tol_d']} (A = su eje)"), ("coax", "Ø0,05", "A", "Rosca M110 × 2 coaxial con A"), ("perp", "0,03", "A", "Cara del extremo delantero (asiento del reborde) perpendicular a A")]) + "."])
    p.build()
    return p.h


# =========================================================================================================== ACC-029: fondo macizo con espiga + ojal trasero (ACC-030) soldados
def sheet_cil_fondo(ctx):
    C = _C(ctx)
    o = cil_bx.geo(C)
    F = C["fondo"]
    OE = F["ojal"]
    AL = OE["alojamiento"]
    nf_ = _loc(ctx, "cil_fondo", "cil_fondo_L", 0.0)
    no_ = _loc(ctx, "cil_ojal_E", "cil_ojal_E_L", 0.0)
    on = [nf_, no_]
    s0, si, sk = o["s0"], o["si"], o["sk"]
    a, b = o["a"], o["b"]
    bE = float(OE["ancho"])
    ES = F["espiga"]
    p = Pieza(ctx, ["cil_fondo", "cil_ojal_E"], f"CILINDRO: FONDO MACIZO {f(F['t'])} (PESTAÑA {f(F['pestana'])} + ESPIGA Ø{f(ES['d'])} {ES['tol']} × {f(ES['largo'])}, S355J2) CON EL OJAL TRASERO SOLDADO (RÓTULA GE70ES)", fmt="A1")
    s = p.s
    p.iso_keys = on

    def corte(V, p_):
        s.line(V.P(-90, 0, 0), V.P(si + 8, 0, 0), "EJE")
        s.line(V.P(0, 0, -bE / 2 - 8), V.P(0, 0, bE / 2 + 8), "EJE")
        V.dimh((0, 0, 0), (s0, 0, 40), "top", 0, on=on, virt_a=float(AL["d"]) / 2, text=f"{f(C['e_cuerpo'])}")
        V.dimh((s0, 0, 60), (sk, 0, 60), "top", 1, on=on, text=f"{f(F['pestana'])} (pestaña)")
        V.dimh((sk, 0, 55), (si, 0, 30), "top", 1, on=on, text=f"{f(ES['largo'])} (espiga)")
        V.dimh((s0, 0, -60), (si, 0, -30), "bottom", 0, on=on, text=f"({f(F['t'])})")
        V.dim((s0 + 4, 0, -b), (s0 + 4, 0, b), -14, orient="v", on=on, text=f"Ø{f(F['D'])} h11")
        V.dim((si - 6, 0, -a), (si - 6, 0, a), 14, orient="v", on=on, text=_fit(ES["d"], ES["tol"]))
        V.dim((-float(OE["R"]) + 6, 0, -bE / 2), (-float(OE["R"]) + 6, 0, bE / 2), -12, orient="v", on=on, text=f"{f(bE)}")
        V.note_pt((si, 0, 20), (24, 30), "Cara de la espiga = tope del retraído", on=on)
        V.note_pt((float(AL["d"]) / 2, 0, 0), (10, -40), f"Alojamiento Ø{f(AL['d'])} {AL['tol']} (ver tabla)", on=on)
        a_ = V.P((s0, 0, bE / 2 + 1))
        p_.h.weld("J38", a_, (a_[0] - 50, a_[1] + 40), sh=-1)
    p.vs("corte", on, "front", cut=CUT_Y, lv=(2, 2, 2, 4), extra=(90, 10, 40, 20), draw=corte, hs=0.6, w=1.6, auto=False, mins=1.0, title="CORTE A-A (EJE DE LA RÓTULA)")

    def planta(V, p_):
        s.centerlines(V.P(0, 0, bE / 2), float(OE["R"]) * V.scale, 6)
        V.dim_rad((0, 0, bE / 2), float(OE["R"]), 135, on=on, text=f"R{fm(OE['R'], 0)}")
        V.dim((s0, -float(OE["cuello"]) / 2, bE / 2), (s0, float(OE["cuello"]) / 2, bE / 2), 12, orient="v", on=on, text=f"{f(OE['cuello'])}")
        V.dimh((-float(OE["R"]), 0, bE / 2), (s0, float(OE["cuello"]) / 2, bE / 2), "bottom", 0, on=on, text=f"{f(float(OE['R']) + s0)}")
        V.dim((0, -float(OE["R"]), bE / 2), (0, float(OE["R"]), bE / 2), -(float(OE["R"]) * V.scale + 12), orient="v", on=on, text=f"{f(2 * float(OE['R']))}")
    p.vs("planta", [no_], "top", lv=(2, 2, 3, 1), extra=(10, 0, 20, 0), draw=planta, hatch=False, w=0.8, auto=False, title="PLANTA DEL OJAL TRASERO (ACC-030)")
    rows = [["Bloque macizo", f"{f(F['t'])} = pestaña Ø{f(F['D'])} h11 × {f(F['pestana'])} + espiga {_fit(ES['d'], ES['tol'])} × {f(ES['largo'])} (t requerido {fm(F['t_req'], 2)}); chaflanes 1 × 45°"],
            ["Espiga", f"{ES['ajuste']}; su cara es el {ES['cara']}"],
            ["Soldadura con la camisa (J37)", f"{F['cjp']['tipo']}; el hombro (cara de la pestaña) queda a escuadra, el bisel en J va en la camisa; END {F['cjp']['end']}"],
            ["Ojal trasero (ACC-030)", f"R{fm(OE['R'], 0)} × {f(OE['ancho'])}, cuello {f(OE['cuello'])} sobre el fondo; {OE['material']}"],
            ["Alojamiento de la rótula", f"Ø{f(AL['d'])} {AL['tol']} × {f(AL['ancho'])}; resalte Ø{f(AL['resalte']['d'])} × {f(AL['resalte']['ancho'])}; ranura Ø{f(AL['ranura']['d'])} × {fm(AL['ranura']['ancho'], 2)} a {fm(AL['ranura']['w'][0], 0)}…{fm(AL['ranura']['w'][1], 2)} ({AL['ranura']['norma']})"],
            ["Ranura y resalte (desde la cara superior)", f"ranura del anillo elástico de {fm(float(OE['ancho']) - float(AL['ranura']['w'][1]), 2)} a {fm(float(OE['ancho']) - float(AL['ranura']['w'][0]), 0)}; resalte a {fm(float(OE['ancho']) - float(AL['resalte']['ancho']), 0)} (desde la inferior: {fm(AL['resalte']['ancho'], 0)})"],
            ["Rótula", f"{OE['rotula']['designacion']}: d {f(OE['rotula']['d'])}, D {f(OE['rotula']['D'])}, B {f(OE['rotula']['B'])}, C {f(OE['rotula']['C'])}; {OE['rotula']['montaje']}"],
            ["Soldadura orejeta–fondo (J38)", f"{OE['soldadura']['tipo']}; END {OE['soldadura']['end']}; {OE['soldadura']['wps']}"]]
    p.table_block("COTAS Y REQUISITOS (bx.cilindro.fondo)", [("Elemento", 40, "L"), ("Valor", 130, "L")], rows)
    p.tables(["J38"])
    p.notes([f"Fondo: {F['material']}.", f"Ojal trasero: {OE['material']}; biseles en K; soldar al fondo (J38) antes de soldar el fondo a la camisa (J37); {F['cjp']['proceso']}.",
             "La soldadura del fondo queda en el hombro, DETRÁS del tope: los sellos del pistón nunca pasan sobre ella ni sobre su ZAC (requisito del fabricante hidráulico, rev. 8).",
             f"Alojamiento Ø{f(AL['d'])} {AL['tol']} mecanizado en línea con el eje de la camisa DESPUÉS de soldar y aliviar (perpendicular al eje del cilindro 0,05).",
             f"END: J38 {OE['soldadura']['end']}; J37 {F['cjp']['end']}.", "Tolerancias geométricas (ISO 1101): eje del alojamiento de la rótula perpendicular al eje de la espiga (A) 0,05; espiga coaxial con la pestaña Ø0,05."])
    p.build()
    return p.h


# =========================================================================================================== ACC-031: tapa delantera
def sheet_cil_tapa(ctx):
    C = _C(ctx)
    o = cil_bx.geo(C)
    T = C["tapa"]
    nk = _loc(ctx, "cil_tapa", "cil_tapa_L", 0.0, dx=o["sp"])
    on = [nk]
    Lt = float(T["largo"])
    Ls = float(T["espiga"]["w"][1])
    w0r, w1r = float(T["reborde"]["w"][0]), float(T["reborde"]["w"][1])
    rv = o["dr"] / 2
    p = Pieza(ctx, ["cil_tapa"], f"CILINDRO: TAPA DELANTERA ROSCADA {T['rosca']['designacion']} (ESPIGA Ø89,5 f7 CON O'RING; SELLOS, GUÍAS Y RASCADOR DEL VÁSTAGO Ø{f(o['dr'])})", fmt="A1")
    s = p.s
    p.iso_keys = on
    G = T["rosca"]["garganta"]

    def corte(V, p_):
        s.line(V.P(-8, 0, 0), V.P(Lt + 8, 0, 0), "EJE")
        V.dimh((0, 0, 40), (Ls, 0, 44.75), "top", 0, on=on, text=f"{fm(Ls, 0)} (espiga)")
        V.dimh((Ls, 0, 50), (w0r, 0, 60), "top", 0, on=on, text=f"{fm(w0r - Ls, 0)} (rosca útil {fm(T['rosca']['util'], 0)} + chaflán 1 + garganta {fm(G['w'][1] - G['w'][0], 0)})")
        V.dimh((w0r, 0, 60), (Lt, 0, 60), "top", 0, on=on, text=f"{fm(w1r - w0r, 0)} (reborde)")
        V.dimh((0, 0, 40), (Lt, 0, 50), "top", 1, on=on, text=f"({fm(Lt, 0)})")
        V.dim((Lt - 6, 0, -65), (Lt - 6, 0, 65), 14, orient="v", on=on, text=f"Ø{f(T['reborde']['d'])} {T['reborde']['tol']}")
        V.dim((Ls / 2 + 3, 0, -44.75), (Ls / 2 + 3, 0, 44.75), -26, orient="v", on=on, text=_fit(T["espiga"]["d"], T["espiga"]["tol"]))
        V.dim((Ls + 12, 0, -55), (Ls + 12, 0, 55), 20, orient="v", on=on, text=T["rosca"]["designacion"])
        V.dim((1.5, 0, -rv), (1.5, 0, rv), 0, orient="v", on=on, text=_fit(T["agujero"]["d"], T["agujero"]["tol"]))
        V.note_pt((6.0, 0, float(_seal(C, "S4")["alojamiento"]["d_fondo"]) / 2), (14, -44), "Ranura S4 (ver tabla)", on=on)
        V.note_pt(((G["w"][0] + G["w"][1]) / 2, 0, float(G["d"]) / 2), (30, 30), f"Garganta Ø{fm(G['d'], 2)} × {fm(G['w'][1] - G['w'][0], 0)}", on=on)
        V.note_pt((0.2, 0, 44.75 - 0.4 + 0.05), (-20, 30), f"Chaflán {T['espiga']['chaflan_entrada']}", on=on)
        for h in T["alojamientos_vastago"]:
            pass
    p.vs("corte", on, "front", cut=CUT_Y, lv=(2, 2, 2, 3), extra=(30, 30, 40, 20), draw=corte, hs=0.5, w=1.6, auto=False, mins=2.0, title="CORTE A-A (ALOJAMIENTOS ACOTADOS EN LA TABLA)")
    p.detail("detS", "corte", (27, 0, 36), 16, "B", lv=(1, 2, 1, 1), title="DETALLE B: ALOJAMIENTOS DE SELLOS Y GUÍAS DEL VÁSTAGO", maxs=4.0)
    LL = T["reborde"]["agujeros_llave"]

    def frente(V, p_):
        s.centerlines(V.P(Lt, 0, 0), 65 * V.scale, 6)
        th = math.radians(45.0)
        V.note_hole((Lt, float(LL["pcd"]) / 2 * math.cos(th), float(LL["pcd"]) / 2 * math.sin(th)), float(LL["d"]) / 2, 45, f"{int(LL['n'])} × Ø{f(LL['d'])} prof. {f(LL['prof'])}, PCD Ø{f(LL['pcd'])}", on=on)
    p.vs("frente", on, "right", lv=(1, 1, 1, 2), extra=(10, 10, 60, 20), draw=frente, hatch=False, w=0.8, auto=False, mins=1.0, title="VISTA DEL REBORDE (AGUJEROS DE LLAVE A 45°)")
    rows = []
    for h in T["alojamientos_vastago"]:
        q = _seal(C, h["ref"])
        an = h["ancho"]
        rows.append([h["ref"], q["nombre"].split(" (")[0], q["norma"], f"Ø{fm(h['d'], 1)} {q['alojamiento']['tol_fondo']}", f"{fm(an, 1)} +0,2", f"{fm(h['w'][0], 1)} … {fm(h['w'][1], 1)}", q["designacion"]])
        if h.get("labio"):
            rows.append([h["ref"], "Labio de retención del rascador", q["norma"], f"Ø{fm(h['labio']['d'], 0)} H11", f"{fm(h['labio']['w'][1] - h['labio']['w'][0], 0)}", f"{fm(h['labio']['w'][0], 0)} … {fm(h['labio']['w'][1], 0)}", "—"])
    q4 = _seal(C, "S4")
    rows.append(["S4", "O'ring estático contra la camisa (en la espiga)", q4["norma"], f"Ø{fm(q4['alojamiento']['d_fondo'], 1)} {q4['alojamiento']['tol_fondo']}", f"{fm(q4['alojamiento']['ancho'], 1)} +0,2",
                 f"{fm(T['espiga']['ranura_oring']['w'][0], 0)} … {fm(T['espiga']['ranura_oring']['w'][1], 0)}", q4["designacion"]])
    p.table_block("ALOJAMIENTOS (x desde la cara interior de la espiga; agujero " + _fit(T["agujero"]["d"], T["agujero"]["tol"]) + "; r fondo 0,4; Ra fondo 1,6, flancos 3,2)",
                  [("Pos.", 9, "C"), ("Elemento", 46, "L"), ("Norma", 22, "L"), ("Ø fondo", 22, "L"), ("Ancho", 16, "L"), ("x [mm]", 20, "L"), ("Designación", 52, "L")], rows)
    rows2 = [["Espiga", f"{_fit(T['espiga']['d'], T['espiga']['tol'])} frente al Ø{f(C['D_camisa'])} H8 de la camisa; largo {fm(Ls, 0)}; chaflán de entrada {T['espiga']['chaflan_entrada']}"],
             ["Rosca exterior", f"{T['rosca']['designacion']}, útil {fm(T['rosca']['util'], 0)}; {T['rosca']['chaflan']}; garganta Ø{fm(G['d'], 2)} × {fm(G['w'][1] - G['w'][0], 0)} R{fm(G['radio'], 0)} ({G['norma']}); d₂ {fm(T['rosca']['d2'], 3)}, d₃ {fm(T['rosca']['d3'], 3)}"],
             ["Reborde", f"Ø{f(T['reborde']['d'])} {T['reborde']['tol']} × {fm(w1r - w0r, 0)}; {T['reborde']['cara_asiento']}; {int(LL['n'])} × Ø{f(LL['d'])} × {f(LL['prof'])} en PCD Ø{f(LL['pcd'])}"],
             ["Apriete y antigiro", f"{T['par_apriete_Nm']} N·m con llave de gancho; {T['antigiro']}"]]
    p.table_block("COTAS Y REQUISITOS (bx.cilindro.tapa)", [("Elemento", 30, "L"), ("Valor", 140, "L")], rows2)
    p.tables()
    p.notes([f"Material: {T['material']}.", f"Agujero {_fit(T['agujero']['d'], T['agujero']['tol'])} Ra {fm(T['agujero']['Ra'], 1)}: {T['agujero']['nota']}.",
             "Alojamientos sin aristas vivas (R0,2 en los bordes), sin rebabas; montaje de sellos con herramienta (sin útiles metálicos con filo).",
             "Los sellos van por DENTRO de la rosca: el o'ring S4 de la espiga sella contra el Ø90 H8 de la camisa más allá de la rosca, que no ve presión.", "Tolerancias geométricas (ISO 1101): " + "; ".join(t[3] + " " + t[1] + ((" respecto de " + t[2]) if t[2] else "") for t in [("coax", "Ø0,03", "A", "Ø89,5 f7 y M110 × 2 coaxiales con el agujero del vástago (A)"), ("perp", "0,03", "A", "Cara de asiento del reborde perpendicular a A")]) + "."])
    p.build()
    return p.h


# =========================================================================================================== ACC-032: pistón y tuerca (ACC-033)
def sheet_cil_piston(ctx):
    C = _C(ctx)
    o = cil_bx.geo(C)
    PI = C["piston"]
    TU = PI["tuerca"]
    p0 = o["si"] + o["hn"]
    npi = _loc(ctx, "cil_piston", "cil_piston_L", 0.0, dx=p0)
    ntu = _loc(ctx, "cil_tuerca", "cil_tuerca_L", 0.0, dx=o["si"] + 80.0)
    Lp = float(PI["largo"])
    u = PI["u"]
    rP = float(PI["D"]) / 2
    p = Pieza(ctx, ["cil_piston", "cil_tuerca"], f"CILINDRO: PISTÓN Ø{fm(PI['D'], 1)} {PI['tol_D']} × {f(Lp)} (42CrMo4+QT) Y TUERCA RANURADA {TU['designacion'].split(' (')[0].replace('tuerca ranurada ', '')}", fmt="A1")
    s = p.s
    p.iso_keys = [npi, ntu]

    def cp(V, p_):
        s.line(V.P(-8, 0, 0), V.P(Lp + 8, 0, 0), "EJE")
        V.dimh((0, 0, rP - 1), (Lp, 0, 35), "bottom", 1, on=[npi], text=f"{f(Lp)} ±0,05")
        V.dim((u["guia1"][1] + 1.5, 0, -rP), (u["guia1"][1] + 1.5, 0, rP), 20, orient="v", on=[npi], text=_fit(PI["D"], PI["tol_D"]))
        V.dim((2.0, 0, -float(PI["d"]) / 2), (2.0, 0, float(PI["d"]) / 2), 0, orient="v", on=[npi], text=_fit(PI["d"], PI["tol_d"]))
        V.dim((Lp - 1, 0, -float(u["d_alivio"]) / 2), (Lp - 1, 0, float(u["d_alivio"]) / 2), 34, orient="v", on=[npi], text=f"Ø{f(u['d_alivio'])}")
    p.vs("pis", [npi], "front", cut=CUT_Y, lv=(2, 2, 3, 2), extra=(10, 0, 30, 0), draw=cp, hs=0.4, w=1.4, auto=False, mins=2.0, title="PISTÓN: CORTE A-A (ALOJAMIENTOS EN LA TABLA)")
    hn = float(TU["alto"])
    rN = float(TU["D"]) / 2

    def ct(V, p_):
        s.line(V.P(-88, 0, 0), V.P(-80 + hn + 8, 0, 0), "EJE")
        V.dimh((-80, 0, 27), (-80 + hn, 0, 27), "bottom", 0, on=[ntu], text=f"{f(hn)}")
        V.dim((-80 + hn - 3, 0, -rN), (-80 + hn - 3, 0, rN), 14, orient="v", on=[ntu], text=f"Ø{f(TU['D'])}")
        V.note_pt((-80 + hn - 2, 0, float(TU["avellanado"]["d"]) / 2), (20, -24), f"Avellanado Ø{f(TU['avellanado']['d'])} × {f(TU['avellanado']['prof'])}", on=[ntu])
    p.vs("tue", [ntu], "front", cut=CUT_Y, lv=(1, 2, 2, 1), extra=(10, 0, 30, 0), draw=ct, hs=0.4, w=0.8, auto=False, mins=2.0, title="TUERCA RANURADA (ACC-033): CORTE")
    rows = [["S2", "Anillo guía 1", f"{fm(u['guia1'][0], 1)} … {fm(u['guia1'][1], 1)}", _aloj_txt(_seal(C, "S2")), _seal(C, "S2")["norma"]],
            ["S1", "Sello de doble efecto", f"{fm(u['sello'][0], 1)} … {fm(u['sello'][1], 1)}", _aloj_txt(_seal(C, "S1")), _seal(C, "S1")["norma"]],
            ["S2", "Anillo guía 2", f"{fm(u['guia2'][0], 1)} … {fm(u['guia2'][1], 1)}", _aloj_txt(_seal(C, "S2")), _seal(C, "S2")["norma"]],
            ["S3", "O'ring estático contra el vástago (en el agujero)", f"{fm(u['ranura_oring'][0], 2)} … {fm(u['ranura_oring'][1], 2)}", _aloj_txt(_seal(C, "S3")), _seal(C, "S3")["norma"]],
            ["—", "Alivio frontal", f"{fm(u['alivio'][0], 1)} … {fm(u['alivio'][1], 1)}", f"Ø{f(u['d_alivio'])}", "—"], ["—", "Chaflán de la cara contra la tuerca", f"{fm(u['chaflan'][0], 0)} … {fm(u['chaflan'][1], 0)}", "1 × 45°", "—"]]
    p.table_block("ALOJAMIENTOS DEL PISTÓN (x desde la cara contra la tuerca)", [("Pos.", 9, "C"), ("Elemento", 50, "L"), ("x [mm]", 24, "L"), ("Ø fondo × ancho", 40, "L"), ("Norma", 26, "L")], rows)
    rows2 = [["Pistón", f"Ø{fm(PI['D'], 1)} {PI['tol_D']} Ra {fm(PI['Ra_D'], 1)}; agujero {_fit(PI['d'], PI['tol_d'])} sobre el asiento Ø{f(PI['d'])} g6 del vástago; perpendicularidad de las caras {fm(PI['perpendicularidad'], 2)}; {PI['coaxialidad']}"],
             ["Tuerca", f"{TU['designacion']}: Ø{f(TU['D'])} × {f(TU['alto'])}; {int(TU['ranuras']['n'])} ranuras {f(TU['ranuras']['ancho'])} × {f(TU['ranuras']['prof'])}; avellanado Ø{f(TU['avellanado']['d'])} × {f(TU['avellanado']['prof'])}; {TU['material']}"],
             ["Apriete y seguro", f"{TU['par_Nm']} N·m (F_V ≈ {fm(TU['F_V_kN'], 0)} kN, VDI 2230); {TU['seguro']}; agujeros M6 a 45° y 225°"]]
    p.table_block("COTAS Y REQUISITOS (bx.cilindro.piston)", [("Elemento", 26, "L"), ("Valor", 144, "L")], rows2)
    p.tables()
    p.notes([f"Pistón y tuerca: {PI['material']}; certificado 3.1 con Re medido.", "Alojamientos sin aristas vivas (R0,2), Ra fondo 1,6 / flancos 3,2; sin rebabas.",
             "La tuerca es el tope del retraído contra el fondo: su cara contra el fondo plana y perpendicular al eje 0,02.", "Tolerancias geométricas (ISO 1101): " + "; ".join(t[3] + " " + t[1] + ((" respecto de " + t[2]) if t[2] else "") for t in [("perp", fm(PI["perpendicularidad"], 2), "A", "Caras del pistón perpendiculares al agujero (A)"), ("coax", "Ø0,03", "A", f"Ø{fm(PI['D'], 1)} coaxial con A")]) + "."])
    p.build()
    return p.h


# =========================================================================================================== ACC-034: vástago
def sheet_cil_vastago(ctx):
    C = _C(ctx)
    o = cil_bx.geo(C)
    V_ = C["vastago"]
    nk = _loc(ctx, "cil_vastago", "cil_vastago_L", 0.0, dx=o["si"])
    on = [nk]
    Lr = float(V_["largo"])
    hn, Lpc = o["hn"], o["Lpc"]
    rv = o["dr"] / 2
    rT = float(V_["rosca"]["designacion"].split("×")[0].strip()[1:]) / 2
    p = Pieza(ctx, ["cil_vastago"], f"CILINDRO: VÁSTAGO Ø{f(V_['d'])} {V_['tol']} CROMADO (ROSCA {V_['rosca']['designacion']}, ASIENTO DEL PISTÓN Y SOLDADURA DEL OJAL)", fmt="A1")
    s = p.s
    p.iso_keys = on
    Lth = float(V_["rosca"]["largo"])
    ga = float(V_["garganta"]["ancho"])

    def el(V, p_):
        s.line(V.P(-8, 0, 0), V.P(Lr + 8, 0, 0), "EJE")
        V.dimh((0, 0, 0), (Lr, 0, 0), "bottom", 2, on=on, text=f"{fm(Lr, 1)} ±0,3 (a la soldadura del ojal)")
        V.dimh((1.5, 0, rT), (Lth, 0, rT), "top", 0, on=on, text=f"{fm(Lth - 1.5, 1)} + chaflán 1,5")
        V.dimh((Lth, 0, float(V_['garganta']['d']) / 2), (Lth + ga, 0, float(V_['garganta']['d']) / 2), "top", 0, on=on, text=f"{fm(ga, 0)}")
        V.dimh((Lth + ga, 0, float(V_['asiento']['d']) / 2), (hn + Lpc, 0, float(V_['asiento']['d']) / 2), "top", 0, on=on, text=f"{fm(Lpc, 0)}")
        V.dim((Lr * 0.6, 0, -rv), (Lr * 0.6, 0, rv), 12, orient="v", on=on, text=f"Ø{f(V_['d'])} {V_['tol']}")
        V.note_pt((Lr * 0.75, 0, rv), (20, 26), f"Cromo duro ≥ {f(V_['cromo']['espesor_min_um'])} µm, Ra ≤ {fm(V_['cromo']['Ra'], 1)}", on=on)
        V.dim((hn + Lpc - 6, 0, -float(V_['asiento']['d']) / 2), (hn + Lpc - 6, 0, float(V_['asiento']['d']) / 2), -16, orient="v", on=on, text=_fit(V_["asiento"]["d"], V_["asiento"]["tol"]))
        V.dim((Lth / 2, 0, -rT), (Lth / 2, 0, rT), -34, orient="v", on=on, text=f"{V_['rosca']['designacion']}")
        V.note_pt((Lth + ga / 2, 0, float(V_['garganta']['d']) / 2), (-6, -30), f"Garganta Ø{fm(V_['garganta']['d'], 1)} × {fm(ga, 0)}, R{fm(V_['garganta']['radio'], 0)} ({V_['garganta']['norma']})", on=on)
        V.note_pt((hn + Lpc + 1.5, 0, rv - 1.5 * math.tan(math.radians(20)) * 2 + 0.55), (22, 26), f"Chaflán de entrada de sellos {V_['asiento']['resalte_chaflan']}", on=on)
        V.note_pt((0.75, 0, rT - 0.75), (-24, 26), f"Chaflán {V_['rosca']['chaflan']}", on=on)
        a_ = V.P((Lr, 0, -rv))
        p_.h.weld("J39", a_, (a_[0] - 30, V.ext[1] - 14), sh=-1)
    p.vs("el", on, "front", cut=CUT_Y, lv=(2, 7, 2, 2), extra=(30, 10, 30, 20), draw=el, hs=0.6, w=1.8, auto=False, mins=1.0, title="VÁSTAGO: CORTE A-A")
    rows = [["Ø del vástago", _fit(V_["d"], V_["tol"]) + f"; rectitud {V_['rectitud']}"], ["Cromo duro", f"≥ {f(V_['cromo']['espesor_min_um'])} µm, {V_['cromo']['dureza']}, Ra ≤ {fm(V_['cromo']['Ra'], 1)} ({V_['cromo']['norma']})"],
            ["Largo", f"{fm(Lr, 1)} (del extremo roscado a la soldadura del ojal)"], ["Rosca", f"{V_['rosca']['designacion']} × {fm(Lth, 0)}, chaflán {V_['rosca']['chaflan']}"],
            ["Garganta", f"Ø{fm(V_['garganta']['d'], 1)} × {fm(ga, 0)}, R{fm(V_['garganta']['radio'], 0)} ({V_['garganta']['norma']})"],
            ["Asiento del pistón", f"{_fit(V_['asiento']['d'], V_['asiento']['tol'])} × {fm(Lpc, 0)}; resalte Ø{f(V_['d'])} con chaflán {V_['asiento']['resalte_chaflan']}"],
            ["Extremo hacia el ojal", f"{V_['extremo_ojal']['tipo']} a {f(V_['extremo_ojal']['x_desde_eje_ojal'])} del eje del ojal; {V_['extremo_ojal']['nota']}"]]
    p.table_block("COTAS Y REQUISITOS (bx.cilindro.vastago)", [("Elemento", 34, "L"), ("Valor", 136, "L")], rows)
    p.tables(["J39"])
    p.notes([f"Material: {V_['material']}.", "Secuencia: tornear el extremo, soldar el ojal por fricción (J39), eliminar la rebaba, rectificar, cromar y pulir; la rosca se protege durante el cromado.",
             "Sin golpes ni marcas en la superficie cromada; embalaje con protector.", "Tolerancias geométricas (ISO 1101): " + "; ".join(t[3] + " " + t[1] + ((" respecto de " + t[2]) if t[2] else "") for t in [("coax", "Ø0,02", "A", f"Asiento Ø{f(V_['asiento']['d'])} y rosca coaxiales con el Ø{f(V_['d'])} (A)")]) + "."])
    p.build()
    return p.h


# =========================================================================================================== ACC-035: ojal del vástago
def sheet_cil_ojal_q(ctx):
    C = _C(ctx)
    OQ = C["ojal_vastago"]
    L0 = float(C["L0"])
    nk = _loc(ctx, "cil_ojal_Q", "cil_ojal_Q_L", 0.0, dx=L0)
    on = [nk]
    RQ, bQ, dQ = float(OQ["R"]), float(OQ["ancho"]), float(OQ["d"])
    xw = float(OQ["espiga"]["x1"])
    xn = float(OQ["cuello"]["x1"])
    rv = float(OQ["espiga"]["d"]) / 2
    p = Pieza(ctx, ["cil_ojal_Q"], f"CILINDRO: OJAL DEL VÁSTAGO R{fm(RQ, 0)} × {f(bQ)} CON AGUJERO Ø{f(dQ)} H9 (SIN RÓTULA) Y ESPIGA Ø{f(OQ['espiga']['d'])}", fmt="A1")
    s = p.s
    p.iso_keys = on

    def pl(V, p_):
        s.centerlines(V.P(0, 0, bQ / 2), RQ * V.scale, 6)
        s.line(V.P(-xw - 8, 0, bQ / 2), V.P(RQ + 8, 0, bQ / 2), "EJE")
        V.dim_dia((0, 0, bQ / 2), dQ / 2, 45, on=on, text=_fit(dQ, OQ["tol_d"]) + f" Ra {fm(OQ['Ra_d'], 1)}")
        V.dim_rad((0, 0, bQ / 2), RQ, 120, on=on, text=f"R{fm(RQ, 0)}")
        V.dimh((-xw, 0, 0), (0, 0, bQ / 2), "bottom", 0, on=on, virt_b=dQ / 2, text=f"{fm(xw, 0)} (soldadura por fricción)")
        V.dimh((-xn, rv, bQ / 2), (0, 0, bQ / 2), "bottom", 1, on=on, virt_b=dQ / 2, text=f"{fm(xn, 0)} (fin del cuello)")
        V.dimh((-xw, 0, 0), (-xn, rv, bQ / 2), "top", 0, on=on, text=f"({fm(xw - xn, 0)})")
        V.dimh((-xw, 0, 0), (RQ, 0, bQ / 2), "top", 1, on=on, text=f"{fm(xw + RQ, 0)} (total)")
        V.dim((0, -RQ, bQ / 2), (0, RQ, bQ / 2), RQ * V.scale + 10, orient="v", on=on, text=f"{fm(2 * RQ, 0)}")
        V.dim((-xn + 4, -rv, bQ / 2), (-xn + 4, rv, bQ / 2), -16, orient="v", on=on, text=f"{f(OQ['cuello']['ancho'])}")
    p.vs("pl", on, "top", lv=(2, 3, 2, 1), extra=(10, 0, 10, 0), draw=pl, hatch=False, w=1.4, auto=False, mins=1.0, title="PLANTA")

    def ct(V, p_):
        V.dim((RQ - 4, 0, -bQ / 2), (RQ - 4, 0, bQ / 2), 14, orient="v", on=on, text=f"{f(bQ)} ±0,1")
        V.dim((-xw + 4, 0, -rv), (-xw + 4, 0, rv), -16, orient="v", on=on, text=f"Ø{f(OQ['espiga']['d'])} (espiga)")
        V.note_pt((RQ, 0, 6), (16, 22), "Grasera M8 × 1", on=on)
    p.vs("ct", on, "front", cut=CUT_Y, lv=(2, 1, 2, 1), extra=(10, 0, 30, 0), draw=ct, hs=0.5, w=1.0, auto=False, title="CORTE A-A")
    rows = [["Agujero", _fit(dQ, OQ["tol_d"]) + f", Ra {fm(OQ['Ra_d'], 1)}; sobre el pasador Q Ø{f(dQ)} f8"], ["Ojal", f"R{fm(RQ, 0)} × {f(bQ)} (≤ R_cubo − holgura del bloque-uña)"],
            ["Cuello", f"{f(OQ['cuello']['ancho'])} × {f(OQ['cuello']['espesor'])} desde {fm(OQ['cuello']['x0'], 1)} hasta {fm(xn, 0)} del eje"], ["Espiga", f"Ø{f(OQ['espiga']['d'])} de {fm(OQ['espiga']['x0'], 0)} a {fm(xw, 0)} del eje"],
            ["Rótula", OQ["rotula"]], ["Unión al vástago (J39)", f"{OQ['soldadura']['tipo']}; END {OQ['soldadura']['end']}"]]
    p.table_block("COTAS Y REQUISITOS (bx.cilindro.ojal_vastago)", [("Elemento", 30, "L"), ("Valor", 140, "L")], rows)
    p.tables(["J39"])
    p.notes([f"Material: {OQ['material']}.", f"El agujero Ø{f(dQ)} {OQ['tol_d']} se mecaniza al final, con el ojal soldado al vástago, perpendicular al eje del vástago 0,05 y en su plano medio ±0,1.",
             "Ranura de engrase helicoidal 3 × 1,5 en el agujero desde la grasera.", "Tolerancias geométricas (ISO 1101): " + "; ".join(t[3] + " " + t[1] + ((" respecto de " + t[2]) if t[2] else "") for t in [("perp", "0,05", "A", "Eje del agujero perpendicular al eje del vástago (A)")]) + "."])
    p.build()
    return p.h


# =========================================================================================================== ACC-036: esquema retraído / extendido
def sheet_cil_esquema(ctx):
    C = _C(ctx)
    o = cil_bx.geo(C)
    if not hasattr(ctx, "subconjuntos"):
        ctx.subconjuntos = set()
    L0, Lx, st = float(C["L0"]), float(C["L_ext"]), float(C["carrera"])
    Z = 230.0
    ks = ("cil_ojal_E", "cil_rotula", "cil_fondo", "cil_camisa", "cil_tapa", "cil_vastago", "cil_ojal_Q")
    r0 = [_loc(ctx, k, k + "_E0", 0.0) for k in ks]
    r1 = []
    for k in ks:
        nk = _loc(ctx, k, k + "_E1", st)
        ctx.shapes[nk] = ctx.shapes[nk].translate(cq.Vector(0, 0, -Z))
        r1.append(nk)
    allk = r0 + r1
    h = Hoja(ctx, "ACC-036", "CILINDRO: ESQUEMA RETRAÍDO / EXTENDIDO, MEDIDAS OJO A OJO (MISMA ESCALA, ALINEADOS POR EL EJE DEL OJAL TRASERO E)", "", fmt="A1",
             material="Ver ACC-013 y ACC-028 a ACC-035", masa=f"{fm(C['masa_total'], 1)} kg c/u", trat="Ver ACC-013", serie="CON", items=[])
    from hojas_con import Conj
    c = Conj.__new__(Conj)
    c.keys, c.p0 = [], None
    c.init_plano(ctx, h)
    c.iso_keys, c.fmt_try = [], None
    ctx.subconjuntos.add(h.plano)
    s = c.s
    rE, rQ = float(C["fondo"]["ojal"]["rotula"]["d"]) / 2, float(C["ojal_vastago"]["d"]) / 2
    s0, sb = o["s0"], o["sb"]
    RQ, RE = float(C["ojal_vastago"]["R"]), float(C["fondo"]["ojal"]["R"])

    def esq(V, c_):
        for zz in (0.0, -Z):
            s.line(V.P(-RE - 12, 0, zz), V.P(Lx + RQ + 12, 0, zz), "EJE")
        s.line(V.P(0, 0, 40), V.P(0, 0, -Z - 40), "EJE")
        V.dimh((0, 0, 0), (L0, 0, 0), "top", 1, on=r0, virt_a=rE, virt_b=rQ, text=f"{f(L0)} (ojo a ojo, RETRAÍDO)")
        V.dimh((0, 0, 0), (s0, 0, 40), "top", 0, on=r0, virt_a=rE, text=f"{f(C['e_cuerpo'])} (e cuerpo)")
        V.dimh((s0, 0, 60), (sb, 0, 60), "top", 0, on=r0, text=f"{f(C['cuerpo'])} (cuerpo)")
        V.dimh((sb, 0, 40), (L0, 0, 0), "top", 0, on=r0, virt_b=rQ, text=f"({f(C['c_vastago'])} c vástago)")
        V.dimh((0, 0, -Z), (Lx, 0, -Z), "bottom", 1, on=r1, virt_a=rE, virt_b=rQ, text=f"{f(Lx)} (ojo a ojo, EXTENDIDO)")
        V.dimh((sb, 0, -Z - 40), (Lx, 0, -Z), "bottom", 0, on=r1, virt_b=rQ, text=f"({f(C['c_vastago'] + C['carrera'])} c vástago extendido)")
        V.dimh((L0, 0, 0), (Lx, 0, -Z), "bottom", 2, on=r0 + r1, virt_a=rQ, virt_b=rQ, text=f"({f(st)} carrera)")
        RT_ = C["fondo"]["ojal"]["rotula"]
        V.note_pt((0, -RE, 10), (-38, 30), f"Ojal trasero: pasador E Ø{f(RT_['d'])} en rótula {RT_['designacion'].split(' (')[0]} (D {f(RT_['D'])})", on=r0)
        V.note_pt((L0, -RQ, 10), (24, 30), f"Ojal del vástago: Ø{f(C['ojal_vastago']['d'])} {C['ojal_vastago']['tol_d']} (pasador Q, sin rótula)", on=r0)
        V.note_pt((0, -RE, -Z + 10), (-38, -30), "Mismo ojal E (fijo)", on=r1)
        dz = float(C.get("dz_tol") or 1.0)
        V.note_pt((0, -RE, -10), (-38, -26), f"Eje E: z ±{fm(dz / 2, 1)} (Δz E–Q ≤ {fm(dz, 0)})", on=r0)
        V.note_pt((L0, -RQ, -10), (24, -26), f"Eje Q: z ±{fm(dz / 2, 1)} (Δz E–Q ≤ {fm(dz, 0)})", on=r0)
        V.note_pt((Lx, -RQ, -Z + 10), (24, -30), f"Ø{f(C['ojal_vastago']['d'])} {C['ojal_vastago']['tol_d']}", on=r1)
    c.vs("esq", allk, "front", lv=(2, 3, 2, 3), extra=(60, 20, 60, 20), draw=esq, hatch=False, w=3.0, auto=False, mins=0.4, maxs=0.5,
         title="ESQUEMA: ARRIBA RETRAÍDO, ABAJO EXTENDIDO (EJE DEL OJAL TRASERO E COMÚN)")
    rows = [["Ojo a ojo retraído / extendido", f"{f(L0)} / {f(Lx)} mm"], ["Carrera", f"{f(st)} mm"],
            ["e cuerpo / cuerpo", f"{f(C['e_cuerpo'])} / {f(C['cuerpo'])} mm"], ["c vástago retraído / extendido", f"{f(C['c_vastago'])} / {f(C['c_vastago'] + C['carrera'])} mm"],
            ["Ojal trasero", f"pasador E Ø{f(C['fondo']['ojal']['rotula']['d'])} f8 en rótula {C['fondo']['ojal']['rotula']['designacion']}; orejeta R{fm(RE, 0)} × {f(C['fondo']['ojal']['ancho'])}"],
            ["Ojal del vástago", f"Ø{f(C['ojal_vastago']['d'])} {C['ojal_vastago']['tol_d']} sobre el pasador Q f8; R{fm(RQ, 0)} × {f(C['ojal_vastago']['ancho'])}; {C['ojal_vastago']['rotula']}"],
            ["Desnivel E–Q", f"≤ {fm(float(C.get('dz_tol') or 1), 1)} mm (admisible del vástago {fm(float(C.get('dz_adm') or 0), 2)} mm en el retraído; 1,3 mm en el estudio rev. 7e)"]]
    c.table_block("MEDIDAS OJO A OJO (bx.cilindro)", [("Dato", 50, "L"), ("Valor", 120, "L")], rows)
    c.table_block("CAPACIDAD (resumen; completa en ACC-013)", [("Dato", 60, "L"), ("Valor", 110, "L")], [list(r) for r in C["capacidad"]["filas"][1:7]])
    c.note_block("NOTAS", [C.get("dz_nota") or "", "Esquema de medidas generales: las piezas, tolerancias y sellos se definen en ACC-013 y ACC-028 a ACC-035.",
                           "Las dos vistas están a la misma escala y alineadas por el eje del ojal trasero E (pasador fijo del soporte E).",
                           "Medidas entre paréntesis: de referencia (resultan de las acotadas)."], numbered=True)
    c.note_block(REF_GEN_TIT, [REF_GEN])
    c.build()
    return c.h


PLAN_CIL = [("sheet_cil_camisa", ["cil_camisa"], sheet_cil_camisa), ("sheet_cil_fondo", ["cil_fondo", "cil_ojal_E"], sheet_cil_fondo), ("sheet_cil_tapa", ["cil_tapa"], sheet_cil_tapa),
            ("sheet_cil_piston", ["cil_piston", "cil_tuerca"], sheet_cil_piston), ("sheet_cil_vastago", ["cil_vastago"], sheet_cil_vastago), ("sheet_cil_ojal_q", ["cil_ojal_Q"], sheet_cil_ojal_q)]


def _extras_cil(ctx):
    C = _C(ctx)
    if C is None or not ctx.m.get("cil_camisa"):
        return []
    n = int(C["n"])
    return [("Prisionero ISO 4026 M6 × 8 con pastilla de latón (seguro de la tuerca del pistón)", 2 * n, "45H", "A DEFINIR POR CATÁLOGO"),
            ("Prisionero ISO 4026 M8 × 10 con pastilla de latón (antigiro de la tapa delantera)", n, "45H", "A DEFINIR POR CATÁLOGO"),
            ("Anillo elástico DIN 472 105 × 4 (rótula del ojal trasero)", n, "acero para resortes", "A DEFINIR POR CATÁLOGO"),
            ("Grasera DIN 71412 M8 × 1 (ojal del vástago)", n, "acero cincado", "A DEFINIR POR CATÁLOGO"),
            ("Racor recto G 1/2 con sello ED (ISO 1179-2) y reducción a 3/8\" para los puertos A y B", 2 * n, "acero cincado; ≥ " + f(C["p_prueba"]) + " bar", "A DEFINIR POR CATÁLOGO"),
            ("Fijador anaeróbico de alta resistencia (tuerca del pistón) y de resistencia media (prisioneros)", 1, "—", "A DEFINIR POR CATÁLOGO")]


def _extras_buje(ctx):
    """TT300-BX rev. 9: tornillo de retención del buje del seguidor (uno por pasador Q)."""
    B = ((getattr(ctx.g, "bx", None) or {}).get("buje_Q")) if ctx.m.get("buje_Q") else None
    if not B:
        return []
    return [(f"Tornillo {B['tornillo']['designacion']} con {B['tornillo']['fijador']} (retención del buje del seguidor {ctx.code('buje_Q').replace(CODE + '-', '')})", ctx.m.get("buje_Q").qty, "acero 10.9 zincado laminar", "A DEFINIR POR CATÁLOGO")]


DZ_TAGS = ("BAS-012-C", "ACC-020-C", "CON-007-C", "CON-010-C")


def _nota_dz(self, title, lines):
    """Rev. 7f: nota de la tolerancia de desnivel E–Q en las láminas del soporte E, de la placa-guía y del montaje del accionamiento."""
    C = _C(self.ctx) if hasattr(self, "ctx") else None
    if C and self.h.tag in DZ_TAGS and title in ("NOTAS DE FABRICACIÓN", "NOTAS DEL SUBCONJUNTO") and not getattr(self.h, "_dz", False):
        self.h._dz = True
        return list(lines) + [C.get("dz_nota") or ""]
    return lines


def _gen008_cil(ctx):
    C = _C(ctx)
    if C is None or not ctx.m.get("cil_camisa"):
        return []
    cap = dict((r[0], r[1]) for r in C["capacidad"]["filas"])
    return [["Cilindros hidráulicos (×" + str(int(C["n"])) + ", FABRICADOS: ACC-013)", f"{cap['Tipo']}; empuje {cap.get('Empuje a p_alivio ' + f(C['p_alivio']) + ' bar', '')} a {f(C['p_alivio'])} bar; prueba {f(C['p_prueba'])} bar; sellos {cap['Sellos']}", "Prueba hidráulica de fábrica a " + f(C["p_prueba"]) + " bar con certificado", "Fabricado (no de catálogo); " + cap["Si se reemplaza por uno comercial"]],
            ["Mangueras de las líneas A y B", cap["Mangueras"] + "; " + cap["Línea A (velocidad)"], "Certificado de prueba del fabricante", "marca/modelo A DEFINIR POR CATÁLOGO"],
            ["Racores de los puertos", cap["Racores"], "Certificado del lote", "marca/modelo A DEFINIR POR CATÁLOGO"],
            ["Circuito hidráulico", cap["Circuito"] + "; caudales: " + cap["Caudales"], "Prueba en vacío y a calado (CON-022)", "—"]]


def activar():
    for nm, keys, fn in PLAN_CIL:
        if not any(x[0] == nm for x in PLAN):
            PLAN.append((nm, keys, fn))
    import layout
    if not getattr(layout.Plano, "_dz", False):
        _nb0 = layout.Plano.note_block
        layout.Plano.note_block = lambda self, title, lines, numbered=False, _f=_nb0: _f(self, title, _nota_dz(self, title, lines), numbered)
        layout.Plano._dz = True
    import propuestas
    if not getattr(propuestas, "_cil_gen008", False):
        _cr0 = propuestas.catalogo_rows
        propuestas.catalogo_rows = lambda ctx, _f=_cr0: (_gen008_cil(ctx) + [r for r in _f(ctx) if not str(r[0]).startswith("Cilindro hidráulico de doble efecto")]) if _gen008_cil(ctx) else _f(ctx)
        propuestas._cil_gen008 = True
    import lista
    if not getattr(lista, "_cil_extras", False):
        _ex0 = lista.extras
        lista.extras = lambda ctx, _f=_ex0: _f(ctx) + _extras_cil(ctx) + _extras_buje(ctx)
        lista._cil_extras = True
    if not any(x[0] == "sheet_cil_conjunto" for x in PLAN):
        PLAN.append(("sheet_cil_conjunto", list(cil_bx.KEYS), sheet_cil_conjunto))
        NOGROUP.add("sheet_cil_conjunto")
    if not any(x[0] == "sheet_cil_esquema" for x in PLAN):
        PLAN.append(("sheet_cil_esquema", ["cil_camisa"], sheet_cil_esquema))
        NOGROUP.add("sheet_cil_esquema")
