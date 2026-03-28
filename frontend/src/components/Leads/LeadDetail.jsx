import { useState, useEffect } from 'react'
import { getLead, updateLead, deleteLead, findEmailHunter, exportLeads } from '../../api/client'
import EmailCompose from '../Email/EmailCompose'

const STATUSES = ['new', 'contacted', 'replied', 'meeting_booked', 'converted']

export default function LeadDetail({ leadId, onClose, onDeleted, onUpdated, showToast }) {
  const [lead, setLead] = useState(null)
  const [tab, setTab] = useState('info')
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [findingEmail, setFindingEmail] = useState(false)

  useEffect(() => {
    if (!leadId) return
    getLead(leadId).then(data => {
      setLead(data)
      setForm(data)
      setTab('info')
    }).catch(() => {})
  }, [leadId])

  if (!lead) return null

  function set(key, val) {
    setForm(f => ({ ...f, [key]: val }))
  }

  async function save() {
    setSaving(true)
    try {
      const updated = await updateLead(lead.id, form)
      setLead({ ...lead, ...updated, email_history: lead.email_history })
      setEditing(false)
      onUpdated?.()
      showToast('Lead saved', 'success')
    } catch {
      showToast('Failed to save', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function handleFindEmail() {
    setFindingEmail(true)
    try {
      const result = await findEmailHunter(lead.id)
      setLead(l => ({ ...l, email: result.email, contact_name: result.contact_name || l.contact_name, email_source: result.source }))
      showToast(`Email found via ${result.source}: ${result.email}`, 'success')
    } catch (e) {
      showToast(e.response?.data?.detail || 'No email found', 'error')
    } finally {
      setFindingEmail(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete "${lead.business_name}"? This cannot be undone.`)) return
    await deleteLead(lead.id)
    onDeleted?.()
    onClose()
    showToast('Lead deleted', 'success')
  }

  async function handleStatusChange(status) {
    const updated = await updateLead(lead.id, { status })
    setLead(l => ({ ...l, status: updated.status }))
    setForm(f => ({ ...f, status: updated.status }))
    onUpdated?.()
  }

  function refreshHistory() {
    getLead(lead.id).then(data => setLead(data))
  }

  return (
    <>
      <div className="detail-header">
        <div className="detail-header-text">
          <div className="detail-title">{lead.business_name}</div>
          <div className="detail-subtitle">
            {lead.city}{lead.state ? `, ${lead.state}` : ''} &middot; {lead.category || 'Uncategorized'}
          </div>
        </div>
        <button className="detail-close" onClick={onClose}>&#x2715;</button>
      </div>

      <div style={{ padding: '8px 16px 0', borderBottom: '1px solid var(--border)' }}>
        <div className="tab-bar" style={{ borderBottom: 'none', marginBottom: 0 }}>
          {['info', 'email', 'history'].map(t => (
            <button
              key={t}
              className={`tab-btn${tab === t ? ' active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t === 'info' ? 'Info' : t === 'email' ? 'Send Email' : 'Email History'}
            </button>
          ))}
        </div>
      </div>

      <div className="detail-body">
        {tab === 'info' && (
          <div>
            {/* Place photo */}
            {lead.photo_ref && (
              <div style={{ marginBottom: 0 }}>
                <img
                  src={`/api/leads/${lead.id}/photo`}
                  alt={lead.business_name}
                  style={{
                    width: '100%', height: 180, objectFit: 'cover',
                    display: 'block', borderBottom: '1px solid var(--border)',
                  }}
                  onError={e => { e.target.style.display = 'none' }}
                />
              </div>
            )}

            {/* Status selector */}
            <div className="detail-section">
              <div className="detail-section-title">Status</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {STATUSES.map(s => (
                  <button
                    key={s}
                    className={`btn btn-sm status-badge status-${s}`}
                    style={{ opacity: lead.status === s ? 1 : 0.4, cursor: 'pointer' }}
                    onClick={() => handleStatusChange(s)}
                  >
                    {s.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>

            {/* Contact info */}
            <div className="detail-section">
              <div className="detail-section-title">Contact Information</div>
              {editing ? (
                <>
                  <Field label="Contact Name">
                    <input className="detail-input" value={form.contact_name || ''} onChange={e => set('contact_name', e.target.value)} />
                  </Field>
                  <Field label="Email">
                    <input className="detail-input" value={form.email || ''} onChange={e => set('email', e.target.value)} />
                  </Field>
                  <Field label="Phone">
                    <input className="detail-input" value={form.phone || ''} onChange={e => set('phone', e.target.value)} />
                  </Field>
                  <Field label="Website">
                    <input className="detail-input" value={form.website || ''} onChange={e => set('website', e.target.value)} />
                  </Field>
                </>
              ) : (
                <>
                  <InfoRow label="Contact" value={lead.contact_name || '—'} />
                  <InfoRow label="Email" value={lead.email ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                      <a href={`mailto:${lead.email}`}>{lead.email}</a>
                      {lead.email_source === 'hunter' && (
                        <span style={{
                          fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
                          background: '#1e3a5f', color: '#60a5fa', letterSpacing: '0.3px'
                        }}>via Hunter.io ✓</span>
                      )}
                      {lead.email_source === 'scraper' && (
                        <span style={{
                          fontSize: 10, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
                          background: '#1a3a2a', color: '#4ade80', letterSpacing: '0.3px'
                        }}>via web scan (free)</span>
                      )}
                    </span>
                  ) : '—'} />
                  <InfoRow label="Phone" value={lead.phone || '—'} />
                  <InfoRow label="Website" value={lead.website
                    ? <a href={lead.website} target="_blank" rel="noreferrer">{lead.website}</a>
                    : '—'} />
                </>
              )}
            </div>

            {/* Location */}
            <div className="detail-section">
              <div className="detail-section-title">Location</div>
              {editing ? (
                <>
                  <Field label="Address">
                    <input className="detail-input" value={form.address || ''} onChange={e => set('address', e.target.value)} />
                  </Field>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Field label="City" style={{ flex: 1 }}>
                      <input className="detail-input" value={form.city || ''} onChange={e => set('city', e.target.value)} />
                    </Field>
                    <Field label="State" style={{ flex: 1 }}>
                      <input className="detail-input" value={form.state || ''} onChange={e => set('state', e.target.value)} />
                    </Field>
                  </div>
                </>
              ) : (
                <>
                  <InfoRow label="Address" value={lead.address || '—'} />
                  <InfoRow label="City / State" value={[lead.city, lead.state].filter(Boolean).join(', ') || '—'} />
                  <InfoRow label="Country" value={lead.country || '—'} />
                </>
              )}
            </div>

            {/* Notes */}
            <div className="detail-section">
              <div className="detail-section-title">Notes</div>
              {editing ? (
                <textarea
                  className="detail-textarea"
                  rows={4}
                  value={form.notes || ''}
                  onChange={e => set('notes', e.target.value)}
                  placeholder="Internal notes about this lead..."
                />
              ) : (
                <div style={{ fontSize: 13, color: lead.notes ? 'var(--text)' : 'var(--text-dim)', whiteSpace: 'pre-wrap' }}>
                  {lead.notes || 'No notes yet.'}
                </div>
              )}
            </div>

            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>Added {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '—'}</span>
              <span>·</span>
              <span>Source: {lead.source || 'manual'}</span>
              {lead.last_contacted && <><span>·</span><span>Last contacted {new Date(lead.last_contacted).toLocaleDateString()}</span></>}
              {lead.score !== undefined && (
                <span style={{ marginLeft: 'auto', color: 'var(--gold)', fontWeight: 600 }}>
                  Score: {lead.score}/10
                </span>
              )}
            </div>
          </div>
        )}

        {tab === 'email' && (
          <EmailCompose lead={lead} showToast={showToast} onSent={refreshHistory} />
        )}

        {tab === 'history' && (
          <div>
            {(lead.email_history || []).length === 0 ? (
              <div className="empty-state">
                <p>No emails sent yet.</p>
              </div>
            ) : (
              (lead.email_history || []).map(e => (
                <div key={e.id} className="email-history-item">
                  <div className="email-history-subject">{e.subject}</div>
                  <div className="email-history-date">{new Date(e.sent_at).toLocaleString()}</div>
                  <div className="email-history-body">{e.body}</div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      <div className="detail-footer">
        {editing ? (
          <>
            <button className="btn btn-primary" onClick={save} disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button className="btn btn-secondary" onClick={() => { setEditing(false); setForm(lead) }}>
              Cancel
            </button>
          </>
        ) : (
          <>
            <button className="btn btn-secondary" onClick={() => setEditing(true)}>Edit</button>
            {lead.website && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleFindEmail}
                disabled={findingEmail}
                title={lead.email ? "Re-search with Hunter.io to find a better HR contact" : "Search Hunter.io or website for HR email"}
                style={{ color: 'var(--gold)', borderColor: 'var(--gold-dim)' }}
              >
                {findingEmail
                  ? <><span className="spinner" style={{width:12,height:12}}/> Searching...</>
                  : lead.email_source === 'hunter'
                    ? '⚡ Re-run Hunter'
                    : '⚡ Hunter Search'}
              </button>
            )}
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => exportLeads({ lead_id: lead.id })}
              title="Export this lead to Excel"
              style={{ marginLeft: 'auto' }}
            >
              ↓ Excel
            </button>
            <button className="btn btn-danger btn-sm" onClick={handleDelete}>
              Delete
            </button>
          </>
        )}
      </div>
    </>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="detail-field">
      <span className="detail-label">{label}</span>
      <span className="detail-value">{value}</span>
    </div>
  )
}

function Field({ label, children, style }) {
  return (
    <div className="detail-field" style={style}>
      <span className="detail-label">{label}</span>
      {children}
    </div>
  )
}
