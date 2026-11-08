# Entregables Rev. C TT300-C: memoria de cálculo; los planos se generan a pedido

Estado del juego de planos: **EMITIDO PARA REVISIÓN, revisión C** (códigos TT300C-…-C). **ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO.** DIBUJÓ/REVISÓ/APROBÓ: A DEFINIR (con casillas de firma y fecha).

## Contenido de esta carpeta
- `TT300-C_Memoria_RevC.docx/.pdf`: memoria de cálculo (texto negro, hipótesis → desarrollo → resultado). Regenerar con `npm run memoria` (necesita `python-docx` y LibreOffice `soffice`); el .docx y el .pdf se copian a esta carpeta.
- `TT300-C_design.json`: diseño por defecto exportado por `node tools/export_design.js` (fuente única del cálculo y de los planos).
- `TT300-C_alternativas.json`: datos de los capítulos 9 y 10 de la memoria (`node tools/export_alternativas.js`).

Desde el 08-11-2026 el repositorio **no guarda juegos de planos** (ni PDF, DXF, STEP, despiece ni los controles del paquete). Los juegos anteriores siguen en el historial de git.

## Cómo obtener los planos (a pedido)
1. En Windows, una sola vez: `Instalar_generador_planos.bat` (raíz del repositorio). Busca Python 3.12 o 3.11, crea `.venv-planos` e instala `requirements-planos.txt`.
2. Cada vez: `Generar_planos_Tornamesa.bat`. Levanta el generador local en http://127.0.0.1:8765 y abre la herramienta `Tornamesa_v<versión>.html`.
3. En la herramienta: elija la alternativa (selector de interfaz de giro, casillas de madera y fijación) y los parámetros. En la pestaña **Planos**, pulse «Generar planos» (unos 4 a 6 minutos).
4. Al terminar, la pestaña muestra los tres grupos **Generales**, **Fabricación** y **Armado**, cada uno con su PDF y la lista de láminas, más el PDF combinado, el despiece XLSX, el modelo STEP y el ZIP de DXF. Todo queda en `salidas/<fecha-hora>_<alternativa>/`, que git ignora. El historial de la pestaña reabre las generaciones anteriores sin regenerar.

Sin la herramienta (Linux o macOS, con las dependencias de `requirements-planos.txt`):

```
echo '{"opt_uhmw":1}' > parametros.json     # A: {"opt_ss":1}; A pegado: {"opt_ss":1,"fix_mode":2}; B: {"opt_uhmw":1}; C1/C2/C3: {"opt_bz":1,"bz_conf":1|2|3}; madera: {"opt_wood":1}
node tools/export_design.js parametros.json > diseno.json
python3 cad/generar_paquete.py diseno.json --out /tmp/tt300c --entrega salidas/mi_juego
python3 tools/indice_planos.py salidas/mi_juego      # PDF por grupo e indice_planos.json
```

El generador se niega a emitir (código ≠ 0) si el diseño no gira, la estructura no cumple o falla un control de calidad.

## Simulación del movimiento en GIF
En la herramienta, botón **Simulación** → elija sentido, carreras, velocidad y fricción → **Exportar GIF**. El GIF (GIF89a, codificado en el propio navegador, sin bibliotecas externas) muestra la planta y el detalle de la estación de un cilindro lado a lado, con un rótulo con la alternativa (accionamiento, interfaz y cubierta), θ, fase y tiempo; la duración de cada cuadro es el tiempo real del caudal de avance y de retorno dividido por la velocidad elegida, con más cuadros en el retorno. Se descarga como `TT300-C_simulacion_<alternativa>.gif` y queda en vista previa dentro de la ventana.

Sin abrir el navegador (mismo codificador, con Playwright y chromium):

```
node tools/gif_simulacion.js --alt B,W --sentido horario --carreras 2 --velocidad 1 --salida salidas/
node tools/gif_simulacion.js --alt AF2 --param W_tf=250 --salida mi_simulacion.gif
node tools/gif_simulacion.js --alt C1 --param drive_mode=2 --sentido horario --salida salidas/   # modo pivotado tipo KIET
```

`--alt`: 0 (base), A, AF2, B, C1, C2, C3, más W para la cubierta de madera; `--friccion nom|dis`; `--param k=v` cambia cualquier parámetro del formulario.

## Contenido del juego que emite el generador
- `planos/`: una lámina por archivo, PDF y DXF (A1 y A2, método de proyección E, letra ≥ 3,5 mm en el plot, tablas 3,0 mm, mínimo 2,5 mm). Series: `GEN` (generales), `CON` (conjunto general, despiece, explosionadas, instructivo de armado y subconjuntos) y láminas de pieza con el código del ítem (`BAS`, `IZA`, `ACC`, `MES`, `PIV`, `INT`, `MAD`).
- Grupos (`tools/indice_planos.py`, por el título de cada lámina): **Armado** = títulos con EXPLOSIONADA, MONTAJE, SECUENCIA o ARMADO; **Generales** = GEN-*, CON-001 a CON-003 y los títulos con DESPIECE COMPLETO o CONJUNTO GENERAL; **Fabricación** = el resto. Cada grupo en `TT300-C_Planos_{Generales,Fabricacion,Armado}_RevC.pdf`.
- `TT300-C_Planos_RevC.pdf` (combinado con marcadores), `TT300-C_DXF_RevC.zip`, `TT300-C.step`, `TT300-C.glb`, `TT300-C_despiece.csv/.xlsx`, `soldaduras.csv`, `lista_de_cortes.csv`, `metricas_laminas.csv`, `chequeo_cotas.csv`, `completitud_piezas.csv`, `control_cadenas.csv`, `checklist_piezas.csv`, `informe_paquete.md`, `lista_verificacion_revisor.md/.pdf`, `TT300-C_masas3d.json` y `TT300-C_design.json`.

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

- Registro de la revisión visual lámina por lámina (historial de QA de las pasadas anteriores): `docs/qa/revision_visual_RevC.md`.
