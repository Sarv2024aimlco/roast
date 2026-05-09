import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, FileText, X, Flame } from 'lucide-react'
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
  'Student / Fresher', 'Junior', 'Mid-level', 'Senior', 'Staff / Principal',
]

const TWO_PLUS = ['Mid-level', 'Senior', 'Staff / Principal']

// Staggered headline words
const WORDS = [
  { text: 'Your resume.', className: 'text-zinc-100' },
  { text: 'Destroyed.', className: 'text-destroyed' },
  { text: 'Improved.', className: 'text-zinc-100' },
]

function HeadlineWord({ word, delay }) {
  return (
    <motion.span
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.22, 1, 0.36, 1] }}
      className={`inline-block mr-3 ${word.className}`}
      style={{ fontFamily: 'Space Grotesk, sans-serif' }}
    >
      {word.text}
    </motion.span>
  )
}

function DropZone({ onFile }) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const handleFile = (f) => {
    if (!f || f.type !== 'application/pdf') return
    if (f.size > 5 * 1024 * 1024) { alert('File too large. Max 5MB.'); return }
    setFile(f)
    onFile(f)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  const clear = (e) => {
    e.stopPropagation()
    setFile(null)
    onFile(null)
    inputRef.current.value = ''
  }

  return (
    <div
      className={`dropzone p-8 text-center cursor-pointer ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !file && inputRef.current.click()}
    >
      <input ref={inputRef} type="file" accept=".pdf" className="hidden"
        onChange={(e) => handleFile(e.target.files[0])} />

      {file ? (
        <div className="flex items-center justify-center gap-3">
          <FileText size={18} className="text-orange-500 shrink-0" />
          <span className="text-sm text-zinc-300 truncate max-w-xs">{file.name}</span>
          <button onClick={clear} className="text-zinc-600 hover:text-zinc-300 transition-colors ml-1">
            <X size={15} />
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex justify-center">
            <div className="w-12 h-12 rounded-xl bg-zinc-800/60 flex items-center justify-center">
              <Flame size={22} className="text-orange-500" />
            </div>
          </div>
          <div>
            <p className="text-sm text-zinc-300 font-medium">Drop your resume here</p>
            <p className="text-xs text-zinc-600 mt-1">PDF only · Max 5MB · Click to browse</p>
          </div>
        </div>
      )}
    </div>
  )
}

function AutoTextarea({ value, onChange, placeholder, maxLength, rows = 3 }) {
  const ref = useRef()

  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = 'auto'
      ref.current.style.height = Math.min(ref.current.scrollHeight, 300) + 'px'
    }
  }, [value])

  return (
    <textarea
      ref={ref}
      value={value}
      onChange={e => onChange(e.target.value.slice(0, maxLength))}
      placeholder={placeholder}
      rows={rows}
      className="roast-input auto-expand w-full px-3 py-2.5 text-sm"
    />
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

  // Pre-create session on page load for timing gate
  const [sessionId, setSessionId] = useState(null)
  useEffect(() => {
    sessionInit({
      role: 'SDE2', market: 'India',
      company_type: 'Indian Product Company (Tier 1)',
      experience_level: 'Junior',
    }).then(s => setSessionId(s.session_id)).catch(() => {})
  }, [])

  const isReferred = new URLSearchParams(window.location.search).has('ref') ||
    window.location.search.includes('utm_')

  const availableRoles = TWO_PLUS.includes(experienceLevel) ? ROLES_2PLUS : ROLES
  const canSubmit = file && role && companyType && market && experienceLevel && consent

  const handleSubmit = async () => {
    if (!canSubmit || loading) return
    setLoading(true)
    setError('')
    try {
      // Use pre-created session (satisfies timing gate)
      // If not ready yet, create one now (timing gate may fire but user waited long enough)
      let sid = sessionId
      if (!sid) {
        const session = await sessionInit({
          role, market, company_type: companyType, experience_level: experienceLevel,
        })
        sid = session.session_id
      }

      await submitAnalysis({
        sessionId: sid, file, role, company_type: companyType, market,
        experience_level: experienceLevel, userContext, jdText, githubUrl,
        optedInCorpus: optedIn,
      })
      onAnalysisStarted(sid, { role, companyType, market, experienceLevel })
    } catch (e) {
      console.error('Submit error:', e)
      // If timing gate fired, create fresh session and retry once
      if (e.message && e.message.includes('too fast')) {
        try {
          const session = await sessionInit({
            role, market, company_type: companyType, experience_level: experienceLevel,
          })
          // Wait 4 seconds then retry
          await new Promise(r => setTimeout(r, 4000))
          await submitAnalysis({
            sessionId: session.session_id, file, role, company_type: companyType, market,
            experience_level: experienceLevel, userContext, jdText, githubUrl,
            optedInCorpus: optedIn,
          })
          onAnalysisStarted(session.session_id, { role, companyType, market, experienceLevel })
          return
        } catch (e2) {
          setError(e2.message || 'Something went wrong.')
          setLoading(false)
          return
        }
      }
      let msg = 'Something went wrong. Please try again.'
      try { const p = JSON.parse(e.message); msg = p.detail || e.message } catch { msg = e.message || msg }
      setError(msg)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16">
      <div className="w-full max-w-xl space-y-7">

        {/* Headline */}
        <div className="relative headline-glow space-y-3">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight">
            {isReferred ? (
              <motion.span initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}>
                Someone shared their roast.{' '}
                <span className="text-destroyed">Get yours free.</span>
              </motion.span>
            ) : (
              WORDS.map((w, i) => <HeadlineWord key={i} word={w} delay={i * 0.15} />)
            )}
          </h1>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.4 }}
            className="text-zinc-400 text-base"
          >
            The brutal honest feedback your well-meaning friends won't give you.
          </motion.p>
        </div>

        {/* Dropzone */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.4 }}>
          <DropZone onFile={setFile} />
        </motion.div>

        {/* Dropdowns */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.4 }}
          className="grid grid-cols-2 gap-3">
          {[
            { value: experienceLevel, onChange: v => { setExperienceLevel(v); setRole('') }, options: EXPERIENCE_LEVELS, placeholder: 'Experience Level' },
            { value: role, onChange: setRole, options: availableRoles, placeholder: 'Target Role' },
            { value: companyType, onChange: setCompanyType, options: COMPANY_TYPES, placeholder: 'Company Type' },
            { value: market, onChange: setMarket, options: MARKETS, placeholder: 'Target Market' },
          ].map(({ value, onChange, options, placeholder }) => (
            <select key={placeholder} value={value} onChange={e => onChange(e.target.value)}
              className={`roast-select px-3 py-2.5 text-sm w-full ${!value ? 'unselected' : ''}`}>
              <option value="">{placeholder}</option>
              {options.map(o => <option key={o}>{o}</option>)}
            </select>
          ))}
        </motion.div>

        {/* Optional context accordion */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ delay: 0.9, duration: 0.4 }}>
          <button
            onClick={() => setShowContext(v => !v)}
            className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <motion.span animate={{ rotate: showContext ? 180 : 0 }} transition={{ duration: 0.2 }}>
              <ChevronDown size={14} />
            </motion.span>
            Add context (optional)
          </button>

          <div className={`accordion-content ${showContext ? 'open' : ''} mt-3`}>
            <div className="accordion-inner space-y-3">
              <AutoTextarea
                value={userContext}
                onChange={setUserContext}
                placeholder="Anything we should know? e.g. career gap reason, location constraint, available to join immediately"
                maxLength={500}
              />
              <AutoTextarea
                value={jdText}
                onChange={setJdText}
                placeholder="Targeting a specific role? Drop the JD here — review calibrates to this exact position."
                maxLength={2000}
                rows={3}
              />
              <input
                value={githubUrl}
                onChange={e => setGithubUrl(e.target.value)}
                placeholder="GitHub URL (optional)"
                className="roast-input w-full px-3 py-2.5 text-sm"
              />
            </div>
          </div>
        </motion.div>

        {/* Consent checkboxes */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ delay: 1.0, duration: 0.4 }}
          className="space-y-2.5">
          {[
            { checked: consent, onChange: setConsent, label: 'Your resume is processed by third-party AI providers for analysis. It is never stored by ROAST.' },
            { checked: optedIn, onChange: setOptedIn, label: 'Contribute anonymised signals to improve competitive positioning for everyone. No resume content, no personal data.' },
          ].map(({ checked, onChange, label }) => (
            <label key={label} className="flex items-start gap-3 cursor-pointer group">
              <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)}
                className="roast-checkbox mt-0.5" />
              <span className="text-xs text-zinc-500 group-hover:text-zinc-400 transition-colors leading-relaxed">
                {label}
              </span>
            </label>
          ))}
        </motion.div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="text-sm text-red-400 bg-red-400/8 border border-red-400/20 rounded-lg px-3 py-2">
              {error}
            </motion.p>
          )}
        </AnimatePresence>

        {/* Submit button */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.1, duration: 0.4 }}>
          <motion.button
            whileTap={canSubmit && !loading ? { scale: 0.97 } : {}}
            onClick={handleSubmit}
            disabled={!canSubmit || loading}
            title={!file ? 'Drop a resume first.' : !consent ? 'Accept the terms first.' : ''}
            className="roast-btn w-full py-4 text-base"
          >
            {loading ? 'Starting analysis...' : '🔥 Roast me'}
          </motion.button>
        </motion.div>

        {/* Token link */}
        <div className="text-center">
          <button onClick={() => setShowToken(v => !v)}
            className="text-xs text-zinc-600 hover:text-zinc-400 transition-colors">
            Have a token?
          </button>
          <AnimatePresence>
            {showToken && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }} className="overflow-hidden pt-2">
                <div className="flex gap-2">
                  <input value={token} onChange={e => setToken(e.target.value)}
                    placeholder="Enter your token"
                    className="roast-input flex-1 px-3 py-2 text-sm" />
                  <button className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-sm text-zinc-300 rounded-lg transition-colors">
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
