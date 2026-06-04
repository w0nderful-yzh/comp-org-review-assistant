<template>
  <section class="exam-page">
    <!-- ===== YEAR SELECTION SCREEN ===== -->
    <template v-if="examState === 'selecting'">
      <div class="exam-select-header">
        <div>
          <p class="eyebrow">Real Exam</p>
          <h2>历年真题模拟</h2>
          <p class="exam-select-desc">选择年份进入模拟考试，系统自动计时并记录答题进度。</p>
        </div>
      </div>

      <section v-if="error" class="notice error">{{ error }}</section>

      <div class="year-card-grid">
        <button
          v-for="paper in papers"
          :key="paper.year"
          class="year-card"
          @click="enterExam(paper.year)"
        >
          <div class="year-card-head">
            <span class="year-badge">{{ paper.year }}</span>
            <span class="year-card-score">{{ paper.total_score }} 分</span>
          </div>
          <div class="year-card-body">
            <h3>{{ paper.title }}</h3>
            <div class="year-card-meta">
              <span>
                <Clock3 :size="14" />
                {{ paper.duration_minutes }} 分钟
              </span>
              <span>
                <FileText :size="14" />
                {{ paper.questions.length }} 题
              </span>
              <span v-if="paperHasImages(paper)" class="year-card-tag">
                含示意图
              </span>
            </div>
          </div>
          <div class="year-card-foot">
            <span class="year-card-enter">
              开始模拟
              <ChevronRight :size="16" />
            </span>
          </div>
        </button>
      </div>
    </template>

    <!-- ===== EXAM WORKSPACE ===== -->
    <template v-else>
      <header class="exam-toolbar">
        <div class="toolbar-left">
          <button class="back-button" title="返回年份选择" @click="exitToSelect">
            <ArrowLeft :size="18" />
          </button>
          <div class="year-tabs" aria-label="选择真题年份">
            <button
              v-for="paper in papers"
              :key="paper.year"
              :class="{ selected: paper.year === selectedYear }"
              @click="selectPaper(paper.year)"
            >
              {{ paper.year }}
            </button>
          </div>
        </div>
        <div class="toolbar-actions">
          <button class="secondary-button" :disabled="!activePaper" @click="openPaperPdf">
            <FileText :size="16" />
            <span>原卷备用</span>
          </button>
          <button class="secondary-button" :disabled="!activePaper" @click="downloadCurrentPaper">
            <Download :size="16" />
            <span>下载试卷</span>
          </button>
        </div>
      </header>

      <section v-if="error" class="notice error">{{ error }}</section>

      <div class="exam-workspace">
        <main class="question-column">
          <section class="paper-intro">
            <div>
              <p class="eyebrow">Real Exam</p>
              <h3>{{ activePaper?.title ?? "真题模拟" }}</h3>
              <span v-if="activePaper">{{ activePaper.duration_minutes }} 分钟 · {{ activePaper.total_score }} 分</span>
            </div>
            <div class="timer-chip" :class="{ hot: remainingSeconds <= 600 && running }">
              <Clock3 :size="18" />
              <strong>{{ timerText }}</strong>
            </div>
          </section>

          <section v-if="!hasStructuredQuestions" class="pdf-fallback">
            <div>
              <p class="eyebrow">Pending</p>
              <h3>{{ activePaper?.year }} 年真题还没有结构化</h3>
              <p>这份卷子还只有 PDF 资源。当前优先把 2023 卷拆成了逐题模式，其他年份可以继续按同样方式补录。</p>
            </div>
            <button class="primary-button" @click="openPaperPdf">
              <FileText :size="18" />
              <span>打开原卷 PDF</span>
            </button>
          </section>

          <template v-else>
            <section
              v-for="section in activeSections"
              :id="`section-${section.id}`"
              :key="section.id"
              class="section-band"
            >
              <div class="section-heading">
                <div>
                  <p class="eyebrow">Section</p>
                  <h3>{{ section.title }}</h3>
                </div>
                <b>{{ section.score }} 分</b>
              </div>

              <article
                v-for="(question, questionIndex) in questionsBySection(section.id)"
                :id="`exam-question-${question.id}`"
                :key="question.id"
                class="exam-question-card"
              >
                <div class="question-head">
                  <span>{{ questionIndex + 1 }}</span>
                  <div>
                    <h4>{{ question.title }}</h4>
                    <small>{{ question.number }} · {{ question.score }} 分</small>
                  </div>
                </div>
                <p class="question-stem">{{ question.stem }}</p>

                <div v-if="question.source_images?.length" class="question-images">
                  <figure v-for="img in question.source_images" :key="img.filename" class="source-figure" @click="openImageZoom(img.url, img.label)" style="cursor:zoom-in">
                    <img :src="img.url" :alt="img.label" loading="lazy" />
                    <figcaption>{{ img.label }}</figcaption>
                  </figure>
                  <p class="image-res-hint">
                    <Info :size="13" />
                    示意图为网页版，点击可放大。如需更清晰原图，请使用右上角
                    <strong>原卷备用</strong> 或 <strong>下载试卷</strong>。
                  </p>
                </div>

                <div class="sub-question-list">
                  <section v-for="sub in question.sub_questions" :key="sub.id" class="sub-question">
                    <div class="sub-prompt">
                      <strong>{{ sub.label }}</strong>
                      <p>{{ sub.prompt }}</p>
                      <span v-if="sub.score !== null">{{ sub.score }} 分</span>
                    </div>

                    <div v-if="sub.answer_type === 'single_choice'" class="choice-grid">
                      <button
                        v-for="option in sub.options"
                        :key="option.key"
                        :disabled="submitted"
                        :class="{ selected: answers[sub.id] === option.key }"
                        @click="setAnswer(sub.id, option.key)"
                      >
                        <b>{{ option.key }}</b>
                        <span>{{ option.text }}</span>
                      </button>
                    </div>

                    <textarea
                      v-else
                      v-model="answers[sub.id]"
                      :disabled="submitted"
                      class="inline-answer"
                      placeholder="在这里作答"
                      @input="saveDraft"
                    />
                  </section>
                </div>
              </article>
            </section>
          </template>
        </main>

        <aside class="exam-side">
          <section class="exam-panel session-panel">
            <p class="eyebrow">Session</p>
            <h3>{{ statusTitle }}</h3>
            <span>{{ answeredCount }} / {{ totalAnswerSlots }} 小题已填写</span>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: progressPercent }"></div>
            </div>
            <div class="side-actions">
              <button v-if="!running && !submitted" class="primary-button" :disabled="!activePaper" @click="startExam">
                <Play :size="17" />
                <span>{{ paused ? "继续" : "开始模拟" }}</span>
              </button>
              <button v-if="running" class="secondary-button" @click="pauseExam">
                <Pause :size="17" />
                <span>暂停</span>
              </button>
              <button class="secondary-button" :disabled="!activePaper" @click="resetExam">
                <RotateCcw :size="17" />
                <span>重置</span>
              </button>
            </div>
          </section>

          <section v-if="hasStructuredQuestions" class="exam-panel mini-map">
            <p class="eyebrow">Jump</p>
            <button
              v-for="section in activeSections"
              :key="section.id"
              @click="jumpToSection(section.id)"
            >
              <span>{{ section.title }}</span>
              <b>{{ sectionAnswered(section.id) }}/{{ sectionTotal(section.id) }}</b>
            </button>
          </section>

          <section class="exam-panel submit-panel">
            <button v-if="!submitted" class="submit-button wide" :disabled="!activePaper || !hasStarted" @click="submitExam">
              <CheckCircle2 :size="18" />
              <span>交卷并查看答案</span>
            </button>
            <template v-else>
              <div class="score-box">
                <label>
                  <span>自评分</span>
                  <input v-model.number="selfScore" type="number" min="0" :max="activePaper?.total_score ?? 100" @change="saveHistory" />
                </label>
                <b>{{ selfScore || 0 }} / {{ activePaper?.total_score ?? 100 }}</b>
              </div>
              <button class="primary-button wide" :disabled="answerLoading" @click="openAnswer">
                <FileSearch :size="18" />
                <span>{{ answerUrl ? "刷新答案" : "查看答案 PDF" }}</span>
              </button>
            </template>
          </section>

          <section v-if="answerUrl" class="exam-panel answer-panel">
            <iframe class="answer-pdf-frame" :src="answerUrl" title="真题答案 PDF"></iframe>
          </section>
        </aside>
      </div>
    </template>

    <!-- ===== PDF MODAL ===== -->
    <div v-if="paperUrl" class="pdf-modal" role="dialog" aria-modal="true">
      <div class="pdf-modal-head">
        <strong>{{ activePaper?.paper_pdf }}</strong>
        <button class="icon-button small" title="关闭" @click="closePaperPdf">
          <X :size="18" />
        </button>
      </div>
      <iframe class="paper-pdf-frame" :src="paperUrl" title="真题原卷 PDF"></iframe>
    </div>

    <!-- ===== IMAGE LIGHTBOX ===== -->
    <Teleport to="body">
      <div v-if="zoomImage" class="image-lightbox" @click.self="zoomImage = null" @keydown.escape="zoomImage = null">
        <button class="lightbox-close" @click="zoomImage = null">
          <X :size="24" />
        </button>
        <img :src="zoomImage.url" :alt="zoomImage.label" />
        <p class="lightbox-caption">{{ zoomImage.label }}</p>
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Download,
  FileSearch,
  FileText,
  Info,
  Pause,
  Play,
  RotateCcw,
  X,
} from "@lucide/vue";
import { api, type ExamPaper, type ExamQuestion } from "../api/client";

type ExamHistoryItem = {
  year: number;
  score: number;
  submitted_at: string;
  answered_count: number;
};

const papers = ref<ExamPaper[]>([]);
const selectedYear = ref<number | null>(null);
const examState = ref<"selecting" | "active">("selecting");
const paperUrl = ref("");
const answerUrl = ref("");
const answerLoading = ref(false);
const error = ref("");
const running = ref(false);
const paused = ref(false);
const submitted = ref(false);
const hasStarted = ref(false);
const remainingSeconds = ref(0);
const selfScore = ref<number | null>(null);
const answers = reactive<Record<string, string>>({});
const zoomImage = ref<{ url: string; label: string } | null>(null);
let timer: ReturnType<typeof setInterval> | null = null;

const activePaper = computed(() => papers.value.find((paper) => paper.year === selectedYear.value) ?? null);
const hasStructuredQuestions = computed(() => Boolean(activePaper.value?.questions.length));
const activeSections = computed(() => {
  const paper = activePaper.value;
  if (!paper) return [];
  const used = new Set(paper.questions.map((question) => question.section_id));
  return paper.sections.filter((section) => used.has(section.id));
});
const activeQuestions = computed(() => activePaper.value?.questions ?? []);
const totalAnswerSlots = computed(() => activeQuestions.value.reduce((sum, question) => sum + question.sub_questions.length, 0));
const answeredCount = computed(() => activeQuestions.value.reduce((sum, question) => {
  return sum + question.sub_questions.filter((sub) => String(answers[sub.id] ?? "").trim().length > 0).length;
}, 0));
const progressPercent = computed(() => totalAnswerSlots.value ? `${Math.round(answeredCount.value / totalAnswerSlots.value * 100)}%` : "0%");

const timerText = computed(() => {
  const seconds = Math.max(remainingSeconds.value, 0);
  const mm = Math.floor(seconds / 60);
  const ss = seconds % 60;
  return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
});

const statusTitle = computed(() => {
  if (submitted.value) return "已交卷";
  if (running.value) return "模拟中";
  if (paused.value) return "已暂停";
  return "待开始";
});

function paperHasImages(paper: ExamPaper): boolean {
  return paper.questions.some((q) => q.source_images?.length > 0);
}

function clearObjectUrl(url: string) {
  if (url.startsWith("blob:")) URL.revokeObjectURL(url);
}

function clearTimer() {
  if (timer) clearInterval(timer);
  timer = null;
}

function tick() {
  if (remainingSeconds.value <= 1) {
    remainingSeconds.value = 0;
    submitExam();
    return;
  }
  remainingSeconds.value -= 1;
}

function storageKey(year = selectedYear.value) {
  return year ? `comp-org-exam-draft-${year}` : "";
}

function questionsBySection(sectionId: string): ExamQuestion[] {
  return activeQuestions.value.filter((question) => question.section_id === sectionId);
}

function sectionTotal(sectionId: string) {
  return questionsBySection(sectionId).reduce((sum, question) => sum + question.sub_questions.length, 0);
}

function sectionAnswered(sectionId: string) {
  return questionsBySection(sectionId).reduce((sum, question) => {
    return sum + question.sub_questions.filter((sub) => String(answers[sub.id] ?? "").trim().length > 0).length;
  }, 0);
}

function setAnswer(subId: string, value: string) {
  if (submitted.value) return;
  answers[subId] = value;
  saveDraft();
}

function restoreDraft() {
  Object.keys(answers).forEach((key) => delete answers[key]);
  const key = storageKey();
  if (!key) return;
  const raw = localStorage.getItem(key);
  if (!raw) return;
  try {
    Object.assign(answers, JSON.parse(raw) as Record<string, string>);
  } catch {
    localStorage.removeItem(key);
  }
}

function saveDraft() {
  const key = storageKey();
  if (key) localStorage.setItem(key, JSON.stringify(answers));
}

function enterExam(year: number) {
  selectedYear.value = year;
  examState.value = "active";
  resetExamState(false);
  restoreDraft();
  closePaperPdf();
}

function exitToSelect() {
  clearTimer();
  examState.value = "selecting";
  selectedYear.value = null;
  closePaperPdf();
  clearObjectUrl(answerUrl.value);
  answerUrl.value = "";
}

async function selectPaper(year: number) {
  selectedYear.value = year;
  resetExamState(false);
  restoreDraft();
  closePaperPdf();
}

function resetExamState(clearAnswers: boolean) {
  clearTimer();
  clearObjectUrl(answerUrl.value);
  answerUrl.value = "";
  running.value = false;
  paused.value = false;
  submitted.value = false;
  hasStarted.value = false;
  selfScore.value = null;
  remainingSeconds.value = (activePaper.value?.duration_minutes ?? 120) * 60;
  if (clearAnswers) {
    Object.keys(answers).forEach((key) => delete answers[key]);
    const key = storageKey();
    if (key) localStorage.removeItem(key);
  }
}

function startExam() {
  if (!activePaper.value) return;
  hasStarted.value = true;
  running.value = true;
  paused.value = false;
  submitted.value = false;
  if (!remainingSeconds.value) remainingSeconds.value = activePaper.value.duration_minutes * 60;
  clearTimer();
  timer = setInterval(tick, 1000);
}

function pauseExam() {
  running.value = false;
  paused.value = true;
  clearTimer();
}

function resetExam() {
  resetExamState(true);
}

function submitExam() {
  if (!activePaper.value || submitted.value) return;
  saveDraft();
  clearTimer();
  running.value = false;
  paused.value = false;
  submitted.value = true;
  hasStarted.value = true;
  saveHistory();
}

function historyItems(): ExamHistoryItem[] {
  const raw = localStorage.getItem("comp-org-exam-history");
  if (!raw) return [];
  try {
    return JSON.parse(raw) as ExamHistoryItem[];
  } catch {
    return [];
  }
}

function saveHistory() {
  if (!activePaper.value || !submitted.value) return;
  const next: ExamHistoryItem = {
    year: activePaper.value.year,
    score: Number(selfScore.value ?? 0),
    submitted_at: new Date().toISOString(),
    answered_count: answeredCount.value,
  };
  const rows = [next, ...historyItems().filter((item) => item.year !== next.year)].slice(0, 20);
  localStorage.setItem("comp-org-exam-history", JSON.stringify(rows));
}

async function openAnswer() {
  if (!activePaper.value) return;
  answerLoading.value = true;
  clearObjectUrl(answerUrl.value);
  answerUrl.value = "";
  try {
    const blob = await api.examPaperPdf(activePaper.value.year, "answer");
    answerUrl.value = URL.createObjectURL(blob);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载答案 PDF 失败";
  } finally {
    answerLoading.value = false;
  }
}

async function openPaperPdf() {
  if (!activePaper.value) return;
  clearObjectUrl(paperUrl.value);
  paperUrl.value = "";
  const blob = await api.examPaperPdf(activePaper.value.year, "paper");
  paperUrl.value = URL.createObjectURL(blob);
}

function closePaperPdf() {
  clearObjectUrl(paperUrl.value);
  paperUrl.value = "";
}

async function downloadCurrentPaper() {
  if (!activePaper.value) return;
  const blob = await api.examPaperPdf(activePaper.value.year, "paper", true);
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = activePaper.value.paper_pdf;
  link.click();
  URL.revokeObjectURL(url);
}

function jumpToSection(sectionId: string) {
  document.getElementById(`section-${sectionId}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function openImageZoom(url: string, label: string) {
  zoomImage.value = { url, label };
}

async function load() {
  error.value = "";
  try {
    papers.value = await api.examPapers();
    if (examState.value === "active" && selectedYear.value) {
      restoreDraft();
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载真题列表失败";
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && zoomImage.value) {
    zoomImage.value = null;
  }
}

defineExpose({ load });

onMounted(() => {
  load();
  document.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  clearTimer();
  clearObjectUrl(paperUrl.value);
  clearObjectUrl(answerUrl.value);
  document.removeEventListener("keydown", handleKeydown);
});

watch(activePaper, (paper) => {
  remainingSeconds.value = (paper?.duration_minutes ?? 120) * 60;
});
</script>

<style scoped>
.exam-page {
  min-width: 0;
}

/* ===== YEAR SELECTION ===== */

.exam-select-header {
  margin-bottom: 8px;
}

.exam-select-header h2 {
  margin: 4px 0 0;
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  font-size: 28px;
  line-height: 1.2;
}

.exam-select-desc {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 14px;
}

.year-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

.year-card {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--rule);
  border-radius: 10px;
  background: var(--panel);
  text-align: left;
  box-shadow: 0 6px 18px rgb(36 48 47 / 5%);
  transition: all 0.18s ease;
  overflow: hidden;
}

.year-card:hover {
  border-color: var(--teal);
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgb(36 48 47 / 10%);
}

.year-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px 0;
}

.year-badge {
  display: inline-grid;
  width: 52px;
  height: 34px;
  place-items: center;
  border-radius: 8px;
  background: var(--teal);
  color: #fff;
  font-size: 16px;
  font-weight: 900;
  letter-spacing: 0.5px;
}

.year-card-score {
  color: var(--muted);
  font-size: 13px;
  font-weight: 800;
}

.year-card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
}

.year-card-body h3 {
  margin: 0;
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  font-size: 17px;
  line-height: 1.3;
}

.year-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.year-card-meta span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.year-card-tag {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgb(45 124 111 / 10%);
  color: var(--teal) !important;
  font-size: 12px !important;
  font-weight: 900 !important;
}

.year-card-foot {
  border-top: 1px solid var(--rule);
  padding: 10px 16px;
}

.year-card-enter {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--teal);
  font-size: 14px;
  font-weight: 900;
}

.year-card:hover .year-card-enter {
  gap: 8px;
}

/* ===== TOOLBAR ===== */

.exam-toolbar {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 16px;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: rgb(255 253 248 / 92%);
  backdrop-filter: blur(12px);
}

.toolbar-left {
  display: flex;
  gap: 10px;
  align-items: center;
  min-width: 0;
}

.back-button {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid var(--rule);
  border-radius: 8px;
  color: var(--ink);
  background: #fffef9;
  flex-shrink: 0;
  transition: all 0.15s;
}

.back-button:hover {
  border-color: var(--teal);
  color: var(--teal);
}

.year-tabs,
.toolbar-actions,
.side-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.year-tabs button {
  min-width: 56px;
  min-height: 38px;
  border: 1px solid #cdd6ca;
  border-radius: 8px;
  color: var(--ink);
  background: #fffef9;
  font-weight: 900;
}

.year-tabs button.selected {
  color: #fff;
  border-color: var(--teal);
  background: var(--teal);
}

/* ===== EXAM WORKSPACE ===== */

.exam-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);
  gap: 18px;
  align-items: start;
}

.question-column {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.paper-intro {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 18px;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: rgb(255 253 248 / 92%);
}

.paper-intro h3,
.section-heading h3,
.exam-panel h3,
.pdf-fallback h3 {
  margin: 4px 0 0;
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  line-height: 1.2;
}

.paper-intro span,
.exam-panel span,
.pdf-fallback p {
  color: var(--muted);
}

.timer-chip {
  display: inline-flex;
  min-width: 128px;
  justify-content: center;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: 1px solid #cdd6ca;
  border-radius: 8px;
  background: #f3f7ed;
}

.timer-chip.hot {
  color: #a43730;
  border-color: #e3b3ad;
  background: #fff0ec;
}

.section-band {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: rgb(255 253 248 / 92%);
  scroll-margin-top: 92px;
}

.section-heading,
.question-head,
.sub-prompt {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.section-heading b {
  color: var(--teal);
  white-space: nowrap;
}

.exam-question-card {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: #fffef9;
}

.question-head {
  justify-content: flex-start;
}

.question-head > span {
  display: inline-grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 999px;
  color: #fff;
  background: var(--ink);
  font-size: 18px;
  font-weight: 900;
}

.question-head h4 {
  margin: 0;
  font-size: 18px;
  line-height: 1.35;
}

.question-head small {
  display: inline-block;
  margin-top: 4px;
  color: var(--teal);
  font-weight: 900;
}

.question-stem,
.sub-prompt p {
  margin: 0;
  line-height: 1.8;
  white-space: pre-wrap;
}

.question-stem {
  padding: 14px;
  border-left: 4px solid #efd174;
  background: #fff9e9;
}

.sub-question-list {
  display: grid;
  gap: 12px;
}

.sub-question {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid #dfe6da;
  border-radius: 8px;
  background: #fbfcf7;
}

.sub-prompt strong {
  color: var(--teal);
  white-space: nowrap;
}

.sub-prompt span {
  color: var(--muted);
  font-size: 13px;
  font-weight: 900;
  white-space: nowrap;
}

.inline-answer {
  width: 100%;
  min-height: 118px;
  resize: vertical;
  border: 1px solid #cdd6ca;
  border-radius: 8px;
  padding: 12px;
  color: var(--ink);
  background: #fffdf8;
  line-height: 1.6;
}

.choice-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px;
}

.choice-grid button {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-height: 46px;
  border: 1px solid #cdd6ca;
  border-radius: 8px;
  padding: 10px;
  color: var(--ink);
  text-align: left;
  background: #fffef9;
}

.choice-grid button.selected {
  border-color: var(--teal);
  box-shadow: inset 0 0 0 2px rgb(45 124 111 / 18%);
}

.choice-grid b {
  color: var(--teal);
}

/* ===== IMAGES ===== */

.question-images {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: start;
}

.source-figure {
  margin: 0;
  border: 1px solid #dfe6da;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  cursor: zoom-in;
  transition: box-shadow 0.15s ease;
}

.source-figure:hover {
  box-shadow: 0 4px 16px rgb(0 0 0 / 12%);
}

.source-figure img {
  display: block;
  max-width: 100%;
  max-height: 420px;
  object-fit: contain;
}

.source-figure figcaption {
  padding: 6px 10px;
  font-size: 12px;
  color: var(--muted);
  text-align: center;
  border-top: 1px solid #dfe6da;
  background: #f8faf5;
}

.image-res-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  margin: 0;
  padding: 8px 12px;
  border-radius: 6px;
  background: rgb(240 201 106 / 12%);
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}

.image-res-hint strong {
  color: var(--teal);
}

/* ===== BUTTONS ===== */

.primary-button,
.submit-button {
  color: #fff;
  -webkit-text-fill-color: #fff;
}

.primary-button span,
.primary-button svg,
.submit-button span,
.submit-button svg {
  color: #fff;
  -webkit-text-fill-color: #fff;
}

.primary-button:disabled,
.submit-button:disabled {
  color: #f7fbf8;
  -webkit-text-fill-color: #f7fbf8;
  background: #4f8c81;
}

.secondary-button,
.secondary-button span,
.secondary-button svg {
  color: #273533;
  -webkit-text-fill-color: #273533;
}

/* ===== SIDEBAR ===== */

.exam-side {
  position: sticky;
  top: 84px;
  display: grid;
  gap: 12px;
  min-width: 0;
}

.exam-panel {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: rgb(255 253 248 / 92%);
}

.progress-track {
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: #e1e7dc;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--teal);
  transition: width 0.2s ease;
}

.mini-map button {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  min-height: 38px;
  border: 1px solid #dfe6da;
  border-radius: 8px;
  padding: 8px 10px;
  color: var(--ink);
  background: #fffef9;
}

.mini-map b,
.score-box b {
  color: var(--teal);
  white-space: nowrap;
}

.wide {
  width: 100%;
}

.score-box {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: end;
}

.score-box span {
  display: block;
  margin-bottom: 5px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 900;
}

.score-box input {
  width: 100%;
  min-height: 38px;
  border: 1px solid #cdd6ca;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fffef9;
}

.answer-pdf-frame {
  width: 100%;
  height: 380px;
  border: 1px solid #dfe6da;
  border-radius: 8px;
  background: #fff;
}

/* ===== PDF FALLBACK ===== */

.pdf-fallback {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 18px;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: rgb(255 253 248 / 92%);
}

/* ===== PDF MODAL ===== */

.pdf-modal {
  position: fixed;
  inset: 32px;
  z-index: 20;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: #fffdf8;
  box-shadow: 0 24px 70px rgb(36 48 47 / 22%);
}

.pdf-modal-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--rule);
}

.paper-pdf-frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff;
}

/* ===== IMAGE LIGHTBOX ===== */

.image-lightbox {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: rgb(0 0 0 / 75%);
  backdrop-filter: blur(4px);
}

.image-lightbox img {
  max-width: 95vw;
  max-height: 85vh;
  object-fit: contain;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 12px 40px rgb(0 0 0 / 40%);
}

.lightbox-caption {
  color: #fff;
  font-size: 14px;
  text-align: center;
  margin: 0;
}

.lightbox-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 999px;
  color: #fff;
  background: rgb(255 255 255 / 20%);
  cursor: pointer;
  transition: background 0.15s ease;
}

.lightbox-close:hover {
  background: rgb(255 255 255 / 35%);
}

/* ===== RESPONSIVE ===== */

@media (max-width: 1100px) {
  .exam-workspace {
    grid-template-columns: 1fr;
  }

  .exam-side {
    position: static;
  }
}

@media (max-width: 720px) {
  .exam-toolbar,
  .paper-intro,
  .pdf-fallback,
  .section-heading,
  .sub-prompt {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-actions,
  .side-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .timer-chip {
    width: 100%;
  }

  .year-card-grid {
    grid-template-columns: 1fr;
  }

  .pdf-modal {
    inset: 10px;
  }
}
</style>
