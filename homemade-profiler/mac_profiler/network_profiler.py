#!/usr/bin/env python3
"""打印 macOS 当前网络状态。"""

from __future__ import annotations

import re
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
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        return f"<unavailable: {exc}>"
    return result.stdout.strip()


def print_section(title: str) -> None:
    """统一打印分节标题。"""
    print(f"\n=== {title} ===")


def read_default_route() -> str:
    """读取默认路由对应的网络接口。"""
    output = run_command(["route", "-n", "get", "default"])
    if output.startswith("<unavailable:"):
        return output

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("interface:"):
            return stripped.split(":", maxsplit=1)[1].strip()
    return "unknown"


def read_ip_addresses() -> list[dict[str, str]]:
    """返回活跃网卡 IPv4 信息。"""
    output = run_command(["ifconfig"])
    if output.startswith("<unavailable:"):
        return []

    current_interface = ""
    matches: list[dict[str, str]] = []

    for line in output.splitlines():
        if line and not line.startswith("\t") and ":" in line:
            current_interface = line.split(":", maxsplit=1)[0]
            continue

        stripped = line.strip()
        if stripped.startswith("status:") and "active" not in stripped:
            current_interface = ""
            continue

        if stripped.startswith("inet ") and current_interface and current_interface != "lo0":
            parts = stripped.split()
            if len(parts) >= 2:
                address = parts[1]
                netmask = parts[3] if len(parts) >= 4 and parts[2] == "netmask" else "unknown"
                matches.append(
                    {
                        "interface": current_interface,
                        "address": address,
                        "netmask": netmask,
                    }
                )

    return matches


def read_network_stats() -> list[dict[str, float | str]]:
    """返回网络接口字节统计。"""
    output = run_command(["netstat", "-ib"])
    if output.startswith("<unavailable:"):
        return []

    seen: set[str] = set()
    rows: list[dict[str, float | str]] = []

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
        rows.append(
            {
                "interface": name,
                "receive_bytes": ibytes,
                "transmit_bytes": obytes,
            }
        )

    return rows


def collect_network_snapshot() -> dict[str, object]:
    """返回结构化网络快照。"""
    return {
        "default_interface": read_default_route(),
        "ip_addresses": read_ip_addresses(),
        "interfaces": read_network_stats(),
    }


def print_ip_addresses() -> None:
    """打印当前活跃网卡及其 IPv4 地址。"""
    output = run_command(["ifconfig"])
    print_section("IP Addresses")
    if output.startswith("<unavailable:"):
        print(output)
        return

    current_interface = ""
    matches: list[tuple[str, str, str]] = []

    for line in output.splitlines():
        if line and not line.startswith("\t") and ":" in line:
            current_interface = line.split(":", maxsplit=1)[0]
            continue

        stripped = line.strip()
        if stripped.startswith("status:") and "active" not in stripped:
            current_interface = ""
            continue

        if stripped.startswith("inet ") and current_interface and current_interface != "lo0":
            parts = stripped.split()
            if len(parts) >= 2:
                address = parts[1]
                netmask = parts[3] if len(parts) >= 4 and parts[2] == "netmask" else "unknown"
                matches.append((current_interface, address, netmask))

    if not matches:
        print("No active IPv4 address found.")
        return

    for interface, address, netmask in matches:
        print(f"{interface:<12} {address:<18} netmask {netmask}")


def print_default_network() -> None:
    """打印默认出口网络信息。"""
    print_section("Default Route")
    interface = read_default_route()
    print(f"Default Interface : {interface}")


def print_network_stats() -> None:
    """打印网络流量摘要。"""
    output = run_command(["netstat", "-ib"])
    print_section("Traffic Summary")
    if output.startswith("<unavailable:"):
        print(output)
        return

    lines = [line for line in output.splitlines() if line.strip()]
    if not lines:
        print("No network statistics returned.")
        return

    print(lines[0])
    seen: set[str] = set()
    count = 0

    for line in lines[1:]:
        columns = re.split(r"\s+", line.strip())
        if not columns:
            continue
        name = columns[0]
        if name == "lo0" or name in seen:
            continue
        seen.add(name)
        print(line)
        count += 1
        if count >= 8:
            break

    if count == 0:
        print("No external interface statistics found.")


def main() -> None:
    """组织网络状态采样并输出结果。"""
    print("Current Network Status")
    print("=" * 40)
    print_default_network()
    print_ip_addresses()
    print_network_stats()


if __name__ == "__main__":
    main()
