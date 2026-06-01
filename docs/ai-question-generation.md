# AI Question Generation Plan

This project should keep AI generation as a teacher-reviewed draft flow, not a direct student-facing flow.

## Server Deployment Shape

```text
students/teachers
  -> Nginx or Caddy
  -> frontend static files
  -> FastAPI backend
  -> PostgreSQL + pgvector
  -> Chroma or pgvector retrieval index
  -> LLM provider API
```

Required production changes before public use:

- Add authentication and roles: student, teacher, admin.
- Keep the LLM API key only in backend environment variables.
- Add per-user and per-IP rate limits for generation endpoints.
- Run generation in a background job for larger batches.
- Log generation requests, reviewed status changes, and published questions.

## Generation Workflow

1. Teacher selects chapter, difficulty, question type, and count.
2. Backend retrieves relevant `knowledge_chunks` and optional existing homework examples.
3. Backend calls the LLM with a strict JSON schema.
4. Backend validates each draft question:
   - supported question type
   - valid answer JSON
   - valid options for choice questions
   - no empty stem or explanation
5. Backend inserts questions with:
   - `is_ai_generated = true`
   - `is_reviewed = false`
   - `source_assignment = "AI题目生成"`
   - `source_context =` referenced chunk IDs or source notes
6. Teacher reviews and edits the draft in `题库维护`.
7. Only reviewed questions become visible to students.

## Practice Source Scope

Student practice supports two source scopes:

- `original_only`: reviewed non-AI questions only.
- `include_ai`: reviewed non-AI questions plus reviewed AI-generated questions.

The frontend defaults to `original_only`. AI-generated questions can only enter practice after a teacher reviews them.

## Suggested API

```http
POST /api/admin/ai-question-drafts
```

Request:

```json
{
  "chapter_id": 3,
  "question_types": ["single_choice", "fill_blank"],
  "difficulty": "medium",
  "count": 5,
  "focus": "cache 命中率与平均访存时间"
}
```

Required environment variables:

```bash
AI_API_KEY=...
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4.1-mini
```

Response:

```json
{
  "created": 5,
  "question_ids": [211, 212, 213, 214, 215]
}
```

## Review Policy

- AI-generated questions stay hidden until `is_reviewed = true`.
- The UI should always show `AI生成` so teachers can distinguish them from homework originals.
- Homework originals should stay marked as `作业原题`; this is useful for复习优先级 and copyright/source tracking.
