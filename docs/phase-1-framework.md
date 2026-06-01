# Phase 1 Development Framework

## Decision

Phase 1 should implement a small, complete MVP before advanced AI workflows.

Recommended stack for this repository:

- Frontend: Vue 3 + Vite + TypeScript
- Backend: FastAPI + Python
- Relational database: PostgreSQL in Docker
- Vector store: Chroma in Docker
- Document parsing: python-docx and PyMuPDF, added after the base question-bank flow works

This keeps the first version close to the overview recommendation while using a Dockerized database from the start. SQLite is still useful for tiny prototypes, but PostgreSQL is a better foundation for the schema, statistics, JSON answers, and later pgvector experiments.

## Phase 1 Scope

Build these first:

- Chapter list seeded from `materials/MATERIALS_MANIFEST.md`
- Question bank tables
- Chapter practice and final-review random practice
- Rule-based grading for single choice, multiple choice, true/false, and fill-in-the-blank questions
- Reference-answer or keyword scoring path for short-answer questions
- Wrong-question tracking
- Basic statistics

Delay these until the base flow is stable:

- User-uploaded courseware
- Full teacher/admin portal
- Class management
- Exam anti-cheating
- Complex knowledge graph
- Multi-model configuration UI

## Local Middleware

Start services:

```bash
docker compose up -d
```

PostgreSQL:

```text
Host: localhost
Port: 5432
Database: comp_org_review
User: comp_org
Password: comp_org_dev_password
```

Chroma:

```text
URL: http://localhost:8001
```

Backend apps can read:

```text
DATABASE_URL=postgresql+psycopg://comp_org:comp_org_dev_password@localhost:5432/comp_org_review
CHROMA_URL=http://localhost:8001
```
