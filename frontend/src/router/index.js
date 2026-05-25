import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/', name: 'dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/accounts', name: 'accounts', component: () => import('../views/Accounts.vue') },
  { path: '/investments', name: 'investments', component: () => import('../views/Investments.vue') },
  { path: '/stock-tracker', name: 'stock-tracker', component: () => import('../views/StockTracker.vue') },
  { path: '/import', name: 'import', component: () => import('../views/DataImport.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const { isAuthenticated } = useAuth()
  if (to.meta.public || isAuthenticated.value) {
    next()
  } else {
    next('/login')
  }
})

export default router
