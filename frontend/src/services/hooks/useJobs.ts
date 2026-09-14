import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type {
  ApplicationOut,
  JobCreate,
  JobOut,
  JobUpdate,
  PipelineStageOut,
  RecommendationResponse,
  ScreeningResultOut,
} from '../../types'

export function useJobs() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.get<JobOut[]>('/jobs'),
  })
}

export function useJob(id: string | undefined) {
  return useQuery({
    queryKey: ['job', id],
    queryFn: () => api.get<JobOut>(`/jobs/${id}`),
    enabled: Boolean(id),
  })
}

export function useCreateJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: JobCreate) => api.post<JobOut>('/jobs', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useUpdateJob(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: JobUpdate) => api.patch<JobOut>(`/jobs/${id}`, body),
    onSuccess: (data) => {
      qc.setQueryData(['job', id], data)
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useDeleteJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/jobs/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
}

export function useJobStages(jobId: string | undefined) {
  return useQuery({
    queryKey: ['job-stages', jobId],
    queryFn: () => api.get<PipelineStageOut[]>(`/jobs/${jobId}/stages`),
    enabled: Boolean(jobId),
  })
}

export function useJobCandidates(jobId: string | undefined) {
  return useQuery({
    queryKey: ['job-candidates', jobId],
    queryFn: () => api.get<ApplicationOut[]>(`/jobs/${jobId}/candidates`),
    enabled: Boolean(jobId),
    retry: 1,
  })
}

export function useScreenJob(jobId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (candidateIds?: string[]) =>
      api.post<ScreeningResultOut[]>(`/jobs/${jobId}/screen`, {
        job_id: jobId,
        candidate_ids: candidateIds,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['job-candidates', jobId] })
      qc.invalidateQueries({ queryKey: ['recommendations', jobId] })
    },
  })
}

export function useRecommendations(jobId: string) {
  return useMutation({
    mutationFn: () => api.post<RecommendationResponse>(`/jobs/${jobId}/recommendations`),
  })
}
