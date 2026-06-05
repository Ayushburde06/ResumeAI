import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Zap, Upload, FileText, AlertCircle, Loader2 } from 'lucide-react'
import { agentAnalyze } from '../lib/api'
import type { AgentStep, AgentAnalyzeResult } from '../types'
import AgentProgressPanel from '../components/AgentProgressPanel'
import { useAuth } from '../context/AuthContext'

export default function AgentAnalyze() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [jobDesc, setJobDesc] = useState('')
  const [dragging, setDragging] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([])
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<(() => void) | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => { abortRef.current?.() }
  }, [])

  const handleFile = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!ext || !['pdf', 'docx'].includes(ext)) {
      setError('Please upload a PDF or DOCX file.')
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
    if (!resumeFile || jobDesc.trim().length < 50) {
      setError('Please upload a resume and enter a job description (min 50 characters).')
      return
    }
    if (!user) {
      navigate('/login')
      return
    }

    setIsRunning(true)
    setAgentSteps([])
    setError(null)

    const cleanup = agentAnalyze(
      resumeFile,
      jobDesc,
      undefined, // use default model (GLM/Qwen)
      (step) => {
        setAgentSteps((prev) => [...prev, step])
      },
      (result: AgentAnalyzeResult) => {
        setIsRunning(false)
        abortRef.current = null
        // Navigate to results page with full agent result
        navigate('/results', {
          state: {
            result,
            job_description: jobDesc,
            model_id: '',
          },
        })
      },
      (errMsg) => {
        setIsRunning(false)
        abortRef.current = null
        setError(errMsg)
      },
    )
    abortRef.current = cleanup
  }

  const handleCancel = () => {
    abortRef.current?.()
    abortRef.current = null
    setIsRunning(false)
    setAgentSteps([])
  }

  const canStart = !!resumeFile && jobDesc.trim().length >= 50 && !isRunning

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 pt-14">
      {/* Header */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm sticky top-14 z-40">
        <div className="max-w-5xl mx-auto px-6 h-12 flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-2 text-sm">
            <Zap className="w-4 h-4 text-indigo-400" />
            <span className="text-white font-medium">Agent Mode</span>
            <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-300 rounded-full text-xs border border-indigo-500/30">
              RAG + Self-Improving Loop
            </span>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-10">
        {/* Hero */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500/10 border border-indigo-500/30 rounded-full text-indigo-300 text-sm mb-5">
            <span className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
            Powered by GLM/Qwen · Up to 3 self-improvement iterations
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">
            Agentic Resume Optimizer
          </h1>
          <p className="text-slate-400 max-w-xl mx-auto text-lg">
            The AI reads your resume, plans a strategy, retrieves industry knowledge,
            rewrites — then critiques and improves itself until ATS&nbsp;≥&nbsp;90%.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left — Inputs */}
          <div className="space-y-6">
            {/* File drop zone */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Resume (PDF or DOCX)
              </label>
              <div
                className={`agent-dropzone ${dragging ? 'dragging' : ''} ${resumeFile ? 'has-file' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
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
                    <div className="w-10 h-10 bg-indigo-500/20 rounded-xl flex items-center justify-center">
                      <FileText className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div className="text-left">
                      <p className="text-white font-medium text-sm">{resumeFile.name}</p>
                      <p className="text-slate-400 text-xs">
                        {(resumeFile.size / 1024).toFixed(0)} KB · Click to replace
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 bg-slate-700 rounded-xl flex items-center justify-center">
                      <Upload className="w-6 h-6 text-slate-400" />
                    </div>
                    <p className="text-slate-300 text-sm">Drop resume here or click to upload</p>
                    <p className="text-slate-500 text-xs">PDF or DOCX · max 10 MB</p>
                  </div>
                )}
              </div>
            </div>

            {/* Job description */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Job Description
              </label>
              <textarea
                className="agent-textarea"
                placeholder="Paste the full job description here…"
                value={jobDesc}
                onChange={(e) => setJobDesc(e.target.value)}
                disabled={isRunning}
                rows={10}
              />
              <p className="text-slate-500 text-xs mt-1">{jobDesc.length} chars · min 50</p>
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 bg-red-900/30 border border-red-700/40 rounded-xl text-sm text-red-300">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-3">
              {!isRunning ? (
                <button
                  id="agent-start-btn"
                  onClick={handleStart}
                  disabled={!canStart}
                  className="agent-start-btn"
                >
                  <Zap className="w-4 h-4" />
                  Run Agent
                </button>
              ) : (
                <button onClick={handleCancel} className="agent-cancel-btn">
                  Cancel
                </button>
              )}
            </div>

            {/* How it works */}
            {!isRunning && agentSteps.length === 0 && (
              <div className="agent-how-it-works">
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-3">
                  How it works
                </p>
                {[
                  ['🧠', 'Plans strategy based on your resume + JD'],
                  ['📚', 'Retrieves industry resume templates + ATS rules'],
                  ['✍️', 'Rewrites resume (up to 3 iterations)'],
                  ['🔄', 'Self-critiques output after each pass'],
                  ['🎤', 'Generates interview prep Q&A for you'],
                ].map(([icon, text], i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-slate-400">
                    <span className="mt-0.5">{icon}</span>
                    <span>{text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right — Agent progress */}
          <div>
            {(isRunning || agentSteps.length > 0) && (
              <AgentProgressPanel steps={agentSteps} isRunning={isRunning} />
            )}

            {!isRunning && agentSteps.length === 0 && (
              <div className="agent-empty-panel">
                <div className="agent-empty-icon">
                  <Loader2 className="w-8 h-8 text-slate-600" />
                </div>
                <p className="text-slate-500 text-sm text-center">
                  Agent progress will appear here in real-time once you start.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
