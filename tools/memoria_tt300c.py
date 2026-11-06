"""Memoria de cálculo TT300-C en Word (.docx) y PDF, generada desde cad/out/TT300-C_design.json.

Fuente única: todos los valores salen del núcleo (tools/export_design.js y tools/export_alternativas.js → TT.analyze, TT.thermal). Este script solo redacta.
Formato: texto negro, hipótesis → desarrollo → resultado, tablas antes que texto, 3 cifras significativas.
Uso (npm run memoria): node tools/export_design.js > cad/out/TT300-C_design.json && node tools/export_alternativas.js > cad/out/TT300-C_alternativas.json && python3 tools/memoria_tt300c.py
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
ALT = json.load(open(OUT / "TT300-C_alternativas.json", encoding="utf-8"))
P, DV, K = D["P"], D["derivados"], D["derivados"]["K"]
REV, DOC = "C", "TT300-C-MC-01"
TOOL = "Tornamesa_v" + (ROOT / "VERSION").read_text(encoding="utf-8").strip() + ".html"   # herramienta principal (versión del archivo VERSION)
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
    if x != 0:
        x = float(f"{x:.{sig - 1}e}")            # redondeo a cifras significativas antes de elegir decimales (0,99999 → 1,00)
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
    ["Planos asociados", "Paquete de planos TT300C-…-B (Rev. B): entregables/RevC/planos; variantes por alternativa en entregables/RevC/variantes"],
    ["Herramienta de verificación", TOOL + " (herramienta principal; misma fuente de datos que esta memoria)"],
    ["Alcance de la revisión", "Alternativas de interfaz (base, A, B, C1, C2, C3 y cubierta de madera) y escenario de exposición solar a 80 °C (capítulos 9 y 10)"],
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
    if ln.startswith("## "):
        break                                    # lo que sigue (sección Temperatura) va en el capítulo 10 y en el Anexo B
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

# ================================================================= 9. ALTERNATIVAS (horizontal)
import re

IDS = ["base", "A", "B", "C1", "C2", "C3", "W"]
AL = {a["id"]: a for a in ALT["alternativas"]}
SHORT = {"base": "Base: acero–acero con grasa", "A": "A: discos inox con grasa", "B": "B: discos inox + lámina UHMW", "C1": "C1: bronce con grafito + disco duro",
         "C2": "C2: dos placas de bronce", "C3": "C3: bronce en pastillas + disco duro", "W": "Madera: base + cubierta con anillo"}
PL = {p["id"]: p for g in D["grupos"] for p in g["p"]}


def plab(pid):
    return PL[pid]["lab"] if pid in PL else pid


def crow(c, conf=False):
    info = c["estado"] == "info"
    r = [c["nombre"], c["formula"], n(c["dem"]), "—" if c.get("cap") is None else n(c["cap"]), c["unidad"],
         "—" if info or c.get("fu") is None else n(c["fu"]), EST.get(c["estado"], c["estado"])]
    if conf:
        r.append(c.get("conf", "—"))
    r.append(c["ref"])
    return r


CH = ["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"]
CW = (48, 78, 16, 16, 17, 11, 17, 64)
CHC = CH[:7] + ["Conf.", "Referencia"]
CWC = (46, 74, 16, 16, 17, 11, 16, 9, 62)


def find(a, key, rx):
    return [c for c in a[key] if re.search(rx, c["nombre"])]


H("9. Alternativas de interfaz de giro y cubierta de madera")
T("Hipótesis. Cada alternativa se evalúa con el mismo núcleo (TT.analyze) y los mismos parámetros del capítulo 4; solo cambia el selector de interfaz: "
  "base (opt_ss = opt_uhmw = opt_bz = 0), A (opt_ss = 1), B (opt_uhmw = 1), C1, C2 y C3 (opt_bz = 1 con bz_conf = 1, 2, 3) y madera (opt_wood = 1 sobre la base). "
  f"En {TOOL} el selector de alternativa de interfaz ejecuta la misma función. Los datos de este capítulo salen de tools/export_alternativas.js; no se copió ninguna cifra a mano.", size=9)
table(["Parámetro común", "Id", "Valor", "Significado"], [
    [plab("hc_min").split(" (")[0], "hc_min", n(P["hc_min"], unit="mm"), "Altura de contacto mínima del tope sobre el canto del sector"],
    [plab("tol_hc").split(" (")[0], "tol_hc", n(P["tol_hc"], unit="mm"), "Corte y rebabas del canto: el aplastamiento se verifica con h_c − tol_hc"],
    [plab("j_sec").split(" (")[0], "j_sec", n(P["j_sec"], unit="mm"), "Junta en frío mínima entre sectores (la dilatación a ΔT de montaje la puede aumentar)"],
    ["Holgura radial de R_i respecto del rebaje del collar", "m_ri", n(P["m_ri"], unit="mm"), "R_i = D_collar/2 + c_boss_r + m_ri"],
    ["Radio de la oreja de izaje / Ø del agujero", "R_ear / d_ear", f"{n(P['R_ear'])} / {n(P['d_ear'])} mm", "Orejas de izaje de la base (AISC 360-22 §D5.2)"],
    ["Anillo de acero de la cubierta de madera", "t_ring", n(P["t_ring"], unit="mm"), "Pletina de borde de alto igual al espesor de los tablones"],
], widths=(70, 28, 30, 139), size=7.5)

H("9.1 Comparación de masa, espesores, presión de contacto, giro y utilización", 2)
T("Desarrollo. Δ masa se mide contra la base (acero–acero); la altura agregada es el espesor que la alternativa suma entre la base y la mesa (en la madera, el espesor de los tablones). "
  "Espesores: requerido por flexión sobre el vacío local (Timoshenko y Woinowsky-Krieger §16, 0,6Fy según AISC 360-22 F11) → comercial adoptado (ASTM A240); lámina UHMW por conformidad con la planitud; bronce por flexión con el ligamento entre tapones. "
  "FU máximo global es el mayor FU de todas las verificaciones; el FU de estructura usa la definición del escenario térmico (resistencia de la estructura; excluye giro y mínimos constructivos) para poder compararlo a 20 y 80 °C.", size=9)


def tr(req, ad):
    return f"{n(req)} → {n(ad)}"


rows = []
for i in IDS:
    a = AL[i]; f = a["interfaz"]
    disc = "—"
    if i in ("A", "B"):
        disc = tr(f["tssReq"], f["tss"]) + ("" if (f["tss2"] == f["tss"] and f["tss2Req"] == f["tssReq"]) else " · mesa " + tr(f["tss2Req"], f["tss2"]))
    elif i.startswith("C"):
        disc = "disco duro " + tr(f["tssReq"], f["tss"])
    rows.append([SHORT[i], n(a["masa"]), "—" if i == "base" else "+" + n(a["dMasa"]), n(P["t_wood"]) if i == "W" else ("—" if i == "base" else n(f["delta"])), disc,
                 tr(f["tuhReq"], f["tuh"]) if i == "B" else "—", tr(f["tbzReq"], f["tbz"]) if i.startswith("C") else "—", n(a["q_max"]), n(a["q_avg"])])
table(["Alternativa", "Masa total (kg)", "Δ masa (kg)", "Altura agregada (mm)", "Discos inox / duro: t_req → adoptado (mm)", "Lámina UHMW: t_req → adoptado (mm)", "Bronce: t_req → adoptado (mm)", "q_máx (MPa)", "q_med (MPa)"],
      rows, widths=(56, 22, 20, 22, 44, 34, 30, 19, 20), size=7.5, num_cols=(1, 2, 3, 7, 8))
rows = []
for i in IDS:
    a = AL[i]; g = a["giro"]; v = a["veredicto"]; c = a["conteo"]; gb = a["gobernante"]; gr = a["gobernante_resistencia"]
    rows.append([SHORT[i], n(g["F"]), n(g["p"]), n(g["FS"]), n(g["mu"]), "Sí" if v["gira"] else "NO", "Sí" if v["estructura"] else "NO", n(v["fuMax"]), gb["nombre"],
                 n(gr["fu"]), gr["nombre"], f"{c['ok']} / {c['warn']} / {c['fail']} / {c['pend']}"])
table(["Alternativa", "F por cilindro (kN)", "p diseño (bar)", "FS giro", "μ diseño", "¿Gira?", "¿Estructura?", "FU máx. global", "Elemento gobernante (global)", "FU estructura", "Gobernante de estructura", "Cumple / adv. / falla / pend."],
      rows, widths=(40, 17, 15, 12, 12, 12, 17, 14, 45, 14, 48, 21), size=7, num_cols=(1, 2, 3, 4, 7, 9))
fs_b, fs_c = AL["base"]["giro"]["FS"], AL["C1"]["giro"]["FS"]
T(f"Resultado: las siete alternativas giran con FS ≥ {n(P['FS_min'])} y verifican la estructura a 20 °C. Contra la base ({n(AL['base']['masa'], unit='kg')}), A agrega {n(AL['A']['dMasa'], unit='kg')}, B {n(AL['B']['dMasa'], unit='kg')}, "
  f"C1 {n(AL['C1']['dMasa'], unit='kg')}, C2 {n(AL['C2']['dMasa'], unit='kg')}, C3 {n(AL['C3']['dMasa'], unit='kg')} y la cubierta de madera con su anillo {n(AL['W']['dMasa'], unit='kg')}. "
  f"El FS de giro sube de {n(fs_b)} (acero–acero) a {n(fs_c)} con bronce grafitado por el menor μ de diseño. "
  "El FU máximo global es 1,00 en todas: lo fijan límites geométricos y de presión (p. ej. alivio igual a la presión nominal del cilindro; filete mínimo igual al adoptado), no la resistencia.", bold=True, size=9)

# ---- 9.2 topes
H("9.2 Topes de los sectores (h_c,mín = 6 mm, tol_hc = 1 mm)", 2)
T("Hipótesis. Cada sector se retiene con un tope: barra soldada al respaldo que apoya sobre el canto del sector. La altura de contacto h_c = t − a_sup − a_inf no baja de h_c,mín y el aplastamiento se verifica con h_c − tol_hc. "
  "El largo del tope es L = máx(aplastamiento; soldadura)/0,9, limitado por el canto radial disponible (R_o − R_i − 100 mm). F_tope = (T_calado/r_u)/n·(q_máx/q_med). ASME BTH-1 §3-3.3 y §3-3.4 (Nd del proyecto), AWS D1.1/D1.1M:2020 para el filete.", size=9)
rows = []
for i in IDS:
    for t in AL[i]["topes"]:
        rows.append([i, t["pieza"], pint(t["n"]), n(t["t"]), n(t["L"]), n(t["Lreq"]), n(t["F"]), n(t["h_c"]), n(t["h_c_min"]), n(t["tol_hc"]), n(t["h_c"] - t["tol_hc"]), n(t["z"]), n(t["h_barra"]), n(t["m_barras"])])
table(["Alt.", "Pieza", "n", "t sector (mm)", "L adoptado (mm)", "L requerido (mm)", "F tope (kN)", "h_c (mm)", "h_c,mín (mm)", "tol_hc (mm)", "h_c − tol_hc (mm)", "z (mm)", "Alto de barra (mm)", "Masa de barras (kg)"],
      rows, widths=(11, 74, 9, 14, 16, 17, 15, 12, 14, 13, 17, 10, 16, 19), size=7, num_cols=tuple(range(2, 14)))
rows = []
for i in ("A", "B", "C1", "C2", "C3"):
    for c in find(AL[i], "topes_checks", r"altura de contacto efectiva|h_c − tol_hc|canto contra el tope"):
        r = crow(c); r[0] = f"[{i}] " + r[0]; rows.append(r)
table(CH, rows, widths=CW, size=6.5, num_cols=(2, 3, 5))
bh = AL["B"]["topes"][1]
T(f"Resultado: todos los topes cumplen con h_c ≥ {n(P['hc_min'])} mm y h_c − tol_hc ≥ {n(P['hc_min'] - P['tol_hc'])} mm; el largo adoptado de los discos es {n(AL['A']['topes'][0]['L'])} mm (requerido {n(AL['A']['topes'][0]['Lreq'])}). "
  f"En la lámina UHMW de B el tope ocupa todo el canto ({n(bh['L'])} mm) y el espesor ({n(bh['t'])} mm) lo fija h_c: la presión admisible del UHMW (5 MPa) manda sobre el acero.", bold=True, size=9)

# ---- 9.3 R_i, collar y cubo
H("9.3 Radio interior R_i, collar del pivote y cubo con holguras", 2)
hb = AL["base"]["hub"]
T(f"Hipótesis. El anillo de contacto de la interfaz empieza en R_i = D_collar/2 + c_boss_r + m_ri = {n(AL['base']['Ri'], unit='mm')} (D_collar = {n(P['D_boss'])} mm, c_boss_r = {n(P['c_boss_r'])} mm, m_ri = {n(P['m_ri'])} mm), "
  f"de modo que la interfaz queda libre del rebaje del collar y del agujero de la plancha inferior (Ø {n(hb['Drb'])} mm). El rebaje del cubo tiene profundidad h_collar − δ + c_boss_a, con δ la altura que suma la interfaz; "
  "se reparte entre la plancha inferior y el cubo. Criterio de proyecto (geometría); filete del collar según AWS D1.1/D1.1M:2020 y AISC 360-22 §J2.2b.", size=9)
table(["Holgura o dimensión", "Id", "Valor", "Unidad"], [[plab(k).split(" (")[0], k, n(P[k]), PL[k]["u"]] for k in ("h_boss", "D_boss", "w_collar", "c_boss_r", "c_boss_a", "m_ri", "g_bush", "D_piv")],
      widths=(150, 35, 30, 30), size=7.5, num_cols=(2,))
table(["Alternativa", "δ interfaz (mm)", "R_i (mm)", "Ø rebaje (mm)", "Profundidad (mm)", "En plancha inferior (mm)", "En el cubo (mm)", "Pared junto al rebaje (mm)"],
      [[SHORT[i], n(AL[i]["hub"]["delta"]), n(AL[i]["Ri"]), n(AL[i]["hub"]["Drb"]), n(AL[i]["hub"]["hRaw"]), n(AL[i]["hub"]["hPl"]), n(AL[i]["hub"]["hHub"]), n(AL[i]["hub"]["wall"])] for i in IDS],
      widths=(66, 28, 24, 26, 30, 32, 28, 33), size=7.5, num_cols=tuple(range(1, 8)))
table(CH, [crow(c) for c in AL["base"]["collar"]], widths=CW, size=6.5, num_cols=(2, 3, 5))
T("Variación con la alternativa (la pared del rebaje, el buje bajo la plancha superior y la profundidad del rebaje dependen de δ):", size=9, after=1)
rows = []
for i in ("A", "B", "C3"):
    for c in find(AL[i], "collar", r"Rebaje del cubo|Buje sobre el collar|Interfaz: R_i"):
        r = crow(c); r[0] = f"[{i}] " + r[0]; rows.append(r)
table(CH, rows, widths=CW, size=6.5, num_cols=(2, 3, 5))
T(f"Resultado: R_i = {n(AL['base']['Ri'])} mm con holgura m_ri = {n(P['m_ri'])} mm (FU 1,00: es la holgura mínima adoptada). En B (δ = {n(AL['B']['interfaz']['delta'])} mm) el rebaje se reduce a {n(AL['B']['hub']['hRaw'])} mm de profundidad y queda todo en la plancha inferior; "
  "el cubo no se rebaja.", bold=True, size=9)

# ---- 9.4 orejas
H("9.4 Orejas de izaje (R = 92 mm, Ø agujero 45 mm)", 2)
T(f"Hipótesis. Cuatro orejas de plancha t = {n(P['t_ear'])} mm en la base, c_lug = {n(P['c_lug'])} mm y x_lug = {n(P['x_lug'])} mm, grillete de pasador Ø {n(P['d_ear'] - P['g_ear'])} mm (holgura g = {n(P['g_ear'])} mm), "
  "3 ramales efectivos a 60°. Resistencia con ASME BTH-1 §3-2 y §3-3 (Nd = 3,0) y AISC 360-22 §D5; geometría de la oreja con AISC 360-22 §D5.2: extensión a ≥ 1,33·b_e y ancho 2R ≥ 2·b_e + d, con b_e = mín(2t + 16; (2R − d)/2).", size=9)
table(CH, [crow(c) for c in AL["base"]["orejas"]], widths=CW, size=6.5, num_cols=(2, 3, 5))
ea = find(AL["base"], "orejas", r"extensión a")[0]
T(f"Resultado: las orejas cumplen; la extensión tras el agujero gobierna con FU {n(ea['fu'])} ({n(ea['dem'])} frente a {n(ea['cap'])} mm). La holgura de {n(P['g_ear'])} mm solo es admisible porque el izaje es estático (el pasador no gira bajo carga plena).", bold=True, size=9)

# ---- 9.5 filetes
H("9.5 Filetes: mínimo AWS D1.1 y máximo AISC 360-22 J2.2b", 2)
T("Hipótesis. Filete mínimo por la parte más gruesa unida (AWS D1.1/D1.1M:2020, Tabla 5.8: 3, 5, 6 y 8 mm para ≤ 6, ≤ 12, ≤ 20 y > 20 mm), sin exceder el espesor de la parte más delgada; filete máximo a lo largo de bordes "
  "(AISC 360-22 §J2.2b: t < 6 mm → t; t ≥ 6 mm → t − 2 mm), aplicado a la parte que termina en el borde. En las filas de mínimo, Demanda = w_mín exigido y Capacidad = w adoptado; en las de máximo, Demanda = w adoptado y Capacidad = w_máx.", size=9)
table(CH, [crow(c) for c in AL["base"]["filetes"]], widths=CW, size=6.5, num_cols=(2, 3, 5))
rows = []
for i in ("A", "B", "C1", "C2", "C3"):
    for c in find(AL[i], "filetes", r"filete mínimo del tope"):
        r = crow(c); r[0] = f"[{i}] " + r[0]; rows.append(r)
T("Filetes de los topes de cada alternativa (mismo criterio AWS D1.1/D1.1M:2020 Tabla 5.8):", size=9, after=1)
table(CH, rows, widths=CW, size=6.5, num_cols=(2, 3, 5))
fm = find(AL["base"], "filetes", r"Filete mínimo almas")[0]
wmax_web = P["t_web"] - 2 if P["t_web"] >= 6 else P["t_web"]
T(f"Resultado: los filetes de mejillas, collar y orejas quedan entre el mínimo de AWS y el máximo de AISC. Los de almas y nervios están en el mínimo exacto ({n(fm['dem'])} mm = {n(fm['cap'])} mm, FU 1,00). "
  f"Queda un punto abierto: el núcleo exige w_mín ≤ w ≤ t_alma, pero el máximo de borde de AISC 360-22 §J2.2b para un alma de {n(P['t_web'])} mm sería t − 2 = {n(wmax_web)} mm, menor que el mínimo de AWS de {n(fm['dem'])} mm (fijado por la plancha de 20 mm). "
  "No es un incumplimiento del núcleo, pero el filete máximo de almas y nervios sigue pendiente de revisión (se resuelve con el procedimiento de soldadura o con el espesor del alma).", bold=True, size=9)

# ---- 9.6 madera
H("9.6 Cubierta de madera dura con anillo de acero", 2)
wd = AL["W"]["madera"]
T(f"Hipótesis. Tablones de madera dura e = {n(wd['t_wood'])} mm dentro de una pletina de acero de borde (t_ring = {n(wd['t_ring'])} mm, alto igual al espesor de los tablones) soldada a la plancha superior; "
  "la cubierta gira con la mesa, no se acredita reparto de la carga y la presión de contacto sube por el peso agregado. Sin tablones, la masa de la cubierta es cero.", size=9)
table(["Magnitud", "Valor"], [["Masa de la madera", n(wd["m_madera"], unit="kg")], ["Masa del anillo de acero", n(wd["m_anillo"], unit="kg")],
                              ["Δ masa total contra la base", "+" + n(AL["W"]["dMasa"], unit="kg")], ["Altura agregada", n(wd["t_wood"], unit="mm")],
                              ["q_máx con la cubierta", n(AL["W"]["q_max"], unit="MPa")], ["FS de giro", n(AL["W"]["giro"]["FS"])]], widths=(90, 50), size=8)
table(CH, [crow(c) for c in wd["checks"]], widths=CW, size=6.5, num_cols=(2, 3, 5))
T("Resultado: la presión de aplastamiento perpendicular a la fibra queda bajo la admisible, la ley lineal de presiones no admite tracción y el giro conserva su FS. "
  "La fijación de los tablones, el acceso a la tapa de inspección y la humedad quedan como pendiente de proyecto.", bold=True, size=9)

# ---- 9.7 pendientes
H("9.7 Advertencias y pendientes por alternativa", 2)
rows = []
for i in IDS:
    av = AL[i]["avisos"]
    if not av:
        rows.append([i, "—", "—", "Sin advertencias ni pendientes", "—"])
    for v in av:
        rows.append([i, EST.get(v["estado"], v["estado"]), v["grp"], v["nombre"], v["ref"]])
table(["Alt.", "Estado", "Grupo", "Advertencia o pendiente", "Referencia"], rows, widths=(11, 20, 28, 140, 68), size=7)
T("Además de lo anterior, quedan como pendiente común el filete máximo de almas y nervios (9.5) y la numeración de artículos de ASME BTH-1 (capítulo 12).", size=9)

# ================================================================= 10. EXPOSICIÓN SOLAR (horizontal)
TH = D["termica"]
THW = ALT["termica_madera"][0]
THA = {a["id"]: a for a in TH["alternativas"]}
THA["W"] = THW
MED = ALT["medidas"]
T0, TS = TH["T_ref"], TH["T_scn"]
iS = TH["T"].index(TS)
F80 = [f for f in TH["factores"] if f["T"] == TS][0]
AC80 = [x for x in TH["aceite"] if x["T"] == TS][0]
VI80 = [x for x in TH["viscosidad"] if x["T"] == TS][0]
bT = lambda i, k=iS: THA[i]["byT"][k]
filas = lambda i, subs, k=iS: [f for f in bT(i, k)["filas"] if f["sub"] in subs]
bas80 = bT("base")
REGREF = "docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)»"

# Afirmaciones cualitativas del texto: si los datos del núcleo cambian y dejan de ser ciertas, la memoria no se emite con texto desactualizado
_b = lambda i, k=iS: THA[i]["byT"][k]
assert all(AL[i]["veredicto"]["gira"] and AL[i]["veredicto"]["estructura"] for i in IDS), "alguna alternativa no cumple a 20 °C"
assert all(abs(AL[i]["veredicto"]["fuMax"] - 1) < 1e-6 for i in IDS), "FU máximo global distinto de 1,00"
assert all(_b(i)["estructura"] for i in ("base", "A", "C1", "C2", "W")) and not _b("B")["estructura"] and not _b("C3")["estructura"], "estructura a 80 °C: texto desactualizado"
assert not _b("A")["gira"] and not _b("B")["gira"] and all(_b(i)["gira"] for i in ("base", "C1", "C2", "C3", "W")), "giro a 80 °C: texto desactualizado"
assert all(_b(i)["nFail"] > 0 and not _b(i)["termico"] for i in IDS), "falla térmica del aceite en todas: texto desactualizado"
assert all(abs(THA[i]["byT"][0]["FS"] - _b(i)["FS"]) < 1e-9 for i in IDS), "el FS de giro cambia con T"
assert (not _b("B", 2)["estructura"]) and (not _b("A", 2)["gira"]) and _b("C3", 2)["fuTerm"] > 1 and all(not _b(i, 4)["estructura"] for i in IDS), "sensibilidad 20–100 °C: texto desactualizado"
assert len(THA["C3"]["sens"]["bz090"]["empeoran"]) == 0, "bronce x 0,90 cambia verificaciones"
assert not THA["B"]["sens"]["uhmw"]["kp"][1]["cumple"] and THA["B"]["sens"]["uhmw"]["kp_crit"] is not None
assert THW["sens"]["madera"][0]["estado"] == "ok" and THW["sens"]["madera"][1]["estado"] == "fail"
assert MED["alivio_termico"][1]["resumen"]["nFail"] == 0 and MED["alivio_termico"][0]["resumen"]["nFail"] > 0

H("10. Exposición solar: servicio a 80 °C")
T("Escenario aparte, pedido del mandante (06-11-2026): la tornamesa expuesta al sol, con el cuerpo a 80 °C. No cambia el cálculo a 20 °C ni el veredicto de los capítulos 8 y 9; "
  f"se obtiene con TT.thermal (clave `termica` de tools/export_design.js, la misma que muestra la pestaña Temperatura de {TOOL}). Los datos y su nivel de confianza A/B/C están en {REGREF}; "
  "lo que no pude leer en la norma original queda marcado con confianza C.", size=9)

H("10.1 Hipótesis", 2)
table(["Hipótesis", "Valor adoptado", "Origen y confianza"], [
    ["Temperatura del cuerpo", f"{pint(TS)} °C uniforme en todo el cuerpo; referencia de diseño y montaje {pint(T0)} °C (ΔT = {pint(TS - T0)} K)", "Pedido del mandante. Plancha horizontal de acero oscuro al sol: 58 a 70 °C medidos, 80 °C es cota alta plausible sin viento (C)"],
    ["Gradiente entre planchas", f"{n(TH['gradiente_scn'])} K entre la plancha superior (al sol) y la inferior (a la sombra) a {pint(TS)} °C; a otra temperatura se escala con ΔT/{pint(TS - T0)} K", "EN 1991-1-5 §6.1.4.1, Tabla 6.1 (18 K, tableros de puentes: otra tipología; C). Medición o análisis térmico propio por hacer"],
    ["Geometría", f"Dimensionada a {pint(T0)} °C y evaluada congelada a {pint(TS)} °C: espesores, largos de tope, ménsula y juntas son los de 20 °C; solo se reducen las capacidades", "Criterio del núcleo (TT.thermalP). No re-dimensiona"],
    ["Capacidades", f"Factores k a {pint(TS)} °C del apartado 10.2, interpolados linealmente entre {pint(T0)} °C y {pint(TS)} °C y extrapolados con nota sobre {pint(TS)} °C", "Registro, tabla «Valores por material»"],
    ["Aceite hidráulico", f"ISO VG 46 a {pint(TS)} °C; ν = {n(VI80['lo'])} a {n(VI80['hi'])} mm²/s (IV 100 a 185); K del aceite {n(P['K_oil'])} a {n(P['K_oil_hi'])} MPa", "ASTM D341 (Walther), fichas de aceite (B/C); K sin fuente a 700 bar y 80 °C (C)"],
    ["Válvula de bloqueo", f"Cada cilindro con válvulas de retención/bloqueo (capítulo 7.7): el tramo cilindro + retenciones puede quedar aislado y calentarse; alivio térmico del tramo: {'no hay' if P['alivio_term'] == 0 else n(P['alivio_term'], unit='bar')}", "ISO 4413:2010 (cláusula por confirmar); práctica de Power & Motion y AIChE/CCPS (secundarias)"],
    ["Contenedor del aceite", f"Cilindro de pared gruesa b/a = {n(P['ba_cil'])} (Lamé), K_c = {n(AC80['Kc_lame_MPa'] / 1000)} GPa; presión máxima de trabajo {n(P['p_max_cil'], unit='bar')}, prueba 1,5× = {n(1.5 * P['p_max_cil'], unit='bar')}", "Hipótesis del revisor (C); ISO 10100 de memoria (C)"],
    ["Alcance", "Informativo: no entra en el veredicto del núcleo a 20 °C (golden file sin cambios)", "Decisión del proyecto"],
], widths=(40, 130, 97), size=7.5)

H("10.2 Factores de reducción por material, dilataciones y ecuaciones", 2)
T("Hipótesis. Los factores k = valor a 80 °C / valor a 20 °C salen de los parámetros kT_* del núcleo; el registro entrega solo el valor a 80 °C. Nivel de confianza: A = transcripción contrastada con copia del editor; "
  "B = ficha de fabricante o dos fuentes secundarias coherentes; C = fuente única, valor de memoria o criterio de ingeniería.", size=9)
KMAP = {"kT_Fy": "Fy", "kT_E": "E", "kT_Fy_ss": "Fy_ss", "kT_E_ss": "E_ss", "kT_p_uh": "p_uh", "kT_E_uh": "E_uh", "kT_bz": "bz", "kT_wood": "wood", "kT_bolt": "bolt", "kT_weld": "weld", "kT_hertz": "hertz", "k_mu_T": "mu"}
APLICA = {"kT_Fy": "Fy, Fy_pin, Fy_dog, Fy_pp, Fy_piv, Fy_shoe, Fy_cara", "kT_E": "E", "kT_Fy_ss": "Fy_ss (discos inox)", "kT_E_ss": "Informativo", "kT_p_uh": "p_uhmw, PV_uh", "kT_E_uh": "E_uhmw",
          "kT_bz": "Fy_bz, Fy_bz2, p_bz, PV_bz, p_bush", "kT_wood": "p_wood", "kT_bolt": "Informativo (sin verificación de resistencia)", "kT_weld": "FEXX", "kT_hertz": "Fy_surf (caras templadas)", "k_mu_T": "μ de las interfaces"}
rows = []
for pid, key in KMAP.items():
    lab = plab(pid); mt = re.match(r"^(.*?) \((.*)\)$", lab)
    prop, src = (mt.group(1), mt.group(2)) if mt else (lab, "—")
    conf = "/".join(dict.fromkeys(re.findall(r"confianza ([ABC])", lab))) or "—"
    rows.append([prop, pid, n(F80["k"][key], 3), APLICA[pid], conf, src])
table(["Material y propiedad", "Id", f"k a {pint(TS)} °C", "Se aplica a", "Conf.", "Fuente (registro, sección Temperatura)"], rows, widths=(66, 18, 16, 50, 12, 105), size=7, num_cols=(2,))
AL_SRC = {"st": ("Acero (media 20–80 °C)", "EN 1993-1-2 §3.4.1.1 (Δl/l = 1,2×10⁻⁵θ + 0,4×10⁻⁸θ² − 2,416×10⁻⁴); EN 1993-1-1 §3.2.6", "B"),
          "ss": ("Inoxidable 304/316", "EN 10088-1 (16,0 a 17,2×10⁻⁶ /K); AmesWeb", "B"), "uh": ("UHMW-PE", "ISO 11359-1/2 (Ensinger PE1000: 180×10⁻⁶ /K; GUR 4120: 200×10⁻⁶ /K)", "B"),
          "bz": ("Bronce", "CDA, de memoria (C93200 ≈ 18×10⁻⁶ /K); no encontrado", "C"), "woodT": ("Madera ⊥ fibra", "Valor de memoria sin fuente (el registro cita ~40×10⁻⁶ /K); Wood Handbook (FPL) por confirmar", "C"),
          "woodL": ("Madera ∥ fibra", "Valor de memoria sin fuente; Wood Handbook (FPL) por confirmar", "C")}
table(["Dilatación térmica", "α (10⁻⁶ /K)", "ε = α·ΔT (mm/m)", "Fuente", "Conf."],
      [[AL_SRC[k][0], n(F80["alpha"][k] * 1e6), n(F80["alpha"][k] * (TS - T0) * 1e3), AL_SRC[k][1], AL_SRC[k][2]] for k in ("st", "ss", "uh", "bz", "woodT", "woodL")], widths=(45, 24, 28, 158, 12), size=7, num_cols=(1, 2))
T("Ecuaciones del escenario y su referencia:", bold=True, size=9, after=1)
table(["Ecuación", "Expresión", "Referencia o fuente"], [
    ["Factor a temperatura intermedia", "k(T) = 1 + (k₈₀ − 1)·(T − T_ref)/(80 − T_ref); extrapolado sobre 80 °C con aviso", "Criterio del núcleo (TT.thermalFactors); k₈₀ del registro"],
    ["Dilatación libre del acero", "ε = α_m·ΔT, α_m = [ε(T) − ε(T_ref)]/(T − T_ref), ε(θ) = 1,2×10⁻⁵θ + 0,4×10⁻⁸θ² − 2,416×10⁻⁴", "EN 1993-1-2 §3.4.1.1 (de memoria, no cotejada con el texto); EN 1993-1-1 §3.2.6"],
    ["Reducción de Fy y E del acero", "Fy(80 °C) = Fy; sensibilidad k = 0,92", "AISC 360-22 Apéndice 4, Tabla A-4.2.1 y EN 1993-1-2 Tabla 3.1 (k = 1,00; solo fuego, cota); ASME II-D Tabla Y-1 (0,92, de memoria)"],
    ["Junta de dilatación de sectores", "j_req = (α_pieza − α_acero)·ΔT·cuerda; cuerda = 2R_o·sin(π/n); debe ser ≤ j_disp en frío", "Registro, «Cálculos del revisor» (~10 mm/m para UHMW contra acero)"],
    ["Aceite atrapado", "Δp = (α_v − 3α_s)·ΔT/(1/K_aceite + 1/K_c); α_v = 7,5×10⁻⁴ /K", "Registro, «Presión por aceite atrapado»; ISO 4413:2010 (cláusula por confirmar)"],
    ["Rigidez volumétrica del tubo", "K_c = E/{2·[(b² + 1)/(b² − 1) + ν]}, con b/a = relación de diámetros", "Lamé, cilindro de pared gruesa (p. ej. Timoshenko, Theory of Elasticity); hipótesis del revisor"],
    ["Curvatura y flecha por gradiente", "κ = α·ΔT_g/h; s = κ·(D/2)²/2", "Registro, «Flexión por gradiente»; EN 1991-1-5 §6.1.4.1, Tabla 6.1"],
    ["Tensión de la plancha restringida", "σ = E·α·ΔT_g/(2·(1 − ν)); verificación combinada (dem + σ_th)/cap, suma conservadora", "Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells (placa restringida); criterio del núcleo"],
    ["Buje de bronce en el cubo", "cierre = 2·[(a·α_bz·ΔT − ρ·(α_bz − α_ac)·ΔT·b) − a·α_ac·ΔT]; ρ = 2ab/[(b² + a²) − ν(b² − a²)]", "Lamé (anillo comprimido); hipótesis del revisor"],
    ["Viscosidad del aceite", "log₁₀log₁₀(ν + 0,7) = A − B·log₁₀T (T en K), con 40 y 100 °C", "ASTM D341 (Walther); Registro, «Viscosidad a 80 °C»"],
    ["PV de la lámina UHMW", "PV(T) = PV₂₀·(80 − T)/(80 − T_ref)", "Criterio del revisor (C); Quadrant TIVAR 1000, «Limiting PV»"],
    ["Madera", "p_adm(T) = C_t·p_adm; C_t = 0,70", "NDS 2018 Tabla 2.3.3 (0,70 a 125–150 °F; 80 °C queda fuera de la tabla: extrapolación, C)"],
    ["Giro con μ distinto", "FS(f·μ) = FS_diseño/f (F lineal en μ)", "Equilibrio del capítulo 7"],
], widths=(48, 126, 93), size=7)
T("Resultado: acero estructural y soldadura sin reducción a 80 °C (k = 1,00, confianza B y C); el inoxidable pierde 18 % de Fy (0,82, C) y el UHMW-PE 60 % de p_adm, PV y módulo (0,40, C); la madera, 30 % (0,70, A en la tabla, C al extrapolar a 80 °C). "
  "La dilatación del UHMW (~10 mm/m más que el acero) es lo que más pesa en las juntas.", bold=True, size=9)

# ---- 10.3 resultados por alternativa
H("10.3 Resultados por alternativa: 20 °C frente a 80 °C", 2)
T("Desarrollo. Para cada alternativa, TT.thermal analiza la geometría de 20 °C con las capacidades de cada temperatura. FS = giro (el μ no cambia con T: k_mu = 1). FU de estructura = mayor FU de resistencia de la estructura; "
  "FU térmico = mayor FU de las verificaciones del grupo «Temperatura» (juntas, gradiente, aceite, sellos). Con gradiente a 80 °C de "
  f"{n(TH['gradiente_scn'])} K.", size=9)
rows = []
for i in IDS:
    b0, b1 = bT(i, 0), bT(i)
    rows.append([SHORT[i], n(b0["FS"]), n(b1["FS"]), n(b0["fuEst"]), n(b1["fuEst"]), b1["gobernante"]["nombre"], n(b0["fuTerm"]), n(b1["fuTerm"]), b1["gobernanteTerm"]["nombre"]])
table(["Alternativa", "FS giro 20 °C", f"FS giro {pint(TS)} °C", "FU estructura 20 °C", f"FU estructura {pint(TS)} °C", f"Gobernante de estructura a {pint(TS)} °C", "FU térmico 20 °C", f"FU térmico {pint(TS)} °C", f"Gobernante térmico a {pint(TS)} °C"],
      rows, widths=(46, 15, 15, 17, 17, 52, 15, 15, 75), size=7, num_cols=(1, 2, 3, 4, 6, 7))
rows = []
for i in IDS:
    b0, b1 = bT(i, 0), bT(i)
    rows.append([SHORT[i], n(b0["masa"]), "Sí" if b0["gira"] else "NO", "Sí" if b0["estructura"] else "NO", "Sí" if b0["termico"] else "NO", f"{b0['nFail']} / {b0['nWarn']}",
                 "Sí" if b1["gira"] else "NO", "Sí" if b1["estructura"] else "NO", "Sí" if b1["termico"] else "NO", f"{b1['nFail']} / {b1['nWarn']}"])
table(["Alternativa", "Masa (kg)", "20 °C: ¿gira?", "20 °C: ¿estructura?", "20 °C: ¿térmico?", "20 °C: fallas / adv.", f"{pint(TS)} °C: ¿gira?", f"{pint(TS)} °C: ¿estructura?", f"{pint(TS)} °C: ¿térmico?", f"{pint(TS)} °C: fallas / adv."],
      rows, widths=(56, 20, 22, 26, 24, 26, 22, 26, 24, 21), size=7, num_cols=(1,))
sB, sC3 = bT("B"), bT("C3")
T(f"Resultado: el FS de giro no cambia con la temperatura porque el μ de entrada no cambia (sensibilidad en 10.11). La estructura sigue verificando a {pint(TS)} °C en base, A, C1, C2 y madera (FU {n(bT('base')['fuEst'])}); "
  f"B deja de cumplir (FU {n(sB['fuEst'])}, {sB['gobernante']['nombre']}) y C3 también (FU térmico {n(sC3['fuTerm'])} en la plancha inferior). "
  "En A y B el giro deja de verificar porque el aplastamiento del tope de los discos inoxidables supera su capacidad reducida (Fy × 0,82). "
  "Todas las alternativas tienen fallas térmicas por el aceite atrapado (10.6): sin válvula de alivio térmico ninguna queda en servicio a 80 °C.", bold=True, size=9)

# ---- 10.4 sensibilidad a la temperatura
H("10.4 Sensibilidad a la temperatura: 20, 40, 60, 80 y 100 °C", 2)
T(f"Desarrollo. Mismos cálculos a cada temperatura; el gradiente se escala con ΔT/{pint(TS - T0)} K; a 100 °C los factores están extrapolados desde 80 °C (sin dato publicado) y valen como orden de magnitud.", size=9)
table(["Factor"] + [f"{pint(f['T'])} °C" + (" (extrap.)" if f["extrapolado"] else "") for f in TH["factores"]],
      [[lab] + [n(f["k"][key], 3) for f in TH["factores"]] for lab, key in (("k Fy inoxidable", "Fy_ss"), ("k E inoxidable", "E_ss"), ("k p_adm, PV y E del UHMW", "p_uh"), ("k C_t madera", "wood"), ("k Rp0,2 pernos 10.9", "bolt"), ("k Fy del acero", "Fy"))]
      + [["α medio del acero (10⁻⁶ /K)"] + [n(f["alpha"]["st"] * 1e6, 4) for f in TH["factores"]], ["Gradiente de plancha (K)"] + [n(bT("base", k)["gradiente"]) for k in range(len(TH["T"]))]],
      widths=(70, 38, 38, 38, 38, 45), size=7.5, num_cols=(1, 2, 3, 4, 5))
TT_ = [f"{pint(t)} °C" for t in TH["T"]]
T("FU de estructura:", size=9, after=1)
table(["Alternativa"] + TT_, [[SHORT[i]] + [n(b["fuEst"]) for b in THA[i]["byT"]] for i in IDS], widths=(80, 36, 36, 36, 36, 36), size=7.5, num_cols=(1, 2, 3, 4, 5))
T("FU térmico (juntas, gradiente, aceite, sellos):", size=9, after=1)
table(["Alternativa"] + TT_, [[SHORT[i]] + [n(b["fuTerm"]) for b in THA[i]["byT"]] for i in IDS], widths=(80, 36, 36, 36, 36, 36), size=7.5, num_cols=(1, 2, 3, 4, 5))
T("Veredicto (¿gira? / ¿estructura? / ¿térmico?) y número de fallas:", size=9, after=1)
yn = lambda x: "Sí" if x else "NO"
table(["Alternativa"] + TT_, [[SHORT[i]] + [f"{yn(b['gira'])} / {yn(b['estructura'])} / {yn(b['termico'])} · {b['nFail']} f." for b in THA[i]["byT"]] for i in IDS], widths=(70, 39, 39, 39, 39, 41), size=7.5)
fb40, fb60 = bT("base", 1), bT("base", 2)
T(f"Resultado: la base, C1 y C2 son estructuralmente insensibles a la temperatura hasta 80 °C (el acero no pierde Fy); lo que crece con T es el FU térmico (gradiente de la plancha) de {n(bT('base', 0)['fuTerm'])} a {n(bT('base')['fuTerm'])} en 80 °C. "
  f"El aceite atrapado ya falla a {pint(TH['T'][1])} °C ({fb40['nFail']} fallas en la base). B es la más sensible: pierde estructura desde {pint(TH['T'][2])} °C (FU {n(bT('B', 2)['fuEst'])}). "
  f"A pierde el giro desde {pint(TH['T'][2])} °C. C3 supera FU térmico 1,00 desde {pint(TH['T'][2])} °C. A 100 °C todas pierden la estructura, incluso la base (gradiente de {n(bT('base', 4)['gradiente'])} K).", bold=True, size=9)

# ---- 10.5 cambios de estado
H("10.5 Verificaciones que cambian de estado entre 20 y 80 °C", 2)
T("Desarrollo. Se comparan, fila a fila, los estados a 20 y 80 °C. El primer bloque es común a todas las alternativas (valores de la base; las alternativas con bronce o UHMW difieren solo en el FU); "
  "los siguientes son propios de cada alternativa. Confianza = nivel del dato reducido.", size=9)
base_names = {c["nombre"]: (c["de"], c["a"]) for c in bT("base")["cambian"]}


def crows(L, tag):
    return [[tag, c["grp"], c["nombre"], EST.get(c["de"], c["de"]), EST.get(c["a"], c["a"]), "—" if c["fu20"] is None else n(c["fu20"]), "—" if c["fuT"] is None else n(c["fuT"]), c["conf"]] for c in L]


rows = crows(bT("base")["cambian"], "Todas")
for i in ("A", "B", "C1", "C2", "C3", "W"):
    spec = [c for c in bT(i)["cambian"] if base_names.get(c["nombre"]) != (c["de"], c["a"])]
    rows += crows(spec, i) if spec else [[i, "—", "Sin cambios adicionales a los comunes", "—", "—", "—", "—", "—"]]
table(["Alt.", "Grupo", "Verificación", "20 °C", f"{pint(TS)} °C", "FU 20 °C", f"FU {pint(TS)} °C", "Conf."], rows, widths=(14, 28, 140, 20, 20, 15, 15, 15), size=6.5, num_cols=(5, 6))
nA = [c for c in bT("A")["cambian"] if c["grp"] == "Interfaz inox"]
T(f"Resultado: en A y B el aplastamiento del tope de los discos inoxidables pasa de FU {n(nA[0]['fu20'])} a {n(nA[0]['fuT'])} con Fy × {n(F80['k']['Fy_ss'], 2)}; "
  "en B además fallan la lámina UHMW (espesor, aplastamiento del canto y del tope, PV) y la junta; en C3 la plancha inferior con la σ térmica pasa de advertencia a falla. "
  "Las que no dependen de la alternativa son el gradiente de las planchas (advertencia), el aceite atrapado (falla), la viscosidad del aceite y los sellos NBR (advertencia).", bold=True, size=9)

# ---- 10.6 aceite atrapado
H("10.6 Aceite atrapado entre la válvula de bloqueo y el tope", 2)
T("Hipótesis. Con las válvulas de retención/bloqueo cerradas, el aceite del cilindro queda aislado entre la válvula y un tope mecánico (fin de carrera, calado o cadena de empuje bloqueada) y se calienta de 20 a 80 °C sin poder expandirse. "
  "Si el pistón puede moverse bajo carga muerta, la presión se mantiene en W/A y la expansión sale como carrera; la sobrepresión aparece solo con el movimiento restringido. "
  "Un alivio de sistema aguas arriba de la retención no protege el tramo aislado: solo una válvula de alivio térmico en el propio tramo lo hace.", size=9)
T("Desarrollo. Δp = (α_v − 3α_s)·ΔT/(1/K_aceite + 1/K_c) (registro, «Presión por aceite atrapado»; ISO 4413:2010, cláusula por confirmar). Con 1/K_c = 0 el contenedor es rígido; con Lamé (b/a = "
  f"{n(P['ba_cil'])}) K_c = {n(AC80['Kc_lame_MPa'] / 1000)} GPa; en manguera, K combinado de 327 MPa (C).", size=9)
table(["T (°C)", "ΔT (K)", "Rígido, K = 1,4 / 1,9 GPa (bar)", "Cilindro (Lamé), K = 1,4 / 1,9 GPa (bar)", "Manguera (bar)", "Adoptado: cilindro, K alta (bar)"],
      [[pint(a["T"]), pint(a["dT"]), f"{n(a['rigido']['bajo'])} / {n(a['rigido']['alto'])}", f"{n(a['cilindro']['bajo'])} / {n(a['cilindro']['alto'])}", n(a["manguera"]), n(a["seleccion_bar"])] for a in TH["aceite"]],
      widths=(25, 25, 62, 68, 40, 47), size=7.5, num_cols=(0, 1, 2, 3, 4, 5))
orows = [f for f in bT("base")["filas"] if f["sub"] == "e"]
table(CHC, [crow(c, True) for c in orows], widths=CWC, size=6.5, num_cols=(2, 3, 5))
dp = AC80["cilindro"]["alto"]
o1 = [f for f in orows if "carrera de diseño" in f["nombre"]][0]; o2 = [f for f in orows if "tras el calado" in f["nombre"]][0]
T(f"Resultado: Δp = {n(dp)} bar con K = 1,9 GPa en el cilindro ({n(AC80['cilindro']['bajo'])} bar con 1,4 GPa; {n(AC80['rigido']['alto'])} bar si el contenedor fuera rígido y {n(AC80['manguera'])} bar solo con manguera). "
  f"En la carrera de diseño la presión llega a {n(o1['dem'])} bar frente a la presión máxima de trabajo de {n(o1['cap'])} bar (FU {n(o1['fu'])}); tras el calado, {n(o2['dem'])} bar frente a la prueba de {n(o2['cap'])} bar (FU {n(o2['fu'])}); "
  f"en la cámara anular, {n(orows[3]['dem'])} bar. La válvula de alivio térmico es necesaria en cada cilindro; el alivio del sistema ({n(P['p_relief'])} bar) está aguas arriba de la retención y no protege el tramo.", bold=True, size=9)

# ---- 10.7 juntas
H("10.7 Juntas de dilatación de los sectores", 2)
T("Hipótesis. Cada sector se coloca con la junta en frío j_disp = máx(j_sec; dilatación a ΔT de montaje) del diseño a 20 °C. A 80 °C el sector de material con mayor α que el acero crece más que su respaldo y, si la junta se cierra, se comprime y pandea. "
  "j_req = (α_pieza − α_acero)·ΔT·cuerda, con la cuerda del sector a R_o. Referencia: registro, «Cálculos del revisor» (UHMW: ~10 mm/m más que el acero).", size=9)
rows = []
for i in IDS:
    js = THA[i]["juntas"]
    if not js:
        rows.append([i, "Sin sectores en la interfaz", "—", "—", "—", "—"])
    for j in js:
        rows.append([i, j["pieza"], n(j["j_req"]), n(j["j_disp"]), n(j["fu"]), EST.get(j["estado"], j["estado"])])
table(["Alt.", "Pieza", "j_req (mm)", "j_disp en frío (mm)", "FU", "Estado"], rows, widths=(14, 120, 30, 38, 25, 40), size=7.5, num_cols=(2, 3, 4))
jb = MED["junta_B"]
jUH = next(j for j in THA["B"]["juntas"] if "UHMW" in j["pieza"]); jUH2 = next(j for j in jb["juntas"] if "UHMW" in j["pieza"])
T(f"Resultado: el UHMW requiere {n(jb['j_req'])} mm de junta y dispone de {n(jUH['j_disp'])} mm en frío (j_sec = {n(jb['j_sec_actual'])} mm; el resto es la dilatación a ΔT de montaje): la junta se cierra (FU {n(jUH['fu'])}). "
  f"Adoptar j_sec ≥ {n(jb['j_sec_nuevo'])} mm: con ese valor la junta pasa a FU {n(jUH2['fu'])} ({EST.get(jUH2['estado'], jUH2['estado']).lower()}, al límite) y la masa de B a 20 °C pasa de {n(jb['masa20_actual'], 4)} a {n(jb['masa20'], 4)} kg. "
  "Los sectores de inox y bronce (junta requerida ≈ 0,1 mm) cumplen con holgura.", bold=True, size=9)

# ---- 10.8 holguras
H("10.8 Holguras del buje y de la uña–pasador", 2)
T("Hipótesis. El buje de bronce (Ø int. D_piv, Ø ext. D_piv + 30) va en el cubo de acero, con holgura diametral en frío c_bush_d (supuesto de ajuste H7/e8; el núcleo no define el ajuste). La mesa caliente y la base a la sombra "
  "es el caso desfavorable para la uña: el círculo de pasadores crece α·ΔT·R_pin y la cuerda entre pasadores crece con la mesa. Referencias: Lamé para el anillo comprimido; EN 1993-1-1 §3.2.6 y EN 1993-1-2 §3.4.1.1 para ε.", size=9)
table(CHC, [crow(c, True) for c in filas("base", ("b", "c", "k"))], widths=CWC, size=6.5, num_cols=(2, 3, 5))
bj = filas("base", ("b",))[0]; uj = filas("base", ("c",))
T(f"Resultado: el buje cierra {n(bj['dem'])} mm de los {n(bj['cap'])} mm de holgura diametral (FU {n(bj['fu'])}), sin riesgo de agarrotar el pivote. En la uña, la holgura radial usada es {n(uj[0]['dem'])} mm de {n(uj[0]['cap'])} mm (FU {n(uj[0]['fu'])}), "
  f"la luz entre pasadores {n(uj[1]['dem'])} mm frente a {n(uj[1]['cap'])} mm y la carrera {n(uj[2]['dem'])} mm de {n(uj[2]['cap'])} mm (FU {n(uj[2]['fu'])}, la más ajustada; quedan {n(uj[2]['cap'] - uj[2]['dem'])} mm de margen): se cumplen. "
  "Son iguales en todas las alternativas.", bold=True, size=9)

# ---- 10.9 gradiente
H("10.9 Gradiente entre planchas, curvatura y flecha", 2)
T(f"Hipótesis. Plancha superior al sol, inferior a la sombra, gradiente de {n(TH['gradiente_scn'])} K, caja de h = {n(P['h_disc'])} mm y Ø {n(P['D_top'])} mm. La mesa libre se curva sin tensión (κ = α·ΔT_g/h, flecha s = κ·(D/2)²/2); "
  "si la restricción de la caja fuera total, la plancha toma σ = E·α·ΔT_g/(2(1 − ν)) que se suma, de forma conservadora, a la tensión global + local. Referencias: EN 1991-1-5 §6.1.4.1 Tabla 6.1 (otra tipología) y Timoshenko.", size=9)
table(CHC, [crow(c, True) for c in filas("base", ("d",))], widths=CWC, size=6.5, num_cols=(2, 3, 5))
gs = filas("base", ("d",))
T(f"Resultado: κ = {n(gs[0]['dem'])} 1/m y flecha {n(gs[1]['dem'])} mm en el diámetro de la mesa, despreciable; la tensión térmica restringida de {n(gs[2]['dem'])} MPa lleva la plancha superior a FU {n(gs[3]['fu'])} y la inferior a {n(gs[4]['fu'])} (advertencia, no falla). "
  "En C3, que ya tiene la plancha inferior a FU 0,92 a 20 °C, la suma pasa de 1,00 (ver 10.5 y 10.12).", bold=True, size=9)

# ---- 10.10 sensibilidades
H("10.10 Sensibilidades: μ, Fy del acero, bronce, madera y k_p / k_E del UHMW", 2)
T("Desarrollo. Cada sensibilidad cambia un solo factor a 80 °C y repite todas las verificaciones.", size=9)
T("a) μ de la interfaz a 80 °C (FS(f·μ) = FS_diseño/f; el μ real a 80 °C no tiene fuente: la grasa fluye y se expulsa).", bold=True, size=9, after=1)
rows = []
for i in ("base", "A", "B", "C1", "C3"):
    s = THA[i]["sens"]; mu_d = AL[i]["giro"]["mu"]
    rows.append([SHORT[i], n(mu_d)] + [f"{n(m['FS'])} ({'gira' if m['gira'] else 'NO gira'})" for m in s["mu"]] + [n(s["mu_crit"] * mu_d)])
table(["Alternativa", "μ de diseño"] + [f"μ × {n(m['f'], 2)}" for m in THA["base"]["sens"]["mu"]] + ["μ máx. con FS ≥ FS_mín"], rows, widths=(70, 22, 32, 32, 32, 32, 36), size=7.5, num_cols=(1, 2, 3, 4, 5, 6))
T(f"Resultado: con acero–acero el giro admite hasta μ = {n(THA['base']['sens']['mu_crit'] * AL['base']['giro']['mu'])} (×{n(THA['base']['sens']['mu_crit'])} el μ de diseño) con FS ≥ {n(P['FS_min'])}; con bronce se llega al mismo μ máximo ({n(THA['C1']['sens']['mu_crit'] * AL['C1']['giro']['mu'])}), "
  "porque lo fija la fuerza de calado. Si la grasa a 80 °C subiera el μ más de un 10 % sobre el de diseño del acero–acero, la base dejaría de girar con FS ≥ FS_mín.", size=9)
T("b) Fy del acero × 0,92 (ASME II-D Tabla Y-1, de memoria, confianza C) y bronce × 0,90.", bold=True, size=9, after=1)
rows = []
for i in IDS:
    k = THA[i]["sens"]["kFy092"]; b = bT(i)
    rows.append([SHORT[i], n(b["fuEst"]), n(k["fuEst"]), k["gobernante"]["nombre"], n(b["fuTerm"]), n(k["fuTerm"]), yn(k["gira"]), yn(k["estructura"]), pint(len(k["empeoran"]))])
table(["Alternativa", "FU estructura (k = 1)", "FU estructura (k = 0,92)", "Gobernante", "FU térmico (k = 1)", "FU térmico (k = 0,92)", "¿Gira?", "¿Estructura?", "Verificaciones que empeoran"],
      rows, widths=(54, 25, 27, 62, 24, 26, 13, 18, 18), size=7, num_cols=(1, 2, 4, 5, 8))
bz = THA["C3"]["sens"]["bz090"]
T(f"Resultado: con k = 0,92 el FU de estructura sube {n(THA['base']['sens']['kFy092']['dFu'])} (de {n(bT('base')['fuEst'])} a {n(THA['base']['sens']['kFy092']['fuEst'])}) y varias verificaciones pasan a advertencia; la plancha superior con la σ térmica llega a FU "
  f"{n(THA['base']['sens']['kFy092']['fuTerm'])} y la estructura deja de cumplir. Con bronce × 0,90 (C1 a C3) no cambia ninguna: C3 queda con FU de estructura {n(bz['fuEst'])}.", bold=True, size=9)
T("c) UHMW-PE (alternativa B): k_p (p_adm y PV) y k_E (módulo) a 80 °C.", bold=True, size=9, after=1)
us = THA["B"]["sens"]["uhmw"]
table(["Variación", "k_p", "k_E", "FU máximo de la lámina", "Gobernante", "¿Cumple?"],
      [["k_p"] + [n(r["k_p"], 2), n(r["k_E"], 2), n(r["fuUHMW"]) if r["fuUHMW"] < 50 else "> 50", r["gobernante"], yn(r["cumple"])] for r in us["kp"]] +
      [["k_E"] + [n(r["k_p"], 2), n(r["k_E"], 2), n(r["fuUHMW"]) if r["fuUHMW"] < 50 else "> 50", r["gobernante"], yn(r["cumple"])] for r in us["kE"]],
      widths=(25, 15, 15, 40, 140, 25), size=7, num_cols=(1, 2, 3))
T(f"Resultado: con k_p = {n(P['kT_p_uh'], 2)} la lámina falla; solo cumple si k_p ≥ {n(us['kp_crit'], 2)}. El módulo reducido casi no cambia el resultado (manda la presión admisible). "
  "Sin la curva del proveedor entre 20 y 80 °C, la alternativa B no se puede acreditar a 80 °C.", bold=True, size=9)
T("d) Madera: factor C_t de aplastamiento perpendicular a la fibra (NDS 2018 Tabla 2.3.3).", bold=True, size=9, after=1)
table(["C_t", "FU del aplastamiento", "Estado"], [[n(m["Ct"], 2), n(m["fu"]), EST.get(m["estado"], m["estado"])] for m in THW["sens"]["madera"]], widths=(30, 50, 40), size=7.5, num_cols=(0, 1))
T(f"Resultado: con C_t = {n(THW['sens']['madera'][0]['Ct'], 2)} la madera cumple (FU {n(THW['sens']['madera'][0]['fu'])}); con madera húmeda (C_t = {n(THW['sens']['madera'][1]['Ct'], 2)}) falla (FU {n(THW['sens']['madera'][1]['fu'])}). "
  "80 °C queda fuera de la tabla del NDS (límite 150 °F = 66 °C): el factor es una extrapolación.", bold=True, size=9)

# ---- 10.11 BTH-1
H("10.11 Alcance térmico de ASME BTH-1", 2)
bth = [f for f in bT("base")["filas"] if "BTH-1" in f["nombre"]][0]
T("Hipótesis. La cadena de empuje se verifica por analogía con ASME BTH-1, Categoría de diseño B (Nd = 3,0). BTH-1 define un rango estándar de servicio de −4 a 66 °C (25 a 150 °F); "
  f"{pint(TS)} °C (176 °F) queda fuera de ese rango y Nd = 3,0 no incluye un margen térmico explícito. La sección exacta de BTH-1 no está confirmada (fuentes secundarias: Hoist Magazine, Tandemloc).", size=9)
table(CHC, [crow(bth, True)] + [crow(c, True) for c in filas("base", ("j",)) if c is not bth and "BTH-1" not in c["nombre"]], widths=CWC, size=6.5, num_cols=(2, 3, 5))
T(f"Resultado: {pint(TS)} °C excede el rango estándar en {pint(TS - 66)} K; usar BTH-1 en este escenario requiere una decisión de persona calificada y el registro de la hipótesis. Si el mandante mantiene {pint(TS)} °C, "
  f"la sensibilidad con k_Fy = 0,92 (10.10 b) es la referencia: el FU de estructura queda en {n(THA['base']['sens']['kFy092']['fuEst'])}.", bold=True, size=9)

# ---- 10.12 medidas
H("10.12 Medidas recomendadas", 2)
T("Desarrollo. Las medidas con efecto numérico se evaluaron con el núcleo a 80 °C (tools/export_alternativas.js, clave `medidas`).", size=9)
ar0, ar1 = MED["alivio_termico"]
c3 = MED["c3_t_bot"]
g0 = MED["gradiente"][0]["alts"]["C3"]; gm = MED["gradiente"][2]["alts"]["C3"]
Lnew = AL["A"]["topes"][0]["L"] * nA[0]["fuT"]
table(["N°", "Medida", "Efecto cuantificado por el núcleo", "Fuente o referencia"], [
    ["1", f"Válvula de alivio térmico en cada cilindro (tramo cilindro + retenciones), apertura sobre el alivio del sistema ({n(P['p_relief'])} bar) y bajo la presión máxima de trabajo del cilindro",
     f"Con apertura de {n(ar1['alivio_term'])} bar: fallas térmicas {ar0['resumen']['nFail']} → {ar1['resumen']['nFail']}, escenario térmico {'cumple' if ar1['resumen']['termico'] else 'no cumple'}; la presión atrapada queda en {n(ar1['filas'][1]['dem'])} bar. "
     f"Hoy la ventana de ajuste es nula (alivio del sistema {n(P['p_relief'])} bar = presión máxima {n(MED['p_max_cil'])} bar): conviene bajar el alivio del sistema o elegir un cilindro de mayor presión",
     "Registro, «Presión por aceite atrapado»; ISO 4413:2010 (cláusula por confirmar). Práctica de Power & Motion y AIChE/CCPS"],
    ["2", "No usar un alivio de sistema aguas arriba como protección del tramo aislado", "No protege: con la retención cerrada el aceite del cilindro no ve el alivio del sistema", "Registro, «Si el pistón puede moverse bajo una carga muerta»"],
    ["3", f"Junta en frío de los sectores j_sec ≥ {n(jb['j_sec_nuevo'])} mm (UHMW de B)", f"j_req {n(jb['j_req'])} mm frente a {n(jUH['j_disp'])} mm disponibles; con j_sec = {n(jb['j_sec_nuevo'])} mm la junta queda en FU {n(jUH2['fu'])}. No basta para B: ver medida 6",
     "Registro, «Cálculos del revisor» (α UHMW 180 a 200×10⁻⁶ /K)"],
    ["4", "A y B: ampliar el largo del tope de los discos inoxidables o aumentar h_c", f"El aplastamiento sube a FU {n(nA[0]['fuT'])} con Fy × {n(F80['k']['Fy_ss'], 2)}; el largo requerido es ≈ {n(Lnew)} mm (hoy {n(AL['A']['topes'][0]['L'])} mm; σ ∝ 1/L; límite R_o − R_i − 100 = {n(AL['A']['Ro'] - AL['A']['Ri'] - 100)} mm). Estimación lineal: confirmar con el núcleo",
     "ASME BTH-1 §3-3.3; EN 10088-2 de memoria (C)"],
    ["5", "C3: engrosar la plancha inferior o reducir el gradiente (sombra, pintura clara, cubierta)", f"t_bot {n(c3[0]['t_bot'])} → {n(c3[1]['t_bot'])} mm: FU de estructura {n(c3[0]['fuEst'])} → {n(c3[1]['fuEst'])}, FU térmico {n(c3[0]['fuTerm'])} → {n(c3[1]['fuTerm'])}, +{n(c3[1]['masa20'] - c3[0]['masa20'])} kg. "
     f"Con gradiente de {n(MED['gradiente'][2]['gradiente'])} K (en vez de {n(TH['gradiente_scn'])}) el FU térmico de C3 es {n(gm['fuTerm'])} y su estructura {'cumple' if gm['estructura'] else 'no cumple'}; sin gradiente, FU térmico {n(g0['fuTerm'])}", "AISC 360-22 (σ ≤ 0,6Fy); EN 1991-1-5 Tabla 6.1 (gradiente, C)"],
    ["6", "B: no acreditar la lámina de UHMW a 80 °C sin la curva del proveedor (límite de servicio continuo = 80 °C)", f"Falla en espesor, canto, tope, PV y junta; solo cumpliría con k_p ≥ {n(us['kp_crit'], 2)}", "Fichas Quadrant/Mitsubishi TIVAR 1000, Ensinger PE1000, Röchling Polystone M"],
    ["7", "Protección solar de la mesa (sombra, pintura clara, ventilación)", f"La sensibilidad a la temperatura (10.4) muestra que a {pint(TH['T'][1])} y {pint(TH['T'][2])} °C el FU de estructura de la base no cambia y las fallas térmicas son {bT('base', 1)['nFail']} y {bT('base', 2)['nFail']}", "Registro, «Temperatura superficial estimada»"],
    ["8", "Aceite y sellos: aceite de mayor índice de viscosidad (VG 68 o IV 185) y sellos para 100 °C o más (FKM)", f"Viscosidad a {pint(TS)} °C: {n(VI80['lo'])} mm²/s (IV 100) frente a {n(VI80['hi'])} mm²/s (IV 185), mínimo de la bomba {n(P['nu_min'])} mm²/s; sellos NBR en su límite ({n(P['T_seal'])} °C)", "ASTM D341; Ulman, Machine Design, Power & Motion (secundarias)"],
    ["9", "Registrar la decisión de persona calificada sobre el rango térmico de BTH-1", f"{pint(TS)} °C excede −4 a 66 °C en {pint(TS - 66)} K", "ASME BTH-1 (sección por confirmar)"],
], widths=(8, 78, 118, 63), size=7)

# ---- 10.13 supuestos C
H("10.13 Supuestos de confianza C a confirmar con el proveedor", 2)
CONF_C = {"UHMW": ("kT_p_uh", "Curva de módulo y de límite elástico del UHMW-PE de 20 a 80 °C, creep y desgaste a T", "Proveedor del UHMW (Quadrant/Mitsubishi, Ensinger, Röchling)"),
          "Inoxidable": ("kT_Fy_ss", "Rp0,2 del inox a 80–100 °C (EN 10088-2: 157 y 166 MPa a 100 °C de memoria; una página de EN 10269 da 177 y 187 MPa)", "Proveedor del inox / EN 10088-2"),
          "Bronce": ("kT_bz", "Fy, α y límite de temperatura del bronce C95400 (la ficha hallada es de C93200)", "Proveedor del bronce grafitado"),
          "Madera": ("kT_wood", "C_t a 80 °C y α de la madera; NCh1198 (factor KT sin dato)", "Proveedor de la madera / NDS 2018 / NCh1198"),
          "Pernos": ("kT_bolt", "Rp0,2 a 100 °C de la clase 10.9 (ISO 898-1, anexo informativo)", "ISO 898-1 / proveedor de pernos"),
          "Soldadura": ("kT_weld", "Criterio térmico de servicio de AWS D1.1:2020 (no lo hay)", "Revisor"),
          "Gradiente": ("dT_grad", "Gradiente real de una caja de ~230 mm al sol", "Medición o análisis térmico propio"),
          "Módulo volumétrico": ("K_oil", "K del aceite a 700 bar y 80 °C; espesor de pared real del cilindro (b/a)", "Fabricante del aceite y del cilindro"),
          "Viscosidad": ("nu_min", "Viscosidad mínima admisible de la bomba", "Fabricante de la bomba"),
          "sello": ("T_seal", "Límite continuo del compuesto del sello elegido", "Catálogo Parker / Trelleborg / Hallite"),
          "μ": ("k_mu_T", "μ de la grasa a 80 °C y su punto de goteo del producto elegido", "Ensayo de aceptación / proveedor de la grasa"),
          "Holgura buje": ("c_bush_d", "Ajuste real del buje en el pivote (H7/e8 supuesto)", "Proveedor del buje / proyectista")}
rows = []
for k, s_ in enumerate(TH["supuestos_C"], 1):
    key = next((kk for kk in CONF_C if kk in s_), None)
    pid, que, quien = CONF_C[key] if key else (None, "Confirmar", "Revisor")
    val = (n(TH["gradiente_scn"]) if pid == "dT_grad" else n(P[pid], 3)) + ("" if PL[pid]["u"] == "–" else " " + PL[pid]["u"]) if pid else "—"
    rows.append([pint(k), s_, val, que, quien])
table(["N°", "Supuesto del núcleo", "Valor del parámetro", "Dato a confirmar", "Responsable"], rows, widths=(8, 70, 28, 100, 61), size=7, num_cols=(0,))
T("Resultado: ningún resultado térmico de este capítulo debe tomarse como definitivo mientras estos supuestos no se confirmen; los de mayor efecto son el factor de capacidad del UHMW (decide B), el gradiente de planchas (decide C3 y el margen de la base) "
  "y el módulo volumétrico del aceite (fija la presión atrapada, aunque la conclusión de instalar la válvula de alivio térmico no depende de ellos: con K = 1,4 GPa el cilindro igualmente llega a "
  f"{n(AC80['cilindro']['bajo'])} bar de sobrepresión).", bold=True, size=9)

# ================================================================= 9. RESUMEN
ps = doc.add_section()   # vuelve a vertical
ps.orientation = WD_ORIENT.PORTRAIT; ps.page_width, ps.page_height = Mm(210), Mm(297)
ps.left_margin = ps.right_margin = Mm(20); ps.top_margin = Mm(20); ps.bottom_margin = Mm(18)
header_footer(ps)
H("11. Resumen de resultados")
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
T("Alternativas de interfaz (capítulo 9) y escenario solar a 80 °C (capítulo 10):", bold=True, size=9.5)
table(["Alternativa", "Masa (kg)", "FS giro", "FU estructura 20 °C", f"FU estructura {pint(TS)} °C", f"¿Cumple a {pint(TS)} °C? (giro / estructura / térmico)"],
      [[SHORT[i], n(AL[i]["masa"]), n(AL[i]["giro"]["FS"]), n(bT(i, 0)["fuEst"]), n(bT(i)["fuEst"]), f"{yn(bT(i)['gira'])} / {yn(bT(i)['estructura'])} / {yn(bT(i)['termico'])}"] for i in IDS],
      widths=(52, 18, 14, 20, 20, 46), size=7.5, num_cols=(1, 2, 3, 4))
T(f"A {pint(TS)} °C la base, C1, C2 y la cubierta de madera conservan giro y estructura; A pierde el giro (tope de los discos con Fy × {n(F80['k']['Fy_ss'], 2)}), B pierde giro y estructura (lámina UHMW y junta) y C3 pierde la estructura (plancha inferior más σ térmica). "
  "Ninguna alternativa cumple el grupo térmico sin válvula de alivio térmico por el aceite atrapado.", size=9)
H("Conclusión", 2)
T(("Con los parámetros indicados la tornamesa TT300-C gira la carga de {0} tf en el caso de diseño con FS = {1} y todas las verificaciones estructurales "
   "y geométricas cumplen (utilización máxima {2}).").format(pint(P["W_tf"]), n(cd["FS"]), n(vd["fuMax"])) if vd["gira"] and vd["estructura"] else
  "ATENCIÓN: la configuración actual no cumple todas las verificaciones; ver capítulo 8.", bold=True)
T(f"A {pint(TS)} °C (capítulo 10) la geometría dimensionada a {pint(T0)} °C sigue girando y verificando la estructura en la configuración base, pero el aceite atrapado exige válvula de alivio térmico en cada cilindro y 80 °C excede el rango estándar de ASME BTH-1: "
  "el servicio a 80 °C queda condicionado a esas dos medidas y a confirmar los supuestos de confianza C.", bold=True)

# ================================================================= 10. PENDIENTES
H("12. Puntos a confirmar antes de fabricar")
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
    ["10", "Interfaz con placa de bronce y grafito (C), si se adopta", f"Aleación (C95400, Fy {pint(P['Fy_bz'])} MPa), p_adm {pint(P['p_bz'])} MPa, PV, desgaste y μ de catálogo; ensayo de arranque (stick-slip); disco duro (≥ 100 HB sobre el bronce, Ra ≤ 0,4 µm); fijación desmontable por sectores con topes (verificada) y ranuras de engrase; par galvánico y sellado; dibujada en las variantes del paquete (entregables/RevC/variantes)", "Proveedor / proyectista"],
    ["11", "Interfaz inoxidable (A) o con UHMW (B), si se adopta", "μ, p_adm y E_ap del UHMW son datos de catálogo; par inox–inox de aleaciones distintas o tratada contra el gripado; fijación y retención de los discos; sectores de UHMW con juntas de dilatación; dibujada en las variantes del paquete (entregables/RevC/variantes); discos pegados con epóxico estructural y respaldo granallado sin pintura; respaldo canteado ≤ 3 mm en el borde; tornillos avellanados M6; sellado perimetral; retención de los sectores de UHMW por rebaje o cola de milano; fluencia de la lámina (asentamiento 0,1 a 0,2 mm)", "Proveedor / proyectista"],
    ["12", "Certificados de material", f"Uña Re ≥ {pint(P['Fy_dog'])} MPa; pasadores Re ≥ {pint(P['Fy_pin'])} MPa; patín Fy ≥ {pint(P['Fy_shoe'])} MPa (3.1)", "Proveedor"],
    ["13", "Temple por inducción de caras de contacto", f"≥ 55 HRC (σy ≥ {pint(P['Fy_surf'])} MPa), profundidad según capítulo 8", "Proveedor / inspección"],
    ["14", "Válvula de alivio térmico en cada cilindro (tramo cilindro + retenciones)", f"No hay en el diseño base (alivio_term = {n(P['alivio_term'])}); ventana entre alivio del sistema ({n(P['p_relief'])} bar) y presión máxima de trabajo ({n(P['p_max_cil'])} bar) nula; ver 10.6 y 10.12", "Proyectista / proveedor hidráulico"],
    ["15", "Decisión sobre el rango térmico de ASME BTH-1", f"{pint(TS)} °C excede −4 a 66 °C; requiere decisión de persona calificada (10.11)", "Revisor / mandante"],
    ["16", "Junta en frío de los sectores de UHMW (B), si se adopta", f"j_sec ≥ {n(MED['junta_B']['j_sec_nuevo'])} mm (requerida {n(MED['junta_B']['j_req'])} mm a {pint(TS)} °C); B no se acredita a {pint(TS)} °C sin la curva del proveedor (10.7, 10.10)", "Proveedor del UHMW"],
    ["17", "Supuestos de confianza C del escenario solar", "Doce supuestos listados en 10.13 (UHMW, inox, bronce, madera, pernos, soldadura, gradiente, aceite, bomba, sellos, μ, buje)", "Proveedores / revisor"],
    ["18", "Filete máximo de almas y nervios", "El núcleo exige w ≤ t_alma; AISC 360-22 §J2.2b da t − 2 mm para t ≥ 6 mm (9.5)", "Revisor"],
], widths=(9, 45, 85, 31), size=8)

# ================================================================= 11. MERCADO
MK = D["mercado"]
H("13. Comparación con equipos comerciales")
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

# ================================================================= ANEXO B (horizontal): registro de valores por material
bs = doc.add_section()
bs.orientation = WD_ORIENT.LANDSCAPE; bs.page_width, bs.page_height = Mm(297), Mm(210)
bs.left_margin = bs.right_margin = Mm(15); bs.top_margin = Mm(18); bs.bottom_margin = Mm(15)
header_footer(bs)
H("Anexo B. Valores por material del escenario térmico (registro de criterios)")
T(f"Transcripción de docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)», tabla «Valores por material». Escala de confianza: A = contrastado con copia del editor de la norma; "
  "B = ficha de fabricante o coherencia entre dos fuentes secundarias; C = fuente única, valor de memoria o criterio de ingeniería.", size=9)
vrows, on = [], False
for ln in reg:
    if ln.startswith("### "):
        on = ln.strip() == "### Valores por material"
        continue
    if on and ln.startswith("|") and not ln.startswith("|---") and "Material" not in ln.split("|")[1]:
        c = [x.strip().replace("**", "") for x in ln.strip().strip("|").split("|")]
        if len(c) >= 7:
            vrows.append(c[:7])
table(["Material", "Propiedad", "Valor a 20 °C", "Valor a 80 °C", "Factor 80/20", "Fuente y artículo", "Conf."], vrows, widths=(30, 38, 42, 48, 24, 74, 11), size=6.5)

# ================================================================= salida
name = f"TT300-C_Memoria_Rev{REV}"
docx = OUT / f"{name}.docx"
doc.save(docx)
# Letras negras siempre: también en los estilos heredados de la plantilla de python-docx (estilos de tabla no usados con colores de tema)
import re, zipfile
_tmp = docx.with_suffix(".tmp")
with zipfile.ZipFile(docx) as zin, zipfile.ZipFile(_tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for it in zin.infolist():
        data = zin.read(it.filename)
        if it.filename in ("word/styles.xml", "word/stylesWithEffects.xml"):
            data = re.sub(rb"<w:color [^>]*/>", b'<w:color w:val="000000"/>', data)
        zout.writestr(it, data)
_tmp.replace(docx)
print(docx)
if "--no-pdf" not in sys.argv:
    r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(docx)], capture_output=True, text=True, timeout=300)
    print(OUT / f"{name}.pdf" if (OUT / f"{name}.pdf").exists() else r.stderr)
