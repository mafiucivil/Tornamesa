"""Estudio de opciones: placa sola, B (espesor), C (marco perimetral continuo abierto o cajón), D (nervios diagonales), con la FEA de la base completa."""
import json, math, sys, time
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from basefea import Base, mom, G_, RHO

ex = json.load(open(sys.argv[1])); hm = float(sys.argv[2]); which = sys.argv[3].split(",")
P = ex["P"]; Fa = P["Fy"] / P["Nd"]; Es = P["E"]; Gs = Es / 2.6; tb0 = P["t_base"]
pA = sorted(ex["psiA"]); pH = sorted(ex["psiH"])
PSIS = [pA[0], pA[-1], pH[0], pH[-1]]


def comp_section(hr, tr, t, be, top=None):
    """rim hr × tr sobre plancha t (ancho efectivo be); top = (b, t) ala superior opcional. Devuelve I_comp, y_NA (desde la cara inferior), c_top, c_bot, área"""
    parts = [(be * t, t / 2, be * t ** 3 / 12), (tr * hr, t + hr / 2, tr * hr ** 3 / 12)]
    if top: parts.append((top[0] * top[1], t + hr + top[1] / 2, top[0] * top[1] ** 3 / 12))
    A = sum(p[0] for p in parts); y = sum(p[0] * p[1] for p in parts) / A
    I = sum(p[2] + p[0] * (p[1] - y) ** 2 for p in parts)
    H = t + hr + (top[1] if top else 0)
    return I, y, H - y, y, A


def build(opt, ex, hm):
    tb = opt.get("t", tb0)
    b = Base(ex, hm=hm, t=tb)
    Bh = b.Bh; info = {"masa_extra": RHO * (tb - tb0) * P["B"] ** 2}
    if opt.get("frame"):
        hr, tr = opt["frame"]; be = min(12 * tb, 200)
        top = opt.get("top")
        I, y, ct, cb, A = comp_section(hr, tr, tb, be, top)
        EI = Es * (I - be * tb ** 3 / 12)
        GJ = Gs * (hr * tr ** 3 / 3 + (top[0] * top[1] ** 3 / 3 if top else 0))
        if opt.get("box"):   # cajón: (ancho bw, espesor tw) — Bredt
            bw, tw = opt["box"]; Am = bw * hr; GJ = Gs * 4 * Am ** 2 / (2 * hr / tw + bw / tw + bw / tb)
            I2, y2, ct2, cb2, _ = comp_section(hr, 2 * tr, tb, be, (bw, tw)); EI = Es * (I2 - be * tb ** 3 / 12); I, ct, cb = I2, ct2, cb2
            info.update(Am=Am, tmin=min(tw, tr, tb))
        kGA = Gs * hr * tr * (2 if opt.get("box") else 1)
        mpm = RHO * (hr * tr + (top[0] * top[1] if top else 0)) + (RHO * (hr * tr + opt["box"][0] * opt["box"][1]) if opt.get("box") else 0)
        e = Bh
        for p0, p1 in (((-e, -e), (e, -e)), ((e, -e), (e, e)), ((e, e), (-e, e)), ((-e, e), (-e, -e))):
            b.add_beam_line(p0, p1, EI, GJ, kGA, mpm, "marco")
        info.update(EI=EI, GJ=GJ, I=I, ct=ct, cb=cb, masa_marco=mpm * 4 * P["B"], J=GJ / Gs, tr=max(tr, top[1] if top else 0))
        # cartela de esquina: los nodos del marco frente a las paredes traseras (y la cartela) se ligan al soporte rígido
        E = np.array(ex["E"]); reach = opt.get("reach", 280)
        for cil, sgn in ((1, 1), (2, -1)):
            for k in range(b.nn):
                x, y_ = sgn * b.X[k], sgn * b.Y[k]
                onx = abs(x - Bh) < 1e-6 and E[1] - 130 - 1e-6 <= y_ <= E[1] + reach
                ony = abs(y_ + Bh) < 1e-6 and E[0] - reach <= x <= E[0] + 130 + 1e-6
                if onx or ony: b.rigid_extra[cil - 1].append(k)
    if opt.get("ribs"):   # nervios diagonales: desde la esquina del soporte hacia el centro hasta R_fin (fuera de la mesa)
        hr, tr = opt["ribs"]; be = min(16 * tb, 300)
        I, y, ct, cb, A = comp_section(hr, tr, tb, be)
        EI = Es * (I - be * tb ** 3 / 12); GJ = Gs * hr * tr ** 3 / 3; kGA = Gs * hr * tr
        for p0, p1 in opt.get("rib_lines", []):
            b.add_beam_line(p0, p1, EI, GJ, kGA, RHO * hr * tr, "nervio")
        info.update(EIr=EI, Ir=I, ctr=ct, cbr=cb)
    b.assemble()
    return b, info


def run(opt, cases=("S-vacía", "S-cargada", "U-cargada"), F=None, sgn=-1, psis=PSIS, tag=""):
    b, info = build(opt, ex, hm)
    Wt = ex["Wd"] + ex["mdogs"] * G_
    fz = b.weights(Wt, ex["Ri"], ex["Ro"]); msup = (ex["msup"] + ex["m"]["cyl"] / P["n_cyl"] / 2) * G_
    r = np.hypot(b.X, b.Y); hold = r <= ex["Ro"]
    F = ex["Fstall"] if F is None else F
    res = []
    for nm in cases:
        worst = None
        for psi in psis:
            only1 = nm.startswith("U"); hd = hold if nm.endswith("cargada") else None
            b.solve(mom(ex, F, psi, sgn, only1), fz, hold=hd, masters_w=[-msup, -msup])
            s, x, y = b.plate_stress()
            # tensión de la plancha lejos del soporte (fuera de 400 mm de las esquinas de los soportes)
            E = np.array(ex["E"])
            far = lambda X, Y: (np.hypot(X - E[0], Y - E[1]) > 450) & (np.hypot(X + E[0], Y + E[1]) > 450)
            s_far, xf, yf = b.plate_stress(exclude_r=far)
            bf = b.beam_forces()
            lift = b.w.max(); il = int(np.argmax(b.w)); rin = r <= ex["Ro"]
            lift_in = b.w[rin].max()
            d = dict(psi=math.degrees(psi), s=s, at=(x, y), s_far=s_far, at_far=(xf, yf), lift=lift, at_lift=(b.X[il], b.Y[il]), lift_mesa=lift_in, nact=int(b.act.sum()), conv=b.conv, beams=bf)
            if worst is None or s > worst["s"]: worst = d
            fr = bf.get("marco"); nv = bf.get("nervio")
            extra = ""
            if fr:
                sb = fr['M'] * max(info['ct'], info['cb']) / info['I']; tau = fr['T'] / (2 * info['Am'] * info['tmin']) if 'Am' in info else fr['T'] * info['tr'] / info['J']
                extra += f" marco M={fr['M']/1e6:6.2f} kN·m T={fr['T']/1e6:6.2f} σb={sb:6.1f} τt={tau:6.1f} FUm={math.hypot(sb, math.sqrt(3)*tau)/Fa:5.2f}"
            if nv: extra += f" nervio M={nv['M']/1e6:6.2f} σb={nv['M']*max(info['ctr'],info['cbr'])/info['Ir']:7.1f}"
            print(f"{tag:22s} {nm:9s} ψ={d['psi']:6.1f} σvm={s:7.1f} (FU {s/Fa:5.2f}) en ({x:5.0f},{y:5.0f}); lejos {s_far:6.1f} (FU {s_far/Fa:5.2f}) en ({xf:5.0f},{yf:5.0f}); lev {lift:8.2f} en ({d['at_lift'][0]:5.0f},{d['at_lift'][1]:5.0f}) bajo mesa {lift_in:7.2f}; c {d['nact']} {'ok' if d['conv'] else 'NOCONV'}{extra}", flush=True)
        res.append((nm, worst))
    return res, info


OPTS = {
    "placa": {},
    "B30": {"t": 30}, "B52": {"t": 52}, "B64": {"t": 64},
    "C150x10": {"frame": (150, 10)}, "C200x20": {"frame": (200, 20)}, "C300x25": {"frame": (300, 25)},
    "Cbox200": {"frame": (200, 12), "box": (70, 12)},
    "Cbox250": {"frame": (250, 16), "box": (70, 16)},
    "Cbox300": {"frame": (300, 20), "box": (70, 20)},
    "B40": {"t": 40}, "B58": {"t": 58},
    "D": {"ribs": (150, 15), "rib_lines": [((1240, -1240), (720, -720)), ((-1240, 1240), (-720, 720))]},
    "C200x20+D": {"frame": (200, 20), "ribs": (150, 15), "rib_lines": [((1240, -1240), (720, -720)), ((-1240, 1240), (-720, 720))]},
}
if __name__ == "__main__":
    CASES = tuple(sys.argv[4].split(",")) if len(sys.argv) > 4 else ("S-vacía", "S-cargada", "U-cargada")
    RET = len(sys.argv) > 5 and sys.argv[5] == "ret"
    for w in which:
        o = OPTS[w]
        _, info = run(o, cases=CASES, tag=w, F=ex["Fret"] if RET else None, sgn=1 if RET else -1)
        print("   ", w, {k: (round(v, 1) if isinstance(v, float) else v) for k, v in info.items() if k.startswith("masa")}, flush=True)
