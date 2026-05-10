import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, FileText, X, Flame, Sparkles, ArrowRight, Zap, Target, BarChart2 } from 'lucide-react'
import { sessionInit, submitAnalysis } from '../lib/api'

// ── Roasting overlay ──────────────────────────────────────────────────────────

const ROAST_LINES = [
  'Feeding your resume to the flames...',
  'Summoning 6 AI agents...',
  'Pulling live market data...',
  'No mercy mode: ON',
]

function RoastingOverlay() {
  const [lineIdx, setLineIdx] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setLineIdx(i => Math.min(i + 1, ROAST_LINES.length - 1)), 600)
    return () => clearInterval(t)
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-50 flex flex-col items-center justify-center"
      style={{ background: 'rgba(14,17,23,0.97)', backdropFilter: 'blur(12px)' }}
    >
      <div className="relative mb-8">
        {[...Array(8)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1.5 h-1.5 rounded-full bg-orange-400"
            style={{ top: '50%', left: '50%' }}
            initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
            animate={{
              x: Math.cos((i / 8) * Math.PI * 2) * 48,
              y: Math.sin((i / 8) * Math.PI * 2) * 48,
              opacity: 0, scale: 0,
            }}
            transition={{ duration: 0.8, delay: i * 0.05, repeat: Infinity, repeatDelay: 0.4 }}
          />
        ))}
        <motion.div
          animate={{ scale: [1, 1.15, 1], rotate: [0, -5, 5, 0] }}
          transition={{ duration: 0.6, repeat: Infinity }}
          className="w-20 h-20 rounded-3xl bg-orange-500/15 border border-orange-500/30 flex items-center justify-center"
        >
          <Flame size={36} className="text-orange-400" />
        </motion.div>
      </div>
      <div className="text-center space-y-3">
        <motion.h2 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className="text-xl font-bold text-[--roast-text]">🔥 Roasting...</motion.h2>
        <div className="h-6">
          <AnimatePresence mode="wait">
            <motion.p key={lineIdx} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.25 }}
              className="text-sm text-[--roast-muted] font-mono">{ROAST_LINES[lineIdx]}</motion.p>
          </AnimatePresence>
        </div>
      </div>
      <div className="flex gap-2 mt-8">
        {ROAST_LINES.map((_, i) => (
          <motion.div key={i} className="h-1.5 rounded-full"
            animate={{ width: i <= lineIdx ? 24 : 6, backgroundColor: i <= lineIdx ? '#f97316' : '#2a3347' }}
            transition={{ duration: 0.3 }} />
        ))}
      </div>
    </motion.div>
  )
}

const ROLES = [
  'Software Engineer / Associate', 'SDE1', 'SDE2 / Senior SDE',
  'Full Stack Engineer', 'Backend Engineer', 'Embedded Systems Engineer',
  'VLSI Design Engineer', 'Data Analyst', 'Data Scientist', 'Data Engineer',
  'AI/ML Engineer', 'AI Engineer', 'DevOps / SRE', 'Product Manager', 'Business Analyst',
]

const COMPANY_TYPES = [
  'Indian Product Company', 'Indian Service Company', 'FAANG / Big Tech',
  'Startup', 'Consulting / IB', 'Semiconductor / Hardware', 'MNC India (Non-FAANG)',
]

const MARKETS = ['India', 'USA', 'UAE', 'Singapore', 'UK']

const EXPERIENCE_LEVELS = [
  'Student / Fresher', 'Junior', 'Mid-level', 'Senior', 'Staff / Principal',
]

// ── What you get strip ────────────────────────────────────────────────────────

const FEATURES = [
  { icon: Zap,      label: 'Shortlist verdict',    desc: 'Pass or fail at named companies' },
  { icon: Target,   label: 'Red flag scan',         desc: 'Every phrase that kills your chances' },
  { icon: BarChart2, label: 'Percentile + CTC',     desc: 'Where you stand vs real applicants' },
]

// ── Drop zone ─────────────────────────────────────────────────────────────────

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
      className={`dropzone cursor-pointer ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
      style={{ padding: file ? '20px 24px' : '32px 24px' }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !file && inputRef.current.click()}
    >
      <input ref={inputRef} type="file" accept=".pdf" className="hidden"
        onChange={(e) => handleFile(e.target.files[0])} />

      {file ? (
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-orange-500/15 flex items-center justify-center shrink-0">
              <FileText size={16} className="text-orange-400" />
            </div>
            <div className="text-left min-w-0">
              <p className="text-sm text-[--roast-text] font-medium truncate max-w-[180px] sm:max-w-xs">{file.name}</p>
              <p className="text-xs text-[--roast-muted]">{(file.size / 1024).toFixed(0)} KB · PDF ready</p>
            </div>
          </div>
          <button onClick={clear} className="text-[--roast-placeholder] hover:text-[--roast-text] transition-colors shrink-0 p-1">
            <X size={14} />
          </button>
        </div>
      ) : (
        <div className="text-center space-y-3">
          <div className="flex justify-center">
            <motion.div
              animate={{ y: [0, -4, 0] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
              className="w-12 h-12 rounded-2xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center"
            >
              <Flame size={22} className="text-orange-400" />
            </motion.div>
          </div>
          <div>
            <p className="text-sm font-semibold text-[--roast-text-2]">Drop your resume here</p>
            <p className="text-xs text-[--roast-placeholder] mt-0.5">PDF only · Max 5MB · Click to browse</p>
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
    <textarea ref={ref} value={value}
      onChange={e => onChange(e.target.value.slice(0, maxLength))}
      placeholder={placeholder} rows={rows}
      className="roast-input auto-expand w-full px-4 py-3 text-sm" />
  )
}

// ── Main component ────────────────────────────────────────────────────────────

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
  const [consent, setConsent] = useState(false)
  const [optedIn, setOptedIn] = useState(false)
  const [loading, setLoading] = useState(false)
  const [roasting, setRoasting] = useState(false)
  const [error, setError] = useState('')
  const [sessionId, setSessionId] = useState(null)

  useEffect(() => {
    sessionInit({
      role: 'SDE1', market: 'India',
      company_type: 'Indian Product Company',
      experience_level: 'Student / Fresher',
    }).then(s => setSessionId(s.session_id)).catch(() => {})
  }, [])

  const isReferred = new URLSearchParams(window.location.search).has('ref') ||
    window.location.search.includes('utm_')

  const canSubmit = file && role && companyType && market && experienceLevel && consent

  const handleSubmit = async () => {
    if (!canSubmit || loading) return
    setLoading(true)
    setError('')
    try {
      let sid = sessionId
      if (!sid) {
        const session = await sessionInit({ role, market, company_type: companyType, experience_level: experienceLevel })
        sid = session.session_id
      }
      await submitAnalysis({ sessionId: sid, file, role, company_type: companyType, market, experience_level: experienceLevel, userContext, jdText, githubUrl, optedInCorpus: optedIn })
      setRoasting(true)
      await new Promise(r => setTimeout(r, 2500))
      onAnalysisStarted(sid, { role, companyType, market, experienceLevel })
    } catch (e) {
      if (e.message?.includes('too fast')) {
        try {
          const session = await sessionInit({ role, market, company_type: companyType, experience_level: experienceLevel })
          await new Promise(r => setTimeout(r, 4000))
          await submitAnalysis({ sessionId: session.session_id, file, role, company_type: companyType, market, experience_level: experienceLevel, userContext, jdText, githubUrl, optedInCorpus: optedIn })
          setRoasting(true)
          await new Promise(r => setTimeout(r, 2500))
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
    <>
      <AnimatePresence>
        {roasting && <RoastingOverlay />}
      </AnimatePresence>

      <div className="min-h-[calc(100vh-52px)] flex flex-col items-center justify-center px-4 py-10 sm:py-16 relative z-10 overflow-x-hidden">
        <div className="w-full max-w-lg space-y-6">

          {/* ── Headline ── */}
          <div className="relative headline-glow space-y-3 text-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-orange-500/10 border border-orange-500/20 text-xs text-orange-400 font-medium"
            >
              <Sparkles size={11} />
              {isReferred ? 'Someone shared their roast' : 'Live market data · 6 AI agents · Free'}
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.1]"
            >
              {isReferred ? (
                <>Get your resume<br /><span className="text-destroyed">roasted free.</span></>
              ) : (
                <>Your resume.<br /><span className="text-destroyed">Destroyed.</span> Improved.</>
              )}
            </motion.h1>

            <motion.p
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              transition={{ delay: 0.35, duration: 0.4 }}
              className="text-[--roast-muted] text-sm sm:text-base leading-relaxed max-w-sm mx-auto"
            >
              Brutally honest feedback calibrated to live hiring data —
              not generic tips from a chatbot.
            </motion.p>
          </div>

          {/* ── Feature strip ── */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.4 }}
            className="grid grid-cols-3 gap-2"
          >
            {FEATURES.map(({ icon: Icon, label, desc }) => (
              <div key={label} className="flex flex-col items-center text-center gap-1.5 px-2 py-3 rounded-xl bg-[--roast-surface] border border-[--roast-border]">
                <Icon size={14} className="text-orange-400" />
                <p className="text-xs font-semibold text-[--roast-text-2] leading-tight">{label}</p>
                <p className="text-[10px] text-[--roast-placeholder] leading-tight">{desc}</p>
              </div>
            ))}
          </motion.div>

          {/* ── Drop zone ── */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45, duration: 0.4 }}>
            <DropZone onFile={setFile} />
          </motion.div>

          {/* ── Selects ── */}
          <motion.div
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.4 }}
          >
            <p className="text-[10px] text-[--roast-placeholder] uppercase tracking-wider mb-2 font-mono">
              Calibrate your roast
            </p>
            <div className="grid grid-cols-2 gap-2.5">
              {[
                { value: experienceLevel, onChange: v => { setExperienceLevel(v); setRole('') }, options: EXPERIENCE_LEVELS, placeholder: 'Experience level' },
                { value: role, onChange: setRole, options: ROLES, placeholder: 'Target role' },
                { value: companyType, onChange: setCompanyType, options: COMPANY_TYPES, placeholder: 'Company type' },
                { value: market, onChange: setMarket, options: MARKETS, placeholder: 'Target market' },
              ].map(({ value, onChange, options, placeholder }) => (
                <select key={placeholder} value={value} onChange={e => onChange(e.target.value)}
                  className={`roast-select px-3 py-2.5 text-sm w-full ${!value ? 'unselected' : ''}`}>
                  <option value="">{placeholder}</option>
                  {options.map(o => <option key={o}>{o}</option>)}
                </select>
              ))}
            </div>
          </motion.div>

          {/* ── Optional context ── */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.55, duration: 0.4 }}>
            <button
              onClick={() => setShowContext(v => !v)}
              className="flex items-center gap-2 text-xs text-[--roast-muted] hover:text-[--roast-text] transition-colors"
            >
              <motion.span animate={{ rotate: showContext ? 180 : 0 }} transition={{ duration: 0.2 }}>
                <ChevronDown size={13} />
              </motion.span>
              Add context · JD · GitHub (optional)
            </button>

            <div className={`accordion-content ${showContext ? 'open' : ''} mt-3`}>
              <div className="accordion-inner space-y-2.5">
                <AutoTextarea value={userContext} onChange={setUserContext}
                  placeholder="Anything we should know? e.g. career gap reason, location constraint, available to join immediately"
                  maxLength={500} />
                <AutoTextarea value={jdText} onChange={setJdText}
                  placeholder="Paste a JD here — the review calibrates to this exact role."
                  maxLength={2000} rows={3} />
                <input value={githubUrl} onChange={e => setGithubUrl(e.target.value)}
                  placeholder="GitHub URL (optional)"
                  className="roast-input w-full px-4 py-2.5 text-sm" />
              </div>
            </div>
          </motion.div>

          {/* ── Consent ── */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6, duration: 0.4 }}
            className="space-y-2">
            {[
              { checked: consent, onChange: setConsent, label: 'Your resume is processed by third-party AI providers for analysis. It is never stored by ROAST.' },
              { checked: optedIn, onChange: setOptedIn, label: 'Contribute anonymised signals to improve competitive positioning for everyone. No resume content, no personal data.' },
            ].map(({ checked, onChange, label }) => (
              <label key={label} className="consent-row flex items-start gap-3 cursor-pointer">
                <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)}
                  className="roast-checkbox mt-0.5 shrink-0" />
                <span className="text-xs text-[--roast-muted] leading-relaxed">{label}</span>
              </label>
            ))}
          </motion.div>

          {/* ── Error ── */}
          <AnimatePresence>
            {error && (
              <motion.p initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="text-sm text-red-400 bg-red-500/8 border border-red-500/20 rounded-xl px-4 py-3">
                {error}
              </motion.p>
            )}
          </AnimatePresence>

          {/* ── Submit ── */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.65, duration: 0.4 }}>
            <motion.button
              whileTap={canSubmit && !loading ? { scale: 0.97 } : {}}
              onClick={handleSubmit}
              disabled={!canSubmit || loading}
              className="roast-btn w-full py-4 text-base flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full spin" />
                  Starting analysis...
                </>
              ) : (
                <>
                  <Flame size={16} />
                  Roast my resume
                  {canSubmit && <ArrowRight size={15} className="ml-1 opacity-70" />}
                </>
              )}
            </motion.button>
          </motion.div>

        </div>
      </div>
    </>
  )
}
