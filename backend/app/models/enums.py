import enum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    RECRUITER = "RECRUITER"
    HIRING_MANAGER = "HIRING_MANAGER"


class JobStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"


class CandidateStatus(str, enum.Enum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    IN_PROCESS = "IN_PROCESS"
    HIRED = "HIRED"
    ARCHIVED = "ARCHIVED"


class ProcessingStatus(str, enum.Enum):
    UPLOADING = "UPLOADING"
    PARSING = "PARSING"
    PROCESSING = "PROCESSING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Recommendation(str, enum.Enum):
    STRONG_MATCH = "STRONG_MATCH"
    MATCH = "MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    WEAK_MATCH = "WEAK_MATCH"


class AssessmentRecommendation(str, enum.Enum):
    STRONG_HIRE = "STRONG_HIRE"
    HIRE = "HIRE"
    MAYBE = "MAYBE"
    NO_HIRE = "NO_HIRE"


class DuplicateAction(str, enum.Enum):
    MERGED = "MERGED"
    KEPT_SEPARATE = "KEPT_SEPARATE"
