import { Link } from 'react-router-dom'
import { Sparkles, ArrowLeft } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-violet-50/40 flex flex-col items-center justify-center px-4 text-center">
      <Link to="/" className="flex items-center gap-2 mb-12 group">
        <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-lg flex items-center justify-center shadow-md shadow-violet-200 transition-shadow group-hover:shadow-lg group-hover:shadow-violet-200">
          <Sparkles className="w-4 h-4 text-white transition-transform duration-300 group-hover:rotate-12" />
        </div>
        <span className="text-gray-900 font-semibold text-lg tracking-tight">ResumeAI</span>
      </Link>

      <p className="text-8xl font-black text-gray-100 select-none mb-2">404</p>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Page not found</h1>
      <p className="text-gray-400 text-sm mb-8 max-w-xs">
        The page you're looking for doesn't exist or has been moved.
      </p>

      <Link
        to="/"
        className="inline-flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold px-6 py-2.5 rounded-xl transition-all shadow-md shadow-violet-200 hover:shadow-lg hover:-translate-y-0.5"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to home
      </Link>
    </div>
  )
}
