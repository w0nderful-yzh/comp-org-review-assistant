<template>
  <div class="guide-overlay" @click.self="close">
    <div class="guide-modal">
      <div class="guide-header">
        <div class="header-icon">📖</div>
        <h2>欢迎使用计组复习助手</h2>
        <p class="subtitle">使用指南与注意事项</p>
      </div>

      <div class="guide-content">
        <div class="guide-section">
          <h3><span class="section-icon">🎯</span> 系统功能</h3>
          <p>本系统帮助你高效复习《计算机组成原理》，提供智能练习和学习统计功能。</p>
        </div>

        <div class="guide-section">
          <h3><span class="section-icon">📝</span> 四种练习模式</h3>
          <div class="mode-grid">
            <div class="mode-card">
              <div class="mode-icon">📚</div>
              <div class="mode-name">只做原题</div>
              <div class="mode-desc">仅练习原始题库中的题目</div>
            </div>
            <div class="mode-card">
              <div class="mode-icon">⭐</div>
              <div class="mode-name">标准练习</div>
              <div class="mode-desc">原题 + 已验证的AI好题</div>
            </div>
            <div class="mode-card">
              <div class="mode-icon">👥</div>
              <div class="mode-name">社区AI题库</div>
              <div class="mode-desc">社区用户共创的AI题目</div>
            </div>
            <div class="mode-card">
              <div class="mode-icon">✨</div>
              <div class="mode-name">AI新题</div>
              <div class="mode-desc">实时生成全新AI题目</div>
            </div>
          </div>
        </div>

        <div class="guide-section">
          <h3><span class="section-icon">⚠️</span> 重要说明</h3>
          <ul class="notice-list">
            <li>
              <span class="notice-icon">🔢</span>
              <span><strong>AI生成限制</strong>：每日最多生成 <strong>50</strong> 道AI题目</span>
            </li>
            <li>
              <span class="notice-icon">🔄</span>
              <span><strong>题目用尽</strong>：当题库题目全部完成时，可选择错题复盘、再刷一遍或AI加练</span>
            </li>
            <li>
              <span class="notice-icon">👍</span>
              <span><strong>社区贡献</strong>：完成AI新题后可为题目点赞/踩，优质题目将进入社区题库</span>
            </li>
            <li>
              <span class="notice-icon">💾</span>
              <span><strong>进度保存</strong>：答题进度会自动保存，可随时继续练习</span>
            </li>
          </ul>
        </div>

        <div class="guide-section tip-section">
          <h3><span class="section-icon">💡</span> 学习建议</h3>
          <ul class="notice-list">
            <li>建议先完成"只做原题"模式，熟悉基础知识点</li>
            <li>使用"标准练习"巩固知识，包含社区验证的优质AI题</li>
            <li>关注学习统计中的章节掌握度，查漏补缺</li>
            <li>定期进行错题复盘，强化薄弱环节</li>
          </ul>
        </div>
      </div>

      <div class="guide-disclaimer">
        <h4>📋 免责声明</h4>
        <p>本系统知识库从 HDU 教学课件中提取，仅供学习参考使用。系统内容可能存在疏漏或偏差，不保证与教材完全一致。AI 生成的题目基于大语言模型，可能存在错误或不准确之处，请结合教材和课堂内容进行判断。本系统不构成任何形式的考试承诺或成绩保证，使用者应自行承担使用风险。如有疑问，请以任课教师的讲解和官方教材为准。</p>
      </div>

      <div class="guide-footer">
        <label class="dont-show">
          <input type="checkbox" v-model="dontShowAgain" />
          <span>下次不再显示</span>
        </label>
        <button class="start-btn" @click="close">
          <span>开始学习</span>
          <span class="btn-arrow">→</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const dontShowAgain = ref(false);

const close = () => {
  if (dontShowAgain.value) {
    localStorage.setItem('hideGuide', 'true');
  }
  emit('close');
};
</script>

<style scoped>
.guide-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
}

.guide-modal {
  background: #ffffff;
  border-radius: 16px;
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  animation: slideUp 0.3s ease;
}

.guide-header {
  text-align: center;
  padding: 24px 24px 16px;
  border-bottom: 1px solid #e5e7eb;
}

.header-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.guide-header h2 {
  margin: 0;
  font-size: 22px;
  color: #1f2937;
}

.subtitle {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.guide-content {
  padding: 20px 24px;
}

.guide-section {
  margin-bottom: 20px;
}

.guide-section:last-child {
  margin-bottom: 0;
}

.guide-section h3 {
  margin: 0 0 12px;
  font-size: 16px;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-icon {
  font-size: 18px;
}

.guide-section p {
  margin: 0;
  color: #4b5563;
  font-size: 14px;
  line-height: 1.6;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.mode-card {
  background: #f9fafb;
  border-radius: 10px;
  padding: 14px;
  text-align: center;
  border: 1px solid #e5e7eb;
}

.mode-icon {
  font-size: 28px;
  margin-bottom: 6px;
}

.mode-name {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.mode-desc {
  font-size: 12px;
  color: #6b7280;
}

.notice-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.notice-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 0;
  font-size: 14px;
  color: #4b5563;
  line-height: 1.5;
}

.notice-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 2px;
}

.notice-list strong {
  color: #1f2937;
}

.tip-section {
  background: linear-gradient(135deg, #eff6ff, #f0fdf4);
  border-radius: 12px;
  padding: 16px;
  margin-top: 4px;
  border: 1px solid #dbeafe;
}

.guide-disclaimer {
  padding: 14px 24px;
  background: #fefce8;
  border-top: 1px solid #e5e7eb;
}

.guide-disclaimer h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #92400e;
}

.guide-disclaimer p {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: #78350f;
}

.guide-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-top: 1px solid #e5e7eb;
}

.dont-show {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #6b7280;
}

.dont-show input {
  cursor: pointer;
}

.start-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.start-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.4);
}

.btn-arrow {
  transition: transform 0.2s;
}

.start-btn:hover .btn-arrow {
  transform: translateX(4px);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>
