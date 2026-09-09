<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import StatusMessage from '../components/StatusMessage.vue'

const status = ref(null)
const loading = ref(true)
const seeding = ref(false)
const error = ref('')

// 页面只管理演示影片简介，避免把未参与推荐的资料入口暴露给用户。
async function load() {
  loading.value = true
  error.value = ''
  try { status.value = await api.getRagStatus() } catch (requestError) { error.value = requestError.message } finally { loading.value = false }
}

// 导入接口可重复调用：同一 TMDB 影片会覆盖旧简介与旧向量，不会重复累积。
async function seedDemo() {
  seeding.value = true
  error.value = ''
  try {
    const result = await api.seedDemoSynopses()
    await load()
    window.alert(`已导入 ${result.imported_movies} 部真实影片简介，并建立 ${result.indexed_chunks} 个向量片段。`)
  } catch (requestError) { error.value = requestError.message } finally { seeding.value = false }
}

onMounted(load)
</script>

<template>
  <section class="content-section">
    <div class="section-heading"><div><p class="eyebrow">故事资料</p><h1>影片简介库</h1></div></div>
    <StatusMessage v-if="error" type="error" :message="error" />
    <div v-else-if="loading" class="loading-panel"><span class="spinner" /> 正在读取影片简介库…</div>
    <template v-else>
      <StatusMessage :type="status.embedding_configured ? 'info' : 'error'" :message="status.embedding_configured ? `已导入 ${status.synopsis_count} 部演示影片简介、${status.chunk_count} 个向量片段。` : `已导入 ${status.synopsis_count} 部演示影片简介；配置 DASHSCOPE_API_KEY 后才能按故事描述找。`" />
      <div class="seed-panel"><div><h2>导入演示影片简介</h2><p>从 TMDB 读取少量真实简介，供“按故事描述找”使用。</p></div><button class="secondary-button" :disabled="seeding" @click="seedDemo">{{ seeding ? '正在导入…' : '导入真实简介' }}</button></div>
    </template>
  </section>
</template>
