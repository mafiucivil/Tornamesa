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
