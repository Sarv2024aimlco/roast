import { useState } from 'react'
import { submitFeedback, requestToken } from '../lib/api'

export function FeedbackButton({ sessionId, role, market, companyType }) {
  const [voted, setVoted] = useState(null)

  const vote = async (useful) => {
    if (voted) return
    setVoted(useful)
    await submitFeedback({ sessionId, useful, role, market, company_type: companyType })
  }

  if (voted !== null) {
    return <p className="text-xs text-gray-600 text-center">Thanks for the feedback.</p>
  }

  return (
    <div className="flex items-center justify-center gap-4">
      <p className="text-xs text-gray-500">Was this review useful?</p>
      <button onClick={() => vote(true)} className="text-lg hover:scale-110 transition-transform">👍</button>
      <button onClick={() => vote(false)} className="text-lg hover:scale-110 transition-transform">👎</button>
    </div>
  )
}

export function ThirdAnalysisUnlock() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const send = async () => {
    if (!email || loading) return
    setLoading(true)
    setError('')
    try {
      await requestToken(email)
      setSent(true)
    } catch (e) {
      setError(e.message || 'Failed to send token.')
    }
    setLoading(false)
  }

  if (sent) {
    return (
      <div className="border border-[#333] rounded-lg p-4 text-center space-y-1">
        <p className="text-sm text-gray-300">Token sent to {email}</p>
        <p className="text-xs text-gray-500">Check your inbox. Valid for 24 hours.</p>
      </div>
    )
  }

  return (
    <div className="border border-[#333] rounded-lg p-4 space-y-3">
      <div>
        <p className="text-sm text-gray-300">Get one more free roast</p>
        <p className="text-xs text-gray-500">Enter your email and we'll send a token.</p>
      </div>
      <div className="flex gap-2">
        <input
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="your@email.com"
          type="email"
          className="flex-1 bg-[#111] border border-[#333] rounded-lg px-3 py-2 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-orange-500"
        />
        <button
          onClick={send}
          disabled={loading}
          className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm rounded-lg transition-colors disabled:opacity-50"
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}
