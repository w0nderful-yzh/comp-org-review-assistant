<template>
  <section class="stats-grid">
    <article class="stat-card">
      <span>作答题数</span>
      <strong>{{ overview?.total_answers ?? 0 }}</strong>
    </article>
    <article class="stat-card">
      <span>正确率</span>
      <strong>{{ percent(overview?.correct_rate ?? 0) }}</strong>
    </article>
    <article class="stat-card">
      <span>未掌握错题</span>
      <strong>{{ overview?.wrong_question_count ?? 0 }}</strong>
    </article>

    <section class="recommendation-panel">
      <div class="section-title">
        <p class="eyebrow">Next Practice</p>
        <h3>下一步建议</h3>
      </div>
      <div v-if="recommendations.length" class="recommendation-list">
        <article v-for="item in recommendations" :key="item.chapter_id" class="recommendation-item">
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

    <section class="type-stats-panel">
      <div class="section-title">
        <p class="eyebrow">Question Types</p>
        <h3>题型表现</h3>
      </div>
      <div v-if="questionTypeStats.length" class="type-stat-list">
        <div v-for="row in questionTypeStats" :key="row.question_type" class="type-stat-row">
          <span>{{ typeLabel(row.question_type) }}</span>
          <div class="progress-track">
            <div :style="{ width: percent(row.correct_rate) }" class="progress-fill"></div>
          </div>
          <strong>{{ percent(row.correct_rate) }}</strong>
          <small>{{ row.answered }} 题</small>
        </div>
      </div>
      <div v-else class="compact-empty">
        暂无题型统计，完成一次练习后会生成。
      </div>
    </section>

    <div class="chapter-stats">
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
      <div v-for="row in chapterStats" :key="row.chapter_id" class="mastery-row">
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
              class="mastery-bar-fill"
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
import { ref } from "vue";
import { api, type ChapterStatistics, type QuestionTypeStatistics, type StudyRecommendation } from "../api/client";
import { useSharedState } from "../composables/useSharedState";

const { overview, percent, typeLabel } = useSharedState();

const chapterStats = ref<ChapterStatistics[]>([]);
const questionTypeStats = ref<QuestionTypeStatistics[]>([]);
const recommendations = ref<StudyRecommendation[]>([]);

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

function masteryClass(score: number): string {
  if (score >= 80) return "mastery-excellent";
  if (score >= 60) return "mastery-good";
  if (score >= 40) return "mastery-fair";
  return "mastery-weak";
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
  transition: width 0.3s ease;
}

.mastery-bar-fill.mastery-excellent { background: #22c55e; }
.mastery-bar-fill.mastery-good { background: #3b82f6; }
.mastery-bar-fill.mastery-fair { background: #f59e0b; }
.mastery-bar-fill.mastery-weak { background: #ef4444; }

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
</style>
