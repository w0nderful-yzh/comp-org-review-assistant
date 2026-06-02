<template>
  <div v-if="!isAuthenticated" class="auth-wrapper">
    <LoginView />
  </div>
  <main v-else class="app-shell">
    <GuideModal v-if="showGuide" @close="showGuide = false" />
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">组</div>
        <div>
          <h1>计算机组成原理复习助手</h1>
          <p>{{ user?.nickname || user?.student_id || "学习中" }}</p>
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

      <button class="btn-logout" @click="handleLogout">
        <LogOut :size="16" />
        <span>退出登录</span>
      </button>
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

      <footer class="app-disclaimer">
        <p>本系统知识库从 HDU 教学课件中提取，仅供学习参考。AI 生成内容可能存在错误，请结合教材使用。本系统不保证与教材完全一致，使用者应自行承担使用风险。</p>
      </footer>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  BarChart3,
  BookOpen,
  FileText,
  LogOut,
  RefreshCw,
  RotateCcw,
} from "@lucide/vue";
import { useAuth } from "./composables/useAuth";
import { useSharedState } from "./composables/useSharedState";
import LoginView from "./components/LoginView.vue";
import GuideModal from "./components/GuideModal.vue";
import PracticeView from "./components/PracticeView.vue";
import WrongQuestionsView from "./components/WrongQuestionsView.vue";
import StatsView from "./components/StatsView.vue";
import KnowledgeView from "./components/KnowledgeView.vue";

const { isAuthenticated, user, logout, fetchUser } = useAuth();
const { chapters, overview, refreshAll, percent } = useSharedState();

const activeView = ref<"practice" | "wrong" | "stats" | "knowledge">("practice");
const practiceMode = ref<string>("chapter");
const error = ref("");
const showGuide = ref(false);

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
  activeView.value = "practice";
  await nextTick();
  practiceRef.value?.startWrongPractice();
}

async function switchView(view: typeof activeView.value) {
  activeView.value = view;
  error.value = "";
  await nextTick();
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

function handleLogout() {
  logout();
}

onMounted(async () => {
  if (isAuthenticated.value) {
    await fetchUser();
    await refreshAll();
    // Show guide for existing session if not hidden
    if (localStorage.getItem('hideGuide') !== 'true') {
      showGuide.value = true;
    }
  }
});

// Watch for login state changes and refresh data
watch(isAuthenticated, async (newValue) => {
  if (newValue) {
    await refreshAll();
    // Show guide if user hasn't hidden it
    if (localStorage.getItem('hideGuide') !== 'true') {
      showGuide.value = true;
    }
  }
});
</script>

<style scoped>
.auth-wrapper {
  min-height: 100vh;
}

.btn-logout {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.8rem;
  margin: 0.75rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  font-size: 0.75rem;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.05em;
  transition: all 0.2s;
}

.btn-logout:hover {
  background: rgba(0, 255, 136, 0.08);
  border-color: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.app-disclaimer {
  padding: 12px 20px;
  margin-top: auto;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background: #fafafa;
}

.app-disclaimer p {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: #9ca3af;
  text-align: center;
}
</style>
