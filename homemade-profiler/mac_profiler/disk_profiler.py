#!/usr/bin/env python3
"""打印 macOS 当前硬盘状态。"""

from __future__ import annotations

import subprocess
import re


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


def print_section(title: str) -> None:
    """统一打印分节标题。"""
    print(f"\n=== {title} ===")


def print_disk_usage() -> None:
    """打印主要挂载点的磁盘使用情况。"""
    output = run_command(["df", "-h"])
    print_section("Disk Usage")
    if output.startswith("<unavailable:"):
        print(output)
        return

    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        print("No disk usage data returned.")
        return

    print(lines[0])
    for line in lines[1:9]:
        print(line)


def print_root_disk_summary() -> None:
    """突出显示根分区容量信息。"""
    output = run_command(["df", "-h", "/"])
    print_section("Root Volume")
    if output.startswith("<unavailable:"):
        print(output)
        return

    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) < 2:
        print("Unable to read root volume usage.")
        return

    print(lines[0])
    print(lines[1])


def print_disk_list() -> None:
    """打印磁盘设备摘要。"""
    output = run_command(["diskutil", "list"])
    print_section("Disk Devices")
    if output.startswith("<unavailable:"):
        print(output)
        return

    lines = [line for line in output.splitlines() if line.strip()]
    for line in lines[:16]:
        print(line)


def read_root_disk_summary() -> dict[str, float | str] | None:
    """返回根卷容量摘要。"""
    output = run_command(["df", "-k", "/"])
    if output.startswith("<unavailable:"):
        return None

    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) < 2:
        return None

    parts = re.split(r"\s+", lines[1].strip())
    if len(parts) < 5:
        return None

    try:
        total_kb = float(parts[1])
        used_kb = float(parts[2])
        avail_kb = float(parts[3])
        capacity = float(parts[4].rstrip("%"))
    except ValueError:
        return None

    return {
        "filesystem": parts[0],
        "total_bytes": total_kb * 1024,
        "used_bytes": used_kb * 1024,
        "available_bytes": avail_kb * 1024,
        "used_percent": capacity,
        "mountpoint": parts[-1],
    }


def collect_disk_snapshot() -> dict[str, object]:
    """返回结构化磁盘快照。"""
    return {
        "root": read_root_disk_summary(),
    }


def main() -> None:
    """组织硬盘状态采样并输出结果。"""
    print("Current Disk Status")
    print("=" * 40)
    print_root_disk_summary()
    print_disk_usage()
    print_disk_list()


if __name__ == "__main__":
    main()
