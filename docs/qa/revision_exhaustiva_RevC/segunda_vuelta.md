# TT300-C Rev. C: verificación de la segunda vuelta (hallazgos A, B y H)

Revisor independiente. Solo reporto: no edité nada en /home/user/Tornamesa ni en los juegos de planos.

**Material revisado**
- Juegos regenerados `rvp2/<base|A|AF2|B|C1|C2|C3|W>/entrega` (commit c37e014): 55/63/60/63/64/64/64/57 láminas, PDF y DXF, más despiece.csv, soldaduras.csv, informe y design.json.
- Comparación contra `rvp/<caso>/planos` (commit 2fe7950).

**Método**
- Texto con posición extraído de los 920 DXF con ezdxf (`rev2/tx1`, `rev2/tx2`).
- Raster de los PDF a 100–250 dpi, en recortes de ≤ 1600 px.
- Controles automáticos propios:
  - choques texto–texto, nuevos frente a rvp;
  - cotas desaparecidas frente a rvp;
  - referencias cruzadas a láminas o piezas inexistentes;
  - CON-002/030 contra despiece.csv (posición, código, cantidad y masa);
  - índice de GEN-001 contra el rótulo (formato y escala);
  - nota obligatoria y «NOTAS GENERALES: VER GEN-001».
- Coordenadas en mm de hoja, con origen abajo a la izquierda.

**Controles transversales: resultado**
- **Nota obligatoria.** «ESTOS PLANOS NO SON VÁLIDOS PARA FABRICACIÓN HASTA SU REVISIÓN Y APROBACIÓN POR UN INGENIERO CALCULISTA HABILITADO.» está textual en las 490 láminas de los 8 juegos.
- **Remisión a GEN-001.** «NOTAS GENERALES: VER GEN-001» está en todas las láminas. Fuera de GEN-001 no quedan bloques «GENERALES», ni «o R1», ni «13920 clase B».
- **CON-002/CON-030 ↔ despiece.csv.** Coinciden posiciones, códigos, cantidades y masas en los 8 juegos. Totales: base 3.106,7 · A 3.942,0 · AF2 3.499,6 · B 4.164,9 · C1 3.902,8 · C2 3.877,5 · C3 3.873,0 · W 3.259,2 kg.
- **Índice ↔ rótulo.** Formato y escala coinciden en las 490 láminas. Única diferencia: en A, AF2 y C1–C3 la escala de BAS-005 se parte en dos renglones de forma distinta en el índice y en el rótulo.
- **Choques texto–texto nuevos frente a rvp:** 0 en los 8 juegos. El choque de B CON-001 «945 / orejas» desapareció.
- **Cotas desaparecidas frente a rvp:** todas corresponden a sobreacotado o tablas eliminadas a propósito: cadenas de BAS-001, Ø81/Ø114/Ø88,4/Ø71,6, coordenadas de PIV-001, despiece de CON-008, «230» de CON-008 y «0,03» de MES-012. No encontré ninguna cota funcional perdida.

**Decisiones aplicadas: verificación específica**

| Decisión | Resultado |
|---|---|
| Pivote Ø120 p6 en z 0–78 y f7 en z 79–211, juego F7/f7 +72/+142 µm | **OK.** <br>• PIV-001: «Ø120 p6 (+0,059 / +0,037) de z = 0 a 78», «Ø120 f7 (−0,036 / −0,071) de z = 79 a 211», cotas «78 (zona p6…)» y «79 (inicio zona f7: buje)». <br>• GEN-004 y CON-011: «120,036 / 120,071», «119,929 / 119,964», «+72 / +142»; H7/p6 «-59 / -2». <br>• PIV-002: «juego F7/f7 +72/+142 µm». <br>• Límites comprobados contra ISO 286-2 (f −36/−71, p +37/+59, F7 +36/+71, H7 +35). <br>• Queda un riesgo nuevo: ver N-02. |
| Tapa de inspección: 6 × ISO 10642 M8×16, avellanado Ø17×90°, PCD Ø214 | **OK.** <br>• Aparece en PIV-003, CON-011, CON-021, GEN-008 y CON-002/030. <br>• Borde: 119 − (107 + 8,5) = 3,5 ≥ 3. <br>• Pared al Ø200: 107 − 4 − 100 = 3,0 (rosca M8) y 3,6 (broca Ø6,8) ≥ 3. <br>• Avellanado Ø17 > dk máx. 16 de ISO 10642 M8. <br>• Toma de rosca 16 − 8 = 8 mm ≤ rosca 10. <br>• La tapa **retenedora** tiene un problema nuevo: ver N-01. |
| WPS-P11 a 110 °C (J06/J07) y P14 (J17, pared 80) según AWS D1.1-2020 Tabla 5.11 | **OK.** <br>• GEN-012: «WPS-P11 · J06, J07 · 110 °C mín. (t mayor = 78 mm)» en base y W; en A y C 108, en AF2 92 y en B 133 mm, siempre > 65. <br>• «WPS-P14 · J17 · 110 °C (t mayor = 80 mm)». <br>• Tabla de la categoría B: ≤ 19 sin precalentar / 19–38 a 10 °C / 38–65 a 65 °C / > 65 a 110 °C. Coincide. <br>• Coherente en GEN-007, CON-007, CON-023, BAS-005, MES-011 («precal. ≥ 110 °C») y soldaduras.csv. Ver N-16. |
| Tabla ISO 2768-1 según la Tabla 1 | **OK.** <br>• GEN-004 trae f, m, c y v exactos, por ejemplo «más de 30 a 120: ±0,15 / ±0,3 / ±0,8 / ±1,5». <br>• Es idéntica en base, A, B, C1 y W. |
| Notas generales solo en GEN-001 | **OK.** Ver los controles transversales. |
| Códigos INT-001…014 con significado único | **Parcial (H-04).** <br>• El mapa de GEN-001 tiene denominación fija. <br>• Pero un mismo código designa piezas de geometría distinta según la variante. <br>• Ver H-04, N-07 y N-08. |
| Variante en rótulo y título | **OK.** <br>• Subtítulo «Variante X · …» y título «— VARIANTE X» en todas las láminas. <br>• AF2: «Opción A, fijación modo 2: discos inoxidables e6/e8 pegados…». <br>• W: «…con cubierta de madera e = 50 y anillo de contención 10×50». |

## 1. Estado de cada hallazgo

Leyenda: **OK** = corregido · **Parcial** = corregido en parte · **NO** = no corregido · **Regr.** = regresión · **Abierto ✓** = sigue abierto y señalado.

### Frente A

| ID | Estado declarado | Estado verificado | Evidencia exacta |
|---|---|---|---|
| A-01 | Corregido | OK | GEN-004 tabla «ISO 2768-1, TABLA 1»: filas f/m/c/v según norma (p. ej. «más de 1.000 a 2.000: ±0,5 / ±1,2 / ±3 / ±6»). Igual en A, B, C1 y W. |
| A-02 | Corregido | OK | Ver «Decisiones aplicadas». CON-011 nota 1: «zona p6 (z = 0 a 78)… zona f7 (z = 79 a 211) en el buje F7/f7». Riesgo nuevo en N-02. |
| A-03 | Corregido | OK | GEN-012 WPS-P11 a 110 °C (t = 78). soldaduras.csv J06/J07: «WPS-P11… (t = 78 mm)». |
| A-04 | Corregido | OK | CON-002: BAS-006 «Plancha 155×180×25», BAS-007 «Plancha 155×180×80», con la nota «Ancho mecanizado a 150 −0,5». |
| A-05 | Corregido | OK | CON-001, raster del corte A-A: globos 1, 2, 23, 12, 20, 18, 24, 10, 17, 14, 15, 19, 11, 16, 13, 9 y 4, todos sobre piezas cortadas. Se quitaron 3, 8, 21 y 22. |
| A-06 | Corregido | OK | CON-001 (base): «Subconjuntos: CON-006/023 (base), CON-007 (ménsula), CON-008/009 (mesa), CON-010…, CON-011 (pivote)». |
| A-07 | Corregido | OK | CON-006: «D1 (CON-023)»…«D4 (CON-023)» y «PLANTA (llamadas D1–D4: detalles en CON-023)». |
| A-08 | Corregido | **Parcial** (Menor) | CON-003 tiene «CORTE X-X POR EL EJE DE UN PASADOR (… plano a 6,429° de +x)», pero ninguna vista lleva traza ni letras «X». CON-011 tiene «DETALLE Y / ESC 1:2» sin llamada «Y» en el corte, sin título descriptivo y con las cotas «15» y «53» apiladas. |
| A-09 | Corregido | **Parcial** (Mayor) | CON-003, corte X-X: las cotas 27/156/27 y «Ø85 H7/m6» ya están. Faltan dos cosas: (1) el pasador sigue rayado en corte longitudinal; (2) el perno M20 no se dibuja: el agujero roscado queda vacío y la cabeza aparece como un bloque mitad rayado sobre la arandela. |
| A-10 | Corregido | OK | CON-009: «DETALLE J12… t = 20 / 27», «DETALLE J13… t = 19 / 30», «b = 3» y «24 (chaflán 1:4)». Ver N-03 (27 frente a 30). |
| A-11 | Corregido | OK | CON-002 MES-008/009/010: «Plancha e = 6 (anidado GEN-010/013) 146×178×6 / 288×178×6 / 248×178×6». Ver N-04. |
| A-12 | Corregido | OK | CON-002 pos. 11 y 13: «4 × segm. de anillo 90° Ø2.010/Ø1.710×30». |
| A-13 | Corregido | OK | CON-002: «Disco Ø260×65… caras planeadas a 60 y Ø250 torneado». BAS-002 J09: «65 (ancho radial; alto 60)». despiece.csv: «desde plancha de 65 mm». |
| A-14 | Corregido | OK | Material único «C45 (EN 10083-2) templado y revenido a 300–370 HV» en CON-002, GEN-008 y MES-013. |
| A-15 | Corregido | OK | GEN-008: «Certificado del lote EN 10204 3.1». No queda «2.2» en el juego. |
| A-16 | Corregido | OK | El juego base no tiene «grasera» ni «71412». |
| A-17 | Corregido | OK | CON-002 «(HOJA 1 DE 2)». CON-030 «(HOJA 2 DE 2, CONTINUACIÓN DE CON-002)» lleva los 8 comerciales con «Plano: GEN-008». |
| A-18 | Corregido | OK | M8×16 en PIV-003, CON-011, CON-021, GEN-008 y CON-030. El M10×25 de la tapa retenedora tiene un problema nuevo (N-01). |
| A-19 | Corregido | **Parcial** (Menor) | Se eliminaron inox, UHMW, madera y A240 del juego base. Quedan en base y W: GEN-003 n.° 12 «juntas en frío entre sectores con galga (CON-012)» y, en CON-030/despiece, «llenado de ranuras». Ver N-09. |
| A-20 | Corregido | OK | Solo «ISO 13920-BF» (GEN-001 n.° 7 y GEN-004). |
| A-21 | Corregido | OK | GEN-006 «Zonas sin pintura (lista única del juego)». GEN-001 n.° 12: «lista única en GEN-006». |
| A-22 | Corregido | **Parcial** (Menor) | GEN-005 ya pone «PROPUESTO por Fy del cálculo» en las dos tablas. Pero CON-002 y el rótulo de MES-012 dicen «34CrNiMo6+QT…, Fy ≥ 800 MPa» sin «PROPUESTO», y las filas A572 de CON-002 no indican estado (PIV-001 sí lo hace). |
| A-23 | Corregido | OK | «±1» en GEN-003 n.° 14, BAS-001 n.° 4 e IZA-001 n.° 2. |
| A-24 | Corregido | **Parcial** (Menor) | CON-007 y BAS-005 ya dicen «centro de la luz entre orejas (eje del cilindro) a 105 ±0,5» y «perpendicular a la cara de apoyo (A)». GEN-003 n.° 10 conserva «altura del eje de ménsulas 105 ±0,5». |
| A-25 | Corregido | OK | Masas acumuladas: 1.229,5 → 2.386,0 → 2.404,6 → 2.404,6 → 2.408,5 → 2.692,9 → 3.102,4 → 3.106,7 → 3.106,7, igual a CON-001 y CON-002. |
| A-26 | Corregido | OK | CON-008 y CON-009, rótulo: «1.156,5 / 1.440,9 kg». CON-009 n.° 2 explica el doble valor. |
| A-27 | Corregido | OK | CON-022: «nivelación con apoyo continuo sobre la losa (grout o mats…); no se admiten cuñas puntuales salvo verificación del calculista». |
| A-28 | Corregido | OK | GEN-012: «WPS-P12 · J18 · Soldadura de ranura (22 × 80) rellena por completo (AWS D1.1, soldaduras de tapón y ranura…)». |
| A-29 | Corregido | OK | GEN-001 n.° 13: «Códigos de pieza: … las piezas sin lámina propia se dibujan en la lámina indicada en la columna «Plano» del despiece». |
| A-30 | Corregido | OK | GEN-001: «Números no emitidos en este juego (reservados o anulados): CON-012, 013; GEN-002. CON-030 y siguientes: hojas de continuación…». |
| A-31 | Corregido | OK | W CON-030: MAD-001, MAD-002 y los comerciales (bloque completo). |
| A-32 | Corregido | OK | GEN-001 trae una sola nota de apoyo y viento (n.° 4). Las CON remiten a ella: «NOTAS GENERALES: VER GEN-001 (apoyo sin anclaje y viento: nota 4)». |
| A-33 | Corregido | OK | Banda del rótulo: «NOTAS GENERALES: VER GEN-001. Cotas en mm. Proyección: método E». No queda ningún bloque «GENERALES». |
| A-34 | Corregido | **Parcial** (Menor) | La tabla de normas está completa salvo **ISO 15787**, que cita MES-012 n.° 2 y no aparece en GEN-001. Además GEN-001 n.° 8 dice «procesos 111/135/141» y GEN-012 usa 135/111/136 (ver N-17). |
| A-35 | Corregido | OK | Instructivos: CON-005 «n.° 14 / n.° 8», CON-014 «n.° 8 / n.° 9», CON-016 «n.° 12», CON-017 «n.° 10 / n.° 13», CON-019 «n.° 9 / n.° 15», CON-022 «n.° 18 / 16 / 15». GEN-003 n.° 15 remite a GEN-008. |
| A-36 | Corregido | OK | BAS-001 n.° 5: «ver CON-023 (detalles D1–D4…) y… GEN-007». |
| A-37 | Corregido | OK | Índice de CON-004: «… (PIVOTE, BUJE Y TAPAS INCLUIDOS; ACCIONAMIENTO EN CON-018)». |
| A-38 | Corregido | OK | CON-011 tiene un solo despiece. CON-008 ya no trae despiece ni tabla de juntas (CON-009 sí). |
| A-39 | Corregido | OK | CON-007 se titula «(PLANTA, CORTES Y DETALLE)», igual en el índice. |
| A-40 | Corregido | OK (base) / Regr. en B | No hay choques de texto en la planta de base. En B (1:20), la cota R930 que movió el commit c37e014 ahora cruza el cubo y el texto «CG» (N-06). |
| A-41 | Corregido | OK | La cadena «80 / 230» desapareció de CON-008. |
| A-42 | Corregido | OK | CON-008 y CON-009 llevan el mismo texto de MATERIAL. |
| A-43 | Corregido | OK | El rótulo trae la lista explícita (BAS-005 «1:2 / 1:2,5 / 1:5»). En A y C, rótulo e índice parten «…/ 1:20» en dos renglones, pero se leen. |
| A-44 | Corregido | OK | MES-005: «15,4 + 30,4 + 43,3 kg c/u». |
| A-45 | Corregido | OK | Cabeceras «Nom.» y «Aguj.». |
| A-46 | Corregido | OK | GEN-008: «precarga F = 70 % de Rp0,2·A_s (Rp0,2 mínimo… = 940 MPa; la carga de prueba de la clase es 830 MPa)». |
| A-47 | Corregido | OK | CON-001: «… según el cálculo 3.237,6 kg; la diferencia incluye la leva de reenganche (178,0 kg) aún no dibujada: brecha B-08 (GEN-009)». |
| A-48 | Corregido | OK | Informe: «Todas las láminas dentro de su formato (A1: 50, A2: 5)». |
| A-49 | Corregido | OK | El título de GEN-009 ya no lleva «(GEN-009)». |

### Frente B

| ID | Estado declarado | Estado verificado | Evidencia exacta |
|---|---|---|---|
| B-01 | Corregido | OK | Igual que A-02. PIV-001 nota 3: «zona f7 en el buje F7/f7, juego +72/+142 µm. El buje no debe pasar sobre la zona p6». |
| B-02 | Corregido | OK | PIV-003: «6 × Ø9, avell. Ø17×90° en PCD Ø214», «avellanado Ø17×90° con borde 3,5 mm hasta el canto de la tapa (≥ 3)». Corte B-B «3,5 (borde)». MES-001: «6 × M8-6H prof. 10 (broca Ø6,8)… PCD Ø214». |
| B-03 | Corregido | OK | MES-002, corte radial (raster): «27,5 \| Ø85 H7 (+0,035/0) \| 27,5», «(140)» como cota auxiliar y «70 (al eje; PCD Ø1.860)» sobre su línea. |
| B-04 | Corregido | OK | MES-001 n.° 4 y MES-003 n.° 4: «chaflán 1:4… hasta 3 mm del agujero de pasador y el resto con la pendiente 1:4 del cordón». Detalles «24 (chaflán 1:4)». Ver N-03. |
| B-05 | Corregido | **Parcial** (Menor) | La nota dice «Ø de corte de preparación 1.714 (= Ø1.720 − 2 × 3)», pero las plantas de MES-001 y MES-003 siguen acotando «Ø1.720» como única cota del contorno. |
| B-06 | Corregido | OK | MES-001: tabla «RANURAS DE CIERRE J18» (A1 8, A2 15, A3 21, nervios 3 × 14; TOTAL 86) y símbolo «c22 86 × 80 (250)». soldaduras.csv J18: 6880. |
| B-07 | Parcial | Parcial (confirmado) | MES-011 tabla J17: «CJP, penetración total t = 16», longitud 1.948 (2 × 974, OK). Detalle «(bisel 45°, t = 16)». **Falta:** separar J17a (plancha inferior, 16) y J17b (plancha superior, 20) y dibujar el detalle con la geometría real en T. |
| B-08 | Corregido | **Parcial** (Mayor) | BAS-003 «DETALLE A… (pletina a ras del canto; filete interior)» está bien. «DETALLE J01 / J02: FILETE INTERIOR z6 (pletina a ras del canto)» sigue dibujando la plancha a **ambos** lados de la pletina (raster): contradice su propio título. |
| B-09 | Corregido | OK | BAS-003 detalle B: la flecha de J03 llega al rincón interior (extremo de la corta contra la cara interior de la larga). soldaduras.csv J03: «rincón interior». |
| B-10 | Corregido | OK | MES-012: corte A-A con rosca (línea gruesa y fina), «40 (rosca útil M20-6H)», «45 (taladro Ø17,5)» y traza A-A en la vista de extremo. |
| B-11 | Corregido | OK | MES-012: «50 (inicio de la franja templada, desde la cara sin rosca)», «160 (fin…)» y n.° 2 «(ISO 15787)». |
| B-12 | Corregido | OK | MES-012 y PIV-001 usan el símbolo de cilindricidad (⌭, raster). Se eliminó la oscilación autorreferida. |
| B-13 | Parcial | Parcial (confirmado) | MES-013: agujero «Ø22», espesor 10 y material C45 únicos, y ya no dice «según modelo 3D». **Falta:** (1) el vástago del perno no se dibuja dentro del agujero Ø22 de la arandela; (2) la cabeza sale rayada en corte longitudinal y sin hexágono interior (s = 17 solo por llamada); (3) en CON-002 la partida de la arandela fabricada figura como «Comercial Según catálogo». |
| B-14 | Corregido | OK | MES-005: «1 pletina» en las tres almas y n.° 2 «1 empalme… ubicar el empalme entre nervios». J16 522. |
| B-15 | Corregido | OK | MES-005: «R303 (cara ext.; eje R300) — A1», etc. La cadena 290/256/546 desapareció. |
| B-16 | Corregido | OK | Partidas «146×178×6 / 288×178×6 / 248×178×6». Ver N-04. |
| B-17 | Corregido | **Parcial / Regr.** (Mayor) | MES-008 n.° 2: «largo de corte = largo entre caras − 2 mm» y destijeres «15 × 15». Tabla: largo de corte 140/282/242. CON-002 y el despiece dicen en cambio «largo terminado 142 (sobremetal 2 por extremo)». Las vistas acotan «142/284/244 ±0,5» sin decir que es entre caras. Destijeres solo en nota. Ver N-04. |
| B-18 | Corregido | OK | J15 «MES-008…010 / MES-001, 003, 005…007, 011», 66.750 mm = 37.518 + 24.360 + 4.872. |
| B-19 | Corregido | OK | CON-009 n.° 5: «Mesa armada (datum A = cara inferior planeada): cara superior paralela a A dentro de 0,5». MES-001 y MES-003 solo traen planitud. |
| B-20 | Corregido | **NO** (Mayor) | No hay ningún marco de tolerancia ni indicador de datum en las vistas de BAS-002, MES-011, MES-012, MES-013, PIV-001, PIV-002, IZA-001… Siguen solo en la tabla de la derecha (raster PIV-001 y MES-012; los DXF no tienen capa ni texto de datum fuera de las tablas). |
| B-21 | Corregido | OK | BAS-002: «Agujero H7 perpendicular a la cara de apoyo (A…)». Coaxialidad Ø0,05 de los agujeros de pasadores en CON-009 n.° 5. |
| B-22 | Corregido | OK | MES-002: «PCD Ø1.860» en recuadro y «Ø0,3 A… PCD y ángulos del patrón: cotas teóricamente exactas». Contradicción residual en CON-014 (N-11). |
| B-23 | Corregido | OK | PIV-001: «78 (zona p6: plancha base + collar)». |
| B-24 | Corregido | OK | PIV-001: «4 × M10-6H, rosca útil 16, taladro Ø8,5 prof. 20, PCD Ø80 a 45° + 90°·k», corte B-B con «16 (rosca útil…)» y «20 (taladro Ø8,5)», sin coordenadas. Ver N-01. |
| B-25 | Abierto | Abierto ✓ | PIV-001 n.° 6: «Retención axial del pivote: … A DEFINIR POR EL CALCULISTA». También en CON-011 n.° 4 y GEN-009. |
| B-26 | Corregido | OK | «ISO 10642 M8×16 10.9» (tapa de inspección). |
| B-27 | Corregido | OK | PIV-003: «PIV-003-C — CORTE A-A POR UN AGUJERO» (5:1) y «PIV-004-C — CORTE B-B POR UN AGUJERO» (2:1), con trazas A-A y B-B y avellanado acotado. |
| B-28 | Corregido | OK | BAS-002 n.° 1: «partida Ø260 oxicortada de plancha de 65; caras planeadas a 60 ±0,5 y Ø250 torneado». |
| B-29 | Corregido | OK | J09 solo en BAS-002, rotulado «65 (ancho radial; alto 60)». |
| B-30 | Corregido | OK | MES-003 n.° 1: «la junta J13 se prepara para el espesor al soldar (19)». Detalle «s19». |
| B-31 | Corregido | OK | MES-002: «Espesor de partida 30 mm (caras planeadas a 27)». Igual en CON-002. |
| B-32 | Corregido | OK | Recuadros «MR» y «M» en los símbolos J11, J12, J13, J16 y J17 (raster CON-009 y MES-002). |
| B-33 | Corregido | OK | J09 y J10: «VT100 MT100». IZA n.° 3: «MT 100 %… UT de laminación de la plancha base (ASTM A578 nivel B)». |
| B-34 | Corregido | OK | IZA-001 n.° 1: «agujero Ø45 H12 mecanizado (taladro y mandrinado)». Contradicción residual en N-15. |
| B-35 | Corregido | **Parcial** (Menor) | IZA-001 n.° 3: «base de la oreja a escuadra sin bisel (J10)». Pero despiece.csv pos. 8 conserva «biselado de la base de apoyo» (N-15). |
| B-36 | Corregido | OK | ±1 en BAS-001 e IZA-001. |
| B-37 | Abierto | Abierto ✓ | MES-005 n.° 4: «El tamaño supera el máximo AISC J2.2b (t − 2): pendiente del calculista». |
| B-38 | Corregido | OK | BAS-001: «Planitud de la zona de apoyo Ø2.020 (cara superior planeada = A)» y «Agujero Ø120 H7 perpendicular a la cara superior planeada (A)». |
| B-39 | Corregido | OK | BAS-001: desaparecen las cadenas «140/540/600/250/1.030». Queda la tabla «POSICIONES DE LAS PIEZAS SOLDADAS» y «2.560 ±2». |
| B-40 | Abierto (acc.) | Abierto ✓ | La tabla de BAS-001 sigue con «M1 ménsula horario 1.140,0 / 945,1…» (pendiente del accionamiento). |
| B-41 | Abierto (acc.) | Abierto ✓ | BAS-005 queda pendiente del accionamiento. Las partidas ya se corrigieron (155×180). |
| B-42 | Corregido | OK | Las láminas de pieza solo traen notas propias y «NOTAS GENERALES: VER GEN-001». |
| B-43 | Corregido | OK | Trazas de corte presentes: BAS-002 (A-A), MES-011, MES-012, MES-013, PIV-001 (B-B), PIV-003 (A-A, B-B) y MES-002 (A-A). |
| B-44 | Corregido | **Parcial** (Menor) | Hay símbolos Ra en las vistas, pero en PIV-001 los dos «Ra 0,8» flotan fuera de la elevación, sin tocar ninguna superficie (N-14). |
| B-45 | Parcial | Parcial (confirmado) | **Falta:** MES-008 repite «174 ±0,5» cuatro veces; BAS-002 repite «Ø250»; MES-012 acota «Ø85» en la vista de extremo además de «Ø85 m6». |
| B-46 | Parcial | Parcial (confirmado) | **Falta:** IZA-001 «Ø184», «R92», «184 (= 2R)», «182 (altura total)»; BAS-003 «63» (= 45 + 18); B INT-009 «27,57 + 20 + 7,9 = 55,47» (cadena cerrada). |
| B-47 | Corregido | **Parcial** (Menor) | MES-001: la línea de referencia de «6 × M8-6H prof. 10 (broca Ø6,8)…» atraviesa el texto «Ø6,8», y «Ra 6,3» sigue tocando la letra «B» del círculo de detalle (raster). |
| B-48 | Corregido | **Parcial** (Menor) | Persisten: en BAS-003, detalle J01, «a = 4,2» sobre la línea de cota y el contorno; en MES-012, la llamada «M20-6H, rosca útil 40…» cruza la circunferencia Ø85. Nuevos en N-12. |
| B-49 | Corregido | OK | Símbolos con el cateto vertical a la izquierda y la cota a la izquierda (raster BAS-003 y MES-002). |
| B-50 | Corregido | OK | Sin línea discontinua en las soldaduras simétricas («z6/z6» de J21) y «b = 3» / «talón c = 2». |
| B-51 | Corregido | OK | BAS-002, cola de J09: «precal. ≥ 65 °C». |
| B-52 | No procede | **No procede: razón válida** | MES-002 sigue con «+x (mesa)» girado −6,43°, pero la geometría es correcta y está acotada («6,429° (1.er agujero desde +x)», «6,429° (empalme)»). Es un asunto de presentación sin riesgo de error. |
| B-53 | Corregido | OK | MES-001 n.° 1: «partida Ø1.725 (sobremetal 2,5 por lado)», igual a la ficha. |
| B-54 | Corregido | **Parcial** (Menor) | Ya no hay referencias a madera en el juego base. BAS-002, tabla de rugosidad, conserva «cara superior (asiento del cubo)» aunque hay holgura axial de 2 mm. |
| B-55 | Corregido | OK | MES-008: largos 142/284/244 y ±0,1° en nota (fuera del marco de posición). |
| B-56 | Corregido | **Parcial** (Menor) | PIV-002 conserva «PLANTA ESC 2:1» y «CORTE A-A ESC 1:1». MES-001, corte A-A a 1:5 (plancha de 20 = 4 mm). Corregidos PIV-003 (cortes 5:1 y 2:1) y MES-012 (extremo 1:1). |
| B-57 | Corregido | OK | Escalas listadas en el rótulo («1:2 / 1:2,5 / 1:5», «2:1 / 1:1 / 1:5 / 1:10»), iguales al índice. |
| B-58 | Corregido | OK | PIV-003: «patrón PROPUESTO, supuesto S15 de GEN-009». Ya no aparece «-0». |

### Frente C

| ID | Estado declarado | Estado verificado | Evidencia exacta |
|---|---|---|---|
| H-01 | Corregido | OK (definida), con problema nuevo | B INT-001: «Ángulo del eje de la barra 3,75° + 15°·k desde +x (-3,75° desde la bisectriz)», «r = 181 a 950», barra en planta y sección D-D. INT-009 n.° 2: «una barra en cada JUNTA entre sectores de UHMW (nunca sobre la bisectriz)». La muesca 22×170 queda a 44 mm: no hay cruce. **Pero** en el extremo interior la barra queda casi sobre la junta del disco de acero (N-05). |
| H-02 | Abierto | Abierto ✓ | C1 INT-010: «Cumple la fracción mínima: NO (mínimo 0,2)». INT-102: «real 0,097 / ideal 0,145; mínimo de lubricación 0,2 → NO cumple (hallazgo del cálculo)». No está marcada «RETENIDA» ni «A DEFINIR». |
| H-03 | Abierto | Abierto ✓ | AF2 CON-012 n.° 3: «La transmisión del par sin topes queda PENDIENTE de la decisión del cliente (adhesivo…)». Ya no hay notas ni tablas de topes o tornillos. INT-001 y INT-002 (AF2) solo dicen «NO desmontable (sectores pegados)», sin remitir al pendiente. |
| H-04 | Corregido | **Parcial** (Mayor) | El mapa de GEN-001 tiene denominación fija y el orden por código está bien. Pero el mismo código y revisión «-C» designa piezas no intercambiables: <br>• INT-001-C: e = 15 (A), e = 6 (AF2), subconjunto soldado con barra (B). <br>• INT-002-C: e15 ranurado (A), e8 (AF2), e15 liso (B). <br>• INT-003-C: 20×170×13 (A/B) frente a 20×205×13 (C). <br>• INT-004-C: 170 (A/B), 150 (C1/C3), 355 (C2). <br>• INT-005-C: «cabeza 0,5» (A/B) frente a «cabeza 1» (C). <br>• Dentro de una misma variante hay dos tipos de sector con un solo código: INT-002 pares/impares; INT-010 con 106 y 114 tapones. |
| H-05 | Corregido | OK | AF2: «Variante AF2 · Opción A, fijación modo 2: discos inoxidables e6/e8 pegados…, sin topes ni tornillos (no desmontable)». |
| H-06 | Corregido | OK | W: «…con cubierta de madera e = 50 y anillo de contención 10×50». CON-001 cita «MAD-001/002». |
| H-07 | Corregido | OK | AF2 INT-001 e INT-002 ya no hablan de muesca, avellanado ni tope. |
| H-08 | Corregido | OK | B INT-008: «sin relapeado», «espesor e ±0,3…; radios ±1; planitud 0,5», sin muesca. |
| H-09 | Corregido | OK | INT-009 n.° 3: «Soldar al disco inoxidable de la base (INT-001, e = 15)». Ya no aparece «a el» ni la muesca de 22. |
| H-10 | Corregido | OK | B INT-001: «DISCO DE LA BASE CON LAS BARRAS DEL REBAJE UHMW SOLDADAS (SUBCONJUNTO SOLDADO)», con secuencia y J21. |
| H-11 | Corregido | OK | Conductos «a 52,5°, 142,5°, 232,5°, 322,5°» (bisectrices) y GD&T «respecto de la bisectriz de su sector». |
| H-12 | Parcial | Parcial (confirmado) | INT-101 n.° 3 define «dos tipos de sector, simétricos: impares… y pares». **Falta:** distinguir los dos tipos en el despiece (INT-002-C × 24, un solo código) y en la lámina de la pieza. |
| H-13 | Parcial | Parcial (confirmado) | INT-007 sitúa la grasera en «el canto del anillo inferior de la mesa (MES-004)», con «CORTE A-A … EN EL ANILLO MES-004», y MES-002 (A) n.° 8 la menciona. **Falta:** MES-002 se sigue titulando «PLANTA (anillo; superior e inferior idénticos)», y MES-004-C usa el mismo código con o sin taladros según la variante (N-08). |
| H-14 | Parcial | Parcial (confirmado) | Ya hay «avellanado Ø12×90°» y «cabeza 0,5 +0,2/0 mm bajo la cara». **Falta:** Ø12 = dk máx. de ISO 10642 M6 (sin holgura), y la profundidad cambia según la variante bajo el mismo código (0,5 en A/B, 1 en C). |
| H-15 | Corregido | OK | C1 INT-010: «2 × M6 ISO 10642… a r = 366,4 y 875,9». |
| H-16 | Corregido | OK | INT-010: «106 tapones de grafito Ø12 H7 en este sector (cantidad por sector: tabla de INT-102)». En C3, 100/97. Una sola tolerancia, H7. |
| H-17 | Corregido | OK | INT-102: «COORDENADAS DE LOS 106 TAPONES DEL SECTOR 1» y «…114 TAPONES DEL SECTOR 2 (tipo con 114 tapones…)». |
| H-18 | Corregido | OK | C3 INT-011: «ángulo de la pastilla 13,5°», «Hueco entre pastillas» y «PLANTA DE LA PASTILLA… 13,5° en una posición de 15°». |
| H-19 | Corregido | OK | Bronce «ASTM B148 C95400». 2.ª placa «Bronce ASTM B584 C93200». Disco duro «ASTM A564 tipo 630 (17-4PH) condición H1025», con «Endurecimiento por precipitación H1025». |
| H-20 | Corregido | OK | A: base «ASTM A240 tipo 304, recocido, ≤ 180 HB»; mesa «dúplex… S32205, ≥ 230 HB». |
| H-21 | Abierto | Abierto ✓ | MAD-002 y despiece: «filete 6 a ambos lados» frente a «z8». |
| H-22 | Abierto | Abierto ✓ | Tabla de J22: «(MAD anillo / MES-001)», «t = 20 mm». |
| H-23 | Abierto | Abierto ✓ | Sin cambios (MAD-001/002). |
| H-24 | Abierto | Abierto ✓ | MAD-001 n.° 4: «PROPUESTA tornillos… (decisión del mandante: confirmar)». |
| H-25 | Abierto | Abierto ✓ | W CON-001: «total sin cubierta 228». |
| H-26 | Parcial | Parcial (confirmado) | **Falta:** A INT-002, corte A-A: «22,28», «8» y «Ra 0,4 (cara deslizante)» siguen amontonados sobre la misma línea de cota (raster). |
| H-27 | Corregido | **Parcial / Regr.** (Menor) | B CON-001 sigue a «ESC 1:20». El cruce «945 / orejas» se resolvió, pero «R930 (círculo de pasadores)» ahora cruza el cubo y el texto «CG» (N-06). |
| H-28 | Corregido | OK | Rótulo e índice coinciden en AF2 y C2 (control automático). |
| H-29 | Parcial | Parcial (confirmado) | Hay trazas A-A y D-D (B INT-001). **Falta:** el triángulo de datum «A» (bisectriz) en las plantas INT. |
| H-30 | Corregido | OK | B INT-002 ya no menciona ranuras. |
| H-31 | Corregido | OK | INT-003 «t = 18» e INT-004 «t = 16». |
| H-32 | Corregido | OK | INT-101 n.° 1: «Lámina de características: la pieza… se define en INT-002-C». |
| H-33 | Corregido | OK | Ya no aparece «A4-80». Ángulos de las graseras en un solo formato (225°/315°). |
| H-34 | Corregido | OK | Un título por variante: «DISCO DURO DE LA MESA (SECTOR)», «PASTILLA DE BRONCE…», etc. |
| H-35 | Corregido | OK | C1 CON-012: «15 (disco duro, mesa)» arriba y «15 (bronce, base)» abajo. |
| H-36 | Corregido | **Parcial** (Menor) | CON-001 y CON-002 (base, W) están bien. GEN-003 n.° 12 (base y W) remite a «CON-012», que no existe en esos juegos (N-09). |
| H-37 | Abierto | Abierto ✓ | MAD-002 sin cambios. |
| H-38 | Abierto | Abierto ✓ | MAD-001 sin cambios. |
| H-39 | No procede | **No procede: razón válida** | Las láminas toman la masa del modelo 3D y redondean igual que el despiece: INT-001 14.678 → «14,68 kg»; CON-012 total «352,3». La diferencia con `m_neta` 352,54 del núcleo es de 0,07 %. |
| H-40 | Parcial | Parcial (confirmado) | INT-005 ya es A2. **Falta:** INT-102 (C1–C3) sigue en A1 con 3,8 % de vistas sobre el área útil. |
| H-41 | Parcial | Parcial (confirmado) | Corregido: C3 INT-011 sección B-B ya trae «6,6». **Falta:** AF2 INT-001 «CORTE A-A POR LA BISECTRIZ ESC 2:1» sigue sin cotas propias. |
| H-42 | No procede | **Razón válida solo en parte** (Menor) | Las firmas «A DEFINIR» son el criterio declarado (GEN-001 n.° 2): válido. El texto TRATAMIENTO sigue truncado en A INT-002 e INT-101: «Decapado y / pasivado; ≥ 50 HB / sobre el disco de / la base (ASTM», con el último renglón cortado por la línea de la celda (raster). Hay que corregirlo. |

**Conteo de la tabla 1 (149 IDs)**
- **OK:** 103 (A 43 · B 39 · H 21).
- **Declarados corregidos que resultan parciales:** 16 (A-08, A-09, A-19, A-22, A-24, A-34, B-05, B-08, B-35, B-44, B-47, B-48, B-54, B-56, H-04, H-36).
- **Parcial con regresión:** 2 (B-17, H-27).
- **NO corregido:** 1 (B-20).
- **Parciales declarados, confirmados:** 11 (B-07, B-13, B-45, B-46, H-12, H-13, H-14, H-26, H-29, H-40, H-41).
- **Abiertos por decisión, confirmados:** 13.
- **No procede:** 3. Razón válida en B-52 y H-39; válida solo en parte en H-42.

## 2. Hallazgos nuevos

| ID | Lámina | Hallazgo | Evidencia | Severidad | Corrección propuesta |
|---|---|---|---|---|---|
| N-01 | PIV-003, CON-011 n.° 3, GEN-008, CON-002/030 (todas las variantes) | El tornillo de la tapa retenedora es 1 mm más largo que la rosca útil del pivote. Hará tope en el fin de rosca antes de apretar la tapa. | «4 × M10×25 ISO 10642 10.9» atraviesa una tapa de 8 (cabeza enrasada): entran 25 − 8 = **17** mm en el pivote. PIV-001: «M10-6H, rosca útil 16, taladro Ø8,5 prof. 20». El raster de CON-011 muestra la tapa apoyada directamente sobre el pivote. | Mayor | Usar M10×20 (toma de 12 ≥ 1·d) o llevar la rosca útil a ≥ 18 con taladro de 22. Corregir las cinco láminas y el despiece. |
| N-02 | PIV-002 n.° 2 (y CON-011 y GEN-004) | El juego F7/f7 se especifica antes del prensado y no hay criterio de aceptación después. El buje se prensa s6/H7 en el cubo (aprieto 60–125 µm), lo que cierra el diámetro interior en un orden comparable al juego mínimo de 72 µm. | «juego F7/f7 +72/+142 µm… antes del prensado; verificar el Ø interior después de prensar el buje». No hay valor admisible ni acción si no cumple. | Mayor | Dar el Ø interior admisible después del prensado (p. ej. ≥ 120,036) o pedir el mandrinado o escariado a F7 una vez prensado. Que lo confirme el calculista o el proveedor del buje. |
| N-03 | CON-009, MES-002, MES-003 | El espesor del anillo al soldar no es coherente. J11 y J12 preparan el anillo superior a 27 y J13 prepara el inferior a 30, pero MES-002 declara los dos anillos idénticos, con caras planeadas a 27. No se dice que MES-004 se planee después de soldar. | CON-009: «DETALLE J12… t = 20 / 27», «DETALLE J13… t = 19 / 30». MES-002: «Espesor de partida 30 mm (caras planeadas a 27)», «superior e inferior idénticos». Además, el chaflán 1:4 limitado a 24 deja un escalón de 5 mm (30 → 19) que debe absorber el cordón. | Mayor | Definir la secuencia: o los dos anillos se planean a 27 antes de soldar y J13 se dibuja con 27, o MES-004 se suelda a 30 y se planea con la cara inferior (indicarlo en MES-002 y en CON-014). |
| N-04 | MES-008 ↔ CON-002, despiece.csv, GEN-010/013 | Dos largos de corte contradictorios para los nervios. Las vistas acotan el largo entre caras sin indicarlo. | MES-008 tabla: «Largo de corte 140 / 282 / 242» y n.° 2 «largo de corte = largo entre caras − 2 mm». CON-002 y el despiece: «largo terminado 142 (sobremetal 2 por extremo)», partida 146. Vistas: «142 ±0,5», «284 ±0,5», «244 ±0,5». | Mayor | Unificar (largo de corte 140/282/242 en CON-002, en el despiece y en las vistas, con el entre caras como cota auxiliar) y dibujar los destijeres de 15×15. |
| N-05 | B: INT-001, INT-009, CON-012 | La barra del rebaje (radial a 3,75° del eje del sector) se acerca a la junta del disco de acero (radial a 7,5°) hacia el centro. En r = 181 su canto queda a ≈ 1,3 mm de la junta de 1 mm. El filete J21 z6 de ese lado cruza la junta para r ≲ 250 mm, lo que soldaría entre sí dos sectores que se declaran desmontables. | B INT-001: «Ángulo del eje de la barra 3,75° + 15°·k… r = 181 a 950», barra de 20 de ancho y «Fijación desmontable por sectores». En el raster de la planta, el extremo interior de la barra toca el borde del sector. 181 · sen 3,75° − 10 − 0,5 = 1,3 mm. | Mayor | Arrancar la barra en r ≥ 260, o poner la junta de UHMW paralela a la junta de acero (barra no radial), o soldar ese tramo solo por el lado alejado de la junta. Revisar con el núcleo (V_junta). |
| N-06 | B CON-001 (planta 1:20) | Regresión del commit c37e014: el texto de la cota R930, llevado al pasador más cercano a 135°, ahora cruza el cubo y el rótulo «CG». | Raster: «R930 (círculo de pasadores)» atraviesa la circunferencia del cubo y queda encima de «CG». | Menor | Mover el texto fuera del cubo (sobre la línea, más allá de R310) o pasar la planta de B a 1:10. |
| N-07 | GEN-001, mapa de códigos INT (todas las variantes con INT) | La columna «En este juego» marca «—» en INT-101 e INT-102 aunque esas láminas existen (INT-101 en A, AF2 y C1–C3; INT-102 en C1–C3). La columna «Variantes» dice «según variante». | Fila «INT-101 · Ranuras de engrase… · según variante · —». En A existe la lámina 'INT-101'. | Menor | Poner «sí» donde la lámina está emitida y listar las variantes (A, AF2, C1, C2, C3 / C1, C2, C3). |
| N-08 | MES-002 (A, AF2, C1–C3) | MES-004-C lleva taladros de grasera solo en algunas variantes, con el mismo código y la misma revisión, mientras la planta se titula «idénticos». Es el mismo problema de código que H-04. | A MES-002 n.° 8: «Solo el anillo INFERIOR (MES-004): conductos de engrase…» frente a «PLANTA (anillo; superior e inferior idénticos)». En el despiece, MES-004 tiene igual descripción en base y en A. | Menor | Quitar «idénticos» del título y diferenciar MES-004 cuando lleva graseras (sufijo o código propio), con los taladros dibujados. |
| N-09 | Base y W: GEN-003 n.° 12, CON-030, despiece.csv | Quedan textos de otras variantes. El plan de inspección pide galgas en «juntas entre sectores» y remite a CON-012, que no existe. La grasa se dosifica para «llenado de ranuras» en una interfaz sin ranuras. | GEN-003: «…juntas en frío entre sectores con galga (CON-012)». CON-030: «Cantidad: llenado de ranuras + película de 0,3–0,5 mm por cara». | Menor | Filtrar esos textos por variante (en base y W: «película… sobre la cara de la base y de la mesa»). |
| N-10 | A y AF2 INT-101 | La tabla de rugosidad remite a tapones de grafito y a INT-102, que no existen en A ni en AF2. Es copia de C. | «Ø12: avellanados de tornillos y alojamientos de tapones (ver lámina del sector e INT-102)». | Menor | En A y AF2, quitar «alojamientos de tapones» e «INT-102». |
| N-11 | CON-014, paso 2 (todas) | La tolerancia del patrón de pasadores contradice MES-002 y CON-009, donde el PCD y los ángulos son cotas teóricamente exactas con posición Ø0,3. | CON-014: «PCD ±0,3; paso 12,857° ±0,05°; planitud 0,20». | Menor | Escribir «posición Ø0,3 respecto del eje (MES-002 / GEN-003 n.° 9)». |
| N-12 | BAS-003 | La línea de referencia de la cota «45 ±0,5» de la pletina corta atraviesa la cola del símbolo J03. | La línea de referencia en x ≈ 459 mm cruza «J03 · 135 · WPS-P01 / ISO 5817-C · VT100 MT10» (raster). | Menor | Desplazar la cola del símbolo o la cota. |
| N-13 | PIV-003 (cortes A-A y B-B), PIV-001 (corte B-B) | Cortes parciales sin línea de rotura y una cota encimada. | En PIV-004, corte B-B, el texto vertical «8 ±0,2» queda sobre las líneas de la cota «3,5 (borde)». Las piezas terminan en un corte recto sin símbolo de rotura. | Menor | Añadir líneas de rotura (ISO 128) y separar las cotas. |
| N-14 | PIV-001 | Los símbolos de rugosidad no están aplicados a ninguna superficie. | Los dos «Ra 0,8» están en x ≈ 455–520 mm, fuera de la elevación (que llega a x ≈ 400) y sin línea de referencia (raster). | Menor | Poner el símbolo sobre cada zona rectificada o en una línea de referencia que la toque. |
| N-15 | IZA-001, despiece.csv pos. 8 | El agujero y la base de la oreja quedan definidos de forma contradictoria. | Nota 1: «agujero Ø45 H12 mecanizado (taladro y mandrinado)». Rugosidad: «Ra 12,5 canto de corte; agujero esmerilado». Despiece: «biselado de la base de apoyo», frente a la n.° 3 «a escuadra sin bisel». | Menor | Ra del agujero mecanizado (p. ej. 6,3) y quitar «biselado» del despiece. |
| N-16 | GEN-012, tabla de precalentamiento | La tabla, rotulada «acero Grupo II (ASTM A572 Gr.50)», trae una columna de «Categoría A: electrodos no bajo hidrógeno». En AWS D1.1 la categoría A (SMAW sin bajo hidrógeno) corresponde a los aceros del Grupo I; el A572 Gr.50 aparece en la categoría B. La columna puede inducir a usar E60xx sin bajo hidrógeno. | «Categoría A: electrodos no bajo hidrógeno · 65 °C / 110 °C / 150 °C». | Menor (a confirmar por el calculista o el fabricante) | Quitar la columna A o rotularla «no aplicable al Grupo II». |
| N-17 | GEN-001 n.° 8 | Los procesos ISO 4063 citados no coinciden con los WPS. | «ISO 4063 (procesos 111/135/141)» frente a GEN-012, que usa 135, 111 y 136 (FCAW). El 141 solo se usa en J21 (B). | Menor | «111/135/136 (141 solo en J21, variante B)». |
| N-18 | CON-002 pos. 22, despiece.csv | La arandela, que es fabricada, no tiene dimensión de partida. | «Perno M20×45 10.9 + arandela Ø115/Ø22×10 (C45…)», con partida «Comercial Según catálogo». | Menor | Partida «disco Ø120×12 de C45» (o la que corresponda) y el perno como comercial aparte. |
| N-19 | GEN-004 | Tolerancias del conjunto mal referidas y unidad mal empleada. | Tabla geométrica: «Coaxialidad · Agujeros de pasadores superior/inferior · Ø0,05 · —», sin datum, mientras CON-009 n.° 5 fija el eje común. Tabla de ajustes: «Juego mín/máx [µm] … 3000 (radial)». | Menor | Referir la coaxialidad al eje común de CON-009 y escribir «3 mm (radial)» fuera de la columna en µm. |
| N-20 | MES-001 | Falta la profundidad de taladro de los agujeros M8, y el fondo del rebaje solo tiene 12 mm. En PIV-001 y MES-012 sí se dan rosca útil y taladro por separado. | «6 × M8-6H prof. 10 (broca Ø6,8) en el fondo del rebaje». El rebaje Ø240 × 8 en plancha de 20 deja 12. | Menor | «rosca útil 10, taladro Ø6,8 pasante» (o una profundidad ≤ 12). |
| N-21 | CON-011, corte por el eje del pivote | Los globos 25 (tapa retenedora) y 23 (pivote) comparten una línea de referencia horizontal que cruza todo el corte. No se distingue a qué pieza apunta cada uno. | Raster: las líneas de referencia de los globos 25 (izquierda) y 23 (derecha) están en la misma cota y casi se tocan sobre el pivote. | Menor | Escalonar las líneas de referencia o inclinarlas hacia cada pieza. |

**Conteo de la tabla 2:** 21 hallazgos nuevos, 5 mayores (N-01 a N-05) y 16 menores. Uno es una regresión directa del último commit (N-06).

## 3. Láminas revisadas como imagen en esta vuelta

- **Juego base:**
  - CON-001 (planta y corte A-A), CON-003, CON-009 (detalles J12 y J13), CON-011;
  - BAS-003, MES-001, MES-002, MES-012, MES-013;
  - PIV-001, PIV-003.
- **Variantes:**
  - B: CON-001, INT-001, INT-009;
  - A: INT-002 y el rótulo de BAS-005;
  - W: rótulo de MAD-002.
- **Solo por texto (ezdxf):** el resto de las láminas de los 8 juegos. Excluidas: ACC-*, CON-010 y CON-018.
