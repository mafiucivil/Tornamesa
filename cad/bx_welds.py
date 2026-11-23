"""Juntas soldadas de la interfaz TT300-BX en el registro único de soldaduras (hojas_base.build_welds).

Tipo, tamaño, norma, aporte, END y largos salen del bloque «bx» del JSON (bx.soldaduras, bx.disco.cjp, bx.portador.filetes / tapones).
Lo que el JSON no fija (proceso ISO 4063 y nivel ISO 5817) se rotula como PROPUESTA, igual que en el resto del juego."""
import math
from geom import fm, f, CODE
import geom


def _sc(ctx, k):
    return ctx.code(k).replace(CODE + "-", "").replace("-" + geom.REV, "") if ctx.m.get(k) else k


def _sold(X, frag):
    return next((w for w in X.get("soldaduras") or [] if frag in str(w.get("union", ""))), {})


def _end_corto(txt):
    """«VT 100 % y PT 100 % de …; RT o UT según …» → «VT 100 % · PT 100 % · RT/UT» (métodos y alcances en el orden del texto del JSON)."""
    import re
    out = []
    for m_ in re.finditer(r"\b(VT|PT|MT|RT|UT)\b(\s*\d+\s*%)?(\s+o\s+(VT|PT|MT|RT|UT)\b)?", str(txt)):
        t_ = m_.group(1) + (" " + m_.group(2).strip().replace("  ", " ") if m_.group(2) else "") + ("/" + m_.group(4) if m_.group(4) else "")
        if t_ not in out:
            out.append(t_)
    return " · ".join(out) if out else str(txt)


def _welds_lamina(ctx, add_n):
    """Modo 1 (lámina soldada): junta a tope CJP entre paneles (J30), tapones (J34) y costuras perimetrales exterior (J35) e interior (J36).
    Tipo, tamaño, aporte, norma, END, cantidades y largos: bloques disco.lamina.junta, disco.tapones, disco.costura y bx.soldaduras del JSON.
    Unión disímil 304–A572 con ER309L/E309L: WPS CALIFICADA (AWS D1.6), no precalificada; proceso ISO 4063 y nivel ISO 5817 PROPUESTOS."""
    g = ctx.g
    X = g.bx
    DSK = X["disco"]
    L, TP, CO = DSK["lamina"], DSK["tapones"], DSK["costura"]
    JN = L["junta"]
    t = float(L.get("espesor") or DSK["t"])
    cL, cM = _sc(ctx, "int_bx_lamina"), _sc(ctx, "mesa_plancha_inf")
    tbo = float(g.tbo)
    ap = JN.get("aporte") or DSK.get("aporte") or "ER309L (AWS A5.9) / E309L-16 (AWS A5.4)"
    wps_txt = "WPS CALIFICADA para la unión disímil 304 / ASTM A572 Gr. 50 con aporte 309L (AWS D1.6/D1.6M:2017; PQR con macro y doblado)"
    comun = dict(t_pre=0.0, pre_txt="sin precalentamiento del inoxidable; acero al carbono seco y ≥ 10 °C (WPS calificada)", interpase_txt="≤ 150 °C (JSON, secuencia de la lámina)",
                 corr_gmaw="GMAW pulsado ER309L Ø0,8–1,0 (Ar + 2 % CO₂), baja energía: según PQR", corr_smaw="GTAW 141 ER309L Ø1,6–2,0 (alternativa E309L-16 Ø2,5): según PQR",
                 corr_fcaw="No aplica con E71T-1: aporte 309L (E309LT1-1/-4, AWS A5.22) solo si el PQR lo califica")
    w1 = _sold(X, "panel")
    j = add_n(30, "Panel – panel de la lámina inoxidable (junta a tope CJP sobre la plancha inferior de la mesa, esmerilada a ras)", f"{cL} / {cL} (sobre {cM})",
              f"{w1.get('tipo') or JN['tipo']} ({w1.get('norma') or JN['norma']})", "square", t=t, groove=True,
              prep=f"A tope recto (corte láser o cizalla), separación de raíz 0–1 mm, sobre respaldo permanente (plancha inferior de la mesa, {fm(tbo, 0)} mm); líneas y = {', '.join(fm(v, 0) for v in JN.get('lineas_y') or [0])}",
              prep_txt="", nivel="ISO 5817-B", end=_end_corto(JN["END"]), wps=13, len_total=float(JN["largo"]), aporte=ap, proc="141 / 135 (PROPUESTA)", nota=JN["acabado"])
    j.update(inox_cjp=True, backing="M", backing_txt="M: respaldo permanente = plancha inferior de la mesa", end_txt=JN["END"], acabado=JN["acabado"],
             fam_txt=f"Ranura a tope recta (I) CJP de lámina inoxidable de {fm(t, 0)} sobre respaldo permanente de acero al carbono; aporte {ap}; {wps_txt}", **comun)
    sw = _sold(X, "tapones")
    d, rel = float(TP["d"]), float(TP.get("relleno") or t)
    w = add_n(34, f"Lámina inoxidable – plancha inferior de la mesa: tapones Ø{fm(d, 0)} (relleno {fm(rel, 1)} = t), esmerilados a ras y pulidos", f"{cL} / {cM}",
              f"{sw.get('tipo') or TP['tipo']} ({sw.get('norma') or TP['norma'].split(';')[0]})", "plug", t=rel, groove=True,
              prep=f"Agujero Ø{fm(d, 1)} taladrado o punzonado en la lámina (pared recta, sin rebaba); lámina apretada contra la plancha (separación ≤ {fm(float((DSK.get('despegue_panel') or {}).get('g0') or 0.2), 2)} mm)",
              prep_txt="", nivel="ISO 5817-B", end="VT 100 % · PT 100 %", wps=17, len_total=0.0, aporte=ap, proc="141 / 135 (PROPUESTA)",
              nota=f"FU tapón {fm(float(TP['V_max']) / float(TP['cap']), 2)} (V {fm(float(TP['V_max']) / 1000, 1)} / {fm(float(TP['cap']) / 1000, 1)} kN; núcleo BX)")
    w.update(size_txt=f"Ø{fm(d, 0)}", garganta=f"tapón Ø{fm(d, 0)}, relleno {fm(rel, 1)}", cateto="—", origen="núcleo BX (disco.tapones)", len_txt=f"{TP['n']} tapones",
             pasadas=max(1, math.ceil(rel / 2.0)), tapon_lamina=dict(d=d, rel=rel, t=t, tbo=tbo),
             fam_txt=f"Soldadura de tapón en agujero Ø{fm(d, 0)} de la lámina de {fm(t, 0)} (relleno = t) sobre acero al carbono, fundida a la plancha y esmerilada a ras (AISC 360-22 §J2.3; AWS D1.3 como referencia de detalle en lámina ≤ 4,8 mm); {wps_txt}; PROBETA DE TAPÓN antes de producción", **comun)
    zc = float(CO["w"])
    for jn, lado, frag in ((35, "exterior", "costura exterior"), (36, "interior", "costura interior")):
        sw = _sold(X, frag)
        w = add_n(jn, f"Lámina inoxidable – plancha inferior de la mesa: costura perimetral {lado} (R{fm(CO[lado]['R'], 0)})", f"{cL} / {cM}",
                  f"{sw.get('tipo') or CO['tipo']} ({sw.get('norma') or 'AWS D1.6/D1.6M:2017'})", "fillet", core=(zc, "núcleo BX (disco.costura.w)"), t=t,
                  len_total=float(CO[lado]["largo"]), wps=18, end="VT 100 % · PT 100 %", nivel="ISO 5817-B", contorno=True, aporte=ap, proc="141 / 135 (PROPUESTA)",
                  nota="por retroceso (backstep) en tramos ≤ 150 mm; sella el intersticio lámina–plancha")
        w.update(fam_txt=f"Filete z{fm(zc, 0)} de lámina inoxidable de {fm(t, 0)} sobre acero al carbono (canto de la lámina), aporte {ap}; {wps_txt}", **comun)


def welds(ctx, add_n):
    g = ctx.g
    X = g.bx
    DSK, POR = X["disco"], X["portador"]
    import bx3d
    if bx3d.modo_lamina(X):
        _welds_lamina(ctx, add_n)
        _welds_portador(ctx, add_n)
        return
    cjp = DSK["cjp"]
    t_d, t_c = float(DSK["t"]), float(POR["t"])
    w1 = _sold(X, "semidisco")
    j = add_n(30, "Semidisco – semidisco del disco de la mesa (CJP sobre el eje x, esmerilada a ras)", f"{_sc(ctx, 'int_bx_disco_mesa')} / {_sc(ctx, 'int_bx_disco_mesa')}",
              f"{cjp['tipo']} ({cjp['norma']})", "V", t=t_d, groove=True,
              prep="V 60°, raíz 2 mm, cara de raíz 1 mm; respaldo cerámico retirado (o doble V sin respaldo con resanado), " + str(w1.get("norma", cjp["norma"])),
              prep_txt="60°", nivel="ISO 5817-B", end=_end_corto(cjp["END"]), wps=13, len_total=float(cjp["largo"]), aporte=cjp["aporte"], proc="141 / 135 (PROPUESTA)",
              nota=cjp["acabado"])
    j.update(inox_cjp=True, t_pre=0.0, backing="MR", backing_txt="MR: respaldo cerámico retirado", end_txt=cjp["END"],
             fam_txt=f"{cjp['tipo']}; {cjp['norma']}; aporte {cjp['aporte']}", pre_txt="sin precalentamiento (acero inoxidable; interpase y calor aportado según la WPS calificada)",
             interpase_txt="≤ 150 °C (inoxidable; confirmar en la WPS)", corr_gmaw="Según WPS calificada (" + cjp["norma"] + ")", corr_smaw="Según WPS calificada", corr_fcaw="No aplica con E71T-1 (aporte inoxidable según WPS calificada)", acabado=cjp["acabado"])
    _welds_portador(ctx, add_n)


def _welds_portador(ctx, add_n):
    g = ctx.g
    X = g.bx
    POR = X["portador"]
    t_c = float(POR["t"])
    wF = POR["filetes"]
    zc = float(wF["w"])
    for jn, lado, frag in ((31, "exterior", "borde exterior"), (32, "interior", "borde interior")):
        sw = _sold(X, frag)
        add_n(jn, f"Portador de pastillas – plancha base, borde {lado} (R{fm(wF[lado]['R'], 0)})", f"{_sc(ctx, 'int_bx_portador')} / {_sc(ctx, 'base_plancha')}",
              f"{sw.get('tipo', f'filete z{fm(zc, 0)} continuo')} ({sw.get('norma', '')})", "fillet", core=(zc, f"núcleo BX (bx.portador.filetes.w; {sw.get('norma', 'AWS D1.1 Tabla 7.7')})"),
              t=max(t_c, g.tb), len_total=float(wF[lado]["largo"]), wps=14, end="VT 100 % · MT 100 %", contorno=True)
    TP = POR.get("tapones") or {}
    if TP.get("n"):
        sw = _sold(X, "agujeros de soldadura")
        add_n(33, "Portador de pastillas – plancha base: filete interior en los agujeros de soldadura", f"{_sc(ctx, 'int_bx_portador')} / {_sc(ctx, 'base_plancha')}",
              f"{sw.get('tipo', '')} ({sw.get('norma', '')})", "fillet", core=(float(TP["w"]), "núcleo BX (bx.portador.tapones.w)"), t=max(t_c, g.tb),
              len_total=float(TP["n"]) * float(sw.get("largo_cada", 0.0)), wps=14, end="VT 100 % · MT 100 %", contorno=True, nota=TP.get("acabado", ""))
