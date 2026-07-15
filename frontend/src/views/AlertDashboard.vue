<template>
  <div class="dashboard">
        <!-- Header -->
        <header class="header">
          <div class="brand">
            <img v-if="logoUrl" :src="logoUrl" class="brand-logo-img" />
            <div v-else class="brand-logo">{{ logoLetter }}</div>
            <div class="brand-text">
              <div class="brand-name">{{ brandName }}</div>
              <div v-if="brandSub" class="brand-sub">{{ brandSub }}</div>
            </div>
          </div>
          <div class="title-wrap">
            <div class="title-wing-l"></div><div class="title-wing-r"></div>
            <div class="title-deco"></div>
            <div class="title-main">告 警 分 析 监 控 大 屏</div>
          </div>
          <div class="header-right">
            <div class="fullscreen-btn" @click="layoutStore.toggleFullscreen()" :title="layoutStore.isFullscreen ? '退出全屏' : '全屏展示'">
              {{ layoutStore.isFullscreen ? '⊠ 退出全屏' : '⊡ 全屏' }}
            </div>
            <div class="theme-switcher">
              <div v-for="c in themes" :key="c" class="theme-dot" :class="{ active: theme === c }" :data-color="c" @click="theme = c"></div>
            </div>
            <div class="clock-block">
              <div class="clock">{{ clock }}</div>
              <div class="clock-date">{{ clockDate }}</div>
            </div>
          </div>
        </header>

        <!-- KPI Strip -->
        <section class="kpi-strip">
          <div v-for="k in kpis" :key="k.key" class="kpi" :class="{ alert: k.alert }">
            <div class="kpi-glow"></div>
            <div class="kpi-icon">{{ k.icon }}</div>
            <div class="kpi-body">
              <div class="kpi-label">{{ k.label }}</div>
              <div class="kpi-value-row">
                <div class="kpi-value" :style="{ color: k.color }">{{ k.display }}</div>
                <div class="kpi-unit">{{ k.unit }}</div>
              </div>
            </div>
          </div>
        </section>

        <!-- Main Area -->
        <section class="main-area">
          <!-- Level Distribution Pie -->
          <div class="panel col-1">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title">
              <div class="panel-title-text">告警级别分布 <span class="panel-title-en">SEVERITY</span></div>
            </div>
            <div class="panel-body no-pad"><div ref="levelPieRef" class="chart"></div></div>
          </div>

          <!-- 24h Trend -->
          <div class="panel col-2">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title">
              <div class="panel-title-text">24小时告警趋势 <span class="panel-title-en">24H TREND</span></div>
            </div>
            <div class="panel-body no-pad"><div ref="trendRef" class="chart"></div></div>
          </div>

          <!-- Trigger Type Distribution Donut (TOP 10) -->
          <div class="panel col-3">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title">
              <div class="panel-title-text">告警类型分布 <span class="panel-title-en">TRIGGER TYPE</span></div>
            </div>
            <div class="panel-body no-pad"><div ref="triggerDonutRef" class="chart"></div></div>
          </div>

          <!-- Host Alert TOP 10 -->
          <div class="panel col-4">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title">
              <div class="panel-title-text">主机告警 TOP 10 <span class="panel-title-en">HOST RANKING</span></div>
            </div>
            <div class="panel-body no-pad"><div ref="hostBarRef" class="chart"></div></div>
          </div>

          <!-- Recent Active Alerts (full column) -->
          <div class="panel col-5 alert-list">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title">
              <div class="panel-title-text">活跃告警列表 <span class="panel-title-en">ACTIVE ALERTS</span></div>
              <div class="panel-title-tools"><span class="live">滚动</span></div>
            </div>
            <div class="alert-list-header">
              <div>时间</div><div>等级</div><div>主机 / 描述</div><div style="text-align:center">值</div>
            </div>
            <div class="alert-list-body" ref="alertBodyRef">
              <div class="alert-list-inner" ref="alertInnerRef" :style="{ transform: 'translateY(-' + alertOffset + 'px)' }">
                <div v-for="a in recentActive" :key="a.id" class="alert-row">
                  <div class="alert-time">{{ formatAlertTime(a.first_occurred) }}</div>
                  <div><span class="alert-sev" :class="a.level?.toLowerCase()">{{ sevLabel(a.level) }}</span></div>
                  <div>
                    <div class="alert-host">{{ a.host_name }}</div>
                    <div class="alert-msg">{{ a.trigger_name }}</div>
                  </div>
                  <div style="text-align:center" class="alert-value">{{ a.value || '-' }}</div>
                </div>
              </div>
            </div>
          </div>
        </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { getAlertDashboard } from '@/api/alert'
import { getSettings } from '@/api/settings'
import { useLayoutStore } from '@/stores/layout'
import { formatDateTime } from '@/utils/format'

const layoutStore = useLayoutStore()
const brandName = computed(() => layoutStore.brandTitle || 'ZBXBoard')
const brandSub = ref('')
const logoLetter = computed(() => layoutStore.brandTitle?.charAt(0) || 'Z')
const logoUrl = ref('')

const LEVEL_COLORS: Record<string, string> = {
  DISASTER: '#820014', HIGH: '#f5222d', AVERAGE: '#faad14', WARNING: '#fa8c16', INFO: '#1890ff',
}
const LEVEL_LABELS: Record<string, string> = {
  DISASTER: '灾难', HIGH: '严重', AVERAGE: '一般', WARNING: '警告', INFO: '信息',
}

const WEEK_CN = ['周日','周一','周二','周三','周四','周五','周六']
const themes = ['cyan','purple','green','orange']
const theme = ref('cyan')
const clock = ref('--:--:--')
const clockDate = ref('----年--月--日')
const levelPieRef = ref<HTMLElement>()
const trendRef = ref<HTMLElement>()
const hostBarRef = ref<HTMLElement>()
const triggerDonutRef = ref<HTMLElement>()
const alertBodyRef = ref<HTMLElement>()
const alertInnerRef = ref<HTMLElement>()
const alertOffset = ref(0)
let levelPie: echarts.ECharts | null = null
let trendChart: echarts.ECharts | null = null
let hostBar: echarts.ECharts | null = null
let triggerDonut: echarts.ECharts | null = null
let clockTimer: number, dataTimer: number, alertScrollTimer: number

const summary = ref({ active_count: 0, today_new: 0, today_recovered: 0, avg_recovery_minutes: 0, unpushed_count: 0 })
const byLevel = ref<Record<string, number>>({})
const trend24h = ref<any[]>([])
const topHosts = ref<any[]>([])
const topTriggers = ref<any[]>([])
const recentActive = ref<any[]>([])

const kpis = computed(() => [
  { key: 'active', label: '活跃告警', unit: '条', icon: '🚨', value: summary.value.active_count, color: '#f5222d', alert: true, display: summary.value.active_count.toLocaleString() },
  { key: 'today_new', label: '今日新增', unit: '条', icon: '📈', value: summary.value.today_new, color: '#faad14', alert: false, display: summary.value.today_new.toLocaleString() },
  { key: 'today_recov', label: '今日恢复', unit: '条', icon: '✅', value: summary.value.today_recovered, color: '#52c41a', alert: false, display: summary.value.today_recovered.toLocaleString() },
  { key: 'avg_recov', label: '平均恢复时长', unit: '分钟', icon: '⏱️', value: summary.value.avg_recovery_minutes, color: '#00e5ff', alert: false, display: summary.value.avg_recovery_minutes.toLocaleString() },
  { key: 'unpushed', label: '未推送告警', unit: '条', icon: '📡', value: summary.value.unpushed_count, color: summary.value.unpushed_count > 0 ? '#fa8c16' : '#00e5ff', alert: false, display: summary.value.unpushed_count.toLocaleString() },
])

function pad(n: number) { return String(n).padStart(2,'0') }
function sevLabel(level: string) { return LEVEL_LABELS[level] || level }
function formatAlertTime(t: string | null) { return formatDateTime(t) }
function tickClock() {
  const d = new Date()
  clock.value = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  clockDate.value = `${d.getFullYear()}.${pad(d.getMonth()+1)}.${pad(d.getDate())} ${WEEK_CN[d.getDay()]}`
}

async function fetchData() {
  try {
    const res = await getAlertDashboard()
    if (res.data.code === 0) {
      const d = res.data.data
      summary.value = d.summary
      byLevel.value = d.by_level
      trend24h.value = d.trend_24h
      topHosts.value = d.top_hosts
      topTriggers.value = d.top_triggers
      recentActive.value = d.recent_active
      updateCharts()
    }
  } catch(e) { console.error("AlertDashboard fetchData failed:", e) }
}

function initLevelPie() {
  if (!levelPieRef.value) return
  levelPie = echarts.init(levelPieRef.value, 'dark')
}

function initTrendChart() {
  if (!trendRef.value) return
  trendChart = echarts.init(trendRef.value, 'dark')
}

function initHostBar() {
  if (!hostBarRef.value) return
  hostBar = echarts.init(hostBarRef.value, 'dark')
}

function initTriggerDonut() {
  if (!triggerDonutRef.value) return
  triggerDonut = echarts.init(triggerDonutRef.value, 'dark')
}

function updateCharts() {
  updateLevelPie()
  updateTriggerDonut()
  updateTrendChart()
  updateHostBar()
}

function updateLevelPie() {
  if (!levelPie) return
  const levels = ['DISASTER', 'HIGH', 'AVERAGE', 'WARNING', 'INFO']
  const data = levels.map(l => ({
    name: LEVEL_LABELS[l], value: byLevel.value[l] || 0,
    itemStyle: { color: LEVEL_COLORS[l] },
  }))
  const total = data.reduce((s, d) => s + d.value, 0)
  levelPie.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 }, formatter: '{b}: {c} 条 ({d}%)' },
    graphic: [
      { type: 'text', left: 'center', top: '42%', style: { text: total, fill: '#e6f7ff', fontSize: 28, fontWeight: 900, fontFamily: 'Orbitron, monospace', textAlign: 'center' } },
      { type: 'text', left: 'center', top: '58%', style: { text: '活跃告警', fill: '#6b89a3', fontSize: 12, textAlign: 'center' } },
    ],
    series: [{
      type: 'pie', radius: ['48%','72%'], center: ['50%','50%'],
      label: { show: true, position: 'outside', color: '#a8c4d8', fontSize: 11, formatter: '{b}\n{c}' },
      labelLine: { length: 8, length2: 6, lineStyle: { color: '#455a72' } },
      itemStyle: { borderColor: '#050d1a', borderWidth: 2 },
      data,
    }],
  }, true)
}

function updateTrendChart() {
  if (!trendChart) return
  const levels = ['WARNING', 'AVERAGE', 'HIGH', 'DISASTER']
  trendChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 48, right: 20, top: 30, bottom: 24 },
    legend: { data: levels.map(l => LEVEL_LABELS[l]), textStyle: { color: '#a8c4d8', fontSize: 10 }, right: 8, top: 4, itemWidth: 12, itemHeight: 8, itemGap: 10 },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 } },
    xAxis: { type: 'category', data: trend24h.value.map((t: any) => t.hour), boundaryGap: false, axisLine: { lineStyle: { color: '#455a72' } }, axisLabel: { color: '#6b89a3', fontSize: 10 } },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { color: '#6b89a3', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } } },
    series: levels.map(l => ({
      name: LEVEL_LABELS[l], type: 'line', smooth: true, symbol: 'none',
      color: LEVEL_COLORS[l],
      data: trend24h.value.map((t: any) => t[l] || 0),
      lineStyle: { width: 1.6, color: LEVEL_COLORS[l] },
      areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:LEVEL_COLORS[l]+'66'},{offset:1,color:'transparent'}]) },
    })),
  }, true)
}

function updateHostBar() {
  if (!hostBar) return
  const hosts = topHosts.value
  hostBar.setOption({
    backgroundColor: 'transparent',
    grid: { left: 140, right: 30, top: 16, bottom: 20 },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 } },
    legend: { data: ['活跃','已恢复'], textStyle: { color: '#a8c4d8', fontSize: 10 }, right: 8, top: 2, itemWidth: 10, itemHeight: 8 },
    xAxis: { type: 'value', axisLabel: { color: '#6b89a3', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } } },
    yAxis: { type: 'category', data: hosts.map((h: any) => h.host_name).reverse(), axisLabel: { color: '#a8c4d8', fontSize: 11, width: 130, overflow: 'truncate' }, axisLine: { lineStyle: { color: '#455a72' } } },
    series: [
      { name: '活跃', type: 'bar', stack: 'total', data: hosts.map((h: any) => h.active).reverse(), itemStyle: { color: '#f5222d' }, barWidth: 16 },
      { name: '已恢复', type: 'bar', stack: 'total', data: hosts.map((h: any) => h.recovered).reverse(), itemStyle: { color: '#52c41a' }, barWidth: 16 },
    ],
  }, true)
}

function updateTriggerDonut() {
  if (!triggerDonut) return
  const triggers = topTriggers.value
  const total = triggers.reduce((s: number, t: any) => s + t.count, 0)
  const colors = ['#00e5ff', '#7b61ff', '#52c41a', '#faad14', '#f5222d', '#1890ff', '#fa8c16', '#722ed1']
  const data = triggers.map((t: any, i: number) => ({
    name: t.trigger_name.length > 22 ? t.trigger_name.slice(0, 22) + '...' : t.trigger_name,
    value: t.count,
    itemStyle: { color: colors[i % colors.length] },
  }))
  triggerDonut.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 }, formatter: '{b}: {c} 条 ({d}%)' },
    graphic: [
      { type: 'text', left: 'center', top: '42%', style: { text: total, fill: '#e6f7ff', fontSize: 24, fontWeight: 900, fontFamily: 'Orbitron, monospace', textAlign: 'center' } },
      { type: 'text', left: 'center', top: '58%', style: { text: '告警类型', fill: '#6b89a3', fontSize: 11, textAlign: 'center' } },
    ],
    series: [{
      type: 'pie', radius: ['50%','75%'], center: ['50%','50%'],
      label: { show: true, position: 'outside', color: '#a8c4d8', fontSize: 10, formatter: '{b}\n{d}%' },
      labelLine: { length: 10, length2: 8, lineStyle: { color: '#455a72' } },
      itemStyle: { borderColor: '#050d1a', borderWidth: 2 },
      data,
    }],
  }, true)
}

watch(theme, (v) => { document.body.dataset.theme = v })

onMounted(async () => {
  try {
    const sRes = await getSettings()
    const s = sRes.data.data
    // 品牌标题和图标由 AppLayout 统一加载到 layoutStore
    if (s.SYSTEM_SUBTITLE) brandSub.value = s.SYSTEM_SUBTITLE
    if (s.SYSTEM_LOGO) logoUrl.value = s.SYSTEM_LOGO
  } catch(e) { /* defaults */ }

  await fetchData()
  tickClock()
  clockTimer = window.setInterval(tickClock, 1000)
  dataTimer = window.setInterval(fetchData, 30000)
  await nextTick()
  initLevelPie(); initTriggerDonut(); initTrendChart(); initHostBar()
  updateCharts()
  alertScrollTimer = window.setInterval(() => {
    if (!alertBodyRef.value || !alertInnerRef.value) return
    const rowH = 42, maxScroll = alertInnerRef.value.scrollHeight - alertBodyRef.value.clientHeight
    alertOffset.value = alertOffset.value >= maxScroll ? 0 : alertOffset.value + rowH
  }, 2500)
})

onUnmounted(() => {
  clearInterval(clockTimer); clearInterval(dataTimer); clearInterval(alertScrollTimer)
  levelPie?.dispose(); triggerDonut?.dispose(); trendChart?.dispose(); hostBar?.dispose()
})
</script>

<style scoped>
.dashboard {
  position: relative; width: 100%; height: 100%;
  display: grid; grid-template-rows: 7.4vh 10.2vh 1fr; grid-template-columns: 1fr;
  gap: 0.625vw; padding: 0.625vw 0.83vw; z-index: 1;
}
.header {
  position: relative; display: grid; grid-template-columns: 1fr auto 1fr;
  align-items: center; padding: 0 24px;
  background: linear-gradient(180deg, rgba(0,229,255,0.05), transparent); overflow: hidden;
}
.header::before, .header::after {
  content: ''; position: absolute; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--primary) 50%, transparent); opacity: 0.6;
}
.header::before { top: 0; } .header::after { bottom: 0; }
.brand { display: flex; align-items: center; gap: 14px; z-index: 2; }
.brand-logo {
  width: 42px; height: 42px; border-radius: 10px;
  background: linear-gradient(135deg, var(--primary), var(--primary-2));
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-num); font-weight: 900; color: #001a2b; font-size: 20px;
  box-shadow: 0 0 24px var(--primary-glow); position: relative;
}
.brand-logo-img { width: 42px; height: 42px; border-radius: 10px; object-fit: contain; box-shadow: 0 0 24px var(--primary-glow); }
.brand-text { display: flex; flex-direction: column; gap: 2px; }
.brand-name {
  font-family: var(--font-num); font-size: 24px; font-weight: 700; letter-spacing: 2px;
  background: linear-gradient(90deg, var(--primary), #7be8ff); -webkit-background-clip: text; background-clip: text; color: transparent;
}
.brand-sub { font-size: 12px; color: var(--text-3); letter-spacing: 4px; }
.title-wrap { position: relative; text-align: center; z-index: 2; }
.title-main {
  font-size: 32px; font-weight: 900; letter-spacing: 10px;
  background: linear-gradient(180deg, #ffffff 30%, var(--primary) 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  text-shadow: 0 0 24px var(--primary-glow); padding: 0 10px;
}
.title-deco { position: absolute; left: 50%; top: 50%; transform: translate(-50%,-50%); width: 460px; height: 64px; border: 1px solid var(--panel-border); pointer-events: none; }
.title-deco::before, .title-deco::after { content: ''; position: absolute; width: 24px; height: 24px; border: 2px solid var(--primary); }
.title-deco::before { top: -2px; left: -2px; border-right: 0; border-bottom: 0; }
.title-deco::after  { bottom: -2px; right: -2px; border-left: 0; border-top: 0; }
.title-wing-l, .title-wing-r { position: absolute; top: 50%; width: 200px; height: 1px; background: linear-gradient(90deg, transparent, var(--primary)); }
.title-wing-l { left: -200px; } .title-wing-r { right: -200px; transform: scaleX(-1); }
.header-right { display: flex; align-items: center; justify-content: flex-end; gap: 18px; z-index: 2; }
.clock-block { text-align: right; }
.clock { font-family: var(--font-num); font-size: 30px; font-weight: 700; color: var(--primary); letter-spacing: 3px; text-shadow: 0 0 16px var(--primary-glow); line-height: 1; }
.clock::after { content: ''; display: inline-block; width: 6px; height: 28px; background: var(--primary); margin-left: 4px; vertical-align: middle; animation: blink 1s steps(2) infinite; }
@keyframes blink { 50% { opacity: 0; } }
.clock-date { font-size: 12px; color: var(--text-3); letter-spacing: 2px; margin-top: 4px; }
.theme-switcher { display: flex; gap: 8px; padding: 4px 8px; border: 1px solid var(--panel-border); border-radius: 20px; background: rgba(0,229,255,0.04); }
.theme-dot { width: 18px; height: 18px; border-radius: 50%; cursor: pointer; border: 2px solid transparent; transition: all 0.25s; }
.theme-dot:hover { transform: scale(1.2); }
.theme-dot.active { border-color: #fff; box-shadow: 0 0 12px currentColor; }
.theme-dot[data-color="cyan"]    { background: #00e5ff; color: #00e5ff; }
.theme-dot[data-color="purple"]  { background: #7b61ff; color: #7b61ff; }
.theme-dot[data-color="green"]   { background: #52c41a; color: #52c41a; }
.theme-dot[data-color="orange"]  { background: #ff7a45; color: #ff7a45; }

.kpi-strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; padding: 0 6px; }
.kpi {
  position: relative; height: 100%; background: var(--panel-bg); border: 1px solid var(--panel-border);
  display: flex; align-items: center; padding: 0 18px; gap: 16px; overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
}
.kpi::after { content: ''; position: absolute; width: 14px; height: 14px; border: 2px solid var(--primary); opacity: 0.8; bottom: -2px; right: -2px; border-left: 0; border-top: 0; }
.kpi:hover { transform: translateY(-2px); box-shadow: 0 0 24px var(--primary-glow); }
.kpi.alert { border-color: rgba(245,34,45,0.3); }
.kpi.alert::after { border-color: var(--danger); }
.kpi-glow { position: absolute; width: 200px; height: 200px; background: radial-gradient(circle, var(--primary-glow), transparent 70%); right: -60px; top: -60px; opacity: 0.3; pointer-events: none; }
.kpi-icon { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; font-size: 26px; background: linear-gradient(135deg, rgba(0,229,255,0.18), rgba(0,229,255,0.04)); border: 1px solid var(--panel-border); border-radius: 6px; flex-shrink: 0; }
.kpi-body { flex: 1; min-width: 0; }
.kpi-label { font-size: 13px; color: var(--text-2); letter-spacing: 2px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
.kpi-label::before { content: ''; display: inline-block; width: 3px; height: 10px; background: var(--primary); }
.kpi-value-row { display: flex; align-items: baseline; gap: 6px; }
.kpi-value { font-family: var(--font-num); font-size: 36px; font-weight: 900; line-height: 1; text-shadow: 0 0 18px var(--primary-glow); font-variant-numeric: tabular-nums; }
.kpi-unit { font-size: 13px; color: var(--text-3); }

.main-area { display: grid; grid-template-columns: 2fr 2fr 3fr; grid-template-rows: 1fr 1fr; gap: 0.625vw; min-height: 0; }
.col-1 { grid-column: 1; grid-row: 1; }
.col-2 { grid-column: 1; grid-row: 2; }
.col-3 { grid-column: 2; grid-row: 1; }
.col-4 { grid-column: 2; grid-row: 2; }
.col-5 { grid-column: 3; grid-row: 1 / 3; }

.alert-list { height: 100%; display: flex; flex-direction: column; }
.alert-list-header {
  display: grid; grid-template-columns: 100px 56px 1fr 50px; align-items: center; gap: 8px;
  padding: 0 14px; height: 28px; font-size: 11px; color: var(--text-3); letter-spacing: 1px;
  border-bottom: 1px solid rgba(0,229,255,0.1); background: rgba(0,229,255,0.04); flex-shrink: 0;
}
.alert-list-body { flex: 1; overflow: hidden; position: relative; }
.alert-list-inner { position: absolute; inset: 0; padding: 4px 0; transition: transform 0.6s ease; }
.alert-row {
  display: grid; grid-template-columns: 100px 56px 1fr 50px; align-items: center; gap: 8px;
  padding: 0 14px; height: 34px; font-size: 12px;
  border-bottom: 1px dashed rgba(0,229,255,0.08); transition: background 0.2s;
}
.alert-row:hover { background: rgba(0,229,255,0.06); }
.alert-time { font-family: var(--font-num); color: var(--text-2); font-size: 11px; }
.alert-sev {
  display: inline-flex; align-items: center; justify-content: center;
  height: 18px; font-size: 10px; font-weight: 700; letter-spacing: 1px;
  color: #fff; border-radius: 2px; padding: 0 5px;
}
.alert-sev.disaster { background: #820014; }
.alert-sev.high     { background: #f5222d; }
.alert-sev.average  { background: #faad14; color: #2b1d00; }
.alert-sev.warning  { background: #fa8c16; }
.alert-sev.info     { background: #1890ff; }
.alert-host { color: var(--primary); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.alert-msg { color: var(--text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 11px; }
.alert-value { font-family: var(--font-num); color: var(--primary); font-size: 12px; font-weight: 600; }

.fullscreen-btn {
  display: flex; align-items: center; gap: 4px; padding: 4px 10px; font-size: 12px;
  background: rgba(0,229,255,0.06); border: 1px solid var(--panel-border);
  color: var(--text-2); cursor: pointer; transition: all 0.2s; border-radius: 2px;
  white-space: nowrap; font-family: var(--font-cn);
}
.fullscreen-btn:hover { border-color: var(--primary); color: var(--primary); background: rgba(0,229,255,0.12); }
</style>
