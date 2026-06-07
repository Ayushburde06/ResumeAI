import re
import json
from typing import NamedTuple

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "we", "you", "they", "he", "she", "it", "i", "our", "your", "their",
    "this", "that", "these", "those", "what", "which", "who", "how",
    "when", "where", "why", "all", "each", "every", "both", "either",
    "not", "no", "nor", "so", "yet", "than", "as", "if", "while",
    "about", "above", "after", "also", "any", "because", "before",
    "between", "during", "into", "must", "only", "other", "such",
    "through", "under", "very", "well", "within", "without", "work",
    "experience", "job", "position", "role", "candidate", "apply",
    "looking", "seeking", "strong", "excellent", "good", "ability",
    "skills", "knowledge", "including", "required", "preferred",
    "qualifications", "responsibilities", "following", "please",
    "opportunity", "team", "company", "organization", "highly", "key",
    "leverage", "implement", "design", "orchestrate", "building",
    "using", "extensive", "performance", "speed",
    # Generic verbs not meaningful as standalone keywords
    "develop", "developed", "developing", "create", "created", "creating",
    "support", "use", "used", "manage", "managed", "ensure", "ensuring",
    "provide", "providing", "maintain", "maintaining",
}

# Comprehensive tech bigrams used in modern JDs
TECH_BIGRAMS = {
    # AI / ML
    "machine learning", "deep learning", "natural language", "natural language processing",
    "computer vision", "artificial intelligence", "large language models", "reinforcement learning",
    # Data
    "data science", "data analysis", "data engineering", "data pipelines",
    "business intelligence", "data visualization", "data warehouse",
    # Software Engineering
    "software engineering", "software development", "software architecture",
    "full stack", "front end", "back end", "rest api", "rest apis",
    "api design", "microservices architecture", "distributed systems",
    "software development lifecycle", "system design",
    # DevOps / Cloud
    "continuous integration", "continuous deployment", "continuous delivery",
    "cloud computing", "cloud services", "cloud infrastructure",
    "infrastructure as code", "site reliability", "version control",
    # Project / Product
    "product management", "project management", "agile methodology",
    "agile development", "scrum master", "test driven", "behavior driven",
    # UX
    "user experience", "user interface", "user research",
    # Security
    "application security", "network security", "penetration testing",
    # Platforms
    "amazon web services", "google cloud", "azure cloud",
    "kubernetes cluster", "container orchestration",
    # DB
    "relational database", "nosql database", "database optimization",
    "sql queries", "query optimization",
    # Misc tech
    "object oriented", "object oriented programming", "functional programming",
    "event driven", "domain driven", "type safety",
    "open source", "code review", "technical documentation",
}

# Irregular verb → root mapping for better stemming
IRREGULAR_VERBS: dict[str, str] = {
    "built": "build", "wrote": "write", "ran": "run", "led": "lead",
    "drove": "drive", "oversaw": "oversee", "grew": "grow", "made": "make",
    "implemented": "implement", "integrated": "integrate", "migrated": "migrate",
    "deployed": "deploy", "designed": "design", "architected": "architect",
    "optimized": "optimize", "refactored": "refactor", "automated": "automate",
    "developed": "develop", "created": "create", "maintained": "maintain",
    "managed": "manage", "improved": "improve", "reduced": "reduce",
    "increased": "increase", "delivered": "deliver", "launched": "launch",
    "collaborated": "collaborate", "contributed": "contribute",
    "spearheaded": "spearhead", "orchestrated": "orchestrate",
    "leveraged": "leverage", "accelerated": "accelerate",
}


class ATSResult(NamedTuple):
    score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    total_keywords: int


def _tokenize(text: str) -> set[str]:
    text_lower = text.lower()
    words = re.findall(r"\b[a-z][a-z0-9+#\-.]{1,}\b", text_lower)
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}


def _extract_bigrams(text: str) -> set[str]:
    text_lower = text.lower()
    found = set()
    for bigram in TECH_BIGRAMS:
        if bigram in text_lower:
            found.add(bigram)
    return found


TECH_UNIGRAMS = {
    # Languages
    "python", "javascript", "typescript", "golang", "go", "rust", "java", "ruby", "php", "swift", "kotlin", "scala",
    "c++", "c#", "solidity", "perl", "r", "julia", "haskell",
    # Frameworks / Libraries
    "fastapi", "django", "flask", "react", "angular", "vue", "svelte", "nextjs", "express", "spring", "nodejs",
    "redux", "webpack", "vite", "nuxt", "nest", "nestjs", "pytorch", "tensorflow", "keras", "pandas", "numpy", "scipy",
    "scikit-learn", "sk-learn", "spark", "hadoop", "pyspark", "opencv", "nltk", "spacy", "huggingface",
    # Cloud & DevOps
    "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "terraform", "ansible", "jenkins", "git", "github", "gitlab",
    "helm", "argocd", "datadog", "prometheus", "grafana", "splunk", "cloudflare", "nginx", "apache",
    # Databases & Caching
    "sql", "nosql", "mysql", "postgres", "postgresql", "mongodb", "redis", "elasticsearch", "graphql", "cassandra",
    "mariadb", "sqlite", "dynamodb", "firebase", "supabase", "snowflake", "redshift", "bigquery", "oracle", "kafka", "rabbitmq",
    # Core concepts
    "html", "css", "sass", "tailwind", "bootstrap", "linux", "unix", "bash", "powershell", "ci", "cd", "cicd",
    "qa", "testing", "automation", "serverless", "microservices", "frontend", "backend", "fullstack", "devops", "mldevops", "mlops"
}


def _extract_capitalized_tech(jd_text: str) -> set[str]:
    tech = set()
    lines = jd_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Remove leading bullet points or numbers
        line = re.sub(r'^[\s\-\*\•\d\.\)]+', '', line).strip()
        words = line.split()
        if len(words) > 1:
            for w in words[1:]:
                # Clean punctuation from the word edges
                cleaned = re.sub(r'^[^a-zA-Z0-9+#\-]+|[^a-zA-Z0-9+#\-]+$', '', w)
                if cleaned and cleaned[0].isupper() and cleaned.lower() not in STOP_WORDS:
                    tech.add(cleaned.lower())
    return tech


def get_resume_plain_text(resume: dict | str) -> str:
    if isinstance(resume, str):
        try:
            resume = json.loads(resume)
        except Exception:
            return resume
            
    if not isinstance(resume, dict):
        return str(resume)

    parts = []
    # personal info
    pi = resume.get("personal_info", {})
    if isinstance(pi, dict):
        parts.extend([pi.get("name", ""), pi.get("location", "")])
    
    # summary
    parts.append(resume.get("summary", ""))
    
    # experience
    for exp in resume.get("experience", []):
        if isinstance(exp, dict):
            parts.extend([exp.get("title", ""), exp.get("company", ""), exp.get("location", "")])
            bullets = exp.get("bullets", [])
            if isinstance(bullets, list):
                parts.extend(bullets)
            
    # education
    for edu in resume.get("education", []):
        if isinstance(edu, dict):
            parts.extend([edu.get("institution", ""), edu.get("degree", ""), edu.get("location", ""), edu.get("honors", "")])
            
    # skills
    skills = resume.get("skills", {})
    if isinstance(skills, dict):
        for k, v in skills.items():
            if isinstance(v, list):
                parts.extend(v)
            elif isinstance(v, str):
                parts.append(v)
                
    # certifications
    for cert in resume.get("certifications", []):
        if isinstance(cert, dict):
            parts.extend([cert.get("name", ""), cert.get("issuer", "")])
            
    # projects
    for proj in resume.get("projects", []):
        if isinstance(proj, dict):
            parts.extend([proj.get("name", ""), proj.get("description", "")])
            tech = proj.get("tech_stack", [])
            if isinstance(tech, list):
                parts.extend(tech)
            
    return "\n".join(str(p) for p in parts if p)


def _extract_jd_keywords(jd_text: str) -> set[str]:
    # Extract unigrams
    words = re.findall(r"\b[a-z][a-z0-9+#\-.]{1,}\b", jd_text.lower())
    freq: dict[str, int] = {}
    for w in words:
        if w not in STOP_WORDS and len(w) > 2:
            freq[w] = freq.get(w, 0) + 1
            
    # Only keep keywords mentioned 2+ times, or in TECH_UNIGRAMS, or capitalized technology names, or in bigrams
    high_freq = {w for w, c in freq.items() if c >= 2}
    tech_unigrams = {w for w in freq if w in TECH_UNIGRAMS}
    cap_tech = _extract_capitalized_tech(jd_text)
    bigrams = _extract_bigrams(jd_text)
    
    return high_freq | tech_unigrams | cap_tech | bigrams


def _stem(word: str) -> str:
    """Normalize a word to its root form using irregular verb map + suffix stripping."""
    w = word.lower()
    # Check irregular verb map first
    if w in IRREGULAR_VERBS:
        return IRREGULAR_VERBS[w]
    # Suffix stripping (order matters — longest suffixes first)
    for suffix in ("ments", "ment", "tions", "tion", "ings", "ing", "ers", "er", "ies", "es", "ed", "ly", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[:-len(suffix)]
    return w


def compute_ats_score(resume_text: str, jd_text: str) -> ATSResult:
    plain_text = get_resume_plain_text(resume_text)
    jd_keywords = _extract_jd_keywords(jd_text)
    resume_tokens = _tokenize(plain_text)
    resume_stems = {_stem(t) for t in resume_tokens}
    resume_text_lower = plain_text.lower()

    matched = []
    missing = []

    for kw in sorted(jd_keywords):
        if " " in kw:
            # Exact bigram match first
            found = kw in resume_text_lower
            if not found:
                # Stem-level match on each part of the bigram
                parts = kw.split()
                found = all(_stem(p) in resume_stems for p in parts)
        else:
            found = _stem(kw) in resume_stems or kw in resume_tokens

        if found:
            matched.append(kw)
        else:
            missing.append(kw)

    total = len(jd_keywords)
    if total == 0:
        return ATSResult(score=0, matched_keywords=[], missing_keywords=[], total_keywords=0)

    raw_score = len(matched) / total * 100
    # Scoring curve tuned for well-optimised AI resumes:
    # A resume that covers 80%+ of JD keywords should display 90%+.
    if raw_score >= 88:
        score = min(98, int(raw_score + 7))   # 88→95, 91→98
    elif raw_score >= 78:
        score = min(94, int(raw_score + 10))  # 78→88, 82→92, 84→94
    elif raw_score >= 65:
        score = min(87, int(raw_score + 13))  # 65→78, 72→85
    else:
        score = min(78, int(raw_score + 16))  # 50→66, 62→78

    return ATSResult(
        score=score,
        matched_keywords=sorted(matched),
        missing_keywords=sorted(missing),
        total_keywords=total,
    )
