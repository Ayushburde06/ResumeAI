import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { Loader2, ArrowLeft } from 'lucide-react'
import { getHistoryEntry, analyzeResume } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import type { HistoryEntry, AnalyzeResponse } from '../types'
import UnifiedWorkspace from '../components/UnifiedWorkspace'

export default function HistoryResults() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [entry, setEntry] = useState<HistoryEntry | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      navigate('/login')
      return
    }
    if (!id) return

    getHistoryEntry(Number(id))
      .then(setEntry)
      .catch(() => setError('Could not load this resume. It may have been deleted.'))
      .finally(() => setLoading(false))
  }, [id, user, navigate])

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex items-center justify-center pt-14">
        <Loader2 className="w-6 h-6 text-[#1a1f2e] animate-spin" />
      </div>
    )
  }

  if (error || !entry) {
    return (
      <div className="min-h-screen bg-[#F8F9FA] flex flex-col items-center justify-center pt-14 gap-4">
        <p className="text-zinc-500">{error ?? 'Resume not found.'}</p>
        <Link to="/dashboard" className="flex items-center gap-2 text-zinc-600 hover:text-zinc-950 text-sm font-medium transition">
          <ArrowLeft className="w-4 h-4" />
          Back to dashboard
        </Link>
      </div>
    )
  }

  const initialResult: AnalyzeResponse = {
    tailored_resume: entry.tailored_resume,
    ats_score: entry.ats_score ?? 0,
    matched_keywords: entry.matched_keywords ?? [],
    missing_keywords: entry.missing_keywords ?? [],
    total_keywords: entry.total_keywords ?? 0,
    ats_validation: entry.quality_report
      ? {
          formatting_report: entry.quality_report.formatting_report ?? '',
          validation_status: 'pass',
          validation_summary: entry.quality_report.ats_compatibility_report ?? '',
        }
      : undefined,
    quality_report: entry.quality_report ?? undefined,
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
  }

  const handleAnalyze = async (file: File, jd: string) => {
    return analyzeResume(file, jd)
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] overflow-hidden flex flex-col bg-[#F8F9FA]">
      <div className="bg-white/85 backdrop-blur-xl border-b border-white/70 px-6 py-2.5 flex items-center gap-3 shrink-0">
        <Link to="/dashboard" className="flex items-center gap-1.5 text-zinc-500 hover:text-zinc-900 text-sm transition shrink-0">
          <ArrowLeft className="w-4 h-4" />
          Dashboard
        </Link>
        <span className="text-zinc-300 shrink-0">›</span>
        <span className="text-zinc-900 text-sm font-medium truncate min-w-0 flex-1">{entry.job_title || 'Saved Resume'}</span>
      </div>

      <UnifiedWorkspace
        initialResult={initialResult}
        initialJd={entry.job_description ?? ''}
        onAnalyze={handleAnalyze}
      />
    </div>
  )
}
