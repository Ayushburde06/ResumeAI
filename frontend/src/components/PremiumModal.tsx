import { X, Sparkles, Zap, Lock, CheckCircle } from 'lucide-react'
import { Link } from 'react-router-dom'

interface Props {
  onClose: () => void
  isLoggedIn: boolean
}

const PERKS = [
  'Unlimited resume tailorings',
  'Priority AI processing',
  'Advanced ATS keyword analysis',
  'LinkedIn profile optimizer',
  'Unlimited cover letters',
  'Resume version history (unlimited)',
]

export default function PremiumModal({ onClose, isLoggedIn }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Card */}
      <div className="relative w-full max-w-md bg-neutral-900 border border-neutral-700 rounded-2xl shadow-2xl overflow-hidden">
        {/* Gradient header */}
        <div className="bg-gradient-to-br from-violet-600 to-indigo-600 px-6 pt-8 pb-6 text-center">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-white/60 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mx-auto mb-3">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-white">Upgrade to Premium</h2>
          <p className="text-white/70 text-sm mt-1">
            You've used all 3 free resume tailorings.
          </p>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          <div className="flex items-center gap-2 text-amber-400 bg-amber-400/10 border border-amber-400/20 rounded-lg px-3 py-2 text-sm mb-5">
            <Lock className="w-4 h-4 shrink-0" />
            This feature requires a Premium subscription to continue.
          </div>

          <p className="text-neutral-300 text-sm font-medium mb-3">Everything in Premium:</p>
          <ul className="space-y-2 mb-6">
            {PERKS.map((perk) => (
              <li key={perk} className="flex items-center gap-2 text-sm text-neutral-300">
                <CheckCircle className="w-4 h-4 text-violet-400 shrink-0" />
                {perk}
              </li>
            ))}
          </ul>

          {/* CTA */}
          <button
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold py-3 rounded-xl transition text-sm shadow-lg shadow-violet-500/25"
            onClick={() => alert('Premium coming soon! We\'ll notify you when it launches.')}
          >
            <Zap className="w-4 h-4" />
            Get Premium — Coming Soon
          </button>

          {!isLoggedIn && (
            <p className="text-center text-neutral-500 text-xs mt-3">
              Already have an account?{' '}
              <Link to="/login" className="text-violet-400 hover:text-violet-300" onClick={onClose}>
                Sign in
              </Link>
            </p>
          )}

          <button
            onClick={onClose}
            className="w-full text-neutral-500 hover:text-neutral-400 text-xs mt-3 transition"
          >
            Maybe later
          </button>
        </div>
      </div>
    </div>
  )
}
