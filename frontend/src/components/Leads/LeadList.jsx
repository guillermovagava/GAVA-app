import { useState, useEffect, useCallback } from 'react'
import { getLeads, getFilterOptions } from '../../api/client'

const STATUSES = ['new', 'contacted', 'replied', 'meeting_booked', 'converted']

export default function LeadList({ selectedId, onSelect }) {
  const [leads, setLeads] = useState([])
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({ search: '', state: '', category: '', status: '' })
  const [options, setOptions] = useState({ states: [], categories: [] })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getFilterOptions().then(setOptions).catch(() => {})
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.search)   params.search   = filters.search
      if (filters.state)    params.state    = filters.state
      if (filters.category) params.category = filters.category
      if (filters.status)   params.status   = filters.status
      const data = await getLeads(params)
      setLeads(data.leads)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    load()
  }, [load])

  function set(key, val) {
    setFilters(f => ({ ...f, [key]: val }))
  }

  return (
    <>
      <div className="sidebar-filters">
        <input
          className="filter-input"
          placeholder="Search businesses, cities..."
          value={filters.search}
          onChange={e => set('search', e.target.value)}
        />
        <div className="filter-row">
          <select className="filter-select" value={filters.state} onChange={e => set('state', e.target.value)}>
            <option value="">All States</option>
            {options.states.map(s => <option key={s}>{s}</option>)}
          </select>
          <select className="filter-select" value={filters.status} onChange={e => set('status', e.target.value)}>
            <option value="">All Status</option>
            {STATUSES.map(s => (
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            ))}
          </select>
        </div>
        <select className="filter-select" value={filters.category} onChange={e => set('category', e.target.value)}>
          <option value="">All Categories</option>
          {options.categories.map(c => <option key={c}>{c}</option>)}
        </select>
        <div style={{ fontSize: 11, color: 'var(--text-dim)', paddingLeft: 2 }}>
          {loading ? 'Loading...' : `${total} lead${total !== 1 ? 's' : ''}`}
        </div>
      </div>

      <div className="sidebar-lead-list">
        {leads.length === 0 && !loading && (
          <div className="empty-state">
            <div style={{ fontSize: 28 }}>📋</div>
            <p>No leads yet. Run the scraper to find businesses!</p>
          </div>
        )}
        {leads.map(lead => (
          <div
            key={lead.id}
            className={`lead-card${selectedId === lead.id ? ' selected' : ''}`}
            onClick={() => onSelect(lead)}
          >
            <div className="lead-card-name">{lead.business_name}</div>
            <div className="lead-card-meta">
              <span>{lead.city}{lead.state ? `, ${lead.state}` : ''}</span>
              <span className={`status-badge status-${lead.status}`}>{lead.status?.replace('_', ' ')}</span>
            </div>
            {lead.category && (
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 3 }}>{lead.category}</div>
            )}
          </div>
        ))}
      </div>
    </>
  )
}
