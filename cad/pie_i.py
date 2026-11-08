"""Láminas de la interfaz de deslizamiento (sectores, topes, tornillos de posición, graseras, ranuras de engrase, patrón de tapones) y de la cubierta de madera."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pie_common import *
from pie_a import ra, wd
from soldadura_det import add_prep
import autodim


def sector_local(ctx, key):
    g = ctx.g
    th = 360.0 / ctx.m.get(key).qty if key == "int_uhmw" else 360.0 / (int(ctx.P["bz_npad"]) if (key == "int_bronce" and g.conf == 3) else g.n_sec)
    a = th / 2 if key != "int_uhmw" else th / 2 + (th / 4.0 if g.n_seg == g.n_sec else 0.0)
    nk = key + "_s1"
    ctx.local_ang(key, nk, a, th)
    return nk, th


def int_sector_sheet(ctx, key, titulo, face):
    """Lámina de un tipo de sector (o pastilla/lámina) de interfaz: planta con radios, muesca del tope, tornillos, ranuras, graseras y tapones; corte por la bisectriz; detalles ampliados."""
    g, P, m = ctx.g, ctx.P, ctx.m
    lay = m.layout
    pt = m.get(key)
    nk, th = sector_local(ctx, key)
    ks = [key] + ([k for k in ("int_tapones",) if key == "int_bronce" and m.get(k)])
    con_barras = key == "int_disco_base" and m.get("int_tope_uhmw") is not None
    if con_barras:
        titulo = "INTERFAZ: DISCO DE LA BASE CON LAS BARRAS DEL REBAJE UHMW SOLDADAS (SUBCONJUNTO SOLDADO)"
        nkb = ctx.local_ang("int_tope_uhmw", "int_tope_uhmw_s1", th / 2, th)
        ofl = m.info.get("uhmw_off", 0.0) - th / 2              # ángulo de la barra respecto de la bisectriz del sector
    if key == "int_cara":
        titulo = "INTERFAZ: 2.ª PLACA DE BRONCE DE LA MESA (SECTOR)" if g.conf == 2 else "INTERFAZ: DISCO DURO DE LA MESA (SECTOR)"
    elif key == "int_bronce":
        titulo = "INTERFAZ: PASTILLA DE BRONCE CON TAPONES DE GRAFITO" if g.conf == 3 else "INTERFAZ: PLACA DE BRONCE CON TAPONES DE GRAFITO (SECTOR)"
    p = Pieza(ctx, ks, titulo, fmt="A1")
    s = p.s
    bb = ctx.shapes[nk].BoundingBox()
    z0_, z1_ = bb.zmin, bb.zmax
    t = z1_ - z0_
    ztop = z1_
    zs = z1_ if face == "top" else z0_            # cara deslizante
    on = [nk]
    p.iso_keys = [nk]
    Ln = lay.L_base if face == "top" else lay.L_mesa

    def planta(V, p):
        s.line(V.P(g.Ri - 10, 0, ztop), V.P(g.Ro + 10, 0, ztop), "EJE")
        rs_ = [math.hypot(vx.X, vx.Y) for vx in ctx.shapes[nk].Vertices()]
        ri_e, ro_e = (min(rs_), max(rs_)) if rs_ else (g.Ri, g.Ro)
        if abs(ri_e - g.Ri) > 0.5 or abs(ro_e - g.Ro) > 0.5:
            ri_e, ro_e = ri_e, ro_e                       # sector con radios propios (p. ej. lámina UHMW): se acota el real
        ah = math.radians(th * 0.35)
        pe = autodim.visible_points(V, on)
        def arc_pt(r_):
            c_ = [q for q in pe if abs(math.hypot(q[0][0], q[0][1]) - r_) < 0.3]
            return min(c_, key=lambda q: abs(q[2])) [0] if c_ else None
        po, pi_ = arc_pt(ro_e), arc_pt(ri_e)
        if po:
            V.note_pt(po, (34, -30), f"R{fm(ro_e, 0)} (radio exterior)", on=on, dot=True)
        if pi_:
            V.note_pt(pi_, (30, 26), f"R{fm(ri_e, 0)} (radio interior)", on=on, dot=True)
        if po and pi_:
            V.dimh(pi_, po, "bottom", 0, on=on, text=f"{fm(ro_e - ri_e, 0)} (ancho radial)")
        if g.removable and Ln and key != "int_uhmw":
            nb = lay.b_tope + 2
            V.dimh((g.r_u - Ln / 2, nb / 2, ztop), (g.r_u + Ln / 2, nb / 2, ztop), "top", 0, on=on, text=f"{fm(Ln, 1)} (muesca del tope)")
            V.dimv((g.r_u + Ln / 2, -nb / 2, ztop), (g.r_u + Ln / 2, nb / 2, ztop), "right", 0, on=on, text=f"{fm(nb, 0)} (barra + 2)")
            V.dimh((g.Ri, 0, ztop), (g.r_u, 0, ztop), "bottom", 0, on=on, text=f"{fm(g.r_u - g.Ri, 1)} (hasta r_u = {fm(g.r_u, 1)})", virt_a=None) if False else None
        cs = V.circles(on, lay.d_clear / 2 - 0.05, lay.d_clear / 2 + 0.05)          # agujero pasante del tornillo (no confundir con los tapones Ø12, H-15)
        if cs:
            sc_ = sorted({round(math.hypot(u, v), 1) for (u, v, r) in cs if abs(v) < 1})
            u, v, r = min(cs, key=lambda q: abs(q[1]))
            V.note_hole((u, v, ztop), r, 90, f"{len(sc_)} × M{fm(lay.d_tor, 0)} ISO 10642 (avellanado Ø{fm(lay.dk, 0)}, pasante Ø{fm(lay.d_clear, 1)}) a r = " + " y ".join(fm(x, 1) for x in sc_), ext=46, on=on)
        gs = V.circles(on, 2.9, 3.1)
        if m.info.get("grease_pts") and gs and face == "bot":
            u, v, r = [q for q in gs if abs(q[2] - 3.0) < 0.1][0]
            V.note_hole((u, v, ztop), r, 40, f"{g.n_greaser} × Ø6 +0,2/0 conducto de engrase axial (graseras en el canto de la mesa)", ext=40, on=on)
        if key == "int_bronce":
            pl = [q for q in V.circles(on, P["bz_plug_d"] / 2 - 0.05, P["bz_plug_d"] / 2 + 0.05) if not any(math.hypot(q[0] - c_[0], q[1] - c_[1]) < 0.5 for c_ in cs)]
            if pl:
                u, v, r = pl[0]
                ps_ = (g.IG.get("tapones") or {}).get("porSector") or []
                n1 = len(ctx.m.info.get("plug_sets", {}).get(0, [])) or len(pl)
                V.note_hole((u, v, ztop), r, 120, f"{n1} tapones de grafito Ø{fm(P['bz_plug_d'], 0)} H7 en este sector (cantidad por sector: tabla de INT-102), paso {fm(P['bz_plug_p'], 0)} (malla triangular)", ext=40, on=on)
        p.cut_mark("planta", "A", (g.Ri - 18, 0, ztop), (g.Ro + 18, 0, ztop), 90)
        if con_barras:
            Lb_, bb_ = m.info["uhmw_bar_L"], P["b_tope"]
            r0b = g.Ri + 50
            ca, sa = math.cos(math.radians(ofl)), math.sin(math.radians(ofl))
            P2 = lambda u, w: V.P(u * ca - w * sa, u * sa + w * ca, ztop)
            s.pline([P2(r0b, -bb_ / 2), P2(r0b + Lb_, -bb_ / 2), P2(r0b + Lb_, bb_ / 2), P2(r0b, bb_ / 2)], "VIS", closed=True)
            s.line(P2(g.Ri - 10, 0), P2(g.Ro + 10, 0), "EJE")
            rm_ = r0b + Lb_ / 2
            p.cut_mark("planta", "D", (rm_ * ca - (-60) * sa * 0 + 60 * sa, rm_ * sa - 60 * ca, ztop), (rm_ * ca - 60 * sa, rm_ * sa + 60 * ca, ztop), (ofl + 180) % 360)
        ang = math.radians(th / 2)
        s.text(f"{fm(th, 3)}°", V.P((g.Ro + 30) * math.cos(ang * 0.0), (g.Ro + 30) * math.sin(ang), ztop), T_N, "BOTTOM_LEFT")
    p.vs("planta", on, "top", lv=(1, 2, 2, 1), extra=(30, 0, 160, 20), draw=planta, hatch=False, title=(f"PLANTA DE LA PASTILLA (bisectriz sobre el eje x; pastilla de {fm(th * float(g.I.get('cov', 1.0)), 3)}° en una posición de {fm(th, 3)}°)" if (key == "int_bronce" and g.conf == 3) else f"PLANTA DEL SECTOR (bisectriz sobre el eje x; sector de {fm(th, 3)}°)"), w=1.8, auto=dict(holes=False, verts=False, hole_notes=False, only_extents=True, overall=True))
    if con_barras:
        # sección D-D perpendicular a la barra, por su punto medio: disco + barra (subconjunto soldado)
        rot_key(ctx, nk, nk + "_D", -ofl)
        rot_key(ctx, nkb, nkb + "_D", -ofl)
        rmD = g.Ri + 50 + m.info["uhmw_bar_L"] / 2
        jb_ = jids(ctx, "Barras del rebaje UHMW")

        def secD(V, p):
            if jb_:
                w_out(p, jb_[0], V, (rmD, P["b_tope"] / 2, z1_ + 1), "right", dy=12)
            V.dimh((rmD, -P["b_tope"] / 2, z1_ + m.info["uhmw_bar_h"]), (rmD, P["b_tope"] / 2, z1_ + m.info["uhmw_bar_h"]), "top", 0, on=[nkb + "_D"], text=f"{fm(P['b_tope'], 0)} (barra)")
            V.dimv((rmD, P["b_tope"] / 2, z1_), (rmD, P["b_tope"] / 2, z1_ + m.info["uhmw_bar_h"]), "right", 0, on=[nkb + "_D"], text=f"{fm(m.info['uhmw_bar_h'], 0)} (altura)")
        p.vs("secD", [nk + "_D", nkb + "_D"], "right", cut=((rmD, 0, 0), (-1, 0, 0)), center=(rmD, 0, (z0_ + z1_) / 2), win=(-45, -t - 6, 45, t + m.info["uhmw_bar_h"] + 8), lv=(1, 2, 2, 2),
             extra=(0, 0, 115, 0), draw=secD, hs=0.35, maxs=2.0, w=1.0, title="SECCIÓN D-D: BARRA DEL REBAJE SOLDADA AL DISCO (J21)", mat={nk + "_D": "inox", nkb + "_D": "inox"}, auto=False)
    rs = (sorted({round(u, 1) for (u, v, r) in autodim.circles3d(type("X", (), dict(shapes=ctx.shapes, view="top", uv=lambda self, p3: (p3[0], p3[1])))(), on, 2.9, lay.dk / 2 + 0.1) and []})) if False else None

    def corte(V, p):
        ra(s, V, (g.r_u - 120, 0, zs), "Ra 0,4 (cara deslizante)" if key != "int_uhmw" else "Ra 3,2", dy=3 if face == "top" else -20)
        if not g.removable:                    # sin muesca: la vista no tiene aristas propias que acotar (H-41)
            V.dimv((g.r_u + 60, 0, z0_), (g.r_u + 60, 0, z1_), "right", 0, on=on, text=f"{fm(t, 1)} (e) ±0,1")
        V.dim_dia((g.Ri + 2, 0, (z0_ + z1_) / 2), 0.0, 0, on=on, text="") if False else None
    p.vs("corte", on, "front", cut=CUT_Y, center=(g.r_u, 0, (z0_ + z1_) / 2), win=(-130, -t - 10, 130, t + 10), lv=(2, 2, 1, 2), extra=(0, 0, 10, 0), draw=corte, title="CORTE A-A POR LA BISECTRIZ", hs=0.35, w=1.2,
         auto=dict(tol={}, text={round(t, 1): f"{fm(t, 1)} (e) ±0,1"}, holes=False))
    # vistas de contorno del sector: elevación (cuerda y espesor) y lateral
    p.vs("elev", on, "front", lv=(1, 2, 2, 1), hatch=False, title="ELEVACIÓN DEL SECTOR (cuerda y espesor)", w=0.9, maxs=1.0,
         auto=dict(holes=False, tol={round(t, 1): " ±0,1"}))
    p.vs("lat", on, "right", lv=(1, 2, 2, 1), hatch=False, title="VISTA LATERAL (ancho del sector en el borde exterior)", w=0.9, maxs=1.0, auto=dict(holes=False, tol={round(t, 1): " ±0,1"}))
    scr_r = list((m.info.get("radii_screw") if face == "top" else m.info.get("radii_screw_m")) or [])
    if g.removable and scr_r and key != "int_uhmw":
        p.vs("det_scr", on, "front", cut=CUT_Y, center=(scr_r[0], 0, (z0_ + z1_) / 2), win=(-14, -t / 2 - 3, 14, t / 2 + 3), lv=(1, 2, 1, 1), hs=0.4, maxs=5.0, w=1.0,
             title=f"DETALLE B (en el plano del corte A-A): AVELLANADO ISO 10642 M{fm(lay.d_tor, 0)} Ø{fm(lay.dk, 0)}×90° A r = {fm(scr_r[0], 1)}", auto=dict(tol={}, holes=False))
    if g.removable and Ln and key != "int_uhmw":
        nb = lay.b_tope + 2
        p.vs("det_muesca", on, "top", center=(g.r_u, 0, ztop), win=(-Ln / 2 - 22, -nb / 2 - 22, Ln / 2 + 22, nb / 2 + 22), lv=(1, 2, 2, 2), hatch=False, maxs=2.0, title="DETALLE C: MUESCA DEL TOPE", w=1.0,
             auto=dict(holes=False, tol={}))
    if key in ("int_disco_mesa", "int_cara") and g.h_gr > 0 and lay.r_circ:
        p.detail("det_gr", "corte", (lay.r_circ[0] - g.r_u, 0, zs), 12, "D", lv=(1, 2, 1, 1), title="DETALLE D: RANURA CIRCUNFERENCIAL (5:1)", maxs=5.0) if False else None
    rows = [["Espesor e", f"{fm(t, 1)} mm"], ["Sectores", f"{pt.qty} de {fm(th, 3)}°"], ["Junta en frío", f"{fm(g.junta('uhmw' if key == 'int_uhmw' else 'disc'), 2)} mm"],
            ["Radios interior / exterior", f"{fm(g.Ri, 0)} / {fm(g.Ro, 0)} mm"], ["Material", pt.material], ["Masa unitaria", f"{f(pt.mass_unit, 2)} kg"]]
    if key == "int_bronce" and g.conf == 3:
        cov = float(g.I.get("cov", 1.0))
        sp_ = th * cov
        rows[1] = ["Pastillas", f"{pt.qty}, una por posición de {fm(th, 3)}°; ángulo de la pastilla {fm(sp_, 3)}° (cubrimiento {fm(cov, 2)}), bordes radiales"]
        rows[2] = ["Hueco entre pastillas", f"{fm(th - sp_, 3)}° = {fm(math.radians(th - sp_) * g.Ri, 1)} mm en R{fm(g.Ri, 0)} y {fm(math.radians(th - sp_) * g.Ro, 1)} mm en R{fm(g.Ro, 0)} (sin junta en frío)"]
    if g.removable and key != "int_uhmw":
        rows.insert(3, ["Muesca del tope", f"{fm(lay.b_tope + 2, 0)} × {fm(Ln, 1)} centrada a r = {fm(g.r_u, 1)} mm"])
        if scr_r:
            rows.append(["Tornillos de posición", f"{len(scr_r)} por sector, M{fm(lay.d_tor, 0)}, a r = {' y '.join(fm(x, 1) for x in scr_r)} sobre la bisectriz"])
    gp_ = m.info.get("grease_pts") or []
    if gp_ and face == "bot" and key in ("int_disco_mesa", "int_cara"):
        angs_ = ", ".join(fm(math.degrees(math.atan2(y_, x_)) % 360, 1) + "°" for x_, y_ in gp_[:g.n_greaser])
        rows.append(["Conductos de engrase", f"{len(gp_[:g.n_greaser])} × Ø6 +0,2/0 axial pasante a r = {fm(math.hypot(*gp_[0]), 1)}, en los sectores de las graseras ({angs_}); el resto de sectores sin conducto"])
    p.table_block("PARÁMETROS DEL SECTOR (JSON)", [("Parámetro", 40, "L"), ("Valor", 130, "L")], rows)
    # tabla de sectores
    srows = [[str(i + 1), fm((i + 0.5) * th, 3) + "°", fm(i * th, 3) + "°", fm((i + 1) * th, 3) + "°"] for i in range(pt.qty)]
    half = (len(srows) + 1) // 2
    s2 = [srows[i] + (srows[i + half] if i + half < len(srows) else [""] * 4) for i in range(half)]
    p.table_block(f"TABLA DE SECTORES (juntas en las líneas de inicio/fin; junta en frío {fm(g.junta('uhmw' if key == 'int_uhmw' else 'disc'), 2)} mm)",
                  [("N°", 10, "C"), ("Bisectriz", 28, "R"), ("Inicio", 24, "R"), ("Fin", 24, "R"), ("N° ", 10, "C"), ("Bisectriz ", 28, "R"), ("Inicio ", 24, "R"), ("Fin ", 24, "R")], s2, wide=True)
    muesca = g.removable and key != "int_uhmw"
    T = g.IG.get("tapones") if key == "int_bronce" else None
    if T:
        rows_t = [["Tapones reales (cálculo)", f(T["N_real"])], ["Posiciones de malla / ideales", f"{f(T['N_malla'])} / {f(T['N_ideal'])}"], ["Fracción de área de grafito real / ideal / usada", f"{fm(T['fg_real'], 3)} / {fm(T['fg_ideal'], 3)} / {fm(T['fg_usado'], 3)}"],
                  ["Pérdidas: borde, muesca, tornillos, ranuras", f"{T['perdidas']['borde']}, {T['perdidas']['muesca']}, {T['perdidas']['tornillos']}, {T['perdidas']['ranCirc'] + T['perdidas']['ranRad']}"],
                  ["Tapones en el 3D", f(m.info.get("n_plugs", 0))], ["Ø / paso / profundidad", f"Ø{fm(T['d'], 0)} / {fm(T['p'], 0)} / {fm(m.info.get('plug_prof', 0), 1)} (70 % de e)"],
                  ["Cumple la fracción mínima", f"{'sí' if T['cumple_lubricacion'] else 'NO'} (mínimo {fm(T['fg_min'], 2)})"]]
        p.table_block("PATRÓN DE TAPONES DE GRAFITO (resumen; ver lámina del patrón)", [("Patrón de tapones (interfazGeom.tapones)", 80, "L"), ("Valor", 90, "L")], rows_t)
    p.tables(jids(ctx, "Barras del rebaje UHMW") if con_barras else None)
    if con_barras:
        p.table_block("BARRAS DEL REBAJE SOLDADAS AL SECTOR (una por sector, en la junta entre sectores de UHMW)", [("Dato", 60, "L"), ("Valor", 110, "L")],
                      [["Pieza", f"{ctx.code('int_tope_uhmw').replace(CODE + '-', '')} (lámina propia)"], ["Ángulo del eje de la barra", f"{fm(m.info.get('uhmw_off', 0.0), 2)}° + {fm(360.0 / m.get('int_tope_uhmw').qty, 2)}°·k desde +x ({fm(ofl, 2)}° desde la bisectriz del sector)"],
                       ["Radios de la barra", f"r = {fm(g.Ri + 50, 0)} a {fm(g.Ri + 50 + m.info['uhmw_bar_L'], 0)}"], ["Soldadura", "J21: 2 filetes 309L, VT 100 % y PT 100 %"]])
    p.notes(([f"Subconjunto soldado: sector del disco + barra {ctx.code('int_tope_uhmw').replace(CODE + '-', '')}. Secuencia: 1) cortar los sectores; 2) trazar la línea de junta de los sectores de UHMW y soldar la barra (J21, 309L, PT 100 %); 3) rectificar/lapear la cara deslizante; 4) decapar y pasivar."] if con_barras else []) +
            [pt.process, pt.obs or "", (f"Cara deslizante: Ra 0,4 rectificada/lapeada; sobreespesor de relapeado {fm(P['ss_allow'], 1)} mm." if key != "int_uhmw" else "Caras de la lámina: sin mecanizado de precisión (cortada de plancha); sin relapeado."),
             "Junta entre sectores de ancho constante (S04): bordes paralelos a la bisectriz" + ("; chaflán de alivio 45° en el canto de la muesca, del tamaño indicado en la lámina del tope." if muesca else "."),
             ("Tolerancias: espesor e ±0,1; radios ±0,5; planitud de la cara deslizante 0,05" + ("; posición de la muesca ±0,2 respecto de la bisectriz." if muesca else ".")) if key != "int_uhmw" else
             "Tolerancias de la lámina cortada (sin rectificar): espesor e ±0,3 (plancha del proveedor); radios ±1; planitud 0,5.", f"Tratamiento: {pt.tratamiento}."],
            gd=([("flat", "0,05", None, "Planitud de la cara deslizante")] if key != "int_uhmw" else [("flat", "0,5", None, "Planitud de la lámina")]) +
               ([("pos", "0,2", "A", "Muesca del tope respecto de la bisectriz del sector (A)")] if muesca else []))
    p.build()
    return p.h


def _mk(key, titulo, face):
    def fn(ctx):
        return int_sector_sheet(ctx, key, titulo, face)
    fn.__name__ = "sheet_" + key
    PLAN.append((fn.__name__, [key] + (["int_tapones"] if key == "int_bronce" else []), fn))
    globals()[fn.__name__] = fn


_mk("int_disco_base", "INTERFAZ: DISCO DE LA BASE (SECTOR)", "top")
_mk("int_disco_mesa", "INTERFAZ: DISCO DE LA MESA (SECTOR)", "bot")
_mk("int_cara", "INTERFAZ: DISCO DURO / 2.ª PLACA (SECTOR)", "bot")
_mk("int_bronce", "INTERFAZ: PLACA DE BRONCE CON TAPONES DE GRAFITO (SECTOR / PASTILLA)", "top")
_mk("int_uhmw", "INTERFAZ: LÁMINA DE UHMW-PE (SECTOR)", "top")


def tope_sheet(ctx, key, titulo, side):
    """Barra de tope: despiece de la barra (planta, elevación, extremo), detalle de junta con el sector (cotas a_sup, a_inf, h_c, b, L, filetes) y preparación del filete."""
    g, P, m = ctx.g, ctx.P, ctx.m
    lay = m.layout
    tp = {"int_tope_base": lay.tp_base, "int_tope_mesa": lay.tp_mesa, "int_tope_uhmw": lay.tp_uhmw}[key]
    pt = m.get(key)
    th = 360.0 / pt.qty
    a = th / 2 if key != "int_tope_uhmw" else (th / 4.0 if g.n_seg == g.n_sec else 0.0) + 0.0
    nk = key + "_b1"
    ctx.local_ang(key, nk, a, 4)
    if nk not in ctx.shapes:
        return None
    sector = {"int_tope_base": "int_disco_base" if m.get("int_disco_base") else "int_bronce", "int_tope_mesa": "int_disco_mesa" if m.get("int_disco_mesa") else "int_cara", "int_tope_uhmw": "int_uhmw"}[key]
    ctx.local_ang(sector, sector + "_t1", a, th * 1.0)
    plate = "mesa_plancha_inf" if key == "int_tope_mesa" else ("int_disco_base" if key == "int_tope_uhmw" else "base_plancha")
    rot_key(ctx, plate, plate + "_t", -a)
    p = Pieza(ctx, [key], titulo, fmt="auto")
    s = p.s
    bb = ctx.shapes[nk].BoundingBox()
    L, b = tp["L"], P["b_tope"]
    zb0, zb1 = bb.zmin, bb.zmax
    on = [nk]
    p.iso_keys = [nk]
    ids = jids(ctx, "Barras de tope – plancha base") if key == "int_tope_base" else jids(ctx, "Barras de tope – plancha inferior") if key == "int_tope_mesa" else jids(ctx, "Barras del rebaje UHMW")
    p.vs("pl", on, "top", lv=(1, 2, 2, 1), hatch=False, title="BARRA — PLANTA", w=1.5, auto=dict(tol={round(L, 1): " (L)", round(b, 1): " (b)"}, holes=False))
    p.vs("el", on, "front", lv=(1, 2, 2, 1), hatch=False, title="BARRA — ELEVACIÓN", w=1.0, auto=dict(tol={round(tp["h_barra"], 1): ""}, holes=False))
    p.vs("ex", on, "right", lv=(1, 2, 2, 1), hatch=False, title="BARRA — VISTA DE EXTREMO", w=0.8, auto=dict(holes=False), maxs=2.0)
    ks = [plate + "_t", sector + "_t1", nk]
    zc_ = (zb0 + zb1) / 2
    xc = (bb.xmin + bb.xmax) / 2

    def jd(V, p):
        if ids:
            w_out(p, ids[0], V, (xc, -b / 2, zb0 + 1), "right", dy=-14)
    p.vs("junta", ks, "right", cut=((xc, 0, 0), (-1, 0, 0)), center=(xc, 0, zc_), win=(-(b / 2 + 34), -tp["t"] - 14, b / 2 + 34, tp["t"] + 14), lv=(1, 2, 1, 2), extra=(0, 0, 115, 0), draw=jd, hs=0.25, w=1.4,
         title="DETALLE DE JUNTA (corte por el centro de la barra)", mat={plate + "_t": ctx.mat.get(plate, "acero"), sector + "_t1": ctx.mat.get(sector, "acero"), nk: ctx.mat.get(key, "acero")},
         auto=dict(on=ks, tol={round(tp["h_barra"], 1): " (h)", round(b, 1): " (b)"}, hole_notes=False))
    if ids:
        add_prep(p, "det_j", wd(ctx, ids[0]), t1=b, t2={"int_tope_base": g.tb, "int_tope_mesa": g.tbo, "int_tope_uhmw": g.I["tss"]}[key])
    rows = [["Cara de la barra bajo la cara deslizante", fm(tp["a_sup"], 1)], ["Chaflán 45° del canto del sector (= filete + 1)", fm(tp["a_inf"], 1)], ["Contacto útil", fm(tp["h_c"], 1)],
            ["Contacto útil mínimo (cálculo)", fm(tp["h_c_min"], 1)], ["b (ancho de la barra)", fm(b, 0)], ["L (largo de la barra)", fm(tp["L"], 1)], ["Altura de la barra (espesor del sector − retiro)", fm(tp["h_barra"], 1)],
            ["Filete de la barra", f"z{fm(P['w_tope'], 0)} (mín. {fm(tp['w_min'], 0)})"], ["Espesor del sector t", fm(tp["t"], 1)], ["Cantidad de barras", f"{pt.qty}"]]
    p.table_block("GEOMETRÍA DEL TOPE (interfazGeom.topes)", [("Parámetro del tope", 120, "L"), ("[mm]", 50, "R")], rows)
    p.tables(ids)
    if key == "int_tope_uhmw":
        off_u = m.info.get("uhmw_off", 0.0)
        th_u = 360.0 / max(pt.qty, 1)
        r_in = g.Ri + 50
        nts = [f"Barra {fm(b, 0)} × {f(L, 1)} × {fm(tp['h_barra'], 1)} de {pt.material.split(',')[0]}; corte a sierra, extremos a escuadra; {pt.qty} unidades.",
               f"Posición (H-01): una barra en cada JUNTA entre sectores de UHMW (nunca sobre la bisectriz), con su eje a θ = {fm(off_u, 2)}° + {fm(th_u, 2)}°·k desde +x y radialmente de r = {fm(r_in, 0)} a {fm(r_in + L, 0)}; "
               f"la franja entre sectores de UHMW mide b + junta en frío = {fm(b + g.junta('uhmw'), 1)} mm. Ubicación en planta: INT-001 y CON-012.",
               f"Soldar al disco inoxidable de la base (INT-001, e = {fm(g.I['tss'], 0)}) con 2 filetes (frente y dorso) z{fm(P['w_tope'], 0)} continuos, aporte 309L; el filete cabe bajo el chaflán de {fm(tp['a_inf'], 0)} mm del sector de UHMW.",
               f"Soldar ANTES del rectificado de la cara del disco; la barra queda {fm(tp['a_sup'], 1)} mm bajo la cara de la lámina (contacto útil {fm(tp['h_c'], 1)} mm, mínimo {fm(tp['h_c_min'], 1)} mm)."]
        gdl = [("par", "0,05", "A", "Caras de contacto de la barra paralelas a la línea de junta entre sectores de UHMW (A)"), ("pos", "±0,1°", "A", "Posición angular del eje de la barra respecto de la línea de junta (A)")]
    else:
        nts = [f"Barra {fm(b, 0)} × {f(L, 1)} × {fm(tp['h_barra'], 1)} de {pt.material.split(',')[0]}; corte a sierra, extremos a escuadra; {pt.qty} unidades.",
               f"Soldar a {'la plancha base' if key == 'int_tope_base' else 'la plancha inferior de la mesa'} con 2 filetes (frente y dorso) z{fm(P['w_tope'], 0)} continuos; el filete cabe bajo el chaflán de {fm(tp['a_inf'], 0)} mm del sector.",
               f"Soldar ANTES del alivio y del rectificado de las caras deslizantes; barra centrada en r_u = {fm(g.r_u, 1)} sobre la bisectriz de cada sector, posición angular ±0,1°.",
               f"El sector va con muesca de {fm(b + 2, 0)} mm (1 mm de holgura por lado); la barra queda {fm(tp['a_sup'], 1)} mm bajo la cara deslizante (contacto útil {fm(tp['h_c'], 1)} mm, mínimo {fm(tp['h_c_min'], 1)} mm)."]
        gdl = [("par", "0,05", "A", "Cara de contacto de la barra paralela al plano de la bisectriz (A)"), ("pos", "±0,1°", "A", "Posición angular respecto de la bisectriz del sector (A)")]
    p.notes(nts, gd=gdl)
    p.build()
    return p.h


def _mkt(key, titulo, side):
    def fn(ctx):
        return tope_sheet(ctx, key, titulo, side)
    fn.__name__ = "sheet_" + key
    PLAN.append((fn.__name__, [key], fn))
    globals()[fn.__name__] = fn


_mkt("int_tope_base", "INTERFAZ: BARRA DE TOPE DE LA BASE Y DETALLE DE JUNTA", "base")
_mkt("int_tope_mesa", "INTERFAZ: BARRA DE TOPE DE LA MESA Y DETALLE DE JUNTA", "mesa")
_mkt("int_tope_uhmw", "INTERFAZ: BARRA DEL REBAJE UHMW Y DETALLE DE JUNTA", "uhmw")


@pieza("int_tornillo_base", "int_tornillo_mesa")
def sheet_int_tornillos(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    lay = m.layout
    ks = [k for k in ("int_tornillo_base", "int_tornillo_mesa") if m.get(k)]
    if not ks:
        return None
    p = Pieza(ctx, ks, f"INTERFAZ: TORNILLOS DE POSICIÓN ISO 10642 M{fm(lay.d_tor, 0)} (ROSCA ISO 262, PAR PROPUESTO)", fmt="auto")
    s = p.s
    loc = []
    for k in ks:
        sol = ctx.shapes[k].Solids()[0]
        c = sol.Center()
        ctx.shapes[k + "_1"] = cq.Compound.makeCompound([sol]).translate(cq.Vector(-c.x, -c.y, 0))
        ctx.mat[k + "_1"] = "acero"
        loc.append(k + "_1")
    p.iso_keys = loc[:1]
    d = lay.d_tor
    rows = []
    for i, (k, kl) in enumerate(zip(ks, loc)):
        bb = ctx.shapes[kl].BoundingBox()
        Lk = bb.zmax - bb.zmin
        pt = m.get(k)

        def el(V, p, bb=bb):
            s.line(V.P(0, 0, bb.zmin - 4), V.P(0, 0, bb.zmax + 6), "EJE")
        p.vs(f"el{i}", [kl], "front", lv=(2, 2, 2, 2), extra=(0, 0, 40, 0), draw=el, hatch=False, title=f"{ctx.code(k).replace(CODE + '-', '')} — {'BASE' if 'base' in k else 'MESA'}: ELEVACIÓN", w=1.2,
             auto=dict(rev=(0, 0), rev_side="top", hole_notes=False, tol={}))
        rows.append([ctx.code(k).replace(CODE + "-", ""), "Base" if "base" in k else "Mesa", f"M{fm(d, 0)}×{fm(pt.qty and Lk, 0)}", fm(Lk, 1), f"{pt.qty}", "ISO 10642 10.9, rosca ISO 262 M%s×%s-6g" % (fm(d, 0), "1" if d == 6 else fm({8: 1.25, 10: 1.5, 12: 1.75}.get(int(d), 1.0), 2))])
    p.vs("planta", [loc[0]], "top", lv=(1, 1, 1, 1), hatch=False, title="CABEZA (planta)", w=0.8, maxs=5.0, mins=2.0, auto=dict(hole_rmin=1.0))
    pos = []
    for i, (rs, nm) in enumerate(((m.info.get("radii_screw") or [], "base"), (m.info.get("radii_screw_m") or [], "mesa"))):
        for j, r in enumerate(rs):
            pos.append([nm, f"{j + 1}", fm(r, 1), "0° (bisectriz del sector)", f"{(m.get('int_tornillo_base') if nm == 'base' else m.get('int_tornillo_mesa') or m.get('int_tornillo_base')).qty // max(len(rs), 1)}"])
    p.table_block("POSICIÓN EN EL SECTOR (S01: 2 por sector sobre la bisectriz; PROVISORIO)", [("Pieza", 14, "L"), ("N°", 10, "C"), ("r [mm]", 22, "R"), ("Ángulo", 60, "L"), ("Cant. por radio", 30, "R")], pos)
    from hojas_gen import torque_rows
    trow = [r for r in torque_rows(ctx) if f"M{fm(d, 0)}" in r[0] and "posición" in r[0]]
    if trow:
        r0 = trow[0]
        p.table_block("PAR DE APRIETE PROPUESTO (GEN-008; no transmiten carga)", [("Dato", 60, "L"), ("Valor", 110, "L")],
                      [["Rosca", r0[2]], ["A_s [mm²]", r0[3]], ["F_pre = 0,7·Rp0,2·A_s [kN]", r0[5]], ["K / T = K·F·d [N·m]", f"{r0[6]} / {r0[7]}"], ["Estado", "PROPUESTA, A CONFIRMAR POR EL CALCULISTA"]])
    p.table_block("ESPECIFICACIÓN (comercial; marca/modelo por catálogo, GEN-008)", [("Pieza", 14, "L"), ("Lado", 14, "L"), ("Designación", 30, "L"), ("Largo [mm]", 18, "R"), ("Cant", 12, "R"), ("Norma / clase / rosca", 70, "L")], rows)
    p.tables()
    rec_ = P["ss_allow"] if g.opt in (1, 2) else P["bz_allow"]
    p.notes([f"Tornillo avellanado ISO 10642 M{fm(d, 0)} cl. 10.9 (cabeza Ø{fm(lay.dk, 0)}) alojado en el avellanado Ø{fm(lay.dk, 0)}×90° del sector (detalle B de la lámina del sector); rosca ISO 262 en el respaldo (plancha base / plancha inferior de la mesa), prof. ≥ 1,5·d.",
             "Los tornillos solo posicionan los sectores: el par lo toman las barras de tope soldadas.", "Largo normalizado ≥ t − 0,55·d + 1,5·d (S11).",
             f"Aplicar fijarroscas de resistencia media; cabeza {fm(rec_, 1)} +0,2/0 mm bajo la cara deslizante (= sobreespesor de relapeado; igual en todas las variantes).", "Marca/modelo por catálogo (GEN-008)."],
            gd=[("perp", "0,1", "A", "Cara de apoyo del avellanado perpendicular al eje del tornillo")])
    p.build()
    return p.h


@pieza("graseras")
def sheet_int_graseras(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    pts = m.info.get("grease_pts") or []
    if not m.get("graseras"):
        return None
    sol = ctx.shapes["graseras"].Solids()[0]
    c = sol.Center()
    a = math.degrees(math.atan2(c.y, c.x))
    ctx.shapes["grasera_1"] = cq.Compound.makeCompound([sol]).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -a).translate(cq.Vector(-math.hypot(c.x, c.y), 0, 0))
    ctx.mat["grasera_1"] = "acero"
    p = Pieza(ctx, ["graseras"], "INTERFAZ: GRASERAS DIN 71412 M10×1, TALADRO Ø6 Y TRAZADO DE ENGRASE", fmt="A1")
    s = p.s
    p.iso_keys = ["grasera_1"]
    cz = ctx.shapes["grasera_1"].BoundingBox()
    p.vs("el", ["grasera_1"], "front", lv=(2, 2, 2, 2), extra=(0, 0, 50, 0), hatch=False, title="GRASERA (elevación)", w=1.0, auto=dict(rev=(0, 0), rev_side="top", hole_notes=False))
    p.vs("pl", ["grasera_1"], "top", lv=(1, 2, 1, 1), hatch=False, title="GRASERA (planta)", w=0.8, maxs=5.0, mins=2.0, auto=dict(hole_rmin=1.0))
    rr = g.Ro - 30

    def trazado(V, p):
        for (x, y) in pts[:g.n_greaser]:
            ang = math.degrees(math.atan2(y, x))
            q1 = polar(g.Rt - 12, ang); q2 = polar(rr, ang)
            s.line(V.P(q1[0], q1[1], g.z0 + g.tpr / 2), V.P(q2[0], q2[1], g.z0 + g.tpr / 2), "EJE")
            s.text(f"{fm(ang % 360, 1)}°", V.P(*(polar(g.Rt + 10, ang) + (g.z0,))), T_N, "MIDDLE_CENTER")
        s.text(f"Taladro Ø6 radial desde el canto hasta R{fm(rr, 0)} y Ø6 axial hasta la cara deslizante", (V.ext[0], V.ext[3] + 6), T_N, "BOTTOM_LEFT")
    p.vs("traz", {k: ctx.shapes[k] for k in ("mesa_plancha_inf", "mesa_anillo_inf", "graseras") if k in ctx.shapes}, "bottom", lv=(1, 1, 1, 1), extra=(0, 0, 40, 10), draw=trazado, hatch=False,
         title="TRAZADO DE LAS GRASERAS EN EL ANILLO INFERIOR DE LA MESA MES-004 (vista inferior)", w=1.6, auto=dict(on=["mesa_anillo_inf"], holes=False, verts=False, only_extents=True))
    ag = math.degrees(math.atan2(pts[0][1], pts[0][0]))
    zk = ["mesa_anillo_inf", "graseras"] + [k for k in ("int_disco_mesa", "int_cara") if ctx.m.get(k)]
    for k in zk:
        rot_key(ctx, k, k + "_G", -ag)
    gk = [k + "_G" for k in zk]
    zc0 = g.z0 + g.tpr / 2

    def cg(V, p):
        s.line(V.P(g.Rt - 40, 0, zc0), V.P(rr - 10, 0, zc0), "EJE")
    p.vs("corte", gk, "front", cut=CUT_Y, center=(rr + 20, 0, zc0), win=(-70, -45, 50, 45), lv=(1, 2, 2, 1), extra=(0, 0, 40, 0), draw=cg, hs=0.4, maxs=2.0, w=1.4,
         title=f"CORTE A-A POR LA GRASERA G1 (a {fm(ag % 360, 1)}°): TALADRO Ø6 RADIAL Y AXIAL EN EL ANILLO MES-004", mat={k + "_G": ctx.mat.get(k, "acero") for k in zk}, auto=dict(on=gk, tol={}, hole_notes=False))
    rows = [[f"G{i + 1}", fm(math.degrees(math.atan2(y, x)) % 360, 2) + "°", fm(math.hypot(x, y), 1), "radial Ø6 + axial Ø6 (bisectriz del sector)"] for i, (x, y) in enumerate(pts[:g.n_greaser])]
    p.table_block("UBICACIÓN DE LAS GRASERAS (origen: eje de la mesa)", [("N°", 12, "C"), ("Ángulo", 30, "R"), ("r [mm]", 28, "R"), ("Conducto", 60, "L")], rows)
    p.tables()
    p.notes([f"Grasera recta DIN 71412 M10×1 de acero zincado, {g.n_greaser} unidades, en el canto del anillo inferior de la mesa (MES-004); rosca M10×1 (ISO 261) prof. 12 con asiento plano.",
             f"Conducto: taladro Ø6 radial hasta R{fm(rr, 0)} (ranura circunferencial exterior) y Ø6 axial hasta la cara deslizante (S08, PROVISORIO); desbarbar y soplar.",
             "Probar cada conducto con grasa grafitada NLGI 2 antes de montar los sectores.", "Marca/modelo por catálogo (GEN-008)."],
            gd=[("pos", "Ø0,5", "A", "Posición del conducto respecto de la bisectriz de su sector (A)")])
    p.build()
    return p.h


@pieza("int_disco_mesa", "int_bronce", nogroup=True)
def sheet_int_ranuras(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    lay = m.layout
    if g.opt not in (1, 3) or g.h_gr <= 0:
        return None
    # opción A: ranuras en el disco de la mesa (cara inferior); opción C: ranuras en la placa de bronce de la base (cara superior)
    key, face = ("int_disco_mesa", "bot") if g.opt == 1 else ("int_bronce", "top")
    if not m.get(key):
        return None
    p = Pieza(ctx, [key], "INTERFAZ: RANURAS DE ENGRASE EN LA CARA DESLIZANTE (TRAZADO: 12 RADIALES Y CIRCUNFERENCIALES, GRASERAS)", fmt="A1", code="INT-101")
    s = p.s
    nk, th = sector_local(ctx, key)
    bb = ctx.shapes[nk].BoundingBox()
    t = bb.zlen
    zs = bb.zmin if face == "bot" else bb.zmax
    sg = 1.0 if face == "bot" else -1.0          # el material está hacia +z (bot) o hacia -z (top) desde la cara deslizante
    zf = zs + sg * g.h_gr                        # fondo de las ranuras
    rr = lay.r_circ
    p.iso_keys = [nk]

    def planta(V, p):
        c3 = (0, 0, zs)
        for r in rr:
            s.circle(V.P(c3), r * V.scale, "EJE")
        for phi in lay.phi_rad:
            q1, q2 = polar(g.Ri, phi), polar(g.Ro, phi)
            s.line(V.P(q1[0], q1[1], zs), V.P(q2[0], q2[1], zs), "EJE")
        for i, r in enumerate(rr):
            a_ = math.radians(40 + 22 * i)
            pa = V.P(r * math.cos(a_), r * math.sin(a_), zs)
            s.leader(pa, (V.ext[2] + 12, pa[1] + 6 * i), f"circunferencial {i + 1}: R{fm(r, 0)} (eje de la ranura)", dot=True)
        s.text(f"{g.n_gr_rad} ranuras radiales a k·{fm(360 / g.n_gr_rad, 2)}° (k = 0…{g.n_gr_rad - 1}), de R_i = {fm(g.Ri, 0)} a R_o = {fm(g.Ro, 0)}; extremos abiertos", (V.ext[0], V.ext[3] + 6), T_N, "BOTTOM_LEFT")
        for gp in (m.info.get("grease_pts") or [])[:g.n_greaser]:
            a = math.degrees(math.atan2(gp[1], gp[0]))
            q = polar(g.Ro + 12, a)
            s.text("G", V.P(q[0], q[1], zs), T_N + 1, "MIDDLE_CENTER", bold=True)
        s.dim_ang(V.P(c3), g.Ri * V.scale * 0.8, 0, 360.0 / g.n_gr_rad, f"{fm(360 / g.n_gr_rad, 2)}° (paso)")
    allk = {k: ctx.shapes[k] for k in [key] if k in ctx.shapes}
    p.vs("planta", allk, "bottom" if face == "bot" else "top", lv=(1, 1, 1, 1), extra=(0, 0, 140, 20), draw=planta, hatch=False,
         title=f"PLANTA DE LA CARA DESLIZANTE (vista {'desde abajo' if face == 'bot' else 'desde arriba'}; ranuras y graseras G)", w=2.0, auto=dict(holes=False, verts=False, only_extents=True), mat={k: ctx.mat.get(k, "acero") for k in allk})

    def sec(V, p):
        pts = [(g.Ri, 0, zs)] + [(r, 0, zf) for r in sorted(rr)] + [(g.Ro, 0, zs)]
        for a_, b_ in zip(pts, pts[1:]):
            V.dimh(a_, b_, "bottom", 0, on=[nk], text=fm(abs(b_[0] - a_[0]), 1))
        V.dimh(pts[0], pts[-1], "bottom", 1, on=[nk], text=f"{fm(g.Ro - g.Ri, 0)} (ancho radial)")
    p.vs("sector", [nk], "bottom" if face == "bot" else "top", lv=(1, 2, 1, 1), draw=sec, hatch=False, title=f"SECTOR DE {fm(th, 1)}° CON SUS RANURAS (distancias entre ejes de ranuras sobre la bisectriz)", w=1.4,
         auto=dict(holes=True, hole_pos=False, verts=False, only_extents=True, overall=False, hole_rmin=2.5,
                   hole_txt={6.0: "Ø6 +0,2/0 (conducto de engrase)", round(P["bz_plug_d"], 1): f"Ø{fm(P['bz_plug_d'], 0)}: alojamientos de tapones (INT-102) y avellanados de tornillos (lámina del sector)",
                             round(lay.dk, 1): f"Ø{fm(lay.dk, 0)}: avellanados de tornillos y alojamientos de tapones (ver lámina del sector e INT-102)", round(lay.d_clear, 1): f"Ø{fm(lay.d_clear, 1)}: pasantes de tornillos (lámina del sector)"}, fits={}))
    r0 = rr[0] if rr else (g.Ri + g.Ro) / 2
    zlo, zhi = (-10, t + 6) if face == "bot" else (-t - 6, 10)
    p.vs("corte", [nk], "front", cut=CUT_Y, center=(r0, 0, zs), win=(-60, zlo, 60, zhi), lv=(1, 2, 1, 2), hs=0.4, maxs=5.0, title=f"CORTE A-A: RANURA CIRCUNFERENCIAL R{fm(r0, 0)} (ancho {fm(g.w_gr, 0)}, prof. {fm(g.h_gr, 1)})", w=1.0,
         auto=dict(tol={round(g.w_gr, 1): " (ancho)", round(g.h_gr, 1): " (prof.)", round(t, 1): " (e)"}, holes=False))
    rows = [["Ranuras radiales", f"{g.n_gr_rad} × a k·{fm(360 / g.n_gr_rad, 2)}°; de R{fm(g.Ri, 0)} a R{fm(g.Ro, 0)}"], ["Ranuras circunferenciales", f"{g.n_gr_circ}; R = " + ", ".join(fm(r, 0) for r in rr)],
            ["Ancho / profundidad", f"{fm(g.w_gr, 0)} / {fm(g.h_gr, 1)} mm (sección rectangular, aristas rotas 0,5×45°)"], ["Graseras", f"{g.n_greaser} a R_o − 30 (ver lámina de graseras)"], ["Área perdida", "ver núcleo (área de ranuras)"]]
    gp_ = m.info.get("grease_pts") or []
    if gp_:
        rows.append(["Conductos de engrase", f"{len(gp_[:g.n_greaser])} × Ø6 +0,2/0 a r = {fm(math.hypot(*gp_[0]), 1)} (sobre la ranura circunferencial exterior), a " + ", ".join(fm(math.degrees(math.atan2(y_, x_)) % 360, 1) + "°" for x_, y_ in gp_[:g.n_greaser])])
    p.table_block("PARÁMETROS DE LAS RANURAS (JSON del núcleo + S05)", [("Parámetro", 50, "L"), ("Valor", 120, "L")], rows)
    p.tables(ficha=False)
    p.notes([f"Lámina de características: la pieza (material, partida, masa) se define en {ctx.code(key).replace(CODE + '-', '')}; aquí solo el trazado de las ranuras.",
             f"Ranuras fresadas en la cara deslizante de cada sector ({'disco de la mesa' if g.opt == 1 else 'placa de bronce de la base'}): ancho {fm(g.w_gr, 0)} × profundidad {fm(g.h_gr, 1)} mm (S05, PROVISORIO); radiales abiertas hacia el perímetro (purga), circunferenciales a R = {', '.join(fm(r, 0) for r in rr)}.",
             f"Las {g.n_gr_rad} radiales van sobre las juntas a k·{fm(360 / g.n_gr_rad, 0)}°, una de cada {int(round((360 / g.n_gr_rad) / th))} juntas: cada radial se reparte entre los dos sectores contiguos (media ranura de {fm(g.w_gr / 2, 1)} mm en el borde de cada uno). "
             f"Hay dos tipos de sector, simétricos: impares (1, 3, …) con la media ranura en el borde inicial y pares (2, 4, …) en el borde final; las circunferenciales son iguales en todos.", "Desbarbar y romper aristas 0,5×45°; Ra ≤ 1,6 en el fondo; lapear la cara después de fresar.",
             "Las ranuras no deben cortar los avellanados de los tornillos ni la muesca del tope (distancia ≥ 3 mm)."],
            gd=[("pos", "±0,5", "A", "Posición de cada media ranura radial respecto del borde (junta) de su sector (A)"), ("pos", "±0,5", "B", "Posición de las ranuras circunferenciales respecto del eje de la mesa (B)")])
    p.build()
    return p.h


@pieza("int_bronce", "int_tapones", nogroup=True)
def sheet_int_tapones(ctx):
    g, P, m = ctx.g, ctx.P, ctx.m
    T = g.IG.get("tapones")
    if not (m.get("int_bronce") and m.get("int_tapones") and T):
        return None
    nk, th = sector_local(ctx, "int_bronce")
    ctx.local_ang("int_tapones", "int_tapones_s1", ((th / 2) if True else 0), th)
    pk = "int_tapones_s1"
    if pk not in ctx.shapes:
        return None
    p = Pieza(ctx, ["int_bronce", "int_tapones"], "INTERFAZ: PATRÓN DE TAPONES DE GRAFITO (PLANTA DEL BRONCE, TABLA DE COORDENADAS Y ALOJAMIENTO)", fmt="A1", code="INT-102")
    s = p.s
    bb = ctx.shapes[nk].BoundingBox()
    zt = bb.zmax
    t = bb.zlen
    d = T["d"]
    cs = autodim.circles3d(type("V", (), dict(shapes=ctx.shapes, view="top", uv=lambda self, p3: (p3[0], p3[1])))(), [pk], d / 2 - 0.05, d / 2 + 0.05)
    cs = sorted([(math.hypot(u, v), math.degrees(math.atan2(v, u)), u, v) for (u, v, r, loc, k_) in cs])
    p.iso_keys = [nk, pk]
    on = [nk, pk]

    def planta(V, p):
        s.line(V.P(g.Ri - 10, 0, zt), V.P(g.Ro + 10, 0, zt), "EJE")
        ah = math.radians(th * 0.35)
        V.note_pt((g.Ro * math.cos(ah), g.Ro * math.sin(ah), zt), (30, 18), f"R{fm(g.Ro, 0)}", on=[nk], dot=True)
        V.note_pt((g.Ri * math.cos(ah), g.Ri * math.sin(ah), zt), (-30, 22), f"R{fm(g.Ri, 0)}", on=[nk], dot=True)
        V.dimh((g.Ri, 0, zt), (g.Ro, 0, zt), "bottom", 0, on=[nk], text=f"{fm(g.Ro - g.Ri, 0)} (ancho radial)")
        s.text(f"Patrón escalonado (malla triangular) paso {fm(T['p'], 0)}; Ø{fm(d, 0)}; {len(cs)} tapones en este sector; origen de la malla en el eje de la mesa; sin tapones a < {fm(T['bz_edge'], 0)} mm de bordes, muesca, tornillos y ranuras.", (V.ext[0], V.ext[3] + 6), T_N, "BOTTOM_LEFT")
        if cs:
            a = cs[len(cs) // 2]
            V.note_hole((a[2], a[3], zt), d / 2, 60, f"{len(cs)} × Ø{fm(d, 0)} H7 (alojamiento), prof. {fm(m.info.get('plug_prof', 0), 1)} (70 % de e = {fm(t, 1)})", ext=40, on=on)
    p.vs("planta", on, "top", lv=(1, 2, 2, 1), extra=(30, 0, 180, 20), draw=planta, hatch=False, title=f"PLANTA DEL SECTOR 1 CON SU PATRÓN COMPLETO (sector de {fm(th, 3)}°)", w=2.0, auto=dict(holes=False, verts=False, only_extents=True), mat={nk: "bronce", pk: "grafito"})
    # (sin planta completa a 1:50: a esa escala el patrón es ilegible; las cantidades por sector van en la tabla, H-17)
    r_ = cs[len(cs) // 2] if cs else None
    if r_:
        ctx.local("int_tapones", "tap_loc", near=(r_[2], r_[3], zt - 5), r=d, shift=(-r_[2], -r_[3], 0)) if False else None
        yv = r_[3]
        p.vs("alojamiento", [nk, pk], "front", cut=((0, yv, 0), (0, 1, 0)), center=(r_[2], yv, zt - t / 2), win=(-d, -t / 2 - 8, d, t / 2 + 8), lv=(1, 2, 1, 2), hs=0.4, maxs=5.0, mins=2.0,
             title=f"CORTE: ALOJAMIENTO DEL TAPÓN Ø{fm(d, 0)} (H7 / p6, prof. 70 % t)", mat={nk: "bronce", pk: "grafito"}, w=1.2, auto=dict(on=[nk, pk], tol={}, hole_notes=False))
    rows = [[str(i + 1), fm(r, 1), fm(a, 2) + "°", fm(u, 1), fm(v, 1)] for i, (r, a, u, v) in enumerate(cs)]
    ncol = 6
    per = math.ceil(len(rows) / ncol)
    cols = [("N°", 9, "C"), ("r [mm]", 18, "R"), ("φ [°]", 18, "R"), ("x [mm]", 18, "R"), ("y [mm]", 18, "R")]
    rows4 = [sum([rows[j * per + i] if j * per + i < len(rows) else [""] * 5 for j in range(ncol)], []) for i in range(per)]
    ps0 = T["por_sector"]
    tipos = sorted(set(ps0))
    p.table_block(f"COORDENADAS DE LOS {len(cs)} TAPONES DEL SECTOR 1 (tipo con {ps0[0]} tapones; origen: eje de la mesa; φ desde la bisectriz)" + ("" if len(tipos) == 1 else
                  f". Los sectores con otra cantidad ({', '.join(str(x) for x in tipos if x != ps0[0])}) tienen el patrón del sector 2 (ver notas)"), sum([[(t_ + " " * j, w, a) for t_, w, a in cols] for j in range(ncol)], []), rows4, wide=True)
    if len(tipos) > 1:
        ctx.local_ang("int_tapones", "int_tapones_s2", 1.5 * th, th)
        cs2 = autodim.circles3d(type("V", (), dict(shapes=ctx.shapes, view="top", uv=lambda self, p3: (p3[0], p3[1])))(), ["int_tapones_s2"], d / 2 - 0.05, d / 2 + 0.05)
        cs2 = sorted([(math.hypot(u, v), math.degrees(math.atan2(v, u)), u, v) for (u, v, r, loc, k_) in cs2])
        rows2_ = [[str(i + 1), fm(r, 1), fm(a, 2) + "°", fm(u, 1), fm(v, 1)] for i, (r, a, u, v) in enumerate(cs2)]
        per2 = math.ceil(len(rows2_) / ncol)
        rows42 = [sum([rows2_[j * per2 + i] if j * per2 + i < len(rows2_) else [""] * 5 for j in range(ncol)], []) for i in range(per2)]
        p.table_block(f"COORDENADAS DE LOS {len(cs2)} TAPONES DEL SECTOR 2 (tipo con {ps0[1]} tapones; mismo origen; φ desde la bisectriz del sector 2)", sum([[(t_ + " " * j, w, a) for t_, w, a in cols] for j in range(ncol)], []), rows42, wide=True)
    ps = T["por_sector"]
    half = (len(ps) + 1) // 2
    prow = [[str(i + 1), str(ps[i]), str(i + 1 + half) if i + half < len(ps) else "", str(ps[i + half]) if i + half < len(ps) else ""] for i in range(half)]
    p.table_block(f"TAPONES POR SECTOR (cálculo): total {f(T['N_real'])} de {f(T['N_malla'])} posiciones de malla", [("Sector", 14, "C"), ("N", 14, "R"), ("Sector ", 14, "C"), ("N ", 14, "R")], prow)
    p.table_block("ALOJAMIENTO, AJUSTE Y FIJACIÓN DEL TAPÓN", [("Característica", 50, "L"), ("Valor", 120, "L")], [
        ["Diámetro / profundidad", f"Ø{fm(d, 0)} H7 / {fm(m.info.get('plug_prof', 0), 1)} mm = 70 % de e ({fm(t, 1)} mm)"], ["Tapón", f"Grafito Ø{fm(d, 0)} p6 × {fm(m.info.get('plug_prof', 0), 1)}, al ras ±0,05 con la cara deslizante (PROPUESTA)"],
        ["Fijación", "Ajuste a presión + sellador anaeróbico de resistencia media (PROPUESTA, confirmar con el proveedor del grafito)"], ["Paso / malla", f"{fm(T['p'], 0)} mm, triangular escalonada; distancia mínima a bordes {fm(T['bz_edge'], 0)} mm"],
        ["Fracción de área de grafito", f"real {fm(T['fg_real'], 3)} / ideal {fm(T['fg_ideal'], 3)}; mínimo de lubricación {fm(T['fg_min'], 2)} → {'cumple' if T['cumple_lubricacion'] else 'NO cumple (hallazgo del cálculo)'}"]])
    p.tables(ficha=False)
    p.notes([f"Lámina de características: las piezas (bronce y tapones) se definen en {ctx.code('int_bronce').replace(CODE + '-', '')} y {ctx.code('int_tapones').replace(CODE + '-', '')}; aquí solo el patrón.",
             f"Tapones de grafito Ø{fm(d, 0)} en malla triangular de paso {fm(T['p'], 0)} (S09): alojamientos taladrados Ø{fm(d, 0)} H7 con profundidad 70 % de e = {fm(m.info.get('plug_prof', 0), 1)} mm, fondo plano.",
             "Taladrar con programa CNC por tipo de sector: la malla es global (origen en el eje de la mesa), por eso los sectores alternan " + "/".join(str(x) for x in sorted(set(T["por_sector"]))) +
             " tapones (tabla «tapones por sector»); el programa de cada sector se obtiene girando la malla global al ángulo del sector y omitiendo los tapones en bordes, muesca, tornillos y ranuras (S09).",
             f"Tapones en el 3D: {f(m.info.get('n_plugs', 0))}; tapones reales según el cálculo: {f(T['N_real'])}; fracción de área de grafito {fm(T['fg_real'], 3)} frente al mínimo {fm(T['fg_min'], 2)}.",
             "Insertar los tapones después de lapear la cara; rectificar al ras con el bronce; grafito sin pintura ni sellado superficial."],
            gd=[("pos", "Ø0,2", "A", "Posición de los alojamientos respecto de la bisectriz (A) y del eje de la mesa"), ("flat", "0,05", None, "Planitud de la cara deslizante con los tapones montados")])
    p.build()
    return p.h


# ======================================================================================================= madera
@pieza("madera")
def sheet_madera(ctx):
    g, P = ctx.g, ctx.P
    zw0, tW = g.z0 + g.hd, P["t_wood"]
    if not ctx.m.get("madera"):
        return None
    Rin = g.Rt - g.t_ring
    p = Pieza(ctx, ["madera"], "CUBIERTA DE MADERA: TABLONES CONTIGUOS DE 200 mm, BOLSILLOS DE PERNOS Y ABERTURA DE LA TAPA", fmt="A1")
    s = p.s
    on = ["madera"]
    w = 200.0
    nb = int(math.ceil(Rin / w))
    edges = [i * w for i in range(0, nb + 1)]
    edges[-1] = Rin
    pins = [polar(g.R_pin, a) for a in ctx.D["pasadores"]]

    def planta(V, p):
        c3 = (0, 0, zw0 + tW)
        for x in [-e for e in edges[1:-1]] + edges[0:-1]:
            ch = math.sqrt(max(Rin ** 2 - x ** 2, 0)) * 0.999
            s.line(V.P(x, -ch, zw0 + tW), V.P(x, ch, zw0 + tW), "FANT")
        for i, (a0, a1) in enumerate(zip(edges, edges[1:])):
            xm = (a0 + a1) / 2
            s.text(str(i + 1), V.P(xm, 0 if i > 0 else 0, zw0 + tW), T_MIN + 0.5, "MIDDLE_CENTER") if False else None
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 90, 20), draw=planta, hatch=False, title="PLANTA: DISPOSICIÓN DE TABLONES (200 mm), ABERTURA Ø%s Y BOLSILLOS" % f(g.cb_D), w=2.0,
         auto=dict(fits={round(g.cb_D, 1): "H12"}, hole_rmin=20, hole_pos=False, text={round(2 * Rin, 1): f"Ø{f(2 * Rin)} −2/−4 (tablones, hasta el anillo)"}, hole_txt={round(g.washer_D + 4, 1): f"{g.N_pin} × Ø{f(g.washer_D + 4)} +2/0 × 31 +2/0 (bolsillo sobre perno y arandela), PCD Ø{f(2 * g.R_pin)}"}))

    def corte(V, p):
        pass
    p.vs("corte", ["madera", "madera_anillo"], "front", cut=CUT_Y, center=(g.Rt - 100, 0, zw0 + tW / 2), win=(-90, -tW / 2 - 8, 105, tW / 2 + 8), lv=(1, 2, 1, 2), hs=0.3, maxs=2.0, title="CORTE RADIAL (tablón y anillo)",
         mat={"madera": "madera", "madera_anillo": "acero"}, w=1.0, auto=dict(on=["madera_anillo"], tol={round(tW, 1): "", round(g.t_ring, 1): ""}))
    a0p = ctx.D["pasadores"][0]
    rot_key(ctx, "madera", "madera_P", -a0p)
    p.vs("bolsillo", ["madera_P"], "front", cut=CUT_Y, center=(g.R_pin, 0, zw0 + tW / 2), win=(-(g.washer_D / 2 + 20), -tW / 2 - 8, g.washer_D / 2 + 20, tW / 2 + 8), lv=(1, 2, 1, 2), hs=0.3, maxs=2.0,
         title="CORTE POR UN BOLSILLO (perno y arandela del pasador)", mat={"madera_P": "madera"}, w=0.9, auto=dict(on=["madera_P"], tol={}, only_extents=True))
    rows = []
    for i, (a0, a1) in enumerate(zip(edges, edges[1:])):
        xm0, xm1 = a0, a1
        L0 = 2 * math.sqrt(max(Rin ** 2 - xm0 ** 2, 0))
        L1 = 2 * math.sqrt(max(Rin ** 2 - xm1 ** 2, 0))
        npk = sum(1 for (x, y) in pins if (a0 <= abs(x) < a1) or (i == nb - 1 and abs(x) >= a0))
        cut_ap = "sí (Ø%s)" % f(g.cb_D) if a0 < g.cb_D / 2 else "no"
        rows.append([f"T{i + 1} (±)", f"{fm(a0, 0)}–{fm(a1, 0)}", fm(a1 - a0, 0), fm(max(L0, L1), 0), fm(min(L0, L1), 0), cut_ap, str(npk), "2"])
    rows.append(["TOTAL", "", "", "", "", "", str(sum(int(r[6]) for r in rows)), str(2 * nb)])
    p.table_block("TABLONES (centro del tablón, simétricos respecto del eje x; chaflán de aristas 1×45°; cortar los extremos a R = %s)" % f(Rin), [("Tablón", 20, "L"), ("x [mm]", 26, "C"), ("Ancho", 16, "R"), ("Largo máx.", 20, "R"), ("Largo mín.", 20, "R"), ("Corte abertura", 24, "C"), ("Bolsillos", 16, "R"), ("Cant", 10, "R")], rows)
    p.tables()
    p.notes([f"Tablones de madera dura de e = {f(tW)} mm y 200 mm de ancho (adoptado por el mandante), densidad ≥ {f(P['rho_wood'])} kg/m³, p adm. {fm(P['p_wood'], 1)} MPa (NCh1198; confirmar con el proveedor).",
             f"Disposición: tablones contiguos paralelos al eje y, junta central en el eje; se cortan en arco a R = {f(Rin)} (cara interior del anillo MAD-002) con holgura de montaje 2 mm; abertura central Ø{f(g.cb_D)} (tapa de inspección Ø{f(g.cb_D - 2)}).",
             f"{g.N_pin} bolsillos Ø{f(g.washer_D + 4)} × 31 sobre las cabezas de los pernos de los pasadores (S06, PROVISORIO).",
             "Fijación de los tablones a la plancha superior: PROPUESTA tornillos para madera avellanados Ø8 × 80 en 4 filas, paso 400 mm, con taladro previo (decisión del mandante: confirmar).",
             "Certificado de clasificación estructural de la madera del proveedor; humedad ≤ 15 %; tratamiento preservante a definir por el proveedor."],
            gd=[("flat", "1,0", None, "Planitud de la cara superior de la cubierta"), ("pos", "±2", "A", "Posición de los bolsillos respecto de los pasadores")])
    p.build()
    return p.h


@pieza("madera_anillo")
def sheet_madera_anillo(ctx):
    g, P = ctx.g, ctx.P
    zw0, tW = g.z0 + g.hd, P["t_wood"]
    if not ctx.m.get("madera_anillo"):
        return None
    p = Pieza(ctx, ["madera_anillo"], "CUBIERTA DE MADERA: ANILLO DE ACERO DE CONTENCIÓN", fmt="A1")
    s = p.s
    on = ["madera_anillo"]
    ids = jids(ctx, "Anillo de contención")
    p.vs("planta", on, "top", lv=(1, 1, 1, 1), extra=(0, 0, 40, 0), hatch=False, title="PLANTA DEL ANILLO", w=1.5, auto=dict(hole_rmin=20, fits={round(2 * (g.Rt - g.t_ring), 1): "H12"}, text={round(2 * g.Rt, 1): f"Ø{f(2 * g.Rt)} ±2 (D_top)"}))
    p.vs("elev", on, "front", lv=(1, 2, 2, 1), hatch=False, title="ELEVACIÓN DEL ANILLO", w=1.0, auto=dict(holes=False, tol={round(tW, 1): " ±1"}, text={round(2 * g.Rt, 1): f"Ø{f(2 * g.Rt)} ±2"}))
    p.vs("det_emp", on, "top", center=(g.Rt - g.t_ring / 2, 0, zw0 + tW), win=(-25, -25, 25, 25), lv=(1, 2, 1, 1), hatch=False, maxs=2.0, title="DETALLE B: SECCIÓN DE LA PLETINA EN PLANTA", w=0.8,
         auto=dict(holes=False, tol={round(g.t_ring, 1): " ±0,5"}))

    def corte(V, p):
        if ids:
            w_out(p, ids[0], V, (g.Rt, 0, zw0 + 1), "right", dy=-12)
    p.vs("corte", ["madera_anillo", "mesa_plancha_sup"], "front", cut=CUT_Y, center=(g.Rt - 20, 0, zw0), win=(-60, -g.tt - 8, 40, tW + 12), lv=(1, 2, 1, 2), extra=(0, 0, 115, 0), draw=corte, hs=0.3, maxs=2.0,
         title="CORTE RADIAL: ANILLO SOBRE LA PLANCHA SUPERIOR", mat={"madera_anillo": "acero", "mesa_plancha_sup": "acero"}, w=1.2, auto=dict(on=["madera_anillo", "mesa_plancha_sup"], tol={round(tW, 1): "", round(g.t_ring, 1): ""}))
    if ids:
        add_prep(p, "det_j", wd(ctx, ids[0]), t1=g.t_ring, t2=g.tt)
    p.tables(ids)
    p.notes([f"Pletina {fm(g.t_ring, 0)} × {f(tW)} rolada a Ø{f(P['D_top'])}, empalme CJP, soldada a la plancha superior con filete ambos lados ({ids[0] if ids else 'J??'}); material A572 Gr.50.",
             "Rolado en frío sobre el canto delgado; empalme con preparación en V y respaldo, esmerilado al ras (WPS-P06, PROPUESTA).", "Soldar con la mesa apoyada plana, secuencia simétrica; alivio no requerido por el espesor.",
             "El anillo contiene los tablones (MAD-001); no tiene función estructural adicional en el cálculo."],
            gd=[("perp", "0,5", "A", "Anillo perpendicular a la cara superior de la plancha (A)")])
    p.build()
    return p.h
