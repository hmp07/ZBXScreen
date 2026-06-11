/**
 * 大屏自适应缩放工具
 * 基于 1920×1080 设计稿，针对不同分辨率/宽高比自适应
 */

const DESIGN_W = 1920;
const DESIGN_H = 1080;

let resizeListeners: (() => void)[] = [];
let globalResizeHandler: (() => void) | null = null;

/**
 * 计算最佳缩放比例并应用到 scale-inner 元素
 * 策略：
 *   - 16:9 附近（1.6~1.9）：等比缩放填满，留少量黑边
 *   - 超宽屏（>1.9）：按高度缩放，水平居中，左右可能裁切
 *   - 窄屏/竖屏（<1.6）：按宽度缩放，垂直居中，上下可能裁切
 */
export function fitScale(scaleInner: HTMLElement) {
  const parent = scaleInner.parentElement!;
  const w = parent.clientWidth;
  const h = parent.clientHeight;
  const ratio = w / h;
  const designRatio = DESIGN_W / DESIGN_H; // 1.778

  let scale: number;
  if (ratio > 1.9) {
    // 超宽屏：填满高度
    scale = h / DESIGN_H;
  } else if (ratio < 1.5) {
    // 窄屏：填满宽度
    scale = w / DESIGN_W;
  } else {
    // 接近 16:9：等比缩放填满
    scale = Math.max(w / DESIGN_W, h / DESIGN_H);
  }

  scaleInner.style.transform = `scale(${scale})`;
  scaleInner.style.transformOrigin = 'center center';
  scaleInner.style.width = `${DESIGN_W}px`;
  scaleInner.style.height = `${DESIGN_H}px`;
}

/**
 * 设置自适应缩放 + resize 监听
 * 调用一次即可，组件卸载时自动清理
 */
export function useAdaptive(scaleInnerRef: () => HTMLElement | undefined) {
  let handler: (() => void) | null = null;

  function setup() {
    const el = scaleInnerRef();
    if (!el) return;
    handler = () => fitScale(el);
    handler();
    window.addEventListener('resize', handler);
  }

  function teardown() {
    if (handler) {
      window.removeEventListener('resize', handler);
      handler = null;
    }
  }

  return { setup, teardown };
}
