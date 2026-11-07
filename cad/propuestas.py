"""Propuestas técnicas del dibujante para lo que el cálculo no fija (rotuladas PROPUESTA / PROPUESTO, a confirmar por el responsable):
WPS pre-calificados (AWS D1.1 cl. 3), sistema de pintura (ISO 12944), grado comercial por Fy y especificación de componentes de catálogo.
Nada de esto sustituye una calificación de procedimiento ni la decisión del calculista; el rótulo obligatorio se imprime con cada uso."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import f, fm

ROTULO_WPS = "PROPUESTA — A CALIFICAR/CONFIRMAR POR EL FABRICANTE (AWS D1.1 cl. 3/4)"
ROTULO_PINT = "PROPUESTA, CONFIRMAR"
ROTULO_GRADO = "PROPUESTO por Fy del cálculo; confirmar"

# ------------------------------------------------------------------------------------------------
# precalentamiento mínimo AWS D1.1 Tabla 3.2 (acero Grupo II: ASTM A572 Gr.50; categoría B: bajo hidrógeno SMAW, GMAW, FCAW)
# espesor de la parte más gruesa de la junta [mm] -> °C
# ------------------------------------------------------------------------------------------------
def precalentamiento(t, categoria="B"):
    """AWS D1.1 Tabla 3.2, aceros Grupo I/II. Categoría B (E7018, ER70S-6, E71T-1): ≤19 mm: ninguno (≥ 10 °C de ambiente); 19–38: 10 °C; 38–65: 65 °C; >65: 110 °C.
    Categoría A (electrodos no bajo hidrógeno): 0; 65; 110; 150 °C."""
    if categoria == "A":
        return 0 if t <= 19 else 65 if t <= 38 else 110 if t <= 65 else 150
    return 0 if t <= 19 else 10 if t <= 38 else 65 if t <= 65 else 110


def pre_txt(t):
    v = precalentamiento(t)
    return "sin precalentar (T ≥ 10 °C, seco)" if v == 0 else f"{v} °C mín."


INTERPASE = "≤ 250 °C (propuesta)"

# rangos típicos de corriente (A) por proceso y diámetro de aporte; propuesta, a ajustar en la calificación del WPS
CORR = {
    "GMAW": "ER70S-6 Ø1,2 (Ar 75 % / CO₂ 25 %): 180–260 A, 23–28 V",
    "SMAW": "E7018 Ø3,2: 100–140 A · Ø4,0: 140–190 A · Ø5,0: 190–250 A (CC+)",
    "FCAW": "E71T-1 Ø1,2 (Ar-CO₂ 75/25): 180–260 A, 24–29 V",
}


def wps_family(w):
    """Clave de la familia WPS para un registro de junta de build_welds."""
    if w["groove"] and w["sym"] == "slot":
        return "RANURA"
    if w["groove"]:
        return "CJP-V" if w["sym"] == "V" else "CJP-BISEL"
    if "ER309L" in w["aporte"]:
        return "FILETE-INOX"
    return "FILETE"


FAM_TXT = {
    "FILETE": ("Filete en T (todas las posiciones de taller: 1F/2F; vertical 3F ascendente con SMAW/FCAW)", "1F, 2F (3F SMAW/FCAW)"),
    "FILETE-INOX": ("Filete en T con aporte inoxidable 309L sobre acero inoxidable (barras de topes UHMW), PT 100 %", "1F, 2F"),
    "CJP-V": ("Ranura en V 60° a tope con respaldo, penetración completa (CJP), serie AWS D1.1 Fig. 3.4 B-U4; confirmar designación", "1G, 2G"),
    "CJP-BISEL": ("Ranura con bisel 45° y respaldo, penetración completa (CJP), tipo AWS D1.1 Fig. 3.4 TC-U4; confirmar designación", "1G, 2G"),
    "RANURA": ("Soldadura de ranura (22 × 80), relleno completo, en posición plana", "1F"),
}


def wps_rows(ctx):
    """Filas de la tabla de WPS propuestos: una por número de WPS del registro de soldaduras."""
    grp = {}
    for w in ctx.welds:
        grp.setdefault(w["wps_n"], []).append(w)
    rows = []
    for n in sorted(grp):
        ws = grp[n]
        fam = wps_family(ws[0])
        tmax = max((x["t"] or 0) for x in ws)
        if fam in ("CJP-V", "CJP-BISEL"):
            passes = f"{max(x['pasadas'] for x in ws)} (raíz sobre respaldo + relleno + tapa)"
        else:
            passes = str(max(x["pasadas"] for x in ws))
        rows.append([f"WPS-P{n:02d}", ", ".join(x["id"] for x in ws), FAM_TXT[fam][0], FAM_TXT[fam][1], CORR["GMAW"], CORR["SMAW"], CORR["FCAW"], pre_txt(tmax) + f" (t mayor = {fm(tmax, 0)} mm)", INTERPASE, passes])
    return rows


WPS_COLS = [("WPS", 13, "C"), ("Juntas", 22, "L"), ("Tipo de junta", 62, "L"), ("Posición", 20, "L"), ("GMAW 135 (típico)", 40, "L"), ("SMAW 111 (típico)", 44, "L"), ("FCAW 136 (típico)", 38, "L"),
            ("Precalentamiento (Tabla 3.2, Gr. II, cat. B)", 38, "L"), ("Interpase", 24, "L"), ("Pasadas", 28, "L")]


# ------------------------------------------------------------------------------------------------
# pintura
# ------------------------------------------------------------------------------------------------
SISTEMA_PINTURA = [
    ("Preparación de superficie", "Chorro abrasivo Sa 2½ (ISO 8501-1), perfil 50–75 µm (ISO 8503)", "—"),
    ("Imprimación", "Epoxi rico en zinc (≥ 80 % Zn en película seca)", "60 µm"),
    ("Intermedia", "Epoxi poliamida de alto sólido", "120 µm"),
    ("Acabado", "Poliuretano alifático (color a definir por el mandante)", "60 µm"),
    ("EPS total", "Sistema ISO 12944-5 para C4 alta (H), vida útil alta; tolerancia: 80 % de las medidas ≥ EPS nominal, ninguna < 80 %", "240 µm"),
]


def pintura_txt():
    return (f"Pintura: ISO 12944 C4 alta, Sa 2½; epoxi-zinc 60 µm + epoxi 120 µm + PU 60 µm = EPS 240 µm ({ROTULO_PINT}). "
            "Sin pintura: caras de apoyo/deslizantes, agujeros con ajuste, zona de soldadura hasta su inspección, roscas.")


# ------------------------------------------------------------------------------------------------
# grado comercial por Fy
# ------------------------------------------------------------------------------------------------
# límite elástico mínimo Re [MPa] de aceros bonificados (EN 10083-3 / EN 10083-2) por diámetro de barra: (d_max, Re)
BON = [
    ("C45+QT (EN 10083-2)", [(16, 490), (40, 430), (100, 370), (250, 340)]),
    ("42CrMo4+QT (EN 10083-3)", [(16, 900), (40, 750), (100, 650), (160, 550), (250, 500)]),
    ("34CrNiMo6+QT (EN 10083-3)", [(16, 1000), (40, 900), (100, 800), (160, 700), (250, 600)]),
]


def _re(tab, d):
    for dm, re_ in tab:
        if d <= dm:
            return re_
    return 0


def grado(Fy, d=None, kind="plancha"):
    """Grado comercial más económico que cumple Fy para una barra de diámetro/espesor d [mm]. Devuelve texto rotulado PROPUESTO."""
    if kind == "plancha" and (d is None or d <= 100):
        if Fy <= 345:
            return f"ASTM A572 Gr.50 (Fy ≥ 345 MPa) — {ROTULO_GRADO}"
        if Fy <= 450 and (d is None or d <= 32):
            return f"ASTM A572 Gr.65 (Fy ≥ 450 MPa, t ≤ 32 mm) — {ROTULO_GRADO}"
    dd = d or 100
    for nm, tab in BON:
        re_ = _re(tab, dd)
        if re_ >= Fy:
            return f"{nm}, Re ≥ {re_} MPa (Ø/e {fm(dd, 0)} mm) — PROPUESTO por Fy ≥ {f(Fy)} MPa del cálculo; confirmar"
    return f"A DEFINIR POR EL CALCULISTA: ningún acero bonificado comercial de la tabla alcanza Fy ≥ {f(Fy)} MPa con Ø/e {fm(dd, 0)} mm"


def grado_corto(Fy, d=None, kind="plancha"):
    t = grado(Fy, d, kind)
    return t.split(" — ")[0]


# ------------------------------------------------------------------------------------------------
# catálogos: tipo de componente y características exigidas; marca/modelo por catálogo
# ------------------------------------------------------------------------------------------------
def catalogo_rows(ctx):
    P, g = ctx.P, ctx.g
    rows = [
        ["Cilindro hidráulico de doble efecto (×2)", f"Camisa Ø{f(P['D_bore'])}, vástago Ø{f(P['d_rod'])}, carrera {f(P['stroke'])} mm, largo ojal–ojal retraído {f(P['L0'])} mm, presión nominal {fm(P['p_rated'] * 0.0689476, 0)} bar (700 bar), alivio {f(P['p_relief'])} bar, ojales con rótula esférica autolubricada Ø{f(P['d_pp'])}, b = {f(P['b_eye'])} mm, masa ≈ {fm(P['m_cyl'], 0)} kg",
         f"Certificado de prueba hidráulica a 1,5 × {f(P['p_relief'])} bar; EN 10204 3.1", "marca/modelo A DEFINIR POR CATÁLOGO (proveedor)"],
        ["Grasera recta DIN 71412 M10×1", f"{g.n_greaser} unidades; acero zincado; rosca M10×1 (ISO 261), conducto Ø6", "Lote con certificado de conformidad", "marca/modelo A DEFINIR POR CATÁLOGO"],
        ["Tornillo ISO 4762 M20×45 cl. 10.9 con arandela", f"{g.N_pin} unidades; recubrimiento zincado/dacromet; arandela dura (HV 300 mín.) Ø{f(g.washer_D)}", "Certificado del lote EN 10204 2.2/3.1", "marca/modelo A DEFINIR POR CATÁLOGO"],
        ["Grillete de izaje ASME B30.26 (×4)", f"Pasador ≤ {fm(P['d_ear'] - P['g_ear'], 0)} mm; WLL ≥ lo calculado en la fila «Orejas de izaje» del núcleo; con certificado de prueba", "Prueba de carga 1,25 × WLL", "marca/modelo A DEFINIR POR CATÁLOGO"],
        ["Buje autolubricado", f"Ø{f(g.d_bush)} / Ø{f(P['D_piv'])} × {f(P['L_bush'])}; presión ≤ {fm(P['p_bush'], 0)} MPa; μ ≤ {fm(P['mu_bush'], 2)}; sobre aleación de bronce con lubricante sólido", "Certificado del proveedor", "marca/modelo A DEFINIR POR CATÁLOGO"],
        ["Resorte de retorno de la uña (compresión) (×2)", f"Carrera ≥ {f(g.KG['travel'] + 5)} mm; fuerza 150–300 N", "—", "marca/modelo A DEFINIR POR CATÁLOGO"],
        ["Grasa grafitada NLGI 2", "≥ 10 % grafito, aditivos EP; película 0,3–0,5 mm por cara", "Hoja de datos del fabricante", "marca/modelo A DEFINIR POR CATÁLOGO"],
        ["Tornillos ISO 10642 M10 cl. 10.9 (tapas del pivote)", "4 × M10×25 (tapa retenedora) y 6 × M10 (tapa de inspección); zincados", "Certificado del lote", "marca/modelo A DEFINIR POR CATÁLOGO"],
    ]
    return rows
