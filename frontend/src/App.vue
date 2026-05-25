<template>
  <div class="app">
    <template v-if="isAuthenticated && $route.path !== '/login'">
      <!-- Desktop sidebar -->
      <nav class="sidebar">
        <div class="logo-wrap">
          <h1 class="logo">墨账</h1>
          <span class="logo-sub">EasyFund</span>
        </div>
        <div class="nav-links">
          <router-link to="/" class="nav-item" active-class="active" @mouseenter="prefetchRoute('/')">
            <span class="nav-icon">◉</span> 资产总览
          </router-link>
          <router-link to="/accounts" class="nav-item" active-class="active" @mouseenter="prefetchRoute('/accounts')">
            <span class="nav-icon">◎</span> 账户管理
          </router-link>
          <router-link to="/investments" class="nav-item" active-class="active" @mouseenter="prefetchRoute('/investments')">
            <span class="nav-icon">◇</span> 投资追踪
          </router-link>
          <router-link to="/stock-tracker" class="nav-item" active-class="active" @mouseenter="prefetchRoute('/stock-tracker')">
            <span class="nav-icon">△</span> 股价追踪
          </router-link>
          <router-link to="/import" class="nav-item" active-class="active" @mouseenter="prefetchRoute('/import')">
            <span class="nav-icon">▼</span> 数据导入
          </router-link>
        </div>
        <div class="nav-footer">
          <div class="user-info">
            <button class="user-switch-btn" @click="showUserMenu = !showUserMenu">
              <span class="user-name">{{ displayName }}</span>
              <span class="user-arrow" :class="{ open: showUserMenu }">▾</span>
            </button>
            <Transition name="dropdown">
              <div v-if="showUserMenu" class="user-dropdown">
                <button
                  v-for="s in savedSessions" :key="s.username"
                  class="dropdown-item"
                  @click="handleSwitch(s.username)"
                >
                  <span class="dropdown-user-name">{{ s.display_name }}</span>
                  <span class="dropdown-item-right">
                    <span class="dropdown-switch-hint">切换</span>
                    <span class="dropdown-delete-btn" @click.stop="handleRemoveSession(s.username)">×</span>
                  </span>
                </button>
                <button class="dropdown-item dropdown-item-add" @click="showLoginModal = true; showUserMenu = false">
                  <span>+ 登录其他账户</span>
                </button>
                <button class="dropdown-item dropdown-item-logout" @click="handleLogout">退出登录</button>
              </div>
            </Transition>
          </div>
        </div>
      </nav>
      <!-- Mobile top bar -->
      <header class="mobile-header">
        <span class="mobile-logo">墨账</span>
        <div class="mobile-user">
          <button class="user-switch-btn mobile-switch" @click="showUserMenu = !showUserMenu">
            <span class="user-name">{{ displayName }}</span>
            <span class="user-arrow" :class="{ open: showUserMenu }">▾</span>
          </button>
          <Transition name="dropdown">
            <div v-if="showUserMenu" class="user-dropdown mobile-dropdown">
              <button
                v-for="s in savedSessions" :key="s.username"
                class="dropdown-item"
                @click="handleSwitch(s.username)"
              >
                <span class="dropdown-user-name">{{ s.display_name }}</span>
                <span class="dropdown-item-right">
                  <span class="dropdown-switch-hint">切换</span>
                  <span class="dropdown-delete-btn" @click.stop="handleRemoveSession(s.username)">×</span>
                </span>
              </button>
              <button class="dropdown-item dropdown-item-add" @click="showLoginModal = true; showUserMenu = false">
                <span>+ 登录其他账户</span>
              </button>
              <button class="dropdown-item dropdown-item-logout" @click="handleLogout">退出登录</button>
            </div>
          </Transition>
        </div>
      </header>
      <main class="content">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </main>
      <!-- Mobile bottom nav -->
      <nav class="bottom-nav">
        <router-link to="/" class="bottom-nav-item" active-class="active" @touchstart.passive="prefetchRoute('/')">
          <span class="bottom-nav-icon">◉</span>
          <span>总览</span>
        </router-link>
        <router-link to="/accounts" class="bottom-nav-item" active-class="active" @touchstart.passive="prefetchRoute('/accounts')">
          <span class="bottom-nav-icon">◎</span>
          <span>账户</span>
        </router-link>
        <router-link to="/investments" class="bottom-nav-item" active-class="active" @touchstart.passive="prefetchRoute('/investments')">
          <span class="bottom-nav-icon">◇</span>
          <span>投资</span>
        </router-link>
        <router-link to="/stock-tracker" class="bottom-nav-item" active-class="active" @touchstart.passive="prefetchRoute('/stock-tracker')">
          <span class="bottom-nav-icon">△</span>
          <span>股价</span>
        </router-link>
        <router-link to="/import" class="bottom-nav-item" active-class="active" @touchstart.passive="prefetchRoute('/import')">
          <span class="bottom-nav-icon">▼</span>
          <span>导入</span>
        </router-link>
      </nav>
      <AiChat />

      <!-- Login modal for switching accounts -->
      <div v-if="showLoginModal" class="modal-overlay" @click.self="showLoginModal = false">
        <div class="card modal switch-login-modal">
          <h3>登录其他账户</h3>
          <form @submit.prevent="handleSwitchLogin">
            <div class="form-group">
              <label class="form-label">用户名</label>
              <input v-model="switchUsername" class="form-input" type="text" autocomplete="username" required />
            </div>
            <div class="form-group">
              <label class="form-label">密码</label>
              <input v-model="switchPassword" class="form-input" type="password" autocomplete="current-password" required />
            </div>
            <div v-if="switchLoginError" style="color: var(--vermillion); font-size: 13px; margin: 4px 0;">{{ switchLoginError }}</div>
            <div class="modal-actions">
              <button type="button" class="btn btn-ghost" @click="showLoginModal = false">取消</button>
              <button type="submit" class="btn btn-primary" :disabled="switchLoginLoading">
                <span v-if="switchLoginLoading" class="login-spinner"></span>
                {{ switchLoginLoading ? '登录中...' : '登录' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="login-wrap"><router-view /></div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from './composables/useAuth'
import { resetAllStores } from './stores'
import AiChat from './components/AiChat.vue'
import api from './api'

const router = useRouter()
const { isAuthenticated, displayName, logout, switchUser, getSavedSessions, removeSession, setAuth } = useAuth()

const showUserMenu = ref(false)
const sessionVersion = ref(0)
const savedSessions = computed(() => {
  sessionVersion.value // track for reactivity
  return getSavedSessions()
})

// Switch login modal state
const showLoginModal = ref(false)
const switchUsername = ref('')
const switchPassword = ref('')
const switchLoginError = ref('')
const switchLoginLoading = ref(false)

async function handleSwitchLogin() {
  switchLoginError.value = ''
  switchLoginLoading.value = true
  try {
    const data = await api.login(switchUsername.value, switchPassword.value)
    setAuth(data)
    resetAllStores()
    showLoginModal.value = false
    switchUsername.value = ''
    switchPassword.value = ''
    if (window.location.pathname === '/') {
      window.location.reload()
    } else {
      window.location.href = '/'
    }
  } catch (e) {
    switchLoginError.value = e.message || '登录失败'
  } finally {
    switchLoginLoading.value = false
  }
}

function closeUserMenu(e) {
  if (!e.target.closest('.user-info') && !e.target.closest('.mobile-user')) {
    showUserMenu.value = false
  }
}
onMounted(() => document.addEventListener('click', closeUserMenu))
onUnmounted(() => document.removeEventListener('click', closeUserMenu))

function handleSwitch(targetUsername) {
  showUserMenu.value = false
  if (switchUser(targetUsername)) {
    if (window.location.pathname === '/') {
      window.location.reload()
    } else {
      window.location.href = '/'
    }
  }
}

// Preload route chunk on nav hover so the page opens instantly on click
const prefetched = new Set()
function prefetchRoute(path) {
  if (prefetched.has(path)) return
  prefetched.add(path)
  const route = router.resolve(path)
  if (route?.matched?.length) {
    route.matched.forEach(m => m.components?.default?.())
  }
}

function handleRemoveSession(targetUsername) {
  removeSession(targetUsername)
  sessionVersion.value++
}

function handleLogout() {
  showUserMenu.value = false
  logout()
  router.push('/login')
}
</script>

<style>
:root {
  --ink: #0d0d14;
  --ink-light: #1a1a2e;
  --ink-mid: #2a2a3e;
  --paper: #faf8f4;
  --paper-warm: #f5f2ec;
  --paper-line: #e8e4dc;
  --vermillion: #c53d43;
  --vermillion-soft: rgba(197,61,67,.08);
  --vermillion-hover: #b03338;
  --gold: #b8945a;
  --gold-soft: rgba(184,148,90,.1);
  --text: #1a1a2e;
  --text-secondary: #6b6b7b;
  --text-muted: #9998a8;
  --positive: #c53d43;
  --negative: #2e7d32;
  --radius: 10px;
  --radius-lg: 14px;
  --shadow-sm: 0 1px 3px rgba(13,13,20,.06);
  --shadow-md: 0 4px 16px rgba(13,13,20,.08);
  --shadow-lg: 0 8px 32px rgba(13,13,20,.12);
  --transition: .25s cubic-bezier(.4,0,.2,1);
  --font-display: 'Noto Serif SC', 'Songti SC', serif;
  --font-body: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font-body);
  background: var(--paper);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}

/* Subtle paper texture */
body::before {
  content: '';
  position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background:
    radial-gradient(ellipse at 20% 50%, rgba(184,148,90,.03) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(197,61,67,.02) 0%, transparent 50%),
    var(--paper);
}
body.screenshot-mode::before { display: none; }

.app { display: flex; height: 100vh; overflow: hidden; }
.login-wrap { width: 100%; height: 100vh; }

/* ---- Mobile Header (hidden on desktop) ---- */
.mobile-header {
  display: none;
  background: var(--ink);
  color: #fff;
  padding: 12px 16px;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.mobile-logo {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: .06em;
}
.mobile-user {
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
}

/* ---- Bottom Nav (hidden on desktop) ---- */
.bottom-nav {
  display: none;
  background: var(--ink);
  color: #fff;
  padding: 6px 0;
  padding-bottom: env(safe-area-inset-bottom, 6px);
  flex-shrink: 0;
}
.bottom-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  color: rgba(255,255,255,.5);
  text-decoration: none;
  font-size: 11px;
  transition: color var(--transition);
  padding: 4px 0;
}
.bottom-nav-icon {
  font-size: 16px;
}
.bottom-nav-item.active {
  color: var(--vermillion);
}

/* ---- Sidebar ---- */
.sidebar {
  width: 220px; background: var(--ink); color: #fff; padding: 0;
  display: flex; flex-direction: column; flex-shrink: 0;
  position: relative; overflow: hidden;
}
/* Ink wash gradient on sidebar */
.sidebar::after {
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 40%;
  background: linear-gradient(to top, rgba(42,42,62,.6), transparent);
  pointer-events: none;
}

.logo-wrap {
  padding: 28px 24px 24px; border-bottom: 1px solid rgba(255,255,255,.06);
  position: relative; z-index: 1;
}
.logo {
  font-family: var(--font-display); font-size: 26px; font-weight: 700;
  letter-spacing: .06em; color: #fff;
}
.logo-sub {
  display: block; font-family: var(--font-body); font-size: 11px;
  color: var(--gold); letter-spacing: .12em; text-transform: uppercase;
  margin-top: 4px;
}

.nav-links { padding: 16px 0; position: relative; z-index: 1; }

.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 11px 24px; color: rgba(255,255,255,.5); text-decoration: none;
  font-size: 14px; font-weight: 400; transition: all var(--transition);
  position: relative; letter-spacing: .02em;
}
.nav-icon { font-size: 10px; opacity: .7; }
.nav-item:hover { color: rgba(255,255,255,.85); background: rgba(255,255,255,.04); }
.nav-item.active {
  color: #fff; background: rgba(255,255,255,.08);
}
.nav-item.active::before {
  content: ''; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 3px; height: 20px; border-radius: 0 3px 3px 0; background: var(--vermillion);
}

.content { flex: 1; padding: 32px 36px; overflow-y: auto; }

/* ---- Sidebar Footer ---- */
.nav-footer {
  margin-top: auto;
  padding: 16px 20px;
  border-top: 1px solid rgba(255,255,255,.06);
  position: relative;
  z-index: 1;
}
.user-info {
  position: relative;
}
.user-switch-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  font-family: var(--font-body);
}
.user-name {
  color: rgba(255,255,255,.7);
  font-size: 13px;
  letter-spacing: .02em;
}
.user-arrow {
  color: rgba(255,255,255,.35);
  font-size: 11px;
  transition: transform var(--transition);
}
.user-arrow.open {
  transform: rotate(180deg);
}

/* ---- User Dropdown ---- */
.user-dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  margin-bottom: 4px;
  background: var(--ink-light);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: var(--radius);
  overflow: hidden;
  z-index: 10;
}
.mobile-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  left: auto;
  margin-top: 4px;
  min-width: 140px;
}
.dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 14px;
  background: none;
  border: none;
  color: rgba(255,255,255,.7);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition);
  font-family: var(--font-body);
  text-align: left;
}
.dropdown-item:hover {
  background: rgba(255,255,255,.06);
  color: #fff;
}
.dropdown-user-name {
  letter-spacing: .02em;
}
.dropdown-item-right {
  display: flex;
  align-items: center;
}
.dropdown-switch-hint {
  font-size: 11px;
  color: rgba(255,255,255,.3);
}
.dropdown-item:hover .dropdown-switch-hint {
  display: none;
}
.dropdown-delete-btn {
  display: none;
  font-size: 15px;
  color: rgba(255,255,255,.3);
  padding: 0 2px;
  line-height: 1;
}
.dropdown-item:hover .dropdown-delete-btn {
  display: inline;
}
.dropdown-delete-btn:hover {
  color: var(--vermillion);
}
.dropdown-item-logout {
  border-top: 1px solid rgba(255,255,255,.06);
  color: rgba(255,255,255,.45);
  justify-content: center;
}
.dropdown-item-logout:hover {
  color: var(--vermillion);
}
.dropdown-item-add {
  color: rgba(255,255,255,.5);
  justify-content: center;
  font-size: 12px;
}
.dropdown-item-add:hover {
  color: var(--gold);
}

.switch-login-modal {
  width: 360px;
  animation: slideUp .25s cubic-bezier(.4,0,.2,1);
}
.switch-login-modal h3 {
  margin-bottom: 12px;
  padding-bottom: 10px;
}

/* Dropdown transition */
.dropdown-enter-active { transition: all .15s ease-out; }
.dropdown-leave-active { transition: all .1s ease-in; }
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.btn-logout {
  background: none;
  border: 1px solid rgba(255,255,255,.15);
  color: rgba(255,255,255,.5);
  padding: 4px 12px;
  border-radius: var(--radius);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition);
  font-family: var(--font-body);
}
.btn-logout:hover {
  color: rgba(255,255,255,.85);
  border-color: rgba(255,255,255,.3);
  background: rgba(255,255,255,.06);
}

/* ---- Cards ---- */
.card {
  background: #fff; border-radius: var(--radius-lg); padding: 24px;
  box-shadow: var(--shadow-sm); border: 1px solid var(--paper-line);
  transition: box-shadow var(--transition);
}
.card:hover { box-shadow: var(--shadow-md); }

.card-title {
  font-family: var(--font-body); font-size: 12px; font-weight: 500;
  color: var(--text-muted); margin-bottom: 6px; letter-spacing: .06em;
  text-transform: uppercase;
}
.card-value {
  font-family: var(--font-body); font-size: 30px; font-weight: 700;
  color: var(--text); letter-spacing: -.02em;
}

/* ---- Grids ---- */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 18px; }
.grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 18px; }

/* ---- Tables ---- */
table { width: 100%; border-collapse: collapse; }
th {
  text-align: left; padding: 10px 14px; font-size: 11px; font-weight: 600;
  color: var(--text-muted); border-bottom: 2px solid var(--paper-line);
  letter-spacing: .06em; text-transform: uppercase;
}
td {
  padding: 12px 14px; border-bottom: 1px solid #f2f0ea; font-size: 14px;
  color: var(--text); vertical-align: middle;
}
tr { transition: background var(--transition); }
tr:hover td { background: var(--paper-warm); }

/* ---- Buttons ---- */
.btn {
  padding: 8px 18px; border-radius: var(--radius); border: none; cursor: pointer;
  font-size: 13px; font-weight: 500; transition: all var(--transition);
  letter-spacing: .02em; font-family: var(--font-body);
}
.btn-primary {
  background: var(--vermillion); color: #fff;
  box-shadow: 0 2px 8px rgba(197,61,67,.2);
}
.btn-primary:hover {
  background: var(--vermillion-hover);
  box-shadow: 0 4px 12px rgba(197,61,67,.3); transform: translateY(-1px);
}
.btn-sm { padding: 5px 12px; font-size: 12px; }
.btn-danger {
  background: transparent; color: var(--vermillion); border: 1px solid rgba(197,61,67,.2);
}
.btn-danger:hover { background: var(--vermillion-soft); border-color: var(--vermillion); }
.btn-ghost {
  background: transparent; color: var(--text-secondary); border: 1px solid var(--paper-line);
}
.btn-ghost:hover { background: var(--paper-warm); color: var(--text); }

/* ---- Tags ---- */
.tag {
  display: inline-block; padding: 4px 14px; border-radius: 20px;
  font-size: 13px; font-weight: 600; letter-spacing: .02em;
}
.tag-cash { background: #e8f5e9; color: #2e7d32; }
.tag-investment { background: var(--vermillion-soft); color: var(--vermillion); }
.tag-insurance { background: #fff3e0; color: #e65100; }
.tag-future_cash { background: var(--gold-soft); color: var(--gold); }

/* ---- Positive / Negative (Chinese market convention) ---- */
.positive { color: var(--positive); font-weight: 500; }
.negative { color: var(--negative); font-weight: 500; }

/* ---- Headings ---- */
h2 {
  font-family: var(--font-display); font-size: 22px; font-weight: 700;
  margin-bottom: 20px; color: var(--text); letter-spacing: .04em;
}
h3 {
  font-family: var(--font-display); font-size: 16px; font-weight: 600;
  color: var(--text); letter-spacing: .03em;
}

/* ---- Toolbar ---- */
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}

/* ---- Action columns ---- */
.action-col { text-align: right; white-space: nowrap; }
.btn-link {
  background: none; border: none; cursor: pointer; font-size: 13px;
  padding: 3px 8px; color: var(--text-secondary); font-weight: 500;
  transition: color var(--transition); font-family: var(--font-body);
  text-decoration: none; border-radius: 4px;
}
.btn-link:hover { color: var(--vermillion); background: var(--vermillion-soft); }
.btn-link.danger:hover { color: var(--vermillion); }

/* ---- Forms ---- */
.form-label {
  display: block; margin-bottom: 5px; font-size: 12px; font-weight: 500;
  color: var(--text-secondary); letter-spacing: .04em;
}
.form-input {
  width: 100%; padding: 8px 12px; border: 1px solid var(--paper-line);
  border-radius: var(--radius); font-size: 14px; font-family: var(--font-body);
  color: var(--text); background: #fff; transition: all var(--transition);
  outline: none;
}
.form-input:focus {
  border-color: var(--vermillion); box-shadow: 0 0 0 3px var(--vermillion-soft);
}
.form-select {
  width: 100%; padding: 8px 12px; border: 1px solid var(--paper-line);
  border-radius: var(--radius); font-size: 14px; font-family: var(--font-body);
  color: var(--text); background: #fff; transition: all var(--transition);
  outline: none; cursor: pointer;
}
.form-select:focus {
  border-color: var(--vermillion); box-shadow: 0 0 0 3px var(--vermillion-soft);
}
.form-group { margin: 14px 0; }
.form-row { display: flex; gap: 10px; }
.form-row > * { flex: 1; }

/* ---- Chart ---- */
.chart-container { width: 100%; height: 320px; }

/* ---- Modal ---- */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(13,13,20,.45);
  display: flex; align-items: center; justify-content: center; z-index: 100;
  backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
  animation: fadeIn .2s ease;
}
.modal {
  width: 480px; max-height: 80vh; overflow-y: auto;
  animation: slideUp .25s cubic-bezier(.4,0,.2,1);
  box-shadow: var(--shadow-lg);
}
.modal h3 {
  font-family: var(--font-display); font-size: 18px; font-weight: 700;
  margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--paper-line);
  letter-spacing: .04em;
}
.modal-actions {
  margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--paper-line);
  display: flex; gap: 10px; justify-content: flex-end;
}

/* ---- Animations ---- */
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px) scale(.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

/* Stagger animation for cards */
.card { animation: cardIn .35s cubic-bezier(.4,0,.2,1) both; }
.grid-2 .card:nth-child(1) { animation-delay: 0s; }
.grid-2 .card:nth-child(2) { animation-delay: .06s; }
.grid-3 .card:nth-child(1) { animation-delay: 0s; }
.grid-3 .card:nth-child(2) { animation-delay: .06s; }
.grid-3 .card:nth-child(3) { animation-delay: .12s; }
.grid-4 .card:nth-child(1) { animation-delay: 0s; }
.grid-4 .card:nth-child(2) { animation-delay: .05s; }
.grid-4 .card:nth-child(3) { animation-delay: .10s; }
.grid-4 .card:nth-child(4) { animation-delay: .15s; }
@keyframes cardIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ---- Scrollbar ---- */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--paper-line); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ---- Responsive (mobile) ---- */
@media (max-width: 768px) {
  .app { flex-direction: column; }
  /* Hide desktop sidebar, show mobile nav */
  .sidebar { display: none; }
  .mobile-header { display: flex; }
  .bottom-nav { display: flex; justify-content: space-around; }
  .content { padding: 16px; overflow-y: auto; }
  .nav-footer { display: none; }
  /* Grids → single column */
  .grid-2, .grid-3, .grid-4 { grid-template-columns: 1fr; gap: 12px; }
  /* Cards */
  .card { padding: 16px; }
  .card-value { font-size: 24px; }
  /* Tables scroll */
  .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
  table { min-width: 500px; }
  /* Headings */
  h2 { font-size: 18px; margin-bottom: 14px; }
  /* Modal full-width */
  .modal { width: calc(100vw - 32px); max-height: 85vh; }
  /* Toolbar keep row */
  .toolbar { flex-wrap: wrap; gap: 8px; }
  .toolbar .btn-screenshot-text { display: none; }
  /* Chart */
  .chart-container { height: 260px; }
}
</style>
