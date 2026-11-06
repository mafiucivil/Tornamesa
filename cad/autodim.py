"""Acotado automático verificado: cadenas de cotas entre los vértices visibles de una vista (y los centros de agujeros), cotas totales,
diámetros y llamadas «n × Ø… PCD …». Los puntos salen del sólido 3D (vértices de las aristas visibles o de la sección) y cada cota
pasa por View.dim, es decir, queda registrada y verificada contra el modelo (extremos sobre la superficie / eje de cilindro real)."""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
import vistas
from vistas import COTAS, numtxt
from draw import tw, T_N
from geom import fm, f


def _cluster(vals, tol=0.06):
    out = []
    for v in sorted(vals, key=lambda t: t[0]):
        if out and abs(v[0] - out[-1][0]) <= tol:
            out[-1][1].append(v)
        else:
            out.append((v[0], [v]))
    return out


def visible_points(V, keys, tol_vis=0.35):
    """[(p3, u, v, key)] vértices visibles (o de la sección) de la vista, en coordenadas de pantalla relativas a 'center'."""
    lines = [LineString(pl) for pl in V.vis if len(pl) >= 2]
    tree = STRtree(lines) if lines else None
    keep = None
    if V.cut:
        pp, nd = V.cut
        keep = (pp, nd)
    pts = []
    seen = set()
    for k in keys:
        shp = V.shapes.get(k)
        if shp is None:
            continue
        for vx in shp.Vertices():
            p3 = (vx.X, vx.Y, vx.Z)
            if keep:
                if sum((a - b) * c for a, b, c in zip(p3, keep[0], keep[1])) < -0.01:
                    continue
            u, v = V.uv(p3)
            if V.win and not (V.win[0] - 0.01 <= u <= V.win[2] + 0.01 and V.win[1] - 0.01 <= v <= V.win[3] + 0.01):
                continue
            key = (round(u, 2), round(v, 2))
            if key in seen:
                continue
            if tree is not None:
                q = Point(u, v)
                idx = tree.nearest(q)
                if lines[int(idx)].distance(q) > tol_vis:
                    continue
            seen.add(key)
            pts.append((p3, u, v, k))
    for (k, p3) in V.secv:
        if k not in keys:
            continue
        u, v = V.uv(p3)
        if V.win and not (V.win[0] - 0.01 <= u <= V.win[2] + 0.01 and V.win[1] - 0.01 <= v <= V.win[3] + 0.01):
            continue
        key = (round(u, 2), round(v, 2))
        if key in seen:
            continue
        seen.add(key)
        pts.append((p3, u, v, k))
    return pts


def circles3d(V, keys, rmin=0.0, rmax=1e9):
    """Cilindros de eje paralelo a la dirección de mirada: [(u, v, r, loc3)] sin duplicados."""
    d, _, _ = vistas.basis(V.view)
    out = {}
    for k in keys:
        if k not in V.shapes:
            continue
        for (rr, loc, dr) in COTAS.cylinders(k):
            if abs(abs(sum(a * b for a, b in zip(dr, d))) - 1) > 1e-3 or not (rmin <= rr <= rmax):
                continue
            u, v = V.uv(loc)
            out[(round(u, 1), round(v, 1), round(rr, 2))] = (u, v, rr, loc, k)
    return sorted(out.values(), key=lambda t: (t[2], t[1], t[0]))


def _thin(items, scale, text_of, minw=6.0, protect=()):
    """Elimina ordenadas cuyo tramo en papel no admite el texto de la cota (conserva los extremos y los protegidos)."""
    items = list(items)
    while len(items) > 2:
        worst, wi = 1e9, None
        for i in range(len(items) - 1):
            gap = (items[i + 1][0] - items[i][0]) * scale
            need = max(minw, tw(text_of(items[i + 1][0] - items[i][0]), T_N) + 3.0)
            r = gap / need
            if r < 1.0 and r < worst:
                worst, wi = r, i
        if wi is None:
            break
        a, b = wi, wi + 1
        cand = [x for x in (a, b) if 0 < x < len(items) - 1 and items[x][0] not in protect]
        if not cand:
            cand = [x for x in (a, b) if 0 < x < len(items) - 1]
        if not cand:
            break
        if len(cand) == 2:
            ga = items[a + 1][0] - items[a - 1][0]
            gb = items[b + 1][0] - items[b - 1][0]
            x = a if ga <= gb else b
        else:
            x = cand[0]
        items.pop(x)
    return items


def auto_dims(V, on=None, h="bottom", v="right", holes=True, verts=True, tol=None, text=None, skip_u=(), skip_v=(), maxn=9, overall=True, hole_rmin=1.5,
              fits=None, hside=None, vside=None, hole_notes=True, max_levels=2, ang0=35, hole_ext=14.0, only_extents=False, lvl0=None, pitch_txt=None, hole_txt=None, minw=6.0, hole_pos=True, rev=None, rev_side="top", rev_max=6, vtol=None):
    """Cotas automáticas de la vista V. tol: {valor_redondeado: sufijo} (p. ej. {20.0: ' ±0,5'}); text: {valor: texto completo}; fits: {Ø: 'H7'} para diámetros.
    Devuelve el nº de cotas dibujadas."""
    on = on or V.keys
    tol = tol or {}
    text = text or {}
    fits = fits or {}
    n0 = len(COTAS.rows)
    pts = visible_points(V, on) if verts else []
    cs = circles3d(V, on, hole_rmin) if holes else []
    cs = [c for c in cs if (not V.win) or (V.win[0] < c[0] < V.win[2] and V.win[1] < c[1] < V.win[3])]

    def label(val, kind="L"):
        r1 = round(val, 1)
        if r1 in text:
            return text[r1]
        return numtxt(val) + tol.get(r1, "")

    def build(axis, side, skip):
        """Lista [(ordenada, p3, virt_r)] de la cadena sobre el eje 'axis' (0 = u, 1 = v)."""
        rep = {}
        for (p3, u, v_, k) in pts:
            o = u if axis == 0 else v_
            other = v_ if axis == 0 else u
            rep.setdefault(round(o / 0.06), []).append((o, other, p3, None))
        for (u, v_, r, loc, k) in cs:
            if hole_pos:
                o = u if axis == 0 else v_
                other = v_ if axis == 0 else u
                rep.setdefault(round(o / 0.06), []).append((o, other, loc, r))
        items = []
        for key, lst in rep.items():
            if any(abs(lst[0][0] - sk) < 0.06 for sk in skip):
                continue
            # prefiere un vértice real; punto más cercano al lado de la cota
            vv = [q for q in lst if q[3] is None] or lst
            if side in ("bottom", "left"):
                q = min(vv, key=lambda t: t[1])
            else:
                q = max(vv, key=lambda t: t[1])
            items.append((q[0], q[2], q[3]))
        items.sort(key=lambda t: t[0])
        return items

    def run(axis, side, skip, lvl):
        items = build(axis, side, skip)
        if len(items) < 2:
            return lvl
        lo, hi = items[0], items[-1]
        txt_of = lambda d: label(d)
        if only_extents:
            chain = [lo, hi]
        else:
            prot = {lo[0], hi[0]}
            chain = _thin(items, V.scale, txt_of, minw=minw, protect=prot)
            while len(chain) > maxn:
                # elimina el punto interior cuyos tramos vecinos suman menos (el resto queda con tramos holgados)
                k = min(range(1, len(chain) - 1), key=lambda i: chain[i + 1][0] - chain[i - 1][0])
                chain.pop(k)
        lv = lvl
        dimf = V.dimh if axis == 0 else V.dimv
        if len(chain) > 2 or (len(chain) == 2 and not overall):
            for a, b in zip(chain, chain[1:]):
                val = abs(b[0] - a[0])
                if val < 0.2:
                    continue
                dimf(a[1], b[1], side, lv, on=on, text=label(val), virt_a=a[2], virt_b=b[2])
            lv += 1
        if overall or len(chain) <= 2:
            if len(chain) > 2 or len(chain) == 2:
                val = abs(hi[0] - lo[0])
                dimf(lo[1], hi[1], side, lv, on=on, text=label(val), virt_a=lo[2], virt_b=hi[2])
        return lv + 1

    if rev is not None:
        # pieza de revolución: cotas de diámetro entre puntos simétricos respecto del eje (rev = (x, y) del eje)
        ax, ay = rev
        ua = V.uv((ax, ay, 0.0))[0]
        rs = {}
        for (p3, u, v_, k) in pts:
            r = abs(u - ua)
            if r > 0.6:
                rs.setdefault(round(r, 1), []).append((v_, p3))
        for (u, v_, r, loc, k) in cs:
            pass
        side = rev_side
        lv = V.lv[side] if lvl0 is None else lvl0
        radii = sorted(rs)
        # descarta los diámetros demasiado próximos en papel para apilarlos (siempre apila: un nivel por diámetro)
        radii = radii[-rev_max:] if len(radii) > rev_max else radii
        ya = text or {}
        for r in radii:
            lst = rs[r]
            v_, p3 = (max(lst, key=lambda t: t[0]) if side == "top" else min(lst, key=lambda t: t[0]))
            a3 = p3
            b3 = (2 * ax - p3[0], 2 * ay - p3[1], p3[2])
            d = 2 * r
            r1 = round(d, 1)
            fit = fits.get(r1) or fits.get(round(d))
            if r1 in ya:
                t_ = ya[r1]
            elif fit:
                import iso286
                try:
                    t_ = f"Ø{numtxt(d)} {fit} ({iso286.fmt_dev(d, fit)})"
                except Exception:
                    t_ = f"Ø{numtxt(d)} {fit}"
            else:
                t_ = f"Ø{numtxt(d)}" + tol.get(r1, "")
            V.dimh(a3, b3, side, lv, on=on, text=t_)
            lv += 1
        vside_ = vside or v
        run(1, vside_, skip_v, V.lv[vside_] if lvl0 is None else lvl0)
        return len(COTAS.rows) - n0
    run(0, hside or h, skip_u, V.lv[hside or h] if lvl0 is None else lvl0)
    run(1, vside or v, skip_v, V.lv[vside or v] if lvl0 is None else lvl0)
    # --- diámetros / agujeros ---
    if holes and cs and hole_notes:
        notes_holes(V, cs, on, fits=fits, ang0=ang0, ext=hole_ext, pitch_txt=pitch_txt, hole_txt=hole_txt)
    return len(COTAS.rows) - n0


def notes_holes(V, cs, on, fits=None, ang0=35, ext=14.0, pitch_txt=None, center=None, hole_txt=None):
    """Una llamada por grupo de agujeros iguales: «n × Ø d (ajuste)» y, si están en un círculo de paso, «PCD Ø D, paso …°»."""
    fits = fits or {}
    groups = {}
    for c in cs:
        groups.setdefault(round(c[2], 2), []).append(c)
    x0, y0, x1, y1 = V.ext
    cxp, cyp = (x0 + x1) / 2, (y0 + y1) / 2
    used = []
    for gi, (r, lst) in enumerate(sorted(groups.items(), reverse=True)):
        d = 2 * r
        fit = fits.get(round(d, 1)) or fits.get(round(d))
        base = f"Ø{numtxt(d)}"
        if fit:
            import iso286
            try:
                base += f" {fit} ({iso286.fmt_dev(d, fit)})"
            except Exception:
                base += f" {fit}"
        n = len(lst)
        txt = base if n == 1 else f"{n} × {base}"
        if hole_txt and (hole_txt.get(round(d, 1)) or hole_txt.get(round(d))):
            txt = hole_txt.get(round(d, 1)) or hole_txt.get(round(d))
        if n >= 3 and not (hole_txt and (hole_txt.get(round(d, 1)) or hole_txt.get(round(d)))):
            # círculo de paso respecto del origen del modelo (centro de la vista)
            rs = [math.hypot(c[0], c[1]) for c in lst]
            if max(rs) - min(rs) < 0.2 and rs[0] > 5:
                txt += f", PCD Ø{numtxt(2 * rs[0])}"
                angs = sorted(math.degrees(math.atan2(c[1], c[0])) % 360 for c in lst)
                dif = [(b - a) for a, b in zip(angs, angs[1:] + [angs[0] + 360])]
                if max(dif) - min(dif) < 0.05:
                    txt += f", paso {fm(dif[0], 3)}°"
        # agujero representativo y dirección de salida (radial desde el centro de la vista)
        best = None
        for c in lst:
            P = V.P(c[3])
            ang = math.degrees(math.atan2(P[1] - cyp, P[0] - cxp)) if math.hypot(P[0] - cxp, P[1] - cyp) > 8 else (40.0, 220.0, 130.0, 310.0)[gi % 4]
            score = sum(min(abs(((ang - a + 180) % 360) - 180) for a in [u_]) for u_ in used[-1:]) if used else 0
            if best is None or score > best[0]:
                best = (score, c, ang)
        _, c, ang = best
        P0 = V.P(c[3])
        # Si el centro de la vista es el centro del agujero, o varios grupos coinciden, separa las direcciones
        for a in used:
            if abs(((ang - a + 180) % 360) - 180) < 12 and math.hypot(P0[0] - cxp, P0[1] - cyp) > 8:
                ang += 24
        used.append(ang)
        # distancia hasta salir de la caja de la vista (papel)
        P = V.P(c[3])
        rpx = c[2] * V.scale
        e = ext
        a = math.radians(ang)
        dx, dy = math.cos(a), math.sin(a)
        tmax = 1e9
        for bound, comp, d_ in ((x1, 0, dx), (x0, 0, dx), (y1, 1, dy), (y0, 1, dy)):
            if abs(d_) > 1e-6:
                t = (bound - (P[0] if comp == 0 else P[1])) / d_
                if t > rpx:
                    tmax = min(tmax, t)
        near_c = math.hypot(P[0] - cxp, P[1] - cyp) < 0.2 * max(x1 - x0, y1 - y0)
        e = (ext + 12.0 * (gi // 4)) if near_c else (max(ext, (tmax - rpx) + 8) if tmax < 1e8 else ext)
        e = min(e, 160)
        qx = P[0] + (rpx + e) * dx
        box = getattr(V, "box", None)
        lines = None
        if box is not None:
            avail = (box[2] - qx - 2) if dx >= 0 else (qx - box[0] - 2)
            if tw(txt, T_N) > avail:
                from draw import wrapw
                lines = wrapw(txt, max(avail, 50.0), T_N)
        V.note_hole(c[3], c[2], ang, txt, ext=e, on=on, lines=lines)
