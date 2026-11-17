"""Lanza cad/generar_paquete.py con los mismos argumentos, adaptando lo que en Windows no existe (sin tocar cad/):

  · fuentes: cad/draw.py mide los textos con /usr/share/fonts/truetype/liberation/LiberationSans-*.ttf; si esa ruta no existe,
    se usa la copia de tools/fuentes/ (Liberation Sans, licencia SIL OFL 1.1) y se registra también en ezdxf para el PDF;
  · procesos: el generador dibuja las láminas con multiprocessing.get_context("fork"), que Windows no tiene; sin «fork»
    las láminas se dibujan en serie dentro del mismo proceso (mismo resultado, más lento).

Uso: python tools/lanzar_generador.py <design.json> --out DIR --entrega DIR   (los argumentos pasan tal cual a cad/generar_paquete.py)
TT300C_COMPAT=1 fuerza ambas adaptaciones también en Linux (prueba del camino de Windows)."""
import multiprocessing
import os
import pathlib
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FUENTES = ROOT / "tools" / "fuentes"
LINUX_LIB = "/usr/share/fonts/truetype/liberation/"
FORZAR = os.environ.get("TT300C_COMPAT") == "1"


def _fuentes():
    if not FORZAR and pathlib.Path(LINUX_LIB, "LiberationSans-Regular.ttf").exists():
        return False
    from PIL import ImageFont
    orig = ImageFont.truetype

    def truetype(font=None, *a, **k):
        if isinstance(font, str) and font.replace("\\", "/").startswith(LINUX_LIB):
            font = str(FUENTES / pathlib.PurePosixPath(font).name)
        return orig(font, *a, **k)

    ImageFont.truetype = truetype
    try:
        from ezdxf.fonts import fonts
        fonts.font_manager.scan_folder(FUENTES)
    except Exception as ex:  # el PDF usará la fuente de reemplazo de ezdxf
        print(f"AVISO: no se pudieron registrar las fuentes en ezdxf: {ex}", flush=True)
    return True


class _PoolSerie:
    """Sustituto de multiprocessing.Pool que ejecuta en serie (para plataformas sin «fork»)."""

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def imap_unordered(self, fn, it, chunksize=1):
        return map(fn, it)

    imap = imap_unordered

    def map(self, fn, it, chunksize=None):
        return list(map(fn, it))


class _CtxSerie:
    Pool = _PoolSerie


def _procesos():
    if not FORZAR and "fork" in multiprocessing.get_all_start_methods():
        return False
    orig = multiprocessing.get_context

    def get_context(method=None):
        if method == "fork":
            return _CtxSerie()
        return orig(method)

    multiprocessing.get_context = get_context
    return True


def main():
    f, p = _fuentes(), _procesos()
    if f or p:
        print("Modo compatible: " + ", ".join(x for x, on in (("fuentes de tools/fuentes", f), ("láminas en serie (sin fork)", p)) if on), flush=True)
    script = ROOT / "cad" / "generar_paquete.py"
    sys.argv = [str(script)] + sys.argv[1:]
    sys.path.insert(0, str(script.parent))
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
