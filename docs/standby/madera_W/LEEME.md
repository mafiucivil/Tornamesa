# Cubierta de madera W: planos en stand by

Por decisión del mandante (09-11-2026), todo lo relacionado con la cubierta de madera W queda en stand by mientras se entregan las otras alternativas.

## Estado

- **Núcleo de cálculo de W:** integrado en la rama (5e2bce5, 6712590). Usa la plancha rebajada, el anillo superior R840–R1000 de t 27, la pared R840–860 y tablones de 45 enrasados. Pasa `npm test`.
- **Planos de W (`cad/`):** el redibujo quedó a medio hacer. El trabajo sin commitear del agente de planos está guardado completo en `cad_wip_sobre_e0fc484.patch`, generado sobre el commit e0fc484.
- **Juegos de planos y memoria:** en esta entrega no incluyen la variante W.

## Cómo retomar

```bash
git checkout claude/dreamy-allen-r5dzqu
git apply --3way docs/standby/madera_W/cad_wip_sobre_e0fc484.patch
```

Lo último que estaba haciendo el agente era una corrida completa de W con el código más reciente; antes había reemplazado nombres de parámetros y corregido una cadena cerrada de cotas. Antes de seguir hay que volver a correr los controles de `cad/`.

## Supuestos de W pendientes de confirmar con el mandante

1. **t_madera:** 45 mm (se pedía 50).
2. **Anillo superior:** una pieza de 27 mm.
3. **k_hmad = 0,10:** con este valor, el apoyo lateral a 80 °C da FU 1,07.
4. **Drenaje del rebaje:** pendiente.
5. **Fijación de tablones:** M10 en taladro ciego.
6. **Criterio de la pared:** AISC 0,6Fy en lugar de BTH-1.
7. **Térmico C3 + W:** la plancha inferior queda en FU 1,01.
