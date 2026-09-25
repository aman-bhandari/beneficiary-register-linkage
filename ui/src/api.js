// All reads carry the acting role; the server folds it into every query.
const KEY = 'ekatra.role'
export function getRole() {
  try { return localStorage.getItem(KEY) || 'dswo_almora' } catch { return 'dswo_almora' }
}
export function setRole(r) {
  try { localStorage.setItem(KEY, r) } catch { /* private mode: the role lasts for this page only */ }
}

async function call(path, opts = {}) {
  const res = await fetch(path, { ...opts, headers: { 'X-Role': getRole(), ...(opts.headers || {}) } })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const msg = typeof body.detail === 'string' ? body.detail : Array.isArray(body.detail) ? body.detail.map(d => d.msg).join('; ') : res.statusText
    const err = new Error(msg)
    err.status = res.status
    throw err
  }
  return body
}

export const api = {
  roles: () => call('/api/roles'),
  overview: () => call('/api/overview'),
  cases: (params) => call('/api/cases?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v))),
  case: (id) => call(`/api/cases/${encodeURIComponent(id)}`),
  unmask: (id, reason) => call(`/api/cases/${encodeURIComponent(id)}/unmask`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason }) }),
  review: (id, decision, note) => call(`/api/cases/${encodeURIComponent(id)}/review`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ decision, note }) }),
  person: (key) => call(`/api/person/${encodeURIComponent(key)}`),
  planning: (district) => call('/api/planning' + (district ? `?district=${encodeURIComponent(district)}` : '')),
  overlap: (district) => call('/api/overlap' + (district ? `?district=${encodeURIComponent(district)}` : '')),
  audit: (params = {}) => call('/api/audit?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v))),
  verify: () => call('/api/audit/verify'),
  method: () => call('/api/method'),
  upload: (form) => call('/api/upload', { method: 'POST', body: form }),
}
