"""Copia las láminas DXF de un paquete de planos con color ACI por capa y fuente Arial (el generador dibuja todo en color 7 con Liberation Sans).
Uso: python3 tools/planos_color.py <carpeta con *.dxf> <carpeta de salida>
No cambia geometría, capas, tipos de línea ni grosores: solo el color de cada capa (las entidades usan PORCAPA).
El texto queda en color 7 (negro sobre fondo blanco, blanco sobre fondo negro) para que siempre se lea."""
import sys, pathlib, ezdxf

COLOR = {                 # capa: (ACI, descripción)
    "VIS": (4, "contorno visible: cian"),
    "FINA": (8, "líneas finas: gris"),
    "OCU": (5, "ocultas: azul"),
    "EJE": (1, "ejes: rojo"),
    "COTA": (3, "cotas: verde"),
    "TXT": (7, "textos: negro/blanco"),
    "ACH": (9, "achurado: gris claro"),
    "MARCO": (7, "marco y cajetín: negro/blanco"),
    "FANT": (6, "fantasma (piezas vecinas): magenta"),
    "TRAT": (30, "tratamientos: naranjo"),
    "CORTE": (1, "líneas de corte: rojo"),
}


# Fuente: el generador dimensiona los textos con Liberation Sans (métricamente idéntica a Arial: mismos anchos de carácter).
# En Windows/AutoCAD Liberation Sans no existe y se sustituye por una fuente más ancha (los textos salían de las casillas):
# se declara Arial (arial.ttf / arialbd.ttf) con el nombre de familia en el XDATA ACAD, como lo guarda AutoCAD.
FUENTE = {"LiberationSans-Regular.ttf": ("arial.ttf", False), "LiberationSans-Bold.ttf": ("arialbd.ttf", True), "txt": ("arial.ttf", False)}


def colorear(src: pathlib.Path, dst: pathlib.Path):
    d = ezdxf.readfile(src)
    for lay in d.layers:
        if lay.dxf.name in COLOR:
            lay.dxf.color = COLOR[lay.dxf.name][0]
    for st in d.styles:
        f = st.dxf.get("font", "")
        if f in FUENTE:
            ttf, bold = FUENTE[f]
            st.dxf.font = ttf
            st.set_extended_font_data("Arial", italic=False, bold=bold)
    # Arial no trae el signo menos superíndice (U+207B): «×10⁻⁶» se escribe «×10^-6»
    for e in d.modelspace().query("TEXT MTEXT"):
        t = e.dxf.text if e.dxftype() == "TEXT" else e.text
        if "⁻" in t:
            t = t.replace("10⁻⁶", "10^-6").replace("⁻", "-")
            if e.dxftype() == "TEXT":
                e.dxf.text = t
            else:
                e.text = t
    estilos = {s.dxf.name: s for s in d.styles}
    for blk in [d.modelspace()] + [b for b in d.blocks if not b.name.startswith("*")]:
        for e in blk.query("TEXT"):
            a_izquierda(e, estilos)
    d.saveas(dst)


# Posición explícita de los textos: el generador guarda los textos centrados, a la derecha, al medio o arriba con el punto de
# inserción igual al de alineación y deja que el programa CAD lo recalcule al abrir. ODA File Converter no lo recalcula al escribir
# el DWG (no tiene la fuente) y AutoCAD muestra el DWG con el punto guardado: todos esos textos quedaban corridos.
# Aquí cada texto pasa a alineación izquierda-línea base, con el punto que deja su caja exactamente donde la ubica el cálculo de
# alineación de ezdxf (que reproduce el de AutoCAD), usando Arial con las métricas de Liberation Sans (mismos anchos).
import os, tempfile, shutil, math
_LIB = "/usr/share/fonts/truetype/liberation/"
_FD = tempfile.mkdtemp(prefix="fuentes_arial_")
shutil.copy(_LIB + "LiberationSans-Regular.ttf", os.path.join(_FD, "arial.ttf"))
shutil.copy(_LIB + "LiberationSans-Bold.ttf", os.path.join(_FD, "arialbd.ttf"))
ezdxf.options.support_dirs = [_FD]
from ezdxf.fonts import fonts as _fonts
_fonts.font_manager.clear(); _fonts.font_manager.build([_FD])
from ezdxf import bbox as _bbox


def a_izquierda(e, estilos):
    ha, va = e.dxf.get("halign", 0), e.dxf.get("valign", 0)
    if (ha == 0 and va == 0) or ha in (3, 5):    # ya a la izquierda-base, o ALIGNED/FIT (el generador no los usa)
        return
    ref = _bbox.extents([e], fast=False)          # caja del texto alineado (ezdxf calcula la posición como AutoCAD)
    if not ref.has_data:
        return
    p = e.dxf.align_point if e.dxf.hasattr("align_point") else e.dxf.insert
    e.dxf.halign = 0; e.dxf.valign = 0
    if e.dxf.hasattr("align_point"):
        e.dxf.discard("align_point")
    e.dxf.insert = (p.x, p.y, 0.0)
    cur = _bbox.extents([e], fast=False)
    r = math.radians(e.dxf.get("rotation", 0.0))
    if abs(math.sin(r)) < 1e-9 or abs(math.cos(r)) < 1e-9:   # horizontal o vertical: la caja ejes-alineados basta
        dx, dy = ref.extmin.x - cur.extmin.x, ref.extmin.y - cur.extmin.y
    else:                                                     # inclinado: centro de la caja
        dx, dy = ref.center.x - cur.center.x, ref.center.y - cur.center.y
    e.dxf.insert = (p.x + dx, p.y + dy, 0.0)


if __name__ == "__main__":
    a, b = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    b.mkdir(parents=True, exist_ok=True)
    fs = sorted(a.glob("*.dxf"))
    for f in fs:
        colorear(f, b / f.name)
    print(f"{len(fs)} láminas DXF coloreadas en {b}")
