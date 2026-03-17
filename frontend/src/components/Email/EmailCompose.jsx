import { useState } from 'react'
import { draftEmail, sendEmail } from '../../api/client'

const TONES = ['professional', 'friendly', 'concise', 'persuasive']

export default function EmailCompose({ lead, showToast, onSent }) {
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [tone, setTone] = useState('professional')
  const [customInstructions, setCustomInstructions] = useState('')
  const [drafting, setDrafting] = useState(false)
  const [sending, setSending] = useState(false)

  async function handleDraft() {
    setDrafting(true)
    try {
      const result = await draftEmail({
        business_name: lead.business_name,
        contact_name: lead.contact_name,
        category: lead.category,
        city: lead.city,
        state: lead.state,
        tone,
        custom_instructions: customInstructions,
      })
      if (result.error) {
        showToast('Claude error: ' + result.error, 'error')
      } else {
        setSubject(result.subject || '')
        setBody(result.body || '')
        showToast('Email drafted by Claude', 'success')
      }
    } catch (e) {
      showToast('Failed to draft email', 'error')
    } finally {
      setDrafting(false)
    }
  }

  async function handleSend() {
    if (!lead.email) { showToast('This lead has no email address', 'error'); return }
    if (!subject.trim()) { showToast('Subject is required', 'error'); return }
    if (!body.trim()) { showToast('Body is required', 'error'); return }
    setSending(true)
    try {
      await sendEmail({ lead_id: lead.id, subject, body })
      showToast(`Email sent to ${lead.email}`, 'success')
      onSent?.()
    } catch (e) {
      showToast(e.response?.data?.detail || 'Failed to send email', 'error')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="email-compose">
      <div className="email-compose-title">Compose Email</div>

      {!lead.email && (
        <div style={{
          background: '#7c2d1244',
          border: '1px solid #dc2626',
          borderRadius: 6,
          padding: '8px 12px',
          fontSize: 12,
          color: '#fca5a5',
        }}>
          No email address on file. Add one in the Info tab first.
        </div>
      )}

      {/* Claude AI drafting */}
      <div style={{
        background: 'var(--surface2)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 12,
      }}>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: 'var(--accent)' }}>
          AI Draft with Claude
        </div>

        <div style={{ marginBottom: 8 }}>
          <div className="detail-label">Tone</div>
          <div className="email-options">
            {TONES.map(t => (
              <button
                key={t}
                className={`tone-btn${tone === t ? ' selected' : ''}`}
                onClick={() => setTone(t)}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: 10 }}>
          <div className="detail-label">Extra instructions (optional)</div>
          <input
            className="detail-input"
            placeholder='e.g. "mention we have workers available for summer season"'
            value={customInstructions}
            onChange={e => setCustomInstructions(e.target.value)}
          />
        </div>

        <button
          className="btn btn-primary btn-sm"
          onClick={handleDraft}
          disabled={drafting}
        >
          {drafting
            ? <><span className="spinner" style={{ width: 12, height: 12 }} /> Drafting...</>
            : 'Generate Draft'}
        </button>
      </div>

      {/* Subject */}
      <div>
        <div className="detail-label">Subject Line</div>
        <input
          className="detail-input"
          placeholder="Email subject..."
          value={subject}
          onChange={e => setSubject(e.target.value)}
        />
      </div>

      {/* Body */}
      <div>
        <div className="detail-label">Email Body</div>
        <textarea
          className="detail-textarea"
          rows={10}
          placeholder="Write your email here, or use AI to generate a draft above..."
          value={body}
          onChange={e => setBody(e.target.value)}
        />
      </div>

      {/* Send */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
          {lead.email ? `To: ${lead.email}` : 'No email on file'}
        </div>
        <button
          className="btn btn-success"
          onClick={handleSend}
          disabled={sending || !lead.email}
        >
          {sending
            ? <><span className="spinner" style={{ width: 14, height: 14 }} /> Sending...</>
            : 'Send Email'}
        </button>
      </div>
    </div>
  )
}
