FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY services/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared /tmp/shared
RUN pip install --no-cache-dir /tmp/shared && rm -rf /tmp/shared

COPY services/policy-admin/app ./app
COPY services/start.sh ./start.sh
RUN chmod +x start.sh

USER appuser
EXPOSE 8000
CMD ["./start.sh"]
