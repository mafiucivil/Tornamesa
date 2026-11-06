"""Láminas de fabricación por pieza (una lámina por pieza o grupo de piezas iguales). Las vistas salen del sólido 3D; las cotas se verifican contra él."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_util import *

PLAN = []          # (nombre_función, [claves de pieza]) — se llena con @pieza


def pieza(*keys):
    def deco(fn):
        PLAN.append((fn.__name__, list(keys), fn))
        return fn
    return deco


def register(ctx):
    """Asigna a cada pieza la lámina que la dibuja (para la columna «Plano» del despiece) antes de dibujar cualquier lámina."""
    ctx.group_of = {}
    for name, keys, fn in PLAN:
        ks = [k for k in keys if ctx.m.get(k)]
        for k in ks:
            ctx.group_of[k] = ctx.m.get(ks[0]).code


def ghost(p, V, keys, hatch=False):
    sh = p.ctx.sh(*[k for k in keys if k in p.ctx.shapes])
    if not sh:
        return
    G = View(p.s, sh, V.view, V.origin, V.scale, center=V.center if hasattr(V, "center") else (0, 0, 0), win=V.win, cut=V.cut, label="fantasma")
    G.draw(layer_vis="FANT", hatch=False)


def rough_note(s, x, y, ra, txt):
    s.roughness((x, y), ra)
    s.text(txt, (x + 12 + tw(ra, T_N) + 4, y + 6), T_N, "MIDDLE_LEFT")


def pos_table(p, x, y, title, cols, rows, width):
    sc = width / sum(c[1] for c in cols)
    return p.s.table(x, y, [(t, w * sc, a) for t, w, a in cols], rows, h=T_S, title=title)[0]


# ======================================================================================================
@pieza("base_plancha")
def sheet_base_plancha(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    B, tb = g.B, g.tb
    p = Pieza(ctx, ["base_plancha"], "PLANCHA BASE: CONTORNO, AGUJERO CENTRAL Y POSICIONES", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    cL = (x0, y0, x0 + 0.56 * (x1 - x0), y1)
    V = p.V(["base_plancha"], "top", cL, label="Planta", margin=(30, 24, 26, 26))
    ghost(p, V, ["marco_largo", "marco_corto", "collar", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "orejas", "bancada"])
    s.line(V.P(-B / 2 - 70, 0, tb), V.P(B / 2 + 70, 0, tb), "EJE"); s.line(V.P(0, -B / 2 - 70, tb), V.P(0, B / 2 + 70, tb), "EJE")
    on = ["base_plancha"]
    xl, cl, xg = P["x_lug"], g.cl_lug, P["x_g"]
    V.chain_h([(-B / 2, B / 2, tb), (-xg, B / 2, tb), (-xl, B / 2, tb), (0, B / 2, tb), (xl, B / 2, tb), (xg, B / 2, tb), (B / 2, B / 2, tb)], "top", 0, on=on)
    V.dimh((-B / 2, B / 2, tb), (B / 2, B / 2, tb), "top", 1, on=on, text=f"{f(B)} ±2")
    V.chain_v([(-B / 2, -B / 2, tb), (-B / 2, -cl, tb), (-B / 2, 0, tb), (-B / 2, cl, tb), (-B / 2, B / 2, tb)], "left", 0, on=on)
    V.dimv((-B / 2, -B / 2, tb), (-B / 2, B / 2, tb), "left", 1, on=on, text=f"{f(B)} ±2")
    V.dim_dia((0, 0, tb), P["D_piv"] / 2, 215, text=f"Ø{f(P['D_piv'])} H7 (+0,035/0), pasante", on=on, ext=30)
    s.circle(V.P(0, 0, tb), g.D_boss / 2 * V.scale, "FANT")
    s.text(f"Collar Ø{f(g.D_boss)} (BAS-002), concéntrico", (V.P(0, 0, tb)[0] + 34, V.P(0, 0, tb)[1] - 15), T_N, "MIDDLE_LEFT")
    s.circle(V.P(0, 0, tb), (P["D_top"] + 20) / 2 * V.scale, "FANT")
    s.leader((V.P(0, 0, tb)[0] + (P["D_top"] + 20) / 2 * V.scale * 0.707, V.P(0, 0, tb)[1] - (P["D_top"] + 20) / 2 * V.scale * 0.707),
             (V.P(0, 0, tb)[0] + 62, V.P(0, 0, tb)[1] - 100), f"Zona de apoyo de la interfaz Ø{f(P['D_top'] + 20)}: planitud 0,20", dot=True)
    # agujeros roscados de los tornillos de posición (variantes con interfaz)
    cs = V.circles(["base_plancha"], 2.0, 4.5)
    if cs:
        r0 = cs[0][2]
        n = len(cs)
        u, v, r = cs[0]
        V.note_hole((u, v, tb), r, 100, f"{n} × M{fm(r * 2, 0)} (rosca en el respaldo; ver tabla de agujeros)", ext=40, on=on)
    # corte A-A
    s.cut_line(V.P(-B / 2 - 38, 0, tb), V.P(B / 2 + 38, 0, tb), "A", 90)
    V.title("PLANTA DE LA PLANCHA BASE")
    # --- corte parcial A-A ---
    cR = (x0 + 0.58 * (x1 - x0), y0 + 0.50 * (y1 - y0), x1, y1)
    VA = p.V(["base_plancha"], "front", cR, label="Corte A-A", cut=((0, 0, 0), (0, 1, 0)), win=(-240, -8, 240, tb + 14), margin=(14, 18, 14, 30), hatch_scale=0.5)
    s.line(VA.P(0, 0, -10), VA.P(0, 0, tb + 10), "EJE")
    VA.dimv((240, 0, 0), (240, 0, tb), "right", 0, on=on, text=f"{f(tb)} (t_base)")
    VA.dim_dia((0, 0, tb / 2), P["D_piv"] / 2, 20, text=f"Ø{f(P['D_piv'])} H7", on=on, ext=22)
    s.roughness((VA.P(70, 0, tb)[0], VA.P(70, 0, tb)[1] + 3), "Ra 1,6")
    s.text("Ra 3,2 cara de apoyo (Ø%s)" % f(P["D_top"] + 20), (VA.P(-230, 0, tb)[0], VA.P(0, 0, tb + 14)[1] - 2), T_N, "TOP_LEFT")
    s.datum((VA.P(-200, 0, 0)[0], VA.P(0, 0, 0)[1] - 1), "A", up=False)
    s.gdt((VA.P(-60, 0, 0)[0] - 30, VA.P(0, 0, 0)[1] - 33), "flat", "0,20", None)
    s.text("Planitud (Ø%s)" % f(P["D_top"] + 20), (VA.P(-60, 0, 0)[0] + 20, VA.P(0, 0, 0)[1] - 30), T_N, "MIDDLE_LEFT")
    s.gdt((VA.P(60, 0, 0)[0] - 10, VA.P(0, 0, 0)[1] - 50), "perp", "0,05", "A")
    s.text("Eje Ø%s H7" % f(P["D_piv"]), (VA.P(60, 0, 0)[0] + 38, VA.P(0, 0, 0)[1] - 46), T_N, "MIDDLE_LEFT")
    VA.title("CORTE PARCIAL A-A (mitad)")
    # --- tabla de posiciones ---
    rows = []
    for i, (ex, ey) in enumerate(g.ear_pos):
        rows.append([f"O{i + 1} oreja de izaje", f(ex), f(ey), "—", f"plano radial {fm(math.degrees(math.atan2(ey, ex)), 2)}°"])
    for grp in ("horario", "antihorario"):
        for k, c in enumerate(D["cilindros"][grp]):
            rows.append([f"M{len(rows) - 3} ménsula {grp}", f(c["eye"][0], 1), f(c["eye"][1], 1), f(c["phiMean"], 1) + "°", "eje del ojal"])
    for sx in (1, -1):
        rows.append(["Bancada (eje de guía)", f(sx * P["x_g"]), "0", "90°", f"largo {f(g.KG['L_bed'], 1)}"])
    rows.append(["Collar / agujero H7", "0", "0", "—", f"Ø{f(g.D_boss)} / Ø{f(P['D_piv'])}"])
    pos_table(p, x0 + 0.58 * (x1 - x0), cR[1] - 6, "POSICIONES DE LAS PIEZAS SOLDADAS (origen: centro de la plancha)",
              [("Elemento", 60, "L"), ("x [mm]", 22, "R"), ("y [mm]", 22, "R"), ("Ángulo", 18, "C"), ("Observación", 52, "L")], rows, (x1 - (x0 + 0.58 * (x1 - x0))) - 2)
    p.tables()
    nz = [
        f"Plancha {f(B)} × {f(B)} × {f(tb)} de {p.p0.material.split(',')[0]}; sobrematerial de corte 5 mm por borde, recortar a medida después del alivio. Corte por oxicorte/plasma con tolerancia ISO 9013 clase 3.",
        f"Agujero central Ø{f(P['D_piv'])} H7: mandrinar plancha y collar en un solo montaje (mandrinadora) después de soldar el collar y aliviar tensiones; Ra 1,6; perpendicular a la cara de apoyo 0,05.",
        f"Cara superior en la zona Ø{f(P['D_top'] + 20)}: planeada (planitud 0,20 / Ra 3,2); sin pintura en esa zona. Compensar la distorsión de la soldadura con contraflecha o secuencia simétrica.",
        "Posiciones de las piezas soldadas (tabla): marcar con granete y trazado antes de armar; tolerancia ±1 salvo indicación.",
        "Soldaduras de la base: ver BAS-CON y el programa de soldaduras (GEN-007). Alivio de tensiones 590–620 °C después de soldar y antes del mecanizado final.",
        "La plancha NO lleva anclajes: equipo sin anclaje (apoyo sobre losa).",
    ]
    if g.opt:
        nz.append(f"Agujeros roscados M{fm(P['d_tor'], 0)} de los tornillos de posición: posiciones y profundidades en la lámina de sectores; roscar después de planear la cara.")
    p.notes(nz)
    p.finish_scale()
    return p.h


# ---------------------------------------------------------------------------------------------- helpers de sección
CUT_Y = ((0, 0, 0), (0, 1, 0))
CUT_X = ((0, 0, 0), (-1, 0, 0))


def tol_dim(V, a, b, code, d, **kw):
    """Cota de diámetro/longitud con ajuste ISO 286 en el texto (límites calculados)."""
    return V.dim(a, b, kw.pop("off", 10), text=tol_txt(d, code), **kw)


def w_sym(p, jid, V, pt3, off, **kw):
    """Símbolo de soldadura de la junta jid apuntando a un punto 3D de la vista V."""
    a = V.P(pt3)
    if "sh" not in kw:
        kw["sh"] = 1 if a[0] < p.views[2] - 190 else -1
    sg = kw["sh"]
    p.h.weld(jid, a, (a[0] + abs(off[0]) * sg, a[1] + off[1]), **kw)


def J(ctx, frag):
    w = ctx.weld_find(frag)
    return w["id"] if w else "J??"


def jids(ctx, *frags):
    out = []
    for fr in frags:
        w = ctx.weld_find(fr)
        if w:
            out.append(w["id"])
    return out


# ======================================================================================================
@pieza("collar")
def sheet_collar(ctx):
    g, P = ctx.g, ctx.P
    tb = g.tb
    p = Pieza(ctx, ["collar"], "COLLAR DE ASIENTO DEL PIVOTE", fmt="A2")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["collar"]
    Vt = p.V(on, "top", (x0, y0, x0 + 0.44 * (x1 - x0), y1), label="Planta", margin=(24, 26, 24, 24))
    Vt.dim_dia((0, 0, tb + g.h_boss), g.D_boss / 2, 40, on=on, text=f"Ø{f(g.D_boss)} ±1", ext=14)
    Vt.dim_dia((0, 0, tb + g.h_boss), P["D_piv"] / 2, 200, on=on, text=tol_txt(P["D_piv"], "H7"), ext=14)
    s.centerlines(Vt.P(0, 0, tb), g.D_boss / 2 * Vt.scale, 6)
    Vt.title("PLANTA")
    Vs = p.V(on, "front", (x0 + 0.46 * (x1 - x0), y0, x1, y1), label="Corte A-A", cut=CUT_Y, margin=(22, 26, 40, 24), hatch_scale=0.6)
    s.line(Vs.P(0, 0, tb - 6), Vs.P(0, 0, tb + g.h_boss + 8), "EJE")
    Vs.dimv((g.D_boss / 2, 0, tb), (g.D_boss / 2, 0, tb + g.h_boss), "right", 0, on=on, text=f"{f(g.h_boss)} ±0,5")
    Vs.dimh((-g.D_boss / 2, 0, tb + g.h_boss), (g.D_boss / 2, 0, tb + g.h_boss), "top", 0, on=on, text=f"Ø{f(g.D_boss)}")
    Vs.dimh((-P["D_piv"] / 2, 0, tb), (P["D_piv"] / 2, 0, tb), "bottom", 0, on=on, text=tol_txt(P["D_piv"], "H7"))
    Vs.dimh((P["D_piv"] / 2, 0, tb + g.h_boss), (g.D_boss / 2, 0, tb + g.h_boss), "top", 1, on=on, text=f"{fm((g.D_boss - P['D_piv']) / 2, 0)} (cara anular)")
    w_sym(p, jids(ctx, "Collar")[0], Vs, (g.D_boss / 2, 0, tb + 1), (45, -40), all_round=True)
    s.roughness((Vs.P(-P["D_piv"] / 2, 0, tb + g.h_boss / 2)[0] + 4, Vs.P(0, 0, tb + g.h_boss / 2)[1] - 3), "Ra 1,6")
    s.roughness((Vs.P(-g.D_boss / 2, 0, tb + g.h_boss)[0] + 6, Vs.P(0, 0, tb + g.h_boss)[1] + 3), "Ra 3,2")
    yy = Vs.ext[1] - 30
    gd_column(s, Vs.ext[0], yy, [("perp", "0,05", "A", "Agujero H7 perpendicular a la cara de apoyo (A = cara inferior)"), ("flat", "0,10", None, "Planitud de la cara superior"),
                                 ("coax", "Ø0,05", "A", "Coaxial con el agujero de la plancha base (mandrinado en línea)")], 12)
    Vs.title("CORTE A-A")
    p.tables(jids(ctx, "Collar"))
    p.notes([f"Disco Ø{f(g.D_boss)} × {f(g.h_boss)}: oxicorte/plasma desde plancha de {f(g.h_boss + 5)} (sobremetal 5); caras planeadas.",
             f"Agujero Ø{f(P['D_piv'])} H7: NO se mecaniza antes de soldar; se mandrina en línea con la plancha base (BAS-001) en un solo montaje, Ra 1,6.",
             f"Soldar a la plancha base con filete perimetral continuo z{fm(g.w_collar, 0)} ({J(ctx, "Collar")}): secuencia simétrica por tramos opuestos para limitar la distorsión; alivio de tensiones antes de mandrinar.",
             "Arista exterior superior e interior de la boca del agujero: 1×45° (ISO 13715).",
             "Sin pintura en la cara superior (asiento del cubo de la mesa: holgura axial c_boss_a)."])
    p.finish_scale()
    return p.h


@pieza("marco_largo", "marco_corto")
def sheet_marcos(ctx):
    g, P = ctx.g, ctx.P
    B, tb, rt, rh = g.B, g.tb, P["rim_t"], P["rim_h"]
    ctx.local("marco_largo", "ml1", near=(0, -B / 2 + 5, tb + 20), r=300)
    ctx.local("marco_corto", "mc1", near=(B / 2 - 5, 0, tb + 20), r=300)
    p = Pieza(ctx, ["marco_largo", "marco_corto"], "MARCO PERIMETRAL: PLETINAS LARGA Y CORTA", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    Vl = p.V(["ml1"], "front", (x0, y0 + 0.62 * (y1 - y0), x1, y1), label="Pletina larga", margin=(20, 40, 20, 30), mat={"ml1": "acero"})
    on = ["ml1"]
    Vl.dimh((-B / 2, -B / 2, tb), (B / 2, -B / 2, tb), "bottom", 0, on=on, text=f"{f(B)} ±2 (largo = B)")
    Vl.dimv((B / 2, -B / 2, tb), (B / 2, -B / 2, tb + rh), "right", 0, on=on, text=f"{f(rh)} ±0,5")
    Vl.title("PLETINA LARGA (BAS-003) — 2 unidades")
    Vc = p.V(["mc1"], "right", (x0, y0 + 0.28 * (y1 - y0), x1, y0 + 0.62 * (y1 - y0)), label="Pletina corta", margin=(20, 40, 20, 24), mat={"mc1": "acero"})
    on2 = ["mc1"]
    Vc.dimh((B / 2, -B / 2 + rt, tb), (B / 2, B / 2 - rt, tb), "bottom", 0, on=on2, text=f"{f(B - 2 * rt)} ±2 (= B − 2·t)")
    Vc.dimv((B / 2, B / 2 - rt, tb), (B / 2, B / 2 - rt, tb + rh), "right", 0, on=on2, text=f"{f(rh)} ±0,5")
    j2 = jids(ctx, "Marco corto – plancha")
    if j2:
        w_sym(p, j2[0], Vc, (B / 2 - 600, -B / 2 + rt + 0, tb + 1) if False else (0, B / 2 if False else 0, tb + 0.5), (30, 34)) if False else None
    Vc.title("PLETINA CORTA (BAS-004) — 2 unidades")
    # sección de junta: pletina sobre la plancha, con soldadura
    kd = ["base_plancha", "marco_largo"]
    Vj = p.V(kd, "right", (x0, y0, x0 + 0.5 * (x1 - x0), y0 + 0.28 * (y1 - y0)), label="Detalle junta", cut=CUT_X, center=(0, -B / 2, tb), win=(-34, -tb - 4, 60, rh + 12), margin=(16, 6, 24, 4), hatch_scale=0.4)
    Vj.dimv((0, -B / 2 + rt, tb), (0, -B / 2 + rt, tb + rh), "right", 0, on=["marco_largo"], text=f"{f(rh)}")
    Vj.dimh((0, -B / 2, tb + rh), (0, -B / 2 + rt, tb + rh), "top", 0, on=["marco_largo"], text=f"{f(rt)}")
    Vj.dimv((0, -B / 2 + 40, 0), (0, -B / 2 + 40, tb), "right", 0, on=["base_plancha"], text=f"{f(tb)}")
    ids = jids(ctx, "Marco perimetral largo", "Marco largo – marco corto")
    w_sym(p, ids[0], Vj, (0, -B / 2 + rt, tb + 3), (28, 36), other=None)
    Vj.title("DETALLE DE JUNTA PLETINA–PLANCHA (ambos lados)")
    # esquina
    kc = ["marco_largo", "marco_corto"]
    Ve = p.V(kc, "top", (x0 + 0.52 * (x1 - x0), y0, x1, y0 + 0.28 * (y1 - y0)), label="Esquina", center=(B / 2, -B / 2, tb), win=(-60, -20, 25, 60), margin=(16, 6, 40, 4), hatch=False)
    Ve.dimh((B / 2 - rt, -B / 2, tb + rh), (B / 2, -B / 2, tb + rh), "bottom", 0, on=kc, text=f"{f(rt)}")
    w_sym(p, ids[1], Ve, (B / 2, -B / 2, tb + rh), (-5, 30), kind="fillet")
    j2 = jids(ctx, "Marco corto – plancha")
    if j2:
        w_sym(p, j2[0], Vj, (0, -B / 2 + rt, tb + rh - 6), (30, 60), other=None)
    Ve.title("ESQUINA (vista en planta)")
    p.tables(ids)
    p.notes([f"Pletinas {f(rt)} × {f(rh)}; 2 largas de {f(B)} y 2 cortas de {f(B - 2 * rt)} (entre las largas); corte a sierra o plasma con borde recto.",
             "Armado: pletinas largas sobre la plancha, cortas entre ellas; puntear y soldar en secuencia simétrica; filete continuo exterior e interior.",
             f"Las esquinas se sueldan con filete exterior de esquina continuo ({J(ctx, "Marco largo – marco corto")}); el tamaño z indicado es el mínimo AWS D1.1 T5.8 por la parte más gruesa (a confirmar, el cálculo no fija el marco).",
             "El marco contiene la interfaz y protege el borde; no tiene función estructural en el cálculo."])
    p.finish_scale()
    return p.h


@pieza("mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf")
def sheet_mensula_piezas(ctx):
    g, P, BR = ctx.g, ctx.P, ctx.g.BR
    c = ctx.D["cilindros"]["horario"][0]
    E, ph = c["eye"], c["phiMean"]
    for k in ("mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf"):
        ctx.local(k, k + "_L", near=(E[0], E[1], 80), r=300, shift=(-E[0], -E[1], 0), rot=-ph)
    tb, H_, rear, Llug, Win, Wout, tc = g.tb, BR["H"], BR["rear"], BR["Llug"], BR["Win"], BR["Wout"], P["t_ch"]
    p = Pieza(ctx, ["mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf"], "MÉNSULA DE CILINDRO: MEJILLA Y OREJAS (PIEZAS)", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    third = (x1 - x0) / 3
    zt = tb + H_
    # mejilla (elevación)
    k1 = ["mensula_mejilla_L"]
    V1 = p.V(k1, "front", (x0, y0 + 0.40 * (y1 - y0), x0 + 1.15 * third, y1), label="Mejilla", margin=(20, 30, 20, 26))
    V1.dimh((-rear, -Wout / 2, tb), (P["L_ch"] - rear, -Wout / 2, tb), "bottom", 0, on=k1, text=f"{f(P['L_ch'])} ±1")
    V1.dimh((-rear, -Wout / 2, tb), (0, -Wout / 2, tb), "bottom", 1, on=k1, text=f"{f(rear)} (saliente trasera)")
    V1.dimv((P["L_ch"] - rear, -Wout / 2, tb), (P["L_ch"] - rear, -Wout / 2, zt), "right", 0, on=k1, text=f"{f(H_)} ±0,5")
    V1.title("MEJILLA (2 por ménsula)")
    V1b = p.V(k1, "top", (x0, y0, x0 + 1.15 * third, y0 + 0.40 * (y1 - y0)), label="Mejillas planta", margin=(20, 24, 20, 8))
    V1b.dimv((P["L_ch"] - rear, -Wout / 2, zt), (P["L_ch"] - rear, -Win / 2, zt), "right", 0, on=k1, text=f"{f(tc)}")
    V1b.dimv((P["L_ch"] - rear, -Win / 2, zt), (P["L_ch"] - rear, Win / 2, zt), "right", 0, on=k1, text=f"{f(Win)} (luz interior)")
    V1b.dimv((P["L_ch"] - rear, -Wout / 2, zt), (P["L_ch"] - rear, Wout / 2, zt), "right", 1, on=k1, text=f"{f(Wout)} (exterior)")
    V1b.title("MEJILLAS EN PLANTA")
    # oreja superior
    xa = x0 + 1.2 * third
    k2 = ["mensula_oreja_sup_L"]
    V2 = p.V(k2, "top", (xa, y0 + 0.40 * (y1 - y0), xa + 0.95 * third, y1), label="Oreja sup. planta", margin=(18, 30, 22, 26))
    V2.dimh((-rear, -Win / 2, zt), (Llug - rear, -Win / 2, zt), "bottom", 0, on=k2, text=f"{f(Llug)} ±0,5")
    V2.dimh((-rear, -Win / 2, zt), (0, -Win / 2, zt), "bottom", 1, on=k2, text=f"{f(rear)}")
    V2.dimv((Llug - rear, -Win / 2, zt), (Llug - rear, Win / 2, zt), "right", 0, on=k2, text=f"{f(Win)} −0,5")
    V2.dim_dia((0, 0, zt), P["d_pp"] / 2, 120, on=k2, text=tol_txt(P["d_pp"], "H9"), ext=22)
    s.centerlines(V2.P(0, 0, zt), P["d_pp"] / 2 * V2.scale, 8)
    V2.title("OREJA SUPERIOR (BAS-006)")
    V2b = p.V(k2, "front", (xa, y0, xa + 0.95 * third, y0 + 0.40 * (y1 - y0)), label="Oreja sup. elev", margin=(18, 24, 22, 8))
    V2b.dimv((Llug - rear, 0, zt - tc), (Llug - rear, 0, zt), "right", 0, on=k2, text=f"{f(tc)}")
    V2b.title("ELEVACIÓN")
    # oreja inferior
    xb = x0 + 2.2 * third
    k3 = ["mensula_oreja_inf_L"]
    hb = BR["spacer"] + tc
    V3 = p.V(k3, "top", (xb, y0 + 0.40 * (y1 - y0), x1, y1), label="Oreja inf. planta", margin=(18, 30, 22, 26))
    V3.dimh((-rear, -Win / 2, tb + hb), (Llug - rear, -Win / 2, tb + hb), "bottom", 0, on=k3, text=f"{f(Llug)} ±0,5")
    V3.dimv((Llug - rear, -Win / 2, tb + hb), (Llug - rear, Win / 2, tb + hb), "right", 0, on=k3, text=f"{f(Win)} −0,5")
    V3.dim_dia((0, 0, tb + hb), P["d_pp"] / 2, 120, on=k3, text=tol_txt(P["d_pp"], "H9"), ext=22)
    s.centerlines(V3.P(0, 0, tb + hb), P["d_pp"] / 2 * V3.scale, 8)
    V3.title("OREJA INFERIOR / BLOQUE (BAS-007)")
    V3b = p.V(k3, "front", (xb, y0, x1, y0 + 0.40 * (y1 - y0)), label="Oreja inf. elev", margin=(18, 24, 22, 8))
    V3b.dimv((Llug - rear, 0, tb), (Llug - rear, 0, tb + hb), "right", 0, on=k3, text=f"{f(hb)} (= {f(BR['spacer'])} + {f(tc)})")
    V3b.title("ELEVACIÓN")
    ids = jids(ctx, "Mejillas de ménsula", "Oreja superior", "Oreja inferior (bloque) – mejillas", "Oreja inferior (bloque) – plancha")
    if len(ids) >= 4:
        w_sym(p, ids[0], V1, (P["L_ch"] / 2 - rear, -Wout / 2, tb + 0.5), (30, -34))
        w_sym(p, ids[1], V2, ((Llug - rear) / 2, -Win / 2, zt), (30, -30))
        w_sym(p, ids[2], V3, ((Llug - rear) / 2, -Win / 2, tb + hb), (30, -30))
        w_sym(p, ids[3], V3b, ((Llug - rear) / 2, -Win / 2, tb + 0.5), (30, -30))
    s.gdt((xa + 10, y0 + 0.40 * (y1 - y0) + 2), "coax", "Ø0,10", "A") if False else None
    p.tables(ids)
    p.notes([f"Mejillas: plancha {f(tc)} × {f(H_)} × {f(P['L_ch'])}, 2 por ménsula ({int(P['n_br'])} ménsulas, {int(2 * P['n_br'])} mejillas); plasma, borde recto.",
             f"Orejas: planchas {f(Win)} (−0,5 para entrar entre mejillas con luz interior {f(Win)}) × {f(Llug)}; la inferior es un bloque {f(hb)} de espesor (pletinas apiladas o plancha gruesa).",
             f"Agujero Ø{f(P['d_pp'])} H9 de ambas orejas: mandrinar en línea DESPUÉS de soldar la ménsula, en un solo montaje; coaxialidad 0,10; eje a {f(g.hax)} ±0,5 sobre la cara de apoyo.",
             "Armar la ménsula en una plantilla sobre la base; soldadura de mejillas: secuencia alternada para limitar la distorsión (filete z de la tabla).",
             "Para la ménsula completa ver el subconjunto CON de ménsula y la lámina de la base."])
    p.finish_scale()
    return p.h


@pieza("orejas")
def sheet_orejas(ctx):
    g, P = ctx.g, ctx.P
    x, y = g.ear_pos[0]
    ang = math.degrees(math.atan2(y, x))
    ctx.local("orejas", "oreja_L", near=(x, y, g.tb + 50), r=200, shift=(-x, -y, 0), rot=-ang)
    tb, R, hE, tE, dE = g.tb, P["R_ear"], P["h_ear"], P["t_ear"], P["d_ear"]
    p = Pieza(ctx, ["orejas"], "OREJA DE IZAJE (4 UNIDADES)", fmt="A2")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["oreja_L"]
    V = p.V(on, "front", (x0, y0, x0 + 0.62 * (x1 - x0), y1), label="Perfil", center=(0, 0, tb), margin=(26, 30, 40, 26), hatch=False)
    s.line(V.P(0, 0, tb - 6), V.P(0, 0, tb + hE + R + 8), "EJE"); s.line(V.P(-R - 8, 0, tb + hE), V.P(R + 8, 0, tb + hE), "EJE")
    V.dimh((-R, tE / 2, tb), (R, tE / 2, tb), "bottom", 0, on=on, text=f"{f(2 * R)} (= 2R)")
    V.dimv((R, tE / 2, tb), (R, tE / 2, tb + hE), "right", 0, on=on, text=f"{f(hE)} ±1 (al centro del agujero)")
    V.dimv((R, tE / 2, tb), (0, tE / 2, tb + hE + R), "right", 1, on=on, text=f"{f(hE + R)} (altura total)") if False else None
    V.dim_dia((0, tE / 2, tb + hE), dE / 2, 40, on=on, text=f"Ø{f(dE)} (corte H12)", ext=26)
    V.dim_rad((0, tE / 2, tb + hE), R, 130, on=on, text=f"R{f(R)}", ext=18)
    w_sym(p, jids(ctx, "Orejas de izaje")[0], V, (R, tE / 2, tb + 3), (36, 40))
    s.roughness((V.P(-R, 0, tb + hE)[0] - 30, V.P(0, 0, tb + hE)[1] + 8), "Ra 12,5")
    V.title("PERFIL")
    Vt = p.V(on, "top", (x0 + 0.64 * (x1 - x0), y0 + 0.4 * (y1 - y0), x1, y1), label="Planta", center=(0, 0, tb), margin=(24, 24, 30, 24))
    Vt.dimv((R, -tE / 2, tb + hE), (R, tE / 2, tb + hE), "right", 0, on=on, text=f"e = {f(tE)}")
    Vt.dimh((-R, -tE / 2, tb + hE), (R, -tE / 2, tb + hE), "bottom", 0, on=on, text=f"{f(2 * R)}")
    Vt.title("PLANTA (espesor)")
    s.text(f"Bisel de la base según WPS (A DEFINIR POR EL FABRICANTE)", (x0 + 0.64 * (x1 - x0), y0 + 0.30 * (y1 - y0)), T_N, "TOP_LEFT")
    s.gdt((x0 + 0.64 * (x1 - x0), y0 + 0.2 * (y1 - y0)), "perp", "0,5", "A")
    s.text("Plano de la oreja ⟂ a la base (A)", (x0 + 0.64 * (x1 - x0) + 40, y0 + 0.2 * (y1 - y0) + 3.5), T_N, "MIDDLE_LEFT")
    p.tables(jids(ctx, "Orejas de izaje"))
    p.notes([f"Plancha e = {f(tE)}; perfil 2R × h + semicírculo R{f(R)}; agujero Ø{f(dE)} de corte (sin mecanizar, aristas esmeriladas); grillete con pasador ≤ d − g_ear = {fm(dE - P['g_ear'], 0)} mm.",
             f"Posición en la base: (±{f(P['x_lug'])}, ±{f(g.cl_lug)}) ±2, plano vertical radial hacia el centro (plano BAS-001, tabla de posiciones).",
             f"Soldadura a la base: filete z{fm(P['w_ear'], 0)} a ambos lados (L = 2R) ({J(ctx, "Orejas de izaje")}); MT 100 % y UT 100 % antes de la prueba de carga y MT después.",
             ramales_txt_short(ctx),
             f"Factor dinámico del cálculo φ_lift = {fm(P['phi_lift'], 2)}; uso: eslinga de 4 ramales con grillete certificado ASME B30.26 (a definir por catálogo)."])
    p.finish_scale()
    return p.h


def ramales_txt_short(ctx):
    g = ctx.g
    v = g.fila("Ramales: longitud mínima")
    d = math.hypot(ctx.P["x_lug"], g.cl_lug)
    L = v["dem"] if v else 2 * d
    return f"Ramales de eslinga a ≥ 60° sobre la horizontal: longitud ≥ {fm(L, 0)} mm por ramal (núcleo, fila «Ramales: longitud mínima»; distancia oreja–eje {fm(d, 0)} mm)."


@pieza("bancada")
def sheet_bancada(ctx):
    g, P, KG = ctx.g, ctx.P, ctx.g.KG
    X = P["x_g"]
    ctx.local("bancada", "bancada_L", near=(X, 0, 40), r=800, shift=(-X, 0, 0))
    tb, zb = g.tb, g.zb
    Yb = KG["Y_bed"]
    p = Pieza(ctx, ["bancada"], "BANCADA DE GUÍA CON RANURA T (2 UNIDADES)", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["bancada_L"]
    Vp = p.V(on, "top", (x0, y0 + 0.45 * (y1 - y0), x1, y1), label="Planta", center=(0, 0, zb), margin=(30, 30, 30, 26), hidden=True)
    s.line(Vp.P(0, -Yb - 20, zb), Vp.P(0, Yb + 20, zb), "EJE")
    Vp.dimh((-P["w_bed"] / 2, -Yb, zb), (P["w_bed"] / 2, -Yb, zb), "bottom", 0, on=on, text=f"{f(P['w_bed'])}")
    Vp.dimv((P["w_bed"] / 2, -Yb, zb), (P["w_bed"] / 2, Yb, zb), "right", 0, on=on, text=f"{f(2 * Yb, 1)} ±1 (largo)")
    Vp.dimh((-P["w_slot"] / 2, Yb, zb), (P["w_slot"] / 2, Yb, zb), "top", 0, on=on, text=tol_txt(P["w_slot"], "H8"))
    Vp.dimh((-P["w_tee"] / 2, Yb, zb - P["h_slot"]), (P["w_tee"] / 2, Yb, zb - P["h_slot"]), "top", 1, on=on, text=f"{f(P['w_tee'])} +0,2/0 (cabeza T, oculta)") if False else None
    Vp.title("PLANTA (ranura T pasante en todo el largo)")
    VA = p.V(on, "front", (x0, y0, x0 + 0.55 * (x1 - x0), y0 + 0.45 * (y1 - y0)), label="Corte A-A", cut=((0, 0, 0), (0, 1, 0)), margin=(130, 30, 30, 26), hatch_scale=0.6)
    s.line(VA.P(0, 0, tb - 6), VA.P(0, 0, zb + 8), "EJE")
    VA.dimh((-P["w_bed"] / 2, 0, zb), (P["w_bed"] / 2, 0, zb), "top", 0, on=on, text=f"{f(P['w_bed'])}")
    VA.dimh((-P["w_slot"] / 2, 0, zb), (P["w_slot"] / 2, 0, zb), "top", 1, on=on, text=tol_txt(P["w_slot"], "H8"))
    VA.dimh((-P["w_tee"] / 2, 0, g.zT0), (P["w_tee"] / 2, 0, g.zT0), "bottom", 0, on=on, text=f"{f(P['w_tee'])} +0,2/0")
    VA.dimv((P["w_bed"] / 2, 0, tb), (P["w_bed"] / 2, 0, zb), "right", 1, on=on, text=f"{f(P['t_bed'])} ±0,5")
    VA.dimv((P["w_slot"] / 2, 0, g.zT1), (P["w_slot"] / 2, 0, zb), "right", 0, on=on, text=f"{f(P['h_slot'])} +0,1/0")
    VA.dimv((P["w_tee"] / 2, 0, g.zT0), (P["w_tee"] / 2, 0, g.zT1), "right", 0, on=on, text=f"{f(P['h_tee'])} +0,2/0") if False else None
    VA.dimv((-P["w_tee"] / 2, 0, g.zT0), (-P["w_tee"] / 2, 0, g.zT1), "left", 0, on=on, text=f"{f(P['h_tee'])} +0,2/0")
    VA.dimv((0, 0, tb), (0, 0, g.zT0), "left", 1, on=on, text=f"{f(g.fondo)} (fondo)")
    w_sym(p, jids(ctx, "Bancada")[0], VA, (-P["w_bed"] / 2, 0, tb + 3), (-25, -25), sh=-1)
    s.roughness((VA.P(P["w_slot"] / 2 + 2, 0, zb)[0], VA.P(0, 0, zb)[1] + 3), "Ra 1,6")
    VA.title("CORTE A-A (ranura T)")
    Vd = p.V(on, "front", (x0 + 0.57 * (x1 - x0), y0, x1, y0 + 0.45 * (y1 - y0)), label="Detalle ranura", cut=((0, 0, 0), (0, 1, 0)), center=(0, 0, zb - 12), win=(-42, -22, 42, 16), margin=(20, 30, 20, 26), hatch_scale=0.3)
    Vd.dimh((-P["w_slot"] / 2, 0, zb), (P["w_slot"] / 2, 0, zb), "top", 0, on=on, text=tol_txt(P["w_slot"], "H8"))
    Vd.dimh((-P["w_tee"] / 2, 0, g.zT1), (P["w_tee"] / 2, 0, g.zT1), "bottom", 0, on=on, text=f"{f(P['w_tee'])} +0,2/0")
    Vd.dimv((P["w_tee"] / 2, 0, g.zT0), (P["w_tee"] / 2, 0, g.zT1), "right", 0, on=on, text=f"{f(P['h_tee'])}")
    Vd.dimv((P["w_slot"] / 2, 0, g.zT1), (P["w_slot"] / 2, 0, zb), "right", 1, on=on, text=f"{f(P['h_slot'])}")
    Vd.title("DETALLE DE LA RANURA T")
    gd_column(s, x0 + 0.57 * (x1 - x0), y0 + 0.45 * (y1 - y0) - 4, [("par", "0,10", "A", "Ranura paralela al eje de la bancada en todo el largo"), ("pos", "Ø0,2", "A", "Ranura coaxial con el ojal de la ménsula (±0,2)")], 12) if False else None
    p.tables(jids(ctx, "Bancada"))
    p.notes([f"Plancha {f(P['w_bed'])} × {f(P['t_bed'])} × {f(2 * Yb, 1)} (largo de carrera del patín); sobremetal 5 mm en el largo.",
             f"Ranura T pasante: cuello {f(P['w_slot'])} H8 × {f(P['h_slot'])}, cabeza {f(P['w_tee'])} × {f(P['h_tee'])}, fondo {f(g.fondo)}; mecanizar DESPUÉS de soldar y aliviar tensiones (fresado/cepillo); flancos Ra 1,6; el patín entra por el extremo.",
             f"Soldadura a la base: filete continuo z{fm(P['w_bed_f'], 0)} ambos lados, precalentar 65 °C ({J(ctx, "Bancada")}); eje de guía en x = ±{f(X)} ±0,5 respecto del centro.",
             "Paralelismo de la ranura 0,10 (datum A = eje de la bancada) y coaxialidad con el ojal ±0,2: verificar antes de montar el patín.",
             "Flancos de la ranura con grasa grafitada en montaje."])
    p.finish_scale()
    return p.h


# ====================================================================================================== MESA
def rot_key(ctx, key, new, deg):
    ctx.shapes[new] = ctx.shapes[key].rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), deg)
    ctx.mat[new] = ctx.mat.get(key, "acero")
    return new


def joint_schematic(p, x, y, t, kind, angle=60, root=3, face=2, title="", jid=None, k=2.0):
    """Esquema 2D de la preparación de junta a tope (ISO 9692-1) a escala k: espesor t, ángulo, abertura de raíz y cara de raíz. Dibuja cotas desde el registro."""
    s = p.s
    L = 40
    if not hasattr(s, "views"):
        s.views = []
    s.views.append((x - L - 30, y - 34, x + L + 70, y + t * k + 30))
    tt_, r_, c_ = t * k, root * k, face * k
    half = math.tan(math.radians(angle / 2)) * (t - face) * k
    for sd in (-1, 1):
        x0 = x + sd * r_ / 2
        if kind == "bevel" and sd == 1:
            pts = [(x0, y), (x0 + sd * L, y), (x0 + sd * L, y + tt_), (x0, y + tt_)]
        else:
            pts = [(x0, y), (x0 + sd * L, y), (x0 + sd * L, y + tt_), (x0 + sd * half + sd * r_ / 2, y + tt_), (x0, y + c_)]
            pts = [(x0, y), (x0 + sd * L, y), (x0 + sd * L, y + tt_), (x0 + sd * half, y + tt_), (x0, y + c_)]
        s.pline(pts, "VIS", closed=True)
        s.hatch_poly(pts, scale=0.4, pattern="ANSI31", angle=0 if sd < 0 else 90)
    s.dim((x - L - r_ / 2, y), (x - L - r_ / 2, y + tt_), -4, f"t = {fm(t, 0)}", "v")
    s.dim((x - r_ / 2, y - 1), (x + r_ / 2, y - 1), -9, f"r = {fm(root, 0)}", "h", outside=True)
    s.text(f"{angle}°" if kind == "V" else "45°", (x, y + tt_ + 4), T_N, "BOTTOM_CENTER")
    s.text(title, (x, y - 24), T_N + 0.5, "TOP_CENTER", bold=True)
    s.text("ESQUEMA DE LA PREPARACIÓN (ISO 9692-1), sin escala del modelo", (x, y - 30), T_N, "TOP_CENTER")
    if jid:
        a = (x + L * 0.3, y + tt_ * 0.5)
        p.h.weld(jid, (x + 4, y + tt_), (x + 38, y + tt_ + 24), prep="60°" if kind == "V" else "45°")


@pieza("mesa_plancha_sup")
def sheet_mesa_sup(ctx):
    g, P = ctx.g, ctx.P
    zt, tt = g.z0 + g.hd, g.tt
    p = Pieza(ctx, ["mesa_plancha_sup"], "MESA: PLANCHA SUPERIOR", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["mesa_plancha_sup"]
    Vt = p.V(on, "top", (x0, y0, x0 + 0.55 * (x1 - x0), y1), label="Planta", margin=(30, 30, 30, 26))
    Vt.dim_dia((0, 0, zt), g.prIn, 40, on=on, text=f"Ø{f(2 * g.prIn)} ±1.5", ext=24)
    Vt.dim_dia((0, 0, zt), g.hole_top / 2, 150, on=on, text=f"Ø{f(g.hole_top)} (pasante)", ext=24)
    Vt.dim_dia((0, 0, zt), g.cb_D / 2, 215, on=on, text=f"Ø{f(g.cb_D)} (rebaje tapa)", ext=24)
    s.centerlines(Vt.P(0, 0, zt), g.prIn * Vt.scale, 8)
    s.cut_line(Vt.P(-g.prIn - 22, 0, zt), Vt.P(g.prIn + 22, 0, zt), "A", 90)
    Vt.title("PLANTA")
    xa = x0 + 0.58 * (x1 - x0)
    Vs = p.V(on, "front", (xa, y0 + 0.35 * (y1 - y0), x1, y1), label="Corte A-A", cut=CUT_Y, center=((g.hole_top / 2 + g.prIn) / 2, 0, zt), win=(-(g.prIn - g.hole_top / 2) / 2 - 20, -tt - 8, (g.prIn - g.hole_top / 2) / 2 + 20, 14), margin=(24, 34, 30, 24), hatch_scale=0.5)
    Vs.dimv((g.prIn, 0, zt - tt), (g.prIn, 0, zt), "right", 0, on=on, text=f"{f(tt)} (t_top)")
    Vs.dimh((g.hole_top / 2, 0, zt), (g.cb_D / 2, 0, zt), "top", 0, on=on, text=f"{fm((g.cb_D - g.hole_top) / 2, 0)}") if False else None
    Vs.dimv((g.cb_D / 2, 0, zt - g.cb_t), (g.cb_D / 2, 0, zt), "left", 0, on=on, text=f"{f(g.cb_t)} (rebaje)")
    Vs.dimh((g.hole_top / 2, 0, zt - tt), (g.prIn, 0, zt - tt), "bottom", 0, on=on, text=f"{f(g.prIn - g.hole_top / 2)} (ancho radial)")
    s.roughness((Vs.P(g.hole_top / 2 + 20, 0, zt)[0], Vs.P(0, 0, zt)[1] + 3), "Ra 6,3")
    Vs.title("CORTE A-A (parcial)")
    gd_column(s, xa, y0 + 0.35 * (y1 - y0) - 4, [("flat", "0,5", None, "Planitud de la cara superior (apoyo de tapa/madera)"), ("par", "0,5", "A", "Cara superior paralela a la inferior de la mesa (A)")], 12)
    jj = jids(ctx, "Plancha superior – anillo", "Cierre de la plancha")
    w_sym(p, jj[0], Vs, (g.prIn, 0, zt - tt / 2), (40, -34), prep="60°")
    w_sym(p, jj[1], Vs, (g.prIn - 120, 0, zt), (40, 40))
    p.tables(jids(ctx, "Plancha superior – anillo", "Cierre de la plancha"))
    p.notes([f"Disco Ø{f(2 * g.prIn)} × {f(tt)}; oxicorte/plasma (ISO 9013 clase 3), con sobremetal 3 mm para empalme con el anillo superior (MES-002).",
             f"Agujero central Ø{f(g.hole_top)} y rebaje Ø{f(g.cb_D)} × {f(g.cb_t)} (apoyo de la tapa de inspección PIV-004): mecanizar en mandrinadora/fresadora; Ra 6,3.",
             f"Si el disco se obtiene de dos mitades: empalme CJP V 60° con respaldo, UT 100 %, esmerilar al ras (junta {J(ctx, "Plancha superior – anillo")} familia).",
             f"Unión con el anillo: soldadura a tope circunferencial, transición 1:4 desde t = {fm(g.tt, 0)} hasta {fm(g.tpr, 0)} ({J(ctx, "Plancha superior – anillo")}).",
             f"Soldadura de cierre sobre almas y nervios por ranuras ({J(ctx, "Cierre de la plancha")}): ubicación y cantidad A DEFINIR POR EL FABRICANTE; no modeladas en 3D.",
             "Distorsión: soldar la plancha superior en último lugar, con la mesa apoyada plana; verificar planitud 0,5."])
    p.finish_scale()
    return p.h


@pieza("mesa_anillo_sup", "mesa_anillo_inf")
def sheet_mesa_anillos(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    a0 = D["pasadores"][0]
    zt = g.z0 + g.hd
    rot_key(ctx, "mesa_anillo_sup", "ras", -a0)
    pitch = 360.0 / g.N_pin
    p = Pieza(ctx, ["mesa_anillo_sup", "mesa_anillo_inf"], "MESA: ANILLOS SUPERIOR E INFERIOR DE PASADORES (28 AGUJEROS)", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["ras"]
    Vt = p.V(on, "top", (x0, y0, x0 + 0.52 * (x1 - x0), y1), label="Planta", margin=(30, 30, 40, 26), hatch=False)
    c3 = (0, 0, zt)
    Vt.dim_dia(c3, g.Rt, 40, on=on, text=f"Ø{f(2 * g.Rt)} ±1.5 (D_top)", ext=30)
    Vt.dim_dia(c3, g.prIn, 150, on=on, text=f"Ø{f(2 * g.prIn)} (interior)", ext=30)
    s.circle(Vt.P(c3), g.R_pin * Vt.scale, "EJE")
    s.leader(Vt.P(polar(g.R_pin, 235) + (zt,)), (Vt.P(c3)[0] - 55, Vt.P(c3)[1] - 130), f"PCD Ø{f(2 * g.R_pin)} ±0,3", dot=True)
    ph = polar(g.R_pin, 0)
    Vt.note_hole((ph[0], ph[1], zt), g.d_pin / 2, 60, f"{g.N_pin} × Ø{f(g.d_pin)} H7 (+0,035/0)", ext=40, on=on)
    for sa in (0, 7, 14, 21):
        ang = (sa + 0.5) * pitch - a0 + a0
        pa = polar(g.prIn - 14, ang - a0)
        pb = polar(g.Rt + 14, ang - a0)
        s.line(Vt.P(pa + (zt,)), Vt.P(pb + (zt,)), "FANT")
    s.text(f"4 empalmes ({J(ctx, 'Empalmes de los anillos')}) a 90°, entre agujeros", (Vt.P(c3)[0] - 70, Vt.P(c3)[1] + 6), T_N, "BOTTOM_LEFT")
    s.dim_ang(Vt.P(c3), g.R_pin * Vt.scale * 0.9, 0, pitch, f"{fm(pitch, 3)}° (paso)")
    s.dim_ang(Vt.P(c3), g.R_pin * Vt.scale * 0.8, -(a0), 0, f"{fm(a0, 3)}° (arranque)") if False else None
    s.text(f"Primer agujero a {fm(a0, 3)}° del eje x (sentido antihorario); paso {fm(pitch, 3)}° ({g.N_pin} agujeros)", (Vt.ext[0], Vt.ext[3] + 14), T_N, "BOTTOM_LEFT")
    s.cut_line(Vt.P(g.prIn - 40, 0, zt), Vt.P(g.Rt + 40, 0, zt), "A", 90) if False else None
    Vt.title("PLANTA (anillo; superior e inferior idénticos)")
    # sección radial por un pasador
    xa = x0 + 0.55 * (x1 - x0)
    Vs = p.V(on, "front", (xa, y0 + 0.50 * (y1 - y0), x1, y1), label="Corte radial", cut=CUT_Y, center=(g.R_pin, 0, zt), win=(-g.R_pin + g.prIn - 40, -g.tpr - 10, g.Rt - g.R_pin + 40, 14), margin=(24, 34, 30, 24), hatch_scale=0.5)
    Vs.dimv((g.Rt, 0, zt - g.tpr), (g.Rt, 0, zt), "right", 0, on=on, text=f"{f(g.tpr)} (t_pr)")
    Vs.dimh((g.prIn, 0, zt - g.tpr), (g.Rt, 0, zt - g.tpr), "bottom", 0, on=on, text=f"{f(g.Rt - g.prIn)} (ancho)")
    Vs.dimh((g.prIn, 0, zt), (g.R_pin - g.d_pin / 2, 0, zt), "top", 0, on=on, text=f"{fm(g.R_pin - g.d_pin / 2 - g.prIn, 1)}")
    Vs.dimh((g.R_pin - g.d_pin / 2, 0, zt), (g.R_pin + g.d_pin / 2, 0, zt), "top", 1, on=on, text=tol_txt(g.d_pin, "H7"))
    Vs.dimh((g.R_pin + g.d_pin / 2, 0, zt), (g.Rt, 0, zt), "top", 0, on=on, text=f"{fm(g.Rt - g.R_pin - g.d_pin / 2, 1)}")
    s.roughness((Vs.P(g.R_pin - g.d_pin / 2, 0, zt)[0] + 3, Vs.P(0, 0, zt - g.tpr / 2)[1] - 4), "Ra 3,2")
    Vs.title("CORTE RADIAL POR UN PASADOR")
    joint_schematic(p, xa + 0.28 * (x1 - xa), y0 + 0.26 * (y1 - y0), g.tpr, "V", 60, 3, 2, f"EMPALME DEL ANILLO ({J(ctx, 'Empalmes de los anillos')})", jids(ctx, "Empalmes de los anillos")[0])
    gd_column(s, xa, y0 + 0.50 * (y1 - y0) - 4, [("pos", "Ø0,3", "A", "PCD y agujeros: posición (A = eje de la mesa)"), ("coax", "Ø0,05", None, "Agujeros superior e inferior coaxiales (mandrinar en línea)"),
                                                 ("flat", "0,3", None, "Planitud de las caras del anillo")], 12)
    jj = jids(ctx, "Plancha superior – anillo", "Plancha inferior – anillo")
    w_sym(p, jj[0], Vs, (g.prIn, 0, zt - 3), (40, 60), prep="60°")
    w_sym(p, jj[1], Vs, (g.prIn, 0, zt - g.tpr + 3), (40, -60), prep="60°")
    p.tables(jids(ctx, "Empalmes de los anillos", "Plancha superior – anillo", "Plancha inferior – anillo"))
    p.notes([f"Anillo Ø{f(2 * g.Rt)} / Ø{f(2 * g.prIn)} × {f(g.tpr)} en 4 segmentos de 90° (plasma); 2 anillos iguales (superior e inferior, MES-002 y MES-004).",
             f"{g.N_pin} agujeros Ø{f(g.d_pin)} H7 en PCD Ø{f(2 * g.R_pin)}: taladrar Ø80 en taladro radial por segmentos y MANDRINAR a Ø{f(g.d_pin)} H7 en línea con el otro anillo ya armado (plantilla común).",
             f"Posición angular: primer agujero a {fm(a0, 3)}°, paso {fm(pitch, 3)}°; los empalmes quedan entre agujeros (a {fm((0.5) * pitch, 2)}° de ellos).",
             f"Empalmes CJP V 60°, raíz 3, respaldo, UT 100 % ({J(ctx, "Empalmes de los anillos")}); esmerilar al ras antes de armar. Soldar los empalmes ANTES de unir con las planchas (J11).",
             "UT de recepción de la plancha ASTM A578 nivel B y Z35 (EN 10164) por el esfuerzo en espesor de los pasadores.",
             "Rugosidad Ra 3,2 en los agujeros; aristas rotas 1×45°."])
    p.finish_scale()
    return p.h


@pieza("mesa_plancha_inf")
def sheet_mesa_inf(ctx):
    g, P = ctx.g, ctx.P
    z0, tbo = g.z0, g.tbo
    p = Pieza(ctx, ["mesa_plancha_inf"], "MESA: PLANCHA INFERIOR (CARA DE APOYO DE LA INTERFAZ)", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["mesa_plancha_inf"]
    Vt = p.V(on, "bottom", (x0, y0, x0 + 0.55 * (x1 - x0), y1), label="Planta inferior", margin=(30, 30, 30, 26))
    ri = g.Drb / 2 if g.rebaje else g.d_bush / 2
    Vt.dim_dia((0, 0, z0), g.prIn, 40, on=on, text=f"Ø{f(2 * g.prIn)} ±1,5", ext=26)
    Vt.dim_dia((0, 0, z0), ri, 215, on=on, text=f"Ø{f(2 * ri)} (agujero pasante, rebaje del collar)" if g.rebaje else f"Ø{f(2 * ri)}", ext=40)
    s.centerlines(Vt.P(0, 0, z0), g.prIn * Vt.scale, 8)
    cs = Vt.circles(on, 2.0, 12.0)
    if cs:
        u, v, r = cs[0]
        Vt.note_hole((u, v, z0), r, 80, f"{len(cs)} × Ø{fm(2 * r, 0)} (rosca/conducto de posición; ver lámina de interfaz)", ext=40, on=on)
    s.cut_line(Vt.P(-g.prIn - 22, 0, z0), Vt.P(g.prIn + 22, 0, z0), "A", -90)
    Vt.title("VISTA INFERIOR (cara de apoyo)")
    xa = x0 + 0.58 * (x1 - x0)
    Vs = p.V(on, "front", (xa, y0 + 0.3 * (y1 - y0), x1, y1), label="Corte A-A", cut=CUT_Y, center=(ri + 120, 0, z0), win=(-200, -6, 200, tbo + 14), margin=(24, 34, 30, 24), hatch_scale=0.5)
    Vs.dimv((g.prIn, 0, z0), (g.prIn, 0, z0 + tbo), "right", 0, on=on, text=f"{f(tbo)} (t_bot)")
    Vs.dimh((ri, 0, z0), (g.prIn if False else ri + 140, 0, z0), "bottom", 0, on=on, text="") if False else None
    s.roughness((Vs.P(ri + 60, 0, z0)[0], Vs.P(0, 0, z0)[1] - 22), "Ra 3,2")
    s.text("Cara inferior (interfaz): planeada, Ra 3,2", (Vs.P(ri + 60, 0, z0)[0] + 20, Vs.P(0, 0, z0)[1] - 14), T_N, "MIDDLE_LEFT")
    Vs.title("CORTE A-A (parcial)")
    gd_column(s, xa, y0 + 0.3 * (y1 - y0) - 4, [("flat", "0,20", None, "Planitud de la cara inferior (antes de montar la interfaz)"), ("par", "0,30", "A", "Paralela a la cara superior de la mesa")], 12)
    jj = jids(ctx, "Plancha inferior – anillo")
    w_sym(p, jj[0], Vs, (g.prIn, 0, z0 + tbo / 2), (40, -36), prep="60°")
    p.tables(jids(ctx, "Plancha inferior – anillo", "Barras de tope – plancha inferior"))
    p.notes([f"Disco Ø{f(2 * g.prIn)} × {f(tbo)} (+3 mm de sobremetal para planear); oxicorte/plasma ISO 9013 clase 3.",
             f"Agujero central Ø{f(2 * ri)}: " + (f"PASANTE por el rebaje del collar (D_boss {f(g.D_boss)} + 2 × c_boss_r {fm(g.c_boss_r, 0)}); holgura radial {fm(g.c_boss_r, 0)}, axial {fm(g.c_boss_a, 0)}." if g.rebaje else "mandrinado para el buje."),
             f"Cara inferior planeada después de soldar la mesa y aliviar tensiones: planitud 0,20, Ra 3,2 (apoyo de la interfaz, {g.interfaz_nombre}).",
             f"Unión con el anillo inferior: soldadura a tope circunferencial con transición 1:4 ({J(ctx, "Plancha inferior – anillo")}). Pasadores Ø{f(g.d_pin)} del anillo: ver MES-002/004."])
    p.finish_scale()
    return p.h


@pieza("mesa_alma0", "mesa_alma1", "mesa_alma2")
def sheet_almas(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    z0 = g.z0 + g.tbo
    ks = [f"mesa_alma{i}" for i in range(len(D["almas"]))]
    p = Pieza(ctx, ks, "MESA: ALMAS ANULARES (3 ANILLOS)", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    Vt = p.V(ks, "top", (x0, y0, x0 + 0.5 * (x1 - x0), y1), label="Planta", margin=(30, 30, 30, 26), hatch=False)
    for i, r in enumerate(D["almas"]):
        Vt.dim_rad((0, 0, z0 + g.hw), r + P["t_web"] / 2, 20 + 28 * i, on=[ks[i]], text=f"R{f(r)} (eje) — A{i + 1}", ext=22 + 6 * i)
    s.centerlines(Vt.P(0, 0, z0), D["almas"][-1] * Vt.scale, 8)
    Vt.title("PLANTA DE LAS 3 ALMAS")
    xa = x0 + 0.52 * (x1 - x0)
    k0 = ks[-1]
    r = D["almas"][-1]
    Vs = p.V([k0], "front", (xa, y0 + 0.30 * (y1 - y0), x1, y1), label="Corte alma", cut=CUT_Y, center=(r, 0, z0), win=(-14, -6, 14, g.hw + 8), margin=(24, 34, 120, 24), hatch_scale=0.35)
    Vs.dimv((r + P["t_web"] / 2, 0, z0), (r + P["t_web"] / 2, 0, z0 + g.hw), "right", 0, on=[k0], text=f"{f(g.hw)} (h = h_disc − t_top − t_bot)")
    Vs.dimh((r - P["t_web"] / 2, 0, z0 + g.hw), (r + P["t_web"] / 2, 0, z0 + g.hw), "top", 0, on=[k0], text=f"{fm(P['t_web'], 0)} (t_web)")
    ids = jids(ctx, "Almas anulares", "Empalme de cada alma")
    w_sym(p, ids[0], Vs, (r + P["t_web"] / 2, 0, z0 + 2), (40, 30), other=None)
    Vs.title("CORTE DE UNA ALMA (todas iguales en sección)")
    rows = [[f"A{i + 1}", f"{ctx.code(k).replace(CODE + '-', '')}", f(2 * r_), f(r_), f(2 * math.pi * r_, 0), f"{math.ceil(2 * math.pi * r_ / 3000)} pletina(s) rolada(s)", f"{fm(g.hw, 0)} × {fm(P['t_web'], 0)}"]
            for i, (k, r_) in enumerate(zip(ks, D["almas"]))]
    sc = (x1 - xa - 4) / 150.0
    s.table(xa, y0 + 0.30 * (y1 - y0) - 8, [("Alma", 14 * sc, "C"), ("Código", 24 * sc, "L"), ("Ø eje [mm]", 22 * sc, "R"), ("R eje [mm]", 22 * sc, "R"), ("Desarrollo [mm]", 26 * sc, "R"), ("Suministro", 26 * sc, "L"), ("h × t", 16 * sc, "C")],
            rows, h=T_S, title="DESARROLLO DE LAS ALMAS (pletina rolada)")
    joint_schematic(p, xa + 40, y0 + 0.08 * (y1 - y0), P["t_web"], "V", 60, 2, 1, "") if False else None
    if len(ids) > 1:
        w_sym(p, ids[1], Vs, (r - P["t_web"] / 2, 0, z0 + g.hw / 2), (60, 30), prep="60°")
    p.tables(ids)
    p.notes([f"Pletina {fm(P['t_web'], 0)} × {f(g.hw)} rolada a los radios de eje R = {', '.join(f(x) for x in D['almas'])} mm; desarrollo = 2πR.",
             f"Cada alma tiene 1 empalme a tope V 60° ({J(ctx, "Empalme de cada alma")}), UT 100 %, esmerilado al ras; ubicar el empalme entre nervios.",
             "Altura h = h_disc − t_top − t_bot ±0,5: cortar a medida y verificar con plantilla antes de armar la mesa.",
             f"Filete a las planchas superior e inferior z{fm(P['w_web'], 0)} ambos lados continuo ({J(ctx, "Almas anulares")}). " + ("El tamaño supera el máximo AISC J2.2b (t − 2): pendiente del calculista (GEN-009)." if P["w_web"] > P["t_web"] - 2 else ""),
             "Las almas son continuas; los nervios se cortan entre almas (ver MES-008…010)."])
    p.finish_scale()
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
    p = Pieza(ctx, ks, "MESA: NERVIOS RADIALES (TRAMOS ENTRE ALMAS)", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    rows = []
    hh = (y1 - y0) / len(ks)
    for i, (k, kl) in enumerate(zip(ks, loc)):
        bb = ctx.shapes[kl].BoundingBox()
        L = bb.xlen
        V = p.V([kl], "front", (x0, y1 - (i + 1) * hh, x0 + 0.62 * (x1 - x0), y1 - i * hh), label=f"Nervio {i + 1}", margin=(20, 30, 30, 28))
        V.dimh((bb.xmin, bb.ymin, z0), (bb.xmax, bb.ymin, z0), "bottom", 0, on=[kl], text=f"{fm(L, 1)} ±0,5 (R{fm(bb.xmin, 1)}–R{fm(bb.xmax, 1)})")
        V.dimv((bb.xmax, bb.ymin, z0), (bb.xmax, bb.ymin, z0 + g.hw), "right", 0, on=[kl], text=f"{f(g.hw)} ±0,5")
        V.title(f"NERVIO TRAMO {i + 1} ({ctx.code(k).replace(CODE + '-', '')}) — {int(P['N_rib'])} unidades")
        rows.append([f"{i + 1}", ctx.code(k).replace(CODE + "-", ""), fm(bb.xmin, 1), fm(bb.xmax, 1), fm(L, 1), f"{fm(g.hw, 0)} × {fm(P['t_rib'], 0)}", f"{int(P['N_rib'])}"])
    jn = jids(ctx, "Nervios radiales")
    if jn:
        w_sym(p, jn[0], V, (bb.xmax, bb.ymin, z0 + g.hw / 2), (30, 40))
    xa = x0 + 0.64 * (x1 - x0)
    sc = (x1 - xa - 4) / 150.0
    s.table(xa, y1 - 6, [("Tramo", 14 * sc, "C"), ("Código", 22 * sc, "L"), ("R interior", 22 * sc, "R"), ("R exterior", 22 * sc, "R"), ("Largo", 24 * sc, "R"), ("h × t", 26 * sc, "C"), ("Cant", 14 * sc, "C")], rows, h=T_S, title="TRAMOS DE NERVIO")
    ang = D["nervios"]
    arows = [[f"{i + 1}", fm(a, 3) + "°"] for i, a in enumerate(ang)]
    half = (len(arows) + 1) // 2
    s.table(xa, y1 - 70, [("N°", 14 * sc, "C"), ("Ángulo [°]", 40 * sc, "R")], arows[:half], h=T_S, title="POSICIÓN ANGULAR DE LOS NERVIOS (desde +x, antihorario)")
    s.table(xa + 70 * sc, y1 - 70 - (T_N + 0.5) * 1.6, [("N°", 14 * sc, "C"), ("Ángulo [°]", 40 * sc, "R")], arows[half:], h=T_S)
    p.tables(jids(ctx, "Nervios radiales"))
    p.notes([f"Pletina {fm(P['t_rib'], 0)} × {f(g.hw)}; {int(P['N_rib'])} nervios por tramo, 3 tramos (entre cubo, almas A1…A3 y borde R_rib = {f(P['R_rib'])}).",
             "Corte por plasma anidado en plancha; largos de la tabla (entre caras de almas/cubo); ajuste con 1–2 mm de holgura de armado.",
             f"Filete z{fm(P['w_web'], 0)} ambos lados contra planchas y almas, continuo ({J(ctx, "Nervios radiales")}); armar sobre la plancha inferior con plantilla angular ±0,1°.",
             "Nervios y almas se sueldan a la plancha inferior ANTES de cerrar con la superior."])
    p.finish_scale()
    return p.h


@pieza("mesa_cubo")
def sheet_cubo(ctx):
    g, P = ctx.g, ctx.P
    z0 = g.z0 + g.tbo
    p = Pieza(ctx, ["mesa_cubo"], "MESA: CUBO", fmt="A2")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["mesa_cubo"]
    zt = z0 + g.hw
    Vt = p.V(on, "top", (x0, y0, x0 + 0.45 * (x1 - x0), y1), label="Planta", margin=(24, 26, 24, 26))
    Vt.dim_dia((0, 0, zt), P["D_hub"] / 2, 40, on=on, text=f"Ø{f(P['D_hub'])}", ext=14)
    Vt.dim_dia((0, 0, zt), g.d_bush / 2, 215, on=on, text=tol_txt(g.d_bush, "H7"), ext=14)
    s.centerlines(Vt.P(0, 0, zt), P["D_hub"] / 2 * Vt.scale, 6)
    Vt.title("PLANTA")
    Vs = p.V(on, "front", (x0 + 0.47 * (x1 - x0), y0, x1, y1), label="Corte A-A", cut=CUT_Y, margin=(22, 28, 40, 26), hatch_scale=0.6)
    Vs.dimv((P["D_hub"] / 2, 0, z0), (P["D_hub"] / 2, 0, zt), "right", 0, on=on, text=f"{f(g.hw)} ±0,5")
    Vs.dimh((-g.d_bush / 2, 0, zt), (g.d_bush / 2, 0, zt), "top", 0, on=on, text=tol_txt(g.d_bush, "H7"))
    Vs.dimh((-P["D_hub"] / 2, 0, zt), (P["D_hub"] / 2, 0, zt), "top", 1, on=on, text=f"Ø{f(P['D_hub'])}")
    if g.rebaje and g.hHub > 0:
        Vs.dimh((-g.Drb / 2, 0, z0), (g.Drb / 2, 0, z0), "bottom", 0, on=on, text=f"Ø{f(g.Drb)} (rebaje del collar)")
        Vs.dimv((-g.Drb / 2, 0, z0), (-g.Drb / 2, 0, z0 + g.hHub), "left", 0, on=on, text=f"{fm(g.hHub, 1)} (rebaje)")
    s.roughness((Vs.P(-g.d_bush / 2, 0, zt - g.hw / 2)[0] + 2, Vs.P(0, 0, zt - g.hw / 2)[1] - 3), "Ra 1,6")
    gd_column(s, Vs.ext[0], Vs.ext[1] - 24, [("coax", "Ø0,05", "A", "Ø%s H7 coaxial con el eje de la mesa (A)" % f(g.d_bush)), ("perp", "0,10", "A", "Caras inferior y superior ⟂ al eje")], 12)
    Vs.title("CORTE A-A")
    jc = jids(ctx, "Cubo")
    if jc:
        w_sym(p, jc[0], Vs, (P["D_hub"] / 2, 0, z0), (40, -34), prep="45°")
    p.tables(jids(ctx, "Cubo"))
    p.notes([f"Anillo Ø{f(P['D_hub'])} / Ø{f(g.d_bush)} × {f(g.hw)} de plancha gruesa o tubo, corte a llama; agujero Ø{f(g.d_bush)} H7 y rebaje Ø{f(g.Drb)} en mandrinadora (sin torno vertical).",
             f"Ajuste del buje (PIV-002): {f(g.d_bush)} H7 / s6, prensado. Holgura radial del collar c_boss_r = {fm(g.c_boss_r, 0)} y axial c_boss_a = {fm(g.c_boss_a, 0)} mm (núcleo).",
             f"Soldar a las planchas inferior y superior ({J(ctx, "Cubo")}) y luego mandrinar H7 con la mesa armada y aliviada; Ra 1,6.",
             "Perpendicularidad de las caras 0,10; coaxialidad del agujero con el eje de la mesa 0,05."])
    p.finish_scale()
    return p.h


@pieza("pasadores")
def sheet_pasador(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    xy = polar(g.R_pin, D["pasadores"][0])
    ctx.local("pasadores", "pin1", near=(xy[0], xy[1], g.z0 + g.hd / 2), r=60, shift=(-xy[0], -xy[1], 0))
    z0, zt, r = g.z0, g.z0 + g.hd, g.d_pin / 2
    p = Pieza(ctx, ["pasadores"], f"MESA: PASADOR DE EMPUJE Ø{f(g.d_pin)} ({g.N_pin} UNIDADES)", fmt="A2")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["pin1"]
    V = p.V(on, "front", (x0, y0, x0 + 0.6 * (x1 - x0), y1), label="Elevación", margin=(30, 30, 60, 26), hatch=False)
    s.line(V.P(0, 0, z0 - 8), V.P(0, 0, zt + 8), "EJE")
    V.dimv((r, 0, z0 + g.ch_pin), (r, 0, zt - g.ch_pin), "right", 0, on=on, text="") if False else None
    V.dimv((r - g.ch_pin, 0, z0), (r - g.ch_pin, 0, zt), "right", 0, on=on, text=f"{f(g.hd)} ±0,1")
    V.dimh((-r, 0, zt - g.ch_pin), (r, 0, zt - g.ch_pin), "top", 0, on=on, text=tol_txt(g.d_pin, "m6"))
    V.dimh((r - g.ch_pin, 0, zt), (r, 0, zt - g.ch_pin), "top", 1, on=on, text=f"{fm(g.ch_pin, 0)}×45°", outside=True)
    V.dimv((r - g.ch_pin, 0, zt), (r, 0, zt - g.ch_pin), "right", 1, on=on, text=f"{fm(g.ch_pin, 0)}", outside=True)
    V.dimv((r, 0, z0 + g.tbo), (r, 0, z0 + g.tbo + g.hw), "left", 0, on=on, text=f"{fm(g.hw, 0)} (altura libre entre planchas)") if False else None
    # franja de contacto: de la cara inferior de la mesa hasta h_c de la uña
    zc0, zc1 = g.zc - P["dog_h"] / 2, g.zc + P["dog_h"] / 2
    s.line(V.P(-r - 6, 0, zc0), V.P(r + 6, 0, zc0), "TRAT"); s.line(V.P(-r - 6, 0, zc1), V.P(r + 6, 0, zc1), "TRAT")
    V.dimv((-r, 0, zc0), (-r, 0, zc1), "left", 0, on=on, text=f"{f(P['dog_h'])} (franja templada)")
    V.note_pt((0, 0, zt), (36, 22), f"Rosca M20 prof. 40 (retención con perno ISO 4762 M20×45)", on=on) if False else None
    s.leader(V.P(0, 0, zt), (V.P(0, 0, zt)[0] + 40, V.P(0, 0, zt)[1] + 24), "Rosca M20-6H prof. 40 (perno ISO 4762 M20×45 cl. 10.9)", dot=True)
    s.roughness((V.P(r, 0, z0 + g.hd / 2)[0] + 30, V.P(0, 0, z0 + g.hd / 2)[1]), "Ra 0,8")
    gd_column(s, x0 + 0.62 * (x1 - x0), y1 - 8, [("cyl", "0,02", None, "Cilindricidad del Ø%s m6" % f(g.d_pin)), ("run", "0,03", "A", "Excentricidad respecto del eje (A = Ø%s)" % f(g.d_pin)), ("perp", "0,05", "A", "Caras extremas ⟂ al eje")], 12)
    s.datum((V.P(0, 0, z0)[0], V.P(0, 0, z0)[1] - 3), "A", up=False) if False else None
    V.title("ELEVACIÓN")
    p.tables()
    p.notes([f"Barra Ø{f(g.d_pin + 5)} laminada/rectificada; torno horizontal o rectificado externo: Ø{f(g.d_pin)} m6 ({iso286.fmt_dev(g.d_pin, 'm6')} mm), Ra 0,8; largo {f(g.hd)} ±0,1.",
             f"Tratamiento: bonificado y temple por inducción de la franja de contacto ≥ 55 HRC (Fy_sup {f(P['Fy_surf'])} MPa del cálculo), profundidad efectiva ≥ {fm(g.z_hard, 1)} mm; Fy ≥ {f(P['Fy_pin'])} MPa (34CrNiMo6+QT, EN 10083-3).",
             f"Chaflán {fm(g.ch_pin, 0)}×45° en ambos extremos (ISO 13715). Rosca M20-6H prof. 40 en un extremo (ISO 262), perno ISO 4762 M20×45 cl. 10.9; torque propuesto en GEN (PROPUESTA, A CONFIRMAR POR EL CALCULISTA).",
             f"Ajuste en los anillos {f(g.d_pin)} H7/m6 (transición, desmontable). Montar con grasa; sin soldadura.",
             f"Marcar con punzón el número del pasador (1…{g.N_pin}) y la colada en el extremo roscado; 10 % de dureza superficial por lote."])
    p.finish_scale()
    return p.h


# ====================================================================================================== PIV / ACC
def revolve_sheet(ctx, key, titulo, d, L, z0, code, ch, notes, extra=None, fmt="A2", tolcode=None):
    """Pieza de revolución con eje z: elevación con diámetro, largo y chaflán, vista de extremo."""
    p = Pieza(ctx, [key], titulo, fmt=fmt)
    s = p.s
    x0, y0, x1, y1 = p.views
    on = [key]
    r = d / 2
    V = p.V(on, "front", (x0, y0, x0 + 0.62 * (x1 - x0), y1), label="Elevación", margin=(30, 30, 60, 30), hatch=False)
    s.line(V.P(0, 0, z0 - 8), V.P(0, 0, z0 + L + 8), "EJE")
    V.dimv((r - ch, 0, z0), (r - ch, 0, z0 + L), "right", 0, on=on, text=f"{fm(L, 1)} ±0,1")
    V.dimh((-r, 0, z0 + L - ch), (r, 0, z0 + L - ch), "top", 0, on=on, text=tol_txt(d, code))
    V.dimh((r - ch, 0, z0 + L), (r, 0, z0 + L - ch), "top", 1, on=on, text=f"{fm(ch, 0)}×45°", outside=True)
    V.dimv((r - ch, 0, z0 + L), (r, 0, z0 + L - ch), "right", 1, on=on, text=f"{fm(ch, 0)}", outside=True)
    s.roughness((V.P(r, 0, z0 + L / 2)[0] + 24, V.P(0, 0, z0 + L / 2)[1]), "Ra 0,8")
    if extra:
        extra(p, V, s)
    V.title("ELEVACIÓN")
    Vt = p.V(on, "top", (x0 + 0.64 * (x1 - x0), y0, x1, y0 + 0.45 * (y1 - y0)), label="Extremo", margin=(24, 30, 24, 26), hatch=False)
    Vt.dim_dia((0, 0, z0 + L), r - ch, 40, on=on, text=f"Ø{fm(d - 2 * ch, 0)} (cara plana)", ext=14) if False else None
    Vt.dim_dia((0, 0, z0 + L - ch), r, 40, on=on, text=f"Ø{fm(d, 0)}", ext=14)
    Vt.title("VISTA DE EXTREMO")
    p.tables()
    p.notes(notes)
    p.finish_scale()
    return p.h


@pieza("pivote")
def sheet_pivote_pieza(ctx):
    g, P = ctx.g, ctx.P

    def extra(p, V, s):
        zA, zB = g.tb, g.tb + g.h_boss
        s.line(V.P(-P["D_piv"] / 2 - 6, 0, zA), V.P(P["D_piv"] / 2 + 6, 0, zA), "TRAT")
        s.line(V.P(-P["D_piv"] / 2 - 6, 0, zB), V.P(P["D_piv"] / 2 + 6, 0, zB), "TRAT")
        V.dimv((-P["D_piv"] / 2, 0, zA), (-P["D_piv"] / 2, 0, zB), "left", 0, on=["pivote"], text=f"{fm(zB - zA, 0)} (zona en plancha base + collar, H7/p6)")
        V.dimv((-P["D_piv"] / 2, 0, 0), (-P["D_piv"] / 2, 0, zA), "left", 1, on=["pivote"], text="") if False else None
        gd_column(s, V.ext[0] + 40, V.ext[1] - 16, [("cyl", "0,02", None, "Cilindricidad del Ø%s p6" % f(P["D_piv"])), ("perp", "0,05", "A", "Caras extremas ⟂ al eje (A = Ø%s)" % f(P["D_piv"]))], 12) if False else None
    return revolve_sheet(ctx, "pivote", f"PIVOTE Ø{f(P['D_piv'])} p6", P["D_piv"], g.L_piv, 0.0, "p6", g.ch_piv, [
        f"Barra redonda Ø{f(P['D_piv'] + 5)} laminada/rectificada; torneado/rectificado externo en torno horizontal: Ø{f(P['D_piv'])} p6 ({iso286.fmt_dev(P['D_piv'], 'p6')} mm), Ra 0,8; largo {fm(g.L_piv, 1)}.",
        f"Material: SEGÚN CÁLCULO Fy ≥ {f(P['Fy_piv'])} MPa, grado A DEFINIR POR EL FABRICANTE (bonificado). Certificado 3.1; UT de la barra.",
        f"Ajuste en plancha base y collar: {f(P['D_piv'])} H7/p6 (aprieto {iso286.fit(P['D_piv'], 'H7', 'p6')['cmin']}…{iso286.fit(P['D_piv'], 'H7', 'p6')['cmax']} µm): prensa o contracción con hielo seco. Ajuste en el buje: f7/F7.",
        f"Chaflanes {fm(g.ch_piv, 0)}×45° en ambos extremos (ISO 13715). Perpendicularidad de las caras extremas 0,05; cilindricidad 0,02.",
        "Retención axial del pivote: ajuste sin soldadura ni tope (A DEFINIR POR EL CALCULISTA: el cálculo no verifica la extracción axial)."], extra=extra)


@pieza("buje", "tapa_ret", "tapa_insp")
def sheet_buje_tapas(ctx):
    g, P = ctx.g, ctx.P
    ks = [k for k in ("buje", "tapa_ret", "tapa_insp") if ctx.m.get(k)]
    p = Pieza(ctx, ks, "PIVOTE: BUJE AUTOLUBRICADO Y TAPAS (RETENEDORA E INSPECCIÓN)", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    hh = (y1 - y0) / 3
    spec = {"buje": (g.z_bush0, P["L_bush"], g.d_bush, P["D_piv"]), "tapa_ret": (g.L_piv, g.cap_t, g.cap_D, None), "tapa_insp": (g.z0 + g.hd - g.cb_t, g.cb_t, g.cb_D - 2, None)}
    for i, k in enumerate(ks):
        zb_, L_, D_, d_ = spec[k]
        zt = zb_ + L_
        yb = y1 - (i + 1) * hh
        Vt = p.V([k], "top", (x0, yb, x0 + 0.40 * (x1 - x0), y1 - i * hh), label=k + " planta", margin=(24, 28, 24, 26))
        Vt.dim_dia((0, 0, zt), D_ / 2, 40, on=[k], text=f"Ø{f(D_)}", ext=14)
        if d_:
            Vt.dim_dia((0, 0, zt), d_ / 2, 215, on=[k], text=tol_txt(d_, "F7") if k == "buje" else f"Ø{f(d_)}", ext=14)
        s.centerlines(Vt.P(0, 0, zt), D_ / 2 * Vt.scale, 6)
        Vt.title(f"{ctx.code(k).replace(CODE + '-', '')} — PLANTA")
        Vs = p.V([k], "front", (x0 + 0.42 * (x1 - x0), yb, x1, y1 - i * hh), label=k + " corte", cut=CUT_Y, margin=(24, 28, 80, 26), hatch_scale=0.35)
        Vs.dimv((D_ / 2, 0, zb_), (D_ / 2, 0, zt), "right", 0, on=[k], text=f"{fm(L_, 1)} ±0,2")
        Vs.dimh((-D_ / 2, 0, zt), (D_ / 2, 0, zt), "top", 0, on=[k], text=(tol_txt(D_, "s6") if k == "buje" else f"Ø{f(D_)} ±0,1"))
        if d_:
            Vs.dimh((-d_ / 2, 0, zb_), (d_ / 2, 0, zb_), "bottom", 0, on=[k], text=tol_txt(d_, "F7"))
        s.roughness((Vs.P(D_ / 2, 0, zb_ + L_ / 2)[0] + 8 if False else Vs.P(0, 0, zb_)[0] + 6, Vs.P(0, 0, zb_ + L_)[1] + 10), "Ra 1,6") if False else None
        Vs.title(f"{ctx.code(k).replace(CODE + '-', '')} — CORTE")
    p.tables()
    p.notes([f"Buje autolubricado Ø{f(g.d_bush)} / Ø{f(P['D_piv'])} × {f(P['L_bush'])}: comercial o a medida (A DEFINIR POR CATÁLOGO; aleación y lubricante según proveedor; p_bush = {fm(P['p_bush'], 0)} MPa y μ = {fm(P['mu_bush'], 2)} del cálculo). Ø exterior s6 prensado en el cubo H7; Ø interior F7 con el pivote f7.",
             f"Montaje del buje: arranca g_bush = {fm(P['g_bush'], 0)} mm sobre el collar (z = {fm(g.z_bush0, 1)} desde la cara inferior de la base).",
             f"Tapa retenedora Ø{f(g.cap_D)} × {f(g.cap_t)}: fijada con 4 × M10×25 ISO 10642 10.9 al extremo del pivote; Ra 3,2; oxicorte/plasma y mecanizado de agujeros en taladro radial (agujeros: A DEFINIR en la lámina del pivote, el cálculo no los fija).",
             f"Tapa de inspección Ø{f(g.cb_D - 2)} × {f(g.cb_t)} (apoyo en rebaje de la plancha superior), 6 × M10 avellanados; sin función estructural.",
             "Material de las tapas: ASTM A572 Gr.50 (Fy del cálculo), certificado 3.1."])
    p.finish_scale()
    return p.h


@pieza("cilindro")
def sheet_cilindro(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    c = D["cilindros"]["antihorario"][0]
    X, ye, yr = c["x"], c["eye"][1], c["rodEngage"][1]
    ctx.local("cilindro", "cil1", near=(X, (ye + yr) / 2, g.zc), r=500)
    zc = g.zc
    p = Pieza(ctx, ["cilindro"], "CILINDRO HIDRÁULICO DE DOBLE EFECTO (ELEMENTO COMERCIAL — DIMENSIONES DE INTERFAZ)", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["cil1"]
    V = p.V(on, "top", (x0, y0 + 0.30 * (y1 - y0), x1, y1), label="Planta", margin=(30, 40, 30, 30), hatch=False)
    s.line(V.P(X, ye + 90, zc), V.P(X, yr - 90, zc), "EJE")
    V.dim((X, ye, zc), (X, yr, zc), 0, f"L ojal–ojal = {fm(abs(ye - yr), 1)} (vástago extendido a la posición de empuje)", "v", on=on, virt_a=P["d_pp"] / 2, virt_b=P["d_pp"] / 2) if False else None
    V.dimv((X, ye, zc), (X, yr, zc), "right", 0, on=on, text=f"{fm(abs(ye - yr), 1)} (entre ejes de ojales, posición de empuje)", virt_a=P["d_pp"] / 2, virt_b=P["d_pp"] / 2)
    ym = (ye + yr) / 2
    yb_m = (ye + c["dir"] * P["e_body"] + c["rodRetracted"][1] - c["dir"] * P["c_rod"]) / 2
    V.dimh((X - P["D_body"] / 2, yb_m, zc), (X + P["D_body"] / 2, yb_m, zc), "bottom", 0, on=on, text=f"Ø{f(P['D_body'])} (cuerpo)")
    V.dimh((X - P["d_rod"] / 2, yr + 130 * c["dir"], zc), (X + P["d_rod"] / 2, yr + 130 * c["dir"], zc), "bottom", 1, on=on, text=f"Ø{f(P['d_rod'])} (vástago)") if False else None
    V.dim_dia((X, ye, zc), 52.5, 40, on=on, text="Ø105 (ojal)", ext=30)
    V.dim_dia((X, ye, zc), P["d_pp"] / 2, 150, on=on, text=f"Ø{f(P['d_pp'])} (rótula/ojal)", ext=30)
    V.title("PLANTA DEL CILINDRO (posición de empuje)")
    rows = [["Diámetro de camisa (D_bore)", f"{f(P['D_bore'])} mm"], ["Diámetro de vástago (d_rod)", f"{f(P['d_rod'])} mm"], ["Carrera (stroke)", f"{f(P['stroke'])} mm"],
            ["Largo ojal–ojal retraído (L0)", f"{f(P['L0'])} mm"], ["Cuerpo exterior (D_body)", f"{f(P['D_body'])} mm"], ["Presión nominal p_rated", f"{f(P['p_rated'])} psi = {fm(P['p_rated'] * 0.0689476, 0)} bar"],
            ["Presión de alivio p_relief", f"{f(P['p_relief'])} bar"], ["Ojales", f"b_eye = {f(P['b_eye'])} mm; Ø{f(P['d_pp'])} (pasador {f(P['d_pp'])} f8)"], ["Masa de catálogo", f"{fm(P['m_cyl'], 0)} kg c/u"],
            ["Fabricante / código", "A DEFINIR POR CATÁLOGO (confirmar L0 y geometría de extremos)"]]
    s.table(x0, y0 + 0.28 * (y1 - y0), [("Característica requerida", 120, "L"), ("Valor (del cálculo)", 260, "L")], rows, h=T_S, title="ESPECIFICACIÓN DE COMPRA")
    p.tables()
    p.notes(["Elemento comercial: este plano fija solo las dimensiones de interfaz que el cálculo exige; el diseño interno es del fabricante.",
             f"Prueba hidráulica a 1,5 × {f(P['p_relief'])} bar con certificado de fábrica (EN 10204 3.1 / certificado de prueba).",
             "Ojales con rótula esférica autolubricada; sellos NBR/PU según el fabricante; protección de vástago (cromo duro) y pintura del fabricante.",
             f"Pasadores de articulación Ø{f(P['d_pp'])} f8 con placa de retención (ACC-005/006).", "Capacidad y velocidad: ver memoria de cálculo (capítulo de cilindros y bomba)."])
    p.finish_scale()
    return p.h


@pieza("patin")
def sheet_patin(ctx):
    g, P, KG = ctx.g, ctx.P, ctx.g.KG
    c = ctx.D["cilindros"]["antihorario"][0]
    X, yr = c["x"], c["rodEngage"][1]
    ctx.local("patin", "patin_L", near=(X, yr + 200, g.zc), r=600, shift=(-X, -yr, 0))
    ws, rear, front, zsh, zb, zc = P["w_s"], KG["rear"], KG["front"], g.z_shoe, g.zb, g.zc
    yF = P["l_p"] - g.d_pin / 2
    p = Pieza(ctx, ["patin"], "PATÍN GUIADO CON LENGÜETA T Y MARCO DE BOCA (2 UNIDADES)", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["patin_L"]
    V = p.V(on, "top", (x0, y0 + 0.42 * (y1 - y0), x0 + 0.5 * (x1 - x0), y1), label="Planta", center=(0, 100, zsh), hidden=True, margin=(30, 30, 50, 26))
    s.line(V.P(0, -rear - 20, zsh), V.P(0, front + 20, zsh), "EJE")
    V.dimv((ws / 2, -rear, zsh), (ws / 2, front, zsh), "right", 0, on=on, text=f"{f(KG['L_s'], 1)} ±1 (largo total)")
    V.dimv((ws / 2, -rear, zsh), (ws / 2, 0, zsh), "right", 1, on=on, text=f"{fm(rear, 1)}")
    V.dimh((-ws / 2, -rear, zsh), (ws / 2, -rear, zsh), "bottom", 0, on=on, text=f"{f(ws)} ±0,5")
    V.dim_dia((0, 0, zsh), P["d_pp"] / 2, 20, text=tol_txt(P["d_pp"], "H9") + " (pasador del vástago)", on=on, ext=30)
    V.title("PLANTA (alojamiento y ojal en trazo)")
    yc = yF - P["dog_b"] / 2
    xa = x0 + 0.52 * (x1 - x0)
    VF = p.V(on, "front", (xa, y0 + 0.30 * (y1 - y0), x1, y1), label="Corte F-F", cut=((0, yc, 0), (0, 1, 0)), center=(0, 0, zb), win=(-200, -55, 130, 150), margin=(24, 34, 30, 26), hatch_scale=0.5)
    s.line(VF.P(0, yc, g.zT0 - 6), VF.P(0, yc, zsh + 14), "EJE")
    VF.dimh((-ws / 2, yc, zsh), (ws / 2, yc, zsh), "top", 0, on=on, text=f"{f(ws)}")
    VF.dimv((ws / 2, yc, zb), (ws / 2, yc, zsh), "right", 0, on=on, text=f"{f(g.Hs)} (sobre la bancada)")
    VF.dimh((-g.neck_w / 2, yc, zb - 3), (g.neck_w / 2, yc, zb - 3), "bottom", 0, on=on, text=tol_txt(g.neck_w, "f7") if False else f"{f(g.neck_w)} f7")
    VF.dimh((-g.head_w / 2, yc, g.zT0 + 1), (g.head_w / 2, yc, g.zT0 + 1), "bottom", 1, on=on, text=f"{f(g.head_w)} h11")
    VF.dimv((g.head_w / 2, yc, g.zT0 + 1), (g.head_w / 2, yc, g.zT1 - 1), "right", 1, on=on, text=f"{f(g.head_h)}", outside=True)
    pe = KG["pocketEnd"] - X
    VF.dimv((pe + CL1, yc, g.pk_bot), (pe + CL1, yc, g.pk_top), "left", 0, on=on, text=f"{f(P['dog_h'] + 2)} H9 (alojamiento de la uña)")
    s.roughness((VF.P(-ws / 2 + 10, yc, zsh)[0], VF.P(0, yc, zsh)[1] + 14), "Ra 1,6")
    VF.title("CORTE F-F (por el alojamiento de la uña)")
    gd_column(s, xa, y0 + 0.30 * (y1 - y0) - 4, [("par", "0,05", "A", "Cara inferior de la lengüeta ∥ a la cara de apoyo (A)"), ("perp", "0,05", "A", "Alojamiento de la uña ⟂ a la cara de empuje")], 12)
    p.tables()
    p.notes([f"Pieza única sin soldadura, desde bloque de plancha gruesa a llama con sobremetal 5 mm; desbaste y alojamientos en mandrinadora/fresadora; Ø{f(P['d_pp'])} {('H9')} en taladro radial.",
             f"Lengüeta T: cuello {f(g.neck_w)} f7 en ranura {f(P['w_slot'])} H8; cabeza {f(g.head_w)} × {f(g.head_h)} en {f(P['w_tee'])} × {f(P['h_tee'])}, 1 mm de juego por lado.",
             f"Alojamiento de la uña {f(P['dog_b'] + 2)} × {f(P['dog_h'] + 2)} H9; tapa {f(zsh - g.pk_top)} y fondo {f(g.pk_bot - zb)} sobre la bancada (mínimo t_pk = {f(P['t_pk'])}).",
             f"Marco de boca e = {f(P['t_fw'])}; inset {f(KG['inset'])}; boca en x = {f(KG['mouthX'] - X, 1)} desde el eje de la guía.",
             f"Material: SEGÚN CÁLCULO Fy ≥ {f(P['Fy_shoe'])} MPa, grado A DEFINIR POR EL FABRICANTE; certificado 3.1. Reacción de guía a calado {f(ctx.DV['Rguide'], 1)} kN (núcleo)."])
    p.finish_scale()
    return p.h


@pieza("una")
def sheet_una(ctx):
    g, P, KG = ctx.g, ctx.P, ctx.g.KG
    c = ctx.D["cilindros"]["antihorario"][0]
    yF = c["pinStart"][1] - c["dir"] * g.d_pin / 2
    ctx.local("una", "una_L", near=(KG["tipX"] + 100, yF - 40, g.zc), r=300, shift=(-KG["tipX"], -yF, 0))
    L, b, hd_, zc = g.paw_L, P["dog_b"], P["dog_h"], g.zc
    zt = zc + hd_ / 2
    p = Pieza(ctx, ["una"], "UÑA DE EMPUJE (CARA PLANA TEMPLADA, CHAFLÁN DE RETORNO) (2 UNIDADES)", fmt="A2")
    s = p.s
    x0, y0, x1, y1 = p.views
    on = ["una_L"]
    V = p.V(on, "top", (x0, y0 + 0.5 * (y1 - y0), x1, y1), label="Planta", center=(0, -b / 2, zt), margin=(30, 30, 30, 26), hatch=False)
    s.line(V.P(-15, -b / 2, zt), V.P(L + 15, -b / 2, zt), "EJE")
    V.dimh((0, 0, zt), (L, 0, zt), "top", 0, on=on, text=f"{fm(L, 1)} ±0,2")
    V.dimv((L, -b, zt), (L, 0, zt), "right", 0, on=on, text=f"{f(b)} f8")
    V.dimh((0, -b + g.ch_dy, zt), (g.ch_dx, -b, zt), "bottom", 0, on=on, text=f"{fm(g.ch_dx, 1)} (chaflán, β = {fm(P['beta_ch'], 0)}°)")
    V.dimv((0, -b + g.ch_dy, zt), (0, 0, zt), "left", 0, on=on, text=f"{fm(b - g.ch_dy, 1)} (punta)")
    s.line(V.P(0, 5, zt), V.P(L, 5, zt), "TRAT")
    s.text("Cara de empuje templada ≥ 55 HRC", (V.P(L * 0.3, 5, zt)[0], V.P(0, 5, zt)[1] + 3), T_N, "BOTTOM_LEFT")
    s.roughness((V.P(L * 0.5, 0, zt)[0], V.P(0, 0, zt)[1] + 14), "Ra 0,8")
    V.title("PLANTA")
    VE = p.V(on, "front", (x0, y0, x1, y0 + 0.5 * (y1 - y0)), label="Elevación", center=(0, 0, zc), margin=(30, 30, 40, 26), hatch=False)
    VE.dimv((L, 0, zc - hd_ / 2), (L, 0, zc + hd_ / 2), "right", 0, on=on, text=f"{f(hd_)} f8")
    VE.dimh((0, 0, zc + hd_ / 2), (L, 0, zc + hd_ / 2), "top", 0, on=on, text=f"{fm(L, 1)}")
    for zz, zz2 in ((zc + hd_ / 2, zc + hd_ / 2 - RELIEF), (zc - hd_ / 2, zc - hd_ / 2 + RELIEF)):
        s.line(VE.P(0, 0, zz2), VE.P(L, 0, zz2), "TRAT")
        VE.dimv((L, 0, zz), (L, 0, zz2), "right", 1, on=on, text=f"{fm(RELIEF, 0)} (alivio)", outside=True)
    VE.title("ELEVACIÓN (cara de empuje)")
    gd_column(s, x0, y0 + 0.5 * (y1 - y0) - 36 if False else y0 + 24, [("flat", "0,05", None, "Cara de empuje plana"), ("perp", "0,05", "A", "Cara de empuje ⟂ a la base (A)")], 12) if False else None
    p.tables()
    p.notes([f"Forja o bloque; 34CrNiMo6+QT (EN 10083-3), Re ≥ {f(P['Fy_dog'])} MPa medido en la propia forja, certificado 3.1; UT EN 10228-3.",
             temple_txt(P) + f" (fila «Profundidad mínima de temple» del núcleo: ≥ {fm(g.z_hard, 1)} mm); revenido; MT de la cara.",
             alivio_txt(P) + f": {fm(RELIEF, 0)} mm desde el borde superior e inferior de la cara; perfil y caída A DEFINIR por el calculista.",
             "Rectificar la cara templada después del temple (rectificadora plana, sin torno). Planitud 0,05; Ra 0,8.",
             f"Ajuste en el alojamiento del patín {f(b)} H9/f8 × {f(hd_)} H9/f8; retorno radial {fm(KG['travel'], 1)} mm; resorte comercial (A DEFINIR POR CATÁLOGO).",
             "Aristas 1×45° salvo la cara de empuje (0,5×45°)."])
    p.finish_scale()
    return p.h


@pieza("pasador_vastago", "pasador_ojal")
def sheet_pasadores_art(ctx):
    g, P, KG, BR = ctx.g, ctx.P, ctx.g.KG, ctx.g.BR
    c = ctx.D["cilindros"]["antihorario"][0]
    X, ye, yr = c["x"], c["eye"][1], c["rodEngage"][1]
    ctx.local("pasador_ojal", "po1", near=(X, ye, g.tb + 80), r=200, shift=(-X, -ye, 0))
    ctx.local("pasador_vastago", "pv1", near=(X, yr, g.zc), r=200, shift=(-X, -yr, 0))
    p = Pieza(ctx, ["pasador_vastago", "pasador_ojal"], f"PASADORES DE ARTICULACIÓN Ø{f(P['d_pp'])} f8 (VÁSTAGO Y OJAL TRASERO)", fmt="A2")
    s = p.s
    x0, y0, x1, y1 = p.views
    r = P["d_pp"] / 2
    for i, (kk, kl) in enumerate((("pasador_vastago", "pv1"), ("pasador_ojal", "po1"))):
        bb = ctx.shapes[kl].BoundingBox()
        z0_, z1_ = bb.zmin, bb.zmax
        cell = (x0 + i * 0.5 * (x1 - x0), y0 + 0.30 * (y1 - y0), x0 + (i + 1) * 0.5 * (x1 - x0), y1)
        V = p.V([kl], "front", cell, label=kl, margin=(24, 30, 60, 28), hatch=False)
        s.line(V.P(0, 0, z0_ - 6), V.P(0, 0, z1_ + 6), "EJE")
        V.dimv((r - g.ch_pp, 0, z0_), (r - g.ch_pp, 0, z1_), "right", 0, on=[kl], text=f"{fm(z1_ - z0_, 1)} ±0,2")
        V.dimh((-r, 0, z1_ - g.ch_pp), (r, 0, z1_ - g.ch_pp), "top", 0, on=[kl], text=tol_txt(P["d_pp"], "f8"))
        V.dimh((r - g.ch_pp, 0, z1_), (r, 0, z1_ - g.ch_pp), "top", 1, on=[kl], text=f"{fm(g.ch_pp, 0)}×45°", outside=True)
        s.roughness((V.P(r, 0, (z0_ + z1_) / 2)[0] + 24, V.P(0, 0, (z0_ + z1_) / 2)[1]), "Ra 0,8")
        V.title(f"{ctx.code(kk).replace(CODE + '-', '')} — {'PASADOR DEL VÁSTAGO (patín)' if i == 0 else 'PASADOR DEL OJAL TRASERO (ménsula)'}")
    p.tables()
    p.notes([f"Barra rectificada Ø{f(P['d_pp'] + 5)}; corte y chaflanes {fm(g.ch_pp, 0)}×45° en torno horizontal; Ø{f(P['d_pp'])} f8 ({iso286.fmt_dev(P['d_pp'], 'f8')} mm), Ra 0,8.",
             f"Material: SEGÚN CÁLCULO Fy ≥ {f(P['Fy_pp'])} MPa, grado A DEFINIR POR EL FABRICANTE (bonificado, 28–34 HRC de referencia); certificado 3.1.",
             f"Ajuste con los ojales H9/f8 (juego {iso286.fit(P['d_pp'], 'H9', 'f8')['cmin']}…{iso286.fit(P['d_pp'], 'H9', 'f8')['cmax']} µm), con grasa grafitada.",
             "Retención: placa y tornillo (comercial, A DEFINIR POR CATÁLOGO); ranura de retención A DEFINIR por el fabricante.",
             "Largos: pasador del vástago desde z de la ménsula del patín; pasador del ojal sobre la ménsula (BR.H + 15)."])
    p.finish_scale()
    return p.h


# ====================================================================================================== INTERFAZ
def sector_local(ctx, key):
    g = ctx.g
    th = 360.0 / ctx.m.get(key).qty if key == "int_uhmw" else 360.0 / (int(ctx.P["bz_npad"]) if (key == "int_bronce" and g.conf == 3) else g.n_sec)
    a = th / 2 if key != "int_uhmw" else th / 2 + (th / 4.0 if g.n_seg == g.n_sec else 0.0)
    nk = key + "_s1"
    ctx.local_ang(key, nk, a, th)
    return nk, th


def int_sector_sheet(ctx, key, titulo, face, z_of):
    """Lámina de un sector (o pastilla/lámina) de interfaz: planta con radios, muesca del tope, tornillos, ranuras, graseras y patrón de tapones; corte por la bisectriz."""
    g, P, m = ctx.g, ctx.P, ctx.m
    lay = m.layout
    pt = m.get(key)
    nk, th = sector_local(ctx, key)
    ks = [key] + ([k for k in ("int_tapones",) if key == "int_bronce" and m.get(k)])
    p = Pieza(ctx, ks, titulo, fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    bb = ctx.shapes[nk].BoundingBox()
    z0_, z1_ = bb.zmin, bb.zmax
    t = z1_ - z0_
    ztop = z1_
    on = [nk]
    V = p.V(on, "top", (x0, y0, x0 + 0.62 * (x1 - x0), y1), label="Planta del sector", margin=(40, 40, 50, 30), hatch=False)
    c3 = (0, 0, ztop)
    s.line(V.P(g.Ri - 10, 0, ztop), V.P(g.Ro + 10, 0, ztop), "EJE")
    V.dim_rad(c3, g.Ro, 3, on=on, text=f"R{fm(g.Ro, 0)} (R_o)", ext=30)
    V.dim_rad(c3, g.Ri, 0.5, on=on, text=f"R{fm(g.Ri, 0)} (R_i)", ext=30)
    Ln = lay.L_base if face == "top" else lay.L_mesa
    if g.removable and Ln and key != "int_uhmw":
        nb = lay.b_tope + 2
        V.dimh((g.r_u - Ln / 2, nb / 2, ztop), (g.r_u + Ln / 2, nb / 2, ztop), "top", 0, on=on, text=f"{fm(Ln, 1)} (muesca del tope)")
        V.dimv((g.r_u + Ln / 2, -nb / 2, ztop), (g.r_u + Ln / 2, nb / 2, ztop), "right", 0, on=on, text=f"{fm(nb, 0)} (b_tope + 2)")
        V.dimh((g.Ri, 0, ztop), (g.r_u - Ln / 2, 0, ztop), "bottom", 0, on=on, text=f"{fm(g.r_u - Ln / 2 - g.Ri, 1)}") if False else None
        V.dimh((g.Ri, -nb / 2, ztop), (g.r_u, -nb / 2, ztop), "bottom", 0, on=on, text=f"{fm(g.r_u - g.Ri, 1)} (a r_u = {fm(g.r_u, 1)})") if False else None
    cs = V.circles(on, 2.9, lay.dk / 2 + 0.1)
    if cs:
        sc_ = sorted({round(u, 1) for (u, v, r) in cs if abs(v) < 1})
        rr = lambda r: round(r, 2)
        u, v, r = cs[0]
        V.note_hole((u, v, ztop), r, 90, f"{len(sc_)} × M{fm(lay.d_tor, 0)} ISO 10642 (avellanado Ø{fm(lay.dk, 0)}, pasante Ø{fm(lay.d_clear, 1)}) a r = " + " y ".join(fm(x, 1) for x in sc_), ext=46, on=on)
    gs = V.circles(on, 2.9, 3.1)
    if m.info.get("grease_pts") and gs:
        u, v, r = [q for q in gs if abs(q[2] - 3.0) < 0.1][0]
        V.note_hole((u, v, ztop), r, 40, f"{g.n_greaser} × Ø6 conducto de engrase axial (graseras en el canto de la mesa)", ext=40, on=on) if face == "bot" else None
    if key == "int_bronce":
        pl = V.circles(on, P["bz_plug_d"] / 2 - 0.05, P["bz_plug_d"] / 2 + 0.05)
        if pl:
            u, v, r = pl[0]
            V.note_hole((u, v, ztop), r, 120, f"{len(pl)} tapones de grafito Ø{fm(P['bz_plug_d'], 0)} por sector, paso {fm(P['bz_plug_p'], 0)} (malla triangular)", ext=40, on=on)
    V.title("PLANTA DEL SECTOR (bisectriz sobre el eje x)")
    xa = x0 + 0.64 * (x1 - x0)
    Vs = p.V(on, "front", (xa, y0 + 0.45 * (y1 - y0), x1, y1), label="Corte por la bisectriz", cut=CUT_Y, center=(g.r_u, 0, (z0_ + z1_) / 2), win=(-130, -t - 10, 130, t + 10), margin=(30, 36, 30, 26), hatch_scale=0.35)
    Vs.dimv((g.r_u + 125 if False else g.Ri + 3, 0, z0_), (g.Ri + 3, 0, z1_), "left", 0, on=on, text=f"{fm(t, 1)} (e)")
    s.roughness((Vs.P(g.r_u - 120, 0, z1_)[0], Vs.P(0, 0, z1_)[1] + 3), "Ra 0,4 (cara deslizante)") if face == "top" else s.roughness((Vs.P(g.r_u - 120, 0, z0_)[0], Vs.P(0, 0, z0_)[1] - 20), "Ra 0,4 (cara deslizante)")
    Vs.title("CORTE POR LA BISECTRIZ")
    # tabla de parámetros
    rows = [["Espesor e", f"{fm(t, 1)} mm"], ["Sectores", f"{pt.qty} de {fm(th, 3)}°"], ["Junta en frío", f"{fm(g.junta('uhmw' if key == 'int_uhmw' else 'disc'), 2)} mm"],
            ["Radios R_i / R_o", f"{fm(g.Ri, 0)} / {fm(g.Ro, 0)} mm"], ["Material", pt.material], ["Masa unitaria", f"{f(pt.mass_unit, 2)} kg"]]
    if g.removable and key != "int_uhmw":
        rows.insert(3, ["Muesca del tope", f"{fm(lay.b_tope + 2, 0)} × {fm(Ln, 1)} centrada en r_u = {fm(g.r_u, 1)}"])
    s.table(xa, y0 + 0.45 * (y1 - y0) - 10, [("Parámetro", 40, "L"), ("Valor", 130, "L")], rows, h=T_S, title="PARÁMETROS DEL SECTOR (JSON)")
    p.tables()
    p.notes([pt.process, pt.obs or "", f"Cara deslizante: {'Ra 0,4 rectificada/lapeada' if key != 'int_uhmw' else 'sin mecanizado de precisión'}; sobreespesor de relapeado {fm(P['ss_allow'], 1)} mm (ss_allow).",
             "Junta entre sectores de ancho constante j (S04): bordes paralelos a la bisectriz; chaflán de alivio en el canto de la muesca = a_inf del tope.",
             f"Tolerancias: espesor e ±0,1; radios ±0,5; planitud de la cara deslizante 0,05; posición de la muesca ±0,2 respecto de la bisectriz.",
             f"Tratamiento: {pt.tratamiento}."])
    p.finish_scale()
    return p.h


def _mk(key, titulo, face):
    def fn(ctx):
        return int_sector_sheet(ctx, key, titulo, face, None)
    fn.__name__ = "sheet_" + key
    PLAN.append((fn.__name__, [key] + (["int_tapones"] if key == "int_bronce" else []), fn))
    globals()[fn.__name__] = fn


_mk("int_disco_base", "INTERFAZ: DISCO DE LA BASE (SECTOR)", "top")
_mk("int_disco_mesa", "INTERFAZ: DISCO DE LA MESA (SECTOR)", "bot")
_mk("int_cara", "INTERFAZ: DISCO DURO / 2.ª PLACA (SECTOR)", "bot")
_mk("int_bronce", "INTERFAZ: PLACA DE BRONCE CON TAPONES DE GRAFITO (SECTOR / PASTILLA)", "top")
_mk("int_uhmw", "INTERFAZ: LÁMINA DE UHMW-PE (SECTOR)", "top")


def tope_sheet(ctx, key, titulo, side):
    """Barra de tope: vista de la barra y detalle de junta con el sector (cotas a_sup, a_inf, h_c, b, L, filetes)."""
    g, P, m = ctx.g, ctx.P, ctx.m
    lay = m.layout
    tp = {"int_tope_base": lay.tp_base, "int_tope_mesa": lay.tp_mesa, "int_tope_uhmw": lay.tp_uhmw}[key]
    pt = m.get(key)
    th = 360.0 / pt.qty
    a = th / 2 if key != "int_tope_uhmw" else (th / 4.0 if g.n_seg == g.n_sec else 0.0) + 0.0
    nk = key + "_b1"
    ctx.local_ang(key, nk, a if key != "int_tope_uhmw" else a, 4 if key != "int_tope_uhmw" else 4)
    if nk not in ctx.shapes:
        return None
    sector = {"int_tope_base": "int_disco_base" if m.get("int_disco_base") else "int_bronce", "int_tope_mesa": "int_disco_mesa" if m.get("int_disco_mesa") else "int_cara", "int_tope_uhmw": "int_uhmw"}[key]
    ctx.local_ang(sector, sector + "_t1", a if key != "int_tope_uhmw" else a, th * 1.0)
    plate = "mesa_plancha_inf" if key == "int_tope_mesa" else "base_plancha"
    rot_key(ctx, plate, plate + "_t", -a)
    p = Pieza(ctx, [key], titulo, fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    bb = ctx.shapes[nk].BoundingBox()
    L, b = tp["L"], P["b_tope"]
    zb0, zb1 = bb.zmin, bb.zmax
    on = [nk]
    V = p.V(on, "top", (x0, y0 + 0.55 * (y1 - y0), x0 + 0.5 * (x1 - x0), y1), label="Barra planta", margin=(30, 30, 30, 26), hatch=False)
    V.dimh((g.r_u - L / 2 if key != "int_tope_uhmw" else bb.xmin, -b / 2, zb1), (g.r_u + L / 2 if key != "int_tope_uhmw" else bb.xmax, -b / 2, zb1), "bottom", 0, on=on, text=f"{fm(L, 1)} (L)")
    V.dimv((bb.xmax, -b / 2, zb1), (bb.xmax, b / 2, zb1), "right", 0, on=on, text=f"{fm(b, 0)} (b)")
    V.title("BARRA — PLANTA")
    Ve = p.V(on, "front", (x0 + 0.5 * (x1 - x0), y0 + 0.55 * (y1 - y0), x1, y1), label="Barra elevación", margin=(30, 30, 40, 26), hatch=False)
    Ve.dimv((bb.xmax, -b / 2, zb0), (bb.xmax, -b / 2, zb1), "right", 0, on=on, text=f"{fm(tp['h_barra'], 1)} (h = t − a_sup)")
    Ve.title("BARRA — ELEVACIÓN")
    # detalle de junta
    ks = [plate + "_t", sector + "_t1", nk]
    zc_ = (zb0 + zb1) / 2
    xc = (bb.xmin + bb.xmax) / 2
    Vj = p.V(ks, "right", (x0, y0, x0 + 0.62 * (x1 - x0), y0 + 0.55 * (y1 - y0)), label="Detalle de junta", cut=CUT_X, center=(xc, 0, zc_), win=(-(b / 2 + 34), -tp["t"] - 14, b / 2 + 34, tp["t"] + 14),
             margin=(40, 36, 90, 28), hatch_scale=0.25, mat={plate + "_t": "acero", sector + "_t1": ctx.mat.get(sector, "acero"), nk: "acero"})
    z_bar_top = zb1 if key != "int_tope_mesa" else zb0
    z_sec_face = (zb0 + (zb1 - zb0) + 0) if False else None
    Vj.dimh((xc, -b / 2, zc_), (xc, b / 2, zc_), "top", 0, on=[nk], text=f"{fm(b, 0)} (b)")
    Vj.dimv((xc, 0, zb0), (xc, 0, zb1), "right", 0, on=[nk], text=f"{fm(tp['h_barra'], 1)}")
    Vj.title("DETALLE DE JUNTA (corte por el centro de la barra)")
    ids = jids(ctx, "Barras de tope – plancha base") if key == "int_tope_base" else jids(ctx, "Barras de tope – plancha inferior") if key == "int_tope_mesa" else jids(ctx, "Barras del rebaje UHMW")
    if ids:
        w_sym(p, ids[0], Vj, (xc, -b / 2, zb0 + (0 if key != "int_tope_mesa" else 0) + 1), (-40, -30), sh=-1)
    rows = [["a_sup (cara de la barra bajo la cara deslizante)", fm(tp["a_sup"], 1)], ["a_inf (chaflán 45° del canto del sector, = w_tope + 1)", fm(tp["a_inf"], 1)], ["h_c (contacto útil)", fm(tp["h_c"], 1)],
            ["h_c mín. (núcleo)", fm(tp["h_c_min"], 1)], ["b (ancho de la barra)", fm(b, 0)], ["L (largo de la barra)", fm(tp["L"], 1)], ["h barra = t − a_sup", fm(tp["h_barra"], 1)],
            ["w_tope (filete)", f"z{fm(P['w_tope'], 0)} (mín. {fm(tp['w_min'], 0)})"], ["Espesor del sector t", fm(tp["t"], 1)]]
    xa = x0 + 0.64 * (x1 - x0)
    s.table(xa, y0 + 0.55 * (y1 - y0) - 8, [("Parámetro del tope (interfazGeom.topes)", 120, "L"), ("[mm]", 50, "R")], rows, h=T_S, title="GEOMETRÍA DEL TOPE")
    p.tables(ids)
    p.notes([f"Barra {fm(b, 0)} × {f(L, 1)} × {fm(tp['h_barra'], 1)} de {pt.material.split(',')[0]}; corte a sierra, extremos a escuadra; {pt.qty} unidades.",
             f"Soldar a {'la plancha base' if key == 'int_tope_base' else 'la plancha inferior de la mesa' if key == 'int_tope_mesa' else 'el disco inoxidable de la base'} con 2 filetes (frente y dorso) z{fm(P['w_tope'], 0)} continuos; el filete cabe bajo el chaflán a_inf = {fm(tp['a_inf'], 0)}.",
             "Soldar ANTES del alivio y del rectificado de las caras deslizantes; posición angular ±0,1° (bisectriz del sector).",
             f"El sector va con muesca de {fm(b + 2, 0)} mm (1 mm de holgura por lado); la barra queda a a_sup = {fm(tp['a_sup'], 1)} bajo la cara deslizante (contacto útil h_c = {fm(tp['h_c'], 1)}, mínimo {fm(tp['h_c_min'], 1)})."])
    p.finish_scale()
    return p.h


def _mkt(key, titulo, side):
    def fn(ctx):
        return tope_sheet(ctx, key, titulo, side)
    fn.__name__ = "sheet_" + key
    PLAN.append((fn.__name__, [key], fn))
    globals()[fn.__name__] = fn


_mkt("int_tope_base", "INTERFAZ: BARRA DE TOPE DE LA BASE Y DETALLE DE JUNTA", "base")
_mkt("int_tope_mesa", "INTERFAZ: BARRA DE TOPE DE LA MESA Y DETALLE DE JUNTA", "mesa")
_mkt("int_tope_uhmw", "INTERFAZ: BARRA DEL REBAJE UHMW Y DETALLE DE JUNTA", "uhmw")


@pieza("madera", "madera_anillo")
def sheet_madera(ctx):
    g, P = ctx.g, ctx.P
    zw0, tW = g.z0 + g.hd, P["t_wood"]
    p = Pieza(ctx, ["madera", "madera_anillo"], "CUBIERTA DE MADERA: ANILLO DE CONTENCIÓN Y TABLONES", fmt="A1")
    s = p.s
    x0, y0, x1, y1 = p.views
    ks = ["madera", "madera_anillo"]
    V = p.V(ks, "top", (x0, y0, x0 + 0.58 * (x1 - x0), y1), label="Planta", margin=(30, 30, 40, 26), hatch=False)
    c3 = (0, 0, zw0 + tW)
    V.dim_dia(c3, g.Rt, 40, on=["madera_anillo"], text=f"Ø{f(P['D_top'])}", ext=30)
    V.dim_dia(c3, g.Rt - g.t_ring, 150, on=["madera"], text=f"Ø{f(2 * (g.Rt - g.t_ring))} (tablones)", ext=30)
    V.dim_dia(c3, g.cb_D / 2, 215, on=["madera"], text=f"Ø{f(g.cb_D)} (abertura central)", ext=30)
    xs = -g.Rt + 200
    while xs < g.Rt:
        a_ = V.P(xs, -math.sqrt(max(g.Rt ** 2 - xs ** 2, 0)) * 0.98, zw0 + tW); b_ = V.P(xs, math.sqrt(max(g.Rt ** 2 - xs ** 2, 0)) * 0.98, zw0 + tW)
        s.line(a_, b_, "FANT")
        xs += 200
    V.title("PLANTA (tablones de 200 mm, esquema)")
    xa = x0 + 0.6 * (x1 - x0)
    Vs = p.V(ks, "front", (xa, y0 + 0.4 * (y1 - y0), x1, y1), label="Corte", cut=CUT_Y, center=(g.Rt - 80, 0, zw0 + tW / 2), win=(-110, -tW - 6, 30, tW + 12), margin=(24, 34, 30, 26), hatch_scale=0.3, mat={"madera": "madera", "madera_anillo": "acero"})
    Vs.dimv((g.Rt, 0, zw0), (g.Rt, 0, zw0 + tW), "right", 0, on=["madera_anillo"], text=f"{f(tW)} (t_wood)")
    Vs.dimh((g.Rt - g.t_ring, 0, zw0 + tW), (g.Rt, 0, zw0 + tW), "top", 0, on=["madera_anillo"], text=f"{fm(g.t_ring, 0)} (t_ring)")
    Vs.title("CORTE RADIAL (anillo y tablón)")
    ids = jids(ctx, "Anillo de contención")
    if ids:
        w_sym(p, ids[0], Vs, (g.Rt, 0, zw0 + 1), (30, -40))
    p.tables(ids)
    p.notes([f"Tablones de madera dura de e = {f(tW)} mm y 200 mm de ancho (adoptado por el mandante), densidad ≥ {f(P['rho_wood'])} kg/m³, p adm. {fm(P['p_wood'], 1)} MPa (NCh1198; confirmar con el proveedor).",
             f"{g.N_pin} bolsillos Ø{f(g.washer_D + 4)} × 31 sobre las cabezas de los pernos de los pasadores (S06, PROVISORIO); fijación de los tablones A DEFINIR.",
             f"Anillo: pletina {fm(g.t_ring, 0)} × {f(tW)} rolada a Ø{f(P['D_top'])}, empalme CJP, soldada a la plancha superior con filete ambos lados (J-anillo); material A572 Gr.50.",
             "Certificado de clasificación estructural de la madera del proveedor."])
    p.finish_scale()
    return p.h
