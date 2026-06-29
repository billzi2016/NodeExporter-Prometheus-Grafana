#!/usr/bin/env python3
"""Custom FastAPI exporter for host metrics."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI, Response
from prometheus_client import CollectorRegistry
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import Gauge
from prometheus_client import generate_latest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_TEST_DIR = PROJECT_ROOT / "API_test"
if str(API_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(API_TEST_DIR))

import cpu_profiler
import gpu_profiler
import ram_profiler


app = FastAPI(title="Custom Host Exporter", version="0.1.0")


def run_command(command: list[str]) -> str:
    """Execute a command and return stdout, or an unavailable marker."""
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, PermissionError, subprocess.CalledProcessError) as exc:
        return f"<unavailable: {exc}>"
    return result.stdout.strip()


def parse_df_root() -> tuple[float | None, float | None, float | None, float | None]:
    """Read root disk usage from df output."""
    output = run_command(["df", "-k", "/"])
    if output.startswith("<unavailable:"):
        return None, None, None, None

    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) < 2:
        return None, None, None, None

    parts = re.split(r"\s+", lines[1].strip())
    if len(parts) < 5:
        return None, None, None, None

    try:
        total_kb = float(parts[1])
        used_kb = float(parts[2])
        avail_kb = float(parts[3])
        capacity = float(parts[4].rstrip("%"))
    except ValueError:
        return None, None, None, None

    return total_kb * 1024, used_kb * 1024, avail_kb * 1024, capacity


def parse_network_interfaces() -> Iterable[tuple[str, float, float]]:
    """Read basic network byte counters from netstat."""
    output = run_command(["netstat", "-ib"])
    if output.startswith("<unavailable:"):
        return []

    seen: set[str] = set()
    rows: list[tuple[str, float, float]] = []
    for line in output.splitlines()[1:]:
        columns = re.split(r"\s+", line.strip())
        if len(columns) < 10:
            continue

        name = columns[0]
        if name == "lo0" or name in seen:
            continue

        try:
            ibytes = float(columns[6])
            obytes = float(columns[9])
        except ValueError:
            continue

        seen.add(name)
        rows.append((name, ibytes, obytes))

    return rows


def populate_cpu_metrics(registry: CollectorRegistry) -> None:
    """Populate CPU metrics."""
    cpu_percentages = cpu_profiler.read_cpu_percentages() or {}

    idle = cpu_percentages.get("idle", 0.0)
    Gauge(
        "custom_host_cpu_used_percent",
        "Current host CPU usage percentage.",
        registry=registry,
    ).set(100.0 - idle if cpu_percentages else 0.0)
    Gauge(
        "custom_host_cpu_user_percent",
        "Current host CPU user percentage.",
        registry=registry,
    ).set(cpu_percentages.get("user", 0.0))
    Gauge(
        "custom_host_cpu_system_percent",
        "Current host CPU system percentage.",
        registry=registry,
    ).set(cpu_percentages.get("system", 0.0))
    Gauge(
        "custom_host_cpu_idle_percent",
        "Current host CPU idle percentage.",
        registry=registry,
    ).set(idle)


def populate_memory_metrics(registry: CollectorRegistry) -> None:
    """Populate RAM metrics."""
    total_memory = ram_profiler.read_total_memory()
    page_size, stats = ram_profiler.read_vm_stats()

    if total_memory is None or page_size is None or not stats:
        return

    free_pages = stats.get("Pages free", 0)
    speculative_pages = stats.get("Pages speculative", 0)
    active_pages = stats.get("Pages active", 0)
    inactive_pages = stats.get("Pages inactive", 0)
    wired_pages = stats.get("Pages wired down", 0)
    compressed_pages = stats.get("Pages occupied by compressor", 0)

    used_pages = active_pages + inactive_pages + wired_pages + compressed_pages
    free_like_pages = free_pages + speculative_pages

    used_bytes = used_pages * page_size
    free_bytes = free_like_pages * page_size

    Gauge(
        "custom_host_memory_total_bytes",
        "Total host memory in bytes.",
        registry=registry,
    ).set(total_memory)
    Gauge(
        "custom_host_memory_used_bytes",
        "Used host memory in bytes.",
        registry=registry,
    ).set(used_bytes)
    Gauge(
        "custom_host_memory_free_bytes",
        "Free host memory in bytes.",
        registry=registry,
    ).set(free_bytes)
    Gauge(
        "custom_host_memory_used_percent",
        "Used host memory percentage.",
        registry=registry,
    ).set((used_bytes / total_memory) * 100 if total_memory else 0.0)


def populate_gpu_metrics(registry: CollectorRegistry) -> None:
    """Populate GPU metrics."""
    metrics = gpu_profiler.collect_gpu_metrics()

    for metric_name, label in (
        ("custom_host_gpu_utilization_percent", "Utilization"),
        ("custom_host_gpu_renderer_utilization_percent", "Renderer Utilization"),
        ("custom_host_gpu_tiler_utilization_percent", "Tiler Utilization"),
    ):
        raw = metrics.get(label, "unavailable")
        if raw == "unavailable":
            continue
        try:
            value = float(str(raw).rstrip("%"))
        except ValueError:
            continue
        Gauge(
            metric_name,
            f"{label} reported by the host GPU sampler.",
            registry=registry,
        ).set(value)


def populate_disk_metrics(registry: CollectorRegistry) -> None:
    """Populate root disk metrics."""
    total_bytes, used_bytes, avail_bytes, used_percent = parse_df_root()
    if total_bytes is None:
        return

    Gauge(
        "custom_host_disk_root_total_bytes",
        "Root filesystem total bytes.",
        registry=registry,
    ).set(total_bytes)
    Gauge(
        "custom_host_disk_root_used_bytes",
        "Root filesystem used bytes.",
        registry=registry,
    ).set(used_bytes)
    Gauge(
        "custom_host_disk_root_available_bytes",
        "Root filesystem available bytes.",
        registry=registry,
    ).set(avail_bytes)
    Gauge(
        "custom_host_disk_root_used_percent",
        "Root filesystem used percentage.",
        registry=registry,
    ).set(used_percent)


def populate_network_metrics(registry: CollectorRegistry) -> None:
    """Populate interface byte counters."""
    receive_gauge = Gauge(
        "custom_host_network_receive_bytes",
        "Received bytes by interface.",
        ["interface"],
        registry=registry,
    )
    transmit_gauge = Gauge(
        "custom_host_network_transmit_bytes",
        "Transmitted bytes by interface.",
        ["interface"],
        registry=registry,
    )

    for interface, ibytes, obytes in parse_network_interfaces():
        receive_gauge.labels(interface=interface).set(ibytes)
        transmit_gauge.labels(interface=interface).set(obytes)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Basic health check."""
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    """Expose Prometheus metrics."""
    registry = CollectorRegistry()
    populate_cpu_metrics(registry)
    populate_memory_metrics(registry)
    populate_gpu_metrics(registry)
    populate_disk_metrics(registry)
    populate_network_metrics(registry)
    payload = generate_latest(registry)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
