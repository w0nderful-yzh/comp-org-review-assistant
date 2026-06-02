<template>
  <div class="guide-overlay" @click.self="close">
    <div class="guide-modal">
      <div class="guide-header">
        <div class="hero-copy">
          <span class="hero-badge">DOUBLE MODE</span>
          <h2>今天复习，先开双形态</h2>
          <p class="subtitle">左手雪碧提神，右手巧克力补能，计组薄弱点一个都别想跑。</p>
        </div>
      </div>

      <div class="guide-content">
        <div class="guide-section">
          <h3><span class="section-icon">🎯</span> 今日作战目标</h3>
          <p>本系统负责把《计算机组成原理》的知识点、错题和练习记录串起来。你负责点开始，然后把 CPU、Cache、总线这些老朋友逐个拿下。</p>
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
          <h3><span class="section-icon">💡</span> 变身建议</h3>
          <ul class="notice-list">
            <li>状态一般时先做"只做原题"，像热身一样把基础肌肉叫醒</li>
            <li>想提速就切"标准练习"，原题和优质AI题一起上强度</li>
            <li>看到章节掌握度掉线，就去薄弱专项里补电</li>
            <li>错题本不是黑历史，是你的隐藏强化素材库</li>
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
          <span>开刷，变身</span>
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
  position: relative;
  min-height: 230px;
  overflow: hidden;
  border-bottom: 1px solid #e5e7eb;
  background:
    linear-gradient(180deg, rgba(5, 18, 14, 0.08), rgba(5, 18, 14, 0.78)),
    linear-gradient(90deg, rgba(5, 18, 14, 0.72), rgba(5, 18, 14, 0.08) 45%, rgba(5, 18, 14, 0.55)),
    url("/assets/guide-hero-combo.jpg") center 36% / cover;
}

.guide-header::after {
  position: absolute;
  inset: auto 0 0;
  height: 78px;
  content: "";
  background: linear-gradient(180deg, transparent, #ffffff);
  pointer-events: none;
}

.hero-copy {
  position: relative;
  z-index: 1;
  display: grid;
  max-width: 380px;
  gap: 8px;
  padding: 118px 24px 28px;
  color: #ffffff;
  text-align: left;
}

.hero-badge {
  display: inline-flex;
  width: fit-content;
  min-height: 26px;
  align-items: center;
  padding: 4px 9px;
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 999px;
  color: #fff3b0;
  background: rgba(0, 0, 0, 0.28);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.guide-header h2 {
  margin: 0;
  color: #ffffff;
  font-size: 28px;
  line-height: 1.12;
  text-shadow: 0 2px 16px rgba(0, 0, 0, 0.45);
}

.subtitle {
  max-width: 340px;
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  line-height: 1.55;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.45);
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
  background: linear-gradient(135deg, #0f8f4e, #5a2a16);
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
  box-shadow: 0 4px 12px rgba(15, 143, 78, 0.36);
}

@media (max-width: 560px) {
  .guide-header {
    min-height: 210px;
    background-position: center 24%;
  }

  .hero-copy {
    padding: 104px 18px 24px;
  }

  .guide-header h2 {
    font-size: 24px;
  }
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
