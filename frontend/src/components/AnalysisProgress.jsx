import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check } from 'lucide-react'
import { getSessionState } from '../lib/api'

const STEPS = [
  { key: 'start',           label: 'Resume parsed' },
  { key: 'market_intel',    label: 'Loading market intelligence...' },
  { key: 'market_context',  label: 'Calibrating to your market...' },
  { key: 'red_flags',       label: 'Hunting for red flags...' },
  { key: 'six_second',      label: 'Reading first impressions + career story...' },
  { key: 'competitive',     label: 'Positioning against competitive pool...' },
  { key: 'review',          label: 'Writing your review...' },
]

function SpinnerIcon() {
  return (
    <svg className="spin shrink-0" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  )
}

export function AnalysisProgress({ sessionId, sections }) {
  const [step, setStep] = useState(0)
  const [sessionStatus, setSessionStatus] = useState('in_progress')

  // Poll session state every 3 seconds to advance steps
  useEffect(() => {
    if (!sessionId) return

    const poll = setInterval(async () => {
      try {
        const state = await getSessionState(sessionId)
        const completed = state.completed || []

        // Advance step based on what's completed
        if (completed.includes('review')) setStep(7)
        else if (completed.includes('competitive')) setStep(6)
        else if (completed.includes('six_second')) setStep(5)
        else if (completed.includes('red_flags')) setStep(4)
        else if (completed.includes('market_context')) setStep(3)
        else setStep(2)

        if (state.status === 'completed') {
          setSessionStatus('completed')
          clearInterval(poll)
        }
      } catch (e) {
        // ignore
      }
    }, 3000)

    // Start at step 1 immediately
    setStep(1)

    return () => clearInterval(poll)
  }, [sessionId])

  // Also advance from WebSocket sections
  useEffect(() => {
    if (sections.review) setStep(7)
    else if (sections.competitive) setStep(6)
    else if (sections.six_second) setStep(5)
    else if (sections.red_flags) setStep(4)
    else if (sections.market_context) setStep(3)
  }, [sections])

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md space-y-4">
        <p className="text-gray-500 text-sm mb-6">Roasting your resume...</p>

        {STEPS.map((s, i) => {
          const isDone = i < step
          const isActive = i === step

          if (i > step) return null

          return (
            <AnimatePresence key={s.key}>
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="flex items-center gap-3"
              >
                {isDone ? (
                  <Check size={16} className="text-orange-500 shrink-0" />
                ) : isActive ? (
                  <SpinnerIcon />
                ) : null}
                <span className={`text-sm ${isDone ? 'text-gray-500' : 'text-gray-200'}`}>
                  {isDone && i === 0 ? 'Resume parsed ✓' : s.label}
                </span>
              </motion.div>
            </AnimatePresence>
          )
        })}
      </div>
    </div>
  )
}
