# Entregables Rev. C del paquete de planos TT300-C

Estado: **B vigente: cambios C respecto de la B anterior** (los códigos TT300C-…-B se mantienen). EMITIDO PARA REVISIÓN: no apto para fabricación hasta su aprobación.

Generado con `python3 cad/generar_paquete.py --entrega entregables/RevC` (diseño por defecto: interfaz acero-acero con grasa) a partir del JSON de `node tools/export_design.js` (fuente única: planos y cálculo salen del mismo JSON).
Contenido completo (planos PDF y DXF por lámina, PDF combinado, STEP, GLB, despiece CSV/XLSX, chequeo de cotas, informe, lista de verificación) en esta carpeta.

`variantes/` contiene, para cada alternativa verificada (A, A pegado «AF2», B, C1, C2, C3 y madera «W»), el informe del paquete, la lista de verificación, el despiece, el chequeo de cotas, el JSON de diseño y los PDF de
conjunto (GEN-002), interfaz (INT-001…003) y madera (MAD-001) cuando aplican (sin DXF). Para regenerar el paquete completo de una variante:

```
echo '{"opt_uhmw":1}' > parametros.json                     # A: {"opt_ss":1}; A pegado: {"opt_ss":1,"fix_mode":2}; C1/C2/C3: {"opt_bz":1,"bz_conf":1|2|3}; madera: {"opt_wood":1}
node tools/export_design.js parametros.json > diseno.json
python3 cad/generar_paquete.py diseno.json --out cad/out/variante_B
```

ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO.
