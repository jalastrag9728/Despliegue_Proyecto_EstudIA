# Imagen del servicio de consulta de Nodo Ruta.
# - Base pequeña y oficial. Sin dependencias externas (solo biblioteca estándar).
# - Corre como usuario SIN privilegios. No contiene secretos ni los datos "vivos":
#   los datos se montan desde un volumen en /data.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_FILE=/data/pedidos.json \
    PORT=8000

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app
COPY app.py ./
# Semilla de datos: solo se copia al volumen la PRIMERA vez (ver servicio init-datos).
COPY seed/ ./seed/

USER 10001
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["python", "/app/app.py"]
