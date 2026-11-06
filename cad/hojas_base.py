"""Marco común de las láminas: contexto, hoja con cajetín diferido, registro de soldaduras (ISO 2553), ajustes (ISO 286), inspección, tablas estándar."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cadquery as cq
import draw
from draw import Sheet, wrap, wrapw, tw, T_N, T_S, T_T, T_MIN
from geom import *
import vistas
import iso286
from vistas import View, COTAS

REV = "C"
import geom
geom.REV = REV


def circ(c, r, n=96, a0=0.0, a1=360.0):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def polar(r, deg):
    return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))


def fillet_min(t):
    """Tamaño mínimo de filete (mm) según la parte más gruesa — AWS D1.1 Tabla 5.8: ≤6,4: 3; ≤12,7: 5; ≤19: 6; >19: 8."""
    return 3 if t <= 6.4 else 5 if t <= 12.7 else 6 if t <= 19 else 8


def mat_class(p):
    """Clase de achurado ISO 128-50 según el material de la pieza."""
    s = (p.material + " " + p.name).lower()
    if "uhmw" in s:
        return "plastico"
    if "madera" in s:
        return "madera"
    if "grafito" in s and "bronce" not in s:
        return "grafito"
    if "bronce" in s or "cuAl" in s.lower() or "cu" in s and "autolub" in s:
        return "bronce"
    if "inox" in s or "17-4" in s or "a240" in s:
        return "inox"
    return "acero"


class Ctx:
    def __init__(self, m):
        self.m, self.g, self.D, self.P = m, m.g, m.D, m.g.P
        self.sup = supuestos(m.g)
        self.DV = m.g.DV
        self.M = m.g.M
        self.shapes = {p.key: cq.Compound.makeCompound(list(p.solid.vals())) for p in m.parts}
        COTAS.set_shapes(self.shapes)
        self.hojas = []
        self.group_of = {}          # clave de pieza -> código de la pieza líder del plano
        self.balloons = {}          # plano -> set(pos)
        self.welds = []
        self.mat = {p.key: mat_class(p) for p in m.parts}
        g = self.g
        self.revs = [
            ("C", g.FECHA, "EMITIDO PARA REVISIÓN. Juego de planos de fabricación rehecho: conjunto, subconjuntos, piezas, soldaduras ISO 2553, ajustes ISO 286, inspección y listas. "
             "Valores leídos del JSON de diseño del núcleo.", "A DEFINIR", "A DEFINIR", "A DEFINIR"),
            ("B", "—", "Emisión anterior (planos básicos), reemplazada por la rev. C.", "—", "—", "—"),
        ]

    # --------------- copias locales de piezas ---------------
    def local(self, key, newkey, near=None, r=1e9, shift=(0, 0, 0), rot=0.0):
        sol = [x for x in self.shapes[key].Solids() if near is None or math.dist((x.Center().x, x.Center().y, x.Center().z), near) < r]
        c = cq.Compound.makeCompound(sol).translate(cq.Vector(*shift))
        if rot:
            c = c.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), rot)
        self.shapes[newkey] = c
        self.mat[newkey] = self.mat.get(key, "acero")
        return newkey

    def local_ang(self, key, newkey, a_deg, span_deg):
        sol = []
        for x in self.shapes[key].Solids():
            c = x.Center()
            d = ((math.degrees(math.atan2(c.y, c.x)) - a_deg + 180) % 360) - 180
            if abs(d) < span_deg / 2:
                sol.append(x)
        c = cq.Compound.makeCompound(sol).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -a_deg) if sol else None
        if c is not None:
            self.shapes[newkey] = c
            self.mat[newkey] = self.mat.get(key, "acero")
        return newkey if sol else None

    def parts(self, *keys):
        return [self.m.get(k) for k in keys if self.m.get(k)]

    def sh(self, *keys):
        return {k: self.shapes[k] for k in keys if k in self.shapes}

    def mass_of(self, *keys):
        return sum(p.mass_total for p in self.parts(*keys))

    def code(self, key):
        return self.m.get(key).code

    def plano_of(self, key):
        p = self.m.get(key)
        lead = self.group_of.get(key)
        return lead if lead else ("CATÁLOGO: " + (p.catalogo or "A DEFINIR POR CATÁLOGO") if p.comercial else p.code)


class Hoja:
    def __init__(self, ctx, plano, titulo, escala, fmt="A1", material="Ver despiece", masa="—", trat="Ver notas", serie="FAB", items=(), grupo=""):
        self.ctx = ctx
        self.fmt = fmt
        self.s = Sheet(fmt)
        self.plano = plano if plano.startswith(CODE) else f"{CODE}-{plano}-{REV}"
        self.titulo, self.escala, self.material, self.masa, self.trat = titulo, escala, material, masa, trat
        self.serie, self.items, self.grupo = serie, list(items), grupo
        self.tag = self.plano.replace(CODE + "-", "")
        ctx.hojas.append(self)
        ctx.balloons[self.plano] = set()
        COTAS.sheet = self.plano
        self.R = self.s.regions(ctx.revs)
        self.welds_here = []

    def begin(self):
        COTAS.sheet = self.plano
        return self.s

    # ----- soldaduras -----
    def weld(self, jid, p, q, kind=None, other=None, all_round=None, field=False, extra_tail=(), sh=None, L=None, length=None, size=None, prep=None):
        """Símbolo ISO 2553 de la junta jid del registro (tamaños, proceso, WPS, END del registro; nada a mano)."""
        w = self.ctx.weld_by_id(jid)
        if w is None:
            return
        w["sheets"].add(self.plano)
        self.welds_here.append(jid)
        tail = [f"{jid} · {w['proceso']} · {w['nivel']}", f"{w['wps']}", w["end"].replace(" · ", " ")] + list(extra_tail)
        kd = kind or w["sym"]
        sz = size if size is not None else w["size_txt"]
        ln = length if length is not None else w.get("len_txt", "")
        pr = prep if prep is not None else w.get("prep_txt", "")
        ar = w["contorno"] if all_round is None else all_round
        self.s.weld(p, q, kd, sz, ln, other=other if other is not None else w.get("other"), all_round=ar, field=field, tail=tail, sh=sh, L=L, prep=pr)

    def balloon(self, pos, p, q):
        self.s.balloon(p, q, pos)
        self.ctx.balloons[self.plano].add(pos)

    def info(self, n, total):
        g = self.ctx.g
        return dict(proj="TT300-C · TORNAMESA HIDRÁULICA 300 tf", subproj=f"Interfaz: {g.interfaz_nombre}", titulo=self.titulo, plano=self.plano, lamina=f"{n} de {total}",
                    escala=self.escala, formato=f"{self.fmt} ({int(self.s.W)}×{int(self.s.H)})", material=self.material, masa=self.masa, trat=self.trat, rev=REV, fecha=g.FECHA, revs=self.ctx.revs,
                    aviso=ADVERTENCIA, estado="EMITIDO PARA REVISIÓN — NO APTO PARA FABRICACIÓN HASTA SU APROBACIÓN",
                    generales="Tolerancias generales ISO 2768-mK; soldadura ISO 2553 / ISO 5817; rugosidad ISO 1302; GD&T ISO 1101.")

    def finish(self, n, total):
        self.s.frame(self.info(n, total))
        return self.s

    def ocupacion(self):
        if not getattr(self.s, "views", None):
            return 0.0, 0.0
        """(área de vistas / área útil del marco, área de vistas / área de dibujo disponible)."""
        s = self.s
        vs = getattr(s, "views", [])
        # unión aproximada por rejilla de 4 mm
        cells = set()
        for (x0, y0, x1, y1) in vs:
            for i in range(int(x0 // 4), int(x1 // 4) + 1):
                for j in range(int(y0 // 4), int(y1 // 4) + 1):
                    cells.add((i, j))
        A = len(cells) * 16.0
        a = self.R["all"]
        tot = (a[2] - a[0]) * (a[3] - a[1])
        avail = (self.R["main"][2] - self.R["main"][0]) * (self.R["main"][3] - self.R["main"][1])
        return A / tot, A / avail


# ----------------------------------------------------------------------------------------------
# soldaduras: registro único (tabla, símbolos y programa salen de aquí)
# ----------------------------------------------------------------------------------------------
def passes(z=None, t=None, groove=False):
    if groove:
        return max(2, math.ceil(t / 4.0))
    return 1 if z <= 6 else 2 if z <= 8 else 3 if z <= 12 else max(4, math.ceil(z / 4.0))


def build_welds(ctx):
    P, g, m, D = ctx.P, ctx.g, ctx.m, ctx.D
    BR, KG = g.BR, g.KG
    tb = g.tb
    W_ = []
    PROC = "135"
    A5 = "ER70S-6 (AWS A5.18) / E7018 (AWS A5.1)"

    def add(desc, piezas, tipo, sym, z=None, t=None, prep="Sin preparación", prep_txt="", nivel="ISO 5817-B", end="VT 100 % · MT 100 %", wps=1, len_total=0.0, nota="", core=None,
            contorno=False, groove=False, aporte=A5, proc=PROC, other=None, len_txt="", modelada=True):
        j = dict(id=f"J{len(W_) + 1:02d}", desc=desc, piezas=piezas, tipo=tipo, sym=sym, prep=prep, prep_txt=prep_txt, nivel=nivel, end=end, len_total=len_total, nota=nota, contorno=contorno,
                 aporte=aporte, proceso=proc, other=other, len_txt=len_txt, sheets=set(), wps=f"WPS-{wps:02d} A DEFINIR POR EL FABRICANTE", modelada=modelada, groove=groove)
        if groove:
            j["t"] = t
            j["z"] = None
            j["a"] = None
            j["size_txt"] = f"s{fm(t, 0)}"
            j["garganta"] = f"CJP, penetración total t = {fm(t, 0)}"
            j["cateto"] = "—"
            j["pasadas"] = passes(t=t, groove=True)
            j["origen"] = "CJP (penetración completa); t de la parte más delgada"
        else:
            if core is not None:
                zz, org = float(core[0]), core[1]
            else:
                zz, org = float(fillet_min(t)), f"mínimo AWS D1.1 T5.8 por la parte más gruesa (t = {fm(t, 0)}), a confirmar"
            j["z"] = zz
            j["a"] = round(zz * 0.7071, 1)
            j["size_txt"] = f"z{fm(zz, 0)}"
            j["garganta"] = f"a = {fm(j['a'], 1)}"
            j["cateto"] = f"z = {fm(zz, 0)}"
            j["pasadas"] = passes(z=zz)
            j["origen"] = org
            j["t"] = t
        W_.append(j)
        return j

    def c(name):
        fr = g.fila(name)
        return f"{fm(fr['dem'], 0)}" if fr else "—"
    L_ch, Win, Wout, H_, Llug = P["L_ch"], BR["Win"], BR["Wout"], BR["H"], BR["Llug"]
    nb = int(P["n_br"])
    B = g.B
    # BAS
    add("Marco perimetral largo – plancha base", "BAS-003 / BAS-001", "Filete en T, ambos lados, continuo", "fillet", t=max(P["rim_t"], tb), len_total=2 * 2 * B, wps=1, end="VT 100 % · MT 10 %", nivel="ISO 5817-C",
        other=dict(kind="fillet", size=f"z{fillet_min(max(P['rim_t'], tb))}"), contorno=False, len_txt="")
    add("Marco corto – plancha base", "BAS-004 / BAS-001", "Filete en T, ambos lados, continuo", "fillet", t=max(P["rim_t"], tb), len_total=2 * 2 * (B - 2 * P["rim_t"]), wps=1, end="VT 100 % · MT 10 %", nivel="ISO 5817-C",
        other=dict(kind="fillet", size=f"z{fillet_min(max(P['rim_t'], tb))}"))
    add("Marco largo – marco corto (esquinas)", "BAS-003 / BAS-004", "Filete de esquina exterior, continuo (4 esquinas)", "fillet", t=P["rim_t"], len_total=4 * P["rim_h"], wps=1, end="VT 100 % · MT 10 %", nivel="ISO 5817-C")
    add("Mejillas de ménsula – plancha base", "BAS-005 / BAS-001", "Filete en T, ambos lados de cada mejilla", "fillet", core=(P["w_br"], f"w_br del núcleo; mín. AWS {c('Filete mínimo mejillas–base')}, máx. AISC J2.2b t_ch − 2 = {fm(P['t_ch'] - 2, 0)}"),
        t=P["t_ch"], len_total=2 * 2 * nb * L_ch, wps=2, end="VT 100 % · MT 100 %", other=dict(kind="fillet", size=f"z{fm(P['w_br'], 0)}"))
    add("Oreja superior – mejillas de ménsula", "BAS-006 / BAS-005", "Filete en T, 2 caras de la oreja contra cada mejilla", "fillet", t=P["t_ch"], len_total=nb * 2 * 2 * Llug, wps=2, end="VT 100 % · MT 100 %",
        other=dict(kind="fillet", size=f"z{fillet_min(P['t_ch'])}"))
    add("Oreja inferior (bloque) – mejillas de ménsula", "BAS-007 / BAS-005", "Filete en T, ambos lados, cara superior del bloque", "fillet", t=P["t_ch"], len_total=nb * 2 * Llug, wps=2, end="VT 100 % · MT 100 %",
        other=dict(kind="fillet", size=f"z{fillet_min(P['t_ch'])}"))
    add("Oreja inferior (bloque) – plancha base", "BAS-007 / BAS-001", "Filete perimetral del bloque", "fillet", t=P["t_ch"], len_total=nb * 2 * (Win + Llug), wps=2, end="VT 100 % · MT 100 %", contorno=True)
    add("Bancada – plancha base", "ACC-001 / BAS-001", "Filete en T, ambos lados, continuo, precalentar 65 °C", "fillet", core=(P["w_bed_f"], "w_bed_f del núcleo"), t=P["t_bed"], len_total=int(P["n_cyl"]) * 2 * 2 * KG["L_bed"], wps=3,
        end="VT 100 % · MT 100 %", other=dict(kind="fillet", size=f"z{fm(P['w_bed_f'], 0)}"))
    if g.boss:
        add("Collar del pivote – plancha base", "BAS-002 / BAS-001", "Filete perimetral continuo", "fillet", core=(g.w_collar, f"w_collar del núcleo; mín. AWS D1.1 T5.8 = {c('Collar: filete mínimo')}"), t=g.h_boss,
            len_total=math.pi * g.D_boss, wps=4, end="VT 100 % · MT 100 % · UT de la unión", contorno=True)
    add("Orejas de izaje – plancha base", "IZA-001 / BAS-001", "Filete en T, ambos lados, L = 2R; base biselada", "fillet", core=(P["w_ear"], f"w_ear del núcleo; mín. AWS D1.1 T5.8 = {c('Oreja: filete mínimo')}"), t=P["t_ear"],
        len_total=4 * 2 * 2 * P["R_ear"], wps=5, end="VT 100 % · MT 100 % · UT 100 %", other=dict(kind="fillet", size=f"z{fm(P['w_ear'], 0)}"))
    # MES
    tp = g.tpr
    add("Empalmes de los anillos de pasadores (4 × 90°, superior e inferior)", "MES-002 / MES-004", "A tope en V 60°, raíz 3, con respaldo", "V", t=tp, prep="V 60°, abertura de raíz 3 mm, cara de raíz 2 mm, respaldo de acero",
        prep_txt="60°", groove=True, len_total=2 * 4 * (g.Rt - g.prIn), wps=6, end="VT 100 % · UT 100 %")
    add("Plancha superior – anillo superior", "MES-001 / MES-002", "A tope circunferencial, transición de espesores 1:4", "V", t=g.tt, prep="V 60°, raíz 3 mm, respaldo; chaflán 1:4 en el lado de la plancha más gruesa",
        prep_txt="60°", groove=True, len_total=2 * math.pi * g.prIn, wps=6, end="VT 100 % · UT 100 %")
    add("Plancha inferior – anillo inferior", "MES-003 / MES-004", "A tope circunferencial, transición de espesores 1:4", "V", t=g.tbo, prep="V 60°, raíz 3 mm, respaldo; chaflán 1:4 en el lado de la plancha más gruesa",
        prep_txt="60°", groove=True, len_total=2 * math.pi * g.prIn, wps=6, end="VT 100 % · UT 100 %")
    rin = [r for r in D["almas"]]
    add("Almas anulares – planchas inferior y superior", "MES-005…007 / MES-001, 003", "Filete en T, ambos lados, continuo (4 líneas por alma)", "fillet", core=(P["w_web"], f"w_web del núcleo ({'supera el máx. AISC J2.2b t − 2: pendiente del calculista (GEN-009)' if P['w_web'] > P['t_web'] - 2 else 'mín. AWS D1.1 T5.8'})"),
        t=P["t_web"], len_total=sum(2 * 2 * 2 * math.pi * r for r in rin), wps=7, end="VT 100 % · MT 100 %", other=dict(kind="fillet", size=f"z{fm(P['w_web'], 0)}"))
    add("Nervios radiales – planchas y almas", "MES-008…010 / MES-001, 003, 005…007", "Filete en T, ambos lados, continuo", "fillet", core=(P["w_web"], "w_web del núcleo"), t=P["t_rib"],
        len_total=int(P["N_rib"]) * 2 * 2 * (P["R_rib"] - P["D_hub"] / 2) * 1.0 + int(P["N_rib"]) * 2 * hw_len(g), wps=7, end="VT 100 % · MT 100 %", other=dict(kind="fillet", size=f"z{fm(P['w_web'], 0)}"))
    add("Empalme de cada alma anular", "MES-005…007", "A tope en V 60° (1 por alma)", "V", t=P["t_web"], prep="V 60°, raíz 2 mm, con respaldo", prep_txt="60°", groove=True, len_total=len(rin) * g.hw, wps=6, end="VT 100 % · UT 100 %")
    add("Cubo – planchas inferior y superior", "MES-011 / MES-001, 003", "Bisel 45° con respaldo (penetración completa)", "bevel", t=min(g.tt, g.tbo), prep="Bisel 45°, raíz 2 mm, respaldo", prep_txt="45°", groove=True,
        len_total=2 * math.pi * P["D_hub"] / 2, wps=6, end="VT 100 % · UT 100 %")
    add("Cierre de la plancha superior (soldadura de ranura sobre almas y nervios)", "MES-001 / MES-005…010", "Ranura 22×80 c/250, relleno completo", "slot", t=g.tt, groove=True, prep="Ranura rectangular 22×80 pasante, relleno completo",
        prep_txt="", len_txt="80", nivel="ISO 5817-C", end="VT 100 % · MT 100 %", len_total=0.0, wps=7, modelada=False, nota="Ranuras no modeladas en 3D; ubicación y cantidad: A DEFINIR POR EL FABRICANTE")
    if g.opt and g.removable:
        tpb = g.tope("base")
        if tpb:
            wt = (P["w_tope"], f"w_tope del núcleo; w_mín = {fm(tpb['w_min'], 0)} (AWS D1.1 T5.8); cabe bajo a_inf = {fm(tpb['a_inf'], 0)}")
            nsec = g.n_sec if g.opt != 3 or g.conf != 3 else int(P["bz_npad"])
            add("Barras de tope – plancha base", "INT tope base / BAS-001", "2 filetes (frente y dorso de la barra), continuos", "fillet", core=wt, t=max(tb, P["b_tope"]), len_total=nsec * 2 * tpb["L"], wps=8,
                end="VT 100 % · MT 100 %", other=dict(kind="fillet", size=f"z{fm(P['w_tope'], 0)}"), nota="soldar antes del alivio y del rectificado de las caras")
            add("Barras de tope – plancha inferior de la mesa", "INT tope mesa / MES-003", "2 filetes (frente y dorso de la barra), continuos", "fillet", core=wt, t=max(g.tbo, P["b_tope"]), len_total=g.n_sec * 2 * (g.tope("mesa") or tpb)["L"], wps=8,
                end="VT 100 % · MT 100 %", other=dict(kind="fillet", size=f"z{fm(P['w_tope'], 0)}"))
        if g.opt == 2 and g.tope("uhmw"):
            add("Barras del rebaje UHMW – disco inoxidable de la base", "INT tope UHMW / INT disco base", "2 filetes, aporte inoxidable 309L, continuos", "fillet", core=(P["w_tope"], "w_tope del núcleo"), t=max(g.I["tss"], P["b_tope"]),
                len_total=g.n_seg * 2 * g.tope("uhmw")["L"], wps=9, end="VT 100 % · PT 100 %", aporte="ER309L (AWS A5.9)", proc="135 / 141", other=dict(kind="fillet", size=f"z{fm(P['w_tope'], 0)}"))
    if g.wood:
        add("Anillo de contención de la madera – plancha superior", "MAD anillo / MES-001", "Filete en T, ambos lados, continuo", "fillet", t=max(g.t_ring, g.tt), len_total=2 * math.pi * P["D_top"] / 2 * 2, wps=10, end="VT 100 % · MT 10 %",
            nivel="ISO 5817-C", other=dict(kind="fillet", size=f"z{fillet_min(max(g.t_ring, g.tt))}"))
    for w in W_:
        w["len_txt"] = w.get("len_txt", "")
    ctx.welds = W_
    return W_


def hw_len(g):
    return g.hw


def weld_by_id(self, jid):
    return next((w for w in self.welds if w["id"] == jid), None)


def weld_find(self, frag):
    return next((w for w in self.welds if frag in w["desc"]), None)


Ctx.weld_by_id = weld_by_id
Ctx.weld_find = weld_find


# ----------------------------------------------------------------------------------------------
# ajustes (ISO 286), inspección, notas
# ----------------------------------------------------------------------------------------------
def ajustes(ctx):
    """(descripción, medida nominal, agujero, eje, aplicación) — los límites se calculan con iso286."""
    P, g = ctx.P, ctx.g
    return [
        ("Pivote en plancha base y collar", P["D_piv"], "H7", "p6", "Aprieto: prensado o contracción (hielo seco); agujero mandrinado en línea"),
        ("Pivote en buje", P["D_piv"], "F7", "f7", "Con juego, lubricado (buje autolubricado)"),
        ("Buje en cubo de la mesa", g.d_bush, "H7", "s6", "Aprieto: prensado"),
        ("Pasador de empuje en anillos", g.d_pin, "H7", "m6", "Transición: desmontable, sin soldadura"),
        ("Pasador de articulación en ojales", P["d_pp"], "H9", "f8", "Con juego, grasa grafitada"),
        ("Cuello del patín en ranura de la bancada", P["w_slot"], "H8", "f7", "Con juego, guiado"),
        ("Uña en alojamiento (ancho)", P["dog_b"], "H9", "f8", "Con juego, retorno de resorte"),
        ("Uña en alojamiento (alto)", P["dog_h"], "H9", "f8", "Con juego, retorno de resorte"),
    ]


def ajuste_txt(d, hole, shaft):
    f_ = iso286.fit(d, hole, shaft)
    lo_h, hi_h = iso286.limits(d, hole)
    lo_s, hi_s = iso286.limits(d, shaft)
    return dict(d=d, hole=hole, shaft=shaft, h_lim=f"{lo_h:.3f} / {hi_h:.3f}".replace(".", ","), s_lim=f"{lo_s:.3f} / {hi_s:.3f}".replace(".", ","),
                juego=f"{f_['cmin']:+d} / {f_['cmax']:+d}", tipo=f_["tipo"])


def tol_txt(d, code):
    return f"Ø{fm(d, 0)} {code} ({iso286.fmt_dev(d, code)})"


def inspecciones(ctx):
    g, P = ctx.g, ctx.P
    L = [
        ("Recepción", "Certificado EN 10204 3.1 de todas las planchas, barras y forjas; trazabilidad por colada; punzonado de la marca de colada en cada pieza.", "100 %", "Doc."),
        ("Recepción", "UT de planchas de la mesa y de la base según ASTM A578 nivel B (si se especifica Z35).", "100 % planchas", "UT"),
        ("Recepción", f"Pasadores y uña: dureza superficial ≥ 55 HRC (Fy_sup {f(P['Fy_surf'])} MPa del cálculo) y profundidad de temple ≥ {fm(g.z_hard, 1)} mm; Re ≥ {f(P['Fy_dog'])} MPa en la forja de la uña.", "100 % uñas; 10 % pasadores", "HRC / macro"),
        ("Soldadura", "WPS/PQR calificados según AWS D1.1 y soldadores calificados; registro de precalentamiento e interpase (≤ 250 °C).", "Todas", "Doc."),
        ("Soldadura", "Inspección visual VT 100 % (ISO 17637 / AWS D1.1 cl. 6) de todas las juntas del programa antes de cualquier END.", "100 %", "VT"),
        ("Soldadura", "Partículas magnéticas MT en filetes críticos (mejillas, collar, orejas de izaje, bancadas, topes, almas y nervios) y en ranuras; 10 % en marco.", "Según programa (100 % / 10 %)", "MT"),
        ("Soldadura", "Ultrasonido UT de uniones CJP (anillos, planchas de la mesa, cubo, empalmes de almas) y de las orejas de izaje y el collar. Criterios AWS D1.1 cl. 6 (cargas estáticas) y BTH-1 Cat. B.", "100 %", "UT"),
        ("Soldadura", "Líquidos penetrantes PT en soldaduras de acero inoxidable (barras de UHMW).", "100 %", "PT"),
        ("Dimensional", f"Planitud de la cara de apoyo de la base (zona Ø{f(P['D_top'] + 20)}) ≤ 0,20 mm y de la cara inferior de la mesa ≤ 0,20 mm antes de montar la interfaz.", "100 %", "Regla/nivel láser"),
        ("Dimensional", f"Pasadores de empuje: PCD Ø{f(2 * g.R_pin)} ±0,3; paso {fm(360 / g.N_pin, 3)}° ±0,05°; agujeros Ø{f(g.d_pin)} H7 coaxiales en ambos anillos (0,05).", "100 %", "CMM / plantilla"),
        ("Dimensional", f"Pivote: perpendicularidad ≤ 0,05 respecto de la cara de apoyo; coaxialidad collar–plancha base 0,05; altura del eje de ménsulas {f(g.hax)} ±0,5.", "100 %", "CMM / comparador"),
        ("Dimensional", f"Ranura T de bancadas: ancho {f(P['w_slot'])} H8, paralelismo 0,10 en todo el largo, coaxial con el ojal de la ménsula ±0,2.", "100 %", "Calibre / comparador"),
        ("Dimensional", f"Orejas de izaje: posición (±{f(P['x_lug'])}, ±{f(g.cl_lug)}) ±2; plano vertical radial; agujero Ø{f(P['d_ear'])} a {f(P['h_ear'])} sobre la base ±1.", "100 %", "Cinta / plantilla"),
        ("Torque", f"Pernos M20×45 de los {g.N_pin} pasadores: ver tabla de torques propuesta (GEN); registro por perno y marca de pintura de control.", "100 %", "Torquímetro"),
        ("Prueba", f"Prueba hidráulica de cilindros y circuito a 1,5 × {f(P['p_relief'])} bar (según certificado del fabricante); p_rated = {fm(P['p_rated'] * 0.0689476, 0)} bar.", "100 %", "Certificado"),
        ("Prueba", "Prueba de carga de izaje de la base a 1,25 × WLL con grilletes y eslinga certificados; MT de las soldaduras de orejas después de la prueba.", "1 vez", "Prueba de carga"),
        ("Aceptación", f"Giro 360° con 1,0 × WLL registrando la presión de despegue; μ real ≤ {fm(P['mu_d'] if g.opt == 0 else ctx.D['apoyo']['mu']['d'], 2)} (diseño de la interfaz elegida).", "1 vez", "Manómetro"),
    ]
    return [(i + 1,) + x for i, x in enumerate(L)]


def pintura(ctx):
    """El cálculo no define el sistema de pintura: se rotula así."""
    return "Sistema de pintura y espesor de película seca (EPS): A DEFINIR (el cálculo no lo fija). Referencia de ambiente: ISO 12944 C4, preparación Sa 2½."


def notas_gen_fab(ctx):
    return ["Tolerancias generales ISO 2768-mK; geométricas ISO 1101; rugosidad ISO 1302; ajustes ISO 286-1/-2.",
            "Soldadura ISO 2553; calidad ISO 5817 indicada en cada símbolo; procesos AWS D1.1; WPS «A DEFINIR POR EL FABRICANTE».",
            "Materiales con certificado EN 10204 3.1; punzonar la marca de colada y el código de la pieza en zona no crítica.",
            "Aristas vivas rotas 1×45° (o R1) salvo indicación; sin torno vertical: gran diámetro por corte a llama/plasma, soldadura y mandrinadora.",
            pintura(ctx)]


# ----------------------------------------------------------------------------------------------
# tablas estándar
# ----------------------------------------------------------------------------------------------
BOM_COLS = [("Pos", 10, "C"), ("Código", 34, "L"), ("Descripción", 112, "L"), ("Cant", 11, "C"), ("Material (norma y grado) / certificado", 98, "L"), ("Dimensión de partida", 62, "L"),
            ("kg unit.", 17, "R"), ("kg total", 19, "R"), ("Observaciones / tratamiento", 120, "L"), ("Plano", 34, "L")]


def partida_dict(ctx):
    import lista
    d = {}
    for r in lista.cut_rows(ctx):
        d[r[0]] = (r[2], r[3], r[6])
    return d


def bom_row(ctx, p, dpart):
    code = p.code.replace(CODE + "-", "")
    forma, dim, nota = dpart.get(code, ("Comercial", "Según catálogo", ""))
    obs = "; ".join(x for x in (p.obs, (f"Tratamiento: {p.tratamiento}" if p.tratamiento and p.tratamiento != "—" else ""), nota) if x)
    return [str(p.pos), code, p.desc, str(p.qty), f"{p.material}. Cert.: {p.cert}", f"{forma} {dim}", f(p.mass_unit, 1), f(p.mass_total, 1), obs, ctx.plano_of(p.key).replace(CODE + "-", "")]


def tabla_despiece(ctx, s, x, y, keys, width, ymin=None, title="DESPIECE", total=True):
    """Tabla de despiece completa (sin truncar). Escala las columnas al ancho dado. Devuelve (y, filas pendientes)."""
    sc = width / sum(c[1] for c in BOM_COLS)
    cols = [(t, w * sc, a) for t, w, a in BOM_COLS]
    dpart = partida_dict(ctx)
    ps = [ctx.m.get(k) for k in keys if ctx.m.get(k)]
    rows = [bom_row(ctx, p, dpart) for p in ps]
    if total:
        rows.append(["", "", "MASA TOTAL DE LAS PIEZAS LISTADAS", "", "", "", "", f(sum(p.mass_total for p in ps), 1), "", ""])
    return s.table(x, y, cols, rows, h=T_S, ymin=ymin, title=title, bold_rows=(len(rows) - 1,) if total else ())


WELD_COLS = [("Junta", 14, "C"), ("Piezas unidas", 40, "L"), ("Tipo / preparación", 55, "L"), ("Garganta a", 15, "C"), ("Cateto z", 14, "C"), ("Longitud total [mm]", 20, "R"), ("Pasadas orient.", 14, "C"),
             ("Proceso", 16, "C"), ("Aporte", 30, "L"), ("WPS", 30, "L"), ("END", 30, "L"), ("Nivel ISO 5817", 16, "C"), ("Origen del tamaño", 52, "L")]


def weld_rows(ctx, ids=None):
    out = []
    for w in ctx.welds:
        if ids is not None and w["id"] not in ids:
            continue
        tipo = w["tipo"] + ("" if w["prep"] == "Sin preparación" else f". Prep.: {w['prep']}")
        out.append([w["id"], f"{w['desc']} ({w['piezas']})", tipo, w["garganta"] if w["groove"] else w["garganta"], w["cateto"], f(w["len_total"], 0) if w["len_total"] else "—",
                    f"{w['pasadas']}", w["proceso"], w["aporte"], w["wps"].replace(" A DEFINIR POR EL FABRICANTE", " (a definir por el fabricante)"), w["end"], w["nivel"].replace("ISO 5817-", ""), w["origen"] + ("" if w["modelada"] else "; no modelada en 3D")])
    return out


def tabla_soldaduras(ctx, s, x, y, ids, width, ymin=None, title="TABLA DE SOLDADURAS"):
    sc = width / sum(c[1] for c in WELD_COLS)
    cols = [(t, w * sc, a) for t, w, a in WELD_COLS]
    return s.table(x, y, cols, weld_rows(ctx, ids), h=T_S, ymin=ymin, title=title)


def leyenda_hatch(s, x, y, classes):
    """Leyenda de achurados utilizados (ISO 128-50)."""
    s.text("ACHURADOS (ISO 128-50)", (x, y), T_N, "TOP_LEFT", bold=True)
    y -= 7
    for cl in sorted(classes):
        pat, ang, sc = draw.HATCH_MAT[cl]
        s.rect(x, y - 6, x + 14, y, "FINA")
        s.hatch_poly([(x, y - 6), (x + 14, y - 6), (x + 14, y), (x, y)], scale=0.35, angle=ang, pattern=pat)
        s.text(draw.HATCH_NAME[cl], (x + 17, y - 3), T_N, "MIDDLE_LEFT")
        y -= 8
    return y
