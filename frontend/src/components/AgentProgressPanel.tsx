import type { AgentStep } from '../types'

interface Props {
  steps: AgentStep[]
  isRunning: boolean
}

const STEP_META: Record<string, { label: string; icon: string }> = {
  planning:       { label: 'Planning strategy',              icon: '🧠' },
  rag_retrieval:  { label: 'Retrieving industry knowledge',  icon: '📚' },
  jd_analysis:    { label: 'Analysing job requirements',     icon: '🔍' },
  rewrite:        { label: 'Rewriting resume',               icon: '✍️'  },
  critique:       { label: 'Self-critiquing output',         icon: '🔄' },
  cover_letter:   { label: 'Generating cover letter',        icon: '🎯' },
  email:          { label: 'Generating application email',   icon: '📧' },
  interview_prep: { label: 'Preparing interview questions',  icon: '🎤' },
  complete:       { label: 'Done!',                          icon: '✅' },
  error:          { label: 'Error',                          icon: '❌' },
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
        ATS:{' '}
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
            ✓ TARGET
          </span>
        )}
      </span>
    )
  }
  if (step.step === 'planning' && step.status === 'done' && step.strategy) {
    return (
      <span className="agent-step-detail" style={{ fontStyle: 'italic' }}>
        {step.strategy.slice(0, 70)}{step.strategy.length > 70 ? '…' : ''}
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
  // Deduplicate: keep latest event per (step, iteration) key
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
          <span className="agent-brain-icon">🤖</span>
          <span>Agent Progress</span>
          {isRunning && <span className="agent-live-dot" />}
        </div>
        {!isRunning && dedupedSteps.length > 0 && (
          <span className="agent-panel-complete-label">Complete</span>
        )}
      </div>

      <div className="agent-steps-list">
        {dedupedSteps.map((s, idx) => {
          const meta = STEP_META[s.step] ?? { label: s.step, icon: '⚙️' }
          const labelSuffix =
            s.step === 'rewrite' && s.iteration ? ` (attempt ${s.iteration})` : ''

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
            <span className="agent-step-icon">🧠</span>
            <div className="agent-step-body">
              <span className="agent-step-label">Starting agent…</span>
            </div>
            <StepBadge status="running" />
          </div>
        )}
      </div>
    </div>
  )
}
