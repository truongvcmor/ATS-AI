import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Dialog } from '../../components/ui/Dialog'
import { Button } from '../../components/ui/Button'
import { Select } from '../../components/ui/Input'
import { useJobs } from '../../services/hooks/useJobs'
import { useScreenJob } from '../../services/hooks/useScreening'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'

export function RunScreeningDialog({
  open,
  onClose,
  candidateId,
  candidateName,
}: {
  open: boolean
  onClose: () => void
  candidateId: string
  candidateName: string
}) {
  const [jobId, setJobId] = useState('')
  const { data: jobs, isLoading } = useJobs()
  const screen = useScreenJob(jobId)
  const toast = useToast()
  const qc = useQueryClient()

  async function onRun() {
    if (!jobId) return
    try {
      const results = await screen.mutateAsync([candidateId])
      const result = results[0]
      qc.invalidateQueries({ queryKey: ['candidate-screening', candidateId] })
      qc.invalidateQueries({ queryKey: ['candidate', candidateId] })
      qc.invalidateQueries({ queryKey: ['candidate-history', candidateId] })
      toast.success(`Screened ${candidateName}: ${result.recommendation.replace(/_/g, ' ')} (${Math.round(result.overall_score)}/100)`)
      reset()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Screening failed')
    }
  }

  function reset() {
    setJobId('')
    onClose()
  }

  return (
    <Dialog open={open} onClose={reset} title="Run AI screening" size="sm">
      <div className="space-y-4">
        <p className="text-sm text-slate-500">
          Compare <strong>{candidateName}</strong>'s profile against a job's requirements. This is an AI-generated
          recommendation — you make the final call.
        </p>

        {isLoading ? (
          <p className="text-sm text-slate-400">Loading jobs...</p>
        ) : !jobs || jobs.length === 0 ? (
          <p className="text-sm text-slate-400">No jobs yet — create one first from the Jobs page.</p>
        ) : (
          <Select label="Job" value={jobId} onChange={(e) => setJobId(e.target.value)}>
            <option value="">Select a job...</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title}
              </option>
            ))}
          </Select>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={reset}>
            Cancel
          </Button>
          <Button onClick={onRun} disabled={!jobId} loading={screen.isPending}>
            Run screening
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
