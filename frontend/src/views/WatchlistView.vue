<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api/client'
import MovieCard from '../components/MovieCard.vue'
import StatusMessage from '../components/StatusMessage.vue'

const items = ref([])
const movies = ref({})
const selectedStatus = ref('')
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true; error.value = ''
  try {
    items.value = await api.getWatchlist(selectedStatus.value || undefined)
    const detailPairs = await Promise.all(items.value.map(async (item) => [item.movie_tmdb_id, item.movie || await api.getMovie(item.movie_tmdb_id)]))
    movies.value = Object.fromEntries(detailPairs)
  } catch (requestError) { error.value = requestError.message } finally { loading.value = false }
}
async function update(item, status) { try { await api.updateWatchlist(item.movie_tmdb_id, { status }); await load() } catch (requestError) { error.value = requestError.message } }
async function remove(item) { if (window.confirm(`从片单移除《${movies.value[item.movie_tmdb_id]?.title || '这部电影'}》吗？`)) { try { await api.deleteWatchlist(item.movie_tmdb_id); await load() } catch (requestError) { error.value = requestError.message } } }
onMounted(load)
</script>

<template>
  <section class="content-section">
    <div class="section-heading"><div><p class="eyebrow">个人记录</p><h1>我的片单</h1></div><select v-model="selectedStatus" aria-label="按观看状态筛选" @change="load"><option value="">全部状态</option><option value="want_to_watch">想看</option><option value="watched">已看</option></select></div>
    <StatusMessage v-if="error" type="error" :message="error" />
    <div v-else-if="loading" class="loading-panel"><span class="spinner" /> 正在读取片单…</div>
    <div v-else-if="!items.length" class="empty-state"><h2>片单还是空的</h2><p>从推荐结果或影片详情页把电影加入“想看”。</p></div>
    <div v-else class="watchlist-list">
      <article v-for="item in items" :key="item.id" class="watchlist-row">
        <MovieCard v-if="movies[item.movie_tmdb_id]" :movie="movies[item.movie_tmdb_id]" compact />
        <div class="watchlist-controls"><span class="status-pill">{{ item.status === 'watched' ? '已看' : '想看' }}</span><p v-if="item.note">短评：{{ item.note }}</p><button v-if="item.status === 'want_to_watch'" class="secondary-button" @click="update(item, 'watched')">标记已看</button><button class="danger-button" @click="remove(item)">移除</button></div>
      </article>
    </div>
  </section>
</template>
