import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  LayoutDashboard, FileText, Trash2, Loader2, Plus, ArrowUpRight, Sparkles,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { listHistory, deleteHistory } from '../lib/api'
import type { HistoryListItem } from '../types'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

function getScoreMeta(n: number) {
  if (n >= 80) return { color: '#166534', label: 'Strong match', bg: '#f0fdf4' }
  if (n >= 60) return { color: '#b45309', label: 'Good match', bg: '#fffbeb' }
  return { color: '#b91c1c', label: 'Needs work', bg: '#fef2f2' }
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
    if (authLoading) return
    if (!user) {
      navigate('/login')
      return
    }

    listHistory()
      .then((data) => setItems(Array.isArray(data) ? data : []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [user, navigate, authLoading])

  const safeItems = Array.isArray(items) ? items : []
  const scoredItems = safeItems.filter((i) => i.ats_score !== null)
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
    } finally {
      setDeletingId(null)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-brand animate-spin" />
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="min-h-screen pt-14">
      <div className="page-shell py-8 lg:py-10">
        <div className="flex flex-col gap-6">
          <div className="panel p-6 lg:p-7 overflow-hidden relative">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(26,31,46,0.08),transparent_34%),radial-gradient(circle_at_bottom_left,rgba(91,114,150,0.10),transparent_28%)]" />
            <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-2xl">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-zinc-500 mb-3">
                  <LayoutDashboard className="w-4 h-4" />
                  Dashboard
                </div>
                <h1 className="hero-title text-4xl md:text-5xl lg:text-[56px] mb-3">
                  Welcome back, {user.name.split(' ')[0]}.
                </h1>
                <p className="hero-copy max-w-2xl">
                  Keep your tailored resumes, ATS scores, and export history in one clean workspace.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Link
                  to="/"
                  className="inline-flex items-center gap-2 rounded-2xl bg-brand px-4 py-2.5 text-sm font-semibold text-white shadow-[0_16px_34px_rgba(26,31,46,0.16)] transition hover:bg-brand-hover hover:-translate-y-0.5"
                >
                  <Plus className="w-4 h-4" />
                  New Resume
                </Link>
                <Link
                  to="/agent"
                  className="inline-flex items-center gap-2 rounded-2xl border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 transition hover:-translate-y-0.5 hover:bg-zinc-50"
                >
                  <Sparkles className="w-4 h-4" />
                  Agent Mode
                </Link>
              </div>
            </div>
          </div>

          {!loading && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="stat-card">
                <p className="text-3xl font-semibold text-slate-ink">{safeItems.length}</p>
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-500 mt-2">Saved resumes</p>
              </div>
              <div className="stat-card">
                <p className="text-3xl font-semibold text-slate-ink">{avgAts !== null ? `${avgAts}%` : '—'}</p>
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-500 mt-2">Average ATS score</p>
              </div>
              <div className="stat-card">
                <p className="text-3xl font-semibold text-slate-ink">{user.is_premium ? '∞' : remaining}</p>
                <p className="text-xs uppercase tracking-[0.18em] text-zinc-500 mt-2">
                  {user.is_premium ? 'Unlimited tailorings' : 'Free tailorings left'}
                </p>
              </div>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-24">
              <Loader2 className="w-6 h-6 text-brand animate-spin" />
            </div>
          ) : safeItems.length === 0 ? (
            <div className="panel p-10 text-center">
              <div className="mx-auto w-14 h-14 rounded-2xl bg-zinc-100 flex items-center justify-center mb-4">
                <FileText className="w-7 h-7 text-zinc-400" />
              </div>
              <p className="text-zinc-900 font-semibold text-lg">No resumes yet</p>
              <p className="text-zinc-500 text-sm mt-2 mb-6 max-w-md mx-auto">
                Upload your resume and a job description to generate your first tailored version.
              </p>
              <Link to="/">
                <Button size="sm" className="bg-brand hover:bg-brand-hover text-white rounded-2xl px-5">
                  <Plus className="w-4 h-4 mr-2" />
                  Analyze my first resume
                </Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {safeItems.map((item) => {
                const score = item.ats_score ?? 0
                const meta = getScoreMeta(score)

                return (
                  <Card
                    key={item.id}
                    className="card-hover cursor-pointer"
                    onClick={() => navigate(`/results/${item.id}`)}
                  >
                    <CardContent className="p-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-2xl bg-zinc-50 border border-zinc-200 flex items-center justify-center shrink-0">
                          <FileText className="h-4.5 w-4.5 text-zinc-500" />
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-semibold text-zinc-900">{item.candidate_name || 'Resume'}</p>
                            {item.ats_score !== null && (
                              <Badge
                                style={{
                                  backgroundColor: meta.bg,
                                  color: meta.color,
                                  border: 'none',
                                }}
                              >
                                {item.ats_score}/100
                              </Badge>
                            )}
                          </div>
                          <p className="text-xs text-zinc-500 mt-1">
                            {item.job_title} · {timeAgo(item.created_at)}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        {confirmDeleteId === item.id ? (
                          <>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDelete(item.id)}
                              disabled={deletingId === item.id}
                            >
                              {deletingId === item.id ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Yes, delete'}
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => setConfirmDeleteId(null)}>
                              Cancel
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => navigate(`/results/${item.id}`)}
                              className="rounded-xl"
                            >
                              Tailor again
                              <ArrowUpRight className="w-3.5 h-3.5 ml-2" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-9 w-9 text-zinc-400 hover:text-red-600"
                              onClick={() => setConfirmDeleteId(item.id)}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
