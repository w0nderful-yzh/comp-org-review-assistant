ALTER TABLE questions ADD COLUMN ai_status TEXT DEFAULT NULL;
ALTER TABLE questions ADD COLUMN quality_score INTEGER NOT NULL DEFAULT 0;
ALTER TABLE questions ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE questions ADD COLUMN helpful_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE questions ADD COLUMN not_helpful_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE questions ADD COLUMN error_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE questions ADD COLUMN flag_count INTEGER NOT NULL DEFAULT 0;

-- Set existing AI questions to 'verified' status (they were already reviewed)
UPDATE questions SET ai_status = 'verified' WHERE is_ai_generated = true AND is_reviewed = true;

CREATE INDEX idx_questions_ai_status ON questions(ai_status) WHERE ai_status IS NOT NULL;
