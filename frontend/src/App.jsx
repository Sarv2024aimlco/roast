import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { LandingPage } from './components/LandingPage'
import { AnalysisProgress } from './components/AnalysisProgress'
import { ResultsPage } from './components/ResultsPage'
import { useWebSocket } from './hooks/useWebSocket'
import './index.css'

// Track analysis count in localStorage for third-analysis unlock
function getAnalysisCount() {
  return parseInt(localStorage.getItem('roast_analysis_count') || '0')
}
function incrementAnalysisCount() {
  const count = getAnalysisCount() + 1
  localStorage.setItem('roast_analysis_count', count)
  return count
}

function AnalysisView({ sessionId, meta }) {
  const { sections, status } = useWebSocket(sessionId)

  if (status === 'complete' || sections.review) {
    return (
      <ResultsPage
        sections={sections}
        sessionId={sessionId}
        meta={meta}
        analysisCount={getAnalysisCount()}
      />
    )
  }

  return <AnalysisProgress sessionId={sessionId} sections={sections} />
}

export default function App() {
  const [view, setView] = useState('landing') // landing | analysis
  const [sessionId, setSessionId] = useState(null)
  const [meta, setMeta] = useState(null)

  const handleAnalysisStarted = (sid, metaData) => {
    incrementAnalysisCount()
    setSessionId(sid)
    setMeta(metaData)
    setView('analysis')
  }

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-gray-100">
      <AnimatePresence mode="wait">
        {view === 'landing' && (
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <LandingPage onAnalysisStarted={handleAnalysisStarted} />
          </motion.div>
        )}

        {view === 'analysis' && (
          <motion.div
            key="analysis"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <AnalysisView
              sessionId={sessionId}
              meta={meta}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Back to home — shown during/after analysis */}
      {view === 'analysis' && (
        <button
          onClick={() => setView('landing')}
          className="fixed top-4 left-4 text-xs text-gray-600 hover:text-gray-400 transition-colors"
        >
          ← New roast
        </button>
      )}
    </div>
  )
}
