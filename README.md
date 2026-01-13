# 外链点击篡改监控 / 安全留痕系统

External Link Click Monitoring & Security Audit System

## 系统概述

这是一个安全留痕系统，用于：
- 模拟真实用户在网页中点击某个按钮
- 记录点击完成后用户"实际看到的页面内容"
- 通过 DOM hash 判断是否发生篡改或跳转劫持

### 核心设计原则

1. **历史留痕**：每次执行必须留痕（INSERT-only），历史记录不可覆盖
2. **DOM 哈希**：篡改判断基于 `page_hash`（点击后页面的 DOM hash）
3. **截图取证**：截图仅用于人工取证展示
4. **单表设计**：数据库只允许一张表

## 系统架构

```
┌─────────────────┐
│  FastAPI        │  ← 对外提供 API
│  Backend        │  ← 保存截图、写入数据库
│  (Python)       │  ← 不安装浏览器
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│  Playwright     │  ← 浏览器自动化
│  Service        │  ← 模拟点击、截图
│  (Node.js)      │  ← 不访问数据库
└─────────────────┘

         ↓ 数据存储
┌─────────────────┐
│  OpenGauss      │  ← 结构化留痕数据
│  Database       │  ← 不存 base64
└─────────────────┘
```

## 快速开始

### 前置要求

- Docker
- Docker Compose

### 1. 克隆或下载项目

```bash
cd external-link-monitor
```

### 2. 配置数据库密码（可选）

编辑 `docker-compose.yml`，修改 `GS_PASSWORD` 和 `DATABASE_PASSWORD`：

```yaml
environment:
  - GS_PASSWORD=your_secure_password
  - DATABASE_PASSWORD=your_secure_password
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 检查服务状态

```bash
docker-compose ps
```

所有服务应显示为 `healthy` 状态。

### 5. 访问 API 文档

打开浏览器访问：http://localhost:8080/docs

## API 使用指南

### 1. 创建快照

**接口**：`POST /api/external-link-snapshot`

**请求示例**：

```bash
curl -X POST "http://localhost:8080/api/external-link-snapshot" \
  -H "Content-Type: application/json" \
  -d '{
    "origin_url": "https://example.com",
    "click_type": "text",
    "click_value": "立即下载",
    "wait_after_click_ms": 3000,
    "full_page": true
  }'
```

**响应示例**：

```json
{
  "snapshot_id": 123,
  "status": "ok"
}
```

**参数说明**：

- `origin_url`：原始页面 URL
- `click_type`：点击类型
  - `text`：按钮可见文本
  - `css`：CSS selector
  - `xpath`：XPath
  - `aria`：ARIA role
- `click_value`：点击值（按钮文本或选择器）
- `wait_after_click_ms`：点击后等待时间（毫秒），默认 3000
- `full_page`：是否全页面截图，默认 true

### 2. 获取快照详情

**接口**：`GET /api/external-link-snapshot/{snapshot_id}`

**请求示例**：

```bash
curl "http://localhost:8080/api/external-link-snapshot/123"
```

**响应示例**：

```json
{
  "id": 123,
  "origin_url": "https://example.com",
  "click_type": "text",
  "click_value": "立即下载",
  "page_url": "https://download.example.com/file.exe",
  "page_hash": "a1b2c3d4e5f6...",
  "screenshot_path": "20240115_123456_abc123.png",
  "created_at": "2024-01-15T12:34:56"
}
```

### 3. 获取快照截图

**接口**：`GET /api/external-link-snapshot/{snapshot_id}/image`

**使用方式**：

在 HTML 中直接使用：

```html
<img src="http://localhost:8080/api/external-link-snapshot/123/image" />
```

或浏览器访问：

```
http://localhost:8080/api/external-link-snapshot/123/image
```

## 数据库表结构

```sql
CREATE TABLE external_link_snapshot (
    id              BIGSERIAL PRIMARY KEY,
    origin_url      TEXT NOT NULL,      -- 原始页面 URL
    click_type      TEXT NOT NULL,      -- text/css/xpath/aria
    click_value     TEXT NOT NULL,      -- 按钮文本或 selector
    page_url        TEXT,               -- 点击后的最终 URL
    page_hash       TEXT,               -- 点击后的页面 DOM hash
    screenshot_path TEXT NOT NULL,      -- 截图文件路径
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### 字段说明

- `id`：自增主键
- `origin_url`：用户输入的原始页面 URL
- `click_type`：点击类型（text/css/xpath/aria）
- `click_value`：点击值
- `page_url`：点击完成后的最终 URL（可能发生跳转）
- `page_hash`：点击完成后页面 DOM 的 SHA256 哈希（核心字段）
- `screenshot_path`：截图文件相对路径
- `created_at`：记录创建时间

## 项目结构

```
external-link-monitor/
├── playwright-service/          # Playwright 服务
│   ├── server.js               # Node.js 服务主文件
│   ├── package.json            # 依赖配置
│   ├── Dockerfile              # Docker 镜像配置
│   └── .dockerignore
│
├── fastapi-backend/            # FastAPI 后端
│   ├── main.py                 # 主应用入口
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库操作
│   ├── services.py             # 业务逻辑
│   ├── models.py               # 数据模型
│   ├── requirements.txt        # Python 依赖
│   ├── Dockerfile              # Docker 镜像配置
│   ├── .dockerignore
│   └── .env.example            # 环境变量示例
│
├── docker-compose.yml          # Docker Compose 配置
└── README.md                   # 项目文档
```

## 日志查看

### 查看所有服务日志

```bash
docker-compose logs -f
```

### 查看特定服务日志

```bash
# FastAPI Backend
docker-compose logs -f fastapi-backend

# Playwright Service
docker-compose logs -f playwright-service

# OpenGauss
docker-compose logs -f opengauss
```

## 故障排查

### 1. 数据库连接失败

检查 OpenGauss 是否正常运行：

```bash
docker-compose ps opengauss
```

检查密码是否一致：

```bash
# 在 docker-compose.yml 中
GS_PASSWORD = DATABASE_PASSWORD
```

### 2. Playwright Service 无响应

检查服务状态：

```bash
curl http://localhost:8000/health
```

查看日志：

```bash
docker-compose logs playwright-service
```

### 3. 截图文件不存在

检查 volume 挂载：

```bash
docker volume ls | grep screenshot
```

进入容器检查：

```bash
docker exec -it external-link-backend ls -la /app/screenshots
```

## 生产环境部署建议

### 1. 安全配置

- 修改默认数据库密码
- 使用环境变量管理敏感信息
- 配置防火墙规则

### 2. 性能优化

- 调整 Playwright Service 资源限制
- 配置 Nginx 反向代理
- 启用日志轮转

### 3. 监控告警

- 配置健康检查
- 集成监控系统（Prometheus, Grafana）
- 设置磁盘空间告警（截图文件）

## 技术栈

- **Playwright Service**: Node.js + Playwright + Express
- **FastAPI Backend**: Python 3.11 + FastAPI + psycopg
- **Database**: OpenGauss (PostgreSQL 兼容)
- **Containerization**: Docker + Docker Compose

## 许可证

本项目仅供内部使用。

## 联系方式

如有问题，请联系开发团队。
