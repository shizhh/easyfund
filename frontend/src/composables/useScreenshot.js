import { toPng } from 'html-to-image'
import { ref } from 'vue'

export function useScreenshot(contentRef, filename) {
  const screenshotLoading = ref(false)

  const screenshot = async () => {
    screenshotLoading.value = true
    try {
      const el = contentRef.value
      if (!el) return
      // Temporarily hide interactive elements for cleaner screenshot
      const hideSelectors = ['.acct-toggle', '.acct-actions', '.drag-handle', '.btn-icon', '.action-col']
      const hidden = []
      hideSelectors.forEach(sel => {
        el.querySelectorAll(sel).forEach(e => {
          hidden.push({ el: e, prev: e.style.display })
          e.style.display = 'none'
        })
      })
      document.body.classList.add('screenshot-mode')
      const dataUrl = await toPng(el, {
        backgroundColor: '#ffffff',
        pixelRatio: 3,
        quality: 1,
      })
      document.body.classList.remove('screenshot-mode')
      hidden.forEach(({ el: e, prev }) => e.style.display = prev)
      const a = document.createElement('a')
      a.href = dataUrl
      a.download = `${filename}_${new Date().toISOString().slice(0, 10)}.png`
      a.click()
    } catch (e) {
      console.error('截图失败', e)
      alert('截图失败，请稍后重试')
    } finally {
      screenshotLoading.value = false
    }
  }

  return { screenshotLoading, screenshot }
}
