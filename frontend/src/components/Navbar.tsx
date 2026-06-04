import { Link, useNavigate } from 'react-router-dom'
import { Sparkles, LayoutDashboard, LogOut, LogIn, UserPlus, Zap } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-lg border-b border-gray-100/80 shadow-sm shadow-gray-100/50">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-7 h-7 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-sm shadow-violet-200 transition-shadow group-hover:shadow-md group-hover:shadow-violet-200">
            <Sparkles className="w-3.5 h-3.5 text-white transition-transform duration-300 group-hover:rotate-12" />
          </div>
          <span className="text-gray-900 font-semibold text-sm tracking-tight">ResumeAI</span>
        </Link>

        {/* Right side */}
        <div className="flex items-center gap-1">
          {user ? (
            <>
              <Link
                to="/dashboard"
                className="flex items-center gap-1.5 text-gray-500 hover:text-gray-900 text-sm px-3 py-1.5 rounded-lg hover:bg-gray-100 transition"
              >
                <LayoutDashboard className="w-4 h-4" />
                <span className="hidden sm:inline">Dashboard</span>
              </Link>
              <Link
                to="/agent"
                className="flex items-center gap-1.5 text-gray-500 hover:text-gray-900 text-sm px-3 py-1.5 rounded-lg hover:bg-gray-100 transition"
              >
                <Sparkles className="w-4 h-4 text-violet-500 animate-pulse" />
                <span className="hidden sm:inline">Agent Mode</span>
              </Link>
              <div className="flex items-center gap-2 pl-2 border-l border-gray-200">
                {/* Usage pill */}
                {!user.is_premium && (
                  <Link
                    to="/"
                    className="hidden sm:flex items-center gap-1 text-xs px-2 py-1 rounded-full border border-gray-300 text-gray-500 hover:border-violet-500 hover:text-violet-600 transition"
                    title="Free tailorings remaining"
                  >
                    <Zap className="w-3 h-3" />
                    {Math.max(0, (user.analyses_limit ?? 3) - (user.analyses_used ?? 0))}/{user.analyses_limit ?? 3} free
                  </Link>
                )}
                <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center text-white text-xs font-bold">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <span className="text-gray-700 text-sm hidden sm:inline max-w-[120px] truncate">
                  {user.name}
                </span>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1 text-gray-400 hover:text-red-500 text-sm px-2 py-1.5 rounded-lg hover:bg-gray-100 transition"
                  title="Sign out"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="flex items-center gap-1.5 text-gray-500 hover:text-gray-900 text-sm px-3 py-1.5 rounded-lg hover:bg-gray-100 transition"
              >
                <LogIn className="w-4 h-4" />
                Sign in
              </Link>
              <Link
                to="/signup"
                className="flex items-center gap-1.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-sm px-3 py-1.5 rounded-lg transition-all shadow-sm shadow-violet-200 hover:shadow-md hover:shadow-violet-200 hover:-translate-y-0.5"
              >
                <UserPlus className="w-4 h-4" />
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
