# syntax=docker/dockerfile:1

FROM alpine:3.20

ARG CLOUDFLARE_SPEED_CLI_VERSION

RUN apk add --no-cache \
    bash \
    ca-certificates \
    curl \
    tzdata \
    python3 \
    && update-ca-certificates

# Install the cloudflare-speed-cli static binary for the target arch.
# Binaries are MUSL, so they run fine on Alpine.
RUN set -eux; \
    arch="$(apk --print-arch)"; \
    case "$arch" in \
      x86_64) target="x86_64-unknown-linux-musl" ;; \
      aarch64) target="aarch64-unknown-linux-musl" ;; \
      *) echo "Unsupported arch: $arch"; exit 1 ;; \
    esac; \
    version="${CLOUDFLARE_SPEED_CLI_VERSION:-latest}"; \
    if [ "$version" = "latest" ]; then \
      version="$(curl -fsSL https://api.github.com/repos/kavehtehrani/cloudflare-speed-cli/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')"; \
    fi; \
    url="https://github.com/kavehtehrani/cloudflare-speed-cli/releases/download/${version}/cloudflare-speed-cli-${target}.tar.xz"; \
    curl -fsSL "$url" -o /tmp/cloudflare-speed-cli.tar.xz; \
    mkdir -p /tmp/cfcli; \
    tar -C /tmp/cfcli -xJf /tmp/cloudflare-speed-cli.tar.xz; \
    mv "/tmp/cfcli/cloudflare-speed-cli-${target}/cloudflare-speed-cli" /usr/local/bin/cloudflare-speed-cli; \
    chmod +x /usr/local/bin/cloudflare-speed-cli; \
    rm -rf /tmp/cloudflare-speed-cli.tar.xz /tmp/cfcli; \
    cloudflare-speed-cli --help >/dev/null


WORKDIR /app

COPY app/ /app/
RUN chmod +x /app/entrypoint.sh /app/run-once.sh /app/otlp_metrics.py

ENV SCHEDULE="*/15 * * * *"

CMD ["/app/entrypoint.sh"]
