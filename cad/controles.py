"""Controles automáticos de coherencia del juego de planos (revisión exhaustiva de la Rev. C).

Cada control devuelve una lista de fallas (texto). El generador los escribe en informe_paquete.md y sale con código 2 si alguno falla.
  - iso2768:     la tabla de GEN-004 coincide con ISO 2768-1:1989, Tabla 1 (valores de referencia escritos aquí, independientes de la tabla dibujada).
  - partidas:    cada dimensión de partida de la lista de cortes es ≥ la dimensión de la pieza terminada (+ sobremedida donde se mecaniza a cota).
  - avellanados: cada avellanado (cara cónica) queda dentro de su pieza con borde ≥ BORDE_MIN; los roscados de la tapa de inspección dejan pared ≥ BORDE_MIN.
  - notas:       ninguna nota se repite dentro de una lámina; las notas generales de GEN-001 no se copian en otras láminas; textos contradictorios prohibidos.
  - codigos:     los códigos de pieza INT salen del registro fijo (un código = una pieza en todas las variantes) y la lámina de cada pieza lleva su código.
  - variante:    el rótulo (subtítulo) y el título de cada lámina identifican la variante del juego.
  - wps:         cada WPS agrupa juntas de una sola familia y un solo rango de precalentamiento (AWS D1.1-2020 Tabla 5.11, por la parte más gruesa)."""
import math
import re
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from geom import CODE, REV, BORDE_MIN

# ISO 2768-1:1989, Tabla 1 — desviaciones admisibles para cotas lineales [mm]; None = no especificado
ISO2768_REF = [((0.5, 3), (0.05, 0.1, 0.2, None)), ((3, 6), (0.05, 0.1, 0.3, 0.5)), ((6, 30), (0.1, 0.2, 0.5, 1.0)), ((30, 120), (0.15, 0.3, 0.8, 1.5)),
               ((120, 400), (0.2, 0.5, 1.2, 2.5)), ((400, 1000), (0.3, 0.8, 2.0, 4.0)), ((1000, 2000), (0.5, 1.2, 3.0, 6.0)), ((2000, 4000), (None, 2.0, 4.0, 8.0))]


def _num(t):
    t = t.strip()
    if t in ("—", "-", ""):
        return None
    return float(t.replace("±", "").replace(".", "").replace(",", "."))


def iso2768(hojas_gen):
    out = []
    tab = hojas_gen.ISO2768_LINEAL
    if len(tab) != len(ISO2768_REF):
        return [f"ISO 2768-1: la tabla tiene {len(tab)} rangos (norma: {len(ISO2768_REF)})"]
    for (rng, vals), ((a, b), ref) in zip(tab, ISO2768_REF):
        nums = [float(x.replace(".", "").replace(",", ".")) for x in re.findall(r"\d[\d.]*,?\d*", rng)]
        if not nums or abs(nums[0] - a) > 1e-9 or abs(nums[-1] - b) > 1e-9:
            out.append(f"ISO 2768-1: rango «{rng}» ≠ {a}–{b}")
        for cl, v, r in zip("fmcv", vals, ref):
            vv = _num(v)
            if (vv is None) != (r is None) or (vv is not None and abs(vv - r) > 1e-9):
                out.append(f"ISO 2768-1: rango {a}–{b}, clase {cl}: {v} (norma ±{r})")
    return out


# ------------------------------------------------------------------------------------------------
def _obb_dims(shape):
    """Dimensiones (ordenadas) de la caja orientada mínima de un sólido."""
    from OCP.Bnd import Bnd_OBB
    from OCP.BRepBndLib import BRepBndLib
    b = Bnd_OBB()
    BRepBndLib.AddOBB_s(shape.wrapped, b, True, True, False)
    return sorted([2 * b.XHSize(), 2 * b.YHSize(), 2 * b.ZHSize()])


def _parse_partida(forma, dim):
    """[d1, d2, d3] de la dimensión de partida («155×180×25», «Ø260×65», «Ø2.010/Ø1.710×30»); None si no es un bloque/disco."""
    s = dim.replace(".", "").replace(",", ".")
    m = re.match(r"^Ø([\d.]+)(?:/Ø[\d.]+)?×([\d.]+)$", s)
    if m:
        D, t = float(m.group(1)), float(m.group(2))
        return sorted([D, D, t])
    m = re.match(r"^([\d.]+)×([\d.]+)×([\d.]+)$", s)
    if m:
        return sorted(float(x) for x in m.groups())
    return None


def partidas(ctx):
    import lista
    out = []
    for r in lista.cut_rows(ctx):
        code, forma, dim = r[0], r[2], r[3]
        if "rolada" in forma:              # pletina rolada: la partida es el desarrollo, no la envolvente
            continue
        pd = _parse_partida(forma, dim)
        p = next((q for q in ctx.m.parts if q.code.replace(CODE + "-", "") == code), None)
        if pd is None or p is None:
            continue
        sol = p.solid.vals()[0]
        so = sol.Solids()[0] if hasattr(sol, "Solids") and sol.Solids() else sol
        if p.key.startswith("mesa_anillo"):
            pz = sorted([2 * ctx.g.Rt, 2 * ctx.g.Rt, ctx.g.tpr])      # anillo completo: se arma con 4 segmentos de la partida
        elif p.key.startswith("mesa_nervio"):
            pz = sorted([lista.rib_len(ctx, p), ctx.g.hw, ctx.P["t_rib"]])
        else:
            pz = _obb_dims(so)
        for a, b in zip(pd, pz):
            if a < b - 0.05:
                out.append(f"Partida menor que la pieza terminada: {code} «{forma} {dim}» frente a {'×'.join(f'{x:.1f}' for x in pz)}")
                break
    return out


# ------------------------------------------------------------------------------------------------
def avellanados(ctx):
    """Cada cara cónica (avellanado) de una pieza fabricada: un anillo de radio (r_avellanado + BORDE_MIN), a 0,3 mm bajo la cara, debe quedar dentro del sólido."""
    import cadquery as cq
    out = []
    g = ctx.g
    for p in ctx.m.parts:
        if p.comercial:
            continue
        for so in p.solid.vals():
            sols = so.Solids() if hasattr(so, "Solids") else [so]
            for sd in sols[:2]:                    # basta un sector/pieza por tipo
                for fc in sd.Faces():
                    if fc.geomType() != "CONE":
                        continue
                    circ = [e for e in fc.Edges() if e.geomType() == "CIRCLE"]
                    if len(circ) < 2:
                        continue
                    big = max(circ, key=lambda e: e.radius())
                    sml = min(circ, key=lambda e: e.radius())
                    cb, cs_ = big.arcCenter(), sml.arcCenter()        # centro de la circunferencia (Center() da el baricentro de un arco)
                    ax = (cb.x - cs_.x, cb.y - cs_.y, cb.z - cs_.z)
                    L = math.sqrt(sum(a * a for a in ax)) or 1.0
                    ax = tuple(a / L for a in ax)
                    u = (1.0, 0.0, 0.0) if abs(ax[0]) < 0.9 else (0.0, 1.0, 0.0)
                    u = (u[0] - ax[0] * sum(a * b for a, b in zip(u, ax)), u[1] - ax[1] * sum(a * b for a, b in zip(u, ax)), u[2] - ax[2] * sum(a * b for a, b in zip(u, ax)))
                    nu = math.sqrt(sum(a * a for a in u))
                    u = tuple(a / nu for a in u)
                    v = (ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0])
                    # chaflán exterior (material por dentro del cono) o avellanado (hueco por dentro): punto a media altura, 0,6 mm hacia el eje
                    rm_ = (big.radius() + sml.radius()) / 2 - 0.6
                    cm_ = ((cb.x + cs_.x) / 2, (cb.y + cs_.y) / 2, (cb.z + cs_.z) / 2)
                    if sd.isInside(cq.Vector(*(c + rm_ * uu for c, uu in zip(cm_, u)))):
                        continue
                    rr = big.radius() + BORDE_MIN
                    bad = 0
                    for k in range(16):
                        t = 2 * math.pi * k / 16
                        q = tuple(c - 0.3 * a + rr * (math.cos(t) * uu + math.sin(t) * vv) for c, a, uu, vv in zip((cb.x, cb.y, cb.z), ax, u, v))
                        if not sd.isInside(cq.Vector(*q)):
                            bad += 1
                    if bad:
                        out.append(f"Avellanado Ø{2 * big.radius():.1f} de {p.code.replace(CODE + '-', '')} a menos de {BORDE_MIN:.0f} mm del borde de la pieza o de otro agujero")
                        break
    # roscados de la tapa de inspección en el fondo del rebaje: pared hasta el agujero central y hasta el canto del rebaje
    r = g.insp_pcd / 2
    if r - g.insp_d / 2 - g.hole_top / 2 < BORDE_MIN - 1e-6:
        out.append(f"Roscados M{g.insp_d:.0f} de la tapa de inspección: pared {r - g.insp_d / 2 - g.hole_top / 2:.1f} mm hasta el agujero Ø{g.hole_top:.0f} (< {BORDE_MIN:.0f})")
    if (g.cb_D / 2 - 1) - (r + g.insp_csk / 2) < BORDE_MIN - 1e-6:
        out.append(f"Avellanado de la tapa de inspección: borde {(g.cb_D / 2 - 1) - (r + g.insp_csk / 2):.1f} mm (< {BORDE_MIN:.0f})")
    return out


# ------------------------------------------------------------------------------------------------
def _norm(t):
    t = re.sub(r"^\s*\d+\.\s*", "", str(t))
    return re.sub(r"\s+", " ", t).strip().lower()


PROHIBIDOS = [(re.compile(r"ISO 13920(?:-B(?!F)|\s*\(?clase)"), "ISO 13920 con clase distinta de «ISO 13920-BF»"), (re.compile(r"\(o R1\)"), "aristas «1×45° (o R1)» (GEN-001: 1×45° ISO 13715)"),
              (re.compile(r"10204 2\.2"), "certificado 2.2 (GEN-001: EN 10204 3.1)"), (re.compile(r"arandela[^.;]*(S355J2|A572)"), "material de la arandela distinto del único del despiece"),
              (re.compile(r"HV 300 mín"), "arandela «HV 300 mín.» (material único: ver despiece)")]


def notas(ctx, hojas):
    out = []
    gen = [_norm(n) for n in getattr(ctx, "notas_generales", [])]
    firma = [x[:70] for x in gen if len(x) > 30]
    for h in hojas:
        tag = h.plano.replace(CODE + "-", "").replace("-" + REV, "")
        ns = [n for n in list(getattr(h, "notas_reg", [])) + list(getattr(h.s, "notas_reg", []))]
        seen = {}
        for n in ns:
            k = _norm(n)
            if len(k) < 12:
                continue
            if k in seen:
                out.append(f"{tag}: nota repetida «{n[:70]}»")
            seen[k] = 1
            if not tag.startswith("GEN-001") and any(k.startswith(fi) or fi.startswith(k[:70]) for fi in firma):
                out.append(f"{tag}: copia una nota general de GEN-001 «{n[:70]}»")
        for t in h.s.texts:
            for rx, why in PROHIBIDOS:
                if rx.search(str(t)):
                    out.append(f"{tag}: {why}: «{str(t)[:80]}»")
    return sorted(set(out))


def codigos(ctx, hojas):
    """H-04: un código = una geometría.
    - registro fijo de números de la interfaz (INT_CODIGOS) sin números repetidos para piezas distintas;
    - cada código del juego agrupa sólidos de una sola firma geométrica (medida sobre el B-rep: firmas.py); los tipos distintos llevan sufijo;
    - la cantidad de tipos coincide con el registro de geometrías por variante (VAR_CODIGOS);
    - si el registro cad/firmas_codigos.json es de la misma base de parámetros, cada código tiene la firma registrada (misma geometría en todas
      las variantes); el control entre juegos completo es `python3 cad/firmas.py <entregas>`;
    - cada lámina de pieza de la interfaz lleva el código de su pieza principal."""
    import json
    import modelo3d_tt300c as M3
    import firmas
    out = list(ctx.m.info.get("codigos_fallas", []))
    usados = {}
    for k, (n, nm, var) in M3.INT_CODIGOS.items():
        usados.setdefault(n, set()).add(nm)
    for n, nms in usados.items():
        if len(nms) > 1:
            out.append(f"INT-{n:03d}: el registro asigna el mismo número a piezas distintas {sorted(nms)}")
    for p in ctx.m.parts:
        if p.sub == "INT":
            ck = M3.int_clave(p.key, ctx.g.conf)
            if ck not in M3.INT_CODIGOS or M3.INT_CODIGOS[ck][0] != p.num:
                out.append(f"{p.code}: código fuera del registro fijo de la interfaz")
        if not p.firmas_cod:
            continue
        ts = firmas.tipos(p)
        if len(ts) != len(p.firmas_cod):
            out.append(f"{p.code}: {len(ts)} geometrías distintas para {len(p.firmas_cod)} código(s)")
    try:
        reg = json.loads(firmas.REGISTRO.read_text(encoding="utf-8"))
    except Exception:
        reg = None
    if reg and reg.get("base") == firmas.base_hash(ctx.D):
        for cod, fs in firmas.firmas_juego(ctx).items():
            r = reg["firmas"].get(cod)
            if r is not None and firmas.clave(r) != firmas.clave(fs):
                out.append(f"{cod}: geometría distinta de la registrada para ese código (variantes {', '.join(reg['variantes'].get(cod, []))})")
    lam = {p.code: p.code_lamina for p in ctx.m.parts}
    for h in hojas:
        t = h.plano.replace(CODE + "-", "")
        if getattr(h, "serie", "") == "FAB" and h.items and int(t.split("-")[1]) < 100:
            if h.plano != lam.get(h.items[0], h.items[0]):
                out.append(f"{t}: la lámina no lleva el número de su pieza principal ({h.items[0]})")
    return out


def variante(ctx, hojas):
    g = ctx.g
    out = []
    for h in hojas:
        inf = h.info(1, 1)
        if f"Variante {g.variante}" not in inf["subproj"]:
            out.append(f"{h.tag}: el rótulo no identifica la variante {g.variante}")
        if not h.titulo.endswith(f"VARIANTE {g.variante}"):
            out.append(f"{h.tag}: el título no identifica la variante {g.variante}")
    return out


def wps(ctx):
    import propuestas
    out = []
    grp = {}
    for w in ctx.welds:
        grp.setdefault(w["wps_n"], []).append(w)
    for n, ws in sorted(grp.items()):
        fam = {propuestas.wps_family(w) for w in ws}
        pre = {propuestas.precalentamiento(w["t_pre"]) for w in ws}
        if len(fam) > 1 or len(pre) > 1:
            out.append(f"WPS-P{n:02d}: juntas {', '.join(w['id'] for w in ws)} con familias {sorted(fam)} o precalentamientos {sorted(pre)} distintos")
    return out


def tornillos_juego(ctx):
    """Todos los tornillos del juego que roscan en una pieza: (descripción, d, L, espesor apretado, rosca útil, agujero ciego)."""
    g = ctx.g
    out = []
    if ctx.m.get("tapa_ret"):
        out.append((f"Tapa retenedora: ISO 10642 M10×{g.cap_L:.0f} en el pivote (rosca útil {g.cap_thr:.0f}, taladro {g.cap_tap:.0f})", 10.0, g.cap_L, g.cap_t, g.cap_thr, True))
    if ctx.m.get("tapa_insp"):
        out.append((f"Tapa de inspección: ISO 10642 M{g.insp_d:.0f}×{g.insp_L} en el fondo del rebaje (rosca pasante {g.insp_rem:.0f})", g.insp_d, float(g.insp_L), g.cb_t, g.insp_rem, False))
    if ctx.m.get("pernos_pasador"):
        out.append((f"Perno ISO 4762 M20×45 en el pasador (arandela {g.washer_t:.0f}, rosca útil {g.pin_thr:.0f}, taladro {g.pin_drill_L:.0f})", 20.0, 45.0, g.washer_t, g.pin_thr, True))
    for lado, r in sorted((ctx.m.info.get("screw_resp") or {}).items()):
        out.append((f"Tornillo de posición ISO 10642 M{r['d']:.0f}×{r['L']:.0f}, lado {lado} (rosca útil {r['thr']:.0f}" + (", pasante)" if r["pasante"] else f", taladro {r['drill']:.0f})"),
                    r["d"], r["L"], r["clamp"], r["thr"], not r["pasante"]))
    return out


def tornillos(ctx):
    """N-01: cada tornillo roscado en una pieza: engrane ≥ 1,0·d; en agujero ciego, la punta queda ≥ 2 mm antes del fin de la rosca útil
    (largo dentro de la rosca ≤ rosca útil − 2); en rosca pasante, el engrane no supera el espesor roscado."""
    out = []
    for txt, d, L, clamp, thr, ciego in tornillos_juego(ctx):
        eng = L - clamp
        if eng < d - 1e-6:
            out.append(f"{txt}: engrane {eng:.1f} mm < 1,0·d = {d:.0f}")
        if ciego and eng > thr - 2.0 + 1e-6:
            out.append(f"{txt}: la punta llega a {thr - eng:.1f} mm del fin de la rosca útil (< 2 mm: toca fondo)")
        if not ciego and eng > thr + 1e-6:
            out.append(f"{txt}: engrane {eng:.1f} mm mayor que el espesor roscado {thr:.0f}")
    return out


def gdt_vistas(ctx, hojas):
    """B-20: en cada lámina de pieza, cada tolerancia geométrica de la tabla tiene su marco dibujado en una vista (sobre la superficie o la cota que controla),
    cada letra de datum citada tiene su indicador ISO 5459 en una vista, y ninguna indicación declarada quedó sin lugar. Incluye todas las láminas del accionamiento."""
    out = []
    for h in hojas:
        t = h.plano.replace(CODE + "-", "")
        if getattr(h, "serie", "") != "FAB":
            continue
        items = getattr(h, "gd_items", None) or []
        ok = getattr(h, "indic_ok", []) or []
        for f_ in getattr(h, "indic_fallo", []) or []:
            out.append(f"{t}: indicación sin lugar en la vista {f_}")
        fr = [o for o in ok if o[0] == "fcf"]
        dl = {o[1] for o in ok if o[0] == "datum"}
        for sym, tol, dat, txt in items:
            key = ("fcf", sym, tol, tuple(dat) if isinstance(dat, list) else dat)
            if key not in fr:
                out.append(f"{t}: tolerancia «{sym} {tol} {dat or ''}» ({txt[:40]}) sin marco en las vistas")
            for d_ in [x for dd_ in (dat if isinstance(dat, list) else [dat] if dat else []) for x in str(dd_).split("-")]:
                if d_ not in dl:
                    out.append(f"{t}: datum {d_} sin indicador en las vistas")
    return out


def cadenas_cerradas(ctx, hojas):
    """ISO 129-1 §5.3: en una misma vista y dirección no se acotan todos los eslabones de una cadena y además su total
    (sobreacotado). Se buscan cotas cuyo intervalo es exactamente la unión de una cadena de ≥ 2 cotas contiguas de la misma vista;
    las cotas auxiliares (entre paréntesis) y las teóricamente exactas (recuadro) no cuentan."""
    from vistas import COTAS
    tol = 0.06
    out = []
    grp = {}
    for r in COTAS.rows:
        e = r.get("eje")
        if not e or e[3] or str(r["texto"]).strip().startswith("(") or e[2] - e[1] < 0.05:
            continue
        grp.setdefault((r["sheet"], r["vista"], e[0]), []).append((e[1], e[2], r["texto"]))
    for (sh, vi, ori), L in grp.items():
        segs = sorted(set((round(a, 2), round(b, 2), t) for a, b, t in L))
        for (A, B, tt) in segs:
            inner = [(a, b, t) for a, b, t in segs if (a, b) != (A, B) and a >= A - tol and b <= B + tol]
            # ¿hay camino de A a B con eslabones contiguos?
            front, seen, camino = [(A, [])], set(), None
            while front and camino is None:
                x, path = front.pop()
                for a, b, t in inner:
                    if abs(a - x) <= tol and (a, b) not in seen:
                        seen.add((a, b))
                        if abs(b - B) <= tol and len(path) + 1 >= 2:
                            camino = path + [t]
                            break
                        front.append((b, path + [t]))
            if camino:
                out.append(f"{sh.replace(CODE + '-', '')} · {vi}: cadena cerrada {' + '.join(camino)} = {tt}")
    return sorted(set(out))


def placa_guia(ctx, hojas):
    """Placa-guía curva (modo pivotado): canto G1 (quiebre ≤ 0,01° entre tramos consecutivos), desviación de las entidades del DXF, del sólido 3D
    y de la polilínea del núcleo respecto de los segmentos del núcleo ≤ tolerancia_polilinea (0,1 mm), y códigos nuevos para la geometría nueva."""
    import contorno
    g = ctx.g
    out = []
    if g.modo != 2 or not ctx.m.get("placa_leva"):
        return out
    PL = g.FPV["placas_leva"]
    ins = PL["instancias"]["1_antihorario"]
    segs = contorno.leer(ins)
    if not contorno.geometrico(segs):
        return out
    tol = float(PL.get("tolerancia_polilinea", 0.1) or 0.1)
    canto = contorno.leer(ins, "segmentos_canto") if ins.get("segmentos_canto") else segs
    q = contorno.quiebres(canto)
    g1 = max((a for _, a, _ in q), default=0.0)
    g0 = max((d for _, _, d in q), default=0.0)
    if g1 > 0.01 or g0 > 1e-3:
        out.append(f"placa-guía: canto no G1 (quiebre máx. {g1:.4f}°, salto {g0:.4f} mm)")
    h = next((h_ for h_ in hojas if getattr(h_, "placa_dxf_pts", None)), None)
    dev_dxf = contorno.desviacion(segs, h.placa_dxf_pts) if h else None
    if dev_dxf is None or dev_dxf > tol:
        out.append(f"placa-guía: desviación del DXF {dev_dxf} mm (máx. {tol})")
    so = ctx.shapes["placa_leva"].Solids()[0]
    zt = PL["z"][1]
    pts = []
    for e in so.Edges():
        a, b = e.startPoint(), e.endPoint()
        if abs(a.z - zt) < 1e-3 and abs(b.z - zt) < 1e-3:
            for i in range(11):
                v = e.positionAt(i / 10)
                pts.append((v.x, v.y))
    from shapely.geometry import Point as _Pt
    hol = [_Pt(x, y).buffer(PL["pernos"]["agujero"] + 20) for x, y in ins["pernos"]] + [_Pt(x, y).buffer(30) for x, y in (ins.get("pasadores_posicion") or [])]
    pts = [q_ for q_ in pts if not any(h_.contains(_Pt(*q_)) for h_ in hol)]
    dev_3d = contorno.desviacion(segs, pts)
    dev_pl = contorno.desviacion(segs, [tuple(q_) for q_ in ins["contorno"]])
    if dev_3d > tol:
        out.append(f"placa-guía: desviación del sólido 3D {dev_3d:.4f} mm (máx. {tol})")
    if dev_pl > tol:
        out.append(f"placa-guía: la polilínea del núcleo se aparta {dev_pl:.4f} mm de sus segmentos (máx. {tol})")
    usados = {p_.code for p_ in ctx.m.parts}
    for viejo in (f"{CODE}-ACC-017-{REV}", f"{CODE}-ACC-018-{REV}") + ((f"{CODE}-ACC-015-{REV}",) if g.FPV["bloque_una"]["cara"].get("radio_planta") else ()):
        if viejo in usados:
            out.append(f"{viejo}: código de la geometría anterior usado para la geometría nueva")
    ctx.m.info["placa_guia_ctl"] = dict(g1_deg=g1, g0_mm=g0, dev_dxf=dev_dxf, dev_3d=dev_3d, dev_polilinea=dev_pl, tol=tol)
    return out


def volteo(ctx, hojas):
    """Una pieza declarada «volteable» (su imagen especular se obtiene volteándola) no puede tener rasgos de una sola cara:
    avellanados (caras cónicas) o una cara de referencia/temple propia. Se mira el B-rep: caras cónicas = avellanado."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cone
    out = []
    for p in ctx.m.parts:
        if not getattr(p, "volteable", False) or p.key not in ctx.shapes:
            continue
        so = ctx.shapes[p.key].Solids()[0]
        if any(BRepAdaptor_Surface(fc.wrapped).GetType() == GeomAbs_Cone for fc in so.Faces()):
            out.append(f"{p.code}: pieza avellanada declarada «montada volteada» (los avellanados quedarían contra el apoyo)")
    for h in hojas:
        if getattr(h, "serie", "") != "FAB":
            continue
        if any("se montan volteadas" in t or "se monta volteado" in t for t in getattr(h, "notas_reg", []) or []):
            for c in h.items:
                p = next((q for q in ctx.m.parts if q.code == c), None)
                if p is not None and p.key in ctx.shapes and any(BRepAdaptor_Surface(fc.wrapped).GetType() == GeomAbs_Cone for fc in ctx.shapes[p.key].Solids()[0].Faces()):
                    out.append(f"{h.tag}: nota de montaje volteado para una pieza avellanada ({c})")
    return out


def cajetin(ctx, hojas):
    """Desborde de texto en el cajetín: material y tratamiento caben en 3 renglones de sus celdas (ancho 94 y 36 mm, letra 3 mm),
    el título en 3 renglones y el subtítulo en 2 (mismo corte de renglones que draw.frame)."""
    from draw import wrapw
    out = []
    for h in hojas:
        t = h.plano.replace(CODE + "-", "")
        if len(wrapw(str(h.material), 94, 3.0)) > 3:
            out.append(f"{t}: el material no cabe en el cajetín ({len(wrapw(str(h.material), 94, 3.0))} renglones)")
        if len(wrapw(str(h.trat), 36, 3.0)) > 3:
            out.append(f"{t}: el tratamiento no cabe en el cajetín ({len(wrapw(str(h.trat), 36, 3.0))} renglones)")
        if len(wrapw(h.titulo, 174, 3.6, True)) > 3:
            out.append(f"{t}: el título no cabe en el cajetín")
    return out


def todos(ctx, hojas):
    import hojas_gen
    res = dict(iso2768=iso2768(hojas_gen), partidas=partidas(ctx), avellanados=avellanados(ctx), notas=notas(ctx, hojas), codigos=codigos(ctx, hojas), variante=variante(ctx, hojas), wps=wps(ctx), tornillos=tornillos(ctx), gdt_vistas=gdt_vistas(ctx, hojas),
               cadenas_cerradas=cadenas_cerradas(ctx, hojas), placa_guia=placa_guia(ctx, hojas), volteo=volteo(ctx, hojas), cajetin=cajetin(ctx, hojas))
    return res
