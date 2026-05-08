import { motion } from 'framer-motion'
import { TLDRBlock } from './TLDRBlock'
import { MarketPulse } from './MarketPulse'
import { ReviewDocument } from './ReviewDocument'
import { FeedbackButton, ThirdAnalysisUnlock } from './Feedback'
import { SkeletonLoader } from './SkeletonLoader'

function SectionWrapper({ children, loaded }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="border border-[#222] rounded-lg p-6"
    >
      {children}
    </motion.div>
  )
}

export function ResultsPage({ sections, sessionId, meta, analysisCount }) {
  const review = sections.review
  const marketContext = sections.market_context
  const competitive = sections.competitive

  return (
    <div className="min-h-screen px-4 py-12">
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Header */}
        <div className="space-y-1">
          <p className="text-xs text-gray-600 uppercase tracking-wider">
            {meta.role} · {meta.companyType} · {meta.market}
          </p>
          <h1 className="text-2xl font-bold">Your Roast</h1>
        </div>

        {/* TL;DR — loads last, shown first */}
        <SectionWrapper loaded={!!review}>
          {review ? (
            <TLDRBlock review={review} />
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-gray-500 uppercase tracking-wider">Bottom Line</p>
              <SkeletonLoader lines={3} />
            </div>
          )}
        </SectionWrapper>

        {/* Market Pulse */}
        <SectionWrapper loaded={!!marketContext}>
          <MarketPulse
            marketContext={marketContext}
            fullContext={null}
            loading={!marketContext}
          />
        </SectionWrapper>

        {/* The Review */}
        <SectionWrapper loaded={!!review}>
          <ReviewDocument
            review={review}
            sessionId={sessionId}
            loading={!review}
          />
        </SectionWrapper>

        {/* Competitive position summary */}
        {competitive && (
          <SectionWrapper loaded={true}>
            <div className="space-y-2">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Where You Stand</h2>
              <p className="text-2xl font-bold text-orange-500">{competitive.percentile_estimate?.range}</p>
              <p className="text-xs text-gray-500">{competitive.percentile_estimate?.confidence} estimate</p>
              <p className="text-sm text-gray-300 mt-2">{competitive.highest_leverage_change}</p>
            </div>
          </SectionWrapper>
        )}

        {/* Third analysis unlock — shown after 2nd analysis */}
        {analysisCount >= 2 && (
          <ThirdAnalysisUnlock />
        )}

        {/* Feedback */}
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
