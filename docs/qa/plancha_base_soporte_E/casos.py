"""Corridas finales del estudio (JSON por línea): placa sola en todos los casos (malla fina) y anclajes A1 / A2 (fuerza por perno)."""
import json, math, sys, time
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from basefea import Base, mom, G_
import opciones as R1   # reutiliza build() y OPTS (no ejecuta su bucle: se importa con argv propio)

ex = json.load(open(sys.argv[1])); hm = float(sys.argv[2]); mode = sys.argv[3]
P = ex["P"]; Fa = P["Fy"] / P["Nd"]
pA = sorted(ex["psiA"]); PS = [pA[0], pA[-1]]
E = np.array(ex["E"])


def go(b, info, name, case, F, sgn, psi, hold=None, anchors=None):
    Wt = ex["Wd"] + ex["mdogs"] * G_
    fz = b.weights(Wt, ex["Ri"], ex["Ro"]); msup = (ex["msup"] + ex["m"]["cyl"] / P["n_cyl"] / 2) * G_
    r = np.hypot(b.X, b.Y)
    hd = np.zeros(b.nn, bool)
    if case.endswith("cargada"): hd |= r <= ex["Ro"]
    ids = []
    if anchors:
        for (x, y) in anchors: k = b.node(x, y); hd[k] = True; ids.append(k)
    t0 = time.time()
    b.solve(mom(ex, F, psi, sgn, case.startswith("U")), fz, hold=hd, masters_w=[-msup, -msup])
    s, x, y = b.plate_stress()
    far = lambda X, Y: (np.hypot(X - E[0], Y - E[1]) > 450) & (np.hypot(X + E[0], Y + E[1]) > 450) & np.all([np.hypot(X - b.X[k], Y - b.Y[k]) > 150 for k in ids] or [np.ones_like(X, bool)], axis=0)
    sf, xf, yf = b.plate_stress(exclude_r=far)
    il = int(np.argmax(b.w)); rin = r <= ex["Ro"]
    anc = [float(-b.react[k]) for k in ids]   # tracción del anclaje (+ = tira hacia abajo de la base)
    bf = b.beam_forces(); fr = bf.get("marco")
    out = dict(opt=name, caso=case, F_kN=F / 1e3, M_kNm=F * ex["h"] / 1e6, psi=math.degrees(psi), s=s, fu=s / Fa, at=[x, y], s_far=sf, fu_far=sf / Fa, at_far=[xf, yf],
               lift=float(b.w.max()), at_lift=[float(b.X[il]), float(b.Y[il])], lift_mesa=float(b.w[rin].max()), ncont=int(b.act.sum()), nn=b.nn, conv=bool(b.conv), it=b.it,
               anclajes_kN=[a / 1e3 for a in anc], t=round(time.time() - t0, 1))
    if fr:
        sb = fr['M'] * max(info['ct'], info['cb']) / info['I']; tau = fr['T'] / (2 * info['Am'] * info['tmin']) if 'Am' in info else fr['T'] * info['tr'] / info['J']
        out.update(marco_M=fr["M"] / 1e6, marco_T=fr["T"] / 1e6, marco_sb=sb, marco_tau=tau, marco_fu=math.hypot(sb, math.sqrt(3) * tau) / Fa)
    print(json.dumps(out), flush=True)


if mode == "placa":
    b, info = R1.build({}, ex, hm)
    for psi in PS:
        for case in ("S-vacía", "S-cargada", "U-cargada", "U-vacía"):
            go(b, info, "placa", case, ex["Fstall"], -1, psi)
        for case in ("S-vacía", "S-cargada"):
            go(b, info, "placa-retorno", case, ex["Fret"], 1, psi)
elif mode == "anclajes":
    # A1: un anclaje por lado del talón de cada soporte (2 por soporte), justo detrás de las paredes traseras prolongadas (marco local (115; 320) y (−320; −115))
    loc = [(115, 320), (-320, -115)]
    A1 = [(E[0] + x, E[1] + y) for x, y in loc] + [(-(E[0] + x), -(E[1] + y)) for x, y in loc]
    b, info = R1.build({}, ex, hm)
    for psi in PS:
        go(b, info, "A1 placa + 2 anclajes por soporte", "S-vacía", ex["Fstall"], -1, psi, anchors=A1)
        go(b, info, "A1 placa + 2 anclajes por soporte", "U-vacía", ex["Fstall"], -1, psi, anchors=A1)
        go(b, info, "A1 placa + 2 anclajes por soporte (retorno)", "S-vacía", ex["Fret"], 1, psi, anchors=A1)
    # A2: marco abierto 200 × 20 continuo + un anclaje en cada esquina libre (C2 y C4)
    A2 = [(1200, 1200), (-1200, -1200)]
    b, info = R1.build(R1.OPTS["C200x20"], ex, hm)
    for psi in PS:
        go(b, info, "A2 marco 200×20 + anclajes en las esquinas libres", "S-vacía", ex["Fstall"], -1, psi, anchors=A2)
        go(b, info, "A2 marco 200×20 + anclajes en las esquinas libres (retorno)", "S-vacía", ex["Fret"], 1, psi, anchors=A2)
else:
    names = mode.split("+")
    for nm in names:
        b, info = R1.build(R1.OPTS[nm], ex, hm)
        for psi in PS:
            for case in ("S-vacía", "S-cargada", "U-cargada"):
                go(b, info, nm, case, ex["Fstall"], -1, psi)
