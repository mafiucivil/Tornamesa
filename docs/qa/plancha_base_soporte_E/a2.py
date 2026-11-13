"""Opción A2 (modo pivotado): marco perimetral continuo con cartelas + un perno en cada esquina libre. Dimensionado del marco (JSON por línea).
Uso: python3 a2.py entrada.json 80 C300x25,T200+80x25,...
Reutiliza basefea.py y opciones.build(); el criterio y la salida son los de casos.py (σ_vM ≤ Fy/Nd en la plancha; √(σ_b² + 3τ_t²) ≤ Fy/Nd en el marco)."""
import json, math, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from basefea import G_, RHO
import opciones as R1   # ex, hm y la lista se leen de argv[1..3] (mismo orden)

ex = R1.ex; hm = R1.hm; P = ex["P"]; Fa = P["Fy"] / P["Nd"]; E = np.array(ex["E"])
pA = sorted(ex["psiA"]); PS = [pA[0], pA[-1]]
ANC = [(1200, 1200), (-1200, -1200)]   # esquinas libres (C2 y C4), fuera del barrido


def opt_of(name):
    """C<h>x<t>: pletina de canto h × t; T<h>+<b>x<t>: pletina h × t_alma (25) con ala superior b × t hacia adentro; K<h>+<b>x<t>: cajón b × h de pared t"""
    if name.startswith("C"):
        h, t = name[1:].split("x"); return {"frame": (float(h), float(t))}
    if name.startswith("T"):
        h, rest = name[1:].split("+"); b, t = rest.split("x"); return {"frame": (float(h), 25.0), "top": (float(b), float(t))}
    if name.startswith("K"):
        h, rest = name[1:].split("+"); b, t = rest.split("x"); return {"frame": (float(h), float(t)), "box": (float(b), float(t))}
    raise ValueError(name)


def go(b, info, name, case, F, sgn, psi):
    from basefea import mom
    Wt = ex["Wd"] + ex["mdogs"] * G_
    fz = b.weights(Wt, ex["Ri"], ex["Ro"]); msup = (ex["msup"] + ex["m"]["cyl"] / P["n_cyl"] / 2) * G_
    r = np.hypot(b.X, b.Y); hd = np.zeros(b.nn, bool)
    if case.endswith("cargada"): hd |= r <= ex["Ro"]
    ids = [b.node(x, y) for (x, y) in ANC]
    for k in ids: hd[k] = True
    t0 = time.time()
    b.solve(mom(ex, F, psi, sgn, case.startswith("U")), fz, hold=hd, masters_w=[-msup, -msup])
    s, x, y = b.plate_stress()
    far = lambda X, Y: (np.hypot(X - E[0], Y - E[1]) > 450) & (np.hypot(X + E[0], Y + E[1]) > 450) & np.all([np.hypot(X - b.X[k], Y - b.Y[k]) > 150 for k in ids], axis=0)
    sf, xf, yf = b.plate_stress(exclude_r=far)
    fr = b.beam_forces()["marco"]
    sb = fr["M"] * max(info["ct"], info["cb"]) / info["I"]; tau = fr["T"] / (2 * info["Am"] * info["tmin"]) if "Am" in info else fr["T"] * info["tr"] / info["J"]
    il = int(np.argmax(b.w))
    out = dict(marco=name, caso=case, psi=math.degrees(psi), M_kNm=F * ex["h"] / 1e6, masa_marco_kg=info["masa_marco"], fu=s / Fa, at=[x, y], fu_far=sf / Fa, at_far=[xf, yf],
               marco_M=fr["M"] / 1e6, marco_T=fr["T"] / 1e6, marco_at=fr["at"], marco_sb=sb, marco_tau=tau, marco_fu=math.hypot(sb, math.sqrt(3) * tau) / Fa,
               anclajes_kN=[float(-b.react[k] / 1e3) for k in ids], lift=float(b.w.max()), at_lift=[float(b.X[il]), float(b.Y[il])], ncont=int(b.act.sum()), conv=bool(b.conv), t=round(time.time() - t0, 1))
    print(json.dumps(out), flush=True)


for name in R1.which:
    b, info = R1.build(opt_of(name), ex, hm)
    for psi in PS:
        for case in ("S-vacía", "U-vacía", "S-cargada", "U-cargada"):
            go(b, info, name, case, ex["Fstall"], -1, psi)
        go(b, info, name, "S-vacía (retorno)", ex["Fret"], 1, psi)
