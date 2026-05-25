import { ref, computed } from 'vue'

const API_BASE = '/api'

function getAuthHeaders() {
  const token = localStorage.getItem('easyfund_token')
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

// Singleton state shared across all component instances
const conversations = ref([])
const currentConversationId = ref(null)
const messages = ref([])
const isLoading = ref(false)
const isStreaming = ref(false)
const streamingContent = ref('')
const toolCallStatus = ref(null)  // { name, args, status }
const config = ref({ base_url: '', api_key: '', model: '' })
const isOpen = ref(false)
const isConfigured = ref(false)

export function useAiChat() {
  const currentConversation = computed(() =>
    conversations.value.find(c => c.id === currentConversationId.value)
  )

  const allMessages = computed(() => {
    if (streamingContent.value) {
      return [
        ...messages.value,
        { role: 'assistant', content: streamingContent.value, isStreaming: true },
      ]
    }
    return messages.value
  })

  async function loadConfig() {
    try {
      const res = await fetch(`${API_BASE}/chat/config`, { headers: getAuthHeaders() })
      if (res.ok) {
        config.value = await res.json()
        isConfigured.value = !!(config.value.api_key && config.value.base_url)
      }
    } catch (e) {
      console.error('Failed to load AI config:', e)
    }
  }

  async function saveConfig(newConfig) {
    const res = await fetch(`${API_BASE}/chat/config`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(newConfig),
    })
    if (res.ok) {
      config.value = await res.json()
      isConfigured.value = !!(newConfig.api_key && newConfig.base_url)
    }
  }

  async function loadConversations() {
    try {
      const res = await fetch(`${API_BASE}/chat/conversations`, { headers: getAuthHeaders() })
      if (res.ok) {
        conversations.value = await res.json()
      }
    } catch (e) {
      console.error('Failed to load conversations:', e)
    }
  }

  async function createConversation(title = '新对话') {
    const res = await fetch(`${API_BASE}/chat/conversations`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ title }),
    })
    if (res.ok) {
      const conv = await res.json()
      conversations.value.unshift({
        id: conv.id,
        title: conv.title,
        created_at: conv.created_at,
        updated_at: conv.updated_at,
        message_count: 0,
      })
      await selectConversation(conv.id)
      return conv
    }
  }

  async function selectConversation(id) {
    if (isStreaming.value) return
    currentConversationId.value = id
    if (!id) {
      messages.value = []
      return
    }
    try {
      const res = await fetch(`${API_BASE}/chat/conversations/${id}`, { headers: getAuthHeaders() })
      if (res.ok) {
        const conv = await res.json()
        messages.value = conv.messages || []
      }
    } catch (e) {
      console.error('Failed to load conversation:', e)
    }
  }

  async function deleteConversation(id) {
    const res = await fetch(`${API_BASE}/chat/conversations/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    })
    if (res.ok) {
      conversations.value = conversations.value.filter(c => c.id !== id)
      if (currentConversationId.value === id) {
        currentConversationId.value = null
        messages.value = []
      }
    }
  }

  async function sendMessage(text) {
    if (!text.trim() || isStreaming.value) return

    // Ensure we have a conversation
    if (!currentConversationId.value) {
      await createConversation()
    }

    // Add user message to UI immediately
    messages.value.push({ role: 'user', content: text })
    isStreaming.value = true
    streamingContent.value = ''
    toolCallStatus.value = null

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          conversation_id: currentConversationId.value,
          message: text,
        }),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        messages.value.push({ role: 'assistant', content: `错误: ${err.detail || '请求失败'}` })
        isStreaming.value = false
        return
      }

      // Read SSE stream
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''  // Keep incomplete line in buffer

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6)
            try {
              const data = JSON.parse(dataStr)

              if (currentEvent === 'content') {
                streamingContent.value += data.text || ''
              } else if (currentEvent === 'tool_call') {
                toolCallStatus.value = { name: data.name, args: data.args, status: data.status }
              } else if (currentEvent === 'tool_result') {
                toolCallStatus.value = null
              } else if (currentEvent === 'error') {
                streamingContent.value = data.detail || '未知错误'
              } else if (currentEvent === 'done') {
                // Stream complete
              }
            } catch (e) {
              // Ignore parse errors for incomplete chunks
            }
            currentEvent = ''
          }
        }
      }
    } catch (e) {
      streamingContent.value = `连接失败: ${e.message}`
    } finally {
      // Finalize: move streaming content to messages
      if (streamingContent.value) {
        messages.value.push({ role: 'assistant', content: streamingContent.value })
      }
      streamingContent.value = ''
      toolCallStatus.value = null
      isStreaming.value = false

      // Update conversation title in list
      const conv = conversations.value.find(c => c.id === currentConversationId.value)
      if (conv) {
        conv.message_count = messages.value.length
        // Title may have been auto-updated by backend
        try {
          const res2 = await fetch(`${API_BASE}/chat/conversations/${currentConversationId.value}`, { headers: getAuthHeaders() })
          if (res2.ok) {
            const updated = await res2.json()
            conv.title = updated.title
            conv.updated_at = updated.updated_at
          }
        } catch (_) {}
      }
    }
  }

  function toggleOpen() {
    isOpen.value = !isOpen.value
    if (isOpen.value && conversations.value.length === 0) {
      loadConversations()
      loadConfig()
    }
  }

  return {
    // State
    conversations,
    currentConversationId,
    messages: allMessages,
    isLoading,
    isStreaming,
    streamingContent,
    toolCallStatus,
    config,
    isConfigured,
    isOpen,
    currentConversation,
    // Actions
    loadConfig,
    saveConfig,
    loadConversations,
    createConversation,
    selectConversation,
    deleteConversation,
    sendMessage,
    toggleOpen,
  }
}
