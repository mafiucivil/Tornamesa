"""Recortes del plano de referencia KIET-1024-REF-TT-400T (rasterizado a 400 dpi) para la figura comparativa y medición de proporciones relativas
(medido en plano de referencia KIET, no acotado). Uso: python3 -I kiet_crops.py <k-1.png> <carpeta_salida>"""
import sys, json, math, pathlib
from PIL import Image
im = Image.open(sys.argv[1]).convert("L"); out = pathlib.Path(sys.argv[2])
plan = im.crop((950, 1500, 3350, 3950)); plan.resize((900, 919)).save(out / "kiet_planta_recorte.png")
im.crop((1000, 1650, 2200, 2100)).resize((900, 338)).save(out / "kiet_detalle_placa_cilindro1.png")
im.crop((1000, 2250, 1350, 2800)).save(out / "kiet_detalle_placa_cilindro1_otro_sentido.png")
# proporciones relativas (coordenadas en la imagen de la planta a la mitad de resolución, centro del anillo y radio exterior del anillo Ø2000)
cx, cy, Rr = 604, 688, 526
pts = {"ojal_cilindro_1": (90, 172), "placa_1_sentido_a": (424, 163), "placa_1_sentido_b": (101, 505), "ojal_cilindro_2": (1117, 1200), "placa_2_sentido_a": (1140, 868), "placa_2_sentido_b": (780, 1200)}
res = {}
for k, (x, y) in pts.items():
    dx, dy = x - cx, cy - y
    res[k] = {"angulo_deg": round(math.degrees(math.atan2(dy, dx)) % 360, 1), "radio_relativo_al_anillo": round(math.hypot(dx, dy) / Rr, 3)}
print(json.dumps(res, ensure_ascii=False, indent=1))
