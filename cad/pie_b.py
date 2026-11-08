"""Láminas de fabricación de la mesa: planchas, anillos, almas, nervios, cubo, pasadores de empuje y pernos."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *
from hojas_base import ranuras_cierre
from pie_a import ra, wd
from soldadura_det import add_prep


@pieza("mesa_plancha_sup")
def sheet_mesa_sup(ctx):
    g, P = ctx.g, ctx.P
    zt, tt = g.z0 + g.hd, g.tt
    p = Pieza(ctx, ["mesa_plancha_sup"], "MESA: PLANCHA SUPERIOR", fmt="auto")
    s = p.s
    on = ["mesa_plancha_sup"]
    jj = jids(ctx, "Plancha superior – anillo", "Cierre de la plancha")

    def planta(V, p):
        s.centerlines(V.P(0, 0, zt), g.prIn * V.scale, 8)
        p.cut_mark("planta", "A", (-g.prIn - 22, 0, zt), (g.prIn + 22, 0, zt), 90)
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 60, 0), draw=planta, title="PLANTA", w=4.0, mins=0.1,
         auto=dict(text={round(2 * g.prIn, 1): f"Ø{f(2 * g.prIn)} ±1,5"}, hole_rmin=3.0, verts=False, hole_pos=False, only_extents=True, fits={round(g.hole_top, 1): "H12", round(g.cb_D, 1): "H12"}, hole_txt={g.insp_drill: f"6 × M{fm(g.insp_d, 0)}-6H prof. {fm(g.insp_tap, 0)} (broca Ø{fm(g.insp_drill, 1)}) en el fondo del rebaje, PCD Ø{fm(g.insp_pcd, 0)}, a 30° + 60°·k"}, tol={}))
    x_a, x_b = g.hole_top / 2 - 25, g.prIn + 25

    def corte(V, p):
        w_out(p, jj[0], V, (g.prIn, 0, zt - tt / 2), "right", prep="60°", dy=-10)
        ra(s, V, (g.hole_top / 2 + 40, 0, zt), "Ra 6,3")
    p.vs("corte", on, "front", cut=CUT_Y, win=(x_a, zt - tt - 6, x_b, zt + 14), center=(0, 0, 0), breaks=[(g.hole_top / 2 + 180, g.prIn - 180)], lv=(1, 2, 1, 2), extra=(0, 0, 115, 0),
         draw=corte, title="CORTE A-A (radial, con rotura)", hs=0.5, w=1.2,
         auto=dict(tol={round(tt, 1): " (t_top)"}, text={}))
    p.detail("det_c", "corte", (g.hole_top / 2 + 10, 0, zt - tt / 2), 38, "B", lv=(1, 2, 1, 1), title="DETALLE B: AGUJERO CENTRAL Y REBAJE DE LA TAPA", maxs=2.0)
    # sin elevación: plancha de espesor constante; el espesor se acota en el corte
    for i, j_ in enumerate(jj):
        add_prep(p, f"det_j{i}", wd(ctx, j_), t1=tt)
    rc_ = ranuras_cierre(ctx)
    p.table_block(f"RANURAS DE CIERRE {jj[1] if len(jj) > 1 else ''} (22 × 80 a paso 250, eje de la ranura sobre el eje del alma o nervio)", [("Elemento", 34, "L"), ("Ubicación", 70, "L"), ("Ángulos", 46, "L"), ("Cant", 14, "R")],
                  [[a, b_, c_, str(n_)] for a, b_, c_, n_ in rc_] + [["TOTAL", "", "", str(sum(r_[3] for r_ in rc_))]], bold_rows=(len(rc_),))
    p.tables(jj)
    p.notes([f"Disco Ø{f(2 * g.prIn)} × {f(tt)}; oxicorte/plasma (ISO 9013 clase 3), partida Ø{f(2 * g.prIn + 5)} (sobremetal 2,5 por lado) para la preparación de la junta con el anillo superior (MES-002).",
             f"Agujero central Ø{f(g.hole_top)} y rebaje Ø{f(g.cb_D)} × {f(g.cb_t)} (apoyo de la tapa de inspección PIV-004): mecanizar en mandrinadora/fresadora; Ra 6,3.",
             f"Si el disco se obtiene de dos mitades: empalme CJP V 60° con respaldo, UT 100 %, esmerilar al ras (junta {jj[0]} familia).",
             f"Unión con el anillo: soldadura a tope circunferencial ({jj[0]}), caras superiores a ras; la plancha absorbe la abertura de raíz: Ø de corte de preparación {f(2 * g.prIn - 6)} (= Ø{f(2 * g.prIn)} − 2 × 3). "
             f"Transición 1:4 de t = {fm(g.tt, 0)} a {fm(g.tpr, 0)}: chaflán 1:4 en la cara inferior del anillo hasta 3 mm del agujero de pasador y el resto con la pendiente 1:4 del cordón (detalle {jj[0]}).",
             f"Soldadura de cierre sobre almas y nervios por ranuras ({jj[1]}): 22 × 80 a paso 250, posiciones en la tabla «RANURAS DE CIERRE» (PROPUESTA, confirmar); no modeladas en 3D.",
             "Distorsión: soldar la plancha superior en último lugar, con la mesa apoyada plana; verificar planitud 0,5. Paralelismo entre caras de la mesa: CON-009."],
            gd=[("flat", "0,5", None, "Planitud de la cara superior" + (" (apoyo de la cubierta de madera)" if g.wood else ""))])
    p.build()
    return p.h


@pieza("mesa_anillo_sup", "mesa_anillo_inf")
def sheet_mesa_anillos(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    a0 = D["pasadores"][0]
    zt = g.z0 + g.hd
    rot_key(ctx, "mesa_anillo_sup", "ras", -a0)
    pitch = 360.0 / g.N_pin
    p = Pieza(ctx, ["mesa_anillo_sup", "mesa_anillo_inf"], "MESA: ANILLOS SUPERIOR E INFERIOR DE PASADORES (28 AGUJEROS)", fmt="auto")
    s = p.s
    on = ["ras"]
    ej = jids(ctx, "Empalmes de los anillos")[0]
    jj = jids(ctx, "Plancha superior – anillo", "Plancha inferior – anillo")

    def planta(V, p):
        c3 = (0, 0, zt)
        s.circle(V.P(c3), g.R_pin * V.scale, "EJE")
        emp = [(sa + 0.5) * pitch for sa in (0, 7, 14, 21)]
        for ang in emp:
            pa = polar(g.prIn - 14, ang); pb = polar(g.Rt + 14, ang)
            s.line(V.P(pa + (zt,)), V.P(pb + (zt,)), "FANT")
        # eje +x de la mesa (la planta está girada para que el primer agujero quede sobre la horizontal)
        qx = polar(g.Rt + 40, -a0)
        s.line(V.P(c3), V.P(polar(g.Rt + 40, -a0) + (zt,)), "EJE")
        qx_ = V.P(polar(g.Rt + 40, -a0) + (zt,))
        s.text("+x (mesa)", (qx_[0] + 1, qx_[1] - 2), T_N, "TOP_LEFT")
        rh = g.d_pin / 2
        def ext_line(ang, r_to):
            s.line(V.P(polar(g.R_pin + rh + 3, ang) + (zt,)), V.P(polar(r_to + 4, ang) + (zt,)), "COTA")
        Ra1, Ra2 = g.Rt + 30, g.Rt + 70
        ext_line(0, Ra1)
        V.dim_ang_axes(c3, Ra1 * V.scale, -a0, 0, f"{fm(a0, 3)}° (1.er agujero desde +x)", axes=[((g.R_pin, 0.0, zt), rh)], on=on)
        kp = int(round(g.N_pin * 0.85))   # paso acotado abajo a la derecha, lejos de la cota del primer agujero y de la llamada de agujeros
        ext_line(kp * pitch, Ra1); ext_line((kp + 1) * pitch, Ra1)
        V.dim_ang_axes(c3, Ra1 * V.scale, kp * pitch, (kp + 1) * pitch, f"{fm(pitch, 3)}° (paso, {g.N_pin}×)",
                       axes=[(polar(g.R_pin, kp * pitch) + (zt,), rh), (polar(g.R_pin, (kp + 1) * pitch) + (zt,), rh)], on=on)
        k14 = g.N_pin // 2
        ext_line(k14 * pitch, Ra1)
        s.line(V.P(polar(g.Rt + 14, emp[2]) + (zt,)), V.P(polar(Ra1 + 4, emp[2]) + (zt,)), "COTA")
        V.dim_ang_axes(c3, Ra1 * V.scale, k14 * pitch, emp[2], f"{fm(emp[2] - k14 * pitch, 3)}° (empalme)", axes=[(polar(g.R_pin, k14 * pitch) + (zt,), rh)], on=on)
        s.line(V.P(polar(g.Rt + 14, emp[2]) + (zt,)), V.P(polar(Ra2 + 4, emp[2]) + (zt,)), "COTA")
        s.line(V.P(polar(g.Rt + 14, emp[1]) + (zt,)), V.P(polar(Ra2 + 4, emp[1]) + (zt,)), "COTA")
        s.dim_ang(V.P(c3), Ra2 * V.scale, emp[1], emp[2], "90° (entre empalmes)")
        p.cut_mark("planta", "A", (g.prIn - 30, 0, zt), (g.Rt + 25, 0, zt), 90)
        # PCD entre ejes de agujeros opuestos (verificada contra los ejes de los cilindros)
        h0, h14 = (g.R_pin, 0.0, zt), (-g.R_pin, 0.0, zt)
        V.dimh(h14, h0, "bottom", 1, on=on, text=f"PCD Ø{f(2 * g.R_pin)}", virt_a=g.d_pin / 2, virt_b=g.d_pin / 2, ted=True)
    p.vs("planta", on, "top", lv=(1, 2, 1, 1), extra=(25, 0, 45, 10), draw=planta, title="PLANTA (anillo; superior e inferior idénticos)", hatch=False, w=4.0, mins=0.1,
         auto=dict(fits={g.d_pin: "H7"}, hole_rmin=20, hole_pos=False, verts=False, only_extents=True, text={round(2 * g.Rt, 1): f"Ø{f(2 * g.Rt)} ±1,5", round(2 * g.prIn, 1): f"Ø{f(2 * g.prIn)} ±1,5"}))
    Rs, rs = g.Rt + 5, g.prIn - 5
    seg = [["Segmentos por anillo", "4 de 90° (empalmes entre agujeros, a 6,429° + 90°·k desde el 1.er agujero)".replace("6,429", fm(0.5 * pitch, 3))],
           ["Radio exterior / interior de corte", f"R{fm(Rs, 0)} / R{fm(rs, 0)} (sobremetal 5 mm por lado)"],
           ["Cuerda exterior de corte", f"{fm(2 * Rs * math.sin(math.radians(45)), 1)} mm"],
           ["Altura del segmento (flecha + ancho)", f"{fm(Rs - rs * math.cos(math.radians(45)), 1)} mm"],
           ["Ancho radial", f"{fm(Rs - rs, 0)} mm (terminado {fm(g.Rt - g.prIn, 0)})"], ["Espesor de partida", f"{fm(g.tpr + 3, 0)} mm (caras planeadas a {fm(g.tpr, 0)})"]]
    p.table_block("SEGMENTO DE PARTIDA PARA CORTE (plasma)", [("Dato", 60, "L"), ("Valor", 110, "L")], seg)
    x_a, x_b = g.prIn - 30, g.Rt + 30

    def corte(V, p):
        ra(s, V, (g.R_pin - g.d_pin / 2, 0, zt - g.tpr / 2), "Ra 3,2", dx=6, dy=-3)
        w_out(p, jj[0], V, (g.prIn, 0, zt - 3), "left", prep="60°", dy=12)
        w_out(p, jj[1], V, (g.prIn, 0, zt - g.tpr + 3), "left", prep="60°", dy=-14)
        V.dimh((g.prIn, 0, zt - g.tpr), (g.R_pin, 0, zt - g.tpr), "bottom", 2, on=on, text=f"{fm(g.R_pin - g.prIn, 1)} (al eje; PCD Ø{f(2 * g.R_pin)})", virt_b=g.d_pin / 2)
    p.vs("corte", on, "front", cut=CUT_Y, win=(x_a - g.R_pin, -g.tpr - 10, x_b - g.R_pin, 14), center=(g.R_pin, 0, zt), lv=(1, 2, 1, 3), extra=(105, 0, 0, 0), draw=corte,
         title="CORTE A-A: RADIAL POR UN PASADOR", hs=0.5, w=1.2, mins=1.0, maxs=1.0, auto=dict(fits={g.d_pin: "H7"}, tol={round(g.tpr, 1): ""}, text={round(g.d_pin, 1): f"Ø{f(g.d_pin)} H7 (+0,035/0)", round(g.Rt - g.prIn, 1): f"({fm(g.Rt - g.prIn, 0)})"}))
    add_prep(p, "det_e", wd(ctx, ej), t1=g.tpr)
    p.detail("det_p", "corte", (g.R_pin - g.d_pin / 2, 0, zt - 2), 22, "B", lv=(1, 1, 1, 1), title="DETALLE B: BORDE DEL AGUJERO", maxs=5.0) if False else None
    p.tables([ej] + jj)
    p.notes([f"Anillo Ø{f(2 * g.Rt)} / Ø{f(2 * g.prIn)} × {f(g.tpr)} en 4 segmentos de 90° (plasma); 2 anillos iguales (superior e inferior, MES-002 y MES-004).",
             f"{g.N_pin} agujeros Ø{f(g.d_pin)} H7 en PCD Ø{f(2 * g.R_pin)}: taladrar Ø80 en taladro radial por segmentos y MANDRINAR a Ø{f(g.d_pin)} H7 en línea con el otro anillo ya armado (plantilla común).",
             f"Posición angular: primer agujero a {fm(a0, 3)}°, paso {fm(pitch, 3)}°; los empalmes quedan entre agujeros (a {fm((0.5) * pitch, 2)}° de ellos).",
             f"Empalmes CJP V 60°, raíz 3, respaldo, UT 100 % ({ej}); esmerilar al ras antes de armar. Soldar los empalmes ANTES de unir con las planchas.",
             "UT de recepción de la plancha ASTM A578 nivel B y Z35 (EN 10164) por el esfuerzo en espesor de los pasadores.",
             "Rugosidad Ra 3,2 en los agujeros; aristas rotas 1×45°."] + notas_anillo_inf(ctx),
            gd=[("pos", "Ø0,3", "A", "Agujeros: posición respecto del eje de la mesa (A); PCD y ángulos del patrón: cotas teóricamente exactas (en recuadro)"), ("flat", "0,3", None, "Planitud de las caras del anillo")])
    p.build()
    return p.h


def notas_anillo_inf(ctx):
    """Agujeros propios del anillo inferior según la interfaz: roscas de los tornillos de posición y conductos de engrase (leídos del modelo)."""
    g, P, m = ctx.g, ctx.P, ctx.m
    out = []
    hm = centros_xy(m.info.get("holes_mesa"))
    pat = patron_txt(hm, f"M{fm(P['d_tor'], 0)}", rmin=g.prIn)
    if pat:
        out.append("Solo el anillo INFERIOR (MES-004): roscas de los tornillos de posición de los sectores de la mesa: " + "; ".join(pat) + "; profundidad según la lámina de sectores.")
    gp = m.info.get("grease_pts") or []
    if gp:
        pg = patron_txt(gp, "taladro axial Ø6", rmin=0)
        out.append(f"Solo el anillo INFERIOR (MES-004): conductos de engrase: grasera M10×1 en el canto (Ø10 × prof. 12 desde Ø{f(2 * g.Rt)}, fondo plano a Ø{f(2 * g.Rt - 24)}), "
                   f"taladro radial Ø6 desde R{fm(g.Ro - 30, 1)} hasta el canto; " + "; ".join(pg) + " hasta la cara inferior. Ver INT (graseras).")
    return out


@pieza("mesa_plancha_inf")
def sheet_mesa_inf(ctx):
    g, P = ctx.g, ctx.P
    z0, tbo = g.z0, g.tbo
    p = Pieza(ctx, ["mesa_plancha_inf"], "MESA: PLANCHA INFERIOR (CARA DE APOYO DE LA INTERFAZ)", fmt="auto")
    s = p.s
    on = ["mesa_plancha_inf"]
    ri = g.Drb / 2 if g.rebaje else g.d_bush / 2
    jj = jids(ctx, "Plancha inferior – anillo")

    def planta(V, p):
        s.centerlines(V.P(0, 0, z0), g.prIn * V.scale, 8)
        p.cut_mark("planta", "A", (-g.prIn - 22, 0, z0), (g.prIn + 22, 0, z0), -90)
    p.vs("planta", on, "bottom", lv=(1, 1, 1, 1), extra=(0, 0, 30, 0), draw=planta, title="VISTA INFERIOR (cara de apoyo)", w=1.5,
         auto=dict(hole_rmin=2.0, text={round(2 * g.prIn, 1): f"Ø{f(2 * g.prIn)} ±1,5"}))
    x_a, x_b = ri - 25, g.prIn + 25

    def corte(V, p):
        ra(s, V, (ri + 60, 0, z0), "Ra 3,2", dy=-20)
        if jj:
            w_out(p, jj[0], V, (g.prIn, 0, z0 + tbo / 2), "right", prep="60°", dy=-12)
    p.vs("corte", on, "front", cut=CUT_Y, win=(x_a, z0 - 6, x_b, z0 + tbo + 14), breaks=[(ri + 150, g.prIn - 150)], lv=(1, 3, 1, 2), extra=(0, 0, 115, 0), draw=corte,
         title="CORTE A-A (radial, con rotura)", hs=0.5, w=1.2, auto=dict(tol={round(tbo, 1): " (t_bot)"}))
    p.detail("det_c", "corte", (ri + 6, 0, z0 + tbo / 2), 30, "B", lv=(1, 2, 1, 1), title="DETALLE B: BORDE DEL AGUJERO (REBAJE DEL COLLAR)", maxs=5.0)
    # sin elevación: plancha de espesor constante; el espesor se acota en el corte A-A
    for i, j_ in enumerate(jj):
        add_prep(p, f"det_j{i}", wd(ctx, j_), t1=tbo)
    p.tables(jids(ctx, "Plancha inferior – anillo", "Barras de tope – plancha inferior"))
    p.notes([f"Disco Ø{f(2 * g.prIn)} × {f(tbo)} con +3 mm de sobremetal en la cara inferior (partida e = {f(tbo + 3)}), que se planea después de soldar; la junta {jj[0] if jj else 'J??'} se prepara para el espesor al soldar ({f(tbo + 3)}). "
             f"Oxicorte/plasma ISO 9013 clase 3; la plancha absorbe la abertura de raíz: Ø de corte de preparación {f(2 * g.prIn - 6)}.",
             f"Agujero central Ø{f(2 * ri)}: " + (f"PASANTE por el rebaje del collar (Ø{f(g.D_boss)} del collar + 2 × {fm(g.c_boss_r, 0)} mm); holgura radial {fm(g.c_boss_r, 0)} mm, axial {fm(g.c_boss_a, 0)} mm." if g.rebaje else "mandrinado para el buje."),
             f"Cara inferior planeada después de soldar la mesa y aliviar tensiones: planitud 0,20, Ra 3,2 (apoyo de la interfaz, {g.interfaz_nombre}).",
             f"Unión con el anillo inferior: soldadura a tope circunferencial con caras inferiores a ras y transición 1:4 en la cara superior del anillo (chaflán hasta 3 mm del agujero de pasador + pendiente del cordón) ({jj[0] if jj else 'J??'}). Pasadores Ø{f(g.d_pin)} del anillo: ver MES-002/004."],
            gd=[("flat", "0,20", None, "Planitud de la cara inferior (antes de montar la interfaz); paralelismo entre caras de la mesa: CON-009")])
    p.build()
    return p.h


@pieza("mesa_alma0", "mesa_alma1", "mesa_alma2")
def sheet_almas(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    z0 = g.z0 + g.tbo
    ks = [f"mesa_alma{i}" for i in range(len(D["almas"]))]
    p = Pieza(ctx, ks, "MESA: ALMAS ANULARES (3 ANILLOS)", fmt="auto")
    s = p.s
    ids = jids(ctx, "Almas anulares", "Empalme de cada alma")

    def planta(V, p):
        for i, r in enumerate(D["almas"]):
            V.dim_rad((0, 0, z0 + g.hw), r + P["t_web"] / 2, -40 + 25 * i, on=[ks[i]], text=f"R{fm(r + P['t_web'] / 2, 0)} (cara ext.; eje R{f(r)}) — A{i + 1}", ext=22 + 6 * i)
        s.centerlines(V.P(0, 0, z0), D["almas"][-1] * V.scale, 8)
    p.vs("planta", ks, "top", lv=(1, 1, 1, 1), extra=(0, 0, 70, 0), draw=planta, title="PLANTA DE LAS 3 ALMAS", hatch=False, w=1.5, auto=False)
    k0, r = ks[-1], D["almas"][-1]

    def corte(V, p):
        w_out(p, ids[0], V, (r + P["t_web"] / 2, 0, z0 + 2), "right", other=None, dy=14)
    p.vs("corte", [k0], "front", cut=CUT_Y, center=(r, 0, z0), win=(-14, -6, 14, g.hw + 8), lv=(1, 2, 1, 2), extra=(0, 0, 115, 0), draw=corte, title="CORTE DE UNA ALMA (todas iguales en sección)", hs=0.35, maxs=2.0, w=1.0,
         auto=dict(tol={round(g.hw, 1): " ±0,5", round(P["t_web"], 1): ""}))
    rows = [[f"A{i + 1}", f"{ctx.code(k).replace(CODE + '-', '')}", f(2 * r_), f"Ø{f(2 * r_ + P['t_web'])} / Ø{f(2 * r_ - P['t_web'])}", f(2 * math.pi * r_, 0), f"{math.ceil((2 * math.pi * r_ + 20) / 6000)} pletina rolada (largo comercial 6 m)", f"{fm(g.hw, 0)} × {fm(P['t_web'], 0)}"]
            for i, (k, r_) in enumerate(zip(ks, D["almas"]))]
    p.table_block("DESARROLLO DE LAS ALMAS (pletina rolada)", [("Alma", 14, "C"), ("Código", 24, "L"), ("Ø eje [mm]", 20, "R"), ("Ø ext. / Ø int.", 34, "R"), ("Desarrollo [mm]", 24, "R"), ("Suministro", 26, "L"), ("h × t", 16, "C")], rows)
    add_prep(p, "det_e", wd(ctx, ids[1]), t1=P["t_web"])
    add_prep(p, "det_f", wd(ctx, ids[0]), t1=P["t_web"], t2=g.tt)
    p.tables(ids)
    p.notes([f"Pletina {fm(P['t_web'], 0)} × {f(g.hw)} rolada a los radios de eje R = {', '.join(f(x) for x in D['almas'])} mm; desarrollo = 2πR.",
             f"Cada alma tiene 1 empalme a tope V 60° ({ids[1]}), UT 100 %, esmerilado al ras; ubicar el empalme entre nervios.",
             f"Altura h = {f(g.hd)} − {f(g.tt)} − {f(g.tbo)} = {f(g.hw)} ±0,5 (altura de la mesa menos espesores de las planchas): cortar a medida y verificar con plantilla antes de armar la mesa.",
             f"Filete a las planchas superior e inferior z{fm(P['w_web'], 0)} ambos lados continuo ({ids[0]}). " + ("El tamaño supera el máximo AISC J2.2b (t − 2): pendiente del calculista (GEN-009)." if P["w_web"] > P["t_web"] - 2 else "Cumple mínimo AWS y máximo AISC J2.2b."),
             "Las almas son continuas; los nervios se cortan entre almas (ver MES-008…010)."],
            gd=[("perp", "0,5", "A", "Alma perpendicular a la cara de la plancha inferior (A); altura h ±0,5"), ("circ", "2,0", None, "Redondez del anillo rolado (desviación radial máx.)")])
    p.build()
    return p.h


@pieza("mesa_nervio0", "mesa_nervio1", "mesa_nervio2")
def sheet_nervios(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    ks = [k for k in ("mesa_nervio0", "mesa_nervio1", "mesa_nervio2") if k in ctx.shapes]
    z0 = g.z0 + g.tbo
    loc = []
    for k in ks:
        ctx.local_ang(k, k + "_1", D["nervios"][0], 4)
        loc.append(k + "_1")
    p = Pieza(ctx, ks, "MESA: NERVIOS RADIALES (TRAMOS ENTRE ALMAS)", fmt="auto")
    s = p.s
    p.iso_keys = list(loc)
    rows = []
    jn = jids(ctx, "Nervios radiales")
    for i, (k, kl) in enumerate(zip(ks, loc)):
        bb = ctx.shapes[kl].BoundingBox()
        L = bb.xlen

        def d_(V, p, i=i, bb=bb):
            if jn and i == len(ks) - 1:
                w_out(p, jn[0], V, (bb.xmax, bb.ymin, z0 + g.hw / 2), "right", dy=12)
        p.vs(f"n{i}", [kl], "front", lv=(1, 2, 2, 1), extra=(0, 0, 100 if i == len(ks) - 1 else 0, 0), draw=d_, hatch=False,
             title=f"NERVIO TRAMO {i + 1} ({ctx.code(k).replace(CODE + '-', '')}) — {int(P['N_rib'])} unidades", w=1.2,
             auto=dict(tol={round(g.hw, 1): " ±0,5"}, text={round(L, 1): f"{fm(L, 0)} ±0,5"}))
        rows.append([f"{i + 1}", ctx.code(k).replace(CODE + "-", ""), fm(bb.xmin, 0), fm(bb.xmax, 0), fm(L, 0), fm(L - 2, 0), f"{fm(g.hw, 0)} × {fm(P['t_rib'], 0)}", f"{int(P['N_rib'])}"])
    p.table_block("TRAMOS DE NERVIO", [("Tramo", 14, "C"), ("Código", 22, "L"), ("R interior", 20, "R"), ("R exterior", 20, "R"), ("Largo entre caras", 24, "R"), ("Largo de corte", 22, "R"), ("h × t", 22, "C"), ("Cant", 12, "C")], rows)
    ang = D["nervios"]
    arows = [[f"{i + 1}", fm(a, 3) + "°", f"{i + 15}" if False else "", ""] for i, a in enumerate(ang)]
    half = (len(ang) + 1) // 2
    arows = [[str(i + 1), fm(ang[i], 3) + "°", str(i + 1 + half) if i + half < len(ang) else "", (fm(ang[i + half], 3) + "°") if i + half < len(ang) else ""] for i in range(half)]
    p.table_block("POSICIÓN ANGULAR DE LOS NERVIOS (desde +x, antihorario)", [("N°", 12, "C"), ("Ángulo", 36, "R"), ("N°", 12, "C"), ("Ángulo", 36, "R")], arows)
    add_prep(p, "det_j", wd(ctx, jn[0]), t1=P["t_rib"], t2=g.tbo) if jn else None
    p.tables(jn)
    p.notes([f"Pletina {fm(P['t_rib'], 0)} × {f(g.hw)}; {int(P['N_rib'])} nervios por tramo, 3 tramos (entre cubo, almas A1…A3 y borde exterior de los nervios a R{f(P['R_rib'])}).",
             "Corte por plasma anidado en plancha (GEN-010/013); largo de corte = largo entre caras − 2 mm (1 mm de holgura de armado por extremo). Destijeres a 45° de 15 × 15 en las 4 esquinas de cada tramo, para el paso de los filetes de las almas (J14) y de la CJP del cubo (J17).",
             f"Filete z{fm(P['w_web'], 0)} ambos lados contra planchas y almas, continuo ({jn[0] if jn else 'J??'}); armar sobre la plancha inferior con plantilla angular ±0,1°.",
             "Nervios y almas se sueldan a la plancha inferior ANTES de cerrar con la superior. Posición angular de cada nervio ±0,1° respecto de +x (tabla de ángulos)."],
            gd=[("straight", "1,0", None, "Rectitud del canto de apoyo de cada nervio")])
    p.build()
    return p.h


@pieza("mesa_cubo")
def sheet_cubo(ctx):
    g, P = ctx.g, ctx.P
    z0 = g.z0 + g.tbo
    p = Pieza(ctx, ["mesa_cubo"], "MESA: CUBO", fmt="auto")
    s = p.s
    on = ["mesa_cubo"]
    zt = z0 + g.hw
    jc = jids(ctx, "Cubo")

    def planta(V, p):
        s.centerlines(V.P(0, 0, zt), P["D_hub"] / 2 * V.scale, 6)
        p.cut_mark("planta", "A", (-P["D_hub"] / 2 - 14, 0, zt), (P["D_hub"] / 2 + 14, 0, zt), 90)
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 70, 0), draw=planta, title="PLANTA", w=1.0, auto=dict(fits={g.d_bush: "H7"}, hole_rmin=20))

    def corte(V, p):
        ra(s, V, (-g.d_bush / 2 + 1, 0, zt - g.hw / 2), "Ra 1,6", dx=4, dy=-6)
        if jc:
            w_out(p, jc[0], V, (P["D_hub"] / 2, 0, z0), "right", prep="45°", dy=-12)
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 2, 2, 3), extra=(0, 0, 115, 0), draw=corte, title="CORTE A-A", hs=0.6, w=1.4,
         auto=dict(rev=(0, 0), fits={g.d_bush: "H7"}, rev_side="top", tol={round(g.hw, 1): " ±0,5"}, text={round(g.Drb, 1): f"Ø{f(g.Drb)} (rebaje del collar)"}))
    if g.rebaje and g.hHub > 0:
        p.detail("det_r", "corte", (g.Drb / 2, 0, z0 + g.hHub / 2), 25, "B", lv=(1, 2, 1, 1), title="DETALLE B: REBAJE DEL COLLAR", maxs=5.0)
    if jc:
        add_prep(p, "det_j", wd(ctx, jc[0]), t1=g.hw)
    p.tables(jc)
    p.notes([f"Anillo Ø{f(P['D_hub'])} / Ø{f(g.d_bush)} × {f(g.hw)} de plancha gruesa o tubo, corte a llama; agujero Ø{f(g.d_bush)} H7 y rebaje Ø{f(g.Drb)} en mandrinadora (sin torno vertical).",
             f"Ajuste del buje (PIV-002): {f(g.d_bush)} H7 / s6, prensado. Holgura radial del collar {fm(g.c_boss_r, 0)} mm y axial {fm(g.c_boss_a, 0)} mm (del cálculo).",
             f"Soldar a las planchas inferior y superior ({jc[0] if jc else 'J??'}) y luego mandrinar H7 con la mesa armada y aliviada; Ra 1,6.",
             "Perpendicularidad de las caras 0,10; coaxialidad del agujero con el eje de la mesa 0,05."],
            gd=[("coax", "Ø0,05", "A", "Ø%s H7 coaxial con el eje de la mesa (A)" % f(g.d_bush)), ("perp", "0,10", "A", "Caras inferior y superior perpendiculares al eje")])
    p.build()
    return p.h


@pieza("pasadores")
def sheet_pasador(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    xy = polar(g.R_pin, D["pasadores"][0])
    ctx.local("pasadores", "pin1", near=(xy[0], xy[1], g.z0 + g.hd / 2), r=60, shift=(-xy[0], -xy[1], 0))
    z0, zt, r = g.z0, g.z0 + g.hd, g.d_pin / 2
    p = Pieza(ctx, ["pasadores"], f"MESA: PASADOR DE EMPUJE Ø{f(g.d_pin)} ({g.N_pin} UNIDADES)", fmt="auto")
    s = p.s
    p.iso_keys = ["pin1"]
    on = ["pin1"]
    zc0, zc1 = g.zc - P["dog_h"] / 2, g.zc + P["dog_h"] / 2

    def elev(V, p):
        s.line(V.P(0, 0, z0 - 8), V.P(0, 0, zt + 8), "EJE")
        for z_ in (zc0, zc1):           # límites de la franja templada (línea gruesa de trazo y punto, ISO 128 tipo 04.2, junto a la superficie)
            s.line(V.P(-r - 6, 0, z_), V.P(-r + 6, 0, z_), "TRAT"); s.line(V.P(r - 6, 0, z_), V.P(r + 6, 0, z_), "TRAT")
        V.dimv((-r + g.ch_pin, 0, z0), (-r, 0, zc0), "left", 0, on=on, text=f"{fm(zc0 - z0, 0)} (inicio de la franja templada, desde la cara sin rosca)")
        V.dimv((-r + g.ch_pin, 0, z0), (-r, 0, zc1), "left", 1, on=on, text=f"{fm(zc1 - z0, 0)} (fin de la franja templada)")
        ra(s, V, (r, 0, z0 + g.hd / 2), "Ra 0,8", dx=22, dy=0)
    p.vs("elev", on, "front", lv=(2, 2, 2, 3), extra=(0, 0, 115, 0), draw=elev, hatch=False, title="ELEVACIÓN", w=1.5,
         auto=dict(rev=(0, 0), rev_only=[g.d_pin], fits={g.d_pin: "m6"}, rev_side="top", tol={round(g.hd, 1): " ±0,1"}, hole_notes=False))

    def extremo(V, p):
        p.cut_mark("extremo", "A", (-r - 14, 0, zt), (r + 14, 0, zt), 90)
    p.vs("extremo", on, "top", lv=(1, 1, 1, 1), title="VISTA DE EXTREMO (extremo roscado)", hatch=False, w=0.8, draw=extremo, maxs=2.0,
         auto=dict(fits={}, hole_rmin=5, hole_pos=False, verts=False, hole_txt={g.pin_drill: f"M20-6H, rosca útil {fm(g.pin_thr, 0)}, taladro Ø{fm(g.pin_drill, 1)} prof. {fm(g.pin_drill_L, 0)} (perno ISO 4762 M20×45 cl. 10.9)"}))

    def corte(V, p):
        zb_ = zt - g.pin_drill_L
        for e_ in (-10.0, 10.0):          # diámetro nominal de la rosca en línea fina (ISO 6410-1)
            s.line(V.P(e_, 0, zt), V.P(e_, 0, zt - g.pin_thr), "FINA")
        s.line(V.P(-10.0, 0, zt - g.pin_thr), V.P(10.0, 0, zt - g.pin_thr), "VIS")
        V.dimv((g.pin_drill / 2, 0, zb_), (g.pin_drill / 2, 0, zt), "right", 0, on=on, text=f"{fm(g.pin_drill_L, 0)} (taladro Ø{fm(g.pin_drill, 1)})")
        V.dimv((-g.pin_drill / 2, 0, zt - g.pin_thr), (-g.pin_drill / 2, 0, zt), "left", 0, on=on, text=f"{fm(g.pin_thr, 0)} (rosca útil M20-6H)")
        a_, b_ = V.P(-r - 3, 0, zt - 62), V.P(r + 3, 0, zt - 62)       # línea de rotura ISO 128-30 (fina con zigzag) en el borde de la vista parcial
        xm_ = (a_[0] + b_[0]) / 2
        s.pline([a_, (xm_ - 6, a_[1]), (xm_ - 2.2, a_[1] + 3.5), (xm_ + 2.2, a_[1] - 3.5), (xm_ + 6, a_[1]), b_], "FINA")
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 1, 1, 1), title="CORTE A-A: ROSCA M20 (vista parcial con rotura)", hs=0.5, w=1.2, auto=False, draw=corte,
         win=(-r - 4, zt - 62, r + 4, zt + 4), maxs=2.0)
    p.detail("det_ch", "elev", (r - 1, 0, zt - 1), 9, "B", lv=(1, 1, 1, 1), title="DETALLE B: CHAFLÁN DE EXTREMO (5:1)", maxs=5.0, hatch=False)
    p.tables()
    p.notes([f"Barra Ø{f(g.d_pin + 5)} laminada/rectificada; torno horizontal o rectificado externo: Ø{f(g.d_pin)} m6 ({iso286.fmt_dev(g.d_pin, 'm6')} mm), Ra 0,8; largo {f(g.hd)} ±0,1.",
             f"Tratamiento (ISO 15787): bonificado y temple por inducción de la franja de contacto ({f(P['dog_h'])} mm, ubicada desde la cara sin rosca según la elevación) ≥ 55 HRC (límite elástico superficial supuesto en el cálculo: {f(P['Fy_surf'])} MPa), profundidad efectiva ≥ {fm(g.z_hard, 1)} mm; Fy ≥ {f(P['Fy_pin'])} MPa (34CrNiMo6+QT, EN 10083-3).",
             f"Chaflán {fm(g.ch_pin, 0)}×45° en ambos extremos (ISO 13715). Rosca M20-6H en un extremo (ISO 262): rosca útil {fm(g.pin_thr, 0)}, taladro Ø{fm(g.pin_drill, 1)} prof. {fm(g.pin_drill_L, 0)}; perno ISO 4762 M20×45 cl. 10.9; torque propuesto en GEN-008 (PROPUESTA, A CONFIRMAR POR EL CALCULISTA).",
             f"Ajuste en los anillos {f(g.d_pin)} H7/m6 (transición, desmontable). Montar con grasa; sin soldadura.",
             f"Marcar con punzón el número del pasador (1…{g.N_pin}) y la colada en el extremo roscado; 10 % de dureza superficial por lote."],
            gd=[("cyl", "0,02", None, "Cilindricidad del Ø%s m6" % f(g.d_pin)), ("perp", "0,05", "A", "Caras extremas perpendiculares al eje del Ø%s m6 (A)" % f(g.d_pin))])
    p.build()
    return p.h


@pieza("pernos_pasador")
def sheet_pernos(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    if not ctx.m.get("pernos_pasador"):
        return None
    xy = polar(g.R_pin, D["pasadores"][0])
    zt = g.z0 + g.hd
    ctx.local("pernos_pasador", "perno1", near=(xy[0], xy[1], zt + 15), r=80, shift=(-xy[0], -xy[1], 0))
    p = Pieza(ctx, ["pernos_pasador"], "MESA: PERNO ISO 4762 M20×45 CON ARANDELA (28 UNIDADES)", fmt="auto")
    s = p.s
    p.iso_keys = ["perno1"]
    on = ["perno1"]

    def elev(V, p):
        s.line(V.P(0, 0, zt - 4), V.P(0, 0, zt + 40), "EJE")
        s.leader(V.P(0, 0, zt + 36), (V.P(0, 0, zt + 36)[0] + 36, V.P(0, 0, zt + 36)[1] + 20), "Hexágono interior s = 17 (ISO 4762, M20)", dot=True)
    p.vs("corte", on, "front", cut=CUT_Y, lv=(2, 2, 2, 3), extra=(0, 0, 70, 0), draw=elev, title="CORTE A-A: PERNO Y ARANDELA (montado sobre el pasador)", hs=0.5, w=1.6, auto=dict(rev=(0, 0), rev_side="top", hole_notes=False),
         mat={"perno1": "acero"})
    def pl_(V, p):
        p.cut_mark("planta", "A", (-g.washer_D / 2 - 12, 0, zt + 10), (g.washer_D / 2 + 12, 0, zt + 10), 90)
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 50, 0), title="PLANTA (cabeza y arandela)", hatch=False, w=1.0, draw=pl_, auto=dict(hole_rmin=3.0, hole_txt={g.washer_d: f"Ø{fm(g.washer_d, 0)} (agujero de la arandela)"}), maxs=2.0)
    rows = [["Perno", "ISO 4762 M20×45, clase 10.9, rosca ISO 262 M20×2,5-6g, recubrimiento zincado/dacromet", f"{g.N_pin}", "ISO 898-1 cl. 10.9"],
            ["Arandela", f"Ø{f(g.washer_D)} / Ø{f(g.washer_d)} × {f(g.washer_t)}, cortada por plasma o láser, templada y revenida, caras rectificadas", f"{g.N_pin}", WASHER_MAT],
            ["Rosca receptora", f"M20-6H, rosca útil {fm(g.pin_thr, 0)}, taladro Ø{fm(g.pin_drill, 1)} prof. {fm(g.pin_drill_L, 0)} en el pasador (MES-012)", f"{g.N_pin}", "Macho de roscar clase 6H"]]
    p.table_block("ESPECIFICACIÓN DEL CONJUNTO PERNO–ARANDELA", [("Elemento", 22, "L"), ("Característica", 80, "L"), ("Cant", 12, "C"), ("Material / certificado", 56, "L")], rows)
    p.tables()
    p.notes(["Elementos comerciales de catálogo (marca/modelo: ver GEN-008); este plano fija las dimensiones de interfaz y el montaje.",
             "Torque de apriete: ver GEN-008 (propuesta, a confirmar por el calculista según VDI 2230); marca de pintura de control tras el apriete.",
             "Rosca limpia y con pasta antigripante; arandela asentada sobre la cara del pasador y del anillo superior" + (" (bolsillo de la cubierta de madera, MAD-001)" if g.wood else "") + "; sin soldadura."],
            gd=[("perp", "0,10", "A", "Cara de apoyo de la arandela perpendicular al eje del pasador")])
    p.build()
    return p.h
