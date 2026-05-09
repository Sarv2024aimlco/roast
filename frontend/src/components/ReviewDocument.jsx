import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { SkeletonLoader } from './SkeletonLoader'
import { useInferenceToggle } from '../hooks/useInferenceToggle'
import { submitFollowup } from '../lib/api'

function Section({ title, content, followups, sessionId, sectionKey }) {
  const [usedFollowup, setUsedFollowup] = useState(false)
  const [activeQuestion, setActiveQuestion] = useState(null)
  const [answer, setAnswer] = useState('')
  const [loadingAnswer, setLoadingAnswer] = useState(false)

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
    <div className="space-y-3">
      <h3 className="text-xs font-semibold text-[--roast-muted] uppercase tracking-wider">{title}</h3>
      <p className="text-sm text-[--roast-text] leading-[1.75] whitespace-pre-wrap">{content}</p>

      {followups?.length > 0 && !usedFollowup && (
        <div className="flex flex-wrap gap-2 pt-1">
          {followups.map((q, i) => (
            <button
              key={i}
              onClick={() => handleFollowup(q)}
              className="text-xs px-3 py-1.5 bg-[--roast-surface-2] border border-[--roast-border] rounded-full text-[--roast-muted] hover:border-orange-500/40 hover:text-[--roast-text] transition-all"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <AnimatePresence>
        {activeQuestion && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="border-l-2 border-orange-500/30 pl-4 space-y-2 mt-2"
          >
            <p className="text-xs text-[--roast-muted]">{activeQuestion}</p>
            {loadingAnswer ? (
              <SkeletonLoader lines={2} />
            ) : (
              <p className="text-sm text-[--roast-text] leading-relaxed">{answer}</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function ReviewDocument({ review, sessionId, loading }) {
  const [showInference, setShowInference] = useInferenceToggle()

  if (loading) return (
    <div className="space-y-5">
      <h2 className="text-xs font-semibold text-[--roast-muted] uppercase tracking-wider">The Review</h2>
      <SkeletonLoader lines={6} />
    </div>
  )

  if (!review) return null

  return (
    <div className="space-y-7">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-semibold text-[--roast-muted] uppercase tracking-wider">The Review</h2>
        <button
          onClick={() => setShowInference(v => !v)}
          className="text-xs text-[--roast-muted] hover:text-[--roast-text] transition-colors"
        >
          Recruiter reasoning:{' '}
          <span className={showInference ? 'text-orange-400' : 'text-[--roast-placeholder]'}>
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
      />

      <div className="h-px bg-[--roast-border]" />

      <Section
        title="What's Hurting You"
        content={showInference ? review.whats_hurting_section : review.whats_hurting_section?.replace(/\([^)]*recruiter[^)]*\)/gi, '')}
        followups={review.whats_hurting_followups}
        sessionId={sessionId}
        sectionKey="whats_hurting"
      />

      <div className="h-px bg-[--roast-border]" />

      <Section
        title="Career Story"
        content={review.career_story_section}
        followups={review.career_story_followups}
        sessionId={sessionId}
        sectionKey="career_story"
      />

      <div className="h-px bg-[--roast-border]" />

      <Section
        title="Competitive Position"
        content={review.competitive_position_section}
        followups={review.competitive_followups}
        sessionId={sessionId}
        sectionKey="competitive"
      />

      <div className="h-px bg-[--roast-border]" />

      <Section
        title="Action Plan"
        content={review.action_plan_section}
        followups={[]}
        sessionId={sessionId}
        sectionKey="action_plan"
      />

      {review.jd_alignment_section && (
        <>
          <div className="h-px bg-[--roast-border]" />
          <Section
            title="JD Alignment"
            content={review.jd_alignment_section}
            followups={[]}
            sessionId={sessionId}
            sectionKey="jd_alignment"
          />
        </>
      )}
    </div>
  )
}
