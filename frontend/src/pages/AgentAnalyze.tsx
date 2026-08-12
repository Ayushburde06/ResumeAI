import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { ArrowLeft, Sparkles, Upload, FileText, AlertCircle, Loader2, RefreshCw, CheckCircle2, Zap, UserCircle, Search, Settings, Flag } from 'lucide-react'
import { agentAnalyze, agentAnalyzeFromProfile, fetchProfile } from '../lib/api'
import type { AgentStep, AgentAnalyzeResult } from '../types'
import AgentProgressPanel from '../components/AgentProgressPanel'
import { useAuth } from '../context/AuthContext'

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

export default function AgentAnalyze() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, refreshUser } = useAuth()
  const navState = location.state as { fromProfile?: boolean; job_description?: string } | null

  const [inputMode, setInputMode] = useState<'upload' | 'profile'>(navState?.fromProfile ? 'profile' : 'upload')
  const [profileReady, setProfileReady] = useState<boolean | null>(null)
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [jobDesc, setJobDesc] = useState(navState?.job_description ?? '')
  const [dragging, setDragging] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([])
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<(() => void) | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const historyIdRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      abortRef.current?.()
    }
  }, [])

  useEffect(() => {
    fetchProfile()
      .then((p) => setProfileReady(p.is_complete))
      .catch(() => setProfileReady(false))
  }, [])

  const handleFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!ext || !['pdf', 'docx'].includes(ext)) {
      setError('Unsupported file type. Please upload a PDF or DOCX file.')
      return
    }
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setError('File is too large. Maximum size is 10 MB.')
      return
    }
    setResumeFile(file)
    setError(null)
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [])

  const handleStart = () => {
    if (jobDesc.trim().length < 50) {
      setError('Please enter a job description with at least 50 characters.')
      return
    }
    if (inputMode === 'upload' && !resumeFile) {
      setError('Please upload a resume or switch to My Profile mode.')
      return
    }
    if (inputMode === 'profile' && !profileReady) {
      setError('Complete your profile first.')
      return
    }
    if (!user) {
      navigate('/login')
      return
    }

    setIsRunning(true)
    setAgentSteps([])
    setError(null)

    historyIdRef.current = null

    const onStep = (step: AgentStep) => {
      if (step.step === 'history_saved' && step.history_id) {
        historyIdRef.current = step.history_id
      } else {
        setAgentSteps((prev) => [...prev, step])
      }
    }

    const onComplete = (result: AgentAnalyzeResult) => {
      setIsRunning(false)
      abortRef.current = null
      refreshUser().catch(() => {})
      navigate('/', {
        state: {
          result: { ...result, history_id: historyIdRef.current ?? undefined },
          job_description: jobDesc,
          model_id: '',
        },
      })
    }

    const onError = (errMsg: string) => {
      setIsRunning(false)
      abortRef.current = null
      setError(errMsg)
    }

    const cleanup = inputMode === 'profile'
      ? agentAnalyzeFromProfile(jobDesc, undefined, onStep, onComplete, onError)
      : agentAnalyze(resumeFile!, jobDesc, undefined, onStep, onComplete, onError)

    abortRef.current = cleanup
  }

  const handleCancel = () => {
    abortRef.current?.()
    abortRef.current = null
    setIsRunning(false)
    setAgentSteps([])
  }

  const canStart = jobDesc.trim().length >= 50 && !isRunning && (
    inputMode === 'profile' ? profileReady === true : !!resumeFile
  )

  return (
    <div className="min-h-screen pt-14 text-slate-ink">
      <div className="border-b border-white/70 bg-white/80 backdrop-blur-xl sticky top-14 z-40">
        <div className="page-shell h-14 flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-950 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <span className="text-zinc-300">|</span>
          <div className="flex items-center gap-2 text-sm">
            <Zap className="w-4 h-4 text-zinc-700" />
            <span className="text-zinc-900 font-semibold">Agent Mode</span>
            <span className="px-2 py-0.5 bg-brand-50 text-brand-700 rounded-full text-xs border border-brand-100">
              RAG + self-improving loop
            </span>
          </div>
        </div>
      </div>

      <div className="page-shell py-8 lg:py-10">
        <div className="text-center mb-10">
          <div className="hero-kicker mb-5">
            Multi-agent optimization with up to 3 refinement passes
          </div>
          <h1 className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight text-slate-ink mb-4">
            Optimize with AI Agent
          </h1>
          <p className="hero-copy max-w-3xl mx-auto">
            The agent parses the resume, reads the job description, retrieves relevant knowledge, rewrites only what evidence supports, validates ATS compatibility, and reflects before the final export.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div className="panel p-6">
              <div className="flex items-center justify-between mb-3">
                <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">
                  Resume source
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setInputMode('upload')}
                    className={`text-xs px-3 py-1 rounded-full ${inputMode === 'upload' ? 'bg-zinc-100 font-semibold' : 'text-zinc-500'}`}
                  >
                    Upload PDF
                  </button>
                  <button
                    type="button"
                    onClick={() => setInputMode('profile')}
                    className={`text-xs px-3 py-1 rounded-full ${inputMode === 'profile' ? 'bg-zinc-100 font-semibold' : 'text-zinc-500'}`}
                  >
                    My Profile
                  </button>
                </div>
              </div>

              {inputMode === 'upload' ? (
              <div
                className={`agent-dropzone ${dragging ? 'dragging' : ''} ${resumeFile ? 'has-file' : ''}`}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                />
                {resumeFile ? (
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 bg-zinc-100 rounded-2xl flex items-center justify-center border border-zinc-200/70">
                      <FileText className="w-5 h-5 text-zinc-600" />
                    </div>
                    <div className="text-left">
                      <p className="text-zinc-900 font-semibold text-sm">{resumeFile.name}</p>
                      <p className="text-zinc-500 text-xs">
                        {(resumeFile.size / 1024).toFixed(0)} KB · Click to replace
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-11 h-11 bg-zinc-50 rounded-2xl flex items-center justify-center border border-zinc-100 mb-1">
                      <Upload className="w-5 h-5 text-zinc-400" />
                    </div>
                    <p className="text-zinc-800 font-semibold text-sm">Drop resume here or click to upload</p>
                    <p className="text-zinc-400 text-xs">PDF or DOCX · max 10 MB</p>
                  </div>
                )}
              </div>
              ) : (
                <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-5 space-y-2">
                  <div className="flex items-center gap-3">
                    <UserCircle className="h-8 w-8 text-brand" />
                    <div>
                      <p className="text-sm font-semibold text-zinc-800">Profile + RAG agent</p>
                      <p className="text-xs text-zinc-500">Uses saved projects & experience with profile RAG</p>
                    </div>
                  </div>
                  {profileReady === false && (
                    <p className="text-xs text-amber-700">
                      Profile incomplete. <Link to="/profile" className="underline font-medium">Fill profile</Link>
                    </p>
                  )}
                  {profileReady === true && (
                    <p className="text-xs text-emerald-700">Profile ready — agent will retrieve relevant evidence chunks.</p>
                  )}
                </div>
              )}
            </div>

            <div className="panel p-6">
              <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500 mb-2">
                Job description
              </label>
              <textarea
                className="agent-textarea"
                placeholder="Paste the full job description here..."
                value={jobDesc}
                onChange={(e) => setJobDesc(e.target.value)}
                disabled={isRunning}
                rows={10}
              />
              <div className="flex justify-between items-center text-zinc-400 text-xs mt-1.5">
                <span>{jobDesc.length} chars</span>
                <span>min 50 chars</span>
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2.5 p-3.5 bg-red-50 border border-red-200 rounded-2xl text-sm text-red-700">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            <div className="flex gap-3">
              {!isRunning ? (
                <button
                  id="agent-start-btn"
                  onClick={handleStart}
                  disabled={!canStart}
                  className="agent-start-btn h-12 font-semibold rounded-2xl text-sm transition-transform active:scale-[0.98]"
                >
                  <Sparkles className="w-4 h-4 fill-white" />
                  Optimize with AI Agent
                </button>
              ) : (
                <button
                  onClick={handleCancel}
                  className="agent-cancel-btn h-12 font-semibold rounded-2xl text-sm transition-transform active:scale-[0.98]"
                >
                  Cancel
                </button>
              )}
            </div>

            {!isRunning && agentSteps.length === 0 && (
              <div className="agent-how-it-works">
                <p className="text-zinc-500 text-xs font-bold uppercase tracking-[0.14em] mb-3">
                  How it works
                </p>
                {[
                  { icon: <Search className="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />, text: 'HR recruiter screens the resume like a real shortlist pass' },
                  { icon: <Settings className="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />, text: 'Technical hiring manager judges interview readiness' },
                  { icon: <Flag className="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />, text: 'Founder / JD poster checks role fit and evidence honesty' },
                  { icon: <RefreshCw className="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />, text: 'If anyone gives red, the agent self-fixes and rechecks' },
                  { icon: <CheckCircle2 className="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />, text: 'Final call: Interview, Revise, or Pass with a clear signal' },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-2.5 text-sm text-zinc-600">
                    {item.icon}
                    <span>{item.text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            {(isRunning || agentSteps.length > 0) && (
              <div className="space-y-4">
                {isRunning && (
                  <div className="panel p-4 border-brand-100 bg-brand-50/40">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white border border-brand-100 shadow-sm">
                        <Loader2 className="w-5 h-5 text-brand animate-spin" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-zinc-900">Reviewers evaluating resume</p>
                        <p className="text-xs text-zinc-500">HR, technical HM, and JD poster — then self-fix if needed.</p>
                      </div>
                    </div>
                  </div>
                )}

                <AgentProgressPanel steps={agentSteps} isRunning={isRunning} />
              </div>
            )}

            {!isRunning && agentSteps.length === 0 && (
              <div className="agent-empty-panel">
                <div className="agent-empty-icon">
                  <Loader2 className="w-6 h-6 text-zinc-300" />
                </div>
                <p className="text-zinc-500 text-sm text-center px-4">
                  Agent progress will appear here in real time once you start.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
