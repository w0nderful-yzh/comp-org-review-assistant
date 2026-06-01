<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">组</div>
        <div>
          <h1>计算机组成原理复习助手</h1>
          <p>MVP 工作台</p>
        </div>
      </div>

      <nav class="nav-list" aria-label="主导航">
        <button :class="{ active: activeView === 'practice' }" @click="activeView = 'practice'">
          <BookOpen :size="18" />
          <span>章节练习</span>
        </button>
        <button :class="{ active: activeView === 'wrong' }" @click="openWrongQuestions">
          <RotateCcw :size="18" />
          <span>错题本</span>
        </button>
        <button :class="{ active: activeView === 'stats' }" @click="openStats">
          <BarChart3 :size="18" />
          <span>学习统计</span>
        </button>
        <button :class="{ active: activeView === 'knowledge' }" @click="openKnowledge">
          <FileText :size="18" />
          <span>知识库</span>
        </button>
        <button :class="{ active: activeView === 'admin' }" @click="openAdmin">
          <ClipboardList :size="18" />
          <span>题库维护</span>
        </button>
      </nav>

      <section class="sidebar-panel">
        <div class="mini-stat">
          <span>练习次数</span>
          <strong>{{ overview?.total_sessions ?? 0 }}</strong>
        </div>
        <div class="mini-stat">
          <span>正确率</span>
          <strong>{{ percent(overview?.correct_rate ?? 0) }}</strong>
        </div>
      </section>
    </aside>

    <section class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">Phase 1</p>
          <h2>{{ viewTitle }}</h2>
        </div>
        <button class="icon-button" title="刷新数据" @click="refreshCurrent">
          <RefreshCw :size="18" />
        </button>
      </header>

      <section v-if="error" class="notice error">
        {{ error }}
      </section>

      <section v-if="activeView === 'practice'" class="practice-layout">
        <div class="chapter-list">
          <button
            class="chapter-row final-row"
            :class="{ selected: practiceMode === 'final_review' }"
            @click="selectFinalReview"
          >
            <div>
              <strong>总复习</strong>
              <span>跨章节随机抽题</span>
            </div>
            <Shuffle :size="18" />
          </button>

          <button
            v-for="chapter in chapters"
            :key="chapter.id"
            class="chapter-row"
            :class="{ selected: selectedChapterId === chapter.id && practiceMode === 'chapter' }"
            @click="selectChapter(chapter.id)"
          >
            <div>
              <strong>第 {{ chapter.order_index }} 章：{{ chapter.title }}</strong>
              <span>{{ chapter.question_count }} 道已审核题</span>
            </div>
            <ChevronRight :size="18" />
          </button>
        </div>

        <div class="practice-panel">
          <div class="controls">
            <label>
              <span>题量</span>
              <input v-model.number="questionCount" type="number" min="1" max="30" />
            </label>
            <label>
              <span>题型</span>
              <select v-model="selectedQuestionType">
                <option value="">混合练习</option>
                <option value="single_choice">单选题</option>
                <option value="multiple_choice">多选题</option>
                <option value="true_false">判断题</option>
                <option value="fill_blank">填空题</option>
                <option value="short_answer">简答题</option>
              </select>
            </label>
            <button class="primary-button" :disabled="loading" @click="startPractice">
              <Play :size="18" />
              <span>开始</span>
            </button>
          </div>

          <div v-if="session" class="question-stack">
            <div class="session-head">
              <span>练习 #{{ session.id }}</span>
              <strong v-if="result">得分 {{ result.score.toFixed(1) }} / {{ result.total }}</strong>
            </div>
            <div class="review-strip">
              <button
                v-for="(question, index) in session.questions"
                :key="question.id"
                class="review-dot"
                :class="reviewDotClass(question.id)"
                :title="`第 ${index + 1} 题`"
                @click="jumpToQuestion(question.id)"
              >
                {{ index + 1 }}
              </button>
            </div>

            <article
              v-for="(question, index) in session.questions"
              :id="`question-${question.id}`"
              :key="question.id"
              class="question-card"
              :class="{ missing: unansweredQuestionIds.has(question.id) }"
            >
              <div class="question-meta">
                <span>{{ index + 1 }}</span>
                <small>{{ typeLabel(question.type) }} · {{ difficultyLabel(question.difficulty) }}</small>
              </div>
              <p class="stem">{{ question.stem }}</p>

              <div v-if="question.type === 'single_choice'" class="options">
                <label v-for="option in question.options" :key="option.key" class="option-line">
                  <input v-model="answers[question.id]" type="radio" :name="`q-${question.id}`" :value="option.key" />
                  <span>{{ option.key }}. {{ option.text }}</span>
                </label>
              </div>

              <div v-else-if="question.type === 'multiple_choice'" class="options">
                <label v-for="option in question.options" :key="option.key" class="option-line">
                  <input
                    type="checkbox"
                    :checked="multiAnswer(question.id).includes(option.key)"
                    @change="toggleMulti(question.id, option.key)"
                  />
                  <span>{{ option.key }}. {{ option.text }}</span>
                </label>
              </div>

              <div v-else-if="question.type === 'true_false'" class="segmented">
                <button :class="{ selected: answers[question.id] === 'TRUE' }" @click="answers[question.id] = 'TRUE'">
                  对
                </button>
                <button :class="{ selected: answers[question.id] === 'FALSE' }" @click="answers[question.id] = 'FALSE'">
                  错
                </button>
              </div>

              <div v-else-if="question.type === 'fill_blank' || question.type === 'cloze'" class="blank-grid">
                <input
                  v-for="blankIndex in blankCount(question)"
                  :key="blankIndex"
                  :value="blankAnswer(question.id, blankIndex - 1)"
                  class="text-answer"
                  :placeholder="`第 ${blankIndex} 空`"
                  @input="setBlankAnswer(question.id, blankIndex - 1, ($event.target as HTMLInputElement).value)"
                />
              </div>

              <textarea
                v-else
                v-model="answers[question.id]"
                class="long-answer"
                placeholder="输入你的答案"
              />

              <div v-if="resultByQuestion[question.id]" class="answer-feedback">
                <strong :class="resultByQuestion[question.id].is_correct ? 'ok' : 'bad'">
                  {{ resultByQuestion[question.id].is_correct ? "正确" : "需要复盘" }}
                </strong>
                <span>{{ resultByQuestion[question.id].feedback }}</span>
                <p>参考答案：{{ formatAnswer(resultByQuestion[question.id].correct_answer) }}</p>
                <p v-if="resultByQuestion[question.id].explanation">{{ resultByQuestion[question.id].explanation }}</p>
              </div>
            </article>

            <button class="submit-button" :disabled="loading || Boolean(result)" @click="submitPractice">
              <CheckCircle2 :size="18" />
              <span>提交并批改</span>
            </button>
          </div>

          <div v-else class="empty-state">
            <GraduationCap :size="38" />
            <p>选择章节或总复习后开始练习。</p>
          </div>
        </div>
      </section>

      <section v-else-if="activeView === 'wrong'" class="data-grid">
        <div v-if="wrongQuestions.length" class="wrong-toolbar">
          <div>
            <strong>{{ wrongQuestions.length }} 道待复习错题</strong>
            <span>重新练习会从当前错题本抽题。</span>
          </div>
          <button class="primary-button" :disabled="loading" @click="startWrongPractice">
            <RotateCcw :size="18" />
            <span>重练错题</span>
          </button>
        </div>
        <article v-for="item in wrongQuestions" :key="item.id" class="question-card">
          <div class="question-meta">
            <span>{{ item.wrong_count }}</span>
            <small>{{ typeLabel(item.question.type) }}</small>
          </div>
          <p class="stem">{{ item.question.stem }}</p>
          <p class="muted">参考答案：{{ formatAnswer(item.question.answer) }}</p>
          <button class="secondary-button" @click="markMastered(item.question.id)">
            <Check :size="16" />
            <span>标记已掌握</span>
          </button>
        </article>
        <div v-if="!wrongQuestions.length" class="empty-state">
          <CheckCircle2 :size="38" />
          <p>当前没有待复习错题。</p>
        </div>
      </section>

      <section v-else-if="activeView === 'admin'" class="admin-layout">
        <div class="admin-list-panel">
          <div class="admin-filters">
            <label>
              <span>章节</span>
              <select v-model.number="adminChapterId">
                <option :value="0">全部章节</option>
                <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">
                  第 {{ chapter.order_index }} 章：{{ chapter.title }}
                </option>
              </select>
            </label>
            <label>
              <span>题型</span>
              <select v-model="adminQuestionType">
                <option value="">全部题型</option>
                <option value="single_choice">单选题</option>
                <option value="multiple_choice">多选题</option>
                <option value="true_false">判断题</option>
                <option value="fill_blank">填空题</option>
                <option value="short_answer">简答题</option>
                <option value="calculation">计算题</option>
              </select>
            </label>
            <label>
              <span>状态</span>
              <select v-model="adminReviewed">
                <option value="">全部</option>
                <option value="true">已审核</option>
                <option value="false">待审核</option>
              </select>
            </label>
            <label>
              <span>关键词</span>
              <input v-model="adminKeyword" placeholder="题干搜索" @keyup.enter="loadAdminQuestions" />
            </label>
            <button class="primary-button" :disabled="loading" @click="loadAdminQuestions">
              <Search :size="18" />
              <span>筛选</span>
            </button>
          </div>

          <div class="admin-total">共 {{ adminTotal }} 题</div>
          <div class="admin-question-list">
            <button
              v-for="question in adminQuestions"
              :key="question.id"
              class="admin-question-row"
              :class="{ selected: editingQuestion?.id === question.id }"
              @click="selectAdminQuestion(question)"
            >
              <span>{{ typeLabel(question.type) }}</span>
              <strong>{{ question.stem }}</strong>
              <small>{{ question.is_reviewed ? "已审核" : "待审核" }} · {{ sourceChapterName(question.chapter_id) }}</small>
            </button>
          </div>
        </div>

        <div class="admin-editor-panel">
          <div v-if="editingQuestion" class="editor-form">
            <div class="editor-head">
              <div>
                <p class="eyebrow">Question #{{ editingQuestion.id }}</p>
                <h3>{{ typeLabel(editingQuestion.type) }}维护</h3>
              </div>
              <label class="toggle-line">
                <input v-model="editForm.is_reviewed" type="checkbox" />
                <span>学生可见</span>
              </label>
            </div>

            <div class="editor-grid">
              <label>
                <span>章节</span>
                <select v-model.number="editForm.chapter_id">
                  <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">
                    第 {{ chapter.order_index }} 章：{{ chapter.title }}
                  </option>
                </select>
              </label>
              <label>
                <span>题型</span>
                <select v-model="editForm.type">
                  <option value="single_choice">单选题</option>
                  <option value="multiple_choice">多选题</option>
                  <option value="true_false">判断题</option>
                  <option value="fill_blank">填空题</option>
                  <option value="short_answer">简答题</option>
                  <option value="calculation">计算题</option>
                </select>
              </label>
              <label>
                <span>难度</span>
                <select v-model="editForm.difficulty">
                  <option value="easy">基础</option>
                  <option value="medium">中等</option>
                  <option value="hard">提高</option>
                </select>
              </label>
            </div>

            <label>
              <span>题干</span>
              <textarea v-model="editForm.stem" class="editor-textarea tall" />
            </label>
            <label>
              <span>选项 JSON</span>
              <textarea v-model="editForm.optionsJson" class="editor-textarea" />
            </label>
            <label>
              <span>答案 JSON</span>
              <textarea v-model="editForm.answerJson" class="editor-textarea" />
            </label>
            <label>
              <span>评分点 JSON</span>
              <textarea v-model="editForm.rubricJson" class="editor-textarea compact" />
            </label>
            <label>
              <span>解析</span>
              <textarea v-model="editForm.explanation" class="editor-textarea" />
            </label>

            <div class="editor-actions">
              <button class="submit-button" :disabled="loading" @click="saveAdminQuestion">
                <Save :size="18" />
                <span>保存题目</span>
              </button>
              <span v-if="adminMessage" class="save-message">{{ adminMessage }}</span>
            </div>
          </div>

          <div v-else class="empty-state">
            <ClipboardList :size="38" />
            <p>选择一道题开始维护。</p>
          </div>
        </div>
      </section>

      <section v-else-if="activeView === 'knowledge'" class="knowledge-layout">
        <div class="knowledge-panel">
          <div class="admin-filters">
            <label>
              <span>章节</span>
              <select v-model.number="knowledgeChapterId" @change="loadKnowledge">
                <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">
                  第 {{ chapter.order_index }} 章：{{ chapter.title }}
                </option>
              </select>
            </label>
            <label>
              <span>检索</span>
              <input v-model="knowledgeQuery" placeholder="例如 Cache、CPI、寻址方式" @keyup.enter="searchKnowledge" />
            </label>
            <button class="primary-button" :disabled="loading" @click="searchKnowledge">
              <Search :size="18" />
              <span>搜索知识块</span>
            </button>
          </div>

          <div class="knowledge-summary">
            <strong>{{ knowledgePoints.length }}</strong>
            <span>个知识点</span>
            <strong>{{ knowledgeChunks.length }}</strong>
            <span>个知识块</span>
          </div>

          <div class="knowledge-point-list">
            <article v-for="point in knowledgePoints" :key="point.id" class="knowledge-point">
              <strong>{{ point.name }}</strong>
              <p>{{ point.summary }}</p>
            </article>
          </div>
        </div>

        <div class="knowledge-panel">
          <div class="section-title">
            <p class="eyebrow">{{ knowledgeQuery ? "Search Results" : "Chapter Context" }}</p>
            <h3>{{ knowledgeQuery ? `“${knowledgeQuery}”` : "章节知识块" }}</h3>
          </div>
          <article v-for="chunk in activeKnowledgeChunks" :key="chunk.id" class="knowledge-chunk">
            <div class="chunk-meta">
              <span>{{ chunk.chunk_id }}</span>
              <small>{{ chunk.source_file }}</small>
            </div>
            <strong>{{ chunk.title }}</strong>
            <p>{{ chunk.content }}</p>
          </article>
          <div v-if="!activeKnowledgeChunks.length" class="empty-state">
            <FileText :size="38" />
            <p>当前没有匹配的知识块。</p>
          </div>
        </div>
      </section>

      <section v-else class="stats-grid">
        <article class="stat-card">
          <span>作答题数</span>
          <strong>{{ overview?.total_answers ?? 0 }}</strong>
        </article>
        <article class="stat-card">
          <span>正确率</span>
          <strong>{{ percent(overview?.correct_rate ?? 0) }}</strong>
        </article>
        <article class="stat-card">
          <span>未掌握错题</span>
          <strong>{{ overview?.wrong_question_count ?? 0 }}</strong>
        </article>

        <div class="chapter-stats">
          <div v-for="row in chapterStats" :key="row.chapter_id" class="progress-row">
            <span>{{ row.chapter_title }}</span>
            <div class="progress-track">
              <div :style="{ width: percent(row.correct_rate) }" class="progress-fill"></div>
            </div>
            <strong>{{ percent(row.correct_rate) }}</strong>
          </div>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  BarChart3,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  FileText,
  GraduationCap,
  Play,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Shuffle,
} from "@lucide/vue";
import { api, type AnswerResult, type Chapter, type ChapterStatistics, type KnowledgeChunk, type KnowledgePoint, type PracticeResult, type PracticeSession, type Question, type QuestionAdmin, type QuestionType, type StatisticsOverview, type WrongQuestion } from "./api/client";

const chapters = ref<Chapter[]>([]);
const session = ref<PracticeSession | null>(null);
const result = ref<PracticeResult | null>(null);
const overview = ref<StatisticsOverview | null>(null);
const chapterStats = ref<ChapterStatistics[]>([]);
const wrongQuestions = ref<WrongQuestion[]>([]);
const adminQuestions = ref<QuestionAdmin[]>([]);
const knowledgePoints = ref<KnowledgePoint[]>([]);
const knowledgeChunks = ref<KnowledgeChunk[]>([]);
const knowledgeSearchResults = ref<KnowledgeChunk[]>([]);
const adminTotal = ref(0);
const editingQuestion = ref<QuestionAdmin | null>(null);
const activeView = ref<"practice" | "wrong" | "stats" | "admin" | "knowledge">("practice");
const practiceMode = ref<"chapter" | "final_review" | "wrong_questions">("chapter");
const selectedChapterId = ref<number | null>(1);
const selectedQuestionType = ref<QuestionType | "">("");
const adminChapterId = ref(0);
const adminQuestionType = ref<QuestionType | "">("");
const adminReviewed = ref<"" | "true" | "false">("");
const adminKeyword = ref("");
const knowledgeChapterId = ref(1);
const knowledgeQuery = ref("");
const adminMessage = ref("");
const questionCount = ref(5);
const loading = ref(false);
const error = ref("");
const answers = reactive<Record<number, string | string[]>>({});
const unansweredQuestionIds = ref<Set<number>>(new Set());
const editForm = reactive({
  chapter_id: 1,
  type: "single_choice" as QuestionType,
  difficulty: "medium" as "easy" | "medium" | "hard",
  stem: "",
  optionsJson: "[]",
  answerJson: "{}",
  rubricJson: "[]",
  explanation: "",
  is_reviewed: true,
});

const viewTitle = computed(() => {
  if (activeView.value === "wrong") return "错题本";
  if (activeView.value === "stats") return "学习统计";
  if (activeView.value === "admin") return "题库维护";
  if (activeView.value === "knowledge") return "课程知识库";
  if (practiceMode.value === "wrong_questions") return "错题重练";
  if (practiceMode.value === "final_review") return "总复习练习";
  const chapter = chapters.value.find((item) => item.id === selectedChapterId.value);
  return chapter ? `第 ${chapter.order_index} 章：${chapter.title}` : "章节练习";
});

const resultByQuestion = computed<Record<number, AnswerResult>>(() => {
  const rows: Record<number, AnswerResult> = {};
  for (const item of result.value?.results ?? []) rows[item.question_id] = item;
  return rows;
});

const activeKnowledgeChunks = computed(() => (knowledgeQuery.value ? knowledgeSearchResults.value : knowledgeChunks.value));

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function typeLabel(type: string) {
  const labels: Record<string, string> = {
    single_choice: "单选",
    multiple_choice: "多选",
    true_false: "判断",
    fill_blank: "填空",
    short_answer: "简答",
  };
  return labels[type] ?? type;
}

function difficultyLabel(value: string) {
  return { easy: "基础", medium: "中等", hard: "提高" }[value] ?? value;
}

function sourceChapterName(chapterId: number) {
  const chapter = chapters.value.find((item) => item.id === chapterId);
  return chapter ? `第 ${chapter.order_index} 章` : `章节 ${chapterId}`;
}

function selectChapter(chapterId: number) {
  selectedChapterId.value = chapterId;
  practiceMode.value = "chapter";
  session.value = null;
  result.value = null;
}

function selectFinalReview() {
  practiceMode.value = "final_review";
  selectedChapterId.value = null;
  session.value = null;
  result.value = null;
}

function multiAnswer(questionId: number) {
  return Array.isArray(answers[questionId]) ? (answers[questionId] as string[]) : [];
}

function toggleMulti(questionId: number, key: string) {
  const current = new Set(multiAnswer(questionId));
  if (current.has(key)) current.delete(key);
  else current.add(key);
  answers[questionId] = Array.from(current).sort();
}

function blankCount(question: Question) {
  return Math.max(question.blank_count || 1, 1);
}

function blankAnswer(questionId: number, index: number) {
  const value = answers[questionId];
  return Array.isArray(value) ? value[index] ?? "" : "";
}

function setBlankAnswer(questionId: number, index: number, value: string) {
  const current = Array.isArray(answers[questionId]) ? [...(answers[questionId] as string[])] : [];
  current[index] = value;
  answers[questionId] = current;
}

function isAnswered(question: Question) {
  const answer = answers[question.id];
  if (question.type === "multiple_choice") return Array.isArray(answer) && answer.length > 0;
  if (question.type === "fill_blank" || question.type === "cloze") {
    if (!Array.isArray(answer)) return false;
    return answer.slice(0, blankCount(question)).every((item) => String(item ?? "").trim());
  }
  return String(answer ?? "").trim().length > 0;
}

function reviewDotClass(questionId: number) {
  const resultItem = resultByQuestion.value[questionId];
  return {
    answered: session.value?.questions.some((question) => question.id === questionId && isAnswered(question)),
    missing: unansweredQuestionIds.value.has(questionId),
    correct: Boolean(resultItem?.is_correct),
    wrong: Boolean(resultItem && !resultItem.is_correct),
  };
}

function jumpToQuestion(questionId: number) {
  document.getElementById(`question-${questionId}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function formatAnswer(value: unknown) {
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === "object" && item !== null && "answer" in item ? item.answer : item)).join("、");
  }
  if (typeof value === "object" && value !== null) return JSON.stringify(value);
  return String(value ?? "");
}

async function refreshAll() {
  error.value = "";
  const [chapterRows, overviewData] = await Promise.all([api.chapters(), api.overview()]);
  chapters.value = chapterRows;
  overview.value = overviewData;
  if (!selectedChapterId.value && chapterRows.length) selectedChapterId.value = chapterRows[0].id;
}

async function refreshCurrent() {
  if (activeView.value === "wrong") await openWrongQuestions();
  else if (activeView.value === "stats") await openStats();
  else if (activeView.value === "admin") await loadAdminQuestions();
  else if (activeView.value === "knowledge") await loadKnowledge();
  else await refreshAll();
}

async function startPractice() {
  loading.value = true;
  error.value = "";
  result.value = null;
  unansweredQuestionIds.value = new Set();
  Object.keys(answers).forEach((key) => delete answers[Number(key)]);
  try {
    session.value = await api.createPractice({
      mode: practiceMode.value,
      chapter_id: practiceMode.value === "chapter" ? selectedChapterId.value : null,
      question_count: questionCount.value,
      question_types: selectedQuestionType.value ? [selectedQuestionType.value] : undefined,
      user_id: "demo",
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : "创建练习失败";
  } finally {
    loading.value = false;
  }
}

async function submitPractice() {
  if (!session.value) return;
  const missing = session.value.questions.filter((question) => !isAnswered(question)).map((question) => question.id);
  if (missing.length) {
    unansweredQuestionIds.value = new Set(missing);
    error.value = `还有 ${missing.length} 道题未作答，请补全后再提交。`;
    jumpToQuestion(missing[0]);
    return;
  }
  loading.value = true;
  error.value = "";
  unansweredQuestionIds.value = new Set();
  try {
    const submitted = session.value.questions.map((question) => ({
      question_id: question.id,
      user_answer:
        question.type === "fill_blank" || question.type === "cloze"
          ? Array.isArray(answers[question.id])
            ? answers[question.id]
            : [answers[question.id] ?? ""]
          : answers[question.id] ?? "",
    }));
    result.value = await api.submitPractice(session.value.id, submitted);
    await refreshAll();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "提交失败";
  } finally {
    loading.value = false;
  }
}

async function openWrongQuestions() {
  activeView.value = "wrong";
  error.value = "";
  wrongQuestions.value = await api.wrongQuestions();
}

async function startWrongPractice() {
  loading.value = true;
  error.value = "";
  result.value = null;
  unansweredQuestionIds.value = new Set();
  Object.keys(answers).forEach((key) => delete answers[Number(key)]);
  try {
    const count = Math.min(Math.max(wrongQuestions.value.length, 1), questionCount.value || 10);
    session.value = await api.createPractice({
      mode: "wrong_questions",
      question_count: count,
      user_id: "demo",
    });
    practiceMode.value = "wrong_questions";
    selectedChapterId.value = session.value.chapter_id;
    activeView.value = "practice";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "创建错题练习失败";
  } finally {
    loading.value = false;
  }
}

async function markMastered(questionId: number) {
  await api.markMastered(questionId);
  await openWrongQuestions();
  await refreshAll();
}

async function openStats() {
  activeView.value = "stats";
  error.value = "";
  const [overviewData, stats] = await Promise.all([api.overview(), api.chapterStats()]);
  overview.value = overviewData;
  chapterStats.value = stats;
}

async function openAdmin() {
  activeView.value = "admin";
  await loadAdminQuestions();
}

async function openKnowledge() {
  activeView.value = "knowledge";
  if (!knowledgeChapterId.value) knowledgeChapterId.value = chapters.value[0]?.id ?? 1;
  await loadKnowledge();
}

async function loadKnowledge() {
  loading.value = true;
  error.value = "";
  try {
    const [points, chunks] = await Promise.all([
      api.knowledgePoints(knowledgeChapterId.value),
      api.knowledgeChunks(knowledgeChapterId.value, 50),
    ]);
    knowledgePoints.value = points;
    knowledgeChunks.value = chunks;
    if (!knowledgeQuery.value) knowledgeSearchResults.value = [];
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载知识库失败";
  } finally {
    loading.value = false;
  }
}

async function searchKnowledge() {
  if (!knowledgeQuery.value.trim()) {
    knowledgeSearchResults.value = [];
    await loadKnowledge();
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const result = await api.searchKnowledge({
      q: knowledgeQuery.value.trim(),
      chapter_id: knowledgeChapterId.value,
      limit: 12,
    });
    knowledgeSearchResults.value = result.items;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "检索知识库失败";
  } finally {
    loading.value = false;
  }
}

async function loadAdminQuestions() {
  loading.value = true;
  error.value = "";
  adminMessage.value = "";
  try {
    const data = await api.adminQuestions({
      chapter_id: adminChapterId.value || null,
      question_type: adminQuestionType.value,
      reviewed: adminReviewed.value === "" ? "" : adminReviewed.value === "true",
      keyword: adminKeyword.value,
      limit: 40,
      offset: 0,
    });
    adminQuestions.value = data.items;
    adminTotal.value = data.total;
    if (!editingQuestion.value && data.items.length) selectAdminQuestion(data.items[0]);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载题库失败";
  } finally {
    loading.value = false;
  }
}

function selectAdminQuestion(question: QuestionAdmin) {
  editingQuestion.value = question;
  editForm.chapter_id = question.chapter_id;
  editForm.type = question.type;
  editForm.difficulty = question.difficulty as "easy" | "medium" | "hard";
  editForm.stem = question.stem;
  editForm.optionsJson = JSON.stringify(question.options, null, 2);
  editForm.answerJson = JSON.stringify(question.answer_json, null, 2);
  editForm.rubricJson = JSON.stringify(question.rubric_json, null, 2);
  editForm.explanation = question.explanation ?? "";
  editForm.is_reviewed = question.is_reviewed;
  adminMessage.value = "";
}

function parseJsonField(value: string, fallback: unknown) {
  if (!value.trim()) return fallback;
  return JSON.parse(value);
}

async function saveAdminQuestion() {
  if (!editingQuestion.value) return;
  loading.value = true;
  error.value = "";
  adminMessage.value = "";
  try {
    const saved = await api.updateQuestion(editingQuestion.value.id, {
      chapter_id: editForm.chapter_id,
      type: editForm.type,
      difficulty: editForm.difficulty,
      stem: editForm.stem,
      options_json: parseJsonField(editForm.optionsJson, []),
      answer_json: parseJsonField(editForm.answerJson, {}),
      rubric_json: parseJsonField(editForm.rubricJson, []),
      explanation: editForm.explanation || null,
      is_reviewed: editForm.is_reviewed,
    });
    const index = adminQuestions.value.findIndex((item) => item.id === saved.id);
    if (index >= 0) adminQuestions.value[index] = saved;
    editingQuestion.value = saved;
    selectAdminQuestion(saved);
    adminMessage.value = "已保存";
    await refreshAll();
  } catch (err) {
    error.value = err instanceof SyntaxError ? "JSON 格式不正确" : err instanceof Error ? err.message : "保存失败";
  } finally {
    loading.value = false;
  }
}

onMounted(refreshAll);
</script>
