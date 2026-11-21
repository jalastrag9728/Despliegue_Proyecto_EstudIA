# Evidencias

`python scripts/pruebas.py` deja aquí, automáticamente:

- `informe_<fecha>.md` - tabla de pruebas con resultado y tiempos.
- `resultado_<fecha>.json` - mismos datos en formato máquina.
- `registros_<fecha>.log` - registros del balanceador y de las instancias (los "registros consultados").

Estos archivos están ignorados por git (`.gitignore`). Para mostrarlos en el repositorio, copie el informe que quiera conservar
a `docs/evidencias/` o súbalo como adjunto del pitch.

## Plantilla para pruebas manuales

| Fecha/hora | Prueba | Comando | Qué se observó | Tiempo | Aprobada |
|---|---|---|---|---|---|
| | Consulta normal | `curl.exe -i http://localhost:8080/pedidos` | | | |
| | Caída de instancia | `docker stop <id>` + consultas | | | |
| | Recrear contenedores | `docker compose up -d --force-recreate app` | | | |
| | Respaldo/alteración/restauración | `docker compose run --rm ops backup / tamper / restore` | | | |
