import { ref, computed } from 'vue'
import { resetAllStores } from '../stores'

const token = ref(localStorage.getItem('easyfund_token') || '')
const userInfo = ref(JSON.parse(localStorage.getItem('easyfund_user') || 'null'))

function loadSessions() {
  return JSON.parse(localStorage.getItem('easyfund_sessions') || '{}')
}

function saveSessions(sessions) {
  localStorage.setItem('easyfund_sessions', JSON.stringify(sessions))
}

export function useAuth() {
  const isAuthenticated = computed(() => !!token.value)
  const username = computed(() => userInfo.value?.username || '')
  const displayName = computed(() => userInfo.value?.display_name || '')

  function setAuth(data) {
    token.value = data.token
    userInfo.value = { username: data.username, display_name: data.display_name }
    localStorage.setItem('easyfund_token', data.token)
    localStorage.setItem('easyfund_user', JSON.stringify(userInfo.value))

    const sessions = loadSessions()
    sessions[data.username] = { token: data.token, display_name: data.display_name }
    saveSessions(sessions)
  }

  function clearAuth() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('easyfund_token')
    localStorage.removeItem('easyfund_user')
  }

  function logout() {
    const currentUsername = userInfo.value?.username
    if (currentUsername) {
      const sessions = loadSessions()
      delete sessions[currentUsername]
      saveSessions(sessions)
    }
    clearAuth()
  }

  function switchUser(targetUsername) {
    const sessions = loadSessions()
    const session = sessions[targetUsername]
    if (!session) return false

    token.value = session.token
    userInfo.value = { username: targetUsername, display_name: session.display_name }
    localStorage.setItem('easyfund_token', session.token)
    localStorage.setItem('easyfund_user', JSON.stringify(userInfo.value))

    resetAllStores()
    return true
  }

  function getSavedSessions() {
    const sessions = loadSessions()
    const current = userInfo.value?.username
    return Object.entries(sessions)
      .filter(([name]) => name !== current)
      .map(([name, data]) => ({ username: name, display_name: data.display_name }))
  }

  function removeSession(targetUsername) {
    const sessions = loadSessions()
    delete sessions[targetUsername]
    saveSessions(sessions)
  }

  return { token, userInfo, isAuthenticated, username, displayName, setAuth, clearAuth, logout, switchUser, getSavedSessions, removeSession }
}
