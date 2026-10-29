# syntax=docker/dockerfile:1
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 git curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock .
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.lock; else pip install --no-cache-dir -r requirements.lock; fi
COPY . .
RUN useradd --create-home studio && mkdir -p data workspace outputs agent_workspace assets videofx_outputs && chmod 700 data && chown -R studio:studio /app
USER studio
EXPOSE 8008
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8008", "--workers", "1", "--no-proxy-headers"]
