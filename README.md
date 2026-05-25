# EasyFund

个人资产管理工具，支持多账户、多币种资产跟踪与净值分析。

## 功能特性

- **多账户管理** — 支持银行、券商、保险等多种账户类型，可设置子账户
- **投资持仓跟踪** — 记录股票持仓、成本价、当前价格，支持 RSU 归属计划
- **存款管理** — 定期存款记录与利息计算
- **多币种支持** — 自动获取汇率（基于 Yahoo Finance），跨币种资金流转记录
- **净值仪表盘** — 按类别汇总总资产，可视化净值变化趋势
- **Excel 导入** — 支持从 Excel 导入数据，AI 辅助列映射
- **AI 对话** — 内置 AI 助手，可查询资产和持仓信息

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python FastAPI + Uvicorn |
| ORM | Tortoise ORM + aiosqlite |
| 数据库 | SQLite (WAL 模式) |
| 前端框架 | Vue 3 (Composition API) |
| 状态管理 | Pinia |
| 图表 | ECharts (vue-echarts) |
| 构建工具 | Vite |
| 认证 | bcrypt + JWT |

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 24+
- pnpm

### 本地开发

```bash
# 安装后端依赖
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 安装前端依赖
cd frontend && pnpm install && cd ..

# 启动开发模式（后端 + 前端热更新）
./manage.sh start --dev

# 使用示例数据启动
./manage.sh start --dev --mock
```

### 生产模式

```bash
# 构建前端静态资源
./manage.sh build

# 启动生产服务
./manage.sh start
```

### Docker 部署

```bash
docker build -t easyfund .
docker run -p 8000:8000 easyfund
```

## manage.sh 常用命令

| 命令 | 说明 |
|------|------|
| `./manage.sh start` | 启动生产服务 |
| `./manage.sh start --dev` | 启动开发模式 |
| `./manage.sh start --dev --mock` | 使用示例数据启动 |
| `./manage.sh build` | 构建前端 |
| `./manage.sh status` | 查看服务状态 |
| `./manage.sh import <file>` | 从 Excel 导入数据 |
| `./manage.sh add-user <name>` | 创建新用户 |
| `./manage.sh stop` | 停止服务 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `EASYFUND_MOCK` | 使用示例数据 | `false` |
| `EASYFUND_DEV` | 开发模式 | `false` |
| `EASYFUND_BACKEND_PORT` | 后端端口 | `8000` |
| `EASYFUND_FRONTEND_PORT` | 前端开发服务器端口 | `3000` |

## 项目结构

```
easyfund/
├── backend/          # FastAPI 后端
│   ├── app.py        # 应用入口
│   ├── models/       # 数据模型
│   ├── routes/       # API 路由
│   └── services/     # 业务逻辑
├── frontend/         # Vue 3 前端
│   ├── src/
│   │   ├── components/  # 组件
│   │   ├── stores/      # Pinia 状态
│   │   └── views/       # 页面
│   └── vite.config.js
├── data/mock/        # 示例数据
├── manage.sh         # 项目管理脚本
├── Dockerfile        # Docker 构建文件
└── requirements.txt  # Python 依赖
```

## License

MIT