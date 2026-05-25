import { defineStore } from 'pinia'
import api from '../api'
import { useAccountsStore } from './accounts'
import { useDashboardStore } from './dashboard'

const MAX_AGE = 5 * 60 * 1000

export const useStockTrackerStore = defineStore('stockTracker', {
  state: () => ({
    summary: { total_pnl_cny: 0, today_change_cny: 0, holding_count: 0, watchlist_count: 0, exchange_rates: [] },
    stocks: [],
    trend: [],
    _fetchedAt: 0,
    _inflight: null,
    loading: false,
    initialLoading: true,
    refreshingPrices: false,
  }),

  actions: {
    async fetchOverview(forceRefresh = false) {
      if (!forceRefresh && this._fetchedAt && Date.now() - this._fetchedAt < MAX_AGE) {
        return
      }
      if (this._inflight) return this._inflight
      this.loading = true
      this._inflight = api.getStockTrackerOverview().then(data => {
        this.summary = data.summary
        this.stocks = data.stocks
        this.trend = data.trend
        this._fetchedAt = Date.now()
        this._inflight = null
        this.loading = false
        return data
      }).catch(e => {
        this._inflight = null
        this.loading = false
        throw e
      })
      return this._inflight
    },

    async refreshLivePrices() {
      this.refreshingPrices = true
      try {
        const data = await api.refreshTrackerPrices()
        this.invalidateAll()
        const accountsStore = useAccountsStore()
        accountsStore.invalidateAll()
        const dashboardStore = useDashboardStore()
        dashboardStore.invalidateAll()
        if (data.summary) this.summary = data.summary
        if (data.stocks) this.stocks = data.stocks
      } catch (e) {
        console.error('Failed to refresh live prices:', e)
      } finally {
        this.refreshingPrices = false
      }
    },

    async addWatchlist(ticker, name) {
      const id = 'wl_' + ticker.toLowerCase().replace(/[^a-z0-9]/g, '_')
      await api.addWatchlistItem({ id, ticker, name })
      this.invalidateAll()
      await this.fetchOverview(true)
    },

    async removeWatchlist(ticker) {
      const id = 'wl_' + ticker.toLowerCase().replace(/[^a-z0-9]/g, '_')
      await api.deleteWatchlistItem(id)
      this.invalidateAll()
      await this.fetchOverview(true)
    },

    async saveEditStock(stock, updates) {
      if (stock.source === 'watchlist') {
        const id = 'wl_' + stock.ticker.toLowerCase().replace(/[^a-z0-9]/g, '_')
        if (Object.keys(updates).length) {
          await api.updateWatchlistItem(id, updates)
        }
      } else {
        if (Object.keys(updates).length) {
          await api.updateHolding(stock.holding_id, updates)
        }
      }
      this.invalidateAll()
      const accountsStore = useAccountsStore()
      accountsStore.invalidateAll()
      const dashboardStore = useDashboardStore()
      dashboardStore.invalidateAll()
      await this.fetchOverview(true)
    },

    async saveSnapshot() {
      await api.savePriceSnapshot()
      this.invalidateAll()
      await this.fetchOverview(true)
    },

    invalidateAll() {
      this._fetchedAt = 0
    },

    resetState() {
      this.summary = { total_pnl_cny: 0, today_change_cny: 0, holding_count: 0, watchlist_count: 0, exchange_rates: [] }
      this.stocks = []
      this.trend = []
      this._fetchedAt = 0
      this._inflight = null
      this.loading = false
      this.initialLoading = true
      this.refreshingPrices = false
    },
  },
})
