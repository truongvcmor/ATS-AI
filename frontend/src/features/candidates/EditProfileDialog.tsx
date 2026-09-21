import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'
import { Dialog } from '../../components/ui/Dialog'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/ui/Input'
import { useUpdateCandidate } from '../../services/hooks/useCandidates'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import type { CandidateDetail, SalaryCurrency, SeniorityLevel } from '../../types'

const LEVELS: SeniorityLevel[] = ['INTERN', 'FRESHER', 'JUNIOR', 'MID', 'SENIOR', 'LEAD', 'MANAGER', 'DIRECTOR']
const CURRENCIES: SalaryCurrency[] = ['VND', 'USD']

export function EditProfileDialog({
  open,
  onClose,
  candidate,
}: {
  open: boolean
  onClose: () => void
  candidate: CandidateDetail
}) {
  const [level, setLevel] = useState<SeniorityLevel | ''>('')
  const [specialty, setSpecialty] = useState('')
  const [portfolioUrl, setPortfolioUrl] = useState('')
  const [salaryMin, setSalaryMin] = useState('')
  const [salaryMax, setSalaryMax] = useState('')
  const [currency, setCurrency] = useState<SalaryCurrency>('VND')
  const update = useUpdateCandidate(candidate.id)
  const toast = useToast()

  useEffect(() => {
    if (open) {
      setLevel(candidate.current_level ?? '')
      setSpecialty(candidate.primary_specialty ?? '')
      setPortfolioUrl(candidate.portfolio_url ?? '')
      setSalaryMin(candidate.expected_salary_min?.toString() ?? '')
      setSalaryMax(candidate.expected_salary_max?.toString() ?? '')
      setCurrency(candidate.expected_salary_currency)
    }
  }, [open, candidate])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    try {
      await update.mutateAsync({
        current_level: level || undefined,
        primary_specialty: specialty || undefined,
        portfolio_url: portfolioUrl || undefined,
        expected_salary_min: salaryMin ? Number(salaryMin) : undefined,
        expected_salary_max: salaryMax ? Number(salaryMax) : undefined,
        expected_salary_currency: currency,
      })
      toast.success('Profile updated')
      onClose()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to update profile')
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="Edit profile details" size="md">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <Select label="Current level" value={level} onChange={(e) => setLevel(e.target.value as SeniorityLevel | '')}>
            <option value="">Unspecified</option>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </Select>
          <Input label="Primary specialty" value={specialty} onChange={(e) => setSpecialty(e.target.value)} />
        </div>
        <Input
          label="Portfolio / GitHub URL"
          value={portfolioUrl}
          onChange={(e) => setPortfolioUrl(e.target.value)}
          placeholder="https://github.com/..."
        />
        <div className="grid grid-cols-3 gap-3">
          <Input label="Expected salary min" type="number" value={salaryMin} onChange={(e) => setSalaryMin(e.target.value)} />
          <Input label="Expected salary max" type="number" value={salaryMax} onChange={(e) => setSalaryMax(e.target.value)} />
          <Select label="Currency" value={currency} onChange={(e) => setCurrency(e.target.value as SalaryCurrency)}>
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={update.isPending}>
            Save changes
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
