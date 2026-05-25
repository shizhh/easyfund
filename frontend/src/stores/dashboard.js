import { defineStore } from 'pinia'
import api from '../api'
import { useAccountsStore } from './accounts'
import { useCurrencies } from '../composables/useCurrencies'
import { useStockTrackerStore } from './stockTracker'

const MAX_AGE = 5 * 60 * 1000

const MODULES = ['overview', 'annualPnl', 'trendData', 'holdingsPnl', 'ratesData']

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    overview: {},
    annualPnl: {},
    trendData: [],
    holdingsPnl: [],
    ratesData: [],
    _fetchedAt: {
      overview: 0,
      annualPnl: 0,
      trendData: 0,
      holdingsPnl: 0,
      ratesData: 0,
    },
    _inflight: {},
    _loadingModules: { overview: true, annualPnl: true, trendData: true, holdingsPnl: true, ratesData: true },
    _firstLoadDone: false,
    loading: true,
  }),

  getters: {
    rateList: (state) => state.ratesData.filter(r => r.currency !== 'CNY'),
    rateDate: (state) => {
      const dates = state.ratesData.map(r => r.date).filter(Boolean)
      return dates.length ? dates[0] : ''
    },
    rateSource: (state) => {
      const sources = [...new Set(state.ratesData.map(r => r.source).filter(Boolean))]
      return sources.length ? `(${sources.join(', ')})` : ''
    },
  },

  actions: {
    async _fetchOne(key, fetcher, forceRefresh) {
      if (!forceRefresh && this._fetchedAt[key] && Date.now() - this._fetchedAt[key] < MAX_AGE) {
        return this[key]
      }
      if (this._inflight[key]) return this._inflight[key]
      this._inflight[key] = fetcher().then(data => {
        this[key] = data
        this._fetchedAt[key] = Date.now()
        this._inflight[key] = null
        return data
      }).catch(e => {
        this._inflight[key] = null
        throw e
      })
      return this._inflight[key]
    },

    async fetchAll(forceRefresh = false) {
      if (!forceRefresh) {
        const allFresh = Object.keys(this._fetchedAt).every(
          key => this._fetchedAt[key] && Date.now() - this._fetchedAt[key] < MAX_AGE
        )
        if (allFresh) {
          this.loading = false
          this._firstLoadDone = true
          return
        }
      }
      this.loading = true
      MODULES.forEach(m => { this._loadingModules[m] = true })
      try {
        if (forceRefresh || !this.overview || !Object.keys(this.overview).length) {
          this.loading = false
          const data = await api.getDashboardAll()
          this._applyPartialData(data)
        } else {
          this.loading = false
          const results = await Promise.allSettled([
            this._fetchOne('overview', api.getOverview, forceRefresh),
            this._fetchOne('annualPnl', api.getAnnualPnl, forceRefresh),
            this._fetchOne('trendData', api.getTrend, forceRefresh),
            this._fetchOne('holdingsPnl', api.getHoldingsPnl, forceRefresh),
            this.fetchRates(forceRefresh),
          ])
          const keys = MODULES
          results.forEach((r, i) => {
            if (r.status === 'fulfilled') {
              this[keys[i]] = r.value
              this._fetchedAt[keys[i]] = Date.now()
            }
            this._loadingModules[keys[i]] = false
          })
        }
      } finally {
        this._firstLoadDone = true
      }
    },

    _applyPartialData(data) {
      const now = Date.now()
      for (const key of MODULES) {
        if (data[key] != null) {
          this[key] = data[key]
          this._fetchedAt[key] = now
        }
        this._loadingModules[key] = false
      }
    },

    isLoadingModule(key) {
      return this._loadingModules[key]
    },

    async fetchRates(forceRefresh = false) {
      return this._fetchOne('ratesData', api.getExchangeRates, forceRefresh)
    },

    invalidateAll() {
      this._fetchedAt = { overview: 0, annualPnl: 0, trendData: 0, holdingsPnl: 0, ratesData: 0 }
    },

    resetState() {
      this.overview = {}
      this.annualPnl = {}
      this.trendData = []
      this.holdingsPnl = []
      this.ratesData = []
      this._fetchedAt = { overview: 0, annualPnl: 0, trendData: 0, holdingsPnl: 0, ratesData: 0 }
      this._inflight = {}
      this._loadingModules = { overview: true, annualPnl: true, trendData: true, holdingsPnl: true, ratesData: true }
      this._firstLoadDone = false
      this.loading = true
    },

    async saveRate(currency, value) {
      await api.updateExchangeRate(currency, value)
      this.invalidateAll()
      const accountsStore = useAccountsStore()
      accountsStore.invalidateAll()
      await this.fetchRates(true)
    },

    async refreshRates() {
      this.ratesData = await api.refreshExchangeRates()
      this.invalidateAll()
      const accountsStore = useAccountsStore()
      accountsStore.invalidateAll()
      const trackerStore = useStockTrackerStore()
      trackerStore.invalidateAll()
    },

    async addCurrency(code, rate) {
      const { registerCurrency } = useCurrencies()
      await registerCurrency(code, rate)
      this.invalidateAll()
      const accountsStore = useAccountsStore()
      accountsStore.invalidateAll()
      await this.fetchRates(true)
    },

    async removeCurrency(currency) {
      const { unregisterCurrency } = useCurrencies()
      await unregisterCurrency(currency)
      this.invalidateAll()
      const accountsStore = useAccountsStore()
      accountsStore.invalidateAll()
      await this.fetchRates(true)
    },

    async saveSnapshot() {
      await api.saveSnapshot()
      this._fetchedAt.trendData = 0
      await this._fetchOne('trendData', api.getTrend, true)
    },
  },
})
