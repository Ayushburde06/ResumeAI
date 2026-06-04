import { Briefcase } from 'lucide-react'

interface Props {
  value: string
  onChange: (v: string) => void
}

const PLACEHOLDER = `Paste the full job description here...

Example:
We are looking for a Senior Software Engineer to join our team...
Requirements:
• 5+ years of experience with Python and FastAPI
• Strong knowledge of cloud platforms (AWS, GCP, Azure)
...`

export default function JobDescInput({ value, onChange }: Props) {
  const wordCount = value.trim() ? value.trim().split(/\s+/).length : 0

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
          <Briefcase className="w-4 h-4 text-brand-500" />
          Job Description
        </div>
        <span className={`text-xs ${wordCount < 50 && wordCount > 0 ? 'text-amber-500' : 'text-gray-400'}`}>
          {wordCount} words{wordCount < 50 && wordCount > 0 ? ' — paste more for better results' : ''}
        </span>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={PLACEHOLDER}
        rows={10}
        className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm text-gray-800
                   placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-brand-400
                   focus:border-transparent resize-none transition-shadow"
      />
    </div>
  )
}
