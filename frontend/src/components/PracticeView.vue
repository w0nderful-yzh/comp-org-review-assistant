<template>
  <section class="practice-page" :class="{ running: Boolean(session) }">
    <!-- AI题目生成加载提示 -->
    <div v-if="loading && practiceSourceScope === 'ai_new' && !session" class="ai-loading-overlay">
      <div class="ai-loading-content">
        <div class="ai-loading-spinner">
          <Sparkles :size="32" class="sparkle-icon" />
        </div>
        <h3>AI 正在生成题目...</h3>
        <p>根据当前章节内容，智能生成练习题目</p>
        <div class="ai-loading-progress">
          <div class="progress-bar"></div>
        </div>
        <small>预计需要 5-15 秒，请耐心等待</small>
      </div>
    </div>

    <div v-if="!session" class="practice-setup">
      <section class="practice-setup-main">
        <section class="study-dashboard" aria-label="今日学习状态">
          <div class="study-overview-card">
            <div class="today-status">
              <div>
                <p class="eyebrow">Today</p>
                <h3>今日学习状态</h3>
                <p>{{ todayAdviceText }}</p>
              </div>
              <div class="mastery-meter" :style="{ '--mastery': `${overallMastery}%` }">
                <strong>{{ overallMastery }}%</strong>
                <span>掌握度</span>
              </div>
            </div>

            <div class="study-metrics">
              <div class="metric-pill">
                <ClipboardList :size="16" />
                <span>作答</span>
                <strong>{{ overview?.total_answers ?? 0 }}</strong>
              </div>
              <div class="metric-pill">
                <Target :size="16" />
                <span>正确率</span>
                <strong>{{ percent(overview?.correct_rate ?? 0) }}</strong>
              </div>
              <div class="metric-pill">
                <AlertTriangle :size="16" />
                <span>薄弱章节</span>
                <strong>{{ weakChapterCount }}</strong>
              </div>
              <div class="metric-pill">
                <History :size="16" />
                <span>最近练习</span>
                <strong>{{ recentPracticeLabel }}</strong>
              </div>
            </div>
          </div>
        </section>

        <section class="daily-recommendation">
          <div class="recommendation-copy">
            <p class="eyebrow">Recommended</p>
            <h3>{{ recommendationTitle }}</h3>
            <p>{{ recommendationReason }}</p>
            <div class="recommendation-tags">
              <span>{{ recommendationAction }}</span>
              <span>预计 {{ recommendedMinutes }} 分钟</span>
            </div>
          </div>
          <button class="primary-button recommendation-button" :disabled="loading" @click="startRecommendedPractice">
            <Play :size="18" />
            <span>立即开始推荐训练</span>
          </button>
        </section>

        <section class="smart-practice-entry">
          <div class="section-title">
            <p class="eyebrow">Smart Practice</p>
            <h3>智能练习入口</h3>
          </div>
          <div class="smart-entry-grid">
            <button class="smart-entry-card" :class="{ selected: selectedSmartMode === 'sprint' }" @click="selectSmartPractice('sprint')">
              <Gauge :size="20" />
              <strong>考前冲刺</strong>
              <span>混合错题、高频题与薄弱章节。</span>
            </button>
            <button class="smart-entry-card" :class="{ selected: selectedSmartMode === 'weak' }" @click="selectSmartPractice('weak')">
              <Target :size="20" />
              <strong>薄弱专项</strong>
              <span>优先训练正确率较低的章节。</span>
            </button>
            <button class="smart-entry-card" :class="{ selected: selectedSmartMode === 'wrong' }" @click="selectSmartPractice('wrong')">
              <RotateCcw :size="20" />
              <strong>错题重刷</strong>
              <span>重新检查历史错题是否掌握。</span>
            </button>
            <button class="smart-entry-card" :class="{ selected: selectedSmartMode === 'mock' }" @click="selectSmartPractice('mock')">
              <Shuffle :size="20" />
              <strong>综合模拟</strong>
              <span>跨章节随机组题，检验整体状态。</span>
            </button>
          </div>
        </section>

        <div class="section-title compact-section-title">
          <p class="eyebrow">Chapters</p>
          <h3>章节练习入口</h3>
        </div>

        <div class="chapter-choice-grid">
          <button
            class="chapter-row final-row"
            :class="{ selected: practiceMode === 'final_review' && selectedSmartMode === null }"
            @click="selectFinalReview"
          >
            <div>
              <strong>总复习</strong>
              <span>跨章节随机抽题 · {{ totalQuestionCount }} 道可练</span>
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
            <div class="chapter-card-body">
              <div class="chapter-card-head">
                <strong>第 {{ chapter.order_index }} 章：{{ chapter.title }}</strong>
                <span class="chapter-status" :class="chapterStatusClass(chapter.id)">
                  {{ chapterStatusLabel(chapter.id) }}
                </span>
              </div>
              <span>{{ chapter.question_count }} 道题 · 已练 {{ chapterStat(chapter.id)?.answered ?? 0 }} 道</span>
              <div class="chapter-progress">
                <div class="progress-track">
                  <div
                    class="progress-fill"
                    :class="chapterStatusClass(chapter.id)"
                    :style="{ width: percent((chapterStat(chapter.id)?.mastery_score ?? 0) / 100) }"
                  ></div>
                </div>
                <b>{{ chapterStat(chapter.id)?.mastery_score ?? 0 }}分</b>
              </div>
              <div class="chapter-mini-stats">
                <span>正确率 {{ percent(chapterStat(chapter.id)?.correct_rate ?? 0) }}</span>
                <span>覆盖率 {{ percent(chapterStat(chapter.id)?.coverage ?? 0) }}</span>
              </div>
            </div>
            <ChevronRight :size="18" />
          </button>
        </div>

        <!-- 所有题目完成提示 -->
        <div v-if="allQuestionsCompleted" class="completion-notice">
          <div class="completion-icon">🎉</div>
          <h3>{{ allQuestionsCompleted.message }}</h3>
          <p class="completion-stats">
            已完成 {{ allQuestionsCompleted.answered_questions }} / {{ allQuestionsCompleted.total_questions }} 道题
          </p>
          <div class="completion-suggestions">
            <h4>建议：</h4>
            <ul>
              <li v-for="(suggestion, index) in allQuestionsCompleted.suggestions" :key="index">
                {{ suggestion }}
              </li>
            </ul>
          </div>
          <div class="completion-actions">
            <button class="primary-button" @click="startWrongPractice">
              <RotateCcw :size="16" />
              <span>错题复盘</span>
            </button>
            <button class="secondary-button" @click="restartPractice">
              <RefreshCw :size="16" />
              <span>再刷一遍</span>
            </button>
            <button class="ai-button" @click="practiceSourceScope = 'ai_new'; startPractice()">
              <Sparkles :size="16" />
              <span>AI加练</span>
            </button>
          </div>
        </div>
      </section>

      <aside class="practice-setup-side">
        <section class="practice-panel setup-card planner-card">
          <div class="planner-summary">
            <p class="eyebrow">Current Plan</p>
            <h3>{{ plannerTitle }}</h3>
            <p>{{ plannerDescription }}</p>
            <div class="planner-stat-grid">
              <span v-for="item in plannerStats" :key="item.label">
                {{ item.label }}
                <strong>{{ item.value }}</strong>
              </span>
            </div>
          </div>

          <div class="controls setup-controls">
            <label>
              <span>本组题量</span>
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
                <option value="calculation">计算题</option>
                <option value="question_group">阅读理解</option>
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
                <button :class="{ selected: practiceSourceScope === 'ai_pool' }" @click="practiceSourceScope = 'ai_pool'">
                  社区AI题库
                </button>
                <button :class="{ selected: practiceSourceScope === 'ai_new' }" @click="practiceSourceScope = 'ai_new'">
                  AI新题
                </button>
              </div>
            </div>
            <div class="source-description">
              <span v-if="practiceSourceScope === 'original_only'">只练习原始题目，不含AI生成题</span>
              <span v-else-if="practiceSourceScope === 'standard'">混合练习原始题和已验证的AI题</span>
              <span v-else-if="practiceSourceScope === 'ai_pool'">练习社区共享的优质AI题库</span>
              <span v-else-if="practiceSourceScope === 'ai_new'">实时生成全新AI题目进行练习</span>
            </div>
            <button class="primary-button" :disabled="loading" @click="startSelectedPractice">
              <template v-if="loading && practiceSourceScope === 'ai_new'">
                <Sparkles :size="18" class="generating-icon" />
                <span>生成中...</span>
              </template>
              <template v-else>
                <Play :size="18" />
                <span>开始{{ plannerButtonLabel }}</span>
              </template>
            </button>
          </div>
        </section>

        <section class="practice-panel setup-card">
          <div v-if="aiEnabled" class="ai-info-section">
            <div class="ai-info-header">
              <div class="ai-toggle-icon">
                <Sparkles :size="16" />
              </div>
              <div class="ai-toggle-text">
                <span>AI 出题已启用</span>
                <small>今日剩余 {{ aiDailyRemaining }} 道</small>
              </div>
            </div>
            <p class="ai-info-hint">选择"AI新题"模式即可实时生成AI题目</p>
          </div>
          <div v-else class="ai-disabled-notice">
            <Sparkles :size="14" />
            <span>AI 服务未配置，补充练习暂不可用</span>
          </div>
        </section>

        <section class="practice-panel setup-card history-card">
          <div class="history-head">
            <div>
              <p class="eyebrow">History</p>
              <h3>练习记录</h3>
            </div>
            <button class="icon-button small" title="刷新记录" @click="loadHistory">
              <History :size="16" />
            </button>
          </div>
          <div v-if="historyItems.length" class="history-list">
            <div v-for="item in historyItems" :key="item.id" class="history-row" role="button" tabindex="0" @click="openHistory(item.id)" @keyup.enter="openHistory(item.id)">
              <div>
                <strong>{{ historyTitle(item) }}</strong>
                <span>{{ formatDate(item.started_at) }} · {{ item.question_count }} 题</span>
              </div>
              <b>{{ item.submitted_at ? `${scoreText(item.score)} 分` : "未完成" }}</b>
              <Eye :size="16" />
              <button class="history-delete" title="删除记录" @click.stop="deleteHistoryItem(item.id)">
                <Trash2 :size="15" />
              </button>
            </div>
          </div>
          <div v-else class="compact-empty">
            暂无练习记录。
          </div>
        </section>
      </aside>
    </div>

    <div v-else class="practice-runner">
      <div class="runner-head">
        <div>
          <p class="eyebrow">{{ isReviewMode ? "Review" : "Practice" }}</p>
          <h3>{{ runnerTitle }}</h3>
          <span>{{ session.question_count }} 题{{ result ? ` · 得分 ${result.score.toFixed(1)} / ${result.total}` : "" }}</span>
        </div>
        <div class="runner-actions">
          <button class="secondary-button" @click="exitPractice">
            <X :size="16" />
            <span>{{ result || isReviewMode ? "返回选择" : "退出练习" }}</span>
          </button>
        </div>
      </div>

      <section v-if="error" class="notice error">
        {{ error }}
      </section>

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

      <div class="question-stack">
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
          <p v-if="question.type !== 'question_group'" class="stem">{{ question.stem }}</p>

          <div v-if="question.ai_status" class="ai-question-notice">
            本题由 AI 根据课程知识库生成，可能存在不严谨之处。欢迎反馈。
          </div>

          <div v-if="question.type === 'question_group'" class="reading-group">
            <div class="reading-material">
              {{ question.stem }}
            </div>
            <section
              v-for="(child, childIndex) in question.children"
              :id="`question-${child.id}`"
              :key="child.id"
              class="sub-question-card"
              :class="{ missing: unansweredQuestionIds.has(child.id) }"
            >
              <div class="question-meta compact-meta">
                <span>{{ index + 1 }}.{{ childIndex + 1 }}</span>
                <small>{{ typeLabel(child.type) }} · {{ difficultyLabel(child.difficulty) }}</small>
                <b class="source-chip" :class="sourceTagClass(child.source_type)">{{ child.source_label }}</b>
              </div>
              <p class="stem">{{ child.stem }}</p>

              <div v-if="child.type === 'single_choice'" class="options">
                <label v-for="option in child.options" :key="option.key" class="option-line">
                  <input v-model="answers[child.id]" type="radio" :disabled="answerLocked" :name="`q-${child.id}`" :value="option.key" />
                  <span>{{ option.key }}. {{ option.text }}</span>
                </label>
              </div>

              <div v-else-if="child.type === 'multiple_choice'" class="options">
                <label v-for="option in child.options" :key="option.key" class="option-line">
                  <input
                    type="checkbox"
                    :disabled="answerLocked"
                    :checked="multiAnswer(child.id).includes(option.key)"
                    @change="toggleMulti(child.id, option.key)"
                  />
                  <span>{{ option.key }}. {{ option.text }}</span>
                </label>
              </div>

              <div v-else-if="child.type === 'true_false'" class="segmented">
                <button :disabled="answerLocked" :class="{ selected: answers[child.id] === 'TRUE' }" @click="answers[child.id] = 'TRUE'">
                  对
                </button>
                <button :disabled="answerLocked" :class="{ selected: answers[child.id] === 'FALSE' }" @click="answers[child.id] = 'FALSE'">
                  错
                </button>
              </div>

              <div v-else-if="child.type === 'fill_blank' || child.type === 'cloze'" class="blank-grid">
                <input
                  v-for="blankIndex in blankCount(child)"
                  :key="blankIndex"
                  :value="blankAnswer(child.id, blankIndex - 1)"
                  class="text-answer"
                  :disabled="answerLocked"
                  :placeholder="`第 ${blankIndex} 空`"
                  @input="setBlankAnswer(child.id, blankIndex - 1, ($event.target as HTMLInputElement).value)"
                />
              </div>

              <textarea
                v-else
                v-model="answers[child.id]"
                class="long-answer"
                :disabled="answerLocked"
                placeholder="输入你的答案"
              />

              <div v-if="resultByQuestion[child.id]" class="answer-feedback">
                <strong :class="resultStatusClass(child.id)">
                  {{ resultStatusText(child.id) }}
                </strong>
                <span v-if="resultByQuestion[child.id].feedback">{{ resultByQuestion[child.id].feedback }}</span>
                <p>你的答案：{{ formatAnswer(answers[child.id]) }}</p>
                <p>参考答案：{{ formatAnswer(resultByQuestion[child.id].correct_answer) }}</p>
                <p v-if="resultByQuestion[child.id].explanation">{{ resultByQuestion[child.id].explanation }}</p>
              </div>
            </section>
          </div>

          <div v-else-if="question.type === 'single_choice'" class="options">
            <label v-for="option in question.options" :key="option.key" class="option-line">
              <input v-model="answers[question.id]" type="radio" :disabled="answerLocked" :name="`q-${question.id}`" :value="option.key" />
              <span>{{ option.key }}. {{ option.text }}</span>
            </label>
          </div>

          <div v-else-if="question.type === 'multiple_choice'" class="options">
            <label v-for="option in question.options" :key="option.key" class="option-line">
              <input
                type="checkbox"
                :disabled="answerLocked"
                :checked="multiAnswer(question.id).includes(option.key)"
                @change="toggleMulti(question.id, option.key)"
              />
              <span>{{ option.key }}. {{ option.text }}</span>
            </label>
          </div>

          <div v-else-if="question.type === 'true_false'" class="segmented">
            <button :disabled="answerLocked" :class="{ selected: answers[question.id] === 'TRUE' }" @click="answers[question.id] = 'TRUE'">
              对
            </button>
            <button :disabled="answerLocked" :class="{ selected: answers[question.id] === 'FALSE' }" @click="answers[question.id] = 'FALSE'">
              错
            </button>
          </div>

          <div v-else-if="question.type === 'fill_blank' || question.type === 'cloze'" class="blank-grid">
            <input
              v-for="blankIndex in blankCount(question)"
              :key="blankIndex"
              :value="blankAnswer(question.id, blankIndex - 1)"
              class="text-answer"
              :disabled="answerLocked"
              :placeholder="`第 ${blankIndex} 空`"
              @input="setBlankAnswer(question.id, blankIndex - 1, ($event.target as HTMLInputElement).value)"
            />
          </div>

          <textarea
            v-else
            v-model="answers[question.id]"
            class="long-answer"
            :disabled="answerLocked"
            placeholder="输入你的答案"
          />

          <div v-if="resultByQuestion[question.id]" class="answer-feedback">
            <strong :class="resultStatusClass(question.id)">
              {{ resultStatusText(question.id) }}
            </strong>
            <span v-if="resultByQuestion[question.id].feedback">{{ resultByQuestion[question.id].feedback }}</span>
            <p>你的答案：{{ formatAnswer(answers[question.id]) }}</p>
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

        <button v-if="!result && !isReviewMode" class="submit-button" :disabled="loading" @click="submitPractice">
          <CheckCircle2 :size="18" />
          <span>提交并批改</span>
        </button>
        <button v-else class="submit-button" @click="exitPractice">
          <ChevronRight :size="18" />
          <span>返回选择章节</span>
        </button>
      </div>
    </div>

    <!-- AI新题投票面板 -->
    <div v-if="showVotingPanel && votingQuestions.length > 0" class="voting-overlay">
      <div class="voting-panel">
        <div class="voting-header">
          <h3>🗳️ 为AI题目投票</h3>
          <p>点赞的题目将加入社区AI题库，帮助更多同学练习</p>
        </div>
        <div class="voting-list">
          <div v-for="(q, index) in votingQuestions" :key="q.id" class="voting-item">
            <div class="voting-index">{{ index + 1 }}</div>
            <div class="voting-stem">{{ q.stem.length > 60 ? q.stem.slice(0, 60) + '...' : q.stem }}</div>
            <div class="voting-buttons">
              <button
                class="vote-btn vote-like"
                :class="{ active: q.voted === 'like' }"
                @click="q.voted = q.voted === 'like' ? null : 'like'"
              >
                <ThumbsUp :size="16" />
                <span>赞</span>
              </button>
              <button
                class="vote-btn vote-dislike"
                :class="{ active: q.voted === 'dislike' }"
                @click="q.voted = q.voted === 'dislike' ? null : 'dislike'"
              >
                <ThumbsDown :size="16" />
                <span>踩</span>
              </button>
            </div>
          </div>
        </div>
        <div class="voting-actions">
          <button class="voting-submit" @click="submitVotes">
            提交投票 ({{ votingQuestions.filter(q => q.voted).length }}/{{ votingQuestions.length }})
          </button>
          <button class="voting-skip" @click="skipVoting">跳过</button>
        </div>
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
  ClipboardList,
  Eye,
  Gauge,
  History,
  Play,
  RefreshCw,
  RotateCcw,
  Shuffle,
  Sparkles,
  Target,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  X,
} from "@lucide/vue";
import { api, type AllQuestionsCompleted, type AnswerResult, type AnswerReviewResult, type ChapterStatistics, type FeedbackType, type FlagReason, type PracticeHistoryItem, type PracticeResult, type PracticeSession, type Question, type QuestionType, type SourceScope, type StudyRecommendation } from "../api/client";
import { useSharedState } from "../composables/useSharedState";

type DisplayResult = Omit<PracticeResult, "results"> & {
  results: Array<AnswerResult | AnswerReviewResult>;
};

type SmartPracticeMode = "sprint" | "weak" | "wrong" | "mock";

const emit = defineEmits<{
  refresh: [];
  modeChange: [mode: string];
}>();

const { chapters, overview, percent, typeLabel, difficultyLabel, sourceTagClass } = useSharedState();

const session = ref<PracticeSession | null>(null);
const result = ref<DisplayResult | null>(null);
const isReviewMode = ref(false);
const practiceMode = ref<"chapter" | "final_review" | "wrong_questions">("chapter");
const selectedSmartMode = ref<SmartPracticeMode | null>(null);
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
const historyItems = ref<PracticeHistoryItem[]>([]);
const chapterStats = ref<ChapterStatistics[]>([]);
const recommendations = ref<StudyRecommendation[]>([]);
const allQuestionsCompleted = ref<{
  message: string;
  total_questions: number;
  answered_questions: number;
  suggestions: string[];
} | null>(null);

const showVotingPanel = ref(false);
const votingQuestions = ref<Array<{ id: number; stem: string; voted: 'like' | 'dislike' | null }>>([]);

const aiForm = reactive({
  type: "" as QuestionType | "",
  difficulty: "medium" as "easy" | "medium" | "hard",
  count: 3,
  focus: "",
});

const setupTitle = computed(() => {
  if (practiceMode.value === "final_review") return "总复习";
  const ch = chapters.value.find((chapter) => chapter.id === selectedChapterId.value);
  return ch ? `第 ${ch.order_index} 章：${ch.title}` : "选择章节";
});

const runnerTitle = computed(() => {
  if (isReviewMode.value) return `练习 #${session.value?.id ?? ""} 回看`;
  if (practiceMode.value === "wrong_questions") return "错题重练";
  return setupTitle.value;
});

const aiChapterLabel = computed(() => {
  if (practiceMode.value === "final_review") return "跨章节随机生成";
  if (selectedChapterId.value) {
    const ch = chapters.value.find((c) => c.id === selectedChapterId.value);
    if (ch) return `第 ${ch.order_index} 章：${ch.title}`;
  }
  return "自动选择题目最少的章节";
});

const chapterStatsById = computed(() => new Map(chapterStats.value.map((item) => [item.chapter_id, item])));

const totalQuestionCount = computed(() => {
  const chapterTotal = chapters.value.reduce((sum, chapter) => sum + chapter.question_count, 0);
  if (chapterTotal) return chapterTotal;
  return chapterStats.value.reduce((sum, stat) => sum + stat.total_questions, 0);
});

const overallMastery = computed(() => {
  const withQuestions = chapterStats.value.filter((item) => item.total_questions > 0);
  const total = withQuestions.reduce((sum, item) => sum + item.total_questions, 0);
  if (!total) return 0;
  const weighted = withQuestions.reduce((sum, item) => sum + item.mastery_score * item.total_questions, 0);
  return Math.round(weighted / total);
});

const weakChapterCount = computed(() => chapterStats.value.filter((item) => item.answered > 0 && item.mastery_score < 50).length);

const primaryRecommendation = computed(() => {
  if (recommendations.value.length) return recommendations.value[0];
  const unpracticed = chapterStats.value.find((item) => item.answered === 0);
  if (!unpracticed) return null;
  return {
    chapter_id: unpracticed.chapter_id,
    chapter_title: unpracticed.chapter_title,
    answered: 0,
    correct_rate: 0,
    wrong_count: 0,
    reason: "还没有练习记录",
    action: "先做 5 道基础混合题建立基线",
    priority: 100,
  } satisfies StudyRecommendation;
});

const recentPracticeLabel = computed(() => {
  const latest = historyItems.value[0];
  if (!latest) return "暂无";
  if (latest.mode === "final_review") return "总复习";
  if (latest.mode === "wrong_questions") return "错题重练";
  const chapter = chapters.value.find((item) => item.id === latest.chapter_id);
  return chapter ? `第 ${chapter.order_index} 章` : "章节练习";
});

const todayAdviceText = computed(() => {
  const item = primaryRecommendation.value;
  if (item) return `建议优先复习「${item.chapter_title}」：${item.reason}。`;
  if ((overview.value?.total_answers ?? 0) === 0) return "先完成一组章节练习，系统会据此生成复习建议。";
  return "当前没有明显薄弱章节，可以做一次综合模拟保持题感。";
});

const recommendationTitle = computed(() => {
  const item = primaryRecommendation.value;
  return item ? `${item.chapter_title}专项训练` : "综合模拟训练";
});

const recommendationReason = computed(() => {
  const item = primaryRecommendation.value;
  return item ? item.reason : "最近数据较稳定，适合跨章节检验整体掌握情况。";
});

const recommendationAction = computed(() => primaryRecommendation.value?.action ?? "跨章节随机组题，检查复习盲区");
const recommendedMinutes = computed(() => (questionCount.value >= 10 ? 15 : 8));

const selectedChapter = computed(() => chapters.value.find((chapter) => chapter.id === selectedChapterId.value) ?? null);
const selectedChapterStat = computed(() => selectedChapterId.value ? chapterStat(selectedChapterId.value) : undefined);

const plannerTitle = computed(() => {
  if (selectedSmartMode.value === "sprint") return "考前冲刺";
  if (selectedSmartMode.value === "weak") return primaryRecommendation.value ? `${primaryRecommendation.value.chapter_title}薄弱专项` : "薄弱专项";
  if (selectedSmartMode.value === "wrong") return "错题重刷";
  if (selectedSmartMode.value === "mock") return "综合模拟";
  return setupTitle.value;
});

const plannerDescription = computed(() => {
  if (selectedSmartMode.value === "sprint") return "混合总复习题与薄弱章节，适合快速查漏补缺。";
  if (selectedSmartMode.value === "weak") return primaryRecommendation.value?.reason ?? "当前没有明显薄弱章节，可以先做综合模拟。";
  if (selectedSmartMode.value === "wrong") return `${overview.value?.wrong_question_count ?? 0} 道未掌握错题会优先进入本组练习。`;
  if (selectedSmartMode.value === "mock") return "跨章节随机组题，按模拟练习节奏检查整体掌握情况。";
  if (practiceMode.value === "final_review") return `跨章节随机抽题，当前题库共 ${totalQuestionCount.value} 道可练。`;
  if (selectedChapter.value) return selectedChapter.value.description ?? `${selectedChapter.value.question_count} 道题，按章节建立复习基线。`;
  return "选择一个章节或训练入口后开始练习。";
});

const plannerStats = computed(() => {
  if (selectedSmartMode.value === "wrong") {
    return [
      { label: "错题", value: `${overview.value?.wrong_question_count ?? 0}` },
      { label: "题量", value: `${questionCount.value}` },
    ];
  }
  if (practiceMode.value === "final_review") {
    return [
      { label: "题库", value: `${totalQuestionCount.value}` },
      { label: "正确率", value: percent(overview.value?.correct_rate ?? 0) },
    ];
  }
  return [
    { label: "已练", value: `${selectedChapterStat.value?.answered ?? 0}` },
    { label: "正确率", value: percent(selectedChapterStat.value?.correct_rate ?? 0) },
    { label: "掌握度", value: `${selectedChapterStat.value?.mastery_score ?? 0}分` },
  ];
});

const plannerButtonLabel = computed(() => {
  if (selectedSmartMode.value === "sprint") return "冲刺";
  if (selectedSmartMode.value === "weak") return "专项";
  if (selectedSmartMode.value === "wrong") return "错题";
  if (selectedSmartMode.value === "mock") return "模拟";
  if (practiceMode.value === "final_review") return "总复习";
  return "练习";
});

const answerLocked = computed(() => Boolean(result.value) || isReviewMode.value);
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

const resultByQuestion = computed<Record<number, AnswerResult | AnswerReviewResult>>(() => {
  const rows: Record<number, AnswerResult | AnswerReviewResult> = {};
  for (const item of result.value?.results ?? []) rows[item.question_id] = item;
  return rows;
});

function resetAnswerState() {
  result.value = null;
  isReviewMode.value = false;
  unansweredQuestionIds.value = new Set();
  flagPanelQuestionId.value = null;
  Object.keys(answers).forEach((key) => delete answers[Number(key)]);
}

function isCompletionResponse(response: PracticeSession | AllQuestionsCompleted): response is AllQuestionsCompleted {
  return "completed" in response && response.completed === true;
}

function selectChapter(chapterId: number) {
  selectedSmartMode.value = null;
  selectedChapterId.value = chapterId;
  practiceMode.value = "chapter";
  emit("modeChange", "chapter");
}

function selectFinalReview() {
  selectedSmartMode.value = null;
  practiceMode.value = "final_review";
  selectedChapterId.value = null;
  emit("modeChange", "final_review");
}

function selectSmartPractice(kind: SmartPracticeMode) {
  selectedSmartMode.value = kind;
  selectedQuestionType.value = "";
  practiceSourceScope.value = "standard";

  if (kind === "wrong") {
    practiceMode.value = "wrong_questions";
    selectedChapterId.value = null;
    questionCount.value = Math.max(questionCount.value, 10);
    emit("modeChange", "wrong_questions");
    return;
  }

  if (kind === "weak") {
    const item = primaryRecommendation.value;
    if (item) {
      selectedChapterId.value = item.chapter_id;
      practiceMode.value = "chapter";
      questionCount.value = Math.max(questionCount.value, 10);
      emit("modeChange", "chapter");
      return;
    }
  }

  practiceMode.value = "final_review";
  selectedChapterId.value = null;
  questionCount.value = kind === "sprint" ? 20 : 15;
  emit("modeChange", "final_review");
}

function chapterStat(chapterId: number) {
  return chapterStatsById.value.get(chapterId);
}

function chapterStatusLabel(chapterId: number) {
  const stat = chapterStat(chapterId);
  if (!stat || stat.answered === 0) return "未练习";
  if (stat.mastery_score >= 80) return "已掌握";
  if (stat.mastery_score >= 50) return "待巩固";
  return "薄弱";
}

function chapterStatusClass(chapterId: number) {
  const stat = chapterStat(chapterId);
  if (!stat || stat.answered === 0) return "status-new";
  if (stat.mastery_score >= 80) return "status-mastered";
  if (stat.mastery_score >= 50) return "status-review";
  return "status-weak";
}

function applyChapterPractice(chapterId: number, count = questionCount.value, sourceScope: SourceScope = "standard") {
  selectedSmartMode.value = null;
  selectedChapterId.value = chapterId;
  practiceMode.value = "chapter";
  questionCount.value = count;
  practiceSourceScope.value = sourceScope;
  selectedQuestionType.value = "";
  emit("modeChange", "chapter");
}

async function startRecommendedPractice() {
  const item = primaryRecommendation.value;
  if (item) {
    applyChapterPractice(item.chapter_id, item.answered === 0 ? 5 : 10, "standard");
  } else {
    selectFinalReview();
    questionCount.value = 12;
    practiceSourceScope.value = "standard";
  }
  await startPractice();
}

async function startSelectedPractice() {
  if (selectedSmartMode.value === "wrong") {
    await startWrongPractice();
    return;
  }

  await startPractice();
}

function multiAnswer(questionId: number) {
  return Array.isArray(answers[questionId]) ? (answers[questionId] as string[]) : [];
}

function toggleMulti(questionId: number, key: string) {
  if (answerLocked.value) return;
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
  if (answerLocked.value) return;
  const current = Array.isArray(answers[questionId]) ? [...(answers[questionId] as string[])] : [];
  current[index] = value;
  answers[questionId] = current;
}

function isAnswered(question: Question): boolean {
  if (question.type === "question_group") {
    return question.children.length > 0 && question.children.every((child) => isAnswered(child));
  }
  const answer = answers[question.id];
  if (question.type === "multiple_choice") return Array.isArray(answer) && answer.length > 0;
  if (question.type === "fill_blank" || question.type === "cloze") {
    if (!Array.isArray(answer)) return false;
    return answer.slice(0, blankCount(question)).every((item) => String(item ?? "").trim());
  }
  return String(answer ?? "").trim().length > 0;
}

function reviewDotClass(questionId: number) {
  const question = session.value?.questions.find((item) => item.id === questionId);
  const childResults = question?.type === "question_group"
    ? question.children.map((child) => resultByQuestion.value[child.id]).filter(Boolean)
    : [];
  const groupDone = question?.type === "question_group" && childResults.length === question.children.length && childResults.length > 0;
  const resultItem = resultByQuestion.value[questionId];
  return {
    answered: session.value?.questions.some((question) => question.id === questionId && isAnswered(question)),
    missing: unansweredQuestionIds.value.has(questionId),
    correct: resultItem?.is_correct === true || (groupDone && childResults.every((item) => item.is_correct === true)),
    wrong: resultItem?.is_correct === false || (groupDone && childResults.some((item) => item.is_correct === false)),
  };
}

function resultStatusClass(questionId: number) {
  const resultItem = resultByQuestion.value[questionId];
  return resultItem?.is_correct === true ? "ok" : resultItem?.is_correct === false ? "bad" : "";
}

function resultStatusText(questionId: number) {
  const resultItem = resultByQuestion.value[questionId];
  if (resultItem?.is_correct === true) return "正确";
  if (resultItem?.is_correct === false) return "需要复盘";
  return "未批改";
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

function scoreText(value: number | null) {
  return value === null ? "-" : value.toFixed(1);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function historyTitle(item: PracticeHistoryItem) {
  if (item.mode === "final_review") return "总复习";
  if (item.mode === "wrong_questions") return "错题重练";
  const chapter = chapters.value.find((row) => row.id === item.chapter_id);
  return item.chapter_title
    ? `第 ${chapter?.order_index ?? item.chapter_id} 章：${item.chapter_title}`
    : "章节练习";
}

function answerableQuestions(questions: Question[]) {
  return questions.flatMap((question) => question.type === "question_group" ? question.children : [question]);
}

function questionMap(questions: Question[]) {
  return new Map(answerableQuestions(questions).map((question) => [question.id, question]));
}

function isEmptyStoredAnswer(value: unknown) {
  return value == null || (typeof value === "object" && !Array.isArray(value) && Object.keys(value).length === 0);
}

function normalizeStoredAnswer(question: Question | undefined, value: unknown): string | string[] {
  if (!question || isEmptyStoredAnswer(value)) {
    return question?.type === "multiple_choice" || question?.type === "fill_blank" || question?.type === "cloze" ? [] : "";
  }
  if (Array.isArray(value)) return value.map((item) => String(item ?? ""));
  return String(value ?? "");
}

async function loadHistory() {
  historyItems.value = await api.practiceHistory();
}

async function loadStudySignals() {
  const [statsResult, recommendationResult] = await Promise.allSettled([
    api.chapterStats(),
    api.recommendations(),
  ]);
  if (statsResult.status === "fulfilled") chapterStats.value = statsResult.value;
  if (recommendationResult.status === "fulfilled") recommendations.value = recommendationResult.value;
}

async function deleteHistoryItem(sessionId: number) {
  await api.deletePractice(sessionId);
  historyItems.value = historyItems.value.filter((item) => item.id !== sessionId);
  if (session.value?.id === sessionId) {
    session.value = null;
    resetAnswerState();
  }
  await loadStudySignals();
  emit("refresh");
}

async function startPractice() {
  loading.value = true;
  error.value = "";
  allQuestionsCompleted.value = null;
  resetAnswerState();
  try {
    const response = await api.createPractice({
      mode: practiceMode.value,
      chapter_id: practiceMode.value === "chapter" ? selectedChapterId.value : null,
      question_count: questionCount.value,
      question_types: selectedQuestionType.value ? [selectedQuestionType.value] : undefined,
      source_scope: practiceSourceScope.value,
    });

    // 检查是否返回了"所有题目已完成"的响应
    if (isCompletionResponse(response)) {
      allQuestionsCompleted.value = {
        message: response.message,
        total_questions: response.total_questions,
        answered_questions: response.answered_questions,
        suggestions: response.suggestions,
      };
      session.value = null;
    } else {
      session.value = response as PracticeSession;
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "创建练习失败";
    session.value = null;
  } finally {
    loading.value = false;
  }
}

async function submitPractice() {
  if (!session.value) return;
  const answerable = answerableQuestions(session.value.questions);
  const missing = answerable.filter((question) => !isAnswered(question)).map((question) => question.id);
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
    const submitted = answerable.map((question) => ({
      question_id: question.id,
      user_answer:
        question.type === "fill_blank" || question.type === "cloze"
          ? Array.isArray(answers[question.id])
            ? answers[question.id]
            : [answers[question.id] ?? ""]
          : answers[question.id] ?? "",
    }));
    result.value = await api.submitPractice(session.value.id, submitted);
    await loadHistory();
    await loadStudySignals();
    emit("refresh");

    // 如果是AI新题模式，显示投票面板
    if (practiceSourceScope.value === "ai_new" && session.value) {
      const aiQuestions = session.value.questions.filter(q => q.source_type === "ai");
      if (aiQuestions.length > 0) {
        votingQuestions.value = aiQuestions.map(q => ({
          id: q.id,
          stem: q.stem,
          voted: null,
        }));
        showVotingPanel.value = true;
      }
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "提交失败";
  } finally {
    loading.value = false;
  }
}

async function startWrongPractice() {
  loading.value = true;
  error.value = "";
  resetAnswerState();
  try {
    const response = await api.createPractice({
      mode: "wrong_questions",
      question_count: questionCount.value || 10,
      source_scope: practiceSourceScope.value,
    });
    if (isCompletionResponse(response)) {
      allQuestionsCompleted.value = {
        message: response.message,
        total_questions: response.total_questions,
        answered_questions: response.answered_questions,
        suggestions: response.suggestions,
      };
      session.value = null;
      return;
    }
    session.value = response;
    practiceMode.value = "wrong_questions";
    selectedChapterId.value = session.value.chapter_id;
    emit("modeChange", "wrong_questions");
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    error.value = err instanceof Error ? err.message : "创建错题练习失败";
    session.value = null;
  } finally {
    loading.value = false;
  }
}

function restartPractice() {
  allQuestionsCompleted.value = null;
  startPractice();
}

async function submitVotes() {
  const likedQuestions = votingQuestions.value.filter(q => q.voted === 'like');
  for (const q of likedQuestions) {
    try {
      await api.submitFeedback(q.id, 'helpful');
    } catch {
      // 忽略单个投票失败
    }
  }
  showVotingPanel.value = false;
  votingQuestions.value = [];
}

function skipVoting() {
  showVotingPanel.value = false;
  votingQuestions.value = [];
}

async function openHistory(sessionId: number) {
  loading.value = true;
  error.value = "";
  resetAnswerState();
  try {
    const review = await api.reviewPractice(sessionId);
    practiceMode.value = review.mode as typeof practiceMode.value;
    selectedChapterId.value = review.chapter_id;
    session.value = {
      id: review.id,
      mode: review.mode,
      chapter_id: review.chapter_id,
      question_count: review.question_count,
      score: review.score,
      started_at: review.started_at,
      submitted_at: review.submitted_at,
      questions: review.questions,
    };
    const questionsById = questionMap(review.questions);
    for (const item of review.results) {
      answers[item.question_id] = normalizeStoredAnswer(questionsById.get(item.question_id), item.user_answer);
    }
    if (review.submitted_at) {
      result.value = {
        session_id: review.id,
        score: review.score ?? 0,
        total: review.results.length,
        results: review.results,
      };
      isReviewMode.value = true;
    } else {
      result.value = null;
      isReviewMode.value = false;
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    error.value = err instanceof Error ? err.message : "打开练习记录失败";
    session.value = null;
  } finally {
    loading.value = false;
  }
}

async function exitPractice() {
  session.value = null;
  resetAnswerState();
  await loadHistory();
  await loadStudySignals();
  emit("refresh");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function generateAiQuestions() {
  aiLoading.value = true;
  aiMessage.value = "";
  try {
    const result = await api.createAiQuestionDrafts({
      chapter_id: practiceMode.value === "chapter" ? selectedChapterId.value : undefined,
      question_types: aiForm.type ? [aiForm.type] : undefined,
      difficulty: aiForm.difficulty,
      count: aiForm.count,
      focus: aiForm.focus.trim() || null,
    });
    aiMessage.value = `已生成 ${result.created} 道AI题，切换到"AI新题"模式即可练习`;
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
  await loadHistory();
  await loadStudySignals();
});

defineExpose({ startWrongPractice, selectedChapterId });
</script>

<style scoped>
.study-dashboard,
.daily-recommendation,
.smart-practice-entry {
  margin-bottom: 14px;
}

.study-dashboard {
  min-width: 0;
}

.study-overview-card,
.daily-recommendation,
.smart-entry-card {
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: var(--panel);
  box-shadow: 0 10px 28px rgb(36 48 47 / 6%);
}

.study-overview-card {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(360px, 0.95fr);
  gap: 14px;
  padding: 16px;
}

.today-status {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.today-status h3,
.daily-recommendation h3 {
  margin: 4px 0 8px;
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  font-size: 22px;
  line-height: 1.2;
}

.today-status p,
.daily-recommendation p {
  margin: 0;
  color: var(--muted);
  line-height: 1.55;
}

.mastery-meter {
  --mastery: 0%;
  display: grid;
  width: 96px;
  aspect-ratio: 1;
  flex: 0 0 auto;
  place-items: center;
  align-content: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, var(--panel) 0 58%, transparent 59%),
    conic-gradient(var(--teal) var(--mastery), #e4eadd 0);
}

.mastery-meter strong {
  font-size: 24px;
  line-height: 1;
}

.mastery-meter span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
}

.study-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  align-content: center;
}

.metric-pill {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  min-height: 42px;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border: 1px solid var(--rule);
  border-radius: 8px;
  color: var(--ink);
  background: #fffef9;
}

.metric-pill svg {
  color: var(--teal);
}

.metric-pill span {
  overflow: hidden;
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-pill strong {
  font-size: 17px;
  line-height: 1.1;
  text-align: right;
  white-space: nowrap;
}

.daily-recommendation {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 16px;
  background:
    linear-gradient(135deg, rgb(240 201 106 / 18%), transparent 42%),
    var(--panel);
}

.recommendation-copy {
  min-width: 0;
}

.recommendation-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.recommendation-tags span {
  min-height: 28px;
  padding: 5px 10px;
  border: 1px solid #d7e1d5;
  border-radius: 999px;
  color: #41504c;
  background: #f7f9f3;
  font-size: 12px;
  font-weight: 900;
}

.recommendation-button {
  flex: 0 0 auto;
}

.smart-practice-entry {
  padding-top: 2px;
}

.smart-entry-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.smart-entry-card {
  display: grid;
  min-height: 122px;
  align-content: start;
  gap: 9px;
  padding: 14px;
  color: var(--ink);
  text-align: left;
}

.smart-entry-card:hover {
  border-color: var(--teal);
  transform: translateY(-1px);
}

.smart-entry-card.selected {
  border-color: var(--teal);
  background: #f3faf7;
  box-shadow: inset 4px 0 0 var(--teal), 0 10px 28px rgb(36 48 47 / 6%);
}

.smart-entry-card svg {
  color: var(--teal);
}

.smart-entry-card strong {
  font-size: 16px;
}

.smart-entry-card span {
  color: var(--muted);
  font-size: 13px;
  line-height: 1.45;
}

.compact-section-title {
  margin-top: 4px;
}

.planner-card {
  display: grid;
  gap: 14px;
}

.planner-summary {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid #d7e1d5;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgb(45 124 111 / 8%), transparent 56%),
    #fffef9;
}

.planner-summary h3 {
  margin: 0;
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  font-size: 24px;
  line-height: 1.2;
}

.planner-summary p {
  margin: 0;
  color: var(--muted);
  line-height: 1.55;
}

.planner-stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.planner-stat-grid span {
  display: grid;
  gap: 4px;
  min-height: 54px;
  padding: 9px;
  border: 1px solid var(--rule);
  border-radius: 8px;
  color: var(--muted);
  background: #f7f9f3;
  font-size: 12px;
  font-weight: 800;
}

.planner-stat-grid strong {
  overflow-wrap: anywhere;
  color: var(--ink);
  font-size: 18px;
  line-height: 1.1;
}

.chapter-card-body {
  width: 100%;
  min-width: 0;
}

.chapter-card-head {
  display: flex !important;
  grid-template-columns: none !important;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px !important;
}

.chapter-status {
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px !important;
  font-weight: 900;
  white-space: nowrap;
}

.chapter-progress {
  display: grid !important;
  grid-template-columns: minmax(80px, 1fr) auto;
  gap: 10px !important;
  align-items: center;
  margin-top: 8px;
}

.chapter-progress b {
  color: var(--teal);
  font-size: 13px;
  white-space: nowrap;
}

.chapter-mini-stats {
  display: flex !important;
  flex-wrap: wrap;
  gap: 8px !important;
  margin-top: 8px;
}

.chapter-mini-stats span {
  font-size: 12px;
  font-weight: 800;
}

.status-mastered {
  color: #16734e !important;
  background: #e8f5ed !important;
}

.status-review {
  color: #8a6417 !important;
  background: #fff3c7 !important;
}

.status-weak {
  color: #9a2f2f !important;
  background: #fff0ef !important;
}

.status-new {
  color: #55615d !important;
  background: #eef1ea !important;
}

.progress-fill.status-mastered {
  background: #2f9c62;
}

.progress-fill.status-review {
  background: #d59c2b;
}

.progress-fill.status-weak {
  background: #c85852;
}

.progress-fill.status-new {
  background: #a9b1a7;
}

@media (max-width: 1180px) {
  .study-overview-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .study-metrics,
  .smart-entry-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .daily-recommendation {
    align-items: stretch;
    flex-direction: column;
  }

  .recommendation-button {
    width: 100%;
  }
}

@media (max-width: 560px) {
  .today-status {
    align-items: flex-start;
    flex-direction: column;
  }

  .study-metrics,
  .smart-entry-grid,
  .planner-stat-grid {
    grid-template-columns: 1fr;
  }

  .chapter-card-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .chapter-progress {
    grid-template-columns: 1fr;
  }
}

.completion-notice {
  background: var(--panel);
  border: 1px solid var(--rule);
  border-radius: 12px;
  padding: 2rem;
  margin-top: 1.5rem;
  text-align: center;
}

.completion-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.completion-notice h3 {
  font-size: 1.25rem;
  margin: 0 0 0.5rem;
  color: var(--ink);
}

.completion-stats {
  color: var(--muted);
  font-size: 0.9rem;
  margin: 0 0 1.5rem;
}

.completion-suggestions {
  text-align: left;
  background: rgba(45, 124, 111, 0.05);
  border-radius: 8px;
  padding: 1rem 1.5rem;
  margin-bottom: 1.5rem;
}

.completion-suggestions h4 {
  font-size: 0.9rem;
  margin: 0 0 0.5rem;
  color: var(--teal);
}

.completion-suggestions ul {
  margin: 0;
  padding-left: 1.5rem;
}

.completion-suggestions li {
  font-size: 0.85rem;
  color: var(--ink);
  margin-bottom: 0.25rem;
}

.completion-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  flex-wrap: wrap;
}

.completion-actions button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.2rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.primary-button {
  background: var(--teal);
  color: white;
  -webkit-text-fill-color: white;
  border: none;
}

.primary-button span,
.primary-button svg {
  color: white;
  -webkit-text-fill-color: white;
}

.primary-button:hover {
  background: #236b5f;
}

.secondary-button {
  background: transparent;
  color: var(--teal);
  -webkit-text-fill-color: var(--teal);
  border: 1px solid var(--teal);
}

.secondary-button span,
.secondary-button svg {
  color: var(--teal);
  -webkit-text-fill-color: var(--teal);
}

.secondary-button:hover {
  background: rgba(45, 124, 111, 0.1);
}

.ai-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
}

.ai-button:hover {
  opacity: 0.9;
}

.source-description {
  font-size: 0.75rem;
  color: var(--muted);
  margin-top: 0.25rem;
  min-height: 1rem;
}

/* AI信息区域 */
.ai-info-section {
  padding: 0.75rem;
}

.ai-info-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.ai-info-hint {
  font-size: 0.75rem;
  color: var(--muted);
  margin: 0.5rem 0 0;
}

/* 投票面板 */
.voting-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.voting-panel {
  background: var(--panel);
  border-radius: 12px;
  padding: 1.5rem;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.voting-header {
  margin-bottom: 1rem;
}

.voting-header h3 {
  margin: 0 0 0.5rem;
  font-size: 1.1rem;
}

.voting-header p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--muted);
}

.voting-list {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.voting-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 8px;
  border: 1px solid var(--rule);
}

.voting-index {
  font-weight: 700;
  color: var(--teal);
  font-size: 0.9rem;
  min-width: 1.5rem;
}

.voting-stem {
  flex: 1;
  font-size: 0.85rem;
  line-height: 1.4;
}

.voting-buttons {
  display: flex;
  gap: 0.5rem;
}

.vote-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.2s;
  background: transparent;
  border: 1px solid var(--rule);
}

.vote-btn:hover {
  background: rgba(0, 0, 0, 0.05);
}

.vote-btn.vote-like.active {
  background: #f0fdf4;
  border-color: #22c55e;
  color: #16a34a;
}

.vote-btn.vote-dislike.active {
  background: #fef2f2;
  border-color: #ef4444;
  color: #dc2626;
}

.voting-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
}

.voting-submit {
  padding: 0.6rem 1.5rem;
  background: var(--teal);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
}

.voting-submit:hover {
  background: #236b5f;
}

.voting-skip {
  padding: 0.6rem 1.5rem;
  background: transparent;
  color: var(--muted);
  border: 1px solid var(--rule);
  border-radius: 8px;
  cursor: pointer;
}

.voting-skip:hover {
  background: rgba(0, 0, 0, 0.05);
}

/* AI加载提示 */
.ai-loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.ai-loading-content {
  text-align: center;
  padding: 2rem;
}

.ai-loading-spinner {
  width: 80px;
  height: 80px;
  margin: 0 auto 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.4); }
  50% { transform: scale(1.05); box-shadow: 0 0 0 20px rgba(102, 126, 234, 0); }
}

.sparkle-icon {
  color: white;
  animation: sparkle 1.5s ease-in-out infinite;
}

@keyframes sparkle {
  0%, 100% { transform: rotate(0deg) scale(1); }
  25% { transform: rotate(-10deg) scale(1.1); }
  75% { transform: rotate(10deg) scale(1.1); }
}

.ai-loading-content h3 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  color: var(--ink);
}

.ai-loading-content p {
  margin: 0 0 1.5rem;
  color: var(--muted);
  font-size: 0.9rem;
}

.ai-loading-progress {
  width: 200px;
  height: 4px;
  background: var(--rule);
  border-radius: 2px;
  margin: 0 auto 1rem;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2, #667eea);
  background-size: 200% 100%;
  border-radius: 2px;
  animation: shimmer 2s linear infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.ai-loading-content small {
  color: var(--muted);
  font-size: 0.75rem;
}

/* 生成中按钮动画 */
.generating-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
