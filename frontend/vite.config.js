import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 浏览器只访问本项目后端；第三方模型和 TMDB Key 始终留在后端环境变量中。
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000'
    }
  }
})
