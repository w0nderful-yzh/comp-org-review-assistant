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
      <div v-for="row in chapterStats" :key="row.chapter_id" class="progress-row">
        <span>{{ row.chapter_title }}</span>
        <div class="progress-track">
          <div :style="{ width: percent(row.correct_rate) }" class="progress-fill"></div>
        </div>
        <strong>{{ percent(row.correct_rate) }}</strong>
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

defineExpose({ load });
</script>
