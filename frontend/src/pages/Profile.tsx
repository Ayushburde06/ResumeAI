import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, Plus, Save, Trash2, Upload, User, Briefcase, FolderGit2, GraduationCap, Wrench } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { CareerProfile, ProfileExperience, ProfileProject } from '../types'
import { fetchProfile, importResumeToProfile, saveProfile } from '../lib/api'

const emptyProfile = (): CareerProfile => ({
  personal_info: {
    name: '', email: '', phone: '', location: '', linkedin: '', github: '', website: '', headline: '',
  },
  summary: '',
  experience: [],
  projects: [],
  education: [],
  skills: { languages: [], frameworks: [], databases: [], tools: [], concepts: [], cloud: [], devops: [] },
  certifications: [],
})

function splitCsv(value: string): string[] {
  return value.split(',').map((s) => s.trim()).filter(Boolean)
}

function joinCsv(items?: string[]): string {
  return (items ?? []).join(', ')
}

function Field({
  label,
  value = '',
  onChange,
  placeholder = '',
  multiline = false,
}: {
  label: string
  value?: string
  onChange: (v: string) => void
  placeholder?: string
  multiline?: boolean
}) {
  const cls = 'w-full rounded-xl border border-zinc-200 bg-zinc-50/80 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand'
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium text-zinc-600">{label}</span>
      {multiline ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} rows={3} className={cls} />
      ) : (
        <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={cls} />
      )}
    </label>
  )
}

export default function Profile() {
  const [profile, setProfile] = useState<CareerProfile>(emptyProfile())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [importing, setImporting] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    fetchProfile()
      .then((res) => {
        setProfile(res.career_data)
        setIsComplete(res.is_complete)
      })
      .catch(() => toast.error('Failed to load profile'))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const res = await saveProfile(profile)
      setIsComplete(res.is_complete)
      toast.success('Profile saved')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    try {
      const res = await importResumeToProfile(file)
      setProfile(res.career_data)
      setIsComplete(res.is_complete)
      toast.success('Resume imported into profile')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Import failed')
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  const updateProject = (index: number, patch: Partial<ProfileProject>) => {
    setProfile((p) => {
      const projects = [...p.projects]
      projects[index] = { ...projects[index], ...patch }
      return { ...p, projects }
    })
  }

  const addProject = () => {
    setProfile((p) => ({
      ...p,
      projects: [...p.projects, {
        name: '', description: '', role: '', problem: '', solution: '',
        architecture: '', tech_stack: [], impact_metrics: [], challenges: '', team_size: '',
        link: '', live_link: '', bullets: [],
      }],
    }))
  }

  const removeProject = (index: number) => {
    setProfile((p) => ({ ...p, projects: p.projects.filter((_, i) => i !== index) }))
  }

  const updateExperience = (index: number, patch: Partial<ProfileExperience>) => {
    setProfile((p) => {
      const experience = [...p.experience]
      experience[index] = { ...experience[index], ...patch }
      return { ...p, experience }
    })
  }

  const addExperience = () => {
    setProfile((p) => ({
      ...p,
      experience: [...p.experience, {
        title: '', company: '', location: '', start_date: '', end_date: '', bullets: [], tech_stack: [],
      }],
    }))
  }

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-brand" />
      </div>
    )
  }

  return (
    <div className="page-shell py-6 max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-ink">Career Profile</h1>
          <p className="text-sm text-zinc-600 mt-1">
            Save your experience and projects once — generate tailored resumes without uploading a PDF every time.
          </p>
          {isComplete ? (
            <span className="inline-block mt-2 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-1 rounded-full">Profile ready</span>
          ) : (
            <span className="inline-block mt-2 text-xs font-medium text-amber-700 bg-amber-50 px-2 py-1 rounded-full">Add name + experience or project</span>
          )}
        </div>
        <div className="flex gap-2">
          <input ref={fileInputRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleImport} disabled={importing} />
          <Button variant="outline" className="rounded-2xl" disabled={importing} type="button" onClick={() => fileInputRef.current?.click()}>
            <Upload className="w-4 h-4 mr-2" />{importing ? 'Importing…' : 'Import PDF'}
          </Button>
          <Button onClick={handleSave} disabled={saving} className="rounded-2xl bg-brand hover:bg-brand-hover text-white">
            {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />}
            Save
          </Button>
        </div>
      </div>

      <Tabs defaultValue="personal">
        <TabsList className="grid w-full grid-cols-5 rounded-2xl">
          <TabsTrigger value="personal"><User className="w-4 h-4 mr-1 hidden sm:inline" />Personal</TabsTrigger>
          <TabsTrigger value="experience"><Briefcase className="w-4 h-4 mr-1 hidden sm:inline" />Work</TabsTrigger>
          <TabsTrigger value="projects"><FolderGit2 className="w-4 h-4 mr-1 hidden sm:inline" />Projects</TabsTrigger>
          <TabsTrigger value="skills"><Wrench className="w-4 h-4 mr-1 hidden sm:inline" />Skills</TabsTrigger>
          <TabsTrigger value="education"><GraduationCap className="w-4 h-4 mr-1 hidden sm:inline" />Edu</TabsTrigger>
        </TabsList>

        <TabsContent value="personal" className="panel p-6 space-y-4 mt-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Full name" value={profile.personal_info.name} onChange={(v) => setProfile((p) => ({ ...p, personal_info: { ...p.personal_info, name: v } }))} />
            <Field label="Headline" value={profile.personal_info.headline ?? ''} onChange={(v) => setProfile((p) => ({ ...p, personal_info: { ...p.personal_info, headline: v } }))} />
            <Field label="Email" value={profile.personal_info.email} onChange={(v) => setProfile((p) => ({ ...p, personal_info: { ...p.personal_info, email: v } }))} />
            <Field label="Phone" value={profile.personal_info.phone} onChange={(v) => setProfile((p) => ({ ...p, personal_info: { ...p.personal_info, phone: v } }))} />
            <Field label="Location" value={profile.personal_info.location} onChange={(v) => setProfile((p) => ({ ...p, personal_info: { ...p.personal_info, location: v } }))} />
            <Field label="LinkedIn" value={profile.personal_info.linkedin} onChange={(v) => setProfile((p) => ({ ...p, personal_info: { ...p.personal_info, linkedin: v } }))} />
            <Field label="GitHub" value={profile.personal_info.github} onChange={(v) => setProfile((p) => ({ ...p, personal_info: { ...p.personal_info, github: v } }))} />
            <Field label="Website" value={profile.personal_info.website} onChange={(v) => setProfile((p) => ({ ...p, personal_info: { ...p.personal_info, website: v } }))} />
          </div>
          <Field label="Professional summary" value={profile.summary} onChange={(v) => setProfile((p) => ({ ...p, summary: v }))} multiline />
        </TabsContent>

        <TabsContent value="experience" className="space-y-4 mt-4">
          {profile.experience.map((exp, i) => (
            <div key={i} className="panel p-5 space-y-3">
              <div className="grid sm:grid-cols-2 gap-3">
                <Field label="Title" value={exp.title} onChange={(v) => updateExperience(i, { title: v })} />
                <Field label="Company" value={exp.company} onChange={(v) => updateExperience(i, { company: v })} />
                <Field label="Start" value={exp.start_date} onChange={(v) => updateExperience(i, { start_date: v })} placeholder="Jan 2023" />
                <Field label="End" value={exp.end_date} onChange={(v) => updateExperience(i, { end_date: v })} placeholder="Present" />
              </div>
              <Field label="Bullets (one per line)" value={exp.bullets.join('\n')} onChange={(v) => updateExperience(i, { bullets: v.split('\n').filter(Boolean) })} multiline />
              <Field label="Tech stack (comma-separated)" value={joinCsv(exp.tech_stack)} onChange={(v) => updateExperience(i, { tech_stack: splitCsv(v) })} />
            </div>
          ))}
          <Button variant="outline" onClick={addExperience} className="rounded-2xl"><Plus className="w-4 h-4 mr-2" />Add experience</Button>
        </TabsContent>

        <TabsContent value="projects" className="space-y-4 mt-4">
          {profile.projects.map((proj, i) => (
            <div key={i} className="panel p-5 space-y-3">
              <div className="flex justify-between items-start">
                <h3 className="font-semibold text-sm text-zinc-800">Project {i + 1}</h3>
                <button type="button" onClick={() => removeProject(i)} className="text-zinc-400 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <Field label="Project name" value={proj.name} onChange={(v) => updateProject(i, { name: v })} />
                <Field label="Your role" value={proj.role} onChange={(v) => updateProject(i, { role: v })} />
              </div>
              <Field label="Problem / context" value={proj.problem} onChange={(v) => updateProject(i, { problem: v })} multiline />
              <Field label="Solution / what you built" value={proj.solution} onChange={(v) => updateProject(i, { solution: v })} multiline />
              <Field label="Architecture" value={proj.architecture} onChange={(v) => updateProject(i, { architecture: v })} multiline />
              <Field label="Tech stack (comma-separated)" value={joinCsv(proj.tech_stack)} onChange={(v) => updateProject(i, { tech_stack: splitCsv(v) })} />
              <Field label="Impact metrics (one per line)" value={(proj.impact_metrics || []).join('\n')} onChange={(v) => updateProject(i, { impact_metrics: v.split('\n').filter(Boolean) })} multiline />
              <Field label="Resume bullets (one per line)" value={(proj.bullets || []).join('\n')} onChange={(v) => updateProject(i, { bullets: v.split('\n').filter(Boolean) })} multiline />
              <div className="grid sm:grid-cols-2 gap-3">
                <Field label="GitHub / repo link" value={proj.link} onChange={(v) => updateProject(i, { link: v })} />
                <Field label="Live demo link" value={proj.live_link} onChange={(v) => updateProject(i, { live_link: v })} />
              </div>
            </div>
          ))}
          <Button variant="outline" onClick={addProject} className="rounded-2xl"><Plus className="w-4 h-4 mr-2" />Add project</Button>
        </TabsContent>

        <TabsContent value="skills" className="panel p-6 space-y-4 mt-4">
          {(['languages', 'frameworks', 'databases', 'tools', 'concepts', 'cloud', 'devops'] as const).map((key) => (
            <Field
              key={key}
              label={key.charAt(0).toUpperCase() + key.slice(1)}
              value={joinCsv(profile.skills[key])}
              onChange={(v) => setProfile((p) => ({ ...p, skills: { ...p.skills, [key]: splitCsv(v) } }))}
              placeholder="Python, JavaScript, …"
            />
          ))}
        </TabsContent>

        <TabsContent value="education" className="panel p-6 space-y-4 mt-4">
          <Field label="Degree" value={profile.education[0]?.degree ?? ''} onChange={(v) => setProfile((p) => ({
            ...p,
            education: [{ ...(p.education[0] ?? { institution: '', location: '', graduation_year: '', gpa: '', honors: '' }), degree: v }],
          }))} />
          <Field label="Institution" value={profile.education[0]?.institution ?? ''} onChange={(v) => setProfile((p) => ({
            ...p,
            education: [{ ...(p.education[0] ?? { degree: '', location: '', graduation_year: '', gpa: '', honors: '' }), institution: v }],
          }))} />
          <Field label="Graduation year" value={profile.education[0]?.graduation_year ?? ''} onChange={(v) => setProfile((p) => ({
            ...p,
            education: [{ ...(p.education[0] ?? { degree: '', institution: '', location: '', gpa: '', honors: '' }), graduation_year: v }],
          }))} />
        </TabsContent>
      </Tabs>

      <div className="text-center text-sm text-zinc-500">
        <Link to="/" className="text-brand hover:underline">Go to workspace</Link> to generate a resume from your profile + job description.
      </div>
    </div>
  )
}
