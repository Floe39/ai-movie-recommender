<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import MovieCard from '../components/MovieCard.vue'
import StatusMessage from '../components/StatusMessage.vue'

const entries = ref([])
const selected = ref(null)
const selectedMovies = ref([])
const loading = ref(true)
const error = ref('')

async function openHistory(entry) {
  selected.value = entry; error.value = ''
  try { selectedMovies.value = await Promise.all(entry.movie_tmdb_ids.map((id) => api.getMovie(id))) } catch (requestError) { error.value = requestError.message }
}
async function load() {
  loading.value = true; error.value = ''
  try { entries.value = await api.getHistory(); if (entries.value[0]) await openHistory(entries.value[0]) } catch (requestError) { error.value = requestError.message } finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <section class="content-section">
    <div class="section-heading"><div><p class="eyebrow">可回放的结果</p><h1>推荐历史</h1></div></div>
    <StatusMessage v-if="error" type="error" :message="error" />
    <div v-else-if="loading" class="loading-panel"><span class="spinner" /> 正在读取历史…</div>
    <div v-else-if="!entries.length" class="empty-state"><h2>还没有推荐记录</h2><p>完成一次推荐后，这里会保存当时的需求和影片结果。</p></div>
    <div v-else class="history-layout">
      <aside class="history-list"><button v-for="entry in entries" :key="entry.id" :class="{ active: selected?.id === entry.id }" @click="openHistory(entry)"><b>{{ entry.query }}</b><small>{{ new Date(entry.created_at).toLocaleString() }}</small></button></aside>
      <div><p v-if="selected" class="condition-summary">筛选条件：{{ selected.parsed_conditions.genres?.join('、') || '未指定类型' }}{{ selected.parsed_conditions.runtime_max_minutes ? `，不超过 ${selected.parsed_conditions.runtime_max_minutes} 分钟` : '' }}</p><div class="movie-grid"><MovieCard v-for="movie in selectedMovies" :key="movie.tmdb_id" :movie="movie" /></div></div>
    </div>
  </section>
</template>
