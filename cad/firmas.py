"""Firma geométrica de las piezas (H-04: un código = una geometría).

La firma de un sólido se mide sobre el B-rep real, en un sistema propio que no depende de dónde está montado:
  - el sólido se gira alrededor del eje z del equipo hasta dejar su baricentro sobre +x (los sectores, barras radiales y tapones quedan
    todos en la misma posición relativa);
  - se miden volumen, área, número de caras, extensión en x/y/z, el producto de inercia Ixy respecto del baricentro (distingue un sector de su
    imagen especular, p. ej. sectores pares e impares) y los radios de las caras cilíndricas con su cantidad (agujeros, tapones, avellanados).
Dos sólidos con la misma firma son la misma pieza; si un código agrupa sólidos de firma distinta, la pieza se separa en tipos con sufijo
(-1, -2, …) y cada tipo es un código propio.

Uso como herramienta (control entre variantes): python3 cad/firmas.py <dir_entrega_1> <dir_entrega_2> …
  lee <dir>/TT300-C_firmas.json de cada juego y verifica que un mismo código tenga la misma firma en todos los juegos de la misma base de parámetros.
  Con --registrar escribe el registro cad/firmas_codigos.json (base de parámetros y firma por código)."""
import json, math, sys, pathlib, hashlib

SELECTORES = ("opt_ss", "opt_uhmw", "opt_bz", "bz_conf", "opt_wood", "fix_mode", "drive_mode")
REGISTRO = pathlib.Path(__file__).resolve().parent / "firmas_codigos.json"


def _sig(v, n=5):
    if abs(v) < 1e-9:
        return 0.0
    return round(v, -int(math.floor(math.log10(abs(v)))) + (n - 1))


def firma_solido(so, volteable=False, libre=False):
    import cadquery as cq
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    c = so.Center()
    ang = math.degrees(math.atan2(c.y, c.x)) if math.hypot(c.x, c.y) > 1.0 else 0.0
    s2 = so.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -ang) if ang else so
    pr = GProp_GProps()
    BRepGProp.VolumeProperties_s(s2.wrapped, pr)
    M = pr.MatrixOfInertia()
    ixx, iyy, ixy = M.Value(1, 1), M.Value(2, 2), M.Value(1, 2)
    if libre:
        # pieza recta montada en distintas orientaciones (paredes y tapas del cajón): se lleva a sus ejes principales de inercia en planta
        th = 0.5 * math.degrees(math.atan2(2 * ixy, ixx - iyy))
        s2 = s2.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -th)
        pr = GProp_GProps()
        BRepGProp.VolumeProperties_s(s2.wrapped, pr)
        M = pr.MatrixOfInertia()
        ixx, iyy, ixy = M.Value(1, 1), M.Value(2, 2), M.Value(1, 2)
        if ixx > iyy:
            s2 = s2.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 90)
            ixx, iyy, ixy = iyy, ixx, -ixy
    ixy = 0.0 if abs(ixy) < 1e-5 * (abs(ixx) + abs(iyy) + 1e-9) else _sig(ixy, 3)
    if volteable:
        ixy = abs(ixy)            # pieza plana simétrica en espesor: su imagen especular es la misma pieza volteada
    bb = s2.BoundingBox()
    rad = {}
    for fc in s2.Faces():
        ad = BRepAdaptor_Surface(fc.wrapped)
        if ad.GetType() == GeomAbs_Cylinder:
            r = round(ad.Cylinder().Radius(), 1)
            rad[r] = rad.get(r, 0) + 1
    if libre:                     # pieza recta girada a sus ejes principales: el redondeo absorbe el ruido numérico del giro
        return dict(vol=_sig(s2.Volume(), 4), area=_sig(s2.Area(), 3), caras=len(s2.Faces()), ext=[round(bb.xlen, 0), round(bb.ylen, 0), round(bb.zlen, 0)],
                    ixy=0.0, cil=sorted([[r, n] for r, n in rad.items()]))
    return dict(vol=_sig(s2.Volume()), area=_sig(s2.Area(), 4), caras=len(s2.Faces()), ext=[round(bb.xlen, 1), round(bb.ylen, 1), round(bb.zlen, 1)],
                ixy=ixy, cil=sorted([[r, n] for r, n in rad.items()]))


def clave(fs):
    return json.dumps(fs, sort_keys=True)


def solidos(p):
    out = []
    for so in p.solid.vals():
        out.extend(so.Solids() if hasattr(so, "Solids") else [so])
    return out


def tipos(p, maxn=400):
    """Agrupa los sólidos de la pieza por firma: [(firma, [índices])] en el orden de la primera aparición."""
    sol = solidos(p)
    if len(sol) > maxn:
        sol = sol[:maxn]
    grupos = {}
    orden = []
    for i, so in enumerate(sol):
        k = clave(firma_solido(so, getattr(p, "volteable", False), getattr(p, "libre", False)))
        if k not in grupos:
            grupos[k] = []
            orden.append(k)
        grupos[k].append(i)
    return [(json.loads(k), grupos[k]) for k in orden]


def base_hash(D):
    P = {k: v for k, v in D["P"].items() if k not in SELECTORES}
    return hashlib.sha1(json.dumps(P, sort_keys=True, default=str).encode()).hexdigest()[:16]


def firmas_juego(ctx):
    """{código: firma} de todas las piezas fabricadas del juego (un código por tipo)."""
    out = {}
    for p in ctx.m.parts:
        for cod, fs in getattr(p, "firmas_cod", {}).items():
            out[cod] = fs
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reg = "--registrar" in sys.argv
    juegos = []
    for d in args:
        f = pathlib.Path(d) / "TT300-C_firmas.json"
        juegos.append((d, json.loads(f.read_text(encoding="utf-8"))))
    bases = {j["base"] for _, j in juegos}
    malos = []
    por_cod = {}
    for d, j in juegos:
        for cod, fs in j["firmas"].items():
            por_cod.setdefault((j["base"], cod), []).append((j["variante"], clave(fs)))
    for (b, cod), lst in sorted(por_cod.items()):
        ks = {k for _, k in lst}
        if len(ks) > 1:
            malos.append(f"{cod}: geometría distinta entre variantes {', '.join(v for v, _ in lst)}")
    for m in malos:
        print("  CÓDIGO CON DOS GEOMETRÍAS:", m)
    print(f"control de códigos entre variantes: {len(juegos)} juegos, {len(por_cod)} códigos, {len(malos)} con geometría distinta")
    if reg and not malos and len(bases) == 1:
        firm = {}
        var = {}
        for d, j in juegos:
            for cod, fs in j["firmas"].items():
                firm[cod] = fs
                var.setdefault(cod, []).append(j["variante"])
        REGISTRO.write_text(json.dumps(dict(base=bases.pop(), firmas=firm, variantes=var), indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        print("registro escrito:", REGISTRO)
    sys.exit(1 if malos else 0)


if __name__ == "__main__":
    main()
