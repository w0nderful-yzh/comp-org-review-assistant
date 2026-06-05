/**
 * Easter eggs for 计组复习助手 — subtle delights for curious users.
 */
import { onMounted, onUnmounted, ref, type Ref } from "vue";

// ── Logo character cycle ──────────────────────────────────────
const LOGO_CHARS = ["组", "计", "机", "存", "算", "指", "流", "汇", "编", "核"];

export function useLogoEasterEgg(): {
  logoChar: Ref<string>;
  logoSpinning: Ref<boolean>;
  clickLogo: () => void;
} {
  const logoChar = ref("组");
  const logoSpinning = ref(false);
  let clickCount = 0;
  let clickTimer: ReturnType<typeof setTimeout> | null = null;

  function clickLogo() {
    clickCount++;
    logoSpinning.value = true;

    // Cycle through characters
    logoChar.value = LOGO_CHARS[clickCount % LOGO_CHARS.length];

    if (clickTimer) clearTimeout(clickTimer);
    clickTimer = setTimeout(() => {
      logoSpinning.value = false;
      // Reset to 组 after 2s of no clicks
      setTimeout(() => {
        if (clickCount > 0) {
          logoChar.value = "组";
          clickCount = 0;
        }
      }, 2000);
    }, 400);
  }

  return { logoChar, logoSpinning, clickLogo };
}

// ── Keyboard konami-style triggers ─────────────────────────────
const EASTER_EGG_SEQUENCES: Record<string, { emoji: string; label: string }> = {
  comporg: { emoji: "🎉", label: "组原永不死！" },
  riscv: { emoji: "✨", label: "RISC-V for the win!" },
  alu: { emoji: "⚡", label: "Add, Shift, Zero, Overflow — 四大皆空！" },
  cpu: { emoji: "🔥", label: "多周期流水线全力运转中…" },
};

export function useKeyboardEasterEgg(onTrigger: (emoji: string, label: string) => void) {
  let buffer = "";
  let resetTimer: ReturnType<typeof setTimeout> | null = null;

  function onKeyDown(e: KeyboardEvent) {
    // Ignore when user is typing in an input
    const tag = (e.target as HTMLElement)?.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

    buffer += e.key.toLowerCase();
    if (resetTimer) clearTimeout(resetTimer);
    resetTimer = setTimeout(() => {
      buffer = "";
    }, 1200);

    for (const [seq, data] of Object.entries(EASTER_EGG_SEQUENCES)) {
      if (buffer.endsWith(seq)) {
        buffer = "";
        onTrigger(data.emoji, data.label);
        return;
      }
    }
  }

  onMounted(() => window.addEventListener("keydown", onKeyDown));
  onUnmounted(() => window.removeEventListener("keydown", onKeyDown));
}

// ── Confetti burst ─────────────────────────────────────────────
interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  char: string;
  color: string;
  opacity: number;
  size: number;
  life: number;
}

export function spawnConfetti(container: HTMLElement, emoji: string, label: string) {
  const COLORS = ["#2d7c6f", "#f0c96a", "#b74343", "#3b82f6", "#22c55e", "#8b5cf6"];
  const CHARS = ["0", "1", "⊕", "∧", "∨", "¬", "→", "←", "#", "@", "&", emoji];

  // Toast message
  const toast = document.createElement("div");
  toast.className = "egg-toast";
  toast.innerHTML = `<span class="egg-toast-emoji">${emoji}</span> ${label}`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 400);
  }, 2200);

  // Particle burst
  const particles: Particle[] = [];
  const centerX = window.innerWidth / 2;
  const centerY = window.innerHeight / 2;

  for (let i = 0; i < 42; i++) {
    const angle = (Math.PI * 2 * i) / 42 + (Math.random() - 0.5) * 0.5;
    const speed = 120 + Math.random() * 220;
    particles.push({
      x: centerX,
      y: centerY,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 60,
      char: CHARS[Math.floor(Math.random() * CHARS.length)],
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      opacity: 1,
      size: 14 + Math.random() * 20,
      life: 1,
    });
  }

  const canvas = document.createElement("canvas");
  canvas.className = "egg-canvas";
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  container.appendChild(canvas);
  const ctx = canvas.getContext("2d")!;

  let lastTime = performance.now();

  function animate(now: number) {
    const dt = Math.min((now - lastTime) / 1000, 0.05);
    lastTime = now;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let alive = false;

    for (const p of particles) {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.vy += 180 * dt; // gravity
      p.life -= dt * 0.85;

      if (p.life <= 0) continue;
      alive = true;

      ctx.font = `${p.size}px "PingFang SC", "Hiragino Sans GB", sans-serif`;
      ctx.fillStyle = p.color;
      ctx.globalAlpha = Math.max(0, p.opacity * p.life);
      ctx.fillText(p.char, p.x, p.y);
    }

    ctx.globalAlpha = 1;
    if (alive) {
      requestAnimationFrame(animate);
    } else {
      canvas.remove();
    }
  }

  requestAnimationFrame(animate);
}
