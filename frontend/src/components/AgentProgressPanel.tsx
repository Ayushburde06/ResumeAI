import React from 'react'
import {
  Brain,
  BookOpen,
  ClipboardCheck,
  FileText,
  Flag,
  Link,
  Lightbulb,
  Mail,
  Mic,
  PenTool,
  RefreshCw,
  Search,
  Settings,
  Sparkles,
  Upload,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Layers,
} from 'lucide-react'
import type { AgentStep } from '../types'

interface Props {
  steps: AgentStep[]
  isRunning: boolean
}

const STEP_META: Record<string, { label: string; icon: React.ReactNode }> = {
  // Phase 1
  parse_resume:      { label: 'Parsing resume',                    icon: <Upload className="w-4.5 h-4.5 text-zinc-500" /> },
  jd_analysis:       { label: 'Analysing job description',         icon: <Search className="w-4.5 h-4.5 text-zinc-500" /> },
  ats_baseline:      { label: 'Running baseline ATS scan',         icon: <TrendingUp className="w-4.5 h-4.5 text-zinc-500" /> },
  rag_retrieval:     { label: 'Retrieving ATS & industry context', icon: <BookOpen className="w-4.5 h-4.5 text-zinc-500" /> },
  // Phase 2
  gap_analysis:      { label: 'Identifying keyword gaps',          icon: <Flag className="w-4.5 h-4.5 text-zinc-500" /> },
  optimization_plan: { label: 'Building section-level plan',       icon: <Brain className="w-4.5 h-4.5 text-zinc-500" /> },
  planning:          { label: 'Planning optimization strategy',    icon: <Brain className="w-4.5 h-4.5 text-zinc-500" /> },
  // Phase 3
  rewrite:           { label: 'Rewriting resume sections',         icon: <PenTool className="w-4.5 h-4.5 text-zinc-500" /> },
  critique:          { label: 'Self-reviewing draft',              icon: <RefreshCw className="w-4.5 h-4.5 text-zinc-500" /> },
  // Phase 4
  humanization:      { label: 'Humanizing rewritten sections',     icon: <Sparkles className="w-4.5 h-4.5 text-zinc-500" /> },
  ats_validation:    { label: 'Validating ATS compatibility',      icon: <ClipboardCheck className="w-4.5 h-4.5 text-zinc-500" /> },
  humanization_check:{ label: 'Checking human tone',              icon: <Sparkles className="w-4.5 h-4.5 text-zinc-500" /> },
  grammar_check:     { label: 'Running grammar review',            icon: <CheckCircle2 className="w-4.5 h-4.5 text-zinc-500" /> },
  reflection:        { label: 'Reflection & quality pass',         icon: <Layers className="w-4.5 h-4.5 text-zinc-500" /> },
  final_review:      { label: 'Final review',                      icon: <ClipboardCheck className="w-4.5 h-4.5 text-zinc-500" /> },
  resume_generation: { label: 'Assembling final resume',           icon: <FileText className="w-4.5 h-4.5 text-zinc-500" /> },
  // Phase 5
  cover_letter:      { label: 'Generating cover letter',           icon: <FileText className="w-4.5 h-4.5 text-zinc-500" /> },
  email:             { label: 'Generating application email',      icon: <Mail className="w-4.5 h-4.5 text-zinc-500" /> },
  interview_prep:    { label: 'Preparing interview questions',     icon: <Mic className="w-4.5 h-4.5 text-zinc-500" /> },
  linkedin_message:  { label: 'Drafting LinkedIn message',         icon: <Link className="w-4.5 h-4.5 text-zinc-500" /> },
  recruiter_tips:    { label: 'Generating recruiter tips',         icon: <Lightbulb className="w-4.5 h-4.5 text-zinc-500" /> },
  // Terminal
  complete:          { label: 'Complete',                          icon: <CheckCircle2 className="w-4.5 h-4.5 text-emerald-500" /> },
  error:             { label: 'Error',                             icon: <AlertTriangle className="w-4.5 h-4.5 text-red-500" /> },
}

function StepBadge({ status }: { status: AgentStep['status'] }) {
  if (status === 'running') {
    return (
      <span className="agent-badge running">
        <span className="agent-spinner" />
        Running
      </span>
    )
  }
  if (status === 'done') {
    return <span className="agent-badge done">Done</span>
  }
  return <span className="agent-badge error">Error</span>
}

function StepDetail({ step }: { step: AgentStep }) {
  if (step.step === 'rewrite' && step.status === 'done') {
    const hit = step.target_reached
    return (
      <span className="agent-step-detail">
        ATS{' '}
        <strong style={{ color: hit ? '#16a34a' : '#d97706' }}>
          {step.ats_score}%
        </strong>
        {step.iteration && step.max_iterations && (
          <span style={{ color: '#94a3b8', marginLeft: 6 }}>
            attempt {step.iteration}/{step.max_iterations}
          </span>
        )}
        {hit && (
          <span style={{ color: '#16a34a', marginLeft: 6, fontSize: 11, fontWeight: 700 }}>
            {' '}
            TARGET
          </span>
        )}
      </span>
    )
  }

  if (step.step === 'planning' && step.status === 'done' && step.strategy) {
    return (
      <span className="agent-step-detail" style={{ fontStyle: 'italic' }}>
        {step.strategy.slice(0, 70)}{step.strategy.length > 70 ? '...' : ''}
      </span>
    )
  }

  if (step.step === 'gap_analysis' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        {step.missing_count ?? 0} keyword gaps found
      </span>
    )
  }

  if (step.step === 'rag_retrieval' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        {step.chunks_retrieved ? 'Context loaded' : 'No context found'}
      </span>
    )
  }

  if (step.step === 'ats_validation' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        {step.validation_summary ?? step.validation_status ?? 'Validation complete'}
      </span>
    )
  }

  if (step.step === 'humanization_check' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        Tone score {step.humanization_score ?? 0}/100
      </span>
    )
  }

  if (step.step === 'grammar_check' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        Grammar score {step.grammar_score ?? 0}/100
      </span>
    )
  }

  if (step.step === 'reflection' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        {step.reflection_summary ?? step.message ?? 'Reflection complete'}
      </span>
    )
  }

  if (step.step === 'final_review' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        Readability {step.recruiter_readability_score ?? 0}/100
      </span>
    )
  }

  if (step.step === 'critique' && step.status === 'done' && step.priority_fixes?.length) {
    return (
      <span className="agent-step-detail">
        Fixes: {step.priority_fixes.slice(0, 3).join(', ')}
      </span>
    )
  }

  return null
}

export default function AgentProgressPanel({ steps, isRunning }: Props) {
  const seen = new Map<string, AgentStep>()
  for (const s of steps) {
    const key = s.step + (s.iteration ?? '')
    seen.set(key, s)
  }
  const dedupedSteps = Array.from(seen.values())

  return (
    <div className="agent-panel">
      <div className="agent-panel-header">
        <div className="agent-panel-title">
          <Brain className="w-4.5 h-4.5 text-zinc-600" />
          <span>Agent Progress</span>
          {isRunning && <span className="agent-live-dot" />}
        </div>
        {!isRunning && dedupedSteps.length > 0 && (
          <span className="agent-panel-complete-label">Complete</span>
        )}
      </div>

      <div className="agent-steps-list">
        {dedupedSteps.map((s, idx) => {
          const meta = STEP_META[s.step] ?? { label: s.step, icon: <Settings className="w-4.5 h-4.5 text-zinc-400" /> }
          const labelSuffix = s.step === 'rewrite' && s.iteration ? ` (attempt ${s.iteration})` : ''

          return (
            <div
              key={idx}
              className={`agent-step-row ${s.status}`}
            >
              <span className="agent-step-icon">{meta.icon}</span>
              <div className="agent-step-body">
                <span className="agent-step-label">
                  {meta.label}{labelSuffix}
                </span>
                <StepDetail step={s} />
              </div>
              <StepBadge status={s.status} />
            </div>
          )
        })}

        {isRunning && dedupedSteps.length === 0 && (
          <div className="agent-step-row running">
            <span className="agent-step-icon">
              <Brain className="w-4.5 h-4.5 text-zinc-500 animate-pulse" />
            </span>
            <div className="agent-step-body">
              <span className="agent-step-label">Starting agent...</span>
            </div>
            <StepBadge status="running" />
          </div>
        )}
      </div>
    </div>
  )
}
