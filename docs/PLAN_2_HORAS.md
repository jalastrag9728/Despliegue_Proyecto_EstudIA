# Plan para sacar el MVP en menos de 2 horas

Este repositorio ya trae todo construido; el tiempo se usa en **entender, ejecutar, probar y documentar** (lo que el reto evalúa).

| Minuto | Actividad | Entregable |
|---|---|---|
| 0-10 | Instalar/abrir Docker Desktop, Git y Python; clonar el repo | `docker compose version` funciona |
| 10-25 | `docker compose up -d --build`; abrir `:8080`, `/health`, `:8404/stats`; leer `ARQUITECTURA.md` | Servicio con 2 instancias respondiendo |
| 25-45 | Prueba 1 y 2 a mano (alternancia de instancias, `docker stop`, mirar panel y logs) | Capturas del panel y de las respuestas |
| 45-65 | Pruebas 3 y 4 a mano (recrear contenedores; respaldo -> alteración -> restauración) | Anotar versión y SHA-256 antes/después |
| 65-80 | `python scripts/pruebas.py` (todo automático y repetible) | Carpeta `evidencias/` con informe, JSON y logs |
| 80-100 | Completar el esquema, tabla de limitaciones y factores de costo con **sus** resultados y tiempos | Póster / diapositiva de arquitectura |
| 100-110 | Subir a GitHub; ver pasar la CI (pestaña Actions) | Repositorio público/privado con CI verde |
| 110-120 | Ensayo del pitch de 3 minutos; `docker compose down -v` | Guion listo, recursos retirados |

## Guion de pitch de 3 minutos

1. **Problema** (20 s): una instancia, datos dentro de la app, sin recuperación probada.
2. **Solución** (40 s): 2 instancias + balanceador + volumen + respaldo con hash.
3. **Demostración** (80 s): `docker stop` de una instancia sin dejar de consultar; alteración y restauración con tiempo.
4. **Honestidad** (20 s): probado local; nube como diseño; esto no es alta disponibilidad de producción.
5. **Siguiente paso** (20 s): 2 zonas, respaldo a almacenamiento de objetos, alertas.

## Criterios de "MVP terminado"

- [ ] Las 4 pruebas del reto aprobadas y con evidencia.
- [ ] Tiempo de recuperación medido y anotado.
- [ ] Esquema de arquitectura y tabla de costos listos.
- [ ] Límites y alcance declarados.
- [ ] Sin secretos en el repo; recursos de prueba retirados.
