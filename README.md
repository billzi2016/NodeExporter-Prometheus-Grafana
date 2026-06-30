# NodeExporter-Prometheus-Grafana

这是一个按 SDD 方式推进的本机监控系统项目。

当前实现目标是搭出一套同时包含“官方方案展示”和“自定义宿主机采集”的监控链路：

- `node exporter`
- `homemade-profiler`
- `Prometheus`
- `Grafana`

这样可以同时展示两种能力：

- 标准 Prometheus 官方生态接法
- 基于本机采样逻辑的自定义 exporter 扩展能力

## 当前实现状态

当前仓库已经包含：

- `API_test/`
  - 本机 CPU、内存、GPU、网络、硬盘采样验证脚本
- `demo/`
  - 项目效果截图目录，用于展示 4 类 dashboard 和整体监控链路
- `homemade-profiler/`
  - 自定义 `FastAPI` 服务与 `mac_profiler` 采样模块
- `docs/prds/`
  - `node exporter`、`Prometheus`、`Grafana` 三份 PRD
- `docker-compose.yml`
  - `node exporter + Prometheus + Grafana` 官方 Docker 编排骨架

## 当前技术路线

当前路线是两套采集并存：

1. 保留官方 `node exporter`，展示标准官方接入方式
2. 同时增加自定义 `homemade-profiler`，展示宿主机本地采样与扩展能力
3. 同时保留宿主机版官方 `node_exporter`
4. 让 `Prometheus` 同时抓取三套 exporter

## 关于 node exporter 的当前结论

当前已经验证过：在 macOS + Docker Desktop 环境里，官方 `node exporter` 容器本身是可以正常启动、正常暴露 `/metrics`、也可以被 `Prometheus` 正常抓取的；问题不在 exporter 本身，而在采集视角。它看到的更接近 LinuxKit / 容器环境，而不是 macOS 宿主机原生视角。

这意味着：

- 官方方案是第一优先的展示路线
- 但“能运行”不等于“满足需求”
- 在当前 macOS + Docker Desktop 环境里，Docker 中的官方 `node exporter` 可以 work，只是它 work 出来的主要是容器 / LinuxKit 视角，不是这台 Mac 的原生宿主机视角
- 它主要只能看到容器 / LinuxKit 内部视角，而不是这台 Mac 本机
- 因此当前项目并行保留三套采集：
  - `9100`: 官方 `node exporter`
  - `9101`: `homemade-profiler`
  - `9102`: 宿主机版官方 `node_exporter`

其中：

- `9100` 主要用于展示 Docker 内官方 `node exporter` 的视角
- `9101` 主要用于提供自定义宿主机本地采样数据
- `9102` 主要用于提供宿主机版官方 `node_exporter` 数据
- `Prometheus` 会同时抓取这三套 exporter

可以直接把这两套理解成：

- `9100`: 一台 Docker 内部机器
- `9101`: 一台自定义采集机器
- `9102`: 一台宿主机官方机器

## 项目结构

```text
NodeExporter-Prometheus-Grafana/
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── homemade-profiler/
│   ├── README.md
│   ├── app.py
│   ├── requirements.txt
│   └── mac_profiler/
├── prometheus/
├── grafana/
├── API_test/
├── demo/
└── docs/
    └── prds/
```

## Demo 截图

- `demo/1.png`
  - `Compare Node In/Out Docker` 总览页截图，用于展示 Docker 内外官方 `node_exporter` 的差异对比。
- `demo/2.png`
  - `Node In Docker View` 截图，用于展示 Docker 内官方 `node_exporter` 看到的容器侧指标。
- `demo/3.png`
  - `Node On Host View` 截图，用于展示宿主机官方 `node_exporter` 看到的主机侧指标。
- `demo/4.png`
  - `FastAPI Homemade Exporter View` 截图，用于展示自定义 exporter 暴露的宿主机指标。
- `demo/5.png`
  - CPU 相关面板截图，用于展示使用率、拆分趋势和负载变化。
- `demo/6.png`
  - 内存相关面板截图，用于展示总量、已用、可用和使用率变化。
- `demo/7.png`
  - 磁盘相关面板截图，用于展示容量、已用空间和磁盘趋势。
- `demo/8.png`
  - 网络相关面板截图，用于展示吞吐趋势和接口级别统计。
- `demo/9.png`
  - exporter 状态截图，用于展示 `Prometheus` 对多个采集端的抓取结果。
- `demo/10.png`
  - Grafana dashboard 列表截图，用于展示项目当前提供的多个视图入口。

## 默认端口

- `node exporter`: `9100`
- `homemade-profiler`: `9101`
- `Host node_exporter`: `9102`
- `Prometheus`: `9090`
- `Grafana`: `3000`

当前 `docker-compose.yml` 使用环境变量形式保留了端口覆盖能力：

- `NODE_EXPORTER_PORT`
- `FASTAPI_EXPORTER_PORT`
- `PROMETHEUS_PORT`
- `GRAFANA_PORT`

后续启动前仍应先检查端口占用。如果默认端口已被占用，应顺延到下一个可用端口。

## 访问与认证

### Grafana

- 地址：`http://127.0.0.1:3000`
- 当前认证方式：Grafana 默认登录
- 当前用户名：`admin`
- 当前密码：`admin`

如果后续你改了 Grafana 管理员密码，需要同步更新这里的说明。

### Prometheus

- 地址：`http://127.0.0.1:9090`
- 当前是否有密码：没有
- 当前是否有登录页：没有
- 当前访问方式：本地直接访问

### 官方 Node Exporter

- 地址：`http://127.0.0.1:9100/metrics`
- 当前是否有密码：没有
- 当前是否有认证：没有

### 宿主机版官方 Node Exporter

- 地址：`http://127.0.0.1:9102/metrics`
- 当前是否有密码：没有
- 当前是否有认证：没有

### homemade-profiler

- 地址：`http://127.0.0.1:9101/metrics`
- 健康检查：`http://127.0.0.1:9101/healthz`
- 当前是否有密码：没有
- 当前是否有认证：没有

## 哪个真的有用

在当前项目环境里：

- `docker compose` 管的官方 `node exporter` 不是主数据源
- 它只能代表容器 / LinuxKit 视角
- 对“监控这台 Mac 本机状态”这个目标来说，它基本没用

真正有用的是：

- 宿主机本地运行的自定义 `FastAPI exporter`
- 它直接复用本机采样逻辑
- 输出更接近真实宿主机 CPU、内存、GPU、网络、硬盘状态

## Homemade Profiler

`homemade-profiler` 运行在宿主机本地，而不是 Docker 容器内。这样 Prometheus 可以通过 `host.docker.internal:9101` 抓到它，同时它采集到的也是更接近宿主机本身的数据。

它的采样逻辑直接来自：

- `homemade-profiler/mac_profiler/cpu_profiler.py`
- `homemade-profiler/mac_profiler/ram_profiler.py`
- `homemade-profiler/mac_profiler/gpu_profiler.py`
- `homemade-profiler/mac_profiler/network_profiler.py`
- `homemade-profiler/mac_profiler/disk_profiler.py`

建议启动方式：

```bash
cd homemade-profiler
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 9101
```
