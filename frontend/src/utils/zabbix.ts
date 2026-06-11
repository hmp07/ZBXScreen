/** Zabbix Item Key → 中文名/单位映射 */

const ITEM_KEY_MAP: Record<string, { name: string; unit: string }> = {
  "system.cpu.util[,idle]": { name: "CPU 使用率", unit: "%" },
  "system.cpu.util": { name: "CPU 使用率", unit: "%" },
  "vm.memory.size[pused]": { name: "内存使用率", unit: "%" },
  "vm.memory.utilization": { name: "内存使用率", unit: "%" },
  "vm.memory.size[total]": { name: "内存总量", unit: "B" },
  "vm.memory.size[available]": { name: "可用内存", unit: "B" },
  "vfs.fs.size[/,pused]": { name: "磁盘使用率(/)", unit: "%" },
  "vfs.fs.size": { name: "磁盘使用率", unit: "%" },
  "net.if.in": { name: "网络入流量", unit: "bps" },
  "net.if.out": { name: "网络出流量", unit: "bps" },
  "system.uptime": { name: "运行时长", unit: "s" },
  "system.uname": { name: "系统信息", unit: "" },
};

export function getItemDisplayName(itemKey: string): string {
  // 精确匹配
  if (ITEM_KEY_MAP[itemKey]) return ITEM_KEY_MAP[itemKey].name;

  // 模糊匹配
  for (const [pattern, info] of Object.entries(ITEM_KEY_MAP)) {
    if (itemKey.startsWith(pattern.replace("[,", "["))) {
      return info.name;
    }
  }

  return itemKey;
}

export function getItemUnit(itemKey: string): string {
  for (const [pattern, info] of Object.entries(ITEM_KEY_MAP)) {
    if (itemKey.startsWith(pattern.replace("[,", "[")) || itemKey === pattern) {
      return info.unit;
    }
  }
  return "";
}
