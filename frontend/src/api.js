const API_BASE = '/api'
const REQUEST_TIMEOUT = 15000 // 15s — prevents infinite loading on unresponsive backend

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  const authToken = localStorage.getItem('easyfund_token')
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, signal: controller.signal }).finally(() => clearTimeout(timer))
  if (res.status === 401 && !path.startsWith('/auth/login')) {
    // Remove stale session for current user
    const currentUser = JSON.parse(localStorage.getItem('easyfund_user') || 'null')
    if (currentUser?.username) {
      const sessions = JSON.parse(localStorage.getItem('easyfund_sessions') || '{}')
      delete sessions[currentUser.username]
      localStorage.setItem('easyfund_sessions', JSON.stringify(sessions))
      // Save expired username so login page can auto-fill it
      localStorage.setItem('easyfund_expired_user', currentUser.username)
    }
    localStorage.removeItem('easyfund_token')
    localStorage.removeItem('easyfund_user')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export default {
  // Auth
  login: (username, password) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }),
  getMe: () => request('/auth/me'),

  // Dashboard
  getOverview: () => request('/dashboard/overview'),
  getTrend: () => request('/dashboard/trend'),
  saveSnapshot: () => request('/dashboard/snapshot', { method: 'POST' }),
  getHoldingsPnl: () => request('/dashboard/holdings-pnl'),
  getDashboardAll: () => request('/dashboard/all'),

  // Accounts
  getAccounts: () => request('/accounts'),
  createAccount: (data) => request('/accounts', { method: 'POST', body: JSON.stringify(data) }),
  updateAccount: (id, data) => request(`/accounts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAccount: (id) => request(`/accounts/${id}`, { method: 'DELETE' }),
  reorderAccounts: (items) => request('/accounts/reorder', { method: 'PUT', body: JSON.stringify(items) }),

  // Holdings
  getHoldings: () => request('/holdings'),
  createHolding: (data) => request('/holdings', { method: 'POST', body: JSON.stringify(data) }),
  updateHolding: (id, data) => request(`/holdings/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteHolding: (id) => request(`/holdings/${id}`, { method: 'DELETE' }),
  getHoldingPnl: (id) => request(`/holdings/${id}/pnl`),
  refreshHoldingPrices: () => request('/holdings/refresh-prices', { method: 'POST' }),

  // Transactions
  getTransactions: (params = '') => request(`/transactions${params}`),
  getAnnualPnl: () => request('/transactions/pnl/annual'),
  createTransaction: (data) => request('/transactions', { method: 'POST', body: JSON.stringify(data) }),
  updateTransaction: (id, data) => request(`/transactions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTransaction: (id) => request(`/transactions/${id}`, { method: 'DELETE' }),

  // Deposits
  getDeposits: () => request('/deposits'),
  createDeposit: (data) => request('/deposits', { method: 'POST', body: JSON.stringify(data) }),
  updateDeposit: (id, data) => request(`/deposits/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteDeposit: (id) => request(`/deposits/${id}`, { method: 'DELETE' }),

  // Market
  getQuote: (ticker) => request(`/market/quote/${ticker}`),
  getQuoteHistory: (ticker, days = 30) => request(`/market/history/${ticker}?days=${days}`),

  // Stock Tracker
  getWatchlist: () => request('/stock-tracker/watchlist'),
  addWatchlistItem: (data) => request('/stock-tracker/watchlist', { method: 'POST', body: JSON.stringify(data) }),
  updateWatchlistItem: (id, data) => request(`/stock-tracker/watchlist/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteWatchlistItem: (id) => request(`/stock-tracker/watchlist/${id}`, { method: 'DELETE' }),
  getStockTrackerOverview: () => request('/stock-tracker/overview'),
  refreshTrackerPrices: () => request('/stock-tracker/refresh-prices'),
  savePriceSnapshot: () => request('/stock-tracker/snapshot', { method: 'POST' }),

  // Fund Flows
  getFundFlows: (params = '') => request(`/fund-flows${params}`),
  createFundFlow: (data) => request('/fund-flows', { method: 'POST', body: JSON.stringify(data) }),
  updateFundFlow: (id, data) => request(`/fund-flows/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteFundFlow: (id) => request(`/fund-flows/${id}`, { method: 'DELETE' }),
  getFundFlowAnalysis: (accountId) => request(`/fund-flows/analysis?account_id=${accountId}`),

  // Exchange rates
  getExchangeRates: () => request('/exchange-rates'),
  updateExchangeRate: (currency, rate) => request(`/exchange-rates?currency=${currency}&rate=${rate}`, { method: 'POST' }),
  refreshExchangeRates: () => request('/exchange-rates/refresh', { method: 'POST' }),

  // Currencies
  getCurrencies: () => request('/currencies'),
  registerCurrency: (currency, rate) => request(`/currencies?currency=${currency}&rate=${rate}`, { method: 'POST' }),
  unregisterCurrency: (currency) => request(`/currencies/${currency}`, { method: 'DELETE' }),

  // Import
  analyzeExcel: async (file) => {
    const authToken = localStorage.getItem('easyfund_token')
    const headers = {}
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`
    }
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/import/analyze`, { method: 'POST', body: form, headers })
    if (res.status === 401) {
      const currentUser = JSON.parse(localStorage.getItem('easyfund_user') || 'null')
      if (currentUser?.username) {
        const sessions = JSON.parse(localStorage.getItem('easyfund_sessions') || '{}')
        delete sessions[currentUser.username]
        localStorage.setItem('easyfund_sessions', JSON.stringify(sessions))
        localStorage.setItem('easyfund_expired_user', currentUser.username)
      }
      localStorage.removeItem('easyfund_token')
      localStorage.removeItem('easyfund_user')
      window.location.href = '/login'
      throw new Error('Unauthorized')
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || 'Analysis failed')
    }
    return res.json()
  },
  confirmImport: (sessionId, mapping) => request('/import/confirm', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, mapping }),
  }),

  // AI Chat
  getAiConfig: () => request('/chat/config'),
  updateAiConfig: (data) => request('/chat/config', { method: 'PUT', body: JSON.stringify(data) }),
  getConversations: () => request('/chat/conversations'),
  createConversation: (title = '新对话') => request('/chat/conversations', { method: 'POST', body: JSON.stringify({ title }) }),
  getConversation: (id) => request(`/chat/conversations/${id}`),
  deleteConversation: (id) => request(`/chat/conversations/${id}`, { method: 'DELETE' }),
}
