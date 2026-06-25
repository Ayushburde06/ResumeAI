import { Link } from 'react-router-dom'
import { Sparkles, ArrowLeft, SearchX } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 text-center relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute -top-24 -left-24 h-72 w-72 rounded-full bg-brand/10 blur-3xl" />
        <div className="absolute bottom-[-5rem] right-[-4rem] h-72 w-72 rounded-full bg-zinc-400/10 blur-3xl" />
      </div>

      <Link to="/" className="relative z-10 flex items-center gap-3 mb-12 group">
        <div className="w-9 h-9 bg-brand rounded-2xl flex items-center justify-center shadow-[0_12px_24px_rgba(26,31,46,0.16)]">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div className="text-left">
          <span className="block text-slate-ink font-semibold text-lg tracking-tight">ResumeAI</span>
          <span className="block text-[11px] uppercase tracking-[0.22em] text-zinc-500">Tailoring workspace</span>
        </div>
      </Link>

      <div className="relative z-10 panel p-8 sm:p-10 max-w-xl w-full">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-zinc-50 border border-zinc-200 flex items-center justify-center text-zinc-500 mb-5">
          <SearchX className="w-6 h-6" />
        </div>
        <p className="text-8xl font-black text-zinc-100 select-none mb-3 leading-none">404</p>
        <h1 className="text-2xl font-semibold text-slate-ink mb-2">Page not found</h1>
        <p className="text-zinc-500 text-sm mb-8 max-w-sm mx-auto leading-6">
          The page you’re looking for doesn’t exist or has been moved.
        </p>

        <Link to="/">
          <Button className="bg-brand hover:bg-brand-hover text-white rounded-2xl px-5 h-11 shadow-[0_16px_34px_rgba(26,31,46,0.16)]">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to home
          </Button>
        </Link>
      </div>
    </div>
  )
}
