"""Láminas de fabricación del pivote y del accionamiento: pivote, buje, tapas, cilindro, patín, uña y pasadores de articulación."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *
from pie_a import ra, wd
from soldadura_det import add_prep


@pieza("pivote")
def sheet_pivote_pieza(ctx):
    g, P = ctx.g, ctx.P
    rot_key(ctx, "pivote", "pivote_45", -45.0)
    D = P["D_piv"]
    p = Pieza(ctx, ["pivote"], f"PIVOTE Ø{f(D)}: ZONA p6 (CALADO) Y ZONA f7 (BUJE)", fmt="auto")
    s = p.s
    on = ["pivote"]
    r = D / 2
    zp6, zf7, Lp = g.z_p6, g.z_f7, g.L_piv
    p.iso_keys = ["pivote"]
    t_p6, t_f7 = tol_txt(D, "p6"), tol_txt(D, "f7")
    fp6, ff7 = iso286.fit(D, "H7", "p6"), iso286.fit(D, "F7", "f7")

    def elev(V, p):
        s.line(V.P(0, 0, -8), V.P(0, 0, Lp + 8), "EJE")
        # límites de zona (línea gruesa de trazo y punto ISO 128, tipo 04.2, junto a la superficie)
        for z_ in (zp6, zf7):
            s.line(V.P(-r - 6, 0, z_), V.P(-r + 6, 0, z_), "TRAT"); s.line(V.P(r - 6, 0, z_), V.P(r + 6, 0, z_), "TRAT")
        V.dimv((-r + g.ch_piv, 0, 0), (-r, 0, zp6), "left", 0, on=on, text=f"{fm(zp6, 0)} (zona p6: plancha base + collar)")
        V.dimv((-r + g.ch_piv, 0, 0), (-r, 0, zf7), "left", 1, on=on, text=f"{fm(zf7, 0)} (inicio zona f7: buje)")
        V.dimh((-r, 0, zp6 / 2), (r, 0, zp6 / 2), "bottom", 0, on=on, text=f"{t_p6} zona de calado")
    p.vs("elev", on, "front", lv=(2, 2, 2, 3), extra=(0, 0, 115, 0), draw=elev, hatch=False, title="ELEVACIÓN (dos zonas rectificadas)", w=1.5,
         auto=dict(rev=(0, 0), rev_only=[D], text={round(D, 1): f"{t_f7} zona del buje"}, rev_side="top", tol={round(Lp, 1): " ±0,1"}, hole_notes=False))
    # rugosidad y tolerancias geométricas sobre las superficies y cotas que controlan (B-20, N-14)
    p.ra_in("elev", "Ra 0,8", (r, 0, zf7 + (Lp - zf7) * 0.35), (1, 0))
    p.ra_in("elev", "Ra 0,8", (r, 0, zp6 * 0.3), (1, 0))
    p.datum_in("elev", "dim", "A", prefix=f"Ø{f(D)} p6")
    p.gd_in("elev", "dim", "coax", "Ø0,02", "A", prefix=f"Ø{f(D)} f7")
    p.gd_in("elev", "surf", "cyl", "0,02", None, at=[(r, 0, zf7 + (Lp - zf7) * 0.75), (-r, 0, zf7 + (Lp - zf7) * 0.6)], d=[(1, 0), (-1, 0)])
    p.gd_in("elev", "surf", "cyl", "0,02", None, at=[(r, 0, zp6 * 0.7), (-r, 0, zp6 * 0.55)], d=[(1, 0), (-1, 0)])
    p.gd_in("elev", "surf", "perp", "0,05", "A", at=[(r * 0.85, 0, Lp), (-r * 0.85, 0, Lp), (r * 0.85, 0, 0)], d=[(0, 1), (0, 1), (0, -1)])
    p.gd_in("extremo", "callout", "pos", "Ø0,2", "A", prefix="4 × M10-6H")
    rc = g.cap_pcd / 2
    thr = g.cap_thr                          # rosca útil (la punta del taladro y la salida del macho ocupan 4 mm)

    def extremo(V, p):
        p.cut_mark("extremo", "B", (-(r + 16) * math.cos(math.radians(45)), -(r + 16) * math.sin(math.radians(45)), Lp), ((r + 16) * math.cos(math.radians(45)), (r + 16) * math.sin(math.radians(45)), Lp), 135)
    p.vs("extremo", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), title="VISTA DE EXTREMO (cara superior)", hatch=False, w=1.0, draw=extremo,
         auto=dict(hole_rmin=3.0, hole_pos=False, verts=False, hole_txt={8.5: f"4 × M10-6H, rosca útil {fm(thr, 0)}, taladro Ø8,5 prof. {fm(g.cap_tap, 0)}, PCD Ø{fm(g.cap_pcd, 0)} a 45° + 90°·k"}, fits={}))

    def corte(V, p):
        zt, zb = Lp, Lp - g.cap_tap
        for sx in (1, -1):
            for e_ in (-5.0, 5.0):           # diámetro nominal de la rosca en línea fina (ISO 6410-1)
                s.line(V.P(sx * rc + e_, 0, zt), V.P(sx * rc + e_, 0, zt - thr), "FINA")
            s.line(V.P(sx * rc - 5.0, 0, zt - thr), V.P(sx * rc + 5.0, 0, zt - thr), "VIS")     # límite de la rosca útil
        V.dimv((rc + 4.25, 0, zb), (rc + 4.25, 0, zt), "right", 0, on=["pivote_45"], text=f"{fm(g.cap_tap, 0)} (taladro Ø8,5)")
        V.dimv((-rc - 4.25, 0, zt - thr), (-rc - 4.25, 0, zt), "left", 0, on=["pivote_45"], text=f"{fm(thr, 0)} (rosca útil M10-6H)")
    p.vs("corte", ["pivote_45"], "front", cut=CUT_Y, win=(-r - 4, Lp - 48, r + 4, Lp + 4), lv=(1, 1, 1, 1), extra=(0, 0, 40, 0), draw=corte, title="CORTE B-B: AGUJEROS ROSCADOS M10", hs=0.5, w=1.0, maxs=2.0, auto=False)
    p.detail("det_ch", "elev", (r - 1.5, 0, Lp - 1.5), 10, "C", lv=(1, 1, 1, 1), title="DETALLE C: CHAFLÁN DE EXTREMO (5:1)", maxs=5.0, hatch=False)
    p.tables()
    p.notes([f"Barra redonda Ø{f(D + 5)} laminada; torneado y rectificado externo en torno horizontal en dos zonas: Ø{f(D)} p6 ({iso286.fmt_dev(D, 'p6')}) de z = 0 a {fm(zp6, 0)} (calado en plancha base + collar) "
             f"y Ø{f(D)} f7 ({iso286.fmt_dev(D, 'f7')}) de z = {fm(zf7, 0)} a {fm(Lp, 0)} (buje); z desde la cara inferior del pivote. Transición de {fm(zf7 - zp6, 0)} mm (z = {fm(zp6, 0)} a {fm(zf7, 0)}): salida de muela cónica, sin garganta ni arista viva. Ra 0,8 en ambas zonas; largo {fm(Lp, 1)}.",
             f"Material: {propuestas.grado(P['Fy_piv'], D, 'barra')}. Bonificado; UT de la barra.",
             f"Ajustes (ISO 286-2): zona p6 en plancha base y collar H7/p6, aprieto {-fp6['cmax']}…{-fp6['cmin']} µm (prensa o contracción con hielo seco, la zona p6 entra primero); "
             f"zona f7 en el buje F7/f7, juego {ff7['cmin']:+d}/{ff7['cmax']:+d} µm. El buje no debe pasar sobre la zona p6.",
             f"Chaflanes {fm(g.ch_piv, 0)}×45° en ambos extremos (ISO 13715). Perpendicularidad de las caras extremas 0,05; cilindricidad 0,02 en cada zona.",
             f"Cara superior: 4 agujeros M10-6H, rosca útil {fm(g.cap_thr, 0)} y taladro Ø8,5 prof. {fm(g.cap_tap, 0)} (ISO 262), en PCD Ø{fm(g.cap_pcd, 0)} a 45° + 90°·k, para la tapa retenedora (PIV-003): "
             f"tornillo M10×{g.cap_L:.0f}, engrane {fm(g.cap_L - g.cap_t, 0)} (≥ 1,0·d) y punta {fm(g.cap_thr - (g.cap_L - g.cap_t), 0)} mm antes del fin de la rosca útil.",
             "Retención axial del pivote: ajuste sin soldadura ni tope; A DEFINIR POR EL CALCULISTA (decisión del mandante: el cálculo no verifica la extracción axial)."],
            gd=[("cyl", "0,02", None, f"Cilindricidad de cada zona (Ø{f(D)} p6 y Ø{f(D)} f7)"), ("coax", "Ø0,02", "A", f"Zona f7 coaxial con la zona p6 (A = eje de la zona p6)"),
                ("perp", "0,05", "A", "Caras extremas perpendiculares al eje A"), ("pos", "Ø0,2", "A", "Agujeros M10: posición respecto del eje A")])
    p.build()
    return p.h


@pieza("buje")
def sheet_buje(ctx):
    g, P = ctx.g, ctx.P
    p = Pieza(ctx, ["buje"], "PIVOTE: BUJE AUTOLUBRICADO (Ø INTERIOR F7 DESPUÉS DEL CALADO)", fmt="auto")
    s = p.s
    on = ["buje"]
    zt = g.z_bush0 + P["L_bush"]
    D = P["D_piv"]
    lf7 = iso286.limits(D, "F7")
    ff7 = iso286.fit(D, "F7", "f7")
    cob = None
    p.ra_in("corte", "Ra 1,6", (-D / 2, 0, g.z_bush0 + P["L_bush"] * 0.3), (1, 0))
    p.ra_in("corte", "Ra 1,6", (-g.d_bush / 2, 0, g.z_bush0 + P["L_bush"] * 0.7), (-1, 0))
    p.datum_in("corte", "dim", "A", prefix=f"Ø{f(g.d_bush)} s6")
    p.gd_in("corte", "dim", "coax", "Ø0,05", "A", prefix=f"Ø{f(D)} F7")
    p.gd_in("corte", "surf", "perp", "0,05", "A", at=(D / 2 + (g.d_bush - D) / 4, 0, zt), d=(0, 1))
    # B-56: el corte lleva las cotas funcionales y es la vista principal (escala mayor); la planta solo ubica el corte
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 2, 2, 3), extra=(0, 0, 30, 0), title="CORTE A-A (Ø interior F7 DESPUÉS del calado en el cubo)", hs=0.35, w=1.6, draw=cob,
         auto=dict(rev=(0, 0), fits={g.d_bush: "s6", D: "F7"}, rev_side="top", tol={round(P["L_bush"], 1): " ±0,2"}, hole_notes=False))
    def plb(V, p):
        p.cut_mark("planta", "A", (-g.d_bush / 2 - 4, 0, zt), (g.d_bush / 2 + 4, 0, zt), 90, ext=6.0)
    p.vs("planta", on, "top", lv=(0, 0, 0, 0), extra=(0, 0, 0, 0), title="PLANTA (ubicación del corte A-A)", w=0.5, maxs=0.5, draw=plb, auto=False)
    p.tables()
    p.notes([f"Buje autolubricado Ø{f(g.d_bush)} / Ø{f(D)} × {f(P['L_bush'])}: comercial o a medida (marca/modelo A DEFINIR POR CATÁLOGO; tipo exigido: bronce con lubricante sólido, presión ≤ {fm(P['p_bush'], 0)} MPa y μ ≤ {fm(P['mu_bush'], 2)} según el cálculo).",
             f"Ø exterior {f(g.d_bush)} s6 ({iso286.fmt_dev(g.d_bush, 's6')}): calado a prensa en el cubo H7 (MES-011). Ø interior {f(D)} F7 ({iso286.fmt_dev(D, 'F7')}) DESPUÉS DEL CALADO: el buje se suministra con "
             f"Ø interior {fm(D - 1, 0)} +0,2/0 (sobremetal 0,5 por lado) y, ya prensado en el cubo, se escaria o mandrina a F7 (el aprieto s6/H7 cierra el Ø interior).",
             f"Verificación después del calado y del mecanizado final (GEN-003; instructivo de montaje, paso 5): Ø interior {fm(lf7[0], 3)} / {fm(lf7[1], 3)} en 3 secciones × 2 direcciones; coaxial con el agujero H7 del cubo Ø0,05. "
             f"Juego resultante con la zona f7 del pivote (PIV-001): {ff7['cmin']:+d}/{ff7['cmax']:+d} µm. Ra 1,6 en el Ø interior.",
             f"Montaje: el buje arranca {fm(P['g_bush'], 0)} mm sobre el collar (z = {fm(g.z_bush0, 1)} desde la cara inferior de la base).",
             "Aristas 1×45° (ISO 13715); sin pintura; entrega con certificado 3.1 del proveedor."],
            gd=[("coax", "Ø0,05", "A", "Ø interior coaxial con el Ø exterior (A), después del calado"), ("perp", "0,05", "A", "Caras extremas perpendiculares al eje A")])
    p.build()
    return p.h


@pieza("tapa_ret", "tapa_insp")
def sheet_tapas(ctx):
    g, P = ctx.g, ctx.P
    ks = [k for k in ("tapa_ret", "tapa_insp") if ctx.m.get(k)]
    p = Pieza(ctx, ks, "PIVOTE: TAPAS RETENEDORA (PIV-003) E INSPECCIÓN (PIV-004)", fmt="auto")
    s = p.s
    spec = {"tapa_ret": (g.L_piv, g.cap_t, g.cap_D, g.cap_pcd, 4, 45.0, "TAPA RETENEDORA", g.clear_m10, g.cap_csk), "tapa_insp": (g.z0 + g.hd - g.cb_t, g.cb_t, g.cb_D - 2, g.insp_pcd, 6, 30.0, "TAPA DE INSPECCIÓN", g.insp_clear, g.insp_csk)}
    rows = []
    letras = {"tapa_ret": "A", "tapa_insp": "B"}
    for k in ks:
        zb_, L_, D_, pcd, n, a0, nm, dcl, dcs = spec[k]
        ct = ctx.code(k).replace(CODE + "-", "")
        zt = zb_ + L_
        lt = letras[k]
        rk = rot_key(ctx, k, k + "_r", -a0)          # copia girada: el 1.er agujero sobre +x para que el corte pase por él
        hole_t = f"{n} × Ø{fm(dcl, 0)}, avell. Ø{fm(dcs, 0)}×90°"

        def pl_(V, p, zt=zt, D_=D_, pcd=pcd, n=n, a0=a0, k=k, hole_t=hole_t, lt=lt, dcl=dcl):
            c3 = (0, 0, zt)
            s.circle(V.P(c3), pcd / 2 * V.scale, "EJE")
            s.centerlines(V.P(c3), D_ / 2 * V.scale, 6)
            V.dim_dia(c3, D_ / 2, a0 % (360 / n) - 25 if a0 % (360 / n) >= 25 else a0 % (360 / n) + 180 / n, on=[k], text=f"Ø{f(D_)}", ext=26)
            ah = a0 + 360 / n * (n // 2)          # agujero del lado izquierdo: llamada hacia afuera, lejos de la cota del Ø
            hp = (pcd / 2 * math.cos(math.radians(ah)), pcd / 2 * math.sin(math.radians(ah)), zt)
            V.note_hole(hp, dcl / 2, 180 - 35, f"{hole_t}, PCD Ø{fm(pcd, 0)} a {fm(a0 % (360 / n), 1)}° + {fm(360 / n, 0)}°·k (tabla)", ext=(D_ / 2 - pcd / 2) * V.scale + 22, on=[k],
                        lines=[hole_t, f"en PCD Ø{fm(pcd, 0)}, a {fm(a0 % (360 / n), 1)}° + {fm(360 / n, 0)}°·k", "(coordenadas en la tabla)"])
            ca, sa = math.cos(math.radians(a0)), math.sin(math.radians(a0))
            p.cut_mark(f"{k}_pl", lt, (-(D_ / 2 + 14) * ca, -(D_ / 2 + 14) * sa, zt), ((D_ / 2 + 14) * ca, (D_ / 2 + 14) * sa, zt), (a0 + 90) % 360)

        def co_(V, p, zt=zt, zb_=zb_, L_=L_, pcd=pcd, dcl=dcl, dcs=dcs, rk=rk, D_=D_):
            r_ = pcd / 2
            V.dimh((r_ - dcs / 2, 0, zt), (r_ + dcs / 2, 0, zt), "top", 0, on=[rk], text=f"Ø{fm(dcs, 0)}×90° (avellanado)")
            V.dimh((r_ + dcs / 2, 0, zt), (D_ / 2, 0, zt), "top", 1, on=[rk], text=f"{fm(D_ / 2 - r_ - dcs / 2, 1)} (borde)")
            V.dimv((D_ / 2, 0, zb_), (D_ / 2, 0, zt), "right", 1, on=[rk], text=f"{fm(L_, 0)} ±0,2")      # N-13: segundo nivel, lejos de la línea de referencia de la cota del borde
            V.dimh((r_ - dcl / 2, 0, zb_), (r_ + dcl / 2, 0, zb_), "bottom", 0, on=[rk], text=f"Ø{fm(dcl, 0)}")
        p.vs(f"{k}_pl", [k], "top", lv=(1, 1, 1, 1), extra=(70, 0, 40, 0), title=f"{ct} — {nm}: PLANTA", hatch=False, w=1.0, draw=pl_, auto=False)
        # letras de datum distintas de las de los cortes (A-A, B-B): C/D en la tapa retenedora, E/F en la de inspección
        dA, dB = ("C", "D") if k == "tapa_ret" else ("E", "F")
        mids = [a0 + 180.0 / n + 360.0 / n * j for j in range(n)]
        mids.sort(key=lambda a_: -math.sin(math.radians(a_)))
        p.datum_in(f"{k}_pl", "surf", dB, at=[(D_ / 2 * math.cos(math.radians(a_)), D_ / 2 * math.sin(math.radians(a_)), zt) for a_ in mids],
                   d=[(math.cos(math.radians(a_)), math.sin(math.radians(a_))) for a_ in mids])
        p.gd_in(f"{k}_pl", "callout", "pos", "Ø0,2", [dA, dB], prefix=hole_t)
        p.datum_in(f"{k}_co", "surf", dA, at=[(D_ / 2 - 3, 0, zb_), (pcd / 2 + dcs / 2 + 2, 0, zb_)], d=[(0, -1), (0, -1)])
        p.gd_in(f"{k}_co", "surf", "flat", "0,10", None, at=[(x_, 0, zb_) for x_ in (pcd / 2 + dcs / 2 + 1.5, pcd / 2 - dcl / 2 - 2, pcd / 2 - dcl / 2 - 12, pcd / 2 - dcl / 2 - 24, pcd / 2 - dcl / 2 - 36) if x_ > 8], d=(0, -1))
        p.vs(f"{k}_co", [rk], "front", cut=CUT_Y, center=(pcd / 2, 0, zb_ + L_ / 2), win=(-min(pcd / 2 - 5, dcs / 2 + 16), -L_ / 2 - 6, D_ / 2 - pcd / 2 + 6, L_ / 2 + 6), lv=(1, 2, 2, 2), extra=(0, 0, 20, 0), draw=co_,
             title=f"{ct} — CORTE {lt}-{lt} POR UN AGUJERO", hs=0.35, w=1.0, maxs=5.0, auto=False)
        for i in range(n):
            a = math.radians(a0 + 360 / n * i)
            x_, y_ = pcd / 2 * math.cos(a), pcd / 2 * math.sin(a)
            rows.append([ct, f"{i + 1}", fm(0.0 if abs(x_) < 0.005 else x_, 2), fm(0.0 if abs(y_) < 0.005 else y_, 2), f"{fm((a0 + 360 / n * i) % 360, 1)}°", f"Ø{fm(dcl, 0)} + avell. Ø{fm(dcs, 0)}×90°"])
    p.table_block("COORDENADAS DE LOS AGUJEROS (origen: eje del pivote; patrón PROPUESTO, supuesto S15 de GEN-009)", [("Pieza", 16, "C"), ("N°", 10, "C"), ("x [mm]", 24, "R"), ("y [mm]", 24, "R"), ("Ángulo", 20, "R"), ("Agujero", 38, "L")], rows)
    p.tables()
    ins = [f"Tapa retenedora Ø{f(g.cap_D)} × {f(g.cap_t)}: 4 × M10×{g.cap_L:.0f} ISO 10642 10.9 (avellanado Ø{fm(g.cap_csk, 0)}×90°; dk máx. 20) a los agujeros M10-6H del extremo del pivote (PIV-001: rosca útil {fm(g.cap_thr, 0)}, taladro {fm(g.cap_tap, 0)}); "
           f"engrane {fm(g.cap_L - g.cap_t, 0)} mm (≥ 1,0·d) y la punta queda {fm(g.cap_thr - (g.cap_L - g.cap_t), 0)} mm antes del fin de la rosca útil (no toca fondo). Ra 3,2; oxicorte/plasma y agujeros en taladro radial."]
    if "tapa_insp" in ks:
        bi = (g.cb_D / 2 - 1) - g.insp_pcd / 2 - g.insp_csk / 2
        ins.append(f"Tapa de inspección Ø{f(g.cb_D - 2)} × {f(g.cb_t)} (en el rebaje Ø{f(g.cb_D)} de la plancha superior MES-001): 6 × ISO 10642 M{fm(g.insp_d, 0)}×{g.insp_L} 10.9 a los agujeros M{fm(g.insp_d, 0)}-6H pasantes del fondo del rebaje (taladro Ø{fm(g.insp_drill, 1)} pasante, rosca en los {fm(g.insp_rem, 0)} mm del remanente; engrane {fm(g.insp_L - g.cb_t, 0)} ≥ 1,0·d); "
                   f"avellanado Ø{fm(g.insp_csk, 0)}×90° con borde {fm(bi, 1)} mm hasta el canto de la tapa (≥ {fm(BORDE_MIN, 0)}); sin función estructural.")
    p.notes(ins + ["Material de las tapas: ASTM A572 Gr.50 (Fy del cálculo) — PROPUESTO.", "Tornillos: torque propuesto en GEN-008; marca/modelo por catálogo (GEN-008)."],
            gd=[("pos", "Ø0,2", ["C", "D"], "Tapa retenedora: patrón de agujeros respecto de la cara de apoyo (C) y del eje del Ø exterior (D)"),
                ("pos", "Ø0,2", ["E", "F"], "Tapa de inspección: patrón de agujeros respecto de la cara de apoyo (E) y del eje del Ø exterior (F)"),
                ("flat", "0,10", None, "Planitud de la cara de apoyo de cada tapa")] if "tapa_insp" in ks else
               [("pos", "Ø0,2", ["C", "D"], "Patrón de agujeros respecto de la cara de apoyo (C) y del eje del Ø exterior (D)"), ("flat", "0,10", None, "Planitud de la cara de apoyo")])
    p.build()
    return p.h


@pieza("cilindro")
def sheet_cilindro(ctx):
    g, P, D = ctx.g, ctx.P, ctx.D
    c = D["cilindros"]["antihorario"][0]
    X, ye, yr = c["x"], c["eye"][1], c["rodEngage"][1]
    ctx.local("cilindro", "cil1", near=(X, (ye + yr) / 2, g.zc), r=500)
    zc = g.zc
    p = Pieza(ctx, ["cilindro"], "CILINDRO HIDRÁULICO DE DOBLE EFECTO (ELEMENTO COMERCIAL — DIMENSIONES DE INTERFAZ)", fmt="auto")
    s = p.s
    on = ["cil1"]
    ym = (ye + yr) / 2
    p.iso_keys = ["cil1"]
    ab = sorted([ye, yr])
    brk = [(ab[0] + 380, ab[1] - 380)] if abs(ye - yr) > 1000 else None

    def lat(V, p):
        s.line(V.P(X, ye + 90 * c["dir"], zc), V.P(X, yr - 90 * c["dir"], zc), "EJE") if False else None
    p.vs("lateral", on, "right", breaks=[(min(ye, yr) + 420, max(ye, yr) - 420)], lv=(1, 2, 1, 2), title="ELEVACIÓN LATERAL (posición de empuje, con rotura)", hatch=False, w=1.5,
         auto=dict(text={round(abs(ye - yr), 1): f"({fm(abs(ye - yr), 1)}: L entre ejes de ojales)"}))
    def planta_c(V, p):
        V.dimv((X, ye, zc), (X, yr, zc), "right", 1, on=on, text=f"({fm(abs(ye - yr), 1)}: entre ejes de ojales, posición de empuje)", virt_a=P["d_pp"] / 2, virt_b=P["d_pp"] / 2)
    p.vs("planta", on, "top", hidden=False, lv=(1, 2, 2, 1), extra=(0, 0, 70, 0), draw=planta_c, title="PLANTA DEL CILINDRO", hatch=False, w=1.0, breaks=[(min(ye, yr) + 420, max(ye, yr) - 420)] if False else None,
         auto=dict(fits={P["d_pp"]: "H9"}, hole_rmin=10))
    p.detail("det_ojal", "planta", (X, ye, zc), 75, "A", lv=(1, 1, 1, 1), title="DETALLE A: OJAL CON RÓTULA (EXTREMO TRASERO)", maxs=2.0, hatch=False)
    p.detail("det_vast", "planta", (X, yr, zc), 75, "B", lv=(1, 1, 1, 1), title="DETALLE B: OJAL DEL VÁSTAGO", maxs=2.0, hatch=False)
    rpp = P["d_pp"] / 2
    zt_eye = zc + P["b_eye"] / 2
    p.datum_in("det_ojal", "surf", "A", at=[(X + rpp * 0.7071, ye + rpp * 0.7071, zt_eye), (X - rpp * 0.7071, ye + rpp * 0.7071, zt_eye)], d=[(1, 1, 0), (-1, 1, 0)])
    p.gd_in("det_vast", "surf", "par", "0,10", "A", at=[(X + rpp * 0.7071, yr - rpp * 0.7071, zt_eye), (X - rpp * 0.7071, yr - rpp * 0.7071, zt_eye)], d=[(1, -1, 0), (-1, -1, 0)])
    p.gd_in("planta", "surf", "coax", "Ø0,20", "A", at=[(X + P["d_rod"] / 2, ym, zc + 1), (X - P["d_rod"] / 2, ym, zc + 1)], d=[(1, 0, 0), (-1, 0, 0)])
    rows = [["Diámetro de camisa", f"{f(P['D_bore'])} mm"], ["Diámetro de vástago", f"{f(P['d_rod'])} mm"], ["Carrera", f"{f(P['stroke'])} mm"],
            ["Largo ojal–ojal retraído", f"{f(P['L0'])} mm"], ["Diámetro exterior del cuerpo", f"{f(P['D_body'])} mm"], ["Presión nominal", f"{f(P['p_rated'])} psi = {fm(P['p_rated'] * 0.0689476, 0)} bar"],
            ["Presión de alivio", f"{f(P['p_relief'])} bar"], ["Ojales con rótula esférica autolubricada", f"ancho de ojal {f(P['b_eye'])} mm; Ø{f(P['d_pp'])} H9 (pasador {f(P['d_pp'])} f8); Ø105 exterior"], ["Masa de catálogo", f"{fm(P['m_cyl'], 0)} kg c/u"],
            ["Fabricante / código", "marca/modelo A DEFINIR POR CATÁLOGO (confirmar el largo ojal–ojal retraído y la geometría de extremos)"]]
    p.table_block("ESPECIFICACIÓN DE COMPRA", [("Característica requerida", 70, "L"), ("Valor (del cálculo)", 100, "L")], rows)
    p.tables()
    p.notes(["Elemento comercial: este plano fija solo las dimensiones de interfaz que el cálculo exige; el diseño interno es del fabricante.",
             f"Prueba hidráulica a 1,5 × {f(P['p_relief'])} bar con certificado de fábrica (EN 10204 3.1 / certificado de prueba).",
             "Ojales con rótula esférica autolubricada; sellos NBR/PU según el fabricante; protección de vástago (cromo duro) y pintura del fabricante.",
             f"Pasadores de articulación Ø{f(P['d_pp'])} f8 con placa de retención (ACC-005).", "Capacidad y velocidad: ver memoria de cálculo (capítulo de cilindros y bomba)."],
            gd=[("par", "0,10", "A", "Ejes de los dos ojales paralelos entre sí (A = agujero del ojal trasero)"), ("coax", "Ø0,20", "A", "Vástago coaxial con la camisa en la posición de empuje")])
    p.build()
    return p.h


@pieza("patin")
def sheet_patin(ctx):
    g, P, KG = ctx.g, ctx.P, ctx.g.KG
    c = ctx.D["cilindros"]["antihorario"][0]
    X, yr = c["x"], c["rodEngage"][1]
    ctx.local("patin", "patin_L", near=(X, yr + 200, g.zc), r=600, shift=(-X, -yr, 0))
    ws, rear, front, zsh, zb, zc = P["w_s"], KG["rear"], KG["front"], g.z_shoe, g.zb, g.zc
    yF = P["l_p"] - g.d_pin / 2
    p = Pieza(ctx, ["patin"], "PATÍN GUIADO CON LENGÜETA T Y MARCO DE BOCA (2 UNIDADES)", fmt="auto")
    s = p.s
    p.iso_keys = ["patin_L"]
    on = ["patin_L"]
    yc = yF - P["dog_b"] / 2
    pe = KG["pocketEnd"] - X
    bbp = ctx.shapes["patin_L"].BoundingBox()
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Plane
    so_ = ctx.shapes["patin_L"].Solids()[0]
    # horquilla del ojal del vástago y alivio: caras planas leídas del sólido (extremo del patín)
    yE = bbp.ymin
    fy = sorted({round(fc.Center().y, 2) for fc in so_.Faces() if BRepAdaptor_Surface(fc.wrapped).GetType() == GeomAbs_Plane and abs(abs(fc.normalAt().y) - 1) < 1e-6 and fc.Center().y < yE + 200})
    slots = []
    for yb in fy[1:]:
        fcs = [fc for fc in so_.Faces() if BRepAdaptor_Surface(fc.wrapped).GetType() == GeomAbs_Plane and abs(abs(fc.normalAt().y) - 1) < 1e-6 and abs(fc.Center().y - yb) < 0.05]
        for fc in fcs:
            b_ = fc.BoundingBox()
            if b_.xmax - b_.xmin < ws - 1:
                slots.append((yb, b_.xmin, b_.xmax, (b_.zmin + b_.zmax) / 2))

    from vistas import COTAS as _CT
    on_s = lambda q: _CT.dist_to_surface(q, ["patin_L"]) < 0.05
    slots = [t for t in slots if on_s((t[1], yE, t[3])) and on_s((t[2], yE, t[3])) and t[0] - yE < 160]

    def planta_h(V, p):
        seen = set()
        for yb, x0_, x1_, zm in slots:
            k_ = (round(yb, 1), round(x1_ - x0_, 1))
            if k_ in seen:
                continue
            seen.add(k_)
            V.dimv((x0_, yE, zm), (x0_, yb, zm), "left", None, on=on, text=f"{fm(yb - yE, 1)} (prof.)")
            V.dimh((x0_, yE, zm), (x1_, yE, zm), "bottom", None, on=on, text=f"{fm(x1_ - x0_, 1)}")
            if on_s((bbp.xmax, yE, zm)):
                V.dimh((x1_, yE, zm), (bbp.xmax, yE, zm), "bottom", None, on=on, text=f"{fm(bbp.xmax - x1_, 1)}")
    p.vs("planta", on, "top", center=(0, 100, zsh), hidden=True, lv=(1 + len(slots), 2 + len(slots), 2, 1), extra=(0, 0, 30, 0), title="PLANTA (alojamiento, horquilla y ojal en trazo)", w=1.5, hatch=False, draw=planta_h,
         auto=dict(fits={P["d_pp"]: "H9"}, hole_rmin=10, tol={round(KG["L_s"], 1): " ±1 (largo total)", round(ws, 1): " ±0,5"}))
    p.vs("corte_f", on, "front", cut=((0, yc, 0), (0, 1, 0)), center=(0, 0, zb), win=(-200, -55, 130, 150), lv=(2, 2, 2, 2), title="CORTE F-F (por el alojamiento de la uña)", hs=0.5, w=1.4,
         auto=dict(tol={round(g.neck_w, 1): " f7", round(g.head_w, 1): " h11", round(P["dog_h"] + 2, 1): " H9 (aloj. uña)"}))
    p.vs("lateral", on, "right", lv=(1, 2, 2, 1), title="ELEVACIÓN LATERAL", hatch=False, w=1.0, hidden=True, auto=dict())
    p.vs("corte_g", on, "right", cut=((0, 0, 0), (-1, 0, 0)), center=(0, 0, zb), lv=(1, 2, 1, 1), title="CORTE G-G (longitudinal, por el eje)", hs=0.5, w=1.0, auto=dict(tol={}), win=(-250, -60, 900, 150)) if False else None
    p.detail("det_t", "corte_f", (0, yc, g.zT0 + g.head_h / 2 + 4), 45, "A", lv=(1, 2, 1, 1), title="DETALLE A: LENGÜETA T (CUELLO Y CABEZA)", maxs=2.0, hs=0.3)
    p.datum_in("corte_f", "surf", "A", at=[(ws / 2 - 15, yc, zb), (-ws / 2 + 15, yc, zb)], d=(0, 0, -1))
    p.gd_in("corte_f", "surf", "par", "0,05", "A", at=[(-ws / 2 + 20, yc, zsh), (ws / 2 - 20, yc, zsh), (0, yc, zsh)], d=(0, 0, 1))
    p.gd_in("corte_f", "surf", "perp", "0,05", "A", at=[(ws / 2, yc, zb + 40), (-ws / 2, yc, zb + 40)], d=[(1, 0, 0), (-1, 0, 0)])
    p.tables()
    p.notes([f"Pieza única sin soldadura, desde bloque de plancha gruesa a llama con sobremetal 5 mm; desbaste y alojamientos en mandrinadora/fresadora; Ø{f(P['d_pp'])} H9 en taladro radial.",
             f"Lengüeta T: cuello {f(g.neck_w)} f7 en ranura {f(P['w_slot'])} H8; cabeza {f(g.head_w)} × {f(g.head_h)} en {f(P['w_tee'])} × {f(P['h_tee'])}, 1 mm de juego por lado.",
             f"Alojamiento de la uña {f(P['dog_b'] + 2)} × {f(P['dog_h'] + 2)} H9; tapa {f(zsh - g.pk_top)} y fondo {f(g.pk_bot - zb)} sobre la bancada (espesor mínimo de pared {f(P['t_pk'])} mm).",
             f"Marco de boca e = {f(P['t_fw'])}; inset {f(KG['inset'])}; boca en x = {f(KG['mouthX'] - X, 1)} desde el eje de la guía.",
             f"Material: {propuestas.grado(P['Fy_shoe'], g.Hs, 'barra')}; certificado 3.1. Reacción de guía a calado {f(ctx.DV['Rguide'], 1)} kN (núcleo)."] + _nota_ranura(ctx),
            gd=[("par", "0,05", "A", "Cara superior del patín paralela a la cara de apoyo (A)"), ("perp", "0,05", "A", "Caras laterales del patín perpendiculares a la cara de apoyo (A)")])
    p.build()
    return p.h


def _nota_ranura(ctx):
    """Modo 1 con leva: ranura de la tapa del patín para el perno del seguidor (núcleo, levaGuiada.fabricacion.ranura_tapa_patin)."""
    g = ctx.g
    if not g.FLG:
        return []
    rn = g.FLG["ranura_tapa_patin"]
    bb = ctx.shapes["patin_L"].BoundingBox()
    c = ctx.D["cilindros"]["antihorario"][0]
    w = rn["ancho"]
    xa, xb = rn["x"][0] + w / 2 - c["x"], rn["x"][1] - w / 2 - c["x"]
    return [f"Ranura de la tapa del alojamiento (perno del seguidor de la leva, núcleo): ancho {fm(w, 0)} pasante en la tapa, extremos R{fm(w / 2, 1)} con centros a x = {fm(xa - bb.xmin, 1)} y {fm(xb - bb.xmin, 1)} desde el borde "
            f"(= {fm(xa, 1)} y {fm(xb, 1)} desde el eje del patín), a {fm(rn['y_respecto_pasador_vastago'], 1)} del eje del pasador del vástago hacia la uña "
            f"(eje de la ranura a {fm(c['dir'] * rn['y_respecto_pasador_vastago'] - bb.ymin, 1)} / {fm(bb.ymax - c['dir'] * rn['y_respecto_pasador_vastago'], 1)} de los extremos del patín); ajuste del núcleo «H9/f8» con el perno Ø{fm(g.FLG['seguidor']['perno']['d'], 0)} (requiere núcleo, GEN-009)."]


@pieza("una")
def sheet_una(ctx):
    g, P, KG = ctx.g, ctx.P, ctx.g.KG
    c = ctx.D["cilindros"]["antihorario"][0]
    yF = c["pinStart"][1] - c["dir"] * g.d_pin / 2
    ctx.local("una", "una_L", near=(KG["tipX"] + 100, yF - 40, g.zc), r=300, shift=(-KG["tipX"], -yF, 0))
    L, b, hd_, zc = g.paw_L, P["dog_b"], P["dog_h"], g.zc
    zt = zc + hd_ / 2
    p = Pieza(ctx, ["una"], "UÑA DE EMPUJE (CARA PLANA TEMPLADA, CHAFLÁN DE RETORNO) (2 UNIDADES)", fmt="auto")
    s = p.s
    p.iso_keys = ["una_L"]
    on = ["una_L"]

    def planta(V, p):
        s.line(V.P(-15, -b / 2, zt), V.P(L + 15, -b / 2, zt), "EJE")
        s.line(V.P(0, 5, zt), V.P(L, 5, zt), "TRAT")
        s.text("Cara de empuje templada ≥ 55 HRC", (V.P(L * 0.3, 5, zt)[0], V.P(0, 5, zt)[1] + 3), T_N, "BOTTOM_LEFT")
        ra(s, V, (L * 0.5, 0, zt), "Ra 0,8", dy=14)
    p.vs("planta", on, "top", center=(0, -b / 2, zt), lv=(2, 2, 2, 2), draw=planta, hatch=False, title="PLANTA", w=1.5,
         auto=dict(tol={round(L, 1): " ±0,2", round(b, 1): " f8"}, text={round(g.ch_dx, 1): f"{fm(g.ch_dx, 1)} (chaflán, β = {fm(P['beta_ch'], 0)}°)"}))

    def elev(V, p):
        for zz, zz2 in ((zc + hd_ / 2, zc + hd_ / 2 - RELIEF), (zc - hd_ / 2, zc - hd_ / 2 + RELIEF)):
            s.line(V.P(0, 0, zz2), V.P(L, 0, zz2), "TRAT")
            V.dimv((L, 0, zz), (L, 0, zz2), "right", 1, on=on, text=f"{fm(RELIEF, 0)} (alivio)", outside=True)
    p.vs("elev", on, "front", center=(0, 0, zc), lv=(1, 2, 3, 2), draw=elev, hatch=False, title="ELEVACIÓN (cara de empuje)", w=1.3, auto=dict(tol={round(hd_, 1): " f8"}))
    p.vs("lateral", on, "right", center=(0, 0, zc), lv=(1, 2, 1, 1), hatch=False, title="VISTA LATERAL (sección de la uña)", w=0.8, auto=dict(tol={round(b, 1): " f8", round(hd_, 1): " f8"}), maxs=2.0)
    p.detail("det_ch", "planta", (g.ch_dx / 2, -b + g.ch_dy / 2, zt), 30, "A", lv=(1, 2, 1, 1), title="DETALLE A: CHAFLÁN DE RETORNO", maxs=2.0, hatch=False)
    p.datum_in("elev", "surf", "A", at=[(L * 0.6, -b / 2, zc + hd_ / 2), (L * 0.3, -b / 2, zc + hd_ / 2), (L * 0.8, -b / 2, zc + hd_ / 2)], d=(0, 0, 1))
    p.gd_in("planta", "surf", "flat", "0,05", None, at=[(L * 0.75, 0, zt), (L * 0.2, 0, zt)], d=(0, 1, 0))
    p.gd_in("lateral", "surf", "perp", "0,05", "A", at=[(L / 2, 0, zc + hd_ * 0.3), (L / 2, 0, zc - hd_ * 0.3)], d=(0, 1, 0))
    p.vs("corte_b", on, "right", cut=((L / 2, 0, 0), (-1, 0, 0)), center=(L / 2, -b / 2, zc), lv=(1, 2, 2, 1), title="CORTE B-B (sección transversal de la uña)", hs=0.5, w=0.8, maxs=2.0, auto=dict(tol={round(b, 1): " f8", round(hd_, 1): " f8"}))
    p.vs("corte_c", on, "front", cut=((0, -b / 2, 0), (0, 1, 0)), center=(0, 0, zc), lv=(1, 2, 2, 1), title="CORTE C-C (longitudinal por el eje)", hs=0.5, w=0.8, maxs=2.0, auto=dict(tol={round(L, 1): " ±0,2"}))
    p.tables()
    p.notes([f"Forja o bloque; 34CrNiMo6+QT (EN 10083-3), Re ≥ {f(P['Fy_dog'])} MPa medido en la propia forja, certificado 3.1; UT EN 10228-3.",
             temple_txt(P) + f" (fila «Profundidad mínima de temple» del núcleo: {g.z_hard_txt}); revenido; MT de la cara.",
             alivio_txt(P) + f": {fm(RELIEF, 0)} mm desde el borde superior e inferior de la cara; perfil de bombeo logarítmico con caída ≤ 0,05 mm (PROPUESTA, confirmar con el calculista).",
             "Rectificar la cara templada después del temple (rectificadora plana, sin torno). Planitud 0,05; Ra 0,8.",
             f"Ajuste en el alojamiento del patín {f(b)} H9/f8 × {f(hd_)} H9/f8; retorno radial {fm(KG['travel'], 1)} mm; resorte comercial (tipo y fuerza: GEN-008).",
             "Aristas 1×45° salvo la cara de empuje (0,5×45°)."],
            gd=[("flat", "0,05", None, "Cara de empuje plana"), ("perp", "0,05", "A", "Cara de empuje perpendicular a la cara superior (A)")])
    p.build()
    return p.h


@pieza("pasador_vastago", "pasador_ojal")
def sheet_pasadores_art(ctx):
    g, P, KG, BR = ctx.g, ctx.P, ctx.g.KG, ctx.g.BR
    c = ctx.D["cilindros"]["antihorario"][0]
    X, ye, yr = c["x"], c["eye"][1], c["rodEngage"][1]
    ctx.local("pasador_ojal", "po1", near=(X, ye, g.tb + 80), r=200, shift=(-X, -ye, 0))
    ctx.local("pasador_vastago", "pv1", near=(X, yr, g.zc), r=200, shift=(-X, -yr, 0))
    p = Pieza(ctx, ["pasador_vastago", "pasador_ojal"], f"PASADORES DE ARTICULACIÓN Ø{f(P['d_pp'])} f8 (VÁSTAGO Y OJAL TRASERO)", fmt="auto")
    s = p.s
    r = P["d_pp"] / 2
    p.iso_keys = ["pv1", "po1"]
    rows = []
    for i, (kk, kl) in enumerate((("pasador_vastago", "pv1"), ("pasador_ojal", "po1"))):
        bb = ctx.shapes[kl].BoundingBox()
        z0_, z1_ = bb.zmin, bb.zmax
        rows.append([ctx.code(kk).replace(CODE + "-", ""), "Vástago (patín)" if i == 0 else "Ojal trasero (ménsula)", f"Ø{f(P['d_pp'])} f8", fm(z1_ - z0_, 1), f"{fm(g.ch_pp, 0)}×45°", "2"])

        def el(V, p, z0_=z0_, z1_=z1_):
            s.line(V.P(0, 0, z0_ - 6), V.P(0, 0, z1_ + 6), "EJE")
            ra(s, V, (r, 0, (z0_ + z1_) / 2), "Ra 0,8", dx=24, dy=0)
        p.vs(f"el{i}", [kl], "front", lv=(1, 2, 2, 3), extra=(0, 0, 30, 0), draw=el, hatch=False, w=1.2,
             title=f"{ctx.code(kk).replace(CODE + '-', '')} — {'PASADOR DEL VÁSTAGO (patín)' if i == 0 else 'PASADOR DEL OJAL TRASERO (ménsula)'}",
             auto=dict(rev=(0, 0), fits={P["d_pp"]: "f8"}, rev_side="top", tol={round(z1_ - z0_, 1): " ±0,2"}, hole_notes=False))
    p.vs("extremo", ["pv1"], "top", lv=(1, 1, 1, 1), title="VISTA DE EXTREMO", hatch=False, w=0.7, maxs=2.0, auto=dict(hole_rmin=5.0))
    bb0 = ctx.shapes["pv1"].BoundingBox()
    p.datum_in("el0", "dim", "A", prefix=f"Ø{f(P['d_pp'])} f8")
    p.gd_in("el0", "surf", "cyl", "0,02", None, at=[(r, 0, bb0.zmin + bb0.zlen * f_) for f_ in (0.3, 0.7, 0.5)], d=(1, 0, 0))
    p.gd_in("el0", "surf", "perp", "0,05", "A", at=[(-r * 0.5, 0, bb0.zmin), (r * 0.5, 0, bb0.zmin), (-r * 0.5, 0, bb0.zmax), (r * 0.5, 0, bb0.zmax)], d=[(0, 0, -1), (0, 0, -1), (0, 0, 1), (0, 0, 1)])
    p.detail("det_ch", "el0", (r - 1, 0, ctx.shapes["pv1"].BoundingBox().zmax - 1), 8, "A", lv=(1, 1, 1, 1), title="DETALLE A: CHAFLÁN (5:1)", maxs=5.0, hatch=False)
    p.vs("corte", ["po1"], "front", cut=CUT_Y, lv=(1, 2, 2, 1), title="CORTE A-A DEL PASADOR DEL OJAL", hs=0.5, w=0.8, maxs=2.0, auto=dict(rev=(0, 0), rev_side="top", hole_notes=False, tol={}))
    p.table_block("VARIANTES DE LONGITUD", [("Pieza", 16, "C"), ("Aplicación", 40, "L"), ("Diámetro", 26, "L"), ("Largo [mm]", 20, "R"), ("Chaflán", 18, "C"), ("Cant", 10, "C")], rows)
    p.tables()
    p.notes([f"Barra rectificada Ø{f(P['d_pp'] + 5)}; corte y chaflanes {fm(g.ch_pp, 0)}×45° en torno horizontal; Ø{f(P['d_pp'])} f8 ({iso286.fmt_dev(P['d_pp'], 'f8')} mm), Ra 0,8.",
             f"Material: {propuestas.grado(P['Fy_pp'], P['d_pp'], 'barra')} (bonificado, 28–34 HRC de referencia); certificado 3.1.",
             f"Ajuste con los ojales H9/f8 (juego {iso286.fit(P['d_pp'], 'H9', 'f8')['cmin']}…{iso286.fit(P['d_pp'], 'H9', 'f8')['cmax']} µm), con grasa grafitada.",
             "Retención: placa y tornillo de catálogo (tipo y características en GEN-008); ranura de retención: PROPUESTA 4 × 8 de profundidad a 8 mm del extremo (confirmar).",
             "Largos: pasador del vástago desde z de la ménsula del patín; pasador del ojal sobre la ménsula (BR.H + 15)."],
            gd=[("cyl", "0,02", None, "Cilindricidad del Ø%s f8" % f(P["d_pp"])), ("perp", "0,05", "A", "Caras extremas perpendiculares al eje")])
    p.build()
    return p.h
