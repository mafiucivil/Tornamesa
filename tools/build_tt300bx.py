"""Arma Tornamesa_BX_v<versión>.html en la raíz del repositorio: herramienta independiente que evalúa SOLO la tornamesa TT300-BX
(disco inoxidable atornillado + pastillas de UHMW). Un solo archivo, sin dependencias externas.
Fuentes: packages/web_bx/shell_bx.html y ui_bx.js (copia adaptada de packages/web/ui.js), packages/web_bx/worker_bx.js, el núcleo
(packages/core/fea.js, tt300c.js, tt300bx.js), los agentes (agentes.js, agentes_bx.js), packages/web/planos_export.js (dentro de la fachada
BX de packages/web/planos_export_bx.js) y packages/web/simulacion.js (con la fachada del hilo principal).
No toca Tornamesa_v*.html ni tools/build_tt300c.py. Requiere Node (precalcula los valores por defecto con tools/precalc_bx.js)."""
import base64, json, pathlib, re, subprocess

BX_VERSION = "1.0"
root = pathlib.Path(__file__).resolve().parents[1]
pk = root / "packages"
s = (pk / "web_bx" / "shell_bx.html").read_text(encoding="utf-8")
EXP = 'if (typeof module !== "undefined") module.exports'
def code(f):
    return f.read_text(encoding="utf-8").replace(EXP, "if (false) module.exports")
for tag, f in [("FEA", pk / "core" / "fea.js"), ("CORE", pk / "core" / "tt300c.js"), ("BX", pk / "core" / "tt300bx.js"),
               ("AGENTS", pk / "agents" / "agentes.js"), ("AGBX", pk / "agents" / "agentes_bx.js"), ("PLANOS_BX", pk / "web" / "planos_export_bx.js"),
               ("PLANOS", pk / "web" / "planos_export.js"), ("WORKER", pk / "web_bx" / "worker_bx.js"), ("SIM", pk / "web" / "simulacion.js"),
               ("UI", pk / "web_bx" / "ui_bx.js")]:
    marker = "/*@@%s@@*/" % tag
    assert s.count(marker) == 1, marker
    s = s.replace(marker, code(f))
# parámetros del núcleo que lee el módulo BX (el formulario muestra solo esos del grupo «inox»)
src = (pk / "core" / "tt300bx.js").read_text(encoding="utf-8") + (pk / "agents" / "agentes_bx.js").read_text(encoding="utf-8")
used = sorted(set(re.findall(r"\bP[A-Za-z0-9_]?\.([A-Za-z_][A-Za-z0-9_]*)", src)))
s = s.replace("/*@@BX_USED@@*/", "const BX_USED = %s;" % json.dumps(used))
# figura de la comparación de la guía (igual que la herramienta principal)
img = root / "docs" / "qa" / "guia_curva_KIET" / "comparacion.png"
s = s.replace("/*@@IMG@@*/", "const TT_IMG = { comparacion: %s };" % ('"data:image/png;base64,' + base64.b64encode(img.read_bytes()).decode("ascii") + '"' if img.exists() else "null"))
# resultado precalculado de los valores por defecto (mismo código del worker)
pre = subprocess.run(["node", str(root / "tools" / "precalc_bx.js")], cwd=str(root), check=True, capture_output=True, text=True, encoding="utf-8").stdout
import html
pj = json.loads(pre)
s = s.replace("@@PRE_ATTR@@", 'data-key="%s" data-fecha="%s"' % (html.escape(json.dumps(pj["key"]), quote=True), html.escape(pj["fecha"], quote=True)))
s = s.replace("/*@@PRE@@*/", json.dumps(pj["r"], ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
try:
    rev = subprocess.run(["git", "log", "-1", "--format=%h", "--", "packages/core"], cwd=str(root), capture_output=True, text=True).stdout.strip()
except Exception:
    rev = ""
s = s.replace("@@CORE_REV@@", rev or "")
s = s.replace("@@VERSION@@", BX_VERSION)
out = root / ("Tornamesa_BX_v%s.html" % BX_VERSION)
out.write_text(s, encoding="utf-8")
print(out, len(s.encode("utf-8")), "bytes")
