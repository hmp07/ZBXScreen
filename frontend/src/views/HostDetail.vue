<template>
  
    
      <div class="dashboard">
        <!-- Top Bar -->
        <div class="topbar">
          <div class="breadcrumb">
            <a class="home" @click="$router.push('/dashboard')"><span class="home-logo">{{ layoutStore.brandTitle?.charAt(0) || 'Z' }}</span><span class="home-text">{{ layoutStore.brandTitle || 'ZBXScreen' }}</span></a>
            <span class="sep">/</span><a @click="$router.push('/hosts')">监控</a>
            <span class="sep">/</span><a @click="$router.push('/hosts')">主机管理</a>
            <span class="sep">/</span><span class="current">{{ host?.host || host?.name || '...' }}</span>
          </div>
          <div class="host-title">
            <span class="host-name">{{ host?.host || host?.name || '主机详情' }}</span>
            <span class="host-ip">{{ host?.interfaces?.[0]?.ip || '-' }}</span>
            <span class="status-badge" :class="host?.status === '0' ? 'ok' : 'problem'">{{ host?.status === '0' ? '在线' : '离线' }} · {{ triggerCount }} 个告警</span>
          </div>
          <div class="topbar-right">
            <div class="clock">{{ clock }}</div>
            <div class="theme-switcher">
              <div v-for="c in themes" :key="c" class="theme-dot" :class="{ active: theme === c }" :data-color="c" @click="theme = c"></div>
            </div>
            <div class="fullscreen-btn" @click="layoutStore.toggleFullscreen()" :title="layoutStore.isFullscreen ? '退出全屏' : '全屏展示'">
              {{ layoutStore.isFullscreen ? '⊠ 退出全屏' : '⊡ 全屏' }}
            </div>
            <a class="back-btn" @click="$router.push('/hosts')">← 返回列表</a>
          </div>
        </div>

        <!-- KPI Strip -->
        <section class="kpi-strip">
          <div class="kpi" v-for="k in kpis" :key="k.key">
            <div class="kpi-icon">{{ k.icon }}</div>
            <div class="kpi-body">
              <div class="kpi-label">{{ k.label }}</div>
              <div class="kpi-value-row">
                <div class="kpi-value">{{ k.display }}</div>
                <div class="kpi-unit">{{ k.unit }}</div>
              </div>
              <div class="kpi-bar"><div class="kpi-bar-fill" :style="{ width: k.pct + '%' }"></div></div>
            </div>
          </div>
        </section>

        <!-- Main Area -->
        <section class="main-area">
          <!-- Host Info -->
          <div class="panel col-1">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title">
              <div class="panel-title-text">基 础 信 息 <span class="panel-title-en">HOST INFO</span></div>
              <div class="panel-title-tools">
                <span class="tabs">
                  <button class="tab" :class="{ active: infoTab === 'basic' }" @click="infoTab = 'basic'">基础</button>
                  <button class="tab" :class="{ active: infoTab === 'tags' }" @click="infoTab = 'tags'">标签</button>
                </span>
              </div>
            </div>
            <div class="panel-body"><div class="info-grid">
              <template v-if="infoTab === 'basic'">
                <div class="info-cell"><div class="info-cell-label">主机名</div><div class="info-cell-value highlight">{{ host?.host }}</div></div>
                <div class="info-cell"><div class="info-cell-label">可见名</div><div class="info-cell-value">{{ host?.name }}</div></div>
                <div class="info-cell"><div class="info-cell-label">IP 地址</div><div class="info-cell-value highlight">{{ host?.interfaces?.[0]?.ip || '-' }}</div></div>
                <div class="info-cell"><div class="info-cell-label">DNS</div><div class="info-cell-value">{{ host?.interfaces?.[0]?.dns || '-' }}</div></div>
                <div class="info-cell"><div class="info-cell-label">状态</div><div class="info-cell-value">{{ host?.status === '0' ? '✅ 在线' : '🔴 离线' }}</div></div>
                <div class="info-cell"><div class="info-cell-label">可用性</div><div class="info-cell-value highlight">ZBX</div></div>
                <div class="info-cell"><div class="info-cell-label">主机组</div><div class="info-cell-value">{{ host?.groups?.map((g:any) => g.name).join(' / ') || '-' }}</div></div>
                <div class="info-cell"><div class="info-cell-label">描述</div><div class="info-cell-value">{{ host?.description || '-' }}</div></div>
              </template>
              <template v-if="infoTab === 'tags'">
                <div class="info-cell" v-for="g in host?.groups || []" :key="g.groupid">
                  <div class="info-cell-label">主机组</div>
                  <div class="info-cell-value"><span class="tag">{{ g.name }}</span></div>
                </div>
                <div v-if="!host?.groups?.length" class="info-cell"><div class="info-cell-label">标签</div><div class="info-cell-value">无</div></div>
              </template>
            </div></div>
          </div>

          <!-- Triggers -->
          <div class="panel col-2">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title">
              <div class="panel-title-text">触 发 器 <span class="panel-title-en">TRIGGERS</span></div>
              <div class="panel-title-tools">
                <span class="tabs">
                  <button class="tab" :class="{ active: trigTab === 'current' }" @click="trigTab = 'current'">当前问题 ({{ activeTriggers.length }})</button>
                  <button class="tab" :class="{ active: trigTab === 'recent' }" @click="trigTab = 'recent'">最近</button>
                </span>
              </div>
            </div>
            <div class="panel-body"><div class="tlist">
              <div v-for="t in (trigTab === 'current' ? activeTriggers : recentTriggers)" :key="t.id" class="trow" :class="t.status === 'active' ? 'problem' : 'ok'">
                <div class="tdot"></div>
                <div>
                  <div class="tname"><span class="tsev" :class="t.level?.toLowerCase()">{{ sevLabel(t.level) }}</span>{{ t.trigger_name }}</div>
                  <div class="tmeta">{{ formatTime(t.created_at) }}</div>
                </div>
                <div class="tval">{{ t.value ?? '-' }}</div>
              </div>
              <div v-if="(trigTab === 'current' ? activeTriggers : recentTriggers).length === 0" style="color:var(--text-3);text-align:center;padding:20px">无触发器</div>
            </div></div>
          </div>

          <!-- Resource Trend + Items -->
          <div class="panel col-3">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title">
              <div class="panel-title-text">资 源 趋 势 <span class="panel-title-en">RESOURCE TREND</span></div>
              <div class="panel-title-tools">
                <span class="tabs">
                  <button class="tab" :class="{ active: itemCat === 'all' }" @click="itemCat = 'all'">全部</button>
                  <button class="tab" :class="{ active: itemCat === 'cpu' }" @click="itemCat = 'cpu'">CPU</button>
                  <button class="tab" :class="{ active: itemCat === 'mem' }" @click="itemCat = 'mem'">内存</button>
                  <button class="tab" :class="{ active: itemCat === 'disk' }" @click="itemCat = 'disk'">磁盘</button>
                  <button class="tab" :class="{ active: itemCat === 'net' }" @click="itemCat = 'net'">网络</button>
                </span>
              </div>
            </div>
            <div style="display:grid;grid-template-rows:320px 1fr;height:100%;min-height:0">
              <div style="padding:8px 14px;min-height:0"><div ref="trendChartRef" class="chart"></div></div>
              <div style="overflow:auto;min-height:0;border-top:1px solid rgba(0,229,255,0.1)">
                <table class="item-table"><thead><tr><th style="width:40%">监控项</th><th>当前值</th><th style="width:22%">趋势</th><th style="width:20%">采集时间</th></tr></thead><tbody>
                  <tr v-for="it in filteredItems" :key="it.key">
                    <td><div class="item-name">{{ it.name }}</div><div class="item-key">{{ it.key_ }}</div></td>
                    <td class="item-val" :class="it.warn ? 'warn' : ''">{{ it.lastvalue != null ? it.lastvalue : '-' }} <span class="item-meta">{{ it.units || '' }}</span></td>
                    <td><div class="spark" :ref="el => setSparkRef(it.key_, el as HTMLElement)"></div></td>
                    <td class="item-meta">{{ it.lastclock ? new Date(parseInt(it.lastclock) * 1000).toLocaleTimeString('zh-CN',{hour12:false}) : '-' }}</td>
                  </tr>
                </tbody></table>
              </div>
            </div>
          </div>
        </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { getHostDetail, getHostHistory } from '@/api/host'
import { useLayoutStore } from '@/stores/layout'

const layoutStore = useLayoutStore()

const route = useRoute()
const hostid = computed(() => route.params.hostid as string)
const datasourceId = computed(() => Number(route.query.datasource_id) || 1)
const host = ref<any>(null)
const metrics = ref<any>({})
const allItems = ref<any[]>([])
const triggerCount = ref(0)
const activeTriggers = ref<any[]>([])
const recentTriggers = ref<any[]>([])
const clock = ref('--:--:--')
const themes = ['cyan','purple','green','orange']
const theme = ref('cyan')
const scaleInner = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const infoTab = ref('basic')
const trigTab = ref('current')
const itemCat = ref('all')
let trendChart: echarts.ECharts | null = null
let clockTimer: number
const sparkRefs = new Map<string, HTMLElement>()

function pad(n: number) { return String(n).padStart(2, '0') }
function formatTime(t: string | null) { if (!t) return '-'; return new Date(t).toLocaleString('zh-CN') }
function sevLabel(level: string): string { const m: Record<string,string> = { DISASTER:'灾难', HIGH:'严重', AVERAGE:'一般', WARNING:'警告', INFO:'信息' }; return m[level] || level || '-' }
function setSparkRef(key: string, el: HTMLElement | null) { if (el) sparkRefs.set(key, el) }

const kpis = computed(() => {
  const cpu = metrics.value?.cpu_usage ?? 0, mem = metrics.value?.memory_usage ?? 0
  const disk = metrics.value?.disk_usage ?? 0, net = metrics.value?.network_in ?? 0
  return [
    { key: 'cpu', label: 'CPU 使用率', unit: '%', icon: '⚙️', value: cpu, display: Number(cpu).toFixed(1), pct: Math.min(100, Math.max(0, cpu)), max: 100 },
    { key: 'mem', label: '内存使用率', unit: '%', icon: '💾', value: mem, display: Number(mem).toFixed(1), pct: Math.min(100, Math.max(0, mem)), max: 100 },
    { key: 'disk', label: '磁盘使用率', unit: '%', icon: '💽', value: disk, display: Number(disk).toFixed(1), pct: Math.min(100, Math.max(0, disk)), max: 100 },
    { key: 'net', label: '网络流量', unit: 'bps', icon: '🌐', value: net, display: formatNet(net), pct: Math.min(100, Math.max(0, net / 1000 * 100 || 0)), max: 1000 },
  ]
})

function formatNet(v: number) { if (v >= 1e6) return (v/1e6).toFixed(1) + 'Mbps'; if (v >= 1e3) return (v/1e3).toFixed(1) + 'Kbps'; return v.toFixed(0) + 'bps' }

const filteredItems = computed(() => {
  if (itemCat.value === 'all') return allItems.value
  const catMap: Record<string, string[]> = { cpu: ['cpu'], mem: ['memory','mem'], disk: ['vfs','disk'], net: ['net','tcp'] }
  const keys = catMap[itemCat.value] || []
  return allItems.value.filter((i: any) => keys.some(k => (i.key_ || '').toLowerCase().includes(k)))
})

function tickClock() { const d = new Date(); clock.value = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` }

watch(theme, (v) => { document.body.dataset.theme = v })

onMounted(async () => {
  tickClock(); clockTimer = window.setInterval(tickClock, 1000)

  try {
    const res = await getHostDetail(hostid.value, datasourceId.value)
    const data = res.data.data
    host.value = data.host
    metrics.value = data.metrics || {}

    // Build items from metrics for display
    if (data.metrics) {
      const items = []
      if (data.metrics.cpu_usage !== undefined) items.push({ name: 'CPU 使用率', key_: 'system.cpu.util', lastvalue: data.metrics.cpu_usage, units: '%', lastclock: String(Math.floor(Date.now()/1000)), warn: data.metrics.cpu_usage > 80 })
      if (data.metrics.memory_usage !== undefined) items.push({ name: '内存使用率', key_: 'vm.memory.utilization', lastvalue: data.metrics.memory_usage, units: '%', lastclock: String(Math.floor(Date.now()/1000)), warn: data.metrics.memory_usage > 85 })
      if (data.metrics.disk_usage !== undefined) items.push({ name: '磁盘使用率 (/)', key_: 'vfs.fs.size[/,pused]', lastvalue: data.metrics.disk_usage, units: '%', lastclock: String(Math.floor(Date.now()/1000)), warn: data.metrics.disk_usage > 80 })
      if (data.metrics.network_in !== undefined) items.push({ name: '网络入流量', key_: 'net.if.in', lastvalue: data.metrics.network_in, units: 'bps', lastclock: String(Math.floor(Date.now()/1000)) })
      if (data.metrics.network_out !== undefined) items.push({ name: '网络出流量', key_: 'net.if.out', lastvalue: data.metrics.network_out, units: 'bps', lastclock: String(Math.floor(Date.now()/1000)) })
      allItems.value = items
    }

    // Fetch alerts for this host
    try {
      const { getAlertRecords } = await import('@/api/alert')
      const aRes = await getAlertRecords({ page: 1, page_size: 20 })
      const all = aRes.data.data?.items || []
      const hostAlerts = all.filter((a: any) => a.host_id === hostid.value || a.host_name === host.value?.host || a.host_name === host.value?.name)
      activeTriggers.value = hostAlerts.filter((a: any) => a.status === 'active')
      recentTriggers.value = hostAlerts.filter((a: any) => a.status !== 'active').slice(0, 5)
      triggerCount.value = hostAlerts.length
    } catch(e) {}
  } catch(e) {
    console.error('Failed to load host detail', e)
  }

  await nextTick()
  initTrendChart()
})

function initTrendChart() {
  if (!trendChartRef.value) return
  trendChart = echarts.init(trendChartRef.value, 'dark')
  trendChart.setOption({
    backgroundColor: 'transparent',
    grid: { left: 50, right: 50, top: 30, bottom: 24 },
    legend: { data: ['CPU %','内存 %','磁盘 %','网络 Mbps'], textStyle: { color: '#a8c4d8', fontSize: 11 }, right: 10, top: 4, itemWidth: 12, itemHeight: 8, itemGap: 16 },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(8,24,48,0.95)', borderColor: '#00e5ff', textStyle: { color: '#e6f7ff', fontSize: 12 } },
    xAxis: { type: 'category', data: [], boundaryGap: false, axisLine: { lineStyle: { color: '#455a72' } }, axisLabel: { color: '#6b89a3', fontSize: 10 } },
    yAxis: [
      { type: 'value', name: '%', max: 100, nameTextStyle: { color: '#6b89a3', fontSize: 10 }, axisLabel: { color: '#6b89a3', fontSize: 10, formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(0,229,255,0.08)' } } },
      { type: 'value', name: 'Mbps', nameTextStyle: { color: '#6b89a3', fontSize: 10 }, axisLabel: { color: '#6b89a3', fontSize: 10 }, splitLine: { show: false } }
    ],
    series: [
      { name: 'CPU %', type: 'line', smooth: true, symbol: 'none', data: [], lineStyle: { width: 1.6, color: '#00e5ff', shadowBlur: 6, shadowColor: '#00e5ff' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(0,229,255,0.4)'},{offset:1,color:'rgba(0,229,255,0)'}]) } },
      { name: '内存 %', type: 'line', smooth: true, symbol: 'none', data: [], lineStyle: { width: 1.6, color: '#52c41a', shadowBlur: 6, shadowColor: '#52c41a' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(82,196,26,0.4)'},{offset:1,color:'rgba(82,196,26,0)'}]) } },
      { name: '磁盘 %', type: 'line', smooth: true, symbol: 'none', data: [], lineStyle: { width: 1.6, color: '#faad14', shadowBlur: 6, shadowColor: '#faad14' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(250,173,20,0.4)'},{offset:1,color:'rgba(250,173,20,0)'}]) } },
      { name: '网络 Mbps', type: 'line', smooth: true, symbol: 'none', data: [], yAxisIndex: 1, lineStyle: { width: 1.6, color: '#7b61ff', shadowBlur: 6, shadowColor: '#7b61ff' } },
    ]
  })
  fetchTrendData()
}

async function fetchTrendData() {
  if (!trendChart || !hostid.value) return
  const dsId = datasourceId.value
  const end = new Date()
  const start = new Date(end.getTime() - 3600000) // last 1 hour

  const fmt = (d: Date) => d.toISOString()
  const metrics = [
    { key: 'system.cpu.util[,idle]', seriesIdx: 0, transform: (v: number) => Math.max(0, Math.min(100, 100 - v)) },
    { key: 'vm.memory.utilization', seriesIdx: 1, transform: (v: number) => Math.max(0, Math.min(100, v)) },
    { key: 'vfs.fs.size[/,pused]', seriesIdx: 2, transform: (v: number) => Math.max(0, Math.min(100, v)) },
    { key: 'net.if.in', seriesIdx: 3, transform: (v: number) => v > 0 ? +(v * 8 / 1_000_000).toFixed(2) : 0 },
  ]

  try {
    const results = await Promise.allSettled(
      metrics.map(m =>
        getHostHistory(hostid.value, {
          datasource_id: dsId,
          item_key: m.key,
          start_time: fmt(start),
          end_time: fmt(end),
        })
      )
    )

    let allTimes: string[] = []
    const allSeriesData: { idx: number; data: [string, number][] }[] = []

    for (let i = 0; i < results.length; i++) {
      const r = results[i]
      if (r.status === 'fulfilled' && r.value.data.code === 0) {
        const rawData = r.value.data.data?.data || []
        const m = metrics[i]
        const points: [string, number][] = rawData.map((d: any) => {
          const ts = new Date(parseInt(d.clock) * 1000)
          const time = `${pad(ts.getHours())}:${pad(ts.getMinutes())}`
          return [time, m.transform(parseFloat(d.value))]
        })
        if (points.length > 0 && allTimes.length === 0) {
          allTimes = points.map(p => p[0])
        }
        allSeriesData.push({ idx: m.seriesIdx, data: points })
      }
    }

    if (allTimes.length > 0) {
      trendChart.setOption({
        xAxis: { data: allTimes },
        series: allSeriesData.map(s => ({
          data: s.data.map(p => p[1]),
        })),
      })
    }
  } catch(e) {
    // History data unavailable; chart remains empty
  }
}

</script>

<style scoped>
.dashboard { position: relative; width: 100%; height: 100%; margin: 0 auto; display: grid; grid-template-rows: 5.9vh 9.3vh 1fr; grid-template-columns: 1fr; gap: 0.625vw; padding: 0.625vw 0.83vw; z-index: 1; }
.topbar { position: relative; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 18px; padding: 0 18px; background: var(--panel-bg); border: 1px solid var(--panel-border); overflow: hidden; }
.topbar::before, .topbar::after { content: ''; position: absolute; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, var(--primary) 50%, transparent); opacity: 0.5; }
.topbar::before { top: 0; } .topbar::after { bottom: 0; }
.home-logo { width: 28px; height: 28px; border-radius: 6px; background: linear-gradient(135deg, var(--primary), var(--primary-2)); display: inline-flex; align-items: center; justify-content: center; font-family: var(--font-num); font-weight: 900; color: #001a2b; font-size: 14px; box-shadow: 0 0 12px var(--primary-glow); }
.home-text { font-family: var(--font-num); font-weight: 700; letter-spacing: 1.5px; }
.host-title { display: flex; align-items: center; gap: 0.625vw; justify-content: center; }
.host-name { font-family: var(--font-num); font-size: 22px; font-weight: 700; background: linear-gradient(90deg, #fff, var(--primary)); -webkit-background-clip: text; background-clip: text; color: transparent; letter-spacing: 1px; }
.host-ip { font-family: var(--font-num); font-size: 13px; color: var(--text-3); }
.status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600; border-radius: 4px; letter-spacing: 1px; }
.status-badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; box-shadow: 0 0 8px currentColor; animation: status-pulse 1.5s infinite; }
@keyframes status-pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(0.8); } }
.status-badge.ok { background: rgba(82,196,26,0.12); border: 1px solid var(--success); color: var(--success); }
.status-badge.problem { background: rgba(245,34,45,0.12); border: 1px solid var(--danger); color: var(--danger); }
.topbar-right { display: flex; align-items: center; gap: 14px; }
.clock { font-family: var(--font-num); font-size: 18px; font-weight: 600; color: var(--primary); letter-spacing: 2px; text-shadow: 0 0 8px var(--primary-glow); }
.theme-switcher { display: flex; gap: 6px; padding: 3px 6px; border: 1px solid var(--panel-border); border-radius: 14px; background: rgba(0,229,255,0.04); }
.theme-dot { width: 14px; height: 14px; border-radius: 50%; cursor: pointer; border: 2px solid transparent; transition: all 0.2s; }
.theme-dot:hover { transform: scale(1.15); }
.theme-dot.active { border-color: #fff; box-shadow: 0 0 8px currentColor; }
.theme-dot[data-color="cyan"]    { background: #00e5ff; color: #00e5ff; }
.theme-dot[data-color="purple"]  { background: #7b61ff; color: #7b61ff; }
.theme-dot[data-color="green"]   { background: #52c41a; color: #52c41a; }
.theme-dot[data-color="orange"]  { background: #ff7a45; color: #ff7a45; }
.back-btn { display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px; border: 1px solid var(--panel-border); background: rgba(0,229,255,0.04); color: var(--text-2); font-size: 13px; cursor: pointer; transition: all 0.2s; text-decoration: none; border-radius: 2px; }
.back-btn:hover { border-color: var(--primary); color: var(--primary); background: rgba(0,229,255,0.08); transform: translateX(-2px); }
.kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; padding: 0 6px; }
.kpi { position: relative; height: 100%; background: var(--panel-bg); border: 1px solid var(--panel-border); display: grid; grid-template-columns: auto 1fr; align-items: center; padding: 0 22px; gap: 16px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s; }
.kpi::after { content: ''; position: absolute; width: 12px; height: 12px; border: 2px solid var(--primary); opacity: 0.7; bottom: -2px; right: -2px; border-left: 0; border-top: 0; }
.kpi:hover { transform: translateY(-2px); box-shadow: 0 0 18px var(--primary-glow); }
.kpi-icon { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; font-size: 26px; background: linear-gradient(135deg, rgba(0,229,255,0.15), rgba(0,229,255,0.03)); border: 1px solid var(--panel-border); border-radius: 6px; }
.kpi-body { min-width: 0; }
.kpi-label { font-size: 12px; color: var(--text-3); letter-spacing: 1.5px; margin-bottom: 4px; display: flex; align-items: center; gap: 5px; }
.kpi-label::before { content: ''; display: inline-block; width: 3px; height: 8px; background: var(--primary); }
.kpi-value-row { display: flex; align-items: baseline; gap: 6px; }
.kpi-value { font-family: var(--font-num); font-size: 32px; font-weight: 900; color: var(--primary); line-height: 1; text-shadow: 0 0 12px var(--primary-glow); font-variant-numeric: tabular-nums; }
.kpi-unit { font-size: 12px; color: var(--text-3); }
.kpi-bar { margin-top: 6px; position: relative; height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; overflow: hidden; }
.kpi-bar-fill { position: absolute; inset: 0; background: linear-gradient(90deg, var(--primary), var(--primary-2)); border-radius: 2px; box-shadow: 0 0 6px var(--primary-glow); transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1); }
.main-area { display: grid; grid-template-columns: 1fr 2fr; grid-template-rows: 1fr 1fr; gap: 0.625vw; min-height: 0; }
.main-area > .panel { min-height: 0; }
.col-1 { grid-column: 1; grid-row: 1; }
.col-2 { grid-column: 1; grid-row: 2; }
.col-3 { grid-column: 2; grid-row: 1 / 3; }
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.info-cell { padding: 8px 10px; border-bottom: 1px dashed rgba(0,229,255,0.08); border-right: 1px dashed rgba(0,229,255,0.08); }
.info-cell:nth-child(2n) { border-right: 0; }
.info-cell:nth-last-child(-n+2) { border-bottom: 0; }
.info-cell-label { font-size: 11px; color: var(--text-3); letter-spacing: 1px; margin-bottom: 4px; }
.info-cell-value { font-size: 13px; color: var(--text-1); font-weight: 500; font-family: var(--font-num); }
.info-cell-value.highlight { color: var(--primary); text-shadow: 0 0 6px var(--primary-glow); }
.tag { display: inline-block; padding: 2px 8px; font-size: 11px; background: rgba(0,229,255,0.08); border: 1px solid rgba(0,229,255,0.3); color: var(--primary); border-radius: 3px; margin: 2px 4px 2px 0; font-family: var(--font-num); }
.tlist { display: flex; flex-direction: column; gap: 6px; padding: 4px 0; }
.trow { display: grid; grid-template-columns: 8px 1fr auto; align-items: center; gap: 10px; padding: 8px 10px; background: rgba(0,229,255,0.03); border: 1px solid rgba(0,229,255,0.1); border-left: 3px solid var(--text-4); font-size: 12px; transition: background 0.2s; }
.trow:hover { background: rgba(0,229,255,0.06); }
.trow.problem { border-left-color: var(--danger); }
.trow.ok { border-left-color: var(--success); }
.tdot { width: 8px; height: 8px; border-radius: 50%; }
.trow.problem .tdot { background: var(--danger); box-shadow: 0 0 8px var(--danger); }
.trow.ok .tdot { background: var(--success); }
.tname { color: var(--text-1); font-weight: 500; }
.tmeta { color: var(--text-3); font-size: 11px; margin-top: 2px; font-family: var(--font-num); }
.tval { font-family: var(--font-num); color: var(--primary); font-size: 13px; font-weight: 600; }
.tsev { display: inline-block; font-size: 10px; padding: 1px 6px; border-radius: 2px; color: #fff; margin-right: 6px; font-weight: 700; }
.tsev.disaster { background: var(--disaster); }
.tsev.high { background: var(--danger); }
.tsev.average { background: var(--warning); color: #2b1d00; }
.tsev.warning { background: #fa8c16; }
.tsev.info { background: var(--info); }
.tabs { display: flex; gap: 4px; }
.tab { padding: 4px 12px; font-size: 12px; background: transparent; border: 1px solid var(--panel-border); color: var(--text-3); cursor: pointer; transition: all 0.2s; border-radius: 2px; font-family: var(--font-cn); }
.tab:hover { color: var(--text-1); }
.tab.active { background: rgba(0,229,255,0.12); border-color: var(--primary); color: var(--primary); }
.item-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.item-table thead th { text-align: left; padding: 8px 10px; color: var(--text-3); font-size: 11px; letter-spacing: 1px; font-weight: 500; border-bottom: 1px solid rgba(0,229,255,0.15); background: rgba(0,229,255,0.04); position: sticky; top: 0; z-index: 1; }
.item-table tbody td { padding: 7px 10px; border-bottom: 1px dashed rgba(0,229,255,0.06); }
.item-table tbody tr { transition: background 0.2s; }
.item-table tbody tr:hover { background: rgba(0,229,255,0.04); }
.item-name { color: var(--text-1); font-family: var(--font-num); }
.item-key { color: var(--text-3); font-size: 10px; font-family: var(--font-num); margin-top: 2px; }
.item-val { font-family: var(--font-num); color: var(--primary); font-weight: 600; text-align: right; }
.item-val.warn { color: var(--warning); }
.item-meta { color: var(--text-3); font-family: var(--font-num); font-size: 11px; }
.spark { width: 100%; height: 24px; }
.fullscreen-btn {
  display: flex; align-items: center; gap: 4px; padding: 5px 10px; font-size: 12px;
  background: rgba(0, 229, 255, 0.06); border: 1px solid var(--panel-border);
  color: var(--text-2); cursor: pointer; transition: all 0.2s; border-radius: 2px;
  white-space: nowrap; font-family: var(--font-cn);
}
.fullscreen-btn:hover { border-color: var(--primary); color: var(--primary); background: rgba(0, 229, 255, 0.12); }
</style>
