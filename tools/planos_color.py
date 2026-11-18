"""Copia las láminas DXF de un paquete de planos asignando un color ACI por capa (el generador dibuja todo en color 7).
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


def colorear(src: pathlib.Path, dst: pathlib.Path):
    d = ezdxf.readfile(src)
    for lay in d.layers:
        if lay.dxf.name in COLOR:
            lay.dxf.color = COLOR[lay.dxf.name][0]
    d.saveas(dst)


if __name__ == "__main__":
    a, b = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    b.mkdir(parents=True, exist_ok=True)
    fs = sorted(a.glob("*.dxf"))
    for f in fs:
        colorear(f, b / f.name)
    print(f"{len(fs)} láminas DXF coloreadas en {b}")
