import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import HomeView from './views/HomeView.vue'
import MovieDetailView from './views/MovieDetailView.vue'
import WatchlistView from './views/WatchlistView.vue'
import HistoryView from './views/HistoryView.vue'
import KnowledgeView from './views/KnowledgeView.vue'
import './styles.css'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', component: HomeView, meta: { title: '为今晚找一部好电影' } },
    { path: '/movies/:tmdbId', component: MovieDetailView, props: true, meta: { title: '影片详情' } },
    { path: '/watchlist', component: WatchlistView, meta: { title: '我的片单' } },
    { path: '/history', component: HistoryView, meta: { title: '推荐历史' } },
    { path: '/knowledge', component: KnowledgeView, meta: { title: '资料库' } }
  ]
})

router.afterEach((to) => { document.title = `${to.meta.title} · 观影推荐助手` })
createApp(App).use(router).mount('#app')
