import { useState, useEffect, useRef, useCallback } from 'react'
import { Download, Eye, FileCode, Loader2, Pencil, Save } from 'lucide-react'
import type { TailoredResume } from '../types'
import { exportLatex, exportPdf } from '../lib/api'
import { buildContactItems, linkLabel, toHref } from '../lib/resumeLinks'
import { FormatBoldText } from '../lib/formatBold'
import ResumeEditor from './ResumeEditor'

type TemplateId = 'modern' | 'classic' | 'minimal'

const TEMPLATES: { id: TemplateId; name: string; description: string; preview: React.ReactNode }[] = [
  {
    id: 'modern',
    name: 'Harshibar (LaTeX)',
    description: 'Dense single-column · Industry standard SWE style',
    preview: (
      <div className="w-full h-14 rounded bg-white border border-gray-100 p-1.5 space-y-1">
        <div className="h-2 w-16 bg-black rounded-sm" />
        <div className="h-1 w-full bg-gray-200 rounded-sm" />
        <div className="h-px w-full bg-black mt-1" />
        <div className="space-y-0.5 mt-0.5">
          <div className="flex justify-between gap-1">
            <div className="h-1 w-10 bg-gray-800 rounded-sm" />
            <div className="h-1 w-6 bg-gray-300 rounded-sm" />
          </div>
          <div className="h-1 w-full bg-gray-100 rounded-sm" />
          <div className="h-1 w-4/5 bg-gray-100 rounded-sm" />
        </div>
      </div>
    ),
  },
  {
    id: 'classic',
    name: 'Classic',
    description: 'Traditional with centred header',
    preview: (
      <div className="w-full h-14 rounded bg-white border border-gray-100 p-1.5 space-y-1">
        <div className="flex justify-center"><div className="h-2 w-16 bg-gray-800 rounded" /></div>
        <div className="h-0.5 w-full bg-gray-800 rounded" />
        <div className="flex justify-center"><div className="h-1 w-20 bg-gray-300 rounded" /></div>
        <div className="space-y-0.5 mt-0.5">
          <div className="h-1 w-full bg-gray-100 rounded" />
          <div className="h-1 w-4/5 bg-gray-100 rounded" />
        </div>
      </div>
    ),
  },
  {
    id: 'minimal',
    name: 'Sidebar',
    description: 'Two-column with dark sidebar',
    preview: (
      <div className="w-full h-14 rounded bg-white border border-gray-100 overflow-hidden flex">
        <div className="w-8 bg-slate-800 p-1 space-y-1 shrink-0">
          <div className="h-1.5 w-full bg-slate-600 rounded" />
          <div className="h-1 w-full bg-slate-700 rounded" />
          <div className="h-1 w-4/5 bg-slate-700 rounded" />
        </div>
        <div className="flex-1 p-1.5 space-y-1">
          <div className="h-1 w-full bg-gray-200 rounded" />
          <div className="h-1 w-4/5 bg-gray-100 rounded" />
          <div className="h-1 w-full bg-gray-100 rounded" />
          <div className="h-1 w-3/4 bg-gray-100 rounded" />
        </div>
      </div>
    ),
  },
]

interface Props {
  resume: TailoredResume
  atsScore?: number
  onResumeChange: (resume: TailoredResume) => void
  onEditComplete?: () => void
  rescoring?: boolean
}

function ContactLine({ pi }: { pi: TailoredResume['personal_info'] }) {
  const items = buildContactItems(pi)
  if (items.length === 0) return null

  return (
    <p className="mt-1 text-[10px] text-neutral-600 leading-snug">
      {items.map((item, i) => (
        <span key={i}>
          {i > 0 && <span className="text-neutral-400 mx-1.5">|</span>}
          {item.kind === 'link' ? (
            <a href={item.href} target="_blank" rel="noopener noreferrer" className="resume-link">
              {item.label}
            </a>
          ) : item.kind === 'email' ? (
            <a href={item.href} className="resume-link">{item.value}</a>
          ) : (
            item.value
          )}
        </span>
      ))}
    </p>
  )
}

function EntryRow({ left, right }: { left: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="flex justify-between items-baseline gap-4 flex-wrap">
      <div className="min-w-0">{left}</div>
      {right && <div className="text-[10px] text-neutral-600 shrink-0">{right}</div>}
    </div>
  )
}

function ResumeSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-1.5 last:mb-0">
      <h4 className="resume-section-title">{title}</h4>
      {children}
    </section>
  )
}

function SkillRow({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <tr>
      <td className="font-bold text-black pr-4 whitespace-nowrap align-top py-[1px]">{label}:</td>
      <td className="align-top py-[1px]">
        {items.map((skill, i) => (
          <span key={i}>
            {i > 0 && ', '}
            <FormatBoldText text={skill} />
          </span>
        ))}
      </td>
    </tr>
  )
}

/* ── Professional Resume (Google SWE style) ── */
function ProfessionalResume({ resume }: { resume: TailoredResume }) {
  const pi = resume.personal_info

  return (
    <div className="resume-doc">
      <header className="mb-1 pb-1">
        <h2 className="text-[20px] font-bold text-black tracking-tight leading-none">{pi.name}</h2>
        <ContactLine pi={pi} />
      </header>

      {resume.summary && (
        <ResumeSection title="Summary">
          <p className="text-[10px] text-neutral-900 leading-snug">
            <FormatBoldText text={resume.summary} />
          </p>
        </ResumeSection>
      )}

      {resume.experience?.length > 0 && (
        <ResumeSection title="Experience">
          <div className="space-y-1.5">
            {resume.experience.map((exp, i) => (
              <div key={i}>
                <EntryRow
                  left={<span className="text-[11px] font-bold text-black">{exp.company}</span>}
                  right={exp.location}
                />
                <EntryRow
                  left={<span className="text-[10px] text-neutral-800">{exp.title}</span>}
                  right={
                    <>
                      {exp.start_date}
                      {exp.start_date && exp.end_date ? ' – ' : ''}
                      {exp.end_date}
                    </>
                  }
                />
                {exp.bullets?.length > 0 && (
                  <ul className="mt-0.5 pl-3 list-disc space-y-0.5">
                    {exp.bullets.map((b, j) => (
                      <li key={j} className="text-[10px] text-neutral-900 leading-snug marker:text-neutral-700">
                        <FormatBoldText text={b} />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </ResumeSection>
      )}

      {resume.education?.length > 0 && (
        <ResumeSection title="Education">
          <div className="space-y-1">
            {resume.education.map((edu, i) => (
              <div key={i}>
                <EntryRow
                  left={<span className="text-[11px] font-bold text-black">{edu.institution}</span>}
                  right={edu.location}
                />
                <EntryRow
                  left={
                    <span className="text-[10px] text-neutral-800">
                      {edu.degree}
                      {edu.gpa && <span className="text-neutral-600"> · GPA {edu.gpa}</span>}
                      {edu.honors && <span className="text-neutral-600"> · {edu.honors}</span>}
                    </span>
                  }
                  right={edu.graduation_year}
                />
              </div>
            ))}
          </div>
        </ResumeSection>
      )}

      {(resume.skills?.languages?.length > 0 ||
        resume.skills?.frameworks?.length > 0 ||
        resume.skills?.databases?.length > 0 ||
        resume.skills?.tools?.length > 0 ||
        resume.skills?.concepts?.length > 0) && (
        <ResumeSection title="Technical Skills">
          <table className="text-[10px] text-neutral-900 leading-snug w-full">
            <tbody>
              {resume.skills.languages?.length > 0 && (
                <SkillRow label="Languages" items={resume.skills.languages} />
              )}
              {resume.skills.frameworks?.length > 0 && (
                <SkillRow label="Frameworks & Libraries" items={resume.skills.frameworks} />
              )}
              {resume.skills.databases?.length > 0 && (
                <SkillRow label="Databases" items={resume.skills.databases} />
              )}
              {resume.skills.tools?.length > 0 && (
                <SkillRow label="Tools & Technologies" items={resume.skills.tools} />
              )}
              {resume.skills.concepts?.length > 0 && (
                <SkillRow label="Concepts" items={resume.skills.concepts} />
              )}
            </tbody>
          </table>
        </ResumeSection>
      )}

      {resume.projects?.length > 0 && (
        <ResumeSection title="Projects">
          <div className="space-y-1">
            {resume.projects.map((p, i) => (
              <div key={i} className="mb-1 last:mb-0">
                <div className="flex justify-between items-baseline gap-2 flex-wrap">
                  <span className="text-[11px] font-bold text-black">
                    {p.name}
                    {p.link && (
                      <>
                        {' '}
                        <span className="font-normal text-neutral-600">
                          —
                          <a
                            href={toHref(p.link)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="resume-link ml-1"
                          >
                            {linkLabel(p.link)}
                          </a>
                        </span>
                      </>
                    )}
                    {p.live_link && (
                      <>
                        {' '}
                        <span className="font-normal text-neutral-600">
                          |
                          <a
                            href={toHref(p.live_link)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="resume-link ml-1 text-brand-600 font-medium"
                          >
                            Live Demo
                          </a>
                        </span>
                      </>
                    )}
                  </span>
                </div>
                {p.tech_stack?.length > 0 && (
                  <div className="text-[9px] italic text-neutral-600 leading-none mb-0.5">
                    {p.tech_stack.join(', ')}
                  </div>
                )}
                {p.description && (
                  <ul className="mt-0.5 pl-3 list-disc space-y-0.5">
                    {p.description.split('\n').filter(l => l.trim()).map((line, li) => (
                      <li key={li} className="text-[10px] text-neutral-900 leading-snug marker:text-neutral-700">
                        <FormatBoldText text={line.trim()} />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </ResumeSection>
      )}

      {resume.certifications?.length > 0 && (
        <ResumeSection title="Certifications">
          <div className="space-y-0.5">
            {resume.certifications.map((c, i) => (
              <p key={i} className="text-[10px] text-neutral-900">
                <span className="font-semibold">{c.name}</span>
                {c.issuer && <span className="text-neutral-600"> · {c.issuer}</span>}
                {c.year && <span className="text-neutral-600"> · {c.year}</span>}
              </p>
            ))}
          </div>
        </ResumeSection>
      )}
    </div>
  )
}

/* ── Classic Resume: LaTeX style (serif, horizontal lines) ── */
function ClassicResume({ resume }: { resume: TailoredResume }) {
  const pi = resume.personal_info
  return (
    <div className="resume-classic-doc" style={{ fontSize: '10px', lineHeight: '1.4' }}>
      <header className="mb-3">
        <div className="flex justify-between items-end mb-1">
          <div className="text-left">
            {pi.email && <div><a href={`mailto:${pi.email}`} className="text-blue-800 underline">{pi.email}</a></div>}
            {pi.linkedin && <div>{pi.linkedin}</div>}
          </div>
          <div className="text-right">
            {pi.phone && <div>Mobile: {pi.phone}</div>}
            {pi.location && <div>{pi.location}</div>}
          </div>
        </div>
        <h2 className="text-[26px] font-normal text-center mt-2 mb-2 tracking-wide leading-none" style={{ fontVariant: 'small-caps' }}>
          {pi.name}
        </h2>
      </header>

      {resume.summary && (
        <section className="mb-2.5">
          <p className="text-justify">
            <FormatBoldText text={resume.summary} />
          </p>
        </section>
      )}

      {resume.education?.length > 0 && (
        <section className="mb-2.5">
          <h4 className="text-[11px] font-normal uppercase tracking-wider border-b border-black pb-[1px] mb-1.5" style={{ fontVariant: 'small-caps' }}>
            Education
          </h4>
          <div className="space-y-1.5">
            {resume.education.map((edu, i) => (
              <div key={i}>
                <div className="flex justify-between items-baseline">
                  <span className="font-bold">• {edu.institution}</span>
                  <span>{edu.location}</span>
                </div>
                <div className="flex justify-between items-baseline pl-3 italic text-[9.5px]">
                  <span>{edu.degree}{edu.gpa && ` · GPA: ${edu.gpa}`}</span>
                  <span>{edu.graduation_year}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {resume.experience?.length > 0 && (
        <section className="mb-2.5">
          <h4 className="text-[11px] font-normal uppercase tracking-wider border-b border-black pb-[1px] mb-1.5" style={{ fontVariant: 'small-caps' }}>
            Work Experience
          </h4>
          <div className="space-y-2">
            {resume.experience.map((exp, i) => (
              <div key={i}>
                <div className="flex justify-between items-baseline">
                  <span className="font-bold">• {exp.company}</span>
                  <span>{exp.location}</span>
                </div>
                <div className="flex justify-between items-baseline pl-3 italic text-[9.5px]">
                  <span>{exp.title}</span>
                  <span>{exp.start_date}{exp.start_date && exp.end_date ? ' – ' : ''}{exp.end_date}</span>
                </div>
                {exp.bullets?.length > 0 && (
                  <ul className="mt-0.5 pl-6 list-none space-y-0.5">
                    {exp.bullets.map((b, j) => (
                      <li key={j} className="relative">
                        <span className="absolute -left-3 top-[0.5px] text-[7px]">○</span>
                        <span className="text-[9.5px] text-justify block">
                          <FormatBoldText text={b} />
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {resume.projects?.length > 0 && (
        <section className="mb-2.5">
          <h4 className="text-[11px] font-normal uppercase tracking-wider border-b border-black pb-[1px] mb-1.5" style={{ fontVariant: 'small-caps' }}>
            Projects
          </h4>
          <div className="space-y-2">
            {resume.projects.map((p, i) => (
              <div key={i}>
                <div className="font-bold">
                  {p.name}:
                  {p.link && (
                    <span className="font-normal text-neutral-600 ml-1">
                      —
                      <a
                        href={toHref(p.link)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-1 text-black underline"
                      >
                        {linkLabel(p.link)}
                      </a>
                    </span>
                  )}
                </div>
                {p.description && (
                  <ul className="mt-0.5 pl-3 list-disc space-y-0.5">
                    {p.description.split('\n').filter(l => l.trim()).map((line, li) => (
                      <li key={li} className="text-[9.5px] leading-snug">
                        <FormatBoldText text={line.trim()} />
                      </li>
                    ))}
                  </ul>
                )}
                {p.tech_stack?.length > 0 && (
                  <ul className="mt-0.5 pl-3 list-disc space-y-0.5">
                    <li className="text-[9.5px] leading-snug">
                      Built with <span className="font-bold">{p.tech_stack.join(', ')}</span>.
                    </li>
                  </ul>
                )}
                {p.live_link && (
                  <ul className="mt-0.5 pl-3 list-disc space-y-0.5">
                    <li className="text-[9.5px] leading-snug">
                      <a 
                        href={toHref(p.live_link)} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="inline-block text-[#00c5cc] border border-[#00c5cc] px-1 font-bold no-underline"
                      >
                        Live Demo
                      </a>
                    </li>
                  </ul>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {(resume.skills?.languages?.length > 0 || resume.skills?.frameworks?.length > 0 ||
        resume.skills?.databases?.length > 0 || resume.skills?.tools?.length > 0 || resume.skills?.concepts?.length > 0) && (
        <section className="mb-2.5">
          <h4 className="text-[11px] font-normal uppercase tracking-wider border-b border-black pb-[1px] mb-1.5" style={{ fontVariant: 'small-caps' }}>
            Technical Skills
          </h4>
          <ul className="pl-3 space-y-0.5 text-[9.5px] list-disc">
            {resume.skills.languages?.length > 0 && (
              <li>
                <span className="font-bold">Languages:</span>{' '}
                {resume.skills.languages.map((s, idx) => <span key={idx}>{idx > 0 && ', '}<FormatBoldText text={s} /></span>)}
              </li>
            )}
            {resume.skills.frameworks?.length > 0 && (
              <li>
                <span className="font-bold">Frameworks &amp; Libraries:</span>{' '}
                {resume.skills.frameworks.map((s, idx) => <span key={idx}>{idx > 0 && ', '}<FormatBoldText text={s} /></span>)}
              </li>
            )}
            {resume.skills.databases?.length > 0 && (
              <li>
                <span className="font-bold">Databases:</span>{' '}
                {resume.skills.databases.map((s, idx) => <span key={idx}>{idx > 0 && ', '}<FormatBoldText text={s} /></span>)}
              </li>
            )}
            {resume.skills.tools?.length > 0 && (
              <li>
                <span className="font-bold">Tools &amp; Technologies:</span>{' '}
                {resume.skills.tools.map((s, idx) => <span key={idx}>{idx > 0 && ', '}<FormatBoldText text={s} /></span>)}
              </li>
            )}
            {resume.skills.concepts?.length > 0 && (
              <li>
                <span className="font-bold">Concepts:</span>{' '}
                {resume.skills.concepts.map((s, idx) => <span key={idx}>{idx > 0 && ', '}<FormatBoldText text={s} /></span>)}
              </li>
            )}
          </ul>
        </section>
      )}

      {resume.certifications?.length > 0 && (
        <section>
          <h4 className="text-[11px] font-normal uppercase tracking-wider border-b border-black pb-[1px] mb-1.5" style={{ fontVariant: 'small-caps' }}>
            Extracurricular Activities & Certifications
          </h4>
          <ul className="pl-3 list-disc space-y-0.5 text-[9.5px]">
            {resume.certifications.map((c, i) => (
              <li key={i}>
                <span className="font-bold">{c.name}</span>
                {c.issuer && <span> · {c.issuer}</span>}
                {c.year && <span> ({c.year})</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

/* ── Sidebar Resume: dark left panel + main content ── */
function SidebarResume({ resume }: { resume: TailoredResume }) {
  const pi = resume.personal_info
  const allSkills = [
    ...(resume.skills?.languages ?? []),
    ...(resume.skills?.frameworks ?? []),
    ...(resume.skills?.databases ?? []),
    ...(resume.skills?.tools ?? []),
    ...(resume.skills?.concepts ?? []),
  ]
  return (
    <div className="resume-doc flex w-full" style={{ minHeight: '100%' }}>
      {/* Dark sidebar */}
      <aside className="w-32 shrink-0 bg-slate-800 text-white px-2.5 py-4 space-y-3.5">
        <div>
          <p className="text-[9.5px] font-bold uppercase tracking-widest text-slate-300 mb-1">Contact</p>
          <div className="text-[8.5px] text-slate-300 leading-relaxed space-y-0.5">
            {pi.email && <p className="break-all">{pi.email}</p>}
            {pi.phone && <p>{pi.phone}</p>}
            {pi.location && <p>{pi.location}</p>}
          </div>
        </div>
        {allSkills.length > 0 && (
          <div>
            <p className="text-[9.5px] font-bold uppercase tracking-widest text-slate-300 mb-1">Skills</p>
            <div className="space-y-0.5">
              {allSkills.slice(0, 18).map((s, i) => (
                <p key={i} className="text-[8.5px] text-slate-200 leading-snug">
                  <FormatBoldText text={s} />
                </p>
              ))}
            </div>
          </div>
        )}
        {resume.certifications?.length > 0 && (
          <div>
            <p className="text-[9.5px] font-bold uppercase tracking-widest text-slate-300 mb-1">Certs</p>
            {resume.certifications.map((c, i) => (
              <p key={i} className="text-[8.5px] text-slate-200 leading-snug">{c.name}</p>
            ))}
          </div>
        )}
        {resume.education?.length > 0 && (
          <div>
            <p className="text-[9.5px] font-bold uppercase tracking-widest text-slate-300 mb-1">Education</p>
            {resume.education.map((edu, i) => (
              <div key={i} className="mb-1">
                <p className="text-[8.5px] text-slate-200 font-semibold leading-snug">{edu.institution}</p>
                <p className="text-[8px] text-slate-400">{edu.graduation_year}</p>
              </div>
            ))}
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className="flex-1 px-4 py-4">
        <h2 className="text-[16px] font-bold text-gray-900">{pi.name}</h2>
        {resume.summary && (
          <p className="text-[9.5px] text-neutral-700 leading-snug mt-1 mb-2.5">
            <FormatBoldText text={resume.summary} />
          </p>
        )}

        {resume.experience?.length > 0 && (
          <section className="mb-2.5">
            <h4 className="text-[9.5px] font-bold uppercase tracking-widest text-slate-700 border-b border-slate-300 pb-0.5 mb-1">
              Experience
            </h4>
            <div className="space-y-2">
              {resume.experience.map((exp, i) => (
                <div key={i}>
                  <div className="flex justify-between items-baseline">
                    <span className="text-[10.5px] font-bold text-gray-900">{exp.title}</span>
                    <span className="text-[8.5px] text-neutral-400">
                      {exp.start_date}{exp.start_date && exp.end_date ? ' – ' : ''}{exp.end_date}
                    </span>
                  </div>
                  <div className="text-[9px] text-neutral-500">{exp.company}</div>
                  {exp.bullets?.length > 0 && (
                    <ul className="mt-0.5 pl-2.5 list-disc space-y-0.5">
                      {exp.bullets.map((b, j) => (
                        <li key={j} className="text-[9.5px] text-neutral-800 leading-snug">
                          <FormatBoldText text={b} />
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {resume.projects?.length > 0 && (
          <section>
            <h4 className="text-[9.5px] font-bold uppercase tracking-widest text-slate-700 border-b border-slate-300 pb-0.5 mb-1">
              Projects
            </h4>
            <div className="space-y-1">
              {resume.projects.map((p, i) => (
                <div key={i}>
                  <p className="text-[9.5px] font-bold text-gray-900">{p.name}</p>
                  {p.description && (
                    <ul className="mt-0.5 pl-2.5 list-disc space-y-0.5">
                      {p.description.split('\n').filter(l => l.trim()).map((line, li) => (
                        <li key={li} className="text-[9px] text-neutral-700 leading-snug">
                          <FormatBoldText text={line.trim()} />
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

const getScore = (n: number) => ({
  color: n >= 80 ? '#10b981' : n >= 60 ? '#f59e0b' : '#ef4444',
  label: n >= 80 ? 'Strong match' : n >= 60 ? 'Good match' : 'Needs work',
  bg: n >= 80 ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : n >= 60 ? 'bg-amber-50 text-amber-700 border-amber-100' : 'bg-red-50 text-red-700 border-red-100'
})

const EDIT_STORAGE_KEY = 'resume_unsaved_edits'

export default function ResumePreview({ resume, atsScore, onResumeChange, onEditComplete, rescoring }: Props) {
  const [template, setTemplate] = useState<TemplateId>('modern')
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [exportingTex, setExportingTex] = useState(false)
  const [editing, setEditing] = useState(false)
  const [hasUnsavedEdits, setHasUnsavedEdits] = useState(false)

  const containerRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  // Restore any unsaved edits from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(EDIT_STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved) as typeof resume
        onResumeChange(parsed)
        setHasUnsavedEdits(true)
      }
    } catch {
      localStorage.removeItem(EDIT_STORAGE_KEY)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!containerRef.current) return
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const width = entry.contentRect.width
        const targetWidth = 595
        if (width < targetWidth) {
          setScale(width / targetWidth)
        } else {
          setScale(1)
        }
      }
    })
    resizeObserver.observe(containerRef.current)
    return () => resizeObserver.disconnect()
  }, [])

  const handleResumeChange = useCallback((updated: TailoredResume) => {
    onResumeChange(updated)
    try {
      localStorage.setItem(EDIT_STORAGE_KEY, JSON.stringify(updated))
      setHasUnsavedEdits(true)
    } catch {
      // storage quota exceeded — silently ignore
    }
  }, [onResumeChange])

  function handleToggleEdit() {
    if (editing) {
      onEditComplete?.()
      setEditing(false)
    } else {
      setEditing(true)
    }
  }

  function handleSaveEdits() {
    // Persist is already done on every change; this just clears the "unsaved" badge
    localStorage.removeItem(EDIT_STORAGE_KEY)
    setHasUnsavedEdits(false)
    onEditComplete?.()
    setEditing(false)
  }

  async function handleExportTex() {
    setExportingTex(true)
    setExportError(null)
    try {
      await exportLatex(resume)
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'LaTeX export failed.')
    } finally {
      setExportingTex(false)
    }
  }

  async function handleExport() {
    setExporting(true)
    setExportError(null)
    try {
      await exportPdf(resume, template)
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'PDF export failed.')
    } finally {
      setExporting(false)
    }
  }

  const templateLabel = TEMPLATES.find((t) => t.id === template)?.name ?? 'Professional'
  const scoreMeta = atsScore !== undefined ? getScore(atsScore) : null

  return (
    <div className="bg-white rounded-lg border border-zinc-200 p-6 space-y-5 animate-slide-up flex flex-col flex-1 min-h-0">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-zinc-100 pb-4 shrink-0">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-zinc-900 text-base">Tailored Resume</h3>
            {scoreMeta && (
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${scoreMeta.bg} border`} style={{ color: scoreMeta.color, borderColor: `${scoreMeta.color}20` }}>
                {atsScore}% ATS
              </span>
            )}
          </div>
          <p className="text-xs text-zinc-500 mt-1">
            {editing ? 'Edit any section, then click Done to update your preview' : 'AI-optimised for this role'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto shrink-0">
          {hasUnsavedEdits && !editing && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-amber-600 bg-amber-50 border border-amber-200 rounded-full px-2.5 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
              Unsaved edits
            </span>
          )}
          {editing && (
            <button
              onClick={handleSaveEdits}
              className="btn-primary text-sm py-2 bg-emerald-600 hover:bg-emerald-700 border-emerald-600"
            >
              <Save className="w-4 h-4" />
              Save Edits
            </button>
          )}
          <button
            onClick={handleToggleEdit}
            disabled={rescoring}
            className={editing ? 'btn-secondary text-sm py-2' : 'btn-secondary text-sm py-2'}
          >
            {rescoring ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : editing ? (
              <Eye className="w-4 h-4" />
            ) : (
              <Pencil className="w-4 h-4" />
            )}
            {rescoring ? 'Updating…' : editing ? 'Cancel' : 'Edit Resume'}
          </button>
          <button onClick={handleExport} disabled={exporting || editing} className="btn-primary text-sm py-2">
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            {exporting ? 'Generating…' : 'Download PDF'}
          </button>
          <button
            onClick={handleExportTex}
            disabled={exportingTex || editing}
            title="Download LaTeX (.tex) — open in Overleaf for perfect typesetting"
            className="btn-secondary text-sm py-2"
          >
            {exportingTex ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileCode className="w-4 h-4" />}
            {exportingTex ? 'Building…' : '.tex'}
          </button>
        </div>
      </div>

      {exportError && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
          {exportError}
        </p>
      )}

      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2.5">Choose Layout</p>
        <div className="grid grid-cols-3 gap-2 sm:gap-3">
          {TEMPLATES.map((t) => (
            <button
              key={t.id}
              onClick={() => setTemplate(t.id)}
              className={`rounded-lg border p-1.5 sm:p-2.5 text-left transition-all focus:outline-none ${
                template === t.id
                  ? 'border-brand bg-brand-50 shadow-sm'
                  : 'border-zinc-200 hover:border-zinc-300 bg-white'
              }`}
            >
              {t.preview}
              <p className={`mt-2 text-xs font-semibold ${template === t.id ? 'text-brand' : 'text-zinc-700'}`}>
                {t.name}
              </p>
              <p className="text-[10px] text-gray-400 mt-0.5 leading-tight">{t.description}</p>
            </button>
          ))}
        </div>
      </div>

      {editing ? (
        <div className="rounded-xl border border-brand-100 bg-brand-50/30 p-4 sm:p-5">
          <ResumeEditor resume={resume} onChange={handleResumeChange} />
        </div>
      ) : (
        <div>
          <div
            ref={containerRef}
            className="rounded-lg border border-zinc-200 bg-zinc-50 p-4 relative overflow-hidden"
            style={{ height: `${842 * scale + 32}px` }}
          >
            <div
              className="bg-white shadow-sm border border-zinc-200 rounded-sm flex flex-col justify-start relative overflow-y-auto select-none absolute left-1/2"
              style={{
                top: '16px',
                width: '595px',
                height: '842px',
                transform: `translateX(-50%) scale(${scale})`,
                transformOrigin: 'top center',
              }}
            >
              {template === 'modern' && <div className="px-7 py-5 flex-1 flex flex-col justify-start"><ProfessionalResume resume={resume} /></div>}
              {template === 'classic' && <div className="px-7 py-5 flex-1 flex flex-col justify-start"><ClassicResume resume={resume} /></div>}
              {template === 'minimal' && <div className="flex-1 flex h-[842px]"><SidebarResume resume={resume} /></div>}
            </div>
          </div>
          <p className="text-center text-[10px] text-neutral-400 mt-2">A4 preview · {templateLabel} layout</p>
        </div>
      )}
    </div>
  )
}
