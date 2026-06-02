import { ref } from "vue";
import { api, type Chapter, type StatisticsOverview } from "../api/client";
import { useAuth } from "./useAuth";

// Module-level refs — shared across all components that call useSharedState()
const chapters = ref<Chapter[]>([]);
const overview = ref<StatisticsOverview | null>(null);

export function useSharedState() {
  const { isAuthenticated } = useAuth();

  async function refreshAll() {
    if (!isAuthenticated.value) return;
    try {
      // Load chapters and overview independently so one failure doesn't block the other
      const [chapterResult, overviewResult] = await Promise.allSettled([
        api.chapters(),
        api.overview(),
      ]);
      if (chapterResult.status === "fulfilled") {
        chapters.value = chapterResult.value;
      }
      if (overviewResult.status === "fulfilled") {
        overview.value = overviewResult.value;
      }
    } catch {
      // Silently fail if not authenticated
    }
  }

  function percent(value: number) {
    return `${Math.round(value * 100)}%`;
  }

  function typeLabel(type: string) {
    const labels: Record<string, string> = {
      single_choice: "单选",
      multiple_choice: "多选",
      true_false: "判断",
      fill_blank: "填空",
      calculation: "计算",
      question_group: "阅读理解",
    };
    return labels[type] ?? type;
  }

  function difficultyLabel(value: string) {
    return { easy: "基础", medium: "中等", hard: "提高" }[value] ?? value;
  }

  function sourceTagClass(value: string) {
    return `source-${value}`;
  }

  function sourceChapterName(chapterId: number) {
    const chapter = chapters.value.find((item) => item.id === chapterId);
    return chapter ? `第 ${chapter.order_index} 章` : `章节 ${chapterId}`;
  }

  return {
    chapters,
    overview,
    refreshAll,
    percent,
    typeLabel,
    difficultyLabel,
    sourceTagClass,
    sourceChapterName,
  };
}
