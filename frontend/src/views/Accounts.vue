<template>
  <div>
    <div v-if="pageLoading" class="page-loading">
      <div class="page-loading-spinner"></div>
      <div class="page-loading-text">数据加载中...</div>
    </div>
    <template v-else>
    <div class="toolbar">
      <h2 style="margin:0">账户管理</h2>
      <div style="display:flex;gap:8px;align-items:center">
        <button class="btn btn-ghost btn-sm" @click="forceRefreshRates" :disabled="ratesLoading" title="刷新汇率">
          &#x21bb; 汇率
        </button>
        <button class="btn btn-ghost btn-sm" @click="screenshot" :disabled="screenshotLoading" title="截图分享">
          &#x1F4F7;<span class="btn-screenshot-text"> 截图</span>
        </button>
        <button class="btn btn-primary btn-sm" @click="newAccount">+ 新增账户</button>
      </div>
    </div>
    <div ref="accountsContent">
    <div v-for="cat in categories" :key="cat" style="margin-bottom: 24px">
      <div v-if="accountsByCategory(cat).length" style="margin-bottom:12px;">
        <span class="tag" :class="'tag-' + cat">{{ categoryLabel(cat) }}</span>
      </div>
      <draggable v-if="accountsByCategory(cat).length" class="grid-3" :list="categoryLists[cat].value" :group="{ name: cat }" item-key="id" handle=".drag-handle" @end="onDragEnd(cat)">

        <!-- Cash (活期) Card -->
        <template #item="{ element: acct }" v-if="cat === 'cash'">
          <div class="card account-card cat-cash">
            <span class="drag-handle" title="拖拽排序">&#x2630;</span>
            <label class="toggle-label acct-toggle" :class="{ active: !acct.exclude_from_total }" @click.prevent="toggleExcludeFromTotal(acct)">
              <span class="toggle-track"><span class="toggle-thumb"></span></span>
            </label>
            <div class="acct-header" @click="toggleCard(acct.id)" style="cursor:pointer">
              <div style="display:flex;align-items:center;gap:6px">
                <span class="card-arrow">{{ collapsedCards.has(acct.id) ? '▸' : '▾' }}</span>
                <span class="acct-name">{{ acct.name }}</span>
              </div>
              <span class="balance-amount"> {{ formatMoney(cashTotalCny(acct)) }} <span class="balance-currency">CNY</span></span>
            </div>
            <!-- Collapsible: all balances + interest + notes -->
            <div v-show="!collapsedCards.has(acct.id)">
              <div v-for="(b, bi) in acct.balances" :key="bi" class="cash-balance-block">
                <div v-if="acct.balances.length > 1 || b.currency !== 'CNY' || b.annual_rate <= 0" class="balance-row">
                  <span class="balance-amount">{{ formatMoney(b.amount) }}</span>
                  <span class="balance-currency">{{ b.currency }}</span>
                </div>
                <div v-if="b.annual_rate > 0" class="cash-rate-section">
                  <div class="cash-rate-row">
                    <span class="cash-rate-label">年化利率</span>
                    <span class="cash-rate-value">{{ (b.annual_rate * 100).toFixed(2) }}%</span>
                  </div>
                  <div class="cash-daily-row">
                    <span class="cash-daily-label">每日利息</span>
                    <span class="cash-daily-value">{{ formatMoney(calcBalanceDailyInterest(b)) }} CNY</span>
                  </div>
                  <div class="cash-yearly-row">
                    <span class="cash-yearly-label">预计年利息</span>
                    <span class="cash-yearly-value">{{ formatMoney(calcBalanceYearlyInterest(b)) }} CNY</span>
                  </div>
                </div>
              </div>
              <div v-if="hasCashInterest(acct)" class="cash-total-interest">
                <span class="cash-yearly-label">年利息合计</span>
                <span class="cash-yearly-value">{{ formatMoney(calcTotalYearlyInterest(acct)) }} CNY</span>
              </div>
              <div v-if="acct.notes" class="acct-notes">{{ acct.notes }}</div>
            </div>
            <div class="acct-actions">
              <button class="btn btn-sm btn-ghost" @click="editAccount(acct)">编辑</button>
              <button class="btn btn-sm btn-danger" @click="deleteAcct(acct.id)">删除</button>
            </div>
          </div>
        </template>

        <!-- Investment (股票) Card -->
        <template #item="{ element: acct }" v-else-if="cat === 'investment'">
          <div class="card account-card cat-investment">
            <span class="drag-handle" title="拖拽排序">&#x2630;</span>
            <label class="toggle-label acct-toggle" :class="{ active: !acct.exclude_from_total }" @click.prevent="toggleExcludeFromTotal(acct)">
              <span class="toggle-track"><span class="toggle-thumb"></span></span>
            </label>
            <div class="acct-header" @click="toggleCard(acct.id)" style="cursor:pointer">
              <div style="display:flex;align-items:center;gap:6px">
                <span class="card-arrow">{{ collapsedCards.has(acct.id) ? '▸' : '▾' }}</span>
                <span class="acct-name">{{ acct.name }}</span>
              </div>
              <span class="balance-amount"> {{ formatMoney(investmentTotalCny(acct)) }} <span class="balance-currency">CNY</span></span>
            </div>
            <!-- Collapsible: all holdings + notes -->
            <div v-show="!collapsedCards.has(acct.id)">
              <div v-if="accountHoldings(acct.id).length" class="holdings-detail">
                <div class="holdings-header">
                  <span class="holdings-title">持仓明细</span>
                  <button class="btn btn-sm btn-ghost refresh-prices-btn" :disabled="pricesLoading" @click.stop="refreshPrices" :title="pricesLoading ? '刷新中...' : '刷新股价'">
                    <span class="refresh-icon" :class="{ spinning: pricesLoading }">&#x21bb;</span> 刷新股价
                  </button>
                </div>
                <div v-for="h in accountHoldings(acct.id)" :key="h.id" class="holding-row">
                  <div class="holding-main">
                    <span class="holding-ticker">{{ h.ticker }}</span>
                    <span class="holding-shares">{{ h.shares }}股</span>
                    <span class="holding-currency">{{ h.currency }}</span>
                  </div>
                  <div class="holding-price">
                    <span>现价 <strong>{{ h.current_price?.toFixed(2) }}</strong> {{ h.currency }}</span>
                    <span>均价 {{ h.avg_cost_price?.toFixed(2) }} {{ h.currency }}</span>
                  </div>
                  <div class="holding-value">
                    <span>市值 <strong>{{ formatMoney(h.shares * h.current_price) }}</strong> {{ h.currency }}</span>
                    <span v-if="rateToCny(h.currency) && h.currency !== 'CNY'" class="holding-cny">≈ {{ formatMoney(h.shares * h.current_price * rateToCny(h.currency)) }} CNY</span>
                    <span v-if="rateToCny(h.currency) && h.currency !== 'CNY'" class="holding-rate">汇率 {{ rateToCny(h.currency) }}</span>
                  </div>
                </div>
              </div>
              <div v-if="acct.notes" class="acct-notes">{{ acct.notes }}</div>
            </div>
            <div class="acct-actions">
              <button class="btn btn-sm btn-ghost" @click="editAccount(acct)">编辑</button>
              <button class="btn btn-sm btn-danger" @click="deleteAcct(acct.id)">删除</button>
            </div>
          </div>
        </template>

        <!-- Future Cash Card (公积金/社保) -->
        <template #item="{ element: acct }" v-else-if="cat === 'future_cash'">
          <div class="card account-card cat-future_cash">
            <span class="drag-handle" title="拖拽排序">&#x2630;</span>
            <label class="toggle-label acct-toggle" :class="{ active: !acct.exclude_from_total }" @click.prevent="toggleExcludeFromTotal(acct)">
              <span class="toggle-track"><span class="toggle-thumb"></span></span>
            </label>
            <div class="acct-header" @click="toggleCard(acct.id)" style="cursor:pointer">
              <div style="display:flex;align-items:center;gap:6px">
                <span class="card-arrow">{{ collapsedCards.has(acct.id) ? '▸' : '▾' }}</span>
                <span class="acct-name">{{ acct.name }}</span>
              </div>
              <span class="balance-amount"> {{ formatMoney(futureCashTotalCny(acct)) }} <span class="balance-currency">CNY</span></span>
            </div>
            <!-- Collapsible: all sub_accounts / balances + notes -->
            <div v-show="!collapsedCards.has(acct.id)">
              <div v-if="acct.sub_accounts && acct.sub_accounts.length" class="sub-accounts">
                <div v-for="sa in acct.sub_accounts" :key="sa.label" class="sub-account-row">
                  <span class="sub-label">{{ sa.label }}</span>
                  <span class="sub-amount">{{ formatMoney(sa.amount) }} CNY</span>
                </div>
              </div>
              <div v-else-if="acct.balances && acct.balances.length">
                <div v-for="b in acct.balances" :key="b.currency" class="balance-row">
                  <span class="balance-amount">{{ formatMoney(b.amount) }}</span>
                  <span class="balance-currency">{{ b.currency }}</span>
                </div>
              </div>
              <div v-if="acct.notes" class="acct-notes">{{ acct.notes }}</div>
            </div>
            <div class="acct-actions">
              <button class="btn btn-sm btn-ghost" @click="editAccount(acct)">编辑</button>
              <button class="btn btn-sm btn-danger" @click="deleteAcct(acct.id)">删除</button>
            </div>
          </div>
        </template>

        <!-- Insurance (保险) Card -->
        <template #item="{ element: acct }" v-else-if="cat === 'insurance'">
          <div class="card account-card cat-insurance">
            <span class="drag-handle" title="拖拽排序">&#x2630;</span>
            <label class="toggle-label acct-toggle" :class="{ active: !acct.exclude_from_total }" @click.prevent="toggleExcludeFromTotal(acct)">
              <span class="toggle-track"><span class="toggle-thumb"></span></span>
            </label>
            <div class="acct-header" @click="toggleCard(acct.id)" style="cursor:pointer">
              <div style="display:flex;align-items:center;gap:6px">
                <span class="card-arrow">{{ collapsedCards.has(acct.id) ? '▸' : '▾' }}</span>
                <span class="acct-name">{{ acct.name }}</span>
              </div>
              <span v-if="acct.ins_premium > 0 && acct.ins_paid_periods > 0" class="balance-amount"> {{ formatMoney(acct.ins_premium * acct.ins_paid_periods) }} <span class="balance-currency">CNY</span></span>
            </div>
            <!-- Always show key summary: premium + progress -->
            <div style="padding-right: 48px">
              <div v-if="acct.ins_premium > 0" class="ins-detail-row">
                <span class="ins-detail-label">年交保费</span>
                <span class="ins-detail-value">{{ formatMoney(acct.ins_premium) }} CNY</span>
              </div>
              <div v-if="acct.ins_paid_periods > 0" class="ins-detail-row">
                <span class="ins-detail-label">交费进度</span>
                <span class="ins-detail-value">{{ acct.ins_paid_periods }} / {{ acct.ins_total_periods }} 期</span>
              </div>
            </div>
            <!-- Collapsible: remaining details -->
            <div v-show="!collapsedCards.has(acct.id)">
              <div v-for="b in acct.balances" :key="b.currency" class="balance-row">
                <span class="balance-amount">{{ formatMoney(b.amount) }}</span>
                <span class="balance-currency">{{ b.currency }}</span>
              </div>
              <div v-if="hasInsDetails(acct)" class="ins-detail-section">
                <div v-if="acct.ins_rate > 0" class="ins-detail-row">
                  <span class="ins-detail-label">年利率</span>
                  <span class="ins-detail-value ins-rate-value">{{ (acct.ins_rate * 100).toFixed(2) }}%</span>
                </div>
                <div v-if="acct.ins_start_year > 0" class="ins-detail-row">
                  <span class="ins-detail-label">开始领息</span>
                  <span class="ins-detail-value">第 {{ acct.ins_start_year }} 年</span>
                </div>
                <div v-if="acct.ins_start_date" class="ins-detail-row">
                  <span class="ins-detail-label">保险开始日期</span>
                  <span class="ins-detail-value">{{ acct.ins_start_date }}</span>
                </div>
                <div v-if="acct.ins_birth_date" class="ins-detail-row">
                  <span class="ins-detail-label">保险人出生日期</span>
                  <span class="ins-detail-value">{{ acct.ins_birth_date }}</span>
                </div>
                <div v-if="acct.ins_end_date" class="ins-detail-row">
                  <span class="ins-detail-label">保单终止日期</span>
                  <span class="ins-detail-value">{{ acct.ins_end_date }}</span>
                </div>
                <div v-if="acct.ins_start_date && acct.ins_end_date" class="ins-detail-row">
                  <span class="ins-detail-label">保险年限</span>
                  <span class="ins-detail-value">{{ calcInsYears(acct) }} 年</span>
                </div>
                <template v-if="acct.ins_payout_schedule && acct.ins_payout_schedule.length">
                  <div class="ins-schedule-title">领取计划</div>
                  <div v-for="(p, pi) in acct.ins_payout_schedule" :key="pi" class="ins-schedule-row">
                    <span class="ins-schedule-label">{{ p.label }}</span>
                    <span class="ins-schedule-amount">{{ formatMoney(p.annual_amount) }} × {{ p.years }}年 = {{ formatMoney(p.annual_amount * p.years) }} CNY</span>
                  </div>
                  <div class="ins-schedule-total">
                    <span>总领取</span>
                    <span class="ins-payout-value">{{ formatMoney(acct.ins_payout_schedule.reduce((s, p) => s + p.annual_amount * p.years, 0)) }} CNY</span>
                  </div>
                </template>
                <template v-else>
                  <div class="ins-detail-row ins-payout-row">
                    <span class="ins-detail-label">到期后每年领取</span>
                    <span class="ins-detail-value ins-payout-value">{{ formatMoney(calcInsAnnualPayout(acct)) }} CNY</span>
                  </div>
                </template>
                <div v-if="acct.ins_paid_periods > 0" class="ins-detail-row">
                  <span class="ins-detail-label">已交总额</span>
                  <span class="ins-detail-value">{{ formatMoney(acct.ins_paid_periods * acct.ins_premium) }} CNY</span>
                </div>
                <div v-if="acct.ins_total_periods > 0" class="ins-detail-row">
                  <span class="ins-detail-label">应交总额</span>
                  <span class="ins-detail-value">{{ formatMoney(acct.ins_total_periods * acct.ins_premium) }} CNY</span>
                </div>
              </div>
              <div v-if="acct.notes" class="acct-notes">{{ acct.notes }}</div>
            </div>
            <div class="acct-actions">
              <button class="btn btn-sm btn-ghost" @click="editAccount(acct)">编辑</button>
              <button class="btn btn-sm btn-danger" @click="deleteAcct(acct.id)">删除</button>
            </div>
          </div>
        </template>

      </draggable>
    </div>
    </div>

    <!-- Edit/Create Modal -->
    <div v-if="editing" class="modal-overlay" @click.self="editing=null">
      <div class="card modal">
        <h3>{{ editing === 'new' ? '新增账户' : '编辑账户' }}</h3>

        <!-- Common fields -->
        <div class="form-group">
          <label class="form-label">名称</label>
          <input v-model="form.name" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">类别</label>
          <select v-model="form.category" class="form-select" @change="onCategoryChange">
            <option v-for="cat in categories" :key="cat" :value="cat">{{ categoryLabel(cat) }}</option>
          </select>
        </div>

        <!-- Balances: for all except future_cash (future_cash uses sub_accounts) -->
        <div v-if="form.category !== 'future_cash'" class="form-group">
          <label class="form-label">余额</label>
          <div v-for="(b, i) in form.balances" :key="i" class="balance-form-row">
            <input v-model.number="b.amount" type="number" class="form-input" style="flex:1" />
            <select v-model="b.currency" class="form-select" style="width:90px">
              <option v-for="c in currencyOptions" :key="c" :value="c">{{ c }}</option>
            </select>
            <input v-if="form.category === 'cash'" v-model.number="b.annual_rate_pct" type="number" step="0.01" class="form-input" style="width:100px" placeholder="利率%" />
            <button class="btn-link danger" @click="form.balances.splice(i, 1)" style="padding:8px;font-size:16px">&times;</button>
          </div>
          <button class="btn-link" @click="form.balances.push({ currency: 'CNY', amount: 0, annual_rate_pct: 0 })">+ 添加余额</button>
          <div v-if="form.category === 'cash' && formTotalDailyInterest() > 0" class="cash-form-preview">
            每日利息约 <strong>{{ formatMoney(formTotalDailyInterest()) }}</strong> CNY
          </div>
        </div>

        <!-- Sub accounts: for future_cash (公积金/社保), default open -->
        <div v-if="form.category === 'future_cash'" class="form-group">
          <label class="form-label">地域明细</label>
          <div v-for="(sa, i) in form.sub_accounts" :key="i" class="balance-form-row">
            <input v-model="sa.label" class="form-input" style="flex:1" placeholder="地域（如：北京）" />
            <input v-model.number="sa.amount" type="number" class="form-input" style="flex:1" />
            <button class="btn-link danger" @click="form.sub_accounts.splice(i, 1)" style="padding:8px;font-size:16px">&times;</button>
          </div>
          <button class="btn-link" @click="form.sub_accounts.push({ label: '', amount: 0 })">+ 添加地域</button>
        </div>

        <!-- Insurance fields -->
        <div v-if="form.category === 'insurance'" class="ins-form-section">
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">年交保费</label>
              <input v-model.number="form.ins_premium" type="number" class="form-input" placeholder="如：6000" />
            </div>
            <div class="form-group">
              <label class="form-label">总期数</label>
              <input v-model.number="form.ins_total_periods" type="number" class="form-input" placeholder="如：5" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">已交期数</label>
              <input v-model.number="form.ins_paid_periods" type="number" class="form-input" placeholder="如：1" />
            </div>
            <div class="form-group">
              <label class="form-label">第几年开始领</label>
              <input v-model.number="form.ins_start_year" type="number" class="form-input" placeholder="如：18" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">年利率(%)</label>
              <input v-model.number="form.ins_rate_pct" type="number" step="0.01" class="form-input" placeholder="如：2.5" />
            </div>
            <div class="form-group">
              <label class="form-label">每年领取金额</label>
              <input v-model.number="form.ins_annual_payout" type="number" class="form-input" placeholder="无分段计划时使用" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">保险开始日期</label>
              <input v-model="form.ins_start_date" type="date" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">保险人出生日期</label>
              <input v-model="form.ins_birth_date" type="date" class="form-input" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">保单终止日期</label>
              <input v-model="form.ins_end_date" type="date" class="form-input" />
            </div>
            <div class="form-group" style="display:flex;align-items:flex-end">
              <div v-if="form.ins_start_date && form.ins_end_date" class="cash-form-preview" style="margin:0">
                保险年限 <strong>{{ calcFormInsYears() }}</strong> 年
              </div>
            </div>
          </div>
          <div v-if="calcFormInsAnnualPayout() > 0 && !form.ins_payout_schedule.length" class="cash-form-preview">
            到期后每年领取约 <strong>{{ formatMoney(calcFormInsAnnualPayout()) }}</strong> CNY
          </div>
          <!-- Payout schedule -->
          <div style="margin-top: 8px">
            <label class="form-label">领取计划（分段）</label>
            <div v-for="(p, pi) in form.ins_payout_schedule" :key="pi" class="balance-form-row">
              <input v-model="p.label" class="form-input" style="flex:1" placeholder="如：大学" />
              <input v-model.number="p.annual_amount" type="number" class="form-input" style="flex:1" placeholder="每年金额" />
              <input v-model.number="p.years" type="number" class="form-input" style="width:80px" placeholder="年数" />
              <button class="btn-link danger" @click="form.ins_payout_schedule.splice(pi, 1)" style="padding:8px;font-size:16px">&times;</button>
            </div>
            <button class="btn-link" @click="form.ins_payout_schedule.push({ label: '', annual_amount: 0, years: 1 })">+ 添加领取阶段</button>
            <div v-if="form.ins_payout_schedule.length" class="cash-form-preview">
              总领取 <strong>{{ formatMoney(form.ins_payout_schedule.reduce((s, p) => s + (p.annual_amount || 0) * (p.years || 0), 0)) }}</strong> CNY
            </div>
          </div>
        </div>

        <!-- Notes -->
        <div class="form-group">
          <label class="form-label">备注</label>
          <textarea v-model="form.notes" rows="2" class="form-input" style="resize:vertical"></textarea>
        </div>

        <!-- Exclude from total -->
        <div class="form-group" style="display:flex;align-items:center;gap:8px">
          <input v-model="form.exclude_from_total" type="checkbox" id="exclude_from_total" />
          <label for="exclude_from_total" class="form-label" style="margin:0">不计入资产总额</label>
        </div>

        <!-- Holdings: for investment -->
        <div v-if="form.category === 'investment'" class="modal-holdings">
          <h4 style="margin:0 0 12px">持仓编辑</h4>
          <div v-for="(fh, i) in formHoldings" :key="i" class="holding-edit-block">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Ticker</label>
                <input v-model="fh.ticker" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label">名称</label>
                <input v-model="fh.name" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">股数</label>
                <input v-model.number="fh.shares" type="number" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label">币种</label>
                <select v-model="fh.currency" class="form-select">
                  <option v-for="c in currencyOptions" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">现价</label>
                <input v-model.number="fh.current_price" type="number" step="0.01" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label">均价</label>
                <input v-model.number="fh.avg_cost_price" type="number" step="0.01" class="form-input" />
              </div>
            </div>
          </div>
          <button class="btn-link" @click="formHoldings.push({ id: 'h_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8), ticker: '', name: '', shares: 0, current_price: 0, avg_cost_price: 0, currency: 'CNY' })">+ 添加持仓</button>
        </div>

        <div class="modal-actions">
          <button class="btn btn-ghost" @click="editing=null">取消</button>
          <button class="btn btn-primary" @click="saveForm">保存</button>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated } from 'vue'
import api from '../api'
import draggable from 'vuedraggable'
import { useScreenshot } from '../composables/useScreenshot'
import { useCurrencies } from '../composables/useCurrencies'
import { formatMoney, categoryLabel } from '../composables/useFormatters'
import { useAccountsStore } from '../stores/accounts'
import { useDashboardStore } from '../stores/dashboard'
import { useStockTrackerStore } from '../stores/stockTracker'

const accountsStore = useAccountsStore()
const dashboardStore = useDashboardStore()
const trackerStore = useStockTrackerStore()
const pageLoading = ref(true)
const { rates: exchangeRates, currencyOptions, fetchRates: fetchCurrencyRates, getRateToCny } = useCurrencies()
const ratesLoading = ref(false)
const pricesLoading = ref(false)
const accountsContent = ref(null)
const { screenshotLoading, screenshot } = useScreenshot(accountsContent, '账户总览')

const editing = ref(null)
const collapsedCards = ref(new Set())
const formHoldings = ref([])
const existingHoldingIds = ref(new Set())
const form = ref({ name: '', category: 'cash', institution: '', notes: '', balances: [], sub_accounts: [], annual_rate: 0, ins_premium: 0, ins_total_periods: 0, ins_paid_periods: 0, ins_start_year: 0, ins_rate_pct: 0, ins_annual_payout: 0, ins_payout_schedule: [], ins_start_date: '', ins_birth_date: '', ins_end_date: '', exclude_from_total: false })

const categories = ['cash', 'investment', 'future_cash', 'insurance']

// Reactive category lists for draggable (must be writable arrays)
const categoryLists = {}
for (const cat of ['cash', 'investment', 'future_cash', 'insurance']) {
  categoryLists[cat] = ref([])
}

const syncCategoryLists = () => {
  const sorted = [...accountsStore.accounts].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
  for (const cat of Object.keys(categoryLists)) {
    categoryLists[cat].value = sorted.filter(a => a.category === cat)
  }
}

const accountsByCategory = (cat) => categoryLists[cat].value

const onDragEnd = async (cat) => {
  const list = accountsByCategory(cat)
  const items = list.map((a, i) => ({ id: a.id, sort_order: i }))
  try {
    await api.reorderAccounts(items)
    accountsStore.invalidateAll()
    dashboardStore.invalidateAll()
    list.forEach((a, i) => a.sort_order = i)
  } catch (e) {
    console.error('排序保存失败', e)
  }
}

const toggleCard = (id) => {
  const s = new Set(collapsedCards.value)
  if (s.has(id)) s.delete(id); else s.add(id)
  collapsedCards.value = s
}

const cashTotalCny = (acct) => {
  return (acct.balances || []).reduce((s, b) => s + b.amount * (rateToCny(b.currency) || 1), 0)
}

const futureCashTotalCny = (acct) => {
  if (acct.sub_accounts && acct.sub_accounts.length) return acct.sub_accounts.reduce((s, sa) => s + sa.amount, 0)
  return (acct.balances || []).reduce((s, b) => s + b.amount * (rateToCny(b.currency) || 1), 0)
}

const accountHoldings = (accountId) => accountsStore.holdingsByAccount(accountId)

const rateToCny = (currency) => getRateToCny(currency)

// Holdings total in CNY
const holdingsTotalCny = (accountId) => {
  return accountHoldings(accountId).reduce((sum, h) => {
    const mv = h.shares * h.current_price
    const rate = rateToCny(h.currency) || 1
    return sum + mv * rate
  }, 0)
}

// Investment total: holdings value + balance
const investmentTotalCny = (acct) => {
  let total = holdingsTotalCny(acct.id)
  for (const b of acct.balances || []) {
    const rate = rateToCny(b.currency) || 1
    total += b.amount * rate
  }
  return total
}

// Cash (活期) interest calculations — per-balance rate
const calcBalanceDailyInterest = (b) => {
  if (!b.annual_rate || b.annual_rate <= 0) return 0
  const rate = rateToCny(b.currency) || 1
  return b.amount * rate * b.annual_rate / 365
}

const calcBalanceYearlyInterest = (b) => {
  if (!b.annual_rate || b.annual_rate <= 0) return 0
  const rate = rateToCny(b.currency) || 1
  return b.amount * rate * b.annual_rate
}

const hasCashInterest = (acct) => {
  return acct.balances && acct.balances.some(b => b.annual_rate > 0)
}

const calcTotalYearlyInterest = (acct) => {
  if (!acct.balances) return 0
  return acct.balances.reduce((sum, b) => sum + calcBalanceYearlyInterest(b), 0)
}

const formTotalDailyInterest = () => {
  if (!form.value.balances) return 0
  return form.value.balances.reduce((sum, b) => {
    const rate = rateToCny(b.currency) || 1
    return sum + b.amount * rate * ((b.annual_rate_pct || 0) / 100) / 365
  }, 0)
}

// Insurance helpers
const hasInsDetails = (acct) => {
  return acct.ins_premium > 0 || acct.ins_total_periods > 0 || acct.ins_start_year > 0 || acct.ins_rate > 0 || acct.ins_annual_payout > 0 || (acct.ins_payout_schedule && acct.ins_payout_schedule.length > 0) || acct.ins_start_date || acct.ins_birth_date || acct.ins_end_date
}

// 到期后每年领取：手动填写优先，否则按利率计算 = 总保费 * 年利率
const calcInsAnnualPayout = (acct) => {
  if (acct.ins_annual_payout > 0) return acct.ins_annual_payout
  const totalPremium = (acct.ins_total_periods || 0) * (acct.ins_premium || 0)
  if (acct.ins_rate > 0 && totalPremium > 0) return totalPremium * acct.ins_rate
  return 0
}

const calcFormInsAnnualPayout = () => {
  if (form.value.ins_annual_payout > 0) return form.value.ins_annual_payout
  const totalPremium = (form.value.ins_total_periods || 0) * (form.value.ins_premium || 0)
  const rate = (form.value.ins_rate_pct || 0) / 100
  if (rate > 0 && totalPremium > 0) return totalPremium * rate
  return 0
}

// 计算保险年限：保单终止日期 - 保险开始日期
const calcInsYears = (acct) => {
  if (!acct.ins_start_date || !acct.ins_end_date) return ''
  const start = new Date(acct.ins_start_date)
  const end = new Date(acct.ins_end_date)
  const diffMs = end - start
  const diffYears = diffMs / (365.25 * 24 * 60 * 60 * 1000)
  return Math.round(diffYears)
}

const calcFormInsYears = () => {
  if (!form.value.ins_start_date || !form.value.ins_end_date) return ''
  const start = new Date(form.value.ins_start_date)
  const end = new Date(form.value.ins_end_date)
  const diffMs = end - start
  const diffYears = diffMs / (365.25 * 24 * 60 * 60 * 1000)
  return Math.round(diffYears)
}

const onCategoryChange = () => {
  if (form.value.category === 'future_cash') {
    if (!form.value.sub_accounts.length) {
      form.value.sub_accounts = [{ label: '', amount: 0 }]
    }
    form.value.balances = []
  } else {
    if (!form.value.balances.length) {
      form.value.balances = [{ currency: 'CNY', amount: 0, annual_rate_pct: 0 }]
    }
    form.value.sub_accounts = []
  }
}

const newAccount = () => {
  editing.value = 'new'
  form.value = { name: '', category: 'cash', institution: '', notes: '', balances: [{ currency: 'CNY', amount: 0, annual_rate_pct: 0 }], sub_accounts: [], ins_premium: 0, ins_total_periods: 0, ins_paid_periods: 0, ins_start_year: 0, ins_rate_pct: 0, ins_annual_payout: 0, ins_payout_schedule: [], ins_start_date: '', ins_birth_date: '', ins_end_date: '' }
  formHoldings.value = []
  existingHoldingIds.value = new Set()
}

const editAccount = (acct) => {
  editing.value = acct.id
  form.value = {
    name: acct.name,
    category: acct.category,
    institution: acct.institution || '',
    notes: acct.notes,
    balances: (acct.balances || []).map(b => ({
      ...b,
      annual_rate_pct: (b.annual_rate || 0) * 100,
    })),
    sub_accounts: JSON.parse(JSON.stringify(acct.sub_accounts || [])),
    ins_premium: acct.ins_premium || 0,
    ins_total_periods: acct.ins_total_periods || 0,
    ins_paid_periods: acct.ins_paid_periods || 0,
    ins_start_year: acct.ins_start_year || 0,
    ins_rate_pct: (acct.ins_rate || 0) * 100,
    ins_annual_payout: acct.ins_annual_payout || 0,
    ins_payout_schedule: JSON.parse(JSON.stringify(acct.ins_payout_schedule || [])),
    ins_start_date: acct.ins_start_date || '',
    ins_birth_date: acct.ins_birth_date || '',
    ins_end_date: acct.ins_end_date || '',
    exclude_from_total: acct.exclude_from_total || false,
  }
  formHoldings.value = accountHoldings(acct.id).map(h => ({
    id: h.id, ticker: h.ticker, name: h.name, shares: h.shares,
    current_price: h.current_price, avg_cost_price: h.avg_cost_price,
    currency: h.currency,
  }))
  existingHoldingIds.value = new Set(formHoldings.value.map(h => h.id))
}

const prepareBalances = () => form.value.balances.map(b => ({
  currency: b.currency,
  amount: b.amount,
  annual_rate: (b.annual_rate_pct || 0) / 100,
}))

const saveForm = async () => {
  const balances = prepareBalances()
  const payload = {
    name: form.value.name, category: form.value.category, institution: form.value.institution,
    notes: form.value.notes, balances, sub_accounts: form.value.sub_accounts, annual_rate: 0,
    ins_premium: form.value.ins_premium || 0, ins_total_periods: form.value.ins_total_periods || 0,
    ins_paid_periods: form.value.ins_paid_periods || 0, ins_start_year: form.value.ins_start_year || 0,
    ins_rate: (form.value.ins_rate_pct || 0) / 100, ins_annual_payout: form.value.ins_annual_payout || 0,
    ins_payout_schedule: (form.value.ins_payout_schedule || []).filter(p => p.label),
    ins_start_date: form.value.ins_start_date || '',
    ins_birth_date: form.value.ins_birth_date || '',
    ins_end_date: form.value.ins_end_date || '',
    exclude_from_total: form.value.exclude_from_total || false,
  }
  if (editing.value === 'new') {
    const id = 'acct_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8)
    await api.createAccount({ id, ...payload })
    // Create holdings for new account
    for (const fh of formHoldings.value) {
      if (fh.ticker) {
        await api.createHolding({ ...fh, account_id: id })
      }
    }
  } else {
    await api.updateAccount(editing.value, payload)
    // Create or update holdings
    for (const fh of formHoldings.value) {
      if (!fh.ticker) continue
      if (existingHoldingIds.value.has(fh.id)) {
        await api.updateHolding(fh.id, {
          ticker: fh.ticker, name: fh.name, shares: fh.shares,
          current_price: fh.current_price, avg_cost_price: fh.avg_cost_price,
          currency: fh.currency,
        })
      } else {
        await api.createHolding({ ...fh, account_id: editing.value })
      }
    }
  }
  editing.value = null
  accountsStore.invalidateAll()
  dashboardStore.invalidateAll()
  await refreshData()
}

const deleteAcct = async (id) => {
  if (!confirm('确认删除？')) return
  await api.deleteAccount(id)
  accountsStore.invalidateAll()
  dashboardStore.invalidateAll()
  await refreshData()
}

const toggleExcludeFromTotal = async (acct) => {
  const newVal = !acct.exclude_from_total
  await api.updateAccount(acct.id, { exclude_from_total: newVal })
  accountsStore.invalidateAll()
  dashboardStore.invalidateAll()
  acct.exclude_from_total = newVal
}

const refreshData = async () => {
  await Promise.all([
    accountsStore.fetchAll(),
    fetchCurrencyRates(),
  ])
  syncCategoryLists()
}

const forceRefreshRates = async () => {
  ratesLoading.value = true
  try {
    await api.refreshExchangeRates()
    await fetchCurrencyRates()
  } finally {
    ratesLoading.value = false
  }
}

const refreshPrices = async () => {
  pricesLoading.value = true
  try {
    const result = await api.refreshHoldingPrices()
    if (result.errors?.length) {
      console.warn('部分股价刷新失败:', result.errors)
    }
    // Reload holdings to reflect updated prices
    accountsStore.invalidateHoldings()
    await accountsStore.fetchHoldings(true)
    trackerStore.invalidateAll()
    dashboardStore.invalidateAll()
  } finally {
    pricesLoading.value = false
  }
}

onMounted(async () => {
  await refreshData()
  pageLoading.value = false
  // Auto-refresh stock prices on page load
  if (accountsStore.holdings.length) {
    refreshPrices()
  }
})

// Refresh data when re-activated from keep-alive cache (stale-while-revalidate)
onActivated(() => {
  refreshData()
})
</script>

<style scoped>
.drag-handle {
  position: absolute; top: 14px; left: 12px; z-index: 1;
  cursor: grab; font-size: 14px; color: var(--text-muted); opacity: 0;
  transition: opacity .2s;
}
.account-card:hover .drag-handle { opacity: 1; }
.drag-handle:active { cursor: grabbing; }
.sortable-ghost { opacity: .4; }
.sortable-chosen { box-shadow: var(--shadow-lg); }
.account-card { position: relative; }
.account-card::before {
  content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%;
  border-radius: 3px 0 0 3px;
}
.account-card.cat-cash::before { background: #2e7d32; }
.account-card.cat-investment::before { background: var(--vermillion); }
.account-card.cat-insurance::before { background: #e65100; }
.account-card.cat-future_cash::before { background: var(--gold); }
.acct-toggle {
  position: absolute; top: 14px; right: 14px; z-index: 1;
}
.acct-header {
  display: flex; flex-direction: column; align-items: flex-start;
  gap: 4px; margin-bottom: 10px; padding-right: 48px;
}
.acct-name { font-family: var(--font-display); font-size: 16px; font-weight: 600; }
.acct-inst { font-size: 12px; color: var(--text-muted); }
.card-arrow {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 4px;
  font-size: 11px; color: var(--text-muted);
  transition: all .2s;
}
.acct-header:hover .card-arrow { color: var(--vermillion); }
.toggle-label { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; user-select: none; }
.toggle-track { width: 32px; height: 18px; border-radius: 9px; background: var(--border, #ddd); position: relative; transition: background .25s; }
.toggle-label.active .toggle-track { background: var(--gold); }
.toggle-thumb { position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: #fff; transition: transform .25s; box-shadow: 0 1px 2px rgba(0,0,0,.15); }
.toggle-label.active .toggle-thumb { transform: translateX(14px); }
.toggle-text { font-size: 11px; color: var(--text-muted); letter-spacing: .02em; }
.toggle-label.active .toggle-text { color: var(--gold); }
.balance-row { margin: 3px 0; }
.balance-amount { font-size: 22px; font-weight: 700; letter-spacing: -.02em; }
.balance-currency { font-size: 12px; color: var(--text-muted); margin-left: 4px; }
.acct-notes { font-size: 12px; color: var(--text-secondary); margin-top: 8px; line-height: 1.5; }
.acct-actions { margin-top: 12px; display: flex; gap: 6px; }

/* Sub accounts (future_cash) */
.sub-accounts { margin-top: 8px; padding: 8px 10px; background: var(--bg-secondary, #f5f5f5); border-radius: 6px; }
.sub-header { font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; letter-spacing: .04em; text-transform: uppercase; }
.sub-account-row { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 13px; }
.sub-account-row .sub-label { color: var(--text-secondary); }
.sub-account-row .sub-amount { font-weight: 500; }
.sub-total-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0 0; margin-top: 4px; border-top: 1px dashed var(--border, #ddd); font-size: 13px; font-weight: 600; }

/* Holdings (investment) */
.holdings-detail { margin-top: 8px; padding: 8px 10px; background: var(--bg-secondary, #f5f5f5); border-radius: 6px; }
.holdings-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.holdings-title { font-size: 12px; color: var(--text-muted); font-weight: 500; }
.refresh-prices-btn { font-size: 11px !important; padding: 2px 8px !important; display: inline-flex; align-items: center; gap: 4px; }
.refresh-icon { display: inline-block; font-size: 13px; transition: transform 0.3s; }
.refresh-icon.spinning { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.holding-row { padding: 6px 0; border-bottom: 1px solid var(--border, #eee); }
.holding-row:last-of-type { border-bottom: none; }
.holding-main { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.holding-ticker { font-weight: 700; font-size: 14px; }
.holding-shares { font-size: 12px; color: var(--text-secondary); }
.holding-currency { font-size: 11px; color: var(--text-muted); background: var(--bg-tertiary, #eee); padding: 1px 6px; border-radius: 3px; }
.holding-price { font-size: 12px; color: var(--text-secondary); display: flex; gap: 12px; margin-bottom: 2px; }
.holding-value { font-size: 12px; display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.holding-cny { color: var(--text-secondary); font-size: 12px; }
.holding-rate { font-size: 11px; color: var(--text-muted); }
.holdings-summary {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 0 0; margin-top: 4px; border-top: 1px dashed var(--border, #ddd);
  font-size: 13px; font-weight: 600;
}
.holdings-total-value { color: var(--vermillion); }

/* Cash rate section */
.cash-rate-section { margin-top: 8px; padding: 8px 10px; background: var(--bg-secondary, #f5f5f5); border-radius: 6px; }
.cash-rate-row { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 13px; }
.cash-rate-label { color: var(--text-secondary); }
.cash-rate-value { color: var(--vermillion); font-weight: 500; background: var(--vermillion-soft); padding: 1px 8px; border-radius: 10px; font-size: 13px; }
.cash-daily-row { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 13px; }
.cash-daily-label { color: var(--text-secondary); }
.cash-daily-value { font-weight: 600; color: var(--gold); }
.cash-yearly-row { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 13px; }
.cash-yearly-label { color: var(--text-secondary); }
.cash-yearly-value { font-weight: 500; }
.cash-form-preview { margin-top: 6px; font-size: 12px; color: var(--text-secondary); }
.cash-form-preview strong { color: var(--gold); }
.cash-balance-block { margin-bottom: 4px; }
.cash-balance-block:not(:last-child) { padding-bottom: 6px; border-bottom: 1px dashed var(--border, #eee); }
.cash-balance-block .cash-rate-section { margin-top: 4px; }
.cash-total-interest { display: flex; justify-content: space-between; align-items: center; padding: 6px 0 0; margin-top: 6px; border-top: 1px dashed var(--border, #ddd); font-size: 13px; font-weight: 600; }

/* Insurance detail section */
.ins-detail-section { margin-top: 8px; padding: 8px 10px; background: var(--bg-secondary, #f5f5f5); border-radius: 6px; }
.ins-detail-row { display: flex; justify-content: space-between; align-items: center; padding: 3px 0; font-size: 13px; gap: 8px; }
.ins-detail-label { color: var(--text-secondary); white-space: nowrap; }
.ins-detail-value { font-weight: 500; text-align: right; }
.ins-payout-value { color: var(--gold); }
.ins-rate-value { color: var(--vermillion); font-weight: 500; background: var(--vermillion-soft); padding: 1px 8px; border-radius: 10px; font-size: 13px; }
.ins-payout-row { padding: 6px 0 0; margin-top: 4px; border-top: 1px dashed var(--border, #ddd); font-weight: 600; }
.ins-schedule-title { font-size: 11px; font-weight: 600; color: var(--text-muted); margin-top: 6px; padding-top: 6px; border-top: 1px dashed var(--border, #ddd); letter-spacing: .04em; }
.ins-schedule-row { display: flex; justify-content: space-between; align-items: center; padding: 2px 0; font-size: 13px; }
.ins-schedule-label { color: var(--text-secondary); min-width: 80px; }
.ins-schedule-amount { font-weight: 500; text-align: right; }
.ins-schedule-total { display: flex; justify-content: space-between; align-items: center; padding: 5px 0 0; margin-top: 4px; border-top: 1px dashed var(--border, #ddd); font-size: 13px; font-weight: 600; }
.ins-progress-bar { flex: 1; max-width: 120px; height: 6px; background: var(--border, #ddd); border-radius: 3px; overflow: hidden; }
.ins-progress-fill { height: 100%; background: var(--gold); border-radius: 3px; transition: width .3s; }
.ins-form-section { margin-top: 4px; }
.ins-form-section .form-row { display: flex; gap: 12px; }
.ins-form-section .form-row .form-group { flex: 1; }

/* Modal extras */
.modal-holdings { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border, #ddd); }
.holding-edit-block { padding: 10px; background: var(--bg-secondary, #f5f5f5); border-radius: 6px; margin-bottom: 10px; }
.holding-edit-block .form-row { display: flex; gap: 12px; }
.holding-edit-block .form-row .form-group { flex: 1; }
.balance-form-row { display: flex; gap: 8px; margin: 8px 0; align-items: center; }

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
