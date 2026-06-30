#!/usr/bin/env python3
"""Homemade FastAPI exporter for host metrics."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, Response
from prometheus_client import CollectorRegistry
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import Gauge
from prometheus_client import generate_latest


PROFILER_DIR = Path(__file__).resolve().parent
if str(PROFILER_DIR) not in sys.path:
    sys.path.insert(0, str(PROFILER_DIR))

from mac_profiler import cpu_profiler
from mac_profiler import disk_profiler
from mac_profiler import gpu_profiler
from mac_profiler import network_profiler
from mac_profiler import ram_profiler


app = FastAPI(title="Homemade Profiler", version="0.1.0")


def populate_cpu_metrics(registry: CollectorRegistry) -> None:
    """Populate CPU metrics."""
    cpu_metrics = cpu_profiler.collect_cpu_metrics() or {}
    idle = cpu_metrics.get("idle_percent", 0.0)

    Gauge(
        "custom_host_cpu_used_percent",
        "Current host CPU usage percentage.",
        registry=registry,
    ).set(cpu_metrics.get("used_percent", 0.0))
    Gauge(
        "custom_host_cpu_user_percent",
        "Current host CPU user percentage.",
        registry=registry,
    ).set(cpu_metrics.get("user_percent", 0.0))
    Gauge(
        "custom_host_cpu_system_percent",
        "Current host CPU system percentage.",
        registry=registry,
    ).set(cpu_metrics.get("system_percent", 0.0))
    Gauge(
        "custom_host_cpu_idle_percent",
        "Current host CPU idle percentage.",
        registry=registry,
    ).set(idle)


def populate_memory_metrics(registry: CollectorRegistry) -> None:
    """Populate RAM metrics."""
    memory_metrics = ram_profiler.collect_memory_metrics()
    if not memory_metrics:
        return

    Gauge(
        "custom_host_memory_total_bytes",
        "Total host memory in bytes.",
        registry=registry,
    ).set(memory_metrics["total_bytes"])
    Gauge(
        "custom_host_memory_used_bytes",
        "Used host memory in bytes.",
        registry=registry,
    ).set(memory_metrics["used_bytes"])
    Gauge(
        "custom_host_memory_free_bytes",
        "Free host memory in bytes.",
        registry=registry,
    ).set(memory_metrics["free_bytes"])
    Gauge(
        "custom_host_memory_used_percent",
        "Used host memory percentage.",
        registry=registry,
    ).set(memory_metrics["used_percent"])


def populate_gpu_metrics(registry: CollectorRegistry) -> None:
    """Populate GPU metrics."""
    snapshot = gpu_profiler.collect_gpu_snapshot()
    metrics = snapshot["metrics"]

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
    disk_snapshot = disk_profiler.collect_disk_snapshot()
    root = disk_snapshot.get("root")
    if not root:
        return

    Gauge(
        "custom_host_disk_root_total_bytes",
        "Root filesystem total bytes.",
        registry=registry,
    ).set(root["total_bytes"])
    Gauge(
        "custom_host_disk_root_used_bytes",
        "Root filesystem used bytes.",
        registry=registry,
    ).set(root["used_bytes"])
    Gauge(
        "custom_host_disk_root_available_bytes",
        "Root filesystem available bytes.",
        registry=registry,
    ).set(root["available_bytes"])
    Gauge(
        "custom_host_disk_root_used_percent",
        "Root filesystem used percentage.",
        registry=registry,
    ).set(root["used_percent"])


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

    snapshot = network_profiler.collect_network_snapshot()
    for row in snapshot["interfaces"]:
        interface = str(row["interface"])
        receive_gauge.labels(interface=interface).set(float(row["receive_bytes"]))
        transmit_gauge.labels(interface=interface).set(float(row["transmit_bytes"]))


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
