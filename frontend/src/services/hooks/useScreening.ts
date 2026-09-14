// Screening results are exposed from two places in the API:
// - GET /candidates/{id}/screening  (per-candidate history of screenings)  -> useCandidateScreening
// - POST /jobs/{id}/screen          (bulk-screen applicants for a job)     -> useScreenJob
// Re-exported here under one name for discoverability.
export { useCandidateScreening } from './useCandidates'
export { useScreenJob } from './useJobs'
