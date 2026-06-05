<template>
  <section class="lab-page">
    <header class="lab-header">
      <div>
        <p class="eyebrow">Lab Exam</p>
        <h2>计组实验模拟考试</h2>
        <p>基于 RISC-V 指令集和实验模型机，按实验练习题格式组织。</p>
      </div>
      <div class="lab-actions">
        <button class="secondary-button" :disabled="loading" @click="load">
          <RefreshCw :size="16" />
          <span>刷新</span>
        </button>
        <button class="primary-button" :disabled="!canGenerate" @click="generatePaper">
          <Sparkles :size="16" />
          <span>{{ generateButtonText }}</span>
        </button>
      </div>
    </header>

    <section v-if="error" class="notice error">{{ error }}</section>

    <section v-if="generationStatusText" class="generation-banner" :class="generationClass">
      <div>
        <p class="eyebrow">AI Paper</p>
        <h3>{{ generationStatusText }}</h3>
        <span>{{ generationHint }}</span>
      </div>
      <Loader2 v-if="isGenerating" class="spin" :size="24" />
      <CheckCircle2 v-else-if="latestGeneration?.status === 'completed'" :size="24" />
      <AlertTriangle v-else-if="latestGeneration?.status === 'failed'" :size="24" />
    </section>

    <div v-if="dashboard" class="paper-switch">
      <button :class="{ selected: selectedPaperMode === 'static' }" @click="selectPaper('static')">
        <FileText :size="16" />
        <span>现成模拟卷</span>
      </button>
      <button
        :class="{ selected: selectedPaperMode === 'generated' }"
        :disabled="!generatedPaper"
        @click="selectPaper('generated')"
      >
        <Sparkles :size="16" />
        <span>AI 生成卷</span>
      </button>
    </div>

    <div v-if="activePaper" class="lab-workspace">
      <main class="paper-column">
        <section class="paper-intro">
          <div>
            <p class="eyebrow">{{ activePaper.generated ? "Generated" : "Ready" }}</p>
            <h3>{{ activePaper.title }}</h3>
            <span>{{ activePaper.duration_minutes }} 分钟 · {{ activePaper.total_score }} 分</span>
          </div>
          <div class="timer-chip" :class="{ hot: remainingSeconds <= 600 && running }">
            <Clock3 :size="18" />
            <strong>{{ timerText }}</strong>
          </div>
        </section>

        <section
          v-for="section in activePaper.sections"
          :id="`lab-section-${section.id}`"
          :key="section.id"
          class="section-band"
        >
          <div class="section-heading">
            <div>
              <p class="eyebrow">Section</p>
              <h3>{{ section.title }}</h3>
              <span v-if="section.description">{{ section.description }}</span>
            </div>
            <b>{{ section.score }} 分</b>
          </div>

          <article
            v-for="question in questionsBySection(section.id)"
            :id="`lab-question-${question.id}`"
            :key="question.id"
            class="lab-question-card"
          >
            <div class="question-head">
              <span>{{ question.number }}</span>
              <div>
                <h4>{{ question.title }}</h4>
                <small>{{ question.score }} 分</small>
              </div>
            </div>
            <p class="question-stem">{{ question.stem }}</p>

            <div v-if="question.answer_type === 'single_choice'" class="choice-grid">
              <button
                v-for="option in question.options"
                :key="option.key"
                :class="{ selected: answers[question.id] === option.key }"
                :disabled="showAnswers"
                @click="setAnswer(question.id, option.key)"
              >
                <b>{{ option.key }}</b>
                <span>{{ option.text }}</span>
              </button>
            </div>

            <textarea
              v-else
              :id="`lab-answer-${question.id}`"
              v-model="answers[question.id]"
              :disabled="showAnswers"
              class="inline-answer"
              placeholder="在这里作答"
              @input="saveDraft"
            />

            <section v-if="showAnswers" class="answer-box">
              <p class="eyebrow">Answer</p>
              <strong v-if="question.answer">答案：{{ question.answer }}</strong>
              <p>{{ question.reference_answer || question.explanation }}</p>
              <small v-if="question.reference_answer && question.explanation">{{ question.explanation }}</small>
            </section>
          </article>
        </section>
      </main>

      <aside class="lab-side">
        <section class="lab-panel">
          <p class="eyebrow">Session</p>
          <h3>{{ statusTitle }}</h3>
          <span>{{ answeredCount }} / {{ activePaper.questions.length }} 题已填写</span>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: progressPercent }"></div>
          </div>
          <div class="side-actions">
            <button v-if="!running && !showAnswers" class="primary-button" @click="startExam">
              <Play :size="17" />
              <span>{{ paused ? "继续" : "开始模拟" }}</span>
            </button>
            <button v-if="running" class="secondary-button" @click="pauseExam">
              <Pause :size="17" />
              <span>暂停</span>
            </button>
            <button class="secondary-button" :disabled="answeredCount >= activePaper.questions.length" @click="jumpToNextUnanswered">
              <ChevronRight :size="17" />
              <span>下一未答</span>
            </button>
            <button class="secondary-button" @click="resetExam">
              <RotateCcw :size="17" />
              <span>重置</span>
            </button>
          </div>
        </section>

        <section class="lab-panel mini-map">
          <p class="eyebrow">Jump</p>
          <button v-for="section in activePaper.sections" :key="section.id" @click="jumpToSection(section.id)">
            <span>{{ section.title }}</span>
            <b>{{ sectionAnswered(section.id) }}/{{ questionsBySection(section.id).length }}</b>
          </button>
        </section>

        <section class="lab-panel">
          <button class="submit-button wide" @click="finishExam">
            <CheckCircle2 :size="18" />
            <span>{{ showAnswers ? "隐藏答案" : "交卷并查看答案" }}</span>
          </button>
        </section>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileText,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Sparkles,
} from "@lucide/vue";
import { api, type LabExamDashboard, type LabExamGeneration, type LabExamPaper, type LabExamQuestion } from "../api/client";

const dashboard = ref<LabExamDashboard | null>(null);
const latestGeneration = ref<LabExamGeneration | null>(null);
const selectedPaperMode = ref<"static" | "generated">("static");
const loading = ref(false);
const error = ref("");
const running = ref(false);
const paused = ref(false);
const showAnswers = ref(false);
const remainingSeconds = ref(90 * 60);
const answers = reactive<Record<string, string>>({});
let timer: ReturnType<typeof setInterval> | null = null;
let pollTimer: ReturnType<typeof setInterval> | null = null;

const generatedPaper = computed(() => latestGeneration.value?.status === "completed" ? latestGeneration.value.paper : null);
const activePaper = computed<LabExamPaper | null>(() => {
  if (!dashboard.value) return null;
  if (selectedPaperMode.value === "generated" && generatedPaper.value) return generatedPaper.value;
  return dashboard.value.static_paper;
});
const isGenerating = computed(() => latestGeneration.value?.status === "pending" || latestGeneration.value?.status === "running");
const canGenerate = computed(() => Boolean(dashboard.value?.ai_enabled && dashboard.value.daily_remaining > 0 && !isGenerating.value));
const generateButtonText = computed(() => {
  if (!dashboard.value?.ai_enabled) return "AI 未配置";
  if (isGenerating.value) return "生成中";
  if (dashboard.value.daily_remaining <= 0) return "今日已生成";
  return "AI 生成一份";
});
const generationStatusText = computed(() => {
  if (!latestGeneration.value) return "";
  if (latestGeneration.value.status === "pending") return "试卷排队生成中";
  if (latestGeneration.value.status === "running") return "试卷生成中";
  if (latestGeneration.value.status === "completed") return "AI 试卷已生成";
  return "AI 试卷生成失败";
});
const generationHint = computed(() => {
  if (!latestGeneration.value) return "";
  if (isGenerating.value) return "生成可能较慢，你可以先去做章节练习、错题本或知识库，回来后这里会自动更新。";
  if (latestGeneration.value.status === "completed") return "今天的 AI 实验模拟卷已准备好，可切换到 AI 生成卷。";
  return latestGeneration.value.error_message || "稍后可以重新查看状态。";
});
const generationClass = computed(() => ({
  done: latestGeneration.value?.status === "completed",
  failed: latestGeneration.value?.status === "failed",
}));
const answeredCount = computed(() => activePaper.value?.questions.filter((q) => String(answers[q.id] ?? "").trim()).length ?? 0);
const progressPercent = computed(() => activePaper.value?.questions.length ? `${Math.round(answeredCount.value / activePaper.value.questions.length * 100)}%` : "0%");
const timerText = computed(() => {
  const seconds = Math.max(remainingSeconds.value, 0);
  const mm = Math.floor(seconds / 60);
  const ss = seconds % 60;
  return `${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
});
const statusTitle = computed(() => {
  if (showAnswers.value) return "已交卷";
  if (running.value) return "模拟中";
  if (paused.value) return "已暂停";
  return "待开始";
});

function questionsBySection(sectionId: string): LabExamQuestion[] {
  return activePaper.value?.questions.filter((question) => question.section_id === sectionId) ?? [];
}

function sectionAnswered(sectionId: string): number {
  return questionsBySection(sectionId).filter((q) => String(answers[q.id] ?? "").trim()).length;
}

function storageKey(paper = activePaper.value): string {
  return paper ? `comp-org-lab-exam-draft-${paper.id}` : "";
}

function saveDraft() {
  const key = storageKey();
  if (key) localStorage.setItem(key, JSON.stringify(answers));
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

function clearTimer() {
  if (timer) clearInterval(timer);
  timer = null;
}

function tick() {
  if (remainingSeconds.value <= 1) {
    remainingSeconds.value = 0;
    finishExam();
    return;
  }
  remainingSeconds.value -= 1;
}

function startExam() {
  running.value = true;
  paused.value = false;
  showAnswers.value = false;
  clearTimer();
  timer = setInterval(tick, 1000);
}

function pauseExam() {
  running.value = false;
  paused.value = true;
  clearTimer();
  saveDraft();
}

function resetExam() {
  clearTimer();
  running.value = false;
  paused.value = false;
  showAnswers.value = false;
  remainingSeconds.value = (activePaper.value?.duration_minutes ?? 90) * 60;
  Object.keys(answers).forEach((key) => delete answers[key]);
  const key = storageKey();
  if (key) localStorage.removeItem(key);
}

function finishExam() {
  if (showAnswers.value) {
    showAnswers.value = false;
    return;
  }
  saveDraft();
  clearTimer();
  running.value = false;
  paused.value = false;
  showAnswers.value = true;
}

function setAnswer(questionId: string, value: string) {
  if (showAnswers.value) return;
  answers[questionId] = value;
  saveDraft();
}

function jumpToSection(sectionId: string) {
  document.getElementById(`lab-section-${sectionId}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function jumpToNextUnanswered() {
  const target = activePaper.value?.questions.find((q) => !String(answers[q.id] ?? "").trim());
  if (!target) return;
  document.getElementById(`lab-question-${target.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  window.setTimeout(() => document.getElementById(`lab-answer-${target.id}`)?.focus(), 260);
}

function selectPaper(mode: "static" | "generated") {
  selectedPaperMode.value = mode;
  resetExam();
  restoreDraft();
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    dashboard.value = await api.labExams();
    latestGeneration.value = dashboard.value.latest_generation;
    if (!generatedPaper.value && selectedPaperMode.value === "generated") {
      selectedPaperMode.value = "static";
    }
    restoreDraft();
    managePolling();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "加载实验模拟考试失败";
  } finally {
    loading.value = false;
  }
}

async function generatePaper() {
  if (!canGenerate.value) return;
  error.value = "";
  try {
    latestGeneration.value = await api.createLabExamGeneration();
    if (dashboard.value) dashboard.value.daily_remaining = 0;
    managePolling();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "创建 AI 试卷失败";
  }
}

async function pollGeneration() {
  if (!latestGeneration.value || !isGenerating.value) return;
  try {
    latestGeneration.value = await api.labExamGeneration(latestGeneration.value.id);
    if (latestGeneration.value.status === "completed") {
      selectedPaperMode.value = "generated";
      restoreDraft();
    }
    managePolling();
  } catch {
    managePolling(false);
  }
}

function managePolling(enable = true) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
  if (enable && isGenerating.value) {
    pollTimer = setInterval(pollGeneration, 5000);
  }
}

defineExpose({ load });

onMounted(load);

onBeforeUnmount(() => {
  clearTimer();
  if (pollTimer) clearInterval(pollTimer);
});

watch(activePaper, (paper) => {
  remainingSeconds.value = (paper?.duration_minutes ?? 90) * 60;
});
</script>

<style scoped>
.lab-page {
  min-width: 0;
}

.lab-header,
.paper-intro,
.section-band,
.lab-panel,
.generation-banner {
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: rgb(255 253 248 / 92%);
}

.lab-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 18px;
  margin-bottom: 14px;
}

.lab-header h2,
.paper-intro h3,
.section-heading h3,
.lab-panel h3,
.generation-banner h3 {
  margin: 4px 0 0;
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  line-height: 1.2;
}

.lab-header p:not(.eyebrow),
.paper-intro span,
.section-heading span,
.lab-panel span,
.generation-banner span {
  color: var(--muted);
}

.lab-actions,
.side-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.generation-banner {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  padding: 14px;
  margin-bottom: 14px;
  border-color: #e8d39b;
  background: #fff9e9;
}

.generation-banner.done {
  border-color: #b9d8c8;
  background: #f4faf4;
}

.generation-banner.failed {
  border-color: #e3b3ad;
  background: #fff0ec;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.paper-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.paper-switch button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  border: 1px solid #cdd6ca;
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--ink);
  background: #fffef9;
  font-weight: 900;
}

.paper-switch button.selected {
  border-color: var(--teal);
  color: #fff;
  background: var(--teal);
}

.lab-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);
  gap: 18px;
  align-items: start;
}

.paper-column {
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
  scroll-margin-top: 92px;
}

.section-heading,
.question-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.section-heading b,
.mini-map b,
.choice-grid b {
  color: var(--teal);
}

.lab-question-card {
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
  font-size: 17px;
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

.question-stem {
  margin: 0;
  padding: 14px;
  border-left: 4px solid #efd174;
  background: #fff9e9;
  line-height: 1.8;
  white-space: pre-wrap;
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

.answer-box {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid #b9d8c8;
  border-radius: 8px;
  background: #f4faf4;
}

.answer-box p,
.answer-box small {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
  white-space: pre-wrap;
}

.lab-side {
  position: sticky;
  top: 84px;
  display: grid;
  gap: 12px;
  min-width: 0;
}

.lab-panel {
  display: grid;
  gap: 12px;
  padding: 14px;
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

.wide {
  width: 100%;
}

.primary-button,
.submit-button,
.primary-button span,
.primary-button svg,
.submit-button span,
.submit-button svg {
  color: #fff;
  -webkit-text-fill-color: #fff;
}

.secondary-button,
.secondary-button span,
.secondary-button svg {
  color: #273533;
  -webkit-text-fill-color: #273533;
}

@media (max-width: 1100px) {
  .lab-workspace {
    grid-template-columns: 1fr;
  }

  .lab-side {
    position: static;
  }
}

@media (max-width: 720px) {
  .lab-header,
  .paper-intro,
  .section-heading {
    flex-direction: column;
    align-items: stretch;
  }

  .lab-actions,
  .side-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}
</style>
