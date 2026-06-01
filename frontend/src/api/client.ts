export type Chapter = {
  id: number;
  title: string;
  description: string | null;
  order_index: number;
  source_file: string;
  question_count: number;
};

export type Question = {
  id: number;
  chapter_id: number;
  type: QuestionType;
  difficulty: string;
  stem: string;
  options: Array<{ key: string; text: string }>;
  blank_count: number;
  source_type: "homework" | "ai" | "sample" | "manual";
  source_label: string;
  explanation?: string | null;
};

export type QuestionAdmin = Question & {
  answer_json: unknown;
  rubric_json: unknown;
  is_ai_generated: boolean;
  is_reviewed: boolean;
  source_assignment: string | null;
  source_context: string | null;
  created_at: string;
  updated_at: string;
};

export type QuestionAdminList = {
  items: QuestionAdmin[];
  total: number;
};

export type QuestionType =
  | "single_choice"
  | "multiple_choice"
  | "true_false"
  | "fill_blank"
  | "short_answer"
  | "calculation"
  | "question_group"
  | "cloze"
  | "matching";

export type PracticeSession = {
  id: number;
  mode: string;
  chapter_id: number | null;
  question_count: number;
  score: string | number | null;
  started_at: string;
  submitted_at: string | null;
  questions: Question[];
};

export type AnswerResult = {
  question_id: number;
  is_correct: boolean;
  score: number;
  feedback: string;
  correct_answer: unknown;
  explanation: string | null;
};

export type PracticeResult = {
  session_id: number;
  score: number;
  total: number;
  results: AnswerResult[];
};

export type WrongQuestion = {
  id: number;
  question: Question & { answer: unknown };
  wrong_count: number;
  mastered: boolean;
  last_wrong_at: string;
};

export type StatisticsOverview = {
  total_sessions: number;
  total_answers: number;
  correct_rate: number;
  wrong_question_count: number;
};

export type ChapterStatistics = {
  chapter_id: number;
  chapter_title: string;
  answered: number;
  correct_rate: number;
};

export type KnowledgePoint = {
  id: number;
  chapter_id: number;
  name: string;
  summary: string | null;
  difficulty: string;
};

export type KnowledgeChunk = {
  id: number;
  chunk_id: string;
  chapter_id: number;
  title: string | null;
  content: string;
  source_file: string;
  source_page: number | null;
};

export type KnowledgeSearch = {
  items: KnowledgeChunk[];
  total: number;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(detail.detail ?? response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  chapters: () => request<Chapter[]>("/api/chapters"),
  knowledgePoints: (chapterId: number) => request<KnowledgePoint[]>(`/api/chapters/${chapterId}/knowledge-points`),
  knowledgeChunks: (chapterId: number, limit = 30) =>
    request<KnowledgeChunk[]>(`/api/chapters/${chapterId}/knowledge-chunks?limit=${limit}`),
  searchKnowledge: (params: { q: string; chapter_id?: number | null; limit?: number }) => {
    const search = new URLSearchParams();
    search.set("q", params.q);
    if (params.chapter_id) search.set("chapter_id", String(params.chapter_id));
    search.set("limit", String(params.limit ?? 8));
    return request<KnowledgeSearch>(`/api/knowledge/search?${search.toString()}`);
  },
  adminQuestions: (params: {
    chapter_id?: number | null;
    question_type?: QuestionType | "";
    source_type?: "" | "homework" | "ai" | "sample" | "manual";
    reviewed?: boolean | "";
    keyword?: string;
    limit?: number;
    offset?: number;
  }) => {
    const search = new URLSearchParams();
    if (params.chapter_id) search.set("chapter_id", String(params.chapter_id));
    if (params.question_type) search.set("question_type", params.question_type);
    if (params.source_type) search.set("source_type", params.source_type);
    if (params.reviewed !== "") search.set("reviewed", String(params.reviewed));
    if (params.keyword) search.set("keyword", params.keyword);
    search.set("limit", String(params.limit ?? 30));
    search.set("offset", String(params.offset ?? 0));
    return request<QuestionAdminList>(`/api/admin/questions?${search.toString()}`);
  },
  updateQuestion: (
    questionId: number,
    payload: Partial<{
      chapter_id: number;
      type: QuestionType;
      difficulty: "easy" | "medium" | "hard";
      stem: string;
      options_json: unknown;
      answer_json: unknown;
      rubric_json: unknown;
      explanation: string | null;
      is_ai_generated: boolean;
      is_reviewed: boolean;
    }>,
  ) =>
    request<QuestionAdmin>(`/api/admin/questions/${questionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  createPractice: (payload: {
    mode: "chapter" | "final_review" | "wrong_questions";
    chapter_id?: number | null;
    question_count: number;
    question_types?: QuestionType[];
    user_id?: string;
  }) =>
    request<PracticeSession>("/api/practice-sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  submitPractice: (sessionId: number, answers: Array<{ question_id: number; user_answer: unknown }>) =>
    request<PracticeResult>(`/api/practice-sessions/${sessionId}/submit`, {
      method: "POST",
      body: JSON.stringify({ user_id: "demo", answers }),
    }),
  wrongQuestions: () => request<WrongQuestion[]>("/api/wrong-questions?user_id=demo"),
  markMastered: (questionId: number) =>
    request<{ mastered: boolean }>(`/api/wrong-questions/${questionId}/mastered?user_id=demo`, {
      method: "POST",
    }),
  overview: () => request<StatisticsOverview>("/api/statistics/overview?user_id=demo"),
  chapterStats: () => request<ChapterStatistics[]>("/api/statistics/chapters?user_id=demo"),
};
