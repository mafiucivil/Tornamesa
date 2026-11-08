"""Brechas con el cálculo, despiece CSV/XLSX, lista de verificación del revisor e informe del paquete."""
import csv, math, sys, pathlib, shutil
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import *
import lista


def vol_hub(g):
    """Longitud de arranque del buje guiado en el cubo: el buje parte en z_bush0; el cubo tiene su alesaje desde el techo del rebaje (núcleo: hPl + hHub)."""
    z_bore = g.z_techo if g.rebaje else g.z0 + g.tbo
    return max(0.0, min(g.P["L_bush"], g.z_bush0 + g.P["L_bush"] - max(z_bore, g.z_bush0)))


def brechas(ctx, rep):
    """Brechas que SIGUEN abiertas con el núcleo actual. Lo que el núcleo ya resuelve (R_i, rebaje con holguras, geometría de topes, tiempo por vuelta) no es brecha."""
    g, P, DV, D = ctx.g, ctx.P, ctx.DV, ctx.D
    G_ = []

    def add(tema, desc, decision):
        G_.append(dict(id=f"B-{len(G_) + 1:02d}", tema=tema, desc=desc, decision=decision))
    tr = DV["tRev"]
    if tr > P["t_vuelta_obj"] + 1e-9:
        add("Tiempo por vuelta", f"D['derivados'].tRev = {fm(tr, 1)} min supera el objetivo de {fm(P['t_vuelta_obj'], 0)} min (Q_pump = {fm(P['Q_pump'], 1)} L/min, Q_ret = {fm(P['Q_ret'], 0)}).", "Aumentar el caudal de bomba o revisar el objetivo.")
    if g.opt and g.removable:
        add("Posición, torque y largo de tornillos de posición", f"Adoptado por el mandante: 2 por sector. El núcleo fija solo d_tor = M{fm(P['d_tor'], 0)} y verifica la cabeza; la posición radial (S01), el largo (S11) y el torque no están definidos.", "Confirmar posición y largo; definir torque (ISO 898-1 / VDI 2230).")
    if g.opt == 2:
        add("Opción B sin engrase", "El núcleo no define ranuras ni graseras para la opción B (UHMW sobre inox «con grasa limpia»); no se dibujan.", "Definir si B lleva engrase y su geometría.")
    if g.wood:
        ab, bol = wood_residual(ctx)
        add("Cubierta de madera: residual de masa fuera del núcleo", f"El anillo de acero (pletina {fm(P['t_ring'], 0)}×{fm(P['t_wood'], 0)}, {fm(ctx.M['ring'], 1)} kg) ya está en el núcleo y en m.total (madera {fm(ctx.M['wood'], 1)} kg dentro del anillo). El modelo 3D descuenta además la abertura central Ø{fm(g.cb_D, 0)} de la tapa de inspección ({fm(ab, 1)} kg) y {g.N_pin} bolsillos de perno/arandela ({fm(bol, 1)} kg) que el núcleo no resta: residual {fm(ab + bol, 1)} kg, conservador en el núcleo.",
            "Informativo: aceptar la diferencia o descontarla en el núcleo. Disposición de tablones (ancho 200 mm) en MAD-001; fijación PROPUESTA (confirmar).")
    ev = vol_hub(g)
    if g.boss and ev < P["L_bush"] - 1e-6:
        add("Buje parcialmente sin guía en el cubo", f"El buje arranca en z = {fm(g.z_bush0, 0)} y el alesaje del cubo (Ø{fm(g.d_bush, 0)} H7) empieza en z = {fm(g.z_techo if g.rebaje else g.z0 + g.tbo, 0)}: engrane {fm(ev, 0)} de {fm(P['L_bush'], 0)} mm (con rebaje de {fm(g.h_rebaje, 0)} < t_bot, el agujero de la plancha inferior es pasante).", "Verificar la presión del buje con el engrane real o subir el buje.")
    add("Izaje de la mesa", "El cálculo solo define las 4 orejas de la base; no hay puntos de izaje de la mesa (los cáncamos M30 de la Rev. B anterior sobre plancha de 20 mm no engranan la profundidad exigible).", "A DEFINIR: orejas o cáncamos verificados para la mesa.")
    add("Retención axial del pivote", "El núcleo verifica asiento y flexión, no la extracción axial del pivote (zona p6 calada H7/p6, sin soldadura).", "A DEFINIR: tope inferior, anillo o interferencia verificada.")
    add("Torque de pernos y tornillos", "El núcleo no entrega torques (pernos M20×45 de pasadores, M10 de tapas, tornillos de posición).", "Torques PROPUESTOS en GEN-008 (ISO 898-1, VDI 2230 simplificado): A CONFIRMAR POR EL CALCULISTA.")
    add("Tamaño de soldaduras sin parámetro", "Marco, esquinas y orejas de ménsula no tienen tamaño en P; se adopta el mínimo AWS D1.1 T5.8 por la parte más gruesa. Sí son parámetro (y el núcleo verifica mínimo y máximo): w_collar, w_ear, w_tope, w_br, w_web, w_bed_f.", "CONFIRMAR o parametrizar tamaños y END de las soldaduras sin parámetro.")
    add("Filetes máximos AISC J2.2b de almas y nervios", f"Almas y nervios de la mesa: w_web = {fm(P['w_web'], 0)} sobre t = {fm(P['t_web'], 0)} superan el máximo de borde t − 2 = {fm(P['t_web'] - 2, 0)} mm que aplica el núcleo (AISC J2.2b) salvo que el cateto se justifique como built-up (el cordón no queda en el borde del alma). Nota para el calculista: la cláusula J2.2b literal permite w = t para bordes de t < 6,35 mm (aquí 6 mm); el criterio t − 2 es el conservador del núcleo. El núcleo exige el mínimo (fila «Filete mínimo almas/nervios–planchas», 6 mm) pero no tiene fila de máximo para esta unión.",
        "PENDIENTE DEL CALCULISTA: concluir si el cateto z6 se acepta como built-up o se reduce a z4 (con verificación de la soldadura alma/nervio–plancha del núcleo) / se espesa el alma.")
    for v in D["verificaciones"]:
        if v["estado"] == "warn":
            if v["nombre"].startswith("Soldadura mejillas–base"):
                add("Advertencia del núcleo aceptada: soldadura mejillas–base", f"«{v['nombre']}»: FU {fm(v['fu'], 3)} (demanda {fm(v['dem'], 1)} / capacidad {fm(v['cap'], 1)} MPa) en banda «warn» con w_br = {fm(P['w_br'], 0)} (mínimo AWS D1.1 T5.8 = {fm(g.fila('Filete mínimo mejillas–base')['dem'], 0) if g.fila('Filete mínimo mejillas–base') else '—'} mm; máximo AISC J2.2b = t_ch − 2 = {fm(P['t_ch'] - 2, 0)} mm, ya en el tope).",
                    "ACEPTADA POR EL MANDANTE como advertencia (no se aumenta el filete: w_br ya está cerca del máximo AISC J2.2b). Dejar registro en la aprobación.")
            elif v["nombre"].startswith("Flexión en la boca del patín"):
                add("Advertencia del núcleo aceptada: flexión de la uña en la boca del patín", f"«{v['nombre']}»: FU {fm(v['fu'], 3)} (demanda {fm(v['dem'], 1)} / capacidad {fm(v['cap'], 1)} {v['unidad']}) con Fy_dog = {fm(P['Fy_dog'], 0)} MPa (34CrNiMo6+QT, EN 10083-3, 40 < t ≤ 100 mm) y Nd = 3,0 (ASME BTH-1 §3-2.3).",
                    "ACEPTADA POR EL MANDANTE el 07-11-2026 como advertencia (FU ≤ 1,0; se relaja solo para esta fila el criterio interno FU ≤ 0,90). Dejar registro en la aprobación.")
            else:
                add("Advertencia del núcleo (banda «warn»)", f"«{v['nombre']}»: FU {fm(v['fu'], 3)} (demanda {fm(v['dem'], 1)} / capacidad {fm(v['cap'], 1)} {v['unidad']}).", "A DECIDIR POR EL MANDANTE: aceptar la advertencia o reforzar la pieza.")
    for v in D["verificaciones"]:
        if v["estado"] == "pend":
            add("Pendiente declarado por el núcleo", v["nombre"], "Atender en fabricación/aprobación según el texto del núcleo.")
    if g.opt == 3 and ctx.m.info.get("n_plugs"):
        add("Tapones de grafito: patrón realizable frente a f_g del núcleo", plug_txt(ctx),
            "A DECIDIR POR EL MANDANTE: densificar el patrón (paso o zonas de exclusión) o que el núcleo use la cantidad real de tapones; el efecto sobre la presión del bronce es conservador, sobre la lubricación no.")
    add("Diferencias de fórmula del patín", "La masa del patín del núcleo difiere del modelo (alojamiento abierto por la cara superior y cuello de la lengüeta): −0,3 % en la pieza.", "Informativo (dentro de tolerancia).")
    cam = float(ctx.M.get("cam") or 0.0)
    if cam > 0.05:
        add("Masa del accionamiento sin dibujar (leva de reenganche)", f"El núcleo suma {fm(cam, 1)} kg de la leva de reenganche (masa «cam» del cálculo) que este juego todavía no dibuja: la masa de las láminas (modelo 3D) es menor que la del cálculo en esa cantidad más el residual de fórmulas.",
            "PENDIENTE ACCIONAMIENTO: se dibuja con el rediseño de la leva de reenganche y del modo pivotado.")
    add("Cilindro comercial", f"Largo ojal–ojal L0 = {fm(P['L0'], 0)} mm y masa {fm(P['m_cyl'], 0)} kg son supuestos del núcleo; el modelo 3D usa la geometría de extremos del núcleo.", "Confirmar con el proveedor del cilindro.")
    return G_


def cortes_control(ctx):
    """Control de masa de las piezas de la interfaz, por pieza, con los cortes que entrega el núcleo (interfazGeom.cortes: junta, muesca, chaflán, masa bruta,
    descontada y neta). La masa neta es la que el núcleo suma a m.total; aquí se compara con la masa de las piezas del modelo 3D. Sin fórmulas propias."""
    g, m = ctx.g, ctx.m
    rows = []
    for c in g.IG.get("cortes", []):
        k = c["n"] * c["capas"]
        kgv = lambda V: c["rho"] * V * k
        ids = {"disc0": ["int_disco_base"] + (["int_disco_mesa"] if c["capas"] == 2 else []), "disc1": ["int_disco_mesa"], "uhmw": ["int_uhmw"], "bz0": ["int_bronce", "int_tapones"], "bz1": ["int_cara"]}.get(c["id"], [])
        m3 = sum(m.get(x).mass_total for x in ids if m.get(x))
        rows.append(dict(id=c["id"], pieza=c["pieza"], k=k, t=c["t"], j=c["j"], strip=c["strip"], jun=kgv(c["V_junta"]), mue=kgv(c["V_muesca"]), cha=kgv(c["V_chaflan"]),
                         bruta=c["m_bruta"], desc=c["m_desc"], neta=c["m_neta"], m3d=m3, res=m3 - c["m_neta"], res_pct=(m3 - c["m_neta"]) / c["m_neta"] * 100 if c["m_neta"] else 0.0))
    return rows


def residual_txt(ctx, grupo):
    """Qué no descuenta el núcleo en cada grupo (explica el residual 3D − núcleo; no se compensa con fórmulas)."""
    g, P = ctx.g, ctx.P
    if grupo == "ss" and g.opt and not g.removable:
        jk = g.n_sec * g.junta("disc") * (g.Ro - g.Ri) * (g.I["tss"] + g.I["tss2"]) * RHO_SS
        return (f"fijación pegada: el núcleo calcula discos completos (sin juntas ni muescas), el modelo 3D conserva {g.n_sec} sectores con junta de {fm(g.junta('disc'), 1)} mm ({fm(jk, 1)} kg) "
                "y además las ranuras de engrase y los taladros de las graseras (el resto del residual)")
    if grupo == "ss":
        return "ranuras de engrase, agujeros avellanados de los tornillos de posición y taladros de las graseras (el núcleo solo descuenta juntas, muescas y chaflanes)"
    if grupo == "bz":
        return "tapones de grafito, ranuras de engrase, tornillos de posición y taladros de las graseras. " + plug_txt(ctx)
    if grupo == "uhmw":
        return "redondeos y tolerancias de corte de los sectores de lámina"
    if grupo == "wood":
        return "abertura central Ø%s de la tapa de inspección (el núcleo usa Ø%s) y %d bolsillos de perno y arandela Ø%s×31 (el núcleo calcula el anulo completo)" % (fm(g.cb_D, 0), fm(g.hole_top, 0), g.N_pin, fm(g.washer_D + 4, 0))
    if grupo == "shoes":
        return "alojamiento abierto por la cara superior y cuello de la lengüeta del patín (fórmula del núcleo frente a la geometría)"
    if grupo == "mesa":
        return "rebaje del cubo, agujeros de pasadores y empalmes (fórmula del núcleo)"
    if grupo == "base":
        return "agujero del pivote, redondeos y chaflanes de las orejas (fórmula del núcleo)"
    return "fórmula del núcleo frente a geometría"


def plug_txt(ctx):
    """Tapones de grafito: el núcleo trata la placa como mezcla homogénea con f_g sobre toda el área; el 3D coloca el patrón S09 (menos tapones)."""
    g, P, m = ctx.g, ctx.P, ctx.m
    n3 = m.info.get("n_plugs")
    T = g.IG.get("tapones")
    if n3 and T:
        return (f"Núcleo v1.2 (interfazGeom.tapones): N_real = {f(T['N_real'])} tapones (malla {f(T['N_malla'])}, N_ideal {f(T['N_ideal'])}), f_g real = {fm(T['fg_real'], 3)} (ideal {fm(T['fg_ideal'], 3)}, usado {fm(T['fg_usado'], 3)}); "
                f"el 3D coloca {f(n3)} ({n3 - T['N_real']:+d} respecto del núcleo). Cumple lubricación (f_g ≥ {fm(T['fg_min'], 2)}): {'sí' if T['cumple_lubricacion'] else 'NO (decisión del calculista)'}.")
    fgv = g.fila("Tapones de grafito: fracción de área")
    if not n3 or not fgv:
        return ""
    cov = P["bz_cover"] if g.conf == 3 else 1.0
    A = math.pi * (g.Ro ** 2 - g.Ri ** 2) * cov
    ap = math.pi / 4 * P["bz_plug_d"] ** 2
    neq = fgv["dem"] * A / ap
    prof = m.info.get("plug_prof", 0.0)
    dm = (neq - n3) * ap * prof * (P["rho_bz"] - RHO_GR * 1e6) * 1e-6
    return (f"El núcleo toma f_g = {fm(fgv['dem'], 3)} sobre toda el área (equivale a ≈ {f(neq)} tapones Ø{fm(P['bz_plug_d'], 0)}×{fm(prof, 1)}); el 3D coloca {f(n3)} (patrón S09: se omiten los tapones a menos de 4 mm de bordes, muescas, tornillos y ranuras). "
            f"Con {f(neq - n3)} tapones menos hay más bronce y menos grafito: ≈ {fm(dm, 1)} kg de más en el 3D (la placa real queda con f_g ≈ {fm(fgv['dem'] * n3 / neq, 3)}: menos grafito lubricante que el supuesto del núcleo).")


def wood_residual(ctx):
    """Residual de la madera por geometría (kg): abertura Ø cb_D frente a Ø hole_top y bolsillos. Solo informativo (explica el residual del 3D)."""
    g, P = ctx.g, ctx.P
    rho = P["rho_wood"] * 1e-9
    ab = math.pi / 4 * (g.cb_D ** 2 - g.hole_top ** 2) * P["t_wood"] * rho if g.cb_D > g.hole_top else 0.0
    bol = g.N_pin * math.pi / 4 * (g.washer_D + 4) ** 2 * 31 * rho
    return ab, bol


def explicar_masas(ctx, rep):
    g, P = ctx.g, ctx.P
    L = []
    ms = rep["masas"]
    for r in ms["comp"]:
        gr = r["grupo"]
        if abs(r["dif_pct"]) < 0.05 and abs(r["dif"]) < 0.5:
            continue
        t = f"{r['pieza']}: 3D {fm(r['modelo3d'], 1)} kg frente a {fm(r['nucleo'], 1)} kg del núcleo ({fm(r['dif_pct'], 2)} %; residual {fm(r['dif'], 2)} kg). Residual no descontado en el núcleo: {residual_txt(ctx, gr)}."
        if gr == "wood":
            ab, bol = wood_residual(ctx)
            t += f" Por geometría: abertura {fm(ab, 1)} kg + bolsillos {fm(bol, 1)} kg = {fm(ab + bol, 1)} kg."
        L.append(t)
    if abs(ms["dif_pct"]) > ms["tol_pct"]:
        L.append(f"TOTAL comparable {fm(ms['dif_pct'], 2)} %: FUERA de ±{fm(ms['tol_pct'], 1)} %. Revisar por pieza (tabla de control de la interfaz) y corregir el modelo 3D o el núcleo.")
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
        for w in ctx.welds:
            w4.append([w["id"], w["desc"], w["tipo"] + ("" if w["prep"] == "Sin preparación" else ". " + w["prep"]), w["size_txt"] + (f" (a = {w['a']})" if w["a"] else ""), w["origen"], w["proceso"], w["nivel"], w["end"], w["wps"]])
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
    "GEN-007": ("Tipo, tamaño y END de cada soldadura; tamaños de P frente a los de las láminas; mínimos AWS donde P no fija.", "Verificaciones «Soldaduras» y filetes de collar, orejas y topes (w_web, w_br, w_bed_f, w_collar, w_ear, w_tope)"),
    "GEN-008": ("Ajustes ISO 286, tolerancias, materiales con certificado, puntos de inspección y torques PROPUESTOS.", "Registro de normas (docs/normas/registro.md); verificaciones de pasadores y uña"),
    "GEN-009": ("Supuestos de dibujo y decisiones adoptadas por el mandante; brechas abiertas (decisiones pendientes): el calculista debe aceptarlas o corregir el cálculo.", "Informe de brechas del paquete"),
    "BAS-001": ("Base soldada: B, t_base, marco, collar Ø D_boss × h_boss con agujero H7, bancadas, planitud 0,20, filetes.", "P.B, t_base, rim_*, h_boss, D_boss; verificaciones «Pivote» (collar) y «Base»"),
    "BAS-005": ("Ménsula: L_ch, saliente trasera, luz Win, altura H, orejas H9, filetes w_br.", "D['derivados'].bracket; verificaciones «Articulaciones»"),
    "IZA-001": ("Oreja R92: e, 2R × h + semicírculo, Ø agujero, altura del centro, filete w_ear, ubicación, plano radial; nota de ramales (L ≥ d/cos 60°).", "Verificaciones «Orejas de izaje» (AISC D5.2, filetes mínimo y máximo, ramales) y «Base» (izaje)"),
    "ACC-001": ("Bancada: ancho, espesor, ranura T (cuello H8, cabeza), fondo, largo L_bed.", "D['derivados'].K (L_bed, Y_bed); P.w_slot, h_slot, w_tee, h_tee"),
    "ACC-002": ("Patín: L_s, w_s, lengüeta T, alojamiento de la uña, marco de boca e = t_fw.", "D['derivados'].K; verificaciones «Patín y guía»"),
    "ACC-003": ("Uña: largo, b, h, chaflán de retorno β, temple por inducción ≥ 55 HRC (Fy_sup), alivio de borde 10 mm con cota (k_edge).", "Verificaciones «Uña» (Hertz con k_borde, profundidad de temple); P.Fy_surf, P.k_edge"),
    "ACC-004": ("Pasadores de articulación f8, cilindro (Ø, carrera, presión de trabajo), circuito.", "P.D_bore, d_rod, stroke, p_rated; verificaciones «Articulaciones»"),
    "MES-001": ("Mesa: Ø, altura, almas, nervios, pasadores (PCD, paso), corte radial.", "P.D_top, h_disc, rings, N_rib, N_pin, R_pin; verificaciones «Mesa»"),
    "MES-002": ("Planchas y anillos: espesores t_top, t_bot, t_pr, agujero Ø200, rebaje Ø240, agujero pasante Ø D_rebaje_bot (collar + 2 c_boss_r), agujeros de pasadores.", "Verificaciones «Mesa (FEA)»; P.t_top, t_bot, t_pr"),
    "MES-003": ("Cubo con rebaje inferior Ø D_rebaje × h_rebaje_cubo (holguras c_boss_r, c_boss_a); almas y nervios (largos de tramo; anillos del JSON).", "interfazGeom (D_rebaje_bot, h_rebaje_cubo); verificación del collar «pared del rebaje ≥ 25 mm»; masas de almas y nervios"),
    "MES-004": ("Pasador Ø85 m6 × h_disc, temple por inducción ≥ 55 HRC (Fy_sup), alivio de borde, perno M20.", "Verificaciones «Pasadores de empuje»; P.Fy_surf, P.k_edge"),
    "PIV-001": ("Pivote, buje, tapas: asiento t_base + h_boss, buje desde t_base + h_boss + g_buje, holguras reales del collar (radial c_boss_r, axial al techo), brazo e = 42, ajustes H7/p6 (zona de calado) y F7/f7 (zona del buje).", "Verificaciones «Pivote» (asiento, brazo efectivo, buje, flexión, rebaje del collar)"),
    "INT-001": ("Capas de la interfaz y alturas (Δ); topes, tornillos y ranuras según la alternativa; NO desmontable si fix_mode = 2.", "D['apoyo'].interfaz; D['interfazChecks']; verificaciones «Interfaz inox/bronce»"),
    "INT-002": ("Sectores: ángulo, juntas, muescas, tornillos, ranuras de engrase, rugosidad y planitud.", "P.n_sec, d_tor, h_gr, w_gr, n_gr_rad, n_gr_circ; verificaciones de sector y tornillo"),
    "INT-003": ("Barras de tope: L, b_tope, h = t − a_sup, a_inf, h_c, w_tope ≥ w_mín; secciones A-A/B-B(/C-C en B); tornillos ISO 10642, graseras, UHMW/bronce con tapones.", "interfazGeom.topes (geometría resuelta) y verificaciones de tope «alivio inferior», «filete dentro de la altura de barra», «filete mínimo»"),
    "MAD-001": ("Madera: espesor, abertura, bolsillos, anillo de acero (pletina t_ring×t_wood, en el núcleo), tablones de 200, f_apoyo.", "Verificaciones «Cubierta» (aplastamiento, espesor mínimo)"),
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
          f"Piezas no incluidas en el núcleo (pernos, buje, tapas, tornillos, graseras, pasadores de articulación; las barras de los topes SÍ están en m.total/m.stopBars): {ms['masa_fuera']:.1f} kg. **Masa total del ensamble: {rep['masa_total_ensamble']:.1f} kg.**",
          f"**Centro de gravedad (x, y, z):** ({rep['cg'][0]:.1f}; {rep['cg'][1]:.1f}; {rep['cg'][2]:.1f}) mm (origen en el eje de la mesa y la cara inferior de la base).", ""]
    cc = cortes_control(ctx)
    if cc:
        L += ["### Control de masa de la interfaz por pieza (cortes del núcleo, `interfazGeom.cortes`)", "",
              "| Pieza | Piezas (n × capas) | t mm | Junta mm | Juntas kg | Muescas kg | Chaflanes kg | Bruta kg | Neta del núcleo kg | 3D kg | Residual kg | Residual % |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in cc:
            L.append(f"| {r['pieza']} | {r['k']} | {fm(r['t'], 0)} | {fm(r['j'], 1)}{' (franja libre)' if r['strip'] else ''} | {r['jun']:.1f} | {r['mue']:.1f} | {r['cha']:.1f} | {r['bruta']:.1f} | {r['neta']:.1f} | {r['m3d']:.1f} | {r['res']:+.2f} | {r['res_pct']:+.2f} |")
        L += ["", "La masa neta es la del núcleo (m_neta = bruta − juntas − muescas − chaflanes). No hay conciliación manual: el 3D se compara directamente con ella. El residual corresponde a lo que el núcleo no descuenta "
              "(ranuras de engrase, agujeros avellanados de tornillos, taladros de graseras; tapones de grafito en la opción C).", ""]
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
    L += ["", "## Control de marco", "", (("Todas las láminas dentro de su formato (" + ", ".join(f"{k}: {v}" for k, v in sorted({fm_: sum(1 for h in hojas if h.fmt == fm_) for fm_ in {h.fmt for h in hojas}}.items())) + ").") if not fuera else "Láminas con entidades fuera del formato: " + "; ".join(f"{a} {b}" for a, b in fuera))]
    L += ["", "## Supuestos del dibujante (PROVISORIO) y decisiones adoptadas por el mandante (ADOPTADO)", "", "| Id | Tema | Valor | Motivo |", "|---|---|---|---|"]
    for x in ctx.sup:
        L.append(f"| {x['id']} | {x['tema']} | {x['valor']} | {x['motivo']} |")
    L += ["", "## Brechas con el cálculo y decisiones requeridas", "", "| Id | Tema | Descripción | Decisión requerida |", "|---|---|---|---|"]
    for x in gaps:
        L.append(f"| {x['id']} | {x['tema']} | {x['desc']} | {x['decision']} |")
    L += ["", "## Reproducción", "", "```", "python3 cad/generar_paquete.py [design.json] [--out DIR] [--entrega DIR]", "```",
          "Dependencias: cadquery, ezdxf, pymupdf, shapely, openpyxl (opcional; sin él se escribe un .xlsx mínimo), Node.js para `tools/export_design.js`."]
    (out / "informe_paquete.md").write_text("\n".join(L), encoding="utf-8")


def copiar_entrega(out, dest, pdfs, con_dxf=True, extra=()):
    dest.mkdir(parents=True, exist_ok=True)
    if (dest / "planos").exists():
        shutil.rmtree(dest / "planos")                     # elimina láminas obsoletas
    for old in list(dest.glob("TT300-C_Planos_Rev*.pdf")) + list(dest.glob("TT300-C_DXF_Rev*.zip")):
        old.unlink()
    for nm in (f"TT300-C_Planos_Rev{REV}.pdf", f"TT300-C_DXF_Rev{REV}.zip", "TT300-C.step", "TT300-C.glb", "TT300-C_despiece.csv", "TT300-C_despiece.xlsx", "lista_verificacion_revisor.md",
               "lista_verificacion_revisor.pdf", "informe_paquete.md", "chequeo_cotas.csv", "TT300-C_masas3d.json", "TT300-C_design.json", "metricas_laminas.csv", "soldaduras.csv", "lista_de_cortes.csv", "checklist_piezas.csv", "control_cadenas.csv", "completitud_piezas.csv", *extra):
        if (out / nm).exists():
            shutil.copy(out / nm, dest / nm)
    pd = dest / "planos"
    pd.mkdir(exist_ok=True)
    for p in pdfs:
        shutil.copy(p, pd / pathlib.Path(p).name)
        if con_dxf:
            shutil.copy(str(p).replace(".pdf", ".dxf"), pd / pathlib.Path(p).name.replace(".pdf", ".dxf"))
    if not con_dxf and (dest / f"TT300-C_DXF_Rev{REV}.zip").exists():
        (dest / f"TT300-C_DXF_Rev{REV}.zip").unlink()
