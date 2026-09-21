"""Known-skill vocabulary used by the rule-based parser and keyword search.

Grouped into coarse categories (also used to auto-infer a candidate's
`primary_specialty` — see rule_based._guess_primary_specialty) and flattened
into a lower-cased lookup for simple substring/token matching. Not
exhaustive by design — the goal is solid recall across the personas used in
this project's seed data (software/AI engineering, HR, marketing, sales).
"""

SKILL_CATEGORIES: dict[str, list[str]] = {
    "Backend": [
        "Python", "Java", "Go", "Golang", "C++", "C#", "Ruby", "PHP", "SQL",
        "FastAPI", "Django", "Flask", "Spring Boot", "Node.js", "Express", "NestJS",
        "GraphQL", "REST API", "gRPC", "PostgreSQL", "MySQL", "MongoDB", "Redis",
        "Elasticsearch", "OpenSearch", "Kafka", "RabbitMQ", "Microservices", "System Design",
    ],
    "Frontend": ["JavaScript", "TypeScript", "React", "Next.js", "Vue", "Angular"],
    "Mobile": ["iOS", "Android", "React Native", "Flutter", "Swift", "Kotlin"],
    "DevOps/Infrastructure": ["Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD", "Jenkins", "Git", "Linux"],
    "AI/ML & Data": [
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "PyTorch", "TensorFlow", "Scikit-learn",
        "LLM", "RAG", "LangChain", "LlamaIndex", "Vector Database", "Qdrant", "Pinecone", "Weaviate", "OpenAI",
        "Hugging Face", "Prompt Engineering", "MLOps", "Data Engineering", "Pandas", "NumPy", "Spark",
        "Data Analysis", "Power BI", "Tableau",
    ],
    "QA/Testing": ["Unit Testing", "TDD"],
    "HR": [
        "Talent Acquisition", "Recruiting", "HRIS", "Onboarding", "Employee Relations", "Payroll", "HR Policy",
        "Interviewing", "Sourcing", "Employer Branding",
    ],
    "Marketing": [
        "SEO", "SEM", "Content Marketing", "Google Ads", "Facebook Ads", "Social Media Marketing", "Email Marketing",
        "Marketing Analytics", "Brand Management", "Copywriting", "Google Analytics",
    ],
    "Sales": [
        "Salesforce", "CRM", "B2B Sales", "Negotiation", "Account Management", "Lead Generation", "Sales Strategy",
        "Cold Calling", "Business Development",
    ],
    # General/cross-cutting skills — real, but too generic to vote toward a
    # specialty (e.g. "Communication" says nothing about Backend vs Sales).
    "General": [
        "Project Management", "Leadership", "Communication", "Stakeholder Management", "Excel",
        "English", "Vietnamese", "Agile", "Scrum",
    ],
}

SKILLS_VOCAB: list[str] = sorted({skill for skills in SKILL_CATEGORIES.values() for skill in skills})
SKILLS_VOCAB_LOWER = {s.lower(): s for s in SKILLS_VOCAB}

# Categories eligible to "win" a candidate's primary_specialty — General is
# deliberately excluded (see comment above).
SPECIALTY_CATEGORIES = [c for c in SKILL_CATEGORIES if c != "General"]


def skill_pattern(skill_lower: str) -> str:
    """Word-boundary regex for a vocab skill, tolerant of a trailing plural
    ('vector database' also matches 'vector databases')."""
    import re

    return rf"\b{re.escape(skill_lower)}s?\b"
