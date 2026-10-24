# Contributing to DataMind

Thanks for your interest in contributing. Here is a short guide to get started.

## Development setup

Follow the steps in [README.md](./README.md#getting-started) to start infrastructure, the backend and the frontend.

```bash
# backend (from the repository root)
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# frontend (separate terminal)
cd frontend
pnpm install
pnpm dev
```

## Before opening a pull request

- Run the golden evaluation set and keep the pass rate from regressing:

  ```bash
  cd backend
  ..\.venv\Scripts\python.exe -m app.eval
  ```

- Verify the backend imports and migrations apply cleanly.
- Verify the frontend builds:

  ```bash
  cd frontend
  pnpm build
  ```

- Extend the evaluation set in `backend/app/eval/cases.py` when you change prompts, the model, or SQL generation.

## Conventions

- All SQL execution goes through `sql_exec`; never run model output directly.
- All model and embedding calls go through `gateway`.
- Keep the single-instance, single-operator assumption: no accounts or tenants.
- Write in the language of the surrounding file (the product UI and most docs are Chinese; the default README is Chinese, and the English version lives in README.en.md).

## Questions

Open an issue for bugs, feature ideas, or questions about the architecture.

