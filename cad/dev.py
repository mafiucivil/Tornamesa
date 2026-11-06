"""Banco de pruebas: python3 cad/dev.py <hoja> [json] -> genera la(s) lámina(s) en el scratchpad y PNG."""
import sys, pathlib, time, importlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
SC = pathlib.Path("/tmp/claude-0/-home-user-Tornamesa/56f13788-1d6a-50be-87ae-e9f5fbee4093/scratchpad")
from geom import load
import modelo3d_tt300c as M3
import hojas_base
from hojas_base import Ctx, build_welds


def main():
    names = sys.argv[1].split(",")
    jp = sys.argv[2] if len(sys.argv) > 2 else str(SC / "d0.json")
    D = load(jp)
    m = M3.build(D, verbose=False)
    M3.apply_backing_holes(m)
    ctx = Ctx(m)
    build_welds(ctx)
    import hojas_pie
    hojas_con = hojas_gen = hojas_pie
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
