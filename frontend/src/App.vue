<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <RouterLink class="brand" to="/" aria-label="返回推荐页">
        <span class="brand-mark">▶</span><span>观影推荐助手</span>
      </RouterLink>
      <nav aria-label="主导航">
        <RouterLink to="/">推荐</RouterLink>
        <RouterLink to="/watchlist">我的片单</RouterLink>
        <RouterLink to="/history">推荐历史</RouterLink>
        <RouterLink to="/knowledge">资料库</RouterLink>
      </nav>
    </header>

    <main><RouterView /></main>

    <footer>
      <p>影片信息、海报与评分由 <a href="https://www.themoviedb.org" target="_blank" rel="noreferrer">TMDB</a> 提供。</p>
      <p>本产品使用 TMDB API，但未获得 TMDB 的认可或认证。</p>
      <p class="tmdb-required-attribution">This product uses the TMDB API but is not endorsed or certified by TMDB.</p>
    </footer>
  </div>
</template>
