"""Known-skill vocabulary used by the rule-based parser and keyword search.

Kept as a flat, lower-cased list so matching is a simple substring/token scan.
Not exhaustive by design — the goal is solid recall across the personas used
in this project's seed data (software/AI engineering, HR, marketing, sales).
"""

SKILLS_VOCAB: list[str] = [
    # Programming languages
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Golang", "C++", "C#", "Ruby", "PHP", "Kotlin", "Swift", "SQL",
    # Web / backend frameworks
    "FastAPI", "Django", "Flask", "Spring Boot", "Node.js", "Express", "NestJS", "React", "Next.js", "Vue", "Angular",
    "GraphQL", "REST API", "gRPC",
    # Data / infra
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "OpenSearch", "Kafka", "RabbitMQ", "Docker",
    "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD", "Jenkins", "Git", "Linux",
    # AI / ML
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "PyTorch", "TensorFlow", "Scikit-learn",
    "LLM", "RAG", "LangChain", "LlamaIndex", "Vector Database", "Qdrant", "Pinecone", "Weaviate", "OpenAI",
    "Hugging Face", "Prompt Engineering", "MLOps", "Data Engineering", "Pandas", "NumPy", "Spark",
    # Mobile
    "iOS", "Android", "React Native", "Flutter",
    # Testing / practices
    "Unit Testing", "TDD", "Agile", "Scrum", "Microservices", "System Design",
    # HR / recruiting
    "Talent Acquisition", "Recruiting", "HRIS", "Onboarding", "Employee Relations", "Payroll", "HR Policy",
    "Interviewing", "Sourcing", "Employer Branding",
    # Marketing
    "SEO", "SEM", "Content Marketing", "Google Ads", "Facebook Ads", "Social Media Marketing", "Email Marketing",
    "Marketing Analytics", "Brand Management", "Copywriting", "Google Analytics",
    # Sales
    "Salesforce", "CRM", "B2B Sales", "Negotiation", "Account Management", "Lead Generation", "Sales Strategy",
    "Cold Calling", "Business Development",
    # General professional
    "Project Management", "Leadership", "Communication", "Stakeholder Management", "Data Analysis", "Excel",
    "Power BI", "Tableau", "English", "Vietnamese",
]

SKILLS_VOCAB_LOWER = {s.lower(): s for s in SKILLS_VOCAB}


def skill_pattern(skill_lower: str) -> str:
    """Word-boundary regex for a vocab skill, tolerant of a trailing plural
    ('vector database' also matches 'vector databases')."""
    import re

    return rf"\b{re.escape(skill_lower)}s?\b"
