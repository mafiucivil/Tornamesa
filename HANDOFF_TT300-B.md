# TT300-B · Tornamesa hidráulica 300 tf, acero-acero con grasa grafitada
## Documento de traspaso completo para continuar en Claude Code

> Estado al 30-10-2026. Este archivo reúne todo lo desarrollado: historia de decisiones, diseño vigente, bases de cálculo, resultados, verificaciones, FEA, planos emitidos, la herramienta web interactiva y **el código fuente completo** (apéndices B, C y D). Con este archivo y el ZIP del proyecto (`TT300-B_proyecto_completo.zip`) se puede reconstruir y regenerar todo.

---

## 0. Instrucciones para el agente que retome el trabajo

### 0.1 Perfil y preferencias del usuario (aplicar siempre)
- Ingeniero estructural chileno, revisor de cálculo, especialista en puentes. Conoce NCh, AISC, ASCE 7 y AASHTO.
- Responder en **español**, como **par técnico** (colega), sin explicaciones básicas salvo que las pida.
- Estructura de respuestas técnicas: **hipótesis → desarrollo → resultado**.
- **Tablas** antes que texto corrido para comparar alternativas.
- Resultados con **2–3 cifras significativas**; citar **artículo/ecuación de la norma** en cada fórmula revisada.
- Si un parámetro es ambiguo, **preguntar antes de asumir**.
- Memorias de cálculo en formato listo para Word/PDF. Cuando pida textos en Word y PDF: **letras negras**.
- Unidades SI.

### 0.2 Estructura de carpetas (dentro del ZIP)
```
TT300-B_proyecto/
├── HANDOFF_TT300-B.md            ← este documento
├── tt300/                        ← proyecto vigente 300 tf (Python: planos + 3D)
│   ├── params.py  calc.py  common.py  draw.py  hlr.py  model3d.py  iso.py
│   ├── sheet1.py (D-01)  sheet2.py (D-03)  sheet3.py (F-01)  sheet4.py (F-02)
│   ├── sheet_d02.py (D-02)  sheet_f03.py (F-03)  build300.py  build_all.py
│   ├── out/        ← PDF, DXF, PNG por lámina; STEP/GLB; ZIP DXF+STEP; *_mass.json
│   └── app/        ← herramienta web interactiva (JS)
│       ├── fea.js calc.js diag.js export.js geo.js ui.js shell.html build.py
│       ├── test_fea.js test_calc.js t2.js
│       ├── tests/  (shot.js, g.js, z.js — Playwright)
│       ├── tornamesa.html                       ← versión para publicar como artifact (sin <html>)
│       └── TT300-B_Verificacion_Tornamesa.html  ← versión autónoma
└── tt/                           ← versión anterior 500 tf (TT500-A UHMW y TT500-B acero-grafito, Rev B)
```

### 0.3 Dependencias
| Uso | Herramienta | Versión |
|---|---|---|
| Modelo 3D, STEP, GLB | CadQuery (OCP) | 2.8 |
| Dibujo DXF | ezdxf | 1.4.4 |
| DXF → PDF | ezdxf drawing addon + PyMuPDF (`pymupdf`) | — |
| Achurados / recortes | shapely | — |
| Web 3D | three.js (UMD) + OrbitControls (examples/js) | 0.147.0 |
| PDF en navegador | jsPDF + jspdf-autotable | 2.5.1 / 3.8.2 |
| ZIP en navegador | JSZip | 3.10.1 |
| Pruebas | Node 22 + Playwright (Chromium en `/opt/pw-browsers/chromium`, `--headless=new`) | 1.47.2 |

### 0.4 Comandos
```bash
# Planos 300 tf (desde tt300/)
python3 model3d.py S          # genera out/TT300-B.step/.glb y out/TT300-B_mass.json (necesario antes de las láminas)
python3 calc.py               # imprime cálculo del accionamiento y verificaciones (versión Python)
python3 build300.py           # genera D-01..D-03, F-01..F-03 (PDF+DXF+PNG), PDFs combinados y ZIP DXF+STEP

# Herramienta web (desde tt300/app/)
node test_fea.js              # benchmarks FEA (Navier, voladizo)
node test_calc.js             # resultados de referencia de todo el modelo con valores por defecto
python3 build.py              # arma tornamesa.html (artifact) + TT300-B_Verificacion_Tornamesa.html (autónomo) + site/
cd site && python3 -m http.server 8765   # servidor local de prueba
node tests/shot.js ; node tests/g.js ; node tests/z.js   # pruebas Playwright (rutean los CDN a node_modules locales)
```
Nota: `build.py` copia los PDF y el ZIP de `../out/` a `site/planos/` y los DXF/STEP como `.txt` a `site/planos/src/` (la página publicada los descarga así porque el visor de artifacts no sirve `.zip`/`.dxf`).

### 0.5 Publicación (claude.ai)
- Herramienta web publicada como artifact: `https://claude.ai/artifact/Tx3Mq7RLd2EWdENfYGC9Th` (versión 2), capacidad `downloads`. Archivos adjuntos: `planos/TT300-B_Tornamesa300_Planos_Diseno.pdf`, `planos/TT300-B_Tornamesa300_Planos_Fabricacion.pdf`, `planos/src/*.dxf.txt` y `planos/src/TT300-B.step.txt`.
- Visor 3D de la versión 500 tf (Rev B): `https://claude.ai/artifact/XaEBcsGSwWAXmHmPyT23vU`.
- Restricciones del visor: no permite `<a download>` ni `window.print()`; las descargas usan `claude.use("downloads").save({filename, data})` con extensiones permitidas (pdf, zip, json, txt, png, svg, csv, html…). **DXF no está permitido suelto → se entrega dentro de ZIP.** CDN permitidos: cdnjs, jsdelivr, unpkg.

---

## 1. Historia de decisiones (cronología)

| # | Solicitud del usuario | Resultado / decisión |
|---|---|---|
| 1 | Tornamesa de 500 tf industrial: materiales, espesores, cómo gira, esquema | Esquema inicial: placa base, disco, pivote central, superficie deslizante, accionamiento hidráulico |
| 2 | Revisar Hydra-Slide (grafito) con manual y ficha LGH | Revisión del sistema de deslizamiento con grafito |
| 3 | Usar UHMW en vez de PTFE | Variante A: pastillas UHMW-PE PE1000 sobre pistas inox |
| 4 | ¿Qué es el grafito seco? ¿es pintura? | Explicación de película seca de grafito (SLIP Plate) |
| 5 | ¿Acero-acero con SLIP Plate? | Variante B: acero-acero con película seca de grafito |
| 6 | Planos de detalle y pieza 3D de ambas (UHMW / acero-grafito), con todas las piezas de montaje y fabricación | Juegos TT500-A y TT500-B (4 láminas A1 c/u), STEP, GLB, visor 3D |
| 7 | "¿Tienes certeza de que funciona? ¿Qué fuerza ejerce el cilindro?" | Corrección de cinemática (10° por ciclo), rótulas esféricas GE70 en ambos ojales, enclavamiento hidráulico que prohíbe empujar con un solo cilindro, base agrandada, trinquete en 34CrNiMo6 |
| 8 | Empuje directo sobre barra vertical; disco de 2 planchas con refuerzos interiores y barras perimetrales soldadas entre planchas (con fotos) | **Rev B**: disco cajón (4a–4f), carro guiado + trinquete que empuja la barra |
| 9 | Planos de diseño y fabricación de la alternativa acero-grafito, **300 tf**, claridad absoluta de la fuerza del actuador, conservador, **grasa grafitada entre acero-acero** | Proyecto **TT300-B**: láminas D-01..D-03 y F-01..F-03, cálculo del actuador, verificaciones, lista de corte, soldaduras, detalle de lubricación. Cambios por verificación a fuerza de calado: guía embutida 10 mm en ranura; bisel de barra 10 → 15 |
| 10 | HTML con diseño, verificaciones, análisis de esfuerzos, diagramas, FEA, cargas en pistones, botón PDF/DXF, parámetros variables | Herramienta web paramétrica con FEA propio (Mindlin MITC4 y tensión plana Q4), exportes PDF/DXF/memoria |
| 11 | Panel izquierdo con desplazamiento independiente; esquema 3D + planta + elevación al inicio que se actualice; agente paralelo que verifique cálculos | Pestaña "Modelo" (3D three.js + 3 vistas 2D con resaltado del parámetro editado); paneles con scroll independiente; agente verificador ejecutado (sección 11, apéndice E) |

### 1.1 Variantes 500 tf (carpeta `tt/`, Rev B, entregadas)
- **TT500-A (UHMW):** 34 pastillas Ø170×10 UHMW-PE PE1000 en alojamientos Ø170,6×5 de la placa base, en anillos R300 (6 @30°), R550 (12 @15°), R735 (16 @0°); pistas inox AISI 316L e=3 en el disco: A Ø810/Ø390, B Ø1680/Ø880.
- **TT500-B (acero-grafito, película seca SLIP Plate No. 4):** contacto pleno acero-acero.
- Geometría común Rev B: placa base 2400×2000×80, disco cajón Ø2000×160, 36 barras Ø70 en R940, 2 cilindros 50 t 700 bar, carrera 200.
- Fricción usada en esa etapa: Engineering ToolBox (acero seco 0,5–0,8 estático, 0,42 cinético; engrasado 0,16; grafito 0,058 cinético) y guía de skidding (seco 0,40–0,60, nominal 0,50; engrasado 0,10–0,20, nominal 0,15).
- Problemas resueltos en el generador: proyección HLR propia con gp_Ax2 (getSVG de CadQuery orientaba mal); contenido fuera de 0..841×0..594 desplazaba la página PDF; achurados con polygonize requerían redondear coordenadas a 0,1 y cerrar anillos; `.glb` no es tipo servido → glTF JSON con buffer data-URI; mojibake en visor → meta charset.

---

## 2. Diseño vigente TT300-B

### 2.1 Descripción general
Tornamesa de 300 tf (WLL) para uso industrial. Placa base apoyada en losa o mats; disco cajón que gira sobre la placa base con interfaz **acero-acero lubricada con grasa grafitada**, centrado por un pivote Ø150 con buje autolubricado. Giro por **2 cilindros hidráulicos de 50 t en par** (diagonalmente opuestos), cada uno empuja un carro guiado; el trinquete del carro toma una **barra vertical Ø70** del disco (36 barras cada 10° en R940). Carrera 200 mm = 36 libres + 164 útiles = **10° por ciclo**, 36 ciclos por vuelta. Retorno: el chaflán del trinquete pasa sobre la barra siguiente y un resorte lo reengancha. Válvula de bloqueo: prohibido empujar con un solo cilindro. Giro antihorario con carros en x = ±1085 y ménsulas (+1085; −818) y (−1085; +818); para invertir, girar carros 180° y usar la ménsula opuesta.

### 2.2 Geometría (params.py, mm; z = 0 cara inferior de placa base)
| Elemento | Valor |
|---|---|
| Placa base pos 1 | 2400 (X) × 2000 (Y) × 80; 2 ranuras 40 H8 × 10 para guías; Ø150 H7 pasante para pivote |
| Disco cajón pos 4 | Ø2000 × 160 (TD) |
| 4a plancha superior | Ø2000 × 30; Ø300 central; 36 × Ø71; 4 × M30 (izaje) en R600 a 45°/135°/225°/315° |
| 4b plancha inferior | Ø2000 × 30; Ø300 central; 36 × Ø71; ranuras de lubricación (det. L) |
| Separación entre planchas | 100 |
| 4c cubo | Ø300 × 160; alojamiento buje Ø190 H7 × 100; paso Ø160; contrataladro sup. Ø260 × 25 |
| 4d almas anulares | e = 25, h = 100, en R300 / R550 / R735 |
| 4e nervios radiales | 12 × e = 20, h = 100, de R150 a R880 (tramos 137,5 / 225 / 160 / 132,5 entre almas) |
| 4f barras de empuje | 36 × Ø70 × 160 en R940, la primera a 5°, paso 10°; agujeros Ø71; bisel PJP 15 (E = 12) a ras en ambas caras |
| Pivote pos 5 | Ø150 × 218 (42CrMo4+QT); 6 × M20 prof. 32 en PCD 100 |
| Buje pos 6 | Ø190/Ø150 × 100 CuAl10Ni5Fe4 + insertos de grafito |
| Tapa pos 7 | Ø240 × 20, 6 pernos M20 × 45 10.9 + Nord-Lock (pos 8), juego vertical 3 mm |
| Niveles (variante S) | cara inf. disco z = 80; sup. z = 240; eje cilindros z = 160 (h_axis 80 sobre la base); mejillas H = 150; tope carro z = 230; tope pivote z = 218; tope buje z = 180 |
| Cilindros pos 9 | 2 × 50 t doble efecto, 700 bar, F ≥ 445 kN, carrera 200, L0 = 450 ojal-ojal retraído (650 extendido), cuerpo Ø140, ojales con rótula GE70 (ancho 70, Ø120), pasadores Ø70 |
| Posición cilindros | eje x = ±1085; pasador de ménsula y = ∓818 |
| Carro pos 10 | 130 × 300 × 150 (S355J2+N); x = 1020–1150; cara frontal 20 sobre el centro de la barra; ranura 41 H11 × 31 sobre la guía; horquilla 80 para ojal; pasador del vástago a 250 detrás del centro de barra |
| Trinquete pos 11 | 245 × 85 × 90 (34CrNiMo6+QT, 300–350 HB); punta en x = 905; asiento R36; chaflán de retorno; resorte Ø50 (pos 13) |
| Guía pos 22 | 40 × 40 × 850 S355J2, **embutida 10 en ranura 40 H8** de pos 1; filete 8 ambos lados (W5) |
| Ménsula pos 2 | 2 mejillas 40 × 280 × 150 separadas 80 + respaldo 40 × 160 × 150; agujero Ø71 H9 en línea |
| Oreja izaje pos 3 | 40 × 150 × 170, R60 superior, Ø32; 4 un. en x = ±600, bordes en Y |
| Sello | faldón NBR e = 5, h = 30, L ≈ 6300 (pos 14); fleje 25 × 6 rolado Ø2022 (pos 15); 36 × M8 × 20 A2-70 (pos 16) en el canto de 4b a 0° + 10°k |
| Lubricación | grasa grafitada pos 19; 4 graseras DIN 71412 M10×1 (pos 20) |

### 2.3 Lista de materiales (BOM, lámina D-01)
| Pos | Descripción | Cant. | Material | kg/u |
|---|---|---|---|---|
| 1 | Placa base 2400×2000×80 mec. (2 ranuras 40H8×10) | 1 | ASTM A572 Gr.50 – Z35 | 2998,0 |
| 2 | Ménsula de reacción (conj. soldado) | 4 | ASTM A572 Gr.50 | 31,4 |
| 3 | Oreja de izaje e = 40 | 4 | ASTM A572 Gr.50 | 7,3 |
| 4 | Disco cajón Ø2000×160 (conj. soldado 4a–4f) | 1 | ASTM A572 Gr.50 – Z35 | 1922,2 |
| 5 | Pivote Ø150×218 | 1 | 42CrMo4+QT (EN 10083-3) | 29,8 |
| 6 | Buje Ø190/Ø150×100 autolubricado | 1 | CuAl10Ni5Fe4 + grafito | 8,1 |
| 7 | Tapa retenedora Ø240×20 | 1 | S355J2 | 6,5 |
| 8 | Perno ISO 4762 M20×45 + arandela Nord-Lock | 6 | 10.9 zincado laminar | 0,2 |
| 9 | Cilindro hidráulico doble efecto 50 t, 700 bar, carrera 200 | 2 | Comercial | 47,5 |
| 10 | Carro de empuje 300×130×150 (guiado) | 2 | S355J2+N | 24,7 |
| 11 | Trinquete 245×85×90 (asiento R36) | 2 | 34CrNiMo6+QT 300–350 HB | 12,6 |
| 12 | Pasador Ø70 (ménsula y vástago) | 4 | 42CrMo4+QT | 5,6 |
| 13 | Resorte del trinquete Ø50 + tapa + manilla; clip R Ø8 | 2+4 | Comercial | 0,6 |
| 14 | Faldón de sello e = 5, h = 30, L ≈ 6300 | 1 | NBR 70 Shore A | 1,1 |
| 15 | Fleje de apriete 25×6 rolado Ø2022 | 1 | S235JR galvanizado | 7,5 |
| 16 | Perno ISO 4017 M8×20 + arandela | 36 | Inox A2-70 | 0,02 |
| 17 | Tapón prisionero M30×25 (agujeros de izaje del disco) | 4 | Acero 8.8 zincado | 0,1 |
| 18 | Cáncamo giratorio M30, WLL ≥ 2,5 t (suelto) | 4 | Comercial | 2,2 |
| 19 | Grasa grafitada NLGI 2 (≥ 10 % grafito), 0,3–0,5 mm/cara | ≈ 2,5 kg/aplicación | Ver especificación D-02 | — |
| 20 | Grasera recta DIN 71412 M10×1 + tapa | 4 | Acero zincado | 0,05 |
| 22 | Guía de carro 40×40×850 (embutida 10 en pos 1) | 2 | S355J2 | 10,7 |

Masa total aproximada del conjunto: ≈ 5354 kg (sin carga, incluye cilindros). Masas de CadQuery: `out/TT300-B_mass.json` = {1: 2998,0; 2: 125,7; 3: 29,1; 4: 1922,2; 5: 29,8; 6: 8,1; 7: 6,5; 8: 1,1; 9: 95,0; 10: 49,4; 11: 25,2; 12: 22,4; 22: 21,4; 14: 1,1; 15: 7,5}.

### 2.4 Despiece del disco (pos 4)
| Sub | Descripción | Cant. | kg total |
|---|---|---|---|
| 4a | Plancha sup. Ø2000×30; Ø300, 36×Ø71, 4×M30 | 1 | 689,1 |
| 4b | Plancha inf. Ø2000×30; Ø300, 36×Ø71 | 1 | 689,6 |
| 4c | Cubo Ø300/Ø190×160 (S355J2+N, forja) | 1 | 50,6 |
| 4d | Almas 25×100 roladas, eje Ø600/1100/1470 | 3 | 195,4 |
| 4e | Nervios 20×100, L 137,5/225/160/132,5 (×12) | 48 | 123,4 |
| 4f | Barras Ø70×160 (S355J2 laminado) | 36 | 174,0 |

### 2.5 Ajustes y pares (lámina D-03)
| Unión | Ajuste / valor | Obs. |
|---|---|---|
| Pivote 5 / placa base 1 | Ø150 H7/p6 | Calado en caliente (pos 1 local ≤ 200 °C o enfriar pos 5) + soldadura de sello inferior |
| Pivote 5 / buje 6 | Ø150 H7/f7 | Giratorio |
| Buje 6 / disco 4 | Ø190 H7/s6 | Prensado |
| Trinquete 11 / alojamiento carro 10 | 85×90 H9/f8 | Deslizante |
| Carro 10 / guía 22 | Ranura 41 H11 / 40 h9 | Guiado, ranura lubricada con grasa grafitada |
| Barra 4f / agujeros 4a, 4b | Ø70 / Ø71 | Soldada |
| Pasadores 12 / ménsula, carro | Ø70 H9/f8 (rótula GE70) | Deslizante |
| Pernos 8 M20 10.9 (VDI 2230, μ 0,12) | 540 N·m | Nord-Lock |
| Pernos 16 M8 A2-70 | 18 N·m | Antigripante |
| Tapones 17 M30 | Manual + fijador media | A ras con el disco |

### 2.6 Montaje, operación y mantenimiento (lámina D-03)
**Montaje:** 1) placa base (con pos 2, 3, 22 soldadas, relevada y mecanizada) sobre apoyo nivelado ≤ 0,5 %; 2) pivote calado en caliente H7/p6 + soldadura de sello; 3) limpiar caras de pos 1 y 4b, aplicar grasa grafitada 0,3–0,5 mm y llenar ranuras; 4) buje prensado H7/s6, verificar planitud ≤ 0,20 de ambas caras antes de lubricar; 5) izar el disco con 4 cáncamos M30 y bajar centrado; 6) tapa con 6 × M20 10.9 a 540 N·m, juego vertical 3 mm; 7) faldón y fleje con 36 × M8, retirar cáncamos, colocar tapones; 8) carros sobre guías con trinquete y resorte; cilindros entre ménsula activa y carro con pasadores + clips; mangueras 700 bar (CR400); 9) prueba en vacío (2 ciclos) y luego ensayo de carga.
**Operación por ciclo:** a) extender ambos cilindros a la vez (colector común): 36 mm libres, el trinquete toma la barra y la carga gira 10°; b) retraer a fondo: el chaflán pasa sobre la barra siguiente; verificar enganche visual de ambos trinquetes; c) registrar presión (esperada ≈ 313 bar); detener si supera 600 bar; d) invertir sentido girando carros 180° y usando la ménsula opuesta; e) no operar con viento > 50 km/h ni con carga sin arriostrar.
**Mantenimiento:** antes de cada operación ≈ 60 g por grasera (4); si p > 600 bar detener, levantar, limpiar y relubricar; usar solo la grasa especificada; mantener el faldón; guardar bajo techo con el disco calzado.

### 2.7 Notas generales (lámina D-01)
1. Capacidad nominal (WLL) 300 tf = 2942 kN; φd = 1,10; excentricidad del CG ≤ 150 mm; carga solo dentro de Ø1600 sobre parrilla de reparto o ≥ 8 apoyos simétricos; prohibidas cargas puntuales sobre el disco.
2. Normas: AISC 360-22 (ASD); ASME BTH-1 Cat. A (Nd = 2,0, referencial elementos mecánicos); AWS D1.1/D1.1M:2020; ISO 2768-mK; ISO 1101; ISO 1302.
3. Materiales con certificado EN 10204 3.1; planchas pos 1 y 4 con UT ASTM A578 nivel B, calidad Z35.
4. Soldadura con WPS/PQR calificados AWS D1.1; E7018 / ER70S-6; precalentamiento ≥ 110 °C en espesores > 65 mm (AWS D1.1 Tabla 5.8, Cat. B); CJP UT 100 %; filetes MT 100 %.
5. Alivio de tensiones 590–620 °C de los conjuntos 1+2+3+22 y 4 antes del mecanizado final.
6. Protección: Sa 2½ + epóxico rico en zinc 75 µm + epóxico 125 µm + PU 50 µm (ISO 12944, C4); sin pintura en caras de giro, alojamientos, agujeros de pasadores, buje y roscas.
7. Interfaz de giro: contacto pleno acero-acero con grasa grafitada en ambas caras, ranuras en 4b y 4 graseras (relubricación sin levantar el disco). Lubricar antes de cada operación. Acero seco (μ 0,5–0,8) no gira.
8. Accionamiento: 2 cilindros en par; fuerza de diseño por cilindro 315 kN (496 bar, μ = 0,20); capacidad 445 kN a 700 bar (FS 1,41); detener y relubricar si p > 600 bar (μ > 0,24). Rótulas GE70; prohibido empujar con un solo cilindro.
9. Apoyo: base totalmente apoyada en losa o mats rígidos; pendiente ≤ 0,5 %; presión bajo la base 0,62 MPa media / 0,90 MPa máx. (e = 150).
10. Ensayo: giro 360° a 1,0 WLL registrando presión; estático 1,25 WLL si hay marco de reacción; MT de soldaduras pos 2/3/22 posterior al ensayo.
11. Cilindro L0 = 450 entre ojales: verificar con el proveedor y ajustar la posición de pos 2 si difiere.

---

## 3. Bases de cálculo e hipótesis

| Id | Hipótesis |
|---|---|
| H1 | W = 300 tf × 9,80665 = 2942,0 kN; e ≤ 150 mm; peso disco + buje ≈ 1922 kg (18,85 kN; la herramienta web calcula 1930,8 kg por geometría); N = W + Wd ≈ 2960,8–2960,9 kN. φd = 1,10 solo para resistencias |
| H2 | Interfaz plana anular acero/acero, R = 1000 mm, r = 95 mm, con grasa grafitada |
| H3 | μ estático de diseño 0,20 = límite superior de acero engrasado (0,10–0,20). Nominal 0,15; contaminado 0,25; seco 0,50 (real 0,5–0,8, prohibido) |
| H4 | r uniforme = 2/3·(R³ − r³)/(R² − r²) = 0,672 m. La distribución lineal por excentricidad **no** cambia el par (∫x·r dA = 0). Diseño r_ef = 0,80 m (concentración al borde por flexión del disco); cota física 0,94 m |
| H5 | Empuje en par: 2 cilindros simultáneos; fuerza paralela a Y; barra entre −5° y +5°; brazo mínimo a = 940·cos 5° = 936,4 mm |
| H6 | Pérdidas: μg = 0,15 en carro/guía por el par de excentricidad Δ = 1085 − 936,4 = 148,6 mm; reacciones de guía separadas Lg = 250 mm; ηc = 0,95 |
| H7 | Buje del pivote: H = 5 % W, μ = 0,20, r = 75 mm → T_piv = 2,21 kN·m |
| H8 | Cilindro Ø90 → A = 6362 mm² (Python usa 445e3/70 = 6357 mm²); F = 445 kN a 700 bar (alivio); operación ≤ 600 bar |
| H9 | La cadena de empuje se verifica a la **fuerza de calado 445 kN** (alivio), no a la de diseño |
| H10 | Rótulas GE70 en ambos ojales (sin momento en el vástago); velocidad de giro ≤ 1 °/s |

---

## 4. Cálculo del accionamiento

### 4.1 Fórmulas
| Ec. | Expresión |
|---|---|
| (1) | T_f = μ · N · r_ef |
| (2) | T = T_f + T_piv |
| (3) | F_barra = T / (2a) |
| (4) | K = (1 + 2·μg·Δ/Lg) / ηc = (1 + 2·0,15·0,1486/0,250)/0,95 = **1,240** |
| (5) | F_cil = K · F_barra |
| (6) | p = F_cil / A |
| (7) | FS = 445 kN / F_cil |
| (8) | μ_max = (p_max·A·2a/K − T_piv) / (N · r_ef) |
| (9) | Equilibrio del carro: F_cil·ηc = F_barra + 2·μg·R ; R = F_barra·Δ/Lg |
| (10) | Ciclo: s = libre + 2·R_b·sin(180°/N_b) = 36 + 163,9 = 199,9 mm ≤ 200 |

### 4.2 Caso de diseño (μ = 0,20; r = 0,80 m)
T_f = 0,20 × 2960,8 × 0,80 = 473,7 kN·m → T = 475,9 kN·m → F_barra = 475,9/(2 × 0,9364) = 254,1 kN → F_cil = 1,240 × 254,1 = **315,2 kN (32,1 tf)** → p = 315 200 / 6357 = 49,6 MPa = **496 bar** (495 bar con A = 6362) → **FS = 1,41**.

### 4.3 Casos
| Caso | μ | r_ef (m) | T (kN·m) | F_barra (kN) | F_cil (kN) | p (bar) | FS | Resultado |
|---|---|---|---|---|---|---|---|---|
| Nominal (grasa limpia) | 0,15 | 0,672 | 301 | 161 | 199 | 313 | 2,23 | Gira |
| **Diseño** | **0,20** | **0,80** | **476** | **254** | **315** | **495–496** | **1,41** | **Gira** |
| Contaminado | 0,25 | 0,80 | 594 | 317 | 394 | 619 | 1,13 | Gira (límite; sobre alarma) |
| Acero seco | 0,50 | 0,672 | 997 | 532–533 | 660 | 1038–1039 | 0,67 | **No gira** |

### 4.4 Fricción máxima vencible
| r_ef (m) | μ_max a 700 bar | μ_max a 600 bar |
|---|---|---|
| 0,672 | 0,337 | 0,288 |
| 0,80 | 0,283 | 0,242 |
| 0,94 | 0,241 | 0,206 |

### 4.5 Carga en cada pistón a lo largo de la carrera (diseño)
| Posición | Nominal kN / bar | Diseño kN / bar | Contaminado kN / bar |
|---|---|---|---|
| Recorrido libre 0–36 mm | ≈ 0 | ≈ 0 | ≈ 0 |
| Toma la barra (θ = −5°) | 199 / 313 | 315 / 495 | 394 / 619 |
| Centro (θ = 0°) | 198 / 311 | 313 / 492 | 391 / 614 |
| Suelta la barra (θ = +5°) | 199 / 313 | 315 / 495 | 394 / 619 |
| Alarma | 382 kN / 600 bar | | |
| Alivio = calado | 445 kN / 700 bar | | |

### 4.6 Reacciones por cilindro
| Elemento | Diseño (kN) | Calado (kN) |
|---|---|---|
| Ménsula pos 2 (pasador Ø70) | 315 | 445 |
| Pasador, cada plano de corte | 158 | 223 |
| Barra 4f (trinquete) | 254 | 359 |
| Guía pos 22, cada reacción R | 151 | 265 |
| Pivote (2 cilindros en par) | 0 | 0 |
| Pivote (accidental, 1 cilindro, bloqueado por válvula) | 315 | 445 |

### 4.7 Desglose de la fuerza de diseño (315 kN)
| Componente | kN | % |
|---|---|---|
| Fricción interfaz μ·N·r | 253,0 | 80,3 |
| Buje del pivote | 1,2 | 0,4 |
| Fricción carro/guía | 45,3 | 14,4 |
| Sellos del cilindro | 15,8 | 5,0 |

### 4.8 Ajustes hidráulicos y criterio de operación
- Alivio 700 bar; bomba ≥ 700 bar; manómetro glicerina 0–1000 bar clase 1,0.
- Presión esperada nominal ≈ 313 bar; despegue de diseño ≤ 496 bar.
- Alarma/detención > 600 bar (μ equivalente > 0,24 con r 0,80): retraer, relubricar por las 4 graseras, inspeccionar, reintentar.
- Prohibido aumentar el alivio sobre 700 bar y operar con un solo cilindro.
- **Ensayo de aceptación a 1,0 WLL:** medir presión de despegue y calcular μ_real = (p·A·2a/K − T_piv)/(N·0,80). Aceptación μ_real ≤ 0,20 (p ≤ 496 bar).

---

## 5. Verificaciones de elementos (valores por defecto, herramienta web)
Cadena de empuje a F calado = 445,3 kN. Clasificación: FU ≤ 0,90 aceptable; 0,90–1,00 monitoreo; > 1,00 no cumple. Las filas "Cumple" son chequeos de paso/no paso.

| Grupo | Elemento | Fórmula | Demanda | Capacidad | FU | Referencia |
|---|---|---|---|---|---|---|
| Accionamiento | F diseño vs capacidad | F_cil = K·T/(2a) ≤ A·p_alivio | 315,2 kN | 445,3 kN | 0,71 | Ec. (5) / 700 bar |
| Accionamiento | Presión de diseño vs alarma | p = F_cil/A ≤ p_alarma | 495,5 bar | 600 bar | 0,83 (cumple) | Criterio de operación |
| Accionamiento | Carrera requerida | s = libre + 2R_b·sin(180°/N_b) | 199,85 mm | 200 mm | 1,00 (cumple, sin margen) | Cinemática |
| Interfaz | Presión de contacto máx. | q = N_D/A·(1 + 4eR/(R²+r²)) | 1,67 MPa | 10 MPa | 0,17 | Criterio acero/acero lubricado |
| Disco (FEA) | Plancha inf. 4b σvm máx. | FEA Mindlin MITC4 | 25,6 MPa | 207 MPa | 0,12 | AISC 360-22 F11 (0,6Fy) |
| Disco (FEA) | Plancha sup. 4a σvm máx. | FEA, q = φd·W/A_parrilla | 24,4 MPa | 207 MPa | 0,12 | AISC 360-22 F11 |
| Disco (FEA) | Almas 4d compresión | σ = r_línea / t_alma | 9,7 MPa | 207 MPa | 0,05 | AISC 360-22 J10.2 / E3 |
| Disco (FEA) | Barra 4f compresión axial | σ = R_barra / A | 13,7 MPa | 207 MPa | 0,07 | AISC 360-22 E3 |
| Disco | Flexión global del cajón (voladizo anular) | M = q_max·(R − R_carga)²/2; S = t·(TD − t) | 8,6 MPa | 207 MPa | 0,04 | AISC 360-22 F11 |
| Barra 4f | Flexión (rotulada) | M = F/4·(L − c/2); Mn = Fy·d³/6 | 6,12 kN·m | 11,81 kN·m | 0,52 | AISC 360-22 F11.1, Ω 1,67 |
| Barra 4f | Corte | τ = 4V/(3A), V = F/2 | 77,1 MPa | 138 MPa | 0,56 | AISC 360-22 G1, Ω 1,50 |
| Barra 4f | Soldadura bisel 15 (E = 12) | √(τV² + τM²); M = F(3L²−c²)/(24L) | 121,9 MPa | 147 MPa | 0,83 | AISC 360-22 J2.5, Ω 2,0 |
| Barra 4f | Aplastamiento en agujero | σ = (F/2)/(t·d) | 106 MPa | 310,5 MPa | 0,34 | AISC 360-22 J7, Ω 2,0 |
| Trinquete | Flexión en boca (vigas) | σ = F·(x_boca − a)/(h·b²/6) | 343 MPa | 400 MPa | **0,86** | ASME BTH-1 (Fy/Nd, Fy 800) |
| Trinquete | Flexión en boca (FEA) | Q4 tensión plana, h = 2,5 mm | 297 MPa | 400 MPa | 0,74 | ASME BTH-1 |
| Guía 22 | Aplastamiento en ranura | R = F·Δ/Lg; σ = R/(e·L) | 176 MPa | 310,5 MPa | 0,57 | AISC 360-22 J7 |
| Guía 22 | Flexión en raíz | M = R·h/2 | 3,97 kN·m | 12,40 kN·m | 0,32 | AISC 360-22 F11.1 |
| Ménsula 2 | Flexión de mejillas en la base | σ = F·h/(2·t·L²/6) | 34,1 MPa | 207 MPa | 0,16 | AISC 360-22 F11 / CJP J2 |
| Pasador 12 | Flexión en horquilla | M = F/2·(t/2 + g + b/4) = 9,46 kN·m | 281 MPa | 325 MPa | **0,86** | Fy/Nd (Fy 650) |
| Pasador 12 | Corte doble | τ = (F/2)/A ≤ Fy/(Nd·√3) | 57,9 MPa | 187,6 MPa | 0,31 | ASME BTH-1 3-2.2 |
| Pivote | Presión en buje | p = H/(D·L), H = 5,5 % W | 10,8 MPa | 30 MPa | 0,36 | Fabricante bronce-grafito |
| Pivote | Flexión | σ = H·e/(πD³/32), e = 50 | 24,4 MPa | 325 MPa | 0,08 | Fy/Nd |
| Cilindro | Pandeo del vástago (Ø63 supuesto) | Pcr = π²EI/L², L = 650 | 445 kN | 1204 kN (Pcr/3) | 0,37 | Euler, FS 3 |
| Apoyo | Presión bajo placa base | σ = N/A·(1 + 6e/B) | 0,90 MPa | 1,00 MPa (ref.) | 0,90 (cumple) | Referencial; verificar losa |

Accidental, un solo cilindro (prohibido por válvula): buje 29,7 MPa / 30 MPa (FU 0,99, sin margen).

**Valores que estaban en la versión Python (calc.py / lámina D-02 emitida) y difieren:** plancha 4a 67 MPa (FU 0,32) y 4b 70 MPa (FU 0,34) eran estimaciones manuales por franja; el FEA da 24,4 y 25,6 MPa. Almas 4d 13 MPa (FU 0,06) en Python. Pivote: en Python se indicó 24,5 MPa con FU 0,09/0,08. En la etapa de cálculo inicial (resumen previo) figuraban barra 91 MPa (FU 0,53), pasador flexión 198 MPa (FU 0,61) y soldadura de guía (filete 12, 84 MPa, FU 0,57); estos fueron reemplazados al verificar a 445 kN: el filete de guía daba FU ≈ 1,27 (por eso la guía se embutió), el bisel de barra 10 se subió a 15, y el pasador con el modelo de horquilla da 281 MPa (FU 0,86).

---

## 6. FEA

### 6.1 Motor (fea.js)
- Solver: Cholesky de banda simétrica (almacenamiento superior por filas). Apoyos por penalización kp = 10⁶ · max(Kii); reacción = −kp·u.
- **Placa Mindlin MITC4** (Bathe-Dvorkin): GDL por nodo (w, βx, βy); flexión 2×2 Gauss; corte transversal con puntos de amarre A(0,1), C(0,−1) para γξ y B(−1,0), D(1,0) para γη; transformación γ = J⁻¹·γ_nat; k = 5/6. Tensiones σ = 6M/t², von Mises en el centro y en los 4 puntos de Gauss (se informa el máximo de Gauss).
- **Tensión plana Q4** con integración completa 2×2.
- Validación: placa cuadrada simplemente apoyada a = 1000, t = 10, q = 0,01 MPa, malla 20×20: w = 2,2178 mm vs Navier 2,2168 (0,05 %); Mx máx 476,1 vs 479 N·mm/mm (0,6 %). Voladizo L 1000, h 100, t 10, P 1000 N, malla 80×10: flecha 1,997 vs 2,026 mm (1,4 %); σx en el centro del elemento de raíz 55,3 MPa (consistente con 59,6·45/50).

### 6.2 Modelo del disco (calc.js, discModel/runDisc)
- Sector de 360°/N_rib (30°) entre nervios, malla polar: radios clave (cubo, almas, R_rib, R_bar ± D_bar/2, R, Ø parrilla) subdivididos a h_r = max(20, (R − r_hub)/45); ángulos clave (0, α, barras y sus bordes) subdivididos a max(1,25°, α/36). Por defecto 1316 elementos, 1392 nodos, 4176 GDL.
- Condiciones de borde: borde del cubo empotrado; almas 4d (líneas r = cte) y nervios 4e (bordes del sector hasta R_rib) con w = 0; barras 4f como apoyos de área (nodos dentro de Ø70) con w = 0; simetría en los bordes del sector con β·n = 0 (penalización).
- Cargas: plancha inferior 4b con q_max = 1,667 MPa uniforme (conservador); plancha superior 4a con q = φd·W/(π·800²) = 1,610 MPa dentro de Ø1600.
- Resultados: 4b σvm máx 25,6 MPa en r = 406 mm, θ = 0,5° (sobre el nervio, entre almas R300 y R550); w máx 0,019 mm; reacciones de almas 146/211/244 N/mm; barras 41,2/52,8/41,2 kN; nervio 125,5 kN; cubo 3,8 kN; Σ carga = Σ reacciones = 426,7 kN. 4a: 24,4 MPa; reacciones almas 141/211/188 N/mm; barras 1,2/1,8/1,2 kN; Σ 260,2 kN.
- Interpretación: apoyos rígidos = flexión local de cada paño (gobierna el espesor). La flexión global del cajón se verifica aparte (8,6 MPa).

### 6.3 Modelo del trinquete (runPawl)
- Rectángulo L × b = 245 × 85 (coordenadas locales desde la punta), espesor 90 (= pawl_h), malla 2,5 mm (98 × 34), elementos eliminados en el asiento R36 (centro en x = a − 905 = 31,4; y = 85) y en la cuña de retorno (triángulo 60 × 36, escalado con b/85).
- Apoyos: uy = 0 en los 25 mm inferiores desde la boca del carro (x = 1020 − 905 = 115) y en los 25 mm superiores del extremo posterior (labio); ux = 0 en un nodo posterior.
- Carga: F calado 445,3 kN en el asiento, en dirección −y, con distribución cos(φ + 90°) por sector de 3° (ΣFy = −445,3 kN, ΣFx = 0).
- Resultados: σ boca, fibra traccionada 297 MPa (FU 0,74); teoría de vigas 343 MPa (FU 0,86, gobierna); máx. fuera de zonas de contacto (≥ 10 mm) 355 MPa (0,89); pico local en apoyo/contacto 942 MPa (singularidad del apoyo puntual); desplazamiento máx. 0,79 mm; 2847 elementos, 6930 GDL.

---

## 7. Lubricación (pos 19 y 20)
- Grasa grafitada NLGI 2, base complejo de litio o calcio, grafito ≥ 10 % en peso, aditivo EP (4 bolas ≥ 2500 N), −20/+150 °C, resistente al lavado por agua (o equivalente aprobado).
- Aplicar 0,3–0,5 mm por cara en pos 1 (zona Ø2000) y 4b, llenando las ranuras (≈ 2,5 kg por aplicación).
- Relubricar ≈ 60 g por grasera (4 × pos 20) antes de cada operación y cada 90° de giro con carga.
- No usar grasas sin sólidos ni aceites: a 1,0–1,7 MPa la película fluida se expulsa; el grafito mantiene la capa límite (μ 0,10–0,20). El grafito es conductor eléctrico: aislar equipos energizados.
- **Detalle L (cara inferior de 4b):** 12 ranuras radiales c/30° (0°…330°, en ejes de nervios) de R200 a R960; 3 ranuras circunferenciales R350/R600/R850; sección R3 × 2 de profundidad (ancho ≈ 5,7), Ra 1,6, aristas matadas 0,5; libre ≥ 82 mm a las barras; mecanizar después del alivio de tensiones y del refrentado de 4b.
- **Detalle L2 (graseras):** 4 graseras a 45° + 90°k en el canto de 4b; rosca M10×1 L12; taladro radial Ø6 ciego L150 (R1000 → R850) a 8 mm sobre la cara inferior; taladro Ø6 vertical a la ranura R850; perforar faldón y fleje Ø24.
- Fuentes de fricción: [1] Engineering ToolBox, "Friction and Friction Coefficients" (acero/acero seco μs 0,5–0,8; engrasado 0,16) https://www.engineeringtoolbox.com/friction-coefficients-d_778.html; [2] guía de deslizamiento de cargas pesadas (rigging/skidding): seco 0,40–0,60, engrasado 0,10–0,20.

---

## 8. Planos emitidos (TT300-B, Rev. 0, 21-10-2026, "emitido para revisión – no apto para fabricación hasta aprobación")

| Plano | Archivo generador | Contenido |
|---|---|---|
| TT300-B-D-01 | sheet1.py | Planta 1:10, corte A-A 1:10, corte B-B por eje de cilindro 1:5, det. C pivote 1:2, det. D borde e interfaz 1:2, det. E trinquete y barra 1:2,5, BOM, notas generales, datos técnicos |
| TT300-B-D-02 | sheet_d02.py | Hipótesis, esquema de fuerzas, desarrollo del cálculo del actuador, casos, μ_max, ajustes hidráulicos, especificación de grasa, fuentes, gráfico F vs μ, tabla de verificación, recuadro de resultado |
| TT300-B-D-03 | sheet2.py | Isométricas (conjunto y explosionada), montaje, operación, mantenimiento, ajustes y pares |
| TT300-B-F-01 | sheet3.py | Placa base (conj. 1+2+3) en planta y elevación, disco cajón en planta y corte, det. F superficie de contacto, det. H cubo, det. J barra, tolerancias, secuencias de fabricación, despiece pos 4 |
| TT300-B-F-02 | sheet4.py | Piezas mecánicas: pivote, buje, tapa, trinquete, carro, pasador, ménsula, oreja, especificación del cilindro, pos 19/20, detalle del sello |
| TT300-B-F-03 | sheet_f03.py | Lista de corte completa, programa de soldaduras W1–W11, precalentamiento y secuencia, det. L (ranuras), L1 (sección ranura 5:1), L2 (grasera 1:2), det. M (guía embutida 1:1), control dimensional y ensayos |

Salidas: `out/TT300-B_Tornamesa300_Planos_Diseno.pdf` (D-01..D-03), `out/TT300-B_Tornamesa300_Planos_Fabricacion.pdf` (F-01..F-03), `out/TT300-B_Tornamesa300_DXF_STEP.zip` (6 DXF + STEP).

### 8.1 Programa de soldaduras (F-03)
| Junta | Elementos | Tipo y preparación | Tamaño | END |
|---|---|---|---|---|
| W1 | 2a – 1 | CJP doble bisel 45°, raíz 3 + filete de refuerzo 8 | 280 × 2 × 8 | UT 100 % |
| W2 | 2b – 1 | Filete ambos lados | 16 | MT 100 % |
| W3 | 2b – 2a | Filete ambos lados (vertical) | 16 | MT 100 % |
| W4 | 3 – 1 | Filete todo alrededor | 12 | MT 100 % |
| W5 | 22 – 1 | Filete ambos lados continuo (fijación; carga por aplastamiento) | 8 | MT 100 % |
| W6 | 4c – 4b / 4c – 4a | CJP bisel 45° con respaldo, por el exterior del cubo | t = 30 | UT 100 % |
| W7 | 4d – 4b | Filete ambos lados continuo | 8 | MT 100 % |
| W8 | 4e – 4b / 4c / 4d | Filete ambos lados continuo | 8 | MT 100 % |
| W9 | 4a – 4d / 4e | Soldadura en ranura 22×80 c/250, relleno completo (88 un.) | c/250 | MT 100 % |
| W10 | 4f – 4a / 4b | PJP bisel 15 todo alrededor (E = 12), a ras y mecanizado | 15 | MT 100 % |
| W11 | Empalmes 4d | CJP a tope en V 60°, raíz 3 (1 por anillo) | t = 25 | UT 100 % |

Precalentamiento (AWS D1.1 Tabla 5.8, Cat. B, espesor mayor): t > 65 (pos 1) 110 °C; 38 < t ≤ 65: 65 °C; 20 < t ≤ 38 (disco): 10 °C, se exige 50 °C mín.; interpase ≤ 250 °C. Secuencia del disco: W7 → W8 → W6 (4b) → W10 (4b) → montar 4a → W9 → W6 (4a) → W10 (4a), por cuadrantes opuestos; alivio 590–620 °C antes del mecanizado final.

### 8.2 Lista de corte (F-03) — ver `sheet_f03.cut_rows()` en el apéndice C para los valores exactos
Incluye pos 1, 2a, 2b, 3, 22, 4a, 4b, 4c, 4d1–4d3 (desarrollos 1885/3456/4618 + 20 de recorte), 4e1–4e4 (×12 c/u), 4f (Ø70×164 bruto → 160), 5, 6, 7, 10, 11, 12 (Ø95×220 bruto → Ø70 f8×200 + cabeza Ø90×15), 14, 15. Total de piezas fabricadas ≈ 5246 kg. Sobremetal 2,5 mm/cara en caras funcionales.

### 8.3 Tolerancias y control (F-01 / F-03)
Cara sup. pos 1 planitud 0,20 en Ø2000, Ra 3,2/1,6–3,2; 4b planitud 0,20, paralelismo con 4a 0,30; Ø150 H7 y Ø190 H7 perpendicularidad 0,05; barras PCD 1880 ±0,5, paso 10° ±0,05°, verticalidad 0,3 en 160; ménsulas Ø71 H9 en línea tras soldar y relevar, coaxialidad 0,10, altura eje ±0,5; ranuras 40 H8 paralelas a Y ±0,10 en 850; ranuras de lubricación prof. 2 +0,3/0 con prueba de continuidad; UT de planchas ASTM A578 nivel B; dureza pos 11 300–350 HB, pos 12 28–34 HRC; ISO 2768-mK, aristas 1×45°.

---

## 9. Herramienta web interactiva (tt300/app)

### 9.1 Arquitectura
| Archivo | Función |
|---|---|
| fea.js | Motor FEA (Band, cholSolve, plate MITC4, planeStress Q4) |
| calc.js | PARAM_GROUPS (67 parámetros con valor Rev. 0), defaults, discMass, compute (accionamiento, curva de carrera, desglose, contacto, suelo), verifs (25 chequeos), discModel/runDisc, runPawl |
| diag.js | Diagramas SVG: planta con fuerzas, cuerpo libre del carro, barra 4f (V, M), pasador (M), gráfico F–μ, gráfico F–carrera, desglose |
| geo.js | Pestaña Modelo: PART_OF (parámetro → elementos), vistas 2D planta / elevación ×2,2 / detalle borde con resaltado; Geo3D (three.js) con vistas iso/planta/frente/lateral y plancha 4a transparente/sólida/oculta |
| export.js | Sheet (primitivas en mm de papel), buildSheet (plano paramétrico A1 TT300-B-P-01: planta 1:10, corte 1:10, detalle borde 1:2,5, detalle carro 1:4, notas, tablas de parámetros, accionamiento y FU), sheetSVG / sheetDXF (R12 AC1009, capas VIS FINA EJE OCU COTA TXT MARCO FUERZA) / sheetPDF (jsPDF), memoriaPDF (A4 con autotable e imágenes) |
| ui.js | Formulario, validación, recálculo con debounce 380 ms, render de todas las pestañas, lectura de valores al pasar el cursor sobre el FEA, descargas (capacidad `downloads` con respaldo `<a download>`), pestañas con hash, localStorage `tt300b-params-v1` |
| shell.html | HTML + CSS (tokens claro/oscuro; Barlow Condensed / IBM Plex Sans / IBM Plex Mono) y marcadores `/*@@...@@*/` donde build.py inserta el JS |

Pestañas: Modelo · Resumen · Cilindros · Diagramas · Verificaciones · FEA · Planos. Layout: panel de parámetros y panel de resultados con scroll independiente (≥ 980 px); en celular se apilan.

### 9.2 Parámetros (valores Rev. 0)
Carga: W 300 tf; e 150; φd 1,10; parrilla Ø1600. Disco: Ø2000; 4a 30; 4b 30; separación 100; cubo Ø300; contacto interior Ø190; almas "300, 550, 735"; t alma 25; 12 nervios; t nervio 20; R nervio 880. Barras: R940; Ø70; 36; agujero Ø71; bisel 15. Interfaz: μ 0,20; r_ef 0,80; μ nominal 0,15; contaminado 0,25; seco 0,50; q adm 10 MPa. Accionamiento: émbolo Ø90; vástago Ø63; alivio 700; alarma 600; carrera 200; libre 36; L0 450; barra → ojal 250; X cilindro 1085; Lg 250; μg 0,15; ηc 0,95; μ pivote 0,20; H/W 0,05. Trinquete: punta 905; largo 245; ancho 85; alto 90; asiento R36; boca 1020; Fy 800. Pasador/ménsula/guía: Ø70; mejilla 40; luz 80; ojal 70; largo 280; altura eje 80; Fy 650; guía 40; empotramiento 10; altura 30; apoyo 150. Pivote/base: Ø150; buje 100; p adm 30; H buje/W 0,055; brazo 50; base 2400 × 2000 × 80. Materiales: Fy 345; FEXX 490; E 200 000; ν 0,30; Nd 2,0.

### 9.3 Exportes
- Planos emitidos: PDF diseño, PDF fabricación, ZIP DXF + STEP (armado en el navegador con JSZip desde `planos/src/*.txt`).
- Plano paramétrico TT300-B-P-01 (A1) en PDF y DXF (ZIP con LEEME.txt).
- Memoria de verificación A4 (≈ 8 páginas): resultado, hipótesis, parámetros, accionamiento, diagramas, verificaciones, FEA con imágenes, conclusión; texto en negro.
- Mapeo de caracteres para PDF (WinAnsi): μ→µ, ≤→<=, φ→phi, Δ→Delta, σ→sigma, ∫→int, etc.; DXF: Ø→%%c, °→%%d, ±→%%p, resto → \U+XXXX.

### 9.4 Pruebas realizadas
Playwright/Chromium: pestañas en claro y oscuro sin errores de consola (salvo fuentes bloqueadas en el entorno de prueba), descargas de los 3 exportes y del ZIP emitido, ancho 400 px sin scroll horizontal, cambio μ = 0,35 → veredicto "no vence", t_bot = 20 → FU sin cambio, N nervios 16 y 4a 40 → 3D y vistas regenerados, scroll independiente comprobado (aside 600 px, main 0; rueda sobre main mueve solo main).

---

## 10. Pendientes, observaciones abiertas e incertidumbres
| # | Tema | Estado / acción |
|---|---|---|
| 1 | **Revisión independiente (agente verificador, 30-10-2026)** | Entregada: aritmética OK (< 0,01 %); 3 hallazgos críticos y 8 mayores **sin resolver aún** — ver sección 11 y apéndice E |
| 2 | Lámina D-02 emitida usa 67/70 MPa en placas (estimación manual) | Actualizar con FEA (25,6 / 24,4 MPa) o dejar como envolvente conservadora y declararlo |
| 3 | Carrera sin margen (199,85 de 200 mm) | Especificar carrera 210 o recorrido libre 30 |
| 4 | Vástago dibujado Ø90 = émbolo Ø90 (inconsistente) | Confirmar con catálogo del cilindro; la herramienta usa Ø63 para pandeo (FU 0,37) |
| 5 | Pasador y trinquete con FU 0,86 | Aceptables; sensibles a Fy real (certificados QT) |
| 6 | Buje en caso accidental de un solo cilindro FU 0,99 | Depende del enclavamiento hidráulico; documentar en el manual |
| 7 | μ y r_ef de tablas genéricas | Confirmar en ensayo de aceptación (μ_real ≤ 0,20) |
| 8 | Presión en losa 0,90 MPa | Verificación de losa o mats por terceros |
| 9 | Diferencias Python vs web | A: 6357 vs 6362 mm²; masa disco 1922 (CadQuery) vs 1931 (fórmula); despreciables |
| 10 | Planos Rev. 0 reflejan solo valores por defecto | Si cambian parámetros, regenerar con `build300.py` o usar el plano paramétrico |
| 11 | Variante TT500-A/B (500 tf) | Entregada en Rev B; no actualizada a las mejoras de TT300-B (guía embutida, bisel 15, grasa) |

---

## 11. Revisión independiente (agente verificador) — hallazgos a resolver
Informe completo en el **apéndice E**; scripts del revisor en `tt300/app/tests/verificacion/` (indep.py, refine.js, signed.js, bench.js, pawl.js, calc_mod.js, fea_mod.js).

**Aritmética:** todos los valores por defecto coinciden con el re-cálculo independiente (< 0,01 %). Sin errores de unidades. calc.py (Python) está obsoleto: pandeo con Ø90 (5016 kN) y placas 67/70 MPa (franja simplemente apoyada).

| Sev. | Id | Hallazgo | Efecto | Acción recomendada |
|---|---|---|---|---|
| Crítico | C1 | Barra 4f y su soldadura calculadas con luz 100 (caras interiores). Si el bisel está en las caras exteriores, la luz real es 160 (holgura 0,5 mm: el agujero no apoya) | Luz 160: soldadura FU 1,31 (no 0,83), flexión barra FU 1,15 (no 0,52). Luz 130: soldadura FU 1,06 | Confirmar ubicación de la soldadura; soldar también caras interiores, especificar ajuste escariado, o aumentar garganta |
| Crítico | C2 | El carro va recto y la barra en arco: la barra se mueve 3,58 mm radialmente respecto del asiento, que tiene 1 mm de holgura (R36 vs r35) | Traba o contacto en el borde con fuerza lateral no verificada | Dar libertad radial al trinquete o agrandar/ranurar el asiento; verificar fuerza lateral |
| Crítico | C3 | Carrera: 199,85 requeridos vs 200 disponibles (0,15 mm) y la fila se aprueba | Sin tolerancia de montaje | Exigir margen mínimo; carrera 210 o libre 30 |
| Mayor | M1 | r_ef = 0,80 no es cota superior (deformación del cajón carga hacia el centro; el borde domina solo por planitud/cordones sin esmerilar) | r = 1,0 y μ 0,20: FS 1,13, 619 bar (sobre alarma); μ 0,25: FS 0,91, no gira | Exigir planitud y esmerilado de 4b; considerar r = R como caso límite; revisar alarma |
| Mayor | M2 | Flexión global del cajón mal modelada (voladizo 8,55 MPa vs ≈ 23 MPa de membrana axisimétrica; total ≈ 52 MPa, FU 0,25). No se verifica corte en nervios (48 MPa en r = 800, FU 0,35) ni soldaduras almas/nervios–planchas (≈ 1 kN/mm) | Pasa, pero fórmula incorrecta y chequeos faltantes | Reemplazar fórmula y agregar verificaciones |
| Mayor | M3 | Guía: σ = R/(e·L) ignora el volcamiento (≈ 5,3 kN·m por 150 mm) sobre 10 mm de empotramiento; el riel debe ir apernado. Lg = 250 no justificado (con 200, K +3,8 %, R +25 %) | Guía potencialmente no verificada | Apernar guía y verificar; justificar Lg |
| Mayor | M4 | Reacción del labio de la boca ≈ 1,8 F (796 kN, FEA) → aplastamiento ≈ 354 MPa, sobre 0,9 Fy si el carro es A572; carro no verificado. "vmFar" no converge (312/355/519 MPa con h 5/2,5/1,25) — singularidad, no reportar. σ en boca converge ≈ 305 MPa < 343 (vigas, conservador) | Carro posiblemente insuficiente | Verificar carro (material, aplastamiento) y eliminar vmFar |
| Mayor | M5 | Fatiga no evaluada (trinquete y pasador: 36 ciclos por vuelta) | — | Evaluar fatiga |
| Mayor | M6 | Plancha superior cargada uniforme y sin excentricidad; con e el pico es ≈ 1,75 veces (≈ 43 MPa). Apoyo real de la carga (patines, parrilla) no definido | — | Definir apoyo de la carga y modelarlo |
| Mayor | M7 | Presión en suelo con excentricidad biaxial: 0,988 MPa (FU 0,99), no 0,904; supone placa base rígida | — | Corregir fórmula; verificar losa |
| Mayor | M8 | Sin caso sísmico (NCh2369). El 5,5 % W lateral solo cubre fricción excéntrica (μ·N·e·(4/3)(Rc³−Ri³)/(Rc⁴−Ri⁴) = 4 % W con μ 0,2; 10 % en seco). Buje aguanta ≈ 0,15 W máx. | — | Agregar sismo y cargas laterales |
| Menor | m1 | Falta tope AISC F11.1 Mn ≤ 1,6·Fy·S (Mn de barra 6 % alto) | | |
| Menor | m2 | Ω_v = 1,50 fuera de alcance; G1 → 1,67 (FU corte 0,56 → 0,62) | | |
| Menor | m3 | Fuerzas en barras sumadas en valor absoluto (crecen con la malla 52,8 → 89,5 kN); con signo convergen a 46 kN | | |
| Menor | m4 | Picos en apoyos subestimados ≈ 12 % con malla por defecto (25,6 vs ≈ 29 MPa convergido) | | |
| Menor | m5–m9 | H inconsistente (0,05 y 0,055); sin sobrepresión de alivio ni impacto al tomar la barra; faltan aplastamiento en pasadores, BTH-1 3-3.3, ojal en carro y contrapresión; simetría de sector no validada para otras combinaciones N_bar/N_rib; masas fijas en código; calc.py obsoleto | | |

**Correcto según el revisor:** formulación MITC4 (amarre, interpolación Bathe-Dvorkin, J⁻¹, k = 5/6, penalización β·n) y equilibrio exacto; benchmarks propios (placa empotrada w 1,267e-3 vs 1,26e-3; anillo sectorial converge a Kirchhoff); tensiones del disco convergen a ≈ 28–29 MPa (inf.) y 27 MPa (sup.); brazo R·cos 5° correcto; K exacto para el Lg dado; los 2 cilindros forman par puro en cualquier ángulo (circuito en paralelo); μ estático correcto (cada carrera parte del reposo); criterio de verificar a la fuerza de calado correcto.

**Siguiente paso sugerido:** resolver C1–C3 en planos y herramienta (ubicación de soldadura y luz de la barra, libertad radial del trinquete, carrera), luego M1–M8, y re-emitir D-01/D-02/F-01/F-02/F-03 como Rev. 1.

---

## Apéndice A. Resultados de referencia (valores por defecto)
Salida de `node test_calc.js` y `node test_fea.js` el 30-10-2026. Sirve para comprobar que una modificación no altera resultados sin querer.

```text
mass 1930.8 N 2960.9 r_u 0.6722 a 936.42 K 1.2403 Fmax 445.3
Nominal – grasa grafitada limpia              0.15 0.672 300.7 160.6 199.2 313 2.24
DISEÑO – μ límite sup., carga al borde        0.2 0.800 476.0 254.1 315.2 495 1.41
Contaminado – arena / película degradada      0.25 0.800 594.4 317.4 393.6 619 1.13
Sin lubricación (acero seco)                  0.5 0.672 997.3 532.5 660.5 1038 0.67
mumax 0.283 qavg 1.046 qmax 1.667 qtop 1.610 ground 0.623 0.904
bot nodes 1392 ms 216 vmMax 25.6 vmC 25.5 at [ '405.8', '0.5' ] w 0.0191 ring N/mm [ '146', '211', '244' ] bars kN [ '41.2', '52.8', '41.2' ] rib 125.5 hub 3.8 F 426.7 R 426.7
top nodes 1392 ms 152 vmMax 24.4 vmC 24.3 at [ '405.8', '0.5' ] w 0.0160 ring N/mm [ '141', '211', '188' ] bars kN [ '1.2', '1.8', '1.2' ] rib 100.3 hub 3.7 F 260.2 R 260.2
pawl ms 92 vmMax 942 mouth 297 far 355 beam 343 dmax 0.790 loads 47 sumFy -445321 sumFx 0
Accionamiento  Fuerza de diseño vs capacidad del cilindro          315.21    445.32 0.71
Accionamiento  Presión de diseño vs alarma                         495.47    600.00 0.83
Accionamiento  Carrera requerida (libre + útil)                    199.85    200.00 1.00
Interfaz       Presión de contacto máx. (e)                          1.67     10.00 0.17
Disco (FEA)    Plancha inf. 4b – σvm máx. (contacto q_max)          25.59    207.00 0.12
Disco (FEA)    Plancha sup. 4a – σvm máx. (carga en parrilla)       24.36    207.00 0.12
Disco (FEA)    Almas 4d – compresión por reacción de línea           9.74    207.00 0.05
Disco (FEA)    Barra 4f – compresión axial (columna)                13.73    207.00 0.07
Disco          Flexión global del cajón en el anillo exterior (voladizo)      8.55    207.00 0.04
Barra 4f       Flexión (rotulada, F calado)                          6.12     11.81 0.52
Barra 4f       Corte                                                77.14    138.00 0.56
Barra 4f       Soldadura bisel 15 (E = 12)                         121.91    147.00 0.83
Barra 4f       Aplastamiento en agujero de plancha                 106.03    310.50 0.34
Trinquete      Flexión en boca del carro (teoría de vigas)         343.42    400.00 0.86
Trinquete      Flexión en boca (FEA tensión plana)                 297.17    400.00 0.74
Guía 22        Aplastamiento en ranura                             176.44    310.50 0.57
Guía 22        Flexión en raíz                                       3.97     12.40 0.32
Ménsula 2      Flexión de mejillas en la base                       34.08    207.00 0.16
Pasador 12     Flexión (horquilla)                                 281.02    325.00 0.86
Pasador 12     Corte doble                                          57.86    187.64 0.31
Pivote         Presión en buje (H)                                  10.79     30.00 0.36
Pivote         Flexión del pivote                                   24.42    325.00 0.08
Cilindro       Pandeo del vástago (rótulas)                        445.32   1204.24 0.37
Apoyo          Presión bajo placa base (máx.)                        0.90      1.00 0.90
w FE 2.2178 Navier 2.2168 ms 85
Mx center elem 0 max M 476.1 theory 479
Fapplied 10000.0 Rsum -10000.0
tip -1.9970 theory -2.0(+shear ~0.026)
max sx 55.3 theory 60 at root (elem center ~ 59)
```

## Apéndice B. Código fuente completo de la herramienta web (`tt300/app`)
Orden de ensamblado en `build.py`: fea → calc → diag → export → geo → ui, insertados en `shell.html`.

### tt300/app/fea.js
`tt300/app/fea.js` — 241 líneas

```javascript
/* FEA engine: banded Cholesky, Mindlin plate MITC4, plane-stress Q4. Units N, mm, MPa. */
const FEA = (() => {
  const GP = [-1 / Math.sqrt(3), 1 / Math.sqrt(3)];
  const XI = [-1, 1, 1, -1], ETA = [-1, -1, 1, 1];

  function Band(n, bw) { this.n = n; this.bw = bw; this.W = bw + 1; this.a = new Float64Array(n * (bw + 1)); }
  Band.prototype.add = function (i, j, v) {
    if (j < i) { const t = i; i = j; j = t; }
    const d = j - i;
    if (d > this.bw) throw new Error("bandwidth " + d + ">" + this.bw);
    this.a[i * this.W + d] += v;
  };
  Band.prototype.diag = function (i) { return this.a[i * this.W]; };

  function cholSolve(B, f) {
    const n = B.n, w = B.bw, W = B.W, a = B.a;
    for (let i = 0; i < n; i++) {
      let s = a[i * W];
      for (let k = Math.max(0, i - w); k < i; k++) { const u = a[k * W + (i - k)]; s -= u * u; }
      if (!(s > 0)) throw new Error("Matriz no definida positiva en GDL " + i + " (modelo inestable)");
      const d = Math.sqrt(s); a[i * W] = d;
      const jmax = Math.min(n - 1, i + w);
      for (let j = i + 1; j <= jmax; j++) {
        let t = a[i * W + (j - i)];
        for (let k = Math.max(0, j - w); k < i; k++) t -= a[k * W + (i - k)] * a[k * W + (j - k)];
        a[i * W + (j - i)] = t / d;
      }
    }
    const y = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      let s = f[i];
      for (let k = Math.max(0, i - w); k < i; k++) s -= a[k * W + (i - k)] * y[k];
      y[i] = s / a[i * W];
    }
    const x = new Float64Array(n);
    for (let i = n - 1; i >= 0; i--) {
      let s = y[i];
      const jmax = Math.min(n - 1, i + w);
      for (let j = i + 1; j <= jmax; j++) s -= a[i * W + (j - i)] * x[j];
      x[i] = s / a[i * W];
    }
    return x;
  }

  function shape(xi, eta) {
    const N = [], dxi = [], deta = [];
    for (let i = 0; i < 4; i++) {
      N.push(0.25 * (1 + xi * XI[i]) * (1 + eta * ETA[i]));
      dxi.push(0.25 * XI[i] * (1 + eta * ETA[i]));
      deta.push(0.25 * ETA[i] * (1 + xi * XI[i]));
    }
    return { N, dxi, deta };
  }
  function jac(X, Y, s) {
    let xx = 0, xy = 0, yx = 0, yy = 0;
    for (let i = 0; i < 4; i++) { xx += s.dxi[i] * X[i]; xy += s.dxi[i] * Y[i]; yx += s.deta[i] * X[i]; yy += s.deta[i] * Y[i]; }
    const det = xx * yy - xy * yx;
    const inv = [[yy / det, -xy / det], [-yx / det, xx / det]];
    const dx = [], dy = [];
    for (let i = 0; i < 4; i++) { dx.push(inv[0][0] * s.dxi[i] + inv[0][1] * s.deta[i]); dy.push(inv[1][0] * s.dxi[i] + inv[1][1] * s.deta[i]); }
    return { det, inv, dx, dy, J: [[xx, xy], [yx, yy]] };
  }
  function addBtDB(K, B, D, f, nd) {
    const nr = B.length;
    const DB = [];
    for (let r = 0; r < nr; r++) { DB.push(new Float64Array(nd)); for (let c = 0; c < nd; c++) { let s = 0; for (let k = 0; k < nr; k++) s += D[r][k] * B[k][c]; DB[r][c] = s; } }
    for (let i = 0; i < nd; i++) for (let j = 0; j < nd; j++) { let s = 0; for (let r = 0; r < nr; r++) s += B[r][i] * DB[r][j]; K[i][j] += s * f; }
  }
  const zeros = (n) => Array.from({ length: n }, () => new Float64Array(n));

  /* ---------------- Mindlin plate (MITC4). DOF/node: w, bx, by ---------------- */
  function plateDb(t, E, nu) {
    const D = E * t ** 3 / (12 * (1 - nu * nu));
    return [[D, nu * D, 0], [nu * D, D, 0], [0, 0, D * (1 - nu) / 2]];
  }
  function plateBb(jj) {
    const B = [new Float64Array(12), new Float64Array(12), new Float64Array(12)];
    for (let i = 0; i < 4; i++) {
      B[0][3 * i + 1] = jj.dx[i];
      B[1][3 * i + 2] = jj.dy[i];
      B[2][3 * i + 1] = jj.dy[i]; B[2][3 * i + 2] = jj.dx[i];
    }
    return B;
  }
  function plateKe(X, Y, t, E, nu) {
    const Db = plateDb(t, E, nu);
    const ks = 5 / 6 * E / (2 * (1 + nu)) * t;
    const K = zeros(12);
    for (const xi of GP) for (const eta of GP) {
      const s = shape(xi, eta), jj = jac(X, Y, s);
      addBtDB(K, plateBb(jj), Db, jj.det, 12);
    }
    const row = (xi, eta, dir) => {
      const s = shape(xi, eta);
      const d = dir === 0 ? s.dxi : s.deta;
      let tx = 0, ty = 0;
      for (let i = 0; i < 4; i++) { tx += d[i] * X[i]; ty += d[i] * Y[i]; }
      const r = new Float64Array(12);
      for (let i = 0; i < 4; i++) { r[3 * i] = d[i]; r[3 * i + 1] = s.N[i] * tx; r[3 * i + 2] = s.N[i] * ty; }
      return r;
    };
    const rA = row(0, 1, 0), rC = row(0, -1, 0), rB = row(-1, 0, 1), rD = row(1, 0, 1);
    const Ds = [[ks, 0], [0, ks]];
    for (const xi of GP) for (const eta of GP) {
      const s = shape(xi, eta), jj = jac(X, Y, s);
      const gx = new Float64Array(12), ge = new Float64Array(12);
      for (let c = 0; c < 12; c++) {
        gx[c] = 0.5 * (1 + eta) * rA[c] + 0.5 * (1 - eta) * rC[c];
        ge[c] = 0.5 * (1 + xi) * rD[c] + 0.5 * (1 - xi) * rB[c];
      }
      const Bs = [new Float64Array(12), new Float64Array(12)];
      for (let c = 0; c < 12; c++) {
        Bs[0][c] = jj.inv[0][0] * gx[c] + jj.inv[0][1] * ge[c];
        Bs[1][c] = jj.inv[1][0] * gx[c] + jj.inv[1][1] * ge[c];
      }
      addBtDB(K, Bs, Ds, jj.det, 12);
    }
    return K;
  }

  function bandwidth(elems, ndof) {
    let bw = 0;
    for (const e of elems) { const mn = Math.min(...e), mx = Math.max(...e); bw = Math.max(bw, (mx - mn + 1) * ndof - 1); }
    return bw;
  }

  /* model: {nodes:[[x,y]], elems:[[n1..n4]], t,E,nu, q:Float64Array per elem (MPa, +z),
     wFix:[node], clamp:[node], betaN:[[node,nx,ny]]} */
  function plate(m) {
    const nn = m.nodes.length, n = 3 * nn;
    const bw = bandwidth(m.elems, 3);
    const K = new Band(n, bw), f = new Float64Array(n);
    let maxd = 0;
    for (let e = 0; e < m.elems.length; e++) {
      const en = m.elems[e];
      const X = en.map((k) => m.nodes[k][0]), Y = en.map((k) => m.nodes[k][1]);
      const ke = plateKe(X, Y, m.t, m.E, m.nu);
      const dofs = [];
      for (const k of en) dofs.push(3 * k, 3 * k + 1, 3 * k + 2);
      for (let i = 0; i < 12; i++) for (let j = i; j < 12; j++) {
        const gi = dofs[i], gj = dofs[j];
        if (gi === gj) K.add(gi, gj, ke[i][j]);
        else if (gi < gj) K.add(gi, gj, ke[i][j]);
        else K.add(gj, gi, ke[i][j]);
        if (i === j) maxd = Math.max(maxd, ke[i][i]);
      }
      const q = m.q[e];
      if (q) for (const xi of GP) for (const eta of GP) {
        const s = shape(xi, eta), jj = jac(X, Y, s);
        for (let i = 0; i < 4; i++) f[3 * en[i]] += s.N[i] * q * jj.det;
      }
    }
    // symmetric fill: ensure lower duplicates added only once (handled by i<=j loop with symmetric storage)
    const kp = maxd * 1e6;
    const used = new Uint8Array(nn);
    for (const en of m.elems) for (const k of en) used[k] = 1;
    for (let k = 0; k < nn; k++) if (!used[k]) { K.add(3 * k, 3 * k, 1); K.add(3 * k + 1, 3 * k + 1, 1); K.add(3 * k + 2, 3 * k + 2, 1); }
    for (const k of m.wFix) K.add(3 * k, 3 * k, kp);
    for (const k of (m.clamp || [])) { K.add(3 * k, 3 * k, kp); K.add(3 * k + 1, 3 * k + 1, kp); K.add(3 * k + 2, 3 * k + 2, kp); }
    for (const [k, nx, ny] of (m.betaN || [])) {
      K.add(3 * k + 1, 3 * k + 1, kp * nx * nx); K.add(3 * k + 2, 3 * k + 2, kp * ny * ny); K.add(3 * k + 1, 3 * k + 2, kp * nx * ny);
    }
    const u = cholSolve(K, f);
    const w = new Float64Array(nn);
    for (let k = 0; k < nn; k++) w[k] = u[3 * k];
    const reac = new Float64Array(nn);
    const fixed = new Set([...m.wFix, ...(m.clamp || [])]);
    for (const k of fixed) reac[k] = -kp * u[3 * k];
    const Db = plateDb(m.t, m.E, m.nu);
    const el = [];
    const pts = [[0, 0]].concat(GP.flatMap((a) => GP.map((b) => [a, b])));
    for (let e = 0; e < m.elems.length; e++) {
      const en = m.elems[e];
      const X = en.map((k) => m.nodes[k][0]), Y = en.map((k) => m.nodes[k][1]);
      const ue = []; for (const k of en) ue.push(u[3 * k], u[3 * k + 1], u[3 * k + 2]);
      let vmc = 0, vmx = 0, Mc = null;
      for (let p = 0; p < pts.length; p++) {
        const s = shape(pts[p][0], pts[p][1]), jj = jac(X, Y, s), B = plateBb(jj);
        const kap = [0, 0, 0];
        for (let r = 0; r < 3; r++) for (let c = 0; c < 12; c++) kap[r] += B[r][c] * ue[c];
        const M = [0, 0, 0];
        for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) M[r] += Db[r][c] * kap[c];
        const k6 = 6 / (m.t * m.t);
        const sx = M[0] * k6, sy = M[1] * k6, txy = M[2] * k6;
        const vm = Math.sqrt(sx * sx - sx * sy + sy * sy + 3 * txy * txy);
        if (p === 0) { vmc = vm; Mc = M; } else vmx = Math.max(vmx, vm);
      }
      el.push({ vm: vmc, vmGauss: vmx, M: Mc });
    }
    let F = 0; for (let k = 0; k < nn; k++) F += f[3 * k];
    let R = 0; for (const k of fixed) R += reac[k];
    return { w, reac, el, Fapplied: F, Rsum: R, ndof: n, bw };
  }

  /* ---------------- Plane stress Q4. DOF/node: ux, uy ---------------- */
  function psD(E, nu) { const c = E / (1 - nu * nu); return [[c, c * nu, 0], [c * nu, c, 0], [0, 0, c * (1 - nu) / 2]]; }
  function psB(jj) {
    const B = [new Float64Array(8), new Float64Array(8), new Float64Array(8)];
    for (let i = 0; i < 4; i++) { B[0][2 * i] = jj.dx[i]; B[1][2 * i + 1] = jj.dy[i]; B[2][2 * i] = jj.dy[i]; B[2][2 * i + 1] = jj.dx[i]; }
    return B;
  }
  /* m: {nodes, elems, t, E, nu, fix:[[node,dof]], loads:[[node,fx,fy]]} */
  function planeStress(m) {
    const nn = m.nodes.length, n = 2 * nn, bw = bandwidth(m.elems, 2);
    const K = new Band(n, bw), f = new Float64Array(n), D = psD(m.E, m.nu);
    let maxd = 0;
    for (const en of m.elems) {
      const X = en.map((k) => m.nodes[k][0]), Y = en.map((k) => m.nodes[k][1]);
      const ke = zeros(8);
      for (const xi of GP) for (const eta of GP) { const s = shape(xi, eta), jj = jac(X, Y, s); addBtDB(ke, psB(jj), D, jj.det * m.t, 8); }
      const dofs = []; for (const k of en) dofs.push(2 * k, 2 * k + 1);
      for (let i = 0; i < 8; i++) for (let j = i; j < 8; j++) K.add(dofs[i], dofs[j], ke[i][j]);
      for (let i = 0; i < 8; i++) maxd = Math.max(maxd, ke[i][i]);
    }
    const used = new Uint8Array(nn);
    for (const en of m.elems) for (const k of en) used[k] = 1;
    for (let k = 0; k < nn; k++) if (!used[k]) { K.add(2 * k, 2 * k, 1); K.add(2 * k + 1, 2 * k + 1, 1); }
    const kp = maxd * 1e6;
    for (const [k, d] of m.fix) K.add(2 * k + d, 2 * k + d, kp);
    for (const [k, fx, fy] of m.loads) { f[2 * k] += fx; f[2 * k + 1] += fy; }
    const u = cholSolve(K, f);
    const el = [];
    for (const en of m.elems) {
      const X = en.map((k) => m.nodes[k][0]), Y = en.map((k) => m.nodes[k][1]);
      const ue = []; for (const k of en) ue.push(u[2 * k], u[2 * k + 1]);
      const s = shape(0, 0), jj = jac(X, Y, s), B = psB(jj);
      const eps = [0, 0, 0];
      for (let r = 0; r < 3; r++) for (let c = 0; c < 8; c++) eps[r] += B[r][c] * ue[c];
      const sg = [0, 0, 0];
      for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) sg[r] += D[r][c] * eps[c];
      const vm = Math.sqrt(sg[0] ** 2 - sg[0] * sg[1] + sg[1] ** 2 + 3 * sg[2] ** 2);
      el.push({ sx: sg[0], sy: sg[1], txy: sg[2], vm });
    }
    const reac = [];
    for (const [k, d] of m.fix) reac.push([k, d, -kp * u[2 * k + d]]);
    return { u, el, reac, ndof: n, bw };
  }

  return { plate, planeStress, cholSolve, Band };
})();
if (typeof module !== "undefined") module.exports = FEA;
```

### tt300/app/calc.js
`tt300/app/calc.js` — 390 líneas

```javascript
/* Modelo paramétrico TT300-B: parámetros, cálculo del accionamiento, verificaciones y modelos FEA. */
const G = 9.80665, RHO = 7.85e-6;

const PARAM_GROUPS = [
  { id: "carga", t: "Carga", items: [
    ["W_tf", "Capacidad nominal W", "tf", 300, 10],
    ["e", "Excentricidad del CG", "mm", 150, 10],
    ["phi_d", "Factor dinámico φd", "–", 1.10, 0.05],
    ["D_load", "Zona de carga (parrilla)", "mm Ø", 1600, 50],
  ]},
  { id: "disco", t: "Disco cajón", items: [
    ["D_disc", "Diámetro del disco", "mm", 2000, 50],
    ["t_top", "Plancha superior 4a", "mm", 30, 2],
    ["t_bot", "Plancha inferior 4b", "mm", 30, 2],
    ["gap", "Separación entre planchas", "mm", 100, 5],
    ["D_hub", "Cubo 4c, Ø exterior", "mm", 300, 10],
    ["D_bore", "Buje / contacto interior Ø", "mm", 190, 5],
    ["rings", "Almas 4d, radios (coma)", "mm", "300, 550, 735", null],
    ["t_ring", "Espesor almas 4d", "mm", 25, 1],
    ["N_rib", "N° nervios radiales 4e", "un", 12, 1],
    ["t_rib", "Espesor nervios 4e", "mm", 20, 1],
    ["R_rib", "Radio final nervios", "mm", 880, 10],
  ]},
  { id: "barras", t: "Barras de empuje 4f", items: [
    ["R_bar", "Radio de barras", "mm", 940, 5],
    ["D_bar", "Diámetro barra", "mm", 70, 2],
    ["N_bar", "N° de barras", "un", 36, 1],
    ["D_hole", "Agujero en planchas Ø", "mm", 71, 1],
    ["weld_S", "Bisel soldadura barra S", "mm", 15, 1],
  ]},
  { id: "friccion", t: "Interfaz de giro", items: [
    ["mu", "μ estático de diseño", "–", 0.20, 0.01],
    ["r_eff", "Radio efectivo de diseño", "m", 0.80, 0.01],
    ["mu_nom", "μ nominal (grasa limpia)", "–", 0.15, 0.01],
    ["mu_cont", "μ contaminado", "–", 0.25, 0.01],
    ["mu_dry", "μ acero seco", "–", 0.50, 0.05],
    ["q_lim", "Presión admisible contacto", "MPa", 10, 0.5],
  ]},
  { id: "act", t: "Accionamiento", items: [
    ["D_piston", "Ø émbolo (área efectiva)", "mm", 90, 1],
    ["D_rod", "Ø vástago (pandeo)", "mm", 63, 1],
    ["p_relief", "Presión de alivio", "bar", 700, 10],
    ["p_alarm", "Presión de alarma", "bar", 600, 10],
    ["stroke", "Carrera cilindro", "mm", 200, 5],
    ["free", "Recorrido libre", "mm", 36, 1],
    ["L0", "L0 entre ojales (retraído)", "mm", 450, 5],
    ["eye_off", "Barra → ojal vástago", "mm", 250, 5],
    ["X_cyl", "Eje cilindro / guía (x)", "mm", 1085, 5],
    ["Lg", "Separación reacciones guía", "mm", 250, 5],
    ["mu_g", "μ carro/guía", "–", 0.15, 0.01],
    ["eta_c", "Rendimiento sellos ηc", "–", 0.95, 0.01],
    ["mu_piv", "μ buje pivote", "–", 0.20, 0.01],
    ["H_frac", "Fuerza lateral pivote / W", "–", 0.05, 0.005],
  ]},
  { id: "trinq", t: "Trinquete y carro", items: [
    ["pawl_tip", "Punta trinquete (x)", "mm", 905, 5],
    ["pawl_L", "Largo trinquete", "mm", 245, 5],
    ["pawl_b", "Ancho trinquete (flexión)", "mm", 85, 1],
    ["pawl_h", "Alto trinquete", "mm", 90, 1],
    ["seat_R", "Radio asiento", "mm", 36, 1],
    ["shoe_x0", "Boca del carro (x)", "mm", 1020, 5],
    ["Fy_pawl", "Fy trinquete (34CrNiMo6+QT)", "MPa", 800, 10],
  ]},
  { id: "pasador", t: "Pasador, ménsula y guía", items: [
    ["D_pin", "Ø pasador", "mm", 70, 1],
    ["t_cheek", "Espesor mejilla", "mm", 40, 1],
    ["gap_cheek", "Luz entre mejillas", "mm", 80, 1],
    ["w_eye", "Ancho ojal", "mm", 70, 1],
    ["L_cheek", "Largo mejilla", "mm", 280, 5],
    ["h_axis", "Altura eje sobre base", "mm", 80, 1],
    ["Fy_pin", "Fy pasador/pivote (42CrMo4+QT)", "MPa", 650, 10],
    ["rail_w", "Ancho guía", "mm", 40, 1],
    ["rail_embed", "Empotramiento guía en ranura", "mm", 10, 1],
    ["rail_h", "Altura libre guía", "mm", 30, 1],
    ["L_brg", "Largo de apoyo por reacción", "mm", 150, 5],
  ]},
  { id: "pivote", t: "Pivote, buje y base", items: [
    ["D_piv", "Ø pivote", "mm", 150, 5],
    ["L_bush", "Largo buje", "mm", 100, 5],
    ["p_bush", "Presión admisible buje", "MPa", 30, 1],
    ["H_bush", "Fuerza lateral buje / W", "–", 0.055, 0.005],
    ["lev_piv", "Brazo flexión pivote", "mm", 50, 5],
    ["BX", "Placa base X", "mm", 2400, 50],
    ["BY", "Placa base Y", "mm", 2000, 50],
    ["t_base", "Espesor placa base", "mm", 80, 5],
  ]},
  { id: "mat", t: "Materiales y factores", items: [
    ["Fy", "Fy planchas (A572 Gr.50)", "MPa", 345, 5],
    ["FEXX", "FEXX electrodo", "MPa", 490, 10],
    ["E", "Módulo E", "MPa", 200000, 1000],
    ["nu", "Poisson ν", "–", 0.3, 0.01],
    ["Nd", "Factor Nd (ASME BTH-1)", "–", 2.0, 0.1],
  ]},
];

function defaults() {
  const P = {};
  for (const g of PARAM_GROUPS) for (const it of g.items) P[it[0]] = it[3];
  return P;
}
function parseRings(s) {
  return String(s).split(/[,; ]+/).map(Number).filter((x) => isFinite(x) && x > 0).sort((a, b) => a - b);
}

function discMass(P) {
  const TD = P.t_top + P.t_bot + P.gap, Rd = P.D_disc / 2, rh = P.D_hub / 2;
  const rings = parseRings(P.rings);
  const plateA = Math.PI * (Rd * Rd - rh * rh) - P.N_bar * Math.PI * (P.D_hole / 2) ** 2;
  const m = {};
  m.top = plateA * P.t_top * RHO;
  m.bot = plateA * P.t_bot * RHO;
  m.hub = RHO * Math.PI / 4 * (P.D_hub ** 2 * TD - P.D_bore ** 2 * P.L_bush - 160 ** 2 * Math.max(0, TD - P.L_bush) - (260 ** 2 - 160 ** 2) * 25);
  m.rings = rings.reduce((s, r) => s + 2 * Math.PI * r * P.t_ring * P.gap * RHO, 0);
  const crossed = rings.filter((r) => r < P.R_rib).length * P.t_ring;
  m.ribs = P.N_rib * P.t_rib * P.gap * Math.max(0, P.R_rib - rh - crossed) * RHO;
  m.bars = P.N_bar * Math.PI * P.D_bar ** 2 / 4 * TD * RHO;
  m.bush = 8.1;
  m.total = m.top + m.bot + m.hub + m.rings + m.ribs + m.bars + m.bush;
  return m;
}

function compute(P) {
  const R = { P };
  R.W = P.W_tf * G;                                   // kN
  R.TD = P.t_top + P.t_bot + P.gap;
  R.mass = discMass(P);
  R.Wd = R.mass.total * G / 1000;
  R.N = R.W + R.Wd;
  R.ND = P.phi_d * R.W + R.Wd;
  const Rc = P.D_disc / 2, Ri = P.D_bore / 2;
  R.Ac = Math.PI * (Rc * Rc - Ri * Ri);
  R.r_u = 2 / 3 * (Rc ** 3 - Ri ** 3) / (Rc ** 2 - Ri ** 2) / 1000;
  R.r_max = P.R_bar / 1000;
  R.r_eff = P.r_eff;
  R.th = Math.PI / P.N_bar;                           // media separación angular (rad)
  R.a = P.R_bar * Math.cos(R.th);                     // mm, brazo mínimo
  R.useful = 2 * P.R_bar * Math.sin(R.th);
  R.strokeReq = P.free + R.useful;
  R.Delta = P.X_cyl - R.a;
  R.Kguide = 1 + 2 * P.mu_g * R.Delta / P.Lg;
  R.K = R.Kguide / P.eta_c;
  R.A = Math.PI * P.D_piston ** 2 / 4;                 // mm²
  R.Fmax = R.A * P.p_relief / 10 / 1000;               // kN
  R.Falarm = R.A * P.p_alarm / 10 / 1000;
  R.Tpiv = P.mu_piv * P.H_frac * R.W * (P.D_piv / 2 / 1000);
  R.Ybrk = P.R_bar * Math.sin(R.th) + P.eye_off + P.L0 + P.free;
  const cs = (mu, r) => {
    const Tf = mu * R.N * r, T = Tf + R.Tpiv, Fb = T / (2 * R.a / 1000), Fc = R.K * Fb;
    const p = Fc * 1e3 / R.A * 10;
    return { mu, r, Tf, T, Fb, Fc, p, FS: R.Fmax / Fc, tf: Fc / G };
  };
  R.cs = cs;
  R.cases = [
    Object.assign(cs(P.mu_nom, R.r_u), { name: "Nominal – grasa grafitada limpia", key: "nom" }),
    Object.assign(cs(P.mu, R.r_eff), { name: "DISEÑO – μ límite sup., carga al borde", key: "dis" }),
    Object.assign(cs(P.mu_cont, R.r_eff), { name: "Contaminado – arena / película degradada", key: "con" }),
    Object.assign(cs(P.mu_dry, R.r_u), { name: "Sin lubricación (acero seco)", key: "dry" }),
  ];
  R.d = R.cases[1];
  R.muMax = (r, p) => ((R.A * p / 10 / 1000) / R.K * (2 * R.a / 1000) - R.Tpiv) / (R.N * r);
  // curva por carrera
  R.stroke = [];
  for (let i = 0; i <= 40; i++) {
    const t = -R.th + 2 * R.th * i / 40;
    const at = P.R_bar * Math.cos(t), Dt = P.X_cyl - at, Kt = (1 + 2 * P.mu_g * Dt / P.Lg) / P.eta_c;
    const s = P.free + P.R_bar * (Math.sin(t) + Math.sin(R.th));
    const row = { t: t * 180 / Math.PI, s };
    for (const c of R.cases.slice(0, 3)) { const Fb = c.T / (2 * at / 1000); row[c.key] = Kt * Fb; }
    R.stroke.push(row);
  }
  // desglose de la fuerza de diseño
  const d = R.d, a2 = 2 * R.a / 1000;
  R.breakdown = [
    ["Fricción interfaz μ·N·r", d.Tf / a2],
    ["Buje del pivote", R.Tpiv / a2],
    ["Fricción carro/guía", d.Fb * (R.Kguide - 1)],
    ["Sellos del cilindro", d.Fc - d.Fb * R.Kguide],
  ];
  // contacto
  R.q_avg = R.ND * 1e3 / R.Ac;
  R.q_max = R.q_avg * (1 + 4 * P.e * Rc / (Rc * Rc + Ri * Ri));
  R.q_top = P.phi_d * R.W * 1e3 / (Math.PI * (P.D_load / 2) ** 2);
  // suelo
  R.Wtot = R.W + (R.mass.total + 3070) * G / 1000;   // + base y accesorios ≈ 3,07 t
  R.g_avg = R.Wtot * 1e3 / (P.BX * P.BY);
  R.g_max = R.g_avg * (1 + 6 * P.e / P.BY);
  return R;
}

/* ---------- verificaciones (requieren resultados FEA opcionales) ---------- */
function verifs(R, fea) {
  const P = R.P, F = R.Fmax, Fy = P.Fy, rows = [];
  const add = (grp, el, dem, cap, unit, ref, formula, note) => rows.push({ grp, el, dem, cap, unit, fu: dem / cap, ref, formula, note });
  // accionamiento
  add("Accionamiento", "Fuerza de diseño vs capacidad del cilindro", R.d.Fc, R.Fmax, "kN", "Ec. (5) / 700 bar", "F_cil = K·T/(2a)  ≤  A·p_alivio");
  add("Accionamiento", "Presión de diseño vs alarma", R.d.p, P.p_alarm, "bar", "Criterio operación", "p = F_cil / A  ≤  p_alarma");
  rows[rows.length - 1].kind = "pass";
  add("Accionamiento", "Carrera requerida (libre + útil)", R.strokeReq, P.stroke, "mm", "Cinemática", "s = libre + 2·R_b·sin(180°/N_b)");
  rows[rows.length - 1].kind = "pass";
  // interfaz
  add("Interfaz", "Presión de contacto máx. (e)", R.q_max, P.q_lim, "MPa", "Criterio acero/acero lubricado", "q = N_D/A·(1 + 4eR/(R²+r²))");
  // disco (FEA)
  if (fea && fea.bot) {
    add("Disco (FEA)", "Plancha inf. 4b – σvm máx. (contacto q_max)", fea.bot.vmMax, 0.6 * Fy, "MPa", "AISC 360-22 F11 (elástico 0,6Fy)", "FEA Mindlin MITC4, sector 360°/N_nerv");
    add("Disco (FEA)", "Plancha sup. 4a – σvm máx. (carga en parrilla)", fea.top.vmMax, 0.6 * Fy, "MPa", "AISC 360-22 F11 (elástico 0,6Fy)", "FEA Mindlin MITC4, q = φd·W/A_parrilla");
    const rw = Math.max(fea.bot.ringMax, fea.top.ringMax);
    add("Disco (FEA)", "Almas 4d – compresión por reacción de línea", rw / P.t_ring, 0.6 * Fy, "MPa", "AISC 360-22 J10.2 / E3", "σ = r_línea / t_alma");
    const rb = Math.max(fea.bot.barMax, fea.top.barMax) * 1e3;
    add("Disco (FEA)", "Barra 4f – compresión axial (columna)", rb / (Math.PI * P.D_bar ** 2 / 4), 0.6 * Fy, "MPa", "AISC 360-22 E3", "σ = R_barra / A_barra");
  }
  // flexión global del cajón: anillo exterior fuera de la zona de carga
  const ov = Math.max(0, P.D_disc / 2 - P.D_load / 2), lever = R.TD - (P.t_top + P.t_bot) / 2;
  const Mov = R.q_max * ov * ov / 2, Sov = Math.min(P.t_top, P.t_bot) * lever;
  add("Disco", "Flexión global del cajón en el anillo exterior (voladizo)", Mov / Sov, 0.6 * Fy, "MPa", "AISC 360-22 F11 (elástico)", "M = q_max·(R − R_carga)²/2; S = t·(TD − t)");
  // barra 4f
  const L = P.gap, c = Math.min(P.pawl_h, P.gap), d = P.D_bar;
  const Mss = F / 4 * (L - c / 2) / 1e3, Mfe = F * (3 * L * L - c * c) / (24 * L) / 1e3;
  const Mn = Fy * d ** 3 / 6 / 1.67 / 1e6;
  add("Barra 4f", "Flexión (rotulada, F calado)", Mss, Mn, "kN·m", "AISC 360-22 F11.1, Ω = 1,67", "M = F/4·(L − c/2); Mn = Fy·d³/6");
  const tau = 4 * (F / 2) * 1e3 / (3 * Math.PI * d * d / 4);
  add("Barra 4f", "Corte", tau, 0.6 * Fy / 1.5, "MPa", "AISC 360-22 G1, Ω = 1,50", "τ = 4V/(3A), V = F/2");
  const Ew = P.weld_S - 3, tv = (F / 2) * 1e3 / (Math.PI * d * Ew), tm = Mfe * 1e6 / (Math.PI * (d / 2) ** 2 * Ew);
  add("Barra 4f", `Soldadura bisel ${P.weld_S} (E = ${Ew})`, Math.hypot(tv, tm), 0.6 * P.FEXX / 2, "MPa", "AISC 360-22 J2.5, Ω = 2,0", "√(τV² + τM²); M empotrada = F(3L²−c²)/(24L)");
  add("Barra 4f", "Aplastamiento en agujero de plancha", (F / 2) * 1e3 / (Math.min(P.t_top, P.t_bot) * d), 0.9 * Fy, "MPa", "AISC 360-22 J7, Ω = 2,0", "σ = (F/2)/(t·d)");
  // trinquete
  const lev = P.shoe_x0 - R.a;
  const sp = F * lev * 1e3 / (P.pawl_h * P.pawl_b ** 2 / 6);
  add("Trinquete", "Flexión en boca del carro (teoría de vigas)", sp, P.Fy_pawl / P.Nd, "MPa", "ASME BTH-1 (Fy/Nd)", "σ = F·(x_boca − a)/(h·b²/6)");
  if (fea && fea.pawl) add("Trinquete", "Flexión en boca (FEA tensión plana)", fea.pawl.vmMouth, P.Fy_pawl / P.Nd, "MPa", "ASME BTH-1 (Fy/Nd)", "FEA Q4, h_malla 2,5 mm");
  // guía
  const Rg = F * R.Delta / P.Lg;
  add("Guía 22", "Aplastamiento en ranura", Rg * 1e3 / (P.rail_embed * P.L_brg), 0.9 * Fy, "MPa", "AISC 360-22 J7, Ω = 2,0", "R = F·Δ/Lg; σ = R/(e·L)");
  const Mg = Rg * P.rail_h / 2 / 1e3, Mng = Fy * P.L_brg * P.rail_w ** 2 / 4 / 1.67 / 1e6;
  add("Guía 22", "Flexión en raíz", Mg, Mng, "kN·m", "AISC 360-22 F11.1, Ω = 1,67", "M = R·h/2");
  // ménsula y pasador
  add("Ménsula 2", "Flexión de mejillas en la base", F * P.h_axis * 1e3 / (2 * P.t_cheek * P.L_cheek ** 2 / 6), 0.6 * Fy, "MPa", "AISC 360-22 F11 / CJP J2", "σ = F·h/(2·t·L²/6)");
  const Mpin = F / 2 * (P.t_cheek / 2 + (P.gap_cheek - P.w_eye) / 2 + P.w_eye / 4) / 1e3;
  add("Pasador 12", "Flexión (horquilla)", Mpin * 1e6 / (Math.PI * P.D_pin ** 3 / 32), P.Fy_pin / P.Nd, "MPa", "ASME BTH-1 (Fy/Nd)", "M = F/2·(t/2 + g + b/4)");
  add("Pasador 12", "Corte doble", (F / 2) * 1e3 / (Math.PI * P.D_pin ** 2 / 4), P.Fy_pin / (P.Nd * Math.sqrt(3)), "MPa", "ASME BTH-1 3-2.2", "τ = (F/2)/A ≤ Fy/(Nd·√3)");
  // pivote
  const H = P.H_bush * R.W;
  add("Pivote", "Presión en buje (H)", H * 1e3 / (P.D_piv * P.L_bush), P.p_bush, "MPa", "Fabricante bronce-grafito", "p = H/(D·L)");
  add("Pivote", "Flexión del pivote", H * P.lev_piv * 1e3 / (Math.PI * P.D_piv ** 3 / 32), P.Fy_pin / P.Nd, "MPa", "Fy/Nd", "σ = H·e/(πD³/32)");
  // vástago
  const I = Math.PI * P.D_rod ** 4 / 64, Lc = P.L0 + P.stroke, Pcr = Math.PI ** 2 * P.E * I / Lc ** 2 / 1e3;
  add("Cilindro", "Pandeo del vástago (rótulas)", F, Pcr / 3, "kN", "Euler, FS = 3", "Pcr = π²EI/L², L = L0 + carrera");
  // suelo
  add("Apoyo", "Presión bajo placa base (máx.)", R.g_max, 1.0, "MPa", "Referencial – verificar losa", "σ = N/A·(1 + 6e/B)", "Capacidad referencial");
  rows[rows.length - 1].kind = "pass";
  R.extra = { Mss, Mfe, lev, Rg, Mpin, H, Pcr, Ew, tv, tm };
  return rows;
}

/* ---------- FEA del disco: sector entre nervios ---------- */
function linspaceKeys(keys, h) {
  const out = [keys[0]];
  for (let i = 1; i < keys.length; i++) {
    const a = keys[i - 1], b = keys[i], n = Math.max(1, Math.ceil((b - a) / h));
    for (let k = 1; k <= n; k++) out.push(a + (b - a) * k / n);
  }
  return out;
}
function uniqSorted(arr, tol) {
  const s = arr.slice().sort((a, b) => a - b), o = [];
  for (const v of s) if (!o.length || v - o[o.length - 1] > tol) o.push(v);
  return o;
}
function discModel(P, which, hr) {
  const alpha = 2 * Math.PI / P.N_rib, r0 = P.D_hub / 2, Rd = P.D_disc / 2;
  hr = hr || Math.max(20, (Rd - r0) / 45);
  const rings = parseRings(P.rings).filter((r) => r > r0 && r < Rd);
  const keyR = uniqSorted([r0, ...rings, P.R_rib, P.R_bar - P.D_bar / 2, P.R_bar, P.R_bar + P.D_bar / 2, Rd, which === "top" ? P.D_load / 2 : r0]
    .filter((r) => r >= r0 && r <= Rd), 2);
  const rs = linspaceKeys(keyR, hr);
  const barAng = [];
  for (let k = 0; k < P.N_bar; k++) {
    let a = Math.PI / P.N_bar + 2 * Math.PI * k / P.N_bar;
    if (a >= -1e-9 && a <= alpha + 1e-9) barAng.push(a);
  }
  const db = (P.D_bar / 2) / P.R_bar;
  const keyT = uniqSorted([0, alpha, ...barAng, ...barAng.map((a) => a - db), ...barAng.map((a) => a + db)].filter((a) => a >= 0 && a <= alpha), 1e-4);
  const ts = linspaceKeys(keyT, Math.max(1.25 * Math.PI / 180, alpha / 36));
  const nT = ts.length, nodes = [], elems = [], pol = [];
  for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) { nodes.push([rs[i] * Math.cos(ts[j]), rs[i] * Math.sin(ts[j])]); pol.push([rs[i], ts[j]]); }
  const id = (i, j) => i * nT + j;
  const q = [], t = which === "top" ? P.t_top : P.t_bot;
  const R = compute(P);
  for (let i = 0; i < rs.length - 1; i++) for (let j = 0; j < nT - 1; j++) {
    elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]);
    const rc = (rs[i] + rs[i + 1]) / 2;
    q.push(which === "top" ? (rc <= P.D_load / 2 ? R.q_top : 0) : R.q_max);
  }
  const wFix = new Set(), clamp = [], betaN = [], groups = { ring: rings.map(() => []), rib: [], bar: barAng.map(() => []), hub: [] };
  const near = (a, b, tol) => Math.abs(a - b) < tol;
  for (let i = 0; i < rs.length; i++) for (let j = 0; j < nT; j++) {
    const k = id(i, j), r = rs[i], th = ts[j];
    if (i === 0) { clamp.push(k); groups.hub.push(k); continue; }
    rings.forEach((rr, ri) => { if (near(r, rr, 0.5)) { wFix.add(k); groups.ring[ri].push(k); } });
    if ((j === 0 || j === nT - 1) && r <= P.R_rib + 0.5) { if (!wFix.has(k)) groups.rib.push(k); wFix.add(k); }
    barAng.forEach((ba, bi) => {
      const x = r * Math.cos(th) - P.R_bar * Math.cos(ba), y = r * Math.sin(th) - P.R_bar * Math.sin(ba);
      if (Math.hypot(x, y) <= P.D_bar / 2 + 0.5) { if (!wFix.has(k)) groups.bar[bi].push(k); wFix.add(k); }
    });
    if (j === 0) betaN.push([k, 0, 1]);
    if (j === nT - 1) betaN.push([k, -Math.sin(alpha), Math.cos(alpha)]);
  }
  return { nodes, pol, elems, q: Float64Array.from(q), t, E: P.E, nu: P.nu, wFix: [...wFix], clamp, betaN, groups, rings, barAng, alpha, rs, ts, which };
}
function runDisc(P, which) {
  const m = discModel(P, which);
  const t0 = performance.now();
  const r = FEA.plate(m);
  const ms = performance.now() - t0;
  let vmMax = 0, vmC = 0, imax = 0;
  r.el.forEach((e, i) => { if (e.vmGauss > vmMax) { vmMax = e.vmGauss; imax = i; } vmC = Math.max(vmC, e.vm); });
  let wMax = 0; for (const w of r.w) wMax = Math.max(wMax, Math.abs(w));
  const sumR = (arr) => arr.reduce((s, k) => s + Math.abs(r.reac[k]), 0);
  const ringLine = m.rings.map((rr, i) => sumR(m.groups.ring[i]) / (rr * m.alpha));   // N/mm
  const barF = m.groups.bar.map((g) => sumR(g) / 1e3);                                 // kN
  const ribF = sumR(m.groups.rib) / 1e3, hubF = sumR(m.groups.hub) / 1e3;
  const ec = m.elems[imax].map((k) => m.nodes[k]);
  const cx = ec.reduce((s, p) => s + p[0], 0) / 4, cy = ec.reduce((s, p) => s + p[1], 0) / 4;
  return {
    model: m, res: r, ms, vmMax, vmC, wMax, ringLine, barF, ribF, hubF,
    ringMax: Math.max(0, ...ringLine), barMax: Math.max(0, ...barF),
    Fapp: r.Fapplied / 1e3, Rsum: Math.abs(r.Rsum) / 1e3, maxAt: [Math.hypot(cx, cy), Math.atan2(cy, cx) * 180 / Math.PI],
  };
}

/* ---------- FEA del trinquete: tensión plana ---------- */
function runPawl(P, R) {
  const h = 2.5, L = P.pawl_L, b = P.pawl_b;
  const nx = Math.round(L / h), ny = Math.round(b / h), hx = L / nx, hy = b / ny;
  const Xs = R.a - P.pawl_tip, Ys = b, Rs = P.seat_R, Xm = P.shoe_x0 - P.pawl_tip;
  const nodes = [], elems = [], cent = [];
  for (let i = 0; i <= nx; i++) for (let j = 0; j <= ny; j++) nodes.push([i * hx, j * hy]);
  const id = (i, j) => i * (ny + 1) + j;
  const wx = 60 * (b / 85), wy = 36 * (b / 85);
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
    const cx = (i + 0.5) * hx, cy = (j + 0.5) * hy;
    if (Math.hypot(cx - Xs, cy - Ys) < Rs) continue;
    if (cx / wx + cy / wy < 1) continue;
    elems.push([id(i, j), id(i + 1, j), id(i + 1, j + 1), id(i, j + 1)]); cent.push([cx, cy]);
  }
  const used = new Set(); elems.forEach((e) => e.forEach((k) => used.add(k)));
  const fix = [], sup = [];
  for (let i = 0; i <= nx; i++) {
    const x = i * hx;
    if (x >= Xm - 1e-6 && x <= Xm + 25) { fix.push([id(i, 0), 1]); sup.push(id(i, 0)); }
    if (x >= L - 25 - 1e-6) { fix.push([id(i, ny), 1]); sup.push(id(i, ny)); }
  }
  fix.push([id(nx, Math.round(ny / 2)), 0]);
  const F = R.Fmax * 1e3, cand = [];
  for (const k of used) {
    const [x, y] = nodes[k], d = Math.hypot(x - Xs, y - Ys);
    if (d >= Rs - 0.01 && d <= Rs + 1.6 * h) {
      const ph = Math.atan2(y - Ys, x - Xs);
      const w = Math.cos(ph + Math.PI / 2);   // máximo en φ = −90°
      if (w > 0.05 && y < Ys) cand.push([k, ph, w]);
    }
  }
  // un nodo por dirección: conservar el más cercano al arco por sector angular de 3°
  const bins = new Map();
  for (const c of cand) {
    const key = Math.round(c[1] * 180 / Math.PI / 3);
    const d = Math.hypot(nodes[c[0]][0] - Xs, nodes[c[0]][1] - Ys);
    if (!bins.has(key) || d < bins.get(key).d) bins.set(key, { c, d });
  }
  const ld = [...bins.values()].map((v) => v.c);
  const sw = ld.reduce((s, [, , w]) => s + w, 0);
  const loads = ld.map(([k, , w]) => [k, 0, -F * w / sw]);
  const t0 = performance.now();
  const r = FEA.planeStress({ nodes, elems, t: P.pawl_h, E: P.E, nu: P.nu, fix, loads });
  const ms = performance.now() - t0;
  let vmMax = 0, vmMouth = 0, vmFar = 0;
  const loadSet = new Set(ld.map((l) => l[0])), supSet = new Set(sup);
  r.el.forEach((e, i) => {
    vmMax = Math.max(vmMax, e.vm);
    const [cx, cy] = cent[i];
    if (Math.abs(cx - Xm) <= hx && cy > b / 2) vmMouth = Math.max(vmMouth, e.vm);
    const nearLoad = Math.hypot(cx - Xs, cy - Ys) < Rs + 4 * h;
    const nearSup = sup.some((k) => Math.hypot(cx - nodes[k][0], cy - nodes[k][1]) < 4 * h);
    if (!nearLoad && !nearSup) vmFar = Math.max(vmFar, e.vm);
  });
  let dmax = 0; for (let k = 0; k < nodes.length; k++) if (used.has(k)) dmax = Math.max(dmax, Math.hypot(r.u[2 * k], r.u[2 * k + 1]));
  const beam = F * (Xm - Xs) / (P.pawl_h * b * b / 6);
  return { nodes, elems, cent, res: r, ms, vmMax, vmMouth, vmFar, dmax, beam, Xs, Ys, Rs, Xm, L, b, loads, sup, nx, ny };
}

if (typeof module !== "undefined") module.exports = { PARAM_GROUPS, defaults, compute, verifs, discModel, runDisc, runPawl, parseRings };
```

### tt300/app/diag.js
`tt300/app/diag.js` — 265 líneas

```javascript
/* Diagramas SVG (fuerzas, vigas, gráficos). Paleta C explícita para poder exportar a PNG/PDF. */
const nf = (x, d = 0) => (isFinite(x) ? Number(x).toLocaleString("es-CL", { minimumFractionDigits: d, maximumFractionDigits: d }) : "–");

const SV = {
  open: (w, h, extra) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" class="dg" style="max-width:${w}px" ${extra || ""}>`,
  line: (x1, y1, x2, y2, c, w = 1, dash) => `<line x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" stroke="${c}" stroke-width="${w}"${dash ? ` stroke-dasharray="${dash}"` : ""} fill="none"/>`,
  rect: (x, y, w, h, c, fill = "none", sw = 1, dash) => `<rect x="${Math.min(x, x + w).toFixed(1)}" y="${Math.min(y, y + h).toFixed(1)}" width="${Math.abs(w).toFixed(1)}" height="${Math.abs(h).toFixed(1)}" stroke="${c}" stroke-width="${sw}" fill="${fill}"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`,
  circ: (x, y, r, c, fill = "none", sw = 1, dash) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${Math.max(0.5, r).toFixed(1)}" stroke="${c}" stroke-width="${sw}" fill="${fill}"${dash ? ` stroke-dasharray="${dash}"` : ""}/>`,
  poly: (pts, c, fill = "none", sw = 1, dash) => `<polyline points="${pts.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}" stroke="${c}" stroke-width="${sw}" fill="${fill}"${dash ? ` stroke-dasharray="${dash}"` : ""} stroke-linejoin="round"/>`,
  pgon: (pts, c, fill, sw = 1, op = 1) => `<polygon points="${pts.map((p) => p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ")}" stroke="${c}" stroke-width="${sw}" fill="${fill}" fill-opacity="${op}"/>`,
  text: (x, y, s, C, o = {}) => `<text x="${x.toFixed(1)}" y="${y.toFixed(1)}" font-family="${C.font}" font-size="${o.size || 12}" fill="${o.fill || C.ink}" text-anchor="${o.anchor || "start"}"${o.weight ? ` font-weight="${o.weight}"` : ""}${o.rot ? ` transform="rotate(${o.rot} ${x.toFixed(1)} ${y.toFixed(1)})"` : ""}${o.base ? ` dominant-baseline="${o.base}"` : ""}>${String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")}</text>`,
  arrow: (x1, y1, x2, y2, c, w = 2.2, head = 9) => {
    const a = Math.atan2(y2 - y1, x2 - x1), hx = x2 - head * Math.cos(a), hy = y2 - head * Math.sin(a);
    const p1 = [hx + head * 0.42 * Math.sin(a), hy - head * 0.42 * Math.cos(a)], p2 = [hx - head * 0.42 * Math.sin(a), hy + head * 0.42 * Math.cos(a)];
    return SV.line(x1, y1, hx, hy, c, w) + SV.pgon([[x2, y2], p1, p2], c, c, 1);
  },
  arcArrow: (cx, cy, r, a0, a1, c, w = 1.8) => {
    const P = (a) => [cx + r * Math.cos(a), cy - r * Math.sin(a)];
    const p0 = P(a0), p1 = P(a1), large = Math.abs(a1 - a0) > Math.PI ? 1 : 0, sweep = a1 > a0 ? 0 : 1;
    const tang = a1 > a0 ? a1 + Math.PI / 2 : a1 - Math.PI / 2;
    const tip = p1, back = [tip[0] - 9 * Math.cos(-tang), tip[1] - 9 * Math.sin(-tang)];
    return `<path d="M${p0[0].toFixed(1)},${p0[1].toFixed(1)} A${r},${r} 0 ${large} ${sweep} ${p1[0].toFixed(1)},${p1[1].toFixed(1)}" stroke="${c}" stroke-width="${w}" fill="none"/>` + SV.arrow(back[0], back[1], tip[0], tip[1], c, w, 9);
  },
  label: (x, y, lines, C, o = {}) => {
    const size = o.size || 12, lh = size * 1.3, w = Math.max(...lines.map((l) => l.length)) * size * 0.56 + 12, h = lines.length * lh + 8;
    const x0 = o.anchor === "end" ? x - w : o.anchor === "middle" ? x - w / 2 : x;
    let s = `<rect x="${x0.toFixed(1)}" y="${(y - size - 3).toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" rx="3" fill="${C.bg}" fill-opacity="0.92" stroke="${o.stroke || C.line}" stroke-width="1"/>`;
    lines.forEach((l, i) => { s += SV.text(x0 + 6, y + i * lh, l, C, { size, weight: i === 0 && o.boldFirst ? 600 : null, fill: i === 0 && o.color ? o.color : C.ink }); });
    return s;
  },
};

/* ---------- D1: planta con fuerzas ---------- */
function dgPlan(R, C) {
  const P = R.P, W = 860, H = 560, k = Math.min(0.2, 460 / Math.max(P.BX, P.BY, P.D_disc)), cx = W / 2, cy = H / 2 + 4;
  const X = (x) => cx + x * k, Y = (y) => cy - y * k;
  let s = SV.open(W, H);
  s += SV.rect(X(-P.BX / 2), Y(P.BY / 2), P.BX * k, P.BY * k, C.mute, C.fill2, 1);
  s += SV.circ(cx, cy, P.D_disc / 2 * k, C.ink, C.fill, 1.6);
  for (const r of parseRings(P.rings)) s += SV.circ(cx, cy, r * k, C.mute, "none", 1, "5 4");
  for (let i = 0; i < P.N_rib; i++) { const a = 2 * Math.PI * i / P.N_rib; s += SV.line(X(P.D_hub / 2 * Math.cos(a)), Y(P.D_hub / 2 * Math.sin(a)), X(P.R_rib * Math.cos(a)), Y(P.R_rib * Math.sin(a)), C.mute, 1, "5 4"); }
  for (let i = 0; i < P.N_bar; i++) { const a = Math.PI / P.N_bar + 2 * Math.PI * i / P.N_bar; s += SV.circ(X(P.R_bar * Math.cos(a)), Y(P.R_bar * Math.sin(a)), P.D_bar / 2 * k, C.ink, C.fill2, 1); }
  s += SV.circ(cx, cy, P.D_hub / 2 * k, C.ink, "none", 1.2) + SV.circ(cx, cy, P.D_piv / 2 * k, C.ink, C.fill2, 1);
  const d = R.d, Fs = 330 / Math.max(R.Fmax, d.Fc);   // mm modelo por kN
  const Rg = d.Fb * R.Delta / P.Lg;
  for (const sx of [1, -1]) {
    const yb = -sx * P.R_bar * Math.sin(R.th), xa = sx * R.a;
    const yE = yb - sx * P.eye_off, yP = -sx * R.Ybrk;
    // guía
    s += SV.rect(X(sx * P.X_cyl - P.rail_w / 2), Y(425), P.rail_w * k, 850 * k, C.mute, C.fill2, 1);
    // ménsula
    s += SV.rect(X(sx * P.X_cyl - P.gap_cheek / 2 - P.t_cheek), Y(yP + P.L_cheek / 2), (P.gap_cheek + 2 * P.t_cheek) * k, P.L_cheek * k, C.ink, C.fill2, 1.2);
    // cilindro
    const yb0 = yP + sx * 70, yb1 = yP + sx * 370;
    s += SV.rect(X(sx * P.X_cyl - 70), Y(Math.max(yb0, yb1)), 140 * k, 300 * k, C.ink, C.cyl, 1.2);
    s += SV.rect(X(sx * P.X_cyl - P.D_rod / 2), Y(Math.max(yb1, yE)), P.D_rod * k, Math.abs(yE - yb1) * k, C.ink, C.fill, 1);
    s += SV.circ(X(sx * P.X_cyl), Y(yP), 35 * k * 1.5, C.ink, C.bg, 1.2) + SV.circ(X(sx * P.X_cyl), Y(yE), 35 * k * 1.5, C.ink, C.bg, 1.2);
    // carro y trinquete
    const yf = yb + sx * 20, yr = yb + sx * 20 - sx * 300;
    s += SV.rect(X(sx * P.shoe_x0), Y(Math.max(yf, yr)), sx * 130 * k, 300 * k, C.ink, C.shoe, 1.2);
    s += SV.rect(X(sx * P.pawl_tip), Y(Math.max(yb, yb - sx * P.pawl_b)), sx * P.pawl_L * k, P.pawl_b * k, C.ink, C.pawl, 1.2);
    // fuerzas
    const Lb = d.Fb * Fs, Lc = d.Fc * Fs, Lr = Rg * Fs * 1.0;
    s += SV.arrow(X(xa), Y(yb - sx * Lb), X(xa), Y(yb), C.force, 3);
    s += SV.arrow(X(sx * P.X_cyl), Y(yE - sx * Lc * 0.55), X(sx * P.X_cyl), Y(yE), C.force, 3);
    s += SV.arrow(X(sx * P.X_cyl), Y(yP), X(sx * P.X_cyl), Y(yP - sx * Lc * 0.55), C.react, 2.6);
    s += SV.arrow(X(sx * (P.X_cyl + 25) + sx * Lr * 0.6), Y(yf - sx * 12), X(sx * (P.X_cyl + 25)), Y(yf - sx * 12), C.react, 2.2);
    s += SV.arrow(X(sx * (P.X_cyl - 25) - sx * Lr * 0.6), Y(yr + sx * 12), X(sx * (P.X_cyl - 25)), Y(yr + sx * 12), C.react, 2.2);
    const lx = sx > 0 ? X(xa) - 12 : X(xa) + 12, an = sx > 0 ? "end" : "start";
    s += SV.label(lx, Y(yb - sx * Lb * 0.55), [`F barra = ${nf(d.Fb)} kN`], C, { anchor: an, color: C.force, boldFirst: true });
    s += SV.label(sx > 0 ? X(sx * P.X_cyl) + 30 : X(sx * P.X_cyl) - 30, Y((yE + yb1) / 2), [`F cil = ${nf(d.Fc)} kN`, `p = ${nf(d.p)} bar`], C, { anchor: sx > 0 ? "start" : "end", color: C.force, boldFirst: true });
    s += SV.label(sx > 0 ? X(sx * P.X_cyl) + 30 : X(sx * P.X_cyl) - 30, Y(yP - sx * 40), [`Reacción ménsula`, `${nf(d.Fc)} kN`], C, { anchor: sx > 0 ? "start" : "end", color: C.react, boldFirst: true });
    s += SV.label(sx > 0 ? X(sx * (P.X_cyl + 25) + sx * Lr * 0.6) + 6 : X(sx * (P.X_cyl + 25) + sx * Lr * 0.6) - 6, Y(yf - sx * 12) + 4, [`R guía = ${nf(Rg)} kN`], C, { anchor: sx > 0 ? "start" : "end", color: C.react, size: 11 });
  }
  s += SV.arcArrow(cx, cy, 70, Math.PI * 0.15, Math.PI * 0.85, C.accent, 2);
  s += SV.text(cx, cy - 78, "giro", C, { anchor: "middle", size: 11, fill: C.accent });
  s += SV.arcArrow(cx, cy, 120, -Math.PI * 0.25, -Math.PI * 0.75, C.react, 2);
  s += SV.label(cx, cy + 150, [`T resistente = ${nf(d.T)} kN·m`, `μ = ${nf(d.mu, 2)} · N = ${nf(R.N)} kN · r = ${nf(d.r, 3)} m`], C, { anchor: "middle", color: C.react, boldFirst: true, size: 11.5 });
  s += SV.line(cx, cy, X(R.a), cy, C.mute, 1, "3 3") + SV.text((cx + X(R.a)) / 2, cy - 6, `a = ${nf(R.a, 1)} mm`, C, { anchor: "middle", size: 11 });
  s += SV.text(14, 22, "PLANTA – FUERZAS EN EL CASO DE DISEÑO (escala de flechas común)", C, { size: 12, weight: 600 });
  s += SV.text(14, H - 12, `Par motor = 2 · F barra · a = ${nf(2 * d.Fb * R.a / 1000)} kN·m   |   Resultante sobre el pivote = 0 (par puro)`, C, { size: 11.5, fill: C.mute });
  return s + "</svg>";
}

/* ---------- D2: diagrama de cuerpo libre del carro ---------- */
function dgShoe(R, C, F) {
  const P = R.P, W = 560, H = 420;
  F = F || R.d.Fb;
  const Fc = F * R.K, Rg = F * R.Delta / P.Lg, fr = P.mu_g * Rg;
  let s = SV.open(W, H);
  const x0 = 210, x1 = 360, y0 = 100, y1 = 320;
  s += SV.rect(x0, y0, x1 - x0, y1 - y0, C.ink, C.shoe, 1.6);
  s += SV.rect(110, y0 - 2, x0 - 110 + 60, 46, C.ink, C.pawl, 1.4);
  s += SV.circ(110, y0 - 2, 22, C.ink, C.fill2, 1.4);
  const xc = 320, xb = 110;
  s += SV.line(xc, 56, xc, H - 40, C.mute, 1, "8 4 2 4");
  s += SV.line(xb, 56, xb, H - 40, C.mute, 1, "8 4 2 4");
  s += SV.text(xc + 4, H - 30, "eje cilindro / guía", C, { size: 10.5, fill: C.mute });
  s += SV.text(xb - 4, H - 30, "línea de la barra", C, { size: 10.5, fill: C.mute, anchor: "end" });
  s += SV.arrow(xc, H - 44, xc, y1 + 2, C.force, 3);
  s += SV.label(xc + 10, y1 + 30, [`F cil·ηc = ${nf(Fc * P.eta_c)} kN`, `(F cil = ${nf(Fc)} kN)`], C, { color: C.force, boldFirst: true, size: 11.5 });
  s += SV.arrow(xb, y0 - 26, xb, y0 + 46, C.react, 3);
  s += SV.label(xb - 6, y0 + 74, [`F barra = ${nf(F)} kN`], C, { anchor: "middle", color: C.react, boldFirst: true, size: 11.5 });
  // reacciones de guía
  s += SV.arrow(x1 + 70, y0 + 20, x1 + 2, y0 + 20, C.react, 2.4);
  s += SV.arrow(x0 - 70, y1 - 20, x0 - 2, y1 - 20, C.react, 2.4);
  s += SV.label(x1 + 74, y0 + 24, [`R1 = ${nf(Rg)} kN`, `μg·R1 = ${nf(fr)} kN`], C, { color: C.react, size: 11 });
  s += SV.label(x0 - 74, y1 - 16, [`R2 = ${nf(Rg)} kN`, `μg·R2 = ${nf(fr)} kN`], C, { anchor: "end", color: C.react, size: 11 });
  s += SV.arrow(x1 + 8, y0 + 24, x1 + 8, y0 + 54, C.mute, 1.8, 7);
  s += SV.arrow(x0 - 8, y1 - 54, x0 - 8, y1 - 24, C.mute, 1.8, 7);
  s += SV.line(xb, 48, xc, 48, C.ink, 1) + SV.text((xb + xc) / 2, 43, `Δ = ${nf(R.Delta, 1)} mm`, C, { anchor: "middle", size: 11 });
  s += SV.line(x1 + 40, y0 + 20, x1 + 40, y1 - 20, C.mute, 1, "3 3") + SV.text(x1 + 46, (y0 + y1) / 2, `Lg = ${nf(P.Lg)} mm`, C, { size: 11, fill: C.mute });
  s += SV.text(14, 18, "CUERPO LIBRE DEL CARRO (planta, sin escala)", C, { size: 12, weight: 600 });
  s += SV.text(14, H - 8, `R = F·Δ/Lg ;  F cil·ηc = F barra + 2·μg·R  →  K = ${nf(R.K, 3)}`, C, { size: 11.5 });
  return s + "</svg>";
}

/* ---------- D3: barra 4f como viga entre planchas ---------- */
function dgBar(R, C) {
  const P = R.P, F = R.Fmax, L = P.gap, c = Math.min(P.pawl_h, L), W = 560, H = 430;
  const x0 = 90, x1 = 470, sc = (x1 - x0) / L, X = (x) => x0 + x * sc;
  const Mss = F / 4 * (L - c / 2), Mfe = F * (3 * L * L - c * c) / (24 * L), Mmidf = Mss - Mfe;
  let s = SV.open(W, H);
  s += SV.text(14, 18, `BARRA 4f Ø${P.D_bar} – VIGA ENTRE PLANCHAS (F calado = ${nf(F)} kN)`, C, { size: 12, weight: 600 });
  const yb = 92;
  s += SV.rect(x0 - 26, yb - 40, 26, 80, C.ink, C.fill2, 1.2) + SV.rect(x1, yb - 40, 26, 80, C.ink, C.fill2, 1.2);
  s += SV.text(x0 - 13, yb + 56, "4b", C, { anchor: "middle", size: 11 }) + SV.text(x1 + 13, yb + 56, "4a", C, { anchor: "middle", size: 11 });
  s += SV.rect(x0, yb - 10, x1 - x0, 20, C.ink, C.fill, 1.4);
  const xa = X((L - c) / 2), xb2 = X((L + c) / 2);
  for (let i = 0; i <= 8; i++) { const x = xa + (xb2 - xa) * i / 8; s += SV.arrow(x, yb - 44, x, yb - 11, C.force, 1.4, 6); }
  s += SV.line(xa, yb - 44, xb2, yb - 44, C.force, 1.4);
  s += SV.text((xa + xb2) / 2, yb - 50, `F = ${nf(F)} kN en c = ${nf(c)} mm (alto trinquete)`, C, { anchor: "middle", size: 11, fill: C.force });
  s += SV.text((x0 + x1) / 2, yb + 30, `L = ${nf(L)} mm (luz libre entre planchas)`, C, { anchor: "middle", size: 11, fill: C.mute });
  // corte
  const yV = 190, vs = 40 / (F / 2);
  s += SV.line(x0, yV, x1, yV, C.mute, 1);
  s += SV.pgon([[x0, yV], [x0, yV - F / 2 * vs], [xa, yV - F / 2 * vs], [xb2, yV + F / 2 * vs], [x1, yV + F / 2 * vs], [x1, yV]], C.accent, C.accent, 1.4, 0.18);
  s += SV.text(14, yV + 4, "V (kN)", C, { size: 11, weight: 600 });
  s += SV.text(x0 + 4, yV - F / 2 * vs - 5, `+${nf(F / 2)}`, C, { size: 11 }) + SV.text(x1 - 4, yV + F / 2 * vs + 14, `−${nf(F / 2)}`, C, { size: 11, anchor: "end" });
  // momento
  const yM = 320, ms = 70 / Math.max(Mss, Mfe);
  const Mpin = (x) => (x <= (L - c) / 2 ? F / 2 * x : x >= (L + c) / 2 ? F / 2 * (L - x) : F / 2 * x - F / c * (x - (L - c) / 2) ** 2 / 2);
  const pts = [], ptsF = [];
  for (let i = 0; i <= 60; i++) { const x = L * i / 60; pts.push([X(x), yM + Mpin(x) * ms]); ptsF.push([X(x), yM + (Mpin(x) - Mfe) * ms]); }
  s += SV.line(x0, yM, x1, yM, C.mute, 1);
  s += SV.pgon([[x0, yM], ...pts, [x1, yM]], C.force, C.force, 1.6, 0.14);
  s += SV.poly(ptsF, C.react, "none", 1.8, "6 4");
  s += SV.text(14, yM + 4, "M (kN·m)", C, { size: 11, weight: 600 });
  s += SV.label(X(L / 2) + 50, yM + Mss * ms - 4, [`Rotulada: M máx = ${nf(Mss / 1e3, 2)} kN·m`], C, { color: C.force, size: 11 });
  s += SV.label(x0 + 8, yM - Mfe * ms - 12, [`Empotrada: M extremo = ${nf(Mfe / 1e3, 2)} kN·m`, `M centro = ${nf(Mmidf / 1e3, 2)} kN·m`], C, { color: C.react, size: 11 });
  s += SV.text(14, H - 8, "Barra: se verifica con M rotulado. Soldadura bisel: con M empotrado + V.", C, { size: 11, fill: C.mute });
  return s + "</svg>";
}

/* ---------- D4: pasador en horquilla ---------- */
function dgPin(R, C) {
  const P = R.P, F = R.Fmax, W = 560, H = 360;
  const t = P.t_cheek, g = (P.gap_cheek - P.w_eye) / 2, b = P.w_eye, tot = 2 * t + P.gap_cheek;
  const x0 = 110, sc = 340 / tot, X = (x) => x0 + x * sc;
  let s = SV.open(W, H);
  s += SV.text(14, 18, `PASADOR Ø${P.D_pin} EN HORQUILLA DE LA MÉNSULA (F = ${nf(F)} kN)`, C, { size: 12, weight: 600 });
  const yp = 110;
  s += SV.rect(X(0), yp - 60, t * sc, 50, C.ink, C.fill2, 1.2) + SV.rect(X(tot - t), yp - 60, t * sc, 50, C.ink, C.fill2, 1.2);
  s += SV.rect(X(t + g), yp + 10, b * sc, 50, C.ink, C.cyl, 1.2);
  s += SV.rect(X(-10), yp - 9, (tot + 20) * sc, 18, C.ink, C.fill, 1.4);
  s += SV.arrow(X(t / 2), yp - 70, X(t / 2), yp - 10, C.react, 2.4) + SV.arrow(X(tot - t / 2), yp - 70, X(tot - t / 2), yp - 10, C.react, 2.4);
  s += SV.arrow(X(tot / 2), yp + 75, X(tot / 2), yp + 10, C.force, 3);
  s += SV.text(X(t / 2), yp - 76, `F/2 = ${nf(F / 2)}`, C, { anchor: "middle", size: 11, fill: C.react });
  s += SV.text(X(tot - t / 2), yp - 76, `F/2 = ${nf(F / 2)}`, C, { anchor: "middle", size: 11, fill: C.react });
  s += SV.text(X(tot / 2), yp + 92, `F = ${nf(F)} kN (ojal GE${P.D_pin})`, C, { anchor: "middle", size: 11, fill: C.force });
  const M = R.extra ? R.extra.Mpin : F / 2 * (t / 2 + g + b / 4) / 1e3;
  const yM = 250, ms = 60 / M;
  const xs = [0, t / 2, t + g, tot / 2, tot - t - g, tot - t / 2, tot].map(X);
  s += SV.line(xs[0], yM, xs[6], yM, C.mute, 1);
  s += SV.pgon([[xs[1], yM], [xs[2], yM + (F / 2 * (t / 2 + g) / 1e3) * ms], [xs[3], yM + M * ms], [xs[4], yM + (F / 2 * (t / 2 + g) / 1e3) * ms], [xs[5], yM]], C.force, C.force, 1.6, 0.15);
  s += SV.text(14, yM + 4, "M (kN·m)", C, { size: 11, weight: 600 });
  s += SV.label(xs[3] + 14, yM + M * ms + 4, [`M máx = F/2·(t/2 + g + b/4) = ${nf(M, 2)} kN·m`, `σ = ${nf(M * 1e6 / (Math.PI * P.D_pin ** 3 / 32))} MPa`], C, { color: C.force, size: 11 });
  s += SV.text(14, H - 8, `t = ${t} mejilla · g = ${nf(g, 1)} holgura · b = ${b} ojal`, C, { size: 11, fill: C.mute });
  return s + "</svg>";
}

/* ---------- gráfico genérico ---------- */
function dgChart(o, C) {
  const W = o.w || 560, H = o.h || 340, m = { l: 58, r: o.y2 ? 58 : 18, t: 34, b: 46 };
  const pw = W - m.l - m.r, ph = H - m.t - m.b;
  const X = (x) => m.l + (x - o.xr[0]) / (o.xr[1] - o.xr[0]) * pw, Y = (y) => m.t + ph - (y - o.yr[0]) / (o.yr[1] - o.yr[0]) * ph;
  let s = SV.open(W, H);
  s += SV.text(14, 18, o.title, C, { size: 12, weight: 600 });
  for (const b of o.bands || []) s += SV.rect(X(b[0]), m.t, X(b[1]) - X(b[0]), ph, "none", C.band, 0) + SV.text((X(b[0]) + X(b[1])) / 2, m.t + 14, b[2], C, { anchor: "middle", size: 10.5, fill: C.mute });
  for (const t of o.xt) { s += SV.line(X(t), m.t, X(t), m.t + ph, C.grid, 1) + SV.text(X(t), m.t + ph + 16, o.xf ? o.xf(t) : nf(t, 2), C, { anchor: "middle", size: 10.5, fill: C.mute }); }
  for (const t of o.yt) { s += SV.line(m.l, Y(t), m.l + pw, Y(t), C.grid, 1) + SV.text(m.l - 6, Y(t) + 4, nf(t), C, { anchor: "end", size: 10.5, fill: C.mute }); }
  if (o.y2) for (const t of o.yt) s += SV.text(m.l + pw + 6, Y(t) + 4, nf(o.y2(t)), C, { size: 10.5, fill: C.mute });
  s += SV.rect(m.l, m.t, pw, ph, C.line, "none", 1);
  s += SV.text(m.l + pw / 2, H - 8, o.xl, C, { anchor: "middle", size: 11 });
  s += SV.text(14, m.t + ph / 2, o.yl, C, { anchor: "middle", size: 11, rot: -90 });
  if (o.y2l) s += SV.text(W - 12, m.t + ph / 2, o.y2l, C, { anchor: "middle", size: 11, rot: 90 });
  for (const h of o.hl || []) { s += SV.line(m.l, Y(h.y), m.l + pw, Y(h.y), h.c, h.w || 1.6, h.dash) + SV.text(m.l + 6, Y(h.y) - 5, h.t, C, { size: 10.5, fill: h.c, weight: 600 }); }
  const clip = `cp${Math.random().toString(36).slice(2, 8)}`;
  s += `<defs><clipPath id="${clip}"><rect x="${m.l}" y="${m.t}" width="${pw}" height="${ph}"/></clipPath></defs><g clip-path="url(#${clip})">`;
  for (const se of o.series) s += SV.poly(se.pts.map((p) => [X(p[0]), Y(p[1])]), se.c, "none", se.w || 2, se.dash);
  s += "</g>";
  for (const se of o.series) if (se.lab) { const p = se.lab.at; s += SV.text(X(p[0]), Y(p[1]), se.lab.t, C, { size: 10.5, fill: se.c, anchor: se.lab.anchor || "start", weight: 600 }); }
  if (o.legend) {
    const lx = m.l + pw - 170, ly = m.t + ph - 14 - o.legend.length * 17;
    s += `<rect x="${lx - 8}" y="${ly - 14}" width="174" height="${o.legend.length * 17 + 10}" rx="3" fill="${C.bg}" fill-opacity="0.92" stroke="${C.line}"/>`;
    o.legend.forEach(([c, w, dash, t], i) => { const y = ly + i * 17; s += SV.line(lx, y - 4, lx + 22, y - 4, c, w, dash) + SV.text(lx + 28, y, t, C, { size: 10.5 }); });
  }
  for (const mk of o.markers || []) {
    s += SV.circ(X(mk.x), Y(Math.min(mk.y, o.yr[1])), 4.5, mk.c, mk.c, 1);
    s += SV.text(X(mk.x) + (mk.dx || 7), Y(Math.min(mk.y, o.yr[1])) + (mk.dy || -7), mk.t, C, { size: 10.5, fill: C.ink, anchor: mk.anchor || "start" });
  }
  return s + "</svg>";
}
function niceTicks(lo, hi, n) {
  const span = hi - lo, step0 = span / n, mag = 10 ** Math.floor(Math.log10(step0)), r = step0 / mag;
  const step = (r < 1.5 ? 1 : r < 3 ? 2 : r < 7 ? 5 : 10) * mag, t = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) t.push(+v.toFixed(10));
  return t;
}
function dgMu(R, C) {
  const P = R.P, xmax = Math.max(0.6, P.mu_dry + 0.05), Fc = (mu, r) => R.cs(mu, r).Fc;
  const ymax = Math.max(R.Fmax * 1.35, Fc(xmax, R.r_eff) * 0.8);
  const curve = (r) => { const pts = []; for (let i = 0; i <= 60; i++) { const mu = xmax * i / 60; pts.push([mu, Fc(mu, r)]); } return pts; };
  const lab = (r, t) => { let mu = xmax; const f = Fc(xmax, r); if (f > ymax) mu = (ymax * 0.97 / R.K * 2 * R.a / 1000 - R.Tpiv) / (R.N * r); return { at: [mu, Fc(mu, r)], t, anchor: "end" }; };
  return dgChart({
    title: "FUERZA POR CILINDRO vs COEFICIENTE DE FRICCIÓN", xr: [0, xmax], yr: [0, ymax], xt: niceTicks(0, xmax, 6), yt: niceTicks(0, ymax, 6),
    xl: "μ estático en la interfaz de giro", yl: "F por cilindro (kN)", y2: (F) => F * 1e3 / R.A * 10, y2l: "presión (bar)",
    bands: [[0.10, 0.20, "acero/acero engrasado"], [0.5, Math.min(0.8, xmax), "acero seco"]],
    hl: [{ y: R.Fmax, c: C.bad, t: `alivio ${nf(P.p_relief)} bar = ${nf(R.Fmax)} kN` }, { y: R.Falarm, c: C.warn, t: `alarma ${nf(P.p_alarm)} bar = ${nf(R.Falarm)} kN`, dash: "6 4" }],
    series: [
      { pts: curve(R.r_u), c: C.mute, w: 1.6 },
      { pts: curve(R.r_eff), c: C.accent, w: 2.6 },
      { pts: curve(R.r_max), c: C.mute, w: 1.4, dash: "5 4" },
    ],
    legend: [[C.accent, 2.6, null, `r ${nf(R.r_eff, 2)} m (diseño)`], [C.mute, 1.6, null, `r ${nf(R.r_u, 3)} m (uniforme)`], [C.mute, 1.4, "5 4", `r ${nf(R.r_max, 2)} m (cota física)`]],
    markers: R.cases.map((c) => ({ x: c.mu, y: c.Fc, c: c.FS >= 1 ? C.good : C.bad, t: `${nf(c.Fc)} kN`, dx: 7, dy: c.key === "nom" ? 14 : -7 })),
  }, C);
}
function dgStroke(R, C) {
  const P = R.P, d = R.stroke, ymax = Math.max(R.Fmax * 1.15, ...d.map((r) => r.con) ) * 1.05;
  const ser = (k, c, w, dash, t) => ({ pts: [[0, 0], [P.free, 0], ...d.map((r) => [r.s, r[k]])], c, w, dash, lab: { at: [d[d.length - 1].s, d[d.length - 1][k]], t, anchor: "end" } });
  return dgChart({
    title: "FUERZA EN CADA CILINDRO A LO LARGO DE LA CARRERA", xr: [0, P.stroke], yr: [0, ymax], xt: niceTicks(0, P.stroke, 8), yt: niceTicks(0, ymax, 6), xf: (t) => nf(t),
    xl: `carrera del vástago (mm) – libre 0–${nf(P.free)}, toma barra a −${nf(180 / P.N_bar, 1)}° y suelta a +${nf(180 / P.N_bar, 1)}°`, yl: "F por cilindro (kN)", y2: (F) => F * 1e3 / R.A * 10, y2l: "presión (bar)",
    hl: [{ y: R.Fmax, c: C.bad, t: "alivio" }, { y: R.Falarm, c: C.warn, t: "alarma", dash: "6 4" }],
    series: [ser("nom", C.good, 1.8, null, "nominal"), ser("dis", C.accent, 2.6, null, "diseño"), ser("con", C.warn, 1.8, "6 4", "contaminado")],
  }, C);
}
function dgBreak(R, C) {
  const W = 900, H = 150, tot = R.d.Fc, x0 = 20, x1 = W - 20, sc = (x1 - x0) / tot;
  let s = SV.open(W, H) + SV.text(14, 18, `DESGLOSE DE LA FUERZA DE DISEÑO POR CILINDRO (${nf(tot)} kN)`, C, { size: 12, weight: 600 });
  const cols = [C.accent, C.react, C.warn, C.mute];
  let x = x0;
  R.breakdown.forEach(([t, v], i) => {
    const w = v * sc;
    s += SV.rect(x, 40, w, 34, C.bg, cols[i], 1.5);
    if (w > 46) s += SV.text(x + w / 2, 62, nf(v), C, { anchor: "middle", size: 11.5, weight: 600, fill: C.bg });
    x += w;
  });
  R.breakdown.forEach(([t, v], i) => {
    const yy = 102 + (i % 2) * 22, xx = 20 + Math.floor(i / 2) * 440;
    s += SV.rect(xx, yy - 10, 12, 12, cols[i], cols[i], 1) + SV.text(xx + 18, yy, `${t}: ${nf(v, 1)} kN (${nf(v / tot * 100, 1)} %)`, C, { size: 11 });
  });
  return s + "</svg>";
}
```

### tt300/app/export.js
`tt300/app/export.js` — 343 líneas

```javascript
/* Plano paramétrico (SVG / DXF / PDF) y memoria de verificación (PDF). Coordenadas de papel en mm, y hacia arriba. */
const LAYERS = {
  VIS: { w: 0.5, dash: null, color: 7 }, FINA: { w: 0.18, dash: null, color: 8 }, EJE: { w: 0.18, dash: [10, 2, 1.5, 2], color: 1 },
  OCU: { w: 0.25, dash: [3, 1.5], color: 3 }, COTA: { w: 0.18, dash: null, color: 4 }, TXT: { w: 0.25, dash: null, color: 7 },
  MARCO: { w: 0.7, dash: null, color: 7 }, FUERZA: { w: 0.5, dash: null, color: 1 },
};
function Sheet() { this.it = []; }
Sheet.prototype = {
  L(x1, y1, x2, y2, ly = "VIS") { this.it.push({ k: "L", x1, y1, x2, y2, ly }); },
  R(x0, y0, x1, y1, ly = "VIS") { this.L(x0, y0, x1, y0, ly); this.L(x1, y0, x1, y1, ly); this.L(x1, y1, x0, y1, ly); this.L(x0, y1, x0, y0, ly); },
  P(pts, closed, ly = "VIS") { for (let i = 0; i < pts.length - 1; i++) this.L(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], ly); if (closed) this.L(pts[pts.length - 1][0], pts[pts.length - 1][1], pts[0][0], pts[0][1], ly); },
  C(x, y, r, ly = "VIS") { this.it.push({ k: "C", x, y, r, ly }); },
  A(x, y, r, a0, a1, ly = "VIS") { this.it.push({ k: "A", x, y, r, a0, a1, ly }); },
  T(s, x, y, h = 2.5, al = "l", ly = "TXT", bold = false) { this.it.push({ k: "T", s: String(s), x, y, h, al, ly, bold }); },
  S(pts, ly = "COTA") { this.it.push({ k: "S", pts, ly }); },
  arrow(x, y, ang, size = 2.6, ly = "COTA") {
    const w = size * 0.33, bx = x - size * Math.cos(ang), by = y - size * Math.sin(ang);
    this.S([[x, y], [bx + w * Math.sin(ang), by - w * Math.cos(ang)], [bx - w * Math.sin(ang), by + w * Math.cos(ang)]], ly);
  },
  force(x1, y1, x2, y2, label, h = 2.4) {
    this.L(x1, y1, x2, y2, "FUERZA"); this.arrow(x2, y2, Math.atan2(y2 - y1, x2 - x1), 4, "FUERZA");
    if (label) this.T(label, x1 + 1.5, y1 + (y1 > y2 ? 1.5 : -4), h, "l", "TXT", true);
  },
  dim(x1, y1, x2, y2, off, txt, orient = "h", h = 2.3) {
    if (orient === "h") {
      const y = y1 + off; this.L(x1, y1, x1, y + Math.sign(off) * 1.5, "COTA"); this.L(x2, y2, x2, y + Math.sign(off) * 1.5, "COTA");
      this.L(x1, y, x2, y, "COTA"); this.arrow(x1, y, Math.PI); this.arrow(x2, y, 0); this.T(txt, (x1 + x2) / 2, y + 0.8, h, "c", "COTA");
    } else {
      const x = x1 + off; this.L(x1, y1, x + Math.sign(off) * 1.5, y1, "COTA"); this.L(x2, y2, x + Math.sign(off) * 1.5, y2, "COTA");
      this.L(x, y1, x, y2, "COTA"); this.arrow(x, y1, y1 < y2 ? -Math.PI / 2 : Math.PI / 2); this.arrow(x, y2, y2 > y1 ? Math.PI / 2 : -Math.PI / 2);
      this.it.push({ k: "T", s: txt, x: x - 0.8, y: (y1 + y2) / 2, h, al: "c", ly: "COTA", rot: 90 });
    }
  },
  table(x0, y0, cols, rows, rh = 4.2, h = 2.0) {
    const Wt = cols.reduce((s, c) => s + c[1], 0); let y = y0;
    const all = [cols.map((c) => c[0])].concat(rows);
    all.forEach((row, i) => {
      this.L(x0, y, x0 + Wt, y, i <= 1 ? "VIS" : "FINA"); let x = x0;
      row.forEach((cell, j) => {
        const al = i === 0 ? "c" : cols[j][2];
        const tx = al === "c" ? x + cols[j][1] / 2 : al === "r" ? x + cols[j][1] - 1 : x + 1;
        this.T(cell, tx, y - rh + (rh - h) / 2 + 0.2, h, al, "TXT", i === 0); x += cols[j][1];
      });
      y -= rh;
    });
    this.L(x0, y, x0 + Wt, y, "VIS"); let x = x0;
    for (const c of cols.concat([[0, 0]])) { this.L(x, y0, x, y, x === x0 || x >= x0 + Wt - 0.01 ? "VIS" : "FINA"); x += c[1]; }
    return y;
  },
};

function buildSheet(R, V, fea) {
  const P = R.P, S = new Sheet(), W = 841, H = 594;
  S.R(0, 0, W, H, "FINA"); S.R(20, 10, W - 10, H - 10, "MARCO");
  // rótulo
  const x0 = W - 190, y1 = 72;
  S.R(x0, 10, W - 10, y1, "MARCO");
  [20, 30, 44].forEach((yy) => S.L(x0, 10 + yy - 10, W - 10, 10 + yy - 10, "FINA"));
  S.L(x0 + 60, 10, x0 + 60, 30, "FINA"); S.L(x0 + 120, 10, x0 + 120, 30, "FINA");
  S.T("PROYECTO: TORNAMESA HIDRÁULICA " + nf(P.W_tf) + " tf", x0 + 2, y1 - 5, 3.2, "l", "TXT", true);
  S.T("SOLUCIÓN B – ACERO-ACERO CON GRASA GRAFITADA", x0 + 2, y1 - 10.5, 2.4);
  S.T("PLANO DE VERIFICACIÓN PARAMÉTRICO", x0 + 2, y1 - 19, 3.6, "l", "TXT", true);
  S.T("Generado desde la herramienta de verificación con los parámetros indicados.", x0 + 2, 31.5, 2.0);
  const today = new Date().toLocaleDateString("es-CL");
  [["ESCALA", "INDICADA", 0, 1], ["FECHA", today, 1, 1], ["FORMATO", "A1", 2, 1], ["PLANO N°", "TT300-B-P-01", 0, 0], ["LÁMINA", "1 de 1", 1, 0], ["REV.", "P", 2, 0]]
    .forEach(([l, v, c, r]) => { S.T(l, x0 + c * 60 + 1.5, 10 + r * 10 + 7.2, 1.8); S.T(v, x0 + c * 60 + 30, 10 + r * 10 + 2.2, r === 0 ? 3.0 : 2.6, "c", "TXT", r === 0); });

  // ---- VISTA 1: planta 1:10 ----
  const k1 = 0.1, cx = 195, cy = 420, X = (x) => cx + x * k1, Y = (y) => cy + y * k1;
  S.R(X(-P.BX / 2), Y(-P.BY / 2), X(P.BX / 2), Y(P.BY / 2));
  S.C(cx, cy, P.D_disc / 2 * k1);
  parseRings(P.rings).forEach((r) => S.C(cx, cy, r * k1, "OCU"));
  for (let i = 0; i < P.N_rib; i++) { const a = 2 * Math.PI * i / P.N_rib; S.L(X(P.D_hub / 2 * Math.cos(a)), Y(P.D_hub / 2 * Math.sin(a)), X(P.R_rib * Math.cos(a)), Y(P.R_rib * Math.sin(a)), "OCU"); }
  for (let i = 0; i < P.N_bar; i++) { const a = Math.PI / P.N_bar + 2 * Math.PI * i / P.N_bar; S.C(X(P.R_bar * Math.cos(a)), Y(P.R_bar * Math.sin(a)), P.D_bar / 2 * k1); }
  S.C(cx, cy, P.D_hub / 2 * k1); S.C(cx, cy, P.D_piv / 2 * k1, "FINA");
  S.L(X(-P.BX / 2 - 30), cy, X(P.BX / 2 + 30), cy, "EJE"); S.L(cx, Y(-P.BY / 2 - 30), cx, Y(P.BY / 2 + 30), "EJE");
  for (const sx of [1, -1]) {
    const yb = -sx * P.R_bar * Math.sin(R.th), yE = yb - sx * P.eye_off, yP = -sx * R.Ybrk;
    S.R(X(sx * P.X_cyl - P.rail_w / 2), Y(-425), X(sx * P.X_cyl + P.rail_w / 2), Y(425), "OCU");
    S.R(X(sx * P.X_cyl - P.gap_cheek / 2 - P.t_cheek), Y(yP - P.L_cheek / 2), X(sx * P.X_cyl + P.gap_cheek / 2 + P.t_cheek), Y(yP + P.L_cheek / 2));
    S.R(X(sx * P.X_cyl - 70), Y(yP + sx * 70), X(sx * P.X_cyl + 70), Y(yP + sx * 370));
    S.R(X(sx * P.X_cyl - P.D_rod / 2), Y(yP + sx * 370), X(sx * P.X_cyl + P.D_rod / 2), Y(yE));
    S.R(X(sx * P.shoe_x0), Y(yb + sx * 20), X(sx * (P.shoe_x0 + 130)), Y(yb + sx * 20 - sx * 300));
    S.R(X(sx * P.pawl_tip), Y(yb), X(sx * (P.pawl_tip + P.pawl_L)), Y(yb - sx * P.pawl_b));
    S.force(X(sx * R.a), Y(yb - sx * 360), X(sx * R.a), Y(yb), sx > 0 ? `F barra ${nf(R.d.Fb)} kN` : null);
  }
  S.dim(X(-P.BX / 2), Y(-P.BY / 2), X(P.BX / 2), Y(-P.BY / 2), -10, nf(P.BX));
  S.dim(X(-P.BX / 2), Y(-P.BY / 2), X(-P.BX / 2), Y(P.BY / 2), -10, nf(P.BY), "v");
  S.dim(X(-P.X_cyl), Y(P.BY / 2), X(P.X_cyl), Y(P.BY / 2), 8, `${nf(2 * P.X_cyl)} (ejes cilindros)`);
  S.T(`Ø${nf(P.D_disc)} disco · ${P.N_bar} barras Ø${P.D_bar} en R${nf(P.R_bar)}`, X(-P.D_disc / 2), Y(P.D_disc / 2) + 3, 2.4);
  S.T("VISTA 1 – PLANTA", cx, Y(-P.BY / 2) - 22, 4, "c", "TXT", true); S.T("ESC. 1:10", cx, Y(-P.BY / 2) - 27, 2.8, "c");

  // ---- VISTA 2: corte diametral 1:10 ----
  const zb = 215;
  const Z = (z) => zb + z * k1, TD = R.TD;
  S.R(X(-P.BX / 2), Z(0), X(P.BX / 2), Z(P.t_base));
  S.R(X(-P.D_disc / 2), Z(P.t_base), X(P.D_disc / 2), Z(P.t_base + P.t_bot));
  S.R(X(-P.D_disc / 2), Z(P.t_base + P.t_bot + P.gap), X(P.D_disc / 2), Z(P.t_base + TD));
  for (const r of parseRings(P.rings)) for (const sg of [1, -1]) S.R(X(sg * r - P.t_ring / 2), Z(P.t_base + P.t_bot), X(sg * r + P.t_ring / 2), Z(P.t_base + P.t_bot + P.gap), "FINA");
  S.R(X(-P.D_hub / 2), Z(P.t_base), X(P.D_hub / 2), Z(P.t_base + TD), "VIS");
  S.L(cx, Z(-15), cx, Z(P.t_base + TD + 25), "EJE");
  S.dim(X(P.BX / 2), Z(0), X(P.BX / 2), Z(P.t_base), 6, nf(P.t_base), "v");
  S.dim(X(P.D_disc / 2), Z(P.t_base), X(P.D_disc / 2), Z(P.t_base + TD), 14, nf(TD), "v");
  S.T("VISTA 2 – CORTE DIAMETRAL", cx, zb - 12, 4, "c", "TXT", true); S.T("ESC. 1:10", cx, zb - 17, 2.8, "c");

  // ---- DETALLE 1: borde del disco 1:2,5 (sección por una barra) ----
  const k2 = 0.4, rl = parseRings(P.rings), r0 = (rl.length ? rl[rl.length - 1] : P.R_bar - 200) - 60, rx = P.D_disc / 2 + 60;
  const ox = 345, oz = 360, XR = (r) => ox + (r - r0) * k2, ZR = (z) => oz + z * k2;
  S.L(XR(r0), ZR(0), XR(rx), ZR(0)); S.L(XR(r0), ZR(P.t_base), XR(rx), ZR(P.t_base));
  S.L(XR(rx), ZR(-5), XR(rx), ZR(P.t_base + 5), "FINA"); S.L(XR(r0), ZR(-5), XR(r0), ZR(P.t_base + TD + 10), "FINA");
  const zt0 = P.t_base, zt1 = P.t_base + P.t_bot, zt2 = zt1 + P.gap, zt3 = zt2 + P.t_top, Rd = P.D_disc / 2;
  const bx0 = P.R_bar - P.D_hole / 2, bx1 = P.R_bar + P.D_hole / 2;
  for (const [za, zz] of [[zt0, zt1], [zt2, zt3]]) { S.P([[XR(r0), ZR(za)], [XR(bx0), ZR(za)], [XR(bx0), ZR(zz)], [XR(r0), ZR(zz)]], false); S.P([[XR(bx1), ZR(za)], [XR(Rd), ZR(za)], [XR(Rd), ZR(zz)], [XR(bx1), ZR(zz)]], false); }
  S.R(XR(P.R_bar - P.D_bar / 2), ZR(zt0), XR(P.R_bar + P.D_bar / 2), ZR(zt3));
  S.L(XR(P.R_bar), ZR(zt0 - 8), XR(P.R_bar), ZR(zt3 + 8), "EJE");
  if (rl.length) { const rr = rl[rl.length - 1]; S.R(XR(rr - P.t_ring / 2), ZR(zt1), XR(rr + P.t_ring / 2), ZR(zt2)); S.L(XR(rr), ZR(zt1 - 6), XR(rr), ZR(zt2 + 6), "EJE"); S.T(`Alma 4d R${nf(rr)} e=${P.t_ring}`, XR(rr) + 3, ZR(zt2) - 6, 2.2); }
  // biseles de soldadura
  const sb = P.weld_S * k2;
  for (const [zf, sgn] of [[zt3, -1], [zt0, 1]]) for (const xe of [XR(P.R_bar - P.D_bar / 2), XR(P.R_bar + P.D_bar / 2)]) {
    const dir = xe < XR(P.R_bar) ? -1 : 1; S.S([[xe, ZR(zf)], [xe + dir * sb, ZR(zf)], [xe, ZR(zf) + sgn * sb]], "VIS");
  }
  S.dim(XR(Rd), ZR(zt0), XR(Rd), ZR(zt1), 8, nf(P.t_bot), "v"); S.dim(XR(Rd), ZR(zt1), XR(Rd), ZR(zt2), 8, nf(P.gap), "v");
  S.dim(XR(Rd), ZR(zt2), XR(Rd), ZR(zt3), 8, nf(P.t_top), "v"); S.dim(XR(Rd), ZR(zt0), XR(Rd), ZR(zt3), 18, nf(TD), "v");
  S.dim(XR(r0), ZR(0), XR(r0), ZR(P.t_base), -6, nf(P.t_base), "v");
  S.dim(XR(P.R_bar - P.D_bar / 2), ZR(zt3), XR(P.R_bar + P.D_bar / 2), ZR(zt3), 8, `Ø${P.D_bar} (agujero Ø${P.D_hole})`);
  S.T(`4a plancha sup. e=${P.t_top}`, XR(r0) + 2, ZR(zt3) + 2, 2.2); S.T(`4b plancha inf. e=${P.t_bot}`, XR(r0) + 2, ZR(zt0) + 1.0 + P.t_bot * k2 * 0.15, 2.2);
  S.T(`Placa base pos 1 e=${P.t_base}`, XR(r0) + 2, ZR(P.t_base / 2) - 1, 2.2);
  S.T(`Bisel ${P.weld_S} (E = ${P.weld_S - 3}) a ras, ambas caras`, XR(P.R_bar) - 16, ZR(zt3) + 16, 2.2);
  S.T(`Grasa grafitada en interfaz (μ diseño ${nf(P.mu, 2)})`, XR(r0) + 2, ZR(zt0) - 4.5, 2.2);
  S.T("DETALLE 1 – BORDE DEL DISCO (corte por barra 4f)", (XR(r0) + XR(rx)) / 2, oz - 18, 3.6, "c", "TXT", true);
  S.T("ESC. 1:2,5", (XR(r0) + XR(rx)) / 2, oz - 23, 2.8, "c");

  // ---- DETALLE 2: carro y trinquete 1:4 ----
  const k3 = 0.25, xm0 = 840, ox3 = 350, oy3 = 270, X3 = (x) => ox3 + (x - xm0) * k3, Y3 = (y) => oy3 + y * k3;
  const yb = -P.R_bar * Math.sin(R.th), yE = yb - P.eye_off;
  const angA = Math.asin(Math.max(-1, -560 / P.R_bar)), angB = Math.asin(Math.min(1, 60 / P.R_bar));
  const arcPts = (rr) => { const p = []; for (let i = 0; i <= 30; i++) { const t = angA + (angB - angA) * i / 30; p.push([X3(rr * Math.cos(t)), Y3(rr * Math.sin(t))]); } return p; };
  S.P(arcPts(P.D_disc / 2), false, "VIS"); S.P(arcPts(P.R_bar), false, "EJE");
  for (let i = -3; i <= 0; i++) { const a = -R.th + i * 2 * R.th; if (P.R_bar * Math.sin(a) < -560) continue; S.C(X3(P.R_bar * Math.cos(a)), Y3(P.R_bar * Math.sin(a)), P.D_bar / 2 * k3); }
  S.R(X3(P.pawl_tip), Y3(yb), X3(P.pawl_tip + P.pawl_L), Y3(yb - P.pawl_b));
  S.R(X3(P.shoe_x0), Y3(yb + 20), X3(P.shoe_x0 + 130), Y3(yb + 20 - 300));
  S.R(X3(P.X_cyl - P.rail_w / 2), Y3(yb + 60), X3(P.X_cyl + P.rail_w / 2), Y3(yb - 360), "OCU");
  S.L(X3(P.X_cyl), Y3(yb + 80), X3(P.X_cyl), Y3(yE - 120), "EJE"); S.L(X3(R.a), Y3(yb + 80), X3(R.a), Y3(yb - 360), "EJE");
  S.C(X3(P.X_cyl), Y3(yE), 35 * k3 * 1.5); S.R(X3(P.X_cyl - P.D_rod / 2), Y3(yE - 20), X3(P.X_cyl + P.D_rod / 2), Y3(yE - 110));
  S.force(X3(R.a) - 0, Y3(yb - 230), X3(R.a), Y3(yb - 2), null);
  S.T(`F barra = ${nf(R.d.Fb)} kN`, X3(R.a) - 2, Y3(yb - 160), 2.3, "r", "TXT", true);
  S.force(X3(P.X_cyl), Y3(yE - 230), X3(P.X_cyl), Y3(yE - 40), null);
  S.T(`F cil = ${nf(R.d.Fc)} kN (${nf(R.d.p)} bar)`, X3(P.X_cyl) + 3, Y3(yE - 200), 2.3, "l", "TXT", true);
  S.dim(X3(R.a), Y3(yb + 40), X3(P.X_cyl), Y3(yb + 40), 4, `Δ = ${nf(R.Delta, 1)}`);
  S.dim(X3(R.a), Y3(yb - P.pawl_b), X3(P.shoe_x0), Y3(yb - P.pawl_b), -6, `${nf(P.shoe_x0 - R.a, 1)}`);
  S.dim(X3(P.pawl_tip), Y3(yb), X3(P.pawl_tip), Y3(yb - P.pawl_b), -5, nf(P.pawl_b), "v");
  S.dim(X3(P.shoe_x0 + 130), Y3(yb + 20 - 25), X3(P.shoe_x0 + 130), Y3(yb + 20 - 25 - P.Lg), 6, `Lg ${nf(P.Lg)}`, "v");
  S.T(`a = R·cos(${nf(180 / P.N_bar, 1)}°) = ${nf(R.a, 1)} mm desde el eje del disco`, X3(xm0) + 2, Y3(yb + 95), 2.2);
  S.T("DETALLE 2 – CARRO, TRINQUETE Y BARRA (planta)", (X3(xm0) + X3(1250)) / 2, Y3(yE - 290), 3.6, "c", "TXT", true);
  S.T("ESC. 1:4", (X3(xm0) + X3(1250)) / 2, Y3(yE - 290) - 5, 2.8, "c");

  // ---- notas ----
  const notes = [
    "BASES DE CÁLCULO",
    `1. Carga WLL ${nf(P.W_tf)} tf = ${nf(R.W)} kN; disco ${nf(R.mass.total)} kg; N = ${nf(R.N, 1)} kN; e ≤ ${nf(P.e)} mm; φd = ${nf(P.phi_d, 2)}.`,
    `2. Fricción estática de diseño μ = ${nf(P.mu, 2)} con r_ef = ${nf(P.r_eff, 2)} m (uniforme ${nf(R.r_u, 3)} m).`,
    `3. Empuje en par: F barra = T/(2a); K = (1 + 2μg·Δ/Lg)/ηc = ${nf(R.K, 3)}; F cil = K·F barra.`,
    `4. Cadena de empuje verificada a la fuerza de calado ${nf(R.Fmax)} kN (alivio ${nf(P.p_relief)} bar).`,
    "5. Placas 4a/4b: FEA Mindlin (MITC4) de un sector entre nervios con almas, nervios y barras como apoyos.",
    "6. Trinquete: FEA tensión plana Q4. Normas: AISC 360-22 (ASD), ASME BTH-1, AWS D1.1.",
    "7. Plano de verificación. No reemplaza los planos de fabricación emitidos (TT300-B-D/F).",
  ];
  notes.forEach((t, i) => S.T(t, 26, 185 - i * 4.4, 2.3, "l", "TXT", i === 0));

  // ---- tablas (columna derecha) ----
  const tx = 610;
  S.T("PARÁMETROS DE ENTRADA", tx, 578, 3.0, "l", "TXT", true);
  const prow = [];
  for (const g of PARAM_GROUPS) for (const it of g.items) prow.push([it[1], String(typeof P[it[0]] === "number" ? nf(P[it[0]], it[4] && it[4] < 1 ? (it[4] < 0.01 ? 3 : 2) : 0) : P[it[0]]), it[2]]);
  const half = Math.ceil(prow.length / 2);
  S.table(tx, 574, [["Parámetro", 54, "l"], ["Valor", 22, "r"], ["Unid.", 13, "l"]], prow.slice(0, half), 3.6, 1.8);
  S.table(tx + 91, 574, [["Parámetro", 54, "l"], ["Valor", 22, "r"], ["Unid.", 13, "l"]], prow.slice(half), 3.6, 1.8);
  let yy = 574 - (half + 1) * 3.6 - 9;
  S.T("ACCIONAMIENTO – FUERZA POR CILINDRO", tx, yy + 4, 3.0, "l", "TXT", true);
  yy = S.table(tx, yy, [["Caso", 50, "l"], ["μ", 12, "c"], ["r m", 14, "c"], ["F cil kN", 20, "r"], ["p bar", 18, "r"], ["FS", 14, "r"], ["", 52, "l"]],
    R.cases.map((c) => [c.name.split(" – ")[0], nf(c.mu, 2), nf(c.r, 3), nf(c.Fc), nf(c.p), nf(c.FS, 2), c.FS >= 1 ? "gira" : "NO GIRA"]), 4.0, 2.0);
  S.T(`μ máximo vencible a ${nf(P.p_relief)} bar: ${nf(R.muMax(R.r_eff, P.p_relief), 3)} (r ${nf(R.r_eff, 2)}) / ${nf(R.muMax(R.r_max, P.p_relief), 3)} (r ${nf(R.r_max, 2)})`, tx, yy - 4, 2.1);
  yy -= 18;
  S.T("VERIFICACIONES – FACTOR DE UTILIZACIÓN", tx, yy + 4, 3.0, "l", "TXT", true);
  S.table(tx, yy, [["Elemento", 108, "l"], ["Demanda", 22, "r"], ["Capac.", 22, "r"], ["FU", 13, "r"], ["", 15, "c"]],
    V.map((v) => [`${v.grp}: ${v.el}`.slice(0, 70), nf(v.dem, v.dem < 20 ? 2 : 0), nf(v.cap, v.cap < 20 ? 2 : 0), nf(v.fu, 2), (v.kind === "pass" ? v.fu <= 1 : v.fu <= 0.9) ? "OK" : v.fu <= 1 ? "MON." : "NO"]), 3.5, 1.75);
  return S;
}

/* ---------- salidas ---------- */
function sheetSVG(S, C) {
  const H = 594;
  let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 841 594" class="sheet">` + `<rect x="0" y="0" width="841" height="594" fill="${C.paper}"/>`;
  for (const e of S.it) {
    const L = LAYERS[e.ly] || LAYERS.VIS, col = e.ly === "FUERZA" ? C.force : C.ink, dash = L.dash ? ` stroke-dasharray="${L.dash.join(" ")}"` : "";
    if (e.k === "L") s += `<line x1="${e.x1.toFixed(2)}" y1="${(H - e.y1).toFixed(2)}" x2="${e.x2.toFixed(2)}" y2="${(H - e.y2).toFixed(2)}" stroke="${col}" stroke-width="${L.w}"${dash}/>`;
    else if (e.k === "C") s += `<circle cx="${e.x.toFixed(2)}" cy="${(H - e.y).toFixed(2)}" r="${e.r.toFixed(2)}" stroke="${col}" stroke-width="${L.w}" fill="none"${dash}/>`;
    else if (e.k === "S") s += `<polygon points="${e.pts.map((p) => p[0].toFixed(2) + "," + (H - p[1]).toFixed(2)).join(" ")}" fill="${col}"/>`;
    else if (e.k === "T") {
      const an = e.al === "c" ? "middle" : e.al === "r" ? "end" : "start", x = e.x, y = H - e.y;
      s += `<text x="${x.toFixed(2)}" y="${y.toFixed(2)}" font-family="Helvetica, Arial, sans-serif" font-size="${(e.h * 1.38).toFixed(2)}" text-anchor="${an}" fill="${C.ink}"${e.bold ? ' font-weight="700"' : ""}${e.rot ? ` transform="rotate(${-e.rot} ${x.toFixed(2)} ${y.toFixed(2)})"` : ""}>${e.s.replace(/&/g, "&amp;").replace(/</g, "&lt;")}</text>`;
    }
  }
  return s + "</svg>";
}

function dxfText(s) {
  let o = "";
  for (const ch of s) {
    const c = ch.codePointAt(0);
    if (ch === "Ø") o += "%%c"; else if (ch === "°") o += "%%d"; else if (ch === "±") o += "%%p";
    else if (c < 128) o += ch; else o += "\\U+" + c.toString(16).toUpperCase().padStart(4, "0");
  }
  return o;
}
function sheetDXF(S) {
  const out = [];
  const g = (code, val) => { out.push(String(code)); out.push(String(val)); };
  g(0, "SECTION"); g(2, "HEADER"); g(9, "$ACADVER"); g(1, "AC1009"); g(9, "$INSUNITS"); g(70, 4); g(9, "$LTSCALE"); g(40, 1.0); g(0, "ENDSEC");
  g(0, "SECTION"); g(2, "TABLES");
  g(0, "TABLE"); g(2, "LTYPE"); g(70, 3);
  const lt = [["CONTINUOUS", "Solid", []], ["DASHED", "__ __", [3, -1.5]], ["CENTER", "__ . __", [10, -2, 1.5, -2]]];
  for (const [n, d, pat] of lt) { g(0, "LTYPE"); g(2, n); g(70, 0); g(3, d); g(72, 65); g(73, pat.length); g(40, pat.reduce((s, v) => s + Math.abs(v), 0)); for (const v of pat) g(49, v); }
  g(0, "ENDTAB");
  g(0, "TABLE"); g(2, "LAYER"); g(70, Object.keys(LAYERS).length);
  for (const [n, L] of Object.entries(LAYERS)) { g(0, "LAYER"); g(2, n); g(70, 0); g(62, L.color); g(6, n === "EJE" ? "CENTER" : n === "OCU" ? "DASHED" : "CONTINUOUS"); }
  g(0, "ENDTAB"); g(0, "ENDSEC");
  g(0, "SECTION"); g(2, "ENTITIES");
  for (const e of S.it) {
    if (e.k === "L") { g(0, "LINE"); g(8, e.ly); g(10, e.x1.toFixed(3)); g(20, e.y1.toFixed(3)); g(30, 0); g(11, e.x2.toFixed(3)); g(21, e.y2.toFixed(3)); g(31, 0); }
    else if (e.k === "C") { g(0, "CIRCLE"); g(8, e.ly); g(10, e.x.toFixed(3)); g(20, e.y.toFixed(3)); g(30, 0); g(40, e.r.toFixed(3)); }
    else if (e.k === "S") { const p = e.pts; g(0, "SOLID"); g(8, e.ly); g(10, p[0][0].toFixed(3)); g(20, p[0][1].toFixed(3)); g(30, 0); g(11, p[1][0].toFixed(3)); g(21, p[1][1].toFixed(3)); g(31, 0); g(12, p[2][0].toFixed(3)); g(22, p[2][1].toFixed(3)); g(32, 0); g(13, p[2][0].toFixed(3)); g(23, p[2][1].toFixed(3)); g(33, 0); }
    else if (e.k === "T") {
      g(0, "TEXT"); g(8, e.ly); g(10, e.x.toFixed(3)); g(20, e.y.toFixed(3)); g(30, 0); g(40, e.h); g(1, dxfText(e.s));
      if (e.rot) g(50, e.rot);
      const ha = e.al === "c" ? 1 : e.al === "r" ? 2 : 0;
      if (ha) { g(72, ha); g(11, e.x.toFixed(3)); g(21, e.y.toFixed(3)); g(31, 0); }
    }
  }
  g(0, "ENDSEC"); g(0, "EOF");
  return out.join("\r\n") + "\r\n";
}
function pdfText(s) {
  const map = { "μ": "µ", "≤": "<=", "≥": ">=", "φ": "phi", "Δ": "Delta ", "σ": "sigma", "τ": "tau", "η": "eta", "π": "pi", "√": "raiz", "−": "-", "→": "->", "≈": "~", "Ω": "Omega", "ν": "nu", "γ": "gamma", "β": "beta", "…": "...", "✓": "OK" };
  map["∫"] = "int "; map["Σ"] = "Sum "; map["θ"] = "theta"; map["κ"] = "kappa"; map["·"] = "·";
  return String(s).replace(/[μ≤≥φΔστηπ√−→≈Ωνγβ…✓∫Σθκ]/g, (m) => map[m]).replace(/[^\x00-\xFF\u2013\u2014\u2018\u2019\u201C\u201D\u2022\u2026\u20AC]/g, "");
}
function sheetPDF(S) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: [841, 594] });
  const H = 594;
  for (const e of S.it) {
    const L = LAYERS[e.ly] || LAYERS.VIS;
    doc.setDrawColor(0); doc.setFillColor(0); doc.setTextColor(0);
    doc.setLineWidth(L.w); doc.setLineDashPattern(L.dash || [], 0);
    if (e.k === "L") doc.line(e.x1, H - e.y1, e.x2, H - e.y2);
    else if (e.k === "C") doc.circle(e.x, H - e.y, e.r, "S");
    else if (e.k === "S") doc.triangle(e.pts[0][0], H - e.pts[0][1], e.pts[1][0], H - e.pts[1][1], e.pts[2][0], H - e.pts[2][1], "F");
    else if (e.k === "T") {
      doc.setFont("helvetica", e.bold ? "bold" : "normal"); doc.setFontSize(e.h * 4.0);
      const str = pdfText(e.s);
      if (e.rot) { const w = doc.getTextWidth(str); doc.text(str, e.x, H - (e.y - w / 2), { angle: 90 }); }
      else doc.text(str, e.x, H - e.y, { align: e.al === "c" ? "center" : e.al === "r" ? "right" : "left" });
    }
  }
  doc.setLineDashPattern([], 0);
  return doc.output("blob");
}

/* ---------- memoria de verificación A4 ---------- */
async function svgToPng(svg, scale = 2) {
  const img = new Image();
  const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  await new Promise((res, rej) => { img.onload = res; img.onerror = () => rej(new Error("svg")); img.src = url; });
  const c = document.createElement("canvas"); c.width = img.width * scale; c.height = img.height * scale;
  const x = c.getContext("2d"); x.fillStyle = "#ffffff"; x.fillRect(0, 0, c.width, c.height); x.drawImage(img, 0, 0, c.width, c.height);
  return { data: c.toDataURL("image/png"), w: img.width, h: img.height };
}
async function memoriaPDF(R, V, fea, Cp, images) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const P = R.P, M = 16, PW = 210 - 2 * M;
  let y = 18;
  const T = (s, size = 9.5, bold = false, x = M) => { doc.setFont("helvetica", bold ? "bold" : "normal"); doc.setFontSize(size); doc.setTextColor(0); const lines = doc.splitTextToSize(pdfText(s), PW - (x - M)); for (const l of lines) { if (y > 280) { doc.addPage(); y = 18; } doc.text(l, x, y); y += size * 0.43; } };
  const H1 = (s) => { y += 3; if (y > 262) { doc.addPage(); y = 18; } T(s, 12.5, true); y += 1.5; doc.setDrawColor(0); doc.setLineWidth(0.3); doc.line(M, y - 3.2, M + PW, y - 3.2); y += 1; };
  const tbl = (head, body, colStyles) => { doc.autoTable({ startY: y, head: [head.map(pdfText)], body: body.map((r) => r.map(pdfText)), margin: { left: M, right: M }, styles: { fontSize: 8, textColor: 0, lineColor: 120, lineWidth: 0.1, cellPadding: 1.2 }, headStyles: { fillColor: [235, 235, 235], textColor: 0, fontStyle: "bold" }, columnStyles: colStyles || {}, theme: "grid" }); y = doc.lastAutoTable.finalY + 5; };
  const img = (im, wmm) => { const h = wmm * im.h / im.w; if (y + h > 282) { doc.addPage(); y = 18; } doc.addImage(im.data, "PNG", M + (PW - wmm) / 2, y, wmm, h); y += h + 4; };
  T("MEMORIA DE VERIFICACIÓN – TORNAMESA HIDRÁULICA " + nf(P.W_tf) + " tf (TT300-B)", 14, true);
  T("Solución B: interfaz acero-acero con grasa grafitada. Accionamiento por 2 cilindros en par sobre barras verticales.", 9.5);
  T(`Fecha: ${new Date().toLocaleDateString("es-CL")} · Generada con la herramienta de verificación paramétrica · Rev. P`, 8.5);
  y += 2;
  const VV = V.filter((v) => v.kind !== "pass"), worst = VV.reduce((a, b) => (b.fu > a.fu ? b : a));
  H1("1. RESULTADO");
  tbl(["Concepto", "Valor"], [
    ["Fuerza de diseño por cilindro", `${nf(R.d.Fc, 1)} kN (${nf(R.d.tf, 1)} tf) a ${nf(R.d.p)} bar`],
    ["Fuerza disponible por cilindro", `${nf(R.Fmax, 1)} kN a ${nf(P.p_relief)} bar (alivio)`],
    ["Factor de seguridad del accionamiento", nf(R.d.FS, 2)],
    ["μ máximo vencible (r diseño / r máx.)", `${nf(R.muMax(R.r_eff, P.p_relief), 3)} / ${nf(R.muMax(R.r_max, P.p_relief), 3)}`],
    ["Factor de utilización máximo", `${nf(worst.fu, 2)} – ${worst.grp}: ${worst.el}`],
    ["Acero seco (μ " + nf(P.mu_dry, 2) + ")", R.cases[3].FS < 1 ? `No gira (requiere ${nf(R.cases[3].p)} bar)` : `Gira (FS ${nf(R.cases[3].FS, 2)})`],
  ], { 0: { cellWidth: 70 } });
  H1("2. HIPÓTESIS");
  [
    `H1 Carga WLL ${nf(P.W_tf)} tf = ${nf(R.W, 1)} kN; peso disco ${nf(R.mass.total)} kg (${nf(R.Wd, 2)} kN); N = ${nf(R.N, 1)} kN. Excentricidad e ≤ ${nf(P.e)} mm. φd = ${nf(P.phi_d, 2)} sólo en resistencias.`,
    `H2 Interfaz plana anular acero/acero, R = ${nf(P.D_disc / 2)} mm, r = ${nf(P.D_bore / 2)} mm, grasa grafitada NLGI 2 (≥10 % grafito).`,
    `H3 μ estático de diseño = ${nf(P.mu, 2)} (límite superior del rango acero/acero engrasado 0,10–0,20). Nominal ${nf(P.mu_nom, 2)}; contaminado ${nf(P.mu_cont, 2)}; seco ${nf(P.mu_dry, 2)}.`,
    `H4 r uniforme = 2/3·(R³−r³)/(R²−r²) = ${nf(R.r_u, 3)} m; la distribución lineal por excentricidad no lo cambia (∫x·r dA = 0). Diseño r_ef = ${nf(P.r_eff, 2)} m por concentración al borde.`,
    `H5 Dos cilindros en par sobre barras en R${nf(P.R_bar)}; brazo mínimo a = R·cos(180°/N) = ${nf(R.a, 1)} mm.`,
    `H6 Pérdidas: μg = ${nf(P.mu_g, 2)} con Δ = ${nf(R.Delta, 1)} mm y Lg = ${nf(P.Lg)} mm; ηc = ${nf(P.eta_c, 2)}; K = ${nf(R.K, 3)}. T piv = ${nf(R.Tpiv, 2)} kN·m.`,
    `H7 Elementos de la cadena de empuje verificados a la fuerza de calado ${nf(R.Fmax, 1)} kN (alivio ${nf(P.p_relief)} bar).`,
  ].forEach((t) => { T(t, 8.8, false); y += 0.8; });
  H1("3. PARÁMETROS");
  const prm = []; for (const g of PARAM_GROUPS) for (const it of g.items) prm.push([g.t, it[1], typeof P[it[0]] === "number" ? nf(P[it[0]], it[4] && it[4] < 1 ? (it[4] < 0.01 ? 3 : 2) : 0) : P[it[0]], it[2]]);
  tbl(["Grupo", "Parámetro", "Valor", "Unidad"], prm, { 2: { halign: "right" } });
  H1("4. ACCIONAMIENTO");
  ["(1) T = μ·N·r_ef + T_piv", "(2) F_barra = T/(2a)", "(3) K = (1 + 2·μg·Δ/Lg)/ηc", "(4) F_cil = K·F_barra ;  p = F_cil/A ;  FS = F_max/F_cil", "(5) μ_max = (F_max/K·2a − T_piv)/(N·r_ef)"].forEach((t) => T(t, 9));
  y += 1;
  T(`Caso de diseño: T = ${nf(P.mu, 2)} × ${nf(R.N, 1)} × ${nf(P.r_eff, 3)} + ${nf(R.Tpiv, 2)} = ${nf(R.d.T, 1)} kN·m → F_barra = ${nf(R.d.Fb, 1)} kN → F_cil = ${nf(R.d.Fc, 1)} kN → p = ${nf(R.d.p)} bar → FS = ${nf(R.d.FS, 2)}.`, 9);
  y += 1;
  tbl(["Caso", "μ", "r_ef m", "T kN·m", "F barra kN", "F cil kN", "p bar", "FS", "Resultado"], R.cases.map((c) => [c.name, nf(c.mu, 2), nf(c.r, 3), nf(c.T), nf(c.Fb), nf(c.Fc), nf(c.p), nf(c.FS, 2), c.FS >= 1.25 ? "Gira" : c.FS >= 1 ? "Gira (límite)" : "NO GIRA"]));
  tbl(["Componente de F_cil (diseño)", "kN", "%"], R.breakdown.map(([t, v]) => [t, nf(v, 1), nf(v / R.d.Fc * 100, 1)]));
  for (const k of ["plan", "mu", "stroke", "breakdown"]) if (images[k]) img(images[k], k === "breakdown" ? 130 : 170);
  H1("5. DIAGRAMAS DE CARGA DE ELEMENTOS");
  for (const k of ["shoe", "bar", "pin"]) if (images[k]) img(images[k], 140);
  H1("6. VERIFICACIONES");
  tbl(["Grupo", "Elemento", "Demanda", "Capacidad", "Unid.", "FU", "Estado", "Referencia"], V.map((v) => [v.grp, v.el, nf(v.dem, v.dem < 20 ? 2 : 1), nf(v.cap, v.cap < 20 ? 2 : 1), v.unit, nf(v.fu, 2), v.kind === "pass" ? (v.fu <= 1 ? "Cumple" : "No cumple") : v.fu <= 0.9 ? "Aceptable" : v.fu <= 1 ? "Monitoreo" : "No cumple", v.ref]),
    { 2: { halign: "right" }, 3: { halign: "right" }, 5: { halign: "right" } });
  H1("7. ANÁLISIS POR ELEMENTOS FINITOS");
  if (fea && fea.bot) {
    T(`Disco: sector de ${nf(360 / P.N_rib, 1)}° entre nervios, placa Mindlin MITC4 (${fea.bot.model.elems.length} elementos, ${fea.bot.res.ndof} GDL). Apoyos: cubo empotrado; almas 4d y nervios 4e como apoyos lineales (w = 0); barras 4f como apoyos de área; simetría en los bordes del sector. Plancha inferior con q_max = ${nf(R.q_max, 2)} MPa uniforme (conservador); superior con q = ${nf(R.q_top, 2)} MPa en Ø${nf(P.D_load)}.`, 8.8);
    tbl(["Plancha", "σvm máx MPa", "w máx mm", "Reacción almas N/mm", "Reacción barra kN", "Σ cargas / Σ reacciones kN"], ["bot", "top"].map((k) => { const f = fea[k]; return [k === "bot" ? "4b inferior" : "4a superior", nf(f.vmMax, 1), nf(f.wMax, 3), f.ringLine.map((v) => nf(v)).join(" / "), nf(f.barMax, 1), `${nf(f.Fapp, 1)} / ${nf(f.Rsum, 1)}`]; }));
    for (const k of ["feaBot", "feaTop"]) if (images[k]) img(images[k], 110);
  }
  if (fea && fea.pawl) {
    T(`Trinquete: tensión plana Q4 h = 2,5 mm, espesor ${P.pawl_h} mm, carga F = ${nf(R.Fmax, 1)} kN en el asiento R${P.seat_R}; apoyo en la boca del carro (25 mm inferiores) y labio posterior. σ boca FEA = ${nf(fea.pawl.vmMouth)} MPa; teoría de vigas = ${nf(fea.pawl.beam)} MPa; máximo fuera de zonas de contacto = ${nf(fea.pawl.vmFar)} MPa; pico local en contacto = ${nf(fea.pawl.vmMax)} MPa (singularidad del modelo de apoyo).`, 8.8);
    if (images.feaPawl) img(images.feaPawl, 170);
  }
  H1("8. CONCLUSIÓN");
  T(R.d.FS >= 1.25 && worst.fu <= 1 ? `Con los parámetros indicados el accionamiento vence la fricción de diseño con FS = ${nf(R.d.FS, 2)} y todos los elementos verificados quedan con FU ≤ ${nf(worst.fu, 2)}. La lubricación con grasa grafitada es obligatoria.` : `Con los parámetros indicados NO se cumple al menos un criterio (FS accionamiento ${nf(R.d.FS, 2)}; FU máx ${nf(worst.fu, 2)}). Revisar antes de aprobar.`, 9.5);
  const n = doc.getNumberOfPages();
  for (let i = 1; i <= n; i++) { doc.setPage(i); doc.setFontSize(7.5); doc.setFont("helvetica", "normal"); doc.text(pdfText(`TT300-B · Memoria de verificación paramétrica · pág. ${i} de ${n}`), M, 290); }
  return doc.output("blob");
}
```

### tt300/app/geo.js
`tt300/app/geo.js` — 226 líneas

```javascript
/* Esquema de geometría: vistas 2D (planta, elevación, detalle de borde) y modelo 3D con resaltado del parámetro editado. */
const PART_OF = {
  W_tf: ["load"], e: ["load"], phi_d: ["load"], D_load: ["load"],
  D_disc: ["top", "bot"], t_top: ["top"], t_bot: ["bot"], gap: ["top", "bot", "rings", "ribs"], D_hub: ["hub"], D_bore: ["hub", "pivot"],
  rings: ["rings"], t_ring: ["rings"], N_rib: ["ribs"], t_rib: ["ribs"], R_rib: ["ribs"],
  R_bar: ["bars"], D_bar: ["bars"], N_bar: ["bars"], D_hole: ["bars"], weld_S: ["bars"],
  mu: ["iface"], r_eff: ["iface"], mu_nom: ["iface"], mu_cont: ["iface"], mu_dry: ["iface"], q_lim: ["iface"],
  D_piston: ["cyl"], D_rod: ["cyl"], p_relief: ["cyl"], p_alarm: ["cyl"], stroke: ["cyl"], free: ["cyl", "shoe"], L0: ["cyl"], eye_off: ["cyl", "shoe"],
  X_cyl: ["cyl", "rail", "bracket"], Lg: ["shoe", "rail"], mu_g: ["shoe", "rail"], eta_c: ["cyl"], mu_piv: ["pivot"], H_frac: ["pivot"],
  pawl_tip: ["pawl"], pawl_L: ["pawl"], pawl_b: ["pawl"], pawl_h: ["pawl"], seat_R: ["pawl"], shoe_x0: ["shoe"], Fy_pawl: ["pawl"],
  D_pin: ["bracket"], t_cheek: ["bracket"], gap_cheek: ["bracket"], w_eye: ["bracket"], L_cheek: ["bracket"], h_axis: ["bracket", "cyl"], Fy_pin: ["bracket", "pivot"],
  rail_w: ["rail"], rail_embed: ["rail"], rail_h: ["rail"], L_brg: ["rail"],
  D_piv: ["pivot"], L_bush: ["pivot"], p_bush: ["pivot"], H_bush: ["pivot"], lev_piv: ["pivot"],
  BX: ["base"], BY: ["base"], t_base: ["base"], Fy: ["top", "bot", "rings", "ribs", "bars", "base"], FEXX: ["bars"], Nd: ["pawl", "bracket", "pivot"],
};
const PART_NAME = { load: "carga sobre la parrilla", top: "plancha superior 4a", bot: "plancha inferior 4b", rings: "almas 4d", ribs: "nervios 4e", hub: "cubo 4c", bars: "barras 4f",
  iface: "interfaz de giro (r efectivo)", cyl: "cilindros", shoe: "carros de empuje", pawl: "trinquetes", bracket: "ménsulas y pasadores", rail: "guías", pivot: "pivote y buje", base: "placa base" };

/* ---------- vistas 2D ---------- */
function geoStyle(C, hl, part, fill) {
  const on = hl && hl.includes(part);
  return { s: on ? C.accent : C.ink, w: on ? 2.4 : 1.1, f: on ? C.band : fill || "none", on };
}
function geoPlan(R, C, hl) {
  const P = R.P, W = 620, H = 540, k = Math.min(520 / P.BX, 440 / P.BY), cx = W / 2, cy = H / 2 + 6;
  const X = (x) => cx + x * k, Y = (y) => cy - y * k;
  let s = SV.open(W, H);
  const g = (p, f) => geoStyle(C, hl, p, f);
  let st = g("base", C.fill2); s += SV.rect(X(-P.BX / 2), Y(P.BY / 2), P.BX * k, P.BY * k, st.s, st.f, st.w);
  st = g("top", C.fill); const stb = g("bot");
  s += SV.circ(cx, cy, P.D_disc / 2 * k, st.on || stb.on ? C.accent : C.ink, st.on || stb.on ? C.band : C.fill, st.on || stb.on ? 2.4 : 1.6);
  st = g("rings"); for (const r of parseRings(P.rings)) s += SV.circ(cx, cy, r * k, st.on ? C.accent : C.mute, "none", st.on ? 2.2 : 1, st.on ? null : "5 4");
  st = g("ribs");
  for (let i = 0; i < P.N_rib; i++) { const a = 2 * Math.PI * i / P.N_rib; s += SV.line(X(P.D_hub / 2 * Math.cos(a)), Y(P.D_hub / 2 * Math.sin(a)), X(P.R_rib * Math.cos(a)), Y(P.R_rib * Math.sin(a)), st.on ? C.accent : C.mute, st.on ? 2.2 : 1, st.on ? null : "5 4"); }
  st = g("bars", C.fill2);
  for (let i = 0; i < P.N_bar; i++) { const a = Math.PI / P.N_bar + 2 * Math.PI * i / P.N_bar; s += SV.circ(X(P.R_bar * Math.cos(a)), Y(P.R_bar * Math.sin(a)), P.D_bar / 2 * k, st.s, st.on ? C.accent : C.fill2, st.w); }
  st = g("hub"); s += SV.circ(cx, cy, P.D_hub / 2 * k, st.s, st.f, st.w);
  st = g("pivot", C.fill2); s += SV.circ(cx, cy, P.D_piv / 2 * k, st.s, st.f, st.w);
  st = g("load"); s += SV.circ(cx, cy, P.D_load / 2 * k, st.on ? C.accent : C.force, "none", st.on ? 2.2 : 1, "10 4 2 4");
  s += SV.circ(X(P.e), cy, 4, C.force, C.force, 1) + SV.text(X(P.e) + 6, cy - 6, "CG", C, { size: 10.5, fill: C.force });
  st = g("iface"); if (st.on) s += SV.circ(cx, cy, P.r_eff * 1000 * k, C.accent, "none", 2.2, "3 3") + SV.text(cx, Y(P.r_eff * 1000) - 4, `r ef = ${nf(P.r_eff, 2)} m`, C, { anchor: "middle", size: 11, fill: C.accent });
  for (const sx of [1, -1]) {
    const yb = -sx * P.R_bar * Math.sin(R.th), yE = yb - sx * P.eye_off, yP = -sx * R.Ybrk;
    st = g("rail", C.fill2); s += SV.rect(X(sx * P.X_cyl - P.rail_w / 2), Y(425), P.rail_w * k, 850 * k, st.s, st.f, st.w);
    st = g("bracket", C.fill2); s += SV.rect(X(sx * P.X_cyl - P.gap_cheek / 2 - P.t_cheek), Y(yP + P.L_cheek / 2), (P.gap_cheek + 2 * P.t_cheek) * k, P.L_cheek * k, st.s, st.f, st.w);
    st = g("cyl", C.cyl);
    const yb1 = yP + sx * 370;
    s += SV.rect(X(sx * P.X_cyl - 70), Y(Math.max(yP + sx * 70, yb1)), 140 * k, 300 * k, st.s, st.on ? C.band : C.cyl, st.w);
    s += SV.rect(X(sx * P.X_cyl - P.D_rod / 2), Y(Math.max(yb1, yE)), P.D_rod * k, Math.abs(yE - yb1) * k, st.s, "none", st.w);
    st = g("shoe", C.shoe); s += SV.rect(X(sx * P.shoe_x0), Y(Math.max(yb + sx * 20, yb + sx * 20 - sx * 300)), sx * 130 * k, 300 * k, st.s, st.on ? C.band : C.shoe, st.w);
    st = g("pawl", C.pawl); s += SV.rect(X(sx * P.pawl_tip), Y(Math.max(yb, yb - sx * P.pawl_b)), sx * P.pawl_L * k, P.pawl_b * k, st.s, st.on ? C.band : C.pawl, st.w);
  }
  // cotas
  const dimH = (x1, x2, y, t) => SV.line(x1, y, x2, y, C.mute, 1) + SV.line(x1, y - 4, x1, y + 4, C.mute, 1) + SV.line(x2, y - 4, x2, y + 4, C.mute, 1) + SV.text((x1 + x2) / 2, y - 4, t, C, { anchor: "middle", size: 10.5, fill: C.mute });
  s += dimH(X(-P.BX / 2), X(P.BX / 2), Y(-P.BY / 2) + 16, `${nf(P.BX)} placa base`);
  s += dimH(X(-P.X_cyl), X(P.X_cyl), Y(P.BY / 2) - 10, `${nf(2 * P.X_cyl)} entre ejes de cilindros`);
  s += SV.text(X(-P.BX / 2) - 6, cy, `${nf(P.BY)}`, C, { anchor: "middle", size: 10.5, fill: C.mute, rot: -90 });
  s += SV.text(14, 18, `PLANTA · disco Ø${nf(P.D_disc)} · ${P.N_bar} barras Ø${P.D_bar} en R${nf(P.R_bar)} · ${P.N_rib} nervios`, C, { size: 12, weight: 600 });
  return s + "</svg>";
}
function geoElev(R, C, hl) {
  const P = R.P, W = 620, H = 300, k = 480 / P.BX, cx = W / 2 - 20, zb = H - 70;
  const X = (x) => cx + x * k, Z = (z) => zb - z * k * 2.2;    // escala vertical ×2,2
  const g = (p, f) => geoStyle(C, hl, p, f), TD = R.TD, Rd = P.D_disc / 2, t0 = P.t_base, t1 = t0 + P.t_bot, t2 = t1 + P.gap, t3 = t2 + P.t_top;
  let s = SV.open(W, H), st;
  st = g("base", C.fill2); s += SV.rect(X(-P.BX / 2), Z(t0), P.BX * k, Z(0) - Z(t0), st.s, st.f, st.w);
  st = g("bot", C.fill2); s += SV.rect(X(-Rd), Z(t1), 2 * Rd * k, Z(t0) - Z(t1), st.s, st.on ? C.band : C.fill2, st.w);
  st = g("top", C.fill2); s += SV.rect(X(-Rd), Z(t3), 2 * Rd * k, Z(t2) - Z(t3), st.s, st.on ? C.band : C.fill2, st.w);
  st = g("ribs"); s += SV.rect(X(P.D_hub / 2), Z(t2), (P.R_rib - P.D_hub / 2) * k, Z(t1) - Z(t2), st.on ? C.accent : C.mute, st.on ? C.band : "none", st.on ? 2 : 0.8, "4 3") + SV.rect(X(-P.R_rib), Z(t2), (P.R_rib - P.D_hub / 2) * k, Z(t1) - Z(t2), st.on ? C.accent : C.mute, st.on ? C.band : "none", st.on ? 2 : 0.8, "4 3");
  st = g("rings"); for (const r of parseRings(P.rings)) for (const sg of [1, -1]) s += SV.rect(X(sg * r - P.t_ring / 2), Z(t2), P.t_ring * k, Z(t1) - Z(t2), st.s, st.on ? C.accent : C.ink, st.w * 0.6);
  st = g("bars"); const xb = R.a; for (const sg of [1, -1]) s += SV.rect(X(sg * xb - P.D_bar / 2), Z(t3), P.D_bar * k, Z(t0) - Z(t3), st.s, st.on ? C.band : "none", st.w, "3 2");
  st = g("hub", C.fill); s += SV.rect(X(-P.D_hub / 2), Z(t3), P.D_hub * k, Z(t0) - Z(t3), st.s, st.on ? C.band : C.fill, st.w);
  st = g("pivot"); s += SV.rect(X(-P.D_piv / 2), Z(t3 - 20), P.D_piv * k, Z(0) - Z(t3 - 20), st.s, st.on ? C.band : "none", st.w, "4 3");
  st = g("load"); s += SV.rect(X(-P.D_load / 2), Z(t3 + 40), P.D_load * k, Z(t3) - Z(t3 + 40), st.on ? C.accent : C.force, "none", st.on ? 2 : 1, "8 4");
  s += SV.arrow(X(P.e), Z(t3 + 110), X(P.e), Z(t3 + 42), C.force, 2.4) + SV.text(X(P.e) + 6, Z(t3 + 90), `W = ${nf(P.W_tf)} tf (e = ${nf(P.e)})`, C, { size: 10.5, fill: C.force });
  for (const sx of [1, -1]) {
    const za = t0 + P.h_axis;
    st = g("rail", C.fill2); s += SV.rect(X(sx * P.X_cyl - P.rail_w / 2), Z(t0 + P.rail_h), P.rail_w * k, Z(t0 - P.rail_embed) - Z(t0 + P.rail_h), st.s, st.f, st.w);
    st = g("cyl"); s += SV.circ(X(sx * P.X_cyl), Z(za), 70 * k * 1.5, st.s, st.on ? C.band : "none", st.w, "4 3");
    st = g("shoe"); s += SV.rect(X(sx * P.shoe_x0), Z(za + 70), sx * 130 * k, Z(t0) - Z(za + 70), st.s, st.on ? C.band : "none", st.w, "4 3");
    st = g("bracket"); s += SV.rect(X(sx * P.X_cyl - P.gap_cheek / 2 - P.t_cheek), Z(za + 70), (P.gap_cheek + 2 * P.t_cheek) * k, Z(t0) - Z(za + 70), st.s, "none", st.w, "2 2");
  }
  // cotas verticales (lado derecho)
  const xr = X(-P.BX / 2) - 22;
  const dimV = (z1, z2, t, x) => SV.line(x, Z(z1), x, Z(z2), C.mute, 1) + SV.line(x - 3, Z(z1), x + 3, Z(z1), C.mute, 1) + SV.line(x - 3, Z(z2), x + 3, Z(z2), C.mute, 1) + SV.text(x + 4, (Z(z1) + Z(z2)) / 2 + 4, t, C, { size: 10, fill: C.mute });
  const xd = X(P.BX / 2) + 12;
  s += dimV(0, t0, nf(P.t_base), xr) + dimV(t0, t1, nf(P.t_bot), xd) + dimV(t1, t2, nf(P.gap), xd) + dimV(t2, t3, nf(P.t_top), xd) + dimV(t0, t3, `TD ${nf(TD)}`, xd + 34);
  s += SV.text(14, 18, "ELEVACIÓN – CORTE A-A POR EL EJE X", C, { size: 12, weight: 600 }) + SV.text(14, 34, "escala vertical ×2,2 para leer espesores", C, { size: 10.5, fill: C.mute });
  return s + "</svg>";
}
function geoEdge(R, C, hl) {
  const P = R.P, rl = parseRings(P.rings), Rd = P.D_disc / 2, r0 = (rl.length ? rl[rl.length - 1] : P.R_bar - 200) - 70, r1 = Rd + 70;
  const W = 620, H = 320, k = Math.min((W - 110) / (r1 - r0), 200 / (R.TD + 50)), x0 = 40, zb = H - 50;
  const X = (r) => x0 + (r - r0) * k, Z = (z) => zb - z * k;
  const g = (p, f) => geoStyle(C, hl, p, f), t0 = 40, t1 = t0 + P.t_bot, t2 = t1 + P.gap, t3 = t2 + P.t_top;
  let s = SV.open(W, H), st;
  st = g("base", C.fill2); s += SV.rect(X(r0), Z(t0), (r1 - r0) * k, Z(0) - Z(t0), st.s, st.f, st.w);
  s += SV.text(X(r0) + 6, Z(t0 / 2) + 4, `placa base e=${P.t_base} (parcial)`, C, { size: 10.5, fill: C.mute });
  const hx0 = P.R_bar - P.D_hole / 2, hx1 = P.R_bar + P.D_hole / 2;
  for (const [p, za, zz, lab] of [["bot", t0, t1, `4b e=${P.t_bot}`], ["top", t2, t3, `4a e=${P.t_top}`]]) {
    st = g(p, C.fill2);
    s += SV.rect(X(r0), Z(zz), (hx0 - r0) * k, Z(za) - Z(zz), st.s, st.on ? C.band : C.fill2, st.w) + SV.rect(X(hx1), Z(zz), (Rd - hx1) * k, Z(za) - Z(zz), st.s, st.on ? C.band : C.fill2, st.w);
    s += SV.text(X(r0) + 6, (Z(za) + Z(zz)) / 2 + 4, lab, C, { size: 10.5, fill: st.on ? C.accent : C.ink, weight: st.on ? 600 : null });
  }
  if (rl.length) { const rr = rl[rl.length - 1]; st = g("rings", C.fill); s += SV.rect(X(rr - P.t_ring / 2), Z(t2), P.t_ring * k, Z(t1) - Z(t2), st.s, st.on ? C.band : C.fill, st.w) + SV.text(X(rr + P.t_ring / 2) + 4, Z(t1) - 8, `alma R${nf(rr)} e=${P.t_ring}`, C, { size: 10.5, fill: st.on ? C.accent : C.mute }); }
  st = g("ribs"); if (P.R_rib > r0) s += SV.rect(X(Math.max(r0, rl.length ? rl[rl.length - 1] + P.t_ring / 2 : r0)), Z(t2), (P.R_rib - Math.max(r0, rl.length ? rl[rl.length - 1] + P.t_ring / 2 : r0)) * k, Z(t1) - Z(t2), st.on ? C.accent : C.mute, st.on ? C.band : "none", st.on ? 2 : 0.8, "4 3");
  st = g("bars", C.fill);
  s += SV.rect(X(P.R_bar - P.D_bar / 2), Z(t3), P.D_bar * k, Z(t0) - Z(t3), st.s, st.on ? C.band : C.fill, st.w);
  const sb = P.weld_S * k;
  for (const [zf, sg] of [[t3, 1], [t0, -1]]) for (const xe of [X(P.R_bar - P.D_bar / 2), X(P.R_bar + P.D_bar / 2)]) { const dir = xe < X(P.R_bar) ? -1 : 1; s += SV.pgon([[xe, Z(zf)], [xe + dir * sb, Z(zf)], [xe, Z(zf) + sg * sb]], st.s, st.s, 1); }
  st = g("iface"); s += SV.line(X(r0), Z(t0), X(Rd), Z(t0), st.on ? C.accent : C.react, st.on ? 3 : 2, "6 3");
  s += SV.text(X(Rd) - 4, Z(t0) + 16, `grasa grafitada · μ ${nf(P.mu, 2)}`, C, { anchor: "end", size: 10.5, fill: st.on ? C.accent : C.react });
  const dimV = (z1, z2, t, x) => SV.line(x, Z(z1), x, Z(z2), C.mute, 1) + SV.line(x - 3, Z(z1), x + 3, Z(z1), C.mute, 1) + SV.line(x - 3, Z(z2), x + 3, Z(z2), C.mute, 1) + SV.text(x + 5, (Z(z1) + Z(z2)) / 2 + 4, t, C, { size: 10.5, fill: C.mute });
  s += dimV(t0, t1, nf(P.t_bot), X(Rd) + 8) + dimV(t1, t2, nf(P.gap), X(Rd) + 8) + dimV(t2, t3, nf(P.t_top), X(Rd) + 8) + dimV(t0, t3, nf(R.TD), X(Rd) + 40);
  s += SV.line(X(P.R_bar - P.D_bar / 2), Z(t3) - 14, X(P.R_bar + P.D_bar / 2), Z(t3) - 14, C.mute, 1) + SV.text(X(P.R_bar), Z(t3) - 18, `Ø${P.D_bar} · bisel ${P.weld_S}`, C, { anchor: "middle", size: 10.5, fill: C.mute });
  s += SV.line(X(P.R_bar), Z(t0) + 4, X(P.R_bar), Z(t3) - 4, C.mute, 0.8, "8 3 2 3");
  s += SV.text(14, 18, "DETALLE – BORDE DEL DISCO (corte por una barra)", C, { size: 12, weight: 600 });
  return s + "</svg>";
}

/* ---------- 3D (three.js r147) ---------- */
function Geo3D(host) {
  this.host = host; this.ok = !!window.THREE;
  if (!this.ok) return;
  try {
    this.ren = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  } catch (e) { this.ok = false; return; }
  this.ren.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  host.appendChild(this.ren.domElement);
  this.scene = new THREE.Scene();
  this.cam = new THREE.PerspectiveCamera(35, 1.6, 10, 40000);
  this.cam.position.set(2350, 1850, 2550);
  this.ctl = new THREE.OrbitControls(this.cam, this.ren.domElement);
  this.ctl.target.set(0, 120, 0); this.ctl.enableDamping = false; this.ctl.update();
  this.ctl.addEventListener("change", () => this.draw());
  this.scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 0.85));
  const dl = new THREE.DirectionalLight(0xffffff, 0.75); dl.position.set(2000, 4000, 1500); this.scene.add(dl);
  const dl2 = new THREE.DirectionalLight(0xffffff, 0.3); dl2.position.set(-2500, 1500, -2000); this.scene.add(dl2);
  this.grp = new THREE.Group(); this.scene.add(this.grp);
  this.parts = {}; this.topMode = "trans";
  new ResizeObserver(() => this.resize()).observe(host);
  this.resize();
}
Geo3D.prototype = {
  resize() { if (!this.ok) return; const w = this.host.clientWidth || 600, h = Math.max(280, Math.round(w * 0.62)); this.ren.setSize(w, h); this.cam.aspect = w / h; this.cam.updateProjectionMatrix(); this.draw(); },
  draw() { if (this.ok) this.ren.render(this.scene, this.cam); },
  mat(hex, part, opt) {
    const m = new THREE.MeshStandardMaterial(Object.assign({ color: hex, metalness: 0.25, roughness: 0.62 }, opt || {}));
    m.userData.base = hex; (this.parts[part] = this.parts[part] || []).push(m); return m;
  },
  add(geo, m, x, z, y) { const me = new THREE.Mesh(geo, m); me.position.set(x || 0, z || 0, -(y || 0)); this.grp.add(me); return me; },
  ringShape(ro, ri, holes) {
    const sh = new THREE.Shape(); sh.absarc(0, 0, ro, 0, Math.PI * 2, false);
    const h = new THREE.Path(); h.absarc(0, 0, ri, 0, Math.PI * 2, true); sh.holes.push(h);
    for (const [x, y, r] of holes || []) { const p = new THREE.Path(); p.absarc(x, y, r, 0, Math.PI * 2, true); sh.holes.push(p); }
    return sh;
  },
  extr(shape, depth, segs) { const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false, curveSegments: segs || 64 }); g.rotateX(-Math.PI / 2); return g; },
  build(R, C) {
    if (!this.ok) return;
    const P = R.P; this.parts = {};
    while (this.grp.children.length) { const o = this.grp.children.pop(); o.geometry && o.geometry.dispose(); }
    this.scene.background = new THREE.Color(C.bg);
    const t0 = P.t_base, t1 = t0 + P.t_bot, t2 = t1 + P.gap, t3 = t2 + P.t_top, Rd = P.D_disc / 2, rh = P.D_hub / 2;
    const holes = []; for (let i = 0; i < P.N_bar; i++) { const a = Math.PI / P.N_bar + 2 * Math.PI * i / P.N_bar; holes.push([P.R_bar * Math.cos(a), P.R_bar * Math.sin(a), P.D_hole / 2]); }
    this.add(new THREE.BoxGeometry(P.BX, P.t_base, P.BY), this.mat(0x8f9aa3, "base"), 0, t0 / 2, 0);
    this.add(this.extr(this.ringShape(Rd, rh, holes), P.t_bot), this.mat(0x6d8fb3, "bot"), 0, t0, 0);
    const mt = this.mat(0x7fa0c4, "top", { transparent: true, opacity: 0.32, depthWrite: false });
    this.topMesh = this.add(this.extr(this.ringShape(Rd, rh, holes), P.t_top), mt, 0, t2, 0);
    const mr = this.mat(0xc9a35a, "rings");
    for (const r of parseRings(P.rings)) this.add(this.extr(this.ringShape(r + P.t_ring / 2, r - P.t_ring / 2), P.gap), mr, 0, t1, 0);
    const mb = this.mat(0xd9b46e, "ribs");
    for (let i = 0; i < P.N_rib; i++) {
      const a = 2 * Math.PI * i / P.N_rib, L = P.R_rib - rh, rc = rh + L / 2;
      const me = this.add(new THREE.BoxGeometry(L, P.gap, P.t_rib), mb, rc * Math.cos(a), t1 + P.gap / 2, rc * Math.sin(a)); me.rotation.y = a;
    }
    const mbar = this.mat(0x3d4650, "bars"), gb = new THREE.CylinderGeometry(P.D_bar / 2, P.D_bar / 2, R.TD, 20);
    for (const [x, y] of holes) this.add(gb, mbar, x, t0 + R.TD / 2, y);
    this.add(new THREE.CylinderGeometry(rh, rh, R.TD, 40), this.mat(0x58626c, "hub"), 0, t0 + R.TD / 2, 0);
    this.add(new THREE.CylinderGeometry(P.D_piv / 2, P.D_piv / 2, t3 + 25, 32), this.mat(0xb8c0c7, "pivot"), 0, (t3 + 25) / 2, 0);
    // carga y radio efectivo
    const ml = this.mat(0xe06a3a, "load", { transparent: true, opacity: 0.18, depthWrite: false });
    this.add(new THREE.CylinderGeometry(P.D_load / 2, P.D_load / 2, 30, 64), ml, 0, t3 + 60, 0);
    const mcg = this.mat(0xc0392b, "load"); this.add(new THREE.SphereGeometry(35, 20, 14), mcg, P.e, t3 + 120, 0);
    const mi = this.mat(0x13a08d, "iface"), ti = new THREE.TorusGeometry(P.r_eff * 1000, 9, 8, 96); ti.rotateX(Math.PI / 2); this.add(ti, mi, 0, t0 + 2, 0);
    // accionamiento
    const za = t0 + P.h_axis;
    for (const sx of [1, -1]) {
      const yb = -sx * P.R_bar * Math.sin(R.th), yE = yb - sx * P.eye_off, yP = -sx * R.Ybrk, xc = sx * P.X_cyl;
      this.add(new THREE.BoxGeometry(P.rail_w, P.rail_h, 850), this.mat(0x9aa4ad, "rail"), xc, t0 + P.rail_h / 2, 0);
      const mbk = this.mat(0x7c8792, "bracket"), hc = za + 70 - t0;
      for (const sd of [1, -1]) this.add(new THREE.BoxGeometry(P.t_cheek, hc, P.L_cheek), mbk, xc + sd * (P.gap_cheek / 2 + P.t_cheek / 2), t0 + hc / 2, yP);
      this.add(new THREE.BoxGeometry(P.gap_cheek + 2 * P.t_cheek, hc, 40), mbk, xc, t0 + hc / 2, yP - sx * (P.L_cheek / 2 + 20));
      const pin = new THREE.CylinderGeometry(P.D_pin / 2, P.D_pin / 2, P.gap_cheek + 2 * P.t_cheek + 40, 20); pin.rotateZ(Math.PI / 2); this.add(pin, mbk, xc, za, yP);
      const mc = this.mat(0x2f5fb3, "cyl");
      const body = new THREE.CylinderGeometry(70, 70, 300, 32); body.rotateX(Math.PI / 2); this.add(body, mc, xc, za, yP + sx * 220);
      const Lr = Math.abs(yE - (yP + sx * 370)), rod = new THREE.CylinderGeometry(P.D_rod / 2, P.D_rod / 2, Lr, 24); rod.rotateX(Math.PI / 2);
      this.add(rod, this.mat(0xc9d1d8, "cyl", { metalness: 0.6, roughness: 0.3 }), xc, za, (yE + yP + sx * 370) / 2);
      const shoeH = za + 70 - t0, ys = yb + sx * 20 - sx * 150;
      this.add(new THREE.BoxGeometry(130, shoeH, 300), this.mat(0xb08a52, "shoe"), sx * (P.shoe_x0 + 65), t0 + shoeH / 2, ys);
      this.add(new THREE.BoxGeometry(P.pawl_L, P.pawl_h, P.pawl_b), this.mat(0xe0a63c, "pawl"), sx * (P.pawl_tip + P.pawl_L / 2), za, yb - sx * P.pawl_b / 2);
    }
    this.setTop(this.topMode);
    this.highlight(this.hl || []);
  },
  setTop(mode) {
    this.topMode = mode; if (!this.topMesh) return;
    this.topMesh.visible = mode !== "hide";
    const m = this.topMesh.material; m.transparent = mode === "trans"; m.opacity = mode === "trans" ? 0.32 : 1; m.depthWrite = mode !== "trans"; m.needsUpdate = true;
    this.draw();
  },
  highlight(parts) {
    this.hl = parts;
    if (!this.ok) return;
    for (const [p, ms] of Object.entries(this.parts)) for (const m of ms) {
      const on = parts.includes(p);
      m.color.setHex(on ? 0xff7a1a : m.userData.base);
      m.emissive && m.emissive.setHex(on ? 0x5a2200 : 0x000000);
    }
    this.draw();
  },
  view(name) {
    const v = { iso: [2350, 1850, 2550], top: [0, 3900, 1], front: [0, 380, 3500], side: [3500, 380, 0] }[name];
    this.cam.position.set(...v); this.ctl.target.set(0, 120, 0); this.ctl.update(); this.draw();
  },
};
```

### tt300/app/ui.js
`tt300/app/ui.js` — 376 líneas

```javascript
(function () {
  const DEF = defaults();
  const KEY = "tt300b-params-v1";
  let P = Object.assign({}, DEF);
  try { const s = JSON.parse(localStorage.getItem(KEY) || "null"); if (s) for (const k in s) if (k in DEF && typeof s[k] === typeof DEF[k]) P[k] = s[k]; } catch (e) { /* sin almacenamiento */ }
  let R = null, V = [], F = {}, plate = "bot", field = "vm", deformed = 0, timer = null, hl = [], g3 = null;
  const $ = (id) => document.getElementById(id);
  const dlP = window.claude && window.claude.use ? window.claude.use("downloads").catch(() => null) : Promise.resolve(null);

  function pal(print) {
    if (print) return { ink: "#000000", mute: "#444444", line: "#8a8a8a", grid: "#dddddd", bg: "#ffffff", accent: "#1f4fbf", force: "#b3361f", react: "#0d776a", good: "#2e7a33", warn: "#a8700f", bad: "#c22a2a", fill: "#eef0ee", fill2: "#dcdfdc", cyl: "#d6dceb", shoe: "#efe2cc", pawl: "#f3d49b", band: "rgba(36,83,196,0.08)", paper: "#ffffff", font: "Helvetica, Arial, sans-serif" };
    const cs = getComputedStyle(document.documentElement), g = (n) => cs.getPropertyValue("--" + n).trim();
    return { ink: g("ink"), mute: g("mute"), line: g("line"), grid: g("grid"), bg: g("panel"), accent: g("accent"), force: g("force"), react: g("react"), good: g("good"), warn: g("warn"), bad: g("bad"), fill: g("fill"), fill2: g("fill2"), cyl: g("cyl"), shoe: g("shoe"), pawl: g("pawl"), band: g("band"), paper: "#ffffff", font: "IBM Plex Sans, Segoe UI, sans-serif" };
  }
  const stOf = (v) => (v.kind === "pass" ? (v.fu <= 1 ? "ok" : "no") : v.fu <= 0.9 ? "ok" : v.fu <= 1 ? "wa" : "no");
  const stTxt = { ok: "OK", wa: "Monitoreo", no: "No cumple" };
  function toast(msg) { const t = $("toast"); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), 3200); }

  /* ---------------- formulario ---------------- */
  function buildForm() {
    const f = $("pform"); let html = "";
    PARAM_GROUPS.forEach((g, gi) => {
      html += `<details class="grp" ${gi < 4 && window.innerWidth > 980 ? "open" : ""}><summary>${g.t}</summary><div class="grp-body">`;
      for (const [id, lab, unit, dv, step] of g.items) {
        const isTxt = typeof dv === "string";
        html += `<div class="prow" data-row="${id}"><label for="p_${id}">${lab}<small>${unit} · Rev.0: ${isTxt ? dv : nf(dv, step && step < 1 ? (step < 0.01 ? 3 : 2) : 0)}</small></label>` +
          `<input id="p_${id}" name="${id}" ${isTxt ? 'type="text" class="txt"' : `type="number" step="${step}" inputmode="decimal"`} value="${P[id]}"></div>`;
      }
      html += "</div></details>";
    });
    f.innerHTML = html;
    f.addEventListener("input", (ev) => {
      const el = ev.target; if (!el.name) return;
      const dv = DEF[el.name];
      if (typeof dv === "string") P[el.name] = el.value;
      else { const v = parseFloat(String(el.value).replace(",", ".")); if (!isFinite(v)) return; P[el.name] = v; }
      markChanged(); schedule();
    });
    f.addEventListener("submit", (e) => e.preventDefault());
    f.addEventListener("focusin", (ev) => { if (ev.target.name) focusParam(ev.target.name); });
    markChanged();
  }
  function markChanged() {
    let n = 0;
    for (const k in DEF) { const row = document.querySelector(`[data-row="${k}"]`); const ch = String(P[k]).replace(/\s/g, "") !== String(DEF[k]).replace(/\s/g, ""); if (ch) n++; if (row) row.classList.toggle("chg", ch); }
    const w = $("issuedWarn"); w.hidden = n === 0; w.textContent = `Hay ${n} parámetro(s) distinto(s) del diseño emitido: los planos Rev. 0 no los reflejan. Use el plano paramétrico para documentar esta variante.`;
    try { localStorage.setItem(KEY, JSON.stringify(P)); } catch (e) { /* sin almacenamiento */ }
  }
  $("reset").addEventListener("click", () => { P = Object.assign({}, DEF); for (const k in DEF) { const el = $("p_" + k); if (el) el.value = DEF[k]; } markChanged(); recompute(); toast("Valores de diseño Rev. 0 restablecidos"); });

  function validate() {
    const errs = [];
    if (P.N_rib < 3 || P.N_rib > 36) errs.push("N° de nervios entre 3 y 36");
    if (P.N_bar < 8 || P.N_bar > 120) errs.push("N° de barras entre 8 y 120");
    if (P.R_bar + P.D_bar / 2 >= P.D_disc / 2) errs.push("Las barras deben quedar dentro del disco");
    if (P.D_hub >= P.D_disc) errs.push("Cubo mayor que el disco");
    if (P.D_bore >= P.D_hub) errs.push("Buje mayor que el cubo");
    if (P.weld_S <= 3) errs.push("Bisel de soldadura > 3 mm");
    for (const k in DEF) if (typeof DEF[k] === "number" && !(P[k] > 0) && k !== "e") errs.push(`${k} debe ser positivo`);
    return errs;
  }
  function schedule() { document.querySelector("main").classList.add("busy"); clearTimeout(timer); timer = setTimeout(recompute, 380); }

  function recompute() {
    document.querySelector("main").classList.remove("busy");
    const errs = validate();
    if (errs.length) { $("verdict").className = "verdict no"; $("verdict").innerHTML = `<strong>Parámetros inválidos</strong><span>${errs.join(" · ")}</span>`; return; }
    R = compute(P); F = {};
    try { F.bot = runDisc(P, "bot"); F.top = runDisc(P, "top"); } catch (e) { F.discErr = e.message; }
    try { F.pawl = runPawl(P, R); } catch (e) { F.pawlErr = e.message; }
    V = verifs(R, F);
    render();
  }

  /* ---------------- render ---------------- */
  function render() {
    const C = pal(false), d = R.d, worst = V.filter((v) => v.kind !== "pass").reduce((a, b) => (b.fu > a.fu ? b : a));
    const fails = V.filter((v) => stOf(v) === "no"), mons = V.filter((v) => stOf(v) === "wa"), dry = R.cases[3];
    // veredicto
    let cls = "ok", head = "Gira con certeza en el rango acero/acero engrasado", body = `Cada cilindro necesita ${nf(d.Fc)} kN (${nf(d.p)} bar) con μ = ${nf(P.mu, 2)} y r = ${nf(P.r_eff, 2)} m; dispone de ${nf(R.Fmax)} kN a ${nf(P.p_relief)} bar → FS = ${nf(d.FS, 2)}. Elementos: FU máx ${nf(worst.fu, 2)} (${worst.grp}).`;
    if (d.FS < 1) { cls = "no"; head = "El accionamiento NO vence la fricción de diseño"; body = `Se requieren ${nf(d.Fc)} kN por cilindro (${nf(d.p)} bar) y el alivio entrega ${nf(R.Fmax)} kN.`; }
    else if (fails.length) { cls = "no"; head = `${fails.length} verificación(es) no cumplen`; body = fails.map((v) => `${v.grp}: ${v.el} (FU ${nf(v.fu, 2)})`).join(" · "); }
    else if (d.FS < 1.25 || mons.length) { cls = "wa"; head = "Cumple con margen reducido"; body = (d.FS < 1.25 ? `FS del accionamiento ${nf(d.FS, 2)} < 1,25. ` : "") + mons.map((v) => `${v.grp}: ${v.el} (FU ${nf(v.fu, 2)})`).join(" · "); }
    $("verdict").className = "verdict " + cls;
    $("verdict").innerHTML = `<strong>${head}</strong><span>${body}</span><span class="note">Acero seco (μ ${nf(P.mu_dry, 2)}): ${dry.FS < 1 ? `no gira, requiere ${nf(dry.p)} bar &gt; ${nf(P.p_relief)} bar. Lubricación obligatoria.` : `gira con FS ${nf(dry.FS, 2)}.`}</span>`;
    // chips
    const chip = (c, t, v) => `<span class="chip ${c}"><span class="dot"></span>${t} <b>${v}</b></span>`;
    $("chips").innerHTML = chip(d.FS >= 1.25 ? "ok" : d.FS >= 1 ? "wa" : "no", "FS accionamiento", nf(d.FS, 2)) + chip(worst.fu <= 0.9 ? "ok" : worst.fu <= 1 ? "wa" : "no", "FU máx", nf(worst.fu, 2)) +
      chip(dry.FS < 1 ? "wa" : "ok", "Acero seco", dry.FS < 1 ? "no gira" : "gira") + (F.bot ? chip(Math.abs(F.bot.Fapp - F.bot.Rsum) / F.bot.Fapp < 1e-3 ? "ok" : "no", "FEA equilibrio", "Σ OK") : chip("no", "FEA", "error"));
    // KPIs
    const k = (c, l, v, s) => `<div class="kpi ${c}"><span class="l">${l}</span><span class="v">${v}</span><span class="s">${s}</span></div>`;
    const plMax = F.bot ? Math.max(F.bot.vmMax, F.top.vmMax) : NaN;
    $("kpis").innerHTML =
      k(d.FS >= 1.25 ? "ok" : d.FS >= 1 ? "wa" : "no", "Fuerza por cilindro", `${nf(d.Fc)} kN`, `${nf(d.tf, 1)} tf · ${nf(d.p)} bar (diseño)`) +
      k("", "Capacidad por cilindro", `${nf(R.Fmax)} kN`, `Ø${nf(P.D_piston)} a ${nf(P.p_relief)} bar · FS ${nf(d.FS, 2)}`) +
      k("", "Fricción máx. vencible <span class=\"nt\">μ</span>", nf(R.muMax(R.r_eff, P.p_relief), 3), `r ${nf(R.r_eff, 2)} m · ${nf(R.muMax(R.r_max, P.p_relief), 3)} con r ${nf(R.r_max, 2)}`) +
      k("", "Par resistente", `${nf(d.T)} kN·m`, `N = ${nf(R.N)} kN · 2 × ${nf(d.Fb)} kN × ${nf(R.a / 1000, 3)} m`) +
      k(worst.fu <= 0.9 ? "ok" : worst.fu <= 1 ? "wa" : "no", "FU máximo", nf(worst.fu, 2), `${worst.grp}: ${worst.el}`) +
      k(plMax <= 0.6 * P.Fy ? "ok" : "no", "Placas 4a/4b (FEA)", `${nf(plMax, 1)} MPa`, `σvm máx · admisible ${nf(0.6 * P.Fy)} MPa`);
    // casos
    $("casesT").innerHTML = `<table class="t"><thead><tr><th>Caso</th><th class="n"><span class="nt">μ</span></th><th class="n"><span class="nt">r m</span></th><th class="n">T kN·m</th><th class="n">F barra</th><th class="n">F cil kN</th><th class="n">p bar</th><th class="n">FS</th><th></th></tr></thead><tbody>` +
      R.cases.map((c) => { const s = c.FS >= 1.25 ? "ok" : c.FS >= 1 ? "wa" : "no"; return `<tr class="${c.key === "dis" ? "hl" : ""}"><td>${c.name}</td><td class="n">${nf(c.mu, 2)}</td><td class="n">${nf(c.r, 3)}</td><td class="n">${nf(c.T)}</td><td class="n">${nf(c.Fb)}</td><td class="n">${nf(c.Fc)}</td><td class="n">${nf(c.p)}</td><td class="n">${nf(c.FS, 2)}</td><td><span class="st ${s}">${c.FS >= 1.25 ? "Gira" : c.FS >= 1 ? "Al límite" : "No gira"}</span></td></tr>`; }).join("") + "</tbody></table>";
    $("mumaxT").textContent = `μ máximo que vencen los cilindros: ${nf(R.muMax(R.r_u, P.p_relief), 3)} (r ${nf(R.r_u, 3)}) · ${nf(R.muMax(R.r_eff, P.p_relief), 3)} (r ${nf(R.r_eff, 2)}) · ${nf(R.muMax(R.r_max, P.p_relief), 3)} (r ${nf(R.r_max, 2)}) a ${nf(P.p_relief)} bar; a ${nf(P.p_alarm)} bar: ${nf(R.muMax(R.r_eff, P.p_alarm), 3)} (r ${nf(R.r_eff, 2)}).`;
    const Tf = P.mu * R.N * P.r_eff;
    $("eqs").innerHTML = [
      `N = W + W_disco = ${nf(R.W, 1)} + ${nf(R.Wd, 2)} = ${nf(R.N, 1)} kN`,
      `T_f = μ·N·r = ${nf(P.mu, 2)} × ${nf(R.N, 1)} × ${nf(P.r_eff, 3)} = ${nf(Tf, 1)} kN·m`,
      `T_piv = μb·H·r = ${nf(P.mu_piv, 2)} × ${nf(P.H_frac * R.W, 1)} × ${nf(P.D_piv / 2000, 3)} = ${nf(R.Tpiv, 2)} kN·m`,
      `a = R_b·cos(180°/N_b) = ${nf(P.R_bar)} × cos ${nf(180 / P.N_bar, 2)}° = ${nf(R.a, 1)} mm`,
      `F_barra = T/(2a) = ${nf(d.T, 1)} / (2 × ${nf(R.a / 1000, 4)}) = ${nf(d.Fb, 1)} kN`,
      `K = (1 + 2·μg·Δ/Lg)/ηc = (1 + 2 × ${nf(P.mu_g, 2)} × ${nf(R.Delta, 1)}/${nf(P.Lg)}) / ${nf(P.eta_c, 2)} = ${nf(R.K, 3)}`,
      `F_cil = K·F_barra = ${nf(R.K, 3)} × ${nf(d.Fb, 1)} = ${nf(d.Fc, 1)} kN (${nf(d.tf, 1)} tf)`,
      `p = F_cil/A = ${nf(d.Fc * 1e3)} N / ${nf(R.A)} mm² = ${nf(d.p)} bar`,
      `FS = A·p_alivio / F_cil = ${nf(R.Fmax, 1)} / ${nf(d.Fc, 1)} = ${nf(d.FS, 2)}`,
    ].map((t) => `<span>${t}</span>`).join("");
    $("hyps").innerHTML = [
      `Carga WLL ${nf(P.W_tf)} tf con CG a e ≤ ${nf(P.e)} mm del pivote; carga solo sobre parrilla de Ø${nf(P.D_load)}.`,
      `Interfaz plana anular acero/acero R ${nf(P.D_disc / 2)} / r ${nf(P.D_bore / 2)} mm con grasa grafitada NLGI 2 (≥10 % grafito). μ estático de diseño ${nf(P.mu, 2)}: límite superior de 0,10–0,20 para acero engrasado.`,
      `Radio efectivo: uniforme ${nf(R.r_u, 3)} m. La distribución lineal por excentricidad no cambia el par (∫x·r dA = 0); el diseño usa ${nf(P.r_eff, 2)} m para cubrir la concentración de presión hacia el borde por flexión del disco.`,
      `Dos cilindros simultáneos (válvula de bloqueo): las fuerzas sobre las barras forman un par puro; el pivote no recibe resultante en operación normal.`,
      `Pérdidas por fricción carro/guía (μg ${nf(P.mu_g, 2)}) debidas a la excentricidad Δ entre eje del cilindro y barra, y rendimiento de sellos ηc ${nf(P.eta_c, 2)}.`,
      `La cadena de empuje (barra, soldadura, trinquete, guía, ménsula, pasador, vástago) se verifica a la fuerza de calado ${nf(R.Fmax)} kN: si el disco se traba, abre la válvula antes de que falle un elemento.`,
      `Placas del disco por FEA (Mindlin MITC4): almas, nervios y barras como apoyos rígidos; plancha inferior con q_max ${nf(R.q_max, 2)} MPa uniforme (conservador).`,
    ].map((t) => `<li>${t}</li>`).join("");
    // cilindros
    $("dgPlan").innerHTML = dgPlan(R, C);
    $("dgStroke").innerHTML = dgStroke(R, C);
    $("dgMu").innerHTML = dgMu(R, C);
    $("dgBreak").innerHTML = dgBreak(R, C);
    const at = (c, t) => { const a = P.R_bar * Math.cos(t), Kt = (1 + 2 * P.mu_g * (P.X_cyl - a) / P.Lg) / P.eta_c; return Kt * c.T / (2 * a / 1000); };
    const posn = [["Recorrido libre (0–" + nf(P.free) + " mm)", null], [`Toma la barra (θ = −${nf(180 / P.N_bar, 1)}°)`, -R.th], ["Centro (θ = 0°)", 0], [`Suelta la barra (θ = +${nf(180 / P.N_bar, 1)}°)`, R.th]];
    const cs3 = R.cases.slice(0, 3);
    $("pistonT").innerHTML = `<table class="t"><thead><tr><th>Posición en la carrera</th>${cs3.map((c) => `<th class="n">${c.name.split(" – ")[0]}<br>kN / bar</th>`).join("")}</tr></thead><tbody>` +
      posn.map(([n, t]) => `<tr class="${t === -R.th ? "hl" : ""}"><td>${n}</td>${cs3.map((c) => { if (t === null) return `<td class="n">≈ 0 / –</td>`; const f = at(c, t); return `<td class="n">${nf(f)} / ${nf(f * 1e3 / R.A * 10)}</td>`; }).join("")}</tr>`).join("") +
      `<tr><td>Alarma (detener y relubricar)</td><td class="n" colspan="3">${nf(R.Falarm)} kN / ${nf(P.p_alarm)} bar</td></tr>` +
      `<tr><td>Alivio = fuerza de calado</td><td class="n" colspan="3">${nf(R.Fmax)} kN / ${nf(P.p_relief)} bar</td></tr></tbody></table>` +
      `<h4>Reacciones por cilindro</h4><table class="t"><thead><tr><th>Elemento</th><th class="n">Diseño kN</th><th class="n">Calado kN</th></tr></thead><tbody>` +
      [["Ménsula pos 2 (pasador Ø" + P.D_pin + ")", d.Fc, R.Fmax], ["Pasador: cada plano de corte", d.Fc / 2, R.Fmax / 2], ["Barra 4f (trinquete)", d.Fb, R.Fmax / R.K], ["Guía pos 22, cada reacción R", d.Fb * R.Delta / P.Lg, R.Fmax * R.Delta / P.Lg], ["Pivote (2 cilindros en par)", 0, 0], ["Pivote (accidental, 1 cilindro – bloqueado por válvula)", d.Fc, R.Fmax]]
        .map(([n, a, b]) => `<tr><td>${n}</td><td class="n">${nf(a)}</td><td class="n">${nf(b)}</td></tr>`).join("") + "</tbody></table>";
    // diagramas
    $("dgShoe").innerHTML = dgShoe(R, C);
    $("dgBar").innerHTML = dgBar(R, C);
    $("dgPin").innerHTML = dgPin(R, C);
    $("pathT").innerHTML = `<table class="t"><thead><tr><th>Tramo del camino de carga</th><th class="n">Diseño</th><th class="n">Calado</th></tr></thead><tbody>` +
      [["Presión en cilindro", `${nf(d.p)} bar`, `${nf(P.p_relief)} bar`], ["Vástago → pasador del carro", `${nf(d.Fc)} kN`, `${nf(R.Fmax)} kN`], ["Carro → guía (2 reacciones)", `${nf(d.Fb * R.Delta / P.Lg)} kN c/u`, `${nf(R.Fmax * R.Delta / P.Lg)} kN c/u`],
        ["Trinquete → barra 4f", `${nf(d.Fb)} kN`, `${nf(R.Fmax / R.K)} kN`], ["Barra → planchas 4a/4b (aplast.)", `${nf(d.Fb / 2)} kN c/u`, `${nf(R.Fmax / 2)} kN c/u`], ["Par motor sobre el disco", `${nf(d.T)} kN·m`, `${nf(R.Fmax / R.K * 2 * R.a / 1000)} kN·m`],
        ["Cuerpo cilindro → ménsula → placa base", `${nf(d.Fc)} kN`, `${nf(R.Fmax)} kN`], ["Interfaz de giro (fricción a vencer)", `${nf(d.Tf)} kN·m`, "–"]]
        .map(([a, b, c]) => `<tr><td>${a}</td><td class="n">${b}</td><td class="n">${c}</td></tr>`).join("") + "</tbody></table>" +
      `<p class="note">En el calado el pistón no vence la fricción: el disco no gira y toda la fuerza del alivio queda en la cadena de empuje. Por eso los elementos se verifican a ese valor.</p>`;
    // verificaciones
    $("verT").innerHTML = `<table class="t"><thead><tr><th>Grupo</th><th>Elemento</th><th>Fórmula</th><th class="n">Demanda</th><th class="n">Capacidad</th><th>FU</th><th>Estado</th><th>Referencia</th></tr></thead><tbody>` +
      V.map((v) => { const s = stOf(v), c = s === "ok" ? "var(--good)" : s === "wa" ? "var(--warn)" : "var(--bad)"; const dd = Math.abs(v.dem) < 20 ? 2 : 1;
        return `<tr><td>${v.grp}</td><td>${v.el}</td><td class="f">${v.formula}</td><td class="n">${nf(v.dem, dd)} ${v.unit}</td><td class="n">${nf(v.cap, Math.abs(v.cap) < 20 ? 2 : 0)} ${v.unit}</td><td><div class="fu"><span class="bar"><i style="width:${Math.min(100, v.fu * 100).toFixed(1)}%;background:${c}"></i></span><b class="n" style="font-family:var(--f-mono)">${nf(v.fu, 2)}</b></div></td><td><span class="st ${s}">${v.kind === "pass" ? (s === "ok" ? "Cumple" : "No cumple") : stTxt[s]}</span></td><td class="note">${v.ref}</td></tr>`; }).join("") + "</tbody></table>";
    renderFEA();
    renderSheet();
    renderGeo(true);
  }

  /* ---------------- geometría ---------------- */
  const LABEL = {}; for (const g of PARAM_GROUPS) for (const it of g.items) LABEL[it[0]] = it[1];
  function focusParam(name) {
    hl = PART_OF[name] || [];
    $("editing").innerHTML = hl.length ? `Editando <b>${LABEL[name]}</b> → resaltado: ${hl.map((p) => PART_NAME[p]).join(", ")}` : `Editando <b>${LABEL[name]}</b> (parámetro de material o de cálculo, sin elemento asociado)`;
    renderGeo(false);
  }
  function renderGeo(rebuild) {
    if (!R) return;
    const C = pal(false);
    $("gPlan").innerHTML = geoPlan(R, C, hl);
    $("gElev").innerHTML = geoElev(R, C, hl);
    $("gEdge").innerHTML = geoEdge(R, C, hl);
    if (!g3) { g3 = new Geo3D($("g3d")); if (!g3.ok) $("g3note").textContent = "Este navegador no permite WebGL: se muestran solo las vistas 2D."; }
    if (g3.ok) { if (rebuild) g3.build(R, C); g3.highlight(hl); }
  }
  document.querySelectorAll("[data-v3]").forEach((b) => b.addEventListener("click", () => { document.querySelectorAll("[data-v3]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); g3 && g3.ok && g3.view(b.dataset.v3); }));
  document.querySelectorAll("[data-top]").forEach((b) => b.addEventListener("click", () => { document.querySelectorAll("[data-top]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); g3 && g3.ok && g3.setTop(b.dataset.top); }));

  /* ---------------- FEA ---------------- */
  const STOPS = [[0, [29, 63, 143]], [0.2, [44, 127, 184]], [0.4, [65, 182, 164]], [0.6, [166, 217, 106]], [0.75, [253, 211, 77]], [0.88, [240, 138, 53]], [1, [198, 40, 40]]];
  function cmap(t) {
    t = Math.max(0, Math.min(1, t));
    for (let i = 1; i < STOPS.length; i++) if (t <= STOPS[i][0]) { const [a, ca] = STOPS[i - 1], [b, cb] = STOPS[i], u = (t - a) / (b - a); return `rgb(${ca.map((v, k) => Math.round(v + (cb[k] - v) * u)).join(",")})`; }
    return "rgb(198,40,40)";
  }
  const rampCSS = "linear-gradient(90deg," + STOPS.map(([t, c]) => `rgb(${c.join(",")}) ${t * 100}%`).join(",") + ")";
  function elemVal(f, e, fld) { if (fld === "vm") return f.res.el[e].vm; const en = f.model.elems[e]; return en.reduce((s, k) => s + Math.abs(f.res.w[k]), 0) / 4; }
  function drawDisc(cv, f, fld, C) {
    const ctx = cv.getContext("2d"), W = cv.width, H = cv.height, m = f.model, Pp = P, Rd = Pp.D_disc / 2, sc = (Math.min(W, H) / 2 - 40) / Rd, cx = W / 2, cy = H / 2 + 10;
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    let vmax = 0; const vals = new Float64Array(m.elems.length);
    for (let e = 0; e < m.elems.length; e++) { vals[e] = elemVal(f, e, fld); vmax = Math.max(vmax, vals[e]); }
    vmax = vmax || 1;
    for (let s = 0; s < Pp.N_rib; s++) {
      const ca = Math.cos(s * m.alpha), sa = Math.sin(s * m.alpha);
      for (let e = 0; e < m.elems.length; e++) {
        ctx.beginPath();
        m.elems[e].forEach((k, i) => { const [x, y] = m.nodes[k], X = cx + (x * ca - y * sa) * sc, Y = cy - (x * sa + y * ca) * sc; i ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); });
        ctx.closePath(); ctx.fillStyle = cmap(vals[e] / vmax); ctx.fill(); ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = 0.6; ctx.stroke();
      }
    }
    ctx.strokeStyle = C.ink; ctx.lineWidth = 1.4; ctx.globalAlpha = 0.85;
    const circ = (r, w, dash) => { ctx.setLineDash(dash || []); ctx.lineWidth = w; ctx.beginPath(); ctx.arc(cx, cy, r * sc, 0, 2 * Math.PI); ctx.stroke(); };
    circ(Rd, 2); circ(Pp.D_hub / 2, 1.4); m.rings.forEach((r) => circ(r, 1.2, [6, 4]));
    if (m.which === "top") circ(Pp.D_load / 2, 1, [2, 4]);
    ctx.setLineDash([6, 4]);
    for (let s = 0; s < Pp.N_rib; s++) { const a = s * m.alpha; ctx.beginPath(); ctx.moveTo(cx + Pp.D_hub / 2 * Math.cos(a) * sc, cy - Pp.D_hub / 2 * Math.sin(a) * sc); ctx.lineTo(cx + Pp.R_rib * Math.cos(a) * sc, cy - Pp.R_rib * Math.sin(a) * sc); ctx.stroke(); }
    ctx.setLineDash([]);
    for (let i = 0; i < Pp.N_bar; i++) { const a = Math.PI / Pp.N_bar + 2 * Math.PI * i / Pp.N_bar; ctx.beginPath(); ctx.arc(cx + Pp.R_bar * Math.cos(a) * sc, cy - Pp.R_bar * Math.sin(a) * sc, Pp.D_bar / 2 * sc, 0, 2 * Math.PI); ctx.stroke(); }
    ctx.globalAlpha = 1;
    if (fld === "vm") { const [r, t] = f.maxAt, a = t * Math.PI / 180, X = cx + r * Math.cos(a) * sc, Y = cy - r * Math.sin(a) * sc; ctx.strokeStyle = C.ink; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(X, Y, 9, 0, 2 * Math.PI); ctx.stroke(); ctx.fillStyle = C.ink; ctx.font = `600 18px ${C.font}`; ctx.fillText(`máx ${nf(f.vmMax, 1)} MPa`, X + 12, Y - 10); }
    ctx.fillStyle = C.ink; ctx.font = `600 20px ${C.font}`; ctx.textAlign = "left";
    ctx.fillText(`${m.which === "bot" ? "Plancha inferior 4b" : "Plancha superior 4a"} · ${fld === "vm" ? "σ von Mises (MPa)" : "flecha relativa |w| (mm)"}`, 14, 26);
    ctx.font = `15px ${C.font}`; ctx.fillStyle = C.mute;
    ctx.fillText(`q = ${nf(m.which === "bot" ? R.q_max : R.q_top, 2)} MPa ${m.which === "bot" ? "(contacto máx., uniforme)" : `en Ø${nf(Pp.D_load)}`} · t = ${nf(m.t)} mm`, 14, 48);
    cv._map = { cx, cy, sc, f, fld, vmax };
    return vmax;
  }
  function drawPawl(cv, f, C, defm) {
    const ctx = cv.getContext("2d"), W = cv.width, H = cv.height;
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    const sc = Math.min((W - 140) / (f.L + 70), (H - 150) / (f.b + 60)), ox = 70 + 45 * sc, oy = H - 70 - 25 * sc;
    const X = (x) => ox + x * sc, Y = (y) => oy - y * sc;
    const ds = defm ? 0.06 * f.L / Math.max(f.dmax, 1e-9) : 0;
    ctx.fillStyle = C.fill2; ctx.fillRect(X(f.Xm), Y(f.b + 20), (f.L + 30 - f.Xm) * sc, (f.b + 40) * sc);
    ctx.fillStyle = C.bg; ctx.fillRect(X(f.Xm), Y(f.b + 0.5), (f.L + 31 - f.Xm) * sc, (f.b + 1) * sc);
    ctx.fillStyle = C.mute; ctx.font = `14px ${C.font}`; ctx.fillText("carro pos 10 (alojamiento)", X(f.Xm) + 6, Y(f.b + 20) + 16);
    let vmax = 0; for (const e of f.res.el) vmax = Math.max(vmax, e.vm);
    const vcap = Math.min(vmax, (P.Fy_pawl / P.Nd) * 1.25);
    f.elems.forEach((en, i) => {
      ctx.beginPath();
      en.forEach((k, j) => { const x = f.nodes[k][0] + ds * f.res.u[2 * k], y = f.nodes[k][1] + ds * f.res.u[2 * k + 1]; j ? ctx.lineTo(X(x), Y(y)) : ctx.moveTo(X(x), Y(y)); });
      ctx.closePath(); ctx.fillStyle = cmap(f.res.el[i].vm / vcap); ctx.fill(); ctx.strokeStyle = ctx.fillStyle; ctx.lineWidth = 0.5; ctx.stroke();
    });
    ctx.strokeStyle = C.ink; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.arc(X(f.Xs), Y(f.Ys), (P.D_bar / 2) * sc, 0, 2 * Math.PI); ctx.stroke();
    ctx.fillStyle = C.mute; ctx.fillText(`barra 4f Ø${P.D_bar}`, X(f.Xs) - 30, Y(f.Ys) - (P.D_bar / 2) * sc - 8);
    ctx.setLineDash([6, 4]); ctx.beginPath(); ctx.moveTo(X(f.Xm), Y(-25)); ctx.lineTo(X(f.Xm), Y(f.b + 30)); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.ink; ctx.fillText("boca del carro", X(f.Xm) + 4, Y(-18));
    ctx.fillStyle = C.react;
    for (const k of f.sup) { const [x, y] = f.nodes[k], up = y < 1; ctx.beginPath(); ctx.moveTo(X(x), Y(y)); ctx.lineTo(X(x) - 4, Y(y) + (up ? 8 : -8)); ctx.lineTo(X(x) + 4, Y(y) + (up ? 8 : -8)); ctx.fill(); }
    ctx.strokeStyle = C.force; ctx.fillStyle = C.force; ctx.lineWidth = 2;
    const step = Math.max(1, Math.floor(f.loads.length / 7));
    f.loads.forEach(([k], i) => { if (i % step) return; const [x, y] = f.nodes[k]; ctx.beginPath(); ctx.moveTo(X(x), Y(y) - 30); ctx.lineTo(X(x), Y(y) - 4); ctx.stroke(); ctx.beginPath(); ctx.moveTo(X(x), Y(y)); ctx.lineTo(X(x) - 4, Y(y) - 9); ctx.lineTo(X(x) + 4, Y(y) - 9); ctx.fill(); });
    ctx.fillStyle = C.ink; ctx.font = `600 20px ${C.font}`;
    ctx.fillText(`σ von Mises (MPa) · F = ${nf(R.Fmax)} kN en el asiento R${P.seat_R}${defm ? ` · deformada ×${nf(ds, 0)}` : ""}`, 14, 26);
    ctx.font = `14px ${C.font}`; ctx.fillStyle = C.mute; ctx.fillText(`escala de color saturada en ${nf(vcap)} MPa (1,25 × admisible); picos locales de contacto hasta ${nf(vmax)} MPa`, 14, 46);
    cv._map = { X, Y, sc, ox, oy, f };
    return vcap;
  }
  function renderFEA() {
    const C = pal(false);
    document.querySelectorAll("[data-plate]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.plate === plate)));
    document.querySelectorAll("[data-field]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.field === field)));
    document.querySelectorAll("[data-def]").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.def === deformed)));
    $("ramp1").style.background = rampCSS; $("ramp2").style.background = rampCSS;
    if (F.discErr) { $("feaDiscN").textContent = "Error en el modelo del disco: " + F.discErr; }
    else {
      const f = F[plate], vmax = drawDisc($("cvDisc"), f, field, C);
      $("lgMin").textContent = "0"; $("lgMax").textContent = field === "vm" ? `${nf(vmax, 1)} MPa` : `${nf(vmax, 4)} mm`;
      const row = (n, b, t) => `<tr><td>${n}</td><td class="n">${b}</td><td class="n">${t}</td></tr>`;
      $("feaDiscT").innerHTML = `<table class="t"><thead><tr><th>Resultado</th><th class="n">4b inferior</th><th class="n">4a superior</th></tr></thead><tbody>` +
        row("Presión aplicada", `${nf(R.q_max, 2)} MPa`, `${nf(R.q_top, 2)} MPa`) + row("σvm máx.", `${nf(F.bot.vmMax, 1)} MPa`, `${nf(F.top.vmMax, 1)} MPa`) +
        row("Ubicación (r, θ)", `${nf(F.bot.maxAt[0])} mm, ${nf(F.bot.maxAt[1], 1)}°`, `${nf(F.top.maxAt[0])} mm, ${nf(F.top.maxAt[1], 1)}°`) +
        row("Flecha máx.", `${nf(F.bot.wMax, 3)} mm`, `${nf(F.top.wMax, 3)} mm`) +
        row("Almas 4d", F.bot.ringLine.map((v) => nf(v)).join(" / ") + " N/mm", F.top.ringLine.map((v) => nf(v)).join(" / ") + " N/mm") +
        row("Barras 4f", F.bot.barF.map((v) => nf(v, 1)).join(" / ") + " kN", F.top.barF.map((v) => nf(v, 1)).join(" / ") + " kN") +
        row("Σ carga / Σ reac.", `${nf(F.bot.Fapp, 1)} / ${nf(F.bot.Rsum, 1)} kN`, `${nf(F.top.Fapp, 1)} / ${nf(F.top.Rsum, 1)} kN`) +
        row("Admisible 0,6 Fy", `${nf(0.6 * P.Fy)} MPa`, `${nf(0.6 * P.Fy)} MPa`) + "</tbody></table>";
      $("feaDiscN").textContent = `Modelo: sector de ${nf(360 / P.N_rib, 1)}° entre nervios, ${F.bot.model.elems.length} elementos placa Mindlin MITC4 (${F.bot.res.ndof} GDL, resuelto en ${nf(F.bot.ms + F.top.ms)} ms). Cubo empotrado; almas, nervios y barras como apoyos verticales rígidos; simetría en los bordes del sector; la imagen repite el sector ${P.N_rib} veces. Al tratar almas y barras como apoyos rígidos se obtiene la flexión local de cada paño, que es la que gobierna el espesor; la flexión global del cajón se verifica aparte (FU en la pestaña Verificaciones).`;
    }
    if (F.pawlErr) $("feaPawlN").textContent = "Error en el modelo del trinquete: " + F.pawlErr;
    else {
      const f = F.pawl, vcap = drawPawl($("cvPawl"), f, C, deformed);
      $("lgMin2").textContent = "0"; $("lgMax2").textContent = `≥ ${nf(vcap)} MPa`;
      const adm = P.Fy_pawl / P.Nd;
      $("feaPawlT").innerHTML = `<table class="t"><thead><tr><th>Resultado</th><th class="n">Valor</th><th class="n">FU</th></tr></thead><tbody>` +
        `<tr><td>σ en la boca, fibra traccionada (FEA)</td><td class="n">${nf(f.vmMouth)} MPa</td><td class="n">${nf(f.vmMouth / adm, 2)}</td></tr>` +
        `<tr><td>σ en la boca, teoría de vigas M/S</td><td class="n">${nf(f.beam)} MPa</td><td class="n">${nf(f.beam / adm, 2)}</td></tr>` +
        `<tr><td>σvm máx. fuera de zonas de contacto (≥ 10 mm)</td><td class="n">${nf(f.vmFar)} MPa</td><td class="n">${nf(f.vmFar / adm, 2)}</td></tr>` +
        `<tr><td>Pico local en contacto/apoyo (singularidad)</td><td class="n">${nf(f.vmMax)} MPa</td><td class="n">–</td></tr>` +
        `<tr><td>Desplazamiento máximo</td><td class="n">${nf(f.dmax, 3)} mm</td><td class="n">–</td></tr>` +
        `<tr><td>Admisible Fy/Nd</td><td class="n">${nf(adm)} MPa</td><td class="n"></td></tr></tbody></table>`;
      $("feaPawlN").textContent = `Tensión plana Q4, malla 2,5 mm (${f.elems.length} elementos, ${f.res.ndof} GDL, ${nf(f.ms)} ms), espesor ${P.pawl_h} mm. Carga del calado repartida en el asiento con distribución cosenoidal. Apoyos: 25 mm inferiores en la boca del carro y labio posterior superior. Los picos en el borde de contacto son singularidades del modelo de apoyo puntual; en la pieza real el contacto se reparte y el chaflán de aristas los elimina. La verificación usa el mayor entre teoría de vigas y FEA en la sección de la boca.`;
    }
  }
  $("cvDisc").addEventListener("mousemove", (ev) => {
    const cv = ev.currentTarget, mp = cv._map; if (!mp) return;
    const r0 = cv.getBoundingClientRect(), x = (ev.clientX - r0.left) * cv.width / r0.width, y = (ev.clientY - r0.top) * cv.height / r0.height;
    const mx = (x - mp.cx) / mp.sc, my = -(y - mp.cy) / mp.sc, r = Math.hypot(mx, my); let th = Math.atan2(my, mx); if (th < 0) th += 2 * Math.PI;
    const m = mp.f.model, tl = th % m.alpha;
    if (r < m.rs[0] || r > m.rs[m.rs.length - 1]) { $("roDisc").textContent = `r = ${nf(r)} mm – fuera de la placa`; return; }
    let i = m.rs.findIndex((v) => v > r) - 1; if (i < 0) i = m.rs.length - 2;
    let j = m.ts.findIndex((v) => v > tl) - 1; if (j < 0) j = m.ts.length - 2;
    const e = i * (m.ts.length - 1) + j, el = mp.f.res.el[e];
    $("roDisc").textContent = `r = ${nf(r)} mm · θ = ${nf(th * 180 / Math.PI, 1)}° · σvm = ${nf(el.vm, 1)} MPa · Mx/My/Mxy = ${nf(el.M[0])}/${nf(el.M[1])}/${nf(el.M[2])} N·mm/mm`;
  });
  $("cvPawl").addEventListener("mousemove", (ev) => {
    const cv = ev.currentTarget, mp = cv._map; if (!mp) return;
    const r0 = cv.getBoundingClientRect(), x = (ev.clientX - r0.left) * cv.width / r0.width, y = (ev.clientY - r0.top) * cv.height / r0.height;
    const mx = (x - mp.ox) / mp.sc, my = (mp.oy - y) / mp.sc, f = mp.f;
    let best = -1, bd = 1e9; f.cent.forEach(([cx, cy], i) => { const d = Math.abs(cx - mx) + Math.abs(cy - my); if (d < bd) { bd = d; best = i; } });
    if (best < 0 || bd > 6) { $("roPawl").textContent = ""; return; }
    const e = f.res.el[best];
    $("roPawl").textContent = `x = ${nf(mx, 1)} · y = ${nf(my, 1)} mm · σx = ${nf(e.sx)} · σy = ${nf(e.sy)} · τxy = ${nf(e.txy)} · σvm = ${nf(e.vm)} MPa`;
  });
  document.querySelectorAll("[data-plate]").forEach((b) => b.addEventListener("click", () => { plate = b.dataset.plate; renderFEA(); }));
  document.querySelectorAll("[data-field]").forEach((b) => b.addEventListener("click", () => { field = b.dataset.field; renderFEA(); }));
  document.querySelectorAll("[data-def]").forEach((b) => b.addEventListener("click", () => { deformed = +b.dataset.def; renderFEA(); }));

  /* ---------------- planos ---------------- */
  function renderSheet() { $("sheetPrev").innerHTML = sheetSVG(buildSheet(R, V, F), { ink: "#000000", paper: "#ffffff", force: "#b3361f" }); }
  async function save(name, blob) {
    let d = null; try { d = await dlP; } catch (e) { d = null; }
    if (d) {
      try { await d.save({ filename: name, data: blob }); toast("Archivo entregado: " + name); }
      catch (e) { toast(e && e.code === "declined" ? "Descarga cancelada" : `No se pudo guardar (${(e && (e.code || e.message)) || "error"})`); }
      return;
    }
    const url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url; a.download = name; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 4000);
    toast("Descargando " + name);
  }
  async function busy(btn, fn) { const t = btn.textContent; btn.disabled = true; btn.textContent = "Generando…"; try { await fn(); } catch (e) { console.error(e); toast("Error: " + e.message); } finally { btn.disabled = false; btn.textContent = t; } }
  const stamp = () => new Date().toISOString().slice(0, 10);
  document.querySelectorAll("[data-file]").forEach((b) => b.addEventListener("click", () => busy(b, async () => {
    const r = await fetch(b.dataset.file); if (!r.ok) throw new Error("archivo no disponible en esta copia");
    await save(b.dataset.file.split("/").pop(), await r.blob());
  })));
  $("bIssuedZip").addEventListener("click", (ev) => busy(ev.currentTarget, async () => {
    if (!window.JSZip) throw new Error("no se cargó la librería ZIP");
    const names = ["TT300-B-D-01.dxf", "TT300-B-D-02.dxf", "TT300-B-D-03.dxf", "TT300-B-F-01.dxf", "TT300-B-F-02.dxf", "TT300-B-F-03.dxf", "TT300-B.step"], z = new JSZip();
    for (const n of names) { const r = await fetch("planos/src/" + n + ".txt"); if (!r.ok) throw new Error("archivo no disponible en esta copia"); z.file(n === "TT300-B.step" ? "TT300-B_conjunto.step" : n, await r.arrayBuffer()); }
    await save("TT300-B_Tornamesa300_DXF_STEP.zip", await z.generateAsync({ type: "blob", compression: "DEFLATE" }));
  }));
  $("bSheetPdf").addEventListener("click", (ev) => busy(ev.currentTarget, async () => {
    if (!window.jspdf) throw new Error("no se cargó la librería PDF");
    await save(`TT300-B-P-01_plano_parametrico_${stamp()}.pdf`, sheetPDF(buildSheet(R, V, F)));
  }));
  $("bSheetDxf").addEventListener("click", (ev) => busy(ev.currentTarget, async () => {
    if (!window.JSZip) throw new Error("no se cargó la librería ZIP");
    const z = new JSZip(); z.file("TT300-B-P-01_plano_parametrico.dxf", sheetDXF(buildSheet(R, V, F)));
    z.file("LEEME.txt", "Plano de verificación paramétrico TT300-B-P-01 en DXF R12 (AC1009), unidades mm, escala de papel 1:1 (formato A1 841x594).\r\nCapas: VIS, FINA, EJE, OCU, COTA, TXT, MARCO, FUERZA.\r\n");
    await save(`TT300-B-P-01_DXF_${stamp()}.zip`, await z.generateAsync({ type: "blob", compression: "DEFLATE" }));
  }));
  $("bMemo").addEventListener("click", (ev) => busy(ev.currentTarget, async () => {
    if (!window.jspdf || !window.jspdf.jsPDF.API.autoTable) throw new Error("no se cargó la librería PDF");
    const Cp = pal(true), im = {};
    im.plan = await svgToPng(dgPlan(R, Cp)); im.mu = await svgToPng(dgMu(R, Cp)); im.stroke = await svgToPng(dgStroke(R, Cp)); im.breakdown = await svgToPng(dgBreak(R, Cp));
    im.shoe = await svgToPng(dgShoe(R, Cp)); im.bar = await svgToPng(dgBar(R, Cp)); im.pin = await svgToPng(dgPin(R, Cp));
    const off = (w, h, fn) => { const c = document.createElement("canvas"); c.width = w; c.height = h; fn(c); return { data: c.toDataURL("image/png"), w, h }; };
    if (F.bot) { im.feaBot = off(900, 900, (c) => drawDisc(c, F.bot, "vm", Cp)); im.feaTop = off(900, 900, (c) => drawDisc(c, F.top, "vm", Cp)); }
    if (F.pawl) im.feaPawl = off(1000, 560, (c) => drawPawl(c, F.pawl, Cp, 0));
    renderFEA();
    await save(`TT300-B_memoria_verificacion_${stamp()}.pdf`, await memoriaPDF(R, V, F, Cp, im));
  }));
  (async () => {
    try { const r = await fetch("planos/TT300-B_Tornamesa300_Planos_Diseno.pdf", { method: "HEAD" }); if (!r.ok) throw 0; }
    catch (e) { document.querySelectorAll("[data-file], #bIssuedZip").forEach((b) => { b.disabled = true; b.title = "Disponible en la versión publicada"; }); }
  })();

  /* ---------------- pestañas ---------------- */
  const TABS = ["modelo", "resumen", "actuador", "diagramas", "verificaciones", "fea", "planos"];
  function show(t) {
    if (!TABS.includes(t)) t = "modelo";
    document.querySelectorAll(".tab").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.t === t)));
    document.querySelectorAll("[data-p]").forEach((p) => (p.hidden = p.dataset.p !== t));
  }
  document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => { show(b.dataset.t); try { history.replaceState(null, "", "#" + b.dataset.t); } catch (e) { location.hash = b.dataset.t; } }));
  window.addEventListener("hashchange", () => show(location.hash.slice(1)));
  try { window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => R && render()); } catch (e) { /* */ }
  new MutationObserver(() => R && render()).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  buildForm();
  show(location.hash.slice(1));
  recompute();
})();
```

### tt300/app/shell.html
`tt300/app/shell.html` — 275 líneas

```html
<title>Tornamesa TT300-B</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Concepto: hoja de taller – panel de parámetros a la izquierda como "cuadro de datos", resultados a la derecha en pestañas. */
:root{
  --bg:#f3f4f1; --panel:#fbfbf9; --ink:#1c2228; --mute:#5c6870; --line:#cfd5d1; --grid:#e4e8e5;
  --accent:#2453c4; --accent-ink:#ffffff; --force:#b3361f; --react:#0d776a;
  --good:#2e7a33; --warn:#a8700f; --bad:#c22a2a;
  --fill:#e6eae7; --fill2:#d5dcd8; --cyl:#c8d2e6; --shoe:#ead9bf; --pawl:#efc77f; --band:#2453c414; --chip:#e8ece9;
  --f-display:"Barlow Condensed", "Arial Narrow", "Roboto Condensed", sans-serif;
  --f-body:"IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --f-mono:"IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#111518; --panel:#181e22; --ink:#e2e7e9; --mute:#98a4ab; --line:#2d363c; --grid:#222a2f;
  --accent:#7ba4ff; --accent-ink:#0b1220; --force:#ff7d5c; --react:#3cc7b1; --good:#62c766; --warn:#e3a63e; --bad:#ff6b6b;
  --fill:#20282d; --fill2:#2a343a; --cyl:#283753; --shoe:#4b3f2b; --pawl:#6d5525; --band:#7ba4ff1c; --chip:#222a2f; color-scheme:dark } }
:root[data-theme="dark"]{
  --bg:#111518; --panel:#181e22; --ink:#e2e7e9; --mute:#98a4ab; --line:#2d363c; --grid:#222a2f;
  --accent:#7ba4ff; --accent-ink:#0b1220; --force:#ff7d5c; --react:#3cc7b1; --good:#62c766; --warn:#e3a63e; --bad:#ff6b6b;
  --fill:#20282d; --fill2:#2a343a; --cyl:#283753; --shoe:#4b3f2b; --pawl:#6d5525; --band:#7ba4ff1c; --chip:#222a2f; color-scheme:dark }
*{box-sizing:border-box}
[hidden]{display:none!important}
html,body{height:100%}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:14px;line-height:1.45;margin:0;overflow:hidden}
.wrap{padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:0;max-width:1600px;margin:0 auto;height:100%;display:flex;flex-direction:column}
header.top{flex:none;display:flex;flex-wrap:wrap;gap:8px 24px;align-items:flex-end;justify-content:space-between;padding-block:12px 10px;border-bottom:2px solid var(--ink)}
.brand h1{font-family:var(--f-display);font-weight:700;font-size:28px;letter-spacing:.01em;margin:0;line-height:1;text-wrap:balance}
.brand p{margin:4px 0 0;color:var(--mute);font-size:13px}
.code{font-family:var(--f-mono);font-size:12px;color:var(--mute);letter-spacing:.06em;text-transform:uppercase}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:4px 10px;font-size:12.5px;white-space:nowrap}
.chip b{font-family:var(--f-mono);font-weight:500}
.dot{width:8px;height:8px;border-radius:50%;background:var(--mute);flex:none}
.ok .dot{background:var(--good)} .wa .dot{background:var(--warn)} .no .dot{background:var(--bad)}
.layout{flex:1;min-height:0;display:grid;grid-template-columns:330px minmax(0,1fr);gap:20px;padding-top:12px}
aside.params{background:var(--panel);border:1px solid var(--line);border-radius:6px 6px 0 0;overflow-y:auto;overscroll-behavior:contain;min-height:0}
main.res{overflow-y:auto;overscroll-behavior:contain;min-height:0;min-width:0;padding-bottom:28px;padding-right:4px}
.tabs{position:sticky;top:0;z-index:4;background:var(--bg)}
@media (max-width:980px){html,body{height:auto}body{overflow:auto}.wrap{height:auto;display:block}.layout{grid-template-columns:minmax(0,1fr)}aside.params,main.res{overflow:visible;min-height:auto}}
.ph{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel);z-index:2}
.ph h2{font-family:var(--f-display);font-size:20px;font-weight:600;margin:0;letter-spacing:.02em}
details.grp{border-bottom:1px solid var(--line)}
details.grp summary{cursor:pointer;padding:9px 14px;font-weight:600;font-size:12.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);list-style:none;display:flex;justify-content:space-between}
details.grp summary::after{content:"+";font-family:var(--f-mono)} details.grp[open] summary::after{content:"−"}
details.grp summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.prow{display:grid;grid-template-columns:minmax(0,1fr) 92px;gap:8px;align-items:center;padding:3px 14px}
.prow label{font-size:12.5px;line-height:1.25}
.prow label small{display:block;color:var(--mute);font-family:var(--f-mono);font-size:10.5px}
.prow input{width:100%;font-family:var(--f-mono);font-size:13px;padding:4px 6px;border:1px solid var(--line);border-radius:4px;background:var(--bg);color:var(--ink);text-align:right}
.prow input.txt{text-align:left}
.prow input:focus-visible{outline:2px solid var(--accent);outline-offset:0}
.prow.chg input{border-color:var(--accent);box-shadow:inset 3px 0 0 var(--accent)}
.grp-body{padding-bottom:8px}
button{font:inherit;cursor:pointer}
.btn{border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:5px;padding:7px 12px;font-size:13px;font-weight:500}
.btn:hover{border-color:var(--accent)} .btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.btn.pri{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.btn[disabled]{opacity:.45;cursor:not-allowed}
.btn.sm{padding:4px 9px;font-size:12px}
.tabs{display:flex;gap:2px;border-bottom:1px solid var(--line);overflow-x:auto}
.tab{background:none;border:none;border-bottom:3px solid transparent;padding:9px 14px;font-family:var(--f-display);font-size:18px;font-weight:600;color:var(--mute);letter-spacing:.02em;white-space:nowrap}
.tab[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent)}
.tab:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.panel{padding-top:16px;display:grid;gap:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px 16px;min-width:0}
.card h3{font-family:var(--f-display);font-size:20px;font-weight:600;margin:0 0 8px;letter-spacing:.02em}
.card h4{font-size:12px;letter-spacing:.07em;text-transform:uppercase;color:var(--mute);margin:12px 0 6px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr));gap:18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.kpi{border:1px solid var(--line);border-radius:6px;padding:10px 12px;background:var(--panel);display:grid;gap:2px;align-content:start}
.kpi .l{font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
.nt{text-transform:none;letter-spacing:0}
.kpi .v{font-family:var(--f-mono);font-size:24px;font-weight:500;font-variant-numeric:tabular-nums}
.kpi .s{font-size:12px;color:var(--mute)}
.kpi.ok{box-shadow:inset 0 3px 0 var(--good)} .kpi.wa{box-shadow:inset 0 3px 0 var(--warn)} .kpi.no{box-shadow:inset 0 3px 0 var(--bad)}
.verdict{border:2px solid var(--good);border-radius:6px;padding:12px 16px;display:grid;gap:4px;background:var(--panel)}
.verdict.no{border-color:var(--bad)} .verdict.wa{border-color:var(--warn)}
.verdict strong{font-family:var(--f-display);font-size:22px;letter-spacing:.02em}
.tw{overflow-x:auto}
table.t{border-collapse:collapse;width:100%;font-size:13px}
table.t th{font-size:11.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--mute);text-align:left;padding:6px 8px;border-bottom:2px solid var(--ink);white-space:nowrap}
table.t td{padding:5px 8px;border-bottom:1px solid var(--grid);vertical-align:top}
table.t td.n,table.t th.n{text-align:right;font-family:var(--f-mono);font-variant-numeric:tabular-nums;white-space:nowrap}
table.t tr.hl td{background:var(--band)}
table.t td.f{font-family:var(--f-mono);font-size:11.5px;color:var(--mute)}
.fu{display:flex;align-items:center;gap:8px;min-width:130px}
.fu .bar{flex:1;height:8px;background:var(--grid);border-radius:4px;position:relative;overflow:hidden}
.fu .bar i{position:absolute;inset:0 auto 0 0;border-radius:4px}
.fu .bar::after{content:"";position:absolute;left:90%;top:-2px;bottom:-2px;width:1px;background:var(--ink);opacity:.5}
.st{font-size:11.5px;font-weight:600;padding:2px 7px;border-radius:999px;white-space:nowrap}
.st.ok{color:var(--good);background:color-mix(in srgb,var(--good) 14%,transparent)}
.st.wa{color:var(--warn);background:color-mix(in srgb,var(--warn) 16%,transparent)}
.st.no{color:var(--bad);background:color-mix(in srgb,var(--bad) 14%,transparent)}
.dgw{overflow-x:auto} .dgw svg{width:100%;height:auto;display:block;margin:0 auto}
.eq{font-family:var(--f-mono);font-size:12.5px;background:var(--bg);border:1px solid var(--line);border-radius:5px;padding:10px 12px;display:grid;gap:3px;overflow-x:auto}
.eq span{white-space:nowrap}
.note{font-size:12.5px;color:var(--mute)}
ul.hyp{margin:0;padding-left:18px;display:grid;gap:4px;font-size:13px}
.ctl{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:5px;overflow:hidden}
.seg button{border:none;background:var(--panel);color:var(--mute);padding:5px 10px;font-size:12.5px}
.seg button[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink)}
.seg button:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
canvas{max-width:100%;height:auto;display:block;border-radius:4px}
.legend{display:flex;align-items:center;gap:8px;font-family:var(--f-mono);font-size:11.5px;color:var(--mute);margin-top:6px}
.legend .ramp{flex:1;height:10px;border-radius:3px;border:1px solid var(--line)}
.readout{font-family:var(--f-mono);font-size:12px;color:var(--mute);min-height:18px;margin-top:4px}
.dl{display:grid;gap:10px}
.dlrow{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.sheetprev{border:1px solid var(--line);border-radius:4px;overflow:auto;background:#fff}
.sheetprev svg{width:100%;height:auto;min-width:640px;display:block}
.geohead{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:baseline;justify-content:space-between}
.edit{font-size:12.5px;color:var(--mute)} .edit b{color:var(--accent)}
.geo-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:16px;margin-top:10px;align-items:start}
.g3d{border:1px solid var(--line);border-radius:4px;overflow:hidden;min-height:280px;touch-action:none}
.g3d canvas{width:100%!important;height:auto!important;display:block}
.toast{position:fixed;left:50%;transform:translateX(-50%);bottom:calc(16px + env(safe-area-inset-bottom,0px));background:var(--ink);color:var(--bg);padding:8px 14px;border-radius:6px;font-size:13px;z-index:20;max-width:calc(100% - 32px)}
.busy{opacity:.55;transition:opacity .15s}
.warnbox{border-left:3px solid var(--warn);padding:6px 10px;background:color-mix(in srgb,var(--warn) 10%,transparent);font-size:12.5px;border-radius:0 4px 4px 0}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<div class="wrap">
  <header class="top">
    <div class="brand">
      <div class="code">TT300-B · Rev. P · Verificación paramétrica</div>
      <h1>Tornamesa hidráulica 300 tf – acero/acero con grasa grafitada</h1>
      <p>Disco cajón Ø2000 con barras de empuje · 2 cilindros 50 t en par · AISC 360-22 (ASD), ASME BTH-1, AWS D1.1</p>
    </div>
    <div class="chips" id="chips"></div>
  </header>

  <div class="layout">
    <aside class="params" aria-label="Parámetros de diseño">
      <div class="ph"><h2>Parámetros</h2><button class="btn sm" id="reset" type="button">Valores Rev. 0</button></div>
      <form id="pform" autocomplete="off"></form>
      <p class="note" style="padding:10px 14px;margin:0">Los campos marcados difieren del diseño emitido. Todo se recalcula al editar (FEA incluido).</p>
    </aside>

    <main class="res">
      <nav class="tabs" role="tablist" aria-label="Secciones">
        <button class="tab" role="tab" data-t="modelo" aria-selected="true">Modelo</button>
        <button class="tab" role="tab" data-t="resumen" aria-selected="false">Resumen</button>
        <button class="tab" role="tab" data-t="actuador" aria-selected="false">Cilindros</button>
        <button class="tab" role="tab" data-t="diagramas" aria-selected="false">Diagramas</button>
        <button class="tab" role="tab" data-t="verificaciones" aria-selected="false">Verificaciones</button>
        <button class="tab" role="tab" data-t="fea" aria-selected="false">FEA</button>
        <button class="tab" role="tab" data-t="planos" aria-selected="false">Planos</button>
      </nav>

      <section class="panel" data-p="modelo">
        <div class="card">
          <div class="geohead"><h3>Esquema de la geometría</h3><span class="edit" id="editing">Seleccione un parámetro para resaltar el elemento que controla.</span></div>
          <div class="geo-grid">
            <div class="g3wrap">
              <div class="ctl">
                <div class="seg" role="group" aria-label="Vista 3D"><button type="button" data-v3="iso" aria-pressed="true">Iso</button><button type="button" data-v3="top" aria-pressed="false">Planta</button><button type="button" data-v3="front" aria-pressed="false">Frente</button><button type="button" data-v3="side" aria-pressed="false">Lateral</button></div>
                <div class="seg" role="group" aria-label="Plancha superior"><button type="button" data-top="trans" aria-pressed="true">4a transparente</button><button type="button" data-top="solid" aria-pressed="false">Sólida</button><button type="button" data-top="hide" aria-pressed="false">Oculta</button></div>
              </div>
              <div id="g3d" class="g3d"></div>
              <p class="note" id="g3note">Arrastre para rotar, rueda para acercar, botón derecho para desplazar.</p>
            </div>
            <div class="dgw" id="gPlan"></div>
          </div>
          <div class="geo-grid">
            <div class="dgw" id="gElev"></div>
            <div class="dgw" id="gEdge"></div>
          </div>
        </div>
      </section>

      <section class="panel" data-p="resumen" hidden>
        <div id="verdict" class="verdict"></div>
        <div class="kpis" id="kpis"></div>
        <div class="card"><h3>Casos de fricción</h3><div class="tw" id="casesT"></div><p class="note" id="mumaxT"></p></div>
        <div class="grid2">
          <div class="card"><h3>Desarrollo del caso de diseño</h3><div class="eq" id="eqs"></div></div>
          <div class="card"><h3>Hipótesis de cálculo</h3><ul class="hyp" id="hyps"></ul></div>
        </div>
      </section>

      <section class="panel" data-p="actuador" hidden>
        <div class="card"><h3>Fuerzas sobre el disco, carros y ménsulas</h3><div class="dgw" id="dgPlan"></div></div>
        <div class="card"><h3>Carga en cada pistón</h3><div class="tw" id="pistonT"></div><p class="note">θ es la posición angular de la barra durante la carrera útil. El brazo a = R·cos θ es mínimo al tomar y al soltar la barra, donde la fuerza es máxima.</p></div>
        <div class="grid2">
          <div class="card"><div class="dgw" id="dgStroke"></div></div>
          <div class="card"><div class="dgw" id="dgMu"></div></div>
        </div>
        <div class="card"><div class="dgw" id="dgBreak"></div></div>
      </section>

      <section class="panel" data-p="diagramas" hidden>
        <div class="grid2">
          <div class="card"><h3>Carro de empuje</h3><div class="dgw" id="dgShoe"></div></div>
          <div class="card"><h3>Barra 4f</h3><div class="dgw" id="dgBar"></div></div>
        </div>
        <div class="grid2">
          <div class="card"><h3>Pasador de ménsula</h3><div class="dgw" id="dgPin"></div></div>
          <div class="card"><h3>Camino de carga y reacciones</h3><div class="tw" id="pathT"></div></div>
        </div>
      </section>

      <section class="panel" data-p="verificaciones" hidden>
        <div class="card"><h3>Verificación de elementos</h3>
          <p class="note">Cadena de empuje a la fuerza de calado (alivio). Clasificación: FU ≤ 0,90 aceptable · 0,90–1,00 monitoreo · &gt; 1,00 no cumple.</p>
          <div class="tw" id="verT"></div></div>
      </section>

      <section class="panel" data-p="fea" hidden>
        <div class="grid2">
          <div class="card"><h3>Disco cajón – placas 4a / 4b</h3>
            <div class="ctl">
              <div class="seg" role="group" aria-label="Plancha"><button type="button" data-plate="bot" aria-pressed="true">Inferior 4b</button><button type="button" data-plate="top" aria-pressed="false">Superior 4a</button></div>
              <div class="seg" role="group" aria-label="Campo"><button type="button" data-field="vm" aria-pressed="true">σ von Mises</button><button type="button" data-field="w" aria-pressed="false">Flecha w</button></div>
            </div>
            <canvas id="cvDisc" width="900" height="900" aria-label="Mapa de tensiones del disco"></canvas>
            <div class="legend"><span id="lgMin"></span><span class="ramp" id="ramp1"></span><span id="lgMax"></span></div>
            <div class="readout" id="roDisc">Mueva el cursor sobre el disco para leer valores.</div>
            <div class="tw" id="feaDiscT"></div>
            <p class="note" id="feaDiscN"></p>
          </div>
          <div class="card"><h3>Trinquete pos 11 – tensión plana</h3>
            <div class="ctl"><div class="seg" role="group" aria-label="Deformada"><button type="button" data-def="0" aria-pressed="true">Sin deformada</button><button type="button" data-def="1" aria-pressed="false">Deformada amplificada</button></div></div>
            <canvas id="cvPawl" width="1000" height="560" aria-label="Mapa de tensiones del trinquete"></canvas>
            <div class="legend"><span id="lgMin2"></span><span class="ramp" id="ramp2"></span><span id="lgMax2"></span></div>
            <div class="readout" id="roPawl"></div>
            <div class="tw" id="feaPawlT"></div>
            <p class="note" id="feaPawlN"></p>
          </div>
        </div>
      </section>

      <section class="panel" data-p="planos" hidden>
        <div class="grid2">
          <div class="card dl"><h3>Planos emitidos Rev. 0</h3>
            <p class="note">Juegos completos de diseño (D-01 a D-03) y fabricación (F-01 a F-03) con los valores de diseño; DXF de cada lámina y modelo STEP en un ZIP.</p>
            <div class="dlrow">
              <button class="btn" type="button" data-file="planos/TT300-B_Tornamesa300_Planos_Diseno.pdf">Diseño · PDF</button>
              <button class="btn" type="button" data-file="planos/TT300-B_Tornamesa300_Planos_Fabricacion.pdf">Fabricación · PDF</button>
              <button class="btn" type="button" id="bIssuedZip">DXF + STEP · ZIP</button>
            </div>
            <div class="warnbox" id="issuedWarn" hidden></div>
          </div>
          <div class="card dl"><h3>Con los parámetros actuales</h3>
            <p class="note">Plano de verificación A1 (planta, corte, detalles acotados, parámetros, fuerzas y FU) y memoria A4 con diagramas y resultados FEA. Texto en negro.</p>
            <div class="dlrow">
              <button class="btn pri" type="button" id="bSheetPdf">Plano paramétrico · PDF</button>
              <button class="btn" type="button" id="bSheetDxf">Plano paramétrico · DXF (ZIP)</button>
              <button class="btn" type="button" id="bMemo">Memoria de verificación · PDF</button>
            </div>
          </div>
        </div>
        <div class="card"><h3>Vista previa del plano paramétrico</h3><div class="sheetprev" id="sheetPrev"></div></div>
      </section>
    </main>
  </div>
</div>
<div class="toast" id="toast" hidden role="status"></div>

<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jspdf-autotable@3.8.2/dist/jspdf.plugin.autotable.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js"></script>
<script>
/*@@FEA@@*/
/*@@CALC@@*/
/*@@DIAG@@*/
/*@@EXPORT@@*/
/*@@GEO@@*/
/*@@UI@@*/
</script>
```

### tt300/app/build.py
`tt300/app/build.py` — 14 líneas

```python
import re
s=open('shell.html').read()
for tag,f in [('FEA','fea.js'),('CALC','calc.js'),('DIAG','diag.js'),('EXPORT','export.js'),('GEO','geo.js'),('UI','ui.js')]:
    code=open(f).read().replace('if (typeof module !== "undefined") module.exports','if (false) module.exports')
    s=s.replace('/*@@%s@@*/'%tag, code)
open('tornamesa.html','w').write(s)
print(len(s))
sk='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>'
open('TT300-B_Verificacion_Tornamesa.html','w').write(sk+s+'</body></html>')
import os, shutil
os.makedirs('site/planos', exist_ok=True)
shutil.copy('TT300-B_Verificacion_Tornamesa.html','site/index.html')
for f in ['TT300-B_Tornamesa300_Planos_Diseno.pdf','TT300-B_Tornamesa300_Planos_Fabricacion.pdf','TT300-B_Tornamesa300_DXF_STEP.zip']:
    shutil.copy('../out/'+f,'site/planos/'+f)
```

### tt300/app/test_fea.js
`tt300/app/test_fea.js` — 26 líneas

```javascript
const FEA = require('./fea.js');
// SS square plate a=1000,t=10,q=0.01
const a=1000,n=20,nodes=[],elems=[];
for(let i=0;i<=n;i++)for(let j=0;j<=n;j++)nodes.push([i*a/n,j*a/n]);
const id=(i,j)=>i*(n+1)+j;
for(let i=0;i<n;i++)for(let j=0;j<n;j++)elems.push([id(i,j),id(i+1,j),id(i+1,j+1),id(i,j+1)]);
const wFix=[],betaN=[];
for(let i=0;i<=n;i++)for(let j=0;j<=n;j++){ if(i==0||i==n){wFix.push(id(i,j));betaN.push([id(i,j),0,1]);} else if(j==0||j==n){wFix.push(id(i,j));betaN.push([id(i,j),1,0]);} }
let t0=Date.now();
const r=FEA.plate({nodes,elems,t:10,E:2e5,nu:0.3,q:new Float64Array(elems.length).fill(0.01),wFix,betaN});
const D=2e5*1000/(12*0.91);
console.log('w FE',r.w[id(n/2,n/2)].toFixed(4),'Navier',(0.00406*0.01*1e12/D).toFixed(4),'ms',Date.now()-t0);
const ec=elems.findIndex(e=>e[0]==id(n/2-1,n/2-1)||false);
console.log('Mx center elem',r.el[id(n/2,n/2)-n/2-1]&&0, 'max M', Math.max(...r.el.map(e=>e.M[0])).toFixed(1),'theory 479');
console.log('Fapplied',r.Fapplied.toFixed(1),'Rsum',r.Rsum.toFixed(1));
// clamped thick check t=100 ratio
// cantilever plane stress L=1000 h=100 t=10 P=1000
const L=1000,h=100,nx=80,ny=10,N2=[],E2=[];
for(let i=0;i<=nx;i++)for(let j=0;j<=ny;j++)N2.push([i*L/nx,j*h/ny]);
const id2=(i,j)=>i*(ny+1)+j;
for(let i=0;i<nx;i++)for(let j=0;j<ny;j++)E2.push([id2(i,j),id2(i+1,j),id2(i+1,j+1),id2(i,j+1)]);
const fix=[];for(let j=0;j<=ny;j++){fix.push([id2(0,j),0],[id2(0,j),1]);}
const loads=[];for(let j=0;j<=ny;j++)loads.push([id2(nx,j),0,-1000/(ny+1)]);
const r2=FEA.planeStress({nodes:N2,elems:E2,t:10,E:2e5,nu:0.3,fix,loads});
console.log('tip',r2.u[2*id2(nx,ny/2)+1].toFixed(4),'theory -2.0(+shear ~0.026)');
console.log('max sx',Math.max(...r2.el.map(e=>Math.abs(e.sx))).toFixed(1),'theory 60 at root (elem center ~ 59)');
```

### tt300/app/test_calc.js
`tt300/app/test_calc.js` — 13 líneas

```javascript
global.FEA = require('./fea.js');
const C = require('./calc.js');
const P = C.defaults();
const R = C.compute(P);
console.log('mass', R.mass.total.toFixed(1), 'N', R.N.toFixed(1), 'r_u', R.r_u.toFixed(4), 'a', R.a.toFixed(2), 'K', R.K.toFixed(4), 'Fmax', R.Fmax.toFixed(1));
for (const c of R.cases) console.log(c.name.padEnd(45), c.mu, c.r.toFixed(3), c.T.toFixed(1), c.Fb.toFixed(1), c.Fc.toFixed(1), c.p.toFixed(0), c.FS.toFixed(2));
console.log('mumax', R.muMax(0.8,700).toFixed(3), 'qavg', R.q_avg.toFixed(3), 'qmax', R.q_max.toFixed(3), 'qtop', R.q_top.toFixed(3), 'ground', R.g_avg.toFixed(3), R.g_max.toFixed(3));
const bot = C.runDisc(P,'bot'), top = C.runDisc(P,'top');
for (const f of [bot, top]) console.log(f.model.which, 'nodes', f.model.nodes.length, 'ms', f.ms.toFixed(0), 'vmMax', f.vmMax.toFixed(1), 'vmC', f.vmC.toFixed(1), 'at', f.maxAt.map(v=>v.toFixed(1)), 'w', f.wMax.toFixed(4), 'ring N/mm', f.ringLine.map(v=>v.toFixed(0)), 'bars kN', f.barF.map(v=>v.toFixed(1)), 'rib', f.ribF.toFixed(1), 'hub', f.hubF.toFixed(1), 'F', f.Fapp.toFixed(1), 'R', f.Rsum.toFixed(1));
const pw = C.runPawl(P, R);
console.log('pawl ms', pw.ms.toFixed(0), 'vmMax', pw.vmMax.toFixed(0), 'mouth', pw.vmMouth.toFixed(0), 'far', pw.vmFar.toFixed(0), 'beam', pw.beam.toFixed(0), 'dmax', pw.dmax.toFixed(3), 'loads', pw.loads.length, 'sumFy', pw.loads.reduce((s,l)=>s+l[2],0).toFixed(0), 'sumFx', pw.loads.reduce((s,l)=>s+l[1],0).toFixed(0));
const V = C.verifs(R, {bot, top, pawl: pw});
for (const v of V) console.log(v.grp.padEnd(14), v.el.padEnd(48), v.dem.toFixed(2).padStart(9), v.cap.toFixed(2).padStart(9), v.fu.toFixed(2));
```

### tt300/app/t2.js
`tt300/app/t2.js` — 9 líneas

```javascript
global.FEA = require('./fea.js');
const C = require('./calc.js');
const P = C.defaults(); const R = C.compute(P);
const pw = C.runPawl(P, R);
const arr = pw.res.el.map((e,i)=>[e.vm, pw.cent[i][0], pw.cent[i][1]]).sort((a,b)=>b[0]-a[0]);
console.log(arr.slice(0,15).map(a=>a.map(v=>v.toFixed(1)).join(' ')).join('\n'));
console.log('Xs',pw.Xs.toFixed(1),'Xm',pw.Xm);
// stress along vertical line x ~ 100
for (const x of [70, 90, 110, 114]) { const col = pw.res.el.map((e,i)=>[e.sx,pw.cent[i][0],pw.cent[i][1]]).filter(a=>Math.abs(a[1]-x)<1.3); console.log(x, col.filter((a,i)=>i%4==0).map(a=>a[0].toFixed(0)+'@'+a[2].toFixed(0)).join(' ')); }
```

## Apéndice C. Código fuente completo del generador de planos y 3D 300 tf (`tt300`)

### tt300/params.py
`tt300/params.py` — 134 líneas

```python
"""Parámetros geométricos tornamesa 300 tf. Unidades: mm. z=0 cara inferior placa base."""
import math

PROJ = "TORNAMESA HIDRÁULICA 300 tf"

# ---------------- comunes ----------------
B = 2000.0          # placa base, lado en Y
BX = 2400.0         # placa base, lado en X (cilindros)
TB = 80.0           # espesor placa base
D_DISC = 2000.0     # disco
TD = 160.0          # altura total disco cajón
TP_TOP = 30.0
TP_BOT = 30.0
GAP = TD - TP_TOP - TP_BOT   # 100 entre planchas
HUB_D = 300.0
RING_T = 25.0
RING_R = [300.0, 550.0, 735.0]
RIB_T = 20.0
N_RIB = 12
RIB_R1 = 880.0

# pivote / buje / tapa
D_PIV = 150.0
D_BUJE_EXT = 190.0
L_BUJE = 100.0
D_CB = 260.0        # contrataladro superior disco
H_CB = 25.0
D_TAPA = 240.0
T_TAPA = 20.0
PIV_UP = 3.0        # sobresale pivote sobre fondo contrataladro
BOLT_PCD = 100.0
N_BOLT = 6

# barras de empuje (perimetrales, entre planchas)
R_BAR = 940.0
D_BAR = 70.0
N_BAR = 36
BAR_ANG0 = 5.0      # 5° + 10°k
R_IDX = R_BAR
D_IDX_HOLE = 71.0
N_IDX = N_BAR
IDX_ANG0 = BAR_ANG0

# izaje disco (M30) y sello
R_M30 = 600.0
M30_ANG = [45, 135, 225, 315]
N_SEAL_BOLT = 36    # M8 radiales en canto plancha inferior a 0°+10°k

# cilindros
F_CYL = 445.0       # kN mín a 700 bar
STROKE = 200.0
L0_CYL = 450.0      # ojal-ojal retraído
D_CYL = 140.0
D_ROD = 90.0
EYE_W = 70.0
EYE_D = 120.0
D_PIN_CYL = 70.0
X_CYL = 1085.0      # eje cilindro / carro / guía
Y_BRK = 818.0       # pasador ménsula (±X_CYL, ±Y_BRK)

# carro de empuje y trinquete
SHOE_X0 = 1020.0    # cara interior del carro
SHOE_X1 = 1150.0
SHOE_L = 300.0
SHOE_FRONT = 20.0   # cara frontal del carro sobre centro de barra
EYE_OFF = 250.0     # centro barra -> pasador ojal vástago (retraído)
PAWL_W = 85.0       # ancho (Y)
PAWL_H = 90.0       # alto (Z)
PAWL_TIP = 905.0    # x de la punta
PAWL_L = 245.0      # largo (X)
SEAT_R = 36.0
RAIL_W, RAIL_H, RAIL_L = 40.0, 30.0, 850.0
FREE = 36.0         # recorrido libre antes de tomar la barra

# ménsula
CHEEK_T = 40.0
CHEEK_GAP = 80.0
CHEEK_L = 280.0
BACK_T = 40.0

# orejas de izaje base
LUG_T = 40.0
LUG_L = 150.0
LUG_H = 170.0
LUG_X = 600.0
LUG_HOLE = 32.0

# sello
SEAL_T = 5.0
BAR_W, BAR_T = 25.0, 6.0

# pastillas UHMW
D_PAD = 170.0
T_PAD = 10.0
D_POCKET = 170.6
H_POCKET = 5.0
RINGS = [(300.0, 6, 30.0), (550.0, 12, 15.0), (735.0, 16, 0.0)]
INOX_T = 3.0
INOX_A = (390.0, 810.0)
INOX_B = (880.0, 1680.0)


def variant(kind):
    """kind: 'U' (UHMW) o 'S' (acero-acero grafito)."""
    g = (H_POCKET + INOX_T) if kind == "U" else 0.0
    v = dict(kind=kind, g=g)
    v["z_base_top"] = TB
    v["z_disc_bot"] = TB + g
    v["z_disc_top"] = TB + g + TD
    v["z_axis"] = v["z_disc_bot"] + TP_BOT + GAP / 2
    v["z_cb_floor"] = v["z_disc_top"] - H_CB
    v["z_piv_top"] = v["z_cb_floor"] + PIV_UP
    v["L_piv"] = v["z_piv_top"]           # desde z=0
    v["z_buje_top"] = v["z_disc_bot"] + L_BUJE
    v["H_cheek"] = v["z_axis"] - TB + 70.0  # sobre cara superior base
    v["shoe_top"] = v["z_axis"] + 70.0
    v["title"] = ("SOLUCIÓN A – PASTILLAS UHMW-PE SOBRE PISTA INOX" if kind == "U"
                  else "SOLUCIÓN B – ACERO-ACERO CON GRASA GRAFITADA")
    v["code"] = "TT300-A" if kind == "U" else "TT300-B"
    return v


def pad_positions():
    out = []
    for r, n, a0 in RINGS:
        for k in range(n):
            a = math.radians(a0 + k * 360.0 / n)
            out.append((r, a0 + k * 360.0 / n, r * math.cos(a), r * math.sin(a)))
    return out


def idx_positions():
    return [(IDX_ANG0 + 10 * k, R_IDX * math.cos(math.radians(IDX_ANG0 + 10 * k)),
             R_IDX * math.sin(math.radians(IDX_ANG0 + 10 * k))) for k in range(N_IDX)]
```

### tt300/calc.py
`tt300/calc.py` — 133 líneas

```python
"""Cálculo del accionamiento y verificaciones – tornamesa 300 tf, acero-acero con grasa grafitada."""
import math
import params as P

G = 9.80665
CAP_TF = 300.0
W = CAP_TF * G                      # kN
PHI_D = 1.10
W_DISC = 1922.0 * G / 1000          # kN, disco cajón + buje
N_F = W + W_DISC                    # carga normal en la interfaz de giro (servicio)
R_C, R_I = 1000.0, 95.0             # contacto anular (mm)
R_UNIF = 2 / 3 * (R_C ** 3 - R_I ** 3) / (R_C ** 2 - R_I ** 2) / 1000   # m
ARM = P.R_BAR * math.cos(math.radians(P.BAR_ANG0)) / 1000            # m, brazo mínimo
DELTA = (P.X_CYL - P.R_BAR * math.cos(math.radians(P.BAR_ANG0))) / 1000
LG = (P.SHOE_L - 50) / 1000         # m, separación reacciones de guía
MU_G = 0.15                         # carro / guía (bandas UHMW, con grasa)
ETA_C = 0.95                        # rendimiento del cilindro (sellos)
K_LOSS = (1 + 2 * MU_G * DELTA / LG) / ETA_C
T_PIV = 0.20 * 0.05 * W * 0.075     # kN·m, buje del pivote
A_CYL = 445e3 / 70.0                # mm² (Ø90)
P_MAX, P_OP = 700.0, 600.0          # bar
F_CYL_MAX = A_CYL * P_MAX / 10 / 1000   # kN

CASES = [
    ("Nominal: grasa grafitada limpia", 0.15, R_UNIF),
    ("DISEÑO: lubricado, límite sup. + presión cargada al borde", 0.20, 0.80),
    ("Contaminado: arena/película degradada", 0.25, 0.80),
    ("Sin lubricación (acero seco) – PROHIBIDO", 0.50, R_UNIF),
]


def case(mu, r):
    T = mu * N_F * r + T_PIV
    Fb = T / (2 * ARM)
    Fc = Fb * K_LOSS
    p = Fc * 1e3 / A_CYL * 10
    return dict(T=T, Fb=Fb, Fc=Fc, p=p, FS=F_CYL_MAX / Fc)


def mu_max(r, p_bar=P_MAX):
    Fc = A_CYL * p_bar / 10 / 1000
    T = Fc / K_LOSS * 2 * ARM
    return (T - T_PIV) / (N_F * r)


def nf(x, d=0):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


if __name__ == "__main__":
    print("W", W, "N_F", N_F, "R_unif", R_UNIF, "ARM", ARM, "DELTA", DELTA, "K_LOSS", K_LOSS, "Tpiv", T_PIV, "Fmax", F_CYL_MAX)
    for n, mu, r in CASES:
        c = case(mu, r)
        print(f"{n:55s} mu={mu} r={r:.3f} T={c['T']:.0f} Fb={c['Fb']:.0f} Fc={c['Fc']:.0f} p={c['p']:.0f} FS={c['FS']:.2f}")
    for r in (R_UNIF, 0.80, 0.94):
        print("mu_max r", round(r, 3), round(mu_max(r), 3), "@600", round(mu_max(r, 600), 3))


# ---------------- verificaciones de elementos (300 tf) ----------------
FY = 345.0                          # A572 Gr.50 / S355
F_STALL = F_CYL_MAX                 # kN: fuerza de calado (válvula de alivio 700 bar)


def verifs():
    ND = PHI_D * W + W_DISC
    A_c = math.pi * (R_C ** 2 - R_I ** 2)
    q_avg = ND * 1e3 / A_c
    q_max = q_avg * (1 + 4 * 150 / R_C * (R_C ** 2) / (R_C ** 2 + R_I ** 2))   # e = 150, anular: M/S
    # barra 4f Ø70, luz libre 100, carga en 90 central
    L, c, d = 100.0, 90.0, 70.0
    Mss = F_STALL / 4 * (L - c / 2) / 1e3          # kN·m (rotulada)
    Mfe = F_STALL * (3 * L ** 2 - c ** 2) / (24 * L) / 1e3   # kN·m (empotrada)
    Mn_bar = FY * d ** 3 / 6 / 1.67 / 1e6          # AISC F11.1, Ω = 1,67
    tau_bar = 4 * F_STALL / 2 * 1e3 / (3 * math.pi * d ** 2 / 4)
    Ew = 12.0
    tw_V = F_STALL / 2 * 1e3 / (math.pi * d * Ew)
    tw_M = Mfe * 1e6 / (math.pi * (d / 2) ** 2 * Ew)
    tw = math.hypot(tw_V, tw_M)
    Fw = 0.6 * 490 / 2.0                           # AISC J2.5, Ω = 2,0
    brg = F_STALL / 2 * 1e3 / (30 * d)             # aplastamiento en agujero de plancha
    # trinquete
    lev = (P.SHOE_X0 - P.R_BAR * math.cos(math.radians(P.BAR_ANG0)))
    Mp = F_STALL * lev / 1e3
    sp = Mp * 1e6 / (P.PAWL_H * P.PAWL_W ** 2 / 6)
    # guía embutida
    Rg = F_STALL * DELTA / LG
    brg_g = Rg * 1e3 / (10 * 150)
    Mg = Rg * 15 / 1e3
    Mn_g = FY * 150 * 40 ** 2 / 4 / 1.67 / 1e6
    # mejillas ménsula
    sc = F_STALL * (160 - 80) * 1e3 / (2 * 40 * 280 ** 2 / 6)
    # pasador Ø70 doble corte
    Ap = math.pi * 70 ** 2 / 4
    tp = F_STALL / 2 * 1e3 / Ap
    Mpin = F_STALL / 2 * (40 / 2 + 5 + 70 / 4) / 1e3   # kN·m, horquilla: a=40, holgura 5, ojal 70
    sb_pin = Mpin * 1e6 / (math.pi * 70 ** 3 / 32)
    # buje / pivote
    H = 0.055 * W
    pb = H * 1e3 / (P.D_PIV * P.L_BUJE)
    pb1 = F_STALL * 1e3 / (P.D_PIV * P.L_BUJE)
    Mpiv = H * 0.050
    spiv = Mpiv * 1e6 / (math.pi * 150 ** 3 / 32)
    # pandeo vástago
    I = math.pi * 90 ** 4 / 64
    Pcr = math.pi ** 2 * 200e3 * I / 650 ** 2 / 1e3
    rows = [
        ("Interfaz de giro: presión media / máx. (e = 150)", f"{q_avg:.2f} / {q_max:.2f} MPa", "10,0 MPa", q_max / 10, "Criterio acero/acero lubricado"),
        ("Plancha sup. 4a – flexión entre almas", "67 MPa", "207 MPa", 67 / 207, "AISC F11, Ω = 1,67"),
        ("Plancha inf. 4b – flexión entre almas", "70 MPa", "207 MPa", 70 / 207, "AISC F11, Ω = 1,67"),
        ("Almas 4d – compresión local", "13 MPa", "207 MPa", 13 / 207, "AISC J10.2"),
        ("Barra 4f Ø70 – flexión (rotulada, F calado)", f"{Mss:.2f} kN·m", f"{Mn_bar:.2f} kN·m", Mss / Mn_bar, "AISC F11.1, Ω = 1,67"),
        ("Barra 4f Ø70 – corte", f"{tau_bar:.0f} MPa", f"{0.6 * FY / 1.5:.0f} MPa", tau_bar / (0.6 * FY / 1.5), "AISC G1, Ω = 1,50"),
        ("Soldadura barra 4f – bisel 15 (E = 12), V+M", f"{tw:.0f} MPa", f"{Fw:.0f} MPa", tw / Fw, "AISC J2.5 / AWS D1.1"),
        ("Agujero Ø71 en 4a/4b – aplastamiento", f"{brg:.0f} MPa", f"{1.8 * FY / 2:.0f} MPa", brg / (0.9 * FY), "AISC J7, Ω = 2,0"),
        ("Trinquete pos 11 – flexión en boca", f"{sp:.0f} MPa", "400 MPa", sp / 400, "Fy/Nd, Nd = 2,0 (Fy 800)"),
        ("Guía pos 22 – aplastamiento en ranura", f"{brg_g:.0f} MPa", f"{0.9 * FY:.0f} MPa", brg_g / (0.9 * FY), "AISC J7, Ω = 2,0"),
        ("Guía pos 22 – flexión en raíz", f"{Mg:.2f} kN·m", f"{Mn_g:.2f} kN·m", Mg / Mn_g, "AISC F11.1, Ω = 1,67"),
        ("Mejillas ménsula pos 2 – flexión base", f"{sc:.0f} MPa", "207 MPa", sc / 207, "AISC F11 / CJP J2"),
        ("Pasador Ø70 – flexión (horquilla 40/80)", f"{sb_pin:.0f} MPa", "325 MPa", sb_pin / 325, "Fy/Nd, Nd = 2,0 (Fy 650)"),
        ("Pasador Ø70 – corte doble", f"{tp:.0f} MPa", "188 MPa", tp / 188, "ASME BTH-1 3-2.2: Fy/(Nd·√3)"),
        ("Buje pos 6 – presión (H = 5,5 % W)", f"{pb:.1f} MPa", "30 MPa", pb / 30, "Fabricante bronce-grafito"),
        ("Pivote pos 5 – flexión", f"{spiv:.1f} MPa", "325 MPa", spiv / 325, "Fy/Nd, Nd = 2,0"),
        ("Vástago Ø90 – pandeo (L = 650, rótulas)", f"{F_STALL:.0f} kN", f"{Pcr / 3:.0f} kN", F_STALL / (Pcr / 3), "Euler, FS = 3,0"),
    ]
    extra = dict(q_avg=q_avg, q_max=q_max, Mss=Mss, Mfe=Mfe, tw=tw, lev=lev, Rg=Rg, pb1=pb1, Pcr=Pcr, H=H)
    return rows, extra


if __name__ == "__main__":
    r, e = verifs()
    for x in r: print(f"{x[0]:50s} {x[1]:>18s} {x[2]:>12s} FU={x[3]:.2f}")
    print(e)
```

### tt300/common.py
`tt300/common.py` — 142 líneas

```python
"""Datos comunes: BOM, notas, utilidades de colocación."""
import json, math
import params as P

G = 9.80665
W_KN = 300 * G
ND = 1.10 * W_KN
A_CYL = 445e3 / 70.0          # mm2 (445 kN @ 700 bar)
ARM = 0.936                   # brazo mín. de la fuerza sobre la barra (m)


def masses(v):
    return {int(k): val for k, val in json.load(open(f"/home/claude/tt300/out/{v['code']}_mass.json")).items()}


def pressure_bar(mu, v):
    r = 0.593 if v["kind"] == "U" else 0.667
    T = mu * W_KN * r + 3.0
    F = T / (2 * ARM)
    return F * 1e3 / A_CYL * 10


def bom(v):
    m = masses(v)
    U = v["kind"] == "U"
    rows = [
        (1, "Placa base 2400×2000×80 mec. (2 ranuras 40H8×10)", "1", "ASTM A572 Gr.50 – Z35", m[1]),
        (2, "Ménsula de reacción (conj. soldado)", "4", "ASTM A572 Gr.50", m[2] / 4),
        (3, "Oreja de izaje e=40", "4", "ASTM A572 Gr.50", m[3] / 4),
        (4, "Disco cajón Ø2000×160 (conj. soldado 4a–4f)", "1", "ASTM A572 Gr.50 – Z35", m[4]),
        (5, f"Pivote Ø150×{v['L_piv']:.0f}", "1", "42CrMo4+QT (EN 10083-3)", m[5]),
        (6, "Buje Ø190/Ø150×100 autolubricado", "1", "CuAl10Ni5Fe4 + grafito", m[6]),
        (7, "Tapa retenedora Ø240×20", "1", "S355J2", m[7]),
        (8, "Perno ISO 4762 M20×45 + arand. Nord-Lock", "6", "10.9 zincado laminar", m[8] / 6),
        (9, "Cilindro hidr. doble efecto 50 t, 700 bar, carrera 200", "2", "Comercial (ver lám. 4)", m[9] / 2),
        (10, "Carro de empuje 300×130×" + f"{v['shoe_top'] - P.TB:.0f}" + " (guiado)", "2", "S355J2+N", m[10] / 2),
        (11, "Trinquete 245×85×90 (asiento R36)", "2", "34CrNiMo6+QT 300–350 HB", m[11] / 2),
        (12, "Pasador Ø70 (ménsula y vástago)", "4", "42CrMo4+QT", m[12] / 4),
        (13, "Resorte trinquete Ø50 + tapa + manilla; clip R Ø8", "2+4", "Comercial", 0.6),
        (14, "Faldón de sello e=5, h=" + f"{v['z_disc_bot'] + P.TP_BOT - P.TB:.0f}" + ", L≈6300", "1", "NBR 70 Shore A", m[14]),
        (15, "Fleje de apriete 25×6 rolado Ø2022", "1", "S235JR galvanizado", m[15]),
        (16, "Perno ISO 4017 M8×20 + arandela", "36", "Inox A2-70", 0.02),
        (17, "Tapón prisionero M30×25 (agujeros izaje disco)", "4", "Acero 8.8 zincado", 0.1),
        (18, "Cáncamo giratorio M30, WLL ≥ 2,5 t (suelto)", "4", "Comercial", 2.2),
    ]
    if U:
        rows += [
            (19, "Pastilla deslizante Ø170×10", "34+4", "UHMW-PE (PE1000)", m[19] / 34),
            (20, "Pista inox A Ø810/Ø390×3", "1", "AISI 316L (1.4404)", m[20]),
            (21, "Pista inox B Ø1680/Ø880×3", "1", "AISI 316L (1.4404)", m[21]),
        ]
    else:
        rows += [
            (19, "Grasa grafitada NLGI 2 (≥10 % grafito), 0,3–0,5 mm/cara", "≈2,5 kg/apl.", "Ver especificación lám. D-02", 0.0),
            (20, "Grasera recta DIN 71412 M10×1 + tapa", "4", "Acero zincado", 0.05),
        ]
    rows.append((22, "Guía de carro 40×40×850 (embutida 10 en pos 1)", "2", "S355J2", m[22] / 2))
    return rows


def total_mass(v):
    tot = 0
    for pos, d, q, mat, mu in bom(v):
        try:
            n = int(q.split("+")[0])
        except ValueError:
            n = 1 if mu else 0
        tot += n * mu
    return tot


def notes_general(v):
    import calc as K
    d = K.case(0.20, 0.80)
    c3 = K.case(0.25, 0.80)
    n = [
        "NOTAS GENERALES",
        "1. CAPACIDAD NOMINAL (WLL): 300 tf = 2 942 kN. Factor dinámico de diseño φd = 1,10 (giro hidráulico lento).",
        "   Excentricidad del CG de la carga respecto del pivote ≤ 150 mm. Carga solo dentro de Ø1600 sobre parrilla",
        "   de reparto o ≥ 8 apoyos simétricos. PROHIBIDO cargas puntuales sobre el disco.",
        "2. NORMAS: AISC 360-22 (ASD); ASME BTH-1 Cat. A (Nd = 2,0, referencial elementos mecánicos);",
        "   AWS D1.1/D1.1M:2020; ISO 2768-mK; ISO 1101; ISO 1302.",
        "3. MATERIALES: certificado EN 10204 3.1. Planchas pos 1 y 4: UT según ASTM A578 nivel B, calidad Z35.",
        "4. SOLDADURA: WPS/PQR calificados AWS D1.1. Electrodo E7018 / ER70S-6.",
        "   Precalentamiento ≥ 110 °C en espesores > 65 mm (AWS D1.1 Tabla 5.8, Cat. B). CJP: UT 100 %. Filetes: MT 100 %.",
        "5. Conjuntos soldados pos 1+2+3+22 y pos 4: alivio de tensiones 590–620 °C antes del mecanizado final.",
        "6. PROTECCIÓN: Sa 2½ + epóxico rico en zinc 75 µm + epóxico 125 µm + PU 50 µm (ISO 12944, C4).",
        "   Sin pintura: caras de giro, alojamientos, agujeros de pasadores, buje y roscas.",
        "7. INTERFAZ DE GIRO: contacto pleno acero-acero (cara sup. pos 1 / cara inf. 4b) con GRASA GRAFITADA pos 19",
        "   en ambas caras, ranuras de lubricación en 4b y 4 graseras pos 20 (relubricación sin levantar el disco).",
        "   OBLIGATORIO lubricar antes de cada operación. Acero seco (μ 0,5–0,8) NO gira con este accionamiento.",
        "8. ACCIONAMIENTO: 2 cilindros pos 9 en par sobre carros guiados pos 10; el trinquete pos 11 empuja",
        "   directo una barra vertical Ø70 del disco (36 barras c/10° en R940). Carrera 200 = 36 libre + 164 = 10°/ciclo.",
        f"   Fuerza de diseño por cilindro {d['Fc']:.0f} kN ({d['p']:.0f} bar, μ = 0,20); capacidad 445 kN a 700 bar (FS {d['FS']:.2f}).".replace("FS 1.", "FS 1,"),
        f"   Detener y relubricar si p > 600 bar (μ > 0,24). Ver cálculo completo en lámina D-02.",
        "   Rótulas GE70 en ambos ojales. PROHIBIDO empujar con un solo cilindro (válvula de bloqueo en paralelo).",
        "   Giro antihorario: carros en x = ±1085 con ménsulas (+1085;-818) y (-1085;+818). Horario: invertir carro y ménsula.",
        "9. APOYO: base totalmente apoyada sobre losa de H.A. o mats rígidos; pendiente ≤ 0,5 %.",
        "   Presión de contacto bajo base: 0,62 MPa media / 0,90 MPa máx. (e = 150 mm).",
        "10. ENSAYO: giro 360° a 1,0 WLL registrando presión; estático 1,25 WLL si existe marco de reacción;",
        "    MT de soldaduras pos 2/3/22 posterior al ensayo.",
        "11. Cilindro: L0 = 450 entre ojales (retraído); verificar con proveedor y ajustar posición de pos 2 si difiere.",
    ]
    return n


def fmt_kg(x):
    return f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


class Place:
    """Transforma coordenadas de modelo (pantalla) a papel."""
    def __init__(self, O, s, m0=(0.0, 0.0)):
        self.O, self.s, self.m0 = O, s, m0

    def __call__(self, p):
        return (self.O[0] + (p[0] - self.m0[0]) * self.s, self.O[1] + (p[1] - self.m0[1]) * self.s)

    def polys(self, sh, polys, layer="VIS"):
        for pl in polys:
            pts = [self(p) for p in pl]
            if len(pts) == 2:
                sh.line(pts[0], pts[1], layer)
            else:
                sh.pline(pts, layer)

    def hatches(self, sh, hatches, small=(14, 20, 21)):
        ang = {1: 0, 2: 90, 3: 90, 4: 90, 5: 0, 6: 0, 7: 90, 8: 0, 10: 0, 11: 90, 12: 90, 15: 0, 19: 0}
        pat = {6: "ANSI33", 19: "ANSI37"}
        for pos, outer, holes in hatches:
            o = [self(p) for p in outer]
            hh = [[self(p) for p in h] for h in holes]
            if pos in small:
                sh.hatch_poly(o, hh, solid=True)
            else:
                sh.hatch_poly(o, hh, scale=0.55 if pos != 19 else 0.45, angle=ang.get(pos, 45), pattern=pat.get(pos, "ANSI31"))


def bbox(polys):
    xs = [p[0] for pl in polys for p in pl]
    ys = [p[1] for pl in polys for p in pl]
    return min(xs), min(ys), max(xs), max(ys)
```

### tt300/draw.py
`tt300/draw.py` — 318 líneas

```python
"""Mini-librería de dibujo técnico sobre ezdxf (coordenadas de papel en mm, A1 841x594)."""
import math
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

W, H = 841.0, 594.0
OVR = {}
TXT_STYLE = "STD"


def new_doc():
    doc = ezdxf.new("R2018", units=4)
    doc.styles.add(TXT_STYLE, font="LiberationSans-Regular.ttf")
    doc.styles.add("STDB", font="LiberationSans-Bold.ttf")
    lt = doc.linetypes
    lt.add("OCULTO", pattern=[4.5, 3.0, -1.5], description="__ __ __")
    lt.add("EJE", pattern=[22.0, 14.0, -3.0, 2.0, -3.0], description="__ . __")
    lt.add("FANTASMA", pattern=[26.0, 14.0, -3.0, 2.0, -2.0, 2.0, -3.0], description="__ . . __")
    for name, lw, ltype in [("VIS", 50, "CONTINUOUS"), ("FINA", 18, "CONTINUOUS"), ("OCU", 25, "OCULTO"),
                            ("EJE", 18, "EJE"), ("COTA", 18, "CONTINUOUS"), ("TXT", 25, "CONTINUOUS"),
                            ("ACH", 13, "CONTINUOUS"), ("MARCO", 70, "CONTINUOUS"), ("FANT", 18, "FANTASMA")]:
        doc.layers.add(name, color=7, lineweight=lw, linetype=ltype)
    doc.header["$LTSCALE"] = 1.0
    doc.header["$PSLTSCALE"] = 0
    return doc


class Sheet:
    def __init__(self):
        self.doc = new_doc()
        self.m = self.doc.modelspace()

    # ---------- primitivas ----------
    def line(self, p1, p2, layer="VIS"):
        self.m.add_line(p1, p2, dxfattribs={"layer": layer})

    def pline(self, pts, layer="VIS", closed=False):
        self.m.add_lwpolyline(pts, close=closed, dxfattribs={"layer": layer})

    def rect(self, x0, y0, x1, y1, layer="VIS"):
        self.pline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, closed=True)

    def circle(self, c, r, layer="VIS"):
        self.m.add_circle(c, r, dxfattribs={"layer": layer})

    def arc(self, c, r, a0, a1, layer="VIS"):
        self.m.add_arc(c, r, a0, a1, dxfattribs={"layer": layer})

    def text(self, s, p, h=2.5, align="BOTTOM_LEFT", rot=0.0, layer="TXT", bold=False):
        t = self.m.add_text(s, height=h, rotation=rot,
                            dxfattribs={"layer": layer, "style": "STDB" if bold else TXT_STYLE})
        t.set_placement(p, align=TA[align])
        return t

    def mtext(self, lines, p, h=2.5, ls=1.6, bold_first=False, width=None):
        y = p[1]
        for i, s in enumerate(lines):
            self.text(s, (p[0], y), h, "TOP_LEFT", bold=(bold_first and i == 0))
            y -= h * ls
        return y

    def hatch_poly(self, outer, holes=(), scale=0.9, angle=0.0, pattern="ANSI31", solid=False):
        h = self.m.add_hatch(color=7, dxfattribs={"layer": "ACH"})
        if solid:
            h.set_solid_fill(color=7)
        else:
            h.set_pattern_fill(pattern, scale=scale, angle=angle)
        h.paths.add_polyline_path(outer, is_closed=True, flags=1)
        for hh in holes:
            h.paths.add_polyline_path(hh, is_closed=True, flags=16)

    def centerlines(self, c, r, ext=3.0):
        self.line((c[0] - r - ext, c[1]), (c[0] + r + ext, c[1]), "EJE")
        self.line((c[0], c[1] - r - ext), (c[0], c[1] + r + ext), "EJE")

    def cross(self, c, s=2.0):
        self.line((c[0] - s, c[1]), (c[0] + s, c[1]), "FINA")
        self.line((c[0], c[1] - s), (c[0], c[1] + s), "FINA")

    # ---------- acotado ----------
    def arrow(self, tip, ang, size=2.8, w=0.9):
        ca, sa = math.cos(ang), math.sin(ang)
        bx, by = tip[0] - size * ca, tip[1] - size * sa
        p1 = (bx - w * sa, by + w * ca)
        p2 = (bx + w * sa, by - w * ca)
        self.m.add_solid([tip, p1, p2], dxfattribs={"layer": "COTA"})

    def dim(self, p1, p2, off, txt, orient="h", h=2.5, txt_shift=0.0, outside=False):
        """Cota lineal. orient 'h' (mide dx), 'v' (mide dy), 'a' alineada. off: distancia firmada de la línea de cota."""
        x1, y1 = p1
        x2, y2 = p2
        if orient == "h":
            yd = (y1 if off >= 0 and y1 >= y2 else y2 if off >= 0 else min(y1, y2)) + off
            yd = max(y1, y2) + off if off >= 0 else min(y1, y2) + off
            a, b = (x1, yd), (x2, yd)
            for (px, py) in (p1, p2):
                s = 1.0 if yd > py else -1.0
                self.line((px, py + s * 1.0), (px, yd + s * 2.0), "COTA")
        elif orient == "v":
            xd = max(x1, x2) + off if off >= 0 else min(x1, x2) + off
            a, b = (xd, y1), (xd, y2)
            for (px, py) in (p1, p2):
                s = 1.0 if xd > px else -1.0
                self.line((px + s * 1.0, py), (xd + s * 2.0, py), "COTA")
        else:
            ang = math.atan2(y2 - y1, x2 - x1)
            nx, ny = -math.sin(ang) * off, math.cos(ang) * off
            a, b = (x1 + nx, y1 + ny), (x2 + nx, y2 + ny)
            for (px, py), q in ((p1, a), (p2, b)):
                self.line((px, py), (q[0] + nx / max(abs(off), 1e-9) * 2, q[1] + ny / max(abs(off), 1e-9) * 2), "COTA")
        self.line(a, b, "COTA")
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if outside or L < 7:
            self.arrow(a, ang); self.arrow(b, ang + math.pi)
            self.line(a, (a[0] - 5 * math.cos(ang), a[1] - 5 * math.sin(ang)), "COTA")
            self.line(b, (b[0] + 5 * math.cos(ang), b[1] + 5 * math.sin(ang)), "COTA")
        else:
            self.arrow(a, ang + math.pi); self.arrow(b, ang)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        deg = math.degrees(ang)
        if deg > 90.01 or deg < -89.99:
            deg += 180
        r = math.radians(deg)
        tx = mx - math.sin(r) * 1.0 + math.cos(r) * txt_shift
        ty = my + math.cos(r) * 1.0 + math.sin(r) * txt_shift
        self.text(txt, (tx, ty), h, "BOTTOM_CENTER", rot=deg)

    def dim_dia(self, c, r, ang_deg, txt, h=2.5, ext=8.0):
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        p1 = (c[0] + r * ca, c[1] + r * sa)
        p2 = (c[0] - r * ca, c[1] - r * sa)
        p3 = (c[0] + (r + ext) * ca, c[1] + (r + ext) * sa)
        self.line(p2, p3, "COTA")
        self.arrow(p1, a)
        self.arrow(p2, a + math.pi)
        sh = 1 if ca >= 0 else -1
        p4 = (p3[0] + sh * (len(txt) * h * 0.62 + 1), p3[1])
        self.line(p3, p4, "COTA")
        self.text(txt, (p3[0] + sh * 0.5, p3[1] + 0.8), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")

    def dim_rad(self, c, r, ang_deg, txt, h=2.5, ext=8.0):
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        p1 = (c[0] + r * ca, c[1] + r * sa)
        p3 = (c[0] + (r + ext) * ca, c[1] + (r + ext) * sa)
        self.line(c, p3, "COTA")
        self.arrow(p1, a)
        sh = 1 if ca >= 0 else -1
        p4 = (p3[0] + sh * (len(txt) * h * 0.62 + 1), p3[1])
        self.line(p3, p4, "COTA")
        self.text(txt, (p3[0] + sh * 0.5, p3[1] + 0.8), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")

    def leader(self, p, q, txt, h=2.5, dot=False, lines=None):
        """Flecha en p, codo en q, texto horizontal."""
        self.line(p, q, "COTA")
        if dot:
            self.m.add_circle(p, 0.6, dxfattribs={"layer": "COTA"})
            self.hatch_poly([(p[0] + 0.6 * math.cos(t / 8 * math.pi * 2), p[1] + 0.6 * math.sin(t / 8 * math.pi * 2)) for t in range(8)], solid=True)
        else:
            self.arrow(p, math.atan2(p[1] - q[1], p[0] - q[0]))
        sh = 1 if q[0] >= p[0] else -1
        txts = [txt] if lines is None else lines
        wmax = max(len(t) for t in txts) * h * 0.58 + 1
        self.line(q, (q[0] + sh * wmax, q[1]), "COTA")
        y = q[1] + 0.8
        for i, t in enumerate(txts):
            if i == 0:
                self.text(t, (q[0] + sh * 0.5, y), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")
            else:
                self.text(t, (q[0] + sh * 0.5, q[1] - 1.0 - (i - 1) * h * 1.5), h, "TOP_LEFT" if sh > 0 else "TOP_RIGHT")

    def balloon(self, p, q, n, r=4.5):
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        ux, uy = (q[0] - p[0]) / d, (q[1] - p[1]) / d
        self.line(p, (q[0] - ux * r, q[1] - uy * r), "COTA")
        self.m.add_circle(p, 0.7, dxfattribs={"layer": "COTA"})
        self.hatch_poly([(p[0] + 0.7 * math.cos(t / 10 * math.pi * 2), p[1] + 0.7 * math.sin(t / 10 * math.pi * 2)) for t in range(10)], solid=True)
        self.circle(q, r, "FINA")
        self.text(str(n), q, 3.2, "MIDDLE_CENTER", bold=True)

    def view_title(self, p, title, scale, h=4.0):
        self.text(title, p, h, "BOTTOM_CENTER", bold=True)
        w = len(title) * h * 0.62
        self.line((p[0] - w / 2, p[1] - 1.2), (p[0] + w / 2, p[1] - 1.2), "VIS")
        self.text(scale, (p[0], p[1] - 2.5), 2.8, "TOP_CENTER")

    def section_mark(self, p, ang_deg, label, length=8.0):
        """Flecha de corte en p, apuntando ang (dirección de mirada)."""
        a = math.radians(ang_deg)
        q = (p[0] + length * math.cos(a), p[1] + length * math.sin(a))
        self.line(p, q, "VIS")
        self.arrow(q, a, size=3.5, w=1.3)
        self.text(label, (q[0] + 3 * math.cos(a), q[1] + 3 * math.sin(a)), 5.0, "MIDDLE_CENTER", bold=True)

    def detail_circle(self, c, r, label):
        self.circle(c, r, "FANT")
        self.text(label, (c[0] + r * 0.72 + 2, c[1] + r * 0.72 + 2), 5.0, "BOTTOM_LEFT", bold=True)

    def finish(self, p, ra, h=2.5):
        """Símbolo de rugosidad (ISO 1302) con Ra."""
        x, y = p
        self.pline([(x - 2.2, y + 3.8), (x, y), (x + 4.4, y + 7.6), (x + 12, y + 7.6)], "COTA")
        self.line((x - 2.2, y + 3.8), (x + 2.2, y + 3.8), "COTA")
        self.text(ra, (x + 4.6, y + 8.2), h, "BOTTOM_LEFT")

    def weld(self, p, q, kind, size, other=False, all_round=False, note="", h=2.5):
        """Símbolo de soldadura AWS A2.4 simplificado. kind 'fillet' | 'cjp' | 'bevel'."""
        self.line(p, q, "COTA")
        self.arrow(p, math.atan2(p[1] - q[1], p[0] - q[0]))
        sh = 1 if q[0] >= p[0] else -1
        L = 26.0
        r = (q[0] + sh * L, q[1])
        self.line(q, r, "COTA")
        mx = q[0] + sh * L * 0.45
        ys = [-1] + ([1] if other else [])
        for side in ys:
            if kind == "fillet":
                self.pline([(mx - 2.2, q[1]), (mx - 2.2, q[1] + side * 4.4), (mx + 2.2, q[1])], "COTA")
            else:
                self.pline([(mx - 2.4, q[1] + side * 4.6), (mx, q[1]), (mx + 2.4, q[1] + side * 4.6)] if kind == "cjp"
                           else [(mx - 2.2, q[1]), (mx - 2.2, q[1] + side * 4.6), (mx + 2.4, q[1] + side * 4.6)], "COTA")
            self.text(size, (mx - sh * 4.0, q[1] + side * 2.6), h, ("MIDDLE_RIGHT" if sh > 0 else "MIDDLE_LEFT"))
        if all_round:
            self.circle(q, 1.6, "COTA")
        if note:
            self.pline([(r[0], r[1]), (r[0] + sh * 3, r[1] + 3), ], "COTA")
            self.pline([(r[0], r[1]), (r[0] + sh * 3, r[1] - 3), ], "COTA")
            self.text(note, (r[0] + sh * 4, r[1]), h, "MIDDLE_LEFT" if sh > 0 else "MIDDLE_RIGHT")

    def table(self, x0, y0, cols, rows, rh=6.0, h=2.3, header_h=None, bold_header=True):
        """cols: lista de (titulo, ancho, align). rows: lista de listas. Dibuja desde y0 hacia abajo. Retorna y final."""
        header_h = header_h or rh * 1.3
        widths = [c[1] for c in cols]
        Wt = sum(widths)
        y = y0
        allrows = [[c[0] for c in cols]] + rows
        for i, row in enumerate(allrows):
            rhh = header_h if i == 0 else rh
            self.line((x0, y), (x0 + Wt, y), "VIS" if i <= 1 else "FINA")
            x = x0
            for j, cell in enumerate(row):
                al = cols[j][2] if i else "C"
                if al == "C":
                    self.text(str(cell), (x + widths[j] / 2, y - rhh / 2), h, "MIDDLE_CENTER", bold=(i == 0 and bold_header))
                elif al == "R":
                    self.text(str(cell), (x + widths[j] - 1.2, y - rhh / 2), h, "MIDDLE_RIGHT")
                else:
                    self.text(str(cell), (x + 1.2, y - rhh / 2), h, "MIDDLE_LEFT", bold=(i == 0 and bold_header))
                x += widths[j]
            y -= rhh
        self.line((x0, y), (x0 + Wt, y), "VIS")
        x = x0
        for wv in widths + [0]:
            self.line((x, y0), (x, y), "FINA" if 0 < x - x0 < Wt else "VIS")
            x += wv
        return y

    # ---------- formato ----------
    def frame(self, v, sheet_no, n_sheets, title2, scale_txt, rev="0", plano=None):
        if OVR:
            sheet_no, n_sheets, plano = OVR.get("no", sheet_no), OVR.get("n", n_sheets), OVR.get("plano", plano)
            title2 = OVR.get("title", title2)
        self.rect(0, 0, W, H, "FINA")
        self.rect(20, 10, W - 10, H - 10, "MARCO")
        # zonas
        for i in range(1, 8):
            x = 20 + i * (W - 30) / 8
            self.line((x, H - 10), (x, H - 5), "FINA"); self.line((x, 10), (x, 5), "FINA")
        for i in range(8):
            self.text(str(i + 1), (20 + (i + 0.5) * (W - 30) / 8, H - 7.5), 2.5, "MIDDLE_CENTER")
        for i, L in enumerate("FEDCBA"):
            y = 10 + (i + 0.5) * (H - 20) / 6
            self.text(L, (15, y), 2.5, "MIDDLE_CENTER")
        # rótulo 180 x 62
        x0, y0, x1 = W - 10 - 180, 10, W - 10
        y1 = y0 + 62
        self.rect(x0, y0, x1, y1, "MARCO")
        rows = [y0 + 10, y0 + 20, y0 + 30, y0 + 44]
        for yy in rows:
            self.line((x0, yy), (x1, yy), "FINA")
        self.line((x0 + 60, y0), (x0 + 60, y0 + 30), "FINA")
        self.line((x0 + 120, y0), (x0 + 120, y0 + 30), "FINA")
        self.text(f"PROYECTO: {v['proj']}", (x0 + 2, y1 - 3), 3.2, "TOP_LEFT", bold=True)
        self.text(v["title"], (x0 + 2, y1 - 9.5), 2.6, "TOP_LEFT")
        self.text(title2, (x0 + 2, y0 + 41.5), 3.6, "TOP_LEFT", bold=True)
        self.text("EMITIDO PARA REVISIÓN – NO APTO PARA FABRICACIÓN HASTA APROBACIÓN", (x0 + 2, y0 + 32), 2.2, "BOTTOM_LEFT", bold=True)
        cells = [("ELABORÓ", "—", 0, 2), ("REVISÓ", "—", 1, 2), ("APROBÓ", "—", 2, 2),
                 ("ESCALA", scale_txt, 0, 1), ("FECHA", "21-10-2026", 1, 1), ("FORMATO", "A1", 2, 1),
                 ("PLANO N°", plano or f"{v['code']}-{sheet_no:02d}", 0, 0), ("LÁMINA", f"{sheet_no} de {n_sheets}", 1, 0), ("REV.", rev, 2, 0)]
        for lab, val, cx, ry in cells:
            xx = x0 + cx * 60
            yy = y0 + ry * 10
            self.text(lab, (xx + 1.5, yy + 8.6), 1.8, "TOP_LEFT")
            self.text(val, (xx + 30, yy + 3.2), 3.0 if ry == 0 else 2.6, "MIDDLE_CENTER", bold=(ry == 0))
        self.text("Cotas en mm salvo indicación. No medir sobre el plano.", (x0, y1 + 1.5), 2.0, "BOTTOM_LEFT")
        self.text("Rev. 0 (21-10-2026): emisión para revisión – capacidad 300 tf, interfaz acero-acero con grasa grafitada.", (20, 6.5), 2.0, "BOTTOM_LEFT")

    # ---------- salida ----------
    def save(self, dxf_path, pdf_path=None):
        self.doc.saveas(dxf_path)
        if pdf_path:
            return render_pdf(self.doc, pdf_path)


def render_pdf(doc, pdf_path):
    from ezdxf.addons.drawing import Frontend, RenderContext, pymupdf, layout, config
    backend = pymupdf.PyMuPdfBackend()
    cfg = config.Configuration(color_policy=config.ColorPolicy.BLACK,
                               background_policy=config.BackgroundPolicy.WHITE,
                               lineweight_scaling=1.0,
                               min_lineweight=0.13)
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace(), finalize=True)
    page = layout.Page(W, H, layout.Units.mm, margins=layout.Margins.all(0))
    pdf = backend.get_pdf_bytes(page, settings=layout.Settings(fit_page=False, scale=1.0))
    open(pdf_path, "wb").write(pdf)
    return pdf_path
```

### tt300/hlr.py
`tt300/hlr.py` — 172 líneas

```python
"""Proyección con líneas ocultas (HLR) y cortes desde el modelo CadQuery."""
import math
import cadquery as cq
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union, polygonize

VIEWS = {
    "top": ((0, 0, 1), (1, 0, 0)),
    "front": ((0, -1, 0), (1, 0, 0)),       # mira hacia +y, pantalla (x, z)
    "back": ((0, 1, 0), (-1, 0, 0)),
    "right": ((1, 0, 0), (0, 1, 0)),        # mira hacia -x, pantalla (y, z)
    "left": ((-1, 0, 0), (0, -1, 0)),
    "iso": ((1, -1, 1), (1, 1, 0)),
    "iso2": ((1, -1.25, 0.9), (1.25, 1, 0)),
}


def basis(view):
    d, x = VIEWS[view]
    dn = [c / math.sqrt(sum(k * k for k in d)) for k in [0] for c in d]
    n = math.sqrt(sum(c * c for c in d)); d = [c / n for c in d]
    n = math.sqrt(sum(c * c for c in x)); x = [c / n for c in x]
    y = [d[1] * x[2] - d[2] * x[1], d[2] * x[0] - d[0] * x[2], d[0] * x[1] - d[1] * x[0]]
    return d, x, y


def proj_pt(p, view):
    d, x, y = basis(view)
    return (sum(a * b for a, b in zip(p, x)), sum(a * b for a, b in zip(p, y)))


def _edges_to_polys(comp, tol):
    out = []
    if comp is None or comp.IsNull():
        return out
    for e in cq.Shape.cast(comp).Edges():
        try:
            if e.geomType() == "LINE":
                a, b = e.startPoint(), e.endPoint()
                out.append([(a.x, a.y), (b.x, b.y)])
            else:
                L = e.Length()
                n = max(6, min(400, int(L / tol)))
                pts = [e.positionAt(i / n) for i in range(n + 1)]
                out.append([(p.x, p.y) for p in pts])
        except Exception:
            pass
    return out


def hlr(shape, view, tol=2.0, hidden=False):
    d, x = VIEWS[view]
    ax = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*d), gp_Dir(*x))
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    algo.Projector(HLRAlgo_Projector(ax))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = _edges_to_polys(h.VCompound(), tol) + _edges_to_polys(h.OutLineVCompound(), tol)
    hid = []
    if hidden:
        hid = _edges_to_polys(h.HCompound(), tol) + _edges_to_polys(h.OutLineHCompound(), tol)
    return vis, hid


NOCUT = {5, 8, 9, 11, 12, 13, 16}


def section(parts, view, plane_pt, keep_dir, tol=2.0, hidden=False, only=None, nocut=NOCUT):
    """parts: [(pos, shape)] cq.Shape. Corta con plano por plane_pt normal keep_dir (se conserva lado +keep_dir).
    Devuelve (vis, hid, hatch) con hatch = [(pos, outer, holes)] en coords de pantalla."""
    big = 20000
    nx, ny, nz = keep_dir
    # semiespacio a eliminar: caja del lado -keep_dir
    c = (plane_pt[0] - nx * big / 2, plane_pt[1] - ny * big / 2, plane_pt[2] - nz * big / 2)
    cutter = cq.Solid.makeBox(big, big, big, pnt=cq.Vector(c[0] - big / 2 * (1 - abs(nx)) - (big / 2 if nx else 0) + (big / 2 if nx else 0),
                                                          c[1], c[2])) if False else None
    halfbox = cq.Solid.makeBox(big, big, big).translate(cq.Vector(-big / 2, -big / 2, -big / 2))
    halfbox = halfbox.translate(cq.Vector(plane_pt[0] - nx * big / 2, plane_pt[1] - ny * big / 2, plane_pt[2] - nz * big / 2))
    kept, hatches = [], []
    plane = cq.Face.makePlane(big, big, basePnt=cq.Vector(*plane_pt), dir=cq.Vector(*keep_dir))
    for pos, shp in parts:
        if only and pos not in only:
            continue
        if pos in nocut:
            kept.append(shp)
            continue
        try:
            k = shp.cut(halfbox)
        except Exception:
            k = shp
        if k.isValid() and k.Volume() > 1e-3:
            kept.append(k)
        try:
            sec = shp.intersect(plane)
            for f in sec.Faces():
                segs = []
                for e in f.Edges():
                    if e.geomType() == "LINE":
                        pts = [e.startPoint(), e.endPoint()]
                    else:
                        n = max(8, min(300, int(e.Length() / tol)))
                        pts = [e.positionAt(i / n) for i in range(n + 1)]
                    pp = [proj_pt((p.x, p.y, p.z), view) for p in pts]
                    pp = [(round(x * 10) / 10, round(y * 10) / 10) for x, y in pp]
                    if len(pp) > 2 and abs(pp[0][0] - pp[-1][0]) < 0.6 and abs(pp[0][1] - pp[-1][1]) < 0.6:
                        pp[-1] = pp[0]
                    segs.append(LineString(pp))
                polys = list(polygonize(unary_union(segs)))
                g = None
                for pg in polys:
                    g = pg if g is None else g.symmetric_difference(pg)
                if g is None:
                    continue
                for gg in getattr(g, "geoms", [g]):
                    if gg.geom_type == "Polygon" and gg.area > 0.5:
                        hatches.append((pos, list(gg.exterior.coords), [list(i.coords) for i in gg.interiors]))
        except Exception as ex:
            print("sec fail", pos, ex)
    comp = cq.Compound.makeCompound(kept)
    vis, hid = hlr(comp, view, tol, hidden)
    return vis, hid, hatches


def _wire_pts(w, tol):
    pts = []
    for e in w.Edges():
        if e.geomType() == "LINE":
            seg = [e.startPoint(), e.endPoint()]
        else:
            n = max(8, min(300, int(e.Length() / tol)))
            seg = [e.positionAt(i / n) for i in range(n + 1)]
        if pts and (pts[-1] - seg[0]).Length > 1e-3 and (pts[-1] - seg[-1]).Length < 1e-3:
            seg = seg[::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts


def clip_polys(polys, win):
    """win=(x0,y0,x1,y1) en coords de pantalla del modelo."""
    b = box(*win)
    out = []
    for p in polys:
        if len(p) < 2:
            continue
        g = LineString(p).intersection(b)
        if g.is_empty:
            continue
        geoms = getattr(g, "geoms", [g])
        for gg in geoms:
            if gg.geom_type == "LineString" and len(gg.coords) >= 2:
                out.append(list(gg.coords))
    return out


def clip_hatch(hatches, win):
    b = box(*win)
    out = []
    for pos, outer, holes in hatches:
        try:
            pg = Polygon(outer, holes).buffer(0)
            g = pg.intersection(b)
        except Exception:
            continue
        for gg in getattr(g, "geoms", [g]):
            if gg.geom_type == "Polygon" and gg.area > 1:
                out.append((pos, list(gg.exterior.coords), [list(i.coords) for i in gg.interiors]))
    return out
```

### tt300/model3d.py
`tt300/model3d.py` — 268 líneas

```python
"""Modelo 3D CadQuery de la tornamesa 500 tf (variantes U y S)."""
import math
import cadquery as cq
import params as P

C = {
    "steel": cq.Color(0.55, 0.57, 0.60), "disc": cq.Color(0.98, 0.78, 0.10),
    "base": cq.Color(0.20, 0.33, 0.55), "bronze": cq.Color(0.72, 0.50, 0.20),
    "pin": cq.Color(0.35, 0.35, 0.38), "uhmw": cq.Color(0.95, 0.95, 0.92),
    "inox": cq.Color(0.82, 0.84, 0.87), "nbr": cq.Color(0.08, 0.08, 0.08),
    "cyl": cq.Color(0.85, 0.15, 0.12), "graph": cq.Color(0.25, 0.25, 0.25),
}


def cyl(r, h, x=0, y=0, z=0):
    return cq.Workplane("XY").workplane(offset=z).center(x, y).circle(r).extrude(h)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def base_plate(v):
    b = cq.Workplane("XY").box(P.BX, P.B, P.TB, centered=(True, True, False))
    b = b.cut(cyl(P.D_PIV / 2, P.TB))
    for sx in (1, -1):   # ranuras 40 H8 x 10 para guías embutidas pos 22
        b = b.cut(box(sx * P.X_CYL - P.RAIL_W / 2, sx * P.X_CYL + P.RAIL_W / 2, -P.RAIL_L / 2, P.RAIL_L / 2, P.TB - 10, P.TB))
    if v["kind"] == "U":
        for _, _, x, y in P.pad_positions():
            b = b.cut(cyl(P.D_POCKET / 2, P.H_POCKET, x, y, P.TB - P.H_POCKET))
            b = b.cut(cyl(5, P.TB, x, y, 0))
    return b


def bracket(v, sx, sy):
    """Ménsula en (sx*X_CYL, sy*Y_BRK); mejillas paralelas a Y, respaldo hacia el borde de la base."""
    h = v["H_cheek"]
    x0, y0 = sx * P.X_CYL, sy * P.Y_BRK
    w = None
    for side in (-1, 1):
        xc = x0 + side * (P.CHEEK_GAP / 2 + P.CHEEK_T / 2)
        ch = cq.Workplane("XY").box(P.CHEEK_T, P.CHEEK_L, h, centered=(True, True, False)).translate((xc, y0, P.TB))
        w = ch if w is None else w.union(ch)
    yb = y0 + sy * (P.CHEEK_L / 2 + P.BACK_T / 2)
    back = cq.Workplane("XY").box(P.CHEEK_GAP + 2 * P.CHEEK_T, P.BACK_T, h, centered=(True, True, False)).translate((x0, yb, P.TB))
    w = w.union(back)
    hole = cq.Workplane("YZ").workplane(offset=x0 - 200).center(y0, v["z_axis"]).circle((P.D_PIN_CYL + 1) / 2).extrude(400)
    return w.cut(hole)


def rails(v):
    r = None
    for sx in (1, -1):
        k = box(sx * P.X_CYL - P.RAIL_W / 2, sx * P.X_CYL + P.RAIL_W / 2, -P.RAIL_L / 2, P.RAIL_L / 2, P.TB - 10, P.TB + P.RAIL_H)
        r = k if r is None else r.union(k)
    return r


def lug(v, sx, sy):
    x0 = sx * P.LUG_X
    y1 = sy * (P.B / 2 - P.LUG_L / 2)
    l = cq.Workplane("XY").box(P.LUG_T, P.LUG_L, P.LUG_H, centered=(True, True, False)).translate((x0, y1, P.TB))
    l = l.edges("|X and >Z").fillet(60)
    hole = cq.Workplane("YZ").workplane(offset=x0 - 50).center(y1, P.TB + 100).circle(P.LUG_HOLE / 2).extrude(100)
    return l.cut(hole)


def disc_parts(v):
    """Disco cajón: dict de sub-piezas (4a..4f)."""
    zb, zt = v["z_disc_bot"], v["z_disc_top"]
    R = P.D_DISC / 2
    def plate(z0, t):
        p = cyl(R, t, z=z0).cut(cyl(P.HUB_D / 2, t, z=z0))
        for _, x, y in P.idx_positions():
            p = p.cut(cyl(P.D_IDX_HOLE / 2, t, x, y, z0))
        return p
    bot = plate(zb, P.TP_BOT)
    top = plate(zt - P.TP_TOP, P.TP_TOP)
    for a in P.M30_ANG:
        x, y = P.R_M30 * math.cos(math.radians(a)), P.R_M30 * math.sin(math.radians(a))
        top = top.cut(cyl(13.25, P.TP_TOP, x, y, zt - P.TP_TOP))
    hub = cyl(P.HUB_D / 2, P.TD, z=zb)
    hub = hub.cut(cyl(P.D_BUJE_EXT / 2, P.L_BUJE, z=zb))
    hub = hub.cut(cyl(80, P.TD, z=zb))
    hub = hub.cut(cyl(P.D_CB / 2, P.H_CB, z=zt - P.H_CB))
    z0, h = zb + P.TP_BOT, P.GAP
    rings = None
    for r in P.RING_R:
        k = cyl(r + P.RING_T / 2, h, z=z0).cut(cyl(r - P.RING_T / 2, h, z=z0))
        rings = k if rings is None else rings.union(k)
    ribs = None
    for k in range(P.N_RIB):
        a = 360.0 / P.N_RIB * k
        rb = box(P.HUB_D / 2 - 2, P.RIB_R1, -P.RIB_T / 2, P.RIB_T / 2, z0, z0 + h).rotate((0, 0, 0), (0, 0, 1), a)
        ribs = rb if ribs is None else ribs.union(rb)
    bars = None
    for _, x, y in P.idx_positions():
        k = cyl(P.D_BAR / 2, P.TD, x, y, zb)
        bars = k if bars is None else bars.union(k)
    return {"4a": top, "4b": bot, "4c": hub, "4d": rings, "4e": ribs, "4f": bars}


def disc(v):
    d = disc_parts(v)
    s = d["4a"]
    for k in ("4b", "4c", "4d", "4e", "4f"):
        s = s.union(d[k])
    return s


def pivot(v):
    p = cyl(P.D_PIV / 2, v["L_piv"])
    p = p.faces("<Z").chamfer(5)
    for k in range(P.N_BOLT):
        a = math.radians(30 + 60 * k)
        p = p.cut(cyl(8.6, 40, P.BOLT_PCD / 2 * math.cos(a), P.BOLT_PCD / 2 * math.sin(a), v["L_piv"] - 40))
    return p


def bushing(v):
    return cyl(P.D_BUJE_EXT / 2, P.L_BUJE, z=v["z_disc_bot"]).cut(cyl(P.D_PIV / 2, P.L_BUJE, z=v["z_disc_bot"]))


def cap(v):
    c = cyl(P.D_TAPA / 2, P.T_TAPA, z=v["z_piv_top"])
    for k in range(P.N_BOLT):
        a = math.radians(30 + 60 * k)
        x, y = P.BOLT_PCD / 2 * math.cos(a), P.BOLT_PCD / 2 * math.sin(a)
        c = c.cut(cyl(11, P.T_TAPA, x, y, v["z_piv_top"])).cut(cyl(16.5, 13, x, y, v["z_piv_top"] + P.T_TAPA - 13))
    return c


def bolts(v):
    s = None
    for k in range(P.N_BOLT):
        a = math.radians(30 + 60 * k)
        x, y = P.BOLT_PCD / 2 * math.cos(a), P.BOLT_PCD / 2 * math.sin(a)
        b = cyl(10, 45, x, y, v["z_piv_top"] + P.T_TAPA - 13 - 32).union(cyl(15, 20, x, y, v["z_piv_top"] + P.T_TAPA - 13))
        s = b if s is None else s.union(b)
    return s


def seal(v):
    r = P.D_DISC / 2
    z0 = P.TB
    h = v["z_disc_bot"] + P.TP_BOT - z0
    rub = cyl(r + P.SEAL_T, h, z=z0).cut(cyl(r, h, z=z0))
    zb = v["z_disc_bot"] + P.TP_BOT / 2 - P.BAR_W / 2
    bar = cyl(r + P.SEAL_T + P.BAR_T, P.BAR_W, z=zb).cut(cyl(r + P.SEAL_T, P.BAR_W, z=zb))
    return rub, bar


def pads():
    s = None
    for _, _, x, y in P.pad_positions():
        c = cyl(P.D_PAD / 2, P.T_PAD, x, y, P.TB - P.H_POCKET)
        s = c if s is None else s.union(c)
    return s


def inox(v, rin, rout):
    z = v["z_disc_bot"] - P.INOX_T
    return cyl(rout / 2, P.INOX_T, z=z).cut(cyl(rin / 2, P.INOX_T, z=z))


def push_geom(v):
    """Lado derecho (x>0), empuje +Y, trinquete tomando la barra a -5°. Devuelve coordenadas clave."""
    a = math.radians(-P.BAR_ANG0)
    xb, yb = P.R_BAR * math.cos(a), P.R_BAR * math.sin(a)
    return xb, yb, yb - P.EYE_OFF


def push_set(v, sx):
    xb, yb, ye = push_geom(v)
    za = v["z_axis"]
    x0, x1 = P.SHOE_X0, P.SHOE_X1
    xc = P.X_CYL
    yf, yr = yb + P.SHOE_FRONT, yb + P.SHOE_FRONT - P.SHOE_L
    shoe = box(x0, x1, yr, yf, P.TB, v["shoe_top"])
    shoe = shoe.cut(box(xc - 20.5, xc + 20.5, yr, yf, P.TB, P.TB + P.RAIL_H + 1))
    shoe = shoe.cut(box(x0, x1, yb - P.PAWL_W - 0.5, yb + 0.5, za - P.PAWL_H / 2 - 0.5, za + P.PAWL_H / 2 + 0.5))
    shoe = shoe.cut(box(xc - 40, xc + 40, yr, yr + 110, za - 65, v["shoe_top"]))
    shoe = shoe.cut(cq.Workplane("YZ").workplane(offset=x0 - 5).center(ye, za).circle((P.D_PIN_CYL + 1) / 2).extrude(x1 - x0 + 10))
    pawl = box(P.PAWL_TIP, P.PAWL_TIP + P.PAWL_L, yb - P.PAWL_W, yb, za - P.PAWL_H / 2, za + P.PAWL_H / 2)
    pawl = pawl.cut(cyl(P.SEAT_R, P.PAWL_H, xb, yb, za - P.PAWL_H / 2))
    wedge = (cq.Workplane("XY").workplane(offset=za - P.PAWL_H / 2)
             .polyline([(P.PAWL_TIP - 1, yb - P.PAWL_W - 1), (P.PAWL_TIP + 60, yb - P.PAWL_W - 1), (P.PAWL_TIP - 1, yb - P.PAWL_W + 35)]).close().extrude(P.PAWL_H))
    pawl = pawl.cut(wedge)
    ybp = -P.Y_BRK
    def ycyl(r, y0, y1):
        lo, hi = min(y0, y1), max(y0, y1)
        return cq.Workplane("XZ").workplane(offset=-hi).center(xc, za).circle(r).extrude(hi - lo)
    body = ycyl(P.D_CYL / 2, ybp + 70, ybp + 70 + 300)
    rod = ycyl(P.D_ROD / 2, ybp + 370, ye - 50)
    eyes = None
    for y_ in (ybp, ye):
        e = cq.Workplane("YZ").workplane(offset=xc - P.EYE_W / 2).center(y_, za).circle(P.EYE_D / 2).extrude(P.EYE_W)
        eyes = e if eyes is None else eyes.union(e)
    cylinder = body.union(rod).union(eyes)
    pins = None
    for y_, ln in ((ybp, P.CHEEK_GAP + 2 * P.CHEEK_T + 40), (ye, x1 - x0 + 40)):
        pp = cq.Workplane("YZ").workplane(offset=xc - ln / 2).center(y_, za).circle(P.D_PIN_CYL / 2).extrude(ln)
        pins = pp if pins is None else pins.union(pp)
    cylinder = cylinder.cut(pins)
    out = [shoe, pawl, cylinder, pins]
    if sx < 0:
        out = [o.rotate((0, 0, 0), (0, 0, 1), 180) for o in out]
    return out


def build(kind):
    v = P.variant(kind)
    parts = []  # (pos, name, shape, color)
    b = base_plate(v)
    parts.append((1, "Placa base", b, C["base"]))
    brk = None
    for sx in (1, -1):
        for sy in (1, -1):
            k = bracket(v, sx, sy)
            brk = k if brk is None else brk.union(k)
    parts.append((2, "Mensulas de reaccion", brk, C["base"]))
    lg = None
    for sx in (1, -1):
        for sy in (1, -1):
            k = lug(v, sx, sy)
            lg = k if lg is None else lg.union(k)
    parts.append((3, "Orejas de izaje", lg, C["base"]))
    parts.append((4, "Disco giratorio", disc(v), C["disc"]))
    parts.append((5, "Pivote", pivot(v), C["pin"]))
    parts.append((6, "Buje bronce", bushing(v), C["bronze"]))
    parts.append((7, "Tapa retenedora", cap(v), C["steel"]))
    parts.append((8, "Pernos M20", bolts(v), C["pin"]))
    sh, pw, cy_, pn = [], [], [], []
    for sx in (1, -1):
        a_, b_, c_, d_ = push_set(v, sx)
        sh.append(a_); pw.append(b_); cy_.append(c_); pn.append(d_)
    parts.append((9, "Cilindros 50 t", cy_[0].union(cy_[1]), C["cyl"]))
    parts.append((10, "Carros de empuje", sh[0].union(sh[1]), C["steel"]))
    parts.append((11, "Trinquetes", pw[0].union(pw[1]), C["pin"]))
    parts.append((12, "Pasadores D70", pn[0].union(pn[1]), C["pin"]))
    parts.append((22, "Guias de carro", rails(v), C["base"]))
    rub, bar = seal(v)
    parts.append((14, "Faldon NBR", rub, C["nbr"]))
    parts.append((15, "Fleje de apriete", bar, C["steel"]))
    if kind == "U":
        parts.append((19, "Pastillas UHMW", pads(), C["uhmw"]))
        parts.append((20, "Pista inox A", inox(v, *P.INOX_A), C["inox"]))
        parts.append((21, "Pista inox B", inox(v, *P.INOX_B), C["inox"]))
    return v, parts


if __name__ == "__main__":
    import sys, time, json
    for kind in sys.argv[1:] or ["U", "S"]:
        t = time.time()
        v, parts = build(kind)
        assy = cq.Assembly(name=v["code"])
        mass = {}
        for pos, name, shp, col in parts:
            assy.add(shp, name=f"P{pos:02d}_{name.replace(' ', '_')}", color=col)
            vol = shp.val().Volume()
            dens = {6: 7.6e-6, 19: 0.94e-6 if kind == "U" else 0, 14: 1.2e-6}.get(pos, 7.85e-6)
            mass[pos] = round(vol * dens, 1)
        out = f"/home/claude/tt300/out/{v['code']}"
        assy.save(out + ".step")
        assy.save(out + ".glb")
        json.dump(mass, open(out + "_mass.json", "w"))
        print(kind, round(time.time() - t, 1), "s", mass, "total", round(sum(mass.values()), 0))
```

### tt300/iso.py
`tt300/iso.py` — 19 líneas

```python
import sys, cadquery as cq, model3d as M
from cadquery.occ_impl.exporters.svg import getSVG
def iso_svg(kind, path, explode=0.0, dirn=(1.0,-1.6,1.1), w=900, h=650, hidden=False, only=None):
    v, parts = M.build(kind)
    shapes=[]
    for pos,name,shp,col in parts:
        if only and pos not in only: continue
        s = shp.val()
        if explode:
            dz = {1:0,2:0,3:0,19:0.4,20:1.4,21:1.4,4:1.6,6:1.6,14:1.6,15:1.6,5:0.0,7:3.2,8:3.6,9:2.6,10:2.6,11:3.0,12:2.6}.get(pos,0)
            s = s.translate(cq.Vector(0,0,dz*explode))
        shapes.append(s)
    comp = cq.Compound.makeCompound(shapes)
    svg = getSVG(comp, opts=dict(width=w, height=h, marginLeft=10, marginTop=10, projectionDir=dirn, showAxes=False, showHidden=hidden, strokeWidth=-1.0, strokeColor=(0,0,0), hiddenColor=(120,120,120)))
    open(path,'w').write(svg)
if __name__=='__main__':
    import time
    for k in ('U','S'):
        t=time.time(); iso_svg(k, f'out/iso_{k}.svg'); iso_svg(k, f'out/isoexp_{k}.svg', explode=250); print(k, time.time()-t)
```

### tt300/sheet1.py
`tt300/sheet1.py` — 226 líneas

```python
"""Lámina 1: Conjunto general (planta, cortes, detalles, lista de materiales, notas)."""
import math
import cadquery as cq
import params as P, model3d as M, hlr, draw
from common import Place, bom, notes_general, fmt_kg, total_mass, bbox

PUSH = (9, 10, 11, 12, 13, 22)


def nf(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def sheet1(kind):
    v, parts = M.build(kind)
    v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 1, 4, "CONJUNTO GENERAL – CORTES Y DETALLES", "INDICADA")
    shapes = [(p, s.val()) for p, n, s, c in parts]
    U = kind == "U"
    zt = v["z_disc_top"]

    # ================= PLANTA 1:10 =================
    allc = cq.Compound.makeCompound([s for _, s in shapes])
    vis, _ = hlr.hlr(allc, "top", tol=4)
    T = Place((160, 448), 0.1)
    T.polys(S, vis)
    S.centerlines(T((0, 0)), 108, 0)
    S.circle(T((0, 0)), P.R_IDX * 0.1, "EJE")
    S.circle(T((0, 0)), 80.0, "FANT")
    S.leader(T((-566, 566)), (T((0, 0))[0] - 62, T((0, 0))[1] + 124), "ZONA DE CARGA Ø1600 MÁX.", h=2.3)
    if U:
        for _, _, x, y in P.pad_positions():
            S.circle(T((x, y)), P.D_PAD / 2 * 0.1, "OCU")
    # dims
    S.dim(T((-1200, 1000)), T((1200, 1000)), 9, "2400")
    S.dim(T((-1200, -1000)), T((-1200, 1000)), -7, "2000", orient="v")
    S.dim(T((0, -1000)), T((P.X_CYL, -1000)), -7, nf(P.X_CYL))
    S.dim(T((-P.X_CYL, -1000)), T((0, -1000)), -7, nf(P.X_CYL))
    S.dim(T((1200, 0)), T((1200, -P.Y_BRK)), 6, nf(P.Y_BRK), orient="v")
    S.dim(T((1200, 0)), T((1200, P.Y_BRK)), 6, nf(P.Y_BRK), orient="v")
    S.dim(T((-600, 1000)), T((600, 1000)), 3.5, "1200")
    S.leader(T((P.R_IDX * math.cos(math.radians(125)), P.R_IDX * math.sin(math.radians(125)))),
             (T((0, 0))[0] + 40, T((0, 0))[1] + 124), "36 barras Ø70 s/ Ø1880 (10°) – ver det. E", h=2.3)
    if U:
        S.balloon(T((550 * math.cos(math.radians(-165)), 550 * math.sin(math.radians(-165)))), T((-1290, -400)), 19)
    # flecha de giro
    c = T((0, 0))
    S.arc(c, 52, 200, 245, "VIS")
    a = math.radians(245)
    S.arrow((c[0] + 52 * math.cos(a), c[1] + 52 * math.sin(a)), a + math.pi / 2, size=4, w=1.4)
    S.text("GIRO ANTIHORARIO", (c[0] - 40, c[1] - 30), 2.3, "MIDDLE_CENTER")
    # marcas de corte
    S.line(T((-1270, 0)), T((-1220, 0)), "VIS"); S.line(T((1220, 0)), T((1270, 0)), "VIS")
    S.section_mark(T((-1270, 0)), 90, "A"); S.section_mark(T((1270, 0)), 90, "A")
    S.line(T((P.X_CYL, 1030)), T((P.X_CYL, 1080)), "VIS"); S.line(T((P.X_CYL, -1030)), T((P.X_CYL, -1080)), "VIS")
    S.section_mark(T((P.X_CYL, 1080)), 180, "B"); S.section_mark(T((P.X_CYL, -1080)), 180, "B")
    S.detail_circle(T((1000, -150)), 15, "E")
    # globos
    bl = [(1, (-1100, -930), (-1290, -1060)), (2, (P.X_CYL + 60, 760), (1290, 1060)), (3, (-600, 950), (-760, 1150)),
          (4, (-420, 300), (-1290, 300)), (7, (60, 60), (330, 350)), (9, (P.X_CYL, -560), (1290, -560)),
          (10, (-P.X_CYL, 200), (-1290, 160)), (12, (-P.X_CYL, P.Y_BRK), (-1290, 760)),
          (22, (-P.X_CYL, -300), (-1290, -200)), (17, (424, 424), (560, 560)), (15, (-707, -707), (-1290, -760))]
    for n, p, q in bl:
        S.balloon(T(p), T(q), n)
    S.view_title((T((0, 0))[0], 322), "PLANTA", "ESCALA 1:10")

    # ================= CORTE A-A 1:10 =================
    vis, hid, hat = hlr.section(shapes, "front", (0, 0, 0), (0, 1, 0), tol=4)
    A = Place((160, 252), 0.1)
    A.polys(S, vis); A.hatches(S, hat)
    S.line(A((0, -15)), A((0, zt + 160)), "EJE")
    S.dim(A((1000, 0)), A((1000, P.TB)), 6, "80", orient="v")
    S.dim(A((1000, P.TB)), A((1000, zt)), 6, nf(zt - P.TB), orient="v")
    S.dim(A((-1200, 0)), A((-1200, zt)), -6, nf(zt), orient="v")
    S.dim(A((-1200, 0)), A((-1200, v["z_axis"])), -14, nf(v["z_axis"]), orient="v")
    S.detail_circle(A((0, 100)), 18, "C")
    S.detail_circle(A((800, 120)), 18, "D")
    S.view_title((A((0, 0))[0], 232), "CORTE A-A", "ESCALA 1:10")

    # ================= CORTE B-B 1:5 =================
    vis, hid, hat = hlr.section(shapes, "right", (P.X_CYL, 0, 0), (-1, 0, 0), tol=2)
    win = (-1010, -5, 160, v["shoe_top"] + 40)
    visc = hlr.clip_polys(vis, win); hatc = hlr.clip_hatch(hat, win)
    Bp = Place((48, 110), 0.2, (-1010, 0))
    Bp.polys(S, visc); Bp.hatches(S, hatc)
    x = Bp((160, 0))[0]
    S.pline([(x, Bp((0, -5))[1]), (x, Bp((0, 120))[1]), (x + 3, Bp((0, 140))[1]), (x - 3, Bp((0, 160))[1]), (x, Bp((0, 180))[1]), (x, Bp((0, v["shoe_top"] + 40))[1])], "FINA")
    za = v["z_axis"]
    yb = -P.Y_BRK
    xbar, yi, ye = M.push_geom(v)
    S.line(Bp((-1010, za)), Bp((160, za)), "EJE")
    S.dim(Bp((yb, za)), Bp((ye, za)), 24, f"{ye - yb:.0f} (L0 {P.L0_CYL:.0f} + 36 libre)")
    S.dim(Bp((ye, za)), Bp((yi, za)), 24, nf(P.EYE_OFF))
    S.dim(Bp((yb, 0)), Bp((0, 0)), -10, nf(P.Y_BRK))
    S.dim(Bp((yi, 0)), Bp((0, 0)), -10, nf(-yi, 1))
    S.dim(Bp((160, 0)), Bp((160, za)), 6, nf(za), orient="v")
    S.dim(Bp((-1000, 0)), Bp((-1000, P.TB)), -5, "80", orient="v")
    S.dim(Bp((-1000, P.TB)), Bp((-1000, P.TB + v["H_cheek"])), -5, nf(v["H_cheek"]), orient="v")
    S.leader(Bp((40, za + 10)), (Bp((175, 0))[0], Bp((0, za + 55))[1]), "EMPUJE → (carrera 200 = 10°)", h=2.3)
    for n, p, q in [(2, (-940, 120), (-960, 330)), (9, (-600, za + 60), (-600, za + 170)), (12, (yb, za), (-800, za + 170)),
                    (10, (-250, v["shoe_top"] - 20), (-330, za + 170)), (11, (yi - 40, za + 30), (-120, za + 170)),
                    (22, (-300, P.TB + 15), (-350, -40)), (4, (60, zt - 15), (110, za + 170)), (1, (-800, 40), (-800, -40)),
                    (14, (-150, P.TB + 10), (-150, -40))]:
        S.balloon(Bp(p), Bp(q), n)
    S.view_title((Bp((-430, 0))[0], 82), f"CORTE B-B (eje cilindro y carro, x = +{P.X_CYL:.0f})", "ESCALA 1:5")

    # ================= DETALLES 1:2 =================
    nopush = [(p, s) for p, s in shapes if p not in PUSH + (2, 3)]
    vis, hid, hat = hlr.section(nopush, "front", (0, 0, 0), (0, 1, 0), tol=1)
    # --- C: pivote
    winC = (-240, -5, 240, zt + 12)
    C = Place((445, 438), 0.5)
    C.polys(S, hlr.clip_polys(vis, winC)); C.hatches(S, hlr.clip_hatch(hat, winC))
    S.line(C((0, -15)), C((0, zt + 25)), "EJE")
    S.dim(C((-75, -5)), C((75, -5)), -6, "Ø150 H7/p6")
    S.dim(C((-95, v["z_disc_bot"])), C((95, v["z_disc_bot"])), -14 - (5 * 0.5 + v["z_disc_bot"] * 0.5) + 10 - 10 if False else -10 - v["z_disc_bot"] * 0.5 - 2.5 - 6 , "Ø190 H7/s6")
    S.dim(C((-130, zt)), C((130, zt)), 8, "Ø260")
    S.dim(C((-120, v["z_piv_top"] + P.T_TAPA)), C((120, v["z_piv_top"] + P.T_TAPA)), 3, "Ø240", txt_shift=0)
    S.dim(C((240, v["z_disc_bot"])), C((240, v["z_buje_top"])), 5, nf(P.L_BUJE), orient="v")
    S.dim(C((240, v["z_cb_floor"])), C((240, zt)), 5, "25", orient="v")
    S.dim(C((240, 0)), C((240, P.TB)), 5, "80", orient="v")
    S.dim(C((-240, v["z_piv_top"])), C((-240, v["z_piv_top"] + P.T_TAPA)), -5, "20", orient="v")
    S.dim(C((-240, v["z_cb_floor"])), C((-240, v["z_piv_top"])), -14, "3", orient="v", outside=True)
    S.leader(C((50, v["z_piv_top"] + 10)), (C((0, 0))[0] + 40, C((0, zt + 30))[1]), "6× M20 s/ PCD 100", h=2.3)
    for n, p, q in [(5, (-40, 40), (-275, 30)), (6, (-85, v["z_disc_bot"] + 40), (-275, 100)),
                    (7, (-110, v["z_piv_top"] + 10), (-215, zt + 22)), (8, (-50, v["z_piv_top"] + 5), (-145, zt + 22)),
                    (4, (180, zt - 30), (275, zt - 15)), (1, (180, 40), (275, 30))]:
        S.balloon(C(p), C(q), n)
    S.leader(C((-60, 2)), (C((0, 0))[0] - 70, C((0, -50))[1]), "Sold. sello chaflán 5×45°, esmerilar", h=2.2)
    if U:
        S.leader(C((160, P.TB + 4)), (C((0, 0))[0] + 70, C((0, -50))[1]), "Holgura g = 8 (5 pastilla + 3 inox)", h=2.2)
    else:
        S.leader(C((160, P.TB)), (C((0, 0))[0] + 70, C((0, -50))[1]), "Contacto pleno + grasa grafitada", h=2.2)
    S.view_title((C((0, 0))[0], 384), "DETALLE C – PIVOTE", "ESCALA 1:2")

    # --- D: borde
    winD = (585, -5, 1018, zt + 12)
    Dp = Place((325, 222), 0.5, (585, 0))
    Dp.polys(S, hlr.clip_polys(vis, winD)); Dp.hatches(S, hlr.clip_hatch(hat, winD))
    zb_ = v["z_disc_bot"]
    S.dim(Dp((1000, zt)), Dp((1000, zt - P.TP_TOP)), 18, "30", orient="v")
    S.dim(Dp((1000, zt - P.TP_TOP)), Dp((1000, zb_ + P.TP_BOT)), 18, "100", orient="v")
    S.dim(Dp((1000, zb_ + P.TP_BOT)), Dp((1000, zb_)), 18, "30", orient="v")
    S.dim(Dp((1000, zt)), Dp((1000, zb_)), 28, "160", orient="v")
    S.dim(Dp((1000, P.TB)), Dp((1000, 0)), 18, "80", orient="v")
    S.text("Nervio radial 4e (cortado)", Dp((700, zb_ + P.TP_BOT + 50)), 2.2, "MIDDLE_LEFT")
    S.dim(Dp((585, zt)), Dp((1000, zt)), 6, "R1000 (a eje)")
    if U:
        S.dim(Dp((650, P.TB + 5)), Dp((820, P.TB + 5)), 22, "Ø170")
        S.dim(Dp((585, P.TB - 5)), Dp((585, P.TB)), -5, "5", orient="v", outside=True)
        S.dim(Dp((630, P.TB)), Dp((630, P.TB + 5)), -5, "5", orient="v", outside=True)
        S.dim(Dp((840, v["z_disc_bot"] - 3)), Dp((840, v["z_disc_bot"])), 3, "3", orient="v", outside=True)
        S.dim(Dp((0, P.TB)), Dp((735, P.TB)), 0, "", orient="h") if False else None
        for n, p, q in [(19, (700, P.TB), (690, -40)), (21, (760, v["z_disc_bot"] - 1.5), (790, -40)),
                        (14, (1003, P.TB + 5), (1060, -30)), (15, (1009, zb_ + 15), (1070, zb_ + 60)),
                        (4, (900, zt - 15), (900, zt + 35)), (1, (900, 30), (950, -40))]:
            S.balloon(Dp(p), Dp(q), n)
        S.text("R735 (eje anillo 3)", Dp((620, -30)), 2.2, "MIDDLE_LEFT")
        S.text("Pista inox B R440–R840", Dp((830, -32)), 2.2, "MIDDLE_LEFT")
    else:
        for n, p, q in [(14, (1003, P.TB + 5), (1060, -30)), (15, (1009, zb_ + 15), (1070, zb_ + 60)),
                        (4, (900, zt - 15), (900, zt + 35)), (1, (900, 30), (950, -40))]:
            S.balloon(Dp(p), Dp(q), n)
        S.leader(Dp((700, P.TB)), (Dp((640, 0))[0], Dp((0, -30))[1]), "", lines=["Pos 19: grasa grafitada 0,3–0,5 mm/cara", "Ranuras en 4b: det. L, lám. F-03"], h=2.2)
    S.view_title((Dp((800, 0))[0], 186), "DETALLE D – BORDE E INTERFAZ DE GIRO", "ESCALA 1:2")

    # --- E: trinquete (corte horizontal en eje del cilindro)
    vis, hid, hat = hlr.section(shapes, "top", (0, 0, za), (0, 0, -1), tol=1, nocut={5, 8})
    winE = (850, -440, 1210, 125)
    E = Place((612, 97), 0.4, (850, -440))
    E.polys(S, hlr.clip_polys(vis, winE)); E.hatches(S, hlr.clip_hatch(hat, winE))
    for k in (-2, -1, 0, 1):
        a_ = math.radians(-P.BAR_ANG0 + 10 * k)
        S.cross(E((P.R_BAR * math.cos(a_), P.R_BAR * math.sin(a_))), 2.5)
    S.line(E((P.X_CYL, -440)), E((P.X_CYL, 125)), "EJE")
    S.dim(E((xbar - 35, yi)), E((xbar + 35, yi)), 0.01 - 52, "Ø70") if False else None
    S.leader(E((xbar + 20, yi + 25)), E((1150, 60)), "Barra Ø70", h=2.1)
    S.dim(E((P.PAWL_TIP, yi)), E((P.PAWL_TIP, yi - P.PAWL_W)), -6, "85", orient="v")
    S.dim(E((P.PAWL_TIP, yi - P.PAWL_W)), E((P.SHOE_X0, yi - P.PAWL_W)), -10, nf(P.SHOE_X0 - P.PAWL_TIP))
    S.dim(E((P.SHOE_X0, yi + P.SHOE_FRONT)), E((P.SHOE_X1, yi + P.SHOE_FRONT)), 22, "130")
    S.dim(E((P.SHOE_X1, yi + P.SHOE_FRONT)), E((P.SHOE_X1, yi + P.SHOE_FRONT - P.SHOE_L)), 6, "300", orient="v")
    S.leader(E((xbar + 30, yi - 22)), E((1225, 40)), "Asiento R36", h=2.1)
    S.leader(E((P.PAWL_TIP + 15, yi - P.PAWL_W + 10)), E((960, -300)), "Chaflán 30°", h=2.1)
    p0 = E((P.SHOE_X1 + 25, -40)); S.line(p0, (p0[0], p0[1] + 30), "VIS"); S.arrow((p0[0], p0[1] + 30), math.pi / 2, size=3.5, w=1.2)
    S.text("EMPUJE", (p0[0] + 2, p0[1] + 12), 2.2, "MIDDLE_LEFT")
    for n, p, q in [(10, (1110, -200), (1300, -200)), (11, (1000, yi - 40), (1300, yi - 40)), (12, (P.X_CYL, ye), (1300, ye)),
                    (4, (880, -20), (880, 60))]:
        S.balloon(E(p), E(q), n)
    S.view_title((E((1030, 0))[0], 84), "DETALLE E – TRINQUETE Y BARRA (corte horiz. en eje)", "ESCALA 1:2,5")

    # ================= BOM =================
    rows = []
    for pos, desc, q, mat, mu in bom(v):
        rows.append([pos, desc, q, mat, fmt_kg(mu) if mu else "—"])
    y = S.table(598, 584, [("POS", 10, "C"), ("DESCRIPCIÓN", 88, "L"), ("CANT.", 13, "C"), ("MATERIAL / NORMA", macro_w := 81, "L"), ("kg/u", 21, "R")], rows, rh=5.4, h=2.15)
    S.text(f"MASA TOTAL APROX. DEL CONJUNTO: {fmt_kg(total_mass(v))} kg (sin carga, incl. cilindros)", (600, y - 4), 2.4, "TOP_LEFT", bold=True)
    S.text("LISTA DE MATERIALES", (598 + 106, 588.5), 3.2, "BOTTOM_CENTER", bold=True) if False else None

    # ================= NOTAS =================
    S.mtext(notes_general(v), (598, y - 12), h=2.1, ls=1.62, bold_first=True)

    # datos técnicos
    U_ = U
    import calc as K
    dd = K.case(0.20, 0.80)
    dt = [["Capacidad nominal (WLL)", "300 tf (2 942 kN)"],
          ["Altura total (sup. disco)", f"{zt:.0f} mm"],
          ["Interfaz de giro", "UHMW-PE / inox 316L" if U_ else "Acero/acero + grasa grafitada"],
          ["Presión media interfaz (φd)", "1,05 MPa (contacto pleno)"],
          ["Presión máx. e = 150 mm", "1,67 MPa"],
          ["Fuerza de diseño por cilindro", f"{dd['Fc']:.0f} kN a {dd['p']:.0f} bar (μ = 0,20)"],
          ["Capacidad cilindro (700 bar)", f"2 × 445 kN (FS {dd['FS']:.2f})".replace(".", ",")],
          ["Rotación por ciclo", "10° (36 libre + 164 de empuje)"]]
    S.table(25, 62, [("DATOS TÉCNICOS", 62, "L"), ("", 58, "L")], dt, rh=5.0, h=2.15, header_h=5.5)
    return S, v


if __name__ == "__main__":
    import sys
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet1(k)
        S.save(f"out/{v['code']}-01.dxf", f"out/{v['code']}-01.pdf")
        import pymupdf
        d = pymupdf.open(f"out/{v['code']}-01.pdf"); d[0].get_pixmap(dpi=75).save(f"out/{v['code']}-01.png")
        print("ok", k)
```

### tt300/sheet2.py
`tt300/sheet2.py` — 127 líneas

```python
"""Lámina 2: isométricas (conjunto y explosionada), montaje y operación."""
import math
import cadquery as cq
import params as P, model3d as M, hlr, draw
from common import Place, bbox, pressure_bar

EXP = {17: 2.1, 19: 0.4, 20: 2.1, 21: 2.1, 4: 2.1, 6: 2.1, 14: 2.1, 15: 2.1, 16: 2.1, 7: 3.6, 8: 4.1, 9: 3.1, 10: 3.1, 11: 3.1, 12: 3.1}


def anchors(v):
    zt, zdb, za = v["z_disc_top"], v["z_disc_bot"], v["z_axis"]
    X = P.X_CYL
    a = {1: (300, -1000, 40), 2: (X + 80, -P.Y_BRK, P.TB + v["H_cheek"] - 20), 3: (620, -925, P.TB + 60),
         4: (-200, -700, zt), 5: (0, -75, 60), 6: (0, -95, zdb + 40), 7: (0, -120, v["z_piv_top"] + 20),
         8: (50, 0, v["z_piv_top"] + 30), 9: (X, -600, za + 60), 10: (P.SHOE_X1, -250, za),
         11: (1000, -120, za + 45), 12: (X + 100, -P.Y_BRK, za), 14: (711, -711, P.TB + 15),
         15: (-300, -965.4, zdb + 15), 17: (424, -424, zt), 22: (X, 250, P.TB + 30)}
    if v["kind"] == "U":
        a.update({19: (520, -520, P.TB + 5), 20: (-560, -560, zdb), 21: (690, -690, zdb)})
    return a


def sheet2(kind):
    v, parts = M.build(kind)
    v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 2, 4, "ISOMÉTRICAS – MONTAJE Y OPERACIÓN", "1:10")
    U = kind == "U"
    shapes = [(p, s.val()) for p, n, s, c in parts]
    view = "iso"
    # ------ conjunto
    comp = cq.Compound.makeCompound([s for _, s in shapes])
    vis, _ = hlr.hlr(comp, view, tol=5)
    x0, y0, x1, y1 = bbox(vis)
    s = 1 / 10
    T = Place((178, 462), s, ((x0 + x1) / 2, (y0 + y1) / 2))
    T.polys(S, vis)
    S.view_title((178, 352), "VISTA ISOMÉTRICA – CONJUNTO", "ESCALA 1:10")
    # ------ explosionada
    ex = 420.0
    sh2 = []
    for p, sh in shapes:
        sh2.append((p, sh.translate(cq.Vector(0, 0, EXP.get(p, 0) * ex))))
    comp2 = cq.Compound.makeCompound([sh for _, sh in sh2])
    vis2, _ = hlr.hlr(comp2, view, tol=5)
    x0, y0, x1, y1 = bbox(vis2)
    E = Place((488, 335), s, ((x0 + x1) / 2, (y0 + y1) / 2))
    E.polys(S, vis2)
    cx = 488
    # globos en dos columnas
    an = anchors(v)
    pts = []
    for pos, p3 in an.items():
        p3 = (p3[0], p3[1], p3[2] + EXP.get(pos, 0) * ex)
        pts.append((pos, E(hlr.proj_pt(p3, view))))
    left = sorted([q for q in pts if q[1][0] < cx], key=lambda t: -t[1][1])
    right = sorted([q for q in pts if q[1][0] >= cx], key=lambda t: -t[1][1])
    for col, xb in ((left, 338), (right, 640)):
        n = len(col)
        ytop = 545
        for i, (pos, pp) in enumerate(col):
            yb = min(pp[1], ytop - i * 0) if False else None
        ys = []
        for i, (pos, pp) in enumerate(col):
            y = pp[1]
            if ys and y > ys[-1] - 11:
                y = ys[-1] - 11
            ys.append(y)
        for (pos, pp), y in zip(col, ys):
            S.balloon(pp, (xb, y), pos)
    S.view_title((488, 92), "VISTA ISOMÉTRICA EXPLOSIONADA", "ESCALA 1:10 – globos según lista de materiales lámina 1")
    # ------ textos
    pbar = pressure_bar(0.10 if U else 0.12, v)
    mont = ["SECUENCIA DE MONTAJE",
            "1. Placa base pos 1 (con pos 2 y 3 soldadas, relevada y mecanizada) sobre apoyo nivelado (≤ 0,5 %).",
            "2. Pivote pos 5 calado en caliente en pos 1 (H7/p6; calentar pos 1 local a ≤ 200 °C o enfriar pos 5),",
            "   soldadura de sello inferior y esmerilado a ras.",
            ("3. Limpiar alojamientos; colocar 34 pastillas pos 19 (ajuste deslizante, sin adhesivo)." if U else
             "3. Limpiar caras de contacto de pos 1 y 4b; aplicar grasa grafitada pos 19 (0,3–0,5 mm) y llenar ranuras."),
            ("4. Buje pos 6 prensado en el cubo 4c (H7/s6). Pistas pos 20/21 soldadas y pulidas previamente en pos 4." if U else
             "4. Buje pos 6 prensado en el cubo 4c (H7/s6). Verificar planitud ≤ 0,20 mm de ambas caras antes de lubricar."),
            "5. Izar pos 4 con 4 cáncamos pos 18 (M30) y bajar centrado sobre pos 5 sin golpear la interfaz.",
            "6. Tapa pos 7 con 6 pernos pos 8 (M20 10.9, par según tabla, arandela Nord-Lock). Juego vertical 3 mm.",
            "7. Faldón pos 14 y fleje pos 15 con 36 pernos pos 16. Retirar cáncamos y colocar tapones pos 17.",
            "8. Carros pos 10 sobre guías pos 22 con trinquete pos 11 y resorte pos 13 (trinquete hacia el sentido de giro);",
            "   cilindros pos 9 entre ménsula activa y carro con pasadores pos 12 + clips. Mangueras 700 bar (CR400).",
            "9. Prueba en vacío: 2 ciclos completos; luego ensayo de carga según nota 10, lámina 1."]
    oper = ["SECUENCIA DE OPERACIÓN (POR CICLO)",
            "a) Extender ambos cilindros a la vez (colector común): 36 mm libres, el trinquete toma la barra y la carga",
            "   gira 10° hasta fin de carrera (200 mm).",
            "b) Retraer a fondo: el chaflán del trinquete pasa sobre la barra siguiente y el resorte lo engancha.",
            "   Verificar visualmente el enganche de ambos trinquetes antes del ciclo siguiente.",
            f"c) Registrar presión de giro. Esperada ≈ {pbar:,.0f} bar. Detener si supera 600 bar.".replace(",", "."),
            "d) Para invertir el sentido: retirar cilindros y carros, girar cada carro 180° y usar la ménsula opuesta.",
            "e) No operar con viento > 50 km/h ni con la carga sin arriostrar. Personal fuera del radio de giro.",
            "",
            "MANTENIMIENTO",
            ("• Cada uso: limpiar pistas inox pos 20/21 con paño y alcohol; no usar abrasivos." if U else
             "• Antes de cada operación: 4 graseras pos 20, ≈ 60 g c/u. Si p > 600 bar: detener, levantar, limpiar y relubricar."),
            ("• Reemplazar pastillas con resalte < 3,0 mm o con fisuras. Retirar con varilla por agujero Ø10." if U else
             "• Usar solo grasa grafitada especificada. Mantener faldón pos 14 en buen estado (evita ingreso de arena)."),
            "• Guardar bajo techo, con el disco calzado y el faldón protegido del sol."]
    y = S.mtext(mont, (26, 330), h=2.3, ls=1.6, bold_first=True)
    S.mtext(oper, (26, y - 7), h=2.3, ls=1.6, bold_first=True)
    fits = [["Pivote 5 / placa base 1", "Ø150 H7/p6", "Calado en caliente"],
            ["Pivote 5 / buje 6", "Ø150 H7/f7", "Giratorio"],
            ["Buje 6 / disco 4", "Ø190 H7/s6", "Prensado"],
            ["Trinquete 11 / alojamiento carro 10", "85×90 H9/f8", "Deslizante"],
            ["Carro 10 / guía 22", "Ranura 41 H11 / 40 h9", "Guiado"],
            ["Barra 4f / agujeros planchas 4a, 4b", "Ø70 / Ø71", "Soldada"],
            ["Pasadores 12 / ménsula, carro", "Ø70 H9/f8 (rótula GE70)", "Deslizante"],
            ["Pernos 8 M20 10.9 (VDI 2230, μ 0,12)", "540 N·m", "Nord-Lock"],
            ["Pernos 16 M8 A2-70", "18 N·m", "Antigripante"],
            ["Tapones 17 M30", "Manual + fijador media", "Ras con disco"]]
    if U:
        fits.insert(5, ["Pastilla 19 / alojamiento", "Ø170 -0,1/-0,2 – Ø170,6 +0,1/0", "Holgura térmica"])
    S.table(26, 140, [("AJUSTES Y PARES DE APRIETE", 80, "L"), ("VALOR", 58, "L"), ("OBS.", 32, "L")], fits, rh=5.0, h=2.1)
    return S, v


if __name__ == "__main__":
    import sys, pymupdf
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet2(k)
        S.save(f"out/{v['code']}-02.dxf", f"out/{v['code']}-02.pdf")
        pymupdf.open(f"out/{v['code']}-02.pdf")[0].get_pixmap(dpi=75).save(f"out/{v['code']}-02.png")
        print("ok", k)
```

### tt300/sheet3.py
`tt300/sheet3.py` — 272 líneas

```python
"""Lámina 3: fabricación placa base (conj. soldado 1+2+3) y disco (4) [+ pistas inox 20/21]."""
import math
import params as P, draw
from common import Place, fmt_kg

def nf(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def sheet3(kind):
    v = P.variant(kind); v["proj"] = P.PROJ
    U = kind == "U"
    S = draw.Sheet()
    S.frame(v, 3, 4, "FABRICACIÓN – PLACA BASE (1+2+3) Y DISCO (4)", "INDICADA")
    hc = v["H_cheek"]; zax = v["z_axis"] - P.TB

    # =================== PLACA BASE – PLANTA 1:10 ===================
    T = Place((158, 440), 0.1)
    c = T((0, 0))
    S.rect(*T((-1200, -1000)), *T((1200, 1000)))
    for sx_ in (1, -1):
        S.rect(*T((sx_ * P.X_CYL - 20, -P.RAIL_L / 2)), *T((sx_ * P.X_CYL + 20, P.RAIL_L / 2)))
        S.line(T((sx_ * P.X_CYL, -P.RAIL_L / 2 - 30)), T((sx_ * P.X_CYL, P.RAIL_L / 2 + 30)), "EJE")
    S.circle(c, 7.5); S.centerlines(c, 106, 0)
    S.circle(c, 100, "FANT")
    S.text("contorno disco Ø2000", T((-640, 840)), 2.0, "BOTTOM_LEFT")
    if U:
        for r, n, a0 in P.RINGS:
            S.circle(c, r * 0.1, "EJE")
        for _, _, x, y in P.pad_positions():
            S.circle(T((x, y)), P.D_POCKET / 2 * 0.1)
            S.circle(T((x, y)), 0.5)
    for sx in (1, -1):
        for sy in (1, -1):
            x0, y0 = sx * P.X_CYL, sy * P.Y_BRK
            for side in (-1, 1):
                xa = x0 + side * P.CHEEK_GAP / 2
                xb = x0 + side * (P.CHEEK_GAP / 2 + P.CHEEK_T)
                S.rect(*T((min(xa, xb), y0 - P.CHEEK_L / 2)), *T((max(xa, xb), y0 + P.CHEEK_L / 2)))
            yb0 = y0 + sy * P.CHEEK_L / 2
            yb1 = yb0 + sy * P.BACK_T
            S.rect(*T((x0 - 80, min(yb0, yb1))), *T((x0 + 80, max(yb0, yb1))))
            S.line(T((x0 - 100, y0)), T((x0 + 100, y0)), "EJE")
            # orejas
            S.rect(*T((sx * P.LUG_X - 20, sy * 850)), *T((sx * P.LUG_X + 20, sy * 1000)))
    S.dim(T((-1200, 1000)), T((1200, 1000)), 9, "2400")
    S.dim(T((-1200, -1000)), T((-1200, 1000)), -7, "2000", orient="v")
    S.dim(T((0, -1000)), T((P.X_CYL, -1000)), -6, nf(P.X_CYL)); S.dim(T((-P.X_CYL, -1000)), T((0, -1000)), -6, nf(P.X_CYL))
    S.dim(T((1200, 0)), T((1200, -P.Y_BRK)), 6, nf(P.Y_BRK), orient="v"); S.dim(T((1200, 0)), T((1200, P.Y_BRK)), 6, nf(P.Y_BRK), orient="v")
    S.dim(T((-1105, -P.RAIL_L / 2)), T((-1105, P.RAIL_L / 2)), -5, "850", orient="v")
    S.dim(T((-600, 1000)), T((600, 1000)), 3.5, "1200")
    S.dim(T((600, 850)), T((600, 1000)), -4, "150", orient="v", outside=True)
    S.leader(T((75 * 0.7071, 75 * 0.7071)), (c[0] + 20, c[1] + 40), "Ø150 H7 pasante", h=2.3)
    if U:
        S.leader(T((P.RINGS[2][0], 0)), (c[0] + 40, c[1] - 112), "34× alojam. Ø170,6 +0,1/0 prof. 5 (ver tabla y det. F)", h=2.2)
    S.balloon(T((-500, -500)), T((-1300, -650)), 1)
    S.balloon(T((P.X_CYL + 60, 760)), T((1300, 1080)), 2)
    S.balloon(T((600, 950)), T((450, 1100)), 3)
    S.balloon(T((-P.X_CYL, 200)), T((-1300, 300)), 22)
    S.leader(T((P.X_CYL, 300)), (T((0, 0))[0] + 60, T((0, 0))[1] + 75), "Guía 40×40 embutida 10 (ranura 40 H8), filete 8 – det. M F-03", h=2.1)
    S.view_title((c[0], 316), "POS 1 – PLACA BASE (CONJ. SOLDADO 1+2+3) – PLANTA", "ESCALA 1:10")

    # ----- ELEVACIÓN FRONTAL 1:10
    F = Place((158, 262), 0.1)
    S.rect(*F((-1200, 0)), *F((1200, P.TB)))
    for sx in (1, -1):
        for side in (-1, 1):
            xa = sx * P.X_CYL + side * P.CHEEK_GAP / 2
            xb = sx * P.X_CYL + side * (P.CHEEK_GAP / 2 + P.CHEEK_T)
            S.rect(*F((min(xa, xb), P.TB)), *F((max(xa, xb), P.TB + hc)))
        S.circle(F((sx * P.X_CYL, v["z_axis"])), 3.55, "OCU")
        S.rect(*F((sx * P.LUG_X - 20, P.TB)), *F((sx * P.LUG_X + 20, P.TB + P.LUG_H)))
        S.rect(*F((sx * P.X_CYL - 20, P.TB - 10)), *F((sx * P.X_CYL + 20, P.TB + P.RAIL_H)), "OCU")
    S.line(F((0, -10)), F((0, P.TB + 40)), "EJE")
    S.dim(F((1200, 0)), F((1200, P.TB)), 6, "80", orient="v")
    S.dim(F((-1200, P.TB)), F((-1200, P.TB + hc)), -14, nf(hc), orient="v")
    S.dim(F((-1200, P.TB)), F((-1200, v["z_axis"])), -6, nf(zax), orient="v")
    S.dim(F((-660, P.TB)), F((-660, P.TB + P.LUG_H)), -3, "170", orient="v")
    S.weld(F((P.X_CYL - 60, P.TB)), (F((P.X_CYL, 0))[0] + 14, F((0, -60))[1]), "cjp", "CJP", other=True, note="MEJILLAS pos 2")
    S.weld(F((-P.LUG_X - 20, P.TB)), (F((-P.LUG_X, 0))[0] - 10, F((0, -60))[1]), "fillet", "12", other=True, all_round=True, note="pos 3")
    S.view_title((158, 222), "ELEVACIÓN FRONTAL", "ESCALA 1:10")

    # ----- DETALLE F 1:1 alojamiento (U) / DETALLE F superficie (S)
    if U:
        Fp = Place((62, 140), 1.0, (0, 0))
        x0, x1 = -15, 112
        for out in ([(5, -40), (x1, -40), (x1, 0), (85.3, 0), (85.3, -5), (5, -5)], [(x0, -40), (-5, -40), (-5, -5), (x0, -5)]):
            pts = [Fp(p) for p in out]
            S.pline(pts, "VIS", closed=True)
            S.hatch_poly(pts, scale=0.8)
        pp = [Fp(p) for p in [(x0, -5), (85, -5), (85, 5), (x0, 5)]]
        S.pline(pp, "VIS", closed=True); S.hatch_poly(pp, pattern="ANSI37", scale=0.7)
        S.line(Fp((0, -48)), Fp((0, 14)), "EJE")
        S.pline([Fp((x1, -40)), Fp((x1 + 4, -20)), Fp((x1 - 3, -14)), Fp((x1, 0))], "FINA")
        S.pline([Fp((x0, -40)), Fp((x0 - 3, -25)), Fp((x0 + 3, -12)), Fp((x0, 5))], "FINA")
        S.dim(Fp((0, -40)), Fp((85.3, -40)), -8, "Ø170,6 +0,1/0")
        S.dim(Fp((0, 5)), Fp((85, 5)), 8, "Ø170 -0,1/-0,2")
        S.dim(Fp((112, -5)), Fp((112, 0)), 6, "5 ±0,05", orient="v", outside=True)
        S.dim(Fp((112, 0)), Fp((112, 5)), 18, "5", orient="v", outside=True)
        S.dim(Fp((-15, -5)), Fp((-15, 5)), -5, "10 ±0,1", orient="v", outside=True)
        S.leader(Fp((5, -25)), (Fp((0, 0))[0] + 30, Fp((0, -30))[1]), "Ø10 pasante (extracción)", h=2.2)
        S.finish(Fp((40, -5)), "Ra 3,2")
        S.leader(Fp((85, 4)), (Fp((0, 0))[0] + 95, Fp((0, 24))[1]), "Chaflán 0,5×45°", h=2.2)
        S.text("pos 19", Fp((30, 0.5)), 2.0, "BOTTOM_LEFT")
        S.text("pos 1", Fp((60, -25)), 2.0, "BOTTOM_LEFT")
        S.view_title((Fp((50, 0))[0], 82), "DETALLE F – ALOJAMIENTO DE PASTILLA", "ESCALA 1:1")
        # tabla anillos
        S.table(200, 168, [("ANILLO", 15, "C"), ("R (mm)", 16, "C"), ("N°", 10, "C"), ("ÁNG. INICIAL", 22, "C"), ("PASO", 14, "C")],
                [["1", "300", "6", "30°", "60°"], ["2", "550", "12", "15°", "30°"], ["3", "735", "16", "0°", "22,5°"]], rh=5.2, h=2.2)
        S.text("Ángulos desde eje +X, sentido antihorario (vista en planta).", (200, 141), 2.0, "TOP_LEFT")
        S.text("Tolerancia posición alojamientos: ±0,5 mm.", (200, 137), 2.0, "TOP_LEFT")
    else:
        lines = ["DETALLE F – SUPERFICIE DE CONTACTO (sin escala)",
                 "• Cara superior pos 1 dentro de Ø2000 y cara inferior pos 4: fresado/planeado",
                 "  final después del alivio de tensiones.",
                 "• Planitud ≤ 0,20 mm en Ø2000; rugosidad Ra 1,6–3,2 µm; sin rayas radiales.",
                 "• Bordes de la zona de contacto: chaflán 2×45°; agujero Ø150: chaflán 3×45°.",
                 "• Cara 4b: ranuras de lubricación y conductos de graseras según det. L (lám. F-03).",
                 "• Lubricante pos 19: grasa grafitada NLGI 2, 0,3–0,5 mm en ambas caras,",
                 "  aplicada con espátula sobre superficie limpia y seca; llenar ranuras de 4b.",
                 "• Almacenaje: caras protegidas con la misma grasa y cubiertas con film.",
                 "• NO pintar con el sistema anticorrosivo las caras de contacto."]
        S.mtext(lines, (26, 205), h=2.3, ls=1.55, bold_first=True)
        S.finish((150, 105), "Ra 1,6–3,2 (ambas caras)")

    # =================== DISCO CAJÓN – PLANTA 1:10 ===================
    import model3d as M, hlr
    D = Place((450, 440), 0.1)
    c = D((0, 0))
    S.circle(c, 100); S.centerlines(c, 106, 0)
    S.circle(c, P.R_BAR * 0.1, "EJE"); S.circle(c, P.R_M30 * 0.1, "EJE")
    for _, x, y in P.idx_positions():
        S.circle(D((x, y)), P.D_BAR / 2 * 0.1)
    for a in P.M30_ANG:
        p = D((P.R_M30 * math.cos(math.radians(a)), P.R_M30 * math.sin(math.radians(a))))
        S.circle(p, 1.5); S.arc(p, 1.25, 0, 270, "FINA")
    S.circle(c, P.HUB_D / 2 * 0.1); S.circle(c, P.D_CB / 2 * 0.1)
    for r in P.RING_R:
        S.circle(c, (r - P.RING_T / 2) * 0.1, "OCU"); S.circle(c, (r + P.RING_T / 2) * 0.1, "OCU")
        n = max(4, int(2 * math.pi * r / 250))
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            ca, sa = math.cos(a), math.sin(a)
            S.line(D(((r - 11) * ca, (r - 11) * sa)), D(((r + 11) * ca, (r + 11) * sa)), "FINA")
    for k in range(P.N_RIB):
        a = math.radians(360 / P.N_RIB * k); ca, sa = math.cos(a), math.sin(a)
        for off in (-P.RIB_T / 2, P.RIB_T / 2):
            S.line(D((150 * ca - off * sa, 150 * sa + off * ca)), D((P.RIB_R1 * ca - off * sa, P.RIB_R1 * sa + off * ca)), "OCU")
    S.circle(c, 80, "FANT")
    S.dim_dia(c, 100, 140, "Ø2000")
    S.leader(D((P.R_BAR * math.cos(math.radians(45)), P.R_BAR * math.sin(math.radians(45)))), (c[0] + 60, c[1] + 112), "36 barras 4f Ø70 s/ Ø1880, inicio 5°, paso 10°", h=2.2)
    S.leader(D((P.R_M30 * math.cos(math.radians(135)), P.R_M30 * math.sin(math.radians(135)))), (c[0] - 60, c[1] + 112), "4× M30 pasante en 4a s/ Ø1200 a 45°", h=2.2)
    S.leader(D((550 * math.cos(math.radians(20)), 550 * math.sin(math.radians(20)))), (c[0] + 60, c[1] - 112), "Almas 4d R300/R550/R735 e=25 y nervios 4e e=20 (ocultos)", h=2.2)
    S.leader(D((-150 * 0.7071, -150 * 0.7071)), (c[0] - 60, c[1] - 112), "Cubo 4c Ø300 (det. H)", h=2.2)
    S.text("Ranuras de soldadura en 4a sobre almas (trazo fino)", D((-560, -400)), 2.0, "BOTTOM_LEFT")
    S.text("0°", D((1040, 15)), 2.3, "BOTTOM_LEFT")
    S.balloon(D((-300, 500)), D((-1150, 650)), 4)
    S.view_title((c[0], 316), "POS 4 – DISCO CAJÓN (CONJ. SOLDADO 4a–4f) – PLANTA", "ESCALA 1:10")

    # ----- CORTE DISCO 1:10 (plano por barras a 0°/180°)
    dp = M.disc_parts(v)
    lab = {"4a": 41, "4b": 42, "4c": 43, "4d": 44, "4e": 45, "4f": 46}
    parts = [(lab[k], sh.rotate((0, 0, 0), (0, 0, 1), -5).val()) for k, sh in dp.items()]
    vis, hid, hat = hlr.section(parts, "front", (0, 0, 0), (0, 1, 0), tol=1.5, nocut=set())
    hat = [(4, o, h) for _, o, h in hat]
    zb = v["z_disc_bot"]
    C = Place((450, 262), 0.1, (0, zb))
    C.polys(S, vis); C.hatches(S, hat)
    S.line(C((0, zb - 10)), C((0, zb + P.TD + 10)), "EJE")
    S.dim(C((1000, zb)), C((1000, zb + P.TD)), 6, "160", orient="v")
    S.detail_circle(C((0, zb + 80)), 16, "H"); S.detail_circle(C((-940, zb + 80)), 12, "J")
    S.view_title((450, 222), "CORTE DIAMETRAL DISCO (por barras a 0° y 180°)", "ESCALA 1:10")

    # ----- DETALLE H 1:2 (cubo)
    winH = (-230, zb - 5, 230, zb + P.TD + 5)
    H = Place((385, 112), 0.5, (0, zb))
    H.polys(S, hlr.clip_polys(vis, winH)); H.hatches(S, hlr.clip_hatch(hat, winH))
    S.line(H((0, zb - 10)), H((0, zb + P.TD + 10)), "EJE")
    zt_ = zb + P.TD
    S.dim(H((-95, zb)), H((95, zb)), -6, "Ø190 H7")
    S.dim(H((-80, zb + P.L_BUJE)), H((80, zb + P.L_BUJE)), 3, "Ø160")
    S.dim(H((-130, zt_)), H((130, zt_)), 6, "Ø260 H11")
    S.dim(H((-150, zt_)), H((150, zt_)), 14, "Ø300 (cubo 4c)")
    S.dim(H((230, zb)), H((230, zb + P.L_BUJE)), 6, "100 +0,1/0", orient="v")
    S.dim(H((230, zt_ - P.H_CB)), H((230, zt_)), 6, "25", orient="v")
    S.dim(H((-230, zb)), H((-230, zb + P.TP_BOT)), -6, "30", orient="v")
    S.dim(H((-230, zt_ - P.TP_TOP)), H((-230, zt_)), -6, "30", orient="v")
    S.dim(H((-230, zb)), H((-230, zt_)), -16, "160", orient="v")
    S.weld(H((150, zt_)), H((175, zt_ + 40)), "bevel", "CJP", note="4c-4a/4b")
    S.finish(H((-60, zb + 40)), "Ra 1,6")
    S.view_title((385, 66), "DETALLE H – CUBO CENTRAL", "ESCALA 1:2")

    # ----- DETALLE J 1:2 (barra de empuje)
    winJ = (850, zb - 5, 1012, zb + P.TD + 5)
    J = Place((572, 112), 0.5, (931, zb))
    J.polys(S, hlr.clip_polys(vis, winJ)); J.hatches(S, hlr.clip_hatch(hat, winJ))
    S.line(J((940, zb - 10)), J((940, zb + P.TD + 10)), "EJE")
    S.dim(J((905, zt_)), J((975, zt_)), 6, "Ø70")
    S.dim(J((940, zb)), J((1000, zb)), -8, "60")
    S.dim(J((1000, zb + P.TP_BOT)), J((1000, zt_ - P.TP_TOP)), 6, "100 libre", orient="v")
    S.weld(J((975, zt_)), J((1015, zt_ + 40)), "bevel", "15", note="a ras")
    S.weld(J((975, zb)), J((1015, zb - 40)), "bevel", "15", note="mec.")
    S.text("Agujero Ø71 en 4a y 4b, chaflán 10×45°", J((860, zb - 20)), 2.1, "TOP_LEFT")
    S.view_title((585, 66), "DETALLE J – BARRA DE EMPUJE 4f", "ESCALA 1:2")

    # =================== PISTAS INOX (U) / TOLERANCIAS ===================
    x0 = 600
    if U:
        R = Place((660, 535), 0.025)
        for k, (din, dout) in enumerate((P.INOX_A, P.INOX_B)):
            cc = (650 + k * 75, 535)
            S.circle(cc, dout / 2 * 0.03); S.circle(cc, din / 2 * 0.03); S.centerlines(cc, dout / 2 * 0.03, 2)
            S.dim_dia(cc, dout / 2 * 0.03, 50, f"Ø{dout:.0f}", ext=5)
            S.dim_dia(cc, din / 2 * 0.03, -60, f"Ø{din:.0f}", ext=6)
            S.text(f"POS {20 + k} – e = 3", (cc[0], cc[1] - dout / 2 * 0.03 - 7), 2.6, "TOP_CENTER", bold=True)
        S.text("ESCALA 1:33 (aprox.)", (700, 495), 2.2, "TOP_CENTER")
        lines = ["PISTAS INOX POS 20 / 21",
                 "• AISI 316L (1.4404), e = 3 mm, cada anillo de una sola pieza (sin juntas).",
                 "• Acabado espejo: Ra ≤ 0,1 µm, Ry5i ≤ 1 µm (EN 1337-2), dureza 150–220 HV.",
                 "• Mecanizar cara inferior 4b en zonas de pistas (planitud ≤ 0,20) antes de soldar.",
                 "• Fijar con filete continuo 3 mm ER309L en bordes interior y exterior, soldadura",
                 "  por tramos alternos de 150 mm para limitar distorsión. Contacto pleno (sin bolsas).",
                 "• Verificar planitud conjunto pista ≤ 0,30 mm en Ø1680. Proteger con film adhesivo",
                 "  hasta el montaje. No pintar ni golpear."]
        y = S.mtext(lines, (x0, 482), h=2.25, ls=1.55, bold_first=True)
    else:
        y = 560
    tol = ["TOLERANCIAS GEOMÉTRICAS Y MECANIZADO",
           "• Cara sup. pos 1 (zona Ø2000): planitud 0,20; Ra 3,2" + (" (fondo alojamientos)." if U else " / 1,6–3,2 contacto."),
           "• Cara inf. 4b: planitud 0,20; paralelismo con cara sup. 4a: 0,30 (mecanizar ambas tras relevar).",
           "• Ø150 H7 (pos 1) y Ø190 H7 (pos 4): perpendicularidad 0,05 respecto de la cara de giro.",
           "• Barras 4f: posición ±0,5 (PCD 1880, paso 10° ±0,05°); verticalidad 0,3 en 160.",
           "• Ménsulas pos 2: agujero Ø71 H9 mecanizado en línea después de soldar y relevar;",
           "  coaxialidad entre mejillas 0,10; altura del eje ±0,5.",
           "• Tolerancias generales ISO 2768-mK. Aristas vivas: chaflán 1×45°.",
           "",
           "SECUENCIA DE FABRICACIÓN POS 1",
           "1. Corte térmico con 5 mm de sobremetal por cara; UT de plancha (A578 nivel B).",
           "2. Soldar pos 2 (CJP mejillas + filetes respaldo) y pos 3 (filete 12 todo alrededor);",
           "   precalentar ≥ 110 °C, control de interpase ≤ 250 °C.",
           "3. Alivio de tensiones 590–620 °C (1 h/25 mm, mín. 2 h), enfriamiento en horno.",
           "4. Mecanizado final: cara superior, Ø150 H7" + (", 34 alojamientos" if U else "") + ", agujeros Ø71 H9.",
           "5. Ensayos: UT CJP 100 %, MT filetes 100 %, control dimensional con protocolo.",
           "",
           "SECUENCIA DE FABRICACIÓN POS 4 (DISCO CAJÓN)",
           "1. 4b sobre mesa plana; soldar cubo 4c (CJP), almas 4d y nervios 4e (filete 8 a ambos lados).",
           "2. Insertar 36 barras 4f en 4b; presentar 4a con ranuras 22×80 c/250 sobre almas y nervios.",
           "3. Soldar ranuras (relleno completo), cubo 4c–4a (CJP) y barras 4f a 4a/4b (bisel 15, E = 12, ver det. J).",
           "4. Drenaje/venteo: 2× Ø20 en 4b por celda; tapar con tapón roscado tras pintura interior.",
           "5. Alivio de tensiones 590–620 °C; mecanizar cara 4b (contacto), cara 4a, cubo (det. H).",
           "6. " + ("Soldar pistas 20/21 en 4b y pulir." if U else "Ranuras y conductos de lubricación en 4b (det. L, lám. F-03)."),
           "   Control: barras ±0,5; planitud 4b ≤ 0,20; UT CJP 100 %, MT 100 %."]
    yy = S.mtext(tol, (x0, y - 8), h=2.2, ls=1.5, bold_first=True)
    dp = M.disc_parts(v)
    mk = {k: dp[k].val().Volume() * 7.85e-6 for k in dp}
    rows = [["4a", "Plancha sup. Ø2000×30; Ø300, 36×Ø71, 4×M30", "1", fmt_kg(mk["4a"])],
            ["4b", "Plancha inf. Ø2000×30; Ø300, 36×Ø71", "1", fmt_kg(mk["4b"])],
            ["4c", "Cubo Ø300/Ø190×160 (S355J2+N, forja)", "1", fmt_kg(mk["4c"])],
            ["4d", "Almas 25×100 roladas, eje Ø600/1100/1470", "3", fmt_kg(mk["4d"])],
            ["4e", "Nervios 20×100, L 137,5/225/160/132,5 (×12)", "48", fmt_kg(20*100*655*12*7.85e-6)],
            ["4f", "Barras Ø70×160 (S355J2 laminado)", "36", fmt_kg(mk["4f"])]]
    S.table(x0, yy - 4, [("SUB", 10, "C"), ("DESPIECE POS 4", 88, "L"), ("CANT.", 12, "C"), ("kg total", 18, "R")], rows, rh=4.8, h=2.05)
    return S, v


if __name__ == "__main__":
    import sys, pymupdf
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet3(k)
        S.save(f"out/{v['code']}-03.dxf", f"out/{v['code']}-03.pdf")
        pymupdf.open(f"out/{v['code']}-03.pdf")[0].get_pixmap(dpi=75).save(f"out/{v['code']}-03.png")
        print("ok", k)
```

### tt300/sheet4.py
`tt300/sheet4.py` — 320 líneas

```python
"""Lámina 4: piezas mecánicas y soldadas."""
import math
import params as P, draw
from common import Place, masses, fmt_kg


def nf(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def hrect(S, pts, scale=0.6, angle=0, pattern="ANSI31"):
    S.pline(pts, "VIS", closed=True)
    S.hatch_poly(pts, scale=scale, angle=angle, pattern=pattern)


def tag(S, p, pos, name, mat, qty, mass):
    S.text(f"POS {pos} – {name}", p, 3.4, "BOTTOM_CENTER", bold=True)
    w = len(f"POS {pos} – {name}") * 3.4 * 0.6
    S.line((p[0] - w / 2, p[1] - 1.2), (p[0] + w / 2, p[1] - 1.2), "VIS")
    S.text(f"{mat} – Cant. {qty} – {mass} kg/u", (p[0], p[1] - 2.6), 2.3, "TOP_CENTER")


def sheet4(kind):
    v = P.variant(kind); v["proj"] = P.PROJ
    U = kind == "U"
    m = masses(v)
    S = draw.Sheet()
    S.frame(v, 4, 4, "PIEZAS MECÁNICAS Y SOLDADAS", "INDICADA")
    L = v["L_piv"]

    # ---------------- POS 5 PIVOTE 1:2 ----------------
    O = Place((75, 442), 0.5)
    r = 75
    prof = [(-r + 5, 0), (r - 5, 0), (r, 5), (r, L), (-r, L), (-r, 5)]
    S.pline([O(p) for p in prof], "VIS", closed=True)
    S.line(O((-r, P.TB)), O((r, P.TB)), "FINA")
    S.line(O((0, -8)), O((0, L + 8)), "EJE")
    for x in (-50, 50):
        S.line(O((x - 8.6, L)), O((x - 8.6, L - 40)), "OCU"); S.line(O((x + 8.6, L)), O((x + 8.6, L - 40)), "OCU")
        S.line(O((x - 10, L)), O((x - 10, L - 32)), "OCU"); S.line(O((x + 10, L)), O((x + 10, L - 32)), "OCU")
        S.line(O((x - 8.6, L - 40)), O((x + 8.6, L - 40)), "OCU")
    S.dim(O((-r, 0)), O((r, 0)), -8, "Ø150 p6 (+0,068/+0,043)")
    S.dim(O((-r, L)), O((r, L)), 6, "Ø150 f7 (-0,043/-0,083)")
    S.dim(O((r, 0)), O((r, P.TB)), 6, "80", orient="v")
    S.dim(O((r, 0)), O((r, L)), 18, nf(L), orient="v")
    S.leader(O((-r + 2.5, 2.5)), (O((0, 0))[0] - 30, O((0, -48))[1]), "5×45°", h=2.3)
    S.leader(O((50, L - 20)), (O((0, 0))[0] + 50, O((0, L + 25))[1]), "6× M20 prof. 32 (Ø17,5 prof. 40) s/ PCD 100", h=2.2)
    S.finish(O((-r, P.TB + 40)), "Ra 0,8")
    S.text("Zona p6", O((-r + 8, 40)), 2.1, "MIDDLE_LEFT")
    S.text("Zona f7", O((-r + 8, P.TB + 40)), 2.1, "MIDDLE_LEFT")
    tag(S, (75, 412), 5, "PIVOTE", "42CrMo4+QT, 280–330 HB", 1, fmt_kg(m[5]))

    # ---------------- POS 6 BUJE 1:2 ----------------
    O = Place((190, 488), 0.5)
    for s in (-1, 1):
        pts = [O((s * 75, 0)), O((s * 95, 0)), O((s * 95, P.L_BUJE)), O((s * 75, P.L_BUJE))]
        hrect(S, pts, pattern="ANSI33", scale=0.5)
        for z in (15, 37.5, 60):
            S.circle(O((s * 85, z)), 2.5, "FINA")
    S.line(O((0, -8)), O((0, P.L_BUJE + 8)), "EJE")
    S.dim(O((-95, 0)), O((95, 0)), -8, "Ø190 s6 (+0,151/+0,122)")
    S.dim(O((-75, P.L_BUJE)), O((75, P.L_BUJE)), 6, "Ø150 H7 (+0,040/0)")
    S.dim(O((95, 0)), O((95, P.L_BUJE)), 6, nf(P.L_BUJE), orient="v")
    S.text("Insertos de grafito sólido Ø10,", O((-95, -38)), 2.2, "TOP_LEFT")
    S.text("≈ 25 % superficie de deslizamiento", O((-95, -44)), 2.2, "TOP_LEFT")
    S.text("Chaflán interior 2×30° ambos extremos", O((-95, -50)), 2.2, "TOP_LEFT")
    tag(S, (190, 412), 6, "BUJE", "CuAl10Ni5Fe4 + grafito", 1, fmt_kg(m[6]))

    # ---------------- POS 7 TAPA 1:2 ----------------
    O = Place((305, 512), 0.5)
    c = O((0, 0))
    S.circle(c, 60); S.centerlines(c, 60, 4)
    S.circle(c, 25, "EJE")
    for k in range(6):
        a = math.radians(30 + 60 * k)
        p = O((50 * math.cos(a), 50 * math.sin(a)))
        S.circle(p, 5.5); S.circle(p, 8.25)
    S.dim_dia(c, 60, 35, "Ø240")
    S.leader(O((50 * math.cos(math.radians(150)), 50 * math.sin(math.radians(150)))), (c[0] - 30, c[1] + 66), "6× Ø22 / avell. Ø33×13 s/ PCD 100", h=2.2)
    Os = Place((305, 440), 0.5)
    pts = [Os(p) for p in [(-120, 0), (120, 0), (120, 20), (-120, 20)]]
    S.pline(pts, "VIS", closed=True)
    for x in (-50, 50):
        S.line(Os((x - 11, 0)), Os((x - 11, 7)), "OCU"); S.line(Os((x + 11, 0)), Os((x + 11, 7)), "OCU")
        S.line(Os((x - 16.5, 7)), Os((x - 16.5, 20)), "OCU"); S.line(Os((x + 16.5, 7)), Os((x + 16.5, 20)), "OCU")
    S.dim(Os((120, 0)), Os((120, 20)), 6, "20", orient="v")
    tag(S, (305, 428), 7, "TAPA RETENEDORA", "S355J2", 1, fmt_kg(m[7]))

    # ---------------- POS 11 TRINQUETE 1:2,5 ----------------
    sc = 0.4
    O = Place((375, 505), sc)
    xs = 936.4 - P.PAWL_TIP
    dz = math.sqrt(P.SEAT_R ** 2 - xs ** 2)
    a0 = math.degrees(math.atan2(-dz, -xs))
    arc = [(xs + P.SEAT_R * math.cos(math.radians(t)), 85 + P.SEAT_R * math.sin(math.radians(t))) for t in [a0 + (0 - a0) * i / 20 for i in range(21)]]
    outline = [(0, 35)] + arc + [(245, 85), (245, 0), (60, 0)]
    pts = [O(p) for p in outline]
    S.pline(pts, "VIS", closed=True)
    S.rect(*O((205, 16.5)), *O((245, 68.5)), "OCU")
    S.line(O((-10, 42.5)), O((255, 42.5)), "EJE")
    S.dim(O((0, 85)), O((245, 85)), 14, "245")
    S.dim(O((245, 0)), O((245, 85)), 6, "85 f8", orient="v")
    S.dim(O((0, 85)), O((xs, 85)), 6, nf(xs, 1))
    S.dim_rad(O((xs, 85)), P.SEAT_R * sc, -60, "R36", ext=6)
    S.dim(O((0, 0)), O((60, 0)), -6, "60")
    S.dim(O((0, 0)), O((0, 35)), -6, "35", orient="v")
    S.text("Asiento de barra Ø70", O((80, 95)), 2.0, "BOTTOM_LEFT")
    S.text("Alojamiento resorte Ø52 prof. 40", O((120, -22)), 2.0, "TOP_LEFT")
    O2 = Place((375, 445), sc)
    S.rect(*O2((0, 0)), *O2((245, 90)))
    S.line(O2((xs - P.SEAT_R + 4.6, 0)), O2((xs - P.SEAT_R + 4.6, 90)), "OCU")
    S.line(O2((xs + P.SEAT_R, 0)), O2((xs + P.SEAT_R, 90)), "OCU")
    S.line(O2((205, 19)), O2((245, 19)), "OCU"); S.line(O2((205, 71)), O2((245, 71)), "OCU"); S.line(O2((205, 19)), O2((205, 71)), "OCU")
    S.dim(O2((245, 0)), O2((245, 90)), 6, "90 f8", orient="v")
    S.leader(O2((245, 45)), (O2((245, 0))[0] + 14, O2((0, 110))[1]), "Manilla M12 (desenganche)", h=2.0)
    tag(S, (420, 428), 11, "TRINQUETE", "34CrNiMo6+QT, 300–350 HB, MT 100 %", 2, fmt_kg(m[11] / 2))

    # ---------------- POS 10 CARRO DE EMPUJE 1:2,5 ----------------
    Hs = v["shoe_top"] - P.TB
    zc = v["z_axis"] - P.TB
    L, Wd = P.SHOE_L, P.SHOE_X1 - P.SHOE_X0
    pf, pb = P.SHOE_FRONT - 0.5, P.SHOE_FRONT + P.PAWL_W + 0.5
    eye = P.SHOE_FRONT + P.EYE_OFF
    # planta: largo horizontal (0 = frente), ancho vertical (0 = cara interior, lado disco)
    O = Place((520, 492), sc)
    S.rect(*O((0, 0)), *O((L, Wd)))
    S.rect(*O((pf, 0)), *O((pb, Wd)), "OCU")
    S.rect(*O((190, (Wd - 80) / 2)), *O((L, (Wd + 80) / 2)))
    S.line(O((eye, -8)), O((eye, Wd + 8)), "EJE")
    S.line(O((-8, Wd / 2)), O((L + 8, Wd / 2)), "EJE")
    S.dim(O((0, Wd)), O((L, Wd)), 6, "300")
    S.dim(O((0, Wd)), O((pf, Wd)), 14, nf(pf, 1))
    S.dim(O((pf, Wd)), O((pb, Wd)), 14, "86 H9")
    S.dim(O((0, Wd)), O((eye, Wd)), 22, nf(eye))
    S.dim(O((L, 0)), O((L, Wd)), 6, "130", orient="v")
    S.dim(O((L, (Wd - 80) / 2)), O((L, (Wd + 80) / 2)), 16, "80 H11", orient="v")
    S.text("lado disco", O((5, -6)), 2.0, "TOP_LEFT")
    S.text("frente (empuje →)", O((5, -14)), 2.0, "TOP_LEFT") if False else None
    # elevación lateral
    O2 = Place((520, 418), sc)
    S.rect(*O2((0, 0)), *O2((L, Hs)))
    S.rect(*O2((pf, zc - 45.5)), *O2((pb, zc + 45.5)))
    S.rect(*O2((0, 0)), *O2((L, 31)), "OCU")
    S.rect(*O2((190, zc - 65)), *O2((L, Hs)), "OCU")
    S.circle(O2((eye, zc)), 35.5 * sc); S.centerlines(O2((eye, zc)), 35.5 * sc, 3)
    S.line(O2((-8, zc)), O2((L + 8, zc)), "EJE")
    S.dim(O2((L, 0)), O2((L, Hs)), 6, nf(Hs), orient="v")
    S.dim(O2((0, 0)), O2((0, zc)), -6, nf(zc), orient="v")
    S.dim(O2((0, zc - 45.5)), O2((0, zc + 45.5)), -16, "91 H9", orient="v")
    S.leader(O2((eye + 12, zc + 12)), (O2((eye, 0))[0] + 12, O2((0, Hs + 22))[1]), "Ø71 H9 (pasador pos 12)", h=2.0)
    S.text("Ranura guía 41 H11 × 31 (inferior)", O2((5, -6)), 2.0, "TOP_LEFT")
    S.text("Ranura lubricada con grasa grafitada pos 19", O2((5, -12)), 2.0, "TOP_LEFT")
    tag(S, (580, 396), 10, "CARRO DE EMPUJE", "S355J2+N", 2, fmt_kg(m[10] / 2))

    # ---------------- POS 12 PASADOR Ø70 1:2 ----------------
    O = Place((720, 540), 0.5)
    S.pline([O(p) for p in [(0, -35), (195, -35), (200, -30), (200, 30), (195, 35), (0, 35)]], "VIS", closed=True)
    S.rect(*O((-15, -45)), *O((0, 45)))
    S.line(O((-22, 0)), O((210, 0)), "EJE")
    S.circle(O((188, 0)), 4.5); S.line(O((188, -40)), O((188, 40)), "EJE")
    S.dim(O((0, 35)), O((200, 35)), 6, "200")
    S.dim(O((-15, 45)), O((0, 45)), 6, "15", outside=True)
    S.dim(O((200, -35)), O((200, 35)), 6, "Ø70 f8", orient="v")
    S.dim(O((-15, -45)), O((-15, 45)), -5, "Ø90", orient="v")
    S.dim(O((0, -35)), O((188, -35)), -8, "188")
    S.leader(O((188, 0)), (O((0, 0))[0] + 60, O((0, 75))[1]), "Ø9 pasante (clip R pos 13)", h=2.1)
    tag(S, (765, 495), 12, "PASADOR Ø70", "42CrMo4+QT, 280–330 HB", 4, fmt_kg(m[12] / 4))

    # ---------------- POS 2 MÉNSULA 1:5 ----------------
    hc = v["H_cheek"]; zh = v["z_axis"] - P.TB
    s5 = 0.2
    # planta
    O = Place((70, 320), s5)
    for sd in (-1, 1):
        xa, xb = sd * 40, sd * 80
        S.rect(*O((min(xa, xb), -140)), *O((max(xa, xb), 140)))
    S.rect(*O((-80, -180)), *O((80, -140)))
    S.line(O((-100, 0)), O((100, 0)), "EJE"); S.line(O((0, -200)), O((0, 165)), "EJE")
    S.dim(O((-80, 140)), O((80, 140)), 5, "160")
    S.dim(O((-40, 140)), O((40, 140)), 12, "80")
    S.dim(O((80, -140)), O((80, 140)), 5, "280", orient="v")
    S.dim(O((80, -180)), O((80, -140)), 5, "40", orient="v", outside=True)
    S.dim(O((-80, -180)), O((-80, 0)), -5, "180", orient="v")
    S.text("Respaldo hacia el exterior", O((-80, -205)), 2.1, "TOP_LEFT")
    S.text("(lado opuesto al disco)", O((-80, -230)), 2.1, "TOP_LEFT")
    # lateral (y-z)
    O2 = Place((165, 262), s5)
    S.rect(*O2((-140, 0)), *O2((140, hc)))
    S.rect(*O2((-180, 0)), *O2((-140, hc)))
    S.circle(O2((0, zh)), 35.5 * s5 * 5 * 0.2 / 0.2 * 0.2 / 0.2 if False else 7.1)
    S.centerlines(O2((0, zh)), 7.1, 3)
    S.dim(O2((140, 0)), O2((140, hc)), 6, nf(hc), orient="v")
    S.dim(O2((140, 0)), O2((140, zh)), 14, nf(zh), orient="v")
    S.dim(O2((-180, hc)), O2((140, hc)), 5, "320")
    S.leader(O2((25, zh + 25)), (O2((0, 0))[0] + 20, O2((0, hc + 40))[1]), "Ø71 H9 (mecanizar en línea)", h=2.2)
    S.weld(O2((-140, 0)), (O2((0, 0))[0] - 10, O2((0, -45))[1]), "cjp", "CJP", other=True, note="mejillas-base")
    S.weld(O2((-170, 0)), (O2((0, 0))[0] - 50, O2((0, -80))[1]), "fillet", "16", other=True, all_round=True, note="respaldo")
    S.text("Base pos 1", O2((60, -12)), 2.0, "TOP_LEFT")
    S.line(O2((-260, 0)), O2((240, 0)), "VIS")
    tag(S, (120, 212), 2, "MÉNSULA DE REACCIÓN (SOLDADA)", "A572 Gr.50, e = 40", 4, fmt_kg(m[2] / 4))
    S.text("ESCALA 1:5", (120, 202), 2.3, "TOP_CENTER")

    # ---------------- POS 3 OREJA 1:2 ----------------
    O = Place((255, 260), 0.5)
    r60 = 60
    pts = [(0, 0), (150, 0), (150, 170 - r60)]
    arc = [(150 - r60 + r60 * math.cos(math.radians(a)), 170 - r60 + r60 * math.sin(math.radians(a))) for a in range(0, 91, 10)]
    arc2 = [(r60 - r60 * math.cos(math.radians(a)), 170 - r60 + r60 * math.sin(math.radians(a))) for a in range(90, -1, -10)]
    S.pline([O(p) for p in pts + arc + arc2 + [(0, 170 - r60)]], "VIS", closed=True)
    S.circle(O((75, 100)), 8); S.centerlines(O((75, 100)), 8, 3)
    S.dim(O((0, 0)), O((150, 0)), -8, "150")
    S.dim(O((150, 0)), O((150, 170)), 6, "170", orient="v")
    S.dim(O((0, 0)), O((0, 100)), -6, "100", orient="v")
    S.dim(O((0, 170)), O((75, 170)), 6, "75")
    S.leader(O((75 + 8 * 0.7 * 2, 100 + 8 * 0.7 * 2)), (O((0, 0))[0] + 60, O((0, 210))[1]), "Ø32 (grillete 4,75 t)", h=2.2)
    S.dim_rad(O((150 - r60, 170 - r60)), 30, 50, "R60", ext=6)
    S.text("Espesor 40. Borde exterior a ras con canto de pos 1.", O((0, -30)), 2.1, "TOP_LEFT")
    S.weld(O((0, 0)), (O((0, 0))[0] - 18, O((0, 40))[1]), "fillet", "12", other=True, all_round=True)
    tag(S, (292, 212), 3, "OREJA DE IZAJE", "A572 Gr.50", 4, fmt_kg(m[3] / 4))

    # ---------------- POS 9 CILINDRO (especificación) 1:5 ----------------
    O = Place((395, 330), 0.2)
    S.circle(O((0, 0)), 12); S.circle(O((0, 0)), 7.1)
    S.rect(*O((60, -70)), *O((330, 70)))
    S.rect(*O((330, -45)), *O((390, 45)))
    S.circle(O((450, 0)), 12); S.circle(O((450, 0)), 7.1)
    S.line(O((-80, 0)), O((700, 0)), "EJE")
    S.dim(O((0, 70)), O((450, 70)), 10, "L0 = 450 ±10 (retraído)")
    S.dim(O((0, -70)), O((650, -70)), -10, "650 (extendido, carrera 200)")
    S.dim(O((200, -70)), O((200, 70)), 0.01, "Ø ≤ 140")
    S.leader(O((450 + 8, 8)), (O((0, 0))[0] + 130, O((0, 140))[1]), "Ojal Ø70 con rótula GE70 (ambos)", h=2.2)
    spec = ["ESPECIFICACIÓN CILINDRO POS 9 (comercial, 2 un.)",
            "• Doble efecto, retorno hidráulico. Presión máx. 700 bar.",
            "• Fuerza de empuje ≥ 445 kN a 700 bar (clase 50 t).",
            "• Carrera 200 mm (36 libre + 164 de empuje). Ojales Ø70, rótula GE70.",
            "• Acoplamientos CR400 hembra; mangueras 700 bar.",
            "• Colector común con bloqueo: no permitir empuje de un solo cilindro;",
            "  y manómetro glicerina 0–1000 bar a la vista del operador.",
            "• Si el ojal difiere: ajustar pos 2 (eje) y pos 12 (Ø)."]
    S.mtext(spec, (375, 300), h=2.2, ls=1.55, bold_first=True)

    # ---------------- POS 19 PASTILLA (U) / FILM (S) ----------------
    if U:
        O = Place((600, 340), 0.4)
        S.circle(O((0, 0)), 34); S.circle(O((0, 0)), 33.8, "FINA"); S.centerlines(O((0, 0)), 34, 4)
        S.dim_dia(O((0, 0)), 34, 40, "Ø170 -0,1/-0,2")
        Os = Place((600, 275), 0.5)
        pts = [Os(p) for p in [(-85, 0), (85, 0), (85, 9.5), (84.5, 10), (-84.5, 10), (-85, 9.5)]]
        hrect(S, pts, pattern="ANSI37", scale=0.45)
        S.dim(Os((85, 0)), Os((85, 10)), 6, "10 ±0,1", orient="v", outside=True)
        sp = ["UHMW-PE PE1000 (ISO 15527), virgen, Mw ≥ 5×10⁶ g/mol.",
              "Presión admisible larga duración ≥ 12 MPa (ensayar).",
              "Alternativa: UHMW certificado para apoyos (EN 1337/ETA).",
              "Cara superior: mecanizada plana Ra ≤ 1,6. Sin lubricante.",
              "Chaflán 0,5×45° borde superior. 34 un. + 4 repuesto."]
        S.mtext(sp, (555, 262), h=2.15, ls=1.5)
        tag(S, (600, 222), 19, "PASTILLA DESLIZANTE", "UHMW-PE PE1000", "34+4", fmt_kg(m[19] / 34))
        S.text("ESCALA 1:2,5 / 1:2", (600, 212), 2.3, "TOP_CENTER")
    else:
        sp = ["POS 19 – GRASA GRAFITADA / POS 20 – GRASERAS",
              "• Grasa grafitada NLGI 2, base complejo de litio o calcio, grafito ≥ 10 %,",
              "  aditivo EP, rango −20/+150 °C, resistente al agua (o equivalente aprobado).",
              "• Superficies: cara sup. pos 1 (Ø2000) y cara inf. 4b completa + ranuras.",
              "• Espesor 0,3–0,5 mm por cara (≈ 2,5 kg por aplicación completa).",
              "• Relubricación: 4 graseras pos 20 (DIN 71412 M10×1) en canto de 4b,",
              "  ≈ 60 g c/u antes de cada operación; conductos Ø6 a ranura R850.",
              "• Grafito conductor eléctrico: aislar de equipos energizados.",
              "• Sin grasa (acero seco μ 0,5–0,8) la tornamesa NO gira: prohibido operar."]
        S.mtext(sp, (560, 322), h=2.25, ls=1.55, bold_first=True)

    # ---------------- POS 14/15/16 SELLO 1:1 ----------------
    O = Place((752, 290), 1.0)
    g = v["g"]
    hrect(S, [O((-40, g)), O((0, g)), O((0, g + 30)), O((-40, g + 30))], scale=0.8)
    S.pline([O((-40, g + 30)), O((-44, g + 34))], "FINA")
    hrect(S, [O((-40, -20)), O((15, -20)), O((15, 0)), O((-40, 0))], scale=0.8, angle=90)
    rub = [O((0, 0)), O((5, 0)), O((5, g + 30)), O((0, g + 30))]
    S.pline(rub, "VIS", closed=True); S.hatch_poly(rub, solid=True)
    bar = [O((5, g + 2.5)), O((11, g + 2.5)), O((11, g + 27.5)), O((5, g + 27.5))]
    S.pline(bar, "VIS", closed=True); S.hatch_poly(bar, scale=0.4)
    zbm = g + 15
    S.rect(*O((11, zbm - 6.5)), *O((16, zbm + 6.5)))
    S.line(O((-16, zbm - 4)), O((11, zbm - 4)), "OCU"); S.line(O((-16, zbm + 4)), O((11, zbm + 4)), "OCU")
    S.line(O((-20, zbm)), O((22, zbm)), "EJE")
    S.dim(O((0, 0)), O((5, 0)), -6, "5", outside=True)
    S.dim(O((-40, g)), O((-40, g + 30)), -5, "30", orient="v")
    S.leader(O((3, 6)), (O((0, 0))[0] + 25, O((0, -10))[1]), "pos 14 NBR 70 ShA", h=2.2)
    S.leader(O((8, g + 24)), (O((0, 0))[0] + 25, O((0, g + 45))[1]), "pos 15 fleje 25×6", h=2.2)
    S.leader(O((15, zbm + 5)), (O((0, 0))[0] + 25, O((0, zbm + 22))[1]), "pos 16 M8×20 A2-70", h=2.2)
    S.text("Plancha inferior 4b", O((-40, g + 36)), 2.1, "BOTTOM_LEFT")
    S.text("Base pos 1", O((-40, -24)), 2.1, "TOP_LEFT")
    S.text("Faldón apoyado sobre pos 1, pretensado 1–2 mm.", O((-40, -32)), 2.1, "TOP_LEFT")
    S.text("Unión del faldón: vulcanizado en frío, traslapo 50.", O((-40, -37)), 2.1, "TOP_LEFT")
    S.text("Fleje rolado Ø2022 en 2 tramos con cubrejunta.", O((-40, -42)), 2.1, "TOP_LEFT")
    S.text("36× M8 radial prof. 16 en canto de 4b (0°+10°k).", O((-40, -47)), 2.1, "TOP_LEFT")
    S.view_title((765, 212), "DETALLE SELLO PERIMETRAL (pos 14/15/16)", "ESCALA 1:1 (parcial)")

    # ---------------- nota de piezas comerciales ----------------
    com = ["PIEZAS COMERCIALES Y TERMINACIONES",
           "• Pos 8: ISO 4762 M20×45 10.9, zincado laminar, con arandela Nord-Lock NL20.",
           "• Clips R Ø8 zincados con cadena de retención para pasadores pos 12.",
           "• Pos 16: ISO 4017 M8×20 A2-70 + arandela ISO 7089 A2.",
           "• Pos 17: prisionero ISO 4026 M30×25 8.8 zincado, ras con cara superior 4a.",
           "• Pos 22: guía 40×40×850 S355J2 embutida 10 en ranura 40 H8 de pos 1; filete 8 ambos lados (W5).",
           "• Pos 13: resorte compresión Ø50×100, k ≈ 5 N/mm, precarga ≈ 150 N; tapa M10 y manilla M12.",
           "• Pos 18: cáncamo giratorio M30, WLL ≥ 2,5 t (tipo RUD VRS o equiv.), suelto.",
           "• Templado y revenido (QT): certificar dureza y ensayo Charpy KV ≥ 27 J a -20 °C.",
           "• Pasadores 5, 11, 12: MT 100 % después del mecanizado; zincado laminar",
           "  o fosfatado + aceite en zonas sin ajuste."]
    S.mtext(com, (26, 170), h=2.25, ls=1.55, bold_first=True)
    return S, v


if __name__ == "__main__":
    import sys, pymupdf
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet4(k)
        S.save(f"out/{v['code']}-04.dxf", f"out/{v['code']}-04.pdf")
        pymupdf.open(f"out/{v['code']}-04.pdf")[0].get_pixmap(dpi=75).save(f"out/{v['code']}-04.png")
        print("ok", k)
```

### tt300/sheet_d02.py
`tt300/sheet_d02.py` — 236 líneas

```python
"""Lámina D-02: accionamiento – cálculo de la fuerza del actuador y verificaciones a 300 tf."""
import math
import params as P, draw, calc as K
from common import Place


def f(x, d=0):
    return K.nf(x, d)


def sheet_d02(kind="S"):
    v = P.variant(kind); v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 2, 3, "DISEÑO – ACCIONAMIENTO Y VERIFICACIONES", "S/E")
    hs = 2.7
    # ======================= COLUMNA 1: HIPÓTESIS =======================
    x1 = 28
    hyp = [
        "1. HIPÓTESIS DE CÁLCULO",
        f"H1  Carga WLL = 300 tf = {f(K.W, 0)} kN; CG con excentricidad e ≤ 150 mm respecto del pivote.",
        f"    Peso disco cajón + buje = 1 922 kg = {f(K.W_DISC, 2)} kN.  N = W + Wd = {f(K.N_F, 1)} kN (giro cuasi-",
        "    estático; φd = 1,10 se aplica solo a resistencias, no a la fricción).",
        "H2  Interfaz de giro: contacto plano anular acero/acero, cara sup. pos 1 / cara inf. 4b,",
        "    R = 1 000 mm, r = 95 mm, con grasa grafitada pos 19 en ambas caras + ranuras (det. L, F-03).",
        "H3  Coeficiente de fricción ESTÁTICO (despegue) de diseño μ = 0,20 = límite superior del",
        "    rango acero/acero engrasado 0,10–0,20 (ref. [1], [2]). Nominal 0,15; contaminado 0,25;",
        "    acero seco 0,50 (rango real 0,5–0,8) – caso prohibido.",
        "H4  Radio efectivo de fricción:  presión uniforme  r_u = 2/3·(R³ − r³)/(R² − r²) = 0,672 m.",
        "    Diseño r_ef = 0,80 m (cubre concentración de presión al borde por e = 150 y flexión del",
        "    disco). Cota física máxima r = 0,94 m (toda la carga en el anillo de barras).",
        "H5  Empuje en PAR: 2 cilindros simultáneos (válvula de bloqueo), cada uno sobre una barra",
        f"    Ø70 en R940. Fuerza paralela a Y; barra entre −5° y +5° → brazo mínimo a = 940·cos5° = {f(K.ARM * 1000, 1)} mm.",
        f"H6  Pérdidas: fricción carro/guía μg = 0,15 (acero engrasado) por el par de excentricidad",
        f"    Δ = {f(K.DELTA * 1000, 1)} mm entre eje del cilindro (x = 1 085) y la barra (x = 936,4); reacciones de",
        f"    guía separadas Lg = {f(K.LG * 1000, 0)} mm. Rendimiento de sellos del cilindro ηc = 0,95.",
        f"H7  Buje del pivote: H = 5 % W, μ = 0,20, r = 75 mm → T_piv = {f(K.T_PIV, 2)} kN·m.",
        f"H8  Cilindro 50 t doble efecto, Ø90 → A = {f(K.A_CYL, 0)} mm²; F = 445 kN a 700 bar (alivio).",
        "H9  Elementos de la cadena de empuje se verifican a la FUERZA DE CALADO 445 kN (alivio",
        "    700 bar), no a la fuerza de diseño: si el disco se traba, nada falla antes que la válvula.",
        "H10 Rótulas GE70 en ambos ojales: sin momento en el vástago. Velocidad de giro ≤ 1 °/s.",
    ]
    y = S.mtext(hyp, (x1, 578), h=hs, ls=1.555, bold_first=True)

    # ---------- esquema de fuerzas ----------
    S.text("2. ESQUEMA DE FUERZAS – PLANTA (S/E)", (x1, y - 4), 2.6, "TOP_LEFT", bold=True)
    sc = 1 / 10.5
    T = Place((152, y - 135), sc)
    c = T((0, 0))
    S.rect(*T((-1200, -1000)), *T((1200, 1000)), "FINA")
    S.circle(c, 1000 * sc)
    S.circle(c, P.R_BAR * sc, "EJE")
    for k in range(P.N_BAR):
        a = math.radians(P.BAR_ANG0 + 10 * k)
        S.circle(T((P.R_BAR * math.cos(a), P.R_BAR * math.sin(a))), 35 * sc)
    S.centerlines(c, 1000 * sc, 3)
    S.circle(c, 75 * sc)
    xb, yb, ye = (P.R_BAR * math.cos(math.radians(-5)), P.R_BAR * math.sin(math.radians(-5)), 0)
    for sx in (1, -1):
        xb_, yb_ = sx * xb, sx * yb
        ybr = -sx * P.Y_BRK
        xc = sx * P.X_CYL
        # cilindro (cuerpo + vástago)
        ya, yb2 = sorted((ybr + sx * 70, ybr + sx * 370))
        S.rect(*T((xc - 70, ya)), *T((xc + 70, yb2)))
        S.rect(*T((xc - 45, min(ybr + sx * 370, yb_ - sx * 250))), *T((xc + 45, max(ybr + sx * 370, yb_ - sx * 250))), "FINA")
        S.line(T((xc, ybr)), T((xc, yb_ - sx * 250)), "EJE")
        S.circle(T((xc, ybr)), 35 * sc * 1.5)
        S.rect(*T((xc - 80, ybr - 140)), *T((xc + 80, ybr + 140)), "FINA")
        # carro
        S.rect(*T((P.SHOE_X0 * sx, yb_ - sx * 280)), *T((P.SHOE_X1 * sx, yb_ + sx * 20)))
        # fuerza sobre la barra
        tip = T((xb_ + sx * 0, yb_))
        tail = T((xb_, yb_ - sx * 420))
        S.line(tail, tip, "VIS")
        S.arrow(tip, math.atan2(tip[1] - tail[1], tip[0] - tail[0]), size=3.4, w=1.3)
        S.text("F_barra", (tail[0] - sx * 2, tail[1] + sx * 2), 2.3, "MIDDLE_RIGHT" if sx > 0 else "MIDDLE_LEFT", bold=True)
        S.text("F_cil", (T((xc, 0))[0] + sx * 6, T((0, -sx * 400))[1]), 2.2, "MIDDLE_LEFT" if sx > 0 else "MIDDLE_RIGHT")
    # brazo a
    S.dim(c, T((xb, yb)), -12, "a = 936,4", orient="h", h=2.1)
    S.dim(T((xb, -650)), T((P.X_CYL, -650)), -4, "Δ=148,6", orient="h", h=1.9)
    # momento resistente (horario) y giro (antihorario)
    S.arc(c, 30, 200, 330, "VIS")
    a1 = math.radians(200)
    S.arrow((c[0] + 30 * math.cos(a1), c[1] + 30 * math.sin(a1)), a1 - math.pi / 2, size=3, w=1.1)
    S.text("T_f = μ·N·r_ef (resistente)", (c[0], c[1] - 35), 2.2, "TOP_CENTER")
    S.arc(c, 22, 30, 150, "FINA")
    a2 = math.radians(150)
    S.arrow((c[0] + 22 * math.cos(a2), c[1] + 22 * math.sin(a2)), a2 + math.pi / 2, size=2.6, w=1.0)
    S.text("giro", (c[0], c[1] + 24), 2.1, "BOTTOM_CENTER")
    yl = y - 135 - 105
    S.mtext(["Par motor = 2 · F_barra · a   (las dos fuerzas forman un par puro: resultante horizontal nula",
             "sobre el pivote). El par de excentricidad F·Δ en cada carro lo toma la guía pos 22 con dos",
             "reacciones R = F·Δ/Lg que generan la fricción adicional 2·μg·R (factor K)."], (x1, yl), h=2.6, ls=1.5)

    # ======================= COLUMNA 2: DESARROLLO =======================
    x2 = 296
    d = K.case(0.20, 0.80)
    Tf = 0.20 * K.N_F * 0.80
    dev = [
        "3. DESARROLLO – FUERZA REQUERIDA EN EL ACTUADOR",
        "(1)  Par de fricción en la interfaz:          T_f = μ · N · r_ef",
        "(2)  Par total resistente:                     T = T_f + T_piv",
        "(3)  Fuerza en cada barra (par de 2):         F_barra = T / (2 · a)",
        "(4)  Factor de pérdidas:                       K = (1 + 2·μg·Δ/Lg) / ηc",
        "(5)  Fuerza en cada cilindro:                 F_cil = K · F_barra",
        "(6)  Presión requerida:                        p = F_cil / A",
        "(7)  Factor de seguridad del accionamiento:  FS = 445 kN / F_cil",
        "(8)  Fricción máxima vencible:                μ_max = (p_max·A·2a/K − T_piv) / (N · r_ef)",
        "",
        "CASO DE DISEÑO (μ = 0,20; r_ef = 0,80 m):",
        f"  T_f = 0,20 × {f(K.N_F, 1)} × 0,80 = {f(Tf, 1)} kN·m",
        f"  T = {f(Tf, 1)} + {f(K.T_PIV, 1)} = {f(d['T'], 1)} kN·m",
        f"  F_barra = {f(d['T'], 1)} / (2 × 0,9364) = {f(d['Fb'], 1)} kN",
        f"  K = (1 + 2 × 0,15 × 0,1486 / 0,250) / 0,95 = {f(K.K_LOSS, 3)}",
        f"  F_cil = {f(K.K_LOSS, 3)} × {f(d['Fb'], 1)} = {f(d['Fc'], 1)} kN  (= {f(d['Fc'] / K.G, 1)} tf)",
        f"  p = {f(d['Fc'] * 1e3, 0)} N / {f(K.A_CYL, 0)} mm² = {f(d['Fc'] * 1e3 / K.A_CYL, 1)} MPa = {f(d['p'], 0)} bar",
        f"  FS = 445 / {f(d['Fc'], 1)} = {f(d['FS'], 2)}   → ACTUADOR SUFICIENTE CON MARGEN",
    ]
    y2 = S.mtext(dev, (x2, 578), h=hs, ls=1.55, bold_first=True)
    rows = []
    for n, mu, r in K.CASES:
        cc = K.case(mu, r)
        st = "NO GIRA" if cc["FS"] < 1 else ("GIRA" if cc["FS"] >= 1.25 else "GIRA (límite)")
        rows.append([n.split(":")[0].replace(" (acero seco) – PROHIBIDO", " (PROHIBIDO)"), f(mu, 2), f(r, 3), f(cc["T"], 0), f(cc["Fb"], 0), f(cc["Fc"], 0),
                     f(cc["p"], 0), f(cc["FS"], 2), st])
    y2 = S.table(x2, y2 - 3, [("CASO", 56, "L"), ("μ", 12, "C"), ("r_ef m", 16, "C"), ("T kN·m", 18, "R"), ("F_barra kN", 22, "R"),
                              ("F_cil kN", 19, "R"), ("p bar", 16, "R"), ("FS", 14, "R"), ("RESULTADO", 30, "C")], rows, rh=6.5, h=2.5)
    S.text("Caso 'Sin lubricación': exige 1 039 bar > 700 bar de alivio → la tornamesa no gira (sin daño: ver H9).", (x2, y2 - 3), 2.5, "TOP_LEFT")
    rows2 = []
    for r in (K.R_UNIF, 0.80, 0.94):
        rows2.append([f(r, 3), "uniforme" if r < 0.7 else ("DISEÑO" if r < 0.9 else "cota máxima"), f(K.mu_max(r, 700), 3), f(K.mu_max(r, 600), 3)])
    y2 = S.table(x2, y2 - 8, [("r_ef (m)", 24, "C"), ("hipótesis", 30, "C"), ("μ_max a 700 bar", 40, "C"), ("μ_max a 600 bar", 40, "C")], rows2, rh=6.2, h=2.5)
    S.text("Ec. (8): fricción que el accionamiento aún vence.", (x2 + 140, y2 + 17), 2.5, "TOP_LEFT")
    S.text("Margen sobre μ diseño 0,20: ×1,41 (r 0,80).", (x2 + 140, y2 + 11), 2.5, "TOP_LEFT")
    op = [
        "4. AJUSTES HIDRÁULICOS Y CRITERIO DE OPERACIÓN",
        "• Válvula de alivio: 700 bar (F = 445 kN/cil.). Bomba ≥ 700 bar, manómetro glicerina 0–1 000 bar clase 1,0.",
        f"• Presión esperada de giro (nominal, μ 0,15): ≈ {f(K.case(0.15, K.R_UNIF)['p'], 0)} bar.  Despegue de diseño ≤ {f(d['p'], 0)} bar.",
        "• ALARMA / DETENCIÓN: p > 600 bar (μ equivalente > 0,24 con r 0,80): detener, retraer, relubricar",
        "  por las 4 graseras pos 20, inspeccionar materiales extraños bajo el disco y reintentar.",
        "• PROHIBIDO aumentar el alivio sobre 700 bar ni operar con un solo cilindro.",
        "• ENSAYO DE ACEPTACIÓN a 1,0 WLL: registrar p de despegue y μ_real con (8) usando p medida:",
        f"  μ_real = (p·A·2a/K − T_piv)/(N·0,80). Aceptación: μ_real ≤ 0,20 (p_despegue ≤ {f(d['p'], 0)} bar).",
        "• Ciclo: carrera 200 = 36 libre + 164 útil → 10° por ciclo; 36 ciclos por vuelta completa.",
        "",
        "5. GRASA GRAFITADA POS 19 (ESPECIFICACIÓN)",
        "• NLGI 2, base complejo de litio o calcio, grafito ≥ 10 % en peso, aditivo EP (4 bolas ≥ 2 500 N),",
        "  rango −20/+150 °C, resistente al lavado por agua. Equivalente aprobado por el mandante.",
        "• Aplicar 0,3–0,5 mm por cara sobre pos 1 (Ø2000) y 4b, llenando ranuras (≈ 2,5 kg por aplicación).",
        "• Relubricar ≈ 60 g por grasera (4 × pos 20) antes de cada operación y cada 90° de giro con carga.",
        "• No usar grasas sin sólidos ni aceites: a 1,0–1,7 MPa la película fluida se expulsa; el grafito",
        "  mantiene la capa límite (μ 0,10–0,20). El grafito es conductor: aislar equipos energizados.",
        "",
        "6. FUENTES DE COEFICIENTES DE FRICCIÓN",
        "[1] Engineering ToolBox, 'Friction and Friction Coefficients': acero/acero seco μs 0,5–0,8;",
        "    acero/acero engrasado μs 0,16.",
        "[2] Guía de deslizamiento de cargas pesadas (rigging/skidding): acero/acero seco 0,40–0,60;",
        "    acero/acero engrasado 0,10–0,20.",
        "[3] AISC 360-22 (ASD); ASME BTH-1-2020; AWS D1.1/D1.1M:2020.",
    ]
    S.mtext(op, (x2, y2 - 8), h=hs, ls=1.55, bold_first=True)
    # títulos en negrita intermedios
    # ======================= COLUMNA 3: GRÁFICO + VERIFICACIONES =======================
    x3 = 586
    S.text("7. FUERZA POR CILINDRO vs μ", (x3, 578), 2.6, "TOP_LEFT", bold=True)
    gx0, gy0, gw, gh = x3 + 14, 452, 225, 112
    mu_max_ax, F_ax = 0.40, 700.0
    X = lambda m: gx0 + m / mu_max_ax * gw
    Y = lambda F: gy0 + F / F_ax * gh
    S.rect(gx0, gy0, gx0 + gw, gy0 + gh, "VIS")
    for i in range(0, 9):
        m = i * 0.05
        S.line((X(m), gy0), (X(m), gy0 + gh), "FINA" if 0 < i < 8 else "VIS")
        S.text(f(m, 2), (X(m), gy0 - 1.5), 2.0, "TOP_CENTER")
    for Fv in range(0, 701, 100):
        S.line((gx0, Y(Fv)), (gx0 + gw, Y(Fv)), "FINA")
        S.text(str(Fv), (gx0 - 1.5, Y(Fv)), 2.0, "MIDDLE_RIGHT")
    S.text("μ (estático)", (gx0 + gw / 2, gy0 - 6), 2.2, "TOP_CENTER")
    S.text("F_cil (kN)", (gx0 - 12, gy0 + gh + 2), 2.2, "BOTTOM_LEFT")
    for r, lay, lab in ((K.R_UNIF, "VIS", "r 0,672"), (0.80, "VIS", "r 0,80 (diseño)"), (0.94, "OCU", "r 0,94")):
        pts = []
        for i in range(0, 41):
            m = i * 0.01
            Fc = K.case(m, r)["Fc"]
            if Fc <= F_ax:
                pts.append((X(m), Y(Fc)))
        S.pline(pts, lay)
        S.text(lab, (pts[-1][0] - 1, pts[-1][1] - 1), 2.0, "TOP_RIGHT")
    for Fv, lab in ((445, "445 kN = 700 bar (alivio)"), (381.4, "381 kN = 600 bar (alarma)")):
        S.line((gx0, Y(Fv)), (gx0 + gw, Y(Fv)), "VIS" if Fv > 400 else "OCU")
        S.text(lab, (gx0 + 2, Y(Fv) + 1), 2.0, "BOTTOM_LEFT", bold=Fv > 400)
    S.line((X(0.10), gy0), (X(0.10), gy0 + gh), "EJE")
    S.line((X(0.20), gy0), (X(0.20), gy0 + gh), "EJE")
    S.text("engrasado 0,10–0,20", (X(0.15), gy0 + gh - 2), 2.0, "TOP_CENTER")
    S.line((X(0.50 if 0.5 < mu_max_ax else 0.39), gy0), (X(0.39), gy0), "VIS")
    pd = (X(0.20), Y(d["Fc"]))
    S.circle(pd, 1.4); S.hatch_poly([(pd[0] + 1.4 * math.cos(t / 10 * 6.283), pd[1] + 1.4 * math.sin(t / 10 * 6.283)) for t in range(10)], solid=True)
    S.leader(pd, (X(0.24), Y(200)), f"Diseño: {f(d['Fc'], 0)} kN – {f(d['p'], 0)} bar", h=2.1)
    S.text("Acero seco (0,5–0,8) fuera de escala: 660 kN > 445 kN", (gx0 + gw - 1, gy0 + 2), 2.0, "BOTTOM_RIGHT")

    S.text("8. VERIFICACIÓN DE ELEMENTOS – 300 tf (cadena de empuje a F calado = 445 kN)", (x3, 438), 2.4, "TOP_LEFT", bold=True)
    vr, ex = K.verifs()
    rows3 = []
    for e, dem, cap, fu, ref in vr:
        st = "OK" if fu <= 0.90 else ("MONIT." if fu <= 1.0 else "NO")
        rows3.append([e, dem.replace(".", ","), cap, f(fu, 2), st, ref])
    y3 = S.table(x3, 432, [("ELEMENTO / SOLICITACIÓN", 88, "L"), ("DEMANDA", 34, "C"), ("CAPACIDAD", 25, "C"), ("FU", 11, "C"), ("", 12, "C"), ("REFERENCIA", 73, "L")],
                 rows3, rh=6.4, h=2.3)
    fus = [r[3] for r in vr]
    S.mtext([f"FU máximo = {f(max(fus), 2)} (trinquete pos 11) ≤ 0,90 → ACEPTABLE.  Aplastamiento AISC J7: Rn/Ω = 1,8·Fy·Apb/2,0.",
             "Placas 4a/4b y almas 4d: solicitación de servicio con φd = 1,10 (carga sobre parrilla, H1).",
             f"Barra 4f: M rotulada = F/4·(L − c/2) = {f(ex['Mss'], 2)} kN·m;  soldadura con M empotrada = F(3L² − c²)/(24L) = {f(ex['Mfe'], 2)} kN·m.",
             f"Guía pos 22: R = F·Δ/Lg = {f(ex['Rg'], 0)} kN tomada por aplastamiento en ranura 40 H8 × 10 (det. M, F-03).",
             f"Accidental 1 cilindro (prohibido por válvula): buje {f(ex['pb1'], 1)} MPa / 30 MPa (FU 0,99) – sin margen, no admisible.",
             "Presión bajo placa base: 0,62 MPa media / 0,90 MPa máx. (e = 150) – verificar losa/mats por terceros."],
            (x3, y3 - 3), h=2.3, ls=1.5)
    # resumen destacado
    bx0, by1 = 20 + 8, 222
    S.rect(bx0, by1 - 40, bx0 + 262, by1, "MARCO")
    S.mtext(["RESULTADO – FUERZA DEL ACTUADOR",
             f"Fuerza de diseño por cilindro:  F_cil = {f(d['Fc'], 0)} kN ({f(d['Fc'] / K.G, 1)} tf)  →  p = {f(d['p'], 0)} bar",
             f"Fuerza disponible por cilindro:  445 kN a 700 bar   →   FS = {f(d['FS'], 2)}",
             f"Fuerza en cada barra: {f(d['Fb'], 0)} kN; par total de giro: {f(d['T'], 0)} kN·m (2 cilindros en par)",
             f"Fricción máxima vencible: μ = {f(K.mu_max(0.80), 2)} (r 0,80) / {f(K.mu_max(0.94), 2)} (cota física r 0,94)",
             "Gira con certeza en todo el rango acero/acero ENGRASADO (0,10–0,20), incluida",
             "la hipótesis de carga concentrada al borde. NO gira en seco: lubricación OBLIGATORIA.",
             "Elementos verificados a la fuerza máxima del cilindro: FU ≤ 0,86."],
            (bx0 + 3, by1 - 3), h=2.7, ls=1.6, bold_first=True)
    return S, v


if __name__ == "__main__":
    S, v = sheet_d02("S")
    S.save("out/TT300-B-D-02.dxf", "out/TT300-B-D-02.pdf")
    import pymupdf
    pymupdf.open("out/TT300-B-D-02.pdf")[0].get_pixmap(dpi=90).save("out/TT300-B-D-02.png")
```

### tt300/sheet_f03.py
`tt300/sheet_f03.py` — 221 líneas

```python
"""Lámina F-03: lista de corte, programa de soldaduras, det. L (lubricación 4b) y det. M (guía embutida)."""
import math, json
import params as P, draw, calc as K
from common import Place

RHO = 7.85e-6


def f(x, d=0):
    return K.nf(x, d)


def kg_box(a, b, c):
    return a * b * c * RHO


def kg_cyl(d, l):
    return math.pi * d ** 2 / 4 * l * RHO


def cut_rows():
    m = {int(k): v for k, v in json.load(open("/home/claude/tt300/out/TT300-B_mass.json")).items()}
    A572 = "A572 Gr.50 – Z35"
    hole71 = kg_cyl(71, 40)
    R = [
        ["1", "Placa base (2 ranuras 40H8×10, Ø150H7)", "2410×2010×85", "2400×2000×80", 1, A572, m[1]],
        ["2a", "Mejilla ménsula (Ø71 H9 en línea)", "45×285×155", "40×280×150", 8, "A572 Gr.50", kg_box(40, 280, 150) - hole71],
        ["2b", "Respaldo ménsula", "45×165×155", "40×160×150", 4, "A572 Gr.50", kg_box(40, 160, 150)],
        ["3", "Oreja izaje (R60 sup., Ø32)", "40×155×175", "40×150×170", 4, "A572 Gr.50", m[3] / 4],
        ["22", "Guía de carro (embutida 10)", "45×45×855", "40 h9×40×850", 2, "S355J2", m[22] / 2],
        ["4a", "Plancha sup. (Ø300, 36×Ø71, 4×M30, ranuras)", "□2020×35", "Ø2000×30", 1, A572, 689.1],
        ["4b", "Plancha inf. (Ø300, 36×Ø71, ranuras lubr.)", "□2020×35", "Ø2000×30", 1, A572, 689.6],
        ["4c", "Cubo (forja)", "Ø310×170", "Ø300×160", 1, "S355J2+N forjado", 50.6],
        ["4d1", "Alma anillo R300, rolada (desarrollo eje)", "25×100×1 905", "L = 1 885", 1, "A572 Gr.50", kg_box(25, 100, 1885)],
        ["4d2", "Alma anillo R550, rolada", "25×100×3 476", "L = 3 456", 1, "A572 Gr.50", kg_box(25, 100, 3456)],
        ["4d3", "Alma anillo R735, rolada", "25×100×4 638", "L = 4 618", 1, "A572 Gr.50", kg_box(25, 100, 4618)],
        ["4e1", "Nervio radial R150–R287,5", "20×100×140", "20×100×137,5", 12, "A572 Gr.50", kg_box(20, 100, 137.5)],
        ["4e2", "Nervio radial R312,5–R537,5", "20×100×228", "20×100×225", 12, "A572 Gr.50", kg_box(20, 100, 225)],
        ["4e3", "Nervio radial R562,5–R722,5", "20×100×163", "20×100×160", 12, "A572 Gr.50", kg_box(20, 100, 160)],
        ["4e4", "Nervio radial R747,5–R880", "20×100×135", "20×100×132,5", 12, "A572 Gr.50", kg_box(20, 100, 132.5)],
        ["4f", "Barra de empuje (a ras tras mecanizar)", "Ø70×164", "Ø70×160", 36, "S355J2 laminado", kg_cyl(70, 160)],
        ["5", "Pivote (6×M20 en cabeza)", "Ø160×225", "Ø150 p6/f7×218", 1, "42CrMo4+QT", m[5]],
        ["6", "Buje autolubricado", "comercial", "Ø190 s6/Ø150 H7×100", 1, "CuAl10Ni5Fe4+graf.", m[6]],
        ["7", "Tapa retenedora", "250×250×25", "Ø240×20", 1, "S355J2", m[7]],
        ["10", "Carro de empuje (ranura 41×31)", "135×305×155", "130×300×150", 2, "S355J2+N", m[10] / 2],
        ["11", "Trinquete (asiento R36)", "255×95×100", "245×85×90", 2, "34CrNiMo6+QT", m[11] / 2],
        ["12", "Pasador ménsula / vástago (cabeza Ø90)", "Ø95×220", "Ø70 f8×200 + cab. 15", 4, "42CrMo4+QT", m[12] / 4],
        ["14", "Faldón de sello (perf. Ø24 en graseras)", "5×30×6 350", "5×30×6 300", 1, "NBR 70 Sh A", m[14]],
        ["15", "Fleje de apriete (perf. Ø24 en graseras)", "25×6×6 420", "rolado Ø2022", 1, "S235JR galv.", m[15]],
    ]
    return R


def sheet_f03(kind="S"):
    v = P.variant(kind); v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 3, 3, "FABRICACIÓN – LISTA DE CORTE, SOLDADURAS Y LUBRICACIÓN", "INDICADA")
    x0 = 28
    S.text("LISTA DE CORTE Y DESPIECE – CONJUNTO TT300-B (masas de piezas terminadas)", (x0, 579), 2.8, "TOP_LEFT", bold=True)
    rows = []
    tot = 0
    for sub, desc, bruto, fin, q, mat, kg in cut_rows():
        rows.append([sub, desc, bruto, fin, str(q), mat, f(kg, 1), f(kg * q, 1)])
        tot += kg * q
    rows.append(["", "TOTAL PIEZAS FABRICADAS (sin cilindros, pernos ni grasa)", "", "", "", "", "", f(tot, 0)])
    y = S.table(x0, 573, [("POS", 13, "C"), ("DESCRIPCIÓN", 92, "L"), ("CORTE / BRUTO", 38, "C"), ("TERMINADO", 44, "C"),
                          ("CANT.", 12, "C"), ("MATERIAL", 44, "L"), ("kg/u", 17, "R"), ("kg total", 20, "R")],
                rows, rh=6.6, h=2.6)
    S.mtext(["Sobremetal de mecanizado 2,5 mm/cara en caras funcionales; planchas cortadas con eje de laminación anotado.",
             "Almas 4d: largo bruto = desarrollo en eje neutro + 20 (recorte tras rolar); radio ±2, cierre con junta CJP (W11).",
             "Nervios 4e: largo final ajustado en obra a la distancia real entre almas (holgura de raíz 2 ±1)."],
            (x0, y - 3), h=2.5, ls=1.5)
    # --------- programa de soldaduras ---------
    yw = y - 20
    S.text("PROGRAMA DE SOLDADURAS (AWS D1.1/D1.1M:2020 – E7018 / ER70S-6, FEXX = 490 MPa)", (x0, yw), 2.8, "TOP_LEFT", bold=True)
    wr = [
        ["W1", "2a – 1", "CJP doble bisel 45°, raíz 3 + filete refuerzo 8", "280 × 2 × 8", "UT 100 %"],
        ["W2", "2b – 1", "Filete ambos lados", "16", "MT 100 %"],
        ["W3", "2b – 2a", "Filete ambos lados (vertical)", "16", "MT 100 %"],
        ["W4", "3 – 1", "Filete todo alrededor", "12", "MT 100 %"],
        ["W5", "22 – 1", "Filete ambos lados, continuo (fijación; carga por aplastamiento)", "8", "MT 100 %"],
        ["W6", "4c – 4b / 4c – 4a", "CJP bisel 45° c/respaldo, por el exterior del cubo", "t = 30", "UT 100 %"],
        ["W7", "4d – 4b", "Filete ambos lados, continuo", "8", "MT 100 %"],
        ["W8", "4e – 4b / 4c / 4d", "Filete ambos lados, continuo", "8", "MT 100 %"],
        ["W9", "4a – 4d / 4e", "Soldadura en ranura 22×80, relleno completo (88 un.)", "c/250", "MT 100 %"],
        ["W10", "4f – 4a / 4b", "PJP bisel 15 todo alrededor (E = 12), a ras y mecanizado", "15", "MT 100 %"],
        ["W11", "Empalmes 4d", "CJP a tope en V 60°, raíz 3 (1 por anillo)", "t = 25", "UT 100 %"],
    ]
    y = S.table(x0, yw - 5, [("JUNTA", 14, "C"), ("ELEMENTOS", 40, "L"), ("TIPO Y PREPARACIÓN", 152, "L"), ("TAMAÑO", 29, "C"), ("END", 25, "C")],
                wr, rh=6.4, h=2.55)
    S.mtext(["PRECALENTAMIENTO (AWS D1.1 Tabla 5.8, Cat. B; espesor mayor de la junta): t > 65 mm (pos 1): 110 °C;",
             "38 < t ≤ 65: 65 °C; 20 < t ≤ 38 (disco 4a–4f): 10 °C, se exige 50 °C mín. para eliminar humedad. Interpase ≤ 250 °C.",
             "Secuencia del disco: W7 → W8 → W6 (4b) → W10 (4b) → montar 4a → W9 → W6 (4a) → W10 (4a), soldando en cuadrantes",
             "opuestos. Alivio de tensiones 590–620 °C antes del mecanizado final (Notas generales, N° 5).",
             "W10: única soldadura que transmite el empuje de la barra; resistencia verificada sin aporte del aplastamiento (D-02)."],
            (x0, y - 3), h=2.45, ls=1.5)

    # =================== DET. L – VISTA INFERIOR 4b (1:12,5) ===================
    sc = 1 / 10
    cL = (470, 450)
    L = Place(cL, sc)
    S.circle(cL, 1000 * sc)
    S.circle(cL, 150 * sc, "FINA")
    S.circle(cL, 95 * sc)
    for k in range(P.N_BAR):
        a = math.radians(P.BAR_ANG0 + 10 * k)
        S.circle(L((P.R_BAR * math.cos(a), P.R_BAR * math.sin(a))), 35.5 * sc)
    for r in (350, 600, 850):
        S.circle(cL, r * sc, "VIS")
    for k in range(12):
        a = math.radians(30 * k)
        S.line(L((200 * math.cos(a), 200 * math.sin(a))), L((960 * math.cos(a), 960 * math.sin(a))), "VIS")
    for k in range(4):
        a = math.radians(45 + 90 * k)
        p0 = L((850 * math.cos(a), 850 * math.sin(a)))
        p1 = L((1000 * math.cos(a), 1000 * math.sin(a)))
        S.line(p0, p1, "OCU")
        S.circle(p0, 0.6 * 6 * sc * 4, "VIS")
        S.circle(p1, 1.6, "VIS")
    S.centerlines(cL, 1000 * sc, 4)
    S.view_title((cL[0], cL[1] + 116), "DETALLE L – CARA INFERIOR 4b (vista desde abajo)", "ESC. 1:10")
    S.leader(L((0, 350)), (cL[0] + 62, cL[1] + 104), "Ranura circ. R350 / R600 / R850", h=2.1)
    S.leader(L((600 * math.cos(math.radians(60)), 600 * math.sin(math.radians(60)))), (cL[0] - 40, cL[1] + 108), "12 ranuras radiales c/30° (0°…330°), R200→R960", h=2.1)
    a = math.radians(45)
    S.leader(L((1000 * math.cos(a), 1000 * math.sin(a))), (cL[0] + 110, cL[1] + 78), "4 graseras pos 20 a 45°+90°k (det. L2)", h=2.1)
    S.leader(L((P.R_BAR * math.cos(math.radians(-5)), P.R_BAR * math.sin(math.radians(-5)))), (cL[0] + 112, cL[1] - 40), "36 × Ø71 (barras 4f) – no cruzar con ranuras", h=2.1)
    S.leader(L((0, -95)), (cL[0] + 50, cL[1] - 110), "Cubo 4c Ø190 H7 (buje)", h=2.1)
    S.text("Ranuras radiales en ejes de nervios 4e (0°+30°k): libre ≥ 82 mm a barras 4f.", (cL[0] - 110, cL[1] - 118), 2.4, "TOP_LEFT")
    S.text("Mecanizar ranuras DESPUÉS del alivio de tensiones y del refrentado de 4b.", (cL[0] - 110, cL[1] - 123.5), 2.4, "TOP_LEFT")

    # =================== DET. L1 – sección de ranura 5:1 ===================
    o = (700, 520)
    s5 = 5.0
    S.view_title((o[0] + 20, o[1] + 20), "DET. L1 – RANURA", "ESC. 5:1", h=3.2)
    w = math.sqrt(9 - 1)
    outer = [(o[0] - 25, o[1]), (o[0] - w * s5, o[1])]
    arcpts = []
    for i in range(0, 21):
        t = math.pi + math.asin(1 / 3) + i / 20 * (math.pi - 2 * math.asin(1 / 3))
        arcpts.append((o[0] + 3 * s5 * math.cos(t), o[1] + 1 * s5 + 3 * s5 * math.sin(t)))
    poly = [(o[0] - 25, o[1])] + arcpts + [(o[0] + 25, o[1]), (o[0] + 25, o[1] + 22), (o[0] - 25, o[1] + 22)]
    S.pline([(o[0] - 25, o[1])] + arcpts + [(o[0] + 25, o[1])])
    S.hatch_poly(poly, scale=0.8)
    S.line((o[0] - 25, o[1] + 22), (o[0] + 25, o[1] + 22), "FINA")
    S.dim((o[0] - w * s5, o[1]), (o[0] + w * s5, o[1]), -13, "≈5,7", orient="h", h=2.2)
    S.dim((o[0] + 18, o[1]), (o[0] + 18, o[1] - 2 * s5), 6, "2", orient="v", h=2.2)
    S.leader(arcpts[14], (o[0] + 28, o[1] - 16), "R3", h=2.2)
    S.text("cara inf. 4b (contacto)", (o[0] - 25, o[1] + 1), 2.0, "BOTTOM_LEFT")
    S.text("Ra 1,6 – aristas matadas 0,5", (o[0] - 25, o[1] - 20), 2.0, "TOP_LEFT")

    # =================== DET. L2 – grasera (sección radial a 45°) 1:2 ===================
    s2 = 0.5
    g = Place((680, 305), s2, (850, 80))      # modelo: x radial, z
    pl = [g((800, 80)), g((1000, 80)), g((1000, 110)), g((800, 110))]
    S.pline(pl[:3] + [pl[3]])
    S.hatch_poly([g((800, 80)), g((849, 80)), g((849, 85)), g((847, 85)), g((847, 91)), g((1000 - 12, 91)), g((1000 - 12, 85)), g((1000, 85)),
                  g((1000, 110)), g((800, 110))], scale=0.6)
    S.hatch_poly([g((851, 80)), g((1000, 80)), g((1000, 85)), g((853, 85)), g((853, 80))], scale=0.6)
    S.line(g((850, 88)), g((1000, 88)), "EJE")
    S.line(g((850, 76)), g((850, 92)), "EJE")
    S.rect(*g((1000, 82.5)), *g((1006, 107.5)), "VIS")   # faldón (aprox.)
    S.rect(*g((1005, 82.5)), *g((1011, 107.5)), "VIS")   # fleje
    S.pline([g((1000, 84)), g((1027, 84)), g((1027, 92)), g((1000, 92))], "VIS")   # grasera
    S.circle(g((1029, 88)), 2.0)
    S.line(g((780, 80)), g((1040, 80)), "FINA")
    S.text("4b (sección)", g((805, 112)), 2.0, "BOTTOM_LEFT")
    S.view_title((g((900, 0))[0], g((0, 155))[1]), "DET. L2 – GRASERA (sección radial a 45°)", "ESC. 1:2", h=3.2)
    S.dim(g((850, 80)), g((1000, 80)), -9, "150 (R850→R1000)", orient="h", h=2.1)
    S.dim(g((800, 80)), g((800, 88)), -5, "8", orient="v", h=2.0)
    S.dim(g((800, 80)), g((800, 110)), -12, "30", orient="v", h=2.0)
    S.leader(g((930, 88)), (g((930, 0))[0], g((0, 130))[1] + 4), "Taladro radial Ø6 ciego, L 150", h=2.0)
    S.leader(g((850, 84)), (g((850, 0))[0] - 15, g((0, 62))[1]), "Taladro Ø6 a ranura R850", h=2.0)
    S.leader(g((1018, 92)), (g((1018, 0))[0] + 6, g((0, 130))[1] + 4), "Pos 20 M10×1, rosca L12", h=2.0)
    S.leader(g((1008, 82.5)), (g((1008, 0))[0] + 8, g((0, 64))[1]), "Faldón 14 + fleje 15: perf. Ø24", h=2.0)

    # =================== DET. M – guía embutida 1:1 ===================
    om = (735, 410)
    M = Place(om, 1.0, (P.X_CYL, P.TB))
    S.view_title((om[0], om[1] + 62), "DET. M – GUÍA POS 22 EMBUTIDA", "ESC. 1:1", h=3.2)
    xg0, xg1 = P.X_CYL - 20, P.X_CYL + 20
    # placa base con ranura
    base = [M((P.X_CYL - 55, P.TB - 30)), M((P.X_CYL + 55, P.TB - 30)), M((P.X_CYL + 55, P.TB)), M((xg1, P.TB)),
            M((xg1, P.TB - 10)), M((xg0, P.TB - 10)), M((xg0, P.TB)), M((P.X_CYL - 55, P.TB))]
    S.pline(base, closed=True)
    S.hatch_poly(base, scale=1.2)
    rail = [M((xg0, P.TB - 10)), M((xg1, P.TB - 10)), M((xg1, P.TB + 30)), M((xg0, P.TB + 30))]
    S.pline(rail, closed=True)
    S.hatch_poly(rail, scale=1.2, angle=90)
    for sx in (-1, 1):
        xe = P.X_CYL + sx * 20
        tri = [M((xe, P.TB)), M((xe + sx * 8, P.TB)), M((xe, P.TB + 8))]
        S.pline(tri, closed=True); S.hatch_poly(tri, solid=True)
    S.pline([M((P.X_CYL - 50, P.TB + 50)), M((P.X_CYL - 50, P.TB + 1)), M((P.X_CYL - 20.5, P.TB + 1)), M((P.X_CYL - 20.5, P.TB + 31)),
             M((P.X_CYL + 20.5, P.TB + 31)), M((P.X_CYL + 20.5, P.TB + 1)), M((P.X_CYL + 50, P.TB + 1)), M((P.X_CYL + 50, P.TB + 50))], "FANT")
    S.text("carro pos 10 (ranura 41 H11×31)", M((P.X_CYL - 50, P.TB + 52)), 2.0, "BOTTOM_LEFT")
    S.dim(M((xg0, P.TB - 10)), M((xg1, P.TB - 10)), -26, "40 H8/h9", orient="h", h=2.2)
    S.dim(M((xg1, P.TB - 10)), M((xg1, P.TB)), 40, "10", orient="v", h=2.2)
    S.dim(M((xg1, P.TB)), M((xg1, P.TB + 30)), 40, "30", orient="v", h=2.2)
    S.weld(M((xg0 - 3, P.TB + 2)), (M((xg0, 0))[0] - 18, M((0, P.TB + 22))[1]), "fillet", "8", other=True, note="W5")
    S.text("R = F·Δ/Lg = 264 kN por aplastamiento", (om[0] - 45, om[1] - 46), 2.1, "TOP_LEFT")
    S.text("en ranura (FU 0,57); W5 solo fija.", (om[0] - 45, om[1] - 50), 2.1, "TOP_LEFT")

    # =================== notas de control ===================
    ctl = ["CONTROL DIMENSIONAL Y ENSAYOS DE FABRICACIÓN",
           "• Placa base pos 1: planitud cara sup. 0,20 en Ø2000; ranuras 40 H8 paralelas al eje Y ±0,10 en 850.",
           "• Disco pos 4: planitud 4b 0,20; paralelismo 4a/4b 0,30; barras 4f PCD 1880 ±0,5, paso 10° ±0,05°.",
           "• Ranuras de lubricación: profundidad 2 +0,3/0; continuidad verificada inyectando grasa por cada",
           "  grasera hasta ver salida por la ranura R850 y las radiales (protocolo con fotografías).",
           "• Rugosidad caras de giro pos 1 y 4b: Ra 3,2 máx. (fresado/rectificado), sin rayas radiales.",
           "• UT de planchas pos 1, 4a, 4b: ASTM A578 nivel B. Trazabilidad: colada estampada en cada pieza.",
           "• Pos 5, 11, 12: certificado de temple y revenido + dureza (pos 11: 300–350 HB; pos 12: 28–34 HRC).",
           "• Masa total del conjunto pesada en balanza calibrada; tolerancia ±3 % respecto de esta lista."]
    S.mtext(ctl, (360, 250), h=2.6, ls=1.55, bold_first=True)
    return S, v


if __name__ == "__main__":
    S, v = sheet_f03("S")
    S.save("out/TT300-B-F-03.dxf", "out/TT300-B-F-03.pdf")
    import pymupdf
    pymupdf.open("out/TT300-B-F-03.pdf")[0].get_pixmap(dpi=90).save("out/TT300-B-F-03.png")
```

### tt300/build300.py
`tt300/build300.py` — 26 líneas

```python
import pymupdf, zipfile, os, draw, sheet1, sheet2, sheet3, sheet4, sheet_d02, sheet_f03
code = "TT300-B"
sets = {
    "Diseno": [("D-01", "DISEÑO – CONJUNTO GENERAL, CORTES Y DATOS", sheet1.sheet1),
               ("D-02", "DISEÑO – ACCIONAMIENTO Y VERIFICACIONES", sheet_d02.sheet_d02),
               ("D-03", None, sheet2.sheet2)],
    "Fabricacion": [("F-01", None, sheet3.sheet3), ("F-02", None, sheet4.sheet4),
                    ("F-03", "FABRICACIÓN – LISTA DE CORTE, SOLDADURAS Y LUBRICACIÓN", sheet_f03.sheet_f03)],
}
dxfs = []
for name, sheets in sets.items():
    out = pymupdf.open()
    for i, (tag, title, fn) in enumerate(sheets, 1):
        draw.OVR.clear(); draw.OVR.update({"no": i, "n": len(sheets), "plano": f"{code}-{tag}"})
        if title: draw.OVR["title"] = title
        S, v = fn("S")
        d, p = f"out/{code}-{tag}.dxf", f"out/{code}-{tag}.pdf"
        S.save(d, p); dxfs.append(d)
        out.insert_pdf(pymupdf.open(p))
        pymupdf.open(p)[0].get_pixmap(dpi=90).save(f"out/{code}-{tag}.png")
    out.set_metadata({"title": f"{code} Tornamesa 300 tf – Planos de {name}", "author": "", "subject": v["title"]})
    out.save(f"out/{code}_Tornamesa300_Planos_{name}.pdf", garbage=3, deflate=True)
with zipfile.ZipFile(f"out/{code}_Tornamesa300_DXF_STEP.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for d in dxfs: z.write(d, os.path.basename(d))
    z.write(f"out/{code}.step", f"{code}_conjunto.step")
print("ok")
```

### tt300/build_all.py
`tt300/build_all.py` — 16 líneas

```python
import pymupdf, sheet1, sheet2, sheet3, sheet4, zipfile, os
names = {"U": "TT500-A_Tornamesa_UHMW", "S": "TT500-B_Tornamesa_Acero-Grafito"}
for k in ("U", "S"):
    out = pymupdf.open()
    dxfs = []
    for i, f in enumerate((sheet1.sheet1, sheet2.sheet2, sheet3.sheet3, sheet4.sheet4), 1):
        S, v = f(k)
        d, p = f"out/{v['code']}-{i:02d}.dxf", f"out/{v['code']}-{i:02d}.pdf"
        S.save(d, p); dxfs.append(d)
        out.insert_pdf(pymupdf.open(p))
    out.set_metadata({"title": f"{names[k]} – Planos mecánicos", "author": "", "subject": v["title"]})
    out.save(f"out/{names[k]}_Planos.pdf", garbage=3, deflate=True)
    with zipfile.ZipFile(f"out/{names[k]}_DXF.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for d in dxfs: z.write(d, os.path.basename(d))
        z.write(f"out/{v['code']}.step", f"{v['code']}_conjunto.step")
    print(k, "ok")
```

## Apéndice D. Pruebas automatizadas y scripts del revisor

### tt300/app/tests/shot.js
`tt300/app/tests/shot.js` — 55 líneas

```javascript
const { chromium } = require('playwright');
const path = require('path');
const NM = path.join(__dirname, 'node_modules');
const map = {
  'jspdf@2.5.1/dist/jspdf.umd.min.js': NM + '/jspdf/dist/jspdf.umd.min.js',
  'jspdf-autotable@3.8.2/dist/jspdf.plugin.autotable.min.js': NM + '/jspdf-autotable/dist/jspdf.plugin.autotable.min.js',
  'jszip@3.10.1/dist/jszip.min.js': NM + '/jszip/dist/jszip.min.js',
};
const OUT = process.argv[2] || '/tmp/claude-0/-home-claude/f880023e-4047-5d94-81d4-3b8b32341d04/scratchpad';
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--headless=new'], ignoreDefaultArgs: ['--headless=old'] });
  for (const scheme of ['light', 'dark']) {
    const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 }, colorScheme: scheme, acceptDownloads: true });
    const page = await ctx.newPage();
    const errs = [];
    page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
    page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
    await page.route('https://cdn.jsdelivr.net/npm/**', (r) => { const k = Object.keys(map).find((k) => r.request().url().endsWith(k)); k ? r.fulfill({ path: map[k], contentType: 'application/javascript' }) : r.abort(); });
    await page.route('https://fonts.**', (r) => r.abort());
    await page.goto('http://localhost:8765/index.html');
    await page.waitForTimeout(1500);
    const tabs = scheme === 'light' ? ['resumen', 'actuador', 'diagramas', 'verificaciones', 'fea', 'planos'] : ['resumen', 'fea'];
    for (const t of tabs) {
      await page.click(`.tab[data-t="${t}"]`); await page.waitForTimeout(300);
      await page.screenshot({ path: `${OUT}/s_${scheme}_${t}.png`, fullPage: true });
    }
    if (scheme === 'light') {
      // downloads
      for (const id of ['bSheetPdf', 'bSheetDxf', 'bMemo']) {
        const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 30000 }), page.click('#' + id)]);
        const p = `${OUT}/dl_${dl.suggestedFilename()}`; await dl.saveAs(p); console.log('downloaded', p);
      }
      const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 30000 }), page.click('[data-file$="Diseno.pdf"]')]);
      console.log('issued', dl.suggestedFilename());
      // change a parameter
      await page.click('.tab[data-t="resumen"]');
      await page.fill('#p_mu', '0.35'); await page.waitForTimeout(1500);
      console.log('verdict mu=0.35:', await page.textContent('#verdict'));
      await page.screenshot({ path: `${OUT}/s_mu035.png` });
      await page.fill('#p_mu', '0.20'); await page.fill('#p_t_bot', '20'); await page.waitForTimeout(1500);
      console.log('chips t_bot=20:', await page.textContent('#chips'));
    }
    // mobile
    if (scheme === 'light') {
      await page.setViewportSize({ width: 400, height: 900 });
      await page.waitForTimeout(400);
      const sw = await page.evaluate(() => document.documentElement.scrollWidth);
      console.log('mobile scrollWidth', sw);
      await page.screenshot({ path: `${OUT}/s_mobile.png` });
    }
    console.log(scheme, 'errors:', errs.slice(0, 10));
    await ctx.close();
  }
  await b.close();
})();
```

### tt300/app/tests/g.js
`tt300/app/tests/g.js` — 32 líneas

```javascript
const { chromium } = require('playwright');
const NM = __dirname + '/node_modules', OUT = '/tmp/claude-0/-home-claude/f880023e-4047-5d94-81d4-3b8b32341d04/scratchpad';
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--headless=new', '--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'], ignoreDefaultArgs: ['--headless=old'] });
  for (const scheme of ['light', 'dark']) {
  const page = await (await b.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: scheme })).newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await page.route('https://cdn.jsdelivr.net/npm/**', (r) => { const u = r.request().url();
    const p = u.includes('OrbitControls') ? NM + '/three/examples/js/controls/OrbitControls.js' : u.includes('three.min') ? NM + '/three/build/three.min.js' : u.includes('jszip') ? NM + '/jszip/dist/jszip.min.js' : u.includes('autotable') ? NM + '/jspdf-autotable/dist/jspdf.plugin.autotable.min.js' : NM + '/jspdf/dist/jspdf.umd.min.js';
    r.fulfill({ path: p, contentType: 'application/javascript' }); });
  await page.route('https://fonts.**', (r) => r.abort());
  await page.goto('http://localhost:8765/index.html'); await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/g_${scheme}.png` });
  if (scheme === 'light') {
    await page.focus('#p_t_bot'); await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}/g_focus_tbot.png` });
    await page.focus('#p_X_cyl'); await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}/g_focus_xcyl.png` });
    // independent scroll
    const r = await page.evaluate(async () => { const a = document.querySelector('aside.params'), m = document.querySelector('main.res'); a.scrollTop = 600; await new Promise(r => setTimeout(r, 100)); return { aside: a.scrollTop, main: m.scrollTop, win: window.scrollY, ah: a.scrollHeight, ach: a.clientHeight, mh: m.scrollHeight, mch: m.clientHeight }; });
    console.log('scroll', JSON.stringify(r));
    await page.mouse.move(900, 600); await page.mouse.wheel(0, 900); await page.waitForTimeout(300);
    const r2 = await page.evaluate(() => ({ aside: document.querySelector('aside.params').scrollTop, main: document.querySelector('main.res').scrollTop, win: window.scrollY }));
    console.log('after wheel on main', JSON.stringify(r2));
    await page.screenshot({ path: `${OUT}/g_scrolled.png` });
    await page.fill('#p_t_top', '40'); await page.fill('#p_N_rib', '16'); await page.waitForTimeout(1800);
    await page.screenshot({ path: `${OUT}/g_changed.png` });
  }
  console.log(scheme, 'errors', errs.filter(e => !e.includes('TUNNEL') && !e.includes('404')));
  }
  await b.close();
})();
```

### tt300/app/tests/z.js
`tt300/app/tests/z.js` — 13 líneas

```javascript
const { chromium } = require('playwright');
const NM = __dirname + '/node_modules';
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--headless=new'], ignoreDefaultArgs: ['--headless=old'] });
  const page = await (await b.newContext({ acceptDownloads: true })).newPage();
  const errs=[]; page.on('pageerror', e=>errs.push(e.message));
  await page.route('https://cdn.jsdelivr.net/npm/**', (r) => { const u=r.request().url(); const p = u.includes('jszip')? NM+'/jszip/dist/jszip.min.js' : u.includes('autotable')? NM+'/jspdf-autotable/dist/jspdf.plugin.autotable.min.js' : NM+'/jspdf/dist/jspdf.umd.min.js'; r.fulfill({path:p, contentType:'application/javascript'}); });
  await page.route('https://fonts.**', (r) => r.abort());
  await page.goto('http://localhost:8765/index.html#planos'); await page.waitForTimeout(1500);
  const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 30000 }), page.click('#bIssuedZip')]);
  await dl.saveAs('/tmp/claude-0/-home-claude/f880023e-4047-5d94-81d4-3b8b32341d04/scratchpad/issued.zip'); console.log('ok', dl.suggestedFilename(), errs);
  await b.close();
})();
```

### tt300/app/tests/verificacion/indep.py
`tt300/app/tests/verificacion/indep.py` — 136 líneas

```python
"""Re-cálculo independiente TT300-B (revisor). Unidades N, mm, MPa salvo indicación."""
import math
g = 9.80665; rho = 7.85e-6
pi = math.pi
# ---- parámetros de diseño (enunciado) ----
W = 300 * g                     # kN
e = 150.0; phid = 1.10
Rd = 1000.0; rh = 150.0; tt = tb = 30.0; gap = 100.0; TD = tt + tb + gap
rings = [300, 550, 735]; tr = 25; Nrib = 12; trib = 20; Rrib = 880
Rb = 940.0; db = 70.0; Nb = 36; dh = 71.0
Ri = 95.0
# ---- masa ----
Ap = pi * (Rd**2 - rh**2) - Nb * pi * (dh / 2)**2
m_top = Ap * tt * rho; m_bot = Ap * tb * rho
m_hub = rho * pi / 4 * (300**2 * TD - 190**2 * 100 - 160**2 * (TD - 100) - (260**2 - 160**2) * 25)
m_ring = sum(2 * pi * r * tr * gap * rho for r in rings)
m_rib = Nrib * trib * gap * (Rrib - rh - 3 * tr) * rho
m_bar = Nb * pi * db**2 / 4 * TD * rho
m_tot = m_top + m_bot + m_hub + m_ring + m_rib + m_bar + 8.1
print(f"masa: top {m_top:.1f} bot {m_bot:.1f} hub {m_hub:.1f} rings {m_ring:.1f} ribs {m_rib:.1f} bars {m_bar:.1f} total {m_tot:.1f} kg")
Wd = m_tot * g / 1000
N = W + Wd; ND = phid * W + Wd
r_u = 2 / 3 * (Rd**3 - Ri**3) / (Rd**2 - Ri**2) / 1000
th = pi / Nb
a = Rb * math.cos(th)
useful = 2 * Rb * math.sin(th); sreq = 36 + useful
Delta = 1085 - a; Kg = 1 + 2 * 0.15 * Delta / 250; K = Kg / 0.95
A = pi * 90**2 / 4; Fmax = A * 700 / 10 / 1000; Falarm = A * 600 / 10 / 1000
Tpiv = 0.20 * 0.05 * W * 0.075
print(f"W {W:.3f} Wd {Wd:.3f} N {N:.3f} ND {ND:.3f} r_u {r_u:.5f} a {a:.3f} useful {useful:.3f} sreq {sreq:.3f}")
print(f"Delta {Delta:.3f} Kg {Kg:.5f} K {K:.5f} A {A:.2f} Fmax {Fmax:.3f} Falarm {Falarm:.3f} Tpiv {Tpiv:.4f}")
print(f"Ybrk {Rb*math.sin(th)+250+450+36:.2f}")

def case(mu, r):
    Tf = mu * N * r; T = Tf + Tpiv; Fb = T / (2 * a / 1000); Fc = K * Fb
    return dict(Tf=Tf, T=T, Fb=Fb, Fc=Fc, p=Fc * 1e3 / A * 10, FS=Fmax / Fc)
cases = [("nom", 0.15, r_u), ("dis", 0.20, 0.80), ("con", 0.25, 0.80), ("dry", 0.50, r_u),
         ("dis r=0.94", 0.20, 0.94), ("dis r=1.00", 0.20, 1.00), ("con r=1.00", 0.25, 1.00)]
for k, mu, r in cases:
    c = case(mu, r)
    print(f"{k:12s} mu {mu} r {r:.4f} Tf {c['Tf']:.2f} T {c['T']:.2f} Fb {c['Fb']:.2f} Fc {c['Fc']:.2f} p {c['p']:.1f} FS {c['FS']:.3f}")
def mumax(r, p):
    return ((A * p / 10 / 1000) / K * (2 * a / 1000) - Tpiv) / (N * r)
for r in (r_u, 0.8, 0.94, 1.0):
    print(f"mumax r {r:.3f}: 700 bar {mumax(r,700):.4f}  600 bar {mumax(r,600):.4f}")
d = case(0.2, 0.8); a2 = 2 * a / 1000
bd = [d['Tf'] / a2, Tpiv / a2, d['Fb'] * (Kg - 1), d['Fc'] - d['Fb'] * Kg]
print("breakdown", [round(x, 3) for x in bd], "sum", round(sum(bd), 3))
# exact guide-friction alternative: Lg = 2/3 Ls (linear distribution over 300 mm shoe)
for Lg in (250, 200, 150):
    Kx = (1 + 2 * 0.15 * Delta / Lg) / 0.95
    print(f"Lg {Lg}: K {Kx:.4f} Fc_dis {Kx*d['Fb']:.1f} kN  Rg(Fmax) {Fmax*Delta/Lg:.1f} kN")
# ---- contacto ----
Ac = pi * (Rd**2 - Ri**2)
q_avg = ND * 1e3 / Ac; q_max = q_avg * (1 + 4 * e * Rd / (Rd**2 + Ri**2))
q_top = phid * W * 1e3 / (pi * 800**2)
print(f"Ac {Ac:.0f} q_avg {q_avg:.4f} q_max {q_max:.4f} q_top {q_top:.4f}")
# fuerza lateral por fricción con presión lineal (excentricidad e)
Ix = pi * (Rd**4 - Ri**4) / 4
k_lin = N * 1e3 * e / Ix            # q = q0 + k x (N/mm^3)
for mu in (0.15, 0.2, 0.25, 0.5):
    Flat = mu * k_lin * pi * (Rd**3 - Ri**3) / 3 / 1e3
    print(f"H friccion mu {mu}: {Flat:.1f} kN = {Flat/W*100:.2f}% W")
# ---- suelo ----
Wtot = W + (m_tot + 3070) * g / 1000
gavg = Wtot * 1e3 / (2400 * 2000); gmax = gavg * (1 + 6 * e / 2000)
gbi = gavg * (1 + 6 * e * math.hypot(1 / 2400, 1 / 2000))
print(f"Wtot {Wtot:.2f} g_avg {gavg:.4f} g_max(uniax) {gmax:.4f} g_max(biax, peor ángulo) {gbi:.4f}")
gcirc = Wtot * 1e3 / (pi * Rd**2); print(f"presión bajo huella del disco Ø2000 (sin reparto de placa): {gcirc:.3f} med, {gcirc*(1+4*e/Rd):.3f} máx")
# ---- verificaciones ----
F = Fmax; Fy = 345
print("\n--- verifs ---")
ov = 200; lever = 130
Mov = q_max * ov**2 / 2; print(f"global voladizo σ {Mov/(30*lever):.3f}")
L = 100; c = 90
Mss = F / 4 * (L - c / 2) / 1e3; Mfe = F * (3 * L * L - c * c) / (24 * L) / 1e3
Z = db**3 / 6; S = pi * db**3 / 32
Mn_tool = Fy * Z / 1.67 / 1e6; Mn_F11 = min(Fy * Z, 1.6 * Fy * S) / 1.67 / 1e6
print(f"barra Mss {Mss:.4f} Mfe {Mfe:.4f} Mn/Ω tool {Mn_tool:.3f} F11 (cap 1.6S) {Mn_F11:.3f}  Z/S {Z/S:.3f}")
tau = 4 * (F / 2) * 1e3 / (3 * pi * db**2 / 4); print(f"tau barra {tau:.2f}")
Ew = 12
tv = F / 2 * 1e3 / (pi * db * Ew); tm = Mfe * 1e6 / (pi * (db / 2)**2 * Ew)
print(f"sold tv {tv:.2f} tm {tm:.2f} res {math.hypot(tv,tm):.2f} cap {0.6*490/2}")
print(f"aplast agujero {(F/2)*1e3/(30*db):.2f}")
# alternativas: luz entre planos medios (130) y entre caras exteriores (160)
for Ls in (100, 130, 160):
    Ms = F / 4 * (Ls - c / 2) / 1e3; Mf = F * (3 * Ls * Ls - c * c) / (24 * Ls) / 1e3
    tmx = Mf * 1e6 / (pi * (db / 2)**2 * Ew)
    print(f" L={Ls}: Mss {Ms:.2f} (FU {Ms/Mn_F11:.2f}) Mfe {Mf:.2f} sold res {math.hypot(tv,tmx):.1f} FU {math.hypot(tv,tmx)/147:.2f}")
lev = 1020 - a
sp = F * lev * 1e3 / (90 * 85**2 / 6); print(f"trinquete lev {lev:.3f} σ {sp:.2f}")
Rg = F * Delta / 250; print(f"guia Rg {Rg:.3f} σb {Rg*1e3/(10*150):.2f} Mg {Rg*15/1e3:.4f} Mng {Fy*150*40**2/4/1.67/1e6:.3f}")
print(f"mejilla σ {F*80*1e3/(2*40*280**2/6):.3f}")
Mpin = F / 2 * (20 + 5 + 17.5) / 1e3
print(f"pasador M {Mpin:.4f} σ {Mpin*1e6/(pi*70**3/32):.2f} τ {(F/2)*1e3/(pi*70**2/4):.2f} adm τ {650/(2*math.sqrt(3)):.2f}")
print(f"pasador aplast. mejilla {(F/2)*1e3/(40*70):.1f} ojal {F*1e3/(70*70):.1f}")
H = 0.055 * W
print(f"pivote H {H:.3f} p {H*1e3/(150*100):.3f} σ {H*50*1e3/(pi*150**3/32):.3f}")
I = pi * 63**4 / 64; Pcr = pi**2 * 2e5 * I / 650**2 / 1e3
print(f"pandeo Pcr {Pcr:.1f} Pcr/3 {Pcr/3:.2f}")
# reacción en boca del carro del trinquete (modelo de apoyos del FEA)
Xs = a - 905; x1 = 115 + 12.5; x2 = 245 - 12.5
R2 = F * (x1 - Xs) / (x2 - x1); R1 = F + R2
print(f"trinquete: reacción boca {R1:.1f} kN, labio post {R2:.1f} kN; aplast. boca (25x90) {R1*1e3/(25*90):.0f} MPa")
# Hertz asiento R36 / barra r35
Rs = 1 / (1 / 35 - 1 / 36); q = F * 1e3 / 90; Es = 2e5 / (2 * (1 - 0.09))
bH = math.sqrt(4 * q * Rs / (pi * Es)); p0 = 2 * q / (pi * bH)
print(f"Hertz conforme: b {bH:.2f} mm p0 {p0:.0f} MPa")
print(f"desplazamiento radial relativo barra/asiento en carrera: {Rb-a:.3f} mm vs holgura radial {36-35} mm")

# ---- flexión global axisimétrica del cajón (placa sándwich, borde libre) ----
import numpy as np
n = 20001; r = np.linspace(1e-6, Rd, n)
qb = ND * 1e3 / (pi * Rd**2)        # reparto uniforme inferior (aprox. sin agujero central)
p = np.where(r <= 800, -q_top, 0.0) + qb    # neto hacia arriba
# corte por unidad de longitud Q(r) = (1/r)∫ p ρ dρ
cum = np.concatenate([[0], np.cumsum(0.5 * (p[1:] * r[1:] + p[:-1] * r[:-1]) * np.diff(r))])
Q = cum / r
print(f"\nGlobal: desequilibrio Q(R)·2πR = {Q[-1]*2*pi*Rd/1e3:.1f} kN (≈0)")
nu = 0.3
# ψ'' + ψ'/r − ψ/r² = Q/D  => (1/r (rψ)')' = Q/D ; trabajar con D=1 (momentos independientes de D)
Iq = np.concatenate([[0], np.cumsum(0.5 * (Q[1:] + Q[:-1]) * np.diff(r))])  # ∫Q dr
J = np.concatenate([[0], np.cumsum(0.5 * (Iq[1:] * r[1:] + Iq[:-1] * r[:-1]) * np.diff(r))])
psi_p = J / r
dpsi_p = np.gradient(psi_p, r)
# ψ = ψp + C r ; Mr = ψ' + ν ψ/r → Mr(R) = dψp(R) + ν ψp(R)/R + C(1+ν) = 0
C = -(dpsi_p[-1] + nu * psi_p[-1] / Rd) / (1 + nu)
psi = psi_p + C * r; dpsi = dpsi_p + C
Mr = dpsi + nu * psi / r; Mt = psi / r + nu * dpsi
i = slice(5, n - 5)
Mmax = max(abs(Mr[i]).max(), abs(Mt[i]).max())
print(f"Mr centro {Mr[50]:.0f}  Mr(800) {Mr[np.searchsorted(r,800)]:.0f}  Mθ(R) {Mt[-6]:.0f}  |M|max {Mmax:.0f} N·mm/mm")
print(f"σ membrana global = M/(t·130) = {Mmax/(30*130):.2f} MPa (herramienta 8,55)")
for rr in (735, 800, 880):
    k = np.searchsorted(r, rr); V = abs(Q[k]) * 2 * pi * rr
    print(f" corte total en r={rr}: {V/1e3:.0f} kN → τ nervios 12x20x100 = {V/(12*20*100):.1f} MPa")
```

### tt300/app/tests/verificacion/refine.js
`tt300/app/tests/verificacion/refine.js` — 23 líneas

```javascript
global.FEA = require('./fea_mod.js');
global.performance = global.performance || require('perf_hooks').performance;
const C = require('./calc_mod.js');
const P = C.defaults();
const deg = Math.PI / 180;
function nodalAvgVM(f) {
  // promedio nodal de momentos (centro de elemento) -> σvm nodal suavizado
  const m = f.model, nn = m.nodes.length, S = Array.from({ length: nn }, () => [0, 0, 0, 0]);
  f.res.el.forEach((e, i) => m.elems[i].forEach((k) => { for (let c = 0; c < 3; c++) S[k][c] += e.M[c]; S[k][3]++; }));
  let mx = 0, at = null; const k6 = 6 / (m.t * m.t);
  S.forEach((s, k) => { if (!s[3]) return; const sx = s[0] / s[3] * k6, sy = s[1] / s[3] * k6, t = s[2] / s[3] * k6;
    const vm = Math.sqrt(sx * sx - sx * sy + sy * sy + 3 * t * t); if (vm > mx) { mx = vm; at = m.pol[k]; } });
  return [mx, at];
}
for (const which of ['bot', 'top']) {
  console.log('==', which);
  for (const [hr, dth] of [[null, null], [10, 0.625 * deg], [5, 0.3125 * deg], [3, 0.2 * deg]]) {
    const f = C.runDisc(P, which, hr, dth);
    let vn = 0; f.res.el.forEach((e) => { vn = Math.max(vn, e.vmNode); });
    const [va, at] = nodalAvgVM(f);
    console.log(`hr ${hr || 'def'} dθ ${dth ? (dth / deg).toFixed(3) : 'def'} nodes ${f.model.nodes.length} vmC ${f.vmC.toFixed(2)} vmGauss ${f.vmMax.toFixed(2)} at r=${f.maxAt[0].toFixed(0)} θ=${f.maxAt[1].toFixed(2)} vmCorner ${vn.toFixed(2)} vmNodalAvg ${va.toFixed(2)} at r=${at[0].toFixed(0)} θ=${(at[1] / deg).toFixed(2)} w ${f.wMax.toFixed(4)} rings ${f.ringLine.map((v) => v.toFixed(0))} bars ${f.barF.map((v) => v.toFixed(1))} rib ${f.ribF.toFixed(1)} hub ${f.hubF.toFixed(1)} F ${f.Fapp.toFixed(1)} R ${f.Rsum.toFixed(1)} ms ${f.ms.toFixed(0)}`);
  }
}
```

### tt300/app/tests/verificacion/signed.js
`tt300/app/tests/verificacion/signed.js` — 9 líneas

```javascript
global.FEA = require('./fea_mod.js');
const C = require('./calc_mod.js'); const P = C.defaults(); const deg=Math.PI/180;
for (const [hr,dth] of [[null,null],[10,0.625*deg],[5,0.3125*deg]]) {
  const f = C.runDisc(P,'bot',hr,dth), m=f.model, r=f.res.reac;
  const s=(g)=>g.reduce((a,k)=>a+r[k],0)/1e3, ab=(g)=>g.reduce((a,k)=>a+Math.abs(r[k]),0)/1e3;
  const neg=(g)=>g.filter(k=>Math.sign(r[k])!==Math.sign(s(g))).length;
  console.log(hr, 'bars signed', m.groups.bar.map(s).map(v=>v.toFixed(1)), 'abs', m.groups.bar.map(ab).map(v=>v.toFixed(1)), 'nodes', m.groups.bar.map(g=>g.length), 'oppSign', m.groups.bar.map(neg),
   'rings signed kN', m.groups.ring.map(s).map(v=>v.toFixed(1)), 'abs', m.groups.ring.map(ab).map(v=>v.toFixed(1)), 'rib', s(m.groups.rib).toFixed(1), ab(m.groups.rib).toFixed(1), 'hub', s(m.groups.hub).toFixed(1));
}
```

### tt300/app/tests/verificacion/bench.js
`tt300/app/tests/verificacion/bench.js` — 39 líneas

```javascript
const FEA = require('./fea_mod.js');
const E=2e5, nu=0.3;
// 1) placa cuadrada empotrada a=1000 t=10 q=0.01: w0=0.00126 q a^4/D, M borde=-0.0513 q a^2, M centro 0.0231 q a^2
for (const n of [10,20,40]) {
  const a=1000,t=10,q=0.01,nodes=[],elems=[]; const id=(i,j)=>i*(n+1)+j;
  for(let i=0;i<=n;i++)for(let j=0;j<=n;j++)nodes.push([i*a/n,j*a/n]);
  for(let i=0;i<n;i++)for(let j=0;j<n;j++)elems.push([id(i,j),id(i+1,j),id(i+1,j+1),id(i,j+1)]);
  const clamp=[];for(let i=0;i<=n;i++)for(let j=0;j<=n;j++)if(i==0||j==0||i==n||j==n)clamp.push(id(i,j));
  const r=FEA.plate({nodes,elems,t,E,nu,q:new Float64Array(elems.length).fill(q),wFix:[],clamp});
  const D=E*t**3/(12*(1-nu*nu));
  const Mx=r.el.map(e=>e.M[0]); 
  console.log(`empotrada n=${n}: w ${(r.w[id(n/2,n/2)]/(q*a**4/D)).toExponential(4)} (teo 1.26e-3) Mmin(centro elem) ${(Math.min(...Mx)/(q*a*a)).toFixed(4)} (teo -0.0513 en borde) Mmax ${(Math.max(...Mx)/(q*a*a)).toFixed(4)} (teo 0.0231)`);
}
// 2) anular sector 30° b=150 empotrado, a=400 simplemente apoyado, t=30, q=1, con simetría β·n=0 en bordes del sector
const b=150,a=400,t=30,q=1,D=E*t**3/(12*(1-nu*nu)),al=Math.PI/6;
// solución Kirchhoff axisimétrica: w = q r^4/(64D) + A + B r^2 + C ln r + Ee r^2 ln r
function solve(){ const f=[(r)=>[1,r*r,Math.log(r),r*r*Math.log(r)],(r)=>[0,2*r,1/r,2*r*Math.log(r)+r],(r)=>[0,2,-1/(r*r),2*Math.log(r)+3]];
 const wp=(r)=>q*r**4/(64*D), wp1=(r)=>q*r**3/(16*D), wp2=(r)=>3*q*r*r/(16*D);
 const Mrow=(r)=>f[2](r).map((v,i)=>v+nu*f[1](r)[i]/r);
 const Ar=[f[0](b),f[1](b),f[0](a),Mrow(a)], rhs=[-wp(b),-wp1(b),-wp(a),-(wp2(a)+nu*wp1(a)/a)];
 // gauss
 const M=Ar.map((row,i)=>[...row,rhs[i]]); for(let i=0;i<4;i++){let p=i;for(let k=i+1;k<4;k++)if(Math.abs(M[k][i])>Math.abs(M[p][i]))p=k;[M[i],M[p]]=[M[p],M[i]];for(let k=0;k<4;k++)if(k!==i){const c=M[k][i]/M[i][i];for(let j=i;j<5;j++)M[k][j]-=c*M[i][j];}}
 const c=M.map((r,i)=>r[4]/r[i]); const w=(r)=>wp(r)+c[0]+c[1]*r*r+c[2]*Math.log(r)+c[3]*r*r*Math.log(r);
 const w1=(r)=>wp1(r)+f[1](r).reduce((s,v,i)=>s+v*c[i],0), w2=(r)=>wp2(r)+f[2](r).reduce((s,v,i)=>s+v*c[i],0);
 return {w,Mr:(r)=>-D*(w2(r)+nu*w1(r)/r),Mt:(r)=>-D*(w1(r)/r+nu*w2(r))}; }
const S=solve(); let wmax=0,rw=0; for(let r=b;r<=a;r+=0.5){if(Math.abs(S.w(r))>wmax){wmax=Math.abs(S.w(r));rw=r;}}
console.log(`anular Kirchhoff: Mr(b) ${S.Mr(b).toFixed(1)} N·mm/mm σ ${(6*Math.abs(S.Mr(b))/t/t).toFixed(2)} MPa; wmax ${wmax.toFixed(5)} at r ${rw}`);
for (const [nr,nt] of [[12,8],[25,24],[50,48]]) {
  const nodes=[],elems=[],rs=[],ts=[]; for(let i=0;i<=nr;i++)rs.push(b+(a-b)*i/nr); for(let j=0;j<=nt;j++)ts.push(al*j/nt);
  const id=(i,j)=>i*(nt+1)+j; rs.forEach(r=>ts.forEach(th=>nodes.push([r*Math.cos(th),r*Math.sin(th)])));
  for(let i=0;i<nr;i++)for(let j=0;j<nt;j++)elems.push([id(i,j),id(i+1,j),id(i+1,j+1),id(i,j+1)]);
  const clamp=[],wFix=[],betaN=[]; for(let j=0;j<=nt;j++){clamp.push(id(0,j));wFix.push(id(nr,j));}
  for(let i=1;i<=nr;i++){betaN.push([id(i,0),0,1]);betaN.push([id(i,nt),-Math.sin(al),Math.cos(al)]);}
  const r=FEA.plate({nodes,elems,t,E,nu,q:new Float64Array(elems.length).fill(q),wFix,clamp,betaN});
  let vg=0,vn=0; r.el.forEach(e=>{vg=Math.max(vg,e.vmGauss);vn=Math.max(vn,e.vmNode);}); let wm=0; for(const w of r.w)wm=Math.max(wm,Math.abs(w));
  // σvm teórico en r=b: σr=6Mr/t², σθ=ν σr (empotrado)
  const sr=6*S.Mr(b)/t/t, vmT=Math.abs(sr)*Math.sqrt(1-nu+nu*nu);
  console.log(`FE ${nr}x${nt}: vmGauss ${vg.toFixed(2)} vmCorner ${vn.toFixed(2)} (teo σvm borde ${vmT.toFixed(2)}) wmax ${wm.toFixed(5)} (Kirchhoff ${wmax.toFixed(5)}) F ${r.Fapplied.toFixed(0)} R ${(-r.Rsum).toFixed(0)}`);
}
```

### tt300/app/tests/verificacion/pawl.js
`tt300/app/tests/verificacion/pawl.js` — 20 líneas

```javascript
global.FEA = require('./fea_mod.js');
const C = require('./calc_mod.js');
for (const h of [5, 2.5, 1.25]) {
  const P = C.defaults(); P._h = h; const R = C.compute(P);
  const pw = C.runPawl(P, R);
  // localizar vmFar y perfil σx en secciones
  let far = 0, fat = null;
  pw.res.el.forEach((e, i) => { const [cx, cy] = pw.cent[i];
    const nearLoad = Math.hypot(cx - pw.Xs, cy - pw.Ys) < pw.Rs + 4 * h;
    const nearSup = pw.sup.some((k) => Math.hypot(cx - pw.nodes[k][0], cy - pw.nodes[k][1]) < 4 * h);
    if (!nearLoad && !nearSup && e.vm > far) { far = e.vm; fat = [cx, cy]; } });
  let top = pw.res.el.map((e,i)=>[e.vm,...pw.cent[i]]).sort((a,b)=>b[0]-a[0]).slice(0,3).map(a=>a.map(v=>v.toFixed(1)).join('@'));
  // sección justo antes de la boca: σx en fibra superior e inferior, y momento integrado
  const xs = pw.Xm - h/2; let M=0, Nx=0; const col = pw.res.el.map((e,i)=>[e.sx,...pw.cent[i]]).filter(a=>Math.abs(a[1]-xs)<h/2+1e-6);
  col.forEach(a=>{ M += a[0]*(a[2]-pw.b/2)*h*P.pawl_h; Nx += a[0]*h*P.pawl_h; });
  console.log(`h=${h}: vmMax ${pw.vmMax.toFixed(0)} mouth ${pw.vmMouth.toFixed(0)} far ${pw.vmFar.toFixed(0)} @(${fat.map(v=>v.toFixed(1))}) beam ${pw.beam.toFixed(0)} dmax ${pw.dmax.toFixed(3)} top3 ${top.join(' | ')}; sección x=${xs.toFixed(2)}: M_int ${(M/1e6).toFixed(2)} kN·m (F·lev ${(R.Fmax*(xs-pw.Xs)/1e3).toFixed(2)}), σx sup ${Math.max(...col.map(a=>a[0])).toFixed(0)} inf ${Math.min(...col.map(a=>a[0])).toFixed(0)}`);
  // reacciones en apoyos
  const rs = pw.res.reac; let Rm=0, Rb=0; rs.forEach(([k,d,f])=>{ if(d!==1) return; if(pw.nodes[k][1]<1) Rm+=f; else Rb+=f; });
  console.log(`   reacción boca (inf) ${(Rm/1e3).toFixed(1)} kN, labio posterior (sup) ${(Rb/1e3).toFixed(1)} kN`);
}
```

## Apéndice E. Informe completo de la revisión independiente

# TT300-B, tornamesa hidráulica 300 tf: verificación independiente de la herramienta paramétrica

**Alcance:** `app/calc.js` (compute, verifs, discModel/runDisc, runPawl), `app/fea.js` (Cholesky en banda, MITC4, Q4), contraste con `calc.py`.
**Método:** re-cálculo propio en Python (`indep.py`), estudio de malla y benchmarks adicionales en JS sobre copias parametrizadas (`calc_mod.js`, `fea_mod.js`, `refine.js`, `signed.js`, `bench.js`, `pawl.js`). Todos los scripts están en `/tmp/claude-0/-home-claude/f880023e-4047-5d94-81d4-3b8b32341d04/scratchpad/`. No se modificó ningún archivo bajo `/home/claude/tt300`.

---

#### 0. Resumen

- **Aritmética:** todos los valores de la corrida por defecto coinciden con mi re-cálculo. La diferencia es menor que 0,01 % en todos los casos. No hay errores de unidades.
- **Hallazgos principales.** Son de modelo e hipótesis, no de aritmética:
  - **Crítico 1.** La barra 4f y su soldadura se modelan con una luz de 100 mm, como si los apoyos estuvieran en las caras interiores. Si la soldadura de bisel está en las caras exteriores, la luz real es 160 mm. Con la holgura de 0,5 mm del agujero, la barra no apoya en el agujero en régimen elástico. En ese caso:
    - soldadura: FU = 1,31 (la herramienta da 0,83);
    - flexión de la barra rotulada: FU = 1,15 (la herramienta da 0,52).
  - **Crítico 2.** Hay incompatibilidad cinemática entre el asiento del trinquete y la trayectoria circular de la barra. El desplazamiento radial relativo es 3,58 mm y la holgura del asiento es 1,0 mm. La herramienta no lo verifica.
  - **Crítico 3.** La carrera requerida es 199,85 mm y la disponible 200 mm. El margen es 0,15 mm.
- **Hallazgos mayores:**
  - El r_eff = 0,80 m no está justificado. En la cota r = 1,0 m:
    - con μ = 0,20: FS = 1,13 y p = 619 bar, sobre la alarma;
    - con μ = 0,25: FS = 0,91, es decir, el disco no gira.
  - La fórmula de flexión global del cajón subestima unas 2,7 veces: 8,6 MPa contra 23 MPa axisimétrico.
  - Faltan verificaciones: corte en nervios, soldaduras de almas, anclaje de la guía y su volcamiento, apoyo trinquete/carro (reacción ≈ 1,8 F en el labio), fatiga, cargas laterales y sísmicas.
  - La presión sobre el suelo sale 9 % más alta con excentricidad biaxial (FU 0,99).
- **FEA:** la formulación MITC4 es correcta y está en equilibrio. Las tensiones de placa convergen alrededor de 12 % por sobre el valor por defecto: unos 28–29 MPa contra 25,6 MPa. El margen sigue siendo amplio. Las fuerzas en barras se calculan con la suma de |R|: dependen de la malla y sobrestiman 15 %.

---

#### 1. Re-derivación de la corrida por defecto

| Magnitud | Herramienta | Revisor | Δ % |
|---|---|---|---|
| Masa disco (top/bot/hub/almas/nervios/barras/buje) [kg] | 689,63/689,63/50,58/195,44/123,40/174,01/8,1 | 689,6/689,6/50,6/195,4/123,4/174,0/8,1 | 0,00 |
| Masa total [kg] | 1930,80 | 1930,8 | 0,00 |
| W [kN] | 2941,995 | 2941,995 | 0,00 |
| N = W + W_d [kN] | 2960,930 | 2960,930 | 0,00 |
| N_D = φd·W + W_d [kN] | 3255,129 | 3255,129 | 0,00 |
| r_u (presión uniforme) [m] | 0,67216 | 0,67216 | 0,00 |
| a = 940·cos5° [mm] | 936,423 | 936,423 | 0,00 |
| Δ = 1085 − a [mm] | 148,577 | 148,577 | 0,00 |
| K_guía / K | 1,17829 / 1,24031 | 1,17829 / 1,24031 | 0,00 |
| A émbolo [mm²] / F_max 700 bar [kN] | 6361,73 / 445,321 | 6361,73 / 445,321 | 0,00 |
| F_alarma 600 bar [kN] | 381,704 | 381,704 | 0,00 |
| T_piv [kN·m] | 2,2065 | 2,2065 | 0,00 |
| Nominal μ 0,15, r_u: T / F_b / F_c / p / FS | 300,74 / 160,58 / 199,17 / 313,1 / 2,236 | ídem | 0,00 |
| Diseño μ 0,20, r 0,80 | 475,96 / 254,13 / 315,21 / 495,5 / 1,413 | ídem | 0,00 |
| Contaminado μ 0,25, r 0,80 | 594,39 / 317,37 / 393,64 / 618,8 / 1,131 | ídem | 0,00 |
| Seco μ 0,50, r_u | 997,32 / 532,52 / 660,48 / 1038,2 / 0,674 | ídem | 0,00 |
| μ_max a 700 bar (r_u / 0,80 / 0,94) | 0,3368 / 0,2829 / 0,2408 | 0,3368 / 0,2829 / 0,2408 | 0,00 |
| μ_max a 600 bar, r 0,80 | 0,2424 | 0,2424 | 0,00 |
| Carrera requerida [mm] | 199,853 | 199,853 | 0,00 |
| Y_brk [mm] | 817,93 | 817,93 (plano: 818) | 0,01 |
| Desglose F_c (interfaz/pivote/guía/sellos) [kN] | 252,96 / 1,18 / 45,31 / 15,76 | 252,96 / 1,18 / 45,31 / 15,76 (Σ 315,21) | 0,00 |
| Curva de carrera F_c (s = 36 / centro) [kN] | 315,21 / 312,86 | 315,21 / 312,86 | 0,00 |
| q_avg / q_max contacto [MPa] | 1,0456 / 1,6673 | 1,0456 / 1,6673 | 0,00 |
| q_top (φd·W / Ø1600) [MPa] | 1,6096 | 1,6096 | 0,00 |
| σ suelo medio / máx. [MPa] | 0,6231 / 0,9035 | 0,6231 / 0,9035 (biaxial: **0,9881**) | 0,00 (+9,4 %) |

**Verificaciones de elementos (verifs).** Todas reproducidas exactamente:

| Elemento | Valor | Capacidad | FU |
|---|---|---|---|
| Barra 4f, flexión | M_ss 6,123 kN·m | 11,81 | 0,52 |
| Barra 4f, corte | τ 77,14 MPa | 138 | 0,56 |
| Barra 4f, soldadura | τ_V 84,37, τ_M 87,99, resultante 121,9 MPa | 147 | 0,83 |
| Barra 4f, aplastamiento | 106,0 MPa | 310,5 | 0,34 |
| Trinquete (vigas) | 343,4 MPa | 400 | 0,86 |
| Guía, aplastamiento | R_g 264,66 kN, σ 176,4 MPa | 310,5 | 0,57 |
| Guía, flexión | M 3,97 kN·m | 12,40 | 0,32 |
| Mejilla | 34,08 MPa | 207 | 0,16 |
| Pasador, flexión | M 9,463 kN·m, σ 281,0 MPa | 325 | 0,86 |
| Pasador, corte | 57,86 MPa | 187,6 | 0,31 |
| Buje | 10,79 MPa | 30 | 0,36 |
| Pivote | 24,42 MPa | 325 | 0,08 |
| Vástago, P_cr/3 | 445,3 kN | 1204,2 kN | 0,37 |
| Flexión global del cajón | 8,55 MPa | 207 | 0,04 |

**Contraste con `calc.py` (versión previa):**
- calc.py usa A = 445e3/70 = 6357 mm² y la herramienta 6361,7 mm². La diferencia en F_max es −0,07 %.
- calc.py usa W_d = 1922 kg y la herramienta 1930,8 kg. La diferencia es −0,46 %, despreciable en N.
- En pandeo, calc.py usa Ø90 (el émbolo) y obtiene P_cr/3 = 5016 kN. calc.js usa el vástago Ø63 y obtiene 1204 kN, que es lo correcto. calc.py estaba errado del lado inseguro.
- calc.py fija para las planchas 67 y 70 MPa. Ese valor corresponde a una franja simplemente apoyada (q·b²/8). El FEA da 25–29 MPa. La diferencia es de concepto, no un error.

---

#### 2. Hallazgos clasificados

### CRÍTICO

**C1. Barra 4f: luz y apoyos del modelo de flexión y soldadura** (`calc.js › verifs`, bloque "barra 4f")
- **Problema:** se usa L = gap = 100 mm, con rótulas o empotramientos en las caras interiores de las planchas. La barra pasa por agujeros Ø71, con 0,5 mm de holgura radial, y se suelda con bisel 15 mm. Si ese bisel está en las caras exteriores, que es lo habitual en barras pasantes:
  - el apoyo real está en la cara exterior, y la luz es TD = 160 mm;
  - la deflexión elástica de la barra en la cara interior es de unos 0,05–0,1 mm, menos que la holgura de 0,5 mm, así que el agujero no apoya;
  - con c = 90 mm, la luz de corte supuesta es de solo 5 mm por lado. La herramienta trata un pasador corto como si fuera una viga.
- **Efecto:** FU con F = 445 kN y la capacidad corregida según m1:

| Hipótesis de luz | Flexión rotulada (M_ss) | Soldadura empotrada (τ resultante) |
|---|---|---|
| L = 100 (herramienta) | 6,12 kN·m → FU 0,55 | 121,9 MPa → FU 0,83 |
| L = 130 (planos medios) | 9,46 kN·m → FU 0,85 | 156,4 MPa → **FU 1,06** |
| L = 160 (caras exteriores) | 12,80 kN·m → **FU 1,15** | 192,0 MPa → **FU 1,31** |

- Un mecanismo plástico (rótulas en extremos y centro) daría FU ≈ 0,77. Ese argumento depende de la ductilidad de una soldadura PJP, que AISC no reconoce para redistribución.
- **Corrección:**
  - Confirmar en planos dónde está la soldadura.
  - Si está en las caras exteriores, hay tres opciones:
    - soldar también las caras interiores (antes de cerrar el cajón);
    - especificar un ajuste escariado (holgura ≤ 0,1 mm) y documentar el apoyo en el agujero;
    - aumentar la garganta (CJP o bisel mayor).
  - Parametrizar la luz del modelo como L = gap + 2·t_eff, según la ubicación real del apoyo.

**C2. Compatibilidad cinemática asiento–barra no verificada** (`calc.js › compute` y `runPawl`)
- **Problema:** el carro se mueve en línea recta (Y) y la barra describe un arco. La posición x de la barra varía entre R·cos5° = 936,42 mm y 940 mm: el desplazamiento radial relativo es R(1 − cos π/N) = 3,58 mm. El asiento es R36 y la barra r35, con su centro en x = a (`Xs = R.a − pawl_tip`). La holgura radial es de 1,0 mm, así que queda una interferencia de unos 2,6 mm a media carrera.
- **Efecto:**
  - Si el trinquete no tiene libertad radial, hay trabado o contacto de borde.
  - La fuerza de contacto aparece con una componente F_x que no está modelada. Esa componente carga la guía, el carro y el pivote.
  - Cambian la flexión y la presión de contacto del trinquete: el contacto Hertz centrado da p₀ = 371 MPa, pero el contacto de borde es muy superior.
- **Corrección:** hay tres alternativas:
  - asiento ranurado radialmente, con longitud de ranura ≥ 2·R(1 − cos π/N) más tolerancia;
  - libertad radial del trinquete en el carro;
  - centrar el asiento en R(1 + cos π/N)/2, lo que reduce la interferencia a ±1,8 mm (todavía insuficiente con 1 mm de holgura).

  En cualquier caso, agregar la verificación `R_bar·(1 − cos θ) ≤ holgura_x` a verifs.

**C3. Carrera sin margen** (`verifs`, fila "Carrera requerida")
- **Problema:** s_req = 36 + 2·940·sin5° = 199,85 mm contra 200 mm. El margen es 0,15 mm (FU 0,999) y la fila se marca como `pass`.
- **Efecto:** las tolerancias pueden impedir que el trinquete caiga detrás de la barra siguiente. Las fuentes son:
  - la posición angular de las 36 barras (±0,5 mm típico);
  - las holguras de los pasadores;
  - la tolerancia de carrera del cilindro;
  - la holgura del asiento.

  El resultado sería que la punta o el chaflán del trinquete apoye sobre la barra, con una carga no considerada en el modelo.
- **Corrección:** subir la carrera a unos 210–220 mm o reducir el recorrido libre de forma justificada. Agregar una verificación con margen mínimo explícito (por ejemplo ≥ 5 mm) en vez de FU ≤ 1.

### MAYOR

**M1. r_eff = 0,80 m no es cota superior** (`PARAM_GROUPS.friccion`, `compute › cases`)
- **Problema:**
  - Con presión lineal (excentricidad e), el torque de fricción no depende de e, porque ∫q·r·dA conserva r_u = 0,672.
  - r_eff = 0,80 es un juicio por planitud o "carga al borde", y no se deriva del FEA: la presión inferior es un dato del modelo, no un resultado.
  - La deformación elástica del cajón (global ≈ 0,4–0,5 mm) concentra el contacto hacia el centro, no hacia el borde.
  - El borde solo domina por imperfecciones. Lo mismo ocurre si los cordones de las 36 barras en la cara inferior no se esmerilan a ras: en ese caso r ≈ 0,94.
- **Efecto:**

| Caso | F_c [kN] | p [bar] | FS |
|---|---|---|---|
| μ 0,20, r 0,94 | 370,1 | 582 | 1,20 |
| μ 0,20, r 1,00 | 393,6 | 619 (> alarma) | 1,13 |
| μ 0,25, r 1,00 | 491,7 | 773 | **0,91 (no gira)** |

  μ_max con r = 1,0 es 0,226 a 700 bar y 0,194 a 600 bar.
- **Corrección:**
  - Especificar planitud de las caras de contacto (disco y placa base) y esmerilado a ras de las soldaduras en la cara inferior.
  - Calcular la distribución de contacto con un modelo unilateral o Winkler del conjunto disco–placa base–grout, o adoptar r = 0,94–1,0 en el caso de diseño.

**M2. Flexión global del cajón mal modelada; faltan corte de nervios y soldaduras de almas** (`verifs`, fila "Flexión global… voladizo")
- **Problema:** se usa M = q_max·(R − R_carga)²/2 como voladizo 1D, lo que da 8,55 MPa. En un disco, la carga superior (Ø1600) y la reacción inferior (Ø2000) forman un sistema autoequilibrado que flecta el sándwich completo.
- **Efecto:**
  - Solución axisimétrica de placa con borde libre y presión inferior uniforme (`indep.py`): M_r,centro ≈ 89,7 kN·mm/mm. La tensión de membrana es σ = M/(t·130) = **23,0 MPa** (2,7 veces la de la herramienta). Sumada a la flexión local convergida (unos 29 MPa) da unos 52 MPa, FU ≈ 0,25. Pasa, pero la fórmula es incorrecta.
  - El corte vertical total en r = 800 mm es V ≈ 1153 kN. Lo toman solo los 12 nervios de 20×100: τ = 48 MPa, FU 0,35 contra 0,6F_y/1,67. No se verifica.
  - El flujo rasante nervio–plancha es de unos 0,96 kN/mm, más la reacción de línea de unos 0,25 kN/mm. Un filete doble de 6 mm da unos 1,25 kN/mm. No hay ninguna verificación de las soldaduras de almas y nervios.
- **Corrección:**
  - Reemplazar la fórmula por un modelo sándwich axisimétrico, o por un modelo 3D de cáscaras del cajón con almas.
  - Agregar el corte de nervios y las soldaduras alma/nervio–plancha.
  - Superponer la membrana global a la flexión local.

**M3. Guía: volcamiento y anclaje no verificados; L_g sin respaldo** (`verifs`, bloque "guía")
- **Problema:**
  - σ = R/(e·L) supone aplastamiento uniforme en 10 mm de empotramiento. La carga R = 264,7 kN actúa a 15 mm sobre la ranura y genera M ≈ R·(15 + 5) ≈ 5,3 kN·m por cada 150 mm. Con 10 mm de empotramiento, el aplastamiento elástico equivalente supera 2000 MPa. El riel solo funciona si está apernado o soldado, y eso no se verifica.
  - L_g = 250 mm, sobre un carro de 300 mm, supone reacciones casi puntuales en los extremos. Con distribución lineal en toda la longitud, L_g ≈ 2/3·300 = 200 mm.
- **Efecto:** con L_g = 200: K pasa de 1,240 a 1,287 (+3,8 %), F_c de diseño de 315 a 327 kN, R_g de 265 a 331 kN (+25 %) y el aplastamiento sube a FU 0,71.
- **Corrección:** definir las almohadillas del carro (posición y largo), verificar pernos o soldadura del riel a la placa base frente a volcamiento, y justificar L_g.

**M4. Interfaz trinquete–carro no verificada; indicador "vmFar" no válido** (`runPawl`, `verifs`; el UI muestra vmFar)
- **Problema:**
  - Con los apoyos del propio modelo (labio inferior de 25 mm en la boca y labio superior posterior), la reacción en la boca es **796 kN ≈ 1,8 F** y la posterior 351 kN, ambas desde el FEA. En 25×90 mm eso da un aplastamiento de unos 354 MPa. Supera 0,9F_y = 310 MPa si el carro es A572 Gr50.
  - No se verifican el cuerpo del carro, su alojamiento ni el ojal del vástago en el carro.
  - El indicador vmFar depende de la malla: 312 / 355 / 519 MPa con h = 5 / 2,5 / 1,25 mm. Es la cola de la singularidad del apoyo puntual por penalización en la esquina del labio, que en compresión llega a −878 MPa con h = 1,25.
- **Efecto:**
  - La fibra traccionada en la boca sí converge: 285 / 297 / 304 MPa, por debajo de la viga (343 MPa). El chequeo por teoría de vigas (FU 0,86) es conservador y válido.
  - El pico (942 MPa) y vmFar no deben reportarse como verificación.
- **Corrección:**
  - Agregar el aplastamiento del labio con la geometría real del carro.
  - Modelar el apoyo como contacto o base elástica distribuida.
  - Reportar tensiones linealizadas (membrana + flexión) en la sección de la boca.
  - Retirar vmFar o rotularlo como singular.

**M5. Fatiga no evaluada** (verifs completo)
- **Problema:** el trinquete, los pasadores, la soldadura de la mejilla y la del riel ven un ciclo por cada 10° de giro (36 por vuelta). Las barras ven 2 ciclos por vuelta. Con tensiones nominales de 280–340 MPa al calado y 200–240 MPa a la fuerza de diseño (en trinquete y pasador), la fatiga puede gobernar.
- **Corrección:** definir el ciclo de servicio (vueltas por año y vida útil), elegir la clase de servicio según ASME BTH-1 o AISC 360-22 Apéndice 3, y verificar.

**M6. Carga en la plancha superior: uniforme, sin excentricidad, con interfaz indefinida** (`discModel`, `compute.q_top`)
- **Problema:** para la plancha inferior se usa q_max (con e), pero para la superior se usa q medio sobre Ø1600. Con e = 150 sobre un círculo de 800 mm de radio, q_max/q_avg = 1 + 4e/R = 1,75. Además, la carga real (patines, apoyos o parrilla de vigas) produce cargas de línea o concentradas, no presión uniforme.
- **Efecto:** con presión uniforme a q_max, σ_top pasa de 24,4 a unos 43 MPa (FU 0,21). Con cargas de línea, el valor queda indeterminado.
- **Corrección:** definir la interfaz de carga y aplicar la excentricidad también en la plancha superior.

**M7. Presión bajo la placa base** (`compute.g_max`)
- **Problema:** se usa σ = N/A·(1 + 6e/B) en un solo eje. La excentricidad puede tener cualquier dirección. En el peor ángulo, σ = N/A·[1 + 6e·√(1/BX² + 1/BY²)]. Además, la fórmula supone una placa rígida de 80 mm, y el disco Ø2000 cubre todo el lado BY.
- **Efecto:**
  - Caso biaxial: 0,988 MPa (FU 0,99), contra 0,904 MPa de la herramienta (+9,4 %).
  - Sin reparto de la placa (huella Ø2000): 0,95 MPa medio y 1,52 MPa máximo.
- **Corrección:** usar la excentricidad biaxial, verificar la rigidez de la placa base (placa sobre Winkler) y la capacidad real de la losa o grout.

**M8. Cargas laterales y sísmicas ausentes** (pivote, buje, placa base, anclajes)
- **Problema:** H = 0,055·W (162 kN) solo representa la fricción excéntrica, que vale μ·N·e·(4/3)(Rc³ − Ri³)/(Rc⁴ − Ri⁴):

| μ | H [kN] | % de W |
|---|---|---|
| 0,15 | 89 | 3,0 |
| 0,20 | 118 | 4,0 |
| 0,25 | 148 | 5,0 |
| 0,50 (seco) | 296 | 10,1 |

  Una instalación permanente en Chile requiere un caso sísmico según NCh2369, con aceleración horizontal muy superior al 5 % de W. El buje admite H ≤ 30·150·100 = 450 kN ≈ 0,15·W.
- **Corrección:** agregar el caso sísmico y de impacto de carga para pivote, buje, tope o anclaje del disco y la placa base, o definir topes o retención sísmica independientes.

### MENOR

| # | Ubicación | Problema | Efecto | Corrección |
|---|---|---|---|---|
| m1 | `verifs` barra 4f | AISC 360-22 F11.1 limita M_n = F_y·Z ≤ 1,6·F_y·S. Para una sección redonda Z/S = 1,698, así que gobierna 1,6S. | M_n/Ω sobrestimado 6,1 % (11,81 contra 11,13 kN·m). FU sube de 0,52 a 0,55. | Aplicar el tope. |
| m2 | `verifs` barra corte | Ω_v = 1,50 solo aplica a G2.1(a) (almas de perfiles I laminados). Para lo demás, G1 exige Ω_v = 1,67. | FU sube de 0,56 a 0,62. | Ω_v = 1,67. |
| m3 | `runDisc` sumR | Las reacciones por grupo se suman con \|R\|. En los parches rígidos de barra hay nodos con signo opuesto. | Barra: 52,8 kN por defecto, 70,9 / 82,3 / 89,5 kN al refinar, siempre creciente. La suma con signo converge a 45,6 → 46,0 kN. Es conservador pero no tiene sentido físico. | Usar la suma con signo, o \|Σ R\|. |
| m4 | `runDisc` y `fea.plate` | La tensión se recupera en puntos de Gauss o centroide. Con Q4, la curvatura normal al apoyo es constante en el elemento, así que el pico en el apoyo converge como O(h). | Disco: 25,6 MPa (por defecto) → 27,3 → 27,9 → 28,3 MPa con h_r 10/5/3 mm. Extrapolado, unos 29 MPa: −12 % en el valor por defecto (FU 0,12 → 0,14). En el benchmark de placa empotrada el error en el borde llega a −36 % con n = 10. | Refinar junto a los apoyos, extrapolar a la línea de apoyo, o agregar un benchmark empotrado a `test_fea.js`. El existente (simplemente apoyado, centro) no ejercita los picos en apoyos. |
| m5 | `PARAM_GROUPS` | H_frac = 0,05 (T_piv) y H_bush = 0,055 (buje) son hipótesis distintas y ninguna depende de μ. | Despreciable en la fuerza (T_piv ≈ 0,5 % de T). En seco, H real ≈ 0,10·W. | Derivar H con la fórmula de M8 para cada caso. |
| m6 | `compute.Fmax` | Se usa la fuerza de calado a la presión nominal de alivio. No se incluyen la sobrepresión de la válvula (presión de apertura, acumulación) ni el impacto al tomar la barra después del recorrido libre de 36 mm. | Del orden de +5–10 % en todas las verificaciones de la cadena de empuje. | Usar 1,1·p_alivio o la presión de acumulación certificada. Especificar el acercamiento lento. |
| m7 | `verifs` | Faltan verificaciones: aplastamiento del pasador en la mejilla y en el ojal (79,5 y 90,9 MPa, pasan); placas con pasador según BTH-1 3-3.3 (mejillas); pasador del ojal del vástago en el carro; anclaje de la ménsula; metal base de la soldadura PJP (J2.5 y J4). Tampoco se considera la contrapresión del lado vástago, que con 5–10 bar vale −1,6 a −3,2 kN. | Bajo | Agregar las verificaciones. |
| m8 | `discModel` | La simetría del sector solo es válida si N_bar/N_rib es entero y el patrón de barras es simétrico respecto de los nervios. Con otros parámetros, el modelo sería incorrecto sin aviso. Hay masas fijas en el código: 3070 kg, buje de 8,1 kg y el contrataladro Ø160/260/25 del cubo. | Robustez paramétrica | Agregar validación y parametrizar. |
| m9 | `calc.py` | Pandeo con Ø90 en vez del vástago, A derivada de 445 kN, masa fija y planchas 67/70 MPa fijas. | Versión obsoleta | No usarla como respaldo. Archivarla. |

### COMENTARIO (sin observación o positivo)

- **Mecánica del accionamiento:**
  - El brazo mínimo R·cos(π/N) es correcto y conservador.
  - La curva por carrera usa a(θ) y Δ(θ) correctamente.
  - Los dos cilindros, en ±X empujando en ±Y sobre barras opuestas (5° y 185°, ambas en el patrón), forman un par puro para cualquier θ: las componentes radiales F·sinθ se anulan. La condición es un circuito en paralelo con igual presión. Con circuito en paralelo, el cilindro libre completa su recorrido antes de que suba la presión, así que el sistema se autoiguala.
  - El torque de reacción queda autoequilibrado dentro de la placa base: ménsulas por un lado, fricción de la interfaz por el otro. No se transmite torque a la fundación.
- **Factor de guía:** K = (1 + 2μ_g·Δ/L_g)/η_c es exacto para fuerzas de guía en el eje del cilindro, con R calculado desde F_b. En verifs, R se calcula con F_max, lo que es conservador.
- **Fricción:** cada carrera parte del reposo, así que corresponde el μ estático, y se usa bien. Advertencia: riesgo de stick-slip con grasa grafitada a muy baja velocidad, y μ estático creciente con el tiempo de permanencia bajo carga.
- **Criterio de calado:** verificar toda la cadena de empuje a F_max = A·p_alivio hace que la seguridad estructural no dependa de μ. Es un buen criterio.
- **Normas:**
  - J7 (1,8F_y, Ω 2,0), J2.5 PJP (0,6F_EXX, Ω 2,0), E = S − 3 mm y E3 (KL/r ≈ 6) están bien aplicados.
  - 0,6F_y frente a σ_vm, rotulado como "F11", es conservador pero no es un criterio de F11.
  - En pasador y trinquete, F_y/N_d es conservador frente a las tensiones de flexión admisibles de BTH-1 3-2.3 para secciones compactas.
  - N_d = 2,0 corresponde a la Categoría de diseño A de BTH-1. BTH-1 aplica por analogía (no es un dispositivo bajo el gancho). Conviene justificar la Categoría A frente a la B (N_d = 3,0).
  - Pandeo de Euler con el vástago en toda la longitud de 650 mm: es conservador respecto del cilindro escalonado. Se recomienda ISO/TS 13725.
- **FEA MITC4 (`fea.js › plateKe`):**
  - La formulación es correcta. Puntos de amarre de γ_ξ en (0, ±1) y de γ_η en (±1, 0). Interpolación de Bathe–Dvorkin. Transformación covariante → cartesiana con J⁻¹. Flexión integrada 2×2. k_s = 5/6.
  - El ensamblaje simétrico en banda es correcto.
  - La penalización k_p = 10⁶·max(K_ii) está bien condicionada en doble precisión.
  - La penalización de simetría k_p·n·nᵀ (β·n = 0, con normal (0,1) y (−sinα, cosα)) es correcta.
  - El equilibrio es exacto (ΣF = ΣR = 426,7 y 260,2 kN).
- **Benchmarks:**
  - Simplemente apoyada: w 2,2178 contra 2,2168 (Navier).
  - Cantiléver Q4: −1,4 %.
  - Placa empotrada (propio): w = 1,267·10⁻³ q a⁴/D contra 1,26·10⁻³.
  - Anillo sectorial empotrado/apoyado (propio, malla polar con simetría): converge a σ_borde = 64,9 MPa (Kirchhoff) con O(h). Valida la malla polar y la condición de simetría.
- **Apoyos rígidos (w = 0) en almas, nervios y barras:**
  - Son adecuados para la flexión local. Las barras tienen EA/h ≈ 7,7·10⁶ N/mm y el panel tiene w ≈ 0,02 mm.
  - El acortamiento de las almas (unos 0,005 mm) es pequeño. Los apoyos rígidos sobrestiman algo los momentos negativos, es decir, son conservadores en lo local.
  - No representan la flexión global del cajón (ver M2), que es el aspecto no conservador.
  - El empotramiento en el cubo es razonable: reacción de unos 3,5 kN, sin influencia.
- **Trinquete (Q4):**
  - El momento integrado en la boca coincide con F·lev (35,97 contra 36,94 kN·m en x = X_m − h/2).
  - La carga nodal solo en Y sobre el arco escalonado es aceptable lejos del asiento.
  - El contacto Hertz conforme Ø70/R36 da b = 8,5 mm y p₀ = 371 MPa, aceptable si el contacto está centrado (ver C2).
- **Contacto q_max:** la fórmula 1 + 4eR/(R² + r²) para el anillo es correcta. La presión local real bajo almas y barras será mayor que q_max, pero está lejos de 10 MPa.

---

#### 3. Estudio de malla FEA (disco)

| Malla (h_r / Δθ) | Nodos | σ_vm inferior [MPa] | σ_vm superior [MPa] | Barra (Σ con signo) [kN] | Barra (Σ\|R\|, herramienta) [kN] |
|---|---|---|---|---|---|
| Por defecto (≈20 mm / 1,25°) | 1392 | 25,59 | 24,36 | 45,6 | 52,8 |
| 10 / 0,625° | 4895 | 27,25 | 25,60 | 45,8 | 70,9 |
| 5 / 0,3125° | 17271 | 27,85 | 26,56 | 46,0 | 82,3 |
| 3 / 0,2° | 44640 | 28,28 | 26,88 | — | 89,5 |

- El máximo está en el nervio, en r ≈ 410 mm (panel entre las almas R300 y R550).
- La reacción del alma R735 converge (244 → 240 N/mm).
- Estimación a mano para el panel empotrado de 250 × 215 mm: unos 30–33 MPa. Es coherente con el FEA convergido.

#### 4. Acciones recomendadas (orden)

1. C1, C2 y C3: confirmar la ubicación de la soldadura de las barras, la libertad radial del asiento y el margen de carrera. Corregir el diseño o el modelo antes de emitir.
2. M1: especificar planitud y esmerilado a ras, y recalcular con r = 0,94–1,0, o con distribución de contacto calculada.
3. M2 a M8: agregar al menos:
   - modelo global del cajón, corte de nervios y soldaduras de almas;
   - anclaje del riel;
   - apoyo del carro;
   - fatiga;
   - plancha superior con e e interfaz real de carga;
   - suelo biaxial;
   - caso sísmico.
4. Menores: tope 1,6S, Ω_v 1,67, suma de reacciones con signo, benchmark empotrado y recuperación en apoyos, y validaciones paramétricas.

## Apéndice F. Código fuente de la versión 500 tf Rev B (`tt/`)
Base de la que se derivó `tt300`. Diferencias principales: capacidad 500 tf, variantes U (UHMW, pastillas + pistas inox) y S (SLIP Plate), guía soldada 40×30, bisel de barras 10, sin láminas D-02/F-03.

### tt/params.py
`tt/params.py` — 134 líneas

```python
"""Parámetros geométricos tornamesa 500 tf. Unidades: mm. z=0 cara inferior placa base."""
import math

PROJ = "TORNAMESA HIDRÁULICA 500 tf"

# ---------------- comunes ----------------
B = 2000.0          # placa base, lado en Y
BX = 2400.0         # placa base, lado en X (cilindros)
TB = 80.0           # espesor placa base
D_DISC = 2000.0     # disco
TD = 160.0          # altura total disco cajón
TP_TOP = 30.0
TP_BOT = 30.0
GAP = TD - TP_TOP - TP_BOT   # 100 entre planchas
HUB_D = 300.0
RING_T = 25.0
RING_R = [300.0, 550.0, 735.0]
RIB_T = 20.0
N_RIB = 12
RIB_R1 = 880.0

# pivote / buje / tapa
D_PIV = 150.0
D_BUJE_EXT = 190.0
L_BUJE = 100.0
D_CB = 260.0        # contrataladro superior disco
H_CB = 25.0
D_TAPA = 240.0
T_TAPA = 20.0
PIV_UP = 3.0        # sobresale pivote sobre fondo contrataladro
BOLT_PCD = 100.0
N_BOLT = 6

# barras de empuje (perimetrales, entre planchas)
R_BAR = 940.0
D_BAR = 70.0
N_BAR = 36
BAR_ANG0 = 5.0      # 5° + 10°k
R_IDX = R_BAR
D_IDX_HOLE = 71.0
N_IDX = N_BAR
IDX_ANG0 = BAR_ANG0

# izaje disco (M30) y sello
R_M30 = 600.0
M30_ANG = [45, 135, 225, 315]
N_SEAL_BOLT = 36    # M8 radiales en canto plancha inferior a 0°+10°k

# cilindros
F_CYL = 445.0       # kN mín a 700 bar
STROKE = 200.0
L0_CYL = 450.0      # ojal-ojal retraído
D_CYL = 140.0
D_ROD = 90.0
EYE_W = 70.0
EYE_D = 120.0
D_PIN_CYL = 70.0
X_CYL = 1085.0      # eje cilindro / carro / guía
Y_BRK = 818.0       # pasador ménsula (±X_CYL, ±Y_BRK)

# carro de empuje y trinquete
SHOE_X0 = 1020.0    # cara interior del carro
SHOE_X1 = 1150.0
SHOE_L = 300.0
SHOE_FRONT = 20.0   # cara frontal del carro sobre centro de barra
EYE_OFF = 250.0     # centro barra -> pasador ojal vástago (retraído)
PAWL_W = 85.0       # ancho (Y)
PAWL_H = 90.0       # alto (Z)
PAWL_TIP = 905.0    # x de la punta
PAWL_L = 245.0      # largo (X)
SEAT_R = 36.0
RAIL_W, RAIL_H, RAIL_L = 40.0, 30.0, 850.0
FREE = 36.0         # recorrido libre antes de tomar la barra

# ménsula
CHEEK_T = 40.0
CHEEK_GAP = 80.0
CHEEK_L = 280.0
BACK_T = 40.0

# orejas de izaje base
LUG_T = 40.0
LUG_L = 150.0
LUG_H = 170.0
LUG_X = 600.0
LUG_HOLE = 32.0

# sello
SEAL_T = 5.0
BAR_W, BAR_T = 25.0, 6.0

# pastillas UHMW
D_PAD = 170.0
T_PAD = 10.0
D_POCKET = 170.6
H_POCKET = 5.0
RINGS = [(300.0, 6, 30.0), (550.0, 12, 15.0), (735.0, 16, 0.0)]
INOX_T = 3.0
INOX_A = (390.0, 810.0)
INOX_B = (880.0, 1680.0)


def variant(kind):
    """kind: 'U' (UHMW) o 'S' (acero-acero grafito)."""
    g = (H_POCKET + INOX_T) if kind == "U" else 0.0
    v = dict(kind=kind, g=g)
    v["z_base_top"] = TB
    v["z_disc_bot"] = TB + g
    v["z_disc_top"] = TB + g + TD
    v["z_axis"] = v["z_disc_bot"] + TP_BOT + GAP / 2
    v["z_cb_floor"] = v["z_disc_top"] - H_CB
    v["z_piv_top"] = v["z_cb_floor"] + PIV_UP
    v["L_piv"] = v["z_piv_top"]           # desde z=0
    v["z_buje_top"] = v["z_disc_bot"] + L_BUJE
    v["H_cheek"] = v["z_axis"] - TB + 70.0  # sobre cara superior base
    v["shoe_top"] = v["z_axis"] + 70.0
    v["title"] = ("SOLUCIÓN A – PASTILLAS UHMW-PE SOBRE PISTA INOX" if kind == "U"
                  else "SOLUCIÓN B – ACERO-ACERO CON PELÍCULA DE GRAFITO (SLIP PLATE)")
    v["code"] = "TT500-A" if kind == "U" else "TT500-B"
    return v


def pad_positions():
    out = []
    for r, n, a0 in RINGS:
        for k in range(n):
            a = math.radians(a0 + k * 360.0 / n)
            out.append((r, a0 + k * 360.0 / n, r * math.cos(a), r * math.sin(a)))
    return out


def idx_positions():
    return [(IDX_ANG0 + 10 * k, R_IDX * math.cos(math.radians(IDX_ANG0 + 10 * k)),
             R_IDX * math.sin(math.radians(IDX_ANG0 + 10 * k))) for k in range(N_IDX)]
```

### tt/common.py
`tt/common.py` — 143 líneas

```python
"""Datos comunes: BOM, notas, utilidades de colocación."""
import json, math
import params as P

G = 9.80665
W_KN = 500 * G
ND = 1.10 * W_KN
A_CYL = 445e3 / 70.0          # mm2 (445 kN @ 700 bar)
ARM = 0.936                   # brazo mín. de la fuerza sobre la barra (m)


def masses(v):
    return {int(k): val for k, val in json.load(open(f"/home/claude/tt/out/{v['code']}_mass.json")).items()}


def pressure_bar(mu, v):
    r = 0.593 if v["kind"] == "U" else 0.667
    T = mu * W_KN * r + 3.0
    F = T / (2 * ARM)
    return F * 1e3 / A_CYL * 10


def bom(v):
    m = masses(v)
    U = v["kind"] == "U"
    rows = [
        (1, "Placa base 2400×2000×80 mecanizada", "1", "ASTM A572 Gr.50 – Z35", m[1]),
        (2, "Ménsula de reacción (conj. soldado)", "4", "ASTM A572 Gr.50", m[2] / 4),
        (3, "Oreja de izaje e=40", "4", "ASTM A572 Gr.50", m[3] / 4),
        (4, "Disco cajón Ø2000×160 (conj. soldado 4a–4f)", "1", "ASTM A572 Gr.50 – Z35", m[4]),
        (5, f"Pivote Ø150×{v['L_piv']:.0f}", "1", "42CrMo4+QT (EN 10083-3)", m[5]),
        (6, "Buje Ø190/Ø150×100 autolubricado", "1", "CuAl10Ni5Fe4 + grafito", m[6]),
        (7, "Tapa retenedora Ø240×20", "1", "S355J2", m[7]),
        (8, "Perno ISO 4762 M20×45 + arand. Nord-Lock", "6", "10.9 zincado laminar", m[8] / 6),
        (9, "Cilindro hidr. doble efecto 50 t, 700 bar, carrera 200", "2", "Comercial (ver lám. 4)", m[9] / 2),
        (10, "Carro de empuje 300×130×" + f"{v['shoe_top'] - P.TB:.0f}" + " (guiado)", "2", "S355J2+N + bandas UHMW", m[10] / 2),
        (11, "Trinquete 245×85×90 (asiento R36)", "2", "34CrNiMo6+QT 300–350 HB", m[11] / 2),
        (12, "Pasador Ø70 (ménsula y vástago)", "4", "42CrMo4+QT", m[12] / 4),
        (13, "Resorte trinquete Ø50 + tapa + manilla; clip R Ø8", "2+4", "Comercial", 0.6),
        (14, "Faldón de sello e=5, h=" + f"{v['z_disc_bot'] + P.TP_BOT - P.TB:.0f}" + ", L≈6300", "1", "NBR 70 Shore A", m[14]),
        (15, "Fleje de apriete 25×6 rolado Ø2022", "1", "S235JR galvanizado", m[15]),
        (16, "Perno ISO 4017 M8×20 + arandela", "36", "Inox A2-70", 0.02),
        (17, "Tapón prisionero M30×25 (agujeros izaje disco)", "4", "Acero 8.8 zincado", 0.1),
        (18, "Cáncamo giratorio M30, WLL ≥ 2,5 t (suelto)", "4", "Comercial", 2.2),
    ]
    if U:
        rows += [
            (19, "Pastilla deslizante Ø170×10", "34+4", "UHMW-PE (PE1000)", m[19] / 34),
            (20, "Pista inox A Ø810/Ø390×3", "1", "AISI 316L (1.4404)", m[20]),
            (21, "Pista inox B Ø1680/Ø880×3", "1", "AISI 316L (1.4404)", m[21]),
        ]
    else:
        rows += [
            (19, "Película seca de grafito, 2 capas 50–150 µm", "≈6,3 m²", "SLIP Plate® No. 4", 0.0),
            (20, "Grasa de protección (solo ambiente húmedo)", "—", "Según manual del film", 0.0),
        ]
    rows.append((22, "Guía de carro 40×30×850 (soldada a pos 1)", "2", "S355J2", m[22] / 2))
    return rows


def total_mass(v):
    tot = 0
    for pos, d, q, mat, mu in bom(v):
        try:
            n = int(q.split("+")[0])
        except ValueError:
            n = 1 if mu else 0
        tot += n * mu
    return tot


def notes_general(v):
    U = v["kind"] == "U"
    pn = pressure_bar(0.10 if U else 0.12, v)
    pa = 600
    mu_a = (pa / 10 * A_CYL / 1e3 * 2 * ARM - 3) / (W_KN * (0.593 if U else 0.667))
    n = [
        "NOTAS GENERALES",
        "1. CAPACIDAD NOMINAL (WLL): 500 tf = 4 903 kN. Factor dinámico de diseño φd = 1,10 (giro hidráulico lento).",
        "   Excentricidad del CG de la carga respecto del pivote ≤ 150 mm. Carga solo dentro de Ø1600 sobre parrilla",
        "   de reparto o ≥ 8 apoyos simétricos. PROHIBIDO cargas puntuales sobre el disco.",
        "2. NORMAS: AISC 360-22 (ASD); ASME BTH-1 Cat. A (Nd = 2,0, referencial elementos mecánicos);",
        "   AWS D1.1/D1.1M:2020; ISO 2768-mK; ISO 1101; ISO 1302" + ("; EN 1337-2 (superficies deslizantes)." if U else "."),
        "3. MATERIALES: certificado EN 10204 3.1. Planchas pos 1 y 4: UT según ASTM A578 nivel B, calidad Z35.",
        "4. SOLDADURA: WPS/PQR calificados AWS D1.1. Electrodo E7018 / ER70S-6" + ("; inox–carbono ER309L." if U else "."),
        "   Precalentamiento ≥ 110 °C en espesores > 65 mm (AWS D1.1 Tabla 5.8, Cat. B). CJP: UT 100 %. Filetes: MT 100 %.",
        "5. Conjunto soldado pos 1+2+3: alivio de tensiones 590–620 °C antes del mecanizado final.",
        "6. PROTECCIÓN: Sa 2½ + epóxico rico en zinc 75 µm + epóxico 125 µm + PU 50 µm (ISO 12944, C4).",
        "   Sin pintura: caras de deslizamiento, alojamientos, agujeros de pasadores, buje y roscas.",
        "7. INTERFAZ DE GIRO: " + ("pastillas UHMW-PE pos 19 en alojamientos de pos 1 contra pistas inox pos 20/21" if U
                                    else "contacto pleno acero-acero pos 1/pos 4 con película seca de grafito pos 19"),
        "   " + ("soldadas a pos 4. Operación EN SECO, sin grasa." if U else "en ambas caras. NO aplicar grasa en ambiente seco/polvoriento."),
        "8. ACCIONAMIENTO: 2 cilindros pos 9 en par sobre carros guiados pos 10; el trinquete pos 11 empuja",
        "   directo una barra vertical Ø70 del disco (36 barras c/10° en R940). Carrera 200 = 36 libre + 164 = 10°/ciclo.",
        "   Retorno: el trinquete se retrae por su chaflán al pasar la barra siguiente y engancha por resorte.",
        "   Rótulas GE70 en ambos ojales. PROHIBIDO empujar con un solo cilindro (válvula de bloqueo en paralelo).",
        f"   Presión esperada ≈ {pn:.0f} bar (μ ≈ {'0,10' if U else '0,12'}). Detener y revisar interfaz si p > {pa} bar (μ > {mu_a:.2f}).".replace("(μ > 0.", "(μ > 0,"),
        "   Giro antihorario: carros en x = ±1085 con ménsulas (+1085;-818) y (-1085;+818). Horario: invertir carro y ménsula.",
        "9. APOYO: base totalmente apoyada sobre losa de H.A. o mats rígidos; pendiente ≤ 0,5 %.",
        "   Presión de contacto bajo base: 1,03 MPa media / 1,49 MPa máx. (e = 150 mm).",
        "10. ENSAYO: giro 360° a 1,0 WLL registrando presión; estático 1,25 WLL si existe marco de reacción;",
        "    MT de soldaduras pos 2/3 posterior al ensayo.",
        "11. Cilindro: L0 = 450 entre ojales (retraído); verificar con proveedor y ajustar posición de pos 2 si difiere.",
    ]
    return n


def fmt_kg(x):
    return f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


class Place:
    """Transforma coordenadas de modelo (pantalla) a papel."""
    def __init__(self, O, s, m0=(0.0, 0.0)):
        self.O, self.s, self.m0 = O, s, m0

    def __call__(self, p):
        return (self.O[0] + (p[0] - self.m0[0]) * self.s, self.O[1] + (p[1] - self.m0[1]) * self.s)

    def polys(self, sh, polys, layer="VIS"):
        for pl in polys:
            pts = [self(p) for p in pl]
            if len(pts) == 2:
                sh.line(pts[0], pts[1], layer)
            else:
                sh.pline(pts, layer)

    def hatches(self, sh, hatches, small=(14, 20, 21)):
        ang = {1: 0, 2: 90, 3: 90, 4: 90, 5: 0, 6: 0, 7: 90, 8: 0, 10: 0, 11: 90, 12: 90, 15: 0, 19: 0}
        pat = {6: "ANSI33", 19: "ANSI37"}
        for pos, outer, holes in hatches:
            o = [self(p) for p in outer]
            hh = [[self(p) for p in h] for h in holes]
            if pos in small:
                sh.hatch_poly(o, hh, solid=True)
            else:
                sh.hatch_poly(o, hh, scale=0.55 if pos != 19 else 0.45, angle=ang.get(pos, 45), pattern=pat.get(pos, "ANSI31"))


def bbox(polys):
    xs = [p[0] for pl in polys for p in pl]
    ys = [p[1] for pl in polys for p in pl]
    return min(xs), min(ys), max(xs), max(ys)
```

### tt/draw.py
`tt/draw.py` — 314 líneas

```python
"""Mini-librería de dibujo técnico sobre ezdxf (coordenadas de papel en mm, A1 841x594)."""
import math
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA

W, H = 841.0, 594.0
TXT_STYLE = "STD"


def new_doc():
    doc = ezdxf.new("R2018", units=4)
    doc.styles.add(TXT_STYLE, font="LiberationSans-Regular.ttf")
    doc.styles.add("STDB", font="LiberationSans-Bold.ttf")
    lt = doc.linetypes
    lt.add("OCULTO", pattern=[4.5, 3.0, -1.5], description="__ __ __")
    lt.add("EJE", pattern=[22.0, 14.0, -3.0, 2.0, -3.0], description="__ . __")
    lt.add("FANTASMA", pattern=[26.0, 14.0, -3.0, 2.0, -2.0, 2.0, -3.0], description="__ . . __")
    for name, lw, ltype in [("VIS", 50, "CONTINUOUS"), ("FINA", 18, "CONTINUOUS"), ("OCU", 25, "OCULTO"),
                            ("EJE", 18, "EJE"), ("COTA", 18, "CONTINUOUS"), ("TXT", 25, "CONTINUOUS"),
                            ("ACH", 13, "CONTINUOUS"), ("MARCO", 70, "CONTINUOUS"), ("FANT", 18, "FANTASMA")]:
        doc.layers.add(name, color=7, lineweight=lw, linetype=ltype)
    doc.header["$LTSCALE"] = 1.0
    doc.header["$PSLTSCALE"] = 0
    return doc


class Sheet:
    def __init__(self):
        self.doc = new_doc()
        self.m = self.doc.modelspace()

    # ---------- primitivas ----------
    def line(self, p1, p2, layer="VIS"):
        self.m.add_line(p1, p2, dxfattribs={"layer": layer})

    def pline(self, pts, layer="VIS", closed=False):
        self.m.add_lwpolyline(pts, close=closed, dxfattribs={"layer": layer})

    def rect(self, x0, y0, x1, y1, layer="VIS"):
        self.pline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, closed=True)

    def circle(self, c, r, layer="VIS"):
        self.m.add_circle(c, r, dxfattribs={"layer": layer})

    def arc(self, c, r, a0, a1, layer="VIS"):
        self.m.add_arc(c, r, a0, a1, dxfattribs={"layer": layer})

    def text(self, s, p, h=2.5, align="BOTTOM_LEFT", rot=0.0, layer="TXT", bold=False):
        t = self.m.add_text(s, height=h, rotation=rot,
                            dxfattribs={"layer": layer, "style": "STDB" if bold else TXT_STYLE})
        t.set_placement(p, align=TA[align])
        return t

    def mtext(self, lines, p, h=2.5, ls=1.6, bold_first=False, width=None):
        y = p[1]
        for i, s in enumerate(lines):
            self.text(s, (p[0], y), h, "TOP_LEFT", bold=(bold_first and i == 0))
            y -= h * ls
        return y

    def hatch_poly(self, outer, holes=(), scale=0.9, angle=0.0, pattern="ANSI31", solid=False):
        h = self.m.add_hatch(color=7, dxfattribs={"layer": "ACH"})
        if solid:
            h.set_solid_fill(color=7)
        else:
            h.set_pattern_fill(pattern, scale=scale, angle=angle)
        h.paths.add_polyline_path(outer, is_closed=True, flags=1)
        for hh in holes:
            h.paths.add_polyline_path(hh, is_closed=True, flags=16)

    def centerlines(self, c, r, ext=3.0):
        self.line((c[0] - r - ext, c[1]), (c[0] + r + ext, c[1]), "EJE")
        self.line((c[0], c[1] - r - ext), (c[0], c[1] + r + ext), "EJE")

    def cross(self, c, s=2.0):
        self.line((c[0] - s, c[1]), (c[0] + s, c[1]), "FINA")
        self.line((c[0], c[1] - s), (c[0], c[1] + s), "FINA")

    # ---------- acotado ----------
    def arrow(self, tip, ang, size=2.8, w=0.9):
        ca, sa = math.cos(ang), math.sin(ang)
        bx, by = tip[0] - size * ca, tip[1] - size * sa
        p1 = (bx - w * sa, by + w * ca)
        p2 = (bx + w * sa, by - w * ca)
        self.m.add_solid([tip, p1, p2], dxfattribs={"layer": "COTA"})

    def dim(self, p1, p2, off, txt, orient="h", h=2.5, txt_shift=0.0, outside=False):
        """Cota lineal. orient 'h' (mide dx), 'v' (mide dy), 'a' alineada. off: distancia firmada de la línea de cota."""
        x1, y1 = p1
        x2, y2 = p2
        if orient == "h":
            yd = (y1 if off >= 0 and y1 >= y2 else y2 if off >= 0 else min(y1, y2)) + off
            yd = max(y1, y2) + off if off >= 0 else min(y1, y2) + off
            a, b = (x1, yd), (x2, yd)
            for (px, py) in (p1, p2):
                s = 1.0 if yd > py else -1.0
                self.line((px, py + s * 1.0), (px, yd + s * 2.0), "COTA")
        elif orient == "v":
            xd = max(x1, x2) + off if off >= 0 else min(x1, x2) + off
            a, b = (xd, y1), (xd, y2)
            for (px, py) in (p1, p2):
                s = 1.0 if xd > px else -1.0
                self.line((px + s * 1.0, py), (xd + s * 2.0, py), "COTA")
        else:
            ang = math.atan2(y2 - y1, x2 - x1)
            nx, ny = -math.sin(ang) * off, math.cos(ang) * off
            a, b = (x1 + nx, y1 + ny), (x2 + nx, y2 + ny)
            for (px, py), q in ((p1, a), (p2, b)):
                self.line((px, py), (q[0] + nx / max(abs(off), 1e-9) * 2, q[1] + ny / max(abs(off), 1e-9) * 2), "COTA")
        self.line(a, b, "COTA")
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if outside or L < 7:
            self.arrow(a, ang); self.arrow(b, ang + math.pi)
            self.line(a, (a[0] - 5 * math.cos(ang), a[1] - 5 * math.sin(ang)), "COTA")
            self.line(b, (b[0] + 5 * math.cos(ang), b[1] + 5 * math.sin(ang)), "COTA")
        else:
            self.arrow(a, ang + math.pi); self.arrow(b, ang)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        deg = math.degrees(ang)
        if deg > 90.01 or deg < -89.99:
            deg += 180
        r = math.radians(deg)
        tx = mx - math.sin(r) * 1.0 + math.cos(r) * txt_shift
        ty = my + math.cos(r) * 1.0 + math.sin(r) * txt_shift
        self.text(txt, (tx, ty), h, "BOTTOM_CENTER", rot=deg)

    def dim_dia(self, c, r, ang_deg, txt, h=2.5, ext=8.0):
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        p1 = (c[0] + r * ca, c[1] + r * sa)
        p2 = (c[0] - r * ca, c[1] - r * sa)
        p3 = (c[0] + (r + ext) * ca, c[1] + (r + ext) * sa)
        self.line(p2, p3, "COTA")
        self.arrow(p1, a)
        self.arrow(p2, a + math.pi)
        sh = 1 if ca >= 0 else -1
        p4 = (p3[0] + sh * (len(txt) * h * 0.62 + 1), p3[1])
        self.line(p3, p4, "COTA")
        self.text(txt, (p3[0] + sh * 0.5, p3[1] + 0.8), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")

    def dim_rad(self, c, r, ang_deg, txt, h=2.5, ext=8.0):
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        p1 = (c[0] + r * ca, c[1] + r * sa)
        p3 = (c[0] + (r + ext) * ca, c[1] + (r + ext) * sa)
        self.line(c, p3, "COTA")
        self.arrow(p1, a)
        sh = 1 if ca >= 0 else -1
        p4 = (p3[0] + sh * (len(txt) * h * 0.62 + 1), p3[1])
        self.line(p3, p4, "COTA")
        self.text(txt, (p3[0] + sh * 0.5, p3[1] + 0.8), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")

    def leader(self, p, q, txt, h=2.5, dot=False, lines=None):
        """Flecha en p, codo en q, texto horizontal."""
        self.line(p, q, "COTA")
        if dot:
            self.m.add_circle(p, 0.6, dxfattribs={"layer": "COTA"})
            self.hatch_poly([(p[0] + 0.6 * math.cos(t / 8 * math.pi * 2), p[1] + 0.6 * math.sin(t / 8 * math.pi * 2)) for t in range(8)], solid=True)
        else:
            self.arrow(p, math.atan2(p[1] - q[1], p[0] - q[0]))
        sh = 1 if q[0] >= p[0] else -1
        txts = [txt] if lines is None else lines
        wmax = max(len(t) for t in txts) * h * 0.58 + 1
        self.line(q, (q[0] + sh * wmax, q[1]), "COTA")
        y = q[1] + 0.8
        for i, t in enumerate(txts):
            if i == 0:
                self.text(t, (q[0] + sh * 0.5, y), h, "BOTTOM_LEFT" if sh > 0 else "BOTTOM_RIGHT")
            else:
                self.text(t, (q[0] + sh * 0.5, q[1] - 1.0 - (i - 1) * h * 1.5), h, "TOP_LEFT" if sh > 0 else "TOP_RIGHT")

    def balloon(self, p, q, n, r=4.5):
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        ux, uy = (q[0] - p[0]) / d, (q[1] - p[1]) / d
        self.line(p, (q[0] - ux * r, q[1] - uy * r), "COTA")
        self.m.add_circle(p, 0.7, dxfattribs={"layer": "COTA"})
        self.hatch_poly([(p[0] + 0.7 * math.cos(t / 10 * math.pi * 2), p[1] + 0.7 * math.sin(t / 10 * math.pi * 2)) for t in range(10)], solid=True)
        self.circle(q, r, "FINA")
        self.text(str(n), q, 3.2, "MIDDLE_CENTER", bold=True)

    def view_title(self, p, title, scale, h=4.0):
        self.text(title, p, h, "BOTTOM_CENTER", bold=True)
        w = len(title) * h * 0.62
        self.line((p[0] - w / 2, p[1] - 1.2), (p[0] + w / 2, p[1] - 1.2), "VIS")
        self.text(scale, (p[0], p[1] - 2.5), 2.8, "TOP_CENTER")

    def section_mark(self, p, ang_deg, label, length=8.0):
        """Flecha de corte en p, apuntando ang (dirección de mirada)."""
        a = math.radians(ang_deg)
        q = (p[0] + length * math.cos(a), p[1] + length * math.sin(a))
        self.line(p, q, "VIS")
        self.arrow(q, a, size=3.5, w=1.3)
        self.text(label, (q[0] + 3 * math.cos(a), q[1] + 3 * math.sin(a)), 5.0, "MIDDLE_CENTER", bold=True)

    def detail_circle(self, c, r, label):
        self.circle(c, r, "FANT")
        self.text(label, (c[0] + r * 0.72 + 2, c[1] + r * 0.72 + 2), 5.0, "BOTTOM_LEFT", bold=True)

    def finish(self, p, ra, h=2.5):
        """Símbolo de rugosidad (ISO 1302) con Ra."""
        x, y = p
        self.pline([(x - 2.2, y + 3.8), (x, y), (x + 4.4, y + 7.6), (x + 12, y + 7.6)], "COTA")
        self.line((x - 2.2, y + 3.8), (x + 2.2, y + 3.8), "COTA")
        self.text(ra, (x + 4.6, y + 8.2), h, "BOTTOM_LEFT")

    def weld(self, p, q, kind, size, other=False, all_round=False, note="", h=2.5):
        """Símbolo de soldadura AWS A2.4 simplificado. kind 'fillet' | 'cjp' | 'bevel'."""
        self.line(p, q, "COTA")
        self.arrow(p, math.atan2(p[1] - q[1], p[0] - q[0]))
        sh = 1 if q[0] >= p[0] else -1
        L = 26.0
        r = (q[0] + sh * L, q[1])
        self.line(q, r, "COTA")
        mx = q[0] + sh * L * 0.45
        ys = [-1] + ([1] if other else [])
        for side in ys:
            if kind == "fillet":
                self.pline([(mx - 2.2, q[1]), (mx - 2.2, q[1] + side * 4.4), (mx + 2.2, q[1])], "COTA")
            else:
                self.pline([(mx - 2.4, q[1] + side * 4.6), (mx, q[1]), (mx + 2.4, q[1] + side * 4.6)] if kind == "cjp"
                           else [(mx - 2.2, q[1]), (mx - 2.2, q[1] + side * 4.6), (mx + 2.4, q[1] + side * 4.6)], "COTA")
            self.text(size, (mx - sh * 4.0, q[1] + side * 2.6), h, ("MIDDLE_RIGHT" if sh > 0 else "MIDDLE_LEFT"))
        if all_round:
            self.circle(q, 1.6, "COTA")
        if note:
            self.pline([(r[0], r[1]), (r[0] + sh * 3, r[1] + 3), ], "COTA")
            self.pline([(r[0], r[1]), (r[0] + sh * 3, r[1] - 3), ], "COTA")
            self.text(note, (r[0] + sh * 4, r[1]), h, "MIDDLE_LEFT" if sh > 0 else "MIDDLE_RIGHT")

    def table(self, x0, y0, cols, rows, rh=6.0, h=2.3, header_h=None, bold_header=True):
        """cols: lista de (titulo, ancho, align). rows: lista de listas. Dibuja desde y0 hacia abajo. Retorna y final."""
        header_h = header_h or rh * 1.3
        widths = [c[1] for c in cols]
        Wt = sum(widths)
        y = y0
        allrows = [[c[0] for c in cols]] + rows
        for i, row in enumerate(allrows):
            rhh = header_h if i == 0 else rh
            self.line((x0, y), (x0 + Wt, y), "VIS" if i <= 1 else "FINA")
            x = x0
            for j, cell in enumerate(row):
                al = cols[j][2] if i else "C"
                if al == "C":
                    self.text(str(cell), (x + widths[j] / 2, y - rhh / 2), h, "MIDDLE_CENTER", bold=(i == 0 and bold_header))
                elif al == "R":
                    self.text(str(cell), (x + widths[j] - 1.2, y - rhh / 2), h, "MIDDLE_RIGHT")
                else:
                    self.text(str(cell), (x + 1.2, y - rhh / 2), h, "MIDDLE_LEFT", bold=(i == 0 and bold_header))
                x += widths[j]
            y -= rhh
        self.line((x0, y), (x0 + Wt, y), "VIS")
        x = x0
        for wv in widths + [0]:
            self.line((x, y0), (x, y), "FINA" if 0 < x - x0 < Wt else "VIS")
            x += wv
        return y

    # ---------- formato ----------
    def frame(self, v, sheet_no, n_sheets, title2, scale_txt, rev="B"):
        self.rect(0, 0, W, H, "FINA")
        self.rect(20, 10, W - 10, H - 10, "MARCO")
        # zonas
        for i in range(1, 8):
            x = 20 + i * (W - 30) / 8
            self.line((x, H - 10), (x, H - 5), "FINA"); self.line((x, 10), (x, 5), "FINA")
        for i in range(8):
            self.text(str(i + 1), (20 + (i + 0.5) * (W - 30) / 8, H - 7.5), 2.5, "MIDDLE_CENTER")
        for i, L in enumerate("FEDCBA"):
            y = 10 + (i + 0.5) * (H - 20) / 6
            self.text(L, (15, y), 2.5, "MIDDLE_CENTER")
        # rótulo 180 x 62
        x0, y0, x1 = W - 10 - 180, 10, W - 10
        y1 = y0 + 62
        self.rect(x0, y0, x1, y1, "MARCO")
        rows = [y0 + 10, y0 + 20, y0 + 30, y0 + 44]
        for yy in rows:
            self.line((x0, yy), (x1, yy), "FINA")
        self.line((x0 + 60, y0), (x0 + 60, y0 + 30), "FINA")
        self.line((x0 + 120, y0), (x0 + 120, y0 + 30), "FINA")
        self.text(f"PROYECTO: {v['proj']}", (x0 + 2, y1 - 3), 3.2, "TOP_LEFT", bold=True)
        self.text(v["title"], (x0 + 2, y1 - 9.5), 2.6, "TOP_LEFT")
        self.text(title2, (x0 + 2, y0 + 41.5), 3.6, "TOP_LEFT", bold=True)
        self.text("EMITIDO PARA REVISIÓN – NO APTO PARA FABRICACIÓN HASTA APROBACIÓN", (x0 + 2, y0 + 32), 2.2, "BOTTOM_LEFT", bold=True)
        cells = [("ELABORÓ", "—", 0, 2), ("REVISÓ", "—", 1, 2), ("APROBÓ", "—", 2, 2),
                 ("ESCALA", scale_txt, 0, 1), ("FECHA", "16-10-2026", 1, 1), ("FORMATO", "A1", 2, 1),
                 ("PLANO N°", f"{v['code']}-{sheet_no:02d}", 0, 0), ("LÁMINA", f"{sheet_no} de {n_sheets}", 1, 0), ("REV.", rev, 2, 0)]
        for lab, val, cx, ry in cells:
            xx = x0 + cx * 60
            yy = y0 + ry * 10
            self.text(lab, (xx + 1.5, yy + 8.6), 1.8, "TOP_LEFT")
            self.text(val, (xx + 30, yy + 3.2), 3.0 if ry == 0 else 2.6, "MIDDLE_CENTER", bold=(ry == 0))
        self.text("Cotas en mm salvo indicación. No medir sobre el plano.", (x0, y1 + 1.5), 2.0, "BOTTOM_LEFT")
        self.text("Rev. B (16-10-2026): disco cajón con barras perimetrales; empuje directo con carro y trinquete.", (20, 6.5), 2.0, "BOTTOM_LEFT")

    # ---------- salida ----------
    def save(self, dxf_path, pdf_path=None):
        self.doc.saveas(dxf_path)
        if pdf_path:
            return render_pdf(self.doc, pdf_path)


def render_pdf(doc, pdf_path):
    from ezdxf.addons.drawing import Frontend, RenderContext, pymupdf, layout, config
    backend = pymupdf.PyMuPdfBackend()
    cfg = config.Configuration(color_policy=config.ColorPolicy.BLACK,
                               background_policy=config.BackgroundPolicy.WHITE,
                               lineweight_scaling=1.0,
                               min_lineweight=0.13)
    Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace(), finalize=True)
    page = layout.Page(W, H, layout.Units.mm, margins=layout.Margins.all(0))
    pdf = backend.get_pdf_bytes(page, settings=layout.Settings(fit_page=False, scale=1.0))
    open(pdf_path, "wb").write(pdf)
    return pdf_path
```

### tt/hlr.py
`tt/hlr.py` — 172 líneas

```python
"""Proyección con líneas ocultas (HLR) y cortes desde el modelo CadQuery."""
import math
import cadquery as cq
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union, polygonize

VIEWS = {
    "top": ((0, 0, 1), (1, 0, 0)),
    "front": ((0, -1, 0), (1, 0, 0)),       # mira hacia +y, pantalla (x, z)
    "back": ((0, 1, 0), (-1, 0, 0)),
    "right": ((1, 0, 0), (0, 1, 0)),        # mira hacia -x, pantalla (y, z)
    "left": ((-1, 0, 0), (0, -1, 0)),
    "iso": ((1, -1, 1), (1, 1, 0)),
    "iso2": ((1, -1.25, 0.9), (1.25, 1, 0)),
}


def basis(view):
    d, x = VIEWS[view]
    dn = [c / math.sqrt(sum(k * k for k in d)) for k in [0] for c in d]
    n = math.sqrt(sum(c * c for c in d)); d = [c / n for c in d]
    n = math.sqrt(sum(c * c for c in x)); x = [c / n for c in x]
    y = [d[1] * x[2] - d[2] * x[1], d[2] * x[0] - d[0] * x[2], d[0] * x[1] - d[1] * x[0]]
    return d, x, y


def proj_pt(p, view):
    d, x, y = basis(view)
    return (sum(a * b for a, b in zip(p, x)), sum(a * b for a, b in zip(p, y)))


def _edges_to_polys(comp, tol):
    out = []
    if comp is None or comp.IsNull():
        return out
    for e in cq.Shape.cast(comp).Edges():
        try:
            if e.geomType() == "LINE":
                a, b = e.startPoint(), e.endPoint()
                out.append([(a.x, a.y), (b.x, b.y)])
            else:
                L = e.Length()
                n = max(6, min(400, int(L / tol)))
                pts = [e.positionAt(i / n) for i in range(n + 1)]
                out.append([(p.x, p.y) for p in pts])
        except Exception:
            pass
    return out


def hlr(shape, view, tol=2.0, hidden=False):
    d, x = VIEWS[view]
    ax = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*d), gp_Dir(*x))
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    algo.Projector(HLRAlgo_Projector(ax))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = _edges_to_polys(h.VCompound(), tol) + _edges_to_polys(h.OutLineVCompound(), tol)
    hid = []
    if hidden:
        hid = _edges_to_polys(h.HCompound(), tol) + _edges_to_polys(h.OutLineHCompound(), tol)
    return vis, hid


NOCUT = {5, 8, 9, 11, 12, 13, 16}


def section(parts, view, plane_pt, keep_dir, tol=2.0, hidden=False, only=None, nocut=NOCUT):
    """parts: [(pos, shape)] cq.Shape. Corta con plano por plane_pt normal keep_dir (se conserva lado +keep_dir).
    Devuelve (vis, hid, hatch) con hatch = [(pos, outer, holes)] en coords de pantalla."""
    big = 20000
    nx, ny, nz = keep_dir
    # semiespacio a eliminar: caja del lado -keep_dir
    c = (plane_pt[0] - nx * big / 2, plane_pt[1] - ny * big / 2, plane_pt[2] - nz * big / 2)
    cutter = cq.Solid.makeBox(big, big, big, pnt=cq.Vector(c[0] - big / 2 * (1 - abs(nx)) - (big / 2 if nx else 0) + (big / 2 if nx else 0),
                                                          c[1], c[2])) if False else None
    halfbox = cq.Solid.makeBox(big, big, big).translate(cq.Vector(-big / 2, -big / 2, -big / 2))
    halfbox = halfbox.translate(cq.Vector(plane_pt[0] - nx * big / 2, plane_pt[1] - ny * big / 2, plane_pt[2] - nz * big / 2))
    kept, hatches = [], []
    plane = cq.Face.makePlane(big, big, basePnt=cq.Vector(*plane_pt), dir=cq.Vector(*keep_dir))
    for pos, shp in parts:
        if only and pos not in only:
            continue
        if pos in nocut:
            kept.append(shp)
            continue
        try:
            k = shp.cut(halfbox)
        except Exception:
            k = shp
        if k.isValid() and k.Volume() > 1e-3:
            kept.append(k)
        try:
            sec = shp.intersect(plane)
            for f in sec.Faces():
                segs = []
                for e in f.Edges():
                    if e.geomType() == "LINE":
                        pts = [e.startPoint(), e.endPoint()]
                    else:
                        n = max(8, min(300, int(e.Length() / tol)))
                        pts = [e.positionAt(i / n) for i in range(n + 1)]
                    pp = [proj_pt((p.x, p.y, p.z), view) for p in pts]
                    pp = [(round(x * 10) / 10, round(y * 10) / 10) for x, y in pp]
                    if len(pp) > 2 and abs(pp[0][0] - pp[-1][0]) < 0.6 and abs(pp[0][1] - pp[-1][1]) < 0.6:
                        pp[-1] = pp[0]
                    segs.append(LineString(pp))
                polys = list(polygonize(unary_union(segs)))
                g = None
                for pg in polys:
                    g = pg if g is None else g.symmetric_difference(pg)
                if g is None:
                    continue
                for gg in getattr(g, "geoms", [g]):
                    if gg.geom_type == "Polygon" and gg.area > 0.5:
                        hatches.append((pos, list(gg.exterior.coords), [list(i.coords) for i in gg.interiors]))
        except Exception as ex:
            print("sec fail", pos, ex)
    comp = cq.Compound.makeCompound(kept)
    vis, hid = hlr(comp, view, tol, hidden)
    return vis, hid, hatches


def _wire_pts(w, tol):
    pts = []
    for e in w.Edges():
        if e.geomType() == "LINE":
            seg = [e.startPoint(), e.endPoint()]
        else:
            n = max(8, min(300, int(e.Length() / tol)))
            seg = [e.positionAt(i / n) for i in range(n + 1)]
        if pts and (pts[-1] - seg[0]).Length > 1e-3 and (pts[-1] - seg[-1]).Length < 1e-3:
            seg = seg[::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts


def clip_polys(polys, win):
    """win=(x0,y0,x1,y1) en coords de pantalla del modelo."""
    b = box(*win)
    out = []
    for p in polys:
        if len(p) < 2:
            continue
        g = LineString(p).intersection(b)
        if g.is_empty:
            continue
        geoms = getattr(g, "geoms", [g])
        for gg in geoms:
            if gg.geom_type == "LineString" and len(gg.coords) >= 2:
                out.append(list(gg.coords))
    return out


def clip_hatch(hatches, win):
    b = box(*win)
    out = []
    for pos, outer, holes in hatches:
        try:
            pg = Polygon(outer, holes).buffer(0)
            g = pg.intersection(b)
        except Exception:
            continue
        for gg in getattr(g, "geoms", [g]):
            if gg.geom_type == "Polygon" and gg.area > 1:
                out.append((pos, list(gg.exterior.coords), [list(i.coords) for i in gg.interiors]))
    return out
```

### tt/model3d.py
`tt/model3d.py` — 266 líneas

```python
"""Modelo 3D CadQuery de la tornamesa 500 tf (variantes U y S)."""
import math
import cadquery as cq
import params as P

C = {
    "steel": cq.Color(0.55, 0.57, 0.60), "disc": cq.Color(0.98, 0.78, 0.10),
    "base": cq.Color(0.20, 0.33, 0.55), "bronze": cq.Color(0.72, 0.50, 0.20),
    "pin": cq.Color(0.35, 0.35, 0.38), "uhmw": cq.Color(0.95, 0.95, 0.92),
    "inox": cq.Color(0.82, 0.84, 0.87), "nbr": cq.Color(0.08, 0.08, 0.08),
    "cyl": cq.Color(0.85, 0.15, 0.12), "graph": cq.Color(0.25, 0.25, 0.25),
}


def cyl(r, h, x=0, y=0, z=0):
    return cq.Workplane("XY").workplane(offset=z).center(x, y).circle(r).extrude(h)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def base_plate(v):
    b = cq.Workplane("XY").box(P.BX, P.B, P.TB, centered=(True, True, False))
    b = b.cut(cyl(P.D_PIV / 2, P.TB))
    if v["kind"] == "U":
        for _, _, x, y in P.pad_positions():
            b = b.cut(cyl(P.D_POCKET / 2, P.H_POCKET, x, y, P.TB - P.H_POCKET))
            b = b.cut(cyl(5, P.TB, x, y, 0))
    return b


def bracket(v, sx, sy):
    """Ménsula en (sx*X_CYL, sy*Y_BRK); mejillas paralelas a Y, respaldo hacia el borde de la base."""
    h = v["H_cheek"]
    x0, y0 = sx * P.X_CYL, sy * P.Y_BRK
    w = None
    for side in (-1, 1):
        xc = x0 + side * (P.CHEEK_GAP / 2 + P.CHEEK_T / 2)
        ch = cq.Workplane("XY").box(P.CHEEK_T, P.CHEEK_L, h, centered=(True, True, False)).translate((xc, y0, P.TB))
        w = ch if w is None else w.union(ch)
    yb = y0 + sy * (P.CHEEK_L / 2 + P.BACK_T / 2)
    back = cq.Workplane("XY").box(P.CHEEK_GAP + 2 * P.CHEEK_T, P.BACK_T, h, centered=(True, True, False)).translate((x0, yb, P.TB))
    w = w.union(back)
    hole = cq.Workplane("YZ").workplane(offset=x0 - 200).center(y0, v["z_axis"]).circle((P.D_PIN_CYL + 1) / 2).extrude(400)
    return w.cut(hole)


def rails(v):
    r = None
    for sx in (1, -1):
        k = box(sx * P.X_CYL - P.RAIL_W / 2, sx * P.X_CYL + P.RAIL_W / 2, -P.RAIL_L / 2, P.RAIL_L / 2, P.TB, P.TB + P.RAIL_H)
        r = k if r is None else r.union(k)
    return r


def lug(v, sx, sy):
    x0 = sx * P.LUG_X
    y1 = sy * (P.B / 2 - P.LUG_L / 2)
    l = cq.Workplane("XY").box(P.LUG_T, P.LUG_L, P.LUG_H, centered=(True, True, False)).translate((x0, y1, P.TB))
    l = l.edges("|X and >Z").fillet(60)
    hole = cq.Workplane("YZ").workplane(offset=x0 - 50).center(y1, P.TB + 100).circle(P.LUG_HOLE / 2).extrude(100)
    return l.cut(hole)


def disc_parts(v):
    """Disco cajón: dict de sub-piezas (4a..4f)."""
    zb, zt = v["z_disc_bot"], v["z_disc_top"]
    R = P.D_DISC / 2
    def plate(z0, t):
        p = cyl(R, t, z=z0).cut(cyl(P.HUB_D / 2, t, z=z0))
        for _, x, y in P.idx_positions():
            p = p.cut(cyl(P.D_IDX_HOLE / 2, t, x, y, z0))
        return p
    bot = plate(zb, P.TP_BOT)
    top = plate(zt - P.TP_TOP, P.TP_TOP)
    for a in P.M30_ANG:
        x, y = P.R_M30 * math.cos(math.radians(a)), P.R_M30 * math.sin(math.radians(a))
        top = top.cut(cyl(13.25, P.TP_TOP, x, y, zt - P.TP_TOP))
    hub = cyl(P.HUB_D / 2, P.TD, z=zb)
    hub = hub.cut(cyl(P.D_BUJE_EXT / 2, P.L_BUJE, z=zb))
    hub = hub.cut(cyl(80, P.TD, z=zb))
    hub = hub.cut(cyl(P.D_CB / 2, P.H_CB, z=zt - P.H_CB))
    z0, h = zb + P.TP_BOT, P.GAP
    rings = None
    for r in P.RING_R:
        k = cyl(r + P.RING_T / 2, h, z=z0).cut(cyl(r - P.RING_T / 2, h, z=z0))
        rings = k if rings is None else rings.union(k)
    ribs = None
    for k in range(P.N_RIB):
        a = 360.0 / P.N_RIB * k
        rb = box(P.HUB_D / 2 - 2, P.RIB_R1, -P.RIB_T / 2, P.RIB_T / 2, z0, z0 + h).rotate((0, 0, 0), (0, 0, 1), a)
        ribs = rb if ribs is None else ribs.union(rb)
    bars = None
    for _, x, y in P.idx_positions():
        k = cyl(P.D_BAR / 2, P.TD, x, y, zb)
        bars = k if bars is None else bars.union(k)
    return {"4a": top, "4b": bot, "4c": hub, "4d": rings, "4e": ribs, "4f": bars}


def disc(v):
    d = disc_parts(v)
    s = d["4a"]
    for k in ("4b", "4c", "4d", "4e", "4f"):
        s = s.union(d[k])
    return s


def pivot(v):
    p = cyl(P.D_PIV / 2, v["L_piv"])
    p = p.faces("<Z").chamfer(5)
    for k in range(P.N_BOLT):
        a = math.radians(30 + 60 * k)
        p = p.cut(cyl(8.6, 40, P.BOLT_PCD / 2 * math.cos(a), P.BOLT_PCD / 2 * math.sin(a), v["L_piv"] - 40))
    return p


def bushing(v):
    return cyl(P.D_BUJE_EXT / 2, P.L_BUJE, z=v["z_disc_bot"]).cut(cyl(P.D_PIV / 2, P.L_BUJE, z=v["z_disc_bot"]))


def cap(v):
    c = cyl(P.D_TAPA / 2, P.T_TAPA, z=v["z_piv_top"])
    for k in range(P.N_BOLT):
        a = math.radians(30 + 60 * k)
        x, y = P.BOLT_PCD / 2 * math.cos(a), P.BOLT_PCD / 2 * math.sin(a)
        c = c.cut(cyl(11, P.T_TAPA, x, y, v["z_piv_top"])).cut(cyl(16.5, 13, x, y, v["z_piv_top"] + P.T_TAPA - 13))
    return c


def bolts(v):
    s = None
    for k in range(P.N_BOLT):
        a = math.radians(30 + 60 * k)
        x, y = P.BOLT_PCD / 2 * math.cos(a), P.BOLT_PCD / 2 * math.sin(a)
        b = cyl(10, 45, x, y, v["z_piv_top"] + P.T_TAPA - 13 - 32).union(cyl(15, 20, x, y, v["z_piv_top"] + P.T_TAPA - 13))
        s = b if s is None else s.union(b)
    return s


def seal(v):
    r = P.D_DISC / 2
    z0 = P.TB
    h = v["z_disc_bot"] + P.TP_BOT - z0
    rub = cyl(r + P.SEAL_T, h, z=z0).cut(cyl(r, h, z=z0))
    zb = v["z_disc_bot"] + P.TP_BOT / 2 - P.BAR_W / 2
    bar = cyl(r + P.SEAL_T + P.BAR_T, P.BAR_W, z=zb).cut(cyl(r + P.SEAL_T, P.BAR_W, z=zb))
    return rub, bar


def pads():
    s = None
    for _, _, x, y in P.pad_positions():
        c = cyl(P.D_PAD / 2, P.T_PAD, x, y, P.TB - P.H_POCKET)
        s = c if s is None else s.union(c)
    return s


def inox(v, rin, rout):
    z = v["z_disc_bot"] - P.INOX_T
    return cyl(rout / 2, P.INOX_T, z=z).cut(cyl(rin / 2, P.INOX_T, z=z))


def push_geom(v):
    """Lado derecho (x>0), empuje +Y, trinquete tomando la barra a -5°. Devuelve coordenadas clave."""
    a = math.radians(-P.BAR_ANG0)
    xb, yb = P.R_BAR * math.cos(a), P.R_BAR * math.sin(a)
    return xb, yb, yb - P.EYE_OFF


def push_set(v, sx):
    xb, yb, ye = push_geom(v)
    za = v["z_axis"]
    x0, x1 = P.SHOE_X0, P.SHOE_X1
    xc = P.X_CYL
    yf, yr = yb + P.SHOE_FRONT, yb + P.SHOE_FRONT - P.SHOE_L
    shoe = box(x0, x1, yr, yf, P.TB, v["shoe_top"])
    shoe = shoe.cut(box(xc - 20.5, xc + 20.5, yr, yf, P.TB, P.TB + P.RAIL_H + 1))
    shoe = shoe.cut(box(x0, x1, yb - P.PAWL_W - 0.5, yb + 0.5, za - P.PAWL_H / 2 - 0.5, za + P.PAWL_H / 2 + 0.5))
    shoe = shoe.cut(box(xc - 40, xc + 40, yr, yr + 110, za - 65, v["shoe_top"]))
    shoe = shoe.cut(cq.Workplane("YZ").workplane(offset=x0 - 5).center(ye, za).circle((P.D_PIN_CYL + 1) / 2).extrude(x1 - x0 + 10))
    pawl = box(P.PAWL_TIP, P.PAWL_TIP + P.PAWL_L, yb - P.PAWL_W, yb, za - P.PAWL_H / 2, za + P.PAWL_H / 2)
    pawl = pawl.cut(cyl(P.SEAT_R, P.PAWL_H, xb, yb, za - P.PAWL_H / 2))
    wedge = (cq.Workplane("XY").workplane(offset=za - P.PAWL_H / 2)
             .polyline([(P.PAWL_TIP - 1, yb - P.PAWL_W - 1), (P.PAWL_TIP + 60, yb - P.PAWL_W - 1), (P.PAWL_TIP - 1, yb - P.PAWL_W + 35)]).close().extrude(P.PAWL_H))
    pawl = pawl.cut(wedge)
    ybp = -P.Y_BRK
    def ycyl(r, y0, y1):
        lo, hi = min(y0, y1), max(y0, y1)
        return cq.Workplane("XZ").workplane(offset=-hi).center(xc, za).circle(r).extrude(hi - lo)
    body = ycyl(P.D_CYL / 2, ybp + 70, ybp + 70 + 300)
    rod = ycyl(P.D_ROD / 2, ybp + 370, ye - 50)
    eyes = None
    for y_ in (ybp, ye):
        e = cq.Workplane("YZ").workplane(offset=xc - P.EYE_W / 2).center(y_, za).circle(P.EYE_D / 2).extrude(P.EYE_W)
        eyes = e if eyes is None else eyes.union(e)
    cylinder = body.union(rod).union(eyes)
    pins = None
    for y_, ln in ((ybp, P.CHEEK_GAP + 2 * P.CHEEK_T + 40), (ye, x1 - x0 + 40)):
        pp = cq.Workplane("YZ").workplane(offset=xc - ln / 2).center(y_, za).circle(P.D_PIN_CYL / 2).extrude(ln)
        pins = pp if pins is None else pins.union(pp)
    cylinder = cylinder.cut(pins)
    out = [shoe, pawl, cylinder, pins]
    if sx < 0:
        out = [o.rotate((0, 0, 0), (0, 0, 1), 180) for o in out]
    return out


def build(kind):
    v = P.variant(kind)
    parts = []  # (pos, name, shape, color)
    b = base_plate(v)
    parts.append((1, "Placa base", b, C["base"]))
    brk = None
    for sx in (1, -1):
        for sy in (1, -1):
            k = bracket(v, sx, sy)
            brk = k if brk is None else brk.union(k)
    parts.append((2, "Mensulas de reaccion", brk, C["base"]))
    lg = None
    for sx in (1, -1):
        for sy in (1, -1):
            k = lug(v, sx, sy)
            lg = k if lg is None else lg.union(k)
    parts.append((3, "Orejas de izaje", lg, C["base"]))
    parts.append((4, "Disco giratorio", disc(v), C["disc"]))
    parts.append((5, "Pivote", pivot(v), C["pin"]))
    parts.append((6, "Buje bronce", bushing(v), C["bronze"]))
    parts.append((7, "Tapa retenedora", cap(v), C["steel"]))
    parts.append((8, "Pernos M20", bolts(v), C["pin"]))
    sh, pw, cy_, pn = [], [], [], []
    for sx in (1, -1):
        a_, b_, c_, d_ = push_set(v, sx)
        sh.append(a_); pw.append(b_); cy_.append(c_); pn.append(d_)
    parts.append((9, "Cilindros 50 t", cy_[0].union(cy_[1]), C["cyl"]))
    parts.append((10, "Carros de empuje", sh[0].union(sh[1]), C["steel"]))
    parts.append((11, "Trinquetes", pw[0].union(pw[1]), C["pin"]))
    parts.append((12, "Pasadores D70", pn[0].union(pn[1]), C["pin"]))
    parts.append((22, "Guias de carro", rails(v), C["base"]))
    rub, bar = seal(v)
    parts.append((14, "Faldon NBR", rub, C["nbr"]))
    parts.append((15, "Fleje de apriete", bar, C["steel"]))
    if kind == "U":
        parts.append((19, "Pastillas UHMW", pads(), C["uhmw"]))
        parts.append((20, "Pista inox A", inox(v, *P.INOX_A), C["inox"]))
        parts.append((21, "Pista inox B", inox(v, *P.INOX_B), C["inox"]))
    return v, parts


if __name__ == "__main__":
    import sys, time, json
    for kind in sys.argv[1:] or ["U", "S"]:
        t = time.time()
        v, parts = build(kind)
        assy = cq.Assembly(name=v["code"])
        mass = {}
        for pos, name, shp, col in parts:
            assy.add(shp, name=f"P{pos:02d}_{name.replace(' ', '_')}", color=col)
            vol = shp.val().Volume()
            dens = {6: 7.6e-6, 19: 0.94e-6 if kind == "U" else 0, 14: 1.2e-6}.get(pos, 7.85e-6)
            mass[pos] = round(vol * dens, 1)
        out = f"/home/claude/tt/out/{v['code']}"
        assy.save(out + ".step")
        assy.save(out + ".glb")
        json.dump(mass, open(out + "_mass.json", "w"))
        print(kind, round(time.time() - t, 1), "s", mass, "total", round(sum(mass.values()), 0))
```

### tt/iso.py
`tt/iso.py` — 19 líneas

```python
import sys, cadquery as cq, model3d as M
from cadquery.occ_impl.exporters.svg import getSVG
def iso_svg(kind, path, explode=0.0, dirn=(1.0,-1.6,1.1), w=900, h=650, hidden=False, only=None):
    v, parts = M.build(kind)
    shapes=[]
    for pos,name,shp,col in parts:
        if only and pos not in only: continue
        s = shp.val()
        if explode:
            dz = {1:0,2:0,3:0,19:0.4,20:1.4,21:1.4,4:1.6,6:1.6,14:1.6,15:1.6,5:0.0,7:3.2,8:3.6,9:2.6,10:2.6,11:3.0,12:2.6}.get(pos,0)
            s = s.translate(cq.Vector(0,0,dz*explode))
        shapes.append(s)
    comp = cq.Compound.makeCompound(shapes)
    svg = getSVG(comp, opts=dict(width=w, height=h, marginLeft=10, marginTop=10, projectionDir=dirn, showAxes=False, showHidden=hidden, strokeWidth=-1.0, strokeColor=(0,0,0), hiddenColor=(120,120,120)))
    open(path,'w').write(svg)
if __name__=='__main__':
    import time
    for k in ('U','S'):
        t=time.time(); iso_svg(k, f'out/iso_{k}.svg'); iso_svg(k, f'out/isoexp_{k}.svg', explode=250); print(k, time.time()-t)
```

### tt/sheet1.py
`tt/sheet1.py` — 224 líneas

```python
"""Lámina 1: Conjunto general (planta, cortes, detalles, lista de materiales, notas)."""
import math
import cadquery as cq
import params as P, model3d as M, hlr, draw
from common import Place, bom, notes_general, fmt_kg, total_mass, bbox

PUSH = (9, 10, 11, 12, 13, 22)


def nf(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def sheet1(kind):
    v, parts = M.build(kind)
    v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 1, 4, "CONJUNTO GENERAL – CORTES Y DETALLES", "INDICADA")
    shapes = [(p, s.val()) for p, n, s, c in parts]
    U = kind == "U"
    zt = v["z_disc_top"]

    # ================= PLANTA 1:10 =================
    allc = cq.Compound.makeCompound([s for _, s in shapes])
    vis, _ = hlr.hlr(allc, "top", tol=4)
    T = Place((160, 448), 0.1)
    T.polys(S, vis)
    S.centerlines(T((0, 0)), 108, 0)
    S.circle(T((0, 0)), P.R_IDX * 0.1, "EJE")
    S.circle(T((0, 0)), 80.0, "FANT")
    S.leader(T((-566, 566)), (T((0, 0))[0] - 62, T((0, 0))[1] + 124), "ZONA DE CARGA Ø1600 MÁX.", h=2.3)
    if U:
        for _, _, x, y in P.pad_positions():
            S.circle(T((x, y)), P.D_PAD / 2 * 0.1, "OCU")
    # dims
    S.dim(T((-1200, 1000)), T((1200, 1000)), 9, "2400")
    S.dim(T((-1200, -1000)), T((-1200, 1000)), -7, "2000", orient="v")
    S.dim(T((0, -1000)), T((P.X_CYL, -1000)), -7, nf(P.X_CYL))
    S.dim(T((-P.X_CYL, -1000)), T((0, -1000)), -7, nf(P.X_CYL))
    S.dim(T((1200, 0)), T((1200, -P.Y_BRK)), 6, nf(P.Y_BRK), orient="v")
    S.dim(T((1200, 0)), T((1200, P.Y_BRK)), 6, nf(P.Y_BRK), orient="v")
    S.dim(T((-600, 1000)), T((600, 1000)), 3.5, "1200")
    S.leader(T((P.R_IDX * math.cos(math.radians(125)), P.R_IDX * math.sin(math.radians(125)))),
             (T((0, 0))[0] + 40, T((0, 0))[1] + 124), "36 barras Ø70 s/ Ø1880 (10°) – ver det. E", h=2.3)
    if U:
        S.balloon(T((550 * math.cos(math.radians(-165)), 550 * math.sin(math.radians(-165)))), T((-1290, -400)), 19)
    # flecha de giro
    c = T((0, 0))
    S.arc(c, 52, 200, 245, "VIS")
    a = math.radians(245)
    S.arrow((c[0] + 52 * math.cos(a), c[1] + 52 * math.sin(a)), a + math.pi / 2, size=4, w=1.4)
    S.text("GIRO ANTIHORARIO", (c[0] - 40, c[1] - 30), 2.3, "MIDDLE_CENTER")
    # marcas de corte
    S.line(T((-1270, 0)), T((-1220, 0)), "VIS"); S.line(T((1220, 0)), T((1270, 0)), "VIS")
    S.section_mark(T((-1270, 0)), 90, "A"); S.section_mark(T((1270, 0)), 90, "A")
    S.line(T((P.X_CYL, 1030)), T((P.X_CYL, 1080)), "VIS"); S.line(T((P.X_CYL, -1030)), T((P.X_CYL, -1080)), "VIS")
    S.section_mark(T((P.X_CYL, 1080)), 180, "B"); S.section_mark(T((P.X_CYL, -1080)), 180, "B")
    S.detail_circle(T((1000, -150)), 15, "E")
    # globos
    bl = [(1, (-1100, -930), (-1290, -1060)), (2, (P.X_CYL + 60, 760), (1290, 1060)), (3, (-600, 950), (-760, 1150)),
          (4, (-420, 300), (-1290, 300)), (7, (60, 60), (330, 350)), (9, (P.X_CYL, -560), (1290, -560)),
          (10, (-P.X_CYL, 200), (-1290, 160)), (12, (-P.X_CYL, P.Y_BRK), (-1290, 760)),
          (22, (-P.X_CYL, -300), (-1290, -200)), (17, (424, 424), (560, 560)), (15, (-707, -707), (-1290, -760))]
    for n, p, q in bl:
        S.balloon(T(p), T(q), n)
    S.view_title((T((0, 0))[0], 322), "PLANTA", "ESCALA 1:10")

    # ================= CORTE A-A 1:10 =================
    vis, hid, hat = hlr.section(shapes, "front", (0, 0, 0), (0, 1, 0), tol=4)
    A = Place((160, 252), 0.1)
    A.polys(S, vis); A.hatches(S, hat)
    S.line(A((0, -15)), A((0, zt + 160)), "EJE")
    S.dim(A((1000, 0)), A((1000, P.TB)), 6, "80", orient="v")
    S.dim(A((1000, P.TB)), A((1000, zt)), 6, nf(zt - P.TB), orient="v")
    S.dim(A((-1200, 0)), A((-1200, zt)), -6, nf(zt), orient="v")
    S.dim(A((-1200, 0)), A((-1200, v["z_axis"])), -14, nf(v["z_axis"]), orient="v")
    S.detail_circle(A((0, 100)), 18, "C")
    S.detail_circle(A((800, 120)), 18, "D")
    S.view_title((A((0, 0))[0], 232), "CORTE A-A", "ESCALA 1:10")

    # ================= CORTE B-B 1:5 =================
    vis, hid, hat = hlr.section(shapes, "right", (P.X_CYL, 0, 0), (-1, 0, 0), tol=2)
    win = (-1010, -5, 160, v["shoe_top"] + 40)
    visc = hlr.clip_polys(vis, win); hatc = hlr.clip_hatch(hat, win)
    Bp = Place((48, 110), 0.2, (-1010, 0))
    Bp.polys(S, visc); Bp.hatches(S, hatc)
    x = Bp((160, 0))[0]
    S.pline([(x, Bp((0, -5))[1]), (x, Bp((0, 120))[1]), (x + 3, Bp((0, 140))[1]), (x - 3, Bp((0, 160))[1]), (x, Bp((0, 180))[1]), (x, Bp((0, v["shoe_top"] + 40))[1])], "FINA")
    za = v["z_axis"]
    yb = -P.Y_BRK
    xbar, yi, ye = M.push_geom(v)
    S.line(Bp((-1010, za)), Bp((160, za)), "EJE")
    S.dim(Bp((yb, za)), Bp((ye, za)), 24, f"{ye - yb:.0f} (L0 {P.L0_CYL:.0f} + 36 libre)")
    S.dim(Bp((ye, za)), Bp((yi, za)), 24, nf(P.EYE_OFF))
    S.dim(Bp((yb, 0)), Bp((0, 0)), -10, nf(P.Y_BRK))
    S.dim(Bp((yi, 0)), Bp((0, 0)), -10, nf(-yi, 1))
    S.dim(Bp((160, 0)), Bp((160, za)), 6, nf(za), orient="v")
    S.dim(Bp((-1000, 0)), Bp((-1000, P.TB)), -5, "80", orient="v")
    S.dim(Bp((-1000, P.TB)), Bp((-1000, P.TB + v["H_cheek"])), -5, nf(v["H_cheek"]), orient="v")
    S.leader(Bp((40, za + 10)), (Bp((175, 0))[0], Bp((0, za + 55))[1]), "EMPUJE → (carrera 200 = 10°)", h=2.3)
    for n, p, q in [(2, (-940, 120), (-960, 330)), (9, (-600, za + 60), (-600, za + 170)), (12, (yb, za), (-800, za + 170)),
                    (10, (-250, v["shoe_top"] - 20), (-330, za + 170)), (11, (yi - 40, za + 30), (-120, za + 170)),
                    (22, (-300, P.TB + 15), (-350, -40)), (4, (60, zt - 15), (110, za + 170)), (1, (-800, 40), (-800, -40)),
                    (14, (-150, P.TB + 10), (-150, -40))]:
        S.balloon(Bp(p), Bp(q), n)
    S.view_title((Bp((-430, 0))[0], 82), f"CORTE B-B (eje cilindro y carro, x = +{P.X_CYL:.0f})", "ESCALA 1:5")

    # ================= DETALLES 1:2 =================
    nopush = [(p, s) for p, s in shapes if p not in PUSH + (2, 3)]
    vis, hid, hat = hlr.section(nopush, "front", (0, 0, 0), (0, 1, 0), tol=1)
    # --- C: pivote
    winC = (-240, -5, 240, zt + 12)
    C = Place((445, 438), 0.5)
    C.polys(S, hlr.clip_polys(vis, winC)); C.hatches(S, hlr.clip_hatch(hat, winC))
    S.line(C((0, -15)), C((0, zt + 25)), "EJE")
    S.dim(C((-75, -5)), C((75, -5)), -6, "Ø150 H7/p6")
    S.dim(C((-95, v["z_disc_bot"])), C((95, v["z_disc_bot"])), -14 - (5 * 0.5 + v["z_disc_bot"] * 0.5) + 10 - 10 if False else -10 - v["z_disc_bot"] * 0.5 - 2.5 - 6 , "Ø190 H7/s6")
    S.dim(C((-130, zt)), C((130, zt)), 8, "Ø260")
    S.dim(C((-120, v["z_piv_top"] + P.T_TAPA)), C((120, v["z_piv_top"] + P.T_TAPA)), 3, "Ø240", txt_shift=0)
    S.dim(C((240, v["z_disc_bot"])), C((240, v["z_buje_top"])), 5, nf(P.L_BUJE), orient="v")
    S.dim(C((240, v["z_cb_floor"])), C((240, zt)), 5, "25", orient="v")
    S.dim(C((240, 0)), C((240, P.TB)), 5, "80", orient="v")
    S.dim(C((-240, v["z_piv_top"])), C((-240, v["z_piv_top"] + P.T_TAPA)), -5, "20", orient="v")
    S.dim(C((-240, v["z_cb_floor"])), C((-240, v["z_piv_top"])), -14, "3", orient="v", outside=True)
    S.leader(C((50, v["z_piv_top"] + 10)), (C((0, 0))[0] + 40, C((0, zt + 30))[1]), "6× M20 s/ PCD 100", h=2.3)
    for n, p, q in [(5, (-40, 40), (-275, 30)), (6, (-85, v["z_disc_bot"] + 40), (-275, 100)),
                    (7, (-110, v["z_piv_top"] + 10), (-215, zt + 22)), (8, (-50, v["z_piv_top"] + 5), (-145, zt + 22)),
                    (4, (180, zt - 30), (275, zt - 15)), (1, (180, 40), (275, 30))]:
        S.balloon(C(p), C(q), n)
    S.leader(C((-60, 2)), (C((0, 0))[0] - 70, C((0, -50))[1]), "Sold. sello chaflán 5×45°, esmerilar", h=2.2)
    if U:
        S.leader(C((160, P.TB + 4)), (C((0, 0))[0] + 70, C((0, -50))[1]), "Holgura g = 8 (5 pastilla + 3 inox)", h=2.2)
    else:
        S.leader(C((160, P.TB)), (C((0, 0))[0] + 70, C((0, -50))[1]), "Contacto pleno + película grafito", h=2.2)
    S.view_title((C((0, 0))[0], 384), "DETALLE C – PIVOTE", "ESCALA 1:2")

    # --- D: borde
    winD = (585, -5, 1018, zt + 12)
    Dp = Place((325, 222), 0.5, (585, 0))
    Dp.polys(S, hlr.clip_polys(vis, winD)); Dp.hatches(S, hlr.clip_hatch(hat, winD))
    zb_ = v["z_disc_bot"]
    S.dim(Dp((1000, zt)), Dp((1000, zt - P.TP_TOP)), 18, "30", orient="v")
    S.dim(Dp((1000, zt - P.TP_TOP)), Dp((1000, zb_ + P.TP_BOT)), 18, "100", orient="v")
    S.dim(Dp((1000, zb_ + P.TP_BOT)), Dp((1000, zb_)), 18, "30", orient="v")
    S.dim(Dp((1000, zt)), Dp((1000, zb_)), 28, "160", orient="v")
    S.dim(Dp((1000, P.TB)), Dp((1000, 0)), 18, "80", orient="v")
    S.text("Nervio radial 4e (cortado)", Dp((700, zb_ + P.TP_BOT + 50)), 2.2, "MIDDLE_LEFT")
    S.dim(Dp((585, zt)), Dp((1000, zt)), 6, "R1000 (a eje)")
    if U:
        S.dim(Dp((650, P.TB + 5)), Dp((820, P.TB + 5)), 22, "Ø170")
        S.dim(Dp((585, P.TB - 5)), Dp((585, P.TB)), -5, "5", orient="v", outside=True)
        S.dim(Dp((630, P.TB)), Dp((630, P.TB + 5)), -5, "5", orient="v", outside=True)
        S.dim(Dp((840, v["z_disc_bot"] - 3)), Dp((840, v["z_disc_bot"])), 3, "3", orient="v", outside=True)
        S.dim(Dp((0, P.TB)), Dp((735, P.TB)), 0, "", orient="h") if False else None
        for n, p, q in [(19, (700, P.TB), (690, -40)), (21, (760, v["z_disc_bot"] - 1.5), (790, -40)),
                        (14, (1003, P.TB + 5), (1060, -30)), (15, (1009, zb_ + 15), (1070, zb_ + 60)),
                        (4, (900, zt - 15), (900, zt + 35)), (1, (900, 30), (950, -40))]:
            S.balloon(Dp(p), Dp(q), n)
        S.text("R735 (eje anillo 3)", Dp((620, -30)), 2.2, "MIDDLE_LEFT")
        S.text("Pista inox B R440–R840", Dp((830, -32)), 2.2, "MIDDLE_LEFT")
    else:
        for n, p, q in [(14, (1003, P.TB + 5), (1060, -30)), (15, (1009, zb_ + 15), (1070, zb_ + 60)),
                        (4, (900, zt - 15), (900, zt + 35)), (1, (900, 30), (950, -40))]:
            S.balloon(Dp(p), Dp(q), n)
        S.leader(Dp((700, P.TB)), (Dp((640, 0))[0], Dp((0, -30))[1]), "", lines=["Pos 19: película grafito en ambas", "caras, 2 capas, 50–150 µm c/u"], h=2.2)
    S.view_title((Dp((800, 0))[0], 186), "DETALLE D – BORDE E INTERFAZ DE GIRO", "ESCALA 1:2")

    # --- E: trinquete (corte horizontal en eje del cilindro)
    vis, hid, hat = hlr.section(shapes, "top", (0, 0, za), (0, 0, -1), tol=1, nocut={5, 8})
    winE = (850, -440, 1210, 125)
    E = Place((612, 97), 0.4, (850, -440))
    E.polys(S, hlr.clip_polys(vis, winE)); E.hatches(S, hlr.clip_hatch(hat, winE))
    for k in (-2, -1, 0, 1):
        a_ = math.radians(-P.BAR_ANG0 + 10 * k)
        S.cross(E((P.R_BAR * math.cos(a_), P.R_BAR * math.sin(a_))), 2.5)
    S.line(E((P.X_CYL, -440)), E((P.X_CYL, 125)), "EJE")
    S.dim(E((xbar - 35, yi)), E((xbar + 35, yi)), 0.01 - 52, "Ø70") if False else None
    S.leader(E((xbar + 20, yi + 25)), E((1150, 60)), "Barra Ø70", h=2.1)
    S.dim(E((P.PAWL_TIP, yi)), E((P.PAWL_TIP, yi - P.PAWL_W)), -6, "85", orient="v")
    S.dim(E((P.PAWL_TIP, yi - P.PAWL_W)), E((P.SHOE_X0, yi - P.PAWL_W)), -10, nf(P.SHOE_X0 - P.PAWL_TIP))
    S.dim(E((P.SHOE_X0, yi + P.SHOE_FRONT)), E((P.SHOE_X1, yi + P.SHOE_FRONT)), 22, "130")
    S.dim(E((P.SHOE_X1, yi + P.SHOE_FRONT)), E((P.SHOE_X1, yi + P.SHOE_FRONT - P.SHOE_L)), 6, "300", orient="v")
    S.leader(E((xbar + 30, yi - 22)), E((1225, 40)), "Asiento R36", h=2.1)
    S.leader(E((P.PAWL_TIP + 15, yi - P.PAWL_W + 10)), E((960, -300)), "Chaflán 30°", h=2.1)
    p0 = E((P.SHOE_X1 + 25, -40)); S.line(p0, (p0[0], p0[1] + 30), "VIS"); S.arrow((p0[0], p0[1] + 30), math.pi / 2, size=3.5, w=1.2)
    S.text("EMPUJE", (p0[0] + 2, p0[1] + 12), 2.2, "MIDDLE_LEFT")
    for n, p, q in [(10, (1110, -200), (1300, -200)), (11, (1000, yi - 40), (1300, yi - 40)), (12, (P.X_CYL, ye), (1300, ye)),
                    (4, (880, -20), (880, 60))]:
        S.balloon(E(p), E(q), n)
    S.view_title((E((1030, 0))[0], 84), "DETALLE E – TRINQUETE Y BARRA (corte horiz. en eje)", "ESCALA 1:2,5")

    # ================= BOM =================
    rows = []
    for pos, desc, q, mat, mu in bom(v):
        rows.append([pos, desc, q, mat, fmt_kg(mu) if mu else "—"])
    y = S.table(598, 584, [("POS", 10, "C"), ("DESCRIPCIÓN", 88, "L"), ("CANT.", 13, "C"), ("MATERIAL / NORMA", macro_w := 81, "L"), ("kg/u", 21, "R")], rows, rh=5.4, h=2.15)
    S.text(f"MASA TOTAL APROX. DEL CONJUNTO: {fmt_kg(total_mass(v))} kg (sin carga, incl. cilindros)", (600, y - 4), 2.4, "TOP_LEFT", bold=True)
    S.text("LISTA DE MATERIALES", (598 + 106, 588.5), 3.2, "BOTTOM_CENTER", bold=True) if False else None

    # ================= NOTAS =================
    S.mtext(notes_general(v), (598, y - 12), h=2.1, ls=1.62, bold_first=True)

    # datos técnicos
    U_ = U
    dt = [["Capacidad nominal (WLL)", "500 tf (4 903 kN)"],
          ["Altura total (sup. disco)", f"{zt:.0f} mm"],
          ["Interfaz de giro", "UHMW-PE / inox 316L" if U_ else "Acero/acero + grafito"],
          ["Presión media interfaz (φd)", "6,99 MPa (pastillas)" if U_ else "1,73 MPa (contacto pleno)"],
          ["Presión máx. e = 150 mm", "11,08 MPa" if U_ else "2,77 MPa"],
          ["μ de diseño accionamiento", "0,15 (FU 0,53)" if U_ else "0,15–0,20 (FU 0,59–0,79)"],
          ["Fuerza cilindro (700 bar)", "2 × 445 kN"],
          ["Rotación por ciclo", "10° (36 libre + 164 de empuje)"]]
    S.table(25, 62, [("DATOS TÉCNICOS", 62, "L"), ("", 58, "L")], dt, rh=5.0, h=2.15, header_h=5.5)
    return S, v


if __name__ == "__main__":
    import sys
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet1(k)
        S.save(f"out/{v['code']}-01.dxf", f"out/{v['code']}-01.pdf")
        import pymupdf
        d = pymupdf.open(f"out/{v['code']}-01.pdf"); d[0].get_pixmap(dpi=75).save(f"out/{v['code']}-01.png")
        print("ok", k)
```

### tt/sheet2.py
`tt/sheet2.py` — 127 líneas

```python
"""Lámina 2: isométricas (conjunto y explosionada), montaje y operación."""
import math
import cadquery as cq
import params as P, model3d as M, hlr, draw
from common import Place, bbox, pressure_bar

EXP = {17: 2.1, 19: 0.4, 20: 2.1, 21: 2.1, 4: 2.1, 6: 2.1, 14: 2.1, 15: 2.1, 16: 2.1, 7: 3.6, 8: 4.1, 9: 3.1, 10: 3.1, 11: 3.1, 12: 3.1}


def anchors(v):
    zt, zdb, za = v["z_disc_top"], v["z_disc_bot"], v["z_axis"]
    X = P.X_CYL
    a = {1: (300, -1000, 40), 2: (X + 80, -P.Y_BRK, P.TB + v["H_cheek"] - 20), 3: (620, -925, P.TB + 60),
         4: (-200, -700, zt), 5: (0, -75, 60), 6: (0, -95, zdb + 40), 7: (0, -120, v["z_piv_top"] + 20),
         8: (50, 0, v["z_piv_top"] + 30), 9: (X, -600, za + 60), 10: (P.SHOE_X1, -250, za),
         11: (1000, -120, za + 45), 12: (X + 100, -P.Y_BRK, za), 14: (711, -711, P.TB + 15),
         15: (-300, -965.4, zdb + 15), 17: (424, -424, zt), 22: (X, 250, P.TB + 30)}
    if v["kind"] == "U":
        a.update({19: (520, -520, P.TB + 5), 20: (-560, -560, zdb), 21: (690, -690, zdb)})
    return a


def sheet2(kind):
    v, parts = M.build(kind)
    v["proj"] = P.PROJ
    S = draw.Sheet()
    S.frame(v, 2, 4, "ISOMÉTRICAS – MONTAJE Y OPERACIÓN", "1:10")
    U = kind == "U"
    shapes = [(p, s.val()) for p, n, s, c in parts]
    view = "iso"
    # ------ conjunto
    comp = cq.Compound.makeCompound([s for _, s in shapes])
    vis, _ = hlr.hlr(comp, view, tol=5)
    x0, y0, x1, y1 = bbox(vis)
    s = 1 / 10
    T = Place((178, 462), s, ((x0 + x1) / 2, (y0 + y1) / 2))
    T.polys(S, vis)
    S.view_title((178, 352), "VISTA ISOMÉTRICA – CONJUNTO", "ESCALA 1:10")
    # ------ explosionada
    ex = 420.0
    sh2 = []
    for p, sh in shapes:
        sh2.append((p, sh.translate(cq.Vector(0, 0, EXP.get(p, 0) * ex))))
    comp2 = cq.Compound.makeCompound([sh for _, sh in sh2])
    vis2, _ = hlr.hlr(comp2, view, tol=5)
    x0, y0, x1, y1 = bbox(vis2)
    E = Place((488, 335), s, ((x0 + x1) / 2, (y0 + y1) / 2))
    E.polys(S, vis2)
    cx = 488
    # globos en dos columnas
    an = anchors(v)
    pts = []
    for pos, p3 in an.items():
        p3 = (p3[0], p3[1], p3[2] + EXP.get(pos, 0) * ex)
        pts.append((pos, E(hlr.proj_pt(p3, view))))
    left = sorted([q for q in pts if q[1][0] < cx], key=lambda t: -t[1][1])
    right = sorted([q for q in pts if q[1][0] >= cx], key=lambda t: -t[1][1])
    for col, xb in ((left, 338), (right, 640)):
        n = len(col)
        ytop = 545
        for i, (pos, pp) in enumerate(col):
            yb = min(pp[1], ytop - i * 0) if False else None
        ys = []
        for i, (pos, pp) in enumerate(col):
            y = pp[1]
            if ys and y > ys[-1] - 11:
                y = ys[-1] - 11
            ys.append(y)
        for (pos, pp), y in zip(col, ys):
            S.balloon(pp, (xb, y), pos)
    S.view_title((488, 92), "VISTA ISOMÉTRICA EXPLOSIONADA", "ESCALA 1:10 – globos según lista de materiales lámina 1")
    # ------ textos
    pbar = pressure_bar(0.10 if U else 0.12, v)
    mont = ["SECUENCIA DE MONTAJE",
            "1. Placa base pos 1 (con pos 2 y 3 soldadas, relevada y mecanizada) sobre apoyo nivelado (≤ 0,5 %).",
            "2. Pivote pos 5 calado en caliente en pos 1 (H7/p6; calentar pos 1 local a ≤ 200 °C o enfriar pos 5),",
            "   soldadura de sello inferior y esmerilado a ras.",
            ("3. Limpiar alojamientos; colocar 34 pastillas pos 19 (ajuste deslizante, sin adhesivo)." if U else
             "3. Desengrasar caras de contacto de pos 1 y pos 4; aplicar 2 capas pos 19 (24 h entre capas, 10–38 °C)."),
            ("4. Buje pos 6 prensado en el cubo 4c (H7/s6). Pistas pos 20/21 soldadas y pulidas previamente en pos 4." if U else
             "4. Buje pos 6 prensado en el cubo 4c (H7/s6). Verificar planitud ≤ 0,20 mm de ambas caras antes del film."),
            "5. Izar pos 4 con 4 cáncamos pos 18 (M30) y bajar centrado sobre pos 5 sin golpear la interfaz.",
            "6. Tapa pos 7 con 6 pernos pos 8 (M20 10.9, par según tabla, arandela Nord-Lock). Juego vertical 3 mm.",
            "7. Faldón pos 14 y fleje pos 15 con 36 pernos pos 16. Retirar cáncamos y colocar tapones pos 17.",
            "8. Carros pos 10 sobre guías pos 22 con trinquete pos 11 y resorte pos 13 (trinquete hacia el sentido de giro);",
            "   cilindros pos 9 entre ménsula activa y carro con pasadores pos 12 + clips. Mangueras 700 bar (CR400).",
            "9. Prueba en vacío: 2 ciclos completos; luego ensayo de carga según nota 10, lámina 1."]
    oper = ["SECUENCIA DE OPERACIÓN (POR CICLO)",
            "a) Extender ambos cilindros a la vez (colector común): 36 mm libres, el trinquete toma la barra y la carga",
            "   gira 10° hasta fin de carrera (200 mm).",
            "b) Retraer a fondo: el chaflán del trinquete pasa sobre la barra siguiente y el resorte lo engancha.",
            "   Verificar visualmente el enganche de ambos trinquetes antes del ciclo siguiente.",
            f"c) Registrar presión de giro. Esperada ≈ {pbar:,.0f} bar. Detener si supera 600 bar.".replace(",", "."),
            "d) Para invertir el sentido: retirar cilindros y carros, girar cada carro 180° y usar la ménsula opuesta.",
            "e) No operar con viento > 50 km/h ni con la carga sin arriostrar. Personal fuera del radio de giro.",
            "",
            "MANTENIMIENTO",
            ("• Cada uso: limpiar pistas inox pos 20/21 con paño y alcohol; no usar abrasivos." if U else
             "• Cada uso: inspeccionar film pos 19; si hay óxido o metal desnudo > 10 %: limpiar a metal y reaplicar."),
            ("• Reemplazar pastillas con resalte < 3,0 mm o con fisuras. Retirar con varilla por agujero Ø10." if U else
             "• No aplicar grasa en ambiente seco o con polvo (la grasa atrapa partículas)."),
            "• Guardar bajo techo, con el disco calzado y el faldón protegido del sol."]
    y = S.mtext(mont, (26, 330), h=2.3, ls=1.6, bold_first=True)
    S.mtext(oper, (26, y - 7), h=2.3, ls=1.6, bold_first=True)
    fits = [["Pivote 5 / placa base 1", "Ø150 H7/p6", "Calado en caliente"],
            ["Pivote 5 / buje 6", "Ø150 H7/f7", "Giratorio"],
            ["Buje 6 / disco 4", "Ø190 H7/s6", "Prensado"],
            ["Trinquete 11 / alojamiento carro 10", "85×90 H9/f8", "Deslizante"],
            ["Carro 10 / guía 22", "Ranura 41 H11 / 40 h9", "Guiado"],
            ["Barra 4f / agujeros planchas 4a, 4b", "Ø70 / Ø71", "Soldada"],
            ["Pasadores 12 / ménsula, carro", "Ø70 H9/f8 (rótula GE70)", "Deslizante"],
            ["Pernos 8 M20 10.9 (VDI 2230, μ 0,12)", "540 N·m", "Nord-Lock"],
            ["Pernos 16 M8 A2-70", "18 N·m", "Antigripante"],
            ["Tapones 17 M30", "Manual + fijador media", "Ras con disco"]]
    if U:
        fits.insert(5, ["Pastilla 19 / alojamiento", "Ø170 -0,1/-0,2 – Ø170,6 +0,1/0", "Holgura térmica"])
    S.table(26, 140, [("AJUSTES Y PARES DE APRIETE", 80, "L"), ("VALOR", 58, "L"), ("OBS.", 32, "L")], fits, rh=5.0, h=2.1)
    return S, v


if __name__ == "__main__":
    import sys, pymupdf
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet2(k)
        S.save(f"out/{v['code']}-02.dxf", f"out/{v['code']}-02.pdf")
        pymupdf.open(f"out/{v['code']}-02.pdf")[0].get_pixmap(dpi=75).save(f"out/{v['code']}-02.png")
        print("ok", k)
```

### tt/sheet3.py
`tt/sheet3.py` — 273 líneas

```python
"""Lámina 3: fabricación placa base (conj. soldado 1+2+3) y disco (4) [+ pistas inox 20/21]."""
import math
import params as P, draw
from common import Place, fmt_kg

def nf(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def sheet3(kind):
    v = P.variant(kind); v["proj"] = P.PROJ
    U = kind == "U"
    S = draw.Sheet()
    S.frame(v, 3, 4, "FABRICACIÓN – PLACA BASE (1+2+3) Y DISCO (4)", "INDICADA")
    hc = v["H_cheek"]; zax = v["z_axis"] - P.TB

    # =================== PLACA BASE – PLANTA 1:10 ===================
    T = Place((158, 440), 0.1)
    c = T((0, 0))
    S.rect(*T((-1200, -1000)), *T((1200, 1000)))
    for sx_ in (1, -1):
        S.rect(*T((sx_ * P.X_CYL - 20, -P.RAIL_L / 2)), *T((sx_ * P.X_CYL + 20, P.RAIL_L / 2)))
        S.line(T((sx_ * P.X_CYL, -P.RAIL_L / 2 - 30)), T((sx_ * P.X_CYL, P.RAIL_L / 2 + 30)), "EJE")
    S.circle(c, 7.5); S.centerlines(c, 106, 0)
    S.circle(c, 100, "FANT")
    S.text("contorno disco Ø2000", T((-640, 840)), 2.0, "BOTTOM_LEFT")
    if U:
        for r, n, a0 in P.RINGS:
            S.circle(c, r * 0.1, "EJE")
        for _, _, x, y in P.pad_positions():
            S.circle(T((x, y)), P.D_POCKET / 2 * 0.1)
            S.circle(T((x, y)), 0.5)
    for sx in (1, -1):
        for sy in (1, -1):
            x0, y0 = sx * P.X_CYL, sy * P.Y_BRK
            for side in (-1, 1):
                xa = x0 + side * P.CHEEK_GAP / 2
                xb = x0 + side * (P.CHEEK_GAP / 2 + P.CHEEK_T)
                S.rect(*T((min(xa, xb), y0 - P.CHEEK_L / 2)), *T((max(xa, xb), y0 + P.CHEEK_L / 2)))
            yb0 = y0 + sy * P.CHEEK_L / 2
            yb1 = yb0 + sy * P.BACK_T
            S.rect(*T((x0 - 80, min(yb0, yb1))), *T((x0 + 80, max(yb0, yb1))))
            S.line(T((x0 - 100, y0)), T((x0 + 100, y0)), "EJE")
            # orejas
            S.rect(*T((sx * P.LUG_X - 20, sy * 850)), *T((sx * P.LUG_X + 20, sy * 1000)))
    S.dim(T((-1200, 1000)), T((1200, 1000)), 9, "2400")
    S.dim(T((-1200, -1000)), T((-1200, 1000)), -7, "2000", orient="v")
    S.dim(T((0, -1000)), T((P.X_CYL, -1000)), -6, nf(P.X_CYL)); S.dim(T((-P.X_CYL, -1000)), T((0, -1000)), -6, nf(P.X_CYL))
    S.dim(T((1200, 0)), T((1200, -P.Y_BRK)), 6, nf(P.Y_BRK), orient="v"); S.dim(T((1200, 0)), T((1200, P.Y_BRK)), 6, nf(P.Y_BRK), orient="v")
    S.dim(T((-1105, -P.RAIL_L / 2)), T((-1105, P.RAIL_L / 2)), -5, "850", orient="v")
    S.dim(T((-600, 1000)), T((600, 1000)), 3.5, "1200")
    S.dim(T((600, 850)), T((600, 1000)), -4, "150", orient="v", outside=True)
    S.leader(T((75 * 0.7071, 75 * 0.7071)), (c[0] + 20, c[1] + 40), "Ø150 H7 pasante", h=2.3)
    if U:
        S.leader(T((P.RINGS[2][0], 0)), (c[0] + 40, c[1] - 112), "34× alojam. Ø170,6 +0,1/0 prof. 5 (ver tabla y det. F)", h=2.2)
    S.balloon(T((-500, -500)), T((-1300, -650)), 1)
    S.balloon(T((P.X_CYL + 60, 760)), T((1300, 1080)), 2)
    S.balloon(T((600, 950)), T((450, 1100)), 3)
    S.balloon(T((-P.X_CYL, 200)), T((-1300, 300)), 22)
    S.leader(T((P.X_CYL, 300)), (T((0, 0))[0] + 60, T((0, 0))[1] + 75), "Guía 40×30, filete 8 ambos lados", h=2.1)
    S.view_title((c[0], 316), "POS 1 – PLACA BASE (CONJ. SOLDADO 1+2+3) – PLANTA", "ESCALA 1:10")

    # ----- ELEVACIÓN FRONTAL 1:10
    F = Place((158, 262), 0.1)
    S.rect(*F((-1200, 0)), *F((1200, P.TB)))
    for sx in (1, -1):
        for side in (-1, 1):
            xa = sx * P.X_CYL + side * P.CHEEK_GAP / 2
            xb = sx * P.X_CYL + side * (P.CHEEK_GAP / 2 + P.CHEEK_T)
            S.rect(*F((min(xa, xb), P.TB)), *F((max(xa, xb), P.TB + hc)))
        S.circle(F((sx * P.X_CYL, v["z_axis"])), 3.55, "OCU")
        S.rect(*F((sx * P.LUG_X - 20, P.TB)), *F((sx * P.LUG_X + 20, P.TB + P.LUG_H)))
        S.rect(*F((sx * P.X_CYL - 20, P.TB)), *F((sx * P.X_CYL + 20, P.TB + P.RAIL_H)), "OCU")
    S.line(F((0, -10)), F((0, P.TB + 40)), "EJE")
    S.dim(F((1200, 0)), F((1200, P.TB)), 6, "80", orient="v")
    S.dim(F((-1200, P.TB)), F((-1200, P.TB + hc)), -14, nf(hc), orient="v")
    S.dim(F((-1200, P.TB)), F((-1200, v["z_axis"])), -6, nf(zax), orient="v")
    S.dim(F((-660, P.TB)), F((-660, P.TB + P.LUG_H)), -3, "170", orient="v")
    S.weld(F((P.X_CYL - 60, P.TB)), (F((P.X_CYL, 0))[0] + 14, F((0, -60))[1]), "cjp", "CJP", other=True, note="MEJILLAS pos 2")
    S.weld(F((-P.LUG_X - 20, P.TB)), (F((-P.LUG_X, 0))[0] - 10, F((0, -60))[1]), "fillet", "12", other=True, all_round=True, note="pos 3")
    S.view_title((158, 222), "ELEVACIÓN FRONTAL", "ESCALA 1:10")

    # ----- DETALLE F 1:1 alojamiento (U) / DETALLE F superficie (S)
    if U:
        Fp = Place((62, 140), 1.0, (0, 0))
        x0, x1 = -15, 112
        for out in ([(5, -40), (x1, -40), (x1, 0), (85.3, 0), (85.3, -5), (5, -5)], [(x0, -40), (-5, -40), (-5, -5), (x0, -5)]):
            pts = [Fp(p) for p in out]
            S.pline(pts, "VIS", closed=True)
            S.hatch_poly(pts, scale=0.8)
        pp = [Fp(p) for p in [(x0, -5), (85, -5), (85, 5), (x0, 5)]]
        S.pline(pp, "VIS", closed=True); S.hatch_poly(pp, pattern="ANSI37", scale=0.7)
        S.line(Fp((0, -48)), Fp((0, 14)), "EJE")
        S.pline([Fp((x1, -40)), Fp((x1 + 4, -20)), Fp((x1 - 3, -14)), Fp((x1, 0))], "FINA")
        S.pline([Fp((x0, -40)), Fp((x0 - 3, -25)), Fp((x0 + 3, -12)), Fp((x0, 5))], "FINA")
        S.dim(Fp((0, -40)), Fp((85.3, -40)), -8, "Ø170,6 +0,1/0")
        S.dim(Fp((0, 5)), Fp((85, 5)), 8, "Ø170 -0,1/-0,2")
        S.dim(Fp((112, -5)), Fp((112, 0)), 6, "5 ±0,05", orient="v", outside=True)
        S.dim(Fp((112, 0)), Fp((112, 5)), 18, "5", orient="v", outside=True)
        S.dim(Fp((-15, -5)), Fp((-15, 5)), -5, "10 ±0,1", orient="v", outside=True)
        S.leader(Fp((5, -25)), (Fp((0, 0))[0] + 30, Fp((0, -30))[1]), "Ø10 pasante (extracción)", h=2.2)
        S.finish(Fp((40, -5)), "Ra 3,2")
        S.leader(Fp((85, 4)), (Fp((0, 0))[0] + 95, Fp((0, 24))[1]), "Chaflán 0,5×45°", h=2.2)
        S.text("pos 19", Fp((30, 0.5)), 2.0, "BOTTOM_LEFT")
        S.text("pos 1", Fp((60, -25)), 2.0, "BOTTOM_LEFT")
        S.view_title((Fp((50, 0))[0], 82), "DETALLE F – ALOJAMIENTO DE PASTILLA", "ESCALA 1:1")
        # tabla anillos
        S.table(200, 168, [("ANILLO", 15, "C"), ("R (mm)", 16, "C"), ("N°", 10, "C"), ("ÁNG. INICIAL", 22, "C"), ("PASO", 14, "C")],
                [["1", "300", "6", "30°", "60°"], ["2", "550", "12", "15°", "30°"], ["3", "735", "16", "0°", "22,5°"]], rh=5.2, h=2.2)
        S.text("Ángulos desde eje +X, sentido antihorario (vista en planta).", (200, 141), 2.0, "TOP_LEFT")
        S.text("Tolerancia posición alojamientos: ±0,5 mm.", (200, 137), 2.0, "TOP_LEFT")
    else:
        lines = ["DETALLE F – SUPERFICIE DE CONTACTO (sin escala)",
                 "• Cara superior pos 1 dentro de Ø2000 y cara inferior pos 4: fresado/planeado",
                 "  final después del alivio de tensiones.",
                 "• Planitud ≤ 0,20 mm en Ø2000; rugosidad Ra 1,6–3,2 µm; sin rayas radiales.",
                 "• Bordes de la zona de contacto: chaflán 2×45°; agujero Ø150: chaflán 3×45°.",
                 "• Preparación film pos 19: desengrase con solvente, granallado fino o",
                 "  limpieza mecánica a metal blanco; aplicar dentro de 4 h.",
                 "• Aplicación: brocha/rodillo/airless, 2 capas de 50–150 µm (película seca),",
                 "  24 h entre capas, superficie a 10–38 °C. Curado total 24 h antes de cargar.",
                 "• Controlar espesor con galga de película seca (ISO 2808), 5 lecturas/m².",
                 "• NO pintar con el sistema anticorrosivo las caras de contacto."]
        S.mtext(lines, (26, 205), h=2.3, ls=1.55, bold_first=True)
        S.finish((150, 105), "Ra 1,6–3,2 (ambas caras)")

    # =================== DISCO CAJÓN – PLANTA 1:10 ===================
    import model3d as M, hlr
    D = Place((450, 440), 0.1)
    c = D((0, 0))
    S.circle(c, 100); S.centerlines(c, 106, 0)
    S.circle(c, P.R_BAR * 0.1, "EJE"); S.circle(c, P.R_M30 * 0.1, "EJE")
    for _, x, y in P.idx_positions():
        S.circle(D((x, y)), P.D_BAR / 2 * 0.1)
    for a in P.M30_ANG:
        p = D((P.R_M30 * math.cos(math.radians(a)), P.R_M30 * math.sin(math.radians(a))))
        S.circle(p, 1.5); S.arc(p, 1.25, 0, 270, "FINA")
    S.circle(c, P.HUB_D / 2 * 0.1); S.circle(c, P.D_CB / 2 * 0.1)
    for r in P.RING_R:
        S.circle(c, (r - P.RING_T / 2) * 0.1, "OCU"); S.circle(c, (r + P.RING_T / 2) * 0.1, "OCU")
        n = max(4, int(2 * math.pi * r / 250))
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            ca, sa = math.cos(a), math.sin(a)
            S.line(D(((r - 11) * ca, (r - 11) * sa)), D(((r + 11) * ca, (r + 11) * sa)), "FINA")
    for k in range(P.N_RIB):
        a = math.radians(360 / P.N_RIB * k); ca, sa = math.cos(a), math.sin(a)
        for off in (-P.RIB_T / 2, P.RIB_T / 2):
            S.line(D((150 * ca - off * sa, 150 * sa + off * ca)), D((P.RIB_R1 * ca - off * sa, P.RIB_R1 * sa + off * ca)), "OCU")
    S.circle(c, 80, "FANT")
    S.dim_dia(c, 100, 140, "Ø2000")
    S.leader(D((P.R_BAR * math.cos(math.radians(45)), P.R_BAR * math.sin(math.radians(45)))), (c[0] + 60, c[1] + 112), "36 barras 4f Ø70 s/ Ø1880, inicio 5°, paso 10°", h=2.2)
    S.leader(D((P.R_M30 * math.cos(math.radians(135)), P.R_M30 * math.sin(math.radians(135)))), (c[0] - 60, c[1] + 112), "4× M30 pasante en 4a s/ Ø1200 a 45°", h=2.2)
    S.leader(D((550 * math.cos(math.radians(20)), 550 * math.sin(math.radians(20)))), (c[0] + 60, c[1] - 112), "Almas 4d R300/R550/R735 e=25 y nervios 4e e=20 (ocultos)", h=2.2)
    S.leader(D((-150 * 0.7071, -150 * 0.7071)), (c[0] - 60, c[1] - 112), "Cubo 4c Ø300 (det. H)", h=2.2)
    S.text("Ranuras de soldadura en 4a sobre almas (trazo fino)", D((-560, -400)), 2.0, "BOTTOM_LEFT")
    S.text("0°", D((1040, 15)), 2.3, "BOTTOM_LEFT")
    S.balloon(D((-300, 500)), D((-1150, 650)), 4)
    S.view_title((c[0], 316), "POS 4 – DISCO CAJÓN (CONJ. SOLDADO 4a–4f) – PLANTA", "ESCALA 1:10")

    # ----- CORTE DISCO 1:10 (plano por barras a 0°/180°)
    dp = M.disc_parts(v)
    lab = {"4a": 41, "4b": 42, "4c": 43, "4d": 44, "4e": 45, "4f": 46}
    parts = [(lab[k], sh.rotate((0, 0, 0), (0, 0, 1), -5).val()) for k, sh in dp.items()]
    vis, hid, hat = hlr.section(parts, "front", (0, 0, 0), (0, 1, 0), tol=1.5, nocut=set())
    hat = [(4, o, h) for _, o, h in hat]
    zb = v["z_disc_bot"]
    C = Place((450, 262), 0.1, (0, zb))
    C.polys(S, vis); C.hatches(S, hat)
    S.line(C((0, zb - 10)), C((0, zb + P.TD + 10)), "EJE")
    S.dim(C((1000, zb)), C((1000, zb + P.TD)), 6, "160", orient="v")
    S.detail_circle(C((0, zb + 80)), 16, "H"); S.detail_circle(C((-940, zb + 80)), 12, "J")
    S.view_title((450, 222), "CORTE DIAMETRAL DISCO (por barras a 0° y 180°)", "ESCALA 1:10")

    # ----- DETALLE H 1:2 (cubo)
    winH = (-230, zb - 5, 230, zb + P.TD + 5)
    H = Place((385, 112), 0.5, (0, zb))
    H.polys(S, hlr.clip_polys(vis, winH)); H.hatches(S, hlr.clip_hatch(hat, winH))
    S.line(H((0, zb - 10)), H((0, zb + P.TD + 10)), "EJE")
    zt_ = zb + P.TD
    S.dim(H((-95, zb)), H((95, zb)), -6, "Ø190 H7")
    S.dim(H((-80, zb + P.L_BUJE)), H((80, zb + P.L_BUJE)), 3, "Ø160")
    S.dim(H((-130, zt_)), H((130, zt_)), 6, "Ø260 H11")
    S.dim(H((-150, zt_)), H((150, zt_)), 14, "Ø300 (cubo 4c)")
    S.dim(H((230, zb)), H((230, zb + P.L_BUJE)), 6, "100 +0,1/0", orient="v")
    S.dim(H((230, zt_ - P.H_CB)), H((230, zt_)), 6, "25", orient="v")
    S.dim(H((-230, zb)), H((-230, zb + P.TP_BOT)), -6, "30", orient="v")
    S.dim(H((-230, zt_ - P.TP_TOP)), H((-230, zt_)), -6, "30", orient="v")
    S.dim(H((-230, zb)), H((-230, zt_)), -16, "160", orient="v")
    S.weld(H((150, zt_)), H((175, zt_ + 40)), "bevel", "CJP", note="4c-4a/4b")
    S.finish(H((-60, zb + 40)), "Ra 1,6")
    S.view_title((385, 66), "DETALLE H – CUBO CENTRAL", "ESCALA 1:2")

    # ----- DETALLE J 1:2 (barra de empuje)
    winJ = (850, zb - 5, 1012, zb + P.TD + 5)
    J = Place((572, 112), 0.5, (931, zb))
    J.polys(S, hlr.clip_polys(vis, winJ)); J.hatches(S, hlr.clip_hatch(hat, winJ))
    S.line(J((940, zb - 10)), J((940, zb + P.TD + 10)), "EJE")
    S.dim(J((905, zt_)), J((975, zt_)), 6, "Ø70")
    S.dim(J((940, zb)), J((1000, zb)), -8, "60")
    S.dim(J((1000, zb + P.TP_BOT)), J((1000, zt_ - P.TP_TOP)), 6, "100 libre", orient="v")
    S.weld(J((975, zt_)), J((1015, zt_ + 40)), "bevel", "10", note="a ras")
    S.weld(J((975, zb)), J((1015, zb - 40)), "bevel", "10", note="mec.")
    S.text("Agujero Ø71 en 4a y 4b, chaflán 10×45°", J((860, zb - 20)), 2.1, "TOP_LEFT")
    S.view_title((585, 66), "DETALLE J – BARRA DE EMPUJE 4f", "ESCALA 1:2")

    # =================== PISTAS INOX (U) / TOLERANCIAS ===================
    x0 = 600
    if U:
        R = Place((660, 535), 0.025)
        for k, (din, dout) in enumerate((P.INOX_A, P.INOX_B)):
            cc = (650 + k * 75, 535)
            S.circle(cc, dout / 2 * 0.03); S.circle(cc, din / 2 * 0.03); S.centerlines(cc, dout / 2 * 0.03, 2)
            S.dim_dia(cc, dout / 2 * 0.03, 50, f"Ø{dout:.0f}", ext=5)
            S.dim_dia(cc, din / 2 * 0.03, -60, f"Ø{din:.0f}", ext=6)
            S.text(f"POS {20 + k} – e = 3", (cc[0], cc[1] - dout / 2 * 0.03 - 7), 2.6, "TOP_CENTER", bold=True)
        S.text("ESCALA 1:33 (aprox.)", (700, 495), 2.2, "TOP_CENTER")
        lines = ["PISTAS INOX POS 20 / 21",
                 "• AISI 316L (1.4404), e = 3 mm, cada anillo de una sola pieza (sin juntas).",
                 "• Acabado espejo: Ra ≤ 0,1 µm, Ry5i ≤ 1 µm (EN 1337-2), dureza 150–220 HV.",
                 "• Mecanizar cara inferior 4b en zonas de pistas (planitud ≤ 0,20) antes de soldar.",
                 "• Fijar con filete continuo 3 mm ER309L en bordes interior y exterior, soldadura",
                 "  por tramos alternos de 150 mm para limitar distorsión. Contacto pleno (sin bolsas).",
                 "• Verificar planitud conjunto pista ≤ 0,30 mm en Ø1680. Proteger con film adhesivo",
                 "  hasta el montaje. No pintar ni golpear."]
        y = S.mtext(lines, (x0, 482), h=2.25, ls=1.55, bold_first=True)
    else:
        y = 560
    tol = ["TOLERANCIAS GEOMÉTRICAS Y MECANIZADO",
           "• Cara sup. pos 1 (zona Ø2000): planitud 0,20; Ra 3,2" + (" (fondo alojamientos)." if U else " / 1,6–3,2 contacto."),
           "• Cara inf. 4b: planitud 0,20; paralelismo con cara sup. 4a: 0,30 (mecanizar ambas tras relevar).",
           "• Ø150 H7 (pos 1) y Ø190 H7 (pos 4): perpendicularidad 0,05 respecto de la cara de giro.",
           "• Barras 4f: posición ±0,5 (PCD 1880, paso 10° ±0,05°); verticalidad 0,3 en 160.",
           "• Ménsulas pos 2: agujero Ø71 H9 mecanizado en línea después de soldar y relevar;",
           "  coaxialidad entre mejillas 0,10; altura del eje ±0,5.",
           "• Tolerancias generales ISO 2768-mK. Aristas vivas: chaflán 1×45°.",
           "",
           "SECUENCIA DE FABRICACIÓN POS 1",
           "1. Corte térmico con 5 mm de sobremetal por cara; UT de plancha (A578 nivel B).",
           "2. Soldar pos 2 (CJP mejillas + filetes respaldo) y pos 3 (filete 12 todo alrededor);",
           "   precalentar ≥ 110 °C, control de interpase ≤ 250 °C.",
           "3. Alivio de tensiones 590–620 °C (1 h/25 mm, mín. 2 h), enfriamiento en horno.",
           "4. Mecanizado final: cara superior, Ø150 H7" + (", 34 alojamientos" if U else "") + ", agujeros Ø71 H9.",
           "5. Ensayos: UT CJP 100 %, MT filetes 100 %, control dimensional con protocolo.",
           "",
           "SECUENCIA DE FABRICACIÓN POS 4 (DISCO CAJÓN)",
           "1. 4b sobre mesa plana; soldar cubo 4c (CJP), almas 4d y nervios 4e (filete 8 a ambos lados).",
           "2. Insertar 36 barras 4f en 4b; presentar 4a con ranuras 22×80 c/250 sobre almas y nervios.",
           "3. Soldar ranuras (relleno completo), cubo 4c–4a (CJP) y barras 4f a 4a/4b (bisel 10, ver det. J).",
           "4. Drenaje/venteo: 2× Ø20 en 4b por celda; tapar con tapón roscado tras pintura interior.",
           "5. Alivio de tensiones 590–620 °C; mecanizar cara 4b (contacto), cara 4a, cubo (det. H).",
           "6. " + ("Soldar pistas 20/21 en 4b y pulir." if U else "Aplicar película pos 19 en cara 4b (lám. 4)."),
           "   Control: barras ±0,5; planitud 4b ≤ 0,20; UT CJP 100 %, MT 100 %."]
    yy = S.mtext(tol, (x0, y - 8), h=2.2, ls=1.5, bold_first=True)
    dp = M.disc_parts(v)
    mk = {k: dp[k].val().Volume() * 7.85e-6 for k in dp}
    rows = [["4a", "Plancha sup. Ø2000×30; Ø300, 36×Ø71, 4×M30", "1", fmt_kg(mk["4a"])],
            ["4b", "Plancha inf. Ø2000×30; Ø300, 36×Ø71", "1", fmt_kg(mk["4b"])],
            ["4c", "Cubo Ø300/Ø190×160 (S355J2+N, forja)", "1", fmt_kg(mk["4c"])],
            ["4d", "Almas 25×100 roladas, eje Ø600/1100/1470", "3", fmt_kg(mk["4d"])],
            ["4e", "Nervios 20×100, L 137/225/160/132 (×12)", "48", fmt_kg(mk["4e"])],
            ["4f", "Barras Ø70×160 (S355J2 laminado)", "36", fmt_kg(mk["4f"])]]
    S.table(x0, yy - 4, [("SUB", 10, "C"), ("DESPIECE POS 4", 88, "L"), ("CANT.", 12, "C"), ("kg total", 18, "R")], rows, rh=4.8, h=2.05)
    return S, v


if __name__ == "__main__":
    import sys, pymupdf
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet3(k)
        S.save(f"out/{v['code']}-03.dxf", f"out/{v['code']}-03.pdf")
        pymupdf.open(f"out/{v['code']}-03.pdf")[0].get_pixmap(dpi=75).save(f"out/{v['code']}-03.png")
        print("ok", k)
```

### tt/sheet4.py
`tt/sheet4.py` — 321 líneas

```python
"""Lámina 4: piezas mecánicas y soldadas."""
import math
import params as P, draw
from common import Place, masses, fmt_kg


def nf(x, d=0):
    return f"{x:.{d}f}".replace(".", ",")


def hrect(S, pts, scale=0.6, angle=0, pattern="ANSI31"):
    S.pline(pts, "VIS", closed=True)
    S.hatch_poly(pts, scale=scale, angle=angle, pattern=pattern)


def tag(S, p, pos, name, mat, qty, mass):
    S.text(f"POS {pos} – {name}", p, 3.4, "BOTTOM_CENTER", bold=True)
    w = len(f"POS {pos} – {name}") * 3.4 * 0.6
    S.line((p[0] - w / 2, p[1] - 1.2), (p[0] + w / 2, p[1] - 1.2), "VIS")
    S.text(f"{mat} – Cant. {qty} – {mass} kg/u", (p[0], p[1] - 2.6), 2.3, "TOP_CENTER")


def sheet4(kind):
    v = P.variant(kind); v["proj"] = P.PROJ
    U = kind == "U"
    m = masses(v)
    S = draw.Sheet()
    S.frame(v, 4, 4, "PIEZAS MECÁNICAS Y SOLDADAS", "INDICADA")
    L = v["L_piv"]

    # ---------------- POS 5 PIVOTE 1:2 ----------------
    O = Place((75, 442), 0.5)
    r = 75
    prof = [(-r + 5, 0), (r - 5, 0), (r, 5), (r, L), (-r, L), (-r, 5)]
    S.pline([O(p) for p in prof], "VIS", closed=True)
    S.line(O((-r, P.TB)), O((r, P.TB)), "FINA")
    S.line(O((0, -8)), O((0, L + 8)), "EJE")
    for x in (-50, 50):
        S.line(O((x - 8.6, L)), O((x - 8.6, L - 40)), "OCU"); S.line(O((x + 8.6, L)), O((x + 8.6, L - 40)), "OCU")
        S.line(O((x - 10, L)), O((x - 10, L - 32)), "OCU"); S.line(O((x + 10, L)), O((x + 10, L - 32)), "OCU")
        S.line(O((x - 8.6, L - 40)), O((x + 8.6, L - 40)), "OCU")
    S.dim(O((-r, 0)), O((r, 0)), -8, "Ø150 p6 (+0,068/+0,043)")
    S.dim(O((-r, L)), O((r, L)), 6, "Ø150 f7 (-0,043/-0,083)")
    S.dim(O((r, 0)), O((r, P.TB)), 6, "80", orient="v")
    S.dim(O((r, 0)), O((r, L)), 18, nf(L), orient="v")
    S.leader(O((-r + 2.5, 2.5)), (O((0, 0))[0] - 30, O((0, -48))[1]), "5×45°", h=2.3)
    S.leader(O((50, L - 20)), (O((0, 0))[0] + 50, O((0, L + 25))[1]), "6× M20 prof. 32 (Ø17,5 prof. 40) s/ PCD 100", h=2.2)
    S.finish(O((-r, P.TB + 40)), "Ra 0,8")
    S.text("Zona p6", O((-r + 8, 40)), 2.1, "MIDDLE_LEFT")
    S.text("Zona f7", O((-r + 8, P.TB + 40)), 2.1, "MIDDLE_LEFT")
    tag(S, (75, 412), 5, "PIVOTE", "42CrMo4+QT, 280–330 HB", 1, fmt_kg(m[5]))

    # ---------------- POS 6 BUJE 1:2 ----------------
    O = Place((190, 488), 0.5)
    for s in (-1, 1):
        pts = [O((s * 75, 0)), O((s * 95, 0)), O((s * 95, P.L_BUJE)), O((s * 75, P.L_BUJE))]
        hrect(S, pts, pattern="ANSI33", scale=0.5)
        for z in (15, 37.5, 60):
            S.circle(O((s * 85, z)), 2.5, "FINA")
    S.line(O((0, -8)), O((0, P.L_BUJE + 8)), "EJE")
    S.dim(O((-95, 0)), O((95, 0)), -8, "Ø190 s6 (+0,151/+0,122)")
    S.dim(O((-75, P.L_BUJE)), O((75, P.L_BUJE)), 6, "Ø150 H7 (+0,040/0)")
    S.dim(O((95, 0)), O((95, P.L_BUJE)), 6, nf(P.L_BUJE), orient="v")
    S.text("Insertos de grafito sólido Ø10,", O((-95, -38)), 2.2, "TOP_LEFT")
    S.text("≈ 25 % superficie de deslizamiento", O((-95, -44)), 2.2, "TOP_LEFT")
    S.text("Chaflán interior 2×30° ambos extremos", O((-95, -50)), 2.2, "TOP_LEFT")
    tag(S, (190, 412), 6, "BUJE", "CuAl10Ni5Fe4 + grafito", 1, fmt_kg(m[6]))

    # ---------------- POS 7 TAPA 1:2 ----------------
    O = Place((305, 512), 0.5)
    c = O((0, 0))
    S.circle(c, 60); S.centerlines(c, 60, 4)
    S.circle(c, 25, "EJE")
    for k in range(6):
        a = math.radians(30 + 60 * k)
        p = O((50 * math.cos(a), 50 * math.sin(a)))
        S.circle(p, 5.5); S.circle(p, 8.25)
    S.dim_dia(c, 60, 35, "Ø240")
    S.leader(O((50 * math.cos(math.radians(150)), 50 * math.sin(math.radians(150)))), (c[0] - 30, c[1] + 66), "6× Ø22 / avell. Ø33×13 s/ PCD 100", h=2.2)
    Os = Place((305, 440), 0.5)
    pts = [Os(p) for p in [(-120, 0), (120, 0), (120, 20), (-120, 20)]]
    S.pline(pts, "VIS", closed=True)
    for x in (-50, 50):
        S.line(Os((x - 11, 0)), Os((x - 11, 7)), "OCU"); S.line(Os((x + 11, 0)), Os((x + 11, 7)), "OCU")
        S.line(Os((x - 16.5, 7)), Os((x - 16.5, 20)), "OCU"); S.line(Os((x + 16.5, 7)), Os((x + 16.5, 20)), "OCU")
    S.dim(Os((120, 0)), Os((120, 20)), 6, "20", orient="v")
    tag(S, (305, 428), 7, "TAPA RETENEDORA", "S355J2", 1, fmt_kg(m[7]))

    # ---------------- POS 11 TRINQUETE 1:2,5 ----------------
    sc = 0.4
    O = Place((375, 505), sc)
    xs = 936.4 - P.PAWL_TIP
    dz = math.sqrt(P.SEAT_R ** 2 - xs ** 2)
    a0 = math.degrees(math.atan2(-dz, -xs))
    arc = [(xs + P.SEAT_R * math.cos(math.radians(t)), 85 + P.SEAT_R * math.sin(math.radians(t))) for t in [a0 + (0 - a0) * i / 20 for i in range(21)]]
    outline = [(0, 35)] + arc + [(245, 85), (245, 0), (60, 0)]
    pts = [O(p) for p in outline]
    S.pline(pts, "VIS", closed=True)
    S.rect(*O((205, 16.5)), *O((245, 68.5)), "OCU")
    S.line(O((-10, 42.5)), O((255, 42.5)), "EJE")
    S.dim(O((0, 85)), O((245, 85)), 14, "245")
    S.dim(O((245, 0)), O((245, 85)), 6, "85 f8", orient="v")
    S.dim(O((0, 85)), O((xs, 85)), 6, nf(xs, 1))
    S.dim_rad(O((xs, 85)), P.SEAT_R * sc, -60, "R36", ext=6)
    S.dim(O((0, 0)), O((60, 0)), -6, "60")
    S.dim(O((0, 0)), O((0, 35)), -6, "35", orient="v")
    S.text("Asiento de barra Ø70", O((80, 95)), 2.0, "BOTTOM_LEFT")
    S.text("Alojamiento resorte Ø52 prof. 40", O((120, -22)), 2.0, "TOP_LEFT")
    O2 = Place((375, 445), sc)
    S.rect(*O2((0, 0)), *O2((245, 90)))
    S.line(O2((xs - P.SEAT_R + 4.6, 0)), O2((xs - P.SEAT_R + 4.6, 90)), "OCU")
    S.line(O2((xs + P.SEAT_R, 0)), O2((xs + P.SEAT_R, 90)), "OCU")
    S.line(O2((205, 19)), O2((245, 19)), "OCU"); S.line(O2((205, 71)), O2((245, 71)), "OCU"); S.line(O2((205, 19)), O2((205, 71)), "OCU")
    S.dim(O2((245, 0)), O2((245, 90)), 6, "90 f8", orient="v")
    S.leader(O2((245, 45)), (O2((245, 0))[0] + 14, O2((0, 110))[1]), "Manilla M12 (desenganche)", h=2.0)
    tag(S, (420, 428), 11, "TRINQUETE", "34CrNiMo6+QT, 300–350 HB, MT 100 %", 2, fmt_kg(m[11] / 2))

    # ---------------- POS 10 CARRO DE EMPUJE 1:2,5 ----------------
    Hs = v["shoe_top"] - P.TB
    zc = v["z_axis"] - P.TB
    L, Wd = P.SHOE_L, P.SHOE_X1 - P.SHOE_X0
    pf, pb = P.SHOE_FRONT - 0.5, P.SHOE_FRONT + P.PAWL_W + 0.5
    eye = P.SHOE_FRONT + P.EYE_OFF
    # planta: largo horizontal (0 = frente), ancho vertical (0 = cara interior, lado disco)
    O = Place((520, 492), sc)
    S.rect(*O((0, 0)), *O((L, Wd)))
    S.rect(*O((pf, 0)), *O((pb, Wd)), "OCU")
    S.rect(*O((190, (Wd - 80) / 2)), *O((L, (Wd + 80) / 2)))
    S.line(O((eye, -8)), O((eye, Wd + 8)), "EJE")
    S.line(O((-8, Wd / 2)), O((L + 8, Wd / 2)), "EJE")
    S.dim(O((0, Wd)), O((L, Wd)), 6, "300")
    S.dim(O((0, Wd)), O((pf, Wd)), 14, nf(pf, 1))
    S.dim(O((pf, Wd)), O((pb, Wd)), 14, "86 H9")
    S.dim(O((0, Wd)), O((eye, Wd)), 22, nf(eye))
    S.dim(O((L, 0)), O((L, Wd)), 6, "130", orient="v")
    S.dim(O((L, (Wd - 80) / 2)), O((L, (Wd + 80) / 2)), 16, "80 H11", orient="v")
    S.text("lado disco", O((5, -6)), 2.0, "TOP_LEFT")
    S.text("frente (empuje →)", O((5, -14)), 2.0, "TOP_LEFT") if False else None
    # elevación lateral
    O2 = Place((520, 418), sc)
    S.rect(*O2((0, 0)), *O2((L, Hs)))
    S.rect(*O2((pf, zc - 45.5)), *O2((pb, zc + 45.5)))
    S.rect(*O2((0, 0)), *O2((L, 31)), "OCU")
    S.rect(*O2((190, zc - 65)), *O2((L, Hs)), "OCU")
    S.circle(O2((eye, zc)), 35.5 * sc); S.centerlines(O2((eye, zc)), 35.5 * sc, 3)
    S.line(O2((-8, zc)), O2((L + 8, zc)), "EJE")
    S.dim(O2((L, 0)), O2((L, Hs)), 6, nf(Hs), orient="v")
    S.dim(O2((0, 0)), O2((0, zc)), -6, nf(zc), orient="v")
    S.dim(O2((0, zc - 45.5)), O2((0, zc + 45.5)), -16, "91 H9", orient="v")
    S.leader(O2((eye + 12, zc + 12)), (O2((eye, 0))[0] + 12, O2((0, Hs + 22))[1]), "Ø71 H9 (pasador pos 12)", h=2.0)
    S.text("Ranura guía 41 H11 × 31 (inferior)", O2((5, -6)), 2.0, "TOP_LEFT")
    S.text("Bandas UHMW e=5 en base y flancos de ranura", O2((5, -12)), 2.0, "TOP_LEFT")
    tag(S, (580, 396), 10, "CARRO DE EMPUJE", "S355J2+N", 2, fmt_kg(m[10] / 2))

    # ---------------- POS 12 PASADOR Ø70 1:2 ----------------
    O = Place((720, 540), 0.5)
    S.pline([O(p) for p in [(0, -35), (195, -35), (200, -30), (200, 30), (195, 35), (0, 35)]], "VIS", closed=True)
    S.rect(*O((-15, -45)), *O((0, 45)))
    S.line(O((-22, 0)), O((210, 0)), "EJE")
    S.circle(O((188, 0)), 4.5); S.line(O((188, -40)), O((188, 40)), "EJE")
    S.dim(O((0, 35)), O((200, 35)), 6, "200")
    S.dim(O((-15, 45)), O((0, 45)), 6, "15", outside=True)
    S.dim(O((200, -35)), O((200, 35)), 6, "Ø70 f8", orient="v")
    S.dim(O((-15, -45)), O((-15, 45)), -5, "Ø90", orient="v")
    S.dim(O((0, -35)), O((188, -35)), -8, "188")
    S.leader(O((188, 0)), (O((0, 0))[0] + 60, O((0, 75))[1]), "Ø9 pasante (clip R pos 13)", h=2.1)
    tag(S, (765, 495), 12, "PASADOR Ø70", "42CrMo4+QT, 280–330 HB", 4, fmt_kg(m[12] / 4))

    # ---------------- POS 2 MÉNSULA 1:5 ----------------
    hc = v["H_cheek"]; zh = v["z_axis"] - P.TB
    s5 = 0.2
    # planta
    O = Place((70, 320), s5)
    for sd in (-1, 1):
        xa, xb = sd * 40, sd * 80
        S.rect(*O((min(xa, xb), -140)), *O((max(xa, xb), 140)))
    S.rect(*O((-80, -180)), *O((80, -140)))
    S.line(O((-100, 0)), O((100, 0)), "EJE"); S.line(O((0, -200)), O((0, 165)), "EJE")
    S.dim(O((-80, 140)), O((80, 140)), 5, "160")
    S.dim(O((-40, 140)), O((40, 140)), 12, "80")
    S.dim(O((80, -140)), O((80, 140)), 5, "280", orient="v")
    S.dim(O((80, -180)), O((80, -140)), 5, "40", orient="v", outside=True)
    S.dim(O((-80, -180)), O((-80, 0)), -5, "180", orient="v")
    S.text("Respaldo hacia el exterior", O((-80, -205)), 2.1, "TOP_LEFT")
    S.text("(lado opuesto al disco)", O((-80, -230)), 2.1, "TOP_LEFT")
    # lateral (y-z)
    O2 = Place((165, 262), s5)
    S.rect(*O2((-140, 0)), *O2((140, hc)))
    S.rect(*O2((-180, 0)), *O2((-140, hc)))
    S.circle(O2((0, zh)), 35.5 * s5 * 5 * 0.2 / 0.2 * 0.2 / 0.2 if False else 7.1)
    S.centerlines(O2((0, zh)), 7.1, 3)
    S.dim(O2((140, 0)), O2((140, hc)), 6, nf(hc), orient="v")
    S.dim(O2((140, 0)), O2((140, zh)), 14, nf(zh), orient="v")
    S.dim(O2((-180, hc)), O2((140, hc)), 5, "320")
    S.leader(O2((25, zh + 25)), (O2((0, 0))[0] + 20, O2((0, hc + 40))[1]), "Ø71 H9 (mecanizar en línea)", h=2.2)
    S.weld(O2((-140, 0)), (O2((0, 0))[0] - 10, O2((0, -45))[1]), "cjp", "CJP", other=True, note="mejillas-base")
    S.weld(O2((-170, 0)), (O2((0, 0))[0] - 50, O2((0, -80))[1]), "fillet", "16", other=True, all_round=True, note="respaldo")
    S.text("Base pos 1", O2((60, -12)), 2.0, "TOP_LEFT")
    S.line(O2((-260, 0)), O2((240, 0)), "VIS")
    tag(S, (120, 212), 2, "MÉNSULA DE REACCIÓN (SOLDADA)", "A572 Gr.50, e = 40", 4, fmt_kg(m[2] / 4))
    S.text("ESCALA 1:5", (120, 202), 2.3, "TOP_CENTER")

    # ---------------- POS 3 OREJA 1:2 ----------------
    O = Place((255, 260), 0.5)
    r60 = 60
    pts = [(0, 0), (150, 0), (150, 170 - r60)]
    arc = [(150 - r60 + r60 * math.cos(math.radians(a)), 170 - r60 + r60 * math.sin(math.radians(a))) for a in range(0, 91, 10)]
    arc2 = [(r60 - r60 * math.cos(math.radians(a)), 170 - r60 + r60 * math.sin(math.radians(a))) for a in range(90, -1, -10)]
    S.pline([O(p) for p in pts + arc + arc2 + [(0, 170 - r60)]], "VIS", closed=True)
    S.circle(O((75, 100)), 8); S.centerlines(O((75, 100)), 8, 3)
    S.dim(O((0, 0)), O((150, 0)), -8, "150")
    S.dim(O((150, 0)), O((150, 170)), 6, "170", orient="v")
    S.dim(O((0, 0)), O((0, 100)), -6, "100", orient="v")
    S.dim(O((0, 170)), O((75, 170)), 6, "75")
    S.leader(O((75 + 8 * 0.7 * 2, 100 + 8 * 0.7 * 2)), (O((0, 0))[0] + 60, O((0, 210))[1]), "Ø32 (grillete 4,75 t)", h=2.2)
    S.dim_rad(O((150 - r60, 170 - r60)), 30, 50, "R60", ext=6)
    S.text("Espesor 40. Borde exterior a ras con canto de pos 1.", O((0, -30)), 2.1, "TOP_LEFT")
    S.weld(O((0, 0)), (O((0, 0))[0] - 18, O((0, 40))[1]), "fillet", "12", other=True, all_round=True)
    tag(S, (292, 212), 3, "OREJA DE IZAJE", "A572 Gr.50", 4, fmt_kg(m[3] / 4))

    # ---------------- POS 9 CILINDRO (especificación) 1:5 ----------------
    O = Place((395, 330), 0.2)
    S.circle(O((0, 0)), 12); S.circle(O((0, 0)), 7.1)
    S.rect(*O((60, -70)), *O((330, 70)))
    S.rect(*O((330, -45)), *O((390, 45)))
    S.circle(O((450, 0)), 12); S.circle(O((450, 0)), 7.1)
    S.line(O((-80, 0)), O((700, 0)), "EJE")
    S.dim(O((0, 70)), O((450, 70)), 10, "L0 = 450 ±10 (retraído)")
    S.dim(O((0, -70)), O((650, -70)), -10, "650 (extendido, carrera 200)")
    S.dim(O((200, -70)), O((200, 70)), 0.01, "Ø ≤ 140")
    S.leader(O((450 + 8, 8)), (O((0, 0))[0] + 130, O((0, 140))[1]), "Ojal Ø70 con rótula GE70 (ambos)", h=2.2)
    spec = ["ESPECIFICACIÓN CILINDRO POS 9 (comercial, 2 un.)",
            "• Doble efecto, retorno hidráulico. Presión máx. 700 bar.",
            "• Fuerza de empuje ≥ 445 kN a 700 bar (clase 50 t).",
            "• Carrera 200 mm (36 libre + 164 de empuje). Ojales Ø70, rótula GE70.",
            "• Acoplamientos CR400 hembra; mangueras 700 bar.",
            "• Colector común con bloqueo: no permitir empuje de un solo cilindro;",
            "  y manómetro glicerina 0–1000 bar a la vista del operador.",
            "• Si el ojal difiere: ajustar pos 2 (eje) y pos 12 (Ø)."]
    S.mtext(spec, (375, 300), h=2.2, ls=1.55, bold_first=True)

    # ---------------- POS 19 PASTILLA (U) / FILM (S) ----------------
    if U:
        O = Place((600, 340), 0.4)
        S.circle(O((0, 0)), 34); S.circle(O((0, 0)), 33.8, "FINA"); S.centerlines(O((0, 0)), 34, 4)
        S.dim_dia(O((0, 0)), 34, 40, "Ø170 -0,1/-0,2")
        Os = Place((600, 275), 0.5)
        pts = [Os(p) for p in [(-85, 0), (85, 0), (85, 9.5), (84.5, 10), (-84.5, 10), (-85, 9.5)]]
        hrect(S, pts, pattern="ANSI37", scale=0.45)
        S.dim(Os((85, 0)), Os((85, 10)), 6, "10 ±0,1", orient="v", outside=True)
        sp = ["UHMW-PE PE1000 (ISO 15527), virgen, Mw ≥ 5×10⁶ g/mol.",
              "Presión admisible larga duración ≥ 12 MPa (ensayar).",
              "Alternativa: UHMW certificado para apoyos (EN 1337/ETA).",
              "Cara superior: mecanizada plana Ra ≤ 1,6. Sin lubricante.",
              "Chaflán 0,5×45° borde superior. 34 un. + 4 repuesto."]
        S.mtext(sp, (555, 262), h=2.15, ls=1.5)
        tag(S, (600, 222), 19, "PASTILLA DESLIZANTE", "UHMW-PE PE1000", "34+4", fmt_kg(m[19] / 34))
        S.text("ESCALA 1:2,5 / 1:2", (600, 212), 2.3, "TOP_CENTER")
    else:
        sp = ["POS 19 – PELÍCULA SECA DE GRAFITO",
              "• Producto: SLIP Plate® No. 4 (Superior Graphite) o equivalente",
              "  aprobado: grafito en base agua, película seca, sin solvente.",
              "• Superficies: cara sup. pos 1 (Ø2000) y cara inf. pos 4 completa.",
              "• Área total ≈ 6,3 m²; rendimiento ≈ 6 m²/gal por capa.",
              "• Espesor por capa 50–150 µm (2–6 mil); 2 capas.",
              "• Aplicar con superficie a 10–38 °C; 24 h entre capas.",
              "• Producto conductor eléctrico: aislar de equipos energizados.",
              "• Grasa pos 20: solo si opera con lluvia/humedad; capa",
              "  delgada sobre el film seco, según manual del fabricante."]
        S.mtext(sp, (560, 322), h=2.25, ls=1.55, bold_first=True)

    # ---------------- POS 14/15/16 SELLO 1:1 ----------------
    O = Place((752, 290), 1.0)
    g = v["g"]
    hrect(S, [O((-40, g)), O((0, g)), O((0, g + 30)), O((-40, g + 30))], scale=0.8)
    S.pline([O((-40, g + 30)), O((-44, g + 34))], "FINA")
    hrect(S, [O((-40, -20)), O((15, -20)), O((15, 0)), O((-40, 0))], scale=0.8, angle=90)
    rub = [O((0, 0)), O((5, 0)), O((5, g + 30)), O((0, g + 30))]
    S.pline(rub, "VIS", closed=True); S.hatch_poly(rub, solid=True)
    bar = [O((5, g + 2.5)), O((11, g + 2.5)), O((11, g + 27.5)), O((5, g + 27.5))]
    S.pline(bar, "VIS", closed=True); S.hatch_poly(bar, scale=0.4)
    zbm = g + 15
    S.rect(*O((11, zbm - 6.5)), *O((16, zbm + 6.5)))
    S.line(O((-16, zbm - 4)), O((11, zbm - 4)), "OCU"); S.line(O((-16, zbm + 4)), O((11, zbm + 4)), "OCU")
    S.line(O((-20, zbm)), O((22, zbm)), "EJE")
    S.dim(O((0, 0)), O((5, 0)), -6, "5", outside=True)
    S.dim(O((-40, g)), O((-40, g + 30)), -5, "30", orient="v")
    S.leader(O((3, 6)), (O((0, 0))[0] + 25, O((0, -10))[1]), "pos 14 NBR 70 ShA", h=2.2)
    S.leader(O((8, g + 24)), (O((0, 0))[0] + 25, O((0, g + 45))[1]), "pos 15 fleje 25×6", h=2.2)
    S.leader(O((15, zbm + 5)), (O((0, 0))[0] + 25, O((0, zbm + 22))[1]), "pos 16 M8×20 A2-70", h=2.2)
    S.text("Plancha inferior 4b", O((-40, g + 36)), 2.1, "BOTTOM_LEFT")
    S.text("Base pos 1", O((-40, -24)), 2.1, "TOP_LEFT")
    S.text("Faldón apoyado sobre pos 1, pretensado 1–2 mm.", O((-40, -32)), 2.1, "TOP_LEFT")
    S.text("Unión del faldón: vulcanizado en frío, traslapo 50.", O((-40, -37)), 2.1, "TOP_LEFT")
    S.text("Fleje rolado Ø2022 en 2 tramos con cubrejunta.", O((-40, -42)), 2.1, "TOP_LEFT")
    S.text("36× M8 radial prof. 16 en canto de 4b (0°+10°k).", O((-40, -47)), 2.1, "TOP_LEFT")
    S.view_title((765, 212), "DETALLE SELLO PERIMETRAL (pos 14/15/16)", "ESCALA 1:1 (parcial)")

    # ---------------- nota de piezas comerciales ----------------
    com = ["PIEZAS COMERCIALES Y TERMINACIONES",
           "• Pos 8: ISO 4762 M20×45 10.9, zincado laminar, con arandela Nord-Lock NL20.",
           "• Clips R Ø8 zincados con cadena de retención para pasadores pos 12.",
           "• Pos 16: ISO 4017 M8×20 A2-70 + arandela ISO 7089 A2.",
           "• Pos 17: prisionero ISO 4026 M30×25 8.8 zincado, ras con cara superior 4a.",
           "• Pos 22: pletina 40×30×850 S355J2, filete 8 continuo ambos lados; ancho 40 h9 tras soldar.",
           "• Pos 13: resorte compresión Ø50×100, k ≈ 5 N/mm, precarga ≈ 150 N; tapa M10 y manilla M12.",
           "• Pos 18: cáncamo giratorio M30, WLL ≥ 2,5 t (tipo RUD VRS o equiv.), suelto.",
           "• Templado y revenido (QT): certificar dureza y ensayo Charpy KV ≥ 27 J a -20 °C.",
           "• Pasadores 5, 11, 12: MT 100 % después del mecanizado; zincado laminar",
           "  o fosfatado + aceite en zonas sin ajuste."]
    S.mtext(com, (26, 170), h=2.25, ls=1.55, bold_first=True)
    return S, v


if __name__ == "__main__":
    import sys, pymupdf
    for k in sys.argv[1:] or ["U"]:
        S, v = sheet4(k)
        S.save(f"out/{v['code']}-04.dxf", f"out/{v['code']}-04.pdf")
        pymupdf.open(f"out/{v['code']}-04.pdf")[0].get_pixmap(dpi=75).save(f"out/{v['code']}-04.png")
        print("ok", k)
```

### tt/build_all.py
`tt/build_all.py` — 16 líneas

```python
import pymupdf, sheet1, sheet2, sheet3, sheet4, zipfile, os
names = {"U": "TT500-A_Tornamesa_UHMW", "S": "TT500-B_Tornamesa_Acero-Grafito"}
for k in ("U", "S"):
    out = pymupdf.open()
    dxfs = []
    for i, f in enumerate((sheet1.sheet1, sheet2.sheet2, sheet3.sheet3, sheet4.sheet4), 1):
        S, v = f(k)
        d, p = f"out/{v['code']}-{i:02d}.dxf", f"out/{v['code']}-{i:02d}.pdf"
        S.save(d, p); dxfs.append(d)
        out.insert_pdf(pymupdf.open(p))
    out.set_metadata({"title": f"{names[k]} – Planos mecánicos", "author": "", "subject": v["title"]})
    out.save(f"out/{names[k]}_Planos.pdf", garbage=3, deflate=True)
    with zipfile.ZipFile(f"out/{names[k]}_DXF.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for d in dxfs: z.write(d, os.path.basename(d))
        z.write(f"out/{v['code']}.step", f"{v['code']}_conjunto.step")
    print(k, "ok")
```

### tt/web/template.html
`tt/web/template.html` — visor 3D 500 tf (three.js r147, glTF JSON embebido)

```html
<meta charset="utf-8">
<title>Tornamesa TT500 3D</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: banda de título, visor 3D dominante a la izquierda y lista de piezas a la derecha; en teléfono se apila. */
:root{
  --bg:#ECEFF1; --panel:#F8F9FA; --fg:#15191C; --muted:#56626B; --line:#C6CDD2;
  --accent:#D99A06; --accent-ink:#3A2A00; --view:#DDE2E5; --sel:#FFF3CF;
  --f-disp:"Barlow Condensed","Arial Narrow",Arial,sans-serif;
  --f-body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#101417; --panel:#171D21; --fg:#E6EAED; --muted:#93A0A9; --line:#2C363D;
  --accent:#F2B42A; --accent-ink:#1C1400; --view:#1B2328; --sel:#3A2F12; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#101417; --panel:#171D21; --fg:#E6EAED; --muted:#93A0A9; --line:#2C363D;
  --accent:#F2B42A; --accent-ink:#1C1400; --view:#1B2328; --sel:#3A2F12; color-scheme:dark}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{background:var(--bg);color:var(--fg);font-family:var(--f-body);font-size:14px;line-height:1.5;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:18px 28px}
.wrap{max-width:1320px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
header{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:12px;border-bottom:2px solid var(--fg);padding-bottom:10px}
h1{font-family:var(--f-disp);font-weight:700;font-size:clamp(28px,4.2vw,44px);line-height:1;letter-spacing:.01em;margin:0;text-wrap:balance}
h1 small{display:block;font-family:var(--f-mono);font-weight:400;font-size:12px;letter-spacing:.06em;color:var(--muted);margin-top:6px;text-transform:uppercase}
.seg{display:inline-flex;border:1px solid var(--fg);border-radius:3px;overflow:hidden}
.seg button{font:600 13px/1 var(--f-body);padding:10px 14px;border:0;background:transparent;color:var(--fg);cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink)}
.seg button:focus-visible,.ctrl button:focus-visible,li:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.grid{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:14px;align-items:start}
@media (max-width:900px){.grid{grid-template-columns:minmax(0,1fr)}}
.viewer{position:relative;background:var(--view);border:1px solid var(--line);aspect-ratio:16/10;max-height:74vh;width:100%;min-width:0}
.viewer canvas{display:block;width:100%;height:100%;touch-action:none}
.hud{position:absolute;left:10px;top:10px;font:500 11px/1.4 var(--f-mono);color:var(--muted);background:color-mix(in srgb,var(--panel) 82%,transparent);padding:6px 8px;border:1px solid var(--line);pointer-events:none}
.hud b{color:var(--fg);font-weight:500}
.loading{position:absolute;inset:0;display:grid;place-items:center;font:500 13px var(--f-mono);color:var(--muted)}
.ctrl{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;background:var(--panel);border:1px solid var(--line);padding:10px 12px}
.ctrl label{font:600 12px var(--f-body);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);display:flex;align-items:center;gap:8px}
.ctrl input[type=range]{width:min(220px,46vw);accent-color:var(--accent)}
.ctrl button{font:500 13px var(--f-body);padding:7px 11px;border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:3px;cursor:pointer}
.ctrl button[aria-pressed="true"]{border-color:var(--fg);background:var(--fg);color:var(--bg)}
aside{background:var(--panel);border:1px solid var(--line);min-width:0;display:flex;flex-direction:column}
aside h2{font-family:var(--f-disp);font-weight:600;font-size:20px;letter-spacing:.02em;margin:0;padding:10px 12px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:baseline}
aside h2 span{font:400 12px var(--f-mono);color:var(--muted)}
ul{list-style:none;margin:0;padding:0;max-height:min(62vh,620px);overflow:auto}
li{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:4px 8px;padding:7px 12px;border-bottom:1px solid var(--line);cursor:pointer}
li:hover{background:color-mix(in srgb,var(--sel) 60%,transparent)}
li.on{background:var(--sel)}
li .p{font:600 13px var(--f-mono);color:var(--fg)}
li .d{font-size:13px;line-height:1.3}
li .m{grid-column:2/4;font:400 11.5px var(--f-mono);color:var(--muted)}
li .q{font:500 12px var(--f-mono);color:var(--muted);text-align:right;font-variant-numeric:tabular-nums}
li.na .d{color:var(--muted)}
.specs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;border:1px solid var(--line);background:var(--panel)}
.specs div{padding:10px 12px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);min-width:0}
.specs dt{font:600 11px var(--f-body);text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.specs dd{margin:2px 0 0;font:500 15px var(--f-mono);font-variant-numeric:tabular-nums}
@media (max-width:700px){.specs{grid-template-columns:repeat(2,minmax(0,1fr))}}
.note{color:var(--muted);font-size:12.5px;max-width:90ch;margin:0}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<div class="wrap">
  <header>
    <h1>Tornamesa hidráulica 500 tf<small id="sub">Modelo 3D de ensamble · TT500</small></h1>
    <div class="seg" role="group" aria-label="Solución">
      <button id="bA" type="button" aria-pressed="true">A · UHMW / inox</button>
      <button id="bB" type="button" aria-pressed="false">B · Acero + grafito</button>
    </div>
  </header>

  <div class="grid">
    <div style="display:flex;flex-direction:column;gap:10px;min-width:0">
      <div class="viewer" id="viewer">
        <div class="loading" id="loading">Cargando modelo…</div>
        <div class="hud" id="hud">Arrastrar: girar · Rueda o pellizco: zoom · Clic derecho: desplazar</div>
      </div>
      <div class="ctrl">
        <label for="exp">Explosión <input id="exp" type="range" min="0" max="100" value="0"></label>
        <button id="cut" type="button" aria-pressed="false">Corte por el eje</button>
        <button id="iso" type="button" aria-pressed="false">Aislar selección</button>
        <button id="reset" type="button">Vista inicial</button>
      </div>
    </div>
    <aside>
      <h2>Lista de piezas <span id="mass"></span></h2>
      <ul id="list"></ul>
    </aside>
  </div>

  <dl class="specs" id="specs"></dl>
  <p class="note">Modelo de conjunto para revisión, generado desde los mismos parámetros que los planos TT500-A/B láminas 1 a 4. Los cilindros (pos 9) son representaciones genéricas del equipo comercial. Las piezas sin geometría (pernos M8, resortes, clips, tapones, cáncamos, película de grafito) aparecen en gris en la lista.</p>
</div>

<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/loaders/GLTFLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/OrbitControls.js"></script>
<script>
const DATA = /*DATA*/null;
const EXP = /*EXP*/null;
const files = {"TT500-A":"TT500-A.json","TT500-B":"TT500-B.json"};
const el = id => document.getElementById(id);
const viewer = el("viewer");
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.localClippingEnabled = true;
renderer.outputEncoding = THREE.sRGBEncoding;
viewer.prepend(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35,1.6,0.01,1000);
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xffffff,0x5a6168,0.95));
const sun = new THREE.DirectionalLight(0xffffff,0.85); sun.position.set(3,6,4); scene.add(sun);
const fill = new THREE.DirectionalLight(0xffffff,0.35); fill.position.set(-4,2,-3); scene.add(fill);
const clip = new THREE.Plane(new THREE.Vector3(0,0,-1),0);

let current=null, cache={}, parts={}, size=1, center=new THREE.Vector3(), selected=null, isolate=false, cutOn=false;

function setBg(){ scene.background = new THREE.Color(css("--view")||"#DDE2E5"); }
setBg();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",setBg);
new MutationObserver(setBg).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});

function resize(){
  const r = viewer.getBoundingClientRect();
  renderer.setSize(r.width, r.height, false);
  camera.aspect = r.width/Math.max(r.height,1); camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(viewer);

function posOf(o){ for(let n=o;n;n=n.parent){ const m=/^P(\d\d)_/.exec(n.name||""); if(m) return +m[1]; } return null; }

function load(code){
  el("loading").hidden=false;
  if(cache[code]) return Promise.resolve(cache[code]);
  return new Promise((res,rej)=>new THREE.GLTFLoader().load(files[code], g=>{cache[code]=g.scene;res(g.scene)}, undefined, rej));
}

function show(code){
  el("bA").setAttribute("aria-pressed", code==="TT500-A");
  el("bB").setAttribute("aria-pressed", code==="TT500-B");
  try{ localStorage.setItem("tt500-variant",code) }catch(e){}
  selected=null; buildList(code);
  load(code).then(root=>{
    if(current) scene.remove(current);
    current=root; scene.add(root);
    parts={};
    root.traverse(o=>{
      if(o.isMesh){
        o.material = o.material.clone();
        o.material.side = THREE.DoubleSide;
        o.material.clippingPlanes = cutOn?[clip]:[];
        o.material.metalness = Math.min(o.material.metalness??0,.35);
        o.material.roughness = Math.max(o.material.roughness??.6,.45);
        o.userData.baseColor = o.material.color.clone();
      }
      const m=/^P(\d\d)_/.exec(o.name||"");
      if(m && !parts[+m[1]]){ parts[+m[1]]={node:o,orig:o.position.clone()}; }
    });
    root.updateMatrixWorld(true);
    const box=new THREE.Box3().setFromObject(root);
    box.getCenter(center); size=box.getSize(new THREE.Vector3()).length();
    for(const k in parts){
      const p=parts[k]; const q=new THREE.Quaternion(); p.node.parent.getWorldQuaternion(q);
      p.up=new THREE.Vector3(0,1,0).applyQuaternion(q.invert());
    }
    clip.constant = center.z;
    el("loading").hidden=true;
    applyExplode(); applySel();
    if(!controls.userData) { resetView(); controls.userData=1; }
  }).catch(()=>{ el("loading").textContent="No se pudo cargar el modelo 3D."; });
  const d=DATA[code];
  el("sub").textContent = d.title;
  el("mass").textContent = "≈ "+d.mass.toLocaleString("es-CL")+" kg";
  const specs=[["Capacidad nominal","500 tf (4 903 kN)"],["Altura sup. disco",d.zt+" mm"],["Interfaz de giro",d.iface],
    ["Presión media",d.pmed],["Presión máx. e = 150 mm",d.pmax],["Fricción de diseño accionamiento",d.mu],["Cilindros","2 × 445 kN, 700 bar"],["Giro por ciclo","10° · 36 barras Ø70 en R940"]];
  el("specs").innerHTML = specs.map(([a,b])=>`<div><dt>${a}</dt><dd>${b}</dd></div>`).join("");
}

function resetView(){
  const s=size||3;
  camera.position.set(center.x+s*0.78, center.y+s*0.62, center.z+s*0.92);
  camera.near=s/500; camera.far=s*20; camera.updateProjectionMatrix();
  controls.target.copy(center); controls.update();
}

function applyExplode(){
  const f = +el("exp").value/100;
  const unit = size/3200*260; // ~420 mm al 100 %
  for(const k in parts){
    const p=parts[k]; const e=(EXP[k]??0)*unit*f*1.0;
    p.node.position.copy(p.orig).addScaledVector(p.up, e);
  }
}

function applySel(){
  if(!current) return;
  current.traverse(o=>{
    if(!o.isMesh) return;
    const pos=posOf(o);
    const on = selected===null || pos===selected;
    o.visible = !(isolate && selected!==null && !on);
    o.material.color.copy(o.userData.baseColor);
    if(selected!==null && on){ o.material.emissive = new THREE.Color(css("--accent")||"#D99A06"); o.material.emissiveIntensity=.35; }
    else { o.material.emissive = new THREE.Color(0x000000); }
    o.material.transparent = selected!==null && !on && !isolate;
    o.material.opacity = (selected!==null && !on && !isolate) ? .28 : 1;
  });
  document.querySelectorAll("#list li").forEach(li=>li.classList.toggle("on", +li.dataset.pos===selected));
}

function buildList(code){
  const rows = DATA[code].rows;
  const ul=el("list"); ul.innerHTML="";
  const geo = new Set([1,2,3,4,5,6,7,8,9,10,11,12,14,15,22].concat(code==="TT500-A"?[19,20,21]:[]));
  rows.forEach(r=>{
    const li=document.createElement("li"); li.tabIndex=0; li.dataset.pos=r.pos;
    if(!geo.has(r.pos)) li.classList.add("na");
    li.innerHTML=`<span class="p">${r.pos}</span><span class="d">${r.desc}</span><span class="q">${r.qty}</span><span class="m">${r.mat}${r.kg?` · ${r.kg.toLocaleString("es-CL")} kg/u`:""}</span>`;
    const pick=()=>{ if(!geo.has(r.pos)) return; selected = selected===r.pos?null:r.pos; applySel(); };
    li.addEventListener("click",pick);
    li.addEventListener("keydown",e=>{ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); pick(); } });
    ul.appendChild(li);
  });
}

// selección en el visor
const ray=new THREE.Raycaster(), mouse=new THREE.Vector2(); let downAt=null;
renderer.domElement.addEventListener("pointerdown",e=>downAt=[e.clientX,e.clientY]);
renderer.domElement.addEventListener("pointerup",e=>{
  if(!downAt||Math.hypot(e.clientX-downAt[0],e.clientY-downAt[1])>5||!current) return;
  const r=renderer.domElement.getBoundingClientRect();
  mouse.set(((e.clientX-r.left)/r.width)*2-1, -((e.clientY-r.top)/r.height)*2+1);
  ray.setFromCamera(mouse,camera);
  const hits=ray.intersectObject(current,true).filter(h=>h.object.visible && (!cutOn || clip.distanceToPoint(h.point)>=0));
  const pos = hits.length? posOf(hits[0].object):null;
  selected = (pos===selected)?null:pos; applySel();
  if(pos!==null){ const li=document.querySelector(`#list li[data-pos="${pos}"]`); li&&li.scrollIntoView({block:"nearest"}); }
});

el("exp").addEventListener("input",applyExplode);
el("cut").addEventListener("click",()=>{ cutOn=!cutOn; el("cut").setAttribute("aria-pressed",cutOn);
  current&&current.traverse(o=>{ if(o.isMesh) o.material.clippingPlanes = cutOn?[clip]:[]; }); });
el("iso").addEventListener("click",()=>{ isolate=!isolate; el("iso").setAttribute("aria-pressed",isolate); applySel(); });
el("reset").addEventListener("click",()=>{ el("exp").value=0; applyExplode(); selected=null; isolate=false; el("iso").setAttribute("aria-pressed",false); applySel(); resetView(); });
el("bA").addEventListener("click",()=>show("TT500-A"));
el("bB").addEventListener("click",()=>show("TT500-B"));

let start="TT500-A";
try{ const s=localStorage.getItem("tt500-variant"); if(s&&DATA[s]) start=s; }catch(e){}
if(location.hash==="#B") start="TT500-B";
resize(); show(start);
(function loop(){ requestAnimationFrame(loop); controls.update(); renderer.render(scene,camera); })();
</script>
```

---
Fin del documento.
