"""Genera el paquete de planos TT300-BX (disco inoxidable atornillado + pastillas de UHMW en un portador soldado) desde el JSON de diseño de
`node tools/export_design_bx.js` (mismo esquema que tools/export_design.js más el bloque «bx»).
Uso: python3 cad/generar_paquete_bx.py [design_bx.json] [--out DIR] [--entrega DIR] [--sin-dxf] [--solo fragmento,...]
Sin design_bx.json se exporta con `node tools/export_design_bx.js`. El trabajo lo hace cad/generar_paquete.py, que detecta el bloque «bx»
(el mismo generador sirve ambos juegos; sin «bx» el juego TT300-C no cambia)."""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import ROOT, OUT_DEFAULT  # noqa: E402


def main():
    argv = sys.argv[1:]
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in ("--out", "--entrega", "--solo"))]
    if not pos:
        out = pathlib.Path(argv[argv.index("--out") + 1]) if "--out" in argv else OUT_DEFAULT / "bx"
        out.mkdir(parents=True, exist_ok=True)
        jpath = out / "TT300-BX_design.json"
        print("Exportando el diseño BX con node tools/export_design_bx.js ...", flush=True)
        r = subprocess.run(["node", str(ROOT / "tools" / "export_design_bx.js")], capture_output=True, text=True)
        if r.returncode:
            sys.exit("No se pudo exportar el diseño BX: " + r.stderr)
        jpath.write_text(r.stdout, encoding="utf-8")
        argv = [str(jpath)] + argv
        if "--out" not in argv:
            argv += ["--out", str(out)]
    import json
    D = json.load(open([a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in ("--out", "--entrega", "--solo"))][0], encoding="utf-8"))
    if not D.get("bx"):
        sys.exit("El JSON no trae el bloque «bx»: use cad/generar_paquete.py (juego TT300-C) o exporte con node tools/export_design_bx.js.")
    import generar_paquete
    sys.argv = [sys.argv[0]] + argv
    generar_paquete.main()


if __name__ == "__main__":
    main()
