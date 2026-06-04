import { useState } from 'react'
import { ChevronDown, ChevronUp, Lightbulb, AlertTriangle, MessageSquare, TrendingUp } from 'lucide-react'
import type { InterviewPrep as InterviewPrepType } from '../types'

interface Props {
  interviewPrep: InterviewPrepType
}

function Accordion({
  title,
  icon,
  accent,
  children,
  defaultOpen = false,
}: {
  title: string
  icon: React.ReactNode
  accent: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className={`interview-accordion ${accent}`}>
      <button
        onClick={() => setOpen(!open)}
        className="interview-accordion-header"
      >
        <div className="interview-accordion-title">
          {icon}
          <span>{title}</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>
      {open && <div className="interview-accordion-body">{children}</div>}
    </div>
  )
}

export default function InterviewPrep({ interviewPrep }: Props) {
  const {
    likely_technical_questions = [],
    likely_behavioral_questions = [],
    strengths_to_highlight = [],
    gaps_to_prepare_for = [],
    questions_to_ask_interviewer = [],
  } = interviewPrep

  return (
    <div className="interview-prep-root">
      <div className="flex items-center gap-2 mb-5">
        <div className="w-8 h-8 bg-violet-100 rounded-lg flex items-center justify-center">
          <span className="text-lg">🎤</span>
        </div>
        <div>
          <h2 className="font-bold text-gray-900 text-sm">Interview Preparation</h2>
          <p className="text-xs text-gray-500">AI-generated Q&A tailored to your resume + this role</p>
        </div>
      </div>

      <div className="space-y-3">
        {/* Technical Questions */}
        <Accordion
          title={`Technical Questions (${likely_technical_questions.length})`}
          icon={<span className="text-base">💻</span>}
          accent="accent-violet"
          defaultOpen
        >
          <div className="space-y-4">
            {likely_technical_questions.map((q, i) => (
              <div key={i} className="interview-question-card">
                <p className="font-medium text-gray-900 text-sm mb-1">
                  {i + 1}. {q.question}
                </p>
                {q.why_asked && (
                  <p className="text-xs text-gray-500 mb-2">
                    <span className="font-medium text-gray-600">Tests:</span> {q.why_asked}
                  </p>
                )}
                {q.tip && (
                  <div className="interview-tip">
                    <Lightbulb className="w-3 h-3 flex-shrink-0 mt-0.5 text-amber-500" />
                    <span>{q.tip}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Accordion>

        {/* Behavioral Questions */}
        <Accordion
          title={`Behavioural Questions (${likely_behavioral_questions.length})`}
          icon={<span className="text-base">🧩</span>}
          accent="accent-blue"
        >
          <div className="space-y-4">
            {likely_behavioral_questions.map((q, i) => (
              <div key={i} className="interview-question-card">
                <p className="font-medium text-gray-900 text-sm mb-1">
                  {i + 1}. {q.question}
                </p>
                {q.star_prompt && (
                  <div className="interview-tip blue">
                    <MessageSquare className="w-3 h-3 flex-shrink-0 mt-0.5 text-blue-500" />
                    <span><span className="font-medium">STAR hint:</span> {q.star_prompt}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Accordion>

        {/* Strengths */}
        {strengths_to_highlight.length > 0 && (
          <Accordion
            title={`Strengths to Highlight (${strengths_to_highlight.length})`}
            icon={<TrendingUp className="w-4 h-4" />}
            accent="accent-green"
          >
            <ul className="space-y-2">
              {strengths_to_highlight.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="flex-shrink-0 w-5 h-5 bg-green-100 text-green-700 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5">
                    {i + 1}
                  </span>
                  {s}
                </li>
              ))}
            </ul>
          </Accordion>
        )}

        {/* Gaps */}
        {gaps_to_prepare_for.length > 0 && (
          <Accordion
            title={`Gaps to Prepare For (${gaps_to_prepare_for.length})`}
            icon={<AlertTriangle className="w-4 h-4" />}
            accent="accent-amber"
          >
            <ul className="space-y-2">
              {gaps_to_prepare_for.map((g, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="flex-shrink-0 mt-1 w-1.5 h-1.5 bg-amber-400 rounded-full" />
                  {g}
                </li>
              ))}
            </ul>
          </Accordion>
        )}

        {/* Questions to Ask */}
        {questions_to_ask_interviewer.length > 0 && (
          <Accordion
            title="Questions to Ask the Interviewer"
            icon={<span className="text-base">🙋</span>}
            accent="accent-slate"
          >
            <ul className="space-y-2">
              {questions_to_ask_interviewer.map((q, i) => (
                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                  <span className="text-gray-400 flex-shrink-0">→</span>
                  {q}
                </li>
              ))}
            </ul>
          </Accordion>
        )}
      </div>
    </div>
  )
}
