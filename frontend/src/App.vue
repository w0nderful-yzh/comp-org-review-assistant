<template>
  <div v-if="!isAuthenticated" class="auth-wrapper">
    <LoginView />
  </div>
  <main v-else class="app-shell" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <BinaryRain :opacity="0.07" :density="0.35" :speed="0.7" />
    <div ref="eggContainer" class="egg-container" />
    <GuideModal v-if="showGuide" @close="showGuide = false" />
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-main">
          <div
            class="brand-mark"
            :class="{ 'egg-spin': logoSpinning }"
            @click="clickLogo"
            title="点击有惊喜 ✨"
            role="button"
            tabindex="0"
          >{{ logoChar }}</div>
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
        <button :class="{ active: activeView === 'labExam' }" @click="switchView('labExam')">
          <Cpu :size="18" />
          <span>实验模拟</span>
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
          <p class="eyebrow phase-clickable" @click="cyclePhase" title="点击切换版本号 🏷️">{{ phaseLabel }}</p>
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
      <LabExamMockView v-else-if="activeView === 'labExam'" ref="labExamRef" />
      <WrongQuestionsView
        v-else-if="activeView === 'wrong'"
        ref="wrongRef"
        @start-wrong-practice="handleStartWrongPractice"
      />
      <StatsView v-else-if="activeView === 'stats'" ref="statsRef" />
      <KnowledgeView v-else-if="activeView === 'knowledge'" ref="knowledgeRef" />

      <footer class="app-footer">
        <div class="footer-fact">
          <span>💡</span>
          <span :key="factIndex" class="footer-fact-swap">{{ footerFacts[factIndex] }}</span>
        </div>
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
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import {
  BarChart3,
  BookOpen,
  ClipboardCheck,
  Cpu,
  FileText,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  RotateCcw,
} from "@lucide/vue";
import { useAuth } from "./composables/useAuth";
import { useSharedState } from "./composables/useSharedState";
import { useKeyboardEasterEgg, useLogoEasterEgg, spawnConfetti } from "./composables/useEasterEggs";
import BinaryRain from "./components/BinaryRain.vue";
import LoginView from "./components/LoginView.vue";
import GuideModal from "./components/GuideModal.vue";
import ExamMockView from "./components/ExamMockView.vue";
import LabExamMockView from "./components/LabExamMockView.vue";
import PracticeView from "./components/PracticeView.vue";
import WrongQuestionsView from "./components/WrongQuestionsView.vue";
import StatsView from "./components/StatsView.vue";
import KnowledgeView from "./components/KnowledgeView.vue";

const { isAuthenticated, user, logout, fetchUser } = useAuth();
const { chapters, overview, refreshAll, percent } = useSharedState();
const { logoChar, logoSpinning, clickLogo } = useLogoEasterEgg();

const activeView = ref<"practice" | "exam" | "labExam" | "wrong" | "stats" | "knowledge">("practice");
const practiceMode = ref<string>("chapter");
const error = ref("");
const showGuide = ref(false);
const sidebarCollapsed = ref(localStorage.getItem("comp-org-sidebar-collapsed") === "true");

const eggContainer = ref<HTMLDivElement | null>(null);
const factIndex = ref(0);
let factTimer: ReturnType<typeof setInterval> | null = null;

const PHASE_LABELS = [
  "Phase 1", "Phase 2", "Phase 3", "Phase 4",
  "Beta 0.1", "Alpha 0xDEAD", "Release Candidate",
  "流水线级", "多周期级", "超标量级", "VLIW级",
];
let phaseIdx = 0;
const phaseLabel = ref("Phase 1");

function cyclePhase() {
  phaseIdx = (phaseIdx + 1) % PHASE_LABELS.length;
  phaseLabel.value = PHASE_LABELS[phaseIdx];
}

const footerFacts = [
  "RISC-V 基础整数指令集只有 40 条指令… 但能构建出完整的操作系统。",
  "一个全加器由 5 个逻辑门组成，而一个 CPU 需要上万个。",
  "流水线并不会减少单条指令的执行时间，而是提高了吞吐率。",
  "Cache 命中的关键是局部性原理：时间局部性和空间局部性。",
  "冯·诺依曼架构的瓶颈在于处理器与内存之间的「单总线」。",
  "ALU 的核心是一个加法器，减法通过补码加法实现。",
  "超标量处理器每个时钟周期可以发射多条指令。",
  "多周期 CPU 中，load 指令通常需要最多的时钟周期。",
  "计算机组成原理 = 软硬件接口的艺术。",
  "「组原」是所有 CS 专业的基石，没有之一。",
];

const practiceRef = ref<InstanceType<typeof PracticeView> | null>(null);
const examRef = ref<InstanceType<typeof ExamMockView> | null>(null);
const labExamRef = ref<InstanceType<typeof LabExamMockView> | null>(null);
const wrongRef = ref<InstanceType<typeof WrongQuestionsView> | null>(null);
const statsRef = ref<InstanceType<typeof StatsView> | null>(null);
const knowledgeRef = ref<InstanceType<typeof KnowledgeView> | null>(null);

const viewTitle = computed(() => {
  if (activeView.value === "wrong") return "错题本";
  if (activeView.value === "exam") return "真题模拟";
  if (activeView.value === "labExam") return "计组实验模拟考试";
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
  else if (view === "labExam") labExamRef.value?.load();
  else if (view === "stats") statsRef.value?.load();
  else if (view === "knowledge") knowledgeRef.value?.load();
}

async function refreshCurrent() {
  if (activeView.value === "wrong") wrongRef.value?.load();
  else if (activeView.value === "exam") examRef.value?.load();
  else if (activeView.value === "labExam") labExamRef.value?.load();
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
    if (localStorage.getItem("hideGuide") !== "true") {
      showGuide.value = true;
    }
  }

  // Rotating footer facts
  factTimer = setInterval(() => {
    factIndex.value = (factIndex.value + 1) % footerFacts.length;
  }, 8000);
});

onUnmounted(() => {
  if (factTimer) clearInterval(factTimer);
});

useKeyboardEasterEgg((emoji, label) => {
  if (eggContainer.value) {
    spawnConfetti(eggContainer.value, emoji, label);
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

.egg-container {
  position: fixed;
  inset: 0;
  z-index: 9997;
  pointer-events: none;
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

.brand-mark {
  cursor: pointer;
  user-select: none;
  transition: box-shadow 0.3s ease, transform 0.2s ease;
}

.brand-mark:hover {
  box-shadow: 0 10px 28px rgb(240 201 106 / 32%);
  transform: scale(1.06);
}

.phase-clickable {
  cursor: pointer;
  user-select: none;
  transition: color 0.2s ease;
}

.phase-clickable:hover {
  color: var(--teal);
}
</style>
