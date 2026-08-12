export type AgentState =
  | 'idle'
  | 'uploading'
  | 'analyzing'
  | 'planning'
  | 'writing'
  | 'scoring'
  | 'done'
  | 'error'
  | 'partial'

const VALID_TRANSITIONS: Record<AgentState, AgentState[]> = {
  idle: ['uploading'],
  uploading: ['analyzing', 'error'],
  analyzing: ['planning', 'writing', 'error'],
  planning: ['writing', 'error'],
  writing: ['scoring', 'partial', 'error', 'done'],
  scoring: ['done', 'error'],
  error: ['idle'],
  partial: ['idle'],
  done: ['idle'],
}

export function transitionState(current: AgentState, next: AgentState): AgentState {
  if (!VALID_TRANSITIONS[current].includes(next)) {
    console.warn(`[State Machine] Invalid transition: ${current} → ${next}`)
    return current
  }
  return next
}
