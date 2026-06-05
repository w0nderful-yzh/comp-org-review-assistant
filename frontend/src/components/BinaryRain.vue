<template>
  <canvas
    ref="canvasRef"
    class="binary-rain"
    :style="{ opacity: String(opacity) }"
    aria-hidden="true"
  />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

const props = withDefaults(
  defineProps<{ opacity?: number; density?: number; speed?: number }>(),
  { opacity: 0.08, density: 0.4, speed: 1.0 }
);

const canvasRef = ref<HTMLCanvasElement | null>(null);
let rafId = 0;

onMounted(() => {
  const el = canvasRef.value;
  if (!el) return;
  const canvas: HTMLCanvasElement = el;
  const context = canvas.getContext("2d");
  if (!context) return;
  const ctx: CanvasRenderingContext2D = context;

  let cols = 0;
  let drops: number[] = [];
  const chars = "01".split("");
  const fontSize = 14;

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    cols = Math.floor(canvas.width / fontSize * props.density);
    drops = Array.from({ length: cols }, () =>
      Math.floor((Math.random() * canvas.height) / fontSize)
    );
  }

  resize();
  window.addEventListener("resize", resize);

  let lastTime = 0;
  const interval = 55 / props.speed;

  function draw(time: number) {
    if (time - lastTime < interval) {
      rafId = requestAnimationFrame(draw);
      return;
    }
    lastTime = time;

    ctx.fillStyle = `rgba(246, 243, 234, 0.08)`;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.font = `${fontSize}px "SF Mono", "JetBrains Mono", "Fira Code", monospace`;

    for (let i = 0; i < drops.length; i++) {
      const char = chars[Math.floor(Math.random() * chars.length)];
      const x = (i / props.density) * fontSize;
      const y = drops[i] * fontSize;

      // Lead character brighter
      ctx.fillStyle = "rgba(45, 124, 111, 0.65)";
      ctx.fillText(char, x, y);

      // Trail
      for (let t = 1; t <= 3; t++) {
        const trailY = y - t * fontSize;
        if (trailY < 0) continue;
        ctx.fillStyle = `rgba(45, 124, 111, ${0.22 - t * 0.06})`;
        const trailChar = chars[Math.floor(Math.random() * chars.length)];
        ctx.fillText(trailChar, x, trailY);
      }

      if (y > canvas.height && Math.random() > 0.985) {
        drops[i] = 0;
      }
      drops[i]++;
    }

    rafId = requestAnimationFrame(draw);
  }

  rafId = requestAnimationFrame(draw);

  onUnmounted(() => {
    cancelAnimationFrame(rafId);
    window.removeEventListener("resize", resize);
  });
});
</script>

<style scoped>
.binary-rain {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  width: 100%;
  height: 100%;
}
</style>
