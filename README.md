# 🚀 ResumeAI: Agentic RAG Resume Builder

> **Why I built this:** I was tired of applying to jobs and getting instantly rejected by ATS (Applicant Tracking System) bots. I knew I needed to tailor my resume for every single application, but doing it manually took hours. So, I built a custom Agentic AI system to do the heavy lifting for me in under 30 seconds.

This isn't just a basic ChatGPT wrapper. It's a full-stack SaaS application powered by an **Agentic Loop** and **RAG (Retrieval-Augmented Generation)** to ensure the resumes actually pass ATS filters.

---

## 🧠 The Architecture: Agentic RAG

Instead of blindly sending a prompt to an LLM, this app uses a structured, self-correcting workflow:

1. **RAG (Knowledge Retrieval):** When you upload a resume, the backend uses a custom TF-IDF retrieval engine to search local knowledge bases (`.jsonl` files containing ATS rules and job market signals) to ground the AI in actual HR best practices.
2. **The Agentic Loop (Self-Correction):**
   * The *Writer Agent* drafts the first tailored resume.
   * The system calculates a hard ATS keyword score against the Job Description.
   * If the score is below 90%, the **Critique Agent** wakes up, analyzes what keywords are missing, and forces the Writer Agent to do a second pass to fix its mistakes.
3. **Parallel Tasking:** Once the resume is perfected, the orchestrator spawns sub-agents in parallel to write a Cover Letter and generate Interview Prep questions simultaneously.

---

## 💻 Tech Stack

I built this end-to-end to handle everything from UI to complex AI state management:

*   **Frontend:** React 18, Vite, TypeScript, Tailwind CSS
*   **Backend:** Python, FastAPI, Uvicorn
*   **Database:** SQLite + SQLAlchemy ORM
*   **AI/Logic:** Custom Python State Machine (Agent Loop), Custom TF-IDF (RAG), OpenAI-compatible GLM API
*   **Authentication:** JWT + bcrypt hashing
*   **Document Processing:** pdfplumber (reading) + Puppeteer/Jinja2 (exporting pixel-perfect PDFs)

---

## ✨ Features

*   **Smart Resume Tailoring:** Completely rewrites summaries, experience, and skills based on the exact job description.
*   **Live ATS Scoring:** Shows you exactly which keywords you matched and which ones you missed.
*   **History Dashboard:** Saves every version of your tailored resumes securely in your account.
*   **PDF Export:** Uses a headless browser (Puppeteer) to export the HTML exactly as it looks on screen into an A4 PDF.
*   **Parallel Cover Letters:** Gets you a matching cover letter instantly.

---

## 🛠️ What I Learned Building This

*   **Building Agents from Scratch:** I learned how to build a state machine in Python instead of relying on heavy frameworks, teaching me the core logic of how AI agents "think" and loop.
*   **Vector Math for RAG:** Implementing TF-IDF and Cosine Similarity from scratch really helped me understand how vector databases actually work under the hood.
*   **Performance Optimization:** By using `ThreadPoolExecutor` to run the cover letter and interview prep agents in parallel, I cut the response time from 75 seconds down to under 30 seconds.

---

## 🚀 Running it Locally

If you want to spin this up yourself:

**1. Start the Backend (Python):**
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

**2. Start the Frontend (React):**
```bash
cd frontend
npm install
npm run dev
```

*(You'll need to create a `.env` in the backend folder with your `OPENAI_API_KEY`!)*

For production, set `ALLOWED_ORIGINS` in `backend/.env` to your deployed frontend origin.

If your frontend is served over HTTPS, `VITE_API_BASE_URL` must also be an HTTPS backend URL, such as `https://api.yourdomain.com/api`. A raw `http://` backend URL will be blocked by the browser as mixed content.

---
