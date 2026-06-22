<template>
  
    
      <div class="dashboard">
        <!-- Top Bar -->
        <div class="topbar">
          <div class="breadcrumb">
            <a class="home" @click="$router.push('/dashboard')"><span class="home-logo">{{ layoutStore.brandTitle?.charAt(0) || 'Z' }}</span><span class="home-text">{{ layoutStore.brandTitle || 'ZBXBoard' }}</span></a>
            <span class="sep">/</span><a @click="$router.push('/alerts/records')">告警</a>
            <span class="sep">/</span><a @click="$router.push('/alerts/records')">告警列表</a>
            <span class="sep">/</span><span class="current">{{ alert?.event_id?.slice(0,12) || '...' }}</span>
          </div>
          <div class="alert-title-wrap">
            <span class="sev-badge" :style="sevStyle">{{ sevBadgeText }}</span>
            <span class="alert-title">{{ alert?.trigger_name || '告警详情' }}</span>
            <span class="status-pill" :class="alert?.status === 'recovered' ? 'resolved' : alert?.status === 'ack' ? 'ack' : ''">{{ alert?.status === 'recovered' ? '已 恢 复' : alert?.status === 'ack' ? '已 确 认' : '告 警 中' }}</span>
          </div>
          <div class="topbar-right">
            <div class="clock">{{ clock }}</div>
            <div class="theme-switcher">
              <div v-for="c in themes" :key="c" class="theme-dot" :class="{ active: theme === c }" :data-color="c" @click="theme = c"></div>
            </div>
            <div class="fullscreen-btn" @click="layoutStore.toggleFullscreen()" :title="layoutStore.isFullscreen ? '退出全屏' : '全屏展示'">
              {{ layoutStore.isFullscreen ? '⊠ 退出全屏' : '⊡ 全屏' }}
            </div>
            <a class="action-btn warn" @click="acknowledge">确认告警</a>
            <a class="action-btn primary" @click="$router.push('/hosts/' + alert?.host_id + '?datasource_id=' + datasourceId)">查看主机</a>
          </div>
        </div>

        <!-- KPI Strip -->
        <section class="kpi-strip">
          <div class="kpi" :class="{ alert: true }">
            <div class="kpi-icon">⏱️</div><div class="kpi-body"><div class="kpi-label">持续时长</div><div class="kpi-value-row"><div class="kpi-value">{{ duration }}</div></div><div class="kpi-sub">发生于 {{ occurredTime }}</div></div>
          </div>
          <div class="kpi" :class="{ alert: true }">
            <div class="kpi-icon">📊</div><div class="kpi-body"><div class="kpi-label">当前值</div><div class="kpi-value-row"><div class="kpi-value">{{ alert?.value || '-' }}</div></div><div class="kpi-sub">事件数值</div></div>
          </div>
          <div class="kpi">
            <div class="kpi-icon">🔁</div><div class="kpi-body"><div class="kpi-label">近期重复</div><div class="kpi-value-row"><div class="kpi-value">{{ relatedAlerts.length }}</div></div><div class="kpi-sub">同触发器</div></div>
          </div>
          <div class="kpi">
            <div class="kpi-icon">📡</div><div class="kpi-body"><div class="kpi-label">推送渠道</div><div class="kpi-value-row"><div class="kpi-value">{{ webhookLogs.length }}</div></div><div class="kpi-sub">Webhook 推送</div></div>
          </div>
        </section>

        <!-- Main Area -->
        <section class="main-area">
          <div class="panel col-1">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title"><div class="panel-title-text">触 发 器 信 息 <span class="panel-title-en">TRIGGER INFO</span></div></div>
            <div class="panel-body"><div class="trig-info">
              <div class="trig-row"><div class="trig-label">触发器</div><div class="trig-value highlight">{{ alert?.trigger_name }}</div></div>
              <div class="trig-row"><div class="trig-label">事件 ID</div><div class="trig-value">{{ alert?.event_id }}</div></div>
              <div class="trig-row"><div class="trig-label">级别</div><div class="trig-value"><span class="tag" :class="alert?.level?.toLowerCase() === 'high' || alert?.level?.toLowerCase() === 'disaster' ? 'danger' : alert?.level?.toLowerCase() === 'warning' || alert?.level?.toLowerCase() === 'average' ? 'warn' : ''">{{ sevLabel(alert?.level) }}</span></div></div>
              <div class="trig-row"><div class="trig-label">关联主机</div><div class="trig-value"><a @click="$router.push('/hosts/' + alert?.host_id + '?datasource_id=' + datasourceId)" style="color:var(--primary);cursor:pointer;text-decoration:none">{{ alert?.host_name }}</a></div></div>
              <div class="trig-row"><div class="trig-label">当前值</div><div class="trig-value alert-color">{{ alert?.value }}</div></div>
              <div class="trig-row"><div class="trig-label">状态</div><div class="trig-value">{{ alert?.status === 'active' ? '告警中' : alert?.status === 'recovered' ? '已恢复' : '已确认' }}</div></div>
              <div class="trig-row"><div class="trig-label">首次发生</div><div class="trig-value">{{ alert?.first_occurred ? new Date(alert.first_occurred).toLocaleString() : '-' }}</div></div>
              <div class="trig-row" v-if="alert?.recovered_at"><div class="trig-label">恢复时间</div><div class="trig-value">{{ new Date(alert.recovered_at).toLocaleString() }}</div></div>
            </div></div>
          </div>

          <div class="panel col-2">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title"><div class="panel-title-text">Webhook 推 送 日 志 <span class="panel-title-en">PUSH LOG</span></div><div class="panel-title-tools"><span>{{ webhookLogs.length }} 条记录</span></div></div>
            <div class="panel-body"><div class="wlist">
              <div v-for="w in webhookLogs" :key="w.id" class="wcard" :class="w.status">
                <div class="wicon">{{ w.status === 'success' ? '✅' : w.status === 'retrying' ? '🔄' : '❌' }}</div>
                <div class="wbody"><div class="wtitle">{{ w.endpoint_name || 'Webhook #' + w.webhook_id }}</div><div class="wurl">HTTP {{ w.http_status_code }} · {{ w.response_ms }}ms</div></div>
                <div class="wstatus"><span class="wbadge" :class="w.status">{{ w.status === 'success' ? '成功' : w.status === 'retrying' ? '重试中' : '失败' }}</span><span class="wmeta">重试 {{ w.retry_count }} 次</span></div>
              </div>
              <div v-if="webhookLogs.length === 0" style="color:var(--text-3);text-align:center;padding:20px">暂无推送记录</div>
            </div></div>
          </div>

          <div class="panel col-3">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title"><div class="panel-title-text">相 关 告 警 <span class="panel-title-en">RELATED ALERTS</span></div></div>
            <div class="panel-body"><table class="similar-table"><thead><tr><th>时间</th><th>触发器</th><th>级别</th><th>状态</th></tr></thead><tbody>
              <tr v-for="r in relatedAlerts" :key="r.id" @click="$router.push('/alerts/' + r.id + '?datasource_id=' + datasourceId)" style="cursor:pointer">
                <td style="font-family:var(--font-num);color:var(--text-3);font-size:11px">{{ formatTime(r.created_at) }}</td>
                <td>{{ r.trigger_name }}</td>
                <td><span :style="{color: levelColor(r.level), fontWeight:700}">{{ sevLabel(r.level) }}</span></td>
                <td>{{ r.status === 'active' ? '告警中' : r.status === 'recovered' ? '已恢复' : '已确认' }}</td>
              </tr>
            </tbody></table></div>
          </div>

          <div class="panel col-4">
            <span class="corner-tr"></span><span class="corner-bl"></span>
            <div class="panel-title"><div class="panel-title-text">告 警 时 间 线 <span class="panel-title-en">TIMELINE</span></div></div>
            <div class="panel-body"><div class="timeline">
              <div class="tl-item alert"><div class="tl-time">{{ formatTime(alert?.first_occurred) }} · 告警</div><div class="tl-content">告警产生：<strong>{{ alert?.trigger_name }}</strong>，当前值 {{ alert?.value }}</div></div>
              <div v-if="alert?.status === 'recovered'" class="tl-item ok"><div class="tl-time">{{ formatTime(alert?.recovered_at) }} · 恢复</div><div class="tl-content">告警已恢复</div></div>
              <div v-for="w in webhookLogs" :key="'tl'+w.id" class="tl-item" :class="w.status === 'success' ? 'ok' : 'alert'">
                <div class="tl-time">{{ w.pushed_at ? new Date(w.pushed_at).toLocaleTimeString('zh-CN') : '' }} · {{ w.status === 'success' ? '成功' : '失败' }}</div>
                <div class="tl-content">Webhook 推送{{ w.status === 'success' ? '成功' : '失败' }} (HTTP {{ w.http_status_code }}, {{ w.response_ms }}ms)</div>
              </div>
            </div></div>
          </div>
        </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getAlertRecords } from '@/api/alert'
import { getWebhookLogs } from '@/api/webhook'
import { useLayoutStore } from '@/stores/layout'

const layoutStore = useLayoutStore()

const route = useRoute()
const router = useRouter()
const alertId = computed(() => Number(route.params.id))
const datasourceId = computed(() => Number(route.query.datasource_id) || 1)
const alert = ref<any>(null)
const relatedAlerts = ref<any[]>([])
const webhookLogs = ref<any[]>([])
const clock = ref('--:--:--')
const themes = ['cyan','purple','green','orange']
const theme = ref('cyan')
const scaleInner = ref<HTMLElement>()
let clockTimer: number

function pad(n: number) { return String(n).padStart(2, '0') }
function formatTime(t: string | null) { if (!t) return '-'; return new Date(t).toLocaleString('zh-CN') }
function acknowledge() { ElMessage.info('告警已确认') }
function sevLabel(level: string): string { const m: Record<string,string> = { DISASTER:'灾难', HIGH:'严重', AVERAGE:'一般', WARNING:'警告', INFO:'信息' }; return m[level] || level || '-' }
function levelColor(level: string): string { const m: Record<string,string> = { DISASTER:'#820014', HIGH:'#f5222d', AVERAGE:'#faad14', WARNING:'#fa8c16', INFO:'#1890ff' }; return m[level] || '#6b89a3' }

const occurredTime = computed(() => alert.value?.first_occurred ? new Date(alert.value.first_occurred).toLocaleString('zh-CN') : '-')
const duration = computed(() => {
  if (!alert.value?.first_occurred) return '-'
  const start = new Date(alert.value.first_occurred).getTime()
  const end = alert.value.recovered_at ? new Date(alert.value.recovered_at).getTime() : Date.now()
  const s = Math.floor((end - start) / 1000)
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  return h > 0 ? `${h}时${m}分${sec}秒` : m > 0 ? `${m}分${sec}秒` : `${sec}秒`
})
const sevStyle = computed(() => {
  const c = levelColor(alert.value?.level || '')
  return { background: c, boxShadow: `0 0 12px ${c}` }
})
const sevBadgeText = computed(() => sevLabel(alert.value?.level))

function tickClock() { const d = new Date(); clock.value = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` }

watch(theme, (v) => { document.body.dataset.theme = v })

onMounted(async () => {
  tickClock(); clockTimer = window.setInterval(tickClock, 1000)

  // Fetch alert detail
  try {
    const res = await getAlertRecords({ page: 1, page_size: 1 })
    const items = res.data.data?.items || []
    alert.value = items.find((a: any) => a.id === alertId.value) || items[0] || null
    // Fetch related alerts (same host)
    if (alert.value) {
      const rel = await getAlertRecords({ page: 1, page_size: 10 })
      relatedAlerts.value = (rel.data.data?.items || []).filter((a: any) => a.host_id === alert.value.host_id && a.id !== alert.value.id)
      // Fetch webhook logs
      try {
        const wRes = await getWebhookLogs(1, { page: 1, page_size: 10 }) // use first webhook config
        webhookLogs.value = wRes.data.data?.items || []
      } catch(e) {}
    }
  } catch(e) {}
})

</script>

<style scoped>
.dashboard { position: relative; width: 100%; height: 100%; margin: 0 auto; display: grid; grid-template-rows: 5.9vh 8.3vh 1fr; grid-template-columns: 1fr; gap: 0.625vw; padding: 0.625vw 0.83vw; z-index: 1; }
.topbar { position: relative; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 18px; padding: 0 18px; background: var(--panel-bg); border: 1px solid var(--panel-border); overflow: hidden; }
.topbar::before, .topbar::after { content: ''; position: absolute; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent, var(--primary) 50%, transparent); opacity: 0.5; }
.topbar::before { top: 0; } .topbar::after { bottom: 0; }
.home-logo { width: 28px; height: 28px; border-radius: 6px; background: linear-gradient(135deg, var(--primary), var(--primary-2)); display: inline-flex; align-items: center; justify-content: center; font-family: var(--font-num); font-weight: 900; color: #001a2b; font-size: 14px; box-shadow: 0 0 12px var(--primary-glow); }
.home-text { font-family: var(--font-num); font-weight: 700; letter-spacing: 1.5px; }
.alert-title-wrap { display: flex; align-items: center; gap: 0.625vw; justify-content: center; min-width: 0; }
.alert-title { font-size: 18px; font-weight: 700; color: var(--text-1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 700px; }
.sev-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; font-size: 12px; font-weight: 700; border-radius: 3px; letter-spacing: 1.5px; color: #fff; position: relative; }
.sev-badge::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #fff; animation: badge-pulse 1.2s infinite; }
@keyframes badge-pulse { 0%,100% { opacity: 1; transform: scale(1); box-shadow: 0 0 0 0 #fff; } 50% { opacity: 0.6; transform: scale(0.85); box-shadow: 0 0 0 4px transparent; } }
.status-pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; font-size: 12px; font-weight: 600; border-radius: 3px; background: rgba(245,34,45,0.12); border: 1px solid var(--danger); color: var(--danger); font-family: var(--font-num); }
.status-pill::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; box-shadow: 0 0 8px currentColor; animation: badge-pulse 1.5s infinite; }
.status-pill.ack { background: rgba(250,173,20,0.12); border-color: var(--warning); color: var(--warning); }
.status-pill.resolved { background: rgba(82,196,26,0.12); border-color: var(--success); color: var(--success); }
.topbar-right { display: flex; align-items: center; gap: 10px; }
.action-btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; font-size: 13px; font-weight: 500; background: rgba(0,229,255,0.06); border: 1px solid var(--panel-border); color: var(--text-1); cursor: pointer; transition: all 0.2s; text-decoration: none; border-radius: 2px; }
.action-btn:hover { background: rgba(0,229,255,0.15); border-color: var(--primary); color: var(--primary); }
.action-btn.primary { background: rgba(0,229,255,0.18); border-color: var(--primary); color: var(--primary); }
.action-btn.warn { background: rgba(250,173,20,0.1); border-color: var(--warning); color: var(--warning); }
.clock { font-family: var(--font-num); font-size: 18px; font-weight: 600; color: var(--primary); letter-spacing: 2px; text-shadow: 0 0 8px var(--primary-glow); }
.theme-switcher { display: flex; gap: 6px; padding: 3px 6px; border: 1px solid var(--panel-border); border-radius: 14px; background: rgba(0,229,255,0.04); }
.theme-dot { width: 14px; height: 14px; border-radius: 50%; cursor: pointer; border: 2px solid transparent; transition: all 0.2s; }
.theme-dot:hover { transform: scale(1.15); }
.theme-dot.active { border-color: #fff; box-shadow: 0 0 8px currentColor; }
.theme-dot[data-color="cyan"]    { background: #00e5ff; color: #00e5ff; }
.theme-dot[data-color="purple"]  { background: #7b61ff; color: #7b61ff; }
.theme-dot[data-color="green"]   { background: #52c41a; color: #52c41a; }
.theme-dot[data-color="orange"]  { background: #ff7a45; color: #ff7a45; }
.kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; padding: 0 6px; }
.kpi { position: relative; height: 100%; background: var(--panel-bg); border: 1px solid var(--panel-border); display: grid; grid-template-columns: auto 1fr; align-items: center; padding: 0 22px; gap: 16px; overflow: hidden; }
.kpi::after { content: ''; position: absolute; width: 12px; height: 12px; border: 2px solid var(--primary); opacity: 0.7; bottom: -2px; right: -2px; border-left: 0; border-top: 0; }
.kpi-icon { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; font-size: 24px; background: linear-gradient(135deg, rgba(0,229,255,0.15), rgba(0,229,255,0.03)); border: 1px solid var(--panel-border); border-radius: 6px; }
.kpi.alert .kpi-icon { background: linear-gradient(135deg, rgba(245,34,45,0.18), rgba(245,34,45,0.04)); border-color: rgba(245,34,45,0.3); }
.kpi-body { min-width: 0; }
.kpi-label { font-size: 12px; color: var(--text-3); letter-spacing: 1.5px; margin-bottom: 4px; display: flex; align-items: center; gap: 5px; }
.kpi-label::before { content: ''; display: inline-block; width: 3px; height: 8px; background: var(--primary); }
.kpi.alert .kpi-label::before { background: var(--danger); }
.kpi-value-row { display: flex; align-items: baseline; gap: 6px; }
.kpi-value { font-family: var(--font-num); font-size: 28px; font-weight: 900; color: var(--primary); line-height: 1; text-shadow: 0 0 10px var(--primary-glow); font-variant-numeric: tabular-nums; }
.kpi.alert .kpi-value { color: var(--danger); text-shadow: 0 0 10px rgba(245,34,45,0.4); }
.kpi-sub { font-size: 11px; color: var(--text-3); margin-top: 2px; font-family: var(--font-num); }
.main-area { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 0.625vw; min-height: 0; }
.main-area > .panel { min-height: 0; }
.col-1 { grid-column: 1; grid-row: 1; }
.col-2 { grid-column: 1; grid-row: 2; }
.col-3 { grid-column: 2; grid-row: 1; }
.col-4 { grid-column: 2; grid-row: 2; }
.trig-info { display: flex; flex-direction: column; gap: 10px; }
.trig-row { display: grid; grid-template-columns: 100px 1fr; gap: 0.625vw; align-items: start; padding: 6px 0; border-bottom: 1px dashed rgba(0,229,255,0.08); }
.trig-row:last-child { border-bottom: 0; }
.trig-label { font-size: 12px; color: var(--text-3); letter-spacing: 1px; padding-top: 2px; }
.trig-value { font-size: 13px; color: var(--text-1); font-family: var(--font-num); word-break: break-all; }
.trig-value.highlight { color: var(--primary); }
.trig-value.alert-color { color: var(--danger); font-weight: 700; }
.tag { display: inline-block; padding: 2px 8px; font-size: 11px; background: rgba(0,229,255,0.08); border: 1px solid rgba(0,229,255,0.3); color: var(--primary); border-radius: 2px; font-family: var(--font-num); }
.tag.danger { color: var(--danger); border-color: rgba(245,34,45,0.4); background: rgba(245,34,45,0.08); }
.tag.warn { color: var(--warning); border-color: rgba(250,173,20,0.4); background: rgba(250,173,20,0.08); }
.timeline { position: relative; padding-left: 28px; }
.timeline::before { content: ''; position: absolute; left: 9px; top: 6px; bottom: 6px; width: 2px; background: linear-gradient(180deg, var(--primary), var(--text-4)); opacity: 0.4; }
.tl-item { position: relative; padding: 8px 0 8px 4px; border-bottom: 1px dashed rgba(0,229,255,0.06); }
.tl-item:last-child { border-bottom: 0; }
.tl-item::before { content: ''; position: absolute; left: -22px; top: 14px; width: 10px; height: 10px; border-radius: 50%; background: var(--bg-2); border: 2px solid var(--text-4); z-index: 1; }
.tl-item.alert::before { background: var(--danger); border-color: var(--danger); box-shadow: 0 0 8px var(--danger); }
.tl-item.ok::before { background: var(--success); border-color: var(--success); }
.tl-time { font-size: 11px; color: var(--text-3); font-family: var(--font-num); }
.tl-content { font-size: 12px; color: var(--text-1); margin-top: 2px; }
.tl-content strong { color: var(--primary); font-weight: 600; }
.wlist { display: flex; flex-direction: column; gap: 8px; }
.wcard { display: grid; grid-template-columns: 24px 1fr auto; gap: 0.625vw; align-items: center; padding: 10px 14px; background: rgba(0,229,255,0.03); border: 1px solid rgba(0,229,255,0.12); border-left: 3px solid var(--text-4); transition: background 0.2s; }
.wcard:hover { background: rgba(0,229,255,0.06); }
.wcard.success { border-left-color: var(--success); }
.wcard.failed { border-left-color: var(--danger); }
.wicon { font-size: 18px; display: flex; align-items: center; justify-content: center; }
.wbody { min-width: 0; }
.wtitle { font-size: 13px; font-weight: 500; color: var(--text-1); margin-bottom: 3px; }
.wurl { font-size: 11px; color: var(--text-3); font-family: var(--font-num); }
.wstatus { display: flex; align-items: center; gap: 8px; font-family: var(--font-num); font-size: 12px; }
.wbadge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; font-size: 11px; font-weight: 700; border-radius: 2px; letter-spacing: 1px; }
.wbadge.success { color: var(--success); background: rgba(82,196,26,0.12); border: 1px solid var(--success); }
.wbadge.failed { color: var(--danger); background: rgba(245,34,45,0.12); border: 1px solid var(--danger); }
.wmeta { color: var(--text-3); font-size: 11px; }
.similar-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.similar-table thead th { text-align: left; padding: 8px 10px; color: var(--text-3); font-size: 11px; letter-spacing: 1px; font-weight: 500; border-bottom: 1px solid rgba(0,229,255,0.15); background: rgba(0,229,255,0.04); }
.similar-table tbody td { padding: 8px 10px; border-bottom: 1px dashed rgba(0,229,255,0.06); }
.similar-table tbody tr { transition: background 0.2s; }
.similar-table tbody tr:hover { background: rgba(0,229,255,0.06); }
.fullscreen-btn {
  display: flex; align-items: center; gap: 4px; padding: 6px 10px; font-size: 12px;
  background: rgba(0,229,255,0.06); border: 1px solid var(--panel-border);
  color: var(--text-2); cursor: pointer; transition: all 0.2s; border-radius: 2px;
  white-space: nowrap; font-family: var(--font-cn);
}
.fullscreen-btn:hover { border-color: var(--primary); color: var(--primary); background: rgba(0,229,255,0.12); }
</style>
