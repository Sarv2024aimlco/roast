import { Copy, Check } from 'lucide-react'
import { useState } from 'react'

export function TLDRBlock({ review }) {
  const [copied, setCopied] = useState(false)

  const copy = () => {
    const text = `ROAST RESULTS\n\nShortlist chance: ${review.tldr_shortlist_chance}\nBiggest blocker: ${review.tldr_biggest_blocker}\nFix first: ${review.tldr_fix_first}`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="border border-[#333] rounded-lg p-6 space-y-4 font-mono text-sm">
      <div className="flex items-center justify-between">
        <span className="text-orange-500 font-bold text-xs tracking-widest">BOTTOM LINE</span>
        <button onClick={copy} className="text-gray-600 hover:text-gray-300 transition-colors">
          {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
        </button>
      </div>

      <div className="border-t border-[#333]" />

      <div className="space-y-3">
        <div className="grid grid-cols-[140px_1fr] gap-2">
          <span className="text-gray-500">Shortlist chance:</span>
          <span className="text-gray-200">{review.tldr_shortlist_chance}</span>
        </div>
        <div className="grid grid-cols-[140px_1fr] gap-2">
          <span className="text-gray-500">Biggest blocker:</span>
          <span className="text-gray-200">{review.tldr_biggest_blocker}</span>
        </div>
        <div className="grid grid-cols-[140px_1fr] gap-2">
          <span className="text-gray-500">Fix first:</span>
          <span className="text-orange-400">{review.tldr_fix_first}</span>
        </div>
      </div>

      <div className="border-t border-[#333]" />
    </div>
  )
}
