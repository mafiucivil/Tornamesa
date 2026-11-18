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
    d.saveas(dst)


if __name__ == "__main__":
    a, b = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    b.mkdir(parents=True, exist_ok=True)
    fs = sorted(a.glob("*.dxf"))
    for f in fs:
        colorear(f, b / f.name)
    print(f"{len(fs)} láminas DXF coloreadas en {b}")
