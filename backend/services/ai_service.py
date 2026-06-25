import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Model Registry ────────────────────────────────────────────────────────

MODEL_REGISTRY: dict[str, dict] = {}
_clients: dict[str, OpenAI] = {}


_PLACEHOLDER_FRAGMENTS = ("YOUR_", "_HERE", "CHANGE_THIS", "placeholder", "example")


def _is_placeholder(value: str) -> bool:
    return not value or any(p in value for p in _PLACEHOLDER_FRAGMENTS)


def _register_models():
    """Build model registry from environment variables."""
    global MODEL_REGISTRY
    MODEL_REGISTRY = {}

    # Qwen
    qwen_key = os.environ.get("QWEN_API_KEY", "")
    if not _is_placeholder(qwen_key):
        MODEL_REGISTRY["qwen"] = {
            "id": "qwen",
            "display_name": "Qwen 2.5",
            "endpoint": os.environ.get("QWEN_ENDPOINT", "https://bedrock-mantle.us-east-1.api.aws/v1"),
            "api_key": qwen_key,
            "model": os.environ.get("QWEN_MODEL", "qwen2.5-72b-instruct"),
        }

    # GLM-5
    glm_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
    glm_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    if not _is_placeholder(glm_key) and glm_endpoint:
        MODEL_REGISTRY["glm"] = {
            "id": "glm",
            "display_name": "GLM-5 (Recommended)",
            "endpoint": glm_endpoint,
            "api_key": glm_key,
            "model": os.environ.get("AZURE_OPENAI_DEPLOYMENT", "zai.glm-5"),
        }

    # GLM-4.7 Flash
    glm_flash_key = os.environ.get("GLM_FLASH_API_KEY", "")
    glm_flash_endpoint = os.environ.get("GLM_FLASH_ENDPOINT", "")
    if not _is_placeholder(glm_flash_key) and glm_flash_endpoint:
        MODEL_REGISTRY["glm-flash"] = {
            "id": "glm-flash",
            "display_name": "GLM-4.7 Flash",
            "endpoint": glm_flash_endpoint,
            "api_key": glm_flash_key,
            "model": os.environ.get("GLM_FLASH_MODEL", "zai.glm-4.7-flash"),
            "admin_only": False,
        }

    # DeepSeek-V4-Flash (admin-only — not shown to public users)
    ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
    ds_endpoint = os.environ.get("DEEPSEEK_ENDPOINT", "")
    if not _is_placeholder(ds_key) and ds_endpoint:
        MODEL_REGISTRY["deepseek"] = {
            "id": "deepseek",
            "display_name": "DeepSeek-V4-Flash",
            "endpoint": ds_endpoint,
            "api_key": ds_key,
            "model": os.environ.get("DEEPSEEK_MODEL", "DeepSeek-V4-Flash"),
            "admin_only": True,   # only returned to admin users
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
  "company_type": "startup/enterprise/agency/...",
  "seniority": "intern/junior/mid/senior/lead/principal/...",
  "required_skills": ["every hard skill explicitly required — include exact names like 'Node.js', 'PostgreSQL', 'REST API'"],
  "preferred_skills": ["nice-to-have skills explicitly mentioned"],
  "key_responsibilities": ["core duties described in the JD — use exact JD phrasing"],
  "industry_keywords": ["domain-specific terms, methodologies, patterns — e.g. 'microservices', 'CI/CD', 'Agile', 'SDLC'"],
  "tone": "formal/casual/technical/...",
  "must_have": ["hard requirements that MUST appear on the resume — degrees, certs, specific tools"],
  "exact_keywords": ["every specific term worth ATS-matching: tool names, framework names, language names, methodology names, certification names — include both common variants e.g. 'Node.js' AND 'NodeJS', 'REST API' AND 'RESTful API', 'JavaScript' AND 'JS' where both appear in the JD"],
  "keyword_density_targets": ["top 6-8 highest-priority keywords to cover naturally somewhere in the resume, without forcing repetition in every section"],
  "rewrite_strategy": "one sentence: what to prioritize in the rewrite based on the JD requirements"
}}

JOB DESCRIPTION:
{jd}"""

REWRITE_SYSTEM = """You are an expert ATS resume writer and software engineering resume formatter.

Your task is to improve and restructure an existing resume while preserving all truthful information,
technologies, education, experience, projects, dates, companies, links, and the candidate's professional identity.

INTEGRITY RULES:
- Do NOT invent fake experience, metrics, companies, credentials, tools, deployments, APIs, users, or achievements.
- Do NOT remove important technologies or projects that are already present.
- Do NOT change the candidate's overall professional identity.
- If a section already looks strong, leave its meaning mostly unchanged.
- The resume text may end with a "Hyperlinks:" section — use those URLs for linkedin, github, website fields.
- Use ONLY the dates, company names, and project names exactly as they appear in the input. Do not reformat, approximate, or invent any of them.
- Where the original resume contains real counts (number of services, endpoints, team size, deployment platform), preserve and use them naturally. Never add numbers that are not in the original.

TARGET PROFILE:
- Optimize for Software Engineer Intern, Full Stack Developer, Python Developer, MERN Stack Developer, and Backend Developer roles.
- Make the resume sound like a polished fresher or early-career software engineering resume — honest about being early-career, not a corporate mission statement.

WRITING STYLE:
- Professional, concise, technical, human-written, and recruiter-friendly.
- Vary bullet openers naturally: some start with an action verb (Built, Integrated, Debugged), some start with a technology name ("React dashboard for..."), some lead with context ("As part of the backend team..."). Avoid starting every bullet the same way.
- Use strong but realistic action verbs: built, developed, implemented, integrated, debugged, optimized, deployed, designed, wrote, configured, migrated.
- Avoid fluff, repetitive wording, excessive buzzwords, and keyword stuffing.
- NEVER use these overused buzzwords: spearheaded, orchestrated, synergized, revolutionized, pioneered, championed, leveraged, utilized.
- Keep bullets factual: what was built, which specific technologies were used, and what practical result or feature was delivered.
- Each experience bullet must describe one specific task or outcome — not a generic responsibility. Avoid meaningless filler like "collaborated using Git" or "participated in Agile". Instead write the actual task: what was the problem, what was done, what technology was used.

ONE-PAGE FORMAT RULES:
- The final resume must fit naturally on one A4 page.
- Keep summary to EXACTLY 2 sentences maximum. First sentence: who you are + core stack. Second sentence: one specific achievement or context. Do NOT mention the target company or job title by name — keep it general. Do NOT write more than 2 sentences.
- Keep the summary human and readable. Avoid listing more than 3 technologies in the summary, even if the JD contains many keywords.
- Keep experience to max 3 roles and max 3 bullets per role.
- Keep projects to the most relevant 2-3 projects.
- Because the app schema has one project description field, write each project description as 2-3 concise bullet points separated by \n (newline character). Never collapse to fewer than 2 lines.
- For the strongest/most complex project use 3 bullets. For simpler side projects, 2 bullets is enough. Do not pad weaker projects to match stronger ones.
- Do not overcrowd sections. Prefer clear, compact writing over long paragraphs.
- Maximum 3 certifications.

PROJECT RULES:
- Improve projects significantly while preserving truthfulness.
- Each project has a separate tech_stack array that is displayed right below the project name. Because of this, DO NOT repeat or re-list the same technology names inside the description bullets. The bullets should describe WHAT was built and HOW it works — not name-drop the same tools already visible in tech_stack.
  BAD bullet: "Built with React.js frontend and Node.js/Express.js backend with JWT authentication"  (tech already in tech_stack)
  GOOD bullet: "Full-stack task manager with JWT-protected REST endpoints and role-based access control"  (describes behaviour, not the tools)
- Write bullets around FEATURES, ARCHITECTURE, and OUTCOMES — not around technology names.
- Only name a specific technology in a bullet when it adds meaningful context not obvious from the tech_stack (e.g. "used Mongoose virtuals to avoid redundant DB calls", "server-side rendering via Next.js for SEO").
- Each bullet must be one tight sentence — no run-on clauses joined by semicolons.
- 2-3 bullets per project maximum; no padding.
- Make projects technically mature without sounding fake.
- Do not claim deployments, auth, databases, metrics, or cloud usage unless they appear in the original resume or job context.

EXPERIENCE RULES:
- Rewrite internships or early-career work professionally.
- Each bullet must describe a specific task, not a generic role description. Name the actual component, module, or system worked on.
- Highlight APIs, microservices, React integration, cloud deployment, debugging, Agile/SCRUM, and collaboration only when supported by existing information.
- Keep it realistic for a fresher.

SKILLS SECTION RULES:
- Organize skills into exactly these 5 JSON categories:
  languages  = Programming languages only (e.g. Python, JavaScript, Java, C++, TypeScript)
  frameworks = Frameworks AND libraries AND runtime environments (e.g. React, Django, Express.js, Node.js, Spring Boot)
  databases  = Database systems only (e.g. MySQL, PostgreSQL, MongoDB, SQLite, Redis)
  tools      = Dev tools, platforms, cloud, DevOps, version control, CI/CD (e.g. Git, Docker, AWS, GitHub Actions)
  concepts   = Methodologies and named patterns ONLY (e.g. REST API, Agile/SCRUM, OOP, MVC, SDLC, JWT, CI/CD)
- ONLY list specific recognizable technologies, languages, frameworks, databases, tools, and named methodologies.
- NEVER include ANY of the following as skills — they are soft skills or filler, not technical skills:
  "problem-solving", "analytical skills", "team collaboration", "communication", "testing" (generic),
  "best practices", "best development practices", "web development", "application development",
  "digital transformation", "enterprise software services", "cloud engineering services", "mobility solutions",
  "server-side programming", "web and server-side programming", "session management",
  "modern technologies", "technical tools", "systems", "products", "projects", "requirements",
  "practices", "overview", "software development", "cloud infrastructure", "cross-functional",
  "development tools", "front-end", "back-end", "HTTP", "JSON", "extensibility", "reusable components".
- "unit test", "integration test", "automated testing" are NOT skills — omit them from skills entirely.
- Max per category: languages 6, frameworks 6, databases 4, tools 6, concepts 5.
- Keep each category SHORT and clean. A recruiter should be able to scan it in 3 seconds.

ATS RULES — TARGET HIGH MATCH WITHOUT OVERSTUFFING:
- Cover EVERY term in job_analysis.required_skills and job_analysis.must_have. Missing even one required skill drops the ATS score significantly.
- Cover as many terms as possible from job_analysis.preferred_skills and job_analysis.industry_keywords.
- Use exact JD phrasing for keywords — ATS systems match exact strings. If the JD says "Node.js", write "Node.js" not "NodeJS". If it says "RESTful API", write "RESTful API".
- For the top 6-8 priority keywords (job_analysis.keyword_density_targets), cover them naturally across the resume, but do not repeat the same term in every section.
- Weave keywords into natural sentences — do not list them separately or pad bullets with keyword dumps.
- If a keyword already appears clearly in one section, do not repeat it just to increase density unless it genuinely improves readability.
- Keep formatting ATS-readable: no tables, icons, graphics, or complex wording in returned content.
- Use both common variants where both appear in the JD (e.g. "REST API" and "RESTful API", "JavaScript" and "JS").
- Add ADJACENT IMPLIED SKILLS: If the JD requires a skill the candidate almost certainly has based on their existing stack, add it naturally. Rules:
  * React/Vue/Angular developer → can add HTML, CSS, JavaScript if not already listed
  * Any backend developer → can add REST API, HTTP, JSON if not already listed
  * Python developer → can add OOP, scripting if not already listed
  * Anyone using GitHub → can add Git, version control if not already listed
  * Anyone using any cloud service → can add cloud computing concept if missing
  * Fresher who built web projects → can add HTML, CSS, responsive design if relevant to JD
  * Anyone using SQL (MySQL/PostgreSQL/SQLite) → can add SQL, relational database
  * Anyone using NoSQL → can add NoSQL, document database
  These are REALISTIC additions — a candidate with these skills would naturally know the adjacent ones. Do NOT add unrelated skills (e.g. don't add Kubernetes to someone with no DevOps background).
- Fill each project's tech_stack array with ONLY real named technologies: languages, frameworks, databases, and tools actually used (e.g. React, Node.js, MySQL, JWT, Git, Render). MAX 8 items per project.
- NEVER put generic words in tech_stack: no "testing", "unit test", "integration test", "front-end", "back-end", "web development", "HTTP", "JSON", "MVC Framework", "REST API" — these are concepts, not technologies. Keep tech_stack clean and scannable.

EMPHASIS RULES:
- Use **double asterisks** only for important technologies, metrics already present, and a few job-matching keywords. Do not bold every tech term.
- Bold 2-3 key terms per bullet at most.
- Never bold entire sentences.

Return ONLY valid JSON — use ** only for inline emphasis inside string values."""

REWRITE_PROMPT = """Improve and tailor the candidate's resume for this role using the system rules.
Focus mainly on projects, bullet quality, one-page balance, technical clarity, and ATS readability.

{keyword_injection}

EXISTING RESUME:
{resume}

JOB ANALYSIS:
{job_analysis}

ORIGINAL JOB DESCRIPTION:
{jd}

Return JSON with EXACTLY this shape:
{{
  "personal_info": {{
    "name": "...", "email": "...", "phone": "...", "location": "...",
    "linkedin": "...", "github": "...", "website": "..."
  }},
  "summary": "2-3 lines in implied first-person tone — honest, specific to the candidate's actual stack, early-career but confident. Example: 'MCA graduate with hands-on experience building full-stack web applications using **Python** and **React**. Worked on backend services during internship at CrystalTech and is comfortable with REST APIs, SQL/NoSQL databases, and SDLC workflows.'",
  "experience": [{{
    "title": "...", "company": "...", "location": "...",
    "start_date": "Mon YYYY", "end_date": "Mon YYYY or Present",
    "bullets": ["Designed and built **3 REST API** endpoints in **Express.js** for user authentication, reducing login latency by removing redundant DB calls", "**Node.js** background job to process and cache report data, used by the React dashboard for real-time display", "..."]
  }}],
  "education": [{{
    "degree": "...", "institution": "...", "location": "...",
    "graduation_year": "YYYY", "gpa": "...", "honors": "..."
  }}],
  "skills": {{"languages": ["**Python**", "JavaScript"], "frameworks": ["**React**", "Django", "Express.js"], "databases": ["**MongoDB**", "PostgreSQL"], "tools": ["**AWS**", "Docker", "Git"], "concepts": ["REST API", "Agile/SCRUM", "OOP"]}},
  "certifications": [{{"name": "...", "issuer": "...", "year": "..."}}],
  "projects": [{{
    "name": "...", "description": "Full-stack task manager with **JWT-protected** REST endpoints and role-based access for three user levels.\nRelational schema designed from scratch; queries optimised to avoid N+1 fetches on the dashboard feed.\nDeployed with environment-based config and production build; structured for easy local setup and CI pipeline.", "tech_stack": ["React.js", "Node.js", "Express.js", "MySQL", "JWT", "Render", "Git"], "link": "...", "live_link": "..."
  }}]
}}
Leave fields as "" or [] if the original has no data. Never invent companies or credentials."""

ATS_IMPROVE_SYSTEM = """You are an ATS optimization specialist and software engineering resume editor.
Your goal: improve keyword coverage, project clarity, and bullet quality WITHOUT making the resume sound fake or robotic.

CRITICAL RULES:
- DO NOT add new experiences or projects — only rewrite existing ones
- Integrate missing keywords by replacing weaker words in existing bullets
- Keep the same page budget: max 3 experiences, 3 bullets each, 2-3 projects
- Keep bullets concise, polished, and one-page friendly
- Use professional but human language — if a bullet sounds like corporate jargon, rewrite it
- Vary bullet openers: some start with an action verb, some with a technology name, some with context. Never start every bullet the same way.
- Each bullet must describe a specific task — not a generic responsibility. Avoid "collaborated using Git" or "participated in Agile". Write the actual task.
- Extract and name specific libraries, packages, and platforms from the original input. Specificity sounds human and genuine.
- NEVER use overused buzzwords: spearheaded, orchestrated, synergized, revolutionized, pioneered, championed, leveraged, utilized.
- Write full phrases before abbreviations: "Amazon Web Services (AWS)"
- Weave keywords into the most natural section, and only repeat the strongest few across a second section when it reads cleanly.
- Do NOT fabricate anything
- Keep **bold** emphasis on metrics, tech names, and JD keywords (2-3 per bullet)
- Improve project descriptions with what was built, features, architecture, and outcomes — NOT by repeating tech names already listed in the tech_stack array. Bullets describe behaviour and results; tech_stack lists the tools.
- Preserve truthful technologies, education, experience, projects, and professional identity
- Keep the resume visually balanced and suitable for one A4 page
- Order technical skills so the most job-relevant ones come first; primary languages before frameworks, frameworks before tools.

SKILLS SECTION — DO NOT POLLUTE:
- Organize skills using exactly these 5 JSON categories:
  languages  = Programming languages only (Python, JavaScript, Java, etc.)
  frameworks = Frameworks, libraries, runtimes (React, Django, Express.js, Node.js, etc.)
  databases  = Database systems only (MySQL, PostgreSQL, MongoDB, etc.)
  tools      = Dev tools, platforms, cloud, DevOps, CI/CD (Git, Docker, AWS, etc.)
  concepts   = Named methodologies and patterns ONLY (REST API, Agile/SCRUM, OOP, MVC, SDLC, JWT, CI/CD)
- Only add REAL technology names or named methodologies to skills.
- STRICT BAN — NEVER add these as skills under any circumstances:
  "problem-solving", "analytical skills", "team collaboration", "communication",
  "testing", "unit test", "integration test", "automated testing",
  "best practices", "best development practices", "digital transformation",
  "enterprise software services", "cloud engineering services", "mobility solutions",
  "web and server-side programming", "session management", "HTTP", "JSON",
  "extensibility", "reusable components", "front-end", "back-end", "web development",
  "software development", "cloud infrastructure", "modern technologies", "technical tools".
- If a missing keyword is a soft skill or generic term, weave it into a bullet sentence — NEVER put it in skills.
- Max per category: languages 6, frameworks 6, databases 4, tools 6, concepts 5. Keep it SHORT.

- Return ONLY valid JSON"""

ATS_IMPROVE_PROMPT = """Your goal: improve ATS coverage by integrating the missing keywords naturally without turning the resume into a keyword wall.

MISSING KEYWORDS — integrate each one only when it fits naturally and truthfully:
{missing_keywords}

KEYWORD DENSITY TARGETS from job analysis (cover these naturally, but avoid repeating them in every section):
{density_targets}

MANDATORY COVERAGE CHECKLIST:
- Every keyword in the missing list should appear somewhere in the final resume if it can be added truthfully and naturally.
- Priority keywords may appear in one strong section instead of being repeated in every section.
- Use exact JD phrasing — ATS matches exact strings. Do not substitute synonyms for keywords.
- Integrate naturally into existing bullets by replacing weaker words — do not create keyword dumps.
- Add ADJACENT IMPLIED SKILLS that are missing but realistically held by the candidate:
  * React/Vue/Angular → HTML, CSS, JavaScript (if not listed)
  * Any backend dev → REST API, HTTP, JSON (if not listed)
  * Python dev → OOP, scripting (if not listed)
  * GitHub user → Git, version control (if not listed)
  * SQL user → SQL, relational database (if not listed)
  * NoSQL user → NoSQL, document database (if not listed)
  Add these to the skills section only if they are genuinely related to the candidate's existing stack.
- Fill each project's tech_stack array with the core stack only. Do not pad it with every adjacent tool or repeat technologies already obvious from the description.

CURRENT RESUME (JSON):
{resume}

JOB ANALYSIS:
{job_analysis}

ORIGINAL JOB DESCRIPTION:
{jd}

Return the improved resume with the EXACT same JSON shape."""

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

JD TEXT (use exact phrasing where it fits naturally):
{jd}

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

Return JSON with this exact shape:
{{
  "subject_line": "...",
  "body": "..."
}}"""


# ── Post-processing ───────────────────────────────────────────────────────────

# Generic filler words that should never appear as standalone skills
_BANNED_SKILLS = {
    "modern technologies", "technical tools", "systems", "products", "projects",
    "requirements", "practices", "overview", "software development",
    "cloud infrastructure", "best practices", "development tools",
    "web development", "application development", "cross-functional",
    "agile development", "nosql database", "modern", "technologies",
    "technical", "tools", "development", "infrastructure", "scalable",
    "performance", "speed", "building", "extensive", "advanced",
    "professional", "strong", "excellent", "proven", "hands-on",
    "experience", "knowledge", "understanding", "proficiency",
    "expertise", "proficient", "familiar", "skilled",
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


def _clean_resume(resume: dict) -> dict:
    """Post-process AI output to remove filler skills and enforce formatting."""
    if isinstance(resume.get("summary"), str):
        resume["summary"] = _trim_to_two_sentences(resume["summary"])

    skills = resume.get("skills", {})
    if isinstance(skills, dict):
        # Support both old 3-category schema (technical/tools/soft) and new 5-category schema
        categories = ("languages", "frameworks", "databases", "tools", "concepts")
        # Migrate old schema if AI still returns technical/soft
        if "technical" in skills and "languages" not in skills:
            skills["languages"] = skills.pop("technical", [])
        if "soft" in skills and "concepts" not in skills:
            skills["concepts"] = skills.pop("soft", [])

        for category in categories:
            items = skills.get(category, [])
            if isinstance(items, list):
                cleaned = []
                for s in items:
                    plain = s.replace("**", "").strip().lower()
                    if plain in _BANNED_SKILLS:
                        continue
                    if len(plain) <= 3 and plain not in {
                        "aws", "gcp", "sql", "git", "c++", "c#", "r", "go",
                        "vue", "ci", "cd", "qa", "ai", "ml", "dl", "nlp",
                        "css", "php", "ios", "api", "k8s", "sas", "rds",
                    }:
                        continue
                    cleaned.append(s)
                limits = {
                    "languages": 6,
                    "frameworks": 6,
                    "databases": 4,
                    "tools": 6,
                    "concepts": 5,
                }
                skills[category] = _dedupe_keep_order(cleaned)[:limits[category]]
        resume["skills"] = skills

    # Trim experience bullets to max 3 per job
    for exp in resume.get("experience", []):
        if isinstance(exp, dict) and isinstance(exp.get("bullets"), list):
            exp["bullets"] = exp["bullets"][:3]

    # Keep projects compact and avoid repeated tech stacks
    for proj in resume.get("projects", []):
        if not isinstance(proj, dict):
            continue
        if isinstance(proj.get("tech_stack"), list):
            proj["tech_stack"] = _dedupe_keep_order(proj["tech_stack"])[:6]
        desc = proj.get("description")
        if isinstance(desc, str):
            lines = [line.strip() for line in desc.splitlines() if line.strip()]
            proj["description"] = "\n".join(lines[:3])

    return resume


# ── API calls ─────────────────────────────────────────────────────────────────

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
        max_tokens=1200,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


@_safe_call
def rewrite_resume(
    resume_text: str,
    jd_text: str,
    job_analysis: dict,
    model_id: str | None = None,
    missing_keywords: list[str] | None = None,
) -> dict:
    """Rewrite a resume for a job. If missing_keywords are provided (from pre-analysis),
    they are injected directly into the prompt so the model knows exactly what to cover
    on the FIRST pass — dramatically improving first-pass ATS score."""
    client, model = _get_client(model_id)

    # Build keyword injection block for first-pass targeting
    if missing_keywords:
        top_kw = missing_keywords[:20]  # top 20 most important missing keywords
        keyword_injection = (
            "MANDATORY KEYWORD CHECKLIST — these specific terms should be covered where they fit naturally in the final resume "
            "(weave them into summary, bullets, and skills only when it reads cleanly — do NOT list them as a dump):\n"
            + ", ".join(top_kw)
        )
    else:
        keyword_injection = ""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM},
            {
                "role": "user",
                "content": REWRITE_PROMPT.format(
                    resume=resume_text,
                    job_analysis=json.dumps(job_analysis),
                    jd=jd_text,
                    keyword_injection=keyword_injection,
                ),
            },
        ],
        temperature=0.2,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    return _clean_resume(result)


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
                    jd=jd_text,
                ),
            },
        ],
        temperature=0.1,
        max_tokens=2000,    # reduced from 3000 — patch pass needs less output space than full rewrite
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    return _clean_resume(result)


@_safe_call
def generate_cover_letter(
    tailored_resume: dict,
    job_analysis: dict,
    jd_text: str = "",
    model_id: str | None = None,
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
                    jd=jd_text or "(not provided)",
                ),
            },
        ],
        temperature=0.3,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)

@_safe_call
def generate_application_email(
    tailored_resume: dict,
    job_analysis: dict,
    jd_text: str = "",
    model_id: str | None = None,
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
                ),
            },
        ],
        temperature=0.3,
        max_tokens=300,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)

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
    return json.loads(response.choices[0].message.content)


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


CRITIQUE_SYSTEM = """You are an ATS optimization expert doing a critical review of a tailored resume.
Your job: identify exactly WHY specific keywords are missing and give concrete fix instructions.
Be specific, blunt, and actionable. Return ONLY valid JSON."""

CRITIQUE_PROMPT = """Review this tailored resume. These keywords are still missing from the ATS scan:
MISSING KEYWORDS: {missing_keywords}

CURRENT RESUME (JSON):
{resume_json}

JOB DESCRIPTION (excerpt):
{jd_excerpt}

For each missing keyword, explain WHY it's absent and WHERE/HOW to add it naturally.

Return JSON:
{{
  "overall_diagnosis": "one sentence on the main reason keywords are still missing",
  "fixes": [
    {{
      "keyword": "exact missing keyword",
      "reason_missing": "why it's not in the resume",
      "suggested_placement": "which section and how to weave it in naturally",
      "example_sentence": "a sample bullet or phrase that includes this keyword naturally"
    }}
  ],
  "priority_order": ["list the top 5 most critical missing keywords to add first"]
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
        max_tokens=600,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


@_safe_call
def critique_resume(
    tailored_resume: dict,
    missing_keywords: list[str],
    jd_text: str,
    model_id: str | None = None,
) -> dict:
    """Agent self-critique step: identify WHY keywords are still missing and how to fix them."""
    client, model = _get_client(model_id)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CRITIQUE_SYSTEM},
            {
                "role": "user",
                "content": CRITIQUE_PROMPT.format(
                    missing_keywords=", ".join(missing_keywords[:20]),
                    resume_json=json.dumps(tailored_resume)[:3000],
                    jd_excerpt=jd_text[:800],
                ),
            },
        ],
        temperature=0.1,
        max_tokens=1200,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


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
        temperature=0.4,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
