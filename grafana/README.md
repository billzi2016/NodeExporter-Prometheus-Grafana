# Grafana Service

该目录用于放置 Grafana 的 provisioning、dashboard 和 datasource 配置。

当前第一版实现先以官方 `grafana/grafana` 镜像为基础，并在 `docker-compose.yml` 中挂载：

- `grafana/provisioning/`
- `grafana/dashboards/`

后续会逐步补齐：

- Prometheus 数据源 provisioning
- 宿主机总览 dashboard
- 资源分类面板
