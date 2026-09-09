<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api/client'
import StatusMessage from '../components/StatusMessage.vue'

const props = defineProps({ tmdbId: { type: [String, Number], required: true } })
const movie = ref(null)
const loading = ref(true)
const error = ref('')
const feedback = ref('')

async function loadMovie() {
  loading.value = true; error.value = ''; feedback.value = ''
  try { movie.value = await api.getMovie(props.tmdbId) } catch (requestError) { error.value = requestError.message } finally { loading.value = false }
}
async function save(status) {
  try { await api.addWatchlist({ movie_tmdb_id: movie.value.tmdb_id, status }); feedback.value = status === 'watched' ? '已标记为看过' : '已加入想看' } catch (requestError) { feedback.value = requestError.message }
}
onMounted(loadMovie)
watch(() => props.tmdbId, loadMovie)
</script>

<template>
  <section class="content-section detail-page">
    <RouterLink class="back-link" to="/">← 返回推荐</RouterLink>
    <div v-if="loading" class="loading-panel"><span class="spinner" /> 正在加载影片详情…</div>
    <StatusMessage v-else-if="error" type="error" :message="error" />
    <article v-else-if="movie" class="detail-card">
      <div class="detail-poster poster"><img v-if="movie.poster_url" :src="movie.poster_url" :alt="`${movie.title}海报`" /><span v-else>暂无海报</span></div>
      <div>
        <p class="eyebrow">TMDB #{{ movie.tmdb_id }}</p>
        <h1>{{ movie.title }}</h1>
        <p class="detail-meta">{{ movie.release_year || '年份未知' }} · {{ movie.runtime_minutes ? `${movie.runtime_minutes} 分钟` : '时长未知' }} · ★ {{ movie.vote_average?.toFixed(1) ?? '暂无评分' }}</p>
        <p class="genres">{{ movie.genres.join(' · ') || '类型未知' }}</p>
        <p class="detail-overview">{{ movie.overview || '暂无影片简介。' }}</p>
        <StatusMessage v-if="movie.is_stale" type="info" :message="`TMDB 暂不可用，显示的是 ${new Date(movie.data_updated_at).toLocaleDateString()} 缓存的数据。`" />
        <div class="card-actions"><button class="primary-button" @click="save('want_to_watch')">加入想看</button><button class="secondary-button" @click="save('watched')">标记已看</button><a class="text-button" :href="movie.tmdb_url" target="_blank" rel="noreferrer">在 TMDB 查看 ↗</a></div>
        <small v-if="feedback" class="inline-feedback">{{ feedback }}</small>
      </div>
    </article>
  </section>
</template>
