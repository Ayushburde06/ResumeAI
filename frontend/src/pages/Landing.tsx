import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Sparkles, Zap, Target, FileCheck, ArrowRight,
  Loader2, CheckCircle, Lock,
} from 'lucide-react'
import ResumeUpload from '../components/ResumeUpload'
import JobDescInput from '../components/JobDescInput'
import JobSearch from '../components/JobSearch'
import PremiumModal from '../components/PremiumModal'
import ModelSelector from '../components/ModelSelector'
import { analyzeResume, fetchModels } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import type { AnalyzeResponse, JobListing, ModelInfo } from '../types'

// ── Constants ────────────────────────────────────────────────────────────────

const STEPS = [
  { icon: <FileCheck className="w-5 h-5" />, label: 'Upload Resume', desc: 'PDF or DOCX' },
  { icon: <Target className="w-5 h-5" />, label: 'Add Job Description', desc: 'Paste or search live listings' },
  { icon: <Sparkles className="w-5 h-5" />, label: 'AI Tailors It', desc: 'Rewrites every section' },
  { icon: <Zap className="w-5 h-5" />, label: 'Download PDF', desc: '3 professional templates' },
]

const FEATURES = [
  { icon: '🎯', title: 'ATS Keyword Match', desc: 'AI scans the job description and weaves exact keywords into your resume naturally.' },
  { icon: '✍️', title: 'Human-Sounding Rewrites', desc: 'Every bullet is rewritten to sound professional, specific, and recruiter-friendly.' },
  { icon: '📄', title: 'Instant Cover Letter', desc: 'A tailored cover letter generated alongside your resume — specific to the company and role.' },
  { icon: '📊', title: 'ATS Score', desc: 'See exactly how well your resume matches the job before you apply.' },
  { icon: '💾', title: 'Resume History', desc: 'Every tailored resume is saved. Go back and re-download any version anytime.' },
  { icon: '🎨', title: '3 PDF Templates', desc: 'Modern, Classic, and Minimal layouts — all ATS-safe and beautifully designed.' },
]

const LOADING_MESSAGES = [
  'Parsing your resume...',
  'Analysing the job description...',
  'Identifying key requirements...',
  'Rewriting experience bullets...',
  'Optimising for ATS scanners...',
  'Crafting your cover letter...',
  'Almost done...',
]

// ── Activity Toast (fixed bottom-left, hidden on mobile) ─────────────────────

const TOASTS = [
  'Sneha from Pune just downloaded a resume',
  'Karan from Hyderabad optimized his resume',
  'Divya from Mumbai just signed up',
  'Rahul from Bangalore downloaded a resume',
  'Ananya from Noida just optimized her resume',
]

function ActivityToast() {
  const [idx, setIdx] = useState(0)
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    let tid: ReturnType<typeof setTimeout>
    const interval = setInterval(() => {
      setVisible(false)
      tid = setTimeout(() => {
        setIdx((i) => (i + 1) % TOASTS.length)
        setVisible(true)
      }, 700)
    }, 6000)
    return () => {
      clearInterval(interval)
      clearTimeout(tid)
    }
  }, [])

  return (
    <div
      className={`hidden md:flex fixed bottom-4 left-4 z-50 items-center gap-2 bg-gray-800 text-white text-sm rounded-full px-3 py-2 transition-opacity duration-500 ${
        visible ? 'opacity-100' : 'opacity-0'
      }`}
    >
      <span>👤</span>
      <span>{TOASTS[idx]}</span>
    </div>
  )
}

// ── Guest Hero (shown when NOT logged in) ────────────────────────────────────

function GuestHero() {
  const [count, setCount] = useState(2847)

  useEffect(() => {
    const id = setInterval(() => setCount((c) => c + 1), 12000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="min-h-screen bg-white text-gray-900 overflow-hidden">
      {/* Hero */}
      <div className="relative max-w-5xl mx-auto px-6 pt-32 pb-20 text-center">

        {/* Gradient orbs — decorative background blobs */}
        <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute -top-48 left-1/2 -translate-x-1/2 w-[800px] h-[520px] bg-gradient-to-r from-violet-300/25 to-indigo-300/20 rounded-full blur-3xl animate-pulse-slow" />
          <div className="absolute top-8 right-[-8%] w-[320px] h-[320px] bg-violet-200/20 rounded-full blur-3xl animate-pulse-slow [animation-delay:1400ms]" />
        </div>

        {/* Badge with pulsing live dot */}
        <div className="inline-flex items-center gap-2 bg-violet-50 border border-violet-200 text-violet-700 text-sm font-medium px-4 py-1.5 rounded-full mb-6 animate-fade-in">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-500" />
          </span>
          AI-powered resume tailoring — Free to start
        </div>

        <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight leading-tight mb-5 text-gray-900 animate-fade-up">
          Get hired with a resume
          <br />
          <span className="bg-gradient-to-r from-violet-600 via-indigo-600 to-violet-600 bg-clip-text text-transparent bg-[length:200%_auto] animate-shimmer">
            built for the job
          </span>
        </h1>

        <p className="text-lg text-gray-500 max-w-2xl mx-auto leading-relaxed mb-4 animate-fade-up-d1">
          Upload your resume + paste a job description. Our AI rewrites every section to match
          what the recruiter is looking for, optimises it for ATS scanners, and generates a
          tailored cover letter — in under 30 seconds.
        </p>

        <p className="text-sm text-gray-400 mb-7 animate-fade-up-d1">
          {count.toLocaleString()} resumes optimized this month
        </p>

        {/* Stats row */}
        <div className="flex items-center justify-center gap-6 sm:gap-10 mb-8 animate-fade-up-d2">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900">97%</p>
            <p className="text-xs text-gray-400 mt-0.5">avg ATS match</p>
          </div>
          <div className="w-px h-8 bg-gray-200" />
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900">~30s</p>
            <p className="text-xs text-gray-400 mt-0.5">generation time</p>
          </div>
          <div className="w-px h-8 bg-gray-200" />
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-900">3</p>
            <p className="text-xs text-gray-400 mt-0.5">PDF templates</p>
          </div>
        </div>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-4 animate-fade-up-d2">
          <Link
            to="/signup"
            className="group w-full sm:w-auto flex items-center justify-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold px-8 py-3.5 rounded-xl text-base transition-all shadow-lg shadow-violet-500/25 hover:shadow-xl hover:shadow-violet-500/35 hover:-translate-y-0.5"
          >
            <Sparkles className="w-5 h-5" />
            Get started — it's free
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </Link>
          <Link
            to="/login"
            className="w-full sm:w-auto flex items-center justify-center gap-2 border border-gray-300 hover:border-gray-400 bg-white hover:bg-gray-50 text-gray-600 hover:text-gray-900 font-medium px-8 py-3.5 rounded-xl text-base transition-all hover:-translate-y-0.5"
          >
            Sign in
          </Link>
        </div>

        <p className="text-gray-400 text-sm animate-fade-up-d3">
          3 free resume tailorings · No credit card required
        </p>
      </div>

      {/* How it works */}
      <div className="max-w-5xl mx-auto px-6 pb-20">
        <p className="text-center text-gray-400 text-sm font-medium uppercase tracking-widest mb-8">
          How it works
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {STEPS.map((step, i) => (
            <div
              key={i}
              style={{ animationDelay: `${i * 80}ms` }}
              className="animate-fade-up flex flex-col items-center text-center gap-2 p-5 bg-white border border-gray-200 hover:border-violet-200 hover:bg-violet-50/30 rounded-2xl transition-all duration-200 hover:-translate-y-1 hover:shadow-sm cursor-default"
            >
              <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-indigo-600 rounded-xl flex items-center justify-center text-white mb-1 shadow-md shadow-violet-100">
                {step.icon}
              </div>
              <p className="text-gray-900 text-sm font-semibold">{step.label}</p>
              <p className="text-gray-500 text-xs">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <div className="max-w-5xl mx-auto px-6 pb-20">
        <p className="text-center text-gray-400 text-sm font-medium uppercase tracking-widest mb-8">
          Everything you need
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group p-5 bg-white border border-gray-200 hover:border-violet-200 rounded-2xl transition-all duration-200 hover:-translate-y-1 hover:shadow-md hover:shadow-violet-50/50 cursor-default"
            >
              <div className="text-2xl mb-3 transition-transform duration-200 group-hover:scale-110 origin-left inline-block">{f.icon}</div>
              <p className="text-gray-900 font-semibold text-sm mb-1">{f.title}</p>
              <p className="text-gray-500 text-xs leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="max-w-5xl mx-auto px-6 pb-24 text-center">
        <div className="relative overflow-hidden bg-gradient-to-br from-violet-600 to-indigo-700 rounded-3xl px-8 py-14">
          {/* Subtle orb inside CTA card */}
          <div className="pointer-events-none absolute -top-20 right-[-5%] w-72 h-72 bg-white/10 rounded-full blur-3xl" />
          <h2 className="text-3xl font-bold text-white mb-3 relative">Ready to land more interviews?</h2>
          <p className="text-violet-200 mb-8 relative">
            Create a free account and tailor your first resume in under a minute.
          </p>
          <Link
            to="/signup"
            className="group relative inline-flex items-center gap-2 bg-white hover:bg-violet-50 text-violet-700 font-semibold px-8 py-3.5 rounded-xl text-base transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
          >
            <Sparkles className="w-5 h-5" />
            Create free account
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </Link>
          <div className="flex items-center justify-center gap-6 mt-6 text-xs text-violet-300">
            <span className="flex items-center gap-1.5"><CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> 3 free tailorings</span>
            <span className="flex items-center gap-1.5"><CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> Resume history saved</span>
            <span className="flex items-center gap-1.5"><Lock className="w-3.5 h-3.5 text-violet-400" /> No credit card needed</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── App (shown when logged in) ───────────────────────────────────────────────

function AppForm() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [jd, setJd] = useState('')
  const [jdMode, setJdMode] = useState<'paste' | 'search'>('paste')
  const [selectedJob, setSelectedJob] = useState<JobListing | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState(LOADING_MESSAGES[0])
  const [error, setError] = useState<string | null>(null)
  const [showPremium, setShowPremium] = useState(false)
  const [analysesUsed, setAnalysesUsed] = useState<number | null>(null)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState('')

  useEffect(() => {
    fetchModels()
      .then((m) => {
        setModels(m)
        const def = m.find((x) => x.is_default)
        if (def) setSelectedModel(def.id)
        else if (m.length > 0) setSelectedModel(m[0].id)
      })
      .catch(() => {
        setModels([{ id: 'glm', display_name: 'GLM-5 (Recommended)', is_default: true }])
        setSelectedModel('glm')
      })
  }, [])

  const canSubmit = !!file && jd.trim().length >= 100

  const used = analysesUsed ?? (user as { analyses_used?: number })?.analyses_used ?? 0
  const limit = (user as { analyses_limit?: number })?.analyses_limit ?? 3
  const isPremium = (user as { is_premium?: boolean })?.is_premium
  const remaining = limit - used

  async function handleAnalyze() {
    if (!file || !canSubmit) return
    setLoading(true)
    setError(null)

    let msgIdx = 0
    const msgInterval = setInterval(() => {
      msgIdx = Math.min(msgIdx + 1, LOADING_MESSAGES.length - 1)
      setLoadingMsg(LOADING_MESSAGES[msgIdx])
    }, 2200)

    try {
      const result: AnalyzeResponse = await analyzeResume(file, jd, selectedModel || undefined)
      if (result.analyses_used !== undefined) {
        setAnalysesUsed(result.analyses_used)
      }
      navigate('/results', { state: { result, job_description: jd, model_id: selectedModel } })
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Something went wrong. Please try again.'
      if (status === 402) {
        setShowPremium(true)
      } else {
        setError(msg)
      }
    } finally {
      clearInterval(msgInterval)
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50/80 via-white to-white">
      {showPremium && (
        <PremiumModal onClose={() => setShowPremium(false)} isLoggedIn={true} />
      )}

      <div className="max-w-6xl mx-auto px-6 py-10 pt-24">
        {/* Hero */}
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="inline-flex items-center gap-2 bg-brand-50 border border-brand-100 text-brand-700 text-sm font-medium px-4 py-1.5 rounded-full mb-3">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-brand-500" />
            </span>
            AI-powered resume tailoring
          </div>

          {/* Usage pill */}
          {!isPremium && (
            <div className="flex justify-center mt-2 mb-4">
              <div
                className={`inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border font-medium cursor-pointer transition ${
                  remaining === 0
                    ? 'text-amber-600 bg-amber-50 border-amber-200 hover:bg-amber-100'
                    : remaining === 1
                    ? 'text-amber-600 bg-amber-50 border-amber-200 hover:bg-amber-100'
                    : 'text-emerald-600 bg-emerald-50 border-emerald-200 hover:bg-emerald-100'
                }`}
                onClick={() => remaining === 0 && setShowPremium(true)}
              >
                {remaining === 0 ? (
                  <><span>🔒</span> Upgrade for more</>
                ) : (
                  <><span>✦</span> {remaining} free tailoring{remaining !== 1 ? 's' : ''} remaining</>
                )}
              </div>
            </div>
          )}

          <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight leading-tight mb-3">
            Get hired with a resume
            <span className="text-brand-600"> built for the job</span>
          </h1>
          <p className="text-base text-gray-500 leading-relaxed">
            Upload your resume and paste the job description. Our AI rewrites every section to
            match exactly what the recruiter is looking for.
          </p>
          <div className="mt-4 flex justify-center">
            <Link
              to="/agent"
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-violet-50 to-indigo-50 border border-violet-100 text-violet-700 text-xs font-semibold rounded-2xl hover:from-violet-100 hover:to-indigo-100 transition-all hover:scale-[1.02] shadow-sm cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5 text-violet-600 animate-pulse" />
              Try new Agent Mode (RAG + self-improving loops for &ge; 90% ATS match)
              <ArrowRight className="w-3.5 h-3.5 text-violet-500" />
            </Link>
          </div>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-4 gap-4 mb-10">
          {STEPS.map((step, i) => (
            <div key={i} className="flex flex-col items-center text-center gap-2">
              <div className="w-11 h-11 rounded-2xl bg-brand-600 text-white flex items-center justify-center shadow-md shadow-brand-200">
                {step.icon}
              </div>
              <div className="text-sm font-semibold text-gray-800">{step.label}</div>
              <div className="text-xs text-gray-400">{step.desc}</div>
            </div>
          ))}
        </div>

        {/* Main form */}
        <div className="max-w-3xl mx-auto">
          <div className="card p-8 space-y-6 shadow-xl shadow-gray-100/80 ring-1 ring-gray-100/50">
            <div>
              <p className="section-title mb-2">Step 1 — Your Resume</p>
              <ResumeUpload file={file} onChange={setFile} />
            </div>

            <div className="border-t border-gray-100" />

            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="section-title">Step 2 — Job Description</p>
                <div className="inline-flex rounded-lg border border-gray-200 p-0.5 bg-gray-50">
                  <button
                    type="button"
                    onClick={() => setJdMode('paste')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      jdMode === 'paste'
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Paste
                  </button>
                  <button
                    type="button"
                    onClick={() => setJdMode('search')}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      jdMode === 'search'
                        ? 'bg-white text-gray-900 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Search jobs
                  </button>
                </div>
              </div>

              {jdMode === 'paste' ? (
                <JobDescInput
                  value={jd}
                  onChange={(value) => {
                    setJd(value)
                    setSelectedJob(null)
                  }}
                />
              ) : (
                <JobSearch
                  selectedJobId={selectedJob?.id}
                  onSelect={(description, job) => {
                    setJd(description)
                    setSelectedJob(job)
                  }}
                  resumeFile={file}
                  modelId={selectedModel}
                />
              )}

              {selectedJob && jdMode === 'search' && (
                <div className="mt-3 p-3 rounded-xl bg-brand-50 border border-brand-100 text-xs text-brand-800">
                  Using <strong>{selectedJob.title}</strong>
                  {selectedJob.company ? ` at ${selectedJob.company}` : ''} as your job description.
                </div>
              )}
            </div>

            <div className="border-t border-gray-100" />

            {/* Model selector */}
            {models.length > 0 && (
              <div>
                <p className="section-title mb-2">AI Model</p>
                <ModelSelector
                  models={models}
                  selectedModel={selectedModel}
                  onChange={setSelectedModel}
                />
              </div>
            )}

            {error && (
              <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-700">
                <span className="flex-shrink-0 mt-0.5">⚠</span>
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!canSubmit || loading || remaining === 0}
              className="btn-primary w-full justify-center py-3 text-base disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>{loadingMsg}</span>
                </>
              ) : remaining === 0 && !isPremium ? (
                <>
                  <Lock className="w-4 h-4" />
                  Upgrade to Premium to continue
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Tailor My Resume
                </>
              )}
            </button>

            {jdMode === 'paste' && (
              <div className="flex justify-between items-center mt-1.5">
                <span className={`text-xs ${
                  jd.trim().length === 0 ? 'text-gray-300' :
                  jd.trim().length < 100 ? 'text-amber-500' : 'text-green-500'
                }`}>
                  {jd.trim().length} / 100 min chars
                </span>
                {jd.trim().length >= 100 && (
                  <span className="text-xs text-green-500 font-medium">✓ Ready</span>
                )}
              </div>
            )}
          </div>

          {loading && (
            <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden mt-4">
              <div
                className="h-1.5 bg-brand-500 rounded-full transition-all duration-[2000ms] ease-in-out"
                style={{ width: `${((LOADING_MESSAGES.indexOf(loadingMsg) + 1) / LOADING_MESSAGES.length) * 100}%` }}
              />
            </div>
          )}

          {!canSubmit && !loading && (
            <p className="text-center text-xs text-gray-400 mt-3">
              {!file ? 'Upload your resume to get started' : 'Add a job description (min 100 characters)'}
            </p>
          )}

          <div className="flex items-center justify-center gap-8 mt-6 text-xs text-gray-400">
            <span className="flex items-center gap-1.5"><FileCheck className="w-3.5 h-3.5 text-green-500" /> ATS Optimised</span>
            <span className="flex items-center gap-1.5"><Target className="w-3.5 h-3.5 text-brand-400" /> Keyword Matched</span>
            <span className="flex items-center gap-1.5"><Zap className="w-3.5 h-3.5 text-amber-400" /> Results in ~30s</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function Landing() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-violet-500 animate-spin" />
      </div>
    )
  }

  return (
    <>
      {user ? <AppForm /> : <GuestHero />}
      <ActivityToast />
    </>
  )
}
