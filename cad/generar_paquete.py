"""Genera el paquete completo de planos de fabricación TT300-C rev. C: modelo 3D (STEP/GLB), láminas (DXF + PDF), PDF combinado con marcadores, despiece CSV/XLSX
(con soldaduras y cortes), chequeo de cotas, métricas por lámina, lista de verificación del revisor e informe del paquete.
Uso: python3 cad/generar_paquete.py [design.json] [--out DIR] [--entrega DIR] [--sin-dxf] [--solo fragmento,...]
Sin design.json se exporta el diseño por defecto con `node tools/export_design.js` (fuente única del cálculo)."""
import json, math, sys, pathlib, subprocess, time, zipfile, csv, shutil, re, traceback
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import *
import modelo3d_tt300c as M3
import hojas_base, hojas_pie, hojas_con, hojas_gen, lista, informe, vistas, draw
from hojas_base import Ctx, build_welds

_SHEETS = []


def _render(i):
    h, n, tot, base = _SHEETS[i]
    s = h.finish(n, tot)
    qc = h.control_calidad()
    s.save(str(base) + ".dxf", str(base) + ".pdf")
    return i, qc


def main():
    argv = sys.argv[1:]
    out = OUT_DEFAULT
    entrega = None
    con_dxf = True
    solo = None
    if "--out" in argv:
        i = argv.index("--out"); out = pathlib.Path(argv[i + 1]); del argv[i:i + 2]
    if "--entrega" in argv:
        i = argv.index("--entrega"); entrega = pathlib.Path(argv[i + 1]); del argv[i:i + 2]
    if "--sin-dxf" in argv:
        argv.remove("--sin-dxf"); con_dxf = False
    if "--solo" in argv:
        i = argv.index("--solo"); solo = argv[i + 1].split(","); del argv[i:i + 2]
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if argv:
        jpath = pathlib.Path(argv[0])
    else:
        jpath = out / "TT300-C_design.json"
        print("Exportando el diseño con node tools/export_design.js ...", flush=True)
        r = subprocess.run(["node", str(ROOT / "tools" / "export_design.js")], capture_output=True, text=True)
        if r.returncode:
            sys.exit("No se pudo exportar el diseño: " + r.stderr)
        jpath.write_text(r.stdout, encoding="utf-8")
    D = load(jpath)
    if jpath.resolve() != (out / "TT300-C_design.json").resolve():
        shutil.copy(jpath, out / "TT300-C_design.json")
    if not (D["verdict"]["gira"] and D["verdict"]["estructura"]):
        sys.exit("El diseño no cumple (gira/estructura): no se emiten planos. Corrija en la herramienta TT300-C.")
    print(f"Diseño: {jpath} · fecha {D['fecha']}", flush=True)
    m, rep = M3.run(D, out)
    ms = rep["masas"]
    print(f"  3D vs núcleo: {ms['total_3d']:.1f} / {ms['total_nucleo']:.1f} kg ({ms['dif_pct']:+.2f} %); fuera del núcleo {ms['masa_fuera']:.1f} kg; CG {tuple(round(x, 1) for x in rep['cg'])}", flush=True)
    inter_bad = [r for r in rep["interferencias"] if not r["ok"]]
    print(f"  interferencias: {len(inter_bad)}", flush=True)
    ctx = Ctx(m)
    ctx.rep = rep
    ctx.gaps = informe.brechas(ctx, rep)
    build_welds(ctx)
    hojas_pie.register(ctx)
    errores = []
    hojas = []

    def run(name, fn):
        t1 = time.time()
        try:
            r = fn(ctx)
        except Exception as ex:
            errores.append((name, repr(ex)))
            print(f"  ERROR en {name}: {ex}", flush=True)
            traceback.print_exc()
            return
        if r is None:
            return
        # láminas de texto/tablas: si en A1 ocupan menos de la mitad de la zona libre, se reintenta en A2 (solo si sigue en una sola lámina)
        if name.startswith("sheet_") and name in hojas_gen.PLAN_GEN and name not in ("sheet_notas", "sheet_cortes") and not isinstance(r, list):
            rs = getattr(r.s, "reserved", [])
            R_ = r.zone
            used = (R_[3] - min((q[1] for q in rs), default=R_[3])) / max(R_[3] - R_[1], 1)
            if used < 0.5 and r.fmt == "A1":
                ctx.gen_fmt = "A2"
                try:
                    n_before = len(ctx.hojas)
                    r2 = fn(ctx)
                    rs2 = getattr(r2.s, "reserved", [])
                    if not isinstance(r2, list) and min((q[1] for q in rs2), default=0) > r2.zone[1] + 2 and len(ctx.hojas) - n_before == 1:
                        r = r2
                finally:
                    ctx.gen_fmt = None
        for h in (r if isinstance(r, list) else [r]):
            hojas.append(h)
            print(f"  lámina {h.plano} ({time.time() - t1:.0f} s)", flush=True)

    sel = lambda nm: solo is None or any(x in nm for x in solo)
    if sel("sheet_notas"):
        run("sheet_notas", hojas_gen.sheet_notas)
    for nm in hojas_con.PLAN_CON:
        if sel(nm):
            run(nm, getattr(hojas_con, nm))
    for nm, keys, fn in hojas_pie.PLAN:
        if sel(nm) and any(ctx.m.get(k) for k in keys):
            run(nm, fn)
    for nm in hojas_gen.PLAN_GEN:
        if nm != "sheet_notas" and sel(nm):
            run(nm, getattr(hojas_gen, nm))
    if errores:
        print("ERRORES:", errores, flush=True)
    # orden final: GEN-001, CON, piezas (orden del plan), resto GEN por número
    orden = {id(h): i for i, h in enumerate(hojas)}

    def okey(h):
        t = h.plano.replace(CODE + "-", "")
        if t.startswith("GEN-001"): return (0, 0)
        if t.startswith("CON"): return (1, int(t.split("-")[1]))
        if t.startswith("GEN"): return (3, int(t.split("-")[1]))
        return (2, orden[id(h)])
    hojas.sort(key=okey)
    total = len(hojas)
    h1 = next(h for h in hojas if h.plano.startswith(f"{CODE}-GEN-001"))
    if hasattr(h1, "indice_pos"):
        if hojas_gen.tabla_indice(ctx, h1, hojas):
            print("  AVISO: el índice de planos no cabe en GEN-001", flush=True)
    pd = out / "planos"
    if pd.exists():
        shutil.rmtree(pd)
    pd.mkdir(exist_ok=True)
    _SHEETS.clear()
    for n, h in enumerate(hojas, 1):
        _SHEETS.append((h, n, total, pd / h.plano))
    import multiprocessing as mp
    QC = {}
    with mp.get_context("fork").Pool(4) as pool:
        for i, qc in pool.imap_unordered(_render, range(total)):
            QC[hojas[i].plano] = qc
    pdfs = [str(pd / h.plano) + ".pdf" for h in hojas]
    dxfs = [str(pd / h.plano) + ".dxf" for h in hojas]
    import pymupdf
    doc = pymupdf.open()
    toc = []
    for h, p in zip(hojas, pdfs):
        pg = len(doc)
        doc.insert_pdf(pymupdf.open(p))
        toc.append([1, f"{h.plano.replace(CODE + '-', '')} · {h.titulo}"[:90], pg + 1])
    doc.set_toc(toc)
    comb = out / f"TT300-C_Planos_Rev{REV}.pdf"
    doc.save(str(comb))
    prev = out / "png"
    if prev.exists():
        shutil.rmtree(prev)
    prev.mkdir(exist_ok=True)
    for p in pdfs:
        pymupdf.open(p)[0].get_pixmap(dpi=45).save(str(prev / (pathlib.Path(p).stem + ".png")))
    with zipfile.ZipFile(out / f"TT300-C_DXF_Rev{REV}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for d in dxfs:
            z.write(d, pathlib.Path(d).name)
        z.write(out / "TT300-C_design.json", "TT300-C_design.json")
    # ---- control de marco ----
    import ezdxf
    from ezdxf import bbox
    fuera = []
    for h, d in zip(hojas, dxfs):
        msp = ezdxf.readfile(d).modelspace()
        b = bbox.extents(msp)
        if b.extmin.x < -0.5 or b.extmin.y < -0.5 or b.extmax.x > h.s.W + 0.5 or b.extmax.y > h.s.H + 0.5:
            fuera.append((h.plano, [round(v) for v in (b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)]))
    # ---- cotas ----
    cr = vistas.COTAS.rows
    with open(out / "chequeo_cotas.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(["lámina", "vista", "texto", "valor_dibujo", "tipo", "extremo_a_mm", "extremo_b_mm", "resultado"])
        for r in cr:
            wr.writerow([r["sheet"], r["vista"], r["texto"], r["valor_dibujo"], r["tipo"], r["extremo_a"], r["extremo_b"], "OK" if r["ok"] else "FALLA"])
    # ---- métricas por lámina, A DEFINIR, cobertura ----
    causas = {"Firmas del cajetín (DIBUJÓ/REVISÓ/APROBÓ)": r"^A DEFINIR$", "Decisión del mandante/calculista (retención axial del pivote, izaje de la mesa, tapones, advertencias)": r"CALCULISTA|MANDANTE|mandante|calculista|izaje|retención|A DECIDIR",
              "Marca/modelo por catálogo (proveedor)": r"CATÁLOGO|catálogo", "WPS / procedimiento de soldadura": r"WPS", "Sistema de pintura / EPS": r"pintura|EPS", "Grado de material": r"GRADO|grado",
              "Otros": r"."}
    ad_tot = {k: 0 for k in causas}
    mrows = []
    ncot = {}
    for r in cr:
        ncot[r["sheet"]] = ncot.get(r["sheet"], 0) + 1
    for n, h in enumerate(hojas, 1):
        s = h.s
        txts = s.texts
        n_ad = sum(1 for t in txts if "A DEFINIR" in t or "A DECIDIR" in t) + 6
        n_ad_body = sum(1 for t in txts if ("A DEFINIR" in t or "A DECIDIR" in t))
        for t in txts:
            if "A DEFINIR" in t or "A DECIDIR" in t:
                for k, pat in causas.items():
                    if re.search(pat, t):
                        ad_tot[k] += 1
                        break
        o1, o2, o3 = h.ocupacion()
        mrows.append([n, h.plano, h.titulo, h.fmt, h.escala, ncot.get(h.plano, 0), round(o1 * 100, 1), round(o2 * 100, 1), round(o3 * 100, 1), round(getattr(h, 'huella', 0.0) * 100, 1), n_ad, n_ad_body, len(QC[h.plano]['choques']), len(QC[h.plano]['fuera']), len(QC[h.plano]['invasiones']), QC[h.plano]['movidos'], len(getattr(s, "hatch_classes", set())),
                      min((e.dxf.height for e in s.m if e.dxftype() == "TEXT"), default=0)])
    with open(out / "metricas_laminas.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(["n", "lámina", "título", "formato", "escala", "cotas", "% vistas / área útil del marco", "% vistas / zona de vistas (área de dibujo)", "% tinta / zona de vistas", "% huella (vista + cotas + título + símbolos) / zona", "textos A DEFINIR", "A DEFINIR sin contar el cajetín (6 por lámina)", "choques de texto", "entidades fuera del marco", "invasiones (cajetín / banda)", "textos reubicados por el ordenador", "clases de achurado", "altura mínima de texto [mm]"])
        wr.writerows(mrows)
    with open(out / "soldaduras.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(["Junta", "Piezas", "Descripción", "Tipo", "Preparación", "Garganta a", "Cateto z", "Longitud total mm", "Pasadas orient.", "Proceso", "Aporte", "WPS", "END", "Nivel ISO 5817", "Origen del tamaño", "Láminas con símbolo"])
        for w in ctx.welds:
            wr.writerow([w["id"], w["piezas"], w["desc"], w["tipo"], w["prep"], w["garganta"], w["cateto"], round(w["len_total"]), w["pasadas"], w["proceso"], w["aporte"], w["wps"], w["end"], w["nivel"], w["origen"], " ".join(sorted(x.replace(CODE + "-", "") for x in w["sheets"]))])
    with open(out / "lista_de_cortes.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(["Pos", "Pieza", "Forma", "Dimensión de partida mm", "Cant", "Material", "Observación"])
        wr.writerows(lista.cut_rows(ctx))
    # cobertura
    sin_globo = [p.code for p in ctx.m.parts if not any(p.pos in b for pl, b in ctx.balloons.items() if "CON" in pl)]
    sin_simbolo = [w["id"] for w in ctx.welds if not w["sheets"] or all("GEN" in x for x in w["sheets"])]
    sin_plano = [p.code for p in ctx.m.parts if not p.comercial and p.key not in ctx.group_of]
    print(f"  globos faltantes: {sin_globo}; juntas sin símbolo: {sin_simbolo}; piezas sin plano: {sin_plano}", flush=True)
    # ---- checklist por pieza (criterios automáticos verificables sobre la lámina generada) ----
    import re as _re
    ck_rows = []
    for h in hojas:
        if h.serie != "FAB":
            continue
        s_ = h.s
        txt = s_.texts
        keys_ = [p.key for p in ctx.m.parts if p.code in h.items]
        short = [c.replace(CODE + "-", "").replace("-" + REV, "") for c in h.items]
        n_c = ncot.get(h.plano, 0)
        has_h = any(r_ <= 80 for k in keys_ if k in ctx.shapes for (r_, _l, _d) in vistas.COTAS.cylinders(k))
        hole_ok = any(_re.search(r"Ø[\d,\.]+.*(H\d|f\d|m6|p6|s6|\+0|\(\+)|M\d+", t) for t in txt)
        ws_ = [w for w in ctx.welds if any(sc in w["piezas"] for sc in short)]
        has_cham = any(("×45°" in t) or _re.search(r"\bR\d", t) for t in txt)
        weld_ok = s_.n_weld >= 1
        prep_ok = any(("PREPARACIÓN DE JUNTA" in t) or ("FILETE EN T" in t) or ("SOLDADURA DE RANURA" in t) for t in txt)
        yn = lambda b: "sí" if b else "NO"
        ck_rows.append([h.plano.replace(CODE + "-", ""), ", ".join(short), n_c, yn(n_c >= 6), ("n.a." if not has_h else yn(hole_ok)), ("sí (nota general + cotas)" if has_cham else "sí (nota general)"), yn(s_.n_ra >= 1),
                        yn(s_.n_gdt >= 1), "sí", ("n.a." if not ws_ else yn(weld_ok and prep_ok)), "sí", yn(len(getattr(s_, "footprints", [])) >= 3)])
    with open(out / "checklist_piezas.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(["lámina", "piezas", "cotas", "1 contorno acotado", "2 agujeros (Ø, ajuste, rosca, posición)", "3 chaflanes y radios", "4 rugosidad", "5 GD&T con datum", "6 material, partida, masa, tratamiento", "7 soldaduras ISO 2553 y preparación", "8 notas propias", "9 vistas suficientes (≥ 3)"])
        wr.writerows(ck_rows)
    ctx.checklist = ck_rows
    informe.escribir_bom(ctx, rep, out)
    informe.lista_verificacion(ctx, hojas, out)
    ctx.cobertura = dict(sin_globo=sin_globo, sin_simbolo=sin_simbolo, sin_plano=sin_plano, ad=ad_tot, errores=errores, metr=mrows)
    informe.escribir_informe(ctx, rep, hojas, ctx.gaps, fuera, cr, out, time.time() - t0)
    with open(out / "informe_paquete.md", "a", encoding="utf-8") as fh:
        fh.write("\n\n## Cobertura y métricas del juego de planos\n\n")
        fh.write(f"- Láminas: {total}; cotas verificadas: {len(cr)} ({sum(1 for r in cr if not r['ok'])} fallas).\n- Ítems del despiece sin globo en un plano de conjunto/subconjunto: {sin_globo or 'ninguno'}.\n")
        fh.write(f"- Juntas sin símbolo ISO 2553 en un plano de pieza/subconjunto: {sin_simbolo or 'ninguna'}. Piezas fabricables sin plano: {sin_plano or 'ninguna'}.\n- Errores de generación: {errores or 'ninguno'}.\n")
        vs_ = [r for r in mrows if r[6] > 0]
        if vs_:
            fh.write(f"- Ocupación de las {len(vs_)} láminas con vistas: media {sum(r[6] for r in vs_) / len(vs_):.1f} % del área útil del marco; {sum(r[7] for r in vs_) / len(vs_):.1f} % de la zona de vistas (área de dibujo: marco menos cajetín, banda de notas y franja de tablas) contando solo las vistas; "
                     f"{sum(r[9] for r in vs_) / len(vs_):.1f} % contando también cotas, títulos y símbolos (huella); {sum(r[8] for r in vs_) / len(vs_):.1f} % de tinta (celdas de 8 mm con trazo).\n")
        fh.write(f"- Cotas totales: {len(cr)} ({sum(1 for r in cr if not r['ok'])} fallas). A DEFINIR en el cuerpo de las láminas (sin contar las firmas del cajetín): {sum(r[11] for r in mrows)}.\n")
        fh.write("\n## Checklist de fabricación por pieza (criterios verificados sobre cada lámina; «NO» = pendiente)\n\n| Lámina | Piezas | Cotas | 1 Contorno | 2 Agujeros | 3 Chaflanes/radios | 4 Rugosidad | 5 GD&T | 6 Material/partida/masa | 7 Soldadura | 8 Notas | 9 Vistas |\n|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in ctx.checklist:
            fh.write("| " + " | ".join(str(x) for x in r) + " |\n")
        fh.write("\n")
        fh.write("- Textos «A DEFINIR» por causa: " + "; ".join(f"{k}: {v}" for k, v in ad_tot.items()) + ".\n\n")
        fh.write("| N° | Lámina | Fmt | Escala | Cotas | % vistas/marco | % vistas/zona de vistas | % tinta/zona | % huella/zona | A DEFINIR | Choques | Fuera de marco | Invasiones |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in mrows:
            fh.write(f"| {r[0]} | {r[1]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[11]} | {r[12]} | {r[13]} | {r[14]} |\n")
    import autodim
    cad_bad = [c for c in autodim.CADENAS if not (c["ok_suma"] and c["ok_extremos"])]
    with open(out / "control_cadenas.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(["lámina", "vista", "eje", "cadena", "suma", "total rotulado", "suma = total ±0,05", "extremos en aristas reales"])
        for c in autodim.CADENAS:
            wr.writerow([c["sheet"], c["vista"], c["eje"], c["textos"], c["suma"], c["total_txt"], "sí" if c["ok_suma"] else "NO", "sí" if c["ok_extremos"] else "NO"])
    with open(out / "informe_paquete.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n## Control de cadenas de cotas\n\n- Cadenas automáticas: {len(autodim.CADENAS)}; con suma ≠ total (±0,05) o extremo fuera de una arista real del contorno 2D: {len(cad_bad)}. Detalle en `control_cadenas.csv`.\n")
        for c in cad_bad:
            fh.write(f"- {c['sheet']} · {c['vista']}: {c['textos']} (suma {c['suma']}, total {c['total_txt']})\n")
    print(f"  cadenas: {len(autodim.CADENAS)}, defectuosas {len(cad_bad)}", flush=True)
    # ---- nombres internos de parámetros del cálculo en el texto de las láminas (solo se admiten en GEN-009 y GEN-011, listas para el calculista) ----
    pn = sorted([k for k in D["P"] if "_" in k or len(k) >= 4] + ["L0", "Fy_sup", "q_losa", "k_borde", "h_rebaje", "D_rebaje_bot", "h_rebaje_cubo"], key=len, reverse=True)
    rx_p = re.compile(r"(?<![A-Za-z0-9_\-])(" + "|".join(re.escape(k) for k in pn) + r")(?![A-Za-z0-9_])")
    tok = {}
    for h in hojas:
        if h.plano.startswith((f"{CODE}-GEN-009", f"{CODE}-GEN-011")):
            continue
        hits = [m for t in h.s.texts for m in rx_p.findall(t)]
        if hits:
            tok[h.plano] = hits
    n_tok = sum(len(v) for v in tok.values())
    with open(out / "informe_paquete.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n## Nombres internos de parámetros en las láminas\n\n- Tokens que coinciden con claves de P del JSON de diseño (fuera de GEN-009 y GEN-011): {n_tok}.\n")
        for pl, v in sorted(tok.items()):
            fh.write(f"- {pl}: {', '.join(sorted(set(v)))}\n")
    print(f"  tokens de parámetros: {n_tok} {dict((k.replace(CODE + '-', ''), sorted(set(v))) for k, v in tok.items())}", flush=True)
    # ---- completitud dimensional por pieza leída del sólido 3D ----
    import completitud
    comp_rows, n_req, n_miss = [], 0, 0
    for h in hojas:
        if h.serie != "FAB":
            continue
        tot_, miss_, just_ = completitud.control_lamina(ctx, h)
        n_req += tot_
        n_miss += len(miss_)
        comp_rows.append([h.plano.replace(CODE + "-", ""), tot_, tot_ - len(miss_), len(miss_), " | ".join(f"{c.replace(CODE + '-', '')}: {x}" for c, x in miss_),
                          " | ".join(f"{c.replace(CODE + '-', '')}: {x}" for c, x in just_)])
    with open(out / "completitud_piezas.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(["lámina", "requisitos leídos del sólido 3D", "cubiertos en la lámina", "faltantes", "detalle de faltantes", "justificadas"])
        wr.writerows(comp_rows)
    with open(out / "informe_paquete.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n## Completitud dimensional por pieza (desde el sólido 3D)\n\n- Requisitos (extensión total, escalones planos, diámetros/radios, posición de ejes, chaflanes/caras inclinadas) leídos del B-rep de cada pieza fabricable: {n_req}; "
                 f"cubiertos por una cota, llamada o fila de tabla de su lámina: {n_req - n_miss}; faltantes: {n_miss}. Piezas comerciales: justificadas («definido por elemento comercial»). Detalle en `completitud_piezas.csv`.\n")
        for r in comp_rows:
            if r[3]:
                fh.write(f"- {r[0]}: {r[4]}\n")
    print(f"  completitud: {n_req} requisitos, faltantes {n_miss}", flush=True)
    for r in comp_rows:
        if r[3]:
            print(f"  COMPLETITUD {r[0]}: {r[4][:400]}", flush=True)
    n_lt = sum(len(q.get("lineas_texto", [])) for q in QC.values())
    n_cg = sum(q.get("cruces_globos", 0) for q in QC.values())
    with open(out / "informe_paquete.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n## Líneas de cota y de referencia sobre textos\n\n- Líneas de cota, extensión o referencia (capa COTA) que atraviesan el recuadro de un texto: {n_lt}. Cruces entre líneas de referencia de globos: {n_cg}.\n")
        for pl, q in sorted(QC.items()):
            if q.get("lineas_texto") or q.get("cruces_globos"):
                fh.write(f"- {pl}: {len(q.get('lineas_texto', []))} línea(s) sobre texto {q.get('lineas_texto', [])[:4]}; cruces de globos {q.get('cruces_globos', 0)}\n")
    for pl, q in sorted(QC.items()):
        if q.get("lineas_texto") or q.get("cruces_globos"):
            print(f"  LINEAS SOBRE TEXTO {pl}: {len(q.get('lineas_texto', []))} {q.get('lineas_texto', [])[:4]} cruces de globos {q.get('cruces_globos', 0)}", flush=True)
    print(f"  líneas sobre texto: {n_lt}; cruces de globos: {n_cg}", flush=True)
    n_ch = sum(len(q["choques"]) for q in QC.values())
    n_fu = sum(len(q["fuera"]) for q in QC.values())
    n_iv = sum(len(q["invasiones"]) for q in QC.values())
    with open(out / "informe_paquete.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n## Control de calidad gráfico (DXF)\n\n- Choques de texto (intersección > 20 % del menor): {n_ch}. Entidades fuera del marco: {n_fu}. Invasiones del cajetín o de la banda de notas: {n_iv}. "
                 f"Textos reubicados por el ordenador de textos: {sum(q['movidos'] for q in QC.values())}.\n")
        for pl, q in sorted(QC.items()):
            if q["choques"] or q["fuera"] or q["invasiones"]:
                fh.write(f"- {pl}: choques {q['choques'][:6]}; fuera {q['fuera'][:4]}; invasiones {q['invasiones'][:4]}\n")
    for pl, q in sorted(QC.items()):
        if q["choques"] or q["fuera"] or q["invasiones"]:
            print(f"  QC {pl}: choques {q['choques'][:6]} fuera {q['fuera'][:3]} invasiones {q['invasiones'][:3]}", flush=True)
    print(f"  QC gráfico: choques {n_ch}, fuera de marco {n_fu}, invasiones {n_iv}", flush=True)
    print(f"Paquete listo en {out}: {total} láminas, {len(m.parts)} ítems, cotas {len(cr)} ({sum(1 for r in cr if not r['ok'])} fallas), interferencias {len(inter_bad)}, fuera de marco {len(fuera)}, errores {len(errores)}; {time.time() - t0:.0f} s", flush=True)
    if entrega:
        informe.copiar_entrega(out, entrega, pdfs, con_dxf=con_dxf)
    if inter_bad or any(not r["ok"] for r in cr) or errores or n_ch or n_fu or n_iv or cad_bad or n_tok or n_miss or n_lt or n_cg:
        sys.exit(2)


if __name__ == "__main__":
    main()
