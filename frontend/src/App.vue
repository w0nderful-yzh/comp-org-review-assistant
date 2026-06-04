<template>
  <div v-if="!isAuthenticated" class="auth-wrapper">
    <LoginView />
  </div>
  <main v-else class="app-shell" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <GuideModal v-if="showGuide" @close="showGuide = false" />
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-main">
          <div class="brand-mark">组</div>
          <div class="brand-copy">
            <h1>计算机组成原理复习助手</h1>
            <p>{{ user?.nickname || user?.student_id || "学习中" }}</p>
          </div>
        </div>
        <button class="sidebar-toggle" :title="sidebarCollapsed ? '展开侧栏' : '收起侧栏'" @click="toggleSidebar">
          <PanelLeftOpen v-if="sidebarCollapsed" :size="18" />
          <PanelLeftClose v-else :size="18" />
        </button>
      </div>

      <section class="sidebar-status">
        <div>
          <span>Review Console</span>
          <h1>复习控制台</h1>
        </div>
        <b>{{ user?.nickname || user?.student_id || "学习中" }}</b>
      </section>

      <nav class="nav-list" aria-label="主导航">
        <button :class="{ active: activeView === 'practice' }" @click="switchView('practice')">
          <BookOpen :size="18" />
          <span>章节练习</span>
        </button>
        <button :class="{ active: activeView === 'exam' }" @click="switchView('exam')">
          <ClipboardCheck :size="18" />
          <span>真题模拟</span>
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
      <ExamMockView v-else-if="activeView === 'exam'" ref="examRef" />
      <WrongQuestionsView
        v-else-if="activeView === 'wrong'"
        ref="wrongRef"
        @start-wrong-practice="handleStartWrongPractice"
      />
      <StatsView v-else-if="activeView === 'stats'" ref="statsRef" />
      <KnowledgeView v-else-if="activeView === 'knowledge'" ref="knowledgeRef" />

      <footer class="app-footer">
        <div class="footer-disclaimer">
          <p>本系统知识库从 HDU 教学课件中提取，仅供学习参考。AI 生成内容可能存在错误，请结合教材使用。本系统不保证与教材完全一致，使用者应自行承担使用风险。</p>
        </div>
        <div class="footer-contact">
          <span>遇到问题或有建议？欢迎反馈：</span>
          <a href="mailto:3353291703@qq.com">📧 3353291703@qq.com</a>
          <span class="divider">|</span>
          <a href="https://github.com/w0nderful-yzh" target="_blank" rel="noopener">🐙 GitHub</a>
        </div>
      </footer>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import {
  BarChart3,
  BookOpen,
  ClipboardCheck,
  FileText,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  RotateCcw,
} from "@lucide/vue";
import { useAuth } from "./composables/useAuth";
import { useSharedState } from "./composables/useSharedState";
import LoginView from "./components/LoginView.vue";
import GuideModal from "./components/GuideModal.vue";
import ExamMockView from "./components/ExamMockView.vue";
import PracticeView from "./components/PracticeView.vue";
import WrongQuestionsView from "./components/WrongQuestionsView.vue";
import StatsView from "./components/StatsView.vue";
import KnowledgeView from "./components/KnowledgeView.vue";

const { isAuthenticated, user, logout, fetchUser } = useAuth();
const { chapters, overview, refreshAll, percent } = useSharedState();

const activeView = ref<"practice" | "exam" | "wrong" | "stats" | "knowledge">("practice");
const practiceMode = ref<string>("chapter");
const error = ref("");
const showGuide = ref(false);
const sidebarCollapsed = ref(localStorage.getItem("comp-org-sidebar-collapsed") === "true");

const practiceRef = ref<InstanceType<typeof PracticeView> | null>(null);
const examRef = ref<InstanceType<typeof ExamMockView> | null>(null);
const wrongRef = ref<InstanceType<typeof WrongQuestionsView> | null>(null);
const statsRef = ref<InstanceType<typeof StatsView> | null>(null);
const knowledgeRef = ref<InstanceType<typeof KnowledgeView> | null>(null);

const viewTitle = computed(() => {
  if (activeView.value === "wrong") return "错题本";
  if (activeView.value === "exam") return "真题模拟";
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
  else if (view === "exam") examRef.value?.load();
  else if (view === "stats") statsRef.value?.load();
  else if (view === "knowledge") knowledgeRef.value?.load();
}

async function refreshCurrent() {
  if (activeView.value === "wrong") wrongRef.value?.load();
  else if (activeView.value === "exam") examRef.value?.load();
  else if (activeView.value === "stats") statsRef.value?.load();
  else if (activeView.value === "knowledge") knowledgeRef.value?.load();
  else await refreshAll();
}

function handleLogout() {
  logout();
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  localStorage.setItem("comp-org-sidebar-collapsed", String(sidebarCollapsed.value));
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
  justify-content: center;
  min-height: 42px;
  padding: 0 0.8rem;
  border: 1px solid rgb(255 255 255 / 12%);
  border-radius: 8px;
  color: rgb(246 243 234 / 76%);
  background: rgb(255 255 255 / 5%);
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 800;
  transition: all 0.2s;
}

.btn-logout:hover {
  color: #f0c96a;
  border-color: rgb(240 201 106 / 42%);
  background: rgb(240 201 106 / 10%);
}

.app-footer {
  margin-top: auto;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  background: #fafafa;
}

.footer-disclaimer {
  padding: 12px 20px 8px;
}

.footer-disclaimer p {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: #9ca3af;
  text-align: center;
}

.footer-contact {
  padding: 0 20px 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
}

.footer-contact a {
  color: #4f46e5;
  text-decoration: none;
  transition: color 0.2s;
}

.footer-contact a:hover {
  color: #7c3aed;
  text-decoration: underline;
}

.footer-contact .divider {
  color: #d1d5db;
}
</style>
