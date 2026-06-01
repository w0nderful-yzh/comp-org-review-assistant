# CompOrg Review Assistant

计算机组成原理复习助手，面向固定课程资料的章节练习、自动批改、错题本和基础统计。

## Phase 1 Stack

- Frontend: Vue 3 + Vite + TypeScript
- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL + pgvector in Docker
- Vector store: Chroma in Docker

## Start Middleware

```bash
docker compose up -d
```

## Start Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python scripts/seed_sample_questions.py
python scripts/import_homework_questions.py
python scripts/import_review_notes.py
uvicorn app.main:app --reload --port 8000
```

Preview the homework parser without writing to the database:

```bash
cd backend
python scripts/import_homework_questions.py --dry-run
```

Preview the review-note parser without writing knowledge chunks:

```bash
cd backend
python scripts/import_review_notes.py --dry-run
```

## Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The app includes:

- `知识库`: inspect parsed review-note knowledge points and search chapter chunks.
- `题库维护`: filter, review, and edit imported questions.
