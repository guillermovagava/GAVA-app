import { useState, useEffect, useRef } from 'react'
import { getScrapeJobs } from '../../api/client'
import axios from 'axios'

const COUNTRIES = [
  { code: 'US', label: '🇺🇸 United States' },
  { code: 'CA', label: '🇨🇦 Canada' },
  { code: 'AU', label: '🇦🇺 Australia' },
]

const STATES_BY_COUNTRY = {
  US: ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN',
       'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
       'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
       'TX','UT','VT','VA','WA','WV','WI','WY'],
  CA: ['BC','AB','ON','QC','NS','NB','MB','SK','PE','NL'],
  AU: ['NSW','VIC','QLD','WA','SA','TAS','NT','ACT'],
}

export default function ScraperPanel({ showToast }) {
  const [categories, setCategories]         = useState([])
  const [status, setStatus]                 = useState({ google_places: false, hunter: false })
  const [selectedCats, setSelectedCats]     = useState([])
  const [selectedCountries, setSelectedCountries] = useState(['US'])
  const [selectedStates, setSelectedStates] = useState([])
  const [customCities, setCustomCities]     = useState('')   // free-text cities
  const [resultsPerCity, setResultsPerCity] = useState(20)
  const [jobs, setJobs]                     = useState([])
  const [running, setRunning]               = useState(false)
  const pollRef = useRef(null)

  useEffect(() => {
    axios.get('/api/scraper/categories').then(r => setCategories(r.data)).catch(() => {})
    axios.get('/api/scraper/status').then(r => setStatus(r.data)).catch(() => {})
    loadJobs()
  }, [])

  useEffect(() => {
    const hasRunning = jobs.some(j => j.status === 'running' || j.status === 'pending')
    if (hasRunning) { pollRef.current = setInterval(loadJobs, 3000) }
    else { clearInterval(pollRef.current) }
    return () => clearInterval(pollRef.current)
  }, [jobs])

  function loadJobs() { getScrapeJobs().then(setJobs).catch(() => {}) }

  function toggleCat(label) {
    setSelectedCats(p => p.includes(label) ? p.filter(c => c !== label) : [...p, label])
  }

  function toggleCountry(code) {
    setSelectedCountries(p => {
      const next = p.includes(code) ? p.filter(c => c !== code) : [...p, code]
      // Remove states that no longer belong to any selected country
      setSelectedStates(s => s.filter(st =>
        next.some(c => STATES_BY_COUNTRY[c]?.includes(st))
      ))
      return next
    })
  }

  function toggleState(s) {
    setSelectedStates(p => p.includes(s) ? p.filter(x => x !== s) : [...p, s])
  }

  function selectAllStates() {
    const all = selectedCountries.flatMap(c => STATES_BY_COUNTRY[c] || [])
    setSelectedStates(all)
  }

  // Parse custom cities text into location strings
  function parseCustomCities() {
    if (!customCities.trim()) return []
    return customCities
      .split('\n')
      .map(l => l.trim())
      .filter(l => l.length > 0)
  }

  async function startScrape() {
    if (!status.google_places) {
      showToast('Add GOOGLE_PLACES_API_KEY to .env first', 'error'); return
    }
    if (selectedCats.length === 0) { showToast('Select at least one business type', 'error'); return }

    const customLocs = parseCustomCities()
    const hasStates  = selectedStates.length > 0
    const hasCities  = customLocs.length > 0

    if (!hasStates && !hasCities) {
      showToast('Select at least one state or enter a custom city', 'error'); return
    }

    setRunning(true)
    try {
      for (const cat of selectedCats) {
        const payload = {
          category_label: cat,
          states: selectedStates,
          custom_locations: customLocs,
          max_results_per_city: resultsPerCity,
        }
        await axios.post('/api/scraper/run', payload)
      }
      showToast(`Started ${selectedCats.length} search job${selectedCats.length > 1 ? 's' : ''}`, 'success')
      loadJobs()
    } catch (e) {
      showToast('Failed to start: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setRunning(false)
    }
  }

  const visibleStates = selectedCountries.flatMap(c => STATES_BY_COUNTRY[c] || [])
  const activeJobs = jobs.filter(j => j.status === 'running' || j.status === 'pending')
  const doneJobs   = jobs.filter(j => j.status === 'done'    || j.status === 'failed')

  return (
    <div className="scraper-panel">
      <h2>Lead Scraper</h2>
      <p>Search Google Maps for businesses to recruit from, then find their HR contact emails.</p>

      {/* API status pills */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <StatusPill label="Google Places" ok={status.google_places}
          okText="Connected" failText="Missing API key — add GOOGLE_PLACES_API_KEY to .env" />
        <StatusPill label="Hunter.io" ok={status.hunter} warn
          okText="Connected — verified emails" failText="Not set — using free website scanner" />
      </div>

      <div className="scraper-form">

        {/* 1 — Business types */}
        <div>
          <label className="form-label">Business Types</label>
          <div className="checkbox-grid">
            {categories.map(cat => (
              <label key={cat.label} className={`checkbox-item${selectedCats.includes(cat.label) ? ' checked' : ''}`}>
                <input type="checkbox" checked={selectedCats.includes(cat.label)} onChange={() => toggleCat(cat.label)} />
                {cat.label}
              </label>
            ))}
          </div>
        </div>

        {/* 2 — Countries */}
        <div>
          <label className="form-label">Countries</label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {COUNTRIES.map(c => (
              <button
                key={c.code}
                onClick={() => toggleCountry(c.code)}
                style={{
                  padding: '6px 14px', borderRadius: 6, border: '1px solid',
                  cursor: 'pointer', fontSize: 12, fontWeight: 600,
                  background: selectedCountries.includes(c.code) ? 'var(--gold)' : 'var(--surface2)',
                  color: selectedCountries.includes(c.code) ? 'var(--navy)' : 'var(--text-dim)',
                  borderColor: selectedCountries.includes(c.code) ? 'var(--gold)' : 'var(--border)',
                  transition: 'all 0.15s',
                }}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        {/* 3 — States / Provinces */}
        {visibleStates.length > 0 && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <label className="form-label" style={{ marginBottom: 0 }}>States &amp; Provinces</label>
              <div style={{ display: 'flex', gap: 6 }}>
                <button className="btn btn-secondary btn-sm" onClick={selectAllStates}>All</button>
                <button className="btn btn-secondary btn-sm" onClick={() => setSelectedStates([])}>Clear</button>
              </div>
            </div>
            {selectedCountries.map(cCode => {
              const sts = STATES_BY_COUNTRY[cCode] || []
              if (!sts.length) return null
              const label = COUNTRIES.find(c => c.code === cCode)?.label || cCode
              return (
                <div key={cCode} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 5 }}>{label}</div>
                  <div className="state-grid">
                    {sts.map(s => (
                      <span key={s}
                        className={`state-tag${selectedStates.includes(s) ? ' selected' : ''}`}
                        onClick={() => toggleState(s)}
                      >{s}</span>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* 4 — Custom cities */}
        <div>
          <label className="form-label">
            Custom Cities <span style={{ fontWeight: 400, color: 'var(--text-dim)', textTransform: 'none', letterSpacing: 0 }}>(optional — one per line, e.g. "Miami Beach, FL")</span>
          </label>
          <textarea
            className="detail-textarea"
            rows={4}
            placeholder={"Miami Beach, FL\nAspen, CO\nWhistler, BC\nGold Coast, QLD"}
            value={customCities}
            onChange={e => setCustomCities(e.target.value)}
            style={{ fontFamily: 'monospace', fontSize: 12 }}
          />
          {parseCustomCities().length > 0 && (
            <div style={{ fontSize: 11, color: 'var(--gold)', marginTop: 4 }}>
              ✓ {parseCustomCities().length} custom location{parseCustomCities().length !== 1 ? 's' : ''} added
            </div>
          )}
        </div>

        {/* 5 — Results per city */}
        <div>
          <label className="form-label">Results per city: <strong style={{ color: 'var(--gold)' }}>{resultsPerCity}</strong></label>
          <input type="range" min={20} max={60} step={20} value={resultsPerCity}
            onChange={e => setResultsPerCity(Number(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--gold)' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>
            <span>20 — quick</span><span>40 — balanced</span><span>60 — thorough</span>
          </div>
        </div>

        {/* Start button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-primary" onClick={startScrape} disabled={running} style={{ minWidth: 140 }}>
            {running ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Starting...</> : 'Start Search'}
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
            {selectedCats.length} type{selectedCats.length !== 1 ? 's' : ''}
            {selectedStates.length > 0 && ` · ${selectedStates.length} state${selectedStates.length !== 1 ? 's' : ''}`}
            {parseCustomCities().length > 0 && ` · ${parseCustomCities().length} custom city${parseCustomCities().length !== 1 ? 'ies' : ''}`}
          </span>
        </div>
      </div>

      {activeJobs.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Running <span className="spinner" style={{ width: 12, height: 12 }} /></div>
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

function StatusPill({ label, ok, okText, failText, warn = false }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface)',
      border: `1px solid ${ok ? '#065f46' : warn ? '#92400e' : '#7f1d1d'}`,
      borderRadius: 8, padding: '8px 12px', fontSize: 12,
    }}>
      <div style={{ width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
        background: ok ? 'var(--converted)' : warn ? '#f59e0b' : '#dc2626' }} />
      <div>
        <div style={{ fontWeight: 600 }}>{label}</div>
        <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>{ok ? okText : failText}</div>
      </div>
    </div>
  )
}

function JobCard({ job }) {
  const duration = job.started_at && job.finished_at
    ? Math.round((new Date(job.finished_at) - new Date(job.started_at)) / 1000) + 's' : null
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
