#!/usr/bin/env python3
"""打印 macOS 当前 CPU 使用情况。"""

from __future__ import annotations

import subprocess


def run_command(command: list[str]) -> str:
    """执行系统命令并返回输出。失败时返回占位字符串。"""
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


def parse_cpu_summary(line: str) -> dict[str, float] | None:
    """解析 top 的 CPU 汇总行。"""
    if "CPU usage:" not in line:
        return None

    try:
        _, values = line.split(":", maxsplit=1)
    except ValueError:
        return None

    result: dict[str, float] = {}
    for part in values.split(","):
        tokens = part.strip().split()
        if len(tokens) < 2:
            continue

        value_text = tokens[0].rstrip("%")
        label = tokens[1].lower()
        if label == "sys":
            label = "system"

        try:
            result[label] = float(value_text)
        except ValueError:
            continue

    if not result:
        return None
    return result


def read_cpu_percentages() -> dict[str, float] | None:
    """从 top 输出中提取当前 CPU 占用比例。"""
    output = run_command(["top", "-l", "2", "-n", "0"])
    if output.startswith("<unavailable:"):
        return None

    last_result: dict[str, float] | None = None
    for line in output.splitlines():
        parsed = parse_cpu_summary(line.strip())
        if parsed:
            last_result = parsed
    return last_result


def collect_cpu_metrics() -> dict[str, float] | None:
    """返回结构化 CPU 指标，供外部服务直接调用。"""
    percentages = read_cpu_percentages()
    if not percentages:
        return None

    idle = percentages.get("idle", 0.0)
    return {
        "used_percent": 100.0 - idle,
        "user_percent": percentages.get("user", 0.0),
        "system_percent": percentages.get("system", 0.0),
        "idle_percent": idle,
        "nice_percent": percentages.get("nice", 0.0),
    }


def print_top_processes() -> None:
    """打印当前 CPU 占用最高的几个进程。"""
    output = run_command(["ps", "-Arcwwwxo", "pid,pcpu,comm", "-r"])
    if output.startswith("<unavailable:"):
        print(f"Top Processes      : {output}")
        return

    lines = [line for line in output.splitlines() if line.strip()]
    print("\n=== Top CPU Processes ===")
    for line in lines[:6]:
        print(line)


def print_per_core_snapshot() -> None:
    """打印 top 提供的 CPU 快照，便于看总体和分核信息。"""
    output = run_command(["top", "-l", "1", "-stats", "cpu"])
    if output.startswith("<unavailable:"):
        print(f"\nPer-core Snapshot  : {output}")
        return

    lines = [line.strip() for line in output.splitlines() if line.strip().startswith("CPU")]
    if not lines:
        print("\nPer-core Snapshot  : unavailable from top output")
        return

    print("\n=== CPU Snapshot ===")
    for line in lines[:12]:
        print(line)


def main() -> None:
    """组织 CPU 采样并输出结果。"""
    percentages = read_cpu_percentages()
    print("Current CPU Usage")
    print("=" * 40)

    if not percentages:
        print("Unable to sample CPU usage from top.")
    else:
        # 总使用率直接按 100 - idle 计算，便于理解。
        user = percentages.get("user", 0.0)
        system = percentages.get("system", 0.0)
        idle = percentages.get("idle", 0.0)
        nice = percentages.get("nice", 0.0)
        used = 100.0 - idle
        print(f"Total CPU Used     : {used:.2f}%")
        print(f"User               : {user:.2f}%")
        print(f"System             : {system:.2f}%")
        print(f"Idle               : {idle:.2f}%")
        print(f"Nice               : {nice:.2f}%")

    print_per_core_snapshot()
    print_top_processes()


if __name__ == "__main__":
    main()
