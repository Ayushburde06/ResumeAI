import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, X, Loader2 } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { toast } from 'sonner'
import type { AnalyzeResponse, ModelInfo } from '../types'
import ResumePreview from './ResumePreview'
import ATSScore from './ATSScore'
import ModelSelector from './ModelSelector'
import { fetchModels, improveAtsScore } from '../lib/api'

interface UnifiedWorkspaceProps {
  initialFile?: File | null
  initialJd?: string
  initialResult?: AnalyzeResponse | null
  onAnalyze: (file: File, jd: string, modelId?: string) => Promise<AnalyzeResponse>
}

export default function UnifiedWorkspace({
  initialFile = null,
  initialJd = '',
  initialResult = null,
  onAnalyze,
}: UnifiedWorkspaceProps) {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(initialFile)
  const [jd, setJd] = useState(initialJd)
  const [jdMode, setJdMode] = useState<'paste' | 'search'>('paste')
  const [result, setResult] = useState<AnalyzeResponse | null>(initialResult)
  const [loading, setLoading] = useState(false)
  const [optimizingAts, setOptimizingAts] = useState(false)
  const [models, setModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState('')
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
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setFile(acceptedFiles[0])
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
    setLoading(true)
    try {
      const res = await onAnalyze(file, jd, selectedModel || undefined)
      setResult(res)
      toast.success('Resume tailored successfully!')
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
              <TooltipTrigger>
                <Button
                  variant="outline"
                  size="lg"
                  className="w-full h-11 rounded-2xl border-zinc-200 bg-white text-zinc-800 hover:bg-zinc-50"
                  onClick={() => navigate('/agent')}
                >
                  Optimize with AI Agent
                </Button>
              </TooltipTrigger>
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
