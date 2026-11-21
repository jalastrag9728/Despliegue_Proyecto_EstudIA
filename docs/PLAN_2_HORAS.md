# Plan para sacar el MVP en menos de 2 horas

El repositorio ya trae el despliegue construido; el tiempo se usa en entender, ejecutar, probar y documentar.
(La guía orienta 4 horas: 10 min retomar plan · 100 construir · 15 pausa · 60 probar · 35 ajustar · 15 documentar · 5 cierre. Este plan comprime el núcleo en < 2 h
y deja el resto como margen para ajustes y para I06.)

| Minuto | Actividad | Entregable |
|---|---|---|
| 0-10 | Abrir Docker Desktop; clonar; `docker compose version` | Entorno listo |
| 10-20 | `python scripts/datos.py preparar` y `python scripts/ejecutar_local.py` (reconocer la app); detener con Ctrl+C | Entender `/`, `/health`, `/pedidos` |
| 20-35 | `docker compose up -d --build`; esperar *healthy*; abrir `/health` y `/pedidos` | Servicio con 2 instancias |
| 35-45 | Leer `docs/EXPLICACION_DEL_DESPLIEGUE.md` (las 6 preguntas) | Poder explicarlo |
| 45-75 | I01-I05 a mano (o `pruebas_automaticas.py`) | JSON en `evidencias/` |
| 75-95 | Completar fichas con **sus** tiempos y el esquema de arquitectura / puntos únicos de fallo | Bitácora |
| 95-110 | Subir a GitHub; ver la CI | Repo + Actions |
| 110-120 | Ensayo del pitch; `docker compose down` | Guion listo |

## Pitch de 3 minutos
1. **Problema** (20 s): una instancia, datos dentro de la app, sin recuperación probada.
2. **Solución** (40 s): 2 instancias + proxy + datos fuera + respaldo con huella.
3. **Demostración** (80 s): `stop app1` sin dejar de consultar; alterar datos → 503 en ambas → restaurar con tiempo.
4. **Honestidad** (20 s): probado local; nube como diseño; puntos únicos de fallo.
5. **Siguiente paso** (20 s): datos fuera del computador, 2 zonas, health checks activos, alertas.

## "MVP terminado"
- [ ] I01-I05 con evidencia; I06 hecha por otro integrante (o marcada "No realizado").
- [ ] Tiempos anotados; esquema y puntos únicos de fallo listos.
- [ ] Límites declarados; sin secretos; `docker compose down` hecho.
