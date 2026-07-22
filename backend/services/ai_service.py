import ast
import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Model Registry ────────────────────────────────────────────────────────

MODEL_REGISTRY: dict[str, dict] = {}
_clients: dict[str, OpenAI] = {}


_PLACEHOLDER_FRAGMENTS = ("YOUR_", "_HERE", "CHANGE_THIS", "placeholder", "example")


def _is_placeholder(value: str) -> bool:
    return not value or any(p in value for p in _PLACEHOLDER_FRAGMENTS)


def _parse_json_response(content: str) -> dict:
    """Safely parse JSON/dict from LLM response, handling markdown blocks and single quotes."""
    if not content:
        raise ValueError("Empty response from AI model")
    content = content.strip()

    if "```" in content:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
        else:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start : end + 1]

    # Strategy 1: Standard json.loads
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"data": data}
    except Exception:
        pass

    # Strategy 2: Robust search for valid JSON object by finding valid matching braces
    start_idx = 0
    while True:
        start = content.find("{", start_idx)
        if start == -1:
            break
        
        end_idx = len(content)
        while True:
            end = content.rfind("}", start, end_idx)
            if end <= start:
                break
            
            blob = content[start:end+1]
            try:
                data = json.loads(blob)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
            
            # Strategy 3: ast.literal_eval for single-quoted Python dicts
            try:
                evaluated = ast.literal_eval(blob)
                if isinstance(evaluated, dict):
                    return evaluated
            except Exception:
                pass
            
            # Strategy 4: Clean single quotes / trailing commas with regex
            try:
                cleaned = re.sub(r",\s*([\}\]])", r"\1", blob)
                cleaned = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', cleaned)
                data = json.loads(cleaned)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
            
            end_idx = end
        
        start_idx = start + 1

    # Strategy 5: ast.literal_eval on full content
    try:
        evaluated = ast.literal_eval(content)
        if isinstance(evaluated, dict):
            return evaluated
    except Exception:
        pass

    raise ValueError(f"Could not parse valid JSON from AI output: {content[:100]}...")


def _register_models():
    """Build model registry from environment variables."""
    global MODEL_REGISTRY
    MODEL_REGISTRY = {}


    # Kimi 2.5
    kimi_key = os.environ.get("KIMI_API_KEY", "")
    if not _is_placeholder(kimi_key):
        MODEL_REGISTRY["kimi"] = {
            "id": "kimi",
            "display_name": "Kimi 2.5",
            "endpoint": os.environ.get("KIMI_ENDPOINT", "https://bedrock-mantle.us-east-1.api.aws/v1"),
            "api_key": kimi_key,
            "model": os.environ.get("KIMI_MODEL", "moonshotai.kimi-k2.5"),
        }

    # GLM-5
    glm_key = os.environ.get("GLM_API_KEY", "")
    glm_endpoint = os.environ.get("GLM_ENDPOINT", "https://bedrock-mantle.us-east-1.api.aws/v1")
    if not _is_placeholder(glm_key) and glm_endpoint:
        MODEL_REGISTRY["glm"] = {
            "id": "glm",
            "display_name": "GLM-5 (Recommended)",
            "endpoint": glm_endpoint,
            "api_key": glm_key,
            "model": os.environ.get("GLM_MODEL", "zai.glm-5"),
        }

    # Qwen3 Next 80B
    qwen_key = os.environ.get("QWEN_API_KEY", "")
    if not _is_placeholder(qwen_key):
        MODEL_REGISTRY["qwen"] = {
            "id": "qwen",
            "display_name": "Qwen3 Next 80B",
            "endpoint": os.environ.get("QWEN_ENDPOINT", "https://bedrock-mantle.us-east-1.api.aws/v1"),
            "api_key": qwen_key,
            "model": os.environ.get("QWEN_MODEL", "qwen.qwen3-next-80b-a3b-instruct"),
        }

    # MiniMax m2.5
    minimax_key = os.environ.get("MINIMAX_API_KEY", "")
    if not _is_placeholder(minimax_key):
        MODEL_REGISTRY["minimax"] = {
            "id": "minimax",
            "display_name": "MiniMax m2.5",
            "endpoint": os.environ.get("MINIMAX_ENDPOINT", "https://bedrock-mantle.us-east-1.api.aws/v1"),
            "api_key": minimax_key,
            "model": os.environ.get("MINIMAX_MODEL", "minimax.minimax-m2.5"),
        }




_register_models()


def get_available_models(is_admin: bool = False) -> list[dict]:
    """Return list of available models for the frontend.
    Admin-only models are hidden from regular users.
    """
    default_id = os.environ.get("DEFAULT_MODEL_ID", "glm")
    models = []
    for mid, cfg in MODEL_REGISTRY.items():
        if cfg.get("admin_only") and not is_admin:
            continue
        models.append({
            "id": mid,
            "display_name": cfg["display_name"],
            "is_default": mid == default_id,
        })
    return models


def _normalize_endpoint(raw: str) -> str:
    endpoint = raw.strip().rstrip("/")
    for suffix in ("/models/chat/completions", "/chat/completions"):
        if endpoint.endswith(suffix):
            endpoint = endpoint[: -len(suffix)]
    return endpoint


def _mask_secrets(text: str) -> str:
    """Replace any live API key values in error messages with [REDACTED]."""
    for cfg in MODEL_REGISTRY.values():
        key = cfg.get("api_key", "")
        if key and len(key) > 8 and key in text:
            text = text.replace(key, "[REDACTED]")
    return text


def _get_client(model_id: str | None = None) -> tuple[OpenAI, str]:
    """Return (client, model_name) for the given model_id."""
    if not model_id:
        model_id = os.environ.get("DEFAULT_MODEL_ID", "glm")

    if model_id not in MODEL_REGISTRY:
        if MODEL_REGISTRY:
            model_id = next(iter(MODEL_REGISTRY))
        else:
            raise RuntimeError("No AI models configured. Check your environment variables.")

    cfg = MODEL_REGISTRY[model_id]

    if model_id not in _clients:
        endpoint = _normalize_endpoint(cfg["endpoint"])
        base_url = endpoint if endpoint.endswith("/") else endpoint + "/"
        _clients[model_id] = OpenAI(
            base_url=base_url,
            api_key=cfg["api_key"],
            timeout=45.0,      # reduced from 90s — prevents 180s stall on hung calls
            max_retries=1,
        )

    return _clients[model_id], cfg["model"]


def _get_cheap_client(preferred_model_id: str | None = None) -> tuple[OpenAI, str]:
    """
    Return a client for low-stakes calls (gap analysis, planning, extraction).
    Prefers glm → kimi → qwen → minimax → first available model.
    Falls back to the user-selected model if no cheap model is registered.
    """
    _CHEAP_PREFERENCE = ["glm", "kimi", "qwen", "minimax"]
    for candidate in _CHEAP_PREFERENCE:
        if candidate in MODEL_REGISTRY:
            return _get_client(candidate)
    # Fall back to user-selected model
    return _get_client(preferred_model_id)


def get_embedding(text: str, model_id: str | None = None) -> list[float]:
    """Generate dense embeddings using the API.
    Defaults to the amazon.titan-embed-text-v1 model as requested for dense vector search."""
    client, _ = _get_cheap_client(model_id)
    embed_model = os.environ.get("EMBEDDING_MODEL", "amazon.titan-embed-text-v1")
    response = client.embeddings.create(
        input=[text.replace("\n", " ")],
        model=embed_model
    )
    return response.data[0].embedding


# ── Prompts ──────────────────────────────────────────────────────────────────
# Key philosophy: genuine, simple, human-readable resumes.
# No fancy buzzwords. No bluff. Clean formatting. ATS-optimized but HR-friendly.

JOB_SEARCH_SUGGESTION_SYSTEM = """You are an expert technical recruiter and career coach.
Your task is to analyze a candidate's resume and determine the BEST job search query and location to find relevant job openings for them.

Analyze the resume and return a JSON object with:
- "search_term": A 1 to 3 word job title that best fits the candidate's most recent experience and skills (e.g., "Software Engineer", "Data Analyst", "Product Manager", "Frontend Developer"). Be specific but standard enough to get good search results.
- "location": The candidate's city and state/country based on their contact info or most recent job (e.g., "New York, NY", "London, UK", "Remote"). If no location is found, return "".

Format exactly as JSON:
{{
  "search_term": "...",
  "location": "..."
}}"""

ANALYSIS_SYSTEM = """You are an expert recruiter with 15+ years of experience reading resumes.
Analyse a job description and extract structured requirements.
Return ONLY valid JSON — no markdown, no commentary."""

ANALYSIS_PROMPT = """Analyse this job description and return JSON.
Be exhaustive — extract every specific term, technology, tool, methodology, and phrase that an ATS system would score.

{{
  "job_title": "...",
  "job_category": "Backend SWE / Frontend SWE / Full Stack SWE / Data Science / ML Engineering / Data Engineering / DevOps / Mobile / QA / Security / Product / Design / Other",
  "company_type": "startup/enterprise/agency/research/consultancy/...",
  "seniority": "intern/junior/mid/senior/lead/principal/staff",
  "hr_tone": "startup (informal, practical, ship-fast culture) / enterprise (formal, process-heavy, metric-driven) / research (depth-first, methodology-focused, academic)",
  "required_skills": ["every hard skill explicitly required — include exact names like 'Node.js', 'PostgreSQL', 'REST API'"],
  "preferred_skills": ["nice-to-have skills explicitly mentioned"],
  "key_responsibilities": ["core duties described in the JD — use exact JD phrasing"],
  "industry_keywords": ["domain-specific terms, methodologies, patterns — e.g. 'microservices', 'CI/CD', 'Agile', 'SDLC'"],
  "tone": "formal/casual/technical/...",
  "must_have": ["hard requirements that MUST appear on the resume — degrees, certs, specific tools"],
  "exact_keywords": ["every specific term worth ATS-matching: tool names, framework names, language names, methodology names, certification names — include both common variants e.g. 'Node.js' AND 'NodeJS', 'REST API' AND 'RESTful API', 'JavaScript' AND 'JS' where both appear in the JD"],
  "keyword_density_targets": ["top 6-8 highest-priority keywords to cover naturally in the resume — avoid repeating across every section"],
  "rewrite_strategy": "one sentence: what to prioritize in the rewrite based on the JD requirements and seniority level"
}}

JOB DESCRIPTION:
{jd}"""


BASE_SYSTEM_INSTRUCTIONS = """You are an Elite Resume Architect, ATS Optimization Specialist, and Senior Technical Recruiter with 20+ years of hiring experience for top product companies.
Your mission is to maximize interview callback probability while keeping every statement 100% truthful.
Outputs must feel like they were written by an experienced human recruiter, not AI.

TARGET OBJECTIVES:
- ATS Score Target: 90–95% (NEVER target 100%, never keyword stuff; natural language and recruiter scanning take top priority).
- Recruiter Ergonomics: Optimized for a 6–10 second skim.

ABSOLUTE RULES:
- Never invent: Experience, Companies, Projects, Numbers, Skills, Certifications, Achievements, Dates, Responsibilities.
- Never exaggerate or remove truthful technical information.
- BANNED AI PHRASES & BUZZWORDS (never use): leveraged, utilized, harnessed, facilitated, showcased, demonstrated ability to, highly motivated, results-driven, dynamic professional, passionate, hardworking, dedicated, self motivated, team player, quick learner, spearheaded, orchestrated, synergized, revolutionized, pioneered, championed, dynamic, details-oriented, fast learner, furthermore, moreover, it should be noted, as a result of, in an effort to, developed and implemented, built and deployed.
- PREFERRED ACTIVE VERBS: built, designed, developed, created, implemented, optimized, integrated, automated, reduced, improved, delivered, engineered, refactored, deployed.
- KEYWORD & METRIC BOLDING IN BULLETS — follow this strict order, max 2–3 bold groups per bullet:
    1. JD-REQUIRED KEYWORDS (highest priority): If a target JD is provided, wrap direct JD skill/tech matches in **term** first.
    2. QUANTIFIABLE METRICS: Wrap ALL measurable results in **term** — e.g. **45% latency reduction**, **10M+ daily users**, **$500K revenue**.
    3. CORE TECH STACK: Wrap the 1–2 most important technologies or tools used in the bullet in **term**.
    - HARD LIMITS: Max 2–3 **bold** groups per bullet. Never bold an entire phrase or sentence. NEVER bold action verbs (built, designed, implemented, etc.) — only the technology, metric, or JD keyword. If a term is already bolded once in a bullet, do NOT bold it again.
    - EXAMPLE: "Engineered microservices in **Python** and **FastAPI** reducing API latency by **45%** serving 10M+ daily requests." (3 groups: 2 tech + 1 metric — stop here).
- If content cannot honestly be improved, leave it unchanged.
- VARY bullet openers — never start 3+ bullets with the same verb.

PROFESSIONAL SUMMARY (1–3 CONCISE LINES):
- Include: Current Role, Experience Level, Core Technologies, Domain Expertise, Business Value, and Career Focus.
- Natural recruiter tone. No generic self-praise buzzwords.

PROFESSIONAL EXPERIENCE (3–5 IMPACT-DRIVEN BULLETS PER ROLE):
- Every bullet formula: [Strong Action Verb] + [Task] + [**JD-Keyword/Technology**] + [**Measurable Impact/Metric**].
- Bold ONLY: (1) JD-required keywords/tools, (2) quantifiable metrics, (3) 1-2 core tech used. MAX 2-3 **bolds** per bullet.
- NEVER bold action verbs (built, designed, implemented, etc.) — only the tech, metric, or JD keyword gets bolded.
- Each bullet answers: What was built? How was it built? What business or technical impact did it create?
- NEVER begin bullets with: Worked on, Responsible for, Helped, Participated in, Involved in.

PROJECTS (3–4 TECHNICAL BULLETS PER PROJECT):
- Line 1: WHY project exists (one-line value proposition / architecture problem).
- Line 2: HOW it was built (deep technical implementation & stack with **bold** key terms).
- Line 3–4: WHAT impact or functionality it delivers (bold metrics, users, deployment, test coverage).

TECHNICAL SKILLS:
- Group into logical categories sorted by Job Description relevance: Languages, Frontend, Backend, Frameworks, Databases, Cloud, DevOps, AI / ML, Tools, Concepts."""

REWRITE_SYSTEM = BASE_SYSTEM_INSTRUCTIONS + "\n\nFocus mainly on projects, bullet quality, and ATS readability."

REWRITE_PROMPT = """Improve and tailor the candidate's resume for this role using the system rules.
Focus mainly on projects, bullet quality, and ATS readability.

{keyword_injection}

EXISTING RESUME:
{resume}

JOB ANALYSIS:
{job_analysis}

Return JSON with EXACTLY this shape:
{{
  "personal_info": {{
    "name": "...", "email": "...", "phone": "...", "location": "...",
    "linkedin": "...", "github": "...", "website": "..."
  }},
  "summary": "1-3 concise lines in natural recruiter tone covering current role, exp level, core stack, domain expertise, business value, and career focus.",
  "experience": [{{
    "title": "...", "company": "...", "location": "...",
    "start_date": "Mon YYYY", "end_date": "Mon YYYY or Present",
    "bullets": ["Bullet 1: Verb + Task + Tech + Impact", "Bullet 2: Verb + Task + Tech + Impact", "Bullet 3: Verb + Task + Tech + Impact", "Bullet 4 (optional)", "Bullet 5 (optional)"]
  }}],
  "education": [{{
    "degree": "...", "institution": "...", "location": "...",
    "graduation_year": "YYYY", "gpa": "...", "honors": "..."
  }}],
  "skills": {{"Languages": [...], "Frontend": [...], "Backend": [...], "Frameworks": [...], "Databases": [...], "Cloud": [...], "DevOps": [...], "AI / ML": [...], "Tools": [...], "Concepts": [...]}},
  "certifications": [{{"name": "...", "issuer": "...", "year": "..."}}],
  "projects": [{{
    "name": "...",
    "bullets": ["Bullet 1: WHY project exists / architecture value prop", "Bullet 2: HOW it was built + stack & implementation", "Bullet 3: WHAT impact or functionality it delivers", "Bullet 4 (optional): Performance / testing / deployment metric"],
    "description": "Bullet 1\\nBullet 2\\nBullet 3",
    "tech_stack": [...],
    "link": "...", "live_link": "..."
  }}]
}}
Leave fields as "" or [] if the original has no data. Never invent companies or credentials."""


ATS_IMPROVE_SYSTEM = BASE_SYSTEM_INSTRUCTIONS + "\n\nFocus on improving ATS keyword coverage by naturally integrating missing keywords."

ATS_IMPROVE_PROMPT = """Your goal: improve ATS coverage by integrating ALL of the missing keywords below.
Every keyword MUST appear verbatim in the returned resume — do not skip any, do not paraphrase.

MISSING KEYWORDS — integrate EACH one (verbatim, exact casing) into the most natural section:
{missing_keywords}

KEYWORD DENSITY TARGETS:
{density_targets}

CURRENT RESUME (JSON):
{resume}

JOB ANALYSIS:
{job_analysis}

Return the improved resume with the EXACT same JSON shape including the 7 skills categories:
{{"personal_info": ..., "summary": ..., "experience": ..., "education": ..., "skills": {{"Languages": [...], "Frontend": [...], "Backend": [...], "Databases": [...], "Cloud & DevOps": [...], "Tools": [...], "Concepts": [...]}}, "certifications": ..., "projects": ...}}"""


COVER_LETTER_SYSTEM = """You write cover letters for fresh graduates and early-career developers.
Your letters are SHORT, real, and specific. A recruiter reads one in 20 seconds and thinks "this person fits."

STRUCTURE — exactly 3 paragraphs, nothing more:

P1 — WHO + WHY THIS ROLE (2 sentences):
- Sentence 1: one line on who the candidate is — their degree or their most recent role, plainly stated.
- Sentence 2: one specific thing from the JD that made them apply — name it (a technology, a product type, a problem the company solves). Not "I am interested in this opportunity."

P2 — PROOF (3 sentences max):
- Name 2 real projects or experiences from the resume. For each say what was built and which JD requirement it covers.
- Be blunt and factual. "Built X using Y, which covers Z requirement from the JD" is better than vague claims.

P3 — CLOSE (1 sentence):
- State one concrete thing the candidate brings to this team. End with what they want (a quick call, an interview).
- No "thank you for your time." No "I look forward to hearing from you." Just a clean, direct sentence.

ABSOLUTE BANS — if any of these words appear, rewrite:
passionate, excited, thrilled, eager, leverage, synergy, spearhead, results-driven, team player,
quick learner, dynamic, hardworking, proven track record, I am writing to apply, I am pleased,
I would like to express, I look forward to hearing from you, Thank you for your consideration.

TONE: plain everyday English. Short sentences. No adjectives about yourself — let the work prove it.
WORD COUNT: 120–150 words. Hard limit. Count before returning.
Return ONLY valid JSON — no markdown, no extra keys."""

COVER_LETTER_PROMPT = """Write a cover letter for {name} applying for {job_title}.

RESUME:
Summary: {summary}
Experience: {experience}
Projects: {projects}
Skills: {skills}

JOB REQUIREMENTS (from JD analysis — map resume work to these):
{job_analysis}

TEMPLATE GUIDANCE (align writing style and tone with these examples):
{rag_context}

CHECKLIST before returning:
[ ] Exactly 3 paragraphs
[ ] 120–150 words total
[ ] 2 real project/experience names from resume above
[ ] 1 specific JD requirement or tech named in P2
[ ] Zero banned words
[ ] Sounds like a person, not a template

Return JSON:
{{
  "subject_line": "Application for {job_title} — {name}",
  "body": "paragraph 1\\n\\nparagraph 2\\n\\nparagraph 3"
}}"""

APPLICATION_EMAIL_SYSTEM = """You write short, professional, and high-impact cold application emails to hiring managers or recruiters.
Your emails are simple, direct, and under 100 words. They immediately state the candidate's core stack and relevance to the position.

STRUCTURE — exactly 3 paragraphs:
P1: Introduce yourself and state the exact role you're applying for. (1-2 sentences)
P2: Call out 1-2 core technologies or projects from your resume that directly align with the job description's main requirements. Keep it factual and brief. (1-2 sentences)
P3: Call to action. Ask if they have 5 minutes for a brief call, or suggest reviewing the attached resume. Keep it clean and polite. (1 sentence)

ABSOLUTE BANS:
Do NOT use overly enthusiastic words: passionate, excited, thrilled, eager, leverage, synergy, spearhead, results-driven, team player, quick learner.
No "thank you for your time." No "I look forward to hearing from you." Just a clean, direct sign-off.

TONE: Professional, confident, concise, and human-written. Simple everyday English.
Return ONLY valid JSON — no markdown, no extra keys."""

APPLICATION_EMAIL_PROMPT = """Write a short job application email for {name} applying for {job_title}.

RESUME SUMMARY: {summary}
KEY SKILLS: {skills}
EXPERIENCE/PROJECT SUMMARY: {experience_projects}

JOB DESCRIPTION SUMMARY:
{job_analysis}

COMMUNICATION PATTERNS (align tone and style with these best practices):
{rag_context}

Return JSON with this exact shape:
{{
  "subject_line": "...",
  "body": "..."
}}"""


# ── Post-processing ───────────────────────────────────────────────────────────

# Hard ban list — anything matching these strings is stripped from skills regardless of AI output
_BANNED_SKILLS = {
    # Generic filler phrases
    "modern technologies", "technical tools", "systems", "products", "projects",
    "requirements", "practices", "overview", "software development",
    "cloud infrastructure", "best practices", "development tools",
    "web development", "application development", "cross-functional",
    "agile development", "nosql database", "modern", "technologies",
    "technical", "development", "infrastructure", "scalable",
    "performance", "speed", "building", "extensive", "advanced",
    "professional", "strong", "excellent", "proven", "hands-on",
    "experience", "knowledge", "understanding", "proficiency",
    "expertise", "proficient", "familiar", "skilled",
    # Soft skills / personality traits — belong in interviews, not skills sections
    "problem-solving", "problem solving", "analytical skills", "analytical thinking",
    "team collaboration", "collaboration", "communication", "communication skills",
    "interpersonal skills", "leadership", "teamwork", "time management",
    "critical thinking", "attention to detail", "adaptability", "creativity",
    "work ethic", "self-motivated", "self motivated", "quick learner",
    "fast learner", "detail-oriented", "detail oriented", "proactive",
    "multitasking", "organizational skills", "presentation skills",
    # Testing generics (should be specific: "Jest", "Pytest", not generic "testing")
    "testing", "unit testing", "integration testing", "automated testing",
    "unit test", "integration test", "test automation", "testing frameworks",
    "quality assurance",
    # Generic web/programming concepts that aren't skills
    "http", "json", "xml", "front-end", "back-end", "frontend", "backend",
    "full-stack", "fullstack", "server-side programming", "web and server-side programming",
    "client-side", "server-side", "web programming", "web applications",
    # Business / management jargon
    "digital transformation", "enterprise software", "enterprise software services",
    "cloud engineering services", "mobility solutions", "cloud services",
    "session management", "extensibility", "reusable components",
    "best development practices", "software development lifecycle",
}


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = re.sub(r"\s+", " ", str(item).replace("**", "").strip()).lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped


def _trim_to_two_sentences(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text.strip())
    if len(parts) <= 2:
        return text.strip()
    return " ".join(parts[:2]).strip()


def _extract_original_vocab(resume_text: str) -> set:
    """
    Build a normalised vocabulary set from the original resume text.
    Used to detect skills the AI invented that were never in the source.
    """
    text_lower = resume_text.lower()
    raw_tokens = re.split(r'[\s,|·•\-/\(\)\[\]{}:;\n\t]+', text_lower)
    vocab: set = set()
    for tok in raw_tokens:
        tok = tok.strip('.,!?"\'+_@#$%^&*=<>~`')
        if not tok or len(tok) < 2:
            continue
        vocab.add(tok)
        # Add suffix-stripped variants: react.js → react, node.js → node
        for suffix in ('.js', '.py', '.ts', '.go', '.rb', '.rs', '.cs', '.io', '.net'):
            if tok.endswith(suffix):
                vocab.add(tok[: -len(suffix)])
        # Add digit-stripped variant: python3 → python, node18 → node
        base = re.sub(r'\d+', '', tok).strip()
        if base and len(base) >= 2:
            vocab.add(base)
    return vocab


def _skill_in_original(skill: str, vocab: set) -> bool:
    """
    Return True if at least one meaningful token of `skill` is found
    in the original resume vocabulary.
    Short known abbreviations (AWS, SQL, …) are always allowed.
    """
    _ALWAYS_ALLOW = {
        "aws", "gcp", "sql", "git", "api", "jwt", "css", "html",
        "php", "ios", "k8s", "ci", "cd", "ai", "ml", "dl", "nlp",
        "c++", "c#", "r", "go", "vue", "rds", "sas", "orm",
    }
    skill_lower = skill.lower()
    tokens = re.split(r'[\s,\-/\.\(\)\+&]+', skill_lower)
    for tok in tokens:
        tok = tok.strip()
        if not tok or len(tok) < 2:
            continue
        if tok in _ALWAYS_ALLOW:
            return True
        if tok in vocab:
            return True
        base = re.sub(r'\d+', '', tok).strip()
        if base and len(base) >= 2 and base in vocab:
            return True
    return False


def _clean_resume(resume: dict, original_text: str | None = None) -> dict:
    """Post-process AI output to remove filler skills and enforce formatting.
    When `original_text` is supplied, skills not found in the source resume
    are removed to prevent the AI from hallucinating technologies.
    """
    if isinstance(resume.get("summary"), str):
        # Clean markdown formatting from summary without forcing 2-sentence truncation
        resume["summary"] = resume["summary"].replace("**", "").replace("*", "").strip()

    skills = resume.get("skills", {})
    if isinstance(skills, dict):
        categories = ("languages", "frontend", "backend", "frameworks", "databases", "cloud", "devops", "ai / ml", "tools", "concepts")
        category_map = {
            "technical": "languages",
            "soft": "concepts",
            "infra": "cloud",
            "infrastructure": "cloud",
            "cloud & devops": "cloud",
            "ai/ml": "ai / ml",
            "aiml": "ai / ml",
            "machine learning": "ai / ml",
            "agile": "concepts",
            "methodologies": "concepts",
        }

        # Lowercase keys and apply mapping
        normalized_skills = {}
        for k, v in list(skills.items()):
            low_k = k.lower().strip()
            mapped_k = category_map.get(low_k, low_k)
            if mapped_k not in normalized_skills:
                normalized_skills[mapped_k] = []
            normalized_skills[mapped_k].extend(v if isinstance(v, list) else [])

        skills = normalized_skills

        for category in categories:
            items = skills.get(category, [])
            if isinstance(items, list):
                cleaned = []
                for s in items:
                    plain = s.replace("**", "").replace("*", "").strip()
                    if plain.lower() in _BANNED_SKILLS:
                        continue
                    if len(plain) <= 3 and plain.lower() not in {
                        "aws", "gcp", "sql", "git", "c++", "c#", "r", "go",
                        "vue", "ci", "cd", "qa", "ai", "ml", "dl", "nlp",
                        "css", "php", "ios", "api", "k8s", "sas", "rds", "jwt",
                    }:
                        continue
                    cleaned.append(plain)
                limits = {
                    "languages": 8,
                    "frontend": 8,
                    "backend": 8,
                    "frameworks": 8,
                    "databases": 6,
                    "cloud": 7,
                    "devops": 7,
                    "ai / ml": 6,
                    "tools": 8,
                    "concepts": 6,
                }
                skills[category] = _dedupe_keep_order(cleaned)[:limits[category]]

        # Keep valid non-empty categories
        resume["skills"] = {k: skills[k] for k in categories if k in skills and skills[k]}

        # ── Hallucination guard ──────────────────────────────────────────────
        if original_text:
            vocab = _extract_original_vocab(original_text)
            for cat in list(resume["skills"].keys()):
                items = resume["skills"].get(cat, [])
                if isinstance(items, list):
                    filtered = [s for s in items if _skill_in_original(s, vocab)]
                    resume["skills"][cat] = filtered if filtered else items

    # Clean experience bullets (3-5 bullets max per job)
    for exp in resume.get("experience", []):
        if isinstance(exp, dict) and isinstance(exp.get("bullets"), list):
            exp["bullets"] = [b.replace("**", "").replace("*", "").strip() for b in exp["bullets"][:5]]

    # Tech stack pollution filter — strip generic/concept words from project tech stacks
    _BANNED_TECH_STACK = {
        "testing", "unit test", "unit testing", "integration test", "integration testing",
        "automated testing", "web development", "front-end", "back-end", "frontend", "backend",
        "http", "json", "xml", "mvc framework", "mvc", "rest api", "restful api",
        "session management", "extensibility", "reusable components", "best practices",
        "digital transformation", "cloud engineering", "web applications", "web app",
        "problem-solving", "collaboration", "agile", "scrum", "sdlc",
    }

    # Keep projects compact (3-4 bullets max per project)
    for proj in resume.get("projects", []):
        if not isinstance(proj, dict):
            continue
        if isinstance(proj.get("tech_stack"), list):
            cleaned_stack = []
            for t in proj["tech_stack"]:
                plain = t.replace("**", "").replace("*", "").strip()
                if plain.lower() not in _BANNED_TECH_STACK:
                    cleaned_stack.append(plain)
            proj["tech_stack"] = _dedupe_keep_order(cleaned_stack)[:8]

        raw_bullets = proj.get("bullets")
        raw_desc = proj.get("description")
        
        bullets_list = []
        if isinstance(raw_bullets, list) and raw_bullets:
            bullets_list = [b.replace("**", "").replace("*", "").strip() for b in raw_bullets if isinstance(b, str) and b.strip()]
        elif isinstance(raw_desc, list) and raw_desc:
            bullets_list = [d.replace("**", "").replace("*", "").strip() for d in raw_desc if isinstance(d, str) and d.strip()]
        elif isinstance(raw_desc, str) and raw_desc.strip():
            plain_desc = raw_desc.replace("**", "").replace("*", "").strip()
            lines = [l.strip() for l in plain_desc.splitlines() if l.strip()]
            if len(lines) <= 1 and ". " in plain_desc:
                lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain_desc) if s.strip()]
            bullets_list = lines

        if bullets_list:
            final_bullets = bullets_list[:4]
            proj["bullets"] = final_bullets
            proj["description"] = "\n".join(final_bullets)
        else:
            proj["bullets"] = []
            proj["description"] = ""

    return resume


def _extract_content(response) -> str:
    """Safely extract message content or reasoning content from LLM response across providers."""
    if not response or not getattr(response, "choices", None):
        return ""
    msg = response.choices[0].message
    content = getattr(msg, "content", "")
    if not content or not str(content).strip():
        content = getattr(msg, "reasoning", "") or getattr(msg, "reasoning_content", "") or ""
    return str(content).strip()


def _safe_call(fn):
    """Decorator: catches any AI provider exception and scrubs API keys from the message."""
    import functools
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            safe_msg = _mask_secrets(str(exc))
            raise RuntimeError(safe_msg) from None
    return wrapper


@_safe_call
def analyse_job_description(jd_text: str, model_id: str | None = None) -> dict:
    client, model = _get_client(model_id)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ANALYSIS_SYSTEM},
            {"role": "user", "content": ANALYSIS_PROMPT.format(jd=jd_text)},
        ],
        temperature=0.2,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))


@_safe_call
def rewrite_resume(
    resume_text: str,
    jd_text: str,
    job_analysis: dict,
    model_id: str | None = None,
    missing_keywords: list[str] | None = None,
    extra_context: str | None = None,
) -> dict:
    """Rewrite a resume for a job. If missing_keywords are provided (from pre-analysis),
    they are injected directly into the prompt so the model knows exactly what to cover
    on the FIRST pass — dramatically improving first-pass ATS score.
    extra_context: optional block from the learning store (past winning examples)."""
    client, model = _get_client(model_id)

    # Build keyword injection block for first-pass targeting
    if missing_keywords:
        top_kw = missing_keywords[:25]
        keyword_injection = (
            "MANDATORY KEYWORD CHECKLIST — every term below MUST appear verbatim (exact spelling, exact casing) "
            "somewhere in the final resume. Do NOT skip any. Do NOT paraphrase. "
            "Verify each keyword appears before returning:\n"
            + ", ".join(top_kw)
        )
    else:
        keyword_injection = ""

    # Prepend real winning examples as style context (compounding learning loop)
    system_prompt = REWRITE_SYSTEM
    if extra_context:
        system_prompt = extra_context + "\n\n" + REWRITE_SYSTEM

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": REWRITE_PROMPT.format(
                    resume=resume_text,
                    job_analysis=json.dumps(job_analysis),
                    keyword_injection=keyword_injection,
                ),
            },
        ],
        temperature=0.2,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )
    result = _parse_json_response(_extract_content(response))
    # Pass original resume_text so hallucinated skills can be filtered out
    return _clean_resume(result, original_text=resume_text)


@_safe_call
def improve_resume_for_ats(
    resume: dict,
    jd_text: str,
    job_analysis: dict,
    missing_keywords: list[str],
    model_id: str | None = None,
) -> dict:
    client, model = _get_client(model_id)
    density_targets = job_analysis.get("keyword_density_targets", [])
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ATS_IMPROVE_SYSTEM},
            {
                "role": "user",
                "content": ATS_IMPROVE_PROMPT.format(
                    missing_keywords=", ".join(missing_keywords) or "(none)",
                    density_targets=", ".join(density_targets) or "(see job_analysis)",
                    resume=json.dumps(resume),
                    job_analysis=json.dumps(job_analysis),
                ),
            },
        ],
        temperature=0.1,
        max_tokens=5000,    # increased: needs full resume output space + all missing keywords injected
        response_format={"type": "json_object"},
    )
    result = _parse_json_response(_extract_content(response))
    return _clean_resume(result)


@_safe_call
def generate_cover_letter(
    tailored_resume: dict,
    job_analysis: dict,
    jd_text: str = "",
    model_id: str | None = None,
    rag_context: str = "",
) -> dict:
    client, model = _get_client(model_id)
    personal = tailored_resume.get("personal_info", {})
    name = personal.get("name", "the candidate")
    summary = tailored_resume.get("summary", "")
    job_title = job_analysis.get("job_title", "the position")
    company_type = job_analysis.get("company_type", "")

    # Build concise experience string (company + title + top 2 bullets)
    experience_lines = []
    for exp in tailored_resume.get("experience", [])[:2]:
        bullets = exp.get("bullets", [])[:2]
        bullets_str = " | ".join(bullets)
        experience_lines.append(
            f"{exp.get('title', '')} at {exp.get('company', '')} ({exp.get('start_date', '')}–{exp.get('end_date', '')}): {bullets_str}"
        )
    experience = "\n".join(experience_lines) or "(none)"

    # Build concise projects string (name + first bullet of description)
    project_lines = []
    for proj in tailored_resume.get("projects", [])[:3]:
        desc = proj.get("description", "")
        first_bullet = desc.split("\n")[0] if desc else ""
        tech = ", ".join(proj.get("tech_stack", [])[:4])
        project_lines.append(f"{proj.get('name', '')}: {first_bullet} [{tech}]")
    projects = "\n".join(project_lines) or "(none)"

    # Build top skills string — supports both old (technical/tools) and new 5-category schema
    skills_data = tailored_resume.get("skills", {})
    all_skills = (
        skills_data.get("languages", [])
        + skills_data.get("frameworks", [])
        + skills_data.get("tools", [])
        + skills_data.get("technical", [])   # legacy fallback
        + skills_data.get("databases", [])
    )
    top_skills = ", ".join(all_skills[:10])

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": COVER_LETTER_SYSTEM},
            {
                "role": "user",
                "content": COVER_LETTER_PROMPT.format(
                    name=name,
                    job_title=job_title,
                    company_type=company_type,
                    summary=summary,
                    experience=experience,
                    projects=projects,
                    skills=top_skills,
                    job_analysis=json.dumps(job_analysis),
                    rag_context=rag_context or "(none)",
                ),
            },
        ],
        temperature=0.3,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))

@_safe_call
def generate_application_email(
    tailored_resume: dict,
    job_analysis: dict,
    jd_text: str = "",
    model_id: str | None = None,
    rag_context: str = "",
) -> dict:
    client, model = _get_client(model_id)
    personal = tailored_resume.get("personal_info", {})
    name = personal.get("name", "the candidate")
    summary = tailored_resume.get("summary", "")
    job_title = job_analysis.get("job_title", "the position")

    # Build concise experience/projects summary
    exp_proj_lines = []
    for exp in tailored_resume.get("experience", [])[:1]:
        exp_proj_lines.append(f"Role: {exp.get('title')} at {exp.get('company')}")
    for proj in tailored_resume.get("projects", [])[:2]:
        exp_proj_lines.append(f"Project: {proj.get('name')}")
    experience_projects = ", ".join(exp_proj_lines) or "(none)"

    skills_data = tailored_resume.get("skills", {})
    all_skills = (
        skills_data.get("languages", [])
        + skills_data.get("frameworks", [])
        + skills_data.get("tools", [])
        + skills_data.get("technical", [])   # legacy fallback
        + skills_data.get("databases", [])
    )
    top_skills = ", ".join(all_skills[:8])

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": APPLICATION_EMAIL_SYSTEM},
            {
                "role": "user",
                "content": APPLICATION_EMAIL_PROMPT.format(
                    name=name,
                    job_title=job_title,
                    summary=summary,
                    skills=top_skills,
                    experience_projects=experience_projects,
                    job_analysis=json.dumps(job_analysis),
                    rag_context=rag_context or "(none)",
                ),
            },
        ],
        temperature=0.3,
        max_tokens=300,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))

@_safe_call
def suggest_job_search_params(resume_text: str, model_id: str | None = None) -> dict:
    """Analyze a raw resume and suggest the best job search term and location."""
    client, model = _get_client(model_id)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JOB_SEARCH_SUGGESTION_SYSTEM},
            {"role": "user", "content": f"Here is the candidate's resume:\n\n{resume_text}"},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))


# ── Agentic AI functions (GLM/Qwen only) ─────────────────────────────────────

PLAN_SYSTEM = """You are a senior technical recruiter planning a resume optimization strategy.
Analyze the resume and job description, then output a concise JSON plan.
Return ONLY valid JSON."""

PLAN_PROMPT = """Analyze this resume and job description. Decide the optimization strategy.

RESUME TEXT (first 1500 chars):
{resume_snippet}

JOB DESCRIPTION (first 1000 chars):
{jd_snippet}

Return JSON:
{{
  "job_title": "exact job title from JD",
  "seniority": "intern/junior/mid/senior/lead",
  "job_category": "e.g. Backend SWE / Data Science / DevOps / Full Stack / Mobile",
  "primary_stack": ["top 5 technologies the candidate must showcase"],
  "critical_missing_areas": ["areas where the resume is weak relative to the JD"],
  "rewrite_strategy": "one sentence: what to prioritize in the rewrite",
  "ats_risk_keywords": ["keywords from JD most likely to be missed by a generic resume rewrite"]
}}"""



INTERVIEW_PREP_SYSTEM = """You are a senior technical interviewer and career coach.
Generate realistic, role-specific interview preparation content based on the candidate's tailored resume and the job description.
Return ONLY valid JSON."""

INTERVIEW_PREP_PROMPT = """Generate interview preparation content for {name} applying for {job_title}.

TAILORED RESUME SUMMARY:
Skills: {skills}
Experience highlights: {experience}
Projects: {projects}

JOB REQUIREMENTS:
Required skills: {required_skills}
Key responsibilities: {responsibilities}
Seniority: {seniority}

Return JSON with EXACTLY this shape:
{{
  "likely_technical_questions": [
    {{"question": "...", "why_asked": "which skill/requirement this tests", "tip": "what to emphasize in your answer"}}
  ],
  "likely_behavioral_questions": [
    {{"question": "...", "star_prompt": "brief STAR method hint for this candidate based on their resume"}}
  ],
  "strengths_to_highlight": ["specific strength from resume that matches a JD requirement"],
  "gaps_to_prepare_for": ["a potential weak point the interviewer may probe and how to address it"],
  "questions_to_ask_interviewer": ["smart, role-specific question the candidate should ask"]
}}

Rules:
- 5 technical questions, 3 behavioral, 3 strengths, 2 gaps, 3 interviewer questions
- Every question must be specific to this candidate's resume and this job — not generic
- Technical questions should reference actual technologies from the resume
- Return ONLY valid JSON"""


@_safe_call
def plan_analysis(
    resume_text: str,
    jd_text: str,
    model_id: str | None = None,
) -> dict:
    """Agent planning step: decide rewrite strategy before touching the resume."""
    client, model = _get_client(model_id)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": PLAN_SYSTEM},
            {
                "role": "user",
                "content": PLAN_PROMPT.format(
                    resume_snippet=resume_text[:1500],
                    jd_snippet=jd_text[:1000],
                ),
            },
        ],
        temperature=0.2,
        max_tokens=5000,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))



@_safe_call
def generate_interview_prep(
    tailored_resume: dict,
    job_analysis: dict,
    model_id: str | None = None,
) -> dict:
    """Generate role-specific interview Q&A and preparation tips."""
    client, model = _get_client(model_id)

    personal = tailored_resume.get("personal_info", {})
    name = personal.get("name", "the candidate")
    job_title = job_analysis.get("job_title", "the position")
    seniority = job_analysis.get("seniority", "mid")

    # Build skills string
    skills_data = tailored_resume.get("skills", {})
    all_skills = (
        skills_data.get("languages", [])[:4]
        + skills_data.get("frameworks", [])[:4]
        + skills_data.get("tools", [])[:3]
    )
    skills = ", ".join(all_skills)

    # Build experience highlights
    exp_lines = []
    for exp in tailored_resume.get("experience", [])[:2]:
        bullets = exp.get("bullets", [])[:1]
        if bullets:
            exp_lines.append(f"{exp.get('title')} at {exp.get('company')}: {bullets[0]}")
    experience = " | ".join(exp_lines) or "(none)"

    # Build project highlights
    proj_lines = []
    for proj in tailored_resume.get("projects", [])[:2]:
        desc = proj.get("description", "")
        first_line = desc.split("\n")[0] if desc else ""
        proj_lines.append(f"{proj.get('name')}: {first_line}")
    projects = " | ".join(proj_lines) or "(none)"

    required_skills = ", ".join(job_analysis.get("required_skills", [])[:8])
    responsibilities = " | ".join(job_analysis.get("key_responsibilities", [])[:4])

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": INTERVIEW_PREP_SYSTEM},
            {
                "role": "user",
                "content": INTERVIEW_PREP_PROMPT.format(
                    name=name,
                    job_title=job_title,
                    skills=skills,
                    experience=experience,
                    projects=projects,
                    required_skills=required_skills,
                    responsibilities=responsibilities,
                    seniority=seniority,
                ),
            },
        ],
        temperature=0.5,
        max_tokens=4000,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))


# ── v2 Agentic functions ──────────────────────────────────────────────────────


GAP_ANALYSIS_SYSTEM = """You are a precision resume gap analyst.
Your ONLY job: compare a structured resume with JD requirements and identify exactly
what is missing, where to put it, and what is already good (do not touch those).
Return ONLY valid JSON. Be surgical — do not suggest rewriting sections that are already strong."""

GAP_ANALYSIS_PROMPT = """Identify keyword and content gaps between this resume and the JD.

BASELINE ATS SCORE: {ats_score}%
MISSING KEYWORDS (from ATS scan): {missing_keywords}

JOB ANALYSIS:
{job_analysis}

RESUME SECTIONS (names + brief content):
Summary: {summary_snippet}
Experience titles: {experience_titles}
Skills categories: {skills_keys}
Projects: {project_names}

Return JSON:
{{
  "critical_gaps": ["keyword that is completely absent from resume"],
  "quick_wins": ["keyword present in wrong section — just move it"],
  "section_priorities": {{
    "summary": "specific instruction or null if already strong",
    "experience": "specific instruction or null if already strong",
    "skills": "specific instruction or null if already strong",
    "projects": "specific instruction or null if already strong"
  }},
  "unchanged_sections": ["section names that should NOT be touched — already strong"],
  "estimated_ats_gain": "e.g. +12 points if critical gaps are filled"
}}"""


@_safe_call
def gap_analysis(
    resume_json: dict,
    job_analysis: dict,
    ats_score: int,
    missing_keywords: list[str],
    model_id: str | None = None,
) -> dict:
    """
    Dedicated gap analysis agent.
    Uses cheap model — sends only section summaries, not full resume.
    Returns section-level instructions so the rewriter only touches what needs work.
    """
    client, model = _get_cheap_client(model_id)

    # Build minimal section summaries — avoid sending full resume text
    summary_snippet = str(resume_json.get("summary", ""))[:120]
    experience_titles = " | ".join(
        f"{e.get('title', '')} @ {e.get('company', '')}"
        for e in resume_json.get("experience", [])[:3]
    )
    skills_keys = ", ".join(resume_json.get("skills", {}).keys())
    project_names = " | ".join(
        p.get("name", "") for p in resume_json.get("projects", [])[:3]
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": GAP_ANALYSIS_SYSTEM},
            {
                "role": "user",
                "content": GAP_ANALYSIS_PROMPT.format(
                    ats_score=ats_score,
                    missing_keywords=", ".join(missing_keywords[:20]) or "(none)",
                    job_analysis=json.dumps({
                        "required_skills": job_analysis.get("required_skills", [])[:12],
                        "must_have": job_analysis.get("must_have", [])[:8],
                        "keyword_density_targets": job_analysis.get("keyword_density_targets", [])[:8],
                        "rewrite_strategy": job_analysis.get("rewrite_strategy", ""),
                    }),
                    summary_snippet=summary_snippet,
                    experience_titles=experience_titles,
                    skills_keys=skills_keys,
                    project_names=project_names,
                ),
            },
        ],
        temperature=0.1,
        max_tokens=700,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))


# Section rewrite prompts — one per section type for focused, lean prompts
_SECTION_SYSTEMS = {
    "summary": """You rewrite ONLY the resume summary section. Write 1–3 concise lines.
Line 1: Candidate's role, seniority, and core tech stack.
Line 2-3: Domain expertise, key business/technical impact, and career focus.
Do NOT use AI buzzwords (no 'passionate', 'results-driven', 'hardworking', 'leveraged').
Keep it natural, human, and recruiter-focused. DO NOT use markdown.
Return JSON: {"summary": "..."}""",

    "experience": """You rewrite ONLY the experience section bullets.
Provide 3 to 5 impact-driven bullets per job.
Formula: [Strong Action Verb] + [Task] + [Technology] + [Impact].
Each bullet MUST answer: What was built? How was it built? What impact did it create?
NEVER start bullets with: 'Worked on', 'Responsible for', 'Helped', 'Participated in', 'Involved in'.
Do NOT use markdown. Return plain text bullets.
Return JSON with the updated experience array.""",

    "skills": """You rewrite ONLY the skills section.
Organize into logical categories: Languages, Frontend, Backend, Frameworks, Databases, Cloud, DevOps, AI / ML, Tools, Concepts.
Sort categories and skills by Job Description relevance.
DO NOT use markdown.
Return JSON: {"skills": {"Languages": [...], "Frontend": [...], "Backend": [...], "Frameworks": [...], "Databases": [...], "Cloud": [...], "DevOps": [...], "AI / ML": [...], "Tools": [...], "Concepts": [...]}}""",

    "projects": """You rewrite ONLY the project entries.
Provide 3 to 4 technical bullet points in the "bullets" array per project.
Bullet 1: WHY the project exists (value proposition & core system problem).
Bullet 2: HOW it was built (technical implementation, architecture, tech stack).
Bullet 3-4: WHAT impact/functionality it delivers (metrics, scale, test coverage, deployment).
DO NOT use markdown.
Return JSON with the updated projects array containing objects with "name", "bullets", "description", and "tech_stack".""",
}

CRITIQUE_SYSTEM = """You are a strict QA Reviewer checking a resume section rewrite.
Your goal is to verify that the draft correctly integrated the missing keywords and adhered to the formatting/style rules provided in the context.

Review the draft against the missing keywords.
Return JSON with EXACTLY this shape:
{
  "passes_audit": true or false,
  "corrective_feedback": "If passes_audit is false, provide a short, direct instruction to the rewrite agent on what to fix. If true, leave empty."
}"""


CRITIQUE_PROMPT = """Analyze this section rewrite.

SECTION NAME: {section_name}

MISSING KEYWORDS (must be present):
{gap_instr}

POLICY/STYLE CONTEXT (must be followed):
{rag_context}

DRAFT TO REVIEW:
{draft_text}

Does the draft contain the required keywords without sounding unnatural? Does it follow the policies?
Return JSON."""


@_safe_call
def critique_section(
    section_name: str,
    draft_text: str,
    gap_instr: str,
    rag_context: str,
    model_id: str | None = None,
) -> dict:
    """Critique a rewritten section to verify keywords and style compliance."""
    client, model = _get_cheap_client(model_id)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CRITIQUE_SYSTEM},
            {
                "role": "user",
                "content": CRITIQUE_PROMPT.format(
                    section_name=section_name,
                    gap_instr=gap_instr,
                    rag_context=rag_context,
                    draft_text=draft_text if isinstance(draft_text, str) else json.dumps(draft_text),
                ),
            },
        ],
        temperature=0.1,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))


_SECTION_PROMPT = """Improve this resume section for the target role.

GAP INSTRUCTIONS (apply these specifically): {gap_instructions}

MISSING KEYWORDS TO INTEGRATE (MANDATORY — ALL MUST APPEAR VERBATIM):
{missing_keywords}
- CRITICAL: You MUST weave every exact keyword listed above (exact spelling, exact casing) into the updated section.
- Do NOT paraphrase (e.g., write 'Kubernetes' not 'k8s', write 'PostgreSQL' not 'postgres').
- Every keyword must appear at least once in the final section output.

RETRIEVED INDUSTRY CONTEXT (writing style reference): {rag_context}

JD KEY REQUIREMENTS:
{jd_requirements}

CURRENT SECTION DATA:
{section_data}

{extra_rules}

Return ONLY the section JSON. No explanation."""


@_safe_call
def rewrite_section(
    section_name: str,
    section_data,
    job_analysis: dict,
    gap_instructions: str,
    missing_keywords: list[str],
    rag_context: str = "",
    model_id: str | None = None,
) -> dict:
    """
    Rewrite a SINGLE resume section in isolation.
    Far smaller prompt than full-resume rewrite — faster and more precise.
    section_name: 'summary' | 'experience' | 'skills' | 'projects'
    """
    client, model = _get_client(model_id)  # Premium model for rewriting

    system = _SECTION_SYSTEMS.get(section_name, _SECTION_SYSTEMS["projects"])

    # Only include top 3 RAG chunks (compact context)
    rag_trimmed = rag_context[:600] if rag_context else "(none)"

    # Only send the most relevant JD fields
    jd_requirements = json.dumps({
        "required_skills": job_analysis.get("required_skills", [])[:10],
        "keyword_density_targets": job_analysis.get("keyword_density_targets", [])[:6],
        "rewrite_strategy": job_analysis.get("rewrite_strategy", ""),
        "seniority": job_analysis.get("seniority", ""),
    })

    extra_rules = ""
    if section_name == "skills":
        extra_rules = (
            "STRICT: Languages=programming languages only, Frontend=frontend framework/libs, Backend=backend framework/libs, "
            "Databases=DB systems only, Cloud & DevOps=cloud/CI-CD/infra tools, Tools=dev tools/git, Concepts=methodologies/patterns. "
            "Max: Languages 7, Frontend 7, Backend 7, Databases 5, Cloud & DevOps 7, Tools 7, Concepts 6."
        )
    elif section_name == "projects":
        extra_rules = (
            "STRICT: EXACTLY 2 to 3 bullets per project — no more, no less. "
            "Each bullet must integrate at least 1 verbatim JD keyword from the MISSING KEYWORDS list. "
            "Do NOT repeat tech names from tech_stack in bullets — bullets describe features, architecture, outcomes. "
            "Max 8 items in tech_stack."
        )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": _SECTION_PROMPT.format(
                    gap_instructions=gap_instructions or "Improve ATS coverage and readability.",
                    missing_keywords=", ".join(missing_keywords[:15]) or "(none)",
                    rag_context=rag_trimmed,
                    jd_requirements=jd_requirements,
                    section_data=json.dumps(section_data)[:1800],
                    extra_rules=extra_rules,
                ),
            },
        ],
        temperature=0.2,
        max_tokens=1400,   # increased: allows full 2-3 bullet project output + section rewrite without truncation
        response_format={"type": "json_object"},
    )
    result = _parse_json_response(_extract_content(response))

    # Post-process skills section to enforce clean categories
    if section_name == "skills" and "skills" in result:
        return {"skills": _clean_resume({"skills": result["skills"]})["skills"]}

    return result


HUMANIZE_SYSTEM = """You are a humanization editor for engineering resumes.
Your ONLY job: find and fix AI-sounding, robotic, or overly corporate language.
You do NOT rewrite content — you polish wording in the provided sections only.
Make the writing sound like an experienced developer wrote it naturally.

CHECK FOR:
- Overused buzzwords: spearheaded, leveraged, orchestrated, synergized, championed, revolutionized, utilized, streamlined
- Repetitive bullet openers (3+ bullets starting the same way — vary them)
- Passive voice where active reads better
- Overly long sentences (>25 words)
- Corporate jargon that sounds unnatural for a software engineer
- AI tic phrases: "developed and implemented", "built and deployed", "responsible for", "in order to", "in an effort to", "as a result of", "it is worth noting", "plays a key role"
- Generic filler: "a wide range of", "not only... but also", "further enhancing"

RULES:
- Only modify lines that genuinely need it — do NOT change lines that already read well
- Keep all facts, technologies, and achievements intact
- Never remove keywords that were added for ATS coverage
- Keep the same JSON structure
- Return ONLY valid JSON"""

HUMANIZE_PROMPT = """Review and humanize these rewritten resume sections.
Only fix lines that sound robotic, repetitive, or AI-generated.

SECTIONS TO REVIEW:
{sections_json}

Return the corrected sections with the same JSON keys."""


@_safe_call
def humanize_sections(
    changed_sections: dict,
    model_id: str | None = None,
) -> dict:
    """
    Dedicated humanization pass on ONLY the sections that were rewritten.
    Uses cheap model — this is a light editing pass, not a full rewrite.
    changed_sections: {section_name: section_data, ...}
    """
    if not changed_sections:
        return {}

    client, model = _get_cheap_client(model_id)

    # Compact the sections — only send what was changed
    sections_json = json.dumps(changed_sections)[:2000]

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": HUMANIZE_SYSTEM},
            {
                "role": "user",
                "content": HUMANIZE_PROMPT.format(sections_json=sections_json),
            },
        ],
        temperature=0.35,
        max_tokens=1000,   # increased: more room for polishing multiple sections
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))


LINKEDIN_MESSAGE_SYSTEM = """You write a LinkedIn connection request note.
Hard limit: 300 characters total (LinkedIn's limit).
Tone: professional but direct. No buzzwords. No "I am excited". No emojis.
Mention: candidate's role/stack + the position they're applying for.
End with a clear ask: connect, chat, or review application.
Return ONLY valid JSON."""

LINKEDIN_MESSAGE_PROMPT = """Write a LinkedIn connection note for {name} applying for {job_title}.

Their stack: {top_skills}
One key project: {top_project}
Company type: {company_type}

Return JSON: {{"message": "..."}}
The message MUST be under 300 characters."""


@_safe_call
def generate_linkedin_message(
    tailored_resume: dict,
    job_analysis: dict,
    model_id: str | None = None,
) -> dict:
    """Generate a ≤300-char LinkedIn connection request note. Uses cheap model."""
    client, model = _get_cheap_client(model_id)

    personal = tailored_resume.get("personal_info", {})
    name = personal.get("name", "the candidate")
    job_title = job_analysis.get("job_title", "the position")
    company_type = job_analysis.get("company_type", "")

    skills_data = tailored_resume.get("skills", {})
    top_skills = ", ".join(
        (skills_data.get("languages", [])[:2] + skills_data.get("frameworks", [])[:2])[:3]
    )

    projects = tailored_resume.get("projects", [])
    top_project = projects[0].get("name", "") if projects else ""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": LINKEDIN_MESSAGE_SYSTEM},
            {
                "role": "user",
                "content": LINKEDIN_MESSAGE_PROMPT.format(
                    name=name,
                    job_title=job_title,
                    top_skills=top_skills,
                    top_project=top_project,
                    company_type=company_type,
                ),
            },
        ],
        temperature=0.2,
        max_tokens=5000,
        response_format={"type": "json_object"},
    )
    result = _parse_json_response(_extract_content(response))
    # Enforce 300-char limit
    if isinstance(result.get("message"), str) and len(result["message"]) > 300:
        result["message"] = result["message"][:297] + "..."
    return result


RECRUITER_TIPS_SYSTEM = """You generate 5–7 actionable, role-specific recruiter preparation tips
for a candidate about to apply to a specific job.

Each tip must be:
- Specific to this candidate's background and this job
- Practical and immediately actionable
- Under 2 sentences

Topics to cover (pick the most relevant 5–7):
- What to emphasize in a phone screen
- How to frame a gap or weakness
- One question to ask the hiring manager
- Salary negotiation hint based on seniority
- Which project to lead with in interviews
- ATS keyword tip for this role
- How to stand out among other applicants

Return ONLY valid JSON."""

RECRUITER_TIPS_PROMPT = """Generate recruiter tips for {name} applying for {job_title} ({seniority} level).

Their strongest asset: {top_asset}
Key matching skills: {matched_skills}
Main gap vs JD: {main_gap}
ATS score: {ats_score}%

Return JSON: {{"tips": ["tip 1", "tip 2", ...]}}"""


@_safe_call
def generate_recruiter_tips(
    tailored_resume: dict,
    job_analysis: dict,
    ats_score: int = 0,
    missing_keywords: list[str] | None = None,
    model_id: str | None = None,
) -> dict:
    """Generate 5–7 role-specific recruiter tips. Uses cheap model."""
    client, model = _get_cheap_client(model_id)

    personal = tailored_resume.get("personal_info", {})
    name = personal.get("name", "the candidate")
    job_title = job_analysis.get("job_title", "the position")
    seniority = job_analysis.get("seniority", "junior")

    # Top asset = strongest project or most recent role
    projects = tailored_resume.get("projects", [])
    experience = tailored_resume.get("experience", [])
    top_asset = (
        projects[0].get("name", "") if projects
        else (f"{experience[0].get('title', '')} at {experience[0].get('company', '')}" if experience else "their projects")
    )

    # Matched skills = intersection of resume skills and JD required
    skills_data = tailored_resume.get("skills", {})
    all_skills = set(
        s.replace("**", "").lower()
        for cat in skills_data.values() if isinstance(cat, list)
        for s in cat
    )
    required = job_analysis.get("required_skills", [])
    matched_skills = ", ".join([s for s in required[:6] if s.lower() in all_skills]) or "core stack"
    main_gap = (missing_keywords or [])[0] if missing_keywords else "none identified"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": RECRUITER_TIPS_SYSTEM},
            {
                "role": "user",
                "content": RECRUITER_TIPS_PROMPT.format(
                    name=name,
                    job_title=job_title,
                    seniority=seniority,
                    top_asset=top_asset,
                    matched_skills=matched_skills,
                    main_gap=main_gap,
                    ats_score=ats_score,
                ),
            },
        ],
        temperature=0.4,
        max_tokens=600,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(response.choices[0].message.content)
