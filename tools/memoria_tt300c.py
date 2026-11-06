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
    ["Herramienta de verificación", "Tornamesa_v1.0.html (misma fuente de datos)"],
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
    ["Patín guiado (pos 16) y bancada (pos 1e)", f"Patín {pint(K['L_s'])} × {pint(P['w_s'])} coaxial con el cilindro en x = ±{pint(P['x_g'])}; lengüeta con cabeza T en ranura T de la bancada "
                                                 f"(cuello {pint(P['w_slot'])} H8 × {pint(P['h_slot'])}, cabeza {pint(P['w_tee'])} × {pint(P['h_tee'])}) que guía y retiene el patín; largo de guía efectivo Lg = {n(K['Lg'])}; marco de boca con paredes de {pint(P['t_fw'])}"],
    ["Uña deslizante (pos 10) y resorte (pos 12)", f"Uña {pint(P['dog_b'])} × {pint(P['dog_h'])} con cara de empuje plana templada; chaflán de retorno a {pint(P['beta_ch'])}° "
                                                   f"({n(DV['chaflan']['dx'])} × {n(DV['chaflan']['dy'])} mm); retorno radial {n(K['travel'])} mm contra resorte; reengancha detrás del pasador siguiente"],
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
    ["Pasadores de empuje (pos 3)", "34CrNiMo6+QT (EN 10083-3); zona de contacto templada por inducción ≥ 55 HRC", pint(P["Fy_pin"])],
    ["Uña (pos 10)", "34CrNiMo6+QT, certificado 3.1; cara de empuje templada por inducción ≥ 55 HRC", pint(P["Fy_dog"])],
    ["Superficies de contacto uña–pasador", "Temple por inducción", pint(P["Fy_surf"])],
    ["Patín (pos 16)", "S460 o 34CrNiMo6+QT", pint(P["Fy_shoe"])],
    ["Pasadores de articulación (pos 11)", "42CrMo4+QT", pint(P["Fy_pp"])],
    ["Pivote (pos 5)", "42CrMo4+QT", pint(P["Fy_piv"])],
    ["Soldadura", f"E70 (FEXX = {pint(P['FEXX'])} MPa)", "—"],
], widths=(80, 60, 30))
T(f"E = {pint(P['E'])} MPa; ν = {n(P['nu'])}. Factor de malla FEA k = {n(P['kFEA'])} aplicado a las tensiones locales.")
H("4.3 Fricción en la interfaz de giro", 2)
MU = D["apoyo"]["mu"]
OPT = D["apoyo"]["interfaz"]["o"]
T("Interfaz verificada: " + ["acero–acero con grasa grafitada (base)", "opción A: dos discos de acero inoxidable con grasa entre sí",
  "opción B: dos discos de acero inoxidable con lámina de UHMW entre ellos"][OPT] + ". Las tres alternativas se comparan en 6.1.", size=9)
table(["Caso", "μ", "Radio de fricción", "Justificación"], [
    ["Nominal (grasa limpia)", n(MU["nom"]), f"r_u = {n(D['apoyo']['r_u'])} mm (presión uniforme)", "Valor esperado de operación"],
    ["Diseño", n(MU["d"]), f"r_ef = {pint(P['r_ef'])} mm", "Límite superior con excentricidad"],
    ["Contacto en el borde", n(MU["d"]), f"R = {pint(D['apoyo']['Ro'])} mm", "Mesa apoyada solo en el borde (revisión M1)"],
    ["Contaminado", n(MU["cont"]), f"r_ef = {pint(P['r_ef'])} mm", "Arena o película degradada"],
    ["Seco (referencial)", n(MU["dry"]), f"r_u = {n(D['apoyo']['r_u'])} mm", "No es condición de operación"],
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
    M3m = M3["masas"]
    T(f"Control: las masas se recalculan sobre el modelo 3D (CadQuery). Diferencia 3D frente al núcleo (masa comparable {n(M3m['total_nucleo'])} kg): {n(M3m['dif_pct'])} % (tolerancia {n(M3m['tol_pct'])} %). "
      f"Masa del ensamble con piezas fuera del núcleo (pernos, buje, tapas, pasadores): {n(M3['masa_total_ensamble'])} kg.", size=9)

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

# ---- 6.1 alternativas de interfaz inoxidable
IF = D["escenarios"]["ifaces"]
H("6.1 Alternativas de interfaz: discos de acero inoxidable (A), con lámina de UHMW (B) y placa de bronce con grafito (C)", 2)
T("Mantenimiento. La fijación por defecto es DESMONTABLE: cada disco o placa de bronce va en {0} sectores retenidos por topes soldados al respaldo y asegurados con tornillos avellanados de posición; con la mesa izada (4 cáncamos M30) los sectores se sacan a mano (cada uno < 25 kg), lo que permite limpiar, engrasar y cambiar piezas. Las ranuras de engrase ({1} radiales y {2} circunferenciales, {3} de profundidad) van en el disco de la mesa (A) o en el bronce (C) y se alimentan por {4} graseras M10×1 del borde. La fijación permanente por pegado no es desmontable y queda solo como alternativa (parámetro de fijación = 2).".format(pint(P["n_sec"]), pint(P["n_gr_rad"]), pint(P["n_gr_circ"]), n(P["h_gr"], unit="mm"), pint(P["n_greaser"])), size=9)
T("Hipótesis. Dos discos anulares de acero inoxidable (R_i = {0} a R_o = {1} mm) se interponen entre la plancha base y la plancha inferior de la mesa: "
  "uno fijo a la base y otro a la mesa, apoyados sobre sus planchas de respaldo. En A deslizan entre sí con grasa; en B se agrega una lámina de UHMW fijada al disco de la base, "
  "que desliza sobre el disco de la mesa. La interfaz no se oxida y se lubrica con facilidad. Los discos y la lámina no cumplen función estructural: transmiten la presión de contacto "
  "q_máx = {2} a la plancha de respaldo. La mesa y la base conservan sus espesores.".format(n(D["apoyo"]["Ri"]), pint(D["apoyo"]["Ro"]), n(IF[1]["q"], unit="MPa")), size=9)
table(["Dato", "Valor", "Fuente"], [
    ["Fy del inoxidable", n(P["Fy_ss"], unit="MPa"), "ASTM A240, tipo 304 recocido (316L: 170 MPa)"],
    ["Ø del vacío local supuesto bajo el disco", n(P["ss_void"], unit="mm"), "Hipótesis de diseño (pérdida de contacto con el respaldo por polvo, soldadura o alabeo)"],
    ["Sobreespesor por desgaste y relapeado", n(P["ss_allow"], unit="mm"), "Hipótesis de diseño"],
    ["Espesor mínimo constructivo del disco", n(P["ss_tmin"], unit="mm"), "Avellanado de fijaciones y rectificado de la cara"],
    ["UHMW: presión admisible sostenida", n(P["p_uhmw"], unit="MPa"), "≈ ¼ del esfuerzo a 10 % de deformación (≈ 21 MPa); datos de catálogo"],
    ["UHMW: módulo aparente con fluencia (1.000 h)", n(P["E_uhmw"], unit="MPa"), "Datos de catálogo del proveedor"],
    ["Variación del hueco entre las dos caras de la lámina", n(P["d_flat"], unit="mm") + f" en una ventana de Ø{pint(P['ss_void'])}", "Requisito de fabricación: suma de las planitudes de discos y respaldos y de la tolerancia de espesor de la lámina; rectificar y medir en obra. ν del UHMW = 0,45 (con 0,42 el módulo confinado baja ≈ 15 %)"],
    ["μ de diseño: A / B", f"{n(P['muA_d'])} / {n(P['muB_d'])}", "Hipótesis; B sin película de grasa tras reposo bajo carga; confirmar con ensayo"],
    ["μ respaldo / pegado estructural (solo en la fijación permanente, no desmontable)", f"{n(P['mu_back'])} / {n(P['tau_bond'], unit='MPa')}", "Clase A de AISC (superficie limpia); adhesivo epóxico estructural de diseño al corte (≈ 3 % de su resistencia). La capacidad es la mayor de las dos, no su suma"],
    ["Adhesivo: G, espesor de línea, cortante cíclico admisible", f"{n(P['G_ad'], unit='MPa')} / {n(P['t_ad'], unit='mm')} / {n(P['tau_cyc'], unit='MPa')}", "Epóxico tenaz con línea ≥ 1 mm; el rígido (G ≈ 1.000) da un cortante térmico de borde de 7 a 14 MPa; ensayo de arrancamiento y de fatiga térmica"],
], widths=(65, 30, 75), size=8)
T("Desarrollo.", bold=True, size=9.5, after=1)
table(["Ecuación", "Expresión", "Referencia"], [
    ["Disco inoxidable: flexión sobre un vacío local (placa circular empotrada, carga uniforme)", "σ = 3·q·a²/(4·t²) ≤ 0,6·Fy   →   t_flex = a·√(0,75·q/(0,6·Fy)), a = Ø_vacío/2", "Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells §16; 0,6Fy: AISC 360-22 F11 (criterio del proyecto)"],
    ["Espesor requerido del disco", "t_req = máx(t_flex + sobreespesor; t_mín constructivo); espesor comercial ≥ t_req", "ASTM A240 (planchas 3, 4, 5, 6, 8, 10, 12, 15, 20, 25 mm)"],
    ["Lámina UHMW: conformidad con la planitud", "t ≥ E_c(S)·δ/(p_adm − q_máx): la sobrepresión local E_c·δ/t se suma a q_máx y no debe pasar de p_adm. E_c = E[1 + (M/E − 1)·S²/(1 + S²)], S = D/(4t), M = E(1−ν)/((1+ν)(1−2ν)), ν = 0,45", "Hipótesis de diseño; datos de catálogo del UHMW; módulo de láminas delgadas (factor de forma)"],
    ["Lámina UHMW: PV y desgaste", "PV = q_máx·v ≤ PV_adm; h = k·q·s ≤ 0,20·t", "Proveedor de UHMW-PE (ASTM D4020)"],
    ["Dilatación diferencial", "σ = E·(α_inox − α_acero)·ΔT; Δr = (α − α_acero)·ΔT·R; junta UHMW = (α_UHMW − α_acero)·ΔT·cuerda", "α: inox 17,3; acero 11,7; UHMW 180 (×10⁻⁶/K)"],
    ["Fijación desmontable (por defecto): topes soldados al respaldo", "F_tope = (T_calado/r_u)/n·(q_máx/q_med); σ = F_tope/(L_tope·t) ≤ 1,25·Fy/Nd; soldadura f = F_tope/(2·0,707·w·L_tope) ≤ 0,60FEXX/(1,20Nd); L_tope = máx(aplastamiento; soldadura)/0,9. Los tornillos avellanados (ISO 10642) solo dan posición. Alternativa permanente: T_calado ≤ máx(μ_respaldo·N·r_u; τ_adhesivo·A·r_u)", "ASME BTH-1 §3-3.3 y §3-3.4 (Nd del proyecto); Equilibrio"],
], widths=(48, 72, 50), size=8)
T("Resultado.", bold=True, size=9.5, after=1)
table(["Alternativa", "Disco inox o duro: t_flex / t_req → adoptado (mm)", "UHMW: t_req → adoptado (mm)", "Bronce: t_flex / t_req → adoptado (mm)", "Altura agregada (mm)", "Δ masa total (kg)", "Masa total (kg)", "μ diseño", "F por cilindro (kN)", "p diseño (bar)", "FS diseño"],
      [[r["name"], "—" if r["k"] == 0 else f"{n(r['tFlex'])} / {n(r['tssReq'])} → {n(r['tss'])}" + ("" if (r['tss2'] == r['tss'] and r['tss2Req'] == r['tssReq']) else f" · mesa {n(r['tss2Req'])} → {n(r['tss2'])}"), "—" if r["k"] != 2 else f"{n(r['tuhReq'])} → {n(r['tuh'])}", "—" if r["k"] != 3 else f"{n(r['tFlexB'])} / {n(r['tbzReq'])} → {n(r['tbz'])}",
        "—" if r["k"] == 0 else n(r["delta"]), "—" if r["k"] == 0 else "+" + n(r["dTot"]), n(r["mass"]), n(r["mu_d"]), n(r["F"]), n(r["p"]), n(r["FS"])] for r in IF],
      widths=(30, 22, 16, 22, 12, 12, 12, 10, 12, 11, 11), size=6.5, num_cols=tuple(range(4, 11)))
def ifrows(L, only=None):
    out = []
    for c in L:
        if only and not any(k in c["nombre"] for k in only): continue
        info = c["estado"] == "info"
        out.append([c["nombre"], c["formula"], n(c["dem"]), "—" if c.get("cap") is None else n(c["cap"]), c["unidad"], "—" if info or c.get("fu") is None else n(c["fu"]), EST.get(c["estado"], c["estado"]), c["ref"]])
    return out
T("Verificaciones de la opción A (los discos de la opción B tienen las mismas, con q levemente mayor por el peso del disco y la lámina):", size=9, after=1)
table(["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"], ifrows(D["interfazChecks"]["A"]),
      widths=(38, 42, 12, 12, 10, 12, 13, 31), size=6.5, num_cols=(2, 3, 5))
T("Verificaciones adicionales de la opción B (lámina de UHMW):", size=9, after=1)
table(["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"], ifrows(D["interfazChecks"]["B"], ("UHMW", "Masa agregada", "Altura")),
      widths=(38, 42, 12, 12, 10, 12, 13, 31), size=6.5, num_cols=(2, 3, 5))
T("Opción C. La placa de bronce con tapones de grafito va fija a la base y desliza contra un disco duro (≥ 100 HB sobre el bronce) fijo a la mesa; el desgaste queda en el bronce, que se reemplaza. "
  "Espesor: t_flex = a·√(0,75q_loc/(0,6Fy_bz)); t_req = t_flex/√η + sobreespesor, con η = (p − d)/p = {0} por los tapones de grafito (f_g = {1} del área). "
  "Verificaciones de C a continuación; la configuración 3 (pastillas) cubre {2} del área y concentra la presión local en 1/cobertura.".format(
      n(D["interfazChecks"]["C"] and IF[3]["tbz"] and (P["bz_plug_p"] - P["bz_plug_d"]) / P["bz_plug_p"]), n(math.pi * P["bz_plug_d"] ** 2 / (2 * math.sqrt(3) * P["bz_plug_p"] ** 2)), n(P["bz_cover"])), size=9)
T("Verificaciones de la opción C (bronce con tapones de grafito):", size=9, after=1)
table(["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"], ifrows(D["interfazChecks"]["C"]),
      widths=(38, 42, 12, 12, 10, 12, 13, 31), size=6.5, num_cols=(2, 3, 5))
T("Conclusión. Con los datos de entrada, cada disco inoxidable debe tener {0} (requerido {1}; espesor comercial inmediato) y la lámina de UHMW de la opción B {2} (requerido {3}). "
  "La opción A agrega {4} de masa total y {5} de altura; la B, {6} y {7}. Con los μ de diseño adoptados la fuerza por cilindro es {8} (A) y {9} (B), frente a {10} con acero–acero: "
  "la ventaja de B aparece en la operación normal (μ nominal {11} frente a {12}) y en la protección contra la corrosión y el gripado, no en el caso de diseño, que supone la película de grasa expulsada.".format(
      n(IF[1]["tss"], unit="mm"), n(IF[1]["tssReq"], unit="mm"), n(IF[2]["tuh"], unit="mm"), n(IF[2]["tuhReq"], unit="mm"),
      n(IF[1]["dTot"], unit="kg"), n(IF[1]["delta"], unit="mm"), n(IF[2]["dTot"], unit="kg"), n(IF[2]["delta"], unit="mm"),
      n(IF[1]["F"], unit="kN"), n(IF[2]["F"], unit="kN"), n(IF[0]["F"], unit="kN"), n(P["muB_nom"]), n(P["mu_nom"])), bold=True, size=9)

# ---- 6.2 cubierta de madera dura y altura
CUB = D["cubierta"]
H("6.2 Cubierta de madera dura y altura total", 2)
T("Hipótesis. Una cubierta de tablones de madera dura (e = {0}, ρ = {1}) sobre la plancha superior de la mesa protege la plancha y da un apoyo antideslizante a la carga, como en los equipos comerciales. "
  "No se acredita reparto de la carga sobre la plancha (criterio conservador: las verificaciones de la mesa no cambian); la cubierta gira con la mesa, suma su peso a la presión de contacto y sube la altura total. "
  "Los resultados se muestran con la cubierta activada aunque la opción esté apagada en este diseño.".format(n(P["t_wood"], unit="mm"), n(P["rho_wood"], unit="kg/m³")), size=9)
table(["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado"],
      [[c["nombre"], c["formula"], n(c["dem"]), "—" if c.get("cap") is None else n(c["cap"]), c["unidad"], "—" if c.get("fu") is None else n(c["fu"]), EST.get(c["estado"], c["estado"])] for c in CUB["checks"]],
      widths=(52, 55, 14, 14, 11, 12, 12), size=7, num_cols=(2, 3, 5))
T(f"Resultado: la cubierta de {n(P['t_wood'], unit='mm')} agrega {n(CUB['mWood'], unit='kg')} (+{n(CUB['dMasa'], unit='kg')} de masa total con el efecto sobre la interfaz) y {n(P['t_wood'], unit='mm')} de altura. "
  "La presión de aplastamiento perpendicular a la fibra queda muy bajo la admisible; la madera se atornilla con tornillos avellanados y se deja desmontable sobre la tapa de inspección.", size=9)

# ================================================================= 7. ACCIONAMIENTO
H("7. Accionamiento")
H("7.1 Par resistente", 2)
T("T(μ, r) = μ·N·r + T_piv(μ)   [equilibrio de momentos respecto del eje del pivote]")
H("7.2 Cinemática y equilibrio del accionamiento guiado", 2)
table(["Magnitud", "Expresión", "Valor"], [
    ["Paso angular", "2π/N_pas", n(360 / P["N_pin"], unit="°")],
    ["Brazo mínimo (toma del pasador)", "a_mín = R_pas·cos(π/N)", n(K["armMin"], unit="mm")],
    ["Cuerda entre pasadores", "c = 2R_pas·sin(π/N)", n(K["chord"], unit="mm")],
    ["Carrera requerida", "s_req = s_libre + c", n(K["s_req"], unit="mm")],
    ["Margen de carrera", "carrera − s_req", n(K["margin"], unit="mm")],
    ["Excentricidad máxima eje cilindro–pasador", "Δ = x_g − a_mín", n(K["DeltaMax"], unit="mm")],
    ["Largo del patín / largo efectivo de guía", "L_patín = l_p + 20 + f_ext + 1,25·d_pp; Lg = ⅔·L_patín", f"{n(K['L_s'])} / {n(K['Lg'])} mm"],
    ["μ guía / μ cara de la uña–pasador", "μ_g / μ_s", f"{n(P['mu_g'])} / {n(P['mu_s'])}"],
    ["Factor equivalente (máximo en la carrera)", "K = F_cil·n·a_mín/T", n(DV["Kguide"], 4)],
], widths=(65, 65, 40))
T("Hipótesis: la uña empuja con una cara plana normal a la guía (eje y). El pasador, fijo a la mesa, desliza sobre la cara: su punto de contacto (x_c, y_c) = "
  "(R cos θ, R sin θ − r) se mueve en x con velocidad ω·(r − y_p), por lo que la fricción H = s·μ_s·F_pas cambia de sentido en y_p = r (θ = asin(r/R)); "
  "en ese punto se evalúan ambos sentidos.", size=9)
table(["Ecuación", "Expresión"], [
    ["Momento sobre la mesa (por cilindro)", "x_c·F_pas − y_c·H = T/n   →   F_pas = (T/n)/(x_c − s·μ_s·y_c)"],
    ["Momento del patín respecto de la reacción trasera", "R_f = [F_pas·(x_g − x_c) + H·(y_c − y_r)]/Lg"],
    ["Fuerzas en x sobre el patín", "R_r = H − R_f"],
    ["Fuerzas en y (fricción de guía)", "F_cil·η_c = F_pas + μ_g·(|R_f| + |R_r|)"],
    ["Fuerza de diseño", "F_dis = máx F_cil(θ) en la carrera"],
    ["Verificación de las piezas de la guía", f"R_guía = máx(|R_f|, |R_r|) a calado = {n(DV['Rguide'], unit='kN')}"],
], widths=(70, 100), size=8.5)
T("El resultado se contrasta en el Anexo A por potencia virtual (F_cil·η·v = T/n·ω + μ_g·Σ|R|·v + μ_s·F_pas·|v_desliz|) con resolución "
  "numérica independiente del equilibrio, y en el verificador independiente en Python.", size=9)
H("7.3 Casos de fricción (por cilindro, brazo mínimo)", 2)
table(["Caso", "μ", "r (mm)", "T (kN·m)", "F_cil (kN)", "p (bar)", "FS al calado", "¿Gira?"],
      [[c["nombre"], n(c["mu"]), n(c["r"]), n(c["T"]), n(c["F"]), n(c["p"]), n(c["FS"]), "Sí" if c["gira"] else "NO"] for c in DV["casos"]],
      widths=(52, 12, 16, 18, 18, 16, 20, 14), size=8, num_cols=(1, 2, 3, 4, 5, 6))
T(f"Resultado: en el caso de diseño F_cil = {n(cd['F'], unit='kN')} a {n(cd['p'], unit='bar')}; FS = F_calado/F_dis = {n(cd['FS'])} ≥ FS_mín = {n(P['FS_min'])}. "
  f"μ máximo que gira con r_ef: {n(DV['muMax_ref'])}.", bold=True)
H("7.4 Fuerzas a lo largo de la carrera (caso de diseño)", 2)
table(["Posición", "θ (°)", "s (mm)", "F_cil (kN)", "p (bar)", "F_pas (kN)", "H (kN)", "Tangencial (kN)", "Radial (kN)", "R_f (kN)", "R_r (kN)"],
      [[c["pos"], n(c["th"]), n(c["s"]), n(c["F"]), n(c["p"]), n(c["Fpin"]), n(c["H"]), n(c["Ft"]), n(c["Fr"]), n(c["Rf"]), n(c["Rr"])] for c in D["carrera"]],
      widths=(34, 11, 13, 15, 13, 15, 13, 17, 14, 13, 13), size=7.5, num_cols=tuple(range(1, 11)))
T("La componente radial va al pivote y se anula en el par simétrico de cilindros; con fricción desigual entre patines (μ_g ± 0,05) queda un empuje neto que se agrega al pivote (capítulo 8). "
  "La fricción de la cara (H) desequilibra las reacciones de guía; las piezas de la guía se verifican con las reacciones a calado.", size=9)
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

H("7.7 Bomba, tiempos, control y capacidad según el número de cilindros", 2)
BM = D["bomba"]
table(["Magnitud", "Valor"], [
    ["Caudal de avance / de retorno", f"{n(P['Q_pump'], unit='L/min')} / {n(BM['Qr'], unit='L/min')}"],
    ["Tiempo de avance / de retorno por ciclo", f"{n(BM['tExt'], unit='min')} / {n(BM['tRet'], unit='min')}"],
    ["Velocidad del vástago: avance / retorno", f"{n(BM['vExt'] * 1000, unit='mm/s')} / {n(BM['vRet'] * 1000, unit='mm/s')} (máx. de retorno {n(P['v_ret_max'], unit='m/s')})"],
    ["Potencia hidráulica: avance / retorno", f"{n(BM['PhExt'], unit='kW')} / {n(BM['PhRet'], unit='kW')}"],
    ["Potencia del motor (η = {0})".format(n(P["eta_pump"])), n(BM["Pmotor"], unit="kW")],
], widths=(75, 95))
T("Tiempo por vuelta según el caudal (28 ciclos; el retorno rápido usa una bomba de dos etapas o una válvula de alto caudal):", size=9, after=1)
table(["Caudal de avance (L/min)", "Caudal de retorno (L/min)", "Tiempo por ciclo (min)", "Tiempo por vuelta (min)", "Potencia del motor (kW)", "Velocidad de retorno (mm/s)"],
      [[n(b["Q"]), n(b["Qr"]), n(b["tCycle"]), n(b["tRev"]), n(b["Pmotor"]), n(b["vRet"] * 1000)] for b in D["bombaBarrido"]], widths=(30, 30, 28, 28, 28, 26), size=8, num_cols=(0, 1, 2, 3, 4, 5))
T("Umbrales de presión para el control (calculados por cilindro):", size=9, after=1)
table(["Condición", "p (bar)"], [["Gira con μ nominal (esperada en operación)", n(casos["nom"]["p"])], ["Gira con μ de diseño", n(casos["dis"]["p"])], ["Gira contaminado", n(casos["cont"]["p"])],
      ["Alarma y detención automática", n(P["p_alarm"])], ["Válvula de alivio (calado)", n(P["p_relief"])]], widths=(110, 40), num_cols=(1,))
T("Sistema de control: transductor de presión en el puerto A con registro por ciclo y detención a la presión de alarma; válvulas de bloqueo en ambos cilindros; mando remoto con parada de emergencia; "
  f"encoder de ángulo (un paso = {n(360 / P['N_pin'])}°, resolución ≤ 0,1°); conteo de carreras. La presión de despegue medida permite calcular el μ real (ensayo de aceptación, lámina F-04).", size=9)
T("Capacidad según el número de cilindros (la menor entre el giro, con μ de diseño y FS mínimo, y el pivote):", size=9, after=1)
table(["Cilindros", "W máx. giro (tf)", "W máx. por pivote (tf)", "Capacidad adoptada (tf)", "W que gira con FS = 1 y μ nominal (tf)"],
      [[pint(c["n"]), n(c["wGiro"]), n(c["wPiv"]), n(c["wCap"]), n(c["wNom"])] for c in D["capCil"]], widths=(25, 35, 40, 40, 40), size=8, num_cols=(0, 1, 2, 3, 4))
T("Con un número impar de cilindros el empuje no es un par puro: el pivote reacciona con la fuerza tangencial del pasador y limita la capacidad (la verificación del pivote la incluye).", size=9)

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
    ["2", "Resorte de retorno de la uña (pos 12)", f"Recorrido ≥ {n(K['travel'] + 5)} mm; largo comprimido + tope ≤ {pint(P['s_sp'])} mm; 150 a 300 N", "Proveedor"],
    ["3", "Fricción patín–guía y cara de la uña", f"μ_g = {n(P['mu_g'])}, μ_s = {n(P['mu_s'])}, μ retorno ≤ {n(P['mu_ret'])} con grasa grafitada", "Ensayo de aceptación (F-04)"],
    ["4", "Numeración de artículos de ASME BTH-1", "§3-2, §3-3, §3-4 de la edición vigente", "Revisor"],
    ["5", "Tamaño mínimo de filete", "AWS D1.1/D1.1M:2020, tabla de tamaño mínimo", "Revisor"],
    ["6", "Puntos de izaje soldables (1d)", "Comerciales certificados, WLL ≥ 1,6 t c/u", "Proveedor"],
    ["7", "Losa o mats de apoyo", f"q ≈ {n(DV['q_max'], unit='MPa')}", "Tercero"],
    ["8", "Artículo de ISO 4413:2010 (sobrepresión)", "Criterio confirmado; numeral por citar", "Revisor"],
    ["9", "Guía de retorno tipo KIET", "No adoptada; evaluar con fotos del equipo existente", "Mandante / proyectista"],
    ["13", "Interfaz con placa de bronce y grafito (C), si se adopta", f"Aleación (C95400, Fy {pint(P['Fy_bz'])} MPa), p_adm {pint(P['p_bz'])} MPa, PV, desgaste y μ de catálogo; ensayo de arranque (stick-slip); disco duro (≥ 100 HB sobre el bronce, Ra ≤ 0,4 µm); fijación desmontable por sectores con topes (verificada) y ranuras de engrase; par galvánico y sellado; aún no dibujada", "Proveedor / proyectista"],
    ["12", "Interfaz inoxidable (A) o con UHMW (B), si se adopta", "μ, p_adm y E_ap del UHMW son datos de catálogo; par inox–inox de aleaciones distintas o tratada contra el gripado; fijación y retención de los discos; sectores de UHMW con juntas de dilatación; no dibujada aún en planos ni en el 3D; discos pegados con epóxico estructural y respaldo granallado sin pintura; respaldo canteado ≤ 3 mm en el borde; tornillos avellanados M6; sellado perimetral; retención de los sectores de UHMW por rebaje o cola de milano; fluencia de la lámina (asentamiento 0,1 a 0,2 mm)", "Proveedor / proyectista"],
    ["10", "Certificados de material", f"Uña Re ≥ {pint(P['Fy_dog'])} MPa; pasadores Re ≥ {pint(P['Fy_pin'])} MPa; patín Fy ≥ {pint(P['Fy_shoe'])} MPa (3.1)", "Proveedor"],
    ["11", "Temple por inducción de caras de contacto", f"≥ 55 HRC (σy ≥ {pint(P['Fy_surf'])} MPa), profundidad según capítulo 8", "Proveedor / inspección"],
], widths=(9, 45, 85, 31), size=8)

# ================================================================= 11. MERCADO
MK = D["mercado"]
H("11. Comparación con equipos comerciales")
T("Referencias: fichas y planos públicos de los fabricantes. El brazo de la fuerza y el radio de fricción de los equipos comerciales son estimaciones; el μ implícito es la fricción que el equipo vence al límite del alivio, "
  "sin factor de seguridad (μ = n·F·a/(N·r_u)).", size=9)
rows = []
for r in [MK["ours"]] + MK["refs"]:
    rows.append([r["name"], n(r["capKN"]) if r.get("capKN") else "—", n(r["mass"]) if r.get("mass") else "—", n(r["massPerKN"], 3) if r.get("massPerKN") else "—", n(r["h"]) if r.get("h") else "—",
                 n(r["D"]) if r.get("D") else "—", pint(r["nCyl"]) if r.get("nCyl") else "—", n(r["Fcyl"]) if r.get("Fcyl") else "—", n(r["FcylPerTon"], 3) if r.get("FcylPerTon") else "—",
                 n(r["muImpl"], 3) if r.get("muImpl") else "—", n(r["rot"]) if r.get("rot") else "—"])
table(["Equipo", "Capac. (kN)", "Masa (kg)", "kg por kN", "Altura (mm)", "Ø (mm)", "Cil.", "F cil. (kN)", "kN cil. por tf", "μ implícito", "Giro por carrera (°)"], rows,
      widths=(36, 14, 13, 12, 12, 12, 8, 13, 14, 13, 14), size=6.5, num_cols=tuple(range(1, 11)))
CAP = MK["capacity"]
table(["Capacidad de giro del TT300-C", "W (tf)"], [
    [f"FS ≥ {n(P['FS_min'])} con μ de diseño y r_ef (criterio de este proyecto)", n(CAP["design"])],
    ["FS = 1 con μ de diseño", n(CAP["designFS1"])],
    ["FS = 1 con μ nominal y r_u (rotulado tipo comercial)", n(CAP["nominal"])]], widths=(135, 35), num_cols=(1,))
T("Lectura. Los equipos comerciales rotulan su capacidad con una fricción implícita de 0,15 a 0,26 y sin margen; este diseño exige FS ≥ 1,25 con μ de 0,20 y verifica la cadena de empuje a la fuerza de calado con BTH-1 Categoría B. "
  "La capacidad estructural es la de la carga de diseño (300 tf); la de giro es una cota de los cilindros.", size=9)
H("Fuentes", 3)
bullets(["Enerpac, ETT-Series Hydraulic Turntables, ficha técnica (EN-GB): https://assets.partbase.com/supplier-docs/enerpac/ETT-Series_Hydraulic_Turntables_EN-GB.pdf",
         "KIET: plano de conjunto KIET-1024-REF-TT-400T y manual de la bomba (análisis del 30-10-2026, docs/referencias).",
         "Hydra-Slide: texto del video del fabricante (8′ × 8′ × 6″, 250 y 500 ton); sin ficha técnica de masa ni cilindros."])

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
    ctrl.append(["Modelo 3D: masas frente al núcleo", f"Diferencia {n(M3['masas']['dif_pct'])} % (tolerancia {n(M3['masas']['tol_pct'])} %)"])
table(["Control", "Resultado"], ctrl, widths=(70, 100), size=8.5)

# ================================================================= salida
name = f"TT300-C_Memoria_Rev{REV}"
docx = OUT / f"{name}.docx"
doc.save(docx)
print(docx)
if "--no-pdf" not in sys.argv:
    r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(docx)], capture_output=True, text=True, timeout=300)
    print(OUT / f"{name}.pdf" if (OUT / f"{name}.pdf").exists() else r.stderr)
