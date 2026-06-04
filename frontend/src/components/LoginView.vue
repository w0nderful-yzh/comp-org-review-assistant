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
    <div class="bg-grid"></div>

    <main class="login-stage">
      <section class="login-brief">
        <div class="brand-lockup">
          <div class="brand-mark">组</div>
          <div>
            <p class="eyebrow">Comp Org Studio</p>
            <h1>
              <span>计算机组成原理</span>
              <span>复习助手</span>
            </h1>
          </div>
        </div>
        <p class="brief-copy">
          把章节练习、错题、知识库和历年真题放在同一个复习工作台里。登录后从你上次停下的地方继续。
        </p>
        <div class="brief-strip">
          <span>Cache</span>
          <span>ALU</span>
          <span>指令系统</span>
          <span>模型机</span>
        </div>
      </section>

      <section class="login-card">
        <div class="card-header">
          <p class="eyebrow">{{ isRegister ? "Create Account" : "Welcome Back" }}</p>
          <h2>{{ isRegister ? "创建复习档案" : "进入复习台" }}</h2>
          <span>{{ isRegister ? "用 8 位序号注册，例如 2405xxxx" : "输入你的 8 位序号和密码" }}</span>
        </div>

        <form class="login-form" @submit.prevent="handleSubmit">
          <div class="form-field">
            <label>学生序号</label>
            <div class="input-wrap">
              <span class="input-hint">ID</span>
              <input
                v-model="studentId"
                type="text"
                placeholder="2405xxxx"
                maxlength="8"
                pattern="\d{8}"
                title="请输入 8 位数字序号，例如 24051234"
                inputmode="numeric"
                required
              />
            </div>
          </div>

          <div class="form-field">
            <label>密码</label>
            <div class="input-wrap">
              <span class="input-hint">PW</span>
              <input
                v-model="password"
                type="password"
                placeholder="至少 6 位"
                minlength="6"
                required
              />
            </div>
          </div>

          <div v-if="isRegister" class="form-field">
            <label>昵称 <span class="optional">可选</span></label>
            <div class="input-wrap">
              <span class="input-hint">NM</span>
              <input
                v-model="nickname"
                type="text"
                placeholder="显示在侧栏里的名字"
              />
            </div>
          </div>

          <div v-if="error" class="error-box">
            {{ error }}
          </div>

          <button type="submit" class="btn-submit" :disabled="loading">
            <span>{{ loading ? "处理中" : (isRegister ? "注册并进入" : "登录") }}</span>
            <span class="btn-arrow">→</span>
          </button>
        </form>

        <div class="card-footer">
          <span>{{ isRegister ? "已有账号？" : "还没有账号？" }}</span>
          <button class="btn-toggle" @click="toggleMode">
            {{ isRegister ? "切换到登录" : "创建新账号" }}
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.login-root {
  --login-ink: #24302f;
  --login-teal: #2d7c6f;
  --login-gold: #f0c96a;
  --login-paper: #f6f3ea;
  --login-rule: #d9dfd2;
  position: relative;
  min-height: 100vh;
  color: var(--login-ink);
  background: var(--login-paper);
  overflow: hidden;
  opacity: 0;
  transform: translateY(12px);
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

.login-root.mounted {
  opacity: 1;
  transform: translateY(0);
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgb(45 124 111 / 8%) 1px, transparent 1px),
    linear-gradient(90deg, rgb(45 124 111 / 8%) 1px, transparent 1px);
  background-size: 28px 28px;
}

.login-stage {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(280px, 520px) minmax(320px, 430px);
  gap: 28px;
  align-items: center;
  width: min(1040px, calc(100vw - 40px));
  min-height: 100vh;
  margin: 0 auto;
  padding: 40px 0;
}

.login-brief {
  display: grid;
  gap: 22px;
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  display: grid;
  width: 58px;
  height: 58px;
  place-items: center;
  border-radius: 8px;
  color: var(--login-ink);
  background: var(--login-gold);
  font-size: 24px;
  font-weight: 900;
}

.eyebrow {
  margin: 0;
  color: #68716d;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brand-lockup h1 {
  margin: 4px 0 0;
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  font-size: clamp(28px, 4vw, 42px);
  line-height: 1.12;
}

.brand-lockup h1 span {
  display: block;
}

.brief-copy {
  max-width: 500px;
  margin: 0;
  color: #56615e;
  font-size: 18px;
  line-height: 1.75;
}

.brief-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.brief-strip span {
  padding: 7px 10px;
  border: 1px solid var(--login-rule);
  border-radius: 8px;
  color: var(--login-teal);
  background: rgb(255 253 248 / 84%);
  font-size: 13px;
  font-weight: 900;
}

.login-card {
  display: grid;
  gap: 18px;
  padding: 24px;
  border: 1px solid var(--login-rule);
  border-radius: 8px;
  background: rgb(255 253 248 / 94%);
  box-shadow: 0 24px 70px rgb(36 48 47 / 12%);
}

.card-header h2 {
  margin: 5px 0 0;
  font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
  font-size: 30px;
  line-height: 1.18;
}

.card-header span {
  display: inline-block;
  margin-top: 8px;
  color: #67716d;
  font-size: 14px;
}

.login-form {
  display: grid;
  gap: 14px;
}

.form-field {
  display: grid;
  gap: 7px;
}

.form-field label {
  color: #4f5c59;
  font-size: 13px;
  font-weight: 900;
}

.optional {
  color: #8c9692;
  font-weight: 700;
}

.input-wrap {
  display: flex;
  align-items: center;
  min-height: 48px;
  border: 1px solid #cdd6ca;
  border-radius: 8px;
  background: #fffef9;
  transition: all 0.2s;
  overflow: hidden;
}

.input-wrap:focus-within {
  border-color: var(--login-teal);
  box-shadow: 0 0 0 3px rgb(45 124 111 / 12%);
}

.input-hint {
  display: inline-grid;
  width: 48px;
  height: 100%;
  min-height: 48px;
  place-items: center;
  color: var(--login-teal);
  background: #eef5ed;
  font-size: 12px;
  font-weight: 900;
  user-select: none;
  flex-shrink: 0;
}

.input-wrap input {
  flex: 1;
  min-width: 0;
  padding: 0 12px;
  background: transparent;
  border: none;
  outline: none;
  color: var(--login-ink);
  font-size: 15px;
  font-weight: 800;
}

.input-wrap input::placeholder {
  color: #8b9690;
  opacity: 1;
}

.error-box {
  padding: 10px 12px;
  border: 1px solid #e3b3ad;
  border-radius: 8px;
  color: #9d342f;
  background: #fff0ec;
  font-size: 13px;
  font-weight: 800;
}

.btn-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 48px;
  margin-top: 4px;
  background: var(--login-teal);
  color: #fff;
  -webkit-text-fill-color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 900;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-submit:hover {
  background: #236b5f;
}

.btn-submit:disabled {
  cursor: not-allowed;
  color: #f7fbf8;
  -webkit-text-fill-color: #f7fbf8;
  background: #6f948c;
}

.btn-arrow {
  font-size: 1.1rem;
  transition: transform 0.2s;
}

.btn-submit:hover .btn-arrow {
  transform: translateX(3px);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #67716d;
  font-size: 14px;
}

.btn-toggle {
  border: none;
  color: var(--login-teal);
  background: transparent;
  font-size: 14px;
  font-weight: 900;
  cursor: pointer;
  padding: 0;
}

.btn-toggle:hover {
  text-decoration: underline;
}

@media (max-width: 820px) {
  .login-stage {
    grid-template-columns: 1fr;
    align-content: center;
  }

  .login-brief {
    gap: 14px;
  }

  .brief-copy {
    font-size: 16px;
  }
}
</style>
