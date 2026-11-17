"""Textos, filas de listas y notas de proceso de la interfaz TT300-BX para las láminas y listas comunes (lista de corte, plan de corte,
torques, normas, tratamientos, notas de pieza). Todo sale del bloque «bx» del JSON (incluida la tabla «fabricacion»: antes → después).
Solo se llama cuando el JSON trae el bloque «bx» (g.opt == 4)."""
import math
import re

from geom import fm, f, CODE, REV


def fab(g, *frags):
    """Fila de bx.fabricacion cuya «pieza» contiene todos los fragmentos (sin distinguir mayúsculas), con los textos sin nombres internos de parámetros."""
    for r in (g.bx or {}).get("fabricacion") or []:
        pz = str(r.get("pieza", "")).lower()
        if all(fr.lower() in pz for fr in frags):
            return {k: (_limpia_g(g, v) if isinstance(v, str) else v) for k, v in r.items()}
    return None


def _limpia_g(g, txt):
    class _C:
        D = g.D
    return limpia(_C, txt)


def fab_txt(g, *frags, campo="despues"):
    r = fab(g, *frags)
    return (r or {}).get(campo) or ""


def fab_nota(g, *frags):
    """Nota de proceso de la tabla de fabricación: «después» + motivo (estado)."""
    r = fab(g, *frags)
    if not r:
        return None
    return f"Fabricación BX ({r['estado']}): {r['despues']}. Motivo: {r['motivo']} (verificación: {r['verificacion']})."


def _lim(fn):
    """Decorador: limpia (recursivamente) los textos que devuelve una función de este módulo."""
    def rec(ctx, v):
        if isinstance(v, str):
            return limpia(ctx, v)
        if isinstance(v, list):
            return [rec(ctx, x) for x in v]
        if isinstance(v, tuple):
            return tuple(rec(ctx, x) for x in v)
        return v

    def w(ctx, *a, **k):
        return rec(ctx, fn(ctx, *a, **k))
    w.__name__ = fn.__name__
    return w


def _clase_num(des):
    m_ = re.search(r"clase\s+(\d+(?:[.,]\d+)?)", str(des))
    return float(m_.group(1).replace(",", ".")) if m_ else 10.9


@_lim
def collar_corte(ctx):
    g = ctx.g
    return fab_txt(g, "collar de asiento") or fab_txt(g, "collar") or "—"


def cut_rows(ctx, add):
    g = ctx.g
    X = g.bx
    DSK, POR, PAS = X["disco"], X["portador"], X["pastillas"]
    Ro, Ri, t = float(DSK["R_ext"]), float(DSK["R_int"]), float(DSK["t"])
    add("int_bx_disco_mesa", "Plancha (semidisco)", f"{f(2 * Ro + 10)}×{f(Ro + 10)}×{fm(t, 0)}",
        f"Semicorona R{fm(Ri, 0)}…R{fm(Ro, 0)} a plasma con 5 de sobremetal en el borde exterior; " + fab_txt(g, "disco"))
    add("int_bx_portador", "Plancha (corona)", f"{f(2 * float(POR['R_ext']) + 10)}×{f(2 * float(POR['R_ext']) + 10)}×{fm(POR['t'], 0)}", POR["corte"])
    import bx3d
    F = bx3d.pforma(X)
    d_t, H = F["pieza"], float(PAS["H"])
    txt = PAS.get("proceso") or fab_txt(g, "uhmw")
    pl = "plancha" in txt.lower() and "barra" not in txt.lower()
    Hb = float(PAS.get("H_plancha") or H)
    dim = (f"{fm(d_t + 5, 0)}×{fm(d_t + 5, 0)}×{fm(Hb, 1)}" if F["sq"] else f"Ø{fm(d_t + 5, 0)}×{fm(Hb if pl else H + 5, 1)}")
    add("int_bx_pastilla", "Plancha" if pl else "Barra", dim, txt + f" (terminado {bx3d.ptxt(F, d_t, 2)} {(PAS['tolerancias'].get('d') or PAS['tolerancias'].get('lado') or '')} × {fm(H, 2)} {PAS['tolerancias']['H']})")


def nest(ctx, add):
    g = ctx.g
    X = g.bx
    DSK, POR = X["disco"], X["portador"]
    Ro = float(DSK["R_ext"])
    add("int_bx_disco_mesa", "Semidisco inoxidable", 2 * Ro + 10, Ro + 10, float(DSK["t"]))
    add("int_bx_portador", "Portador de pastillas", 2 * float(POR["R_ext"]) + 10, 2 * float(POR["R_ext"]) + 10, float(POR["t"]))


def torque_items(ctx):
    g = ctx.g
    X = g.bx
    T, TP = X["disco"]["tornillos"], X["pastillas"]["tornillo"]
    return [(f"Tornillo {T['designacion_base']} (disco de la mesa BX; toma el par de la interfaz y la dilatación)", int(T["d"]), _clase_num(T["designacion_base"]), int(T["n"])),
            (f"Tornillo {TP['designacion']} (pastilla BX: {TP['apriete']}; aplicar solo el par de asiento, NO la precarga de la tabla)", int(TP["d"]), _clase_num(TP["designacion"]), int(TP["n"]))]


def normas(ctx):
    X = ctx.g.bx
    return [("ASTM A240 / EN 10088-2", f"Acero inoxidable del disco de la mesa ({X['disco']['material']}; acabado 2B/1D)"),
            (X["disco"]["cjp"]["norma"].split(" (")[0], "Soldadura de acero inoxidable estructural (CJP de los semidiscos)"),
            ("AWS A5.9 / A5.4", f"Aporte inoxidable ({X['disco']['cjp']['aporte']})"),
            ("ISO 15527 / ASTM D4020", "UHMW-PE de las pastillas"), ("EN 10025-2", "Acero del portador (" + X["portador"]["material"].split(",")[0] + ")"),
            ("ISO 10683", "Recubrimiento de zinc laminar de los tornillos de la interfaz"), ("ASTM A380 / A967", "Decapado y pasivado del inoxidable después de soldar")]


@_lim
def tratamientos(ctx):
    X = ctx.g.bx
    D = X["disco"]
    return [[f"Disco inoxidable BX ({_cc(ctx, 'int_bx_disco_mesa')})", f"{D['acabado']}; CJP: {D['cjp']['acabado']}; decapado y pasivado de la zona soldada (ASTM A380/A967); sin pintura", "Rugosidad de la franja de la CJP; PT 100 %"],
            [f"Pastillas UHMW-PE ({_cc(ctx, 'int_bx_pastilla')})", f"Sin tratamiento ni pintura; {X['pastillas']['material']}", "Certificado del proveedor"],
            [f"Portador ({_cc(ctx, 'int_bx_portador')})", "Sin pintura en la cara superior ni en los agujeros de las pastillas (contacto UHMW); resto según el sistema de pintura", "VT"]]


def _F(g):
    import bx3d
    F = bx3d.pforma(g.bx)
    return dict(F, pz=bx3d.ptxt(F, F["pieza"], 2), ag=bx3d.ptxt(F, F["nom"]))


def _cc(ctx, k):
    return ctx.code(k).replace(CODE + "-", "").replace("-" + REV, "") if ctx.m.get(k) else "—"


# ---------------------------------------------------------------------- notas de las láminas comunes afectadas por BX
@_lim
def notas_base(ctx):
    g = ctx.g
    X = g.bx
    TP = X["pastillas"]["tornillo"]
    import bx3d
    SI = bx3d.sitios(X)
    F = bx3d.pforma(X)
    cen = [S_ for S_ in SI if S_["sx"] == S_["hx"] and S_["sy"] == S_["hy"]]
    exc = [S_ for S_ in SI if S_ not in cen]
    if F["sq"] and F["orient"] is not None:
        an = ("en los centros de los agujeros del portador: x = " + ", ".join(fm(v, 1) for v in sorted({S_["hx"] for S_ in cen})) + "; y = " + ", ".join(fm(v, 1) for v in sorted({S_["hy"] for S_ in cen})))
    else:
        rr = {}
        for S_ in cen:
            rr.setdefault(round(math.hypot(S_["hx"], S_["hy"]), 1), 0)
            rr[round(math.hypot(S_["hx"], S_["hy"]), 1)] += 1
        an = "anillos " + "; ".join(f"R{fm(r, 1)} ({n})" for r, n in sorted(rr.items()))
    if exc:
        an += "; en el centroide de las pastillas recortadas: " + "; ".join(f"({fm(S_['sx'], 1)}; {fm(S_['sy'], 1)})" for S_ in exc)
    r_ = fab(g, "cara de apoyo de la base")
    return [f"Roscas M{fm(TP['d'], 0)}-6H ciegas de las pastillas ({TP['n']}): taladro prof. {fm(TP['taladro_ciego'], 0)}, rosca útil {fm(TP['rosca_util'], 0)}, remanente {fm(TP['remanente'], 0)}; "
            f"{an} (tabla de {_cc(ctx, 'int_bx_portador')}); se taladran por los agujeros del portador ya soldado.",
            f"Portador {_cc(ctx, 'int_bx_portador')} soldado sobre la cara planeada (J31/J32)" + (f"; planeado de la cara: {r_['estado']} (GEN-026)." if r_ else ".")]


@_lim
def notas_mesa_inf(ctx):
    g = ctx.g
    X = g.bx
    T = X["disco"]["tornillos"]
    pas = [b for b in T["lista"] if not b["anillo"] and not b["ciego"]]
    out = []
    if pas:
        rs = sorted({round(float(b["r"])) for b in pas})
        out.append(f"Roscas M{fm(T['d'], 0)}-6H PASANTES de los tornillos del disco BX en la plancha ({len(pas)}, anillos R{', R'.join(fm(r, 0) for r in rs)}; tabla de anillos en {_cc(ctx, 'int_bx_disco_mesa')}): "
                   f"taladradas por plantilla con el disco cortado (taladrado coincidente) después de planear la cara. {T['nota']}.")
    for frs in (("rebaje del collar",), ("cara inferior de la mesa",)):
        n = fab_nota(g, *frs)
        if n:
            out.append(n)
    return out


@_lim
def notas_anillo_inf(ctx):
    g = ctx.g
    X = g.bx
    T = X["disco"]["tornillos"]
    cie = [b for b in T["lista"] if b["anillo"] or b["ciego"]]
    if not cie:
        return []
    b0 = cie[0]
    rs = sorted({round(float(b["r"])) for b in cie})
    return [f"Roscas M{fm(T['d'], 0)}-6H CIEGAS de los tornillos del disco BX en el anillo inferior ({len(cie)}, R{', R'.join(fm(r, 0) for r in rs)}): taladro prof. {fm(b0['prof'], 0)} desde la cara inferior, "
            f"rosca útil {fm(b0['rosca_util'], 0)} (espesor {fm(b0['t_pieza'], 0)}); por plantilla con el disco cortado, después de planear la cara inferior."]


@_lim
def notas_collar(ctx):
    g = ctx.g
    n = fab_nota(g, "collar de asiento") or fab_nota(g, "collar")
    return [n] if n else []


# ---------------------------------------------------------------------- instructivo de armado (pasos 4 y 5 de hojas_con.pasos)
def _pasos_secuencia(txt):
    """«1) …; 2) …» → [«…», «…»]."""
    partes = re.split(r"\s*\d+\)\s*", str(txt or ""))
    return [x.strip().rstrip(";").strip() for x in partes if x.strip()]


@_lim
def paso4(ctx, pq, insp, T):
    g = ctx.g
    X = g.bx
    POR, PAS = X["portador"], X["pastillas"]
    TP, AJ = PAS["tornillo"], PAS["ajuste"]
    ids_ = [w["id"] for w in ctx.welds if w["id"] in ("J31", "J32", "J33")]
    rows = []
    for i, st in enumerate(_pasos_secuencia(POR["secuencia"])):
        rows.append([pq("int_bx_portador") if i == 0 else "—", f"Portador ({_cc(ctx, 'int_bx_portador')}): {st}" + (f" ({', '.join(ids_)})" if "filete" in st.lower() and ids_ else ""),
                     "Centrado ±1 respecto del eje del pivote; contacto ≤ 1 mm; planitud de los fondos según GEN-004" if i < 2 else "VT 100 % · MT 100 % de los filetes", "Regla, galgas, MT", insp("Interfaz")])
    rows.append([pq("int_bx_pastilla"), f"Pastillas ({_cc(ctx, 'int_bx_pastilla')}): {AJ['montaje']}", f"Interferencia {fm(AJ['delta'], 2)} mm ({_F(g)['pz']} en {_F(g)['ag']}); apoyo pleno en la base; saliente {fm(PAS['h_p'], 2)} sobre el portador",
                 "Prensa con guía, galgas", insp("Interfaz")])
    rows.append([pq("int_bx_tor_pastilla"), f"Tornillos {TP['designacion']} de las pastillas: {TP['apriete']}", f"Cabeza {fm(PAS['cabeza']['cara_superior_cabeza_bajo_cara'], 1)} bajo la cara de la pastilla; par de asiento (GEN-008)",
                 "Torquímetro", insp("torques propuestos")])
    rows.append(["—", "Limpiar las caras de deslizamiento (pastillas y disco) sin partículas; " + (fab_txt(g, "ranuras de engrase") or "sin grasa").split(":")[-1].strip(), "Sin partículas", "Paño", insp("Interfaz")])
    return rows


@_lim
def paso5(ctx, pq, insp, T):
    g = ctx.g
    X = g.bx
    D = X["disco"]
    Tt = D["tornillos"]
    return [[pq("int_bx_disco_mesa"), f"Disco ({_cc(ctx, 'int_bx_disco_mesa')}): soldar los {D['semidiscos']} semidiscos con la CJP J30 en taller ({D['cjp']['norma']}), esmerilar a ras y pulir la franja ({D['cjp']['acabado']}); END: {D['cjp']['END']}",
             "Planitud del disco libre: la del laminado (copia la cara de la mesa al apretar)", "Esmeril, rugosímetro, PT", insp("Interfaz")],
            [pq("int_bx_tor_mesa"), f"Con la mesa invertida: presentar el disco (CJP sobre el eje x, nervio de 0°/180°), taladrar y roscar por plantilla ({Tt['nota']}) y apretar los {Tt['n']} tornillos {Tt['designacion_base']} en secuencia cruzada desde el centro",
             f"Cabeza {fm(Tt['cabeza_bajo_cara'], 1)} bajo la cara de deslizamiento; par según GEN-008", "Taladro magnético, machos, torquímetro", insp("torques propuestos")]]


@_lim
def inspecciones(ctx):
    """Filas del plan de inspección (GEN-003) propias de la interfaz BX: (etapa, verificación, alcance, método)."""
    g = ctx.g
    X = g.bx
    D, POR, PAS = X["disco"], X["portador"], X["pastillas"]
    return [("Soldadura", f"CJP de los semidiscos (J30, {D['cjp']['norma']}): {D['cjp']['END']}; {D['cjp']['acabado']}.", "100 %", "VT / PT / RT-UT"),
            ("Dimensional", f"Portador: agujeros {_F(g)['ag']} con {POR['corte']}; ligamento ≥ {fm(POR['ligamento'], 0)} mm; posición de los agujeros por anillo (tabla de {_cc(ctx, 'int_bx_portador')}).", "100 %", "Calibre / plantilla"),
            ("Dimensional", f"Pastillas: {_F(g)['pz']} {(PAS['tolerancias'].get('d') or PAS['tolerancias'].get('lado') or '')} y alto {fm(PAS['H'], 2)} {PAS['tolerancias']['H']}; saliente montada {fm(PAS['h_p'], 2)} sobre el portador (interferencia {fm(PAS['ajuste']['delta'], 2)}).", "10 % por lote; saliente 100 %", "Micrómetro / galgas")]


# ---------------------------------------------------------------------- textos del JSON sin nombres internos de parámetros
NOMBRES = {"d_flat": "planitud local de la base", "c_boss_r": "holgura radial del collar", "c_boss_a": "holgura axial del collar", "h_collar": "alto del collar",
           "h_boss": "alto del collar", "D_boss": "Ø del collar", "D_top": "Ø de la mesa", "t_base": "espesor de la base", "pv_tolg": "tolerancia del canto",
           "muB_d": "μ de la opción B", "Q_pump": "caudal de la bomba"}
_RX = {}


def limpia(ctx, txt):
    """Reemplaza en un texto del JSON los nombres internos de parámetros de P (el control del juego no los admite fuera de GEN-009/011)."""
    import re as _re
    if not isinstance(txt, str):
        return txt
    key = id(ctx.D["P"])
    if key not in _RX:
        pn = sorted([k for k in ctx.D["P"] if "_" in k or len(k) >= 4] + ["L0", "Fy_sup", "q_losa", "k_borde", "h_rebaje", "D_rebaje_bot", "h_rebaje_cubo", "h_collar"], key=len, reverse=True)
        _RX[key] = _re.compile(r"(?<![A-Za-z0-9_\-])(" + "|".join(_re.escape(k) for k in pn) + r")(?![A-Za-z0-9_])")
    txt = txt.replace("planitud d_flat", "planitud local")
    return _RX[key].sub(lambda m_: NOMBRES.get(m_.group(1), m_.group(1).replace("_", " ")), txt)
