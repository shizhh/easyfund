<template>
  <div>
    <div v-if="loading && !firstLoadDone" class="page-loading">
      <div class="page-loading-spinner"></div>
      <div class="page-loading-text">数据加载中...</div>
    </div>
    <template v-else>
    <div class="toolbar">
      <h2 style="margin:0">资产总览</h2>
      <button class="btn btn-ghost btn-sm" @click="screenshot" :disabled="screenshotLoading" title="截图分享">
        &#x1F4F7;<span class="btn-screenshot-text"> 截图</span>
      </button>
    </div>

    <!-- Summary Cards -->
    <div ref="dashboardContent">
    <div class="summary-row" style="margin-bottom: 24px">
      <div :class="['card', 'summary-card', 'sc-total', { clickable: overview.total_cny != null }]" @click="overview.total_cny != null && scrollToCharts()" title="查看资产分布">
        <div class="sc-icon">&#x2B1A;</div>
        <div class="sc-body">
          <div class="sc-label">资产总额</div>
          <div v-if="moduleLoading('overview')" class="skeleton skeleton-value"></div>
          <template v-else>
            <div class="sc-value">{{ formatMoney(overview.total_cny) }} <span class="sc-unit">CNY</span></div>
            <div v-if="assetChange" class="sc-change">
              <span :class="assetChange.amount >= 0 ? 'change-positive' : 'change-negative'">
                {{ assetChange.amount >= 0 ? '↑' : '↓' }}{{ formatMoney(Math.abs(assetChange.amount)) }} ({{ formatPct(assetChange.pct) }})
              </span>
              <span class="change-date">较 {{ assetChange.date }}</span>
            </div>
          </template>
        </div>
      </div>
      <div class="card summary-card sc-rates">
        <div class="sc-icon">&#x2248;</div>
        <div class="sc-body">
          <div class="sc-header">
            <span class="sc-label">汇率</span>
            <div style="display:flex;gap:4px">
              <button class="btn-icon" title="添加币种" @click="showAddCurrency=true">&#x2b;</button>
              <button class="btn-icon" title="刷新汇率" @click="refreshRates" :disabled="ratesLoading">&#x21bb;</button>
            </div>
          </div>
          <div v-if="moduleLoading('ratesData')" class="skeleton skeleton-rates"></div>
          <template v-else>
            <div class="sc-rates-list">
              <div v-for="r in rateList" :key="r.currency" class="rate-row">
                <span class="rate-label">{{ r.currency }}/CNY</span>
                <span v-if="editingRate === r.currency" class="rate-edit">
                  <input v-model.number="editRateValue" type="number" step="0.0001" class="rate-input" @keyup.enter="saveRate(r.currency)" @keyup.escape="editingRate=null" ref="rateInput" />
                  <button class="btn-link" @click="saveRate(r.currency)">✓</button>
                  <button class="btn-link" @click="editingRate=null">✗</button>
                </span>
                <span v-else class="rate-row-right">
                  <span class="rate-val" @dblclick="startEditRate(r)" title="双击编辑">{{ r.rate_to_cny }}</span>
                  <button class="btn-icon btn-remove-currency" title="移除币种" @click="removeCurrency(r.currency)">&#x2715;</button>
                </span>
              </div>
              <div v-if="showAddCurrency" class="rate-row add-currency-row">
                <input v-model="newCurrency" type="text" maxlength="3" class="rate-input" style="width:50px;text-transform:uppercase" placeholder="EUR" @keyup.enter="addCurrency" @keyup.escape="showAddCurrency=false" />
                <input v-model.number="newCurrencyRate" type="number" step="0.0001" class="rate-input" style="width:80px" placeholder="汇率" @keyup.enter="addCurrency" @keyup.escape="showAddCurrency=false" />
                <button class="btn-link" @click="addCurrency">✓</button>
                <button class="btn-link" @click="showAddCurrency=false">✗</button>
              </div>
            </div>
            <div v-if="rateDate" class="rate-date">更新于 {{ rateDate }} {{ rateSource }}</div>
          </template>
        </div>
      </div>
      <router-link to="/accounts" class="card summary-card sc-accounts clickable" title="账户管理">
        <div class="sc-icon">&#x25CE;</div>
        <div class="sc-body">
          <div class="sc-label">账户数</div>
          <div v-if="moduleLoading('overview')" class="skeleton skeleton-count"></div>
          <div v-else class="sc-value">{{ overview.account_count }}</div>
        </div>
      </router-link>
      <router-link to="/investments" class="card summary-card sc-holdings clickable" title="投资追踪">
        <div class="sc-icon">&#x25C7;</div>
        <div class="sc-body">
          <div class="sc-label">持仓数</div>
          <div v-if="moduleLoading('overview')" class="skeleton skeleton-count"></div>
          <div v-else class="sc-value">{{ overview.holding_count }}</div>
        </div>
      </router-link>
    </div>

    <!-- Charts Row -->
    <div ref="chartsRow" class="grid-2" style="margin-bottom: 24px">
      <div class="card">
        <div class="chart-header">
          <h3 style="margin:0">资产分布</h3>
          <div style="display:flex;gap:4px">
            <button class="chart-tab" :class="{ active: pieMode === 'pie' }" @click="pieMode='pie'">占比</button>
            <button class="chart-tab" :class="{ active: pieMode === 'detail' }" @click="pieMode='detail'">明细</button>
          </div>
        </div>
        <div v-if="moduleLoading('overview')" class="skeleton skeleton-chart"></div>
        <template v-else-if="Object.keys(overview.category_totals || {}).length">
          <v-chart v-if="pieMode === 'pie'" :option="pieOption" style="height:320px" autoresize />
          <v-chart v-else :option="detailPieOption" style="height:320px" autoresize />
        </template>
        <div v-else class="trend-empty"><p>暂无资产数据</p></div>
      </div>
      <div class="card">
        <div class="chart-header">
          <h3 style="margin:0">盈亏</h3>
          <div style="display:flex;gap:4px">
            <button class="chart-tab" :class="{ active: pnlMode === 'annual' }" @click="pnlMode='annual'">年度盈亏</button>
            <button class="chart-tab" :class="{ active: pnlMode === 'total' }" @click="pnlMode='total'">总盈亏</button>
            <button class="chart-tab" :class="{ active: pnlMode === 'cumulative' }" @click="pnlMode='cumulative'">累计盈亏</button>
          </div>
        </div>
        <div v-if="moduleLoading('annualPnl')" class="skeleton skeleton-chart"></div>
        <template v-else-if="Object.keys(annualPnl).length">
          <v-chart v-if="pnlMode === 'annual'" :option="lineOption" style="height:320px" autoresize />
          <v-chart v-else-if="pnlMode === 'total'" :option="totalPnlOption" style="height:320px" autoresize />
          <v-chart v-else :option="cumulativePnlOption" style="height:320px" autoresize />
        </template>
        <div v-else class="trend-empty"><p>暂无盈亏数据</p></div>
      </div>
    </div>

    <!-- Trend & Holdings PnL Row -->
    <div class="grid-2" style="margin-bottom: 24px">
      <div class="card">
        <div class="chart-header">
          <h3 style="margin:0">资产趋势</h3>
          <button class="btn btn-ghost btn-sm" @click="saveSnapshot" :disabled="snapshotLoading" title="保存今日快照">
            {{ snapshotLoading ? '保存中...' : '保存快照' }}
          </button>
        </div>
        <div v-if="moduleLoading('trendData')" class="skeleton skeleton-chart"></div>
        <template v-else-if="trendData.length > 0">
          <v-chart :option="trendOption" style="height:280px" autoresize />
        </template>
        <div v-else class="trend-empty">
          <p>暂无趋势数据</p>
          <p class="trend-empty-hint">点击「保存快照」开始记录资产变化趋势</p>
        </div>
      </div>
      <div class="card">
        <div class="chart-header">
          <h3 style="margin:0">持仓盈亏</h3>
          <span v-if="holdingsPnl.length" class="chart-subtitle">共 {{ holdingsPnl.length }} 只</span>
        </div>
        <div v-if="moduleLoading('holdingsPnl')" class="skeleton skeleton-chart"></div>
        <template v-else-if="holdingsPnl.length > 0">
          <div class="holdings-pnl-list">
            <div v-for="h in displayedHoldings" :key="h.id" class="h-pnl-row">
              <div class="h-pnl-info">
                <span class="h-pnl-ticker">{{ h.ticker || h.name }}</span>
                <span v-if="h.ticker && h.name" class="h-pnl-name">{{ h.name }}</span>
              </div>
              <div class="h-pnl-values">
                <span class="h-pnl-amount" :class="h.pnl >= 0 ? 'pnl-positive' : 'pnl-negative'">
                  {{ formatPnl(h.pnl_cny) }}
                </span>
                <span class="h-pnl-pct" :class="h.pnl_pct >= 0 ? 'pnl-positive' : 'pnl-negative'">
                  {{ formatPct(h.pnl_pct) }}
                </span>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="trend-empty"><p>暂无持仓数据</p></div>
        <button v-if="holdingsPnl.length > 5" class="btn btn-ghost btn-sm h-pnl-toggle" @click="showAllHoldings = !showAllHoldings">
          {{ showAllHoldings ? '收起' : `查看全部 (${holdingsPnl.length})` }}
        </button>
      </div>
    </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, nextTick } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart, LineChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import api from '../api'
import { useScreenshot } from '../composables/useScreenshot'
import { useCurrencies } from '../composables/useCurrencies'
import { formatMoney, categoryLabel } from '../composables/useFormatters'
import { useDashboardStore } from '../stores/dashboard'

use([PieChart, LineChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const dashboardStore = useDashboardStore()
const { registerCurrency, unregisterCurrency, fetchRates: fetchCurrencyRates } = useCurrencies()

const loading = computed(() => dashboardStore.loading)
const moduleLoading = (key) => dashboardStore._loadingModules[key]
const firstLoadDone = computed(() => dashboardStore._firstLoadDone)
const chartsRow = ref(null)
const dashboardContent = ref(null)
const { screenshotLoading, screenshot } = useScreenshot(dashboardContent, '资产总览')

const scrollToCharts = () => {
  chartsRow.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
const ratesLoading = ref(false)
const editingRate = ref(null)
const editRateValue = ref(null)
const pieMode = ref('pie')
const pnlMode = ref('annual')
const showAddCurrency = ref(false)
const newCurrency = ref('')
const newCurrencyRate = ref(null)
const showAllHoldings = ref(false)
const snapshotLoading = ref(false)

const overview = computed(() => dashboardStore.overview)
const annualPnl = computed(() => dashboardStore.annualPnl)
const trendData = computed(() => dashboardStore.trendData)
const holdingsPnl = computed(() => dashboardStore.holdingsPnl)
const rateList = computed(() => dashboardStore.rateList)
const rateDate = computed(() => dashboardStore.rateDate)
const rateSource = computed(() => dashboardStore.rateSource)

const startEditRate = (r) => {
  editingRate.value = r.currency
  editRateValue.value = r.rate_to_cny
  nextTick(() => {
    const input = document.querySelector('.rate-input')
    if (input) input.focus()
  })
}

const saveRate = async (currency) => {
  if (editRateValue.value == null || editRateValue.value <= 0) return
  await dashboardStore.saveRate(currency, editRateValue.value)
  editingRate.value = null
}

const refreshRates = async () => {
  ratesLoading.value = true
  try {
    await dashboardStore.refreshRates()
  } finally {
    ratesLoading.value = false
  }
}

const addCurrency = async () => {
  const code = newCurrency.value.toUpperCase().trim()
  const rate = newCurrencyRate.value
  if (!code || !rate || rate <= 0) return
  try {
    await dashboardStore.addCurrency(code, rate)
    showAddCurrency.value = false
    newCurrency.value = ''
    newCurrencyRate.value = null
  } catch (e) {
    alert(e.message)
  }
}

const removeCurrency = async (currency) => {
  if (!confirm(`确定移除币种 ${currency}？`)) return
  try {
    await dashboardStore.removeCurrency(currency)
  } catch (e) {
    alert(e.message)
  }
}

const pieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0, textStyle: { fontSize: 12, fontFamily: 'DM Sans' } },
  series: [{
    type: 'pie', radius: ['40%', '70%'], itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
    label: { show: true, formatter: '{b}\n{d}%', fontFamily: 'DM Sans' },
    data: Object.entries(overview.value.category_totals || {}).map(([cat, amt]) => ({
      name: categoryLabel(cat), value: Math.round(amt)
    }))
  }]
}))

const detailPieOption = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: (p) => `${p.name}<br/>${formatMoney(p.value)} CNY (${p.percent}%)`
  },
  legend: { bottom: 0, textStyle: { fontSize: 12, fontFamily: 'DM Sans' } },
  series: [{
    type: 'pie', radius: ['40%', '70%'], itemStyle: { borderRadius: 8, borderColor: '#fff', borderWidth: 2 },
    label: {
      show: true,
      formatter: (p) => `${p.name}\n${formatMoney(p.value)} CNY`,
      fontFamily: 'DM Sans',
    },
    data: Object.entries(overview.value.category_totals || {}).map(([cat, amt]) => ({
      name: categoryLabel(cat), value: Math.round(amt)
    }))
  }]
}))

const lineOption = computed(() => {
  const data = annualPnl.value
  const years = new Set()
  const series = []
  const colors = { futu: '#c53d43', alipay: '#b8945a' }
  const names = { futu: '富途', alipay: '支付宝' }
  for (const [acct, yearMap] of Object.entries(data)) {
    const values = []
    for (const [yr, amt] of Object.entries(yearMap)) {
      years.add(yr)
      values.push([yr, amt])
    }
    values.sort((a, b) => a[0] - b[0])
    series.push({
      name: names[acct] || acct, type: 'line', data: values, color: colors[acct],
      smooth: true, symbol: 'circle', symbolSize: 8,
      lineStyle: { width: 3 },
      areaStyle: { opacity: 0.08 },
    })
  }
  const sortedYears = [...years].sort()
  return {
    tooltip: { trigger: 'axis' }, legend: { bottom: 0, textStyle: { fontFamily: 'DM Sans' } },
    grid: { top: 20, bottom: 40, left: 60, right: 20 },
    xAxis: { type: 'category', data: sortedYears, axisLine: { lineStyle: { color: '#e8e4dc' } }, boundaryGap: false },
    yAxis: { type: 'value', axisLabel: { formatter: v => (v/10000).toFixed(0) + '万', fontFamily: 'DM Sans' }, splitLine: { lineStyle: { color: '#f2f0ea' } } },
    series
  }
})

const formatPnl = (v) => {
  if (!v) return '0'
  const formatted = v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return v > 0 ? `+${formatted}` : formatted
}

const formatPct = (v) => {
  const formatted = v.toFixed(2)
  return v > 0 ? `+${formatted}%` : `${formatted}%`
}

// Asset change from last snapshot
const assetChange = computed(() => {
  const data = trendData.value
  const currentTotal = overview.value.total_cny
  if (!data.length || !currentTotal) return null
  // Find the most recent snapshot that is not from today
  const today = new Date().toISOString().slice(0, 10)
  const prevPoints = data.filter(d => d.date !== today)
  if (!prevPoints.length) return null
  const last = prevPoints[prevPoints.length - 1]
  const prevTotal = last.total_cny
  if (!prevTotal) return null
  const change = currentTotal - prevTotal
  const pct = change / prevTotal * 100
  return {
    amount: Math.round(change * 100) / 100,
    pct: Math.round(pct * 100) / 100,
    date: last.date,
  }
})

// Trend chart option — single total asset line
const trendOption = computed(() => {
  const data = trendData.value
  if (!data.length) return {}
  const dates = data.map(d => d.date)
  const values = data.map(d => Math.round(d.total_cny))
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `${p.name}<br/>${formatMoney(p.value)} CNY`
      }
    },
    grid: { top: 20, bottom: 30, left: 60, right: 20 },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e8e4dc' } },
      boundaryGap: false,
      axisLabel: {
        formatter: (v) => v.length > 7 ? v.slice(5) : v,
        fontFamily: 'DM Sans',
        fontSize: 11,
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: v => (v/10000).toFixed(0) + '万',
        fontFamily: 'DM Sans',
      },
      splitLine: { lineStyle: { color: '#f2f0ea' } }
    },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 2.5, color: '#c53d43' },
      areaStyle: { opacity: 0.08, color: '#c53d43' },
      itemStyle: { color: '#c53d43' },
    }]
  }
})

// Displayed holdings (top 5 or all)
const displayedHoldings = computed(() => {
  if (showAllHoldings.value) return holdingsPnl.value
  return holdingsPnl.value.slice(0, 5)
})

// Save snapshot
const saveSnapshot = async () => {
  snapshotLoading.value = true
  try {
    await dashboardStore.saveSnapshot()
  } catch (e) {
    console.error('Failed to save snapshot:', e)
  } finally {
    snapshotLoading.value = false
  }
}

const totalPnlOption = computed(() => {
  const data = annualPnl.value
  const colors = { futu: '#c53d43', alipay: '#b8945a' }
  const names = { futu: '富途', alipay: '支付宝' }
  const categories = []
  const values = []
  const barColors = []
  for (const [acct, yearMap] of Object.entries(data)) {
    const total = Object.values(yearMap).reduce((s, v) => s + v, 0)
    categories.push(names[acct] || acct)
    values.push(Math.round(total))
    barColors.push(colors[acct] || '#999')
  }
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (p) => p.map(i => `${i.name}<br/>${formatMoney(i.value)} CNY`).join('<br/>')
    },
    grid: { top: 20, bottom: 30, left: 60, right: 20 },
    xAxis: { type: 'category', data: categories, axisLine: { lineStyle: { color: '#e8e4dc' } } },
    yAxis: { type: 'value', axisLabel: { formatter: v => (v/10000).toFixed(0) + '万', fontFamily: 'DM Sans' }, splitLine: { lineStyle: { color: '#f2f0ea' } } },
    series: [{
      type: 'bar', data: values.map((v, i) => ({ value: v, itemStyle: { color: barColors[i] } })),
      barWidth: '40%',
      label: {
        show: true, position: 'top',
        formatter: (p) => formatMoney(p.value),
        fontFamily: 'DM Sans', fontSize: 11, color: '#666'
      }
    }]
  }
})

const cumulativePnlOption = computed(() => {
  const data = annualPnl.value
  const allYears = new Set()
  const colors = { futu: '#c53d43', alipay: '#b8945a' }
  const names = { futu: '富途', alipay: '支付宝' }
  const series = []
  for (const [acct, yearMap] of Object.entries(data)) {
    const sorted = Object.entries(yearMap).sort((a, b) => a[0] - b[0])
    sorted.forEach(([yr]) => allYears.add(yr))
    let cumulative = 0
    const values = sorted.map(([yr, amt]) => {
      cumulative += amt
      return [yr, Math.round(cumulative)]
    })
    series.push({
      name: names[acct] || acct, type: 'line', data: values, color: colors[acct],
      smooth: true, symbol: 'circle', symbolSize: 8,
      lineStyle: { width: 3 },
      areaStyle: { opacity: 0.08 },
    })
  }
  const sortedYears = [...allYears].sort()
  return {
    tooltip: { trigger: 'axis' }, legend: { bottom: 0, textStyle: { fontFamily: 'DM Sans' } },
    grid: { top: 20, bottom: 40, left: 60, right: 20 },
    xAxis: { type: 'category', data: sortedYears, axisLine: { lineStyle: { color: '#e8e4dc' } }, boundaryGap: false },
    yAxis: { type: 'value', axisLabel: { formatter: v => (v/10000).toFixed(0) + '万', fontFamily: 'DM Sans' }, splitLine: { lineStyle: { color: '#f2f0ea' } } },
    series
  }
})

onMounted(async () => {
  try {
    await dashboardStore.fetchAll()
    // Auto-save snapshot in background
    api.saveSnapshot().catch(() => {})
  } catch (e) {
    console.error(e)
  }
})

// Re-validate data when re-activated from keep-alive cache
onActivated(async () => {
  try {
    await dashboardStore.fetchAll()
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.summary-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  align-items: stretch;
}
.summary-card {
  position: relative; overflow: hidden;
  display: flex; align-items: center; gap: 10px;
  padding: 14px 16px;
}
.summary-card::before {
  content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%;
  border-radius: 3px 0 0 3px;
}
.sc-total::before { background: var(--vermillion); }
.sc-accounts::before { background: var(--gold); }
.sc-holdings::before { background: #5c8a6e; }
.sc-rates::before { background: #6b7db3; }

.sc-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.sc-total .sc-icon { background: var(--vermillion-soft); color: var(--vermillion); }
.sc-accounts .sc-icon { background: var(--gold-soft); color: var(--gold); }
.sc-holdings .sc-icon { background: rgba(92,138,110,.1); color: #5c8a6e; }
.sc-rates .sc-icon { background: rgba(107,125,179,.1); color: #6b7db3; }

.sc-body { flex: 1; min-width: 0; }
.sc-label {
  font-size: 12px; font-weight: 500; color: var(--text-muted);
  letter-spacing: .04em; margin-bottom: 2px;
}
.sc-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 2px;
}
.sc-header .sc-label { margin-bottom: 0; }
.sc-value {
  font-size: 20px; font-weight: 700; color: var(--text);
  letter-spacing: -.02em; line-height: 1.2;
}
.sc-unit {
  font-size: 12px; font-weight: 400; color: var(--text-muted);
  margin-left: 3px; letter-spacing: 0;
}

.sc-rates-list { margin-top: 2px; }

.summary-card.clickable {
  cursor: pointer;
  transition: all var(--transition);
}
.summary-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
.summary-card.clickable:active {
  transform: translateY(0);
}
a.summary-card {
  text-decoration: none; color: inherit;
}
.rate-row { display: flex; justify-content: space-between; align-items: baseline; padding: 2px 0; }
.rate-label { font-size: 12px; color: var(--text-secondary); }
.rate-val {
  font-size: 16px; font-weight: 600; cursor: pointer; letter-spacing: -.01em;
  color: var(--text); transition: color .2s;
}
.rate-val:hover { color: var(--vermillion); }

.btn-icon {
  background: none; border: none; cursor: pointer; font-size: 14px; padding: 2px 4px;
  color: var(--text-muted); border-radius: 4px; transition: all .2s;
}
.btn-icon:hover { color: var(--vermillion); background: var(--bg-secondary, #f5f5f5); }
.btn-icon:disabled { opacity: .4; cursor: not-allowed; }
.btn-icon:disabled:hover { color: var(--text-muted); background: none; }

.rate-edit { display: flex; align-items: center; gap: 4px; }
.rate-input { width: 80px; padding: 2px 6px; font-size: 14px; border: 1px solid var(--border, #ddd); border-radius: 4px; text-align: right; }
.rate-date { font-size: 11px; color: var(--text-muted); margin-top: 4px; }
.rate-row-right { display: flex; align-items: center; gap: 4px; }
.btn-remove-currency { font-size: 10px; opacity: 0; transition: opacity .2s; }
.rate-row:hover .btn-remove-currency { opacity: .5; }
.btn-remove-currency:hover { opacity: 1 !important; color: var(--vermillion); }
.add-currency-row { margin-top: 4px; padding-top: 4px; border-top: 1px dashed var(--paper-line); gap: 6px; align-items: center; }

.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.chart-tab {
  padding: 4px 12px; font-size: 12px; border: 1px solid var(--paper-line); background: transparent;
  color: var(--text-secondary); cursor: pointer; transition: all .2s; font-family: var(--font-body);
}
.chart-tab:first-child { border-radius: var(--radius) 0 0 var(--radius); }
.chart-tab:last-child { border-radius: 0 var(--radius) var(--radius) 0; border-left: none; }
.chart-tab.active { background: var(--vermillion); color: #fff; border-color: var(--vermillion); }

/* Change indicator */
.sc-change { margin-top: 4px; font-size: 12px; line-height: 1.4; }
.change-positive { color: #c53d43; font-weight: 600; }
.change-negative { color: #5c8a6e; font-weight: 600; }
.change-date { color: var(--text-muted); margin-left: 6px; font-size: 11px; }

/* Trend chart empty state */
.trend-empty { padding: 40px 0; text-align: center; }
.trend-empty p { margin: 0; color: var(--text-muted); font-size: 14px; }
.trend-empty-hint { font-size: 12px !important; margin-top: 8px !important; }

/* Chart subtitle */
.chart-subtitle { font-size: 12px; color: var(--text-muted); }

/* Holdings P&L list */
.holdings-pnl-list { max-height: 240px; overflow-y: auto; }
.h-pnl-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-bottom: 1px solid var(--paper-line);
}
.h-pnl-row:last-child { border-bottom: none; }
.h-pnl-info { display: flex; flex-direction: column; min-width: 0; }
.h-pnl-ticker { font-weight: 600; font-size: 14px; color: var(--text); }
.h-pnl-name {
  font-size: 12px; color: var(--text-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 140px;
}
.h-pnl-values { display: flex; flex-direction: column; align-items: flex-end; flex-shrink: 0; }
.h-pnl-amount { font-weight: 600; font-size: 14px; }
.h-pnl-pct { font-size: 12px; }
.pnl-positive { color: #c53d43; }
.pnl-negative { color: #5c8a6e; }
.h-pnl-toggle { width: 100%; margin-top: 4px; }

/* ---- Mobile ---- */
@media (max-width: 768px) {
  .summary-row {
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .sc-value { font-size: 17px; }
  .sc-icon { width: 30px; height: 30px; font-size: 15px; }
  .summary-card { padding: 12px; }
  .rate-val { font-size: 14px; }
  .h-pnl-name { max-width: 100px; }
}

.page-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 50vh;
  gap: 16px;
}
.page-loading-spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--paper-line);
  border-top-color: var(--vermillion);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
.page-loading-text {
  font-size: 14px;
  color: var(--text-muted);
  letter-spacing: .04em;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Skeleton placeholders for progressive loading */
.skeleton {
  background: linear-gradient(90deg, #f0ece6 25%, #e8e4dc 50%, #f0ece6 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 6px;
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.skeleton-value { width: 140px; height: 28px; margin-top: 2px; }
.skeleton-count { width: 40px; height: 28px; margin-top: 2px; }
.skeleton-rates { width: 100%; height: 80px; margin-top: 4px; }
.skeleton-chart { width: 100%; height: 280px; }
</style>
