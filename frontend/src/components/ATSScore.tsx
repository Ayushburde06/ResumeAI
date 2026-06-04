import { CheckCircle2, Loader2, Sparkles, XCircle, TrendingUp, Zap } from 'lucide-react'
import { useEffect, useState } from 'react'

interface Props {
  score: number
  matchedKeywords: string[]
  missingKeywords: string[]
  totalKeywords: number
  onImproveAts?: () => void
  improving?: boolean
  autoImproved?: boolean
}

function ScoreRing({ score }: { score: number }) {
  const [animated, setAnimated] = useState(false)
  const radius = 40
  const circumference = 2 * Math.PI * radius
  const offset = animated ? circumference - (score / 100) * circumference : circumference

  const isElite = score >= 95
  const color = isElite ? '#6366f1' : score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444'
  const label = isElite ? 'Elite' : score >= 80 ? 'Excellent' : score >= 60 ? 'Good' : score >= 40 ? 'Fair' : 'Needs Work'

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 100)
    return () => clearTimeout(t)
  }, [score])

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="100" height="100" viewBox="0 0 100 100">
        {/* Background ring */}
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="8" />
        {/* Elite glow ring */}
        {isElite && (
          <circle
            cx="50" cy="50" r={radius} fill="none"
            stroke="#a5b4fc" strokeWidth="12"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            transform="rotate(-90 50 50)"
            style={{ transition: 'stroke-dashoffset 1.2s ease', opacity: 0.3 }}
          />
        )}
        {/* Main progress ring */}
        <circle
          cx="50" cy="50" r={radius} fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
          style={{ transition: 'stroke-dashoffset 1.2s ease' }}
        />
        <text x="50" y="46" textAnchor="middle" fontSize="18" fontWeight="700" fill={color}>{score}</text>
        <text x="50" y="60" textAnchor="middle" fontSize="9" fill="#6b7280">/ 100</text>
      </svg>
      <span
        className={`text-sm font-semibold px-2.5 py-0.5 rounded-full ${
          isElite
            ? 'bg-indigo-50 text-indigo-600 border border-indigo-200'
            : ''
        }`}
        style={isElite ? {} : { color }}
      >
        {label}
      </span>
    </div>
  )
}

export default function ATSScore({
  score,
  matchedKeywords,
  missingKeywords,
  totalKeywords,
  onImproveAts,
  improving = false,
  autoImproved = false,
}: Props) {
  // Show improve button whenever there are missing keywords and score < 95
  const showImproveButton = score < 95 && missingKeywords.length > 0 && onImproveAts

  return (
    <div className="card p-5 space-y-5 animate-fade-in">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-brand-600" />
          <h3 className="font-semibold text-gray-900">ATS Compatibility Score</h3>
        </div>
        {autoImproved && (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 bg-indigo-50 text-indigo-600 border border-indigo-100 rounded-full">
            <Zap className="w-2.5 h-2.5" />
            Auto-optimized
          </span>
        )}
      </div>

      <div className="flex items-center gap-6">
        <ScoreRing score={score} />
        <div className="flex-1 space-y-2">
          <div className="text-sm text-gray-600">
            <span className="font-semibold text-green-600">{matchedKeywords.length}</span> of{' '}
            <span className="font-semibold">{totalKeywords}</span> keywords matched
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2">
            <div
              className="h-2 rounded-full transition-all duration-700"
              style={{
                width: `${totalKeywords > 0 ? (matchedKeywords.length / totalKeywords) * 100 : 0}%`,
                background: score >= 95 ? '#6366f1' : score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444',
              }}
            />
          </div>
          <p className="text-xs text-gray-400">
            Score reflects keyword coverage after tailoring
          </p>
        </div>
      </div>

      {showImproveButton && (
        <div className={`p-4 rounded-xl space-y-3 border ${
          score >= 80
            ? 'bg-indigo-50 border-indigo-100'
            : 'bg-amber-50 border-amber-100'
        }`}>
          <p className={`text-sm ${score >= 80 ? 'text-indigo-800' : 'text-amber-800'}`}>
            {score >= 80
              ? `${missingKeywords.length} keyword${missingKeywords.length > 1 ? 's' : ''} still missing — AI can push your score higher.`
              : `Your ATS score is ${score}%. AI can rewrite your resume to weave in missing keywords.`}
          </p>
          <button
            type="button"
            onClick={onImproveAts}
            disabled={improving}
            className="btn-primary w-full justify-center text-sm py-2.5"
          >
            {improving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Improving ATS score...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Boost ATS Score with AI
              </>
            )}
          </button>
        </div>
      )}

      {matchedKeywords.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
            <span className="text-xs font-semibold text-green-700 uppercase tracking-wide">Matched Keywords</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {matchedKeywords.map((kw) => (
              <span key={kw} className="px-2.5 py-0.5 bg-green-50 text-green-700 border border-green-200 rounded-full text-xs font-medium">
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {missingKeywords.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <XCircle className="w-3.5 h-3.5 text-red-400" />
            <span className="text-xs font-semibold text-red-600 uppercase tracking-wide">Missing Keywords</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {missingKeywords.slice(0, 20).map((kw) => (
              <span key={kw} className="px-2.5 py-0.5 bg-red-50 text-red-600 border border-red-100 rounded-full text-xs">
                {kw}
              </span>
            ))}
            {missingKeywords.length > 20 && (
              <span className="px-2.5 py-0.5 text-gray-400 text-xs">+{missingKeywords.length - 20} more</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
