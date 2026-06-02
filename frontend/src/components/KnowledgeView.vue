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

      <section class="courseware-card">
        <div>
          <p class="eyebrow">Courseware PDF</p>
          <h3>{{ currentChapter ? `第 ${currentChapter.order_index} 章课件` : "课程课件" }}</h3>
          <span>{{ currentChapter?.title ?? "选择章节后查看对应课件" }}</span>
        </div>
        <div class="courseware-actions">
          <button class="secondary-button" :disabled="pdfLoading || !currentChapter" @click="openCourseware">
            <BookOpen :size="16" />
            <span>{{ pdfPreviewUrl ? "重新载入" : "在线阅读" }}</span>
          </button>
          <button class="primary-button" :disabled="pdfLoading || !currentChapter" @click="downloadCourseware">
            <Download :size="16" />
            <span>下载 PDF</span>
          </button>
        </div>
        <p v-if="pdfError" class="courseware-error">{{ pdfError }}</p>
      </section>

      <div class="knowledge-point-list">
        <article v-for="point in knowledgePoints" :key="point.id" class="knowledge-point">
          <strong>{{ point.name }}</strong>
          <p>{{ point.summary }}</p>
        </article>
      </div>
    </div>

    <div class="knowledge-panel">
      <section v-if="pdfPreviewUrl" class="pdf-reader">
        <div class="pdf-reader-head">
          <div>
            <p class="eyebrow">PDF Reader</p>
            <h3>{{ currentChapter ? `第 ${currentChapter.order_index} 章课件` : "课件预览" }}</h3>
          </div>
          <button class="icon-button small" title="关闭预览" @click="closeCourseware">
            <X :size="16" />
          </button>
        </div>
        <iframe :src="pdfPreviewUrl" title="课程课件 PDF 预览"></iframe>
      </section>

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
import { computed, onBeforeUnmount, ref } from "vue";
import { BookOpen, Download, FileText, Search, X } from "@lucide/vue";
import { api, type KnowledgeChunk, type KnowledgePoint } from "../api/client";
import { useSharedState } from "../composables/useSharedState";

const { chapters } = useSharedState();

const knowledgeChapterId = ref(1);
const knowledgeQuery = ref("");
const knowledgePoints = ref<KnowledgePoint[]>([]);
const knowledgeChunks = ref<KnowledgeChunk[]>([]);
const knowledgeSearchResults = ref<KnowledgeChunk[]>([]);
const loading = ref(false);
const pdfLoading = ref(false);
const pdfPreviewUrl = ref("");
const pdfError = ref("");

const activeKnowledgeChunks = computed(() => (knowledgeQuery.value ? knowledgeSearchResults.value : knowledgeChunks.value));
const currentChapter = computed(() => chapters.value.find((chapter) => chapter.id === knowledgeChapterId.value) ?? null);

async function loadKnowledge() {
  loading.value = true;
  closeCourseware();
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

function coursewareFilename() {
  const chapter = currentChapter.value;
  return chapter ? `第${chapter.order_index}章-${chapter.title}-课件.pdf` : "课程课件.pdf";
}

function setPdfPreview(blob: Blob) {
  closeCourseware();
  pdfPreviewUrl.value = URL.createObjectURL(blob);
}

function closeCourseware() {
  if (pdfPreviewUrl.value) {
    URL.revokeObjectURL(pdfPreviewUrl.value);
    pdfPreviewUrl.value = "";
  }
}

async function openCourseware() {
  if (!currentChapter.value) return;
  pdfLoading.value = true;
  pdfError.value = "";
  try {
    const blob = await api.coursewarePdf(currentChapter.value.id);
    setPdfPreview(blob);
  } catch (err) {
    pdfError.value = err instanceof Error ? err.message : "课件读取失败";
  } finally {
    pdfLoading.value = false;
  }
}

async function downloadCourseware() {
  if (!currentChapter.value) return;
  pdfLoading.value = true;
  pdfError.value = "";
  try {
    const blob = await api.coursewarePdf(currentChapter.value.id, true);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = coursewareFilename();
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    pdfError.value = err instanceof Error ? err.message : "课件下载失败";
  } finally {
    pdfLoading.value = false;
  }
}

onBeforeUnmount(closeCourseware);

defineExpose({ load: loadKnowledge });
</script>
