# Homemade Profiler

该目录用于放置自定义宿主机采样服务，也就是 `homemade-profiler`。

当前目录同时承担两种角色：

- `FastAPI` 服务入口目录
- `mac_profiler` 可调用采样模块目录

当前设计中，两套采集并存：

- `9100`: 官方 `node exporter`，由 Docker Compose 启动
- `9101`: `homemade-profiler`，由宿主机本地启动

需要注意：

- 在 Linux 宿主机场景下，官方方案通常更容易获得宿主机视角
- 在 macOS + Docker Desktop 环境下，当前已观察到指标更接近 LinuxKit / 容器环境
- 因此这里额外实现了 `homemade-profiler`，用于展示宿主机本地采样能力
- `FastAPI` 入口不会自己重复写一套采样逻辑，而是直接调用 `mac_profiler` 模块
- 在当前项目环境里，真正有价值的宿主机指标来自 `9101`，不是 Docker 里的 `9100`

本地启动示例：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 9101
```
