CREATE TABLE IF NOT EXISTS lab_exam_generations (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  paper_json JSONB,
  answer_json JSONB,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_lab_exam_generations_user_created
  ON lab_exam_generations(user_id, created_at DESC);
