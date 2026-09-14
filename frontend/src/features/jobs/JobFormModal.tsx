import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { Dialog } from '../../components/ui/Dialog'
import { Button } from '../../components/ui/Button'
import { Input, Select, Textarea } from '../../components/ui/Input'
import { useCreateJob, useUpdateJob } from '../../services/hooks/useJobs'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import type { EmploymentType, JobOut, JobStatus } from '../../types'

const EMPLOYMENT_TYPES: EmploymentType[] = ['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP']
const STATUSES: JobStatus[] = ['DRAFT', 'OPEN', 'PAUSED', 'CLOSED']

interface FormState {
  title: string
  department: string
  location: string
  employment_type: EmploymentType
  status: JobStatus
  description: string
  responsibilities: string
  requirements: string
  preferred_requirements: string
}

const EMPTY: FormState = {
  title: '',
  department: '',
  location: '',
  employment_type: 'FULL_TIME',
  status: 'DRAFT',
  description: '',
  responsibilities: '',
  requirements: '',
  preferred_requirements: '',
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
              status: job.status,
              description: job.description ?? '',
              responsibilities: job.responsibilities ?? '',
              requirements: job.requirements ?? '',
              preferred_requirements: job.preferred_requirements ?? '',
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
      status: form.status,
      description: form.description || null,
      responsibilities: form.responsibilities || null,
      requirements: form.requirements || null,
      preferred_requirements: form.preferred_requirements || null,
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

        <Textarea label="Description" value={form.description} onChange={(e) => set('description', e.target.value)} />
        <Textarea
          label="Responsibilities"
          value={form.responsibilities}
          onChange={(e) => set('responsibilities', e.target.value)}
        />
        <Textarea
          label="Requirements"
          hint="One requirement per line — used for AI screening and skill matching."
          value={form.requirements}
          onChange={(e) => set('requirements', e.target.value)}
        />
        <Textarea
          label="Preferred requirements"
          value={form.preferred_requirements}
          onChange={(e) => set('preferred_requirements', e.target.value)}
        />

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
