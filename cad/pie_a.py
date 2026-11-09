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
    ghosts = ["marco_largo", "marco_corto", "collar", "mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf", "cajon_pared", "cajon_ventana_a", "cajon_ventana_b", "cajon_tapa", "orejas", "bancada",
              "leva_prolong", "leva_pata", "placa_leva", "placa_leva_h"]

    def planta(V, p):
        ghost(p, V, ghosts)
        s.line(V.P(-B / 2 - 70, 0, tb), V.P(B / 2 + 70, 0, tb), "EJE"); s.line(V.P(0, -B / 2 - 70, tb), V.P(0, B / 2 + 70, tb), "EJE")
        V.dimh((-B / 2, B / 2, tb), (B / 2, B / 2, tb), "top", 0, on=on, text=f"{f(B)} ±2")
        V.dimv((-B / 2, -B / 2, tb), (-B / 2, B / 2, tb), "left", 0, on=on, text=f"{f(B)} ±2")
        s.circle(V.P(0, 0, tb), g.D_boss / 2 * V.scale, "FANT")
        s.circle(V.P(0, 0, tb), (P["D_top"] + 20) / 2 * V.scale, "FANT")
        ph = ctx.m.info.get("placa_leva_holes")
        if ph:                             # roscas de los pernos de las placas-leva (modo 2)
            dpl = g.FPV["placas_leva"]["pernos"]["d"]
            x_, y_ = ph[0]
            V.note_hole((x_, y_, tb), dpl / 2, 200, f"{len(ph)} × M{fm(dpl, 0)} pasantes (placas-guía; coordenadas en la tabla)", ext=26, on=on,
                        lines=[f"{len(ph)} × M{fm(dpl, 0)}-6H pasantes", "(placas-guía; coordenadas en la tabla)"])
            pp_ = ctx.m.info.get("placa_pas_holes")
            if pp_:
                dpp = g.FPV["placas_leva"]["pasadores_posicion"]["d"]
                V.note_hole((pp_[0][0], pp_[0][1], tb), dpp / 2, 160, f"{len(pp_)} × Ø{fm(dpp, 0)} H7 (pasadores)", ext=26, on=on,
                            lines=[f"{len(pp_)} × Ø{fm(dpp, 0)} H7 ciegos", "(pasadores de las placas-guía)"])
        cs = [c_ for c_ in V.circles(["base_plancha"], 2.0, 4.5)]
        if cs:
            n = len(cs)
            u, v, r = cs[0]
            V.note_hole((u, v, tb), r, 60, f"{n} × M{fm(r * 2, 0)} (rosca en el respaldo; ver tabla de agujeros)", ext=30, on=on, lines=[f"{n} × M{fm(r * 2, 0)} (rosca en el respaldo;", "ver tabla de agujeros)"])
        c0 = V.P(0, 0, tb)
        s.circle(c0, (P["D_top"] + 20) / 2 * V.scale, "FANT")
        s.text(f"zona de apoyo Ø{f(P['D_top'] + 20)}", (c0[0], c0[1] - (P["D_top"] + 20) / 2 * V.scale + 3), T_N, "BOTTOM_CENTER")
        s.circle(c0, g.D_boss / 2 * V.scale, "FANT")
        s.text(f"collar Ø{f(g.D_boss)} (BAS-002)", (c0[0], c0[1] - g.D_boss / 2 * V.scale - 3), T_N, "TOP_CENTER")
        p.cut_mark("planta", "A", (-B / 2 - 38, 0, tb), (B / 2 + 38, 0, tb), 90)
        p.cut_mark("planta", "D", (B / 2 - 150, B / 2 + 30, tb), (B / 2 - 150, B / 2 - 150, tb), 0) if False else None

    p.vs("planta", on, "top", lv=(2, 0, 0, 2), draw=planta, auto=False, title="PLANTA DE LA PLANCHA BASE", w=2.0, extra=(0, 0, 0, 0))

    def corte(V, p):
        s.line(V.P(0, 0, -10), V.P(0, 0, g.tb + g.h_boss + 10), "EJE")
        zt_ = g.tb + g.h_boss
        rb, rp = g.D_boss / 2, P["D_piv"] / 2
        # B-46: una sola cota por elemento; las del collar son de referencia (BAS-002) y el total es auxiliar
        V.dimh((-rb, 0, zt_), (rb, 0, zt_), "top", 0, on=["collar"], text=f"(Ø{f(g.D_boss)}: collar BAS-002)")
        V.dimh((-rp, 0, zt_), (rp, 0, zt_), "top", 1, on=["collar"], text=f"Ø{f(P['D_piv'])} H7 (+0,035/0)")
        V.dimv((rb, 0, g.tb), (rb, 0, zt_), "right", 0, on=["collar"], text=f"({f(g.h_boss)})")
        V.dimv((rb, 0, 0), (rb, 0, zt_), "right", 1, on=["collar", "base_plancha"], text=f"({f(zt_)})")
        V.dimv((-285, 0, 0), (-285, 0, tb), "left", 0, on=["base_plancha"], text=f"{f(tb)} ±0,5 (t_base)")
        w_out(p, jids(ctx, "Collar")[0], V, (g.D_boss / 2, 0, tb + 1), "right", all_round=True, dy=20)
    # B-20: datum A en la cara superior planeada, planitud sobre ella y perpendicularidad del agujero H7 sobre su cota; Ra en la superficie
    p.datum_in("corte", "surf", "A", at=[(-262, 0, tb), (262, 0, tb), (-200, 0, tb)], d=(0, 1))
    p.gd_in("corte", "surf", "flat", "0,20", None, at=[(-215, 0, tb), (215, 0, tb), (-170, 0, tb)], d=(0, 1))
    p.gd_in("corte", "dim", "perp", "0,05", "A", prefix=f"Ø{f(P['D_piv'])} H7")
    p.ra_in("corte", "Ra 1,6", prefix=f"Ø{f(P['D_piv'])} H7")
    p.ra_in("corte", "Ra 3,2", [(-240, 0, tb), (240, 0, tb)], (0, 1))
    p.vs("corte", ["base_plancha", "collar"], "front", cut=CUT_Y, win=(-290, -4, 290, tb + g.h_boss + 12), lv=(1, 2, 1, 1), draw=corte, title="CORTE A-A (central, collar soldado)", extra=(0, 0, 115, 0), mat={"base_plancha": "acero", "collar": "acero"},
         auto=False, w=2.0, hs=0.5)
    # tabla de posiciones
    rows = []
    for i, (ex, ey) in enumerate(g.ear_pos):
        rows.append([f"O{i + 1} oreja de izaje", f(ex), f(ey), "—", f"plano radial {fm(math.degrees(math.atan2(ey, ex)), 2)}°"])
    if g.modo == 1:
        for grp in ("horario", "antihorario"):
            for k, c in enumerate(D["cilindros"][grp]):
                rows.append([f"M{len(rows) - 3} ménsula {grp}", f(c["eye"][0], 1), f(c["eye"][1], 1), f(c["phiMean"], 1) + "°", "eje del ojal"])
        for sx in (1, -1):
            rows.append(["Bancada (eje de guía)", f(sx * P["x_g"]), "0", "90°", f"largo {f(g.KG['L_bed'], 1)}"])
    else:
        Sx = g.FPV["soporte_E"]
        for i_, lk_ in enumerate(("cilindro1", "cilindro2")):
            E_ = Sx[lk_]["centro"]
            rows.append([f"C{i_ + 1} cajón del ojal E (eje E)", f(E_[0], 1), f(E_[1], 1), "—", f"cajón {f(Sx['lado'])} × {f(Sx['lado'])}; posición con tolerancia ajustada (CON-007)"])
        for k_, ins in [(k__, v__) for k__, v__ in g.FPV["placas_leva"]["instancias"].items() if k__.startswith("1")]:      # placas 2: simétricas respecto del centro
            for j_, (x_, y_) in enumerate(ins["pernos"]):
                rows.append([f"Rosca M{fm(g.FPV['placas_leva']['pernos']['d'], 0)} placa {k_.replace('_', ' ')} T{j_ + 1}", f(x_, 1), f(y_, 1), "—", "pasante (Ø0,2 de posición)"])
            for j_, (x_, y_) in enumerate(ins.get("pasadores_posicion") or []):
                rows.append([f"Pasador Ø{fm(g.FPV['placas_leva']['pasadores_posicion']['d'], 0)} H7 placa {k_.replace('_', ' ')} D{j_ + 1}", f(x_, 1), f(y_, 1), "—", f"ciego prof. {fm(ctx.m.info.get('placa_pas_L', 0) - g.FPV['placas_leva']['t'], 0)}, escariado con la placa"])
    rows.append(["Collar / agujero H7", "0", "0", "—", f"Ø{f(g.D_boss)} / Ø{f(P['D_piv'])}"])
    p.table_block("POSICIONES DE LAS PIEZAS SOLDADAS Y AGUJEROS (origen: centro de la plancha" + ("; placas-guía del cilindro 2: (−x; −y) de las del cilindro 1)" if g.modo == 2 else ")"), [("Elemento", 60, "L"), ("x [mm]", 22, "R"), ("y [mm]", 22, "R"), ("Ángulo", 18, "C"), ("Observación", 52, "L")], rows)
    p.tables(jids(ctx, "Collar"))
    nz = [
        f"Plancha {f(B)} × {f(B)} × {f(tb)} de {p.p0.material.split(',')[0]}; sobrematerial de corte 5 mm por borde, recortar a medida después del alivio. Corte por oxicorte/plasma con tolerancia ISO 9013 clase 3.",
        f"Agujero central Ø{f(P['D_piv'])} H7: mandrinar plancha y collar en un solo montaje (mandrinadora) después de soldar el collar y aliviar tensiones; Ra 1,6; perpendicular a la cara de apoyo 0,05.",
        f"Cara superior en la zona Ø{f(P['D_top'] + 20)}: planeada (planitud 0,20 / Ra 3,2); sin pintura en esa zona. Compensar la distorsión de la soldadura con contraflecha o secuencia simétrica.",
        "Posiciones de las piezas soldadas (tabla): marcar con granete y trazado antes de armar; tolerancia ±1 (también orejas de izaje).",
        "Soldaduras de la base: ver CON-023 (detalles D1–D4 y tabla del subconjunto) y el programa de soldaduras (GEN-007); detalle del collar (J09) en BAS-002. Alivio de tensiones 590–620 °C después de soldar y antes del mecanizado final.",
        "La plancha NO lleva anclajes: equipo sin anclaje (apoyo sobre losa).",
    ]
    if g.opt:
        hb = centros_xy(ctx.m.info.get("holes_base"))
        pat = patron_txt(hb, f"M{fm(P['d_tor'], 0)}")
        rr_ = (ctx.m.info.get("screw_resp") or {}).get("base")
        prof_ = (f"pasantes" if rr_ and rr_["pasante"] else f"rosca útil {fm(rr_['thr'], 0)}, taladro Ø{fm(rr_['broca'], 1)} prof. {fm(rr_['drill'], 0)}") if rr_ else "según la lámina de tornillos"
        nz.append(f"Agujeros roscados M{fm(P['d_tor'], 0)}-6H de los tornillos de posición" + (": " + "; ".join(pat) if pat else "") + f"; {prof_} (INT-005); roscar después de planear la cara.")
    p.h.retener("placa_orejas", "las placas-guía chocan con las orejas de izaje; las posiciones de las orejas y de las roscas de las placas pueden cambiar")
    p.notes(nz, gd=[("flat", "0,20", None, f"Planitud de la zona de apoyo Ø{f(P['D_top'] + 20)} (cara superior planeada = A)"), ("perp", "0,05", "A", f"Agujero Ø{f(P['D_piv'])} H7 perpendicular a la cara superior planeada (A)")])
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

    def corte(V, p):
        s.line(V.P(0, 0, tb - 6), V.P(0, 0, zt + 3), "EJE")          # B-48: el eje no llega a la línea de cota del Ø H7
        w_sym(p, jc, V, (g.D_boss / 2, 0, tb + 1), (45, -40), all_round=True)
    # B-45/B-46: el corte lleva todas las cotas (una sola vez); la planta solo ubica el corte
    p.ra_in("corte", "Ra 1,6", [(-P["D_piv"] / 2, 0, tb + g.h_boss * 0.35), (P["D_piv"] / 2, 0, tb + g.h_boss * 0.35)], [(1, 0), (-1, 0)])
    p.ra_in("corte", "Ra 6,3", [(-g.D_boss / 2 + 12, 0, zt), (g.D_boss / 2 - 12, 0, zt)], (0, 1))
    p.datum_in("corte", "surf", "A", at=[(-g.D_boss / 2 + 14, 0, tb), (g.D_boss / 2 - 30, 0, tb), (-P["D_piv"] / 2 - 12, 0, tb)], d=(0, -1))
    p.gd_in("corte", "dim", "perp", "0,05", "A", prefix=f"Ø{f(P['D_piv'])} H7")
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 2, 2, 3), extra=(0, 0, 10, 0), draw=corte, title="CORTE A-A", w=1.6,
         auto=dict(rev=(0, 0), fits={P["D_piv"]: "H7"}, rev_side="top", tol={round(g.h_boss, 1): " ±0,5"}, hole_notes=False))
    def planta(V, p):
        s.centerlines(V.P(0, 0, zt), g.D_boss / 2 * V.scale, 6)
        p.cut_mark("planta", "A", (-g.D_boss / 2 - 14, 0, zt), (g.D_boss / 2 + 14, 0, zt), 90)
    p.vs("planta", on, "top", lv=(0, 0, 0, 0), extra=(0, 0, 0, 0), draw=planta, title="PLANTA (ubicación del corte A-A)", auto=False, w=0.5, maxs=0.2)
    add_prep(p, "det_j", wd(ctx, jc), t1=(g.D_boss - P["D_piv"]) / 2, t2=g.tb, both=False, lab1=f"{fm((g.D_boss - P['D_piv']) / 2, 0)} (ancho radial; alto {fm(g.h_boss, 0)})")
    p.tables([jc])
    p.notes([f"Disco Ø{f(g.D_boss)} × {f(g.h_boss)}: partida Ø{f(g.D_boss + 10)} oxicortada de plancha de {f(g.h_boss + 5)}; caras planeadas a {f(g.h_boss)} ±0,5 y Ø{f(g.D_boss)} torneado en torno horizontal.",
             f"Agujero Ø{f(P['D_piv'])} H7: NO se mecaniza antes de soldar; se mandrina en línea con la plancha base (BAS-001) en un solo montaje, Ra 1,6.",
             f"Soldar a la plancha base con filete perimetral continuo z{fm(g.w_collar, 0)} ({jc}): secuencia simétrica por tramos opuestos para limitar la distorsión; alivio de tensiones antes de mandrinar.",
             "Arista exterior superior e interior de la boca del agujero: 1×45° (ISO 13715).",
             f"Sin pintura en la cara superior: queda frente al cubo de la mesa con holgura axial {fm(g.c_boss_a, 0)} mm (sin contacto; no es asiento)."],
            gd=[("perp", "0,05", "A", "Agujero H7 perpendicular a la cara inferior (A, cara soldada a la plancha base)")])
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
    p.iso_keys = ["ml1", "mc1"]
    ids = jids(ctx, "Marco perimetral largo", "Marco largo – marco corto", "Marco corto – plancha")
    p.vs("larga", ["ml1"], "front", breaks=[(-900, 900)], lv=(1, 2, 1, 1), title="PLETINA LARGA (BAS-003) — 2 unidades, con rotura", mat={"ml1": "acero"},
         auto=dict(tol={round(rh, 1): " ±0,5"}), w=1.5)
    def corta_(V, p):
        if len(ids) > 2:
            w_out(p, ids[2], V, (B / 2 - rt, -B / 4, tb + 0.5), "bottom")
    p.vs("corta", ["mc1"], "right", breaks=[(-900, 900)], lv=(1, 2, 1, 1), extra=(0, 0, 0, 0), title="PLETINA CORTA (BAS-004) — 2 unidades, con rotura", mat={"mc1": "acero"},
         auto=dict(tol={round(rh, 1): " ±0,5"}), w=1.5, draw=corta_)
    p.vs("perfil", ["ml1"], "left", lv=(1, 1, 1, 1), title="PERFIL DE LA PLETINA (sección)", maxs=5.0, auto=dict(), hatch=False, w=1.0)

    def juntad(V, p):
        w_sym(p, ids[0], V, (0, -B / 2 + rt, tb + 3), (28, 36), other=None)
    p.vs("junta", ["base_plancha", "marco_largo"], "right", cut=CUT_X, center=(0, -B / 2, tb), win=(-34, -tb - 4, 60, rh + 12), lv=(1, 1, 2, 1), draw=juntad, title="DETALLE A: JUNTA PLETINA–PLANCHA (pletina a ras del canto; filete interior)",
         auto=dict(on=["base_plancha", "marco_largo"], text={round(rh + tb, 1): f"({f(rh + tb)})"}), mat={"base_plancha": "acero", "marco_largo": "acero"}, maxs=2.0, w=1.0)
    # B-20: datum A = cara superior de la plancha base; perpendicularidad de la cara interior de la pletina; rectitud del canto superior
    p.datum_in("junta", "surf", "A", at=[(0, -B / 2 + rt + 34, tb), (0, -B / 2 + rt + 44, tb)], d=(0, 0, 1))
    p.gd_in("junta", "surf", "perp", "0,5", "A", at=[(0, -B / 2 + rt, tb + rh * 0.65)], d=(0, 1, 0))
    p.gd_in("larga", "surf", "straight", "2,0", None, at=[(-B / 2 + 160, -B / 2, tb + rh), (B / 2 - 160, -B / 2, tb + rh)], d=(0, 0, 1))

    def esq(V, p):
        w_out(p, ids[1], V, (B / 2 - rt, -B / 2 + rt, tb + rh), "top")          # N-12: la cola del símbolo no invade la cota 45 de la pletina corta
    p.vs("esquina", ["marco_largo", "marco_corto", "base_plancha"], "top", center=(B / 2, -B / 2, tb), win=(-60, -20, 25, 60), lv=(1, 1, 1, 1), draw=esq, title="DETALLE B: ESQUINA (PLANTA)", hatch=False,
         auto=dict(on=["marco_largo", "marco_corto"]), maxs=2.0, w=1.0)
    add_prep(p, "det_j1", wd(ctx, ids[0]), t1=rt, t2=tb, both=False, edge=True, title=f"DETALLE {ids[0]} / {ids[2] if len(ids) > 2 else ''}: FILETE INTERIOR z{fm(wd(ctx, ids[0])['z'], 0)} (pletina a ras del canto)")
    p.tables(ids)
    p.notes([f"Pletinas {f(rt)} × {f(rh)}; 2 largas de {f(B)} y 2 cortas de {f(B - 2 * rt)} (entre las largas); corte a sierra o plasma con borde recto.",
             "Armado: pletinas largas sobre la plancha con su cara exterior a ras del canto de la plancha; cortas entre ellas; puntear y soldar en secuencia simétrica; filete continuo solo por el lado interior (por fuera las caras quedan coplanares).",
             f"Esquinas: el extremo de la pletina corta apoya contra la cara interior de la larga; filete interior vertical en el rincón ({ids[1]}). Tamaños z: mínimo AWS D1.1 T5.8 por la parte más gruesa (a confirmar, el cálculo no fija el marco).",
             "El marco contiene la interfaz y protege el borde; no tiene función estructural en el cálculo."],
            gd=[("straight", "2,0", None, "Rectitud del canto en todo el largo (pletinas largas y cortas)"), ("perp", "0,5", "A", "Pletina perpendicular a la cara mayor (A) tras soldar")])
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
    p.iso_keys = [k + "_L" for k in ("mensula_mejilla", "mensula_oreja_sup", "mensula_oreja_inf")]
    zt = tb + H_
    hb = BR["spacer"] + tc
    ids = jids(ctx, "Mejillas de ménsula", "Oreja superior", "Oreja inferior (bloque) – mejillas", "Oreja inferior (bloque) – plancha")
    k1, k2, k3 = ["mensula_mejilla_L"], ["mensula_oreja_sup_L"], ["mensula_oreja_inf_L"]

    def d1(V, p):
        if len(ids) >= 4:
            w_out(p, ids[0], V, (P["L_ch"] / 2 - rear, -Wout / 2, tb + 0.5), "right", dy=24)
        s.roughness((V.P(0, -Wout / 2, zt)[0] + 6, V.P(0, 0, zt)[1] + 3), "Ra 12,5 (corte)") if False else None
    p.vs("mej_el", k1, "front", lv=(1, 2, 1, 1), extra=(0, 0, 115, 0), draw=d1, title="MEJILLA — ELEVACIÓN (2 por ménsula, 8 en total)", auto=dict(tol={round(H_, 1): " ±0,5", round(P["L_ch"], 1): " ±1"}), w=1.5)
    p.vs("mej_pl", k1, "top", lv=(1, 2, 1, 1), title="MEJILLAS — PLANTA", auto=dict(), w=0.8)
    p.vs("os_pl", k2, "top", lv=(1, 2, 1, 1), extra=(0, 0, 72, 0), title="OREJA SUPERIOR (BAS-006) — PLANTA", auto=dict(fits={P["d_pp"]: "H9"}, tol={round(Llug, 1): " ±0,5", round(Win, 1): " −0,5"}), w=1.0)
    p.vs("os_el", k2, "front", lv=(1, 2, 1, 1), title="OREJA SUPERIOR — ELEVACIÓN", auto=dict(tol={round(tc, 1): " ±0,2"}), w=0.7)
    p.vs("oi_pl", k3, "top", lv=(1, 2, 1, 1), extra=(0, 0, 72, 0), title="OREJA INFERIOR / BLOQUE (BAS-007) — PLANTA", auto=dict(fits={P["d_pp"]: "H9"}, tol={round(Llug, 1): " ±0,5", round(Win, 1): " −0,5"}), w=1.0)

    def d3(V, p):
        if len(ids) >= 4:
            w_out(p, ids[3], V, ((Llug - rear) / 2, -Win / 2, tb + 0.5), "top", dy=14, sh=-1)
    p.vs("oi_el", k3, "front", lv=(1, 2, 1, 1), extra=(80, 0, 0, 34), draw=d3, title="OREJA INFERIOR — ELEVACIÓN (bloque)", auto=dict(tol={round(hb, 1): ""}), w=0.9)
    # corte por el eje del agujero de la oreja superior
    p.vs("os_corte", k2, "front", cut=((0, 0, 0), (0, 1, 0)), lv=(1, 2, 1, 1), title="CORTE A-A: AGUJERO DE LA OREJA", hatch=True, auto=dict(tol={}, hole_notes=False, text={round(P["d_pp"], 1): f"Ø{f(P['d_pp'])} H9"}), w=0.8, hs=0.4)
    p.datum_in("os_el", "surf", "A", at=[(-rear + 15, 0, zt), (Llug - rear - 15, 0, zt), ((Llug - 2 * rear) / 2, 0, zt)], d=(0, 0, 1))
    p.gd_in("os_corte", "dim", "coax", "Ø0,10", "A", prefix=f"Ø{f(P['d_pp'])} H9")
    p.gd_in("oi_pl", "dim", "perp", "0,10", "A", prefix=f"Ø{f(P['d_pp'])} H9", alt=("os_pl", "dim", None, None, f"Ø{f(P['d_pp'])} H9"))
    if len(ids) >= 4:
        add_prep(p, "det_j4", wd(ctx, ids[0]), t1=tc, t2=tb)
        add_prep(p, "det_j5", wd(ctx, ids[1]), t1=tc, t2=tc)
        add_prep(p, "det_j6", wd(ctx, ids[2]), t1=tc, t2=BR["spacer"] + tc)
    p.tables(ids)
    p.notes([f"Mejillas: plancha {f(tc)} × {f(H_)} × {f(P['L_ch'])}, 2 por ménsula ({int(P['n_br'])} ménsulas, {int(2 * P['n_br'])} mejillas); plasma, borde recto.",
             f"Orejas: planchas {f(Win)} (−0,5 para entrar entre mejillas con luz interior {f(Win)}) × {f(Llug)}; la inferior es un bloque {f(hb)} de espesor (pletinas apiladas o plancha gruesa).",
             f"Agujero Ø{f(P['d_pp'])} H9 de ambas orejas: mandrinar en línea DESPUÉS de soldar la ménsula, en un solo montaje; coaxialidad 0,10; centro de la luz entre orejas (eje del cilindro) a {f(g.hax)} ±0,5 sobre la cara de apoyo.",
             "Armar la ménsula en una plantilla sobre la base; soldadura de mejillas: secuencia alternada para limitar la distorsión (filete z de la tabla).",
             "Para la ménsula completa ver el subconjunto CON-007 y la lámina de la base."],
            gd=[("coax", "Ø0,10", "A", f"Agujeros Ø{f(P['d_pp'])} H9 de las dos orejas coaxiales (mandrinado en línea)"), ("perp", "0,10", "A", "Eje del agujero perpendicular a la cara de apoyo (A)")])
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
    p.iso_keys = ["oreja_L"]
    on = ["oreja_L"]
    jid = jids(ctx, "Orejas de izaje")[0]

    def perfil(V, p):
        s.line(V.P(0, 0, tb - 6), V.P(0, 0, tb + hE + R + 8), "EJE"); s.line(V.P(-R - 8, 0, tb + hE), V.P(R + 8, 0, tb + hE), "EJE")
        V.dim_rad((0, tE / 2, tb + hE), R, 130, on=on, text=f"R{f(R)}", ext=18)
        V.dim_dia((0, tE / 2, tb + hE), dE / 2, 320, on=on, text=f"Ø{f(dE)} H12", ext=12)
        # B-46: una sola cota por elemento; ancho (= 2R) y altura total son auxiliares
        V.dimv((R, tE / 2, tb), (0, tE / 2, tb + hE), "right", 0, on=on, text=f"{f(hE)} ±1 (al centro del agujero)", virt_b=dE / 2)
        V.dimh((-R, tE / 2, tb), (R, tE / 2, tb), "bottom", 0, on=on, text=f"({f(2 * R)})")
        V.dimv((-R, tE / 2, tb), (0, tE / 2, tb + hE + R), "left", 0, on=on, text=f"({f(hE + R)})")
        w_out(p, jid, V, (R, tE / 2, tb + 3), "right", dy=26)
    p.ra_in("perfil", "Ra 12,5", [(-R, 0, tb + hE * 0.5), (R, 0, tb + hE * 0.5)], [(-1, 0), (1, 0)])
    p.ra_in("perfil", "Ra 6,3", prefix=f"Ø{f(dE)} H12")
    p.vs("perfil", on, "front", center=(0, 0, tb), lv=(1, 2, 2, 1), extra=(0, 0, 115, 0), draw=perfil, hatch=False, title="PERFIL", auto=False, w=1.5)

    def lateral(V, p):
        V.dimh((0, -tE / 2, tb + hE + R), (0, tE / 2, tb + hE + R), "top", 0, on=on, text=f"{f(tE)} (e)")
    # B-20: datum A = cara de apoyo (base) y perpendicularidad de la cara de la oreja, en la vista lateral
    p.datum_in("perfil", "surf", "A", at=[(-R * 0.65, tE / 2, tb), (R * 0.65, tE / 2, tb), (-R * 0.35, tE / 2, tb)], d=(0, 0, -1))
    p.gd_in("lateral", "surf", "perp", "0,5", "A", at=[(0, tE / 2, tb + hE * 0.7), (0, -tE / 2, tb + hE * 0.7)], d=[(0, 1, 0), (0, -1, 0)])
    p.vs("lateral", on, "right", center=(0, 0, tb), lv=(1, 1, 1, 1), extra=(40, 0, 40, 0), title="VISTA LATERAL (espesor)", draw=lateral, auto=False, w=0.7, maxs=1.0, hatch=False)
    add_prep(p, "det_j", wd(ctx, jid), t1=tE, t2=tb)

    p.tables([jid])
    p.notes([f"Plancha e = {f(tE)}; perfil 2R × h + semicírculo R{f(R)}; agujero Ø{f(dE)} H12 ({iso286.fmt_dev(dE, 'H12')}) mecanizado (taladro y mandrinado) después del corte, Ra 6,3, aristas 1×45°; grillete con pasador de Ø ≤ {fm(dE - P['g_ear'], 0)} mm (agujero Ø{f(dE)} menos {fm(P['g_ear'], 0)} mm de juego).",
             f"Posición en la base: (±{f(P['x_lug'])}, ±{f(g.cl_lug)}) ±1, plano vertical radial hacia el centro (plano BAS-001, tabla de posiciones).",
             f"Soldadura a la base: filete z{fm(P['w_ear'], 0)} a ambos lados (L = 2R), base de la oreja a escuadra sin bisel ({jid}); MT 100 % antes y después de la prueba de carga; UT de laminación de la plancha base bajo la oreja (ASTM A578 nivel B).",
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
    p.iso_keys = ["bancada_L"]
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
    p.datum_in("corte", "surf", "A", at=[(-P["w_bed"] / 2 + 15, 0, tb), (P["w_bed"] / 2 - 15, 0, tb)], d=(0, 0, -1))
    p.gd_in("corte", "surf", "par", "0,10", "A", at=[(P["w_slot"] / 2, 0, zb - P["h_slot"] / 2), (-P["w_slot"] / 2, 0, zb - P["h_slot"] / 2)], d=[(1, 0, 0), (-1, 0, 0)])
    p.gd_in("det_ranura", "surf", "pos", "Ø0,2", "A", at=[(-P["w_slot"] / 2, 0, zb - P["h_slot"] * 0.3), (P["w_slot"] / 2, 0, zb - P["h_slot"] * 0.3)], d=[(-1, 0, 0), (1, 0, 0)])
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
            gd=[("par", "0,10", "A", "Flancos de la ranura paralelos entre sí y a la cara de apoyo (A) en todo el largo"), ("pos", "Ø0,2", "A", "Ranura en posición respecto del eje de la bancada (alineada con el ojal de la ménsula)")])
    p.build()
    return p.h
