# 🚀 ResumeAI: Your Agentic RAG Resume Builder

> **Why I built this:** Let's face it—applying to jobs right now is brutal. If your resume isn't perfectly tailored to the ATS (Applicant Tracking System), a bot rejects you before a human even sees your name. I knew I had to tailor my resume for every application, but doing it manually took hours. So, I built a custom **Agentic AI** system to do the heavy lifting for me in under 30 seconds.

This isn't just another ChatGPT wrapper. It is a full-stack SaaS application powered by a sophisticated **Agentic Loop** and **RAG (Retrieval-Augmented Generation)** to ensure the resumes you generate actually beat ATS filters.

---

## 🧠 How It Thinks: The Agentic Orchestrator & RAG

Instead of blindly firing a prompt to an LLM and hoping for the best, this application uses a structured, self-correcting workflow that mimics how a professional career coach operates.

### 1. RAG (Knowledge Retrieval)
When you upload your base resume, the backend doesn't just guess what to write. It uses a custom **TF-IDF retrieval engine** to search our local knowledge bases (`.jsonl` files filled with ATS rules, HR communication standards, and job market signals). This grounds the AI in actual hiring best practices.

### 2. The Agentic Loop (Self-Correction)
The **Agent Orchestrator** acts as the brain of the operation, managing a team of specialized AI agents:
* **The Writer Agent:** Drafts the first tailored version of your resume based on the job description.
* **The Critic Agent:** Once the draft is done, the system calculates a hard ATS keyword match score. If the score falls below 90%, the Critic Agent wakes up. It analyzes exactly which keywords are missing and forces the Writer Agent to do a second pass, injecting the missing technical terms naturally without keyword stuffing.
* **The Formatting Engine:** After the content is perfected, the text is dynamically injected into Jinja2 HTML templates and rendered into a pixel-perfect, ATS-friendly PDF using headless Chromium (Playwright).

### 3. Parallel Tasking
Why stop at just a resume? Once the resume is finalized, the Orchestrator spawns sub-agents in parallel to write a tailored **Cover Letter** and generate custom **Interview Prep** questions simultaneously. What used to take 75 seconds now finishes in under 30.

---

## 💻 Tech Stack

I built this end-to-end to handle everything from a buttery-smooth UI to complex AI state management:

*   **Frontend (The Face):** React 18, Vite, TypeScript, and Tailwind CSS. The UI is designed to be sleek, fast, and highly responsive.
*   **Backend (The Brains):** Python, FastAPI, and Uvicorn. FastAPI handles the asynchronous heavy lifting required to manage parallel AI agents effortlessly.
*   **Database:** SQLite + SQLAlchemy ORM for robust user history and session management.
*   **AI/Logic:** Custom Python State Machine (Agent Loop), Custom TF-IDF (RAG), and an OpenAI-compatible API.
*   **Authentication:** JWT + bcrypt hashing for secure user access.
*   **Document Processing:** `pdfplumber` for reading your base resume, and **Playwright** with Jinja2 for exporting beautiful, pixel-perfect PDFs that won't break ATS parsers.

---

## ✨ Key Features

*   **Smart Resume Tailoring:** Completely rewrites your summary, experience, and skills to perfectly align with the exact job description you provide.
*   **Live ATS Scoring:** Shows you exactly which keywords you matched and which ones you missed, in real-time.
*   **History Dashboard:** Saves every tailored version of your resume securely in your account so you can track your applications.
*   **Dynamic PDF Export:** Uses Playwright to render HTML templates into pixel-perfect PDFs, automatically adapting typography and spacing to fit everything beautifully on one page.
*   **Parallel Cover Letters & Prep:** Gets you a matching cover letter and interview guide instantly, zero extra waiting time.

---

## 🛠️ What I Learned Building This

*   **Building Agents from Scratch:** I learned how to build an agentic state machine in pure Python instead of relying on heavy frameworks. This taught me the core logic of how AI agents "think", loop, and correct themselves.
*   **Vector Math for RAG:** Implementing TF-IDF and Cosine Similarity from scratch gave me a deep, fundamental understanding of how vector search actually works under the hood.
*   **Performance Optimization:** By using `ThreadPoolExecutor` and Python's `asyncio` to run the cover letter and interview prep agents in parallel, I massively reduced the wait time for the end user.

---

## 🚀 Running it Locally

If you want to spin this up yourself:

**1. Start the Backend (FastAPI):**
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m playwright install chromium  # Install Playwright browser
uvicorn main:app --reload
```

**2. Start the Frontend (React/Vite):**
```bash
cd frontend
npm install
npm run dev
```

**3. Run Automated Tests:**
```bash
cd backend
python -m pytest tests
```

*(You'll need to create a `.env` in the `backend` folder with at least one provider key such as `GLM_API_KEY`, `GEMINI_API_KEY`, `NVIDIA_API_KEY`, or another supported model key.)*

For production, set `ALLOWED_ORIGINS` in `backend/.env` to your deployed frontend origin. If your frontend is served over HTTPS, `VITE_API_BASE_URL` must also be an HTTPS backend URL.
