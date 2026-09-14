// ---- Enums ----

export type UserRole = 'ADMIN' | 'RECRUITER' | 'HIRING_MANAGER'

export type CandidateStatus = 'NEW' | 'ACTIVE' | 'IN_PROCESS' | 'HIRED' | 'ARCHIVED'

export type ProcessingStatus =
  | 'UPLOADING'
  | 'PARSING'
  | 'PROCESSING'
  | 'INDEXING'
  | 'COMPLETED'
  | 'FAILED'

export type Recommendation = 'STRONG_MATCH' | 'MATCH' | 'POSSIBLE_MATCH' | 'WEAK_MATCH'

export type AssessmentRecommendation = 'STRONG_HIRE' | 'HIRE' | 'MAYBE' | 'NO_HIRE'

export type EmploymentType = 'FULL_TIME' | 'PART_TIME' | 'CONTRACT' | 'INTERNSHIP'

export type JobStatus = 'DRAFT' | 'OPEN' | 'PAUSED' | 'CLOSED'

export type SortBy = 'relevance' | 'ai_score' | 'experience' | 'recently_added' | 'recently_updated'

// ---- Auth ----

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

// ---- Labels ----

export interface LabelBadge {
  id: string
  name: string
  color: string
}

export interface Label {
  id: string
  name: string
  color: string
  candidate_count: number
}

// ---- Candidates ----

export interface CandidateListItem {
  id: string
  full_name: string
  current_title: string | null
  years_of_experience: number | null
  location: string | null
  email: string | null
  ai_score: number | null
  status: CandidateStatus
  skills: string[]
  labels: LabelBadge[]
  updated_at: string
  created_at: string
  relevance_score?: number
}

export interface ExperienceOut {
  id: string
  company: string
  position: string
  start_date: string | null
  end_date: string | null
  is_current: boolean
  description: string | null
}

export interface EducationOut {
  id: string
  school: string
  degree: string | null
  major: string | null
  start_date: string | null
  end_date: string | null
}

export interface CertificationOut {
  id: string
  name: string
  issuer: string | null
  issue_date: string | null
}

export interface LanguageOut {
  id: string
  name: string
  proficiency: string | null
}

export interface ProjectOut {
  id: string
  name: string
  description: string | null
  technologies: string | null
}

export interface CVOut {
  id: string
  file_name: string
  content_type: string
  extraction_method: 'text' | 'ocr'
  is_primary: boolean
  uploaded_at: string
}

export interface CandidateDetail extends CandidateListItem {
  phone: string | null
  summary: string | null
  source: string
  experiences: ExperienceOut[]
  educations: EducationOut[]
  certifications: CertificationOut[]
  languages: LanguageOut[]
  projects: ProjectOut[]
  cvs: CVOut[]
}

export interface CandidateUpdate {
  full_name?: string
  email?: string
  phone?: string
  location?: string
  current_title?: string
  years_of_experience?: number
  summary?: string
  status?: CandidateStatus
}

export interface PaginatedCandidates {
  items: CandidateListItem[]
  total: number
  page: number
  page_size: number
}

export interface CandidateSearchParams {
  q?: string
  semantic?: boolean
  skills?: string[]
  min_experience?: number
  locations?: string[]
  labels?: string[]
  min_ai_score?: number
  sort_by?: SortBy
  page?: number
  page_size?: number
}

export interface ProcessingJobOut {
  id: string
  file_name: string
  candidate_id: string | null
  status: ProcessingStatus
  error_message: string | null
  duplicate_of_candidate_id: string | null
  created_at: string
  updated_at: string
}

export interface UploadResponse {
  jobs: ProcessingJobOut[]
}

export interface ActivityOut {
  id: string
  type: string
  description: string
  activity_metadata: Record<string, unknown> | null
  created_at: string
  created_by: string | null
}

export interface ScreeningResultOut {
  id: string
  candidate_id: string
  job_id: string
  overall_score: number
  recommendation: Recommendation
  matched_requirements: string[]
  missing_requirements: string[]
  strengths: string[]
  concerns: string[]
  reasoning: string | null
  created_at: string
}

export interface AssessmentOut {
  id: string
  candidate_id: string
  job_id: string | null
  interview_type: string
  interviewer: string
  score: number | null
  strengths: string | null
  weaknesses: string | null
  comments: string | null
  recommendation: AssessmentRecommendation
  created_at: string
}

export interface AssessmentCreate {
  job_id?: string | null
  interview_type: string
  interviewer: string
  score?: number | null
  strengths?: string | null
  weaknesses?: string | null
  comments?: string | null
  recommendation: AssessmentRecommendation
}

export interface MergeRequest {
  source_candidate_id: string
  target_candidate_id: string
}

// ---- Jobs ----

export interface JobOut {
  id: string
  title: string
  department: string | null
  location: string | null
  employment_type: EmploymentType
  description: string | null
  responsibilities: string | null
  requirements: string | null
  preferred_requirements: string | null
  status: JobStatus
  created_at: string
  updated_at: string
  application_count: number
}

export interface JobCreate {
  title: string
  department?: string | null
  location?: string | null
  employment_type?: EmploymentType
  description?: string | null
  responsibilities?: string | null
  requirements?: string | null
  preferred_requirements?: string | null
  status?: JobStatus
}

export type JobUpdate = Partial<JobCreate>

export interface PipelineStageOut {
  id: string
  name: string
  order: number
  is_terminal: boolean
}

export interface ApplicationCandidateSummary {
  id: string
  full_name: string
  current_title: string | null
  ai_score: number | null
  location: string | null
}

export interface ApplicationOut {
  id: string
  candidate_id: string
  job_id: string
  current_stage_id: string
  applied_at: string
  updated_at: string
  candidate: ApplicationCandidateSummary | null
}

export interface ApplicationCreate {
  candidate_id: string
  job_id: string
}

export interface CandidateRecommendation {
  candidate: CandidateListItem
  final_score: number
  keyword_score: number
  semantic_score: number
  skill_match_score: number
  experience_score: number
  screening_score: number | null
  matched_skills: string[]
  missing_skills: string[]
  explanation: string
}

export interface RecommendationResponse {
  job_id: string
  recommendations: CandidateRecommendation[]
}

// ---- Dashboard ----

export interface DashboardKpis {
  total_candidates: number
  new_candidates_last_30_days: number
  open_jobs: number
  candidates_in_pipeline: number
  ai_shortlisted: number
  hired: number
}

export interface ChartPoint {
  label: string
  value: number
}

export interface SkillCount {
  skill: string
  count: number
}

export interface LocationCount {
  location: string
  count: number
}

export interface StageCount {
  stage: string
  count: number
}

export interface BucketCount {
  bucket: string
  count: number
}

export interface DashboardResponse {
  kpis: DashboardKpis
  candidates_over_time: ChartPoint[]
  candidates_by_source: ChartPoint[]
  top_skills: SkillCount[]
  top_locations: LocationCount[]
  pipeline_by_stage: StageCount[]
  ai_score_distribution: BucketCount[]
}

// ---- Generic API error ----

export interface ApiErrorBody {
  detail?: string | { msg: string }[] | unknown
}

// ---- AI Settings (admin only) ----

export type LlmProviderChoice = 'mock' | 'openai' | 'gemini' | 'auto'
export type OcrProviderChoice = 'tesseract' | 'llm_vision' | 'auto'
export type SettingsSource = 'database' | 'env' | 'none'

export interface AISettings {
  llm_provider: LlmProviderChoice
  embedding_provider: LlmProviderChoice
  ocr_provider: OcrProviderChoice

  openai_configured: boolean
  openai_keys_masked: string[]
  openai_model: string
  openai_source: SettingsSource

  gemini_configured: boolean
  gemini_keys_masked: string[]
  gemini_model: string
  gemini_source: SettingsSource

  embedding_model: string
  gemini_embedding_model: string
  embedding_dim: number

  updated_at: string | null
  updated_by: string | null
}

export interface AISettingsUpdate {
  llm_provider?: LlmProviderChoice
  embedding_provider?: LlmProviderChoice
  ocr_provider?: OcrProviderChoice
  openai_api_keys?: string
  openai_model?: string
  gemini_api_keys?: string
  gemini_model?: string
  embedding_model?: string
  gemini_embedding_model?: string
}

export interface AISettingsTestRequest {
  provider: 'openai' | 'gemini'
  api_key?: string
  model?: string
}

export interface AISettingsTestResult {
  ok: boolean
  message: string
  latency_ms: number | null
}
