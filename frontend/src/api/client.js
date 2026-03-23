import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Leads ──────────────────────────────────────────────────────────────────
export const getLeads        = (params = {}) => api.get('/leads/', { params }).then(r => r.data)
export const getMapPins      = ()            => api.get('/leads/map-pins').then(r => r.data)
export const getLead         = (id)          => api.get(`/leads/${id}`).then(r => r.data)
export const createLead      = (data)        => api.post('/leads/', data).then(r => r.data)
export const updateLead      = (id, data)    => api.patch(`/leads/${id}`, data).then(r => r.data)
export const deleteLead      = (id)          => api.delete(`/leads/${id}`).then(r => r.data)
export const getStats        = ()            => api.get('/leads/stats').then(r => r.data)
export const getFilterOptions = (params={})  => api.get('/leads/filters', { params }).then(r => r.data)
export const findEmailHunter = (id)          => api.post(`/leads/${id}/find-email`).then(r => r.data)

export const exportLeads = (params = {}) => {
  const qs = new URLSearchParams(params).toString()
  window.open(`/api/leads/export${qs ? '?' + qs : ''}`, '_blank')
}

// ── Scraper ────────────────────────────────────────────────────────────────
export const getCategories  = () => api.get('/scraper/categories').then(r => r.data)
export const getScrapeJobs  = () => api.get('/scraper/jobs').then(r => r.data)
export const getScrapeJob   = (id) => api.get(`/scraper/jobs/${id}`).then(r => r.data)

// ── Email ──────────────────────────────────────────────────────────────────
export const sendEmail = (data) => api.post('/email/send', data).then(r => r.data)

// ── Claude ─────────────────────────────────────────────────────────────────
export const draftEmail = (data) => api.post('/claude/draft-email', data).then(r => r.data)
