const BASE = '/api'

export async function sessionInit({ role, market, company_type, experience_level }) {
  const res = await fetch(`${BASE}/session-init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ role, market, company_type, experience_level }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function submitAnalysis({ sessionId, file, role, company_type, market, experience_level, userContext, jdText, githubUrl, optedInCorpus }) {
  const form = new FormData()
  form.append('session_id', sessionId)
  form.append('role', role)
  form.append('company_type', company_type)
  form.append('market', market)
  form.append('experience_level', experience_level)
  form.append('user_context', userContext || '')
  form.append('jd_text', jdText || '')
  form.append('github_url', githubUrl || '')
  form.append('opted_in_corpus', optedInCorpus ? 'true' : 'false')
  form.append('file', file)

  const res = await fetch(`${BASE}/analyse`, { method: 'POST', body: form })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(body)
  }
  return res.json()
}

export async function getSessionState(sessionId) {
  const res = await fetch(`${BASE}/session/${sessionId}/state`)
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function submitFollowup({ sessionId, section, question }) {
  const res = await fetch(`${BASE}/followup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, section, question }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function submitFeedback({ sessionId, useful, role, market, company_type }) {
  await fetch(`${BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, useful, role, market, company_type }),
  })
}

export async function requestToken(email) {
  const res = await fetch(`${BASE}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function verifyToken({ token, sessionId }) {
  const res = await fetch(`${BASE}/token/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, session_id: sessionId }),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export function createWebSocket(sessionId) {
  const wsBase = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return new WebSocket(`${wsBase}//${window.location.host}/ws/${sessionId}`)
}
