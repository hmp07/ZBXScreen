/** 单位格式化工具 */

export function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0 || !bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + " " + sizes[i];
}

export function formatBitsPerSec(bps: number, decimals = 1): string {
  if (!bps) return "0 bps";
  const k = 1000;
  const sizes = ["bps", "Kbps", "Mbps", "Gbps"];
  const i = Math.floor(Math.log(bps) / Math.log(k));
  return parseFloat((bps / Math.pow(k, i)).toFixed(decimals)) + " " + sizes[i];
}

export function formatHertz(hz: number): string {
  if (!hz) return "0 Hz";
  if (hz >= 1e9) return (hz / 1e9).toFixed(1) + " GHz";
  if (hz >= 1e6) return (hz / 1e6).toFixed(1) + " MHz";
  return hz + " Hz";
}

export function formatPercent(value: number): string {
  return (value || 0).toFixed(1) + "%";
}

export function formatDateTime(t: string | null): string {
  if (!t) return '-'
  const d = new Date(t)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export function formatUptime(seconds: number): string {
  if (!seconds) return "-";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}
