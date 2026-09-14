import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
import type { DashboardResponse } from '../../types'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<DashboardResponse>('/dashboard'),
  })
}
