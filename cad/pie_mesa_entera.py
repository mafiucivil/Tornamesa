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


def _stadium_xy(c0, c1, r_, n=10):
    """Contorno de una ranura recta obonga entre los centros de sus extremos c0, c1 (radio r_): [(x, y)]."""
    dx, dy = c1[0] - c0[0], c1[1] - c0[1]
    a = math.atan2(dy, dx)
    pts = []
    for (cx, cy), a0_ in ((c1, a - math.pi / 2), (c0, a + math.pi / 2)):
        pts += [(cx + r_ * math.cos(a0_ + math.pi * i / n), cy + r_ * math.sin(a0_ + math.pi * i / n)) for i in range(n + 1)]
    return pts


def _arc_slot_xy(R, th, L, w, n=10):
    """Contorno de una ranura curva sobre el eje R (centro angular th en rad, largo L en el eje, ancho w, extremos semicirculares): [(x, y)]."""
    r_, h = w / 2, (L - w) / (2 * R)
    m = max(4, int(math.ceil((L - w) / 10.0)))
    pol = lambda rr, aa: (rr * math.cos(aa), rr * math.sin(aa))
    pts = [pol(R + r_, th - h + 2 * h * i / m) for i in range(m + 1)]
    c1 = pol(R, th + h)
    pts += [(c1[0] + r_ * math.cos(th + h + math.pi * i / n), c1[1] + r_ * math.sin(th + h + math.pi * i / n)) for i in range(n + 1)]
    pts += [pol(R - r_, th + h - 2 * h * i / m) for i in range(m + 1)]
    c0 = pol(R, th - h)
    pts += [(c0[0] + r_ * math.cos(th - h + math.pi + math.pi * i / n), c0[1] + r_ * math.sin(th - h + math.pi + math.pi * i / n)) for i in range(n + 1)]
    return pts


def _ranuras_planta(ctx, RG, z, a0, on, jtxt):
    """TT300-BX rev. 9g (Rev. H): dibuja TODAS las ranuras J18 en la planta de la plancha superior, a escala (modelo girado −a0)."""
    g, D, P = ctx.g, ctx.D, ctx.P
    ang = [float(a) for a in D["nervios"]]
    w = float(RG["ancho"])

    def draw(V, p):
        s = p.s
        for a in RG["almas"]:
            for k in range(int(a["n"])):
                th = math.radians(float(a["a0_deg"]) + float(a["paso_deg"]) * k - a0)
                s.pline([V.P((x, y, z)) for x, y in _arc_slot_xy(float(a["r"]), th, float(a["L"]), w)], "VIS", closed=True)
        for t_ in RG["tramos"]:
            k_ = int(t_["cada_k_nervios"])
            for j in range(0, len(ang), k_):
                ph = math.radians(ang[j] - a0)
                for c in t_["centros"]:
                    r0_, r1_ = c - t_["L"] / 2 + w / 2, c + t_["L"] / 2 - w / 2
                    s.pline([V.P((x, y, z)) for x, y in _stadium_xy((r0_ * math.cos(ph), r0_ * math.sin(ph)), (r1_ * math.cos(ph), r1_ * math.sin(ph)), w / 2)], "VIS", closed=True)
    return draw


def sheet_sup(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    zt, tt = g.z0 + g.hd, g.tt
    a0 = float(D["pasadores"][0])
    pitch = 360.0 / g.N_pin
    rot_key(ctx, "mesa_plancha_sup", "pse", -a0)
    DC = M3.disco_central(g) if ctx.m.get("mesa_disco") else None      # rev. 9f: el centro mecanizado pasa al disco MES-016 (agujero biselado 45° de J19)
    rh_ = DC["plancha"]["agujero"] / 2 if DC else g.hole_top / 2
    rs_ = DC["plancha"]["agujero_sup"] / 2 if DC else rh_
    p = Pieza(ctx, ["mesa_plancha_sup"], f"MESA: PLANCHA SUPERIOR ENTERA Ø{f(P['D_top'])} × {f(tt)} CON {g.N_pin} AGUJEROS Ø{f(g.d_pin)} H7", fmt="auto")
    on = ["pse"]
    jj = jids(ctx, "Cierre de la plancha")
    jP = ctx.weld_find("Pasadores de empuje")
    jD = jids(ctx, "Disco central torneado") if DC else []

    def m8(V, p):
        hx = (g.insp_pcd / 2 * math.cos(math.radians(330 - a0)), g.insp_pcd / 2 * math.sin(math.radians(330 - a0)), zt - g.cb_t)
        V.note_hole(hx, g.insp_drill / 2, -40, "6 × M8-6H", ext=(g.R_pin - g.d_pin - g.insp_pcd / 2) * V.scale, on=on,
                    lines=[f"6 × M{fm(g.insp_d, 0)}-6H pasante (taladro Ø{fm(g.insp_drill, 1)})", f"en el fondo del rebaje, PCD Ø{fm(g.insp_pcd, 0)}, 30° + 60°·k desde +x"])
    RGp_ = (((getattr(g, "bx", None) or {}).get("mesa") or {}).get("soldaduras") or {}).get("ranuras") or {}
    dr_sl = _ranuras_planta(ctx, RGp_, zt, a0, on, jj[0] if jj else "J18") if RGp_ else None
    ex_ = (lambda V, p_: (dr_sl(V, p_), (None if DC else m8(V, p_)))) if dr_sl else (None if DC else m8)
    p.vs("planta", on, "top", lv=(1, 2, 1, 1), extra=(25, 0, 45, 10), draw=_planta(ctx, p, zt, on, a0, pitch, 1, ex_, r_in=rh_), title="PLANTA (girada: 1.er agujero sobre la horizontal" + (f"; {int(RGp_['n_total'])} ranuras {jj[0] if jj else 'J18'} dibujadas)" if RGp_ else ")"), hatch=False, w=4.0, mins=0.1, **({"maxs": 0.04} if RGp_ else {}),
         auto=dict(fits={} if DC else {round(g.hole_top, 1): "H12", round(g.cb_D, 1): "H12"}, hole_rmin=g.d_pin / 2 + 1, hole_pos=False, verts=False, only_extents=True,
                   text={**{round(2 * g.Rt, 1): f"Ø{f(2 * g.Rt)} ±1,5"}, **({round(2 * rh_, 1): f"Ø{fm(2 * rh_, 0)} ±1,5 (cara inferior)", round(2 * rs_, 1): f"Ø{fm(2 * rs_, 0)} (cara superior, ref.)"} if DC else {})}))
    # datum A: agujero central (su eje = eje de la mesa), en el detalle B (en la planta no hay lugar libre junto al rebaje)
    p.datum_in("det_c", "surf", "A", at=([(rh_ + 4, 0, zt - tt + 4), (rh_ + 7, 0, zt - tt + 7)] if DC else [(rh_, 0, zt - tt + 4), (rh_, 0, zt - tt + 7)]), d=(-1, 0, 0))
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
    if DC:                               # rev. 9f: agujero de corte térmico con bisel 45° (bisel de J19); la junta con el disco y el cubo se detalla en MES-016
        def detC(V, p):
            V.note_pt((rh_ + tt / 2, 0, zt - tt / 2), (-34, -24), f"bisel {fm(DC['junta']['alfa'], 0)}° +10°/−0° de corte térmico (J19)", on=on, dot=True)
        p.detail("det_c", "corte", (rh_ + 14, 0, zt - tt / 2), 38, "B", lv=(1, 2, 1, 1), title=f"DETALLE B: AGUJERO CENTRAL Ø{fm(2 * rh_, 0)}/Ø{fm(2 * rs_, 0)} BISELADO {fm(DC['junta']['alfa'], 0)}° (JUNTA J19 CON EL DISCO {_cc(ctx, 'mesa_disco')} SOBRE EL CUBO)", maxs=2.0, mins=0.5, draw=detC)
    else:
        p.detail("det_c", "corte", (g.hole_top / 2 + 10, 0, zt - tt / 2), 38, "B", lv=(1, 2, 1, 1), title="DETALLE B: AGUJERO CENTRAL Y REBAJE DE LA TAPA", maxs=2.0,
                 auto=dict(text={round(tt - g.cb_t, 1): f"({f(tt - g.cb_t)})"}))
        p.ra_in("det_c", "Ra 6,3", [(g.hole_top / 2 + 22, 0, zt - g.cb_t), (g.hole_top / 2 + 12, 0, zt - g.cb_t), (g.cb_D / 2 + 12, 0, zt), (g.cb_D / 2 + 20, 0, zt)], (0, 0, 1))
    _tabla_agujeros(ctx, p, "vista desde la cara superior")
    rc_ = ranuras_cierre(ctx)
    RG_ = (((getattr(g, "bx", None) or {}).get("mesa") or {}).get("soldaduras") or {}).get("ranuras") or {}
    rtx_ = (f"{fm(RG_['ancho'], 0)} × L con extremos semicirculares R{fm(RG_['ancho'] / 2, 1)}, sin respaldo, relleno completo {fm(RG_['relleno'], 0)}; separación entre centros ≥ 2·L" if RG_ else "22 × 80 a paso 250")
    if jj and RG_:
        add_prep(p, "det_j18", wd(ctx, jj[0]))
    if RG_:                              # rev. 9g: columna L (largo por elemento) y largo total
        p.table_block(f"RANURAS DE CIERRE {jj[0] if jj else ''} ({rtx_}; eje de la ranura sobre el eje del alma o nervio)" + (f"; las del tramo 1 se abren en el bisel de J19" if DC else ""),
                      [("Elemento", 30, "L"), ("Ubicación", 72, "L"), ("Ángulos", 44, "L"), ("L [mm]", 14, "R"), ("Cant", 12, "R")],
                      [[a, b_, c_, fm(r5[0], 0), str(n_)] for a, b_, c_, n_, *r5 in rc_] + [["TOTAL", f"largo total {fm(sum(r_[3] * r_[4] for r_ in rc_), 0)} mm", "", "", str(sum(r_[3] for r_ in rc_))]], bold_rows=(len(rc_),))
    else:
        p.table_block(f"RANURAS DE CIERRE {jj[0] if jj else ''} ({rtx_}; eje de la ranura sobre el eje del alma o nervio)", [("Elemento", 34, "L"), ("Ubicación", 70, "L"), ("Ángulos", 46, "L"), ("Cant", 14, "R")],
                      [[a, b_, c_, str(n_)] for a, b_, c_, n_, *_ in rc_] + [["TOTAL", "", "", str(sum(r_[3] for r_ in rc_))]], bold_rows=(len(rc_),))
    p.tables(jj + jD + ([jP["id"]] if jP else []))
    U_ = (D.get("pasadores_empuje") or {}).get("union")
    p.notes([f"Plancha ENTERA de una pieza Ø{f(2 * g.Rt)} × {f(tt)} (TT300-BX rev. 7c, decisión del mandante 19-11-2026): sin anillo de pasadores, sin empalmes CJP de segmentos y sin unión soldada plancha–anillo. "
             f"Compra: plancha de {f(tt)} mm de AL MENOS {f(2 * g.Rt)} × {f(2 * g.Rt)} (ASTM A572 Gr. 50, Z35, UT ASTM A578 nivel B).",
             (f"Contorno Ø{f(2 * g.Rt)} ±1,5 por plasma/oxicorte (ISO 9013 clase 3). Agujero central con BISEL {fm(DC['junta']['alfa'], 0)}° +10°/−0° de corte térmico (plasma u oxicorte con cabezal de bisel; rev. 9f, pedido del mandante 23-11-2026): "
              f"Ø{fm(2 * rh_, 0)} ±{fm(DC['plancha']['tol'], 1)} en la cara inferior (raíz de J19: abertura R = {fm(DC['junta']['R'], 0)} con el disco Ø{fm(DC['D'], 0)}) y Ø{fm(2 * rs_, 0)} en la superior; esmerilar escoria y bisel (metal brillante 25 mm). "
              f"El agujero Ø{f(g.hole_top)} de J17b, el rebaje Ø{f(g.cb_D)} × {f(g.cb_t)} y las roscas de la tapa de inspección van en el disco central torneado {_cc(ctx, 'mesa_disco')}, a escuadra y apoyado en la cara superior del cubo, "
              f"soldado a esta plancha con la CJP {', '.join(jids(ctx, 'Disco central torneado')) or 'J19'} (B-U4a: bisel en esta plancha, f = {fm(DC['junta']['f'], 0)}; respaldo permanente = cara superior del cubo, {fm(DC['cubo']['margen'], 0)} mm más allá de la raíz). "
              f"El recorte central sirve de tocho del disco (misma colada)." if DC else
              f"Contorno Ø{f(2 * g.Rt)} ±1,5 por plasma/oxicorte (ISO 9013 clase 3). Agujero central Ø{f(g.hole_top)} y rebaje Ø{f(g.cb_D)} × {f(g.cb_t)} (apoyo de la tapa de inspección PIV-004): mecanizar en mandrinadora/fresadora; Ra 6,3."),
             f"{g.N_pin} agujeros Ø{f(g.d_pin)} H7 (+0,035/0) PASANTES en PCD Ø{f(2 * g.R_pin)} (tabla de agujeros; 1.er agujero a {fm(a0, 3)}° de +x, paso {fm(pitch, 3)}°): pretaladrar Ø80 en la plancha suelta "
             f"y MANDRINAR/ESCARIAR a Ø{f(g.d_pin)} H7 EN LÍNEA con la plancha inferior ({_cc(ctx, 'mesa_plancha_inf')}) con la mesa armada, soldada y aliviada (eje común; coaxialidad Ø0,05, CON-009). Ra 3,2; aristas rotas 1 × 45°.",
             (f"Borde EXTERIOR de cada agujero (cara superior): bisel 45° × {f(U_['S'])} para la PJP {jP['id'] if jP else 'J-P1'} del pasador soldado a ras (detalle en la lámina del pasador), mecanizado después del mandrinado."
              if U_ else "Pasadores montados m6/H7 según la lámina del pasador."),
             (f"Unión con almas y nervios SOLO por {jj[0] if jj else 'J18'}: unión en T a través de ranura, SIN respaldo y NO PRECALIFICADA (ancho {fm(RG_['ancho'], 0)} < t + 8 = {fm(RG_['ancho_precal_min'], 0)}, AISC 360-22 §J2.3b; WPS calificada por ensayo): "
              f"{RG_.get('n_total', '')} ranuras pasantes de {fm(RG_['ancho'], 0)} × L (L = {' / '.join(sorted({fm(r_[4], 0) for r_ in rc_}, key=float))} según el elemento), extremos semicirculares R{fm(RG_['ancho'] / 2, 1)}, cortadas a plasma antes de montar la plancha (ISO 9013 clase 3; eje sobre el eje del alma o nervio ±1; curvas en las almas), "
              f"centradas sobre el canto del alma o nervio de {fm(RG_['t_alma'], 0)} ({fm(RG_['holgura_lado'], 1)} por lado); en las almas, al centro del vano entre nervios (ninguna en un cruce alma–nervio); en el tramo 1, en nervios alternados desde R{fm(RG_['tramos'][0]['r_int'], 0)}. "
              f"Largo L de cada elemento = el mínimo con FU ≤ 1 para su corte horizontal (rev. 9h, decisión del mandante 25-11-2026; L ≥ 2·ancho = {fm(RG_.get('L_min', 30), 0)}); la carga vertical pasa por CONTACTO directo de la plancha sobre los cantos. "
              f"Soldadas en taller desde arriba (plana) con la plancha apretada contra los cantos (≤ 1 mm, OBLIGATORIO en todo el canto): relleno completo fundido al canto y a las dos paredes, esmerilado a ras; VT 100 % y MT 100 % (UT no practicable), ISO 5817-C. "
              f"Ranuras dibujadas en la planta (posiciones en la tabla «RANURAS DE CIERRE»); no modeladas en 3D."
              if RG_ else f"Soldadura de cierre sobre almas y nervios por ranuras ({jj[0] if jj else 'J18'}): 22 × 80 a paso 250, posiciones en la tabla «RANURAS DE CIERRE» (PROPUESTA, confirmar); no modeladas en 3D."),
             *([f"{jj[0] if jj else 'J18'}: {RG_['calificacion']}. La calificación precede a la producción."] if RG_ else []),
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


def sheet_disco(ctx):
    """TT300-BX rev. 9f (pedido del mandante 23-11-2026; reemplaza el Ø700 de la rev. 9e): plano de torno del disco central de la plancha superior
    (MES-016), a escuadra y apoyado entero en la cara superior del cubo, con el agujero Ø D_piv + 80 de J17b, el rebaje de la tapa de inspección y las
    roscas M8; detalle de la CJP J19 (bisel en la plancha, respaldo = cara del cubo). Todas las medidas salen de bx.mesa.soldaduras.disco_central."""
    g, P, D = ctx.g, ctx.P, ctx.D
    DC = M3.disco_central(g)
    zt = g.z0 + g.hd
    t, Rb = float(DC["t"]), float(DC["R_inf"])
    rH, rC, hC = float(DC["agujero"]["d"]) / 2, float(DC["rebaje"]["d"]) / 2, float(DC["rebaje"]["prof"])
    J, C, T = DC["junta"], DC["cubo"], DC["torneado"]
    cD, cS, cH = _cc(ctx, "mesa_disco"), _cc(ctx, "mesa_plancha_sup"), _cc(ctx, "mesa_cubo")
    p = Pieza(ctx, ["mesa_disco"], f"MESA: DISCO CENTRAL TORNEADO Ø{fm(2 * Rb, 0)} × {fm(t, 0)} SOBRE EL CUBO (J17b Y TAPA DE INSPECCIÓN)", fmt="auto")
    s = p.s
    on = ["mesa_disco"]
    j19 = jids(ctx, "Disco central torneado")
    jB, jj = jids(ctx, "Cubo – plancha superior, en el disco"), jids(ctx, "Cierre de la plancha")
    smL, smF = float(T["sm_lado"]), float(T["sm_fondo"])

    def planta(V, p):
        c3 = (0, 0, zt)
        s.centerlines(V.P(c3), Rb * V.scale + 6, 8)
        V.dim_dia((0, 0, zt - t), Rb, 138, on=on, text=f"Ø{fm(2 * Rb, 0)} ±{fm(DC['tol_D'], 1)}", ext=16)
        V.dim_dia(c3, rC, 166, on=on, text=f"Ø{fm(2 * rC, 0)} H12", ext=(Rb - rC) * V.scale + 16)
        V.dim_dia(c3, rH, 196, on=on, text=f"Ø{fm(2 * rH, 0)} H12", ext=(Rb - rH) * V.scale + 16)
        hx = (g.insp_pcd / 2 * math.cos(math.radians(330)), g.insp_pcd / 2 * math.sin(math.radians(330)), zt - hC)
        V.note_hole(hx, g.insp_drill / 2, -40, "6 × M8-6H", ext=(Rb - g.insp_pcd / 2) * V.scale + 10, on=on,
                    lines=[f"6 × M{fm(g.insp_d, 0)}-6H pasante (taladro Ø{fm(g.insp_drill, 1)}) en el fondo del rebaje", f"PCD Ø{fm(g.insp_pcd, 0)}, 30° + 60°·k; AL FINAL (mesa soldada y aliviada)"])
        p.cut_mark("planta", "A", (-Rb - 16, 0, zt), (Rb + 16, 0, zt), 90)
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(50, 20, 60, 20), draw=planta, title="PLANTA (cara superior; sin ranuras J18 en el disco)", hatch=False, w=4.0, auto=False, mins=0.1)

    def corte(V, p):
        V.dimh((0, 0, zt - t), (Rb, 0, zt - t), "bottom", 0, on=on, text=f"Ø{fm(2 * Rb, 0)} ±{fm(DC['tol_D'], 1)}", virt_a=rH)
        V.dimh((0, 0, zt), (rC, 0, zt), "top", 0, on=on, text=f"Ø{fm(2 * rC, 0)} H12 (+0,46/0)", virt_a=rH)
        V.dimh((0, 0, zt - t), (rH, 0, zt - t), "bottom", 1, on=on, text=f"Ø{fm(2 * rH, 0)} H12 (+0,46/0)", virt_a=rH)
        V.dimv((Rb, 0, zt - t), (Rb, 0, zt), "right", 0, on=on, text=f"{fm(t, 0)}")
        V.note_pt((Rb, 0, zt - t / 2), (40, 16), f"canto a escuadra (sin bisel: el bisel de {j19[0] if j19 else 'J19'} va en la plancha)", on=on, dot=True)
        s.line(V.P(0, 0, zt - t - 6), V.P(0, 0, zt + 6), "EJE")
    p.ra_in("corte", "Ra 3,2", [(rC + 6, 0, zt), (Rb - 6, 0, zt), (rC + 12, 0, zt)], (0, 0, 1))
    p.vs("corte", on, "front", cut=CUT_Y, win=(-8, zt - t - 6, Rb + 12, zt + 8), center=(0, 0, 0), lv=(2, 2, 2, 2), extra=(0, 0, 40, 0), draw=corte,
         title="CORTE A-A (semicorte radial)", hs=0.5, w=1.4, mins=0.2, auto=False)

    def detB(V, p):
        pass
    p.detail("det_b", "corte", (rC - 4, 0, zt - t / 2), 26, "B", lv=(1, 2, 2, 1), title=f"DETALLE B: AGUJERO Ø{fm(2 * rH, 0)} Y REBAJE Ø{fm(2 * rC, 0)} × {fm(hC, 0)} (TERMINADO)", draw=detB, mins=0.1, maxs=3.0, auto=dict(text={round(t - hC, 1): f"({fm(t - hC, 0)})", round(hC, 1): f"{fm(hC, 0)} +0,2/0"}))
    p.datum_in("det_b", "surf", "A", at=[(rC + 8, 0, zt), (rC + 14, 0, zt), (rC + 18, 0, zt)], d=(0, 0, 1))
    p.gd_in("det_b", "surf", "flat", f"{fm(DC['planitud'], 1)}", None, at=[(rC + 12, 0, zt), (rC + 4, 0, zt), (rC + 18, 0, zt)], d=(0, 0, 1))
    p.gd_in("det_b", "surf", "par", "0,1", "A", at=[(rH + 6, 0, zt - hC), (rH + 12, 0, zt - hC), (rH + 16, 0, zt - hC)], d=(0, 0, 1))
    if j19:
        add_prep(p, "det_j19", wd(ctx, j19[0]), title=f"DETALLE {j19[0]}: CJP PLANCHA–DISCO B-U4a SOBRE EL CUBO (BISEL {fm(J['alfa'], 0)}° EN LA PLANCHA, DISCO A ESCUADRA, R = {fm(J['R'], 0)}, f = {fm(J['f'], 0)}, RESPALDO = CARA DEL CUBO, ESMERILADA A RAS)")
    tol = [["Ø exterior, canto a escuadra (raíz de J19)", f"Ø{fm(2 * Rb, 0)}", f"±{fm(DC['tol_D'], 1)}", "Ra 6,3", f"abertura de raíz R = {fm(J['R'], 0)} con el agujero Ø{fm(DC['plancha']['agujero'], 0)} ±{fm(DC['plancha']['tol'], 1)} de la plancha"],
           ["Agujero de J17b", f"Ø{fm(2 * rH, 0)}", "H12 (+0,46/0)", "Ra 3,2", f"referencia del cabezal portátil; tapa retenedora Ø{fm(g.cap_D, 0)} adentro"],
           ["Rebaje de la tapa de inspección (asiento)", f"Ø{fm(2 * rC, 0)} × {fm(hC, 0)}", "H12 (+0,46/0); prof. +0,2/0", "Ra 3,2", f"desbaste Ø{fm(2 * rC - 2 * smL, 0)} × {fm(hC - smF, 1)}; terminar en sitio tras J19, J17b y alivio; fondo paralelo a A 0,1"],
           ["Cara superior (A)", f"espesor {fm(t, 0)}", "limpieza ≤ 0,5", "Ra 3,2", f"planitud {fm(DC['planitud'], 1)} (referencia de la profundidad del rebaje)"],
           ["Cara inferior", "—", "de laminación", "—", f"apoya entera en la cara del cubo (Ø{fm(2 * C['R_int'], 0)}/Ø{fm(2 * C['R_ext'], 0)})"],
           ["Roscas de la tapa de inspección", f"6 × M{fm(g.insp_d, 0)}-6H, PCD Ø{fm(g.insp_pcd, 0)}", "posición Ø0,3", "—", "taladrar y roscar AL FINAL, con plantilla en el rebaje terminado"]]
    p.table_block(f"TOLERANCIAS DE TORNEADO ({cD}; ISO 2768-m donde no se indica)", [("Elemento", 46, "L"), ("Nominal", 30, "L"), ("Tolerancia", 30, "L"), ("Ra", 12, "C"), ("Observación", 62, "L")], tol)
    p.tables(j19 + jB + jj)
    p.notes([f"Disco central de la plancha superior (TT300-BX rev. 9f, pedido del mandante 23-11-2026; POR DEFECTO, A CONFIRMAR POR EL MANDANTE): {DC['material']}, mismo material, espesor y colada que la plancha {cS} (plancha superior de {fm(t, 0)} mm en ASTM A572 Gr. 50 CONFIRMADA por el mandante el 23-11-2026; Z35 y UT ASTM A578 nivel B siguen propuestos). "
             f"Tocho Ø{fm(DC['tocho']['d'], 0)} × {fm(t, 0)}: {DC['tocho']['nota']}.",
             f"Diámetro: {DC['motivo']}",
             f"Respaldo de {j19[0] if j19 else 'J19'}: {C['respaldo']}. Margen de la cara del cubo más allá de la raíz: {fm(C['margen'], 0)} mm (≥ {fm(C['margen_min'], 0)}).",
             f"Torneado: {T['decision']}. Motivo: {T['razon']}. {T['alternativa'][0].upper() + T['alternativa'][1:]}.",
             f"Montaje y soldadura (secuencia del núcleo): " + " ".join(DC["secuencia"]),
             f"{j19[0] if j19 else 'J19'}: {J['tipo']}; bisel en la plancha {cS} ({DC['plancha']['corte']}); disco a escuadra; R = {fm(J['R'], 0)}, f = {fm(J['f'], 0)}; {J['tolerancias']}; {J['terminacion']}; END {J['END']}; nivel {J['nivel']}; "
             f"{int(J['sectores'])} sectores opuestos. Precalentamiento por la parte más gruesa (pared del cubo {fm(J['precalentamiento_t'], 0)} mm, fundida por la raíz; AWS D1.1:2020 Tabla 5.8): ver la tabla de soldaduras.",
             f"Ranuras J18: ninguna en el disco; {DC['ranura_tramo1']['nota']}."],
            gd=[("flat", f"{fm(DC['planitud'], 1)}", None, "Planitud de la cara superior del disco (A) después de tornear"),
                ("par", "0,1", "A", "Fondo del rebaje de la tapa de inspección paralelo a la cara superior (A), al terminarlo en sitio")])
    p.build()
    return p.h
