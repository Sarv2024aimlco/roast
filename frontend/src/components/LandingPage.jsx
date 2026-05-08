import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { DropZone } from './DropZone'
import { sessionInit, submitAnalysis } from '../lib/api'

const ROLES = [
  'SDE1', 'SDE2', 'Senior SDE', 'Full Stack Engineer', 'Backend Engineer',
  'Embedded Systems Engineer', 'VLSI Design Engineer',
  'Data Analyst', 'Data Scientist', 'Data Engineer',
  'ML Engineer', 'AI Engineer',
  'DevOps / SRE', 'Product Manager', 'Business Analyst',
]

const ROLES_2PLUS = [...ROLES, 'ML/AI Engineer']

const COMPANY_TYPES = [
  'Indian Product Company (Tier 1)',
  'Indian Product Company (Tier 2)',
  'Indian Service Company',
  'FAANG / Big Tech',
  'Early Stage Startup',
  'Growth Stage Startup',
  'Consulting / IB',
  'Semiconductor / Hardware',
  'MNC India (Non-FAANG)',
]

const MARKETS = ['India', 'USA', 'UAE', 'Singapore', 'UK']

const EXPERIENCE_LEVELS = [
  'Student / Fresher',
  'Junior',
  'Mid-level',
  'Senior',
  'Staff / Principal',
]

const TWO_PLUS = ['Mid-level', 'Senior', 'Staff / Principal']

const HEADLINE_WORDS = ['Your', 'resume.', 'Destroyed.', 'Improved.']

function TypewriterHeadline() {
  const [visible, setVisible] = useState(0)

  useEffect(() => {
    if (visible >= HEADLINE_WORDS.length) return
    const t = setTimeout(() => setVisible(v => v + 1), 300)
    return () => clearTimeout(t)
  }, [visible])

  return (
    <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
      {HEADLINE_WORDS.map((word, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0, y: 10 }}
          animate={i < visible ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.3 }}
          className={`inline-block mr-3 ${word === 'Destroyed.' ? 'text-orange-500' : ''}`}
        >
          {word}
        </motion.span>
      ))}
    </h1>
  )
}

export function LandingPage({ onAnalysisStarted }) {
  const [file, setFile] = useState(null)
  const [role, setRole] = useState('')
  const [companyType, setCompanyType] = useState('')
  const [market, setMarket] = useState('')
  const [experienceLevel, setExperienceLevel] = useState('')
  const [userContext, setUserContext] = useState('')
  const [jdText, setJdText] = useState('')
  const [githubUrl, setGithubUrl] = useState('')
  const [showContext, setShowContext] = useState(false)
  const [showToken, setShowToken] = useState(false)
  const [token, setToken] = useState('')
  const [consent, setConsent] = useState(false)
  const [optedIn, setOptedIn] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Pre-create session on page load — timing gate needs 3s between session-init and analyse
  // By the time user fills form and clicks submit, well over 3s have passed
  const [sessionId, setSessionId] = useState(null)
  useEffect(() => {
    sessionInit({
      role: 'SDE2', market: 'India',
      company_type: 'Indian Product Company (Tier 1)',
      experience_level: 'Junior',
    }).then(s => setSessionId(s.session_id)).catch(() => {})
  }, [])

  // UTM detection
  const isReferred = new URLSearchParams(window.location.search).has('ref') ||
    window.location.search.includes('utm_')

  const availableRoles = TWO_PLUS.includes(experienceLevel) ? ROLES_2PLUS : ROLES

  const canSubmit = file && role && companyType && market && experienceLevel && consent

  const handleSubmit = async () => {
    if (!canSubmit || loading) return
    setLoading(true)
    setError('')

    try {
      // Use pre-created session (timing gate already satisfied)
      // If session wasn't created yet, create one now as fallback
      let sid = sessionId
      if (!sid) {
        const session = await sessionInit({
          role, market, company_type: companyType, experience_level: experienceLevel,
        })
        sid = session.session_id
      }

      await submitAnalysis({
        sessionId: sid,
        file, role, company_type: companyType, market,
        experience_level: experienceLevel,
        userContext, jdText, githubUrl,
        optedInCorpus: optedIn,
      })

      onAnalysisStarted(sid, { role, companyType, market, experienceLevel })
    } catch (e) {
      setError(e.message || 'Something went wrong. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-xl space-y-8">

        {/* Headline */}
        <div className="space-y-3">
          {isReferred ? (
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
              Someone shared their roast.{' '}
              <span className="text-orange-500">Get yours free.</span>
            </h1>
          ) : (
            <TypewriterHeadline />
          )}
          <p className="text-gray-400 text-lg">
            The brutal honest feedback your well-meaning friends won't give you.
          </p>
        </div>

        {/* Upload */}
        <DropZone onFile={setFile} />

        {/* Dropdowns */}
        <div className="grid grid-cols-2 gap-3">
          <select
            value={experienceLevel}
            onChange={e => { setExperienceLevel(e.target.value); setRole('') }}
            className="bg-[#111] border border-[#333] rounded-lg px-3 py-2.5 text-sm text-gray-300 focus:outline-none focus:border-orange-500"
          >
            <option value="">Experience Level</option>
            {EXPERIENCE_LEVELS.map(l => <option key={l}>{l}</option>)}
          </select>

          <select
            value={role}
            onChange={e => setRole(e.target.value)}
            className="bg-[#111] border border-[#333] rounded-lg px-3 py-2.5 text-sm text-gray-300 focus:outline-none focus:border-orange-500"
          >
            <option value="">Target Role</option>
            {availableRoles.map(r => <option key={r}>{r}</option>)}
          </select>

          <select
            value={companyType}
            onChange={e => setCompanyType(e.target.value)}
            className="bg-[#111] border border-[#333] rounded-lg px-3 py-2.5 text-sm text-gray-300 focus:outline-none focus:border-orange-500"
          >
            <option value="">Company Type</option>
            {COMPANY_TYPES.map(c => <option key={c}>{c}</option>)}
          </select>

          <select
            value={market}
            onChange={e => setMarket(e.target.value)}
            className="bg-[#111] border border-[#333] rounded-lg px-3 py-2.5 text-sm text-gray-300 focus:outline-none focus:border-orange-500"
          >
            <option value="">Target Market</option>
            {MARKETS.map(m => <option key={m}>{m}</option>)}
          </select>
        </div>

        {/* Optional context */}
        <div>
          <button
            onClick={() => setShowContext(v => !v)}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-300 transition-colors"
          >
            {showContext ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            Add context (optional)
          </button>

          <AnimatePresence>
            {showContext && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="pt-3 space-y-3">
                  <textarea
                    value={userContext}
                    onChange={e => setUserContext(e.target.value.slice(0, 500))}
                    placeholder="Anything we should know? e.g. career gap reason, location constraint, available to join immediately"
                    rows={3}
                    className="w-full bg-[#111] border border-[#333] rounded-lg px-3 py-2.5 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-orange-500 resize-none"
                  />
                  <textarea
                    value={jdText}
                    onChange={e => setJdText(e.target.value.slice(0, 2000))}
                    placeholder="Paste job description (optional) — review will calibrate to this specific role"
                    rows={3}
                    className="w-full bg-[#111] border border-[#333] rounded-lg px-3 py-2.5 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-orange-500 resize-none"
                  />
                  <input
                    value={githubUrl}
                    onChange={e => setGithubUrl(e.target.value)}
                    placeholder="GitHub URL (optional)"
                    className="w-full bg-[#111] border border-[#333] rounded-lg px-3 py-2.5 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-orange-500"
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Consent */}
        <div className="space-y-2">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={consent}
              onChange={e => setConsent(e.target.checked)}
              className="mt-0.5 accent-orange-500"
            />
            <span className="text-xs text-gray-500">
              Your resume is processed by third-party AI providers for analysis. It is never stored by ROAST.
            </span>
          </label>
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={optedIn}
              onChange={e => setOptedIn(e.target.checked)}
              className="mt-0.5 accent-orange-500"
            />
            <span className="text-xs text-gray-500">
              Contribute anonymised signals to improve competitive positioning for everyone. No resume content, no personal data.
            </span>
          </label>
        </div>

        {/* Error */}
        {error && (
          <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        {/* Submit */}
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={handleSubmit}
          disabled={!canSubmit || loading}
          className={`
            w-full py-4 rounded-lg font-semibold text-base transition-all
            ${canSubmit && !loading
              ? 'bg-orange-500 hover:bg-orange-600 text-white cursor-pointer'
              : 'bg-[#222] text-gray-600 cursor-not-allowed'
            }
          `}
        >
          {loading ? 'Starting analysis...' : '🔥 Roast me'}
        </motion.button>

        {/* Token link */}
        <div className="text-center">
          <button
            onClick={() => setShowToken(v => !v)}
            className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
          >
            Have a token?
          </button>
          <AnimatePresence>
            {showToken && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden pt-2"
              >
                <div className="flex gap-2">
                  <input
                    value={token}
                    onChange={e => setToken(e.target.value)}
                    placeholder="Enter your token"
                    className="flex-1 bg-[#111] border border-[#333] rounded-lg px-3 py-2 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-orange-500"
                  />
                  <button className="px-4 py-2 bg-[#222] hover:bg-[#333] text-sm text-gray-300 rounded-lg transition-colors">
                    Apply
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

      </div>
    </div>
  )
}
