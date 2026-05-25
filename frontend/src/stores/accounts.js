import { defineStore } from 'pinia'
import api from '../api'

const MAX_AGE = 5 * 60 * 1000

export const useAccountsStore = defineStore('accounts', {
  state: () => ({
    accounts: [],
    holdings: [],
    _accountsFetchedAt: 0,
    _holdingsFetchedAt: 0,
    _accountsInflight: null,
    _holdingsInflight: null,
    loading: false,
  }),

  getters: {
    accountById: (state) => (id) => state.accounts.find(a => a.id === id),
    accountName: (state) => (id) => {
      const acct = state.accounts.find(a => a.id === id)
      return acct ? acct.name : (id || '未知')
    },
    investmentAccounts: (state) => state.accounts.filter(a => a.category === 'investment'),
    holdingsByAccount: (state) => (accountId) => state.holdings.filter(h => h.account_id === accountId),
  },

  actions: {
    async fetchAccounts(forceRefresh = false) {
      if (!forceRefresh && this._accountsFetchedAt && Date.now() - this._accountsFetchedAt < MAX_AGE) {
        return this.accounts
      }
      if (this._accountsInflight) return this._accountsInflight
      this._accountsInflight = api.getAccounts().then(data => {
        this.accounts = data
        this._accountsFetchedAt = Date.now()
        this._accountsInflight = null
        return data
      }).catch(e => {
        this._accountsInflight = null
        throw e
      })
      return this._accountsInflight
    },

    async fetchHoldings(forceRefresh = false) {
      if (!forceRefresh && this._holdingsFetchedAt && Date.now() - this._holdingsFetchedAt < MAX_AGE) {
        return this.holdings
      }
      if (this._holdingsInflight) return this._holdingsInflight
      this._holdingsInflight = api.getHoldings().then(data => {
        this.holdings = data
        this._holdingsFetchedAt = Date.now()
        this._holdingsInflight = null
        return data
      }).catch(e => {
        this._holdingsInflight = null
        throw e
      })
      return this._holdingsInflight
    },

    async fetchAll(forceRefresh = false) {
      if (!forceRefresh) {
        const accountsFresh = this._accountsFetchedAt && Date.now() - this._accountsFetchedAt < MAX_AGE
        const holdingsFresh = this._holdingsFetchedAt && Date.now() - this._holdingsFetchedAt < MAX_AGE
        if (accountsFresh && holdingsFresh) {
          this.loading = false
          return
        }
      }
      this.loading = true
      try {
        await Promise.all([
          this.fetchAccounts(forceRefresh),
          this.fetchHoldings(forceRefresh),
        ])
      } finally {
        this.loading = false
      }
    },

    invalidateAccounts() {
      this._accountsFetchedAt = 0
    },

    invalidateHoldings() {
      this._holdingsFetchedAt = 0
    },

    invalidateAll() {
      this._accountsFetchedAt = 0
      this._holdingsFetchedAt = 0
    },

    resetState() {
      this.accounts = []
      this.holdings = []
      this._accountsFetchedAt = 0
      this._holdingsFetchedAt = 0
      this._accountsInflight = null
      this._holdingsInflight = null
      this.loading = false
    },
  },
})
