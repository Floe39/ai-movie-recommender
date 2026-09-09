<script setup>
import { computed, onMounted, ref, toRef } from 'vue'
import { api } from '../api/client'
import MovieCard from '../components/MovieCard.vue'
import StatusMessage from '../components/StatusMessage.vue'
import { recommendationState } from '../stores/recommendation'

const query = toRef(recommendationState, 'query')
const searchMode = toRef(recommendationState, 'searchMode')
const showFilters = toRef(recommendationState, 'showFilters')
const loading = ref(false)
const error = toRef(recommendationState, 'error')
const result = toRef(recommendationState, 'result')
const filters = recommendationState.filters
const todayMovies = ref([])
const todayLoading = ref(true)
// 两种入口对应不同的表达方式，切换后只更换示例，不覆盖用户已经输入的内容。
const queryPlaceholder = computed(() => searchMode.value === 'vector'
  ? '例如：想找一个小女孩和一匹狼的故事'
  : '例如：喜剧、两小时以内、评分 7 分以上')

function buildConditions() {
  // 空输入转为 null，避免把 NaN 或空字符串发送给后端的数值校验。
  const genres = filters.genres.split(',').map((genre) => genre.trim()).filter(Boolean)
  const numberOrNull = (value) => value === '' ? null : Number(value)
  return { genres, runtime_max_minutes: numberOrNull(filters.runtime_max_minutes), release_year_min: numberOrNull(filters.release_year_min), release_year_max: numberOrNull(filters.release_year_max), min_vote_average: numberOrNull(filters.min_vote_average) }
}

async function submit(useFilters = false) {
  error.value = ''
  loading.value = true
  try {
    const payload = { limit: 10, search_mode: searchMode.value }
    if (useFilters) payload.conditions = buildConditions()
    else payload.query = query.value
    result.value = await api.recommend(payload)
  } catch (requestError) { error.value = requestError.message } finally { loading.value = false }
}

async function loadTodayMovies() {
  // 后端会优先返回 SQLite 中当天缓存的片单。
  try { todayMovies.value = await api.getTodayMovies() } finally { todayLoading.value = false }
}

onMounted(loadTodayMovies)
</script>

<template>
  <section class="hero">
    <p class="eyebrow">观影推荐</p>
    <h1>今天想看什么？</h1>
    <p>说说你的心情和限制条件，找一部刚好适合现在的电影。</p>
    <form class="recommend-form" @submit.prevent="submit(false)">
      <label for="movie-query" class="sr-only">观影需求</label>
      <textarea id="movie-query" v-model="query" maxlength="500" :placeholder="queryPlaceholder" required />
      <button class="primary-button" :disabled="loading">{{ loading ? '正在找电影…' : '为我推荐' }}</button>
    </form>
    <div class="search-mode" role="group" aria-label="检索方式">
      <button type="button" :class="{ active: searchMode === 'full_text' }" @click="searchMode = 'full_text'">按类型、时长等条件找</button>
      <button type="button" :class="{ active: searchMode === 'vector' }" @click="searchMode = 'vector'">按故事描述找</button>
    </div>
    <button class="filter-toggle" @click="showFilters = !showFilters">{{ showFilters ? '收起条件筛选' : '使用条件筛选' }}</button>
    <form v-if="showFilters" class="filters" @submit.prevent="submit(true)">
      <label>类型（逗号分隔）<input v-model="filters.genres" placeholder="喜剧、动画" /></label>
      <label>最长时长（分钟）<input v-model="filters.runtime_max_minutes" type="number" min="40" max="360" /></label>
      <label>最早年份<input v-model="filters.release_year_min" type="number" min="1888" max="2100" /></label>
      <label>最晚年份<input v-model="filters.release_year_max" type="number" min="1888" max="2100" /></label>
      <label>最低评分<input v-model="filters.min_vote_average" type="number" min="0" max="10" step="0.1" /></label>
      <button class="secondary-button" :disabled="loading">按条件筛选</button>
    </form>
  </section>

  <section class="content-section" aria-live="polite">
    <StatusMessage v-if="error" type="error" :message="error" />
    <div v-else-if="loading" class="loading-panel"><span class="spinner" /> 正在核验候选影片…</div>
    <template v-else-if="result">
      <div class="section-heading result-heading"><h2>筛选结果</h2></div>
      <StatusMessage v-if="result.relaxation_suggestion" type="info" :message="result.relaxation_suggestion" />
      <div v-if="result.movies.length" class="movie-grid"><MovieCard v-for="movie in result.movies" :key="movie.tmdb_id" :movie="movie" /></div>
    </template>
  </section>

  <section class="today-section">
    <div class="section-heading"><h2>今日推荐</h2></div>
    <div v-if="todayLoading" class="today-loading">正在挑选今日电影…</div>
    <div v-else-if="todayMovies.length" class="today-grid"><MovieCard v-for="movie in todayMovies" :key="movie.tmdb_id" :movie="movie" today /></div>
  </section>
</template>
