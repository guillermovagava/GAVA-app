import { useState, useEffect, useRef } from 'react'
import { getScrapeJobs } from '../../api/client'
import axios from 'axios'

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN',
  'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
  'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
  'TX','UT','VT','VA','WA','WV','WI','WY',
]
const CA_PROVINCES = ['BC','AB','ON','QC','NS','NB','MB','SK','PE','NL']
const AU_STATES = ['NSW','VIC','QLD','WA','SA','TAS','NT','ACT']

export default function ScraperPanel({ showToast }) {
  const [categories, setCategories] = useState([])
  const [status, setStatus] = useState({ google_places: false, hunter: false })
  const [selectedCats, setSelectedCats] = useState([])
  const [selectedStates, setSelectedStates] = useState([])
  const [jobs, setJobs] = useState([])
  const [running, setRunning] = useState(false)
  const [resultsPerCity, setResultsPerCity] = useState(20)
  const [hunterCredits, setHunterCredits] = useState(5)
  const pollRef = useRef(null)

  useEffect(() => {
    axios.get('/api/scraper/categories').then(r => setCategories(r.data)).catch(() => {})
    axios.get('/api/scraper/status').then(r => setStatus(r.data)).catch(() => {})
    loadJobs()
  }, [])

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
    if (!status.google_places) {
      showToast('Add your GOOGLE_PLACES_API_KEY to the .env file first', 'error')
      return
    }
    if (selectedCats.length === 0) { showToast('Select at least one business type', 'error'); return }
    if (selectedStates.length === 0) { showToast('Select at least one state/province', 'error'); return }

    setRunning(true)
    try {
      for (const cat of selectedCats) {
        await axios.post('/api/scraper/run', { category_label: cat, states: selectedStates, max_results_per_city: resultsPerCity })
      }
      showToast(`Started ${selectedCats.length} search job${selectedCats.length > 1 ? 's' : ''}`, 'success')
      loadJobs()
    } catch (e) {
      showToast('Failed to start: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setRunning(false)
    }
  }

  const activeJobs = jobs.filter(j => j.status === 'running' || j.status === 'pending')
  const doneJobs   = jobs.filter(j => j.status === 'done'    || j.status === 'failed')

  return (
    <div className="scraper-panel">
      <h2>Lead Scraper</h2>
      <p>
        Search Google Maps for businesses to recruit from. For each business found,
        the app automatically tries to find an HR contact email — using Hunter.io
        if you have a key, or by scanning the company's website for free.
      </p>

      {/* API key status */}
      <div style={{
        display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap',
      }}>
        <StatusPill
          label="Google Places"
          ok={status.google_places}
          okText="Connected"
          failText="Missing API key — add GOOGLE_PLACES_API_KEY to .env"
        />
        <StatusPill
          label="Hunter.io"
          ok={status.hunter}
          okText="Connected — using paid email lookup"
          failText="Not set — using free website scanner instead"
          warn
        />
      </div>

      <div className="scraper-form">
        {/* Business types */}
        <div>
          <label className="form-label">Business Types (select one or more)</label>
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
        </div>

        {/* States */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <label className="form-label" style={{ marginBottom: 0 }}>States &amp; Provinces</label>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedStates([...US_STATES, ...CA_PROVINCES, ...AU_STATES])}>All</button>
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
          <div style={{ marginBottom: 5, fontSize: 11, color: 'var(--text-dim)' }}>Australia</div>
          <div className="state-grid">
            {AU_STATES.map(s => (
              <span key={s} className={`state-tag${selectedStates.includes(s) ? ' selected' : ''}`} onClick={() => toggleState(s)}>{s}</span>
            ))}
          </div>
        </div>

        {/* Hunter.io credit slider — only show if Hunter is connected */}
        {status.hunter && (
          <div style={{
            background: 'var(--surface)', border: '1px solid #92400e',
            borderRadius: 10, padding: '12px 16px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>Hunter.io credits for this search</span>
              <span style={{
                fontWeight: 700, fontSize: 15, color: '#f59e0b',
                background: '#451a03', borderRadius: 6, padding: '2px 10px',
              }}>
                {hunterCredits === 0 ? 'None (free scraper only)' : `${hunterCredits} credit${hunterCredits !== 1 ? 's' : ''}`}
              </span>
            </div>
            <input
              type="range" min={0} max={25} step={1}
              value={hunterCredits}
              onChange={e => setHunterCredits(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#f59e0b' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
              <span>0 — Free scraper only</span>
              <span style={{ color: '#f59e0b' }}>
                {hunterCredits > 0
                  ? `Uses ${hunterCredits} of your 25 monthly credits → better contact names & verified emails`
                  : 'Scans company websites for free — slower but unlimited'}
              </span>
              <span>25</span>
            </div>
          </div>
        )}

        <div>
          <label className="form-label">Results per city: <strong style={{color:'var(--gold)'}}>{resultsPerCity}</strong></label>
          <input
            type="range" min={20} max={60} step={20}
            value={resultsPerCity}
            onChange={e => setResultsPerCity(Number(e.target.value))}
            style={{ width: '100%', accentColor: 'var(--gold)' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>
            <span>20 — quick</span><span>40 — balanced</span><span>60 — thorough</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-primary" onClick={startScrape} disabled={running} style={{ minWidth: 140 }}>
            {running
              ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Starting...</>
              : 'Start Search'}
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

function StatusPill({ label, ok, okText, failText, warn = false }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      background: 'var(--surface)',
      border: `1px solid ${ok ? '#065f46' : warn ? '#92400e' : '#7f1d1d'}`,
      borderRadius: 8, padding: '8px 12px', fontSize: 12,
    }}>
      <div style={{
        width: 8, height: 8, borderRadius: '50%',
        background: ok ? 'var(--converted)' : warn ? '#f59e0b' : '#dc2626',
        flexShrink: 0,
      }} />
      <div>
        <div style={{ fontWeight: 600 }}>{label}</div>
        <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>{ok ? okText : failText}</div>
      </div>
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
