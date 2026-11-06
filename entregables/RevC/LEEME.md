# Entregables Rev. C del paquete de planos TT300-C

Estado: **B vigente (códigos TT300C-…-B), con los cambios del núcleo de la 4.ª pasada**. EMITIDO PARA REVISIÓN: no apto para fabricación hasta su aprobación.

Generado con `python3 cad/generar_paquete.py --entrega entregables/RevC` (diseño por defecto: interfaz acero-acero con grasa) a partir del JSON de `node tools/export_design.js` (fuente única: planos y cálculo salen del mismo JSON).
Contenido (carpeta raíz = diseño por defecto): planos PDF y DXF por lámina, PDF combinado, STEP, GLB, despiece CSV/XLSX, chequeo de cotas, informe del paquete, lista de verificación del revisor y memoria de cálculo (DOCX/PDF).

Cambios de esta emisión respecto de la anterior (86a7e4d), todos tomados del JSON:
- Sectores y discos de 15 mm (hc_min 6, tol_hc 1), Δ 30 mm (A, C) y 55 mm (B), lámina UHMW de B de 25 mm, largos de tope de `interfazGeom.topes`.
- Masas netas de sectores (juntas, muescas, chaflanes, franjas de UHMW) directamente del núcleo (`interfazGeom.cortes`): sin conciliación manual; el informe trae el control por pieza.
- c_lug 200 (orejas de izaje en ±600, ±1.080): BAS-001 e IZA-001 (nueva planta de ubicación de las 4 orejas).
- Madera: anillo de acero (t_ring) dentro del núcleo; residual de abertura y bolsillos explicado en el informe.
- BAS-001: corte A-A simplificado con detalles D1 (marco) y D2 (bancada) con sus soldaduras; MES-003 sin texto sobre el nervio.
- GEN-009 con advertencias del núcleo (mejillas–base en B, plancha inferior en C-3) y el pendiente de filetes máximos de almas y nervios.

`variantes/` contiene, para cada alternativa verificada (A, A pegado «AF2», B, C1, C2, C3 y madera «W»), el informe del paquete, la lista de verificación, el despiece, el chequeo de cotas, el JSON de diseño, el control de masas y los PDF de
conjunto (GEN-002), interfaz (INT-001…003) y madera (MAD-001) cuando aplican (sin DXF). Para regenerar el paquete completo de una variante:

```
echo '{"opt_uhmw":1}' > parametros.json                     # A: {"opt_ss":1}; A pegado: {"opt_ss":1,"fix_mode":2}; B: {"opt_uhmw":1}; C1/C2/C3: {"opt_bz":1,"bz_conf":1|2|3}; madera: {"opt_wood":1}
node tools/export_design.js parametros.json > diseno.json
python3 cad/generar_paquete.py diseno.json --out cad/out/variante_B
```
(C1–C3 tardan 8–10 min cada una.)

ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO.
