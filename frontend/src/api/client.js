const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

/** 将后端的统一错误响应转换为可直接展示的错误信息。 */
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options
  })
  if (response.status === 204) return null
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.message || '请求失败，请稍后重试。')
  return payload
}

export const api = {
  recommend: (payload) => request('/api/recommendations', { method: 'POST', body: JSON.stringify(payload) }),
  getTodayMovies: () => request('/api/movies/today?limit=5'),
  getMovie: (id) => request(`/api/movies/${id}`),
  getWatchlist: (status) => request(`/api/watchlist${status ? `?status_filter=${status}` : ''}`),
  addWatchlist: (payload) => request('/api/watchlist', { method: 'POST', body: JSON.stringify(payload) }),
  updateWatchlist: (id, payload) => request(`/api/watchlist/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteWatchlist: (id) => request(`/api/watchlist/${id}`, { method: 'DELETE' }),
  getHistory: () => request('/api/recommendations/history'),
  getRagStatus: () => request('/api/rag/status'),
  seedDemoSynopses: () => request('/api/rag/demo-synopses/seed', { method: 'POST' })
}
