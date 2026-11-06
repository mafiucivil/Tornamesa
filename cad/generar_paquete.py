"""Genera el paquete completo de planos de fabricación TT300-C: modelo 3D (STEP/GLB), láminas (DXF + PDF), despiece (CSV/XLSX), chequeo de cotas,
lista de verificación del revisor e informe del paquete.
Uso: python3 cad/generar_paquete.py [design.json] [--out DIR] [--entrega DIR]
Sin design.json se exporta el diseño por defecto con `node tools/export_design.js` (misma fuente única del cálculo)."""
import json, math, sys, pathlib, subprocess, time, zipfile, csv, shutil, datetime
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import *
import modelo3d_tt300c as M3
import hojas_base, hojas_fab, hojas_gen, lista, informe
import vistas
import draw


def main():
    argv = sys.argv[1:]
    out = OUT_DEFAULT
    entrega = None
    if "--out" in argv:
        i = argv.index("--out"); out = pathlib.Path(argv[i + 1]); del argv[i:i + 2]
    if "--entrega" in argv:
        i = argv.index("--entrega"); entrega = pathlib.Path(argv[i + 1]); del argv[i:i + 2]
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
    # ---- modelo 3D ----
    m, rep = M3.run(D, out)
    ms = rep["masas"]
    print(f"  3D vs núcleo: {ms['total_3d']:.1f} / {ms['total_nucleo']:.1f} kg ({ms['dif_pct']:+.2f} %); fuera del núcleo {ms['masa_fuera']:.1f} kg; CG {tuple(round(x, 1) for x in rep['cg'])}", flush=True)
    inter_bad = [r for r in rep["interferencias"] if not r["ok"]]
    print(f"  interferencias: {len(inter_bad)}", flush=True)
    # ---- láminas ----
    ctx = hojas_base.Ctx(m)
    ctx.rep = rep
    gaps = informe.brechas(ctx, rep)
    ctx.gaps = gaps
    g = ctx.g
    order = [hojas_gen.sheet_notas, hojas_gen.sheet_conjunto, hojas_gen.sheet_explosionada, hojas_gen.sheet_secuencia, hojas_gen.sheet_bom, hojas_gen.sheet_corte,
             hojas_gen.sheet_soldaduras, hojas_gen.sheet_tolerancias, lambda c: hojas_gen.sheet_supuestos(c, gaps),
             hojas_fab.sheet_base, hojas_fab.sheet_mensula, hojas_fab.sheet_oreja, hojas_fab.sheet_bancada, hojas_fab.sheet_patin, hojas_fab.sheet_una, hojas_fab.sheet_art,
             hojas_fab.sheet_mesa, hojas_fab.sheet_mesa_plan, hojas_fab.sheet_mesa_cubo, hojas_fab.sheet_pasador, hojas_fab.sheet_pivote]
    if g.opt:
        order += [hojas_fab.sheet_int_conj, hojas_fab.sheet_int_sect, hojas_fab.sheet_int_topes]
    if g.wood:
        order += [hojas_fab.sheet_madera]
    hojas = []
    for fn in order:
        t1 = time.time()
        h = fn(ctx)
        hojas.append(h)
        print(f"  lámina {h.plano} ({time.time() - t1:.0f} s)", flush=True)
    total = len(hojas)
    # índice en la lámina de notas
    h1 = hojas[0]
    s1 = h1.s
    idx = [[hh.plano, hh.titulo, hh.escala] for hh in hojas]
    hojas_gen.wtable(s1, 30, h1.indice_pos[1], [("Plano", 52), ("Título", 150), ("Escala", 40)], idx, h=1.9)
    pd = out / "planos"
    pd.mkdir(exist_ok=True)
    pdfs, dxfs = [], []
    for n, h in enumerate(hojas, 1):
        s = h.finish(n, total)
        base = pd / h.plano
        s.save(str(base) + ".dxf", str(base) + ".pdf")
        pdfs.append(str(base) + ".pdf"); dxfs.append(str(base) + ".dxf")
    import pymupdf
    doc = pymupdf.open()
    for p in pdfs:
        doc.insert_pdf(pymupdf.open(p))
    comb = out / f"TT300-C_Planos_Rev{REV}.pdf"
    doc.save(str(comb))
    prev = out / "png"
    prev.mkdir(exist_ok=True)
    for p in pdfs:
        pymupdf.open(p)[0].get_pixmap(dpi=45).save(str(prev / (pathlib.Path(p).stem + ".png")))
    with zipfile.ZipFile(out / f"TT300-C_DXF_Rev{REV}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for d in dxfs:
            z.write(d, pathlib.Path(d).name)
        z.write(out / "TT300-C_design.json", "TT300-C_design.json")
    # ---- control de marco: todo dentro de la hoja ----
    import ezdxf
    from ezdxf import bbox
    fuera = []
    for d in dxfs:
        msp = ezdxf.readfile(d).modelspace()
        b = bbox.extents(msp)
        if b.extmin.x < -0.5 or b.extmin.y < -0.5 or b.extmax.x > draw.W + 0.5 or b.extmax.y > draw.H + 0.5:
            fuera.append((pathlib.Path(d).stem, [round(v) for v in (b.extmin.x, b.extmin.y, b.extmax.x, b.extmax.y)]))
    # ---- cotas ----
    cr = vistas.COTAS.rows
    with open(out / "chequeo_cotas.csv", "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh, delimiter=";")
        wr.writerow(["lámina", "vista", "texto", "valor_dibujo", "tipo", "extremo_a_mm", "extremo_b_mm", "resultado"])
        for r in cr:
            wr.writerow([r["sheet"], r["vista"], r["texto"], r["valor_dibujo"], r["tipo"], r["extremo_a"], r["extremo_b"], "OK" if r["ok"] else "FALLA"])
    # ---- despiece ----
    informe.escribir_bom(ctx, rep, out)
    informe.lista_verificacion(ctx, hojas, out)
    informe.escribir_informe(ctx, rep, hojas, gaps, fuera, cr, out, time.time() - t0)
    print(f"Paquete listo en {out}: {total} láminas, {len(m.parts)} ítems, cotas {len(cr)} ({sum(1 for r in cr if not r['ok'])} fallas), "
          f"interferencias {len(inter_bad)}, fuera de marco {len(fuera)}; {time.time() - t0:.0f} s", flush=True)
    if entrega:
        informe.copiar_entrega(out, entrega, pdfs)
    if inter_bad or any(not r["ok"] for r in cr):
        sys.exit(2)


if __name__ == "__main__":
    main()
