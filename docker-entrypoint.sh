#!/bin/sh
set -e

# Defaults
CONFIG_FILE="${CONFIG_FILE:-/repo/.docforge.yml}"
REPO_PATH="${REPO_PATH:-/repo}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"

# If no .docforge.yml exists in /repo, use the default config
if [ ! -f "${CONFIG_FILE}" ] && [ "${CONFIG_FILE}" = "/repo/.docforge.yml" ]; then
    echo "[docforge] No config found at ${CONFIG_FILE}, using /app/docforge.default.yml"
    CONFIG_FILE="/app/docforge.default.yml"
fi

# If user passed arguments, use them; otherwise use defaults
if [ "$#" -eq 0 ]; then
    exec python /app/generate.py \
        --config "${CONFIG_FILE}" \
        --repo-path "${REPO_PATH}" \
        --output-dir "${OUTPUT_DIR}"
else
    exec python /app/generate.py "$@"
fi
