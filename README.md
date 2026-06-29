# NodeExporter-Prometheus-Grafana

这是一个按 SDD 方式推进的本机监控系统项目。

当前实现目标是先搭出第一版纯官方监控链路：

- `node exporter`
- `Prometheus`
- `Grafana`

然后基于实际验证结果，决定 `node` 这一层是否需要从官方方案切换到自定义 exporter。

## 当前实现状态

当前仓库已经包含：

- `API_test/`
  - 本机 CPU、内存、GPU、网络、硬盘采样验证脚本
- `docs/prds/`
  - `node exporter`、`Prometheus`、`Grafana` 三份 PRD
- `docker-compose.yml`
  - 第一版官方 Docker 编排骨架

## 当前技术路线

当前路线遵循以下优先级：

1. 尽可能先使用官方组件
2. 优先尝试纯官方 `node exporter`
3. 如果纯官方 `node exporter` 无法在当前环境中提供宿主机视角指标，则切换到自定义 exporter

## 关于 node exporter 的当前结论

当前已经验证过：在 macOS + Docker Desktop 环境里，官方 `node exporter` 容器虽然可以启动并暴露 `/metrics`，但采集视角更接近 LinuxKit / 容器环境，而不是 macOS 宿主机原生视角。

这意味着：

- 官方方案是第一优先
- 但“能运行”不等于“满足需求”
- 如果后续验证仍然不能提供宿主机级指标，项目将改为：
  - 复用 `API_test` 中的采样逻辑
  - 通过 `FastAPI` 或等价方式暴露 exporter 接口
  - 再由 `Prometheus` 抓取

如果最终采用了自定义 exporter，而不是纯官方 `node exporter`，会在本 README 中明确写清楚原因、差异和替代实现方式。

## 项目结构

```text
NodeExporter-Prometheus-Grafana/
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── node-exporter/
├── prometheus/
├── grafana/
├── API_test/
└── docs/
    └── prds/
```

## 默认端口

- `node exporter`: `9100`
- `Prometheus`: `9090`
- `Grafana`: `3000`

当前 `docker-compose.yml` 使用环境变量形式保留了端口覆盖能力：

- `NODE_EXPORTER_PORT`
- `PROMETHEUS_PORT`
- `GRAFANA_PORT`

后续启动前仍应先检查端口占用。如果默认端口已被占用，应顺延到下一个可用端口。
