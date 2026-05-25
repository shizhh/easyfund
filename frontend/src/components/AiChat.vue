<template>
  <!-- Floating trigger button -->
  <button v-if="!isOpen" class="ai-trigger" @click="toggleOpen" title="AI 助手">
    <span class="ai-trigger-icon">✦</span>
  </button>

  <!-- Chat panel -->
  <div v-if="isOpen" class="ai-panel">
    <!-- Header -->
    <div class="ai-header">
      <div class="ai-header-left">
        <select
          v-if="conversations.length > 0"
          class="ai-conv-select"
          :value="currentConversationId"
          @change="selectConversation($event.target.value)"
        >
          <option value="">选择对话...</option>
          <option v-for="c in conversations" :key="c.id" :value="c.id">
            {{ c.title }}
          </option>
        </select>
        <span v-else class="ai-title">AI 助手</span>
      </div>
      <div class="ai-header-actions">
        <button class="ai-btn-icon" @click="handleNewConversation" title="新对话">+</button>
        <button class="ai-btn-icon" @click="showSettings = !showSettings" title="设置">⚙</button>
        <button class="ai-btn-icon" @click="toggleOpen" title="关闭">✕</button>
      </div>
    </div>

    <!-- Settings panel -->
    <div v-if="showSettings" class="ai-settings">
      <div class="ai-settings-title">AI 配置</div>
      <div class="form-group">
        <label class="form-label">Base URL</label>
        <input v-model="settingsForm.base_url" class="form-input" placeholder="https://api.openai.com/v1" />
      </div>
      <div class="form-group">
        <label class="form-label">API Key</label>
        <input v-model="settingsForm.api_key" class="form-input" type="password" placeholder="sk-..." />
      </div>
      <div class="form-group">
        <label class="form-label">Model</label>
        <input v-model="settingsForm.model" class="form-input" placeholder="gpt-4o-mini" />
      </div>
      <button class="btn btn-primary btn-sm" @click="handleSaveSettings" style="width:100%">保存配置</button>
    </div>

    <!-- Not configured hint -->
    <div v-if="!isConfigured && !showSettings" class="ai-empty">
      <p>AI 助手尚未配置</p>
      <button class="btn btn-primary btn-sm" @click="showSettings = true">前往配置</button>
    </div>

    <!-- Messages -->
    <div v-else class="ai-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="ai-empty">
        <p>试试问我：</p>
        <div class="ai-suggestions">
          <button class="ai-suggestion" @click="sendMessage('我的总资产是多少？')">我的总资产是多少？</button>
          <button class="ai-suggestion" @click="sendMessage('BIDU 今天涨了多少？')">BIDU 今天涨了多少？</button>
          <button class="ai-suggestion" @click="sendMessage('我的持仓有哪些？')">我的持仓有哪些？</button>
          <button class="ai-suggestion" @click="sendMessage('帮我刷新一下汇率')">帮我刷新一下汇率</button>
        </div>
      </div>
      <div v-for="(msg, i) in messages" :key="i" class="ai-msg" :class="`ai-msg-${msg.role}`">
        <div class="ai-msg-role">{{ msg.role === 'user' ? '你' : 'AI' }}</div>
        <div class="ai-msg-content" v-html="renderMarkdown(msg.content)"></div>
        <!-- Tool call indicator -->
        <div v-if="msg.tool_calls && msg.tool_calls.length" class="ai-tool-calls">
          <div v-for="tc in msg.tool_calls" :key="tc.name" class="ai-tool-tag">
            ⟳ {{ getToolDisplayName(tc.name) }}
          </div>
        </div>
      </div>
      <!-- Tool call status -->
      <div v-if="toolCallStatus" class="ai-tool-status">
        <span class="ai-tool-spinner"></span>
        正在{{ getToolDisplayName(toolCallStatus.name) }}...
      </div>
      <!-- Typing indicator -->
      <div v-if="isStreaming && !streamingContent && !toolCallStatus" class="ai-typing">
        <span></span><span></span><span></span>
      </div>
    </div>

    <!-- Input area -->
    <div class="ai-input-area">
      <div class="ai-input-wrap">
        <textarea
          v-model="inputText"
          class="ai-input"
          placeholder="输入问题..."
          rows="1"
          @keydown.enter.exact.prevent="handleSend"
          @input="autoResize"
          ref="inputEl"
        ></textarea>
        <button class="ai-send-btn" @click="handleSend" :disabled="!inputText.trim() || isStreaming">
          ↑
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'
import { useAiChat } from '../composables/useAiChat'

const {
  conversations,
  currentConversationId,
  messages,
  isStreaming,
  streamingContent,
  toolCallStatus,
  config,
  isConfigured,
  isOpen,
  loadConfig,
  saveConfig,
  loadConversations,
  createConversation,
  selectConversation,
  sendMessage: doSendMessage,
  toggleOpen,
} = useAiChat()

const inputText = ref('')
const showSettings = ref(false)
const settingsForm = ref({ base_url: '', api_key: '', model: '' })
const messagesContainer = ref(null)
const inputEl = ref(null)

onMounted(() => {
  loadConfig()
  loadConversations()
})

watch(() => config.value, (cfg) => {
  settingsForm.value = {
    base_url: cfg.base_url || '',
    api_key: '',  // Don't populate masked key
    model: cfg.model || '',
  }
}, { immediate: true })

watch(() => messages.value.length, async () => {
  await nextTick()
  scrollToBottom()
})

watch(isStreaming, async () => {
  await nextTick()
  scrollToBottom()
})

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || isStreaming.value) return
  inputText.value = ''
  if (inputEl.value) {
    inputEl.value.style.height = 'auto'
  }
  await doSendMessage(text)
}

async function handleNewConversation() {
  await createConversation()
}

async function handleSaveSettings() {
  const form = { ...settingsForm.value }
  // Only include api_key if user actually typed something
  if (!form.api_key) delete form.api_key
  await saveConfig(form)
  showSettings.value = false
}

function getToolDisplayName(name) {
  const names = {
    get_dashboard_overview: '查询资产总览',
    get_asset_trend: '查询资产趋势',
    list_accounts: '查询账户列表',
    get_account: '查询账户详情',
    list_holdings: '查询持仓列表',
    get_holding_pnl: '查询持仓盈亏',
    get_stock_quote: '查询股票报价',
    list_transactions: '查询交易记录',
    get_annual_pnl: '查询年度盈亏',
    get_fund_flow_analysis: '分析资金流',
    get_exchange_rates: '查询汇率',
    get_stock_tracker_overview: '查询股价追踪',
    list_watchlist: '查询关注列表',
    add_watchlist_item: '添加关注',
    remove_watchlist_item: '移除关注',
    refresh_stock_prices: '刷新股价',
    refresh_exchange_rates: '刷新汇率',
    update_exchange_rate: '更新汇率',
  }
  return names[name] || name
}

function renderMarkdown(text) {
  if (!text) return ''
  let html = text
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Line breaks
    .replace(/\n/g, '<br>')
  return html
}
</script>

<style scoped>
/* Trigger button */
.ai-trigger {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--vermillion);
  color: #fff;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(197,61,67,.3);
  z-index: 1000;
  transition: all var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
}
.ai-trigger:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(197,61,67,.4);
}
.ai-trigger-icon {
  font-size: 22px;
}

/* Chat panel */
.ai-panel {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 420px;
  height: 560px;
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--paper-line);
  display: flex;
  flex-direction: column;
  z-index: 1001;
  animation: slideUp .25s cubic-bezier(.4,0,.2,1);
  overflow: hidden;
}

/* Header */
.ai-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--paper-line);
  background: var(--paper);
  flex-shrink: 0;
}
.ai-header-left {
  flex: 1;
  min-width: 0;
}
.ai-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}
.ai-conv-select {
  width: 100%;
  padding: 4px 8px;
  border: 1px solid var(--paper-line);
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  color: var(--text);
  font-family: var(--font-body);
  outline: none;
  cursor: pointer;
}
.ai-conv-select:focus {
  border-color: var(--vermillion);
}
.ai-header-actions {
  display: flex;
  gap: 4px;
  margin-left: 8px;
}
.ai-btn-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
}
.ai-btn-icon:hover {
  background: var(--paper-warm);
  color: var(--text);
}

/* Settings */
.ai-settings {
  padding: 16px;
  border-bottom: 1px solid var(--paper-line);
  background: var(--paper);
  flex-shrink: 0;
}
.ai-settings-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 10px;
}

/* Messages */
.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  color: var(--text-muted);
  font-size: 13px;
  gap: 12px;
}

.ai-suggestions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}
.ai-suggestion {
  text-align: left;
  padding: 8px 12px;
  border: 1px solid var(--paper-line);
  border-radius: var(--radius);
  background: var(--paper);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition);
  font-family: var(--font-body);
}
.ai-suggestion:hover {
  background: var(--paper-warm);
  border-color: var(--vermillion);
  color: var(--text);
}

/* Message bubbles */
.ai-msg {
  max-width: 88%;
}
.ai-msg-user {
  align-self: flex-end;
}
.ai-msg-assistant {
  align-self: flex-start;
}
.ai-msg-role {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
  font-weight: 500;
}
.ai-msg-user .ai-msg-role {
  text-align: right;
}
.ai-msg-content {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-word;
}
.ai-msg-user .ai-msg-content {
  background: var(--ink);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.ai-msg-assistant .ai-msg-content {
  background: var(--paper-warm);
  color: var(--text);
  border-bottom-left-radius: 4px;
}
.ai-msg-content :deep(code) {
  background: rgba(0,0,0,.06);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
}
.ai-msg-content :deep(strong) {
  font-weight: 600;
  color: var(--ink);
}

/* Tool calls */
.ai-tool-calls {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.ai-tool-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--gold-soft);
  color: var(--gold);
}

/* Tool call status */
.ai-tool-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--gold);
  padding: 4px 0;
}
.ai-tool-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--paper-line);
  border-top-color: var(--gold);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Typing indicator */
.ai-typing {
  display: flex;
  gap: 4px;
  padding: 10px 14px;
}
.ai-typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: typing 1.4s ease-in-out infinite;
}
.ai-typing span:nth-child(2) { animation-delay: .2s; }
.ai-typing span:nth-child(3) { animation-delay: .4s; }
@keyframes typing {
  0%, 60%, 100% { opacity: .3; transform: scale(.8); }
  30% { opacity: 1; transform: scale(1); }
}

/* Input area */
.ai-input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--paper-line);
  background: var(--paper);
  flex-shrink: 0;
}
.ai-input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #fff;
  border: 1px solid var(--paper-line);
  border-radius: 12px;
  padding: 6px 6px 6px 14px;
  transition: border-color var(--transition);
}
.ai-input-wrap:focus-within {
  border-color: var(--vermillion);
  box-shadow: 0 0 0 3px var(--vermillion-soft);
}
.ai-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--text);
  resize: none;
  min-height: 20px;
  max-height: 120px;
  line-height: 1.5;
  background: transparent;
}
.ai-input::placeholder {
  color: var(--text-muted);
}
.ai-send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: var(--vermillion);
  color: #fff;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition);
  flex-shrink: 0;
}
.ai-send-btn:hover:not(:disabled) {
  background: var(--vermillion-hover);
}
.ai-send-btn:disabled {
  opacity: .4;
  cursor: not-allowed;
}

/* Mobile */
@media (max-width: 768px) {
  .ai-panel {
    position: fixed;
    inset: 0;
    width: 100%;
    height: 100%;
    border-radius: 0;
    bottom: 0;
    right: 0;
  }
  .ai-trigger {
    bottom: 80px;
    right: 16px;
  }
}
</style>
