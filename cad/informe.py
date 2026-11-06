"""Brechas con el cálculo, despiece CSV/XLSX, lista de verificación del revisor e informe del paquete."""
import csv, math, sys, pathlib, shutil
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import *
import lista


def brechas(ctx, rep):
    g, P, DV, D = ctx.g, ctx.P, ctx.DV, ctx.D
    G_ = []

    def add(tema, desc, decision):
        G_.append(dict(id=f"B-{len(G_) + 1:02d}", tema=tema, desc=desc, decision=decision))
    tr = DV["tRev"]
    if abs(tr - 15) > 1:
        add("Tiempo por vuelta", f"El mandante indicó 15 min/vuelta «ya definido en el cálculo», pero D['derivados'].tRev = {fm(tr, 1)} min (Q_pump = {fm(P['Q_pump'], 1)} L/min, t_vuelta_obj = {fm(P['t_vuelta_obj'], 0)}, D['bomba'].Qreq = {fm(D['bomba'].get('Qreq', 0), 1)}). Los planos rotulan el valor del JSON.",
            "Confirmar el caudal de bomba o fijar t_vuelta_obj = 15 en el cálculo y regenerar.")
    if g.opt and g.removable:
        lay = ctx.m.layout
        hb, hm = ctx.m.info["tope_h"]
        tb_, tm_ = hb + 1, hm + 1
        filas = []
        for v in D["verificaciones"]:
            if "aplastamiento del tope sobre el canto" in v["nombre"] and v.get("dem") and v.get("cap"):
                filas.append(v)
        fu = "; ".join(f"{v['nombre'].split(':')[0][:40]}: FU núcleo {fm(v['dem'] / v['cap'], 2)}" for v in filas)
        add("Altura y soldadura del tope", f"El núcleo calcula el aplastamiento con el espesor completo t como altura de contacto y el filete w_tope = {fm(lay.w_tope, 0)} con brazo t/2, pero no define la altura de la barra ni su alojamiento. "
            f"Se dibuja h = t − 1 (S02): {fm(hb, 0)} mm (lado base) y {fm(hm, 0)} mm (lado mesa). Un filete de pierna {fm(lay.w_tope, 0)} " + ("NO cabe" if min(hb, hm) <= lay.w_tope else "cabe con poco margen") + f" en una barra de esa altura y, con alivio de soldadura, la altura de contacto efectiva queda en t − w_tope − 1 ≤ {fm(min(tb_, tm_) - lay.w_tope - 1, 0)} mm (≈ 0). {fu}.",
            "El calculista debe fijar la geometría del tope (altura, alojamiento, alivio del cordón) y reverificar aplastamiento y soldadura; se sugiere topes más altos que el disco con rebaje en el respaldo o barras soldadas en la cara opuesta.")
        add("Cantidad y posición de tornillos de posición", "El núcleo fija solo d_tor y verifica la cabeza; la cantidad (2 por sector) y la posición son supuesto S01.", "Confirmar o definir cantidad, posición y torque.")
    if g.opt:
        add("Radio interior de la interfaz y collar", f"El núcleo usa R_i = D_piv/2 + 15 = {fm(g.Ri_core, 0)} mm para el área, la masa y el largo del tope UHMW (R_o − R_i − 100); el collar Ø{fm(g.D_boss, 0)} obliga a R_i ≥ {fm(g.Ri_if, 1)} mm (S07). "
            f"Efecto: área de contacto −{fm((g.Ri_if ** 2 - g.Ri_core ** 2) / (g.Ro ** 2 - g.Ri_core ** 2) * 100, 2)} %, barras UHMW {fm(g.tope_L('uhmw'), 0)} mm en lugar de {fm(g.Ro - g.Ri_core - 100, 0)} mm.", "Actualizar R_i del núcleo con el collar (D_boss) y reverificar.")
    if g.opt == 2 or g.opt == 1 or g.opt == 3:
        pass
    if g.opt == 2:
        add("Opción B sin engrase", "El núcleo no define ranuras ni graseras para la opción B (UHMW sobre inox «con grasa limpia»); no se dibujan.", "Definir si B lleva engrase y su geometría.")
    if g.wood:
        mm = {p.key: p for p in ctx.m.parts}
        add("Cubierta de madera: anillo, bolsillos y abertura", f"El núcleo calcula la madera como anulo Ø{fm(P['D_top'], 0)}/Ø{fm(g.hole_top, 0)} sin anillo de acero. Se dibuja anillo 10×{fm(P['t_wood'], 0)} ({fm(mm['madera_anillo'].mass_total, 1)} kg, fuera del núcleo), abertura Ø{fm(g.cb_D, 0)} para la tapa de inspección y {g.N_pin} bolsillos sobre los pernos de pasador (S06): "
            f"madera 3D {fm(mm['madera'].mass_total, 1)} kg frente a {fm(ctx.M['wood'], 1)} kg del núcleo.", "Definir el anillo (ancho, altura), ancho de tablón, fijación y la masa a incluir en m.total.")
    if g.boss and g.delta < 1:
        add("Collar y rebaje del cubo sin interfaz", f"Con Δ = 0 la cara superior del collar (z = {fm(g.tb + g.h_boss, 0)}) coincide con el techo del rebaje del cubo: contacto cara a cara sin holgura.", "Definir holgura vertical collar–cubo (p. ej. ≥ 2 mm).")
    if g.boss and g.delta > 2:
        add("Buje y rebaje del cubo", f"El buje arranca en z = {fm(g.z_bush0, 0)} y el techo del rebaje está en z = {fm(g.tb + g.delta + g.h_boss, 0)}: {fm(g.delta - 2, 0)} mm del buje quedan sin guiar en el cubo (engrane {fm(P['L_bush'] - (g.delta - 2), 0)} de {fm(P['L_bush'], 0)} mm).", "Verificar la presión del buje con el engrane real o subir el buje.")
    add("Izaje de la mesa", "El cálculo solo define las 4 orejas de la base; no hay puntos de izaje de la mesa (los cáncamos M30 de la Rev. B anterior sobre plancha de 20 mm no engranan la profundidad exigible).", "Definir izaje de la mesa (orejas o cáncamos verificados).")
    add("Retención axial del pivote", "El núcleo verifica asiento y flexión, no la extracción axial del pivote (ajuste p6/H7 sin soldadura, 42CrMo4 no soldable).", "Definir retención (tope inferior, anillo o interferencia verificada).")
    add("Torque de pernos y tornillos", "El núcleo no entrega torques (pernos M20×45 de pasadores, M10 de tapas, tornillos de posición).", "Definir torques de apriete (ISO 898-1 / VDI 2230).")
    add("Tamaño de soldaduras sin parámetro", "Marco, esquinas, orejas de ménsula y anillo de madera no tienen tamaño en P; se adopta el mínimo AWS D1.1 por la parte más gruesa. El filete del collar (10 mm) sale del texto de la verificación del núcleo.", "Confirmar o parametrizar tamaños y END.")
    add("Diferencias de fórmula del patín", "La masa del patín del núcleo difiere del modelo (alojamiento abierto por la cara superior y cuello de la lengüeta): −0,3 % en la pieza.", "Informativo (dentro de tolerancia).")
    add("Cilindro comercial", f"Largo ojal–ojal L0 = {fm(P['L0'], 0)} mm y masa {fm(P['m_cyl'], 0)} kg son supuestos del núcleo; el modelo 3D usa la geometría de extremos del núcleo.", "Confirmar con el proveedor del cilindro.")
    return G_


def explicar_masas(ctx, rep):
    g, P = ctx.g, ctx.P
    L = []
    ms = rep["masas"]
    for r in ms["comp"]:
        if abs(r["dif_pct"]) <= 0.5:
            continue
        gr = r["grupo"]
        t = f"{r['pieza']}: 3D {fm(r['modelo3d'], 1)} kg frente a {fm(r['nucleo'], 1)} kg ({fm(r['dif_pct'], 2)} %). Causas: "
        if gr in ("ss", "bz", "uhmw") and g.opt:
            lay = ctx.m.layout
            n = g.n_sec
            rho = {"ss": RHO_SS, "bz": P["rho_bz"] * 1e-6, "uhmw": RHO_UH}[gr]
            causas, tot = [], 0.0
            if gr != "uhmw":
                capas = [(l, lay.L_base if l["lado"] == "base" else lay.L_mesa) for l in g.stack if (gr == "ss" and l["id"] in ("disc_base", "disc_mesa", "cara") and not (g.opt == 3 and g.conf == 2)) or (gr == "bz" and (l["id"] == "bronce" or (l["id"] == "cara" and g.conf == 2)))]
                tsum = sum(l["t"] for l, _ in capas)
                hole = rho * math.pi * (g.Ri_if ** 2 - g.Ri_core ** 2) * tsum
                jun = rho * n * g.junta("disc") * (g.Ro - g.Ri_if) * tsum
                nt = rho * n * (lay.b_tope + 2) * sum((L_ or 0) * l["t"] for l, L_ in capas) if g.removable else 0.0
                causas += [f"agujero central mayor por el collar (R_i {fm(g.Ri_if, 1)} frente a {fm(g.Ri_core, 0)}): {fm(hole, 1)} kg", f"juntas de {fm(g.junta('disc'), 1)} mm entre {n} sectores: {fm(jun, 1)} kg"]
                if nt:
                    causas.append(f"muescas de los topes ({fm(lay.b_tope + 2, 0)} mm de ancho): {fm(nt, 1)} kg")
                tot = hole + jun + nt
                res = -r["dif"] - tot
                causas.append(("tapones de grafito, ranuras de engrase y agujeros avellanados / otros" if gr == "bz" else "ranuras de engrase y agujeros avellanados") + f": {fm(res, 1)} kg")
            else:
                strip = rho * g.n_seg * (lay.b_tope + g.junta("uhmw")) * (g.Ro - g.Ri_if) * g.I["tuh"]
                causas.append(f"franjas de las barras del rebaje y juntas entre sectores de UHMW: {fm(strip, 1)} kg; resto por el collar")
            t += "; ".join(causas) + "."
        elif gr == "wood":
            mm = {p.key: p for p in ctx.m.parts}
            t += f"anillo de contención de 10 mm que reemplaza madera, abertura Ø{fm(g.cb_D, 0)} frente a Ø{fm(g.hole_top, 0)} y {g.N_pin} bolsillos Ø{fm(g.washer_D + 4, 0)}×31 (el núcleo calcula el anulo completo)."
        else:
            t += "fórmula del núcleo frente a geometría (ver brechas)."
        L.append(t)
    if abs(ms["dif_pct"]) > 0.5:
        L.append(f"TOTAL comparable fuera de la tolerancia de {fm(ms['tol_pct'], 1)} %: {fm(ms['dif_pct'], 2)} %. Se debe a las piezas explicadas arriba (geometría real de sectores, juntas y collar que el núcleo no descuenta).")
    return L


# ----------------------------------------------------------------------------------------------
def escribir_bom(ctx, rep, out):
    rows = lista.bom_rows(ctx)
    ex = lista.extras(ctx)
    cols = ["Pos", "Código", "Descripción", "Cantidad", "Material / norma", "Masa unitaria (kg)", "Masa total (kg)", "Proceso", "Observación", "Código de catálogo"]
    with open(out / "TT300-C_despiece.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(cols)
        for r in rows:
            wr.writerow([r["pos"], r["code"], f"{r['nombre']}: {r['desc']}", r["qty"], r["material"], f"{r['unit']:.3f}", f"{r['total']:.2f}", r["proceso"], r["obs"], r["catalogo"]])
        for (d, q, e, c) in ex:
            wr.writerow(["—", "—", d, q, e, "", "", "", "No modelado", c])
        wr.writerow([])
        wr.writerow(["MASA TOTAL (kg)", "", "", "", "", "", f"{rep['masa_total_ensamble']:.1f}"])
        wr.writerow(["CENTRO DE GRAVEDAD x; y; z (mm)", "", "", "", "", "", "", "", f"{rep['cg'][0]:.1f}; {rep['cg'][1]:.1f}; {rep['cg'][2]:.1f}"])
        ms = rep["masas"]
        wr.writerow(["Comparable con el núcleo (kg)", f"3D {ms['total_3d']:.1f}", f"núcleo {ms['total_nucleo']:.1f}", f"dif {ms['dif']:.1f} kg", f"{ms['dif_pct']:+.2f} %", f"tolerancia {ms['tol_pct']} %"])
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Despiece"
        ws.append(cols)
        for r in rows:
            ws.append([r["pos"], r["code"], f"{r['nombre']}: {r['desc']}", r["qty"], r["material"], round(r["unit"], 3), round(r["total"], 2), r["proceso"], r["obs"], r["catalogo"]])
        for (d, q, e, c) in ex:
            ws.append(["—", "—", d, q, e, None, None, "", "No modelado", c])
        ws.append([])
        ws.append(["MASA TOTAL (kg)", None, None, None, None, None, round(rep["masa_total_ensamble"], 1)])
        ws.append(["CENTRO DE GRAVEDAD x; y; z (mm)", None, None, None, None, None, None, None, f"{rep['cg'][0]:.1f}; {rep['cg'][1]:.1f}; {rep['cg'][2]:.1f}"])
        for c in ws[1]:
            c.font = Font(bold=True)
        for col, w in zip("ABCDEFGHIJ", (6, 18, 70, 9, 40, 12, 12, 60, 50, 40)):
            ws.column_dimensions[col].width = w
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        w2 = wb.create_sheet("Masas")
        w2.append(["Grupo", "Masa 3D (kg)", "Núcleo (kg)", "Diferencia (kg)", "Diferencia (%)"])
        for r in ms["comp"]:
            w2.append([r["pieza"], round(r["modelo3d"], 2), round(r["nucleo"], 2), round(r["dif"], 2), round(r["dif_pct"], 2)])
        w2.append(["TOTAL comparable", round(ms["total_3d"], 2), round(ms["total_nucleo"], 2), round(ms["dif"], 2), round(ms["dif_pct"], 2)])
        w2.append(["Piezas fuera del núcleo", round(ms["masa_fuera"], 2)])
        w2.append(["MASA TOTAL del ensamble", round(rep["masa_total_ensamble"], 2)])
        w2.append(["CG x (mm)", round(rep["cg"][0], 1)]); w2.append(["CG y (mm)", round(rep["cg"][1], 1)]); w2.append(["CG z (mm)", round(rep["cg"][2], 1)])
        w3 = wb.create_sheet("Corte")
        w3.append(["Pos", "Pieza", "Forma", "Dimensión bruta (mm)", "Cant", "Material", "Observación"])
        for r in lista.cut_rows(ctx):
            w3.append(r)
        w4 = wb.create_sheet("Soldaduras")
        w4.append(["Id", "Juntas", "Tipo", "Tamaño", "Origen", "Proceso", "Calidad ISO 5817", "END", "WPS"])
        from hojas_base import soldaduras
        for w in soldaduras(ctx):
            w4.append([w["id"], w["juntas"], w["tipo"], w["tamano"], w["nota"], w["proc"], w["calidad"], w["end"], w["wps"]])
        w5 = wb.create_sheet("Supuestos y brechas")
        w5.append(["Id", "Tema", "Valor / descripción", "Motivo / decisión"])
        for x in ctx.sup:
            w5.append([x["id"], x["tema"], x["valor"], x["motivo"]])
        for x in ctx.gaps:
            w5.append([x["id"], x["tema"], x["desc"], x["decision"]])
        wb.save(out / "TT300-C_despiece.xlsx")
    except ImportError:
        _xlsx_minimo(out / "TT300-C_despiece.xlsx", cols, rows, rep)


def _xlsx_minimo(path, cols, rows, rep):
    """xlsx mínimo escrito a mano (si openpyxl no está instalado)."""
    import zipfile
    from xml.sax.saxutils import escape
    data = [cols] + [[r["pos"], r["code"], r["desc"], r["qty"], r["material"], round(r["unit"], 3), round(r["total"], 2), r["proceso"], r["obs"], r["catalogo"]] for r in rows]
    data.append(["MASA TOTAL (kg)", "", "", "", "", "", round(rep["masa_total_ensamble"], 1)])
    colname = lambda i: "ABCDEFGHIJ"[i]
    xml = ['<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for ri, row in enumerate(data, 1):
        xml.append(f'<row r="{ri}">')
        for ci, v in enumerate(row):
            ref = f"{colname(ci)}{ri}"
            if isinstance(v, (int, float)):
                xml.append(f'<c r="{ref}"><v>{v}</v></c>')
            else:
                xml.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(v))}</t></is></c>')
        xml.append("</row>")
    xml.append("</sheetData></worksheet>")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Despiece" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", "".join(xml))


# ----------------------------------------------------------------------------------------------
VERIF = {
    "GEN-001": ("Advertencia obligatoria, notas de viento y anclaje, presión máxima de trabajo, normas, procedimiento de limpieza y engrase.", "Decisiones del mandante; P.p_rated, p_relief, p_alarm; D['derivados'].tRev"),
    "GEN-002": ("Planta, corte A-A y datos técnicos coinciden con el núcleo (masa, WLL, presiones, altura total).", "D['derivados'] (masas, Fstall, q_max); verificación «Altura total sobre el piso»"),
    "GEN-003": ("Todas las posiciones del despiece tienen globo; el sentido de montaje de cada pieza es coherente.", "Despiece GEN-005; geometría del ensamble 3D"),
    "GEN-004": ("Secuencia constructible: topes antes del rectificado, mesa izada por medios del montajista, cilindros al final.", "Notas de la interfaz del núcleo (soldar topes antes del alivio); brecha de izaje de la mesa"),
    "GEN-005": ("Cantidades, materiales y masas; masa total y CG; diferencia con el núcleo dentro de la tolerancia o explicada.", "D['derivados'].masas; verificaciones de materiales"),
    "GEN-006": ("Dimensiones brutas con sobremetal razonable y cantidades iguales al despiece.", "Parámetros P (B, t_base, t_pr, d_pin, …)"),
    "GEN-007": ("Tipo, tamaño y END de cada soldadura; tamaños de P frente a los de las láminas; mínimos AWS donde P no fija.", "Verificaciones «Soldaduras» (w_web, w_br, w_bed_f, w_ear, w_tope, collar 10 mm)"),
    "GEN-008": ("Ajustes ISO 286, tolerancias, materiales con certificado, puntos de inspección y torques A DEFINIR.", "Registro de normas (docs/normas/registro.md); verificaciones de pasadores y uña"),
    "GEN-009": ("Supuestos de dibujo y brechas: el calculista debe aceptarlos o corregir el cálculo.", "Informe de brechas del paquete"),
    "BAS-001": ("Base soldada: B, t_base, marco, collar Ø D_boss × h_boss con agujero H7, bancadas, planitud 0,20, filetes.", "P.B, t_base, rim_*, h_boss, D_boss; verificaciones «Pivote» (collar) y «Base»"),
    "BAS-005": ("Ménsula: L_ch, saliente trasera, luz Win, altura H, orejas H9, filetes w_br.", "D['derivados'].bracket; verificaciones «Articulaciones»"),
    "IZA-001": ("Oreja: e, R, Ø agujero, altura del centro, filete w_ear, ubicación (±x_lug, ±(B/2 − c_lug)), plano radial.", "Verificaciones «Orejas de izaje» y «Base» (izaje)"),
    "ACC-001": ("Bancada: ancho, espesor, ranura T (cuello H8, cabeza), fondo, largo L_bed.", "D['derivados'].K (L_bed, Y_bed); P.w_slot, h_slot, w_tee, h_tee"),
    "ACC-002": ("Patín: L_s, w_s, lengüeta T, alojamiento de la uña, marco de boca e = t_fw.", "D['derivados'].K; verificaciones «Patín y guía»"),
    "ACC-003": ("Uña: largo, b, h, chaflán de retorno β, temple ≥ 55 HRC con profundidad del JSON.", "Verificaciones «Uña» (Hertz, profundidad de temple)"),
    "ACC-004": ("Pasadores de articulación f8, cilindro (Ø, carrera, presión de trabajo), circuito.", "P.D_bore, d_rod, stroke, p_rated; verificaciones «Articulaciones»"),
    "MES-001": ("Mesa: Ø, altura, almas, nervios, pasadores (PCD, paso), corte radial.", "P.D_top, h_disc, rings, N_rib, N_pin, R_pin; verificaciones «Mesa»"),
    "MES-002": ("Planchas y anillos: espesores t_top, t_bot, t_pr, agujero Ø200, rebaje Ø240, rebaje del collar, agujeros de pasadores.", "Verificaciones «Mesa (FEA)»; P.t_top, t_bot, t_pr"),
    "MES-003": ("Cubo con rebaje inferior Ø D_boss × h_boss; almas y nervios (largos de tramo).", "Verificación del collar «pared del rebaje ≥ 25 mm»; masas de almas y nervios"),
    "MES-004": ("Pasador Ø85 m6 × h_disc, franja templada, perno M20.", "Verificaciones «Pasadores de empuje»"),
    "PIV-001": ("Pivote, buje, tapas: asiento t_base + h_boss, buje desde t_base + h_boss + 2, ajustes p6/H7.", "Verificaciones «Pivote» (asiento, buje, flexión)"),
    "INT-001": ("Capas de la interfaz y alturas (Δ); topes, tornillos y ranuras según la alternativa; NO desmontable si fix_mode = 2.", "D['apoyo'].interfaz; D['interfazChecks']; verificaciones «Interfaz inox/bronce»"),
    "INT-002": ("Sectores: ángulo, juntas, muescas, tornillos, ranuras de engrase, rugosidad y planitud.", "P.n_sec, d_tor, h_gr, w_gr, n_gr_rad, n_gr_circ; verificaciones de sector y tornillo"),
    "INT-003": ("Topes (L_tope, b_tope, w_tope), tornillos ISO 10642, graseras, UHMW/bronce con tapones.", "interfazGeom.topes; verificaciones de tope y soldadura del tope (brecha B de altura)"),
    "MAD-001": ("Madera: espesor, abertura, bolsillos, anillo de acero PROVISORIO, f_apoyo.", "Verificaciones «Cubierta» (aplastamiento, espesor mínimo)"),
}


def lista_verificacion(ctx, hojas, out):
    lines = ["# Lista de verificación para el revisor · TT300-C", "",
             f"Fecha de emisión: {ctx.g.FECHA} · Interfaz: {ctx.g.interfaz_nombre}", "", f"**{ADVERTENCIA}**", "",
             "| N° | Plano | Título | Qué verificar | Contra qué cálculo |", "|---|---|---|---|---|"]
    rows = []
    for i, h in enumerate(hojas, 1):
        tag = h.tag
        q, c = VERIF.get(tag, ("Verificar contenido y cotas.", "Núcleo de cálculo"))
        lines.append(f"| {i} | {h.plano} | {h.titulo} | {q} | {c} |")
        rows.append((i, h.plano, h.titulo, q, c))
    lines += ["", "## Verificaciones transversales", "- Todas las láminas llevan la advertencia obligatoria, cajetín completo, estado «EMITIDO PARA REVISIÓN» y tabla de revisiones.",
              "- Cotas verificadas automáticamente contra el modelo 3D: ver `chequeo_cotas.csv` y el informe del paquete.",
              "- Masas 3D frente al núcleo, centro de gravedad e interferencias: ver `informe_paquete.md`.",
              "- Supuestos S## y brechas B-## de GEN-009: aceptar o corregir antes de aprobar."]
    (out / "lista_verificacion_revisor.md").write_text("\n".join(lines), encoding="utf-8")
    try:
        import pymupdf
        css = "body{font-family:sans-serif;color:#000;font-size:8pt} th,td{border:0.5pt solid #000;padding:2pt;vertical-align:top} table{border-collapse:collapse;width:100%} h1{font-size:13pt} h2{font-size:10pt}"
        html = f"<h1>Lista de verificación para el revisor · TT300-C</h1><p>Fecha de emisión: {ctx.g.FECHA} · Interfaz: {ctx.g.interfaz_nombre}</p><p><b>{ADVERTENCIA}</b></p><table><tr><th>N°</th><th>Plano</th><th>Título</th><th>Qué verificar</th><th>Contra qué cálculo</th></tr>"
        for r in rows:
            html += "<tr>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>"
        html += "</table><h2>Verificaciones transversales</h2><ul><li>Todas las láminas llevan advertencia, cajetín, estado y tabla de revisiones.</li><li>Cotas verificadas contra el modelo 3D (chequeo_cotas.csv).</li><li>Masas, CG e interferencias: informe_paquete.md.</li><li>Supuestos y brechas de GEN-009: aceptar o corregir.</li></ul>"
        story = pymupdf.Story(html=html, user_css=css)
        w = pymupdf.DocumentWriter(str(out / "lista_verificacion_revisor.pdf"))
        mediabox = pymupdf.paper_rect("a4-l")
        where = mediabox + (30, 30, -30, -30)
        more = 1
        while more:
            dev = w.begin_page(mediabox)
            more, _ = story.place(where)
            story.draw(dev)
            w.end_page()
        w.close()
    except Exception as ex:
        print("   (lista de verificación PDF no generada:", ex, ")")


def escribir_informe(ctx, rep, hojas, gaps, fuera, cr, out, dt):
    g = ctx.g
    ms = rep["masas"]
    L = [f"# Informe del paquete de planos TT300-C · Rev. {REV}", "", f"Generado el {g.FECHA} desde `TT300-C_design.json` (fuente única) en {dt:.0f} s.", f"Interfaz dibujada: **{g.interfaz_nombre}**" + ("" if g.removable or not g.opt else " (fijación pegada: NO desmontable)"),
         f"Cubierta de madera: {'sí' if g.wood else 'no'}. Collar del pivote: {'sí' if g.boss else 'no'}. Estado: EMITIDO PARA REVISIÓN.", "", f"**{ADVERTENCIA}**", "",
         f"## Láminas ({len(hojas)})", "", "| N° | Plano | Título | Escala |", "|---|---|---|---|"]
    for i, h in enumerate(hojas, 1):
        L.append(f"| {i} | {h.plano} | {h.titulo} | {h.escala} |")
    L += ["", f"## Ítems ({len(ctx.m.parts)})", "", "| Pos | Código | Ítem | Cant | Masa unit. kg | Masa total kg | En núcleo |", "|---|---|---|---|---|---|---|"]
    for p in ctx.m.parts:
        L.append(f"| {p.pos} | {p.code} | {p.name} | {p.qty} | {p.mass_unit:.2f} | {p.mass_total:.1f} | {'sí' if p.core else 'no'} |")
    L += ["", "## Masas: modelo 3D frente al núcleo", "", "| Grupo | 3D kg | Núcleo kg | Δ kg | Δ % |", "|---|---|---|---|---|"]
    for r in ms["comp"]:
        L.append(f"| {r['pieza']} | {r['modelo3d']:.1f} | {r['nucleo']:.1f} | {r['dif']:+.1f} | {r['dif_pct']:+.2f} |")
    ok = abs(ms["dif_pct"]) <= ms["tol_pct"]
    L += ["", f"**Total comparable:** 3D {ms['total_3d']:.1f} kg frente a {ms['total_nucleo']:.1f} kg del núcleo: Δ {ms['dif']:+.1f} kg ({ms['dif_pct']:+.2f} %), tolerancia ±{ms['tol_pct']} % → {'DENTRO' if ok else 'FUERA'}.",
          f"Piezas no incluidas en el núcleo (pernos, buje, tapas, topes, tornillos, graseras, anillo, pasadores de articulación): {ms['masa_fuera']:.1f} kg. **Masa total del ensamble: {rep['masa_total_ensamble']:.1f} kg.**",
          f"**Centro de gravedad (x, y, z):** ({rep['cg'][0]:.1f}; {rep['cg'][1]:.1f}; {rep['cg'][2]:.1f}) mm (origen en el eje de la mesa y la cara inferior de la base).", ""]
    ex = explicar_masas(ctx, rep)
    if ex:
        L += ["### Diferencias explicadas por pieza"] + [f"- {x}" for x in ex] + [""]
    L += ["## Interferencias", "", f"{sum(1 for r in rep['interferencias'] if not r['ok'])} pares con volumen común > 1 mm³ de {rep['pares_evaluados']} pares evaluados con cajas envolventes solapadas (total de pares {rep['pares_totales']}).", ""]
    for r in rep["interferencias"]:
        if not r["ok"]:
            L.append(f"- XX {r['a']} × {r['b']}: {r['vol_mm3']} mm³")
    nf = sum(1 for r in cr if not r["ok"])
    L += ["", "## Chequeo automático de cotas (dibujo frente a modelo 3D)", "",
          f"{len(cr)} cotas registradas; {len(cr) - nf} verificadas (extremos sobre la superficie del sólido o ejes de superficies cilíndricas reales, tolerancia 0,05 mm); **{nf} fallas**. Detalle en `chequeo_cotas.csv`."]
    for r in cr:
        if not r["ok"]:
            L.append(f"- FALLA [{r['sheet']}] {r['texto']} ({r['extremo_a']} / {r['extremo_b']})")
    L += ["", "## Control de marco", "", ("Todas las láminas dentro del formato A1." if not fuera else "Láminas con entidades fuera del formato: " + "; ".join(f"{a} {b}" for a, b in fuera))]
    L += ["", "## Supuestos del dibujante (rotulados PROVISORIO)", "", "| Id | Tema | Valor | Motivo |", "|---|---|---|---|"]
    for x in ctx.sup:
        L.append(f"| {x['id']} | {x['tema']} | {x['valor']} | {x['motivo']} |")
    L += ["", "## Brechas con el cálculo y decisiones requeridas", "", "| Id | Tema | Descripción | Decisión requerida |", "|---|---|---|---|"]
    for x in gaps:
        L.append(f"| {x['id']} | {x['tema']} | {x['desc']} | {x['decision']} |")
    L += ["", "## Reproducción", "", "```", "python3 cad/generar_paquete.py [design.json] [--out DIR] [--entrega DIR]", "```",
          "Dependencias: cadquery, ezdxf, pymupdf, shapely, openpyxl (opcional; sin él se escribe un .xlsx mínimo), Node.js para `tools/export_design.js`."]
    (out / "informe_paquete.md").write_text("\n".join(L), encoding="utf-8")


def copiar_entrega(out, dest, pdfs):
    dest.mkdir(parents=True, exist_ok=True)
    for nm in (f"TT300-C_Planos_Rev{REV}.pdf", f"TT300-C_DXF_Rev{REV}.zip", "TT300-C.step", "TT300-C.glb", "TT300-C_despiece.csv", "TT300-C_despiece.xlsx", "lista_verificacion_revisor.md",
               "lista_verificacion_revisor.pdf", "informe_paquete.md", "chequeo_cotas.csv", "TT300-C_masas3d.json", "TT300-C_design.json"):
        if (out / nm).exists():
            shutil.copy(out / nm, dest / nm)
    pd = dest / "planos"
    pd.mkdir(exist_ok=True)
    for p in pdfs:
        shutil.copy(p, pd / pathlib.Path(p).name)
        shutil.copy(str(p).replace(".pdf", ".dxf"), pd / pathlib.Path(p).name.replace(".pdf", ".dxf"))
