"""Arma la herramienta principal Tornamesa_v<versión>.html en la raíz del repositorio (un solo archivo, sin dependencias externas).
La versión sale del archivo VERSION; al subirla se elimina el archivo de la versión anterior (queda en el historial de git)."""
import pathlib
root = pathlib.Path(__file__).resolve().parents[1]
pk = root / "packages"
s = (pk / "web" / "shell.html").read_text(encoding="utf-8")
for tag, f in [("FEA", pk / "core" / "fea.js"), ("CORE", pk / "core" / "tt300c.js"), ("AGENTS", pk / "agents" / "agentes.js"), ("PLANOS", pk / "web" / "planos_export.js"), ("SIM", pk / "web" / "simulacion.js"), ("UI", pk / "web" / "ui.js")]:
    code = f.read_text(encoding="utf-8").replace('if (typeof module !== "undefined") module.exports', "if (false) module.exports")
    s = s.replace("/*@@%s@@*/" % tag, code)
# figura de la comparación de la guía (docs/qa/guia_curva_KIET/comparacion.png), embebida en base64 para la pestaña «Comparación de la guía»
import base64
img = root / "docs" / "qa" / "guia_curva_KIET" / "comparacion.png"
s = s.replace("/*@@IMG@@*/", "const TT_IMG = { comparacion: %s };" % ('"data:image/png;base64,' + base64.b64encode(img.read_bytes()).decode("ascii") + '"' if img.exists() else "null"))
ver = (root / "VERSION").read_text(encoding="utf-8").strip()
s = s.replace("@@VERSION@@", ver)
out = root / ("Tornamesa_v%s.html" % ver)
for old in root.glob("Tornamesa_v*.html"):
    if old != out:
        old.unlink()
out.write_text(s, encoding="utf-8")
print(out, len(s.encode("utf-8")), "bytes")
