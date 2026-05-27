#!/usr/bin/with-contenv bashio
set -euo pipefail

mkdir -p /data/codex-home /config/codex_tasks
export CODEX_HOME=/data/codex-home
export HOME=/data
export PYTHONDONTWRITEBYTECODE=1

if [ -z "$(bashio::config 'api_token')" ]; then
    generated_token="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
    export CODEX_WORKER_TOKEN="${generated_token}"
    bashio::addon.option 'api_token' "${generated_token}"
    bashio::log.info "Generated a random worker API token and stored it in the add-on options."
fi

echo "Codex CLI Worker starting"
python3 /server.py
