<script setup>
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api/client'

const props = defineProps({ movie: { type: Object, required: true }, compact: Boolean, today: Boolean })
const emit = defineEmits(['watchlist-changed'])
const saving = ref(false)
const feedback = ref('')
const year = computed(() => props.movie.release_year || '上映年份未知')

async function addToWatchlist() {
  saving.value = true
  feedback.value = ''
  try {
    await api.addWatchlist({ movie_tmdb_id: props.movie.tmdb_id, status: 'want_to_watch' })
    feedback.value = '已加入想看片单'
    emit('watchlist-changed')
  } catch (error) {
    feedback.value = error.message
  } finally { saving.value = false }
}
</script>

<template>
  <article class="movie-card" :class="{ compact, today }">
    <RouterLink class="poster" :to="`/movies/${movie.tmdb_id}`" :aria-label="`查看${movie.title}详情`">
      <img v-if="movie.poster_url" :src="movie.poster_url" :alt="`${movie.title}海报`" loading="lazy" />
      <span v-else>暂无海报</span>
    </RouterLink>
    <div class="movie-content">
      <div class="movie-heading">
        <h3><RouterLink :to="`/movies/${movie.tmdb_id}`">{{ movie.title }}</RouterLink></h3>
        <span class="rating">★ {{ movie.vote_average?.toFixed(1) ?? '暂无' }}</span>
      </div>
      <p class="metadata">{{ year }} · {{ movie.runtime_minutes ? `${movie.runtime_minutes} 分钟` : '时长未知' }}</p>
      <p v-if="!today" class="genres">{{ movie.genres?.join(' · ') || '类型未知' }}</p>
      <p v-if="!compact && movie.overview" class="overview">{{ movie.overview }}</p>
      <p v-if="movie.recommendation_reason" class="reason"><b>推荐理由：</b>{{ movie.recommendation_reason }}</p>
      <p v-if="movie.matched_conditions?.length" class="matched">{{ movie.matched_conditions.join(' · ') }}</p>
      <p v-if="movie.is_stale" class="stale">当前显示的是缓存数据，TMDB 暂不可用。</p>
      <details v-if="movie.rag_sources?.length" class="rag-sources">
        <summary>语义匹配资料（{{ movie.rag_sources.length }}）</summary>
        <blockquote v-for="source in movie.rag_sources" :key="`${source.source_type}-${source.source_name}-${source.excerpt}`">
          <p>{{ source.excerpt }}</p>
          <footer><a v-if="source.source_url" :href="source.source_url" target="_blank" rel="noreferrer">{{ source.source_name }} ↗</a><span v-else>{{ source.source_name }}</span> · 匹配度 {{ Math.round(source.similarity * 100) }}%</footer>
        </blockquote>
      </details>
      <div v-if="!today" class="card-actions">
        <RouterLink class="text-button" :to="`/movies/${movie.tmdb_id}`">查看详情</RouterLink>
        <a class="text-button" :href="movie.tmdb_url" target="_blank" rel="noreferrer">TMDB 官方页 ↗</a>
        <button class="secondary-button" :disabled="saving" @click="addToWatchlist">{{ saving ? '保存中…' : '想看' }}</button>
      </div>
      <small v-if="feedback" class="inline-feedback">{{ feedback }}</small>
    </div>
  </article>
</template>
