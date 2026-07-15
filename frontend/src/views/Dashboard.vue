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
            <div class="title-main">{{ systemTitle }}</div>
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
          <div v-for="k in kpis" :key="k.key" class="kpi">
            <div class="kpi-glow"></div>
            <!-- 主机总数：复合卡片（主数据 + 子数据水平分隔） -->
            <template v-if="k.key === 'hosts'">
              <div class="kpi-body">
                <div class="kpi-label">{{ k.label }}</div>
                <div class="kpi-split">
                  <div class="kpi-main">
                    <div class="kpi-value" data-key="hosts">{{ formatKpi(k) }}</div>
                    <div class="kpi-unit">{{ k.unit }}</div>
                  </div>
                  <div class="kpi-divider"></div>
                  <div class="kpi-subs">
                    <div class="kpi-sub-label">启用</div>
                    <div class="kpi-sub">
                      <span class="kpi-sub-dot enabled"></span>
                      <span class="kpi-sub-val">{{ (summary.enabled_hosts || 0).toLocaleString() }}</span>
                      <span class="kpi-sub-unit">台</span>
                    </div>
                    <div class="kpi-sub-gap"></div>
                    <div class="kpi-sub-label">停用</div>
                    <div class="kpi-sub">
                      <span class="kpi-sub-dot disabled"></span>
                      <span class="kpi-sub-val">{{ (summary.disabled_hosts || 0).toLocaleString() }}</span>
                      <span class="kpi-sub-unit">台</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <!-- 其他卡片：标准布局 -->
            <template v-else>
              <div class="kpi-icon">{{ k.icon }}</div>
              <div class="kpi-body">
                <div class="kpi-label">{{ k.label }}</div>
                <div class="kpi-value-row">
                  <div class="kpi-value">{{ formatKpi(k) }}</div>
                  <div class="kpi-unit">{{ k.unit }}</div>
                </div>
                <div class="kpi-delta" :class="k.trend">
                  <span>{{ k.trend === 'up' ? '▲' : k.trend === 'down' ? '▼' : '—' }}</span>
                  <span>{{ Math.abs(k.delta) }}{{ k.key === 'cpu' ? 'pp' : '' }}</span>
                  <span style="color:var(--text-3);font-family:var(--font-cn)">较 1h 前</span>
                </div>
              </div>
            </template>
          </div>
        </section>

        <!-- Main Area -->
        <section class="main-area">
          <div class="col-stack">
            <div class="panel">
              <span class="corner-tr"></span><span class="corner-bl"></span>
              <div class="panel-title">
                <div class="panel-title-text">主 机 CPU TOP 5 <span class="panel-title-en">CPU RANKING</span></div>
                <div class="panel-title-tools"><span class="live">3s 刷新</span></div>
              </div>
              <div class="panel-body no-pad">
                <div class="top-list">
                  <div v-for="(it, idx) in topCpu" :key="idx" class="top-item">
                    <div class="top-rank" :class="'r' + (idx + 1)">{{ idx + 1 }}</div>
                    <div class="top-info">
                      <div class="top-host">{{ it.host }}</div>
                      <div class="top-bar"><div class="top-bar-fill" :style="{ width: (it.value / 100 * 100) + '%' }"></div></div>
                    </div>
                    <div class="top-value"><span class="top-value-num">{{ it.value?.toFixed(1) }}</span><span class="top-value-unit">%</span></div>
                  </div>
                </div>
              </div>
            </div>
            <div class="panel">
              <span class="corner-tr"></span><span class="corner-bl"></span>
              <div class="panel-title">
                <div class="panel-title-text">主 机 内 存 TOP 5 <span class="panel-title-en">MEMORY RANKING</span></div>
                <div class="panel-title-tools"><span class="live">3s 刷新</span></div>
              </div>
              <div class="panel-body no-pad">
                <div class="top-list">
                  <div v-for="(it, idx) in topMem" :key="idx" class="top-item">
                    <div class="top-rank" :class="'r' + (idx + 1)">{{ idx + 1 }}</div>
                    <div class="top-info">
                      <div class="top-host">{{ it.host }}</div>
                      <div class="top-bar"><div class="top-bar-fill" :style="{ width: (it.value / 100 * 100) + '%' }"></div></div>
                    </div>
                    <div class="top-value"><span class="top-value-num">{{ it.value?.toFixed(1) }}</span><span class="top-value-unit">%</span></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="col-stack">
            <div class="panel">
              <span class="corner-tr"></span><span class="corner-bl"></span>
              <div class="panel-title">
                <div class="panel-title-text">资 源 实 时 趋 势 <span class="panel-title-en">REAL-TIME TREND</span></div>
                <div class="panel-title-tools"><span class="live">5s 刷新</span></div>
              </div>
              <div class="panel-body no-pad"><div ref="trendChartRef" class="chart"></div></div>
            </div>
            <div class="panel">
              <span class="corner-tr"></span><span class="corner-bl"></span>
              <div class="panel-title">
                <div class="panel-title-text">主 机 状 态 <span class="panel-title-en">HOST STATUS</span></div>
                <div class="panel-title-tools"><span class="live">实时</span></div>
              </div>
              <div class="panel-body no-pad"><div ref="statusChartRef" class="chart"></div></div>
            </div>
          </div>

          <div class="col-stack">
            <div class="panel">
              <span class="corner-tr"></span><span class="corner-bl"></span>
              <div class="panel-title">
                <div class="panel-title-text">发 送 流 量 TOP 5 <span class="panel-title-en">TX RANKING</span></div>
                <div class="panel-title-tools"><span class="live">3s 刷新</span></div>
              </div>
              <div class="panel-body no-pad">
                <div class="top-list">
                  <div v-for="(it, idx) in topTx" :key="idx" class="top-item">
                    <div class="top-rank" :class="'r' + (idx + 1)">{{ idx + 1 }}</div>
                    <div class="top-info">
                      <div class="top-host">{{ it.host }}</div>
                      <div class="top-bar"><div class="top-bar-fill" :style="{ width: Math.max(it.value / 10, 0.5) + '%' }"></div></div>
                    </div>
                    <div class="top-value"><span class="top-value-num">{{ it.value?.toFixed(2) }}</span><span class="top-value-unit">Mbps</span></div>
                  </div>
                </div>
              </div>
            </div>
            <div class="panel">
              <span class="corner-tr"></span><span class="corner-bl"></span>
              <div class="panel-title">
                <div class="panel-title-text">接 收 流 量 TOP 5 <span class="panel-title-en">RX RANKING</span></div>
                <div class="panel-title-tools"><span class="live">3s 刷新</span></div>
              </div>
              <div class="panel-body no-pad">
                <div class="top-list">
                  <div v-for="(it, idx) in topRx" :key="idx" class="top-item">
                    <div class="top-rank" :class="'r' + (idx + 1)">{{ idx + 1 }}</div>
                    <div class="top-info">
                      <div class="top-host">{{ it.host }}</div>
                      <div class="top-bar"><div class="top-bar-fill" :style="{ width: Math.max(it.value / 10, 0.5) + '%' }"></div></div>
                    </div>
                    <div class="top-value"><span class="top-value-num">{{ it.value?.toFixed(2) }}</span><span class="top-value-unit">Mbps</span></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Alert Bar -->
        <section class="alert-bar">
          <div class="panel alert-list">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title">
              <div class="panel-title-text">实 时 告 警 <span class="panel-title-en">LIVE ALERTS</span></div>
              <div class="panel-title-tools"><span class="live">滚动</span></div>
            </div>
            <div class="alert-list-header">
              <div>时间</div><div>等级</div><div>主机 / 描述</div><div style="text-align:center">状态</div>
            </div>
            <div class="alert-list-body" ref="alertBodyRef">
              <div class="alert-list-inner" ref="alertInnerRef" :style="{ transform: 'translateY(-' + alertOffset + 'px)' }">
                <div v-for="a in alerts" :key="a.id" class="alert-row" :class="{ new: a.isNew }">
                  <div class="alert-time">{{ formatAlertTime(a.first_occurred) }}</div>
                  <div><span class="alert-sev" :class="a.level?.toLowerCase()">{{ sevLabel(a.level) }}</span></div>
                  <div>
                    <div class="alert-host">{{ a.host_name }}</div>
                    <div class="alert-msg">{{ a.trigger_name }}</div>
                  </div>
                  <div style="text-align:center"><span class="alert-status" :class="a.status === 'active' ? 'problem' : a.status === 'recovered' ? 'ok' : 'ack'">{{ a.status === 'active' ? '告警' : a.status === 'recovered' ? '已恢复' : '已确认' }}</span></div>
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
import { getSummary, getHosts, getAlerts, getTopCpu, getTopMemory, getTopDisk, getTopNetworkIn, getTopNetworkOut } from '@/api/monitor'
import { getSettings } from '@/api/settings'
import { useLayoutStore } from '@/stores/layout'
import { formatDateTime } from '@/utils/format'

const layoutStore = useLayoutStore()
const brandName = computed(() => layoutStore.brandTitle || 'ZBXBoard')
const brandSub = ref('')
const logoLetter = computed(() => layoutStore.brandTitle?.charAt(0) || 'Z')
const logoUrl = ref('')

const WEEK_CN = ['周日','周一','周二','周三','周四','周五','周六']
const themes = ['cyan','purple','green','orange']
const theme = ref('cyan')
const clock = ref('--:--:--')
const clockDate = ref('----年--月--日')
const systemTitle = ref('数 据 中 心 监 控 大 屏')
const trendChartRef = ref<HTMLElement>()
const statusChartRef = ref<HTMLElement>()
const alertBodyRef = ref<HTMLElement>()
const alertInnerRef = ref<HTMLElement>()
const alertOffset = ref(0)
let trendChart: echarts.ECharts | null = null
let statusChart: echarts.ECharts | null = null
let clockTimer: number, dataTimer: number, alertScrollTimer: number

const summary = ref({ total_hosts: 0, enabled_hosts: 0, disabled_hosts: 0, online_hosts: 0, offline_hosts: 0, alert_count: 0 })
const hosts = ref<any[]>([])
const alerts = ref<any[]>([])
const topCpu = ref<{ host: string; value: number }[]>([])
const topMem = ref<{ host: string; value: number }[]>([])
const topTx = ref<{ host: string; value: number }[]>([])
const topRx = ref<{ host: string; value: number }[]>([])

// Rolling window for real-time trend (last 30 samples from real data)
const HISTORY_WINDOW = 30
const trendHistory = ref<{ time: string; cpu: number; mem: number; disk: number; net: number }[]>([])

const cpuAvg = computed(() => {
  if (topCpu.value.length === 0) return 0
  return topCpu.value.reduce((s, x) => s + x.value, 0) / topCpu.value.length
})
const memAvg = computed(() => {
  if (topMem.value.length === 0) return 0
  return topMem.value.reduce((s, x) => s + x.value, 0) / topMem.value.length
})

const kpis = computed(() => [
  { key: 'hosts' as const, label: '主机总数', unit: '台', icon: '🖥️', value: summary.value.total_hosts, delta: 0, trend: 'flat' as 'flat' | 'up' | 'down' },
  { key: 'online' as const, label: '在线主机', unit: '台', icon: '✅', value: summary.value.online_hosts, delta: 0, trend: 'flat' as 'flat' | 'up' | 'down', color: '#52c41a' },
  { key: 'offline' as const, label: '离线主机', unit: '台', icon: '🔴', value: summary.value.offline_hosts, delta: 0, trend: 'flat' as 'flat' | 'up' | 'down', color: '#f5222d' },
  { key: 'alerts' as const, label: '告警总数', unit: '条', icon: '🚨', value: summary.value.alert_count, delta: 0, trend: 'flat' as 'flat' | 'up' | 'down' },
  { key: 'cpu' as const, label: 'CPU 均值', unit: '%', icon: '⚙️', value: cpuAvg.value, delta: 0, trend: 'flat' as 'flat' | 'up' | 'down' },
])

function pad(n: number) { return String(n).padStart(2, '0') }
function formatKpi(k: any) {
  if (k.key === 'cpu') return k.value?.toFixed(1) ?? '0.0'
  return Math.round(k.value || 0).toLocaleString()
}
function sevLabel(level: string) {
  const m: Record<string,string> = { DISASTER:'灾难', HIGH:'严重', AVERAGE:'一般', WARNING:'警告', INFO:'信息', NOT_CLASSIFIED:'未分' }
  return m[level] || level
}
function formatAlertTime(t: string | null) { return formatDateTime(t) }

function tickClock() {
  const d = new Date()
  clock.value = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  clockDate.value = `${d.getFullYear()}.${pad(d.getMonth()+1)}.${pad(d.getDate())} ${WEEK_CN[d.getDay()]}`
}


async function fetchData() {
  try {
    const [sRes, hRes, aRes, cpuRes, memRes, netInRes, netOutRes] = await Promise.all([
      getSummary(),
      getHosts({ limit: 100 }),
      getAlerts({ limit: 50 }),
      getTopCpu({ limit: 5 }),
      getTopMemory({ limit: 5 }),
      getTopNetworkIn({ limit: 5 }),
      getTopNetworkOut({ limit: 5 }),
    ])
    if (sRes.data.code === 0) summary.value = sRes.data.data
    if (hRes.data.code === 0) hosts.value = hRes.data.data
    if (aRes.data.code === 0) alerts.value = aRes.data.data
    if (cpuRes.data.code === 0) topCpu.value = cpuRes.data.data || []
    if (memRes.data.code === 0) topMem.value = memRes.data.data || []
    if (netInRes.data.code === 0) topRx.value = netInRes.data.data || []
    if (netOutRes.data.code === 0) topTx.value = netOutRes.data.data || []

    // Push real values into rolling trend window
    const now = new Date()
    const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
    const cpuArr = topCpu.value
    const memArr = topMem.value
    const rxArr = topRx.value
    trendHistory.value.push({
      time: timeStr,
      cpu: cpuArr.length > 0 ? cpuArr.reduce((s, x) => s + x.value, 0) / cpuArr.length : 0,
      mem: memArr.length > 0 ? memArr.reduce((s, x) => s + x.value, 0) / memArr.length : 0,
      disk: 0, // Disk TOP N not on dashboard main view by default
      net: rxArr.length > 0 ? rxArr.reduce((s, x) => s + x.value, 0) / rxArr.length : 0,
    })
    if (trendHistory.value.length > HISTORY_WINDOW) {
      trendHistory.value = trendHistory.value.slice(-HISTORY_WINDOW)
    }

    // Update trend chart with real rolling data
    updateTrendChart()
    // Update status pie
    updateStatusChart()
  } catch(e) {
    console.error("Dashboard fetchData failed:", e);
  }
}

function initTrendChart() {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value, 'dark')
  trendChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 50, right: 30, top: 36, bottom: 28 },
    legend: { data: ['CPU %','内存 %','磁盘 %','网络 Mbps'], textStyle: { color: '#a8c4d8', fontSize: 11 }, right: 10, top: 6, itemWidth: 14, itemHeight: 8, itemGap: 18 },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 } },
    xAxis: { type: 'category', data: [], boundaryGap: false, axisLine: { lineStyle: { color: '#455a72' } }, axisLabel: { color: '#6b89a3', fontSize: 10 } },
    yAxis: { type: 'value', max: 100, axisLabel: { color: '#6b89a3', fontSize: 10, formatter: '{value}' }, splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } } },
    series: [
      { name: 'CPU %', type: 'line', smooth: true, symbol: 'none', data: [], lineStyle: { width: 1.6, color: '#00e5ff', shadowBlur: 8, shadowColor: '#00e5ff' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,229,255,0.73)'},{offset:1,color:'rgba(0,229,255,0)'}]) } },
      { name: '内存 %', type: 'line', smooth: true, symbol: 'none', data: [], lineStyle: { width: 1.6, color: '#52c41a', shadowBlur: 8, shadowColor: '#52c41a' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(82,196,26,0.73)'},{offset:1,color:'rgba(82,196,26,0)'}]) } },
      { name: '磁盘 %', type: 'line', smooth: true, symbol: 'none', data: [], lineStyle: { width: 1.6, color: '#faad14', shadowBlur: 8, shadowColor: '#faad14' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(250,173,20,0.73)'},{offset:1,color:'rgba(250,173,20,0)'}]) } },
      { name: '网络 Mbps', type: 'line', smooth: true, symbol: 'none', data: [], lineStyle: { width: 1.6, color: '#7b61ff', shadowBlur: 8, shadowColor: '#7b61ff' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(123,97,255,0.73)'},{offset:1,color:'rgba(123,97,255,0)'}]) } },
    ]
  })
}

function updateTrendChart() {
  if (!trendChart) return
  const times = trendHistory.value.map(p => p.time)
  const cpuData = trendHistory.value.map(p => p.cpu)
  const memData = trendHistory.value.map(p => p.mem)
  const diskData = trendHistory.value.map(p => p.disk)
  const netData = trendHistory.value.map(p => p.net)
  trendChart.setOption({
    xAxis: { data: times },
    series: [
      { data: cpuData },
      { data: memData },
      { data: diskData },
      { data: netData },
    ]
  })
}

function initStatusChart() {
  if (!statusChartRef.value) return
  statusChart = echarts.init(statusChartRef.value, 'dark')
  updateStatusChart()
}

function updateStatusChart() {
  if (!statusChart) return
  const disabled = summary.value.disabled_hosts || 0
  const offline = summary.value.offline_hosts || 0
  const hasAlert = summary.value.alert_count || 0
  const healthy = Math.max(0, summary.value.online_hosts - hasAlert)
  statusChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 } },
    graphic: [
      { type: 'text', left: 'center', top: '38%', style: { text: summary.value.total_hosts, fill: '#e6f7ff', fontSize: 32, fontWeight: 900, fontFamily: 'Orbitron, monospace', textAlign: 'center' } },
      { type: 'text', left: 'center', top: '60%', style: { text: '总主机', fill: '#6b89a3', fontSize: 12, textAlign: 'center' } },
    ],
    series: [{
      type: 'pie', radius: ['52%','76%'], center: ['50%','50%'],
      label: { show: true, position: 'outside', color: '#a8c4d8', fontSize: 11, formatter: '{b}\n{c}' },
      labelLine: { length: 6, length2: 6, lineStyle: { color: '#455a72' } },
      itemStyle: { borderColor: '#050d1a', borderWidth: 2 },
      data: [
        { name: '健康', value: healthy, itemStyle: { color: '#52c41a' } },
        { name: '告警', value: hasAlert, itemStyle: { color: '#f5222d' } },
        { name: '离线', value: offline, itemStyle: { color: '#fa8c16' } },
        { name: '停用', value: disabled, itemStyle: { color: '#6b89a3' } },
      ]
    }]
  })
}

watch(theme, (v) => {
  document.body.dataset.theme = v
  trendChart?.setOption(trendChart!.getOption(), true)
  statusChart?.setOption(statusChart!.getOption(), true)
})

onMounted(async () => {
  // Load custom brand settings
  try {
    const sRes = await getSettings()
    const s = sRes.data.data
    // 品牌标题和图标由 AppLayout 统一加载到 layoutStore，此处不再覆盖
    if (s.SYSTEM_SUBTITLE) brandSub.value = s.SYSTEM_SUBTITLE
    if (s.SYSTEM_LOGO) logoUrl.value = s.SYSTEM_LOGO
  } catch(e) { /* use defaults */ }

  await fetchData()
  tickClock()
  clockTimer = window.setInterval(tickClock, 1000)
  dataTimer = window.setInterval(fetchData, 30000)
  await nextTick()
  initTrendChart()
  initStatusChart()
  alertScrollTimer = window.setInterval(() => {
    if (!alertBodyRef.value || !alertInnerRef.value) return
    const rowH = 42, maxScroll = alertInnerRef.value.scrollHeight - alertBodyRef.value.clientHeight
    alertOffset.value = alertOffset.value >= maxScroll ? 0 : alertOffset.value + rowH
  }, 2500)
})

onUnmounted(() => {
  clearInterval(clockTimer); clearInterval(dataTimer); clearInterval(alertScrollTimer)
  trendChart?.dispose(); statusChart?.dispose()
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
  box-shadow: 0 0 24px var(--primary-glow), inset 0 0 12px rgba(255,255,255,0.3); position: relative;
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
.kpi-strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 0.73vw; padding: 0 0.31vw; }
/* 主机总数复合卡片 */
.kpi-split { display: flex; align-items: center; gap: 0.5vw; }
.kpi-main { flex: 1; display: flex; align-items: baseline; gap: 6px; }
.kpi-divider { width: 1px; height: 3.2vh; background: rgba(0,229,255,0.15); }
.kpi-subs { display: flex; flex-direction: column; }
.kpi-sub-label { font-size: 11px; color: var(--text-3); letter-spacing: 1px; margin-bottom: 1px; }
.kpi-sub-gap { height: 4px; }
.kpi-sub { display: flex; align-items: baseline; gap: 6px; }
.kpi-sub-dot { width: 18px; height: 18px; border-radius: 50%; flex-shrink: 0; align-self: center; }
.kpi-sub-dot.enabled { background: #52c41a; box-shadow: 0 0 10px rgba(82,196,26,0.5); }
.kpi-sub-dot.disabled { background: #6b89a3; }
.kpi-sub-val { font-family: var(--font-num); font-size: 34px; font-weight: 900; color: var(--primary); line-height: 1.1; }
.kpi-sub-unit { font-size: 12px; color: var(--text-3); }
.main-area { display: grid; grid-template-columns: 3fr 5fr 3fr; gap: 0.625vw; min-height: 0; }
.col-stack { position: relative; display: grid; grid-template-rows: 1fr 1fr; gap: 0.625vw; min-height: 0; }
.col-stack > .panel { min-height: 0; }
.alert-bar { display: grid; grid-template-columns: 1fr; gap: 0.625vw; min-height: 0; }
.alert-list { height: 100%; display: flex; flex-direction: column; }
.alert-list-header {
  display: grid; grid-template-columns: 5.2vw 3.1vw 1fr 4.7vw; align-items: center; gap: 0.625vw;
  padding: 0 0.83vw; height: clamp(22px, 2.8vh, 30px); font-size: clamp(9px, 0.57vw, 11px); color: var(--text-3); letter-spacing: 0.05vw;
  border-bottom: 1px solid rgba(0,229,255,0.1); background: rgba(0,229,255,0.04); flex-shrink: 0;
}
.alert-list-body { flex: 1; overflow: hidden; position: relative; }
.alert-list-inner { position: absolute; inset: 0; padding: 0.3vw 0; transition: transform 0.6s ease; }
.alert-row.new { background: linear-gradient(90deg, rgba(245,34,45,0.25), transparent); animation: flash 2s ease-out; }
@keyframes flash { 0% { background: rgba(245,34,45,0.6); } 100% { background: transparent; } }
.alert-status { font-size: clamp(9px, 0.57vw, 11px); padding: 0.1vw 0.42vw; border-radius: 2px; text-align: center; }
.alert-status.problem { color: var(--danger); border: 1px solid var(--danger); }
.alert-status.ack     { color: var(--warning); border: 1px solid var(--warning); }
.alert-status.ok      { color: var(--success); border: 1px solid var(--success); }
.top-list { height: 100%; display: flex; flex-direction: column; padding: 0.3vw 0.52vw 0.42vw; gap: 0.3vw; overflow: hidden; }
.fullscreen-btn {
  display: flex; align-items: center; gap: 0.2vw; padding: 0.2vw 0.52vw; font-size: clamp(10px, 0.63vw, 12px);
  background: rgba(0, 229, 255, 0.06); border: 1px solid var(--panel-border);
  color: var(--text-2); cursor: pointer; transition: all 0.2s; border-radius: 2px;
  white-space: nowrap; font-family: var(--font-cn);
}
.fullscreen-btn:hover { border-color: var(--primary); color: var(--primary); background: rgba(0, 229, 255, 0.12); }
</style>
