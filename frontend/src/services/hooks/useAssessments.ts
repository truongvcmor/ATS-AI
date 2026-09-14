import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { AssessmentCreate, AssessmentOut } from '../../types'

export function useAssessments(candidateId: string | undefined) {
  return useQuery({
    queryKey: ['assessments', candidateId],
    queryFn: () => api.get<AssessmentOut[]>(`/candidates/${candidateId}/assessments`),
    enabled: Boolean(candidateId),
  })
}

export function useCreateAssessment(candidateId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AssessmentCreate) => api.post<AssessmentOut>(`/candidates/${candidateId}/assessments`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assessments', candidateId] })
      qc.invalidateQueries({ queryKey: ['candidate-history', candidateId] })
    },
  })
}
