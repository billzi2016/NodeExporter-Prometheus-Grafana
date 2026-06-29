#!/usr/bin/env python3
"""打印 Apple Silicon / macOS 的静态硬件信息。"""

from __future__ import annotations

import json
import platform
import subprocess
from typing import Any


def run_command(command: list[str]) -> str:
    """执行系统命令并返回标准输出。失败时返回占位字符串。"""
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
    """执行返回 JSON 的系统命令，并解析结果。"""
    output = run_command(command)
    if not output or output.startswith("<unavailable:"):
        return None
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return None


def bytes_to_gb(value: str) -> str:
    """把字节数转换成 GB 字符串，便于直接打印。"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "unknown"
    return f"{number / (1024 ** 3):.2f} GB"


def print_section(title: str) -> None:
    """统一打印分节标题。"""
    print(f"\n=== {title} ===")


def main() -> None:
    """收集 CPU、内存、机器型号和 GPU 的静态信息。"""
    # 先从 system_profiler 取结构化硬件信息。
    hardware_info = run_json_command(["system_profiler", "SPHardwareDataType", "-json"]) or {}
    display_info = run_json_command(["system_profiler", "SPDisplaysDataType", "-json"]) or {}

    hardware_items = hardware_info.get("SPHardwareDataType", []) if isinstance(hardware_info, dict) else []
    display_items = display_info.get("SPDisplaysDataType", []) if isinstance(display_info, dict) else []
    hardware = hardware_items[0] if hardware_items else {}

    # Apple Silicon 上 machdep.cpu.brand_string 可能为空，所以这里做回退。
    cpu_brand = run_command(["sysctl", "-n", "machdep.cpu.brand_string"])
    if cpu_brand.startswith("<unavailable:") or not cpu_brand:
        cpu_brand = str(hardware.get("chip_type") or hardware.get("machine_name") or platform.processor() or "unknown")

    physical_cores = run_command(["sysctl", "-n", "hw.physicalcpu"])
    logical_cores = run_command(["sysctl", "-n", "hw.logicalcpu"])
    total_memory = run_command(["sysctl", "-n", "hw.memsize"])

    print("Apple Silicon / macOS Hardware Information")
    print("=" * 40)

    print_section("CPU")
    print(f"CPU / Chip        : {cpu_brand}")
    print(f"Physical Cores    : {physical_cores}")
    print(f"Logical Cores     : {logical_cores}")
    print(f"Architecture      : {platform.machine()}")
    print(f"macOS Version     : {platform.mac_ver()[0] or 'unknown'}")

    print_section("Memory")
    print(f"Total Memory      : {bytes_to_gb(total_memory)} ({total_memory} bytes)")

    print_section("System")
    print(f"Model Name        : {hardware.get('machine_name', 'unknown')}")
    print(f"Model Identifier  : {hardware.get('machine_model', 'unknown')}")
    print(f"Chip              : {hardware.get('chip_type', 'unknown')}")
    print(f"Serial Number     : {hardware.get('serial_number', 'unknown')}")

    print_section("GPU / Display")
    if not display_items:
        print("No GPU/display data returned by system_profiler.")
        return

    for index, gpu in enumerate(display_items, start=1):
        # 优先输出稳定字段。拿不到的字段不打印，避免噪声。
        name = gpu.get("_name") or gpu.get("sppci_model") or gpu.get("spdisplays_vendor") or "unknown"
        vendor = gpu.get("spdisplays_vendor", "unknown")
        print(f"GPU {index} Name      : {name}")
        print(f"GPU {index} Vendor    : {vendor}")
        print("-" * 40)


if __name__ == "__main__":
    main()
