<template>
  <div>
    <div v-if="pageLoading" class="page-loading">
      <div class="page-loading-spinner"></div>
      <div class="page-loading-text">数据加载中...</div>
    </div>
    <template v-else>
    <div class="toolbar">
      <h2 style="margin:0">入金分析</h2>
      <button class="btn btn-ghost btn-sm" @click="screenshot" :disabled="screenshotLoading" title="截图分享">
        &#x1F4F7;<span class="btn-screenshot-text"> 截图</span>
      </button>
    </div>

    <div ref="investmentsContent">
    <!-- Annual P&L -->
    <div class="card">
      <div class="section-header">
        <h3 style="margin:0">年度盈亏</h3>
        <div style="display:flex;gap:8px;align-items:center">
          <select v-model="groupMode" class="form-select" style="width:auto;min-width:120px">
            <option value="account">按账户分组</option>
            <option value="year">按年份分组</option>
          </select>
          <button class="btn btn-primary btn-sm" @click="newPnl">+ 新增记录</button>
        </div>
      </div>

      <!-- Grouped by Account -->
      <template v-if="groupMode === 'account'">
        <div v-for="group in groupedByAccount" :key="group.key" class="pnl-group">
          <div class="pnl-group-header">{{ group.label }}</div>
          <div class="table-wrap"><table>
            <thead>
              <tr><th>年份</th><th>盈亏金额</th><th>币种</th><th>备注</th><th class="action-col">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="t in group.items" :key="t.id">
                <td class="date-cell">{{ t.date?.substring(0, 4) }}</td>
                <td :class="t.amount >= 0 ? 'positive' : 'negative'" style="font-weight:600">{{ formatMoney(t.amount) }}</td>
                <td><span class="curr-badge">{{ t.currency }}</span></td>
                <td style="color:var(--text-secondary)">{{ t.notes }}</td>
                <td class="action-col">
                  <button class="btn-link" @click="editPnl(t)">编辑</button>
                  <button class="btn-link danger" @click="deletePnl(t.id)">删除</button>
                </td>
              </tr>
            </tbody>
          </table></div>
          <div class="pnl-group-summary">
            <span>合计</span>
            <span :class="group.total >= 0 ? 'positive' : 'negative'" style="font-weight:600">{{ formatMoney(group.total) }} CNY</span>
          </div>
        </div>
      </template>

      <!-- Grouped by Year -->
      <template v-else>
        <div v-for="group in groupedByYear" :key="group.key" class="pnl-group">
          <div class="pnl-group-header">{{ group.key }}年</div>
          <div class="table-wrap"><table>
            <thead>
              <tr><th>账户</th><th>盈亏金额</th><th>币种</th><th>备注</th><th class="action-col">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="t in group.items" :key="t.id">
                <td style="color:var(--text-secondary)">{{ accountName(t.account_id) }}</td>
                <td :class="t.amount >= 0 ? 'positive' : 'negative'" style="font-weight:600">{{ formatMoney(t.amount) }}</td>
                <td><span class="curr-badge">{{ t.currency }}</span></td>
                <td style="color:var(--text-secondary)">{{ t.notes }}</td>
                <td class="action-col">
                  <button class="btn-link" @click="editPnl(t)">编辑</button>
                  <button class="btn-link danger" @click="deletePnl(t.id)">删除</button>
                </td>
              </tr>
            </tbody>
          </table></div>
          <div class="pnl-group-summary">
            <span>合计</span>
            <span :class="group.total >= 0 ? 'positive' : 'negative'" style="font-weight:600">{{ formatMoney(group.total) }} CNY</span>
          </div>
        </div>
      </template>
    </div>

    <!-- P&L Modal -->
    <div v-if="pnlModal" class="modal-overlay" @click.self="pnlModal=null">
      <div class="card modal">
        <h3>{{ pnlModal === 'new' ? '新增盈亏记录' : '编辑盈亏记录' }}</h3>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">年份</label>
            <select v-model="pnlForm.year" class="form-select">
              <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">账户</label>
            <select v-model="pnlForm.account_id" class="form-select">
              <option value="">请选择账户</option>
              <option v-for="a in accounts" :key="a.id" :value="a.id">{{ a.name }}</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">盈亏金额</label>
            <input v-model.number="pnlForm.amount" type="number" step="0.01" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">币种</label>
            <select v-model="pnlForm.currency" class="form-select">
              <option v-for="c in currencyOptions" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">备注</label>
          <input v-model="pnlForm.notes" class="form-input" />
        </div>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="pnlModal=null">取消</button>
          <button class="btn btn-primary" @click="savePnl">保存</button>
        </div>
      </div>
    </div>

    <!-- Fund Flow Analysis -->
    <div class="card" style="margin-top:18px">
      <div class="section-header">
        <h3 style="margin:0">入金分析</h3>
        <div style="display:flex;gap:8px;align-items:center">
          <select v-model="displayCurrency" class="form-select" style="width:auto;min-width:80px">
            <option v-for="c in currencyOptions" :key="c" :value="c">{{ c }}</option>
          </select>
          <select v-model="flowAccountId" class="form-select" style="width:auto;min-width:140px">
            <option value="">选择账户</option>
            <option v-for="a in investmentAccounts" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select>
          <button class="btn btn-primary btn-sm" @click="newFlow" :disabled="!flowAccountId">+ 新增</button>
        </div>
      </div>

      <!-- Analysis Summary -->
      <template v-if="flowAnalysis">
        <div class="grid-2" style="margin-bottom:16px">
          <div class="card analysis-metric">
            <div class="card-title" style="display:flex;align-items:center;gap:6px">
              入金总额 (历史汇率)
              <button class="btn-icon" title="编辑" @click="startEditDepositFlows">&#x270E;</button>
            </div>
            <div v-if="editingDepositFlows" class="ni-edit">
              <div v-for="(item, i) in depositFlowItems" :key="i" class="ni-row">
                <input v-model.number="item.amount" type="number" step="0.01" class="form-input ni-amount" placeholder="金额" />
                <select v-model="item.currency" class="form-select ni-currency" @change="onFlowCurrencyChange(item)">
                  <option v-for="c in currencyOptions" :key="c" :value="c">{{ c }}</option>
                </select>
                <input v-model.number="item.rate_at_time" type="number" step="0.0001" class="form-input ni-rate" placeholder="汇率" />
                <span class="ni-cny">→ {{ formatMoney((item.amount || 0) * (item.rate_at_time || 0)) }} CNY</span>
                <button class="btn-link danger" @click="depositFlowItems.splice(i, 1)" style="padding:4px;font-size:16px">&times;</button>
              </div>
              <button class="btn-link" @click="depositFlowItems.push({ amount: 0, currency: 'CNY', rate_at_time: 1.0 })">+ 添加</button>
              <div class="ni-total">
                合计 <strong>{{ formatMoney(depositFlowTotalCny) }}</strong> CNY
              </div>
              <div class="ni-actions">
                <button class="btn btn-ghost btn-sm" @click="editingDepositFlows=false">取消</button>
                <button class="btn btn-primary btn-sm" @click="saveDepositFlows">保存</button>
              </div>
            </div>
            <div v-else class="card-value analysis-value">{{ formatMoney(convertCny(flowAnalysis.total_deposited_cny)) }} <span class="curr-label">{{ displayCurrency }}</span></div>
          </div>
          <div class="card analysis-metric">
            <div class="card-title" style="display:flex;align-items:center;gap:6px">
              出金总额 (历史汇率)
              <button class="btn-icon" title="编辑" @click="startEditWithdrawFlows">&#x270E;</button>
            </div>
            <div v-if="editingWithdrawFlows" class="ni-edit">
              <div v-for="(item, i) in withdrawFlowItems" :key="i" class="ni-row">
                <input v-model.number="item.amount" type="number" step="0.01" class="form-input ni-amount" placeholder="金额" />
                <select v-model="item.currency" class="form-select ni-currency" @change="onFlowCurrencyChange(item)">
                  <option v-for="c in currencyOptions" :key="c" :value="c">{{ c }}</option>
                </select>
                <input v-model.number="item.rate_at_time" type="number" step="0.0001" class="form-input ni-rate" placeholder="汇率" />
                <span class="ni-cny">→ {{ formatMoney((item.amount || 0) * (item.rate_at_time || 0)) }} CNY</span>
                <button class="btn-link danger" @click="withdrawFlowItems.splice(i, 1)" style="padding:4px;font-size:16px">&times;</button>
              </div>
              <button class="btn-link" @click="withdrawFlowItems.push({ amount: 0, currency: 'CNY', rate_at_time: 1.0 })">+ 添加</button>
              <div class="ni-total">
                合计 <strong>{{ formatMoney(withdrawFlowTotalCny) }}</strong> CNY
              </div>
              <div class="ni-actions">
                <button class="btn btn-ghost btn-sm" @click="editingWithdrawFlows=false">取消</button>
                <button class="btn btn-primary btn-sm" @click="saveWithdrawFlows">保存</button>
              </div>
            </div>
            <div v-else class="card-value analysis-value">{{ formatMoney(convertCny(flowAnalysis.total_withdrawn_cny)) }} <span class="curr-label">{{ displayCurrency }}</span></div>
          </div>
        </div>
        <div class="grid-3" style="margin-bottom:16px">
          <div class="card analysis-metric">
            <div class="card-title" style="display:flex;align-items:center;gap:6px">
              当前账户资产
              <button class="btn-icon" title="编辑" @click="startEditCurrentValue">&#x270E;</button>
            </div>
            <div v-if="editingCurrentValue" class="current-value-edit">
              <input v-model.number="currentValueInput" type="number" step="0.01" class="rate-input" style="width:120px" @keyup.enter="saveCurrentValue" @keyup.escape="editingCurrentValue=false" />
              <span class="curr-label" style="margin-right:4px">{{ displayCurrency }}</span>
              <button class="btn-link" @click="saveCurrentValue">✓</button>
              <button class="btn-link" @click="editingCurrentValue=false">✗</button>
            </div>
            <div v-else class="card-value analysis-value">{{ formatMoney(convertCny(flowAnalysis.current_value_cny)) }} <span class="curr-label">{{ displayCurrency }}</span></div>
          </div>
          <div class="card analysis-metric">
            <div class="card-title">净投入</div>
            <div class="card-value analysis-value">{{ formatMoney(convertCny(flowAnalysis.net_invested_cny)) }} <span class="curr-label">{{ displayCurrency }}</span></div>
            <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">入金 - 出金</div>
          </div>
          <div class="card analysis-metric">
            <div class="card-title">总盈亏</div>
            <div class="card-value analysis-value" :class="flowAnalysis.unrealized_pnl >= 0 ? 'positive' : 'negative'">
              {{ (flowAnalysis.unrealized_pnl >= 0 ? '+' : '') + formatMoney(convertCny(flowAnalysis.unrealized_pnl)) }} <span class="curr-label">{{ displayCurrency }}</span>
              <span style="font-size:14px;font-weight:400">({{ flowAnalysis.unrealized_pnl_pct.toFixed(2) }}%)</span>
            </div>
          </div>
        </div>
        <div class="grid-2" style="margin-bottom:16px">
          <div class="card analysis-metric">
            <div class="card-title">汇率影响</div>
            <div class="card-value analysis-value" :class="flowAnalysis.fx_gain_loss >= 0 ? 'positive' : 'negative'">
              {{ (flowAnalysis.fx_gain_loss >= 0 ? '+' : '') + formatMoney(convertCny(flowAnalysis.fx_gain_loss)) }} <span class="curr-label">{{ displayCurrency }}</span>
            </div>
            <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">
              投入按当前汇率折算 {{ formatMoney(convertCny(flowAnalysis.deposits_at_current_rate_cny)) }} {{ displayCurrency }}
            </div>
          </div>
          <div class="card analysis-metric">
            <div class="card-title">投资收益（剔除汇率）</div>
            <div class="card-value analysis-value" :class="flowAnalysis.investment_gain_loss >= 0 ? 'positive' : 'negative'">
              {{ (flowAnalysis.investment_gain_loss >= 0 ? '+' : '') + formatMoney(convertCny(flowAnalysis.investment_gain_loss)) }} <span class="curr-label">{{ displayCurrency }}</span>
            </div>
          </div>
        </div>

        <!-- Flow History -->
        <template v-if="flowAnalysis.flows.length">
          <div class="table-wrap"><table>
            <thead>
              <tr><th>日期</th><th>类型</th><th>金额</th><th>币种</th><th>入金汇率</th><th>折合CNY</th><th>备注</th><th class="action-col">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="f in sortedFlows" :key="f.id">
                <td class="date-cell">{{ f.date }}</td>
                <td><span class="tag" :style="{background: f.type==='deposit'?'rgba(46,125,50,.1)':'rgba(230,81,0,.1)', color: f.type==='deposit'?'#2e7d32':'#e65100'}">{{ f.type === 'deposit' ? '入金' : '出金' }}</span></td>
                <td style="font-weight:600">{{ formatMoney(f.amount) }}</td>
                <td><span class="curr-badge">{{ f.currency }}</span></td>
                <td style="color:var(--text-secondary)">{{ f.rate_at_time }}</td>
                <td style="font-weight:500">{{ formatMoney(f.amount * f.rate_at_time) }}</td>
                <td style="color:var(--text-secondary)">{{ f.notes }}</td>
                <td class="action-col">
                  <button class="btn-link" @click="editFlow(f)">编辑</button>
                  <button class="btn-link danger" @click="deleteFlow(f.id)">删除</button>
                </td>
              </tr>
            </tbody>
          </table></div>
        </template>
        <div v-else style="padding:24px;text-align:center;color:var(--text-muted)">
          暂无入金/出金记录，点击「+ 新增」开始记录
        </div>
      </template>
      <div v-else-if="flowAccountId" style="padding:24px;text-align:center;color:var(--text-muted)">
        加载中...
      </div>
    </div>

    <!-- Fund Flow Modal -->
    <div v-if="flowModal" class="modal-overlay" @click.self="flowModal=null">
      <div class="card modal">
        <h3>{{ flowModal === 'new' ? '新增入金/出金' : '编辑入金/出金' }}</h3>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">类型</label>
            <select v-model="flowForm.type" class="form-select">
              <option value="deposit">入金</option>
              <option value="withdraw">出金</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">日期</label>
            <input v-model="flowForm.date" type="date" class="form-input" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">金额</label>
            <input v-model.number="flowForm.amount" type="number" step="0.01" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">币种</label>
            <select v-model="flowForm.currency" class="form-select" @change="autoFillRate">
              <option v-for="c in currencyOptions" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">入金汇率（折合CNY）</label>
          <div style="display:flex;gap:8px;align-items:center">
            <input v-model.number="flowForm.rate_at_time" type="number" step="0.0001" class="form-input" style="flex:1" />
            <button class="btn btn-ghost btn-sm" @click="autoFillRate" type="button">当前汇率</button>
          </div>
          <div style="font-size:12px;color:var(--text-secondary);margin-top:4px">
            折合 {{ formatMoney((flowForm.amount || 0) * (flowForm.rate_at_time || 0)) }} CNY
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">备注</label>
          <input v-model="flowForm.notes" class="form-input" />
        </div>
        <div class="modal-actions">
          <button class="btn btn-ghost" @click="flowModal=null">取消</button>
          <button class="btn btn-primary" @click="saveFlow">保存</button>
        </div>
      </div>
    </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import api from '../api'
import { useScreenshot } from '../composables/useScreenshot'
import { useCurrencies } from '../composables/useCurrencies'
import { formatMoney } from '../composables/useFormatters'
import { useAccountsStore } from '../stores/accounts'
import { useDashboardStore } from '../stores/dashboard'

const accountsStore = useAccountsStore()
const dashboardStore = useDashboardStore()
const investmentsContent = ref(null)
const { screenshotLoading, screenshot } = useScreenshot(investmentsContent, '入金分析')
const pageLoading = ref(true)
const transactions = ref([])
const { rates: exchangeRates, currencyOptions, fetchRates: fetchCurrencyRates } = useCurrencies()
const pnlModal = ref(null)
const pnlForm = ref({})
const groupMode = ref('account')
const flowAccountId = ref('')
const flowAnalysis = ref(null)
const flowModal = ref(null)
const flowForm = ref({})
const editingCurrentValue = ref(false)
const currentValueInput = ref(0)
const editingDepositFlows = ref(false)
const depositFlowItems = ref([])
const editingWithdrawFlows = ref(false)
const withdrawFlowItems = ref([])
const displayCurrency = ref('CNY')

const cnyToDisplayRate = computed(() => {
  if (displayCurrency.value === 'CNY') return 1
  const rate = exchangeRates.value.find(r => r.currency === displayCurrency.value)
  return rate ? 1 / rate.rate_to_cny : 1
})

const convertCny = (cnyAmount) => (cnyAmount || 0) * cnyToDisplayRate.value

const accounts = computed(() => accountsStore.accounts)
const accountName = (id) => accountsStore.accountName(id)
const investmentAccounts = computed(() => accountsStore.investmentAccounts)

const pnlTransactions = computed(() =>
  transactions.value
    .filter(t => t.type === 'pnl')
    .sort((a, b) => b.date?.localeCompare(a.date))
)

const groupedByAccount = computed(() => {
  const map = new Map()
  for (const t of pnlTransactions.value) {
    const key = t.account_id || '_unknown'
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(t)
  }
  return [...map.entries()].map(([key, items]) => ({
    key,
    label: accountName(key === '_unknown' ? '' : key),
    items,
    total: items.reduce((s, t) => s + (t.amount || 0), 0),
  }))
})

const groupedByYear = computed(() => {
  const map = new Map()
  for (const t of pnlTransactions.value) {
    const key = t.date?.substring(0, 4) || '未知'
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(t)
  }
  return [...map.entries()]
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([key, items]) => ({
      key,
      items,
      total: items.reduce((s, t) => s + (t.amount || 0), 0),
    }))
})

const availableYears = computed(() => {
  const current = new Date().getFullYear()
  const years = []
  for (let y = current + 1; y >= current - 10; y--) years.push(y)
  return years
})

const defaultPnlForm = () => ({
  year: new Date().getFullYear(),
  account_id: '',
  amount: 0,
  currency: 'CNY',
  notes: '',
})

const newPnl = () => {
  pnlModal.value = 'new'
  pnlForm.value = defaultPnlForm()
}

const editPnl = (t) => {
  pnlModal.value = t.id
  pnlForm.value = {
    year: t.date?.substring(0, 4) || new Date().getFullYear(),
    account_id: t.account_id,
    amount: t.amount,
    currency: t.currency,
    notes: t.notes || '',
  }
}

const savePnl = async () => {
  if (!pnlForm.value.account_id) {
    alert('请选择账户')
    return
  }
  const dateStr = pnlForm.value.year + '-01-01'
  const payload = {
    account_id: pnlForm.value.account_id,
    type: 'pnl',
    date: dateStr,
    amount: pnlForm.value.amount || 0,
    currency: pnlForm.value.currency || 'CNY',
    notes: pnlForm.value.notes || '',
  }
  try {
    if (pnlModal.value === 'new') {
      const id = 'tx_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
      await api.createTransaction({ id, ...payload })
    } else {
      await api.updateTransaction(pnlModal.value, payload)
    }
    dashboardStore.invalidateAll()
    accountsStore.invalidateAll()
    pnlModal.value = null
    transactions.value = await api.getTransactions()
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}

const deletePnl = async (id) => {
  if (!confirm('确认删除该盈亏记录？')) return
  await api.deleteTransaction(id)
  dashboardStore.invalidateAll()
  accountsStore.invalidateAll()
  transactions.value = await api.getTransactions()
}

// --- Fund Flow Analysis ---

const sortedFlows = computed(() => {
  if (!flowAnalysis.value) return []
  return [...flowAnalysis.value.flows].sort((a, b) => b.date?.localeCompare(a.date))
})

watch(flowAccountId, async (newId) => {
  if (newId) {
    try {
      flowAnalysis.value = await api.getFundFlowAnalysis(newId)
    } catch (e) {
      console.error(e)
      flowAnalysis.value = null
    }
  } else {
    flowAnalysis.value = null
  }
})

const autoFillRate = () => {
  if (flowForm.value.currency === 'CNY') {
    flowForm.value.rate_at_time = 1.0
  } else {
    const rate = exchangeRates.value.find(r => r.currency === flowForm.value.currency)
    if (rate) flowForm.value.rate_at_time = rate.rate_to_cny
  }
}

const defaultFlowForm = () => ({
  type: 'deposit',
  date: new Date().toISOString().slice(0, 10),
  amount: 0,
  currency: 'CNY',
  rate_at_time: 1.0,
  notes: '',
})

const newFlow = () => {
  flowModal.value = 'new'
  flowForm.value = defaultFlowForm()
}

const editFlow = (f) => {
  flowModal.value = f.id
  flowForm.value = {
    type: f.type,
    date: f.date,
    amount: f.amount,
    currency: f.currency,
    rate_at_time: f.rate_at_time,
    notes: f.notes || '',
  }
}

const saveFlow = async () => {
  if (!flowAccountId.value) {
    alert('请先选择账户')
    return
  }
  const payload = {
    account_id: flowAccountId.value,
    type: flowForm.value.type,
    date: flowForm.value.date,
    amount: flowForm.value.amount || 0,
    currency: flowForm.value.currency || 'CNY',
    rate_at_time: flowForm.value.rate_at_time || 1.0,
    notes: flowForm.value.notes || '',
  }
  try {
    if (flowModal.value === 'new') {
      const id = 'ff_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
      await api.createFundFlow({ id, ...payload })
    } else {
      await api.updateFundFlow(flowModal.value, payload)
    }
    dashboardStore.invalidateAll()
    accountsStore.invalidateAll()
    flowModal.value = null
    flowAnalysis.value = await api.getFundFlowAnalysis(flowAccountId.value)
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}

const startEditDepositFlows = () => {
  const flows = (flowAnalysis.value?.flows || []).filter(f => f.type === 'deposit')
  depositFlowItems.value = flows.length
    ? flows.map(f => ({ id: f.id, amount: f.amount, currency: f.currency, rate_at_time: f.rate_at_time, date: f.date, notes: f.notes || '' }))
    : [{ amount: 0, currency: 'CNY', rate_at_time: 1.0 }]
  editingDepositFlows.value = true
}

const startEditWithdrawFlows = () => {
  const flows = (flowAnalysis.value?.flows || []).filter(f => f.type === 'withdraw')
  withdrawFlowItems.value = flows.length
    ? flows.map(f => ({ id: f.id, amount: f.amount, currency: f.currency, rate_at_time: f.rate_at_time, date: f.date, notes: f.notes || '' }))
    : [{ amount: 0, currency: 'CNY', rate_at_time: 1.0 }]
  editingWithdrawFlows.value = true
}

const onFlowCurrencyChange = (item) => {
  if (item.currency === 'CNY') {
    item.rate_at_time = 1.0
  } else {
    const rate = exchangeRates.value.find(r => r.currency === item.currency)
    if (rate) item.rate_at_time = rate.rate_to_cny
  }
}

const depositFlowTotalCny = computed(() =>
  depositFlowItems.value.reduce((sum, item) => sum + (item.amount || 0) * (item.rate_at_time || 0), 0)
)

const withdrawFlowTotalCny = computed(() =>
  withdrawFlowItems.value.reduce((sum, item) => sum + (item.amount || 0) * (item.rate_at_time || 0), 0)
)

const saveFlows = async (type, items) => {
  try {
    // Delete existing flows of this type
    const existing = (flowAnalysis.value?.flows || []).filter(f => f.type === type)
    for (const f of existing) {
      await api.deleteFundFlow(f.id)
    }
    // Create new flows from items
    for (const item of items) {
      if (!item.amount) continue
      const id = 'ff_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
      await api.createFundFlow({
        id,
        account_id: flowAccountId.value,
        type,
        currency: item.currency || 'CNY',
        amount: item.amount || 0,
        rate_at_time: item.rate_at_time || 1.0,
        date: item.date || new Date().toISOString().slice(0, 10),
        notes: item.notes || '',
      })
    }
    dashboardStore.invalidateAll()
    accountsStore.invalidateAll()
    flowAnalysis.value = await api.getFundFlowAnalysis(flowAccountId.value)
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}

const saveDepositFlows = async () => {
  await saveFlows('deposit', depositFlowItems.value)
  editingDepositFlows.value = false
}

const saveWithdrawFlows = async () => {
  await saveFlows('withdraw', withdrawFlowItems.value)
  editingWithdrawFlows.value = false
}

const startEditCurrentValue = () => {
  currentValueInput.value = Math.round(convertCny(flowAnalysis.value?.current_value_cny || 0) * 100) / 100
  editingCurrentValue.value = true
}

const saveCurrentValue = async () => {
  const acct = accounts.value.find(a => a.id === flowAccountId.value)
  if (!acct) return
  // Convert display currency amount back to CNY for storage
  const cnyAmount = displayCurrency.value === 'CNY'
    ? (currentValueInput.value || 0)
    : (currentValueInput.value || 0) / cnyToDisplayRate.value
  const balances = [...(acct.balances || [])]
  const cnyIdx = balances.findIndex(b => b.currency === 'CNY')
  if (cnyIdx >= 0) {
    balances[cnyIdx] = { ...balances[cnyIdx], amount: cnyAmount }
  } else {
    balances.push({ currency: 'CNY', amount: cnyAmount, annual_rate: 0 })
  }
  try {
    await api.updateAccount(flowAccountId.value, { balances })
    accountsStore.invalidateAll()
    dashboardStore.invalidateAll()
    const updated = accounts.value.find(a => a.id === flowAccountId.value)
    if (updated) updated.balances = balances
    editingCurrentValue.value = false
    flowAnalysis.value = await api.getFundFlowAnalysis(flowAccountId.value)
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}

const deleteFlow = async (id) => {
  if (!confirm('确认删除该入金/出金记录？')) return
  await api.deleteFundFlow(id)
  dashboardStore.invalidateAll()
  accountsStore.invalidateAll()
  flowAnalysis.value = await api.getFundFlowAnalysis(flowAccountId.value)
}

onMounted(async () => {
  const [t] = await Promise.all([
    api.getTransactions(),
    accountsStore.fetchAccounts(),
    fetchCurrencyRates(),
  ])
  transactions.value = t
  pageLoading.value = false
  // Default to 富途牛牛
  const futu = accounts.value.find(acct => acct.name === '富途牛牛')
  if (futu) flowAccountId.value = futu.id
})

// Re-validate data when re-activated from keep-alive cache
onActivated(async () => {
  const [t] = await Promise.all([
    api.getTransactions(),
    accountsStore.fetchAccounts(),
    fetchCurrencyRates(),
  ])
  transactions.value = t
  const futu = accounts.value.find(acct => acct.name === '富途牛牛')
  if (futu) flowAccountId.value = futu.id
})
</script>

<style scoped>
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.date-cell { font-variant-numeric: tabular-nums; }
.curr-badge {
  display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 11px;
  font-weight: 600; background: var(--paper-warm); color: var(--text-secondary);
  letter-spacing: .04em;
}
.curr-label { font-size: 11px; color: var(--text-muted); margin-left: 2px; }
.pnl-group { margin-bottom: 16px; }
.pnl-group:last-child { margin-bottom: 0; }
.pnl-group-header {
  font-family: var(--font-display); font-size: 15px; font-weight: 600;
  padding: 8px 14px; background: var(--paper-warm); border-radius: var(--radius) var(--radius) 0 0;
  border-bottom: 2px solid var(--paper-line);
}
.pnl-group-summary {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 14px; background: var(--paper-warm); border-radius: 0 0 var(--radius) var(--radius);
  font-size: 13px; font-weight: 500; border-top: 1px dashed var(--paper-line);
}
.analysis-metric { position: relative; overflow: hidden; }
.analysis-metric::before {
  content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%;
  background: var(--gold); border-radius: 3px 0 0 3px;
}
.analysis-value { font-size: 22px; }
.ni-edit { margin-top: 4px; }
.ni-row { display: flex; gap: 6px; align-items: center; margin-bottom: 6px; flex-wrap: wrap; }
.ni-amount { width: 100px; flex-shrink: 0; }
.ni-currency { width: 80px; flex-shrink: 0; }
.ni-rate { width: 90px; flex-shrink: 0; }
.ni-cny { font-size: 12px; color: var(--text-secondary); min-width: 100px; }
.ni-total { font-size: 13px; color: var(--text-secondary); padding: 6px 0; border-top: 1px dashed var(--border, #ddd); margin-top: 4px; }
.ni-total strong { color: var(--gold); font-size: 15px; }
.ni-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
.current-value-edit { display: flex; align-items: center; gap: 4px; margin-top: 2px; }
.btn-icon {
  background: none; border: none; cursor: pointer; font-size: 12px; padding: 1px 3px;
  color: var(--text-muted); border-radius: 4px; transition: all .2s;
}
.btn-icon:hover { color: var(--vermillion); background: var(--bg-secondary, #f5f5f5); }

.page-loading {
  display: flex; flex-direction: column; align-items: center; justify-content: center; height: 50vh; gap: 16px;
}
.page-loading-spinner {
  width: 32px; height: 32px; border: 3px solid var(--paper-line); border-top-color: var(--vermillion);
  border-radius: 50%; animation: spin .7s linear infinite;
}
.page-loading-text { font-size: 14px; color: var(--text-muted); letter-spacing: .04em; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
