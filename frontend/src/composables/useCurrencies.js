// frontend/src/composables/useCurrencies.js
import { ref, computed } from 'vue'
import api from '../api'

const rates = ref([])
let loadPromise = null

async function loadRates() {
  rates.value = await api.getExchangeRates()
}

export function useCurrencies() {
  const currencyOptions = computed(() => {
    const set = new Set(['CNY'])
    for (const r of rates.value) {
      if (r.currency) set.add(r.currency)
    }
    return [...set]
  })

  async function fetchRates() {
    if (!loadPromise) {
      loadPromise = loadRates().finally(() => { loadPromise = null })
    }
    await loadPromise
  }

  function getRateToCny(currency) {
    if (currency === 'CNY') return 1
    const r = rates.value.find(r => r.currency === currency)
    return r ? r.rate_to_cny : 1
  }

  async function registerCurrency(currency, rate) {
    await api.registerCurrency(currency, rate)
    await loadRates()
  }

  async function unregisterCurrency(currency) {
    await api.unregisterCurrency(currency)
    await loadRates()
  }

  return { rates, currencyOptions, fetchRates, getRateToCny, registerCurrency, unregisterCurrency }
}
