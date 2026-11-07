"""Índice de un juego de planos TT300-C y PDF por grupo (Generales · Fabricación · Armado).

Uso:
    python3 tools/indice_planos.py                 # todos los juegos de entregables/RevC (raíz y variantes/*)
    python3 tools/indice_planos.py CARPETA [...]   # solo esas carpetas (p. ej. salidas/2026-11-07_1530_base)
    python3 tools/indice_planos.py --sin-pdf ...   # solo indice_planos.json (no une PDF)

Para cada carpeta de juego (la que contiene informe_paquete.md, TT300-C_design.json y planos/TT300C-XXX-NNN-C.pdf):
  · lee la tabla «| n | código | título | escala |» de la sección «## Láminas» de informe_paquete.md;
  · clasifica cada lámina por su título (no por número fijo, para admitir láminas nuevas):
      Armado      → el título contiene EXPLOSIONADA, MONTAJE, SECUENCIA o ARMADO;
      Generales   → GEN-*, CON-001, CON-002, CON-003 o el título contiene DESPIECE COMPLETO o CONJUNTO GENERAL;
      Fabricación → el resto (subconjuntos soldados, interfaz, BAS, MES, PIV, ACC, IZA, INT, MAD…);
  · une las láminas individuales en el orden del informe en TT300-C_Planos_{Generales,Fabricacion,Armado}_Rev<R>.pdf (pypdf);
  · escribe indice_planos.json con la lista de láminas por grupo, la ruta y el título.
La función indice(carpeta) devuelve el mismo diccionario sin escribir nada (la usa tools/build_tt300c.py)."""
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENTREGA = ROOT / "entregables" / "RevC"
ADVERTENCIA = "ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO."
GRUPOS = [("generales", "Generales", "Generales"), ("fabricacion", "Fabricación", "Fabricacion"), ("armado", "Armado", "Armado")]
_ARMADO = ("EXPLOSIONADA", "MONTAJE", "SECUENCIA", "ARMADO")
_GENERALES_TIT = ("DESPIECE COMPLETO", "CONJUNTO GENERAL")
_GENERALES_COD = ("CON-001", "CON-002", "CON-003")


def _sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").upper()


def clasificar(codigo, titulo):
    """Grupo de una lámina: 'armado', 'generales' o 'fabricacion' (por título; el código solo para GEN-* y CON-001…003)."""
    t = _sin_tildes(titulo)
    if any(k in t for k in _ARMADO):
        return "armado"
    corto = re.sub(r"^TT300C-|-[A-Z]$", "", codigo.strip())
    if corto.startswith("GEN-") or corto in _GENERALES_COD or any(k in t for k in _GENERALES_TIT):
        return "generales"
    return "fabricacion"


def leer_laminas(informe):
    """Filas de la tabla de la sección «## Láminas» del informe: [(n, código, título, escala)]."""
    filas, dentro = [], False
    for ln in pathlib.Path(informe).read_text(encoding="utf-8").splitlines():
        if ln.startswith("## "):
            dentro = ln.startswith("## Láminas")
            continue
        if not dentro:
            continue
        m = re.match(r"^\|\s*(\d+)\s*\|\s*(TT300C-[A-Z0-9]+-\d+-[A-Z])\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", ln)
        if m:
            filas.append((int(m.group(1)), m.group(2), m.group(3), m.group(4)))
    return filas


def _rev(carpeta):
    pdfs = sorted(carpeta.glob("TT300-C_Planos_Rev*.pdf"))
    m = re.search(r"_Rev([A-Z])\.pdf$", pdfs[0].name) if pdfs else None
    return m.group(1) if m else "C"


def _existe(carpeta, nombre):
    return nombre if (carpeta / nombre).exists() else None


def _descripcion(informe):
    """Interfaz dibujada y cubierta, tal como las rotula el informe del paquete."""
    txt = pathlib.Path(informe).read_text(encoding="utf-8")
    m = re.search(r"Interfaz dibujada:\s*\*\*(.+?)\*\*(.*)", txt)
    interfaz = (m.group(1) + m.group(2)).strip() if m else ""
    m2 = re.search(r"Cubierta de madera:\s*(sí|no)", txt)
    return interfaz, (m2.group(1) == "sí") if m2 else False


def indice(carpeta):
    """Índice del juego en `carpeta` (rutas relativas a la carpeta, con '/')."""
    carpeta = pathlib.Path(carpeta).resolve()
    inf = carpeta / "informe_paquete.md"
    if not inf.exists():
        raise FileNotFoundError(f"{carpeta}: falta informe_paquete.md")
    rev = _rev(carpeta)
    laminas = []
    for n, cod, tit, esc in leer_laminas(inf):
        g = clasificar(cod, tit)
        pdf, dxf = f"planos/{cod}.pdf", f"planos/{cod}.dxf"
        laminas.append({"n": n, "codigo": cod, "titulo": tit, "escala": esc, "grupo": g,
                        "pdf": pdf if (carpeta / pdf).exists() else None, "dxf": _existe(carpeta, dxf)})
    if not laminas:
        raise ValueError(f"{inf}: no se encontró la tabla de láminas")
    faltan = [l["codigo"] for l in laminas if not l["pdf"]]
    grupos = {}
    for gid, titulo, archivo in GRUPOS:
        grupos[gid] = {"titulo": titulo, "pdf": f"TT300-C_Planos_{archivo}_Rev{rev}.pdf",
                       "laminas": [l["codigo"] for l in laminas if l["grupo"] == gid]}
    interfaz, madera = _descripcion(inf)
    try:
        rel = carpeta.relative_to(ROOT).as_posix()
    except ValueError:
        rel = carpeta.as_posix()
    return {
        "proyecto": "TT300-C", "rev": rev, "carpeta": rel, "interfaz": interfaz, "madera": madera, "advertencia": ADVERTENCIA,
        "grupos": grupos, "laminas": laminas, "faltan_pdf": faltan,
        "archivos": {"combinado": _existe(carpeta, f"TT300-C_Planos_Rev{rev}.pdf"), "despiece_xlsx": _existe(carpeta, "TT300-C_despiece.xlsx"),
                     "despiece_csv": _existe(carpeta, "TT300-C_despiece.csv"), "step": _existe(carpeta, "TT300-C.step"),
                     "dxf_zip": _existe(carpeta, f"TT300-C_DXF_Rev{rev}.zip"), "informe": _existe(carpeta, "informe_paquete.md"),
                     "design": _existe(carpeta, "TT300-C_design.json")},
    }


def _pypdf():
    try:
        import pypdf
    except ImportError:
        import subprocess
        print("pypdf no está instalado: se instala con pip ...", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf"])
        import pypdf
    return pypdf


def unir_pdf(carpeta, idx):
    """Une las láminas de cada grupo (orden del informe) con un marcador por lámina."""
    pypdf = _pypdf()
    carpeta = pathlib.Path(carpeta)
    por_cod = {l["codigo"]: l for l in idx["laminas"]}
    hechos = []
    for gid, g in idx["grupos"].items():
        dest = carpeta / g["pdf"]
        w = pypdf.PdfWriter()
        for cod in g["laminas"]:
            l = por_cod[cod]
            if not l["pdf"]:
                continue
            w.append(str(carpeta / l["pdf"]), outline_item=f"{cod.replace('TT300C-', '')} · {l['titulo']}"[:90])
        w.add_metadata({"/Title": f"TT300-C · Planos {g['titulo']} · Rev. {idx['rev']}", "/Subject": ADVERTENCIA})
        tmp = dest.with_suffix(".pdf.tmp")
        with open(tmp, "wb") as fh:
            w.write(fh)
        tmp.replace(dest)
        hechos.append((dest.name, len(g["laminas"]), dest.stat().st_size))
    return hechos


def procesar(carpeta, con_pdf=True):
    carpeta = pathlib.Path(carpeta).resolve()
    idx = indice(carpeta)
    if con_pdf:
        for nombre, n, sz in unir_pdf(carpeta, idx):
            print(f"  {nombre}: {n} láminas, {sz / 1e6:.1f} MB", flush=True)
    (carpeta / "indice_planos.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    cuenta = {g: len(v["laminas"]) for g, v in idx["grupos"].items()}
    print(f"{idx['carpeta']}: {len(idx['laminas'])} láminas {cuenta}" + (f"; FALTAN PDF: {idx['faltan_pdf']}" if idx["faltan_pdf"] else ""), flush=True)
    return idx


def juegos_entregados():
    """Carpetas de los juegos pre-generados: la raíz de entregables/RevC (caso Base) y variantes/* (orden alfabético)."""
    out = [ENTREGA] if (ENTREGA / "informe_paquete.md").exists() else []
    var = ENTREGA / "variantes"
    if var.exists():
        out += sorted(d for d in var.iterdir() if (d / "informe_paquete.md").exists())
    return out


def main(argv):
    con_pdf = "--sin-pdf" not in argv
    dirs = [a for a in argv if not a.startswith("--")]
    carpetas = [pathlib.Path(d) for d in dirs] or juegos_entregados()
    if not carpetas:
        sys.exit("No hay juegos de planos que indexar.")
    for c in carpetas:
        procesar(c, con_pdf)


if __name__ == "__main__":
    main(sys.argv[1:])
