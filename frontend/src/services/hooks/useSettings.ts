import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import type { AISettings, AISettingsTestRequest, AISettingsTestResult, AISettingsUpdate } from '../../types'

export function useAISettings() {
  return useQuery({
    queryKey: ['settings', 'ai'],
    queryFn: () => api.get<AISettings>('/settings/ai'),
    retry: false,
  })
}

export function useUpdateAISettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AISettingsUpdate) => api.put<AISettings>('/settings/ai', body),
    onSuccess: (data) => qc.setQueryData(['settings', 'ai'], data),
  })
}

export function useTestAIProvider() {
  return useMutation({
    mutationFn: (body: AISettingsTestRequest) => api.post<AISettingsTestResult>('/settings/ai/test', body),
  })
}
