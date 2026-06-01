CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE question_type AS ENUM (
  'single_choice',
  'multiple_choice',
  'true_false',
  'fill_blank',
  'short_answer',
  'calculation',
  'question_group',
  'cloze',
  'matching'
);

CREATE TYPE question_difficulty AS ENUM ('easy', 'medium', 'hard');
CREATE TYPE practice_mode AS ENUM ('chapter', 'final_review', 'wrong_questions');

CREATE TABLE chapters (
  id SMALLSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  order_index SMALLINT NOT NULL UNIQUE,
  source_file TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE knowledge_points (
  id BIGSERIAL PRIMARY KEY,
  chapter_id SMALLINT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  summary TEXT,
  difficulty question_difficulty NOT NULL DEFAULT 'medium',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (chapter_id, name)
);

CREATE TABLE questions (
  id BIGSERIAL PRIMARY KEY,
  chapter_id SMALLINT NOT NULL REFERENCES chapters(id) ON DELETE RESTRICT,
  knowledge_point_id BIGINT REFERENCES knowledge_points(id) ON DELETE SET NULL,
  parent_question_id BIGINT REFERENCES questions(id) ON DELETE CASCADE,
  type question_type NOT NULL,
  difficulty question_difficulty NOT NULL DEFAULT 'medium',
  stem TEXT NOT NULL,
  options_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  answer_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  rubric_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  explanation TEXT,
  source_context TEXT,
  source_assignment TEXT,
  is_ai_generated BOOLEAN NOT NULL DEFAULT false,
  is_reviewed BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE practice_sessions (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT,
  mode practice_mode NOT NULL,
  chapter_id SMALLINT REFERENCES chapters(id) ON DELETE SET NULL,
  question_count INTEGER NOT NULL DEFAULT 0 CHECK (question_count >= 0),
  score NUMERIC(6, 2),
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  submitted_at TIMESTAMPTZ
);

CREATE TABLE answer_records (
  id BIGSERIAL PRIMARY KEY,
  session_id BIGINT NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
  question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
  user_answer JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_correct BOOLEAN,
  score NUMERIC(6, 2),
  feedback TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (session_id, question_id)
);

CREATE TABLE wrong_questions (
  id BIGSERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  question_id BIGINT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  wrong_count INTEGER NOT NULL DEFAULT 1 CHECK (wrong_count > 0),
  last_wrong_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  mastered BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (user_id, question_id)
);

CREATE TABLE knowledge_chunks (
  id BIGSERIAL PRIMARY KEY,
  chapter_id SMALLINT NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
  chunk_id TEXT NOT NULL UNIQUE,
  title TEXT,
  content TEXT NOT NULL,
  source_file TEXT NOT NULL,
  source_page INTEGER,
  embedding vector(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_knowledge_points_chapter_id ON knowledge_points(chapter_id);
CREATE INDEX idx_questions_chapter_type_reviewed ON questions(chapter_id, type, is_reviewed);
CREATE INDEX idx_questions_parent_question_id ON questions(parent_question_id);
CREATE INDEX idx_practice_sessions_user_id ON practice_sessions(user_id);
CREATE INDEX idx_answer_records_session_id ON answer_records(session_id);
CREATE INDEX idx_wrong_questions_user_mastered ON wrong_questions(user_id, mastered);
CREATE INDEX idx_knowledge_chunks_chapter_id ON knowledge_chunks(chapter_id);

INSERT INTO chapters (order_index, title, description, source_file)
VALUES
  (1, '概论', '计算机系统概论与基础概念', 'materials/review-notes/chapter-01-overview-summary.docx'),
  (2, '总线', '总线结构、通信与控制', 'materials/review-notes/chapter-02-bus-summary.docx'),
  (3, '信息编码与数据表示', '数据表示、编码与数制转换', 'materials/review-notes/chapter-03-data-representation-summary.docx'),
  (4, '运算方法与运算器', '算术逻辑运算、补码与运算器', 'materials/review-notes/chapter-04-arithmetic-alu-summary.docx'),
  (5, '存储体系', '主存、Cache、虚拟存储与层次结构', 'materials/review-notes/chapter-05-memory-hierarchy-summary.docx'),
  (6, '指令系统', '指令格式、寻址方式与指令类型', 'materials/review-notes/chapter-06-instruction-system-summary.docx'),
  (7, '控制器', '控制单元、微程序与流水线基础', 'materials/review-notes/chapter-07-control-unit-summary.docx'),
  (8, 'RISC-V 与 ARM 模型机设计实例', 'RISC-V、ARM 与模型机设计', 'materials/review-notes/chapter-08-riscv-arm-model-machine-summary.docx'),
  (9, '输入输出系统', 'I/O 接口、中断、DMA 与外设管理', 'materials/review-notes/chapter-09-io-system-summary.docx')
ON CONFLICT (order_index) DO NOTHING;
