#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SCHEDULE:-}" ]]; then
  echo "[$(date +"%d/%m/%Y %H:%M:%S")] SCHEDULE env var is required (cron syntax)."
  exit 2
fi

if [[ -z "${EXPOSITION_ENDPOINT:-}" ]]; then
  echo "[$(date +"%d/%m/%Y %H:%M:%S")] EXPOSITION_ENDPOINT env var is required (full URL for POSTing Prometheus exposition data)."
  exit 2
fi

mkdir -p /var/log

# Ensure a trailing newline so vixie-cron parsing is happy.
cat >/etc/crontabs/root <<EOF
${SCHEDULE} /app/run-once.sh > /proc/1/fd/1 2>&1
EOF

echo "[$(date +"%d/%m/%Y %H:%M:%S")] Installed crontab: ${SCHEDULE}"

# Run immediately once at startup (optional), controlled via RUN_ON_START.
if [[ "${RUN_ON_START:-true}" == "true" ]]; then
  echo "[$(date +"%d/%m/%Y %H:%M:%S")] Running once on start..."
  /app/run-once.sh || true
fi

exec crond -f -l 8
