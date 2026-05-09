import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Flame } from 'lucide-react'
import { getSessionState } from '../lib/api'

const STEPS = [
  { key: 'start',          label: 'Parsing resume',                      done: 'Resume parsed' },
  { key: 'market_intel',   label: 'Loading live market intelligence',    done: 'Market intelligence loaded' },
  { key: 'market_context', label: 'Calibrating to your market',          done: 'Market calibrated' },
  { key: 'red_flags',      label: 'Hunting for red flags',               done: 'Red flags identified' },
  { key: 'six_second',     label: 'Simulating recruiter scan',           done: 'Career story analysed' },
  { key: 'competitive',    label: 'Mapping competitive position',        done: 'Competitive position mapped' },
  { key: 'technical',      label: 'Deep technical evaluation',           done: 'Technical depth evaluated' },
  { key: 'review',         label: 'Writing your roast',                  done: 'Roast complete' },
]

const ROAST_QUOTES = [
  'Pulling live job postings from Naukri...',
  'Checking what Razorpay is actually hiring for...',
  'Comparing against real applicants at your level...',
  'Reading between the lines of your resume...',
  'Calibrating to the Bengaluru market...',
  'Running 6 agents in parallel...',
]

export function AnalysisProgress({ sessionId, sections }) {
  const [step, setStep] = useState(1)
  const [quoteIdx, setQuoteIdx] = useState(0)

  useEffect(() => {
    const q = setInterval(() => setQuoteIdx(i => (i + 1) % ROAST_QUOTES.length), 3000)
    return () => clearInterval(q)
  }, [])

  useEffect(() => {
    if (!sessionId) return
    const poll = setInterval(async () => {
      try {
        const state = await getSessionState(sessionId)
        const completed = state.completed || []
        if (completed.includes('review')) setStep(8)
        else if (completed.includes('technical_depth')) setStep(7)
        else if (completed.includes('competitive')) setStep(6)
        else if (completed.includes('six_second')) setStep(5)
        else if (completed.includes('red_flags')) setStep(4)
        else if (completed.includes('market_context')) setStep(3)
        else setStep(2)
        if (state.status === 'completed') clearInterval(poll)
      } catch { /* ignore */ }
    }, 3000)
    setStep(1)
    return () => clearInterval(poll)
  }, [sessionId])

  useEffect(() => {
    if (sections.review) setStep(8)
    else if (sections.technical_depth) setStep(7)
    else if (sections.competitive) setStep(6)
    else if (sections.six_second) setStep(5)
    else if (sections.red_flags) setStep(4)
    else if (sections.market_context) setStep(3)
  }, [sections])

  const pct = Math.round((step / STEPS.length) * 100)

  return (
    <div className="min-h-[calc(100vh-52px)] flex flex-col items-center justify-center px-4 relative z-10">
      <div className="w-full max-w-md space-y-8">

        {/* ROAST branding */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center space-y-3"
        >
          <motion.div
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-orange-500/10 border border-orange-500/20"
          >
            <Flame size={28} className="text-orange-400" />
          </motion.div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Roasting your resume</h2>
            <AnimatePresence mode="wait">
              <motion.p
                key={quoteIdx}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.3 }}
                className="text-sm text-[--roast-muted] mt-1"
              >
                {ROAST_QUOTES[quoteIdx]}
              </motion.p>
            </AnimatePresence>
          </div>
        </motion.div>

        {/* Terminal */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="roast-card"
        >
          {/* Terminal chrome */}
          <div className="flex items-center gap-2 mb-5 pb-4 border-b border-[--roast-border]">
            <div className="w-3 h-3 rounded-full bg-red-500/50" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
            <div className="w-3 h-3 rounded-full bg-green-500/50" />
            <span className="text-[--roast-placeholder] text-xs font-mono ml-2">roast — analysis in progress</span>
          </div>

          {/* Steps */}
          <div className="space-y-2.5">
            {STEPS.map((s, i) => {
              const isDone = i < step
              const isActive = i === step
              if (i > step) return null
              return (
                <motion.div
                  key={s.key}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.25, delay: i * 0.04 }}
                  className="terminal-line flex items-center gap-3"
                >
                  <span className={`w-4 text-center shrink-0 ${isDone ? 'text-emerald-400' : isActive ? 'text-orange-400' : 'text-[--roast-placeholder]'}`}>
                    {isDone ? '✓' : isActive ? '›' : ' '}
                  </span>
                  <span className={`flex-1 ${isDone ? 'text-[--roast-placeholder]' : isActive ? 'text-[--roast-text]' : 'text-[--roast-placeholder]'}`}>
                    {isDone ? s.done : s.label}
                    {isActive && <span className="terminal-cursor" />}
                  </span>
                  {isDone && (
                    <span className="text-[--roast-placeholder] text-xs shrink-0">done</span>
                  )}
                  {isActive && (
                    <span className="text-orange-500/60 text-xs shrink-0">running</span>
                  )}
                </motion.div>
              )
            })}
          </div>

          {/* Progress */}
          <div className="mt-6 space-y-2">
            <div className="h-1.5 bg-[--roast-surface-2] rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: 'linear-gradient(90deg, #f97316, #fb923c)' }}
                initial={{ width: '0%' }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.6, ease: 'easeOut' }}
              />
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs text-[--roast-placeholder] font-mono">{pct}% complete</span>
              <span className="text-xs text-[--roast-placeholder] font-mono">~{Math.max(0, Math.round((STEPS.length - step) * 2))}s remaining</span>
            </div>
          </div>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center text-xs text-[--roast-placeholder]"
        >
          6 AI agents · Live market data · Takes ~10-15 seconds
        </motion.p>

      </div>
    </div>
  )
}
