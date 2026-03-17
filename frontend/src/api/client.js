import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Leads ─────────────────────────────────────────────────────────────────
export const getLeads = (params = {}) => api.get('/leads/', { params }).then(r => r.data)
export const getMapPins = () => api.get('/leads/map-pins').then(r => r.data)
export const getLead = (id) => api.get(`/leads/${id}`).then(r => r.data)
export const createLead = (data) => api.post('/leads/', data).then(r => r.data)
export const updateLead = (id, data) => api.patch(`/leads/${id}`, data).then(r => r.data)
export const deleteLead = (id) => api.delete(`/leads/${id}`).then(r => r.data)
export const getStats = () => api.get('/leads/stats').then(r => r.data)
export const getFilterOptions = () => api.get('/leads/filters').then(r => r.data)

// ── Scraper ───────────────────────────────────────────────────────────────
export const getCategories = () => api.get('/scraper/categories').then(r => r.data)
export const quickScrape = (data) => api.post('/scraper/quick', data).then(r => r.data)
export const getScrapeJobs = () => api.get('/scraper/jobs').then(r => r.data)
export const getScrapeJob = (id) => api.get(`/scraper/jobs/${id}`).then(r => r.data)

// ── Email ─────────────────────────────────────────────────────────────────
export const sendEmail = (data) => api.post('/email/send', data).then(r => r.data)

// ── Claude ────────────────────────────────────────────────────────────────
export const draftEmail = (data) => api.post('/claude/draft-email', data).then(r => r.data)
