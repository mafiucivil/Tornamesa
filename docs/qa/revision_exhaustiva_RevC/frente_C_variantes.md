# TT300-C Rev. C, frente C: láminas específicas de cada variante de interfaz y cubierta

Revisor independiente. Fecha: 08-11-2026. Solo hallazgos: no se editó nada en /home/user/Tornamesa ni en los juegos de planos.

**Fuentes:** `rvp/{base,A,AF2,B,C1,C2,C3,W}/planos/*.pdf|.dxf`, `TT300-C_design.json`, `TT300-C_despiece.csv`, `soldaduras.csv` y `metricas_laminas.csv`. Los PDF no tienen capa de texto (pdftotext da vacío), así que el texto se extrajo de los DXF gemelos con ezdxf. Las coordenadas `y x` que se citan son mm de hoja A1 del DXF. Las láminas se leyeron como imagen con `pdftoppm -r 170`.

**Fuera de alcance:** ACC-*, CON-010, CON-018 y los pasos de montaje del accionamiento.

**Escalas verificadas midiendo sobre la imagen**, sin desvíos:
- A INT-001: 1:5, 1:1 y 5:1.
- B INT-007: 1:2,5 y 1:1.
- B INT-008: 1:2 y 2:1.
- C3 INT-001, sección B-B: 2:1.
- C1 INT-102: 5:1 y 1:50.
- W MAD-001: 1:10, 1:1 y 2:1.
- W MAD-002: 1:10 y 2:1.

**Nota obligatoria:** está presente, textual, en todas las láminas revisadas (búsqueda exacta en los DXF).

---

## 1. Matriz variante × lámina presente (contenido real de cada código)

| Lámina | base | A | AF2 | B | C1 / C2 / C3 | W |
|---|---|---|---|---|---|---|
| INT-001 | – | Disco base inox e15 | Disco base inox **e6** | Disco base inox e15 | **Placa de bronce con tapones** (C3: pastillas) | – |
| INT-002 | – | Disco mesa inox e15 ranurado | Disco mesa inox **e8** ranurado | Disco mesa inox e15 "liso" | – (el código **INT-002-C** se usa como *pieza* "tapón de grafito", con plano INT-001) | – |
| INT-003 | – | Barra de tope, base | **Graseras** | Barra de tope, base | **Disco duro** (C2: **2.ª placa de bronce**) | – |
| INT-004 | – | Barra de tope, mesa | – | Barra de tope, mesa | Barra de tope, base | – |
| INT-005 | – | Tornillos M6 ISO 10642 | – | Tornillos M6 | Barra de tope, mesa | – |
| INT-006 | – | – (sí existe como *pieza* INT-006-C: tornillo de la mesa) | – | – (ídem) | **Tornillos M6** | – |
| INT-007 | – | **Graseras** | – | **Lámina UHMW** | – (sí existe como *pieza* INT-007-C: tornillo de la mesa) | – |
| INT-008 | – | – | – | **Barra del rebaje UHMW** | **Graseras** | – |
| INT-101 | – | Ranuras de engrase (disco de la mesa) | Ranuras (disco de la mesa) | – | Ranuras (placa de bronce de la base) | – |
| INT-102 | – | – | – | – | Patrón de tapones de grafito | – |
| MAD-001 | – | – | – | – | – | Tablones |
| MAD-002 | – | – | – | – | – | Anillo de contención |
| CON-012 | – | ✔ | ✔ | ✔ | ✔ | **– (no existe)** |
| CON-030 | **– (no existe)** | ✔ | ✔ | ✔ | ✔ | ✔ (solo la posición MAD-002) |
| CON-001 / CON-002 | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| Total de láminas | 54 | 63 | 60 | 63 | 64 | 57 |

**Coherencia con el JSON:**
- **Ranuras de engrase (INT-101):** existen donde `apoyo.interfaz.gr = 1`, es decir en A, AF2, C1, C2 y C3. B tiene `gr = 0` y no tiene ni INT-101 ni graseras. Eso es coherente, pero ver H-30.
- **Topes y tornillos:** existen donde `fix_mode = 1`. AF2 tiene `fix_mode = 2`, `tTope = 0` y `topes = []`, y no tiene láminas de tope ni de tornillos. Eso es coherente, pero las notas no lo son: ver H-03 y H-07.
- **C1, C2 y C3:** las tres no tienen INT-002; INT-006 e INT-102 solo existen en C.
- **Problema de fondo:** un mismo número de plano designa piezas distintas según la variante (ver H-04).

**Material y espesores contra `TT300-C_design.json`:**

| Variante | JSON (`apoyo.interfaz` / `interfazGeom`) | Planos | ¿Coincide? |
|---|---|---|---|
| A | tss = tss2 = 15; topes de L = 170; delta 30 | INT-001/002: e = 15, muesca 22×170, inoxidable A240 | Sí |
| AF2 | tss = 6, tss2 = 8; sin topes; delta 14 | INT-001: e = 6; INT-002: e = 8; sin muesca | Sí en espesores. Las notas no coinciden (H-07) |
| B | discos 15/15 (`capas: 2`); UHMW tuh = 25 (tuhReq 14,08); junta 1,8; barra de L 769 × h 23 | INT-007: UHMW-PE PE1000, e = 25, junta 1,8, 2,54 kg; INT-008: barra 20×769×23 | Sí |
| C1 | tbz = 15 (bronce, L = 205); disco duro 15 (FyC = 1000, L = 150); 2640 tapones | INT-001: 22×205; INT-003: 17-4PH ≥ 1000 MPa, 22×150; 2.640 tapones | Sí, salvo los tapones por sector (H-16) |
| C2 | 2.ª placa de bronce Fy 97, L = 355 | INT-003: "C93200, Fy ≥ 97", muesca 22×355; barra de tope 20×355 | Sí |
| C3 | pastillas, cov 0,9, j = 0, 2364 tapones | INT-001: cubrimiento 0,9; 2.364 tapones; vista lateral 235,07 | Parcial (H-18) |
| W | t_wood 50; anillo 10×50, Ø2000/Ø1980; m 24,54 kg | MAD-001: e = 50, Ø1.980; MAD-002: 10×50, Ø2.000, 24,5 kg | Sí. MAD-001 da 128,0 kg contra 137,1 kg del núcleo, que el propio JSON declara conservador |

**Diferencias reales entre C1, C2 y C3 que se ven en los planos:**
- **C1:** placa de bronce con 2.640 tapones y disco duro 17-4PH de e = 15 con muesca 22×150. Tornillos de la mesa a r = 366,4 y 875,9. Barra de tope de la mesa 20×150. Conjunto de 681,5 kg.
- **C2:** misma placa 1 que C1. La 2.ª placa es de bronce "p. ej. C93200, Fy ≥ 97", sin tapones, con muesca 22×355. Tornillos de la mesa a r = 315,1 y 877,5. Barra de tope de la mesa 20×355 (17,4 kg en total). Conjunto de 656,2 kg.
- **C3:** igual a C1, salvo que el bronce va en pastillas (cubrimiento 0,9, ancho exterior 235,07, 11,45 kg) con 2.364 tapones.
- **Sin diferencias:** INT-004, INT-006 (salvo los radios de C2), INT-008 e INT-101 son idénticas entre C1, C2 y C3, salvo el subtítulo. INT-102 de C2 es idéntica a la de C1.

---

## 2. Hallazgos

| ID | Variante(s) | Lámina | Vista/zona | Hallazgo | Evidencia exacta | Severidad | Corrección propuesta |
|---|---|---|---|---|---|---|---|
| H-01 | B | INT-008, INT-007, INT-001, CON-012 | Notas; planta; vista lateral; corte radial | La posición de las 24 barras del rebaje UHMW (L 769, soldadas al disco de la base) es contradictoria y ninguna lámina la define. INT-008 las pone **sobre la bisectriz**. La geometría del UHMW las pone **en la junta entre sectores**: una franja de 1,8 + 20. Si fueran en la bisectriz, cruzarían la muesca 22×170 del tope del disco de la base. Si van en la junta, quedarían soldadas sobre la junta de dos sectores "desmontables". Ninguna planta las dibuja. | INT-008, nota 3: "posición angular ±0,1° (bisectriz del sector)"; GD&T "Posición angular respecto de la bisectriz". INT-007, vista lateral: "239,42" (cuerda 261,05 − 1,8 − ≈20). Despiece pos. 38: "junta en frío 1,8 mm + barra de 20". JSON `cortes.uhmw`: `strip: true`, `V_junta 473605` (= 25 × 869 × 21,8). INT-001 (B): "Muesca del tope 22 × 170 centrada a r = 676,8". CON-012 (B): la planta muestra solo las muescas; en el "CORTE RADIAL POR LA BISECTRIZ DEL SECTOR 1" el globo 39 apunta a una línea y la barra no está dibujada. | Crítica | Definir la posición angular y radial de la barra (cotas en planta en INT-001 B, INT-007 y CON-012), el ancho y el radio de la franja o ranura del UHMW, y resolver el cruce con la muesca del tope o con la junta de los sectores. |
| H-02 | C1, C2, C3 | INT-001, INT-102 | Tabla "PATRÓN DE TAPONES"; tabla de alojamiento | La lámina se emite declarando que la pieza **no cumple** su propio criterio de fracción mínima de grafito. | INT-001: "Cumple la fracción mínima: NO (mínimo 0,2)"; "0,097 / 0,145 / 0,097" (C3: 0,096). INT-102: "mínimo de lubricación 0,2 → NO cumple (hallazgo del cálculo)". | Crítica | Que el calculista resuelva el patrón (Ø, paso, profundidad) o el criterio antes de liberar C. Mientras tanto, marcar la lámina como "RETENIDA". |
| H-03 | AF2 | CON-012, INT-001, INT-002 | Notas del subconjunto; despiece | En AF2 no está definido en estas láminas cómo se transmite el par. No hay topes, no hay tornillos y los sectores van "pegados" sin especificar el adhesivo en ninguna lámina INT ni en el despiece. Al mismo tiempo, CON-012 afirma que el par lo toman topes soldados y tornillos que no existen. | CON-012 (AF2): "2. … muescas de tope en la bisectriz", "3. Los tornillos de posición solo posicionan … el par lo toman los topes soldados", "4. Ver láminas de sector, tope, tornillos…", tabla "COORDENADAS DE LOS SECTORES (tope en r_u = 676,8…)" con columnas x/y del tope. Despiece: solo pos. 32, 33 y 34 (discos y grasera). INT-001/002: "NO desmontable (sectores pegados)". JSON: `fix_mode 2`, `tTope 0`, `topes []`. El adhesivo solo aparece como pendiente en CON-016 y GEN-009: "adhesivo estructural, preparación de superficie, espesor de capa y curado A DEFINIR POR EL CALCULISTA". | Crítica | Especificar en INT-001/002 y CON-012 el adhesivo (tipo, espesor de capa, preparación, curado, ensayo), con su posición en el despiece. Borrar las notas y tablas de topes y tornillos de CON-012 (AF2). |
| H-04 | Todas con INT | INT-*, CON-012, CON-030, GEN-001 | Rótulo; despiece | Los mismos códigos de plano y de pieza con la misma revisión C designan piezas distintas según la variante. El orden de las láminas tampoco sigue la numeración. | INT-003 es "BARRA DE TOPE DE LA BASE" en A y B, "GRASERAS" en AF2 y "DISCO DURO / 2.ª PLACA" en C. INT-007 es graseras en A y "LÁMINA DE UHMW-PE" en B. INT-008 es "BARRA DEL REBAJE UHMW" en B y graseras en C. INT-001 es disco inox en A, AF2 y B, y bronce en C. La pieza INT-002-C es "Disco de la mesa" en A y B y "Tapón de grafito" en C. La pieza INT-006-C es tornillo de la mesa en A y B, pero INT-006 es la lámina de tornillos en C. Orden: en B, INT-007 es la lámina 48 e INT-003 la 49, e INT-008 es la 51 e INT-005 la 52; en C, INT-003 es la 46 e INT-001 la 47. Las juntas tampoco son estables: J19 es "Barras de tope – plancha base" en A, B y C, y "Anillo de contención de la madera" en W. | Mayor | Asignar códigos fijos por pieza para todas las variantes (por ejemplo, un bloque por opción: INT-A0x, INT-B0x, INT-C0x) o un sufijo de variante en el número de plano. Ordenar las láminas por código. |
| H-05 | AF2 | Todas (rótulo), CON-012 | Rótulo, campo PROYECTO | El rótulo no distingue AF2 de A. | Subtítulo de todas las láminas AF2: "Interfaz: Opción A: dos discos de acero inoxidable con grasa (base liso, mesa ranurado)". CON-012 se titula "OPCIÓN A…". En CON-001 la fila "Carga de diseño / interfaz" dice lo mismo. Los discos son de e = 6/8 y van pegados. | Mayor | Subtítulo del tipo "Opción A, fijación modo 2: discos inox e6/e8 pegados, sin topes". |
| H-06 | W | CON-001, CON-002, CON-030, MAD-001, MAD-002 | Rótulo | El rótulo no distingue W de base. | Subtítulo en todas las láminas W: "Interfaz: Acero-acero con grasa grafitada (sin interfaz alternativa)". En CON-001 (W), la fila "Carga de diseño / interfaz" es idéntica a la de base. Solo los títulos de MAD-001/002 nombran la madera. | Mayor | Añadir "con cubierta de madera e = 50 y anillo 10×50" al subtítulo y a la tabla de CON-001. |
| H-07 | AF2 | INT-001, INT-002 | Notas 1, 4 y 5; GD&T | Quedaron notas de topes y tornillos en piezas que no tienen muesca ni avellanados. | INT-001, nota 1: "avellanado en taladro radial". Nota 4: "chaflán de alivio 45° en el canto de la muesca, del tamaño indicado en la lámina del tope". Nota 5: "posición de la muesca ±0,2". GD&T: "Muesca del tope respecto de la bisectriz del sector (A) 0,2". Las plantas no tienen muesca ni agujeros y no existe lámina de tope. | Mayor | Borrar las notas y el GD&T de la muesca y los avellanados en AF2. |
| H-08 | B | INT-007 | Notas 3 y 5; GD&T | Las tolerancias de la lámina UHMW se contradicen y quedaron referencias a una muesca inexistente. | Nota 3: "Cara deslizante: sin mecanizado de precisión; sobreespesor de relapeado 0,5 mm". Nota 5: "espesor e ±0,1 … planitud de la cara deslizante 0,05". GD&T: "Planitud 0,05" y "Muesca del tope respecto de la bisectriz del sector (A) 0,2". La tabla de parámetros no tiene fila de muesca. La planta y el corte A-A no muestran franja ni ranura. | Mayor | Dar tolerancias acordes a UHMW cortado sin rectificar; borrar el relapeado y la muesca; acotar la franja o ranura de la barra. |
| H-09 | B | INT-008 | Detalle J21; nota 4; nota 2 | El detalle de la soldadura dibuja como pieza base la lámina UHMW en lugar del disco inox de 15. Además, la nota 4 copia la muesca de 22 del tope. | "DETALLE J21: FILETE EN T z6": la pieza base está rotulada "t = 25" (espesor del UHMW), pero según la nota 2 la barra se suelda "a el disco inoxidable de la base" (e = 15). Nota 4: "El sector va con muesca de 22 mm (1 mm de holgura por lado)", contra la franja 1,8 + 20. Errata: "a el". | Mayor | Rotular t = 15 (disco de la base) y redactar la nota 4 con la franja real. |
| H-10 | B | INT-001 | Toda la lámina | El disco de la base de B recibe 24 barras soldadas (J21, 36,9 m), pero su lámina es copia de la de A y no muestra la barra, la soldadura ni la secuencia. | `sdiff A INT-001` contra `B INT-001`: la única diferencia es el subtítulo. CON-012 (B), J21: "Barras del rebaje UHMW – disco inoxidable de la base … 36.912". | Mayor | Hacer de INT-001 (B) un plano de subconjunto soldado (disco + barra), con la posición y la secuencia de J21. |
| H-11 | A, AF2, C1, C2, C3 | INT-002 (A, AF2), INT-003 (C), INT-007, INT-003 (AF2), INT-008 (C), INT-101 | Tabla de parámetros; tabla de graseras; GD&T | Los 4 conductos Ø6 de engrase están a 45°, 135°, 225° y 315°, que son **líneas de junta entre sectores**, no bisectrices. Queda sin definir qué sector se taladra, y el conducto cae sobre la junta en frío de 1 mm. | INT-002: "4 × Ø6 +0,2/0 axial pasante a r = 970, en los sectores de las graseras (45°, 135°, 225°, 315°)". Tabla de sectores: n.º 3, "30° / 45°"; n.º 4, "45° / 60°". INT-007 (A), GD&T: "Ø0,5 A – Posición angular del conducto respecto de la bisectriz del sector". | Mayor | Mover los conductos a bisectrices (por ejemplo 37,5°, 127,5°…) o definir explícitamente el medio taladro en cada sector. Corregir el dato de referencia del GD&T. |
| H-12 | A, AF2, C1, C2, C3 | INT-101 | Nota 2; tabla; detalle "SECTOR DE 15° CON SUS RANURAS" | Las 12 ranuras radiales a k·30° coinciden con juntas de sector y solo caen en una de cada dos juntas, así que los sectores no pueden ser idénticos. La nota lo afirma y el detalle omite las radiales. | Tabla: "12 × a k·30°; de R131 a R1000". Nota 2: "el trazado se repite igual en cada sector (los sectores de 15° se mecanizan idénticos)". GD&T: "Posición de las ranuras radiales respecto de la bisectriz del sector (A) ±0,5". El detalle 1:2 muestra solo las 3 circunferenciales. | Mayor | Definir dos tipos de sector (pares e impares) o radiales sobre la bisectriz; dibujar las radiales en el detalle; corregir el GD&T. |
| H-13 | A, AF2, C1, C2, C3 | INT-007 (A), INT-003 (AF2), INT-008 (C) | Nota 1; ficha; corte A-A | La grasera y el taladro radial se asignan a "la plancha inferior de la mesa", que es Ø1.720 (r = 860) y no llega a R970. Entre r = 860 y r = 1000 está MES-004, el anillo inferior. El corte A-A no dibuja la pieza que aloja la grasera, ni el taladro radial, ni la rosca M10×1. La grasera está dibujada como un rectángulo de 12×10 y la isométrica es un cilindro que ocupa el centro de la hoja. | Nota 1: "en el canto de la plancha inferior de la mesa; rosca M10×1 (ISO 261) prof. 12". Despiece MES-003: "Disco Ø1.720×16"; MES-004: "Anillo Ø2.000/Ø1.720×27". "CORTE A-A POR LA GRASERA G1 … TALADRO Ø6 RADIAL Y AXIAL": solo se ve el disco de 15 y la grasera flotando ("8,5", "10", "33,5"). | Mayor | Referir la grasera a MES-004; dibujar el corte con el anillo, el taladro radial Ø6 hasta R970, el axial y la rosca. Representar la grasera según DIN 71412 o como referencia comercial. |
| H-14 | A, B, C1, C2, C3 | INT-001/002 (A, B), INT-003 (C), INT-001 (C), INT-005 (A, B), INT-006 (C) | Sección B-B; ficha; nota 4 | La profundidad del avellanado de un mismo tornillo M6 ISO 10642 se contradice entre láminas, y el avellanado está acotado de forma incompleta. | INT-005, nota 4: "cabeza al ras o hundida ≤ 0,2 mm"; ficha de INT-005/006 (A, B): "cabeza 0,5 bajo la cara deslizante". Sección B-B del disco inox: avellanado de 3,5 (2,7 + 6,6 + 2,7 = 12). Sección B-B del bronce (C INT-001): "4 / 11 / 15", sin acotar Ø6,6. En ningún caso se acota el ángulo de 90° ni el tramo cilíndrico. El avellanado Ø12 es igual al dk máx. de ISO 10642, sin holgura ni tolerancia. Nota 1: "cabeza hundida 12 mm" (redacción ambigua). | Mayor | Un único detalle de avellanado (por ejemplo Ø12,4 o Ø13 × 90°, con profundidad tolerada) con la condición de enrase y en coherencia con el sobreespesor de relapeado de 0,5. |
| H-15 | C1, C2, C3 | INT-001 | Planta; tabla de parámetros | La llamada de la planta pide 4 tornillos por sector, en radios que son posiciones de tapones. La tabla y el dibujo tienen 2. | Llamada: "4 × M6 ISO 10642 (avellanado Ø12, pasante Ø6,6) a r = 196,7 y 352,6 y 393,4 y 877,5". Tabla: "2 por sector, M6, a r = 352,6 y 877,5". Planta: 2 agujeros. JSON `tap.nTor = 2`. INT-102, tabla de coordenadas: tapón 1 en "196,7 / 0,09°" y tapón 14 en "393,4 / 0,09°". | Mayor | Corregir la llamada a "2 × M6 … a r = 352,6 y 877,5". |
| H-16 | C1, C3 (C2 = C1) | INT-001, INT-101, INT-102 | Notas de tapones | El número de tapones por sector y la tolerancia del alojamiento se contradicen entre láminas. | C1: INT-001 dice "108 tapones de grafito Ø12 por sector"; INT-101, "108 × Ø12 H12"; INT-102, "106 × Ø12 H7 (alojamiento)" con la tabla alternando 106/114 (JSON `porSector [106,114,114,106…]`; 108 × 24 = 2.592 ≠ 2.640). C3: INT-001 dice "102"; INT-101, "102 × Ø12 H12"; INT-102, "100 × Ø12 H7" (JSON [100, 97, 97, 100…]). | Mayor | Unificar los conteos con el JSON por sector y fijar una sola tolerancia (H7 con tapón p6, según INT-102). |
| H-17 | C1, C2, C3 | INT-102 | Tabla de coordenadas; planta completa | Solo se dan coordenadas del sector 1 y se dice que el resto es "repetición angular", pero los sectores alternan 106 y 114 tapones (C3: 100 y 97). Los sectores de 114 o 97 no tienen patrón. La planta completa a 1:50 se ve como un disco negro sin información. | "COORDENADAS DE LOS 106 TAPONES DEL SECTOR 1 (… el resto de sectores es una repetición angular)". Tabla "TAPONES POR SECTOR": 106, 114, 114, 106… "PLANTA COMPLETA: 24 SECTORES, 2.640 TAPONES ESC 1:50". | Mayor | Dar coordenadas por tipo de sector (A y B) y quitar o ampliar la planta 1:50. |
| H-18 | C3 | INT-001 | Planta; vista lateral; tabla de sectores | La geometría de la pastilla no está definida. La planta sigue siendo un sector completo de 15° con junta de 1 mm, mientras la vista lateral da un ancho reducido. No se acota el ancho angular ni el hueco entre pastillas. | Planta: "sector de 15°", "15°". Tabla: "junta en frío 1 mm". Vista lateral: "235,07", contra 260,06 en C1. JSON: `cortes.bz0.j = 0`, `cov 0,9`. Elevación: "173,38 / 262,08 / 427,52". | Mayor | Dibujar y acotar la pastilla real (ángulo o ancho, radios y holgura entre pastillas) y su tabla de posiciones. |
| H-19 | C1, C2, C3 | INT-001, INT-003 | Material; tratamiento | La especificación de materiales es ambigua o alternativa. | Bronce: "ASTM B148 C95400 / B584; confirmar con el proveedor" (dos familias de aleación distintas). 2.ª placa (C2): "Bronce de aleación distinta del de la placa 1 (p. ej. C93200)". Disco duro: "17-4PH H1025 o inoxidable nitrurado, Fy ≥ 1.000 MPa", con tratamiento "Temple y revenido a ≥ HB indicado; nitrurado si es inoxidable" (el 17-4PH se endurece por precipitación, no por temple y revenido). INT-001, nota 6: "Tratamiento: —." | Mayor | Una designación por pieza (norma, grado y estado) y el tratamiento coherente con ella. |
| H-20 | A, AF2 | INT-002, INT-101 | Nota 6; rótulo | Se exige una diferencia de dureza de 50 HB entre dos discos del mismo material austenítico, sin grado, sin valores de HB y sin proceso. | "dureza distinta del disco de la base (≥ 50 HB de diferencia, ASTM G98)". Material de los dos discos: "Acero inoxidable austenítico ASTM A240 (Fy ≥ 205 MPa)"; tratamiento "Decapado y pasivado". | Mayor | Indicar grado y HB mínimo de cada disco y cómo se consigue (por ejemplo 304 recocido y un grado o tratamiento de mayor dureza). |
| H-21 | W | MAD-002 | Ficha contra símbolo y tabla | El tamaño del filete de J19 se contradice. | Ficha y despiece: "soldada a la plancha superior (filete 6 a ambos lados)". Símbolo, detalle y tabla: "z8", "a = 5,7", "DETALLE J19: FILETE EN T z8". | Mayor | Unificar en z8 (o en el valor que dé el cálculo). |
| H-22 | W | MAD-002, CON-001 | Detalle J19; tabla de soldaduras | J19 refiere el anillo a MES-001, de t = 20, pero el anillo Ø2.000/Ø1.980 se apoya sobre MES-002 (anillo superior de pasadores, Ø2.000/Ø1.720 × 27). MES-001 es Ø1.720. | Tabla: "Anillo de contención de la madera – plancha superior (MAD anillo / MES-001)". Detalle: "t = 20". Despiece: MES-001 "Disco Ø1.720×20"; MES-002 "Anillo Ø2.000/Ø1.720×27". En el corte A-A de CON-001 (W), el globo 33 está sobre el anillo exterior. | Mayor | Referir J19 a MES-002 con t = 27 y revisar el tamaño mínimo del filete. |
| H-23 | W | MAD-001, MAD-002 | Corte radial; notas | Interferencias geométricas en el borde. El filete interior z8 del anillo (a R990) choca con el canto de los tablones, que solo llevan chaflán de 1×45°. Los bolsillos Ø119 a PCD Ø1.860 llegan a r = 989,5, más allá del extremo del tablón (R990 − 2 mm de holgura), así que el bolsillo abre el canto. El corte radial dibuja el tablón tocando el anillo, sin holgura ni soldadura. | MAD-001, nota 2: "se cortan en arco a R = 990 … holgura de montaje 2 mm"; cuadro: "chaflán de aristas 1×45°; cortar los extremos a R = 990". MAD-002: "filete ambos lados", "z8". MAD-001: "28 × Ø119 +2/0 × 31 +2/0 …, PCD Ø1.860" (930 + 59,5 = 989,5). | Mayor | Acotar un rebaje o chaflán de ≥ 8 mm en el canto inferior del tablón, o soldar solo por fuera. Revisar la posición o el diámetro del bolsillo respecto del borde. Dibujar la holgura y el filete en el corte. |
| H-24 | W | MAD-001 | Planta; nota 4; despiece | Los 28 bolsillos y los tornillos de fijación no están dibujados ni ubicados en la planta (solo hay llamada). El tornillo propuesto, "para madera Ø8 × 80", es más largo que tablón + plancha (50 + 20 = 70) y es de madera para roscar en acero. Los tornillos no figuran en el despiece. | Planta: solo la llamada "28 × Ø119…"; tabla de bolsillos por tablón (4, 4, 4, 8, 8). Nota 4: "PROPUESTA tornillos para madera avellanados Ø8 × 80 en 4 filas, paso 400 mm". Despiece W: solo MAD-001-C y MAD-002-C. | Mayor | Dibujar los bolsillos y las filas de fijación con cotas. Definir un fijador compatible con plancha de acero de 20 (por ejemplo, perno con tuerca soldada o inserto) y su largo. Incluirlo en el despiece. |
| H-25 | W | CON-001 | Tabla "Alturas"; corte A-A | El plano de instalación no da la cota de la cara superior de la cubierta: solo la altura sin cubierta. La planta no muestra tablones ni anillo. | "Alturas: base 18; mesa 210 (cara inferior a z = 18); total sin cubierta 228". La cota "228" llega al acero. | Mayor | Añadir la cota total con cubierta (228 + 50 = 278, a confirmar) y la representación de la cubierta en planta. |
| H-26 | Todas | INT-*, CON-012 | Cotas y textos | Hay solapes de texto con cotas o líneas que `metricas_laminas.csv` no detecta (reporta "choques de texto" = 0). | A INT-002, corte A-A: "22,28 8 Ra 0,4 (cara deslizante)" encimados. INT-101: "30° (paso)" cruzado por las ranuras. B CON-012: "15 25 (uhmw)" en una sola línea vertical. C CON-012: "15 (cara) 15 (bronce)". AF2 CON-012: "6 8". C3 INT-001: el leader de "R131 (radio interior)" cruza "102 tapones…". INT-102: la nota "Patrón escalonado…" cruza la línea de "R1000". | Menor | Reubicar los textos y separar las cotas apiladas. |
| H-27 | B | CON-001 | Planta 1:20 | B es la única variante con la planta de CON-001 a 1:20 (las demás a 1:10), y a esa escala los textos se encima. | Escala "1:5 / 1:20". "4 orejas de izaje en (±600; ±1030) agujero Ø45…" sobre "945 (ojal de ménsula)". `metricas_laminas`: 11,4 % de vistas sobre área útil, contra 22,3 % en A. | Menor | Volver a 1:10 reorganizando la hoja, o reubicar los textos. |
| H-28 | AF2, C2 | INT-001 (AF2), INT-003 (C2) | Rótulo, campo ESCALA | La escala del rótulo no coincide con la del índice GEN-001. | Rótulo: "2:1 a 1:5 (ver vistas)" contra GEN-001 "2:1 / 1:1 / 1:2,5 / 1:5". C2 INT-003: "5:1 a 1:5 (ver vistas)" contra "5:1 / 1:1 / 1:2 / 1:5". | Menor | Listar las escalas explícitamente, como en el resto de láminas. |
| H-29 | Todas con INT | INT-001…003, INT-101 | Plantas | Hay secciones y detalles sin indicación en la vista de origen, y el dato A (bisectriz) no tiene símbolo de referencia. | "SECCIÓN B-B" y "DETALLE C: MUESCA DEL TOPE" no están marcados en la planta (solo existe el corte A-A). El "CORTE A-A" de INT-101 no está marcado en la planta. El GD&T usa "(A)" sin triángulo de referencia. En la sección B-B de A, las líneas auxiliares de Ø12 atraviesan todo el rayado. | Menor | Marcar los planos de corte y los detalles, y añadir el símbolo de referencia A. |
| H-30 | B | INT-002 | Nota 1; rugosidad | El disco de la mesa "liso" de B conserva instrucciones de ranurado. | Despiece: "Disco de la mesa (sector liso)". Nota 1: "ranuras fresadas en mandrinadora/fresadora". Rugosidad: "Ra 1,6 fondo de ranuras". JSON B: `gr = 0`. | Menor | Borrar las referencias a ranuras. |
| H-31 | A, B, C | INT-003/004 (A, B), INT-004/005 (C) | Detalles J19 y J20 | La pieza base del filete está rotulada "t = 15", pero BAS-001 tiene 18 y MES-003 tiene 16. | "DETALLE J19: FILETE EN T z6": "t = 15" (y lo mismo en J20). Despiece: BAS-001 "Plancha 2.560×2.560×18"; MES-003 "Disco Ø1.720×16". | Menor | Rotular el espesor real. |
| H-32 | Todas | INT-001/002, INT-101, CON-012, CON-030 | Notas; fichas | Redundancia: la misma pieza se define en varias láminas con riesgo de divergencia. | Notas 2 y 3 de INT-001/002 repiten "Ra 0,4 … sobreespesor 0,5". INT-101 repite la ficha completa de INT-002-C (A, AF2) o de INT-001-C (C), sin ser el plano de la pieza. CON-012 repite fichas completas y las tablas de soldadura J19, J20 y J21 de las láminas INT. El bloque "GENERALES" y la línea de normas del rótulo se repiten en cada hoja. | Menor | Dejar la definición de la pieza en una sola lámina y que las demás la referencien. Integrar INT-101 en INT-002 (o en INT-001 de C), o quitarle la ficha. |
| H-33 | A, B, C | INT-005 (A, B), INT-006 (C) | Material del tornillo | La misma pieza tiene notas distintas según la variante. | A y B: "10.9 (ISO 10642), inoxidable A4-80 si se exige contacto con grasa y humedad (opción a confirmar)". C: "10.9 (ISO 10642)". Las graseras se dan como "-135°/-45°" en INT-007 y como "225°/315°" en INT-002 e INT-101. | Menor | Unificar la especificación y la notación angular. |
| H-34 | C1, C2, C3 | INT-001, INT-003 | Título | Los títulos genéricos no corresponden a la configuración concreta: el subtítulo sí la identifica, pero el título no. | C1 y C3: "DISCO DURO / 2.ª PLACA (SECTOR)", aunque no hay 2.ª placa. C1 y C2: "PLACA DE BRONCE … (SECTOR / PASTILLA)", aunque no hay pastilla. | Menor | Un título por variante. |
| H-35 | C1 | CON-012 | Corte radial | Las etiquetas de espesor parecen invertidas respecto de los globos. | "15 (bronce)" está en la capa superior (y = 426,4) y "15 (cara)" en la inferior (y = 401,1). En cambio, el globo 35 (INT-004, "Barra de tope (placa de bronce)", soldada a la plancha base) está en la capa inferior, e INT-101 dice "placa de bronce de la base". "cara" no es un término definido. | Menor | Rotular "bronce (base)" y "disco duro (mesa)" en el orden correcto. |
| H-36 | base, W | CON-001, CON-002 | Notas de conjunto; título | Hay referencias cruzadas rotas. | CON-001 de base y de W: "Subconjuntos: … CON-012 (interfaz)", y en esos juegos no existe CON-012. CON-001 (W) no cita MAD-001/002. CON-002 de base se titula "(HOJA 1)", pero base no tiene CON-030. | Menor | Ajustar las notas por variante. |
| H-37 | W | MAD-002 | Notas 1 y 2; tabla de soldaduras | El empalme CJP del anillo (WPS-P06) no tiene identificador de junta, ni END, ni nivel ISO 5817 en la tabla de soldaduras. La cota de radio "1.000" no lleva R. | Nota 2: "empalme con preparación en V y respaldo, esmerilado al ras (WPS-P06, PROPUESTA)". La tabla solo incluye J19. Planta: "1.000". | Menor | Añadir la junta del empalme a la tabla y escribir "R1000". |
| H-38 | W | MAD-001 | Corte por un bolsillo; ficha; planta | El acotado está incompleto o es incoherente. | Llamada "Ø119 +2/0" contra corte "119,5". La profundidad de 31 no se acota en el corte (solo 50). La cota "870" en planta tiene un origen no identificado (no es radio ni diámetro). La ficha dice "Comercial Según catálogo" con Cant 1 para 10 tablones (T1…T5 ±). | Menor | Acotar el bolsillo (Ø y profundidad con tolerancia), definir el origen de la cota 870 y dar en la ficha el escuadrado de partida y la cantidad de tablones. |
| H-39 | A, B, C | INT-001, INT-102, CON-012 | Masas | Hay redondeos inconsistentes. | A INT-001: "14,68 kg" contra JSON 14,689 (debería redondear a 14,69); total "352,3" contra `m_neta` 352,54. | Menor | Redondear las masas de forma consistente con el JSON. |
| H-40 | Varias | INT-005/006, INT-102, INT-008 (B), INT-001 (A) | Ocupación de hoja | Varias láminas A1 tienen muy poco dibujo. | `metricas_laminas.csv`, % vistas sobre área útil: INT-005 (A, B) 5,2; INT-006 (C) 5,4; INT-102 4,5–4,9; INT-008 (B) 7,5; INT-001 (A) 8,1. | Menor | Pasar a A2 o A3, o agrupar piezas pequeñas (tornillos, graseras y barras) en una lámina. |
| H-41 | AF2, C3 | INT-001 | Corte A-A; sección B-B | Hay vistas sin acotar o con cotas que faltan. | AF2, "CORTE A-A POR LA BISECTRIZ ESC 2:1": una banda rayada sin ninguna cota ni línea de rotura. C3, sección B-B: falta Ø6,6. | Menor | Acotar o quitar las vistas. |
| H-42 | Todas | Todas (rótulo) | DIBUJÓ / REVISÓ / APROBÓ | Las firmas están sin asignar. El rótulo de tratamiento queda truncado. | "A DEFINIR" ×3 en cada rótulo. A INT-002 e INT-101, TRATAMIENTO: "…dureza distinta del disco de la base (≥ 50" (texto cortado). | Menor | Completar las firmas y ajustar el texto a la celda. |

### Conteo por severidad

| Severidad | Cantidad | Hallazgos |
|---|---|---|
| Crítica | 3 | H-01, H-02, H-03 |
| Mayor | 22 | H-04 a H-25 |
| Menor | 17 | H-26 a H-42 |
| **Total** | **42** | |

---

## 3. Variante W: cómo está modelada la madera

Solo se describe y se revisa el dibujo. El concepto está en discusión con el cliente y no se juzga.

**Dónde va:**
- La cubierta se apoya sobre toda la cara superior de la mesa: la plancha superior MES-001 (Ø1.720 × 20) y el anillo superior de pasadores MES-002 (Ø2.000/Ø1.720 × 27), con sus caras superiores enrasadas en el corte A-A de CON-001.
- No hay interfaz alternativa: el apoyo es acero-acero con grasa grafitada, igual que en base, y no existe CON-012.

**Tablones (MAD-001):**

| Aspecto | Definición en el plano |
|---|---|
| Material | Madera dura "seca al aire, ρ ≥ 900 kg/m³, p adm. 6 MPa (NCh1198; confirmar con el proveedor)". Humedad ≤ 15 %; preservante a definir por el proveedor. No se define la especie |
| Dimensiones | e = 50 mm, ancho 200 mm ("adoptado por el mandante", S06) |
| Disposición | Tablones contiguos paralelos al eje y, con la junta central en el eje (5 por lado: T1…T5 ±, en x = 0–200, 200–400, 400–600, 600–800 y 800–990). El T5 tiene 190 de ancho |
| Largos | Máx. y mín. por tablón: 1980/1939, 1939/1811, 1811/1575, 1575/1166, 1166/0 |
| Contorno | Extremos cortados en arco a R = 990 (cara interior del anillo), con "holgura de montaje 2 mm" y chaflán de aristas 1×45° |
| Abertura central | Ø240 H12 para la tapa de inspección Ø238, en T1 |
| Bolsillos | 28, de Ø119 +2/0 × 31 +2/0, desde abajo, sobre las cabezas de perno y arandela de los pasadores a PCD Ø1.860 ("S06, PROVISORIO"). Reparto por tablón: 4, 4, 4, 8 y 8 |
| Fijación a la plancha | "PROPUESTA tornillos para madera avellanados Ø8 × 80 en 4 filas, paso 400 mm, con taladro previo (decisión del mandante: confirmar)". No están dibujados ni en el despiece |
| Tolerancias | Planitud de la cara superior 1,0; posición de los bolsillos ±2 respecto de los pasadores |
| Masa | 128,0 kg en el plano; el núcleo da 137,1 kg (conservador) |

**Anillo de contención (MAD-002):**

| Aspecto | Definición en el plano |
|---|---|
| Pieza | Pletina 10 × 50 (alto = espesor del tablón) de ASTM A572 Gr.50, rolada en frío sobre el canto delgado |
| Diámetros | Ø exterior 2.000 (enrasado con el borde de la mesa), Ø interior 1.980 H12 |
| Empalme | 1 empalme CJP en V con respaldo, esmerilado al ras (WPS-P06) |
| Unión a la mesa | Soldado "a la plancha superior" con filete continuo a ambos lados, J19 z8 (a = 5,7), 12.566 mm, ISO 5817-C, VT 100 % y MT 10 %. La ficha dice "filete 6" |
| Función | Nota 4: contiene los tablones y "no tiene función estructural adicional en el cálculo" |
| Tolerancias | Perpendicularidad 0,5 respecto de la plancha; alto 50 ±1; espesor 10 ±0,5 |
| Masa | 24,5 kg |

**En las láminas de conjunto:**
- **CON-001 (W):** el corte A-A muestra la capa de tablones (globo 32) sobre toda la mesa y el anillo (globo 33) en el borde exterior. La planta no los muestra. La tabla de alturas da "total sin cubierta 228", sin la cota de la cara superior de la madera.
- **CON-002 / CON-030 (W):** MAD-001 en CON-002 (posición 32, 128,0 kg) y MAD-002 en CON-030 (posición 33, 24,5 kg). Masa total 3.262,5 kg.
- **Rótulos:** todas las láminas W llevan el subtítulo de base (H-06).

**Problemas de dibujo de esta variante:** H-21 a H-25, H-36, H-37 y H-38.
