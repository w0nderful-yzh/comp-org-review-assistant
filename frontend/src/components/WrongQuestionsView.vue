<template>
  <section class="data-grid">
    <div v-if="wrongQuestions.length" class="wrong-toolbar">
      <div>
        <strong>{{ wrongQuestions.length }} 道待复习错题</strong>
        <span>重新练习会从当前错题本抽题。</span>
      </div>
      <button class="primary-button" :disabled="loading" @click="$emit('startWrongPractice')">
        <RotateCcw :size="18" />
        <span>重练错题</span>
      </button>
    </div>
    <article
      v-for="item in wrongQuestions"
      :key="item.id"
      class="question-card wrong-question-card"
      :class="{ expanded: expandedQuestionIds.has(item.question.id) }"
    >
      <button class="wrong-question-main" @click="toggleExpanded(item.question.id)">
        <div class="wrong-question-head">
          <div class="question-meta wrong-meta">
            <span class="wrong-count-chip">错 {{ item.wrong_count }} 次</span>
            <small>{{ chapterLabel(item.question.chapter_id) }}</small>
            <small>{{ typeLabel(item.question.type) }}</small>
            <b class="source-chip" :class="sourceTagClass(item.question.source_type)">{{ item.question.source_label }}</b>
          </div>
          <span class="review-toggle">{{ expandedQuestionIds.has(item.question.id) ? "收起复习" : "查看解析" }}</span>
        </div>
        <p class="stem">{{ item.question.stem }}</p>
        <p class="answer-summary">参考答案：{{ formatAnswer(item.question.answer, item.question) }}</p>
      </button>

      <div v-if="expandedQuestionIds.has(item.question.id)" class="wrong-review-panel">
        <div v-if="item.question.options.length" class="wrong-option-list">
          <div
            v-for="option in item.question.options"
            :key="option.key"
            class="wrong-option-row"
            :class="{ correct: answerKeys(item.question.answer).includes(option.key) }"
          >
            <strong>{{ option.key }}</strong>
            <span>{{ option.text }}</span>
          </div>
        </div>
        <div v-if="item.question.explanation" class="wrong-explanation">
          <strong>解析</strong>
          <p>{{ item.question.explanation }}</p>
        </div>
        <div class="wrong-review-meta">
          <span>{{ chapterLabel(item.question.chapter_id) }}</span>
          <span>最近出错：{{ formatDate(item.last_wrong_at) }}</span>
        </div>
      </div>

      <div class="feedback-bar">
        <span class="feedback-prompt">这道题有帮助吗？</span>
        <button
          class="feedback-btn"
          :class="{ active: feedbackState[item.question.id] === 'helpful' || (item.question.user_liked && !feedbackState[item.question.id]) }"
          @click.stop="toggleFeedback(item.question, 'helpful')"
        >
          <ThumbsUp :size="16" />
          <span>{{ item.question.likes || 0 }}</span>
        </button>
        <button
          class="feedback-btn"
          :class="{ active: feedbackState[item.question.id] === 'not_helpful' }"
          @click.stop="toggleFeedback(item.question, 'not_helpful')"
        >
          <ThumbsDown :size="16" />
        </button>
      </div>
      <button class="secondary-button" @click.stop="markMastered(item.question.id)">
        <Check :size="16" />
        <span>标记已掌握</span>
      </button>
    </article>
    <div v-if="!wrongQuestions.length" class="empty-state">
      <CheckCircle2 :size="38" />
      <p>当前没有待复习错题。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { Check, CheckCircle2, RotateCcw, ThumbsDown, ThumbsUp } from "@lucide/vue";
import { api, type FeedbackType, type Question, type WrongQuestion } from "../api/client";
import { useSharedState } from "../composables/useSharedState";

defineEmits<{
  startWrongPractice: [];
}>();

const { chapters, typeLabel, sourceTagClass } = useSharedState();

const wrongQuestions = ref<WrongQuestion[]>([]);
const loading = ref(false);
const feedbackState = reactive<Record<number, FeedbackType | null>>({});
const expandedQuestionIds = ref<Set<number>>(new Set());

function toggleExpanded(questionId: number) {
  const next = new Set(expandedQuestionIds.value);
  if (next.has(questionId)) next.delete(questionId);
  else next.add(questionId);
  expandedQuestionIds.value = next;
}

function chapterLabel(chapterId: number) {
  const chapter = chapters.value.find((item) => item.id === chapterId);
  return chapter ? `第 ${chapter.order_index} 章：${chapter.title}` : `章节 ${chapterId}`;
}

function answerKeys(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item ?? ""));
  if (typeof value === "string") return value.split(/[,，、\s]+/).filter(Boolean);
  return [];
}

function formatAnswer(value: unknown, question?: Question & { answer?: unknown }) {
  if (question?.type === "true_false") {
    const text = String(value ?? "").toUpperCase();
    if (text === "TRUE") return "正确";
    if (text === "FALSE") return "错误";
  }
  if (question?.options?.length) {
    const keys = answerKeys(value);
    if (keys.length) {
      return keys
        .map((key) => {
          const option = question.options.find((item) => item.key === key);
          return option ? `${option.key}. ${option.text}` : key;
        })
        .join("、");
    }
  }
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === "object" && item !== null && "answer" in item ? item.answer : item)).join("、");
  }
  if (typeof value === "object" && value !== null) return JSON.stringify(value);
  return String(value ?? "");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

async function load() {
  loading.value = true;
  try {
    wrongQuestions.value = await api.wrongQuestions();
    expandedQuestionIds.value = new Set();
  } finally {
    loading.value = false;
  }
}

async function markMastered(questionId: number) {
  await api.markMastered(questionId);
  await load();
}

async function toggleFeedback(question: Question & { answer?: unknown }, feedbackType: FeedbackType) {
  const current = feedbackState[question.id];
  if (current === feedbackType) {
    await api.deleteFeedback(question.id);
    feedbackState[question.id] = null;
    if (feedbackType === "helpful") question.likes = Math.max(0, question.likes - 1);
    question.user_liked = false;
  } else {
    const result = await api.submitFeedback(question.id, feedbackType);
    feedbackState[question.id] = feedbackType;
    question.likes = result.likes;
    question.user_liked = result.user_liked;
  }
}

defineExpose({ load });
</script>

<style scoped>
.wrong-question-card {
  display: grid;
  gap: 12px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.wrong-question-card.expanded {
  border-color: var(--teal);
  box-shadow: inset 4px 0 0 var(--teal);
}

.wrong-question-main {
  display: grid;
  gap: 12px;
  width: 100%;
  padding: 0;
  border: 0;
  color: inherit;
  text-align: left;
  background: transparent;
}

.wrong-question-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.wrong-meta {
  flex-wrap: wrap;
}

.wrong-meta .wrong-count-chip,
.review-toggle {
  display: inline-flex;
  width: auto;
  height: auto;
  min-width: 0;
  min-height: 28px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 13px;
  font-weight: 900;
  line-height: 1.2;
  white-space: nowrap;
}

.wrong-meta .wrong-count-chip {
  color: #ffffff;
  background: var(--teal);
}

.review-toggle {
  flex: 0 0 auto;
  color: var(--teal);
  background: #e9f4f1;
}

.answer-summary {
  margin: 0;
  color: #5f6966;
  font-weight: 800;
  line-height: 1.6;
}

.wrong-review-panel {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: #f7f9f3;
}

.wrong-option-list {
  display: grid;
  gap: 8px;
}

.wrong-option-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 10px;
  border: 1px solid #dce2d7;
  border-radius: 8px;
  background: #fffef9;
}

.wrong-option-row.correct {
  border-color: #8fc6b7;
  background: #edf8f4;
}

.wrong-option-row strong {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  background: var(--teal);
  font-size: 13px;
}

.wrong-option-row span {
  line-height: 1.55;
}

.wrong-explanation {
  display: grid;
  gap: 6px;
}

.wrong-explanation p {
  margin: 0;
  color: #4b5652;
  line-height: 1.65;
}

.wrong-review-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.wrong-review-meta span {
  min-height: 26px;
  padding: 4px 9px;
  border: 1px solid #d7e1d5;
  border-radius: 999px;
  color: #4b5652;
  background: #fffef9;
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 720px) {
  .wrong-question-head {
    flex-direction: column;
  }

  .review-toggle {
    align-self: flex-start;
  }
}
</style>
