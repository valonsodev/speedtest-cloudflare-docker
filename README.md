# speedtest-cloudflare-docker

Runs `cloudflare-speed-cli --json` on a schedule and POSTs the results in Prometheus exposition format to an HTTP endpoint.

## docker-compose example

```yaml
services:
  speedtest:
    image: ghcr.io/<owner>/speedtest-cloudflare-docker:<tag>
    environment:
      TZ: UTC
      SCHEDULE: "*/15 * * * *"
      RUN_ON_START: "true"

      # Full URL to POST the Prometheus exposition payload.
      EXPOSITION_ENDPOINT: "http://example-prometheus-ingest:8428/api/v1/import/prometheus"

      # Optional: extra request headers (comma-separated key=value pairs)
      # EXPOSITION_HEADERS: "Authorization=Bearer <token>"

      # Optional: extra labels appended to every metric (comma-separated key=value pairs)
      # EXPOSITION_EXTRA_LABELS: "env=prod,region=us-east-1"

      # Optional: label value for `service_name`
      # SERVICE_NAME: "speedtest-cloudflare-docker"
```


## Configuration

### Scheduling

- `SCHEDULE` (required): cron expression, e.g. `*/15 * * * *`
- `RUN_ON_START` (optional, default `true`): run once immediately in addition to cron
- `TZ` (optional): timezone for cron, e.g. `UTC`

### Exposition export

- `EXPOSITION_ENDPOINT` (required): full URL to POST Prometheus exposition payload
- `EXPOSITION_HEADERS` (optional): comma-separated headers
  - Format: `Header=Value,Header2=Value2`
- `EXPOSITION_EXTRA_LABELS` (optional): comma-separated labels appended to every metric
  - Format: `label=value,label2=value2`

### Labels

The exporter adds a small set of low-cardinality labels:

- `service_name` (from `SERVICE_NAME`, default `speedtest-cloudflare-docker`)
- `host`
- `colo`
- `interface_name`
- `is_wireless`
