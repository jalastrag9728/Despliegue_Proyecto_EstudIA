# Imagen del servicio Nodo Ruta (Django + Gunicorn).
# - Base oficial y pequena.
# - Corre como usuario SIN privilegios.
# - NO contiene los datos: se montan desde data/pedidos.json (ver compose.yaml).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py ./
COPY pedidos.json ./
COPY scripts ./scripts
COPY nodoruta_web ./nodoruta_web

USER 10001
EXPOSE 8080

CMD ["gunicorn", "nodoruta_web.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "2", "--worker-tmp-dir", "/tmp", "--access-logfile", "-", "--error-logfile", "-"]
