import { useState, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Sparkles, Loader2, Eye, EyeOff, ShieldCheck, Zap } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { loginUser } from '../lib/api'
import { Button } from '@/components/ui/button'

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await loginUser(email, password)
      login(res.token, res.user)
      navigate('/dashboard')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen px-4 py-6 flex items-center justify-center">
      <div className="w-full max-w-6xl grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="hidden lg:flex flex-col justify-between rounded-[32px] border border-white/70 bg-brand text-white p-10 shadow-[0_24px_80px_rgba(26,31,46,0.18)] relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.16),transparent_32%),radial-gradient(circle_at_bottom_left,rgba(91,114,150,0.26),transparent_28%)]" />
          <div className="relative z-10 flex items-center gap-2 text-sm font-semibold tracking-[0.2em] uppercase text-white/75">
            <Sparkles className="w-4 h-4" />
            ResumeAI
          </div>
          <div className="relative z-10 max-w-xl">
            <p className="hero-kicker border-white/15 bg-white/10 text-white/85 mb-6">Secure workspace</p>
            <h1 className="text-5xl font-semibold tracking-tight leading-[0.95] mb-5">
              Sign in to a cleaner resume workflow.
            </h1>
            <p className="text-white/72 text-lg leading-8 max-w-lg">
              Tailor resumes, compare ATS scores, and keep every version organized in one focused workspace.
            </p>
          </div>
          <div className="relative z-10 grid grid-cols-2 gap-4 max-w-lg">
            <div className="rounded-3xl border border-white/10 bg-white/10 p-4">
              <ShieldCheck className="w-5 h-5 text-white/85 mb-3" />
              <p className="text-sm font-semibold mb-1">Protected sessions</p>
              <p className="text-sm text-white/65 leading-6">Token-based auth keeps your resume data private.</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/10 p-4">
              <Zap className="w-5 h-5 text-white/85 mb-3" />
              <p className="text-sm font-semibold mb-1">Fast tailoring</p>
              <p className="text-sm text-white/65 leading-6">Move from upload to export in a single flow.</p>
            </div>
          </div>
        </div>

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
              <p className="section-title mb-2">Welcome back</p>
              <h2 className="text-3xl font-semibold tracking-tight text-slate-ink">Sign in</h2>
              <p className="hero-copy text-sm leading-6 mt-2">Pick up where you left off and keep your tailored resumes in sync.</p>
            </div>

            {error && (
              <div className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500 mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full rounded-2xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-900 outline-none transition focus:border-brand-700 focus:ring-1 focus:ring-brand-700"
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500 mb-2">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full rounded-2xl border border-zinc-200 bg-white px-4 py-3 pr-12 text-sm text-zinc-900 outline-none transition focus:border-brand-700 focus:ring-1 focus:ring-brand-700"
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg p-2 text-zinc-400 transition hover:bg-zinc-50 hover:text-zinc-700"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-brand hover:bg-brand-hover text-white h-12 rounded-2xl shadow-[0_18px_40px_rgba(26,31,46,0.18)]"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                {loading ? 'Signing in...' : 'Sign in'}
              </Button>
            </form>

            <p className="text-center text-zinc-500 text-sm mt-6">
              Don't have an account?{' '}
              <Link to="/signup" className="text-brand-700 hover:text-brand-900 font-medium">
                Create one free
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
