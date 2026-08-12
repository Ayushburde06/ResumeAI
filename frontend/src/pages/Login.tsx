import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Sparkles, Loader2, ShieldCheck, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/context/AuthContext'

export default function Login() {
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [isRegister, setIsRegister] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form fields
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      if (isRegister) {
        await register(name, email, password)
      } else {
        await login(email, password)
      }
      navigate('/dashboard')
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || 'Something went wrong.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen px-4 py-6 flex items-center justify-center">
      <div className="w-full max-w-6xl grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        {/* Left branding panel */}
        <div className="hidden lg:flex flex-col justify-between rounded-[32px] border border-white/70 bg-brand text-white p-10 shadow-[0_24px_80px_rgba(26,31,46,0.18)] relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.16),transparent_32%),radial-gradient(circle_at_bottom_left,rgba(91,114,150,0.26),transparent_28%)]" />
          <div className="relative z-10 flex items-center gap-2 text-sm font-semibold tracking-[0.14em] uppercase text-white/75">
            <Sparkles className="w-4 h-4" />
            ResumeAI
          </div>
          <div className="relative z-10 max-w-xl">
            <p className="hero-kicker border-white/15 bg-white/10 text-white/85 mb-6">Simple & secure</p>
            <h1 className="text-5xl font-semibold tracking-tight leading-[0.95] mb-5">
              {isRegister ? 'Create your account.' : 'Sign in to your account.'}
            </h1>
            <p className="text-white/72 text-lg leading-8 max-w-lg">
              No Google, no OAuth — just email and password. 3 free resumes, forever.
            </p>
          </div>
          <div className="relative z-10 grid grid-cols-2 gap-4 max-w-lg">
            <div className="rounded-3xl border border-white/10 bg-white/10 p-4">
              <ShieldCheck className="w-5 h-5 text-white/85 mb-3" />
              <p className="text-sm font-semibold mb-1">Bot protection</p>
              <p className="text-sm text-white/65 leading-6">Disposable and suspicious emails are blocked automatically.</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/10 p-4">
              <Zap className="w-5 h-5 text-white/85 mb-3" />
              <p className="text-sm font-semibold mb-1">No spam</p>
              <p className="text-sm text-white/65 leading-6">We never send marketing emails. Your inbox stays clean.</p>
            </div>
          </div>
        </div>

        {/* Right form card */}
        <div className="auth-card mx-auto lg:mx-0">
          <div className="auth-card-accent" />
          <div className="p-6 sm:p-8">
            <Link to="/" className="flex items-center gap-2 mb-8 group w-fit">
              <div className="w-9 h-9 rounded-2xl bg-brand flex items-center justify-center shadow-[0_12px_24px_rgba(26,31,46,0.18)]">
                <Sparkles className="w-4.5 h-4.5 text-white" />
              </div>
              <div>
                <span className="block text-slate-ink font-semibold text-lg tracking-tight">ResumeAI</span>
                <span className="block text-xs text-zinc-500">Professional resume tailoring</span>
              </div>
            </Link>

            <div className="mb-6">
              <p className="section-title mb-2">{isRegister ? 'Get started' : 'Welcome back'}</p>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-ink">
                {isRegister ? 'Create an account' : 'Sign in'}
              </h2>
              <p className="hero-copy text-sm leading-6 mt-2">
                {isRegister
                  ? '3 free resumes. No credit card needed.'
                  : 'Enter your email and password to continue.'}
              </p>
            </div>

            {error && (
              <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {isRegister && (
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-slate-700 mb-1">
                    Full name
                  </label>
                  <input
                    id="name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full rounded-xl border border-zinc-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
                    placeholder="John Doe"
                  />
                </div>
              )}

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-zinc-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-zinc-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
                  placeholder="Min 8 characters"
                />
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-brand hover:bg-brand-hover text-white h-12 rounded-2xl shadow-[0_18px_40px_rgba(26,31,46,0.18)]"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                {loading ? 'Please wait...' : isRegister ? 'Create account' : 'Sign in'}
              </Button>
            </form>

            <p className="text-center text-zinc-500 text-sm mt-5">
              {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
              <button
                type="button"
                onClick={() => { setIsRegister(!isRegister); setError(null) }}
                className="text-brand font-medium hover:underline"
              >
                {isRegister ? 'Sign in' : 'Create one'}
              </button>
            </p>

            <p className="text-center text-zinc-400 text-xs mt-4">
              By continuing, you agree to our <Link to="/terms" className="underline hover:text-zinc-300">Terms of Service</Link>.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}