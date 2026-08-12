import React from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
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
import { transitionFast } from '@/lib/motion'
import { Badge } from '@/components/ui/badge'

interface Props {
  steps: AgentStep[]
  isRunning: boolean
}

const STEP_META: Record<string, { label: string; icon: React.ReactNode }> = {
  parse_resume:      { label: 'Parsing resume',                    icon: <Upload className="w-4.5 h-4.5 text-zinc-500" /> },
  jd_analysis:       { label: 'Analysing job description',         icon: <Search className="w-4.5 h-4.5 text-zinc-500" /> },
  ats_baseline:      { label: 'Running baseline ATS scan',         icon: <TrendingUp className="w-4.5 h-4.5 text-zinc-500" /> },
  rag_retrieval:     { label: 'Retrieving ATS & industry context', icon: <BookOpen className="w-4.5 h-4.5 text-zinc-500" /> },
  structural_parse:  { label: 'Structuring resume data',           icon: <Layers className="w-4.5 h-4.5 text-zinc-500" /> },
  career_identity:   { label: 'Identifying career focus',          icon: <Brain className="w-4.5 h-4.5 text-zinc-500" /> },
  evidence_mapping:  { label: 'Mapping evidence to the JD',        icon: <ClipboardCheck className="w-4.5 h-4.5 text-zinc-500" /> },
  ranking:           { label: 'Prioritizing strongest evidence',   icon: <TrendingUp className="w-4.5 h-4.5 text-zinc-500" /> },
  domain_classify:   { label: 'Classifying role domain',           icon: <Brain className="w-4.5 h-4.5 text-zinc-500" /> },
  capability_graph:  { label: 'Building capability graph',         icon: <Layers className="w-4.5 h-4.5 text-zinc-500" /> },
  adaptive_gap:      { label: 'Computing adaptive gap diff',       icon: <TrendingUp className="w-4.5 h-4.5 text-zinc-500" /> },
  gap_analysis:      { label: 'Finding gaps vs the JD',            icon: <Flag className="w-4.5 h-4.5 text-zinc-500" /> },
  hr_review:         { label: 'HR recruiter is reviewing',         icon: <Search className="w-4.5 h-4.5 text-zinc-500" /> },
  hm_review:         { label: 'Technical hiring manager review',   icon: <Settings className="w-4.5 h-4.5 text-zinc-500" /> },
  rewrite:           { label: 'Fixing issues from reviewers',      icon: <PenTool className="w-4.5 h-4.5 text-zinc-500" /> },
  jd_poster_review:  { label: 'Founder / JD poster is reviewing',  icon: <Flag className="w-4.5 h-4.5 text-zinc-500" /> },
  fact_check:        { label: 'Checking evidence honesty',         icon: <ClipboardCheck className="w-4.5 h-4.5 text-zinc-500" /> },
  quality_loop:      { label: 'Self-fixing reviewer flags',        icon: <RefreshCw className="w-4.5 h-4.5 text-zinc-500" /> },
  optimization_plan: { label: 'Building section-level plan',       icon: <Brain className="w-4.5 h-4.5 text-zinc-500" /> },
  planning:          { label: 'Planning optimization strategy',    icon: <Brain className="w-4.5 h-4.5 text-zinc-500" /> },
  critique:          { label: 'Self-reviewing draft',              icon: <RefreshCw className="w-4.5 h-4.5 text-zinc-500" /> },
  humanization:      { label: 'Humanizing rewritten sections',     icon: <Sparkles className="w-4.5 h-4.5 text-zinc-500" /> },
  ats_validation:    { label: 'Final ATS & composite check',       icon: <ClipboardCheck className="w-4.5 h-4.5 text-zinc-500" /> },
  humanization_check:{ label: 'Checking human tone',              icon: <Sparkles className="w-4.5 h-4.5 text-zinc-500" /> },
  grammar_check:     { label: 'Running grammar review',            icon: <CheckCircle2 className="w-4.5 h-4.5 text-zinc-500" /> },
  reflection:        { label: 'Reflection & quality pass',         icon: <Layers className="w-4.5 h-4.5 text-zinc-500" /> },
  final_review:      { label: 'Final hiring call',                 icon: <ClipboardCheck className="w-4.5 h-4.5 text-zinc-500" /> },
  resume_generation: { label: 'Assembling final resume',           icon: <FileText className="w-4.5 h-4.5 text-zinc-500" /> },
  cover_letter:      { label: 'Generating cover letter',           icon: <FileText className="w-4.5 h-4.5 text-zinc-500" /> },
  email:             { label: 'Generating application email',      icon: <Mail className="w-4.5 h-4.5 text-zinc-500" /> },
  interview_prep:    { label: 'Preparing interview questions',     icon: <Mic className="w-4.5 h-4.5 text-zinc-500" /> },
  linkedin_message:  { label: 'Drafting LinkedIn message',         icon: <Link className="w-4.5 h-4.5 text-zinc-500" /> },
  recruiter_tips:    { label: 'Generating recruiter tips',         icon: <Lightbulb className="w-4.5 h-4.5 text-zinc-500" /> },
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
    return <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-200 border-none">Done</Badge>
  }
  return <Badge variant="destructive">Error</Badge>
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

  if (step.step === 'domain_classify' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        Identified {step.domain} ({step.role_type})
      </span>
    )
  }

  if (step.step === 'capability_graph' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        Mapped {step.skills_mapped ?? 0} explicit capabilities
      </span>
    )
  }

  if (step.step === 'adaptive_gap' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        Found {step.bridgeable_count ?? 0} bridgeable gaps
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
    const color = step.final_signal === 'GREEN' ? '#16a34a' : step.final_signal === 'YELLOW' ? '#d97706' : step.final_signal === 'RED' ? '#dc2626' : '#64748b'
    return (
      <span className="agent-step-detail">
        <strong style={{ color }}>{step.final_signal || 'DONE'}</strong>
        {step.final_call ? ` — ${String(step.final_call).slice(0, 80)}` : ''}
      </span>
    )
  }

  if (
    (step.step === 'hr_review' || step.step === 'hm_review' || step.step === 'jd_poster_review') &&
    step.status === 'done'
  ) {
    const color = step.signal === 'GREEN' ? '#16a34a' : '#dc2626'
    return (
      <span className="agent-step-detail">
        <strong style={{ color }}>{step.signal || '—'}</strong>
        {step.signal_reason ? ` — ${String(step.signal_reason).slice(0, 70)}` : ''}
      </span>
    )
  }

  if (step.step === 'quality_loop' && step.status === 'done') {
    return (
      <span className="agent-step-detail">
        {step.message || `${step.iteration ?? 0} fix pass(es)`}
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
  const reduceMotion = useReducedMotion()
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
          {isRunning && <span className="agent-live-dot" aria-label="Live" />}
        </div>
        {!isRunning && dedupedSteps.length > 0 && (
          <span className="agent-panel-complete-label">Complete</span>
        )}
      </div>

      <div className="agent-steps-list">
        <AnimatePresence initial={false}>
          {dedupedSteps.map((s, idx) => {
            const meta = STEP_META[s.step] ?? { label: s.step, icon: <Settings className="w-4.5 h-4.5 text-zinc-400" /> }
            const labelSuffix = s.step === 'rewrite' && s.iteration ? ` (attempt ${s.iteration})` : ''
            const key = `${s.step}-${s.iteration ?? 0}-${idx}`

            return (
              <motion.div
                key={key}
                layout={!reduceMotion}
                className={`agent-step-row ${s.status}`}
                initial={reduceMotion ? false : { opacity: 0, y: 10, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
                transition={transitionFast}
              >
                <span className="agent-step-icon">{meta.icon}</span>
                <div className="agent-step-body">
                  <span className="agent-step-label">
                    {meta.label}{labelSuffix}
                  </span>
                  <StepDetail step={s} />
                </div>
                <StepBadge status={s.status} />
              </motion.div>
            )
          })}
        </AnimatePresence>

        {isRunning && dedupedSteps.length === 0 && (
          <motion.div
            className="agent-step-row running"
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <span className="agent-step-icon">
              <Brain className="w-4.5 h-4.5 text-zinc-500" />
            </span>
            <div className="agent-step-body">
              <span className="agent-step-label">Starting agent...</span>
            </div>
            <StepBadge status="running" />
          </motion.div>
        )}
      </div>
    </div>
  )
}
