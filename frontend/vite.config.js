import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'

const sslDir = path.resolve(__dirname, '..', '.ssl')

const backendPort = process.env.EASYFUND_BACKEND_PORT || '8000'
const frontendPort = process.env.EASYFUND_FRONTEND_PORT || '3000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: Number(frontendPort),
    https: fs.existsSync(path.join(sslDir, 'cert.pem'))
      ? { key: fs.readFileSync(path.join(sslDir, 'key.pem')), cert: fs.readFileSync(path.join(sslDir, 'cert.pem')) }
      : undefined,
    proxy: {
      '/api': {
        target: `https://127.0.0.1:${backendPort}`,
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
