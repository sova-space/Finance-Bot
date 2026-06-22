#!/usr/bin/env bash
set -euo pipefail

export HERMES_HOME="${HERMES_HOME:-/data/.hermes}"
export HERMES_PROVIDER="${HERMES_PROVIDER:-openai-codex}"
export HERMES_MODEL="${HERMES_MODEL:-gpt-5.5}"
export HERMES_CONTINUE_SESSION="${HERMES_CONTINUE_SESSION:-finance-bot}"
export HERMES_DASHBOARD_PORT="${PORT:-${HERMES_DASHBOARD_PORT:-8080}}"
export HERMES_DASHBOARD_HOST="${HERMES_DASHBOARD_HOST:-0.0.0.0}"

mkdir -p "$HERMES_HOME"

python - <<'PY'
from pathlib import Path
import os
import yaml

home = Path(os.environ.get("HERMES_HOME", "/data/.hermes"))
home.mkdir(parents=True, exist_ok=True)
config_path = home / "config.yaml"
existing = {}
if config_path.exists():
    existing = yaml.safe_load(config_path.read_text()) or {}

def merge(a, b):
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out

token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    raise SystemExit("TELEGRAM_BOT_TOKEN is required")

desired = {
    "model": {
        "provider": os.environ.get("HERMES_PROVIDER", "openai-codex"),
        "default": os.environ.get("HERMES_MODEL", "gpt-5.5"),
    },
    "telegram": {
        "enabled": True,
        "bot_token": token,
    },
    "gateway": {
        "enabled": True,
    },
    "memory": {
        "memory_enabled": True,
        "user_profile_enabled": True,
    },
    "compression": {
        "codex_gpt55_autoraise": False,
    },
    "terminal": {
        "cwd": os.environ.get("RAILWAY_PROJECT_DIR", "/app"),
    },
    "stt": {
        "provider": "local",
        "local": {"model": os.environ.get("HERMES_STT_LOCAL_MODEL", "base")},
    },
}
config_path.write_text(yaml.safe_dump(merge(existing, desired), sort_keys=False))

soul = Path("/app/SOUL.md")
if soul.exists():
    (home / "SOUL.md").write_text(soul.read_text())
PY

if [ ! -s "$HERMES_HOME/auth.json" ]; then
  echo "Codex OAuth missing at $HERMES_HOME/auth.json; dashboard will start, gateway may fail until auth is uploaded." >&2
fi

hermes dashboard \
  --host "$HERMES_DASHBOARD_HOST" \
  --port "$HERMES_DASHBOARD_PORT" \
  --no-open \
  --insecure \
  --skip-build &
dashboard_pid=$!

shutdown() {
  kill "$dashboard_pid" 2>/dev/null || true
}
trap shutdown EXIT INT TERM

echo "Starting native Finance Hermes gateway: session=${HERMES_CONTINUE_SESSION} provider=${HERMES_PROVIDER} model=${HERMES_MODEL}"
exec hermes gateway run --replace --accept-hooks
