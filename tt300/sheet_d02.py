"""Lámina D-02: accionamiento – cálculo de la fuerza del actuador y verificaciones a 300 tf."""
import math
import params as P, draw, calc as K
from common import Place


def f(x, d=0):
    return K.nf(x, d)


def sheet_d02(kind="S"):
    v = P.variant(kind); v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 2, 3, "DISEÑO – ACCIONAMIENTO Y VERIFICACIONES", "S/E")
    hs = 2.7
    # ======================= COLUMNA 1: HIPÓTESIS =======================
    x1 = 28
    hyp = [
        "1. HIPÓTESIS DE CÁLCULO",
        f"H1  Carga WLL = 300 tf = {f(K.W, 0)} kN; CG con excentricidad e ≤ 150 mm respecto del pivote.",
        f"    Peso disco cajón + buje = 1 922 kg = {f(K.W_DISC, 2)} kN.  N = W + Wd = {f(K.N_F, 1)} kN (giro cuasi-",
        "    estático; φd = 1,10 se aplica solo a resistencias, no a la fricción).",
        "H2  Interfaz de giro: contacto plano anular acero/acero, cara sup. pos 1 / cara inf. 4b,",
        "    R = 1 000 mm, r = 95 mm, con grasa grafitada pos 19 en ambas caras + ranuras (det. L, F-03).",
        "H3  Coeficiente de fricción ESTÁTICO (despegue) de diseño μ = 0,20 = límite superior del",
        "    rango acero/acero engrasado 0,10–0,20 (ref. [1], [2]). Nominal 0,15; contaminado 0,25;",
        "    acero seco 0,50 (rango real 0,5–0,8) – caso prohibido.",
        "H4  Radio efectivo de fricción:  presión uniforme  r_u = 2/3·(R³ − r³)/(R² − r²) = 0,672 m.",
        "    Diseño r_ef = 0,80 m (cubre concentración de presión al borde por e = 150 y flexión del",
        "    disco). Cota física máxima r = 0,94 m (toda la carga en el anillo de barras).",
        "H5  Empuje en PAR: 2 cilindros simultáneos (válvula de bloqueo), cada uno sobre una barra",
        f"    Ø70 en R940. Fuerza paralela a Y; barra entre −5° y +5° → brazo mínimo a = 940·cos5° = {f(K.ARM * 1000, 1)} mm.",
        f"H6  Pérdidas: fricción carro/guía μg = 0,15 (acero engrasado) por el par de excentricidad",
        f"    Δ = {f(K.DELTA * 1000, 1)} mm entre eje del cilindro (x = 1 085) y la barra (x = 936,4); reacciones de",
        f"    guía separadas Lg = {f(K.LG * 1000, 0)} mm. Rendimiento de sellos del cilindro ηc = 0,95.",
        f"H7  Buje del pivote: H = 5 % W, μ = 0,20, r = 75 mm → T_piv = {f(K.T_PIV, 2)} kN·m.",
        f"H8  Cilindro 50 t doble efecto, Ø90 → A = {f(K.A_CYL, 0)} mm²; F = 445 kN a 700 bar (alivio).",
        "H9  Elementos de la cadena de empuje se verifican a la FUERZA DE CALADO 445 kN (alivio",
        "    700 bar), no a la fuerza de diseño: si el disco se traba, nada falla antes que la válvula.",
        "H10 Rótulas GE70 en ambos ojales: sin momento en el vástago. Velocidad de giro ≤ 1 °/s.",
    ]
    y = S.mtext(hyp, (x1, 578), h=hs, ls=1.555, bold_first=True)

    # ---------- esquema de fuerzas ----------
    S.text("2. ESQUEMA DE FUERZAS – PLANTA (S/E)", (x1, y - 4), 2.6, "TOP_LEFT", bold=True)
    sc = 1 / 10.5
    T = Place((152, y - 135), sc)
    c = T((0, 0))
    S.rect(*T((-1200, -1000)), *T((1200, 1000)), "FINA")
    S.circle(c, 1000 * sc)
    S.circle(c, P.R_BAR * sc, "EJE")
    for k in range(P.N_BAR):
        a = math.radians(P.BAR_ANG0 + 10 * k)
        S.circle(T((P.R_BAR * math.cos(a), P.R_BAR * math.sin(a))), 35 * sc)
    S.centerlines(c, 1000 * sc, 3)
    S.circle(c, 75 * sc)
    xb, yb, ye = (P.R_BAR * math.cos(math.radians(-5)), P.R_BAR * math.sin(math.radians(-5)), 0)
    for sx in (1, -1):
        xb_, yb_ = sx * xb, sx * yb
        ybr = -sx * P.Y_BRK
        xc = sx * P.X_CYL
        # cilindro (cuerpo + vástago)
        ya, yb2 = sorted((ybr + sx * 70, ybr + sx * 370))
        S.rect(*T((xc - 70, ya)), *T((xc + 70, yb2)))
        S.rect(*T((xc - 45, min(ybr + sx * 370, yb_ - sx * 250))), *T((xc + 45, max(ybr + sx * 370, yb_ - sx * 250))), "FINA")
        S.line(T((xc, ybr)), T((xc, yb_ - sx * 250)), "EJE")
        S.circle(T((xc, ybr)), 35 * sc * 1.5)
        S.rect(*T((xc - 80, ybr - 140)), *T((xc + 80, ybr + 140)), "FINA")
        # carro
        S.rect(*T((P.SHOE_X0 * sx, yb_ - sx * 280)), *T((P.SHOE_X1 * sx, yb_ + sx * 20)))
        # fuerza sobre la barra
        tip = T((xb_ + sx * 0, yb_))
        tail = T((xb_, yb_ - sx * 420))
        S.line(tail, tip, "VIS")
        S.arrow(tip, math.atan2(tip[1] - tail[1], tip[0] - tail[0]), size=3.4, w=1.3)
        S.text("F_barra", (tail[0] - sx * 2, tail[1] + sx * 2), 2.3, "MIDDLE_RIGHT" if sx > 0 else "MIDDLE_LEFT", bold=True)
        S.text("F_cil", (T((xc, 0))[0] + sx * 6, T((0, -sx * 400))[1]), 2.2, "MIDDLE_LEFT" if sx > 0 else "MIDDLE_RIGHT")
    # brazo a
    S.dim(c, T((xb, yb)), -12, "a = 936,4", orient="h", h=2.1)
    S.dim(T((xb, -650)), T((P.X_CYL, -650)), -4, "Δ=148,6", orient="h", h=1.9)
    # momento resistente (horario) y giro (antihorario)
    S.arc(c, 30, 200, 330, "VIS")
    a1 = math.radians(200)
    S.arrow((c[0] + 30 * math.cos(a1), c[1] + 30 * math.sin(a1)), a1 - math.pi / 2, size=3, w=1.1)
    S.text("T_f = μ·N·r_ef (resistente)", (c[0], c[1] - 35), 2.2, "TOP_CENTER")
    S.arc(c, 22, 30, 150, "FINA")
    a2 = math.radians(150)
    S.arrow((c[0] + 22 * math.cos(a2), c[1] + 22 * math.sin(a2)), a2 + math.pi / 2, size=2.6, w=1.0)
    S.text("giro", (c[0], c[1] + 24), 2.1, "BOTTOM_CENTER")
    yl = y - 135 - 105
    S.mtext(["Par motor = 2 · F_barra · a   (las dos fuerzas forman un par puro: resultante horizontal nula",
             "sobre el pivote). El par de excentricidad F·Δ en cada carro lo toma la guía pos 22 con dos",
             "reacciones R = F·Δ/Lg que generan la fricción adicional 2·μg·R (factor K)."], (x1, yl), h=2.6, ls=1.5)

    # ======================= COLUMNA 2: DESARROLLO =======================
    x2 = 296
    d = K.case(0.20, 0.80)
    Tf = 0.20 * K.N_F * 0.80
    dev = [
        "3. DESARROLLO – FUERZA REQUERIDA EN EL ACTUADOR",
        "(1)  Par de fricción en la interfaz:          T_f = μ · N · r_ef",
        "(2)  Par total resistente:                     T = T_f + T_piv",
        "(3)  Fuerza en cada barra (par de 2):         F_barra = T / (2 · a)",
        "(4)  Factor de pérdidas:                       K = (1 + 2·μg·Δ/Lg) / ηc",
        "(5)  Fuerza en cada cilindro:                 F_cil = K · F_barra",
        "(6)  Presión requerida:                        p = F_cil / A",
        "(7)  Factor de seguridad del accionamiento:  FS = 445 kN / F_cil",
        "(8)  Fricción máxima vencible:                μ_max = (p_max·A·2a/K − T_piv) / (N · r_ef)",
        "",
        "CASO DE DISEÑO (μ = 0,20; r_ef = 0,80 m):",
        f"  T_f = 0,20 × {f(K.N_F, 1)} × 0,80 = {f(Tf, 1)} kN·m",
        f"  T = {f(Tf, 1)} + {f(K.T_PIV, 1)} = {f(d['T'], 1)} kN·m",
        f"  F_barra = {f(d['T'], 1)} / (2 × 0,9364) = {f(d['Fb'], 1)} kN",
        f"  K = (1 + 2 × 0,15 × 0,1486 / 0,250) / 0,95 = {f(K.K_LOSS, 3)}",
        f"  F_cil = {f(K.K_LOSS, 3)} × {f(d['Fb'], 1)} = {f(d['Fc'], 1)} kN  (= {f(d['Fc'] / K.G, 1)} tf)",
        f"  p = {f(d['Fc'] * 1e3, 0)} N / {f(K.A_CYL, 0)} mm² = {f(d['Fc'] * 1e3 / K.A_CYL, 1)} MPa = {f(d['p'], 0)} bar",
        f"  FS = 445 / {f(d['Fc'], 1)} = {f(d['FS'], 2)}   → ACTUADOR SUFICIENTE CON MARGEN",
    ]
    y2 = S.mtext(dev, (x2, 578), h=hs, ls=1.55, bold_first=True)
    rows = []
    for n, mu, r in K.CASES:
        cc = K.case(mu, r)
        st = "NO GIRA" if cc["FS"] < 1 else ("GIRA" if cc["FS"] >= 1.25 else "GIRA (límite)")
        rows.append([n.split(":")[0].replace(" (acero seco) – PROHIBIDO", " (PROHIBIDO)"), f(mu, 2), f(r, 3), f(cc["T"], 0), f(cc["Fb"], 0), f(cc["Fc"], 0),
                     f(cc["p"], 0), f(cc["FS"], 2), st])
    y2 = S.table(x2, y2 - 3, [("CASO", 56, "L"), ("μ", 12, "C"), ("r_ef m", 16, "C"), ("T kN·m", 18, "R"), ("F_barra kN", 22, "R"),
                              ("F_cil kN", 19, "R"), ("p bar", 16, "R"), ("FS", 14, "R"), ("RESULTADO", 30, "C")], rows, rh=6.5, h=2.5)
    S.text("Caso 'Sin lubricación': exige 1 039 bar > 700 bar de alivio → la tornamesa no gira (sin daño: ver H9).", (x2, y2 - 3), 2.5, "TOP_LEFT")
    rows2 = []
    for r in (K.R_UNIF, 0.80, 0.94):
        rows2.append([f(r, 3), "uniforme" if r < 0.7 else ("DISEÑO" if r < 0.9 else "cota máxima"), f(K.mu_max(r, 700), 3), f(K.mu_max(r, 600), 3)])
    y2 = S.table(x2, y2 - 8, [("r_ef (m)", 24, "C"), ("hipótesis", 30, "C"), ("μ_max a 700 bar", 40, "C"), ("μ_max a 600 bar", 40, "C")], rows2, rh=6.2, h=2.5)
    S.text("Ec. (8): fricción que el accionamiento aún vence.", (x2 + 140, y2 + 17), 2.5, "TOP_LEFT")
    S.text("Margen sobre μ diseño 0,20: ×1,41 (r 0,80).", (x2 + 140, y2 + 11), 2.5, "TOP_LEFT")
    op = [
        "4. AJUSTES HIDRÁULICOS Y CRITERIO DE OPERACIÓN",
        "• Válvula de alivio: 700 bar (F = 445 kN/cil.). Bomba ≥ 700 bar, manómetro glicerina 0–1 000 bar clase 1,0.",
        f"• Presión esperada de giro (nominal, μ 0,15): ≈ {f(K.case(0.15, K.R_UNIF)['p'], 0)} bar.  Despegue de diseño ≤ {f(d['p'], 0)} bar.",
        "• ALARMA / DETENCIÓN: p > 600 bar (μ equivalente > 0,24 con r 0,80): detener, retraer, relubricar",
        "  por las 4 graseras pos 20, inspeccionar materiales extraños bajo el disco y reintentar.",
        "• PROHIBIDO aumentar el alivio sobre 700 bar ni operar con un solo cilindro.",
        "• ENSAYO DE ACEPTACIÓN a 1,0 WLL: registrar p de despegue y μ_real con (8) usando p medida:",
        f"  μ_real = (p·A·2a/K − T_piv)/(N·0,80). Aceptación: μ_real ≤ 0,20 (p_despegue ≤ {f(d['p'], 0)} bar).",
        "• Ciclo: carrera 200 = 36 libre + 164 útil → 10° por ciclo; 36 ciclos por vuelta completa.",
        "",
        "5. GRASA GRAFITADA POS 19 (ESPECIFICACIÓN)",
        "• NLGI 2, base complejo de litio o calcio, grafito ≥ 10 % en peso, aditivo EP (4 bolas ≥ 2 500 N),",
        "  rango −20/+150 °C, resistente al lavado por agua. Equivalente aprobado por el mandante.",
        "• Aplicar 0,3–0,5 mm por cara sobre pos 1 (Ø2000) y 4b, llenando ranuras (≈ 2,5 kg por aplicación).",
        "• Relubricar ≈ 60 g por grasera (4 × pos 20) antes de cada operación y cada 90° de giro con carga.",
        "• No usar grasas sin sólidos ni aceites: a 1,0–1,7 MPa la película fluida se expulsa; el grafito",
        "  mantiene la capa límite (μ 0,10–0,20). El grafito es conductor: aislar equipos energizados.",
        "",
        "6. FUENTES DE COEFICIENTES DE FRICCIÓN",
        "[1] Engineering ToolBox, 'Friction and Friction Coefficients': acero/acero seco μs 0,5–0,8;",
        "    acero/acero engrasado μs 0,16.",
        "[2] Guía de deslizamiento de cargas pesadas (rigging/skidding): acero/acero seco 0,40–0,60;",
        "    acero/acero engrasado 0,10–0,20.",
        "[3] AISC 360-22 (ASD); ASME BTH-1-2020; AWS D1.1/D1.1M:2020.",
    ]
    S.mtext(op, (x2, y2 - 8), h=hs, ls=1.55, bold_first=True)
    # títulos en negrita intermedios
    # ======================= COLUMNA 3: GRÁFICO + VERIFICACIONES =======================
    x3 = 586
    S.text("7. FUERZA POR CILINDRO vs μ", (x3, 578), 2.6, "TOP_LEFT", bold=True)
    gx0, gy0, gw, gh = x3 + 14, 452, 225, 112
    mu_max_ax, F_ax = 0.40, 700.0
    X = lambda m: gx0 + m / mu_max_ax * gw
    Y = lambda F: gy0 + F / F_ax * gh
    S.rect(gx0, gy0, gx0 + gw, gy0 + gh, "VIS")
    for i in range(0, 9):
        m = i * 0.05
        S.line((X(m), gy0), (X(m), gy0 + gh), "FINA" if 0 < i < 8 else "VIS")
        S.text(f(m, 2), (X(m), gy0 - 1.5), 2.0, "TOP_CENTER")
    for Fv in range(0, 701, 100):
        S.line((gx0, Y(Fv)), (gx0 + gw, Y(Fv)), "FINA")
        S.text(str(Fv), (gx0 - 1.5, Y(Fv)), 2.0, "MIDDLE_RIGHT")
    S.text("μ (estático)", (gx0 + gw / 2, gy0 - 6), 2.2, "TOP_CENTER")
    S.text("F_cil (kN)", (gx0 - 12, gy0 + gh + 2), 2.2, "BOTTOM_LEFT")
    for r, lay, lab in ((K.R_UNIF, "VIS", "r 0,672"), (0.80, "VIS", "r 0,80 (diseño)"), (0.94, "OCU", "r 0,94")):
        pts = []
        for i in range(0, 41):
            m = i * 0.01
            Fc = K.case(m, r)["Fc"]
            if Fc <= F_ax:
                pts.append((X(m), Y(Fc)))
        S.pline(pts, lay)
        S.text(lab, (pts[-1][0] - 1, pts[-1][1] - 1), 2.0, "TOP_RIGHT")
    for Fv, lab in ((445, "445 kN = 700 bar (alivio)"), (381.4, "381 kN = 600 bar (alarma)")):
        S.line((gx0, Y(Fv)), (gx0 + gw, Y(Fv)), "VIS" if Fv > 400 else "OCU")
        S.text(lab, (gx0 + 2, Y(Fv) + 1), 2.0, "BOTTOM_LEFT", bold=Fv > 400)
    S.line((X(0.10), gy0), (X(0.10), gy0 + gh), "EJE")
    S.line((X(0.20), gy0), (X(0.20), gy0 + gh), "EJE")
    S.text("engrasado 0,10–0,20", (X(0.15), gy0 + gh - 2), 2.0, "TOP_CENTER")
    S.line((X(0.50 if 0.5 < mu_max_ax else 0.39), gy0), (X(0.39), gy0), "VIS")
    pd = (X(0.20), Y(d["Fc"]))
    S.circle(pd, 1.4); S.hatch_poly([(pd[0] + 1.4 * math.cos(t / 10 * 6.283), pd[1] + 1.4 * math.sin(t / 10 * 6.283)) for t in range(10)], solid=True)
    S.leader(pd, (X(0.24), Y(200)), f"Diseño: {f(d['Fc'], 0)} kN – {f(d['p'], 0)} bar", h=2.1)
    S.text("Acero seco (0,5–0,8) fuera de escala: 660 kN > 445 kN", (gx0 + gw - 1, gy0 + 2), 2.0, "BOTTOM_RIGHT")

    S.text("8. VERIFICACIÓN DE ELEMENTOS – 300 tf (cadena de empuje a F calado = 445 kN)", (x3, 438), 2.4, "TOP_LEFT", bold=True)
    vr, ex = K.verifs()
    rows3 = []
    for e, dem, cap, fu, ref in vr:
        st = "OK" if fu <= 0.90 else ("MONIT." if fu <= 1.0 else "NO")
        rows3.append([e, dem.replace(".", ","), cap, f(fu, 2), st, ref])
    y3 = S.table(x3, 432, [("ELEMENTO / SOLICITACIÓN", 88, "L"), ("DEMANDA", 34, "C"), ("CAPACIDAD", 25, "C"), ("FU", 11, "C"), ("", 12, "C"), ("REFERENCIA", 73, "L")],
                 rows3, rh=6.4, h=2.3)
    fus = [r[3] for r in vr]
    S.mtext([f"FU máximo = {f(max(fus), 2)} (trinquete pos 11) ≤ 0,90 → ACEPTABLE.  Aplastamiento AISC J7: Rn/Ω = 1,8·Fy·Apb/2,0.",
             "Placas 4a/4b y almas 4d: solicitación de servicio con φd = 1,10 (carga sobre parrilla, H1).",
             f"Barra 4f: M rotulada = F/4·(L − c/2) = {f(ex['Mss'], 2)} kN·m;  soldadura con M empotrada = F(3L² − c²)/(24L) = {f(ex['Mfe'], 2)} kN·m.",
             f"Guía pos 22: R = F·Δ/Lg = {f(ex['Rg'], 0)} kN tomada por aplastamiento en ranura 40 H8 × 10 (det. M, F-03).",
             f"Accidental 1 cilindro (prohibido por válvula): buje {f(ex['pb1'], 1)} MPa / 30 MPa (FU 0,99) – sin margen, no admisible.",
             "Presión bajo placa base: 0,62 MPa media / 0,90 MPa máx. (e = 150) – verificar losa/mats por terceros."],
            (x3, y3 - 3), h=2.3, ls=1.5)
    # resumen destacado
    bx0, by1 = 20 + 8, 222
    S.rect(bx0, by1 - 40, bx0 + 262, by1, "MARCO")
    S.mtext(["RESULTADO – FUERZA DEL ACTUADOR",
             f"Fuerza de diseño por cilindro:  F_cil = {f(d['Fc'], 0)} kN ({f(d['Fc'] / K.G, 1)} tf)  →  p = {f(d['p'], 0)} bar",
             f"Fuerza disponible por cilindro:  445 kN a 700 bar   →   FS = {f(d['FS'], 2)}",
             f"Fuerza en cada barra: {f(d['Fb'], 0)} kN; par total de giro: {f(d['T'], 0)} kN·m (2 cilindros en par)",
             f"Fricción máxima vencible: μ = {f(K.mu_max(0.80), 2)} (r 0,80) / {f(K.mu_max(0.94), 2)} (cota física r 0,94)",
             "Gira con certeza en todo el rango acero/acero ENGRASADO (0,10–0,20), incluida",
             "la hipótesis de carga concentrada al borde. NO gira en seco: lubricación OBLIGATORIA.",
             "Elementos verificados a la fuerza máxima del cilindro: FU ≤ 0,86."],
            (bx0 + 3, by1 - 3), h=2.7, ls=1.6, bold_first=True)
    return S, v


if __name__ == "__main__":
    S, v = sheet_d02("S")
    S.save("out/TT300-B-D-02.dxf", "out/TT300-B-D-02.pdf")
    import pymupdf
    pymupdf.open("out/TT300-B-D-02.pdf")[0].get_pixmap(dpi=90).save("out/TT300-B-D-02.png")
