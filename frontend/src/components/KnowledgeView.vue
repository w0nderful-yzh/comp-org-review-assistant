<template>
  <section class="knowledge-layout">
    <div class="knowledge-panel">
      <div class="admin-filters">
        <label>
          <span>章节</span>
          <select v-model.number="knowledgeChapterId" @change="loadKnowledge">
            <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">
              第 {{ chapter.order_index }} 章：{{ chapter.title }}
            </option>
          </select>
        </label>
        <label>
          <span>检索</span>
          <input v-model="knowledgeQuery" placeholder="例如 Cache、CPI、寻址方式" @keyup.enter="searchKnowledge" />
        </label>
        <button class="primary-button" :disabled="loading" @click="searchKnowledge">
          <Search :size="18" />
          <span>搜索知识块</span>
        </button>
      </div>

      <div class="knowledge-summary">
        <strong>{{ knowledgePoints.length }}</strong>
        <span>个知识点</span>
        <strong>{{ knowledgeChunks.length }}</strong>
        <span>个知识块</span>
      </div>

      <div class="knowledge-point-list">
        <article v-for="point in knowledgePoints" :key="point.id" class="knowledge-point">
          <strong>{{ point.name }}</strong>
          <p>{{ point.summary }}</p>
        </article>
      </div>
    </div>

    <div class="knowledge-panel">
      <div class="section-title">
        <p class="eyebrow">{{ knowledgeQuery ? "Search Results" : "Chapter Context" }}</p>
        <h3>{{ knowledgeQuery ? `"${knowledgeQuery}"` : "章节知识块" }}</h3>
      </div>
      <article v-for="chunk in activeKnowledgeChunks" :key="chunk.id" class="knowledge-chunk">
        <div class="chunk-meta">
          <span>{{ chunk.chunk_id }}</span>
          <small>{{ chunk.source_file }}</small>
        </div>
        <strong>{{ chunk.title }}</strong>
        <p>{{ chunk.content }}</p>
      </article>
      <div v-if="!activeKnowledgeChunks.length" class="empty-state">
        <FileText :size="38" />
        <p>当前没有匹配的知识块。</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { FileText, Search } from "@lucide/vue";
import { api, type KnowledgeChunk, type KnowledgePoint } from "../api/client";
import { useSharedState } from "../composables/useSharedState";

const { chapters } = useSharedState();

const knowledgeChapterId = ref(1);
const knowledgeQuery = ref("");
const knowledgePoints = ref<KnowledgePoint[]>([]);
const knowledgeChunks = ref<KnowledgeChunk[]>([]);
const knowledgeSearchResults = ref<KnowledgeChunk[]>([]);
const loading = ref(false);

const activeKnowledgeChunks = computed(() => (knowledgeQuery.value ? knowledgeSearchResults.value : knowledgeChunks.value));

async function loadKnowledge() {
  loading.value = true;
  try {
    const [points, chunks] = await Promise.all([
      api.knowledgePoints(knowledgeChapterId.value),
      api.knowledgeChunks(knowledgeChapterId.value, 50),
    ]);
    knowledgePoints.value = points;
    knowledgeChunks.value = chunks;
    if (!knowledgeQuery.value) knowledgeSearchResults.value = [];
  } finally {
    loading.value = false;
  }
}

async function searchKnowledge() {
  if (!knowledgeQuery.value.trim()) {
    knowledgeSearchResults.value = [];
    await loadKnowledge();
    return;
  }
  loading.value = true;
  try {
    const result = await api.searchKnowledge({
      q: knowledgeQuery.value.trim(),
      chapter_id: knowledgeChapterId.value,
      limit: 12,
    });
    knowledgeSearchResults.value = result.items;
  } finally {
    loading.value = false;
  }
}

defineExpose({ load: loadKnowledge });
</script>
