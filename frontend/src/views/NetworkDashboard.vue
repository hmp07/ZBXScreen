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
        <div class="title-main">网 络 设 备 监 控 大 屏</div>
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

    <!-- Main Area (3 columns × 2 rows) -->
    <section class="main-area">
      <!-- R1C1: 设备分类统计 -->
      <div class="panel r1c1">
        <span class="corner-tr"></span><span class="corner-bl"></span>
        <div class="panel-title">
          <div class="panel-title-text">设 备 分 类 统 计 <span class="panel-title-en">DEVICE CATEGORIES</span></div>
          <div class="panel-title-tools"><span class="live">静态</span></div>
        </div>
        <div class="panel-body no-pad">
          <div class="cat-grid">
            <div v-for="cat in deviceCats" :key="cat.name" class="cat-card">
              <div class="cat-icon">{{ cat.icon }}</div>
              <div>
                <div class="cat-name">{{ cat.name }}</div>
                <div class="cat-row">
                  <span class="cat-total">{{ cat.total }}</span>
                  <span class="cat-up">▲{{ cat.up }}</span>
                  <span class="cat-down" v-if="cat.down">▼{{ cat.down }}</span>
                  <span v-if="cat.alerts" style="color:var(--danger);font-size:11px;margin-left:4px">⚠{{ cat.alerts }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- R1C2: 告警严重等级 -->
      <div class="panel r1c2">
        <span class="corner-tr"></span><span class="corner-bl"></span>
        <div class="panel-title">
          <div class="panel-title-text">告 警 严 重 等 级 <span class="panel-title-en">ALERT SEVERITY</span></div>
          <div class="panel-title-tools"><span class="live">实时</span></div>
        </div>
        <div class="panel-body no-pad"><div ref="sevChartRef" class="chart"></div></div>
      </div>

      <!-- R1C3: 厂商分布 -->
      <div class="panel r1c3">
        <span class="corner-tr"></span><span class="corner-bl"></span>
        <div class="panel-title">
          <div class="panel-title-text">设 备 厂 商 分 布 <span class="panel-title-en">VENDOR</span></div>
          <div class="panel-title-tools"><span class="live">静态</span></div>
        </div>
        <div class="panel-body no-pad"><div ref="vendorChartRef" class="chart"></div></div>
      </div>

      <!-- R2C1: 端口流量 TOP 10 -->
      <div class="panel r2c1">
        <span class="corner-tr"></span><span class="corner-bl"></span>
        <div class="panel-title">
          <div class="panel-title-text">端 口 流 量 TOP 10 <span class="panel-title-en">PORT TRAFFIC</span></div>
          <div class="panel-title-tools"><span class="live">30s 刷新</span></div>
        </div>
        <div class="panel-body no-pad"><div ref="trafficChartRef" class="chart"></div></div>
      </div>

      <!-- R2C2: 端口利用率 TOP 10 -->
      <div class="panel r2c2">
        <span class="corner-tr"></span><span class="corner-bl"></span>
        <div class="panel-title">
          <div class="panel-title-text">端 口 利 用 率 TOP 10 <span class="panel-title-en">PORT UTIL</span></div>
          <div class="panel-title-tools"><span class="live">30s 刷新</span></div>
        </div>
        <div class="panel-body no-pad"><div ref="utilChartRef" class="chart"></div></div>
      </div>

      <!-- R2C3: 接口CRC错误 TOP 10 -->
      <div class="panel r2c3">
        <span class="corner-tr"></span><span class="corner-bl"></span>
        <div class="panel-title">
          <div class="panel-title-text">接 口 CRC 错 误 TOP 10 <span class="panel-title-en">INTERFACE CRC ERRORS</span></div>
          <div class="panel-title-tools"><span class="live">静态</span></div>
        </div>
        <div class="panel-body no-pad"><div ref="crcChartRef" class="chart"></div></div>
      </div>
    </section>

    <!-- Alert Bar -->
    <section class="alert-bar">
      <div class="panel alert-list">
        <span class="corner-tr"></span><span class="corner-bl"></span>
        <div class="panel-title">
          <div class="panel-title-text">实 时 网 络 告 警 <span class="panel-title-en">LIVE NETWORK ALERTS</span></div>
          <div class="panel-title-tools"><span class="live">滚动</span></div>
        </div>
        <div class="alert-list-header">
          <div>时间</div><div>等级</div><div>设备 / 描述</div><div style="text-align:center">状态</div>
        </div>
        <div class="alert-list-body" ref="alertBodyRef">
          <div class="alert-list-inner" ref="alertInnerRef" :style="{ transform: 'translateY(-' + alertOffset + 'px)' }">
            <div v-for="a in recentAlerts" :key="a.id" class="alert-row">
              <div class="alert-time">{{ formatTime(a.created_at) }}</div>
              <div><span class="alert-sev" :class="a.level?.toLowerCase()">{{ sevLabel(a.level) }}</span></div>
              <div>
                <div class="alert-host">{{ a.host_name }}</div>
                <div class="alert-msg">{{ a.trigger_name }}</div>
              </div>
              <div style="text-align:center"><span class="alert-status problem">告警</span></div>
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
import { getNetworkDashboard } from '@/api/network'
import { getSettings } from '@/api/settings'
import { useLayoutStore } from '@/stores/layout'

const layoutStore = useLayoutStore()
const brandName = ref('ZBXBoard')
const brandSub = ref('NETWORK · VISUALIZATION')
const logoLetter = ref('Z')
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
const sevChartRef = ref<HTMLElement>()
const vendorChartRef = ref<HTMLElement>()
const trafficChartRef = ref<HTMLElement>()
const utilChartRef = ref<HTMLElement>()
const crcChartRef = ref<HTMLElement>()
const alertBodyRef = ref<HTMLElement>()
const alertInnerRef = ref<HTMLElement>()
const alertOffset = ref(0)
let sevChart: echarts.ECharts | null = null
let vendorChart: echarts.ECharts | null = null
let trafficChart: echarts.ECharts | null = null
let utilChart: echarts.ECharts | null = null
let crcChart: echarts.ECharts | null = null
let clockTimer: number, dataTimer: number, alertScrollTimer: number

const summary = ref({ total: 0, online: 0, offline: 0, alert_devices: 0, total_traffic_mbps: 0 })
const bySeverity = ref<Record<string, number>>({})
const portTraffic = ref<any[]>([])
const portUtil = ref<any[]>([])
const recentAlerts = ref<any[]>([])
const deviceCats = ref<any[]>([])
const vendorData = ref<{name: string; value: number; color: string}[]>([])
const crcData = ref<any[]>([])


const kpis = computed(() => [
  { key: 'total', label: '设备总数', unit: '台', icon: '🖥️', value: summary.value.total, color: '#00e5ff', alert: false, display: summary.value.total.toLocaleString() },
  { key: 'online', label: '在线设备', unit: '台', icon: '✅', value: summary.value.online, color: '#52c41a', alert: false, display: summary.value.online.toLocaleString() },
  { key: 'offline', label: '离线设备', unit: '台', icon: '🔴', value: summary.value.offline, color: summary.value.offline > 0 ? '#f5222d' : '#6b89a3', alert: summary.value.offline > 0, display: summary.value.offline.toLocaleString() },
  { key: 'alerts', label: '告警设备', unit: '台', icon: '🚨', value: summary.value.alert_devices, color: summary.value.alert_devices > 0 ? '#faad14' : '#00e5ff', alert: summary.value.alert_devices > 0, display: summary.value.alert_devices.toLocaleString() },
  { key: 'traffic', label: '端口总流量', unit: 'Mbps', icon: '📊', value: summary.value.total_traffic_mbps, color: '#00e5ff', alert: false, display: summary.value.total_traffic_mbps.toFixed(1) },
])

function pad(n: number) { return String(n).padStart(2,'0') }
function sevLabel(level: string) { return LEVEL_LABELS[level] || level }
function formatTime(t: string | null) {
  if (!t) return '--:--:--'; const d = new Date(t); return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
function tickClock() {
  const d = new Date()
  clock.value = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  clockDate.value = `${d.getFullYear()}.${pad(d.getMonth()+1)}.${pad(d.getDate())} ${WEEK_CN[d.getDay()]}`
}

async function fetchData() {
  try {
    const res = await getNetworkDashboard()
    if (res.data.code === 0) {
      const d = res.data.data
      summary.value = d.summary
      bySeverity.value = d.by_severity
      portTraffic.value = d.port_traffic_top10 || []
      portUtil.value = d.port_util_top10 || []
      recentAlerts.value = d.recent_alerts || []
      deviceCats.value = d.device_categories || []
      vendorData.value = d.vendor_distribution || []
      crcData.value = d.crc_errors_top10 || []
      updateCharts()
    }
  } catch(e) { /* silent */ }
}

function initCharts() {
  sevChart = echarts.init(sevChartRef.value!, 'dark')
  vendorChart = echarts.init(vendorChartRef.value!, 'dark')
  trafficChart = echarts.init(trafficChartRef.value!, 'dark')
  utilChart = echarts.init(utilChartRef.value!, 'dark')
  crcChart = echarts.init(crcChartRef.value!, 'dark')
}

function updateCharts() {
  updateSevChart()
  updateVendorChart()
  updateTrafficChart()
  updateUtilChart()
  updateCrcChart()
}

function updateSevChart() {
  if (!sevChart) return
  const levels = ['DISASTER', 'HIGH', 'AVERAGE', 'WARNING', 'INFO']
  const total = levels.reduce((s, l) => s + (bySeverity.value[l] || 0), 0)
  sevChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 }, formatter: '{b}: {c} ({d}%)' },
    graphic: [
      { type: 'text', left: 'center', top: '42%', style: { text: total, fill: '#e6f7ff', fontSize: 24, fontWeight: 900, fontFamily: 'Orbitron, monospace', textAlign: 'center' } },
      { type: 'text', left: 'center', top: '58%', style: { text: '活跃告警', fill: '#6b89a3', fontSize: 11, textAlign: 'center' } },
    ],
    series: [{
      type: 'pie', radius: ['50%','76%'], center: ['50%','50%'],
      label: { color: '#a8c4d8', fontSize: 10, formatter: '{b}\n{d}%' },
      itemStyle: { borderColor: '#050d1a', borderWidth: 2 },
      data: levels.map(l => ({ name: LEVEL_LABELS[l], value: bySeverity.value[l] || 0, itemStyle: { color: LEVEL_COLORS[l] } })),
    }],
  }, true)
}

function updateVendorChart() {
  if (!vendorChart) return
  vendorChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 }, formatter: '{b}: {c} 台 ({d}%)' },
    series: [{
      type: 'pie', radius: ['48%','74%'], center: ['50%','50%'],
      label: { color: '#a8c4d8', fontSize: 10, formatter: '{b}\n{d}%' },
      itemStyle: { borderColor: '#050d1a', borderWidth: 2 },
      data: vendorData.value.map((v: any) => ({ name: v.name, value: v.value, itemStyle: { color: v.color } })),
    }],
  }, true)
}

function updateTrafficChart() {
  if (!trafficChart) return
  const data = portTraffic.value
  trafficChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 12, right: 40, top: 10, bottom: 16 },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 } },
    legend: { data: ['入流量','出流量'], textStyle: { color: '#a8c4d8', fontSize: 10 }, right: 6, top: 2 },
    xAxis: { type: 'value', name: 'Mbps', axisLabel: { color: '#6b89a3', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } } },
    yAxis: { type: 'category', data: data.map((d: any) => (d.device?.length > 14 ? d.device.slice(0,14)+'…' : d.device) + ' | ' + (d.port||'')).reverse(), axisLabel: { color: '#a8c4d8', fontSize: 10 }, axisLine: { lineStyle: { color: '#455a72' } } },
    series: [
      { name: '入流量', type: 'bar', stack: 'total', data: data.map((d: any) => d.in_mbps).reverse(), itemStyle: { color: '#00e5ff' }, barWidth: 14 },
      { name: '出流量', type: 'bar', stack: 'total', data: data.map((d: any) => d.out_mbps).reverse(), itemStyle: { color: '#7b61ff' }, barWidth: 14 },
    ],
  }, true)
}

function updateUtilChart() {
  if (!utilChart) return
  const data = portUtil.value
  utilChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 12, right: 40, top: 10, bottom: 16 },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 }, formatter: '{b}: {c}%' },
    xAxis: { type: 'value', max: 100, name: '%', axisLabel: { color: '#6b89a3', fontSize: 9, formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } } },
    yAxis: { type: 'category', data: data.map((d: any) => (d.device?.length > 14 ? d.device.slice(0,14)+'…' : d.device)).reverse(), axisLabel: { color: '#a8c4d8', fontSize: 10 }, axisLine: { lineStyle: { color: '#455a72' } } },
    series: [{
      type: 'bar', data: data.map((d: any) => d.util_pct).reverse(),
      itemStyle: { color: new echarts.graphic.LinearGradient(0,0,1,0,[{offset:0,color:'#52c41a'},{offset:0.7,color:'#faad14'},{offset:1,color:'#f5222d'}]) },
      barWidth: 14,
    }],
  }, true)
}

function updateCrcChart() {
  if (!crcChart) return
  const data = crcData.value
  crcChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 12, right: 50, top: 10, bottom: 16 },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 },
      formatter: (params: any) => {
        const n = params[0].name
        const d = data.find((x: any) => (x.device + ' | ' + x.port) === n)
        const inn = d?.in_errors ?? 0; const out = d?.out_errors ?? 0
        return `${n}<br/>CRC错误总计: ${params[0].value.toLocaleString()} 个<br/>入方向: ${inn.toLocaleString()} · 出方向: ${out.toLocaleString()}`
      }
    },
    xAxis: { type: 'value', name: '个', axisLabel: { color: '#6b89a3', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } } },
    yAxis: { type: 'category', data: data.map((d: any) => d.device + ' | ' + d.port).reverse(), axisLabel: { color: '#a8c4d8', fontSize: 10 }, axisLine: { lineStyle: { color: '#455a72' } } },
    series: [{
      type: 'bar', data: data.map((d: any) => d.errors).reverse(),
      itemStyle: { color: (params: any) => params.value > 10000 ? '#f5222d' : params.value > 5000 ? '#faad14' : '#fa8c16' },
      barWidth: 14,
      markLine: { silent: true, symbol: 'none', lineStyle: { color: '#f5222d', type: 'dashed', width: 1 }, label: { color: '#f5222d', fontSize: 9, formatter: '告警 10000' }, data: [{ xAxis: 10000 }] },
    }],
  }, true)
}

watch(theme, (v) => { document.body.dataset.theme = v })

onMounted(async () => {
  try {
    const sRes = await getSettings()
    const s = sRes.data.data
    if (s.SYSTEM_TITLE) { brandName.value = s.SYSTEM_TITLE; logoLetter.value = s.SYSTEM_TITLE.charAt(0) }
    if (s.SYSTEM_SUBTITLE) brandSub.value = s.SYSTEM_SUBTITLE
    if (s.SYSTEM_LOGO) logoUrl.value = s.SYSTEM_LOGO
  } catch(e) { /* defaults */ }

  await fetchData()
  tickClock()
  clockTimer = window.setInterval(tickClock, 1000)
  dataTimer = window.setInterval(fetchData, 30000)
  await nextTick()
  initCharts()
  updateCharts()
  alertScrollTimer = window.setInterval(() => {
    if (!alertBodyRef.value || !alertInnerRef.value) return
    const rowH = 36, maxScroll = alertInnerRef.value.scrollHeight - alertBodyRef.value.clientHeight
    alertOffset.value = alertOffset.value >= maxScroll ? 0 : alertOffset.value + rowH
  }, 2500)
})

onUnmounted(() => {
  clearInterval(clockTimer); clearInterval(dataTimer); clearInterval(alertScrollTimer)
  sevChart?.dispose(); vendorChart?.dispose(); trafficChart?.dispose(); utilChart?.dispose(); crcChart?.dispose()
})
</script>

<style scoped>
.dashboard {
  position: relative; width: 100%; height: 100%;
  display: grid; grid-template-rows: 7.4vh 10.2vh 1fr 22.2vh; grid-template-columns: 1fr;
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
.title-deco { position: absolute; left: 50%; top: 50%; transform: translate(-50%,-50%); width: 440px; height: 64px; border: 1px solid var(--panel-border); pointer-events: none; }
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
  display: flex; align-items: center; padding: 0 22px; gap: 18px; overflow: hidden;
}
.kpi::after { content: ''; position: absolute; width: 14px; height: 14px; border: 2px solid var(--primary); opacity: 0.8; bottom: -2px; right: -2px; border-left: 0; border-top: 0; }
.kpi-glow { position: absolute; width: 200px; height: 200px; background: radial-gradient(circle, var(--primary-glow), transparent 70%); right: -60px; top: -60px; opacity: 0.3; pointer-events: none; }
.kpi-icon { width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; font-size: 28px; background: linear-gradient(135deg, rgba(0,229,255,0.18), rgba(0,229,255,0.04)); border: 1px solid var(--panel-border); border-radius: 6px; flex-shrink: 0; }
.kpi.alert .kpi-icon { background: linear-gradient(135deg, rgba(245,34,45,0.18), rgba(245,34,45,0.04)); border-color: rgba(245,34,45,0.3); }
.kpi-body { flex: 1; min-width: 0; }
.kpi-label { font-size: 13px; color: var(--text-2); letter-spacing: 2px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
.kpi-label::before { content: ''; display: inline-block; width: 3px; height: 10px; background: var(--primary); }
.kpi-value-row { display: flex; align-items: baseline; gap: 6px; }
.kpi-value { font-family: var(--font-num); font-size: 38px; font-weight: 900; line-height: 1; text-shadow: 0 0 14px var(--primary-glow); }
.kpi-unit { font-size: 14px; color: var(--text-3); }

.main-area { display: grid; grid-template-columns: 1fr 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 0.625vw; min-height: 0; }
.main-area > .panel { min-height: 0; }
.r1c1 { grid-row: 1; grid-column: 1; }
.r1c2 { grid-row: 1; grid-column: 2; }
.r1c3 { grid-row: 1; grid-column: 3; }
.r2c1 { grid-row: 2; grid-column: 1; }
.r2c2 { grid-row: 2; grid-column: 2; }
.r2c3 { grid-row: 2; grid-column: 3; }

.alert-bar { display: grid; grid-template-columns: 1fr; min-height: 0; }

.cat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 10px 12px; }
.cat-card {
  display: grid; grid-template-columns: 36px 1fr; gap: 8px; align-items: center;
  padding: 8px 10px; background: rgba(0,229,255,0.04); border: 1px solid rgba(0,229,255,0.12);
  border-left: 3px solid var(--primary);
}
.cat-icon { font-size: 20px; display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; background: rgba(0,229,255,0.1); border-radius: 6px; }
.cat-name { font-size: 11px; color: var(--text-2); letter-spacing: 1px; margin-bottom: 2px; }
.cat-row { display: flex; align-items: baseline; gap: 4px; font-family: var(--font-num); }
.cat-total { font-size: 16px; font-weight: 900; color: var(--text-1); }
.cat-up { font-size: 10px; color: var(--success); }
.cat-down { font-size: 10px; color: var(--danger); }

.alert-list { height: 100%; display: flex; flex-direction: column; }
.alert-list-header {
  display: grid; grid-template-columns: 100px 60px 1fr 90px; align-items: center; gap: 12px;
  padding: 0 16px; height: 30px; font-size: 11px; color: var(--text-3); letter-spacing: 1px;
  border-bottom: 1px solid rgba(0,229,255,0.1); background: rgba(0,229,255,0.04); flex-shrink: 0;
}
.alert-list-body { flex: 1; overflow: hidden; position: relative; }
.alert-list-inner { position: absolute; inset: 0; padding: 4px 0; transition: transform 0.6s ease; }
.alert-row {
  display: grid; grid-template-columns: 100px 60px 1fr 90px; align-items: center; gap: 12px;
  padding: 0 16px; height: 34px; font-size: 12px;
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
.alert-status { font-size: 11px; padding: 2px 8px; border-radius: 2px; text-align: center; }
.alert-status.problem { color: var(--danger); border: 1px solid var(--danger); }

.fullscreen-btn {
  display: flex; align-items: center; gap: 4px; padding: 4px 10px; font-size: 12px;
  background: rgba(0,229,255,0.06); border: 1px solid var(--panel-border);
  color: var(--text-2); cursor: pointer; transition: all 0.2s; border-radius: 2px;
  white-space: nowrap; font-family: var(--font-cn);
}
.fullscreen-btn:hover { border-color: var(--primary); color: var(--primary); background: rgba(0,229,255,0.12); }
</style>
