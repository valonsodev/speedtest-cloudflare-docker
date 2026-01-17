#!/usr/bin/env python3

import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


def ns_now() -> int:
    return int(time.time() * 1_000_000_000)


def get_timestamp() -> str:
    return time.strftime("%d/%m/%Y %H:%M:%S")


def get(obj: Any, path: List[str], default: Any = None) -> Any:
    cur = obj
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def as_float(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return None
    return None


def prom_escape_label_value(value: str) -> str:
    # See Prometheus exposition format escaping rules.
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def prom_label(key: str, value: Optional[str]) -> Optional[tuple[str, str]]:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return (key, value)


def parse_env_headers(raw: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    raw = raw.strip()
    if not raw:
        return headers

    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
        elif ":" in part:
            k, v = part.split(":", 1)
        else:
            continue
        headers[k.strip()] = v.strip()

    return headers


def render_prom_labels(labels: Dict[str, str]) -> str:
    if not labels:
        return ""
    items = ",".join(
        f'{k}="{prom_escape_label_value(v)}"' for k, v in sorted(labels.items())
    )
    return "{" + items + "}"


def metric_line(
    name: str, value: Optional[float], labels: Dict[str, str]
) -> Optional[str]:
    if value is None:
        return None
    return f"{name}{render_prom_labels(labels)} {float(value)}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    endpoint = os.getenv("EXPOSITION_ENDPOINT", "").strip()
    if not endpoint:
        raise SystemExit(f"[{get_timestamp()}] EXPOSITION_ENDPOINT is required")

    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    exposition_url = endpoint

    with open(args.input, "r", encoding="utf-8") as f:
        d = json.load(f)

    download = get(d, ["download"], {}) or {}
    upload = get(d, ["upload"], {}) or {}
    idle = get(d, ["idle_latency"], {}) or {}
    lld = get(d, ["loaded_latency_download"], {}) or {}
    llu = get(d, ["loaded_latency_upload"], {}) or {}

    service_name = (
        os.getenv("SERVICE_NAME", "speedtest-cloudflare-docker").strip()
        or "speedtest-cloudflare-docker"
    )
    colo = get(d, ["colo"]) or get(d, ["meta", "colo"]) or ""
    interface_name = get(d, ["interface_name"]) or ""
    is_wireless = get(d, ["is_wireless"], None)

    base_labels: Dict[str, str] = {}
    for item in [
        prom_label("service_name", service_name),
        prom_label("host", socket.gethostname()),
        prom_label("colo", str(colo) if colo is not None else None),
        prom_label(
            "interface_name",
            str(interface_name) if interface_name is not None else None,
        ),
        prom_label(
            "is_wireless",
            str(is_wireless).lower() if isinstance(is_wireless, bool) else None,
        ),
    ]:
        if item is not None:
            k, v = item
            base_labels[k] = v

    # Extra labels via EXPOSITION_EXTRA_LABELS (key=value,key2=value2)
    extra = os.getenv("EXPOSITION_EXTRA_LABELS", "").strip()
    if extra:
        for part in extra.split(","):
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k and v:
                base_labels[k] = v

    lines: List[str] = []
    candidates = [
        ("network_download_mbps", as_float(get(download, ["mbps"]))),
        ("network_download_bytes", as_float(get(download, ["bytes"]))),
        ("network_download_duration_ms", as_float(get(download, ["duration_ms"]))),
        ("network_download_mean_mbps", as_float(get(download, ["mean_mbps"]))),
        ("network_download_median_mbps", as_float(get(download, ["median_mbps"]))),
        ("network_download_p25_mbps", as_float(get(download, ["p25_mbps"]))),
        ("network_download_p75_mbps", as_float(get(download, ["p75_mbps"]))),
        ("network_upload_mbps", as_float(get(upload, ["mbps"]))),
        ("network_upload_bytes", as_float(get(upload, ["bytes"]))),
        ("network_upload_duration_ms", as_float(get(upload, ["duration_ms"]))),
        ("network_upload_mean_mbps", as_float(get(upload, ["mean_mbps"]))),
        ("network_upload_median_mbps", as_float(get(upload, ["median_mbps"]))),
        ("network_upload_p25_mbps", as_float(get(upload, ["p25_mbps"]))),
        ("network_upload_p75_mbps", as_float(get(upload, ["p75_mbps"]))),
        ("network_idle_latency_sent", as_float(get(idle, ["sent"]))),
        ("network_idle_latency_received", as_float(get(idle, ["received"]))),
        ("network_idle_latency_loss", as_float(get(idle, ["loss"]))),
        ("network_idle_latency_min_ms", as_float(get(idle, ["min_ms"]))),
        ("network_idle_latency_mean_ms", as_float(get(idle, ["mean_ms"]))),
        ("network_idle_latency_median_ms", as_float(get(idle, ["median_ms"]))),
        ("network_idle_latency_p25_ms", as_float(get(idle, ["p25_ms"]))),
        ("network_idle_latency_p75_ms", as_float(get(idle, ["p75_ms"]))),
        ("network_idle_latency_max_ms", as_float(get(idle, ["max_ms"]))),
        ("network_idle_latency_jitter_ms", as_float(get(idle, ["jitter_ms"]))),
        ("network_loaded_latency_download_sent", as_float(get(lld, ["sent"]))),
        ("network_loaded_latency_download_received", as_float(get(lld, ["received"]))),
        ("network_loaded_latency_download_loss", as_float(get(lld, ["loss"]))),
        ("network_loaded_latency_download_min_ms", as_float(get(lld, ["min_ms"]))),
        ("network_loaded_latency_download_mean_ms", as_float(get(lld, ["mean_ms"]))),
        (
            "network_loaded_latency_download_median_ms",
            as_float(get(lld, ["median_ms"])),
        ),
        ("network_loaded_latency_download_p25_ms", as_float(get(lld, ["p25_ms"]))),
        ("network_loaded_latency_download_p75_ms", as_float(get(lld, ["p75_ms"]))),
        ("network_loaded_latency_download_max_ms", as_float(get(lld, ["max_ms"]))),
        (
            "network_loaded_latency_download_jitter_ms",
            as_float(get(lld, ["jitter_ms"])),
        ),
        ("network_loaded_latency_upload_sent", as_float(get(llu, ["sent"]))),
        ("network_loaded_latency_upload_received", as_float(get(llu, ["received"]))),
        ("network_loaded_latency_upload_loss", as_float(get(llu, ["loss"]))),
        ("network_loaded_latency_upload_min_ms", as_float(get(llu, ["min_ms"]))),
        ("network_loaded_latency_upload_mean_ms", as_float(get(llu, ["mean_ms"]))),
        ("network_loaded_latency_upload_median_ms", as_float(get(llu, ["median_ms"]))),
        ("network_loaded_latency_upload_p25_ms", as_float(get(llu, ["p25_ms"]))),
        ("network_loaded_latency_upload_p75_ms", as_float(get(llu, ["p75_ms"]))),
        ("network_loaded_latency_upload_max_ms", as_float(get(llu, ["max_ms"]))),
        ("network_loaded_latency_upload_jitter_ms", as_float(get(llu, ["jitter_ms"]))),
        ("network_interface_link_speed_mbps", as_float(get(d, ["link_speed_mbps"]))),
    ]

    for name, value in candidates:
        line = metric_line(name, value, base_labels)
        if line is not None:
            lines.append(line)

    if not lines:
        raise SystemExit(f"[{get_timestamp()}] No metrics extracted from JSON.")

    payload = "\n".join(lines) + "\n"

    if dry_run:
        sys.stdout.write(payload)
        return 0

    headers: Dict[str, str] = {"Content-Type": "text/plain"}
    headers.update(parse_env_headers(os.getenv("EXPOSITION_HEADERS", "")))

    req = urllib.request.Request(
        exposition_url,
        data=payload.encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 400:
                body = resp.read().decode("utf-8", errors="replace")
                raise SystemExit(
                    f"[{get_timestamp()}] Exposition export failed: {resp.status} {body}"
                )
            print(
                f"[{get_timestamp()}] Successfully exported metrics to {exposition_url} (HTTP {resp.status})"
            )
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"[{get_timestamp()}] Exposition export failed: {e.code} {e.reason}: {body} (POST {exposition_url})"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
