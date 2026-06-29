#!/usr/bin/env python3
"""统一调用各类状态采样脚本。"""

from __future__ import annotations

import cpu_gpu_info
import cpu_profiler
import disk_profiler
import gpu_profiler
import network_profiler
import ram_profiler


def print_divider() -> None:
    """打印模块间分隔线。"""
    print("\n" + "#" * 60 + "\n")


def main() -> None:
    """依次打印硬件、CPU、内存、GPU、网络、硬盘状态。"""
    cpu_gpu_info.main()
    print_divider()
    cpu_profiler.main()
    print_divider()
    ram_profiler.main()
    print_divider()
    gpu_profiler.main()
    print_divider()
    network_profiler.main()
    print_divider()
    disk_profiler.main()


if __name__ == "__main__":
    main()
