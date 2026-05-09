import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, AlertTriangle, BookOpen, BarChart2, Zap, AlignLeft, MessageCircle } from 'lucide-react'
import { SkeletonLoader } from './SkeletonLoader'
import { useInferenceToggle } from '../hooks/useInferenceToggle'
import { submitFollowup } from '../lib/api'

const SECTION_CONFIG = {
  working:     { icon: CheckCircle,  color: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/5' },
  hurting:     { icon: AlertTriangle, color: 'text-red-400',    border: 'border-red-500/30',     bg: 'bg-red-500/5' },
  career:      { icon: BookOpen,     color: 'text-blue-400',    border: 'border-blue-500/30',    bg: 'bg-blue-500/5' },
  competitive: { icon: BarChart2,    color: 'text-purple-400',  border: 'border-purple-500/30',  bg: 'bg-purple-500/5' },
  action:      { icon: Zap,          color: 'text-orange-400',  border: 'border-orange-500/30',  bg: 'bg-orange-500/5' },
  jd:          { icon: AlignLeft,    color: 'text-cyan-400',    border: 'border-cyan-500/30',    bg: 'bg-cyan-500/5' },
}

function Section({ title, content, followups, sessionId, sectionKey, configKey }) {
  const [usedFollowup, setUsedFollowup] = useState(false)
  const [activeQuestion, setActiveQuestion] = useState(null)
  const [answer, setAnswer] = useState('')
  const [loadingAnswer, setLoadingAnswer] = useState(false)
  const cfg = SECTION_CONFIG[configKey] || SECTION_CONFIG.action
  const Icon = cfg.icon

  const handleFollowup = async (question) => {
    if (usedFollowup) return
    setActiveQuestion(question)
    setLoadingAnswer(true)
    try {
      const res = await submitFollowup({ sessionId, section: sectionKey, question })
      setAnswer(res.answer)
      setUsedFollowup(true)
    } catch {
      setAnswer('Unable to load answer. Please try again.')
    }
    setLoadingAnswer(false)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className={`section-card border-l-2 ${cfg.border}`}
    >
      {/* Section header */}
      <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-lg ${cfg.bg} mb-3`}>
        <Icon size={12} className={cfg.color} />
        <span className={`text-xs font-semibold uppercase tracking-wider ${cfg.color}`}>{title}</span>
      </div>

      {/* Content */}
      <p className="text-sm text-[--roast-text-2] leading-[1.8] whitespace-pre-wrap">{content}</p>

      {/* Follow-up questions */}
      {followups?.length > 0 && !usedFollowup && (
        <div className="flex flex-wrap gap-2 mt-4">
          {followups.map((q, i) => (
            <button
              key={i}
              onClick={() => handleFollowup(q)}
              className="followup-pill"
            >
              <MessageCircle size={10} />
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Follow-up answer */}
      <AnimatePresence>
        {activeQuestion && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mt-4 border-l-2 ${cfg.border} pl-4 space-y-2`}
          >
            <p className="text-xs text-[--roast-muted] italic">{activeQuestion}</p>
            {loadingAnswer ? (
              <SkeletonLoader lines={2} />
            ) : (
              <p className="text-sm text-[--roast-text-2] leading-relaxed">{answer}</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function ReviewDocument({ review, sessionId, loading }) {
  const [showInference, setShowInference] = useInferenceToggle()

  if (loading) return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="section-label">The Review</div>
      </div>
      <SkeletonLoader lines={8} />
    </div>
  )

  if (!review) return null

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="section-label">The Review</div>
        <button
          onClick={() => setShowInference(v => !v)}
          className="text-xs text-[--roast-muted] hover:text-[--roast-text] transition-colors flex items-center gap-1.5"
        >
          Recruiter reasoning:{' '}
          <span className={`font-medium ${showInference ? 'text-orange-400' : 'text-[--roast-placeholder]'}`}>
            {showInference ? 'ON' : 'OFF'}
          </span>
        </button>
      </div>

      <Section
        title="What's Working"
        content={review.whats_working_section}
        followups={review.six_second_followups}
        sessionId={sessionId}
        sectionKey="six_second"
        configKey="working"
      />

      <Section
        title="What's Hurting You"
        content={showInference ? review.whats_hurting_section : review.whats_hurting_section?.replace(/\([^)]*recruiter[^)]*\)/gi, '')}
        followups={review.whats_hurting_followups}
        sessionId={sessionId}
        sectionKey="whats_hurting"
        configKey="hurting"
      />

      <Section
        title="Career Story"
        content={review.career_story_section}
        followups={review.career_story_followups}
        sessionId={sessionId}
        sectionKey="career_story"
        configKey="career"
      />

      <Section
        title="Competitive Position"
        content={review.competitive_position_section}
        followups={review.competitive_followups}
        sessionId={sessionId}
        sectionKey="competitive"
        configKey="competitive"
      />

      <Section
        title="Action Plan"
        content={review.action_plan_section}
        followups={[]}
        sessionId={sessionId}
        sectionKey="action_plan"
        configKey="action"
      />

      {review.jd_alignment_section && (
        <Section
          title="JD Alignment"
          content={review.jd_alignment_section}
          followups={[]}
          sessionId={sessionId}
          sectionKey="jd_alignment"
          configKey="jd"
        />
      )}
    </div>
  )
}
