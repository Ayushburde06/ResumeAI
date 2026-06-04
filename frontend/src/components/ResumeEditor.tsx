import { Plus, Trash2 } from 'lucide-react'
import type {
  Certification,
  EducationItem,
  ExperienceItem,
  PersonalInfo,
  Project,
  TailoredResume,
} from '../types'

interface Props {
  resume: TailoredResume
  onChange: (resume: TailoredResume) => void
}

const inputClass =
  'w-full px-3 py-2 rounded-lg border border-gray-200 text-sm text-gray-800 ' +
  'placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent'

const labelClass = 'block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1'

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={inputClass}
      />
    </div>
  )
}

function SkillsField({
  label,
  items,
  onChange,
}: {
  label: string
  items: string[]
  onChange: (items: string[]) => void
}) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      <input
        type="text"
        value={items.join(', ')}
        onChange={(e) =>
          onChange(
            e.target.value
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean)
          )
        }
        placeholder="Comma-separated"
        className={inputClass}
      />
    </div>
  )
}

function updatePersonalInfo(resume: TailoredResume, patch: Partial<PersonalInfo>): TailoredResume {
  return { ...resume, personal_info: { ...resume.personal_info, ...patch } }
}

function updateExperience(resume: TailoredResume, index: number, patch: Partial<ExperienceItem>): TailoredResume {
  const experience = resume.experience.map((exp, i) => (i === index ? { ...exp, ...patch } : exp))
  return { ...resume, experience }
}

function updateEducation(resume: TailoredResume, index: number, patch: Partial<EducationItem>): TailoredResume {
  const education = resume.education.map((edu, i) => (i === index ? { ...edu, ...patch } : edu))
  return { ...resume, education }
}

function updateProject(resume: TailoredResume, index: number, patch: Partial<Project>): TailoredResume {
  const projects = resume.projects.map((p, i) => (i === index ? { ...p, ...patch } : p))
  return { ...resume, projects }
}

function updateCertification(resume: TailoredResume, index: number, patch: Partial<Certification>): TailoredResume {
  const certifications = resume.certifications.map((c, i) => (i === index ? { ...c, ...patch } : c))
  return { ...resume, certifications }
}

export default function ResumeEditor({ resume, onChange }: Props) {
  const pi = resume.personal_info

  return (
    <div className="space-y-6 max-h-[620px] overflow-y-auto pr-1">
      <section className="space-y-3">
        <h4 className="text-sm font-semibold text-gray-900">Personal Info</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label="Name" value={pi.name} onChange={(v) => onChange(updatePersonalInfo(resume, { name: v }))} />
          <Field label="Email" value={pi.email} onChange={(v) => onChange(updatePersonalInfo(resume, { email: v }))} />
          <Field label="Phone" value={pi.phone} onChange={(v) => onChange(updatePersonalInfo(resume, { phone: v }))} />
          <Field
            label="Location"
            value={pi.location}
            onChange={(v) => onChange(updatePersonalInfo(resume, { location: v }))}
          />
          <Field
            label="LinkedIn"
            value={pi.linkedin}
            onChange={(v) => onChange(updatePersonalInfo(resume, { linkedin: v }))}
          />
          <Field
            label="GitHub"
            value={pi.github}
            onChange={(v) => onChange(updatePersonalInfo(resume, { github: v }))}
          />
          <Field
            label="Website"
            value={pi.website}
            onChange={(v) => onChange(updatePersonalInfo(resume, { website: v }))}
          />
        </div>
      </section>

      <section className="space-y-2">
        <label className={labelClass}>Summary</label>
        <textarea
          value={resume.summary}
          onChange={(e) => onChange({ ...resume, summary: e.target.value })}
          rows={4}
          placeholder="Professional summary..."
          className={`${inputClass} resize-none`}
        />
        <p className="text-[11px] text-gray-400">Use **double asterisks** around text for bold emphasis in the PDF.</p>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-900">Experience</h4>
          <button
            type="button"
            onClick={() =>
              onChange({
                ...resume,
                experience: [
                  ...resume.experience,
                  {
                    title: '',
                    company: '',
                    location: '',
                    start_date: '',
                    end_date: '',
                    bullets: [''],
                  },
                ],
              })
            }
            className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
          >
            <Plus className="w-3.5 h-3.5" />
            Add role
          </button>
        </div>
        {resume.experience.map((exp, i) => (
          <div key={i} className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 space-y-3">
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-semibold text-gray-400">Role {i + 1}</span>
              {resume.experience.length > 1 && (
                <button
                  type="button"
                  onClick={() =>
                    onChange({ ...resume, experience: resume.experience.filter((_, idx) => idx !== i) })
                  }
                  className="text-gray-400 hover:text-red-500 transition-colors"
                  aria-label="Remove role"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field
                label="Company"
                value={exp.company}
                onChange={(v) => onChange(updateExperience(resume, i, { company: v }))}
              />
              <Field
                label="Title"
                value={exp.title}
                onChange={(v) => onChange(updateExperience(resume, i, { title: v }))}
              />
              <Field
                label="Location"
                value={exp.location}
                onChange={(v) => onChange(updateExperience(resume, i, { location: v }))}
              />
              <Field
                label="Start date"
                value={exp.start_date}
                onChange={(v) => onChange(updateExperience(resume, i, { start_date: v }))}
                placeholder="Jan 2020"
              />
              <Field
                label="End date"
                value={exp.end_date}
                onChange={(v) => onChange(updateExperience(resume, i, { end_date: v }))}
                placeholder="Present"
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className={labelClass}>Bullets</label>
                <button
                  type="button"
                  onClick={() =>
                    onChange(updateExperience(resume, i, { bullets: [...exp.bullets, ''] }))
                  }
                  className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add bullet
                </button>
              </div>
              {exp.bullets.map((bullet, j) => (
                <div key={j} className="flex gap-2">
                  <textarea
                    value={bullet}
                    onChange={(e) => {
                      const bullets = [...exp.bullets]
                      bullets[j] = e.target.value
                      onChange(updateExperience(resume, i, { bullets }))
                    }}
                    rows={2}
                    placeholder="Achievement or responsibility..."
                    className={`${inputClass} flex-1 resize-none`}
                  />
                  {exp.bullets.length > 1 && (
                    <button
                      type="button"
                      onClick={() =>
                        onChange(
                          updateExperience(resume, i, {
                            bullets: exp.bullets.filter((_, idx) => idx !== j),
                          })
                        )
                      }
                      className="self-start mt-2 text-gray-400 hover:text-red-500"
                      aria-label="Remove bullet"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-900">Education</h4>
          <button
            type="button"
            onClick={() =>
              onChange({
                ...resume,
                education: [
                  ...resume.education,
                  {
                    degree: '',
                    institution: '',
                    location: '',
                    graduation_year: '',
                    gpa: '',
                    honors: '',
                  },
                ],
              })
            }
            className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
          >
            <Plus className="w-3.5 h-3.5" />
            Add education
          </button>
        </div>
        {resume.education.map((edu, i) => (
          <div key={i} className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 space-y-3">
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-semibold text-gray-400">Entry {i + 1}</span>
              {resume.education.length > 1 && (
                <button
                  type="button"
                  onClick={() =>
                    onChange({ ...resume, education: resume.education.filter((_, idx) => idx !== i) })
                  }
                  className="text-gray-400 hover:text-red-500"
                  aria-label="Remove education"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field
                label="Institution"
                value={edu.institution}
                onChange={(v) => onChange(updateEducation(resume, i, { institution: v }))}
              />
              <Field
                label="Degree"
                value={edu.degree}
                onChange={(v) => onChange(updateEducation(resume, i, { degree: v }))}
              />
              <Field
                label="Location"
                value={edu.location}
                onChange={(v) => onChange(updateEducation(resume, i, { location: v }))}
              />
              <Field
                label="Graduation year"
                value={edu.graduation_year}
                onChange={(v) => onChange(updateEducation(resume, i, { graduation_year: v }))}
              />
              <Field label="GPA" value={edu.gpa} onChange={(v) => onChange(updateEducation(resume, i, { gpa: v }))} />
              <Field
                label="Honors"
                value={edu.honors}
                onChange={(v) => onChange(updateEducation(resume, i, { honors: v }))}
              />
            </div>
          </div>
        ))}
      </section>

      <section className="space-y-3">
        <h4 className="text-sm font-semibold text-gray-900">Skills</h4>
        <SkillsField
          label="Languages"
          items={resume.skills.languages ?? []}
          onChange={(languages) => onChange({ ...resume, skills: { ...resume.skills, languages } })}
        />
        <SkillsField
          label="Frameworks & Libraries"
          items={resume.skills.frameworks ?? []}
          onChange={(frameworks) => onChange({ ...resume, skills: { ...resume.skills, frameworks } })}
        />
        <SkillsField
          label="Databases"
          items={resume.skills.databases ?? []}
          onChange={(databases) => onChange({ ...resume, skills: { ...resume.skills, databases } })}
        />
        <SkillsField
          label="Tools & Technologies"
          items={resume.skills.tools ?? []}
          onChange={(tools) => onChange({ ...resume, skills: { ...resume.skills, tools } })}
        />
        <SkillsField
          label="Concepts"
          items={resume.skills.concepts ?? []}
          onChange={(concepts) => onChange({ ...resume, skills: { ...resume.skills, concepts } })}
        />
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-900">Projects</h4>
          <button
            type="button"
            onClick={() =>
              onChange({
                ...resume,
                projects: [...resume.projects, { name: '', description: '', tech_stack: [], link: '', live_link: '' }],
              })
            }
            className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
          >
            <Plus className="w-3.5 h-3.5" />
            Add project
          </button>
        </div>
        {resume.projects.map((project, i) => (
          <div key={i} className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 space-y-3">
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-semibold text-gray-400">Project {i + 1}</span>
              <button
                type="button"
                onClick={() =>
                  onChange({ ...resume, projects: resume.projects.filter((_, idx) => idx !== i) })
                }
                className="text-gray-400 hover:text-red-500"
                aria-label="Remove project"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field
                label="Name"
                value={project.name}
                onChange={(v) => onChange(updateProject(resume, i, { name: v }))}
              />
              <Field
                label="GitHub Link"
                value={project.link}
                onChange={(v) => onChange(updateProject(resume, i, { link: v }))}
              />
              <Field
                label="Live Demo Link"
                value={project.live_link || ''}
                onChange={(v) => onChange(updateProject(resume, i, { live_link: v }))}
              />
            </div>
            <div>
              <label className={labelClass}>Description</label>
              <textarea
                value={project.description}
                onChange={(e) => onChange(updateProject(resume, i, { description: e.target.value }))}
                rows={2}
                className={`${inputClass} resize-none`}
              />
            </div>
            <SkillsField
              label="Tech stack"
              items={project.tech_stack}
              onChange={(tech_stack) => onChange(updateProject(resume, i, { tech_stack }))}
            />
          </div>
        ))}
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-900">Certifications</h4>
          <button
            type="button"
            onClick={() =>
              onChange({
                ...resume,
                certifications: [...resume.certifications, { name: '', issuer: '', year: '' }],
              })
            }
            className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
          >
            <Plus className="w-3.5 h-3.5" />
            Add certification
          </button>
        </div>
        {resume.certifications.map((cert, i) => (
          <div key={i} className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 space-y-3">
            <div className="flex items-start justify-between gap-2">
              <span className="text-xs font-semibold text-gray-400">Certification {i + 1}</span>
              <button
                type="button"
                onClick={() =>
                  onChange({
                    ...resume,
                    certifications: resume.certifications.filter((_, idx) => idx !== i),
                  })
                }
                className="text-gray-400 hover:text-red-500"
                aria-label="Remove certification"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Field
                label="Name"
                value={cert.name}
                onChange={(v) => onChange(updateCertification(resume, i, { name: v }))}
              />
              <Field
                label="Issuer"
                value={cert.issuer}
                onChange={(v) => onChange(updateCertification(resume, i, { issuer: v }))}
              />
              <Field
                label="Year"
                value={cert.year}
                onChange={(v) => onChange(updateCertification(resume, i, { year: v }))}
              />
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}
