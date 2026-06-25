import { useState, useRef, useEffect, ReactNode } from 'react'
import { ChevronDown, Check, Cpu, Zap, Star } from 'lucide-react'
import type { ModelInfo } from '../types'

interface Props {
  models: ModelInfo[]
  selectedModel: string
  onChange: (id: string) => void
}

const MODEL_META: Record<string, { badge: string; color: string; icon: ReactNode }> = {
  glm: {
    badge: 'Recommended',
    color: 'text-zinc-800 bg-zinc-100 border-zinc-200/80',
    icon: <Star className="w-3 h-3" />,
  },
  qwen: {
    badge: 'Fast',
    color: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    icon: <Zap className="w-3 h-3" />,
  },
  deepseek: {
    badge: 'Precise',
    color: 'text-blue-700 bg-blue-50 border-blue-200',
    icon: <Cpu className="w-3 h-3" />,
  },
}

function getModelMeta(id: string) {
  return MODEL_META[id] ?? {
    badge: 'Standard',
    color: 'text-gray-500 bg-gray-50 border-gray-200',
    icon: <Cpu className="w-3 h-3" />,
  }
}

export default function ModelSelector({ models, selectedModel, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const selected = models.find((m) => m.id === selectedModel)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (models.length === 0) return null

  return (
    <div className="relative" ref={ref}>
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex items-center gap-2 w-full px-3.5 py-2.5 rounded-xl border border-gray-200 bg-white text-gray-700 text-sm font-medium hover:border-brand-400 hover:bg-gray-50 transition shadow-sm"
      >
        <Cpu className="w-4 h-4 text-brand-500 shrink-0" />
        <span className="flex-1 text-left">
          {selected ? selected.display_name : 'Select model'}
        </span>
        {selected && (
          <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-1.5 py-0.5 rounded-md border ${getModelMeta(selected.id).color}`}>
            {getModelMeta(selected.id).icon}
            {getModelMeta(selected.id).badge}
          </span>
        )}
        <ChevronDown className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-1.5 w-full min-w-[260px] bg-white border border-gray-200 rounded-2xl shadow-md overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-100">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">AI Model</p>
          </div>

          <ul className="py-1.5">
            {models.map((m) => {
              const meta = getModelMeta(m.id)
              const isSelected = m.id === selectedModel
              return (
                <li key={m.id}>
                  <button
                    type="button"
                    onClick={() => { onChange(m.id); setOpen(false) }}
                    className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${
                      isSelected ? 'bg-brand-50' : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                      isSelected ? 'bg-brand-100' : 'bg-gray-100'
                    }`}>
                      <Cpu className={`w-4 h-4 ${isSelected ? 'text-brand-600' : 'text-gray-400'}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium truncate ${isSelected ? 'text-brand-700' : 'text-gray-800'}`}>
                        {m.display_name}
                      </p>
                      {m.is_default && (
                        <p className="text-xs text-gray-400">Default</p>
                      )}
                    </div>
                    <span className={`inline-flex items-center gap-1 text-[11px] font-medium px-1.5 py-0.5 rounded-md border shrink-0 ${meta.color}`}>
                      {meta.icon}
                      {meta.badge}
                    </span>
                    {isSelected && <Check className="w-4 h-4 text-brand-600 shrink-0" />}
                  </button>
                </li>
              )
            })}
          </ul>

          <div className="px-4 py-2.5 border-t border-gray-100 bg-gray-50">
            <p className="text-xs text-gray-400">All models produce the same structured resume output.</p>
          </div>
        </div>
      )}
    </div>
  )
}
