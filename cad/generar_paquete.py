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
    s.save(str(base) + ".dxf", str(base) + ".pdf")
    return i


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
    with mp.get_context("fork").Pool(4) as pool:
        for i in pool.imap_unordered(_render, range(total)):
            pass
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
        mrows.append([n, h.plano, h.titulo, h.fmt, h.escala, ncot.get(h.plano, 0), round(o1 * 100, 1), round(o2 * 100, 1), round(o3 * 100, 1), n_ad, n_ad_body, len(getattr(s, "hatch_classes", set())),
                      min((e.dxf.height for e in s.m if e.dxftype() == "TEXT"), default=0)])
    with open(out / "metricas_laminas.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(["n", "lámina", "título", "formato", "escala", "cotas", "% vistas / área útil del marco", "% vistas / zona de vistas (área de dibujo)", "% tinta / zona de vistas", "textos A DEFINIR", "A DEFINIR sin contar el cajetín (6 por lámina)", "clases de achurado", "altura mínima de texto [mm]"])
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
    informe.escribir_bom(ctx, rep, out)
    informe.lista_verificacion(ctx, hojas, out)
    ctx.cobertura = dict(sin_globo=sin_globo, sin_simbolo=sin_simbolo, sin_plano=sin_plano, ad=ad_tot, errores=errores, metr=mrows)
    informe.escribir_informe(ctx, rep, hojas, ctx.gaps, fuera, cr, out, time.time() - t0)
    with open(out / "informe_paquete.md", "a", encoding="utf-8") as fh:
        fh.write("\n\n## Cobertura y métricas del juego de planos\n\n")
        fh.write(f"- Láminas: {total}; cotas verificadas: {len(cr)} ({sum(1 for r in cr if not r['ok'])} fallas).\n- Ítems del despiece sin globo en un plano de conjunto/subconjunto: {sin_globo or 'ninguno'}.\n")
        fh.write(f"- Juntas sin símbolo ISO 2553 en un plano de pieza/subconjunto: {sin_simbolo or 'ninguna'}. Piezas fabricables sin plano: {sin_plano or 'ninguna'}.\n- Errores de generación: {errores or 'ninguno'}.\n")
        fh.write("- Textos «A DEFINIR» por causa: " + "; ".join(f"{k}: {v}" for k, v in ad_tot.items()) + ".\n\n")
        fh.write("| N° | Lámina | Fmt | Escala | Cotas | % vistas/marco | % vistas/zona de vistas | % tinta/zona | A DEFINIR |\n|---|---|---|---|---|---|---|---|---|\n")
        for r in mrows:
            fh.write(f"| {r[0]} | {r[1]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[10]} |\n")
    print(f"Paquete listo en {out}: {total} láminas, {len(m.parts)} ítems, cotas {len(cr)} ({sum(1 for r in cr if not r['ok'])} fallas), interferencias {len(inter_bad)}, fuera de marco {len(fuera)}, errores {len(errores)}; {time.time() - t0:.0f} s", flush=True)
    if entrega:
        informe.copiar_entrega(out, entrega, pdfs, con_dxf=con_dxf)
    if inter_bad or any(not r["ok"] for r in cr) or errores:
        sys.exit(2)


if __name__ == "__main__":
    main()
