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
  explanation?: string | null;
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
