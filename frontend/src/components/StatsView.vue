<template>
  <section class="stats-grid">
    <!-- Overview cards -->
    <article v-for="(card, i) in overviewCards" :key="card.label" class="stat-card card-reveal" :style="{ animationDelay: `${i * 0.06}s` }">
      <span>{{ card.label }}</span>
      <div class="stat-value-row">
        <div class="stat-ring-wrap">
          <svg viewBox="0 0 64 64">
            <circle class="stat-ring-bg" cx="32" cy="32" r="29" />
            <circle
              class="stat-ring-fill"
              :class="ringClass(card.pct)"
              cx="32" cy="32" r="29"
              :style="ringStyle(card.pct, i)"
            />
          </svg>
          <span class="stat-ring-label">{{ card.pct }}%</span>
        </div>
        <strong>{{ card.value }}</strong>
      </div>
    </article>

    <!-- Recommendations -->
    <section class="recommendation-panel card-reveal" style="animation-delay: 0.18s">
      <div class="section-title">
        <p class="eyebrow">Next Practice</p>
        <h3>下一步建议</h3>
      </div>
      <div v-if="recommendations.length" class="recommendation-list">
        <article v-for="(item, i) in recommendations" :key="item.chapter_id" class="recommendation-item card-reveal" :style="{ animationDelay: `${0.22 + i * 0.05}s` }">
          <div>
            <strong>第 {{ item.chapter_id }} 章：{{ item.chapter_title }}</strong>
            <p>{{ item.reason }} · {{ item.action }}</p>
          </div>
          <span>{{ percent(item.correct_rate) }}</span>
        </article>
      </div>
      <div v-else class="compact-empty">
        当前数据很干净，继续做标准练习保持手感。
      </div>
    </section>

    <!-- Question type stats -->
    <section class="type-stats-panel card-reveal" style="animation-delay: 0.24s">
      <div class="section-title">
        <p class="eyebrow">Question Types</p>
        <h3>题型表现</h3>
      </div>
      <div v-if="questionTypeStats.length" class="type-stat-list">
        <div v-for="row in questionTypeStats" :key="row.question_type" class="type-stat-row">
          <span>{{ typeLabel(row.question_type) }}</span>
          <div class="progress-track">
            <div :style="{ width: percent(row.correct_rate) }" class="progress-fill" :class="barClass(row.correct_rate)"></div>
          </div>
          <strong>{{ percent(row.correct_rate) }}</strong>
          <small>{{ row.answered }} 题</small>
        </div>
      </div>
      <div v-else class="compact-empty">
        暂无题型统计，完成一次练习后会生成。
      </div>
    </section>

    <!-- Chapter mastery -->
    <div class="chapter-stats card-reveal" style="animation-delay: 0.28s">
      <div class="section-title">
        <p class="eyebrow">Chapters</p>
        <h3>章节掌握</h3>
      </div>
      <div class="mastery-legend">
        <span class="legend-item"><span class="legend-dot mastery-excellent"></span> 优秀 ≥80</span>
        <span class="legend-item"><span class="legend-dot mastery-good"></span> 良好 ≥60</span>
        <span class="legend-item"><span class="legend-dot mastery-fair"></span> 一般 ≥40</span>
        <span class="legend-item"><span class="legend-dot mastery-weak"></span> 待加强 &lt;40</span>
      </div>
      <div v-for="(row, i) in chapterStats" :key="row.chapter_id" class="mastery-row card-reveal" :style="{ animationDelay: `${0.30 + i * 0.04}s` }">
        <div class="mastery-header">
          <span class="mastery-title">{{ row.chapter_title }}</span>
          <span class="mastery-score" :class="masteryClass(row.mastery_score)">
            {{ row.mastery_score }}分
          </span>
        </div>
        <div class="mastery-bar">
          <div class="mastery-bar-track">
            <div
              :style="{ width: percent(row.mastery_score / 100) }"
              class="mastery-bar-fill shimmer-fill"
              :class="masteryClass(row.mastery_score)"
            ></div>
          </div>
        </div>
        <div class="mastery-details">
          <span class="detail-item">
            <span class="detail-label">答题</span>
            <span class="detail-value">{{ row.answered }}/{{ row.total_questions }}</span>
          </span>
          <span class="detail-item">
            <span class="detail-label">正确率</span>
            <span class="detail-value">{{ percent(row.correct_rate) }}</span>
          </span>
          <span class="detail-item">
            <span class="detail-label">覆盖率</span>
            <span class="detail-value">{{ percent(row.coverage) }}</span>
          </span>
          <span class="detail-item" v-if="row.mastered_rate < 1">
            <span class="detail-label">错题掌握</span>
            <span class="detail-value">{{ percent(row.mastered_rate) }}</span>
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { api, type ChapterStatistics, type QuestionTypeStatistics, type StudyRecommendation } from "../api/client";
import { useSharedState } from "../composables/useSharedState";

const { overview, percent, typeLabel } = useSharedState();

const chapterStats = ref<ChapterStatistics[]>([]);
const questionTypeStats = ref<QuestionTypeStatistics[]>([]);
const recommendations = ref<StudyRecommendation[]>([]);

const RING_CIRCUMFERENCE = 2 * Math.PI * 29; // r=29

const overviewCards = computed(() => [
  { label: "作答题数", value: overview.value?.total_answers ?? 0, pct: 0 },
  { label: "正确率", value: percent(overview.value?.correct_rate ?? 0), pct: Math.round((overview.value?.correct_rate ?? 0) * 100) },
  { label: "未掌握错题", value: overview.value?.wrong_question_count ?? 0, pct: 0 },
]);

function ringStyle(pct: number, index: number) {
  const offset = RING_CIRCUMFERENCE * (1 - pct / 100);
  return {
    "--ring-circumference": String(RING_CIRCUMFERENCE),
    "--ring-offset": String(offset),
    animationDelay: `${0.3 + index * 0.08}s`,
  };
}

function ringClass(pct: number): string {
  if (pct >= 80) return "mastery-excellent";
  if (pct >= 60) return "mastery-good";
  if (pct >= 40) return "mastery-fair";
  return "mastery-weak";
}

function barClass(rate: number): string {
  if (rate >= 0.8) return "mastery-excellent";
  if (rate >= 0.6) return "mastery-good";
  if (rate >= 0.4) return "mastery-fair";
  return "mastery-weak";
}

function masteryClass(score: number): string {
  if (score >= 80) return "mastery-excellent";
  if (score >= 60) return "mastery-good";
  if (score >= 40) return "mastery-fair";
  return "mastery-weak";
}

async function load() {
  const [stats, typeStats, recommendationRows] = await Promise.all([
    api.chapterStats(),
    api.questionTypeStats(),
    api.recommendations(),
  ]);
  chapterStats.value = stats;
  questionTypeStats.value = typeStats;
  recommendations.value = recommendationRows;
}

defineExpose({ load });
</script>

<style scoped>
.mastery-legend {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  font-size: 0.75rem;
  color: var(--muted);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.mastery-excellent { background: #22c55e; }
.mastery-good { background: #3b82f6; }
.mastery-fair { background: #f59e0b; }
.mastery-weak { background: #ef4444; }

.mastery-row {
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--rule);
}

.mastery-row:last-child {
  border-bottom: none;
}

.mastery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.mastery-title {
  font-weight: 500;
  font-size: 0.9rem;
}

.mastery-score {
  font-weight: 700;
  font-size: 1rem;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
}

.mastery-score.mastery-excellent {
  color: #16a34a;
  background: #f0fdf4;
}

.mastery-score.mastery-good {
  color: #2563eb;
  background: #eff6ff;
}

.mastery-score.mastery-fair {
  color: #d97706;
  background: #fffbeb;
}

.mastery-score.mastery-weak {
  color: #dc2626;
  background: #fef2f2;
}

.mastery-bar {
  margin-bottom: 0.5rem;
}

.mastery-bar-track {
  height: 6px;
  background: var(--rule);
  border-radius: 3px;
  overflow: hidden;
}

.mastery-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

.mastery-bar-fill.mastery-excellent { background: #22c55e; }
.mastery-bar-fill.mastery-good { background: #3b82f6; }
.mastery-bar-fill.mastery-fair { background: #f59e0b; }
.mastery-bar-fill.mastery-weak { background: #ef4444; }

.shimmer-fill {
  position: relative;
}

.shimmer-fill::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent 0%, rgb(255 255 255 / 35%) 50%, transparent 100%);
  animation: shimmer 2s ease-in-out infinite;
}

.mastery-details {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
}

.detail-item {
  display: flex;
  gap: 0.25rem;
}

.detail-label {
  color: var(--muted);
}

.detail-value {
  font-weight: 500;
}

/* Overview stat cards with rings */
.stat-value-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.stat-value-row strong {
  font-size: 34px;
  white-space: nowrap;
}

.stat-ring-fill.mastery-excellent { stroke: #22c55e; }
.stat-ring-fill.mastery-good { stroke: #3b82f6; }
.stat-ring-fill.mastery-fair { stroke: #f59e0b; }
.stat-ring-fill.mastery-weak { stroke: #ef4444; }
.stat-ring-fill { stroke: #2d7c6f; }

.progress-fill.mastery-excellent { background: #22c55e; }
.progress-fill.mastery-good { background: #3b82f6; }
.progress-fill.mastery-fair { background: #f59e0b; }
.progress-fill.mastery-weak { background: #ef4444; }
</style>
