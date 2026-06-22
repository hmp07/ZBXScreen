import { defineStore } from "pinia";
import { ref, computed } from "vue";

const CAROUSEL_DASHBOARDS = ["/dashboard", "/alerts/dashboard", "/network"];
const CAROUSEL_INTERVAL = 60; // 秒

export const useLayoutStore = defineStore("layout", () => {
  const isFullscreen = ref(false);
  const sidebarCollapsed = ref(localStorage.getItem("sidebar_collapsed") === "true");
  const sidebarHovered = ref(false);
  const carouselEnabled = ref(localStorage.getItem("carousel_enabled") === "true");

  // 品牌信息（登录页 + 侧边栏使用，系统设置保存后更新）
  const brandTitle = ref("ZBXScreen");
  const brandLogo = ref("");
  function setBrand(title: string, logo: string) {
    if (title) brandTitle.value = title;
    if (logo !== undefined) brandLogo.value = logo;
  }
  const carouselInterval = ref(
    Number(localStorage.getItem("carousel_interval")) || CAROUSEL_INTERVAL
  );
  const carouselTick = ref(0);

  const sidebarEffective = computed(() => {
    // 悬浮时临时展开
    if (sidebarCollapsed.value && sidebarHovered.value) return false;
    return sidebarCollapsed.value;
  });

  function persistCarousel() {
    localStorage.setItem("carousel_enabled", String(carouselEnabled.value));
    localStorage.setItem("carousel_interval", String(carouselInterval.value));
  }

  function toggleCarousel() {
    carouselEnabled.value = !carouselEnabled.value;
    persistCarousel();
  }

  function setCarouselInterval(seconds: number) {
    carouselInterval.value = Math.max(10, Math.min(300, seconds));
    persistCarousel();
  }

  function enterFullscreen() {
    const el = document.documentElement;
    if (el.requestFullscreen) {
      el.requestFullscreen().catch(() => {});
    }
  }
  function exitFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    carouselEnabled.value = false;
    persistCarousel();
  }
  async function toggleFullscreen() {
    if (document.fullscreenElement) {
      await document.exitFullscreen().catch(() => {});
      carouselEnabled.value = false;
      persistCarousel();
    } else {
      await document.documentElement.requestFullscreen().catch(() => {});
    }
  }

  // 监听原生全屏事件同步状态（处理 ESC 键退出等）
  function _syncFullscreen() {
    isFullscreen.value = !!document.fullscreenElement;
    if (!document.fullscreenElement) {
      carouselEnabled.value = false;
      persistCarousel();
    }
  }
  if (typeof document !== 'undefined') {
    document.addEventListener('fullscreenchange', _syncFullscreen);
  }

  function getNextDashboard(currentPath: string): string {
    const idx = CAROUSEL_DASHBOARDS.indexOf(currentPath);
    if (idx === -1) return CAROUSEL_DASHBOARDS[0];
    return CAROUSEL_DASHBOARDS[(idx + 1) % CAROUSEL_DASHBOARDS.length];
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value;
    localStorage.setItem("sidebar_collapsed", String(sidebarCollapsed.value));
  }

  return {
    isFullscreen,
    sidebarCollapsed,
    sidebarHovered,
    sidebarEffective,
    carouselEnabled,
    carouselInterval,
    carouselTick,
    brandTitle,
    brandLogo,
    setBrand,
    toggleSidebar,
    enterFullscreen,
    exitFullscreen,
    toggleFullscreen,
    toggleCarousel,
    setCarouselInterval,
    getNextDashboard,
  };
});
