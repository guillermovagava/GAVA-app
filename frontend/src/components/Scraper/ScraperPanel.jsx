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

// Mirror of backend STATE_CITIES — cities known per state
const CITIES_BY_STATE = {
  FL:  ['Miami','Orlando','Tampa','Jacksonville','Fort Lauderdale'],
  CA:  ['Los Angeles','San Francisco','San Diego','Sacramento','Anaheim'],
  NY:  ['New York City','Buffalo','Albany','Rochester','Syracuse'],
  TX:  ['Houston','Dallas','Austin','San Antonio','El Paso'],
  CO:  ['Denver','Colorado Springs','Aspen','Vail','Breckenridge'],
  HI:  ['Honolulu','Maui','Kauai','Kailua-Kona'],
  NV:  ['Las Vegas','Reno','Lake Tahoe'],
  AZ:  ['Phoenix','Scottsdale','Sedona','Tucson'],
  WA:  ['Seattle','Spokane','Bellevue','Tacoma'],
  OR:  ['Portland','Eugene','Bend','Salem'],
  GA:  ['Atlanta','Savannah','Augusta','Macon'],
  NC:  ['Charlotte','Raleigh','Asheville','Wilmington'],
  SC:  ['Charleston','Myrtle Beach','Hilton Head','Columbia'],
  VA:  ['Virginia Beach','Richmond','Charlottesville','Roanoke'],
  MI:  ['Detroit','Traverse City','Grand Rapids','Ann Arbor'],
  MN:  ['Minneapolis','Duluth','Rochester','Brainerd'],
  WI:  ['Milwaukee','Madison','Green Bay','Wisconsin Dells'],
  IL:  ['Chicago','Springfield','Galena','Rockford'],
  PA:  ['Philadelphia','Pittsburgh','Hershey','Lancaster'],
  MA:  ['Boston','Cape Cod','Springfield','Worcester'],
  ME:  ['Portland','Bar Harbor','Kennebunkport','Bangor'],
  NH:  ['Manchester','Portsmouth','Conway','Laconia'],
  VT:  ['Burlington','Stowe','Montpelier','Brattleboro'],
  // Canada
  BC:  ['Vancouver','Victoria','Whistler','Kelowna'],
  AB:  ['Calgary','Edmonton','Banff','Jasper'],
  ON:  ['Toronto','Ottawa','Niagara Falls','Muskoka'],
  QC:  ['Montreal','Quebec City','Mont-Tremblant'],
  // Australia
  NSW: ['Sydney','Newcastle','Wollongong','Byron Bay','Port Macquarie'],
  VIC: ['Melbourne','Geelong','Ballarat','Bendigo','Mornington'],
  QLD: ['Brisbane','Gold Coast','Cairns','Townsville','Noosa','Whitsundays'],
  SA:  ['Adelaide','Port Augusta','Kangaroo Island','Barossa Valley'],
  TAS: ['Hobart','Launceston','Cradle Mountain','Freycinet'],
  NT:  ['Darwin','Alice Springs','Kakadu'],
  ACT: ['Canberra'],
}

export default function ScraperPanel({ showToast }) {
  const [categories, setCategories]               = useState([])
  const [status, setStatus]                       = useState({ google_places: false, hunter: false })
  const [selectedCats, setSelectedCats]           = useState([])
  const [selectedCountries, setSelectedCountries] = useState(['US'])
  const [selectedStates, setSelectedStates]       = useState([])
  const [selectedCities, setSelectedCities]       = useState([])  // empty = any city
  const [customCities, setCustomCities]           = useState('')
  const [resultsPerCity, setResultsPerCity]       = useState(20)
  const [jobs, setJobs]                           = useState([])
  const [running, setRunning]                     = useState(false)
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
      setSelectedStates(s => s.filter(st => next.some(c => STATES_BY_COUNTRY[c]?.includes(st))))
      setSelectedCities([])
      return next
    })
  }

  function toggleState(s) {
    setSelectedStates(p => {
      const next = p.includes(s) ? p.filter(x => x !== s) : [...p, s]
      // Remove selected cities that belong to a state that was just deselected
      setSelectedCities(c => c.filter(city =>
        next.some(st => (CITIES_BY_STATE[st] || []).includes(city))
      ))
      return next
    })
  }

  function selectAllStates() {
    setSelectedStates(selectedCountries.flatMap(c => STATES_BY_COUNTRY[c] || []))
    setSelectedCities([])
  }

  function toggleCity(city) {
    setSelectedCities(p => p.includes(city) ? p.filter(x => x !== city) : [...p, city])
  }

  function selectAllCities() {
    const all = selectedStates.flatMap(s => CITIES_BY_STATE[s] || [])
    setSelectedCities(all)
  }

  function parseCustomCities() {
    if (!customCities.trim()) return []
    return customCities.split('\n').map(l => l.trim()).filter(l => l.length > 0)
  }

  async function startScrape() {
    if (!status.google_places) {
      showToast('Add GOOGLE_PLACES_API_KEY to .env first', 'error'); return
    }
    if (selectedCats.length === 0) { showToast('Select at least one business type', 'error'); return }

    const customLocs = parseCustomCities()
    if (selectedStates.length === 0 && customLocs.length === 0) {
      showToast('Select at least one state or enter a custom city', 'error'); return
    }

    setRunning(true)
    try {
      for (const cat of selectedCats) {
        await axios.post('/api/scraper/run', {
          category_label:   cat,
          states:           selectedStates,
          selected_cities:  selectedCities,   // empty = any city in those states
          custom_locations: customLocs,
          max_results_per_city: resultsPerCity,
        })
      }
      showToast(`Started ${selectedCats.length} search job${selectedCats.length > 1 ? 's' : ''}`, 'success')
      loadJobs()
    } catch (e) {
      showToast('Failed to start: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setRunning(false)
    }
  }

  // Which states have a known city list
  const statesWithCities = selectedStates.filter(s => (CITIES_BY_STATE[s] || []).length > 0)
  const anyCityMode      = selectedCities.length === 0
  const customLocs       = parseCustomCities()

  const visibleStates = selectedCountries.flatMap(c => STATES_BY_COUNTRY[c] || [])
  const activeJobs    = jobs.filter(j => j.status === 'running' || j.status === 'pending')
  const doneJobs      = jobs.filter(j => j.status === 'done'    || j.status === 'failed')

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
                <button className="btn btn-secondary btn-sm" onClick={() => { setSelectedStates([]); setSelectedCities([]) }}>Clear</button>
              </div>
            </div>
            {selectedCountries.map(cCode => {
              const sts   = STATES_BY_COUNTRY[cCode] || []
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

        {/* 4 — City picker (only when states with known cities are selected) */}
        {statesWithCities.length > 0 && (
          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 10,
            padding: '12px 14px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <label className="form-label" style={{ marginBottom: 0 }}>Cities</label>
              <div style={{ display: 'flex', gap: 6 }}>
                {/* Any city button — active when nothing is selected */}
                <button
                  className="btn btn-sm"
                  onClick={() => setSelectedCities([])}
                  style={{
                    background: anyCityMode ? 'var(--gold)' : 'var(--surface2)',
                    color:      anyCityMode ? 'var(--navy)' : 'var(--text-dim)',
                    border:     `1px solid ${anyCityMode ? 'var(--gold)' : 'var(--border)'}`,
                    fontWeight: 600,
                  }}
                >
                  Any city
                </button>
                <button className="btn btn-secondary btn-sm" onClick={selectAllCities}>All</button>
                {!anyCityMode && (
                  <button className="btn btn-secondary btn-sm" onClick={() => setSelectedCities([])}>Clear</button>
                )}
              </div>
            </div>

            {anyCityMode && (
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 8 }}>
                Will search all known cities in the selected states. Click a city below to narrow it down.
              </div>
            )}

            {statesWithCities.map(state => (
              <div key={state} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 5, fontWeight: 600 }}>
                  {state}
                </div>
                <div className="state-grid">
                  {(CITIES_BY_STATE[state] || []).map(city => (
                    <span
                      key={city}
                      className={`state-tag${selectedCities.includes(city) ? ' selected' : ''}`}
                      onClick={() => toggleCity(city)}
                      style={{ fontSize: 11 }}
                    >
                      {city}
                    </span>
                  ))}
                </div>
              </div>
            ))}

            <div style={{ fontSize: 11, color: anyCityMode ? 'var(--text-dim)' : 'var(--gold)', marginTop: 4 }}>
              {anyCityMode
                ? `${statesWithCities.flatMap(s => CITIES_BY_STATE[s] || []).length} cities queued`
                : `${selectedCities.length} city${selectedCities.length !== 1 ? 'ies' : 'y'} selected`}
            </div>
          </div>
        )}

        {/* 5 — Custom cities */}
        <div>
          <label className="form-label">
            Custom Cities{' '}
            <span style={{ fontWeight: 400, color: 'var(--text-dim)', textTransform: 'none', letterSpacing: 0 }}>
              (optional — one per line, e.g. "Miami Beach, FL")
            </span>
          </label>
          <textarea
            className="detail-textarea"
            rows={3}
            placeholder={"Miami Beach, FL\nAspen, CO\nWhistler, BC\nGold Coast, QLD"}
            value={customCities}
            onChange={e => setCustomCities(e.target.value)}
            style={{ fontFamily: 'monospace', fontSize: 12 }}
          />
          {customLocs.length > 0 && (
            <div style={{ fontSize: 11, color: 'var(--gold)', marginTop: 4 }}>
              ✓ {customLocs.length} custom location{customLocs.length !== 1 ? 's' : ''} added
            </div>
          )}
        </div>

        {/* 6 — Results per city */}
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
            {!anyCityMode && ` · ${selectedCities.length} city${selectedCities.length !== 1 ? 'ies' : 'y'}`}
            {anyCityMode && statesWithCities.length > 0 && ' · any city'}
            {customLocs.length > 0 && ` · ${customLocs.length} custom`}
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
