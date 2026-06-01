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
    <article v-for="item in wrongQuestions" :key="item.id" class="question-card">
      <div class="question-meta">
        <span>{{ item.wrong_count }}</span>
        <small>{{ typeLabel(item.question.type) }}</small>
        <b class="source-chip" :class="sourceTagClass(item.question.source_type)">{{ item.question.source_label }}</b>
      </div>
      <p class="stem">{{ item.question.stem }}</p>
      <p class="muted">参考答案：{{ formatAnswer(item.question.answer) }}</p>
      <div class="feedback-bar">
        <span class="feedback-prompt">这道题有帮助吗？</span>
        <button
          class="feedback-btn"
          :class="{ active: feedbackState[item.question.id] === 'helpful' || (item.question.user_liked && !feedbackState[item.question.id]) }"
          @click="toggleFeedback(item.question, 'helpful')"
        >
          <ThumbsUp :size="16" />
          <span>{{ item.question.likes || 0 }}</span>
        </button>
        <button
          class="feedback-btn"
          :class="{ active: feedbackState[item.question.id] === 'not_helpful' }"
          @click="toggleFeedback(item.question, 'not_helpful')"
        >
          <ThumbsDown :size="16" />
        </button>
      </div>
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
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { Check, CheckCircle2, RotateCcw, ThumbsDown, ThumbsUp } from "@lucide/vue";
import { api, type FeedbackType, type Question, type WrongQuestion } from "../api/client";
import { useSharedState } from "../composables/useSharedState";

defineEmits<{
  startWrongPractice: [];
}>();

const { typeLabel, sourceTagClass } = useSharedState();

const wrongQuestions = ref<WrongQuestion[]>([]);
const loading = ref(false);
const feedbackState = reactive<Record<number, FeedbackType | null>>({});

function formatAnswer(value: unknown) {
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === "object" && item !== null && "answer" in item ? item.answer : item)).join("、");
  }
  if (typeof value === "object" && value !== null) return JSON.stringify(value);
  return String(value ?? "");
}

async function load() {
  loading.value = true;
  try {
    wrongQuestions.value = await api.wrongQuestions();
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
