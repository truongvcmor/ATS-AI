import type { FormEvent } from 'react'
import { useState } from 'react'
import { Dialog } from '../../components/ui/Dialog'
import { Button } from '../../components/ui/Button'
import { Input, Select, Textarea } from '../../components/ui/Input'
import { useCreateAssessment } from '../../services/hooks/useAssessments'
import { useJobs } from '../../services/hooks/useJobs'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import type { AssessmentRecommendation } from '../../types'
import { useAuth } from '../../hooks/useAuth'

const RECOMMENDATIONS: AssessmentRecommendation[] = ['STRONG_HIRE', 'HIRE', 'MAYBE', 'NO_HIRE']

export function AssessmentForm({
  open,
  onClose,
  candidateId,
}: {
  open: boolean
  onClose: () => void
  candidateId: string
}) {
  const { user } = useAuth()
  const { data: jobs } = useJobs()
  const create = useCreateAssessment(candidateId)
  const toast = useToast()

  const [jobId, setJobId] = useState('')
  const [interviewType, setInterviewType] = useState('')
  const [interviewer, setInterviewer] = useState(user?.full_name ?? '')
  const [score, setScore] = useState('')
  const [recommendation, setRecommendation] = useState<AssessmentRecommendation>('MAYBE')
  const [strengths, setStrengths] = useState('')
  const [weaknesses, setWeaknesses] = useState('')
  const [comments, setComments] = useState('')

  function reset() {
    setJobId('')
    setInterviewType('')
    setScore('')
    setRecommendation('MAYBE')
    setStrengths('')
    setWeaknesses('')
    setComments('')
    onClose()
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!interviewType.trim() || !interviewer.trim()) return
    try {
      await create.mutateAsync({
        job_id: jobId || null,
        interview_type: interviewType.trim(),
        interviewer: interviewer.trim(),
        score: score ? Number(score) : null,
        strengths: strengths || null,
        weaknesses: weaknesses || null,
        comments: comments || null,
        recommendation,
      })
      toast.success('Assessment added')
      reset()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to add assessment')
    }
  }

  return (
    <Dialog open={open} onClose={reset} title="Add assessment" size="lg">
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Record the interviewer's own judgment here — this is separate from the AI screening score.
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Interview type"
            required
            placeholder="e.g. Technical Interview"
            value={interviewType}
            onChange={(e) => setInterviewType(e.target.value)}
          />
          <Input
            label="Interviewer"
            required
            value={interviewer}
            onChange={(e) => setInterviewer(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Select label="Related job (optional)" value={jobId} onChange={(e) => setJobId(e.target.value)}>
            <option value="">— None —</option>
            {jobs?.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title}
              </option>
            ))}
          </Select>
          <Input
            label="Score (0-10)"
            type="number"
            min={0}
            max={10}
            step={0.5}
            value={score}
            onChange={(e) => setScore(e.target.value)}
          />
        </div>

        <Select
          label="Recommendation"
          required
          value={recommendation}
          onChange={(e) => setRecommendation(e.target.value as AssessmentRecommendation)}
        >
          {RECOMMENDATIONS.map((r) => (
            <option key={r} value={r}>
              {r.replace('_', ' ')}
            </option>
          ))}
        </Select>

        <Textarea label="Strengths" value={strengths} onChange={(e) => setStrengths(e.target.value)} rows={2} />
        <Textarea label="Weaknesses" value={weaknesses} onChange={(e) => setWeaknesses(e.target.value)} rows={2} />
        <Textarea label="Comments" value={comments} onChange={(e) => setComments(e.target.value)} rows={2} />

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={reset}>
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending}>
            Save assessment
          </Button>
        </div>
      </form>
    </Dialog>
  )
}
