# Backend

FastAPI service for the CompOrg Review Assistant MVP.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/seed_sample_questions.py
uvicorn app.main:app --reload --port 8000
```

The service expects PostgreSQL from the repository root:

```bash
docker compose up -d
```
