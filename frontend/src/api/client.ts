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
  likes: number;
  user_liked: boolean;
  ai_status: string | null;
  quality_score: number;
  children: Question[];
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

export type AllQuestionsCompleted = {
  completed: true;
  message: string;
  total_questions: number;
  answered_questions: number;
  suggestions: string[];
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

export type PracticeHistoryItem = {
  id: number;
  mode: string;
  chapter_id: number | null;
  chapter_title: string | null;
  question_count: number;
  score: number | null;
  started_at: string;
  submitted_at: string | null;
};

export type AnswerReviewResult = {
  question_id: number;
  user_answer: unknown;
  is_correct: boolean | null;
  score: number | null;
  feedback: string | null;
  correct_answer: unknown;
  explanation: string | null;
};

export type PracticeReview = {
  id: number;
  mode: string;
  chapter_id: number | null;
  chapter_title: string | null;
  question_count: number;
  score: number | null;
  started_at: string;
  submitted_at: string | null;
  questions: Array<Question & { answer: unknown }>;
  results: AnswerReviewResult[];
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
  total_questions: number;
  correct_rate: number;
  coverage: number;
  mastered_rate: number;
  mastery_score: number;
};

export type QuestionTypeStatistics = {
  question_type: QuestionType;
  answered: number;
  correct_rate: number;
};

export type StudyRecommendation = {
  chapter_id: number;
  chapter_title: string;
  answered: number;
  correct_rate: number;
  wrong_count: number;
  reason: string;
  action: string;
  priority: number;
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

export type SourceScope = "original_only" | "standard" | "ai_new" | "ai_pool";

export type AiQuestionDraftResult = {
  created: number;
  question_ids: number[];
};

export type QuestionFeedbackResult = {
  question_id: number;
  likes: number;
  unhelpful: number;
  flags: number;
  user_liked: boolean;
  ai_status: string | null;
  quality_score: number;
};

export type AiStatus = {
  enabled: boolean;
  daily_remaining: number;
};

export type ExamSection = {
  id: string;
  title: string;
  score: number;
  slots: string[];
};

export type ExamSubQuestion = {
  id: string;
  label: string;
  prompt: string;
  score: number | null;
  answer_type: "text" | "single_choice";
  options: Array<{ key: string; text: string }>;
};

export type ExamSourceImage = {
  label: string;
  filename: string;
  url: string;
};

export type ExamQuestion = {
  id: string;
  section_id: string;
  number: string;
  title: string;
  score: number;
  stem: string;
  source_images: ExamSourceImage[];
  sub_questions: ExamSubQuestion[];
};

export type ExamPaper = {
  year: number;
  title: string;
  duration_minutes: number;
  total_score: number;
  paper_pdf: string;
  answer_pdf: string;
  sections: ExamSection[];
  source_url: string;
  questions: ExamQuestion[];
};

export type FeedbackType = "helpful" | "not_helpful" | "flag";
export type FlagReason = "answer_error" | "unclear_stem" | "ambiguous_options" | "out_of_scope" | "duplicate" | "unclear_explanation";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const TOKEN_KEY = "comp-org-review-token";

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE}${path}`, {
    headers,
    ...init,
  });
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem("comp-org-review-user");
      window.location.reload();
    }
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(detail.detail ?? response.statusText);
  }
  return response.json() as Promise<T>;
}

async function requestBlob(path: string, init?: RequestInit): Promise<Blob> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE}${path}`, {
    headers,
    ...init,
  });
  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem("comp-org-review-user");
      window.location.reload();
    }
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(detail.detail ?? response.statusText);
  }
  return response.blob();
}

export const api = {
  chapters: () => request<Chapter[]>("/api/chapters"),
  aiStatus: () => request<AiStatus>("/api/ai-status"),
  knowledgePoints: (chapterId: number) => request<KnowledgePoint[]>(`/api/chapters/${chapterId}/knowledge-points`),
  knowledgeChunks: (chapterId: number, limit = 30) =>
    request<KnowledgeChunk[]>(`/api/chapters/${chapterId}/knowledge-chunks?limit=${limit}`),
  coursewarePdf: (chapterId: number, download = false) =>
    requestBlob(`/api/chapters/${chapterId}/courseware-pdf${download ? "?download=true" : ""}`),
  examPapers: () => request<ExamPaper[]>("/api/exam-papers"),
  examPaperPdf: (year: number, kind: "paper" | "answer", download = false) =>
    requestBlob(`/api/exam-papers/${year}/${kind}-pdf${download ? "?download=true" : ""}`),
  searchKnowledge: (params: { q: string; chapter_id?: number | null; limit?: number }) => {
    const search = new URLSearchParams();
    search.set("q", params.q);
    if (params.chapter_id) search.set("chapter_id", String(params.chapter_id));
    search.set("limit", String(params.limit ?? 8));
    return request<KnowledgeSearch>(`/api/knowledge/search?${search.toString()}`);
  },
  createAiQuestionDrafts: (payload: {
    chapter_id?: number | null;
    question_types?: QuestionType[];
    difficulty?: "easy" | "medium" | "hard";
    count?: number;
    focus?: string | null;
  }) =>
    request<AiQuestionDraftResult>("/api/ai-question-drafts", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  submitFeedback: (questionId: number, feedbackType: FeedbackType, reason?: FlagReason) =>
    request<QuestionFeedbackResult>(`/api/questions/${questionId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ feedback_type: feedbackType, reason }),
    }),
  deleteFeedback: (questionId: number) =>
    request<{ deleted: boolean }>(`/api/questions/${questionId}/feedback`, {
      method: "DELETE",
    }),
  createPractice: (payload: {
    mode: "chapter" | "final_review" | "wrong_questions";
    chapter_id?: number | null;
    question_count: number;
    question_types?: QuestionType[];
    source_scope?: SourceScope;
  }) =>
    request<PracticeSession | AllQuestionsCompleted>("/api/practice-sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  submitPractice: (sessionId: number, answers: Array<{ question_id: number; user_answer: unknown }>) =>
    request<PracticeResult>(`/api/practice-sessions/${sessionId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),
  practiceHistory: () => request<PracticeHistoryItem[]>("/api/practice-sessions"),
  reviewPractice: (sessionId: number) => request<PracticeReview>(`/api/practice-sessions/${sessionId}/review`),
  deletePractice: (sessionId: number) =>
    request<{ deleted: boolean }>(`/api/practice-sessions/${sessionId}`, {
      method: "DELETE",
    }),
  wrongQuestions: () => request<WrongQuestion[]>("/api/wrong-questions"),
  markMastered: (questionId: number) =>
    request<{ mastered: boolean }>(`/api/wrong-questions/${questionId}/mastered`, {
      method: "POST",
    }),
  overview: () => request<StatisticsOverview>("/api/statistics/overview"),
  chapterStats: () => request<ChapterStatistics[]>("/api/statistics/chapters"),
  questionTypeStats: () => request<QuestionTypeStatistics[]>("/api/statistics/question-types"),
  recommendations: () => request<StudyRecommendation[]>("/api/statistics/recommendations"),
};
