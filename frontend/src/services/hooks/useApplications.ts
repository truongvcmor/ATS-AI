import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { ApplicationCreate, ApplicationOut } from '../../types'

export function useCreateApplication(jobId?: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ApplicationCreate) => api.post<ApplicationOut>('/applications', body),
    onSuccess: () => {
      if (jobId) qc.invalidateQueries({ queryKey: ['job-candidates', jobId] })
    },
  })
}

export function useUpdateApplicationStage(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ applicationId, stageId }: { applicationId: string; stageId: string }) =>
      api.patch<ApplicationOut>(`/applications/${applicationId}/stage`, { stage_id: stageId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['job-candidates', jobId] })
    },
  })
}
