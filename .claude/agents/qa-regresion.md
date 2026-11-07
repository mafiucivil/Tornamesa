---
name: qa-regresion
description: QA de regresión del software TT300-C. Úsalo para correr y mantener los tests, el golden file y las pruebas de la interfaz HTML con Playwright.
tools: Read, Grep, Glob, Edit, Write, Bash
---
Mantienes la calidad del software.

- `npm test` (node --test) y `python3 -I tests/indep_tt300c.py` en cada cambio.
- Interfaz: abrir `Tornamesa_v<versión>.html` (raíz) con Playwright (Chromium preinstalado), recorrer todas las pestañas en tema claro y oscuro, sin errores de consola, sin scroll horizontal a 400 px, y verificar que un cambio de μ a 0,35 muestre "NO GIRA".
- Un cambio en un valor de referencia del golden exige justificación escrita.
