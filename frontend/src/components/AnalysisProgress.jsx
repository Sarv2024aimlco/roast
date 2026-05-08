import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { getSessionState } from '../lib/api'

const STEPS = [
  { key: 'start',          label: 'Extracting text from resume',        done_label: 'Resume parsed' },
  { key: 'market_intel',   label: 'Loading market intelligence',         done_label: 'Market intelligence loaded' },
  { key: 'market_context', label: 'Calibrating to your market',          done_label: 'Market calibrated' },
  { key: 'red_flags',      label: 'Hunting for red flags',               done_label: 'Red flags identified' },
  { key: 'six_second',     label: 'Reading first impressions',           done_label: 'Career story analysed' },
  { key: 'competitive',    label: 'Positioning against applicant pool',  done_label: 'Competitive position mapped' },
  { key: 'technical',      label: 'Evaluating technical depth',          done_label: 'Technical depth evaluated' },
  { key: 'review',         label: 'Writing your review',                 done_label: 'Review complete' },
]

function TerminalLine({ step, isDone, isActive, index }) {
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.25, delay: index * 0.05 }}
        className="terminal-line flex items-center gap-3"
      >
        <span className={isDone ? 'text-orange-500' : isActive ? 'text-zinc-400' : 'text-zinc-700'}>
          {isDone ? '✓' : isActive ? '›' : ' '}
        </span>
        <span className={isDone ? 'text-zinc-500' : isActive ? 'text-zinc-200' : 'text-zinc-700'}>
          {isDone ? step.done_label : step.label}
          {isActive && <span className="terminal-cursor ml-1" />}
        </span>
        {isDone && <span className="text-zinc-700 text-xs ml-auto">[Done]</span>}
        {isActive && <span className="text-orange-500/60 text-xs ml-auto">[Active]</span>}
      </motion.div>
    </AnimatePresence>
  )
}

export function AnalysisProgress({ sessionId, sections }) {
  const [step, setStep] = useState(1)

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
      } catch (e) { /* ignore */ }
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

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-lg">

        {/* Terminal header */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="mb-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-3 h-3 rounded-full bg-red-500/60" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
            <div className="w-3 h-3 rounded-full bg-green-500/60" />
            <span className="text-zinc-600 text-xs ml-2 font-mono">roast — analysis</span>
          </div>
          <p className="terminal-line text-zinc-500">
            <span className="text-orange-500">$</span> roast analyse --resume resume.pdf
          </p>
        </motion.div>

        {/* Steps */}
        <div className="space-y-2">
          {STEPS.map((s, i) => {
            const isDone = i < step
            const isActive = i === step
            if (i > step) return null
            return (
              <TerminalLine
                key={s.key}
                step={s}
                isDone={isDone}
                isActive={isActive}
                index={i}
              />
            )
          })}
        </div>

        {/* Progress bar */}
        <div className="mt-8 h-0.5 bg-zinc-800 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-orange-600 to-orange-400 rounded-full"
            initial={{ width: '0%' }}
            animate={{ width: `${(step / STEPS.length) * 100}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
        <p className="text-xs text-zinc-600 mt-2 font-mono">
          {Math.round((step / STEPS.length) * 100)}% complete
        </p>

      </div>
    </div>
  )
}
