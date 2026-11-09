"""Utilidades para armar láminas: regiones, ficha de pieza, notas, bloques GD&T y cotas repetidas."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hojas_base import *
from layout import Plano, VS
import autodim


def split(rect, nx=1, ny=1, i=0, j=0, gap=6.0):
    """Subcelda (i,j) de la rejilla nx×ny dentro del rectángulo (i: columna desde la izquierda; j: fila desde arriba)."""
    x0, y0, x1, y1 = rect
    cw, ch = (x1 - x0) / nx, (y1 - y0) / ny
    return (x0 + i * cw + gap / 2, y1 - (j + 1) * ch + gap / 2, x0 + (i + 1) * cw - gap / 2, y1 - j * ch - gap / 2)


def vspan(rect, f0, f1):
    """Franja vertical del rectángulo entre las fracciones f0 y f1 (0 = arriba)."""
    x0, y0, x1, y1 = rect
    H = y1 - y0
    return (x0, y1 - f1 * H, x1, y1 - f0 * H)


def hspan(rect, f0, f1):
    x0, y0, x1, y1 = rect
    Wd = x1 - x0
    return (x0 + f0 * Wd, y0, x0 + f1 * Wd, y1)


class Pieza(Plano):
    """Lámina de fabricación de una pieza (o grupo de piezas iguales). Las vistas se declaran con p.vs(...) y se componen en build()."""

    def __init__(self, ctx, keys, titulo, fmt="A2", mat_override=None, grupo="", code=None):
        self.keys = [k for k in keys if ctx.m.get(k)]
        self.p0 = ctx.m.get(self.keys[0])
        self.lead = self.p0.code_lamina
        masa = " + ".join(f"{f(ctx.m.get(k).mass_unit, 1)}" for k in self.keys[:3]) + " kg c/u"
        h = Hoja(ctx, code or self.lead, titulo, "", fmt=("A1" if fmt in ("auto", "auto3") else fmt), material=mat_override or self.p0.material, masa=(masa if len(masa) <= 30 else "ver ficha (kg c/u)") if len(self.keys) > 1 else f"{f(self.p0.mass_unit, 1)} kg c/u",
                 trat=self.p0.tratamiento if self.p0.tratamiento != "—" else "Ninguno (ver notas)", serie="FAB", items=[ctx.m.get(k).code for k in self.keys], grupo=grupo)
        # el cajetín admite 3 renglones de material y de tratamiento: si no caben, remite a la ficha/notas (el texto completo va en la ficha de la pieza)
        if len(wrapw(str(h.material), 94, 3.0)) > 3:
            h.material = "Ver la ficha de la pieza (despiece)"
        if len(wrapw(str(h.trat), 36, 3.0)) > 3:
            h.trat = "Ver ficha y notas"
        self.init_plano(ctx, h)
        self.boost_main = True          # vista principal a la escala normalizada siguiente si cabe (ver layout._build_once)
        self.iso_keys = list(self.keys)
        self.fmt_try = ["A2", "A1"] if fmt == "auto" else (["A3", "A2", "A1"] if fmt == "auto3" else None)
        self.W_right = 172.0

    def tables(self, weld_ids=None, extra_rows=None, ficha_h=None, ficha=True):
        """Ficha (despiece de la pieza) y tabla de soldaduras: bloques anchos de la franja inferior. ficha=False en las láminas de características (la pieza se define en su lámina, H-32)."""
        if ficha:
            self.ficha_block(self.keys)
        if weld_ids:
            self.weld_block(weld_ids)

    def notes(self, specific, gd=(), inspect=None, y_top=None):
        """Notas: fabricación específica + generales + inspección (bloques de la banda lateral)."""
        ctx = self.ctx
        if any(k in ("int_bronce", "int_tapones") for k in self.keys):
            # H-02: el patrón de tapones del bronce no cumple la fracción mínima de lubricación del cálculo; lámina retenida hasta los datos del proveedor
            T = ctx.g.IG.get("tapones") or {}
            n0 = len(self.blocks)
            self.note_block("RETENIDA — A DEFINIR (DATOS DEL PROVEEDOR)", [
                "Esta lámina queda RETENIDA: la placa de bronce con tapones de grafito se define con los datos del proveedor (patrón, Ø, paso y profundidad de los tapones, "
                f"fracción de grafito). Con el patrón del cálculo la fracción real es {fm(T.get('fg_real', 0), 3)} (mínimo de lubricación {fm(T.get('fg_min', 0.2), 2)}): "
                + ("NO cumple. " if not T.get("cumple_lubricacion", True) else "") + "No fabricar ni comprar hasta su definición y aprobación."])
            self.blocks.insert(0, self.blocks.pop(n0))
        self.note_block("NOTAS DE FABRICACIÓN", list(specific), numbered=True)
        if gd:
            self.gd(list(gd))
        self.rugosidad_block()
        # notas generales: solo la referencia a GEN-001 (no se repiten en la lámina); inspección propia solo si la pieza la tiene
        self.note_block(REF_GEN_TIT, [REF_GEN])
        if inspect:
            self.note_block("PLAN DE INSPECCIÓN DE LA PIEZA", [inspect])

    def rugosidad_block(self):
        """Bloque de rugosidad ISO 1302 por cara funcional de la pieza (valores ya usados en las vistas) y general para el resto."""
        g, P = self.ctx.g, self.ctx.P
        k = self.keys[0]
        RA = {
            "base_plancha": [("Ra 3,2", f"cara de apoyo de la interfaz (zona Ø{f(P['D_top'] + 20)}), planeada"), ("Ra 1,6", f"agujero Ø{f(P['D_piv'])} H7")],
            "collar": [("Ra 6,3", "cara superior torneada (frente al cubo, sin contacto)"), ("Ra 1,6", f"agujero Ø{f(P['D_piv'])} H7")],
            "bancada": [("Ra 1,6", "flancos y fondo de la ranura T")], "patin": [("Ra 1,6", "cuello y cabeza de la lengüeta, alojamientos, ojal H9")],
            "una": [("Ra 0,8", "cara de empuje templada (rectificada)"), ("Ra 1,6", "caras de guía en el alojamiento")], "pasadores": [("Ra 0,8", f"Ø{f(g.d_pin)} m6 (franja templada y resto)")],
            "pivote": [("Ra 0,8", f"Ø{f(P['D_piv'])} p6 (zona de calado) y Ø{f(P['D_piv'])} f7 (zona del buje)"), ("Ra 3,2", "caras extremas")], "buje": [("Ra 1,6", "Ø interior F7 y Ø exterior s6")],
            "pasador_vastago": [("Ra 0,8", f"Ø{f(P['d_pp'])} f8")], "mesa_anillo_sup": [("Ra 3,2", "agujeros de pasadores H7 y caras del anillo")],
            "mesa_plancha_sup": [("Ra 6,3", "cara superior y rebaje de la tapa")], "mesa_plancha_inf": [("Ra 3,2", "cara inferior (apoyo de la interfaz), planeada")],
            "mesa_cubo": [("Ra 1,6", f"agujero Ø{f(g.d_bush)} H7"), ("Ra 3,2", "rebaje y caras de apoyo")], "orejas": [("Ra 6,3", "agujero H12 mecanizado (taladro y mandrinado)"), ("Ra 12,5", "cantos de corte térmico (perfil)")],
            "mensula_mejilla": [("Ra 6,3", "caras de apoyo de las orejas"), ("Ra 3,2", f"agujeros Ø{f(P['d_pp'])} H9 de las orejas")],
            "int_disco_base": [("Ra 0,4", "cara deslizante (lapeada)")], "int_disco_mesa": [("Ra 0,4", "cara deslizante (lapeada)")] + ([("Ra 1,6", "fondo de ranuras")] if g.opt == 1 and g.h_gr > 0 else []),
            "int_cara": [("Ra 0,4", "cara deslizante (lapeada)")], "int_bronce": [("Ra 0,4", "cara deslizante (lapeada)"), ("Ra 1,6", "fondo de ranuras y alojamientos de tapones")],
            "int_uhmw": [("Ra 3,2", "caras de la lámina (sin mecanizado de precisión)")],
        }
        RA.update({"tapa_ret": [("Ra 3,2", "cara de apoyo y avellanados")], "tapa_insp": [("Ra 3,2", "cara de apoyo y avellanados")],
                   "bloque_una": [("Ra 0,8", "cara de empuje templada (rectificada)"), ("Ra 1,6", "agujero del pasador Q H9 y caras de la horquilla")],
                   "pasador_E": [("Ra 0,8", "Ø f8 de los pasadores E y Q")], "cajon_pared": [("Ra 1,6", "agujeros H9 de las tapas (mandrinados)"), ("Ra 12,5", "cantos de corte térmico")],
                   "placa_leva": [("Ra 1,6", "canto guía fresado y templado (ver nota 3)")], "cilindro_pv": [("Ra 1,6", "ojales H9 (proveedor)")],
                   "leva_riel": [("Ra 1,6", "canto de leva fresado y templado")], "leva_rodillo": [("Ra 0,8", "diámetro exterior del rodillo y del perno")], "leva_pata": [("Ra 6,3", "caras de apoyo fresadas")],
                   "pernos_pasador": [("Ra 1,6", "caras de la arandela (rectificadas)")], "arandela_pasador": [("Ra 1,6", "caras de la arandela (rectificadas)")], "marco_largo": [("Ra 12,5", "cantos de corte (a escuadra)")]})
        rows = RA.get(k, [("Ra 6,3", "bordes de las caras que se sueldan (preparación)")])
        rows = rows + [("Ra 12,5", "resto de las superficies (corte térmico o laminado)")]

        def d(s, x, y, w):
            s.text("RUGOSIDAD POR CARA FUNCIONAL (ISO 1302 / ISO 21920)", (x, y), T_N + 0.5, "TOP_LEFT", bold=True)
            yy = y - (T_N + 0.5) * 1.7 - 5.0
            for ra_, txt in rows:
                s.roughness((x + 5, yy - 15.0), ra_)
                for i, l_ in enumerate(wrapw(txt, w - 40 - tw(ra_, T_N), T_N)):
                    s.text(l_, (x + 14 + tw(ra_, T_N) + 12, yy - 8.0 - i * T_N * 1.4), T_N, "MIDDLE_LEFT")
                yy -= 17.0
            return yy
        self.block("rugosidad", d, name="rugosidad")

    def finish_scale(self):
        self.build()


def gd_column(s, x, y, items, step=14.0):
    """Columna de recuadros GD&T con su leyenda; items = [(sym, tol, datum, texto)]; devuelve y final."""
    for sym, tol, datum, txt in items:
        if not hasattr(s, "views"):
            s.views = []
        s.views.append((x, y - 7 - 6, x + 14 + 7 + tw(txt, T_N) + 3, y))
        wd = s.gdt((x, y - 7), sym, tol, datum)
        s.text(txt, (x + wd + 3, y - 3.5), T_N, "MIDDLE_LEFT")
        y -= step
    return y


def thread_txt(d, pitch=None, L=None):
    return f"M{fm(d, 0)}" + (f"×{fm(pitch, 2)}" if pitch else "") + (f" prof. {fm(L, 0)}" if L else "")


def diam_dims(V, c3, rs, ang=35, keys=None, texts=None, ext=12.0, step=7.0):
    """Cotas de varios diámetros concéntricos (lista de radios) con llamadas apiladas."""
    for i, r in enumerate(rs):
        V.dim_dia(c3, r, ang + i * 24, text=(texts[i] if texts else None), on=keys, ext=ext + step * i)
