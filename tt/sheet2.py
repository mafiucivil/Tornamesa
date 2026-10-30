"""Lámina 2: isométricas (conjunto y explosionada), montaje y operación."""
import math
import cadquery as cq
import params as P, model3d as M, hlr, draw
from common import Place, bbox, pressure_bar

EXP = {17: 2.1, 19: 0.4, 20: 2.1, 21: 2.1, 4: 2.1, 6: 2.1, 14: 2.1, 15: 2.1, 16: 2.1, 7: 3.6, 8: 4.1, 9: 3.1, 10: 3.1, 11: 3.1, 12: 3.1}


def anchors(v):
    zt, zdb, za = v["z_disc_top"], v["z_disc_bot"], v["z_axis"]
    X = P.X_CYL
    a = {1: (300, -1000, 40), 2: (X + 80, -P.Y_BRK, P.TB + v["H_cheek"] - 20), 3: (620, -925, P.TB + 60),
         4: (-200, -700, zt), 5: (0, -75, 60), 6: (0, -95, zdb + 40), 7: (0, -120, v["z_piv_top"] + 20),
         8: (50, 0, v["z_piv_top"] + 30), 9: (X, -600, za + 60), 10: (P.SHOE_X1, -250, za),
         11: (1000, -120, za + 45), 12: (X + 100, -P.Y_BRK, za), 14: (711, -711, P.TB + 15),
         15: (-300, -965.4, zdb + 15), 17: (424, -424, zt), 22: (X, 250, P.TB + 30)}
    if v["kind"] == "U":
        a.update({19: (520, -520, P.TB + 5), 20: (-560, -560, zdb), 21: (690, -690, zdb)})
    return a


def sheet2(kind):
    v, parts = M.build(kind)
    v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 2, 4, "ISOMÉTRICAS – MONTAJE Y OPERACIÓN", "1:10")
    U = kind == "U"
    shapes = [(p, s.val()) for p, n, s, c in parts]
    view = "iso"
    # ------ conjunto
    comp = cq.Compound.makeCompound([s for _, s in shapes])
    vis, _ = hlr.hlr(comp, view, tol=5)
    x0, y0, x1, y1 = bbox(vis)
    s = 1 / 10
    T = Place((178, 462), s, ((x0 + x1) / 2, (y0 + y1) / 2))
    T.polys(S, vis)
    S.view_title((178, 352), "VISTA ISOMÉTRICA – CONJUNTO", "ESCALA 1:10")
    # ------ explosionada
    ex = 420.0
    sh2 = []
    for p, sh in shapes:
        sh2.append((p, sh.translate(cq.Vector(0, 0, EXP.get(p, 0) * ex))))
    comp2 = cq.Compound.makeCompound([sh for _, sh in sh2])
    vis2, _ = hlr.hlr(comp2, view, tol=5)
    x0, y0, x1, y1 = bbox(vis2)
    E = Place((488, 335), s, ((x0 + x1) / 2, (y0 + y1) / 2))
    E.polys(S, vis2)
    cx = 488
    # globos en dos columnas
    an = anchors(v)
    pts = []
    for pos, p3 in an.items():
        p3 = (p3[0], p3[1], p3[2] + EXP.get(pos, 0) * ex)
        pts.append((pos, E(hlr.proj_pt(p3, view))))
    left = sorted([q for q in pts if q[1][0] < cx], key=lambda t: -t[1][1])
    right = sorted([q for q in pts if q[1][0] >= cx], key=lambda t: -t[1][1])
    for col, xb in ((left, 338), (right, 640)):
        n = len(col)
        ytop = 545
        for i, (pos, pp) in enumerate(col):
            yb = min(pp[1], ytop - i * 0) if False else None
        ys = []
        for i, (pos, pp) in enumerate(col):
            y = pp[1]
            if ys and y > ys[-1] - 11:
                y = ys[-1] - 11
            ys.append(y)
        for (pos, pp), y in zip(col, ys):
            S.balloon(pp, (xb, y), pos)
    S.view_title((488, 92), "VISTA ISOMÉTRICA EXPLOSIONADA", "ESCALA 1:10 – globos según lista de materiales lámina 1")
    # ------ textos
    pbar = pressure_bar(0.10 if U else 0.12, v)
    mont = ["SECUENCIA DE MONTAJE",
            "1. Placa base pos 1 (con pos 2 y 3 soldadas, relevada y mecanizada) sobre apoyo nivelado (≤ 0,5 %).",
            "2. Pivote pos 5 calado en caliente en pos 1 (H7/p6; calentar pos 1 local a ≤ 200 °C o enfriar pos 5),",
            "   soldadura de sello inferior y esmerilado a ras.",
            ("3. Limpiar alojamientos; colocar 34 pastillas pos 19 (ajuste deslizante, sin adhesivo)." if U else
             "3. Desengrasar caras de contacto de pos 1 y pos 4; aplicar 2 capas pos 19 (24 h entre capas, 10–38 °C)."),
            ("4. Buje pos 6 prensado en el cubo 4c (H7/s6). Pistas pos 20/21 soldadas y pulidas previamente en pos 4." if U else
             "4. Buje pos 6 prensado en el cubo 4c (H7/s6). Verificar planitud ≤ 0,20 mm de ambas caras antes del film."),
            "5. Izar pos 4 con 4 cáncamos pos 18 (M30) y bajar centrado sobre pos 5 sin golpear la interfaz.",
            "6. Tapa pos 7 con 6 pernos pos 8 (M20 10.9, par según tabla, arandela Nord-Lock). Juego vertical 3 mm.",
            "7. Faldón pos 14 y fleje pos 15 con 36 pernos pos 16. Retirar cáncamos y colocar tapones pos 17.",
            "8. Carros pos 10 sobre guías pos 22 con trinquete pos 11 y resorte pos 13 (trinquete hacia el sentido de giro);",
            "   cilindros pos 9 entre ménsula activa y carro con pasadores pos 12 + clips. Mangueras 700 bar (CR400).",
            "9. Prueba en vacío: 2 ciclos completos; luego ensayo de carga según nota 10, lámina 1."]
    oper = ["SECUENCIA DE OPERACIÓN (POR CICLO)",
            "a) Extender ambos cilindros a la vez (colector común): 36 mm libres, el trinquete toma la barra y la carga",
            "   gira 10° hasta fin de carrera (200 mm).",
            "b) Retraer a fondo: el chaflán del trinquete pasa sobre la barra siguiente y el resorte lo engancha.",
            "   Verificar visualmente el enganche de ambos trinquetes antes del ciclo siguiente.",
            f"c) Registrar presión de giro. Esperada ≈ {pbar:,.0f} bar. Detener si supera 600 bar.".replace(",", "."),
            "d) Para invertir el sentido: retirar cilindros y carros, girar cada carro 180° y usar la ménsula opuesta.",
            "e) No operar con viento > 50 km/h ni con la carga sin arriostrar. Personal fuera del radio de giro.",
            "",
            "MANTENIMIENTO",
            ("• Cada uso: limpiar pistas inox pos 20/21 con paño y alcohol; no usar abrasivos." if U else
             "• Cada uso: inspeccionar film pos 19; si hay óxido o metal desnudo > 10 %: limpiar a metal y reaplicar."),
            ("• Reemplazar pastillas con resalte < 3,0 mm o con fisuras. Retirar con varilla por agujero Ø10." if U else
             "• No aplicar grasa en ambiente seco o con polvo (la grasa atrapa partículas)."),
            "• Guardar bajo techo, con el disco calzado y el faldón protegido del sol."]
    y = S.mtext(mont, (26, 330), h=2.3, ls=1.6, bold_first=True)
    S.mtext(oper, (26, y - 7), h=2.3, ls=1.6, bold_first=True)
    fits = [["Pivote 5 / placa base 1", "Ø150 H7/p6", "Calado en caliente"],
            ["Pivote 5 / buje 6", "Ø150 H7/f7", "Giratorio"],
            ["Buje 6 / disco 4", "Ø190 H7/s6", "Prensado"],
            ["Trinquete 11 / alojamiento carro 10", "85×90 H9/f8", "Deslizante"],
            ["Carro 10 / guía 22", "Ranura 41 H11 / 40 h9", "Guiado"],
            ["Barra 4f / agujeros planchas 4a, 4b", "Ø70 / Ø71", "Soldada"],
            ["Pasadores 12 / ménsula, carro", "Ø70 H9/f8 (rótula GE70)", "Deslizante"],
            ["Pernos 8 M20 10.9 (VDI 2230, μ 0,12)", "540 N·m", "Nord-Lock"],
            ["Pernos 16 M8 A2-70", "18 N·m", "Antigripante"],
            ["Tapones 17 M30", "Manual + fijador media", "Ras con disco"]]
    if U:
        fits.insert(5, ["Pastilla 19 / alojamiento", "Ø170 -0,1/-0,2 – Ø170,6 +0,1/0", "Holgura térmica"])
    S.table(26, 140, [("AJUSTES Y PARES DE APRIETE", 80, "L"), ("VALOR", 58, "L"), ("OBS.", 32, "L")], fits, rh=5.0, h=2.1)
    return S, v


if __name__ == "__main__":
    import sys, pymupdf
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet2(k)
        S.save(f"out/{v['code']}-02.dxf", f"out/{v['code']}-02.pdf")
        pymupdf.open(f"out/{v['code']}-02.pdf")[0].get_pixmap(dpi=75).save(f"out/{v['code']}-02.png")
        print("ok", k)
