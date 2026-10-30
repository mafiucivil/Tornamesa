"""Datos comunes: BOM, notas, utilidades de colocación."""
import json, math
import params as P

G = 9.80665
W_KN = 500 * G
ND = 1.10 * W_KN
A_CYL = 445e3 / 70.0          # mm2 (445 kN @ 700 bar)
ARM = 0.936                   # brazo mín. de la fuerza sobre la barra (m)


def masses(v):
    return {int(k): val for k, val in json.load(open(f"/home/claude/tt/out/{v['code']}_mass.json")).items()}


def pressure_bar(mu, v):
    r = 0.593 if v["kind"] == "U" else 0.667
    T = mu * W_KN * r + 3.0
    F = T / (2 * ARM)
    return F * 1e3 / A_CYL * 10


def bom(v):
    m = masses(v)
    U = v["kind"] == "U"
    rows = [
        (1, "Placa base 2400×2000×80 mecanizada", "1", "ASTM A572 Gr.50 – Z35", m[1]),
        (2, "Ménsula de reacción (conj. soldado)", "4", "ASTM A572 Gr.50", m[2] / 4),
        (3, "Oreja de izaje e=40", "4", "ASTM A572 Gr.50", m[3] / 4),
        (4, "Disco cajón Ø2000×160 (conj. soldado 4a–4f)", "1", "ASTM A572 Gr.50 – Z35", m[4]),
        (5, f"Pivote Ø150×{v['L_piv']:.0f}", "1", "42CrMo4+QT (EN 10083-3)", m[5]),
        (6, "Buje Ø190/Ø150×100 autolubricado", "1", "CuAl10Ni5Fe4 + grafito", m[6]),
        (7, "Tapa retenedora Ø240×20", "1", "S355J2", m[7]),
        (8, "Perno ISO 4762 M20×45 + arand. Nord-Lock", "6", "10.9 zincado laminar", m[8] / 6),
        (9, "Cilindro hidr. doble efecto 50 t, 700 bar, carrera 200", "2", "Comercial (ver lám. 4)", m[9] / 2),
        (10, "Carro de empuje 300×130×" + f"{v['shoe_top'] - P.TB:.0f}" + " (guiado)", "2", "S355J2+N + bandas UHMW", m[10] / 2),
        (11, "Trinquete 245×85×90 (asiento R36)", "2", "34CrNiMo6+QT 300–350 HB", m[11] / 2),
        (12, "Pasador Ø70 (ménsula y vástago)", "4", "42CrMo4+QT", m[12] / 4),
        (13, "Resorte trinquete Ø50 + tapa + manilla; clip R Ø8", "2+4", "Comercial", 0.6),
        (14, "Faldón de sello e=5, h=" + f"{v['z_disc_bot'] + P.TP_BOT - P.TB:.0f}" + ", L≈6300", "1", "NBR 70 Shore A", m[14]),
        (15, "Fleje de apriete 25×6 rolado Ø2022", "1", "S235JR galvanizado", m[15]),
        (16, "Perno ISO 4017 M8×20 + arandela", "36", "Inox A2-70", 0.02),
        (17, "Tapón prisionero M30×25 (agujeros izaje disco)", "4", "Acero 8.8 zincado", 0.1),
        (18, "Cáncamo giratorio M30, WLL ≥ 2,5 t (suelto)", "4", "Comercial", 2.2),
    ]
    if U:
        rows += [
            (19, "Pastilla deslizante Ø170×10", "34+4", "UHMW-PE (PE1000)", m[19] / 34),
            (20, "Pista inox A Ø810/Ø390×3", "1", "AISI 316L (1.4404)", m[20]),
            (21, "Pista inox B Ø1680/Ø880×3", "1", "AISI 316L (1.4404)", m[21]),
        ]
    else:
        rows += [
            (19, "Película seca de grafito, 2 capas 50–150 µm", "≈6,3 m²", "SLIP Plate® No. 4", 0.0),
            (20, "Grasa de protección (solo ambiente húmedo)", "—", "Según manual del film", 0.0),
        ]
    rows.append((22, "Guía de carro 40×30×850 (soldada a pos 1)", "2", "S355J2", m[22] / 2))
    return rows


def total_mass(v):
    tot = 0
    for pos, d, q, mat, mu in bom(v):
        try:
            n = int(q.split("+")[0])
        except ValueError:
            n = 1 if mu else 0
        tot += n * mu
    return tot


def notes_general(v):
    U = v["kind"] == "U"
    pn = pressure_bar(0.10 if U else 0.12, v)
    pa = 600
    mu_a = (pa / 10 * A_CYL / 1e3 * 2 * ARM - 3) / (W_KN * (0.593 if U else 0.667))
    n = [
        "NOTAS GENERALES",
        "1. CAPACIDAD NOMINAL (WLL): 500 tf = 4 903 kN. Factor dinámico de diseño φd = 1,10 (giro hidráulico lento).",
        "   Excentricidad del CG de la carga respecto del pivote ≤ 150 mm. Carga solo dentro de Ø1600 sobre parrilla",
        "   de reparto o ≥ 8 apoyos simétricos. PROHIBIDO cargas puntuales sobre el disco.",
        "2. NORMAS: AISC 360-22 (ASD); ASME BTH-1 Cat. A (Nd = 2,0, referencial elementos mecánicos);",
        "   AWS D1.1/D1.1M:2020; ISO 2768-mK; ISO 1101; ISO 1302" + ("; EN 1337-2 (superficies deslizantes)." if U else "."),
        "3. MATERIALES: certificado EN 10204 3.1. Planchas pos 1 y 4: UT según ASTM A578 nivel B, calidad Z35.",
        "4. SOLDADURA: WPS/PQR calificados AWS D1.1. Electrodo E7018 / ER70S-6" + ("; inox–carbono ER309L." if U else "."),
        "   Precalentamiento ≥ 110 °C en espesores > 65 mm (AWS D1.1 Tabla 5.8, Cat. B). CJP: UT 100 %. Filetes: MT 100 %.",
        "5. Conjunto soldado pos 1+2+3: alivio de tensiones 590–620 °C antes del mecanizado final.",
        "6. PROTECCIÓN: Sa 2½ + epóxico rico en zinc 75 µm + epóxico 125 µm + PU 50 µm (ISO 12944, C4).",
        "   Sin pintura: caras de deslizamiento, alojamientos, agujeros de pasadores, buje y roscas.",
        "7. INTERFAZ DE GIRO: " + ("pastillas UHMW-PE pos 19 en alojamientos de pos 1 contra pistas inox pos 20/21" if U
                                    else "contacto pleno acero-acero pos 1/pos 4 con película seca de grafito pos 19"),
        "   " + ("soldadas a pos 4. Operación EN SECO, sin grasa." if U else "en ambas caras. NO aplicar grasa en ambiente seco/polvoriento."),
        "8. ACCIONAMIENTO: 2 cilindros pos 9 en par sobre carros guiados pos 10; el trinquete pos 11 empuja",
        "   directo una barra vertical Ø70 del disco (36 barras c/10° en R940). Carrera 200 = 36 libre + 164 = 10°/ciclo.",
        "   Retorno: el trinquete se retrae por su chaflán al pasar la barra siguiente y engancha por resorte.",
        "   Rótulas GE70 en ambos ojales. PROHIBIDO empujar con un solo cilindro (válvula de bloqueo en paralelo).",
        f"   Presión esperada ≈ {pn:.0f} bar (μ ≈ {'0,10' if U else '0,12'}). Detener y revisar interfaz si p > {pa} bar (μ > {mu_a:.2f}).".replace("(μ > 0.", "(μ > 0,"),
        "   Giro antihorario: carros en x = ±1085 con ménsulas (+1085;-818) y (-1085;+818). Horario: invertir carro y ménsula.",
        "9. APOYO: base totalmente apoyada sobre losa de H.A. o mats rígidos; pendiente ≤ 0,5 %.",
        "   Presión de contacto bajo base: 1,03 MPa media / 1,49 MPa máx. (e = 150 mm).",
        "10. ENSAYO: giro 360° a 1,0 WLL registrando presión; estático 1,25 WLL si existe marco de reacción;",
        "    MT de soldaduras pos 2/3 posterior al ensayo.",
        "11. Cilindro: L0 = 450 entre ojales (retraído); verificar con proveedor y ajustar posición de pos 2 si difiere.",
    ]
    return n


def fmt_kg(x):
    return f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


class Place:
    """Transforma coordenadas de modelo (pantalla) a papel."""
    def __init__(self, O, s, m0=(0.0, 0.0)):
        self.O, self.s, self.m0 = O, s, m0

    def __call__(self, p):
        return (self.O[0] + (p[0] - self.m0[0]) * self.s, self.O[1] + (p[1] - self.m0[1]) * self.s)

    def polys(self, sh, polys, layer="VIS"):
        for pl in polys:
            pts = [self(p) for p in pl]
            if len(pts) == 2:
                sh.line(pts[0], pts[1], layer)
            else:
                sh.pline(pts, layer)

    def hatches(self, sh, hatches, small=(14, 20, 21)):
        ang = {1: 0, 2: 90, 3: 90, 4: 90, 5: 0, 6: 0, 7: 90, 8: 0, 10: 0, 11: 90, 12: 90, 15: 0, 19: 0}
        pat = {6: "ANSI33", 19: "ANSI37"}
        for pos, outer, holes in hatches:
            o = [self(p) for p in outer]
            hh = [[self(p) for p in h] for h in holes]
            if pos in small:
                sh.hatch_poly(o, hh, solid=True)
            else:
                sh.hatch_poly(o, hh, scale=0.55 if pos != 19 else 0.45, angle=ang.get(pos, 45), pattern=pat.get(pos, "ANSI31"))


def bbox(polys):
    xs = [p[0] for pl in polys for p in pl]
    ys = [p[1] for pl in polys for p in pl]
    return min(xs), min(ys), max(xs), max(ys)
