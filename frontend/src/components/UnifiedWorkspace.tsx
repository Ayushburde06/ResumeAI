import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, X, Loader2, Mail, ChevronDown, ChevronUp, Mic, MessageSquare, Link as LinkIcon, Lightbulb, Target, ThumbsUp, ThumbsDown } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { toast } from 'sonner'
import type { AgentAnalyzeResult, ModelInfo, InterviewPrep } from '../types'
import ResumePreview from './ResumePreview'
import ATSScore from './ATSScore'
import ModelSelector from './ModelSelector'
import { fetchModels, improveAtsScore, submitFeedback } from '../lib/api'
import { useAuth } from '../context/AuthContext'

const MAX_FILE_SIZE_MB = 10
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

interface UnifiedWorkspaceProps {
  initialFile?: File | null
  initialJd?: string
  initialResult?: AgentAnalyzeResult | null
  initialInterviewPrep?: InterviewPrep | null
  onAnalyze: (file: File, jd: string, modelId?: string) => Promise<AgentAnalyzeResult>
}

export default function UnifiedWorkspace({
  initialFile = null,
  initialJd = '',
  initialResult = null,
  initialInterviewPrep = null,
  onAnalyze,
}: UnifiedWorkspaceProps) {
  const navigate = useNavigate()
  const { refreshUser } = useAuth()
  const [file, setFile] = useState<File | null>(initialFile)
  const [jd, setJd] = useState(initialJd)
  const [jdMode, setJdMode] = useState<'paste' | 'search'>('paste')
  const [result, setResult] = useState<AgentAnalyzeResult | null>(initialResult)
  const [loading, setLoading] = useState(false)
  const [optimizingAts, setOptimizingAts] = useState(false)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [openPanel, setOpenPanel] = useState<string | null>(null)
  const [feedbackRating, setFeedbackRating] = useState<'up' | 'down' | null>(null)
  const [feedbackSaving, setFeedbackSaving] = useState(false)
  const interviewPrep = initialInterviewPrep
  const qualityReport = result?.quality_report
  const hasQualityScores = !!qualityReport && (
    typeof qualityReport.humanization_score === 'number' ||
    typeof qualityReport.recruiter_readability_score === 'number'
  )
  const hasQualityChanges = !!qualityReport?.changes_made?.length
  const hasQualityComparison = !!qualityReport?.before_after_comparison

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

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles: 1,
    maxSize: MAX_FILE_SIZE_BYTES,
    onDrop: (acceptedFiles, rejectedFiles) => {
      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0]
        const isTooLarge = rejection.errors.some((e) => e.code === 'file-too-large')
        const isWrongType = rejection.errors.some((e) => e.code === 'file-invalid-type')
        if (isTooLarge) {
          toast.error(`File is too large. Maximum size is ${MAX_FILE_SIZE_MB} MB.`)
        } else if (isWrongType) {
          toast.error('Unsupported file type. Please upload a PDF or DOCX file.')
        } else {
          toast.error('File rejected. Please upload a valid PDF or DOCX under 10 MB.')
        }
        return
      }
      if (acceptedFiles.length > 0) {
        const f = acceptedFiles[0]
        if (f.size > MAX_FILE_SIZE_BYTES) {
          toast.error(`File is too large. Maximum size is ${MAX_FILE_SIZE_MB} MB.`)
          return
        }
        setFile(f)
      }
    }
  })

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const handleTailor = async () => {
    if (!file || jd.trim().length < 50) return
    // Client-side file size guard before hitting the server
    if (file.size > MAX_FILE_SIZE_BYTES) {
      toast.error(`File is too large. Maximum size is ${MAX_FILE_SIZE_MB} MB.`)
      return
    }
    setLoading(true)
    try {
      const res = await onAnalyze(file, jd, selectedModel || undefined)
      setResult(res)
      toast.success('Resume tailored successfully!')
      // Refresh quota badge immediately so counter stays accurate
      await refreshUser()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to tailor resume')
    } finally {
      setLoading(false)
    }
  }

  const handleImproveAts = async () => {
    if (!result || !result.missing_keywords.length || !result.job_analysis) return
    setOptimizingAts(true)
    try {
      const boosted = await improveAtsScore({
        tailoredResume: result.tailored_resume,
        jobDescription: jd,
        jobAnalysis: result.job_analysis,
        missingKeywords: result.missing_keywords,
        modelId: selectedModel || undefined,
      })

      setResult((prev) => prev ? ({
        ...prev,
        tailored_resume: boosted.tailored_resume,
        ats_score: boosted.ats_score,
        matched_keywords: boosted.matched_keywords,
        missing_keywords: boosted.missing_keywords,
        total_keywords: boosted.total_keywords,
        auto_improved: true,
      }) : prev)
      toast.success(`ATS optimized to ${boosted.ats_score}%`)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to optimize ATS score')
    } finally {
      setOptimizingAts(false)
    }
  }


  return (
    <div className="flex-1 min-h-0 flex flex-col w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 lg:py-6">
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[0.94fr_1.06fr] gap-6">
        
        {/* LEFT PANEL */}
        <div className="flex flex-col gap-6 lg:overflow-y-auto lg:h-full pr-0 lg:pr-1 pb-4">
          <div className="panel p-6">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <p className="section-title mb-1">Step 1</p>
                <h3 className="text-base font-semibold text-zinc-950">Upload Resume</h3>
              </div>
              <span className="text-xs text-zinc-500">PDF or DOCX, up to 10 MB</span>
            </div>
            
            {!file ? (
              <div {...getRootProps()} className={cn(
                "border-2 border-dashed rounded-3xl p-8 text-center cursor-pointer",
                "transition-all duration-200",
                isDragActive 
                  ? "border-brand-700 bg-brand-50/60" 
                  : "border-zinc-200 hover:border-brand-300 hover:bg-zinc-50"
              )}>
                <input {...getInputProps()} />
                <Upload className="mx-auto h-8 w-8 text-zinc-300 mb-3" />
                <p className="text-sm font-semibold text-zinc-800">
                  Drop your resume here
                </p>
                <p className="text-xs text-zinc-400 mt-1">PDF or DOCX up to 10MB</p>
              </div>
            ) : (
              <div className="flex items-center gap-3 p-4 bg-zinc-50 border border-zinc-200 rounded-2xl">
                <FileText className="h-4 w-4 text-zinc-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-800 truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-zinc-400">{formatBytes(file.size)}</p>
                </div>
                <button onClick={() => setFile(null)}>
                  <X className="h-3.5 w-3.5 text-zinc-400 hover:text-zinc-600" />
                </button>
              </div>
            )}
          </div>

          <div className="panel p-6">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <p className="section-title mb-1">Step 2</p>
                <h3 className="text-base font-semibold text-zinc-950">Job Description</h3>
              </div>
              <div className="flex gap-2">
                <Button 
                  variant={jdMode === 'paste' ? 'secondary' : 'ghost'} 
                  size="sm" 
                  onClick={() => setJdMode('paste')}
                  className={jdMode === 'paste' ? 'bg-zinc-100' : ''}
                >
                  Paste
                </Button>
                <Button 
                  variant={jdMode === 'search' ? 'secondary' : 'ghost'} 
                  size="sm" 
                  onClick={() => setJdMode('search')}
                  className={jdMode === 'search' ? 'bg-zinc-100' : ''}
                >
                  Search jobs
                </Button>
              </div>
            </div>

            {jdMode === 'paste' ? (
              <div className="relative">
                <textarea
                  value={jd}
                  onChange={(e) => setJd(e.target.value)}
                  placeholder="Paste the full job description here..."
                  className="w-full h-52 p-4 text-sm text-zinc-800 border border-zinc-200 outline-none resize-none rounded-2xl focus:ring-1 focus:ring-brand focus:border-brand bg-zinc-50/80"
                />
                <div className="absolute top-3 right-3 text-xs text-zinc-400">
                  {jd.length} chars
                </div>
              </div>
            ) : (
              <div className="text-sm text-zinc-500 p-4 text-center bg-zinc-50 rounded-lg">
                Job search integration coming soon. Use paste for now.
              </div>
            )}
          </div>

          {models.length > 0 && (
            <div className="panel p-6">
              <div className="mb-4">
                <p className="section-title mb-1">Step 3</p>
                <h3 className="text-base font-semibold text-zinc-950">AI Model</h3>
              </div>
              <ModelSelector
                models={models}
                selectedModel={selectedModel}
                onChange={setSelectedModel}
              />
            </div>
          )}
          
          <div className="flex flex-col gap-2">
            <Button 
              size="lg" 
              className="w-full bg-brand hover:bg-brand-hover text-white h-12 shrink-0 rounded-2xl shadow-[0_18px_40px_rgba(26,31,46,0.18)]"
              onClick={handleTailor}
              disabled={!file || jd.length < 50 || loading}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Optimizing Resume
                </>
              ) : (
                'Optimize Resume'
              )}
            </Button>

            <Tooltip>
              <TooltipTrigger 
                render={
                  <Button
                    variant="outline"
                    size="lg"
                    className="w-full h-11 rounded-2xl border-zinc-200 bg-white text-zinc-800 hover:bg-zinc-50"
                    onClick={() => navigate('/agent')}
                  >
                    Optimize with AI Agent
                  </Button>
                }
              />
              <TooltipContent>
                Uses multi-agent reasoning and knowledge retrieval for deeper optimization.
              </TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="flex flex-col lg:overflow-y-auto lg:h-full pl-0 lg:pl-1 pb-4">
          {loading && (
            <div className="panel p-5 mb-4 border-brand-100 bg-brand-50/40">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white border border-brand-100 shadow-sm">
                  <Loader2 className="w-5 h-5 text-brand animate-spin" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-zinc-900">Optimizing resume</p>
                  <p className="text-xs text-zinc-500">Comparing keywords, rewriting sections, and checking ATS fit.</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-brand animate-pulse" />
                  <span className="h-2 w-2 rounded-full bg-brand/70 animate-pulse [animation-delay:150ms]" />
                  <span className="h-2 w-2 rounded-full bg-brand/40 animate-pulse [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}

          {result ? (
            <div className="space-y-4">
              <ATSScore
                score={result.ats_score}
                matchedKeywords={result.matched_keywords}
                missingKeywords={result.missing_keywords}
                totalKeywords={result.total_keywords}
                onImproveAts={handleImproveAts}
                improving={optimizingAts}
                autoImproved={result.auto_improved}
              />

              {/* ── Match Analysis ── */}
              {result.match_analysis && (
                <div className="panel p-5 space-y-4">
                  <div className="flex items-center gap-2.5 mb-2">
                    <Target className="w-4 h-4 text-brand" />
                    <h3 className="text-base font-semibold text-zinc-950">Match Analysis</h3>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-zinc-200 bg-white p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Candidate Strengths</p>
                      <ul className="space-y-1">
                        {result.match_analysis.candidate_strengths?.map((s: string, i: number) => (
                          <li key={i} className="flex gap-2 text-sm text-zinc-700">
                            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded-xl border border-zinc-200 bg-white p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Unmet Requirements</p>
                      <ul className="space-y-1">
                        {result.match_analysis.unmet_requirements?.map((req: string, i: number) => (
                          <li key={i} className="flex gap-2 text-sm text-zinc-700">
                            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
                            {req}
                          </li>
                        ))}
                        {!result.match_analysis.unmet_requirements?.length && (
                          <li className="text-sm text-zinc-500 italic">No significant gaps found.</li>
                        )}
                      </ul>
                    </div>
                  </div>
                  <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3">
                    <p className="text-sm font-medium text-zinc-800 flex gap-2 items-center">
                      <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Verdict</span>
                      {result.match_analysis.fit_verdict}
                    </p>
                  </div>
                </div>
              )}

              {qualityReport && (
                <div className="panel p-5 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="section-title mb-1">Quality report</p>
                      <h3 className="text-base font-semibold text-zinc-950">Validation and review</h3>
                    </div>
                    {hasQualityScores && (
                      <div className="flex items-center gap-2 text-xs text-zinc-500">
                        {typeof qualityReport.humanization_score === 'number' && (
                          <span className="rounded-full border border-emerald-100 bg-emerald-50 px-2.5 py-1 text-emerald-700">
                            Humanization {qualityReport.humanization_score}/100
                          </span>
                        )}
                        {typeof qualityReport.recruiter_readability_score === 'number' && (
                          <span className="rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-zinc-700">
                            Readability {qualityReport.recruiter_readability_score}/100
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-zinc-200 bg-white p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">ATS compatibility</p>
                      <p className="text-sm text-zinc-700 leading-6">{qualityReport.ats_compatibility_report}</p>
                    </div>
                    <div className="rounded-2xl border border-zinc-200 bg-white p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Formatting</p>
                      <p className="text-sm text-zinc-700 leading-6">{qualityReport.formatting_report}</p>
                    </div>
                    <div className="rounded-2xl border border-zinc-200 bg-white p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Grammar</p>
                      <p className="text-sm text-zinc-700 leading-6">{qualityReport.grammar_report}</p>
                    </div>
                    <div className="rounded-2xl border border-zinc-200 bg-white p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Confidence</p>
                      <p className="text-sm text-zinc-700 leading-6">{qualityReport.confidence_report}</p>
                    </div>
                  </div>

                  {hasQualityChanges && (
                    <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Changes made</p>
                      <ul className="space-y-2 text-sm text-zinc-700 leading-6">
                        {qualityReport.changes_made!.slice(0, 4).map((change) => (
                          <li key={change} className="flex gap-2">
                            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-brand shrink-0" />
                            <span>{change}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {hasQualityComparison && (
                    <div className="grid gap-3 sm:grid-cols-3">
                      {[
                        { label: 'ATS score', before: qualityReport.before_after_comparison!.ats_before, after: qualityReport.before_after_comparison!.ats_after },
                        { label: 'Keyword coverage', before: qualityReport.before_after_comparison!.keyword_coverage_before, after: qualityReport.before_after_comparison!.keyword_coverage_after },
                        { label: 'Missing keywords', before: qualityReport.before_after_comparison!.missing_before, after: qualityReport.before_after_comparison!.missing_after },
                      ].map((item) => (
                        <div key={item.label} className="rounded-2xl border border-zinc-200 bg-white p-4">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">{item.label}</p>
                          <div className="flex items-baseline gap-2">
                            <span className="text-sm text-zinc-400">{item.before}</span>
                            <span className="text-xs text-zinc-400">→</span>
                            <span className="text-sm font-semibold text-zinc-900">{item.after}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <ResumePreview 
                resume={result.tailored_resume} 
                atsScore={result.ats_score}
                onResumeChange={(updated) => setResult({...result, tailored_resume: updated})} 
              />

              {/* ── Cover Letter ── */}
              {result.cover_letter?.body && (
                <div className="panel overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between gap-3 p-5 text-left hover:bg-zinc-50/60 transition-colors"
                    onClick={() => setOpenPanel(openPanel === 'cover_letter' ? null : 'cover_letter')}
                  >
                    <div className="flex items-center gap-2.5">
                      <MessageSquare className="w-4 h-4 text-brand" />
                      <div>
                        <p className="section-title mb-0.5">Agent Generated</p>
                        <h3 className="text-base font-semibold text-zinc-950">Cover Letter</h3>
                      </div>
                    </div>
                    {openPanel === 'cover_letter' ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
                  </button>
                  {openPanel === 'cover_letter' && (
                    <div className="px-5 pb-5 space-y-3">
                      {result.cover_letter.subject_line && (
                        <div className="rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-2.5">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400 mb-1">Subject</p>
                          <p className="text-sm font-medium text-zinc-800">{result.cover_letter.subject_line}</p>
                        </div>
                      )}
                      <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3">
                        <p className="text-sm text-zinc-700 whitespace-pre-wrap leading-7">{result.cover_letter.body}</p>
                      </div>
                      <button
                        className="text-xs text-brand hover:text-brand-hover font-medium transition-colors"
                        onClick={() => {
                          navigator.clipboard.writeText(
                            (result.cover_letter.subject_line ? `Subject: ${result.cover_letter.subject_line}\n\n` : '') + result.cover_letter.body
                          )
                          toast.success('Cover letter copied!')
                        }}
                      >
                        Copy to clipboard
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* ── Application Email ── */}
              {result.application_email?.body && (
                <div className="panel overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between gap-3 p-5 text-left hover:bg-zinc-50/60 transition-colors"
                    onClick={() => setOpenPanel(openPanel === 'app_email' ? null : 'app_email')}
                  >
                    <div className="flex items-center gap-2.5">
                      <Mail className="w-4 h-4 text-brand" />
                      <div>
                        <p className="section-title mb-0.5">Agent Generated</p>
                        <h3 className="text-base font-semibold text-zinc-950">Application Email</h3>
                      </div>
                    </div>
                    {openPanel === 'app_email' ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
                  </button>
                  {openPanel === 'app_email' && (
                    <div className="px-5 pb-5 space-y-3">
                      {result.application_email.subject_line && (
                        <div className="rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-2.5">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400 mb-1">Subject</p>
                          <p className="text-sm font-medium text-zinc-800">{result.application_email.subject_line}</p>
                        </div>
                      )}
                      <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3">
                        <p className="text-sm text-zinc-700 whitespace-pre-wrap leading-7">{result.application_email.body}</p>
                      </div>
                      <button
                        className="text-xs text-brand hover:text-brand-hover font-medium transition-colors"
                        onClick={() => {
                          navigator.clipboard.writeText(
                            (result.application_email.subject_line ? `Subject: ${result.application_email.subject_line}\n\n` : '') + result.application_email.body
                          )
                          toast.success('Email copied!')
                        }}
                      >
                        Copy to clipboard
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* ── Interview Prep ── */}
              {interviewPrep && (
                <div className="panel overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between gap-3 p-5 text-left hover:bg-zinc-50/60 transition-colors"
                    onClick={() => setOpenPanel(openPanel === 'interview' ? null : 'interview')}
                  >
                    <div className="flex items-center gap-2.5">
                      <Mic className="w-4 h-4 text-brand" />
                      <div>
                        <p className="section-title mb-0.5">Agent Generated</p>
                        <h3 className="text-base font-semibold text-zinc-950">Interview Prep</h3>
                      </div>
                    </div>
                    {openPanel === 'interview' ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
                  </button>
                  {openPanel === 'interview' && (
                    <div className="px-5 pb-5 space-y-4">
                      {interviewPrep.likely_technical_questions?.length > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Technical Questions</p>
                          <div className="space-y-2">
                            {interviewPrep.likely_technical_questions.map((q, i) => (
                              <div key={i} className="rounded-xl border border-zinc-200 bg-white p-3.5">
                                <p className="text-sm font-semibold text-zinc-800 mb-1">{q.question}</p>
                                {q.tip && <p className="text-xs text-zinc-500 italic">💡 {q.tip}</p>}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {interviewPrep.likely_behavioral_questions?.length > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Behavioral Questions</p>
                          <div className="space-y-2">
                            {interviewPrep.likely_behavioral_questions.map((q, i) => (
                              <div key={i} className="rounded-xl border border-zinc-200 bg-white p-3.5">
                                <p className="text-sm font-semibold text-zinc-800 mb-1">{q.question}</p>
                                {q.star_prompt && <p className="text-xs text-zinc-500 italic">⭐ {q.star_prompt}</p>}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      {interviewPrep.strengths_to_highlight?.length > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Strengths to Highlight</p>
                          <ul className="space-y-1">
                            {interviewPrep.strengths_to_highlight.map((s, i) => (
                              <li key={i} className="flex gap-2 text-sm text-zinc-700">
                                <span className="mt-2 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
                                {s}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {interviewPrep.gaps_to_prepare_for?.length > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Gaps to Prepare For</p>
                          <ul className="space-y-1">
                            {interviewPrep.gaps_to_prepare_for.map((g, i) => (
                              <li key={i} className="flex gap-2 text-sm text-zinc-700">
                                <span className="mt-2 h-1.5 w-1.5 rounded-full bg-amber-400 shrink-0" />
                                {g}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {interviewPrep.questions_to_ask_interviewer?.length > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500 mb-2">Questions to Ask the Interviewer</p>
                          <ul className="space-y-1">
                            {interviewPrep.questions_to_ask_interviewer.map((q, i) => (
                              <li key={i} className="flex gap-2 text-sm text-zinc-700">
                                <span className="mt-2 h-1.5 w-1.5 rounded-full bg-brand shrink-0" />
                                {q}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* ── LinkedIn Message ── */}
              {result.linkedin_message?.message && (
                <div className="panel overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between gap-3 p-5 text-left hover:bg-zinc-50/60 transition-colors"
                    onClick={() => setOpenPanel(openPanel === 'linkedin' ? null : 'linkedin')}
                  >
                    <div className="flex items-center gap-2.5">
                      <LinkIcon className="w-4 h-4 text-brand" />
                      <div>
                        <p className="section-title mb-0.5">Agent Generated</p>
                        <h3 className="text-base font-semibold text-zinc-950">LinkedIn Connection Note</h3>
                      </div>
                    </div>
                    {openPanel === 'linkedin' ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
                  </button>
                  {openPanel === 'linkedin' && (
                    <div className="px-5 pb-5 space-y-3">
                      <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3">
                        <p className="text-sm text-zinc-700 whitespace-pre-wrap leading-7">{result.linkedin_message.message}</p>
                      </div>
                      <button
                        className="text-xs text-brand hover:text-brand-hover font-medium transition-colors"
                        onClick={() => {
                          navigator.clipboard.writeText(result.linkedin_message!.message)
                          toast.success('LinkedIn note copied!')
                        }}
                      >
                        Copy to clipboard
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* ── Recruiter Tips ── */}
              {result.recruiter_tips?.tips && result.recruiter_tips.tips.length > 0 && (
                <div className="panel overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between gap-3 p-5 text-left hover:bg-zinc-50/60 transition-colors"
                    onClick={() => setOpenPanel(openPanel === 'tips' ? null : 'tips')}
                  >
                    <div className="flex items-center gap-2.5">
                      <Lightbulb className="w-4 h-4 text-brand" />
                      <div>
                        <p className="section-title mb-0.5">Agent Generated</p>
                        <h3 className="text-base font-semibold text-zinc-950">Recruiter Tips</h3>
                      </div>
                    </div>
                    {openPanel === 'tips' ? <ChevronUp className="w-4 h-4 text-zinc-400" /> : <ChevronDown className="w-4 h-4 text-zinc-400" />}
                  </button>
                  {openPanel === 'tips' && (
                    <div className="px-5 pb-5">
                      <ul className="space-y-3">
                        {result.recruiter_tips.tips.map((tip: string, i: number) => (
                          <li key={i} className="flex gap-3 text-sm text-zinc-700 bg-zinc-50 p-3 rounded-lg border border-zinc-100">
                            <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-brand shrink-0" />
                            {tip}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* ── Feedback ── */}
              <div className="panel p-5 flex flex-col items-center gap-3 text-center">
                <p className="text-xs font-semibold uppercase tracking-widest text-zinc-400">Was this result helpful?</p>
                {feedbackRating ? (
                  <p className="text-sm text-emerald-600 font-medium">
                    {feedbackRating === 'up' ? 'Thanks! This helps us improve.' : 'Got it — we\'ll refine our model.'}
                  </p>
                ) : (
                  <div className="flex gap-3">
                    <button
                      disabled={feedbackSaving}
                      onClick={async () => {
                        setFeedbackSaving(true)
                        try {
                          if (result.history_id) await submitFeedback(result.history_id, 'up')
                          setFeedbackRating('up')
                          toast.success('Thanks for the feedback!')
                        } catch {
                          toast.error('Could not save feedback.')
                        } finally {
                          setFeedbackSaving(false)
                        }
                      }}
                      className="flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:border-emerald-400 hover:text-emerald-600 hover:bg-emerald-50 transition-all disabled:opacity-50"
                    >
                      <ThumbsUp className="w-4 h-4" /> Helpful
                    </button>
                    <button
                      disabled={feedbackSaving}
                      onClick={async () => {
                        setFeedbackSaving(true)
                        try {
                          if (result.history_id) await submitFeedback(result.history_id, 'down')
                          setFeedbackRating('down')
                          toast.success('Feedback noted.')
                        } catch {
                          toast.error('Could not save feedback.')
                        } finally {
                          setFeedbackSaving(false)
                        }
                      }}
                      className="flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:border-rose-400 hover:text-rose-500 hover:bg-rose-50 transition-all disabled:opacity-50"
                    >
                      <ThumbsDown className="w-4 h-4" /> Not helpful
                    </button>
                  </div>
                )}
              </div>

            </div>
          ) : (
            <div className="panel flex-1 flex flex-col items-center justify-center text-zinc-400 text-sm min-h-[400px] p-8">
              <FileText className="w-10 h-10 text-zinc-300 mb-3 shrink-0" />
              Upload resume and paste a job description to see results.
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
