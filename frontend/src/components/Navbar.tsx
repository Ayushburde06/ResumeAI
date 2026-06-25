import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Sparkles, LayoutDashboard, LogOut, Zap, Menu, ArrowRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  if (location.pathname === '/' && !user) {
    return null
  }

  function handleLogout() {
    logout()
    navigate('/')
  }

  const isDashboardActive = location.pathname === '/dashboard'
  const isAgentActive = location.pathname === '/agent'

  return (
    <nav className="sticky top-0 left-0 right-0 z-50 border-b border-white/70 bg-white/85 backdrop-blur-xl">
      <div className="page-shell h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
          <div className="w-9 h-9 rounded-2xl bg-brand flex items-center justify-center shadow-[0_12px_24px_rgba(26,31,46,0.16)]">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div className="leading-tight">
            <span className="block text-slate-ink text-lg tracking-tight font-semibold">ResumeAI</span>
            <span className="block text-[11px] uppercase tracking-[0.22em] text-zinc-500">Tailoring workspace</span>
          </div>
        </Link>

        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <>
              <Link to="/dashboard">
                <Button
                  variant="ghost"
                  size="sm"
                  className={`gap-2 rounded-2xl px-4 ${
                    isDashboardActive ? 'text-zinc-950 bg-zinc-50 font-semibold' : 'text-zinc-600 hover:text-zinc-950'
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4 text-zinc-500" />
                  Dashboard
                </Button>
              </Link>
              <Link to="/agent">
                <Button
                  variant="ghost"
                  size="sm"
                  className={`gap-2 rounded-2xl px-4 ${
                    isAgentActive ? 'text-zinc-950 bg-zinc-50 font-semibold' : 'text-zinc-600 hover:text-zinc-950'
                  }`}
                >
                  <Sparkles className={`w-4 h-4 ${isAgentActive ? 'text-zinc-950' : 'text-zinc-400'}`} />
                  Agent Mode
                </Button>
              </Link>
              <div className="flex items-center gap-3 pl-3 border-l border-zinc-200">
                {!user.is_premium && (
                  <div className="flex items-center gap-1.5 text-xs text-zinc-600 font-medium bg-zinc-50 px-3 py-1.5 rounded-full border border-zinc-200">
                    <Zap className="w-3 h-3 text-brand fill-brand" />
                    {Math.max(0, (user.analyses_limit ?? 3) - (user.analyses_used ?? 0))} left
                  </div>
                )}
                <div className="w-8 h-8 rounded-2xl bg-brand flex items-center justify-center text-white text-xs font-semibold shadow-[0_10px_22px_rgba(26,31,46,0.16)]">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-9 w-9 rounded-2xl text-zinc-400 hover:text-red-600 hover:bg-red-50"
                  onClick={handleLogout}
                >
                  <LogOut className="w-4 h-4" />
                </Button>
              </div>
            </>
          ) : (
            <>
              <Link to="/login">
                <Button variant="ghost" size="sm" className="rounded-2xl px-4 text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50">
                  Sign in
                </Button>
              </Link>
              <Link to="/signup">
                <Button size="sm" className="bg-brand hover:bg-brand-hover text-white rounded-2xl px-4 shadow-[0_14px_28px_rgba(26,31,46,0.14)]">
                  Get started
                  <ArrowRight className="w-4 h-4 ml-1" />
                </Button>
              </Link>
            </>
          )}
        </div>

        <div className="md:hidden flex items-center gap-2">
          {user && (
            <div className="w-8 h-8 rounded-2xl bg-brand flex items-center justify-center text-white text-xs font-semibold shadow-[0_10px_22px_rgba(26,31,46,0.16)]">
              {user.name.charAt(0).toUpperCase()}
            </div>
          )}
          <Sheet>
            <SheetTrigger className="inline-flex items-center justify-center p-2 rounded-xl text-zinc-700 hover:bg-white/80 border border-zinc-200/70 transition-colors">
              <Menu className="w-4.5 h-4.5" />
            </SheetTrigger>
            <SheetContent side="right" className="w-[280px] sm:w-[320px] bg-white p-6">
              <div className="flex flex-col gap-6 mt-6">
                <Link to="/" className="flex items-center gap-2 text-lg tracking-tight font-semibold">
                  <Sparkles className="w-4 h-4 text-brand" />
                  ResumeAI
                </Link>

                {user ? (
                  <>
                    <Link to="/dashboard">
                      <Button variant="ghost" className="w-full justify-start gap-2.5 text-zinc-700 rounded-2xl">
                        <LayoutDashboard className="w-4.5 h-4.5 text-zinc-500" />
                        Dashboard
                      </Button>
                    </Link>
                    <Link to="/agent">
                      <Button variant="ghost" className="w-full justify-start gap-2.5 text-zinc-700 rounded-2xl">
                        <Sparkles className="w-4.5 h-4.5 text-zinc-500" />
                        Agent Mode
                      </Button>
                    </Link>
                    <div className="h-px bg-zinc-100 my-1" />
                    {!user.is_premium && (
                      <div className="flex items-center justify-between text-xs text-zinc-500 bg-zinc-50 px-3 py-2 rounded-2xl border border-zinc-200">
                        <span className="flex items-center gap-1.5">
                          <Zap className="w-3.5 h-3.5 text-brand fill-brand" />
                          Remaining analyses
                        </span>
                        <span className="font-semibold">{Math.max(0, (user.analyses_limit ?? 3) - (user.analyses_used ?? 0))} left</span>
                      </div>
                    )}
                    <Button
                      variant="outline"
                      className="w-full justify-center gap-2 text-red-600 border-red-100 hover:bg-red-50 hover:text-red-700 rounded-2xl"
                      onClick={handleLogout}
                    >
                      <LogOut className="w-4 h-4" />
                      Sign out
                    </Button>
                  </>
                ) : (
                  <>
                    <Link to="/login" className="w-full">
                      <Button variant="outline" className="w-full justify-center rounded-2xl">
                        Sign in
                      </Button>
                    </Link>
                    <Link to="/signup" className="w-full">
                      <Button className="w-full bg-brand hover:bg-brand-hover text-white justify-center rounded-2xl">
                        Get started
                      </Button>
                    </Link>
                  </>
                )}
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </nav>
  )
}
