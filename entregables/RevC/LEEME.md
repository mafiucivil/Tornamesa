# Entregables Rev. C del paquete de planos TT300-C (juego de planos de fabricación rehecho)

Estado: **EMITIDO PARA REVISIÓN, revisión C** (códigos TT300C-…-C). NO apto para fabricación hasta su revisión y aprobación por un ingeniero calculista habilitado. DIBUJÓ/REVISÓ/APROBÓ: A DEFINIR (con casillas de firma y fecha).

Segunda pasada (compositor de lámina, cotas automáticas verificadas, láminas nuevas, WPS/pintura/grados propuestos). Generado con `python3 cad/generar_paquete.py --entrega entregables/RevC` (diseño por defecto: interfaz acero-acero con grasa) a partir del JSON de `node tools/export_design.js` (fuente única: planos y cálculo salen del mismo JSON; el generador no tiene valores a mano).

## Contenido (carpeta raíz = diseño por defecto)
- `planos/`: una lámina por archivo, PDF y DXF (A1 y A2, método de proyección E, letra ≥ 3,5 mm en el plot, tablas 3,0 mm, mínimo 2,5 mm). Cada vista se dibuja a la mayor escala normalizada que cabe (1:1, 1:2, 1:2,5, 1:5, 1:10, 1:20, 1:25, 1:50, 1:100; ampliaciones 2:1 y 5:1 en detalles); las isométricas llevan la leyenda «SIN ESCALA». Series: `GEN` (generales: notas/normas/índice, inspección, tolerancias y ajustes ISO 286, materiales y grados propuestos, tratamientos y pintura, programa de soldaduras, torques y componentes de catálogo, supuestos y brechas, cortes de plancha, lista de verificación, GEN-012 WPS pre-calificados propuestos), `CON` (conjunto general, despiece completo, explosionada, secuencia, base, ménsula, mesa, accionamiento, pivote, interfaz) y láminas de pieza con el código del ítem (`BAS`, `IZA`, `ACC`, `MES`, `PIV`, `INT`, `MAD`).
- `TT300-C_Planos_RevC.pdf`: PDF combinado con marcadores (índice de láminas). `TT300-C_DXF_RevC.zip`: DXF de todas las láminas.
- `TT300-C.step`, `TT300-C.glb`: modelo 3D. `TT300-C_despiece.csv/.xlsx` (pestañas Despiece, Masas, Corte, Soldaduras, Supuestos y brechas), `soldaduras.csv` (programa de soldaduras con las láminas donde cada junta tiene su símbolo), `lista_de_cortes.csv`, `metricas_laminas.csv` (cotas, ocupación por vistas y textos A DEFINIR por lámina), `chequeo_cotas.csv` (cada cota verificada contra el sólido 3D), `informe_paquete.md`, `lista_verificacion_revisor.md/.pdf`, `TT300-C_masas3d.json`, `TT300-C_design.json`.
- `variantes/` (A, A pegado «AF2», B, C1, C2, C3 y madera «W»): el mismo juego completo (PDF por lámina y combinado, STEP/GLB, despiece, soldaduras, informe); sin DXF. Regenerar una variante:

```
echo '{"opt_uhmw":1}' > parametros.json     # A: {"opt_ss":1}; A pegado: {"opt_ss":1,"fix_mode":2}; B: {"opt_uhmw":1}; C1/C2/C3: {"opt_bz":1,"bz_conf":1|2|3}; madera: {"opt_wood":1}
node tools/export_design.js parametros.json > diseno.json
python3 cad/generar_paquete.py diseno.json --out cad/out/variante_B --sin-dxf
```

Memoria de cálculo: `TT300-C_Memoria_RevC.docx/.pdf` (texto negro, hipótesis → desarrollo → resultado, formato para insertar en documento) y `TT300-C_alternativas.json` (datos de los capítulos 9 y 10, incluida la clave `tapones`). Actualizada con el núcleo v1.2 (commit c5a9f15, `Tornamesa_v1.2.html`): cap. 9.7 «Opción C: tapones de grafito, cantidad real frente a ideal» (N_real 2.640 / 2.640 / 2.364 frente a ideal 3.961 / 3.961 / 3.565; f_g real 0,0967 frente a 0,145; hallazgos G1 a G4 y recomendación al proveedor); cap. 10 «Exposición solar a 80 °C» con alcance solo placas y disco (`term_alcance` = 1; cilindros, aceite atrapado, válvula de alivio térmico, sellos, viscosidad/bomba y accionamiento fuera del escenario, 51 filas informativas en la nota 10.12); cap. 14 con el juego de planos Rev. C leído de `informe_paquete.md`; Anexo C con los parámetros nuevos de la v1.2. Regenerar: `npm run memoria` (necesita `python-docx` y LibreOffice `soffice`); el .docx y el .pdf se copian a esta carpeta.

## Planos de armado (sexta pasada)
- `CON-004`: isométrica explosionada por grupos en z (base soldada con bancadas; pivote y tapa retenedora; interfaz lado base; interfaz lado mesa; buje; mesa en tres niveles; pasadores; pernos; tapa de inspección; madera), con trayectorias de montaje en trazo y punto y un globo por posición en la periferia (líneas sin cruces, cada una termina en un punto visible de su pieza).
- `CON-018`: explosionadas del pivote con buje y tapa sobre el collar y del accionamiento de un lado (bancada, patín, uña, pasadores, cilindro).
- Instructivo de armado, un paso por lámina: `CON-005` (1 base soldada), `CON-014` (2 mesa soldada), `CON-015` (3 pivote en la base), `CON-016` (4 interfaz, lado base, según la alternativa; acero-acero: engrase), `CON-017` (5 buje y mesa sobre el pivote, con interfaz lado mesa), `CON-019` (6 pasadores y pernos), `CON-020` (7 accionamiento), `CON-021` (8 tapas y cubierta), `CON-022` (9 prueba en vacío). Cada paso: lo ya montado en trazo fino, lo que se agrega en trazo grueso y desplazado con flecha de inserción, globos de las posiciones del paso y tabla con posición (cantidad), operación, ajuste/holgura/par a verificar, herramienta y control (número del plan de inspección GEN-003). Izaje de la mesa: medios del montajista.
- `CON-001`: planta 1:10 y corte A-A 1:5 con cotas de instalación (2.560 × 2.560 huella de apoyo, Ø2.000, ejes de guías y cilindros a ±x desde el eje del pivote, ojales de ménsula, R del círculo de pasadores, orejas de izaje, alturas, CG) y tabla de datos de instalación con holguras base–mesa medidas en el 3D. `CON-003`: corte B-B, elevación frontal y detalle del pasador (sin repetir cotas de CON-001).
- Controles nuevos del generador (fallan la generación si no dan 0): `completitud_piezas.csv` (requisitos dimensionales leídos del sólido 3D de cada pieza: extensión total, escalones planos, diámetros/radios, posición de ejes, chaflanes; cada uno debe figurar como cota, llamada o fila de tabla; comerciales justificadas), líneas de cota/referencia sobre textos (el ordenador desplaza el texto; si no es posible, la línea se interrumpe bajo el texto, ISO 128-20) y cruces entre líneas de globos.

## Séptima pasada
- Instructivo: cada paso tiene globos de sus posiciones, flecha de inserción y lo montado en trazo fino; paso 4 acero–acero con la zona de engrase Ø2.020 achurada y llamada; paso 9 con la flecha de giro; paso 3 en vista local.
- CON-006 con planta 1:10 y cortes 1:5; los detalles D1–D4 y la tabla de soldaduras de la base pasan a CON-023. CON-007 con escalas equilibradas.
- GEN-010: plan de corte por franjas con planchas acotadas (ancho comercial o trozo a medida, largo de compra) y aprovechamiento por espesor; GEN-013: posición de cada franja y de las piezas.
- Globos: anclaje en el extremo de la pieza hacia su columna; si quedaran cruces, línea quebrada con intercambio de destinos (control de cruces = 0).

## Reglas del juego de planos
- Cada pieza del despiece tiene plano propio (código de la pieza = número de plano) o referencia a catálogo; cada ítem aparece con globo en un plano de conjunto o subconjunto.
- Cada junta soldada J## tiene símbolo ISO 2553 (flecha, línea de referencia, tamaño a/z, proceso, nivel ISO 5817, WPS, END) y fila en la tabla de soldaduras (global GEN-007 y por lámina). Tamaños: parámetros w_* del núcleo; donde el núcleo no los da, mínimo AWS D1.1 T5.8 por la parte más gruesa, rotulado «mínimo AWS, a confirmar».
- Materiales: donde el cálculo solo fija Fy, el grado comercial más económico que lo cumple se rotula «PROPUESTO por Fy del cálculo; confirmar» (GEN-005). WPS: tabla de WPS pre-calificados propuestos (GEN-012, «PROPUESTA — A CALIFICAR/CONFIRMAR POR EL FABRICANTE»). Pintura: ISO 12944 C4 alta, 240 µm, «PROPUESTA, CONFIRMAR» (GEN-006). «A DEFINIR» queda solo para firmas del cajetín, decisiones del mandante (retención axial del pivote, izaje de la mesa) y marca/modelo de catálogo.
- Torques de pernos: PROPUESTA, A CONFIRMAR POR EL CALCULISTA (GEN-008).

- `revision_visual.md`: registro de la revisión visual lámina por lámina (qué se abrió, qué se vio, qué se corrigió).
