# Node Exporter Service

该目录用于放置 `node exporter` 相关配置、说明和后续可能的 fallback 实现资料。

当前第一版实现仍然优先采用官方 `prom/node-exporter` 镜像，由根目录 `docker-compose.yml` 编排。

需要注意：

- 在 Linux 宿主机场景下，官方方案通常更容易获得宿主机视角
- 在 macOS + Docker Desktop 环境下，当前已观察到指标更接近 LinuxKit / 容器环境
- 如果后续确认官方方案不能满足宿主机监控要求，这个目录将承载自定义 exporter 的实现
