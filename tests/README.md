# Insurance platform test automation

Python suite covering **API**, **E2E** (Kafka-backed happy path), and **UI** (Playwright), with optional **Zephyr Scale** sync for Story → Test Case → Automation.

## Prerequisites

```bash
# Stack running locally
docker compose up -d --build

# Or point at a cluster / remote gateway + UI
export API_BASE_URL=http://localhost:8090
export UI_BASE_URL=http://localhost:8088

# Install test deps (from repo root)
python3 -m venv .venv-tests
source .venv-tests/bin/activate
pip install -r tests/requirements.txt
playwright install chromium
```

| Target | Default URL | Env override |
|--------|-------------|--------------|
| Gateway API | http://localhost:8090 | `API_BASE_URL` |
| Staff UI | http://localhost:8088 | `UI_BASE_URL` |
| Product Studio | http://localhost:8089 | `PRODUCT_UI_BASE_URL` |

## Run

```bash
# All tests + JUnit report (for Zephyr / CI artifacts)
mkdir -p reports
pytest tests/ -v --browser chromium --junitxml=reports/junit.xml

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
├── conftest.py          # URLs, auth helpers, Zephyr plugin hook
├── api/                 # Gateway API contracts
├── e2e/                 # quote → UW → policy → finance
├── ui/                  # Playwright staff console flows
└── zephyr/              # Scale client, pytest plugin, nodeid→case mapping
scripts/
├── zephyr_sync.py       # Code → Zephyr Scale test cases (+ story links)
└── zephyr_publish.py    # JUnit XML → Zephyr Scale test cycle
reports/                 # Local junit.xml (gitignored)
```

Demo users match README (`agent@insurance.local` / `agent123`, etc.).

## Story → Case → Automation (Zephyr Scale)

```text
Jira Story (INS-101…)
    → Zephyr Scale Test Case (INS-T12…)
        → pytest test (httpx and/or Playwright)
            → reports/junit.xml
                → Zephyr Scale Test Cycle (pass/fail)
```

Playwright is the **UI driver** inside pytest (`pytest-playwright`). Zephyr only consumes pytest JUnit results; it does not talk to Playwright directly.

### Markers

| Marker | Meaning |
|--------|---------|
| `@pytest.mark.story("INS-101")` | Jira story for coverage linking |
| `@pytest.mark.zephyr("INS-T12")` | Stable Zephyr Scale case key |
| `@pytest.mark.api` / `e2e` / `ui` | Layer labels synced to Scale |

Placeholder stories used in this suite (replace with real Jira keys in your project):

| Story key | Capability |
|-----------|------------|
| `KAN-1` | Auth / login |
| `KAN-2` | New business quote → bind |
| `KAN-3` | Underwriting / policy admin |
| `KAN-4` | Claims / finance |
| `KAN-5` | Product Studio catalog / risk schema / UW rules / rates |

After the first `zephyr_sync.py` run, case keys are written to [`tests/zephyr/mapping.json`](zephyr/mapping.json). Prefer promoting them into `@pytest.mark.zephyr("…")` on the test for durable source control.

### Sync cases (code → Zephyr)

```bash
export ZEPHYR_SCALE_TOKEN=...          # Zephyr Scale API token
export ZEPHYR_PROJECT_KEY=INS          # Jira / Scale project key

# Optional: link cases to Jira stories
export JIRA_BASE_URL=https://your-domain.atlassian.net
export JIRA_EMAIL=you@example.com
export JIRA_API_TOKEN=...
# Required for scoped API tokens (ATATT…): site cloud ID
export JIRA_CLOUD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

python scripts/zephyr_sync.py --dry-run
python scripts/zephyr_sync.py
```

### Publish results (automation → cycle)

```bash
pytest tests/ -v --browser chromium --junitxml=reports/junit.xml
python scripts/zephyr_publish.py \
  --junit reports/junit.xml \
  --cycle-name "local $(git rev-parse --short HEAD)" \
  --auto-create-cases
```
