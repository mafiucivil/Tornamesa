"""Juntas soldadas de la interfaz TT300-BX en el registro único de soldaduras (hojas_base.build_welds).

Tipo, tamaño, norma, aporte, END y largos salen del bloque «bx» del JSON (bx.soldaduras, bx.disco.cjp, bx.portador.filetes / tapones).
Lo que el JSON no fija (proceso ISO 4063 y nivel ISO 5817) se rotula como PROPUESTA, igual que en el resto del juego."""
from geom import fm, f, CODE


def _sc(ctx, k):
    return ctx.code(k).replace(CODE + "-", "").replace("-C", "") if ctx.m.get(k) else k


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


def welds(ctx, add_n):
    g = ctx.g
    X = g.bx
    DSK, POR = X["disco"], X["portador"]
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
             interpase_txt="≤ 150 °C (inoxidable; confirmar en la WPS)", corr_gmaw="Según WPS calificada (" + cjp["norma"] + ")", corr_smaw="Según WPS calificada", acabado=cjp["acabado"])
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
