<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuth } from "../composables/useAuth";

const { register, login } = useAuth();

const isRegister = ref(false);
const studentId = ref("");
const password = ref("");
const nickname = ref("");
const error = ref("");
const loading = ref(false);
const mounted = ref(false);

onMounted(() => {
  setTimeout(() => (mounted.value = true), 100);
});

async function handleSubmit() {
  error.value = "";
  loading.value = true;
  try {
    if (isRegister.value) {
      await register(studentId.value, password.value, nickname.value || undefined);
    } else {
      await login(studentId.value, password.value);
    }
  } catch (e: any) {
    error.value = e.message || "操作失败";
  } finally {
    loading.value = false;
  }
}

function toggleMode() {
  isRegister.value = !isRegister.value;
  error.value = "";
}
</script>

<template>
  <div class="login-root" :class="{ mounted }">
    <!-- Animated background -->
    <div class="bg-grid"></div>
    <div class="bg-scanline"></div>
    <div class="bg-glow"></div>

    <div class="login-card">
      <!-- Header with ASCII art vibe -->
      <div class="card-header">
        <div class="chip-icon">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="8" y="8" width="32" height="32" rx="4" stroke="currentColor" stroke-width="2"/>
            <rect x="14" y="14" width="20" height="20" rx="2" stroke="currentColor" stroke-width="1.5"/>
            <!-- Pins top -->
            <line x1="16" y1="2" x2="16" y2="8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="24" y1="2" x2="24" y2="8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="32" y1="2" x2="32" y2="8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <!-- Pins bottom -->
            <line x1="16" y1="40" x2="16" y2="46" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="24" y1="40" x2="24" y2="46" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="32" y1="40" x2="32" y2="46" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <!-- Pins left -->
            <line x1="2" y1="16" x2="8" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="2" y1="24" x2="8" y2="24" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="2" y1="32" x2="8" y2="32" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <!-- Pins right -->
            <line x1="40" y1="16" x2="46" y2="16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="40" y1="24" x2="46" y2="24" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="40" y1="32" x2="46" y2="32" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <!-- Inner circuit -->
            <circle cx="20" cy="20" r="2" fill="currentColor"/>
            <circle cx="28" cy="28" r="2" fill="currentColor"/>
            <line x1="20" y1="22" x2="20" y2="26" stroke="currentColor" stroke-width="1.5"/>
            <line x1="22" y1="28" x2="26" y2="28" stroke="currentColor" stroke-width="1.5"/>
          </svg>
        </div>
        <h1>COMP<span class="accent">ORG</span></h1>
        <p class="subtitle">// 计算机组成原理 · 复习助手</p>
      </div>

      <!-- Terminal-style form -->
      <form class="login-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label>
            <span class="label-prefix">&gt;</span>
            STUDENT_ID
          </label>
          <div class="input-wrap">
            <span class="input-hint">0x</span>
            <input
              v-model="studentId"
              type="text"
              placeholder="24050823"
              maxlength="8"
              pattern="\d{8}"
              required
            />
          </div>
        </div>

        <div class="form-field">
          <label>
            <span class="label-prefix">&gt;</span>
            PASSWORD
          </label>
          <div class="input-wrap">
            <span class="input-hint">**</span>
            <input
              v-model="password"
              type="password"
              placeholder="••••••"
              minlength="6"
              required
            />
          </div>
        </div>

        <div v-if="isRegister" class="form-field">
          <label>
            <span class="label-prefix">&gt;</span>
            NICKNAME <span class="optional">// 可选</span>
          </label>
          <div class="input-wrap">
            <span class="input-hint">::</span>
            <input
              v-model="nickname"
              type="text"
              placeholder="给自己起个名字"
            />
          </div>
        </div>

        <div v-if="error" class="error-box">
          <span class="error-icon">✕</span>
          {{ error }}
        </div>

        <button type="submit" class="btn-submit" :disabled="loading">
          <span class="btn-text">{{ loading ? "PROCESSING..." : (isRegister ? "REGISTER" : "LOGIN") }}</span>
          <span class="btn-arrow">→</span>
        </button>
      </form>

      <div class="card-footer">
        <span class="footer-prompt">$</span>
        <span>{{ isRegister ? "已有账号？" : "没有账号？" }}</span>
        <button class="btn-toggle" @click="toggleMode">
          {{ isRegister ? "login --now" : "register --new" }}
        </button>
      </div>
    </div>

    <!-- Decorative binary rain -->
    <div class="binary-rain" aria-hidden="true">
      <span v-for="i in 12" :key="i" class="rain-col" :style="{ '--i': i }">
        {{ Array.from({length: 20}, () => Math.random() > 0.5 ? '1' : '0').join('') }}
      </span>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Space+Grotesk:wght@400;500;600&display=swap');

.login-root {
  --c-bg: #0a0e17;
  --c-card: #111827;
  --c-border: #1e293b;
  --c-accent: #00ff88;
  --c-accent-dim: #00cc6a;
  --c-accent-glow: rgba(0, 255, 136, 0.15);
  --c-cyan: #22d3ee;
  --c-text: #e2e8f0;
  --c-text-dim: #64748b;
  --c-error: #ff4757;
  --c-input-bg: #0d1117;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-body: 'Space Grotesk', system-ui, sans-serif;

  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--c-bg);
  overflow: hidden;
  font-family: var(--font-mono);
  color: var(--c-text);

  opacity: 0;
  transform: translateY(12px);
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.login-root.mounted {
  opacity: 1;
  transform: translateY(0);
}

/* ── Background effects ── */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 255, 136, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 255, 136, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: radial-gradient(ellipse 60% 60% at 50% 50%, black 20%, transparent 70%);
}

.bg-scanline {
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.08) 2px,
    rgba(0, 0, 0, 0.08) 4px
  );
  pointer-events: none;
}

.bg-glow {
  position: absolute;
  top: 30%;
  left: 50%;
  width: 600px;
  height: 600px;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, rgba(0, 255, 136, 0.06) 0%, transparent 60%);
  pointer-events: none;
}

/* ── Binary rain ── */
.binary-rain {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: space-around;
  pointer-events: none;
  opacity: 0.04;
  font-size: 14px;
  line-height: 1.6;
  color: var(--c-accent);
  overflow: hidden;
}

.rain-col {
  display: flex;
  flex-direction: column;
  animation: rain-fall 8s linear infinite;
  animation-delay: calc(var(--i) * -0.7s);
  writing-mode: vertical-lr;
  white-space: nowrap;
}

@keyframes rain-fall {
  from { transform: translateY(-100%); }
  to { transform: translateY(100vh); }
}

/* ── Card ── */
.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  margin: 1rem;
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: 2px;
  box-shadow:
    0 0 0 1px rgba(0, 255, 136, 0.05),
    0 4px 24px rgba(0, 0, 0, 0.4),
    0 0 120px rgba(0, 255, 136, 0.03);
}

/* ── Header ── */
.card-header {
  padding: 2rem 2rem 0;
  text-align: center;
}

.chip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: 1rem;
  color: var(--c-accent);
  animation: chip-pulse 3s ease-in-out infinite;
}

.chip-icon svg {
  width: 48px;
  height: 48px;
}

@keyframes chip-pulse {
  0%, 100% { opacity: 0.8; filter: drop-shadow(0 0 4px rgba(0, 255, 136, 0.3)); }
  50% { opacity: 1; filter: drop-shadow(0 0 12px rgba(0, 255, 136, 0.6)); }
}

.card-header h1 {
  font-family: var(--font-mono);
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: 0.15em;
  margin: 0;
  color: var(--c-text);
}

.card-header .accent {
  color: var(--c-accent);
  text-shadow: 0 0 20px rgba(0, 255, 136, 0.4);
}

.subtitle {
  margin: 0.5rem 0 0;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--c-text-dim);
  letter-spacing: 0.05em;
}

/* ── Form ── */
.login-form {
  padding: 1.5rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-field label {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--c-accent-dim);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.label-prefix {
  color: var(--c-cyan);
  margin-right: 0.3rem;
}

.optional {
  color: var(--c-text-dim);
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
}

.input-wrap {
  display: flex;
  align-items: center;
  background: var(--c-input-bg);
  border: 1px solid var(--c-border);
  border-radius: 2px;
  transition: all 0.2s;
  overflow: hidden;
}

.input-wrap:focus-within {
  border-color: var(--c-accent);
  box-shadow: 0 0 0 1px var(--c-accent-glow), 0 0 20px rgba(0, 255, 136, 0.08);
}

.input-hint {
  padding: 0 0 0 0.75rem;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--c-text-dim);
  user-select: none;
  flex-shrink: 0;
}

.input-wrap input {
  flex: 1;
  padding: 0.7rem 0.75rem 0.7rem 0.4rem;
  background: transparent;
  border: none;
  outline: none;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  color: var(--c-text);
  letter-spacing: 0.04em;
}

.input-wrap input::placeholder {
  color: var(--c-text-dim);
  opacity: 0.5;
}

/* ── Error ── */
.error-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.8rem;
  background: rgba(255, 71, 87, 0.08);
  border: 1px solid rgba(255, 71, 87, 0.2);
  border-radius: 2px;
  font-size: 0.8rem;
  color: var(--c-error);
}

.error-icon {
  font-weight: 700;
  flex-shrink: 0;
}

/* ── Submit button ── */
.btn-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  padding: 0.8rem 1.5rem;
  margin-top: 0.5rem;
  background: var(--c-accent);
  color: var(--c-bg);
  border: none;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}

.btn-submit::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transform: translateX(-100%);
  transition: transform 0.4s;
}

.btn-submit:hover::before {
  transform: translateX(100%);
}

.btn-submit:hover {
  background: var(--c-accent-dim);
  box-shadow: 0 0 24px rgba(0, 255, 136, 0.3);
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-arrow {
  font-size: 1.1rem;
  transition: transform 0.2s;
}

.btn-submit:hover .btn-arrow {
  transform: translateX(3px);
}

/* ── Footer ── */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 1rem 2rem 1.5rem;
  font-size: 0.75rem;
  color: var(--c-text-dim);
}

.footer-prompt {
  color: var(--c-accent);
  font-weight: 700;
}

.btn-toggle {
  background: none;
  border: none;
  color: var(--c-cyan);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  cursor: pointer;
  text-decoration: none;
  padding: 0;
  transition: all 0.2s;
}

.btn-toggle:hover {
  color: var(--c-accent);
  text-shadow: 0 0 8px rgba(34, 211, 238, 0.4);
}

/* ── Responsive ── */
@media (max-width: 480px) {
  .login-card {
    margin: 0.5rem;
  }

  .card-header,
  .login-form,
  .card-footer {
    padding-left: 1.25rem;
    padding-right: 1.25rem;
  }

  .card-header h1 {
    font-size: 1.6rem;
  }
}
</style>
