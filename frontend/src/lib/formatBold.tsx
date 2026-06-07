import { Fragment } from 'react'

const BOLD_PATTERN = /\*\*(.+?)\*\*/g

export function FormatBoldText({ text }: { text: string }) {
  if (!text) return null

  const parts: (string | JSX.Element)[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null
  let key = 0

  BOLD_PATTERN.lastIndex = 0
  while ((match = BOLD_PATTERN.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<Fragment key={key++}>{text.slice(lastIndex, match.index)}</Fragment>)
    }
    parts.push(
      <strong key={key++} className="font-bold text-black">
        {match[1]}
      </strong>
    )
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    parts.push(<Fragment key={key++}>{text.slice(lastIndex)}</Fragment>)
  }

  return <>{parts}</>
}
