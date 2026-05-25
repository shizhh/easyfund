<template>
  <div class="login-page">
    <div class="login-card card">
      <div class="login-header">
        <h1 class="logo">墨账</h1>
        <span class="logo-sub">EasyFund</span>
      </div>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input v-model="username" class="form-input" type="text" autocomplete="username" required />
        </div>
        <div class="form-group">
          <label class="form-label">密码</label>
          <input ref="passwordInput" v-model="password" class="form-input" type="password" autocomplete="current-password" required />
        </div>
        <div v-if="error" class="login-error">{{ error }}</div>
        <button class="btn btn-primary login-btn" type="submit" :disabled="loading">
          <span v-if="loading" class="login-spinner"></span>
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { resetAllStores } from '../stores'
import api from '../api'

const router = useRouter()
const { setAuth } = useAuth()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const passwordInput = ref(null)

onMounted(async () => {
  const expiredUser = localStorage.getItem('easyfund_expired_user')
  if (expiredUser) {
    username.value = expiredUser
    localStorage.removeItem('easyfund_expired_user')
    await nextTick()
    passwordInput.value?.focus()
  }
})

async function handleLogin() {
  error.value = ''
  loading.value = true

  // Start preloading the Dashboard chunk while login request is in-flight
  const dashboardChunk = import('../views/Dashboard.vue')

  try {
    const data = await api.login(username.value, password.value)
    setAuth(data)

    // Clear stale cache from previous sessions before navigating
    resetAllStores()

    // Ensure dashboard chunk is loaded, then navigate immediately
    await dashboardChunk
    router.replace('/')

    // Preload route chunks in background so page transitions feel instant.
    // Data loading is handled by each page's onMounted — no prefetch needed.
    Promise.all([
      import('../views/Accounts.vue'),
      import('../views/Investments.vue'),
      import('../views/StockTracker.vue'),
      import('../views/DataImport.vue'),
    ]).catch(() => {})
  } catch (e) {
    error.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100vh;
  background: var(--paper);
}

.login-card {
  width: 380px;
  padding: 40px 36px;
  text-align: center;
}

.login-header {
  margin-bottom: 32px;
}

.login-header .logo {
  font-family: var(--font-display);
  font-size: 36px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.06em;
  margin: 0;
}

.login-header .logo-sub {
  display: block;
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--gold);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-top: 4px;
}

.login-btn {
  width: 100%;
  margin-top: 8px;
  padding: 10px 18px;
  font-size: 14px;
}

.login-error {
  color: var(--vermillion);
  font-size: 13px;
  margin: 8px 0 0;
  text-align: left;
}

.login-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .6s linear infinite;
  vertical-align: middle;
  margin-right: 6px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
