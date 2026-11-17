"""Arma Tornamesa_BX_v<versión>.html en la raíz del repositorio: herramienta independiente que evalúa SOLO la tornamesa TT300-BX
(disco inoxidable atornillado + pastillas de UHMW). Un solo archivo, sin dependencias externas.
Fuentes: packages/web_bx/shell_bx.html y ui_bx.js (copia adaptada de packages/web/ui.js), packages/web_bx/worker_bx.js, el núcleo
(packages/core/fea.js, tt300c.js, tt300bx.js), los agentes (agentes.js, agentes_bx.js), packages/web/planos_export.js (dentro de la fachada
BX de packages/web/planos_export_bx.js) y packages/web/simulacion.js (con la fachada del hilo principal).
No toca Tornamesa_v*.html ni tools/build_tt300c.py. Requiere Node (precalcula los valores por defecto con tools/precalc_bx.js, en paralelo; tarda unos minutos)."""
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
# resultados precalculados de los valores por defecto (mismo código del worker), en procesos de Node en paralelo:
# análisis, bloques diferidos (escenarios, mercado, capacidad por cilindros, térmica) y la memoria del JSON de diseño (PLANOS_BX.exportCalls)
import html
from concurrent.futures import ThreadPoolExecutor
def node(mode):
    return subprocess.run(["node", str(root / "tools" / "precalc_bx.js"), mode], cwd=str(root), check=True, capture_output=True, text=True, encoding="utf-8").stdout
ncalls = int(subprocess.run(["node", "-e", 'const B=require("./packages/web/planos_export_bx.js");console.log(B.exportCalls(require("./packages/core/tt300bx.js").defaults()).length)'], cwd=str(root), check=True, capture_output=True, text=True).stdout)
calls = list(range(3, ncalls))                                  # 0 mercado y 1 capacidad = bloques diferidos MK y CN; 2 térmica aparte
jobs = {"analyze": "analyze", "SC": "lazy:SC", "MK": "lazy:MK", "CN": "lazy:CN", "TH": "lazy:TH", "c2": "calls:2"}
for k in range(0, len(calls), 3):
    jobs["c%d" % calls[k]] = "calls:" + ",".join(str(c) for c in calls[k:k + 3])
with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
    res = dict(zip(jobs, ex.map(node, jobs.values())))
pj = json.loads(res["analyze"])
lazy = {k: json.loads(res[k]) for k in ("SC", "MK", "CN", "TH")}
memo = {}
for k, v in res.items():
    if k.startswith("c"):
        memo.update(json.loads(v))
keys = json.loads(subprocess.run(["node", "-e", 'const B=require("./packages/web/planos_export_bx.js"),BX=require("./packages/core/tt300bx.js");const P=Object.assign(BX.defaults(),{opt_uhmw:1,opt_ss:0,opt_bz:0});console.log(JSON.stringify(B.exportCalls(Object.assign(BX.defaults(),P)).map(c=>c.key)))'], cwd=str(root), check=True, capture_output=True, text=True).stdout)
memo[keys[0]] = lazy["MK"]
memo[keys[1]] = lazy["CN"]
assert set(memo) == set(keys), "memoria del JSON de diseño incompleta"
dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
s = s.replace("@@PRE_ATTR@@", 'data-key="%s" data-fecha="%s"' % (html.escape(json.dumps(pj["key"]), quote=True), html.escape(pj["fecha"], quote=True)))
s = s.replace("/*@@PRE@@*/", dump(pj["r"]))
s = s.replace("/*@@PRE_LZ@@*/", dump(lazy))
s = s.replace("/*@@PRE_MEMO@@*/", dump(memo))
try:
    rev = subprocess.run(["git", "log", "-1", "--format=%h", "--", "packages/core"], cwd=str(root), capture_output=True, text=True).stdout.strip()
except Exception:
    rev = ""
s = s.replace("@@CORE_REV@@", rev or "")
s = s.replace("@@VERSION@@", BX_VERSION)
out = root / ("Tornamesa_BX_v%s.html" % BX_VERSION)
out.write_text(s, encoding="utf-8")
print(out, len(s.encode("utf-8")), "bytes")
