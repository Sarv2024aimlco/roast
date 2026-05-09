import { Copy, Check, AlertTriangle, Wrench, Zap } from 'lucide-react'
import { useState } from 'react'
import { motion } from 'framer-motion'

function ShortlistBadge({ text }) {
  const lower = text.toLowerCase()
  let color, label
  if (lower.includes('strong') || lower.includes('high') || lower.includes('top')) {
    color = 'bg-green-500/15 text-green-400 border-green-500/25'
    label = 'Strong'
  } else if (lower.includes('low') || lower.includes('weak') || lower.includes('below')) {
    color = 'bg-red-500/15 text-red-400 border-red-500/25'
    label = 'Low'
  } else {
    color = 'bg-yellow-500/15 text-yellow-400 border-yellow-500/25'
    label = 'Medium'
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border font-mono ${color}`}>
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
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-[--roast-muted] uppercase tracking-widest">Bottom Line</span>
        <button onClick={copy} className="text-[--roast-muted] hover:text-[--roast-text] transition-colors p-1">
          {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
        </button>
      </div>

      <div className="space-y-4">
        {/* Shortlist chance */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <Zap size={13} className="text-orange-400 shrink-0" />
            <span className="text-xs text-[--roast-muted]">Shortlist chance</span>
            <ShortlistBadge text={review.tldr_shortlist_chance} />
          </div>
          <p className="text-sm text-[--roast-text] leading-relaxed pl-5">{review.tldr_shortlist_chance}</p>
        </div>

        <div className="h-px bg-[--roast-border]" />

        {/* Biggest blocker */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <AlertTriangle size={13} className="text-red-400 shrink-0" />
            <span className="text-xs text-[--roast-muted]">Biggest blocker</span>
          </div>
          <p className="text-sm text-[--roast-text] leading-relaxed pl-5">{review.tldr_biggest_blocker}</p>
        </div>

        <div className="h-px bg-[--roast-border]" />

        {/* Fix first */}
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <Wrench size={13} className="text-orange-400 shrink-0" />
            <span className="text-xs text-[--roast-muted]">Fix first</span>
          </div>
          <p className="text-sm text-orange-300 leading-relaxed pl-5">{review.tldr_fix_first}</p>
        </div>
      </div>
    </div>
  )
}
