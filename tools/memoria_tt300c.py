"""Memoria de cálculo TT300-C en Word (.docx) y PDF, generada desde cad/out/TT300-C_design.json.

Fuente única: todos los valores salen del núcleo (tools/export_design.js y tools/export_alternativas.js → TT.analyze, TT.thermal). Este script solo redacta.
Formato: texto negro, hipótesis → desarrollo → resultado, tablas antes que texto, 3 cifras significativas.
Uso (npm run memoria): node tools/export_design.js > cad/out/TT300-C_design.json && node tools/export_alternativas.js > cad/out/TT300-C_alternativas.json && python3 tools/memoria_tt300c.py
Variable de entorno TT_MEMORIA_DIR: carpeta de entrada y salida (por defecto cad/out). El .docx y el .pdf se copian además a entregables/RevC.
"""
import csv, json, math, os, pathlib, re, shutil, subprocess, sys
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(os.environ["TT_MEMORIA_DIR"]) if os.environ.get("TT_MEMORIA_DIR") else ROOT / "cad" / "out"
ENTREGA = ROOT / "entregables" / "RevC"
D = json.load(open(OUT / "TT300-C_design.json", encoding="utf-8"))
M3 = json.load(open(OUT / "TT300-C_masas3d.json", encoding="utf-8")) if (OUT / "TT300-C_masas3d.json").exists() else None
ALT = json.load(open(OUT / "TT300-C_alternativas.json", encoding="utf-8"))
ACC = ALT["accionamiento"]                             # modos de accionamiento (pivotado por defecto, guiado con leva como alternativa), familias de la placa-leva, holguras y AF2
PVM, GUM = ACC["pivotado"], ACC["guiado"]
PIV = D["pivotado"]                                    # geometría del modo por defecto (TT.designDrive)
# El control 3D de masas solo vale si el modelo 3D es del mismo diseño que el núcleo (los juegos de planos se generan a pedido; un masas3d.json de otro juego se descarta)
if M3:
    _g3 = {"mesa": "disc"}
    if not all(abs(c["nucleo"] - D["derivados"]["masas"].get(_g3.get(c["grupo"], c["grupo"]), -1e9)) <= 1e-3 * max(1.0, abs(c["nucleo"])) for c in M3["masas"]["comp"]):
        M3 = None
TAP = ALT["tapones"]                                   # tapones de grafito (TT.tapones): cantidad real frente a ideal, barridos y patrón máximo alcanzable
TPA = {a["id"]: a for a in TAP["alternativas"]}
P, DV, K = D["P"], D["derivados"], D["derivados"]["K"]
REV, DOC = "C", "TT300-C-MC-01"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
TOOL = "Tornamesa_v" + VERSION + ".html"   # herramienta principal (versión del archivo VERSION)
try:   # último commit que tocó el núcleo (packages/core); la memoria se rotula con él
    CORE_COMMIT = subprocess.run(["git", "log", "-1", "--format=%h", "--", "packages/core"], cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip() or "bc9e44f"
except (OSError, subprocess.SubprocessError):
    CORE_COMMIT = "bc9e44f"
NUCLEO = f"núcleo v{VERSION} (commit {CORE_COMMIT})"
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
    if 0 < a < 1e-3:                                   # cifras muy pequeñas: notación científica legible (7,12·10⁻¹¹)
        e_ = int(math.floor(math.log10(a))); mnt = x / 10 ** e_
        sup = str(e_).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))
        return f"{mnt:.{sig - 1}f}".replace(".", ",") + "·10" + sup + (f" {unit}" if unit else "")
    if a == 0:
        s = "0"
    elif a >= 10 ** (sig - 1):
        s = f"{round(x):,.0f}".replace(",", ".")
    else:
        dec = max(0, sig - 1 - int(math.floor(math.log10(a))))
        s = f"{x:,.{dec}f}".replace(",", "§").replace(".", ",").replace("§", ".")   # miles con punto (solo aparece con 5 o más cifras)
    return s + (f" {unit}" if unit else "")


def nd(x, unit=""):
    """Demanda o capacidad de una fila: 3 cifras significativas; las cotas en mm de 4 cifras van al mm (una holgura de 0,8 mm no se pierde en el redondeo)."""
    if isinstance(x, (int, float)) and not isinstance(x, bool) and str(unit).startswith("mm") and abs(x) >= 1000:
        return n(x, 4 if abs(x) < 1e4 else 5)
    return n(x)


def pint(x):
    return f"{round(x):,.0f}".replace(",", ".")


n2 = lambda x: f"{x:.2f}".replace(".", ",")                                             # criterios con dos decimales (0,20; 0,45)


def fu3(x):
    """Factor de utilización con 3 decimales (formato del usuario)."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    return f"{x:,.3f}".replace(",", "§").replace(".", ",").replace("§", ".")


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
    r = hp.add_run(f"TT300-C · Tornamesa hidráulica {P['W_tf']:.0f} tf · Memoria de cálculo {DOC} · Rev. {REV} · Para revisión por ingeniero calculista habilitado")
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
T("Mesa giratoria Ø{0} para cargas sobredimensionadas (transformadores y equipos pesados). Accionamiento por defecto: dos cilindros pivotados tipo KIET con bloque-uña "
  "y placas-guía curvas (drive_mode = {1}); alternativa: patín guiado con riel-leva de reenganche positiva.".format(pint(P["D_top"]), pint(P["drive_mode"])), size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=18)
table(["Campo", "Valor"], [
    ["Documento", DOC], ["Revisión", REV], ["Fecha", D["fecha"]],
    ["Estado", "Emitido para revisión – no apto para fabricación hasta aprobación"],
    ["Planos asociados", "Paquete de planos TT300C-…-C (Rev. C), generado a pedido con el generador local para la alternativa y los parámetros elegidos; el repositorio no guarda juegos de planos (capítulo 14)"],
    ["Herramienta de verificación", TOOL + " (herramienta principal; misma fuente de datos que esta memoria)"],
    ["Núcleo de cálculo", NUCLEO + ": accionamiento pivotado tipo KIET por defecto (drive_mode = 2) con placa-guía curva G1 y empuje guiado, cara cilíndrica del bloque-uña, riel-leva del modo guiado, tornillos avellanados AF2, tapones de grafito reales y alcance térmico de placas y disco"],
    ["Alcance de la revisión", "Accionamiento pivotado tipo KIET por defecto (7.2), placa-guía curva (7.3) y su comparación con el diseño original y con el concepto KIET (7.4); guiado con riel-leva como alternativa (7.5, 7.6); tornillos avellanados AF2 (6.3); alternativas de interfaz base, A, B, C1, C2 y C3 (capítulo 9) y escenario solar a 80 °C de placas y disco (capítulo 10). Cubierta de madera W: EN STAND BY, fuera de esta entrega (6.2). Datos faltantes en el capítulo 12 y modificaciones de la Rev. C en el capítulo 15"],
    ["Normas principales", "AISC 360-22 (ASD); ASME BTH-1, Categoría de diseño B (Nd = 3,0); AWS D1.1/D1.1M:2020"],
], widths=(50, 120), size=9.5)
table(["", "Nombre", "Firma", "Fecha"], [["Elaboró", "", "", ""], ["Revisó (ingeniero calculista habilitado)", "", "", ""], ["Aprobó", "", "", ""]], widths=(25, 65, 45, 35), size=9.5)
LEYENDA = ("ESTA MEMORIA DE CÁLCULO ES UN DOCUMENTO EMITIDO PARA REVISIÓN. NO ES VÁLIDA PARA FABRICACIÓN NI PARA MONTAJE HASTA SU REVISIÓN, APROBACIÓN Y FIRMA "
           "POR UN INGENIERO CALCULISTA HABILITADO, QUIEN ASUME LA RESPONSABILIDAD PROFESIONAL DEL CÁLCULO.")
T(LEYENDA, bold=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
T("Todos los valores de esta memoria se generan automáticamente desde el núcleo de cálculo TT300-C; no se transcriben a mano. "
  "Un cambio de parámetros regenera memoria, planos y herramienta con la misma fuente.", italic=True, size=8.5)
doc.add_page_break()

# ================================================================= 1. OBJETO
H("1. Objeto y alcance")
T("Verificar la tornamesa hidráulica TT300-C para el giro de cargas de hasta {0} tf: mesa giratoria soldada tipo cajón, base, pivote central, "
  "pasadores de empuje, accionamiento hidráulico (por defecto, cilindros pivotados tipo KIET con bloque-uña y placas-guía; como alternativa, patines guiados con uña y leva de reenganche), "
  "articulaciones, soldaduras, izaje del equipo y fatiga."
  .format(pint(P["W_tf"])))
table(["Ítem", "Incluido", "Observación"], [
    ["Giro bajo carga (capacidad del accionamiento)", "Sí", "Casos de fricción nominal, diseño, borde, contaminado y seco"],
    ["Cadena de empuje", "Sí", "Verificada a la fuerza de calado (área × presión de alivio)"],
    ["Accionamiento pivotado tipo KIET (por defecto)", "Sí", "7.2: cinemática, empuje guiado, retorno y sincronía, cara del bloque-uña, verificaciones y holguras"],
    ["Placa-guía curva", "Sí", "7.3: inconsistencias del original, construcción G1, segmentos, placas y verificaciones A a D; comparación original / curva / KIET en 7.4"],
    ["Accionamiento guiado con riel-leva (alternativa)", "Sí", "7.5; comparación con el pivotado en 7.6"],
    ["Cubierta de madera W", "No (stand by)", "Decisión del mandante: fuera de esta entrega (6.2; docs/standby/madera_W/LEEME.md)"],
    ["Mesa y base", "Sí", "FEA propio (MITC4 / Q4) más flexión global axisimétrica"],
    ["Izaje del equipo vacío", "Sí", f"4 puntos, factor dinámico {n(P['phi_lift'])}"],
    ["Fatiga", "Sí", f"{pint(P['turns_yr'])} vueltas/año × {pint(P['life'])} años"],
    ["Exposición solar a 80 °C", "Sí, solo placas y disco", "term_alcance = 1 (capítulo 10); cilindros, aceite, sellos, viscosidad/bomba y accionamiento mecánico quedan fuera del escenario"],
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
SEC_CAP = {"Temperatura (exposición solar, 80 °C)": "Capítulo 10 y Anexo B", "Uña de empuje: material y excepción del criterio FU ≤ 0,90": "7.5.5 (modo guiado)",
           "Leva de reenganche positiva (modo guiado)": "7.5", "Accionamiento pivotado tipo KIET": "7.2 y 7.3 (incluye «Placa-guía curva»)", "Valor por defecto del accionamiento (08-11-2026)": "7.2.7 y 7.6",
           "Tornillos avellanados del disco de la mesa (AF2)": "6.3", "Cubierta de madera W (rebaje)": "En stand by (6.2): no se aplica en esta entrega"}
_secs = [ln[3:].strip() for ln in reg if ln.startswith("## ")]
T("El registro tiene además secciones propias, cuyos criterios se transcriben en el capítulo donde se aplican:", size=9, after=1)
table(["Sección de docs/normas/registro.md", "Dónde se aplica"], [[x, SEC_CAP.get(x, "—")] for x in _secs], widths=(110, 60), size=8)


def reg_rows(title, sub=None):
    """Filas de la tabla de una sección «## title» (o de su subsección «### sub») de docs/normas/registro.md (celdas separadas por | sin escapar)."""
    out, on, in_sub = [], False, None
    for ln in reg:
        if ln.startswith("## "):
            on = ln[3:].strip() == title; in_sub = None
            continue
        if ln.startswith("### "):
            in_sub = ln[4:].strip()
            continue
        if on and (in_sub == sub or (sub is not None and in_sub is not None and in_sub.startswith(sub))) and ln.startswith("|") and not ln.startswith("|---"):
            c = [x.strip().replace("\\|", "|") for x in re.split(r"(?<!\\)\|", ln.strip().strip("|"))]
            out.append(c)
    return out[1:] if out else []   # sin la fila de encabezado


def md_table(text, heading):
    """Primera tabla markdown bajo el encabezado (#…) que empieza con `heading`: (encabezados, filas)."""
    lines = text.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("#") and l.lstrip("#").strip().startswith(heading))
    rows = []
    for l in lines[i + 1:]:
        if l.startswith("#"):
            break
        if l.startswith("|"):
            if re.match(r"^\|\s*-", l):
                continue
            rows.append([c.strip().replace("**", "") for c in re.split(r"(?<!\\)\|", l.strip().strip("|"))])
        elif rows:
            break
    return rows[0], rows[1:]


FIGN = [0]


def figure(path, title, width_mm=170):
    """Figura numerada con título (centrada)."""
    FIGN[0] += 1
    doc.add_picture(str(path), width=Mm(width_mm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    T(f"Figura {FIGN[0]}. {title}", italic=True, size=8.5, align=WD_ALIGN_PARAGRAPH.CENTER, after=6)
    return FIGN[0]


# ================================================================= 3. DESCRIPCIÓN
H("3. Descripción del sistema")
table(["Componente", "Descripción"], [
    ["Mesa giratoria (pos 2)", f"Cajón soldado Ø{pint(P['D_top'])} × {pint(P['h_disc'])}: plancha superior e={pint(P['t_top'])}, inferior e={pint(P['t_bot'])}, "
                               f"almas anulares R {', '.join(pint(r) for r in D['almas'])} (e={pint(P['t_web'])}), {pint(P['N_rib'])} nervios e={pint(P['t_rib'])}, anillos de pasadores e={pint(P['t_pr'])}"],
    ["Pasadores de empuje (pos 3)", f"{pint(P['N_pin'])} × Ø{pint(P['d_pin'])} en R{pint(P['R_pin'])}; paso {n(360 / P['N_pin'])}°; Fy ≥ {pint(P['Fy_pin'])} MPa"],
    ["Base (pos 1)", f"Plancha {pint(P['B'])} × {pint(P['B'])} × {pint(P['t_base'])} con marco perimetral, 2 soportes del ojal E en la diagonal, 4 placas-guía y 4 orejas de izaje"],
    ["Pivote (pos 5) y buje (pos 6)", f"Pivote Ø{pint(P['D_piv'])}; buje autolubricado L = {pint(P['L_bush'])}"],
    ["Interfaz de giro", "Acero-acero con grasa grafitada (pos 14) sobre la cara inferior de la mesa"],
    ["Cilindros (pos 9)", f"{pint(P['n_cyl'])} × doble efecto Ø{pint(P['D_bore'])}/Ø{pint(P['d_rod'])}, carrera {pint(P['stroke'])}, clase {pint(P['p_rated'])} psi ({pint(psi_bar)} bar), "
                          f"alivio {pint(P['p_relief'])} bar, alarma {pint(P['p_alarm'])} bar; pivotados sobre pasadores verticales E (Ø{pint(P['pv_dE'])}) en la diagonal, "
                          f"φ_E = {pint(P['pv_phE'])}° y {pint((P['pv_phE'] + 180) % 360)}°, R_E = {pint(PIV['R_E'])} mm"],
    ["Soporte del ojal E", f"Cajón soldado a la base, lado {pint(PIV['soporte_E']['lado_cajon'])} mm, paredes de {pint(PIV['soporte_E']['t_pared'])} mm (sección en U: ventana del ojal hacia la mesa), "
                           f"tapas de {pint(PIV['soporte_E']['t_tapas'])} mm que hacen de orejas del pasador E; filete {pint(PIV['soporte_E']['filete'])} mm; {PIV['fabricacion']['soporte_E']['material']}"],
    ["Bloque-uña y pasador Q", f"Bloque {PIV['fabricacion']['bloque_una']['material']} que gira libre sobre el pasador vertical Q (Ø{pint(PIV['bloque_una']['d_Q'])}) del ojal del vástago; "
                               f"Q a L_qp = {pint(PIV['L_qp'])} mm del centro del pasador tomado; cuerpo {pint(PIV['bloque_una']['b_cuerpo'])} × {pint(PIV['bloque_una']['h'])} acodado e_cr = {pint(PIV['bloque_una']['e_acodado'])} mm hacia afuera "
                               f"para librar el pasador siguiente; cara de empuje {pint(PIV['bloque_una']['b_cara'])} × {pint(PIV['bloque_una']['l_cara'])} cilíndrica convexa R{pint(PIV['bloque_una']['R_cara'])} templada ≥ 55 HRC. El extremo inferior de Q es el seguidor de la placa-guía"],
    ["Placas-guía", f"4 (una por cilindro y sentido de giro), {n(PIV['fabricacion']['placas_leva']['marco']['largo'])} × {n(PIV['fabricacion']['placas_leva']['marco']['ancho'])} × {pint(PIV['placa_leva']['t'])} mm, {PIV['fabricacion']['placas_leva']['material'].split(',')[0]}, "
                    f"empernadas a la base fuera de la mesa ({pint(PIV['placa_leva']['n_pernos'])} × {PIV['fabricacion']['placas_leva']['pernos']['norma'].split(' (')[0]} {PIV['fabricacion']['placas_leva']['pernos']['clase']} y 2 pasadores de posición por placa); "
                    f"recorte en media luna con canto curvo G1: flanco recto a {n(PIV['placa_leva']['alpha_deg'])}° y arcos tangentes, bolsillo de {n(PIV['placa_leva']['bolsillo_w'])} mm; contacto {PIV['placa_leva']['familia_nombre']}"],
    ["Alternativa: patín guiado con leva de reenganche (drive_mode = 1)", f"Patín {pint(GUM['K']['L_s'])} × {pint(P['w_s'])} coaxial con el cilindro en x = ±{pint(P['x_g'])} sobre bancada con ranura T; uña {pint(P['dog_b'])} × {pint(P['dog_h'])} con chaflán de retorno a {pint(P['beta_ch'])}° y resorte; "
     f"riel-leva fijo sobre el patín en pórticos de dos patas y seguidor de rodillo Ø{pint(P['cam_df'])} (7.5)"],
], widths=(48, 122), size=8.5)
T("Funcionamiento (modo pivotado, por defecto): los dos cilindros, en ojales opuestos de la diagonal, trabajan en par (par puro sobre la mesa; sus componentes radiales se anulan en el pivote). "
  f"En cada carrera el bloque-uña, libre en Q, empuja el pasador tomado con Q apoyado en el canto de la placa-guía (empuje guiado): la mesa gira un paso ({n(360 / P['N_pin'])}°). Al retraer, el extremo inferior de Q corre por el canto curvo: "
  "el bolsillo deja salir el bloque hacia afuera para pasar sobre el pasador siguiente y el flanco recto del extremo retraído lo devuelve a la posición de toma detrás de él. "
  "Para invertir el sentido de giro, cada cilindro pivota en su mismo ojal hacia el otro lado de la diagonal (imagen especular) y trabaja con la otra placa-guía; no se trasladan cilindros.")

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
    ["Planchas de mesa y base; cajón del ojal E (verificado con Fy del acero estructural)", "ASTM A572 Gr.50; cajón " + PIV["fabricacion"]["soporte_E"]["material"], pint(P["Fy"])],
    ["Pasadores de empuje (pos 3)", "34CrNiMo6+QT (EN 10083-3); zona de contacto templada por inducción ≥ 55 HRC", pint(P["Fy_pin"])],
    ["Bloque-uña (modo pivotado) y uña (modo guiado)", "34CrNiMo6+QT, certificado 3.1 (EN 10083-3, Re ≥ 800 para 40 < t ≤ 100 mm); cara de empuje templada por inducción ≥ 55 HRC", pint(P["Fy_dog"])],
    ["Superficies de contacto uña–pasador y canto de la placa-guía o del riel", "Temple por inducción", pint(P["Fy_surf"])],
    ["Pasadores verticales E y Q (modo pivotado); pasadores de articulación (modo guiado)", "42CrMo4+QT", pint(P["Fy_pp"])],
    ["Placas-guía (modo pivotado)", PIV["fabricacion"]["placas_leva"]["material"] + f"; Fu = {pint(P['Fu_camP'])} MPa", pint(P["Fy_camP"])],
    ["Tornillos de las placas-guía", f"{PIV['fabricacion']['placas_leva']['pernos']['norma'].split(' (')[0]}, ISO 898-1 clase {PIV['fabricacion']['placas_leva']['pernos']['clase']}, Fu = {pint(P['pv_Fub'])} MPa", "—"],
    ["Pernos del riel-leva y de sus pórticos (modo guiado)", f"ISO 898-1 clase 10.9 (≈ AISC 360-22 grupo 150), Fu = {pint(P['Fu_bolt'])} MPa", "—"],
    ["Vástago del cilindro", "Acero templado y cromado: HIPÓTESIS hasta la ficha del proveedor (capítulo 12)", pint(P["pv_Fyrod"])],
    ["Patín (solo modo guiado)", "S460 o 34CrNiMo6+QT", pint(P["Fy_shoe"])],
    ["Riel-leva y pórticos (solo modo guiado)", f"42CrMo4+QT (EN 10083-3, 16 < t ≤ 40 mm); canto templado ≥ 55 HRC; Fu = {pint(P['Fu_cam'])} MPa", pint(P["Fy_cam"])],
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
    if re.search(r"[Mm]adera", g["titulo"]):
        T(g["titulo"] + ": grupo de parámetros de la cubierta W, en stand by (6.2); no se lista.", italic=True, size=8.5, after=2)
        continue
    rows = [[p["lab"], p["id"], (P[p["id"]] if isinstance(P[p["id"]], str) else n(P[p["id"]], 4)), p["u"]] for p in g["p"]]
    T(g["titulo"], bold=True, size=9, after=1)
    table(["Parámetro", "Id", "Valor", "Unidad"], rows, widths=(100, 25, 25, 20), size=7.5, num_cols=(2,))

# ================================================================= 5. MASAS
H("5. Masas")
mg = GUM["masas"]
assert abs(m["total"] - PVM["masa"]) < 1e-6 and abs(mg["total"] - GUM["masa"]) < 1e-6, "masas del modo por defecto distintas entre exportadores"
MD_P, MD_G = D["derivados"]["masas_desc"], GUM["masas_desc"]
T(f"Hipótesis: masas del núcleo (ρ·V de cada pieza) para la interfaz base. Columna principal: modo pivotado tipo KIET (por defecto, drive_mode = {pint(P['drive_mode'])}); "
  "columna de comparación: modo guiado con leva de reenganche positiva (drive_mode = 1, opt_cam = 1). Las filas que cambian con el modo se describen con el texto del núcleo.", size=9)
mrows = [["Plancha superior", "top"], ["Plancha inferior", "bot"], ["Almas anulares", "webs"], ["Nervios radiales", "ribs"], ["Cubo", "hub"], ["Pasadores de empuje", "pins"],
         ["Subtotal mesa", "disc"], ["Plancha base (con collar y orejas de izaje)", "base"], ["Marco perimetral", "rim"], ["brackets", "brackets"], ["beds", "beds"], ["shoes", "shoes"],
         ["dogs", "dogs"], ["cam", "cam"], ["Pivote", "pivot"], ["Cilindros", "cyl"], ["TOTAL", "total"]]
_cap = lambda t: t[0].upper() + t[1:]
_lab = lambda k, lab: ((f"Guiado: {MD_G[k]}" if MD_P[k].startswith("—") else f"{_cap(MD_P[k])} / guiado: {MD_G[k]}") if k in MD_P else lab)
table(["Componente (pivotado / guiado)", "Pivotado (kg)", "Guiado con leva (kg)"],
      [[_lab(k, a), n(m[k], 4) if m[k] else "—", n(mg[k], 4) if mg[k] else "—"] for a, k in mrows], widths=(110, 30, 30), num_cols=(1, 2), size=8.5)
T(f"Resultado: masa total {n(m['total'], 5, 'kg')} con el modo pivotado y {n(mg['total'], 5, 'kg')} con el guiado con leva ({n(mg['total'] - m['total'], 3, 'kg')} más). "
  "La mesa, la base y el pivote son iguales en los dos modos; la diferencia está en el accionamiento (patines, bancadas, ménsulas y riel-leva con pórticos frente a cajones del ojal E, bloques-uña y placas-guía).", bold=True, size=9)
if M3:
    M3m = M3["masas"]
    T(f"Control: las masas se recalculan sobre el modelo 3D (CadQuery). Diferencia 3D frente al núcleo (masa comparable {n(M3m['total_nucleo'])} kg): {n(M3m['dif_pct'])} % (tolerancia {n(M3m['tol_pct'])} %). "
      f"Masa del ensamble con piezas fuera del núcleo (pernos, buje, tapas, pasadores): {n(M3['masa_total_ensamble'])} kg.", size=9)
else:
    T("Control 3D de masas: lo hace el generador de planos sobre el modelo 3D de cada juego generado a pedido (informe_paquete.md y TT300-C_masas3d.json del juego, tolerancia 0,5 %); "
      "no hay en esta carpeta un modelo 3D del diseño por defecto actual, de modo que la memoria no lo repite.", size=9)

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
        out.append([c["nombre"], c["formula"], nd(c["dem"], c["unidad"]), "—" if c.get("cap") is None else nd(c["cap"], c["unidad"]), c["unidad"], "—" if info or c.get("fu") is None else fu3(c["fu"]), EST.get(c["estado"], c["estado"]), c["ref"]])
    return out
T("Verificaciones de la opción A (los discos de la opción B tienen las mismas, con q levemente mayor por el peso del disco y la lámina):", size=9, after=1)
table(["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"], ifrows(D["interfazChecks"]["A"]),
      widths=(38, 42, 12, 12, 10, 12, 13, 31), size=6.5, num_cols=(2, 3, 5))
T("Verificaciones adicionales de la opción B (lámina de UHMW):", size=9, after=1)
table(["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"], ifrows(D["interfazChecks"]["B"], ("UHMW", "Masa agregada", "Altura")),
      widths=(38, 42, 12, 12, 10, 12, 13, 31), size=6.5, num_cols=(2, 3, 5))
_g1 = TPA["C1"]["geom"]
T("Opción C. La placa de bronce con tapones de grafito va fija a la base y desliza contra un disco duro (≥ 100 HB sobre el bronce) fijo a la mesa; el desgaste queda en el bronce, que se reemplaza. "
  "Espesor: t_flex = a·√(0,75q_loc/(0,6Fy_bz)); t_req = t_flex/√η + sobreespesor, con η = (p − d)/p = {0} por los tapones de grafito. "
  "La fracción de grafito que usa el cálculo es la REAL (bz_fg_modo = {1}): f_g = N_real·π·d²/(4·A_contacto) = {2} con los {3} tapones que caben, frente a {4} de la malla ideal sobre toda la corona; "
  "la diferencia, su efecto y los criterios de lubricación están en 9.7. La configuración 3 (pastillas) cubre {5} del área y concentra la presión local en 1/cobertura.".format(
      n(_g1["eta"]), pint(P["bz_fg_modo"]), n(_g1["fg_real"]), pint(_g1["N_real"]), n(_g1["fg_ideal"]), n(P["bz_cover"])), size=9)
T("Verificaciones de la opción C (bronce con tapones de grafito):", size=9, after=1)
table(["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"], ifrows(D["interfazChecks"]["C"]),
      widths=(38, 42, 12, 12, 10, 12, 13, 31), size=6.5, num_cols=(2, 3, 5))
T("Conclusión. Con los datos de entrada, cada disco inoxidable debe tener {0} (requerido {1}; espesor comercial inmediato) y la lámina de UHMW de la opción B {2} (requerido {3}). "
  "La opción A agrega {4} de masa total y {5} de altura; la B, {6} y {7}. Con los μ de diseño adoptados la fuerza por cilindro es {8} (A) y {9} (B), frente a {10} con acero–acero: "
  "la ventaja de B aparece en la operación normal (μ nominal {11} frente a {12}) y en la protección contra la corrosión y el gripado, no en el caso de diseño, que supone la película de grasa expulsada.".format(
      n(IF[1]["tss"], unit="mm"), n(IF[1]["tssReq"], unit="mm"), n(IF[2]["tuh"], unit="mm"), n(IF[2]["tuhReq"], unit="mm"),
      n(IF[1]["dTot"], unit="kg"), n(IF[1]["delta"], unit="mm"), n(IF[2]["dTot"], unit="kg"), n(IF[2]["delta"], unit="mm"),
      n(IF[1]["F"], unit="kN"), n(IF[2]["F"], unit="kN"), n(IF[0]["F"], unit="kN"), n(P["muB_nom"]), n(P["mu_nom"])), bold=True, size=9)

# ---- 6.2 cubierta de madera W: EN STAND BY
assert not any(a_.get("madera") for a_ in ALT["alternativas"]), "la variante W está en stand by: exportar sin TT_CON_MADERA"
STANDBY_W = ("Cubierta de madera W: EN STAND BY por decisión del mandante (09-11-2026). La variante W (plancha rebajada con tablones enrasados) queda fuera de esta entrega Rev. C: "
             "no se desarrolla en esta memoria, no figura en las tablas comparativas de alternativas ni en el escenario solar, y su estado, supuestos pendientes y forma de retomarla están en "
             "docs/standby/madera_W/LEEME.md.")
H("6.2 Cubierta de madera W", 2)
T(STANDBY_W, bold=True, size=9.5)

# ---- 6.3 AF2: tornillos avellanados del disco de la mesa
AF2 = ACC["af2"]; TOR = AF2["tornillos"]
H("6.3 Opción A pegada (AF2): tornillos avellanados del disco de la mesa", 2)
T("Hipótesis. Decisión del mandante del 08-11-2026: en la opción A con fijación permanente (opt_ss = 1, fix_mode = 2, «AF2») el par de la interfaz pasa del disco inoxidable de la mesa "
  "a la plancha inferior de la mesa con tornillos avellanados ISO 10642 clase 10.9, roscados en la plancha. El núcleo elige el número n como el menor múltiplo del número de ranuras radiales de engrase "
  "con FU ≤ 0,85 y el radio r entre la ranura circunferencial exterior y el borde (cabeza a 5 mm de la ranura). Datos de TT.designDrive (clave tornillos_interfaz), modo pivotado por defecto.", size=9)
table(["Dato", "Valor", "Fuente"], [
    ["Designación", TOR["designacion"], "ISO 10642; registro, «Tornillos avellanados del disco de la mesa (AF2)»"],
    ["Número y radio", f"{pint(TOR['n'])} tornillos en R{pint(TOR['r'])} (PCD {pint(TOR['PCD'])} mm), a {n(TOR['angulos_deg'][0])}° + k·{n(360 / TOR['n'])}°, entre las ranuras radiales", "Núcleo (n automático, FU ≤ 0,85)"],
    ["Avellanado en la cara de deslizamiento del disco de la mesa", f"Ø{pint(TOR['avellanado']['d_cabeza'])} × {pint(TOR['avellanado']['angulo_deg'])}°, profundidad k = {n(TOR['avellanado']['prof'])} mm; cabeza {n(TOR['avellanado']['bajo_cara'])} mm bajo la cara", "ISO 10642 (k máx.)"],
    ["Rosca en la plancha inferior de la mesa", f"M{pint(TOR['rosca_en_mesa']['d'])} × {n(TOR['rosca_en_mesa']['paso'])}, pasante en t = {pint(TOR['t_plancha_mesa'])} mm, broca Ø{n(TOR['rosca_en_mesa']['d_broca'])}", "VDI 2230 (orientativo)"],
    ["Fuerza por tornillo", f"V = T_dis/(n·r) = {n(TOR['V_por_tornillo_kN'], unit='kN')}", "Equilibrio"],
    ["Fu del disco / de la plancha", f"{pint(P['Fu_ss'])} / {pint(P['Fu'])} MPa", "ASTM A240 304; ASTM A572 Gr.50"],
], widths=(55, 70, 45), size=8)
T("Desarrollo. Criterios del registro (docs/normas/registro.md, «Tornillos avellanados del disco de la mesa (AF2)»):", bold=True, size=9, after=1)
table(["Verificación", "Criterio", "Referencia", "Nota"], reg_rows("Tornillos avellanados del disco de la mesa (AF2)"), widths=(32, 55, 45, 38), size=7.5)
T("Resultado.", bold=True, size=9.5, after=1)
table(["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"], ifrows(AF2["filas"]),
      widths=(36, 44, 12, 12, 10, 10, 12, 34), size=6.5, num_cols=(2, 3, 5))
COM = (3, 4, 5, 6, 8, 10, 12, 15, 20, 25)     # espesores comerciales ASTM A240 (lista de 6.1)
t_flex_com = next(t for t in COM if t >= AF2["tss2Req"] - 1e-9)
_cab = next(c for c in AF2["filas"] if "cabeza avellanada dentro del espesor" in c["nombre"])
_fu = max(c["fu"] for c in AF2["filas"] if c.get("fu") is not None)
_fun = next(c["nombre"] for c in AF2["filas"] if c.get("fu") == _fu)
assert AF2["tss2"] > t_flex_com, "AF2: el disco de la mesa ya no lo fija la cabeza avellanada; revisar el texto"
T(f"Resultado: los {pint(TOR['n'])} tornillos {TOR['designacion']} en R{pint(TOR['r'])} cumplen todas las verificaciones (FU máximo {fu3(_fu)}: {_fun[6:].lower() if _fun.startswith('AF2 · ') else _fun}). "
  f"El disco inoxidable de la mesa pasa de {pint(t_flex_com)} a {pint(AF2['tss2'])} mm: por flexión sobre el vacío local basta t_req = {n(AF2['tss2Req'])} mm (comercial {pint(t_flex_com)} mm), "
  f"pero la cabeza avellanada exige k + 0,5 + sobreespesor = {n(_cab['dem'])} mm ≤ t, lo que lleva al comercial de {pint(AF2['tss2'])} mm. El disco de la base queda en {pint(AF2['tss'])} mm. "
  f"Masa total de AF2 con el modo pivotado: {n(AF2['masa'], 5, 'kg')}; FS de giro {n(AF2['FS'])}.", bold=True, size=9)

# ================================================================= 7. ACCIONAMIENTO
assert D["modo"] == 2 and P["drive_mode"] == 2 and PVM["drive_mode"] == 2 and GUM["drive_mode"] == 1, "la memoria está redactada con el modo pivotado por defecto"
assert abs(PVM["cd"]["F"] - cd["F"]) < 1e-9, "exportadores con resultados distintos del modo pivotado"
VG = GUM["verificaciones"]                                   # verificaciones del modo guiado con leva (mismo formato que VER)
VH = ["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"]
VW = (33, 41, 14, 14, 12, 11, 14, 31)


def vres(L):
    """Frase de resultado de un bloque de verificaciones (cuenta estados y nombra la de mayor FU)."""
    fu = [c for c in L if c["estado"] not in ("info",) and c.get("fu") is not None]
    if not fu:
        return "Resultado: filas informativas, sin criterio de aceptación."
    k = {s_: sum(1 for c in fu if c["estado"] == s_) for s_ in ("ok", "warn", "fail", "pend")}
    g = max(fu, key=lambda c: c["fu"])
    est = "todas cumplen" if k["ok"] == len(fu) else f"{k['ok']} cumplen, {k['warn']} con advertencia, {k['fail']} no cumplen" + (f", {k['pend']} pendientes" if k["pend"] else "")
    return f"Resultado: {len(fu)} verificaciones con criterio, {est}; FU máximo {fu3(g['fu'])} ({g['nombre'][0].lower() + g['nombre'][1:]})."


def vblock(titulo, hip, L, nota=""):
    T(titulo, bold=True, size=9.5, after=1)
    T("Hipótesis. " + hip[0].upper() + hip[1:], size=9)
    table(VH, ifrows(L), widths=VW, size=6.5, num_cols=(2, 3, 5))
    T(vres(L) + (" " + nota if nota else ""), bold=True, size=9)


def pick(L, grp=None, rx=None):
    return [c for c in L if (grp is None or c["grp"] == grp) and (rx is None or re.search(rx, c["nombre"]))]


H("7. Accionamiento")
T(f"Decisión del mandante del 08-11-2026: el accionamiento por defecto es el modo pivotado tipo KIET (drive_mode = {pint(P['drive_mode'])}, apartado 7.2) con la placa-guía curva del 09-11-2026 (7.3) y su comparación con el diseño original y con KIET (7.4); el modo guiado con riel-leva de reenganche positiva "
  "(drive_mode = 1, opt_cam = 1) queda como alternativa (7.5). La comparación de ambos modos está en 7.6. Los apartados 7.1 y 7.7 a 7.9 (par, casos de fricción, clase de presión, bomba y control) "
  "se presentan con el modo por defecto. Todos los valores salen de TT.analyze (tools/export_design.js y tools/export_alternativas.js, clave accionamiento).", size=9)

H("7.1 Par resistente y casos de fricción (modo por defecto)", 2)
T(f"Hipótesis: casos de fricción de 4.3; {pint(P['n_cyl'])} cilindros en par simétrico; fuerza de calado F_calado = A·p_alivio = {n(DV['Fstall'], unit='kN')}; FS_mín = {n(P['FS_min'])}.", size=9)
table(["Ecuación", "Expresión", "Referencia"], [
    ["Par resistente", "T(μ, r) = μ·N·r + T_piv(μ)", "Equilibrio de momentos respecto del eje del pivote"],
    ["Fuerza de calado por cilindro", "F_calado = A·p_alivio", "ISO 4413:2010 (protección contra sobrepresión); registro, «Presión nominal del cilindro»"],
    ["Factor de seguridad del giro", "FS = F_calado/F_dis ≥ FS_mín; gira si F(μ_cont) ≤ F_calado y F(μ_d, R) ≤ F_calado", "Criterio del proyecto (registro, «Giro»); revisión independiente M1"],
], widths=(45, 75, 50), size=8)
table(["Caso", "μ", "r (mm)", "T (kN·m)", "F_cil (kN)", "p (bar)", "FS al calado", "¿Gira?"],
      [[c["nombre"], n(c["mu"]), n(c["r"]), n(c["T"]), n(c["F"]), n(c["p"]), fu3(c["FS"]), "Sí" if c["gira"] else "NO"] for c in DV["casos"]],
      widths=(52, 12, 16, 18, 18, 16, 20, 14), size=8, num_cols=(1, 2, 3, 4, 5, 6))
T(f"Resultado: en el caso de diseño F_cil = {n(cd['F'], unit='kN')} a {n(cd['p'], unit='bar')}; FS = F_calado/F_dis = {fu3(cd['FS'])} ≥ FS_mín = {n(P['FS_min'])}. "
  f"μ máximo que gira con r_ef: {n(DV['muMax_ref'])}. El caso seco es referencial (no es condición de operación).", bold=True, size=9)

# ---------------------------------------------------------------- 7.2 PIVOTADO
H("7.2 Accionamiento pivotado tipo KIET (por defecto, drive_mode = 2)", 2)
SE, BU, PL_ = PIV["soporte_E"], PIV["bloque_una"], PIV["placa_leva"]
SUG = PIV["sugerencia"]
CIN = PIV["cinematica"]
FAB = PIV["fabricacion"]
FPL = FAB["placas_leva"]
GKD = ROOT / "docs" / "qa" / "guia_curva_KIET"
CAMB = (GKD / "cambios.md").read_text(encoding="utf-8")
ORIG = json.load(open(GKD / "original_b928552.json", encoding="utf-8"))
c1 = lambda x: f"{x:,.1f}".replace(",", "§").replace(".", ",").replace("§", ".")          # cotas de fabricación al 0,1 mm
pt = lambda p: f"({c1(p[0])}; {c1(p[1])})"
deg = lambda r: r * 180 / math.pi
VPIV = {}                                                                                   # filas del modo pivotado ya presentadas en el capítulo 7


def take(rx, grp=None, opt=False):
    """Filas de VER cuyo nombre calza con rx (y grupo), sin repetir las ya presentadas en 7.2–7.3."""
    out = [c for c in VER if (grp is None or c["grp"] == grp) and re.search(rx, c["nombre"]) and id(c) not in VPIV]
    for c in out:
        VPIV[id(c)] = c
    assert out or opt, f"sin filas del núcleo para «{rx}»"
    return out


H("7.2.1 Hipótesis y geometría", 3)
table(["Hipótesis", "Valor adoptado (núcleo)", "Origen"], [
    ["Ojales traseros E", f"{pint(P['n_cyl'])} pasadores verticales Ø{pint(P['pv_dE'])} fijos a la base en la diagonal: φ_E = {pint(P['pv_phE'])}° y {pint((P['pv_phE'] + 180) % 360)}°; "
     f"R_E = {pint(PIV['R_E'])} mm; E₁ = {pt(PIV['E'])} mm", "Concepto KIET-1024-REF-TT-400T (disposición, no dimensiones); parámetros pv_RE y pv_phE"],
    ["Distancia Q → centro del pasador tomado", f"L_qp = {pint(PIV['L_qp'])} mm (sugerencia del núcleo {pint(SUG['Lqp'])} mm con R_E = {pint(SUG['RE'])} mm; se adoptan 2 mm de margen sobre la holgura con el pasador siguiente)",
     "Sugerencia de E (malla 10 mm y 1 mm); parámetro pv_Lqp"],
    ["Bloque-uña", f"Libre en Q (gira sobre el pasador vertical Q Ø{pint(BU['d_Q'])}); cuerpo {pint(BU['b_cuerpo'])} × {pint(BU['h'])} mm acodado e_cr = {pint(BU['e_acodado'])} mm hacia afuera; "
     f"cara de empuje {pint(BU['b_cara'])} × {pint(BU['l_cara'])} mm cilíndrica convexa en planta R{pint(BU['R_cara'])}, templada ≥ 55 HRC; horquilla de {pint(BU['t_horquilla'])} mm en Q", "Registro, «Cara del bloque-uña»; 7.2.5"],
    ["Seguidor", f"Extremo inferior del pasador Q (r_f = d_Q/2 = {n(BU['d_Q'] / 2)} mm, voladizo {n(BU['voladizo_leva'])} mm bajo la horquilla) apoyado en el canto de la placa-guía", "Geometría del modo 2"],
    ["Placas-guía", f"4 (una por cilindro y sentido de giro), t = {pint(PL_['t'])} mm, sobre la base y fuera de la mesa; recorte en media luna con canto curvo G1 (7.3)", "La mesa apoya sobre la base hasta R_o: no hay lugar bajo ella"],
    ["Soporte del ojal E", f"Cajón {pint(SE['lado_cajon'])} × {pint(SE['lado_cajon'])} mm, paredes de {pint(SE['t_pared'])} mm, alto {pint(SE['alto'])} mm, sección resistente en U (ventana del ojal hacia la mesa); "
     f"tapas de {pint(SE['t_tapas'])} mm; filete {pint(SE['filete'])} mm; {FAB['soporte_E']['material']}", "Registro, «Soporte del ojal E»"],
    ["Inversión del sentido de giro", "El cilindro pivota en el mismo ojal hacia el otro lado de la diagonal (imagen especular respecto de O–E) y trabaja con la otra placa-guía; no se trasladan cilindros", "Concepto KIET"],
    ["Roce", f"μ_s (cara–pasador) = {n(P['mu_s'])}; μ_leva (seguidor–canto) = {n(PL_['mu'])} ({PL_['familia_nombre']}); μ_E = μ_Q = {n(P['pv_muE'])}; η_c = {n(P['eta_c'])}", "Parámetros; familia automática (7.3.6)"],
    ["Cilindro", f"Ø{pint(P['D_bore'])}/Ø{pint(P['d_rod'])} × {pint(P['stroke'])} mm, L0 = {pint(P['L0'])} mm, s_libre = {pint(P['s_free'])} mm; alivio {pint(P['p_relief'])} bar, alarma {pint(P['p_alarm'])} bar, retorno {pint(P['p_ret'])} bar",
     "Parámetros; datos del proveedor por confirmar (capítulo 12)"],
    ["Base", f"B = {pint(P['B'])} mm (lado), marco de {pint(P['rim_t'])} mm", "Decisión del mandante (7.2.7)"],
], widths=(34, 92, 44), size=7.5)
T("Criterios aplicados (docs/normas/registro.md, «Accionamiento pivotado tipo KIET»):", size=9, after=1)
table(["Verificación", "Criterio", "Referencia", "Ecuación / nota"], reg_rows("Accionamiento pivotado tipo KIET"), widths=(28, 60, 36, 46), size=6.5)

H("7.2.2 Ecuaciones de la cinemática y del empuje", 3)
T("Hipótesis. El cilindro es un miembro biarticulado (pasadores verticales E y Q). El bloque-uña, libre en Q, transmite la fuerza al pasador tomado P. La rodilla E–Q–P es inestable en compresión "
  "(rigidez lateral −F·(1/L + 1/L_qp)) y el roce de la cara la empuja hacia afuera: en todo el empuje Q queda apoyado en el canto de la placa-guía (empuje guiado). "
  "La cinemática colineal E–Q–P se conserva como referencia.", size=9)
table(["N°", "Magnitud", "Ecuación", "Norma o referencia"], [
    ["(1)", "Posición de Q (colineal, referencia)", "Q = P + L_qp·(E − P)/|E − P|", "Estática del miembro de dos fuerzas; registro, «Cinemática»"],
    ["(2)", "Largo del cilindro", "L = |P − E| − L_qp;  toma en L(θ_ini) = L0 + s_libre", "Geometría; registro, «Cinemática»"],
    ["(3)", "Brazo geométrico", "a = (P × u)_z = dL/dθ,  u = (P − E)/|P − E|", "Potencia virtual: F·dL = T·dθ"],
    ["(4)", "Empuje guiado (Q en el canto)", "|P(θ) − Q| = L_qp con Q sobre la trayectoria del seguidor W(L)", "Geometría; registro, «Placa-guía curva»"],
    ["(5)", "Equilibrio del pasador Q", "F·u_c + H·(n − μ_leva·t) = F_n·b′;  b′ = Q→P girada asin(r·sen(atan μ_s)/L_qp) hacia la mesa", "Equilibrio con el círculo de rozamiento; registro, «Fuerza del cilindro»"],
    ["(6)", "Par por cilindro", "T/n = F_n·(Q × b′)_z", "Equilibrio de momentos respecto de O"],
    ["(7)", "Fuerza del cilindro", "F_cil(θ) = F/η_c;  F_dis = máx_θ F_cil(θ) con μ_d y r_ef", "Registro, «Fuerza del cilindro»"],
    ["(8)", "Presión", "p = F_cil/A,  A = π·D²/4 (p en bar = 10·F[N]/A[mm²])", "Hidráulica"],
    ["(9)", "Factor de seguridad del giro", "FS = F_calado/F_dis ≥ FS_mín,  F_calado = A·p_alivio", "Criterio del proyecto; ISO 4413:2010 (sobrepresión)"],
    ["(10)", "Carrera requerida", "s_req = L(θ_fin) − L0 + margen ≤ carrera", "Cinemática"],
    ["(11)", "Control", "Potencia virtual con diferencias finitas de L, deslizamiento y roce del canto", "Revisor cruzado (Anexo A); tests/indep_pivotado.py"],
], widths=(10, 40, 76, 44), size=7.5)
FST, A_ = DV["Fstall"], DV["A"]
table(["Magnitud", "Valor (núcleo)", "Ecuación"], [
    ["θ de toma / θ final (paso)", f"{n(PIV['theta_ini_deg'] - 360)}° / {n(PIV['theta_fin_deg'] - 360)}° ({n(360 / P['N_pin'])}°)", "(2)"],
    ["Brazo geométrico mínimo / máximo", f"{n(PIV['brazo_min'])} / {n(PIV['brazo_max'])} mm", "(3)"],
    ["Brazo efectivo mínimo (colineal)", n(PIV["brazo_ef_min"], unit="mm"), "(3) con el roce de la cara"],
    ["Área del émbolo / fuerza de calado", f"{pint(A_)} mm² / {n(FST, unit='kN')}", "(8), (9)"],
    ["F_dis (empuje guiado) / colineal", f"{n(cd['F'], unit='kN')} / {n(max(c['F_cil_colineal'] for c in CIN), unit='kN')} (relación máxima en la carrera {n(PL_['relacion_F_guiado_colineal_max'])})", "(5)–(7)"],
    ["Presión de diseño", n(cd["p"], unit="bar"), "(8)"],
    ["FS de diseño", f"{fu3(cd['FS'])} ≥ {n(P['FS_min'])}", "(9)"],
    ["Carrera requerida (guiado / colineal)", f"{n(PIV['carrera_req'])} / {n(PIV['carrera_req_colineal'])} mm de {pint(P['stroke'])} mm", "(10)"],
], widths=(60, 80, 30), size=8)
T(f"Resultado: F_dis = {n(cd['F'], unit='kN')} a {n(cd['p'], unit='bar')}; FS = {fu3(cd['FS'])} ≥ {n(P['FS_min'])}; carrera requerida {n(PIV['carrera_req'])} mm ≤ {pint(P['stroke'])} mm. "
  f"El empuje guiado pide hasta {n((PL_['relacion_F_guiado_colineal_max'] - 1) * 100)} % más fuerza que la cinemática colineal.", bold=True, size=9)

H("7.2.3 Tabla cinemática: casos de fricción y posiciones a lo largo del empuje", 3)
assert abs(max(c["F_cil"] for c in CIN) - cd["F"]) < 1e-6 * cd["F"], "F_dis distinta del máximo de la cinemática"
T("Hipótesis: los 5 casos de fricción de 4.3 con la cinemática del empuje guiado; ecuaciones (2) a (10) de 7.2.2. La carrera requerida es geométrica y no depende del caso.", size=9)
table(["Caso", "μ", "r (mm)", "T (kN·m)", "F_cil (kN)", "p (bar)", "FS al calado", "Carrera req. (mm)", "¿Gira?"],
      [[c["nombre"], n(c["mu"]), n(c["r"]), n(c["T"]), n(c["F"]), n(c["p"]), fu3(c["FS"]), n(PIV["carrera_req"]), "Sí" if c["gira"] else "NO"] for c in DV["casos"]],
      widths=(44, 12, 14, 15, 15, 14, 18, 20, 12), size=7.5, num_cols=(1, 2, 3, 4, 5, 6, 7))
idx = sorted(set(list(range(0, len(CIN), 6)) + [len(CIN) - 1]))
T("Posiciones del empuje (caso de diseño, cilindro 1, giro antihorario):", size=9, after=1)
table(["θ (°)", "L (mm)", "s (mm)", "Q (mm)", "w (mm)", "Sep. colineal (mm)", "φ (°)", "a (mm)", "F_cil (kN)", "F colineal (kN)", "F_n (kN)", "H guía (kN)", "p (bar)"],
      [[n(c["th"], 5), n(c["L"]), n(c["s"]), pt(PIV["posiciones"]["1_antihorario"]["Q"][i]), n(c["w"]), n(c["separacion_colineal"]), n(c["phi_presion_deg"]), n(c["a"]),
        n(c["F_cil"]), n(c["F_cil_colineal"]), n(c["F_n"]), n(c["F_leva"]), n(c["p"])] for i, c in ((i, CIN[i]) for i in idx)],
      widths=(13, 12, 11, 24, 10, 13, 10, 12, 13, 13, 12, 12, 12), size=6.5, num_cols=tuple(i for i in range(13) if i != 3))
T("w: desplazamiento lateral de Q hacia afuera respecto de la recta E–P al inicio; sep. colineal: distancia de Q a su posición colineal; φ: ángulo de presión del canto en Q; F_n: fuerza normal cara–pasador; "
  f"H guía: reacción de la placa-guía sobre Q. Resultado: la fuerza máxima {n(cd['F'], unit='kN')} coincide con el caso de diseño; φ ≤ {n(max(c['phi_presion_deg'] for c in CIN))}° en todo el empuje.", size=9)

H("7.2.4 Retorno y sincronía", 3)
RET = PL_["retorno"]; PC = PL_["primer_contacto"]; FN_ = PL_["fuerzas_N"]
T("Hipótesis. La mesa queda detenida en θ_fin; al retraer, Q conserva ψ salvo que el pasador siguiente B lo empuje hacia afuera (holgura 0) y, desde el primer contacto con el canto, la placa-guía lo conduce "
  "por el flanco hasta el nivel de toma w = c en L0. Margen de sincronía m + δ, con δ = tolerancia de posición del canto (pv_tolg) + α·ΔT·R_pin (mesa a 80 °C, EN 1993-1-2 §3.4.1.1). "
  "Bloque alineado con el vástago en el retorno (hipótesis conservadora).", size=9)
table(["N°", "Magnitud", "Ecuación", "Valor (núcleo)", "Norma o referencia"], [
    ["(12)", "Margen exigido", "m + δ;  δ = pv_tolg + α·ΔT·R_pin", f"{n(PL_['margen_sincronia'])} + {n(PL_['tolerancias_mm'])} = {n(PL_['margen_diseno'])} mm", "Registro, «Requisitos de la trayectoria»; EN 1993-1-2 §3.4.1.1"],
    ["(13)", "Sincronía nominal", "mín holgura bloque–B ≥ m + δ en la conducción final", f"{n(PL_['sincronia'])} mm ≥ {n(PL_['margen_diseno'])} mm", "Geometría (polígono del bloque frente al círculo de B)"],
    ["(14)", "Sincronía en el peor caso", "nominal − δ ≥ m", f"{n(PL_['sincronia_peor'])} mm ≥ {n(PL_['margen_sincronia'])} mm", "Geometría"],
    ["(15)", "Primer contacto de la conducción", "L₁, w₁, φ₁", f"L₁ = {n(PC['L'])} mm, w₁ = {n(PC['w'])} mm, φ₁ = {n(PC['phi'])}°", "Geometría"],
    ["(16)", "Atasco del retorno", "N = F_ret/sen φ₁,  F_ret = A_anular·p_ret", f"N = {n(DV['Fret'])}/sen {n(PC['phi'])}° = {n(FN_['rampa_atasco'] / 1e3)} kN", "Equilibrio (cota sin roce)"],
    ["(17)", "Sin autobloqueo", "μ_E·d_E/(2·L0)·(sen φ + μ·cos φ) < cos φ − μ·sen φ en cada punto", "ver tabla siguiente", "Equilibrio con fricción; registro"],
], widths=(10, 32, 52, 44, 32), size=7)
ir = sorted(set(list(range(0, len(RET), max(1, len(RET) // 10))) + [len(RET) - 1]))
table(["L (mm)", "W centro del seguidor (mm)", "Holgura bloque–B (mm)", "φ (°)", "¿Conducido por el canto?"],
      [[n(RET[i]["L"]), n(RET[i]["W"]), "0 (en contacto con B)" if abs(RET[i]["holgura"]) < 1e-3 else n(RET[i]["holgura"]), n(RET[i]["phi_deg"]), "Sí" if RET[i]["guia"] else ("No: B empuja el bloque hacia afuera" if abs(RET[i]["holgura"]) < 1e-3 else "No (libre)")] for i in ir], widths=(28, 36, 36, 26, 44), size=7.5, num_cols=(0, 1, 2, 3))
vblock("Verificaciones del retorno y de la sincronía", "ecuaciones (12) a (17); placa-guía en su posición nominal y en el extremo de la tolerancia, mesa a 80 °C.",
       take(r"^Sincronía|^Flanco de reenganche|sin autobloqueo en toda la conducción", "Giro") + take(r"^Velocidad de retorno", "Giro"))

H("7.2.5 Cara del bloque-uña: contacto dentro de la cara", 3)
CARA = FAB["bloque_una"]["cara"]
rho = math.atan(P["mu_s"]); gam = math.asin(BU["contacto_cara"] / BU["R_cara"])
T("Hipótesis. Con la cara plana y roce μ_s el contacto se va a s₂·tan ρ + μ_Q·d_Q/2 del eje y cae en la arista (inconsistencia I9 de 7.3.1). Se adopta una cara cilíndrica convexa en planta (generatriz vertical) "
  f"de radio R = {pint(BU['R_cara'])} mm con vértice en s₂ = L_qp − r: la normal pasa por el centro de curvatura y por el pasador, y el contacto queda cerca del eje. μ_Q = μ_E = {n(P['pv_muE'])} (hipótesis).", size=9)
table(["N°", "Magnitud", "Ecuación", "Valor (núcleo)", "Norma o referencia"], [
    ["(18)", "Ángulo de rozamiento", "ρ = atan μ_s", f"{n(deg(rho))}°", "Equilibrio con fricción"],
    ["(19)", "Brazo del roce del pasador Q", "d_R = μ_Q·d_Q/2", n(P["pv_muE"] * BU["d_Q"] / 2, unit="mm"), "Círculo de rozamiento"],
    ["(20)", "Ángulo de la normal", "sen γ = (s₂·sen ρ + d_R)/(s₂ − R)", f"s₂ = {n(BU['s_cara'], 4)} mm; γ = {n(deg(gam))}°", "Equilibrio del bloque libre en Q"],
    ["(21)", "Contacto desde el eje", "e_c = R·sen γ", n(BU["contacto_cara"], unit="mm"), "Geometría"],
    ["(22)", "Contacto dentro de la cara", "e_c + b_Hertz ≤ b_f/2 − 3 (chaflán 3 × 45°)", "ver fila «contacto dentro de la cara»", "Hertz; registro, «Cara del bloque-uña»"],
    ["(23)", "Giro de equilibrio del bloque (hacia afuera)", "δ = asin((R + r)·sen γ/L_qp)", f"{n(BU['giro_equilibrio_deg'])}°", "Holguras con los pasadores en 7.3.5 D"],
    ["(24)", "Flecha de las aristas", "R − √(R² − (b_f/2)²)", n(CARA["flecha_arista"], unit="mm"), "Geometría"],
    ["(25)", "Excentricidades en el cuerpo y en la cara", "cuerpo: e_cr + e + e_c·s₁/s₂;  cara: e + e_c", "ver filas «compresión + flexión»", "ASME BTH-1 §3-2.1, §3-2.3"],
], widths=(10, 36, 56, 36, 32), size=7)
vblock("Verificaciones del bloque-uña", f"bloque libre en Q cargado con F_calado = {n(FST, unit='kN')} (cota de F_n); cara templada (Fy_sup = {pint(P['Fy_surf'])} MPa); ASME BTH-1 Cat. B, Nd = {n(P['Nd'])}.",
       take(r".", "Uña") + take(r"pasador–uña", "Pasadores de empuje", opt=True))

H("7.2.6 Verificaciones de los pasadores, del cajón del ojal E, del pivote y de la geometría del cilindro", 3)
T("Desarrollo: cada fila indica la fórmula, la demanda, la capacidad, el FU (demanda/capacidad, o su inversa en los criterios de mínimo) y la norma. Fuerza de calado F_calado = "
  f"{n(FST, unit='kN')} por cilindro en las piezas de la cadena de empuje (ASME BTH-1 Cat. B, Nd = {n(P['Nd'])}).", size=9)
vblock("a) Pasadores Q y E y tapas del cajón", f"pasadores verticales en doble corte; Q con la reacción de la placa-guía en su extremo inferior (voladizo {n(BU['voladizo_leva'])} mm); F_calado; ASME BTH-1 §3-2 y §3-3.",
       take(r"^(?!Pasador Q)", "Articulaciones"))
vblock("b) Soporte del ojal E (cajón)", f"F_calado repartida en las dos tapas; sección en U (S_U = {n(SE['S_U'] / 1e3)}·10³ mm³); filetes a ambos lados de las tres paredes; ASME BTH-1 §3-2, §3-3.4; AISC 360-22 §J2.",
       take(r".", "Soporte del ojal E"))
vblock("c) Pivote central: componentes del empuje", "con el par en la diagonal las componentes radiales se anulan; al pivote llega la asimetría del roce (μ_s ± 0,05) a calado; ASME BTH-1 §3-2.3.", take(r"Pivotado|Empuje neto", "Pivote"))
vblock("d) Fatiga del bloque-uña y de las articulaciones", f"{pint(P['turns_yr'])} vueltas/año × {pint(P['life'])} años; AISC 360-22 Apéndice 3, Ec. A-3-1, Tabla A-3.1.", take(r"Bloque|articulación|ojal|cajón|Pasador", "Fatiga"))
vblock("e) Geometría del cilindro, del bloque y del ojal E", "geometría en planta y alzado del modo pivotado en toda la carrera; las dos holguras ajustadas se tratan en 7.2.7.",
       take(r"^Pivotado:|^Pasador Q fuera|^Holgura cilindro–mesa|^Bloque-uña libre del pasador siguiente|^Soporte del ojal E dentro|^Bloque-uña dentro de la luz|^Bloque-uña sobre la placa|^Oreja inferior del ojal E|^Cuerpo del cilindro libre sobre la base", "Giro"))

H("7.2.7 Holguras geométricas ajustadas y decisión del mandante", 3)
HO, H1 = ACC["holguras"]["adoptada"], ACC["holguras"]["B2760"]
T("Hipótesis. El mandante pidió FU ≤ 0,95 en las holguras geométricas del modo pivotado. Dos de ellas no pueden quedar a la vez bajo 0,95 con B = "
  f"{pint(HO['B'])} mm: el cajón del ojal dentro de la base pide un R_E chico y Q fuera de la mesa lo pide grande. El núcleo evalúa además B = {pint(H1['B'])} mm con la sugerencia de E a FU {n2(H1['fugeo'])} (pv_fugeo). "
  "Registro, «Valor por defecto del accionamiento (08-11-2026)».", size=9)
table(["Magnitud", "Fórmula", f"B = {pint(HO['B'])} (adoptada)", f"B = {pint(H1['B'])} (alternativa)"], [
    ["Cajón del ojal E dentro de la base", HO["cajon"]["formula"], f"{n(HO['cajon']['dem'], 5)} ≤ {pint(HO['cajon']['cap'])} mm · FU {fu3(HO['cajon']['fu'])}", f"{n(H1['cajon']['dem'], 5)} ≤ {pint(H1['cajon']['cap'])} mm · FU {fu3(H1['cajon']['fu'])}"],
    ["Q fuera de la mesa", HO["Q"]["formula"], f"{pint(HO['Q']['dem'])} ≤ {n(HO['Q']['cap'], 5)} mm · FU {fu3(HO['Q']['fu'])}", f"{pint(H1['Q']['dem'])} ≤ {n(H1['Q']['cap'], 5)} mm · FU {fu3(H1['Q']['fu'])}"],
    ["R_E / L_qp", "Sugerencia de E (registro)", f"{pint(HO['R_E'])} / {pint(HO['L_qp'])} mm", f"{pint(H1['R_E'])} / {pint(H1['L_qp'])} mm"],
    ["FS de diseño", "F_calado/F_dis", fu3(HO["FS"]), fu3(H1["FS"])],
    ["Masa total", "Núcleo", n(HO["masa"], 5, "kg"), f"{n(H1['masa'], 5, 'kg')} (+{n(H1['masa'] - HO['masa'], 3, 'kg')})"],
], widths=(36, 54, 40, 40), size=7.5)
mg_caj = HO["cajon"]["cap"] - HO["cajon"]["dem"]; mg_q = HO["Q"]["cap"] - HO["Q"]["dem"]
T(f"Decisión del mandante (08-11-2026): se acepta la base de {pint(HO['B'])} mm con las holguras «cajón del ojal E dentro de la base» FU {fu3(HO['cajon']['fu'])} y «Q fuera de la mesa» FU {fu3(HO['Q']['fu'])}; "
  f"ambas cumplen (FU ≤ 1) y se evita el aumento de {n(H1['masa'] - HO['masa'], 3, 'kg')} y de {pint(H1['B'] - HO['B'])} mm de lado que exige B = {pint(H1['B'])}. "
  f"Consecuencia: el cajón del ojal E queda a {n(mg_caj, 2)} mm del límite interior del marco (B/2 − t_marco − 5) y Q a {n(mg_q)} mm de su límite; la posición del cajón se fabrica con una "
  "tolerancia de posición menor que esa holgura, indicada en las láminas del soporte del ojal E y de su replanteo sobre la base, y se controla en la inspección dimensional.", bold=True, size=9)

# ---------------------------------------------------------------- 7.3 PLACA-GUÍA CURVA
H("7.3 Placa-guía curva del accionamiento pivotado", 2)
T("Fuentes: docs/qa/guia_curva_KIET/cambios.md (registro del cambio del 09-11-2026), docs/normas/registro.md («Placa-guía curva (09-11-2026)») y los campos del núcleo pivotado.placa_leva y "
  "fabricacion.placas_leva (tools/export_design.js). Los valores del diseño vigente salen del núcleo; los del diseño original, de docs/qa/guia_curva_KIET/original_b928552.json (commit b928552).", size=9)
H("7.3.1 Inconsistencias del diseño original", 3)
_h, _rows = md_table(CAMB, "2. Inconsistencias")
T("Hipótesis: diseño original de la placa-leva poligonal (commit b928552, valores por defecto). Las inconsistencias se transcriben del registro del cambio:", size=9, after=1)
table(_h, _rows, widths=(10, 95, 65), size=7.5)
T(f"Resultado: el perfil original no era fabricable tal como se exportaba (canto que invade el seguidor), su sincronía declarada ({n(ORIG['placa_leva']['sincronia'])} mm) no era alcanzable y el empuje no estaba verificado con Q apoyado en el canto. "
  "Las nueve se corrigen con la placa-guía curva (7.3.2 a 7.3.5) y la cara cilíndrica del bloque-uña (7.2.5).", bold=True, size=9)

H("7.3.2 Construcción de la curva", 3)
SC_, SK_ = PL_["segmentos_centro"], PL_["segmentos_canto"]
EF = PL_["eleccion_flanco"]
T("Hipótesis. W(L) = trayectoria del centro del seguidor (extremo inferior de Q, r_f = d_Q/2) en coordenadas del cilindro; w medido hacia afuera desde la recta E–P al inicio. "
  "Se construye para el cilindro 1 en giro antihorario; los otros tres canto se obtienen por rotación de 180° y por reflexión respecto de la diagonal O–E.", size=9)
table(["Paso", "Construcción", "Valor (núcleo)", "Norma o criterio"], [
    ["1", "Requisitos: W ≥ w_nec(L; m + δ) en el retorno; W ≥ w_emp + c en el empuje; W(L0 + tramo) = c (reenganche)", f"m + δ = {n(PL_['margen_diseno'])} mm; c = {n(P['pv_c'])} mm; bolsillo máx W = {n(PL_['bolsillo_w'])} mm", "Registro, «Requisitos de la trayectoria»"],
    ["2", "Flanco recto por (L0 + tramo, c) con el ángulo mínimo φ_req que deja W ≥ w_nec, limitado por α_máx", f"φ = {n(PL_['alpha_deg'])}° (requerido {n(PL_['alpha_req_deg'])}°) ≤ α_máx = {pint(P['pv_alpha'])}°; L pie / tope = {n(PL_['L_pie_flanco'])} / {n(PL_['L_tope_flanco'])} mm", "Registro, «Curva»"],
    ["3", "Dos biarcos de brazos iguales (hombro–cresta y bajada–empalme), tangentes entre sí y a la trayectoria de empuje en L_fin; nodos por búsqueda en malla con W ≥ requisito", f"cresta en L = {n(PL_['L_cresta'])} mm; tope del flanco elegido para hacer mínima máx(N_atasco; H_calado) = {n(EF['J'] / 1e3)} kN", "Geometría de biarcos"],
    ["4", "Salida tangente y cierre del bolsillo hacia la mesa (sin contacto)", f"{sum(1 for s in SK_ if s['tipo'] == 'linea')} rectas y {sum(1 for s in SK_ if s['tipo'] == 'arco')} arcos en el canto", "Geometría"],
    ["5", "Canto = desplazamiento exacto de W a d_Q/2 hacia la placa: arcos concéntricos con R_c = R − d_Q/2 (convexo) y R_c = R + d_Q/2 (cóncavo); es la envolvente exacta del seguidor", f"d_Q/2 = {n(BU['d_Q'] / 2)} mm", "Registro, «Canto»"],
    ["6", "Continuidad G1 en todos los empalmes", f"quiebre máx. {n(deg(PL_['g1_max_rad']), 2)}° (≤ 0,01°); salto de curvatura máx. {n(PL_['salto_curvatura_max'], 2)} 1/mm", "Registro, «Canto» (quiebre ≤ 0,01°)"],
    ["7", "Sin socavado: R_canto,convexo ≥ pv_rmin", f"R convexo mín. {n(PL_['radio_min_canto']['convexo'])} mm ≥ {pint(P['pv_rmin'])} mm; R cóncavo mín. {n(PL_['radio_min_canto']['concavo'])} mm", "Registro, «Sin socavado»"],
    ["8", "Polilínea de exportación (DXF con ARC exactos desde los segmentos)", f"flecha ≤ {n(PL_['tolerancia_polilinea'])} mm", "Tolerancia de perfil ± 0,2 mm (ISO 1101)"],
], widths=(10, 72, 54, 34), size=7)
T(f"Resultado: canto G1 de {pint(len(SK_))} tramos, envolvente exacta del seguidor, flanco a {n(PL_['alpha_deg'])}° y radio convexo mínimo {n(PL_['radio_min_canto']['convexo'])} mm.", bold=True, size=9)

H("7.3.3 Tabla de segmentos del canto (cilindro 1, giro antihorario)", 3)
srows = []
for k, s in enumerate(SK_, 1):
    sc = SC_[k - 1] if k - 1 < len(SC_) and SC_[k - 1]["rol"] == s["rol"] else None
    if s["tipo"] == "linea":
        ang = deg(math.atan2(s["p1"][1] - s["p0"][1], s["p1"][0] - s["p0"][0]))
        srows.append([pint(k), s["rol"], f"recta, {n(math.dist(s['p0'], s['p1']))} mm, {n(ang)}° en planta", "—", "—", "—", "—", pt(s["p0"]), pt(s["p1"])])
    else:
        srows.append([pint(k), s["rol"], f"arco {s['sentido']}", s.get("curvatura") or "—", n(sc["radio"]) if sc else "— (sin contacto)", n(s["radio"]), pt(s["centro"]), pt(s["p0"]), pt(s["p1"])])
table(["#", "Rol", "Tipo", "Curvatura (vista del seguidor)", "R trayectoria (mm)", "R canto (mm)", "Centro (mm)", "Inicio, tangencia (mm)", "Fin, tangencia (mm)"], srows,
      widths=(6, 28, 24, 16, 15, 13, 24, 24, 24), size=6.5, num_cols=(4, 5))
T("Sistema de la tornamesa (O en el centro de la mesa, mm). Cilindro 2: rotación de 180°; giro horario: reflexión respecto de la diagonal O–E (fabricacion.placas_leva.instancias). "
  "Los inicios y fines son los puntos de tangencia entre tramos consecutivos.", size=8.5)
PF = PL_["perfil"]
ip = sorted(set(list(range(0, len(PF), max(1, len(PF) // 12))) + [len(PF) - 1]))
T("Requisitos y trayectoria W(L) del centro del seguidor:", size=9, after=1)
_dw = lambda q: (lambda d: 0.0 if abs(d) < 1e-6 else d)(q["w_leva"] - max(q["w_nec"], q["w_emp"] + P["pv_c"]))
table(["L (mm)", "w_nec (m + δ) (mm)", "w_emp (mm)", "W(L) (mm)", "W − máx(w_nec; w_emp + c) (mm)"],
      [[n(PF[i]["L"]), n(PF[i]["w_nec"]), n(PF[i]["w_emp"]), n(PF[i]["w_leva"]), n(_dw(PF[i]))] for i in ip],
      widths=(30, 34, 30, 30, 34), size=7.5, num_cols=(0, 1, 2, 3, 4))

GF = None
try:   # figuras regeneradas con el núcleo de esta memoria (mismo script que docs/qa/guia_curva_KIET); si falla, se usan las del registro
    GF = OUT / "fig_guia_curva"; GF.mkdir(exist_ok=True)
    _src = (ROOT / "tools" / "fig_guia_curva.py").read_text(encoding="utf-8")
    assert _src.count("fig.savefig(OUT / (") == 2
    _src = _src.replace("fig.savefig(OUT / (", "fig.savefig(FIGOUT / (")
    _argv = sys.argv; sys.argv = ["fig_guia_curva.py", str(OUT / "TT300-C_design.json")]
    try:
        exec(compile(_src, str(ROOT / "tools" / "fig_guia_curva.py"), "exec"), {"__name__": "fig_guia_curva", "__file__": str(ROOT / "tools" / "fig_guia_curva.py"), "FIGOUT": GF})
    finally:
        sys.argv = _argv
    import matplotlib.pyplot as _plt; _plt.close("all")
    assert (GF / "comparacion.png").exists() and (GF / "cinematica.png").exists()
except Exception as _e:   # noqa: BLE001
    print("figuras de la placa-guía: se usan las de docs/qa/guia_curva_KIET (", _e, ")")
    GF = GKD
FIG_CIN = figure(GF / "cinematica.png", "Placa-guía curva: trayectorias de Q en el empuje y en el retorno, curva guía con radios, centros y tangencias, ángulo de presión y fuerzas del empuje "
                 "(tools/fig_guia_curva.py con el núcleo de esta memoria; figura del registro docs/qa/guia_curva_KIET/cinematica.png).", 170)

H("7.3.4 Placas: geometría, material y fabricación", 3)
INS = FPL["instancias"]["1_antihorario"]
_cor = [s["p1"] for s in INS["segmentos_contorno"] if s["rol"] == "contorno de la placa"][:4]
_cen = (sum(p[0] for p in _cor) / 4, sum(p[1] for p in _cor) / 4)
_angc = deg(math.atan2(_cen[1], _cen[0])) % 360
PBT = FPL["pernos"]; PPS = FPL["pasadores_posicion"]
table(["Dato", "Valor (núcleo)", "Norma o referencia"], [
    ["Configuración", "Placa rectangular empernada a la base junto a la cabeza del vástago, con recorte en media luna abierto hacia la mesa; 4 placas: 2 por cilindro (una por sentido, simétricas respecto de la diagonal)", "Concepto KIET (sin dimensiones)"],
    ["Marco", f"{n(FPL['marco']['largo'])} × {n(FPL['marco']['ancho'])} × {pint(FPL['t'])} mm; z de {pint(FPL['z'][0])} a {pint(FPL['z'][1])} mm", "fabricacion.placas_leva.marco"],
    ["Esquinas (cilindro 1, antihorario)", "; ".join(pt(p) for p in _cor), "Sistema de la tornamesa"],
    ["Posición del centro del rectángulo de la placa", f"{n(_angc, 4)}° ({n(abs(_angc - P['pv_phE']))}° de la diagonal del ojal), R {pint(math.hypot(*_cen))} mm", "Geometría"],
    ["Material", FPL["material"], "EN 10083-3; EN 10328"],
    ["Tratamiento del canto", f"{FPL['tratamiento']['canto']}; {FPL['tratamiento']['rugosidad_canto']}; {FPL['tratamiento']['bordes']}", "EN 10328; ISO 1302"],
    ["Corte", FPL["corte"], "ISO 1101"],
    ["Tornillos", f"{pint(PBT['n'])} × {PBT['norma']}, clase {PBT['clase']}; avellanado {PBT['avellanado']}; agujero Ø{pint(PBT['agujero'])}; par {PBT['par_apriete']}", "ISO 10642; VDI 2230-1"],
    ["Tornillos (cilindro 1, antihorario)", "; ".join(pt(p) for p in INS["pernos"]), "Ejes"],
    ["Pasadores de posición", f"{pint(PPS['n'])} × {PPS['norma']}; {PPS['ajuste']}; en {'; '.join(pt(p) for p in INS['pasadores_posicion'])}", "ISO 8734; ISO 286"],
    ["Masa", f"{n(m['cam'] / 4)} kg por placa; {n(m['cam'])} kg las 4 (original: {n(ORIG['placa_leva']['area'] * ORIG['placa_leva']['t'] * 7.85e-6 * 4)} kg con ρ = 7.850 kg/m³)", "ρ·V del núcleo"],
], widths=(36, 104, 30), size=7)

H("7.3.5 Verificaciones de la placa-guía", 3)
_cg = PL_["fuerzas_N"]
T(f"Cargas del seguidor: atasco del retorno N = {n(_cg['rampa_atasco'] / 1e3, unit='kN')} (16); empuje a calado H = {n(_cg['transversal_calado'] / 1e3, unit='kN')} (gobierna); "
  f"H de diseño = {n(_cg['transversal_diseno'] / 1e3, unit='kN')}. Las verificaciones de resistencia de la placa, los tornillos y el pasador Q usan máx(N_atasco; H_calado) = {n(_cg['diseno'] / 1e3, unit='kN')}.", size=9)
T("Criterios aplicados (docs/normas/registro.md, «Placa-guía curva (09-11-2026)»):", size=9, after=1)
table(["Verificación", "Criterio", "Referencia", "Ecuación / nota"], reg_rows("Accionamiento pivotado tipo KIET", "Placa-guía curva"), widths=(28, 60, 36, 46), size=6.5)
vblock("A) Placa: Hertz, capa templada, ligamento (ASME BTH-1), concentración de tensiones (Peterson) y fatiga (AISC 360-22 Apéndice 3)",
       f"familia {pint(PL_['familia'])} ({PL_['familia_nombre']}); canto templado Fy_sup = {pint(P['Fy_surf'])} MPa (supuesto de temple, capítulo 12); placa {FPL['material'].split(',')[0]} Fy = {pint(PL_['Fy'])} MPa; "
       f"fatiga con N = N_pin·vueltas·años.",
       take(r"^Placa-guía", "Placas-leva") + take(r"^Placa-guía", "Fatiga"))
vblock("B) Conexiones: tornillos ISO 10642 M16 (AISC 360-22 §J3.3, §J3.4, §J3.6, §J3.7, §J3.10) y rosca (VDI 2230)",
       f"grupo elástico (AISC Manual, Parte 7) con la carga en el punto de contacto; tornillos clase {PBT['clase']} (Fu = {pint(P['pv_Fub'])} MPa) roscados en la base de {pint(P['t_base'])} mm; "
       "los pasadores de posición no se cuentan en la resistencia.",
       take(r"^Tornillos|^Pasadores de posición", "Placas-leva"))
_vas = next(c for c in VER if re.search(r"^Vástago: flexocompresión", c["nombre"]))
vblock("C) Hidráulica, vástago y pasador Q",
       f"FS, presión y carrera con el empuje guiado; vástago en flexocompresión a calado con AISC 360-22 §H1.1 (Ec. H1-1a), §E3 y Apéndice 8 (B₁) con Fy = {pint(P['pv_Fyrod'])} MPa declarado como HIPÓTESIS "
       f"(dato del proveedor) y μ de los ojales = {n(P['pv_muE'])}; pandeo con Euler y FS 3; pasador Q con la reacción de la placa según ASME BTH-1 §3-3.3.",
       take(r"^FS del accionamiento|^Presión de diseño|^Alivio dentro|^Alarma bajo|^Retorno dentro|^Gira con|^Carrera requerida|^Empuje guiado: fuerza|^Vástago|^Pandeo del vástago|^Ojal comercial", "Giro") +
       take(r"^Pasador Q", "Articulaciones"),
       f"El vástago queda con FU {fu3(_vas['fu'])} con Fy = {pint(P['pv_Fyrod'])} MPa: es HIPÓTESIS hasta recibir la ficha del cilindro (capítulo 12).")
vblock("D) Apoyos y geometría: empuje con Q apoyado, canto, interferencias y holguras",
       "geometría en planta y alzado de las 4 placas (rotación y reflexión), bloque girado el ángulo de equilibrio δ (23) hacia afuera.",
       take(r"^Empuje con Q apoyado|^Canto de la placa-guía|^Placa-guía libre del seguidor|^Bloque-uña libre de los pasadores en el empuje guiado|^Cuerpo del cilindro fuera de la mesa en el empuje|^Placas-guía|^Cuerpo del cilindro sobre la placa-guía|^Placa-guía: profundidad del bolsillo", "Giro"))
T("Resultado: la placa-guía curva, sus tornillos, la hidráulica y la geometría cumplen; las filas de mayor FU son las de tornillos, distancia al borde, enganche de rosca y capa templada, "
  "y el vástago depende de la ficha del proveedor.", bold=True, size=9)

H("7.3.6 Material del contacto seguidor–canto (familias)", 3)
FAM = ACC["familias"]
T("Hipótesis. Cuatro familias para el contacto seguidor–canto, con los μ, presiones admisibles y PV de la interfaz de giro (pedido del mandante del 07-11-2026): 1 = acero templado–acero con grasa grafitada (Hertz con el radio real del canto); "
  "2 = UHMW sobre respaldo de acero; 3 = bronce con tapones de grafito sobre respaldo; 4 = inoxidable–inoxidable con grasa (familias 2 a 4: zapata del seguidor, p = H/(l·t) ≤ p_adm, PV ≤ PV_adm y l ≤ 3·d_Q). "
  "Con cam_mat = 0 la regla automática sigue la interfaz de giro. Cada familia se calcula con TT.analyze del modo pivotado y la interfaz base.", size=9)
rows = []
for f_ in FAM:
    fu = [c for c in f_["filas"] if c.get("fu") is not None and c["estado"] not in ("info", "pend")]
    g = max(fu, key=lambda c: c["fu"])
    rows.append([f"{pint(f_['cam_mat'])}: {f_['nombre']}", n(f_["mu"]), n(f_["F"]), fu3(f_["FS"]), n(f_["masa"], 5), "Sí" if f_["veredicto"]["estructura"] else "NO", f"{g['nombre']} (FU {fu3(g['fu'])})",
                 "; ".join(c["nombre"] for c in f_["fallas"]) or "—"])
table(["Familia (cam_mat)", "μ leva", "F_dis (kN)", "FS", "Masa total (kg)", "¿Cumple?", "Fila de mayor FU de la placa", "Falla"], rows, widths=(36, 11, 13, 10, 16, 13, 44, 27), size=7, num_cols=(1, 2, 3, 4))
rows = []
for f_ in FAM:
    for c in f_["filas"]:
        if c["estado"] != "info" and re.search(r"zapata|Zapata|PV|revestimiento|Hertz|respaldo", c["nombre"]):
            rows.append([pint(f_["cam_mat"])] + ifrows([c])[0])
table(["Fam."] + VH, rows, widths=(10, 31, 37, 14, 14, 12, 11, 13, 28), size=6.5, num_cols=(3, 4, 6))
table(["Interfaz de giro", "Familia automática (cam_mat = 0)"], [[a_["nombre"], f"{pint(a_['f'])}: {a_['familia']}"] for a_ in ACC["familias_auto"]], widths=(85, 85), size=8)
okf = [f_["nombre"] for f_ in FAM if f_["veredicto"]["estructura"]]
nok = [f_ for f_ in FAM if not f_["veredicto"]["estructura"]]
T(f"Resultado: cumplen las familias {', '.join(pint(f_['cam_mat']) for f_ in FAM if f_['veredicto']['estructura'])}"
  + (f"; no cumple la {', '.join(pint(f_['cam_mat']) for f_ in nok)} ({'; '.join(c['nombre'] for f_ in nok for c in f_['fallas'])})" if nok else "")
  + ". En las familias 2 a 4 la forma de la zapata sobre el canto curvo queda PENDIENTE (fila «pend»: una zapata plana no apoya sobre radios de 74 a 79 mm); por eso el diseño por defecto usa la familia 1 "
  "(acero templado), que no tiene zapata.", bold=True, size=9)

# ---------------------------------------------------------------- 7.4 COMPARACIÓN ORIGINAL / CURVA / KIET
H("7.4 Comparación: placa-leva original, placa-guía curva y concepto KIET", 2)
T("Hipótesis. Original = commit b928552 (valores por defecto, docs/qa/guia_curva_KIET/original_b928552.json); curva = núcleo vigente. KIET = plano de referencia KIET-1024-REF-TT-400T, MEDIDO en el plano "
  "(no acotado), solo como proporción relativa: no se trasladaron dimensiones de KIET al TT300-C.", size=9)
OPL = ORIG["placa_leva"]; ocs = {c["id"]: c for c in ORIG["casos"]}
_ncar = sum(1 for s in SK_ if s["tipo"] == "arco" and "sin contacto" not in s["rol"])
table(["Magnitud", "Original (b928552)", "Curva (vigente)", "Observación"], [
    ["Perfil del canto", f"poligonal: tramo a nivel, rampa {pint(OPL['alpha_deg'])}°, bolsillo plano, rampa de bajada", f"flanco recto {n(PL_['alpha_deg'])}° + {pint(_ncar)} arcos tangentes + salida recta (G1)", "7.3.2"],
    ["Ángulo de presión del reenganche", f"{pint(OPL['alpha_deg'])}° (vértices sin definir)", f"{n(PL_['alpha_deg'])}° (máximo, en el pie del flanco)", f"α_máx = {pint(P['pv_alpha'])}°"],
    ["Bolsillo (máx W)", n(OPL["bolsillo_w"], unit="mm"), n(PL_["bolsillo_w"], unit="mm"), "Salida de Q sobre el pasador siguiente"],
    ["Sincronía declarada", n(OPL["sincronia"], unit="mm"), f"{n(PL_['sincronia'])} mm (peor caso {n(PL_['sincronia_peor'])})", "La original no era alcanzable con el contorno exportado (I3)"],
    ["Fracción del empuje con Q retenido", f"{n(OPL['fraccion_empuje_retenida'] * 100)} %", f"Q apoyado en todo el empuje (fracción con Q a ≤ c + 0,5 mm de la colineal: {n(PL_['fraccion_empuje_retenida'] * 100)} %)", "I4"],
    ["Carga de diseño de la placa", f"{n(OPL['fuerzas_N']['diseno'] / 1e3)} kN (atasco)", f"{n(PL_['fuerzas_N']['diseno'] / 1e3)} kN ({'empuje a calado' if PL_['fuerzas_N']['diseno'] == PL_['fuerzas_N']['transversal_calado'] else 'atasco'})", "7.3.5"],
    ["Atasco del retorno", f"{n(OPL['fuerzas_N']['rampa_atasco'] / 1e3)} kN", f"{n(PL_['fuerzas_N']['rampa_atasco'] / 1e3)} kN", "(16)"],
    ["F cilindro, caso de diseño", n(ocs["dis"]["F"], unit="kN"), f"{n(cd['F'], unit='kN')} ({'+' if cd['F'] >= ocs['dis']['F'] else ''}{n((cd['F'] / ocs['dis']['F'] - 1) * 100)} %)", "Empuje guiado (7.2.2)"],
    ["Presión de diseño", n(ocs["dis"]["p"], unit="bar"), n(cd["p"], unit="bar"), f"Alarma {pint(P['p_alarm'])} bar"],
    ["FS diseño / contaminado / borde", f"{fu3(ocs['dis']['FS'])} / {fu3(ocs['cont']['FS'])} / {fu3(ocs['borde']['FS'])}", f"{fu3(cd['FS'])} / {fu3(casos['cont']['FS'])} / {fu3(casos['borde']['FS'])}", f"FS_mín = {n(P['FS_min'])}"],
    ["Carrera requerida", n(ORIG["carrera_req"], 4, "mm"), n(PIV["carrera_req"], 4, "mm"), f"Carrera {pint(P['stroke'])} mm"],
    ["Placa: fijación", f"labio de {pint(OPL['ancho_labio'])} mm, {pint(OPL['n_pernos'])} pernos M{pint(OPL['d_perno'])}", f"rectángulo {n(FPL['marco']['largo'])} × {n(FPL['marco']['ancho'])} mm, {pint(PBT['n'])} × {PBT['norma'].split(' (')[0]} + {pint(PPS['n'])} pasadores", "I6"],
    ["Placa: material (Fy)", f"Fy {pint(OPL['Fy'])} MPa (S355J2, no templable)", f"Fy {pint(PL_['Fy'])} MPa ({FPL['material'].split(',')[0]})", "I7"],
    ["Largo del canto / área de la placa", f"{n(OPL['largo_canto'])} mm / {n(OPL['area'] / 1e6, 3)} m²", f"{n(PL_['largo_canto'])} mm / {n(PL_['area'] / 1e6, 3)} m²", "Geometría"],
], widths=(40, 44, 54, 32), size=7.5)
_hk, _rk = md_table(CAMB, "5. Concepto KIET")
for _r in _rk:                                         # columna TT300-C de las filas medibles: valores del núcleo (centro del rectángulo de la placa)
    if _r[0].startswith("Posición angular"):
        _r[2] = f"± {n(abs(_angc - P['pv_phE']))}° (centro del rectángulo de la placa, núcleo)"
    elif _r[0].startswith("Radio del centro"):
        _r[2] = f"{n(math.hypot(*_cen) / (P['D_top'] / 2))} (centro del rectángulo sobre R = D/2 = {pint(P['D_top'] / 2)}; núcleo)"
T("Concepto KIET frente al TT300-C (transcripción del registro del cambio, sección 5; la columna KIET es una medición sobre el plano de referencia, sin cotas):", size=9, after=1)
table(_hk, _rk, widths=(40, 65, 65), size=7.5)
T(f"Control con el núcleo: centro de la placa del cilindro 1 a {n(_angc)}° ({n(abs(_angc - P['pv_phE']))}° de la diagonal del ojal) y a R/(D/2) = {n(math.hypot(*_cen) / (P['D_top'] / 2))}. "
  "Resultado: la placa-guía curva conserva el concepto constructivo de KIET (placa rectangular empernada con recorte en media luna junto a la cabeza del vástago) con una curva propia, obtenida de la cinemática del TT300-C; "
  "el flanco empinado queda en el extremo retraído porque lo exige la sincronía con el pasador siguiente.", bold=True, size=9)
FIG_CMP = figure(GF / "comparacion.png", "Placa-guía: original poligonal, rediseño curvo y concepto KIET (recortes del plano de referencia sin escala; no se trasladan dimensiones).", 160)

# ---------------------------------------------------------------- 7.3 GUIADO CON LEVA
H("7.5 Modo guiado con riel-leva de reenganche positiva (alternativa, drive_mode = 1)", 2)
LG = GUM["levaGuiada"]; KG = GUM["K"]; cdg = GUM["cd"]
ET = ACC["etiquetas"]
_prev = lambda lab, cur: (lambda mm: (int(mm[-1][0]), int(mm[-1][1])) if mm and abs(int(mm[-1][1]) - cur) < 1e-9 else (None, cur))(re.findall(r"(\d+) → (\d+) mm", lab))
sf0, sf1 = _prev(ET["s_free"], P["s_free"]); cl0, cl1 = _prev(ET["c_lug"], P["c_lug"])
assert sf0 is not None and cl0 is not None, "etiquetas de s_free o c_lug sin el valor anterior"
H("7.5.1 Hipótesis", 3)
POR = LG["soportes"]; RIEL = LG["riel"]; SEG = LG["seguidor"]
table(["Hipótesis", "Valor adoptado", "Origen"], [
    ["Modo", "drive_mode = 1, opt_cam = 1: patín guiado coaxial con el cilindro, uña con chaflán de retorno y resorte de apoyo, más riel-leva fijo que limita la salida de la uña", "Pedido del mandante del 07-11-2026 (Tarea 1)"],
    ["Riel-leva", f"Pletina 42CrMo4+QT (Fy = {pint(RIEL['Fy'])} MPa) de {pint(RIEL['t'])} × {pint(RIEL['ancho'])} mm, largo {n(RIEL['largo'], 4)} mm, sobre el patín (entre la cara superior del patín + 2 mm y la de la mesa); canto templado ≥ 55 HRC; "
     f"una por cilindro, se voltea para el otro sentido", "EN 10083-3 (16 < t ≤ 40 mm: Re ≥ 750)"],
    ["Pórticos del riel", f"{POR['tipo'][0].upper() + POR['tipo'][1:]}; patas de {pint(POR['espesor_pata_x'])} mm (x) × {pint(POR['largo_y'])} mm (y), alto {pint(POR['alto'])} mm, filete {pint(POR['filete_pata'])} mm; "
     f"luz entre pórticos {n(RIEL['luz_soportes'], 4)} mm; {pint(POR['n_pernos'])} pernos M{pint(POR['d_perno'])} 10.9 por pórtico; bancada prolongada {pint(POR['prolongacion_bancada_por_extremo'])} mm por extremo", "Registro, «Pórticos del riel (08-11-2026)»"],
    ["Seguidor", f"Rodillo Ø{pint(SEG['d_rodillo'])} × {pint(SEG['b_rodillo'])} mm en perno vertical Ø{pint(SEG['d_perno'])} fijo en la uña (voladizo {n(SEG['voladizo_perno'])} mm), guiado en y por una ranura de la tapa del patín; "
     f"familia {pint(LG['familia'])} ({LG['familia_nombre']}), μ del rodillo {n(LG['mu_seguidor'])}", "Registro, «Material del contacto»"],
    ["Rampa de reenganche", f"α = {pint(LG['alpha_deg'])}° respecto del eje de la bancada; holgura de toma {n(LG['holgura_toma'])} mm; margen de sincronía {n(P['cam_msync'])} mm", "Mínimo por sincronía, máximo por autobloqueo"],
    ["Recorrido libre antes de tomar el pasador", f"s_libre: {pint(sf0)} → {pint(sf1)} mm (con {pint(sf0)} mm no cabe la rampa detrás del pasador siguiente)", "Etiqueta del parámetro s_free del núcleo; registro, «Sincronía»"],
    ["Distancia de los puntos de izaje al borde", f"c_lug: {pint(cl0)} → {pint(cl1)} mm (la leva suma masa sobre la base; flecha de izaje con margen ≥ 10 %)", "Etiqueta del parámetro c_lug del núcleo"],
], widths=(36, 94, 40), size=7.5)
T("Criterios aplicados (docs/normas/registro.md, «Leva de reenganche positiva (modo guiado)»):", size=9, after=1)
table(["Verificación", "Criterio", "Referencia", "Ecuación / nota"], reg_rows("Leva de reenganche positiva (modo guiado)"), widths=(28, 60, 36, 46), size=6.5)

H("7.5.2 Cinemática y equilibrio del patín guiado", 3)
table(["Magnitud", "Expresión", "Valor"], [
    ["Paso angular", "2π/N_pas", n(360 / P["N_pin"], unit="°")],
    ["Brazo mínimo (toma del pasador)", "a_mín = R_pas·cos(π/N)", n(KG["armMin"], unit="mm")],
    ["Cuerda entre pasadores", "c = 2R_pas·sin(π/N)", n(KG["chord"], unit="mm")],
    ["Carrera requerida", "s_req = s_libre + c", n(KG["s_req"], unit="mm")],
    ["Margen de carrera", "carrera − s_req", n(KG["margin"], unit="mm")],
    ["Excentricidad máxima eje cilindro–pasador", "Δ = x_g − a_mín", n(KG["DeltaMax"], unit="mm")],
    ["Largo del patín / largo efectivo de guía", "L_patín = l_p + 20 + f_ext + 1,25·d_pp; Lg = ⅔·L_patín", f"{n(KG['L_s'])} / {n(KG['Lg'])} mm"],
    ["Recorrido de retorno de la uña", "Δx (alojamiento del patín)", n(KG["travel"], unit="mm")],
    ["μ guía / μ cara de la uña–pasador", "μ_g / μ_s", f"{n(P['mu_g'])} / {n(P['mu_s'])}"],
    ["Factor equivalente (máximo en la carrera)", "K = F_cil·n·a_mín/T", n(GUM["Kguide"], 4)],
], widths=(65, 65, 40), size=8)
T("Hipótesis: la uña empuja con una cara plana normal a la guía (eje y). El pasador desliza sobre la cara: su punto de contacto (x_c, y_c) = (R cos θ, R sin θ − r) se mueve en x con velocidad ω·(r − y_p), "
  "por lo que la fricción H = s·μ_s·F_pas cambia de sentido en y_p = r (θ = asin(r/R)); en ese punto se evalúan ambos sentidos.", size=9)
table(["Ecuación", "Expresión", "Referencia"], [
    ["Momento sobre la mesa (por cilindro)", "x_c·F_pas − y_c·H = T/n   →   F_pas = (T/n)/(x_c − s·μ_s·y_c)", "Equilibrio de momentos"],
    ["Momento del patín respecto de la reacción trasera", "R_f = [F_pas·(x_g − x_c) + H·(y_c − y_r)]/Lg", "Equilibrio del patín"],
    ["Fuerzas en x sobre el patín", "R_r = H − R_f", "Equilibrio del patín"],
    ["Fuerzas en y (fricción de guía)", "F_cil·η_c = F_pas + μ_g·(|R_f| + |R_r|)", "Equilibrio del patín"],
    ["Fuerza de diseño", "F_dis = máx F_cil(θ) en la carrera", "Criterio del proyecto"],
    ["Reacciones de guía a calado", f"R_guía = máx(|R_f|, |R_r|) = {n(GUM['Rguide'], unit='kN')}", "Equilibrio; piezas de la guía con ASME BTH-1"],
], widths=(55, 80, 35), size=8)
table(["Caso", "μ", "r (mm)", "T (kN·m)", "F_cil (kN)", "p (bar)", "FS al calado", "¿Gira?"],
      [[c["nombre"], n(c["mu"]), n(c["r"]), n(c["T"]), n(c["F"]), n(c["p"]), n(c["FS"]), "Sí" if c["gira"] else "NO"] for c in GUM["casos"]],
      widths=(52, 12, 16, 18, 18, 16, 20, 14), size=8, num_cols=(1, 2, 3, 4, 5, 6))
table(["Posición", "θ (°)", "s (mm)", "F_cil (kN)", "p (bar)", "F_pas (kN)", "H (kN)", "Tang. (kN)", "Radial (kN)", "R_f (kN)", "R_r (kN)"],
      [[c["pos"], n(c["th"]), n(c["s"]), n(c["F"]), n(c["p"]), n(c["Fpin"]), n(c["H"]), n(c["Ft"]), n(c["Fr"]), n(c["Rf"]), n(c["Rr"])] for c in GUM["carrera"]],
      widths=(34, 11, 12, 14, 12, 14, 12, 15, 15, 13, 13), size=7, num_cols=tuple(range(1, 11)))
T(f"Resultado: F_dis = {n(cdg['F'], unit='kN')} a {n(cdg['p'], unit='bar')}, FS = {n(cdg['FS'])} ≥ {n(P['FS_min'])}; margen de carrera {n(KG['margin'])} mm con s_libre = {pint(sf1)} mm. "
  "El resultado se contrasta por potencia virtual en el verificador independiente (tests/indep_accionamiento.py).", bold=True, size=9)

H("7.5.3 Sincronía, autobloqueo de la rampa y fuerzas de atasco", 3)
AB, FN = LG["autobloqueo"], LG["fuerzas_N"]
table(["Magnitud", "Expresión", "Valor", "Referencia"], [
    ["Sincronía (rampa / entrada a la toma)", "mín holgura uña–pasador B con u = u_leva(η) ≥ margen", f"{n(LG['sincronia'])} / {n(LG['sincronia_entrada'])} mm ≥ {n(P['cam_msync'])} mm", "Geometría (polígono de la uña frente al círculo de B)"],
    ["Bolsillo", "máx u_nec ≤ Δx", f"{n(LG['u_nec_max'])} ≤ {n(LG['recorrido_bolsillo'])} mm", "Geometría"],
    ["Autobloqueo de la rampa", "μ_ret·k_t·(sen α + μ_seg·cos α) < (cos α − μ_seg·sen α)·(1 − 2μ_ret·z_f/L_in)", f"{n(AB['dem'])} < {n(AB['cap'])} (FU {n(AB['dem'] / AB['cap'])})", "Equilibrio de la cuña con fricción"],
    ["Factor de torsión de la uña", "k_t = 1 + 2(z_f − z_ranura)/h_uña", n(AB["k_t"]), "Torsión por la fuerza del seguidor sobre la tapa"],
    ["Fuerza de retorno disponible", "F_ret = A_anular·p_ret", n(FN["F_ret"] / 1e3, unit="kN"), "Hidráulica"],
    ["Atasco en la rampa", "N_rampa = F_ret/sen α (componente en x: N·cos α)", f"{n(FN['rampa'] / 1e3)} kN (x: {n(FN['rampa_x'] / 1e3)} kN)", "Cota sin roce"],
    ["Atasco a nivel de toma", "N_toma = F_ret/tan β (chaflán de la uña sobre B)", n(FN["toma"] / 1e3, unit="kN"), "Cota sin roce"],
    ["Fracción del empuje con la uña retenida", "(η₁ − η_entrada)/cuerda", f"{n(LG['fraccion_empuje_retenida'] * 100)} %", "Geometría"],
], widths=(40, 58, 36, 36), size=7.5)
T(f"Resultado: la rampa a {pint(LG['alpha_deg'])}° deja {n(LG['sincronia'])} mm de sincronía y no se autobloquea con el rodillo (FU {n(AB['dem'] / AB['cap'])}). Limitación: la leva retiene la uña solo en el "
  f"{n(LG['fraccion_empuje_retenida'] * 100, 2)} % del empuje, porque el bolsillo coincide con la toma del pasador siguiente y una leva posicional no distingue el sentido; en el resto la uña queda con el resorte y el roce "
  "del alojamiento, como antes. La función positiva de la leva es la rampa de reenganche del retorno. Las familias 2 a 4 (zapata deslizante) se autobloquean con la rampa que exige la sincronía: en el modo guiado el núcleo usa el rodillo.", bold=True, size=9)

H("7.5.4 Verificaciones del riel-leva de reenganche", 3)
vblock("a) Leva, seguidor y pórticos", "fuerzas de atasco al retraer a p_ret (cotas sin roce) y geometría del riel sobre el patín; ASME BTH-1 Cat. B y AISC 360-22 §J3 y §J2.4.", pick(VG, "Leva de reenganche"))
H("7.5.5 Verificaciones del patín, la uña y las articulaciones (modo guiado)", 3)
vblock("a) Patín y guía", "fuerza de calado; reacciones de guía por el par F·Δ; ASME BTH-1 Cat. B.", pick(VG, "Patín y guía"))
_una = next(c for c in VG if c["nombre"].startswith("Flexión en la boca del patín"))
vblock("b) Uña", "uña en voladizo desde la boca del patín, fuerza de calado.", pick(VG, "Uña"),
       f"Advertencia aceptada por el mandante (07-11-2026): flexión de la uña en la boca del patín, FU {fu3(_una['fu'])} (σ = {n(_una['dem'])} ≤ Fy/Nd = {n(_una['cap'])} MPa; ASME BTH-1 §3-2.3), con Fy = {pint(P['Fy_dog'])} MPa "
       "(34CrNiMo6+QT, Re ≥ 800 MPa para 40 < t ≤ 100 mm, EN 10083-3). El criterio interno FU ≤ 0,90 se relaja solo para esta fila.")
vblock("c) Articulaciones", "pasadores de ojal en doble corte, mejillas y orejas de ménsula; fuerza de calado; ASME BTH-1 Cat. B.", pick(VG, "Articulaciones"))

# ---------------------------------------------------------------- 7.6 COMPARACIÓN DE MODOS
H("7.6 Comparación guiado frente a pivotado y recomendación", 2)
T("Hipótesis: mismos parámetros, interfaz base y casos de fricción; cada modo se calcula con TT.analyze completo (con FEA). FU máximo global: mayor FU de todas las verificaciones (incluye mínimos constructivos); "
  "FU de resistencia: mayor FU de las verificaciones de resistencia del sistema estructural.", size=9)
cs = lambda M, i: next(c for c in M["casos"] if c["id"] == i)
gp, gg = PVM["gobernante_resistencia"], GUM["gobernante_resistencia"]
cmp_rows = [
    ["Masa total", n(PVM["masa"], 5, "kg"), n(GUM["masa"], 5, "kg"), f"Pivotado {n(GUM['masa'] - PVM['masa'], 3, 'kg')} más liviano"],
    ["F_cil de diseño", n(PVM["cd"]["F"], unit="kN"), n(GUM["cd"]["F"], unit="kN"), "máx_θ F_cil (7.2.2 / 7.5.2)"],
    ["Presión de diseño", n(PVM["cd"]["p"], unit="bar"), n(GUM["cd"]["p"], unit="bar"), f"Alarma {pint(P['p_alarm'])} bar"],
    ["FS de diseño", fu3(PVM["cd"]["FS"]), fu3(GUM["cd"]["FS"]), f"≥ {n(P['FS_min'])}"],
    ["FS contaminado (μ = " + n(cs(PVM, 'cont')["mu"]) + ")", fu3(cs(PVM, "cont")["FS"]), fu3(cs(GUM, "cont")["FS"]), "Debe girar (FS ≥ 1)"],
    ["FS con contacto en el borde (r = R)", fu3(cs(PVM, "borde")["FS"]), fu3(cs(GUM, "borde")["FS"]), "Debe girar (FS ≥ 1)"],
    ["Brazo mínimo (geométrico / efectivo)", f"{n(PVM['K']['armMin'])} / {n(PVM['K']['aEffMin'])} mm", f"{n(GUM['K']['armMin'])} mm", "El pivotado pierde brazo por el ángulo del cilindro y el roce"],
    ["Componente radial en el pasador, por cilindro (diseño)", n(PVM["radial"]["por_cilindro_dis"], unit="kN"), n(GUM["radial"]["por_cilindro_dis"], unit="kN"), "Se anula en el par; va al pivote solo la asimetría"],
    ["Empuje neto al pivote (roce desigual ± 0,05)", n(PVM["radial"]["neta"]["dem"], unit="kN"), n(GUM["radial"]["neta"]["dem"], unit="kN"), "Equilibrio; revisión independiente H10"],
    ["Carrera requerida / margen", f"{n(PVM['K']['s_req'])} / {n(PVM['K']['margin'])} mm", f"{n(GUM['K']['s_req'])} / {n(GUM['K']['margin'])} mm", f"Carrera {pint(P['stroke'])} mm"],
    ["FU máximo global", fu3(PVM["veredicto"]["fuMax"]), fu3(GUM["veredicto"]["fuMax"]), "Mínimos constructivos (filete mínimo = adoptado)"],
    ["FU máximo de resistencia", f"{fu3(gp['fu'])} ({gp['nombre']})", f"{fu3(gg['fu'])} ({gg['nombre']})", "Criterio interno FU ≤ 0,90"],
    ["Advertencias / fallas", f"{PVM['veredicto']['warnEst'] + PVM['veredicto']['warnGiro']} / 0" if PVM["veredicto"]["estructura"] else "falla", f"{GUM['veredicto']['warnEst'] + GUM['veredicto']['warnGiro']} / 0" if GUM["veredicto"]["estructura"] else "falla", "Guiado: uña en la boca del patín (aceptada)"],
]
table(["Magnitud", "Pivotado (por defecto)", "Guiado con leva", "Observación"], cmp_rows, widths=(44, 42, 42, 42), size=7.5)
MA = {x["id"]: x for x in ALT["modos_accionamiento"]}
IDS_ACC = [i for i in ("base", "A", "B", "C1", "C2", "C3") if i in MA]          # W en stand by (6.2)
rows = []
for i in IDS_ACC:
    mm_ = {q["drive_mode"]: q for q in MA[i]["modos"]}
    g1, g2 = mm_[1], mm_[2]
    rows.append([MA[i]["nombre"], n(g2["masa"], 5), n(g1["masa"], 5), n(g1["masa"] - g2["masa"], 3), n(g2["FS"]), n(g1["FS"]), n(g2["p_dis"]), n(g1["p_dis"]),
                 "Sí" if g2["veredicto"]["estructura"] and g2["veredicto"]["gira"] else "NO", "Sí" if g1["veredicto"]["estructura"] and g1["veredicto"]["gira"] else "NO"])
T("Las dos variantes de accionamiento para cada alternativa de interfaz (capítulo 9), con la familia automática del contacto de la leva:", size=9, after=1)
table(["Alternativa", "Masa pivotado (kg)", "Masa guiado (kg)", "Δ (kg)", "FS pivotado", "FS guiado", "p pivotado (bar)", "p guiado (bar)", "¿Cumple pivotado?", "¿Cumple guiado?"], rows,
      widths=(44, 15, 15, 11, 13, 12, 14, 14, 16, 16), size=6.5, num_cols=tuple(range(1, 8)))
_mas = "más" if PVM["cd"]["F"] > GUM["cd"]["F"] else "menos"
T(f"Recomendación adoptada (decisión del mandante del 08-11-2026): modo pivotado tipo KIET por defecto. Es {n(GUM['masa'] - PVM['masa'], 3, 'kg')} más liviano, no tiene advertencias de resistencia (FU máximo {fu3(gp['fu'])}) "
  f"y su reenganche lo garantiza la geometría de la placa-guía curva. Con el empuje guiado necesita {_mas} fuerza que el guiado ({n(PVM['cd']['F'])} frente a {n(GUM['cd']['F'])} kN; FS {fu3(PVM['cd']['FS'])} frente a {fu3(GUM['cd']['FS'])}). "
  f"A cambio, tiene menor brazo efectivo ({n(PVM['K']['aEffMin'])} mm frente a {n(GUM['K']['armMin'])}), una componente radial por cilindro mayor ({n(PVM['radial']['por_cilindro_dis'])} frente a {n(GUM['radial']['por_cilindro_dis'])} kN, "
  f"que se anula en el par), menos margen de carrera ({n(PVM['K']['margin'])} mm) y las dos holguras ajustadas de 7.2.7. El guiado con leva queda como alternativa verificada.", bold=True, size=9)

H("7.7 Clase de presión del cilindro", 2)
table(["Clase (psi)", "Alivio / alarma (bar)", "Émbolo mínimo (mm)", f"FS con Ø{pint(P['D_bore'])}", "p diseño (bar)"],
      [[pint(c["psi"]), f"{pint(c['pr'])} / {pint(c['pa'])}", n(c["Dmin"]), n(c["FScur"]), n(c["pcur"])] for c in D["escenarios"]["classes"]],
      widths=(28, 38, 34, 34, 30), num_cols=(2, 3, 4))
T("Émbolo mínimo = máx(FS_mín·F_dis/p_alivio; F_dis/p_alarma), con alarma = 0,85·alivio.")
H("7.8 Retorno, ciclo y sensibilidad", 2)
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

H("7.9 Bomba, tiempos, control y capacidad según el número de cilindros", 2)
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
  f"encoder de ángulo (un paso = {n(360 / P['N_pin'])}°, resolución ≤ 0,1°); conteo de carreras. La presión de despegue medida permite calcular el μ real (ensayo de aceptación, plan de inspección TT300C-GEN-003-C).", size=9)
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
T("Desarrollo: lista completa de las verificaciones del diseño por defecto (modo pivotado tipo KIET, interfaz base). Cada fila indica la fórmula aplicada, la demanda, la capacidad y la referencia normativa. FU = demanda/capacidad "
  "(o su inversa cuando el criterio es de mínimo). Las filas \"Info\" son valores informativos sin criterio de aceptación. Las verificaciones propias del modo guiado con riel-leva están en 7.5. FU con 3 decimales.", size=9)
INTRO = {
    "Giro": "Hipótesis: casos de fricción de 4.3; cinemática y empuje guiado del modo pivotado de 7.2; placa-guía curva de 7.3. Incluye geometría (holguras e interferencias) del accionamiento; las holguras ajustadas se tratan en 7.2.7.",
    "Patín y guía": "Hipótesis: fuerza de calado; reacciones de guía por el par F·Δ; ASME BTH-1 Cat. B.",
    "Uña": f"Hipótesis: bloque-uña libre en Q, fuerza de calado con la excentricidad del cuerpo acodado (e_cr = {pint(P['pv_ecr'])} mm); ASME BTH-1 Cat. B.",
    "Articulaciones": "Hipótesis: pasadores verticales Q y E en doble corte y tapas del cajón del ojal E; fuerza de calado; ASME BTH-1 Cat. B.",
    "Soporte del ojal E": "Hipótesis: cajón soldado a la base con sección resistente en U; F_calado repartida en las dos tapas; ASME BTH-1 §3-2 y §3-3.4, AISC 360-22 §J2.",
    "Placas-leva": "Hipótesis: placa-guía curva de 7.3; cargas del seguidor (atasco del retorno y empuje a calado con Q apoyado); familia del contacto de 7.3.6; tornillos con AISC 360-22 §J3.",
    "Orejas de izaje": "Hipótesis: 4 orejas de la base, izaje del equipo vacío (9.4).",
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
        rows.append([str(k), v["nombre"], v["formula"], nd(v["dem"], v["unidad"]), "—" if v.get("cap") is None else nd(v["cap"], v["unidad"]), v["unidad"],
                     "—" if info or v.get("fu") is None else fu3(v["fu"]), EST.get(v["estado"], v["estado"]), v["ref"]])
    table(["N°", "Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"], rows,
          widths=(8, 52, 70, 17, 17, 13, 14, 18, 58), size=7, num_cols=(3, 4, 6))

# ================================================================= 9. ALTERNATIVAS (horizontal)
IDS = ["base", "A", "B", "C1", "C2", "C3"]                          # W en stand by (6.2)
AL = {a["id"]: a for a in ALT["alternativas"]}
SHORT = {"base": "Base: acero–acero con grasa", "A": "A: discos inox con grasa", "B": "B: discos inox + lámina UHMW", "C1": "C1: bronce con grafito + disco duro",
         "C2": "C2: dos placas de bronce", "C3": "C3: bronce en pastillas + disco duro"}
PL = {p["id"]: p for g in D["grupos"] for p in g["p"]}


def plab(pid):
    return PL[pid]["lab"] if pid in PL else pid


def crow(c, conf=False):
    info = c["estado"] == "info"
    r = [c["nombre"], c["formula"], nd(c["dem"], c["unidad"]), "—" if c.get("cap") is None else nd(c["cap"], c["unidad"]), c["unidad"],
         "—" if info or c.get("fu") is None else fu3(c["fu"]), EST.get(c["estado"], c["estado"])]
    if conf:
        r.append(c.get("conf", "—"))
    r.append(c["ref"])
    return r


CH = ["Verificación", "Fórmula", "Demanda", "Capacidad", "Unidad", "FU", "Estado", "Referencia"]
CW = (48, 78, 16, 16, 17, 11, 17, 64)
CHC = CH[:7] + ["Conf.", "Referencia"]
CWC = (46, 74, 16, 16, 17, 11, 16, 11, 60)


def find(a, key, rx):
    return [c for c in a[key] if re.search(rx, c["nombre"])]


H("9. Alternativas de interfaz de giro")
T("La cubierta de madera W está EN STAND BY (6.2) y no se incluye en las tablas de este capítulo ni del capítulo 10.", bold=True, size=9)
T("Hipótesis. Cada alternativa se evalúa con el mismo núcleo (TT.analyze) y los mismos parámetros del capítulo 4; solo cambia el selector de interfaz: "
  "base (opt_ss = opt_uhmw = opt_bz = 0), A (opt_ss = 1), B (opt_uhmw = 1), C1, C2 y C3 (opt_bz = 1 con bz_conf = 1, 2, 3), todas con el accionamiento pivotado por defecto. "
  f"En {TOOL} el selector de alternativa de interfaz ejecuta la misma función. Los datos de este capítulo salen de tools/export_alternativas.js; no se copió ninguna cifra a mano.", size=9)
table(["Parámetro común", "Id", "Valor", "Significado"], [
    [plab("hc_min").split(" (")[0], "hc_min", n(P["hc_min"], unit="mm"), "Altura de contacto mínima del tope sobre el canto del sector"],
    [plab("tol_hc").split(" (")[0], "tol_hc", n(P["tol_hc"], unit="mm"), "Corte y rebabas del canto: el aplastamiento se verifica con h_c − tol_hc"],
    [plab("j_sec").split(" (")[0], "j_sec", n(P["j_sec"], unit="mm"), "Junta en frío mínima entre sectores (la dilatación a ΔT de montaje la puede aumentar)"],
    ["Holgura radial de R_i respecto del rebaje del collar", "m_ri", n(P["m_ri"], unit="mm"), "R_i = D_collar/2 + c_boss_r + m_ri"],
    ["Radio de la oreja de izaje / Ø del agujero", "R_ear / d_ear", f"{n(P['R_ear'])} / {n(P['d_ear'])} mm", "Orejas de izaje de la base (AISC 360-22 §D5.2)"],
], widths=(70, 28, 30, 139), size=7.5)

H("9.1 Comparación de masa, espesores, presión de contacto, giro y utilización", 2)
T("Desarrollo. Δ masa se mide contra la base (acero–acero); la altura agregada es el espesor que la alternativa suma entre la base y la mesa. "
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
    rows.append([SHORT[i], n(a["masa"]), "—" if i == "base" else "+" + n(a["dMasa"]), "—" if i == "base" else n(f["delta"]), disc,
                 tr(f["tuhReq"], f["tuh"]) if i == "B" else "—", tr(f["tbzReq"], f["tbz"]) if i.startswith("C") else "—", n(a["q_max"]), n(a["q_avg"])])
table(["Alternativa", "Masa total (kg)", "Δ masa (kg)", "Altura agregada (mm)", "Discos inox / duro: t_req → adoptado (mm)", "Lámina UHMW: t_req → adoptado (mm)", "Bronce: t_req → adoptado (mm)", "q_máx (MPa)", "q_med (MPa)"],
      rows, widths=(56, 22, 20, 22, 44, 34, 30, 19, 20), size=7.5, num_cols=(1, 2, 3, 7, 8))
rows = []
for i in IDS:
    a = AL[i]; g = a["giro"]; v = a["veredicto"]; c = a["conteo"]; gb = a["gobernante"]; gr = a["gobernante_resistencia"]
    rows.append([SHORT[i], n(g["F"]), n(g["p"]), n(g["FS"]), n(g["mu"]), "Sí" if v["gira"] else "NO", "Sí" if v["estructura"] else "NO", fu3(v["fuMax"]), gb["nombre"],
                 fu3(gr["fu"]), gr["nombre"], f"{c['ok']} / {c['warn']} / {c['fail']} / {c['pend']}"])
table(["Alternativa", "F por cilindro (kN)", "p diseño (bar)", "FS giro", "μ diseño", "¿Gira?", "¿Estructura?", "FU máx. global", "Elemento gobernante (global)", "FU estructura", "Gobernante de estructura", "Cumple / adv. / falla / pend."],
      rows, widths=(40, 17, 15, 12, 12, 12, 17, 14, 45, 14, 48, 21), size=7, num_cols=(1, 2, 3, 4, 7, 9))
fs_b, fs_c = AL["base"]["giro"]["FS"], AL["C1"]["giro"]["FS"]
T(f"Resultado: las seis alternativas giran con FS ≥ {n(P['FS_min'])} y verifican la estructura a 20 °C. Contra la base ({n(AL['base']['masa'], unit='kg')}), A agrega {n(AL['A']['dMasa'], unit='kg')}, B {n(AL['B']['dMasa'], unit='kg')}, "
  f"C1 {n(AL['C1']['dMasa'], unit='kg')}, C2 {n(AL['C2']['dMasa'], unit='kg')} y C3 {n(AL['C3']['dMasa'], unit='kg')}. "
  f"El FS de giro sube de {n(fs_b)} (acero–acero) a {n(fs_c)} con bronce grafitado por el menor μ de diseño. "
  f"El FU máximo global es {fu3(AL['base']['veredicto']['fuMax'])} en todas: lo fijan límites geométricos y de presión (p. ej. alivio igual a la presión nominal del cilindro; filete mínimo igual al adoptado), no la resistencia.", bold=True, size=9)

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
T(f"Resultado: las orejas cumplen; la extensión tras el agujero gobierna con FU {fu3(ea['fu'])} ({n(ea['dem'])} frente a {n(ea['cap'])} mm). La holgura de {n(P['g_ear'])} mm solo es admisible porque el izaje es estático (el pasador no gira bajo carga plena).", bold=True, size=9)

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

# ---- 9.6 madera (stand by)
H("9.6 Cubierta de madera W", 2)
T("En stand by: ver 6.2.", size=9)

# ---- 9.7 tapones de grafito (opción C)
H("9.7 Opción C: tapones de grafito, cantidad real frente a ideal", 2)
TC = ("C1", "C2", "C3")
TG = {i: TPA[i]["geom"] for i in TC}
TCMP = {i: TPA[i]["comparacion"] for i in TC}
PROF_TAP = next(c["cap"] for c in D["interfazChecks"]["C"] if "profundidad restante tras el desgaste" in c["nombre"])   # = PLUG_DEPTH·t_bz (núcleo)
LIG_FAB, PROF_D_FAB = TAP["barridos"]["ligamento_min_fab"], TAP["barridos"]["prof_max_d"]
d_, p_ = TAP["parametros"]["bz_plug_d"], TAP["parametros"]["bz_plug_p"]
ng = lambda x, sig=3: (lambda t: re.sub(r",?0+$", "", t) if "," in t else t)(n(x, sig))   # parámetros enteros sin ceros de relleno (Ø12, paso 30)
sg = lambda x, sig=2: ("+" if x > 0 else "") + n(x, sig).replace("-", "−") + " %"


def ligado(x):
    return x["p"] - x["d"]


T("Hipótesis. Los tapones de grafito (Ø d, paso p) se disponen en una malla escalonada sobre la corona de contacto. La malla ideal supone la corona completa cubierta, f_g,ideal = π·d²/(2√3·p²) y "
  "N_ideal = f_g,ideal·A_contacto/(π·d²/4). En la placa real hay que dejar una franja de borde, la muesca de cada tope, los tornillos de posición y las ranuras de engrase, de modo que caben menos tapones. "
  f"Desde el {NUCLEO} el cálculo cuenta los tapones que caben (N_real) con el mismo patrón S09 que coloca el dibujante, y con bz_fg_modo = {pint(P['bz_fg_modo'])} la masa del bronce, q_neto, PV, desgaste y la lubricación usan la fracción REAL "
  f"f_g,real = N_real·π·d²/(4·A_contacto). Datos de tools/export_alternativas.js (clave tapones, función TT.tapones); ninguna cifra se copió a mano. Patrón adoptado: Ø{ng(d_)} mm, paso {ng(p_)} mm, "
  f"{pint(P['n_sec'])} sectores (C1, C2) o {pint(P['bz_npad'])} pastillas con cobertura {ng(P['bz_cover'])} (C3).", size=9)

H("9.7.1 Definición geométrica de N_real", 3)
g1 = TG["C1"]
b_t = AL["C1"]["topes"][0]["b_tope"]
table(["Elemento", "Definición geométrica", "Valor del cálculo", "Referencia"], [
    ["Malla escalonada", "Centros (x, y) = (i·p + (j mod 2)·p/2, j·p·√3/2), anclada al centro de la mesa; fila alterna desplazada p/2", f"Ø{ng(d_)} · paso {ng(p_)} mm; {pint(g1['N_malla'])} centros en la corona tras la franja de borde (C1)", "Geometría del proyecto (patrón S09 del modelo 3D)"],
    ["Corona de contacto", "R_i ≤ r ≤ R_o; A_contacto = cobertura·π·(R_o² − R_i²)", f"R_i = {n(AL['C1']['Ri'])} mm, R_o = {pint(AL['C1']['Ro'])} mm; A = {n(g1['area_contacto'] / 1e6, 4)} m² (C3: × {ng(P['bz_cover'])})", "Geometría; R_i del apartado 9.3"],
    ["Franja de borde bz_edge", "Distancia mínima desde el BORDE DEL TAPÓN (no su centro) al borde del bronce, a la muesca, a los tornillos y a las ranuras: centro a ≥ bz_edge + d/2", f"bz_edge = {ng(P['bz_edge'])} mm → centro a ≥ {n(P['bz_edge'] + d_ / 2)} mm", "Criterio del proyecto (S09)"],
    ["Bordes del sector o de la pastilla", "C1 y C2: sectores de bordes paralelos a la radial de contorno, separados por la junta en frío; C3: pastillas de bordes radiales que cubren la fracción bz_cover", f"{pint(g1['n_sectores'])} piezas; junta {ng(g1['junta'])} mm (C1, C2); cobertura {ng(TG['C3']['cov'])} (C3)", "Geometría; juntas del apartado 10.6"],
    ["Muesca del tope", "Rectángulo (b_tope + 2) × L_tope centrado en r_u sobre la bisectriz, ensanchado en bz_edge", f"({ng(b_t)} + 2) × {ng(g1['L_muesca'])} mm (largo del tope, 9.2)", "ASME BTH-1 §3-3.3 (largo del tope); geometría"],
    ["Tornillos de posición", f"ISO 10642 M{pint(P['d_tor'])}, cabeza avellanada Ø{pint(g1['d_cabeza'])} mm; {pint(g1['n_tornillos_sector'])} por sector sobre la bisectriz, a mitad de camino entre la muesca y cada borde; franja bz_edge desde la cabeza",
     "Radios " + " y ".join(n(r) for r in g1["radios_tornillos"]) + " mm", "ISO 10642 (cabeza avellanada); geometría"],
    ["Ranuras de engrase", f"{pint(P['n_gr_circ'])} circunferenciales (la exterior a R_o − 30; el resto equiespaciado hasta R_i + 30) y {pint(P['n_gr_rad'])} radiales; franja bz_edge a cada lado",
     f"Ancho {ng(P['w_gr'])} mm, profundidad {ng(P['h_gr'])} mm", "Geometría del proyecto (engrase)"],
    ["Orden de descarte", "Cada centro de la malla se cuenta una sola vez, en la primera causa que lo excluye: borde → muesca → tornillos → ranura circunferencial → ranura radial", "—", "Conteo determinista del núcleo"],
], widths=(40, 105, 72, 50), size=7.5)
T("Ecuaciones.", bold=True, size=9, after=1)
table(["Magnitud", "Expresión", "Referencia"], [
    ["Cantidad real", "N_real = #{centros de la malla con R_i + m ≤ r ≤ R_o − m, distancia al borde del sector ≥ m y fuera de la muesca, de los tornillos y de las ranuras ensanchados en m}, con m = bz_edge + d/2", "Geometría del proyecto; núcleo TT.tapones"],
    ["Fracción de grafito real", "f_g,real = N_real·(π·d²/4)/A_contacto", "Geometría"],
    ["Fracción de grafito ideal", "f_g,ideal = π·d²/(2√3·p²);  N_ideal = f_g,ideal·A_contacto/(π·d²/4)", "Empaquetamiento hexagonal (geometría)"],
    ["Ligamento entre tapones", "η = (p − d)/p ≥ bz_eta_min; fabricación: p − d ≥ " + ng(LIG_FAB) + " mm y profundidad ≤ " + ng(PROF_D_FAB) + "·d", "Criterio del proyecto; fabricación: criterio de taller por confirmar"],
    ["Profundidad del tapón", "h_tapón = 0,70·t_bz = " + n(PROF_TAP) + " mm (t_bz = " + n(TCMP["C1"]["real"]["tbz"]) + " mm)", "Catálogo del bronce con grafito (supuesto C)"],
    ["Efecto de f_g en el cálculo", "q_neto = q_máx/(cobertura·(1 − f_g)); masa del bronce = ρ_bz·(1 − 0,70·f_g) + ρ_grafito·0,70·f_g sobre el área cubierta; PV = q_neto·v; h_desgaste = k·q_neto·s", "Datos de catálogo del bronce (confianza C); TT.analyze"],
], widths=(40, 150, 77), size=7.5)

H("9.7.2 Cantidad real frente a ideal", 3)
rows = []
for i in TC:
    g = TG[i]
    rows.append([SHORT[i], pint(g["n_sectores"]), n(g["area_contacto"] / 1e6, 4), pint(g["N_malla"]), pint(g["N_real"]), pint(g["N_ideal"]), sg((g["N_real"] / g["N_ideal"] - 1) * 100, 3),
                 n(g["fg_real"], 3), n(g["fg_ideal"], 3), n(g["eta"]), f"{pint(g['por_sector_min'])} a {pint(g['por_sector_max'])}"])
table(["Alternativa", "Piezas", "A_contacto (m²)", "Centros tras la franja de borde", "N_real", "N_ideal", "N_real frente a ideal", "f_g real", "f_g ideal", "η", "Tapones por pieza"], rows,
      widths=(50, 14, 22, 28, 18, 18, 22, 16, 16, 12, 28), size=7.5, num_cols=tuple(range(1, 11)))
H("9.7.3 Pérdidas por causa", 3)
rows = []
for i in TC:
    g = TG[i]; pd_ = g["perdidas"]; tot = sum(pd_.values())
    assert g["N_malla"] - g["N_real"] == tot, "las pérdidas por causa no suman N_malla − N_real"
    rows.append([SHORT[i], pint(g["N_malla"]), pint(pd_["borde"]), pint(pd_["muesca"]), pint(pd_["tornillos"]), pint(pd_["ranCirc"]), pint(pd_["ranRad"]), pint(tot), pint(g["N_real"]), pint(g["N_ideal"] - g["N_real"])])
table(["Alternativa", "Centros tras la franja de borde", "Borde del sector o pastilla", "Muesca del tope", "Tornillos de posición", "Ranura circunferencial", "Ranura radial", "Suma de pérdidas", "N_real", "N_ideal − N_real"], rows,
      widths=(50, 26, 26, 22, 24, 26, 20, 22, 18, 24), size=7.5, num_cols=tuple(range(1, 10)))
T(f"Resultado: de los {pint(g1['N_ideal'])} tapones de la malla ideal caben {pint(g1['N_real'])} en C1 y C2 ({pint(g1['N_real'] / g1['N_ideal'] * 100)} %) y {pint(TG['C3']['N_real'])} en C3 ({pint(TG['C3']['N_real'] / TG['C3']['N_ideal'] * 100)} %); "
  f"f_g,real = {n(g1['fg_real'])} frente a {n(g1['fg_ideal'])} ideal. La causa mayor es la franja de borde ({pint(g1['perdidas']['borde'])} en C1; {pint(TG['C3']['perdidas']['borde'])} en C3 por los bordes radiales de las pastillas), "
  f"seguida de la ranura circunferencial ({pint(g1['perdidas']['ranCirc'])}), la muesca de los topes ({pint(g1['perdidas']['muesca'])}) y los tornillos de posición ({pint(g1['perdidas']['tornillos'])}). "
  "La diferencia entre la malla ideal y los centros que caben en la corona se debe a que la malla ideal es una densidad promedio y no respeta el contorno.", bold=True, size=9)

H("9.7.4 Sensibilidad: fracción ideal frente a real", 3)
T("Desarrollo. Mismo cálculo con bz_fg_modo = 0 (ideal) y 1 (real). f_g solo afecta la masa del bronce, q_neto (y con él PV y desgaste) y la cobertura de lubricación; no afecta q_máx, el espesor ni η.", size=9)
rows = []
for i in TC:
    c = TCMP[i]
    for lab, k in (("ideal (bz_fg_modo = 0)", "ideal"), ("real (bz_fg_modo = 1)", "real")):
        r = c[k]
        rows.append([SHORT[i].split(":")[0] + " " + lab, pint(r["N"]), n(r["fg"], 3), n(r["masa_bz"]), n(r["masa_total"], 4), n(r["qNet"]), n(r["PV"], 3), n(r["desgaste"], 3), n(r["FS"]), f"{n(r['tbzReq'])} → {n(r['tbz'])}"])
    dp = c["delta_pct"]
    rows.append([SHORT[i].split(":")[0] + " variación", sg(dp["N"], 3), sg(dp["fg"], 3), sg(dp["masa_bz"]), sg(dp["masa_total"]), sg(dp["qNet"]), sg(dp["PV"]), sg(dp["desgaste"]), "sin cambio" if abs(dp["FS"]) < 1e-9 else sg(dp["FS"]), "sin cambio" if abs(dp["tbz"]) < 1e-9 and abs(dp["tbzReq"]) < 1e-9 else "cambia"])
table(["Caso", "N", "f_g", "Masa del bronce (kg)", "Masa total (kg)", "q_neto (MPa)", "PV (MPa·m/s)", "Desgaste (mm)", "FS giro", "t_bz requerido → adoptado (mm)"], rows,
      widths=(62, 18, 18, 24, 24, 20, 22, 22, 18, 36), size=7.5, num_cols=tuple(range(1, 9)))
dc1 = TCMP["C1"]["delta_pct"]
T(f"Resultado: con los tapones reales el bronce de C1 pesa {sg(dc1['masa_bz'])} ({n(TCMP['C1']['real']['masa_bz'] - TCMP['C1']['ideal']['masa_bz'])} kg), q_neto {sg(dc1['qNet'])} (de {n(TCMP['C1']['ideal']['qNet'])} a {n(TCMP['C1']['real']['qNet'])} MPa, FU {fu3(TCMP['C1']['real']['fuQ'])}), "
  f"PV y desgaste {sg(dc1['PV'])} cada uno, y el FS de giro queda en {n(TCMP['C1']['real']['FS'], 4)} sin cambio. El espesor de {n(TCMP['C1']['real']['tbz'])} mm lo fija el tope (la flexión pide {n(TCMP['C1']['real']['tbzReq'])} mm) y por eso f_g no lo cambia mientras η ≥ {n2(P['bz_eta_min'])}. "
  "Menos tapones significa más bronce, más masa y menor presión neta: ninguna verificación empeora; lo que empeora es la cobertura de lubricante (9.7.6).", bold=True, size=9)

H("9.7.5 Barridos de la franja de borde, de los tornillos, de f_g y de (d, p)", 3)
T("a) Franja de borde bz_edge (sensibilidad del conteo; el resto del cálculo no cambia de estado).", bold=True, size=9, after=1)
yn = lambda x: "Sí" if x else "NO"
rows = []
for i in ("C1", "C3"):
    for sb in TPA[i]["sens_borde"]:
        rows.append([SHORT[i].split(":")[0], ng(sb["bz_edge"]), pint(sb["N"]), n(sb["fg"], 3), n(sb["masa_bz"]), n(sb["qNet"]), yn(sb["gira"]), yn(sb["estructura"]), pint(sb["n_fallan"])])
table(["Alt.", "bz_edge (mm)", "N_real", "f_g real", "Masa del bronce (kg)", "q_neto (MPa)", "¿Gira?", "¿Estructura?", "Verificaciones que fallan"], rows, widths=(14, 24, 20, 20, 30, 24, 16, 24, 32), size=7.5, num_cols=tuple(range(1, 6)))
T("b) Tornillos de posición (Ø de la cabeza ISO 10642 y número por sector).", bold=True, size=9, after=1)
rows = []
for i in ("C1", "C3"):
    for st in TPA[i]["sens_tornillos"]:
        rows.append([SHORT[i].split(":")[0], "M" + pint(st["d_tor"]), pint(st["bz_n_tor"]), pint(st["N"]), n(st["fg"], 3), n(st["masa_bz"]), n(st["qNet"]), yn(st["estructura"])])
table(["Alt.", "Tornillo", "Por sector", "N_real", "f_g real", "Masa del bronce (kg)", "q_neto (MPa)", "¿Estructura?"], rows, widths=(14, 24, 24, 22, 22, 32, 26, 28), size=7.5, num_cols=tuple(range(2, 7)))
a1 = TPA["C1"]
T(f"c) Barrido de la fracción de grafito objetivo ({n(a1['barrido_fg'][0]['fg_obj'], 2)} a {n(a1['barrido_fg'][-1]['fg_obj'], 2)}): para cada f_g objetivo, el patrón Ø{ng(d_)} de mayor paso que lo alcanza. Alternativa C1 (C2 es igual; C3 difiere en menos de 1 punto de f_g).", bold=True, size=9, after=1)
rows = [[n(x["fg_obj"], 3), ng(x["d"]), ng(x["p"]), n(x["eta"]), pint(x["N"]), n(x["fg"], 3), ng(ligado(x)), "Sí" if x["fab"] else "NO", x["estado"]] for x in a1["barrido_fg"]]
table(["f_g objetivo", "Ø (mm)", "Paso (mm)", "η", "Perforaciones", "f_g real", "Ligamento p − d (mm)", "¿Fabricable?", "Estado"], rows, widths=(24, 16, 18, 14, 26, 20, 32, 26, 60), size=7.5, num_cols=tuple(range(0, 7)))
T(f"d) Barrido de (Ø, paso): Ø {pint(TAP['barridos']['d'][0])} a {pint(TAP['barridos']['d'][-1])} mm y paso {pint(TAP['barridos']['p'][0])} a {pint(TAP['barridos']['p'][-1])} mm ({len(a1['barrido_dp'])} patrones por alternativa). "
  f"Por cada Ø, el patrón de mayor f_g real con η ≥ {n2(P['bz_eta_min'])}, fabricable y que cumple las demás verificaciones del bronce (C1).", bold=True, size=9, after=1)
rows = []
for dd in TAP["barridos"]["d"]:
    L = [x for x in a1["barrido_dp"] if x["d"] == dd]
    okk = [x for x in L if x["eta"] >= P["bz_eta_min"] - 1e-12 and x["fab"] and x["estado"] != "no cumple"]
    mx = max(L, key=lambda x: x["fg"])
    if okk:
        b = max(okk, key=lambda x: x["fg"])
        rows.append([ng(dd), pint(len(L)), pint(len(okk)), ng(b["p"]), n(b["eta"]), pint(b["N"]), n(b["fg"], 3), n(mx["fg"], 3), f"paso {ng(mx['p'])} (η {n(mx['eta'])})"])
    else:
        rows.append([ng(dd), pint(len(L)), "0", "—", "—", "—", "—", n(mx["fg"], 3), f"paso {ng(mx['p'])} (η {n(mx['eta'])})"])
table(["Ø (mm)", "Patrones", f"Con η ≥ {n2(P['bz_eta_min'])} y fabricables", "Mejor paso (mm)", "η", "Perforaciones", "f_g real máxima", "f_g real sin restricción", "Patrón sin restricción"], rows,
      widths=(18, 20, 36, 24, 16, 26, 28, 32, 50), size=7.5, num_cols=tuple(range(0, 8)))

H("9.7.6 Patrón máximo alcanzable y criterios de lubricación", 3)
T(f"Hipótesis. Dos criterios acotan el patrón: bz_fg_min = {n2(P['bz_fg_min'])} (cobertura mínima de lubricante sólido; supuesto de confianza C, el valor lo fija la ficha del proveedor) y bz_eta_min = {n2(P['bz_eta_min'])} "
  f"(ligamento mínimo, criterio de proyecto). Con bz_fg_estricto = {pint(P['bz_fg_estricto'])} el primero es un AVISO permanente que no cambia el veredicto; con 1 el diseño por defecto no cumpliría nunca.", size=9)
rows = []
for i in TC:
    cn = TPA[i]["conclusion"]; act, mx = cn["patron_actual"], cn["mejor_alcanzable"]
    for lab, x in (("Adoptado", act), ("Máximo alcanzable (η ≥ " + n2(P["bz_eta_min"]) + ")", mx)):
        rows.append([SHORT[i].split(":")[0], lab, ng(x["d"]), ng(x["p"]), n(x["eta"]), ng(ligado(x)), pint(x["N"]), n(x["fg"], 3), n(x["masa_bz"]), n(x["qNet"]),
                     "Sí" if x["fg"] >= P["bz_fg_min"] - 1e-12 else "NO", "Sí" if x["eta"] >= P["bz_eta_min"] - 1e-12 else "NO", "Sí" if x["fab"] else "NO"])
for x in TAP["patron_minusculo"]:
    pm = dict(x); pm["eta"] = x["eta"]
    rows.append([x["id"], "Perforaciones minúsculas", ng(x["d"]), ng(x["p"]), n(x["eta"]), ng(x["p"] - x["d"]), pint(x["N"]), n(x["fg"], 3), "—", "—",
                 "Sí" if x["cumple_fg"] else "NO", "Sí" if x["eta"] >= P["bz_eta_min"] - 1e-12 else "NO", "Sí" if x["p"] - x["d"] >= LIG_FAB - 1e-9 else "NO"])
table(["Alt.", "Patrón", "Ø (mm)", "Paso (mm)", "η", "Ligamento (mm)", "Perforaciones", "f_g real", "Masa del bronce (kg)", "q_neto (MPa)", f"¿f_g ≥ {n2(P['bz_fg_min'])}?", f"¿η ≥ {n2(P['bz_eta_min'])}?", "¿Fabricable?"], rows,
      widths=(12, 50, 14, 16, 14, 20, 24, 16, 26, 20, 20, 20, 22), size=7, num_cols=tuple(range(2, 10)))
cn1, cn3 = TPA["C1"]["conclusion"], TPA["C3"]["conclusion"]
mn1 = next(x for x in TAP["patron_minusculo"] if x["id"] == "C1")
T(f"Resultado: ningún patrón del barrido con Ø ≥ {ng(TAP['barridos']['d'][0])} mm, η ≥ {n2(P['bz_eta_min'])} y fabricable cumple f_g ≥ {n2(P['bz_fg_min'])}: el máximo alcanzable es {n(cn1['fg_max_alcanzable'])} (Ø{n(cn1['mejor_alcanzable']['d'])} · paso {n(cn1['mejor_alcanzable']['p'])}, "
  f"{pint(cn1['mejor_alcanzable']['N'])} agujeros, η {n(cn1['mejor_alcanzable']['eta'])}) en C1 y C2 y {n(cn3['fg_max_alcanzable'])} en C3. Para llegar a ~{n2(P['bz_fg_min'])} con η = {n2(P['bz_eta_min'])} haría falta Ø{ng(mn1['d'])} con paso {ng(mn1['p'])}: "
  f"f_g = {n(mn1['fg'])} con {pint(mn1['N'])} perforaciones en C1 (todavía bajo el mínimo), ligamento de {ng(mn1['p'] - mn1['d'])} mm bajo el mínimo de fabricación de {ng(LIG_FAB)} mm: inviable. "
  f"El máximo admisible por la física del contacto (q_neto, PV y desgaste) es f_g = {n(cn1['fg_max_fisico'])}, muy sobre lo que cabe: el límite lo ponen el ligamento y la geometría, no la resistencia. "
  "El criterio bz_fg_min queda como aviso permanente y se conserva el patrón adoptado.", bold=True, size=9)

H("9.7.7 Hallazgos de la réplica independiente (G1 a G4)", 3)
T("Hipótesis. La réplica independiente (tests/indep_interfaz.py, escrita sin leer el código del núcleo) reproduce N_real de C1, C2 y C3 y emitió cuatro hallazgos menores. Se cuantifican aquí con los datos del núcleo.", size=9)
emp = TAP["empates"]
muC = f"μ_d = {ng(P['muC_d'])}, μ_cont = {n(P['muC_cont'])}, μ_seco = {n(P['muC_dry'])}"
pared, prof = P["bz_edge"], PROF_TAP
rows = [
    ["G1", f"Los criterios bz_fg_min = {n2(P['bz_fg_min'])} y bz_eta_min = {n2(P['bz_eta_min'])} no se cumplen a la vez con tapones de Ø{ng(d_)}: solo con perforaciones minúsculas",
     f"Máximo con Ø{ng(d_)} y η ≥ {n2(P['bz_eta_min'])}: f_g = {n(cn1['fg_max_alcanzable'])} (C1) y {n(cn3['fg_max_alcanzable'])} (C3). Con Ø{ng(mn1['d'])} · paso {ng(mn1['p'])}: {n(mn1['fg'])} con {pint(mn1['N'])} perforaciones (C1) y {n(TAP['patron_minusculo'][1]['fg'])} con {pint(TAP['patron_minusculo'][1]['N'])} (C3)",
     f"Fijar con el proveedor una cobertura mínima alcanzable o bajar bz_eta_min; no usar bz_fg_estricto = 1 con los valores actuales"],
    ["G2", "Empates de coma flotante: un tapón con el borde a exactamente bz_edge cumple «≥ bz_edge»; el conteo puede variar entre ejecuciones de aritmética distinta. La muesca del tope se trata como rectángulo ensanchado (esquinas vivas)",
     f"{pint(emp['n_con_empate'])} de {pint(emp['n_patrones'])} patrones del barrido (C1 y C3) cambian de N con ±{('%.0e' % emp['eps']).replace('e-0', 'e-')} mm (hasta {n(emp['max_dif_pct'])} %); el patrón adoptado no tiene empates (C1: {pint(emp['patron_actual'][0]['N_menos'])} y {pint(emp['patron_actual'][0]['N_mas'])}; C3: {pint(emp['patron_actual'][1]['N_menos'])} y {pint(emp['patron_actual'][1]['N_mas'])})",
     "Definir «≥ bz_edge» con tolerancia de 1e-6 mm (empate admitido) para que el conteo no dependa de la coma flotante; esquinas redondeadas darían más tapones (hipótesis conservadora actual: esquinas vivas)"],
    ["G3", "El μ de la opción C no depende de f_g: la cobertura real es 2/3 de la ideal y está bajo bz_fg_min, pero el μ es un dato fijo de catálogo y el FS de giro no lo refleja",
     f"f_g real / ideal = {n(g1['fg_real'] / g1['fg_ideal'])} ({n(g1['fg_real'] * 100)} % frente a {n(g1['fg_ideal'] * 100)} %); {muC}; FS de giro {n(TCMP['C1']['real']['FS'], 4)} igual con f_g ideal y real",
     f"Ensayar μ con el patrón real (Ø{ng(d_)} · paso {ng(p_)}, {n(g1['fg_real'] * 100)} % de grafito) o pedir la ficha del proveedor para esa cobertura"],
    ["G4", "La pared de bz_edge junto al borde, muesca, tornillo o ranura es menor que el ligamento entre tapones y la flexión usa solo η = (p − d)/p",
     f"Pared {n(pared)} mm sobre {n(prof)} mm de profundidad del tapón (relación {n(pared / prof)}); η del borde = pared/(pared + d/2) = {n(pared / (pared + d_ / 2))} frente a η = {n(g1['eta'])}; ligamento entre tapones p − d = {ng(p_ - d_)} mm",
     f"Criterio de fabricación por confirmar con el proveedor (pared ≥ 0,5·(p − d) = {n(0.5 * (p_ - d_))} mm o ≥ 0,3·d = {n(0.3 * d_)} mm); no cambia espesores ni masas, solo el conteo (9.7.5 a)"],
]
table(["Id", "Hallazgo", "Evidencia (núcleo)", "Acción"], rows, widths=(10, 80, 100, 77), size=7.5)

H("9.7.8 Recomendación", 3)
fg_cota = max(TPA[i]["conclusion"]["fg_max_alcanzable"] for i in TC)
bullets([
    f"Confirmar con el proveedor del bronce autolubricado su fracción real de grafito y la ficha (p_adm, PV, k, μ) para el patrón real: Ø{ng(d_)} · paso {ng(p_)} da f_g = {n(g1['fg_real'])} (ideal {n(g1['fg_ideal'])}), no la ideal.",
    f"Ensayar el μ con el patrón real (arranque tras reposo y a 2,5 mm/s, con y sin grasa); el cálculo trata μ = {ng(P['muC_d'])} como dato fijo (G3).",
    f"Si el proveedor o el ensayo exige f_g mayor que {n(fg_cota, 2)} (la cota alcanzable con tapones es {n(fg_cota)} y exige el patrón Ø{ng(d_)} · paso 22, de η {n(cn1['mejor_alcanzable']['eta'])}), cambiar a bronce con lubricante sólido distribuido o con ranuras de grafito, no a tapones.",
    f"Mientras tanto se conserva Ø{ng(d_)} · paso {ng(p_)}: el aviso de bz_fg_min permanece y bz_fg_estricto queda en {pint(P['bz_fg_estricto'])}.",
])

# ---- 9.8 pendientes
H("9.8 Advertencias y pendientes por alternativa", 2)
rows = []
for i in IDS:
    av = AL[i]["avisos"]
    if not av:
        rows.append([i, "—", "—", "Sin advertencias ni pendientes", "—"])
    for v in av:
        rows.append([i, EST.get(v["estado"], v["estado"]), v["grp"], v["nombre"], v["ref"]])
table(["Alt.", "Estado", "Grupo", "Advertencia o pendiente", "Referencia"], rows, widths=(11, 20, 28, 140, 68), size=7)
T("Además de lo anterior, quedan como pendiente común el filete máximo de almas y nervios (9.5) y la numeración de artículos de ASME BTH-1 (capítulo 12).", size=9)
T(f"La advertencia aceptada de la flexión de la uña en la boca del patín (FU {fu3(_una['fu'])}) es propia del modo guiado y se trata en 7.5.5; con el modo pivotado por defecto no aparece.", size=9)

# ================================================================= 10. EXPOSICIÓN SOLAR (horizontal)
TH = D["termica"]
THA = {a["id"]: a for a in TH["alternativas"]}
MED = ALT["medidas"]
FA = MED["fuera_alcance"]
T0, TS = TH["T_ref"], TH["T_scn"]
iS = TH["T"].index(TS)
F80 = [f for f in TH["factores"] if f["T"] == TS][0]
AC80 = [x for x in TH["aceite"] if x["T"] == TS][0]
VI80 = [x for x in TH["viscosidad"] if x["T"] == TS][0]
bT = lambda i, k=iS: THA[i]["byT"][k]
filas = lambda i, subs, k=iS: [f for f in bT(i, k)["filas"] if f["sub"] in subs]
bas80 = bT("base")
yn = lambda x: "Sí" if x else "NO"
REGREF = "docs/normas/registro.md, sección «Temperatura (exposición solar, 80 °C)»"
TIT_TERM = {"base": "Base", "A": "A", "B": "B", "C1": "C1", "C2": "C2", "C3": "C3"}


def first_fail(i, key):
    """Primera temperatura de la grilla en que la clave booleana (gira/estructura/termico) deja de cumplirse; None si cumple en todas."""
    for b in THA[i]["byT"]:
        if not b[key]:
            return b["T"]
    return None


# Afirmaciones cualitativas del texto: si los datos del núcleo cambian y dejan de ser ciertas, la memoria no se emite con texto desactualizado
_b = lambda i, k=iS: THA[i]["byT"][k]
assert TH["alcance"] == 1 and P["term_alcance"] == 1 and TH["aceite_fuera_de_alcance"], "el texto del capítulo 10 es del alcance 1 (placas y disco)"
_NFA = {i: _b(i)["fuera_resumen"]["n"] for i in IDS}
assert _NFA["base"] == FA["n"] and all(FA["n"] <= x <= FA["n"] + 6 for x in _NFA.values()), "filas fuera de alcance: texto desactualizado"
assert all(AL[i]["veredicto"]["gira"] and AL[i]["veredicto"]["estructura"] for i in IDS), "alguna alternativa no cumple a 20 °C"
assert all(abs(AL[i]["veredicto"]["fuMax"] - 1) < 1e-6 for i in IDS), "FU máximo global distinto de 1,00"
# Veredictos a 80 °C en que se apoya el texto (giro, estructura, grupo térmico). La réplica independiente tests/indep_termica.py verifica el modo guiado
# (tests/golden/tt300c_guiado.json); con el modo pivotado por defecto los FU de estructura cambian levemente (asiento del pivote, topes) y los veredictos se mantienen.
_REP = {"base": (True, True, True), "A": (False, True, True), "B": (False, False, False), "C1": (True, True, True), "C2": (True, True, True), "C3": (True, False, False)}
for _i, (_g, _e, _t) in _REP.items():
    assert (_b(_i)["gira"], _b(_i)["estructura"], _b(_i)["termico"]) == (_g, _e, _t), f"{_i}: veredicto a 80 °C distinto del supuesto en el texto"
assert _b("B")["fuEst"] > 1, "B a 80 °C: texto desactualizado"
assert all(abs(THA[i]["byT"][0]["FS"] - _b(i)["FS"]) < 1e-9 for i in IDS), "el FS de giro cambia con T"
assert (not _b("B", 2)["estructura"]) and (not _b("A", 2)["gira"]) and _b("C3", 2)["fuTerm"] > 1 and all(not _b(i, 4)["estructura"] for i in IDS), "sensibilidad 20–100 °C: texto desactualizado"
assert len(THA["C3"]["sens"]["bz090"]["empeoran"]) == 0, "bronce x 0,90 cambia verificaciones"
assert not THA["B"]["sens"]["uhmw"]["kp"][1]["cumple"] and THA["B"]["sens"]["uhmw"]["kp_crit"] is not None
assert all(TPA[i]["comparacion"][k]["gira"] and TPA[i]["comparacion"][k]["estructura"] for i in ("C1", "C2", "C3") for k in ("ideal", "real")), "tapones: ideal y real cumplen estructura y giro"
# con el modo pivotado no hay fila de la uña en la boca del patín: las advertencias informativas son solo del aceite, los sellos y la bomba
assert FA["fail"] == 4 and FA["warn"] == 2 and {f["grp"] for f in FA["filas_aviso"]} <= {"Temperatura · aceite atrapado", "Temperatura · aceite, sellos y bomba"}, "fuera de alcance: texto desactualizado"

H("10. Exposición solar a 80 °C")
T("Escenario aparte, pedido del mandante (06-11-2026): la tornamesa expuesta al sol, con el cuerpo a 80 °C. ALCANCE: este escenario verifica solo el sistema de placas y disco (term_alcance = 1). "
  "Los cilindros, el aceite atrapado, la válvula de alivio térmico, los sellos, la viscosidad y la bomba, y el accionamiento mecánico quedan FUERA del escenario; sus filas se calculan como información y no afectan el veredicto (10.12). "
  f"No cambia el cálculo a 20 °C ni el veredicto de los capítulos 8 y 9; se obtiene con TT.thermal del {NUCLEO} (clave `termica` de tools/export_design.js, la misma que muestra la pestaña Temperatura de {TOOL}). "
  f"Los datos y su nivel de confianza A/B/C están en {REGREF}; lo que no pude leer en la norma original queda marcado con confianza C. Las alternativas con bronce (C1 a C3) se evalúan con los tapones de grafito reales (9.7).", size=9)

H("10.1 Alcance e hipótesis", 2)
table(["Alcance", "Contenido", "Efecto en el veredicto"], [
    [f"Dentro (term_alcance = {pint(TH['alcance'])})", (lambda t: t[0].upper() + t[1:])(TH["alcance_texto"].split(". Los cilindros")[0].replace("Alcance 1 (por defecto): ", "").rstrip(".")) + ".", "Entra al estado, al FU de estructura, al FU térmico y a los cambios de estado"],
    ["Fuera", "Cilindros, aceite atrapado, válvula de alivio térmico, sellos, viscosidad y bomba; accionamiento mecánico (bloque-uña, placas-guía, soporte del ojal E, pasadores de empuje, articulaciones y fatiga)", f"{pint(FA['n'])} filas informativas en la base ({pint(min(_NFA.values()))} a {pint(max(_NFA.values()))} según la alternativa, por las filas de la placa-guía de cada familia; nota 10.12): no afectan el estado, el FU ni el veredicto; term_alcance = 2 las reactiva"],
], widths=(36, 150, 81), size=7.5)
table(["Hipótesis", "Valor adoptado", "Origen y confianza"], [
    ["Temperatura del cuerpo", f"{pint(TS)} °C uniforme en todo el cuerpo; referencia de diseño y montaje {pint(T0)} °C (ΔT = {pint(TS - T0)} K)", "Pedido del mandante. Plancha horizontal de acero oscuro al sol: 58 a 70 °C medidos, 80 °C es cota alta plausible sin viento (C)"],
    ["Gradiente entre planchas", f"{n(TH['gradiente_scn'])} K entre la plancha superior (al sol) y la inferior (a la sombra) a {pint(TS)} °C; a otra temperatura se escala con ΔT/{pint(TS - T0)} K", "EN 1991-1-5 §6.1.4.1, Tabla 6.1 (18 K, tableros de puentes: otra tipología; C). Medición o análisis térmico propio por hacer"],
    ["Geometría", f"Dimensionada a {pint(T0)} °C y evaluada congelada a {pint(TS)} °C: espesores, largos de tope, número de tapones de grafito y juntas son los de 20 °C; solo se reducen las capacidades", "Criterio del núcleo (TT.thermalP). No re-dimensiona"],
    ["Capacidades", f"Factores k a {pint(TS)} °C del apartado 10.2, interpolados linealmente entre {pint(T0)} °C y {pint(TS)} °C y extrapolados con nota sobre {pint(TS)} °C", "Registro, tabla «Valores por material»"],
    ["Tapones de grafito (C1 a C3)", f"N_real y f_g real de 9.7 (bz_fg_modo = {pint(P['bz_fg_modo'])}); el bronce no se reduce a {pint(TS)} °C (k = {n(F80['k']['bz'])}, confianza C)", "Núcleo v1.2; ficha del bronce por confirmar"],
    ["Alcance", f"term_alcance = {pint(P['term_alcance'])}: sistema de placas y disco. {pint(FA['n'])} filas del accionamiento y del circuito hidráulico son informativas", "Decisión del proyecto (núcleo v1.2)"],
], widths=(40, 130, 97), size=7.5)

H("10.2 Factores de reducción por material, dilataciones y ecuaciones", 2)
T("Hipótesis. Los factores k = valor a 80 °C / valor a 20 °C salen de los parámetros kT_* del núcleo; el registro entrega solo el valor a 80 °C. Nivel de confianza: A = transcripción contrastada con copia del editor; "
  "B = ficha de fabricante o dos fuentes secundarias coherentes; C = fuente única, valor de memoria o criterio de ingeniería.", size=9)
KMAP = {"kT_Fy": "Fy", "kT_E": "E", "kT_Fy_ss": "Fy_ss", "kT_E_ss": "E_ss", "kT_p_uh": "p_uh", "kT_E_uh": "E_uh", "kT_bz": "bz", "kT_wood": "wood", "kT_bolt": "bolt", "kT_weld": "weld", "kT_hertz": "hertz", "k_mu_T": "mu"}
APLICA = {"kT_Fy": "Fy de las placas, collar, pivote y soldadura (Fy_pin, Fy_dog, Fy_pp, Fy_shoe, Fy_cara solo en la nota 10.12)", "kT_E": "E", "kT_Fy_ss": "Fy_ss (discos inox)", "kT_E_ss": "Informativo", "kT_p_uh": "p_uhmw, PV_uh", "kT_E_uh": "E_uhmw",
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
    ["Curvatura y flecha por gradiente", "κ = α·ΔT_g/h; s = κ·(D/2)²/2", "Registro, «Flexión por gradiente»; EN 1991-1-5 §6.1.4.1, Tabla 6.1"],
    ["Tensión de la plancha restringida", "σ = E·α·ΔT_g/(2·(1 − ν)); verificación combinada (dem + σ_th)/cap, suma conservadora", "Timoshenko y Woinowsky-Krieger, Theory of Plates and Shells (placa restringida); criterio del núcleo"],
    ["Buje de bronce en el cubo", "cierre = 2·[(a·α_bz·ΔT − ρ·(α_bz − α_ac)·ΔT·b) − a·α_ac·ΔT]; ρ = 2ab/[(b² + a²) − ν(b² − a²)]", "Lamé (anillo comprimido); hipótesis del revisor"],
    ["PV de la lámina UHMW", "PV(T) = PV₂₀·(80 − T)/(80 − T_ref)", "Criterio del revisor (C); Quadrant TIVAR 1000, «Limiting PV»"],
    ["Madera", "p_adm(T) = C_t·p_adm; C_t = 0,70", "NDS 2018 Tabla 2.3.3 (0,70 a 125–150 °F; 80 °C queda fuera de la tabla: extrapolación, C)"],
    ["Giro con μ distinto", "FS(f·μ) = FS_diseño/f (F lineal en μ)", "Equilibrio del capítulo 7"],
], widths=(48, 126, 93), size=7)
T(f"Resultado: acero estructural y soldadura con k = {n(F80['k']['Fy'], 3)} y {n(F80['k']['weld'], 3)} a 80 °C (confianza B y C); el inoxidable k = {n(F80['k']['Fy_ss'], 2)} en Fy (C) y el UHMW-PE k = {n(F80['k']['p_uh'], 2)} en p_adm, PV y módulo (C); el bronce k = {n(F80['k']['bz'], 3)} (C). "
  "La dilatación del UHMW (~10 mm/m más que el acero) es lo que más pesa en las juntas.", bold=True, size=9)

# ---- 10.3 resultados por alternativa
H("10.3 Resultados por alternativa: 20 °C frente a 80 °C", 2)
T("Desarrollo. Para cada alternativa, TT.thermal analiza la geometría de 20 °C con las capacidades de cada temperatura, solo para el sistema de placas y disco. FS = giro (el μ no cambia con T: k_mu = 1). FU de estructura = mayor FU de resistencia de la estructura; "
  "FU térmico = mayor FU de las verificaciones del grupo «Temperatura» dentro del alcance (juntas, gradiente, buje, UHMW). Gradiente a 80 °C de "
  f"{n(TH['gradiente_scn'])} K. Las alternativas C1 a C3 llevan los tapones de grafito reales.", size=9)
rows = []
for i in IDS:
    b0, b1 = bT(i, 0), bT(i)
    rows.append([SHORT[i], n(b0["FS"]), n(b1["FS"]), fu3(b0["fuEst"]), fu3(b1["fuEst"]), b1["gobernante"]["nombre"], fu3(b0["fuTerm"]), fu3(b1["fuTerm"]), b1["gobernanteTerm"]["nombre"]])
table(["Alternativa", "FS giro 20 °C", f"FS giro {pint(TS)} °C", "FU estructura 20 °C", f"FU estructura {pint(TS)} °C", f"Gobernante de estructura a {pint(TS)} °C", "FU térmico 20 °C", f"FU térmico {pint(TS)} °C", f"Gobernante térmico a {pint(TS)} °C"],
      rows, widths=(46, 15, 15, 17, 17, 52, 15, 15, 75), size=7, num_cols=(1, 2, 3, 4, 6, 7))
rows = []
for i in IDS:
    b0, b1 = bT(i, 0), bT(i)
    rows.append([SHORT[i], n(b0["masa"]), yn(b0["gira"]), yn(b0["estructura"]), yn(b0["termico"]), f"{b0['nFail']} / {b0['nWarn']}",
                 yn(b1["gira"]), yn(b1["estructura"]), yn(b1["termico"]), f"{b1['nFail']} / {b1['nWarn']}"])
table(["Alternativa", "Masa (kg)", "20 °C: ¿gira?", "20 °C: ¿estructura?", "20 °C: ¿térmico?", "20 °C: fallas / adv.", f"{pint(TS)} °C: ¿gira?", f"{pint(TS)} °C: ¿estructura?", f"{pint(TS)} °C: ¿térmico?", f"{pint(TS)} °C: fallas / adv."],
      rows, widths=(56, 20, 22, 26, 24, 26, 22, 26, 24, 21), size=7, num_cols=(1,))
sB, sC3, sA = bT("B"), bT("C3"), bT("A")
T(f"Resultado a {pint(TS)} °C: base FU de estructura {n(bT('base')['fuEst'])} y térmico {n(bT('base')['fuTerm'])}, cumple; A no gira (aplastamiento del tope de los discos inoxidables con Fy × {n(F80['k']['Fy_ss'], 2)}), estructura sí y térmico {fu3(sA['fuTerm'])}; "
  f"B no gira ni cumple estructura (lámina UHMW: FU {fu3(sB['fuEst'])}) y su FU térmico es {fu3(sB['fuTerm'])}; C1 FU de estructura {n(bT('C1')['fuEst'])} y C2 {n(bT('C2')['fuEst'])}, ambas cumplen; "
  f"C3 FU de estructura {fu3(sC3['fuEst'])} y FU térmico {fu3(sC3['fuTerm'])}: no cumple (plancha inferior con la σ térmica restringida). "
  "El FS de giro no cambia con la temperatura porque el μ de entrada no cambia (sensibilidad en 10.9). El aceite atrapado, los sellos y la viscosidad no se evalúan en este escenario (10.12).", bold=True, size=9)

# ---- 10.4 sensibilidad a la temperatura
H("10.4 Sensibilidad a la temperatura: 20, 40, 60, 80 y 100 °C", 2)
T(f"Desarrollo. Mismos cálculos a cada temperatura; el gradiente se escala con ΔT/{pint(TS - T0)} K; a 100 °C los factores están extrapolados desde 80 °C (sin dato publicado) y valen como orden de magnitud.", size=9)
table(["Factor"] + [f"{pint(f['T'])} °C" + (" (extrap.)" if f["extrapolado"] else "") for f in TH["factores"]],
      [[lab] + [n(f["k"][key], 3) for f in TH["factores"]] for lab, key in (("k Fy inoxidable", "Fy_ss"), ("k E inoxidable", "E_ss"), ("k p_adm, PV y E del UHMW", "p_uh"), ("k Rp0,2 pernos 10.9", "bolt"), ("k Fy del acero", "Fy"))]
      + [["α medio del acero (10⁻⁶ /K)"] + [n(f["alpha"]["st"] * 1e6, 4) for f in TH["factores"]], ["Gradiente de plancha (K)"] + [n(bT("base", k)["gradiente"]) for k in range(len(TH["T"]))]],
      widths=(70, 38, 38, 38, 38, 45), size=7.5, num_cols=(1, 2, 3, 4, 5))
TT_ = [f"{pint(t)} °C" for t in TH["T"]]
T("FS de giro (no cambia con T):", size=9, after=1)
table(["Alternativa"] + TT_, [[SHORT[i]] + [n(b["FS"]) for b in THA[i]["byT"]] for i in IDS], widths=(80, 36, 36, 36, 36, 36), size=7.5, num_cols=(1, 2, 3, 4, 5))
T("FU de estructura:", size=9, after=1)
table(["Alternativa"] + TT_, [[SHORT[i]] + [fu3(b["fuEst"]) for b in THA[i]["byT"]] for i in IDS], widths=(80, 36, 36, 36, 36, 36), size=7.5, num_cols=(1, 2, 3, 4, 5))
T("FU térmico (juntas, gradiente, buje, UHMW):", size=9, after=1)
table(["Alternativa"] + TT_, [[SHORT[i]] + [fu3(b["fuTerm"]) for b in THA[i]["byT"]] for i in IDS], widths=(80, 36, 36, 36, 36, 36), size=7.5, num_cols=(1, 2, 3, 4, 5))
T("Estado (¿gira? / ¿estructura? / ¿térmico?) y número de fallas:", size=9, after=1)
table(["Alternativa"] + TT_, [[SHORT[i]] + [f"{yn(b['gira'])} / {yn(b['estructura'])} / {yn(b['termico'])} · {b['nFail']} f." for b in THA[i]["byT"]] for i in IDS], widths=(70, 39, 39, 39, 39, 41), size=7.5)
fgB, fgA = first_fail("B", "gira"), first_fail("A", "gira")
T(f"Resultado: la base, C1 y C2 son estructuralmente insensibles a la temperatura hasta {pint(TH['T'][3])} °C (el acero no pierde Fy); lo que crece con T es el FU térmico (gradiente de la plancha) de {n(bT('base', 0)['fuTerm'])} a {n(bT('base')['fuTerm'])} a {pint(TS)} °C. "
  f"B es la más sensible: pierde el giro desde {pint(fgB)} °C y la estructura desde {pint(first_fail('B', 'estructura'))} °C (FU {n(bT('B', 2)['fuEst'])} a {pint(TH['T'][2])} °C). A pierde el giro desde {pint(fgA)} °C. "
  f"C3 supera FU térmico 1,00 desde {pint(first_fail('C3', 'termico'))} °C. A {pint(TH['T'][4])} °C todas pierden la estructura, incluso la base (gradiente de {n(bT('base', 4)['gradiente'])} K, FU térmico {n(bT('base', 4)['fuTerm'])}).", bold=True, size=9)

# ---- 10.5 cambios de estado
H("10.5 Verificaciones que cambian de estado entre 20 y 80 °C", 2)
T("Desarrollo. Se comparan, fila a fila, los estados a 20 y 80 °C dentro del alcance. El primer bloque es común a todas las alternativas (valores de la base); "
  "los siguientes son propios de cada alternativa. Confianza = nivel del dato reducido.", size=9)
base_names = {c["nombre"]: (c["de"], c["a"]) for c in bT("base")["cambian"]}


def crows(L, tag):
    return [[tag, c["grp"], c["nombre"], EST.get(c["de"], c["de"]), EST.get(c["a"], c["a"]), "—" if c["fu20"] is None else fu3(c["fu20"]), "—" if c["fuT"] is None else fu3(c["fuT"]), c["conf"]] for c in L]


rows = crows(bT("base")["cambian"], "Todas")
for i in ("A", "B", "C1", "C2", "C3"):
    spec = [c for c in bT(i)["cambian"] if base_names.get(c["nombre"]) != (c["de"], c["a"])]
    rows += crows(spec, i) if spec else [[i, "—", "Sin cambios adicionales a los comunes", "—", "—", "—", "—", "—"]]
table(["Alt.", "Grupo", "Verificación", "20 °C", f"{pint(TS)} °C", "FU 20 °C", f"FU {pint(TS)} °C", "Conf."], rows, widths=(14, 28, 140, 20, 20, 15, 15, 15), size=6.5, num_cols=(5, 6))
nA = [c for c in bT("A")["cambian"] if c["grp"] == "Interfaz inox"]
gsup = next(c for c in bT("base")["cambian"] if "Gradiente: plancha superior" in c["nombre"])
T(f"Resultado: en A y B el aplastamiento del tope de los discos inoxidables pasa de FU {fu3(nA[0]['fu20'])} a {fu3(nA[0]['fuT'])} con Fy × {n(F80['k']['Fy_ss'], 2)}; "
  "en B además fallan la lámina UHMW (espesor, aplastamiento del canto y del tope, PV) y la junta; en C3 la plancha inferior con la σ térmica pasa de advertencia a falla. "
  "Lo común a todas las alternativas es el gradiente de las planchas, que pasa de cumple a advertencia (FU " + fu3(gsup["fuT"]) + " en la plancha superior de la base).", bold=True, size=9)

# ---- 10.6 juntas
H("10.6 Juntas de dilatación de los sectores", 2)
T("Hipótesis. Cada sector se coloca con la junta en frío j_disp = máx(j_sec; dilatación a ΔT de montaje) del diseño a 20 °C. A 80 °C el sector de material con mayor α que el acero crece más que su respaldo y, si la junta se cierra, se comprime y pandea. "
  "j_req = (α_pieza − α_acero)·ΔT·cuerda, con la cuerda del sector a R_o. Referencia: registro, «Cálculos del revisor» (UHMW: ~10 mm/m más que el acero). Las pastillas de C3 y los sectores de C1 y C2 conservan su número y junta de 9.7.", size=9)
rows = []
for i in IDS:
    js = THA[i]["juntas"]
    if not js:
        rows.append([i, "Sin sectores en la interfaz", "—", "—", "—", "—"])
    for j in js:
        rows.append([i, j["pieza"], n(j["j_req"]), n(j["j_disp"]), fu3(j["fu"]), EST.get(j["estado"], j["estado"])])
table(["Alt.", "Pieza", "j_req (mm)", "j_disp en frío (mm)", "FU", "Estado"], rows, widths=(14, 120, 30, 38, 25, 40), size=7.5, num_cols=(2, 3, 4))
jb = MED["junta_B"]
jUH = next(j for j in THA["B"]["juntas"] if "UHMW" in j["pieza"]); jUH2 = next(j for j in jb["juntas"] if "UHMW" in j["pieza"])
T(f"Resultado: el UHMW requiere {n(jb['j_req'])} mm de junta y dispone de {n(jUH['j_disp'])} mm en frío (j_sec = {n(jb['j_sec_actual'])} mm; el resto es la dilatación a ΔT de montaje): la junta se cierra (FU {fu3(jUH['fu'])}). "
  f"Adoptar j_sec ≥ {n(jb['j_sec_nuevo'])} mm: con ese valor la junta pasa a FU {fu3(jUH2['fu'])} ({EST.get(jUH2['estado'], jUH2['estado']).lower()}, al límite) y la masa de B a 20 °C pasa de {n(jb['masa20_actual'], 4)} a {n(jb['masa20'], 4)} kg. "
  "Los sectores de inox y bronce (junta requerida ≈ 0,1 mm) cumplen con holgura.", bold=True, size=9)

# ---- 10.7 holguras del buje
H("10.7 Holgura del buje de bronce y dilatación global", 2)
T("Hipótesis. El buje de bronce (Ø int. D_piv, Ø ext. D_piv + 30) va en el cubo de acero, con holgura diametral en frío c_bush_d (supuesto de ajuste H7/e8; el núcleo no define el ajuste). "
  "Referencias: Lamé para el anillo comprimido; EN 1993-1-1 §3.2.6 y EN 1993-1-2 §3.4.1.1 para ε. Las holguras uña–pasador y patín–guía dependen del accionamiento y quedan fuera de alcance (10.12).", size=9)
table(CHC, [crow(c, True) for c in filas("base", ("b", "k"))], widths=CWC, size=6.5, num_cols=(2, 3, 5))
bj = filas("base", ("b",))[0]; kj = filas("base", ("k",))[0]
T(f"Resultado: el buje cierra {n(bj['dem'])} mm de los {n(bj['cap'])} mm de holgura diametral (FU {fu3(bj['fu'])}), sin riesgo de agarrotar el pivote. La mesa crece {n(kj['dem'])} mm en diámetro y la base {n(kj['cap'])} mm (dilatación libre, sin tensión). "
  "Son iguales en todas las alternativas.", bold=True, size=9)

# ---- 10.8 gradiente
H("10.8 Gradiente entre planchas, curvatura y flecha", 2)
T(f"Hipótesis. Plancha superior al sol, inferior a la sombra, gradiente de {n(TH['gradiente_scn'])} K, caja de h = {n(P['h_disc'])} mm y Ø {n(P['D_top'])} mm. La mesa libre se curva sin tensión (κ = α·ΔT_g/h, flecha s = κ·(D/2)²/2); "
  "si la restricción de la caja fuera total, la plancha toma σ = E·α·ΔT_g/(2(1 − ν)) que se suma, de forma conservadora, a la tensión global + local. Referencias: EN 1991-1-5 §6.1.4.1 Tabla 6.1 (otra tipología) y Timoshenko.", size=9)
table(CHC, [crow(c, True) for c in filas("base", ("d",))], widths=CWC, size=6.5, num_cols=(2, 3, 5))
gs = filas("base", ("d",))
T(f"Resultado: κ = {n(gs[0]['dem'])} 1/m y flecha {n(gs[1]['dem'])} mm en el diámetro de la mesa, despreciable; la tensión térmica restringida de {n(gs[2]['dem'])} MPa lleva la plancha superior a FU {fu3(gs[3]['fu'])} y la inferior a {fu3(gs[4]['fu'])} (advertencia, no falla). "
  f"En C3, que ya tiene la plancha inferior a FU {n(bT('C3', 0)['fuEst'])} a 20 °C, la suma pasa de 1,00 (ver 10.5 y 10.11).", bold=True, size=9)

# ---- 10.9 sensibilidades
H("10.9 Sensibilidades: μ, Fy del acero, bronce y k_p / k_E del UHMW", 2)
T("Desarrollo. Cada sensibilidad cambia un solo factor a 80 °C y repite todas las verificaciones del alcance.", size=9)
T("a) μ de la interfaz a 80 °C (FS(f·μ) = FS_diseño/f; el μ real a 80 °C no tiene fuente: la grasa fluye y se expulsa; el μ de la opción C es dato fijo, ver G3 en 9.7.7).", bold=True, size=9, after=1)
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
    rows.append([SHORT[i], fu3(b["fuEst"]), fu3(k["fuEst"]), k["gobernante"]["nombre"], fu3(b["fuTerm"]), fu3(k["fuTerm"]), yn(k["gira"]), yn(k["estructura"]), pint(len(k["empeoran"]))])
table(["Alternativa", "FU estructura (k = 1)", "FU estructura (k = 0,92)", "Gobernante", "FU térmico (k = 1)", "FU térmico (k = 0,92)", "¿Gira?", "¿Estructura?", "Verificaciones que empeoran"],
      rows, widths=(50, 25, 27, 60, 24, 26, 13, 20, 22), size=7, num_cols=(1, 2, 4, 5, 8))
bz = THA["C3"]["sens"]["bz090"]
T(f"Resultado: con k = 0,92 el FU de estructura sube {n(THA['base']['sens']['kFy092']['dFu'])} (de {n(bT('base')['fuEst'])} a {fu3(THA['base']['sens']['kFy092']['fuEst'])}) y varias verificaciones pasan a advertencia; la plancha superior con la σ térmica llega a FU "
  f"{fu3(THA['base']['sens']['kFy092']['fuTerm'])} y la estructura deja de cumplir. Con bronce × 0,90 (C1 a C3) no cambia ninguna: C3 queda con FU de estructura {fu3(bz['fuEst'])}.", bold=True, size=9)
T("c) UHMW-PE (alternativa B): k_p (p_adm y PV) y k_E (módulo) a 80 °C.", bold=True, size=9, after=1)
us = THA["B"]["sens"]["uhmw"]
table(["Variación", "k_p", "k_E", "FU máximo de la lámina", "Gobernante", "¿Cumple?"],
      [["k_p"] + [n(r["k_p"], 2), n(r["k_E"], 2), fu3(r["fuUHMW"]) if r["fuUHMW"] < 50 else "> 50", r["gobernante"], yn(r["cumple"])] for r in us["kp"]] +
      [["k_E"] + [n(r["k_p"], 2), n(r["k_E"], 2), fu3(r["fuUHMW"]) if r["fuUHMW"] < 50 else "> 50", r["gobernante"], yn(r["cumple"])] for r in us["kE"]],
      widths=(25, 15, 15, 40, 140, 25), size=7, num_cols=(1, 2, 3))
T(f"Resultado: con k_p = {n(P['kT_p_uh'], 2)} la lámina falla; solo cumple si k_p ≥ {n(us['kp_crit'], 2)}. El módulo reducido casi no cambia el resultado (manda la presión admisible). "
  "Sin la curva del proveedor entre 20 y 80 °C, la alternativa B no se puede acreditar a 80 °C.", bold=True, size=9)

# ---- 10.10 BTH-1
H("10.10 Rango térmico de ASME BTH-1 y filas pendientes", 2)
bth = [f for f in bT("base")["filas"] if "BTH-1" in f["nombre"]][0]
grs = filas("base", ("g",))[0]
T("Hipótesis. Las pletinas, el collar y las soldaduras de las placas se verifican con criterios de AISC 360-22 y AWS D1.1; el accionamiento (cadena de empuje) se verifica por analogía con ASME BTH-1, Categoría de diseño B (Nd = 3,0), y queda fuera de este escenario. "
  f"BTH-1 define un rango estándar de servicio de −4 a 66 °C (25 a 150 °F); {pint(TS)} °C (176 °F) queda fuera de ese rango y Nd = 3,0 no incluye un margen térmico explícito. La sección exacta de BTH-1 no está confirmada (fuentes secundarias: Hoist Magazine, Tandemloc). "
  "La fila permanece como pendiente porque el núcleo la emite también con alcance 1.", size=9)
table(CHC, [crow(bth, True)] + [crow(c, True) for c in filas("base", ("j", "g")) if c is not bth], widths=CWC, size=6.5, num_cols=(2, 3, 5))
T(f"Resultado: {pint(TS)} °C excede el rango estándar en {pint(TS - 66)} K; usar BTH-1 en este escenario requiere una decisión de persona calificada y el registro de la hipótesis. Si el mandante mantiene {pint(TS)} °C, "
  f"la sensibilidad con k_Fy = 0,92 (10.9 b) es la referencia: el FU de estructura queda en {fu3(THA['base']['sens']['kFy092']['fuEst'])}. La grasa trabaja a {pint(TS)} °C con margen de {n(grs['cap'] - grs['dem'])} K bajo su punto de goteo (FU {fu3(grs['fu'])}).", bold=True, size=9)

# ---- 10.11 medidas
H("10.11 Medidas recomendadas (sistema de placas y disco)", 2)
T("Desarrollo. Las medidas con efecto numérico se evaluaron con el núcleo a 80 °C (tools/export_alternativas.js, clave `medidas`). La válvula de alivio térmico no es medida de este escenario: ver la nota informativa 10.12.", size=9)
c3 = MED["c3_t_bot"]
g0 = MED["gradiente"][0]["alts"]; g10 = MED["gradiente"][2]
Lnew = AL["A"]["topes"][0]["L"] * nA[0]["fuT"]
table(["N°", "Medida", "Efecto cuantificado por el núcleo", "Fuente o referencia"], [
    ["1", f"Junta en frío de los sectores j_sec ≥ {n(jb['j_sec_nuevo'])} mm (UHMW de B)", f"j_req {n(jb['j_req'])} mm frente a {n(jUH['j_disp'])} mm disponibles; con j_sec = {n(jb['j_sec_nuevo'])} mm la junta queda en FU {fu3(jUH2['fu'])}. No basta para B: ver medida 4",
     "Registro, «Cálculos del revisor» (α UHMW 180 a 200×10⁻⁶ /K)"],
    ["2", "A y B: ampliar el largo del tope de los discos inoxidables o aumentar h_c", f"El aplastamiento sube a FU {fu3(nA[0]['fuT'])} con Fy × {n(F80['k']['Fy_ss'], 2)}; el largo requerido es ≈ {n(Lnew)} mm (hoy {n(AL['A']['topes'][0]['L'])} mm; σ ∝ 1/L; límite R_o − R_i − 100 = {n(AL['A']['Ro'] - AL['A']['Ri'] - 100)} mm). Estimación lineal: confirmar con el núcleo",
     "ASME BTH-1 §3-3.3; EN 10088-2 de memoria (C)"],
    ["3", "C3: engrosar la plancha inferior o reducir el gradiente (sombra, pintura clara, cubierta)", f"t_bot {n(c3[0]['t_bot'])} → {n(c3[1]['t_bot'])} mm: FU de estructura {fu3(c3[0]['fuEst'])} → {fu3(c3[1]['fuEst'])}, FU térmico {fu3(c3[0]['fuTerm'])} → {fu3(c3[1]['fuTerm'])}, +{n(c3[1]['masa20'] - c3[0]['masa20'])} kg. "
     f"Con gradiente de {n(g10['gradiente'])} K (en vez de {n(TH['gradiente_scn'])}) el FU térmico de C3 es {fu3(g10['alts']['C3']['fuTerm'])} y su estructura {'cumple' if g10['alts']['C3']['estructura'] else 'no cumple'}; sin gradiente, FU térmico {fu3(g0['C3']['fuTerm'])}", "AISC 360-22 (σ ≤ 0,6Fy); EN 1991-1-5 Tabla 6.1 (gradiente, C)"],
    ["4", "B: no acreditar la lámina de UHMW a 80 °C sin la curva del proveedor (límite de servicio continuo = 80 °C)", f"Falla en espesor, canto, tope, PV y junta; solo cumpliría con k_p ≥ {n(us['kp_crit'], 2)}", "Fichas Quadrant/Mitsubishi TIVAR 1000, Ensinger PE1000, Röchling Polystone M"],
    ["5", "Protección solar de la mesa (sombra, pintura clara, ventilación)", f"FU térmico de la base {fu3(g0['base']['fuTerm'])} sin gradiente, {fu3(g10['alts']['base']['fuTerm'])} con {n(g10['gradiente'])} K y {n(bT('base')['fuTerm'])} con {n(TH['gradiente_scn'])} K; a {pint(TH['T'][4])} °C ya {n(bT('base', 4)['fuTerm'])} (10.4)", "Registro, «Temperatura superficial estimada»"],
    ["6", "Registrar la decisión de persona calificada sobre el rango térmico de BTH-1", f"{pint(TS)} °C excede −4 a 66 °C en {pint(TS - 66)} K", "ASME BTH-1 (sección por confirmar)"],
], widths=(8, 78, 118, 63), size=7)

# ---- 10.12 nota informativa
H("10.12 Nota informativa: accionamiento y circuito hidráulico (fuera de alcance)", 2)
T(f"Hipótesis. Con term_alcance = {pint(P['term_alcance'])} el núcleo calcula igual las {pint(FA['n'])} filas del accionamiento mecánico y del circuito hidráulico, pero las marca «fuera de alcance»: no entran al estado, al FU térmico, al veredicto ni a los cambios de estado, y no generan medidas. "
  "Se informan solo como dato referencial. Con term_alcance = 2 el núcleo las reactiva y reproduce el escenario completo anterior.", size=9)
table(["Grupo (fuera de alcance)", "Filas", "Fallarían (informativo)", "Avisarían (informativo)"],
      [[g["grp"], pint(g["n"]), pint(g["fail"]), pint(g["warn"])] for g in FA["por_grupo"]] + [["Total", pint(FA["n"]), pint(FA["fail"]), pint(FA["warn"])]],
      widths=(110, 25, 40, 40), size=7.5, num_cols=(1, 2, 3))
T("Filas informativas con estado de falla o advertencia (80 °C):", size=9, after=1)
table(["Grupo", "Verificación", "Demanda", "Capacidad", "Unidad", "FU", "Estado informativo", "Referencia"],
      [[f["grp"], f["nombre"], n(f["dem"]), "—" if f.get("cap") is None else n(f["cap"]), f["unidad"], "—" if f.get("fu") is None else fu3(f["fu"]), EST.get(f["estado_informativo"], f["estado_informativo"]), f["ref"]] for f in FA["filas_aviso"]],
      widths=(34, 78, 16, 16, 12, 12, 22, 77), size=6.5, num_cols=(2, 3, 5))
T("Dato referencial del aceite atrapado: Δp = (α_v − 3α_s)·ΔT/(1/K_aceite + 1/K_c), α_v = 7,5×10⁻⁴ /K (registro, «Presión por aceite atrapado»; ISO 4413:2010, cláusula por confirmar); "
  f"K_c = E/{{2·[(b² + 1)/(b² − 1) + ν]}} (Lamé, cilindro de pared gruesa b/a = {n(P['ba_cil'])}, K_c = {n(AC80['Kc_lame_MPa'] / 1000)} GPa).", size=9)
table(["T (°C)", "ΔT (K)", "Rígido, K = 1,4 / 1,9 GPa (bar)", "Cilindro (Lamé), K = 1,4 / 1,9 GPa (bar)", "Manguera (bar)", "Cilindro, K alta (bar)"],
      [[pint(a["T"]), pint(a["dT"]), f"{n(a['rigido']['bajo'])} / {n(a['rigido']['alto'])}", f"{n(a['cilindro']['bajo'])} / {n(a['cilindro']['alto'])}", n(a["manguera"]), n(a["seleccion_bar"])] for a in TH["aceite"]],
      widths=(25, 25, 62, 68, 40, 47), size=7.5, num_cols=(0, 1, 2, 3, 4, 5))
dp = AC80["cilindro"]["alto"]
T(f"NOTA (no es medida del escenario): un tramo de aceite aislado entre la válvula de retención o bloqueo y un tope mecánico, calentado de {pint(T0)} a {pint(TS)} °C, tendría Δp = {n(dp)} bar con K = 1,9 GPa en el cilindro "
  f"({n(AC80['cilindro']['bajo'])} bar con 1,4 GPa; {n(AC80['rigido']['alto'])} bar si el contenedor fuera rígido y {n(AC80['manguera'])} bar solo con manguera), frente a la presión máxima de trabajo de {n(MED['p_max_cil'])} bar. "
  "CONDICIÓN: la sobrepresión aparece solo con el movimiento restringido (pistón contra tope mecánico o cadena de empuje bloqueada, válvulas cerradas); si el pistón puede moverse bajo carga muerta, la expansión sale como carrera y la presión se mantiene en W/A. "
  "Si el mandante amplía el alcance a term_alcance = 2, la protección de ese tramo (válvula de alivio térmico propia en el tramo, no el alivio de sistema aguas arriba) pasa a ser medida del escenario.", bold=True, size=9)
T("Supuestos del circuito hidráulico fuera de alcance (informativos, confianza C):", size=9, after=1)
table(["N°", "Supuesto", "Responsable"], [[pint(k), s_, "Fabricante del aceite, de la bomba, del cilindro y de los sellos"] for k, s_ in enumerate(TH["supuestos_fuera_alcance"], 1)], widths=(10, 170, 87), size=7.5, num_cols=(0,))

# ---- 10.13 supuestos C
H("10.13 Supuestos de confianza C a confirmar con el proveedor", 2)
CONF_C = {"UHMW": ("kT_p_uh", "Curva de módulo y de límite elástico del UHMW-PE de 20 a 80 °C, creep y desgaste a T", "Proveedor del UHMW (Quadrant/Mitsubishi, Ensinger, Röchling)"),
          "Inoxidable": ("kT_Fy_ss", "Rp0,2 del inox a 80–100 °C (EN 10088-2: 157 y 166 MPa a 100 °C de memoria; una página de EN 10269 da 177 y 187 MPa)", "Proveedor del inox / EN 10088-2"),
          "Bronce": ("kT_bz", "Fy, α y límite de temperatura del bronce C95400 (la ficha hallada es de C93200) y su fracción real de grafito (9.7)", "Proveedor del bronce grafitado"),
          "Madera": ("kT_wood", "C_t a 80 °C y α de la madera; NCh1198 (factor KT sin dato)", "Proveedor de la madera / NDS 2018 / NCh1198"),
          "Pernos": ("kT_bolt", "Rp0,2 a 100 °C de la clase 10.9 (ISO 898-1, anexo informativo)", "ISO 898-1 / proveedor de pernos"),
          "Soldadura": ("kT_weld", "Criterio térmico de servicio de AWS D1.1:2020 (no lo hay)", "Revisor"),
          "Gradiente": ("dT_grad", "Gradiente real de una caja de ~230 mm al sol", "Medición o análisis térmico propio"),
          "μ": ("k_mu_T", "μ de la grasa a 80 °C y su punto de goteo del producto elegido", "Ensayo de aceptación / proveedor de la grasa"),
          "Holgura buje": ("c_bush_d", "Ajuste real del buje en el pivote (H7/e8 supuesto)", "Proveedor del buje / proyectista")}
rows = []
for k, s_ in enumerate([x for x in TH["supuestos_C"] if not x.startswith("Madera")], 1):   # la madera (W) está en stand by
    key = next((kk for kk in CONF_C if kk in s_), None)
    pid, que, quien = CONF_C[key] if key else (None, "Confirmar", "Revisor")
    val = (n(TH["gradiente_scn"]) if pid == "dT_grad" else n(P[pid], 3)) + ("" if PL[pid]["u"] == "–" else " " + PL[pid]["u"]) if pid else "—"
    rows.append([pint(k), s_, val, que, quien])
table(["N°", "Supuesto del núcleo", "Valor del parámetro", "Dato a confirmar", "Responsable"], rows, widths=(8, 70, 28, 100, 61), size=7, num_cols=(0,))
T("Resultado: ningún resultado térmico de este capítulo debe tomarse como definitivo mientras estos supuestos no se confirmen; los de mayor efecto son el factor de capacidad del UHMW (decide B), el gradiente de planchas (decide C3 y el margen de la base) "
  f"y el factor del inoxidable (decide A). Los supuestos del circuito hidráulico ({pint(len(TH['supuestos_fuera_alcance']))}) no entran al escenario (10.12).", bold=True, size=9)

# ================================================================= 9. RESUMEN
ps = doc.add_section()   # vuelve a vertical
ps.orientation = WD_ORIENT.PORTRAIT; ps.page_width, ps.page_height = Mm(210), Mm(297)
ps.left_margin = ps.right_margin = Mm(20); ps.top_margin = Mm(20); ps.bottom_margin = Mm(18)
header_footer(ps)
H("11. Resumen de resultados")
vd = D["verdict"]
cnt = {s: sum(1 for v in VER if v["estado"] == s) for s in EST}
HO_ = ACC["holguras"]["adoptada"]
table(["Resultado", "Valor"], [
    ["Accionamiento por defecto", f"Pivotado tipo KIET (drive_mode = {pint(P['drive_mode'])}): 2 cilindros en ojales E diagonales (R_E = {pint(PIV['R_E'])} mm), bloque-uña libre en Q (L_qp = {pint(PIV['L_qp'])} mm, cara R{pint(PIV['bloque_una']['R_cara'])}) y 4 placas-guía curvas G1 ({PIV['placa_leva']['familia_nombre']}); sincronía {n(PIV['placa_leva']['sincronia'])} mm (peor caso {n(PIV['placa_leva']['sincronia_peor'])})"],
    ["Cubierta de madera W", "EN STAND BY (6.2): fuera de esta entrega"],
    ["¿Gira?", "Sí" if vd["gira"] else "NO"], ["¿Estructura verifica?", "Sí" if vd["estructura"] else "NO"],
    ["Utilización máxima (global / de resistencia)", f"{fu3(vd['fuMax'])} / {fu3(PVM['gobernante_resistencia']['fu'])} ({PVM['gobernante_resistencia']['nombre']})"],
    ["FS del accionamiento (diseño / contaminado / borde)", f"{fu3(cd['FS'])} / {fu3(casos['cont']['FS'])} / {fu3(casos['borde']['FS'])}"], ["Presión de diseño", n(cd["p"], unit="bar")],
    ["Masa total (interfaz base)", f"{n(m['total'], 5, 'kg')} pivotado; {n(GUM['masa'], 5, 'kg')} con el guiado con leva (alternativa, 7.3)"],
    ["Holguras ajustadas aceptadas por el mandante (7.2.7)", f"Cajón del ojal E dentro de la base FU {fu3(HO_['cajon']['fu'])}; Q fuera de la mesa FU {fu3(HO_['Q']['fu'])}; B = {pint(HO_['B'])} mm; tolerancia de posición del cajón ajustada en planos"],
    ["AF2 (6.3)", f"{pint(ACC['af2']['tornillos']['n'])} × {ACC['af2']['tornillos']['designacion']} en R{pint(ACC['af2']['tornillos']['r'])}; disco de la mesa {pint(ACC['af2']['tss2'])} mm"],
    ["Verificaciones", f"{len(VER)}: {cnt['ok']} cumplen, {cnt['warn']} advertencias, {cnt['fail']} no cumplen, {cnt['info']} informativas, {cnt['pend']} pendientes"],
], widths=(70, 100))
T("Verificaciones que gobiernan (mayor FU):", bold=True, size=9.5)
gov = sorted([v for v in VER if v["estado"] not in ("info",) and v.get("fu") is not None], key=lambda v: -v["fu"])[:12]
table(["Verificación", "Grupo", "FU", "Referencia"], [[v["nombre"], v["grp"], fu3(v["fu"]), v["ref"]] for v in gov],
      widths=(72, 25, 13, 60), size=8, num_cols=(2,))
T("Las verificaciones geométricas con FU cercano a 1,00 son mínimos constructivos (holgura, filete mínimo, presión nominal) y no admiten desviaciones de fabricación mayores; "
  f"la más ajustada del accionamiento es el cajón del ojal E dentro de la base ({n(HO_['cajon']['cap'] - HO_['cajon']['dem'], 2)} mm, 7.2.7). Están controladas por las tolerancias y ajustes de la lámina TT300C-GEN-004-C y por el plan de inspección TT300C-GEN-003-C.", size=9)
T("Accionamiento: pivotado (por defecto) frente a guiado con leva (7.4):", bold=True, size=9.5)
table(["Magnitud", "Pivotado (por defecto)", "Guiado con leva", "Observación"], [r for r in cmp_rows if not r[0].startswith(("Componente", "Empuje neto", "Advertencias"))], widths=(44, 42, 42, 42), size=7.5)
T(f"Alternativas de interfaz (capítulo 9) y escenario solar a {pint(TS)} °C, sistema de placas y disco (capítulo 10):", bold=True, size=9.5)
table(["Alternativa", "Masa (kg)", "FS giro", "FU estructura 20 °C", f"FU estructura {pint(TS)} °C", f"FU térmico {pint(TS)} °C", f"¿Cumple a {pint(TS)} °C? (giro / estructura / térmico)"],
      [[SHORT[i], n(AL[i]["masa"]), n(AL[i]["giro"]["FS"]), n(bT(i, 0)["fuEst"]), n(bT(i)["fuEst"]), n(bT(i)["fuTerm"]), f"{yn(bT(i)['gira'])} / {yn(bT(i)['estructura'])} / {yn(bT(i)['termico'])}"] for i in IDS],
      widths=(48, 16, 13, 20, 20, 20, 33), size=7.5, num_cols=(1, 2, 3, 4, 5))
T(f"A {pint(TS)} °C la base, C1 y C2 conservan giro, estructura y grupo térmico; A no gira (tope de los discos con Fy × {n(F80['k']['Fy_ss'], 2)}) pero cumple estructura y térmico; "
  f"B no gira ni cumple estructura (lámina UHMW) y su FU térmico es {n(bT('B')['fuTerm'])}; C3 no cumple (FU de estructura {n(bT('C3')['fuEst'])}, FU térmico {n(bT('C3')['fuTerm'])}: plancha inferior más σ térmica). "
  "El alcance del escenario es solo el sistema de placas y disco: el aceite atrapado, la válvula de alivio térmico, los sellos, la viscosidad/bomba y el accionamiento mecánico están fuera (nota informativa 10.12).", size=9)
T(f"Opción C, tapones de grafito (9.7): con el patrón Ø{ng(d_)} · paso {ng(p_)} caben {pint(TG['C1']['N_real'])} tapones en C1 y C2 y {pint(TG['C3']['N_real'])} en C3 (ideal {pint(TG['C1']['N_ideal'])} y {pint(TG['C3']['N_ideal'])}); "
  f"f_g real {n(TG['C1']['fg_real'])} frente a {n(TG['C1']['fg_ideal'])} ideal y {n2(P['bz_fg_min'])} exigido como aviso. El máximo alcanzable con η ≥ {n2(P['bz_eta_min'])} es {n(cn1['fg_max_alcanzable'])}: el criterio de lubricación queda como aviso permanente "
  "y se resuelve con el proveedor del bronce (9.7.8).", size=9)
H("Conclusión", 2)
T(("Con los parámetros indicados la tornamesa TT300-C gira la carga de {0} tf en el caso de diseño con FS = {1} y todas las verificaciones estructurales "
   "y geométricas cumplen (utilización máxima {2}; de resistencia {3}) con el accionamiento pivotado tipo KIET por defecto, de {4} kg. El guiado con leva de reenganche positiva también cumple "
   "({5} kg, FS = {6}, con la advertencia aceptada de la uña) y queda como alternativa.").format(pint(P["W_tf"]), fu3(cd["FS"]), fu3(vd["fuMax"]), fu3(PVM["gobernante_resistencia"]["fu"]),
                                                                    n(m["total"], 5), n(GUM["masa"], 5), fu3(GUM["cd"]["FS"])) if vd["gira"] and vd["estructura"] else
  "ATENCIÓN: la configuración actual no cumple todas las verificaciones; ver capítulo 8.", bold=True)
T(f"A {pint(TS)} °C (capítulo 10) la geometría dimensionada a {pint(T0)} °C sigue girando y verificando la estructura y el grupo térmico en la configuración base (FU {n(bT('base')['fuEst'])} y {n(bT('base')['fuTerm'])}): "
  "el servicio a 80 °C del sistema de placas y disco queda condicionado a la decisión sobre el rango térmico de ASME BTH-1 y a confirmar los supuestos de confianza C. "
  "El accionamiento y el circuito hidráulico no se evaluaron en este escenario (nota 10.12). En la opción C la fracción real de grafito está por debajo del criterio de lubricación y debe confirmarse con el proveedor.", bold=True)

# ================================================================= 10. PENDIENTES
H("12. Datos faltantes, hipótesis y puntos a confirmar")
H("12.1 Datos faltantes e hipótesis del accionamiento", 2)
T("Hipótesis. Donde falta el dato del proveedor o una decisión, el cálculo usa el valor indicado y lo declara como HIPÓTESIS o PENDIENTE; el efecto se cuantifica con las filas del núcleo. "
  "Ninguna de estas hipótesis debe tomarse como confirmada para fabricar.", size=9)
_vrow = lambda rx: next(c for c in VER if re.search(rx, c["nombre"]))
_vas, _pan, _capa = _vrow(r"^Vástago: flexocompresión"), _vrow(r"^Pandeo del vástago"), _vrow(r"capa templada")
_zap = [(f_["cam_mat"], c) for f_ in FAM for c in f_["filas"] if c["estado"] == "pend"]
_pendV = [c for c in VER if c["estado"] == "pend"]
_DF = [
    ["Proveedor del cilindro: Fy del vástago", "FALTA", f"Fy = {pint(P['pv_Fyrod'])} MPa (HIPÓTESIS: acero templado y cromado)", f"Flexocompresión del vástago FU {fu3(_vas['fu'])} (AISC 360-22 §H1.1, Ec. H1-1a)"],
    ["Proveedor del cilindro: tipo de ojal (rótula o casquillo) y μ de los ojales E y Q", "FALTA", f"μ = {n(P['pv_muE'])} (pv_muE), ojales comerciales para pasadores Ø{pint(P['pv_dE'])} (E) y Ø{pint(P['pv_dq'])} (Q)", "Momento de roce en el vástago, cara del bloque (μ_Q) y autobloqueo del retorno; con rótula autolubricada el μ baja"],
    ["Proveedor del cilindro: d_rod y longitud entre ojales L", "A CONFIRMAR", f"d_rod = {pint(P['d_rod'])} mm; L0 = {pint(P['L0'])} mm; L extendida = L0 + carrera = {pint(P['L0'] + P['stroke'])} mm; K = 1", f"Pandeo del vástago FU {fu3(_pan['fu'])} y flexocompresión"],
    ["Temple del canto de la placa-guía y de la cara del bloque-uña", "ESPECIFICACIÓN", f"{FPL['tratamiento']['canto']}; cara del bloque {FAB['bloque_una']['cara']['templada']}; Fy_sup = {pint(P['Fy_surf'])} MPa", f"Hertz y capa templada (FU {fu3(_capa['fu'])}); certificado de dureza y profundidad (EN 10328)"],
    ["Material y forma de la zapata del seguidor, familias 2–4", "PENDIENTE", "Familia 1 (acero templado, sin zapata) por defecto; en 2–4 la zapata plana no apoya sobre el canto curvo", ("Filas «Pendiente» del núcleo: zapata plana sobre el canto curvo, flecha l²/(8·R_mín) = " + "; ".join(f"{n(c['dem'])} mm (familia {pint(k)})" for k, c in _zap) + (lambda m_: f" frente a {m_.group(1)} mm admisible para usar p = H/(l·t)" if m_ else "")(re.search(r"flecha ≤ ([0-9,]+) mm", _zap[0][1]["formula"]))) if _zap else "—"],
    ["Retención axial del pivote", "A DEFINIR (mandante / calculista)", "Pivote calado en el asiento sin tope ni tapa; el cálculo verifica el asiento y la flexión, no la extracción axial", "Definir tope, tapa o verificación del aprieto frente a la extracción antes de liberar la lámina del pivote"],
    ["Pendientes «PROPUESTO» de los planos", "A CONFIRMAR", "Grado comercial del material por el Fy del cálculo; WPS pre-calificados; sistema de pintura ISO 12944 C4; torques de pernos; ajustes ISO 286", "Confirmación del calculista y del fabricante (láminas GEN-005, GEN-006, GEN-008, GEN-012)"],
    ["Unión J17 (cubo–planchas de la mesa)", "PENDIENTE DE CONFIRMACIÓN", f"Por defecto CJP con bisel en la plancha según AWS D1.1/D1.1M:2020 Fig. 5.2 (J17a plancha inferior t = {pint(P['t_bot'])} mm; J17b plancha superior t = {pint(P['t_top'])} mm)", "Confirmar con el WPS del fabricante y la inspección (UT)"],
    ["Roce de la cara y del canto", "HIPÓTESIS", f"μ_s = {n(P['mu_s'])}; μ_leva = {n(PL_['mu'])} ({PL_['familia_nombre']})", "Fuerza del cilindro y autobloqueo; ensayo de aceptación"],
    ["Bloque alineado con el vástago en el retorno", "HIPÓTESIS (conservadora)", "Modelo del retorno", "w_nec y sincronía"],
    ["Dilatación", "HIPÓTESIS", f"Mesa a 80 °C y base a 20 °C: δ = pv_tolg + α·ΔT·R_pin = {n(PL_['tolerancias_mm'])} mm", "Margen de sincronía m + δ"],
    ["Dimensiones de KIET", "NO SE TRASLADAN", "Solo el concepto constructivo (placa rectangular empernada con recorte en media luna)", "—"],
]
table(["Dato", "Estado", "Hipótesis usada en esta memoria", "Efecto o acción"], _DF, widths=(34, 28, 58, 50), size=7.5)
if _pendV:
    T("Filas del núcleo con estado «Pendiente» (diseño por defecto):", size=9, after=1)
    table(VH, ifrows(_pendV), widths=VW, size=6.5, num_cols=(2, 3, 5))
H("12.2 Otros puntos a confirmar antes de fabricar", 2)
_PEND = [
    ["1", "Ficha del cilindro", f"Ø{pint(P['D_bore'])}/Ø{pint(P['d_rod'])} × {pint(P['stroke'])}; L0 {pint(P['L0'])}; e_cuerpo ≥ {pint(P['e_body'])}; c_vástago ≥ {pint(P['c_rod'])}; cuerpo Ø ≤ {pint(P['D_body'])}; {pint(P['m_cyl'])} kg; ojales con rótula", "Proveedor"],
    ["2", "Ojales del cilindro pivotado y pandeo", f"Ojal del vástago para pasador Ø{pint(P['pv_dq'])} (Q) y ojal trasero para Ø{pint(P['pv_dE'])} (E), con rótula; pandeo del cilindro biarticulado con el vástago a L0 + carrera (la fila del núcleo usa solo el vástago)", "Proveedor del cilindro"],
    ["3", "Fricción de la cara del bloque-uña y del contacto con la placa-guía", f"μ_s = {n(P['mu_s'])}; μ de la leva = {n(PIV['placa_leva']['mu'])} ({PIV['placa_leva']['familia_nombre']}); μ_E = {n(P['pv_muE'])}", "Ensayo de aceptación (plan de inspección TT300C-GEN-003-C)"],
    ["4", "Numeración de artículos de ASME BTH-1", "§3-2, §3-3, §3-4 de la edición vigente", "Revisor"],
    ["5", "Tamaño mínimo de filete", "AWS D1.1/D1.1M:2020, tabla de tamaño mínimo", "Revisor"],
    ["6", "Puntos de izaje soldables (1d)", "Comerciales certificados, WLL ≥ 1,6 t c/u", "Proveedor"],
    ["7", "Losa o mats de apoyo", f"q ≈ {n(DV['q_max'], unit='MPa')}", "Tercero"],
    ["8", "Artículo de ISO 4413:2010 (sobrepresión por aceite atrapado)", "Fuera del alcance térmico (10.12); numeral por citar solo si el mandante amplía a term_alcance = 2", "Revisor"],
    ["9", "Tolerancia de posición del cajón del ojal E (7.2.7)", f"Holgura «cajón dentro de la base» de {n(ACC['holguras']['adoptada']['cajon']['cap'] - ACC['holguras']['adoptada']['cajon']['dem'], 2)} mm (FU {fu3(ACC['holguras']['adoptada']['cajon']['fu'])}) y «Q fuera de la mesa» de {n(ACC['holguras']['adoptada']['Q']['cap'] - ACC['holguras']['adoptada']['Q']['dem'])} mm (FU {fu3(ACC['holguras']['adoptada']['Q']['fu'])}), aceptadas por el mandante con B = {pint(P['B'])}: tolerancia de posición ajustada en planos e inspección dimensional", "Proyectista / inspección"],
    ["9a", "Modo guiado con riel-leva, si se adopta (7.5)", f"Resorte de retorno de la uña: recorrido ≥ {n(GUM['K']['travel'] + 5)} mm, largo comprimido + tope ≤ {pint(P['s_sp'])} mm, 150 a 300 N; μ_g = {n(P['mu_g'])}, μ retorno ≤ {n(P['mu_ret'])}; la leva retiene la uña solo en el {n(GUM['levaGuiada']['fraccion_empuje_retenida'] * 100, 2)} % del empuje", "Proveedor / ensayo"],
    ["10", "Interfaz con placa de bronce y grafito (C), si se adopta", f"Aleación (C95400, Fy {pint(P['Fy_bz'])} MPa), p_adm {pint(P['p_bz'])} MPa, PV, desgaste y μ de catálogo; ensayo de arranque (stick-slip); disco duro (≥ 100 HB sobre el bronce, Ra ≤ 0,4 µm); fijación desmontable por sectores con topes (verificada) y ranuras de engrase; par galvánico y sellado; láminas INT del juego de planos que se genera a pedido para la variante C (capítulo 14)", "Proveedor / proyectista"],
    ["10a", "Fracción real de grafito de los tapones (C), 9.7", f"Patrón Ø{ng(d_)} · paso {ng(p_)}: f_g real {n(TG['C1']['fg_real'])} (C1, C2) y {n(TG['C3']['fg_real'])} (C3), ideal {n(TG['C1']['fg_ideal'])}; bz_fg_min = {n2(P['bz_fg_min'])} es supuesto C (aviso permanente). Confirmar con el proveedor del bronce autolubricado su fracción real de grafito y ensayar el μ con el patrón real; si exige más de {n(fg_cota, 2)} → bronce con lubricante sólido distribuido o ranuras de grafito, no tapones", "Proveedor / ensayo de aceptación"],
    ["10b", "Criterio de conteo y de pared de los tapones (G2, G4), 9.7.7", f"Tolerancia de 1e-6 mm en «≥ bz_edge» (empates en {pint(TAP['empates']['n_con_empate'])} de {pint(TAP['empates']['n_patrones'])} patrones del barrido); pared de {ng(P['bz_edge'])} mm junto a bordes frente a profundidad del tapón de {n(PROF_TAP)} mm", "Proveedor del bronce / revisor"],
    ["11", "Interfaz inoxidable (A) o con UHMW (B), si se adopta", "μ, p_adm y E_ap del UHMW son datos de catálogo; par inox–inox de aleaciones distintas o tratada contra el gripado; fijación y retención de los discos; sectores de UHMW con juntas de dilatación; láminas INT del juego de planos que se genera a pedido para la variante A o B (capítulo 14); en AF2 (A pegada) el par lo toman los tornillos avellanados de 6.3; discos pegados con epóxico estructural y respaldo granallado sin pintura; respaldo canteado ≤ 3 mm en el borde; tornillos avellanados M6; sellado perimetral; retención de los sectores de UHMW por rebaje o cola de milano; fluencia de la lámina (asentamiento 0,1 a 0,2 mm)", "Proveedor / proyectista"],
    ["12", "Certificados de material", f"Bloque-uña y uña Re ≥ {pint(P['Fy_dog'])} MPa; pasadores Re ≥ {pint(P['Fy_pin'])} MPa; placas-guía Re ≥ {pint(P['Fy_camP'])} MPa ({FPL['material'].split(',')[0]}); patín Fy ≥ {pint(P['Fy_shoe'])} MPa (3.1)", "Proveedor"],
    ["13", "Temple por inducción de caras de contacto", f"≥ 55 HRC (σy ≥ {pint(P['Fy_surf'])} MPa), profundidad según capítulo 8", "Proveedor / inspección"],
    ["14", "NOTA informativa: válvula de alivio térmico del tramo cilindro + retenciones (fuera de alcance)", f"No forma parte del escenario (term_alcance = {pint(P['term_alcance'])}); dato referencial Δp = {n(dp)} bar a {pint(TS)} °C, solo con movimiento restringido; no hay válvula en el diseño base (alivio_term = {n(P['alivio_term'])}); ver 10.12. Decidir si se amplía el alcance a term_alcance = 2", "Mandante / proveedor hidráulico"],
    ["15", "Decisión sobre el rango térmico de ASME BTH-1", f"{pint(TS)} °C excede −4 a 66 °C; requiere decisión de persona calificada (10.10, 10.11)", "Revisor / mandante"],
    ["16", "Junta en frío de los sectores de UHMW (B), si se adopta", f"j_sec ≥ {n(MED['junta_B']['j_sec_nuevo'])} mm (requerida {n(MED['junta_B']['j_req'])} mm a {pint(TS)} °C); B no se acredita a {pint(TS)} °C sin la curva del proveedor (10.6, 10.9)", "Proveedor del UHMW"],
    ["17", "Supuestos de confianza C del escenario solar", f"{pint(len([x for x in TH['supuestos_C'] if not x.startswith('Madera')]))} supuestos listados en 10.13 (UHMW, inox, bronce, pernos, soldadura, gradiente, μ, buje); los {pint(len(TH['supuestos_fuera_alcance']))} del circuito hidráulico quedan fuera de alcance", "Proveedores / revisor"],
    ["18", "Filete máximo de almas y nervios", "El núcleo exige w ≤ t_alma; AISC 360-22 §J2.2b da t − 2 mm para t ≥ 6 mm (9.5)", "Revisor"],
]
table(["N°", "Ítem", "Supuesto en esta memoria", "Responsable"], [[pint(k)] + r[1:] for k, r in enumerate(_PEND, 1)], widths=(9, 45, 85, 31), size=8)

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

# ================================================================= 14. PLANOS (paquete Rev. C, generado a pedido)
# Los juegos de planos ya no se guardan en el repositorio: se generan a pedido con el generador local (tools/servidor_planos.py, pestaña «Planos» de la herramienta).
# Este capítulo describe el juego y cómo obtenerlo; no lee archivos de entregables/ ni de salidas/.
SER = {"GEN": "Generales: notas, normas e índice; inspección; tolerancias y ajustes ISO 286; materiales; tratamientos; soldaduras; torques y compras; supuestos y brechas; cortes de plancha; lista de verificación",
       "CON": "Conjunto general, despiece, explosionadas, instructivo de armado por pasos y subconjuntos (base, ménsula, mesa, accionamiento, pivote, interfaz)",
       "BAS": "Piezas de la base (plancha, collar, marco, ménsula)", "IZA": "Orejas de izaje", "ACC": "Accionamiento: modo pivotado (BAS-008…011, ACC-013…018; placa-guía curva ACC-020 en el sentido antihorario y ACC-024 en el horario, dibujada desde los segmentos del núcleo) y modo guiado con riel-leva (BAS-005…007, ACC-001…012 y 019)",
       "MES": "Piezas de la mesa (planchas, anillos, almas, nervios, cubo y pasadores de empuje)", "PIV": "Pivote, buje y tapas",
       "INT": "Interfaz de giro (discos, sectores, topes, tapones de grafito, ranuras y fijaciones); solo en las alternativas A, B y C"}
REL = {"GEN": "Capítulos 2, 12 y Anexo A (normas, tolerancias, soldaduras, brechas con el cálculo, lista de verificación)", "CON": "Capítulos 3, 5, 7 y 8", "BAS": "Capítulos 5 y 8 (base)", "IZA": "9.4 (orejas de izaje)",
       "ACC": "Capítulo 7 (7.2 pivotado, 7.3 placa-guía, 7.5 guiado) y grupos Uña, Articulaciones, Soporte del ojal E y Placas-leva del capítulo 8", "MES": "Capítulos 5 y 8 (mesa, pasadores de empuje)", "PIV": "Capítulos 6 y 9.3 (pivote, collar, buje)",
       "INT": "Capítulos 6, 9.1 a 9.2 y 9.7 (interfaz, topes y tapones de grafito: patrón S09 con N_real)"}
H("14. Planos asociados (paquete Rev. C, generado a pedido)")
T("Hipótesis. El paquete de planos de fabricación Rev. C (nomenclatura TT300C-SSS-nnn-C, con SSS la serie y C la revisión) se genera a pedido para la alternativa y los parámetros elegidos en la herramienta, "
  "con el mismo JSON del núcleo que esta memoria (tools/export_design.js): planos y cálculo no tienen valores a mano distintos. El repositorio no guarda juegos de planos; el juego se obtiene con el generador local "
  "(Generar_planos_Tornamesa.bat, pestaña «Planos» de la herramienta, botón «Generar planos») y queda en salidas/<fecha-hora>_<alternativa>/. "
  "Estado: emitido para revisión; NO válido para fabricación hasta su revisión y aprobación por un ingeniero calculista habilitado.", size=9)
table(["Magnitud", "Valor"], [
    ["Cómo se obtiene", "Una vez: Instalar_generador_planos.bat (Python 3.12/3.11 y requirements-planos.txt). Luego: Generar_planos_Tornamesa.bat y, en la pestaña «Planos», «Generar planos» (unos 4 a 6 minutos)"],
    ["Grupos del juego", "Generales (GEN-*, CON-001 a CON-003, despiece completo), Fabricación (subconjuntos soldados, interfaz y piezas) y Armado (explosionadas, secuencia e instructivo de armado), cada uno en su PDF"],
    ["Archivos del juego", "PDF por lámina y por grupo, PDF combinado con marcadores, DXF por lámina y ZIP, modelo 3D STEP/GLB, despiece CSV/XLSX, soldaduras, lista de cortes, controles de cotas y de completitud, informe_paquete.md y lista de verificación del revisor"],
    ["Controles que condicionan la emisión", "El generador se niega a emitir (código ≠ 0) si el diseño no gira, la estructura no cumple, hay interferencias en el 3D, cotas que no coinciden con el sólido, textos superpuestos, entidades fuera del marco o cadenas de cotas defectuosas"],
], widths=(55, 115), size=8.5)
T("Desarrollo. Series de láminas y su relación con los capítulos de la memoria:", bold=True, size=9, after=1)
table(["Serie", "Contenido", "Relación con la memoria"],
      [[k, SER[k], REL[k]] for k in SER], widths=(14, 92, 64), size=8)
QA = ROOT / "docs" / "qa" / "revision_exhaustiva_RevC"
_qa1 = []
for ln in (QA / "LEEME.md").read_text(encoding="utf-8").splitlines():
    if ln.startswith("| ") and not ln.startswith("| Frente") and not ln.startswith("|---"):
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) >= 6 and c[0] in ("A", "B", "C"):
            _qa1.append(c)
_qa2_txt = (QA / "segunda_vuelta.md").read_text(encoding="utf-8")
_st = {}
for ln in _qa2_txt.split("## 2. Hallazgos nuevos")[0].splitlines():
    if ln.startswith("| ") and not ln.startswith("| ID") and not ln.startswith("|---"):
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) >= 3:
            k_ = re.sub(r"\*", "", c[2])
            k_ = "OK" if k_.startswith("OK") and "Regr" not in k_ and "problema" not in k_ else ("Abierto (declarado y confirmado)" if k_.startswith("Abierto") else
                 ("Parcial o con regresión" if ("Parcial" in k_ or "Regr" in k_ or "problema" in k_ or "solo en parte" in k_) else ("No corregido" if k_.startswith("NO") else "No procede (razón válida)")))
            _st[k_] = _st.get(k_, 0) + 1
_mN = re.search(r"\*\*Conteo de la tabla 2:\*\*\s*(\d+) hallazgos nuevos, (\d+) mayores \(([^)]*)\) y (\d+) menores", _qa2_txt)
_qa_log = subprocess.run(["git", "log", "--format=%h %s", "ef6113a..HEAD", "--", "cad"], cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip().splitlines()
_qa_fix = [x for x in _qa_log if x.split(" ", 1)[1].startswith("Planos TT300-C")]
H("14.1 Revisión independiente de planos y estado", 2)
T("Hipótesis. La revisión exhaustiva de planos Rev. C (docs/qa/revision_exhaustiva_RevC/) la hacen revisores independientes del generador, que solo reportan hallazgos; "
  "la primera vuelta revisó los 8 juegos (base, A, AF2, B, C1, C2, C3, W) y la segunda verificó las correcciones y agregó hallazgos nuevos. Los conteos se leen de los propios informes.", size=9)
table(["Frente (primera vuelta)", "Alcance", "Críticos", "Mayores", "Menores", "Accionamiento"], [c[:6] for c in _qa1] +
      [["Total", "—", pint(sum(int(c[2]) for c in _qa1)), pint(sum(int(c[3]) for c in _qa1)), pint(sum(int(c[4]) for c in _qa1)), "—"]], widths=(28, 62, 18, 18, 18, 26), size=8, num_cols=(2, 3, 4))
table(["Segunda vuelta: estado verificado de los hallazgos de la primera", "Cantidad"], [[k_, pint(v_)] for k_, v_ in sorted(_st.items(), key=lambda x: -x[1])] + [["Total", pint(sum(_st.values()))]],
      widths=(130, 40), size=8, num_cols=(1,))
T((f"Hallazgos nuevos de la segunda vuelta: {_mN.group(1)} ({_mN.group(2)} mayores, {_mN.group(3)}, y {_mN.group(4)} menores). " if _mN else "") +
  f"Después de la segunda vuelta se registran {pint(len(_qa_fix))} commits de corrección de planos («Planos TT300-C: …», que citan los hallazgos que atienden: H-, N-, B-, A-); "
  "no hay todavía en docs/qa un informe de una tercera vuelta que verifique esas correcciones.", size=9)
T("Resultado: la revisión independiente sigue abierta. Las dos vueltas no cubrieron las láminas del accionamiento (ACC-*, CON-010, CON-018 y los pasos de montaje), que se rediseñaron después con el modo pivotado, "
  "la placa-guía curva (ACC-020 y ACC-024) y el riel-leva del guiado. Antes de emitir para fabricación hacen falta la revisión independiente de esas láminas (incluida la tolerancia de posición del cajón del ojal E de 7.2.7) "
  "y una vuelta de verificación de las correcciones posteriores a la segunda vuelta. La cubierta de madera W queda fuera (stand by).", bold=True, size=9)
T("Los datos que el cálculo aún no define (WPS, sistema de pintura, grado del material, catálogo del proveedor, firmas) se rotulan «A DEFINIR» en cada lámina; las brechas y las decisiones requeridas están en la lámina TT300C-GEN-009-C. "
  "Los torques de pernos son propuesta, a confirmar por el calculista (TT300C-GEN-008-C). El índice de láminas está en TT300C-GEN-001-C y el detalle de controles en informe_paquete.md de cada juego.", size=9)

# ================================================================= 15. MODIFICACIONES DE LA REV. C Y CONTROL DE CAMBIOS
H("15. Modificaciones de la Rev. C y control de cambios")
H("15.1 Lista de modificaciones de esta edición", 2)
_gx = lambda args: subprocess.run(["git"] + args, cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip().splitlines()
_PCH = ["pv_dwell", "Fy_camP", "Fu_camP", "pv_nb", "pv_db", "pv_rmin", "pv_tolg", "pv_Fub", "pv_dd", "pv_Fyrod", "pv_rface", "pv_bu", "pv_ecr"]
table(["N°", "Modificación", "Dónde", "Origen"], [
    ["1", f"Placa-guía curva G1 en lugar de la placa-leva poligonal: flanco recto a {n(PL_['alpha_deg'])}°, biarcos tangentes y canto como envolvente exacta a d_Q/2; placa {n(FPL['marco']['largo'])} × {n(FPL['marco']['ancho'])} × {pint(FPL['t'])} mm "
          f"de {FPL['material'].split(',')[0]} con canto templado; {pint(PBT['n'])} tornillos {PBT['norma'].split(' (')[0]} {PBT['clase']} y {pint(PPS['n'])} pasadores de posición por placa", "7.3", "Inconsistencias I1 a I8 del diseño original (7.3.1); docs/qa/guia_curva_KIET/cambios.md"],
    ["2", f"Empuje guiado con Q apoyado en el canto (equilibrio del pasador Q): F_dis {n(ocs['dis']['F'])} → {n(cd['F'])} kN, p {n(ocs['dis']['p'])} → {n(cd['p'])} bar, FS {fu3(ocs['dis']['FS'])} → {fu3(cd['FS'])}", "7.2.2, 7.2.3, 7.4", "I4: rodilla E–Q–P inestable en compresión"],
    ["3", f"Retorno y sincronía con tolerancias y dilatación: m + δ = {n(PL_['margen_diseno'])} mm; sincronía {n(PL_['sincronia'])} mm (peor caso {n(PL_['sincronia_peor'])})", "7.2.4", "I3"],
    ["4", f"Cara cilíndrica convexa R{pint(BU['R_cara'])} del bloque-uña; cuerpo {pint(BU['b_cuerpo'])} mm acodado {pint(BU['e_acodado'])} mm; contacto a {n(BU['contacto_cara'])} mm del eje", "7.2.5", "I9: el contacto con roce caía en la arista de la cara plana"],
    ["5", f"Vástago en flexocompresión (AISC 360-22 §H1.1, §E3, Ap. 8) con Fy = {pint(P['pv_Fyrod'])} MPa como HIPÓTESIS; pasador Q con la reacción de la placa (ASME BTH-1 §3-3.3)", "7.3.5 C", "Carga transversal del cilindro biarticulado"],
    ["6", "Comparación placa-leva original / placa-guía curva / concepto KIET (KIET medido en el plano de referencia, sin trasladar dimensiones) y figuras numeradas", "7.4", "Pedido del mandante"],
    ["7", "Cubierta de madera W EN STAND BY: fuera de las tablas de alternativas y del escenario solar", "6.2, 9, 10", "Decisión del mandante (docs/standby/madera_W/LEEME.md)"],
    ["8", "Datos faltantes e hipótesis del accionamiento (proveedor del cilindro, temple, zapata de las familias 2–4, retención axial del pivote, pendientes PROPUESTO, unión J17)", "12.1", "Pedido del mandante"],
    ["9", "Modo guiado con riel-leva renumerado como alternativa; comparación de modos con el empuje guiado", "7.5, 7.6", "Reordenamiento del capítulo 7"],
    ["10", "Formato: FU con 3 decimales; texto negro; leyenda de revisión por ingeniero calculista habilitado; norma y ecuación en cada verificación", "Todo el documento", "Formato del usuario"],
    ["11", "Parámetros nuevos o con valor por defecto cambiado: " + "; ".join(f"{k} = {pint(P[k]) if float(P[k]).is_integer() else n(P[k], 3)}" for k in _PCH if k in P), "Anexo D", "Núcleo (tests/golden/params_defaults.json)"],
], widths=(9, 92, 24, 45), size=7.5)
H("15.2 Control de cambios", 2)
_mem = [l.split(" ", 2) for l in _gx(["log", "--date=short", "--format=%h %ad %s", "--", "tools/memoria_tt300c.py"]) if "emoria" in l][:8]
table(["Edición", "Fecha", "Descripción", "Commit"], [["Rev. C (esta edición)", D["fecha"], "Placa-guía curva, empuje guiado, cara del bloque-uña, comparación con el original y KIET, W en stand by, datos faltantes", NUCLEO]] +
      [["Rev. C (anterior)", c[1], c[2], c[0]] for c in _mem], widths=(26, 18, 100, 26), size=7.5)
_core = [l.split(" ", 2) for l in _gx(["log", "--date=short", "--format=%h %ad %s", "-12", "--", "packages/core"])]
T("Historial reciente del núcleo de cálculo (packages/core; la memoria se regenera con el último):", size=9, after=1)
table(["Commit", "Fecha", "Cambio del núcleo"], [[c[0], c[1], c[2]] for c in _core], widths=(18, 20, 132), size=7.5)
T(LEYENDA, bold=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
table(["", "Nombre", "Registro profesional", "Firma", "Fecha"], [["Revisó y aprobó: ingeniero calculista habilitado", "", "", "", ""]], widths=(50, 40, 30, 30, 20), size=9)

# ================================================================= ANEXO A
H("Anexo A. Control de calidad del cálculo")
T("A.1 Revisor cruzado (cálculo independiente dentro de la herramienta)", bold=True, size=9.5)
table(["Control", "Herramienta", "Independiente", "Dif. %", "Tol. %", "Resultado", "Nota"],
      [[c["name"], n(c["tool"], 4), n(c["indep"], 4), n(c["d"]), "—" if c["tol"] is None else n(c["tol"]), "Cumple" if c["ok"] else "NO", c.get("note", "")]
       for c in D["revisionCruzada"]], widths=(55, 20, 20, 13, 12, 15, 35), size=7.5, num_cols=(1, 2, 3, 4))
T("A.2 Otros controles", bold=True, size=9.5)
ctrl = [["Auditoría normativa", "Toda verificación tiene fórmula y referencia" if D["auditoria"]["ok"] else "Faltan referencias: " + ", ".join(D["auditoria"]["missing"])],
        ["Verificadores independientes (Python, sin leer el código JS)", "tests/indep_tt300c.py, indep_accionamiento.py, indep_interfaz.py (incluye las filas AF2), indep_izaje_collar.py e indep_termica.py contra el modo guiado (tests/golden/tt300c_guiado.json); "
         "tests/indep_pivotado.py para el modo pivotado por defecto; se ejecutan con npm test"],
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
  "B = ficha de fabricante o coherencia entre dos fuentes secundarias; C = fuente única, valor de memoria o criterio de ingeniería. Las filas de aceite, sellos y bomba del registro son informativas: el circuito hidráulico está fuera del alcance del capítulo 10 (nota 10.12).", size=9)
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


# ================================================================= ANEXO C (horizontal): parámetros añadidos en la versión 1.2
doc.add_page_break()
H("Anexo C. Parámetros añadidos en la versión " + VERSION + " del núcleo")
T(f"Parámetros del {NUCLEO} que gobiernan el alcance térmico y los tapones de grafito. Definición (etiqueta, unidad, valor por defecto y rango) tomada de TT.PARAM_GROUPS por tools/export_alternativas.js; valor = el usado en esta memoria.", size=9)
USO = {"term_alcance": "Capítulo 10", "bz_fg_modo": "9.7", "bz_edge": "9.7.1, 9.7.5", "bz_fg_min": "9.7.6", "bz_fg_estricto": "9.7.6", "bz_eta_min": "9.7.6", "bz_n_tor": "9.7.1, 9.7.5", "d_tor": "9.7.1, 9.7.5"}
table(["Id", "Parámetro", "Unidad", "Valor", "Por defecto", "Mínimo", "Máximo", "Dónde se usa"],
      [[q["id"], q["lab"], q["u"], n(q["valor"], 3), n(q["def"], 3), n(q["min"], 3), n(q["max"], 3), USO.get(q["id"], "—")] for q in ALT["parametros_v12"]],
      widths=(24, 140, 14, 14, 18, 14, 14, 29), size=7, num_cols=(3, 4, 5, 6))

# ================================================================= ANEXO D (horizontal): parámetros del accionamiento
H("Anexo D. Parámetros del accionamiento (modo, levas y modo pivotado)")
T(f"Parámetros del {NUCLEO} que definen el modo de accionamiento, la leva de reenganche del modo guiado (cam_*) y el modo pivotado (pv_*). Definición tomada de TT.PARAM_GROUPS por tools/export_alternativas.js; "
  "valor = el usado en esta memoria (diseño por defecto). Los cam_* solo actúan con drive_mode = 1 y opt_cam = 1; los pv_*, con drive_mode = 2.", size=9)
table(["Id", "Parámetro", "Unidad", "Valor", "Por defecto", "Mínimo", "Máximo"],
      [[q["id"], q["lab"], q["u"], n(q["valor"], 4) if not isinstance(q["valor"], str) else q["valor"], q["def"] if isinstance(q["def"], str) else n(q["def"], 4), n(q["min"], 4), n(q["max"], 4)] for q in ALT["parametros_accionamiento"]],
      widths=(18, 170, 13, 14, 16, 18, 18), size=6.5, num_cols=(3, 4, 5, 6))

# ================================================================= salida
name = f"TT300-C_Memoria_Rev{REV}"
docx = OUT / f"{name}.docx"
doc.save(docx)
# Letras negras siempre: también en los estilos heredados de la plantilla de python-docx (estilos de tabla no usados con colores de tema)
import zipfile
_tmp = docx.with_suffix(".tmp")
with zipfile.ZipFile(docx) as zin, zipfile.ZipFile(_tmp, "w", zipfile.ZIP_DEFLATED) as zout:
    for it in zin.infolist():
        data = zin.read(it.filename)
        if it.filename.startswith("word/") and it.filename.endswith(".xml"):
            data = re.sub(rb"<w:color [^>]*/>", b'<w:color w:val="000000"/>', data)                       # color de texto
            data = re.sub(rb'(\sw:color=")[^"]*(")', rb"\g<1>000000\g<2>", data)                         # bordes y sombreados: color de línea negro
            data = re.sub(rb'\sw:theme(?:Color|Shade|Tint|Fill|FillShade|FillTint)="[^"]*"', b"", data)   # sin colores de tema
        zout.writestr(it, data)
_tmp.replace(docx)
with zipfile.ZipFile(docx) as zin:                        # control: ningún color distinto de 000000 ni colores de tema en el XML
    for it in zin.infolist():
        if it.filename.startswith("word/") and it.filename.endswith(".xml"):
            _x = zin.read(it.filename)
            assert not re.search(rb'w:color="(?!000000")', _x) and not re.search(rb"<w:color (?!w:val=\"000000\")", _x) and b"w:theme" not in _x.replace(b"w:themeFontLang", b""), f"color no negro en {it.filename}"
print(docx)
if "--no-pdf" not in sys.argv:
    r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(docx)], capture_output=True, text=True, timeout=300)
    print(OUT / f"{name}.pdf" if (OUT / f"{name}.pdf").exists() else r.stderr)
    try:                                                   # control del PDF: todo el texto en negro
        import pymupdf
        _col = {}
        with pymupdf.open(OUT / f"{name}.pdf") as _pdf:
            for _pg in _pdf:
                for _b in _pg.get_text("dict")["blocks"]:
                    for _l in _b.get("lines", []):
                        for _s in _l["spans"]:
                            if _s["text"].strip():
                                _col[_s["color"]] = _col.get(_s["color"], 0) + 1
        print("colores de texto en el PDF (sRGB entero: tramos):", _col)
        assert set(_col) == {0}, "texto no negro en el PDF"
    except ImportError:
        print("pymupdf no disponible: control de color del PDF omitido")
# Entrega: copia a entregables/RevC (junto con el JSON de alternativas del que salen los datos de los capítulos 9 y 10)
if ENTREGA.is_dir() and "--no-entrega" not in sys.argv:
    for f in (docx, OUT / f"{name}.pdf", OUT / "TT300-C_alternativas.json", OUT / "TT300-C_design.json"):
        if f.exists():
            shutil.copy2(f, ENTREGA / f.name)
            print("copiado a", ENTREGA / f.name)
