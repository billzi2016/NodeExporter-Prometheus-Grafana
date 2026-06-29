#!/usr/bin/env python3
"""打印 Apple Silicon / macOS 当前 GPU 使用线索。"""

from __future__ import annotations

import json
import plistlib
import re
import subprocess
from typing import Any


def run_command(command: list[str]) -> str:
    """执行系统命令并返回输出。失败时返回占位字符串。"""
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        return f"<unavailable: {exc}>"
    return result.stdout.strip()


def run_json_command(command: list[str]) -> dict[str, Any] | list[Any] | None:
    """执行 JSON 命令并解析结果。"""
    output = run_command(command)
    if not output or output.startswith("<unavailable:"):
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def print_section(title: str) -> None:
    """统一打印分节标题。"""
    print(f"\n=== {title} ===")


def run_plist_command(command: list[str]) -> Any | None:
    """执行返回 plist 的命令，并解析结果。"""
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    if not result.stdout:
        return None

    try:
        return plistlib.loads(result.stdout)
    except Exception:
        return None


def print_gpu_summary() -> None:
    """打印 GPU 设备摘要，只保留稳定且有意义的字段。"""
    display_info = run_json_command(["system_profiler", "SPDisplaysDataType", "-json"]) or {}
    display_items = display_info.get("SPDisplaysDataType", []) if isinstance(display_info, dict) else []

    print_section("GPU Devices")
    if not display_items:
        print("No GPU/display data returned by system_profiler.")
        return

    for index, gpu in enumerate(display_items, start=1):
        name = gpu.get("_name") or gpu.get("sppci_model") or "unknown"
        print(f"GPU {index} Name      : {name}")
        print("-" * 40)


def collect_nested_objects(node: Any, results: list[dict[str, Any]]) -> None:
    """递归遍历 plist 结构，收集所有字典节点。"""
    if isinstance(node, dict):
        results.append(node)
        for value in node.values():
            collect_nested_objects(value, results)
        return

    if isinstance(node, list):
        for item in node:
            collect_nested_objects(item, results)


def normalize_metric(value: Any) -> str:
    """把不同格式的利用率值统一转换成可打印字符串。"""
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}%"

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return "unavailable"
        if stripped.endswith("%"):
            return stripped
        try:
            return f"{float(stripped):.2f}%"
        except ValueError:
            return stripped

    return "unavailable"


def collect_gpu_metrics() -> dict[str, str]:
    """从 ioreg 的 plist 输出中提取 4 类利用率指标。"""
    plist_data = run_plist_command(["ioreg", "-r", "-d", "2", "-a", "-w", "0", "-c", "IOAccelerator"])
    if plist_data is None:
        return {
            "Utilization": "unavailable",
            "Renderer Utilization": "unavailable",
            "Tiler Utilization": "unavailable",
            "ANE Utilization": "unavailable",
        }

    all_nodes: list[dict[str, Any]] = []
    collect_nested_objects(plist_data, all_nodes)

    key_map = {
        "Utilization": (
            "Device Utilization %",
            "GPU Utilization %",
            "Utilization %",
        ),
        "Renderer Utilization": (
            "Renderer Utilization %",
            "Renderer Utilization",
        ),
        "Tiler Utilization": (
            "Tiler Utilization %",
            "Tiler Utilization",
        ),
        "ANE Utilization": (
            "ANE Utilization %",
            "ANE Utilization",
            "Neural Engine Utilization %",
        ),
    }

    metrics = {label: "unavailable" for label in key_map}

    for node in all_nodes:
        for label, candidate_keys in key_map.items():
            if metrics[label] != "unavailable":
                continue
            for key in candidate_keys:
                if key in node:
                    metrics[label] = normalize_metric(node[key])
                    break

    return metrics


def print_gpu_metrics() -> None:
    """打印 4 个核心利用率指标。"""
    metrics = collect_gpu_metrics()
    print_section("GPU Metrics")
    print(f"Utilization            : {metrics['Utilization']}")
    print(f"Renderer Utilization   : {metrics['Renderer Utilization']}")
    print(f"Tiler Utilization      : {metrics['Tiler Utilization']}")
    print(f"ANE Utilization        : {metrics['ANE Utilization']}")


def is_gpu_related_process(command: str) -> bool:
    """根据进程名做启发式筛选，找出更可能和 GPU/深度学习有关的进程。"""
    lowered = command.lower()
    keywords = (
        "python",
        "pytorch",
        "tensorflow",
        "jax",
        "ml",
        "metal",
        "windowserver",
        "chrome",
        "renderer",
        "gpu",
        "ollama",
        "comfyui",
        "jupyter",
    )
    return any(keyword in lowered for keyword in keywords)


def print_gpu_related_processes() -> None:
    """打印可能和 GPU 占用相关的进程，帮助定位是谁在吃资源。"""
    output = run_command(["ps", "-Ao", "pid,pcpu,%mem,comm", "-r"])
    print_section("Potential GPU Users")
    if output.startswith("<unavailable:"):
        print(output)
        return

    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        print("No process data returned.")
        return

    print(lines[0])
    matches = [line for line in lines[1:] if is_gpu_related_process(line)]
    if not matches:
        print("No obvious GPU-related processes found.")
        return

    for line in matches[:10]:
        print(line)


def print_metric_note() -> None:
    """补充说明 4 个指标的意义和限制。"""
    print_section("Notes")
    print("Utilization usually tracks total GPU load.")
    print("Renderer/Tiler are graphics pipeline indicators.")
    print("ANE reflects Neural Engine activity when the system exposes it.")
    print("Per-process GPU attribution is limited on macOS, so process rows are heuristic hints.")


def main() -> None:
    """按顺序输出 GPU 设备信息、4 个指标和相关进程摘要。"""
    print("Current GPU Usage")
    print("=" * 40)
    print_gpu_summary()
    print_gpu_metrics()
    print_gpu_related_processes()
    print_metric_note()


if __name__ == "__main__":
    main()
