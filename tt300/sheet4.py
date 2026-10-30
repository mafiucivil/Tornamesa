"""Lámina 4: piezas mecánicas y soldadas."""
import math
import params as P, draw
from common import Place, masses, fmt_kg


def nf(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def hrect(S, pts, scale=0.6, angle=0, pattern="ANSI31"):
    S.pline(pts, "VIS", closed=True)
    S.hatch_poly(pts, scale=scale, angle=angle, pattern=pattern)


def tag(S, p, pos, name, mat, qty, mass):
    S.text(f"POS {pos} – {name}", p, 3.4, "BOTTOM_CENTER", bold=True)
    w = len(f"POS {pos} – {name}") * 3.4 * 0.6
    S.line((p[0] - w / 2, p[1] - 1.2), (p[0] + w / 2, p[1] - 1.2), "VIS")
    S.text(f"{mat} – Cant. {qty} – {mass} kg/u", (p[0], p[1] - 2.6), 2.3, "TOP_CENTER")


def sheet4(kind):
    v = P.variant(kind); v["proj"] = P.PROJ
    U = kind == "U"
    m = masses(v)
    S = draw.Sheet()
    S.frame(v, 4, 4, "PIEZAS MECÁNICAS Y SOLDADAS", "INDICADA")
    L = v["L_piv"]

    # ---------------- POS 5 PIVOTE 1:2 ----------------
    O = Place((75, 442), 0.5)
    r = 75
    prof = [(-r + 5, 0), (r - 5, 0), (r, 5), (r, L), (-r, L), (-r, 5)]
    S.pline([O(p) for p in prof], "VIS", closed=True)
    S.line(O((-r, P.TB)), O((r, P.TB)), "FINA")
    S.line(O((0, -8)), O((0, L + 8)), "EJE")
    for x in (-50, 50):
        S.line(O((x - 8.6, L)), O((x - 8.6, L - 40)), "OCU"); S.line(O((x + 8.6, L)), O((x + 8.6, L - 40)), "OCU")
        S.line(O((x - 10, L)), O((x - 10, L - 32)), "OCU"); S.line(O((x + 10, L)), O((x + 10, L - 32)), "OCU")
        S.line(O((x - 8.6, L - 40)), O((x + 8.6, L - 40)), "OCU")
    S.dim(O((-r, 0)), O((r, 0)), -8, "Ø150 p6 (+0,068/+0,043)")
    S.dim(O((-r, L)), O((r, L)), 6, "Ø150 f7 (-0,043/-0,083)")
    S.dim(O((r, 0)), O((r, P.TB)), 6, "80", orient="v")
    S.dim(O((r, 0)), O((r, L)), 18, nf(L), orient="v")
    S.leader(O((-r + 2.5, 2.5)), (O((0, 0))[0] - 30, O((0, -48))[1]), "5×45°", h=2.3)
    S.leader(O((50, L - 20)), (O((0, 0))[0] + 50, O((0, L + 25))[1]), "6× M20 prof. 32 (Ø17,5 prof. 40) s/ PCD 100", h=2.2)
    S.finish(O((-r, P.TB + 40)), "Ra 0,8")
    S.text("Zona p6", O((-r + 8, 40)), 2.1, "MIDDLE_LEFT")
    S.text("Zona f7", O((-r + 8, P.TB + 40)), 2.1, "MIDDLE_LEFT")
    tag(S, (75, 412), 5, "PIVOTE", "42CrMo4+QT, 280–330 HB", 1, fmt_kg(m[5]))

    # ---------------- POS 6 BUJE 1:2 ----------------
    O = Place((190, 488), 0.5)
    for s in (-1, 1):
        pts = [O((s * 75, 0)), O((s * 95, 0)), O((s * 95, P.L_BUJE)), O((s * 75, P.L_BUJE))]
        hrect(S, pts, pattern="ANSI33", scale=0.5)
        for z in (15, 37.5, 60):
            S.circle(O((s * 85, z)), 2.5, "FINA")
    S.line(O((0, -8)), O((0, P.L_BUJE + 8)), "EJE")
    S.dim(O((-95, 0)), O((95, 0)), -8, "Ø190 s6 (+0,151/+0,122)")
    S.dim(O((-75, P.L_BUJE)), O((75, P.L_BUJE)), 6, "Ø150 H7 (+0,040/0)")
    S.dim(O((95, 0)), O((95, P.L_BUJE)), 6, nf(P.L_BUJE), orient="v")
    S.text("Insertos de grafito sólido Ø10,", O((-95, -38)), 2.2, "TOP_LEFT")
    S.text("≈ 25 % superficie de deslizamiento", O((-95, -44)), 2.2, "TOP_LEFT")
    S.text("Chaflán interior 2×30° ambos extremos", O((-95, -50)), 2.2, "TOP_LEFT")
    tag(S, (190, 412), 6, "BUJE", "CuAl10Ni5Fe4 + grafito", 1, fmt_kg(m[6]))

    # ---------------- POS 7 TAPA 1:2 ----------------
    O = Place((305, 512), 0.5)
    c = O((0, 0))
    S.circle(c, 60); S.centerlines(c, 60, 4)
    S.circle(c, 25, "EJE")
    for k in range(6):
        a = math.radians(30 + 60 * k)
        p = O((50 * math.cos(a), 50 * math.sin(a)))
        S.circle(p, 5.5); S.circle(p, 8.25)
    S.dim_dia(c, 60, 35, "Ø240")
    S.leader(O((50 * math.cos(math.radians(150)), 50 * math.sin(math.radians(150)))), (c[0] - 30, c[1] + 66), "6× Ø22 / avell. Ø33×13 s/ PCD 100", h=2.2)
    Os = Place((305, 440), 0.5)
    pts = [Os(p) for p in [(-120, 0), (120, 0), (120, 20), (-120, 20)]]
    S.pline(pts, "VIS", closed=True)
    for x in (-50, 50):
        S.line(Os((x - 11, 0)), Os((x - 11, 7)), "OCU"); S.line(Os((x + 11, 0)), Os((x + 11, 7)), "OCU")
        S.line(Os((x - 16.5, 7)), Os((x - 16.5, 20)), "OCU"); S.line(Os((x + 16.5, 7)), Os((x + 16.5, 20)), "OCU")
    S.dim(Os((120, 0)), Os((120, 20)), 6, "20", orient="v")
    tag(S, (305, 428), 7, "TAPA RETENEDORA", "S355J2", 1, fmt_kg(m[7]))

    # ---------------- POS 11 TRINQUETE 1:2,5 ----------------
    sc = 0.4
    O = Place((375, 505), sc)
    xs = 936.4 - P.PAWL_TIP
    dz = math.sqrt(P.SEAT_R ** 2 - xs ** 2)
    a0 = math.degrees(math.atan2(-dz, -xs))
    arc = [(xs + P.SEAT_R * math.cos(math.radians(t)), 85 + P.SEAT_R * math.sin(math.radians(t))) for t in [a0 + (0 - a0) * i / 20 for i in range(21)]]
    outline = [(0, 35)] + arc + [(245, 85), (245, 0), (60, 0)]
    pts = [O(p) for p in outline]
    S.pline(pts, "VIS", closed=True)
    S.rect(*O((205, 16.5)), *O((245, 68.5)), "OCU")
    S.line(O((-10, 42.5)), O((255, 42.5)), "EJE")
    S.dim(O((0, 85)), O((245, 85)), 14, "245")
    S.dim(O((245, 0)), O((245, 85)), 6, "85 f8", orient="v")
    S.dim(O((0, 85)), O((xs, 85)), 6, nf(xs, 1))
    S.dim_rad(O((xs, 85)), P.SEAT_R * sc, -60, "R36", ext=6)
    S.dim(O((0, 0)), O((60, 0)), -6, "60")
    S.dim(O((0, 0)), O((0, 35)), -6, "35", orient="v")
    S.text("Asiento de barra Ø70", O((80, 95)), 2.0, "BOTTOM_LEFT")
    S.text("Alojamiento resorte Ø52 prof. 40", O((120, -22)), 2.0, "TOP_LEFT")
    O2 = Place((375, 445), sc)
    S.rect(*O2((0, 0)), *O2((245, 90)))
    S.line(O2((xs - P.SEAT_R + 4.6, 0)), O2((xs - P.SEAT_R + 4.6, 90)), "OCU")
    S.line(O2((xs + P.SEAT_R, 0)), O2((xs + P.SEAT_R, 90)), "OCU")
    S.line(O2((205, 19)), O2((245, 19)), "OCU"); S.line(O2((205, 71)), O2((245, 71)), "OCU"); S.line(O2((205, 19)), O2((205, 71)), "OCU")
    S.dim(O2((245, 0)), O2((245, 90)), 6, "90 f8", orient="v")
    S.leader(O2((245, 45)), (O2((245, 0))[0] + 14, O2((0, 110))[1]), "Manilla M12 (desenganche)", h=2.0)
    tag(S, (420, 428), 11, "TRINQUETE", "34CrNiMo6+QT, 300–350 HB, MT 100 %", 2, fmt_kg(m[11] / 2))

    # ---------------- POS 10 CARRO DE EMPUJE 1:2,5 ----------------
    Hs = v["shoe_top"] - P.TB
    zc = v["z_axis"] - P.TB
    L, Wd = P.SHOE_L, P.SHOE_X1 - P.SHOE_X0
    pf, pb = P.SHOE_FRONT - 0.5, P.SHOE_FRONT + P.PAWL_W + 0.5
    eye = P.SHOE_FRONT + P.EYE_OFF
    # planta: largo horizontal (0 = frente), ancho vertical (0 = cara interior, lado disco)
    O = Place((520, 492), sc)
    S.rect(*O((0, 0)), *O((L, Wd)))
    S.rect(*O((pf, 0)), *O((pb, Wd)), "OCU")
    S.rect(*O((190, (Wd - 80) / 2)), *O((L, (Wd + 80) / 2)))
    S.line(O((eye, -8)), O((eye, Wd + 8)), "EJE")
    S.line(O((-8, Wd / 2)), O((L + 8, Wd / 2)), "EJE")
    S.dim(O((0, Wd)), O((L, Wd)), 6, "300")
    S.dim(O((0, Wd)), O((pf, Wd)), 14, nf(pf, 1))
    S.dim(O((pf, Wd)), O((pb, Wd)), 14, "86 H9")
    S.dim(O((0, Wd)), O((eye, Wd)), 22, nf(eye))
    S.dim(O((L, 0)), O((L, Wd)), 6, "130", orient="v")
    S.dim(O((L, (Wd - 80) / 2)), O((L, (Wd + 80) / 2)), 16, "80 H11", orient="v")
    S.text("lado disco", O((5, -6)), 2.0, "TOP_LEFT")
    S.text("frente (empuje →)", O((5, -14)), 2.0, "TOP_LEFT") if False else None
    # elevación lateral
    O2 = Place((520, 418), sc)
    S.rect(*O2((0, 0)), *O2((L, Hs)))
    S.rect(*O2((pf, zc - 45.5)), *O2((pb, zc + 45.5)))
    S.rect(*O2((0, 0)), *O2((L, 31)), "OCU")
    S.rect(*O2((190, zc - 65)), *O2((L, Hs)), "OCU")
    S.circle(O2((eye, zc)), 35.5 * sc); S.centerlines(O2((eye, zc)), 35.5 * sc, 3)
    S.line(O2((-8, zc)), O2((L + 8, zc)), "EJE")
    S.dim(O2((L, 0)), O2((L, Hs)), 6, nf(Hs), orient="v")
    S.dim(O2((0, 0)), O2((0, zc)), -6, nf(zc), orient="v")
    S.dim(O2((0, zc - 45.5)), O2((0, zc + 45.5)), -16, "91 H9", orient="v")
    S.leader(O2((eye + 12, zc + 12)), (O2((eye, 0))[0] + 12, O2((0, Hs + 22))[1]), "Ø71 H9 (pasador pos 12)", h=2.0)
    S.text("Ranura guía 41 H11 × 31 (inferior)", O2((5, -6)), 2.0, "TOP_LEFT")
    S.text("Ranura lubricada con grasa grafitada pos 19", O2((5, -12)), 2.0, "TOP_LEFT")
    tag(S, (580, 396), 10, "CARRO DE EMPUJE", "S355J2+N", 2, fmt_kg(m[10] / 2))

    # ---------------- POS 12 PASADOR Ø70 1:2 ----------------
    O = Place((720, 540), 0.5)
    S.pline([O(p) for p in [(0, -35), (195, -35), (200, -30), (200, 30), (195, 35), (0, 35)]], "VIS", closed=True)
    S.rect(*O((-15, -45)), *O((0, 45)))
    S.line(O((-22, 0)), O((210, 0)), "EJE")
    S.circle(O((188, 0)), 4.5); S.line(O((188, -40)), O((188, 40)), "EJE")
    S.dim(O((0, 35)), O((200, 35)), 6, "200")
    S.dim(O((-15, 45)), O((0, 45)), 6, "15", outside=True)
    S.dim(O((200, -35)), O((200, 35)), 6, "Ø70 f8", orient="v")
    S.dim(O((-15, -45)), O((-15, 45)), -5, "Ø90", orient="v")
    S.dim(O((0, -35)), O((188, -35)), -8, "188")
    S.leader(O((188, 0)), (O((0, 0))[0] + 60, O((0, 75))[1]), "Ø9 pasante (clip R pos 13)", h=2.1)
    tag(S, (765, 495), 12, "PASADOR Ø70", "42CrMo4+QT, 280–330 HB", 4, fmt_kg(m[12] / 4))

    # ---------------- POS 2 MÉNSULA 1:5 ----------------
    hc = v["H_cheek"]; zh = v["z_axis"] - P.TB
    s5 = 0.2
    # planta
    O = Place((70, 320), s5)
    for sd in (-1, 1):
        xa, xb = sd * 40, sd * 80
        S.rect(*O((min(xa, xb), -140)), *O((max(xa, xb), 140)))
    S.rect(*O((-80, -180)), *O((80, -140)))
    S.line(O((-100, 0)), O((100, 0)), "EJE"); S.line(O((0, -200)), O((0, 165)), "EJE")
    S.dim(O((-80, 140)), O((80, 140)), 5, "160")
    S.dim(O((-40, 140)), O((40, 140)), 12, "80")
    S.dim(O((80, -140)), O((80, 140)), 5, "280", orient="v")
    S.dim(O((80, -180)), O((80, -140)), 5, "40", orient="v", outside=True)
    S.dim(O((-80, -180)), O((-80, 0)), -5, "180", orient="v")
    S.text("Respaldo hacia el exterior", O((-80, -205)), 2.1, "TOP_LEFT")
    S.text("(lado opuesto al disco)", O((-80, -230)), 2.1, "TOP_LEFT")
    # lateral (y-z)
    O2 = Place((165, 262), s5)
    S.rect(*O2((-140, 0)), *O2((140, hc)))
    S.rect(*O2((-180, 0)), *O2((-140, hc)))
    S.circle(O2((0, zh)), 35.5 * s5 * 5 * 0.2 / 0.2 * 0.2 / 0.2 if False else 7.1)
    S.centerlines(O2((0, zh)), 7.1, 3)
    S.dim(O2((140, 0)), O2((140, hc)), 6, nf(hc), orient="v")
    S.dim(O2((140, 0)), O2((140, zh)), 14, nf(zh), orient="v")
    S.dim(O2((-180, hc)), O2((140, hc)), 5, "320")
    S.leader(O2((25, zh + 25)), (O2((0, 0))[0] + 20, O2((0, hc + 40))[1]), "Ø71 H9 (mecanizar en línea)", h=2.2)
    S.weld(O2((-140, 0)), (O2((0, 0))[0] - 10, O2((0, -45))[1]), "cjp", "CJP", other=True, note="mejillas-base")
    S.weld(O2((-170, 0)), (O2((0, 0))[0] - 50, O2((0, -80))[1]), "fillet", "16", other=True, all_round=True, note="respaldo")
    S.text("Base pos 1", O2((60, -12)), 2.0, "TOP_LEFT")
    S.line(O2((-260, 0)), O2((240, 0)), "VIS")
    tag(S, (120, 212), 2, "MÉNSULA DE REACCIÓN (SOLDADA)", "A572 Gr.50, e = 40", 4, fmt_kg(m[2] / 4))
    S.text("ESCALA 1:5", (120, 202), 2.3, "TOP_CENTER")

    # ---------------- POS 3 OREJA 1:2 ----------------
    O = Place((255, 260), 0.5)
    r60 = 60
    pts = [(0, 0), (150, 0), (150, 170 - r60)]
    arc = [(150 - r60 + r60 * math.cos(math.radians(a)), 170 - r60 + r60 * math.sin(math.radians(a))) for a in range(0, 91, 10)]
    arc2 = [(r60 - r60 * math.cos(math.radians(a)), 170 - r60 + r60 * math.sin(math.radians(a))) for a in range(90, -1, -10)]
    S.pline([O(p) for p in pts + arc + arc2 + [(0, 170 - r60)]], "VIS", closed=True)
    S.circle(O((75, 100)), 8); S.centerlines(O((75, 100)), 8, 3)
    S.dim(O((0, 0)), O((150, 0)), -8, "150")
    S.dim(O((150, 0)), O((150, 170)), 6, "170", orient="v")
    S.dim(O((0, 0)), O((0, 100)), -6, "100", orient="v")
    S.dim(O((0, 170)), O((75, 170)), 6, "75")
    S.leader(O((75 + 8 * 0.7 * 2, 100 + 8 * 0.7 * 2)), (O((0, 0))[0] + 60, O((0, 210))[1]), "Ø32 (grillete 4,75 t)", h=2.2)
    S.dim_rad(O((150 - r60, 170 - r60)), 30, 50, "R60", ext=6)
    S.text("Espesor 40. Borde exterior a ras con canto de pos 1.", O((0, -30)), 2.1, "TOP_LEFT")
    S.weld(O((0, 0)), (O((0, 0))[0] - 18, O((0, 40))[1]), "fillet", "12", other=True, all_round=True)
    tag(S, (292, 212), 3, "OREJA DE IZAJE", "A572 Gr.50", 4, fmt_kg(m[3] / 4))

    # ---------------- POS 9 CILINDRO (especificación) 1:5 ----------------
    O = Place((395, 330), 0.2)
    S.circle(O((0, 0)), 12); S.circle(O((0, 0)), 7.1)
    S.rect(*O((60, -70)), *O((330, 70)))
    S.rect(*O((330, -45)), *O((390, 45)))
    S.circle(O((450, 0)), 12); S.circle(O((450, 0)), 7.1)
    S.line(O((-80, 0)), O((700, 0)), "EJE")
    S.dim(O((0, 70)), O((450, 70)), 10, "L0 = 450 ±10 (retraído)")
    S.dim(O((0, -70)), O((650, -70)), -10, "650 (extendido, carrera 200)")
    S.dim(O((200, -70)), O((200, 70)), 0.01, "Ø ≤ 140")
    S.leader(O((450 + 8, 8)), (O((0, 0))[0] + 130, O((0, 140))[1]), "Ojal Ø70 con rótula GE70 (ambos)", h=2.2)
    spec = ["ESPECIFICACIÓN CILINDRO POS 9 (comercial, 2 un.)",
            "• Doble efecto, retorno hidráulico. Presión máx. 700 bar.",
            "• Fuerza de empuje ≥ 445 kN a 700 bar (clase 50 t).",
            "• Carrera 200 mm (36 libre + 164 de empuje). Ojales Ø70, rótula GE70.",
            "• Acoplamientos CR400 hembra; mangueras 700 bar.",
            "• Colector común con bloqueo: no permitir empuje de un solo cilindro;",
            "  y manómetro glicerina 0–1000 bar a la vista del operador.",
            "• Si el ojal difiere: ajustar pos 2 (eje) y pos 12 (Ø)."]
    S.mtext(spec, (375, 300), h=2.2, ls=1.55, bold_first=True)

    # ---------------- POS 19 PASTILLA (U) / FILM (S) ----------------
    if U:
        O = Place((600, 340), 0.4)
        S.circle(O((0, 0)), 34); S.circle(O((0, 0)), 33.8, "FINA"); S.centerlines(O((0, 0)), 34, 4)
        S.dim_dia(O((0, 0)), 34, 40, "Ø170 -0,1/-0,2")
        Os = Place((600, 275), 0.5)
        pts = [Os(p) for p in [(-85, 0), (85, 0), (85, 9.5), (84.5, 10), (-84.5, 10), (-85, 9.5)]]
        hrect(S, pts, pattern="ANSI37", scale=0.45)
        S.dim(Os((85, 0)), Os((85, 10)), 6, "10 ±0,1", orient="v", outside=True)
        sp = ["UHMW-PE PE1000 (ISO 15527), virgen, Mw ≥ 5×10⁶ g/mol.",
              "Presión admisible larga duración ≥ 12 MPa (ensayar).",
              "Alternativa: UHMW certificado para apoyos (EN 1337/ETA).",
              "Cara superior: mecanizada plana Ra ≤ 1,6. Sin lubricante.",
              "Chaflán 0,5×45° borde superior. 34 un. + 4 repuesto."]
        S.mtext(sp, (555, 262), h=2.15, ls=1.5)
        tag(S, (600, 222), 19, "PASTILLA DESLIZANTE", "UHMW-PE PE1000", "34+4", fmt_kg(m[19] / 34))
        S.text("ESCALA 1:2,5 / 1:2", (600, 212), 2.3, "TOP_CENTER")
    else:
        sp = ["POS 19 – GRASA GRAFITADA / POS 20 – GRASERAS",
              "• Grasa grafitada NLGI 2, base complejo de litio o calcio, grafito ≥ 10 %,",
              "  aditivo EP, rango −20/+150 °C, resistente al agua (o equivalente aprobado).",
              "• Superficies: cara sup. pos 1 (Ø2000) y cara inf. 4b completa + ranuras.",
              "• Espesor 0,3–0,5 mm por cara (≈ 2,5 kg por aplicación completa).",
              "• Relubricación: 4 graseras pos 20 (DIN 71412 M10×1) en canto de 4b,",
              "  ≈ 60 g c/u antes de cada operación; conductos Ø6 a ranura R850.",
              "• Grafito conductor eléctrico: aislar de equipos energizados.",
              "• Sin grasa (acero seco μ 0,5–0,8) la tornamesa NO gira: prohibido operar."]
        S.mtext(sp, (560, 322), h=2.25, ls=1.55, bold_first=True)

    # ---------------- POS 14/15/16 SELLO 1:1 ----------------
    O = Place((752, 290), 1.0)
    g = v["g"]
    hrect(S, [O((-40, g)), O((0, g)), O((0, g + 30)), O((-40, g + 30))], scale=0.8)
    S.pline([O((-40, g + 30)), O((-44, g + 34))], "FINA")
    hrect(S, [O((-40, -20)), O((15, -20)), O((15, 0)), O((-40, 0))], scale=0.8, angle=90)
    rub = [O((0, 0)), O((5, 0)), O((5, g + 30)), O((0, g + 30))]
    S.pline(rub, "VIS", closed=True); S.hatch_poly(rub, solid=True)
    bar = [O((5, g + 2.5)), O((11, g + 2.5)), O((11, g + 27.5)), O((5, g + 27.5))]
    S.pline(bar, "VIS", closed=True); S.hatch_poly(bar, scale=0.4)
    zbm = g + 15
    S.rect(*O((11, zbm - 6.5)), *O((16, zbm + 6.5)))
    S.line(O((-16, zbm - 4)), O((11, zbm - 4)), "OCU"); S.line(O((-16, zbm + 4)), O((11, zbm + 4)), "OCU")
    S.line(O((-20, zbm)), O((22, zbm)), "EJE")
    S.dim(O((0, 0)), O((5, 0)), -6, "5", outside=True)
    S.dim(O((-40, g)), O((-40, g + 30)), -5, "30", orient="v")
    S.leader(O((3, 6)), (O((0, 0))[0] + 25, O((0, -10))[1]), "pos 14 NBR 70 ShA", h=2.2)
    S.leader(O((8, g + 24)), (O((0, 0))[0] + 25, O((0, g + 45))[1]), "pos 15 fleje 25×6", h=2.2)
    S.leader(O((15, zbm + 5)), (O((0, 0))[0] + 25, O((0, zbm + 22))[1]), "pos 16 M8×20 A2-70", h=2.2)
    S.text("Plancha inferior 4b", O((-40, g + 36)), 2.1, "BOTTOM_LEFT")
    S.text("Base pos 1", O((-40, -24)), 2.1, "TOP_LEFT")
    S.text("Faldón apoyado sobre pos 1, pretensado 1–2 mm.", O((-40, -32)), 2.1, "TOP_LEFT")
    S.text("Unión del faldón: vulcanizado en frío, traslapo 50.", O((-40, -37)), 2.1, "TOP_LEFT")
    S.text("Fleje rolado Ø2022 en 2 tramos con cubrejunta.", O((-40, -42)), 2.1, "TOP_LEFT")
    S.text("36× M8 radial prof. 16 en canto de 4b (0°+10°k).", O((-40, -47)), 2.1, "TOP_LEFT")
    S.view_title((765, 212), "DETALLE SELLO PERIMETRAL (pos 14/15/16)", "ESCALA 1:1 (parcial)")

    # ---------------- nota de piezas comerciales ----------------
    com = ["PIEZAS COMERCIALES Y TERMINACIONES",
           "• Pos 8: ISO 4762 M20×45 10.9, zincado laminar, con arandela Nord-Lock NL20.",
           "• Clips R Ø8 zincados con cadena de retención para pasadores pos 12.",
           "• Pos 16: ISO 4017 M8×20 A2-70 + arandela ISO 7089 A2.",
           "• Pos 17: prisionero ISO 4026 M30×25 8.8 zincado, ras con cara superior 4a.",
           "• Pos 22: guía 40×40×850 S355J2 embutida 10 en ranura 40 H8 de pos 1; filete 8 ambos lados (W5).",
           "• Pos 13: resorte compresión Ø50×100, k ≈ 5 N/mm, precarga ≈ 150 N; tapa M10 y manilla M12.",
           "• Pos 18: cáncamo giratorio M30, WLL ≥ 2,5 t (tipo RUD VRS o equiv.), suelto.",
           "• Templado y revenido (QT): certificar dureza y ensayo Charpy KV ≥ 27 J a -20 °C.",
           "• Pasadores 5, 11, 12: MT 100 % después del mecanizado; zincado laminar",
           "  o fosfatado + aceite en zonas sin ajuste."]
    S.mtext(com, (26, 170), h=2.25, ls=1.55, bold_first=True)
    return S, v


if __name__ == "__main__":
    import sys, pymupdf
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet4(k)
        S.save(f"out/{v['code']}-04.dxf", f"out/{v['code']}-04.pdf")
        pymupdf.open(f"out/{v['code']}-04.pdf")[0].get_pixmap(dpi=75).save(f"out/{v['code']}-04.png")
        print("ok", k)
