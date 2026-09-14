import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { Label } from '../../types'

interface LabelInput {
  name: string
  color: string
}

export function useLabels() {
  return useQuery({
    queryKey: ['labels'],
    queryFn: () => api.get<Label[]>('/labels'),
  })
}

export function useCreateLabel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LabelInput) => api.post<Label>('/labels', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['labels'] }),
  })
}

export function useUpdateLabel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Partial<LabelInput>) => api.patch<Label>(`/labels/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['labels'] }),
  })
}

export function useDeleteLabel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete<void>(`/labels/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['labels'] })
      qc.invalidateQueries({ queryKey: ['candidates'] })
    },
  })
}
