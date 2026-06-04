import { useState } from 'react'
import { Copy, Check, Mail } from 'lucide-react'
import type { CoverLetter as CoverLetterType } from '../types'

interface Props {
  coverLetter: CoverLetterType
}

export default function CoverLetter({ coverLetter }: Props) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    const text = `${coverLetter.subject_line}\n\n${coverLetter.body}`
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  return (
    <div className="card p-5 space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mail className="w-4 h-4 text-brand-600" />
          <h3 className="font-semibold text-gray-900">Cover Letter</h3>
        </div>
        <button
          onClick={handleCopy}
          className={`inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border transition-all duration-150
            ${copied
              ? 'bg-green-50 border-green-200 text-green-700'
              : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`}
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {coverLetter.subject_line && (
        <div className="px-4 py-2.5 bg-brand-50 border border-brand-100 rounded-lg">
          <p className="text-xs font-semibold text-brand-600 uppercase tracking-wide mb-0.5">Subject</p>
          <p className="text-sm font-medium text-gray-800">{coverLetter.subject_line}</p>
        </div>
      )}

      <div className="bg-gray-50/70 rounded-xl p-4 border border-gray-100 max-h-72 overflow-y-auto">
        {coverLetter.body.split('\n\n').map((para, i) => (
          <p key={i} className="text-sm text-gray-700 leading-relaxed mb-3 last:mb-0">
            {para}
          </p>
        ))}
      </div>
    </div>
  )
}
