"""TT300-BX rev. 7c (decisión del mandante 19-11-2026): láminas de las planchas ENTERAS de la mesa (una pieza Ø D_top por nivel con los N_pin
agujeros H7 de los pasadores de empuje). Reemplazan a MES-001 / MES-003 del juego con disco + anillo; MES-002 / MES-004 (anillos) no existen.
Solo se usan con el bloque bx.mesa.plancha_entera del JSON (g.mesa_entera); sin él, las láminas de cad/pie_b.py no cambian."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *
from hojas_base import ranuras_cierre
from pie_a import wd
from soldadura_det import add_prep
import modelo3d_tt300c as M3


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


def _planta(ctx, p, z, on, a0, pitch, sg, extra_draw=None, r_in=None):
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
        p.cut_mark("planta", "A", ((r_in or g.hole_top / 2) - 25 if sg > 0 else g.Drb / 2 - 25, 0, z), (g.Rt + 25, 0, z), 90 * sg)
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
    DC = M3.disco_central(g) if ctx.m.get("mesa_disco") else None      # rev. 9e: el centro mecanizado pasa al disco MES-016
    rh_ = DC["plancha"]["agujero"] / 2 if DC else g.hole_top / 2
    p = Pieza(ctx, ["mesa_plancha_sup"], f"MESA: PLANCHA SUPERIOR ENTERA Ø{f(P['D_top'])} × {f(tt)} CON {g.N_pin} AGUJEROS Ø{f(g.d_pin)} H7", fmt="auto")
    on = ["pse"]
    jj = jids(ctx, "Cierre de la plancha")
    jP = ctx.weld_find("Pasadores de empuje")
    jD = jids(ctx, "Disco central torneado", "Aro de respaldo de J19") if DC else []

    def m8(V, p):
        hx = (g.insp_pcd / 2 * math.cos(math.radians(330 - a0)), g.insp_pcd / 2 * math.sin(math.radians(330 - a0)), zt - g.cb_t)
        V.note_hole(hx, g.insp_drill / 2, -40, "6 × M8-6H", ext=(g.R_pin - g.d_pin - g.insp_pcd / 2) * V.scale, on=on,
                    lines=[f"6 × M{fm(g.insp_d, 0)}-6H pasante (taladro Ø{fm(g.insp_drill, 1)})", f"en el fondo del rebaje, PCD Ø{fm(g.insp_pcd, 0)}, 30° + 60°·k desde +x"])
    p.vs("planta", on, "top", lv=(1, 2, 1, 1), extra=(25, 0, 45, 10), draw=_planta(ctx, p, zt, on, a0, pitch, 1, None if DC else m8, r_in=rh_), title="PLANTA (girada: 1.er agujero sobre la horizontal)", hatch=False, w=4.0, mins=0.1,
         auto=dict(fits={} if DC else {round(g.hole_top, 1): "H12", round(g.cb_D, 1): "H12"}, hole_rmin=g.d_pin / 2 + 1, hole_pos=False, verts=False, only_extents=True,
                   text={**{round(2 * g.Rt, 1): f"Ø{f(2 * g.Rt)} ±1,5"}, **({round(2 * rh_, 1): f"Ø{fm(2 * rh_, 0)} ±1,5 (corte térmico)"} if DC else {})}))
    # datum A: agujero central (su eje = eje de la mesa), en el detalle B (en la planta no hay lugar libre junto al rebaje)
    p.datum_in("det_c", "surf", "A", at=[(rh_, 0, zt - tt + 4), (rh_, 0, zt - tt + 7)], d=(-1, 0, 0))
    p.gd_in("planta", "callout", "pos", "Ø0,3", "A", prefix=f"{g.N_pin} × Ø{f(g.d_pin)}")
    x_a, x_b = rh_ - 25, g.Rt + 25

    def corte(V, p):
        V.dimv((g.Rt, 0, zt - tt), (g.Rt, 0, zt), "right", 0, on=on, text=f"{f(tt)} (t_top)")
        V.dimh((g.R_pin - g.d_pin / 2, 0, zt), (g.R_pin + g.d_pin / 2, 0, zt), "top", 0, on=on, text=f"Ø{f(g.d_pin)} H7 (+0,035/0)")
        V.dimh((g.R_pin, 0, zt - tt), (g.Rt, 0, zt - tt), "bottom", 0, on=on, text=f"{fm(g.Rt - g.R_pin, 0)}", virt_a=g.d_pin / 2)
        if jj:                           # ranura de cierre J18 sobre el alma exterior (posiciones en la tabla «RANURAS DE CIERRE»; preparación en GEN-007)
            ra_ = max(r_ for r_ in D["almas"] if r_ < g.R_pin - g.d_pin / 2)
            w_out(p, jj[0], V, (ra_, 0, zt), "top", dy=0)
    p.ra_in("corte", "Ra 6,3", [(rh_ + 150, 0, zt), (g.R_pin - g.d_pin / 2 - 60, 0, zt)], (0, 0, 1))
    p.gd_in("corte", "surf", "flat", "0,5", None, at=[(rh_ + 100, 0, zt), (g.R_pin - g.d_pin / 2 - 100, 0, zt)], d=(0, 0, 1))
    p.vs("corte", on, "front", cut=CUT_Y, win=(x_a, zt - tt - 6, x_b, zt + 14), center=(0, 0, 0), breaks=[(rh_ + 170, g.R_pin - g.d_pin / 2 - 150)] if (g.R_pin - g.d_pin / 2 - 150) - (rh_ + 170) > 60 else None, lv=(1, 2, 1, 2), extra=(0, 0, 60, 0),
         draw=corte, title="CORTE A-A (radial por el agujero 1, con rotura)", hs=0.5, w=1.2, mins=0.5, maxs=0.5, auto=False)
    if DC:                               # rev. 9e: agujero de corte térmico a escuadra; la junta J19 (bisel en el disco) se detalla en MES-016
        p.detail("det_c", "corte", (rh_ + 10, 0, zt - tt / 2), 38, "B", lv=(1, 2, 1, 1), title=f"DETALLE B: BORDE DEL AGUJERO CENTRAL Ø{fm(2 * rh_, 0)} (CORTE TÉRMICO A ESCUADRA; JUNTA J19 CON EL DISCO {_cc(ctx, 'mesa_disco')})", maxs=2.0, mins=0.1)
    else:
        p.detail("det_c", "corte", (g.hole_top / 2 + 10, 0, zt - tt / 2), 38, "B", lv=(1, 2, 1, 1), title="DETALLE B: AGUJERO CENTRAL Y REBAJE DE LA TAPA", maxs=2.0,
                 **({"mins": 0.1} if ctx.m.get("mesa_respaldo") else {}),
                 auto=dict(text={round(tt - g.cb_t, 1): f"({f(tt - g.cb_t)})"}))
        p.ra_in("det_c", "Ra 6,3", [(g.hole_top / 2 + 22, 0, zt - g.cb_t), (g.hole_top / 2 + 12, 0, zt - g.cb_t), (g.cb_D / 2 + 12, 0, zt), (g.cb_D / 2 + 20, 0, zt)], (0, 0, 1))
    _tabla_agujeros(ctx, p, "vista desde la cara superior")
    rc_ = ranuras_cierre(ctx)
    RG_ = (((getattr(g, "bx", None) or {}).get("mesa") or {}).get("soldaduras") or {}).get("ranuras") or {}
    rtx_ = (f"{fm(RG_['ancho'], 0)} × {fm(RG_['L'], 0)} con extremos semicirculares, relleno completo {fm(RG_['relleno'], 0)}, separación entre centros ≥ {fm(2 * RG_['L'], 0)} (AISC 360-22 §J2.3b)" if RG_ else "22 × 80 a paso 250")
    if jj and RG_:
        add_prep(p, "det_j18", wd(ctx, jj[0]))
    if DC:                               # rev. 9e: las ranuras que quedan dentro del disco se cortan en el disco (tabla de MES-016)
        rc_ = [r_ for r_ in rc_ if not _en_disco(DC, r_[0])]
    p.table_block(f"RANURAS DE CIERRE {jj[0] if jj else ''} ({rtx_}; eje de la ranura sobre el eje del alma o nervio)" + (f"; las del alma A1 y del tramo 1 están en el disco {_cc(ctx, 'mesa_disco')}" if DC else ""), [("Elemento", 34, "L"), ("Ubicación", 70, "L"), ("Ángulos", 46, "L"), ("Cant", 14, "R")],
                  [[a, b_, c_, str(n_)] for a, b_, c_, n_ in rc_] + [["TOTAL" + (" EN LA PLANCHA" if DC else ""), "", "", str(sum(r_[3] for r_ in rc_))]], bold_rows=(len(rc_),))
    p.tables(jj + jids(ctx, "Tiras de respaldo de J18") + jD + ([jP["id"]] if jP else []))
    U_ = (D.get("pasadores_empuje") or {}).get("union")
    p.notes([f"Plancha ENTERA de una pieza Ø{f(2 * g.Rt)} × {f(tt)} (TT300-BX rev. 7c, decisión del mandante 19-11-2026): sin anillo de pasadores, sin empalmes CJP de segmentos y sin unión soldada plancha–anillo. "
             f"Compra: plancha de {f(tt)} mm de AL MENOS {f(2 * g.Rt)} × {f(2 * g.Rt)} (ASTM A572 Gr. 50, Z35, UT ASTM A578 nivel B).",
             (f"Contorno Ø{f(2 * g.Rt)} ±1,5 y agujero central Ø{fm(2 * rh_, 0)} ±1,5 por plasma/oxicorte (ISO 9013 clase 3), canto del agujero A ESCUADRA y sin mecanizar (rev. 9e, pedido del mandante 23-11-2026): "
              f"el agujero Ø{f(g.hole_top)} de J17b, el rebaje Ø{f(g.cb_D)} × {f(g.cb_t)} y las roscas de la tapa de inspección van en el disco central torneado {_cc(ctx, 'mesa_disco')}, soldado a esta plancha con la CJP {', '.join(jids(ctx, 'Disco central torneado')) or 'J19'} "
              f"(B-U4a: bisel {fm(DC['junta']['alfa'], 0)}° en el disco, R = {fm(DC['junta']['R'], 0)}, aro de respaldo {_cc(ctx, 'mesa_aro_j19')} {fm(DC['aro']['t'], 0)} × {fm(DC['aro']['b'], 0)} punteado por debajo con {', '.join(jids(ctx, 'Aro de respaldo de J19')) or 'J19r'} antes de cerrar la mesa). "
              f"Esmerilar el canto (metal brillante 25 mm). El recorte central sirve de tocho del disco (misma colada)." if DC else
              f"Contorno Ø{f(2 * g.Rt)} ±1,5 por plasma/oxicorte (ISO 9013 clase 3). Agujero central Ø{f(g.hole_top)} y rebaje Ø{f(g.cb_D)} × {f(g.cb_t)} (apoyo de la tapa de inspección PIV-004): mecanizar en mandrinadora/fresadora; Ra 6,3."),
             f"{g.N_pin} agujeros Ø{f(g.d_pin)} H7 (+0,035/0) PASANTES en PCD Ø{f(2 * g.R_pin)} (tabla de agujeros; 1.er agujero a {fm(a0, 3)}° de +x, paso {fm(pitch, 3)}°): pretaladrar Ø80 en la plancha suelta "
             f"y MANDRINAR/ESCARIAR a Ø{f(g.d_pin)} H7 EN LÍNEA con la plancha inferior ({_cc(ctx, 'mesa_plancha_inf')}) con la mesa armada, soldada y aliviada (eje común; coaxialidad Ø0,05, CON-009). Ra 3,2; aristas rotas 1 × 45°.",
             (f"Borde EXTERIOR de cada agujero (cara superior): bisel 45° × {f(U_['S'])} para la PJP {jP['id'] if jP else 'J-P1'} del pasador soldado a ras (detalle en la lámina del pasador), mecanizado después del mandrinado."
              if U_ else "Pasadores montados m6/H7 según la lámina del pasador."),
             (f"Unión con almas y nervios SOLO por las soldaduras de ranura rellena {jj[0] if jj else 'J18'} con respaldo permanente (no CJP; las celdas quedan cerradas y no admiten filetes por debajo): ranuras {rtx_}, cortadas antes de montar la plancha; "
              f"{RG_.get('n_total', '')} ranuras en la tabla «RANURAS DE CIERRE» (en el tramo 1 de los nervios, en nervios alternados por la separación transversal ≥ 4·ancho; su extremo interior apoya sobre el cubo); no modeladas en 3D."
              if RG_ else f"Soldadura de cierre sobre almas y nervios por ranuras ({jj[0] if jj else 'J18'}): 22 × 80 a paso 250, posiciones en la tabla «RANURAS DE CIERRE» (PROPUESTA, confirmar); no modeladas en 3D."),
             *([_nota_tiras(ctx, RG_["tiras"])] if (RG_ and RG_.get("tiras") and ctx.m.get("mesa_respaldo")) else []),
             "UT de recepción de la plancha ASTM A578 nivel B y Z35 (EN 10164) por el esfuerzo en espesor de los pasadores (antes: solo en el anillo).",
             "Distorsión: soldar la plancha superior en último lugar, con la mesa apoyada plana; verificar planitud 0,5. Paralelismo entre caras de la mesa: CON-009."
             + (f" Planitud 0,5 en toda la cara superior con el disco {_cc(ctx, 'mesa_disco')} soldado y J19 esmerilada a ras." if DC else "")],
            gd=[("pos", "Ø0,3", "A", "Agujeros de los pasadores: posición respecto del eje del agujero central (A)" + (f"; con la mesa armada, A = eje del agujero Ø{f(g.hole_top)} H12 del disco {_cc(ctx, 'mesa_disco')}, centrado en el cubo" if DC else "") + "; PCD y ángulos: cotas teóricamente exactas (en recuadro)"),
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


def _en_disco(DC, elemento):
    """True si las ranuras J18 del elemento («Alma A1», «Nervios, tramo 1», …) quedan dentro del disco central (rev. 9e)."""
    e_ = elemento.replace("Alma", "alma").replace("Nervios", "nervios")
    return any(q["que"].endswith(e_) for q in DC.get("ranuras_en_disco") or [])


def _nota_tiras(ctx, T):
    """TT300-BX rev. 9d: tiras de respaldo permanentes de J18 (pieza de esta lámina; núcleo BX bx.mesa.soldaduras.ranuras.tiras)."""
    cR = _cc(ctx, "mesa_respaldo")
    PT = T["punteo"]
    return (f"Respaldo permanente de {', '.join(jids(ctx, 'Cierre de la plancha')) or 'J18'}: {T['n']} tiras {cR} de {fm(T['b'], 0)} × {fm(T['t'], 0)} ({T['material']}; {fm(T['masa_total'], 1)} kg en total), dos por ranura, "
            f"una a cada lado del canto del alma o nervio y a ras de él (± 0,5), largo = L + 2 × {fm(T['run'], 0)} (recortadas a 1 mm del cubo y fuera de las tiras del alma; 8 geometrías: rectas en los nervios y arcos en las almas, despiece CON-002). "
            f"Secuencia: con la mesa abierta, puntear cada tira por debajo contra el alma o nervio ({', '.join(jids(ctx, 'Tiras de respaldo de J18')) or 'J18r'}: z{fm(PT['z'], 0)}, {PT['n']} tramos de {fm(PT['l'], 0)} mm) ANTES de montar la plancha superior; "
            f"las tiras de las almas pasan por el destijer superior de {fm(T['destijer_superior_almas'], 0)} × {fm(T['destijer_superior_almas'], 0)} de los nervios; quedan dentro de la mesa.")


def _slot_pts(r0, r1, w, ang, z, n=10):
    """Contorno de una ranura recta (extremos semicirculares) sobre el eje radial a ángulo ang, de r0 a r1 (extremos), ancho w."""
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    h = w / 2
    pts = []
    for k in range(n + 1):                                   # extremo exterior (centro r1 − h)
        t = -math.pi / 2 + math.pi * k / n
        pts.append((r1 - h + h * math.cos(t), h * math.sin(t)))
    for k in range(n + 1):                                   # extremo interior (centro r0 + h)
        t = math.pi / 2 + math.pi * k / n
        pts.append((r0 + h + h * math.cos(t), h * math.sin(t)))
    return [(u * ca - v * sa, u * sa + v * ca, z) for u, v in pts]


def _slot_arc_pts(R, L, w, ang, z, n=24):
    """Contorno de una ranura curva sobre el eje R (largo L medido en el eje, extremos semicirculares) centrada en el ángulo ang."""
    h = w / 2
    b = (L - w) / R / 2                                      # semiángulo del tramo recto (en el eje)
    a0 = math.radians(ang)
    pts = []
    for k in range(n + 1):
        t = a0 - b + 2 * b * k / n
        pts.append(((R + h) * math.cos(t), (R + h) * math.sin(t)))
    c1 = (R * math.cos(a0 + b), R * math.sin(a0 + b))
    for k in range(1, n // 2):
        t = a0 + b + math.pi * k / (n // 2)
        pts.append((c1[0] + h * math.cos(t), c1[1] + h * math.sin(t)))
    for k in range(n + 1):
        t = a0 + b - 2 * b * k / n
        pts.append(((R - h) * math.cos(t), (R - h) * math.sin(t)))
    c0 = (R * math.cos(a0 - b), R * math.sin(a0 - b))
    for k in range(1, n // 2):
        t = a0 - b + math.pi + math.pi * k / (n // 2)
        pts.append((c0[0] + h * math.cos(t), c0[1] + h * math.sin(t)))
    return [(x, y, z) for x, y in pts]


def sheet_disco(ctx):
    """TT300-BX rev. 9e (pedido del mandante 23-11-2026): plano de torno del disco central de la plancha superior (MES-016) con el agujero Ø D_piv + 80 de
    J17b, el rebaje de la tapa de inspección, las roscas M8, el bisel de la CJP J19 y sus ranuras J18; y el aro de respaldo de J19 (MES-017).
    Todas las medidas salen de bx.mesa.soldaduras.disco_central (núcleo BX)."""
    g, P, D = ctx.g, ctx.P, ctx.D
    DC = M3.disco_central(g)
    zt = g.z0 + g.hd
    t, Rb, Rs = float(DC["t"]), float(DC["R_inf"]), float(DC["R_sup"])
    rH, rC, hC = float(DC["agujero"]["d"]) / 2, float(DC["rebaje"]["d"]) / 2, float(DC["rebaje"]["prof"])
    J, A, T = DC["junta"], DC["aro"], DC["torneado"]
    RG = ((((g.bx or {}).get("mesa") or {}).get("soldaduras") or {}).get("ranuras")) or {}
    cD, cA, cS = _cc(ctx, "mesa_disco"), _cc(ctx, "mesa_aro_j19"), _cc(ctx, "mesa_plancha_sup")
    keys = ["mesa_disco"] + (["mesa_aro_j19"] if ctx.m.get("mesa_aro_j19") else [])
    p = Pieza(ctx, keys, f"MESA: DISCO CENTRAL TORNEADO Ø{fm(2 * Rb, 0)} × {fm(t, 0)} Y ARO DE RESPALDO DE J19", fmt="auto")
    s = p.s
    on = ["mesa_disco"]
    j19, j19r = jids(ctx, "Disco central torneado"), jids(ctx, "Aro de respaldo de J19")
    jB, jj = jids(ctx, "Cubo – plancha superior, en el disco"), jids(ctx, "Cierre de la plancha")
    w_, L_ = float(RG.get("ancho", 30)), float(RG.get("L", 125))
    alm = [a for a in RG.get("almas", []) if a["r"] + w_ / 2 < Rs]
    trs = [q for q in RG.get("tramos", []) if q["centros"][-1] + q["L"] / 2 < Rs]
    ang_n = [float(a) for a in D["nervios"]]

    def planta(V, p):
        c3 = (0, 0, zt)
        s.centerlines(V.P(c3), Rb * V.scale + 6, 8)
        for a in alm:                                   # ranuras J18 del alma (curvas, sobre el eje del alma)
            for k in range(int(a["n"])):
                s.pline([V.P(q) for q in _slot_arc_pts(a["r"], a["L"], w_, a["a0_deg"] + a["paso_deg"] * k, zt)], "VIS", closed=True)
        for q in trs:                                   # ranuras J18 de los nervios (rectas, en nervios alternados)
            for j in range(0, len(ang_n), int(q["cada_k_nervios"])):
                for c_ in q["centros"]:
                    s.pline([V.P(x) for x in _slot_pts(c_ - q["L"] / 2, c_ + q["L"] / 2, w_, ang_n[j], zt)], "VIS", closed=True)
        # marca de referencia de 0° (eje x de la mesa = nervio n.° 1), grabada en la cara superior junto al borde
        s.line(V.P((Rs - 14, 0, zt)), V.P((Rs - 2, 0, zt)), "VIS")
        s.text("0° (+x de la mesa, nervio 1)", (V.P((Rs - 2, 0, zt))[0] + 3, V.P((Rs, 0, zt))[1] + 4), T_S, "BOTTOM_LEFT")
        V.dim_dia((0, 0, zt - t), Rb, 138, on=on, text=f"Ø{fm(2 * Rb, 0)} ±0,5 (abajo)", ext=16)
        V.dim_dia(c3, Rs, 108, on=on, text=f"Ø{fm(2 * Rs, 0)} (arriba, ref.)", ext=(Rb - Rs) * V.scale + 16)
        V.dim_dia(c3, rC, 166, on=on, text=f"Ø{fm(2 * rC, 0)} H12", ext=(Rb - rC) * V.scale + 16)
        V.dim_dia(c3, rH, 196, on=on, text=f"Ø{fm(2 * rH, 0)} H12", ext=(Rb - rH) * V.scale + 16)
        hx = (g.insp_pcd / 2 * math.cos(math.radians(330)), g.insp_pcd / 2 * math.sin(math.radians(330)), zt - hC)
        V.note_hole(hx, g.insp_drill / 2, -40, "6 × M8-6H", ext=(Rb - g.insp_pcd / 2) * V.scale + 10, on=on,
                    lines=[f"6 × M{fm(g.insp_d, 0)}-6H pasante (taladro Ø{fm(g.insp_drill, 1)}) en el fondo del rebaje", f"PCD Ø{fm(g.insp_pcd, 0)}, 30° + 60°·k; DESPUÉS de soldar y aliviar"])
        p.cut_mark("planta", "A", (-Rb - 16, 0, zt), (Rb + 16, 0, zt), 90)
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(50, 20, 60, 20), draw=planta, title="PLANTA (cara superior; ranuras J18 cortadas a plasma antes de tornear)", hatch=False, w=4.0, auto=False, mins=0.1)

    def corte(V, p):
        V.dimh((0, 0, zt - t), (Rb, 0, zt - t), "bottom", 0, on=on, text=f"Ø{fm(2 * Rb, 0)} ±0,5", virt_a=rH)
        V.dimh((0, 0, zt), (Rs, 0, zt), "top", 1, on=on, text=f"Ø{fm(2 * Rs, 0)} (ref.)", virt_a=rH)
        V.dimh((0, 0, zt), (rC, 0, zt), "top", 0, on=on, text=f"Ø{fm(2 * rC, 0)} H12 (+0,46/0)", virt_a=rH)
        V.dimh((0, 0, zt - t), (rH, 0, zt - t), "bottom", 1, on=on, text=f"Ø{fm(2 * rH, 0)} H12 (+0,46/0)", virt_a=rH)
        V.dimv((Rb, 0, zt - t), (Rs, 0, zt), "right", 0, on=on, text=f"{fm(t, 0)}")
        V.note_pt(((Rb + Rs) / 2, 0, zt - t / 2), (-70, 16), f"bisel {fm(J['alfa'], 0)}° +5°/0, talón {fm(J['f'], 0)} (detalle {j19[0] if j19 else 'J19'})", on=on, dot=True)
        s.line(V.P(0, 0, zt - t - 6), V.P(0, 0, zt + 6), "EJE")
    p.ra_in("corte", "Ra 3,2", [(rC + 30, 0, zt), (Rs - 30, 0, zt), (rC + 90, 0, zt)], (0, 0, 1))
    p.vs("corte", on, "front", cut=CUT_Y, win=(-8, zt - t - 6, Rb + 12, zt + 8), center=(0, 0, 0), lv=(2, 2, 2, 2), extra=(0, 0, 40, 0), draw=corte,
         title="CORTE A-A (semicorte radial; las ranuras J18 no se muestran)", hs=0.5, w=1.4, mins=0.2, auto=False)

    def detB(V, p):
        pass
    p.detail("det_b", "corte", (rC - 4, 0, zt - t / 2), 26, "B", lv=(1, 2, 2, 1), title=f"DETALLE B: AGUJERO Ø{fm(2 * rH, 0)} Y REBAJE Ø{fm(2 * rC, 0)} × {fm(hC, 0)}", draw=detB, mins=0.1, maxs=3.0, auto=dict(text={round(t - hC, 1): f"({fm(t - hC, 0)})", round(hC, 1): f"{fm(hC, 0)} +0,2/0"}))
    p.datum_in("det_b", "surf", "A", at=[(rC + 8, 0, zt), (rC + 14, 0, zt), (rC + 18, 0, zt)], d=(0, 0, 1))
    p.gd_in("det_b", "surf", "flat", "0,3", None, at=[(rC + 12, 0, zt), (rC + 4, 0, zt), (rC + 18, 0, zt)], d=(0, 0, 1))
    p.gd_in("det_b", "surf", "par", "0,1", "A", at=[(rH + 6, 0, zt - hC), (rH + 12, 0, zt - hC), (rH + 16, 0, zt - hC)], d=(0, 0, 1))
    if j19:
        add_prep(p, "det_j19", wd(ctx, j19[0]), title=f"DETALLE {j19[0]}: CJP DISCO–PLANCHA B-U4a (BISEL {fm(J['alfa'], 0)}° TORNEADO EN EL DISCO, R = {fm(J['R'], 0)}, f = {fm(J['f'], 0)}, ARO {fm(A['t'], 0)} × {fm(A['b'], 0)})")
    if ctx.m.get("mesa_aro_j19"):
        def aro(V, p):
            c3 = (0, 0, zt - t - A["t"])
            s.centerlines(V.P(c3), A["R_ext"] * V.scale + 5, 4)
            V.dim_dia(c3, A["R_ext"], 35, on=["mesa_aro_j19"], text=f"Ø{fm(A['D_ext'], 0)} ±1,5", ext=14)
            V.dim_dia(c3, A["R_int"], 215, on=["mesa_aro_j19"], text=f"Ø{fm(A['D_int'], 0)} ±1,5", ext=A["b"] * V.scale + 14)
            if j19r:                     # punteo del aro bajo la plancha (canto exterior)
                w_out(p, j19r[0], V, (A["R_ext"] * math.cos(math.radians(-30)), A["R_ext"] * math.sin(math.radians(-30)), zt - t), "right", dy=-10)
        p.vs("aro", ["mesa_aro_j19"], "top", lv=(1, 1, 1, 1), extra=(0, 0, 0, 0), draw=aro, title=f"{cA}: ARO DE RESPALDO DE J19 (plancha de {fm(A['t'], 0)}, una pieza)", hatch=False, w=0.8, auto=False, mins=0.05)
    rows = []
    for a in alm:
        rows.append([a["elemento"], f"curvas sobre el eje R{fm(a['r'], 0)}; L = {fm(a['L'], 0)} en el eje", f"{fm(a['a0_deg'], 3)}° + {fm(a['paso_deg'], 3)}°·k", str(a["n"])])
    for q in trs:
        k_ = int(q["cada_k_nervios"])
        rows.append([q["elemento"], f"rectas sobre el eje del nervio, centro a R{fm(q['centros'][0], 1)} (R{fm(q['centros'][0] - q['L'] / 2, 1)}–R{fm(q['centros'][-1] + q['L'] / 2, 1)}); L = {fm(q['L'], 0)}",
                     ("ángulos de los nervios" if k_ == 1 else f"nervios alternados: 1 de cada {k_} (n.° 1, {1 + k_}, …: 0° + {fm(360.0 * k_ / len(ang_n), 3)}°·k)"), str(int(q["n"]))])
    p.table_block(f"RANURAS J18 DEL DISCO ({fm(w_, 0)} × L, extremos semicirculares R{fm(w_ / 2, 0)}; ángulos desde la marca 0° = +x de la mesa)", [("Elemento", 30, "L"), ("Ubicación", 74, "L"), ("Ángulos", 48, "L"), ("Cant", 12, "R")],
                  rows + [["TOTAL", "", "", str(sum(int(r[3]) for r in rows))]], bold_rows=(len(rows),))
    tol = [["Ø exterior en la cara inferior (raíz de J19)", f"Ø{fm(2 * Rb, 0)}", "±0,5", "Ra 6,3", f"abertura de raíz R = {fm(J['R'], 0)} con el agujero Ø{fm(DC['plancha']['agujero'], 0)} ±1,5 de la plancha"],
           ["Bisel de J19 (cara cónica)", f"{fm(J['alfa'], 0)}°, f = {fm(J['f'], 0)}", "+5°/0; f +1/0", "Ra 6,3", f"Ø{fm(2 * Rs, 0)} en la cara superior (referencia)"],
           ["Agujero de J17b", f"Ø{fm(2 * rH, 0)}", "H12 (+0,46/0)", "Ra 3,2", f"tapa retenedora Ø{fm(g.cap_D, 0)} adentro (holgura radial con el filete: 3 mm)"],
           ["Rebaje de la tapa de inspección", f"Ø{fm(2 * rC, 0)} × {fm(hC, 0)}", "H12 (+0,46/0); prof. +0,2/0", "Ra 3,2", f"tapa Ø{fm(2 * rC - 2, 0)} × {fm(hC, 0)}: 1 mm por lado; fondo ∥ A 0,1"],
           ["Cara superior (A)", f"espesor {fm(t, 0)}", "limpieza ≤ 0,5", "Ra 3,2", "planitud 0,3 (referencia de la profundidad del rebaje)"],
           ["Cara inferior", "—", "de laminación", "—", "apoya en el cubo, almas, nervios y aro"],
           ["Roscas de la tapa de inspección", f"6 × M{fm(g.insp_d, 0)}-6H, PCD Ø{fm(g.insp_pcd, 0)}", "posición Ø0,3", "—", "taladrar y roscar DESPUÉS de soldar J17b y aliviar (plantilla en el rebaje)"]]
    p.table_block(f"TOLERANCIAS DE TORNEADO ({cD}; ISO 2768-m donde no se indica)", [("Elemento", 46, "L"), ("Nominal", 30, "L"), ("Tolerancia", 30, "L"), ("Ra", 12, "C"), ("Observación", 62, "L")], tol)
    p.tables(j19 + j19r + jB + jj)
    p.notes([f"Disco central de la plancha superior (TT300-BX rev. 9e, pedido del mandante 23-11-2026; POR DEFECTO, A CONFIRMAR POR EL MANDANTE): {DC['material']}, mismo material, espesor y colada que la plancha {cS}. "
             f"Tocho Ø{fm(DC['tocho']['d'], 0)} × {fm(t, 0)}: {DC['tocho']['nota']}.",
             f"Diámetro: {DC['motivo']}",
             f"Orden de fabricación: (1) cortar las {sum(int(r[3]) for r in rows)} ranuras J18 a plasma en el tocho (tabla; ±1,5) con la marca de 0° grabada; (2) TORNEAR en un montaje: cara superior (A), Ø{fm(2 * rH, 0)} H12, rebaje Ø{fm(2 * rC, 0)} H12 × {fm(hC, 0)}, "
             f"Ø{fm(2 * Rb, 0)} ±0,5 y bisel {fm(J['alfa'], 0)}° hasta la arista viva (f = {fm(J['f'], 0)}); (3) las 6 roscas M{fm(g.insp_d, 0)} se hacen al final, con la mesa soldada y aliviada.",
             f"Torneado completo sin sobremedida: {T['razon']}. Después de soldar: verificar el asiento de la tapa (Ø{fm(2 * rC, 0)} H12, profundidad {fm(hC, 0)} +0,2/0, fondo ∥ A 0,1); si queda fuera, refrentar el fondo en sitio.",
             f"Montaje y soldadura (secuencia del núcleo): " + " ".join(DC["secuencia"]),
             f"J19: {J['tipo']}; bisel en el disco, plancha a escuadra; R = {fm(J['R'], 0)}, f = {fm(J['f'], 0)}; {J['tolerancias']}; {J['terminacion']}; END {J['END']}; nivel {J['nivel']}. "
             f"Precalentamiento por la parte más gruesa ({fm(J['precalentamiento_t'], 0)} mm, AWS D1.1:2020 Tabla 5.8): ver la tabla de soldaduras.",
             f"Aro de respaldo {cA}: {fm(A['t'], 0)} × {fm(A['b'], 0)} (Ø{fm(A['D_ext'], 0)} / Ø{fm(A['D_int'], 0)}), {A['material']}; {A['fabricacion']}; margen bajo la raíz {fm(A['m_int'], 0)} (disco) y {fm(A['m_ext'], 0)} (plancha). "
             f"Los {DC['muesca']['n']} nervios del tramo {DC['muesca']['tramo']} llevan una muesca {fm(DC['muesca']['prof'], 0)} × {fm(DC['muesca']['r1'] - DC['muesca']['r0'], 0)} en el canto superior (R{fm(DC['muesca']['r0'], 0)}–R{fm(DC['muesca']['r1'], 0)}) por donde pasa el aro (MES-009).",
             f"Las ranuras J18 del disco ({sum(int(r[3]) for r in rows)}) son las mismas de la rev. 9d (geometría y FU sin cambio); la circunferencia de la junta J19 queda a {fm(DC['sep_ranuras'], 0)} mm de la ranura más cercana ({DC['sep_ranura_gob']}) y el aro a {fm(DC['sep_aro'], 1)} mm de {DC['sep_aro_gob']}."],
            gd=[("flat", "0,3", None, "Planitud de la cara superior del disco (A) después de tornear"),
                ("par", "0,1", "A", "Fondo del rebaje de la tapa de inspección paralelo a la cara superior (A)")])
    p.build()
    return p.h
