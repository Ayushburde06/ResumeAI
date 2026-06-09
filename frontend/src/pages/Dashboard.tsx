import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  LayoutDashboard, FileText, Trash2, ArrowRight, Loader2, Plus, Target,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { listHistory, deleteHistory } from '../lib/api'
import type { HistoryListItem } from '../types'

function ATSBadge({ score }: { score: number | null }) {
  if (score === null) return null
  const color =
    score >= 85 ? 'text-emerald-600 bg-emerald-50 border-emerald-200'
    : score >= 70 ? 'text-amber-600 bg-amber-50 border-amber-200'
    : 'text-red-600 bg-red-50 border-red-200'
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full border ${color}`}>
      <Target className="w-3 h-3" />
      {score}% ATS
    </span>
  )
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return new Date(isoDate).toLocaleDateString()
}

export default function Dashboard() {
  const { user, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [items, setItems] = useState<HistoryListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null)

  useEffect(() => {
    if (authLoading) return          // wait for auth to finish loading
    if (!user) { navigate('/login'); return }
    listHistory()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [user, navigate, authLoading])

  const scoredItems = items.filter(i => i.ats_score !== null)
  const avgAts = scoredItems.length > 0
    ? Math.round(scoredItems.reduce((a, i) => a + (i.ats_score ?? 0), 0) / scoredItems.length)
    : null
  const remaining = Math.max(0, (user?.analyses_limit ?? 3) - (user?.analyses_used ?? 0))

  async function handleDelete(id: number) {
    setDeletingId(id)
    setConfirmDeleteId(null)
    try {
      await deleteHistory(id)
      setItems((prev) => prev.filter((item) => item.id !== id))
    } catch {
      // silently re-show the item on failure
    } finally {
      setDeletingId(null)
    }
  }

  // Show spinner while auth is loading (prevents flash/blank page)
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-violet-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50/60 via-white to-white pt-14">
      <div className="max-w-4xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-2 text-violet-600 text-xs font-semibold uppercase tracking-widest mb-1">
              <LayoutDashboard className="w-3.5 h-3.5" />
              Dashboard
            </div>
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome back, {user?.name.split(' ')[0]} 👋
            </h1>
            <p className="text-gray-400 text-sm mt-0.5">
              {items.length === 0
                ? 'Analyze your first resume to get started.'
                : `${items.length} saved resume${items.length !== 1 ? 's' : ''}`}
            </p>
          </div>
          <Link
            to="/"
            className="group flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-xl transition-all shadow-md shadow-violet-200 hover:shadow-lg hover:shadow-violet-200 hover:-translate-y-0.5"
          >
            <Plus className="w-4 h-4" />
            New Resume
          </Link>
        </div>

        {/* Stats strip */}
        {!loading && (
          <div className="grid grid-cols-3 gap-3 mb-8">
            <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm">
              <p className="text-2xl font-bold text-gray-900">{items.length}</p>
              <p className="text-xs text-gray-400 mt-0.5">Saved resumes</p>
            </div>
            <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm">
              <p className="text-2xl font-bold text-gray-900">
                {avgAts !== null ? `${avgAts}%` : '—'}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">Avg ATS score</p>
            </div>
            <div className="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm">
              <p className="text-2xl font-bold text-gray-900">
                {user?.is_premium ? '∞' : remaining}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {user?.is_premium ? 'Unlimited tailorings' : 'Free tailorings left'}
              </p>
            </div>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="w-6 h-6 text-violet-500 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-24 border border-dashed border-gray-200 rounded-2xl bg-white">
            <div className="w-14 h-14 bg-gradient-to-br from-violet-100 to-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <FileText className="w-7 h-7 text-violet-400" />
            </div>
            <p className="text-gray-700 font-semibold">No resumes yet</p>
            <p className="text-gray-400 text-sm mt-1 mb-6">
              Upload your resume and a job description to get started.
            </p>
            <Link
              to="/"
              className="inline-flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-all shadow-md shadow-violet-200 hover:shadow-lg hover:-translate-y-0.5"
            >
              <Plus className="w-4 h-4" />
              Analyze my first resume
            </Link>
          </div>
        ) : (
          <div className="space-y-2.5">
            {items.map((item) => (
              <div
                key={item.id}
                className="group flex items-center gap-4 bg-white border border-gray-100 hover:border-violet-200 rounded-2xl px-5 py-4 transition-all duration-200 cursor-pointer shadow-sm hover:shadow-md hover:-translate-y-0.5"
                onClick={() => navigate(`/results/${item.id}`)}
              >
                <div className="w-10 h-10 bg-gradient-to-br from-violet-50 to-indigo-50 border border-violet-100 rounded-xl flex items-center justify-center shrink-0">
                  <FileText className="w-5 h-5 text-violet-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-gray-900 font-semibold text-sm truncate">
                      {item.job_title || 'Untitled Role'}
                    </p>
                    <ATSBadge score={item.ats_score} />
                  </div>
                  <p className="text-gray-400 text-xs mt-0.5">
                    {item.candidate_name && <span className="mr-2">{item.candidate_name}</span>}
                    {timeAgo(item.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                  {confirmDeleteId === item.id ? (
                    <div className="flex items-center gap-1.5 bg-red-50 border border-red-200 rounded-xl px-2 py-1 animate-scale-in">
                      <span className="text-xs text-red-600 font-medium">Delete?</span>
                      <button
                        onClick={() => handleDelete(item.id)}
                        disabled={deletingId === item.id}
                        className="text-xs font-semibold text-white bg-red-500 hover:bg-red-600 px-2 py-0.5 rounded-lg transition"
                      >
                        {deletingId === item.id ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Yes'}
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(null)}
                        className="text-xs font-medium text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded-lg transition"
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => setConfirmDeleteId(item.id)}
                        disabled={deletingId === item.id}
                        className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition opacity-0 group-hover:opacity-100"
                        aria-label="Delete resume"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <ArrowRight className="w-4 h-4 text-gray-200 group-hover:text-violet-400 transition-colors" />
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
