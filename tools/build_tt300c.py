"""Arma la herramienta autónoma dist/TT300-C_Verificacion.html (un solo archivo, sin dependencias externas)."""
import pathlib
root = pathlib.Path(__file__).resolve().parents[1]
pk = root / "packages"
s = (pk / "web" / "shell.html").read_text(encoding="utf-8")
for tag, f in [("FEA", pk / "core" / "fea.js"), ("CORE", pk / "core" / "tt300c.js"), ("AGENTS", pk / "agents" / "agentes.js"), ("PLANOS", pk / "web" / "planos_export.js"), ("UI", pk / "web" / "ui.js")]:
    code = f.read_text(encoding="utf-8").replace('if (typeof module !== "undefined") module.exports', "if (false) module.exports")
    s = s.replace("/*@@%s@@*/" % tag, code)
out = root / "dist" / "TT300-C_Verificacion.html"
out.parent.mkdir(exist_ok=True)
out.write_text(s, encoding="utf-8")
print(out, len(s.encode("utf-8")), "bytes")
