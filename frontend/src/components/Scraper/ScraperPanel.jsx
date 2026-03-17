import { useState, useEffect, useRef } from 'react'
import { getScrapeJobs, quickScrape } from '../../api/client'
import axios from 'axios'

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN',
  'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
  'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
  'TX','UT','VT','VA','WA','WV','WI','WY',
]
const CA_PROVINCES = ['BC','AB','ON','QC','NS','NB','MB','SK','PE','NL']

const SOURCE_INFO = {
  yelp: {
    name: 'Yelp',
    description: 'Best for local businesses, hotels, restaurants. Free (500 calls/day).',
    color: '#d32323',
  },
  google: {
    name: 'Google Places',
    description: 'Most accurate and complete coverage of US & Canada. $200/month free credit.',
    color: '#4285f4',
  },
  apollo: {
    name: 'Apollo.io',
    description: 'Finds HR/Recruiting contacts by name & email at companies. Free: 50 reveals/month.',
    color: '#7c3aed',
  },
}

export default function ScraperPanel({ showToast }) {
  const [sources, setSources] = useState({ yelp: false, google: false, apollo: false })
  const [allCategories, setAllCategories] = useState({ yelp: [], google: [], apollo: [] })
  const [activeSource, setActiveSource] = useState('yelp')
  const [selectedCats, setSelectedCats] = useState([])
  const [selectedStates, setSelectedStates] = useState([])
  const [jobs, setJobs] = useState([])
  const [running, setRunning] = useState(false)
  const pollRef = useRef(null)

  useEffect(() => {
    axios.get('/api/scraper/sources').then(r => setSources(r.data)).catch(() => {})
    axios.get('/api/scraper/categories').then(r => setAllCategories(r.data)).catch(() => {})
    loadJobs()
  }, [])

  // Reset category selection when source changes
  useEffect(() => { setSelectedCats([]) }, [activeSource])

  function loadJobs() {
    getScrapeJobs().then(setJobs).catch(() => {})
  }

  useEffect(() => {
    const hasRunning = jobs.some(j => j.status === 'running' || j.status === 'pending')
    if (hasRunning) {
      pollRef.current = setInterval(loadJobs, 3000)
    } else {
      clearInterval(pollRef.current)
    }
    return () => clearInterval(pollRef.current)
  }, [jobs])

  function toggleCat(label) {
    setSelectedCats(prev =>
      prev.includes(label) ? prev.filter(c => c !== label) : [...prev, label]
    )
  }

  function toggleState(s) {
    setSelectedStates(prev =>
      prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s]
    )
  }

  async function startScrape() {
    if (selectedCats.length === 0) { showToast('Select at least one business type', 'error'); return }
    if (selectedStates.length === 0) { showToast('Select at least one state/province', 'error'); return }
    setRunning(true)
    try {
      let started = 0
      for (const cat of selectedCats) {
        await quickScrape({ category_label: cat, states: selectedStates, source: activeSource })
        started++
      }
      showToast(`Started ${started} scrape job${started > 1 ? 's' : ''} via ${SOURCE_INFO[activeSource].name}`, 'success')
      loadJobs()
    } catch (e) {
      showToast('Failed to start: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setRunning(false)
    }
  }

  const categories = allCategories[activeSource] || []
  const activeJobs = jobs.filter(j => j.status === 'running' || j.status === 'pending')
  const doneJobs = jobs.filter(j => j.status === 'done' || j.status === 'failed')

  return (
    <div className="scraper-panel">
      <h2>Lead Scraper</h2>
      <p>Find businesses to recruit from across the US and Canada. Choose a data source, select business types and states, then click Start.</p>

      <div className="scraper-form">

        {/* Source selector */}
        <div>
          <label className="form-label">Data Source</label>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {Object.entries(SOURCE_INFO).map(([key, info]) => {
              const configured = sources[key]
              return (
                <div
                  key={key}
                  onClick={() => configured && setActiveSource(key)}
                  style={{
                    flex: '1 1 180px',
                    background: activeSource === key ? '#1e2540' : 'var(--surface2)',
                    border: `1px solid ${activeSource === key ? info.color : 'var(--border)'}`,
                    borderRadius: 8,
                    padding: '10px 12px',
                    cursor: configured ? 'pointer' : 'not-allowed',
                    opacity: configured ? 1 : 0.45,
                    transition: 'border-color 0.15s',
                  }}
                >
                  <div style={{ fontWeight: 700, color: info.color, fontSize: 13, marginBottom: 3 }}>
                    {info.name}
                    {!configured &&
                      <span style={{ fontSize: 10, color: 'var(--text-dim)', fontWeight: 400, marginLeft: 6 }}>
                        (no API key)
                      </span>
                    }
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.4 }}>
                    {info.description}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Category picker */}
        <div>
          <label className="form-label">Business Types</label>
          {categories.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
              Add your {SOURCE_INFO[activeSource].name} API key in the .env file to enable this source.
            </div>
          ) : (
            <div className="checkbox-grid">
              {categories.map(cat => (
                <label
                  key={cat.label}
                  className={`checkbox-item${selectedCats.includes(cat.label) ? ' checked' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={selectedCats.includes(cat.label)}
                    onChange={() => toggleCat(cat.label)}
                  />
                  {cat.label}
                </label>
              ))}
            </div>
          )}
        </div>

        {/* State/province picker */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <label className="form-label" style={{ marginBottom: 0 }}>States &amp; Provinces</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedStates([...US_STATES, ...CA_PROVINCES])}>All</button>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedStates([])}>Clear</button>
            </div>
          </div>
          <div style={{ marginBottom: 5, fontSize: 11, color: 'var(--text-dim)' }}>United States</div>
          <div className="state-grid" style={{ marginBottom: 10 }}>
            {US_STATES.map(s => (
              <span key={s} className={`state-tag${selectedStates.includes(s) ? ' selected' : ''}`} onClick={() => toggleState(s)}>{s}</span>
            ))}
          </div>
          <div style={{ marginBottom: 5, fontSize: 11, color: 'var(--text-dim)' }}>Canada</div>
          <div className="state-grid">
            {CA_PROVINCES.map(s => (
              <span key={s} className={`state-tag${selectedStates.includes(s) ? ' selected' : ''}`} onClick={() => toggleState(s)}>{s}</span>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-primary" onClick={startScrape} disabled={running} style={{ minWidth: 140 }}>
            {running
              ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Starting...</>
              : `Search via ${SOURCE_INFO[activeSource]?.name}`}
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
            {selectedCats.length} type{selectedCats.length !== 1 ? 's' : ''} &times; {selectedStates.length} location{selectedStates.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {activeJobs.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            Running <span className="spinner" style={{ width: 12, height: 12 }} />
          </div>
          <div className="jobs-list">{activeJobs.map(j => <JobCard key={j.id} job={j} />)}</div>
        </div>
      )}

      {doneJobs.length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            Completed
            <button className="btn btn-secondary btn-sm" style={{ marginLeft: 10 }} onClick={loadJobs}>Refresh</button>
          </div>
          <div className="jobs-list">{doneJobs.slice(0, 20).map(j => <JobCard key={j.id} job={j} />)}</div>
        </div>
      )}
    </div>
  )
}

function JobCard({ job }) {
  const duration = job.started_at && job.finished_at
    ? Math.round((new Date(job.finished_at) - new Date(job.started_at)) / 1000) + 's'
    : null
  return (
    <div className="job-card">
      <div className="job-info">
        <div className="job-title">{job.category} — {job.location}</div>
        <div className="job-meta">
          {job.leads_found > 0 && `${job.leads_found} leads · `}
          {duration && `${duration} · `}
          {job.created_at && new Date(job.created_at).toLocaleString()}
          {job.error && <span style={{ color: '#fca5a5' }}> · {job.error}</span>}
        </div>
      </div>
      <span className={`job-status job-${job.status}`}>{job.status}</span>
    </div>
  )
}
