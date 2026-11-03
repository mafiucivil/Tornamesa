"""Memoria de cálculo TT300-C en Word (.docx) y PDF, generada desde cad/out/TT300-C_design.json.

Fuente única: todos los valores salen del núcleo (tools/export_design.js → TT.analyze). Este script solo redacta.
Formato: texto negro, hipótesis → desarrollo → resultado, tablas antes que texto, 3 cifras significativas.
Uso: node tools/export_design.js > cad/out/TT300-C_design.json && python3 tools/memoria_tt300c.py
"""
import json, math, pathlib, subprocess, sys
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "cad" / "out"
D = json.load(open(OUT / "TT300-C_design.json", encoding="utf-8"))
M3 = json.load(open(OUT / "TT300-C_masas3d.json", encoding="utf-8")) if (OUT / "TT300-C_masas3d.json").exists() else None
P, DV, K = D["P"], D["derivados"], D["derivados"]["K"]
REV, DOC = "B", "TT300-C-MC-01"
BLACK = RGBColor(0, 0, 0)
FONT = "Arial"


# ---------------------------------------------------------------- formato numérico (coma decimal, 3 cifras significativas)
def n(x, sig=3, unit=""):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    if isinstance(x, bool):
        return "Sí" if x else "No"
    if isinstance(x, str):
        return x
    a = abs(x)
    if a == 0:
        s = "0"
    elif a >= 10 ** (sig - 1):
        s = f"{round(x):,.0f}".replace(",", ".")
    else:
        dec = max(0, sig - 1 - int(math.floor(math.log10(a))))
        s = f"{x:.{dec}f}".replace(".", ",")
    return s + (f" {unit}" if unit else "")


def pint(x):
    return f"{round(x):,.0f}".replace(",", ".")


# ---------------------------------------------------------------- documento y estilos en negro
doc = Document()
for st in doc.styles:
    try:
        if st.font is not None:
            st.font.color.rgb = BLACK
            st.font.name = FONT
            rpr = st.element.get_or_add_rPr()
            rf = rpr.find(qn("w:rFonts"))
            if rf is None:
                rf = OxmlElement("w:rFonts"); rpr.append(rf)
            for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                rf.set(qn(k), FONT)
    except (AttributeError, ValueError):
        pass
doc.styles["Normal"].font.size = Pt(10)
for lvl, sz in ((1, 14), (2, 12), (3, 10.5)):
    s = doc.styles[f"Heading {lvl}"]
    s.font.size = Pt(sz); s.font.bold = True; s.font.color.rgb = BLACK
    s.paragraph_format.space_before = Pt(12 if lvl == 1 else 8); s.paragraph_format.space_after = Pt(4)

sec = doc.sections[0]
sec.page_width, sec.page_height = Mm(210), Mm(297)
sec.left_margin = sec.right_margin = Mm(20); sec.top_margin = Mm(20); sec.bottom_margin = Mm(18)


def field(par, code):
    r = par.add_run()
    for tag, txt in (("begin", None), (None, code), ("separate", None), (None, "1"), ("end", None)):
        if tag:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tag); r._r.append(e)
        elif txt == code:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = code; r._r.append(e)
        else:
            e = OxmlElement("w:t"); e.text = txt; r._r.append(e)
    r.font.size = Pt(8); r.font.color.rgb = BLACK


def header_footer(s):
    s.header.is_linked_to_previous = False; s.footer.is_linked_to_previous = False
    hp = s.header.paragraphs[0]; hp.text = ""
    r = hp.add_run(f"TT300-C · Tornamesa hidráulica {P['W_tf']:.0f} tf · Memoria de cálculo {DOC} · Rev. {REV}")
    r.font.size = Pt(8); r.font.color.rgb = BLACK
    fp = s.footer.paragraphs[0]; fp.text = ""; fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = fp.add_run("Página "); r.font.size = Pt(8); r.font.color.rgb = BLACK
    field(fp, "PAGE")
    r = fp.add_run(" de "); r.font.size = Pt(8); r.font.color.rgb = BLACK
    field(fp, "NUMPAGES")


header_footer(sec)


def H(t, lvl=1):
    h = doc.add_heading(t, level=lvl)
    for r in h.runs:
        r.font.color.rgb = BLACK; r.font.name = FONT
    return h


def T(text, bold=False, italic=False, size=None, align=None, after=3):
    p = doc.add_paragraph()
    r = p.add_run(text); r.bold = bold; r.italic = italic; r.font.color.rgb = BLACK
    if size: r.font.size = Pt(size)
    if align: p.alignment = align
    p.paragraph_format.space_after = Pt(after)
    return p


def bullets(items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet"); r = p.add_run(it); r.font.color.rgb = BLACK
        p.paragraph_format.space_after = Pt(1)


def shade(cell, hexcolor="D9D9D9"):
    tcPr = cell._tc.get_or_add_tcPr(); sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), hexcolor); tcPr.append(sh)


def table(headers, rows, widths=None, size=8.5, num_cols=(), repeat=True):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(size); r.font.color.rgb = BLACK
        shade(c)
    if repeat:
        trPr = t.rows[0]._tr.get_or_add_trPr(); e = OxmlElement("w:tblHeader"); e.set(qn("w:val"), "true"); trPr.append(e)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; par = cells[i].paragraphs[0]
            r = par.add_run(str(v)); r.font.size = Pt(size); r.font.color.rgb = BLACK
            if i in num_cols: par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if widths:
        t.autofit = False
        tblPr = t._tbl.tblPr; lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
        grid = t._tbl.tblGrid
        for i, gc in enumerate(grid.findall(qn("w:gridCol"))):
            gc.set(qn("w:w"), str(int(widths[i] * 56.7)))
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Mm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


EST = {"ok": "Cumple", "warn": "Advertencia", "fail": "NO CUMPLE", "info": "Info", "pend": "Pendiente"}
VER = D["verificaciones"]
casos = {c["id"]: c for c in DV["casos"]}
cd = casos["dis"]
m = DV["masas"]
psi_bar = P["p_rated"] * 0.07

# ================================================================= PORTADA
T("MEMORIA DE CÁLCULO", bold=True, size=20, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
T(f"TORNAMESA HIDRÁULICA TT300-C · {P['W_tf']:.0f} tf", bold=True, size=15, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
T("Mesa giratoria Ø{0} para cargas sobredimensionadas (transformadores y equipos pesados). Accionamiento por cilindros con patín guiado y uña."
  .format(pint(P["D_top"])), size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=18)
table(["Campo", "Valor"], [
    ["Documento", DOC], ["Revisión", REV], ["Fecha", D["fecha"]],
    ["Estado", "Emitido para revisión – no apto para fabricación hasta aprobación"],
    ["Planos asociados", "TT300-C-D-01, D-02, F-01, F-02, F-03, F-04 (Rev. B)"],
    ["Herramienta de verificación", "dist/TT300-C_Verificacion.html (misma fuente de datos)"],
    ["Normas principales", "AISC 360-22 (ASD); ASME BTH-1, Categoría de diseño B (Nd = 3,0); AWS D1.1/D1.1M:2020"],
], widths=(50, 120), size=9.5)
table(["", "Nombre", "Firma", "Fecha"], [["Elaboró", "", "", ""], ["Revisó", "", "", ""], ["Aprobó", "", "", ""]], widths=(25, 65, 45, 35), size=9.5)
T("Todos los valores de esta memoria se generan automáticamente desde el núcleo de cálculo TT300-C; no se transcriben a mano. "
  "Un cambio de parámetros regenera memoria, planos y herramienta con la misma fuente.", italic=True, size=8.5)
doc.add_page_break()

# ================================================================= 1. OBJETO
H("1. Objeto y alcance")
T("Verificar la tornamesa hidráulica TT300-C para el giro de cargas de hasta {0} tf: mesa giratoria soldada tipo cajón, base, pivote central, "
  "pasadores de empuje, accionamiento hidráulico (cilindros, patines guiados y uñas), articulaciones, soldaduras, izaje del equipo y fatiga."
  .format(pint(P["W_tf"])))
table(["Ítem", "Incluido", "Observación"], [
    ["Giro bajo carga (capacidad del accionamiento)", "Sí", "Casos de fricción nominal, diseño, borde, contaminado y seco"],
    ["Cadena de empuje", "Sí", "Verificada a la fuerza de calado (área × presión de alivio)"],
    ["Mesa y base", "Sí", "FEA propio (MITC4 / Q4) más flexión global axisimétrica"],
    ["Izaje del equipo vacío", "Sí", f"4 puntos, factor dinámico {n(P['phi_lift'])}"],
    ["Fatiga", "Sí", f"{pint(P['turns_yr'])} vueltas/año × {pint(P['life'])} años"],
    ["Sismo", "No aplica", "Decisión del mandante (Ch = 0). Instalación permanente: verificar con NCh2369"],
    ["Losa o terreno de apoyo", "No", f"Presión de contacto informada ({n(DV['q_max'], unit='MPa')}); la verifica un tercero"],
], widths=(65, 22, 83))

# ================================================================= 2. NORMAS
H("2. Normas y criterios")
reg = (ROOT / "docs" / "normas" / "registro.md").read_text(encoding="utf-8").splitlines()
rows = []
for ln in reg:
    if ln.startswith("|") and not ln.startswith("|---") and "Ámbito" not in ln:
        c = [x.strip() for x in ln.strip("|").split("|")]
        if len(c) >= 3: rows.append(c[:3])
table(["Ámbito", "Criterio", "Referencia"], rows, widths=(38, 82, 50), size=8)

# ================================================================= 3. DESCRIPCIÓN
H("3. Descripción del sistema")
table(["Componente", "Descripción"], [
    ["Mesa giratoria (pos 2)", f"Cajón soldado Ø{pint(P['D_top'])} × {pint(P['h_disc'])}: plancha superior e={pint(P['t_top'])}, inferior e={pint(P['t_bot'])}, "
                               f"almas anulares R {', '.join(pint(r) for r in D['almas'])} (e={pint(P['t_web'])}), {pint(P['N_rib'])} nervios e={pint(P['t_rib'])}, anillos de pasadores e={pint(P['t_pr'])}"],
    ["Pasadores de empuje (pos 3)", f"{pint(P['N_pin'])} × Ø{pint(P['d_pin'])} en R{pint(P['R_pin'])}; paso {n(360 / P['N_pin'])}°; Fy ≥ {pint(P['Fy_pin'])} MPa"],
    ["Base (pos 1)", f"Plancha {pint(P['B'])} × {pint(P['B'])} × {pint(P['t_base'])} con marco perimetral, ménsulas de cilindro, bancadas de guía y 4 puntos de izaje"],
    ["Pivote (pos 5) y buje (pos 6)", f"Pivote Ø{pint(P['D_piv'])}; buje autolubricado L = {pint(P['L_bush'])}"],
    ["Interfaz de giro", "Acero-acero con grasa grafitada (pos 14) sobre la cara inferior de la mesa"],
    ["Cilindros (pos 9)", f"{pint(P['n_cyl'])} × doble efecto Ø{pint(P['D_bore'])}/Ø{pint(P['d_rod'])}, carrera {pint(P['stroke'])}, clase {pint(P['p_rated'])} psi ({pint(psi_bar)} bar), "
                          f"alivio {pint(P['p_relief'])} bar, alarma {pint(P['p_alarm'])} bar"],
    ["Patín guiado (pos 16) y bancada (pos 1e)", f"Patín coaxial con el cilindro en x = ±{pint(P['x_g'])}; lengüeta en ranura {pint(P['w_slot'])} H8 × {pint(P['h_slot'])}; largo de guía efectivo Lg = {n(K['Lg'])}"],
    ["Uña deslizante (pos 10) y resorte (pos 12)", f"Uña {pint(P['dog_b'])} × {pint(P['dog_h'])}, retorno radial {n(K['travel'])} mm contra resorte; reengancha detrás del pasador siguiente"],
], widths=(48, 122), size=8.5)
T("Funcionamiento: los dos cilindros trabajan en par simétrico (par puro sobre la mesa). En cada carrera la uña toma un pasador y la mesa gira un paso; "
  "al retraer, la cara trasera achaflanada de la uña la desplaza radialmente contra el resorte, pasa el pasador siguiente y se reengancha. "
  "Para invertir el sentido de giro se trasladan cilindros, patines y uñas a las ménsulas del otro extremo de la guía.")

# ================================================================= 4. HIPÓTESIS
H("4. Hipótesis")
H("4.1 Cargas y combinaciones", 2)
table(["Magnitud", "Símbolo", "Valor", "Origen"], [
    ["Capacidad nominal (WLL)", "W", n(DV["W"], unit="kN") + f" ({pint(P['W_tf'])} tf)", "Mandante; modificable"],
    ["Excentricidad máxima del CG", "e", n(P["e"], unit="mm"), "Criterio del proyecto"],
    ["Factor de impacto de diseño", "φ_d", n(P["phi_d"]), "Criterio del proyecto"],
    ["Peso propio de mesa + ½ pivote", "W_d", n(DV["N"] - DV["W"], unit="kN"), "Núcleo (masas)"],
    ["Normal sobre la interfaz", "N = W + W_d", n(DV["N"], unit="kN"), "Giro"],
    ["Normal de diseño", "N_D = φ_d·W + W_d", n(DV["ND"], unit="kN"), "Presión de contacto"],
    ["Factor de diseño cadena de empuje", "Nd", n(P["Nd"]), "ASME BTH-1 Cat. B"],
    ["Fuerza de calado por cilindro", "F_calado = A·p_alivio", n(DV["Fstall"], unit="kN"), f"A = {pint(DV['A'])} mm², p = {pint(P['p_relief'])} bar"],
    ["Factor dinámico de izaje", "φ_izaje", n(P["phi_lift"]), "Criterio del proyecto"],
    ["Sismo", "Ch", n(P["Ch"]), "No aplica"],
], widths=(55, 40, 35, 40))
H("4.2 Materiales", 2)
table(["Elemento", "Material", "Fy (MPa)"], [
    ["Planchas de mesa, base, ménsulas, bancadas", "ASTM A572 Gr.50", pint(P["Fy"])],
    ["Pasadores de empuje (pos 3)", "34CrNiMo6+QT (EN 10083-3)", pint(P["Fy_pin"])],
    ["Uña (pos 10)", "34CrNiMo6+QT", pint(P["Fy_dog"])],
    ["Pasadores de articulación (pos 11)", "42CrMo4+QT", pint(P["Fy_pp"])],
    ["Pivote (pos 5)", "42CrMo4+QT", pint(P["Fy_piv"])],
    ["Soldadura", f"E70 (FEXX = {pint(P['FEXX'])} MPa)", "—"],
], widths=(80, 60, 30))
T(f"E = {pint(P['E'])} MPa; ν = {n(P['nu'])}. Factor de malla FEA k = {n(P['kFEA'])} aplicado a las tensiones locales.")
H("4.3 Fricción en la interfaz de giro", 2)
table(["Caso", "μ", "Radio de fricción", "Justificación"], [
    ["Nominal (grasa grafitada limpia)", n(P["mu_nom"]), f"r_u = {n(D['apoyo']['r_u'])} mm (presión uniforme)", "Valor esperado de operación"],
    ["Diseño", n(P["mu_d"]), f"r_ef = {pint(P['r_ef'])} mm", "Límite superior con excentricidad"],
    ["Contacto en el borde", n(P["mu_d"]), f"R = {pint(D['apoyo']['Ro'])} mm", "Mesa apoyada solo en el borde (revisión M1)"],
    ["Grasa contaminada", n(P["mu_cont"]), f"r_ef = {pint(P['r_ef'])} mm", "Arena o película degradada"],
    ["Acero seco (referencial)", n(P["mu_dry"]), f"r_u = {n(D['apoyo']['r_u'])} mm", "No es condición de operación"],
], widths=(52, 15, 55, 48))
H("4.4 Parámetros de entrada", 2)
T("Valores de la configuración verificada (todos editables en la herramienta HTML; la herramienta repite las verificaciones de esta memoria).", size=9)
for g in D["grupos"]:
    rows = [[p["lab"], p["id"], (P[p["id"]] if isinstance(P[p["id"]], str) else n(P[p["id"]], 4)), p["u"]] for p in g["p"]]
    T(g["titulo"], bold=True, size=9, after=1)
    table(["Parámetro", "Id", "Valor", "Unidad"], rows, widths=(100, 25, 25, 20), size=7.5, num_cols=(2,))

# ================================================================= 5. MASAS
H("5. Masas")
mrows = [["Plancha superior", m["top"]], ["Plancha inferior", m["bot"]], ["Almas anulares", m["webs"]], ["Nervios radiales", m["ribs"]],
         ["Cubo", m["hub"]], ["Pasadores de empuje", m["pins"]], ["Subtotal mesa", m["disc"]], ["Plancha base", m["base"]], ["Marco perimetral", m["rim"]],
         ["Ménsulas de cilindro", m["brackets"]], ["Bancadas de guía", m["beds"]], ["Patines", m["shoes"]], ["Uñas", m["dogs"]], ["Pivote", m["pivot"]],
         ["Cilindros", m["cyl"]], ["TOTAL", m["total"]]]
table(["Componente", "Masa (kg)"], [[a, n(b)] for a, b in mrows], widths=(80, 30), num_cols=(1,))
if M3:
    dmax = max(abs(r["dif_%"]) for r in M3["comparacion"])
    T(f"Control: las masas se recalculan sobre el modelo 3D (CadQuery). Diferencia máxima 3D frente al núcleo: {n(dmax)} %.", size=9)

# ================================================================= 6. INTERFAZ
H("6. Interfaz de giro y presión de contacto")
ap = D["apoyo"]
T("Hipótesis: contacto anular entre R_i = {0} y R_o = {1} mm, distribución lineal por la excentricidad e (núcleo central).".format(n(ap["Ri"]), pint(ap["Ro"])))
table(["Magnitud", "Expresión", "Valor"], [
    ["Área de contacto", "A_c = π(R_o² − R_i²)", n(ap["Ac"] / 1e6, unit="m²")],
    ["Presión media", "q = N_D / A_c", n(DV["q_avg"], unit="MPa")],
    ["Presión máxima", "q_máx = q·(1 + 4eR_o/(R_o² + R_i²))", n(DV["q_max"], unit="MPa")],
    ["Presión mínima", "q_mín = q·(1 − 4eR_o/(R_o² + R_i²))", n(ap["q_min"], unit="MPa")],
    ["Radio de fricción (presión uniforme)", "r_u = ⅔(R_o³ − R_i³)/(R_o² − R_i²)", n(ap["r_u"], unit="mm")],
    ["Empuje horizontal por excentricidad (μ_d)", "H = μN·e·(4/3)(R_o³ − R_i³)/(R_o⁴ − R_i⁴)", n(ap["H_ecc_d"], unit="kN")],
    ["Par de fricción del pivote (μ_d)", "T_piv = μ_buje·H·D_piv/2", n(ap["T_piv_d"], unit="kN·m")],
], widths=(60, 75, 35))
T(f"Resultado: q_mín > 0, la mesa no despega. La presión máxima {n(DV['q_max'], unit='MPa')} se transmite a la losa o a los mats a través de la base delgada; "
  "su verificación corresponde a un tercero.")

# ================================================================= 7. ACCIONAMIENTO
H("7. Accionamiento")
H("7.1 Par resistente", 2)
T("T(μ, r) = μ·N·r + T_piv(μ)   [equilibrio de momentos respecto del eje del pivote]")
H("7.2 Cinemática del accionamiento guiado", 2)
table(["Magnitud", "Expresión", "Valor"], [
    ["Paso angular", "2π/N_pas", n(360 / P["N_pin"], unit="°")],
    ["Brazo mínimo (toma del pasador)", "a_mín = R_pas·cos(π/N)", n(K["armMin"], unit="mm")],
    ["Cuerda entre pasadores", "c = 2R_pas·sin(π/N)", n(K["chord"], unit="mm")],
    ["Carrera requerida", "s_req = s_libre + c", n(K["s_req"], unit="mm")],
    ["Margen de carrera", "carrera − s_req", n(K["margin"], unit="mm")],
    ["Excentricidad máxima eje cilindro–pasador", "Δ = x_g − a_mín", n(K["DeltaMax"], unit="mm")],
    ["Largo efectivo de guía", "Lg = ⅔·L_patín", n(K["Lg"], unit="mm")],
    ["Factor de guía", "K = (1 + 2μ_g·Δ/Lg)/η_c", n(DV["Kguide"], 4)],
    ["Fuerza por cilindro", "F_cil = K·T/(n·a)", "ver 7.3"],
], widths=(65, 65, 40))
T("Equilibrio del patín: la fuerza del cilindro actúa sobre x_g y la reacción del pasador sobre x = R·cos θ. El par F·Δ lo toman dos reacciones de la bancada "
  "separadas Lg (R_guía = F_pas·Δ/Lg), cuya fricción 2μ_g·R_guía produce el factor K. La expresión se contrasta en el revisor cruzado por trabajos virtuales (Anexo A).")
H("7.3 Casos de fricción (por cilindro, brazo mínimo)", 2)
table(["Caso", "μ", "r (mm)", "T (kN·m)", "F_cil (kN)", "p (bar)", "FS al calado", "¿Gira?"],
      [[c["nombre"], n(c["mu"]), n(c["r"]), n(c["T"]), n(c["F"]), n(c["p"]), n(c["FS"]), "Sí" if c["gira"] else "NO"] for c in DV["casos"]],
      widths=(52, 12, 16, 18, 18, 16, 20, 14), size=8, num_cols=(1, 2, 3, 4, 5, 6))
T(f"Resultado: en el caso de diseño F_cil = {n(cd['F'], unit='kN')} a {n(cd['p'], unit='bar')}; FS = F_calado/F_dis = {n(cd['FS'])} ≥ FS_mín = {n(P['FS_min'])}. "
  f"μ máximo que gira con r_ef: {n(DV['muMax_ref'])}.", bold=True)
H("7.4 Fuerzas a lo largo de la carrera (caso de diseño)", 2)
table(["Posición", "θ (°)", "a (mm)", "Δ (mm)", "K", "F_cil (kN)", "p (bar)", "F_pas (kN)", "Tangencial (kN)", "Radial (kN)", "R_guía (kN)"],
      [[c["pos"], n(c["th"]), n(c["arm"]), n(c["Delta"]), n(c["Kg"]), n(c["F"]), n(c["p"]), n(c["Fpin"]), n(c["Ft"]), n(c["Fr"]), n(c["Rg"])] for c in D["carrera"]],
      widths=(24, 12, 15, 13, 12, 16, 13, 16, 18, 15, 16), size=7.5, num_cols=tuple(range(1, 11)))
T("La componente radial (F_pas·sin θ, máximo 11 %) la toma el pivote; la tangencial es ≥ 99,4 % de F_pas. "
  f"Las piezas de la guía se verifican con la fuerza de calado: R_guía = F_calado·Δ/Lg = {n(DV['Rguide'], unit='kN')}.")
H("7.5 Clase de presión del cilindro", 2)
table(["Clase (psi)", "Alivio / alarma (bar)", "Émbolo mínimo (mm)", f"FS con Ø{pint(P['D_bore'])}", "p diseño (bar)"],
      [[pint(c["psi"]), f"{pint(c['pr'])} / {pint(c['pa'])}", n(c["Dmin"]), n(c["FScur"]), n(c["pcur"])] for c in D["escenarios"]["classes"]],
      widths=(28, 38, 34, 34, 30), num_cols=(2, 3, 4))
T("Émbolo mínimo = máx(FS_mín·F_dis/p_alivio; F_dis/p_alarma), con alarma = 0,85·alivio.")
H("7.6 Retorno, ciclo y sensibilidad", 2)
table(["Magnitud", "Valor"], [
    ["Fuerza de retorno disponible (puerto B)", f"{n(DV['Fret'], unit='kN')} (A_anular {pint(DV['Aann'])} mm² × {pint(P['p_ret'])} bar)"],
    ["Tiempo por ciclo / por vuelta", f"{n(DV['tCycle'], unit='min')} / {n(DV['tRev'], unit='min')} (bomba {n(P['Q_pump'])} L/min)"],
], widths=(70, 100))
sc = D["escenarios"]
T("FS al calado en función de μ y del radio de fricción:", size=9, after=1)
table(["μ"] + [f"{a} = {n(b)} mm" for a, b in sc["rs"]],
      [[n(row[0]["mu"])] + [n(c["FS"]) for c in row] for row in sc["grid"]], widths=(20, 45, 45, 45), num_cols=(1, 2, 3))
table(["W (tf)", "FS diseño", "p diseño (bar)", "μ máx (r_ef)"],
      [[n(l["W"]), n(l["FS"]), n(l["p"]), n(l["muMax"])] for l in sc["loads"]], widths=(30, 30, 35, 35), num_cols=(0, 1, 2, 3))

# ================================================================= 8. VERIFICACIONES (horizontal)
ls = doc.add_section()
ls.orientation = WD_ORIENT.LANDSCAPE; ls.page_width, ls.page_height = Mm(297), Mm(210)
ls.left_margin = ls.right_margin = Mm(15); ls.top_margin = Mm(18); ls.bottom_margin = Mm(15)
header_footer(ls)
H("8. Verificaciones")
T("Desarrollo: cada fila indica la fórmula aplicada, la demanda, la capacidad y la referencia normativa. FU = demanda/capacidad "
  "(o su inversa cuando el criterio es de mínimo). Las filas \"Info\" son valores informativos sin criterio de aceptación.", size=9)
INTRO = {
    "Giro": "Hipótesis: casos de fricción de 4.3; cinemática de 7.2. Incluye geometría (holguras e interferencias) del accionamiento.",
    "Patín y guía": "Hipótesis: fuerza de calado; reacciones de guía por el par F·Δ; ASME BTH-1 Cat. B.",
    "Uña": "Hipótesis: uña en voladizo desde la boca del patín, fuerza de calado.",
    "Articulaciones": "Hipótesis: pasadores de ojal en doble corte, mejillas y orejas de ménsula; fuerza de calado; ASME BTH-1 Cat. B.",
    "Pasadores de empuje": "Hipótesis: pasador biempotrado en los anillos de la mesa, carga en la altura de la uña; fuerza de calado.",
    "Mesa": "Hipótesis: carga de diseño N_D sobre parrilla Ø{0}; flexión global axisimétrica de la sección sándwich.".format(pint(P["D_load"])),
    "Mesa (FEA)": f"Hipótesis: sector de mesa con placas MITC4; tensiones locales × k = {n(P['kFEA'])}.",
    "Interfaz": "Hipótesis: distribución lineal de presiones (capítulo 6).",
    "Pivote": "Hipótesis: empuje horizontal por excentricidad (capítulo 6).",
    "Base": f"Hipótesis: izaje en 4 puntos con φ = {n(P['phi_lift'])}; FEA de placa de un cuarto de base.",
    "Soldaduras": "Hipótesis: filetes de la mesa con AISC J2.4 (Ω = 2,00); soldaduras de la cadena de empuje con BTH-1.",
    "Fatiga": f"Hipótesis: {pint(P['turns_yr'])} vueltas/año × {pint(P['life'])} años; AISC 360-22 Apéndice 3.",
}
order = []
for v in VER:
    if v["grp"] not in order: order.append(v["grp"])
k = 0
for gi, g in enumerate(order, 1):
    H(f"8.{gi} {g}", 2)
    if g in INTRO: T(INTRO[g], italic=True, size=8.5)
    rows = []
    for v in [x for x in VER if x["grp"] == g]:
        k += 1
        info = v["estado"] == "info"
        rows.append([str(k), v["nombre"], v["formula"], n(v["dem"]), "—" if v.get("cap") is None else n(v["cap"]), v["unidad"],
                     "—" if info or v.get("fu") is None else n(v["fu"]), EST.get(v["estado"], v["estado"]), v["ref"]])
    table(["N°", "Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"], rows,
          widths=(8, 52, 70, 17, 17, 13, 14, 18, 58), size=7, num_cols=(3, 4, 6))

# ================================================================= 9. RESUMEN
ps = doc.add_section()
ps.orientation = WD_ORIENT.PORTRAIT; ps.page_width, ps.page_height = Mm(210), Mm(297)
ps.left_margin = ps.right_margin = Mm(20); ps.top_margin = Mm(20); ps.bottom_margin = Mm(18)
header_footer(ps)
H("9. Resumen de resultados")
vd = D["verdict"]
cnt = {s: sum(1 for v in VER if v["estado"] == s) for s in EST}
table(["Resultado", "Valor"], [
    ["¿Gira?", "Sí" if vd["gira"] else "NO"], ["¿Estructura verifica?", "Sí" if vd["estructura"] else "NO"],
    ["Utilización máxima", n(vd["fuMax"])], ["FS del accionamiento (diseño)", n(cd["FS"])], ["Presión de diseño", n(cd["p"], unit="bar")],
    ["Masa total", n(m["total"], 4, "kg")],
    ["Verificaciones", f"{len(VER)}: {cnt['ok']} cumplen, {cnt['warn']} advertencias, {cnt['fail']} no cumplen, {cnt['info']} informativas, {cnt['pend']} pendientes"],
], widths=(70, 100))
T("Verificaciones que gobiernan (mayor FU):", bold=True, size=9.5)
gov = sorted([v for v in VER if v["estado"] not in ("info",) and v.get("fu") is not None], key=lambda v: -v["fu"])[:12]
table(["Verificación", "Grupo", "FU", "Referencia"], [[v["nombre"], v["grp"], n(v["fu"]), v["ref"]] for v in gov],
      widths=(72, 25, 13, 60), size=8, num_cols=(2,))
T("Las verificaciones geométricas con FU = 1,00 incluyen su holgura constructiva (10 a 15 mm) y no admiten desviaciones de fabricación mayores; "
  "están controladas por las tolerancias de los planos F-01 a F-04.", size=9)
H("Conclusión", 2)
T(("Con los parámetros indicados la tornamesa TT300-C gira la carga de {0} tf en el caso de diseño con FS = {1} y todas las verificaciones estructurales "
   "y geométricas cumplen (utilización máxima {2}).").format(pint(P["W_tf"]), n(cd["FS"]), n(vd["fuMax"])) if vd["gira"] and vd["estructura"] else
  "ATENCIÓN: la configuración actual no cumple todas las verificaciones; ver capítulo 8.", bold=True)

# ================================================================= 10. PENDIENTES
H("10. Puntos a confirmar antes de fabricar")
table(["N°", "Ítem", "Supuesto en esta memoria", "Responsable"], [
    ["1", "Ficha del cilindro", f"Ø{pint(P['D_bore'])}/Ø{pint(P['d_rod'])} × {pint(P['stroke'])}; L0 {pint(P['L0'])}; e_cuerpo ≥ {pint(P['e_body'])}; c_vástago ≥ {pint(P['c_rod'])}; cuerpo Ø ≤ {pint(P['D_body'])}; {pint(P['m_cyl'])} kg; ojales con rótula", "Proveedor"],
    ["2", "Resorte de retorno de la uña (pos 12)", f"Recorrido ≥ {n(K['travel'] + 5)} mm; 150 a 300 N", "Proveedor"],
    ["3", "Fricción patín–guía", f"μ_g = {n(P['mu_g'])} con grasa grafitada", "Ensayo de aceptación (F-04)"],
    ["4", "Numeración de artículos de ASME BTH-1", "§3-2, §3-3, §3-4 de la edición vigente", "Revisor"],
    ["5", "Tamaño mínimo de filete", "AWS D1.1/D1.1M:2020, tabla de tamaño mínimo", "Revisor"],
    ["6", "Puntos de izaje soldables (1d)", "Comerciales certificados, WLL ≥ 1,6 t c/u", "Proveedor"],
    ["7", "Losa o mats de apoyo", f"q ≈ {n(DV['q_max'], unit='MPa')}", "Tercero"],
    ["8", "Artículo de ISO 4413:2010 (sobrepresión)", "Criterio confirmado; numeral por citar", "Revisor"],
    ["9", "Guía de retorno tipo KIET", "No adoptada; evaluar con fotos del equipo existente", "Mandante / proyectista"],
], widths=(9, 45, 85, 31), size=8)

# ================================================================= ANEXO A
H("Anexo A. Control de calidad del cálculo")
T("A.1 Revisor cruzado (cálculo independiente dentro de la herramienta)", bold=True, size=9.5)
table(["Control", "Herramienta", "Independiente", "Dif. %", "Tol. %", "Resultado", "Nota"],
      [[c["name"], n(c["tool"], 4), n(c["indep"], 4), n(c["d"]), "—" if c["tol"] is None else n(c["tol"]), "Cumple" if c["ok"] else "NO", c.get("note", "")]
       for c in D["revisionCruzada"]], widths=(55, 20, 20, 13, 12, 15, 35), size=7.5, num_cols=(1, 2, 3, 4))
T("A.2 Otros controles", bold=True, size=9.5)
ctrl = [["Auditoría normativa", "Toda verificación tiene fórmula y referencia" if D["auditoria"]["ok"] else "Faltan referencias: " + ", ".join(D["auditoria"]["missing"])],
        ["Verificador independiente (Python, sin leer el código JS)", "tests/indep_tt300c.py; se ejecuta con npm test"],
        ["Pruebas automáticas", "tests/test_tt300c.js: FEA Navier y voladizo, cinemática, agentes, golden file"]]
if M3:
    ni = len(M3["interferencias"]); nok = sum(1 for x in M3["interferencias"] if x["ok"])
    ctrl.append(["Modelo 3D (CadQuery): interferencias", f"{nok} de {ni} pares sin interferencia"])
    ctrl.append(["Modelo 3D: masas frente al núcleo", f"Diferencia máxima {n(max(abs(r['dif_%']) for r in M3['comparacion']))} %"])
table(["Control", "Resultado"], ctrl, widths=(70, 100), size=8.5)

# ================================================================= salida
name = f"TT300-C_Memoria_Rev{REV}"
docx = OUT / f"{name}.docx"
doc.save(docx)
print(docx)
if "--no-pdf" not in sys.argv:
    r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(docx)], capture_output=True, text=True, timeout=300)
    print(OUT / f"{name}.pdf" if (OUT / f"{name}.pdf").exists() else r.stderr)
