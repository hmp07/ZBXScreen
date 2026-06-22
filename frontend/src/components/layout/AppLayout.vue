<template>
  <!-- 背景粒子动画 -->
  <canvas ref="particleCanvas" class="particle-canvas"></canvas>

  <div class="app-layout" :class="{ fullscreen: layoutStore.isFullscreen }">
    <Sidebar v-if="!layoutStore.isFullscreen" />
    <div class="main-area">
      <div class="content">
        <router-view />
      </div>
    </div>

    <!-- 全屏轮播控制条 -->
    <div v-if="layoutStore.isFullscreen" class="carousel-bar" :class="{ active: layoutStore.carouselEnabled }">
      <div class="carousel-left">
        <button class="carousel-toggle" @click="layoutStore.toggleCarousel()">
          <span class="carousel-icon">{{ layoutStore.carouselEnabled ? '⏸' : '▶' }}</span>
          <span>{{ layoutStore.carouselEnabled ? '轮播中' : '已暂停' }}</span>
        </button>
        <span v-if="layoutStore.carouselEnabled" class="carousel-next">
          下一屏: {{ nextLabel }} · {{ countdown }}s
        </span>
      </div>
      <div class="carousel-right">
        <span class="carousel-pages">
          <span :class="{ current: isMonitor }" @click="$router.push('/dashboard')">监控</span>
          <span class="sep">|</span>
          <span :class="{ current: isAlert }" @click="$router.push('/alerts/dashboard')">告警</span>
          <span class="sep">|</span>
          <span :class="{ current: isNetwork }" @click="$router.push('/network')">网络</span>
        </span>
        <div class="carousel-interval">
          <span>间隔:</span>
          <button v-for="s in [30,60,120]" :key="s"
            :class="{ active: layoutStore.carouselInterval === s }"
            @click="layoutStore.setCarouselInterval(s)">{{ s }}s</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import Sidebar from "./Sidebar.vue";
import { useLayoutStore } from "@/stores/layout";
import axios from "axios";

const layoutStore = useLayoutStore();
const route = useRoute();
const router = useRouter();
const particleCanvas = ref<HTMLCanvasElement>();

// ── 集中获取品牌设置（登录页 + 侧边栏 + 所有大屏页面共用）──
async function fetchBrand() {
  try {
    const res = await axios.get("/api/v1/settings/public");
    if (res.data?.code === 0) {
      const d = res.data.data;
      layoutStore.setBrand(d.title || "ZBXScreen", d.logo || "");
    }
  } catch {
    // keep defaults
  }
}

// ── 背景粒子动画 ──
let particleAnimId: number;
function initParticles() {
  const canvas = particleCanvas.value;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const particles: { x: number; y: number; vx: number; vy: number; r: number; alpha: number }[] = [];
  const COUNT = 60;

  function resize() {
    canvas!.width = window.innerWidth;
    canvas!.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  for (let i = 0; i < COUNT; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3 - 0.15,
      r: Math.random() * 1.5 + 0.5,
      alpha: Math.random() * 0.5 + 0.15,
    });
  }

  function drawConnections() {
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 150) {
          cctx.beginPath();
          cctx.moveTo(particles[i].x, particles[i].y);
          cctx.lineTo(particles[j].x, particles[j].y);
          cctx.strokeStyle = `rgba(0, 229, 255, ${0.06 * (1 - dist / 150)})`;
          cctx.lineWidth = 0.5;
          cctx.stroke();
        }
      }
    }
  }

  const c = canvas!;
  const cctx = ctx!;

  function animate() {
    cctx.clearRect(0, 0, c.width, c.height);
    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = c.width;
      if (p.x > c.width) p.x = 0;
      if (p.y < 0) p.y = c.height;
      if (p.y > c.height) p.y = 0;
      cctx.beginPath();
      cctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      cctx.fillStyle = `rgba(0, 229, 255, ${p.alpha})`;
      cctx.fill();
    });
    drawConnections();
    particleAnimId = requestAnimationFrame(animate);
  }
  animate();
}

const countdown = ref(layoutStore.carouselInterval);
let carouselTimer: number | null = null;
let countdownTimer: number | null = null;

const DASHBOARD_LABELS: Record<string, string> = {
  "/dashboard": "数据中心大屏",
  "/alerts/dashboard": "告警大屏",
};

const isMonitor = computed(() => route.path === "/dashboard");
const isAlert = computed(() => route.path === "/alerts/dashboard");
const isNetwork = computed(() => route.path === "/network");
const nextLabel = computed(() => {
  const next = layoutStore.getNextDashboard(route.path);
  return DASHBOARD_LABELS[next] || next;
});

function startCarousel() {
  stopCarousel();
  if (!layoutStore.isFullscreen || !layoutStore.carouselEnabled) return;

  countdown.value = layoutStore.carouselInterval;

  countdownTimer = window.setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      const next = layoutStore.getNextDashboard(route.path);
      router.push(next);
    }
  }, 1000);
}

function stopCarousel() {
  if (carouselTimer) clearInterval(carouselTimer);
  if (countdownTimer) clearInterval(countdownTimer);
  carouselTimer = null;
  countdownTimer = null;
}

// Watch for route changes to reset countdown
watch(() => route.path, () => {
  if (layoutStore.isFullscreen && layoutStore.carouselEnabled) {
    countdown.value = layoutStore.carouselInterval;
  }
});

// Watch fullscreen + carousel state
watch(
  () => [layoutStore.isFullscreen, layoutStore.carouselEnabled, layoutStore.carouselInterval] as const,
  ([fs, enabled]) => {
    if (fs && enabled) {
      startCarousel();
    } else {
      stopCarousel();
    }
  },
  { immediate: true }
);

// Sidebar collapse/expand → trigger resize for dashboard pages to recalibrate
watch(() => layoutStore.sidebarEffective, () => {
  // 等待 CSS transition 完成 (250ms) 后触发 resize，让自适应缩放重新计算
  setTimeout(() => window.dispatchEvent(new Event('resize')), 260);
});

onMounted(() => { initParticles(); fetchBrand(); });
onUnmounted(() => { stopCarousel(); cancelAnimationFrame(particleAnimId); });
</script>

<style scoped>
.particle-canvas {
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  opacity: 0.7;
}
.app-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}
.app-layout.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: #000;
}
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}
.content {
  flex: 1;
  overflow: hidden;
  background: var(--bg-primary);
  min-height: 0;
  position: relative;
}
.app-layout.fullscreen .content {
  background: #000;
}

/* 全屏轮播控制条 */
.carousel-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 36px;
  background: rgba(8, 22, 40, 0.92);
  border-top: 1px solid rgba(0, 229, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  z-index: 1000;
  font-size: 13px;
  color: var(--text-2);
  backdrop-filter: blur(8px);
  transition: border-color 0.3s;
}
.carousel-bar.active {
  border-top-color: var(--primary);
  box-shadow: 0 -4px 20px rgba(0, 229, 255, 0.1);
}
.carousel-left,
.carousel-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.carousel-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(0, 229, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.25);
  color: var(--text-1);
  cursor: pointer;
  font-size: 12px;
  border-radius: 3px;
  transition: all 0.2s;
  font-family: var(--font-cn);
}
.carousel-toggle:hover {
  background: rgba(0, 229, 255, 0.16);
  border-color: var(--primary);
}
.carousel-icon {
  font-size: 14px;
}
.carousel-next {
  font-family: var(--font-num);
  color: var(--primary);
  font-size: 12px;
  letter-spacing: 0.5px;
}
.carousel-pages {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.carousel-pages span {
  cursor: pointer;
  color: var(--text-3);
  transition: color 0.2s;
}
.carousel-pages span:hover {
  color: var(--text-1);
}
.carousel-pages span.current {
  color: var(--primary);
  font-weight: 600;
  text-shadow: 0 0 8px var(--primary-glow);
}
.carousel-pages .sep {
  color: var(--text-4);
  cursor: default;
}
.carousel-interval {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-3);
}
.carousel-interval button {
  padding: 2px 8px;
  background: transparent;
  border: 1px solid var(--panel-border);
  color: var(--text-3);
  cursor: pointer;
  font-size: 11px;
  border-radius: 2px;
  font-family: var(--font-num);
  transition: all 0.2s;
}
.carousel-interval button:hover {
  border-color: var(--primary);
  color: var(--text-1);
}
.carousel-interval button.active {
  background: rgba(0, 229, 255, 0.15);
  border-color: var(--primary);
  color: var(--primary);
}
</style>
