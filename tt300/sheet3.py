"""Lámina 3: fabricación placa base (conj. soldado 1+2+3) y disco (4) [+ pistas inox 20/21]."""
import math
import params as P, draw
from common import Place, fmt_kg

def nf(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def sheet3(kind):
    v = P.variant(kind); v["proj"] = P.PROJ
    U = kind == "U"
    S = draw.Sheet()
    S.frame(v, 3, 4, "FABRICACIÓN – PLACA BASE (1+2+3) Y DISCO (4)", "INDICADA")
    hc = v["H_cheek"]; zax = v["z_axis"] - P.TB

    # =================== PLACA BASE – PLANTA 1:10 ===================
    T = Place((158, 440), 0.1)
    c = T((0, 0))
    S.rect(*T((-1200, -1000)), *T((1200, 1000)))
    for sx_ in (1, -1):
        S.rect(*T((sx_ * P.X_CYL - 20, -P.RAIL_L / 2)), *T((sx_ * P.X_CYL + 20, P.RAIL_L / 2)))
        S.line(T((sx_ * P.X_CYL, -P.RAIL_L / 2 - 30)), T((sx_ * P.X_CYL, P.RAIL_L / 2 + 30)), "EJE")
    S.circle(c, 7.5); S.centerlines(c, 106, 0)
    S.circle(c, 100, "FANT")
    S.text("contorno disco Ø2000", T((-640, 840)), 2.0, "BOTTOM_LEFT")
    if U:
        for r, n, a0 in P.RINGS:
            S.circle(c, r * 0.1, "EJE")
        for _, _, x, y in P.pad_positions():
            S.circle(T((x, y)), P.D_POCKET / 2 * 0.1)
            S.circle(T((x, y)), 0.5)
    for sx in (1, -1):
        for sy in (1, -1):
            x0, y0 = sx * P.X_CYL, sy * P.Y_BRK
            for side in (-1, 1):
                xa = x0 + side * P.CHEEK_GAP / 2
                xb = x0 + side * (P.CHEEK_GAP / 2 + P.CHEEK_T)
                S.rect(*T((min(xa, xb), y0 - P.CHEEK_L / 2)), *T((max(xa, xb), y0 + P.CHEEK_L / 2)))
            yb0 = y0 + sy * P.CHEEK_L / 2
            yb1 = yb0 + sy * P.BACK_T
            S.rect(*T((x0 - 80, min(yb0, yb1))), *T((x0 + 80, max(yb0, yb1))))
            S.line(T((x0 - 100, y0)), T((x0 + 100, y0)), "EJE")
            # orejas
            S.rect(*T((sx * P.LUG_X - 20, sy * 850)), *T((sx * P.LUG_X + 20, sy * 1000)))
    S.dim(T((-1200, 1000)), T((1200, 1000)), 9, "2400")
    S.dim(T((-1200, -1000)), T((-1200, 1000)), -7, "2000", orient="v")
    S.dim(T((0, -1000)), T((P.X_CYL, -1000)), -6, nf(P.X_CYL)); S.dim(T((-P.X_CYL, -1000)), T((0, -1000)), -6, nf(P.X_CYL))
    S.dim(T((1200, 0)), T((1200, -P.Y_BRK)), 6, nf(P.Y_BRK), orient="v"); S.dim(T((1200, 0)), T((1200, P.Y_BRK)), 6, nf(P.Y_BRK), orient="v")
    S.dim(T((-1105, -P.RAIL_L / 2)), T((-1105, P.RAIL_L / 2)), -5, "850", orient="v")
    S.dim(T((-600, 1000)), T((600, 1000)), 3.5, "1200")
    S.dim(T((600, 850)), T((600, 1000)), -4, "150", orient="v", outside=True)
    S.leader(T((75 * 0.7071, 75 * 0.7071)), (c[0] + 20, c[1] + 40), "Ø150 H7 pasante", h=2.3)
    if U:
        S.leader(T((P.RINGS[2][0], 0)), (c[0] + 40, c[1] - 112), "34× alojam. Ø170,6 +0,1/0 prof. 5 (ver tabla y det. F)", h=2.2)
    S.balloon(T((-500, -500)), T((-1300, -650)), 1)
    S.balloon(T((P.X_CYL + 60, 760)), T((1300, 1080)), 2)
    S.balloon(T((600, 950)), T((450, 1100)), 3)
    S.balloon(T((-P.X_CYL, 200)), T((-1300, 300)), 22)
    S.leader(T((P.X_CYL, 300)), (T((0, 0))[0] + 60, T((0, 0))[1] + 75), "Guía 40×40 embutida 10 (ranura 40 H8), filete 8 – det. M F-03", h=2.1)
    S.view_title((c[0], 316), "POS 1 – PLACA BASE (CONJ. SOLDADO 1+2+3) – PLANTA", "ESCALA 1:10")

    # ----- ELEVACIÓN FRONTAL 1:10
    F = Place((158, 262), 0.1)
    S.rect(*F((-1200, 0)), *F((1200, P.TB)))
    for sx in (1, -1):
        for side in (-1, 1):
            xa = sx * P.X_CYL + side * P.CHEEK_GAP / 2
            xb = sx * P.X_CYL + side * (P.CHEEK_GAP / 2 + P.CHEEK_T)
            S.rect(*F((min(xa, xb), P.TB)), *F((max(xa, xb), P.TB + hc)))
        S.circle(F((sx * P.X_CYL, v["z_axis"])), 3.55, "OCU")
        S.rect(*F((sx * P.LUG_X - 20, P.TB)), *F((sx * P.LUG_X + 20, P.TB + P.LUG_H)))
        S.rect(*F((sx * P.X_CYL - 20, P.TB - 10)), *F((sx * P.X_CYL + 20, P.TB + P.RAIL_H)), "OCU")
    S.line(F((0, -10)), F((0, P.TB + 40)), "EJE")
    S.dim(F((1200, 0)), F((1200, P.TB)), 6, "80", orient="v")
    S.dim(F((-1200, P.TB)), F((-1200, P.TB + hc)), -14, nf(hc), orient="v")
    S.dim(F((-1200, P.TB)), F((-1200, v["z_axis"])), -6, nf(zax), orient="v")
    S.dim(F((-660, P.TB)), F((-660, P.TB + P.LUG_H)), -3, "170", orient="v")
    S.weld(F((P.X_CYL - 60, P.TB)), (F((P.X_CYL, 0))[0] + 14, F((0, -60))[1]), "cjp", "CJP", other=True, note="MEJILLAS pos 2")
    S.weld(F((-P.LUG_X - 20, P.TB)), (F((-P.LUG_X, 0))[0] - 10, F((0, -60))[1]), "fillet", "12", other=True, all_round=True, note="pos 3")
    S.view_title((158, 222), "ELEVACIÓN FRONTAL", "ESCALA 1:10")

    # ----- DETALLE F 1:1 alojamiento (U) / DETALLE F superficie (S)
    if U:
        Fp = Place((62, 140), 1.0, (0, 0))
        x0, x1 = -15, 112
        for out in ([(5, -40), (x1, -40), (x1, 0), (85.3, 0), (85.3, -5), (5, -5)], [(x0, -40), (-5, -40), (-5, -5), (x0, -5)]):
            pts = [Fp(p) for p in out]
            S.pline(pts, "VIS", closed=True)
            S.hatch_poly(pts, scale=0.8)
        pp = [Fp(p) for p in [(x0, -5), (85, -5), (85, 5), (x0, 5)]]
        S.pline(pp, "VIS", closed=True); S.hatch_poly(pp, pattern="ANSI37", scale=0.7)
        S.line(Fp((0, -48)), Fp((0, 14)), "EJE")
        S.pline([Fp((x1, -40)), Fp((x1 + 4, -20)), Fp((x1 - 3, -14)), Fp((x1, 0))], "FINA")
        S.pline([Fp((x0, -40)), Fp((x0 - 3, -25)), Fp((x0 + 3, -12)), Fp((x0, 5))], "FINA")
        S.dim(Fp((0, -40)), Fp((85.3, -40)), -8, "Ø170,6 +0,1/0")
        S.dim(Fp((0, 5)), Fp((85, 5)), 8, "Ø170 -0,1/-0,2")
        S.dim(Fp((112, -5)), Fp((112, 0)), 6, "5 ±0,05", orient="v", outside=True)
        S.dim(Fp((112, 0)), Fp((112, 5)), 18, "5", orient="v", outside=True)
        S.dim(Fp((-15, -5)), Fp((-15, 5)), -5, "10 ±0,1", orient="v", outside=True)
        S.leader(Fp((5, -25)), (Fp((0, 0))[0] + 30, Fp((0, -30))[1]), "Ø10 pasante (extracción)", h=2.2)
        S.finish(Fp((40, -5)), "Ra 3,2")
        S.leader(Fp((85, 4)), (Fp((0, 0))[0] + 95, Fp((0, 24))[1]), "Chaflán 0,5×45°", h=2.2)
        S.text("pos 19", Fp((30, 0.5)), 2.0, "BOTTOM_LEFT")
        S.text("pos 1", Fp((60, -25)), 2.0, "BOTTOM_LEFT")
        S.view_title((Fp((50, 0))[0], 82), "DETALLE F – ALOJAMIENTO DE PASTILLA", "ESCALA 1:1")
        # tabla anillos
        S.table(200, 168, [("ANILLO", 15, "C"), ("R (mm)", 16, "C"), ("N°", 10, "C"), ("ÁNG. INICIAL", 22, "C"), ("PASO", 14, "C")],
                [["1", "300", "6", "30°", "60°"], ["2", "550", "12", "15°", "30°"], ["3", "735", "16", "0°", "22,5°"]], rh=5.2, h=2.2)
        S.text("Ángulos desde eje +X, sentido antihorario (vista en planta).", (200, 141), 2.0, "TOP_LEFT")
        S.text("Tolerancia posición alojamientos: ±0,5 mm.", (200, 137), 2.0, "TOP_LEFT")
    else:
        lines = ["DETALLE F – SUPERFICIE DE CONTACTO (sin escala)",
                 "• Cara superior pos 1 dentro de Ø2000 y cara inferior pos 4: fresado/planeado",
                 "  final después del alivio de tensiones.",
                 "• Planitud ≤ 0,20 mm en Ø2000; rugosidad Ra 1,6–3,2 µm; sin rayas radiales.",
                 "• Bordes de la zona de contacto: chaflán 2×45°; agujero Ø150: chaflán 3×45°.",
                 "• Cara 4b: ranuras de lubricación y conductos de graseras según det. L (lám. F-03).",
                 "• Lubricante pos 19: grasa grafitada NLGI 2, 0,3–0,5 mm en ambas caras,",
                 "  aplicada con espátula sobre superficie limpia y seca; llenar ranuras de 4b.",
                 "• Almacenaje: caras protegidas con la misma grasa y cubiertas con film.",
                 "• NO pintar con el sistema anticorrosivo las caras de contacto."]
        S.mtext(lines, (26, 205), h=2.3, ls=1.55, bold_first=True)
        S.finish((150, 105), "Ra 1,6–3,2 (ambas caras)")

    # =================== DISCO CAJÓN – PLANTA 1:10 ===================
    import model3d as M, hlr
    D = Place((450, 440), 0.1)
    c = D((0, 0))
    S.circle(c, 100); S.centerlines(c, 106, 0)
    S.circle(c, P.R_BAR * 0.1, "EJE"); S.circle(c, P.R_M30 * 0.1, "EJE")
    for _, x, y in P.idx_positions():
        S.circle(D((x, y)), P.D_BAR / 2 * 0.1)
    for a in P.M30_ANG:
        p = D((P.R_M30 * math.cos(math.radians(a)), P.R_M30 * math.sin(math.radians(a))))
        S.circle(p, 1.5); S.arc(p, 1.25, 0, 270, "FINA")
    S.circle(c, P.HUB_D / 2 * 0.1); S.circle(c, P.D_CB / 2 * 0.1)
    for r in P.RING_R:
        S.circle(c, (r - P.RING_T / 2) * 0.1, "OCU"); S.circle(c, (r + P.RING_T / 2) * 0.1, "OCU")
        n = max(4, int(2 * math.pi * r / 250))
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            ca, sa = math.cos(a), math.sin(a)
            S.line(D(((r - 11) * ca, (r - 11) * sa)), D(((r + 11) * ca, (r + 11) * sa)), "FINA")
    for k in range(P.N_RIB):
        a = math.radians(360 / P.N_RIB * k); ca, sa = math.cos(a), math.sin(a)
        for off in (-P.RIB_T / 2, P.RIB_T / 2):
            S.line(D((150 * ca - off * sa, 150 * sa + off * ca)), D((P.RIB_R1 * ca - off * sa, P.RIB_R1 * sa + off * ca)), "OCU")
    S.circle(c, 80, "FANT")
    S.dim_dia(c, 100, 140, "Ø2000")
    S.leader(D((P.R_BAR * math.cos(math.radians(45)), P.R_BAR * math.sin(math.radians(45)))), (c[0] + 60, c[1] + 112), "36 barras 4f Ø70 s/ Ø1880, inicio 5°, paso 10°", h=2.2)
    S.leader(D((P.R_M30 * math.cos(math.radians(135)), P.R_M30 * math.sin(math.radians(135)))), (c[0] - 60, c[1] + 112), "4× M30 pasante en 4a s/ Ø1200 a 45°", h=2.2)
    S.leader(D((550 * math.cos(math.radians(20)), 550 * math.sin(math.radians(20)))), (c[0] + 60, c[1] - 112), "Almas 4d R300/R550/R735 e=25 y nervios 4e e=20 (ocultos)", h=2.2)
    S.leader(D((-150 * 0.7071, -150 * 0.7071)), (c[0] - 60, c[1] - 112), "Cubo 4c Ø300 (det. H)", h=2.2)
    S.text("Ranuras de soldadura en 4a sobre almas (trazo fino)", D((-560, -400)), 2.0, "BOTTOM_LEFT")
    S.text("0°", D((1040, 15)), 2.3, "BOTTOM_LEFT")
    S.balloon(D((-300, 500)), D((-1150, 650)), 4)
    S.view_title((c[0], 316), "POS 4 – DISCO CAJÓN (CONJ. SOLDADO 4a–4f) – PLANTA", "ESCALA 1:10")

    # ----- CORTE DISCO 1:10 (plano por barras a 0°/180°)
    dp = M.disc_parts(v)
    lab = {"4a": 41, "4b": 42, "4c": 43, "4d": 44, "4e": 45, "4f": 46}
    parts = [(lab[k], sh.rotate((0, 0, 0), (0, 0, 1), -5).val()) for k, sh in dp.items()]
    vis, hid, hat = hlr.section(parts, "front", (0, 0, 0), (0, 1, 0), tol=1.5, nocut=set())
    hat = [(4, o, h) for _, o, h in hat]
    zb = v["z_disc_bot"]
    C = Place((450, 262), 0.1, (0, zb))
    C.polys(S, vis); C.hatches(S, hat)
    S.line(C((0, zb - 10)), C((0, zb + P.TD + 10)), "EJE")
    S.dim(C((1000, zb)), C((1000, zb + P.TD)), 6, "160", orient="v")
    S.detail_circle(C((0, zb + 80)), 16, "H"); S.detail_circle(C((-940, zb + 80)), 12, "J")
    S.view_title((450, 222), "CORTE DIAMETRAL DISCO (por barras a 0° y 180°)", "ESCALA 1:10")

    # ----- DETALLE H 1:2 (cubo)
    winH = (-230, zb - 5, 230, zb + P.TD + 5)
    H = Place((385, 112), 0.5, (0, zb))
    H.polys(S, hlr.clip_polys(vis, winH)); H.hatches(S, hlr.clip_hatch(hat, winH))
    S.line(H((0, zb - 10)), H((0, zb + P.TD + 10)), "EJE")
    zt_ = zb + P.TD
    S.dim(H((-95, zb)), H((95, zb)), -6, "Ø190 H7")
    S.dim(H((-80, zb + P.L_BUJE)), H((80, zb + P.L_BUJE)), 3, "Ø160")
    S.dim(H((-130, zt_)), H((130, zt_)), 6, "Ø260 H11")
    S.dim(H((-150, zt_)), H((150, zt_)), 14, "Ø300 (cubo 4c)")
    S.dim(H((230, zb)), H((230, zb + P.L_BUJE)), 6, "100 +0,1/0", orient="v")
    S.dim(H((230, zt_ - P.H_CB)), H((230, zt_)), 6, "25", orient="v")
    S.dim(H((-230, zb)), H((-230, zb + P.TP_BOT)), -6, "30", orient="v")
    S.dim(H((-230, zt_ - P.TP_TOP)), H((-230, zt_)), -6, "30", orient="v")
    S.dim(H((-230, zb)), H((-230, zt_)), -16, "160", orient="v")
    S.weld(H((150, zt_)), H((175, zt_ + 40)), "bevel", "CJP", note="4c-4a/4b")
    S.finish(H((-60, zb + 40)), "Ra 1,6")
    S.view_title((385, 66), "DETALLE H – CUBO CENTRAL", "ESCALA 1:2")

    # ----- DETALLE J 1:2 (barra de empuje)
    winJ = (850, zb - 5, 1012, zb + P.TD + 5)
    J = Place((572, 112), 0.5, (931, zb))
    J.polys(S, hlr.clip_polys(vis, winJ)); J.hatches(S, hlr.clip_hatch(hat, winJ))
    S.line(J((940, zb - 10)), J((940, zb + P.TD + 10)), "EJE")
    S.dim(J((905, zt_)), J((975, zt_)), 6, "Ø70")
    S.dim(J((940, zb)), J((1000, zb)), -8, "60")
    S.dim(J((1000, zb + P.TP_BOT)), J((1000, zt_ - P.TP_TOP)), 6, "100 libre", orient="v")
    S.weld(J((975, zt_)), J((1015, zt_ + 40)), "bevel", "15", note="a ras")
    S.weld(J((975, zb)), J((1015, zb - 40)), "bevel", "15", note="mec.")
    S.text("Agujero Ø71 en 4a y 4b, chaflán 10×45°", J((860, zb - 20)), 2.1, "TOP_LEFT")
    S.view_title((585, 66), "DETALLE J – BARRA DE EMPUJE 4f", "ESCALA 1:2")

    # =================== PISTAS INOX (U) / TOLERANCIAS ===================
    x0 = 600
    if U:
        R = Place((660, 535), 0.025)
        for k, (din, dout) in enumerate((P.INOX_A, P.INOX_B)):
            cc = (650 + k * 75, 535)
            S.circle(cc, dout / 2 * 0.03); S.circle(cc, din / 2 * 0.03); S.centerlines(cc, dout / 2 * 0.03, 2)
            S.dim_dia(cc, dout / 2 * 0.03, 50, f"Ø{dout:.0f}", ext=5)
            S.dim_dia(cc, din / 2 * 0.03, -60, f"Ø{din:.0f}", ext=6)
            S.text(f"POS {20 + k} – e = 3", (cc[0], cc[1] - dout / 2 * 0.03 - 7), 2.6, "TOP_CENTER", bold=True)
        S.text("ESCALA 1:33 (aprox.)", (700, 495), 2.2, "TOP_CENTER")
        lines = ["PISTAS INOX POS 20 / 21",
                 "• AISI 316L (1.4404), e = 3 mm, cada anillo de una sola pieza (sin juntas).",
                 "• Acabado espejo: Ra ≤ 0,1 µm, Ry5i ≤ 1 µm (EN 1337-2), dureza 150–220 HV.",
                 "• Mecanizar cara inferior 4b en zonas de pistas (planitud ≤ 0,20) antes de soldar.",
                 "• Fijar con filete continuo 3 mm ER309L en bordes interior y exterior, soldadura",
                 "  por tramos alternos de 150 mm para limitar distorsión. Contacto pleno (sin bolsas).",
                 "• Verificar planitud conjunto pista ≤ 0,30 mm en Ø1680. Proteger con film adhesivo",
                 "  hasta el montaje. No pintar ni golpear."]
        y = S.mtext(lines, (x0, 482), h=2.25, ls=1.55, bold_first=True)
    else:
        y = 560
    tol = ["TOLERANCIAS GEOMÉTRICAS Y MECANIZADO",
           "• Cara sup. pos 1 (zona Ø2000): planitud 0,20; Ra 3,2" + (" (fondo alojamientos)." if U else " / 1,6–3,2 contacto."),
           "• Cara inf. 4b: planitud 0,20; paralelismo con cara sup. 4a: 0,30 (mecanizar ambas tras relevar).",
           "• Ø150 H7 (pos 1) y Ø190 H7 (pos 4): perpendicularidad 0,05 respecto de la cara de giro.",
           "• Barras 4f: posición ±0,5 (PCD 1880, paso 10° ±0,05°); verticalidad 0,3 en 160.",
           "• Ménsulas pos 2: agujero Ø71 H9 mecanizado en línea después de soldar y relevar;",
           "  coaxialidad entre mejillas 0,10; altura del eje ±0,5.",
           "• Tolerancias generales ISO 2768-mK. Aristas vivas: chaflán 1×45°.",
           "",
           "SECUENCIA DE FABRICACIÓN POS 1",
           "1. Corte térmico con 5 mm de sobremetal por cara; UT de plancha (A578 nivel B).",
           "2. Soldar pos 2 (CJP mejillas + filetes respaldo) y pos 3 (filete 12 todo alrededor);",
           "   precalentar ≥ 110 °C, control de interpase ≤ 250 °C.",
           "3. Alivio de tensiones 590–620 °C (1 h/25 mm, mín. 2 h), enfriamiento en horno.",
           "4. Mecanizado final: cara superior, Ø150 H7" + (", 34 alojamientos" if U else "") + ", agujeros Ø71 H9.",
           "5. Ensayos: UT CJP 100 %, MT filetes 100 %, control dimensional con protocolo.",
           "",
           "SECUENCIA DE FABRICACIÓN POS 4 (DISCO CAJÓN)",
           "1. 4b sobre mesa plana; soldar cubo 4c (CJP), almas 4d y nervios 4e (filete 8 a ambos lados).",
           "2. Insertar 36 barras 4f en 4b; presentar 4a con ranuras 22×80 c/250 sobre almas y nervios.",
           "3. Soldar ranuras (relleno completo), cubo 4c–4a (CJP) y barras 4f a 4a/4b (bisel 15, E = 12, ver det. J).",
           "4. Drenaje/venteo: 2× Ø20 en 4b por celda; tapar con tapón roscado tras pintura interior.",
           "5. Alivio de tensiones 590–620 °C; mecanizar cara 4b (contacto), cara 4a, cubo (det. H).",
           "6. " + ("Soldar pistas 20/21 en 4b y pulir." if U else "Ranuras y conductos de lubricación en 4b (det. L, lám. F-03)."),
           "   Control: barras ±0,5; planitud 4b ≤ 0,20; UT CJP 100 %, MT 100 %."]
    yy = S.mtext(tol, (x0, y - 8), h=2.2, ls=1.5, bold_first=True)
    dp = M.disc_parts(v)
    mk = {k: dp[k].val().Volume() * 7.85e-6 for k in dp}
    rows = [["4a", "Plancha sup. Ø2000×30; Ø300, 36×Ø71, 4×M30", "1", fmt_kg(mk["4a"])],
            ["4b", "Plancha inf. Ø2000×30; Ø300, 36×Ø71", "1", fmt_kg(mk["4b"])],
            ["4c", "Cubo Ø300/Ø190×160 (S355J2+N, forja)", "1", fmt_kg(mk["4c"])],
            ["4d", "Almas 25×100 roladas, eje Ø600/1100/1470", "3", fmt_kg(mk["4d"])],
            ["4e", "Nervios 20×100, L 137,5/225/160/132,5 (×12)", "48", fmt_kg(20*100*655*12*7.85e-6)],
            ["4f", "Barras Ø70×160 (S355J2 laminado)", "36", fmt_kg(mk["4f"])]]
    S.table(x0, yy - 4, [("SUB", 10, "C"), ("DESPIECE POS 4", 88, "L"), ("CANT.", 12, "C"), ("kg total", 18, "R")], rows, rh=4.8, h=2.05)
    return S, v


if __name__ == "__main__":
    import sys, pymupdf
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet3(k)
        S.save(f"out/{v['code']}-03.dxf", f"out/{v['code']}-03.pdf")
        pymupdf.open(f"out/{v['code']}-03.pdf")[0].get_pixmap(dpi=75).save(f"out/{v['code']}-03.png")
        print("ok", k)
