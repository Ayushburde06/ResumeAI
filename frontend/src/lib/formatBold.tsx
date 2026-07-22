import { Fragment } from 'react'

// ── Patterns (mirror backend text_formatting.py logic) ─────────────────────

const BOLD_PATTERN = /\*\*(.+?)\*\*/g

/** Quantifiable impact metrics: 45%, $500K, 10M+, 2.5x, 99.9% uptime, etc. */
const METRIC_PATTERN =
  /\b(\$?\d+(?:\.\d+)?(?:%|k|M|B|x|\+)?(?:\s*(?:users|events|requests|ms|seconds|minutes|hours|days|percent|latency\s+reduction|uptime|downloads|revenue|queries|rps|QPS|API\s+calls?|page\s+views?|transactions?|deployments?))?)\b/gi

/** Fallback static core tech keywords when no JD/skills list is provided. */
const CORE_TECH_PATTERN =
  /\b(Python|FastAPI|React|Next\.js|Node\.js|TypeScript|JavaScript|PostgreSQL|Redis|Docker|Kubernetes|AWS|GCP|Azure|Microservices|RESTful\s+APIs?|REST\s+APIs?|GraphQL|CI\/CD|Django|Flask|Spring\s+Boot|Java|Go|Golang|Rust|C\+\+|PyTorch|TensorFlow|MongoDB|Kafka|Elasticsearch|TailwindCSS|Redux|SQL|NoSQL|gRPC|Celery|Nginx|Terraform|Ansible|Prometheus|Grafana|OpenAI|LangChain|Pinecone|Supabase|Firebase|Vercel|HuggingFace|scikit-learn|Pandas|NumPy)\b/gi

const ACTION_VERBS = new Set([
  'built','designed','developed','created','implemented','optimized',
  'integrated','automated','reduced','improved','delivered','engineered',
  'refactored','deployed','led','managed','wrote','configured',
  'architected','migrated','containerized','maintained','debugged',
  'tested','reviewed','launched','shipped','published',
])

const MAX_BOLDS = 3

function isActionVerb(s: string): boolean {
  return ACTION_VERBS.has(s.trim().toLowerCase().replace(/[.,;:]$/, ''))
}

/**
 * Auto-insert **bold** markers into a bullet string using the same
 * 3-layer priority order as the backend engine:
 *   1. JD keywords  2. Metrics  3. Core tech stack
 * Respects MAX_BOLDS limit and skips action verbs.
 * Returns original text unchanged if it already contains ** markers.
 */
function autoInsertBoldMarkers(
  text: string,
  jdKeywords?: string[],
  resumeSkills?: string[],
): string {
  if (!text || text.includes('**')) return text

  let result = text
  let count = 0

  // ── Layer 1: JD keywords ────────────────────────────────────────────────
  if (jdKeywords?.length && count < MAX_BOLDS) {
    const escaped = [...jdKeywords]
      .filter(Boolean)
      .sort((a, b) => b.length - a.length)
      .map(k => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    if (escaped.length) {
      const jdPat = new RegExp(`\\b(${escaped.join('|')})\\b`, 'gi')
      result = result.replace(jdPat, (match) => {
        if (count >= MAX_BOLDS || isActionVerb(match)) return match
        count++
        return `**${match}**`
      })
    }
  }

  // ── Layer 2: Metrics ────────────────────────────────────────────────────
  if (count < MAX_BOLDS) {
    METRIC_PATTERN.lastIndex = 0
    result = result.replace(METRIC_PATTERN, (match) => {
      if (count >= MAX_BOLDS) return match
      // Skip standalone small numbers / years
      if (/^\d+$/.test(match) && (match.length === 4 || parseInt(match, 10) < 10)) return match
      count++
      return `**${match}**`
    })
  }

  // ── Layer 3: Tech stack ──────────────────────────────────────────────────
  if (count < MAX_BOLDS) {
    let techPat: RegExp

    if (resumeSkills?.length) {
      const escaped = [...resumeSkills]
        .filter(s => s && s.length > 1)
        .sort((a, b) => b.length - a.length)
        .map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      techPat = new RegExp(`\\b(${escaped.join('|')})\\b`, 'gi')
    } else {
      CORE_TECH_PATTERN.lastIndex = 0
      techPat = CORE_TECH_PATTERN
    }

    result = result.replace(techPat, (match) => {
      if (count >= MAX_BOLDS || isActionVerb(match)) return match
      count++
      return `**${match}**`
    })
  }

  return result
}

// ── React component ────────────────────────────────────────────────────────

interface FormatBoldTextProps {
  text: string
  /** JD keywords to highlight with highest priority */
  jdKeywords?: string[]
  /** Candidate's own skill list for Layer 3 tech bolding */
  resumeSkills?: string[]
  /** If true, auto-insert bold markers even when none exist (default: true) */
  autoHighlight?: boolean
}

export function FormatBoldText({
  text,
  jdKeywords,
  resumeSkills,
  autoHighlight = true,
}: FormatBoldTextProps) {
  if (!text) return null

  const processedText = autoHighlight
    ? autoInsertBoldMarkers(text, jdKeywords, resumeSkills)
    : text

  const parts: (string | JSX.Element)[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0

  BOLD_PATTERN.lastIndex = 0
  while ((match = BOLD_PATTERN.exec(processedText)) !== null) {
    if (match.index > lastIndex) {
      parts.push(
        <Fragment key={key++}>{processedText.slice(lastIndex, match.index)}</Fragment>,
      )
    }
    parts.push(
      <strong key={key++} className="font-bold text-black">
        {match[1]}
      </strong>,
    )
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < processedText.length) {
    parts.push(
      <Fragment key={key++}>{processedText.slice(lastIndex)}</Fragment>,
    )
  }

  return <>{parts}</>
}
