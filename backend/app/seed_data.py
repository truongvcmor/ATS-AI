"""Static persona data used by app/seed.py to build realistic-looking sample CVs."""

VIETNAMESE_NAMES = [
    "Nguyen Van An", "Tran Thi Bich", "Le Van Cuong", "Pham Thi Dung", "Hoang Van Em",
    "Vu Thi Giang", "Dang Van Hai", "Bui Thi Huong", "Do Van Khoa", "Ngo Thi Lan",
    "Duong Van Minh", "Ly Thi Ngoc", "Truong Van Phuc", "Phan Thi Quyen", "Vo Van Son",
]

ENGLISH_NAMES = [
    "James Anderson", "Emily Carter", "Michael Brooks", "Sarah Mitchell", "David Thompson",
    "Jessica Parker", "Daniel Foster", "Laura Bennett", "Matthew Reed", "Olivia Ward",
    "Ryan Coleman", "Sophia Bailey", "Andrew Hayes", "Grace Sullivan", "Nathan Price",
]

LOCATIONS = ["Ho Chi Minh City", "Hanoi", "Da Nang", "Remote", "Singapore"]

SOFTWARE_ENGINEERING = dict(
    category="software",
    titles=["Backend Engineer", "Full-stack Engineer", "Software Engineer", "DevOps Engineer", "Mobile Engineer"],
    skill_pools=[
        "Python, FastAPI, PostgreSQL, Docker, AWS, Git",
        "Java, Spring Boot, MySQL, Kubernetes, CI/CD",
        "TypeScript, React, Node.js, GraphQL, MongoDB",
        "Go, Microservices, Kafka, Redis, Terraform",
        "React Native, iOS, Android, Flutter, REST API",
    ],
    companies=["TechNova", "Bitcraft Labs", "CloudForge", "Vertex Systems", "Northwind Software"],
    summary="Software engineer focused on building reliable, scalable backend and web systems.",
)

AI_ML = dict(
    category="ai",
    titles=["AI Engineer", "Machine Learning Engineer", "Data Scientist", "NLP Engineer", "AI Research Engineer"],
    skill_pools=[
        "Python, FastAPI, LLM, RAG, LangChain, Vector Database, Qdrant",
        "PyTorch, Deep Learning, Computer Vision, MLOps, Docker",
        "Machine Learning, NLP, Hugging Face, Prompt Engineering, AWS",
        "TensorFlow, Data Engineering, Spark, Pandas, SQL",
        "Python, OpenAI, LangChain, Elasticsearch, System Design",
    ],
    companies=["DeepStack AI", "Cognivia", "NeuralWorks", "Insight Analytics", "Vector Labs"],
    summary="AI/ML engineer experienced building and shipping production LLM and RAG-based systems.",
)

HR = dict(
    category="hr",
    titles=["HR Generalist", "Talent Acquisition Specialist", "HR Business Partner", "Recruiter", "People Operations Manager"],
    skill_pools=[
        "Talent Acquisition, Recruiting, Sourcing, Interviewing, HRIS",
        "Employee Relations, Onboarding, HR Policy, Payroll, Communication",
        "Employer Branding, Stakeholder Management, Project Management, Excel",
    ],
    companies=["PeopleFirst Co", "TalentBridge", "HR Solutions Vietnam", "WorkWell Group", "Unity HR"],
    summary="HR professional experienced in end-to-end recruiting and employee lifecycle management.",
)

MARKETING = dict(
    category="marketing",
    titles=["Marketing Specialist", "Digital Marketing Manager", "Content Marketing Lead", "Brand Manager", "SEO Specialist"],
    skill_pools=[
        "SEO, SEM, Google Ads, Google Analytics, Content Marketing",
        "Social Media Marketing, Facebook Ads, Copywriting, Brand Management",
        "Email Marketing, Marketing Analytics, Content Marketing, Communication",
    ],
    companies=["BrightWave Media", "Growth Studio", "MarketEdge", "Nova Brands", "Reach Digital"],
    summary="Marketing professional with a track record of driving growth through data-informed campaigns.",
)

SALES = dict(
    category="sales",
    titles=["Sales Executive", "Account Manager", "Business Development Manager", "Sales Manager", "Inside Sales Representative"],
    skill_pools=[
        "Salesforce, CRM, B2B Sales, Negotiation, Lead Generation",
        "Account Management, Business Development, Cold Calling, Sales Strategy",
        "Negotiation, Stakeholder Management, CRM, Communication",
    ],
    companies=["SalesPeak", "Momentum Partners", "Apex Commerce", "Growth Partners", "Frontier Sales"],
    summary="Sales professional focused on building long-term client relationships and exceeding targets.",
)

PERSONA_CATEGORIES = [SOFTWARE_ENGINEERING, AI_ML, HR, MARKETING, SALES]

# how many candidates to generate from each category, in order (sums to 30)
CATEGORY_COUNTS = [10, 6, 5, 5, 4]

JOB_TEMPLATES = [
    dict(
        title="Senior Python AI Engineer",
        category="ai",
        department="Engineering",
        location="Ho Chi Minh City",
        requirements=(
            "5+ years experience\nStrong Python\nExperience with FastAPI\nExperience with RAG\n"
            "Experience with LLM\nExperience with vector databases"
        ),
        preferred_requirements="Experience with LangChain\nExperience with Qdrant\nEnglish communication",
        status="OPEN",
    ),
    dict(
        title="Senior Backend Engineer",
        category="software",
        department="Engineering",
        location="Hanoi",
        requirements="4+ years experience\nStrong Python or Java\nExperience with FastAPI or Spring Boot\nPostgreSQL\nDocker",
        preferred_requirements="AWS\nKubernetes\nMicroservices",
        status="OPEN",
    ),
    dict(
        title="Talent Acquisition Specialist",
        category="hr",
        department="People",
        location="Ho Chi Minh City",
        requirements="2+ years experience\nRecruiting\nSourcing\nInterviewing",
        preferred_requirements="HRIS\nEmployer Branding",
        status="OPEN",
    ),
    dict(
        title="Digital Marketing Manager",
        category="marketing",
        department="Marketing",
        location="Da Nang",
        requirements="3+ years experience\nSEO\nGoogle Ads\nContent Marketing",
        preferred_requirements="Marketing Analytics\nBrand Management",
        status="OPEN",
    ),
    dict(
        title="Business Development Manager",
        category="sales",
        department="Sales",
        location="Remote",
        requirements="3+ years experience\nB2B Sales\nNegotiation\nCRM",
        preferred_requirements="Salesforce\nAccount Management",
        status="DRAFT",
    ),
]

LABELS = [
    ("AI Engineer", "#6366f1"),
    ("Backend", "#0ea5e9"),
    ("Frontend", "#8b5cf6"),
    ("Senior", "#f59e0b"),
    ("Potential Hire", "#22c55e"),
    ("High Priority", "#ef4444"),
    ("Interview Later", "#a855f7"),
    ("Rejected Previously", "#64748b"),
    ("HR", "#ec4899"),
    ("Sales", "#14b8a6"),
]
