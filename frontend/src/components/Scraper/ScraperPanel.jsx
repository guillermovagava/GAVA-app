import { useState, useEffect, useRef } from 'react'
import { getCategories, quickScrape, getScrapeJobs } from '../../api/client'

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN',
  'IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV',
  'NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN',
  'TX','UT','VT','VA','WA','WV','WI','WY',
]
const CA_PROVINCES = ['BC','AB','ON','QC','NS','NB','MB','SK','PE','NL']

export default function ScraperPanel({ showToast }) {
  const [categories, setCategories] = useState([])
  const [selectedCats, setSelectedCats] = useState([])
  const [selectedStates, setSelectedStates] = useState([])
  const [jobs, setJobs] = useState([])
  const [running, setRunning] = useState(false)
  const pollRef = useRef(null)

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {})
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

  function selectAllStates() { setSelectedStates([...US_STATES, ...CA_PROVINCES]) }
  function clearStates() { setSelectedStates([]) }

  async function startScrape() {
    if (selectedCats.length === 0) { showToast('Select at least one business type', 'error'); return }
    if (selectedStates.length === 0) { showToast('Select at least one state/province', 'error'); return }
    setRunning(true)
    try {
      let started = 0
      for (const cat of selectedCats) {
        await quickScrape({ category_label: cat, states: selectedStates })
        started++
      }
      showToast(`Started ${started} scrape job${started > 1 ? 's' : ''}`, 'success')
      loadJobs()
    } catch (e) {
      showToast('Failed to start scrape: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setRunning(false)
    }
  }

  const activeJobs = jobs.filter(j => j.status === 'running' || j.status === 'pending')
  const doneJobs = jobs.filter(j => j.status === 'done' || j.status === 'failed')

  return (
    <div className="scraper-panel">
      <h2>Lead Scraper</h2>
      <p>
        Select business types and states/provinces to search. The scraper uses the Yelp API
        to find businesses and automatically discovers HR emails from their websites.
        {!window.__yelpConfigured &&
          ' Make sure your YELP_API_KEY is set in the .env file.'}
      </p>

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
            <label className="form-label" style={{ marginBottom: 0 }}>
              US States &amp; Canadian Provinces
            </label>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn btn-secondary btn-sm" onClick={selectAllStates}>All</button>
              <button className="btn btn-secondary btn-sm" onClick={clearStates}>Clear</button>
            </div>
          </div>

          <div style={{ marginBottom: 6, fontSize: 11, color: 'var(--text-dim)' }}>United States</div>
          <div className="state-grid" style={{ marginBottom: 10 }}>
            {US_STATES.map(s => (
              <span
                key={s}
                className={`state-tag${selectedStates.includes(s) ? ' selected' : ''}`}
                onClick={() => toggleState(s)}
              >{s}</span>
            ))}
          </div>

          <div style={{ marginBottom: 6, fontSize: 11, color: 'var(--text-dim)' }}>Canada</div>
          <div className="state-grid">
            {CA_PROVINCES.map(s => (
              <span
                key={s}
                className={`state-tag${selectedStates.includes(s) ? ' selected' : ''}`}
                onClick={() => toggleState(s)}
              >{s}</span>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            className="btn btn-primary"
            onClick={startScrape}
            disabled={running}
            style={{ minWidth: 140 }}
          >
            {running ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Starting...</> : 'Start Scraping'}
          </button>
          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
            {selectedCats.length} type{selectedCats.length !== 1 ? 's' : ''} &times; {selectedStates.length} location{selectedStates.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Active jobs */}
      {activeJobs.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            Running Jobs <span className="spinner" style={{ width: 12, height: 12 }} />
          </div>
          <div className="jobs-list">
            {activeJobs.map(job => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        </div>
      )}

      {/* Completed jobs */}
      {doneJobs.length > 0 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            Completed Jobs
            <button
              className="btn btn-secondary btn-sm"
              style={{ marginLeft: 10 }}
              onClick={loadJobs}
            >Refresh</button>
          </div>
          <div className="jobs-list">
            {doneJobs.slice(0, 20).map(job => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function JobCard({ job }) {
  const statusClass = `job-${job.status}`
  const duration = job.started_at && job.finished_at
    ? Math.round((new Date(job.finished_at) - new Date(job.started_at)) / 1000) + 's'
    : null

  return (
    <div className="job-card">
      <div className="job-info">
        <div className="job-title">{job.category} — {job.location}</div>
        <div className="job-meta">
          {job.leads_found > 0 && `${job.leads_found} leads found · `}
          {duration && `${duration} · `}
          {job.created_at && new Date(job.created_at).toLocaleString()}
          {job.error && <span style={{ color: '#fca5a5' }}> · Error: {job.error}</span>}
        </div>
      </div>
      <span className={`job-status ${statusClass}`}>{job.status}</span>
    </div>
  )
}
