# Insurance platform test automation

Python suite covering **API**, **E2E** (Kafka-backed happy path), and **UI** (Playwright).

## Prerequisites

```bash
# Stack running locally
docker compose up -d --build

# Install test deps (from repo root or tests/)
python3 -m venv .venv-tests
source .venv-tests/bin/activate
pip install -r tests/requirements.txt
playwright install chromium
```

| Target | Default URL | Env override |
|--------|-------------|--------------|
| Gateway API | http://localhost:8090 | `API_BASE_URL` |
| Staff UI | http://localhost:8088 | `UI_BASE_URL` |

## Run

```bash
# All tests
pytest tests/ -v

# Layers
pytest tests/api -v -m api
pytest tests/e2e -v -m e2e
pytest tests/ui -v -m ui --browser chromium

# Headed UI
pytest tests/ui -v -m ui --headed
```

## Layout

```
tests/
├── conftest.py          # URLs, auth helpers, wait utilities
├── api/                 # Gateway API contracts
├── e2e/                 # quote → UW → policy → finance
└── ui/                  # Playwright staff console flows
```

Demo users match README (`agent@insurance.local` / `agent123`, etc.).
