import { useState, useEffect, useCallback } from 'react'
import { getLeads, getFilterOptions, exportLeads } from '../../api/client'
import axios from 'axios'

const STATUSES = ['new', 'contacted', 'replied', 'meeting_booked', 'converted']
const COUNTRY_LABELS = { US: '🇺🇸 United States', CA: '🇨🇦 Canada', AU: '🇦🇺 Australia' }

function ScoreDots({ score }) {
  return (
    <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
      {[...Array(10)].map((_, i) => (
        <div key={i} style={{
          width: 5, height: 5, borderRadius: '50%', flexShrink: 0,
          background: i < score ? 'var(--gold)' : 'var(--border)',
        }} />
      ))}
    </div>
  )
}

export default function LeadList({ selectedId, onSelect }) {
  const [leads, setLeads]     = useState([])
  const [total, setTotal]     = useState(0)
  const [filters, setFilters] = useState({ search: '', country: '', state: '', city: '', category: '', status: '', email_source: '', sort: '' })
  const [options, setOptions] = useState({ countries: [], states: [], cities: [], categories: [] })
  const [loading, setLoading] = useState(false)

  // Bulk Hunter state
  const [bulkMode, setBulkMode]       = useState(false)
  const [selected, setSelected]       = useState([])   // list of lead IDs
  const [running, setRunning]         = useState(false)
  const [bulkResult, setBulkResult]   = useState(null) // { found, processed }

  // Cascade filter options
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
      if (filters.search)       params.search       = filters.search
      if (filters.country)      params.country      = filters.country
      if (filters.state)        params.state        = filters.state
      if (filters.city)         params.city         = filters.city
      if (filters.category)     params.category     = filters.category
      if (filters.status)       params.status       = filters.status
      if (filters.email_source) params.email_source = filters.email_source
      if (filters.sort)         params.sort         = filters.sort
      const data = await getLeads(params)
      setLeads(data.leads)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => { load() }, [load])

  // Reset selection when leaving bulk mode
  useEffect(() => { if (!bulkMode) setSelected([]) }, [bulkMode])

  function set(key, val) {
    if (key === 'country') setFilters(f => ({ ...f, country: val, state: '', city: '' }))
    else if (key === 'state') setFilters(f => ({ ...f, state: val, city: '' }))
    else setFilters(f => ({ ...f, [key]: val }))
  }

  function toggleSelect(id) {
    setSelected(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id])
  }

  function selectAll() { setSelected(leads.map(l => l.id)) }
  function clearSelection() { setSelected([]) }

  async function runBulkHunter() {
    if (selected.length === 0) return
    setRunning(true)
    setBulkResult(null)
    try {
      const r = await axios.post('/api/leads/bulk-find-email', { lead_ids: selected })
      setBulkResult(r.data)
      load() // refresh list
    } catch (e) {
      console.error(e)
    } finally {
      setRunning(false)
    }
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

  return (
    <>
      <div className="sidebar-filters">
        <input className="filter-input" placeholder="Search businesses, cities..."
          value={filters.search} onChange={e => set('search', e.target.value)} />

        <select className="filter-select" value={filters.country} onChange={e => set('country', e.target.value)}>
          <option value="">All Countries</option>
          {options.countries.map(c => <option key={c} value={c}>{COUNTRY_LABELS[c] || c}</option>)}
        </select>

        <div className="filter-row">
          <select className="filter-select" value={filters.state} onChange={e => set('state', e.target.value)}>
            <option value="">All States</option>
            {options.states.map(s => <option key={s}>{s}</option>)}
          </select>
          <select className="filter-select" value={filters.status} onChange={e => set('status', e.target.value)}>
            <option value="">All Status</option>
            {STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </select>
        </div>

        <div className="filter-row">
          <select className="filter-select" value={filters.city} onChange={e => set('city', e.target.value)}>
            <option value="">All Cities</option>
            {options.cities.map(c => <option key={c}>{c}</option>)}
          </select>
          <select className="filter-select" value={filters.category} onChange={e => set('category', e.target.value)}>
            <option value="">All Categories</option>
            {options.categories.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>

        {/* Email source filter */}
        <select className="filter-select" value={filters.email_source} onChange={e => set('email_source', e.target.value)}>
          <option value="">All Emails</option>
          <option value="hunter">⚡ Via Hunter.io</option>
          <option value="scraper">🆓 Via Free Scraper</option>
          <option value="none">❌ No Email Yet</option>
        </select>

        {/* Sort */}
        <select className="filter-select" value={filters.sort} onChange={e => set('sort', e.target.value)}>
          <option value="">Sort: Newest First</option>
          <option value="score_desc">Sort: Score ↑ High to Low</option>
          <option value="score_asc">Sort: Score ↓ Low to High</option>
          <option value="name_asc">Sort: A → Z Name</option>
        </select>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
          <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
            {loading ? 'Loading...' : `${total} lead${total !== 1 ? 's' : ''}`}
          </div>
          <div style={{ display: 'flex', gap: 5 }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setBulkMode(b => !b)}
              style={bulkMode ? { color: 'var(--gold)', borderColor: 'var(--gold-dim)' } : {}}
            >
              {bulkMode ? '✕ Cancel' : '⚡ Hunter'}
            </button>
            <button className="btn btn-secondary btn-sm" onClick={handleExport} title="Export to Excel">
              ↓ Excel
            </button>
          </div>
        </div>

        {/* Bulk Hunter toolbar */}
        {bulkMode && (
          <div style={{
            background: 'rgba(200,169,110,0.08)', border: '1px solid var(--gold-dim)',
            borderRadius: 6, padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8,
          }}>
            <div style={{ fontSize: 11, color: 'var(--gold)', fontWeight: 600, letterSpacing: '0.05em' }}>
              ⚡ HUNTER BULK MODE
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              Select leads below, then run Hunter to find their HR emails. Tip: filter by "No Email" first.
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <button className="btn btn-secondary btn-sm" onClick={selectAll}>Select All ({leads.length})</button>
              <button className="btn btn-secondary btn-sm" onClick={clearSelection}>Clear</button>
            </div>
            {selected.length > 0 && (
              <button
                className="btn btn-primary"
                onClick={runBulkHunter}
                disabled={running}
                style={{ width: '100%', justifyContent: 'center', display: 'flex', alignItems: 'center', gap: 6 }}
              >
                {running
                  ? <><span className="spinner" style={{ width: 13, height: 13 }} /> Searching {selected.length} leads...</>
                  : `⚡ Run Hunter on ${selected.length} lead${selected.length !== 1 ? 's' : ''}`}
              </button>
            )}
            {bulkResult && (
              <div style={{ fontSize: 11, color: 'var(--gold)', textAlign: 'center' }}>
                ✓ Found {bulkResult.found} emails out of {bulkResult.processed} leads searched
              </div>
            )}
          </div>
        )}
      </div>

      <div className="sidebar-lead-list">
        {leads.length === 0 && !loading && (
          <div className="empty-state">
            <div style={{ fontSize: 28 }}>📋</div>
            <p>No leads yet. Run the scraper to find businesses!</p>
          </div>
        )}
        {leads.map(lead => {
          const isSelected = selected.includes(lead.id)
          return (
            <div
              key={lead.id}
              className={`lead-card${selectedId === lead.id && !bulkMode ? ' selected' : ''}${isSelected ? ' selected' : ''}`}
              onClick={() => bulkMode ? toggleSelect(lead.id) : onSelect(lead)}
              style={bulkMode ? { cursor: 'pointer' } : {}}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                {bulkMode && (
                  <div style={{
                    width: 16, height: 16, borderRadius: 4, border: '2px solid',
                    borderColor: isSelected ? 'var(--gold)' : 'var(--border)',
                    background: isSelected ? 'var(--gold)' : 'transparent',
                    flexShrink: 0, marginRight: 8, marginTop: 2,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}>
                    {isSelected && <span style={{ fontSize: 10, color: 'var(--navy)', fontWeight: 900 }}>✓</span>}
                  </div>
                )}
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
                  {lead.category && <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{lead.category}</span>}
                  {lead.email_source === 'hunter' && (
                    <span style={{ fontSize: 9, fontWeight: 700, padding: '1px 5px', borderRadius: 3, background: '#1e3a5f', color: '#60a5fa', letterSpacing: '0.3px' }}>⚡ HUNTER</span>
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
          )
        })}
      </div>
    </>
  )
}
