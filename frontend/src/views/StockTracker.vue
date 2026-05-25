<template>
  <div>
    <div v-if="initialLoading" class="page-loading">
      <div class="page-loading-spinner"></div>
      <div class="page-loading-text">数据加载中...</div>
    </div>
    <template v-else>
    <div class="toolbar">
      <h2 style="margin:0">股价追踪</h2>
      <div class="toolbar-actions">
        <button class="btn btn-ghost btn-sm" @click="saveSnapshot" :disabled="loading" title="记录今日快照">
          &#x1F4CB; 记录
        </button>
        <button class="btn btn-ghost btn-sm" @click="refreshLivePrices" :disabled="refreshingPrices" title="刷新实时股价">
          <span class="refresh-icon" :class="{ spinning: refreshingPrices }">&#x21bb;</span> 刷新股价
        </button>
        <button class="btn btn-primary btn-sm" @click="showAddModal = true">+ 添加关注</button>
      </div>
    </div>

    <!-- Summary Cards -->
    <div class="summary-row" style="margin-bottom: 24px">
      <div class="card summary-card sc-pnl">
        <div class="sc-icon">&#x25B2;</div>
        <div class="sc-body">
          <div class="sc-label">持仓盈亏</div>
          <div class="sc-value" :class="summary.total_pnl_cny >= 0 ? 'positive' : 'negative'">
            {{ summary.total_pnl_cny >= 0 ? '+' : '' }}{{ formatMoney(summary.total_pnl_cny) }}
            <span class="sc-unit">CNY</span>
          </div>
        </div>
      </div>
      <div class="card summary-card sc-change">
        <div class="sc-icon">&#x2195;</div>
        <div class="sc-body">
          <div class="sc-label">今日变动</div>
          <div class="sc-value" :class="summary.today_change_cny >= 0 ? 'positive' : 'negative'">
            {{ summary.today_change_cny >= 0 ? '+' : '' }}{{ formatMoney(summary.today_change_cny) }}
            <span class="sc-unit">CNY</span>
          </div>
        </div>
      </div>
      <div class="card summary-card sc-count">
        <div class="sc-icon">&#x2606;</div>
        <div class="sc-body">
          <div class="sc-label">关注股票</div>
          <div class="sc-value">{{ summary.holding_count + summary.watchlist_count }} <span class="sc-unit">只</span></div>
        </div>
      </div>
      <div class="card summary-card sc-rates">
        <div class="sc-icon">&#x2248;</div>
        <div class="sc-body">
          <div class="sc-label">汇率</div>
          <div class="sc-rates-list">
            <div v-for="r in summary.exchange_rates" :key="r.currency" class="rate-row" v-show="r.currency !== 'CNY'">
              <span class="rate-label">{{ r.currency }}/CNY</span>
              <span class="rate-value">{{ r.rate_to_cny?.toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Stock Cards Grid -->
    <div class="grid-3" style="margin-bottom: 24px" v-if="stocks.length">
      <div v-for="s in stocks" :key="s.holding_id || s.ticker" class="card stock-card">
        <div class="stock-header">
          <span class="stock-ticker">{{ s.ticker }}</span>
          <span class="stock-source" :class="s.source">{{ s.source === 'holding' ? '持仓' : '关注' }}</span>
        </div>
        <div v-if="s.name" class="stock-name">{{ s.name }}</div>
        <div v-if="s.account_id" class="stock-account">{{ accountName(s.account_id) }}</div>
        <div class="stock-price-row">
          <span class="stock-price">{{ s.price?.toFixed(2) || '--' }}</span>
          <span class="stock-currency">{{ s.currency }}</span>
        </div>
        <div class="stock-change" :class="s.change_pct > 0 ? 'positive' : s.change_pct < 0 ? 'negative' : ''" v-if="s.change_pct != null">
          {{ s.change_pct > 0 ? '+' : '' }}{{ s.change_pct.toFixed(2) }}%
          <span class="change-arrow">{{ s.change_pct > 0 ? '&#x25B2;' : '&#x25BC;' }}</span>
        </div>
        <div v-else class="stock-change muted">--</div>
        <!-- Mini sparkline (click to view trend) -->
        <div v-if="getSparkline(s.ticker).length > 1" class="sparkline-wrap clickable" @click="showTrend(s)" title="查看趋势图">
          <v-chart :option="sparklineOption(getSparkline(s.ticker), s.change_pct)" autoresize style="height: 40px" />
        </div>
        <div class="stock-card-actions">
          <button class="btn btn-sm btn-ghost trend-btn" @click="showTrend(s)">&#x1F4C8; 趋势</button>
        </div>
        <div v-if="s.source === 'holding'" class="stock-holding-info">
          <span>{{ s.shares }}股</span>
          <span>市值 {{ formatMoney(s.market_value_cny) }} CNY</span>
        </div>
      </div>
    </div>

    <!-- Full Data Table -->
    <div class="card" v-if="stocks.length">
      <table>
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>账户</th>
            <th>现价</th>
            <th>币种</th>
            <th>涨跌幅</th>
            <th>持仓</th>
            <th>市值(CNY)</th>
            <th>盈亏(CNY)</th>
            <th>来源</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in stocks" :key="s.holding_id || s.ticker">
            <td><strong>{{ s.ticker }}</strong></td>
            <td>{{ s.name || '--' }}</td>
            <td class="td-account">{{ s.account_id ? accountName(s.account_id) : '--' }}</td>
            <td>{{ s.price?.toFixed(2) || '--' }}</td>
            <td>{{ s.currency }}</td>
            <td :class="s.change_pct > 0 ? 'positive' : s.change_pct < 0 ? 'negative' : ''">
              {{ s.change_pct != null ? (s.change_pct > 0 ? '+' : '') + s.change_pct.toFixed(2) + '%' : '--' }}
            </td>
            <td>{{ s.shares || '--' }}</td>
            <td>{{ s.market_value_cny ? formatMoney(s.market_value_cny) : '--' }}</td>
            <td :class="s.pnl_cny > 0 ? 'positive' : s.pnl_cny < 0 ? 'negative' : ''">
              {{ s.pnl_cny ? (s.pnl_cny > 0 ? '+' : '') + formatMoney(s.pnl_cny) : '--' }}
            </td>
            <td><span class="stock-source" :class="s.source">{{ s.source === 'holding' ? '持仓' : '关注' }}</span></td>
            <td>
              <button class="btn btn-sm btn-ghost" @click="showTrend(s)">趋势</button>
              <button class="btn btn-sm btn-ghost" @click="editStock(s)">编辑</button>
              <button v-if="s.source === 'watchlist'" class="btn btn-sm btn-danger" @click="removeWatchlist(s.ticker)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty state -->
    <div class="card empty-state" v-if="!loading && !stocks.length">
      <p>暂无关注股票</p>
      <button class="btn btn-primary" @click="showAddModal = true">添加关注</button>
    </div>

    <!-- Add Watchlist Modal -->
    <div class="modal-overlay" v-if="showAddModal" @click.self="showAddModal = false">
      <div class="modal">
        <h3>添加关注</h3>
        <div class="form-group">
          <label class="form-label">股票代码</label>
          <input class="form-input" v-model="addForm.ticker" placeholder="如 BIDU, 9988.HK, 600519.SS" @keyup.enter="addWatchlist" />
        </div>
        <div class="form-group">
          <label class="form-label">名称（可选）</label>
          <input class="form-input" v-model="addForm.name" placeholder="如 百度" @keyup.enter="addWatchlist" />
        </div>
        <div v-if="addError" class="add-error">{{ addError }}</div>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="showAddModal = false">取消</button>
          <button class="btn btn-primary" @click="addWatchlist" :disabled="!addForm.ticker.trim()">添加</button>
        </div>
      </div>
    </div>

    <!-- Stock Trend Chart Modal -->
    <div class="modal-overlay" v-if="trendStock" @click.self="trendStock = null">
      <div class="modal modal-lg">
        <div class="chart-header">
          <h3 style="margin:0">{{ trendStock.ticker }} {{ trendStock.name ? `- ${trendStock.name}` : '' }} 股价趋势</h3>
          <div class="trend-range-btns">
            <button class="btn btn-sm" :class="trendDays === 7 ? 'btn-primary' : 'btn-ghost'" @click="trendDays = 7; loadStockHistory()">7天</button>
            <button class="btn btn-sm" :class="trendDays === 30 ? 'btn-primary' : 'btn-ghost'" @click="trendDays = 30; loadStockHistory()">30天</button>
          </div>
        </div>
        <div v-if="trendHistory.length" style="margin-top: 12px">
          <v-chart :option="stockTrendOption" autoresize style="height: 300px" />
        </div>
        <div v-else-if="trendLoading" class="trend-loading">加载中...</div>
        <div v-else class="trend-empty">暂无历史数据</div>
        <div class="modal-actions" style="margin-top: 16px">
          <button class="btn btn-ghost" @click="trendStock = null">关闭</button>
        </div>
      </div>
    </div>

    <!-- Edit Stock Modal -->
    <div class="modal-overlay" v-if="editingStock" @click.self="editingStock = null">
      <div class="modal">
        <h3>编辑 - {{ editingStock.ticker }}{{ editingStock.account_id ? ` (${accountName(editingStock.account_id)})` : '' }}</h3>
        <div class="form-group">
          <label class="form-label">名称</label>
          <input class="form-input" v-model="editForm.name" placeholder="股票名称" />
        </div>
        <template v-if="editingStock.source === 'watchlist'">
          <div class="form-group">
            <label class="form-label">股票代码</label>
            <input class="form-input" v-model="editForm.ticker" placeholder="股票代码" />
          </div>
        </template>
        <template v-if="editingStock.source === 'holding'">
          <div class="form-group">
            <label class="form-label">持股数</label>
            <input class="form-input" type="number" v-model.number="editForm.shares" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">均价</label>
              <input class="form-input" type="number" step="0.01" v-model.number="editForm.avg_cost_price" />
            </div>
            <div class="form-group">
              <label class="form-label">现价</label>
              <input class="form-input" type="number" step="0.01" v-model.number="editForm.current_price" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">币种</label>
            <select class="form-select" v-model="editForm.currency">
              <option v-for="c in currencyOptions" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
        </template>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="editingStock = null">取消</button>
          <button class="btn btn-primary" @click="saveEditStock">保存</button>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import api from '../api'
import { useCurrencies } from '../composables/useCurrencies'
import { formatMoney } from '../composables/useFormatters'
import { useAccountsStore } from '../stores/accounts'
import { useStockTrackerStore } from '../stores/stockTracker'

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])

const { currencyOptions, fetchRates: fetchCurrencyRates } = useCurrencies()
const accountsStore = useAccountsStore()
const trackerStore = useStockTrackerStore()

const showAddModal = ref(false)
const addForm = ref({ ticker: '', name: '' })
const addError = ref('')
const editingStock = ref(null)
const editForm = ref({ name: '', ticker: '', shares: 0, avg_cost_price: 0, current_price: 0, currency: 'USD' })

const accountName = (accountId) => accountsStore.accountName(accountId)

const getSparkline = (ticker) => sparklineData.value[ticker] || []

const summary = computed(() => trackerStore.summary)
const stocks = computed(() => trackerStore.stocks)
const loading = computed(() => trackerStore.loading)
const initialLoading = computed(() => trackerStore.initialLoading)
const refreshingPrices = computed(() => trackerStore.refreshingPrices)

// Sparkline data from real market history (7-day), overrides snapshot-based sparkline
const sparklineData = ref({}) // { ticker: [price, ...] }

const fetchSparklines = async () => {
  const tickers = stocks.value.map(s => s.ticker).filter(Boolean)
  if (!tickers.length) return
  // Fetch 7-day history for each ticker in parallel (with concurrency limit)
  const results = await Promise.allSettled(
    tickers.map(t => api.getQuoteHistory(t, 7).then(d => [t, (d.history || []).map(h => h.price)]))
  )
  const newData = {}
  for (const r of results) {
    if (r.status === 'fulfilled' && r.value[1].length > 1) {
      newData[r.value[0]] = r.value[1]
    }
  }
  sparklineData.value = newData
}

const refreshData = async () => {
  try {
    await Promise.all([
      trackerStore.fetchOverview(),
      accountsStore.fetchAccounts(),
      fetchCurrencyRates(),
    ])
  } catch (e) {
    console.error('Failed to load tracker data:', e)
  }
  // Then fetch live prices and sparklines in background
  trackerStore.refreshLivePrices()
  fetchSparklines()
}

const refreshLivePrices = () => trackerStore.refreshLivePrices()

const addWatchlist = async () => {
  const ticker = addForm.value.ticker.trim().toUpperCase()
  if (!ticker) return
  addError.value = ''
  try {
    await trackerStore.addWatchlist(ticker, addForm.value.name.trim())
    showAddModal.value = false
    addForm.value = { ticker: '', name: '' }
  } catch (e) {
    addError.value = e.message || '添加失败'
  }
}

const removeWatchlist = async (ticker) => {
  if (!confirm(`确认删除 ${ticker} ？`)) return
  try {
    await trackerStore.removeWatchlist(ticker)
  } catch (e) {
    console.error('Failed to delete watchlist item:', e)
  }
}

const editStock = (stock) => {
  editForm.value = {
    name: stock.name || '',
    ticker: stock.ticker,
    shares: stock.shares || 0,
    avg_cost_price: stock.avg_cost_price || 0,
    current_price: stock.price || 0,
    currency: stock.currency || 'USD',
  }
  editingStock.value = stock
}

const saveEditStock = async () => {
  const s = editingStock.value
  if (!s) return
  try {
    const updates = {}
    if (s.source === 'watchlist') {
      const newTicker = editForm.value.ticker.trim()
      const newName = editForm.value.name.trim()
      if (newTicker && newTicker !== s.ticker) updates.ticker = newTicker
      if (newName !== (s.name || '')) updates.name = newName
    } else {
      const formShares = Number(editForm.value.shares) || 0
      const formPrice = Number(editForm.value.current_price) || 0
      const formAvgCost = Number(editForm.value.avg_cost_price) || 0
      const newName = editForm.value.name.trim()
      if (newName && newName !== (s.name || '')) updates.name = newName
      if (editForm.value.currency !== s.currency) updates.currency = editForm.value.currency
      if (formPrice > 0 && Math.abs(formPrice - s.price) > 0.001) updates.current_price = formPrice
      if (formAvgCost > 0 && Math.abs(formAvgCost - s.avg_cost_price) > 0.001) updates.avg_cost_price = formAvgCost
      if (formShares !== s.shares) updates.shares = formShares
    }
    await trackerStore.saveEditStock(s, updates)
    editingStock.value = null
  } catch (e) {
    console.error('Failed to save edit:', e)
    alert('保存失败: ' + e.message)
  }
}

const saveSnapshot = () => trackerStore.saveSnapshot()

// ── Chart options ──

const sparklineOption = (data, changePct) => {
  const color = changePct >= 0 ? '#c53d43' : '#2e7d32'
  // If price range is very narrow (<0.5%), center Y axis around midpoint to avoid exaggeration
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min
  const mid = (min + max) / 2
  const yAxisMin = range / mid < 0.005 ? mid * 0.997 : 'dataMin'
  const yAxisMax = range / mid < 0.005 ? mid * 1.003 : 'dataMax'
  return {
    grid: { top: 2, bottom: 2, left: 2, right: 2 },
    xAxis: { show: false, type: 'category', data: data.map((_, i) => i), boundaryGap: false },
    yAxis: { show: false, type: 'value', min: yAxisMin, max: yAxisMax },
    series: [{
      type: 'line', data, smooth: true, symbol: 'none',
      lineStyle: { width: 1.5, color },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: color.replace(')', ',0.2)').replace('rgb', 'rgba') }, { offset: 1, color: color.replace(')', ',0.02)').replace('rgb', 'rgba') }] } },
    }]
  }
}

// ── Single stock trend chart ──
const trendStock = ref(null)
const trendDays = ref(30)
const trendHistory = ref([])
const trendLoading = ref(false)

const showTrend = (stock) => {
  trendStock.value = stock
  trendDays.value = 30
  trendHistory.value = []
  loadStockHistory()
}

const loadStockHistory = async () => {
  if (!trendStock.value) return
  trendLoading.value = true
  try {
    const data = await api.getQuoteHistory(trendStock.value.ticker, trendDays.value)
    trendHistory.value = data.history || []
  } catch (e) {
    console.error('Failed to load stock history:', e)
    trendHistory.value = []
  } finally {
    trendLoading.value = false
  }
}

const stockTrendOption = computed(() => {
  if (!trendHistory.value.length) return {}
  const dates = trendHistory.value.map(h => h.date.slice(5))
  const prices = trendHistory.value.map(h => h.price)
  const first = prices[0]
  const last = prices[prices.length - 1]
  const color = last >= first ? '#c53d43' : '#2e7d32'
  return {
    tooltip: { trigger: 'axis', formatter: params => {
      const p = params[0]
      return `${trendHistory.value[p.dataIndex]?.date}<br/>价格: ${p.value?.toFixed(2)}`
    }},
    grid: { top: 20, bottom: 30, left: 60, right: 20 },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#e8e4dc' } }, boundaryGap: false },
    yAxis: { type: 'value', scale: true, axisLabel: { fontFamily: 'DM Sans' }, splitLine: { lineStyle: { color: '#f2f0ea' } } },
    series: [{
      type: 'line', data: prices, smooth: true, symbol: 'circle', symbolSize: 4,
      lineStyle: { width: 2.5, color },
      itemStyle: { color },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: color === '#c53d43' ? 'rgba(197,61,67,0.15)' : 'rgba(46,125,50,0.15)' }, { offset: 1, color: color === '#c53d43' ? 'rgba(197,61,67,0.01)' : 'rgba(46,125,50,0.01)' }] } },
    }]
  }
})

onMounted(async () => {
  await refreshData()
  trackerStore.initialLoading = false
})

// Refresh data when re-activated from keep-alive cache (stale-while-revalidate)
onActivated(refreshData)
</script>

<style scoped>
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 24px;
}
.toolbar-actions { display: flex; gap: 8px; align-items: center; }

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
.sc-pnl::before { background: var(--vermillion); }
.sc-change::before { background: var(--gold); }
.sc-count::before { background: var(--text-secondary); }
.sc-rates::before { background: var(--text-muted); }
.sc-icon { font-size: 20px; opacity: 0.6; }
.sc-body { flex: 1; min-width: 0; }
.sc-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
.sc-value { font-size: 22px; font-weight: 700; font-family: var(--font-body); }
.sc-unit { font-size: 12px; color: var(--text-muted); font-weight: 400; }
.sc-rates-list { display: flex; flex-direction: column; gap: 2px; }
.rate-row { display: flex; justify-content: space-between; gap: 8px; font-size: 13px; }
.rate-label { color: var(--text-secondary); }
.rate-value { font-weight: 600; font-family: var(--font-body); }
.positive { color: var(--positive); }
.negative { color: var(--negative); }
.muted { color: var(--text-muted); }

.chart-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}

/* Stock cards */
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.stock-card { padding: 16px; }
.stock-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.stock-ticker { font-weight: 700; font-size: 16px; font-family: var(--font-body); }
.stock-source {
  font-size: 10px; padding: 2px 8px; border-radius: 10px;
  background: var(--bg-secondary, #f5f5f5); color: var(--text-secondary);
}
.stock-source.holding { background: var(--vermillion-soft); color: var(--vermillion); }
.stock-source.watchlist { background: var(--gold-soft); color: var(--gold); }
.stock-name { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; }
.stock-account { font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.td-account { font-size: 11px; color: var(--text-muted); }
.stock-price-row { display: flex; align-items: baseline; gap: 4px; margin-bottom: 2px; }
.stock-price { font-size: 22px; font-weight: 700; font-family: var(--font-body); }
.stock-currency { font-size: 12px; color: var(--text-muted); }
.stock-change { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.change-arrow { font-size: 10px; }
.sparkline-wrap { margin: 4px -4px 0; }
.sparkline-wrap.clickable { cursor: pointer; border-radius: 4px; }
.sparkline-wrap.clickable:hover { background: var(--bg-secondary, #f5f5f5); }
.stock-card-actions { margin-top: 6px; display: flex; gap: 4px; }
.trend-btn { font-size: 11px; padding: 2px 6px; }
.stock-holding-info {
  display: flex; justify-content: space-between;
  font-size: 11px; color: var(--text-secondary);
  margin-top: 8px; padding-top: 8px;
  border-top: 1px dashed var(--border, #eee);
}

/* Trend modal */
.modal-lg { max-width: 640px; width: 90vw; }
.trend-range-btns { display: flex; gap: 4px; }
.trend-loading, .trend-empty { text-align: center; padding: 48px 0; color: var(--text-muted); }

/* Table */
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 10px; border-bottom: 2px solid var(--border, #eee); font-size: 11px; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; }
td { padding: 8px 10px; border-bottom: 1px solid var(--border, #eee); }
tr:hover td { background: var(--paper-warm, #f5f2ec); }

/* Empty state */
.empty-state { text-align: center; padding: 48px 24px; color: var(--text-secondary); }
.empty-state p { margin-bottom: 16px; }

/* Add modal */
.add-error { color: var(--vermillion); font-size: 13px; margin-top: 4px; }
.edit-hint { font-size: 11px; color: var(--text-muted); font-weight: 400; }
.form-row { display: flex; gap: 12px; }
.form-row .form-group { flex: 1; }

/* Refresh icon */
.refresh-icon { display: inline-block; transition: transform 0.3s; }
.refresh-icon.spinning { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Mobile */
@media (max-width: 768px) {
  .summary-row { grid-template-columns: repeat(2, 1fr); }
  .grid-3 { grid-template-columns: 1fr; }
  .toolbar { flex-direction: column; gap: 8px; align-items: flex-start; }
  .toolbar-actions { width: 100%; justify-content: flex-end; }
}

.page-loading {
  display: flex; flex-direction: column; align-items: center; justify-content: center; height: 50vh; gap: 16px;
}
.page-loading-spinner {
  width: 32px; height: 32px; border: 3px solid var(--paper-line); border-top-color: var(--vermillion);
  border-radius: 50%; animation: spin .7s linear infinite;
}
.page-loading-text { font-size: 14px; color: var(--text-muted); letter-spacing: .04em; }
</style>
