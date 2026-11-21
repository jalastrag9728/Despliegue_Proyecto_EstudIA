# Evidencias

- `PLANTILLA_EVIDENCIAS.md`: plantilla del reto para pruebas manuales (una ficha por prueba).
- `python scripts/pruebas_automaticas.py` crea `auto_<fecha>/` con:
  `informe.md` (fichas I01-I06), `resultado.json`, un JSON por prueba de `verificar_servicio.py` y `registros.log`.
- `verificar_servicio.py` **no sobrescribe** evidencia: use un `--salida` nuevo en cada prueba manual.

Esta carpeta está ignorada por git. Para publicar un informe, copie el que quiera conservar a `docs/evidencias/`.
No incluya secretos en capturas ni archivos.
