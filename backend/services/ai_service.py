import ast
import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

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

    # ── Strip reasoning / thinking blocks (NVIDIA, DeepSeek R1, etc.) ──────
    # Remove <think>...</think> and similar reasoning wrappers
    content = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE)
    content = re.sub(r"<reasoning>[\s\S]*?</reasoning>", "", content, flags=re.IGNORECASE)
    # Remove leading prose before the first JSON object
    first_brace = content.find("{")
    if first_brace > 0:
        content = content[first_brace:]
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

    # Strategy 1: Standard json.loads (strict=False permits literal unescaped newlines inside strings)
    try:
        data = json.loads(content, strict=False)
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
                data = json.loads(blob, strict=False)
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
                data = json.loads(cleaned, strict=False)
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
    """Build model registry from environment variables — only GLM-5 and GLM-4.7 Flash."""
    global MODEL_REGISTRY
    MODEL_REGISTRY = {}

    bedrock_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK", "").strip()

    # GLM-5
    glm_key = os.environ.get("GLM_API_KEY", "").strip() or bedrock_token
    glm_endpoint = os.environ.get("GLM_ENDPOINT", "https://bedrock-mantle.us-east-1.api.aws/v1")
    if not _is_placeholder(glm_key) and glm_endpoint:
        MODEL_REGISTRY["glm"] = {
            "id": "glm",
            "display_name": "GLM-5 (Recommended)",
            "endpoint": glm_endpoint,
            "api_key": glm_key,
            "model": os.environ.get("GLM_MODEL", "zai.glm-5"),
            "supports_embeddings": True,
        }

    # GLM-4.7 Flash (Fast)
    glm_flash_key = os.environ.get("GLM_FLASH_API_KEY", "").strip() or glm_key
    glm_flash_endpoint = os.environ.get("GLM_FLASH_ENDPOINT", glm_endpoint)
    if not _is_placeholder(glm_flash_key) and glm_flash_endpoint:
        MODEL_REGISTRY["glm-flash"] = {
            "id": "glm-flash",
            "display_name": "GLM-4.7 Flash (Fast)",
            "endpoint": glm_flash_endpoint,
            "api_key": glm_flash_key,
            "model": os.environ.get("GLM_FLASH_MODEL", "zai.glm-4.7-flash"),
            "supports_embeddings": False,
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
        endpoint = endpoint.removesuffix(suffix)
    return endpoint


def _mask_secrets(text: str) -> str:
    """Replace any live API key values in error messages with [REDACTED]."""
    for cfg in MODEL_REGISTRY.values():
        key = cfg.get("api_key", "")
        if key and len(key) > 8 and key in text:
            text = text.replace(key, "[REDACTED]")
    return text


def _resolve_model_id(model_id: str | None = None) -> str:
    """Resolve the active provider ID with env/default fallback."""
    if not model_id:
        model_id = os.environ.get("DEFAULT_MODEL_ID", "glm")

    if model_id not in MODEL_REGISTRY:
        if MODEL_REGISTRY:
            return next(iter(MODEL_REGISTRY))
        raise RuntimeError("No AI models configured. Check your environment variables.")

    return model_id


def _to_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _merge_extra_body(existing: dict | None, defaults: dict) -> dict:
    merged = dict(existing or {})
    for key, value in defaults.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        elif key not in merged:
            merged[key] = value
    return merged


def _get_chat_completion_options(model_id: str | None = None) -> dict:
    """Return provider-specific chat completion defaults."""
    resolved_model_id = _resolve_model_id(model_id)

    options: dict = {}
    raw_max = os.environ.get("GLM_MAX_TOKENS", "").strip()
    if raw_max:
        options["max_tokens"] = int(raw_max)

    raw_top_p = os.environ.get("GLM_TOP_P", "").strip()
    if raw_top_p:
        options["top_p"] = float(raw_top_p)

    return options


import logging

logger = logging.getLogger(__name__)

# List of preferred fallback models
_FALLBACK_CHAIN = ["glm-flash", "glm"]

def _create_chat_completion(client: OpenAI, model_id: str | None = None, **kwargs):
    """Create a chat completion with provider-level defaults applied and automatic fallback."""
    import openai
    
    resolved = _resolve_model_id(model_id)
    
    def _attempt(current_client, current_model_id, current_kwargs):
        provider_options = _get_chat_completion_options(current_model_id)
        
        if "max_tokens" in provider_options:
            if "max_tokens" not in current_kwargs:
                current_kwargs["max_tokens"] = provider_options["max_tokens"]

        if "top_p" in provider_options and "top_p" not in current_kwargs:
            current_kwargs["top_p"] = provider_options["top_p"]

        if "extra_body" in provider_options:
            current_kwargs["extra_body"] = _merge_extra_body(current_kwargs.get("extra_body"), provider_options["extra_body"])

        return current_client.chat.completions.create(**current_kwargs)

    try:
        # First attempt with the requested model
        return _attempt(client, resolved, dict(kwargs))
    except (openai.RateLimitError, openai.APIStatusError) as e:
        # If it's an APIStatusError, only retry if it's a 429
        if isinstance(e, openai.APIStatusError) and getattr(e, "status_code", None) != 429:
            raise e
            
        logger.warning(f"Rate limit hit on {resolved}. Attempting fallback models...")
        
        # Try fallbacks
        for fallback_id in _FALLBACK_CHAIN:
            if fallback_id == resolved or fallback_id not in MODEL_REGISTRY:
                continue
                
            try:
                logger.info(f"Trying fallback model: {fallback_id}")
                fallback_client, fallback_model_name = _get_client(fallback_id)
                fallback_kwargs = dict(kwargs)
                fallback_kwargs["model"] = fallback_model_name
                
                return _attempt(fallback_client, fallback_id, fallback_kwargs)
            except (openai.RateLimitError, openai.APIStatusError) as fallback_e:
                if isinstance(fallback_e, openai.APIStatusError) and getattr(fallback_e, "status_code", None) != 429:
                    logger.warning(f"Fallback {fallback_id} failed with non-429 error: {fallback_e}")
                    continue # Try next if not a rate limit
                logger.warning(f"Rate limit hit on fallback {fallback_id}.")
                continue
            except Exception as ex:
                logger.error(f"Error on fallback {fallback_id}: {ex}")
                continue
                
        # If all fallbacks fail (or aren't configured), raise the original error
        raise e


def _get_client(model_id: str | None = None) -> tuple[OpenAI, str]:
    """Return (client, model_name) for the given model_id."""
    model_id = _resolve_model_id(model_id)
    cfg = MODEL_REGISTRY[model_id]

    if model_id not in _clients:
        import httpx
        endpoint = _normalize_endpoint(cfg["endpoint"])
        base_url = endpoint if endpoint.endswith("/") else endpoint + "/"
        http_client = httpx.Client(
            timeout=120.0,
            follow_redirects=True,
        )
        _clients[model_id] = OpenAI(
            base_url=base_url,
            api_key=cfg["api_key"],
            timeout=120.0,
            max_retries=1,
            http_client=http_client,
        )

    return _clients[model_id], cfg["model"]


# ── Task-based auto-routing ──────────────────────────────────────────────────
# Heavy tasks (complex reasoning, full rewrites) → GLM-5
# Light tasks (JD parse, gap analysis, fact check, critique) → GLM-4.7 Flash
_HEAVY_TASKS = frozenset({
    "rewrite",          # full resume rewrite
    "rewrite_section",  # section-level rewrite
    "humanize",         # humanization pass
    "cover_letter",     # cover letter generation
    "email",            # application email
    "interview_prep",   # interview Q&A generation
})
_LIGHT_TASKS = frozenset({
    "jd_analysis",      # job description parsing
    "gap_analysis",     # keyword gap analysis
    "fact_check",       # factual consistency check
    "critique",         # section critique
    "embedding",        # text embeddings
})


def get_client_for_task(task: str) -> tuple["OpenAI", str]:
    """
    Auto-select the best model for a given task.
    Heavy reasoning tasks → GLM-5 (quality).
    Fast/cheap tasks     → GLM-4.7 Flash (speed + cost).
    Falls back gracefully if only one model is configured.
    """
    if task in _LIGHT_TASKS and "glm-flash" in MODEL_REGISTRY:
        return _get_client("glm-flash")
    if task in _HEAVY_TASKS and "glm" in MODEL_REGISTRY:
        return _get_client("glm")
    # Fallback: use whatever is available
    for candidate in ("glm", "glm-flash"):
        if candidate in MODEL_REGISTRY:
            return _get_client(candidate)
    return _get_client(None)


def _get_cheap_client(preferred_model_id: str | None = None) -> tuple["OpenAI", str]:
    """Legacy shim — routes light tasks to GLM-4.7 Flash automatically."""
    return get_client_for_task("jd_analysis")


def _get_embedding_client(preferred_model_id: str | None = None) -> tuple[str, OpenAI]:
    """
    Return (provider_id, openai_client) for embeddings.
    Embeddings stay pinned to providers known to support them.
    """
    if preferred_model_id in MODEL_REGISTRY and MODEL_REGISTRY[preferred_model_id].get("supports_embeddings"):
        client, _ = _get_client(preferred_model_id)
        return preferred_model_id, client

    explicit_id = os.environ.get("EMBEDDING_PROVIDER_ID", "").strip()
    if explicit_id in MODEL_REGISTRY and MODEL_REGISTRY[explicit_id].get("supports_embeddings"):
        client, _ = _get_client(explicit_id)
        return explicit_id, client

    for candidate in ["glm", "nvidia"]:
        if candidate in MODEL_REGISTRY and MODEL_REGISTRY[candidate].get("supports_embeddings"):
            client, _ = _get_client(candidate)
            return candidate, client

    raise RuntimeError(
        "No embedding-capable model configured. Set EMBEDDING_PROVIDER_ID or configure a supported provider."
    )


def _get_embedding_model(provider_id: str) -> str:
    """Return the embedding model to use for the active provider."""
    if provider_id == "gemini":
        return os.environ.get("GEMINI_EMBEDDING_MODEL", "text-embedding-004")
    if provider_id == "nvidia":
        return os.environ.get("NVIDIA_EMBEDDING_MODEL", "baai/bge-m3")
    # GLM and all other providers behind bedrock-mantle use the same embedding model
    return os.environ.get("EMBEDDING_MODEL", "amazon.titan-embed-text-v1")


def get_embedding(text: str, model_id: str | None = None) -> list[float]:
    """Generate dense embeddings using the API.
    Raises RuntimeError if no embedding provider is available — callers
    (rag_service, profile_rag_service) catch this and fall back to keyword matching."""
    embedding_provider_id, client = _get_embedding_client(model_id)
    embed_model = _get_embedding_model(embedding_provider_id)
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

INTERNAL REASONING & OPTIMIZATION PIPELINE:
Before returning your final response, you MUST execute these steps internally. You must return ONLY the final polished version in the requested JSON format (do not output the step details in the text):

Step 1: Write/draft the resume improvements.
Step 2: Act as a critical Amazon / FAANG Recruiter. Read the draft, find weaknesses, identify vague descriptions, and evaluate impact density.
Step 3: Rewrite the draft to fix all identified weaknesses.
Step 4: Act as an ATS Parser. Review the updated draft, scan for missing target keywords, and verify they are present.
Step 5: Rewrite the draft again to seamlessly integrate missing keywords while maintaining a natural human voice.

TARGET OBJECTIVES:
- ATS Score Target: 90–95% (NEVER target 100%, never keyword stuff; natural language and recruiter scanning take top priority).
- Recruiter Ergonomics: Optimized for a 6–10 second skim.

JOB DESCRIPTION PRIORITY:
Treat the Job Description as the primary optimization target. For every required or preferred skill:
1. If the candidate genuinely possesses the exact skill, emphasize it naturally where relevant.
2. If the candidate has closely related experience, describe the transferable experience honestly without claiming expertise in the exact technology.
   Examples: PostgreSQL ↔ MySQL, Flask ↔ Django, Azure ↔ AWS.
3. If the candidate lacks the required skill, never fabricate experience or imply proficiency. Instead, optimize the resume around the candidate's strongest relevant qualifications.

NO FAKE METRICS:
If measurable impact is not explicitly provided, never invent percentages, time savings, revenue, user counts, performance improvements, or other numerical metrics. Instead, describe impact using truthful qualitative language such as:
Successfully, Efficiently, Reliably, Scalable, Maintainable, Production-ready, Robust, Secure, Reusable, Well-tested.

RECRUITER WRITING STANDARD (SINGLE PROFESSIONAL IDENTITY RULE):
Write like an experienced recruiter is helping the candidate present their work honestly and clearly.
- Detect & Enforce ONE Strong Identity: Before rewriting, determine the candidate's strongest career identity (e.g., Backend, Frontend, AI). Every section must relentlessly support this single identity. A recruiter must know what role they fit within 10 seconds.
- Organize Skills logically (Languages, Backend, Frontend, Database, Cloud & Tools). Never use a flat list. Only include technologies they can confidently discuss.
- Highlight real contributions, use natural language, avoid buzzwords.
- Prefer evidence over adjectives. (e.g., "Built a backend service using X" instead of "Expert in X").
- Never exaggerate or invent achievements.
- Every bullet should immediately answer: What was built? Which technologies were used? Why does it matter?
- Avoid sounding like marketing copy. The resume should feel authentic and written by a real software engineer.

BULLET WRITING:
Internally analyze accomplishments using STAR (Situation, Task, Action, Result). Do not expose STAR.
Write bullets as: Action + Technology + Result.
Examples:
- Built REST APIs using Django and PostgreSQL for user authentication.
- Developed a React dashboard for managing customer orders.
- Improved database performance by optimizing SQL queries.
Each bullet should describe one accomplishment.

FINAL REVIEW:
Before returning the response, silently verify:
✓ No fabricated skills
✓ No fabricated metrics
✓ No fabricated technologies
✓ Strong ATS keyword coverage
✓ Natural keyword placement
✓ Professional but simple English
✓ No AI buzzwords
✓ Resume sounds human-written
✓ Every statement is supported by the candidate's original resume

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
- MUST follow this fixed formula:
  1. Identity (e.g., Python Backend Developer with 5 years experience). Do not write "Seeking an opportunity" or apologize for being a fresher.
  2. Core technologies (e.g., FastAPI, React, PostgreSQL). Never write "Various technologies" or "Knowledge of".
  3. Evidence (e.g., "Built an AI Resume Builder supporting 4 ATS templates"). Use strong verbs (Built, Designed, Deployed) and numbers. Never write "Experienced in" or "Proficient in".
  4. Value (What problems you solve for a team).
- Natural recruiter tone. No generic self-praise buzzwords.

PROFESSIONAL EXPERIENCE (3–5 IMPACT-DRIVEN BULLETS PER ROLE):
- Every bullet formula: [Strong Action Verb] + [Task] + [**JD-Keyword/Technology**] + [**Measurable Impact/Metric or Power Descriptor**].
- Bold ONLY: (1) JD-required keywords/tools, (2) quantifiable metrics, (3) 1-2 core tech used. MAX 2-3 **bolds** per bullet.
- NEVER bold action verbs (built, designed, implemented, etc.) — only the tech, metric, or JD keyword gets bolded.
- Each bullet answers: What was built? How was it built? What business or technical impact did it create?
- NEVER begin bullets with: Worked on, Responsible for, Helped, Participated in, Involved in.

PROJECTS (3–4 TECHNICAL BULLETS PER PROJECT):
- Recruiter-First Invariant: Projects must serve as proof of capability for the target role, not just a list of features.
- Every project must answer these 4 questions across its bullets:
  1. What problem did you solve? (WHY the project exists, value prop / core challenge)
  2. What technologies did you use? (Listed in tech_stack)
  3. What engineering work did YOU do? (HOW it was built, e.g. "Implemented JWT auth..." instead of "Used JWT")
  4. Why should I care / what was the impact? (WHAT it delivers, e.g. performance improvements, latency reduction)
- Dynamic Role Alignment: Shift bullet emphasis based on the target job (Backend focus on APIs/DBs/Auth/Architecture; Frontend on UI/UX/responsive/state; AI on LLMs/RAG/embeddings/agents; Cloud on Docker/Terraform/CI/CD).
- Strict Relevance Sorting: Always sort and return projects in descending order of relevance to the target Job Description (best match first).

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

CERTIFICATIONS RULE — CRITICAL:
Copy every certification entry EXACTLY from the original resume.
The "name", "issuer", and "year" fields MUST be preserved verbatim.
Never empty these fields. If the original says "Udemy" keep "Udemy".
If the original has no issuer, leave the field as it was — do not replace it with "".

SKILLS TAXONOMY RULE:
Docker, docker-compose, and container tools go under "DevOps" — never under "Cloud".
Use "REST APIs" as the canonical form everywhere — never "RESTful API" or "REST API".

Return JSON with EXACTLY this shape:
{{
  "personal_info": {{
    "name": "...", "email": "...", "phone": "...", "location": "...",
    "linkedin": "...", "github": "...", "website": "..."
  }},
  "summary": "1-3 concise lines following the strict formula: Identity -> Core Tech -> Evidence (Built/Deployed...) -> Value. No generic AI fluff.",
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


COVER_LETTER_SYSTEM = """You write cover letters. Keep them human. A recruiter should read this and think a real person wrote it.

STRUCTURE — exactly 3 paragraphs:

P1 — WHO + WHY THIS COMPANY (2 sentences):
- One plain sentence on who the candidate is (their role or degree).
- One sentence on why THIS company specifically — name the company (find it in the JD), mention what they build or the problem they solve. Not a generic "I am interested in this role."

P2 — PROOF (2-3 sentences):
- Name 2 specific things the candidate built (projects or work experience). State what they built, the tech they used, and how it maps to what the JD needs.
- No vague claims. No adjectives. Just facts.

P3 — CLOSE (1 sentence):
- A short, direct ask for a call or interview. One sentence.
- Sign off: "Regards,\n{candidate_name}"

FORMAT — the body must open with the date and a greeting:
{today_date}

Dear Hiring Manager,

[paragraph 1]

[paragraph 2]

[paragraph 3]

Regards,
{candidate_name}
Portfolio: {portfolio_url}
GitHub: {github_url}

HARD BANS — any of these = rewrite:
passionate, excited, thrilled, eager, leverage, synergy, spearhead, results-driven, team player,
quick learner, dynamic, hardworking, proven track record, I am writing to apply, I am pleased,
I would like to express, I look forward to hearing from you, Thank you for your consideration,
I believe, I feel, I think, as a result of, in an effort to, it should be noted.

TONE: Plain English. Short sentences. No adjectives about the candidate — let the facts speak.
WORD COUNT: 120–160 words (body only, excluding header). Count before returning.
Return ONLY valid JSON — no markdown, no extra keys."""

COVER_LETTER_PROMPT = """Write a cover letter for {name} applying for {job_title}.

Today's date: {today_date}

CANDIDATE LINKS (include in sign-off):
Portfolio: {portfolio}
GitHub: {github}

RESUME:
Summary: {summary}
Experience: {experience}
Projects: {projects}
Skills: {skills}

RAW JD TEXT (first 800 chars — extract the company name from this):
{jd_snippet}

JOB ANALYSIS (structured):
{job_analysis}

BEFORE RETURNING CHECK:
[ ] Body opens with date, then blank line, then "Dear Hiring Manager,"
[ ] P1 names the company from the JD
[ ] P2 names 2 real projects/experiences with specific tech
[ ] P3 is a direct one-sentence ask
[ ] Sign-off is "Regards,\\n{name}" with portfolio and GitHub on separate lines
[ ] Zero banned words
[ ] 120-160 words in the body

Return JSON:
{{
  "subject_line": "Application for {job_title} — {name}",
  "body": "{today_date}\\n\\nDear Hiring Manager,\\n\\nparagraph 1\\n\\nparagraph 2\\n\\nparagraph 3\\n\\nRegards,\\n{name}\\nPortfolio: {portfolio}\\nGitHub: {github}"
}}"""


APPLICATION_EMAIL_SYSTEM = """You write job application emails. Keep them short and human.
A hiring manager should read this and immediately understand who the person is and why they applied.

STRUCTURE:
Line 1: Greeting — "Dear [Hiring Team]," or "Dear [Recruiter],"
Blank line.
Paragraph 1 (2 sentences): Who you are and the exact role you're applying for.
Paragraph 2 (2 sentences): 1-2 specific things from your resume that match what the JD needs. Name the project or tech directly.
Paragraph 3 (1 sentence): A direct ask — can they take a quick call, or please find the resume attached.
Blank line.
Sign-off: "Regards, {name}" — then on a new line: portfolio link and GitHub link.

HARD BANS:
passionate, excited, thrilled, eager, leverage, synergy, spearhead, results-driven, team player, quick learner.
No "thank you for your time." No "I look forward to hearing from you."

TONE: Direct, professional, plain English. 80-120 words total.
Return ONLY valid JSON."""

APPLICATION_EMAIL_PROMPT = """Write a job application email for {name} applying for {job_title}.

RESUME SUMMARY: {summary}
KEY SKILLS: {skills}
EXPERIENCE/PROJECTS: {experience_projects}
PORTFOLIO: {portfolio}
GITHUB: {github}

JOB SUMMARY:
{job_analysis}

COMMUNICATION EXAMPLES (style reference only):
{rag_context}

Return JSON:
{{
  "subject_line": "...",
  "body": "Dear Hiring Team,\\n\\n[paragraph 1]\\n\\n[paragraph 2]\\n\\n[paragraph 3]\\n\\nRegards,\\n{name}\\nPortfolio: {portfolio}\\nGitHub: {github}"
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

def smart_truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars strictly at sentence or word boundaries."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Find last sentence boundary
    last_end = max(truncated.rfind('.'), truncated.rfind('?'), truncated.rfind('!'))
    if last_end > 0:
        return truncated[:last_end+1].strip()
    # Fallback to word boundary
    last_space = truncated.rfind(' ')
    if last_space > 0:
        return truncated[:last_space].strip() + "..."
    return truncated + "..."

# ── Banned AI Buzzwords & Rephrasing Map ──────────────────────────────────────
_BANNED_PHRASE_REPLACEMENTS: dict[str, str] = {
    r"\bleveraged\b": "used",
    r"\butilized\b": "used",
    r"\bharnessed\b": "applied",
    r"\bfacilitated\b": "managed",
    r"\bshowcased\b": "demonstrated",
    r"\bdemonstrated ability to\b": "engineered",
    r"\bhighly motivated\b": "",
    r"\bresults-driven\b": "",
    r"\bresults driven\b": "",
    r"\bdynamic professional\b": "engineer",
    r"\bpassionate\b": "",
    r"\bhardworking\b": "",
    r"\bdedicated\b": "",
    r"\bself-motivated\b": "",
    r"\bself motivated\b": "",
    r"\bteam player\b": "",
    r"\bquick learner\b": "",
    r"\bspearheaded\b": "led",
    r"\bsynergized\b": "integrated",
    r"\brevolutionized\b": "optimized",
    r"\bpioneered\b": "developed",
    r"\bchampioned\b": "implemented",
    r"\bdynamic\b": "",
    r"\bbuilt and deployed\b": "built",
    r"\borchestrated\b": "coordinated",
}


def _scan_and_rephrase_banned_phrases(text: str) -> str:
    """Scan and replace/remove generic AI buzzwords from text."""
    if not isinstance(text, str) or not text.strip():
        return text or ""
    result = text
    for pattern, replacement in _BANNED_PHRASE_REPLACEMENTS.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return re.sub(r" +", " ", result).strip()


def _capitalize_sentences(text: str) -> str:
    """Issue 5: Ensure every sentence in text starts with a capital letter.
    Handles the common case of 'word. next word' → 'word. Next word'.
    """
    if not isinstance(text, str) or not text.strip():
        return text or ""
    # Capitalize the very first character
    text = text[0].upper() + text[1:] if text else text
    # Capitalize the character after '. ', '! ', '? '
    text = re.sub(r'([.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
    return text


def _verify_numeric_metrics(text: str, original_text: str) -> str:
    """Verify numeric claims in AI output against original text. Strips unverified numbers."""
    if not isinstance(text, str) or not original_text:
        return text or ""
    metric_matches = list(re.finditer(r"\b\d+(?:\.\d+)?%|\$\d+(?:\.\d+)?[kKmMbB]?|\b\d+[xX]\b|\b\d{2,}\b", text))
    if not metric_matches:
        return text
    orig_numbers = set(re.findall(r"\d+", original_text))
    result = text
    for m in metric_matches:
        claim_str = m.group(0)
        digits = re.findall(r"\d+", claim_str)
        if digits and not any(d in orig_numbers for d in digits):
            result = re.sub(re.escape(claim_str), "", result)
    return re.sub(r" +", " ", result).strip()


def _validate_bold_markers(bullet: str) -> str:
    """Ensure ** bold markers are balanced (even count). Strip if unbalanced."""
    if not isinstance(bullet, str):
        return ""
    count = bullet.count("**")
    if count % 2 != 0:
        return bullet.replace("**", "").replace("*", "").strip()
    return bullet.strip()


def _match_and_filter_entries(resume: dict, original_text: str) -> dict:
    """Match returned experience and project entries against original_text. Strip fabricated entries."""
    if not original_text or not isinstance(resume, dict):
        return resume
    orig_lower = original_text.lower()

    # 1. Match Experience Entries by company name
    exp_list = resume.get("experience", [])
    if isinstance(exp_list, list) and exp_list:
        legal_suffixes = {"inc", "llc", "corp", "corporation", "ltd", "pvt", "private", "limited", "services", "solutions", "co"}
        filtered_exp = []
        for exp in exp_list:
            if not isinstance(exp, dict):
                continue
            company = str(exp.get("company", "")).strip()
            if not company:
                filtered_exp.append(exp)
                continue
            comp_tokens = [t.lower() for t in re.findall(r"\b[A-Za-z0-9]+\b", company) if t.lower() not in legal_suffixes and len(t) >= 3]
            if not comp_tokens or any(tok in orig_lower for tok in comp_tokens):
                filtered_exp.append(exp)
        resume["experience"] = filtered_exp

    # 2. Match Projects by project title / distinctive tokens
    proj_list = resume.get("projects", [])
    if isinstance(proj_list, list) and proj_list:
        filtered_proj = []
        for proj in proj_list:
            if not isinstance(proj, dict):
                continue
            name = str(proj.get("name", "") or proj.get("title", "")).strip()
            if not name:
                filtered_proj.append(proj)
                continue
            name_tokens = [t.lower() for t in re.findall(r"\b[A-Za-z0-9]+\b", name) if len(t) >= 4 and t.lower() not in {"system", "platform", "management", "application", "project", "tool"}]
            if not name_tokens or any(tok in orig_lower for tok in name_tokens):
                filtered_proj.append(proj)
        resume["projects"] = filtered_proj

    return resume


def _clean_resume(resume: dict, original_text: str | None = None) -> dict:
    """Post-process AI output to remove filler skills and enforce formatting.
    Executes post-processing guards in exact sequence:
      1. Banned Phrase Scan & Rephrase
      2. Numeric Metric Guard (if original_text)
      3. Project & Experience Entry Matcher (if original_text)
      4. Smart Truncation (420-char summary, 180-char bullets cap)
      5. Bold Marker Validation (balanced ** check)
    """
    if not isinstance(resume, dict):
        return resume

    # ── Step 1 & 4 & 5: Clean & Truncate Summary ───────────────────────────
    if isinstance(resume.get("summary"), str):
        summary = _scan_and_rephrase_banned_phrases(resume["summary"])
        if original_text:
            summary = _verify_numeric_metrics(summary, original_text)
        summary = smart_truncate(summary, 420)
        summary = _capitalize_sentences(summary)   # Issue 5: auto-capitalize sentence starts
        resume["summary"] = _validate_bold_markers(summary)

    # ── Step 3: Match & Filter Fabricated Entries ───────────────────────────
    if original_text:
        resume = _match_and_filter_entries(resume, original_text)

    # ── Clean Skills Section ───────────────────────────────────────────────
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
            # Issue 10: Docker belongs in devops, never cloud
            "docker": "devops",
            "containers": "devops",
        }

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

        resume["skills"] = {k: skills[k] for k in categories if skills.get(k)}

        if original_text:
            vocab = _extract_original_vocab(original_text)
            for cat in list(resume["skills"].keys()):
                items = resume["skills"].get(cat, [])
                if isinstance(items, list):
                    filtered = [s for s in items if _skill_in_original(s, vocab)]
                    resume["skills"][cat] = filtered if filtered else items

    # ── Experience Bullets Post-Processing ─────────────────────────────────
    for exp in resume.get("experience", []):
        if isinstance(exp, dict) and isinstance(exp.get("bullets"), list):
            cleaned_bullets = []
            for b in exp["bullets"][:5]:
                if not isinstance(b, str) or not b.strip():
                    continue
                bullet = _scan_and_rephrase_banned_phrases(b)
                if original_text:
                    bullet = _verify_numeric_metrics(bullet, original_text)
                bullet = smart_truncate(bullet, 180)
                bullet = _validate_bold_markers(bullet)
                # Issue 9: Detect mid-sentence truncation
                if bullet and not bullet.rstrip().endswith(('.', '!', '?', '"', "'")):
                    logger.warning("Truncated experience bullet detected: '%s...'", bullet[:60])
                if bullet:
                    cleaned_bullets.append(bullet)
            exp["bullets"] = cleaned_bullets

    # ── Project Bullets Post-Processing ────────────────────────────────────
    _BANNED_TECH_STACK = {
        "testing", "unit test", "unit testing", "integration test", "integration testing",
        "automated testing", "web development", "front-end", "back-end", "frontend", "backend",
        "http", "json", "xml", "mvc framework", "mvc", "rest api", "restful api",
        "session management", "extensibility", "reusable components", "best practices",
        "digital transformation", "cloud engineering", "web applications", "web app",
        "problem-solving", "collaboration", "agile", "scrum", "sdlc",
    }

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
            bullets_list = [b for b in raw_bullets if isinstance(b, str) and b.strip()]
        elif isinstance(raw_desc, list) and raw_desc:
            bullets_list = [d for d in raw_desc if isinstance(d, str) and d.strip()]
        elif isinstance(raw_desc, str) and raw_desc.strip():
            plain_desc = raw_desc.replace("**", "").replace("*", "").strip()
            lines = [l.strip() for l in plain_desc.splitlines() if l.strip()]
            if len(lines) <= 1 and ". " in plain_desc:
                lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain_desc) if s.strip()]
            bullets_list = lines

        cleaned_bullets = []
        for b in bullets_list[:4]:
            bullet = _scan_and_rephrase_banned_phrases(b)
            if original_text:
                bullet = _verify_numeric_metrics(bullet, original_text)
            bullet = smart_truncate(bullet, 180)
            bullet = _validate_bold_markers(bullet)
            # Issue 9: Detect mid-sentence truncation
            if bullet and not bullet.rstrip().endswith(('.', '!', '?', '"', "'")):
                logger.warning("Truncated project bullet detected: '%s...'", bullet[:60])
            if bullet:
                cleaned_bullets.append(bullet)
        proj["bullets"] = cleaned_bullets
        proj["description"] = "\n".join(cleaned_bullets)

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
    client, model = _get_cheap_client(model_id)
    response = _create_chat_completion(client, model_id,
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

    response = _create_chat_completion(client, model_id,
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
    resume: dict | str,
    jd_text: str,
    job_analysis: dict | str,
    missing_keywords: list[str],
    model_id: str | None = None,
) -> dict:
    if isinstance(resume, str):
        try:
            resume = json.loads(resume)
        except Exception:
            resume = {"summary": resume}
    if isinstance(job_analysis, str):
        try:
            job_analysis = json.loads(job_analysis)
        except Exception:
            job_analysis = {}

    client, model = _get_client(model_id)
    density_targets = job_analysis.get("keyword_density_targets", [])
    response = _create_chat_completion(client, model_id,
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
    return _clean_resume(result, original_text=json.dumps(resume))


@_safe_call
def generate_cover_letter(
    tailored_resume: dict,
    job_analysis: dict,
    jd_text: str = "",
    model_id: str | None = None,
    rag_context: str = "",
) -> dict:
    """Generate a human cover letter with proper date header, company name, and portfolio links.
    Issues fixed: 1 (generic/robotic), proper header, company name from JD.
    """
    import datetime
    client, model = _get_cheap_client(model_id)
    personal = tailored_resume.get("personal_info", {})
    name = personal.get("name", "the candidate")
    portfolio = personal.get("website", "") or personal.get("portfolio", "")
    github = personal.get("github", "")
    summary = tailored_resume.get("summary", "")
    job_title = job_analysis.get("job_title", "the position")

    # Today's date for the letter header
    today_date = datetime.date.today().strftime("%B %d, %Y")

    # Build concise experience string (company + title + top 2 bullets)
    experience_lines = []
    for exp in tailored_resume.get("experience", [])[:2]:
        bullets = exp.get("bullets", [])[:2]
        bullets_str = " | ".join(bullets)
        experience_lines.append(
            f"{exp.get('title', '')} at {exp.get('company', '')} ({exp.get('start_date', '')}–{exp.get('end_date', '')}): {bullets_str}"
        )
    experience = "\n".join(experience_lines) or "(none)"

    # Build concise projects string
    project_lines = []
    for proj in tailored_resume.get("projects", [])[:3]:
        desc = proj.get("description", "")
        first_bullet = desc.split("\n")[0] if desc else ""
        tech = ", ".join(proj.get("tech_stack", [])[:4])
        project_lines.append(f"{proj.get('name', '')}: {first_bullet} [{tech}]")
    projects = "\n".join(project_lines) or "(none)"

    # Build top skills string
    skills_data = tailored_resume.get("skills", {})
    all_skills = (
        skills_data.get("languages", [])
        + skills_data.get("frameworks", [])
        + skills_data.get("tools", [])
        + skills_data.get("technical", [])   # legacy fallback
        + skills_data.get("databases", [])
    )
    top_skills = ", ".join(all_skills[:10])

    # Pass first 800 chars of JD as raw context so model can extract company name
    jd_snippet = (jd_text or "")[:800]

    response = _create_chat_completion(client, model_id,
        model=model,
        messages=[
            {"role": "system", "content": COVER_LETTER_SYSTEM},
            {
                "role": "user",
                "content": COVER_LETTER_PROMPT.format(
                    name=name,
                    job_title=job_title,
                    today_date=today_date,
                    portfolio=portfolio or "(not provided)",
                    github=github or "(not provided)",
                    summary=summary,
                    experience=experience,
                    projects=projects,
                    skills=top_skills,
                    jd_snippet=jd_snippet or "(not provided)",
                    job_analysis=json.dumps(job_analysis),
                    rag_context=rag_context or "(none)",
                ),
            },
        ],
        temperature=0.3,
        max_tokens=700,
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
    """Generate a professional application email with greeting, links, and sign-off.
    Issues fixed: 2 (too short, no greeting, no links).
    """
    client, model = _get_cheap_client(model_id)
    personal = tailored_resume.get("personal_info", {})
    name = personal.get("name", "the candidate")
    portfolio = personal.get("website", "") or personal.get("portfolio", "")
    github = personal.get("github", "")
    summary = tailored_resume.get("summary", "")
    job_title = job_analysis.get("job_title", "the position")

    # Build concise experience/projects summary
    exp_proj_lines = []
    for exp in tailored_resume.get("experience", [])[:1]:
        exp_proj_lines.append(f"{exp.get('title')} at {exp.get('company')}")
    for proj in tailored_resume.get("projects", [])[:2]:
        first_bullet = ""
        desc = proj.get("description", "")
        if desc:
            first_bullet = " — " + desc.split("\n")[0][:80]
        exp_proj_lines.append(f"{proj.get('name')}{first_bullet}")
    experience_projects = "\n".join(exp_proj_lines) or "(none)"

    skills_data = tailored_resume.get("skills", {})
    all_skills = (
        skills_data.get("languages", [])
        + skills_data.get("frameworks", [])
        + skills_data.get("tools", [])
        + skills_data.get("technical", [])   # legacy fallback
        + skills_data.get("databases", [])
    )
    top_skills = ", ".join(all_skills[:8])

    response = _create_chat_completion(client, model_id,
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
                    portfolio=portfolio or "(not provided)",
                    github=github or "(not provided)",
                    job_analysis=json.dumps(job_analysis),
                    rag_context=rag_context or "(none)",
                ),
            },
        ],
        temperature=0.3,
        max_tokens=600,   # Issue 2: was 300 — doubled to allow full email with greeting + sign-off
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))

@_safe_call
def suggest_job_search_params(resume_text: str, model_id: str | None = None) -> dict:
    """Analyze a raw resume and suggest the best job search term and location."""
    client, model = _get_cheap_client(model_id)
    response = _create_chat_completion(client, model_id,
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
    client, model = _get_cheap_client(model_id)
    response = _create_chat_completion(client, model_id,
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
    client, model = _get_cheap_client(model_id)

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

    response = _create_chat_completion(client, model_id,
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

{adaptive_context}

Return JSON:
{{
  "critical_gaps": ["keyword that is completely absent from resume with no bridgeable equivalent"],
  "quick_wins": ["keyword present in wrong section — just move it"],
  "section_priorities": {{
    "summary": "1-3 concise lines following the strict formula: Identity -> Core Tech -> Evidence -> Value.",
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
    adaptive_report: dict | None = None,  # NEW: from adaptive_gap.adaptive_gap_diff()
) -> dict:
    """
    Dedicated gap analysis agent.
    Uses cheap model — sends only section summaries, not full resume.
    Returns section-level instructions so the rewriter only touches what needs work.

    When adaptive_report is provided, the prompt is enriched with:
    - Bridgeable gap framing (auto-generated bridge sentences)
    - Implicit domain expectations (HM assumes even if not in JD)
    - Critical gaps (truly missing, no bridge)
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

    # Build adaptive context block if available
    adaptive_context = ""
    if adaptive_report:
        try:
            from services.adaptive_gap import build_gap_context_for_rewrite
            adaptive_context = build_gap_context_for_rewrite(adaptive_report)
        except Exception as _e:
            logger.warning("adaptive gap context injection failed: %s", _e)

    response = _create_chat_completion(client, model_id,
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
                    adaptive_context=adaptive_context,
                ),
            },
        ],
        temperature=0.1,
        max_tokens=900,
        response_format={"type": "json_object"},
    )
    return _parse_json_response(_extract_content(response))


# ── Adaptive Gap wrappers (thin; all prompt logic lives in adaptive_gap.py) ───


def classify_role_domain(jd_text: str, model_id: str | None = None) -> dict:
    """Domain classifier — delegates to adaptive_gap service."""
    from services.adaptive_gap import classify_role_domain as _classify
    return _classify(jd_text, model_id)


def build_capability_graph(resume_json: dict, model_id: str | None = None) -> dict:
    """Capability graph builder — delegates to adaptive_gap service."""
    from services.adaptive_gap import build_capability_graph as _build
    return _build(resume_json, model_id)


# Section rewrite prompts — one per section type for focused, lean prompts
_SECTION_SYSTEMS = {
    "summary": """You rewrite ONLY the resume summary section. Write strictly 1–3 concise lines.
MUST follow this fixed formula: Identity -> Core Tech -> Evidence (Built/Deployed...) -> Value.
Never use generic AI fluff or write 'Experienced in'. Use strong verbs like Built, Designed, Implemented.
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
Align projects dynamically to emphasize capabilities matching the target role (Backend focus on APIs/DB/Auth/Architecture; Frontend on UI/UX/state; AI on LLMs/RAG/agents; Cloud on DevOps/CI-CD).
Strictly sort the projects array in descending order of relevance to the target job description (most relevant project first).
Bullet 1: WHY the project exists (value proposition & core engineering challenge solved).
Bullet 2: HOW it was built (your specific engineering contributions, e.g., "Designed REST APIs" instead of "Used REST APIs").
Bullet 3-4: WHAT impact/functionality it delivers (scale, latency reduction, performance metrics, testing).
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
    response = _create_chat_completion(client, model_id,
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

    response = _create_chat_completion(client, model_id,
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

    response = _create_chat_completion(client, model_id,
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


LINKEDIN_MESSAGE_SYSTEM = """You write a LinkedIn connection note asking for a referral. Hard limit: 300 characters.

RULES:
- Open with "Hi there," — NEVER write "Hi [Name]" or "Hi [First Name]" (those are unfilled placeholders).
- Name the company and the specific role.
- Include one short fact about the candidate that makes them a fit (a project name or a skill — not a vague claim).
- End with a polite one-line ask.
- Sound like a real person, not a template.
- Return ONLY valid JSON."""

LINKEDIN_MESSAGE_PROMPT = """Write a LinkedIn referral request note for {name} applying for {job_title} at {company_name}.

Top skills: {top_skills}
Strongest project: {top_project}

Return JSON:
{{
  "message": "Hi there, ...",
  "_note": "Replace 'Hi there' with the recruiter's first name if you know it."
}}
The message MUST be under 300 characters. Sound like a real person."""


@_safe_call
def generate_linkedin_message(
    tailored_resume: dict,
    job_analysis: dict,
    model_id: str | None = None,
    jd_text: str = "",
) -> dict:
    """Generate a ≤300-char LinkedIn connection request note. Uses cheap model.
    Issue 3: Uses 'Hi there,' as the opener — never '[Name]' or '[First Name]' placeholders.
    Caller should replace 'Hi there,' with the recruiter's actual name if known.
    """
    client, model = _get_cheap_client(model_id)

    personal = tailored_resume.get("personal_info", {})
    name = personal.get("name", "the candidate")
    job_title = job_analysis.get("job_title", "the position")

    # Try to extract company name: prefer job_analysis.company_name, fall back to searching JD
    company_name = job_analysis.get("company_name", "").strip()
    if not company_name:
        # Heuristic: look for "at <Company>" or "<Company> is hiring" in first 400 chars of JD
        jd_head = (jd_text or "")[:400]
        match = re.search(
            r'(?:at|@|from|join|by|with)\s+([A-Z][A-Za-z0-9&.,\s]{1,40}?)(?:\s+is|\s+are|\.|,|\n)',
            jd_head
        )
        company_name = match.group(1).strip() if match else job_analysis.get("company_type", "the company")

    skills_data = tailored_resume.get("skills", {})
    top_skills = ", ".join(
        (skills_data.get("languages", [])[:2] + skills_data.get("frameworks", [])[:2])[:3]
    )

    projects = tailored_resume.get("projects", [])
    top_project = projects[0].get("name", "") if projects else ""

    response = _create_chat_completion(client, model_id,
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
                    company_name=company_name,
                ),
            },
        ],
        temperature=0.2,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    result = _parse_json_response(_extract_content(response))
    # Enforce 300-char limit on message
    if isinstance(result.get("message"), str):
        msg = result["message"]
        # Guarantee no literal placeholder leaks through
        msg = re.sub(r'\[(?:Name|First\s*Name|Last\s*Name|Recruiter)\]', 'Hi there,', msg, flags=re.IGNORECASE)
        if len(msg) > 300:
            msg = msg[:297] + "..."
        result["message"] = msg
    # Always emit the user-facing note
    result.setdefault("_note", "Replace 'Hi there,' with the recruiter's first name if known.")
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

    response = _create_chat_completion(client, model_id,
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

# =============================================================================
# V4 12-STAGE PIPELINE AGENTS
# =============================================================================

@_safe_call
def analyze_career_identity(resume_text: str, model_id: str | None = None) -> dict:
    client, model = _get_cheap_client(model_id)
    system_prompt = """You are the Career Identity Agent.
Analyze the raw resume and definitively declare the candidate's primary role and identity.
Output JSON:
{
  "primary_role": "Backend Developer / Data Scientist / etc",
  "confidence": 95,
  "supporting_evidence": ["Python (4 yrs)", "Built REST APIs", "AWS"],
  "weak_areas": ["Frontend", "Leadership"]
}
"""
    response = _create_chat_completion(client, model_id,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"RESUME:\n{resume_text}"}
        ],
        temperature=0.2,
        max_tokens=500,
        response_format={"type": "json_object"}
    )
    return _parse_json_response(_extract_content(response))

@_safe_call
def map_evidence(resume_data: dict, jd_analysis: dict, model_id: str | None = None) -> dict:
    client, model = _get_cheap_client(model_id)
    system_prompt = """You are the Evidence Mapper.
Map the candidate's parsed history directly to the Job Description requirements.
For each JD requirement (must-have and preferred), find exact matching evidence from the resume.
Output JSON:
{
  "evidence_map": {
    "Python": ["Used Python in Project X", "5 years experience at Company Y"],
    "Docker": []
  },
  "verified_score": 85
}
"""
    import json
    response = _create_chat_completion(client, model_id,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"JD ANALYSIS:\n{json.dumps(jd_analysis)}\n\nRESUME:\n{json.dumps(resume_data)}"}
        ],
        temperature=0.2,
        max_tokens=1500,
        response_format={"type": "json_object"}
    )
    return _parse_json_response(_extract_content(response))

@_safe_call
def review_hr(resume_data: dict, model_id: str | None = None) -> dict:
    client, model = _get_cheap_client(model_id)
    system_prompt = """You are a real corporate HR recruiter screening this resume for the first time (20-second scan).
Be honest and decisive — like you would for a real open role.

Output JSON only:
{
  "first_impression": "one sentence gut reaction",
  "perceived_role": "what role this person seems to fit",
  "trustworthy_elements": ["concrete strengths you notice"],
  "generic_elements": ["vague or template-sounding parts"],
  "confusing_elements": ["things that would make you pause"],
  "rejection_risks": ["why an HR screen might reject"],
  "issues_to_fix": ["specific resume fixes needed before shortlist, empty if none"],
  "shortlist_decision": "YES or NO",
  "signal": "GREEN or RED",
  "signal_reason": "one sentence why green or red",
  "hr_readability_score": 0-100
}

Rules:
- signal=GREEN only if shortlist_decision=YES and you would send this to a hiring manager.
- signal=RED if you would reject or send back for revision.
- Be specific; do not invent experience.
"""
    import json
    response = _create_chat_completion(client, model_id,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"RESUME:\n{json.dumps(resume_data)}"}
        ],
        temperature=0.4,
        max_tokens=900,
        response_format={"type": "json_object"}
    )
    result = _parse_json_response(_extract_content(response))
    decision = str(result.get("shortlist_decision", "NO")).upper()
    if "YES" in decision:
        result["shortlist_decision"] = "YES"
        result.setdefault("signal", "GREEN")
    else:
        result["shortlist_decision"] = "NO"
        result["signal"] = "RED"
    return result

@_safe_call
def review_hiring_manager(resume_data: dict, model_id: str | None = None) -> dict:
    client, model = _get_cheap_client(model_id)
    system_prompt = """You are a real technical hiring manager / senior engineer reviewing this resume for an interview decision.
Judge technical depth, credibility of claims, and whether you would interview this person.

Output JSON only:
{
  "interview_decision": "YES or NO",
  "signal": "GREEN or RED",
  "signal_reason": "one sentence why green or red",
  "reason": "brief overall judgment",
  "weak_bullets": ["bullets that feel weak or fluffy"],
  "exaggerated_tech": ["tech claims that look overstated"],
  "interview_defense_concerns": ["questions you would grill them on"],
  "issues_to_fix": ["specific technical resume fixes needed, empty if none"],
  "hm_confidence_score": 0-100
}

Rules:
- signal=GREEN only if interview_decision=YES.
- signal=RED if you would pass or demand a rewrite first.
- Do not invent projects or skills.
"""
    import json
    response = _create_chat_completion(client, model_id,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"RESUME:\n{json.dumps(resume_data)}"}
        ],
        temperature=0.4,
        max_tokens=900,
        response_format={"type": "json_object"}
    )
    result = _parse_json_response(_extract_content(response))
    decision = str(result.get("interview_decision", "NO")).upper()
    if "YES" in decision:
        result["interview_decision"] = "YES"
        result.setdefault("signal", "GREEN")
    else:
        result["interview_decision"] = "NO"
        result["signal"] = "RED"
    return result

@_safe_call
def review_jd_poster(
    rewritten_resume: dict,
    original_resume_text: str,
    job_analysis: dict,
    jd_text: str,
    model_id: str | None = None,
) -> dict:
    """Founder / hiring manager who wrote the JD — final stakeholder review + evidence check."""
    client, model = _get_cheap_client(model_id)
    system_prompt = """You are the founder / hiring lead who wrote this job description.
You are reviewing a tailored resume against YOUR posting.

Do two jobs:
1) Evidence check — strip or rewrite any claim not supported by the ORIGINAL resume text.
2) Hiring call — would YOU shortlist this person for your role?

Output JSON only:
{
  "fact_checked_resume": { ...same resume structure, evidence-safe... },
  "stripped_claims": ["unsupported claims removed or softened"],
  "role_fit_notes": ["how well they match the JD priorities"],
  "missing_for_role": ["JD requirements still weak or missing"],
  "issues_to_fix": ["what must be fixed before you hire-signal green, empty if ready"],
  "hire_decision": "YES or NO",
  "signal": "GREEN or RED",
  "signal_reason": "one sentence final stakeholder judgment",
  "final_call": "one clear sentence: Interview / Revise / Pass — and why",
  "evidence_credibility_score": 0-100
}

Rules:
- Never invent experience. Prefer honesty over keyword stuffing.
- signal=GREEN only if hire_decision=YES and evidence looks solid for this JD.
- Keep fact_checked_resume complete and valid JSON matching the input resume shape.
"""
    import json
    response = _create_chat_completion(client, model_id,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"JOB TITLE: {job_analysis.get('job_title', '')}\n"
                    f"JD ANALYSIS:\n{json.dumps(job_analysis)}\n\n"
                    f"JOB DESCRIPTION:\n{jd_text[:4000]}\n\n"
                    f"ORIGINAL RESUME TEXT:\n{original_resume_text[:6000]}\n\n"
                    f"TAILORED RESUME JSON:\n{json.dumps(rewritten_resume)}"
                ),
            },
        ],
        temperature=0.25,
        max_tokens=4200,
        response_format={"type": "json_object"}
    )
    result = _parse_json_response(_extract_content(response))
    decision = str(result.get("hire_decision", "NO")).upper()
    if "YES" in decision:
        result["hire_decision"] = "YES"
        result.setdefault("signal", "GREEN")
    else:
        result["hire_decision"] = "NO"
        result["signal"] = "RED"
    if not isinstance(result.get("fact_checked_resume"), dict):
        result["fact_checked_resume"] = rewritten_resume
    return result

@_safe_call
def rewrite_human_tone(resume_data: dict, mapped_evidence: dict, hr_review: dict, hm_review: dict, identity: dict, model_id: str | None = None) -> dict:
    client, model = _get_client(model_id)
    system_prompt = """You are an experienced resume writer hired after HR and a technical hiring manager reviewed this draft.
Rewrite the resume so it sounds human and addresses their RED flags / issues_to_fix.

Constraints:
- Avoid AI buzzwords and empty filler.
- Base EVERY bullet ONLY on mapped_evidence / proven experience.
- Fix issues flagged in hr_review and hm_review.
- Enforce identity.primary_role.
Output exactly the same JSON structure as the input resume, fully rewritten.
"""
    import json
    response = _create_chat_completion(client, model_id,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"RESUME:\n{json.dumps(resume_data)}\n\nEVIDENCE:\n{json.dumps(mapped_evidence)}\n\nHR REVIEW:\n{json.dumps(hr_review)}\n\nHM REVIEW:\n{json.dumps(hm_review)}\n\nIDENTITY:\n{json.dumps(identity)}"}
        ],
        temperature=0.4,
        max_tokens=4000,
        response_format={"type": "json_object"}
    )
    return _parse_json_response(_extract_content(response))

@_safe_call
def fact_check(rewritten_resume: dict, original_resume_text: str, model_id: str | None = None) -> dict:
    """Legacy alias — prefer review_jd_poster for full stakeholder review."""
    client, model = _get_client(model_id)
    system_prompt = """You are checking resume evidence honesty before a founder/hiring lead reviews it.
If ANY claim, number, or technology cannot be proven by original_resume_text, strip it or rewrite honestly.
Output JSON:
{
  "fact_checked_resume": { ... },
  "stripped_claims": ["..."],
  "evidence_credibility_score": 95
}
"""
    import json
    response = _create_chat_completion(client, model_id,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"ORIGINAL:\n{original_resume_text}\n\nREWRITTEN:\n{json.dumps(rewritten_resume)}"}
        ],
        temperature=0.2,
        max_tokens=4000,
        response_format={"type": "json_object"}
    )
    return _parse_json_response(_extract_content(response))
