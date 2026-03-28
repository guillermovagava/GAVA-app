import { useState } from 'react'
import { createLead } from '../../api/client'

export default function AddLeadModal({ onClose, onCreated, showToast }) {
  const [form, setForm] = useState({
    business_name: '', address: '', city: '', state: '', country: 'US',
    category: '', phone: '', website: '', email: '', contact_name: '',
    position: '', notes: '',
  })
  const [saving, setSaving] = useState(false)

  function set(field, value) {
    setForm(f => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.business_name.trim()) {
      showToast('Business name is required', 'error')
      return
    }
    setSaving(true)
    try {
      const lead = await createLead({ ...form, source: 'manual' })
      showToast(`Added: ${lead.business_name}`)
      onCreated(lead)
      onClose()
    } catch {
      showToast('Failed to create lead', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <span>+ Add Lead Manually</span>
          <button className="detail-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          <div className="modal-field full">
            <label>Business Name *</label>
            <input value={form.business_name} onChange={e => set('business_name', e.target.value)} placeholder="e.g. Grand Mountain Resort" />
          </div>

          <div className="modal-field">
            <label>Category</label>
            <input value={form.category} onChange={e => set('category', e.target.value)} placeholder="Hotels & Resorts" />
          </div>

          <div className="modal-field">
            <label>Country</label>
            <select value={form.country} onChange={e => set('country', e.target.value)}>
              <option value="US">🇺🇸 United States</option>
              <option value="CA">🇨🇦 Canada</option>
              <option value="AU">🇦🇺 Australia</option>
            </select>
          </div>

          <div className="modal-field">
            <label>City</label>
            <input value={form.city} onChange={e => set('city', e.target.value)} placeholder="Denver" />
          </div>

          <div className="modal-field">
            <label>State / Province</label>
            <input value={form.state} onChange={e => set('state', e.target.value)} placeholder="CO" />
          </div>

          <div className="modal-field full">
            <label>Address</label>
            <input value={form.address} onChange={e => set('address', e.target.value)} placeholder="123 Mountain Rd, Denver, CO 80201, USA" />
          </div>

          <div className="modal-field">
            <label>Phone</label>
            <input value={form.phone} onChange={e => set('phone', e.target.value)} placeholder="+1 303-555-0100" />
          </div>

          <div className="modal-field">
            <label>Website</label>
            <input value={form.website} onChange={e => set('website', e.target.value)} placeholder="https://example.com" />
          </div>

          <div className="modal-field">
            <label>Email</label>
            <input value={form.email} onChange={e => set('email', e.target.value)} placeholder="hr@example.com" />
          </div>

          <div className="modal-field">
            <label>Contact Name</label>
            <input value={form.contact_name} onChange={e => set('contact_name', e.target.value)} placeholder="Jane Smith" />
          </div>

          <div className="modal-field full">
            <label>Position / Title</label>
            <input value={form.position} onChange={e => set('position', e.target.value)} placeholder="HR Manager" />
          </div>

          <div className="modal-field full">
            <label>Notes</label>
            <textarea value={form.notes} onChange={e => set('notes', e.target.value)} placeholder="Any notes about this lead..." />
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Adding…' : 'Add Lead'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
