import { reactive } from 'vue'

// 页面切换时 HomeView 会卸载；把推荐状态放在应用级模块中可避免返回首页后丢失结果。
export const recommendationState = reactive({
  query: '',
  searchMode: 'full_text',
  showFilters: false,
  filters: {
    genres: '',
    runtime_max_minutes: '',
    release_year_min: '',
    release_year_max: '',
    min_vote_average: ''
  },
  result: null,
  error: ''
})
