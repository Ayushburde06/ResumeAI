import { X, Sparkles, Zap, Lock, CheckCircle2, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

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
  'Resume version history',
]

export default function PremiumModal({ onClose, isLoggedIn }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div
        className="absolute inset-0 bg-zinc-950/45 backdrop-blur-sm"
        onClick={onClose}
      />

      <div className="relative w-full max-w-lg overflow-hidden rounded-[32px] border border-white/70 bg-white shadow-[0_28px_90px_rgba(15,23,42,0.2)]">
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_top_right,rgba(26,31,46,0.14),transparent_35%),radial-gradient(circle_at_bottom_left,rgba(91,114,150,0.10),transparent_28%)]" />

        <div className="relative bg-brand px-6 pt-8 pb-7 text-center">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 rounded-xl p-2 text-white/70 transition hover:bg-white/10 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="w-12 h-12 bg-white/15 rounded-2xl flex items-center justify-center mx-auto mb-3 border border-white/10">
            <Sparkles className="w-5.5 h-5.5 text-white" />
          </div>
          <h2 className="text-2xl font-semibold tracking-tight text-white">Upgrade to Premium</h2>
          <p className="text-white/78 text-sm mt-2 max-w-md mx-auto">
            You’ve used your free tailored resume runs. Unlock the full workflow and keep iterating without limits.
          </p>
        </div>

        <div className="relative px-6 py-6">
          <div className="flex items-center gap-2 text-amber-700 bg-amber-50 border border-amber-200 rounded-2xl px-3 py-2 text-xs mb-5 font-medium">
            <Lock className="w-4 h-4 shrink-0" />
            Premium is required to continue beyond the free tier.
          </div>

          <p className="text-sm font-semibold text-zinc-900 mb-3">Everything in Premium</p>
          <ul className="space-y-3 mb-7">
            {PERKS.map((perk) => (
              <li key={perk} className="flex items-center gap-2.5 text-sm text-zinc-600">
                <CheckCircle2 className="w-4 h-4 text-brand shrink-0" />
                {perk}
              </li>
            ))}
          </ul>

          <Button
            className="w-full bg-brand hover:bg-brand-hover text-white h-12 rounded-2xl shadow-[0_16px_34px_rgba(26,31,46,0.16)]"
            onClick={() => alert('Premium coming soon! We\'ll notify you when it launches.')}
          >
            <Zap className="w-4 h-4 mr-2" />
            Get Premium
            <ArrowRight className="w-4 h-4 ml-1" />
          </Button>

          {!isLoggedIn && (
            <p className="text-center text-zinc-500 text-xs mt-4">
              Already have an account?{' '}
              <Link to="/login" className="text-brand hover:text-brand-hover font-medium" onClick={onClose}>
                Sign in
              </Link>
            </p>
          )}

          <button
            onClick={onClose}
            className="w-full text-zinc-500 hover:text-zinc-900 text-xs mt-4 transition"
          >
            Maybe later
          </button>
        </div>
      </div>
    </div>
  )
}
