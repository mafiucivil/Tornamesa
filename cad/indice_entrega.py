"""Índice general de una entrega de juegos de planos TT300-C (varios casos), con el estado de cada lámina.

Uso: python3 cad/indice_entrega.py <dir_entrega> [--casos base,A,...] [--logs <dir con <caso>/log.txt>] [--nota-standby "texto"]

Lee de cada <dir_entrega>/<caso>/ lo que escribió generar_paquete.py (nada a mano):
  estado_laminas.csv (lámina, título, EMITIDA PARA REVISIÓN / RETENIDA y motivo), TT300-C_masas3d.json (conflictos del núcleo e interferencias),
  TT300-C_despiece.csv (ítems), chequeo_cotas.csv (cotas), control_cadenas_cerradas.csv (fallas de los controles), informe_paquete.md (interfaz dibujada),
  TT300-C_design.json (fecha y parámetros del caso) y, si se da --logs, el código de salida del generador.
Escribe <dir_entrega>/INDICE.md e INDICE.pdf (A3 apaisado)."""
import csv
import json
import pathlib
import re
import sys

ADVERTENCIA = "ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO."
CASOS = ["base", "A", "AF2", "B", "C1", "C2", "C3", "base_G", "A_G"]
NOTA_W = ("Cubierta de madera W: EN STAND BY por decisión del mandante. No forma parte de esta entrega; su trabajo de planos está respaldado en "
          "docs/standby/madera_W/ y se retomará cuando el mandante lo indique.")
NOTA_E = ("Soporte del ojal E (modo pivotado): la flexión local de la plancha base bajo el soporte E está EN VERIFICACIÓN por el núcleo de cálculo; "
          "podría agregar cartelas o un refuerzo local. Las láminas de la base y del soporte del ojal E se emiten para revisión con esa salvedad.")


def nota_plancha(C):
    """Nota de la plancha base bajo el soporte E (casos del modo pivotado): con la verificación del núcleo en el JSON (pivotado.fabricacion.soporte_E.plancha_base)
    se informa su resultado por caso; sin ella, la verificación figura como en curso (NOTA_E)."""
    piv = [c for c in C if c.get("soporte_E") is not None]
    if not piv:
        return None
    res = []
    for c in piv:
        pb = c["soporte_E"].get("plancha_base")
        if not pb:
            return NOTA_E
        fu = max((k.get("fu") or 0) for k in pb.get("casos") or [{}])
        res.append(f"{c['caso']} FU {fu:.2f}".replace(".", ","))
    pb = piv[0]["soporte_E"]["plancha_base"]
    rb = pb.get("revision_base_completa") or {}
    ops = "; ".join(f"{o['id']}: {o['nombre']}" for o in rb.get("opciones", [])) or "marco perimetral tipo KIET, nervios radiales o base rígida"
    tor = f" Con la base completa (dos soportes) gobierna la torsión de la plancha (FU ≥ {rb['fu_torsion_cota_inferior']:.2f}, cota inferior).".replace(".", ",", 1) if rb.get("fu_torsion_cota_inferior") else ""
    return (f"Plancha base de {pb.get('t', '—')} mm bajo el soporte del ojal E (modo pivotado): según el núcleo NO cumple en flexión sin anclaje a la losa "
            f"(peor caso por juego: {'; '.join(res)}); estado: {pb.get('estado', '—')}." + tor + f" Solución en estudio ({ops}). "
            "En los juegos del modo pivotado BAS-001, BAS-012 y CON-007 quedan RETENIDAS con ese motivo; los juegos del modo guiado no se afectan.")


def _csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig") as fh:
        return list(csv.reader(fh, delimiter=";"))[1:]


def leer_caso(d, logs=None, caso=None):
    est = [dict(n=int(r[0]), lamina=r[1], titulo=r[2], estado=r[3], motivo=r[4]) for r in _csv(d / "estado_laminas.csv")]
    rep = json.loads((d / "TT300-C_masas3d.json").read_text(encoding="utf-8")) if (d / "TT300-C_masas3d.json").exists() else {}
    D = json.loads((d / "TT300-C_design.json").read_text(encoding="utf-8")) if (d / "TT300-C_design.json").exists() else {}
    inf = (d / "informe_paquete.md").read_text(encoding="utf-8") if (d / "informe_paquete.md").exists() else ""
    m = re.search(r"Interfaz dibujada: \*\*(.+?)\*\*(.*)", inf)
    interfaz = (m.group(1) + m.group(2)).strip() if m else "—"
    ctl = _csv(d / "control_cadenas_cerradas.csv")
    cot = _csv(d / "chequeo_cotas.csv")
    inter = rep.get("interferencias", [])
    salida = "—"
    if logs:
        lg = pathlib.Path(logs) / caso / "log.txt"
        if lg.exists():
            mm = re.findall(r"^exit (\d+)", lg.read_text(encoding="utf-8", errors="replace"), re.M)
            salida = mm[-1] if mm else "—"
    P = D.get("P", {})
    return dict(caso=caso, est=est, n=len(est), ret=[e for e in est if e["estado"] == "RETENIDA"], items=len(rep.get("partes") or {}) or len(_csv(d / "TT300-C_despiece.csv")),
                cotas=len(cot), cotas_mal=sum(1 for r in cot if r[-1] != "OK"), controles=len(ctl), interf=sum(1 for r in inter if not r.get("ok") and not r.get("declarado")),
                conflictos=rep.get("conflictos_ids") or {t[:60]: dict(corto=t[:60]) for t in rep.get("conflictos_nucleo", [])}, interfaz=interfaz,
                modo=D.get("modo_nombre") or ("guiado" if P.get("drive_mode") == 1 else "pivotado"), fecha=D.get("fecha", "—"), salida=salida,
                soporte_E=(D.get("pivotado") or {}).get("fabricacion", {}).get("soporte_E") if D.get("modo") == 2 else None,
                variante=(re.search(r"VARIANTE (\S+)$", est[0]["titulo"]).group(1) if est and re.search(r"VARIANTE (\S+)$", est[0]["titulo"]) else caso))


def corto(cod):
    return cod.replace("TT300C-", "").replace("-C", "") if cod.endswith("-C") else cod.replace("TT300C-", "")


def escribir(dest, casos, logs=None, nota_w=NOTA_W, nucleo=None):
    dest = pathlib.Path(dest)
    C = [leer_caso(dest / c, logs, c) for c in casos if (dest / c / "estado_laminas.csv").exists()]
    fecha = max((c["fecha"] for c in C), default="—")
    L = [f"# TT300-C · Índice general de la entrega de planos (Rev. C)", "", f"Fecha de los juegos: {fecha}." + (f" Núcleo: {nucleo}." if nucleo else ""), "",
         f"**{ADVERTENCIA}**", "", "Estado de las láminas: todas EMITIDAS PARA REVISIÓN (sin aprobación; firmas DIBUJÓ/REVISÓ/APROBÓ A DEFINIR). "
         "Las RETENIDAS no deben fabricarse: dependen de un conflicto geométrico declarado del núcleo (GEN-009 de cada juego) o de datos del proveedor; "
         "una lámina deja de estar retenida solo cuando el choque ya no existe en la geometría del JSON.", "", f"**{nota_w}**", ""] + ([f"**{nota_plancha(C)}**", ""] if nota_plancha(C) else []) + [
         "## Resumen por caso", "", "| Caso | Variante | Accionamiento | Interfaz | Láminas | Emitidas p/ revisión | Retenidas | Ítems | Cotas (fallas) | Fallas de controles | Interferencias no declaradas | Salida | Carpeta |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in C:
        L.append(f"| {c['caso']} | {c['variante']} | {c['modo']} | {c['interfaz']} | {c['n']} | {c['n'] - len(c['ret'])} | {len(c['ret'])} | {c['items']} | {c['cotas']} ({c['cotas_mal']}) | {c['controles']} | {c['interf']} | {c['salida']} | `{c['caso']}/` |")
    L += ["", "## Conflictos del núcleo activos (geometría del JSON) por caso", ""]
    for c in C:
        L.append(f"- **{c['caso']}**: " + ("; ".join(v.get("corto", k) for k, v in c["conflictos"].items()) or "ninguno"))
    # matriz lámina × caso
    cods = []
    for c in C:
        for e in c["est"]:
            if corto(e["lamina"]) not in cods:
                cods.append(corto(e["lamina"]))
    orden = lambda s: (0 if s.startswith("GEN-001") else 1 if s.startswith("CON") else 3 if s.startswith("GEN") else 2, s)
    cods.sort(key=orden)
    tit = {}
    for c in C:
        for e in c["est"]:
            tit.setdefault(corto(e["lamina"]), re.sub(r" — VARIANTE \S+$", "", e["titulo"]))
    L += ["", "## Láminas por caso (E = emitida para revisión, R = RETENIDA, · = no aplica)", "",
          "| Lámina | Título (del caso donde aparece primero) | " + " | ".join(c["caso"] for c in C) + " |", "|---|---|" + "---|" * len(C)]
    est_of = {c["caso"]: {corto(e["lamina"]): e for e in c["est"]} for c in C}
    for k in cods:
        L.append(f"| {k} | {tit[k]} | " + " | ".join(("R" if est_of[c['caso']][k]["estado"] == "RETENIDA" else "E") if k in est_of[c["caso"]] else "·" for c in C) + " |")
    L += ["", "## Láminas RETENIDAS y su motivo", ""]
    for c in C:
        L.append(f"### {c['caso']} ({len(c['ret'])} de {c['n']})")
        L.append("")
        for e in c["ret"]:
            L.append(f"- {corto(e['lamina'])} · {re.sub(r' — VARIANTE \S+$', '', e['titulo'])}: {e['motivo']}")
        if not c["ret"]:
            L.append("- ninguna")
        L.append("")
    L += ["## Contenido de cada carpeta de caso", "",
          "`TT300-C_Planos_RevC.pdf` (juego combinado con marcadores), `planos/` (PDF y DXF por lámina), `TT300-C_DXF_RevC.zip`, `TT300-C.step` / `.glb`, despiece CSV/XLSX, "
          "`lista_de_cortes.csv`, `soldaduras.csv` (programa: tipo, tamaño, END), `estado_laminas.csv`, `chequeo_cotas.csv`, `informe_paquete.md`, lista de verificación del revisor (MD/PDF) "
          "y `TT300-C_design.json` (el JSON exportado del núcleo del que salen el cálculo y los planos).", "", f"**{ADVERTENCIA}**", ""]
    (dest / "INDICE.md").write_text("\n".join(L), encoding="utf-8")
    _pdf(dest / "INDICE.pdf", C, cods, tit, est_of, fecha, nota_w, nucleo)
    return C


def _pdf(path, C, cods, tit, est_of, fecha, nota_w, nucleo):
    from reportlab.lib.pagesizes import A3, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    fn, fb = "Helvetica", "Helvetica-Bold"
    for reg, bold in (("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),):
        if pathlib.Path(reg).exists() and pathlib.Path(bold).exists():
            pdfmetrics.registerFont(TTFont("DV", reg)); pdfmetrics.registerFont(TTFont("DVB", bold)); fn, fb = "DV", "DVB"
    ss = getSampleStyleSheet()
    sN = ParagraphStyle("n", parent=ss["Normal"], fontName=fn, fontSize=8.5, leading=10.5)
    sS = ParagraphStyle("s", parent=sN, fontSize=7, leading=8.4)
    sB = ParagraphStyle("b", parent=sN, fontName=fb)
    sH1 = ParagraphStyle("h1", parent=sN, fontName=fb, fontSize=15, leading=19, spaceAfter=4)
    sH2 = ParagraphStyle("h2", parent=sN, fontName=fb, fontSize=11, leading=14, spaceBefore=6, spaceAfter=3)
    sW = ParagraphStyle("w", parent=sB, fontSize=9.5, leading=12, textColor=colors.HexColor("#a00000"))
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def footer(cv, doc):
        cv.saveState()
        cv.setFont(fb, 8)
        cv.setFillColor(colors.HexColor("#a00000"))
        cv.drawCentredString(doc.pagesize[0] / 2, 8 * mm, ADVERTENCIA)
        cv.setFillColor(colors.black)
        cv.setFont(fn, 7.5)
        cv.drawRightString(doc.pagesize[0] - 12 * mm, 8 * mm, f"Página {doc.page}")
        cv.drawString(12 * mm, 8 * mm, "TT300-C · Índice de entrega · EMITIDO PARA REVISIÓN")
        cv.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=landscape(A3), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=16 * mm,
                            title="TT300-C Índice general de la entrega de planos", author="Generador de planos TT300-C (cad/)")
    st = [Paragraph("TT300-C · Tornamesa hidráulica 300 tf · Índice general de la entrega de planos (Rev. C)", sH1),
          Paragraph(esc(f"Fecha de los juegos: {fecha}." + (f" Núcleo: {nucleo}." if nucleo else "") + " Estado: EMITIDO PARA REVISIÓN (sin aprobación)."), sN),
          Spacer(1, 3), Paragraph(esc(ADVERTENCIA), sW), Spacer(1, 3), Paragraph(esc(nota_w), sW), Spacer(1, 3)] + ([Paragraph(esc(nota_plancha(C)), sW), Spacer(1, 3)] if nota_plancha(C) else []) + [
          Paragraph(esc("Las láminas RETENIDAS no deben fabricarse: dependen de un conflicto geométrico declarado del núcleo (GEN-009 de cada juego) o de datos del proveedor; "
                        "una lámina deja de estar retenida solo cuando el choque ya no existe en la geometría del JSON. El cajetín de cada lámina RETENIDA lo indica en el campo de estado."), sN),
          Paragraph("Resumen por caso", sH2)]
    hdr = ["Caso", "Var.", "Accionamiento", "Interfaz dibujada", "Láminas", "Emitidas p/ rev.", "Retenidas", "Ítems", "Cotas (fallas)", "Fallas controles", "Interf. no decl.", "Salida", "Conflictos del núcleo activos"]
    rows = [[Paragraph(esc(h), ParagraphStyle("hh", parent=sS, fontName=fb)) for h in hdr]]
    for c in C:
        rows.append([Paragraph(esc(x), sS) for x in (c["caso"], c["variante"], c["modo"], c["interfaz"], c["n"], c["n"] - len(c["ret"]), len(c["ret"]), c["items"], f"{c['cotas']} ({c['cotas_mal']})",
                                                     c["controles"], c["interf"], c["salida"], "; ".join(v.get("corto", k) for k, v in c["conflictos"].items()) or "ninguno")])
    t = Table(rows, colWidths=[16 * mm, 14 * mm, 30 * mm, 70 * mm, 18 * mm, 20 * mm, 20 * mm, 14 * mm, 22 * mm, 20 * mm, 20 * mm, 14 * mm, 118 * mm], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    st += [t, Paragraph("Láminas RETENIDAS y su motivo", sH2)]
    rr = [[Paragraph(esc(h), ParagraphStyle("hh", parent=sS, fontName=fb)) for h in ("Caso", "Lámina", "Título", "Motivo")]]
    for c in C:
        for e in c["ret"]:
            rr.append([Paragraph(esc(x), sS) for x in (c["caso"], corto(e["lamina"]), re.sub(r" — VARIANTE \S+$", "", e["titulo"]), e["motivo"])])
    if len(rr) == 1:
        rr.append([Paragraph("—", sS)] * 4)
    t = Table(rr, colWidths=[18 * mm, 26 * mm, 190 * mm, 160 * mm], repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    st += [t, PageBreak(), Paragraph("Láminas por caso (E = emitida para revisión · R = RETENIDA · en blanco = no aplica a ese caso)", sH2)]
    hdr = ["Lámina", "Título (del primer caso donde aparece)"] + [c["caso"] for c in C]
    rows = [[Paragraph(esc(h), ParagraphStyle("hh", parent=sS, fontName=fb)) for h in hdr]]
    sty = [("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
           ("ALIGN", (2, 0), (-1, -1), "CENTER"), ("FONTNAME", (0, 1), (-1, -1), fn), ("FONTSIZE", (0, 1), (-1, -1), 7)]
    for i, k in enumerate(cods, 1):
        r = [k, Paragraph(esc(tit[k]), sS)]
        for j, c in enumerate(C):
            e = est_of[c["caso"]].get(k)
            r.append("" if e is None else ("R" if e["estado"] == "RETENIDA" else "E"))
            if e is not None and e["estado"] == "RETENIDA":
                sty.append(("BACKGROUND", (2 + j, i), (2 + j, i), colors.HexColor("#f4c7c3")))
        rows.append(r)
    t = Table(rows, colWidths=[24 * mm, 236 * mm] + [15 * mm] * len(C), repeatRows=1)
    t.setStyle(TableStyle(sty))
    st += [t]
    for c in C:
        st += [PageBreak(), Paragraph(esc(f"Caso {c['caso']} · variante {c['variante']} · {c['modo']} · {c['interfaz']}"), sH2),
               Paragraph(esc(f"Carpeta {c['caso']}/ · PDF combinado {c['caso']}/TT300-C_Planos_RevC.pdf · {c['n']} láminas ({len(c['ret'])} RETENIDAS) · {c['items']} ítems · {c['cotas']} cotas verificadas"), sN), Spacer(1, 3)]
        rows = [[Paragraph(esc(h), ParagraphStyle("hh", parent=sS, fontName=fb)) for h in ("N°", "Lámina", "Título", "Estado", "Motivo de la retención")]]
        sty = [("GRID", (0, 0), (-1, -1), 0.3, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        for i, e in enumerate(c["est"], 1):
            rows.append([Paragraph(str(e["n"]), sS), Paragraph(esc(corto(e["lamina"])), sS), Paragraph(esc(re.sub(r" — VARIANTE \S+$", "", e["titulo"])), sS),
                         Paragraph(esc(e["estado"]), sS), Paragraph(esc(e["motivo"]), sS)])
            if e["estado"] == "RETENIDA":
                sty.append(("BACKGROUND", (3, i), (3, i), colors.HexColor("#f4c7c3")))
        t = Table(rows, colWidths=[10 * mm, 26 * mm, 220 * mm, 40 * mm, 100 * mm], repeatRows=1)
        t.setStyle(TableStyle(sty))
        st.append(t)
    doc.build(st, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    dest = a[0]
    casos = CASOS
    logs = None
    nucleo = None
    if "--casos" in a:
        casos = a[a.index("--casos") + 1].split(",")
    if "--logs" in a:
        logs = a[a.index("--logs") + 1]
    if "--nucleo" in a:
        nucleo = a[a.index("--nucleo") + 1]
    C = escribir(dest, casos, logs, nucleo=nucleo)
    for c in C:
        print(f"{c['caso']}: {c['n']} láminas, {len(c['ret'])} retenidas, {c['items']} ítems, cotas {c['cotas']} ({c['cotas_mal']}), controles {c['controles']}, interf. {c['interf']}, salida {c['salida']}")
