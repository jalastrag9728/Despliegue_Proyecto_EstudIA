# Imagen del servicio Nodo Ruta (app.py, solo biblioteca estandar de Python).
# - Base oficial y pequena.
# - Corre como usuario SIN privilegios.
# - NO contiene los datos: se montan desde data/pedidos.json (ver compose.yaml).
# Si su paquete del reto trae un Dockerfile propio, puede usarlo en su lugar.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app
COPY app.py ./

USER 10001
EXPOSE 8080

CMD ["python", "app.py"]
