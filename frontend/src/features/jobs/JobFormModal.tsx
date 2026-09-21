import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { Dialog } from '../../components/ui/Dialog'
import { Button } from '../../components/ui/Button'
import { Input, Select, Textarea } from '../../components/ui/Input'
import { useCreateJob, useUpdateJob } from '../../services/hooks/useJobs'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import type {
  EmploymentType,
  GenderRequirement,
  JobOut,
  JobStatus,
  SalaryCurrency,
  SeniorityLevel,
} from '../../types'

const EMPLOYMENT_TYPES: EmploymentType[] = ['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP']
const STATUSES: JobStatus[] = ['DRAFT', 'OPEN', 'PAUSED', 'CLOSED']
const LEVELS: SeniorityLevel[] = ['INTERN', 'FRESHER', 'JUNIOR', 'MID', 'SENIOR', 'LEAD', 'MANAGER', 'DIRECTOR']
const CURRENCIES: SalaryCurrency[] = ['VND', 'USD']
const GENDER_REQUIREMENTS: GenderRequirement[] = ['ANY', 'MALE', 'FEMALE']

interface FormState {
  title: string
  department: string
  location: string
  employment_type: EmploymentType
  level: SeniorityLevel | ''
  status: JobStatus
  salary_min: string
  salary_max: string
  salary_currency: SalaryCurrency
  salary_negotiable: boolean
  working_hours: string
  benefits: string
  hiring_reason: string
  age_min: string
  age_max: string
  gender_requirement: GenderRequirement
  description: string
  responsibilities: string
  requirements: string
  preferred_requirements: string
  technical_skills: string
  soft_skills: string
}

const EMPTY: FormState = {
  title: '',
  department: '',
  location: '',
  employment_type: 'FULL_TIME',
  level: '',
  status: 'DRAFT',
  salary_min: '',
  salary_max: '',
  salary_currency: 'VND',
  salary_negotiable: false,
  working_hours: '',
  benefits: '',
  hiring_reason: '',
  age_min: '',
  age_max: '',
  gender_requirement: 'ANY',
  description: '',
  responsibilities: '',
  requirements: '',
  preferred_requirements: '',
  technical_skills: '',
  soft_skills: '',
}

export function JobFormModal({
  open,
  onClose,
  job,
  onSaved,
}: {
  open: boolean
  onClose: () => void
  job?: JobOut | null
  onSaved?: (job: JobOut) => void
}) {
  const [form, setForm] = useState<FormState>(EMPTY)
  const create = useCreateJob()
  const update = useUpdateJob(job?.id ?? '')
  const toast = useToast()
  const isEdit = Boolean(job)

  useEffect(() => {
    if (open) {
      setForm(
        job
          ? {
              title: job.title,
              department: job.department ?? '',
              location: job.location ?? '',
              employment_type: job.employment_type,
              level: job.level ?? '',
              status: job.status,
              salary_min: job.salary_min?.toString() ?? '',
              salary_max: job.salary_max?.toString() ?? '',
              salary_currency: job.salary_currency,
              salary_negotiable: job.salary_negotiable,
              working_hours: job.working_hours ?? '',
              benefits: job.benefits ?? '',
              hiring_reason: job.hiring_reason ?? '',
              age_min: job.age_min?.toString() ?? '',
              age_max: job.age_max?.toString() ?? '',
              gender_requirement: job.gender_requirement,
              description: job.description ?? '',
              responsibilities: job.responsibilities ?? '',
              requirements: job.requirements ?? '',
              preferred_requirements: job.preferred_requirements ?? '',
              technical_skills: job.technical_skills ?? '',
              soft_skills: job.soft_skills ?? '',
            }
          : EMPTY,
      )
    }
  }, [open, job])

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.title.trim()) return
    const body = {
      title: form.title.trim(),
      department: form.department || null,
      location: form.location || null,
      employment_type: form.employment_type,
      level: form.level || null,
      status: form.status,
      salary_min: form.salary_min ? Number(form.salary_min) : null,
      salary_max: form.salary_max ? Number(form.salary_max) : null,
      salary_currency: form.salary_currency,
      salary_negotiable: form.salary_negotiable,
      working_hours: form.working_hours || null,
      benefits: form.benefits || null,
      hiring_reason: form.hiring_reason || null,
      age_min: form.age_min ? Number(form.age_min) : null,
      age_max: form.age_max ? Number(form.age_max) : null,
      gender_requirement: form.gender_requirement,
      description: form.description || null,
      responsibilities: form.responsibilities || null,
      requirements: form.requirements || null,
      preferred_requirements: form.preferred_requirements || null,
      technical_skills: form.technical_skills || null,
      soft_skills: form.soft_skills || null,
    }
    try {
      const saved = isEdit ? await update.mutateAsync(body) : await create.mutateAsync(body)
      toast.success(isEdit ? 'Job updated' : 'Job created')
      onSaved?.(saved)
      onClose()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to save job')
    }
  }

  const pending = create.isPending || update.isPending

  return (
    <Dialog open={open} onClose={onClose} title={isEdit ? 'Edit job' : 'New job'} size="xl">
      <form onSubmit={onSubmit} className="space-y-4">
        <Input label="Title" required value={form.title} onChange={(e) => set('title', e.target.value)} />

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Input label="Department" value={form.department} onChange={(e) => set('department', e.target.value)} />
          <Input label="Location" value={form.location} onChange={(e) => set('location', e.target.value)} />
          <Select
            label="Employment type"
            value={form.employment_type}
            onChange={(e) => set('employment_type', e.target.value as EmploymentType)}
          >
            {EMPLOYMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace('_', ' ')}
              </option>
            ))}
          </Select>
          <Select label="Status" value={form.status} onChange={(e) => set('status', e.target.value as JobStatus)}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Select
            label="Level"
            value={form.level}
            onChange={(e) => set('level', e.target.value as SeniorityLevel | '')}
          >
            <option value="">Unspecified</option>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </Select>
          <Input
            label="Salary min"
            type="number"
            value={form.salary_min}
            onChange={(e) => set('salary_min', e.target.value)}
          />
          <Input
            label="Salary max"
            type="number"
            value={form.salary_max}
            onChange={(e) => set('salary_max', e.target.value)}
          />
          <Select
            label="Currency"
            value={form.salary_currency}
            onChange={(e) => set('salary_currency', e.target.value as SalaryCurrency)}
          >
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
        </div>

        <label className="flex items-center gap-1.5 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={form.salary_negotiable}
            onChange={(e) => set('salary_negotiable', e.target.checked)}
            className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
          />
          Salary negotiable
        </label>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Input
            label="Working hours"
            placeholder="e.g. Mon-Fri, 9:00-18:00"
            value={form.working_hours}
            onChange={(e) => set('working_hours', e.target.value)}
          />
          <Input label="Age min" type="number" value={form.age_min} onChange={(e) => set('age_min', e.target.value)} />
          <Input label="Age max" type="number" value={form.age_max} onChange={(e) => set('age_max', e.target.value)} />
        </div>
        <Select
          label="Gender requirement"
          hint="Informational only — never used by AI screening or recommendations."
          value={form.gender_requirement}
          onChange={(e) => set('gender_requirement', e.target.value as GenderRequirement)}
        >
          {GENDER_REQUIREMENTS.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </Select>

        <Textarea label="Description" value={form.description} onChange={(e) => set('description', e.target.value)} />
        <Textarea
          label="Responsibilities"
          value={form.responsibilities}
          onChange={(e) => set('responsibilities', e.target.value)}
        />
        <Textarea
          label="Requirements"
          hint="Mandatory requirements — one per line. Used for AI screening and skill matching."
          value={form.requirements}
          onChange={(e) => set('requirements', e.target.value)}
        />
        <Textarea
          label="Preferred requirements"
          hint="Nice-to-have requirements."
          value={form.preferred_requirements}
          onChange={(e) => set('preferred_requirements', e.target.value)}
        />
        <Textarea
          label="Technical skills"
          value={form.technical_skills}
          onChange={(e) => set('technical_skills', e.target.value)}
        />
        <Textarea label="Soft skills" value={form.soft_skills} onChange={(e) => set('soft_skills', e.target.value)} />
        <Textarea
          label="Hiring reason"
          hint="Why this position is being opened (optional)."
          value={form.hiring_reason}
          onChange={(e) => set('hiring_reason', e.target.value)}
        />
        <Textarea label="Benefits" value={form.benefits} onChange={(e) => set('benefits', e.target.value)} />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pending}>
            {isEdit ? 'Save changes' : 'Create job'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
