import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:5050/api'
})

export const runScan = (path) => api.post('/scan', { path, source: 'local' })
export const autoTag = () => api.post('/tag/auto')
export const fetchEvidence = (params = {}) => api.get('/evidence', { params })
export const fetchTimeline = () => api.get('/timeline')
export const fetchGraph = () => api.get('/graph')
export const fetchInconsistencies = () => api.get('/analysis/inconsistencies')
export const fetchScenarios = () => api.get('/analysis/scenarios')
export const fetchPrivacy = () => api.get('/analysis/privacy')
export const fetchReport = () => api.get('/analysis/report')
export const runSearch = (q) => api.get('/search', { params: { q } })

export default api
