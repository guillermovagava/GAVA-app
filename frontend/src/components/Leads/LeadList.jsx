import { useState, useEffect, useCallback } from 'react'
import { getLeads, getFilterOptions, exportLeads } from '../../api/client'

const STATUSES = ['new', 'contacted', 'replied', 'meeting_booked', 'converted']

function ScoreDots({ score }) {
  return (
    <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
      {[...Array(10)].map((_, i) => (
        <div key={i} style={{
          width: 5, height: 5, borderRadius: '50%',
          background: i < score ? 'var(--gold)' : 'var(--border)',
          flexShrink: 0,
        }} />
      ))}
    </div>
  )
}

export default function LeadList({ selectedId, onSelect }) {
  const [leads, setLeads] = useState([])
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({ search: '', country: '', state: '', city: '', category: '', status: '' })
  const [options, setOptions] = useState({ countries: [], states: [], cities: [], categories: [] })
  const [loading, setLoading] = useState(false)

  // Load filter options — cascade: country → state → city
  useEffect(() => {
    const params = {}
    if (filters.country) params.country = filters.country
    if (filters.state)   params.state   = filters.state
    getFilterOptions(params).then(setOptions).catch(() => {})
  }, [filters.country, filters.state])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.search)   params.search   = filters.search
      if (filters.country)  params.country  = filters.country
      if (filters.state)    params.state    = filters.state
      if (filters.city)     params.city     = filters.city
      if (filters.category) params.category = filters.category
      if (filters.status)   params.status   = filters.status
      const data = await getLeads(params)
      setLeads(data.leads)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { load() }, [load])

  function set(key, val) {
    // Reset child filters when parent changes
    if (key === 'country') setFilters(f => ({ ...f, country: val, state: '', city: '' }))
    else if (key === 'state') setFilters(f => ({ ...f, state: val, city: '' }))
    else setFilters(f => ({ ...f, [key]: val }))
  }

  function handleExport() {
    const params = {}
    if (filters.country)  params.country  = filters.country
    if (filters.state)    params.state    = filters.state
    if (filters.city)     params.city     = filters.city
    if (filters.category) params.category = filters.category
    if (filters.status)   params.status   = filters.status
    exportLeads(params)
  }

  const COUNTRY_LABELS = { US: '🇺🇸 United States', CA: '🇨🇦 Canada', AU: '🇦🇺 Australia' }

  return (
    <>
      <div className="sidebar-filters">
        <input
          className="filter-input"
          placeholder="Search businesses, cities..."
          value={filters.search}
          onChange={e => set('search', e.target.value)}
        />

        {/* Country */}
        <select className="filter-select" value={filters.country} onChange={e => set('country', e.target.value)}>
          <option value="">All Countries</option>
          {options.countries.map(c => (
            <option key={c} value={c}>{COUNTRY_LABELS[c] || c}</option>
          ))}
        </select>

        <div className="filter-row">
          {/* State */}
          <select className="filter-select" value={filters.state} onChange={e => set('state', e.target.value)}>
            <option value="">All States</option>
            {options.states.map(s => <option key={s}>{s}</option>)}
          </select>
          {/* Status */}
          <select className="filter-select" value={filters.status} onChange={e => set('status', e.target.value)}>
            <option value="">All Status</option>
            {STATUSES.map(s => (
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            ))}
          </select>
        </div>

        <div className="filter-row">
          {/* City */}
          <select className="filter-select" value={filters.city} onChange={e => set('city', e.target.value)}>
            <option value="">All Cities</option>
            {options.cities.map(c => <option key={c}>{c}</option>)}
          </select>
          {/* Category */}
          <select className="filter-select" value={filters.category} onChange={e => set('category', e.target.value)}>
            <option value="">All Categories</option>
            {options.categories.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>

        {/* Footer row: count + export */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
            {loading ? 'Loading...' : `${total} lead${total !== 1 ? 's' : ''}`}
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleExport}
            title="Export to Excel"
            style={{ display: 'flex', alignItems: 'center', gap: 4 }}
          >
            ↓ Excel
          </button>
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
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div className="lead-card-name" style={{ flex: 1 }}>{lead.business_name}</div>
              <span className={`status-badge status-${lead.status}`} style={{ marginLeft: 6, flexShrink: 0 }}>
                {lead.status?.replace('_', ' ')}
              </span>
            </div>

            <div className="lead-card-meta" style={{ marginTop: 3 }}>
              <span>{lead.city}{lead.state ? `, ${lead.state}` : ''}{lead.country && lead.country !== 'US' ? ` · ${lead.country}` : ''}</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 5 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexWrap: 'wrap' }}>
                {lead.category && (
                  <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{lead.category}</span>
                )}
                {lead.email_source === 'hunter' && (
                  <span style={{ fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 3, background: '#1e3a5f', color: '#60a5fa', letterSpacing: '0.3px' }}>HUNTER</span>
                )}
                {lead.email_source === 'scraper' && (
                  <span style={{ fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 3, background: '#1a3a2a', color: '#4ade80', letterSpacing: '0.3px' }}>FREE</span>
                )}
                {!lead.email && (
                  <span style={{ fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 3, background: '#3a1a1a', color: '#f87171', letterSpacing: '0.3px' }}>NO EMAIL</span>
                )}
              </div>
              {lead.score !== undefined && <ScoreDots score={lead.score} />}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
