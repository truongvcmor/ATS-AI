import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './app/ProtectedRoute'
import { AppLayout } from './app/AppLayout'
import { LoginPage } from './features/auth/LoginPage'
import { DashboardPage } from './features/dashboard/DashboardPage'
import { TalentPoolPage } from './features/talent-pool/TalentPoolPage'
import { CandidateDetailPage } from './features/candidates/CandidateDetailPage'
import { JobsListPage } from './features/jobs/JobsListPage'
import { JobDetailPage } from './features/jobs/JobDetailPage'
import { LabelsPage } from './features/labels/LabelsPage'
import { SettingsPage } from './features/settings/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="talent-pool" element={<TalentPoolPage />} />
        <Route path="candidates/:id" element={<CandidateDetailPage />} />
        <Route path="jobs" element={<JobsListPage />} />
        <Route path="jobs/:id" element={<JobDetailPage />} />
        <Route path="labels" element={<LabelsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}
