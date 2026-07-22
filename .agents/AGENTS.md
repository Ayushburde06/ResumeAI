# Senior Technical Recruiter & Resume Architect Standards

## Objectives & ATS Target
- **ATS Target Score**: 90–95% (never target 100%; natural language and recruiter readability always take priority over raw score). Never keyword stuff.
- **Scanning Ergonomics**: Optimize for a 6–10 second recruiter skim.
- **Truthfulness Invariant**: 100% truthful. Never invent experience, companies, projects, numbers, skills, certifications, achievements, dates, or responsibilities.

## Section Rules
1. **Professional Summary**:
   - 3–5 concise lines.
   - Must include: Current Role, Experience Level, Core Technologies, Domain Expertise, Business Value, and Career Focus.
   - Banned buzzwords: *hardworking, dedicated, quick learner, self motivated, passionate, team player, results driven*.

2. **Technical Skills**:
   - Logically group into categories sorted by JD relevance: *Languages, Frontend, Backend, Frameworks, Databases, Cloud, DevOps, AI / ML, Tools, Concepts*.

3. **Professional Experience**:
   - 3–5 impact-driven bullets per role.
   - Bullet formula: `[Strong Action Verb] + [Task] + [Technology] + [Impact]`.
   - Each bullet must answer: What was built? How was it built? What business or technical impact did it create?
   - Never begin bullets with: *Worked on, Responsible for, Helped, Participated in, Involved in*.

4. **Projects**:
   - 3–4 technical bullets per project.
   - Structure: Line 1 explains WHY the project exists (value proposition), Line 2 explains HOW it was built, Lines 3–4 explain WHAT impact or functionality it delivers.

5. **AI Phrase Bans**:
   - Never use: *Leveraged, Utilized, Harnessed, Facilitated, Showcased, Demonstrated ability to, Highly motivated, Results-driven, Dynamic professional*.
   - Preferred active verbs: *Built, Designed, Developed, Created, Implemented, Optimized, Integrated, Automated, Reduced, Improved, Delivered, Engineered, Refactored, Deployed*.

6. **Rewrite Policy**:
   - Only improve weak content. Do NOT rewrite already strong bullets. Preserve candidate voice, technical details, and original accuracy.

## Deep Reasoning Models (MiniMax, DeepSeek, Qwen)
When integrating or calling deep reasoning models via OpenAI-compatible SDKs:
1. **Never hardcode `.message.content`**: Always use a wrapper like `_extract_content(response)` that falls back to `.reasoning_content` and `.reasoning` if `.content` is empty.
2. **Generous `max_tokens`**: Reasoning models consume thousands of tokens just for thinking. Always set `max_tokens=4000` or higher (even for short tasks like cover letters) to prevent truncation during the reasoning phase.

## Bullet Keyword Bolding Standard (Hybrid AI + Dynamic Engine)
When generating, tailoring, or enhancing experience / project bullets, ALWAYS apply the following bolding rules:

### Priority Order
1. **JD-Required Keywords** (highest priority): If a target Job Description is provided, wrap direct JD skill/tech matches in `**term**`.
2. **Quantifiable Impact Metrics**: Wrap ALL measurable results in `**term**` (e.g., `**45%** latency reduction`, `**10M+** daily users`, `**$500K** revenue`).
3. **Core Technical Stack**: Wrap primary technologies and frameworks used in the bullet in `**term**`.

### Hard Limits
- **Max 2–3 bold highlights per bullet**. Never bold an entire phrase or sentence.
- **Never bold action verbs** (Built, Designed, Implemented, etc.) — only the technology, metric, or JD keyword.
- **Existing `**markers**` take priority** — never reformat already-bolded text.
- **No keyword stuffing**: If a term already appears bolded earlier in the same bullet, do not bold it again.

### Bullet Bolding Example
- Before: `"Engineered microservices in Python and FastAPI reducing API latency by 45% serving 10M+ daily requests."`
- After: `"Engineered microservices in **Python** and **FastAPI** reducing API latency by **45%** serving **10M+** daily requests."`

### Rendering Layers
- **AI Layer**: LLM wraps keywords in `**term**` during generation/tailoring.
- **Backend Auto-Detect Layer**: `text_formatting.py` auto-bolds JD keywords + metrics for manually typed bullets (passed as `jd_keywords` parameter).
- **Frontend Preview**: `formatBold.tsx` renders `**term**` as `<strong>` in live preview.
- **PDF Export**: Jinja `{{ bullet | bold }}` filter renders `**term**` as `<strong>` in WeasyPrint PDF.

## PDF Template Rendering & Page Break Rules
When creating or updating HTML resume templates (modern, classic, minimal) and PDF generator logic:

1. **Markdown Bold Filter Invariant**:
   - ALWAYS pipe degree, institution, project titles, and description strings through `| bold` in Jinja templates (e.g. `{{ edu.degree | bold }}`).
   - Never assume bold markers `**` only exist in bullet points.

2. **Contact Line Wrap Invariant**:
   - Never use CSS `.contact-item + .contact-item::before { content: "|"; }` because flex wrapping creates a stray leading `|` on wrapped lines.
   - Use CSS `gap` or flex layout without pseudo-element pipes for wrap-safe contact lines.

3. **Page-Break Invariant**:
   - Single entry blocks (`.entry`, `.project`, `.job`) MUST have `page-break-inside: avoid !important` so WeasyPrint never slices individual entries or text lines across page boundaries.
   - Section containers (`.section`) keep `page-break-inside: auto !important` to allow multi-entry sections to flow across pages naturally.
