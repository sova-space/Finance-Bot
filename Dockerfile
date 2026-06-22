FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/hermes \
    && /opt/hermes/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/hermes/bin/pip install --no-cache-dir 'hermes-agent[voice]==0.17.0' 'aiohttp>=3.12'

ENV PATH="/opt/hermes/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV HERMES_HOME=/data/.hermes
ENV HERMES_PROVIDER=openai-codex
ENV HERMES_MODEL=gpt-5.5
ENV HERMES_CONTINUE_SESSION=finance-bot

WORKDIR /app
COPY . .
RUN chmod +x scripts/start-finance-hermes.sh

EXPOSE 8080
CMD ["scripts/start-finance-hermes.sh"]
