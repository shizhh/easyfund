import { useAccountsStore } from './accounts'
import { useDashboardStore } from './dashboard'
import { useStockTrackerStore } from './stockTracker'

export function invalidateAllStores() {
  useAccountsStore().invalidateAll()
  useDashboardStore().invalidateAll()
  useStockTrackerStore().invalidateAll()
}

export function resetAllStores() {
  useAccountsStore().resetState()
  useDashboardStore().resetState()
  useStockTrackerStore().resetState()
}
