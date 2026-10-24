# DataMind

自然语言驱动的数据分析智能体：向数据库提一个问题，即可得到可执行的 SQL、ECharts 图表、可追溯的 BI 洞察，以及引用真实数字的整体解读。

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-18%2B-339933)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](./CONTRIBUTING.md)

> English version: [README.en.md](./README.en.md)

DataMind 能把一句自然语言变成：

- 一条只读的 SQL 查询；
- 一张或多张 ECharts 图表（图表类型不限制）；
- 确定性 BI 洞察——汇总、排名、构成占比、趋势、异常检测、归因分析；
- 一段只引用给定数字的自然语言整体解读。

整个过程通过 SSE 流式返回并持久化，后续追问会带上之前的上下文。

## 核心特性

- 多模型网关：基于 LiteLLM，支持 OpenAI、DeepSeek、通义、智谱等厂商；带主备模型链与降级、instructor 结构化输出、流式输出和按任务的调用计量。
- RGA 知识库：把数据库 Schema 元数据（表、字段、类型、注释、主外键）切块并向量化写入 Qdrant，支持稠密 + 稀疏混合检索。
- 安全的 SQL 执行：sqlglot AST 级只读校验、强制 LIMIT、执行超时、Decimal/日期序列化；模型输出从不被当作安全边界。
- 多图表生成：一次提问可生成多张任意类型的图表，执行结果回填进 ECharts 配置。
- BI 分析：确定性洞察 + LLM 语言化解读，含异常检测与维度级归因。
- 会话与多轮：消息、图表、洞察持久化，追问会携带历史与上轮 SQL。
- 看板、导出、类型切换：看板保存/载入、PNG/PDF 导出、图表类型即时切换。
- 工程能力：黄金评测集、结构化请求日志、`/api/metrics`、限流与 Docker 镜像。

## 工作原理

```
用户提问
  → 持久化 user 消息并加载最近几轮对话
  → RGA 检索（Qdrant 稠密 + 稀疏混合检索）
  → 组装 Prompt（系统约束 + 检索上下文 + 历史）
  → LLM 生成结构化 AnalysisPlan（每张图的 SQL + ECharts option）
  → 逐图处理：只读校验 → 执行 SQL → 把真实数据回填进图表配置
  → 确定性 BI 洞察（汇总 / 排名 / 占比 / 趋势 / 异常 / 归因）
  → LLM 整体解读（summary + highlights）
  → SSE 流式：start → retrieved → sql → executing → chart → insight → narrative → done
  → 持久化图表、洞察和解读，供历史回看
```

## 总体架构

```
┌───────────────┐        ┌────────────────────────────────────────────┐
│  前端 SPA      │        │              后端（FastAPI）                │
│ React + TS    │◀─HTTP/SSE─▶│  API 层（REST + SSE）                    │
│ ECharts / chat│        │  Agent 编排 · 模型网关 · RGA · SQL 执行      │
└───────────────┘        └───────┬─────────────────────────────────────┘
                                  │
                 ┌────────────────┼──────────────────┐
                 ▼                ▼                  ▼
           ┌───────────┐    ┌──────────┐      ┌──────────────┐
           │   Qdrant  │    │   Redis  │      │  PostgreSQL  │
           │  RGA 索引 │    │（预留）   │      │ 元数据/会话   │
           └───────────┘    └──────────┘      └──────────────┘
                 │
                 ▼
        外部模型厂商                   目标数据库（只读连接）
        OpenAI / DeepSeek / 通义 / …  MySQL / PostgreSQL / ClickHouse / …
```

## 技术栈

| 层       | 技术                                                                       |
| -------- | -------------------------------------------------------------------------- |
| 后端     | Python 3.11+ · FastAPI · SQLAlchemy 2（async） · Alembic · Pydantic v2 |
| 模型     | LiteLLM · instructor · 默认 DeepSeek（可替换）                           |
| 检索     | Qdrant（稠密 + 稀疏混合检索） · sqlglot                                   |
| 前端     | React 18 · TypeScript · Vite · ECharts · Zustand · jsPDF              |
| 基础设施 | PostgreSQL 16 · Qdrant · Redis                                           |
| 可观测   | structlog ·`/api/metrics` · 请求级 request_id                          |

## 目录结构

```
datamind/
├─ backend/
│  ├─ app/
│  │  ├─ api/            # REST 与 SSE 路由
│  │  ├─ agent/          # 编排、Prompt、结构化输出
│  │  ├─ bi/             # 洞察、异常、归因、语言化、数据回填
│  │  ├─ core/           # 配置、数据库、安全、日志、限流、指标
│  │  ├─ eval/           # 黄金评测集与跑分
│  │  ├─ gateway/        # LiteLLM 适配 + 路由降级
│  │  ├─ knowledge/      # Schema 采集、切块、向量化、检索
│  │  ├─ models/         # SQLAlchemy 模型
│  │  ├─ schemas/        # Pydantic 模型
│  │  ├─ services/       # 数据源等业务服务
│  │  └─ sql_exec/       # SQL 校验与只读执行
│  ├─ alembic/           # 数据库迁移
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/
│  ├─ src/
│  │  ├─ api/            # fetch + SSE 客户端
│  │  ├─ charts/         # ECharts 封装、类型转换、实例注册
│  │  ├─ export/         # PNG / PDF 导出
│  │  ├─ stores/         # Zustand 状态
│  │  └─ App.tsx
│  └─ Dockerfile
├─ deploy/
│  ├─ docker-compose.yml       # 开发基础设施
│  └─ docker-compose.prod.yml  # 生产全栈
├─ PRD.md                      # 产品需求设计
├─ 技术方案设计.md              # 技术方案
└─ 开发计划.md                  # 开发计划与进度
```

## 快速开始（开发模式）

前置要求：Python 3.11+、Node.js 18+、pnpm、Docker Desktop。

### 1. 启动基础设施

```bash
docker compose -f deploy/docker-compose.yml up -d
```

这会启动 PostgreSQL（`5432`）、Qdrant（`6333`）和 Redis（`6379`）。

### 2. 启动后端

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip

copy backend\.env.example backend\.env
# 编辑 backend\.env，至少填入 DEEPSEEK_API_KEY

cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

> 如果本机裸 `python` 指向 Python 2.7，请使用 `py -3.13` 启动器。

健康检查：

- 存活：`GET http://127.0.0.1:8000/api/healthz`
- 就绪（含 Qdrant 连通性）：`GET http://127.0.0.1:8000/api/readyz`
- 指标：`GET http://127.0.0.1:8000/api/metrics`

### 3. 启动前端

```bash
cd frontend
pnpm install
pnpm dev
```

打开 `http://localhost:5173`，`/api` 请求已代理到后端 8000 端口。

### 4. 首次提问

1. 在左侧选择或添加数据源（添加后点击「同步知识库」建立 RGA 索引）。
2. 点击「新建会话」。
3. 输入问题，例如「各区域成交额是多少，并给出每日趋势」。

## 配置说明

后端配置从 `backend/.env` 读取（该文件已加入 .gitignore）。主要变量：

| 变量                                   | 说明                                               |
| -------------------------------------- | -------------------------------------------------- |
| `ENVIRONMENT`                        | `dev` 或 `prod`，影响日志格式                  |
| `DEBUG`                              | `true` 时输出 SQL 执行日志                       |
| `DATABASE_URL`                       | 元数据库连接串（PostgreSQL + asyncpg）             |
| `QDRANT_URL` / `QDRANT_COLLECTION` | Qdrant 地址与集合名                                |
| `REDIS_URL`                          | Redis 地址                                         |
| `FERNET_KEY`                         | 数据源密码加密密钥；留空使用本地开发默认密钥       |
| `MODEL_DEFAULT`                      | 主模型，LiteLLM 命名，如`deepseek/deepseek-chat` |
| `MODEL_FALLBACKS`                    | 备用模型链，逗号分隔                               |
| `EMBEDDING_DEFAULT`                  | 向量模型名（当前检索默认走本地 Hash 嵌入）         |
| `RATE_LIMIT_PER_MINUTE`              | `/analyze`、`/query` 的限流（默认 30）         |
| `DEEPSEEK_API_KEY` 等                | 各厂商 API Key，按 LiteLLM 约定注入                |

模型网关基于 LiteLLM，任何 LiteLLM 支持的厂商都可以通过 `MODEL_DEFAULT` 与对应 Key 接入。

## API 概览

| 方法       | 路径                                     | 说明                  |
| ---------- | ---------------------------------------- | --------------------- |
| GET        | `/api/healthz`                         | 存活检查              |
| GET        | `/api/readyz`                          | 就绪检查（含 Qdrant） |
| GET        | `/api/metrics`                         | 计数器与运行时长      |
| GET / POST | `/api/datasources`                     | 数据源列表 / 创建     |
| DELETE     | `/api/datasources/{id}`                | 删除数据源            |
| GET        | `/api/datasources/{id}/test`           | 连接测试              |
| GET        | `/api/datasources/{id}/schema`         | 拉取 Schema 元数据    |
| POST       | `/api/datasources/{id}/sync`           | 同步知识库（RGA）     |
| GET        | `/api/datasources/{id}/search?q=`      | 知识库检索            |
| POST       | `/api/datasources/{id}/analyze`        | 非流式分析            |
| POST       | `/api/datasources/{id}/analyze/stream` | 流式分析（SSE）       |
| GET / POST | `/api/conversations`                   | 会话列表 / 创建       |
| GET        | `/api/conversations/{id}/messages`     | 历史消息              |
| GET        | `/api/conversations/{id}/charts`       | 会话图表              |
| POST       | `/api/conversations/{id}/query`        | 会话内提问（SSE）     |
| GET / POST | `/api/dashboards`                      | 看板列表 / 保存       |
| GET        | `/api/dashboards/{id}`                 | 看板详情              |
| PATCH      | `/api/charts/{id}`                     | 更新图表类型与配置    |

SSE 事件顺序：`start → retrieved → sql → executing → chart → insight → narrative → done`，失败时发送 `error`。

## 评测与可观测

运行黄金评测集（需已配置模型 Key）：

```bash
cd backend
..\.venv\Scripts\python.exe -m app.eval
```

可传入数据源 ID 覆盖默认值：`python -m app.eval 1`。

可观测能力：

- structlog 结构化请求日志，带 `request_id`、method、path、status、耗时；生产环境输出 JSON。
- `/api/metrics` 返回网关调用（按任务分 ok/error）、SQL 执行次数等计数器。
- 消息与图表持久化在 `messages` / `charts` 表；`audit_logs` 表已建立，供后续审计接入。

## 生产部署（Docker）

```bash
cp deploy/.env.example deploy/.env
# 编辑 deploy/.env，填入 DEEPSEEK_API_KEY、FERNET_KEY 等
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

前端运行在 `http://localhost:8080`，后端为 `http://localhost:8000`。后端容器启动时自动执行 Alembic 迁移。

## 贡献

欢迎提交 Pull Request。较大改动请先开 Issue 讨论。

评测集（`backend/app/eval`）是生成质量的安全网——修改 Prompt、模型或 SQL 生成逻辑时，请同步扩展它。详细约定见 [CONTRIBUTING.md](./CONTRIBUTING.md)。

## 实现说明与注意事项

- 模型只负责理解与生成，SQL 安全由后端独立强制；生产环境请使用数据库只读账号。
- RGA 索引的是 Schema 元数据（表/字段/注释/主外键），不索引数据行。
- 当前 RGA 检索嵌入使用本地 Hash 占位（DeepSeek 不提供 Embedding 接口）；如需语义检索，把 `EMBEDDING_DEFAULT` 换成真实向量模型并接入网关即可。
- Redis 已随基础设施启动，但结果缓存与异步任务队列目前是预留，尚未接线。
- 演示环境将应用元数据与示例业务表放在同一个 `datamind` 库；真实使用请让数据源指向独立业务库。
- 前端默认打包完整 ECharts 与 jsPDF，产物体积较大，可按需做代码分割。

## License

[MIT](./LICENSE) © DataMind contributors
