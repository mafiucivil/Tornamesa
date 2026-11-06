# Entregables Rev. C del paquete de planos TT300-C

Generado con `python3 cad/generar_paquete.py --entrega entregables/RevC` (diseño por defecto: interfaz acero-acero con grasa).
Contenido completo (planos PDF y DXF por lámina, PDF combinado, STEP, GLB, despiece CSV/XLSX, chequeo de cotas, informe, lista de verificación) en esta carpeta.

`variantes/` contiene, para cada alternativa verificada, el informe del paquete, la lista de verificación, el despiece, el chequeo de cotas, el JSON de diseño y los PDF de
conjunto (GEN-002), interfaz (INT-001…003) y madera (MAD-001) cuando aplican. Para regenerar el paquete completo de una variante:

```
node tools/export_design.js parametros.json > diseno.json   # parametros.json p. ej. {"opt_ss":1}
python3 cad/generar_paquete.py diseno.json --out cad/out/variante_A
```

ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO.
