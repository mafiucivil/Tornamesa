"""Modelo 3D CadQuery de la tornamesa 500 tf (variantes U y S)."""
import math
import cadquery as cq
import params as P

C = {
    "steel": cq.Color(0.55, 0.57, 0.60), "disc": cq.Color(0.98, 0.78, 0.10),
    "base": cq.Color(0.20, 0.33, 0.55), "bronze": cq.Color(0.72, 0.50, 0.20),
    "pin": cq.Color(0.35, 0.35, 0.38), "uhmw": cq.Color(0.95, 0.95, 0.92),
    "inox": cq.Color(0.82, 0.84, 0.87), "nbr": cq.Color(0.08, 0.08, 0.08),
    "cyl": cq.Color(0.85, 0.15, 0.12), "graph": cq.Color(0.25, 0.25, 0.25),
}


def cyl(r, h, x=0, y=0, z=0):
    return cq.Workplane("XY").workplane(offset=z).center(x, y).circle(r).extrude(h)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def base_plate(v):
    b = cq.Workplane("XY").box(P.BX, P.B, P.TB, centered=(True, True, False))
    b = b.cut(cyl(P.D_PIV / 2, P.TB))
    for sx in (1, -1):   # ranuras 40 H8 x 10 para guías embutidas pos 22
        b = b.cut(box(sx * P.X_CYL - P.RAIL_W / 2, sx * P.X_CYL + P.RAIL_W / 2, -P.RAIL_L / 2, P.RAIL_L / 2, P.TB - 10, P.TB))
    if v["kind"] == "U":
        for _, _, x, y in P.pad_positions():
            b = b.cut(cyl(P.D_POCKET / 2, P.H_POCKET, x, y, P.TB - P.H_POCKET))
            b = b.cut(cyl(5, P.TB, x, y, 0))
    return b


def bracket(v, sx, sy):
    """Ménsula en (sx*X_CYL, sy*Y_BRK); mejillas paralelas a Y, respaldo hacia el borde de la base."""
    h = v["H_cheek"]
    x0, y0 = sx * P.X_CYL, sy * P.Y_BRK
    w = None
    for side in (-1, 1):
        xc = x0 + side * (P.CHEEK_GAP / 2 + P.CHEEK_T / 2)
        ch = cq.Workplane("XY").box(P.CHEEK_T, P.CHEEK_L, h, centered=(True, True, False)).translate((xc, y0, P.TB))
        w = ch if w is None else w.union(ch)
    yb = y0 + sy * (P.CHEEK_L / 2 + P.BACK_T / 2)
    back = cq.Workplane("XY").box(P.CHEEK_GAP + 2 * P.CHEEK_T, P.BACK_T, h, centered=(True, True, False)).translate((x0, yb, P.TB))
    w = w.union(back)
    hole = cq.Workplane("YZ").workplane(offset=x0 - 200).center(y0, v["z_axis"]).circle((P.D_PIN_CYL + 1) / 2).extrude(400)
    return w.cut(hole)


def rails(v):
    r = None
    for sx in (1, -1):
        k = box(sx * P.X_CYL - P.RAIL_W / 2, sx * P.X_CYL + P.RAIL_W / 2, -P.RAIL_L / 2, P.RAIL_L / 2, P.TB - 10, P.TB + P.RAIL_H)
        r = k if r is None else r.union(k)
    return r


def lug(v, sx, sy):
    x0 = sx * P.LUG_X
    y1 = sy * (P.B / 2 - P.LUG_L / 2)
    l = cq.Workplane("XY").box(P.LUG_T, P.LUG_L, P.LUG_H, centered=(True, True, False)).translate((x0, y1, P.TB))
    l = l.edges("|X and >Z").fillet(60)
    hole = cq.Workplane("YZ").workplane(offset=x0 - 50).center(y1, P.TB + 100).circle(P.LUG_HOLE / 2).extrude(100)
    return l.cut(hole)


def disc_parts(v):
    """Disco cajón: dict de sub-piezas (4a..4f)."""
    zb, zt = v["z_disc_bot"], v["z_disc_top"]
    R = P.D_DISC / 2
    def plate(z0, t):
        p = cyl(R, t, z=z0).cut(cyl(P.HUB_D / 2, t, z=z0))
        for _, x, y in P.idx_positions():
            p = p.cut(cyl(P.D_IDX_HOLE / 2, t, x, y, z0))
        return p
    bot = plate(zb, P.TP_BOT)
    top = plate(zt - P.TP_TOP, P.TP_TOP)
    for a in P.M30_ANG:
        x, y = P.R_M30 * math.cos(math.radians(a)), P.R_M30 * math.sin(math.radians(a))
        top = top.cut(cyl(13.25, P.TP_TOP, x, y, zt - P.TP_TOP))
    hub = cyl(P.HUB_D / 2, P.TD, z=zb)
    hub = hub.cut(cyl(P.D_BUJE_EXT / 2, P.L_BUJE, z=zb))
    hub = hub.cut(cyl(80, P.TD, z=zb))
    hub = hub.cut(cyl(P.D_CB / 2, P.H_CB, z=zt - P.H_CB))
    z0, h = zb + P.TP_BOT, P.GAP
    rings = None
    for r in P.RING_R:
        k = cyl(r + P.RING_T / 2, h, z=z0).cut(cyl(r - P.RING_T / 2, h, z=z0))
        rings = k if rings is None else rings.union(k)
    ribs = None
    for k in range(P.N_RIB):
        a = 360.0 / P.N_RIB * k
        rb = box(P.HUB_D / 2 - 2, P.RIB_R1, -P.RIB_T / 2, P.RIB_T / 2, z0, z0 + h).rotate((0, 0, 0), (0, 0, 1), a)
        ribs = rb if ribs is None else ribs.union(rb)
    bars = None
    for _, x, y in P.idx_positions():
        k = cyl(P.D_BAR / 2, P.TD, x, y, zb)
        bars = k if bars is None else bars.union(k)
    return {"4a": top, "4b": bot, "4c": hub, "4d": rings, "4e": ribs, "4f": bars}


def disc(v):
    d = disc_parts(v)
    s = d["4a"]
    for k in ("4b", "4c", "4d", "4e", "4f"):
        s = s.union(d[k])
    return s


def pivot(v):
    p = cyl(P.D_PIV / 2, v["L_piv"])
    p = p.faces("<Z").chamfer(5)
    for k in range(P.N_BOLT):
        a = math.radians(30 + 60 * k)
        p = p.cut(cyl(8.6, 40, P.BOLT_PCD / 2 * math.cos(a), P.BOLT_PCD / 2 * math.sin(a), v["L_piv"] - 40))
    return p


def bushing(v):
    return cyl(P.D_BUJE_EXT / 2, P.L_BUJE, z=v["z_disc_bot"]).cut(cyl(P.D_PIV / 2, P.L_BUJE, z=v["z_disc_bot"]))


def cap(v):
    c = cyl(P.D_TAPA / 2, P.T_TAPA, z=v["z_piv_top"])
    for k in range(P.N_BOLT):
        a = math.radians(30 + 60 * k)
        x, y = P.BOLT_PCD / 2 * math.cos(a), P.BOLT_PCD / 2 * math.sin(a)
        c = c.cut(cyl(11, P.T_TAPA, x, y, v["z_piv_top"])).cut(cyl(16.5, 13, x, y, v["z_piv_top"] + P.T_TAPA - 13))
    return c


def bolts(v):
    s = None
    for k in range(P.N_BOLT):
        a = math.radians(30 + 60 * k)
        x, y = P.BOLT_PCD / 2 * math.cos(a), P.BOLT_PCD / 2 * math.sin(a)
        b = cyl(10, 45, x, y, v["z_piv_top"] + P.T_TAPA - 13 - 32).union(cyl(15, 20, x, y, v["z_piv_top"] + P.T_TAPA - 13))
        s = b if s is None else s.union(b)
    return s


def seal(v):
    r = P.D_DISC / 2
    z0 = P.TB
    h = v["z_disc_bot"] + P.TP_BOT - z0
    rub = cyl(r + P.SEAL_T, h, z=z0).cut(cyl(r, h, z=z0))
    zb = v["z_disc_bot"] + P.TP_BOT / 2 - P.BAR_W / 2
    bar = cyl(r + P.SEAL_T + P.BAR_T, P.BAR_W, z=zb).cut(cyl(r + P.SEAL_T, P.BAR_W, z=zb))
    return rub, bar


def pads():
    s = None
    for _, _, x, y in P.pad_positions():
        c = cyl(P.D_PAD / 2, P.T_PAD, x, y, P.TB - P.H_POCKET)
        s = c if s is None else s.union(c)
    return s


def inox(v, rin, rout):
    z = v["z_disc_bot"] - P.INOX_T
    return cyl(rout / 2, P.INOX_T, z=z).cut(cyl(rin / 2, P.INOX_T, z=z))


def push_geom(v):
    """Lado derecho (x>0), empuje +Y, trinquete tomando la barra a -5°. Devuelve coordenadas clave."""
    a = math.radians(-P.BAR_ANG0)
    xb, yb = P.R_BAR * math.cos(a), P.R_BAR * math.sin(a)
    return xb, yb, yb - P.EYE_OFF


def push_set(v, sx):
    xb, yb, ye = push_geom(v)
    za = v["z_axis"]
    x0, x1 = P.SHOE_X0, P.SHOE_X1
    xc = P.X_CYL
    yf, yr = yb + P.SHOE_FRONT, yb + P.SHOE_FRONT - P.SHOE_L
    shoe = box(x0, x1, yr, yf, P.TB, v["shoe_top"])
    shoe = shoe.cut(box(xc - 20.5, xc + 20.5, yr, yf, P.TB, P.TB + P.RAIL_H + 1))
    shoe = shoe.cut(box(x0, x1, yb - P.PAWL_W - 0.5, yb + 0.5, za - P.PAWL_H / 2 - 0.5, za + P.PAWL_H / 2 + 0.5))
    shoe = shoe.cut(box(xc - 40, xc + 40, yr, yr + 110, za - 65, v["shoe_top"]))
    shoe = shoe.cut(cq.Workplane("YZ").workplane(offset=x0 - 5).center(ye, za).circle((P.D_PIN_CYL + 1) / 2).extrude(x1 - x0 + 10))
    pawl = box(P.PAWL_TIP, P.PAWL_TIP + P.PAWL_L, yb - P.PAWL_W, yb, za - P.PAWL_H / 2, za + P.PAWL_H / 2)
    pawl = pawl.cut(cyl(P.SEAT_R, P.PAWL_H, xb, yb, za - P.PAWL_H / 2))
    wedge = (cq.Workplane("XY").workplane(offset=za - P.PAWL_H / 2)
             .polyline([(P.PAWL_TIP - 1, yb - P.PAWL_W - 1), (P.PAWL_TIP + 60, yb - P.PAWL_W - 1), (P.PAWL_TIP - 1, yb - P.PAWL_W + 35)]).close().extrude(P.PAWL_H))
    pawl = pawl.cut(wedge)
    ybp = -P.Y_BRK
    def ycyl(r, y0, y1):
        lo, hi = min(y0, y1), max(y0, y1)
        return cq.Workplane("XZ").workplane(offset=-hi).center(xc, za).circle(r).extrude(hi - lo)
    body = ycyl(P.D_CYL / 2, ybp + 70, ybp + 70 + 300)
    rod = ycyl(P.D_ROD / 2, ybp + 370, ye - 50)
    eyes = None
    for y_ in (ybp, ye):
        e = cq.Workplane("YZ").workplane(offset=xc - P.EYE_W / 2).center(y_, za).circle(P.EYE_D / 2).extrude(P.EYE_W)
        eyes = e if eyes is None else eyes.union(e)
    cylinder = body.union(rod).union(eyes)
    pins = None
    for y_, ln in ((ybp, P.CHEEK_GAP + 2 * P.CHEEK_T + 40), (ye, x1 - x0 + 40)):
        pp = cq.Workplane("YZ").workplane(offset=xc - ln / 2).center(y_, za).circle(P.D_PIN_CYL / 2).extrude(ln)
        pins = pp if pins is None else pins.union(pp)
    cylinder = cylinder.cut(pins)
    out = [shoe, pawl, cylinder, pins]
    if sx < 0:
        out = [o.rotate((0, 0, 0), (0, 0, 1), 180) for o in out]
    return out


def build(kind):
    v = P.variant(kind)
    parts = []  # (pos, name, shape, color)
    b = base_plate(v)
    parts.append((1, "Placa base", b, C["base"]))
    brk = None
    for sx in (1, -1):
        for sy in (1, -1):
            k = bracket(v, sx, sy)
            brk = k if brk is None else brk.union(k)
    parts.append((2, "Mensulas de reaccion", brk, C["base"]))
    lg = None
    for sx in (1, -1):
        for sy in (1, -1):
            k = lug(v, sx, sy)
            lg = k if lg is None else lg.union(k)
    parts.append((3, "Orejas de izaje", lg, C["base"]))
    parts.append((4, "Disco giratorio", disc(v), C["disc"]))
    parts.append((5, "Pivote", pivot(v), C["pin"]))
    parts.append((6, "Buje bronce", bushing(v), C["bronze"]))
    parts.append((7, "Tapa retenedora", cap(v), C["steel"]))
    parts.append((8, "Pernos M20", bolts(v), C["pin"]))
    sh, pw, cy_, pn = [], [], [], []
    for sx in (1, -1):
        a_, b_, c_, d_ = push_set(v, sx)
        sh.append(a_); pw.append(b_); cy_.append(c_); pn.append(d_)
    parts.append((9, "Cilindros 50 t", cy_[0].union(cy_[1]), C["cyl"]))
    parts.append((10, "Carros de empuje", sh[0].union(sh[1]), C["steel"]))
    parts.append((11, "Trinquetes", pw[0].union(pw[1]), C["pin"]))
    parts.append((12, "Pasadores D70", pn[0].union(pn[1]), C["pin"]))
    parts.append((22, "Guias de carro", rails(v), C["base"]))
    rub, bar = seal(v)
    parts.append((14, "Faldon NBR", rub, C["nbr"]))
    parts.append((15, "Fleje de apriete", bar, C["steel"]))
    if kind == "U":
        parts.append((19, "Pastillas UHMW", pads(), C["uhmw"]))
        parts.append((20, "Pista inox A", inox(v, *P.INOX_A), C["inox"]))
        parts.append((21, "Pista inox B", inox(v, *P.INOX_B), C["inox"]))
    return v, parts


if __name__ == "__main__":
    import sys, time, json
    for kind in sys.argv[1:] or ["U", "S"]:
        t = time.time()
        v, parts = build(kind)
        assy = cq.Assembly(name=v["code"])
        mass = {}
        for pos, name, shp, col in parts:
            assy.add(shp, name=f"P{pos:02d}_{name.replace(' ', '_')}", color=col)
            vol = shp.val().Volume()
            dens = {6: 7.6e-6, 19: 0.94e-6 if kind == "U" else 0, 14: 1.2e-6}.get(pos, 7.85e-6)
            mass[pos] = round(vol * dens, 1)
        out = f"/home/claude/tt300/out/{v['code']}"
        assy.save(out + ".step")
        assy.save(out + ".glb")
        json.dump(mass, open(out + "_mass.json", "w"))
        print(kind, round(time.time() - t, 1), "s", mass, "total", round(sum(mass.values()), 0))
