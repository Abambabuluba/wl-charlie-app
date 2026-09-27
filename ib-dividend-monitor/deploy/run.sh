#!/usr/bin/env bash
# Envoltorio para cron: entra en la carpeta del proyecto, usa su entorno virtual y guarda un log.
# Uso: deploy/run.sh daily | deploy/run.sh report --send | deploy/run.sh margin-live
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/logs
exec .venv/bin/divmon "$@" >> "data/logs/divmon-$(date +%Y-%m).log" 2>&1
