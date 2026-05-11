import { Copy, Check, AlertTriangle, Wrench, Zap } from 'lucide-react'
import { useState } from 'react'
import { motion } from 'framer-motion'

function ShortlistBadge({ text }) {
  const lower = text.toLowerCase()
  let color, label, dot
  if (lower.includes('strong') || lower.includes('high') || lower.includes('top') || lower.includes('clears')) {
    color = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25'
    dot = 'bg-emerald-400'
    label = 'Strong'
  } else if (lower.includes('low') || lower.includes('weak') || lower.includes('below') || lower.includes('struggle')) {
    color = 'bg-red-500/15 text-red-400 border-red-500/25'
    dot = 'bg-red-400'
    label = 'Low'
  } else {
    color = 'bg-yellow-500/15 text-yellow-400 border-yellow-500/25'
    dot = 'bg-yellow-400'
    label = 'Medium'
  }
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border font-mono ${color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  )
}

export function TLDRBlock({ review }) {
  const [copied, setCopied] = useState(false)

  const copy = () => {
    const text = `ROAST RESULTS\n\nShortlist chance: ${review.tldr_shortlist_chance}\nBiggest blocker: ${review.tldr_biggest_blocker}\nFix first: ${review.tldr_fix_first}`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="text-xs font-semibold text-[--roast-muted] uppercase tracking-widest">Bottom Line</span>
          <ShortlistBadge text={review.tldr_shortlist_chance} />
        </div>
        <button onClick={copy} className="text-[--roast-muted] hover:text-[--roast-text] transition-colors p-1 rounded-lg hover:bg-white/5">
          {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
        </button>
      </div>

      {/* Shortlist verdict — HERO. This is what they read first. */}
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="rounded-2xl border border-orange-500/20 px-5 py-5"
        style={{ background: 'linear-gradient(135deg, rgba(249,115,22,0.07) 0%, rgba(249,115,22,0.03) 100%)' }}
      >
        <div className="flex items-center gap-2 mb-2">
          <Zap size={13} className="text-orange-400 shrink-0" />
          <span className="text-[10px] font-semibold text-orange-400/70 uppercase tracking-wider">Shortlist chance</span>
        </div>
        <p className="text-base sm:text-lg text-[--roast-text] leading-relaxed font-medium">{review.tldr_shortlist_chance}</p>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {/* Biggest blocker */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.08 }}
          className="rounded-xl bg-red-500/5 border border-red-500/15 px-4 py-3.5"
        >
          <div className="flex items-center gap-2 mb-1.5">
            <AlertTriangle size={12} className="text-red-400 shrink-0" />
            <span className="text-[10px] font-semibold text-red-400/70 uppercase tracking-wider">Biggest blocker</span>
          </div>
          <p className="text-sm text-[--roast-text-2] leading-relaxed">{review.tldr_biggest_blocker}</p>
        </motion.div>

        {/* Fix first */}
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.14 }}
          className="rounded-xl bg-orange-500/5 border border-orange-500/15 px-4 py-3.5"
        >
          <div className="flex items-center gap-2 mb-1.5">
            <Wrench size={12} className="text-orange-400 shrink-0" />
            <span className="text-[10px] font-semibold text-orange-400/70 uppercase tracking-wider">Fix first</span>
          </div>
          <p className="text-sm text-orange-200/80 leading-relaxed">{review.tldr_fix_first}</p>
        </motion.div>
      </div>
    </div>
  )
}
