import { useState } from 'react'
import { Copy, Check, Send } from 'lucide-react'

interface ApplicationEmail {
  subject_line?: string
  body?: string
}

interface Props {
  email: ApplicationEmail
}

export default function ApplicationEmail({ email }: Props) {
  const [copiedSubject, setCopiedSubject] = useState(false)
  const [copiedBody, setCopiedBody] = useState(false)

  async function handleCopySubject() {
    if (!email?.subject_line) return
    await navigator.clipboard.writeText(email.subject_line)
    setCopiedSubject(true)
    setTimeout(() => setCopiedSubject(false), 2500)
  }

  async function handleCopyBody() {
    const text = [email?.subject_line, email?.body].filter(Boolean).join('\n\n')
    await navigator.clipboard.writeText(text)
    setCopiedBody(true)
    setTimeout(() => setCopiedBody(false), 2500)
  }

  if (!email?.body) {
    return (
      <div className="card p-5">
        <p className="text-sm text-center py-8" style={{ color: 'var(--text-faint)' }}>
          No application email generated for this result.
        </p>
      </div>
    )
  }

  return (
    <div className="card p-5 space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--green-dim)' }}
          >
            <Send className="w-3.5 h-3.5" style={{ color: 'var(--green)' }} />
          </div>
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            Application Email
          </span>
        </div>
        <button
          onClick={handleCopyBody}
          className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-all duration-150"
          style={copiedBody
            ? { background: 'rgba(62,207,142,0.15)', border: '1px solid rgba(62,207,142,0.3)', color: 'var(--green)' }
            : { background: 'var(--surface-2)', border: '1px solid var(--border-2)', color: 'var(--text-muted)' }
          }
        >
          {copiedBody ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copiedBody ? 'Copied!' : 'Copy All'}
        </button>
      </div>

      {/* Subject line */}
      {email.subject_line && (
        <div
          className="flex items-start justify-between gap-3 px-3.5 py-2.5 rounded-lg"
          style={{ background: 'rgba(62,207,142,0.06)', border: '1px solid rgba(62,207,142,0.18)' }}
        >
          <div className="flex-1 min-w-0">
            <p className="section-title mb-0.5">Subject Line</p>
            <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
              {email.subject_line}
            </p>
          </div>
          <button
            onClick={handleCopySubject}
            title="Copy subject"
            className="shrink-0 p-1.5 rounded-lg transition-colors"
            style={copiedSubject
              ? { color: 'var(--green)', background: 'var(--green-dim)' }
              : { color: 'var(--text-faint)' }
            }
          >
            {copiedSubject ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      )}

      {/* Body */}
      <div
        className="rounded-xl p-4 max-h-72 overflow-y-auto"
        style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
      >
        {email.body.split('\n\n').map((para, i) => (
          <p key={i} className="text-sm leading-relaxed mb-3 last:mb-0" style={{ color: 'var(--text-muted)' }}>
            {para}
          </p>
        ))}
      </div>

      <p className="text-xs" style={{ color: 'var(--text-faint)' }}>
        💡 Tip: Personalise the opening with the hiring manager's name if known.
      </p>
    </div>
  )
}
