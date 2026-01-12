#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${EXPOSITION_ENDPOINT:-}" ]]; then
  echo "EXPOSITION_ENDPOINT env var is required."
  exit 2
fi

out_json="$(mktemp)"

# Prefer JSON mode for machine processing. The CLI supports --json per README.
# If the CLI changes flags, set CLOUDFLARE_SPEED_CLI_ARGS to override.
args=(--json --auto-save false)
if [[ -n "${CLOUDFLARE_SPEED_CLI_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  args=(${CLOUDFLARE_SPEED_CLI_ARGS})
fi

echo "Starting Cloudflare Speed Test..."
cloudflare-speed-cli "${args[@]}" >"$out_json"

echo "Exporting metrics to ${EXPOSITION_ENDPOINT}..."
python3 /app/otlp_metrics.py --input "$out_json"

echo "Scan finished successfully."
rm -f "$out_json"
