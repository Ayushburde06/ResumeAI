import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Loader2, ArrowLeft } from 'lucide-react'
import { getHistoryEntry } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import type { HistoryEntry, ResultsState } from '../types'
import Results from './Results'

export default function HistoryResults() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [entry, setEntry] = useState<HistoryEntry | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) { navigate('/login'); return }
    if (!id) return
    getHistoryEntry(Number(id))
      .then(setEntry)
      .catch(() => setError('Could not load this resume. It may have been deleted.'))
      .finally(() => setLoading(false))
  }, [id, user, navigate])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center pt-14">
        <Loader2 className="w-6 h-6 text-violet-500 animate-spin" />
      </div>
    )
  }

  if (error || !entry) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center pt-14 gap-4">
        <p className="text-gray-500">{error ?? 'Resume not found.'}</p>
        <Link to="/dashboard" className="flex items-center gap-2 text-violet-600 hover:text-violet-500 text-sm transition">
          <ArrowLeft className="w-4 h-4" />
          Back to dashboard
        </Link>
      </div>
    )
  }

  const injectedState: ResultsState = {
    result: {
      tailored_resume: entry.tailored_resume,
      ats_score: entry.ats_score ?? 0,
      matched_keywords: [],
      missing_keywords: [],
      total_keywords: 0,
      cover_letter: entry.cover_letter ?? { subject_line: '', body: '' },
      application_email: entry.application_email ?? { subject_line: '', body: '' },
      job_analysis: entry.job_analysis ?? {
        job_title: entry.job_title,
        company_type: '',
        seniority: '',
        required_skills: [],
        preferred_skills: [],
        key_responsibilities: [],
        industry_keywords: [],
        tone: '',
        must_have: [],
      },
    },
    job_description: entry.job_description ?? '',
  }

  return (
    <div>
      {/* Breadcrumb banner */}
      <div className="fixed top-14 left-0 right-0 z-40 bg-white/90 backdrop-blur border-b border-gray-200 px-4 py-2 flex items-center gap-3">
        <Link to="/dashboard" className="flex items-center gap-1.5 text-gray-500 hover:text-gray-900 text-sm transition shrink-0">
          <ArrowLeft className="w-4 h-4" />
          Dashboard
        </Link>
        <span className="text-gray-300 shrink-0">›</span>
        <span className="text-gray-700 text-sm truncate min-w-0 flex-1">{entry.job_title || 'Saved Resume'}</span>
        {entry.ats_score !== null && (
          <span className="ml-auto text-xs text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full shrink-0">
            {entry.ats_score}% ATS
          </span>
        )}
      </div>

      <div className="pt-10">
        <Results injectedState={injectedState} />
      </div>
    </div>
  )
}
