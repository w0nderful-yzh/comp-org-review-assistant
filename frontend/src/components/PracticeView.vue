<template>
  <section class="practice-layout">
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
          <span>{{ chapter.question_count }} 道题</span>
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
        <div class="source-toggle">
          <span>练习模式</span>
          <div class="segmented compact">
            <button :class="{ selected: practiceSourceScope === 'original_only' }" @click="practiceSourceScope = 'original_only'">
              只做原题
            </button>
            <button :class="{ selected: practiceSourceScope === 'standard' }" @click="practiceSourceScope = 'standard'">
              标准练习
            </button>
            <button :class="{ selected: practiceSourceScope === 'supplement' }" @click="practiceSourceScope = 'supplement'">
              专项补充
            </button>
          </div>
        </div>
        <button class="primary-button" :disabled="loading" @click="startPractice">
          <Play :size="18" />
          <span>开始</span>
        </button>
      </div>

      <div v-if="aiEnabled" class="ai-generate-section">
        <button class="ai-generate-toggle" @click="showAiPanel = !showAiPanel">
          <Sparkles :size="16" />
          <span>专项补充练习</span>
          <small>当原题不够，或你想针对某个知识点加强练习时，可以生成少量 AI 补充题。</small>
          <ChevronRight :size="16" :class="{ rotated: showAiPanel }" />
        </button>
        <div v-if="showAiPanel" class="ai-generate-panel">
          <div class="ai-generate-grid">
            <label>
              <span>章节</span>
              <select v-model.number="aiForm.chapter_id">
                <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">
                  第 {{ chapter.order_index }} 章：{{ chapter.title }}
                </option>
              </select>
            </label>
            <label>
              <span>题型</span>
              <select v-model="aiForm.type">
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
              <select v-model="aiForm.difficulty">
                <option value="easy">基础</option>
                <option value="medium">中等</option>
                <option value="hard">提高</option>
              </select>
            </label>
            <label>
              <span>数量</span>
              <input v-model.number="aiForm.count" type="number" min="1" max="5" />
            </label>
          </div>
          <label>
            <span>关注点（可选）</span>
            <input v-model="aiForm.focus" placeholder="例如 Cache 命中率、流水线冒险、补码运算" />
          </label>
          <div class="ai-generate-actions">
            <button class="primary-button" :disabled="aiLoading" @click="generateAiQuestions">
              <Sparkles :size="18" />
              <span>{{ aiLoading ? "生成中..." : "生成补充题" }}</span>
            </button>
            <small v-if="aiDailyRemaining >= 0">今日剩余 {{ aiDailyRemaining }} 道</small>
          </div>
          <p v-if="aiMessage" class="save-message">{{ aiMessage }}</p>
        </div>
      </div>
      <div v-else class="ai-disabled-notice">
        当前未配置 AI 服务，补充练习功能不可用。
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
            <b class="source-chip" :class="sourceTagClass(question.source_type)">{{ question.source_label }}</b>
          </div>
          <p class="stem">{{ question.stem }}</p>

          <div v-if="question.ai_status" class="ai-question-notice">
            本题由 AI 根据课程知识库生成，可能存在不严谨之处。欢迎反馈。
          </div>

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

          <div class="feedback-bar">
            <span class="feedback-prompt">这道题{{ question.ai_status ? '对你' : '' }}有帮助吗？</span>
            <button
              class="feedback-btn"
              :class="{ active: questionFeedbackState[question.id] === 'helpful' || (question.user_liked && questionFeedbackState[question.id] === undefined) }"
              @click="toggleFeedback(question, 'helpful')"
            >
              <ThumbsUp :size="16" />
              <span>{{ question.likes || 0 }}</span>
            </button>
            <button
              class="feedback-btn"
              :class="{ active: questionFeedbackState[question.id] === 'not_helpful' }"
              @click="toggleFeedback(question, 'not_helpful')"
            >
              <ThumbsDown :size="16" />
            </button>
            <button
              class="feedback-btn flag-btn"
              :class="{ active: questionFeedbackState[question.id] === 'flag' }"
              @click="toggleFlagPanel(question.id)"
            >
              <AlertTriangle :size="16" />
              <span>题目有问题</span>
            </button>
          </div>
          <div v-if="flagPanelQuestionId === question.id" class="flag-panel">
            <button
              v-for="reason in flagReasons"
              :key="reason.value"
              class="flag-reason-btn"
              @click="submitFlag(question, reason.value)"
            >
              {{ reason.label }}
            </button>
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
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  GraduationCap,
  Play,
  Shuffle,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from "@lucide/vue";
import { api, type AnswerResult, type FeedbackType, type FlagReason, type PracticeResult, type PracticeSession, type Question, type QuestionType, type SourceScope } from "../api/client";
import { useSharedState } from "../composables/useSharedState";

const emit = defineEmits<{
  refresh: [];
  modeChange: [mode: string];
}>();

const { chapters, typeLabel, difficultyLabel, sourceTagClass } = useSharedState();

const session = ref<PracticeSession | null>(null);
const result = ref<PracticeResult | null>(null);
const practiceMode = ref<"chapter" | "final_review" | "wrong_questions">("chapter");
const selectedChapterId = ref<number | null>(1);
const selectedQuestionType = ref<QuestionType | "">("");
const practiceSourceScope = ref<SourceScope>("standard");
const questionCount = ref(5);
const loading = ref(false);
const error = ref("");
const aiEnabled = ref(false);
const aiDailyRemaining = ref(0);
const showAiPanel = ref(false);
const aiLoading = ref(false);
const aiMessage = ref("");
const flagPanelQuestionId = ref<number | null>(null);

const aiForm = reactive({
  chapter_id: 1,
  type: "single_choice" as QuestionType,
  difficulty: "medium" as "easy" | "medium" | "hard",
  count: 3,
  focus: "",
});

const answers = reactive<Record<number, string | string[]>>({});
const unansweredQuestionIds = ref<Set<number>>(new Set());
const questionFeedbackState = reactive<Record<number, FeedbackType | null>>({});

const flagReasons = [
  { value: "answer_error" as FlagReason, label: "答案疑似错误" },
  { value: "unclear_stem" as FlagReason, label: "题干表述不清" },
  { value: "ambiguous_options" as FlagReason, label: "选项有歧义" },
  { value: "out_of_scope" as FlagReason, label: "内容超纲" },
  { value: "duplicate" as FlagReason, label: "重复题" },
  { value: "unclear_explanation" as FlagReason, label: "解析不清楚" },
];

const resultByQuestion = computed<Record<number, AnswerResult>>(() => {
  const rows: Record<number, AnswerResult> = {};
  for (const item of result.value?.results ?? []) rows[item.question_id] = item;
  return rows;
});

function selectChapter(chapterId: number) {
  selectedChapterId.value = chapterId;
  aiForm.chapter_id = chapterId;
  practiceMode.value = "chapter";
  session.value = null;
  result.value = null;
  emit("modeChange", "chapter");
}

function selectFinalReview() {
  practiceMode.value = "final_review";
  selectedChapterId.value = null;
  session.value = null;
  result.value = null;
  emit("modeChange", "final_review");
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
      source_scope: practiceSourceScope.value,
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
    emit("refresh");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "提交失败";
  } finally {
    loading.value = false;
  }
}

async function startWrongPractice() {
  loading.value = true;
  error.value = "";
  result.value = null;
  unansweredQuestionIds.value = new Set();
  Object.keys(answers).forEach((key) => delete answers[Number(key)]);
  try {
    session.value = await api.createPractice({
      mode: "wrong_questions",
      question_count: questionCount.value || 10,
      source_scope: practiceSourceScope.value,
      user_id: "demo",
    });
    practiceMode.value = "wrong_questions";
    selectedChapterId.value = session.value.chapter_id;
    emit("modeChange", "wrong_questions");
  } catch (err) {
    error.value = err instanceof Error ? err.message : "创建错题练习失败";
  } finally {
    loading.value = false;
  }
}

async function generateAiQuestions() {
  aiLoading.value = true;
  aiMessage.value = "";
  try {
    const result = await api.createAiQuestionDrafts({
      chapter_id: aiForm.chapter_id,
      question_types: [aiForm.type],
      difficulty: aiForm.difficulty,
      count: aiForm.count,
      focus: aiForm.focus.trim() || null,
    });
    aiMessage.value = `已生成 ${result.created} 道补充题，可通过"专项补充"模式练习`;
    aiDailyRemaining.value = Math.max(0, aiDailyRemaining.value - result.created);
    emit("refresh");
  } catch (err) {
    aiMessage.value = err instanceof Error ? err.message : "生成失败";
  } finally {
    aiLoading.value = false;
  }
}

async function toggleFeedback(question: Question, feedbackType: FeedbackType) {
  const current = questionFeedbackState[question.id];
  if (current === feedbackType) {
    await api.deleteFeedback(question.id);
    questionFeedbackState[question.id] = null;
    if (feedbackType === "helpful") question.likes = Math.max(0, question.likes - 1);
    question.user_liked = false;
  } else {
    const prevType = current;
    const fbResult = await api.submitFeedback(question.id, feedbackType);
    questionFeedbackState[question.id] = feedbackType;
    question.likes = fbResult.likes;
    question.user_liked = fbResult.user_liked;
    if (fbResult.ai_status) question.ai_status = fbResult.ai_status;
  }
}

function toggleFlagPanel(questionId: number) {
  flagPanelQuestionId.value = flagPanelQuestionId.value === questionId ? null : questionId;
}

async function submitFlag(question: Question, reason: FlagReason) {
  const fbResult = await api.submitFeedback(question.id, "flag", reason);
  questionFeedbackState[question.id] = "flag";
  question.likes = fbResult.likes;
  if (fbResult.ai_status) question.ai_status = fbResult.ai_status;
  flagPanelQuestionId.value = null;
}

onMounted(async () => {
  try {
    const status = await api.aiStatus();
    aiEnabled.value = status.enabled;
    aiDailyRemaining.value = status.daily_remaining;
  } catch {
    aiEnabled.value = false;
  }
});

defineExpose({ startWrongPractice, selectedChapterId });
</script>
