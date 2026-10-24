# DataMind

Natural-language data analytics agent. Ask a question about your database, get back executable SQL, ECharts charts, deterministic BI insights, and a narrative that cites the real numbers.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-18%2B-339933)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)](./CONTRIBUTING.md)

DataMind turns a plain-language question into:

- a read-only SQL query,
- one or more ECharts charts (any chart type),
- deterministic BI insights — summary, ranking, composition, trend, anomaly, attribution,
- a natural-language narrative that only cites figures it was given.

Everything is streamed over SSE and persisted so follow-up questions keep the previous context.

## Features

- **Model-agnostic gateway** — built on LiteLLM. Works with OpenAI, DeepSeek, Qwen, GLM, and any provider LiteLLM supports. Fallback model chains, structured output via instructor, streaming, and per-task usage metrics.
- **RGA knowledge base** — database schema metadata (tables, columns, types, comments, keys) is chunked and vectorized into Qdrant, with dense + sparse hybrid retrieval.
- **Safe SQL execution** — `sqlglot` AST-level read-only validation, a forced `LIMIT`, execution timeout, and JSON-safe decimal/date serialization. The LLM is never trusted to be the safety layer.
- **Multi-chart generation** — one question can produce several charts of any type; real query results are injected back into the ECharts options.
- **BI analysis** — deterministic insights plus an LLM-written narrative; anomaly detection and dimension-level attribution included.
- **Conversations & multi-turn** — messages, charts and insights persist; follow-ups receive the prior turns and their SQL.
- **Dashboards, export, type switching** — save/load dashboards, export charts as PNG/PDF, switch chart types on the fly.
- **Engineering** — golden evaluation set, structured request logs, `/api/metrics`, rate limiting, and Docker images.

## How it works

```
question
  → persist user message + load recent turns
  → RGA retrieval (Qdrant dense + sparse hybrid)
  → build prompt (system rules + retrieved context + history)
  → LLM generates a structured AnalysisPlan (SQL + ECharts option per chart)
  → per chart: read-only validation → execute SQL → inject real data into chart option
  → deterministic BI insights (summary / rank / composition / trend / anomaly / attribution)
  → LLM narrative (summary + highlights)
  → SSE stream: start → retrieved → sql → executing → chart → insight → narrative → done
  → persist charts, insights and narrative for history
```

## Architecture

```
┌───────────────┐        ┌────────────────────────────────────────────┐
│   Frontend    │        │              Backend (FastAPI)              │
│ React + TS    │◀─HTTP/SSE─▶│  API layer (REST + SSE)                  │
│ ECharts / chat│        │  Agent · Model gateway · RGA · SQL executor │
└───────────────┘        └───────┬─────────────────────────────────────┘
                                  │
                 ┌────────────────┼──────────────────┐
                 ▼                ▼                  ▼
           ┌───────────┐    ┌──────────┐      ┌──────────────┐
           │   Qdrant  │    │   Redis  │      │  PostgreSQL  │
           │ RGA index │    │ (reserved)│      │ metadata/chat│
           └───────────┘    └──────────┘      └──────────────┘
                 │
                 ▼
        External model providers         Target database (read-only connection)
        OpenAI / DeepSeek / Qwen / ...   MySQL / PostgreSQL / ClickHouse / ...
```

## Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.11+ · FastAPI · SQLAlchemy 2 (async) · Alembic · Pydantic v2 |
| Models | LiteLLM · instructor · DeepSeek by default (replaceable) |
| Retrieval | Qdrant (dense + sparse hybrid) · sqlglot |
| Frontend | React 18 · TypeScript · Vite · ECharts · Zustand · jsPDF |
| Infrastructure | PostgreSQL 16 · Qdrant · Redis |
| Observability | structlog · `/api/metrics` · per-request `request_id` |

## Directory structure

```
datamind/
├─ backend/
│  ├─ app/
│  │  ├─ api/            # REST + SSE routers
│  │  ├─ agent/          # orchestration, prompts, structured output
│  │  ├─ bi/             # insights, anomaly, attribution, narrative, data fill
│  │  ├─ core/           # config, db, security, logging, rate limit, metrics
│  │  ├─ eval/           # golden evaluation set and runner
│  │  ├─ gateway/        # LiteLLM adapter + routing/fallback
│  │  ├─ knowledge/      # schema crawl, chunking, embedding, retrieval
│  │  ├─ models/         # SQLAlchemy models
│  │  ├─ schemas/        # Pydantic schemas
│  │  ├─ services/       # datasource service and others
│  │  └─ sql_exec/       # SQL validation and read-only execution
│  ├─ alembic/           # database migrations
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/
│  ├─ src/
│  │  ├─ api/            # fetch + SSE client
│  │  ├─ charts/         # ECharts wrapper, type conversion, instance registry
│  │  ├─ export/         # PNG / PDF export
│  │  ├─ stores/         # Zustand state
│  │  └─ App.tsx
│  └─ Dockerfile
├─ deploy/
│  ├─ docker-compose.yml       # development infrastructure
│  └─ docker-compose.prod.yml  # production stack
├─ PRD.md                      # product requirements (Chinese)
├─ 技术方案设计.md              # technical design (Chinese)
└─ 开发计划.md                  # development plan (Chinese)
```

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+ and pnpm
- Docker Desktop

### 1. Start infrastructure

```bash
docker compose -f deploy/docker-compose.yml up -d
```

This starts PostgreSQL (`5432`), Qdrant (`6333`) and Redis (`6379`).

### 2. Run the backend

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip

copy backend\.env.example backend\.env
# edit backend\.env and set at least DEEPSEEK_API_KEY

cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

> If bare `python` resolves to Python 2.7 on your machine, use the `py -3.13` launcher.

Health checks:

- liveness: `GET http://127.0.0.1:8000/api/healthz`
- readiness (includes Qdrant): `GET http://127.0.0.1:8000/api/readyz`
- metrics: `GET http://127.0.0.1:8000/api/metrics`

### 3. Run the frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:5173`. Requests to `/api` are proxied to the backend on port `8000`.

### 4. First query

1. Select or add a data source in the sidebar (click "sync knowledge base" after adding).
2. Create a conversation.
3. Ask something like: *"各区域成交额是多少，并给出每日趋势"* (what is GMV by region, with the daily trend).

## Configuration

Backend settings are read from `backend/.env` (gitignored). Key variables:

| Variable | Description |
| --- | --- |
| `ENVIRONMENT` | `dev` or `prod`; controls log format |
| `DEBUG` | `true` logs SQL execution |
| `DATABASE_URL` | metadata database URL (PostgreSQL + asyncpg) |
| `QDRANT_URL` / `QDRANT_COLLECTION` | Qdrant endpoint and collection name |
| `REDIS_URL` | Redis endpoint |
| `FERNET_KEY` | encryption key for datasource passwords; empty uses a dev default |
| `MODEL_DEFAULT` | primary model in LiteLLM naming, e.g. `deepseek/deepseek-chat` |
| `MODEL_FALLBACKS` | comma-separated fallback model chain |
| `EMBEDDING_DEFAULT` | embedding model name |
| `RATE_LIMIT_PER_MINUTE` | request limit for `/analyze` and `/query` (default 30) |
| `DEEPSEEK_API_KEY` etc. | provider API keys, following LiteLLM conventions |

The gateway is built on LiteLLM, so any provider it supports can be enabled through `MODEL_DEFAULT` and its API key.

## API overview

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/healthz` | liveness |
| GET | `/api/readyz` | readiness (includes Qdrant) |
| GET | `/api/metrics` | counters and uptime |
| GET / POST | `/api/datasources` | list / create data sources |
| DELETE | `/api/datasources/{id}` | delete a data source |
| GET | `/api/datasources/{id}/test` | test connection |
| GET | `/api/datasources/{id}/schema` | fetch schema metadata |
| POST | `/api/datasources/{id}/sync` | build the RGA knowledge base |
| GET | `/api/datasources/{id}/search?q=` | search the knowledge base |
| POST | `/api/datasources/{id}/analyze` | non-streaming analysis |
| POST | `/api/datasources/{id}/analyze/stream` | streaming analysis (SSE) |
| GET / POST | `/api/conversations` | list / create conversations |
| GET | `/api/conversations/{id}/messages` | conversation messages |
| GET | `/api/conversations/{id}/charts` | conversation charts |
| POST | `/api/conversations/{id}/query` | ask within a conversation (SSE) |
| GET / POST | `/api/dashboards` | list / save dashboards |
| GET | `/api/dashboards/{id}` | dashboard detail |
| PATCH | `/api/charts/{id}` | update chart type and options |

SSE event order: `start → retrieved → sql → executing → chart → insight → narrative → done`, with `error` on failure.

## Evaluation & observability

Run the golden evaluation set (requires a configured model key):

```bash
cd backend
..\.venv\Scripts\python.exe -m app.eval
```

Pass a data source id to override the default: `python -m app.eval 1`.

Observability:

- structlog request logs with `request_id`, method, path, status and duration; JSON in production.
- `/api/metrics` exposes gateway calls (per task, ok/error) and SQL execution counts.
- messages and charts persist in `messages` / `charts`; `audit_logs` is reserved for future auditing.

## Production (Docker)

```bash
cp deploy/.env.example deploy/.env
# edit deploy/.env and set DEEPSEEK_API_KEY, FERNET_KEY, ...
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

Frontend runs at `http://localhost:8080`, backend at `http://localhost:8000`. The backend container runs migrations on startup.

## Contributing

Pull requests are welcome. For larger changes, open an issue first to discuss what you would like to change.

The evaluation set (`backend/app/eval`) is the safety net for generation quality — please extend it when you change prompts, the model, or SQL generation.

## Documentation

Product requirements, technical design and the development plan are tracked in the repository (currently written in Chinese):

- [PRD.md](./PRD.md)
- [技术方案设计.md](./技术方案设计.md)
- [开发计划.md](./开发计划.md)

## Implementation notes

- The model only understands and generates; SQL safety is enforced independently by the backend. Use a read-only database account in production.
- RGA indexes schema metadata (tables, columns, comments, keys), not data rows.
- Retrieval embeddings currently use a local hash placeholder because DeepSeek has no embedding endpoint. Point `EMBEDDING_DEFAULT` at a real embedding model for semantic search.
- Redis is provisioned but result caching and async task queues are not wired yet.
- The demo reuses one `datamind` database for both app metadata and sample business tables; point data sources at a separate business database in real use.
- The frontend bundles full ECharts and jsPDF; the bundle is large and can be code-split later.

## License

[MIT](./LICENSE) © DataMind contributors

