ALTER TABLE questions ADD COLUMN archived BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE question_feedback (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  is_helpful BOOLEAN NOT NULL,
  feedback_type TEXT,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, question_id)
);

CREATE INDEX idx_question_feedback_question_id ON question_feedback(question_id);
