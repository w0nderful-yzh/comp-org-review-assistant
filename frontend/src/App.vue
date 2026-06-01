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
        <button class="icon-button" title="刷新数据" @click="refreshAll">
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

            <article v-for="(question, index) in session.questions" :key="question.id" class="question-card">
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
  GraduationCap,
  Play,
  RefreshCw,
  RotateCcw,
  Shuffle,
} from "@lucide/vue";
import { api, type AnswerResult, type Chapter, type ChapterStatistics, type PracticeResult, type PracticeSession, type Question, type QuestionType, type StatisticsOverview, type WrongQuestion } from "./api/client";

const chapters = ref<Chapter[]>([]);
const session = ref<PracticeSession | null>(null);
const result = ref<PracticeResult | null>(null);
const overview = ref<StatisticsOverview | null>(null);
const chapterStats = ref<ChapterStatistics[]>([]);
const wrongQuestions = ref<WrongQuestion[]>([]);
const activeView = ref<"practice" | "wrong" | "stats">("practice");
const practiceMode = ref<"chapter" | "final_review">("chapter");
const selectedChapterId = ref<number | null>(1);
const selectedQuestionType = ref<QuestionType | "">("");
const questionCount = ref(5);
const loading = ref(false);
const error = ref("");
const answers = reactive<Record<number, string | string[]>>({});

const viewTitle = computed(() => {
  if (activeView.value === "wrong") return "错题本";
  if (activeView.value === "stats") return "学习统计";
  if (practiceMode.value === "final_review") return "总复习练习";
  const chapter = chapters.value.find((item) => item.id === selectedChapterId.value);
  return chapter ? `第 ${chapter.order_index} 章：${chapter.title}` : "章节练习";
});

const resultByQuestion = computed<Record<number, AnswerResult>>(() => {
  const rows: Record<number, AnswerResult> = {};
  for (const item of result.value?.results ?? []) rows[item.question_id] = item;
  return rows;
});

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

async function startPractice() {
  loading.value = true;
  error.value = "";
  result.value = null;
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
  loading.value = true;
  error.value = "";
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

onMounted(refreshAll);
</script>
