# Prometheus PRD

## 1. 文档目的

本文档用于定义本项目中 `Prometheus` 模块的需求范围、配置目标和验收标准。

本项目的定位是做一套面向本机宿主机监控的 Docker 化系统，而不是只观察容器本身运行状态。`Prometheus` 在其中负责抓取、存储和组织监控指标，是连接 `node exporter` 与 `Grafana` 的中间层。

## 2. 背景与问题

当前存在 `API_test` 目录用于本地脚本验证，但这些脚本没有形成标准的时间序列采集体系，也不能自然支持历史趋势展示。

如果没有 Prometheus：

- 采样结果无法持续抓取
- 无法形成标准时序数据
- Grafana 无法稳定建立监控面板
- 后续告警和规则体系没有统一基础

因此，Prometheus 不是一个可选配件，而是整个系统的数据中枢。

## 3. 产品目标

- 提供一个 Docker 化运行的 Prometheus 服务
- 稳定抓取 `node exporter` 暴露的宿主机指标
- 为 `Grafana` 提供查询数据源
- 为后续引入更多 exporter 或业务指标保留配置扩展能力

## 4. 非目标

- 本阶段不处理跨主机联邦
- 本阶段不处理高可用部署
- 本阶段不处理复杂远程存储
- 本阶段不优先实现 Alertmanager 联动

## 5. 用户故事

### 5.1 作为开发者

我希望 Prometheus 能在 Docker 环境里稳定运行，并通过简单配置抓取 `node exporter`，以便快速形成基础监控链路。

### 5.2 作为使用者

我希望 Grafana 中看到的数据有持续时间轴，而不是某个瞬时打印结果。

### 5.3 作为后续维护者

我希望后续新增 exporter 或监控目标时，不需要推翻当前目录结构和配置方式。

## 6. 功能需求

### 6.1 部署形态

- Prometheus 必须以 Docker 容器形式运行
- 必须可以通过统一编排配置启动
- 配置文件需要外置，方便版本管理和后续修改

### 6.2 抓取目标

第一阶段至少包含以下抓取目标：

- 优先为官方 `node exporter`
- 如果官方 `node exporter` 在目标环境下不能提供宿主机视角指标，则改为抓取自定义 exporter

后续预留但不要求本阶段完成：

- 自定义 exporter
- 业务 API 指标
- 容器级补充指标

### 6.3 抓取行为

- 必须支持固定抓取间隔配置
- 必须支持目标地址配置
- 必须具备基础 job 组织能力
- 配置文件格式应保持清晰，方便后续扩展多个 scrape job

### 6.4 数据能力

- 存储抓取到的时间序列数据
- 为 Grafana 提供标准 PromQL 查询能力
- 能够支持基础资源监控面板的查询性能

### 6.5 可运维性

- 必须暴露 Web UI 供本地查看 targets 和 query
- 必须可以快速判断某个抓取目标是否健康
- 当抓取失败时，必须能通过 UI 或日志定位原因

## 7. 约束与设计原则

### 7.1 先单机、后扩展

本项目当前目标是单机监控系统，不提前为分布式场景做过度设计。

### 7.2 配置透明

Prometheus 配置不能藏在镜像内部，必须作为仓库中的明确配置文件存在，方便审查和修改。

### 7.3 围绕宿主机监控组织

Prometheus 的首要职责是采集宿主机监控指标链路，而不是泛化为一个无边界监控平台。

### 7.4 接受上游 exporter 的实现替换

Prometheus 本身不应强绑定“必须是官方 node exporter”。  
只要上游 exporter 最终能稳定提供 Prometheus 兼容、并且语义上代表宿主机状态的指标，Prometheus 应能接入。

### 7.4 为后续增长留口子

虽然首期只接 `node exporter`，但配置结构要足够清晰，后续加 job 时不需要推倒重来。

## 8. 配置需求

后续实现阶段至少需要考虑：

- 项目根目录必须统一放置 `docker-compose.yml`、`.dockerignore` 等编排级文件
- `Prometheus` 必须有独立服务目录，例如 `prometheus/`
- Prometheus 主配置文件
- `scrape_configs` 的独立维护方式
- 数据目录持久化
- Web 访问端口暴露
- 在真正绑定宿主机端口前，必须先检查目标端口是否已被占用
- 如果默认端口已被占用，则按顺序顺延到下一个可用端口
- 和 `node exporter`、`Grafana` 所在网络的连通性

## 9. 项目结构要求

本项目后续实现阶段至少应遵循以下目录边界：

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

目录职责说明：

- `node-exporter/`：放置 node exporter 相关配置、说明和后续可能的自定义内容
- `prometheus/`：放置 Prometheus 配置、规则、数据卷组织说明等内容
- `grafana/`：放置 Grafana provisioning、dashboard、datasource 等文件
- `API_test/`：保留为验证和原型目录，不直接等同于正式监控实现
- `docs/prds/`：存放需求文档与 SDD 过程文档

## 10. 风险与关注点

- 如果 `node exporter` 暴露的不是稳定宿主机指标，那么 Prometheus 抓取得再稳定也没有意义
- 如果最终 node 层切换到自定义 exporter，Prometheus 配置和 job 命名需要同步反映这种变化
- 本机磁盘资源和保留策略需要在实现阶段给出合理默认值
- 容器网络命名、端口映射和服务发现方式要简单可维护，避免过早复杂化

## 11. 验收标准

满足以下条件视为 Prometheus 第一阶段完成：

- 可以通过 Docker 成功启动
- 服务目录结构符合项目约定
- 可以通过配置文件抓取 `node exporter`
- Web UI 中能看到抓取目标状态
- 可以直接查询宿主机 CPU、内存、磁盘、网络相关指标
- Grafana 可以把它作为数据源接入
- 最终实际绑定端口经过占用检查，且能稳定访问

## 12. 后续扩展

- 引入规则文件与告警能力
- 增加更多 scrape job
- 增加数据保留策略调优
- 评估是否需要远程写入或长期存储方案
