"""Retorno con la mesa cargada y mesa vacía en servicio, con el inserto (modo pivotado). python3 extra.py geo design t_base h 'tins' """
import json, math, sys, os
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
tb, h = float(sys.argv[3]), float(sys.argv[4]); tl = [float(v) for v in sys.argv[5].split(",")]
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], str(tb), str(h), "10", "8", "50", "445.32", "40", "0", "muesca"]
import sweep, fe
Fret = math.pi / 4 * (sweep.D["P"]["D_bore"] ** 2 - sweep.D["P"]["d_rod"] ** 2) * sweep.D["P"]["p_ret"] / 10 / 1e3
Wd = 14.976


def job(a):
    t, kind, F = a; psi = sweep.band[0]; u = (math.cos(math.radians(psi)), math.sin(math.radians(psi)))
    tv = fe.tvec_poly([sweep.poly1, sweep.poly2], t, tb)
    if kind == "ret": r = fe.caso(F * 1e3, u, sweep.E1, sweep.rects, h, sweep.B, tv, sweep.W_tab, sweep.Rt, sense=1)
    elif kind == "vac": r = fe.caso(F * 1e3, u, sweep.E1, sweep.rects, h, sweep.B, tv, Wd * 1e3, sweep.Rt, table="weight")
    else: r = fe.caso(F * 1e3, u, sweep.E1, sweep.rects, h, sweep.B, tv, sweep.W_tab, sweep.Rt)
    s = fe.summary(r, tb); s.update(t=t, kind=kind, F=F); return s


if __name__ == "__main__":
    jobs = [(t, "ret", Fret) for t in tl] + [(t, "vac", F) for t in tl for F in (3.0, 10.0, 30.0)]
    with Pool(4) as p:
        for s in p.imap(job, jobs):
            print(f"{s['kind']} t {s['t']} F {s['F']:.2f} M {s['M']:.3f} pico {s['pico']:.1f} lejos {s['lejos']:.2f} base {s['lejos_base']:.2f} ins {s['lejos_ins']:.2f} en {s['donde']} w {s['w']:.3f} {'ok' if s['conv'] else 'NC'}", flush=True)
