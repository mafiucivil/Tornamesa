"""Arma la herramienta principal Tornamesa_v<versión>.html en la raíz del repositorio (un solo archivo, sin dependencias externas).
La versión sale del archivo VERSION; al subirla se elimina el archivo de la versión anterior (queda en el historial de git).
Incrusta además el índice compacto de los juegos de planos pre-generados de entregables/RevC (raíz = caso Base, variantes/*):
por juego, id, carpeta, parámetros P completos, PDF por grupo y láminas (código, título, grupo). Los PDF no se incrustan."""
import json
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "tools"))
import indice_planos as IP  # noqa: E402


def indice_juegos():
    """Índice compacto de los juegos pre-generados (rutas relativas a la raíz del repositorio, con '/')."""
    gids = [g[0] for g in IP.GRUPOS]
    juegos, avisos = [], []
    for d in IP.juegos_entregados():
        idx = IP.indice(d)
        jid = "0" if d == IP.ENTREGA else d.name
        P = json.loads((d / "TT300-C_design.json").read_text(encoding="utf-8"))["P"]
        disco = d / "indice_planos.json"
        prev = json.loads(disco.read_text(encoding="utf-8")) if disco.exists() else None
        if prev is None or [l["codigo"] for l in prev["laminas"]] != [l["codigo"] for l in idx["laminas"]] or prev["grupos"] != idx["grupos"]:
            avisos.append(f"{idx['carpeta']}: indice_planos.json falta o no coincide con informe_paquete.md")
        pdf = {}
        for g in gids:
            f = d / idx["grupos"][g]["pdf"]
            ok = f.exists() and f.stat().st_mtime >= (d / "informe_paquete.md").stat().st_mtime - 1
            if not ok:
                avisos.append(f"{idx['carpeta']}: {f.name} falta o es anterior al informe")
            pdf[g] = idx["grupos"][g]["pdf"] if ok else None
        juegos.append({
            "id": jid, "carpeta": idx["carpeta"], "interfaz": idx["interfaz"], "madera": idx["madera"], "P": P, "pdf": pdf,
            "archivos": {k: v for k, v in idx["archivos"].items() if v and k in ("combinado", "despiece_xlsx", "despiece_csv", "step", "dxf_zip", "informe")},
            "laminas": [[l["codigo"], l["titulo"], gids.index(l["grupo"]), 1 if l["pdf"] else 0, 1 if l["dxf"] else 0] for l in idx["laminas"]],
        })
    for a in avisos:
        print("AVISO:", a, "→ ejecute python3 tools/indice_planos.py", file=sys.stderr)
    return {"rev": "C", "advertencia": IP.ADVERTENCIA, "grupos": [[g[0], g[1]] for g in IP.GRUPOS], "juegos": juegos}


pk = root / "packages"
s = (pk / "web" / "shell.html").read_text(encoding="utf-8")
for tag, f in [("FEA", pk / "core" / "fea.js"), ("CORE", pk / "core" / "tt300c.js"), ("AGENTS", pk / "agents" / "agentes.js"), ("PLANOS", pk / "web" / "planos_export.js"), ("UI", pk / "web" / "ui.js")]:
    code = f.read_text(encoding="utf-8").replace('if (typeof module !== "undefined") module.exports', "if (false) module.exports")
    s = s.replace("/*@@%s@@*/" % tag, code)
idxj = json.dumps(indice_juegos(), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
s = s.replace("/*@@PLANOS_IDX@@*/", "const PLANOS_IDX = " + idxj + ";")
ver = (root / "VERSION").read_text(encoding="utf-8").strip()
s = s.replace("@@VERSION@@", ver)
out = root / ("Tornamesa_v%s.html" % ver)
for old in root.glob("Tornamesa_v*.html"):
    if old != out:
        old.unlink()
out.write_text(s, encoding="utf-8")
print(out, len(s.encode("utf-8")), "bytes")
