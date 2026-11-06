# Entregables Rev. C del paquete de planos TT300-C (juego de planos de fabricación rehecho)

Estado: **EMITIDO PARA REVISIÓN, revisión C** (códigos TT300C-…-C). NO apto para fabricación hasta su revisión y aprobación por un ingeniero calculista habilitado. DIBUJÓ/REVISÓ/APROBÓ: A DEFINIR (con casillas de firma y fecha).

Generado con `python3 cad/generar_paquete.py --entrega entregables/RevC` (diseño por defecto: interfaz acero-acero con grasa) a partir del JSON de `node tools/export_design.js` (fuente única: planos y cálculo salen del mismo JSON; el generador no tiene valores a mano).

## Contenido (carpeta raíz = diseño por defecto)
- `planos/`: una lámina por archivo, PDF y DXF (A1 y A2, método de proyección E, letra ≥ 3,5 mm en el plot, tablas 3,0 mm, mínimo 2,5 mm). Series: `GEN` (generales: notas/normas/índice, inspección, tolerancias y ajustes ISO 286, materiales, tratamientos, programa de soldaduras, torques y compras, supuestos y brechas, cortes de plancha, lista de verificación), `CON` (conjunto general, despiece completo, explosionada, secuencia, base, ménsula, mesa, accionamiento, pivote, interfaz) y láminas de pieza con el código del ítem (`BAS`, `IZA`, `ACC`, `MES`, `PIV`, `INT`, `MAD`).
- `TT300-C_Planos_RevC.pdf`: PDF combinado con marcadores (índice de láminas). `TT300-C_DXF_RevC.zip`: DXF de todas las láminas.
- `TT300-C.step`, `TT300-C.glb`: modelo 3D. `TT300-C_despiece.csv/.xlsx` (pestañas Despiece, Masas, Corte, Soldaduras, Supuestos y brechas), `soldaduras.csv` (programa de soldaduras con las láminas donde cada junta tiene su símbolo), `lista_de_cortes.csv`, `metricas_laminas.csv` (cotas, ocupación por vistas y textos A DEFINIR por lámina), `chequeo_cotas.csv` (cada cota verificada contra el sólido 3D), `informe_paquete.md`, `lista_verificacion_revisor.md/.pdf`, `TT300-C_masas3d.json`, `TT300-C_design.json`.
- `variantes/` (A, A pegado «AF2», B, C1, C2, C3 y madera «W»): el mismo juego completo (PDF por lámina y combinado, STEP/GLB, despiece, soldaduras, informe); sin DXF. Regenerar una variante:

```
echo '{"opt_uhmw":1}' > parametros.json     # A: {"opt_ss":1}; A pegado: {"opt_ss":1,"fix_mode":2}; B: {"opt_uhmw":1}; C1/C2/C3: {"opt_bz":1,"bz_conf":1|2|3}; madera: {"opt_wood":1}
node tools/export_design.js parametros.json > diseno.json
python3 cad/generar_paquete.py diseno.json --out cad/out/variante_B --sin-dxf
```

Memoria de cálculo: `TT300-C_Memoria_RevC.docx/.pdf` (texto negro, hipótesis → desarrollo → resultado, formato para insertar en documento) y `TT300-C_alternativas.json` (datos de los capítulos 9 y 10, incluida la clave `tapones`). Actualizada con el núcleo v1.2 (commit c5a9f15, `Tornamesa_v1.2.html`): cap. 9.7 «Opción C: tapones de grafito, cantidad real frente a ideal» (N_real 2.640 / 2.640 / 2.364 frente a ideal 3.961 / 3.961 / 3.565; f_g real 0,0967 frente a 0,145; hallazgos G1 a G4 y recomendación al proveedor); cap. 10 «Exposición solar a 80 °C» con alcance solo placas y disco (`term_alcance` = 1; cilindros, aceite atrapado, válvula de alivio térmico, sellos, viscosidad/bomba y accionamiento fuera del escenario, 51 filas informativas en la nota 10.12); cap. 14 con el juego de planos Rev. C leído de `informe_paquete.md`; Anexo C con los parámetros nuevos de la v1.2. Regenerar: `npm run memoria` (necesita `python-docx` y LibreOffice `soffice`); el .docx y el .pdf se copian a esta carpeta.

## Reglas del juego de planos
- Cada pieza del despiece tiene plano propio (código de la pieza = número de plano) o referencia a catálogo; cada ítem aparece con globo en un plano de conjunto o subconjunto.
- Cada junta soldada J## tiene símbolo ISO 2553 (flecha, línea de referencia, tamaño a/z, proceso, nivel ISO 5817, WPS, END) y fila en la tabla de soldaduras (global GEN-007 y por lámina). Tamaños: parámetros w_* del núcleo; donde el núcleo no los da, mínimo AWS D1.1 T5.8 por la parte más gruesa, rotulado «mínimo AWS, a confirmar».
- Materiales: solo los grados que el cálculo soporta (A572 Gr.50, 34CrNiMo6+QT, A240, 17-4PH, C95400); el resto se rotula «SEGÚN CÁLCULO Fy ≥ … MPa, A DEFINIR POR EL FABRICANTE».
- Torques de pernos: PROPUESTA, A CONFIRMAR POR EL CALCULISTA (GEN-008).
