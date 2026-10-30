"""Lámina F-03: lista de corte, programa de soldaduras, det. L (lubricación 4b) y det. M (guía embutida)."""
import math, json
import params as P, draw, calc as K
from common import Place

RHO = 7.85e-6


def f(x, d=0):
    return K.nf(x, d)


def kg_box(a, b, c):
    return a * b * c * RHO


def kg_cyl(d, l):
    return math.pi * d ** 2 / 4 * l * RHO


def cut_rows():
    m = {int(k): v for k, v in json.load(open("/home/claude/tt300/out/TT300-B_mass.json")).items()}
    A572 = "A572 Gr.50 – Z35"
    hole71 = kg_cyl(71, 40)
    R = [
        ["1", "Placa base (2 ranuras 40H8×10, Ø150H7)", "2410×2010×85", "2400×2000×80", 1, A572, m[1]],
        ["2a", "Mejilla ménsula (Ø71 H9 en línea)", "45×285×155", "40×280×150", 8, "A572 Gr.50", kg_box(40, 280, 150) - hole71],
        ["2b", "Respaldo ménsula", "45×165×155", "40×160×150", 4, "A572 Gr.50", kg_box(40, 160, 150)],
        ["3", "Oreja izaje (R60 sup., Ø32)", "40×155×175", "40×150×170", 4, "A572 Gr.50", m[3] / 4],
        ["22", "Guía de carro (embutida 10)", "45×45×855", "40 h9×40×850", 2, "S355J2", m[22] / 2],
        ["4a", "Plancha sup. (Ø300, 36×Ø71, 4×M30, ranuras)", "□2020×35", "Ø2000×30", 1, A572, 689.1],
        ["4b", "Plancha inf. (Ø300, 36×Ø71, ranuras lubr.)", "□2020×35", "Ø2000×30", 1, A572, 689.6],
        ["4c", "Cubo (forja)", "Ø310×170", "Ø300×160", 1, "S355J2+N forjado", 50.6],
        ["4d1", "Alma anillo R300, rolada (desarrollo eje)", "25×100×1 905", "L = 1 885", 1, "A572 Gr.50", kg_box(25, 100, 1885)],
        ["4d2", "Alma anillo R550, rolada", "25×100×3 476", "L = 3 456", 1, "A572 Gr.50", kg_box(25, 100, 3456)],
        ["4d3", "Alma anillo R735, rolada", "25×100×4 638", "L = 4 618", 1, "A572 Gr.50", kg_box(25, 100, 4618)],
        ["4e1", "Nervio radial R150–R287,5", "20×100×140", "20×100×137,5", 12, "A572 Gr.50", kg_box(20, 100, 137.5)],
        ["4e2", "Nervio radial R312,5–R537,5", "20×100×228", "20×100×225", 12, "A572 Gr.50", kg_box(20, 100, 225)],
        ["4e3", "Nervio radial R562,5–R722,5", "20×100×163", "20×100×160", 12, "A572 Gr.50", kg_box(20, 100, 160)],
        ["4e4", "Nervio radial R747,5–R880", "20×100×135", "20×100×132,5", 12, "A572 Gr.50", kg_box(20, 100, 132.5)],
        ["4f", "Barra de empuje (a ras tras mecanizar)", "Ø70×164", "Ø70×160", 36, "S355J2 laminado", kg_cyl(70, 160)],
        ["5", "Pivote (6×M20 en cabeza)", "Ø160×225", "Ø150 p6/f7×218", 1, "42CrMo4+QT", m[5]],
        ["6", "Buje autolubricado", "comercial", "Ø190 s6/Ø150 H7×100", 1, "CuAl10Ni5Fe4+graf.", m[6]],
        ["7", "Tapa retenedora", "250×250×25", "Ø240×20", 1, "S355J2", m[7]],
        ["10", "Carro de empuje (ranura 41×31)", "135×305×155", "130×300×150", 2, "S355J2+N", m[10] / 2],
        ["11", "Trinquete (asiento R36)", "255×95×100", "245×85×90", 2, "34CrNiMo6+QT", m[11] / 2],
        ["12", "Pasador ménsula / vástago (cabeza Ø90)", "Ø95×220", "Ø70 f8×200 + cab. 15", 4, "42CrMo4+QT", m[12] / 4],
        ["14", "Faldón de sello (perf. Ø24 en graseras)", "5×30×6 350", "5×30×6 300", 1, "NBR 70 Sh A", m[14]],
        ["15", "Fleje de apriete (perf. Ø24 en graseras)", "25×6×6 420", "rolado Ø2022", 1, "S235JR galv.", m[15]],
    ]
    return R


def sheet_f03(kind="S"):
    v = P.variant(kind); v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 3, 3, "FABRICACIÓN – LISTA DE CORTE, SOLDADURAS Y LUBRICACIÓN", "INDICADA")
    x0 = 28
    S.text("LISTA DE CORTE Y DESPIECE – CONJUNTO TT300-B (masas de piezas terminadas)", (x0, 579), 2.8, "TOP_LEFT", bold=True)
    rows = []
    tot = 0
    for sub, desc, bruto, fin, q, mat, kg in cut_rows():
        rows.append([sub, desc, bruto, fin, str(q), mat, f(kg, 1), f(kg * q, 1)])
        tot += kg * q
    rows.append(["", "TOTAL PIEZAS FABRICADAS (sin cilindros, pernos ni grasa)", "", "", "", "", "", f(tot, 0)])
    y = S.table(x0, 573, [("POS", 13, "C"), ("DESCRIPCIÓN", 92, "L"), ("CORTE / BRUTO", 38, "C"), ("TERMINADO", 44, "C"),
                          ("CANT.", 12, "C"), ("MATERIAL", 44, "L"), ("kg/u", 17, "R"), ("kg total", 20, "R")],
                rows, rh=6.6, h=2.6)
    S.mtext(["Sobremetal de mecanizado 2,5 mm/cara en caras funcionales; planchas cortadas con eje de laminación anotado.",
             "Almas 4d: largo bruto = desarrollo en eje neutro + 20 (recorte tras rolar); radio ±2, cierre con junta CJP (W11).",
             "Nervios 4e: largo final ajustado en obra a la distancia real entre almas (holgura de raíz 2 ±1)."],
            (x0, y - 3), h=2.5, ls=1.5)
    # --------- programa de soldaduras ---------
    yw = y - 20
    S.text("PROGRAMA DE SOLDADURAS (AWS D1.1/D1.1M:2020 – E7018 / ER70S-6, FEXX = 490 MPa)", (x0, yw), 2.8, "TOP_LEFT", bold=True)
    wr = [
        ["W1", "2a – 1", "CJP doble bisel 45°, raíz 3 + filete refuerzo 8", "280 × 2 × 8", "UT 100 %"],
        ["W2", "2b – 1", "Filete ambos lados", "16", "MT 100 %"],
        ["W3", "2b – 2a", "Filete ambos lados (vertical)", "16", "MT 100 %"],
        ["W4", "3 – 1", "Filete todo alrededor", "12", "MT 100 %"],
        ["W5", "22 – 1", "Filete ambos lados, continuo (fijación; carga por aplastamiento)", "8", "MT 100 %"],
        ["W6", "4c – 4b / 4c – 4a", "CJP bisel 45° c/respaldo, por el exterior del cubo", "t = 30", "UT 100 %"],
        ["W7", "4d – 4b", "Filete ambos lados, continuo", "8", "MT 100 %"],
        ["W8", "4e – 4b / 4c / 4d", "Filete ambos lados, continuo", "8", "MT 100 %"],
        ["W9", "4a – 4d / 4e", "Soldadura en ranura 22×80, relleno completo (88 un.)", "c/250", "MT 100 %"],
        ["W10", "4f – 4a / 4b", "PJP bisel 15 todo alrededor (E = 12), a ras y mecanizado", "15", "MT 100 %"],
        ["W11", "Empalmes 4d", "CJP a tope en V 60°, raíz 3 (1 por anillo)", "t = 25", "UT 100 %"],
    ]
    y = S.table(x0, yw - 5, [("JUNTA", 14, "C"), ("ELEMENTOS", 40, "L"), ("TIPO Y PREPARACIÓN", 152, "L"), ("TAMAÑO", 29, "C"), ("END", 25, "C")],
                wr, rh=6.4, h=2.55)
    S.mtext(["PRECALENTAMIENTO (AWS D1.1 Tabla 5.8, Cat. B; espesor mayor de la junta): t > 65 mm (pos 1): 110 °C;",
             "38 < t ≤ 65: 65 °C; 20 < t ≤ 38 (disco 4a–4f): 10 °C, se exige 50 °C mín. para eliminar humedad. Interpase ≤ 250 °C.",
             "Secuencia del disco: W7 → W8 → W6 (4b) → W10 (4b) → montar 4a → W9 → W6 (4a) → W10 (4a), soldando en cuadrantes",
             "opuestos. Alivio de tensiones 590–620 °C antes del mecanizado final (Notas generales, N° 5).",
             "W10: única soldadura que transmite el empuje de la barra; resistencia verificada sin aporte del aplastamiento (D-02)."],
            (x0, y - 3), h=2.45, ls=1.5)

    # =================== DET. L – VISTA INFERIOR 4b (1:12,5) ===================
    sc = 1 / 10
    cL = (470, 450)
    L = Place(cL, sc)
    S.circle(cL, 1000 * sc)
    S.circle(cL, 150 * sc, "FINA")
    S.circle(cL, 95 * sc)
    for k in range(P.N_BAR):
        a = math.radians(P.BAR_ANG0 + 10 * k)
        S.circle(L((P.R_BAR * math.cos(a), P.R_BAR * math.sin(a))), 35.5 * sc)
    for r in (350, 600, 850):
        S.circle(cL, r * sc, "VIS")
    for k in range(12):
        a = math.radians(30 * k)
        S.line(L((200 * math.cos(a), 200 * math.sin(a))), L((960 * math.cos(a), 960 * math.sin(a))), "VIS")
    for k in range(4):
        a = math.radians(45 + 90 * k)
        p0 = L((850 * math.cos(a), 850 * math.sin(a)))
        p1 = L((1000 * math.cos(a), 1000 * math.sin(a)))
        S.line(p0, p1, "OCU")
        S.circle(p0, 0.6 * 6 * sc * 4, "VIS")
        S.circle(p1, 1.6, "VIS")
    S.centerlines(cL, 1000 * sc, 4)
    S.view_title((cL[0], cL[1] + 116), "DETALLE L – CARA INFERIOR 4b (vista desde abajo)", "ESC. 1:10")
    S.leader(L((0, 350)), (cL[0] + 62, cL[1] + 104), "Ranura circ. R350 / R600 / R850", h=2.1)
    S.leader(L((600 * math.cos(math.radians(60)), 600 * math.sin(math.radians(60)))), (cL[0] - 40, cL[1] + 108), "12 ranuras radiales c/30° (0°…330°), R200→R960", h=2.1)
    a = math.radians(45)
    S.leader(L((1000 * math.cos(a), 1000 * math.sin(a))), (cL[0] + 110, cL[1] + 78), "4 graseras pos 20 a 45°+90°k (det. L2)", h=2.1)
    S.leader(L((P.R_BAR * math.cos(math.radians(-5)), P.R_BAR * math.sin(math.radians(-5)))), (cL[0] + 112, cL[1] - 40), "36 × Ø71 (barras 4f) – no cruzar con ranuras", h=2.1)
    S.leader(L((0, -95)), (cL[0] + 50, cL[1] - 110), "Cubo 4c Ø190 H7 (buje)", h=2.1)
    S.text("Ranuras radiales en ejes de nervios 4e (0°+30°k): libre ≥ 82 mm a barras 4f.", (cL[0] - 110, cL[1] - 118), 2.4, "TOP_LEFT")
    S.text("Mecanizar ranuras DESPUÉS del alivio de tensiones y del refrentado de 4b.", (cL[0] - 110, cL[1] - 123.5), 2.4, "TOP_LEFT")

    # =================== DET. L1 – sección de ranura 5:1 ===================
    o = (700, 520)
    s5 = 5.0
    S.view_title((o[0] + 20, o[1] + 20), "DET. L1 – RANURA", "ESC. 5:1", h=3.2)
    w = math.sqrt(9 - 1)
    outer = [(o[0] - 25, o[1]), (o[0] - w * s5, o[1])]
    arcpts = []
    for i in range(0, 21):
        t = math.pi + math.asin(1 / 3) + i / 20 * (math.pi - 2 * math.asin(1 / 3))
        arcpts.append((o[0] + 3 * s5 * math.cos(t), o[1] + 1 * s5 + 3 * s5 * math.sin(t)))
    poly = [(o[0] - 25, o[1])] + arcpts + [(o[0] + 25, o[1]), (o[0] + 25, o[1] + 22), (o[0] - 25, o[1] + 22)]
    S.pline([(o[0] - 25, o[1])] + arcpts + [(o[0] + 25, o[1])])
    S.hatch_poly(poly, scale=0.8)
    S.line((o[0] - 25, o[1] + 22), (o[0] + 25, o[1] + 22), "FINA")
    S.dim((o[0] - w * s5, o[1]), (o[0] + w * s5, o[1]), -13, "≈5,7", orient="h", h=2.2)
    S.dim((o[0] + 18, o[1]), (o[0] + 18, o[1] - 2 * s5), 6, "2", orient="v", h=2.2)
    S.leader(arcpts[14], (o[0] + 28, o[1] - 16), "R3", h=2.2)
    S.text("cara inf. 4b (contacto)", (o[0] - 25, o[1] + 1), 2.0, "BOTTOM_LEFT")
    S.text("Ra 1,6 – aristas matadas 0,5", (o[0] - 25, o[1] - 20), 2.0, "TOP_LEFT")

    # =================== DET. L2 – grasera (sección radial a 45°) 1:2 ===================
    s2 = 0.5
    g = Place((680, 305), s2, (850, 80))      # modelo: x radial, z
    pl = [g((800, 80)), g((1000, 80)), g((1000, 110)), g((800, 110))]
    S.pline(pl[:3] + [pl[3]])
    S.hatch_poly([g((800, 80)), g((849, 80)), g((849, 85)), g((847, 85)), g((847, 91)), g((1000 - 12, 91)), g((1000 - 12, 85)), g((1000, 85)),
                  g((1000, 110)), g((800, 110))], scale=0.6)
    S.hatch_poly([g((851, 80)), g((1000, 80)), g((1000, 85)), g((853, 85)), g((853, 80))], scale=0.6)
    S.line(g((850, 88)), g((1000, 88)), "EJE")
    S.line(g((850, 76)), g((850, 92)), "EJE")
    S.rect(*g((1000, 82.5)), *g((1006, 107.5)), "VIS")   # faldón (aprox.)
    S.rect(*g((1005, 82.5)), *g((1011, 107.5)), "VIS")   # fleje
    S.pline([g((1000, 84)), g((1027, 84)), g((1027, 92)), g((1000, 92))], "VIS")   # grasera
    S.circle(g((1029, 88)), 2.0)
    S.line(g((780, 80)), g((1040, 80)), "FINA")
    S.text("4b (sección)", g((805, 112)), 2.0, "BOTTOM_LEFT")
    S.view_title((g((900, 0))[0], g((0, 155))[1]), "DET. L2 – GRASERA (sección radial a 45°)", "ESC. 1:2", h=3.2)
    S.dim(g((850, 80)), g((1000, 80)), -9, "150 (R850→R1000)", orient="h", h=2.1)
    S.dim(g((800, 80)), g((800, 88)), -5, "8", orient="v", h=2.0)
    S.dim(g((800, 80)), g((800, 110)), -12, "30", orient="v", h=2.0)
    S.leader(g((930, 88)), (g((930, 0))[0], g((0, 130))[1] + 4), "Taladro radial Ø6 ciego, L 150", h=2.0)
    S.leader(g((850, 84)), (g((850, 0))[0] - 15, g((0, 62))[1]), "Taladro Ø6 a ranura R850", h=2.0)
    S.leader(g((1018, 92)), (g((1018, 0))[0] + 6, g((0, 130))[1] + 4), "Pos 20 M10×1, rosca L12", h=2.0)
    S.leader(g((1008, 82.5)), (g((1008, 0))[0] + 8, g((0, 64))[1]), "Faldón 14 + fleje 15: perf. Ø24", h=2.0)

    # =================== DET. M – guía embutida 1:1 ===================
    om = (735, 410)
    M = Place(om, 1.0, (P.X_CYL, P.TB))
    S.view_title((om[0], om[1] + 62), "DET. M – GUÍA POS 22 EMBUTIDA", "ESC. 1:1", h=3.2)
    xg0, xg1 = P.X_CYL - 20, P.X_CYL + 20
    # placa base con ranura
    base = [M((P.X_CYL - 55, P.TB - 30)), M((P.X_CYL + 55, P.TB - 30)), M((P.X_CYL + 55, P.TB)), M((xg1, P.TB)),
            M((xg1, P.TB - 10)), M((xg0, P.TB - 10)), M((xg0, P.TB)), M((P.X_CYL - 55, P.TB))]
    S.pline(base, closed=True)
    S.hatch_poly(base, scale=1.2)
    rail = [M((xg0, P.TB - 10)), M((xg1, P.TB - 10)), M((xg1, P.TB + 30)), M((xg0, P.TB + 30))]
    S.pline(rail, closed=True)
    S.hatch_poly(rail, scale=1.2, angle=90)
    for sx in (-1, 1):
        xe = P.X_CYL + sx * 20
        tri = [M((xe, P.TB)), M((xe + sx * 8, P.TB)), M((xe, P.TB + 8))]
        S.pline(tri, closed=True); S.hatch_poly(tri, solid=True)
    S.pline([M((P.X_CYL - 50, P.TB + 50)), M((P.X_CYL - 50, P.TB + 1)), M((P.X_CYL - 20.5, P.TB + 1)), M((P.X_CYL - 20.5, P.TB + 31)),
             M((P.X_CYL + 20.5, P.TB + 31)), M((P.X_CYL + 20.5, P.TB + 1)), M((P.X_CYL + 50, P.TB + 1)), M((P.X_CYL + 50, P.TB + 50))], "FANT")
    S.text("carro pos 10 (ranura 41 H11×31)", M((P.X_CYL - 50, P.TB + 52)), 2.0, "BOTTOM_LEFT")
    S.dim(M((xg0, P.TB - 10)), M((xg1, P.TB - 10)), -26, "40 H8/h9", orient="h", h=2.2)
    S.dim(M((xg1, P.TB - 10)), M((xg1, P.TB)), 40, "10", orient="v", h=2.2)
    S.dim(M((xg1, P.TB)), M((xg1, P.TB + 30)), 40, "30", orient="v", h=2.2)
    S.weld(M((xg0 - 3, P.TB + 2)), (M((xg0, 0))[0] - 18, M((0, P.TB + 22))[1]), "fillet", "8", other=True, note="W5")
    S.text("R = F·Δ/Lg = 264 kN por aplastamiento", (om[0] - 45, om[1] - 46), 2.1, "TOP_LEFT")
    S.text("en ranura (FU 0,57); W5 solo fija.", (om[0] - 45, om[1] - 50), 2.1, "TOP_LEFT")

    # =================== notas de control ===================
    ctl = ["CONTROL DIMENSIONAL Y ENSAYOS DE FABRICACIÓN",
           "• Placa base pos 1: planitud cara sup. 0,20 en Ø2000; ranuras 40 H8 paralelas al eje Y ±0,10 en 850.",
           "• Disco pos 4: planitud 4b 0,20; paralelismo 4a/4b 0,30; barras 4f PCD 1880 ±0,5, paso 10° ±0,05°.",
           "• Ranuras de lubricación: profundidad 2 +0,3/0; continuidad verificada inyectando grasa por cada",
           "  grasera hasta ver salida por la ranura R850 y las radiales (protocolo con fotografías).",
           "• Rugosidad caras de giro pos 1 y 4b: Ra 3,2 máx. (fresado/rectificado), sin rayas radiales.",
           "• UT de planchas pos 1, 4a, 4b: ASTM A578 nivel B. Trazabilidad: colada estampada en cada pieza.",
           "• Pos 5, 11, 12: certificado de temple y revenido + dureza (pos 11: 300–350 HB; pos 12: 28–34 HRC).",
           "• Masa total del conjunto pesada en balanza calibrada; tolerancia ±3 % respecto de esta lista."]
    S.mtext(ctl, (360, 250), h=2.6, ls=1.55, bold_first=True)
    return S, v


if __name__ == "__main__":
    S, v = sheet_f03("S")
    S.save("out/TT300-B-F-03.dxf", "out/TT300-B-F-03.pdf")
    import pymupdf
    pymupdf.open("out/TT300-B-F-03.pdf")[0].get_pixmap(dpi=90).save("out/TT300-B-F-03.png")
