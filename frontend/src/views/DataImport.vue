<template>
  <div>
    <h2>数据导入</h2>

    <!-- Step 1: Upload -->
    <div v-if="step === 1" class="card">
      <h3 style="margin-bottom:16px;">AI 智能导入</h3>
      <p class="import-desc">上传 Excel 文件，AI 将自动分析文件结构并生成列映射，支持任意格式的资产数据表</p>

      <div class="upload-row">
        <input type="file" accept=".xlsx,.xls" @change="onFileChange" ref="fileInput" class="file-input" />
        <button class="btn btn-primary" @click="doAnalyze" :disabled="!selectedFile || analyzing">
          {{ analyzing ? '分析中...' : '开始分析' }}
        </button>
      </div>

      <div v-if="error" class="result-box result-error">
        {{ error }}
        <span v-if="error.includes('AI') && error.includes('配置')" class="link" @click="$router.push('/chat')">前往设置</span>
      </div>
    </div>

    <!-- Step 2: Mapping Editor -->
    <div v-if="step === 2" class="card">
      <h3 style="margin-bottom:8px;">映射配置</h3>
      <p class="import-desc">
        AI 已分析文件结构并生成以下映射，请检查并调整后确认导入
        <span v-if="mapping.confidence < 0.5" class="warn-text">（置信度较低，请仔细核对）</span>
      </p>

      <div v-if="mapping.notes && mapping.notes.length" class="ai-notes">
        <div v-for="note in mapping.notes" :key="note" class="ai-note-item">💡 {{ note }}</div>
      </div>

      <div v-for="(sheet, si) in mapping.sheets" :key="si" class="sheet-section">
        <h4 class="sheet-title">{{ sheet.sheet_name }}
          <span class="target-types">{{ sheet.target_types.join(', ') }}</span>
        </h4>

        <table class="mapping-table">
          <thead>
            <tr>
              <th>列名</th>
              <th>映射字段</th>
              <th>转换规则</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(col, ci) in sheet.column_mappings" :key="ci">
              <td>{{ col.column_header }}</td>
              <td>
                <select v-model="col.target_field" class="field-select">
                  <option value="skip">跳过</option>
                  <optgroup label="Account">
                    <option value="name">name (名称)</option>
                    <option value="category_raw">category_raw (类别原文)</option>
                    <option value="institution">institution (机构)</option>
                    <option value="amount_cny">amount_cny (金额CNY)</option>
                    <option value="amount">amount (金额)</option>
                    <option value="balances">balances (多币种余额)</option>
                    <option value="notes">notes (备注)</option>
                  </optgroup>
                  <optgroup label="Holding">
                    <option value="holding_ticker">ticker (代码)</option>
                    <option value="holding_name">name (名称)</option>
                    <option value="holding_shares">shares (股数)</option>
                    <option value="holding_avg_cost">avg_cost_price (成本价)</option>
                    <option value="holding_current_price">current_price (现价)</option>
                    <option value="holding_currency">currency (币种)</option>
                  </optgroup>
                  <optgroup label="Transaction">
                    <option value="account_name">account_name (账户名)</option>
                    <option value="type">type (类型)</option>
                    <option value="date">date (日期)</option>
                    <option value="amount">amount (金额)</option>
                    <option value="currency">currency (币种)</option>
                    <option value="quantity">quantity (数量)</option>
                    <option value="price">price (价格)</option>
                    <option value="pnl">pnl (盈亏)</option>
                    <option value="notes">notes (备注)</option>
                  </optgroup>
                  <optgroup label="Deposit">
                    <option value="amount">amount (金额)</option>
                    <option value="rate">rate (利率)</option>
                    <option value="start_date">start_date (开始日期)</option>
                    <option value="maturity_date">maturity_date (到期日期)</option>
                    <option value="interest">interest (利息)</option>
                  </optgroup>
                </select>
              </td>
              <td>
                <input v-model="col.transform" class="transform-input" placeholder="无" />
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Cell references -->
        <div v-if="sheet.cell_references.length" class="cell-refs">
          <strong>独立单元格：</strong>
          <span v-for="(cr, cri) in sheet.cell_references" :key="cri" class="cell-ref-item">
            {{ cr.cell_ref }} → {{ cr.purpose }} ({{ cr.target_type }}{{ cr.currency ? '/' + cr.currency : '' }})
          </span>
        </div>

        <!-- Category rules -->
        <div v-if="sheet.category_rules.length" class="cat-rules">
          <strong>类别映射：</strong>
          <span v-for="(cr, cri) in sheet.category_rules" :key="cri" class="cat-rule-item">
            "{{ cr.raw_value }}" → {{ cr.category }}
          </span>
        </div>

        <!-- Skip conditions -->
        <div v-if="sheet.skip_conditions.length" class="skip-conds">
          <strong>跳过条件：</strong>
          <span v-for="(sc, sci) in sheet.skip_conditions" :key="sci" class="skip-cond-item">{{ sc }}</span>
        </div>
      </div>

      <div class="action-row">
        <button class="btn" @click="step = 1">返回</button>
        <button class="btn btn-primary" @click="doConfirm" :disabled="importing">
          {{ importing ? '导入中...' : '确认导入' }}
        </button>
      </div>
    </div>

    <!-- Step 3: Result -->
    <div v-if="step === 3" class="card">
      <h3 style="margin-bottom:16px;">导入结果</h3>
      <div v-if="importResult" class="result-box result-success">
        <strong>导入成功！</strong>
        <div class="result-counts">
          <span v-for="(count, key) in importResult" :key="key" class="result-item">
            {{ importLabels[key] || key }}: {{ count }}
          </span>
        </div>
      </div>
      <div class="action-row" style="margin-top:16px;">
        <button class="btn" @click="reset">再次导入</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import api from '../api'

const step = ref(1)
const selectedFile = ref(null)
const fileInput = ref(null)
const analyzing = ref(false)
const importing = ref(false)
const error = ref('')
const sessionId = ref('')
const mapping = reactive({ sheets: [], confidence: 0, notes: [], detected_language: 'zh' })
const importResult = ref(null)

const importLabels = { accounts: '账户', holdings: '持仓', transactions: '交易', deposits: '存款', rates: '汇率' }

const onFileChange = (e) => {
  selectedFile.value = e.target.files[0]
  error.value = ''
}

const doAnalyze = async () => {
  if (!selectedFile.value) return
  error.value = ''
  analyzing.value = true
  try {
    const result = await api.analyzeExcel(selectedFile.value)
    sessionId.value = result.session_id
    Object.assign(mapping, result.mapping)
    step.value = 2
  } catch (e) {
    error.value = e.message
  } finally {
    analyzing.value = false
  }
}

const doConfirm = async () => {
  importing.value = true
  error.value = ''
  try {
    importResult.value = await api.confirmImport(sessionId.value, mapping)
    step.value = 3
  } catch (e) {
    error.value = e.message
  } finally {
    importing.value = false
  }
}

const reset = () => {
  step.value = 1
  selectedFile.value = null
  sessionId.value = ''
  mapping.sheets = []
  mapping.confidence = 0
  mapping.notes = []
  importResult.value = null
  error.value = ''
}
</script>

<style scoped>
.import-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: 14px; line-height: 1.6; }
.upload-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.file-input { font-size: 14px; font-family: var(--font-body); }
.result-box { margin-top: 16px; padding: 14px 18px; border-radius: var(--radius); font-size: 14px; line-height: 1.6; }
.result-success { background: rgba(46,125,50,.06); border: 1px solid rgba(46,125,50,.15); color: #2e7d32; }
.result-error { background: rgba(197,61,67,.06); border: 1px solid rgba(197,61,67,.15); color: var(--vermillion); }
.result-counts { margin-top: 8px; font-size: 13px; }
.result-item { margin-right: 18px; }
.link { color: var(--primary); cursor: pointer; text-decoration: underline; margin-left: 8px; }
.warn-text { color: #e65100; font-weight: 500; }
.ai-notes { margin-bottom: 16px; padding: 10px 14px; background: rgba(33,150,243,.05); border: 1px solid rgba(33,150,243,.12); border-radius: var(--radius); }
.ai-note-item { font-size: 13px; color: var(--text-secondary); line-height: 1.6; }
.sheet-section { margin-bottom: 20px; padding: 16px; background: var(--bg-secondary, #f8f9fa); border-radius: var(--radius); }
.sheet-title { margin-bottom: 10px; font-size: 15px; }
.target-types { font-size: 12px; color: var(--text-secondary); font-weight: 400; margin-left: 8px; }
.mapping-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.mapping-table th { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--border, #e0e0e0); color: var(--text-secondary); font-weight: 500; }
.mapping-table td { padding: 6px 10px; border-bottom: 1px solid var(--border, #e0e0e0); }
.field-select { font-size: 13px; padding: 3px 6px; border: 1px solid var(--border, #ccc); border-radius: 4px; background: #fff; min-width: 160px; }
.transform-input { font-size: 13px; padding: 3px 6px; border: 1px solid var(--border, #ccc); border-radius: 4px; width: 160px; }
.cell-refs, .cat-rules, .skip-conds { margin-top: 10px; font-size: 13px; line-height: 1.8; }
.cell-refs strong, .cat-rules strong, .skip-conds strong { color: var(--text-secondary); }
.cell-ref-item, .cat-rule-item, .skip-cond-item { margin-right: 12px; }
.action-row { margin-top: 16px; display: flex; gap: 12px; }
</style>
