"""TT300-BX rev. 7c (decisión del mandante 19-11-2026): láminas de las planchas ENTERAS de la mesa (una pieza Ø D_top por nivel con los N_pin
agujeros H7 de los pasadores de empuje). Reemplazan a MES-001 / MES-003 del juego con disco + anillo; MES-002 / MES-004 (anillos) no existen.
Solo se usan con el bloque bx.mesa.plancha_entera del JSON (g.mesa_entera); sin él, las láminas de cad/pie_b.py no cambian."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *
from hojas_base import ranuras_cierre
from pie_a import wd
from soldadura_det import add_prep


def _cc(ctx, k):
    return ctx.code(k).replace(CODE + "-", "").replace("-" + REV, "")


def _tabla_agujeros(ctx, p, cara):
    """Tabla de los N_pin agujeros (n.°, ángulo desde +x de la mesa, X, Y) en dos columnas de filas."""
    g, D = ctx.g, ctx.D
    angs = [float(a) for a in D["pasadores"]]
    filas = [(i + 1, a, g.R_pin * math.cos(math.radians(a)), g.R_pin * math.sin(math.radians(a))) for i, a in enumerate(angs)]
    h = (len(filas) + 1) // 2
    rows = []
    for k in range(h):
        r_ = []
        for q in (filas[k], filas[k + h] if k + h < len(filas) else None):
            r_ += [str(q[0]), fm(q[1], 3), fm(q[2], 1), fm(q[3], 1)] if q else ["", "", "", ""]
        rows.append(r_)
    cols = [("N.°", 8, "C"), ("Ángulo [°]", 18, "R"), ("X [mm]", 18, "R"), ("Y [mm]", 18, "R")] * 2
    p.table_block(f"TABLA DE AGUJEROS: {len(filas)} × Ø{f(g.d_pin)} H7 (+0,035/0) PASANTES, PCD Ø{f(2 * g.R_pin)} (R{fm(g.R_pin, 0)}); origen = eje de la mesa, ángulos desde +x (antihorario visto desde arriba; {cara})",
                  cols, rows)


def _planta(ctx, p, z, on, a0, pitch, sg, extra_draw=None):
    """Patrón de agujeros en la planta girada (primer agujero sobre la horizontal): ejes, ángulo del 1.er agujero, paso, PCD y llamada de los
    agujeros. sg = +1 vista superior, −1 vista inferior (el papel ve el ángulo del modelo con signo cambiado; el patrón es simétrico respecto de x)."""
    g = ctx.g
    s = p.s

    def planta(V, p):
        c3 = (0, 0, z)
        s.circle(V.P(c3), g.R_pin * V.scale, "EJE")
        s.centerlines(V.P(c3), g.Rt * V.scale, 8)
        s.line(V.P(c3), V.P(polar(g.Rt + 40, -a0) + (z,)), "EJE")            # +x de la mesa (modelo girado −a0)
        qx_ = V.P(polar(g.Rt + 40, -a0) + (z,))
        s.text("+x (mesa)", (qx_[0] + 1, qx_[1] - 2 if sg > 0 else qx_[1] + 5), T_N, "TOP_LEFT")
        rh = g.d_pin / 2

        def ext_line(pa, r_to):              # pa: ángulo en el papel (el modelo lo ve con sg·pa)
            s.line(V.P(polar(g.R_pin + rh + 3, sg * pa) + (z,)), V.P(polar(r_to + 4, sg * pa) + (z,)), "COTA")
        Ra1 = g.Rt + 30
        ext_line(0, Ra1)
        A_, B_ = sorted((0.0, -sg * a0))
        V.dim_ang_axes(c3, Ra1 * V.scale, A_, B_, f"{fm(a0, 3)}° (1.er agujero desde +x)", axes=[((g.R_pin, 0.0, z), rh)], on=on)
        # paso: abajo a la derecha en el papel; los ejes que verifican la cota se toman en el mismo ángulo del modelo (patrón simétrico respecto de x)
        k_ = int(round(g.N_pin * 0.15))
        a1_, a2_ = -(k_ + 1) * pitch, -k_ * pitch
        ext_line(a1_, Ra1); ext_line(a2_, Ra1)
        V.dim_ang_axes(c3, Ra1 * V.scale, a1_, a2_, f"{fm(pitch, 3)}° (paso, {g.N_pin}×)",
                       axes=[(polar(g.R_pin, a1_) + (z,), rh), (polar(g.R_pin, a2_) + (z,), rh)], on=on)
        h0, h14 = (g.R_pin, 0.0, z), (-g.R_pin, 0.0, z)
        V.dimh(h14, h0, "bottom", 1, on=on, text=f"PCD Ø{f(2 * g.R_pin)}", virt_a=g.d_pin / 2, virt_b=g.d_pin / 2, ted=True)
        p.cut_mark("planta", "A", (g.hole_top / 2 - 25 if sg > 0 else g.Drb / 2 - 25, 0, z), (g.Rt + 25, 0, z), 90 * sg)
        # llamada de los agujeros de los pasadores: agujero a ≈ 77° en el papel, línea casi vertical hacia arriba y texto a la derecha
        pq_ = 6 * pitch
        V.note_hole(polar(g.R_pin, sg * pq_) + (z,), rh, pq_ + 3, f"{g.N_pin} × Ø{f(g.d_pin)} H7", ext=(g.Rt - g.R_pin) * V.scale + 14, on=on,
                    lines=[f"{g.N_pin} × Ø{f(g.d_pin)} H7 (+0,035/0) pasantes", f"PCD Ø{f(2 * g.R_pin)}, paso {fm(pitch, 3)}° (tabla de agujeros)"])
        if extra_draw:
            extra_draw(V, p)
    return planta


def sheet_sup(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    zt, tt = g.z0 + g.hd, g.tt
    a0 = float(D["pasadores"][0])
    pitch = 360.0 / g.N_pin
    rot_key(ctx, "mesa_plancha_sup", "pse", -a0)
    p = Pieza(ctx, ["mesa_plancha_sup"], f"MESA: PLANCHA SUPERIOR ENTERA Ø{f(P['D_top'])} × {f(tt)} CON {g.N_pin} AGUJEROS Ø{f(g.d_pin)} H7", fmt="auto")
    on = ["pse"]
    jj = jids(ctx, "Cierre de la plancha")
    jP = ctx.weld_find("Pasadores de empuje")

    def m8(V, p):
        hx = (g.insp_pcd / 2 * math.cos(math.radians(330 - a0)), g.insp_pcd / 2 * math.sin(math.radians(330 - a0)), zt - g.cb_t)
        V.note_hole(hx, g.insp_drill / 2, -40, "6 × M8-6H", ext=(g.R_pin - g.d_pin - g.insp_pcd / 2) * V.scale, on=on,
                    lines=[f"6 × M{fm(g.insp_d, 0)}-6H pasante (taladro Ø{fm(g.insp_drill, 1)})", f"en el fondo del rebaje, PCD Ø{fm(g.insp_pcd, 0)}, 30° + 60°·k desde +x"])
    p.vs("planta", on, "top", lv=(1, 2, 1, 1), extra=(25, 0, 45, 10), draw=_planta(ctx, p, zt, on, a0, pitch, 1, m8), title="PLANTA (girada: 1.er agujero sobre la horizontal)", hatch=False, w=4.0, mins=0.1,
         auto=dict(fits={round(g.hole_top, 1): "H12", round(g.cb_D, 1): "H12"}, hole_rmin=g.d_pin / 2 + 1, hole_pos=False, verts=False, only_extents=True,
                   text={round(2 * g.Rt, 1): f"Ø{f(2 * g.Rt)} ±1,5"}))
    # datum A: agujero central Ø200 (su eje = eje de la mesa), en el detalle B (en la planta no hay lugar libre junto al rebaje)
    p.datum_in("det_c", "surf", "A", at=[(g.hole_top / 2, 0, zt - tt + 4), (g.hole_top / 2, 0, zt - tt + 7)], d=(-1, 0, 0))
    p.gd_in("planta", "callout", "pos", "Ø0,3", "A", prefix=f"{g.N_pin} × Ø{f(g.d_pin)}")
    x_a, x_b = g.hole_top / 2 - 25, g.Rt + 25

    def corte(V, p):
        V.dimv((g.Rt, 0, zt - tt), (g.Rt, 0, zt), "right", 0, on=on, text=f"{f(tt)} (t_top)")
        V.dimh((g.R_pin - g.d_pin / 2, 0, zt), (g.R_pin + g.d_pin / 2, 0, zt), "top", 0, on=on, text=f"Ø{f(g.d_pin)} H7 (+0,035/0)")
        V.dimh((g.R_pin, 0, zt - tt), (g.Rt, 0, zt - tt), "bottom", 0, on=on, text=f"{fm(g.Rt - g.R_pin, 0)}", virt_a=g.d_pin / 2)
        if jj:                           # ranura de cierre J18 sobre el alma exterior (posiciones en la tabla «RANURAS DE CIERRE»; preparación en GEN-007)
            ra_ = max(r_ for r_ in D["almas"] if r_ < g.R_pin - g.d_pin / 2)
            w_out(p, jj[0], V, (ra_, 0, zt), "top", dy=0)
    p.ra_in("corte", "Ra 6,3", [(g.hole_top / 2 + 150, 0, zt), (g.R_pin - g.d_pin / 2 - 60, 0, zt)], (0, 0, 1))
    p.gd_in("corte", "surf", "flat", "0,5", None, at=[(g.hole_top / 2 + 100, 0, zt), (g.R_pin - g.d_pin / 2 - 100, 0, zt)], d=(0, 0, 1))
    p.vs("corte", on, "front", cut=CUT_Y, win=(x_a, zt - tt - 6, x_b, zt + 14), center=(0, 0, 0), breaks=[(g.hole_top / 2 + 170, g.R_pin - g.d_pin / 2 - 150)], lv=(1, 2, 1, 2), extra=(0, 0, 60, 0),
         draw=corte, title="CORTE A-A (radial por el agujero 1, con rotura)", hs=0.5, w=1.2, mins=0.5, maxs=0.5, auto=False)
    p.detail("det_c", "corte", (g.hole_top / 2 + 10, 0, zt - tt / 2), 38, "B", lv=(1, 2, 1, 1), title="DETALLE B: AGUJERO CENTRAL Y REBAJE DE LA TAPA", maxs=2.0,
             auto=dict(text={round(tt - g.cb_t, 1): f"({f(tt - g.cb_t)})"}))
    p.ra_in("det_c", "Ra 6,3", [(g.hole_top / 2 + 22, 0, zt - g.cb_t), (g.hole_top / 2 + 12, 0, zt - g.cb_t), (g.cb_D / 2 + 12, 0, zt), (g.cb_D / 2 + 20, 0, zt)], (0, 0, 1))
    _tabla_agujeros(ctx, p, "vista desde la cara superior")
    rc_ = ranuras_cierre(ctx)
    RG_ = (((getattr(g, "bx", None) or {}).get("mesa") or {}).get("soldaduras") or {}).get("ranuras") or {}
    rtx_ = (f"{fm(RG_['ancho'], 0)} × {fm(RG_['L'], 0)} con extremos semicirculares, relleno completo {fm(RG_['relleno'], 0)}, separación entre centros ≥ {fm(2 * RG_['L'], 0)} (AISC 360-22 §J2.3b)" if RG_ else "22 × 80 a paso 250")
    if jj and RG_:
        add_prep(p, "det_j18", wd(ctx, jj[0]))
    p.table_block(f"RANURAS DE CIERRE {jj[0] if jj else ''} ({rtx_}; eje de la ranura sobre el eje del alma o nervio)", [("Elemento", 34, "L"), ("Ubicación", 70, "L"), ("Ángulos", 46, "L"), ("Cant", 14, "R")],
                  [[a, b_, c_, str(n_)] for a, b_, c_, n_ in rc_] + [["TOTAL", "", "", str(sum(r_[3] for r_ in rc_))]], bold_rows=(len(rc_),))
    p.tables(jj + ([jP["id"]] if jP else []))
    U_ = (D.get("pasadores_empuje") or {}).get("union")
    p.notes([f"Plancha ENTERA de una pieza Ø{f(2 * g.Rt)} × {f(tt)} (TT300-BX rev. 7c, decisión del mandante 19-11-2026): sin anillo de pasadores, sin empalmes CJP de segmentos y sin unión soldada plancha–anillo. "
             f"Compra: plancha de {f(tt)} mm de AL MENOS {f(2 * g.Rt)} × {f(2 * g.Rt)} (ASTM A572 Gr. 50, Z35, UT ASTM A578 nivel B).",
             f"Contorno Ø{f(2 * g.Rt)} ±1,5 por plasma/oxicorte (ISO 9013 clase 3). Agujero central Ø{f(g.hole_top)} y rebaje Ø{f(g.cb_D)} × {f(g.cb_t)} (apoyo de la tapa de inspección PIV-004): mecanizar en mandrinadora/fresadora; Ra 6,3.",
             f"{g.N_pin} agujeros Ø{f(g.d_pin)} H7 (+0,035/0) PASANTES en PCD Ø{f(2 * g.R_pin)} (tabla de agujeros; 1.er agujero a {fm(a0, 3)}° de +x, paso {fm(pitch, 3)}°): pretaladrar Ø80 en la plancha suelta "
             f"y MANDRINAR/ESCARIAR a Ø{f(g.d_pin)} H7 EN LÍNEA con la plancha inferior ({_cc(ctx, 'mesa_plancha_inf')}) con la mesa armada, soldada y aliviada (eje común; coaxialidad Ø0,05, CON-009). Ra 3,2; aristas rotas 1 × 45°.",
             (f"Borde EXTERIOR de cada agujero (cara superior): bisel 45° × {f(U_['S'])} para la PJP {jP['id'] if jP else 'J-P1'} del pasador soldado a ras (detalle en la lámina del pasador), mecanizado después del mandrinado."
              if U_ else "Pasadores montados m6/H7 según la lámina del pasador."),
             (f"Unión con almas y nervios SOLO por las soldaduras de ranura rellena {jj[0] if jj else 'J18'} (no CJP; las celdas quedan cerradas y no admiten filetes por debajo): ranuras {rtx_}, cortadas antes de montar la plancha; "
              f"{RG_.get('n_total', '')} ranuras en la tabla «RANURAS DE CIERRE» (en el tramo 1 de los nervios, en nervios alternados por la separación transversal ≥ 4·ancho); fondo sobre el canto del alma: {RG_.get('respaldo', '')}; no modeladas en 3D."
              if RG_ else f"Soldadura de cierre sobre almas y nervios por ranuras ({jj[0] if jj else 'J18'}): 22 × 80 a paso 250, posiciones en la tabla «RANURAS DE CIERRE» (PROPUESTA, confirmar); no modeladas en 3D."),
             "UT de recepción de la plancha ASTM A578 nivel B y Z35 (EN 10164) por el esfuerzo en espesor de los pasadores (antes: solo en el anillo).",
             "Distorsión: soldar la plancha superior en último lugar, con la mesa apoyada plana; verificar planitud 0,5. Paralelismo entre caras de la mesa: CON-009."],
            gd=[("pos", "Ø0,3", "A", "Agujeros de los pasadores: posición respecto del eje del agujero central (A); PCD y ángulos: cotas teóricamente exactas (en recuadro)"),
                ("flat", "0,5", None, "Planitud de la cara superior")])
    p.build()
    return p.h


def sheet_inf(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    z0, tbo = g.z0, g.tbo
    a0 = float(D["pasadores"][0])
    pitch = 360.0 / g.N_pin
    ri = g.Drb / 2 if g.rebaje else g.d_bush / 2
    rot_key(ctx, "mesa_plancha_inf", "pie", -a0)
    p = Pieza(ctx, ["mesa_plancha_inf"], f"MESA: PLANCHA INFERIOR ENTERA Ø{f(P['D_top'])} × {f(tbo)} CON {g.N_pin} AGUJEROS Ø{f(g.d_pin)} H7 (CARA DE APOYO DE LA INTERFAZ)", fmt="auto")
    on = ["pie"]
    jj = jids(ctx, "Barras de tope – plancha inferior")
    jP = ctx.weld_find("Pasadores de empuje")
    p.vs("planta", on, "bottom", lv=(1, 2, 1, 1), extra=(25, 0, 45, 10), draw=_planta(ctx, p, z0, on, a0, pitch, -1), title="VISTA INFERIOR (cara de apoyo; girada: 1.er agujero sobre la horizontal)", hatch=False, w=4.0, mins=0.1,
         auto=dict(hole_rmin=g.d_pin / 2 + 1, hole_pos=False, verts=False, only_extents=True, text={round(2 * g.Rt, 1): f"Ø{f(2 * g.Rt)} ±1,5"}))
    am_ = [pitch * (k_ + 0.5) for k_ in (20, 21, 19, 22, 18)]
    p.datum_in("planta", "surf", "A", at=[(ri * math.cos(math.radians(a_)), ri * math.sin(math.radians(a_)), z0) for a_ in am_],
               d=[(-math.cos(math.radians(a_)), -math.sin(math.radians(a_)), 0) for a_ in am_])
    p.gd_in("planta", "callout", "pos", "Ø0,3", "A", prefix=f"{g.N_pin} × Ø{f(g.d_pin)}")
    x_a, x_b = ri - 25, g.Rt + 25
    p.ra_in("corte", "Ra 3,2", [(ri + 90, 0, z0), (g.R_pin - g.d_pin / 2 - 60, 0, z0)], (0, 0, -1))
    p.gd_in("corte", "surf", "flat", "0,20", None, at=[(ri + 120, 0, z0), (g.R_pin - g.d_pin / 2 - 100, 0, z0)], d=(0, 0, -1))

    def corte(V, p):
        V.dimv((g.Rt, 0, z0), (g.Rt, 0, z0 + tbo), "right", 0, on=on, text=f"{f(tbo)} (t_bot)")
        V.dimh((g.R_pin - g.d_pin / 2, 0, z0 + tbo), (g.R_pin + g.d_pin / 2, 0, z0 + tbo), "top", 0, on=on, text=f"Ø{f(g.d_pin)} H7 (+0,035/0)")
        V.dimh((g.R_pin, 0, z0), (g.Rt, 0, z0), "bottom", 0, on=on, text=f"{fm(g.Rt - g.R_pin, 0)}", virt_a=g.d_pin / 2)
    p.vs("corte", on, "front", cut=CUT_Y, win=(x_a, z0 - 6, x_b, z0 + tbo + 14), center=(0, 0, 0), breaks=[(ri + 150, g.R_pin - g.d_pin / 2 - 150)], lv=(1, 3, 1, 2), extra=(0, 0, 60, 0), draw=corte,
         title="CORTE A-A (radial por el agujero 1, con rotura)", hs=0.5, w=1.2, mins=0.5, maxs=0.5, auto=False)
    p.detail("det_c", "corte", (ri + 6, 0, z0 + tbo / 2), 30, "B", lv=(1, 2, 1, 1), title="DETALLE B: BORDE DEL AGUJERO CENTRAL (REBAJE DEL COLLAR)", maxs=5.0)
    _tabla_agujeros(ctx, p, "posiciones en el sistema de la mesa; la vista inferior las muestra en espejo")
    p.tables(jj + ([jP["id"]] if jP else []))
    U_ = (D.get("pasadores_empuje") or {}).get("union")
    p.notes([f"Plancha ENTERA de una pieza Ø{f(2 * g.Rt)} × {f(tbo)} (TT300-BX rev. 7c, decisión del mandante 19-11-2026): sin anillo de pasadores, sin empalmes CJP de segmentos y sin unión soldada plancha–anillo. "
             f"Compra: plancha de {f(tbo)} mm de AL MENOS {f(2 * g.Rt)} × {f(2 * g.Rt)} con tolerancia de espesor solo positiva (ASTM A6/A6M), ASTM A572 Gr. 50, Z35, UT ASTM A578 nivel B.",
             f"Contorno Ø{f(2 * g.Rt)} ±1,5 por plasma/oxicorte (ISO 9013 clase 3). Agujero central Ø{f(2 * ri)} " + (f"PASANTE por el rebaje del collar (Ø{f(g.D_boss)} del collar + 2 × {fm(g.c_boss_r, 0)} mm); holgura radial {fm(g.c_boss_r, 0)} mm, axial {fm(g.c_boss_a, 0)} mm." if g.rebaje else "mandrinado para el buje."),
             f"{g.N_pin} agujeros Ø{f(g.d_pin)} H7 (+0,035/0) PASANTES en PCD Ø{f(2 * g.R_pin)} (tabla de agujeros): pretaladrar Ø80 y MANDRINAR/ESCARIAR a Ø{f(g.d_pin)} H7 EN LÍNEA con la plancha superior ({_cc(ctx, 'mesa_plancha_sup')}) "
             f"con la mesa armada, soldada y aliviada (eje común; coaxialidad Ø0,05, CON-009). Ra 3,2; aristas rotas 1 × 45°" + (f"; borde EXTERIOR de cada agujero (cara inferior): bisel 45° × {f(U_['S'])} para la PJP {jP['id'] if jP else 'J-P1'} del pasador soldado a ras, mecanizado después del planeado final." if U_ else "."),
             f"Cara inferior planeada después de soldar la mesa y aliviar tensiones (remoción mínima, espesor terminado ≥ {f(tbo)}): planitud 0,20, Ra 3,2 (apoyo de la interfaz, {g.interfaz_nombre}).",
             "UT de recepción de la plancha ASTM A578 nivel B y Z35 (EN 10164) por el esfuerzo en espesor de los pasadores (antes: solo en el anillo)."]
            + (__import__("bx_notas").notas_mesa_inf(ctx) if g.opt == 4 else []) + (__import__("bx_notas").notas_anillo_inf(ctx) if g.opt == 4 else []),
            gd=[("pos", "Ø0,3", "A", "Agujeros de los pasadores: posición respecto del eje del agujero central (A); PCD y ángulos: cotas teóricamente exactas (en recuadro)"),
                ("flat", "0,20", None, "Planitud de la cara inferior (antes de montar la interfaz); paralelismo entre caras de la mesa: CON-009")])
    p.build()
    return p.h
