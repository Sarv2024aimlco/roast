import { SkeletonLoader } from './SkeletonLoader'

export function MarketPulse({ marketContext, fullContext, loading }) {
  if (loading) return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Market Pulse</h2>
      <SkeletonLoader lines={4} />
    </div>
  )

  if (!marketContext) return null

  const freshness = fullContext?.distilled?.freshness_label || 'Current'
  const breaking = fullContext?.breaking_signal
  const breakingAvailable = fullContext?.breaking_available

  const freshnessColor = {
    'Current': 'text-green-400',
    'Recent': 'text-yellow-400',
    'Needs Refresh': 'text-red-400',
  }[freshness] || 'text-gray-400'

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Market Pulse</h2>
        <span className={`text-xs ${freshnessColor}`}>{freshness}</span>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="space-y-1">
          <p className="text-gray-500 text-xs">Sentiment</p>
          <p className="text-gray-200">{marketContext.live_context_summary}</p>
        </div>
        <div className="space-y-1">
          <p className="text-gray-500 text-xs">Salary band</p>
          <p className="text-gray-200">{fullContext?.distilled?.salary_band || 'data unavailable'}</p>
        </div>
        <div className="space-y-1">
          <p className="text-gray-500 text-xs">Top skills</p>
          <p className="text-gray-200">{fullContext?.distilled?.top_required_skills?.slice(0, 4).join(', ') || '—'}</p>
        </div>
        <div className="space-y-1">
          <p className="text-gray-500 text-xs">Competitive pool</p>
          <p className="text-gray-200 text-xs">{marketContext.competitive_pool_description?.slice(0, 80)}...</p>
        </div>
      </div>

      <div className="border-t border-[#222] pt-3">
        <p className="text-xs text-gray-500">
          Breaking signal:{' '}
          {breakingAvailable
            ? <span className="text-green-400">{breaking}</span>
            : <span className="text-gray-600">⚠ Unavailable — showing cached intel</span>
          }
        </p>
      </div>
    </div>
  )
}
