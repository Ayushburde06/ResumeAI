# ResumeAI

**An Agentic RAG Pipeline for Job-Winning Resumes**

Tailoring a resume for every single job application is exhausting, but sending a generic one means getting lost in the ATS void. I built **ResumeAI** to solve this. It’s an intelligent workflow that rewrites, formats, and scores your resume against a specific job description—usually in under 30 seconds.

This isn't just a basic ChatGPT wrapper. It uses a multi-agent feedback loop and Retrieval-Augmented Generation (RAG) grounded in actual HR best practices to ensure the output sounds like a professional human wrote it, not a robot.

---

## ⚡ The Impact
- **Saves Hours per Application:** What used to take 45 minutes of manual tweaking now takes 30 seconds.
- **Beats the ATS:** Automatically integrates critical missing keywords to maximize ATS match scores without keyword stuffing.
- **Full Application Collateral:** Generates a highly personalized cover letter, cold application email, LinkedIn outreach note, and interview prep guide—all running concurrently while your PDF renders.
- **Human-First Tone:** Employs rigorous post-processing to strip out generic AI buzzwords ("spearheaded," "delve," "synergy") and enforce a direct, fact-based writing style.

---

## 🏗️ Architecture & Workflow

ResumeAI runs on a structured, self-correcting agent pipeline:

1. **Knowledge Retrieval (RAG):** Before writing a single word, the system queries a local vector database of HR communication standards and ATS rules. This forces the LLM to adhere to proven best practices.
2. **The Agentic Loop:** 
   - A **Writer Agent** drafts a tailored version of your resume, mapping your true experience to the JD.
   - A **Critic Agent** evaluates the draft, computing a deterministic ATS keyword score. 
   - If the score is too low, the Critic forces the Writer to do another pass until the ATS threshold is met.
3. **Deterministic Verification:** A separate HR & Technical review layer fact-checks the final draft against your original uploaded resume to ensure absolute honesty. Zero hallucinated experience.
4. **Export Engine:** The finalized JSON is injected into Jinja2 templates and rendered into beautiful, A4-perfect PDFs using pure Python (WeasyPrint).

---

## 🛠️ The Tech Stack

I chose this stack for speed, reliability, and modularity:

*   **Frontend:** React 18, Vite, TypeScript, Tailwind CSS
*   **Backend:** Python 3.12+, FastAPI, Uvicorn
*   **AI Orchestration:** Custom Python state-machine orchestrator (no heavy frameworks like LangChain)
*   **Database:** SQLite with SQLAlchemy ORM
*   **PDF Generation:** Jinja2 & WeasyPrint (lightweight, Chromium-free rendering)
*   **Testing:** Pytest for deep component and agent-layer integration tests

---

## 🚀 Running Locally

Want to try it out? Setup is straightforward.

**1. Clone & Setup Backend**
```bash
git clone https://github.com/Ayushburde06/ResumeAI.git
cd ResumeAI/backend
python -m venv .venv

# Activate virtual environment
# Windows: .\.venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

pip install -r requirements.txt
```

**2. Add Environment Variables**
Create a `.env` file in the `backend/` directory and add your LLM API keys:
```env
GEMINI_API_KEY="your_key_here"
# Optional: ANTHROPIC_API_KEY, GROQ_API_KEY, OPENAI_API_KEY
```

**3. Run the Backend**
```bash
uvicorn main:app --reload
```

**4. Run the Frontend**
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
```

---

*Built with precision and care to help engineers get past the screen and into the interview.*
