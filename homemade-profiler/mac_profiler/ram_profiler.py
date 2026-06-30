#!/usr/bin/env python3
"""Print current RAM usage on macOS."""

from __future__ import annotations

import subprocess


def run_command(command: list[str]) -> str:
    """执行系统命令并返回输出，失败时返回占位字符串。"""
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


def bytes_to_gb(value: int) -> str:
    """把字节数转换成 GB 字符串，便于直接打印。"""
    return f"{value / (1024 ** 3):.2f} GB"


def read_total_memory() -> int | None:
    """读取机器总内存字节数。"""
    output = run_command(["sysctl", "-n", "hw.memsize"])
    if output.startswith("<unavailable:"):
        return None

    try:
        return int(output)
    except ValueError:
        return None


def read_vm_stats() -> tuple[int | None, dict[str, int]]:
    """读取 vm_stat 输出，并解析页大小和各类页计数。"""
    output = run_command(["vm_stat"])
    if output.startswith("<unavailable:"):
        return None, {}

    page_size: int | None = None
    stats: dict[str, int] = {}

    for line in output.splitlines():
        if "page size of" in line:
            for token in line.split():
                if token.isdigit():
                    page_size = int(token)
                    break
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", maxsplit=1)
        cleaned_value = value.strip().rstrip(".").replace(".", "")
        try:
            stats[key.strip()] = int(cleaned_value)
        except ValueError:
            continue

    return page_size, stats


def collect_memory_metrics() -> dict[str, float] | None:
    """返回结构化内存指标，供外部服务直接调用。"""
    total_memory = read_total_memory()
    page_size, stats = read_vm_stats()
    if total_memory is None or page_size is None or not stats:
        return None

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
    active_bytes = active_pages * page_size
    inactive_bytes = inactive_pages * page_size
    wired_bytes = wired_pages * page_size
    compressed_bytes = compressed_pages * page_size

    return {
        "total_bytes": float(total_memory),
        "used_bytes": float(used_bytes),
        "free_bytes": float(free_bytes),
        "active_bytes": float(active_bytes),
        "inactive_bytes": float(inactive_bytes),
        "wired_bytes": float(wired_bytes),
        "compressed_bytes": float(compressed_bytes),
        "used_percent": (used_bytes / total_memory) * 100 if total_memory else 0.0,
    }


def print_memory_summary() -> None:
    """打印总内存、已用、空闲和主要内存分类。"""
    total_memory = read_total_memory()
    page_size, stats = read_vm_stats()

    print("Current RAM Usage")
    print("=" * 40)

    if total_memory is None or page_size is None or not stats:
        print("Unable to sample RAM usage from vm_stat/sysctl.")
        return

    free_pages = stats.get("Pages free", 0)
    speculative_pages = stats.get("Pages speculative", 0)
    active_pages = stats.get("Pages active", 0)
    inactive_pages = stats.get("Pages inactive", 0)
    wired_pages = stats.get("Pages wired down", 0)
    compressed_pages = stats.get("Pages occupied by compressor", 0)

    # 这里沿用 macOS 常见分类，先给出一个直观总览。
    used_pages = active_pages + inactive_pages + wired_pages + compressed_pages
    free_like_pages = free_pages + speculative_pages

    used_bytes = used_pages * page_size
    free_bytes = free_like_pages * page_size
    active_bytes = active_pages * page_size
    inactive_bytes = inactive_pages * page_size
    wired_bytes = wired_pages * page_size
    compressed_bytes = compressed_pages * page_size
    usage_percent = (used_bytes / total_memory) * 100 if total_memory else 0.0

    print(f"Total RAM          : {bytes_to_gb(total_memory)}")
    print(f"Used RAM           : {bytes_to_gb(used_bytes)} ({usage_percent:.2f}%)")
    print(f"Free RAM           : {bytes_to_gb(free_bytes)}")
    print(f"Active RAM         : {bytes_to_gb(active_bytes)}")
    print(f"Inactive RAM       : {bytes_to_gb(inactive_bytes)}")
    print(f"Wired RAM          : {bytes_to_gb(wired_bytes)}")
    print(f"Compressed RAM     : {bytes_to_gb(compressed_bytes)}")


def print_top_memory_processes() -> None:
    """打印当前内存占用最高的几个进程。"""
    output = run_command(["ps", "-Arcwwwxo", "pid,rss,%mem,comm", "-m"])
    if output.startswith("<unavailable:"):
        print(f"\nTop Memory Processes: {output}")
        return

    lines = [line for line in output.splitlines() if line.strip()]
    print("\n=== Top Memory Processes ===")
    for line in lines[:6]:
        print(line)


def main() -> None:
    """组织内存采样并输出结果。"""
    print_memory_summary()
    print_top_memory_processes()


if __name__ == "__main__":
    main()
