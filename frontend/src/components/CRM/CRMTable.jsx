import { useState, useEffect, useCallback } from 'react'
import {
  getLeads, getFilterOptions, updateLeadStatus,
  archiveLead, unarchiveLead, exportLeads,
} from '../../api/client'
import LeadDetail from '../Leads/LeadDetail'
import AddLeadModal from './AddLeadModal'

const PIPELINE_STATUSES = [
  { value: 'new',       label: '🆕 New',       cls: 'status-select-new' },
  { value: 'contacted', label: '📧 Contacted',  cls: 'status-select-contacted' },
  { value: 'replied',   label: '💬 Replied',    cls: 'status-select-replied' },
  { value: 'qualified', label: '✅ Qualified',  cls: 'status-select-qualified' },
  { value: 'converted', label: '🏆 Converted',  cls: 'status-select-converted' },
  { value: 'lost',      label: '❌ Lost',       cls: 'status-select-lost' },
]

const STATUS_CLS = Object.fromEntries(PIPELINE_STATUSES.map(s => [s.value, s.cls]))

function ScoreDots({ score }) {
  return (
    <div style={{ display: 'flex', gap: 2 }}>
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} style={{
          width: 5, height: 5, borderRadius: '50%', flexShrink: 0,
          background: i < score ? 'var(--gold)' : 'var(--border)',
        }} />
      ))}
    </div>
  )
}

function SortHeader({ field, label, sort, onSort, style }) {
  const active = sort.field === field
  return (
    <th className="crm-th sortable" onClick={() => onSort(field)} style={style}>
      {label}{active ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : ''}
    </th>
  )
}

function sortLeads(rows, sort) {
  return [...rows].sort((a, b) => {
    const dir = sort.dir === 'asc' ? 1 : -1
    if (sort.field === 'business_name') return dir * a.business_name.localeCompare(b.business_name)
    if (sort.field === 'score')         return dir * (a.score - b.score)
    if (sort.field === 'city')          return dir * (a.city || '').localeCompare(b.city || '')
    if (sort.field === 'status')        return dir * (a.status || '').localeCompare(b.status || '')
    if (sort.field === 'created_at') {
      return dir * (new Date(a.created_at) - new Date(b.created_at))
    }
    return 0
  })
}

export default function CRMTable({ showToast, onLeadUpdated }) {
  const [leads, setLeads]         = useState([])
  const [loading, setLoading]     = useState(false)
  const [options, setOptions]     = useState({ countries: [], states: [], cities: [], categories: [] })
  const [filters, setFilters]     = useState({
    search: '', country: '', state: '', city: '',
    category: '', status: '', email_source: '', showArchived: false,
  })
  const [sort, setSort]           = useState({ field: 'created_at', dir: 'desc' })
  const [detailId, setDetailId]   = useState(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [addOpen, setAddOpen]     = useState(false)

  // Load cascading filter options
  useEffect(() => {
    getFilterOptions({ country: filters.country, state: filters.state })
      .then(setOptions).catch(() => {})
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
      if (filters.email_source === 'none')    params.has_email = false
      if (filters.email_source === 'hunter')  params.email_source = 'hunter'
      if (filters.email_source === 'scraper') params.email_source = 'scraper'
      if (filters.showArchived) params.archived = true
      params.limit = 1000
      const data = await getLeads(params)
      setLeads(data.leads)
    } catch {
      showToast('Failed to load leads', 'error')
    } finally {
      setLoading(false)
    }
  }, [filters, showToast])

  useEffect(() => { load() }, [load])

  function setFilter(key, value) {
    setFilters(f => {
      const next = { ...f, [key]: value }
      // Reset downstream cascades
      if (key === 'country') { next.state = ''; next.city = '' }
      if (key === 'state')   { next.city = '' }
      return next
    })
  }

  function toggleSort(field) {
    setSort(s => s.field === field
      ? { field, dir: s.dir === 'asc' ? 'desc' : 'asc' }
      : { field, dir: 'asc' }
    )
  }

  async function handleStatusChange(lead, newStatus) {
    // Optimistic update
    setLeads(prev => prev.map(l => l.id === lead.id ? { ...l, status: newStatus } : l))
    try {
      await updateLeadStatus(lead.id, newStatus)
      onLeadUpdated?.()
    } catch {
      showToast('Failed to update status', 'error')
      load()
    }
  }

  async function handleArchive(lead) {
    try {
      if (lead.archived) {
        await unarchiveLead(lead.id)
        showToast('Lead restored')
      } else {
        await archiveLead(lead.id)
        showToast('Lead archived')
      }
      load()
      onLeadUpdated?.()
    } catch {
      showToast('Action failed', 'error')
    }
  }

  function openDetail(lead) {
    setDetailId(lead.id)
    setDetailOpen(true)
  }

  function closeDetail() {
    setDetailOpen(false)
    setTimeout(() => setDetailId(null), 250)
  }

  const sorted = sortLeads(leads, sort)

  return (
    <div className="crm-panel">
      {/* Filter bar */}
      <div className="crm-filters">
        <input
          type="text"
          placeholder="🔍 Search leads..."
          value={filters.search}
          onChange={e => setFilter('search', e.target.value)}
        />

        <select value={filters.country} onChange={e => setFilter('country', e.target.value)}>
          <option value="">All Countries</option>
          {options.countries.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <select value={filters.state} onChange={e => setFilter('state', e.target.value)}>
          <option value="">All States</option>
          {options.states.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <select value={filters.city} onChange={e => setFilter('city', e.target.value)}>
          <option value="">All Cities</option>
          {options.cities.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <select value={filters.category} onChange={e => setFilter('category', e.target.value)}>
          <option value="">All Categories</option>
          {options.categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <select value={filters.status} onChange={e => setFilter('status', e.target.value)}>
          <option value="">All Statuses</option>
          {PIPELINE_STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>

        <select value={filters.email_source} onChange={e => setFilter('email_source', e.target.value)}>
          <option value="">All Emails</option>
          <option value="hunter">⚡ Hunter.io</option>
          <option value="scraper">🔍 Free Scraper</option>
          <option value="none">No Email</option>
        </select>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-dim)', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={filters.showArchived}
            onChange={e => setFilter('showArchived', e.target.checked)}
          />
          Show Archived
        </label>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={() => exportLeads(filters)}>
            ↓ Excel
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => setAddOpen(true)}>
            + Add Lead
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div style={{
        padding: '6px 16px', fontSize: 11, color: 'var(--text-dim)',
        borderBottom: '1px solid var(--border)', background: 'var(--surface)',
        display: 'flex', gap: 16, flexShrink: 0,
      }}>
        <span>{loading ? 'Loading…' : `${sorted.length} leads`}</span>
        {PIPELINE_STATUSES.map(s => {
          const count = leads.filter(l => l.status === s.value).length
          return count > 0 ? (
            <span key={s.value} style={{ cursor: 'pointer' }} onClick={() => setFilter('status', filters.status === s.value ? '' : s.value)}>
              {s.label} <strong style={{ color: 'var(--mist)' }}>{count}</strong>
            </span>
          ) : null
        })}
      </div>

      {/* Table */}
      <div className="crm-table-wrap">
        <table className="crm-table">
          <thead>
            <tr>
              <th className="crm-th" style={{ width: 36 }}>#</th>
              <SortHeader field="business_name" label="Business"  sort={sort} onSort={toggleSort} />
              <SortHeader field="city"          label="Location"  sort={sort} onSort={toggleSort} style={{ width: 120 }} />
              <th className="crm-th">Category</th>
              <SortHeader field="score"         label="Score"     sort={sort} onSort={toggleSort} style={{ width: 90 }} />
              <th className="crm-th">Email</th>
              <th className="crm-th">Phone</th>
              <SortHeader field="status"        label="Pipeline"  sort={sort} onSort={toggleSort} style={{ width: 150 }} />
              <th className="crm-th" style={{ width: 100 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((lead, i) => (
              <tr key={lead.id} className={`crm-tr${lead.archived ? ' archived' : ''}`}>
                <td className="crm-td" style={{ color: 'var(--text-dim)', width: 36 }}>{i + 1}</td>

                <td className="crm-td">
                  <button className="crm-name-btn" onClick={() => openDetail(lead)}>
                    {lead.business_name}
                  </button>
                  {lead.contact_name && (
                    <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 1 }}>
                      {lead.contact_name}{lead.position ? ` · ${lead.position}` : ''}
                    </div>
                  )}
                </td>

                <td className="crm-td" style={{ width: 120 }}>
                  {[lead.city, lead.state].filter(Boolean).join(', ')}
                </td>

                <td className="crm-td" style={{ maxWidth: 130 }}>
                  {lead.category}
                </td>

                <td className="crm-td" style={{ width: 90 }}>
                  <ScoreDots score={lead.score} />
                </td>

                <td className="crm-td">
                  {lead.email ? (
                    <div>
                      <a href={`mailto:${lead.email}`} style={{ color: 'var(--glacial)', fontSize: 11 }}>
                        {lead.email}
                      </a>
                      {lead.email_source === 'hunter' && (
                        <span style={{
                          marginLeft: 4, fontSize: 9, background: '#78350f',
                          color: '#fcd34d', borderRadius: 4, padding: '1px 4px', fontWeight: 700,
                        }}>⚡</span>
                      )}
                    </div>
                  ) : (
                    <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>—</span>
                  )}
                </td>

                <td className="crm-td">
                  {lead.phone
                    ? <span style={{ fontSize: 11 }}>{lead.phone}</span>
                    : <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>—</span>
                  }
                </td>

                <td className="crm-td" style={{ width: 150 }}>
                  <select
                    className={`crm-status-select ${STATUS_CLS[lead.status] || 'status-select-new'}`}
                    value={lead.status || 'new'}
                    onChange={e => handleStatusChange(lead, e.target.value)}
                  >
                    {PIPELINE_STATUSES.map(s => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </td>

                <td className="crm-td" style={{ width: 100 }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button
                      className={`crm-action-btn ${lead.archived ? 'restore' : 'danger'}`}
                      title={lead.archived ? 'Restore lead' : 'Archive lead'}
                      onClick={() => handleArchive(lead)}
                    >
                      {lead.archived ? '↩' : '▽'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}

            {!loading && sorted.length === 0 && (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: 48, color: 'var(--text-dim)' }}>
                  No leads match your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Detail drawer — reuse existing LeadDetail */}
      <div className={`detail-panel${detailOpen ? ' open' : ''}`}>
        {detailId && (
          <LeadDetail
            leadId={detailId}
            onClose={closeDetail}
            onDeleted={() => { load(); closeDetail(); onLeadUpdated?.() }}
            onUpdated={() => { load(); onLeadUpdated?.() }}
            showToast={showToast}
          />
        )}
      </div>

      {/* Add Lead modal */}
      {addOpen && (
        <AddLeadModal
          onClose={() => setAddOpen(false)}
          onCreated={() => { load(); onLeadUpdated?.() }}
          showToast={showToast}
        />
      )}
    </div>
  )
}
