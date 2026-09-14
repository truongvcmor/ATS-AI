import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, buildQuery } from '../api'
import type {
  ActivityOut,
  CandidateDetail,
  CandidateSearchParams,
  CandidateUpdate,
  MergeRequest,
  PaginatedCandidates,
  ProcessingJobOut,
  ScreeningResultOut,
  UploadResponse,
} from '../../types'

export function useCandidates(params: CandidateSearchParams) {
  const useSearch = Boolean(params.q && params.q.trim().length > 0)
  const path = useSearch ? '/search/candidates' : '/candidates'
  return useQuery({
    queryKey: ['candidates', path, params],
    queryFn: () => api.get<PaginatedCandidates>(`${path}${buildQuery(params as Record<string, string | number | boolean | string[] | undefined>)}`),
    placeholderData: (prev) => prev,
  })
}

export function useCandidate(id: string | undefined) {
  return useQuery({
    queryKey: ['candidate', id],
    queryFn: () => api.get<CandidateDetail>(`/candidates/${id}`),
    enabled: Boolean(id),
  })
}

export function useCandidateHistory(id: string | undefined) {
  return useQuery({
    queryKey: ['candidate-history', id],
    queryFn: () => api.get<ActivityOut[]>(`/candidates/${id}/history`),
    enabled: Boolean(id),
  })
}

export function useCandidateScreening(id: string | undefined) {
  return useQuery({
    queryKey: ['candidate-screening', id],
    queryFn: () => api.get<ScreeningResultOut[]>(`/candidates/${id}/screening`),
    enabled: Boolean(id),
  })
}

export function useUpdateCandidate(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CandidateUpdate) => api.patch<CandidateDetail>(`/candidates/${id}`, body),
    onSuccess: (data) => {
      qc.setQueryData(['candidate', id], data)
      qc.invalidateQueries({ queryKey: ['candidates'] })
      qc.invalidateQueries({ queryKey: ['candidate-history', id] })
    },
  })
}

export function useDeleteCandidate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/candidates/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidates'] })
    },
  })
}

export function useMergeCandidates(targetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sourceId: string) =>
      api.post<CandidateDetail>(`/candidates/${targetId}/merge`, {
        source_candidate_id: sourceId,
        target_candidate_id: targetId,
      } satisfies MergeRequest),
    onSuccess: (data) => {
      qc.setQueryData(['candidate', targetId], data)
      qc.invalidateQueries({ queryKey: ['candidates'] })
      qc.invalidateQueries({ queryKey: ['candidate-history', targetId] })
    },
  })
}

export function useAddLabel(candidateId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (labelId: string) => api.post<void>(`/candidates/${candidateId}/labels/${labelId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidate', candidateId] })
      qc.invalidateQueries({ queryKey: ['candidates'] })
      qc.invalidateQueries({ queryKey: ['labels'] })
    },
  })
}

export function useRemoveLabel(candidateId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (labelId: string) => api.delete<void>(`/candidates/${candidateId}/labels/${labelId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidate', candidateId] })
      qc.invalidateQueries({ queryKey: ['candidates'] })
      qc.invalidateQueries({ queryKey: ['labels'] })
    },
  })
}

export function useUploadCvs() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData()
      files.forEach((f) => form.append('files', f))
      return api.postForm<UploadResponse>('/candidates/upload', form)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['candidates'] })
    },
  })
}

export function processingJobQueryOptions(jobId: string | undefined, enabled: boolean) {
  return {
    queryKey: ['processing-job', jobId] as const,
    queryFn: () => api.get<ProcessingJobOut>(`/candidates/processing/${jobId}`),
    enabled: Boolean(jobId) && enabled,
    refetchInterval: (query: { state: { data?: ProcessingJobOut } }) => {
      const status = query.state.data?.status
      if (status === 'COMPLETED' || status === 'FAILED') return false
      return 1500
    },
  }
}

export function useProcessingJob(jobId: string | undefined, enabled: boolean) {
  return useQuery(processingJobQueryOptions(jobId, enabled))
}

export function useRetryProcessing() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: string) => api.post<ProcessingJobOut>(`/candidates/processing/${jobId}/retry`),
    onSuccess: (data) => {
      qc.setQueryData(['processing-job', data.id], data)
      qc.invalidateQueries({ queryKey: ['candidates'] })
    },
  })
}

export function downloadCvUrl(candidateId: string, cvId: string) {
  return `/candidates/${candidateId}/cvs/${cvId}/download`
}
