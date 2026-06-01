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
        <button :class="{ active: activeView === 'practice' }" @click="switchView('practice')">
          <BookOpen :size="18" />
          <span>章节练习</span>
        </button>
        <button :class="{ active: activeView === 'wrong' }" @click="switchView('wrong')">
          <RotateCcw :size="18" />
          <span>错题本</span>
        </button>
        <button :class="{ active: activeView === 'stats' }" @click="switchView('stats')">
          <BarChart3 :size="18" />
          <span>学习统计</span>
        </button>
        <button :class="{ active: activeView === 'knowledge' }" @click="switchView('knowledge')">
          <FileText :size="18" />
          <span>知识库</span>
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

      <PracticeView
        v-if="activeView === 'practice'"
        ref="practiceRef"
        @refresh="handleRefresh"
        @mode-change="handleModeChange"
      />
      <WrongQuestionsView
        v-else-if="activeView === 'wrong'"
        ref="wrongRef"
        @start-wrong-practice="handleStartWrongPractice"
      />
      <StatsView v-else-if="activeView === 'stats'" ref="statsRef" />
      <KnowledgeView v-else-if="activeView === 'knowledge'" ref="knowledgeRef" />
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  BarChart3,
  BookOpen,
  FileText,
  RefreshCw,
  RotateCcw,
} from "@lucide/vue";
import { useSharedState } from "./composables/useSharedState";
import PracticeView from "./components/PracticeView.vue";
import WrongQuestionsView from "./components/WrongQuestionsView.vue";
import StatsView from "./components/StatsView.vue";
import KnowledgeView from "./components/KnowledgeView.vue";

const { chapters, overview, refreshAll, percent } = useSharedState();

const activeView = ref<"practice" | "wrong" | "stats" | "knowledge">("practice");
const practiceMode = ref<string>("chapter");
const error = ref("");

const practiceRef = ref<InstanceType<typeof PracticeView> | null>(null);
const wrongRef = ref<InstanceType<typeof WrongQuestionsView> | null>(null);
const statsRef = ref<InstanceType<typeof StatsView> | null>(null);
const knowledgeRef = ref<InstanceType<typeof KnowledgeView> | null>(null);

const viewTitle = computed(() => {
  if (activeView.value === "wrong") return "错题本";
  if (activeView.value === "stats") return "学习统计";
  if (activeView.value === "knowledge") return "课程知识库";
  if (practiceMode.value === "wrong_questions") return "错题重练";
  if (practiceMode.value === "final_review") return "总复习练习";
  const chapter = chapters.value.find((item) => item.id === practiceRef.value?.selectedChapterId);
  return chapter ? `第 ${chapter.order_index} 章：${chapter.title}` : "章节练习";
});

function handleModeChange(mode: string) {
  practiceMode.value = mode;
  if (mode === "wrong_questions") {
    activeView.value = "practice";
  }
}

async function handleRefresh() {
  await refreshAll();
}

async function handleStartWrongPractice() {
  if (practiceRef.value) {
    activeView.value = "practice";
    practiceRef.value.startWrongPractice();
  }
}

function switchView(view: typeof activeView.value) {
  activeView.value = view;
  error.value = "";
  if (view === "wrong") wrongRef.value?.load();
  else if (view === "stats") statsRef.value?.load();
  else if (view === "knowledge") knowledgeRef.value?.load();
}

async function refreshCurrent() {
  if (activeView.value === "wrong") wrongRef.value?.load();
  else if (activeView.value === "stats") statsRef.value?.load();
  else if (activeView.value === "knowledge") knowledgeRef.value?.load();
  else await refreshAll();
}

onMounted(refreshAll);
</script>
