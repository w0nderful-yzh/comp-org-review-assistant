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

    <div class="chapter-stats">
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
import { api, type ChapterStatistics } from "../api/client";
import { useSharedState } from "../composables/useSharedState";

const { overview, percent } = useSharedState();

const chapterStats = ref<ChapterStatistics[]>([]);

async function load() {
  const stats = await api.chapterStats();
  chapterStats.value = stats;
}

defineExpose({ load });
</script>
