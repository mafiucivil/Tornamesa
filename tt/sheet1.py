"""Lámina 1: Conjunto general (planta, cortes, detalles, lista de materiales, notas)."""
import math
import cadquery as cq
import params as P, model3d as M, hlr, draw
from common import Place, bom, notes_general, fmt_kg, total_mass, bbox

PUSH = (9, 10, 11, 12, 13, 22)


def nf(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def sheet1(kind):
    v, parts = M.build(kind)
    v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 1, 4, "CONJUNTO GENERAL – CORTES Y DETALLES", "INDICADA")
    shapes = [(p, s.val()) for p, n, s, c in parts]
    U = kind == "U"
    zt = v["z_disc_top"]

    # ================= PLANTA 1:10 =================
    allc = cq.Compound.makeCompound([s for _, s in shapes])
    vis, _ = hlr.hlr(allc, "top", tol=4)
    T = Place((160, 448), 0.1)
    T.polys(S, vis)
    S.centerlines(T((0, 0)), 108, 0)
    S.circle(T((0, 0)), P.R_IDX * 0.1, "EJE")
    S.circle(T((0, 0)), 80.0, "FANT")
    S.leader(T((-566, 566)), (T((0, 0))[0] - 62, T((0, 0))[1] + 124), "ZONA DE CARGA Ø1600 MÁX.", h=2.3)
    if U:
        for _, _, x, y in P.pad_positions():
            S.circle(T((x, y)), P.D_PAD / 2 * 0.1, "OCU")
    # dims
    S.dim(T((-1200, 1000)), T((1200, 1000)), 9, "2400")
    S.dim(T((-1200, -1000)), T((-1200, 1000)), -7, "2000", orient="v")
    S.dim(T((0, -1000)), T((P.X_CYL, -1000)), -7, nf(P.X_CYL))
    S.dim(T((-P.X_CYL, -1000)), T((0, -1000)), -7, nf(P.X_CYL))
    S.dim(T((1200, 0)), T((1200, -P.Y_BRK)), 6, nf(P.Y_BRK), orient="v")
    S.dim(T((1200, 0)), T((1200, P.Y_BRK)), 6, nf(P.Y_BRK), orient="v")
    S.dim(T((-600, 1000)), T((600, 1000)), 3.5, "1200")
    S.leader(T((P.R_IDX * math.cos(math.radians(125)), P.R_IDX * math.sin(math.radians(125)))),
             (T((0, 0))[0] + 40, T((0, 0))[1] + 124), "36 barras Ø70 s/ Ø1880 (10°) – ver det. E", h=2.3)
    if U:
        S.balloon(T((550 * math.cos(math.radians(-165)), 550 * math.sin(math.radians(-165)))), T((-1290, -400)), 19)
    # flecha de giro
    c = T((0, 0))
    S.arc(c, 52, 200, 245, "VIS")
    a = math.radians(245)
    S.arrow((c[0] + 52 * math.cos(a), c[1] + 52 * math.sin(a)), a + math.pi / 2, size=4, w=1.4)
    S.text("GIRO ANTIHORARIO", (c[0] - 40, c[1] - 30), 2.3, "MIDDLE_CENTER")
    # marcas de corte
    S.line(T((-1270, 0)), T((-1220, 0)), "VIS"); S.line(T((1220, 0)), T((1270, 0)), "VIS")
    S.section_mark(T((-1270, 0)), 90, "A"); S.section_mark(T((1270, 0)), 90, "A")
    S.line(T((P.X_CYL, 1030)), T((P.X_CYL, 1080)), "VIS"); S.line(T((P.X_CYL, -1030)), T((P.X_CYL, -1080)), "VIS")
    S.section_mark(T((P.X_CYL, 1080)), 180, "B"); S.section_mark(T((P.X_CYL, -1080)), 180, "B")
    S.detail_circle(T((1000, -150)), 15, "E")
    # globos
    bl = [(1, (-1100, -930), (-1290, -1060)), (2, (P.X_CYL + 60, 760), (1290, 1060)), (3, (-600, 950), (-760, 1150)),
          (4, (-420, 300), (-1290, 300)), (7, (60, 60), (330, 350)), (9, (P.X_CYL, -560), (1290, -560)),
          (10, (-P.X_CYL, 200), (-1290, 160)), (12, (-P.X_CYL, P.Y_BRK), (-1290, 760)),
          (22, (-P.X_CYL, -300), (-1290, -200)), (17, (424, 424), (560, 560)), (15, (-707, -707), (-1290, -760))]
    for n, p, q in bl:
        S.balloon(T(p), T(q), n)
    S.view_title((T((0, 0))[0], 322), "PLANTA", "ESCALA 1:10")

    # ================= CORTE A-A 1:10 =================
    vis, hid, hat = hlr.section(shapes, "front", (0, 0, 0), (0, 1, 0), tol=4)
    A = Place((160, 252), 0.1)
    A.polys(S, vis); A.hatches(S, hat)
    S.line(A((0, -15)), A((0, zt + 160)), "EJE")
    S.dim(A((1000, 0)), A((1000, P.TB)), 6, "80", orient="v")
    S.dim(A((1000, P.TB)), A((1000, zt)), 6, nf(zt - P.TB), orient="v")
    S.dim(A((-1200, 0)), A((-1200, zt)), -6, nf(zt), orient="v")
    S.dim(A((-1200, 0)), A((-1200, v["z_axis"])), -14, nf(v["z_axis"]), orient="v")
    S.detail_circle(A((0, 100)), 18, "C")
    S.detail_circle(A((800, 120)), 18, "D")
    S.view_title((A((0, 0))[0], 232), "CORTE A-A", "ESCALA 1:10")

    # ================= CORTE B-B 1:5 =================
    vis, hid, hat = hlr.section(shapes, "right", (P.X_CYL, 0, 0), (-1, 0, 0), tol=2)
    win = (-1010, -5, 160, v["shoe_top"] + 40)
    visc = hlr.clip_polys(vis, win); hatc = hlr.clip_hatch(hat, win)
    Bp = Place((48, 110), 0.2, (-1010, 0))
    Bp.polys(S, visc); Bp.hatches(S, hatc)
    x = Bp((160, 0))[0]
    S.pline([(x, Bp((0, -5))[1]), (x, Bp((0, 120))[1]), (x + 3, Bp((0, 140))[1]), (x - 3, Bp((0, 160))[1]), (x, Bp((0, 180))[1]), (x, Bp((0, v["shoe_top"] + 40))[1])], "FINA")
    za = v["z_axis"]
    yb = -P.Y_BRK
    xbar, yi, ye = M.push_geom(v)
    S.line(Bp((-1010, za)), Bp((160, za)), "EJE")
    S.dim(Bp((yb, za)), Bp((ye, za)), 24, f"{ye - yb:.0f} (L0 {P.L0_CYL:.0f} + 36 libre)")
    S.dim(Bp((ye, za)), Bp((yi, za)), 24, nf(P.EYE_OFF))
    S.dim(Bp((yb, 0)), Bp((0, 0)), -10, nf(P.Y_BRK))
    S.dim(Bp((yi, 0)), Bp((0, 0)), -10, nf(-yi, 1))
    S.dim(Bp((160, 0)), Bp((160, za)), 6, nf(za), orient="v")
    S.dim(Bp((-1000, 0)), Bp((-1000, P.TB)), -5, "80", orient="v")
    S.dim(Bp((-1000, P.TB)), Bp((-1000, P.TB + v["H_cheek"])), -5, nf(v["H_cheek"]), orient="v")
    S.leader(Bp((40, za + 10)), (Bp((175, 0))[0], Bp((0, za + 55))[1]), "EMPUJE → (carrera 200 = 10°)", h=2.3)
    for n, p, q in [(2, (-940, 120), (-960, 330)), (9, (-600, za + 60), (-600, za + 170)), (12, (yb, za), (-800, za + 170)),
                    (10, (-250, v["shoe_top"] - 20), (-330, za + 170)), (11, (yi - 40, za + 30), (-120, za + 170)),
                    (22, (-300, P.TB + 15), (-350, -40)), (4, (60, zt - 15), (110, za + 170)), (1, (-800, 40), (-800, -40)),
                    (14, (-150, P.TB + 10), (-150, -40))]:
        S.balloon(Bp(p), Bp(q), n)
    S.view_title((Bp((-430, 0))[0], 82), f"CORTE B-B (eje cilindro y carro, x = +{P.X_CYL:.0f})", "ESCALA 1:5")

    # ================= DETALLES 1:2 =================
    nopush = [(p, s) for p, s in shapes if p not in PUSH + (2, 3)]
    vis, hid, hat = hlr.section(nopush, "front", (0, 0, 0), (0, 1, 0), tol=1)
    # --- C: pivote
    winC = (-240, -5, 240, zt + 12)
    C = Place((445, 438), 0.5)
    C.polys(S, hlr.clip_polys(vis, winC)); C.hatches(S, hlr.clip_hatch(hat, winC))
    S.line(C((0, -15)), C((0, zt + 25)), "EJE")
    S.dim(C((-75, -5)), C((75, -5)), -6, "Ø150 H7/p6")
    S.dim(C((-95, v["z_disc_bot"])), C((95, v["z_disc_bot"])), -14 - (5 * 0.5 + v["z_disc_bot"] * 0.5) + 10 - 10 if False else -10 - v["z_disc_bot"] * 0.5 - 2.5 - 6 , "Ø190 H7/s6")
    S.dim(C((-130, zt)), C((130, zt)), 8, "Ø260")
    S.dim(C((-120, v["z_piv_top"] + P.T_TAPA)), C((120, v["z_piv_top"] + P.T_TAPA)), 3, "Ø240", txt_shift=0)
    S.dim(C((240, v["z_disc_bot"])), C((240, v["z_buje_top"])), 5, nf(P.L_BUJE), orient="v")
    S.dim(C((240, v["z_cb_floor"])), C((240, zt)), 5, "25", orient="v")
    S.dim(C((240, 0)), C((240, P.TB)), 5, "80", orient="v")
    S.dim(C((-240, v["z_piv_top"])), C((-240, v["z_piv_top"] + P.T_TAPA)), -5, "20", orient="v")
    S.dim(C((-240, v["z_cb_floor"])), C((-240, v["z_piv_top"])), -14, "3", orient="v", outside=True)
    S.leader(C((50, v["z_piv_top"] + 10)), (C((0, 0))[0] + 40, C((0, zt + 30))[1]), "6× M20 s/ PCD 100", h=2.3)
    for n, p, q in [(5, (-40, 40), (-275, 30)), (6, (-85, v["z_disc_bot"] + 40), (-275, 100)),
                    (7, (-110, v["z_piv_top"] + 10), (-215, zt + 22)), (8, (-50, v["z_piv_top"] + 5), (-145, zt + 22)),
                    (4, (180, zt - 30), (275, zt - 15)), (1, (180, 40), (275, 30))]:
        S.balloon(C(p), C(q), n)
    S.leader(C((-60, 2)), (C((0, 0))[0] - 70, C((0, -50))[1]), "Sold. sello chaflán 5×45°, esmerilar", h=2.2)
    if U:
        S.leader(C((160, P.TB + 4)), (C((0, 0))[0] + 70, C((0, -50))[1]), "Holgura g = 8 (5 pastilla + 3 inox)", h=2.2)
    else:
        S.leader(C((160, P.TB)), (C((0, 0))[0] + 70, C((0, -50))[1]), "Contacto pleno + película grafito", h=2.2)
    S.view_title((C((0, 0))[0], 384), "DETALLE C – PIVOTE", "ESCALA 1:2")

    # --- D: borde
    winD = (585, -5, 1018, zt + 12)
    Dp = Place((325, 222), 0.5, (585, 0))
    Dp.polys(S, hlr.clip_polys(vis, winD)); Dp.hatches(S, hlr.clip_hatch(hat, winD))
    zb_ = v["z_disc_bot"]
    S.dim(Dp((1000, zt)), Dp((1000, zt - P.TP_TOP)), 18, "30", orient="v")
    S.dim(Dp((1000, zt - P.TP_TOP)), Dp((1000, zb_ + P.TP_BOT)), 18, "100", orient="v")
    S.dim(Dp((1000, zb_ + P.TP_BOT)), Dp((1000, zb_)), 18, "30", orient="v")
    S.dim(Dp((1000, zt)), Dp((1000, zb_)), 28, "160", orient="v")
    S.dim(Dp((1000, P.TB)), Dp((1000, 0)), 18, "80", orient="v")
    S.text("Nervio radial 4e (cortado)", Dp((700, zb_ + P.TP_BOT + 50)), 2.2, "MIDDLE_LEFT")
    S.dim(Dp((585, zt)), Dp((1000, zt)), 6, "R1000 (a eje)")
    if U:
        S.dim(Dp((650, P.TB + 5)), Dp((820, P.TB + 5)), 22, "Ø170")
        S.dim(Dp((585, P.TB - 5)), Dp((585, P.TB)), -5, "5", orient="v", outside=True)
        S.dim(Dp((630, P.TB)), Dp((630, P.TB + 5)), -5, "5", orient="v", outside=True)
        S.dim(Dp((840, v["z_disc_bot"] - 3)), Dp((840, v["z_disc_bot"])), 3, "3", orient="v", outside=True)
        S.dim(Dp((0, P.TB)), Dp((735, P.TB)), 0, "", orient="h") if False else None
        for n, p, q in [(19, (700, P.TB), (690, -40)), (21, (760, v["z_disc_bot"] - 1.5), (790, -40)),
                        (14, (1003, P.TB + 5), (1060, -30)), (15, (1009, zb_ + 15), (1070, zb_ + 60)),
                        (4, (900, zt - 15), (900, zt + 35)), (1, (900, 30), (950, -40))]:
            S.balloon(Dp(p), Dp(q), n)
        S.text("R735 (eje anillo 3)", Dp((620, -30)), 2.2, "MIDDLE_LEFT")
        S.text("Pista inox B R440–R840", Dp((830, -32)), 2.2, "MIDDLE_LEFT")
    else:
        for n, p, q in [(14, (1003, P.TB + 5), (1060, -30)), (15, (1009, zb_ + 15), (1070, zb_ + 60)),
                        (4, (900, zt - 15), (900, zt + 35)), (1, (900, 30), (950, -40))]:
            S.balloon(Dp(p), Dp(q), n)
        S.leader(Dp((700, P.TB)), (Dp((640, 0))[0], Dp((0, -30))[1]), "", lines=["Pos 19: película grafito en ambas", "caras, 2 capas, 50–150 µm c/u"], h=2.2)
    S.view_title((Dp((800, 0))[0], 186), "DETALLE D – BORDE E INTERFAZ DE GIRO", "ESCALA 1:2")

    # --- E: trinquete (corte horizontal en eje del cilindro)
    vis, hid, hat = hlr.section(shapes, "top", (0, 0, za), (0, 0, -1), tol=1, nocut={5, 8})
    winE = (850, -440, 1210, 125)
    E = Place((612, 97), 0.4, (850, -440))
    E.polys(S, hlr.clip_polys(vis, winE)); E.hatches(S, hlr.clip_hatch(hat, winE))
    for k in (-2, -1, 0, 1):
        a_ = math.radians(-P.BAR_ANG0 + 10 * k)
        S.cross(E((P.R_BAR * math.cos(a_), P.R_BAR * math.sin(a_))), 2.5)
    S.line(E((P.X_CYL, -440)), E((P.X_CYL, 125)), "EJE")
    S.dim(E((xbar - 35, yi)), E((xbar + 35, yi)), 0.01 - 52, "Ø70") if False else None
    S.leader(E((xbar + 20, yi + 25)), E((1150, 60)), "Barra Ø70", h=2.1)
    S.dim(E((P.PAWL_TIP, yi)), E((P.PAWL_TIP, yi - P.PAWL_W)), -6, "85", orient="v")
    S.dim(E((P.PAWL_TIP, yi - P.PAWL_W)), E((P.SHOE_X0, yi - P.PAWL_W)), -10, nf(P.SHOE_X0 - P.PAWL_TIP))
    S.dim(E((P.SHOE_X0, yi + P.SHOE_FRONT)), E((P.SHOE_X1, yi + P.SHOE_FRONT)), 22, "130")
    S.dim(E((P.SHOE_X1, yi + P.SHOE_FRONT)), E((P.SHOE_X1, yi + P.SHOE_FRONT - P.SHOE_L)), 6, "300", orient="v")
    S.leader(E((xbar + 30, yi - 22)), E((1225, 40)), "Asiento R36", h=2.1)
    S.leader(E((P.PAWL_TIP + 15, yi - P.PAWL_W + 10)), E((960, -300)), "Chaflán 30°", h=2.1)
    p0 = E((P.SHOE_X1 + 25, -40)); S.line(p0, (p0[0], p0[1] + 30), "VIS"); S.arrow((p0[0], p0[1] + 30), math.pi / 2, size=3.5, w=1.2)
    S.text("EMPUJE", (p0[0] + 2, p0[1] + 12), 2.2, "MIDDLE_LEFT")
    for n, p, q in [(10, (1110, -200), (1300, -200)), (11, (1000, yi - 40), (1300, yi - 40)), (12, (P.X_CYL, ye), (1300, ye)),
                    (4, (880, -20), (880, 60))]:
        S.balloon(E(p), E(q), n)
    S.view_title((E((1030, 0))[0], 84), "DETALLE E – TRINQUETE Y BARRA (corte horiz. en eje)", "ESCALA 1:2,5")

    # ================= BOM =================
    rows = []
    for pos, desc, q, mat, mu in bom(v):
        rows.append([pos, desc, q, mat, fmt_kg(mu) if mu else "—"])
    y = S.table(598, 584, [("POS", 10, "C"), ("DESCRIPCIÓN", 88, "L"), ("CANT.", 13, "C"), ("MATERIAL / NORMA", macro_w := 81, "L"), ("kg/u", 21, "R")], rows, rh=5.4, h=2.15)
    S.text(f"MASA TOTAL APROX. DEL CONJUNTO: {fmt_kg(total_mass(v))} kg (sin carga, incl. cilindros)", (600, y - 4), 2.4, "TOP_LEFT", bold=True)
    S.text("LISTA DE MATERIALES", (598 + 106, 588.5), 3.2, "BOTTOM_CENTER", bold=True) if False else None

    # ================= NOTAS =================
    S.mtext(notes_general(v), (598, y - 12), h=2.1, ls=1.62, bold_first=True)

    # datos técnicos
    U_ = U
    dt = [["Capacidad nominal (WLL)", "500 tf (4 903 kN)"],
          ["Altura total (sup. disco)", f"{zt:.0f} mm"],
          ["Interfaz de giro", "UHMW-PE / inox 316L" if U_ else "Acero/acero + grafito"],
          ["Presión media interfaz (φd)", "6,99 MPa (pastillas)" if U_ else "1,73 MPa (contacto pleno)"],
          ["Presión máx. e = 150 mm", "11,08 MPa" if U_ else "2,77 MPa"],
          ["μ de diseño accionamiento", "0,15 (FU 0,53)" if U_ else "0,15–0,20 (FU 0,59–0,79)"],
          ["Fuerza cilindro (700 bar)", "2 × 445 kN"],
          ["Rotación por ciclo", "10° (36 libre + 164 de empuje)"]]
    S.table(25, 62, [("DATOS TÉCNICOS", 62, "L"), ("", 58, "L")], dt, rh=5.0, h=2.15, header_h=5.5)
    return S, v


if __name__ == "__main__":
    import sys
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet1(k)
        S.save(f"out/{v['code']}-01.dxf", f"out/{v['code']}-01.pdf")
        import pymupdf
        d = pymupdf.open(f"out/{v['code']}-01.pdf"); d[0].get_pixmap(dpi=75).save(f"out/{v['code']}-01.png")
        print("ok", k)
