import { useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, Briefcase, Bot, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import type { AnalyzeResponse, ResultsState } from '../types'
import type { AgentAnalyzeResult, AgentTrace } from '../types'
import ATSScore from '../components/ATSScore'
import ResumePreview from '../components/ResumePreview'
import CoverLetter from '../components/CoverLetter'
import InterviewPrep from '../components/InterviewPrep'
import { improveAtsScore, rescoreAts } from '../lib/api'
import type { TailoredResume } from '../types'

interface Props {
  injectedState?: ResultsState
}

function AgentTraceCard({ trace }: { trace: AgentTrace }) {
  return (
    <div className="card p-4 bg-gradient-to-r from-indigo-50 to-violet-50 border-indigo-100">
      <div className="flex items-center gap-2 mb-3">
        <Bot className="w-4 h-4 text-indigo-600" />
        <span className="text-sm font-semibold text-indigo-900">Agent Trace</span>
        {trace.rag_context_used && (
          <span className="text-xs px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full border border-indigo-200">
            📚 RAG used
          </span>
        )}
      </div>
      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <div className="text-2xl font-bold text-indigo-700">{trace.iterations_run}</div>
          <div className="text-xs text-gray-500">iterations</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-indigo-700">{trace.best_ats_score}%</div>
          <div className="text-xs text-gray-500">best ATS</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-indigo-700">
            {(trace.total_time_ms / 1000).toFixed(0)}s
          </div>
          <div className="text-xs text-gray-500">total time</div>
        </div>
      </div>
      {trace.ats_progression.length > 1 && (
        <div className="mt-3 flex items-center gap-1 text-xs text-gray-500">
          <span>Score progression:</span>
          {trace.ats_progression.map((score, i) => (
            <span key={i} className="flex items-center gap-0.5">
              {i > 0 && <ChevronRight className="w-3 h-3 text-gray-400" />}
              <span
                className="font-semibold"
                style={{ color: score >= 90 ? '#16a34a' : score >= 80 ? '#d97706' : '#dc2626' }}
              >
                {score}%
              </span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Results({ injectedState }: Props = {}) {
  const location = useLocation()
  const navigate = useNavigate()
  const pageState = injectedState ?? (location.state as ResultsState | undefined)

  const [result, setResult] = useState<AnalyzeResponse | undefined>(pageState?.result)
  const agentResult = result as AgentAnalyzeResult | undefined
  const jobDescription = pageState?.job_description ?? ''
  const modelId = pageState?.model_id ?? ''
  const [improving, setImproving] = useState(false)
  const [improveError, setImproveError] = useState<string | null>(null)
  const [rescoring, setRescoring] = useState(false)
  const [manuallyImproved, setManuallyImproved] = useState(false)
  const [leftTab, setLeftTab] = useState<'ats' | 'cover' | 'interview'>('ats')

  if (!result) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-gray-50 pt-14">
        <p className="text-gray-500">No results found. Please analyse a resume first.</p>
        <button onClick={() => navigate('/')} className="btn-primary">Go back</button>
      </div>
    )
  }

  const {
    tailored_resume,
    ats_score,
    matched_keywords,
    missing_keywords,
    total_keywords,
    cover_letter,
    job_analysis,
  } = result

  const hasInterviewPrep = !!agentResult?.interview_prep
  const hasAgentTrace = !!agentResult?.agent_trace

  async function handleImproveAts() {
    if (!jobDescription.trim()) {
      setImproveError('Job description not available. Please run a new analysis from the home page.')
      return
    }
    setImproving(true)
    setImproveError(null)
    try {
      const improved = await improveAtsScore({
        tailoredResume: tailored_resume,
        jobDescription,
        jobAnalysis: job_analysis,
        missingKeywords: missing_keywords,
        modelId: modelId || undefined,
      })
      setManuallyImproved(true)
      setResult((prev) =>
        prev
          ? {
              ...prev,
              tailored_resume: improved.tailored_resume,
              ats_score: improved.ats_score,
              matched_keywords: improved.matched_keywords,
              missing_keywords: improved.missing_keywords,
              total_keywords: improved.total_keywords,
            }
          : prev
      )
    } catch (err: unknown) {
      const msg =
        (err as Error)?.message ??
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to improve ATS score.'
      setImproveError(msg)
    } finally {
      setImproving(false)
    }
  }

  function handleResumeChange(updated: TailoredResume) {
    setResult((prev) => (prev ? { ...prev, tailored_resume: updated } : prev))
  }

  async function handleEditComplete() {
    if (!jobDescription.trim()) return
    setRescoring(true)
    try {
      const scored = await rescoreAts(tailored_resume, jobDescription)
      setResult((prev) =>
        prev
          ? {
              ...prev,
              ats_score: scored.ats_score,
              matched_keywords: scored.matched_keywords,
              missing_keywords: scored.missing_keywords,
              total_keywords: scored.total_keywords,
            }
          : prev
      )
    } catch {
      /* keep edited resume even if rescore fails */
    } finally {
      setRescoring(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-brand-50 pt-14">
      {/* Sub-nav */}
      {!injectedState && (
        <div className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-14 z-40">
          <div className="max-w-7xl mx-auto px-6 h-11 flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              New Resume
            </button>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Job analysis banner */}
        {job_analysis.job_title && (
          <div className="flex items-center gap-3 mb-6 p-4 bg-white border border-gray-100 rounded-2xl shadow-sm animate-fade-in">
            <div className="w-10 h-10 bg-brand-100 rounded-xl flex items-center justify-center flex-shrink-0">
              <Briefcase className="w-5 h-5 text-brand-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-gray-900">{job_analysis.job_title}</div>
              <div className="text-sm text-gray-500 flex items-center gap-3 mt-0.5">
                {job_analysis.seniority && <span className="capitalize">{job_analysis.seniority} level</span>}
                {job_analysis.company_type && <span>· {job_analysis.company_type}</span>}
                {job_analysis.tone && <span>· {job_analysis.tone} tone</span>}
                {hasAgentTrace && (
                  <span className="flex items-center gap-1 text-indigo-600 font-medium">
                    · <Bot className="w-3 h-3" /> Agent ({agentResult!.agent_trace!.iterations_run} iterations)
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5 max-w-sm justify-end">
              {job_analysis.required_skills?.slice(0, 5).map((s) => (
                <span key={s} className="px-2 py-0.5 bg-brand-50 text-brand-700 border border-brand-100 rounded-full text-xs font-medium">{s}</span>
              ))}
            </div>
          </div>
        )}

        {/* Agent trace card */}
        {hasAgentTrace && (
          <div className="mb-6 animate-fade-in">
            <AgentTraceCard trace={agentResult!.agent_trace!} />
          </div>
        )}

        {improveError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
            {improveError}
          </div>
        )}

        {/* Main grid */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Left — tabbed panel */}
          <div className="space-y-4">
            {/* Tab bar */}
            <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
              <button
                onClick={() => setLeftTab('ats')}
                className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all ${
                  leftTab === 'ats'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                ATS Score
              </button>
              <button
                onClick={() => setLeftTab('cover')}
                className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all ${
                  leftTab === 'cover'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                Cover Letter
              </button>
              {hasInterviewPrep && (
                <button
                  onClick={() => setLeftTab('interview')}
                  className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all ${
                    leftTab === 'interview'
                      ? 'bg-white text-indigo-700 shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  🎤 Interview
                </button>
              )}
            </div>

            {leftTab === 'ats' && (
              <ATSScore
                score={ats_score}
                matchedKeywords={matched_keywords}
                missingKeywords={missing_keywords}
                totalKeywords={total_keywords}
                onImproveAts={handleImproveAts}
                improving={improving}
                autoImproved={result.auto_improved || manuallyImproved}
              />
            )}
            {leftTab === 'cover' && <CoverLetter coverLetter={cover_letter} />}
            {leftTab === 'interview' && hasInterviewPrep && (
              <InterviewPrep interviewPrep={agentResult!.interview_prep!} />
            )}
          </div>

          {/* Right — Resume preview */}
          <div className="xl:col-span-2">
            <ResumePreview
              resume={tailored_resume}
              onResumeChange={handleResumeChange}
              onEditComplete={handleEditComplete}
              rescoring={rescoring}
            />
          </div>
        </div>

        {/* Job requirements breakdown */}
        {(job_analysis.must_have?.length > 0 || job_analysis.key_responsibilities?.length > 0) && (
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6 animate-slide-up">
            {job_analysis.must_have?.length > 0 && (
              <div className="card p-5">
                <p className="section-title mb-3">Must-Have Requirements</p>
                <ul className="space-y-1.5">
                  {job_analysis.must_have.map((req, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="flex-shrink-0 w-4 h-4 bg-brand-100 text-brand-600 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5">
                        {i + 1}
                      </span>
                      {req}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {job_analysis.key_responsibilities?.length > 0 && (
              <div className="card p-5">
                <p className="section-title mb-3">Key Responsibilities</p>
                <ul className="space-y-1.5">
                  {job_analysis.key_responsibilities.slice(0, 6).map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="flex-shrink-0 mt-1.5 w-1.5 h-1.5 bg-brand-400 rounded-full" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
