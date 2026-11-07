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
    import hojas_gen
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
            qc = h.control_calidad()
            if qc.get("lineas_texto") or qc.get("cruces_globos"):
                print("   LINEAS SOBRE TEXTO", h.plano, len(qc["lineas_texto"]), qc["lineas_texto"][:8], "cruces de globos", qc.get("cruces_globos"))
            if qc["choques"] or qc["fuera"] or qc["invasiones"]:
                print("   QC", nm, "choques", qc["choques"], "fuera", qc["fuera"][:3], "inv", qc["invasiones"][:3], "movidos", qc["movidos"])
            fn_ = h.plano
            s.save(str(out / (fn_ + ".dxf")), str(out / (fn_ + ".pdf")))
            d = pymupdf.open(str(out / (fn_ + ".pdf")))
            d[0].get_pixmap(dpi=60).save(str(out / (fn_ + ".png")))
            o = h.ocupacion()
            import ezdxf
            from ezdxf import bbox as _bb
            b_ = _bb.extents(ezdxf.readfile(str(out / (fn_ + ".dxf"))).modelspace())
            if b_.extmin.x < -0.5 or b_.extmin.y < -0.5 or b_.extmax.x > h.s.W + 0.5 or b_.extmax.y > h.s.H + 0.5:
                print("   FUERA DE MARCO", nm, [round(v) for v in (b_.extmin.x, b_.extmin.y, b_.extmax.x, b_.extmax.y)], "hoja", h.s.W, h.s.H)
            import os
            import autodim
            for c_ in autodim.CADENAS:
                if c_["sheet"] == h.plano and not (c_["ok_suma"] and c_["ok_extremos"]):
                    print("   CADENA MALA", c_)
            if os.environ.get("COTAS"):
                for r in vistas_rows():
                    if r["sheet"] == h.plano:
                        print("    ", r["vista"], "|", r["texto"], "|", r["valor_dibujo"], r["ok"])
            if getattr(h, "serie", "") == "FAB":
                import completitud
                n_, miss_, _j = completitud.control_lamina(ctx, h)
                print("   COMPLETITUD", h.plano, f"{n_ - len(miss_)}/{n_}", miss_[:40])
            print(nm, h.plano, f"{time.time() - t0:.0f}s", "ocup", [round(x, 2) for x in o], "huella", round(getattr(h, "huella", 0), 2), "cotas", sum(1 for r in vistas_rows() if r['sheet'] == h.plano), "fallas", [r['texto'] for r in vistas_rows() if r['sheet'] == h.plano and not r['ok']][:5])


def vistas_rows():
    import vistas
    return vistas.COTAS.rows


if __name__ == "__main__":
    main()
