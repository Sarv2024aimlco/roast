import { motion } from 'framer-motion'
import { TLDRBlock } from './TLDRBlock'
import { MarketPulse } from './MarketPulse'
import { ReviewDocument } from './ReviewDocument'
import { FeedbackButton, ThirdAnalysisUnlock } from './Feedback'
import { SkeletonLoader } from './SkeletonLoader'

function Card({ children, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.22, 1, 0.36, 1] }}
      className="roast-card"
    >
      {children}
    </motion.div>
  )
}

function PercentileBar({ range, confidence }) {
  const match = range?.match(/(\d+)(?:th|st|nd|rd)[–\-](\d+)/)
  const single = range?.match(/(\d+)(?:th|st|nd|rd)\s*percentile/)
  let pct = 50
  if (match) pct = (parseInt(match[1]) + parseInt(match[2])) / 2
  else if (single) pct = parseInt(single[1])

  // Split "60th-70th percentile among freshers" into numeric part + label
  const numericMatch = range?.match(/^([\d\w\-–]+(?:th|st|nd|rd))/)
  const numericPart = numericMatch ? numericMatch[0] : range
  const labelPart = numericMatch ? range?.slice(numericPart.length) : ''

  const confidenceLabel = confidence === 'calibrated'
    ? 'Based on real applicant data'
    : 'Estimated from market signals'

  return (
    <div className="space-y-3">
      <div className="text-xl sm:text-2xl font-bold">
        <span className="text-orange-400">{numericPart}</span>
        {labelPart && <span className="text-[--roast-text]">{labelPart}</span>}
      </div>
      <div className="percentile-bar">
        <motion.div
          className="percentile-bar-fill"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
      <p className="text-xs text-[--roast-muted]">{confidenceLabel}</p>
    </div>
  )
}

export function ResultsPage({ sections, sessionId, meta, analysisCount }) {
  const review = sections.review
  const marketContext = sections.market_context
  const competitive = sections.competitive

  return (
    <div className="min-h-screen px-4 py-10 sm:py-14">
      <div className="max-w-2xl mx-auto space-y-4 sm:space-y-5">

        {/* Header */}
        <div className="space-y-1 px-1">
          <p className="text-xs text-[--roast-muted] uppercase tracking-wider font-mono">
            {meta.role} · {meta.companyType} · {meta.market}
          </p>
          <h1 className="text-xl sm:text-2xl font-bold">Your Roast</h1>
        </div>

        {/* TL;DR */}
        <Card delay={0.05}>
          {review ? (
            <TLDRBlock review={review} />
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-[--roast-muted] uppercase tracking-wider">Bottom Line</p>
              <SkeletonLoader lines={3} />
            </div>
          )}
        </Card>

        {/* Market Pulse */}
        <Card delay={0.1}>
          <MarketPulse
            marketContext={marketContext}
            fullContext={null}
            loading={!marketContext}
          />
        </Card>

        {/* The Review */}
        <Card delay={0.15}>
          <ReviewDocument
            review={review}
            sessionId={sessionId}
            loading={!review}
          />
        </Card>

        {/* Competitive position */}
        {competitive && (
          <Card delay={0.2}>
            <div className="space-y-4">
              <h2 className="text-xs font-semibold text-[--roast-muted] uppercase tracking-wider">Where You Stand</h2>
              <PercentileBar range={competitive.percentile_estimate?.range} confidence={competitive.percentile_estimate?.confidence} />
              <div className="h-px bg-[--roast-border]" />
              <p className="text-sm text-[--roast-text] leading-relaxed">{competitive.highest_leverage_change}</p>
            </div>
          </Card>
        )}

        {analysisCount >= 2 && <ThirdAnalysisUnlock />}

        {review && (
          <FeedbackButton
            sessionId={sessionId}
            role={meta.role}
            market={meta.market}
            companyType={meta.companyType}
          />
        )}

      </div>
    </div>
  )
}
