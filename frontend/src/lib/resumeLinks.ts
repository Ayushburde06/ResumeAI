export function toHref(raw: string): string {
  const value = raw.trim()
  if (!value) return ''
  if (/^(mailto:|tel:|https?:\/\/)/i.test(value)) return value
  return `https://${value.replace(/^\/\//, '')}`
}

export function linkLabel(raw: string, kind?: 'github' | 'linkedin' | 'website'): string {
  if (kind === 'github') return 'GitHub'
  if (kind === 'linkedin') return 'LinkedIn'
  if (kind === 'website') return 'Website'

  const lower = raw.toLowerCase()
  if (lower.includes('github.com')) return 'GitHub'
  if (lower.includes('linkedin.com')) return 'LinkedIn'
  if (lower.includes('gitlab.com')) return 'GitLab'
  return 'Link'
}

export type ContactItem =
  | { kind: 'text'; value: string }
  | { kind: 'email'; value: string; href: string }
  | { kind: 'link'; href: string; label: string }

export function buildContactItems(pi: {
  email?: string
  phone?: string
  location?: string
  linkedin?: string
  github?: string
  website?: string
}): ContactItem[] {
  const items: ContactItem[] = []
  if (pi.email) items.push({ kind: 'email', value: pi.email, href: `mailto:${pi.email}` })
  if (pi.phone) items.push({ kind: 'text', value: pi.phone })
  if (pi.location) items.push({ kind: 'text', value: pi.location })
  if (pi.linkedin) items.push({ kind: 'link', href: toHref(pi.linkedin), label: 'LinkedIn' })
  if (pi.github) items.push({ kind: 'link', href: toHref(pi.github), label: 'GitHub' })
  if (pi.website) items.push({ kind: 'link', href: toHref(pi.website), label: 'Website' })
  return items
}
