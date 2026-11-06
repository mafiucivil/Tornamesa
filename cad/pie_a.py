"""Láminas de fabricación: base, collar, marco, ménsula, izaje y bancada."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *


@pieza("base_plancha")
def sheet_base_plancha(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    B, tb = g.B, g.tb
    p = Pieza(ctx, ["base_plancha"], "PLANCHA BASE: CONTORNO, AGUJERO CENTRAL Y POSICIONES", fmt="auto")
    s = p.s
    on = ["base_plancha"]
    xl, cl, xg = P["x_lug"], g.cl_lug, P["x_g"]
    ghosts = ["marco_largo", "marco_corto", "collar", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "orejas", "bancada"]

    def planta(V, p):
        ghost(p, V, ghosts)
        s.line(V.P(-B / 2 - 70, 0, tb), V.P(B / 2 + 70, 0, tb), "EJE"); s.line(V.P(0, -B / 2 - 70, tb), V.P(0, B / 2 + 70, tb), "EJE")
        V.chain_h([(-B / 2, B / 2, tb), (-xg, B / 2, tb), (-xl, B / 2, tb), (0, B / 2, tb), (xl, B / 2, tb), (xg, B / 2, tb), (B / 2, B / 2, tb)], "top", 0, on=on)
        V.dimh((-B / 2, B / 2, tb), (B / 2, B / 2, tb), "top", 1, on=on, text=f"{f(B)} ±2")
        V.chain_v([(-B / 2, -B / 2, tb), (-B / 2, -cl, tb), (-B / 2, 0, tb), (-B / 2, cl, tb), (-B / 2, B / 2, tb)], "left", 0, on=on)
        V.dimv((-B / 2, -B / 2, tb), (-B / 2, B / 2, tb), "left", 1, on=on, text=f"{f(B)} ±2")
        V.dim_dia((0, 0, tb), P["D_piv"] / 2, 215, text=f"Ø{f(P['D_piv'])} H7 (+0,035/0), pasante", on=on, ext=30)
        s.circle(V.P(0, 0, tb), g.D_boss / 2 * V.scale, "FANT")
        s.leader((V.P(0, 0, tb)[0] + g.D_boss / 2 * V.scale * 0.707, V.P(0, 0, tb)[1] - g.D_boss / 2 * V.scale * 0.707), (V.P(0, 0, tb)[0] + 40, V.P(0, 0, tb)[1] - 40), f"Collar Ø{f(g.D_boss)} (BAS-002), concéntrico", dot=True)
        s.circle(V.P(0, 0, tb), (P["D_top"] + 20) / 2 * V.scale, "FANT")
        s.leader((V.P(0, 0, tb)[0] + (P["D_top"] + 20) / 2 * V.scale * 0.707, V.P(0, 0, tb)[1] - (P["D_top"] + 20) / 2 * V.scale * 0.707),
                 (V.P(0, 0, tb)[0] + 62, V.P(0, 0, tb)[1] - 120), f"Zona de apoyo de la interfaz Ø{f(P['D_top'] + 20)}: planitud 0,20", dot=True)
        cs = V.circles(["base_plancha"], 2.0, 4.5)
        if cs:
            n = len(cs)
            u, v, r = cs[0]
            V.note_hole((u, v, tb), r, 100, f"{n} × M{fm(r * 2, 0)} (rosca en el respaldo; ver tabla de agujeros)", ext=40, on=on)
        p.cut_mark("planta", "A", (-B / 2 - 38, 0, tb), (B / 2 + 38, 0, tb), 90)
        p.cut_mark("planta", "D", (B / 2 - 150, B / 2 + 30, tb), (B / 2 - 150, B / 2 - 150, tb), 0) if False else None

    p.vs("planta", on, "top", lv=(2, 0, 0, 2), draw=planta, auto=False, title="PLANTA DE LA PLANCHA BASE", w=2.0, extra=(0, 0, 0, 0))

    def corte(V, p):
        s.line(V.P(0, 0, -10), V.P(0, 0, g.tb + g.h_boss + 10), "EJE")
        V.dim_dia((0, 0, tb / 2), P["D_piv"] / 2, 20, text=f"Ø{f(P['D_piv'])} H7", on=on, ext=22)
        V.dimv((V.shapes["base_plancha"].BoundingBox().xmax * 0 + 150, 0, 0), (150, 0, tb), "right", 0, on=on, text=f"{f(tb)} (t_base) ±0,5") if False else None
        s.roughness((V.P(-70, 0, tb)[0], V.P(0, 0, tb + g.h_boss)[1] + 6), "Ra 3,2 (cara de apoyo)")
        s.roughness((V.P(P["D_piv"] / 2 + 2, 0, tb / 2)[0] + 22, V.P(0, 0, tb / 2)[1] - 40), "Ra 1,6 (agujero)")
        s.datum((V.P(-250, 0, 0)[0], V.P(0, 0, 0)[1] - 1), "A", up=False)
        s.gdt((V.P(120, 0, 0)[0], V.P(0, 0, 0)[1] - 34), "perp", "0,05", "A")
        s.text("Eje Ø%s H7 perpendicular a la cara de apoyo" % f(P["D_piv"]), (V.P(120, 0, 0)[0] + 24, V.P(0, 0, 0)[1] - 34), T_N, "MIDDLE_LEFT")
        w_sym(p, jids(ctx, "Collar")[0], V, (g.D_boss / 2, 0, tb + 1), (45, 30), all_round=True)
    p.vs("corte", ["base_plancha", "collar"], "front", cut=CUT_Y, win=(-290, -4, 290, tb + g.h_boss + 12), lv=(1, 2, 1, 1), draw=corte, title="CORTE A-A (central, collar soldado)", mat={"base_plancha": "acero", "collar": "acero"},
         auto=dict(on=["base_plancha", "collar"], fits={P["D_piv"]: "H7"}), w=2.0, hs=0.5)
    # detalle del borde: pletina del marco soldada a la plancha, ambos lados
    rt, rh = P["rim_t"], P["rim_h"]

    def det_borde(V, p):
        ids = jids(ctx, "Marco perimetral largo")
        if ids:
            w_sym(p, ids[0], V, (0, -B / 2 + rt, tb + 3), (28, 36))
    p.vs("borde", ["base_plancha", "marco_largo"], "right", cut=CUT_X, center=(0, -B / 2, tb), win=(-30, -tb - 6, 40, rh + 10), lv=(1, 1, 1, 1), draw=det_borde, title="DETALLE B: BORDE CON MARCO PERIMETRAL",
         auto=dict(on=["base_plancha", "marco_largo"], text={}), mat={"base_plancha": "acero", "marco_largo": "acero"}, maxs=2.0, w=1.0)
    # detalle de la esquina en planta
    p.vs("esquina", ["base_plancha", "marco_largo", "marco_corto"], "top", center=(B / 2, -B / 2, tb), win=(-70, -10, 20, 70), lv=(1, 1, 1, 1), title="DETALLE C: ESQUINA (PLANTA)", hatch=False,
         auto=dict(on=["base_plancha", "marco_largo", "marco_corto"]), maxs=2.0, w=1.0)
    # tabla de posiciones
    rows = []
    for i, (ex, ey) in enumerate(g.ear_pos):
        rows.append([f"O{i + 1} oreja de izaje", f(ex), f(ey), "—", f"plano radial {fm(math.degrees(math.atan2(ey, ex)), 2)}°"])
    for grp in ("horario", "antihorario"):
        for k, c in enumerate(D["cilindros"][grp]):
            rows.append([f"M{len(rows) - 3} ménsula {grp}", f(c["eye"][0], 1), f(c["eye"][1], 1), f(c["phiMean"], 1) + "°", "eje del ojal"])
    for sx in (1, -1):
        rows.append(["Bancada (eje de guía)", f(sx * P["x_g"]), "0", "90°", f"largo {f(g.KG['L_bed'], 1)}"])
    rows.append(["Collar / agujero H7", "0", "0", "—", f"Ø{f(g.D_boss)} / Ø{f(P['D_piv'])}"])
    p.table_block("POSICIONES DE LAS PIEZAS SOLDADAS (origen: centro de la plancha)", [("Elemento", 60, "L"), ("x [mm]", 22, "R"), ("y [mm]", 22, "R"), ("Ángulo", 18, "C"), ("Observación", 52, "L")], rows)
    p.tables(jids(ctx, "Collar", "Marco perimetral largo", "Marco corto – plancha"))
    nz = [
        f"Plancha {f(B)} × {f(B)} × {f(tb)} de {p.p0.material.split(',')[0]}; sobrematerial de corte 5 mm por borde, recortar a medida después del alivio. Corte por oxicorte/plasma con tolerancia ISO 9013 clase 3.",
        f"Agujero central Ø{f(P['D_piv'])} H7: mandrinar plancha y collar en un solo montaje (mandrinadora) después de soldar el collar y aliviar tensiones; Ra 1,6; perpendicular a la cara de apoyo 0,05.",
        f"Cara superior en la zona Ø{f(P['D_top'] + 20)}: planeada (planitud 0,20 / Ra 3,2); sin pintura en esa zona. Compensar la distorsión de la soldadura con contraflecha o secuencia simétrica.",
        "Posiciones de las piezas soldadas (tabla): marcar con granete y trazado antes de armar; tolerancia ±1 salvo indicación.",
        "Soldaduras de la base: ver CON-006 y el programa de soldaduras (GEN-007). Alivio de tensiones 590–620 °C después de soldar y antes del mecanizado final.",
        "La plancha NO lleva anclajes: equipo sin anclaje (apoyo sobre losa).",
    ]
    if g.opt:
        nz.append(f"Agujeros roscados M{fm(P['d_tor'], 0)} de los tornillos de posición: posiciones y profundidades en la lámina de sectores; roscar después de planear la cara.")
    p.notes(nz, gd=[("flat", "0,20", None, f"Planitud de la zona de apoyo Ø{f(P['D_top'] + 20)}"), ("perp", "0,05", "A", f"Agujero Ø{f(P['D_piv'])} H7 perpendicular a la cara de apoyo (A)")])
    p.build()
    return p.h


from soldadura_det import add_prep


def ra(s, V, p3, txt, dx=0.0, dy=3.0):
    a = V.P(p3)
    s.roughness((a[0] + dx, a[1] + dy), txt)


def wd(ctx, jid):
    return ctx.weld_by_id(jid)


# ======================================================================================================
@pieza("collar")
def sheet_collar(ctx):
    g, P = ctx.g, ctx.P
    tb = g.tb
    p = Pieza(ctx, ["collar"], "COLLAR DE ASIENTO DEL PIVOTE", fmt="auto")
    s = p.s
    on = ["collar"]
    zt = tb + g.h_boss
    jc = jids(ctx, "Collar")[0]

    def planta(V, p):
        s.centerlines(V.P(0, 0, zt), g.D_boss / 2 * V.scale, 6)
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 70, 0), draw=planta, title="PLANTA", auto=dict(fits={P["D_piv"]: "H7"}, hole_rmin=5), w=1.0)

    def corte(V, p):
        s.line(V.P(0, 0, tb - 8), V.P(0, 0, zt + 10), "EJE")
        w_sym(p, jc, V, (g.D_boss / 2, 0, tb + 1), (45, -40), all_round=True)
        ra(s, V, (-P["D_piv"] / 2 + 1, 0, tb + g.h_boss / 2), "Ra 1,6", dx=3, dy=-4)
        ra(s, V, (-g.D_boss / 2 + 10, 0, zt), "Ra 3,2", dy=2)
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 2, 2, 3), extra=(0, 0, 10, 0), draw=corte, title="CORTE A-A", w=1.6,
         auto=dict(rev=(0, 0), fits={P["D_piv"]: "H7"}, rev_side="top", tol={round(g.h_boss, 1): " ±0,5"}, hole_notes=False))
    add_prep(p, "det_j", wd(ctx, jc), t1=(g.D_boss - P["D_piv"]) / 2, t2=g.tb, both=False)
    p.tables([jc])
    p.notes([f"Disco Ø{f(g.D_boss)} × {f(g.h_boss)}: oxicorte/plasma desde plancha de {f(g.h_boss + 5)} (sobremetal 5); caras planeadas.",
             f"Agujero Ø{f(P['D_piv'])} H7: NO se mecaniza antes de soldar; se mandrina en línea con la plancha base (BAS-001) en un solo montaje, Ra 1,6.",
             f"Soldar a la plancha base con filete perimetral continuo z{fm(g.w_collar, 0)} ({jc}): secuencia simétrica por tramos opuestos para limitar la distorsión; alivio de tensiones antes de mandrinar.",
             "Arista exterior superior e interior de la boca del agujero: 1×45° (ISO 13715).",
             "Sin pintura en la cara superior (asiento del cubo de la mesa: holgura axial c_boss_a)."],
            gd=[("perp", "0,05", "A", "Agujero H7 perpendicular a la cara de apoyo (A = cara inferior)"), ("flat", "0,10", None, "Planitud de la cara superior"),
                ("coax", "Ø0,05", "A", "Coaxial con el agujero de la plancha base (mandrinado en línea)")])
    p.build()
    return p.h


@pieza("marco_largo", "marco_corto")
def sheet_marcos(ctx):
    g, P = ctx.g, ctx.P
    B, tb, rt, rh = g.B, g.tb, P["rim_t"], P["rim_h"]
    ctx.local("marco_largo", "ml1", near=(0, -B / 2 + 5, tb + 20), r=300)
    ctx.local("marco_corto", "mc1", near=(B / 2 - 5, 0, tb + 20), r=300)
    p = Pieza(ctx, ["marco_largo", "marco_corto"], "MARCO PERIMETRAL: PLETINAS LARGA Y CORTA", fmt="auto")
    s = p.s
    ids = jids(ctx, "Marco perimetral largo", "Marco largo – marco corto", "Marco corto – plancha")
    p.vs("larga", ["ml1"], "front", breaks=[(-900, 900)], lv=(1, 2, 1, 1), title="PLETINA LARGA (BAS-003) — 2 unidades, con rotura", mat={"ml1": "acero"},
         auto=dict(tol={round(rh, 1): " ±0,5"}), w=1.5)
    p.vs("corta", ["mc1"], "right", breaks=[(-900, 900)], lv=(1, 2, 1, 1), title="PLETINA CORTA (BAS-004) — 2 unidades, con rotura", mat={"mc1": "acero"},
         auto=dict(tol={round(rh, 1): " ±0,5"}), w=1.5)
    p.vs("perfil", ["ml1"], "left", lv=(1, 1, 1, 1), title="PERFIL DE LA PLETINA (sección)", maxs=5.0, auto=dict(), hatch=False, w=1.0)

    def juntad(V, p):
        w_sym(p, ids[0], V, (0, -B / 2 + rt, tb + 3), (28, 36), other=None)
        s.cut_line  # (marca de corte en la planta de la esquina)
    p.vs("junta", ["base_plancha", "marco_largo"], "right", cut=CUT_X, center=(0, -B / 2, tb), win=(-34, -tb - 4, 60, rh + 12), lv=(1, 1, 2, 1), draw=juntad, title="DETALLE A: JUNTA PLETINA–PLANCHA (ambos lados)",
         auto=dict(on=["base_plancha", "marco_largo"]), mat={"base_plancha": "acero", "marco_largo": "acero"}, maxs=2.0, w=1.0)

    def esq(V, p):
        w_sym(p, ids[1], V, (B / 2, -B / 2, tb + rh), (-5, 30), kind="fillet")
    p.vs("esquina", ["marco_largo", "marco_corto", "base_plancha"], "top", center=(B / 2, -B / 2, tb), win=(-60, -20, 25, 60), lv=(1, 1, 1, 1), draw=esq, title="DETALLE B: ESQUINA (PLANTA)", hatch=False,
         auto=dict(on=["marco_largo", "marco_corto"]), maxs=2.0, w=1.0)
    add_prep(p, "det_j1", wd(ctx, ids[0]), t1=rt, t2=tb, both=True)
    add_prep(p, "det_j2", wd(ctx, ids[2]), t1=rt, t2=tb, both=True) if len(ids) > 2 else None
    p.tables(ids)
    p.notes([f"Pletinas {f(rt)} × {f(rh)}; 2 largas de {f(B)} y 2 cortas de {f(B - 2 * rt)} (entre las largas); corte a sierra o plasma con borde recto.",
             "Armado: pletinas largas sobre la plancha, cortas entre ellas; puntear y soldar en secuencia simétrica; filete continuo exterior e interior.",
             f"Las esquinas se sueldan con filete exterior de esquina continuo ({ids[1]}); el tamaño z indicado es el mínimo AWS D1.1 T5.8 por la parte más gruesa (a confirmar, el cálculo no fija el marco).",
             "El marco contiene la interfaz y protege el borde; no tiene función estructural en el cálculo."])
    p.build()
    return p.h


@pieza("mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf")
def sheet_mensula_piezas(ctx):
    g, P, BR = ctx.g, ctx.P, ctx.g.BR
    c = ctx.D["cilindros"]["horario"][0]
    E, ph = c["eye"], c["phiMean"]
    for k in ("mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf"):
        ctx.local(k, k + "_L", near=(E[0], E[1], 80), r=300, shift=(-E[0], -E[1], 0), rot=-ph)
    tb, H_, rear, Llug, Win, Wout, tc = g.tb, BR["H"], BR["rear"], BR["Llug"], BR["Win"], BR["Wout"], P["t_ch"]
    p = Pieza(ctx, ["mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf"], "MÉNSULA DE CILINDRO: MEJILLA Y OREJAS (PIEZAS)", fmt="auto")
    s = p.s
    zt = tb + H_
    hb = BR["spacer"] + tc
    ids = jids(ctx, "Mejillas de ménsula", "Oreja superior", "Oreja inferior (bloque) – mejillas", "Oreja inferior (bloque) – plancha")
    k1, k2, k3 = ["mensula_mejilla_L"], ["mensula_oreja_sup_L"], ["mensula_oreja_inf_L"]

    def d1(V, p):
        if len(ids) >= 4:
            w_sym(p, ids[0], V, (P["L_ch"] / 2 - rear, -Wout / 2, tb + 0.5), (30, -34))
        s.roughness((V.P(0, -Wout / 2, zt)[0] + 6, V.P(0, 0, zt)[1] + 3), "Ra 12,5 (corte)") if False else None
    p.vs("mej_el", k1, "front", lv=(1, 2, 1, 1), draw=d1, title="MEJILLA — ELEVACIÓN (2 por ménsula, 8 en total)", auto=dict(tol={round(H_, 1): " ±0,5", round(P["L_ch"], 1): " ±1"}), w=1.5)
    p.vs("mej_pl", k1, "top", lv=(1, 2, 1, 1), title="MEJILLAS — PLANTA", auto=dict(), w=0.8)
    p.vs("os_pl", k2, "top", lv=(1, 2, 1, 1), extra=(0, 0, 40, 0), title="OREJA SUPERIOR (BAS-006) — PLANTA", auto=dict(fits={P["d_pp"]: "H9"}, tol={round(Llug, 1): " ±0,5", round(Win, 1): " −0,5"}), w=1.0)
    p.vs("os_el", k2, "front", lv=(1, 2, 1, 1), title="OREJA SUPERIOR — ELEVACIÓN", auto=dict(tol={round(tc, 1): " ±0,2"}), w=0.7)
    p.vs("oi_pl", k3, "top", lv=(1, 2, 1, 1), extra=(0, 0, 40, 0), title="OREJA INFERIOR / BLOQUE (BAS-007) — PLANTA", auto=dict(fits={P["d_pp"]: "H9"}, tol={round(Llug, 1): " ±0,5", round(Win, 1): " −0,5"}), w=1.0)

    def d3(V, p):
        if len(ids) >= 4:
            w_sym(p, ids[3], V, ((Llug - rear) / 2, -Win / 2, tb + 0.5), (30, -30))
    p.vs("oi_el", k3, "front", lv=(1, 2, 1, 1), draw=d3, title="OREJA INFERIOR — ELEVACIÓN (bloque)", auto=dict(tol={round(hb, 1): f" (= {f(BR['spacer'])} + {f(tc)})"}), w=0.7)
    # corte por el eje del agujero de la oreja superior
    p.vs("os_corte", k2, "front", cut=((0, 0, 0), (0, 1, 0)), lv=(1, 2, 1, 1), title="CORTE A-A: AGUJERO DE LA OREJA", hatch=True, auto=dict(tol={}, hole_notes=False, text={round(P["d_pp"], 1): tol_txt(P["d_pp"], "H9")}), w=0.8, hs=0.4)
    if len(ids) >= 4:
        add_prep(p, "det_j4", wd(ctx, ids[0]), t1=tc, t2=tb)
        add_prep(p, "det_j5", wd(ctx, ids[1]), t1=tc, t2=tc)
        add_prep(p, "det_j6", wd(ctx, ids[2]), t1=tc, t2=BR["spacer"] + tc)
    p.tables(ids)
    p.notes([f"Mejillas: plancha {f(tc)} × {f(H_)} × {f(P['L_ch'])}, 2 por ménsula ({int(P['n_br'])} ménsulas, {int(2 * P['n_br'])} mejillas); plasma, borde recto.",
             f"Orejas: planchas {f(Win)} (−0,5 para entrar entre mejillas con luz interior {f(Win)}) × {f(Llug)}; la inferior es un bloque {f(hb)} de espesor (pletinas apiladas o plancha gruesa).",
             f"Agujero Ø{f(P['d_pp'])} H9 de ambas orejas: mandrinar en línea DESPUÉS de soldar la ménsula, en un solo montaje; coaxialidad 0,10; eje a {f(g.hax)} ±0,5 sobre la cara de apoyo.",
             "Armar la ménsula en una plantilla sobre la base; soldadura de mejillas: secuencia alternada para limitar la distorsión (filete z de la tabla).",
             "Para la ménsula completa ver el subconjunto CON-007 y la lámina de la base."],
            gd=[("coax", "Ø0,10", "A", f"Agujeros Ø{f(P['d_pp'])} H9 de las dos orejas coaxiales (mandrinado en línea)"), ("perp", "0,10", "B", "Eje del agujero perpendicular al plano de las mejillas")])
    p.build()
    return p.h


@pieza("orejas")
def sheet_orejas(ctx):
    g, P = ctx.g, ctx.P
    x, y = g.ear_pos[0]
    ang = math.degrees(math.atan2(y, x))
    ctx.local("orejas", "oreja_L", near=(x, y, g.tb + 50), r=200, shift=(-x, -y, 0), rot=-ang)
    tb, R, hE, tE, dE = g.tb, P["R_ear"], P["h_ear"], P["t_ear"], P["d_ear"]
    p = Pieza(ctx, ["orejas"], "OREJA DE IZAJE (4 UNIDADES)", fmt="auto")
    s = p.s
    on = ["oreja_L"]
    jid = jids(ctx, "Orejas de izaje")[0]

    def perfil(V, p):
        s.line(V.P(0, 0, tb - 6), V.P(0, 0, tb + hE + R + 8), "EJE"); s.line(V.P(-R - 8, 0, tb + hE), V.P(R + 8, 0, tb + hE), "EJE")
        V.dim_rad((0, tE / 2, tb + hE), R, 130, on=on, text=f"R{f(R)}", ext=18)
        w_sym(p, jid, V, (R, tE / 2, tb + 3), (36, 40))
        s.roughness((V.P(-R, 0, tb + hE)[0] - 30, V.P(0, 0, tb + hE)[1] + 8), "Ra 12,5")
    p.vs("perfil", on, "front", center=(0, 0, tb), lv=(1, 2, 2, 1), extra=(0, 0, 30, 0), draw=perfil, hatch=False, title="PERFIL",
         auto=dict(tol={round(hE, 1): " ±1 (al centro del agujero)", round(2 * R, 1): " (= 2R)"}, fits={}, hole_pos=True), w=1.5)
    p.vs("planta", on, "top", center=(0, 0, tb), lv=(1, 2, 1, 1), title="PLANTA (espesor)", auto=dict(tol={round(tE, 1): ""}), w=0.7, maxs=2.0)
    p.vs("corte", on, "right", cut=((0, 0, 0), (-1, 0, 0)), center=(0, 0, tb), lv=(1, 2, 1, 1), title="CORTE B-B (espesor y agujero)", auto=dict(), w=0.7, maxs=2.0, hs=0.4) if False else None
    add_prep(p, "det_j", wd(ctx, jid), t1=tE, t2=tb)

    def det_bis(V, p):
        s.text("Bisel de la base: preparar según WPS-P05 (propuesta)", (V.ext[0], V.ext[3] + 6), T_N, "BOTTOM_LEFT")
    p.tables([jid])
    p.notes([f"Plancha e = {f(tE)}; perfil 2R × h + semicírculo R{f(R)}; agujero Ø{f(dE)} de corte (sin mecanizar, aristas esmeriladas); grillete con pasador ≤ d − g_ear = {fm(dE - P['g_ear'], 0)} mm.",
             f"Posición en la base: (±{f(P['x_lug'])}, ±{f(g.cl_lug)}) ±2, plano vertical radial hacia el centro (plano BAS-001, tabla de posiciones).",
             f"Soldadura a la base: filete z{fm(P['w_ear'], 0)} a ambos lados (L = 2R) ({jid}); MT 100 % y UT 100 % antes de la prueba de carga y MT después.",
             ramales_txt_short(ctx),
             f"Factor dinámico del cálculo φ_lift = {fm(P['phi_lift'], 2)}; uso: eslinga de 4 ramales con grillete certificado ASME B30.26 (marca/modelo por catálogo; WLL ≥ lo calculado, ver GEN-008)."],
            gd=[("perp", "0,5", "A", "Plano de la oreja perpendicular a la base (A)")])
    p.build()
    return p.h


@pieza("bancada")
def sheet_bancada(ctx):
    g, P, KG = ctx.g, ctx.P, ctx.g.KG
    X = P["x_g"]
    ctx.local("bancada", "bancada_L", near=(X, 0, 40), r=800, shift=(-X, 0, 0))
    tb, zb = g.tb, g.zb
    Yb = KG["Y_bed"]
    p = Pieza(ctx, ["bancada"], "BANCADA DE GUÍA CON RANURA T (2 UNIDADES)", fmt="auto")
    s = p.s
    on = ["bancada_L"]
    jid = jids(ctx, "Bancada")[0]

    def planta(V, p):
        s.line(V.P(0, -Yb - 20, zb), V.P(0, Yb + 20, zb), "EJE")
    p.vs("planta", on, "top", center=(0, 0, zb), hidden=True, lv=(1, 2, 2, 1), draw=planta, title="PLANTA (ranura T pasante en todo el largo)", breaks=None,
         auto=dict(tol={round(2 * Yb, 1): " ±1 (largo)"}, fits={}), w=1.5)

    def corte(V, p):
        s.line(V.P(0, 0, tb - 6), V.P(0, 0, zb + 8), "EJE")
        w_sym(p, jid, V, (-P["w_bed"] / 2, 0, tb + 3), (-25, -25), sh=-1)
        ra(s, V, (P["w_slot"] / 2 + 2, 0, zb), "Ra 1,6")
        s.datum((V.P(0, 0, zb)[0] - 30, V.P(0, 0, zb)[1] + 10), "A", up=True)
    p.vs("corte", on, "front", cut=((0, 0, 0), (0, 1, 0)), lv=(2, 2, 2, 2), draw=corte, title="CORTE A-A (ranura T)", hs=0.6,
         auto=dict(tol={round(P["t_bed"], 1): " ±0,5", round(P["w_slot"], 1): " H8", round(P["h_slot"], 1): " +0,1/0", round(P["w_tee"], 1): " +0,2/0", round(P["h_tee"], 1): " +0,2/0"}), w=1.5)
    p.vs("det_ranura", on, "front", cut=((0, 0, 0), (0, 1, 0)), center=(0, 0, zb - 12), win=(-42, -22, 42, 16), lv=(1, 2, 1, 2), title="DETALLE B: RANURA T (ampliado)", hs=0.3, maxs=2.0,
         auto=dict(tol={round(P["w_slot"], 1): " H8", round(P["w_tee"], 1): " +0,2/0", round(P["h_tee"], 1): " +0,2/0", round(P["h_slot"], 1): " +0,1/0"}), w=1.0)
    p.vs("extremo", on, "right", lv=(1, 2, 1, 1), title="VISTA DE EXTREMO (entrada del patín)", hatch=False, auto=dict(), w=0.8)
    add_prep(p, "det_j", wd(ctx, jid), t1=P["t_bed"], t2=tb)
    p.tables([jid])
    p.notes([f"Plancha {f(P['w_bed'])} × {f(P['t_bed'])} × {f(2 * Yb, 1)} (largo de carrera del patín); sobremetal 5 mm en el largo.",
             f"Ranura T pasante: cuello {f(P['w_slot'])} H8 × {f(P['h_slot'])}, cabeza {f(P['w_tee'])} × {f(P['h_tee'])}, fondo {f(g.fondo)}; mecanizar DESPUÉS de soldar y aliviar tensiones (fresado/cepillo); flancos Ra 1,6; el patín entra por el extremo.",
             f"Soldadura a la base: filete continuo z{fm(P['w_bed_f'], 0)} ambos lados, precalentar 65 °C ({jid}); eje de guía en x = ±{f(X)} ±0,5 respecto del centro.",
             "Paralelismo de la ranura 0,10 (datum A = eje de la bancada) y coaxialidad con el ojal ±0,2: verificar antes de montar el patín.",
             "Flancos de la ranura con grasa grafitada en montaje."],
            gd=[("par", "0,10", "A", "Ranura paralela al eje de la bancada en todo el largo"), ("pos", "Ø0,2", "A", "Ranura coaxial con el ojal de la ménsula (±0,2)")])
    p.build()
    return p.h
