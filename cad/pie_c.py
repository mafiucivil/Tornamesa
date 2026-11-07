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
    p = Pieza(ctx, ["pivote"], f"PIVOTE Ø{f(P['D_piv'])} p6", fmt="auto")
    s = p.s
    on = ["pivote"]
    zA, zB = g.tb, g.tb + g.h_boss
    r = P["D_piv"] / 2
    p.iso_keys = ["pivote"]

    def elev(V, p):
        s.line(V.P(0, 0, -8), V.P(0, 0, g.L_piv + 8), "EJE")
        s.line(V.P(-r - 6, 0, zA), V.P(r + 6, 0, zA), "TRAT"); s.line(V.P(-r - 6, 0, zB), V.P(r + 6, 0, zB), "TRAT")
        V.dimv((-r, 0, zA), (-r, 0, zB), "left", 1, on=on, text=f"{fm(zB - zA, 0)} (zona en plancha base + collar, H7/p6)")
        V.dimv((-r, 0, 0), (-r, 0, zA), "left", 1, on=on, text=f"{fm(zA, 0)} (bajo la plancha)") if False else None
        ra(s, V, (r, 0, g.L_piv / 2), "Ra 0,8", dx=24, dy=0)
        V.dim_dia((0, 0, g.L_piv - 12), 4.25, 40, text="4 × M10-6H prof. 20 (broca Ø8,5)", on=on, ext=30) if False else None
    p.vs("elev", on, "front", lv=(2, 2, 2, 3), extra=(0, 0, 115, 0), draw=elev, hatch=False, title="ELEVACIÓN", w=1.5,
         auto=dict(rev=(0, 0), fits={P["D_piv"]: "p6"}, rev_side="top", tol={round(g.L_piv, 1): " ±0,1"}, hole_notes=False))
    p.vs("extremo", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), title="VISTA DE EXTREMO (cara superior)", hatch=False, w=1.0,
         auto=dict(hole_rmin=3.0, hole_txt={8.5: f"4 × M10-6H prof. {fm(g.cap_tap, 0)} (broca Ø8,5), PCD Ø{fm(g.cap_pcd, 0)}, a 45° + 90°·k"}, fits={}))
    p.vs("corte", ["pivote_45"], "front", cut=CUT_Y, win=(-r - 4, g.L_piv - 48, r + 4, g.L_piv + 4), lv=(1, 2, 1, 2), extra=(0, 0, 40, 0), title="CORTE B-B: AGUJEROS ROSCADOS M10", hs=0.5, w=1.0, maxs=2.0,
         auto=dict(rev=(0, 0), rev_side="top", hole_notes=False, tol={round(g.cap_tap, 1): " (roscado)"}))
    p.detail("det_ch", "elev", (r - 1.5, 0, g.L_piv - 1.5), 10, "A", lv=(1, 1, 1, 1), title="DETALLE A: CHAFLÁN DE EXTREMO (5:1)", maxs=5.0, hatch=False)
    p.tables()
    p.notes([f"Barra redonda Ø{f(P['D_piv'] + 5)} laminada/rectificada; torneado/rectificado externo en torno horizontal: Ø{f(P['D_piv'])} p6 ({iso286.fmt_dev(P['D_piv'], 'p6')} mm), Ra 0,8; largo {fm(g.L_piv, 1)}.",
             f"Material: {propuestas.grado(P['Fy_piv'], P['D_piv'], 'barra')}. Bonificado; certificado 3.1; UT de la barra.",
             f"Ajuste en plancha base y collar: {f(P['D_piv'])} H7/p6 (aprieto {iso286.fit(P['D_piv'], 'H7', 'p6')['cmin']}…{iso286.fit(P['D_piv'], 'H7', 'p6')['cmax']} µm): prensa o contracción con hielo seco. Ajuste en el buje: f7/F7.",
             f"Chaflanes {fm(g.ch_piv, 0)}×45° en ambos extremos (ISO 13715). Perpendicularidad de las caras extremas 0,05; cilindricidad 0,02.",
             f"Cara superior: 4 agujeros M10-6H prof. {fm(g.cap_tap, 0)} (ISO 262) en PCD Ø{fm(g.cap_pcd, 0)} para la tapa retenedora (PIV-003); profundidad útil de rosca ≥ 16.",
             "Retención axial del pivote: ajuste sin soldadura ni tope; A DEFINIR POR EL CALCULISTA (decisión del mandante: el cálculo no verifica la extracción axial)."],
            gd=[("cyl", "0,02", None, "Cilindricidad del Ø%s p6" % f(P["D_piv"])), ("perp", "0,05", "A", "Caras extremas perpendiculares al eje (A = Ø%s)" % f(P["D_piv"])),
                ("pos", "Ø0,2", "A", "Agujeros M10: posición respecto del eje del pivote")])
    p.build()
    return p.h


@pieza("buje")
def sheet_buje(ctx):
    g, P = ctx.g, ctx.P
    p = Pieza(ctx, ["buje"], "PIVOTE: BUJE AUTOLUBRICADO", fmt="auto")
    s = p.s
    on = ["buje"]
    zt = g.z_bush0 + P["L_bush"]
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 60, 0), title="PLANTA", w=1.0, auto=dict(fits={P["D_piv"]: "F7"}, hole_rmin=20))
    p.vs("corte", on, "front", cut=CUT_Y, lv=(1, 2, 2, 3), extra=(0, 0, 30, 0), title="CORTE A-A", hs=0.35, w=1.4,
         auto=dict(rev=(0, 0), fits={g.d_bush: "s6", P["D_piv"]: "F7"}, rev_side="top", tol={round(P["L_bush"], 1): " ±0,2"}, hole_notes=False))
    p.detail("det_ch", "corte", (-(g.d_bush / 2 - 1.5), 0, zt - 1.5), 12, "B", lv=(1, 1, 1, 1), title="DETALLE B: EXTREMO DEL BUJE", maxs=5.0)
    p.vs("elev", on, "front", lv=(1, 2, 2, 1), hatch=False, title="ELEVACIÓN", w=0.8, auto=dict(tol={round(P["L_bush"], 1): " ±0,2"}, holes=False), maxs=2.0)
    p.tables()
    p.notes([f"Buje autolubricado Ø{f(g.d_bush)} / Ø{f(P['D_piv'])} × {f(P['L_bush'])}: comercial o a medida (marca/modelo A DEFINIR POR CATÁLOGO; tipo exigido: bronce con lubricante sólido, presión ≤ {fm(P['p_bush'], 0)} MPa y μ ≤ {fm(P['mu_bush'], 2)} según el cálculo).",
             f"Ø exterior {f(g.d_bush)} s6 (aprieto en el cubo H7, prensado) y Ø interior {f(P['D_piv'])} F7 (juego con el pivote p6/f7), Ra 1,6; mecanizar en mandrinadora (sin torno vertical).",
             f"Montaje: el buje arranca {fm(P['g_bush'], 0)} mm sobre el collar (z = {fm(g.z_bush0, 1)} desde la cara inferior de la base).",
             "Aristas 1×45° (ISO 13715); sin pintura; entrega con certificado 3.1 del proveedor."],
            gd=[("coax", "Ø0,05", "A", "Ø interior coaxial con el exterior"), ("perp", "0,05", "A", "Caras extremas perpendiculares al eje")])
    p.build()
    return p.h


@pieza("tapa_ret", "tapa_insp")
def sheet_tapas(ctx):
    g, P = ctx.g, ctx.P
    ks = [k for k in ("tapa_ret", "tapa_insp") if ctx.m.get(k)]
    p = Pieza(ctx, ks, "PIVOTE: TAPAS RETENEDORA (PIV-003) E INSPECCIÓN (PIV-004)", fmt="auto")
    s = p.s
    spec = {"tapa_ret": (g.L_piv, g.cap_t, g.cap_D, g.cap_pcd, 4, 45.0, "TAPA RETENEDORA"), "tapa_insp": (g.z0 + g.hd - g.cb_t, g.cb_t, g.cb_D - 2, g.insp_pcd, 6, 30.0, "TAPA DE INSPECCIÓN")}
    rows = []
    for k in ks:
        zb_, L_, D_, pcd, n, a0, nm = spec[k]
        ct = ctx.code(k).replace(CODE + "-", "")
        zt = zb_ + L_
        p.vs(f"{k}_pl", [k], "top", lv=(1, 1, 1, 1), extra=(0, 0, 115, 0), title=f"{ct} — {nm}: PLANTA", hatch=False, w=1.0,
             auto=dict(hole_rmin=3.0, hole_txt={11.0: f"{n} × Ø11, avell. Ø20×90°, PCD Ø{fm(pcd, 0)}"}, fits={}))
        p.vs(f"{k}_co", [k], "front", cut=CUT_Y, lv=(1, 2, 2, 2), extra=(0, 0, 20, 0), title=f"{ct} — CORTE A-A", hs=0.35, w=1.0,
             auto=dict(rev=(0, 0), rev_side="top", hole_notes=False, tol={round(L_, 1): " ±0,2"}))
        for i in range(n):
            a = math.radians(a0 + 360 / n * i)
            rows.append([ct, f"{i + 1}", f"{fm(pcd / 2 * math.cos(a), 2)}", f"{fm(pcd / 2 * math.sin(a), 2)}", f"{fm((a0 + 360 / n * i) % 360, 1)}°", "Ø11 + avell. Ø20 90°"])
    p.table_block("COORDENADAS DE LOS AGUJEROS (origen: eje del pivote; PROPUESTA S15)", [("Pieza", 16, "C"), ("N°", 10, "C"), ("x [mm]", 24, "R"), ("y [mm]", 24, "R"), ("Ángulo", 20, "R"), ("Agujero", 38, "L")], rows)
    p.tables()
    p.notes([f"Tapa retenedora Ø{f(g.cap_D)} × {f(g.cap_t)}: fijada con 4 × M10×25 ISO 10642 10.9 (avellanado 90° Ø20) a los agujeros M10-6H prof. {fm(g.cap_tap, 0)} del extremo del pivote (PIV-001); Ra 3,2; oxicorte/plasma y agujeros en taladro radial.",
             f"Tapa de inspección Ø{f(g.cb_D - 2)} × {f(g.cb_t)} (apoyo en rebaje de la plancha superior MES-001), 6 × M10 avellanados a los agujeros M10-6H prof. {fm(g.insp_tap, 0)} del fondo del rebaje; sin función estructural.",
             "El patrón de agujeros es una PROPUESTA del dibujante (S15), geométricamente compatible con el pivote y la plancha superior; confirmar.",
             "Material de las tapas: ASTM A572 Gr.50 (Fy del cálculo), certificado 3.1.", "Tornillos: torque propuesto en GEN-008; marca/modelo por catálogo (GEN-008)."],
            gd=[("pos", "Ø0,2", "A", "Patrón de agujeros respecto del eje de la tapa"), ("flat", "0,10", None, "Planitud de la cara de apoyo")])
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
         auto=dict(text={round(abs(ye - yr), 1): f"{fm(abs(ye - yr), 1)} (L entre ejes de ojales)"}))
    def planta_c(V, p):
        V.dimv((X, ye, zc), (X, yr, zc), "right", 1, on=on, text=f"{fm(abs(ye - yr), 1)} (entre ejes de ojales, posición de empuje)", virt_a=P["d_pp"] / 2, virt_b=P["d_pp"] / 2)
    p.vs("planta", on, "top", hidden=False, lv=(1, 2, 2, 1), extra=(0, 0, 70, 0), draw=planta_c, title="PLANTA DEL CILINDRO", hatch=False, w=1.0, breaks=[(min(ye, yr) + 420, max(ye, yr) - 420)] if False else None,
         auto=dict(fits={P["d_pp"]: "H9"}, hole_rmin=10))
    p.detail("det_ojal", "planta", (X, ye, zc), 75, "A", lv=(1, 1, 1, 1), title="DETALLE A: OJAL CON RÓTULA (EXTREMO TRASERO)", maxs=2.0, hatch=False)
    p.detail("det_vast", "planta", (X, yr, zc), 75, "B", lv=(1, 1, 1, 1), title="DETALLE B: OJAL DEL VÁSTAGO", maxs=2.0, hatch=False)
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
            gd=[("par", "0,10", "A", "Ejes de los dos ojales paralelos entre sí (A = eje del ojal trasero)"), ("coax", "Ø0,20", "A", "Vástago coaxial con la camisa en la posición de empuje")])
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
    p.tables()
    p.notes([f"Pieza única sin soldadura, desde bloque de plancha gruesa a llama con sobremetal 5 mm; desbaste y alojamientos en mandrinadora/fresadora; Ø{f(P['d_pp'])} H9 en taladro radial.",
             f"Lengüeta T: cuello {f(g.neck_w)} f7 en ranura {f(P['w_slot'])} H8; cabeza {f(g.head_w)} × {f(g.head_h)} en {f(P['w_tee'])} × {f(P['h_tee'])}, 1 mm de juego por lado.",
             f"Alojamiento de la uña {f(P['dog_b'] + 2)} × {f(P['dog_h'] + 2)} H9; tapa {f(zsh - g.pk_top)} y fondo {f(g.pk_bot - zb)} sobre la bancada (espesor mínimo de pared {f(P['t_pk'])} mm).",
             f"Marco de boca e = {f(P['t_fw'])}; inset {f(KG['inset'])}; boca en x = {f(KG['mouthX'] - X, 1)} desde el eje de la guía.",
             f"Material: {propuestas.grado(P['Fy_shoe'], g.Hs, 'barra')}; certificado 3.1. Reacción de guía a calado {f(ctx.DV['Rguide'], 1)} kN (núcleo)."],
            gd=[("par", "0,05", "A", "Cara inferior de la lengüeta paralela a la cara de apoyo (A)"), ("perp", "0,05", "A", "Alojamiento de la uña perpendicular a la cara de empuje")])
    p.build()
    return p.h


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
    p.vs("corte_b", on, "right", cut=((L / 2, 0, 0), (-1, 0, 0)), center=(L / 2, -b / 2, zc), lv=(1, 2, 2, 1), title="CORTE B-B (sección transversal de la uña)", hs=0.5, w=0.8, maxs=2.0, auto=dict(tol={round(b, 1): " f8", round(hd_, 1): " f8"}))
    p.vs("corte_c", on, "front", cut=((0, -b / 2, 0), (0, 1, 0)), center=(0, 0, zc), lv=(1, 2, 2, 1), title="CORTE C-C (longitudinal por el eje)", hs=0.5, w=0.8, maxs=2.0, auto=dict(tol={round(L, 1): " ±0,2"}))
    p.tables()
    p.notes([f"Forja o bloque; 34CrNiMo6+QT (EN 10083-3), Re ≥ {f(P['Fy_dog'])} MPa medido en la propia forja, certificado 3.1; UT EN 10228-3.",
             temple_txt(P) + f" (fila «Profundidad mínima de temple» del núcleo: ≥ {fm(g.z_hard, 1)} mm); revenido; MT de la cara.",
             alivio_txt(P) + f": {fm(RELIEF, 0)} mm desde el borde superior e inferior de la cara; perfil de bombeo logarítmico con caída ≤ 0,05 mm (PROPUESTA, confirmar con el calculista).",
             "Rectificar la cara templada después del temple (rectificadora plana, sin torno). Planitud 0,05; Ra 0,8.",
             f"Ajuste en el alojamiento del patín {f(b)} H9/f8 × {f(hd_)} H9/f8; retorno radial {fm(KG['travel'], 1)} mm; resorte comercial (tipo y fuerza: GEN-008).",
             "Aristas 1×45° salvo la cara de empuje (0,5×45°)."],
            gd=[("flat", "0,05", None, "Cara de empuje plana"), ("perp", "0,05", "A", "Cara de empuje perpendicular a la base (A)")])
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
