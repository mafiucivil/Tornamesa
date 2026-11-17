"""Pares sobre la base en cada apoyo del modo guiado (cilindro 1: lado +x, empuje +y) y balance por cilindro (docs/qa/plancha_base_modo_guiado.md §1).
Uso: python3 cargas.py entrada.json
Fuerzas horizontales a la altura z sobre la cara superior de la plancha: Mx = −z·Fy, My = z·Fx (kN·m). Un balance nulo por cilindro = el par se cierra en la
franja de su bancada; distinto de cero = la otra mitad la toma la mesa y el par cruza la base hasta el otro cilindro (M₂ = −M₁)."""
import json, math, sys

ex = json.load(open(sys.argv[1])); P = ex["P"]
h, zT, zF = ex["h"], ex["zT"], ex["zF"]; F = ex["Fstall"]; Fp = P["eta_c"] * F; Fr, NT, NRx = ex["Fret"], ex["NT"], ex["NRx"]
k = lambda v: v / 1e6
print(f"h = {h} mm, z_T = {zT} mm (lengüeta en la ranura), z_F = {zF} mm (seguidor), F = {F/1e3:.1f} kN, F_pas = η·F = {Fp/1e3:.1f} kN, F_ret = {Fr/1e3:.1f} kN, N_toma = {NT/1e3:.1f} kN, N_rampa,x = {NRx/1e3:.1f} kN\n")
for st in ex["shoe"]:
    Rf, Rr, Hx = st["rf"] * Fp, st["rr"] * Fp, -st["h"] * Fp
    rows = [("ménsula (−F·ŷ a h)", h * F, 0.0),
            ("bancada: reacción delantera de la guía (−R_f·x̂ a z_T)", 0.0, zT * (-Rf)), ("bancada: reacción trasera (−R_r·x̂ a z_T)", 0.0, zT * (-Rr)),
            ("bancada: roce de la guía (F − F_pas)·ŷ a z_T y cabeceo hasta h", -h * (F - Fp), 0.0), ("bancada: resto del vuelco del patín (lengüeta T)", 0.0, (h - zT) * Hx)]
    sx, sy = sum(r[1] for r in rows), sum(r[2] for r in rows)
    print(f"Empuje a calado, θ = {math.degrees(st['th']):5.1f}°: R_f = {Rf/1e3:7.1f} kN, R_r = {Rr/1e3:7.1f} kN, H = {Hx/1e3:6.1f} kN")
    for nm, mx, my in rows: print(f"   {nm:62s} Mx = {k(mx):7.2f}  My = {k(my):6.2f}")
    print(f"   {'suma sobre la base (la mesa toma lo opuesto en el pasador)':62s} Mx = {k(sx):7.2f}  My = {k(sy):6.2f}  |M| = {k(math.hypot(sx, sy)):6.2f} kN·m → cruza la base\n")
rows = [("ménsula (+F_ret·ŷ a h)", -h * Fr, 0.0), ("riel → pórticos (−F_ret·ŷ y +N_x·x̂ a z_F)", zF * Fr, zF * NRx), ("patín → bancada (resto: −(z_F − h)·F_ret; −z_F·N_x)", -(zF - h) * Fr, -zF * NRx)]
print("Retorno, uña trabada en la rampa del riel-leva:")
for nm, mx, my in rows: print(f"   {nm:62s} Mx = {k(mx):7.2f}  My = {k(my):6.2f}")
print(f"   {'suma sobre la base':62s} Mx = {k(sum(r[1] for r in rows)):7.2f}  My = {k(sum(r[2] for r in rows)):6.2f} → se cierra en la franja de la bancada\n")
rows = [("ménsula (+F_ret·ŷ a h)", -h * Fr, 0.0), ("riel → pórticos (+N_toma·x̂ a z_F)", 0.0, zF * NT), ("patín → bancada (par de la uña −(z_F − h)·N_toma)", 0.0, -(zF - h) * NT)]
sx, sy = sum(r[1] for r in rows), sum(r[2] for r in rows)
print("Retorno, chaflán sobre el pasador siguiente a nivel de toma:")
for nm, mx, my in rows: print(f"   {nm:62s} Mx = {k(mx):7.2f}  My = {k(my):6.2f}")
print(f"   {'suma sobre la base (la mesa toma lo opuesto en el pasador B)':62s} Mx = {k(sx):7.2f}  My = {k(sy):6.2f}  |M| = {k(math.hypot(sx, sy)):6.2f} kN·m = h·√(F_ret² + N_toma²) → cruza la base")
