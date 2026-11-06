"""Banco de pruebas: python3 cad/dev.py <función_de_lámina[,otra]> [design.json] -> genera la(s) lámina(s) (PDF/PNG) en el directorio temporal."""
import sys, pathlib, time, importlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tempfile
SC = pathlib.Path(tempfile.gettempdir()) / "tt300_dev"
(SC / "dev").mkdir(parents=True, exist_ok=True)
from geom import load
import modelo3d_tt300c as M3
import hojas_base
from hojas_base import Ctx, build_welds


def main():
    names = sys.argv[1].split(",")
    jp = sys.argv[2] if len(sys.argv) > 2 else str(pathlib.Path(__file__).resolve().parent / "out" / "TT300-C_design.json")
    D = load(jp)
    m = M3.build(D, verbose=False)
    M3.apply_backing_holes(m)
    ctx = Ctx(m)
    import modelo3d_tt300c as M3b
    ctx.rep = M3b.masas(m) and dict(masa_total_ensamble=M3b.cog(m)[0], cg=M3b.cog(m)[1])
    build_welds(ctx)
    import hojas_pie
    import hojas_con
    hojas_gen = hojas_pie
    hojas_pie.register(ctx)
    out = SC / "dev"
    import pymupdf
    for nm in names:
        t0 = time.time()
        fn = None
        for mod in (hojas_pie, hojas_con, hojas_gen):
            if hasattr(mod, nm):
                fn = getattr(mod, nm)
        h = fn(ctx)
        for h in (h if isinstance(h, list) else [h]):
            s = h.finish(1, 1)
            s.save(str(out / (nm + ".dxf")), str(out / (nm + ".pdf")))
            d = pymupdf.open(str(out / (nm + ".pdf")))
            d[0].get_pixmap(dpi=60).save(str(out / (nm + ".png")))
            o = h.ocupacion()
            print(nm, h.plano, f"{time.time() - t0:.0f}s", "ocup", [round(x, 2) for x in o], "cotas", sum(1 for r in vistas_rows() if r['sheet'] == h.plano), "fallas", [r['texto'] for r in vistas_rows() if r['sheet'] == h.plano and not r['ok']][:5])


def vistas_rows():
    import vistas
    return vistas.COTAS.rows


if __name__ == "__main__":
    main()
